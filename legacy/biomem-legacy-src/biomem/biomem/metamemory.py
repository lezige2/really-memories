"""元记忆路由：先判断「这一句需不需要翻长期记忆」。

规则版，可解释、零延迟；后续可换成小模型分类器。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .textutil import estimate_tokens

# 指向过去/共同经历
PAST_MARKERS = (
    "记得", "还记得", "之前", "以前", "上次", "上回", "那天", "当时", "后来",
    "曾经", "去年", "前年", "小时候", "当年", "说过", "提过", "聊过", "答应",
)
# 关系词
RELATION_MARKERS = ("我们", "咱", "你和我", "你和我的", "咱俩", "你之前", "你上次")
# 询问自我信息
SELF_QUESTION = re.compile(
    r"(我(?:的)?[^，。！？]{0,8}(?:叫什么|是谁|几岁|多大|生日|住在哪|喜欢什么|讨厌什么|养了|叫什么名字))"
)
# 明确指令
EXPLICIT_RECALL = re.compile(r"(回忆|想一想|翻一下|找找|查一下记忆|你记得|还记得)")
# 招呼/应答，通常不需要检索
SMALL_TALK = re.compile(
    r"^(你好|您好|hi|hello|嗨|在吗|在么|早|早上好|晚安|好梦|谢谢|多谢|ok|好的|嗯+|哦+|啊+|哈哈+|hhh+|拜拜|再见)[。！？!?~～]*$",
    re.I,
)


@dataclass
class Decision:
    needs_recall: bool
    score: float
    reasons: list[str] = field(default_factory=list)

    def explain(self) -> str:
        return ("需要检索" if self.needs_recall else "无需检索") + \
               f"（{self.score:.1f}）" + ("：" + "、".join(self.reasons) if self.reasons else "")


class Metamemory:
    def __init__(self, threshold: float = 2.0) -> None:
        self.threshold = threshold

    def decide(self, text: str, *, has_history: bool = True) -> Decision:
        t = (text or "").strip()
        score = 0.0
        reasons: list[str] = []

        if SMALL_TALK.match(t):
            return Decision(False, 0.0, ["寒暄/应答"])

        if any(w in t for w in PAST_MARKERS):
            score += 2.0
            reasons.append("提到过去/共同经历")
        if EXPLICIT_RECALL.search(t):
            score += 2.5
            reasons.append("明确要求回忆")
        if any(w in t for w in RELATION_MARKERS):
            score += 1.2
            reasons.append("关系词")
        if SELF_QUESTION.search(t):
            score += 1.6
            reasons.append("询问自我信息")
        if re.search(r"(生日|纪念日|周年|忌日)", t):
            score += 1.2
            reasons.append("时间锚点")
        if re.search(r"(它|他|她|那件事|那个|那个梗|那句话)", t):
            score += 0.8
            reasons.append("代词回指")

        # 专有名词/称呼无法完全靠规则判断，长句默认略加分
        length = estimate_tokens(t)
        if length >= 18:
            score += 0.5
            reasons.append("信息量较大")

        if not has_history:
            return Decision(False, score, reasons + ["没有历史可查"])

        return Decision(score >= self.threshold, round(score, 2), reasons or ["无显著线索"])