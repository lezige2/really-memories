"""多路召回与重排（海马体的索引路由）。

通道：关键词 FTS、向量、实体、人物、地点、事件、时间、情绪、最近。
融合：RRF + 相关性/热度/情绪/时间衰减重排 + 近重复抑制。
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime

from .config import Settings
from .entities import Mention
from .store import Card, Store
from .textutil import jaccard, now, parse_iso


@dataclass
class Recalled:
    card: Card
    score: float
    channels: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


@dataclass
class RecallTrace:
    query: str
    channel_hits: dict[str, int] = field(default_factory=dict)
    fused: int = 0
    picked: list[int] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = [f"{k}:{v}" for k, v in self.channel_hits.items() if v]
        return "召回通道 " + ("，".join(parts) if parts else "无") + \
               f"；融合 {self.fused} 张；注入 {len(self.picked)} 张"


def fact_predicates(query: str) -> list[str]:
    """把「我叫什么 / 我家猫叫啥 / 我住哪」映射到结构化谓词。"""
    q = query.strip()
    preds: list[str] = []
    if re.search(r"(猫|狗|宠物|养了|养着)", q):
        preds.append("宠物/养着")
    if re.search(r"(名字|叫什么|叫我什么|怎么称呼)", q) and not preds:
        preds.append("名字")
    if re.search(r"(生日|哪年出生)", q):
        preds.append("生日")
    if re.search(r"(住哪|住在|家在|哪里人)", q):
        preds.append("居住地")
    if re.search(r"(在哪工作|在哪上班|工作地|在哪上学)", q):
        preds.append("工作地")
    if re.search(r"(多大|几岁|年龄)", q):
        preds.append("年龄")
    if re.search(r"(做什么工作|职业|干什么的)", q):
        preds.append("职业")
    return preds


class IndexRouter:
    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.s = settings

    # ------------------------------------------------------------------
    def recall(self, query: str, *, emotion: float = 0.0,
               mentions: list[Mention] | None = None, topics: list[str] | None = None,
               limit: int | None = None, exclude: set[int] | None = None,
               now_dt: datetime | None = None) -> tuple[list[Recalled], RecallTrace]:
        limit = limit or self.s.max_recalled_cards
        now_dt = now_dt or now()
        mentions = mentions or []
        topics = topics or []
        exclude = set(exclude or ())
        trace = RecallTrace(query=query)
        channels: dict[str, list[int]] = {}

        def add(name: str, ids) -> None:
            ids = [int(i) for i in ids if int(i) not in exclude]
            if ids:
                channels[name] = ids
                trace.channel_hits[name] = len(ids)

        add("keyword", [cid for cid, _ in self.store.search_fts(query, self.s.recall_candidates)])
        add("vector", [cid for cid, _ in self.store.vectors.search(
            query, self.s.recall_candidates, exclude=exclude)])

        values = [m.value for m in mentions if m.type in ("person", "place", "event")]
        if values:
            add("entity", self.store.cards_mentioning(values, self.s.recall_candidates))

        people = [m.value for m in mentions if m.type == "person"]
        if people:
            ids: list[int] = []
            for p in people:
                ids.extend(self.store.cards_by_person(p, 8))
            add("person", list(dict.fromkeys(ids)))

        places = [m.value for m in mentions if m.type == "place"]
        if places:
            ids = []
            for p in places:
                ids.extend(self.store.cards_by_place(p, 8))
            add("place", list(dict.fromkeys(ids)))

        events = [m.value for m in mentions if m.type == "event"]
        if events:
            ids = []
            for e in events:
                ids.extend(self.store.cards_by_event(e, 8))
            add("event", list(dict.fromkeys(ids)))

        preds = fact_predicates(query)
        if preds:
            ids = []
            for p in preds:
                ids.extend(self.store.cards_by_predicate(p, 8))
            add("fact", list(dict.fromkeys(ids)))

        time_ids: list[int] = []
        for m in mentions:
            if m.type == "time" and m.meta.get("precision") == "day":
                time_ids.extend(self.store.cards_near_time(m.value, window_days=3, limit=10))
            elif m.type == "time" and m.meta.get("precision") == "annual":
                # 生日/纪念日：取过去一年内、且命中该标签的卡片
                time_ids.extend(self.store.search_text_like(m.value, limit=6))
        if time_ids:
            add("time", list(dict.fromkeys(time_ids)))

        if emotion >= 0.35:
            add("emotion", self.store.emotional_cards(max(0.5, emotion - 0.1), 10))

        # 近期卡片只在别的通道都没线索时兜底，避免把无关的最近记忆硬塞进来
        if not any(k in channels for k in
                   ("keyword", "vector", "entity", "person", "place", "event", "time",
                    "fact")):
            add("recent", self.store.recent_cards(5))

        # ---- RRF 融合 ----
        fused: dict[int, float] = {}
        hit_map: dict[int, dict[str, float]] = {}
        k = self.s.rrf_k
        for name, ids in channels.items():
            for rank, cid in enumerate(ids, start=1):
                fused[cid] = fused.get(cid, 0.0) + 1.0 / (k + rank)
                hit_map.setdefault(cid, {})[name] = 1.0 / (k + rank)
        trace.fused = len(fused)
        if not fused:
            trace.notes.append("长期记忆中没有可用线索")
            return [], trace

        cards = self.store.cards_by_ids(fused.keys())
        max_rrf = max(fused.values()) or 1.0
        scored: list[Recalled] = []
        for cid, rrf in fused.items():
            card = cards.get(cid)
            if not card or card.status != "active":
                continue
            days = 0.0
            at = parse_iso(card.last_access_at or card.created_at)
            if at:
                days = max(0.0, (now_dt - at).total_seconds() / 86400.0)
            heat = min(card.access_count, 8) / 8.0
            recency = math.exp(-days / 60.0)
            norm = rrf / max_rrf
            score = (0.52 * norm
                     + 0.12 * heat
                     + 0.12 * min(1.0, card.emotion_weight)
                     + 0.10 * recency
                     + 0.07 * card.confidence
                     + 0.07 * min(1.0, card.salience))
            reasons = []
            ch = hit_map.get(cid, {})
            if "keyword" in ch:
                reasons.append("关键词命中")
            if "vector" in ch:
                reasons.append("语义相近")
            if "entity" in ch or "person" in ch or "place" in ch or "event" in ch:
                reasons.append("实体命中")
            if "time" in ch:
                reasons.append("时间接近")
            if "emotion" in ch:
                reasons.append("情绪显著")
            if "recent" in ch:
                reasons.append("近期发生")
            if card.access_count:
                reasons.append(f"被想起过{card.access_count}次")
            scored.append(Recalled(card, round(score, 4), ch, reasons))

        scored.sort(key=lambda r: -r.score)

        picked: list[Recalled] = []
        for cand in scored:
            if len(picked) >= limit:
                break
            if any(self._overlaps(cand.card.text, p.card.text) for p in picked):
                continue
            picked.append(cand)

        trace.picked = [r.card.id for r in picked]
        if not picked and scored:
            trace.notes.append("候选都因近重复被抑制")
        return picked, trace

    @staticmethod
    def _overlaps(a: str, b: str) -> bool:
        """近重复抑制：高 Jaccard，或短卡片被长卡片整段包含。"""
        a, b = (a or "").strip(), (b or "").strip()
        if not a or not b:
            return False
        if jaccard(a, b) > 0.86:
            return True
        small, big = (a, b) if len(a) <= len(b) else (b, a)
        return len(small) >= 6 and small in big and len(small) / len(big) >= 0.3