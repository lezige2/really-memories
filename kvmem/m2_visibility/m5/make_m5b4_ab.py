#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Controlled A/B: frozen old rule judge v2.3 vs rev5.1 on the same B4 261 sentences."""
import hashlib
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
sys.path.insert(0, str(M5))
import m5_ground_v2_3 as OLD  # noqa: E402

JUDGE = OUT / "M5B4-JUDGE.json"
GOLD = OUT / "M5B4-LEAD-RULING.json"
SENT = OUT / "M5B4-SENTENCES.json"
RATES = OUT / "M5B4-RATES.json"
ART = OUT / "M5B4-AB-OLD-VS-NEW.json"
JUDGE_SHA = "6a3001b6ca23ef7d"
GOLD_SHA = "9054479b32b79eb1"
SENT_SHA = "c349ca5a93192aac"
OLD_SHA = "cc03e48c360ae0ee"
OLD_BYTES = 44209
OLD_VERSION = "v2.3"
NEW_VERSION = "rev5.1"
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


def rates(rows, verdict_key, definition):
    if definition == "b4":
        leak = [r for r in rows if r["gold"] == "fabricated"
                and r[verdict_key] in ("supported", "undecidable")]
    else:
        leak = [r for r in rows if r["gold"] == "fabricated"
                and r[verdict_key] not in ("unsupported", "old_unavailable")]
    false = [r for r in rows if r["gold"] == "support_present"
             and r[verdict_key] == "unsupported"]
    strict = [r for r in rows if r["gold"] == "fabricated"
              and r[verdict_key] == "supported"]
    if definition == "b4":
        any_non = [r for r in rows if r["gold"] == "support_present"
                   and r[verdict_key] in ("unsupported", "undecidable")]
    else:
        any_non = [r for r in rows if r["gold"] == "support_present"
                   and r[verdict_key] != "supported"]
    fab = [r for r in rows if r["gold"] == "fabricated"]
    supp = [r for r in rows if r["gold"] == "support_present"]
    parse = [r for r in rows if r[verdict_key] == "parse_fail"]
    return {
        "leak": {"numerator": len(leak), "denominator": len(fab),
                 "rate": round(len(leak) / len(fab), 6) if fab else None,
                 "wilson95": wilson(len(leak), len(fab)),
                 "rows": [r["sid"] for r in leak]},
        "false": {"numerator": len(false), "denominator": len(supp),
                  "rate": round(len(false) / len(supp), 6) if supp else None,
                  "wilson95": wilson(len(false), len(supp)),
                  "rows": [r["sid"] for r in false]},
        "strict_leak": {"numerator": len(strict), "denominator": len(fab),
                        "rate": round(len(strict) / len(fab), 6) if fab else None,
                        "wilson95": wilson(len(strict), len(fab)),
                        "rows": [r["sid"] for r in strict]},
        "any_non_supported_false": {"numerator": len(any_non), "denominator": len(supp),
                                    "rate": round(len(any_non) / len(supp), 6) if supp else None,
                                    "wilson95": wilson(len(any_non), len(supp)),
                                    "rows": [r["sid"] for r in any_non]},
        "parse_fail": {"numerator": len(parse), "denominator": len(rows),
                       "rate": round(len(parse) / len(rows), 6) if rows else None,
                       "rows": [r["sid"] for r in parse]},
    }


def qlevel(rows, verdict_key):
    byq = defaultdict(list)
    for r in rows:
        byq[r["qid"]].append(r)
    qr = []
    for qid in sorted(byq):
        rs = byq[qid]
        gc = Counter(r["gold"] for r in rs)
        qr.append({"qid": qid, "scenario": rs[0]["scenario"],
                   "gold_counts": dict(gc),
                   "has_fabricated": gc["fabricated"] > 0,
                   "has_support": gc["support_present"] > 0,
                   "leak_hit": any(r["gold"] == "fabricated"
                                   and r[verdict_key] in ("supported", "undecidable")
                                   for r in rs),
                   "false_hit": any(r["gold"] == "support_present"
                                    and r[verdict_key] == "unsupported" for r in rs)})
    qf = [q for q in qr if q["has_fabricated"]]
    qs = [q for q in qr if q["has_support"]]
    ql = [q for q in qf if q["leak_hit"]]
    qfa = [q for q in qs if q["false_hit"]]
    return {"leak": {"numerator": len(ql), "denominator": len(qf),
                     "rate": round(len(ql) / len(qf), 6) if qf else None,
                     "wilson95": wilson(len(ql), len(qf)),
                     "rows": [q["qid"] for q in ql]},
            "false": {"numerator": len(qfa), "denominator": len(qs),
                      "rate": round(len(qfa) / len(qs), 6) if qs else None,
                      "wilson95": wilson(len(qfa), len(qs)),
                      "rows": [q["qid"] for q in qfa]},
            "n_qids_with_fabricated": len(qf), "n_qids_with_support": len(qs),
            "qrows": qr}


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "p_exact": 1.0, "note": "no discordant pairs"}
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return {"b": b, "c": c, "p_exact": round(min(1.0, 2 * tail), 6),
            "method": "exact two-sided binomial on discordant pairs"}


def paired_scenario_bootstrap(rows, old_key, new_key, den_fn, seed=20261026, reps=10000):
    by_s = defaultdict(list)
    for r in rows:
        by_s[r["scenario"]].append(r)
    scenarios = sorted(by_s)
    rng = random.Random(seed)
    diff = []
    for _ in range(reps):
        chosen = [scenarios[rng.randrange(len(scenarios))] for _ in range(len(scenarios))]
        on = od = nn = nd = 0
        for s in chosen:
            for r in by_s[s]:
                if den_fn(r):
                    od += 1
                    nd += 1
                    on += 1 if r[old_key] else 0
                    nn += 1 if r[new_key] else 0
        if od:
            diff.append(nn / nd - on / od)
    diff.sort()
    def pct(q):
        if not diff:
            return None
        pos = (len(diff) - 1) * q
        lo = int(math.floor(pos)); hi = int(math.ceil(pos))
        return round(diff[lo] + (diff[hi] - diff[lo]) * (pos - lo), 6)
    return {"reps": reps, "seed": seed, "valid_reps": len(diff),
            "lo": pct(0.025), "hi": pct(0.975), "median": pct(0.5)}


def main():
    jb = JUDGE.read_bytes(); gb = GOLD.read_bytes(); sb = SENT.read_bytes()
    ob = (M5 / "m5_ground_v2_3.py").read_bytes()
    if sha16(jb) != JUDGE_SHA: raise SystemExit("JUDGE changed")
    if sha16(gb) != GOLD_SHA or len(gb) != 10208: raise SystemExit("GOLD changed")
    if sha16(sb) != SENT_SHA: raise SystemExit("SENT changed")
    if sha16(ob) != OLD_SHA or len(ob) != OLD_BYTES: raise SystemExit("OLD judge changed")
    j = json.loads(jb.decode("utf-8"))
    g = json.loads(gb.decode("utf-8"))["gold"]
    sents = json.loads(sb.decode("utf-8"))["sentences"]
    if len(sents) != 261 or len(j["items"]) != 261:
        raise SystemExit("expected 261")

    facts_cache = {}; fb_cache = {}
    q_order = defaultdict(list)
    for s in sents:
        q_order[s["qid"]].append(s["sid"])
    last_sid = {q: max(ids) for q, ids in q_order.items()}
    old_rows = []; unavailable = []
    for s in sents:
        src = s["source_text"]
        if src not in facts_cache:
            facts_cache[src] = OLD.source_facts([src])
            fb_cache[src] = OLD.source_b_units([src])
        try:
            r = OLD.analyze_sentence(s["text"], 0, facts_cache[src],
                                     fact_b_units=fb_cache[src],
                                     is_last=(s["sid"] == last_sid[s["qid"]]))
            ov = r["verdict"]; reason = r["reason"]
        except Exception as e:  # noqa: BLE001
            ov = "old_unavailable"; reason = repr(e)
            unavailable.append({"sid": s["sid"], "error": repr(e)})
        old_rows.append({"sid": s["sid"], "qid": s["qid"], "scenario": s["scenario"],
                         "gold": g[s["sid"]], "old_verdict": ov, "old_reason": reason})

    new_by = {x["sid"]: x for x in j["items"]}
    rows = []
    for o in old_rows:
        n = new_by[o["sid"]]; nv = n["verdict"]
        oh = (o["gold"] == "fabricated" and o["old_verdict"] in ("supported", "undecidable")) or \
             (o["gold"] == "support_present" and o["old_verdict"] == "unsupported")
        nh = (o["gold"] == "fabricated" and nv in ("supported", "undecidable")) or \
             (o["gold"] == "support_present" and nv == "unsupported")
        oleg = o["gold"] == "fabricated" and o["old_verdict"] not in ("unsupported", "old_unavailable")
        nleg = o["gold"] == "fabricated" and nv != "unsupported"
        rows.append({**o, "new_verdict": nv, "old_hit": bool(oh), "new_hit": bool(nh),
                     "old_hit_legacy": bool(oleg), "new_hit_legacy": bool(nleg),
                     "old_leak_num": bool(o["gold"] == "fabricated" and o["old_verdict"] in ("supported", "undecidable")),
                     "new_leak_num": bool(o["gold"] == "fabricated" and nv in ("supported", "undecidable")),
                     "old_false_num": bool(o["gold"] == "support_present" and o["old_verdict"] == "unsupported"),
                     "new_false_num": bool(o["gold"] == "support_present" and nv == "unsupported")})

    old_b4 = rates(rows, "old_verdict", "b4")
    new_b4 = rates(rows, "new_verdict", "b4")
    old_legacy = rates(rows, "old_verdict", "b2legacy")
    new_legacy = rates(rows, "new_verdict", "b2legacy")
    olq = qlevel(rows, "old_verdict")
    nwq = qlevel(rows, "new_verdict")

    def delta_block(o, n):
        on = o["numerator"]; od = o["denominator"]; nn = n["numerator"]; nd = n["denominator"]
        d = (nn / nd) - (on / od) if od and nd else None
        return {"old": f"{on}/{od}", "new": f"{nn}/{nd}",
                "old_rate": o["rate"], "new_rate": n["rate"],
                "delta_new_minus_old": round(d, 6) if d is not None else None,
                "delta_pp": round(100 * d, 2) if d is not None else None,
                "wilson_ci_overlap": bool(o["wilson95"]["lo"] <= n["wilson95"]["hi"]
                                          and n["wilson95"]["lo"] <= o["wilson95"]["hi"])
                if od and nd else None}

    leak_delta = delta_block(old_b4["leak"], new_b4["leak"])
    false_delta = delta_block(old_b4["false"], new_b4["false"])

    def paired(kind):
        oldk = "old_leak_num" if kind == "leak" else "old_false_num"
        newk = "new_leak_num" if kind == "leak" else "new_false_num"
        den = [r for r in rows if (r["gold"] == "fabricated" if kind == "leak"
                                     else r["gold"] == "support_present")]
        b = sum(1 for r in den if r[oldk] and not r[newk])
        c = sum(1 for r in den if not r[oldk] and r[newk])
        return {"denominator": len(den), "old_only_hit_b": b, "new_only_hit_c": c,
                "mcnemar": mcnemar_exact(b, c),
                "paired_scenario_bootstrap_delta_new_minus_old":
                    paired_scenario_bootstrap(rows, oldk, newk,
                                              lambda r, k=kind: r["gold"] == ("fabricated" if k == "leak" else "support_present"))}
    paired_leak = paired("leak")
    paired_false = paired("false")

    old_verdict_counts = Counter(r["old_verdict"] for r in rows)
    new_verdict_counts = Counter(r["new_verdict"] for r in rows)
    abstain_sids = set(json.loads(RATES.read_text(encoding="utf-8"))["abstain"]["sids"])
    old_abstain = Counter(r["old_verdict"] for r in rows if r["sid"] in abstain_sids)

    out = {
        "schema": "m5c2_b4_ab_old_vs_new_v1",
        "status": "controlled_ab_done",
        "controlled_ab": True,
        "same_sentences": 261,
        "same_gold": GOLD_SHA,
        "same_gold_file": "M5B4-LEAD-RULING.json",
        "old_judge": {"version": OLD_VERSION, "file": "m5_ground_v2_3.py",
                      "sha16": OLD_SHA, "bytes": OLD_BYTES,
                      "why": "M5B2-JUDGE.json was generated by make_m5b2_judge.py with m5_ground_v2_3.py; M5B2-RATES leak 14/35, false 10/71 = 40.00%/14.08%"},
        "new_judge": {"version": NEW_VERSION, "file": "run_m5c2_b4_judge.py",
                      "judge_sha16": JUDGE_SHA, "prompt_sha16": j.get("prompt_sha16")},
        "definition": {
            "leak": "gold=fabricated ∧ verdict ∈ {supported,undecidable}",
            "false": "gold=support_present ∧ verdict=unsupported",
            "strict_leak": "gold=fabricated ∧ verdict=supported",
            "any_non_supported_false": "gold=support_present ∧ verdict ∈ {unsupported,undecidable}",
            "parse_fail": "verdict=parse_fail / 261",
            "abstain": "old v2.3 has no abstain route; those sentences are judged normally"},
        "rates_b4_same_definition": {"old_v2.3": old_b4, "new_rev5.1": new_b4},
        "rates_legacy_b2_definition": {"old_v2.3": old_legacy, "new_rev5.1": new_legacy,
                                       "definition": "legacy leak = gold fabricated ∧ judge != unsupported; false same"},
        "question_level": {"definition": "qid positive if any matching sentence is a numerator",
                           "old_v2.3": {k: olq[k] for k in ("leak", "false")},
                           "new_rev5.1": {k: nwq[k] for k in ("leak", "false")}},
        "deltas": {"leak": leak_delta, "false": false_delta,
                   "note": "delta = new rev5.1 minus old v2.3; negative means new is lower"},
        "paired_tests": {"leak": paired_leak, "false": paired_false},
        "old_unavailable": {"n": len(unavailable), "rows": unavailable},
        "old_verdict_counts": dict(old_verdict_counts),
        "new_verdict_counts": dict(new_verdict_counts),
        "old_abstain_sentences": {"n": len(abstain_sids), "old_verdict_counts": dict(old_abstain)},
        "rows": [{k: r[k] for k in ("sid", "gold", "old_verdict", "new_verdict",
                                    "old_hit", "new_hit", "old_hit_legacy", "new_hit_legacy")}
                 for r in rows],
        "no_gpu": True, "no_model": True, "no_rule_changes": True,
        "no_threshold_changes": True, "no_gold_changes": True, "no_deletions": True,
    }
    tmp = str(ART) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, ART)
    print(json.dumps({
        "old": {k: out["rates_b4_same_definition"]["old_v2.3"][k] for k in ("leak", "false", "strict_leak", "parse_fail")},
        "new": {k: out["rates_b4_same_definition"]["new_rev5.1"][k] for k in ("leak", "false", "strict_leak", "parse_fail")},
        "deltas": out["deltas"], "paired": out["paired_tests"],
        "old_unavailable": len(unavailable), "old_counts": out["old_verdict_counts"]},
        ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
