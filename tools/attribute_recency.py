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
    r"[一二三四五六七八九十]{1,3}点(半|[一二三四五六七八九十]{1,3}分?)?")


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

def apply_rerank(query, selection, meta=None):
    """K3' 最小版：只重排不隐藏。有值块按 created_at/id 最新在前，无值块随后（稳定）。"""
    out = {"applied": False, "attribute": None, "order": [], "reason": ""}
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
    ids, texts = [], {}
    for s in se:
        sid = int(s.get("source_id"))
        ids.append(sid)
        texts[sid] = str(meta.get(sid, {}).get("text") or "")
    if any(MULTI.search(t) for t in texts.values()):
        out["reason"] = "multi_entity"
        return out
    valued = []
    for sid in ids:
        if extract(texts[sid], attr) is not None:
            m = meta.get(sid) or {}
            valued.append((str(m.get("created_at") or ""), int(sid)))
    if len(valued) < 2:
        out["reason"] = "value_missing"
        return out

    def key(item):
        return (item[0], item[1])

    order_valued = [sid for _t, sid in sorted(valued, key=key, reverse=True)]
    order = order_valued + [sid for sid in ids if sid not in order_valued]
    out.update(applied=True, order=order, reason="reranked")
    return out

FALLBACK_MULTI = re.compile(r"另一辆|另一只|我爱人|第二套|第二辆|第二只|还有一只|两只")
FALLBACK_NEG = re.compile(r"算了|不是这个|还叫原来|不去了|取消了|不再|不是|改回")


def _my_query(query):
    q = str(query or "")
    return "我" in q


def direct_answer(query, rows):
    """确定性槽位直答：rows=[{id,text,created_at}]。返回 applied/value/block_id/reason。"""
    out = {"applied": False, "attribute": None, "value": None,
           "block_id": None, "reason": ""}
    attr = detect(query)
    out["attribute"] = attr
    if attr is None:
        out["reason"] = "no_attribute"
        return out
    if not _my_query(query):
        out["reason"] = "not_my_query"
        return out
    rows = list(rows or [])
    if not rows:
        out["reason"] = "no_rows"
        return out
    if any(FALLBACK_MULTI.search(str(r.get("text") or "")) for r in rows):
        out["reason"] = "multi_entity"
        return out
    # 最新块整体含否定/回滚 -> 回退（即使没有可抽值）
    newest_row = max(rows, key=lambda r: (str(r.get("created_at") or ""),
                                          int(r["id"])))
    if FALLBACK_NEG.search(str(newest_row.get("text") or "")):
        out["reason"] = "negation_in_latest"
        return out
    vals = []
    for r in rows:
        v = extract(r.get("text"), attr)
        if v is None:
            continue
        vals.append({"id": int(r["id"]), "value": v,
                     "created_at": str(r.get("created_at") or ""),
                     "text": str(r.get("text") or "")})
    if not vals:
        out["reason"] = "value_missing"
        return out
    vals.sort(key=lambda x: (x["created_at"], x["id"]))
    newest = vals[-1]
    prev = vals[-2] if len(vals) > 1 else None
    reason = "latest"
    if prev and prev["created_at"] == newest["created_at"]:
        if prev["id"] == newest["id"]:               # 同一行：不可能
            out["reason"] = "same_row"
            return out
        reason = "latest_same_second"                # 同秒按 id 大者胜
    out.update(applied=True, value=newest["value"], block_id=newest["id"],
               reason=reason)
    return out