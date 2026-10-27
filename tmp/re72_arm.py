#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 REV7.2 offline dev runner — M1 / M2 / M3 mechanisms (CPU only).

Spec: docs/_work/RULING-M5C2-B7.md 3dfafd1253f0a833 (R3 / R4 / R5' / R7).
Base rule code: run_m5c2_rev7_1_offline.py 88256d274c9993cc (copied, then only
the three ruled mechanisms are changed; function shapes/schema stay close).

Mechanisms (independent switches, default all on):
  M1  R3 closed-set normalisation N-1..N-5, used for every evidence<->source
      comparison (matching copy only; original text never rewritten).
      N-4' deletes only {的,是}, only inside anchor(numeric/entity) +/-6 chars.
  M2  R4 extractor-false-negative override: when the item literal (after M1) is
      present in the source and the evidence is not the answer sentence, the
      extractor's "not mentioned" markers (R3) and the fabricated_evidence
      penalty (R4+ caused by that evidence) are ignored; counted per sentence.
  M3  R5' evidence relocation + fourth item state `ungrounded`:
      evidence counts only when locatable in the source. When the evidence only
      occurs in the answer sentence, the item is re-located in the source; on
      success the source span becomes the evidence (item=present). U1:
      `ungrounded` is not `absent` and never suffers fabricated_evidence.
      U2: if all items of a sentence are ungrounded => verdict `not-supported`,
      reason `all_items_ungrounded` (never absent-soft).

Dev input (read only): out/M5C2-B5-EXTRACT.json 93505eecc539634a
Compare baseline: out/M5C2-B5-DECIDE.json 59da64cb6f2464de (rev7.1 verdicts)
Output: out/M5C2-REV7-2-DEV.json

ZERO GPU / model / network.  No gold / blind-label read: leak-sentinel A3 is
established structurally (only unsupported->supported changes; no leak-eligible
rev7.1 verdict changes, no sentence becomes unsupported/undecidable/parse_fail).

Run:  python -X utf8 kvmem/m2_visibility/m5/run_m5c2_rev7_2_offline.py
Modes: --dry-run (static only, writes nothing) | default (write DEV artifact)
"""
import argparse
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

import run_m5c2_rev5_offline as R5      # noqa: E402
import run_m5c2_rev5_1_offline as R51   # noqa: E402
import run_m5c2_rev7_1_offline as R71   # noqa: E402

R41 = R5.R41

PRE = ROOT / "docs/_work/PREREG-M5-C2-REV7.1.md"
PRE_SHA16 = "09d6f1b163ea0b84"
PRE_BYTES = 16313
RULING = ROOT / "docs/_work/RULING-M5C2-B7.md"
RULING_SHA16 = "3dfafd1253f0a833"
RULING_BYTES = 9425
EXTRACT = OUT / "M5C2-B5-EXTRACT.json"
EXTRACT_SHA16 = "93505eecc539634a"
EXTRACT_BYTES = 444613
DECIDE = OUT / "M5C2-B5-DECIDE.json"
DECIDE_SHA16 = "59da64cb6f2464de"
DECIDE_BYTES = 741080
ART = OUT / ("M5C2-REV7-2-ARM-" + __import__("os").environ.get("ARM", "all_on") + ".json")
AME = "m5c2_rev7_2_offline_v1"
N_SENTENCES = 326

TARGET_SIDS = ["b5-s1-q1-s01", "b5-s1-q1-s02", "b5-s2-q1-s01", "b5-s2-q1-s02",
               "b5-s6-q2-s09", "b5-s7-q1-s01", "b5-s7-q4-s03"]
TARGET_MECH = {"b5-s1-q1-s01": "M1", "b5-s1-q1-s02": "M1",
               "b5-s2-q1-s01": "M2", "b5-s2-q1-s02": "M2",
               "b5-s6-q2-s09": "M3", "b5-s7-q1-s01": "M3",
               "b5-s7-q4-s03": "M2"}

# --- R5 (M3) relocation / U1 / U2 ------------------------------------------
UNGROUNDED = "ungrounded"
ALL_UNGROUNDED_REASON = "all_items_ungrounded"

# --- N-1..N-5 closed set ----------------------------------------------------
UNIT_CHARS = set("元度MGT层楼排号节个个月年日千万亿米寸分秒人次份件杯盒台车辆套双张部")
ENTITY_ANCHOR_RE = re.compile(
    r"[^\s，。！？；：、\"'（）()]{2,8}(?:公司|店|院|馆|中心|银行|医院|学院|酒店|机场|"
    r"快递|超市|商场|学校|车站|药店|理发店|干洗店|花店)")
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
N4_WORDS = ("的", "是")
N4_WINDOW = 6


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def verify_inputs():
    pb = PRE.read_bytes()
    if sha16(pb) != PRE_SHA16 or len(pb) != PRE_BYTES:
        raise SystemExit("REV7.1 prereg changed: %s / %d B" % (sha16(pb), len(pb)))
    rb = RULING.read_bytes()
    if sha16(rb) != RULING_SHA16 or len(rb) != RULING_BYTES:
        raise SystemExit("RULING-M5C2-B7 changed: %s / %d B"
                         % (sha16(rb), len(rb)))
    eb = EXTRACT.read_bytes()
    if sha16(eb) != EXTRACT_SHA16 or len(eb) != EXTRACT_BYTES:
        raise SystemExit("M5C2-B5-EXTRACT.json changed: %s / %d B"
                         % (sha16(eb), len(eb)))
    db = DECIDE.read_bytes()
    if sha16(db) != DECIDE_SHA16 or len(db) != DECIDE_BYTES:
        raise SystemExit("M5C2-B5-DECIDE.json changed: %s / %d B"
                         % (sha16(db), len(db)))
    code = Path(__file__).read_bytes()
    return {
        "prereg_rev7_1": {"path": "docs/_work/PREREG-M5-C2-REV7.1.md",
                          "sha16": PRE_SHA16, "bytes": PRE_BYTES},
        "ruling_b7": {"path": "docs/_work/RULING-M5C2-B7.md",
                      "sha16": RULING_SHA16, "bytes": RULING_BYTES},
        "extract": {"path": "kvmem/m2_visibility/m5/out/M5C2-B5-EXTRACT.json",
                    "sha16": EXTRACT_SHA16, "bytes": EXTRACT_BYTES},
        "baseline_decide": {
            "path": "kvmem/m2_visibility/m5/out/M5C2-B5-DECIDE.json",
            "sha16": DECIDE_SHA16, "bytes": DECIDE_BYTES},
        "rule_code_rev7_1": {"path": "kvmem/m2_visibility/m5/"
                                     "run_m5c2_rev7_1_offline.py",
                             "sha16": "88256d274c9993cc", "bytes": 50618},
        "self": {"file": Path(__file__).name, "sha16": sha16(code),
                 "bytes": len(code)},
    }


# =========================== M1: closed-set normalisation ====================
def normalize7(s):
    """rev7.1 N1 (kept for byte-compatibility of the ablation baseline)."""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"(?<=\d)[,，](?=\d{3})", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def _n4_anchor_spans(t):
    spans = [m.span() for m in NUM_RE.finditer(t)]
    spans += [m.span(0) for m in ENTITY_ANCHOR_RE.finditer(t)]
    return spans


def _delete_n4_words(t):
    """N-4': delete only {的,是} inside +/-6 chars of a numeric/entity anchor."""
    anchors = _n4_anchor_spans(t)
    if not anchors:
        return t
    drop = set()
    for a0, a1 in anchors:
        lo = max(0, a0 - N4_WINDOW)
        hi = min(len(t), a1 + N4_WINDOW)
        for i in range(lo, hi):
            if t[i] in N4_WORDS:
                drop.add(i)
    if not drop:
        return t
    return "".join(ch for i, ch in enumerate(t) if i not in drop)


def norm_m1(s, sw):
    """RULING R3 closed-set normalisation N-1..N-5 (matching copy only)."""
    s = s or ""
    if not sw.get("m1"):
        return normalize7(s)
    t = unicodedata.normalize("NFKC", s)                      # N-1
    t = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", t)             # N-2
    t = re.sub(r"(?<=\d)\s+(?=[%s])" % re.escape(
        "".join(sorted(UNIT_CHARS))), "", t)                   # N-3
    t = _delete_n4_words(t)                                   # N-4'
    t = re.sub(r"\s+", "", t)                                 # N-5
    return t


def norm(s, sw):
    return norm_m1(s, sw)


TRAIL_PUNCT_RE = re.compile(r"[。！？!?.]+$")


def _strip_trail(s):
    return TRAIL_PUNCT_RE.sub("", s or "")


def _is_alnum(ch):
    """ASCII alphanumeric only (CJK ideographs are alnum to str.isalnum())."""
    return bool(ch) and ch.isascii() and ch.isalnum()


def literal_in_source(item_n, source_n):
    """Exact literal occurrence with alphanumeric boundary (closed-set match)."""
    if not item_n:
        return False
    start = 0
    while True:
        i = source_n.find(item_n, start)
        if i < 0:
            return False
        j = i + len(item_n)
        left_ok = True
        right_ok = True
        if _is_alnum(item_n[0]) and i > 0 and _is_alnum(source_n[i - 1]):
            left_ok = False
        if (_is_alnum(item_n[-1]) and j < len(source_n)
                and _is_alnum(source_n[j])):
            right_ok = False
        if left_ok and right_ok:
            return True
        start = i + 1


# =========================== item matching ==================================
def matcher(item, sentence, sw):
    """N3 locator (item<->sentence), unchanged except the M1 matching copy."""
    a = norm(item, sw)
    b = norm(sentence, sw)
    if a and a in b:
        return "substring", 1.0
    cov = R5.window_coverage(a, b) if a and b else 0.0
    return ("window" if cov >= 0.90 else "none"), cov


# =========================== R1/R2/R3 =======================================
def r1_r2_r3(entry, evidence, source, valid, sw):
    """rev7.1 r1_r2_r3_rev7 with norm_m1 for every comparison."""
    hits = []
    ev = norm(evidence, sw)
    ent = norm(entry, sw)
    src = norm(source, sw)
    toks = R71.value_tokens(entry)

    r1_detail = []
    for tok, kind in toks:
        tn = norm(tok, sw)
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

    anchors = []
    for a in [t for t, _ in toks] + [ent]:
        a = norm(a, sw)
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
            mt = re.compile(r"(不是|并非|而不是)\s*" + re.escape(anchor)).search(ev)
            if mt:
                hits.append({"rule": "R2", "reason": "negated_pattern",
                             "span": mt.group(0), "anchor": anchor})
                r2_done = True
                break
            mt2 = re.compile(re.escape(anchor) + r"\s*(不是|是错的)").search(ev)
            if mt2:
                hits.append({"rule": "R2", "reason": "negated_after",
                             "span": mt2.group(0), "anchor": anchor})
                r2_done = True
                break

    r3 = None
    if valid:
        for marker in R5.ABSENT_MARKERS:
            if norm(marker, sw) in ev:
                r3 = marker
                hits.append({"rule": "R3", "reason": "absent_marker",
                             "span": marker})
                break
    return hits, r3, r1_detail


def r4_plus(evidence, source, has_r3, sw):
    if has_r3:
        return None
    ev = norm(evidence, sw)
    src = norm(source, sw)
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


# =========================== M2 / M3 item judging ===========================
def judge_item(item, evidence, sentence, source, sw):
    """One item under rev7.2 (M1 normalisation + M2 override + M3 relocation)."""
    mh, cov = matcher(item, sentence, sw)
    valid = (mh != "none")
    item_n = norm(item, sw)
    ev_n = norm(evidence, sw)
    src_n = norm(source, sw)
    sent_n = norm(sentence, sw)
    item_in_source = literal_in_source(item_n, src_n)
    evidence_in_source = bool(ev_n) and ev_n in src_n
    evidence_in_sentence = bool(ev_n) and ev_n in sent_n
    # R5' scope (FP-attribution "answer-as-evidence"): the evidence must be the
    # whole judged answer sentence (trailing sentence punctuation ignored).
    answer_sentence_evidence = (bool(ev_n) and evidence_in_sentence
                                and _strip_trail(ev_n) == _strip_trail(sent_n))

    # M3: evidence that only lives in the answer sentence is not effective.
    relocated = False
    ungrounded = False
    relocation_span = None
    evidence_effective = evidence_in_source
    if (sw.get("m3") and answer_sentence_evidence
            and not evidence_in_source):
        if item_in_source:
            relocated = True
            evidence_effective = True
            pos = src_n.find(item_n)
            relocation_span = {"pos": pos, "text": source}
        else:
            ungrounded = True
            evidence_effective = False

    # R3/R4+ on effective evidence only (M3); ungrounded takes no fabricated
    # penalty and is never absent (U1).
    hits, r3, r1_detail = ([], None, [])
    if not ungrounded:
        hits, r3, r1_detail = r1_r2_r3(item, evidence, source, valid, sw)
        if relocated:
            # relocated source span replaces the answer-sentence evidence
            hits = [h for h in hits if h["rule"] not in ("R3", "R4+")]
            r3 = None
        r4 = r4_plus(evidence, source, r3 is not None, sw)
        if r4 and not relocated:
            hits.append(r4)

    # M2 override: item literal (after M1) in source, evidence not the answer
    # sentence => ignore the extractor's "not mentioned" marks.  Only an
    # override that actually clears the item's absent state is counted.
    override = False
    if sw.get("m2") and item_in_source and not evidence_in_sentence and ev_n:
        bad = [h for h in hits if h["rule"] in ("R3", "R4+")]
        if bad:
            override = True
            hits = [h for h in hits if h["rule"] not in ("R3", "R4+")]
            r3 = None
            if r4_plus(evidence, source, True, sw) is None:
                pass

    numeric_ok = not any(h["rule"] == "R1" for h in hits)
    binding = valid and not ungrounded
    absent = bool(binding and hits)
    if not valid:
        item_verdict = "invalid"
    elif ungrounded:
        item_verdict = UNGROUNDED
    elif absent:
        item_verdict = "absent"
    elif ev_n and ev_n not in src_n and not relocated and not override:
        item_verdict = "unverified"
    else:
        item_verdict = "present"
    first = hits[0] if hits else None
    return {
        "item": item, "evidence": evidence,
        "valid": valid, "matcher_hit": mh, "coverage": round(cov, 6),
        "item_in_source": item_in_source,
        "evidence_in_source": evidence_in_source,
        "evidence_in_sentence": evidence_in_sentence,
        "relocated": relocated, "relocation_span": relocation_span,
        "ungrounded": ungrounded, "override": override,
        "numeric_ok": numeric_ok, "binding": binding, "absent": absent,
        "item_verdict": item_verdict,
        "rule": first["rule"] if first else None,
        "reason": first.get("reason") if first else None,
        "r3_hit": r3 is not None,
        "rule_hits": hits, "value_tokens": r1_detail,
    }


def judge_row(row, sw):
    """One sentence under rev7.2; schema close to rev7.1's judge_row_rev7."""
    sid = row["sid"]
    sent = row["sentence"]
    src = row["source_text"]
    recs = [judge_item(z["item"], z["evidence"], sent, src, sw)
            for z in row["items"]]
    en, dd = R5.derived_plus(sent, src)

    n_ung = sum(1 for z in recs if z["ungrounded"])
    all_ung = bool(recs) and n_ung == len(recs)
    if row["route"] == "empty_source":
        v = "unsupported"
        reason = "empty_source"
    elif row["route"] == "abstain_check":
        v = row["layer0"]["verdict"]
        reason = "layer0_abstain"
    elif not row["parse_ok"]:
        v = "parse_fail"
        reason = "parse_fail"
    elif en:
        v = "undecidable"
        reason = "derived_plus"
    elif not recs:
        v = "undecidable"
        reason = "no_items"
    elif all_ung:
        v = "not-supported"
        reason = ALL_UNGROUNDED_REASON
    elif any(z["absent"] for z in recs if z["binding"]):
        v = "unsupported"
        reason = "binding_item_hit"
    else:
        # rev7.1 aggregation is preserved for every non-ungrounded sentence
        # (A2': 319 sentences must not move); U2 only removes the *new*
        # ungrounded state from the support side.
        v = "supported"
        reason = "no_binding_hit"
    counts = {"invalid": 0, "absent": 0, "unverified": 0, "present": 0,
              UNGROUNDED: 0}
    for z in recs:
        counts[z["item_verdict"]] += 1
    return {
        "sid": sid,
        "verdict": v,
        "verdict_reason": reason,
        "route": row["route"], "parse_ok": row["parse_ok"],
        "derived_rev7_2": bool(en),
        "n_items": len(recs),
        "n_valid": counts["present"] + counts["absent"] + counts["unverified"],
        "n_invalid": counts["invalid"],
        "n_absent": counts["absent"],
        "n_ungrounded": counts[UNGROUNDED],
        "n_unverified": counts["unverified"],
        "n_override": sum(1 for z in recs if z["override"]),
        "n_relocated": sum(1 for z in recs if z["relocated"]),
        "items": recs,
        "derived_detail": dd,
    }


# =========================== target assertions ==============================
def judging_run(rows, sw):
    recs = [judge_row(r, sw) for r in rows]
    return {r["sid"]: r for r in recs}


def diff_vs(decide_by_sid, recs):
    changed = []
    for sid, rec in recs.items():
        old = decide_by_sid[sid]["verdict_rev7"]
        if rec["verdict"] != old:
            changed.append({"sid": sid, "rev7_1": old, "rev7_2": rec["verdict"],
                            "reason": rec["verdict_reason"]})
    return sorted(changed, key=lambda x: x["sid"])


def _item_reasons(items):
    out = []
    for it in items or []:
        out.append({"item": it.get("item"), "evidence": it.get("evidence"),
                    "verdict": it.get("item_verdict"),
                    "rule": it.get("rule"), "reason": it.get("reason")})
    return out


def a1_a2_a3(recs, decide_by_sid):
    a1 = []
    for sid in TARGET_SIDS:
        rec = recs[sid]
        old_row = decide_by_sid[sid]
        old = old_row["verdict_rev7"]
        a1.append({"sid": sid, "mechanism": TARGET_MECH[sid],
                   "rev7_1": old, "rev7_2": rec["verdict"],
                   "rev7_1_item_reasons": _item_reasons(old_row.get("items")),
                   "rev7_2_item_reasons": _item_reasons(rec.get("items")),
                   "rev7_2_reason": rec["verdict_reason"],
                   "detected_change": old != rec["verdict"],
                   "pass": (old == "unsupported"
                            and rec["verdict"] == "supported")})
    changed = diff_vs(decide_by_sid, recs)
    allowed = set(TARGET_SIDS)
    only_targets = {c["sid"] for c in changed} == allowed
    all_to_supported = all(c["rev7_2"] == "supported" for c in changed)
    too_many = [c["sid"] for c in changed if c["sid"] not in allowed]
    became_bad = [c["sid"] for c in changed
                  if decide_by_sid[c["sid"]]["verdict_rev7"] == "supported"
                  and c["rev7_2"] != "supported"]
    a2 = {
        "n_sentences": len(recs),
        "n_changed": len(changed),
        "n_unchanged": len(recs) - len(changed),
        "changed": changed,
        "unexpected_sids": too_many,
        "all_changes_to_supported": all_to_supported,
        "pass": (only_targets and all_to_supported and len(changed) == 7
                 and not became_bad),
    }
    # A3 (leak sentinel) structural: no sentence may move OUT of supported/
    # undecidable INTO supported/undecidable from a non-leak state, and no
    # leak-eligible (rev7.1 supported/undecidable) sentence may change at all.
    leak_eligible = {sid for sid, rec in decide_by_sid.items()
                     if rec["verdict_rev7"] in ("supported", "undecidable")}
    leak_changed = [c for c in changed if c["sid"] in leak_eligible]
    new_bad = [c for c in changed
               if c["rev7_2"] in ("unsupported", "undecidable", "parse_fail")
               and c["rev7_1"] not in ("unsupported", "undecidable", "parse_fail")]
    a3 = {
        "rev7_1_leak": {"k": 0, "n": 29,
                        "source": "b5 RATES aae1b790d19dfa73 (F1 of RULING-M5C2-B7)"},
        "leak_eligible_sentences_changed": leak_changed,
        "new_unsupported_or_undecidable_from_supported": new_bad,
        "leak_delta": 0 if not leak_changed and not new_bad else None,
        "pass": (not leak_changed and not new_bad),
        "note": ("leak can only move if a leak-eligible rev7.1 verdict changes or a "
                 "previously supported sentence becomes unsupported/undecidable; "
                 "neither happens => leak stays 0/29 (no gold read needed)"),
    }
    return a1, a2, a3


# =========================== T1/T2/T3/T4 ====================================
T1_PAIRS = [
    ("做的是保养", "做的是手术"),
    ("4S店", "3S店"),
    ("2万公里", "3万公里"),
    ("8600元", "6800元"),
    ("65寸", "85寸"),
    ("顺丰", "顺风"),
    ("320元", "620元"),
    ("11月15日", "12月15日"),
    ("车损险", "三者险"),
    ("苏宁", "国美"),
    ("3公斤", "5公斤"),
    ("500元", "600元"),
    ("28元", "82元"),
    ("做了", "没做"),
    ("交了", "未交"),
    ("是", "不是"),
]


def t1(sw):
    rows = []
    for a, b in T1_PAIRS:
        na, nb = norm(a, sw), norm(b, sw)
        rows.append({"pair": [a, b], "norm": [na, nb], "distinct": na != nb})
    return {"n_pairs": len(rows), "rows": rows,
            "pass": len(rows) >= 10 and all(r["distinct"] for r in rows)}


def _content_spans(s, min_len=2, max_len=12):
    """Distinct source spans by whitespace-stripped content (T2 candidates)."""
    out = {}
    n = len(s)
    for i in range(n):
        for j in range(i + min_len, min(i + max_len, n) + 1):
            raw = s[i:j]
            if raw != raw.strip():
                continue
            key = re.sub(r"\s+", "", raw)
            if key not in out:
                out[key] = raw
    return out


def _shortest_raw_window(raw, target_norm, sw):
    """Shortest raw substring whose M1 form equals target_norm (grounded span)."""
    if not target_norm:
        return None
    raw = raw or ""
    for ln in range(1, len(raw) + 1):
        for i in range(0, len(raw) - ln + 1):
            if norm(raw[i:i + ln], sw) == target_norm:
                return i, raw[i:i + ln]
    return None


def t2(rows, recs, sw):
    """Span injectivity on the grounded spans the rule engine actually uses.

    A "source span" is the shortest raw source substring whose M1 form is the
    grounded text of a matched item (evidence-in-source, item literal, or
    relocated item).  Different raw spans inside one sentence must not collapse
    to the same normalised text; identical raw text at different positions
    (a repeated phrase) is the same content and is not a collision.
    """
    collisions = []
    checked = 0
    for r in rows:
        rec = recs[r["sid"]]
        raw = r["source_text"]
        spans = {}
        for it in rec["items"]:
            targets = []
            if it["evidence_in_source"]:
                targets.append(norm(it["evidence"], sw))
            if it["item_in_source"]:
                targets.append(norm(it["item"], sw))
            for tn in targets:
                if not tn:
                    continue
                got = _shortest_raw_window(raw, tn, sw)
                if not got:
                    continue
                pos, text = got
                checked += 1
                spans.setdefault((pos, text), tn)
        seen = {}
        for (pos, text), tn in spans.items():
            if tn in seen and seen[tn][1] != text:
                collisions.append({"sid": r["sid"], "a": seen[tn][1],
                                   "b": text, "norm": tn,
                                   "pos_a": seen[tn][0], "pos_b": pos})
            else:
                seen[tn] = (pos, text)
    return {"n_sentences": len(rows), "n_spans_checked": checked,
            "span_definition": ("shortest raw source span whose closed-set M1 "
                                "form is the grounded text of a matched item; "
                                "repeat of identical raw text is not a collision"),
            "n_collisions": len(collisions),
            "collisions": collisions[:20], "pass": len(collisions) == 0}


def t3(rows, recs):
    """Export successful matching spans on the whole b5 set; sample >=20."""
    all_spans = []
    for r in rows:
        rec = recs[r["sid"]]
        src = r["source_text"]
        src_n = norm(src, {"m1": True, "m2": True, "m3": True})
        for it in rec["items"]:
            if it["matcher_hit"] == "none":
                continue
            if it["relocated"]:
                span = {"kind": "relocated_item", "sid": r["sid"],
                        "item": it["item"], "evidence": it["evidence"],
                        "pos": (it["relocation_span"] or {}).get("pos"),
                        "span_text": it["item"]}
            elif it["evidence_in_source"]:
                ev_n = norm(it["evidence"], {"m1": True, "m2": True, "m3": True})
                span = {"kind": "evidence_in_source", "sid": r["sid"],
                        "item": it["item"], "evidence": it["evidence"],
                        "pos": src_n.find(ev_n), "span_text": it["evidence"]}
            else:
                continue
            all_spans.append(span)
    n = len(all_spans)
    sample = [all_spans[i] for i in range(0, n, max(1, n // 20))][:20] if n else []
    return {"n_sentences": len(rows), "n_matched_spans": n,
            "sample_n": len(sample), "sample": sample, "pass": len(sample) >= 20}


T4_CASES = [
    {"sid": "syn-t4-01", "sentence": "运费是 28 元。",
     "source_text": "我在顺丰寄了一件 3 公斤的包裹到成都。",
     "items": [{"item": "运费", "evidence": "运费是 28 元"}],
     "route": "model_extract", "parse_ok": True, "layer0": None},
    {"sid": "syn-t4-02", "sentence": "保价是 500 元。",
     "source_text": "我在顺丰寄了一件 3 公斤的包裹到成都。",
     "items": [{"item": "保价", "evidence": "保价是 500 元"}],
     "route": "model_extract", "parse_ok": True, "layer0": None},
    {"sid": "syn-t4-03", "sentence": "保修期是整机一年。",
     "source_text": "我在苏宁买了台 65 寸电视。",
     "items": [{"item": "保修期", "evidence": "保修期是整机一年"}],
     "route": "model_extract", "parse_ok": True, "layer0": None},
    {"sid": "syn-t4-04", "sentence": "这付药一天喝两次。",
     "source_text": "我在社区药店抓了七付中药。",
     "items": [{"item": "一天喝几次", "evidence": "这付药一天喝两次"}],
     "route": "model_extract", "parse_ok": True, "layer0": None},
]


def t4(sw):
    rows = []
    for c in T4_CASES:
        row = dict(c)
        row["derived"] = False
        rec = judge_row(row, sw)
        rows.append({
            "sid": c["sid"], "sentence": c["sentence"],
            "source_text": c["source_text"],
            "items": [{"item": it["item"], "evidence": it["evidence"],
                       "item_verdict": it["item_verdict"],
                       "ungrounded": it["ungrounded"]} for it in rec["items"]],
            "verdict": rec["verdict"], "reason": rec["verdict_reason"],
            "pass": (rec["verdict"] == "not-supported"
                     and rec["verdict_reason"] == ALL_UNGROUNDED_REASON),
        })
    return {"n_cases": len(rows), "cases": rows,
            "pass": bool(rows) and all(r["pass"] for r in rows)}


# =========================== driver =========================================
def load_rows():
    d = json.loads(EXTRACT.read_bytes().decode("utf-8"))
    if d.get("schema") != "m5c2_b5_extract_v1":
        raise SystemExit("unexpected b5 EXTRACT schema")
    out = []
    for rec in d["records"]:
        route = rec.get("route") or "model_extract"
        layer0 = rec.get("layer0")
        items = R51.judge_items(rec.get("items") or [], rec["source_text"])
        out.append({
            "sid": rec["sid"], "qid": rec["qid"], "scenario": rec["scenario"],
            "sentence": rec["text"], "source_text": rec["source_text"],
            "route": route, "parse_ok": bool(rec.get("parse_ok")),
            "derived": False, "layer0": layer0, "items": items,
            "verdict": None,
        })
    if len(out) != N_SENTENCES:
        raise SystemExit("expected %d sentences, got %d"
                         % (N_SENTENCES, len(out)))
    for r in out:
        r["verdict"] = R71.verdict_v51(r)
    return out


def baseline_check(rows, decide_by_sid):
    """Recomputed rev7.1 verdicts must equal the frozen DECIDE 326/326."""
    mism = []
    for r in rows:
        rec, _items, _dd = R71.judge_row_rev7(r)
        old = decide_by_sid[r["sid"]]["verdict_rev7"]
        if rec["verdict_rev7"] != old:
            mism.append({"sid": r["sid"], "recomputed": rec["verdict_rev7"],
                         "stored": old})
    return {"n_sentences": len(rows), "n_mismatch": len(mism),
            "mismatches": mism[:20], "pass": not mism}


def switches(args):
    sw = {"m1": args.m1, "m2": args.m2, "m3": args.m3}
    return sw


def dev(pins, rows, decide_by_sid, sw):
    recs = judging_run(rows, sw)
    a1, a2, a3 = a1_a2_a3(recs, decide_by_sid)

    # A4: three ablation rows (plus the all-on row)
    ablations = []
    for name, over in (("all_on", {}),
                       ("m1_off", {"m1": False}),
                       ("m2_off", {"m2": False}),
                       ("m3_off", {"m3": False})):
        swx = dict(sw, **over)
        rx = judging_run(rows, swx)
        x1, x2, x3 = a1_a2_a3(rx, decide_by_sid)
        ablations.append({
            "config": name,
            "switches": {k: swx[k] for k in ("m1", "m2", "m3")},
            "a1_fixed": sum(1 for r in x1 if r["pass"]),
            "a1_pass": all(r["pass"] for r in x1),
            "a2_changed": x2["n_changed"],
            "a2_pass": x2["pass"],
            "changed_sids": [c["sid"] for c in x2["changed"]],
            "a3_pass": x3["pass"],
            "n_ungrounded_items": sum(r["n_ungrounded"] for r in rx.values()),
            "n_override_items": sum(r["n_override"] for r in rx.values()),
            "n_relocated_items": sum(r["n_relocated"] for r in rx.values()),
        })

    t1r = t1(sw)
    t2r = t2(rows, recs, sw)
    t3r = t3(rows, recs)
    t4r = t4(sw)

    all_pass = (all(r["pass"] for r in a1) and a2["pass"] and a3["pass"]
                and all(v["pass"] for v in (t1r, t2r, t3r, t4r))
                and ablations[0]["a1_pass"] and ablations[0]["a2_pass"])

    counts = {}
    for rec in recs.values():
        counts[rec["verdict"]] = counts.get(rec["verdict"], 0) + 1
    ung_items = sum(r["n_ungrounded"] for r in recs.values())
    over_items = sum(r["n_override"] for r in recs.values())
    reloc_items = sum(r["n_relocated"] for r in recs.values())

    out = {
        "schema": AME,
        "status": "dev_only（b5 dev；非验收读数）",
        "dev_set": True,
        "acceptance": False,
        "ruling": {"path": "docs/_work/RULING-M5C2-B7.md",
                   "sha16": RULING_SHA16, "bytes": RULING_BYTES},
        "rule_version": "rev7.2",
        "rule_code_base": "run_m5c2_rev7_1_offline.py 88256d274c9993cc",
        "mech_switches": {"m1": sw["m1"], "m2": sw["m2"], "m3": sw["m3"]},
        "m1_items": {"N-1": "全半角 NFKC", "N-2": "千分位删除",
                     "N-3": "数字-单位空白删除", "N-4'": "仅删 {的,是}，锚点±6字符",
                     "N-5": "其余空白删除（仅匹配副本）"},
        "n_sentences": len(recs),
        "n_forward": 0,
        "n_gpu": 0,
        "no_gold_read": True,
        "no_blind_label_read": True,
        "no_rule_change": False,
        "rule_change_scope": "only R3 (M1) / R4 (M2) / R5' (M3) as ruled",
        "verdict_counts_rev7_2": dict(sorted(counts.items())),
        "n_items": sum(r["n_items"] for r in recs.values()),
        "n_ungrounded_items": ung_items,
        "n_override_items": over_items,
        "n_relocated_items": reloc_items,
        "baseline_reproduction": baseline_check(rows, decide_by_sid),
        "A1": {"targets": a1, "fixed": sum(1 for r in a1 if r["pass"]),
               "n": len(a1), "pass": all(r["pass"] for r in a1)},
        "A2_prime": a2,
        "A3_leak_sentinel": a3,
        "A4_ablation": ablations,
        "T1_min_pairs": t1r,
        "T2_span_injectivity": t2r,
        "T3_matched_spans": t3r,
        "T4_ungrounded_synthetic": t4r,
        "all_pass": all_pass,
        "diff_vs_rev7_1": diff_vs(decide_by_sid, recs),
        "sentences": [recs[r["sid"]] for r in rows],
        "determinism": {"timestamps": False, "json_indent": 1,
                        "ensure_ascii": False, "trailing_newline": True,
                        "double_run_expected": "byte-identical"},
        "no_network": True,
        "no_git_commit": True,
    }
    write_json_atomic(ART, out)
    b = ART.read_bytes()
    summary = {
        "schema": AME,
        "artifact": "kvmem/m2_visibility/m5/out/M5C2-REV7-2-DEV.json",
        "artifact_sha16": sha16(b), "artifact_bytes": len(b),
        "mech_switches": out["mech_switches"],
        "all_pass": all_pass,
        "A1": {"fixed": out["A1"]["fixed"], "n": out["A1"]["n"],
               "pass": out["A1"]["pass"],
               "targets": [{"sid": r["sid"], "mech": r["mechanism"],
                            "to": r["rev7_2"], "pass": r["pass"]}
                           for r in a1]},
        "A2_prime": {"n_changed": a2["n_changed"],
                     "n_unchanged": a2["n_unchanged"],
                     "pass": a2["pass"],
                     "changed_sids": [c["sid"] for c in a2["changed"]]},
        "A3": {"pass": a3["pass"], "leak_delta": a3["leak_delta"],
               "note": a3["note"]},
        "A4": ablations,
        "T1": {"pairs": t1r["n_pairs"], "pass": t1r["pass"]},
        "T2": {"spans": t2r["n_spans_checked"],
               "collisions": t2r["n_collisions"], "pass": t2r["pass"]},
        "T3": {"matched_spans": t3r["n_matched_spans"],
               "sample_n": t3r["sample_n"], "pass": t3r["pass"]},
        "T4": {"n": t4r["n_cases"], "pass": t4r["pass"],
               "verdicts": [(c["sid"], c["verdict"], c["reason"])
                            for c in t4r["cases"]]},
        "baseline_reproduction": {"pass": out["baseline_reproduction"]["pass"],
                                  "n_mismatch":
                                  out["baseline_reproduction"]["n_mismatch"]},
        "verdict_counts_rev7_2": out["verdict_counts_rev7_2"],
        "item_states": {"ungrounded": ung_items, "override": over_items,
                        "relocated": reloc_items},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if all_pass else 3


def dry_run(pins):
    print(json.dumps({
        "schema": AME + "_dry_run",
        "status": "dry_run_only",
        "pins": pins,
        "n_forward": 0, "no_gpu": True, "no_model_call": True,
        "writes_any_file": False,
        "planned": {
            "n_sentences": N_SENTENCES,
            "targets": TARGET_SIDS,
            "mechanisms": {"m1": "R3 closed-set normalisation N-1..N-5",
                           "m2": "R4 extractor false-negative override",
                           "m3": "R5' relocation + ungrounded (U1/U2)"},
            "assertions": ["A1", "A2'", "A3", "A4", "T1", "T2", "T3", "T4"],
        },
    }, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--m1", choices=("on", "off"), default="on")
    ap.add_argument("--m2", choices=("on", "off"), default="on")
    ap.add_argument("--m3", choices=("on", "off"), default="on")
    ap.add_argument("--ablate", choices=("m1", "m2", "m3"), default=None,
                    help="single ablation run (also reported in --dev table)")
    ap.add_argument("--no-m1", action="store_true", help="disable M1 (ablation)")
    ap.add_argument("--no-m2", action="store_true", help="disable M2 (ablation)")
    ap.add_argument("--no-m3", action="store_true", help="disable M3 (ablation)")
    a = ap.parse_args()
    pins = verify_inputs()
    if a.dry_run:
        return dry_run(pins)
    rows = load_rows()
    decide = json.loads(DECIDE.read_bytes().decode("utf-8"))
    decide_by_sid = {r["sid"]: r for r in decide["rows"]}
    if len(decide_by_sid) != N_SENTENCES:
        raise SystemExit("DECIDE row count mismatch")
    sw = {"m1": a.m1 == "on", "m2": a.m2 == "on", "m3": a.m3 == "on"}
    sw["m1"] = sw["m1"] and not a.no_m1
    sw["m2"] = sw["m2"] and not a.no_m2
    sw["m3"] = sw["m3"] and not a.no_m3
    if a.ablate:
        sw[a.ablate] = False
    return dev(pins, rows, decide_by_sid, sw)


if __name__ == "__main__":
    sys.exit(main())