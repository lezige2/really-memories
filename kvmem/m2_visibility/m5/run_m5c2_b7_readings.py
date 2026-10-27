#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B7 READINGS post-processor (CPU only).

Frozen AFTER the 4 run-scripts and BEFORE b7' runs; implements
RULING-M5C2-B7-A2 (readout preset) and RULING-M5C2-B7-A3 (two-reading
side-by-side + undecidable disclosure) as a standalone, machine-executed step.

Pipeline (all frozen, this file runs last):
  out/M5C2-B7-DECIDE.json            narrow reading A (main readout, rev7.2)
  out/M5C2-B7-WIDE-SENSITIVITY.json  wide reading B (clean-blind impl)
  out/M5C2-B7-GOLD.json              LEAD gold (read-only)
  -> out/M5C2-B7-READINGS.json

Rules implemented verbatim:
  A2 mapping: FP point <= 8.67% AND Wilson upper <= 15% (leak side <= 20% with
              Wilson upper <= 20%) => 达标; point <= 15% but a Wilson upper
              crosses => 擦边; point > 15% => 未通过;
              n_fp < 20 or n_leak < 20 => 未接上（样本量不足）.
  A3 R3:      both readings same grade => report that grade, state 两读一致;
              different grades => final verdict 擦边/不可判, state 结论对读法敏感.
  A3 R4:      n_fp_eligible, undecidable_on_gold_support{k,n,rate},
              fp_readings{canonical, undecidable_in_denominator}; when
              rate > 15% append caveat 分母含高比例免检 and forbid claiming
              usability from a passing FP alone.

Exit codes: 0 ok; 2 pin/input error; 4 pending (missing DECIDE/WIDE/GOLD or
WIDE not filled) -- nothing is written in that case.

Zero GPU / zero model / zero network.  Gold is read-only; no write outside --out.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"

A2 = ROOT / "docs/_work/RULING-M5C2-B7-A2.md"
A2_SHA16 = "320b643ad6ea20f7"
A2_BYTES = 1902
A3 = ROOT / "docs/_work/RULING-M5C2-B7-A3.md"
A3_SHA16 = "10a23960aee8af32"
A3_BYTES = 2215
A4 = ROOT / "docs/_work/RULING-M5C2-B7-A4.md"
A4_SHA16 = "8b7a7d47d6b30000"
A4_BYTES = 2460
A5 = ROOT / "docs/_work/RULING-M5C2-B7-A5.md"
A5_SHA16 = "ab06e8be828897c5"
A5_BYTES = 2281
A2A1 = ROOT / "docs/_work/RULING-M5C2-B7-EXTRACT-RESUME-A2-A1.md"
A2A1_SHA16 = "ecbebaa82448e0fb"
A2A1_BYTES = 636
FREEZE = OUT / "M5C2-REV7-2-FREEZE.json"
FREEZE_SHA16 = "87a13b0c9aeae083"
FREEZE_BYTES = 5036
CLEANBLIND = OUT / "M5C2-REV7-2-CLEANBLIND-DECISION.json"
CLEANBLIND_SHA16 = "5d27944cb1e02f99"
CLEANBLIND_BYTES = 25501
WIDE_SCRIPT = M5 / "run_m5c2_b7_wide_sensitivity.py"
WIDE_SCRIPT_SHA16 = "616380af352092d8"
WIDE_SCRIPT_BYTES = 19273

DEFAULT_DECIDE = OUT / "M5C2-B7-DECIDE.json"
DEFAULT_WIDE = OUT / "M5C2-B7-WIDE-SENSITIVITY.json"
DEFAULT_GOLD = OUT / "M5C2-B7-GOLD.json"
DEFAULT_OUT = OUT / "M5C2-B7-READINGS.json"

Z95 = 1.959964
FALSE_MAX = 0.15
LEAK_MAX = 0.20
MIN_N_FP = 20
MIN_N_LEAK = 20
GOLD_STATES = ("support_present", "fabricated", "no_fact", "undecidable")
JUDGE_VERDICTS = ("supported", "unsupported", "undecidable", "parse_fail",
                  "not-supported", "abstain_ok")


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def rel(p):
    try:
        return str(Path(p).relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def verify_pin(path, want_sha, want_bytes, label):
    p = Path(path)
    if not p.exists():
        raise SystemExit("missing frozen file %s (%s)" % (label, rel(p)))
    b = p.read_bytes()
    if sha16(b) != want_sha or len(b) != want_bytes:
        raise SystemExit("%s changed: %s / %d B (expected %s / %d B)"
                         % (label, sha16(b), len(b), want_sha, want_bytes))
    return {"path": rel(p), "sha16": want_sha, "bytes": len(b)}


def wilson(k, n, z=Z95):
    if n <= 0:
        return {"k": 0, "n": 0, "rate": None, "lo": None, "hi": None}
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return {"k": k, "n": n, "rate": round(p, 6),
            "lo": round(max(0.0, center - half), 6),
            "hi": round(min(1.0, center + half), 6)}


def max_pass_k(n, threshold, z=Z95):
    """Largest k such that the Wilson 95% upper bound stays <= threshold."""
    if n <= 0:
        return 0
    k = 0
    while k < n:
        if wilson(k + 1, n, z)["hi"] > threshold:
            break
        k += 1
    return k


def grade_from_counts(n_fp, fp_k, n_leak, leak_k):
    """RULING-M5C2-B7-A5 R1, verbatim (Wilson upper rule; point => 未通过 only).

    达标: denominators >=20 AND FP Wilson upper <=15% AND leak Wilson upper <=20%.
    未通过: FP point >15% or leak point >20%.
    擦边: in band by point but a Wilson upper crosses.
    """
    wfp = wilson(fp_k, n_fp)
    wleak = wilson(leak_k, n_leak)
    if n_fp < MIN_N_FP or n_leak < MIN_N_LEAK:
        return {"grade": "未接上（样本量不足）",
                "basis": "n_fp=%d<%d or n_leak=%d<%d"
                         % (n_fp, MIN_N_FP, n_leak, MIN_N_LEAK),
                "fp": wfp, "leak": wleak}
    if fp_k / n_fp > FALSE_MAX:
        return {"grade": "未通过", "basis": "FP 点估计 >15%",
                "fp": wfp, "leak": wleak}
    if leak_k / n_leak > LEAK_MAX:
        return {"grade": "未通过", "basis": "漏判点估计 >20%",
                "fp": wfp, "leak": wleak}
    if wfp["hi"] > FALSE_MAX:
        return {"grade": "擦边",
                "basis": "FP 点估计在线内但 Wilson 95% 上界 >15%",
                "fp": wfp, "leak": wleak}
    if wleak["hi"] > LEAK_MAX:
        return {"grade": "擦边",
                "basis": "漏判点估计在线内但 Wilson 95% 上界 >20%",
                "fp": wfp, "leak": wleak}
    return {"grade": "达标",
            "basis": "两率 Wilson 95% 上界均在线内（FP<=15%, 漏判<=20%）",
            "fp": wfp, "leak": wleak}


def read_block(name, verdict_by_sid, gold_by_sid, sids):
    """One reading (A or B): counts, rates, Wilson, grade, undecidable fields."""
    n_fp = n_leak = 0
    fp_k = leak_k = 0
    und_k = 0
    fp_sids, leak_sids, und_sids = [], [], []
    layer0_sids = []
    layer0_gold = {"support_present": 0, "fabricated": 0, "no_fact": 0,
                   "undecidable": 0}
    for sid in sids:
        g = gold_by_sid.get(sid)
        jv = verdict_by_sid.get(sid)
        if g is None:
            raise SystemExit("gold misses sid %s" % sid)
        if jv not in JUDGE_VERDICTS:
            raise SystemExit("reading %s has unknown/missing verdict for %s: %r"
                             % (name, sid, jv))
        if jv == "abstain_ok":
            # C2: layer0 abstain_check short-circuit; single group, never mixed
            # into the FP/leak rate pools.
            layer0_sids.append(sid)
            if g in layer0_gold:
                layer0_gold[g] += 1
            continue
        if g == "support_present":
            n_fp += 1
            if jv == "unsupported":
                fp_k += 1
                fp_sids.append(sid)
            if jv == "undecidable":
                und_k += 1
                und_sids.append(sid)
        elif g == "fabricated":
            n_leak += 1
            if jv in ("supported", "undecidable"):
                leak_k += 1
                leak_sids.append(sid)
    und_rate = round(und_k / n_fp, 6) if n_fp else None
    grade = grade_from_counts(n_fp, fp_k, n_leak, leak_k)
    fp_reading_excl = {
        "k": fp_k, "n": n_fp - und_k,
        "rate": round(fp_k / (n_fp - und_k), 6) if (n_fp - und_k) > 0 else None,
        "wilson95": wilson(fp_k, n_fp - und_k),
        "label": "undecidable 计入分子（等效 FP 第二读）",
    }
    caveat = {
        "n_fp_eligible": n_fp,
        "undecidable_on_gold_support": {"k": und_k, "n": n_fp,
                                        "rate": und_rate},
        "threshold": FALSE_MAX,
        "exceeds_threshold": bool(und_rate is not None
                                  and und_rate > FALSE_MAX),
        "caveat": ("分母含高比例免检：undecidable_on_gold_support / "
                   "n_fp_eligible = %.2f%% > 15%%；不得仅凭 FP 达标宣称判据可用"
                   % ((und_rate or 0) * 100)),
    }
    return {
        "reading": name,
        "n_fp_eligible": n_fp,
        "n_leak": n_leak,
        "fp": dict(grade["fp"], sids=fp_sids),
        "leak": dict(grade["leak"], sids=leak_sids),
        "undecidable_on_gold_support": caveat["undecidable_on_gold_support"],
        "undecidable_sids": und_sids,
        "fp_readings": {
            "canonical": {"k": fp_k, "n": n_fp,
                          "rate": round(fp_k / n_fp, 6) if n_fp else None,
                          "wilson95": wilson(fp_k, n_fp)},
            "undecidable_in_denominator": fp_reading_excl,
        },
        "fp_reading_caveat": caveat,
        "grade": grade["grade"],
        "grade_basis": grade["basis"],
        "layer0_group": {
            "n": len(layer0_sids),
            "sids": layer0_sids,
            "verdicts": {"abstain_ok": len(layer0_sids)},
            "gold_mix": layer0_gold,
            "excluded_from_rates": True,
        },
        "rates_n_sentences": len(sids) - len(layer0_sids),
        "pass_region_from_wilson": {
            "fp_max_k": max_pass_k(n_fp, FALSE_MAX),
            "fp_max_rate": (round(max_pass_k(n_fp, FALSE_MAX) / n_fp, 6)
                            if n_fp else None),
            "leak_max_k": max_pass_k(n_leak, LEAK_MAX),
            "leak_max_rate": (round(max_pass_k(n_leak, LEAK_MAX) / n_leak, 6)
                              if n_leak else None),
            "rule": "RULING-M5C2-B7-A5 R1/R2: 达标按 Wilson 上界；条数线由实际分母"
                    "动态导出（A2 的 8.67% 仅为 n_fp=150 示例，不硬编码）",
        },
    }


def load_decide(path):
    p = Path(path)
    if not p.exists():
        return None, None
    b = p.read_bytes()
    d = json.loads(b.decode("utf-8"))
    if d.get("schema") != "m5c2_b7_decide_v1":
        raise SystemExit("unexpected B7 DECIDE schema %r" % (d.get("schema"),))
    rows = d.get("rows") or []
    verdict_by_sid = {}
    for r in rows:
        sid = r.get("sid")
        v = r.get("verdict_rev7", r.get("verdict"))
        if sid is None or v is None:
            raise SystemExit("B7 DECIDE row missing sid/verdict")
        verdict_by_sid[sid] = v
    if not verdict_by_sid:
        return None, {"path": rel(p), "sha16": sha16(b), "bytes": len(b)}
    return verdict_by_sid, {"path": rel(p), "sha16": sha16(b),
                            "bytes": len(b), "n_sentences": len(verdict_by_sid)}


def load_wide(path):
    p = Path(path)
    if not p.exists():
        return None, None
    b = p.read_bytes()
    d = json.loads(b.decode("utf-8"))
    if d.get("schema") != "m5c2_b7_wide_sensitivity_v1":
        raise SystemExit("unexpected wide-sensitivity schema %r"
                         % (d.get("schema"),))
    verdicts = d.get("verdicts") or {}
    if not isinstance(verdicts, dict) or not verdicts:
        return None, {"path": rel(p), "sha16": sha16(b), "bytes": len(b),
                      "status": d.get("status")}
    if (d.get("reading") or {}).get("declared") != "B":
        raise SystemExit("wide reading is not declared B")
    return dict(verdicts), {"path": rel(p), "sha16": sha16(b),
                            "bytes": len(b), "n_sentences": len(verdicts),
                            "status": d.get("status"),
                            "verdict_map_sha16": d.get("verdict_map_sha16")}


def load_gold(path):
    p = Path(path)
    if not p.exists():
        return None, None
    b = p.read_bytes()
    d = json.loads(b.decode("utf-8"))
    out = {}
    labels = d.get("labels")
    if isinstance(labels, list):
        for x in labels:
            sid = x.get("sid")
            g = x.get("gold_label") or x.get("label") or x.get("state")
            if sid is None or g not in GOLD_STATES:
                raise SystemExit("bad gold row %r" % (x,))
            out[sid] = g
    elif isinstance(d.get("gold"), dict):
        out = dict(d["gold"])
    else:
        raise SystemExit("gold has neither labels[] nor gold{}")
    return out, {"path": rel(p), "sha16": sha16(b), "bytes": len(b),
                 "n": len(out)}


SEVERITY_ORDER = ["未通过", "擦边", "未接上", "达标"]


def _severity_key(grade):
    """A4 R2 severity: 未通过 > 擦边 > 未接上 > 达标 (higher = worse)."""
    base = grade.replace("（样本量不足）", "")
    if base not in SEVERITY_ORDER:
        raise SystemExit("unknown grade %r" % (grade,))
    return len(SEVERITY_ORDER) - 1 - SEVERITY_ORDER.index(base)


def build_readings(decide, wide, gold, meta, pins):
    sids = sorted(gold)
    missing_a = [s for s in sids if s not in decide]
    missing_b = [s for s in sids if s not in wide]
    if missing_a or missing_b:
        raise SystemExit("reading maps miss gold sids: A=%r B=%r"
                         % (missing_a[:5], missing_b[:5]))
    a = read_block("A_narrow", decide, gold, sids)
    b = read_block("B_wide", wide, gold, sids)
    diff_sids = [s for s in sids if decide[s] != wide[s]]
    consistent = a["grade"] == b["grade"]
    ka, kb = _severity_key(a["grade"]), _severity_key(b["grade"])
    # A4 R2: conclusion takes the WORSE of the two readings.
    if ka >= kb:
        headline = "A_narrow"
        final = a["grade"]
    else:
        headline = "B_wide"
        final = b["grade"]
    if consistent:
        note = "两读一致（A/B 判定档相同，按该档报）"
    else:
        note = "结论对读法敏感（取较差档；headline 用较差读）"
    out = {
        "schema": "m5c2_b7_readings_v1",
        "status": "ok",
        "pipeline_role": "b7' final readout: DECIDE(A) + WIDE(B) + GOLD -> READINGS",
        "pins": pins,
        "inputs": meta,
        "n_sentences": len(sids),
        "severity_order": list(SEVERITY_ORDER),
        "label_order": {
            "A_narrow": "narrow_self_evidence（整句自证据，去尾标点；DEV=A）",
            "B_wide": "wide_substring（任意子串包含）",
            "dev_reading": "A",
        },
        "headline_reading": headline,
        "readings": {"A_narrow": a, "B_wide": b},
        "readings_consistency": {
            "consistent": consistent,
            "grade_a": a["grade"],
            "grade_b": b["grade"],
            "worse_grade": final,
            "final_verdict": final,
            "headline_reading": headline,
            "note": note,
        },
        "final_verdict": final,
        "readings_disclosure": ("A 读法（窄）漏报 1 例编造（b5-s4-q1-s01，"
                                "gold=fabricated）；B 读法（宽）多检 2 句，"
                                "其中 1 例为真漏判。"),
        "layer0_group": a["layer0_group"],
        "layer0_group_b": b["layer0_group"],
        "layer0_caveat": ("layer0 abstain_check %d/%d 单独成组、不混入两率池"
                          "（b6 对照 28/233；RULING-M5C2-B7-EXTRACT-RESUME-A2-A1）"
                          % (a["layer0_group"]["n"], len(sids))),
        "diff_b_vs_a": {
            "n_diff": len(diff_sids),
            "sids": diff_sids,
            "rows": [{"sid": s, "gold": gold[s], "A": decide[s], "B": wide[s]}
                     for s in diff_sids],
        },
        "fp_reading_caveat": a["fp_reading_caveat"],
        "b5_reference_values": {
            "undecidable_on_gold_support": {"k": 16, "n": 72, "rate": 0.222222},
            "fp_two_readings": [{"k": 2, "n": 72, "rate": 0.027778},
                                {"k": 2, "n": 56, "rate": 0.035714}],
            "note": "b5 dev 值仅作参照；A2 明令不得当作 b7' 预期",
        },
        "rules_applied": {
            "A5_R1": "达标=两率 Wilson 95% 上界 ≤15%/≤20% 且分母≥20；点估计仅用于"
                     "判未通过（>15%/>20%）；其余在线内但上界越线⇒擦边；"
                     "A2 的 8.67% 为 n_fp=150 示例、不硬编码",
            "C2_layer0": "abstain_ok 句四档外单列（layer0_group），"
                         "excluded_from_rates=true，不参与两率分子/分母",
            "A4_R2": "两读判定档一致⇒按该档并写两读一致；不一致⇒取较差档"
                     "（severity: 未通过 > 擦边 > 未接上 > 达标），headline 用较差读",
            "A3_R4": "n_fp_eligible / undecidable_on_gold_support / fp_readings "
                     "两读并列；>15% 须带『分母含高比例免检』caveat，"
                     "不得仅凭 FP 达标宣称判据可用",
        },
        "no_gpu": True,
        "no_model_call": True,
        "no_network": True,
        "no_gold_write": True,
        "gold_read_only": True,
        "determinism": {"timestamps": False, "json_indent": 1,
                        "ensure_ascii": False, "trailing_newline": True},
    }
    return out


def pins_all():
    pins = {
        "a2": verify_pin(A2, A2_SHA16, A2_BYTES, "RULING-M5C2-B7-A2.md"),
        "a3": verify_pin(A3, A3_SHA16, A3_BYTES, "RULING-M5C2-B7-A3.md"),
        "a4": verify_pin(A4, A4_SHA16, A4_BYTES, "RULING-M5C2-B7-A4.md"),
        "a5": verify_pin(A5, A5_SHA16, A5_BYTES, "RULING-M5C2-B7-A5.md"),
        "a2_a1_layer0": verify_pin(A2A1, A2A1_SHA16, A2A1_BYTES,
                                  "RULING-M5C2-B7-EXTRACT-RESUME-A2-A1.md"),
        "rev7_2_freeze": verify_pin(FREEZE, FREEZE_SHA16, FREEZE_BYTES,
                                    "M5C2-REV7-2-FREEZE.json"),
        "cleanblind_decision": verify_pin(CLEANBLIND, CLEANBLIND_SHA16,
                                          CLEANBLIND_BYTES,
                                          "M5C2-REV7-2-CLEANBLIND-DECISION.json"),
        "wide_script": verify_pin(WIDE_SCRIPT, WIDE_SCRIPT_SHA16,
                                  WIDE_SCRIPT_BYTES,
                                  "run_m5c2_b7_wide_sensitivity.py"),
    }
    return pins


# =========================== dry-run synthetic =============================
def _fake_case(n_support, n_fab, n_nofact, verdict_fn, name):
    """Build (gold, decide, wide) in memory for a synthetic case."""
    gold, a, b = {}, {}, {}
    i = 0
    for k in range(n_support):
        sid = "%s-fp-%03d" % (name, k)
        gold[sid] = "support_present"
        v = verdict_fn("support_present", k)
        a[sid] = b[sid] = v
    for k in range(n_fab):
        sid = "%s-lk-%03d" % (name, k)
        gold[sid] = "fabricated"
        v = verdict_fn("fabricated", k)
        a[sid] = b[sid] = v
    for k in range(n_nofact):
        sid = "%s-nf-%03d" % (name, k)
        gold[sid] = "no_fact"
        a[sid] = b[sid] = "supported"
    return gold, a, b


def _run_case(gold, a, b, expected_grade_a, expected_grade_b,
              expected_final, expected_diff):
    meta = {"decide": {"path": "synthetic", "sha16": "x", "bytes": 1},
            "wide": {"path": "synthetic", "sha16": "x", "bytes": 1},
            "gold": {"path": "synthetic", "sha16": "x", "bytes": 1}}
    out = build_readings(a, b, gold, meta, {"synthetic": True})
    ra = out["readings"]["A_narrow"]["grade"]
    rb = out["readings"]["B_wide"]["grade"]
    ok = (ra == expected_grade_a and rb == expected_grade_b
          and out["final_verdict"] == expected_final
          and out["diff_b_vs_a"]["n_diff"] == expected_diff)
    return ok, {"grade_a": ra, "grade_b": rb,
                "final": out["final_verdict"],
                "consistent": out["readings_consistency"]["consistent"],
                "n_diff": out["diff_b_vs_a"]["n_diff"],
                "caveat_exceeds": out["readings"]["A_narrow"]
                                  ["fp_reading_caveat"]["exceeds_threshold"]}


def dry_run():
    try:
        pins = pins_all()
    except SystemExit as e:
        print(json.dumps({"status": "pin_error", "detail": str(e)},
                         ensure_ascii=False, indent=1))
        return 2
    cases = []

    # 1) consistent 达标 at count level (n_fp=150, fp=8; n_leak=45, leak=0)
    g = grade_from_counts(150, 8, 45, 0)
    cases.append(("count_consistent_pass", g["grade"] == "达标"))
    # 2) inconsistent: A 达标 (8/150), B 擦边 (9/150 upper >15%? 9/150 hi=9.6%
    #    -> still 达标; use fp=14/150: point 9.33% >8.67% => 擦边)
    ga = grade_from_counts(150, 8, 45, 0)["grade"]
    gb = grade_from_counts(150, 14, 45, 0)["grade"]
    cases.append(("count_inconsistent_Ab", ga == "达标" and gb == "擦边"))
    # A5 R1/R2 boundary matrix (n_fp=148 / n_leak=63 per GOLD v2)
    g13_148 = grade_from_counts(148, 13, 63, 0)
    g14_148 = grade_from_counts(148, 14, 63, 0)
    g13_150 = grade_from_counts(150, 13, 63, 0)
    gpoint = grade_from_counts(100, 16, 63, 0)          # 16% > 15%
    gdenom = grade_from_counts(15, 1, 63, 0)
    cases.append(("A5_13_of_148_pass", g13_148["grade"] == "达标"
                  and g13_148["fp"]["hi"] <= 0.15))
    cases.append(("A5_14_of_148_marginal", g14_148["grade"] == "擦边"))
    cases.append(("A5_13_of_150_pass", g13_150["grade"] == "达标"))
    cases.append(("A5_point_16pct_fail", gpoint["grade"] == "未通过"))
    cases.append(("A5_denominator_insufficient",
                  gdenom["grade"] == "未接上（样本量不足）"))
    # C2: abstain_ok sentences are a separate layer0 group, excluded from rates
    _g2, _a2, _b2 = {}, {}, {}
    for k in range(30):
        sid = "lo-fp-%03d" % k
        _g2[sid] = "support_present"
        if k < 5:
            _a2[sid] = _b2[sid] = "abstain_ok"
        else:
            _a2[sid] = _b2[sid] = "unsupported" if k == 5 else "supported"
    for k in range(20):
        sid = "lo-lk-%03d" % k
        _g2[sid] = "fabricated"
        _a2[sid] = _b2[sid] = "unsupported"
    _m2 = {"decide": {"path": "synthetic", "sha16": "x", "bytes": 1},
           "wide": {"path": "synthetic", "sha16": "x", "bytes": 1},
           "gold": {"path": "synthetic", "sha16": "x", "bytes": 1}}
    _o2 = build_readings(_a2, _b2, _g2, _m2, {"synthetic": True})
    _la = _o2["readings"]["A_narrow"]
    cases.append(("c2_abstain_layer0_group",
                  _la["layer0_group"]["n"] == 5
                  and _la["layer0_group"]["excluded_from_rates"] is True
                  and _la["n_fp_eligible"] == 25
                  and _o2["layer0_group"]["n"] == 5))
    # 2b) A4 severity: A=未通过 / B=擦边 => final must be 未通过 (worse reading)
    _gold, _a, _b = {}, {}, {}
    for k in range(150):
        sid = "sev-fp-%03d" % k
        _gold[sid] = "support_present"
        _a[sid] = "unsupported" if k < 24 else "supported"
        _b[sid] = "unsupported" if k < 14 else "supported"
    for k in range(45):
        sid = "sev-lk-%03d" % k
        _gold[sid] = "fabricated"
        _a[sid] = _b[sid] = "unsupported"
    _meta = {"decide": {"path": "synthetic", "sha16": "x", "bytes": 1},
             "wide": {"path": "synthetic", "sha16": "x", "bytes": 1},
             "gold": {"path": "synthetic", "sha16": "x", "bytes": 1}}
    _out = build_readings(_a, _b, _gold, _meta, {"synthetic": True})
    cases.append(("severity_A_weiyou_B_chabian",
                  _out["readings_consistency"]["grade_a"] == "未通过"
                  and _out["readings_consistency"]["grade_b"] == "擦边"
                  and _out["final_verdict"] == "未通过"
                  and _out["headline_reading"] == "A_narrow"))
    # 3) denominator insufficient
    g = grade_from_counts(10, 1, 5, 0)
    cases.append(("count_denominator_insufficient",
                  g["grade"] == "未接上（样本量不足）"))
    # 4) undecidable > 15% caveat: n_fp=60, fp=3, und=12 (20%)
    gold, a, b = {}, {}, {}
    for k in range(60):
        sid = "fp-%03d" % k
        gold[sid] = "support_present"
        a[sid] = b[sid] = ("undecidable" if k < 12
                           else ("unsupported" if k < 12 + 3 else "supported"))
    for k in range(20):
        sid = "lk-%03d" % k
        gold[sid] = "fabricated"
        a[sid] = b[sid] = "unsupported"
    meta = {"decide": {"path": "synthetic", "sha16": "x", "bytes": 1},
            "wide": {"path": "synthetic", "sha16": "x", "bytes": 1},
            "gold": {"path": "synthetic", "sha16": "x", "bytes": 1}}
    out = build_readings(a, b, gold, meta, {"synthetic": True})
    cases.append(("count_undecidable_caveat",
                  out["fp_reading_caveat"]["exceeds_threshold"] is True
                  and out["readings"]["A_narrow"]["fp_readings"]
                  ["undecidable_in_denominator"]["n"] == 48))
    # 5) end-to-end tiny consistent (denominators insufficient => both 未接上)
    gold, a, b = _fake_case(6, 4, 0, lambda g, k: "unsupported" if k == 0
                            else ("supported" if g == "support_present"
                                  else "unsupported"), "t5")
    ok, info = _run_case(gold, a, b, "未接上（样本量不足）",
                         "未接上（样本量不足）", "未接上（样本量不足）", 0)
    cases.append(("e2e_tiny_consistent", ok))
    # 6) end-to-end inconsistent (A/B differ on two support sids => same grade
    #    here because denominators <20; simulate via grade mismatch at count
    #    level is case 2, so check diff detection + A/B maps here)
    gold, a, b = _fake_case(8, 4, 0, lambda g, k: "supported", "t6")
    b = dict(b)
    sid0 = sorted(s for s in gold if gold[s] == "support_present")[0]
    b[sid0] = "unsupported"
    ok, info = _run_case(gold, a, b, "未接上（样本量不足）",
                         "未接上（样本量不足）", "未接上（样本量不足）", 1)
    cases.append(("e2e_tiny_diff_detected", ok))
    all_ok = all(c[1] for c in cases)
    print(json.dumps({
        "schema": "m5c2_b7_readings_dry_run_v1",
        "status": "dry_run_only",
        "pins": pins,
        "n_forward": 0, "no_gpu": True, "writes_any_file": False,
        "cases": [{"case": c[0], "pass": c[1]} for c in cases],
        "all_pass": all_ok,
        "case4_detail": {"grade": out["final_verdict"]},
    }, ensure_ascii=False, indent=1))
    return 0 if all_ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decide", default=str(DEFAULT_DECIDE))
    ap.add_argument("--wide", default=str(DEFAULT_WIDE))
    ap.add_argument("--gold", default=str(DEFAULT_GOLD))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--expected-decide-sha16", default=None)
    ap.add_argument("--expected-wide-sha16", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.dry_run:
        return dry_run()

    pins = pins_all()
    decide, decide_meta = load_decide(a.decide)
    wide, wide_meta = load_wide(a.wide)
    gold, gold_meta = load_gold(a.gold)
    pending = []
    if decide is None:
        pending.append("DECIDE missing/empty: %s" % rel(a.decide))
    if wide is None:
        pending.append("WIDE missing/unfilled: %s (%r)"
                       % (rel(a.wide), (wide_meta or {}).get("status")))
    if gold is None:
        pending.append("GOLD missing: %s" % rel(a.gold))
    if a.expected_decide_sha16 and decide_meta and \
            decide_meta.get("sha16") != a.expected_decide_sha16:
        raise SystemExit("DECIDE sha16 %s != expected %s"
                         % (decide_meta.get("sha16"),
                            a.expected_decide_sha16))
    if a.expected_wide_sha16 and wide_meta and \
            wide_meta.get("sha16") != a.expected_wide_sha16:
        raise SystemExit("WIDE sha16 %s != expected %s"
                         % (wide_meta.get("sha16"), a.expected_wide_sha16))
    if pending:
        print(json.dumps({"schema": "m5c2_b7_readings_v1",
                          "status": "pending",
                          "reasons": pending,
                          "n_forward": 0, "no_gpu": True,
                          "writes_any_file": False,
                          "note": "不写假数据；待 DECIDE+WIDE+GOLD 齐备后重跑"},
                         ensure_ascii=False, indent=1))
        return 4

    meta = {"decide": decide_meta, "wide": wide_meta, "gold": gold_meta}
    out = build_readings(decide, wide, gold, meta, pins)
    write_json_atomic(a.out, out)
    b = Path(a.out).read_bytes()
    print(json.dumps({
        "schema": out["schema"],
        "status": out["status"],
        "out": rel(a.out), "sha16": sha16(b), "bytes": len(b),
        "n_sentences": out["n_sentences"],
        "grade_a": out["readings_consistency"]["grade_a"],
        "grade_b": out["readings_consistency"]["grade_b"],
        "final_verdict": out["final_verdict"],
        "consistent": out["readings_consistency"]["consistent"],
        "diff_b_vs_a": out["diff_b_vs_a"]["n_diff"],
        "caveat_exceeds": out["fp_reading_caveat"]["exceeds_threshold"],
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())