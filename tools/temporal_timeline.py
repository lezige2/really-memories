# -*- coding: utf-8 -*-
"""时间轴检索（纯离线）：多时间词 -> 归一区间 -> 区间+主题检索。

只做检索，不调模型、不改回答。默认不接服务；不建表/不改块。
"""

import re
from datetime import datetime, timedelta

import temporal_retrieval as T

Interval = dict


def _period_phrase(pattern, kind, start, end, phrase):
    return {"kind": kind, "start": start.date().isoformat(),
            "end": end.date().isoformat(), "phrase": phrase,
            "spec": {"D": 3, "R": 3, "M": 2, "Y": 1}[kind]}


def extract_intervals(text, anchor):
    """支持多时间词（绝对/相对、过去/未来）；返回按出现顺序的区间列表。"""
    t = str(text or "")
    now = anchor if isinstance(anchor, datetime) else datetime.fromisoformat(str(anchor))
    out = []

    def add(kind, start, end, phrase):
        p = _period_phrase(None, kind, start, end, phrase)
        if not any(x["start"] == p["start"] and x["end"] == p["end"] for x in out):
            out.append(p)

    for m in T.ABS_DATE.finditer(t):
        d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        add("D", d, d, m.group(0))
    for m in T.ABS_MONTH.finditer(t):
        y, mo = int(m.group(1)), int(m.group(2))
        s = datetime(y, mo, 1)
        e = datetime(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1) - timedelta(days=1)
        add("M", s, e, m.group(0))
    for m in re.finditer(r"(\d{4})\s*年(?!\s*\d{1,2}\s*月)", t):
        y = int(m.group(1))
        add("Y", datetime(y, 1, 1), datetime(y, 12, 31), m.group(0))
    for word, off in T.REL_DAY.items():
        if word in t:
            d = now + timedelta(days=off)
            add("D", d, d, word)
    for word, off in T.WEEK.items():
        if word in t:
            monday = now - timedelta(days=now.weekday()) + timedelta(weeks=off)
            add("R", monday, monday + timedelta(days=6), word)
    for word, off in T.REL_MONTH.items():
        if word in t:
            y = now.year + (now.month - 1 + off) // 12
            mo = (now.month - 1 + off) % 12 + 1
            s = datetime(y, mo, 1)
            e = datetime(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1) - timedelta(days=1)
            add("M", s, e, word)
    for word, off in T.REL_YEAR.items():
        for mm in re.finditer(re.escape(word) + r"\s*([一二三四五六七八九十]{1,2})月", t):
            y = now.year + off
            mo = T._int(mm.group(1))
            if 1 <= mo <= 12:
                s2 = datetime(y, mo, 1)
                e2 = datetime(y + (1 if mo == 12 else 0),
                              1 if mo == 12 else mo + 1, 1) - timedelta(days=1)
                add("M", s2, e2, mm.group(0))
    for word, off in T.REL_YEAR.items():
        if word in t:
            y = now.year + off
            add("Y", datetime(y, 1, 1), datetime(y, 12, 31), word)
    for m in T.N_YEARS.finditer(t):
        y = now.year - T._int(m.group(1))
        add("Y", datetime(y, 1, 1), datetime(y, 12, 31), m.group(0))
    for m in T.N_YEARS_AFTER.finditer(t):
        y = now.year + T._int(m.group(1))
        add("Y", datetime(y, 1, 1), datetime(y, 12, 31), m.group(0))
    return out


def build_timeline(rows):
    """每块导出 intervals + anchor + phrase。"""
    out = []
    for r in rows or []:
        text = str(r.get("text") or "")
        anchor = str(r.get("created_at") or "")
        ivs = extract_intervals(text, anchor)
        out.append({"id": int(r["id"]), "text": text, "anchor": anchor,
                    "intervals": ivs,
                    "phrases": [x["phrase"] for x in ivs]})
    return out


def _overlap(a, b):
    return a["start"] <= b["end"] and b["start"] <= a["end"]


def retrieve(query, now, rows, topk=4):
    """查询区间 + 主题；无时间词惰性；显式时间无块 -> abstain；歧义 -> fallback。"""
    anchor = now if isinstance(now, datetime) else datetime.fromisoformat(str(now))
    qivs = extract_intervals(query, anchor)
    tl = build_timeline(rows)
    out = {"query": query, "anchor": anchor.isoformat(),
           "query_intervals": qivs, "kept": [], "abstain": False,
           "ambiguous": False, "lazy": False, "reason": "",
           "timeline": tl}
    if not qivs:
        out.update(lazy=True, reason="no_time_expression")
        ranked = []
        for b in tl:
            score, shared = T._topic_score(query, b["text"])
            ranked.append((score, b))
        ranked.sort(key=lambda x: (-x[0], x[1]["id"]))
        out["kept"] = [{"id": b["id"], "score": s, "intervals": b["intervals"],
                        "anchor": b["anchor"], "phrase": None,
                        "reason": "lazy_topic"} for s, b in ranked[:topk]]
        return out
    ranges = {(x["start"], x["end"]) for x in qivs}
    if len(ranges) > 1:
        out.update(ambiguous=True, reason="ambiguous_time_expression")
    cand = []
    for b in tl:
        hit = any(_overlap(q, iv) for q in qivs for iv in b["intervals"])
        score, shared = T._topic_score(query, b["text"])
        if hit or (out["ambiguous"] and shared > 0):
            cand.append((hit, score, b))
    if not cand:
        out.update(abstain=True, reason="no_time_match")
        return out
    cand.sort(key=lambda x: (-int(x[0]), -x[1], x[2]["id"]))
    for hit, score, b in cand[:topk]:
        out["kept"].append({"id": b["id"], "score": round(score, 4),
                            "intervals": b["intervals"], "anchor": b["anchor"],
                            "phrase": (b["phrases"][0] if b["phrases"] else None),
                            "reason": "time+topic" if hit else "ambiguous_fallback"})
    return out