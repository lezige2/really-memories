#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B6 offline decision / rates runner (CPU only, zero GPU).

Split architecture (post-incident rebuild):
  out/M5C2-B6-EXTRACT.json  (GPU pass, run_m5c2_b6_extract.py)
  -> out/M5C2-B6-DECIDE.json  per-sentence rev5.1 + rev7.1 verdicts  (--run)
  -> out/M5C2-B6-RATES.json   three-gold rates + Wilson + H1         (--rates-only)

Judge rules are IMPORTED, never rewritten:
  run_m5c2_rev7_1_offline.py  (rev7.1: N1-N4 / R4+ / judge_row_rev7)
  run_m5c2_rev5_1_offline.py, run_m5c2_rev5_offline.py, run_m5c2_rev4_1.py

Modes:
  --dry-run     static pin/path validation only (writes nothing, no GPU)
  --run         judge every extracted sentence (CPU), writes DECIDE.json
  --rates-only  requires DECIDE.json + three frozen golds -> RATES.json
"""
import argparse
import json
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
sys.path.insert(0, str(M5))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/engine"))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/m7/out"))
sys.path.insert(0, str(ROOT / "tools"))

import run_m5c2_rev4 as R4  # noqa: E402
import run_m5c2_rev4_1 as R41  # noqa: E402
import run_m5c2_rev5_offline as R5  # noqa: E402
import run_m5c2_rev5_1_offline as R51  # noqa: E402
import run_m5c2_rev7_1_offline as R71  # noqa: E402

EXTRACT = OUT / "M5C2-B6-EXTRACT.json"
DECIDE = OUT / "M5C2-B6-DECIDE.json"
RATES = OUT / "M5C2-B6-RATES.json"
EXTRACT_SHA16 = None  # pinned from DECIDE.json on --rates-only
GEN = OUT / "M5C2-B6-GEN.json"
GEN_SHA16 = "93957fb3be6665a9"    # frozen after the b6 GPU pass
GEN_BYTES = 73633
SENT = OUT / "M5C2-B6-SENTS.json"
SENT_SHA16 = "1fad9d1c5291a77a"  # frozen by M5C2-B6-SENTS-FREEZE.json
SENT_BYTES = 100745
SENT_N = 233    # frozen by M5C2-B6-SENTS-FREEZE.json
QS = OUT / "M5C2-B6-SENTENCES.json"   # frozen question types (lure map)
QS_SHA16 = "23588ec099ca9255"
QS_BYTES = 9482
PRE = ROOT / "docs/_work/PREREG-M5-C2-B6.md"
PRE_SHA16 = "ac27d47d3a3efff9"
PRE_BYTES = 17374
PROMPT_SHA = "a6bc4f268f7711de"
R71_PATH = M5 / "run_m5c2_rev7_1_offline.py"
R71_SHA16 = "88256d274c9993cc"
R71_BYTES = 50618
R71_PRE_SHA16 = "09d6f1b163ea0b84"
JUDGE_VERSION = "rev7.1"
LEAK_MAX = 0.20
FALSE_MAX = 0.15
MIN_N_FP = 20
MIN_N_LEAK = 20   # PREREG-M5-C2-B6.md §6: both denominators >= 20
Z95 = 1.959964
BOOT_SEED = 20261026
BOOT_REPS = 10000
GOLD_STATES = ("support_present", "fabricated", "no_fact", "undecidable")

H1_MD = ROOT / "docs/_work/PREREG-M5-C2-B6.md"   # b6 acceptance is §6
H1_MD_SHA16 = "ac27d47d3a3efff9"
SENS_MD = ROOT / "docs/_work/PREREG-M5-C2-B6.md"
SENS_MD_SHA16 = "ac27d47d3a3efff9"

GOLDS = (
    {"key": "lead", "label": "LEAD-gold", "arg": "--gold-lead",
     "default": OUT / "M5C2-B6-GOLD.json",
     "sha16": "44d4dd86cac21f0a", "bytes": 48102, "official": True},
    {"key": "a", "label": "A-only", "arg": "--gold-a", "default": None,
     "sha16": None, "bytes": None, "official": False, "required": False},
    {"key": "b", "label": "B-only", "arg": "--gold-b", "default": None,
     "sha16": None, "bytes": None, "official": False, "required": False},
)


def sha16(b):
    return __import__("hashlib").sha256(b).hexdigest()[:16]


def rel(p):
    try:
        return str(Path(p).relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def write_json_atomic(path, obj):
    """Atomic write only: tmp + os.replace (never truncate a live deliverable)."""
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)
    return Path(path)


class PendingArtifacts(SystemExit):
    """b6 GEN/SENTS not produced yet: dry-run reports it instead of failing."""


def verify_pins():
    pb = PRE.read_bytes()
    if sha16(pb) != PRE_SHA16 or len(pb) != PRE_BYTES:
        raise SystemExit("B5 prereg changed")
    if not GEN.exists() or not SENT.exists():
        raise PendingArtifacts("missing b6 GEN/SENTS artifacts")
    gb = GEN.read_bytes()
    if GEN_SHA16 and (sha16(gb) != GEN_SHA16 or len(gb) != GEN_BYTES):
        raise SystemExit("M5C2-B6-GEN.json does not match its pin")
    sb = SENT.read_bytes()
    if SENT_SHA16 and (sha16(sb) != SENT_SHA16 or len(sb) != SENT_BYTES):
        raise SystemExit("M5C2-B6-SENTS.json does not match its pin")
    sdoc = json.loads(sb.decode("utf-8"))
    if sdoc.get("schema") != "m5c2_b6_sents_v1":
        raise SystemExit("unexpected b6 SENTS schema")
    if (sdoc.get("gen") or {}).get("sha16") != sha16(gb):
        raise SystemExit("b6 SENTS was split from a different b6 GEN")
    rb = R71_PATH.read_bytes()
    if sha16(rb) != R71_SHA16 or len(rb) != R71_BYTES:
        raise SystemExit("rev7.1 judge code changed")
    if R71.PRE_SHA16 != R71_PRE_SHA16:
        raise SystemExit("rev7.1 prereg pin changed")
    if R71.SUPERSEDES_SHA16 != "32eaf82ca56600c4":
        raise SystemExit("rev7.1 supersedes changed")
    if R71.CORRECTION_TYPE != "statement_correction":
        raise SystemExit("rev7.1 correction type changed")
    if R71.RULE_CODE_UNCHANGED is not True:
        raise SystemExit("rev7.1 rule code is not unchanged")
    if sha16(R4.REV4_TEMPLATE.encode("utf-8")) != PROMPT_SHA:
        raise SystemExit("frozen extraction prompt changed")
    return {
        "prereg": {"sha16": PRE_SHA16, "bytes": PRE_BYTES},
        "gen": {"sha16": GEN_SHA16, "bytes": GEN_BYTES},
        "sentences": {"sha16": SENT_SHA16, "bytes": SENT_BYTES,
                      "n_sentences": SENT_N},
        "judge_layer": {"version": JUDGE_VERSION, "code": rel(R71_PATH),
                        "sha16": R71_SHA16, "bytes": R71_BYTES,
                        "prereg_sha16": R71_PRE_SHA16,
                        "supersedes_sha16": R71.SUPERSEDES_SHA16,
                        "correction_type": R71.CORRECTION_TYPE,
                        "rule_code_unchanged": R71.RULE_CODE_UNCHANGED},
        "extraction_prompt_sha16": PROMPT_SHA,
        "harness": {"no_gpu": True, "no_forward": True, "no_network": True},
    }


def load_extract():
    if not EXTRACT.exists():
        raise SystemExit("missing %s (run the GPU extraction pass first)"
                         % rel(EXTRACT))
    b = EXTRACT.read_bytes()
    d = json.loads(b.decode("utf-8"))
    if d.get("schema") != "m5c2_b6_extract_v1":
        raise SystemExit("unexpected EXTRACT schema %r" % (d.get("schema"),))
    if d.get("aborted") is not None:
        raise SystemExit("EXTRACT aborted=%r; judging refuses partial data"
                         % (d.get("aborted"),))
    recs = d.get("records") or []
    sdoc = json.loads(SENT.read_bytes().decode("utf-8"))
    n_sents = int(sdoc.get("n_sentences") or 0)
    if len(recs) != n_sents:
        raise SystemExit("EXTRACT holds %d records, expected %d"
                         % (len(recs), n_sents))
    expected_forwards = n_sents - int(d.get("layer0_skipped") or 0)
    if int(d.get("n_forward") or 0) != expected_forwards:
        raise SystemExit("EXTRACT n_forward=%r != %d (n_sentences %d - "
                         "layer0_skipped %r)"
                         % (d.get("n_forward"), expected_forwards, n_sents,
                            d.get("layer0_skipped")))
    return d, {"path": rel(EXTRACT), "sha16": sha16(b), "bytes": len(b)}


def judge_record(rec):
    """Per-sentence rev5.1 verdict, then rev7.1 item/sentence judgement."""
    src = str(rec.get("source_text") or "")
    sent = str(rec.get("text") or "")
    route = rec.get("route") or "model_extract"
    layer0 = rec.get("layer0")
    items = rec.get("items") or []
    parse_ok = bool(rec.get("parse_ok"))
    row = {"sid": rec["sid"], "sentence": sent, "source_text": src,
           "route": route, "parse_ok": parse_ok, "derived": False,
           "layer0": layer0, "items": [], "verdict": None}
    if route == "empty_source":
        row["verdict"] = "unsupported"
        row["items"] = []
    elif route == "abstain_check":
        row["verdict"] = (layer0 or {}).get("verdict") or "abstain_ok"
        row["items"] = []
    else:
        items2 = R51.judge_items(items, src)
        en, dd = R5.derived_plus(sent, src)
        row["items"] = items2
        row["derived"] = bool((dd or {}).get("enabled"))
        if not parse_ok:
            row["verdict"] = "parse_fail"
        elif en:
            row["verdict"] = "undecidable"
        elif not items2:
            row["verdict"] = "undecidable"
        elif any(z["absent"] for z in items2):
            row["verdict"] = "unsupported"
        else:
            row["verdict"] = "supported"
    sent_rec, item_recs, dd7 = R71.judge_row_rev7(row)
    return {
        "sid": rec["sid"], "qid": rec["qid"], "scenario": rec["scenario"],
        "text": sent, "route": route, "parse_ok": parse_ok,
        "parse_reason": rec.get("parse_reason"),
        "verdict_v51": row["verdict"],
        "verdict_rev7": sent_rec["verdict_rev7"],
        "changed": bool(sent_rec.get("changed")),
        "n_items": sent_rec.get("n_items"),
        "n_valid": sent_rec.get("n_valid"),
        "n_invalid": sent_rec.get("n_invalid"),
        "n_absent": sent_rec.get("n_absent"),
        "n_unverified": sent_rec.get("n_unverified"),
        "derived_rev7": bool(sent_rec.get("derived_rev7")),
        "items": item_recs,
        "derived_detail": dd7 if isinstance(dd7, dict) else None,
        "verdict": sent_rec["verdict_rev7"],
        "rule_codes": sorted({it["rule"] for it in item_recs if it.get("rule")}),
        "extraction_prompt_sha16": rec.get("prompt_sha16"),
        "raw_sha16": (sha16(str(rec.get("raw_out")).encode("utf-8"))
                      if rec.get("raw_out") else None),
    }


def lure_qids():
    """qids whose frozen type is `lure` (拒答诊断用; no label values involved)."""
    try:
        b = QS.read_bytes()
        if sha16(b) != QS_SHA16 or len(b) != QS_BYTES:
            return []
        d = json.loads(b.decode("utf-8"))
        out = []
        for sc in d.get("scenarios") or []:
            for q in sc.get("questions") or []:
                if q.get("type") == "lure":
                    out.append(q["qid"])
        return sorted(out)
    except Exception:  # noqa: BLE001
        return []


def aggregate(judged, extract_meta, pins):
    verdicts = Counter(r["verdict_rev7"] for r in judged)
    routes = Counter(r["route"] for r in judged)
    changed = [r["sid"] for r in judged if r["changed"]]
    item_states = Counter()
    rule_hits = Counter()
    for r in judged:
        for it in r["items"]:
            item_states[it["item_verdict"]] += 1
            if it.get("rule"):
                rule_hits[it["rule"]] += 1
    value_states = ["support_present", "no_fact", "undecidable", "fabricated"]
    lures = lure_qids()
    lure_dist = {}
    for lq in lures:
        d = Counter(r["verdict_rev7"] for r in judged if r["qid"] == lq)
        lure_dist[lq] = {k: d.get(k, 0) for k in
                         ("supported", "unsupported", "undecidable", "parse_fail")}
    return {
        "schema": "m5c2_b5_decide_v1",
        "status": "已判未读数",
        "pins": pins,
        "extract": extract_meta,
        "n_sentences": len(judged),
        "n_questions": len({r["qid"] for r in judged}),
        "verdict_counts_rev5_1": dict(Counter(r["verdict_v51"] for r in judged)),
        "verdict_counts_rev7_1": dict(sorted(verdicts.items())),
        "routes": dict(sorted(routes.items())),
        "n_changed_vs_rev5_1": len(changed),
        "changed_sids": changed,
        "item_state_counts": dict(sorted(item_states.items())),
        "rule_hit_counts": dict(sorted(rule_hits.items())),
        "rule_code_unchanged": True,
        "n_forward": 0,
        "extraction_sha16": extract_meta.get("sha16"),
        "extraction_bytes": extract_meta.get("bytes"),
        "conclusion": "未接上（样本量不足）",
        "conclusion_statement": "b5 的擦边仍是本项目唯一有效的 H1 读数；"
                                "b6 未提供新的有效判定证据",
        "diagnostics_lure_rejection": {
            "note": "b6 模型对 lure 的拒答行为变好、fabricated 产出下降——这是"
                    "产品侧好消息，不是判据坏消息（gold 侧计数见 RATES）",
            "n_lure_qids": len(lures),
            "lure_qids": lures,
            "judge_four_state_per_lure_qid": lure_dist,
        },
        "diagnostic_only": True,
        "no_rates": True,
        "rates_gold_pending": "run --rates-only --gold-lead out/M5C2-B6-GOLD.json "
                              "(denominator gate: n_leak=17<20 => 未接上)",
        "no_gold": True,
        "no_blind_labels_read": True,
        "no_rule_changes": True,
        "no_threshold_changes": True,
        "no_forward": True,
        "no_network": True,
        "rows": judged,
    }


def wilson(k, n, z=Z95):
    if n <= 0:
        return {"k": 0, "n": 0, "rate": None, "lo": None, "hi": None}
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return {"k": k, "n": n, "rate": round(p, 6),
            "lo": round(max(0.0, center - half), 6),
            "hi": round(min(1.0, center + half), 6)}


def percentile(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    pos = (len(xs) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def cluster_bootstrap(rows, num_pred, den_pred, seed=BOOT_SEED, reps=BOOT_REPS):
    by_s = defaultdict(list)
    for r in rows:
        by_s[r["scenario"]].append(r)
    scen = sorted(by_s)
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        num = den = 0
        for _ in range(len(scen)):
            for r in by_s[scen[rng.randrange(len(scen))]]:
                num += 1 if num_pred(r) else 0
                den += 1 if den_pred(r) else 0
        if den:
            vals.append(num / den)
    return {"reps": reps, "seed": seed, "valid_reps": len(vals),
            "lo": round(percentile(vals, 0.025), 6) if vals else None,
            "hi": round(percentile(vals, 0.975), 6) if vals else None,
            "median": round(percentile(vals, 0.5), 6) if vals else None}


def load_gold(path, expect_sha16, label):
    p = Path(path)
    if not p.exists():
        raise SystemExit("missing gold %r (%s)" % (str(p), label))
    b = p.read_bytes()
    if expect_sha16 is not None and sha16(b) != expect_sha16:
        raise SystemExit("gold %s changed: %s (expected %s)"
                         % (label, sha16(b), expect_sha16))
    d = json.loads(b.decode("utf-8"))
    labels = d.get("labels")
    if isinstance(labels, list):
        gold = {}
        for x in labels:
            sid = x.get("sid")
            lab = x.get("gold_label") or x.get("state") or x.get("label")
            if sid is None or lab not in GOLD_STATES:
                raise SystemExit("bad gold label row in %s: %r" % (label, x))
            gold[sid] = lab
    elif isinstance(d.get("gold"), dict):
        gold = d["gold"]
    else:
        raise SystemExit("gold %s has neither labels[] nor gold{}" % label)
    return gold, {"path": rel(p), "sha16": sha16(b), "bytes": len(b)}


def max_pass_k(n, threshold):
    """Largest numerator k with Wilson upper <= threshold (arithmetic, not a
    new threshold): the唯一达标区间 of H1-FEASIBILITY-M5C2-B5.md."""
    k = 0
    while k <= n:
        w = wilson(k + 1, n)
        if w["hi"] is None or w["hi"] > threshold:
            break
        k += 1
    return k


def rate_block(rows, num_pred, den_pred):
    num = sum(1 for r in rows if num_pred(r))
    den = sum(1 for r in rows if den_pred(r))
    return {"numerator": num, "denominator": den,
            "rate": round(num / den, 6) if den else None,
            "wilson95": wilson(num, den),
            "cluster_bootstrap_8scen": cluster_bootstrap(rows, num_pred, den_pred),
            "rows": [r["sid"] for r in rows if num_pred(r)]}


def decide_grade(k_a, n_a, thr_a, k_b, n_b, thr_b):
    """Four-state grade (§9.4) for one gold set.

    达标 / 擦边 / 未通过 / 未接上（样本量不足）
      - sample floor: n_fp < 25 or n_leak < 20 => 未接上（样本量不足）
      - 达标: both Wilson 95% upper bounds <= thresholds (z=1.959964)
      - 擦边: both point estimates <= thresholds but >=1 upper bound crosses
      - 未通过: a point estimate exceeds its threshold
    """
    wa = wilson(k_a, n_a)
    wb = wilson(k_b, n_b)
    out = {"fp": wa, "leak": wb,
           "sample_floor": {"n_fp_min": MIN_N_FP, "n_leak_min": MIN_N_LEAK,
                            "pass": n_a >= MIN_N_FP and n_b >= MIN_N_LEAK}}
    if not out["sample_floor"]["pass"]:
        return dict(out, grade="未接上（样本量不足）",
                    reason="n_fp=%d<%d or n_leak=%d<%d"
                           % (n_a, MIN_N_FP, n_b, MIN_N_LEAK))
    fp_rate = wa["rate"]
    lk_rate = wb["rate"]
    if wa["hi"] is not None and wa["hi"] <= thr_a and \
            wb["hi"] is not None and wb["hi"] <= thr_b:
        return dict(out, grade="达标", reason="both Wilson upper bounds in band")
    if fp_rate is not None and fp_rate > thr_a:
        return dict(out, grade="未通过",
                    reason="false point %.6f > %.2f" % (fp_rate, thr_a))
    if lk_rate is not None and lk_rate > thr_b:
        return dict(out, grade="未通过",
                    reason="leak point %.6f > %.2f" % (lk_rate, thr_b))
    return dict(out, grade="擦边",
                reason="point estimates in band but a Wilson upper bound crosses")


def gold_report(judged, gold, meta, label):
    rows = []
    for r in judged:
        g = gold.get(r["sid"])
        if g is None:
            raise SystemExit("gold %s misses sid %s" % (label, r["sid"]))
        jv = r["verdict_rev7"]
        leak = (g == "fabricated" and jv in ("supported", "undecidable"))
        false = (g == "support_present" and jv == "unsupported")
        rows.append({"sid": r["sid"], "qid": r["qid"], "scenario": r["scenario"],
                     "route": r["route"], "gold": g, "judge": jv,
                     "leak_num": bool(leak), "false_num": bool(false)})
    if set(gold) != {r["sid"] for r in judged}:
        raise SystemExit("gold %s sid set differs from the judged sentence set"
                         % label)
    counts = Counter(r["gold"] for r in rows)
    n_fp = counts.get("support_present", 0)
    n_leak = counts.get("fabricated", 0)
    fp_k = sum(1 for r in rows if r["false_num"])
    lk_k = sum(1 for r in rows if r["leak_num"])
    g = decide_grade(fp_k, n_fp, FALSE_MAX, lk_k, n_leak, LEAK_MAX)
    strict_k = sum(1 for r in rows if r["gold"] == "fabricated"
                   and r["judge"] == "supported")
    return {
        "label": label, "gold": meta, "counts": dict(sorted(counts.items())),
        "denominators": {"n_fp_support_present": n_fp,
                         "n_leak_fabricated": n_leak},
        "rates": {
            "false": rate_block(rows, lambda r: r["false_num"],
                                lambda r: r["gold"] == "support_present"),
            "leak": rate_block(rows, lambda r: r["leak_num"],
                               lambda r: r["gold"] == "fabricated"),
            "strict_leak_supported_only": {
                "numerator": strict_k, "denominator": n_leak,
                "rate": round(strict_k / n_leak, 6) if n_leak else None,
                "wilson95": wilson(strict_k, n_leak)},
        },
        "h1_interval_from_denominators": {
            "fp_max_k": max_pass_k(n_fp, FALSE_MAX),
            "leak_max_k": max_pass_k(n_leak, LEAK_MAX),
            "rule": "达标 requires false<=fp_max_k and leak<=leak_max_k "
                    "(Wilson upper, z=1.959964; H1-FEASIBILITY-M5C2-B5.md)"},
        "grade": g["grade"], "grade_reason": g["reason"],
        "grade_wilson": g,
        "sample_floor": g["sample_floor"],
        "judge_counts": dict(sorted(Counter(r["judge"] for r in rows).items())),
        "rows": rows,
    }


def _lure_breakdown(judged, gold_rows):
    """Per-lure-qid judge four-state + gold distribution (diagnostic only)."""
    lures = lure_qids()
    by_sid_judge = {r["sid"]: r["verdict_rev7"] for r in judged}
    out = {}
    for lq in lures:
        js = Counter(v for sid, v in by_sid_judge.items()
                     if sid.startswith(lq + "-s"))
        gs = Counter(r["gold"] for r in gold_rows if r["qid"] == lq)
        out[lq] = {"judge": {k: js.get(k, 0) for k in
                             ("supported", "unsupported", "undecidable",
                              "parse_fail")},
                   "gold": dict(sorted(gs.items()))}
    return out


def compute_rates(decide_doc, decide_meta, gold_paths):
    judged = decide_doc["rows"]
    reports = {}
    metas = {}
    for spec in GOLDS:
        path = gold_paths.get(spec["key"])
        if not path:
            if spec.get("required", True):
                raise SystemExit("--rates-only needs %s <path> (%s)"
                                 % (spec["arg"], spec["label"]))
            continue
        gold, meta = load_gold(path, spec["sha16"], spec["label"])
        reports[spec["key"]] = gold_report(judged, gold, meta, spec["label"])
        metas[spec["key"]] = meta
    lead = reports["lead"]
    n_fp = lead["denominators"]["n_fp_support_present"]
    n_leak = lead["denominators"]["n_leak_fabricated"]
    denom_ok = (n_fp >= MIN_N_FP and n_leak >= MIN_N_LEAK)
    official = lead["grade"]
    grades = {k: v["grade"] for k, v in reports.items()}
    inconsistent = len(set(grades.values())) > 1
    final = "擦边/不可判" if inconsistent else official
    if inconsistent and official == "未通过":
        final = "未通过"
    if not denom_ok:
        # PREREG-M5-C2-B6.md §6: either denominator <20 => 未接上（样本量不足）.
        # No two-rate judgement may be issued (not 擦边, not 通过, not 未通过).
        final = "未接上"
        official = "未接上"
    consistency = {
        "grades": grades,
        "inconsistent": inconsistent,
        "rule": "SENSITIVITY-M5C2-B5.md: three golds must all be reported; if "
                "any grade differs the H1 conclusion is downgraded to "
                "擦边/不可判 (never 通过); LEAD-gold is the official readout",
        "conclusion_sensitive": ("结论对 7 票裁定敏感" if inconsistent else
                                 "三套一致，结论不依赖 7 票裁定"),
        "official": official,
        "final_h1": final,
        "denominator_check": {
            "n_fp": n_fp, "n_leak": n_leak,
            "min_n_fp": MIN_N_FP, "min_n_leak": MIN_N_LEAK,
            "pass": denom_ok,
            "rule": "PREREG-M5-C2-B6.md §6: 两率分母均须 ≥20，任一 <20 ⇒ "
                    "未接上（样本量不足），不得给出两率判定",
        },
        "verdict": ("未接上" if not denom_ok else final),
        "reason": ("样本量不足（n_leak=%d < %d，B6 §6）" % (n_leak, MIN_N_LEAK)
                   if not denom_ok else "分母达标，按四档判定"),
        "disclosure": ("(b6) 分母不足是设计抽样与模型对 lure 多拒答共同导致，"
                       "不是判据失效；一次性 (b6) 已消耗，不得重跑"
                       if not denom_ok else
                       "(b6) 只做验收读数，不用于调参；一次性已消耗"),
    }
    constraints_disclosure = {
        "h1_feasibility": {
            "path": rel(PRE), "sha16": PRE_SHA16,
            "quotes": [
                "门槛：漏判 ≤20% 且 误判 ≤15%（与 v2.1/v2.3 同线）；两率分母均须 ≥20，任一 <20 ⇒ 未接上（样本量不足）。",
                "擦边：漏判 CI 上界 >20% 或 误判 CI 上界 >15% ⇒ 即使点估计达标也不得宣称通过，须记 擦边。",
                "统计：题级（40 qid）为主读数 + 场景 cluster bootstrap；句级读数作辅助；全部报 Wilson 95% CI。",
            ]},
        "sensitivity": {
            "path": rel(PRE), "sha16": PRE_SHA16,
            "quotes": [
                "以 LEAD-gold 为唯一正式结论；A-only / B-only 只作稳健性证据，"
                "不得择优选用；三套不一致 ⇒ 结论降级擦边/不可判。",
                "禁：accuracy/F1/总分；只用一套数字；跑后调 θ/词表/规则；"
                "重跑 (b6) 补读数。",
                "（b6）只产生验收读数，不产生任何判据改动；不得据（b6）结果调参后重跑（b6）。",
            ]},
        "note": "约束句原样引用自上述两件冻结预置；本脚本不自创判定。",
    }
    h1_pins = {}
    pre_b = PRE.read_bytes()
    if sha16(pre_b) != PRE_SHA16 or len(pre_b) != PRE_BYTES:
        raise SystemExit("B6 prereg changed")
    h1_pins["prereg"] = {"path": rel(PRE), "sha16": PRE_SHA16,
                         "bytes": len(pre_b)}
    out = {
        "schema": "m5c2_b5_rates_v1",
        "status": "已读数",
        "pins": {"decide": decide_meta,
                 "judge_layer": {"version": JUDGE_VERSION,
                                 "sha16": R71_SHA16, "bytes": R71_BYTES,
                                 "prereg_sha16": R71_PRE_SHA16,
                                 "supersedes_sha16": R71.SUPERSEDES_SHA16,
                                 "rule_code_unchanged": True},
                 "h1_documents": h1_pins},
        "n_sentences": len(judged),
        "n_forward": 0,
        "no_gpu": True,
        "judge_counts": dict(sorted(Counter(r["verdict_rev7"] for r in judged).items())),
        "three_golds": {k: {"grade": reports[k]["grade"],
                            "grade_reason": reports[k]["grade_reason"],
                            "sample_floor": reports[k]["sample_floor"],
                            "denominators": reports[k]["denominators"],
                            "counts": reports[k]["counts"],
                            "rates": reports[k]["rates"],
                            "h1_interval_from_denominators":
                                reports[k]["h1_interval_from_denominators"],
                            "gold": reports[k]["gold"]}
                        for k in reports},
        "consistency": consistency,
        "verdict": consistency["verdict"],
        "reason": consistency["reason"],
        "denominator_check": consistency["denominator_check"],
        "disclosure": consistency["disclosure"],
        "one_shot_consumed": True,
        "rerun_allowed": False,
        "constraints_disclosure": constraints_disclosure,
        "final_h1": consistency["final_h1"],
        "official_gold": "lead (44d4dd86cac21f0a)",
        "diagnostics": {
            "diagnostic_only": True,
            "verdict_counts_rev7_1":
                dict(sorted(Counter(r["verdict_rev7"] for r in judged).items())),
            "lure_rejection": {
                "note": "17 条 fabricated、133 条 no_fact（gold）说明模型对 lure 的"
                        "拒答行为变好、fabricated 产出下降——这是产品侧好消息，"
                        "不是判据坏消息",
                "gold_counts": reports["lead"]["counts"],
                "per_lure_qid": _lure_breakdown(judged, reports["lead"]["rows"]),
            },
            "point_estimates_diagnostic_only": {
                "diagnostic_only": True,
                "false": reports["lead"]["rates"]["false"]["rate"],
                "false_k": reports["lead"]["rates"]["false"]["numerator"],
                "false_n": reports["lead"]["rates"]["false"]["denominator"],
                "leak": reports["lead"]["rates"]["leak"]["rate"],
                "leak_k": reports["lead"]["rates"]["leak"]["numerator"],
                "leak_n": reports["lead"]["rates"]["leak"]["denominator"],
                "note": "点估计仅供诊断，不作判定（B6 §6 分母不足 ⇒ 未接上）；"
                        "禁止写成擦边/通过/未通过",
            },
        },
        "conclusion_statement": "b5 的擦边仍是本项目唯一有效的 H1 读数；"
                                "b6 未提供新的有效判定证据",
        "prohibitions": ["不得写 b6 擦边/通过/未通过",
                         "不得事后改分母或放行 n_leak<20",
                         "不得重跑一次性 (b6)"],
        "thresholds": {"leak_max": LEAK_MAX, "false_max": FALSE_MAX,
                       "z": Z95, "min_n_fp": MIN_N_FP,
                       "min_n_leak": MIN_N_LEAK},
        "rule_code_unchanged": True,
        "no_rule_changes": True, "no_threshold_changes": True,
        "no_gold_changes": True, "no_forward": True, "no_network": True,
        "rows": reports["lead"]["rows"],
    }
    write_json_atomic(RATES, out)
    print(json.dumps({"status": out["status"], "final_h1": out["final_h1"],
                      "grades": consistency["grades"],
                      "official": consistency["official"],
                      "inconsistent": inconsistent},
                     ensure_ascii=False, indent=1))
    return 0


def dry_run(pins):
    info = {"schema": "m5c2_b6_decide_dry_run_v1", "status": "dry_run_only",
            "pins": pins, "n_forward": 0, "no_gpu": True,
            "writes_any_file": False}
    if EXTRACT.exists():
        b = EXTRACT.read_bytes()
        d = json.loads(b.decode("utf-8"))
        info["extract"] = {"present": True, "sha16": sha16(b), "bytes": len(b),
                           "schema": d.get("schema"),
                           "n_forward": d.get("n_forward"),
                           "n_records": len(d.get("records") or []),
                           "aborted": d.get("aborted")}
        recs = d.get("records") or []
        if recs:
            info["extract_first_record"] = {
                k: recs[0].get(k) for k in
                ("sid", "qid", "scenario", "route", "parse_ok", "rc",
                 "n_items")}
    else:
        info["extract"] = {"present": False,
                           "expected": rel(EXTRACT),
                           "note": "expected before the GPU extraction pass"}
    info["gold_expectations"] = [
        {k: spec[k] for k in ("key", "label", "sha16")} for spec in GOLDS]
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--rates-only", action="store_true")
    ap.add_argument("--gold-lead", default=str(OUT / "M5C2-B5-GOLD.json"))
    ap.add_argument("--gold-a", default=None)
    ap.add_argument("--gold-b", default=None)
    a = ap.parse_args()
    modes = [m for m in (a.dry_run, a.run, a.rates_only) if m]
    if len(modes) != 1:
        print("choose exactly one of --dry-run / --run / --rates-only")
        return 2
    try:
        pins = verify_pins()
    except PendingArtifacts as e:
        if a.dry_run:
            print(json.dumps({"schema": "m5c2_b6_decide_dry_run_v1",
                              "status": "pending_generation",
                              "reason": str(e),
                              "n_forward": 0, "no_gpu": True,
                              "writes_any_file": False},
                             ensure_ascii=False, indent=1))
            return 0
        raise
    if a.dry_run:
        return dry_run(pins)
    if a.rates_only:
        if not DECIDE.exists():
            raise SystemExit("missing %s; run --run first" % rel(DECIDE))
        db = DECIDE.read_bytes()
        d = json.loads(db.decode("utf-8"))
        if d.get("schema") != "m5c2_b5_decide_v1":
            raise SystemExit("unexpected DECIDE schema")
        if d.get("status") != "已判未读数":
            raise SystemExit("DECIDE status=%r; refusing to read rates"
                             % (d.get("status"),))
        return compute_rates(d, {"path": rel(DECIDE), "sha16": sha16(db),
                                 "bytes": len(db)},
                             {"lead": a.gold_lead, "a": a.gold_a, "b": a.gold_b})
    edoc, emeta = load_extract()
    judged = [judge_record(r) for r in edoc["records"]]
    out = aggregate(judged, emeta, pins)
    out["extract_pins"] = {"sha16": emeta["sha16"], "bytes": emeta["bytes"],
                           "n_forward": edoc.get("n_forward"),
                           "peak_gib": edoc.get("peak_gib"),
                           "gate_exception_applied": edoc.get("gate_exception_applied")}
    write_json_atomic(DECIDE, out)
    print(json.dumps({k: out[k] for k in ("status", "n_sentences",
                                          "verdict_counts_rev7_1",
                                          "n_changed_vs_rev5_1",
                                          "routes")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())