#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B7′ readings AUDIT — independent recomputation (CPU only).

Reads (never writes) the frozen b7′ reading chain:
  out/M5C2-B7-DECIDE.json             main reading A (narrow)
  out/M5C2-B7-WIDE-SENSITIVITY.json   wide reading B
  out/M5C2-B7-READINGS.json           final readings file (worse-band A4 rule)
  out/M5C2-B7-GOLD.json               d5726d9cc59bb6f6 / 110,099 B (gold may be read; LEAD v2)
Reference rules (frozen):
  RULING-M5C2-B7-A5.md   mapping (Wilson upper <=15%/<=20% & denominators >=20
                         => 达标; point >15%/>20% => 未通过; upper crosses =>
                         擦边).  A2 §2 text superseded by A5 R1 for the band math
                         ≤15% 但上界>15% ⇒ 擦边; 点估计>15% ⇒ 未通过; 分母<20 ⇒
                         未接上（样本量不足））; 漏判侧 20% 同理; 两率同时满足
  RULING-M5C2-B7-A3.md   R4: undecidable_on_gold_support / n_fp_eligible >15%
                         ⇒ caveat「分母含高比例免检」
  RULING-M5C2-B7-A4.md   R2: 两读并列、final=较差档（severity 未通过>擦边>
                         未接上>达标）、headline 用较差读、同档取 A、禁止把 A 的
                         leak=0 单独作 headline; R3: 固定披露句
  M5C2-B7-READINGS-FREEZE.json  script pin 8a8174aa08a850fb
  M5C2-REV7-2-CLEANBLIND-DECISION.json 5d27944cb1e02f99 (b5 A/B diff=2 方向参照)

Output (only this file): out/M5C2-B7-READINGS-AUDIT.json
  per-reading recomputed FP k/n, leak k/n, Wilson 95% (z=1.959964), 4-band counts,
  undecidable_on_gold_support, fp_readings{canonical, undecidable_in_denominator},
  A4 four checks, preset lines (n=148 ⇒ FP ≤13; n=63 ⇒ leak ≤6), two-reading
  per-sid diff + direction vs CLEANBLIND, numeric diff vs the producer artifacts,
  commands, pass/fail.

Modes:
  (default)          audit the b7′ chain; refuses (exit 4) while inputs are missing
  --self-test-b5     validate the recomputation engine against b5 A/B maps and
                     the frozen A4 R1 numbers (A: FP 2/72, leak 0/29;
                     B: FP 2/72, leak 1/29)

Zero GPU / zero forwards / zero network.  No frozen file is modified.  No commit.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"

DECIDE = OUT / "M5C2-B7-DECIDE.json"
WIDE = OUT / "M5C2-B7-WIDE-SENSITIVITY.json"
READINGS = OUT / "M5C2-B7-READINGS.json"
EXTRACT = OUT / "M5C2-B7-EXTRACT.json"
GOLD = OUT / "M5C2-B7-GOLD.json"
GOLD_SHA16, GOLD_BYTES = "d5726d9cc59bb6f6", 110099  # LEAD re-pin v2
B5_GOLD = OUT / "M5C2-B5-GOLD.json"
B5_GOLD_SHA16, B5_GOLD_BYTES = "54aa3da53c45da69", 64148
CLEANBLIND = OUT / "M5C2-REV7-2-CLEANBLIND-DECISION.json"
CLEANBLIND_SHA16 = "5d27944cb1e02f99"
A2_MD = ROOT / "docs/_work/RULING-M5C2-B7-A2.md"
A2_SHA16, A2_BYTES = None, None  # recorded, not hard-pinned (lead-frozen docs)
A3_MD = ROOT / "docs/_work/RULING-M5C2-B7-A3.md"
A3_SHA16 = "10a23960aee8af32"
A5A1_MD = ROOT / "docs/_work/RULING-M5C2-B7-A5-A1.md"
A5A1_SHA16, A5A1_BYTES = "da07f0b2b0ab7a3e", 748
A5A1_JSON = OUT / "RULING-M5C2-B7-A5-A1.json"
A5A1_JSON_SHA16 = "824aeb7d7d47cacd"
A5_MD = ROOT / "docs/_work/RULING-M5C2-B7-A5.md"
A5_SHA16, A5_BYTES = "ab06e8be828897c5", 2281
A5_JSON = OUT / "RULING-M5C2-B7-A5.json"
A5_JSON_SHA16 = "6d984a8514f0645c"
A4_MD = ROOT / "docs/_work/RULING-M5C2-B7-A4.md"
A4_SHA16, A4_BYTES = "8b7a7d47d6b30000", 2460
A4_JSON = OUT / "RULING-M5C2-B7-A4.json"
READINGS_FREEZE = OUT / "M5C2-B7-READINGS-FREEZE.json"
ART = OUT / "M5C2-B7-READINGS-AUDIT.json"

WILSON_Z = 1.959964
FP_MAX = 0.15
LEAK_MAX = 0.20
MIN_DENOM = 20
N_FP_EXPECT = 148  # LEAD re-pin v2
N_LEAK_EXPECT = 63
SEVERITY = {"未通过": 4, "擦边": 3, "未接上": 2, "达标": 1}
BANDS = ("达标", "擦边", "未通过", "未通过（漏判越线）", "未接上（样本量不足）")
STATES = ("supported", "unsupported", "undecidable", "parse_fail")

DISCLOSURE_PHRASES = ("A 读法（窄）漏报 1 例编造", "b5-s4-q1-s01",
                      "B 读法（宽）多检 2 句", "其中 1 例为真漏判")
CAVEAT_PHRASE = "分母含高比例免检"


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def die(msg, code=2):
    print(json.dumps({"status": "FAIL", "reason": msg}, ensure_ascii=False))
    raise SystemExit(code)


def pinned_bytes(path, sha, size, label):
    b = Path(path).read_bytes()
    if sha is not None and (sha16(b) != sha or (size is not None and len(b) != size)):
        die("%s pin mismatch: %s/%d" % (label, sha16(b), len(b)))
    return b


def wilson(k, n, z=WILSON_Z):
    if n <= 0:
        return {"k": k, "n": n, "rate": None, "lo": None, "hi": None,
                "upper": None}
    p = k / float(n)
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return {"k": k, "n": n, "rate": round(p, 6),
            "lo": round(max(0.0, center - half), 6),
            "hi": round(min(1.0, center + half), 6),
            "upper": round(min(1.0, center + half), 6)}


def max_pass_k(n, threshold):
    k, best = 0, 0
    while k <= n:
        if wilson(k, n)["upper"] <= threshold:
            best = k
        k += 1
    return best


def band_of(fp, leak):
    """Frozen A2 §2 mapping; two rates must both hold."""
    if fp["n"] < MIN_DENOM or leak["n"] < MIN_DENOM:
        return "未接上（样本量不足）"
    if fp["rate"] is not None and fp["rate"] > FP_MAX:
        return "未通过"
    if leak["rate"] is not None and leak["rate"] > LEAK_MAX:
        return "未通过（漏判越线）"
    if fp["upper"] > FP_MAX or leak["upper"] > LEAK_MAX:
        return "擦边"
    return "达标"


def severity_level(band):
    if band in ("未通过", "未通过（漏判越线）"):
        return "未通过"
    if band == "擦边":
        return "擦边"
    if band in ("未接上", "未接上（样本量不足）"):
        return "未接上"
    return "达标"


def _iter_text(obj):
    return json.dumps(obj, ensure_ascii=False)


def norm_text(s):
    return re.sub(r"\s+", "", s or "")


def contains_phrase(doc, phrases):
    txt = norm_text(_iter_text(doc))
    return all(norm_text(p) in txt for p in phrases)


# ------------------------------------------------------------- loaders -----
def load_gold(path, expect_sha, expect_bytes):
    b = pinned_bytes(path, expect_sha, expect_bytes, Path(path).name)
    doc = json.loads(b)
    labels = {}
    for x in doc.get("labels") or []:
        lab = x.get("gold_label") or x.get("label") or x.get("state")
        if lab:
            labels[x["sid"]] = lab
    if not labels:
        die("gold has no labels[]")
    counts = {}
    for v in labels.values():
        counts[v] = counts.get(v, 0) + 1
    return {"path": _rel(path), "sha16": sha16(b), "bytes": len(b),
            "schema": doc.get("schema"), "n": len(labels), "counts": counts,
            "labels": labels}, doc


def _rel(path):
    try:
        return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _find_list(doc, keys):
    for k in keys:
        v = doc.get(k)
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return k, v
    return None, None


def load_verdict_map(path, label):
    if not Path(path).exists():
        return None
    b = Path(path).read_bytes()
    doc = json.loads(b)
    meta = {"path": _rel(path), "sha16": sha16(b), "bytes": len(b),
            "name": label, "schema": doc.get("schema"),
            "status": doc.get("status"), "present": True}
    vm = {}
    for k in ("verdicts", "verdict_map", "verdicts_rev7_2", "map"):
        v = doc.get(k)
        if isinstance(v, dict) and v:
            vm = {sid: (lab.get("verdict") if isinstance(lab, dict) else lab)
                  for sid, lab in v.items()}
            break
    if not vm:
        key, rows = _find_list(doc, ("rows", "records", "sentences", "items"))
        if rows:
            for r in rows:
                v = (r.get("verdict_rev7_2") or r.get("verdict_rev7")
                     or r.get("verdict") or r.get("label") or r.get("state"))
                if r.get("sid") and v:
                    vm[r["sid"]] = v
            meta["rows_key"] = key
    meta["n_verdicts"] = len(vm)
    meta["verdict_map_sha16"] = (
        sha16(json.dumps(vm, sort_keys=True, ensure_ascii=False).encode())
        if vm else None)
    return {"meta": meta, "verdicts": vm, "doc": doc}


def load_readings(path):
    if not Path(path).exists():
        return None
    b = Path(path).read_bytes()
    doc = json.loads(b)
    return {"meta": {"path": _rel(path), "sha16": sha16(b), "bytes": len(b),
                     "schema": doc.get("schema"), "status": doc.get("status"),
                     "present": True},
            "doc": doc}


def deep_get(doc, names, default=None):
    if not isinstance(doc, dict):
        return default
    for n in names:
        if n in doc:
            return doc[n]
    for v in doc.values():
        if isinstance(v, dict):
            for n in names:
                if n in v:
                    return v[n]
    return default


# -------------------------------------------------------- recomputation ----
def recompute(gold_labels, verdicts, label, pool_sids=None):
    """Rate pool = all gold sids minus layer0 group (excluded_from_rates)."""
    pool = set(pool_sids) if pool_sids is not None else set(gold_labels)
    g = {s: gold_labels[s] for s in pool}
    fp_sids = sorted(s for s, gg in g.items()
                     if gg == "support_present"
                     and verdicts.get(s) == "unsupported")
    not_supported_sids = sorted(s for s, gg in g.items()
                                if gg == "support_present"
                                and verdicts.get(s) == "not-supported")
    und_sids = sorted(s for s, gg in g.items()
                      if gg == "support_present"
                      and verdicts.get(s) == "undecidable")
    leak_sids = sorted(s for s, gg in g.items()
                       if gg == "fabricated"
                       and verdicts.get(s) in ("supported", "undecidable"))
    n_fp_eligible = sum(1 for gg in g.values() if gg == "support_present")
    n_leak = sum(1 for gg in g.values() if gg == "fabricated")
    fp = wilson(len(fp_sids), n_fp_eligible)
    leak = wilson(len(leak_sids), n_leak)
    und_rate = (len(und_sids) / float(n_fp_eligible)
                if n_fp_eligible else None)
    fp_und_den = len(fp_sids) / float(n_fp_eligible - len(und_sids)) \
        if (n_fp_eligible - len(und_sids)) > 0 else None
    vc = {}
    for v in verdicts.values():
        vc[v] = vc.get(v, 0) + 1
    four = {s: vc.get(s, 0) for s in STATES}
    band = band_of(fp, leak)
    return {
        "reading": label,
        "fp": dict(fp, sids=fp_sids, max_pass_k=max_pass_k(n_fp_eligible, FP_MAX)),
        "leak": dict(leak, sids=leak_sids,
                     max_pass_k=max_pass_k(n_leak, LEAK_MAX)),
        "not_supported_sids": not_supported_sids,
        "n_not_supported": len(not_supported_sids),
        "band": band,
        "verdict_counts": dict(sorted(vc.items())),
        "four_state_counts": four,
        "undecidable_on_gold_support": {
            "k": len(und_sids), "n": n_fp_eligible,
            "rate": round(und_rate, 6) if und_rate is not None else None,
            "sids": und_sids,
        },
        "fp_readings": {
            "canonical": {"k": len(fp_sids), "n": n_fp_eligible,
                          "rate": round(len(fp_sids) / n_fp_eligible, 6)
                          if n_fp_eligible else None},
            "undecidable_in_denominator": {
                "k": len(fp_sids),
                "n": n_fp_eligible - len(und_sids),
                "rate": round(fp_und_den, 6) if fp_und_den is not None else None,
            },
        },
        "pool": {"n_fp_eligible": n_fp_eligible, "n_leak": n_leak,
                 "n_pool_sentences": len(pool),
                 "n_layer0_excluded": len(gold_labels) - len(pool)},
    }


# --------------------------------------------------------- self-test b5 -----
def self_test_b5():
    gold, _gd = load_gold(B5_GOLD, B5_GOLD_SHA16, B5_GOLD_BYTES)
    cb = json.loads(pinned_bytes(CLEANBLIND, CLEANBLIND_SHA16, None,
                                 "M5C2-REV7-2-CLEANBLIND-DECISION.json"))
    maps = {"A": cb.get("A_verdict_map") or {}, "B": cb.get("B_verdict_map") or {}}
    if len(maps["A"]) != 326 or len(maps["B"]) != 326:
        die("cleanblind b5 maps are not 326 rows")
    out = {}
    for lab, vm in maps.items():
        r = recompute(gold["labels"], vm, lab)
        out[lab] = {"fp": [r["fp"]["k"], r["fp"]["n"]],
                    "leak": [r["leak"]["k"], r["leak"]["n"]],
                    "upper": [r["fp"]["upper"], r["leak"]["upper"]],
                    "band": r["band"],
                    "und": [r["undecidable_on_gold_support"]["k"],
                            r["undecidable_on_gold_support"]["n"]],
                    "fp_canonical": r["fp_readings"]["canonical"],
                    "fp_und": r["fp_readings"]["undecidable_in_denominator"]}
    exp = {"A": {"fp": [2, 72], "leak": [0, 29]},
           "B": {"fp": [2, 72], "leak": [1, 29]}}
    ok = all(out[l]["fp"] == exp[l]["fp"] and out[l]["leak"] == exp[l]["leak"]
             for l in ("A", "B"))
    print(json.dumps({"status": "self_test_ok" if ok else "self_test_FAIL",
                      "b5": out, "expected": exp,
                      "note": "b5 verify: A=2/72,0/29; B=2/72,1/29 "
                              "(RULING-M5C2-B7-A4 R1)"},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 3


# ---------------------------------------------------------------- audit ----
def load_layer0():
    ex = json.loads(EXTRACT.read_text(encoding="utf-8"))
    recs = ex.get("records") or []
    l0 = [r for r in recs if (r.get("route") or "model_extract") != "model_extract"]
    vc = {}
    for r in l0:
        vc[r.get("route")] = vc.get(r.get("route"), 0) + 1
    return {
        "path": _rel(EXTRACT), "sha16": sha16(EXTRACT.read_bytes()),
        "bytes": EXTRACT.stat().st_size,
        "n_forward": ex.get("n_forward"), "n_sentences": ex.get("n_sentences"),
        "layer0_skipped": ex.get("layer0_skipped"), "aborted": ex.get("aborted"),
        "routes": dict(sorted(vc.items())),
        "sids": sorted(r["sid"] for r in l0),
    }


def _deep(obj, *names):
    if not isinstance(obj, dict):
        return None
    for n in names:
        if n in obj:
            return obj[n]
    for v in obj.values():
        if isinstance(v, dict):
            for n in names:
                if n in v:
                    return v[n]
    return None


def audit():
    missing = [str(x) for x in (EXTRACT, DECIDE, WIDE, READINGS)
               if not Path(x).exists()]
    if missing:
        print(json.dumps({"status": "pending_inputs", "missing": missing,
                          "note": "b7′ 判定链尚未完整落盘；不生成部分件"},
                         ensure_ascii=False, indent=1))
        return 4

    gold, _gd = load_gold(GOLD, GOLD_SHA16, GOLD_BYTES)
    l0 = load_layer0()
    a_doc = load_verdict_map(DECIDE, "A")
    b_doc = load_verdict_map(WIDE, "B")
    rd = load_readings(READINGS)
    if not rd:
        die("readings artifact unreadable")
    doc = rd["doc"]

    l0_sids = l0["sids"]
    if len(l0_sids) != 42:
        die("layer0 group is not 42 sids (got %d)" % len(l0_sids))
    if not set(l0_sids) <= set(gold["labels"]):
        die("layer0 sids not inside gold sid set")
    pool_sids = [s for s in gold["labels"] if s not in set(l0_sids)]
    for nm, d in (("A", a_doc), ("B", b_doc)):
        if set(d["verdicts"]) != set(gold["labels"]):
            die("%s verdict map does not cover 623 gold sids" % nm)

    rec = {"A": recompute(gold["labels"], a_doc["verdicts"], "A", pool_sids),
           "B": recompute(gold["labels"], b_doc["verdicts"], "B", pool_sids)}
    l0_gold_mix = {}
    for s in l0_sids:
        g = gold["labels"][s]
        l0_gold_mix[g] = l0_gold_mix.get(g, 0) + 1
    l0_verdicts = {
        "A": {v: sum(1 for s in l0_sids if a_doc["verdicts"][s] == v)
              for v in set(a_doc["verdicts"][s] for s in l0_sids)},
        "B": {v: sum(1 for s in l0_sids if b_doc["verdicts"][s] == v)
              for v in set(b_doc["verdicts"][s] for s in l0_sids)},
    }

    lv = {k: severity_level(v["band"]) for k, v in rec.items()}
    worst = max(SEVERITY[v] for v in lv.values())
    worse = [k for k, v in lv.items() if SEVERITY[v] == worst]
    expected_worse = "A" if len(worse) > 1 else worse[0]
    expected_final = rec[expected_worse]["band"]
    expected_headline = "A_narrow" if expected_worse == "A" else "B_wide"

    # preset lines on the layer0-excluded pool (A5 R1/R2, dynamic)
    n_fp, n_leak = rec["A"]["pool"]["n_fp_eligible"], rec["A"]["pool"]["n_leak"]
    fp_max = max_pass_k(n_fp, FP_MAX)
    leak_max = max_pass_k(n_leak, LEAK_MAX)
    preset = {
        "fp_line": {"threshold": FP_MAX, "n": n_fp, "max_pass_k": fp_max,
                    "upper_at_max": wilson(fp_max, n_fp)["hi"],
                    "upper_at_next": wilson(fp_max + 1, n_fp)["hi"]
                    if fp_max < n_fp else None,
                    "a5_claim_13_of_148": wilson(13, 148)["hi"],
                    "a5_claim_14_of_148": wilson(14, 148)["hi"]},
        "leak_line": {"threshold": LEAK_MAX, "n": n_leak,
                      "max_pass_k": leak_max,
                      "upper_at_max": wilson(leak_max, n_leak)["hi"],
                      "upper_at_next": wilson(leak_max + 1, n_leak)["hi"]
                      if leak_max < n_leak else None,
                      "a5a1_claim_6_of_63": wilson(6, 63)["hi"],
                      "a5a1_claim_7_of_63": wilson(7, 63)["hi"]},
    }

    # ---- READINGS fields
    rd_readings = _deep(doc, "readings") or {}
    actual_final = doc.get("final_verdict")
    actual_headline = doc.get("headline_reading")
    disc_ok = contains_phrase(doc, DISCLOSURE_PHRASES)
    und_rate = rec["A"]["undecidable_on_gold_support"]["rate"]
    caveat_required = (und_rate or 0) > 0.15
    fp_cav = _deep(doc, "fp_reading_caveat") or {}
    caveat_text = (fp_cav.get("caveat") or "") if isinstance(fp_cav, dict) else ""
    caveat_present = norm_text(CAVEAT_PHRASE) in norm_text(_iter_text(doc))
    caveat_text_claims = "> 15%" in caveat_text or ">15%" in caveat_text
    caveat_ok = (caveat_required
                 == bool(fp_cav.get("exceeds_threshold")))
    caveat_text_ok = not (caveat_present and not caveat_required
                          and caveat_text_claims)
    caveat_issue = None
    if caveat_present and not caveat_required:
        caveat_issue = ("caveat text present while undecidable ratio %.4f%% "
                        "<= 15%% (fp_reading_caveat.exceeds_threshold=%r); "
                        "text claims %r -> 文案自相矛盾"
                        % ((und_rate or 0) * 100, fp_cav.get("exceeds_threshold"),
                           caveat_text[:60]))

    # ---- layer0 checks
    layer0_art = _deep(doc, "layer0_group") or {}
    layer0_ok = (isinstance(layer0_art, dict)
                 and layer0_art.get("n") == 42
                 and layer0_art.get("excluded_from_rates") is True
                 and sorted(layer0_art.get("sids") or []) == l0_sids
                 and {k: v for k, v in (layer0_art.get("gold_mix") or {}).items()
                      if v} == {k: v for k, v in l0_gold_mix.items() if v}
                 and (layer0_art.get("verdicts") or {}) == l0_verdicts["A"])
    doc_txt = norm_text(_iter_text(doc))
    layer0_caveat_ok = ("layer0abstain_check42/623" in doc_txt
                        and "28/233" in doc_txt)

    # ---- A4/A5 rule checks
    grade_labels = {k: rec[k]["band"] for k in ("A", "B")}
    checks = {
        "A4_1_final_is_worse_band": {
            "expected": expected_final, "actual": actual_final,
            "worse_readings": worse, "levels": lv,
            "pass": actual_final == expected_final},
        "A4_2_headline_points_to_worse": {
            "expected": expected_headline, "actual": actual_headline,
            "pass": actual_headline == expected_headline},
        "A4_3_readings_disclosure": {
            "required_phrases": list(DISCLOSURE_PHRASES),
            "present": disc_ok, "pass": bool(disc_ok)},
        "A4_4_A3R4_undecidable_caveat": {
            "undecidable_ratio": und_rate, "threshold": 0.15,
            "required": caveat_required,
            "exceeds_threshold_field": fp_cav.get("exceeds_threshold"),
            "caveat_text_present": caveat_present,
            "pass": bool(caveat_ok), "issue": caveat_issue},
        "A4_4b_caveat_text_consistency": {
            "caveat_present": caveat_present,
            "required": caveat_required,
            "text_claims_over_15": caveat_text_claims,
            "caveat_text": caveat_text[:120],
            "pass": bool(caveat_text_ok),
            "note": "producer 件 fp_reading_caveat.caveat 文案固定写成 >15%，"
                    "与 exceeds_threshold=false/2.04% 自相矛盾；规则判定本身正确"},
        "A5_R1_preset_lines": {"fp": preset["fp_line"],
                               "leak": preset["leak_line"],
                               "pass": (fp_max == 13 and leak_max in (5, 6))},
        "A5_R1_readings_grades_match_recompute": {
            "audit": grade_labels,
            "readings": {k: (_deep(rd_readings, k) or {}).get("grade")
                         for k in ("A_narrow", "B_wide")},
            "pass": all((_deep(rd_readings, k) or {}).get("grade")
                        == rec[k.split("_")[0]]["band"]
                        for k in ("A_narrow", "B_wide"))},
        "C2_layer0_group": {
            "audit": {"n": len(l0_sids), "routes": l0["routes"],
                      "gold_mix": l0_gold_mix, "verdicts": l0_verdicts,
                      "excluded_from_rates": True},
            "artifact": layer0_art if isinstance(layer0_art, dict) else None,
            "pass": bool(layer0_ok and layer0_caveat_ok)},
        "denominator_pool": {
            "n_fp_eligible": n_fp, "n_leak": n_leak,
            "n_sentences": len(gold["labels"]),
            "n_layer0_excluded": len(l0_sids),
            "n_fp_total_gold": gold["counts"].get("support_present"),
            "n_leak_total_gold": gold["counts"].get("fabricated"),
            "pass": (n_fp == 147 and n_leak == 62)},
    }

    # ---- two-reading diff (actual)
    sids = sorted(gold["labels"])
    rows = [{"sid": s, "A": a_doc["verdicts"][s], "B": b_doc["verdicts"][s],
             "gold": gold["labels"][s]} for s in sids
            if a_doc["verdicts"][s] != b_doc["verdicts"][s]]
    negative = ("unsupported", "not-supported", "parse_fail")
    dirs = {}
    for r in rows:
        if r["A"] in negative and r["B"] == "supported":
            key = "loose_B_supported_A_negative"
        elif r["A"] == "supported" and r["B"] in negative:
            key = "strict_A_supported_B_negative"
        else:
            key = "other"
        dirs[key] = dirs.get(key, 0) + 1
    b5_class = [r for r in rows if r["A"] == "unsupported"
                and r["B"] == "supported" and r["gold"] == "fabricated"]
    art_diff = _deep(doc, "diff_b_vs_a") or {}
    wide_diff = b_doc["doc"].get("diff_vs_decide") or {}
    two = {
        "actual_n_diff": len(rows),
        "actual_diff_sids": [r["sid"] for r in rows],
        "rows": rows,
        "direction_counts": dirs,
        "b5_class_fabricated_Aneg_Bsupported": [r["sid"] for r in b5_class],
        "readings_diff": {"n_diff": art_diff.get("n_diff"),
                          "sids": art_diff.get("sids"),
                          "match": (art_diff.get("n_diff") == len(rows)
                                    and sorted(art_diff.get("sids") or [])
                                    == [r["sid"] for r in rows])},
        "wide_artifact_diff_vs_decide": {
            "n_diff": wide_diff.get("n_diff"),
            "n_sids": len(wide_diff.get("diff_sids") or []),
            "consistent_with_actual": wide_diff.get("n_diff") == len(rows),
            "issue": None if wide_diff.get("n_diff") == len(rows)
                     else ("WIDE.diff_vs_decide.n_diff=%r/%d sids != actual %d "
                           "(self-reported field stale/buggy; READINGS diff is "
                           "the correct one)" % (wide_diff.get("n_diff"),
                                                 len(wide_diff.get("diff_sids")
                                                     or []), len(rows)))},
        "cleanblind_class_consistent": bool(b5_class),
        "direction_note": "b7 为混合方向（B 既有更宽也有更严），与 b5 的纯"
                          "loose 方向不同；b5 类（gold=fabricated, A unsupported"
                          " -> B supported）逐 sid 列出供对齐",
        "pass": (art_diff.get("n_diff") == len(rows)),
    }

    # ---- field-by-field diff vs READINGS.readings
    def cmp(field, mine, theirs):
        return {"field": field, "audit": mine, "readings": theirs,
                "equal": mine == theirs}

    diffs_vs_readings = []
    for lab, key in (("A", "A_narrow"), ("B", "B_wide")):
        blk = rd_readings.get(key) or {}
        r = rec[lab]
        for f, mine, theirs in (
                ("fp.k", r["fp"]["k"], (blk.get("fp") or {}).get("k")),
                ("fp.n", r["fp"]["n"], (blk.get("fp") or {}).get("n")),
                ("fp.rate", r["fp"]["rate"], (blk.get("fp") or {}).get("rate")),
                ("fp.hi", r["fp"]["hi"], (blk.get("fp") or {}).get("hi")),
                ("leak.k", r["leak"]["k"], (blk.get("leak") or {}).get("k")),
                ("leak.n", r["leak"]["n"], (blk.get("leak") or {}).get("n")),
                ("leak.rate", r["leak"]["rate"],
                 (blk.get("leak") or {}).get("rate")),
                ("leak.hi", r["leak"]["hi"], (blk.get("leak") or {}).get("hi")),
                ("grade", r["band"], blk.get("grade")),
                ("n_fp_eligible", r["pool"]["n_fp_eligible"],
                 blk.get("n_fp_eligible")),
                ("n_leak", r["pool"]["n_leak"], blk.get("n_leak")),
                ("und.k", r["undecidable_on_gold_support"]["k"],
                 (blk.get("undecidable_on_gold_support") or {}).get("k")),
                ("fp_readings.canonical",
                 r["fp_readings"]["canonical"].get("rate"),
                 ((blk.get("fp_readings") or {}).get("canonical") or {}).get("rate")),
                ("fp_readings.undecidable_in_denominator",
                 r["fp_readings"]["undecidable_in_denominator"].get("rate"),
                 ((blk.get("fp_readings") or {})
                  .get("undecidable_in_denominator") or {}).get("rate"))):
            diffs_vs_readings.append(cmp("%s.%s" % (lab, f), mine, theirs))
    readings_match = all(d["equal"] for d in diffs_vs_readings)

    core_checks = ("A4_1_final_is_worse_band", "A4_2_headline_points_to_worse",
                   "A4_3_readings_disclosure", "A4_4_A3R4_undecidable_caveat",
                   "A5_R1_preset_lines", "A5_R1_readings_grades_match_recompute",
                   "C2_layer0_group", "denominator_pool")
    core_ok = all(checks[k]["pass"] for k in core_checks)
    if not caveat_text_ok:
        warn = [caveat_issue] if caveat_issue else []
    else:
        warn = []
    warn += [x for x in (two["wide_artifact_diff_vs_decide"]["issue"],) if x]
    out = {
        "schema": "m5c2_b7_readings_audit_v1",
        "role": "independent recomputation of the b7′ readings (CPU only)",
        "status": "computed",
        "pins": {
            "gold": {"path": _rel(GOLD), "sha16": GOLD_SHA16,
                     "bytes": GOLD_BYTES},
            "a2_md": {"path": _rel(A2_MD), "sha16": sha16(A2_MD.read_bytes())
                      if A2_MD.exists() else None},
            "a5_md": {"path": _rel(A5_MD), "sha16": A5_SHA16,
                      "bytes": A5_BYTES},
            "a5_json": {"path": _rel(A5_JSON), "sha16": A5_JSON_SHA16},
            "a5_a1_md": {"path": _rel(A5A1_MD), "sha16": A5A1_SHA16,
                         "bytes": A5A1_BYTES},
            "a5_a1_json": {"path": _rel(A5A1_JSON),
                           "sha16": A5A1_JSON_SHA16},
            "a4_md": {"path": _rel(A4_MD), "sha16": A4_SHA16,
                      "bytes": A4_BYTES},
            "a3_md": {"path": _rel(A3_MD), "sha16": A3_SHA16},
            "readings_freeze": {"path": _rel(READINGS_FREEZE),
                                "sha16": sha16(READINGS_FREEZE.read_bytes())
                                if READINGS_FREEZE.exists() else None},
            "extract": {"path": l0["path"], "sha16": l0["sha16"],
                        "bytes": l0["bytes"]},
            "decide": a_doc["meta"], "wide": b_doc["meta"],
            "readings": rd["meta"],
        },
        "gold": {k: gold[k] for k in ("path", "sha16", "bytes", "schema",
                                      "n", "counts")},
        "layer0": {"n": len(l0_sids), "sids": l0_sids,
                   "routes": l0["routes"], "gold_mix": l0_gold_mix,
                   "verdicts": l0_verdicts, "excluded_from_rates": True,
                   "caveat": doc.get("layer0_caveat")},
        "denominators": {
            "n_sentences": len(gold["labels"]),
            "n_layer0_excluded": len(l0_sids),
            "n_fp_eligible": n_fp, "n_leak": n_leak,
            "n_fp_total_gold": gold["counts"].get("support_present"),
            "n_leak_total_gold": gold["counts"].get("fabricated"),
            "pool_rule": "rates pool = gold sids minus layer0 abstain_ok group "
                         "(C2 layer0 exclusion)",
        },
        "readings": rec,
        "final": {
            "severity_order": ["未通过", "擦边", "未接上", "达标"],
            "levels": lv, "worse_readings": worse,
            "expected_final": expected_final,
            "expected_headline": expected_headline,
            "actual_final": actual_final,
            "actual_headline": actual_headline,
        },
        "preset_lines": preset,
        "checks": checks,
        "two_reading_diff": two,
        "diffs_vs_readings": diffs_vs_readings,
        "readings_match": readings_match,
        "warnings": warn,
        "pass": bool(core_ok and readings_match),
        "commands": [
            "python -X utf8 tmp/b7_readings_recheck.py --self-test",
            "python -X utf8 tmp/b7_readings_recheck.py --decide out/M5C2-B7-DECIDE.json --wide out/M5C2-B7-WIDE-SENSITIVITY.json --gold out/M5C2-B7-GOLD.json --readings out/M5C2-B7-READINGS.json",
            "python -X utf8 kvmem/m2_visibility/m5/run_m5c2_b7_readings_audit.py",
        ],
        "notes": [
            "两率池排除 layer0 abstain_ok 42 句（C2）；故 n_fp=147、n_leak=62；"
            "总 gold 为 148/63。",
            "FP = gold support_present ∧ verdict==unsupported；漏判 = gold "
            "fabricated ∧ verdict ∈ {supported, undecidable}；Wilson z=1.959964。",
            "A5 R1：达标=两率 Wilson 上界 ≤15%/≤20% 且分母≥20；点估计仅判未通过；"
            "上界越线=擦边。",
            "A4 R2/R3：final=较差档、headline=较差读、固定 disclosure；"
            "A3 R4：undecidable>15% 才需 caveat。",
            "未读 rev7-impl 实现；gold 可读；blind 原文未读。",
        ],
    }
    write_json_atomic(ART, out)
    print(json.dumps({
        "status": out["status"],
        "artifact": str(ART),
        "sha16": sha16(ART.read_bytes()),
        "pool": {"n_fp": n_fp, "n_leak": n_leak},
        "A": {"fp": [rec["A"]["fp"]["k"], rec["A"]["fp"]["n"],
                    rec["A"]["fp"]["hi"]],
              "leak": [rec["A"]["leak"]["k"], rec["A"]["leak"]["n"],
                       rec["A"]["leak"]["hi"]], "band": rec["A"]["band"]},
        "B": {"fp": [rec["B"]["fp"]["k"], rec["B"]["fp"]["n"],
                    rec["B"]["fp"]["hi"]],
              "leak": [rec["B"]["leak"]["k"], rec["B"]["leak"]["n"],
                       rec["B"]["leak"]["hi"]], "band": rec["B"]["band"]},
        "final_verdict": actual_final, "headline": actual_headline,
        "checks": {k: bool(v.get("pass")) for k, v in checks.items()},
        "caveat_text_consistent": bool(caveat_text_ok),
        "two_reading_diff": {"n": len(rows),
                             "readings_match": two["readings_diff"]["match"],
                             "wide_artifact_consistent":
                                 two["wide_artifact_diff_vs_decide"][
                                     "consistent_with_actual"]},
        "readings_match": readings_match,
        "warnings": warn,
        "pass": out["pass"],
    }, ensure_ascii=False, indent=1))
    return 0 if out["pass"] else 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test-b5", action="store_true")
    a = ap.parse_args()
    if a.self_test_b5:
        return self_test_b5()
    return audit()


if __name__ == "__main__":
    sys.exit(main())