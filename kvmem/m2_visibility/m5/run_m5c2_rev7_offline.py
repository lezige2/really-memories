#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 REV7 offline: judge-layer recompute with the four frozen fixes.

Frozen prereg: docs/_work/PREREG-M5-C2-REV7.md
  sha16=32eaf82ca56600c4 / 5,835 B / 88 lines / frozen=true / frozen_rev=1
Inputs (byte-verified, never modified):
  out/M5B4-JUDGE.json        6a3001b6ca23ef7d / 452,456 B  (rev5.1 items, 261 rows)
  out/M5B4-LEAD-RULING.json  9273ebc97aa1413a /  13,195 B  (gold)
  out/M5B4-SENTENCES.json    c349ca5a93192aac /  99,636 B  (cross-check only)

ZERO GPU, ZERO model forwards, ZERO network.  Every judged quantity is
deterministically recomputed from the items[] already stored in
M5B4-JUDGE.json; the frozen model output is never re-generated.

Fixes implemented literally from PREREG-M5-C2-REV7.md section 2:
  N1  normalize7(): NFKC -> thousands-separator strip -> whitespace strip.
      Every comparison in R1/R2/R3/R4+ uses normalize7.
  N2  value_tokens(): 4 pure-value regexes unchanged; the old greedy entity
      regex `[^\\s，。]{2,}(?:公司|店|院|馆|中心)` is DELETED and replaced by the
      non-greedy, pronoun-prefix-excluded capture group 1 form.  An entity
      token participates in R1 only if normalize7(token) is a substring of
      normalize7(source); otherwise it is treated as a descriptor and left to
      R4+ evidence verification.
  N3  item atomicity gate: valid = normalize7(item) in normalize7(sentence)
      OR R5.window_coverage(normalize7(item), normalize7(sentence)) >= 0.90.
      Invalid items take no part in aggregation, produce no absent, and are
      not counted as unverified.
  N4  absent-marker scope: R3 fires only on valid items.

output: out/M5C2-REV7-OFFLINE.json  (deterministic, no timestamps, indent=1,
        ensure_ascii=False, one trailing newline)

Run:  python -X utf8 kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py
"""
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
sys.path.insert(0, str(M5))

# Only pure offline judge modules are imported (no engine / no GPU runner /
# no run_m5c2_b4_judge).  run_m5c2_rev4_1 is the R1 helper module named in the
# task's allowlist; it reaches this script through run_m5c2_rev5_offline, and is
# accessed as R41 = R5.R41 so no extra import surface is introduced.
import run_m5c2_rev5_offline as R5      # noqa: E402
import run_m5c2_rev5_1_offline as R51   # noqa: E402

R41 = R5.R41

PRE = ROOT / "docs/_work/PREREG-M5-C2-REV7.md"
PRE_SHA16 = "32eaf82ca56600c4"
PRE_BYTES = 5835
PRE_LINES = 88
JUDGE = OUT / "M5B4-JUDGE.json"
JUDGE_SHA16 = "6a3001b6ca23ef7d"
JUDGE_BYTES = 452456
GOLD = OUT / "M5B4-LEAD-RULING.json"
GOLD_SHA16 = "9273ebc97aa1413a"
GOLD_BYTES = 13195
SENT = OUT / "M5B4-SENTENCES.json"
SENT_SHA16 = "c349ca5a93192aac"
SENT_BYTES = 99636
ART = OUT / "M5C2-REV7-OFFLINE.json"
PROMPT_SHA16 = "a6bc4f268f7711de"

N_SENTENCES = 261
N_PURE_MODEL_ROWS = 246
N_ABSTAIN_ROWS = 15

# --- verification constants only (never used as judging inputs) -------------
# Baseline rev5.1 readings the executor must reproduce before proceeding.
EXPECT_FP = ["b4-s1-q2-s01", "b4-s1-q2-s07", "b4-s1-q2-s09", "b4-s1-q2-s15",
             "b4-s1-q3-s03", "b4-s2-q1-s01", "b4-s8-q2-s02"]
EXPECT_LEAK = ["b4-s2-q2-s01", "b4-s3-q4-s03", "b4-s3-q4-s11", "b4-s3-q4-s12"]
# PREREG section 2 assertion subjects.
ASSERT_A2 = ("b4-s1-q2-s07", "患者")
ASSERT_A3 = ("b4-s1-q2-s09", "患者")

# --- N2: token regexes ------------------------------------------------------
# 4 pure-value patterns are frozen and unchanged.
PURE_PATTERNS = [
    r"\d+(?:\.\d+)?\s*(?:元|度|M|G|层|楼|排|号|节|个月|年|月|日)",
    r"下?(?:周|星期)[一二三四五六日天]",
    r"\d+月\d+日",
    r"[A-Z]{2,}-\d{3,}",
]
# Entity pattern: non-greedy + functional-word prefixes excluded; group(1) only.
ENTITY_PATTERN = (r"(?:(?:是|叫|为|在|到)\s*)?"
                  r"([^\s，。是叫为在的]{2,8}(?:公司|店|院|馆|中心|银行|医院|学院|酒店|机场))")


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def verify_inputs():
    """Byte/line verify every frozen input; hard stop on any drift."""
    pb = PRE.read_bytes()
    if sha16(pb) != PRE_SHA16:
        raise SystemExit("REV7 prereg changed (sha16 %s)" % sha16(pb))
    if len(pb) != PRE_BYTES:
        raise SystemExit("REV7 prereg byte count changed (%d)" % len(pb))
    if pb.count(b"\n") + 1 != PRE_LINES:
        raise SystemExit("REV7 prereg line count changed")
    if pb.endswith(b"\n"):
        raise SystemExit("REV7 prereg trailing newline changed")
    if b"frozen=true" not in pb or b"frozen_rev=1" not in pb:
        raise SystemExit("REV7 prereg frozen marker missing")
    if b"executed=false" not in pb:
        raise SystemExit("REV7 prereg executed marker missing")

    jb = JUDGE.read_bytes()
    if sha16(jb) != JUDGE_SHA16 or len(jb) != JUDGE_BYTES:
        raise SystemExit("M5B4-JUDGE changed")
    gb = GOLD.read_bytes()
    if sha16(gb) != GOLD_SHA16 or len(gb) != GOLD_BYTES:
        raise SystemExit("M5B4-LEAD-RULING gold changed")
    sb = SENT.read_bytes()
    if sha16(sb) != SENT_SHA16 or len(sb) != SENT_BYTES:
        raise SystemExit("M5B4-SENTENCES changed")
    return {
        "prereg": {"file": PRE.name, "sha16": sha16(pb), "bytes": len(pb),
                   "lines": pb.count(b"\n") + 1,
                   "ends_with_newline": False, "frozen": "frozen=true",
                   "frozen_rev": 1},
        "items_source": {"file": JUDGE.name, "sha16": sha16(jb), "bytes": len(jb)},
        "gold": {"file": GOLD.name, "sha16": sha16(gb), "bytes": len(gb)},
        "sentences": {"file": SENT.name, "sha16": sha16(sb), "bytes": len(sb)},
    }


# =========================== N1 =============================================
def normalize7(s):
    """PREREG N1, literally: NFKC -> thousands strip -> whitespace strip."""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"(?<=\d)[,，](?=\d{3})", "", s)
    s = re.sub(r"\s+", "", s)
    return s


# =========================== N2 =============================================
def value_tokens(entry):
    """Return [(token, kind)] with kind in {"pure","entity"}.

    pure   : the 4 frozen pure-value regexes, always R1 values.
    entity : new non-greedy capture group 1 only (old greedy form deleted).
    Dedupe keeps first occurrence, matching the rev4.1 ordering habit.
    """
    toks = []
    seen = []
    for pat in PURE_PATTERNS:
        for m in re.finditer(pat, entry or ""):
            t = m.group(0).strip()
            if t and t not in seen:
                seen.append(t)
                toks.append((t, "pure"))
    for m in re.finditer(ENTITY_PATTERN, entry or ""):
        t = (m.group(1) or "").strip()
        if t and t not in seen:
            seen.append(t)
            toks.append((t, "entity"))
    return toks


def token_kind_of_span(span):
    """Classify a rule-hit span for attribution (N1 vs N2)."""
    span = span or ""
    for pat in PURE_PATTERNS:
        if re.fullmatch(pat, span):
            return "pure"
    if re.search(ENTITY_PATTERN, span):
        return "entity"
    return "other"


# =========================== N3 =============================================
def matcher(item, sentence):
    """N3 locator.  Returns (matcher_hit, coverage) with coverage of N3."""
    a = normalize7(item)
    b = normalize7(sentence)
    if a in b:
        return "substring", 1.0
    cov = R5.window_coverage(a, b)
    return ("window" if cov >= 0.90 else "none"), cov


# =========================== R1/R2/R3 (rev7) ================================
def r1_r2_r3_rev7(entry, evidence, source, valid):
    """r5.r1_r2_r3 logic with normalize7; N2 gate on R1; N4 gate on R3."""
    hits = []
    ev = normalize7(evidence)
    ent = normalize7(entry)
    src = normalize7(source)
    toks = value_tokens(entry)

    # --- R1 value check (N2 participation gate) ---
    r1_detail = []
    for tok, kind in toks:
        tn = normalize7(tok)
        participates = True
        if kind == "entity" and tn not in src:
            participates = False
        cov = R41.fuzzy_coverage(tn, ev) if tn else 0.0
        r1_detail.append({"token": tok, "kind": kind,
                          "in_source": (tn in src) if tn else False,
                          "r1_participates": participates,
                          "coverage": round(cov, 6)})
        if participates and cov < 0.80:
            hits.append({"rule": "R1", "reason": "value_mismatch", "span": tok})

    # --- R2 negation check (same shape as R5.r1_r2_r3, normalize7 only) ---
    anchors = []
    for a in [t for t, _ in toks] + [ent]:
        a = normalize7(a)
        if a and a not in anchors:
            anchors.append(a)
    r2_done = False
    for anchor in anchors:
        if r2_done or not anchor:
            continue
        for m in re.finditer(re.escape(anchor), ev):
            i = m.start()
            before = ev[max(0, i - 6):i]
            neg = [w for w in R5.NEG_WORDS if w in before]
            if neg:
                hits.append({"rule": "R2", "reason": "negated",
                             "span": ev[max(0, i - 8):i + len(anchor) + 8],
                             "anchor": anchor, "before": before,
                             "neg_word": sorted(neg, key=len, reverse=True)[0]})
                r2_done = True
                break
            pat = re.compile(r"(不是|并非|而不是)\s*" + re.escape(anchor))
            mt = pat.search(ev)
            if mt:
                hits.append({"rule": "R2", "reason": "negated_pattern",
                             "span": mt.group(0), "anchor": anchor})
                r2_done = True
                break
            pat2 = re.compile(re.escape(anchor) + r"\s*(不是|是错的)")
            mt2 = pat2.search(ev)
            if mt2:
                hits.append({"rule": "R2", "reason": "negated_after",
                             "span": mt2.group(0), "anchor": anchor})
                r2_done = True
                break

    # --- R3 absent-marker vocabulary (N4: only on valid items) ---
    r3 = None
    if valid:
        for marker in R5.ABSENT_MARKERS:
            if normalize7(marker) in ev:
                r3 = marker
                hits.append({"rule": "R3", "reason": "absent_marker",
                             "span": marker})
                break
    return hits, r3, r1_detail


# =========================== R4+ (rev5.1 metric, normalize7) ================
def r4_plus_rev7(evidence, source, has_r3):
    """run_m5c2_rev5_1_offline.r4_plus_v51 with normalize7."""
    if has_r3:
        return None
    ev = normalize7(evidence)
    src = normalize7(source)
    if not ev:
        return {"rule": "R4+", "reason": "fabricated_evidence",
                "span": "(empty)", "metric": "empty", "jaccard_or_bigram": 0.0}
    if ev in src:
        return None
    if len(ev) <= 4:
        j = R51.max_window_jaccard(ev, src)
        if j >= 0.80:
            return None
        return {"rule": "R4+", "reason": "fabricated_evidence",
                "span": evidence, "metric": "char_jaccard",
                "jaccard_or_bigram": round(j, 6)}
    cov = R5.window_coverage(ev, src)
    if cov >= 0.80:
        return None
    return {"rule": "R4+", "reason": "fabricated_evidence",
            "span": evidence, "metric": "bigram",
            "jaccard_or_bigram": round(cov, 6)}


# =========================== rev5.1 baseline ===============================
def verdict_v51(row):
    """Baseline rev5.1 verdict, recomputed from the stored rev5.1 artifacts."""
    if row["route"] == "empty_source":
        return "unsupported"
    if row["route"] == "abstain_check":
        return row["layer0"]["verdict"]
    if not row["parse_ok"]:
        return "parse_fail"
    if row["derived"]:
        return "undecidable"
    if not row["items"]:
        return "undecidable"
    if any(z["absent"] for z in row["items"]):
        return "unsupported"
    return "supported"


def baseline_reproduce(rows, gold):
    """Hard gate: the baseline must be reproduced exactly before rev7 runs."""
    mismatches = []
    item_mismatches = []
    derived_mismatches = []
    for row in rows:
        v = verdict_v51(row)
        if v != row["verdict"]:
            mismatches.append({"sid": row["sid"], "recomputed": v,
                               "stored": row["verdict"]})
        if row["route"] == "abstain_check":
            if row["layer0"].get("verdict") != row["verdict"]:
                mismatches.append({"sid": row["sid"], "recomputed": "layer0",
                                   "stored": row["verdict"]})
            continue
        # item-level fidelity: re-run rev5.1 rules on the stored items
        redo = R51.judge_items(
            [{"item": z["item"], "evidence": z["evidence"]} for z in row["items"]],
            row["source_text"])
        for a, b in zip(row["items"], redo):
            if a["absent"] != b["absent"]:
                item_mismatches.append({"sid": row["sid"], "item": a["item"],
                                        "stored": a["absent"], "recomputed": b["absent"]})
            if ([(h["rule"], h.get("reason")) for h in a["rule_hits"]]
                    != [(h["rule"], h.get("reason")) for h in b["rule_hits"]]):
                item_mismatches.append({"sid": row["sid"], "item": a["item"],
                                        "stored_rules": [h["rule"] for h in a["rule_hits"]],
                                        "recomputed_rules": [h["rule"] for h in b["rule_hits"]]})
        en, _dd = R5.derived_plus(row["sentence"], row["source_text"])
        if bool(en) != bool(row["derived"]):
            derived_mismatches.append({"sid": row["sid"], "stored": row["derived"],
                                       "recomputed": bool(en)})

    supp = [r for r in rows if gold[r["sid"]] == "support_present"]
    fab = [r for r in rows if gold[r["sid"]] == "fabricated"]
    fp = [r["sid"] for r in supp if r["verdict"] == "unsupported"]
    leak = [r["sid"] for r in fab if r["verdict"] in ("supported", "undecidable")]
    pf = [r["sid"] for r in rows if r["verdict"] == "parse_fail"]

    ok = (not mismatches and not item_mismatches and not derived_mismatches
          and len(fp) == 7 and len(leak) == 4 and len(pf) == 1
          and sorted(fp) == sorted(EXPECT_FP) and sorted(leak) == sorted(EXPECT_LEAK))
    repro = {
        "n_checked": len(rows),
        "n_match": len(rows) - len(mismatches),
        "match_all": not mismatches,
        "rule": ("stored items[] absent flags re-aggregated; abstain_check keeps "
                 "layer0 verdict; parse_ok=False => parse_fail; derived => undecidable"),
        "mismatches": mismatches,
        "item_level": {
            "n_items_checked": sum(len(r["items"]) for r in rows),
            "n_mismatch": len(item_mismatches),
            "rule": "R51.judge_items(stored item/evidence, source) must reproduce stored absent + rule_hits",
            "mismatches": item_mismatches[:20],
        },
        "derived_recompute": {
            "n_checked": sum(1 for r in rows if r["route"] != "abstain_check"),
            "n_mismatch": len(derived_mismatches),
            "rule": "R5.derived_plus(sentence, source) must reproduce stored derived flag",
            "mismatches": derived_mismatches[:20],
        },
        "baseline_verdict_distribution": {},
        "baseline_false_positive": {"k": len(fp), "n": len(supp),
                                    "threshold_le": 4, "sids": sorted(fp)},
        "baseline_leak": {"k": len(leak), "n": len(fab),
                          "threshold_le": 5, "sids": sorted(leak)},
        "baseline_parse_fail": {"k": len(pf), "n": len(rows), "sids": sorted(pf)},
        "expected_from_brief": {"false_positive_sids": sorted(EXPECT_FP),
                                "leak_sids": sorted(EXPECT_LEAK)},
        "matches_brief": ok,
        "reproduced": not mismatches and not item_mismatches and not derived_mismatches,
    }
    dist = {}
    for r in rows:
        dist[r["verdict"]] = dist.get(r["verdict"], 0) + 1
    repro["baseline_verdict_distribution"] = dict(sorted(dist.items()))
    return repro


# =========================== rev7 item/sentence judging =====================
def judge_row_rev7(row):
    """Recompute one sentence's items and verdict under N1-N4."""
    sid = row["sid"]
    sent = row["sentence"]
    src = row["source_text"]
    item_recs = []
    for z in row["items"]:
        item = z["item"]
        evidence = z["evidence"]
        mh, cov = matcher(item, sent)
        valid = (mh != "none")
        hits, r3, r1_detail = r1_r2_r3_rev7(item, evidence, src, valid)
        r4 = r4_plus_rev7(evidence, src, r3 is not None)
        if r4:
            hits.append(r4)
        numeric_ok = not any(h["rule"] == "R1" for h in hits)
        binding = valid
        absent = bool(valid and hits)
        ev7 = normalize7(evidence)
        if not valid:
            item_verdict = "invalid"
        elif absent:
            item_verdict = "absent"
        elif ev7 and ev7 not in normalize7(src):
            item_verdict = "unverified"
        else:
            item_verdict = "present"
        first = hits[0] if hits else None
        item_recs.append({
            "sid": sid,
            "item": item,
            "evidence": evidence,
            "valid": valid,
            "absent": absent,
            "matcher_hit": mh,
            "coverage": round(cov, 6),
            "numeric_ok": numeric_ok,
            "item_verdict": item_verdict,
            "rule": first["rule"] if first else None,
            "reason": first.get("reason") if first else None,
            "r3_hit": r3 is not None,
            "binding": binding,
            "rule_hits": hits,
            "value_tokens": r1_detail,
        })

    en, dd = R5.derived_plus(sent, src)
    if row["route"] == "empty_source":
        v7 = "unsupported"
    elif row["route"] == "abstain_check":
        v7 = row["layer0"]["verdict"]
    elif not row["parse_ok"]:
        v7 = "parse_fail"
    elif en:
        v7 = "undecidable"
    elif not row["items"]:
        v7 = "undecidable"
    elif any(z["absent"] for z in item_recs):
        v7 = "unsupported"
    else:
        v7 = "supported"

    counts = {"invalid": 0, "absent": 0, "unverified": 0, "present": 0}
    for z in item_recs:
        counts[z["item_verdict"]] += 1
    sent_rec = {
        "sid": sid,
        "gold": None,  # filled by caller
        "verdict_rev5_1": row["verdict"],
        "verdict_rev7": v7,
        "route": row["route"],
        "parse_ok": row["parse_ok"],
        "derived_rev7": bool(en),
        "derived_stored": bool(row["derived"]),
        "n_items": len(item_recs),
        "n_valid": counts["present"] + counts["absent"] + counts["unverified"],
        "n_invalid": counts["invalid"],
        "n_absent": counts["absent"],
        "n_unverified": counts["unverified"],
        "changed": v7 != row["verdict"],
    }
    return sent_rec, item_recs, dd


def pick_attribution(rev5_hits):
    """N1 / N2 / N3 / N4 / R4+ / declared / other from the rev5.1 hits."""
    rules = [h["rule"] for h in rev5_hits]
    r1_kinds = [token_kind_of_span(h.get("span")) for h in rev5_hits
                if h["rule"] == "R1"]
    if "pure" in r1_kinds:
        return "N1"
    if "entity" in r1_kinds:
        return "N2"
    if "R3" in rules:
        return "N3"
    if "R4+" in rules:
        return "R4+"
    if "R2" in rules:
        return "declared"
    return "other"


def rev7_causes(row, item_recs):
    """Mechanical cause tags for a verdict change."""
    old_hits = [h for z in row["items"] for h in z["rule_hits"]]
    new_hits = [h for z in item_recs if z["binding"] for h in z["rule_hits"]]
    old_rules = set(h["rule"] for h in old_hits)
    new_rules = set(h["rule"] for h in new_hits)
    tags = []
    if "R1" in old_rules and "R1" not in new_rules:
        kinds = set(token_kind_of_span(h.get("span")) for h in old_hits
                    if h["rule"] == "R1")
        if "pure" in kinds:
            tags.append("N1")
        if "entity" in kinds:
            tags.append("N2")
    if "R4+" in old_rules and "R4+" not in new_rules:
        tags.append("R4+")
    if "R3" in old_rules and "R3" not in new_rules:
        tags.append("N4")
    n_invalid = sum(1 for z in item_recs if not z["valid"])
    if n_invalid:
        tags.append("N3")
    if not tags:
        tags.append("aggregation")
    order = {"N1": 0, "N2": 1, "N3": 2, "N4": 3, "R4+": 4, "aggregation": 5}
    return sorted(tags, key=lambda t: order.get(t, 9))


def char_evidence(sid, target_item, item_recs_by_sid):
    """Character-level evidence for an N3 assertion subject."""
    sent = SENTENCE_OF.get(sid)
    occ = []
    for idx, z in enumerate(item_recs_by_sid.get(sid, [])):
        if z["item"] != target_item:
            continue
        a = normalize7(z["item"])
        b = normalize7(sent or "")
        occ.append({
            "item_index": idx,
            "item": z["item"],
            "sentence": sent,
            "normalize7_item": a,
            "normalize7_sentence": b,
            "item_in_sentence": a in b,
            "item_pos": b.find(a) if a in b else None,
            "matcher_hit": z["matcher_hit"],
            "coverage": z["coverage"],
            "valid": z["valid"],
            "binding_hits": [h["rule"] for h in z["rule_hits"]] if z["binding"] else [],
        })
    passed = bool(occ) and all(o["valid"] is False for o in occ)
    return {
        "sid": sid,
        "target_item": target_item,
        "n_occurrences": len(occ),
        "occurrences": occ,
        "pass": passed,
    }


SENTENCE_OF = {}


# =========================== main ===========================================
def main():
    meta = verify_inputs()
    judge = json.loads(JUDGE.read_bytes().decode("utf-8"))
    gold_doc = json.loads(GOLD.read_bytes().decode("utf-8"))
    gold = gold_doc["gold"]
    rows = judge["items"]
    if len(rows) != N_SENTENCES:
        raise SystemExit("expected %d sentences, got %d" % (N_SENTENCES, len(rows)))
    if len(gold) != N_SENTENCES:
        raise SystemExit("gold size mismatch")
    if judge.get("n_sentences") != N_SENTENCES:
        raise SystemExit("judge n_sentences mismatch")
    if judge.get("sentences_sha16") != SENT_SHA16:
        raise SystemExit("judge sentences_sha16 mismatch")
    n_model = sum(1 for r in rows if r["route"] == "model_extract")
    n_abstain = sum(1 for r in rows if r["route"] == "abstain_check")
    if (n_model, n_abstain) != (N_PURE_MODEL_ROWS, N_ABSTAIN_ROWS):
        raise SystemExit("route mix changed")
    for r in rows:
        SENTENCE_OF[r["sid"]] = r["sentence"]

    # ---- 1) baseline rev5.1 must reproduce 261/261 before rev7 ----
    repro = baseline_reproduce(rows, gold)
    if not repro["match_all"] or repro["item_level"]["n_mismatch"] or \
            repro["derived_recompute"]["n_mismatch"]:
        print(json.dumps({"status": "基线复现失败", "baseline_reproduction": repro},
                         ensure_ascii=False, indent=1))
        raise SystemExit(3)
    if not repro["matches_brief"]:
        print(json.dumps({"status": "基线读数与简报不符",
                          "baseline_reproduction": repro},
                         ensure_ascii=False, indent=1))
        raise SystemExit(3)

    # ---- 2) rev7 recompute ----
    sent_recs = []
    item_recs_all = []
    item_by_sid = {}
    derived_applicable = []
    for row in rows:
        sent_rec, item_recs, dd = judge_row_rev7(row)
        sent_rec["gold"] = gold[row["sid"]]
        sent_recs.append(sent_rec)
        item_recs_all.extend(item_recs)
        item_by_sid[row["sid"]] = item_recs
        if dd.get("applicable"):
            derived_applicable.append({
                "sid": row["sid"],
                "enabled": bool(dd.get("enabled")),
                "keyword": dd.get("keyword", ""),
                "sentence_values": dd.get("sentence_values"),
                "source_values": dd.get("source_values"),
                "missing_values": dd.get("missing_values"),
            })
    row_by_sid = {r["sid"]: r for r in rows}

    # ---- 3) assertions ----
    a1_value = R5.coverage("8600元", normalize7("手术费 8,600 元"))
    assertions = {
        "A1": {
            "expr": "R5.coverage('8600元', normalize7('手术费 8,600 元')) == 1.0",
            "value": a1_value,
            "normalize7_input": normalize7("手术费 8,600 元"),
            "pass": a1_value == 1.0,
        },
        "A2": char_evidence(ASSERT_A2[0], ASSERT_A2[1], item_by_sid),
        "A3": char_evidence(ASSERT_A3[0], ASSERT_A3[1], item_by_sid),
    }
    assertions["all_pass"] = bool(assertions["A1"]["pass"]
                                  and assertions["A2"]["pass"]
                                  and assertions["A3"]["pass"])
    if not assertions["A2"]["pass"] or not assertions["A3"]["pass"]:
        assertions["assertion_note"] = (
            "PREREG-M5-C2-REV7.md section 2 N3 declares that the item 患者 in "
            "b4-s1-q2-s07 / b4-s1-q2-s09 must be judged valid=false. Under the "
            "literal N3 definition (normalize7(item) substring of "
            "normalize7(sentence) OR window_coverage >= 0.90) both items ARE "
            "literally present in their sentences (they are the leading "
            "'患者：' label), so valid=true and the assertion is unsatisfiable "
            "without adding an unregistered condition. The rule implementation "
            "was NOT bent to satisfy the assertion; the FAIL is kept and the "
            "character-level evidence is attached. Consequence: the R3 "
            "absent-marker path for these two sentences is not gated away, so "
            "both remain false positives (see sentence_diff.unchanged_false_positive).")

    # ---- 3b) implementation checks (not prereg assertions; audit helpers) ----
    toks_a = value_tokens("地点是宠安医院")
    toks_b = value_tokens("租车公司")
    n2_absent_src = r1_r2_r3_rev7("租车公司", "迅达租车", "我在迅达租车", True)
    n2_present_src = r1_r2_r3_rev7("租车公司", "迅达租车", "租车公司是迅达租车", True)
    n4_invalid = r1_r2_r3_rev7("就诊人", "未提及", "我在仁和口腔", False)
    n4_valid = r1_r2_r3_rev7("就诊人", "未提及", "我在仁和口腔", True)
    implementation_checks = {
        "N2_entity_capture_no_greedy_prefix": {
            "input": "地点是宠安医院",
            "tokens": [[t, k] for t, k in toks_a],
            "pass": toks_a == [("宠安医院", "entity")],
        },
        "N2_entity_capture_plain": {
            "input": "租车公司",
            "tokens": [[t, k] for t, k in toks_b],
            "pass": toks_b == [("租车公司", "entity")],
        },
        "N2_entity_gate_skips_non_source_token": {
            "item": "租车公司", "evidence": "迅达租车", "source": "我在迅达租车",
            "r1_hits": [h["rule"] for h in n2_absent_src[0]],
            "r1_participation": [d["r1_participates"] for d in n2_absent_src[2]],
            "pass": (not any(h["rule"] == "R1" for h in n2_absent_src[0])
                     and [d["r1_participates"] for d in n2_absent_src[2]] == [False]),
        },
        "N2_entity_gate_keeps_source_token": {
            "item": "租车公司", "evidence": "迅达租车", "source": "租车公司是迅达租车",
            "r1_hits": [h["rule"] for h in n2_present_src[0]],
            "r1_participation": [d["r1_participates"] for d in n2_present_src[2]],
            "pass": (any(h["rule"] == "R1" for h in n2_present_src[0])
                     and [d["r1_participates"] for d in n2_present_src[2]] == [True]),
        },
        "N4_r3_only_on_valid_items": {
            "invalid_item_hits": [h["rule"] for h in n4_invalid[0]],
            "valid_item_hits": [h["rule"] for h in n4_valid[0]],
            "pass": (not any(h["rule"] == "R3" for h in n4_invalid[0])
                     and any(h["rule"] == "R3" for h in n4_valid[0])),
        },
    }
    implementation_checks["all_pass"] = all(
        v["pass"] for v in implementation_checks.values() if isinstance(v, dict))

    # ---- 4) metrics / gate ----
    supp = [r for r in sent_recs if r["gold"] == "support_present"]
    fab = [r for r in sent_recs if r["gold"] == "fabricated"]
    fp = [r for r in supp if r["verdict_rev7"] == "unsupported"]
    leak = [r for r in fab if r["verdict_rev7"] in ("supported", "undecidable")]
    pf = [r for r in sent_recs if r["verdict_rev7"] == "parse_fail"]
    fab_at_risk = [r for r in fab if r["verdict_rev5_1"] == "unsupported"]
    new_miss = [r for r in fab_at_risk if r["verdict_rev7"] == "supported"]

    def gate_item(k, n, threshold, kind="le"):
        if kind == "le":
            ok = k <= threshold
        else:
            ok = k == threshold
        return {"k": k, "n": n, "threshold": ("<=%d" % threshold) if kind == "le"
                else ("==%d" % threshold), "pass": bool(ok)}

    gate = {
        "false_positive": gate_item(len(fp), len(supp), 4),
        "leak_missed": gate_item(len(leak), len(fab), 5),
        "parse_fail": gate_item(len(pf), len(sent_recs), 2),
        "new_miss": gate_item(len(new_miss), len(fab_at_risk), 0, kind="eq"),
    }
    gate["false_positive_sids"] = sorted(r["sid"] for r in fp)
    gate["leak_missed_sids"] = sorted(r["sid"] for r in leak)
    gate["parse_fail_sids"] = sorted(r["sid"] for r in pf)
    gate["new_miss_sids"] = sorted(r["sid"] for r in new_miss)
    gate["any_fail"] = any(not gate[k]["pass"] for k in
                           ("false_positive", "leak_missed", "parse_fail", "new_miss"))
    gate["rev7_unusable"] = bool(gate["any_fail"])
    gate["rev7_unusable_basis"] = ("PREREG section 3: any of the four thresholds "
                                   "failing => rev7_unusable=true (assertions are "
                                   "reported separately, not a section-3 gate)")

    # ---- 5) sentence diff + false_by_reason ----
    fixed, broken, neutral = [], [], []
    for rec in sent_recs:
        if not rec["changed"]:
            continue
        row = row_by_sid[rec["sid"]]
        causes = rev7_causes(row, item_by_sid[rec["sid"]])
        entry = {"sid": rec["sid"], "gold": rec["gold"],
                 "verdict_rev5_1": rec["verdict_rev5_1"],
                 "verdict_rev7": rec["verdict_rev7"],
                 "cause": causes,
                 "n_items": rec["n_items"], "n_valid": rec["n_valid"],
                 "n_invalid": rec["n_invalid"]}
        is_fixed = ((rec["gold"] == "support_present"
                     and rec["verdict_rev5_1"] == "unsupported"
                     and rec["verdict_rev7"] == "supported")
                    or (rec["gold"] == "fabricated"
                        and rec["verdict_rev5_1"] in ("supported", "undecidable")
                        and rec["verdict_rev7"] == "unsupported"))
        is_broken = ((rec["gold"] == "support_present"
                      and rec["verdict_rev7"] == "unsupported")
                     or (rec["gold"] == "fabricated"
                         and rec["verdict_rev7"] in ("supported", "undecidable")))
        if is_fixed:
            fixed.append(entry)
        elif is_broken:
            broken.append(entry)
        else:
            neutral.append(entry)

    unchanged_fp = [r for r in supp if r["verdict_rev5_1"] == "unsupported"
                    and r["verdict_rev7"] == "unsupported"]
    sentence_diff = {
        "n_changed": len(fixed) + len(broken) + len(neutral),
        "n_fixed": len(fixed), "n_broken": len(broken), "n_neutral": len(neutral),
        "fixed": fixed,
        "broken": broken,
        "neutral": neutral,
        "unchanged_false_positive": [{"sid": r["sid"], "gold": r["gold"],
                                      "verdict_rev5_1": r["verdict_rev5_1"],
                                      "verdict_rev7": r["verdict_rev7"]}
                                     for r in unchanged_fp],
        "unchanged_leak": [{"sid": r["sid"], "gold": r["gold"],
                            "verdict_rev5_1": r["verdict_rev5_1"],
                            "verdict_rev7": r["verdict_rev7"]}
                           for r in leak],
        "definitions": {
            "fixed": ("gold=support_present and rev5.1 unsupported -> rev7 supported, "
                      "OR gold=fabricated and rev5.1 supported/undecidable -> rev7 unsupported"),
            "broken": ("gold=support_present and rev7 unsupported, OR gold=fabricated "
                       "and rev7 supported/undecidable"),
            "neutral": "changed but neither fixed nor broken (e.g. gold=no_fact)",
        },
    }

    false_by_reason = []
    for r in supp:
        if r["verdict_rev5_1"] != "unsupported":
            continue
        row = row_by_sid[r["sid"]]
        old_hits = [{"rule": h["rule"], "reason": h.get("reason"),
                     "span": h.get("span")} for h in row["rule_hits"]]
        attr = pick_attribution(row["rule_hits"])
        fixed_now = r["verdict_rev7"] == "supported"
        note = None
        if attr == "N3" and not fixed_now:
            note = ("N3 intended to void the absent-marker items, but the item 患者 "
                    "is literally present in the sentence as the '患者：' label, so "
                    "N3 keeps valid=true (PREREG section 2 assertion conflict); "
                    "R3 therefore still fires.")
        false_by_reason.append({
            "sid": r["sid"],
            "gold": r["gold"],
            "verdict_rev5_1": r["verdict_rev5_1"],
            "verdict_rev7": r["verdict_rev7"],
            "attribution": attr,
            "fixed": fixed_now,
            "rev5_1_rule_hits": old_hits,
            "rev7_binding_rule_hits": [{"rule": h["rule"], "span": h.get("span")}
                                       for z in item_by_sid[r["sid"]]
                                       if z["binding"] for h in z["rule_hits"]],
            "note": note,
        })

    # ---- 6) invalid items / all-invalid sentences ----
    invalid_items = []
    for rec in item_recs_all:
        if rec["valid"]:
            continue
        sent = SENTENCE_OF[rec["sid"]]
        a = normalize7(rec["item"])
        b = normalize7(sent)
        invalid_items.append({
            "sid": rec["sid"],
            "item": rec["item"],
            "sentence": sent,
            "normalize7_item": a,
            "item_in_sentence": a in b,
            "item_pos": b.find(a) if a in b else None,
            "matcher_hit": rec["matcher_hit"],
            "coverage": rec["coverage"],
        })
    all_invalid = []
    for rec in sent_recs:
        if rec["n_items"] > 0 and rec["n_valid"] == 0:
            all_invalid.append({
                "sid": rec["sid"], "gold": rec["gold"],
                "verdict_rev5_1": rec["verdict_rev5_1"],
                "verdict_rev7": rec["verdict_rev7"],
                "n_items": rec["n_items"],
                "note": ("all items invalid under N3 => no absent, no unverified "
                         "=> literal aggregation gives supported (reported, not "
                         "special-cased)"),
            })

    # ---- 7) rule-hit tallies ----
    rev7_rule_counts = {}
    for rec in item_recs_all:
        if not rec["binding"]:
            continue
        for h in rec["rule_hits"]:
            rev7_rule_counts[h["rule"]] = rev7_rule_counts.get(h["rule"], 0) + 1
    rev5_rule_counts = {}
    for row in rows:
        for h in row["rule_hits"]:
            rev5_rule_counts[h["rule"]] = rev5_rule_counts.get(h["rule"], 0) + 1

    # ---- 8) assemble ----
    code_bytes = Path(__file__).read_bytes()
    out = {
        "schema": "m5c2_rev7_offline_v1",
        "rev7_ver": 1,
        "status": "已读数",
        "design_set": True,
        "design_set_note": "design set = (b4); acceptance set = (b5) not run here",
        "not_acceptance": True,
        "n_sentences": len(sent_recs),
        "n_forward": 0,
        "n_forward_planned": 0,
        "n_model_rows": n_model,
        "n_abstain_rows": n_abstain,
        "reused_model_output": True,
        "prereg_sha16": PRE_SHA16,
        "items_source_sha16": JUDGE_SHA16,
        "gold_sha16_current": GOLD_SHA16,
        "prompt_sha16": PROMPT_SHA16,
        "code_sha16": sha16(code_bytes),
        "code_file": "kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py",
        "code_bytes": len(code_bytes),
        "inputs": meta,
        "rule_impl": {
            "N1": ("normalize7(s) = NFKC -> re.sub(r'(?<=\\d)[,，](?=\\d{3})','',s) "
                   "-> re.sub(r'\\s+','',s); used by every R1/R2/R3/R4+ comparison"),
            "N2": ("value_tokens: 4 pure-value regexes unchanged; old greedy entity "
                   "regex deleted; entity = capture group 1 of "
                   "(?:(?:是|叫|为|在|到)\\s*)?([^\\s，。是叫为在的]{2,8}(?:公司|店|院|馆|中心|银行|医院|学院|酒店|机场)); "
                   "entity participates in R1 only when normalize7(token) is a "
                   "substring of normalize7(source)"),
            "N3": ("valid = normalize7(item) in normalize7(sentence) OR "
                   "R5.window_coverage(normalize7(item), normalize7(sentence)) >= 0.90; "
                   "invalid items take no part in aggregation"),
            "N4": "R3 absent markers fire only on valid items",
            "aggregation": ("empty_source->unsupported; abstain_check->layer0 verdict; "
                            "not parse_ok->parse_fail; derived_plus->undecidable; "
                            "no items->undecidable; any valid item with any hit->unsupported; "
                            "else supported"),
            "R2_anchor_choice": ("R2 anchors are built from the N2 value_tokens() list "
                                 "(pure + entity) plus normalize7(entry), exactly mirroring "
                                 "run_m5c2_rev5_offline.r1_r2_r3 with normalize7; the N2 "
                                 "source-substring gate is applied to R1 participation only, "
                                 "as PREREG section 2 N2 item 3 states"),
            "thresholds": {"R1": 0.80, "R4+_long": 0.80, "R4+_short_jaccard": 0.80,
                           "N3": 0.90},
        },
        "definitions": {
            "coverage": "N3 locator coverage (1.0 on substring hit, else best same-length window bigram coverage)",
            "numeric_ok": "true iff the item produced no R1 value_mismatch hit",
            "item_verdict": ("invalid (N3 void) | absent (valid and any rule hit) | "
                             "unverified (valid, no hit, evidence not verbatim locatable "
                             "in source) | present (valid, no hit, evidence verbatim in source)"),
            "binding": "true iff the item is valid; only binding items enter aggregation",
            "n_valid": "present + absent + unverified",
            "n_unverified": ("count of valid items with item_verdict=unverified; "
                             "count-only field required by PREREG section 4, it never "
                             "affects the verdict"),
            "rule": "first hit rule of the item",
            "reason": "reason of the first hit rule",
        },
        "baseline_reproduction": repro,
        "assertions": assertions,
        "implementation_checks": implementation_checks,
        "gate": gate,
        "rates": {
            "false_positive": {"k": len(fp), "n": len(supp),
                               "rate": round(len(fp) / len(supp), 4)},
            "leak_missed": {"k": len(leak), "n": len(fab),
                            "rate": round(len(leak) / len(fab), 4)},
            "parse_fail": {"k": len(pf), "n": len(sent_recs),
                           "rate": round(len(pf) / len(sent_recs), 4)},
            "invalid_items": {"k": len(invalid_items), "n": len(item_recs_all),
                              "rate": round(len(invalid_items) / len(item_recs_all), 4)},
        },
        "rev7_rule_hit_counts": dict(sorted(rev7_rule_counts.items())),
        "rev5_1_rule_hit_counts": dict(sorted(rev5_rule_counts.items())),
        "derived_applicable": derived_applicable,
        "false_by_reason": false_by_reason,
        "sentence_diff": sentence_diff,
        "invalid_items": invalid_items,
        "all_invalid_sentences": all_invalid,
        "sentences": sent_recs,
        "items": item_recs_all,
        "determinism": {"timestamps": False,
                        "json_indent": 1, "ensure_ascii": False,
                        "trailing_newline": True,
                        "double_run_expected": "byte-identical"},
        "imports": ["run_m5c2_rev5_offline", "run_m5c2_rev5_1_offline"],
        "import_notes": ("R41 (= run_m5c2_rev4_1) is reached through "
                         "run_m5c2_rev5_offline (R5.R41), the module named in the "
                         "task allowlist; no direct import of run_m5c2_b4_judge, "
                         "run_m5c2_r2/floor/engine or any GPU runner"),
        "no_gpu": True,
        "no_model_call": True,
        "no_network": True,
        "no_forward": True,
        "signals_sent": False,
        "no_sid_special_cases": True,
        "sid_literals": {
            "b4-s1-q2-s07": ["assertion A2"],
            "b4-s1-q2-s09": ["assertion A3"],
            "baseline false-positive list": ["verification only"],
            "baseline leak list": ["verification only"],
        },
        "no_threshold_change": True,
        "no_wordlist_change": True,
        "no_gold_change": True,
        "no_prereg_change": True,
        "no_input_change": True,
        "no_git_commit": True,
        "no_b5_read": True,
        "n_forward_reused_only": True,
    }
    write_json_atomic(ART, out)

    # ---- console readout ----
    summary = {
        "schema": out["schema"],
        "status": out["status"],
        "n_sentences": out["n_sentences"],
        "n_forward": out["n_forward"],
        "baseline_reproduction": {
            "match_all": repro["match_all"],
            "n_match": repro["n_match"],
            "n_checked": repro["n_checked"],
            "item_level_mismatch": repro["item_level"]["n_mismatch"],
            "derived_mismatch": repro["derived_recompute"]["n_mismatch"],
            "false_positive": repro["baseline_false_positive"],
            "leak": repro["baseline_leak"],
            "parse_fail": repro["baseline_parse_fail"],
            "matches_brief": repro["matches_brief"],
        },
        "assertions": {
            "A1": {"pass": assertions["A1"]["pass"], "value": assertions["A1"]["value"]},
            "A2": {"pass": assertions["A2"]["pass"],
                   "occurrences": assertions["A2"]["occurrences"]},
            "A3": {"pass": assertions["A3"]["pass"],
                   "occurrences": assertions["A3"]["occurrences"]},
            "all_pass": assertions["all_pass"],
        },
        "implementation_checks": implementation_checks,
        "gate": gate,
        "rates": out["rates"],
        "rev7_rule_hit_counts": out["rev7_rule_hit_counts"],
        "false_by_reason": false_by_reason,
        "sentence_diff": {
            "n_changed": sentence_diff["n_changed"],
            "n_fixed": sentence_diff["n_fixed"],
            "n_broken": sentence_diff["n_broken"],
            "n_neutral": sentence_diff["n_neutral"],
            "fixed": [e["sid"] for e in fixed],
            "broken": [e["sid"] for e in broken],
            "neutral": [{"sid": e["sid"], "gold": e["gold"],
                         "from": e["verdict_rev5_1"], "to": e["verdict_rev7"],
                         "cause": e["cause"]} for e in neutral],
            "unchanged_false_positive": sentence_diff["unchanged_false_positive"],
        },
        "invalid_items": {
            "n": len(invalid_items),
            "rate": out["rates"]["invalid_items"]["rate"],
            "by_sid": sorted(set(z["sid"] for z in invalid_items)),
        },
        "all_invalid_sentences": all_invalid,
        "code_sha16": out["code_sha16"],
        "artifact_sha16": sha16(ART.read_bytes()),
        "artifact_bytes": ART.stat().st_size,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())