# -*- coding: utf-8 -*-
"""out/relation_heldout_score.py —— 只评分，不改规则、不打印/查看原文。

对 out/RELATION-HELDOUT-60.jsonl 跑现有 predict(old,new)（v1 规则）与
predict_v2(old,new)（recall 补丁），只输出聚合指标、混淆矩阵、id 列表。
任何 old/new 原文都不写入 stdout / 本脚本输出文件。
"""
import hashlib
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import relation_baseline as rb  # noqa: E402  只 import，不修改其行为

GOLD = "out/RELATION-HELDOUT-60.jsonl"
OUT = "out/RELATION-HELDOUT-SCORE.json"
EXPECT_SHA = "475d6ec44fe3e4aa09629f0fa862fac0e46de84cb5b29ad61e841edbe21946f4"

LABELS = ["correct", "new_subject", "ambiguous"]


def buckets(cm):
    """四向拆分（cm: gold x pred）。"""
    return {
        "正则_regular": sum(cm[c][c] for c in LABELS),
        "错隐藏_ambiguous_to_correct": cm["ambiguous"]["correct"],
        "重复_correct_to_new_subject": cm["correct"]["new_subject"],
        "重复_ambiguous_to_new_subject": cm["ambiguous"]["new_subject"],
        "重复_total": cm["correct"]["new_subject"] + cm["ambiguous"]["new_subject"],
        "漏判_correct_to_ambiguous": cm["correct"]["ambiguous"],
        "其余_new_subject_to_ambiguous": cm["new_subject"]["ambiguous"],
        "其余_new_subject_to_correct": cm["new_subject"]["correct"],
    }


def prf(cm):
    out = {}
    for c in LABELS:
        tp = cm[c][c]
        fp = sum(cm[a][c] for a in LABELS if a != c)
        fn = sum(cm[c][b] for b in LABELS if b != c)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        out[c] = {"precision": round(p, 4), "recall": round(r, 4),
                  "f1": round(f, 4), "support": tp + fn}
    return out


def score(rows, field):
    cm = {a: {b: 0 for b in LABELS} for a in LABELS}
    for r in rows:
        cm[r["label"]][r[field]] += 1
    n = len(rows)
    acc = sum(cm[c][c] for c in LABELS) / n
    residual = [r["id"] for r in rows
                if r[field] != r["label"] and r["label"] == "correct"]
    return {
        "accuracy": round(acc, 4),
        "correct_n": sum(1 for r in rows if r[field] == r["label"]),
        "confusion": cm,
        "four_way": buckets(cm),
        "per_class": prf(cm),
        "oos_residual": {"count": len(residual), "ids": residual},
    }


def rg43_analog(rows):
    """RG43 类比项：裸值替换、两侧都判 ambiguous、旧句有锚点新句无主体。
    只按结构定位，不读原文语义，也不输出文本。"""
    ids = {r["id"] for r in rows}
    if "RG43" in ids:
        r = next(x for x in rows if x["id"] == "RG43")
        return {"id": "RG43", "match": "id_present",
                "v1_pred": r["_v1"], "v2_pred": r["_v2"], "gold": r["label"]}
    cand = []
    for r in rows:
        ev = r["_ev1"]
        if (ev.get("p") == 0 and ev.get("s") == 0
                and ev.get("old_subject") and not ev.get("new_subject")):
            cand.append({"id": r["id"], "v1_pred": r["_v1"], "v2_pred": r["_v2"],
                         "gold": r["label"]})
    return {"match": "structural", "candidates": cand}


def main():
    raw = open(GOLD, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != EXPECT_SHA:
        print("SHA256 MISMATCH: %s" % sha)
        sys.exit(2)

    rows = []
    with open(GOLD, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                obj = json.loads(line)
                # 只保留评分所需字段，原文不落盘、不打印
                rows.append({"id": obj["id"], "label": obj["label"],
                             "old": obj["old"], "new": obj["new"]})

    for r in rows:
        p1, ev1 = rb.predict(r["old"], r["new"])
        p2, ev2 = rb.predict_v2(r["old"], r["new"])
        r["_v1"], r["_v2"], r["_ev1"] = p1, p2, ev1

    s1 = score(rows, "_v1")
    s2 = score(rows, "_v2")

    result = {
        "meta": {
            "gold": GOLD,
            "sha256": sha,
            "n": len(rows),
            "labels_present": {k: sum(1 for r in rows if r["label"] == k) for k in LABELS},
            "scorer": "out/relation_heldout_score.py",
            "rules_untouched": True,
            "content_printed": False,
            "note": "只评分；old/new 原文不进入输出。arm_v1=relation_baseline.predict，"
                    "arm_v2=relation_baseline.predict_v2。",
        },
        "arm_v1_rule": s1,
        "arm_v2_rule": s2,
        "rg43_analog": rg43_analog(rows),
        "verdict": {
            "v1_residual_vs_threshold_12": "below" if s1["oos_residual"]["count"] < 12 else "at_or_above",
            "v2_residual_vs_threshold_12": "below" if s2["oos_residual"]["count"] < 12 else "at_or_above",
        },
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    for name, s in (("v1", s1), ("v2", s2)):
        print("%s acc=%.4f (%d/%d) residual=%d" % (
            name, s["accuracy"], s["correct_n"], len(rows),
            s["oos_residual"]["count"]))
        print("   four_way=%s" % json.dumps(s["four_way"], ensure_ascii=False))
        print("   residual_ids=%s" % s["oos_residual"]["ids"])


if __name__ == "__main__":
    main()