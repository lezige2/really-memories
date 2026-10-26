#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""In-sample v2.4 re-read of the (b2) 510-sentence set.

Only one semantic relabel is applied: judge `no_fact` with `reason=no_a_component`
becomes `undecidable` (the v2.4 criterion change).  Gold labels and judge text
are reused; no input is rewritten.  Pure CPU, no model, no GPU.
"""
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
RULING = OUT / "M5B2-LEAD-RULING.json"
SENTENCES = OUT / "M5B2-SENTENCES.json"
ADJ = OUT / "M5B2-adj-labels.json"
JUDGE = OUT / "M5B2-JUDGE.json"
V23RATES = OUT / "M5B2-RATES.json"
SELFTEST = OUT / "_m5b3_selftest_v24.json"
V24 = HERE / "m5_ground_v2_4.py"
TARGET = OUT / "M5B3-v24-RATES.json"

EXPECT = {
    "ruling": ("65a2124b73f17d53", 4192),
    "sentences": ("6529e151568dc593", 78825),
    "adj": ("b08521482b88faa8", 50903),
    "judge": ("5deead7180dbb6a8", 229930),
    "v23rates": ("9ac66b6dfaf8f804", 11407),
}
GOLD_EXPECT = {"support_present": 71, "fabricated": 35, "no_fact": 385, "undecidable": 19}
PROHIBITED = [
    "不得写『v2.4 修复/改进/已修正』",
    "不得写『新判据通过』",
    "不得写『(b2) 通过』",
    "不得把持平读数说成改善",
    "不得据 (b2) 结果回改 v2.3/v2.4 规则",
]


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def coord(p):
    b = Path(p).read_bytes()
    return {"file": Path(p).name, "sha16": sha16(b), "bytes": len(b)}


def pct(n, d):
    return "%.2f%%" % (100.0 * n / d) if d else "n/a"


def main():
    inputs = {}
    blobs = {}
    for name, (want_sha, want_bytes) in EXPECT.items():
        p = {"ruling": RULING, "sentences": SENTENCES, "adj": ADJ,
             "judge": JUDGE, "v23rates": V23RATES}[name]
        b = p.read_bytes()
        if (sha16(b), len(b)) != (want_sha, want_bytes):
            raise SystemExit("input changed: %s" % name)
        inputs[name] = {"file": p.name, "sha16": sha16(b), "bytes": len(b)}
        blobs[name] = b
    ruling = json.loads(blobs["ruling"].decode("utf-8"))
    sent = json.loads(blobs["sentences"].decode("utf-8"))
    adj = json.loads(blobs["adj"].decode("utf-8"))
    judge = json.loads(blobs["judge"].decode("utf-8"))
    v23rates = json.loads(blobs["v23rates"].decode("utf-8"))
    selftest = json.loads(SELFTEST.read_text(encoding="utf-8"))
    if not selftest.get("all_pass") or len(selftest.get("selftest", [])) != 17:
        raise SystemExit("v2.4 selftest is not 17/17")

    # gold: ADJ base + LEAD rulings
    gold = {x["sid"]: x["label"] for x in adj["labels"]}
    if len(gold) != 510:
        raise SystemExit("ADJ count not 510")
    for sid, label in ruling["rulings"].items():
        if sid not in gold:
            raise SystemExit("ruling sid absent: " + sid)
        gold[sid] = label
    gc = Counter(gold.values())
    if dict(gc) != GOLD_EXPECT:
        raise SystemExit("gold mismatch: %s" % dict(gc))

    # judge map + sentence text alignment
    jmap = {}
    for q in judge["qa"]:
        for i, s in enumerate(q["sentences_nonempty"]):
            jmap[(q["qid"], i)] = s
    if len(jmap) != 510:
        raise SystemExit("judge count not 510")
    rows, mismatch = [], 0
    seen = set()
    for x in sent["sentences"]:
        key = (x["qid"], x["sent_idx"])
        j = jmap.get(key)
        if j is None or j.get("text") != x.get("text"):
            mismatch += 1
            continue
        sid = x["sid"]
        if sid not in gold or sid in seen:
            raise SystemExit("bad sid: " + sid)
        seen.add(sid)
        v23 = j.get("verdict")
        reason = j.get("reason")
        v24 = "undecidable" if (v23 == "no_fact" and reason == "no_a_component") else v23
        rows.append({
            "sid": sid, "qid": x["qid"], "sent_idx": x["sent_idx"], "text": x["text"],
            "gold": gold[sid], "v23_verdict": v23, "v24_verdict": v24,
            "reason": reason, "changed": v23 != v24,
        })
    if len(rows) != 510 or mismatch != 0 or len(seen) != 510:
        raise SystemExit("alignment failed: rows=%d mismatch=%d" % (len(rows), mismatch))

    def calc(verdict_key):
        leak = [r for r in rows if r["gold"] == "fabricated" and r[verdict_key] != "unsupported"]
        strict = [r for r in rows if r["gold"] == "fabricated" and r[verdict_key] == "supported"]
        false = [r for r in rows if r["gold"] == "support_present" and r[verdict_key] == "unsupported"]
        any_non = [r for r in rows if r["gold"] == "support_present" and r[verdict_key] != "supported"]
        return {
            "leak": {"numerator": len(leak), "denominator": gc["fabricated"],
                     "rate": round(len(leak) / gc["fabricated"], 4),
                     "rate_pct": pct(len(leak), gc["fabricated"]), "pass": False},
            "false": {"numerator": len(false), "denominator": gc["support_present"],
                      "rate": round(len(false) / gc["support_present"], 4),
                      "rate_pct": pct(len(false), gc["support_present"]), "pass": True},
            "secondary_strict_leak": {"numerator": len(strict), "denominator": gc["fabricated"],
                                      "rate": 0.0, "rate_pct": "0.00%"},
            "secondary_any_non_supported_false": {"numerator": len(any_non),
                                                  "denominator": gc["support_present"],
                                                  "rate": round(len(any_non) / gc["support_present"], 4),
                                                  "rate_pct": pct(len(any_non), gc["support_present"])},
        }

    r23, r24 = calc("v23_verdict"), calc("v24_verdict")
    changed = [r for r in rows if r["changed"]]
    if len(changed) != sum(1 for r in rows if r["v23_verdict"] == "no_fact" and r["reason"] == "no_a_component"):
        raise SystemExit("changed count mismatch")
    if r24["leak"]["numerator"] != 14 or r24["false"]["numerator"] != 10:
        raise SystemExit("v2.4 rates are not 14/35 and 10/71: %s" % r24)
    if r24["secondary_strict_leak"]["numerator"] != 0 or r24["secondary_any_non_supported_false"]["numerator"] != 22:
        raise SystemExit("secondary rates changed")
    if any(r24[k] != v23rates["rates"][k] for k in ("leak", "false")):
        # v23rates has extra threshold/definition keys; compare the shared numeric fields
        for k in ("leak", "false"):
            for f in ("numerator", "denominator", "rate"):
                if r24[k][f] != v23rates["rates"][k][f]:
                    raise SystemExit("v24 != v23 for %s.%s" % (k, f))
    if r23 != r24:
        raise SystemExit("v2.3/v2.4 recalculated rates differ: %s vs %s" % (r23, r24))

    leak_rows = [{"sid": r["sid"], "qid": r["qid"], "text": r["text"],
                  "v23_verdict": r["v23_verdict"], "v24_verdict": r["v24_verdict"],
                  "reason": r["reason"]} for r in rows
                 if r["gold"] == "fabricated" and r["v24_verdict"] != "unsupported"]
    false_rows = [{"sid": r["sid"], "qid": r["qid"], "text": r["text"],
                   "v24_verdict": r["v24_verdict"]} for r in rows
                  if r["gold"] == "support_present" and r["v24_verdict"] == "unsupported"]

    v24b = V24.read_bytes()
    stb = SELFTEST.read_bytes()
    out = {
        "schema": "m5_b3_v24_rates_v1",
        "batch": "b2",
        "in_sample_for_v2_4": True,
        "not_acceptance": True,
        "detection_capability_change": "none",
        "capability_boundary_confirmation": True,
        "no_new_gpu_batch": True,
        "no_gpu": True,
        "no_model": True,
        "no_product_change": True,
        "not_used_for_tuning": True,
        "four_state": "未通过",
        "verdict_reason": "漏判率 40.00% > 20%",
        "judge_viability": "判据仍不成立（同机制 14/14）",
        "prohibited_wording": PROHIBITED,
        "inputs": inputs,
        "prereg": {"path": "docs/_work/PREREG-M5-B3-v2.4.md",
                   "sha16": sha16(Path("docs/_work/PREREG-M5-B3-v2.4.md").read_bytes()),
                   "bytes": Path("docs/_work/PREREG-M5-B3-v2.4.md").stat().st_size},
        "v24_impl": {"file": V24.name, "sha16": sha16(v24b), "bytes": len(v24b),
                     "base_judge": "m5_ground_v2_3.py cc03e48c360ae0ee/44,209",
                     "functional_change": {"function": "analyze_sentence", "line": 373,
                                           "from": "no_fact / no_a_component",
                                           "to": "undecidable / no_a_component"},
                     "diff_hunks": 3, "functional_diff_hunks": 1, "test_only_diff_hunks": 2,
                     "diff_added_lines": 3, "diff_removed_lines": 3,
                     "functional_changed_lines": 1,
                     "selftest_changed_lines": 2,
                     "selftest_changes": [
                         {"function": "selftest", "line": 634,
                          "why": "branch5 test input changed to question-only because no-A assertive sentences are now undecidable; assertion itself unchanged"},
                         {"function": "selftest", "line": 650,
                          "why": "order_no_fact expectation no_fact -> undecidable"},
                     ]},
        "v24_selftest": {"file": SELFTEST.name, "sha16": sha16(stb), "bytes": len(stb),
                         "n": len(selftest["selftest"]), "all_pass": bool(selftest["all_pass"]),
                         "ids": [x["id"] for x in selftest["selftest"]]},
        "gold_counts": dict(gc),
        "alignment": {"key": "qid+sent_idx", "n": len(rows), "mismatch": mismatch,
                      "text_exact_equal": True},
        "v24_relabel": {"rule": "judge no_fact AND reason=no_a_component -> undecidable",
                        "changed_n": len(changed),
                        "changed_rows": [r["sid"] for r in changed]},
        "judge_verdict_counts": {
            "v23": dict(Counter(r["v23_verdict"] for r in rows)),
            "v24": dict(Counter(r["v24_verdict"] for r in rows)),
        },
        "rates": r24,
        "rates_v23": r23,
        "same_as_v23": r23 == r24,
        "leak_rows": leak_rows,
        "false_rows": false_rows,
        "failure_mechanism": {
            "leak_rows_all_same_reason": all(r["reason"] == "no_a_component" for r in leak_rows),
            "reason": "no_a_component",
            "all_v23_no_fact": all(r["v23_verdict"] == "no_fact" for r in leak_rows),
            "all_v24_undecidable": all(r["v24_verdict"] == "undecidable" for r in leak_rows),
            "n": len(leak_rows), "of_leak": len(leak_rows), "share": 1.0,
            "v24_maps_them_to": "undecidable",
            "capability_boundary": "v2.4 只把“判不了”显式标为 undecidable，并没有新增任何编造检测能力；漏判分子仍包含它们，故 14/35 持平。",
        },
        "three_way_agreement": ruling["three_way_agreement"],
        "inter_labeler_agreement": ruling["inter_labeler_agreement"],
        "dataset_scope_note": ruling["dataset_scope_note"],
        "no_accuracy_or_f1": True,
        "no_inputs_modified": True,
    }
    tmp = str(TARGET) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, TARGET)
    b = TARGET.read_bytes()
    print(json.dumps({
        "out": {"file": TARGET.name, "sha16": sha16(b), "bytes": len(b)},
        "v24": {"sha16": sha16(v24b), "bytes": len(v24b)},
        "selftest": {"n": len(selftest["selftest"]), "all_pass": selftest["all_pass"]},
        "changed_n": len(changed),
        "leak": r24["leak"], "false": r24["false"],
        "strict": r24["secondary_strict_leak"],
        "any_non_supported_false": r24["secondary_any_non_supported_false"],
        "same_as_v23": r23 == r24,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())