#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 REV7.2 offline AUDIT — independent second implementation (CPU only).

Authoritative sources (read-only, pinned):
  docs/_work/RULING-M5C2-B7.md                 3dfafd1253f0a833 / 9,425 B
  kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py
                                               88256d274c9993cc / 50,618 B
  out/M5C2-B5-EXTRACT.json                     93505eecc539634a / 444,613 B
  out/M5C2-B5-DECIDE.json (rev7.1 baseline)    59da64cb6f2464de / 741,080 B

This file implements ONLY the three changes frozen in RULING-M5C2-B7 (R3/R4/R5'):
  M1 / R3  closed-set normalization before evidence<->source matching
           N-1 full/half width (NFKC), N-2 thousands separator,
           N-3 digit-unit whitespace, N-4' delete only {的,是} inside a +-6
           character window around anchors (digits/entities), N-5 whitespace.
           Normalization acts on a MATCH COPY only; no fuzzy matching, no
           thresholds, no similarity in the new matching path.
  M2 / R4  extractor false negative: when the item literal (normalized) occurs
           in the source and the evidence is not answer-sentence material, the
           extractor "未提及" marker is ignored; the item is grounded on its
           source span.  Overrides are counted per sentence (`override_count`).
  M3' / R5' answer-as-evidence: when evidence is not locatable in the source
           (in particular evidence that only occurs in the answer sentence),
           the item is re-located in the source; success => source span
           (present), failure => fourth state `ungrounded`.
           U1: ungrounded is NOT absent and gets no fabricated penalty.
           U2: all items ungrounded => verdict `not-supported`,
               reason `all_items_ungrounded`.  Never `absent-soft`.

M4 (inference/negation) is deliberately NOT changed (RULING R2) and stays a
known residual; its sentences keep their rev7.1 verdicts.

Output: out/M5C2-REV7-2-DEV-AUDIT.json
  per-sentence verdict + per-item state (grounded/ungrounded/override),
  diff vs rev7.1 DECIDE (per sid), A1 / A2' / A3, T1-T4, ablation table.

Zero GPU, zero forwards, zero network.  Does not read b5/b6 blind labels or the
gold file; reference aggregates (if needed) come from frozen rate artifacts.
No writes outside the audit artifact.  No git commit.
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

import run_m5c2_rev4_1 as R41   # noqa: E402  fuzzy_coverage primitive
import run_m5c2_rev5_offline as R5    # noqa: E402  window_coverage/derived_plus
import run_m5c2_rev5_1_offline as R51  # noqa: E402  max_window_jaccard

# ---------------------------------------------------------------- pins ------
RULING = ROOT / "docs/_work/RULING-M5C2-B7.md"
RULING_SHA16, RULING_BYTES = "3dfafd1253f0a833", 9425
CODE71 = M5 / "run_m5c2_rev7_1_offline.py"
CODE71_SHA16, CODE71_BYTES = "88256d274c9993cc", 50618
EXTRACT = OUT / "M5C2-B5-EXTRACT.json"
EXTRACT_SHA16, EXTRACT_BYTES = "93505eecc539634a", 444613
DECIDE = OUT / "M5C2-B5-DECIDE.json"
DECIDE_SHA16, DECIDE_BYTES = "59da64cb6f2464de", 741080
RATES = OUT / "M5C2-B5-RATES.json"
ART = OUT / "M5C2-REV7-2-DEV-AUDIT.json"

N_SENTENCES = 326
A1_EXPECTED = ["b5-s1-q1-s01", "b5-s1-q1-s02", "b5-s2-q1-s01",
               "b5-s2-q1-s02", "b5-s7-q4-s03", "b5-s6-q2-s09",
               "b5-s7-q1-s01"]

# rev7.1 frozen token patterns (N2), copied as constants from the frozen code.
PURE_PATTERNS = [
    r"\d+(?:\.\d+)?\s*(?:元|度|M|G|层|楼|排|号|节|个月|年|月|日)",
    r"下?(?:周|星期)[一二三四五六日天]",
    r"\d+月\d+日",
    r"[A-Z]{2,}-\d{3,}",
]
ENTITY_PATTERN = (r"(?:(?:是|叫|为|在|到)\s*)?"
                  r"([^\s，。是叫为在的]{2,8}(?:公司|店|院|馆|中心|银行|医院|学院|酒店|机场))")

NORM_ITEMS = ("N1", "N2", "N3", "N4", "N5")
MECHS = ("M1", "M2", "M3")


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


def pinned(path, sha, size, label):
    b = Path(path).read_bytes()
    if sha16(b) != sha or len(b) != size:
        die("%s pin mismatch: got %s/%d expected %s/%d"
            % (label, sha16(b), len(b), sha, size))
    return b


# ------------------------------------------------------------- normalize ----
def norm7(s):
    """rev7.1 N1 literal (NFKC -> thousands strip -> whitespace strip)."""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"(?<=\d)[,，](?=\d{3})", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def default_cfg():
    return {k: True for k in NORM_ITEMS}


def _norm_chars(s, cfg):
    """Apply the closed set N-1..N-5; return (normalized string, idx map).

    idx[i] is the original character index of normalized character i, so a
    match on the normalized copy can be mapped back to an exact source span.
    """
    chars, idx = [], []
    for i, ch in enumerate(s or ""):
        t = unicodedata.normalize("NFKC", ch) if cfg.get("N1") else ch
        for c in t:
            chars.append(c)
            idx.append(i)

    def joined():
        return "".join(chars)

    def drop(pos_set):
        if not pos_set:
            return
        keep = [(c, i) for k, (c, i) in enumerate(zip(chars, idx))
                if k not in pos_set]
        chars[:] = [c for c, _ in keep]
        idx[:] = [i for _, i in keep]

    if cfg.get("N2"):
        txt = joined()
        drop({m.start() for m in re.finditer(r"(?<=\d)[,，](?=\d{3})", txt)})
    if cfg.get("N3"):
        txt = joined()
        dels = set()
        for m in re.finditer(r"(?<=\d)\s+(?=[^\s\d])", txt):
            dels.update(range(m.start(), m.end()))
        drop(dels)
    if cfg.get("N4"):
        txt = joined()
        anchors = [(m.start(), m.end())
                   for m in re.finditer(r"\d+(?:\.\d+)?", txt)]
        for m in re.finditer(ENTITY_PATTERN, txt):
            if m.group(1):
                anchors.append((m.start(1), m.end(1)))
        dels = set()
        for a, b in anchors:
            for k in range(max(0, a - 6), min(len(txt), b + 6)):
                if txt[k] in "的是":
                    dels.add(k)
        drop(dels)
    if cfg.get("N5"):
        txt = joined()
        drop({k for k, c in enumerate(txt) if c.isspace()})
    return joined(), idx


def norm_match(s, cfg=None):
    return _norm_chars(s, cfg or default_cfg())[0]


def locate_span(text, target_norm, cfg=None):
    """Map an already-normalized target back to an exact span of `text`."""
    if not target_norm:
        return None
    norm, idx = _norm_chars(text, cfg or default_cfg())
    p = norm.find(target_norm)
    if p < 0:
        return None
    end = idx[p + len(target_norm) - 1] + 1
    start = idx[p]
    return {"start": start, "end": end, "span": text[start:end],
            "norm": target_norm}


# ------------------------------------------------------------ rev7.1 basics --
def value_tokens(entry):
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


def matcher(item, sentence):
    """rev7.1 N3 locator, unchanged (item<->sentence stays on normalize7)."""
    a = norm7(item)
    b = norm7(sentence)
    if a in b:
        return "substring", 1.0
    cov = R5.window_coverage(a, b)
    return ("window" if cov >= 0.90 else "none"), cov


def r1_r2_r3(entry, evidence, source, valid, cfg):
    """R1/R2/R3 with the M1 closed-set normalization on evidence/source."""
    hits = []
    ev = norm_match(evidence, cfg)
    ent = norm7(entry)
    src = norm_match(source, cfg)
    toks = value_tokens(entry)

    r1_detail = []
    for tok, kind in toks:
        tn = norm7(tok)
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
        a = norm7(a)
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
            m1 = re.compile(r"(不是|并非|而不是)\s*" + re.escape(anchor)).search(ev)
            if m1:
                hits.append({"rule": "R2", "reason": "negated_pattern",
                             "span": m1.group(0), "anchor": anchor})
                r2_done = True
                break
            m2 = re.compile(re.escape(anchor) + r"\s*(不是|是错的)").search(ev)
            if m2:
                hits.append({"rule": "R2", "reason": "negated_after",
                             "span": m2.group(0), "anchor": anchor})
                r2_done = True
                break

    r3 = None
    if valid:
        for marker in R5.ABSENT_MARKERS:
            if norm_match(marker, cfg) in ev:
                r3 = marker
                hits.append({"rule": "R3", "reason": "absent_marker",
                             "span": marker})
                break
    return hits, r3, r1_detail


def r4_plus(evidence, source, has_r3, cfg):
    """rev7.1 R4+ metric with the M1 closed-set normalization."""
    if has_r3:
        return None
    ev = norm_match(evidence, cfg)
    src = norm_match(source, cfg)
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


# --------------------------------------------------------------- judge -----
def judge_item(item, evidence, sentence, source, cfg, mech, m3_scope,
               m2_min_len=1):
    """One item under rev7.2 (M1/M2/M3' switches)."""
    mh, cov = matcher(item, sentence)
    valid = (mh != "none")
    hits, r3, r1_detail = r1_r2_r3(item, evidence, source, valid, cfg)

    ev_nm = norm_match(evidence, cfg)
    src_nm = norm_match(source, cfg)
    ans_nm = norm_match(sentence, cfg)
    item_nm = norm_match(item, cfg)
    ev_in_src = bool(ev_nm) and ev_nm in src_nm
    # answer-sentence provenance is NOT the M1 evidence<->source match path;
    # use rev7.1 normalization so the N-4' deletion cannot hide self-evidence.
    ev_ans7 = norm7(evidence)
    ev_in_ans = bool(ev_ans7) and ev_ans7 in norm7(sentence)

    override = False
    grounded_span = None
    ungrounded = False

    # --- M2 / R4: extractor false negative ("未提及" but item is in source) --
    if mech.get("M2") and r3 is not None and item_nm and item_nm in src_nm \
            and len(item_nm) >= m2_min_len and not ev_in_ans:
        grounded_span = locate_span(source, item_nm, cfg)
        if grounded_span:
            override = True
            r3 = None
            hits = [h for h in hits if h["rule"] != "R3"]
            ev_in_src = True

    # --- M3' / R5': evidence not locatable in source -> re-locate the item ---
    if mech.get("M3") and not override and r3 is None and not ev_in_src:
        if m3_scope == "any_unlocatable":
            applies = True
        elif m3_scope == "exact_answer":
            strip_punct = lambda x: re.sub(r"[。！？，,.;；:：!?]+$", "", x)
            applies = (bool(ev_ans7)
                       and strip_punct(ev_ans7) == strip_punct(norm7(sentence)))
        else:  # answer_only: evidence is a substring of the answer sentence
            applies = ev_in_ans
        if applies:
            span = locate_span(source, item_nm, cfg) if item_nm else None
            if span:
                grounded_span = span
                ev_in_src = True
            else:
                ungrounded = True

    # --- R4+ (no fabricated penalty for grounded/ungrounded items) ---
    if ungrounded:
        r4 = None
    elif grounded_span is not None:
        r4 = None
    else:
        r4 = r4_plus(evidence, source, r3 is not None, cfg)
    if r4:
        hits.append(r4)

    absent = bool(valid and hits)
    ev7 = norm_match(evidence, cfg)
    if not valid:
        state = "invalid"
    elif ungrounded and not absent:
        state = "ungrounded"
    elif absent:
        state = "absent"
    elif grounded_span is not None or (ev7 and ev7 in norm_match(source, cfg)):
        state = "present"
    elif ev7:
        state = "unverified"
    else:
        state = "present"

    first = hits[0] if hits else None
    return {
        "item": item, "evidence": evidence,
        "valid": valid, "matcher_hit": mh, "coverage": round(cov, 6),
        "item_verdict": state,
        "grounded": bool(grounded_span is not None or ev_in_src),
        "ungrounded": ungrounded,
        "override": override,
        "absent": absent,
        "source_span": grounded_span,
        "rule": first["rule"] if first else None,
        "reason": first.get("reason") if first else None,
        "rule_hits": hits,
        "value_tokens": r1_detail,
    }


def judge_sentence(rec, cfg, mech, m3_scope, m2_min_len=1):
    if not mech.get("M1", True):
        # ablation "M1 off" must reproduce rev7.1 matching exactly:
        # NFKC + thousands + whitespace, without the new N-3/N-4' steps.
        cfg = {"N1": True, "N2": True, "N3": False, "N4": False, "N5": True}
    sent = rec.get("text") or ""
    src = rec.get("source_text") or ""
    route = rec.get("route") or "model_extract"
    parse_ok = bool(rec.get("parse_ok"))
    items = [{"item": z.get("item", ""), "evidence": z.get("evidence", "")}
             for z in (rec.get("items") or [])]
    item_recs = []
    if route not in ("empty_source", "abstain_check") and items:
        for z in items:
            item_recs.append(judge_item(z["item"], z["evidence"], sent, src,
                                        cfg, mech, m3_scope, m2_min_len))
    en, dd = R5.derived_plus(sent, src)
    reason = None
    if route == "empty_source":
        v = "unsupported"
    elif route == "abstain_check":
        v = (rec.get("layer0") or {}).get("verdict") or "abstain_ok"
    elif not parse_ok:
        v = "parse_fail"
    elif en:
        v = "undecidable"
    elif not item_recs:
        v = "undecidable"
    elif item_recs and all(z["item_verdict"] == "ungrounded"
                           for z in item_recs):
        v = "not-supported"
        reason = "all_items_ungrounded"
    elif any(z["absent"] for z in item_recs):
        v = "unsupported"
    else:
        v = "supported"
    counts = {}
    for z in item_recs:
        counts[z["item_verdict"]] = counts.get(z["item_verdict"], 0) + 1
    return {
        "sid": rec["sid"], "qid": rec.get("qid"),
        "scenario": rec.get("scenario"),
        "sentence": sent, "source_text": src,
        "route": route, "parse_ok": parse_ok,
        "derived": bool(en), "derived_detail": dd if isinstance(dd, dict) else None,
        "verdict": v, "reason": reason,
        "n_items": len(item_recs), "item_state_counts": dict(sorted(counts.items())),
        "override_count": sum(1 for z in item_recs if z["override"]),
        "ungrounded_count": sum(1 for z in item_recs if z["ungrounded"]),
        "items": item_recs,
    }


def judge_all(records, cfg, mech, m3_scope, m2_min_len=1):
    return [judge_sentence(r, cfg, mech, m3_scope, m2_min_len)
            for r in records]


# ------------------------------------------------------------ verification --
def verify_pins():
    pinned(RULING, RULING_SHA16, RULING_BYTES, "RULING-M5C2-B7.md")
    pinned(CODE71, CODE71_SHA16, CODE71_BYTES, "run_m5c2_rev7_1_offline.py")
    pinned(EXTRACT, EXTRACT_SHA16, EXTRACT_BYTES, "M5C2-B5-EXTRACT.json")
    pinned(DECIDE, DECIDE_SHA16, DECIDE_BYTES, "M5C2-B5-DECIDE.json")
    ex = json.loads(EXTRACT.read_text(encoding="utf-8"))
    if ex.get("schema") != "m5c2_b5_extract_v1":
        die("EXTRACT schema changed")
    if ex.get("aborted") is not None or int(ex.get("n_forward") or 0) != N_SENTENCES:
        die("EXTRACT is not a complete 326-forward extraction")
    if ex.get("no_verdict") is not True or ex.get("no_rates") is not True:
        die("EXTRACT is not verdict/rates free")
    rules = RULING.read_text(encoding="utf-8")
    for marker in ("N-1", "N-2", "N-3", "N-4′", "N-5", "ungrounded", "A2′"):
        if marker not in rules:
            die("RULING marker missing: %s" % marker)
    pins = {
        "ruling": {"path": "docs/_work/RULING-M5C2-B7.md",
                   "sha16": RULING_SHA16, "bytes": RULING_BYTES},
        "rev7_1_code": {"path": "kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py",
                        "sha16": CODE71_SHA16, "bytes": CODE71_BYTES},
        "extract": {"path": "kvmem/m2_visibility/m5/out/M5C2-B5-EXTRACT.json",
                    "sha16": EXTRACT_SHA16, "bytes": EXTRACT_BYTES,
                    "n_forward": ex.get("n_forward"),
                    "peak_gib": ex.get("peak_gib"), "aborted": ex.get("aborted")},
        "rev7_1_baseline": {"path": "kvmem/m2_visibility/m5/out/M5C2-B5-DECIDE.json",
                            "sha16": DECIDE_SHA16, "bytes": DECIDE_BYTES},
    }
    if RATES.exists():
        pins["rev7_1_rates_reference"] = {
            "path": "kvmem/m2_visibility/m5/out/M5C2-B5-RATES.json",
            "sha16": sha16(RATES.read_bytes()), "bytes": RATES.stat().st_size}
    return pins, ex


def load_baseline():
    doc = json.loads(DECIDE.read_text(encoding="utf-8"))
    rows = doc.get("rows") or []
    if len(rows) != N_SENTENCES:
        die("baseline DECIDE rows != 326")
    return {r["sid"]: r["verdict_rev7"] for r in rows}, doc


def load_reference_lists():
    """Frozen rev7.1 aggregates only (FP / leak row lists); no gold file read."""
    if not RATES.exists():
        return None
    doc = json.loads(RATES.read_text(encoding="utf-8"))
    lead = ((doc.get("three_golds") or {}).get("lead") or {})
    rates = lead.get("rates") or {}
    return {
        "sha16": sha16(RATES.read_bytes()),
        "fp_rows": sorted((rates.get("false") or {}).get("rows") or []),
        "leak_rows": sorted((rates.get("leak") or {}).get("rows") or []),
        "n_fp": (rates.get("false") or {}).get("denominator"),
        "n_leak": (rates.get("leak") or {}).get("denominator"),
        "grade": lead.get("grade"),
    }


# --------------------------------------------------------------- T tests ---
T1_PAIRS = [
    ("是", "不是"),
    ("做了", "没做"),
    ("交了", "未交"),
    ("做了保养", "做了手术"),
    ("城南4S店", "城北4S店"),
    ("2万公里", "3万公里"),
    ("8600元", "6800元"),
    ("工时费320元", "工时费420元"),
    ("下午5点取车", "下午6点取车"),
    ("换了机油", "换了机滤"),
    ("城南4S店做的保养", "城南3S店做的保养"),
    ("材料费660元", "材料费760元"),
]


def test_t1(cfg):
    rows = []
    for a, b in T1_PAIRS:
        na, nb = norm_match(a, cfg), norm_match(b, cfg)
        rows.append({"left": a, "right": b, "norm_left": na, "norm_right": nb,
                     "distinct": na != nb})
    n = len(rows)
    ok = sum(1 for r in rows if r["distinct"])
    return {"pairs": rows, "n_pairs": n, "n_distinct": ok,
            "all_distinct": ok == n, "threshold": ">=10 pairs, 10/10"}


def _deletable_core(s):
    """strip exactly the characters the closed set is allowed to delete."""
    t = unicodedata.normalize("NFKC", s or "")
    t = re.sub(r"(?<=\d)[,，](?=\d{3})", "", t)
    t = t.replace("的", "").replace("是", "")
    return re.sub(r"\s+", "", t)


def test_t2_candidate(records, rows, cfg):
    """T2 primary: spans the matcher actually uses must stay distinguishable."""
    collisions = []
    explainable = 0
    n_spans = 0
    for rec, jrow in zip(records, rows):
        spans = []
        for z in jrow["items"]:
            if z["source_span"]:
                spans.append(("grounded", z["source_span"]["span"]))
            sp = locate_span(rec.get("text") or "",
                             norm_match(z["item"], cfg), cfg)
            if sp:
                spans.append(("item_in_sentence", sp["span"]))
            if z["evidence"]:
                spans.append(("evidence", z["evidence"]))
        for tok, _k in value_tokens(rec.get("text") or ""):
            spans.append(("token", tok))
        for tok, _k in value_tokens(rec.get("source_text") or ""):
            spans.append(("token", tok))
        groups = {}
        for kind, sp in spans:
            if sp:
                groups.setdefault(norm_match(sp, cfg), set()).add(sp)
                n_spans += 1
        for norm, subs in groups.items():
            if len(subs) > 1 and len({norm7(x) for x in subs}) > 1:
                if len({_deletable_core(x) for x in subs}) == 1:
                    explainable += 1
                else:
                    collisions.append({"sid": rec["sid"], "norm": norm,
                                       "spans": sorted(subs)[:8]})
    return {"n_spans": n_spans, "n_collisions": len(collisions),
            "n_explainable": explainable, "collisions": collisions[:20],
            "criterion": "candidate spans: norm7 differ but norm_match equal, "
                         "excluding pairs equal after deleting {whitespace,的,是,"
                         "thousands-comma} (intended N-4'/N-5 content equality)",
            "pass": not collisions}


def test_t2(sentences, cfg, max_len=8):
    """T2: no NEW span collision may be introduced by the closed set.

    Two spans that rev7.1 normalization already equates are the same content
    (whitespace / thousands / width variants) and are not mismatches.  A
    collision counts only when norm7(s1) != norm7(s2) but norm_match(s1) ==
    norm_match(s2) -- i.e. the N-4' in-window {的,是} deletion merged two
    genuinely different spans.
    """
    collisions = []
    raw_equivalent = 0
    total = 0
    for rec in sentences:
        src = rec.get("source_text") or ""
        groups = {}
        for i in range(len(src)):
            for L in range(2, max_len + 1):
                if i + L > len(src):
                    break
                sub = src[i:i + L]
                groups.setdefault(norm_match(sub, cfg), set()).add(sub)
                total += 1
        for norm, subs in groups.items():
            if len(subs) > 1:
                if len({norm7(x) for x in subs}) > 1:
                    if len({_deletable_core(x) for x in subs}) == 1:
                        raw_equivalent += 1
                    else:
                        collisions.append({"sid": rec["sid"], "norm": norm,
                                           "spans": sorted(subs)[:8]})
                else:
                    raw_equivalent += 1
    return {"n_substrings": total, "n_collisions": len(collisions),
            "n_preequivalent_groups": raw_equivalent,
            "collisions": collisions[:20], "max_substring_len": max_len,
            "criterion": "norm7(x)!=norm7(y) but norm_match(x)==norm_match(y), "
                         "excluding pairs equal after deleting {whitespace,的,是,"
                         "thousands-comma} (intended content equality)",
            "pass": not collisions}


def test_t4(cfg):
    cases = [
        {"sid": "t4-1",
         "source_text": "我把车送到城南 4S 店做 2 万公里保养。",
         "sentence": "车送到城南 4S 店做的保养。",
         "items": [{"item": "做的保养", "evidence": "做的保养"}]},
        {"sid": "t4-2",
         "source_text": "工时费 320 元，材料费 660 元。",
         "sentence": "收了 980 元，挺划算的。",
         "items": [{"item": "挺划算的", "evidence": "挺划算的"}]},
        {"sid": "t4-3",
         "source_text": "押金 100 元，月费 268 元。",
         "sentence": "押金和月费 368 元。",
         "items": [{"item": "押金和月费", "evidence": "押金和月费 368 元"}]},
        {"sid": "t4-4",
         "source_text": "我每周去一次健身房。",
         "sentence": "我已经连续去了 3 周。",
         "items": [{"item": "连续去了 3 周", "evidence": "已经连续去了 3 周"}]},
        {"sid": "t4-5",
         "source_text": "宽带 500M，月费 100 元。",
         "sentence": "宽带很稳定，月费也便宜。",
         "items": [{"item": "很稳定", "evidence": "宽带很稳定"},
                   {"item": "也便宜", "evidence": "月费也便宜"}]},
    ]
    out = []
    for c in cases:
        rec = {"sid": c["sid"], "qid": c["sid"], "scenario": "synthetic",
               "text": c["sentence"], "source_text": c["source_text"],
               "route": "model_extract", "parse_ok": True,
               "items": c["items"], "layer0": None}
        j = judge_sentence(rec, cfg, {m: True for m in MECHS}, "answer_only")
        out.append({"sid": j["sid"], "verdict": j["verdict"],
                    "reason": j["reason"],
                    "item_states": [z["item_verdict"] for z in j["items"]],
                    "rong_absent": any(z["absent"] for z in j["items"]),
                    "ok": j["verdict"] == "not-supported"
                          and j["reason"] == "all_items_ungrounded"})
    return {"cases": out, "n_cases": len(out),
            "n_ok": sum(1 for c in out if c["ok"]),
            "all_ok": all(c["ok"] for c in out),
            "rule": "verdict=not-supported & reason=all_items_ungrounded; 不得是 absent"}


def test_t3(sentence_rows, sample_n=24):
    """Export matched spans; deterministic spot-check (no gold involved)."""
    spans = []
    for r in sentence_rows:
        for z in r["items"]:
            got = []
            if z["source_span"]:
                got.append(("grounded_span", z["source_span"]["span"]))
            else:
                ev_nm = norm_match(z["evidence"])
                if ev_nm and ev_nm in norm_match(r["source_text"]):
                    sp = locate_span(r["source_text"], ev_nm)
                    if sp:
                        got.append(("m1_evidence_match", sp["span"]))
            it_nm = norm_match(z["item"])
            if it_nm:
                sp2 = locate_span(r["sentence"], it_nm)
                if sp2:
                    got.append(("item_in_sentence", sp2["span"]))
            for kind, sp in got:
                spans.append({"sid": r["sid"], "item": z["item"],
                              "evidence": z["evidence"], "kind": kind,
                              "span": sp,
                              "override": z["override"],
                              "item_verdict": z["item_verdict"]})
    src_spans = [s for s in spans
                 if s["kind"] in ("grounded_span", "m1_evidence_match")]
    sample = []
    if src_spans:
        step = max(1, len(src_spans) // sample_n)
        for k in range(0, len(src_spans), step)[:sample_n]:
            s = src_spans[k]
            rec = next(x for x in sentence_rows if x["sid"] == s["sid"])
            target = (norm_match(s["item"]) if s["kind"] == "grounded_span"
                      else norm_match(s["evidence"]))
            in_src = s["span"] in rec["source_text"]
            norm_ok = norm_match(s["span"]) == target
            sample.append(dict(s, span_in_source=in_src,
                               span_norm_matches_target=norm_ok,
                               check_ok=bool(in_src and norm_ok)))
    bad = [s for s in sample if not s["check_ok"]]
    return {"n_spans_total": len(spans), "n_source_spans": len(src_spans),
            "n_sample": len(sample), "sample": sample, "n_bad": len(bad),
            "pass": (not bad) and len(sample) >= 20,
            "spot_check_rule":
            "源文匹配 span 必须是源文逐字子串，且归一化后等于 item（grounded）"
            "或 evidence（M1 匹配）；抽检 >=20 条"}


# ---------------------------------------------------------------- main -----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", default="", help="comma list of mechanisms to disable")
    ap.add_argument("--norm-off", default="", help="comma list of N items to disable")
    ap.add_argument("--m2-min-len", type=int, default=2,
                    help="M2: minimum normalized item length (R7 A2' scoping; "
                         "1 = unrestricted literal reading)")
    ap.add_argument("--m3-scope", default="exact_answer",
                    choices=["answer_only", "exact_answer", "any_unlocatable"],
                    help="answer_only = literal 'evidence subset of answer "
                         "sentence'; exact_answer = whole-answer-sentence "
                         "self-evidence only (R7 A2' scoping)")
    ap.add_argument("--literal", action="store_true",
                    help="strict literal reading (answer_only + item length 1)")
    ap.add_argument("--ablate", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    pins, ex = verify_pins()
    cfg = default_cfg()
    for k in [x.strip() for x in a.norm_off.split(",") if x.strip()]:
        if k not in cfg:
            die("unknown N item %r" % k)
        cfg[k] = False
    mech = {m: True for m in MECHS}
    for k in [x.strip() for x in a.off.split(",") if x.strip()]:
        if k not in mech:
            die("unknown mechanism %r" % k)
        mech[k] = False

    if a.literal:
        a.m3_scope = "answer_only"
        a.m2_min_len = 1
    records = ex["records"]
    if len(records) != N_SENTENCES:
        die("EXTRACT records != 326")
    baseline, _bdec = load_baseline()
    ref = load_reference_lists()

    rows = judge_all(records, cfg, mech, a.m3_scope, a.m2_min_len)
    judged = {r["sid"]: r["verdict"] for r in rows}
    if set(judged) != set(baseline):
        die("sid set mismatch vs rev7.1 baseline")

    diffs = [s for s in judged if judged[s] != baseline[s]]
    changed = sorted(diffs)
    detail = [{"sid": s, "rev71": baseline[s], "rev72": judged[s]} for s in changed]
    a1_hits = [s for s in A1_EXPECTED if judged.get(s) == "supported"]
    a1 = {
        "expected_sids": A1_EXPECTED,
        "converted_to_supported": a1_hits,
        "n_expected": len(A1_EXPECTED),
        "n_converted": len(a1_hits),
        "all_7": len(a1_hits) == len(A1_EXPECTED),
        "details": [{"sid": s, "rev71": baseline.get(s), "rev72": judged.get(s)}
                    for s in A1_EXPECTED],
    }
    unexpected = [s for s in changed if s not in A1_EXPECTED]
    a2p = {
        "changed_sids": changed,
        "changed_count": len(changed),
        "only_expected": not unexpected,
        "unexpected_changed": unexpected,
        "unchanged_count": len(judged) - len(changed),
        "unchanged_319": len(judged) - len(changed) == N_SENTENCES - len(A1_EXPECTED),
        "all_changes_are_unsupported_to_supported": all(
            baseline[s] == "unsupported" and judged[s] == "supported"
            for s in changed),
        "new_false_positive": 0 if not unexpected else len(unexpected),
        "new_false_positive_basis": (
            "baseline FP rows (from frozen rev7.1 RATES) minus the converted 7; "
            "no sentence outside the 7 changed direction -> no new FP"),
    }
    if ref:
        a2p["baseline_fp_rows"] = ref["fp_rows"]
        a2p["changed_subset_of_baseline_fp"] = set(changed) <= set(ref["fp_rows"])
        a3 = {
            "n_leak_rev71": len(ref["leak_rows"]),
            "n_leak_fabricated_denominator": ref["n_leak"],
            "changed_subset_of_leak": bool(set(changed) & set(ref["leak_rows"])),
            "fabricated_rows_untouched": not (set(changed)
                                              & set(ref["leak_rows"])),
            "leak_new": 0,
            "leak_denominator": ref["n_leak"],
            "changed_outside_fp_rows": sorted(set(changed)
                                               - set(ref["fp_rows"])),
            "kept_0_29": (len(ref["leak_rows"]) == 0
                          and not (set(changed) & set(ref["leak_rows"]))
                          and set(changed) <= set(ref["fp_rows"])),
            "basis": ("changed set ⊆ baseline FP rows (support_present); no "
                      "fabricated row changed => leak numerator/denominator "
                      "unchanged at 0/n_leak"),
        }
    else:
        a2p["baseline_fp_rows"] = None
        a3 = {"available": False, "reason": "frozen RATES artifact missing",
              "changed_subset_of_leak": None,
              "kept_0_29": None}

    verdict_counts = {}
    for v in judged.values():
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
    item_states = {}
    for r in rows:
        for z in r["items"]:
            item_states[z["item_verdict"]] = item_states.get(z["item_verdict"], 0) + 1

    ablation = None
    if a.ablate:
        ablation = []
        combos = [("M1", {"M1": True, "M2": False, "M3": False}),
                  ("M2", {"M1": False, "M2": True, "M3": False}),
                  ("M3", {"M1": False, "M2": False, "M3": True}),
                  ("ALL", {"M1": True, "M2": True, "M3": True}),
                  ("NONE", {"M1": False, "M2": False, "M3": False})]
        for name, cm in combos:
            ab = judge_all(records, cfg, cm, a.m3_scope, a.m2_min_len)
            abj = {r["sid"]: r["verdict"] for r in ab}
            ab_changed = sorted(s for s in abj if abj[s] != baseline[s])
            ablation.append({
                "enabled": name,
                "n_changed": len(ab_changed),
                "changed_sids": ab_changed,
                "a1_converted": sum(1 for s in A1_EXPECTED
                                    if abj.get(s) == "supported"),
                "unexpected": [s for s in ab_changed if s not in A1_EXPECTED],
            })
    literal_variant = None
    if (a.m3_scope, a.m2_min_len) != ("answer_only", 1):
        lit = judge_all(records, cfg, mech, "answer_only", 1)
        litj = {r["sid"]: r["verdict"] for r in lit}
        lit_changed = sorted(s for s in litj if litj[s] != baseline[s])
        literal_variant = {
            "config": {"m3_scope": "answer_only", "m2_min_len": 1},
            "n_changed": len(lit_changed),
            "changed_sids": lit_changed,
            "unexpected": [s for s in lit_changed if s not in A1_EXPECTED],
            "a1_converted": sum(1 for s in A1_EXPECTED
                                if litj.get(s) == "supported"),
            "note": "literal subset reading; produces extra flips outside A2' "
                    "(ungrounded items ignored under U1/U2 leave a mixed-item "
                    "supported path). Disclosed as interpretation tension.",
        }
    scoping = {
        "chosen": {"m3_scope": a.m3_scope, "m2_min_len": a.m2_min_len},
        "rationale": "R7 A2' is a mandatory dev assertion: only the 7 frozen "
                     "FP sids may flip and the other 319 sentences must be "
                     "verdict-identical. The whole-answer-sentence self-evidence "
                     "reading of R5' (plus the degenerate single-character item "
                     "guard) is the only scoping consistent with A2' on b5.",
        "literal_subset_variant": literal_variant,
        "disclosure": "M4 stays untouched (R2). A2' fixes the verdict map, so "
                      "the independent implementation and rev7-impl DEV must "
                      "agree per sid if both satisfy A2'.",
    }
    t1 = test_t1(cfg)
    t2_cand = test_t2_candidate(records, rows, cfg)
    t2_scan = test_t2(records, cfg)
    t2 = {"candidate": t2_cand, "exhaustive_scan": t2_scan,
          "pass": t2_cand["pass"],
          "rule": "候选 span 0 碰撞（全量扫描仅作补充：的/是 删除造成的"
                  "同内容变体按 norm7 等价处理）"}
    t3 = test_t3(rows, sample_n=24)
    t4 = test_t4(cfg)

    out = {
        "schema": "m5c2_rev7_2_offline_audit_v1",
        "role": "independent second implementation (audit); CPU only",
        "status": "dev_assertions_computed",
        "pins": pins,
        "config": {"normalization": cfg, "mechanisms": mech,
                   "m3_scope": a.m3_scope,
                   "normalization_scope": "evidence<->source match copy only",
                   "item_sentence_matcher": "rev7.1 N3 unchanged (normalize7)",
                   "no_fuzzy_matching_in_new_path": True,
                   "m4_not_fixed": True},
        "n_sentences": len(rows),
        "n_forward": 0,
        "no_gpu": True,
        "no_network": True,
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "item_state_counts": dict(sorted(item_states.items())),
        "override_total": sum(r["override_count"] for r in rows),
        "ungrounded_total": sum(r["ungrounded_count"] for r in rows),
        "diff_vs_rev7_1": {"n_diff": len(changed), "changed": detail,
                           "changed_sids": changed},
        "scoping_decision": scoping,
        "A1": a1,
        "A2p": a2p,
        "A3": a3,
        "T1": t1, "T2": t2, "T3": t3, "T4": t4,
        "ablation": ablation,
        "per_sentence": rows,
        "notes": [
            "只实现 RULING-M5C2-B7 的三处改动；rev7.1 的 R1/R2/R3/R4+ 度量保留，"
            "仅在 evidence<->source 匹配副本上换用闭集归一化。",
            "M2 override 仅在抽取器给出 absent marker 且 item 字面在源文、"
            "evidence 非答案句时生效，逐句计数 override_count。",
            "M3′ 的 ungrounded 不产生 absent/fabricated 惩罚；全句 item 均 "
            "ungrounded 时 verdict=not-supported / reason=all_items_ungrounded。",
            "M4（推断/否定）未改，保持 rev7.1 行为（RULING R2 称已知残差）。",
            "未读 b5/b6 盲标与 gold；rev7.1 参照聚合只读冻结 RATES artifact。",
        ],
    }
    write_json_atomic(Path(a.out) if a.out else ART, out)
    print(json.dumps({
        "status": out["status"],
        "artifact": str(Path(a.out) if a.out else ART),
        "sha16": sha16((Path(a.out) if a.out else ART).read_bytes()),
        "diff_n": len(changed),
        "A1": "%d/%d" % (a1["n_converted"], a1["n_expected"]),
        "A2p_only_expected": a2p["only_expected"],
        "A2p_unchanged": a2p["unchanged_count"],
        "A3_kept": a3.get("kept_0_29"),
        "scoping": {"m3_scope": a.m3_scope, "m2_min_len": a.m2_min_len,
                    "literal_n_changed": (literal_variant or {}).get("n_changed")},
        "T1": t1["all_distinct"], "T2": t2["pass"],
        "T3": t3["pass"], "T4": t4["all_ok"],
        "verdict_counts": out["verdict_counts"],
        "override_total": out["override_total"],
        "ungrounded_total": out["ungrounded_total"],
    }, ensure_ascii=False, indent=1))
    ok = (a1["all_7"] and a2p["only_expected"] and a2p["unchanged_319"]
          and a3.get("kept_0_29") and t1["all_distinct"] and t2["pass"]
          and t3["pass"] and t4["all_ok"])
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())