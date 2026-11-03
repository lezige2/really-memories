# -*- coding: utf-8 -*-
"""Shadow 去重判定（纯代码；只给 would_merge/risk，绝不合并、不写库）。

规则：
  1) 同 tenant+scope；
  2) 同族（p1b_subject.extract 的 predicate）且值归一等 → would_merge=True；
  3) 无值时按字符 bigram Jaccard >= 0.80；
  4) 多实体重叠（同族同值但主体不同/多个“我的车”）→ would_merge=True + risk=multi_entity；
  5) 值不同/族不同 → would_merge=False（risk=value_mismatch/family_mismatch）。
调用方只能在 risk 为空时合并；本模块永不写库。
"""

import re
import unicodedata

try:
    import p1b_subject as P
except ImportError:                                  # 纯兜底：无 P1b 也能跑
    P = None

JACCARD_MIN = 0.80
_MULTI_HINT = re.compile(r"另一辆|另一只|另外一|第二辆|第二个|新买的|又买了|也白|也是白色|也黑")
_NEG = re.compile(r"不是|不叫|不在|不养|没有|不是我的|已经不在|离职|退|取消|不")
_QUALIFIER = re.compile(r"工作|私人|备用|家庭|公司|个人")
_DIGITS = re.compile(r"\d+")


def _norm(v):
    s = unicodedata.normalize("NFKC", str(v or ""))
    return re.sub(r"[\s,，。．.、:：;；!！?？\-—_·]+", "", s).lower()


def _bigrams(text):
    s = _norm(text)
    return {s[i:i + 2] for i in range(max(0, len(s) - 1))}


def jaccard(a, b):
    A, B = _bigrams(a), _bigrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / float(len(A | B))


def family_contain_ok(family):
    return family in ("车牌", "工位", "会议")


def _extract(text):
    if P is None:
        return {}
    try:
        return P.extract(text) or {}
    except Exception:                                # noqa: BLE001
        return {}


def decide(text_a, text_b, tenant="default", scope="default"):
    """-> {would_merge, risk, reason, score, family, value_equal, tenant, scope}"""
    out = {"would_merge": False, "risk": None, "reason": "",
           "score": 0.0, "family": None, "value_equal": False,
           "tenant": tenant, "scope": scope,
           "merge_allowed": False}
    ia, ib = _extract(text_a), _extract(text_b)
    fa, fb = ia.get("predicate"), ib.get("predicate")
    va, vb = _norm(ia.get("value")), _norm(ib.get("value"))
    if fa and fb and fa != fb:
        out.update(risk="family_mismatch", reason="不同族：%s vs %s" % (fa, fb))
        return out
    same_family = bool(fa and fa == fb)
    # 否定（一方否定/离开）不得合并
    neg_a, neg_b = bool(_NEG.search(text_a)), bool(_NEG.search(text_b))
    if neg_a != neg_b:
        out.update(risk="negation", reason="一方是否定/离开表述")
        return out
    # 槽位限定词（工作号 vs 手机号）不同槽
    qa, qb = bool(_QUALIFIER.search(text_a)), bool(_QUALIFIER.search(text_b))
    if same_family and qa != qb:
        out.update(risk="slot_qualifier", reason="限定词不同，视为不同槽")
        return out
    # 数字/日期不一致不得合并
    da, db = set(_DIGITS.findall(text_a)), set(_DIGITS.findall(text_b))
    if da and db and da != db:
        out.update(risk="value_mismatch", reason="数字/日期不一致")
        return out
    norm_a, norm_b = _norm(text_a), _norm(text_b)
    value_equal = bool(va and vb and va == vb)
    if not value_equal and same_family and family_contain_ok(fa):
        value_equal = bool((va and va in norm_b) or (vb and vb in norm_a))
    score = jaccard(text_a, text_b)
    out.update(family=fa or fb, value_equal=value_equal, score=round(score, 4))
    if same_family and value_equal:
        multi = bool(_MULTI_HINT.search(text_a) or _MULTI_HINT.search(text_b))
        if multi:
            out.update(would_merge=True, risk="multi_entity",
                       reason="同族同值但存在多实体线索，禁止静默合并")
            return out
        out.update(would_merge=True, merge_allowed=True, reason="同族+值归一相等")
        return out
    if not (va and vb) and score >= JACCARD_MIN:
        out.update(would_merge=True, merge_allowed=True,
                   reason="无值但文本 Jaccard=%.2f>=%.2f" % (score, JACCARD_MIN))
        return out
    if va and vb and va != vb:
        out.update(risk="value_mismatch", reason="同族但值不同：%s vs %s" % (va, vb))
        return out
    out.update(risk="low_similarity" if score < JACCARD_MIN else "value_missing",
               reason="相似度不足或无值")
    return out


def evaluate(pairs, labels):
    """pairs: {pair_id: (a,b)}；labels: {pair_id: 'same'|'different'}。"""
    stats = {"total": 0, "correct": 0, "same": 0, "different": 0,
             "wrong_merge": 0, "missed_merge": 0, "multi_entity_flagged": 0,
             "failures": []}
    for pid, label in labels.items():
        if pid not in pairs:
            continue
        a, b = pairs[pid]
        d = decide(a, b)
        stats["total"] += 1
        stats[label] = stats.get(label, 0) + 1
        if d["risk"] == "multi_entity":
            stats["multi_entity_flagged"] += 1
        predicted = bool(d["would_merge"] and d["risk"] is None)
        if predicted == (label == "same"):
            stats["correct"] += 1
        else:
            stats["failures"].append({"pair_id": pid, "label": label,
                                      "decision": d})
        if label == "different" and predicted:
            stats["wrong_merge"] += 1
        if label == "same" and not predicted:
            stats["missed_merge"] += 1
    stats["accuracy"] = (round(stats["correct"] / stats["total"], 4)
                         if stats["total"] else 0.0)
    return stats


def evaluate_fixtures(fixtures):
    """42 冲突夹具：同一 pre_state 内 remember 文本两两不得 merge_allowed。"""
    stats = {"fixtures": 0, "pairs": 0, "wrong_merge": 0, "failures": []}
    for fx in fixtures:
        texts = [s.get("text") or "" for s in (fx.get("pre_state") or [])
                 if s.get("action") == "remember"]
        stats["fixtures"] += 1
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                stats["pairs"] += 1
                d = decide(texts[i], texts[j])
                if d["would_merge"] and d["risk"] is None:
                    stats["wrong_merge"] += 1
                    stats["failures"].append({"fixture": fx.get("id"),
                                              "decision": d})
    return stats