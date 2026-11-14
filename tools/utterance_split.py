# -*- coding: utf-8 -*-
"""句内语义块拆分（纯离线、默认不接写库）。

规则 span：主语 / 时间 / 动作-地点 / 谓词-值；同组保序，拼回原文逐字一致。
否定/转折/条件不拆；问句/控制句不拆；最多 6 块；抽不出就整句一块。
"""

import re

MAX_PARTS = 6
NEG_COND = re.compile(r"不是|而是|但是|但|如果|否则|虽然|不过|可是|除非|要么|"
                      r"要是|假如|即使|因为|所以")
QUESTION = re.compile(r"[？?]|吗[。！!]?$|呢[。！!]?$|什么|怎么|哪|谁|多少")
CONTROL = re.compile(r"^(记住|请|帮我|提醒|别忘了|不要|给我)")

_SUBJ = re.compile(r"^(我|你|他|她|它|我们|他们|她们)"
                   r"(女儿|儿子|爸爸|妈妈|老婆|老公|孩子|猫|狗|车|手机|"
                   r"公司|老家|工作|名字|小名)?(的)?")
_TIME = re.compile(r"^(下周[一二三四五六日天]?|上周[一二三四五六日天]?|"
                   r"下个月|上个月|这个月|明年|今年|去年|前年|"
                   r"明天|今天|昨天|前天|后天|"
                   r"周[一二三四五六日天]|星期[一二三四五六日天]|"
                   r"每天早上|每天晚上|每天|"
                   r"(?:上午|下午|晚上|早上|中午|凌晨)\S{0,6})")
_VERB = re.compile(r"去|到|在|回|来|买|吃|喝|见|参加|开|做|看|住|飞|坐|用|"
                   r"叫|是|有|养|准备|安排|订|换|搬|学|考|玩|睡|工作|上班")


def _semantic_spans(t):
    spans = []
    rest = t
    m = _SUBJ.match(rest)
    if m and m.end() > 0:
        subject = rest[:m.end()]
        if subject.endswith("的") and len(subject) > 2:
            subject = subject[:-1]
            spans.append(subject)
            rest = "的" + rest[m.end():]
        else:
            spans.append(subject)
            rest = rest[m.end():]
    tm = _TIME.match(rest)
    if tm:
        spans.append(tm.group(0))
        rest = rest[tm.end():]
    verbs = list(_VERB.finditer(rest))
    if verbs:
        prev = 0
        for i, vm in enumerate(verbs):
            if vm.start() > prev:
                seg = rest[prev:vm.start()]
                if seg.strip():
                    spans.append(seg)
            nxt = verbs[i + 1].start() if i + 1 < len(verbs) else len(rest)
            seg = rest[vm.start():nxt]
            if seg.strip():
                spans.append(seg)
            prev = nxt
        if prev < len(rest) and rest[prev:].strip():
            spans.append(rest[prev:])
    elif rest.strip():
        spans.append(rest)
    return [s for s in spans if s]


def split_utterance(text):
    t = str(text or "")
    out = {"text": t, "parts": [t], "ok": False, "reason": ""}
    if not t.strip():
        out["reason"] = "empty"
        return out
    if QUESTION.search(t.strip()):
        out["reason"] = "question"
        return out
    if CONTROL.search(t.strip()):
        out["reason"] = "control"
        return out
    if NEG_COND.search(t):
        out["reason"] = "negation_or_condition"
        return out
    parts = _semantic_spans(t)
    while len(parts) > MAX_PARTS:                      # 合并尾部，保持逐字
        parts[-2:] = [parts[-2] + parts[-1]]
    if "".join(parts) != t:
        out["reason"] = "fidelity_broken"
        out["parts"] = [t]
        return out
    if len(parts) < 2:
        out["reason"] = "single_block"
        return out
    out.update(parts=parts, ok=True)
    return out