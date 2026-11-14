# -*- coding: utf-8 -*-
"""Span 标注 + 独立 KV 标签片段（纯离线；不拼 prompt、不改块文本/sha）。

- annotate(text)：主体/时间/动作/地点对象 + 起止偏移；否定/转折/条件不抽；每块≤4类。
- search(query, blocks)：按 span 命中返回**整块**（不返回片段）。
- label_fragment(id, spans)：生成“块22｜主体=我｜时间=下周三｜事件=开会”。
- 标签片段可开关、按 token 预算裁剪（estimate_tokens 粗估）。
"""

import re

CLASSES = ("subject", "time", "action", "place_object")
MAX_CLASSES = 4
NEG_COND = re.compile(r"不是|而是|但是|但|如果|否则|虽然|不过|可是|除非|要么|"
                      r"要是|假如|即使|因为|所以")

_SUBJ = re.compile(r"(我|你|他|她|它|我们|他们|她们)"
                   r"(女儿|儿子|爸爸|妈妈|老婆|老公|孩子|猫|狗|车|手机|"
                   r"公司|老家|工作|名字|小名)?(的)?")
_TIME = re.compile(r"下周[一二三四五六日天]?|上周[一二三四五六日天]?|"
                   r"下个月|上个月|这个月|明年|今年|去年|前年|"
                   r"明天|今天|昨天|前天|后天|"
                   r"周[一二三四五六日天]|星期[一二三四五六日天]|"
                   r"每天早上|每天晚上|每天|"
                   r"(?:上午|下午|晚上|早上|中午|凌晨)\S{0,6}")
_VERB = re.compile(r"去|到|在|回|来|买|吃|喝|见|参加|开|做|看|住|飞|坐|用|"
                   r"叫|是|有|养|准备|安排|订|换|搬|学|考|玩|睡|工作|上班")
_PLACE = re.compile(r"(?:去|到|在)([\u4e00-\u9fff]{2,6})")


def _add(spans, typ, m, text):
    s = {"type": typ, "text": m.group(0), "start": m.start(), "end": m.end()}
    if s["text"] and text[s["start"]:s["end"]] == s["text"]:
        spans.append(s)


def annotate(text):
    t = str(text or "")
    out = {"text": t, "spans": [], "ok": False, "reason": ""}
    if not t.strip():
        out["reason"] = "empty"
        return out
    if NEG_COND.search(t):
        out["reason"] = "negation_or_condition"
        return out
    spans = []
    m = _SUBJ.search(t)
    if m:
        _add(spans, "subject", m, t)
    tm = _TIME.search(t)
    if tm:
        pm = _PLACE.search(t)
        _add(spans, "time", tm, t)
        if pm:
            _add(spans, "place_object", pm, t)
    act = _VERB.search(t)
    if act:
        _add(spans, "action", act, t)
    # 每类只留一个 span，且 ≤4 类
    seen, kept = set(), []
    for s in spans:
        if s["type"] in seen:
            continue
        seen.add(s["type"])
        kept.append(s)
        if len(kept) >= MAX_CLASSES:
            break
    out["spans"] = sorted(kept, key=lambda x: x["start"])
    out["ok"] = bool(out["spans"])
    if not out["ok"]:
        out["reason"] = "no_span"
    return out


def search(query, blocks, min_hit=1):
    """按 span 文本/类型命中；返回整块列表（不改块）。"""
    q = annotate(query)
    qtypes = {(s["type"], s["text"]) for s in q["spans"]}
    hit = []
    for b in blocks or []:
        a = annotate(str(b.get("text") or ""))
        btypes = {(s["type"], s["text"]) for s in a["spans"]}
        n = len(qtypes & btypes)
        if n >= min_hit or (qtypes and btypes and
                            {t for t, _ in qtypes} & {t for t, _ in btypes}):
            hit.append({"id": int(b["id"]), "score": max(n, 1),
                        "block": b})
    hit.sort(key=lambda x: (-x["score"], x["id"]))
    return hit


LABEL_NAMES = {"subject": "主体", "time": "时间", "action": "事件",
               "place_object": "地点"}


def label_fragment(block_id, spans, max_types=4):
    parts = ["块%s" % int(block_id)]
    for s in (spans or [])[:max_types]:
        name = LABEL_NAMES.get(s["type"], s["type"])
        parts.append("%s=%s" % (name, s["text"]))
    return "｜".join(parts)


def estimate_tokens(text):
    t = str(text or "")
    return max(1, int(len(t) / 1.6) + 1)


def fit_labels(fragments, max_tokens):
    """按预算裁剪标签片段（不切块文本）。"""
    kept, total = [], 0
    for f in fragments or []:
        n = estimate_tokens(f)
        if total + n > int(max_tokens):
            break
        kept.append(f)
        total += n
    return {"labels": kept, "tokens": total, "dropped": len(fragments or []) - len(kept)}