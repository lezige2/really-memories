# -*- coding: utf-8 -*-
"""组级配对检索（纯离线，不接生成、不改块、不建表）。

- groups：显式 group_id/related_ids/derived_from 优先；否则按“区间重叠 + 主题相同”派生。
- 组级时间：组内区间并集与查询区间相交。
- 组级主题：组内最大主题分需过阈值（默认 0.15）。
- 组级歧义：组内多区间互不重叠 -> fallback。
- created_at 晚于查询指向的事件区间 -> fallback（指向不明）。
- 无组同时满足时间+主题 -> abstain。
- 事实类返回组内最新块；事件类返回组内多块（同一组全部）。
"""

import temporal_timeline as TL
import temporal_retrieval as T

TOPIC_MIN = 0.14


def _key(row):
    return (str(row.get("group_id") or ""), tuple(row.get("related") or []))


def build_groups(rows):
    """只按显式 group_id 分组；无 group_id 的单块自成组（不派生、不加 session_id）。"""
    groups = {}
    for r in rows or []:
        gid = r.get("group_id")
        key = str(gid) if gid else "single-%s" % r.get("id")
        groups.setdefault(key, []).append(r)
    return [_mk_group(gid, grp) for gid, grp in groups.items()]


def _mk_group(gid, rows):
    ivs = []
    for r in rows:
        ivs.extend(TL.extract_intervals(r.get("text"), str(r.get("created_at"))))
    return {"group_id": str(gid), "rows": list(rows), "intervals": ivs,
            "anchor": str(rows[0].get("created_at") if rows else ""),
            "text": "\n".join(str(r.get("text") or "") for r in rows)}


def _uniq_ranges(ivs):
    return {(i["start"], i["end"]) for i in ivs}


def retrieve(query, now, rows, topk=4):
    now_dt = now
    qivs = TL.extract_intervals(query, now_dt)
    groups = build_groups(rows)
    out = {"query": query, "query_intervals": qivs, "groups": [],
           "kept": [], "abstain": False, "ambiguous": False,
           "created_conflict": False, "reason": "", "lazy": False}
    if not qivs:
        out.update(lazy=True, reason="no_time_expression")
        for g in groups:
            score, shared = T._topic_score(query, g["text"])
            out["groups"].append(_export(g, score, "lazy"))
        out["kept"] = [r for g in out["groups"] for r in g["blocks"]][:topk]
        return out
    cands = []
    for g in groups:
        hit = any(TL._overlap(q, iv) for q in qivs for iv in g["intervals"])
        score, shared = T._topic_score(query, g["text"])
        if g["intervals"]:
            max_end = max(i["end"] for i in g["intervals"])
            q_end = max(i["end"] for i in qivs)
            if g["anchor"] and g["anchor"][:10] > q_end:
                out["created_conflict"] = True
        if hit and score >= TOPIC_MIN:
            cands.append((g, score))
    if not cands:
        out.update(abstain=True, reason="no_group_time_topic")
        return out
    for g, score in cands:
        amb = len(_uniq_ranges(g["intervals"])) > 1
        if amb:
            out["ambiguous"] = True
        reason = "ambiguous_fallback" if amb else "time+topic"
        exp = _export(g, score, reason)
        out["groups"].append(exp)
        out["kept"].extend(exp["blocks"])
    if out["created_conflict"]:
        out["reason"] = "created_after_event"
    elif out["ambiguous"]:
        out["reason"] = "ambiguous_time_expression"
    else:
        out["reason"] = "group_time_topic"
    out["kept"] = out["kept"][:topk]
    return out


def _export(g, score, reason):
    latest = None
    for r in g["rows"]:
        key = (str(r.get("created_at") or ""), int(r["id"]))
        if latest is None or key > latest[0]:
            latest = (key, r)
    blocks = [{"id": int(r["id"]), "text": str(r.get("text") or ""),
               "note": "event_block"} for r in g["rows"]]
    if latest is not None:
        blocks[0]["note"] = "fact_latest"
    ivs = sorted(g["intervals"], key=lambda i: -i.get("spec", 0))
    return {"group_id": g["group_id"], "score": round(float(score), 4),
            "reason": reason, "anchor": g["anchor"],
            "intervals": ivs,
            "phrases": [i.get("phrase") for i in g["intervals"]],
            "blocks": blocks, "latest_id": int(latest[1]["id"]) if latest else None}