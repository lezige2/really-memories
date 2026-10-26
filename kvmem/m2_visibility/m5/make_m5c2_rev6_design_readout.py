#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stage-A readout for rev6 B4 design set. No GPU, no model, no rule changes."""
import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "kvmem/m2_visibility/m5/out"
REV6 = OUT / "M5C2-REV6-B4DESIGN.json"
OLDJ = OUT / "M5B4-JUDGE.json"
GOLD = OUT / "M5B4-LEAD-RULING.json"
RATES = OUT / "M5B4-RATES.json"
ART = OUT / "M5C2-REV6-B4DESIGN-READOUT.json"
OLD_SHA = "6a3001b6ca23ef7d"
GOLD_SHA = "9054479b32b79eb1"
EXPECT_SIDS = 261


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def wilson(k, n, z=1.96):
    if not n:
        return {"n": 0, "k": 0, "rate": None, "lo": None, "hi": None}
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return {"n": n, "k": k, "rate": round(p, 6),
            "lo": round(max(0.0, c - h), 6), "hi": round(min(1.0, c + h), 6)}


def explicit_absent(ev):
    return any(t in (ev or "") for t in ("未提及", "未找到", "找不到"))


def verbatim(rec):
    q = qh = an = ah = 0
    sq = sa = 0
    for z in rec.get("items") or []:
        ev = str(z.get("evidence") or "")
        hit = bool(ev and ev in (rec.get("source_text") or ""))
        an += 1
        ah += int(hit)
        if not explicit_absent(ev):
            q += 1
            qh += int(hit)
    for z in rec.get("items") or []:
        pass
    return q, qh, an, ah


def all_verbatim_stats(records):
    q = qh = an = ah = sq = sa = 0
    for r in records:
        items = r.get("items") or []
        if not items:
            continue
        local_q = []
        for z in items:
            ev = str(z.get("evidence") or "")
            hit = bool(ev and ev in (r.get("source_text") or ""))
            an += 1
            ah += int(hit)
            if not explicit_absent(ev):
                q += 1; qh += int(hit); local_q.append(hit)
        if local_q:
            sq += 1
            if all(local_q):
                sa += 1
    return {
        "quote_bearing_items": q,
        "verbatim_hits": qh,
        "evidence_verbatim_rate": round(qh / q, 6) if q else None,
        "all_items": an,
        "all_items_verbatim_hits": ah,
        "all_items_verbatim_rate": round(ah / an, 6) if an else None,
        "sentences_with_quote_items": sq,
        "sentences_all_verbatim": sa,
        "sentence_all_verbatim_rate": round(sa / sq, 6) if sq else None,
        "definition": "quote-bearing = evidence non-empty and no explicit 未提及/未找到/找不到; exact substring in source_text",
    }


def reason_of(rec):
    hits = []
    for z in rec.get("items") or []:
        hits.extend(z.get("rule_hits") or [])
    if any((h.get("rule") in ("R4+", "R4") and h.get("reason") == "fabricated_evidence")
           for h in hits):
        return "fabricated_evidence"
    if any(h.get("rule") == "R2" for h in hits):
        return "negated"
    if any(h.get("rule") == "R3" for h in hits):
        return "absent_marker"
    if any(h.get("rule") == "R1" for h in hits):
        return "value_mismatch"
    return "other"


def r4_fabricated(rec):
    for z in rec.get("items") or []:
        for h in z.get("rule_hits") or []:
            if h.get("rule") in ("R4+", "R4") and h.get("reason") == "fabricated_evidence":
                return True
    return False


def policy_b_from_items(rec):
    v = rec.get("verdict")
    if rec.get("route") in ("abstain_check", "empty_source"):
        return v
    if v == "parse_fail":
        return "parse_fail"
    if rec.get("derived"):
        return "undecidable"
    items = rec.get("items") or []
    if not items:
        return "undecidable"
    n = sum(1 for z in items if z.get("absent"))
    return "unsupported" if n / len(items) >= 0.5 else "undecidable"


def summarize(records, gold):
    model = [r for r in records if r.get("route") == "model_extract"]
    false = [r for r in model if gold[r["sid"]] == "support_present" and r["verdict"] == "unsupported"]
    leak = [r for r in model if gold[r["sid"]] == "fabricated" and r["verdict"] in ("supported", "undecidable")]
    strict = [r for r in model if gold[r["sid"]] == "fabricated" and r["verdict"] == "supported"]
    fab = [r for r in records if gold[r["sid"]] == "fabricated"]
    supp = [r for r in records if gold[r["sid"]] == "support_present"]
    pf = [r for r in records if r["verdict"] == "parse_fail"]
    empty = [r for r in model if not (r.get("items") or [])]
    false_r4 = [r for r in false if r4_fabricated(r)]
    reasons = Counter(reason_of(r) for r in false)
    pb = Counter(policy_b_from_items(r) for r in records)
    pa = Counter(r.get("verdict") for r in records)
    return {
        "n_sentences": len(records),
        "n_forward": len(model),
        "parse_fail": {"n": len(pf), "rate": round(len(pf) / len(records), 6), "sids": [r["sid"] for r in pf]},
        "false_unsupported": {
            "n": len(false), "denominator": len(supp),
            "rate": round(len(false) / len(supp), 6) if supp else None,
            "wilson95": wilson(len(false), len(supp)),
            "sids": [r["sid"] for r in false],
            "r4_fabricated_evidence_n": len(false_r4),
            "r4_fabricated_evidence_sids": [r["sid"] for r in false_r4],
            "by_reason": {k: reasons.get(k, 0) for k in
                          ("fabricated_evidence", "negated", "absent_marker", "value_mismatch", "other")},
        },
        "leak": {"n": len(leak), "denominator": len(fab),
                 "rate": round(len(leak) / len(fab), 6) if fab else None,
                 "sids": [r["sid"] for r in leak]},
        "strict_leak": {"n": len(strict), "denominator": len(fab),
                        "sids": [r["sid"] for r in strict]},
        "empty_items_model": {"n": len(empty), "sids": [r["sid"] for r in empty]},
        "verdict_counts": dict(pa),
        "verdict_policyB_counts": dict(pb),
    }


def main():
    rb = REV6.read_bytes(); jb = OLDJ.read_bytes(); gb = GOLD.read_bytes()
    if sha16(jb) != OLD_SHA:
        raise SystemExit("old JUDGE changed")
    rv = json.loads(rb.decode("utf-8"))
    old = json.loads(jb.decode("utf-8"))
    gold = json.loads(gb.decode("utf-8"))["gold"]
    prior = json.loads(RATES.read_text(encoding="utf-8"))
    prior_gold = {r["sid"]: r["gold"] for r in prior["rows"]}
    gold_changed = any(prior_gold.get(s) != v for s, v in gold.items()) or set(gold) != set(prior_gold)
    if gold_changed:
        raise SystemExit("gold values changed versus M5B4-RATES snapshot")
    if rv.get("design_set") is not True or rv.get("not_acceptance") is not True:
        raise SystemExit("design flags missing")
    if len(rv["items"]) != EXPECT_SIDS or len(old["items"]) != EXPECT_SIDS:
        raise SystemExit("expected 261 items")
    if {x["sid"] for x in rv["items"]} != {x["sid"] for x in old["items"]}:
        raise SystemExit("sid mismatch")
    if rv.get("n_forward", 0) < 246:
        raise SystemExit("n_forward too low: %r" % rv.get("n_forward"))

    old_s = summarize(old["items"], gold)
    new_s = summarize(rv["items"], gold)
    old_v = all_verbatim_stats(old["items"])
    new_v = all_verbatim_stats(rv["items"])

    false_sids = old_s["false_unsupported"]["sids"]
    leak_sids = old_s["leak"]["sids"]
    by_new = {x["sid"]: x for x in rv["items"]}
    by_old = {x["sid"]: x for x in old["items"]}
    false_changes = []
    for sid in false_sids:
        o = by_old[sid]; n = by_new[sid]
        false_changes.append({
            "sid": sid, "old_verdict": o["verdict"], "new_verdict": n["verdict"],
            "old_reason": reason_of(o), "new_reason": reason_of(n),
            "old_r4_fabricated": r4_fabricated(o), "new_r4_fabricated": r4_fabricated(n),
            "old_items": [(z.get("item"), z.get("evidence"), z.get("absent")) for z in (o.get("items") or [])],
            "new_items": [(z.get("item"), z.get("evidence"), z.get("absent")) for z in (n.get("items") or [])],
            "new_raw_out": n.get("raw_out"),
        })
    leak_changes = []
    for sid in leak_sids:
        o = by_old[sid]; n = by_new[sid]
        leak_changes.append({
            "sid": sid, "old_verdict": o["verdict"], "new_verdict": n["verdict"],
            "old_items": [(z.get("item"), z.get("evidence")) for z in (o.get("items") or [])],
            "new_items": [(z.get("item"), z.get("evidence")) for z in (n.get("items") or [])],
        })
    new_leaks = [x for x in new_s["leak"]["sids"]]
    gate = {
        "parse_fail_ok": new_s["parse_fail"]["n"] <= 5,
        "r4_false_ok": new_s["false_unsupported"]["r4_fabricated_evidence_n"] <= 2,
        "leak_ok": new_s["leak"]["n"] <= 6,
        "thresholds": {"parse_fail_max": 5, "r4_false_max": 2, "leak_max": 6},
        "rev6_prompt_unusable": not (
            new_s["parse_fail"]["n"] <= 5
            and new_s["false_unsupported"]["r4_fabricated_evidence_n"] <= 2
            and new_s["leak"]["n"] <= 6),
    }
    out = {
        "schema": "m5c2_rev6_design_readout_v1",
        "design_set": True,
        "not_acceptance": True,
        "rev6_meta": {k: rv.get(k) for k in
                      ("judge_version", "rev6_prompt_sha16", "n_prompt_changes",
                       "n_sentences", "n_forward", "layer0_skipped", "parse_fail",
                       "design_set", "not_acceptance", "elapsed", "peak_vram",
                       "gate_exceptions", "signals_sent", "aborted")},
        "b4_judge_sha16": OLD_SHA,
        "gold_sha16_current": sha16(gb),
        "gold_sha16_original": GOLD_SHA,
        "gold_values_unchanged_vs_M5B4-RATES": not gold_changed,
        "gold_file_note": "lead audit_fix appended ruled 11->19; gold values compared and unchanged",
        "gate": gate,
        "evidence_verbatim_rate": {"old_rev5.1": old_v, "new_rev6": new_v,
                                   "delta_pp": round(100 * (new_v["evidence_verbatim_rate"]
                                                            - old_v["evidence_verbatim_rate"]), 2)
                                   if old_v["evidence_verbatim_rate"] is not None
                                   and new_v["evidence_verbatim_rate"] is not None else None},
        "old_rev5_1": old_s,
        "new_rev6": new_s,
        "false_examples_change": false_changes,
        "leak_examples_change": leak_changes,
        "new_leak_added": sorted(set(new_leaks) - set(leak_sids)),
        "new_leak_removed": sorted(set(leak_sids) - set(new_leaks)),
        "new_false_added": sorted(set(new_s["false_unsupported"]["sids"])
                                  - set(old_s["false_unsupported"]["sids"])),
        "new_false_removed": sorted(set(old_s["false_unsupported"]["sids"])
                                    - set(new_s["false_unsupported"]["sids"])),
        "no_gpu": True, "no_model_in_readout": True,
        "no_rule_changes": True, "no_threshold_changes": True, "no_gold_changes": True,
    }
    tmp = str(ART) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, ART)
    print(json.dumps({"gate": gate, "old": old_s, "new": new_s,
                      "verbatim": out["evidence_verbatim_rate"]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
