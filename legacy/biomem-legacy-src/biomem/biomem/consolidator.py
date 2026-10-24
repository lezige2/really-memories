"""空闲巩固（睡眠）：把对话压成情景卡片、去重、抽象、处理冲突。

串行、低优先级；生产环境里应放在后台线程/低优先级进程，这里用一个
显式的 run() 保证可测试、可观察。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

from .config import Settings
from .db import get_meta, set_meta
from .entities import extract
from .persona import Persona
from .store import Store
from .textutil import (clip_tokens, estimate_tokens, iso, jaccard, now,
                       parse_iso, split_sentences)

SMALL_TALK = {"嗯", "哦", "啊", "好", "好的", "哈哈", "在吗", "你好", "晚安", "谢谢"}


@dataclass
class ConsolidationReport:
    windows: int = 0
    created: int = 0
    merged: int = 0
    conflicts: int = 0
    skipped: int = 0
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (f"巩固完成：窗口 {self.windows}，新卡片 {self.created}，"
                f"合并 {self.merged}，冲突 {self.conflicts}，跳过 {self.skipped}")


class Consolidator:
    def __init__(self, store: Store, settings: Settings, persona: Persona,
                 llm=None) -> None:
        self.store = store
        self.s = settings
        self.persona = persona
        self.llm = llm

    # ------------------------------------------------------------------
    def run(self, *, session_id: str | None = None, force: bool = False,
            use_llm: bool = False) -> ConsolidationReport:
        report = ConsolidationReport()
        cursor = int(get_meta(self.store.conn, "consolidate_cursor", "0") or 0)
        rows = self.store.conn.execute(
            "SELECT * FROM utterance WHERE id>? " +
            ("AND session_id=? " if session_id else "") +
            "ORDER BY id LIMIT 400",
            ([cursor, session_id] if session_id else [cursor]),
        ).fetchall()
        if not rows:
            return report

        windows = self._windows([dict(r) for r in rows])
        report.windows = len(windows)
        for win in windows:
            if not self._worth_remembering(win):
                report.skipped += 1
                continue
            payload = self._build_window(win, use_llm=use_llm)
            if payload is None:
                report.skipped += 1
                continue
            dup = self._find_duplicate(payload["text"])
            if dup:
                self._absorb(dup, payload)
                report.merged += 1
            else:
                self.store.add_card(**payload["card"])
                report.created += 1

        report.conflicts = self._resolve_conflicts()
        set_meta(self.store.conn, "consolidate_cursor",
                 str(max(int(r["id"]) for r in rows)))
        self.store.add_event(
            "consolidate",
            detail=json.dumps({"windows": report.windows, "created": report.created,
                               "merged": report.merged, "conflicts": report.conflicts},
                              ensure_ascii=False),
        )
        return report

    # ------------------------------------------------------------------
    def _windows(self, rows: list[dict]) -> list[list[dict]]:
        """按会话、连续回合切窗；窗口最多 N 条发言。"""
        windows: list[list[dict]] = []
        cur: list[dict] = []
        for r in rows:
            if cur and (r["session_id"] != cur[-1]["session_id"]
                        or len(cur) >= self.s.consolidate_window):
                windows.append(cur)
                cur = []
            cur.append(r)
        if cur:
            windows.append(cur)
        return windows

    def _worth_remembering(self, win: list[dict]) -> bool:
        text = " ".join(r["text"] for r in win)
        if len(text.strip()) < 8:
            return False
        stripped = text.strip()
        if stripped in SMALL_TALK or all(len(r["text"].strip()) <= 3 for r in win):
            return False
        return True

    def _build_window(self, win: list[dict], *, use_llm: bool) -> dict | None:
        user_turns = [r for r in win if r["speaker"] == "user"]
        if not user_turns:
            return None
        text_parts = []
        for r in win:
            who = "用户" if r["speaker"] == "user" else "你"
            text_parts.append(f"{who}：{r['text'].strip()}")
        text = "\n".join(text_parts)
        ex = extract(text, known_people=self.persona.known_people())
        emotion = max([float(r["emotion_weight"] or 0) for r in win] + [ex.emotion])
        salience = min(1.0, 0.35 + emotion * 0.4 + (0.15 if ex.mentions else 0))
        summary = None
        if use_llm and self.llm is not None:
            try:
                summary = self.llm.summarize(text)
            except Exception:
                summary = None
        if not summary:
            summary = self._rule_summary(text)
        return {
            "text": text,
            "card": dict(
                text=clip_tokens(text, 900),
                kind="episodic",
                source="consolidation",
                confidence=0.65,
                emotion=emotion,
                salience=salience,
                summary=summary,
                meta={"window": [r["id"] for r in win], "topics": ex.topics[:4]},
                utterance_ids=[r["id"] for r in win],
                mentions=ex.mentions,
                created_at=win[0]["created_at"],
            ),
        }

    def _absorb(self, card_id: int, payload: dict) -> None:
        """把重复窗口并进已有卡片：加来源、提强度，不再新建。"""
        card = self.store.get_card(card_id)
        if not card:
            return
        for uid in payload["card"]["utterance_ids"]:
            self.store.conn.execute(
                "INSERT OR IGNORE INTO card_provenance(card_id, utterance_id) VALUES(?,?)",
                (card_id, uid),
            )
        meta = card.meta
        merged = meta.get("merged_from", [])
        merged.append(payload["card"]["meta"]["window"])
        meta["merged_from"] = merged[-20:]
        self.store.update_card(
            card_id,
            strength=min(1.5, card.strength + 0.08),
            salience=min(1.0, card.salience + 0.04),
            version=card.version + 1,
            updated_at=iso(now()),
            meta_json=json.dumps(meta, ensure_ascii=False),
        )
        self.store.add_event("merge", card_id, f"absorb {len(payload['card']['utterance_ids'])} utts")

    @staticmethod
    def _rule_summary(text: str) -> str:
        # 取用户说的第一句有效内容做摘要，去掉「用户：」前缀
        lines = [ln for ln in text.splitlines() if ln.startswith("用户：")]
        base = lines[0][3:] if lines else text
        sent = split_sentences(base)
        s = sent[0][3] if sent else base
        return s[:80] + ("…" if len(s) > 80 else "")

    def _find_duplicate(self, text: str) -> int | None:
        candidates = [cid for cid, _ in self.store.search_fts(text, 8)]
        candidates += [cid for cid, _ in self.store.vectors.search(text, 8)]
        for cid in dict.fromkeys(candidates):
            card = self.store.get_card(cid)
            if not card or card.status != "active":
                continue
            if jaccard(text, card.text) >= self.s.dedupe_jaccard:
                return cid
            # 语义卡片往往只是窗口里的一句话：用包含度判断是否已被覆盖
            if card.kind == "semantic" and len(card.text) >= 6 and card.text[:120] in text:
                return cid
        return None

    # ------------------------------------------------------------------
    def _resolve_conflicts(self) -> int:
        """同一主体+谓词下出现不同宾语：显式纠正则取代，否则标记冲突。"""
        rows = self.store.conn.execute(
            "SELECT * FROM memory_card WHERE status='active' AND kind IN ('semantic','relational')"
        ).fetchall()
        groups: dict[tuple[str, str], list] = {}
        for r in rows:
            try:
                meta = json.loads(r["meta_json"] or "{}")
            except Exception:
                continue
            pred, obj = meta.get("predicate"), meta.get("object")
            if not pred or not obj:
                continue
            groups.setdefault((meta.get("subject", "用户"), pred), []).append((r, obj, meta))

        count = 0
        for (_subject, pred), items in groups.items():
            objects = {obj for _r, obj, _m in items}
            if len(objects) <= 1:
                continue
            items.sort(key=lambda x: (x[0]["created_at"], x[0]["id"]))
            newest = items[-1]
            corrected = bool(newest[2].get("correction"))
            for old in items[:-1]:
                if old[0]["id"] == newest[0]["id"]:
                    continue
                if corrected and float(newest[0]["confidence"]) >= float(old[0]["confidence"]):
                    self.store.update_card(
                        old[0]["id"], status="superseded",
                        supersedes_id=newest[0]["id"], updated_at=iso(now()))
                    self.store.add_event("conflict", old[0]["id"],
                                         f"被纠正：{pred}={newest[1]}")
                else:
                    for cid in (old[0]["id"], newest[0]["id"]):
                        card = self.store.get_card(cid)
                        if not card:
                            continue
                        meta = card.meta
                        meta["conflict"] = True
                        self.store.update_card(
                            cid, meta_json=json.dumps(meta, ensure_ascii=False))
                    exists = self.store.conn.execute(
                        "SELECT 1 FROM conflict WHERE resolved=0 AND "
                        "((card_a=? AND card_b=?) OR (card_a=? AND card_b=?))",
                        (old[0]["id"], newest[0]["id"],
                         newest[0]["id"], old[0]["id"]),
                    ).fetchone()
                    if not exists:
                        self.store.add_conflict(old[0]["id"], newest[0]["id"],
                                                f"{pred}: {old[1]} vs {newest[1]}")
                count += 1
        return count