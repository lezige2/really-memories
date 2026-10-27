#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""b7′ readings AUDIT SUPPLEMENT (independent; CPU only; temporary tool).

Supplements out/M5C2-B7-READINGS-AUDIT.json (e7ad14a9b576a442) with the four
items the advisor asked for.  IMPORTANT: this run does NOT read
out/M5C2-B7-READINGS.json at all.  The only inputs are:
  out/M5C2-B7-DECIDE.json          reading A (narrow) verdicts
  out/M5C2-B7-WIDE-SENSITIVITY.json reading B (wide) verdicts
  out/M5C2-B7-GOLD.json            d5726d9cc59bb6f6 / 110,099 B (LEAD v2)
  out/M5C2-B7-EXTRACT.json         layer0 route identification only
  docs/_work/RULING-M5C2-B7-A3-V2.md  75e7035855992dcf (sensitivity institution)

Items:
  1) per-reading FP/leak, Wilson 95% (z=1.959964), band  -- canonical pool
  2) denominators: layer0-excluded pool 147/62 vs total gold 148/63
  3) BOTH pools: excluded (147/62) and included (148/63), with bands
  4) the 11-sentence two-reading diff (sid + gold + A + B + direction)
  plus: A3-V2 consistency (two readings same band => no downgrade).

Output (only this file): out/M5C2-B7-READINGS-AUDIT-SUPPLEMENT.json
No GPU, no gold write, no blind-label read, no commit.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "kvmem/m2_visibility/m5/out"

GOLD = OUT / "M5C2-B7-GOLD.json"
GOLD_SHA16, GOLD_BYTES = "d5726d9cc59bb6f6", 110099
DECIDE = OUT / "M5C2-B7-DECIDE.json"
WIDE = OUT / "M5C2-B7-WIDE-SENSITIVITY.json"
EXTRACT = OUT / "M5C2-B7-EXTRACT.json"
A3V2 = ROOT / "docs/_work/RULING-M5C2-B7-A3-V2.md"
A3V2_SHA16, A3V2_BYTES = "75e7035855992dcf", 1361
ART = OUT / "M5C2-B7-READINGS-AUDIT-SUPPLEMENT.json"
SUPERSEDES = "e7ad14a9b576a442"

Z = 1.959964
FP_MAX, LEAK_MAX, MIN_DENOM = 0.15, 0.20, 20
SEVERITY = {"未通过": 4, "擦边": 3, "未接上": 2, "达标": 1}
NEG = ("unsupported", "not-supported", "parse_fail")


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    Path(tmp).replace(path)


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


def band_of(fp, leak):
    if fp["n"] < MIN_DENOM or leak["n"] < MIN_DENOM:
        return "未接上（样本量不足）"
    if fp["rate"] > FP_MAX:
        return "未通过"
    if leak["rate"] > LEAK_MAX:
        return "未通过（漏判越线）"
    if fp["hi"] > FP_MAX or leak["hi"] > LEAK_MAX:
        return "擦边"
    return "达标"


def severity(band):
    if band in ("未通过", "未通过（漏判越线）"):
        return "未通过"
    if band == "擦边":
        return "擦边"
    if band.startswith("未接上"):
        return "未接上"
    return "达标"


def load_gold():
    b = GOLD.read_bytes()
    if sha16(b) != GOLD_SHA16 or len(b) != GOLD_BYTES:
        raise SystemExit("GOLD pin mismatch")
    doc = json.loads(b)
    labels = {x["sid"]: (x.get("gold_label") or x.get("label"))
              for x in doc["labels"]}
    return labels, {"path": rel(GOLD), "sha16": sha16(b), "bytes": len(b),
                    "counts": doc.get("counts"), "n": len(labels)}


def load_verdicts(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    vm = {}
    v = doc.get("verdicts")
    if isinstance(v, dict) and v:
        vm = {k: (x.get("verdict") if isinstance(x, dict) else x)
              for k, x in v.items()}
    if not vm:
        rows = doc.get("rows") or doc.get("records") or doc.get("sentences")
        if isinstance(rows, list):
            for r in rows:
                val = (r.get("verdict_rev7_2") or r.get("verdict_rev7")
                       or r.get("verdict"))
                if r.get("sid") and val:
                    vm[r["sid"]] = val
    if not vm:
        raise SystemExit("no verdicts in %s" % path)
    return vm, {"path": rel(path),
                "sha16": sha16(Path(path).read_bytes()),
                "bytes": Path(path).stat().st_size,
                "schema": doc.get("schema")}


def layer0_sids():
    ex = json.loads(EXTRACT.read_text(encoding="utf-8"))
    sids = sorted(r["sid"] for r in (ex.get("records") or [])
                  if (r.get("route") or "model_extract") != "model_extract")
    return sids, {"path": rel(EXTRACT),
                  "sha16": sha16(EXTRACT.read_bytes()),
                  "bytes": EXTRACT.stat().st_size,
                  "n_forward": ex.get("n_forward"),
                  "n_sentences": ex.get("n_sentences"),
                  "layer0_skipped": ex.get("layer0_skipped")}


def rates(gold, vm, pool):
    g = {s: gold[s] for s in pool}
    fp = sorted(s for s in g if g[s] == "support_present"
                and vm.get(s) == "unsupported")
    leak = sorted(s for s in g if g[s] == "fabricated"
                  and vm.get(s) in ("supported", "undecidable"))
    und = sorted(s for s in g if g[s] == "support_present"
                 and vm.get(s) == "undecidable")
    n_fp = sum(1 for v in g.values() if v == "support_present")
    n_leak = sum(1 for v in g.values() if v == "fabricated")
    f, l = wilson(len(fp), n_fp), wilson(len(leak), n_leak)
    return {"fp": dict(f, sids=fp, max_pass_k=_max_pass_k(n_fp, FP_MAX)),
            "leak": dict(l, sids=leak, max_pass_k=_max_pass_k(n_leak, LEAK_MAX)),
            "n_fp": n_fp, "n_leak": n_leak,
            "undecidable_on_gold_support": {
                "k": len(und), "n": n_fp,
                "rate": round(len(und) / float(n_fp), 6) if n_fp else None},
            "fp_readings": {
                "canonical": {"k": len(fp), "n": n_fp,
                              "rate": round(len(fp) / float(n_fp), 6)
                              if n_fp else None},
                "undecidable_in_denominator": {
                    "k": len(fp), "n": n_fp - len(und),
                    "rate": round(len(fp) / float(n_fp - len(und)), 6)
                    if n_fp - len(und) > 0 else None}},
            "band": band_of(f, l)}


def _max_pass_k(n, thr):
    best, k = 0, 0
    while k <= n:
        if wilson(k, n)["hi"] <= thr:
            best = k
        k += 1
    return best


def main():
    gold, gold_meta = load_gold()
    va, a_meta = load_verdicts(DECIDE)
    vb, b_meta = load_verdicts(WIDE)
    l0, l0_meta = layer0_sids()
    if set(va) != set(gold) or set(vb) != set(gold):
        raise SystemExit("verdict maps do not cover the gold sid set")
    all_sids = sorted(gold)
    pool = [s for s in all_sids if s not in set(l0)]
    l0_mix = {}
    for s in l0:
        l0_mix[gold[s]] = l0_mix.get(gold[s], 0) + 1

    excl = {"A": rates(gold, va, pool), "B": rates(gold, vb, pool)}
    incl = {"A": rates(gold, va, all_sids), "B": rates(gold, vb, all_sids)}

    rows = []
    for s in all_sids:
        if va[s] != vb[s]:
            if va[s] in NEG and vb[s] == "supported":
                direction = "loose(B more permissive)"
            elif va[s] == "supported" and vb[s] in NEG:
                direction = "strict(B more strict)"
            else:
                direction = "other"
            rows.append({"sid": s, "gold": gold[s], "A": va[s], "B": vb[s],
                         "direction": direction,
                         "b5_class": (va[s] == "unsupported"
                                      and vb[s] == "supported"
                                      and gold[s] == "fabricated")})
    dir_counts = {}
    for r in rows:
        dir_counts[r["direction"]] = dir_counts.get(r["direction"], 0) + 1

    a3 = A3V2.read_bytes()
    a3_ok = sha16(a3) == A3V2_SHA16 and len(a3) == A3V2_BYTES
    a3_txt = a3.decode("utf-8")
    same_band = (excl["A"]["band"].split("（")[0]
                 == excl["B"]["band"].split("（")[0])
    worse = "A" if (not same_band and SEVERITY[severity(excl["A"]["band"])]
                    >= SEVERITY[severity(excl["B"]["band"])]) else (
        "B" if not same_band else "A")
    final = (excl[worse]["band"] if not same_band else excl["A"]["band"])
    a3_consistency = {
        "path": rel(A3V2), "sha16": sha16(a3), "bytes": len(a3),
        "pin_ok": a3_ok,
        "declares_same_band_headline_A": "两读同档" in a3_txt,
        "declares_final_marginal": "final_verdict=擦边" in a3_txt,
        "audit_same_band": bool(same_band),
        "audit_final_verdict": final,
        "audit_headline": "A_narrow" if same_band or worse == "A" else "B_wide",
        "no_downgrade": bool(same_band),
        "consistent": bool(a3_ok and same_band
                           and "两读同档" in a3_txt
                           and final == "擦边"),
        "note": "A3-V2 R1/R3: 两读同档 ⇒ headline=A_narrow、final=擦边、"
                "不触发降级；与本次复算一致",
    }

    # compare with the numbers the advisor quoted (2-dp checks)
    def pct(x):
        return None if x is None else round(x * 100, 2)

    quote_checks = [
        {"field": "excl.A.fp", "audit": pct(excl["A"]["fp"]["rate"]),
         "quoted": 14.97},
        {"field": "excl.A.fp.hi", "audit": pct(excl["A"]["fp"]["hi"]),
         "quoted": 21.62},
        {"field": "excl.A.leak", "audit": pct(excl["A"]["leak"]["rate"]),
         "quoted": 16.13},
        {"field": "excl.A.leak.hi", "audit": pct(excl["A"]["leak"]["hi"]),
         "quoted": 27.21},
        {"field": "excl.B.fp", "audit": pct(excl["B"]["fp"]["rate"]),
         "quoted": 14.29},
        {"field": "excl.B.fp.hi", "audit": pct(excl["B"]["fp"]["hi"]),
         "quoted": 20.85},
        {"field": "excl.B.leak", "audit": pct(excl["B"]["leak"]["rate"]),
         "quoted": 17.74},
        {"field": "excl.B.leak.hi", "audit": pct(excl["B"]["leak"]["hi"]),
         "quoted": 29.04},
        {"field": "incl.A.fp", "audit": pct(incl["A"]["fp"]["rate"]),
         "quoted": 14.86},
        {"field": "incl.A.fp.hi", "audit": pct(incl["A"]["fp"]["hi"]),
         "quoted": 21.48},
        {"field": "incl.A.leak", "audit": pct(incl["A"]["leak"]["rate"]),
         "quoted": 15.87},
        {"field": "incl.A.leak.hi", "audit": pct(incl["A"]["leak"]["hi"]),
         "quoted": 26.81},
        {"field": "incl.B.fp", "audit": pct(incl["B"]["fp"]["rate"]),
         "quoted": 14.19},
        {"field": "incl.B.fp.hi", "audit": pct(incl["B"]["fp"]["hi"]),
         "quoted": 20.72},
        {"field": "incl.B.leak", "audit": pct(incl["B"]["leak"]["rate"]),
         "quoted": 17.46},
        {"field": "incl.B.leak.hi", "audit": pct(incl["B"]["leak"]["hi"]),
         "quoted": 28.62},
    ]
    for c in quote_checks:
        c["equal"] = c["audit"] == c["quoted"]

    out = {
        "schema": "m5c2_b7_readings_audit_supplement_v1",
        "supersedes": SUPERSEDES,
        "role": "independent re-computation supplement (CPU only); READINGS "
                "artifact NOT read",
        "inputs": {"gold": gold_meta, "decide": a_meta, "wide": b_meta,
                   "layer0_source": l0_meta},
        "independence": {"readings_read": False,
                         "blind_labels_read": False, "gpu": False,
                         "sources": ["DECIDE", "WIDE", "GOLD", "EXTRACT",
                                     "A3-V2"]},
        "denominators": {
            "layer0": {"n": len(l0), "sids": l0, "gold_mix": l0_mix,
                       "excluded_from_rates": True},
            "canonical_pool": {"n_fp_eligible": excl["A"]["n_fp"],
                               "n_leak": excl["A"]["n_leak"],
                               "n_sentences": len(pool)},
            "total_gold": {"n_fp_eligible": incl["A"]["n_fp"],
                           "n_leak": incl["A"]["n_leak"],
                           "n_sentences": len(all_sids)},
            "note": "canonical = layer0 42 句排除; total = 全部 623 句",
        },
        "readings_excluded_pool": excl,
        "readings_included_pool": incl,
        "bands_both_versions": {
            "excluded": {"A": excl["A"]["band"], "B": excl["B"]["band"]},
            "included": {"A": incl["A"]["band"], "B": incl["B"]["band"]},
            "robust_to_layer0_choice": (
                severity(excl["A"]["band"]) == severity(incl["A"]["band"])
                and severity(excl["B"]["band"]) == severity(incl["B"]["band"])),
        },
        "two_reading_diff": {
            "n_diff": len(rows), "rows": rows,
            "direction_counts": dir_counts,
            "b5_class_sids": [r["sid"] for r in rows if r["b5_class"]],
            "cleanblind_class_consistent": any(r["b5_class"] for r in rows),
        },
        "quote_checks": {"checks": quote_checks,
                         "all_equal": all(c["equal"] for c in quote_checks)},
        "sensitivity": a3_consistency,
        "commands": ["python -X utf8 tmp/b7_readings_supplement.py"],
        "pass": bool(all(c["equal"] for c in quote_checks) and a3_consistency[
            "consistent"] and len(rows) == 11
            and excl["A"]["n_fp"] == 147 and excl["A"]["n_leak"] == 62),
        "notes": [
            "本件只读 DECIDE/WIDE/GOLD/EXTRACT/A3-V2，未读 READINGS。",
            "两版读数：(a) layer0 排除 147/62（canonical）；(b) layer0 纳入 "
            "148/63。两版两读均判擦边 ⇒ 档位对 layer0 取舍鲁棒。",
            "Wilson z=1.959964；A5 R1 判定（上界判达标/擦边、点估计判未通过）。",
        ],
    }
    write_json_atomic(ART, out)
    print(json.dumps({
        "status": "supplement_written",
        "artifact": rel(ART),
        "sha16": sha16(ART.read_bytes()),
        "bytes": ART.stat().st_size,
        "excluded": {"A": excl["A"]["band"], "B": excl["B"]["band"],
                     "n_fp": excl["A"]["n_fp"], "n_leak": excl["A"]["n_leak"]},
        "included": {"A": incl["A"]["band"], "B": incl["B"]["band"],
                     "n_fp": incl["A"]["n_fp"], "n_leak": incl["A"]["n_leak"]},
        "diff11_self_computed": len(rows) == 11,
        "direction_counts": dir_counts,
        "b5_class_sids": [r["sid"] for r in rows if r["b5_class"]],
        "quote_all_equal": all(c["equal"] for c in quote_checks),
        "a3v2_consistent": a3_consistency["consistent"],
        "pass": out["pass"],
    }, ensure_ascii=False, indent=1))
    return 0 if out["pass"] else 3


if __name__ == "__main__":
    sys.exit(main())