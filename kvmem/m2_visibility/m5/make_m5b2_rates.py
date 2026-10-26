#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build M5B2-RATES.json from the LEAD ruling, ADJ labels and frozen JUDGE.

Pure CPU.  Reads every input, never writes anything except the output file.
The 10 ruling overrides are applied on top of ADJ; the resulting gold counts
must equal the ruling; the judge is aligned by qid+sent_idx with exact text.
No accuracy/F1 is computed.  No model, no GPU, no input rewrite.
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
REVIEW = OUT / "M5B2-review-labels.json"
JUDGE = OUT / "M5B2-JUDGE.json"
PREREG = HERE.parents[2] / "docs" / "_work" / "PREREG-M5-B2.md"
TARGET = OUT / "M5B2-RATES.json"

EXPECT = {
    "ruling": ("65a2124b73f17d53", 4192),
    "sentences": ("6529e151568dc593", 78825),
    "adj": ("b08521482b88faa8", 50903),
    "review": ("1dfbb60436133b93", 50691),
    "judge": ("5deead7180dbb6a8", 229930),
}
GOLD_EXPECT = {"support_present": 71, "fabricated": 35, "no_fact": 385, "undecidable": 19}
PROHIBITED = [
    "不得写『新判据通过』",
    "不得写『(b) 通过』",
    "不得写『判据已验证』",
    "不得因本批结果回改 v2.3 规则",
]


def sha16(data):
    return hashlib.sha256(data).hexdigest()[:16]


def coord(p):
    b = Path(p).read_bytes()
    return {"file": Path(p).name, "sha16": sha16(b), "bytes": len(b)}


def pct(n, d):
    return "%.2f%%" % (100.0 * n / d) if d else "n/a"


def main():
    inputs = {}
    for name, (want_sha, want_bytes) in EXPECT.items():
        p = {"ruling": RULING, "sentences": SENTENCES, "adj": ADJ,
             "review": REVIEW, "judge": JUDGE}[name]
        b = p.read_bytes()
        got = (sha16(b), len(b))
        if got != (want_sha, want_bytes):
            raise SystemExit("input changed: %s %s != %s" % (name, got, (want_sha, want_bytes)))
        inputs[name] = {"file": p.name, "sha16": got[0], "bytes": got[1]}

    ruling = json.loads(RULING.read_text(encoding="utf-8"))
    sent = json.loads(SENTENCES.read_text(encoding="utf-8"))
    adj = json.loads(ADJ.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    judge = json.loads(JUDGE.read_text(encoding="utf-8"))

    # --- gold: ADJ as base, LEAD rulings override exactly 10 rows ---
    base = {x["sid"]: x["label"] for x in adj["labels"]}
    if len(base) != 510 or len(adj["labels"]) != 510:
        raise SystemExit("ADJ label count not 510")
    rulings = ruling["rulings"]
    if len(rulings) != 10:
        raise SystemExit("ruling count not 10")
    gold = dict(base)
    applied = []
    for sid, label in rulings.items():
        if sid not in base:
            raise SystemExit("ruling sid absent from ADJ: " + sid)
        applied.append({"sid": sid, "adj": base[sid], "ruled": label})
        gold[sid] = label
    gc = Counter(gold.values())
    if dict(gc) != GOLD_EXPECT:
        raise SystemExit("gold counts mismatch: %s != %s" % (dict(gc), GOLD_EXPECT))
    if len(gold) != 510:
        raise SystemExit("gold count not 510")

    # --- judge map by qid + sent_idx, exact text ---
    jmap = {}
    for q in judge["qa"]:
        for i, s in enumerate(q["sentences_nonempty"]):
            key = (q["qid"], i)
            if key in jmap:
                raise SystemExit("duplicate judge key: %r" % (key,))
            jmap[key] = s
    if len(jmap) != 510:
        raise SystemExit("judge sentence count not 510")

    rows = []
    mismatch = 0
    seen = set()
    for x in sent["sentences"]:
        sid = x["sid"]
        key = (x["qid"], x["sent_idx"])
        j = jmap.get(key)
        if j is None:
            mismatch += 1
            continue
        if j.get("text") != x.get("text"):
            mismatch += 1
            continue
        if sid not in gold:
            raise SystemExit("sentence sid absent from gold: " + sid)
        if sid in seen:
            raise SystemExit("duplicate sentence sid: " + sid)
        seen.add(sid)
        rows.append({
            "sid": sid, "scenario": x["scenario"], "qid": x["qid"],
            "sent_idx": x["sent_idx"], "text": x["text"],
            "gold": gold[sid], "judge_verdict": j.get("verdict"),
            "judge_reason": j.get("reason"), "uncovered": j.get("uncovered", []),
        })
    if len(rows) != 510 or mismatch != 0 or len(seen) != 510:
        raise SystemExit("alignment failed: rows=%d mismatch=%d seen=%d" % (len(rows), mismatch, len(seen)))

    # --- main rates: literal pre-registered comparisons ---
    leak = [r for r in rows if r["gold"] == "fabricated" and r["judge_verdict"] != "unsupported"]
    strict = [r for r in rows if r["gold"] == "fabricated" and r["judge_verdict"] == "supported"]
    false = [r for r in rows if r["gold"] == "support_present" and r["judge_verdict"] == "unsupported"]
    any_non = [r for r in rows if r["gold"] == "support_present" and r["judge_verdict"] != "supported"]
    expected = ruling["rates"]
    checks = {
        "leak": len(leak) == expected["leak"]["numerator"] and len(leak) == 14,
        "leak_denominator": gc["fabricated"] == 35,
        "false": len(false) == expected["false"]["numerator"] and len(false) == 10,
        "false_denominator": gc["support_present"] == 71,
        "strict_leak": len(strict) == expected["secondary_strict_leak"]["numerator"] == 0,
        "any_non_supported_false": len(any_non) == expected["secondary_any_non_supported_false"]["numerator"] == 22,
        "gold_counts": dict(gc) == GOLD_EXPECT,
        "alignment_mismatch_zero": mismatch == 0,
    }
    if not all(checks.values()):
        raise SystemExit("recomputation does not match ruling: %s" % checks)

    leak_all_no_fact = all(r["judge_verdict"] == "no_fact" for r in leak)
    leak_all_no_a = all(r["judge_reason"] == "no_a_component" for r in leak)
    if not (leak_all_no_fact and leak_all_no_a):
        raise SystemExit("leak mechanism is not 14/14 no_fact/no_a_component")

    # keep row payloads readable; text is already present in SENTENCES
    leak_rows = [{"sid": r["sid"], "qid": r["qid"], "sent_idx": r["sent_idx"],
                  "text": r["text"], "judge_verdict": r["judge_verdict"],
                  "judge_reason": r["judge_reason"]} for r in leak]
    false_rows = [{"sid": r["sid"], "qid": r["qid"], "sent_idx": r["sent_idx"],
                   "text": r["text"], "judge_verdict": r["judge_verdict"],
                   "uncovered": r["uncovered"]} for r in false]

    out = {
        "schema": "m5_b2_rates_v1",
        "batch": "b2",
        "adjudicator": "LEAD",
        "four_state": "未通过",
        "verdict_reason": "漏判率 40.00% > 20%",
        "judge_viability": "判据仍不成立（同机制 14/14）",
        "not_used_for_tuning": True,
        "no_gpu": True,
        "no_product_change": True,
        "prohibited_wording": PROHIBITED,
        "inputs": inputs,
        "prereg": {"path": str(PREREG.relative_to(HERE.parents[2])).replace("\\", "/"),
                   "sha16": sha16(PREREG.read_bytes()), "bytes": PREREG.stat().st_size},
        "rulings_applied": applied,
        "gold_counts": dict(gc),
        "ruling_gold_counts": ruling["gold_counts"],
        "alignment": {"key": "qid+sent_idx", "n": len(rows), "mismatch": mismatch,
                      "text_exact_equal": True},
        "judge_verdict_counts": dict(Counter(r["judge_verdict"] for r in rows)),
        "judge_mapping_note": "judge verdicts are used literally: only judge=unsupported counts as 'not fabricated' for leak; only judge=supported counts as supported for the secondary any_non_supported false metric. 'excluded' is a v2.3 question-echo verdict and is left as-is for literal comparisons.",
        "rates": {
            "leak": {"numerator": len(leak), "denominator": int(gc["fabricated"]),
                     "rate": round(len(leak) / gc["fabricated"], 4),
                     "rate_pct": pct(len(leak), gc["fabricated"]),
                     "threshold": expected["leak"]["threshold"], "pass": False,
                     "definition": "gold=fabricated 且 judge!=unsupported"},
            "false": {"numerator": len(false), "denominator": int(gc["support_present"]),
                      "rate": round(len(false) / gc["support_present"], 4),
                      "rate_pct": pct(len(false), gc["support_present"]),
                      "threshold": expected["false"]["threshold"], "pass": True,
                      "definition": "gold=support_present 且 judge=unsupported"},
            "secondary_strict_leak": {"numerator": len(strict), "denominator": int(gc["fabricated"]),
                                      "rate": 0.0, "rate_pct": "0.00%",
                                      "definition": "gold=fabricated 且 judge=supported"},
            "secondary_any_non_supported_false": {"numerator": len(any_non), "denominator": int(gc["support_present"]),
                                                  "rate": round(len(any_non) / gc["support_present"], 4),
                                                  "rate_pct": pct(len(any_non), gc["support_present"]),
                                                  "definition": "gold=support_present 且 judge!=supported"},
        },
        "failure_mechanism": {
            "leak_rows_all_same_reason": True,
            "reason": "no_a_component",
            "n": len(leak), "of_leak": len(leak), "share": 1.0,
            "all_no_fact": leak_all_no_fact,
            "explain": "v2.3 对无 A 级成分（无数字/无六类实体）的句子一律给 no_fact；散文型编造在结构上不可见。",
            "false_rows_mechanism": "10 条误判均为实体抽取越界/切分错位；逐条 uncovered 见 false_rows。",
        },
        "leak_rows": leak_rows,
        "false_rows": false_rows,
        "three_way_agreement": ruling["three_way_agreement"],
        "inter_labeler_agreement": ruling["inter_labeler_agreement"],
        "checks": checks,
        "dataset_scope_note": ruling["dataset_scope_note"],
        "rate_definition_source": "PREREG-M5-B2.md §3/§4",
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
        "gold_counts": dict(gc), "alignment_mismatch": mismatch,
        "leak": {"n": len(leak), "d": gc["fabricated"], "pct": pct(len(leak), gc["fabricated"])},
        "false": {"n": len(false), "d": gc["support_present"], "pct": pct(len(false), gc["support_present"])},
        "strict": len(strict), "any_non_supported_false": len(any_non),
        "leak_mechanism": {"no_fact": leak_all_no_fact, "no_a_component": leak_all_no_a, "n": len(leak)},
        "false_rows": len(false_rows),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())