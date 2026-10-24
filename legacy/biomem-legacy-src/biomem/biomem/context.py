"""上下文存储模块：把工作记忆与长期记忆装配成有限上下文。

不是 prompt 压缩器，而是「存储—召回—装配」循环里的装配端：
预算固定，优先保证最近对话，其次召回卡片，最后才是话题/任务提示。
"""
from __future__ import annotations

from .config import Settings
from .indexes import Recalled
from .textutil import clip_tokens, estimate_tokens, human_date, now
from .working_memory import WorkingState


class ContextAssembler:
    def __init__(self, settings: Settings) -> None:
        self.s = settings

    # ------------------------------------------------------------------
    def _card_line(self, r: Recalled) -> str:
        c = r.card
        when = human_date(c.created_at)
        body = c.summary or c.text
        body = clip_tokens(body, 90)
        return f"- [{when}] {body}"

    def build(self, *, system_prompt: str, state: WorkingState,
              user_text: str) -> list[dict]:
        budget = self.s.context_budget_tokens
        messages: list[dict] = [{"role": "system", "content": system_prompt}]

        memory_block = ""
        if state.cards:
            lines = [self._card_line(r) for r in state.cards[: self.s.max_recalled_cards]]
            memory_block = "【回忆起：关于用户的信息，可能模糊】\n" + "\n".join(lines)
            messages.append({"role": "system", "content": memory_block})

        wm = state.summary()
        if wm:
            messages.append({"role": "system", "content": f"【当前工作记忆】{wm}"})

        history = list(state.recent)
        # 预算：先保证系统提示 + 本轮用户输入
        fixed = sum(estimate_tokens(m["content"]) for m in messages) + estimate_tokens(user_text)
        room = max(300, budget - fixed)
        lines = []
        for u in history:
            speaker = "用户" if u["speaker"] == "user" else "你"
            lines.append(f"{speaker}：{u['text']}")
        # 从最旧的开始丢，直到进预算
        while lines and estimate_tokens("\n".join(lines)) > room:
            lines.pop(0)

        if lines:
            messages.append({"role": "system", "content": "【最近对话】\n" + "\n".join(lines)})
        messages.append({"role": "user", "content": user_text})
        return messages