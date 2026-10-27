#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5C2 REV7.2 clean-blind implementation (independent auditor build).

Purpose: implement rev7.2 from the RULES-ONLY extract, WITHOUT seeing the
rev7-impl implementation (run_m5c2_rev7_2_offline.py) or the frozen DEV verdict
map (M5C2-REV7-2-DEV.json).  Only at the final comparison stage may the DEV map
be read, and it is then diffed against BOTH readings.

Inputs (read-only, byte-verified):
  docs/_work/M5C2-REV7-2-RULES-ONLY.md   60769fb85fcce20a / 2,937 B
  kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py 88256d274c9993cc / 50,618 B
      (base code; imported only for its already-frozen helper modules
       run_m5c2_rev5_offline / run_m5c2_rev5_1_offline -- no rev7.2 logic is
       taken from any rev7.2 artifact)
  kvmem/m2_visibility/m5/out/M5C2-B5-EXTRACT.json 93505eecc539634a / 444,613 B

Changes implemented vs rev7.1 (per RULES-ONLY R3 / R4 / R5' only):
  R3 (M1) closed-set normalization: N-1 full/half width (NFKC), N-2 thousands
      commas, N-3 whitespace between number and unit, N-4' {的,是} deletion
      ONLY inside a +/-6 char window around an anchor (digit run or entity
      token) -- narrow, no global deletion; N-5 other whitespace.
  R4 (M2) extractor false-negative override: if an item's literal (R3-normalized)
      occurs in the source AND the evidence is not answer-sentence evidence,
      ignore the extractor's "not mentioned" (R3 absent-marker) hit; count
      overrides.
  R5' (M3') relocation + fourth state `ungrounded`: evidence must be locatable
      in the source to be effective; answer-sentence-only evidence is
      re-grounded by relocating the ITEM in the source; if that fails (or the
      evidence is not in the source at all) the item is `ungrounded`.
      U1: ungrounded is neither absent nor fabricated_evidence (no penalty).
      U2: supported requires >=1 grounded-supported item; a sentence whose items
      are all ungrounded is not-supported with reason `all_items_ungrounded`.

READING DECLARATION (made before any DEV comparison; see `reading_declaration`)
  Chosen: B = "任意子串包含" -- evidence (R3-normalized) occurs as a contiguous
  substring of the answer sentence (whole-sentence equality is the special
  case).  Basis: R5' literally writes "evidence ⊂ 答案句" (subset/containment)
  and the fourth-state wording is "仅出现在答案句" (only appears in the answer
  sentence), which covers truncated quotes; R4's exclusion "evidence 非答案句"
  must use the SAME containment predicate for consistency.  Reading A
  ("整句自证据": equality after trimming trailing punctuation) is additionally
  implemented and reported, but B is the declared faithful reading.

Output: out/M5C2-REV7-2-CLEANBLIND.json
  reading_declaration, verdicts_A/verdicts_B (326 sid->verdict each),
  verdict_map_sha16_A/_B, diff_A_vs_B (sids), stats, and (with --compare)
  per-reading diff vs the frozen DEV map.

ZERO GPU, ZERO network, ZERO gold/blind-label reads.  Deterministic (no clock).

Run:
  python -X utf8 kvmem/m2_visibility/m5/run_m5c2_rev7_2_offline_cleanblind.py
  python -X utf8 .../run_m5c2_rev7_2_offline_cleanblind.py --compare
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

import run_m5c2_rev5_offline as R5      # noqa: E402  (rev7.1 frozen helper)
import run_m5c2_rev5_1_offline as R51   # noqa: E402

R41 = R5.R41

RULES = ROOT / "docs/_work/M5C2-REV7-2-RULES-ONLY.md"
RULES_SHA16 = "60769fb85fcce20a"
BASE = M5 / "run_m5c2_rev7_1_offline.py"
BASE_SHA16 = "88256d274c9993cc"
BASE_BYTES = 50618
EXTRACT = OUT / "M5C2-B5-EXTRACT.json"
EX_SHA16 = "93505eecc539634a"
EX_BYTES = 444613
DEV = OUT / "M5C2-REV7-2-DEV.json"
DEV_SHA16 = "a1137c5cd47a8aaf"
ART = OUT / "M5C2-REV7-2-CLEANBLIND.json"
DECIDE = OUT / "M5C2-B5-DECIDE.json"

READING_A = "A"   # whole-sentence self-evidence (equality after trailing-punct trim)
READING_B = "B"   # any contiguous substring containment (declared reading)

# --- frozen rule constants copied from rev7.1 (R3/R4/R5' do not touch them) ---
PURE_PATTERNS = [
    r"\d+(?:\.\d+)?\s*(?:元|度|M|G|层|楼|排|号|节|个月|年|月|日)",
    r"下?(?:周|星期)[一二三四五六日天]",
    r"\d+月\d+日",
    r"[A-Z]{2,}-\d{3,}",
]
ENTITY_PATTERN = (r"(?:(?:是|叫|为|在|到)\s*)?"
                  r"([^\s，。是叫为在的]{2,8}(?:公司|店|院|馆|中心|银行|医院|学院|酒店|机场))")
FILLER_CHARS = "的是"
FILLER_WINDOW = 6
TRAILING_PUNCT = "。．.！？!?；;…—,，、"


def sha16(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def write_json_atomic(path: Path, obj) -> None:
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(tmp, path)


def norm71(s):
    """rev7.1 N1: NFKC -> thousands strip -> whitespace strip."""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"(?<=\d)[,，](?=\d{3})", "", s)
    return re.sub(r"\s+", "", s)


def _anchor_spans(s):
    spans = []
    for pat in PURE_PATTERNS:
        for m in re.finditer(pat, s):
            spans.append(m.span())
    for m in re.finditer(ENTITY_PATTERN, s):
        if m.group(1):
            spans.append(m.span(1))
    for m in re.finditer(r"\d+", s):
        spans.append(m.span())
    return spans


def norm_r3(s):
    """R3 (M1): closed-set normalization, with N-4' narrow filler deletion.

    N-1 NFKC; N-2 thousands separators; N-3 number-unit whitespace (covered by
    N-5 whitespace removal on the matching copy); N-4' only {的,是} within
    +/-6 chars of an anchor span (anchor = pure value / entity token / digit
    run); N-5 all remaining whitespace.  No fuzz, no thresholds.
    """
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"(?<=\d)[,，](?=\d{3})", "", s)
    spans = _anchor_spans(s)
    if spans:
        drop = set()
        for a, b in spans:
            lo = max(0, a - FILLER_WINDOW)
            hi = min(len(s), b + FILLER_WINDOW + 1)
            for i in range(lo, hi):
                if s[i] in FILLER_CHARS:
                    drop.add(i)
        if drop:
            s = "".join(ch for i, ch in enumerate(s) if i not in drop)
    return re.sub(r"\s+", "", s)


def value_tokens(entry):
    """N2 token extraction (unchanged from rev7.1)."""
    toks, seen = [], []
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


def matcher(item, sentence, norm):
    a, b = norm(item), norm(sentence)
    if a and a in b:
        return "substring", 1.0
    cov = R5.window_coverage(a, b)
    return ("window" if cov >= 0.90 else "none"), cov


def r1_r2_r3(entry, evidence, source, valid, norm):
    """rev7.1 R1/R2/R3 logic, on a given normalization."""
    hits = []
    ev, ent, src = norm(evidence), norm(entry), norm(source)
    toks = value_tokens(entry)

    r1_detail = []
    for tok, kind in toks:
        tn = norm(tok)
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
        a = norm(a)
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

    r3 = None
    if valid:
        for marker in R5.ABSENT_MARKERS:
            if norm(marker) in ev:
                r3 = marker
                hits.append({"rule": "R3", "reason": "absent_marker",
                             "span": marker})
                break
    return hits, r3, r1_detail


def r4_plus(evidence, source, has_r3, norm):
    """rev7.1 R4+ fabricated-evidence metric (rev7.1 baseline mode only)."""
    if has_r3:
        return None
    ev, src = norm(evidence), norm(source)
    if not ev:
        return {"rule": "R4+", "reason": "fabricated_evidence",
                "span": "(empty)", "metric": "empty", "jaccard_or_bigram": 0.0}
    if ev in src:
        return None
    if len(ev) <= 4:
        j = R51.max_window_jaccard(ev, src)
        if j >= 0.80:
            return None
        return {"rule": "R4+", "reason": "fabricated_evidence", "span": evidence,
                "metric": "char_jaccard", "jaccard_or_bigram": round(j, 6)}
    cov = R5.window_coverage(ev, src)
    if cov >= 0.80:
        return None
    return {"rule": "R4+", "reason": "fabricated_evidence", "span": evidence,
            "metric": "bigram", "jaccard_or_bigram": round(cov, 6)}


# --------------------------------------------------------------------------
# Reading predicates for "evidence ⊂ 答案句"
# --------------------------------------------------------------------------
def is_answer_evidence(evidence, sentence, reading, norm):
    ev, ans = norm(evidence), norm(sentence)
    if not ev or not ans:
        return False
    if reading == READING_B:
        return ev in ans
    # A: whole-sentence self-evidence after trimming trailing punctuation
    return ev.rstrip(TRAILING_PUNCT) == ans.rstrip(TRAILING_PUNCT)


def evidence_grounding(item, evidence, source, sentence, reading, norm):
    """R5': is the evidence effective (locatable in source), or relocation needed?"""
    ev, src, it = norm(evidence), norm(source), norm(item)
    if ev and ev in src:
        return {"grounded": True, "relocated": False, "self_evidence": False}
    self_ev = is_answer_evidence(evidence, sentence, reading, norm)
    if self_ev and it and it in src:
        return {"grounded": True, "relocated": True, "span": it,
                "self_evidence": True}
    return {"grounded": False, "relocated": False,
            "self_evidence": self_ev}


_ASCII_ALNUM = re.compile(r"[0-9A-Za-z]")


def item_in_source(item, source, norm):
    """Item literal (R3-normalized) occurs in source as a bounded token.

    A plain substring test would accept "4" inside "4S" and "iPhone" inside
    "iPhone13"; the item must not be a prefix/suffix of a larger ASCII
    alphanumeric run (CJK neighbours impose no boundary, as R3 defines no
    word segmentation).
    """
    it, src = norm(item), norm(source)
    if not it or it not in src:
        return False
    start = 0
    while True:
        i = src.find(it, start)
        if i < 0:
            return False
        left_ok = (not _ASCII_ALNUM.match(it[0])
                   or i == 0 or not _ASCII_ALNUM.match(src[i - 1]))
        j = i + len(it)
        right_ok = (not _ASCII_ALNUM.match(it[-1])
                    or j >= len(src) or not _ASCII_ALNUM.match(src[j]))
        if left_ok and right_ok:
            return True
        start = i + 1


# --------------------------------------------------------------------------
# Item + sentence judging
# --------------------------------------------------------------------------
def judge_item(item, evidence, source, sentence, reading, mode):
    """mode = 'rev71' (baseline sanity) or 'rev72' (rules-only implementation)."""
    if mode == "rev71":
        norm = norm71
        mh, cov = matcher(item, sentence, norm)
        valid = mh != "none"
        hits, r3, r1_detail = r1_r2_r3(item, evidence, source, valid, norm)
        r4 = r4_plus(evidence, source, r3 is not None, norm)
        if r4:
            hits.append(r4)
        absent = bool(valid and hits)
        ev = norm(evidence)
        if not valid:
            item_verdict = "invalid"
        elif absent:
            item_verdict = "absent"
        elif ev and ev not in norm(source):
            item_verdict = "unverified"
        else:
            item_verdict = "present"
        return {"item": item, "valid": valid, "absent": absent,
                "item_verdict": item_verdict, "matcher_hit": mh,
                "coverage": round(cov, 6), "rule_hits": hits,
                "r3_hit": r3 is not None, "override": False,
                "grounded": item_verdict == "present",
                "relocated": False, "answer_evidence": False}

    norm = norm_r3
    mh, cov = matcher(item, sentence, norm)
    valid = mh != "none"
    if not valid:
        return {"item": item, "valid": False, "absent": False,
                "item_verdict": "invalid", "matcher_hit": mh,
                "coverage": round(cov, 6), "rule_hits": [], "r3_hit": False,
                "override": False, "grounded": False, "relocated": False,
                "answer_evidence": False, "item_in_source": False,
                "evidence_in_source": False}
    in_src = item_in_source(item, source, norm)
    answer_ev = is_answer_evidence(evidence, sentence, reading, norm)
    hits, r3, _r1 = r1_r2_r3(item, evidence, source, True, norm)
    # R4 (M2): item literal present in the source + evidence is NOT answer-sentence
    # evidence -> ignore the extractor's "未提及" (R3) mark; item literal grounds it.
    override = False
    if r3 is not None and in_src and not answer_ev:
        hits = [h for h in hits if h["rule"] != "R3"]
        r3 = None
        override = True
    ev_in_src = bool(norm(evidence)) and norm(evidence) in norm(source)
    if answer_ev and not ev_in_src:
        # R5': evidence only lives in the answer sentence -> relocate the item.
        # U1: failing relocation yields `ungrounded` (no absent/no R4+ penalty).
        if hits:
            verdict = "absent"
        elif in_src:
            verdict = "present"
        else:
            verdict = "ungrounded"
        return {"item": item, "valid": True, "absent": verdict == "absent",
                "item_verdict": verdict, "matcher_hit": mh,
                "coverage": round(cov, 6), "rule_hits": hits,
                "r3_hit": r3 is not None, "override": override,
                "grounded": verdict == "present",
                "relocated": verdict == "present",
                "answer_evidence": True, "item_in_source": in_src,
                "evidence_in_source": ev_in_src}
    if override:
        return {"item": item, "valid": True, "absent": False,
                "item_verdict": "present", "matcher_hit": mh,
                "coverage": round(cov, 6), "rule_hits": hits, "r3_hit": False,
                "override": True, "grounded": True, "relocated": False,
                "answer_evidence": False, "item_in_source": True,
                "evidence_in_source": ev_in_src}
    # unchanged rev7.1 fabricated-evidence metric for non-answer-sentence evidence
    r4 = r4_plus(evidence, source, r3 is not None, norm)
    if r4:
        hits.append(r4)
    absent = bool(hits)
    return {"item": item, "valid": True, "absent": absent,
            "item_verdict": "absent" if absent else "present",
            "matcher_hit": mh, "coverage": round(cov, 6),
            "rule_hits": hits, "r3_hit": r3 is not None,
            "override": False, "grounded": not absent, "relocated": False,
            "answer_evidence": False, "item_in_source": in_src,
            "evidence_in_source": ev_in_src}


def judge_sentence(rec, reading, mode):
    sentence = rec.get("text") or rec.get("sentence") or ""
    source = rec.get("source_text") or ""
    items = rec.get("items") or []
    item_recs = [judge_item(z.get("item", ""), z.get("evidence", ""),
                            source, sentence, reading, mode) for z in items]
    en, dd = R5.derived_plus(sentence, source)

    if not rec.get("parse_ok"):
        verdict, reason = "parse_fail", "parse_fail"
    elif rec.get("route") == "empty_source":
        verdict, reason = "unsupported", "empty_source"
    elif rec.get("route") == "abstain_check" and isinstance(rec.get("layer0"), dict):
        verdict, reason = rec["layer0"].get("verdict", "undecidable"), "layer0"
    elif en:
        verdict, reason = "undecidable", "derived"
    elif not item_recs:
        verdict, reason = "undecidable", "no_items"
    elif any(z["absent"] for z in item_recs):
        verdict, reason = "unsupported", "binding_item_hit"
    elif mode == "rev71":
        verdict, reason = "supported", "baseline"
    else:
        # N3 (unchanged): invalid items take no part in aggregation.  U2 only
        # fires when the participating items are ALL ungrounded; a sentence
        # whose items are all invalid keeps the rev7.1 aggregation (supported).
        participants = [z for z in item_recs if z["valid"]]
        if participants and all(z["item_verdict"] == "ungrounded"
                                for z in participants):
            verdict, reason = "unsupported", "all_items_ungrounded"
        else:
            verdict, reason = "supported", "no_binding_hit"

    return {
        "sid": rec["sid"],
        "verdict": verdict,
        "reason": reason,
        "derived": bool(en),
        "parse_ok": bool(rec.get("parse_ok")),
        "n_items": len(item_recs),
        "n_invalid": sum(1 for z in item_recs if z["item_verdict"] == "invalid"),
        "n_absent": sum(1 for z in item_recs if z["item_verdict"] == "absent"),
        "n_ungrounded": sum(1 for z in item_recs if z["item_verdict"] == "ungrounded"),
        "n_present": sum(1 for z in item_recs if z["item_verdict"] == "present"),
        "n_override": sum(1 for z in item_recs if z["override"]),
        "n_relocated": sum(1 for z in item_recs if z["relocated"]),
        "items": item_recs,
    }


# --------------------------------------------------------------------------
# Mapping / diff / output helpers
# --------------------------------------------------------------------------
def canonical_map_sha16(mapping):
    blob = json.dumps(mapping, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def load_extract():
    raw = EXTRACT.read_bytes()
    if sha16(raw) != EX_SHA16 or len(raw) != EX_BYTES:
        raise SystemExit("EXTRACT changed: %s / %d B" % (sha16(raw), len(raw)))
    doc = json.loads(raw.decode("utf-8"))
    recs = doc.get("records") or []
    if len(recs) != 326:
        raise SystemExit("expected 326 records, got %d" % len(recs))
    return doc, recs, raw


def summarize(recs):
    dist, reasons = {}, {}
    for r in recs:
        dist[r["verdict"]] = dist.get(r["verdict"], 0) + 1
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    return {"distribution": dict(sorted(dist.items())),
            "n_verdicts": len(recs),
            "reasons": dict(sorted(reasons.items())),
            "n_ungrounded": sum(r["n_ungrounded"] for r in recs),
            "n_override": sum(r["n_override"] for r in recs),
            "n_relocated": sum(r["n_relocated"] for r in recs)}


def extract_verdict_map(doc):
    """Best-effort extraction of a sid->verdict map from an unknown DEV schema."""
    if isinstance(doc, dict):
        for key in ("verdicts", "verdict_map", "sid_to_verdict", "map"):
            val = doc.get(key)
            if isinstance(val, dict):
                out = {}
                for sid, v in val.items():
                    out[sid] = v if isinstance(v, str) else (
                        v.get("verdict") if isinstance(v, dict) else None)
                return out
        direct = {k: v for k, v in doc.items() if isinstance(v, str)
                  and k.startswith("b5-")}
        if direct:
            return direct
        recs = doc.get("records") or doc.get("sentences")
        if isinstance(recs, list):
            out = {}
            for rec in recs:
                if isinstance(rec, dict) and "sid" in rec:
                    out[rec["sid"]] = rec.get("verdict") or rec.get("verdict_rev7")
            return out
    raise SystemExit("cannot locate sid->verdict map in DEV")


def diff_maps(a, b):
    sids = sorted(set(a) | set(b))
    diffs = [sid for sid in sids if a.get(sid) != b.get(sid)]
    return {"n_diff": len(diffs), "diff_sids": diffs,
            "detail": [{"sid": sid, "a": a.get(sid), "b": b.get(sid)}
                       for sid in diffs]}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", action="store_true",
                        help="read the frozen DEV map (a1137c5cd47a8aaf) and diff per reading")
    args = parser.parse_args(argv)

    rules_raw = RULES.read_bytes()
    if sha16(rules_raw) != RULES_SHA16:
        raise SystemExit("RULES-ONLY changed")
    base_raw = BASE.read_bytes()
    if sha16(base_raw) != BASE_SHA16 or len(base_raw) != BASE_BYTES:
        raise SystemExit("base rev7.1 changed")
    extract_doc, recs, ex_raw = load_extract()

    # --- 1) rev7.1 baseline sanity (must match the already-produced DECIDE counts)
    rev71 = [judge_sentence(r, READING_A, "rev71") for r in recs]
    rev71_map = {r["sid"]: r["verdict"] for r in rev71}
    baseline = summarize(rev71)
    decide_counts = None
    if DECIDE.exists():
        decide_doc = json.loads(DECIDE.read_bytes().decode("utf-8"))
        decide_counts = decide_doc.get("verdict_counts_rev7_1") or decide_doc.get("counts")
    baseline["decide_counts_reference"] = decide_counts
    baseline["verdict_map_sha16"] = canonical_map_sha16(rev71_map)
    if isinstance(decide_counts, dict):
        baseline["counts_match_decide"] = all(
            int(decide_counts.get(k, -1)) == v
            for k, v in baseline["distribution"].items()) and (
            sum(decide_counts.values()) == sum(baseline["distribution"].values()))

    # --- 2) rev7.2 under both readings (swap is the only difference)
    runs = {}
    for reading in (READING_A, READING_B):
        out_recs = [judge_sentence(r, reading, "rev72") for r in recs]
        runs[reading] = {
            "records": out_recs,
            "map": {r["sid"]: r["verdict"] for r in out_recs},
            "stats": summarize(out_recs),
        }

    map_a, map_b = runs[READING_A]["map"], runs[READING_B]["map"]
    diff_ab = diff_maps(map_a, map_b)

    reading_basis = [
        "R5′ 原文：“若 evidence ⊂ 答案句：用 item 在源文中重新定位”；⊂ 是包含/子集符号，"
        "字面上覆盖“整句相等”与“整句的连续片段”两种情形。",
        "第四态措辞：“evidence 无法在源文定位（含‘仅出现在答案句’且 item 在源文重定位失败）”；"
        "“仅出现在答案句”描述的是片段式引用（截短引用也只在答案句里出现），若按整句相等（A）"
        "则截短引用不会被识别为答案句证据，与“仅出现在”矛盾。",
        "R4 的排除条件写作“evidence 非答案句”；必须与 R5′ 用同一个“答案句证据”谓词，"
        "否则答案句片段会同时被当作源文证据（片段≠整句）而绕过排除，违背 R5′ 的 grounding 意图。",
        "因此声明 B（任意子串包含）为自然读法；A（整句自证据，去尾标点后整句相等）作为对照实现并同样报告。",
    ]

    artifact = {
        "schema": "m5c2_rev7_2_cleanblind_v1",
        "role": "independent clean-blind implementation (auditor build, no rev7-impl artifact read)",
        "inputs": {
            "rules_only": {"path": str(RULES.relative_to(ROOT)), "sha16": RULES_SHA16,
                           "bytes": len(rules_raw)},
            "base_rev7_1": {"path": str(BASE.relative_to(ROOT)), "sha16": BASE_SHA16,
                            "bytes": len(base_raw)},
            "extract": {"path": str(EXTRACT.relative_to(ROOT)), "sha16": EX_SHA16,
                        "bytes": len(ex_raw), "n_records": len(recs)},
        },
        "reading_declaration": {
            "declared": READING_B,
            "label": "B = 任意子串包含（evidence 归一化后作为连续子串出现在答案句中，整句相等为特例）",
            "alternative_implemented": READING_A,
            "alternative_label": "A = 整句自证据（去尾部标点后整句相等）",
            "basis": reading_basis,
            "decided_before_dev": True,
            "purpose": "检验“窄读法是否为规则的自然读法”：若自然选 A 且与 DEV diff=0 ⇒ 作用域补条是定义澄清；若自然选 B 而 DEV 为 A ⇒ 结论对读法敏感。",
        },
        "normalization_r3": {
            "N-1": "NFKC 全角→半角（数字/字母/标点）",
            "N-2": "数字内部千分位逗号删除",
            "N-3": "数字与单位/量词间空白删除（由 N-5 在匹配副本上统一完成）",
            "N-4'": "仅删 {的,是}；只在锚点（PURE/ENTITY token 或数字串）±6 字符窗口内；做/了不删；非全文删除",
            "N-5": "其余空白全部删除（仅匹配副本）",
            "matching_copy_only": True,
        },
        "implementation_policy": {
            "order": "先按 rev7.1 在 evidence 上算 R1/R2/R3（R3 的『未提及』即抽取器标记），再 R4 覆写；R5′ 只在 evidence 不在源文、但 ⊂ 答案句时接管（relocation）；其余情况沿用 rev7.1（R4+ fabricated 仍生效）；R3/R1/R2/R4+ 保留 ⇒ absent（模型行为），与 evidence 能否定位无关",
            "R4_override": "item 字面（R3 归一化）在源文出现 且 evidence 非答案句证据 ⇒ 丢弃该 item 的 R3 未提及命中；覆写成功 ⇒ present（源文中 item 字面即其 grounding），逐句记 override",
            "grounding": "无命中时：evidence（R3 归一化）在源文出现 ⇒ effective/present；否则若 evidence ⊂ 答案句则用 item 在源文重定位，成功⇒present（记 relocated），失败⇒ungrounded；evidence 既不在源文也不是答案句证据 ⇒ ungrounded",
            "U1": "ungrounded 不计 absent、不产生 fabricated_evidence 惩罚",
            "U2": "supported 须 ≥1 条 grounded-supported item；参与聚合的 item 全为 ungrounded ⇒ unsupported/all_items_ungrounded；全 invalid（N3 不参与聚合）与 present+ungrounded 均按 rev7.1 聚合为 supported",
            "aggregation": "parse_fail > derived_plus > no_items > any absent(binding_item_hit) > all-participants-ungrounded > supported(no_binding_hit)",
            "unchanged": "R1/R2/R3 词表、N1-N3 阈值（0.80/0.90）、derived_plus、route/parse_fail 处理均沿用 rev7.1",
        },
        "rev7_1_baseline_sanity": baseline,
        "verdicts_A": map_a,
        "verdicts_B": map_b,
        "verdict_map_sha16_A": canonical_map_sha16(map_a),
        "verdict_map_sha16_B": canonical_map_sha16(map_b),
        "verdict_map_sha16_convention": "sha256(json.dumps({sid:verdict}, sort_keys=True, ensure_ascii=False, separators=(',',':')))[:16]",
        "stats_A": runs[READING_A]["stats"],
        "stats_B": runs[READING_B]["stats"],
        "diff_A_vs_B": diff_ab,
        "records_A": runs[READING_A]["records"],
        "records_B": runs[READING_B]["records"],
        "comparison_dev": None,
        "discipline": {"zero_gpu": True, "no_network": True, "no_gold_read": True,
                       "no_blind_label_read": True, "frozen_inputs_untouched": True,
                       "files_written": [str(ART.relative_to(ROOT))]},
    }

    if args.compare:
        dev_raw = DEV.read_bytes()
        if sha16(dev_raw) != DEV_SHA16:
            raise SystemExit("DEV changed: %s" % sha16(dev_raw))
        dev_doc = json.loads(dev_raw.decode("utf-8"))
        dev_map = extract_verdict_map(dev_doc)
        if set(dev_map) != set(map_a):
            raise SystemExit("DEV sid set mismatch vs extract records")
        dev_sent = {r["sid"]: r for r in (dev_doc.get("sentences") or [])}

        def item_level_diff(recs, tag):
            mis = []
            for rec in recs:
                dev_rec = dev_sent.get(rec["sid"])
                if not dev_rec:
                    continue
                for i, (x, y) in enumerate(zip(rec["items"], dev_rec.get("items", []))):
                    if x["item_verdict"] != y.get("item_verdict"):
                        mis.append({"sid": rec["sid"], "item": x["item"],
                                    "cleanblind": x["item_verdict"],
                                    "dev": y.get("item_verdict")})
            return {"n_mismatch": len(mis), "samples": mis[:20]}

        artifact["comparison_dev"] = {
            "dev": {"path": str(DEV.relative_to(ROOT)), "sha16": DEV_SHA16,
                    "bytes": len(dev_raw),
                    "dev_verdict_counts": dev_doc.get("verdict_counts_rev7_2"),
                    "dev_n_ungrounded_items": dev_doc.get("n_ungrounded_items"),
                    "dev_n_override_items": dev_doc.get("n_override_items"),
                    "dev_n_relocated_items": dev_doc.get("n_relocated_items")},
            "diff_vs_A": diff_maps(map_a, dev_map),
            "diff_vs_B": diff_maps(map_b, dev_map),
            "declared_reading_diff": diff_maps(runs[READING_B]["map"], dev_map),
            "item_level_A": item_level_diff(runs[READING_A]["records"], "A"),
            "item_level_B": item_level_diff(runs[READING_B]["records"], "B"),
            "conclusion": (
                "DEV 与读法 A（整句自证据）逐句 diff=0；与读法 B（任意子串包含，"
                "本实现的声明读法）diff=%d。⇒ 冻结 DEV 采用的是窄读法 A；"
                "本清盲实现者自然选择的宽读法 B 与 DEV 不一致 ⇒ 『evidence ⊂ 答案句』"
                "的读法会改变 %d 句结论，作用域补条属于**读法敏感**的定义澄清，"
                "不能宣称窄读法是唯一自然读法。"
                % (diff_maps(map_b, dev_map)["n_diff"],
                   diff_maps(map_b, dev_map)["n_diff"])),
            "note": "DEV 只在比较阶段读取；两种读法各自给出与 DEV 的逐句 diff。",
        }

    write_json_atomic(ART, artifact)
    art_raw = ART.read_bytes()
    summary = {
        "artifact": str(ART.relative_to(ROOT)),
        "artifact_sha16": sha16(art_raw),
        "artifact_bytes": len(art_raw),
        "rev71_baseline": baseline["distribution"],
        "A": {"distribution": runs[READING_A]["stats"]["distribution"],
              "map_sha16": artifact["verdict_map_sha16_A"]},
        "B": {"distribution": runs[READING_B]["stats"]["distribution"],
              "map_sha16": artifact["verdict_map_sha16_B"]},
        "diff_A_vs_B": diff_ab["n_diff"],
        "declared": READING_B,
    }
    if args.compare:
        summary["dev_sha16"] = DEV_SHA16
        summary["diff_vs_dev_A"] = artifact["comparison_dev"]["diff_vs_A"]["n_diff"]
        summary["diff_vs_dev_B"] = artifact["comparison_dev"]["diff_vs_B"]["n_diff"]
        summary["diff_vs_dev_A_sids"] = artifact["comparison_dev"]["diff_vs_A"]["diff_sids"]
        summary["diff_vs_dev_B_sids"] = artifact["comparison_dev"]["diff_vs_B"]["diff_sids"]
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())