# -*- coding: utf-8 -*-
"""S2-A：确定性 query expansion（只扩 query，不动块/阈值/K2/event）。

4 条通用同义对（预注册 out/S2-A-PREREG.md）：
  牌子→车牌、号码→手机号、会→会议（仅时间/日期语境）、哪儿人→老家。
保留原词、只追加目标词、最多 2 条；否定/无槽/卡号工号语境不扩。
"""

import re

MAX_EXPANSIONS = 2

_TIME_CTX = re.compile(r"几点|什么时候|哪一天|哪天|周[一二三四五六日天]|"
                       r"下周|本周|这周|下下周|几号|日期|时间")
_NEGATIVE_GUARD = re.compile(r"不会|能会|学会|会做|会不|开会")


def _has(text, term):
    return term in text


def _guard_plate(q):
    return bool(re.search(r"车|上牌|摇号|挂", q))


def _guard_phone(q):
    if re.search(r"银行卡|卡号|尾号|工号|座机|电话", q):
        return False
    return "我" in q


def _guard_meeting(q):
    if _NEGATIVE_GUARD.search(q) or "会议" in q:
        return False
    return bool(_TIME_CTX.search(q))


def _guard_hometown(q):
    return bool(re.search(r"哪儿人|哪里人", q))


_RULES = (
    {"item": "牌子→车牌", "src": "牌子", "target": "车牌", "guard": _guard_plate,
     "source": "通用口语同义（车牌也叫牌子）；限 车/上牌/摇号 语境"},
    {"item": "号码→手机号", "src": "号码", "target": "手机号", "guard": _guard_phone,
     "source": "通用口语同义；限“我”且无卡/尾号/工号"},
    {"item": "会→会议", "src": "会", "target": "会议", "guard": _guard_meeting,
     "source": "口语省略；仅时间/日期语境，排除 会做/学会/开会"},
    {"item": "哪儿人→老家", "src": "哪儿人", "pattern": r"哪儿人|哪里人",
     "target": "老家", "guard": _guard_hometown,
     "source": "通用口语同义；哪儿人/哪里人"},
)


def expand_query(text):
    """-> (expanded_text, hits)。hits=[{item,source,src,target}]（不含块文本）。"""
    q = str(text or "")
    if not q.strip():
        return q, []
    out = q
    hits = []
    for rule in _RULES:
        if len(hits) >= MAX_EXPANSIONS:
            break
        src_pat = rule.get("pattern") or re.escape(rule["src"])
        if not re.search(src_pat, q):
            continue
        if _has(out, rule["target"]):
            continue
        try:
            if not rule["guard"](q):
                continue
        except Exception:                                # noqa: BLE001
            continue
        out = out + " " + rule["target"]
        hits.append({"item": rule["item"], "source": rule["source"],
                     "src": rule["src"], "target": rule["target"]})
    return out, hits