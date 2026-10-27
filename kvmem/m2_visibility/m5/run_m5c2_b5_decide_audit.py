#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B5 decide AUDIT — independent second implementation (CPU only).

Role: a *second*, independent judgment pass over the frozen B5 sentence set /
frozen extraction artifact.  It reuses the frozen rev7.1 judge functions by
import (R71.judge_row_rev7) and never copies or re-implements N1-N4/R4+/rules.

Inputs (read-only):
  out/M5C2-B5-EXTRACT.json        (preferred; rev7-impl GPU extraction artifact)
                                  fallback -> out/M5C2-B5-GEN.json +
                                  out/M5C2-B5-SENTENCES.json (skeleton mode:
                                  no items, no verdicts, pipeline validated only)
  kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py   88256d274c9993cc
  docs/_work/PREREG-M5-C2-REV7.1.md                   09d6f1b163ea0b84
  out/M5C2-B5-SENTENCES.json                          ba92635c8ad0c410
  out/M5C2-B5-GOLD.json                               54aa3da53c45da69  (LEAD gold)
  out/M5C2-B5-BLIND-A.json                            f74d6045c0b582d0  (A-only gold)
  out/M5C2-B5-BLIND-B.json                            1eaf701eb3e458fa  (B-only gold)

Output: out/M5C2-B5-DECIDE-AUDIT.json  (deterministic, no timestamps, indent=1,
ensure_ascii=False, one trailing newline):
  pins / extraction source / per-sentence verdict / 4-state verdict counts /
  item 4-state counts / three gold sets each with FP + leak + denominators +
  Wilson upper bound (z=1.959964) + 4-band decision / gold agreement /
  optional diff vs rev7-impl out/M5C2-B5-DECIDE.json (diff=0 required).

Modes:
  (default)      decide over EXTRACT if present, else skeleton from GEN+SENT
  --smoke-b4     CPU-only vertical smoke test: re-judge the frozen B4
                 extraction (M5B4-JUDGE.json, items only) with rev7.1 and
                 compare per-sid verdicts against M5C2-REV7-1-OFFLINE.json;
                 expected FP 2/46, leak 4/41, parse_fail 1/261.
  --compare P    compare against a rev7-impl DECIDE artifact at path P
                 (default: out/M5C2-B5-DECIDE.json when it exists)

NO GPU, no model, no network, no forward.  Does not write or modify any frozen
file and does not touch rev7-impl scripts/artifacts.
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
sys.path.insert(0, str(M5))

import run_m5c2_rev5_1_offline as R51  # noqa: E402  rev5.1 archive layer
import run_m5c2_rev5_offline as R5    # noqa: E402  derived_plus
import run_m5c2_rev7_1_offline as R71  # noqa: E402  N1-N4 judge (reused verbatim)

# ---------------------------------------------------------------- pins ------
PRE71 = ROOT / "docs/_work/PREREG-M5-C2-REV7.1.md"
PRE71_SHA16, PRE71_BYTES = "09d6f1b163ea0b84", 16313
CODE71 = M5 / "run_m5c2_rev7_1_offline.py"
CODE71_SHA16, CODE71_BYTES = "88256d274c9993cc", 50618
SENT = OUT / "M5C2-B5-SENTENCES.json"
SENT_SHA16, SENT_BYTES = "ba92635c8ad0c410", 116566
GEN = OUT / "M5C2-B5-GEN.json"
GEN_SHA16, GEN_BYTES = "2b63a02463994c03", 68184
EXTRACT = OUT / "M5C2-B5-EXTRACT.json"
DECIDE = OUT / "M5C2-B5-DECIDE.json"
GOLD_FILES = {
    "LEAD": (OUT / "M5C2-B5-GOLD.json", "54aa3da53c45da69", 64148),
    "A_only": (OUT / "M5C2-B5-BLIND-A.json", "f74d6045c0b582d0", 21266),
    "B_only": (OUT / "M5C2-B5-BLIND-B.json", "1eaf701eb3e458fa", 22024),
}
ART = OUT / "M5C2-B5-DECIDE-AUDIT.json"

# Frozen decision basis (LEAD-frozen 2026-10-26T22:42): H1 credibility +
# three-gold sensitivity.  The audit must obey these, never invent thresholds.
H1_MD = ROOT / "docs/_work/H1-FEASIBILITY-M5C2-B5.md"
H1_MD_SHA16, H1_MD_BYTES = "b514f3bdfa7a0b46", 2024
H1_JSON = OUT / "H1-FEASIBILITY-M5C2-B5-FREEZE.json"
H1_JSON_SHA16, H1_JSON_BYTES = "dcd9b7fc7d6827d5", 730
SENS_MD = ROOT / "docs/_work/SENSITIVITY-M5C2-B5.md"
SENS_MD_SHA16, SENS_MD_BYTES = "02f5927c9bb507d8", 1763
SENS_JSON = OUT / "SENSITIVITY-M5C2-B5-FREEZE.json"
SENS_JSON_SHA16, SENS_JSON_BYTES = "0a387bebb70de59a", 567
EXTRACT_SHA16, EXTRACT_BYTES = "93505eecc539634a", 444613
PASS_REGION = "FP<=4/72 and leak<=1/29"
BOUNDS = {"fp_4_72": "13.43%", "fp_5_72": "15.25%",
          "leak_1_29": "17.18%", "leak_2_29": "21.96%"}

B4_JUDGE = OUT / "M5B4-JUDGE.json"
B4_JUDGE_SHA16, B4_JUDGE_BYTES = "6a3001b6ca23ef7d", 452456
B4_GOLD = OUT / "M5B4-LEAD-RULING.json"
B4_GOLD_SHA16, B4_GOLD_BYTES = "9273ebc97aa1413a", 13195
B4_REV71 = OUT / "M5C2-REV7-1-OFFLINE.json"
B4_REV71_SHA16, B4_REV71_BYTES = "55191eaf2426f736", 510508

WILSON_Z = 1.959964
LEAK_MAX = 0.20
FALSE_MAX = 0.15
N_FP_MIN = 25          # frozen H1/SENS sample floor for the FP denominator
N_LEAK_MIN = 20        # frozen H1/SENS sample floor for the leak denominator
MIN_PER_RATE = 20      # legacy alias (kept for readability)
STATES = ("supported", "unsupported", "undecidable", "parse_fail")
GOLD_STATES = ("support_present", "fabricated", "no_fact", "undecidable")
BANDS = ("达标", "擦边", "未通过", "未通过（漏判越线）", "未接上（样本量不足）")

JUDGE_IMPORT_SHA = "88256d274c9993cc"


# ------------------------------------------------------------- helpers ------
def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def die(msg, code=2):
    print(json.dumps({"status": "FAIL", "reason": msg}, ensure_ascii=False))
    raise SystemExit(code)


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def _rel(path):
    """Repo-relative POSIX path when inside ROOT, else absolute string."""
    try:
        return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(Path(path))


def pinned(path, sha, size, label):
    b = Path(path).read_bytes()
    if sha16(b) != sha or len(b) != size:
        die("%s pin mismatch: got %s/%d expected %s/%d"
            % (label, sha16(b), len(b), sha, size))
    return b


def wilson(k, n, z=WILSON_Z):
    if n <= 0:
        return [0.0, 0.0]
    p = k / float(n)
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(max(0.0, center - half), 6),
            round(min(1.0, center + half), 6)]


def rate_obj(k, n):
    ci = wilson(k, n)
    return {"numerator": k, "denominator": n,
            "rate": round(k / n, 6) if n else None,
            "wilson95": ci, "wilson_upper": ci[1]}


def max_pass_k(n, threshold):
    """Largest k whose Wilson upper bound still <= threshold (frozen H1 table)."""
    if n <= 0:
        return None
    k = 0
    best = 0
    while k <= n:
        if wilson(k, n)[1] <= threshold:
            best = k
        k += 1
    return best


def decide_band(fp, leak):
    """PREREG-M5-C2-B5.md section 6 / 9.4; sample floor per SENSITIVITY §3.4."""
    if fp["denominator"] < N_FP_MIN or leak["denominator"] < N_LEAK_MIN:
        return "未接上（样本量不足）"
    if fp["rate"] is None or leak["rate"] is None:
        return "未接上（样本量不足）"
    if fp["rate"] > FALSE_MAX:
        return "未通过"
    if leak["rate"] > LEAK_MAX:
        return "未通过（漏判越线）"
    if fp["wilson_upper"] > FALSE_MAX or leak["wilson_upper"] > LEAK_MAX:
        return "擦边"
    return "达标"


# --------------------------------------------------------------- inputs -----
def verify_pins():
    pinned(PRE71, PRE71_SHA16, PRE71_BYTES, "PREREG-M5-C2-REV7.1.md")
    pinned(CODE71, CODE71_SHA16, CODE71_BYTES, "run_m5c2_rev7_1_offline.py")
    pinned(SENT, SENT_SHA16, SENT_BYTES, "M5C2-B5-SENTENCES.json")
    pinned(GEN, GEN_SHA16, GEN_BYTES, "M5C2-B5-GEN.json")
    if sha16(Path(R71.__file__).read_bytes()) != JUDGE_IMPORT_SHA:
        die("imported judge module is not the frozen rev7.1 code")
    if R71.CORRECTION_TYPE != "statement_correction" \
            or R71.RULE_CODE_UNCHANGED is not True:
        die("rev7.1 statement-correction pins are not valid")
    pinned(H1_MD, H1_MD_SHA16, H1_MD_BYTES, "H1-FEASIBILITY-M5C2-B5.md")
    pinned(H1_JSON, H1_JSON_SHA16, H1_JSON_BYTES,
           "H1-FEASIBILITY-M5C2-B5-FREEZE.json")
    pinned(SENS_MD, SENS_MD_SHA16, SENS_MD_BYTES, "SENSITIVITY-M5C2-B5.md")
    pinned(SENS_JSON, SENS_JSON_SHA16, SENS_JSON_BYTES,
           "SENSITIVITY-M5C2-B5-FREEZE.json")
    h1 = json.loads(H1_JSON.read_text(encoding="utf-8"))
    sens = json.loads(SENS_JSON.read_text(encoding="utf-8"))
    if h1.get("pass_region") != PASS_REGION or not h1.get("frozen"):
        die("H1 feasibility freeze is not the frozen pass region")
    if sens.get("mandatory_reporting") != \
            "三套各报；不一致必降级，禁择优；LEAD-gold 为唯一正式结论":
        die("sensitivity freeze wording changed")
    gold_meta = {}
    for name, (path, sha, size) in GOLD_FILES.items():
        pinned(path, sha, size, path.name)
        gold_meta[name] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                           "sha16": sha, "bytes": size}
    return {
        "judge_layer": {
            "version": "rev7.1",
            "prereg_sha16": PRE71_SHA16,
            "prereg_bytes": PRE71_BYTES,
            "code_sha16": CODE71_SHA16,
            "code_bytes": CODE71_BYTES,
            "supersedes_sha16": R71.SUPERSEDES_SHA16,
            "correction_type": R71.CORRECTION_TYPE,
            "rule_code_unchanged": True,
            "imported_not_copied": True,
            "judge_entry": "R71.judge_row_rev7",
        },
        "sentences": {"path": "kvmem/m2_visibility/m5/out/M5C2-B5-SENTENCES.json",
                      "sha16": SENT_SHA16, "bytes": SENT_BYTES},
        "gen": {"path": "kvmem/m2_visibility/m5/out/M5C2-B5-GEN.json",
                "sha16": GEN_SHA16, "bytes": GEN_BYTES},
        "gold_files": gold_meta,
        "decision_basis": {
            "h1_feasibility": {
                "md": {"path": "docs/_work/H1-FEASIBILITY-M5C2-B5.md",
                       "sha16": H1_MD_SHA16, "bytes": H1_MD_BYTES},
                "freeze_json": {"path": "kvmem/m2_visibility/m5/out/"
                                        "H1-FEASIBILITY-M5C2-B5-FREEZE.json",
                                "sha16": H1_JSON_SHA16,
                                "bytes": H1_JSON_BYTES},
                "pass_region": PASS_REGION,
                "wilson_z": 1.959964,
                "bounds": BOUNDS,
                "sample_floor": {"n_fp_min": N_FP_MIN, "n_leak_min": N_LEAK_MIN,
                                 "rule": "任一 gold 下 n_fp<25 或 n_leak<20 "
                                         "=> 未接上（样本量不足）"},
                "rule": "达标 <=> Wilson 上界<=阈值（FP 15%、漏判 20%）；"
                        "点估计<=阈值但上界越线 => 擦边；点估计越线 => 未通过",
            },
            "sensitivity": {
                "md": {"path": "docs/_work/SENSITIVITY-M5C2-B5.md",
                       "sha16": SENS_MD_SHA16, "bytes": SENS_MD_BYTES},
                "freeze_json": {"path": "kvmem/m2_visibility/m5/out/"
                                        "SENSITIVITY-M5C2-B5-FREEZE.json",
                                "sha16": SENS_JSON_SHA16,
                                "bytes": SENS_JSON_BYTES},
                "gold_variants": sens.get("gold_variants"),
                "mandatory_reporting": sens.get("mandatory_reporting"),
                "no_cherry_pick": True,
                "lead_gold_is_formal": True,
            },
            "not_threshold_change": True,
        },
    }


def load_sentences():
    rows = json.loads(SENT.read_text(encoding="utf-8"))["sentences"]
    if len(rows) != 326:
        die("expected 326 frozen B5 sentences, got %d" % len(rows))
    return rows


def _label_map(obj):
    if isinstance(obj.get("gold"), dict) and obj["gold"]:
        return dict(obj["gold"])
    labels = obj.get("labels")
    if isinstance(labels, list) and labels and isinstance(labels[0], dict):
        out = {}
        for x in labels:
            lab = x.get("gold_label") or x.get("label") or x.get("state")
            if lab:
                out[x["sid"]] = lab
        if out:
            return out
    die("cannot read gold labels from file")
    return {}


def load_golds(sids):
    golds = {}
    meta = {}
    for name, (path, sha, size) in GOLD_FILES.items():
        obj = json.loads(path.read_text(encoding="utf-8"))
        m = _label_map(obj)
        if set(m) != set(sids):
            die("%s gold sid set mismatch (missing=%d extra=%d)"
                % (name, len(set(sids) - set(m)), len(set(m) - set(sids))))
        bad = [s for s in m if m[s] not in GOLD_STATES]
        if bad:
            die("%s gold has unknown labels %s" % (name, bad[:3]))
        golds[name] = m
        meta[name] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                      "sha16": sha, "bytes": size, "n": len(m),
                      "counts": {g: sum(1 for v in m.values() if v == g)
                                 for g in GOLD_STATES}}
    return golds, meta


def _norm_rows(doc):
    if isinstance(doc, list):
        return doc
    for key in ("records", "items", "sentences", "results", "rows",
                "extractions"):
        if isinstance(doc.get(key), list) and doc[key]:
            return doc[key]
    die("cannot locate per-sentence rows in extraction artifact")
    return []


def load_extract(rows_sent, path=None):
    """Load rev7-impl EXTRACT if it exists; otherwise return None (skeleton)."""
    src_path = Path(path) if path else EXTRACT
    if not src_path.exists():
        return None
    doc = json.loads(src_path.read_text(encoding="utf-8"))
    if doc.get("schema") != "m5c2_b5_extract_v1":
        die("unexpected EXTRACT schema %r" % (doc.get("schema"),))
    if doc.get("aborted") is not None:
        die("EXTRACT aborted=%r; refusing partial extraction"
            % (doc.get("aborted"),))
    if int(doc.get("n_forward") or 0) != 326:
        die("EXTRACT n_forward=%r != 326" % (doc.get("n_forward"),))
    if doc.get("no_verdict") is not True or doc.get("no_rates") is not True:
        die("EXTRACT is not a verdict-free/rates-free extraction artifact")
    if path is None:
        b = src_path.read_bytes()
        if sha16(b) != EXTRACT_SHA16 or len(b) != EXTRACT_BYTES:
            die("EXTRACT pin mismatch: got %s/%d expected %s/%d"
                % (sha16(b), len(b), EXTRACT_SHA16, EXTRACT_BYTES))
    raw_rows = _norm_rows(doc)
    by_sid = {}
    for r in raw_rows:
        sid = r.get("sid")
        if not sid:
            continue
        by_sid[sid] = r
    sent_by_sid = {r["sid"]: r for r in rows_sent}
    out = []
    for sid, sent in sent_by_sid.items():
        r = by_sid.get(sid)
        if r is None:
            die("EXTRACT is missing sentence %s" % sid)
        sentence = r.get("sentence") or r.get("text") or sent["text"]
        source = r.get("source_text") or sent["source_text"]
        parse_ok = r.get("parse_ok")
        if parse_ok is None:
            parse_ok = r.get("parse") == "ok" or bool(r.get("items"))
        items = r.get("items")
        if items is None and isinstance(r.get("pairs"), list):
            items = [{"item": x.get("item"), "evidence": x.get("evidence")}
                     for x in r["pairs"]]
        if items is None:
            raw = r.get("raw_out") or r.get("raw") or ""
            import run_m5c2_rev4_1 as _R41  # local import: parse fallback only
            items, parse_ok2, _reason = _R41.parse_extraction(raw, source)
            parse_ok = parse_ok2
        items = [{"item": str(z.get("item", "")),
                  "evidence": str(z.get("evidence", ""))}
                 for z in (items or []) if isinstance(z, dict)]
        route = r.get("route") or "model_extract"
        layer0 = r.get("layer0")
        if route == "abstain_check" and not isinstance(layer0, dict):
            import run_m5c2_rev4 as _R4
            layer0 = _R4.deterministic_abstain(sentence, source)
        if route == "empty_source" and not isinstance(layer0, dict):
            layer0 = {"route": "empty_source"}
        out.append({
            "sid": sid, "qid": r.get("qid") or sent["qid"],
            "scenario": r.get("scenario") or sent["scenario"],
            "source_text": source, "question": r.get("question") or sent["question"],
            "sentence": sentence,
            "items": items,
            "parse_ok": bool(parse_ok),
            "parse_reason": r.get("parse_reason") or r.get("reason"),
            "route": route,
            "layer0": layer0,
            "derived": r.get("derived"),
            "raw_out": r.get("raw_out") or r.get("raw"),
        })
    return {"source": "EXTRACT",
            "path": _rel(src_path),
            "sha16": sha16(src_path.read_bytes()),
            "bytes": src_path.stat().st_size,
            "schema": doc.get("schema"),
            "n_forward": doc.get("n_forward"),
            "aborted": doc.get("aborted"),
            "peak_gib": doc.get("peak_gib"),
            "target_gib": doc.get("target_gib"),
            "fuse_gib": doc.get("fuse_gib"),
            "n_rows": len(out),
            "n_with_items": sum(1 for r in out if r["items"]),
            "n_parse_ok": sum(1 for r in out if r["parse_ok"]),
            "rows": out}


def skeleton_rows(rows_sent):
    return {"source": "skeleton(GEN+SENTENCES)", "sha16": None, "bytes": None,
            "n_rows": len(rows_sent), "n_with_items": 0, "n_parse_ok": 0,
            "rows": [{
                "sid": r["sid"], "qid": r["qid"], "scenario": r["scenario"],
                "source_text": r["source_text"], "question": r["question"],
                "sentence": r["text"], "items": [], "parse_ok": False,
                "parse_reason": "skeleton_no_extraction_yet",
                "route": "pending_extract", "derived": None, "raw_out": None,
            } for r in rows_sent]}


# -------------------------------------------------------------- decide -----
def judge_one(row):
    """One sentence through the frozen rev7.1 judge function."""
    if row["route"] == "pending_extract":
        return {"verdict": None, "items": [], "counts": {},
                "verdict_rev5_1_archive": None, "note": "pending_extract"}
    items = row["items"]
    items51 = R51.judge_items(items, row["source_text"]) if row["parse_ok"] else []
    en, _dd51 = R5.derived_plus(row["sentence"], row["source_text"])
    if row["route"] == "empty_source":
        items51 = []
        v51 = "unsupported"
    elif row["route"] == "abstain_check":
        items51 = []
        v51 = (row.get("layer0") or {}).get("verdict") or "abstain_ok"
    elif not row["parse_ok"]:
        v51 = "parse_fail"
    elif en:
        v51 = "undecidable"
    elif not items51:
        v51 = "undecidable"
    elif any(z["absent"] for z in items51):
        v51 = "unsupported"
    else:
        v51 = "supported"
    payload = {
        "sid": row["sid"], "sentence": row["sentence"],
        "source_text": row["source_text"], "items": items,
        "route": row["route"], "parse_ok": row["parse_ok"],
        "derived": bool(en), "verdict": v51,
        "layer0": row.get("layer0"),
    }
    sent_rec, item_recs, _dd = R71.judge_row_rev7(payload)
    counts = {}
    for z in item_recs:
        counts[z["item_verdict"]] = counts.get(z["item_verdict"], 0) + 1
    return {"verdict": sent_rec["verdict_rev7"],
            "verdict_rev5_1_archive": v51,
            "items": item_recs, "counts": counts,
            "n_items": sent_rec["n_items"], "n_invalid": sent_rec["n_invalid"],
            "n_absent": sent_rec["n_absent"],
            "n_unverified": sent_rec["n_unverified"],
            "changed_vs_rev5_1": sent_rec["changed"],
            "derived": bool(sent_rec["derived_rev7"])}


def rates_for_gold(gold, judged, sids):
    support = [s for s in sids if gold[s] == "support_present"]
    fab = [s for s in sids if gold[s] == "fabricated"]
    other = [s for s in sids if gold[s] not in ("support_present", "fabricated")]
    fp_sids = [s for s in support if judged[s] == "unsupported"]
    leak_sids = [s for s in fab if judged[s] in ("supported", "undecidable")]
    strict_leak = [s for s in fab if judged[s] == "supported"]
    fp = rate_obj(len(fp_sids), len(support))
    leak = rate_obj(len(leak_sids), len(fab))
    return {
        "gold_counts": {g: sum(1 for s in sids if gold[s] == g)
                        for g in GOLD_STATES},
        "false_positive": dict(fp, sids=sorted(fp_sids), threshold_max=FALSE_MAX),
        "leak_missed": dict(leak, sids=sorted(leak_sids), threshold_max=LEAK_MAX),
        "strict_leak_supported": {"k": len(strict_leak), "n": len(fab),
                                  "rate": round(len(strict_leak) / len(fab), 6)
                                  if fab else None,
                                  "sids": sorted(strict_leak)},
        "n_other_gold": len(other),
        "h1_pass_region": {
            "pass_region_rule": PASS_REGION,
            "fp_max_k": max_pass_k(len(support), FALSE_MAX),
            "leak_max_k": max_pass_k(len(fab), LEAK_MAX),
            "fp_k": len(fp_sids),
            "leak_k": len(leak_sids),
            "fp_in_region": len(fp_sids) <= max_pass_k(len(support), FALSE_MAX),
            "leak_in_region": len(leak_sids) <= max_pass_k(len(fab), LEAK_MAX),
            "both_in_region": (len(fp_sids) <= max_pass_k(len(support), FALSE_MAX)
                               and len(leak_sids) <= max_pass_k(len(fab),
                                                              LEAK_MAX)),
        },
        "decision": decide_band(fp, leak),
        "h1": "误判<=15% 且 漏判<=20%（两率同时满足）；Wilson 上界越线记擦边",
    }


def _gold_agreement(golds, sids):
    a, b, lead = golds["A_only"], golds["B_only"], golds["LEAD"]
    agree_ab = [s for s in sids if a[s] == b[s]]
    return {
        "A_vs_B": {"agree": len(agree_ab), "n": len(sids),
                   "rate": round(len(agree_ab) / len(sids), 6),
                   "disagreements": sorted(set(sids) - set(agree_ab))},
        "A_vs_LEAD": {"agree": sum(1 for s in sids if a[s] == lead[s]),
                      "n": len(sids),
                      "rate": round(sum(1 for s in sids if a[s] == lead[s])
                                    / len(sids), 6)},
        "B_vs_LEAD": {"agree": sum(1 for s in sids if b[s] == lead[s]),
                      "n": len(sids),
                      "rate": round(sum(1 for s in sids if b[s] == lead[s])
                                    / len(sids), 6)},
    }


def cross_check_impl_rates(gold_rates):
    """Read-only consistency check against rev7-impl out/M5C2-B5-RATES.json."""
    rp = OUT / "M5C2-B5-RATES.json"
    if not rp.exists():
        return {"present": False, "equal": None,
                "note": "rev7-impl RATES artifact not on disk"}
    doc = json.loads(rp.read_text(encoding="utf-8"))
    impl = doc.get("three_golds") or {}

    def num(node, keys):
        for k in keys:
            if isinstance(node, dict) and k in node and node[k] is not None:
                node = node[k]
            else:
                return None
        return node

    checks = {}
    mapping = {"LEAD": "lead", "A_only": "a", "B_only": "b"}
    for mine, theirs in mapping.items():
        g = gold_rates.get(mine) or {}
        t = impl.get(theirs) or {}
        tr = t.get("rates") or {}
        pair = {}
        for label, mine_block, impl_block in (
                ("fp", g.get("false_positive"), tr.get("false")),
                ("leak", g.get("leak_missed"), tr.get("leak"))):
            pair[label] = {
                "audit_k": (mine_block or {}).get("numerator"),
                "audit_n": (mine_block or {}).get("denominator"),
                "impl_k": (impl_block or {}).get("numerator"),
                "impl_n": (impl_block or {}).get("denominator"),
                "audit_upper": (mine_block or {}).get("wilson_upper"),
                "impl_upper": num(impl_block, ("wilson95", "hi")),
            }
            pair[label]["equal"] = (
                pair[label]["audit_k"] == pair[label]["impl_k"]
                and pair[label]["audit_n"] == pair[label]["impl_n"]
                and pair[label]["audit_upper"] == pair[label]["impl_upper"])
        pair["grade_equal"] = g.get("decision") == t.get("grade")
        checks[mine] = pair
    all_equal = all(v[l]["equal"] for v in checks.values()
                    for l in ("fp", "leak")) and \
        all(v["grade_equal"] for v in checks.values())
    return {
        "present": True,
        "path": _rel(rp),
        "sha16": sha16(rp.read_bytes()),
        "impl_final_h1": doc.get("final_h1"),
        "impl_official_gold": doc.get("official_gold"),
        "per_gold": checks,
        "all_equal": all_equal,
        "note": "只读比对；不一致时以冻结预置复算为准并列入差异",
    }


def sensitivity_block(gold_rates):
    """Frozen SENSITIVITY rule: report all three, downgrade on disagreement."""
    decisions = {name: v["decision"] for name, v in gold_rates.items()}
    lead = decisions.get("LEAD")
    distinct = sorted(set(decisions.values()))
    bad = ("未通过", "未通过（漏判越线）")
    note = None
    final = lead
    if len(distinct) == 1:
        note = "三套 gold 判定一致，LEAD-gold 为唯一正式结论"
    elif any(d in bad for d in distinct):
        final = "不可判（三套 gold 分歧且含未通过，禁择优）"
        note = "三套 gold 跨越通过/未通过边界 => 不可判"
    elif lead == "达标":
        final = "擦边（降级：三套 gold 分歧）"
        note = "LEAD=达标 但 A/B 不一致 => 按冻结敏感性规则降级擦边"
    else:
        final = "擦边（降级：三套 gold 分歧）"
        note = "三套 gold 不一致 => 降级擦边，禁择优"
    return {
        "per_gold": decisions,
        "distinct": distinct,
        "consistent": len(distinct) == 1,
        "downgraded": final != lead,
        "formal_rule": "LEAD-gold 唯一正式结论；三套不一致必降级擦边/不可判，"
                       "禁择优 (SENSITIVITY-M5C2-B5 02f5927c)",
        "lead_gold_formal": lead,
        "final_conclusion": final,
        "note": note,
    }


def load_decide_verdicts(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for key in ("rows", "items", "sentences", "results", "decisions"):
        if isinstance(doc.get(key), list) and doc[key]:
            for r in doc[key]:
                if not isinstance(r, dict) or not r.get("sid"):
                    continue
                v = (r.get("verdict_rev7") or r.get("verdict")
                     or r.get("verdict_rev7_1") or r.get("label"))
                if v:
                    out[r["sid"]] = {"verdict": v, "route": r.get("route")}
            break
    if not out:
        die("cannot read per-sentence verdicts from DECIDE artifact %s" % path)
    return out, doc


# --------------------------------------------------------------- decide ----
def run_decide(compare_path, extract_path=None, out_path=None):
    pins = verify_pins()
    sent_rows = load_sentences()
    sids = [r["sid"] for r in sent_rows]
    golds, gold_meta = load_golds(sids)
    ext = load_extract(sent_rows, extract_path)
    skeleton = ext is None
    if skeleton:
        ext = skeleton_rows(sent_rows)

    per_sentence = []
    judged = {}
    verdict_counts = {s: 0 for s in STATES}
    other_counts = {}
    item_states = {"invalid": 0, "absent": 0, "unverified": 0, "present": 0}
    for row in ext["rows"]:
        j = judge_one(row)
        v = j["verdict"]
        judged[row["sid"]] = v
        if v is not None:
            verdict_counts[v] = verdict_counts.get(v, 0) + 1
        else:
            other_counts["pending_extract"] = \
                other_counts.get("pending_extract", 0) + 1
        for z in (j["items"] or []):
            item_states[z["item_verdict"]] = \
                item_states.get(z["item_verdict"], 0) + 1
        per_sentence.append({
            "sid": row["sid"], "qid": row["qid"], "scenario": row["scenario"],
            "route": row["route"], "parse_ok": row["parse_ok"],
            "n_items": j.get("n_items", 0),
            "n_invalid": j.get("n_invalid", 0),
            "n_absent": j.get("n_absent", 0),
            "n_unverified": j.get("n_unverified", 0),
            "verdict": v,
            "verdict_rev5_1_archive": j["verdict_rev5_1_archive"],
            "derived": j.get("derived", False),
        })

    gold_rates = {}
    for name, gold in golds.items():
        if skeleton:
            gold_rates[name] = {
                "gold_counts": {g: sum(1 for s in sids if gold[s] == g)
                                for g in GOLD_STATES},
                "false_positive": rate_obj(0, sum(1 for s in sids
                                                  if gold[s] == "support_present")),
                "leak_missed": rate_obj(0, sum(1 for s in sids
                                               if gold[s] == "fabricated")),
                "decision": "未接上（样本量不足）",
                "note": "skeleton: no extraction/verdicts yet",
            }
        else:
            gold_rates[name] = rates_for_gold(gold, judged, sids)

    compare = None
    cpath = Path(compare_path) if compare_path else DECIDE
    if not skeleton and cpath.exists():
        dv, doc = load_decide_verdicts(cpath)
        my_route = {r["sid"]: r["route"] for r in ext["rows"]}
        common = sorted(set(dv) & set(judged))
        diffs = [s for s in common if dv[s]["verdict"] != judged[s]]
        missing = sorted(set(judged) - set(dv))
        detail = [{"sid": s,
                   "audit_verdict": judged[s],
                   "decide_verdict": dv[s]["verdict"],
                   "audit_route": my_route.get(s),
                   "decide_route": dv[s]["route"]} for s in diffs[:200]]
        compare = {
            "decide_path": _rel(cpath),
            "decide_sha16": sha16(cpath.read_bytes()),
            "decide_status": doc.get("status"),
            "decide_schema": doc.get("schema"),
            "n_decide": len(dv), "n_audit": len(judged),
            "n_compared": len(common), "n_diff": len(diffs),
            "diff_zero": not diffs and not missing,
            "diff_sids": diffs[:200],
            "diff_detail": detail,
            "missing_in_decide": missing,
            "extra_in_decide": sorted(set(dv) - set(judged)),
            "counts_compare": {
                "audit_4state": {s: verdict_counts.get(s, 0) for s in STATES},
                "audit_abstain_ok": verdict_counts.get("abstain_ok", 0),
                "decide_verdict_counts_rev7_1":
                    doc.get("verdict_counts_rev7_1"),
            },
        }
    elif skeleton:
        compare = {"decide_path": None, "diff_zero": None,
                   "note": "skeleton mode: no verdicts to compare yet"}
    else:
        compare = {"decide_path": str(cpath.relative_to(ROOT)).replace("\\", "/"),
                   "present": False, "diff_zero": None,
                   "note": "rev7-impl DECIDE artifact not on disk yet"}

    out = {
        "schema": "m5c2_b5_decide_audit_v1",
        "status": "skeleton_no_extraction" if skeleton else "decided",
        "role": "independent second implementation (audit); CPU only",
        "pins": pins,
        "extraction": {
            "source": ext["source"],
            "path": ext.get("path"),
            "sha16": ext["sha16"],
            "bytes": ext["bytes"],
            "n_rows": ext["n_rows"],
            "n_with_items": ext["n_with_items"],
            "n_parse_ok": ext["n_parse_ok"],
        },
        "n_sentences": len(per_sentence),
        "verdict_distribution": dict(sorted(verdict_counts.items()))
        if not skeleton else None,
        "verdict_distribution_4state": ({s: verdict_counts.get(s, 0)
                                         for s in STATES}
                                        if not skeleton else None),
        "abstain_ok_count": (verdict_counts.get("abstain_ok", 0)
                             if not skeleton else None),
        "other_route_counts": other_counts if not skeleton else None,
        "n_forward": 0,
        "no_gpu": True,
        "no_model_loaded": True,
        "no_network": True,
        "item_states": item_states if not skeleton else None,
        "gold_sets": gold_rates,
        "h1_pass_region_check_lead": (None if skeleton else {
            "gold": "LEAD",
            "pass_region": PASS_REGION,
            "fp_max_k": gold_rates["LEAD"]["h1_pass_region"]["fp_max_k"],
            "leak_max_k": gold_rates["LEAD"]["h1_pass_region"]["leak_max_k"],
            "fp_k": gold_rates["LEAD"]["h1_pass_region"]["fp_k"],
            "leak_k": gold_rates["LEAD"]["h1_pass_region"]["leak_k"],
            "both_in_region": gold_rates["LEAD"]["h1_pass_region"][
                "both_in_region"],
            "band": gold_rates["LEAD"]["decision"],
            "note": "FP k 不在 pass region => 不写达标；点估计未越 15% => 记擦边"
                    "（H1-FEASIBILITY b514f3bd §3）",
        }),
        "diagnostics": (None if skeleton else {
            "item_states": item_states,
            "n_items": sum(len(r["items"] or []) for r in ext["rows"]),
            "invalid_ratio": round(item_states["invalid"] /
                                   max(1, sum(item_states.values())), 6),
            "unverified_ratio": round(
                item_states["unverified"] /
                max(1, sum(item_states.values())), 6),
            "n_parse_fail": verdict_counts.get("parse_fail", 0),
            "not_used_in_decision": "诊断项，不进 H1 判定",
        }),
        "cross_check_impl_rates": (None if skeleton
                                   else cross_check_impl_rates(gold_rates)),
        "diff_vs_decide": (None if skeleton else {
            "n_diff": compare.get("n_diff"),
            "diff_sids": compare.get("diff_sids"),
            "diff_zero": compare.get("diff_zero"),
            "note": "逐 sid 比对 rev7-impl DECIDE 的 verdict_rev7",
        }),
        "sensitivity": (None if skeleton
                        else sensitivity_block(gold_rates)),
        "formal_conclusion": (None if skeleton
                              else sensitivity_block(gold_rates)[
                                  "final_conclusion"]),
        "gold_files": gold_meta,
        "gold_agreement": _gold_agreement(golds, sids),
        "compare_vs_decide": compare,
        "per_sentence": per_sentence,
        "notes": [
            "verdict 由 R71.judge_row_rev7 直接产出，未复制任何规则代码。",
            "四档判定按 PREREG-M5-C2-B5.md §6/§9.4；Wilson z=1.959964。",
            "LEAD gold 与 A-only/B-only gold 均为只读输入，不参与判定。",
        ],
    }
    write_json_atomic(Path(out_path) if out_path else ART, out)
    print(json.dumps({
        "status": out["status"],
        "artifact": str(Path(out_path) if out_path else ART),
        "sha16": sha16((Path(out_path) if out_path else ART).read_bytes()),
        "verdict_distribution": out["verdict_distribution"],
        "gold_decisions": {k: v["decision"] for k, v in gold_rates.items()},
        "formal_conclusion": out["formal_conclusion"],
        "compare_diff_zero": compare.get("diff_zero"),
        "compare_n_diff": compare.get("n_diff"),
    }, ensure_ascii=False, indent=1))
    return 0 if (skeleton or (compare.get("diff_zero") is not False)) else 2


# -------------------------------------------------------------- smoke ------
def smoke_b4():
    """Vertical smoke test on frozen B4 extraction (CPU only)."""
    pinned(B4_JUDGE, B4_JUDGE_SHA16, B4_JUDGE_BYTES, "M5B4-JUDGE.json")
    pinned(B4_GOLD, B4_GOLD_SHA16, B4_GOLD_BYTES, "M5B4-LEAD-RULING.json")
    rows = json.loads(B4_JUDGE.read_text(encoding="utf-8"))["items"]
    gold = json.loads(B4_GOLD.read_text(encoding="utf-8"))["gold"]
    if len(rows) != 261 or set(gold) != {r["sid"] for r in rows}:
        die("B4 smoke inputs are not the expected 261 rows")
    judged = {}
    dist = {s: 0 for s in STATES}
    n_items = 0
    n_invalid = 0
    for r in rows:
        payload = {
            "sid": r["sid"], "sentence": r["sentence"],
            "source_text": r["source_text"],
            "items": [{"item": z["item"], "evidence": z["evidence"]}
                      for z in r["items"]],
            "route": r["route"], "parse_ok": r["parse_ok"],
            "derived": bool(r["derived"]), "verdict": r["verdict"],
            "layer0": r.get("layer0"),
        }
        sent_rec, item_recs, _dd = R71.judge_row_rev7(payload)
        v = sent_rec["verdict_rev7"]
        judged[r["sid"]] = v
        dist[v] = dist.get(v, 0) + 1
        n_items += len(item_recs)
        n_invalid += sum(1 for z in item_recs if not z["valid"])
    support = [s for s in judged if gold[s] == "support_present"]
    fab = [s for s in judged if gold[s] == "fabricated"]
    fp = [s for s in support if judged[s] == "unsupported"]
    leak = [s for s in fab if judged[s] in ("supported", "undecidable")]
    pf = [s for s in judged if judged[s] == "parse_fail"]
    res = {
        "status": "smoke_ok",
        "rows": len(rows),
        "verdict_distribution": dist,
        "false_positive": {"k": len(fp), "n": len(support), "sids": sorted(fp)},
        "leak_missed": {"k": len(leak), "n": len(fab), "sids": sorted(leak)},
        "parse_fail": {"k": len(pf), "sids": sorted(pf)},
        "items": {"n_items": n_items, "n_invalid": n_invalid},
        "expected": {"false_positive": "2/46", "leak_missed": "4/41",
                     "parse_fail": "1/261"},
        "matches_expected": (len(fp) == 2 and len(leak) == 4 and len(pf) == 1),
    }
    if B4_REV71.exists():
        pinned(B4_REV71, B4_REV71_SHA16, B4_REV71_BYTES,
               "M5C2-REV7-1-OFFLINE.json")
        off = json.loads(B4_REV71.read_text(encoding="utf-8"))
        stored = {}
        for key in ("sentences", "items", "rows", "results"):
            if isinstance(off.get(key), list) and off[key] \
                    and isinstance(off[key][0], dict) and "verdict_rev7" in off[key][0]:
                stored = {r["sid"]: r["verdict_rev7"] for r in off[key]}
                break
        diffs = sorted(s for s in stored if stored[s] != judged.get(s))
        res["compare_vs_rev7_1_artifact"] = {
            "artifact_sha16": B4_REV71_SHA16,
            "n_compared": len(stored), "n_diff": len(diffs),
            "diff_zero": not diffs, "diff_sids": diffs[:50],
        }
        res["matches_expected"] = bool(res["matches_expected"] and not diffs)
    res["status"] = "smoke_ok" if res["matches_expected"] else "smoke_FAIL"
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["matches_expected"] else 3


# ---------------------------------------------------------------- main -----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke-b4", action="store_true")
    ap.add_argument("--compare", default=None)
    ap.add_argument("--extract", default=None,
                    help="override extraction artifact path (debug)")
    ap.add_argument("--out", default=None,
                    help="override output path (debug)")
    a = ap.parse_args()
    if a.smoke_b4:
        return smoke_b4()
    return run_decide(a.compare, a.extract, a.out)


if __name__ == "__main__":
    sys.exit(main())