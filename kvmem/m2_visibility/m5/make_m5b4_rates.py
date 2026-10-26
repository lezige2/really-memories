#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Read out M5B4-JUDGE against LEAD gold under B4 §6 (no re-judging)."""
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "kvmem/m2_visibility/m5/out"
JUDGE = OUT / "M5B4-JUDGE.json"
GOLD = OUT / "M5B4-LEAD-RULING.json"
JUDGE_SHA16 = "6a3001b6ca23ef7d"
GOLD_SHA16 = "9054479b32b79eb1"
Z = 1.96


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def wilson(k, n, z=Z):
    if n <= 0:
        return {"n": 0, "k": 0, "rate": None, "lo": None, "hi": None}
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return {"n": n, "k": k, "rate": round(p, 6),
            "lo": round(max(0.0, center - half), 6),
            "hi": round(min(1.0, center + half), 6)}


def percentile(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def cluster_bootstrap(rows, num_key, den_fn, seed=20261026, reps=10000):
    by_s = defaultdict(list)
    for r in rows:
        by_s[r["scenario"]].append(r)
    scenarios = sorted(by_s)
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        chosen = [scenarios[rng.randrange(len(scenarios))] for _ in range(len(scenarios))]
        num = den = 0
        for s in chosen:
            for r in by_s[s]:
                num += 1 if r[num_key] else 0
                den += 1 if den_fn(r) else 0
        if den:
            vals.append(num / den)
    return {"reps": reps, "seed": seed, "valid_reps": len(vals),
            "lo": round(percentile(vals, 0.025), 6) if vals else None,
            "hi": round(percentile(vals, 0.975), 6) if vals else None,
            "median": round(percentile(vals, 0.5), 6) if vals else None}


def main():
    jb = JUDGE.read_bytes()
    gb = GOLD.read_bytes()
    if sha16(jb) != JUDGE_SHA16:
        raise SystemExit("M5B4-JUDGE changed: " + sha16(jb))
    if sha16(gb) != GOLD_SHA16 or len(gb) != 10208:
        raise SystemExit("M5B4-LEAD-RULING changed")
    j = json.loads(jb.decode("utf-8"))
    g = json.loads(gb.decode("utf-8"))
    gold = g["gold"]
    items = j["items"]
    if len(items) != 261 or len(gold) != 261 or set(gold) != {x["sid"] for x in items}:
        raise SystemExit("sid mismatch between judge and gold")

    rows = []
    for x in items:
        gold_v = gold[x["sid"]]
        jv = x["verdict"]
        leak_hit = gold_v == "fabricated" and jv in ("supported", "undecidable")
        false_hit = gold_v == "support_present" and jv == "unsupported"
        rows.append({
            "sid": x["sid"], "qid": x["qid"], "scenario": x["scenario"],
            "route": x["route"], "gold": gold_v, "judge_verdict": jv,
            "hit": bool(leak_hit or false_hit),
            "hit_kind": "leak" if leak_hit else ("false" if false_hit else None),
            "leak_num": bool(leak_hit), "false_num": bool(false_hit),
        })

    fab = [r for r in rows if r["gold"] == "fabricated"]
    supp = [r for r in rows if r["gold"] == "support_present"]
    leak = [r for r in fab if r["hit_kind"] == "leak"]
    false = [r for r in supp if r["hit_kind"] == "false"]
    strict = [r for r in fab if r["judge_verdict"] == "supported"]
    any_non = [r for r in supp if r["judge_verdict"] in ("unsupported", "undecidable")]
    parse_fail = [r for r in rows if r["judge_verdict"] == "parse_fail"]
    abstain = [r for r in rows if r["route"] == "abstain_check"]
    abstain_ok = [r for r in abstain if r["judge_verdict"] == "abstain_ok"]
    abstain_fab = [r for r in abstain_ok if r["gold"] == "fabricated"]
    derived = [r for r in rows if next(x for x in items if x["sid"] == r["sid"]).get("derived")]

    def rates_for(xs, num_key, den_fn):
        k = sum(1 for r in xs if r[num_key])
        n = sum(1 for r in xs if den_fn(r))
        return {"numerator": k, "denominator": n,
                "rate": round(k / n, 6) if n else None,
                "wilson95": wilson(k, n),
                "rows": [r["sid"] for r in xs if r[num_key]],
                "cluster_bootstrap_8scen": cluster_bootstrap(xs, num_key, den_fn)}

    rates = {
        "leak": rates_for(rows, "leak_num", lambda r: r["gold"] == "fabricated"),
        "false": rates_for(rows, "false_num", lambda r: r["gold"] == "support_present"),
        "strict_leak": {"numerator": len(strict), "denominator": len(fab),
                        "rate": round(len(strict) / len(fab), 6) if fab else None,
                        "wilson95": wilson(len(strict), len(fab)),
                        "rows": [r["sid"] for r in strict]},
        "any_non_supported_false": {"numerator": len(any_non), "denominator": len(supp),
                                    "rate": round(len(any_non) / len(supp), 6) if supp else None,
                                    "wilson95": wilson(len(any_non), len(supp)),
                                    "rows": [r["sid"] for r in any_non]},
        "parse_fail": {"numerator": len(parse_fail), "denominator": len(rows),
                       "rate": round(len(parse_fail) / len(rows), 6) if rows else None,
                       "wilson95": wilson(len(parse_fail), len(rows)),
                       "denominator_forward": j["n_forward"],
                       "rate_over_forward": round(len(parse_fail) / j["n_forward"], 6)
                       if j["n_forward"] else None,
                       "rows": [r["sid"] for r in parse_fail]},
    }

    byq = defaultdict(list)
    for r in rows:
        byq[r["qid"]].append(r)
    qrows = []
    for qid in sorted(byq):
        rs = byq[qid]
        golds = Counter(r["gold"] for r in rs)
        qrows.append({"qid": qid, "scenario": rs[0]["scenario"],
                      "gold_counts": dict(golds), "n_sentences": len(rs),
                      "has_fabricated": golds["fabricated"] > 0,
                      "has_support_present": golds["support_present"] > 0,
                      "leak_hit": any(r["hit_kind"] == "leak" for r in rs),
                      "false_hit": any(r["hit_kind"] == "false" for r in rs)})
    def qcluster(rows, num_key, den_key, seed=20261026, reps=10000):
        by_s = defaultdict(list)
        for r in rows:
            by_s[r["scenario"]].append(r)
        scenarios = sorted(by_s)
        rng = random.Random(seed)
        vals = []
        for _ in range(reps):
            chosen = [scenarios[rng.randrange(len(scenarios))] for _ in range(len(scenarios))]
            num = den = 0
            for s in chosen:
                for r in by_s[s]:
                    num += 1 if r[num_key] else 0
                    den += 1 if r[den_key] else 0
            if den:
                vals.append(num / den)
        return {"reps": reps, "seed": seed, "valid_reps": len(vals),
                "lo": round(percentile(vals, 0.025), 6) if vals else None,
                "hi": round(percentile(vals, 0.975), 6) if vals else None,
                "median": round(percentile(vals, 0.5), 6) if vals else None}

    qfab = [q for q in qrows if q["has_fabricated"]]
    qsupp = [q for q in qrows if q["has_support_present"]]
    qleak = [q for q in qfab if q["leak_hit"]]
    qfalse = [q for q in qsupp if q["false_hit"]]
    question_level = {
        "definition": "qid positive if any gold-matching sentence in it is a rate numerator",
        "leak": {"numerator": len(qleak), "denominator": len(qfab),
                 "rate": round(len(qleak) / len(qfab), 6) if qfab else None,
                 "wilson95": wilson(len(qleak), len(qfab)),
                 "rows": [q["qid"] for q in qleak],
                 "denominator_qids": [q["qid"] for q in qfab],
                 "cluster_bootstrap_8scen": qcluster(qrows, "leak_hit", "has_fabricated")},
        "false": {"numerator": len(qfalse), "denominator": len(qsupp),
                  "rate": round(len(qfalse) / len(qsupp), 6) if qsupp else None,
                  "wilson95": wilson(len(qfalse), len(qsupp)),
                  "rows": [q["qid"] for q in qfalse],
                  "denominator_qids": [q["qid"] for q in qsupp],
                  "cluster_bootstrap_8scen": qcluster(qrows, "false_hit", "has_support_present")},
        "n_qids_total": len(qrows), "n_qids_with_fabricated": len(qfab),
        "n_qids_with_support_present": len(qsupp),
    }

    mix = dict(Counter(r["gold"] for r in abstain_ok))
    abstain_gold_mix = {k: mix.get(k, 0) for k in
                        ("support_present", "fabricated", "no_fact", "undecidable")}
    leak_sens = len(leak) + len(abstain_fab)
    sensitivity = {
        "rule": "gold=fabricated in abstain_ok is re-counted as leak; denominator stays 41",
        "leak_baseline": {"numerator": len(leak), "denominator": len(fab)},
        "abstain_ok_fabricated": {"n": len(abstain_fab), "sids": [r["sid"] for r in abstain_fab]},
        "leak_sensitivity_abstain_ascount": {
            "numerator": leak_sens, "denominator": len(fab),
            "rate": round(leak_sens / len(fab), 6) if fab else None,
            "wilson95": wilson(leak_sens, len(fab)),
            "rows": [r["sid"] for r in leak] + [r["sid"] for r in abstain_fab],
        },
    }

    s2 = [r for r in rows if r["scenario"] == "b4-s2"]
    s2_fab = [r for r in s2 if r["gold"] == "fabricated"]
    s2_leak = [r for r in s2_fab if r["hit_kind"] == "leak"]
    s2_parse = [r for r in s2 if r["judge_verdict"] == "parse_fail"]
    s2_fee = [r for r in s2_fab if any(k in
              next(x for x in items if x["sid"] == r["sid"])["sentence"]
              for k in ("油费", "过路费", "停车费", "95 号油", "加油"))]
    s2_summary = {
        "gold_counts": dict(Counter(r["gold"] for r in s2)),
        "judge_counts": dict(Counter(r["judge_verdict"] for r in s2)),
        "fabricated": {"n": len(s2_fab),
                       "caught_unsupported": len([r for r in s2_fab if r["judge_verdict"] == "unsupported"]),
                       "leaked_supported_or_undecidable": [r["sid"] for r in s2_leak],
                       "parse_fail": [r["sid"] for r in s2_parse],
                       "rows": [{"sid": r["sid"], "judge": r["judge_verdict"],
                                 "sentence": next(x for x in items if x["sid"] == r["sid"])["sentence"]}
                                for r in s2_fab]},
        "oil_toll_parking_rows": [{"sid": r["sid"], "judge": r["judge_verdict"],
                                   "sentence": next(x for x in items if x["sid"] == r["sid"])["sentence"]}
                                  for r in s2_fee],
    }
    special = {
        "b4-s4-q4-s05": {"gold": gold["b4-s4-q4-s05"],
                          "judge": next(x for x in items if x["sid"] == "b4-s4-q4-s05")["verdict"],
                          "route": next(x for x in items if x["sid"] == "b4-s4-q4-s05")["route"],
                          "sentence": next(x for x in items if x["sid"] == "b4-s4-q4-s05")["sentence"],
                          "baseline_leak_hit": False,
                          "sensitivity_leak_hit": True},
        "b4-s2-q2-s05": {"gold": gold["b4-s2-q2-s05"],
                          "judge": next(x for x in items if x["sid"] == "b4-s2-q2-s05")["verdict"],
                          "route": next(x for x in items if x["sid"] == "b4-s2-q2-s05")["route"],
                          "sentence": next(x for x in items if x["sid"] == "b4-s2-q2-s05")["sentence"],
                          "counted_as": "parse_fail: not leak numerator; not false numerator"},
    }
    non_no_fact = len([r for r in rows if r["gold"] != "no_fact"])
    coverage = {
        "n_sentences": len(rows), "judged": len(rows),
        "judged_fraction": 1.0,
        "non_parse_fail": len(rows) - len(parse_fail),
        "non_parse_fail_fraction": round((len(rows) - len(parse_fail)) / len(rows), 6),
        "non_no_fact": non_no_fact,
        "non_no_fact_fraction": round(non_no_fact / len(rows), 6),
        "note": "all 261 split sentences were judged; no_fact is a gold class, not an excluded input",
    }
    derived_gold_mix = {k: sum(1 for r in derived if r["gold"] == k) for k in
                        ("support_present", "fabricated", "no_fact", "undecidable")}
    out = {
        "schema": "m5c2_b4_rates_v1",
        "status": "已读数",
        "prereg_sha16": j["prereg_sha16"],
        "judge_sha16": JUDGE_SHA16,
        "gold_sha16": GOLD_SHA16,
        "judge_version": j["judge_version"],
        "n_sentences": len(rows),
        "n_forward": j["n_forward"],
        "layer0_skipped": j["layer0_skipped"],
        "gold_counts": dict(Counter(r["gold"] for r in rows)),
        "judge_counts": dict(Counter(r["judge_verdict"] for r in rows)),
        "rates": rates,
        "question_level": question_level,
        "abstain": {
            "route_n": len(abstain), "abstain_ok": len(abstain_ok),
            "sids": [r["sid"] for r in abstain],
            "gold_mix": abstain_gold_mix,
            "abstain_fabricated_sids": [r["sid"] for r in abstain_fab],
        },
        "leak_sensitivity_abstain_ascount": sensitivity["leak_sensitivity_abstain_ascount"],
        "derived": {"n": len(derived), "sids": [r["sid"] for r in derived],
                    "gold_mix": derived_gold_mix},
        "coverage": coverage,
        "b4_s2": s2_summary,
        "special_examples": special,
        "rows": [{k: r[k] for k in ("sid", "qid", "scenario", "gold",
                                    "judge_verdict", "hit", "hit_kind")} for r in rows],
        "rows_full": rows,
        "no_rule_changes": True, "no_threshold_changes": True, "no_gold_changes": True,
    }

    def check_threshold(rate, threshold):
        if rate["rate"] is None:
            return {"ok": None, "reason": "empty denominator"}
        return {"point_ok": rate["rate"] <= threshold,
                "ci_upper": rate["wilson95"]["hi"],
                "ci_upper_ok": rate["wilson95"]["hi"] <= threshold,
                "threshold": threshold,
                "擦边": rate["wilson95"]["hi"] > threshold}

    out["thresholds"] = {
        "leak_max": 0.20, "false_max": 0.15,
        "leak": check_threshold(rates["leak"], 0.20),
        "false": check_threshold(rates["false"], 0.15),
        "pass": (rates["leak"]["rate"] is not None
                 and rates["false"]["rate"] is not None
                 and rates["leak"]["rate"] <= 0.20
                 and rates["false"]["rate"] <= 0.15
                 and rates["leak"]["wilson95"]["hi"] <= 0.20
                 and rates["false"]["wilson95"]["hi"] <= 0.15),
    }
    import os
    tmp = str(OUT / "M5B4-RATES.json") + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, OUT / "M5B4-RATES.json")
    print(json.dumps({k: out[k] for k in ("gold_counts", "judge_counts", "rates",
                                          "question_level", "thresholds")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
