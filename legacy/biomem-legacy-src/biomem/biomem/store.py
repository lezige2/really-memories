"""长期存储：原文、卡片、实体/位置索引、关键词、向量分片、审计。

内容只存一份；其余都是线索。
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from array import array
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

from .config import Settings
from .entities import Extraction, Mention
from .textutil import (clip_tokens, estimate_tokens, fts_body, fts_match,
                       iso, jaccard, now, parse_iso, tokenize)


# ----------------------------------------------------------------------
# 轻量向量：哈希 n-gram 词形向量（无需额外模型，离线可用）
# 语义模型的接口保留在 Embedder 协议里，后续可换成 llama.cpp 的 bge 端点。
# ----------------------------------------------------------------------
def embed_text(text: str, dim: int = 512) -> list[float]:
    feats: dict[str, float] = {}
    for t in tokenize(text, drop_stop=True):
        feats[t] = feats.get(t, 0.0) + 1.0
    compact = re.sub(r"\s+", "", text.lower())
    for i in range(max(0, len(compact) - 2)):
        g = "#" + compact[i:i + 3]
        feats[g] = feats.get(g, 0.0) + 0.35
    vec = [0.0] * dim
    for key, count in feats.items():
        h = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(h[:4], "little") % dim
        sign = 1.0 if h[4] & 1 else -1.0
        vec[idx] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class VectorIndex:
    """按 shard 落盘的向量索引；查询时逐片加载，仅缓存少量热片。"""

    def __init__(self, conn, dim: int, shards: int, cache_shards: int = 3) -> None:
        self.conn = conn
        self.dim = dim
        self.shards = max(1, shards)
        self.cache_shards = max(1, cache_shards)
        self._cache: OrderedDict[int, tuple[list[int], list[list[float]]]] = OrderedDict()

    def shard_of(self, card_id: int) -> int:
        return card_id % self.shards

    def add(self, card_id: int, text: str) -> None:
        vec = embed_text(text, self.dim)
        blob = array("f", vec).tobytes()
        shard = self.shard_of(card_id)
        self.conn.execute(
            "INSERT OR REPLACE INTO idx_vector(card_id, shard_id, dim, vec) VALUES(?,?,?,?)",
            (card_id, shard, self.dim, blob),
        )
        self._cache.pop(shard, None)

    def remove(self, card_id: int) -> None:
        self.conn.execute("DELETE FROM idx_vector WHERE card_id=?", (card_id,))
        self._cache.clear()

    def _load_shard(self, shard: int) -> tuple[list[int], list[list[float]]]:
        if shard in self._cache:
            self._cache.move_to_end(shard)
            return self._cache[shard]
        ids: list[int] = []
        vecs: list[list[float]] = []
        rows = self.conn.execute(
            "SELECT card_id, dim, vec FROM idx_vector WHERE shard_id=?", (shard,)
        ).fetchall()
        for row in rows:
            if row["dim"] != self.dim:
                continue
            arr = array("f")
            arr.frombytes(row["vec"])
            ids.append(row["card_id"])
            vecs.append(list(arr))
        self._cache[shard] = (ids, vecs)
        self._cache.move_to_end(shard)
        while len(self._cache) > self.cache_shards:
            self._cache.popitem(last=False)
        return ids, vecs

    def search(self, text: str, limit: int = 24, exclude: set[int] | None = None) -> list[tuple[int, float]]:
        q = embed_text(text, self.dim)
        exclude = exclude or set()
        scored: list[tuple[int, float]] = []
        for shard in range(self.shards):
            ids, vecs = self._load_shard(shard)
            for cid, v in zip(ids, vecs):
                if cid in exclude:
                    continue
                score = sum(a * b for a, b in zip(q, v))
                if score > 0.02:
                    scored.append((cid, score))
        scored.sort(key=lambda x: -x[1])
        return scored[:limit]

    def clear_cache(self) -> None:
        self._cache.clear()


@dataclass
class Card:
    id: int
    kind: str
    text: str
    summary: str | None
    created_at: str
    updated_at: str
    source: str
    confidence: float
    emotion_weight: float
    salience: float
    strength: float
    strength_updated_at: str
    access_count: int
    last_access_at: str | None
    version: int
    status: str
    supersedes_id: int | None
    session_id: str | None
    meta_json: str | None

    @property
    def meta(self) -> dict:
        try:
            return json.loads(self.meta_json or "{}")
        except Exception:
            return {}

    @classmethod
    def from_row(cls, row) -> "Card":
        return cls(**{k: row[k] for k in row.keys() if k in cls.__dataclass_fields__})


class Store:
    def __init__(self, conn, settings: Settings) -> None:
        self.conn = conn
        self.s = settings
        self.vectors = VectorIndex(conn, settings.vector_dim, settings.vector_shards,
                                   settings.vector_cache_shards)

    # ------------------------------------------------------------------
    # 原文 / 会话
    # ------------------------------------------------------------------
    def ensure_session(self, session_id: str, mode: str = "chat") -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO session(id, started_at, mode) VALUES(?,?,?)",
            (session_id, iso(now()), mode),
        )

    def set_session_mode(self, session_id: str, mode: str) -> None:
        self.conn.execute("UPDATE session SET mode=? WHERE id=?", (mode, session_id))

    def session_mode(self, session_id: str) -> str:
        row = self.conn.execute("SELECT mode FROM session WHERE id=?", (session_id,)).fetchone()
        return row["mode"] if row else "chat"

    def next_turn(self, session_id: str) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(MAX(turn_idx), 0) + 1 AS n FROM utterance WHERE session_id=?",
            (session_id,),
        ).fetchone()
        return int(row["n"])

    def add_utterance(self, session_id: str, turn_idx: int, speaker: str, text: str,
                      emotion: float = 0.0, meta: dict | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO utterance(session_id, turn_idx, speaker, text, created_at, "
            "emotion_weight, meta_json) VALUES(?,?,?,?,?,?,?)",
            (session_id, turn_idx, speaker, text, iso(now()), emotion,
             json.dumps(meta or {}, ensure_ascii=False)),
        )
        return int(cur.lastrowid)

    def index_utterance(self, utterance_id: int, mentions: Sequence[Mention]) -> None:
        for m in mentions:
            eid = self._entity_id(m.type, m.value)
            self.conn.execute(
                "INSERT OR IGNORE INTO idx_entity_span(entity_id, utterance_id, sentence_idx, "
                "start_offset, end_offset, surface) VALUES(?,?,?,?,?,?)",
                (eid, utterance_id, m.sentence_idx, m.start, m.end, m.surface),
            )

    def recent_utterances(self, session_id: str, limit: int = 8) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM utterance WHERE session_id=? ORDER BY turn_idx DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def count_utterances(self, session_id: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM utterance WHERE session_id=?", (session_id,)
        ).fetchone()
        return int(row[0])

    # ------------------------------------------------------------------
    # 卡片
    # ------------------------------------------------------------------
    def add_card(self, *, text: str, kind: str, source: str, confidence: float,
                 emotion: float = 0.0, salience: float = 0.5, session_id: str | None = None,
                 summary: str | None = None, meta: dict | None = None,
                 status: str = "active", supersedes_id: int | None = None,
                 created_at: str | None = None,
                 utterance_ids: Sequence[int] = (),
                 mentions: Sequence[Mention] = ()) -> int:
        ts = created_at or iso(now())
        cur = self.conn.execute(
            "INSERT INTO memory_card(kind, text, summary, created_at, updated_at, source, "
            "confidence, emotion_weight, salience, strength, strength_updated_at, access_count, "
            "version, status, supersedes_id, session_id, meta_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (kind, text, summary, ts, ts, source, confidence, emotion, salience,
             1.0, ts, 0, 1, status, supersedes_id, session_id,
             json.dumps(meta or {}, ensure_ascii=False)),
        )
        cid = int(cur.lastrowid)
        self._index_card(cid, text, ts, mentions)
        for uid in utterance_ids:
            self.conn.execute(
                "INSERT OR IGNORE INTO card_provenance(card_id, utterance_id) VALUES(?,?)",
                (cid, uid),
            )
        return cid

    def _index_card(self, card_id: int, text: str, ts: str,
                    mentions: Sequence[Mention] = ()) -> None:
        self.conn.execute(
            "INSERT INTO card_fts(card_id, body) VALUES(?,?)", (card_id, fts_body(text))
        )
        self.vectors.add(card_id, text)
        for m in mentions:
            eid = self._entity_id(m.type, m.value)
            self.conn.execute(
                "INSERT OR IGNORE INTO card_entity(card_id, entity_id, weight) VALUES(?,?,?)",
                (card_id, eid, 1.0),
            )
            if m.type == "time":
                precision = m.meta.get("precision", "day")
                self.conn.execute(
                    "INSERT OR REPLACE INTO idx_time(card_id, ts, precision, label) VALUES(?,?,?,?)",
                    (card_id, m.value, precision, m.surface),
                )
            elif m.type == "person":
                self.conn.execute(
                    "INSERT OR IGNORE INTO idx_person(card_id, person) VALUES(?,?)",
                    (card_id, m.value),
                )
            elif m.type == "place":
                self.conn.execute(
                    "INSERT OR IGNORE INTO idx_place(card_id, place) VALUES(?,?)",
                    (card_id, m.value),
                )
            elif m.type == "event":
                self.conn.execute(
                    "INSERT OR IGNORE INTO idx_event(card_id, event_type) VALUES(?,?)",
                    (card_id, m.value),
                )

    def _entity_id(self, etype: str, value: str) -> int:
        row = self.conn.execute(
            "SELECT id FROM entity WHERE type=? AND value=?", (etype, value)
        ).fetchone()
        if row:
            return int(row["id"])
        cur = self.conn.execute(
            "INSERT INTO entity(type, value, created_at) VALUES(?,?,?)",
            (etype, value, iso(now())),
        )
        return int(cur.lastrowid)

    def get_card(self, card_id: int) -> Card | None:
        row = self.conn.execute("SELECT * FROM memory_card WHERE id=?", (card_id,)).fetchone()
        return Card.from_row(row) if row else None

    def cards_by_ids(self, ids: Iterable[int]) -> dict[int, Card]:
        ids = list(ids)
        if not ids:
            return {}
        q = ",".join("?" * len(ids))
        rows = self.conn.execute(
            f"SELECT * FROM memory_card WHERE id IN ({q})", ids
        ).fetchall()
        return {r["id"]: Card.from_row(r) for r in rows}

    def update_card(self, card_id: int, **fields) -> None:
        allowed = {"text", "summary", "confidence", "emotion_weight", "salience",
                   "strength", "strength_updated_at", "status", "version",
                   "supersedes_id", "meta_json", "updated_at", "last_access_at",
                   "access_count", "created_at"}
        sets, vals = [], []
        for k, v in fields.items():
            if k not in allowed:
                raise ValueError(f"不可更新字段: {k}")
            sets.append(f"{k}=?")
            vals.append(v)
        if not sets:
            return
        vals.append(card_id)
        self.conn.execute(f"UPDATE memory_card SET {', '.join(sets)} WHERE id=?", vals)

    def set_status(self, card_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE memory_card SET status=?, updated_at=? WHERE id=?",
            (status, iso(now()), card_id),
        )

    def touch(self, card_ids: Iterable[int], delta: float | None = None) -> None:
        delta = self.s.access_reinforce if delta is None else delta
        ts = iso(now())
        for cid in card_ids:
            row = self.conn.execute(
                "SELECT strength FROM memory_card WHERE id=?", (cid,)
            ).fetchone()
            if not row:
                continue
            new_strength = min(1.5, float(row["strength"]) + delta)
            self.conn.execute(
                "UPDATE memory_card SET access_count=access_count+1, last_access_at=?, "
                "strength=?, strength_updated_at=? WHERE id=?",
                (ts, new_strength, ts, cid),
            )

    def list_cards(self, *, status: str | None = "active", kind: str | None = None,
                   limit: int = 20, order: str = "recent") -> list[Card]:
        where, args = [], []
        if status:
            where.append("status=?")
            args.append(status)
        if kind:
            where.append("kind=?")
            args.append(kind)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        order_sql = {
            "recent": "ORDER BY created_at DESC, id DESC",
            "strong": "ORDER BY strength DESC, emotion_weight DESC",
            "old": "ORDER BY created_at ASC",
        }.get(order, "ORDER BY created_at DESC")
        rows = self.conn.execute(
            f"SELECT * FROM memory_card {clause} {order_sql} LIMIT ?", args + [limit]
        ).fetchall()
        return [Card.from_row(r) for r in rows]

    # ------------------------------------------------------------------
    # 召回通道
    # ------------------------------------------------------------------
    def search_fts(self, query: str, limit: int = 24) -> list[tuple[int, float]]:
        match = fts_match(query)
        if not match:
            return []
        try:
            rows = self.conn.execute(
                "SELECT card_id, bm25(card_fts) AS rank FROM card_fts "
                "WHERE card_fts MATCH ? ORDER BY rank LIMIT ?",
                (match, limit),
            ).fetchall()
        except Exception:
            return []
        return [(int(r["card_id"]), -float(r["rank"])) for r in rows]

    def cards_mentioning(self, values: Sequence[str], limit: int = 24) -> list[int]:
        values = [v for v in dict.fromkeys(values) if v]
        if not values:
            return []
        q = ",".join("?" * len(values))
        rows = self.conn.execute(
            f"SELECT ce.card_id, SUM(ce.weight) AS w FROM card_entity ce "
            f"JOIN entity e ON e.id = ce.entity_id "
            f"JOIN memory_card c ON c.id = ce.card_id "
            f"WHERE e.value IN ({q}) AND c.status='active' "
            f"GROUP BY ce.card_id ORDER BY w DESC LIMIT ?",
            list(values) + [limit],
        ).fetchall()
        return [int(r["card_id"]) for r in rows]

    def cards_by_person(self, person: str, limit: int = 16) -> list[int]:
        rows = self.conn.execute(
            "SELECT ip.card_id FROM idx_person ip JOIN memory_card c ON c.id=ip.card_id "
            "WHERE ip.person=? AND c.status='active' ORDER BY c.created_at DESC LIMIT ?",
            (person, limit),
        ).fetchall()
        return [int(r["card_id"]) for r in rows]

    def cards_by_predicate(self, predicate: str, limit: int = 8) -> list[int]:
        rows = self.conn.execute(
            "SELECT id FROM memory_card WHERE status='active' "
            "AND json_extract(meta_json, '$.predicate')=? "
            "ORDER BY salience DESC, strength DESC, id DESC LIMIT ?",
            (predicate, limit),
        ).fetchall()
        return [int(r["id"]) for r in rows]

    def cards_by_place(self, place: str, limit: int = 16) -> list[int]:
        rows = self.conn.execute(
            "SELECT ip.card_id FROM idx_place ip JOIN memory_card c ON c.id=ip.card_id "
            "WHERE ip.place=? AND c.status='active' ORDER BY c.created_at DESC LIMIT ?",
            (place, limit),
        ).fetchall()
        return [int(r["card_id"]) for r in rows]

    def cards_by_event(self, event: str, limit: int = 16) -> list[int]:
        rows = self.conn.execute(
            "SELECT ie.card_id FROM idx_event ie JOIN memory_card c ON c.id=ie.card_id "
            "WHERE ie.event_type=? AND c.status='active' ORDER BY c.created_at DESC LIMIT ?",
            (event, limit),
        ).fetchall()
        return [int(r["card_id"]) for r in rows]

    def cards_near_time(self, day_iso: str, window_days: int = 3, limit: int = 16) -> list[int]:
        from datetime import date, timedelta
        try:
            d = date.fromisoformat(day_iso)
        except ValueError:
            return []
        lo = (d - timedelta(days=window_days)).isoformat()
        hi = (d + timedelta(days=window_days)).isoformat()
        rows = self.conn.execute(
            "SELECT it.card_id FROM idx_time it JOIN memory_card c ON c.id=it.card_id "
            "WHERE it.ts BETWEEN ? AND ? AND c.status='active' "
            "ORDER BY ABS(julianday(it.ts) - julianday(?)) LIMIT ?",
            (lo, hi, day_iso, limit),
        ).fetchall()
        return [int(r["card_id"]) for r in rows]

    def recent_cards(self, limit: int = 8) -> list[int]:
        rows = self.conn.execute(
            "SELECT id FROM memory_card WHERE status='active' "
            "ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [int(r["id"]) for r in rows]

    def emotional_cards(self, min_emotion: float, limit: int = 12) -> list[int]:
        rows = self.conn.execute(
            "SELECT id FROM memory_card WHERE status='active' AND emotion_weight>=? "
            "ORDER BY emotion_weight DESC, created_at DESC LIMIT ?",
            (min_emotion, limit),
        ).fetchall()
        return [int(r["id"]) for r in rows]

    def search_text_like(self, needle: str, limit: int = 10) -> list[int]:
        rows = self.conn.execute(
            "SELECT id FROM memory_card WHERE status='active' AND text LIKE ? "
            "ORDER BY created_at DESC LIMIT ?", (f"%{needle}%", limit)
        ).fetchall()
        return [int(r["id"]) for r in rows]

    # ------------------------------------------------------------------
    # 维护
    # ------------------------------------------------------------------
    def merge_cards(self, target_id: int, source_id: int) -> None:
        """把来源卡片并入目标卡片：保留原文，索引去重，强度叠加。"""
        src = self.get_card(source_id)
        tgt = self.get_card(target_id)
        if not src or not tgt:
            return
        self.conn.execute(
            "INSERT OR IGNORE INTO card_provenance(card_id, utterance_id) "
            "SELECT ?, utterance_id FROM card_provenance WHERE card_id=?",
            (target_id, source_id),
        )
        meta = tgt.meta
        dup = meta.get("merged_from", [])
        dup.append(source_id)
        meta["merged_from"] = dup[-20:]
        self.update_card(
            target_id,
            strength=min(1.5, tgt.strength + 0.08),
            salience=min(1.0, tgt.salience + 0.05),
            version=tgt.version + 1,
            updated_at=iso(now()),
            meta_json=json.dumps(meta, ensure_ascii=False),
        )
        self.conn.execute("DELETE FROM card_fts WHERE card_id=?", (source_id,))
        self.vectors.remove(source_id)
        self.conn.execute("DELETE FROM card_entity WHERE card_id=?", (source_id,))
        self.conn.execute("DELETE FROM idx_person WHERE card_id=?", (source_id,))
        self.conn.execute("DELETE FROM idx_place WHERE card_id=?", (source_id,))
        self.conn.execute("DELETE FROM idx_event WHERE card_id=?", (source_id,))
        self.update_card(source_id, status="superseded", supersedes_id=target_id,
                         updated_at=iso(now()))

    def archive(self, card_id: int, reason: str = "forgotten") -> None:
        card = self.get_card(card_id)
        if not card or card.kind == "procedural":
            return
        self.set_status(card_id, "archived")
        self.add_event("archive", card_id, reason)

    def add_event(self, kind: str, card_id: int | None = None, detail: str = "") -> None:
        self.conn.execute(
            "INSERT INTO memory_event(ts, kind, card_id, detail) VALUES(?,?,?,?)",
            (iso(now()), kind, card_id, detail),
        )

    def add_conflict(self, a: int, b: int, reason: str) -> None:
        self.conn.execute(
            "INSERT INTO conflict(card_a, card_b, reason, created_at) VALUES(?,?,?,?)",
            (a, b, reason, iso(now())),
        )
        self.add_event("conflict", b, f"{a} <-> {b}: {reason}")

    def active_cards(self, limit: int = 5000) -> list[Card]:
        rows = self.conn.execute(
            "SELECT * FROM memory_card WHERE status='active' AND kind!='procedural' "
            "ORDER BY id LIMIT ?", (limit,)
        ).fetchall()
        return [Card.from_row(r) for r in rows]

    def stats(self) -> dict:
        def count(sql: str, *args) -> int:
            return int(self.conn.execute(sql, args).fetchone()[0])

        cards = count("SELECT COUNT(*) FROM memory_card WHERE status='active'")
        return {
            "cards_active": cards,
            "cards_archived": count("SELECT COUNT(*) FROM memory_card WHERE status='archived'"),
            "cards_superseded": count("SELECT COUNT(*) FROM memory_card WHERE status='superseded'"),
            "cards_conflicted": count("SELECT COUNT(*) FROM memory_card WHERE status='conflicted'"),
            "utterances": count("SELECT COUNT(*) FROM utterance"),
            "entities": count("SELECT COUNT(*) FROM entity"),
            "sessions": count("SELECT COUNT(*) FROM session"),
            "conflicts_open": count("SELECT COUNT(*) FROM conflict WHERE resolved=0"),
            "db_mb": round(self.conn.execute("PRAGMA page_count").fetchone()[0]
                           * self.conn.execute("PRAGMA page_size").fetchone()[0] / 1048576, 2),
        }