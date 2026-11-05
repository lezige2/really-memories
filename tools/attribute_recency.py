# -*- coding: utf-8 -*-
"""属性最新值 POC（手机号 / 健身时间）；默认 off，只做选择集过滤，不改答案。

- 仅显式问句触发；
- 同属性+同值类型才成组；组内多值只留 created_at/id 最新 1 条；
- 多实体/类型不一致/值抽取失败 -> 不过滤（不静默：返回 reason）。
"""

import re

PHONE_Q = re.compile(r"手机号|手机|电话")
FIT_Q = re.compile(r"健身")
FIT_TIME_Q = re.compile(r"几点|什么时候|时间")
MULTI = re.compile(r"另一|第二|另一只|另一辆|还有一只|两只|另外一")

PHONE_VAL = re.compile(r"(?<!\d)(1[3-9]\d(?:-?\d{4}){2}|1[3-9]\d{9})(?!\d)")
FIT_VAL = re.compile(
    r"周[一二三四五六日天].{0,6}?(上午|下午|晚上|早上|中午)?"
    r"[一二三四五六七八九十]{1,3}点(半|[一二三四五六七八九十]{1,3}分)?")


def detect(query):
    q = str(query or "")
    if PHONE_Q.search(q) and "我" in q:
        return "phone"
    if FIT_Q.search(q) and FIT_TIME_Q.search(q):
        return "fitness"
    return None


def extract(text, attr):
    t = str(text or "")
    if attr == "phone":
        m = PHONE_VAL.search(t)
        return m.group(0) if m else None
    if attr == "fitness":
        m = FIT_VAL.search(t)
        return m.group(0) if m else None
    return None


def apply_filter(query, selection, meta=None):
    """-> {applied, attribute, kept, hidden, reason}；selection 为 [{source_id,...}]。"""
    out = {"applied": False, "attribute": None, "kept": [], "hidden": [],
           "reason": ""}
    attr = detect(query)
    out["attribute"] = attr
    if attr is None:
        out["reason"] = "no_attribute"
        return out
    se = list(selection or [])
    if not se:
        out["reason"] = "empty_selection"
        return out
    meta = meta or {}
    texts = {}
    for s in se:
        sid = int(s.get("source_id"))
        texts[sid] = str(meta.get(sid, {}).get("text") or "")
    if any(MULTI.search(t) for t in texts.values()):
        out["reason"] = "multi_entity"
        return out
    # 只在“有值块”中成组；无值块原样保留、不算失败
    ids = sorted(texts)
    if not ids:
        out["reason"] = "empty_selection"
        return out
    values = {}
    for sid in ids:
        v = extract(texts[sid], attr)
        if v is not None:
            values[sid] = re.sub(r"[-\s]", "", v)
    if len(values) < 2:
        out["reason"] = "value_missing"
        return out

    def key(sid):
        m = meta.get(sid) or {}
        return (str(m.get("created_at") or ""), int(sid))

    newest = max(values, key=key)
    hidden = sorted(sid for sid in values if sid != newest)
    kept = [sid for sid in ids if sid not in hidden]
    out.update(applied=True, kept=kept, hidden=hidden,
               reason="filtered" if hidden else "single_value",
               values={str(k): v for k, v in values.items()})
    return out