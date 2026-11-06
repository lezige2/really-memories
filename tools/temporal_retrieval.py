# -*- coding: utf-8 -*-
"""离线两轴检索 POC（时间 + 主题），不改 daily、不建表。

输入 query / anchor / rows；返回 kept、normalized_query、每块 normalized_date/anchor/reason。
规则：显式时间且无任何块落在范围 -> abstain（不做“现在”顶替）；过滤后为空回退加权，不返回空。
"""

import re
from datetime import datetime, timedelta

ABS_DATE = re.compile(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日号]?")
ABS_MONTH = re.compile(r"(\d{4})[-/年](\d{1,2})月?")
ABS_YEAR = re.compile(r"(\d{4})\s*年?")
N_YEARS = re.compile(r"([一二两三四五六七八九十\d]{1,2})\s*年前")
N_YEARS_AFTER = re.compile(r"([一二两三四五六七八九十\d]{1,2})\s*年后")
REL_YEAR = {"去年": -1, "前年": -2, "今年": 0, "明年": 1, "后年": 2}
REL_MONTH = {"下下个月": 2, "上上个月": -2, "上个月": -1, "下个月": 1,
             "这个月": 0, "本月": 0, "上月": -1, "下月": 1}
REL_DAY = {"前天": -2, "昨天": -1, "今天": 0, "明天": 1, "后天": 2}
WEEK = {"下下周": 2, "上上周": -2, "上周": -1, "这周": 0, "本周": 0,
        "下周": 1}

_CN = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
       "七": 7, "八": 8, "九": 9, "十": 10}
_STOP_CHARS = set("我的你他她它是在有和与就都也这那么什几谁哪吗呢吧啊呀哦了过要去到"
                  "个年月日周天点时候上下午晚早前后")
_STOP_BIGRAMS = {"去年", "前年", "今年", "明年", "后年", "上个", "下个", "这个",
                 "个月", "上个月", "下个月", "这个月", "上周", "下周", "这周",
                 "本周", "去过", "什么", "几个", "多少", "买了", "换了", "去了",
                 "在哪", "哪天", "时候", "几点", "我去", "我在", "我在", "我买",
                 "我换", "么时", "么搬", "年我", "月我", "我要", "我在",
                 "买什", "交什", "忙什", "有什", "周我"}
_STOP = _STOP_CHARS


def _int(s):
    s = str(s)
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if "十" in s:
        a, _, b = s.partition("十")
        return (_CN.get(a, 1) if a else 1) * 10 + (_CN.get(b, 0) if b else 0)
    return _CN.get(s, 1)


def _period(kind, start, end):
    return {"kind": kind, "start": start.date().isoformat() if hasattr(start, "date") else str(start),
            "end": end.date().isoformat() if hasattr(end, "date") else str(end),
            "spec": {"D": 3, "R": 3, "M": 2, "Y": 1}[kind]}


def normalize(text, anchor):
    """-> period|None（多词取最具体：D/R > M > Y）。"""
    t = str(text or "")
    if isinstance(anchor, str):
        anchor = datetime.fromisoformat(anchor)
    cands = []
    m = ABS_DATE.search(t)
    if m:
        d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        cands.append(_period("D", d, d))
    m = ABS_MONTH.search(t)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        s = datetime(y, mo, 1)
        e = datetime(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1) - timedelta(days=1)
        cands.append(_period("M", s, e))
    m = ABS_YEAR.search(t)
    if m and not ABS_MONTH.search(t) and not ABS_DATE.search(t):
        y = int(m.group(1))
        cands.append(_period("Y", datetime(y, 1, 1), datetime(y, 12, 31)))
    for word, off in REL_DAY.items():
        if word in t:
            d = anchor + timedelta(days=off)
            cands.append(_period("D", d, d))
    for word, off in WEEK.items():
        if word in t:
            monday = anchor - timedelta(days=anchor.weekday()) + timedelta(weeks=off)
            cands.append(_period("R", monday, monday + timedelta(days=6)))
    for word, off in REL_MONTH.items():
        if word in t:
            y = anchor.year + (anchor.month - 1 + off) // 12
            mo = (anchor.month - 1 + off) % 12 + 1
            s = datetime(y, mo, 1)
            e = datetime(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1) - timedelta(days=1)
            cands.append(_period("M", s, e))
    for word, off in REL_YEAR.items():
        if word in t:
            y = anchor.year + off
            cands.append(_period("Y", datetime(y, 1, 1), datetime(y, 12, 31)))
    m = N_YEARS.search(t)
    if m:
        y = anchor.year - _int(m.group(1))
        cands.append(_period("Y", datetime(y, 1, 1), datetime(y, 12, 31)))
    m = N_YEARS_AFTER.search(t)
    if m:
        y = anchor.year + _int(m.group(1))
        cands.append(_period("Y", datetime(y, 1, 1), datetime(y, 12, 31)))
    if not cands:
        return None
    return max(cands, key=lambda p: p["spec"])


def _overlap(a, b):
    return a["start"] <= b["end"] and b["start"] <= a["end"]


def _bigrams(text):
    t = "".join(ch for ch in str(text or "") if ch.isalnum())
    return {t[i:i + 2] for i in range(max(0, len(t) - 1))
            if t[i:i + 2] not in _STOP_BIGRAMS}


GENERIC_Q = re.compile(r"做什么|干什么|有什么事|什么安排|干嘛|做啥|什么计划|计划|打算")


def _topic_score(query, text):
    q = {g for g in _bigrams(query) if g not in _STOP}
    d = {g for g in _bigrams(text) if g not in _STOP}
    if not q or not d:
        return 0.0, 0
    shared = q & d
    return len(shared) / float(len(q)), len(shared)


def search(query, anchor, rows, topk=4):
    anchor_dt = anchor if isinstance(anchor, datetime) else datetime.fromisoformat(str(anchor))
    qp = normalize(query, anchor_dt)
    out = {"query": query, "anchor": anchor_dt.isoformat(),
           "normalized_query": qp, "abstain": False, "reason": "",
           "kept": []}
    scored = []
    for r in rows or []:
        text = str(r.get("text") or "")
        b_anchor = str(r.get("created_at") or anchor_dt.isoformat())
        bp = normalize(text, b_anchor)
        ts, shared = _topic_score(query, text)
        scored.append({"id": int(r["id"]), "text": text, "period": bp,
                       "anchor": b_anchor, "topic": round(ts, 4),
                       "shared": shared})
    if qp is not None:
        cand = [b for b in scored if b["period"] and _overlap(qp, b["period"])]
        if not GENERIC_Q.search(str(query or "")):
            cand = [b for b in cand if b["shared"] > 0]
        if not cand:
            out.update(abstain=True, reason="no_time_match")
            return out
        ranked = cand
    else:
        ranked = [b for b in scored if b["shared"] > 0] or scored
    ranked.sort(key=lambda b: (-(b["topic"]), b["id"]))
    for b in ranked[:max(1, int(topk))]:
        out["kept"].append({"id": b["id"], "score": b["topic"],
                            "normalized_date": (b["period"]["start"]
                                                if b["period"] else None),
                            "anchor": b["anchor"],
                            "reason": ("time+topic" if qp else "topic")})
    if not out["kept"]:
        out["abstain"] = True
        out["reason"] = "empty_fallback"
    return out

RETRO_RE = re.compile(r"去年|前年|[一二两三四五六七八九十\d]{1,2}年前|上个月|上月|"
                      r"上周|前天|昨天|当时|上次|过去|以前|之前")
FUTURE_RE = re.compile(r"下周|下个月|明年|后天|明天|今天|下下周|后年")


def is_retrospective(query, now):
    """只认回溯词/过去的绝对日期；下周三/明年/下个月/今天/明天不触发。"""
    q = str(query or "")
    now_dt = now if isinstance(now, datetime) else datetime.fromisoformat(str(now))
    if FUTURE_RE.search(q) and not RETRO_RE.search(q):
        return False
    if RETRO_RE.search(q):
        return True
    m = ABS_DATE.search(q)
    if m:
        try:
            d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return d.date() < now_dt.date()
        except Exception:                            # noqa: BLE001
            return False
    return False