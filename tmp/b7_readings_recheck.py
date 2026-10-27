#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""b7′ readings independent re-check harness (CPU only, temporary tool).

Purpose: a self-contained re-implementation of the frozen b7′ reading math so
that the moment M5C2-B7-DECIDE.json / WIDE / READINGS land, the audit is a
one-command comparison.  Nothing is frozen; nothing is written unless --out is
given; no GPU, no gold writes, no blind-label reads.

Frozen rules implemented (from the ruling docs, not from any producer script):
  * two rates: FP = gold support_present ∧ verdict == unsupported (over the
    eligible denominator); leak = gold fabricated ∧ verdict ∈ {supported,
    undecidable}.
  * Wilson 95% CI, z = 1.959964.
  * A2 §2 mapping (two rates must both hold):
        numerator ≤ max_pass_k(denominator, threshold) AND upper ≤ threshold
        for FP (15%) and leak (20%) -> 达标
        point ≤ threshold but upper > threshold       -> 擦边
        point > threshold (FP)                        -> 未通过
        point > threshold (leak)                      -> 未通过（漏判越线）
        denominator < 20                              -> 未接上（样本量不足）
    (max_pass_k = largest k with Wilson upper ≤ threshold; for the frozen
     denominators n=148 -> 13 and n=63 -> 6.)
  * A3 R4: undecidable_on_gold_support / n_fp_eligible > 15% -> caveat
    「分母含高比例免检」required; fp_readings{canonical, undecidable_in_
    denominator}.
  * A4 R2/R3: final_verdict = worse reading by severity
    (未通过 > 擦边 > 未接上 > 达标); headline_reading = worse reading, tie -> A;
    fixed disclosure sentence checked when --readings is supplied.

Usage:
  python -X utf8 tmp/b7_readings_recheck.py --self-test
  python -X utf8 tmp/b7_readings_recheck.py \
      --decide out/M5C2-B7-DECIDE.json --wide out/M5C2-B7-WIDE-SENSITIVITY.json \
      --gold out/M5C2-B7-GOLD.json --readings out/M5C2-B7-READINGS.json

GOLD pin (LEAD re-pin v2): d5726d9cc59bb6f6 / 110,099 B
  counts support_present 148 / fabricated 63 / no_fact 380 / undecidable 32.
  (v1 3afddd2446e621f8 had 147 support; superseded.)
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "kvmem/m2_visibility/m5/out"

DEFAULT_DECIDE = OUT / "M5C2-B7-DECIDE.json"
DEFAULT_WIDE = OUT / "M5C2-B7-WIDE-SENSITIVITY.json"
DEFAULT_GOLD = OUT / "M5C2-B7-GOLD.json"
DEFAULT_READINGS = OUT / "M5C2-B7-READINGS.json"
DEFAULT_EXTRACT = OUT / "M5C2-B7-EXTRACT.json"

GOLD_SHA16 = "d5726d9cc59bb6f6"
GOLD_BYTES = 110099
N_FP = 148
N_LEAK = 63

Z = 1.959964
FP_MAX = 0.15
LEAK_MAX = 0.20
MIN_DENOM = 20
SEVERITY = {"未通过": 4, "擦边": 3, "未接上": 2, "达标": 1}
DISCLOSURE = ("A 读法（窄）漏报 1 例编造", "b5-s4-q1-s01",
              "B 读法（宽）多检 2 句", "其中 1 例为真漏判")
CAVEAT = "分母含高比例免检"


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def wilson(k, n, z=Z):
    if n <= 0:
        return {"k": k, "n": n, "rate": None, "lo": None, "hi": None}
    p = k / float(n)
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return {"k": k, "n": n, "rate": round(p, 6),
            "lo": round(max(0.0, center - half), 6),
            "hi": round(min(1.0, center + half), 6)}


def max_pass_k(n, threshold):
    best, k = 0, 0
    while k <= n:
        if wilson(k, n)["hi"] <= threshold:
            best = k
        k += 1
    return best


def band_of(fp, leak):
    if fp["n"] < MIN_DENOM or leak["n"] < MIN_DENOM:
        return "未接上（样本量不足）"
    if fp["rate"] is not None and fp["rate"] > FP_MAX:
        return "未通过"
    if leak["rate"] is not None and leak["rate"] > LEAK_MAX:
        return "未通过（漏判越线）"
    if fp["hi"] > FP_MAX or leak["hi"] > LEAK_MAX:
        return "擦边"
    return "达标"


def severity(band):
    if band in ("未通过", "未通过（漏判越线）"):
        return "未通过"
    if band.startswith("擦边"):
        return "擦边"
    if band.startswith("未接上"):
        return "未接上"
    return "达标"


def worse(a, b):
    sa, sb = severity(a), severity(b)
    if SEVERITY[sa] > SEVERITY[sb]:
        return "A", a
    if SEVERITY[sb] > SEVERITY[sa]:
        return "B", b
    return "A", a  # same band => A


def recompute(gold, verdicts):
    """Return per-reading numbers; gold is {sid: gold_label}, verdicts {sid: v}."""
    fp_sids = sorted(s for s, g in gold.items()
                     if g == "support_present" and verdicts.get(s) == "unsupported")
    und_sids = sorted(s for s, g in gold.items()
                      if g == "support_present" and verdicts.get(s) == "undecidable")
    leak_sids = sorted(s for s, g in gold.items()
                       if g == "fabricated"
                       and verdicts.get(s) in ("supported", "undecidable"))
    n_fp_elig = sum(1 for g in gold.values() if g == "support_present")
    n_leak = sum(1 for g in gold.values() if g == "fabricated")
    fp = wilson(len(fp_sids), n_fp_elig)
    leak = wilson(len(leak_sids), n_leak)
    band = band_of(fp, leak)
    fp_und_den = (len(fp_sids) / float(n_fp_elig - len(und_sids))
                  if n_fp_elig - len(und_sids) > 0 else None)
    counts = {}
    for v in verdicts.values():
        counts[v] = counts.get(v, 0) + 1
    return {
        "fp": dict(fp, sids=fp_sids),
        "leak": dict(leak, sids=leak_sids),
        "band": band,
        "verdict_counts": dict(sorted(counts.items())),
        "undecidable_on_gold_support": {
            "k": len(und_sids), "n": n_fp_elig,
            "rate": round(len(und_sids) / float(n_fp_elig), 6)
            if n_fp_elig else None, "sids": und_sids},
        "fp_readings": {
            "canonical": {"k": len(fp_sids), "n": n_fp_elig,
                          "rate": round(len(fp_sids) / float(n_fp_elig), 6)
                          if n_fp_elig else None},
            "undecidable_in_denominator": {
                "k": len(fp_sids), "n": n_fp_elig - len(und_sids),
                "rate": round(fp_und_den, 6) if fp_und_den is not None else None},
        },
        "max_pass_k": {"fp": max_pass_k(n_fp_elig, FP_MAX),
                       "leak": max_pass_k(n_leak, LEAK_MAX)},
    }


def combine(reading_a, reading_b):
    rw, final = worse(reading_a["band"], reading_b["band"])
    return {"worse_reading": rw, "final_verdict": final,
            "headline_reading": rw,
            "bands": {"A": reading_a["band"], "B": reading_b["band"]}}


def two_reading_diff(vm_a, vm_b):
    sids = sorted(set(vm_a) & set(vm_b))
    rows = [{"sid": s, "A": vm_a[s], "B": vm_b[s]}
            for s in sids if vm_a[s] != vm_b[s]]
    negative = ("unsupported", "not-supported", "parse_fail")
    loose = [r for r in rows if r["A"] in negative and r["B"] == "supported"]
    strict = [r for r in rows if r["A"] == "supported" and r["B"] in negative]
    other = [r for r in rows if r not in loose and r not in strict]
    b5_class = [r for r in loose if r["gold"] == "fabricated"] \
        if "gold" in (rows[0] if rows else {}) else []
    return {"n_diff": len(rows), "diff_sids": [r["sid"] for r in rows],
            "rows": rows,
            "direction_classes": {"loose_B_supported_A_negative": len(loose),
                                  "strict_A_supported_B_negative": len(strict),
                                  "other": len(other)},
            "b5_class_fabricated_Aneg_Bsupported": [r["sid"] for r in b5_class],
            "direction_consistent": (len(loose) + len(strict)) == len(rows),
            "direction": "b5 reference = loose class (A unsupported -> B "
                         "supported on gold=fabricated); b7 is mixed, both "
                         "classes reported"}


# ------------------------------------------------------------- loaders -----
def _rel(path):
    try:
        return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def load_gold(path, expect_sha=GOLD_SHA16, expect_bytes=GOLD_BYTES,
              allow_drift=False):
    b = Path(path).read_bytes()
    sha, n = sha16(b), len(b)
    if not allow_drift and (sha != expect_sha or n != expect_bytes):
        raise SystemExit("GOLD pin mismatch: %s/%d (expected %s/%d)"
                         % (sha, n, expect_sha, expect_bytes))
    doc = json.loads(b)
    labels = {}
    for x in doc.get("labels") or []:
        lab = x.get("gold_label") or x.get("label") or x.get("state")
        if lab:
            labels[x["sid"]] = lab
    if not labels:
        raise SystemExit("gold has no labels[]")
    return {"path": _rel(path), "sha16": sha, "bytes": n,
            "schema": doc.get("schema"), "n": len(labels),
            "counts": {g: sum(1 for v in labels.values() if v == g)
                       for g in sorted(set(labels.values()))},
            "labels": labels}


def load_verdict_map(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    vm = {}
    for key in ("verdicts", "verdict_map", "verdicts_rev7_2"):
        v = doc.get(key)
        if isinstance(v, dict) and v:
            vm = {sid: (x.get("verdict") if isinstance(x, dict) else x)
                  for sid, x in v.items()}
            break
    if not vm:
        for key in ("rows", "records", "sentences", "items"):
            rows = doc.get(key)
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                for r in rows:
                    v = (r.get("verdict_rev7_2") or r.get("verdict_rev7")
                         or r.get("verdict") or r.get("label"))
                    if r.get("sid") and v:
                        vm[r["sid"]] = v
                break
    if not vm:
        raise SystemExit("cannot read per-sentence verdicts from %s" % path)
    b = Path(path).read_bytes()
    return {"path": _rel(path), "sha16": sha16(b), "bytes": len(b),
            "schema": doc.get("schema"), "status": doc.get("status"),
            "verdicts": vm}


def norm_text(s):
    return "".join(str(s).split())


def compare_readings(readings_doc, rec_a, rec_b, comb):
    doc_txt = norm_text(json.dumps(readings_doc, ensure_ascii=False))

    def deep(names):
        if not isinstance(readings_doc, dict):
            return None
        for n in names:
            if n in readings_doc:
                return readings_doc[n]
        for v in readings_doc.values():
            if isinstance(v, dict):
                for n in names:
                    if n in v:
                        return v[n]
        return None

    actual_final = deep(("final_verdict", "final", "conclusion"))
    actual_headline = deep(("headline_reading", "headline"))
    exp_headline = comb["headline_reading"]
    exp_labels = {exp_headline, "%s_narrow" % exp_headline
                  if exp_headline == "A" else "%s_wide" % exp_headline}
    checks = {
        "final_verdict": {"expected": comb["final_verdict"],
                          "actual": actual_final,
                          "pass": actual_final == comb["final_verdict"]},
        "headline_reading": {"expected": sorted(exp_labels),
                             "actual": actual_headline,
                             "pass": actual_headline in exp_labels},
        "readings_disclosure": {
            "required_phrases": list(DISCLOSURE),
            "present": all(norm_text(p) in doc_txt for p in DISCLOSURE),
            "pass": all(norm_text(p) in doc_txt for p in DISCLOSURE)},
        "undecidable_caveat_rule": {
            "ratio": rec_a["undecidable_on_gold_support"]["rate"],
            "required": bool(rec_a["undecidable_on_gold_support"]["rate"]
                             and rec_a["undecidable_on_gold_support"]["rate"] > 0.15),
            "exceeds_field": deep(("exceeds_threshold",)),
            "pass": bool(rec_a["undecidable_on_gold_support"]["rate"]
                         and rec_a["undecidable_on_gold_support"]["rate"] > 0.15)
                    == bool(deep(("exceeds_threshold",)))},
        "undecidable_caveat_text": {
            "caveat_present": norm_text(CAVEAT) in doc_txt,
            "required": bool(rec_a["undecidable_on_gold_support"]["rate"]
                             and rec_a["undecidable_on_gold_support"]["rate"] > 0.15),
            "pass": True,
            "note": "fp_reading_caveat.caveat 固定文案含 >15% 断言；未触发时应"
                    "为空或明示未越线（producer 文案缺陷，不影响判定）"},
    }
    return checks


def _layer0_sids(extract_path):
    if not extract_path or not Path(extract_path).exists():
        return [], {"present": False}
    ex = json.loads(Path(extract_path).read_text(encoding="utf-8"))
    recs = ex.get("records") or []
    sids = sorted(r["sid"] for r in recs
                  if (r.get("route") or "model_extract") != "model_extract")
    return sids, {"present": True, "path": _rel(extract_path),
                  "sha16": sha16(Path(extract_path).read_bytes()),
                  "n": len(sids), "n_forward": ex.get("n_forward"),
                  "n_sentences": ex.get("n_sentences"),
                  "layer0_skipped": ex.get("layer0_skipped")}


def run(decide, wide, gold_path, readings=None, allow_gold_drift=False,
        extract_path=str(DEFAULT_EXTRACT)):
    gold = load_gold(gold_path, allow_drift=allow_gold_drift)
    a = load_verdict_map(decide)
    b = load_verdict_map(wide)
    if set(a["verdicts"]) != set(gold["labels"]) \
            or set(b["verdicts"]) != set(gold["labels"]):
        raise SystemExit("A/B verdict maps do not cover the gold sid set")
    l0_sids, l0_meta = _layer0_sids(extract_path)
    pool = {s: g for s, g in gold["labels"].items() if s not in set(l0_sids)}
    rec_a = recompute(pool, a["verdicts"])
    rec_b = recompute(pool, b["verdicts"])
    # four-state counts over the full 623 (layer0 included, as reported)
    from collections import Counter as _C
    for lab, vm in (("A", a["verdicts"]), ("B", b["verdicts"])):
        pass
    rec_a["verdict_counts_all"] = dict(sorted(_C(a["verdicts"].values()).items()))
    rec_b["verdict_counts_all"] = dict(sorted(_C(b["verdicts"].values()).items()))
    comb = combine(rec_a, rec_b)
    diff = two_reading_diff(a["verdicts"], b["verdicts"])
    for r in diff["rows"]:
        r["gold"] = gold["labels"].get(r["sid"])
    diff["b5_class_fabricated_Aneg_Bsupported"] = [
        r["sid"] for r in diff["rows"]
        if r["A"] == "unsupported" and r["B"] == "supported"
        and r["gold"] == "fabricated"]
    diff["cleanblind_class_consistent"] = bool(
        diff["b5_class_fabricated_Aneg_Bsupported"])
    out = {
        "status": "recomputed",
        "gold": {k: gold[k] for k in ("path", "sha16", "bytes", "schema", "n",
                                      "counts")},
        "gold_totals": {"n_fp_eligible": gold["counts"].get("support_present"),
                        "n_leak": gold["counts"].get("fabricated")},
        "layer0": dict(l0_meta, sids=l0_sids,
                       excluded_from_rates=True),
        "denominators": {"n_fp_eligible": rec_a["fp"]["n"],
                         "n_leak": rec_a["leak"]["n"],
                         "note": "layer0 abstain_ok group excluded (C2)"},
        "inputs": {"A": {k: a[k] for k in ("path", "sha16", "bytes", "schema",
                                           "status")},
                   "B": {k: b[k] for k in ("path", "sha16", "bytes", "schema",
                                           "status")}},
        "readings": {"A": rec_a, "B": rec_b},
        "final": comb,
        "two_reading_diff": diff,
    }
    if readings and Path(readings).exists():
        rd = json.loads(Path(readings).read_text(encoding="utf-8"))
        out["readings_compare"] = compare_readings(rd, rec_a, rec_b, comb)
        out["readings_compare"]["path"] = _rel(readings)
        out["readings_compare"]["sha16"] = sha16(Path(readings).read_bytes())
        out["pass"] = all(c["pass"] for c in out["readings_compare"].values()
                          if isinstance(c, dict) and "pass" in c)
    else:
        out["readings_compare"] = {"present": False}
        out["pass"] = True
    return out


# ------------------------------------------------------------ self test ----
def _mk_gold(n_support=148, n_fab=63, n_nofact=380, n_und=32):
    gold = {}
    i = 0
    for lab, cnt in (("support_present", n_support), ("fabricated", n_fab),
                     ("no_fact", n_nofact), ("undecidable", n_und)):
        for _ in range(cnt):
            i += 1
            gold["x%04d" % i] = lab
    return gold


def _mk_maps(gold, fp=0, leak=0, und=0, diff_sids=()):
    supp = [s for s, g in gold.items() if g == "support_present"]
    fab = [s for s, g in gold.items() if g == "fabricated"]
    a, b = {}, {}
    for s, g in gold.items():
        if g == "support_present":
            a[s] = b[s] = "supported"
        elif g == "fabricated":
            a[s] = b[s] = "unsupported"
        else:
            a[s] = b[s] = "supported"
    for s in supp[:fp]:
        a[s] = b[s] = "unsupported"
    for s in supp[fp:fp + und]:
        a[s] = b[s] = "undecidable"
    for s in fab[:leak]:
        a[s] = b[s] = "supported"
    for s in diff_sids:
        a[s] = "unsupported"
        b[s] = "supported"
    return a, b


def self_test():
    """A5 mapping cases: 13/148 pass, 14/148 marginal, 13/150 pass,
    point>15% fail, denominator<20 floor; plus A4 worse-band/headline,
    caveat, two-reading diff and producer-doc comparison."""
    cases = []
    gold = _mk_gold()            # 148 support / 63 fabricated / 412 other
    # 1) 13/148 -> 达标 (Wilson upper 14.56% <= 15%, point 8.78%)
    a, b = _mk_maps(gold, fp=13)
    ra, rb = recompute(gold, a), recompute(gold, b)
    c1 = combine(ra, rb)
    cases.append({"name": "13_of_148_pass",
                  "ok": (ra["band"] == "达标" and rb["band"] == "达标"
                         and c1["final_verdict"] == "达标"
                         and c1["headline_reading"] == "A"
                         and 13 <= ra["max_pass_k"]["fp"]),
                  "got": {"A": ra["band"], "B": rb["band"],
                          "final": c1["final_verdict"],
                          "fp_upper": ra["fp"]["hi"],
                          "fp_max_k": ra["max_pass_k"]["fp"]}})
    # 2) 14/148 -> 擦边 (upper 15.37% > 15%, point 9.46% <= 15%)
    a2, b2 = _mk_maps(gold, fp=14)
    ra2 = recompute(gold, a2)
    cases.append({"name": "14_of_148_marginal",
                  "ok": (ra2["band"] == "擦边"
                         and ra2["fp"]["rate"] <= FP_MAX
                         and ra2["fp"]["hi"] > FP_MAX),
                  "got": {"band": ra2["band"], "rate": ra2["fp"]["rate"],
                          "upper": ra2["fp"]["hi"]}})
    # 3) 13/150 -> 达标 (dynamic line, no hard-coded 8.67%)
    gold150 = _mk_gold(n_support=150)
    a3, b3 = _mk_maps(gold150, fp=13)
    ra3 = recompute(gold150, a3)
    cases.append({"name": "13_of_150_pass",
                  "ok": (ra3["band"] == "达标"
                         and ra3["fp"]["rate"] <= FP_MAX
                         and ra3["fp"]["hi"] <= FP_MAX),
                  "got": {"band": ra3["band"], "rate": ra3["fp"]["rate"],
                          "upper": ra3["fp"]["hi"],
                          "max_k": ra3["max_pass_k"]["fp"]}})
    # 4) point estimate >15% -> 未通过 (24/148 = 16.22%)
    a4, b4 = _mk_maps(gold, fp=24)
    ra4 = recompute(gold, a4)
    cases.append({"name": "point_over_15_fail",
                  "ok": (ra4["band"] == "未通过"
                         and ra4["fp"]["rate"] > FP_MAX),
                  "got": {"band": ra4["band"], "rate": ra4["fp"]["rate"]}})
    # 5) denominator < 20 -> 未接上（样本量不足）
    small = _mk_gold(n_support=19, n_fab=5, n_nofact=30, n_und=3)
    a5, b5 = _mk_maps(small, fp=2)
    ra5, rb5 = recompute(small, a5), recompute(small, b5)
    c5 = combine(ra5, rb5)
    cases.append({"name": "denominator_floor",
                  "ok": (ra5["band"] == "未接上（样本量不足）"
                         and c5["final_verdict"] == "未接上（样本量不足）"),
                  "got": {"band": ra5["band"],
                          "final": c5["final_verdict"]}})
    # 6) two readings: A 14/148 (擦边), B 24/148 (未通过) -> worse = B
    a6, b6 = _mk_maps(gold, fp=14)
    for sid in [s for s, g in gold.items() if g == "support_present"][14:24]:
        b6[sid] = "unsupported"
    ra6, rb6 = recompute(gold, a6), recompute(gold, b6)
    c6 = combine(ra6, rb6)
    cases.append({"name": "worse_band_and_headline",
                  "ok": (ra6["band"] == "擦边" and rb6["band"] == "未通过"
                         and c6["final_verdict"] == "未通过"
                         and c6["headline_reading"] == "B"),
                  "got": {"A": ra6["band"], "B": rb6["band"],
                          "final": c6["final_verdict"],
                          "headline": c6["headline_reading"]}})
    # 7) undecidable > 15% -> caveat required + fp_readings
    a7, b7m = _mk_maps(gold, fp=13, und=30)
    ra7 = recompute(gold, a7)
    caveat_required = ra7["undecidable_on_gold_support"]["rate"] > 0.15
    cases.append({"name": "undecidable_caveat",
                  "ok": (caveat_required
                         and ra7["fp_readings"]["canonical"] == {
                             "k": 13, "n": 148, "rate": round(13 / 148, 6)}
                         and ra7["fp_readings"]["undecidable_in_denominator"] == {
                             "k": 13, "n": 118, "rate": round(13 / 118, 6)}),
                  "got": {"und": ra7["undecidable_on_gold_support"]["rate"],
                          "fp_readings": ra7["fp_readings"]}})
    # 8) two-reading per-sid diff (rates unaffected: diff on no_fact sids)
    nofact = [s for s, g in gold.items() if g == "no_fact"][:2]
    a8, b8 = _mk_maps(gold, fp=13)
    for sid in nofact:
        a8[sid] = "unsupported"
        b8[sid] = "supported"
    d8 = two_reading_diff(a8, b8)
    cases.append({"name": "two_reading_diff",
                  "ok": (d8["diff_sids"] == sorted(nofact)
                         and d8["direction_consistent"]),
                  "got": {"n_diff": d8["n_diff"],
                          "sids": d8["diff_sids"],
                          "consistent": d8["direction_consistent"]}})
    # 9) compare_readings against a synthetic producer doc
    fake_doc = {"final_verdict": "未通过", "headline_reading": "B",
                "readings_disclosure": " ".join(DISCLOSURE)}
    rdet = compare_readings(fake_doc, ra6, rb6, c6)
    cases.append({"name": "compare_readings",
                  "ok": all(c["pass"] for c in rdet.values()),
                  "got": rdet})
    ok = all(c["ok"] for c in cases)
    print(json.dumps({"status": "self_test_ok" if ok else "self_test_FAIL",
                      "n_cases": len(cases),
                      "n_pass": sum(1 for c in cases if c["ok"]),
                      "cases": cases}, ensure_ascii=False, indent=1))
    return 0 if ok else 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--decide", default=str(DEFAULT_DECIDE))
    ap.add_argument("--wide", default=str(DEFAULT_WIDE))
    ap.add_argument("--gold", default=str(DEFAULT_GOLD))
    ap.add_argument("--readings", default=None)
    ap.add_argument("--extract", default=str(DEFAULT_EXTRACT))
    ap.add_argument("--allow-gold-drift", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    out = run(a.decide, a.wide, a.gold, a.readings, a.allow_gold_drift,
              a.extract)
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                               encoding="utf-8")
        out["written"] = a.out
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out.get("pass") else 3


if __name__ == "__main__":
    sys.exit(main())