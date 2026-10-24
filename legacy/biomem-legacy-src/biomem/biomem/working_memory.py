"""工作记忆（前额叶工作台）：有限槽位，按显著性淘汰。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .entities import Extraction
from .indexes import Recalled
from .store import Store

TASK_RE = re.compile(r"(帮我|请你|帮忙|写一?个|查一下|算一下|分析一下|整理一下|给我建议|怎么做|怎么办)")


@dataclass
class WorkingState:
    recent: list[dict] = field(default_factory=list)
    topic: str | None = None
    emotion: float = 0.0
    task: str | None = None
    cards: list[Recalled] = field(default_factory=list)
    persona_digest: str = ""

    def summary(self) -> str:
        bits = []
        if self.topic:
            bits.append(f"话题：{self.topic}")
        if self.emotion >= 0.3:
            bits.append(f"情绪强度：{self.emotion:.2f}")
        if self.task:
            bits.append(f"当前任务：{self.task}")
        return "；".join(bits)


class WorkingMemory:
    """固定槽位：最近对话 / 当前话题 / 当前情绪 / 当前任务 / 召回卡片。"""

    def __init__(self, store: Store, recent_turns: int = 8) -> None:
        self.store = store
        self.recent_turns = recent_turns
        self.state = WorkingState()

    def begin_turn(self, session_id: str, user_text: str,
                   extraction: Extraction, cards: list[Recalled],
                   persona_digest: str) -> WorkingState:
        recent = self.store.recent_utterances(session_id, self.recent_turns)
        # 当前这句已经入库，历史里去掉它，避免重复
        if recent and recent[-1]["speaker"] == "user" and recent[-1]["text"] == user_text:
            history = recent[:-1]
        else:
            history = recent

        topics = extraction.topics
        if topics:
            topic = topics[0]
            if self.state.topic and self.state.topic != topic and len(topics) > 1:
                topic = f"{self.state.topic} → {topics[0]}"
        else:
            topic = self.state.topic

        emotion = max(extraction.emotion, self.state.emotion * 0.55)
        task = None
        m = TASK_RE.search(user_text)
        if m:
            task = user_text[:60]
        elif self.state.task and extraction.emotion < 0.2:
            task = self.state.task

        self.state = WorkingState(
            recent=history,
            topic=topic,
            emotion=round(emotion, 3),
            task=task,
            cards=cards,
            persona_digest=persona_digest,
        )
        return self.state

    def reset(self) -> None:
        self.state = WorkingState()