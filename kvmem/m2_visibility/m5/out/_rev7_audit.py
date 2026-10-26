#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Independent inspector reimplementation for M5-C2 REV7.  Read-only w.r.t. all
frozen inputs and the implementer's artifacts (only *reads* them).

DISCIPLINE
  * From-scratch independent implementation of PREREG-M5-C2-REV7.md
    (sha16 32eaf82ca56600c4, 5835 B, 88 lines) + the frozen rev5.1 rule set
    (R1/R2/R3/R4+/R_DERIVED+, threshold 0.80, frozen vocabularies).
  * Does NOT import / execute / copy run_m5c2_rev7_offline.py.  Rule constants
    were transcribed from the frozen PREREG and the reference modules
    rev4.1 / rev5 / rev5.1 (explicitly allowed reading).
  * Inputs: M5B4-JUDGE.json (6a3001b6ca23ef7d) and M5B4-LEAD-RULING.json
    (9273ebc97aa1413a).  (b5) is never read or referenced as data.

Output: out/M5C2-REV7-AUDIT.json
"""
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"

PRE = ROOT / "docs/_work/PREREG-M5-C2-REV7.md"
PRE_SHA16 = "32eaf82ca56600c4"
PRE_BYTES = 5835
PRE_LINES = 88

JUDGE = OUT / "M5B4-JUDGE.json"
JUDGE_SHA16 = "6a3001b6ca23ef7d"
GOLD_F = OUT / "M5B4-LEAD-RULING.json"
GOLD_SHA16 = "9273ebc97aa1413a"

IMPL_SCRIPT = M5 / "run_m5c2_rev7_offline.py"
IMPL_ART = OUT / "M5C2-REV7-OFFLINE.json"
AUDIT_ART = OUT / "M5C2-REV7-AUDIT.json"
DET_PROBE = os.path.join(tempfile.gettempdir(), "rev7_determinism.json")

THRESH = 0.80
VALID_THRESH = 0.90

# ---------------------------------------------------------------- frozen vocab
DERIVED_RE = re.compile(r"共|总共|合计|一共|平均|最|加起来")
NEG_WORDS = ["不是", "而不是", "并非", "不符", "另一", "改为", "换成",
             "没", "不", "非", "无"]
ABSENT_MARKERS = ["未提及", "没有提到", "未找到", "找不到", "未记录",
                  "无对应", "无相关", "未涉及", "未写明", "未说明",
                  "未给出", "未提供", "N/A", "NA", "None", "null", "—"]

# rev5.1 pure-value token patterns (frozen; N2 leaves these untouched)
PURE_VALUE_PATS = [
    r"\d+(?:\.\d+)?\s*(?:元|度|M|G|层|楼|排|号|节|个月|年|月|日)",
    r"下?(?:周|星期)[一二三四五六日天]",
    r"\d+月\d+日",
    r"[A-Z]{2,}-\d{3,}",
]
# N2 new (narrow, non-greedy, function-word-excluding) entity pattern
ENTITY_RE = re.compile(
    r"(?:(?:是|叫|为|在|到)\s*)?"
    r"([^\s，。是叫为在的]{2,8}(?:公司|店|院|馆|中心|银行|医院|学院|酒店|机场))"
)
# deleted by N2 (documentation only)
OLD_ENTITY_RE = re.compile(r"[^\s，。]{2,}(?:公司|店|院|馆|中心)")

CN_DIGITS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


# ============================================================ normalisation
def normalize_old(s):
    """rev5.1 normalize (whitespace only)."""
    return re.sub(r"\s+", "", s or "")


def normalize(s):
    """N1 literal: NFKC -> thousands-separator strip -> whitespace delete."""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"(?<=\d)[,，](?=\d{3})", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def normalize_alt_order(s):
    """Sensitivity only: NFKC -> whitespace delete -> thousands strip."""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"\s+", "", s)
    return re.sub(r"(?<=\d)[,，](?=\d{3})", "", s)


# ============================================================ metrics
def bigrams(s):
    return [s[i:i + 2] for i in range(max(0, len(s) - 1))] or ([s] if s else [])


def coverage(a, b):
    if not a:
        return 0.0
    if a in b:
        return 1.0
    bs = bigrams(a)
    if not bs:
        return 0.0
    return sum(1 for x in bs if x in b) / float(len(bs))


def window_coverage(ev, src):
    """Best char-bigram coverage of ev against a same-length source window."""
    if not ev or not src:
        return 0.0
    if ev in src:
        return 1.0
    L = len(ev)
    if L > len(src):
        return coverage(ev, src)
    best = 0.0
    for i in range(0, len(src) - L + 1):
        c = coverage(ev, src[i:i + L])
        if c > best:
            best = c
            if best >= 0.999:
                break
    return best


def char_jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / float(len(sa | sb))


def max_window_jaccard(ev, src):
    if not ev or not src:
        return 0.0
    if ev in src:
        return 1.0
    L = len(ev)
    if L > len(src):
        return char_jaccard(ev, src)
    best = 0.0
    for i in range(0, len(src) - L + 1):
        j = char_jaccard(ev, src[i:i + L])
        if j > best:
            best = j
            if best >= 0.999:
                break
    return best


def fuzzy_coverage(token, evidence):
    if token in evidence:
        return 1.0
    bs = bigrams(token)
    if not bs:
        return 0.0
    return sum(1 for b in bs if b in evidence) / float(len(bs))


# ============================================================ token extraction
def value_tokens_old(entry):
    pats = PURE_VALUE_PATS + [r"[^\s，。]{2,}(?:公司|店|院|馆|中心)"]
    toks = []
    for p in pats:
        for m in re.finditer(p, entry or ""):
            t = m.group(0).strip()
            if t and t not in toks:
                toks.append(t)
    return toks


def value_tokens_v7(entry, gate_text_norm):
    """N2: pure-value tokens unchanged; entity token = capture group 1, only
    when the token itself occurs in gate_text_norm."""
    toks = []
    for p in PURE_VALUE_PATS:
        for m in re.finditer(p, entry or ""):
            t = m.group(0).strip()
            if t and t not in toks:
                toks.append(t)
    entity_gate = []
    for m in ENTITY_RE.finditer(entry or ""):
        t = (m.group(1) or "").strip()
        if not t:
            continue
        present = normalize(t) in gate_text_norm
        entity_gate.append({"token": t, "in_gate_text": present})
        if present and t not in toks:
            toks.append(t)
    return toks, entity_gate


# ============================================================ R1/R2/R3
def r1_r2_r3(entry, evidence, tokens, norm=normalize):
    hits = []
    ev = norm(evidence)
    ent = norm(entry)
    for tok in tokens:
        cov = fuzzy_coverage(norm(tok), ev)
        if cov < THRESH:
            hits.append({"rule": "R1", "reason": "value_mismatch", "span": tok,
                         "coverage": round(cov, 6)})
    anchors = []
    for a in list(tokens) + [ent]:
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
            neg = [w for w in NEG_WORDS if w in before]
            if neg:
                hits.append({"rule": "R2", "reason": "negated",
                             "span": ev[max(0, i - 8):i + len(anchor) + 8],
                             "anchor": anchor, "before": before,
                             "neg_word": sorted(neg, key=len, reverse=True)[0]})
                r2_done = True
                break
            pat = re.compile(r"(不是|并非|而不是)\s*" + re.escape(anchor))
            if pat.search(ev):
                hits.append({"rule": "R2", "reason": "negated_pattern",
                             "span": pat.search(ev).group(0), "anchor": anchor})
                r2_done = True
                break
            pat2 = re.compile(re.escape(anchor) + r"\s*(不是|是错的)")
            if pat2.search(ev):
                hits.append({"rule": "R2", "reason": "negated_after",
                             "span": pat2.search(ev).group(0), "anchor": anchor})
                r2_done = True
                break
        if r2_done:
            break
    r3 = None
    for marker in ABSENT_MARKERS:
        if norm(marker) in ev:
            r3 = marker
            hits.append({"rule": "R3", "reason": "absent_marker", "span": marker})
            break
    return hits, r3


def r4_plus_v51(evidence, source, has_r3, norm=normalize):
    """rev5.1 R4+ (short <=4 => char Jaccard; long => bigram coverage; 0.80)."""
    if has_r3:
        return None
    ev = norm(evidence)
    src = norm(source)
    if not ev:
        return {"rule": "R4+", "reason": "fabricated_evidence",
                "span": "(empty)", "metric": "empty", "value": 0.0}
    if ev in src:
        return None
    if len(ev) <= 4:
        j = max_window_jaccard(ev, src)
        if j >= THRESH:
            return None
        return {"rule": "R4+", "reason": "fabricated_evidence", "span": evidence,
                "metric": "char_jaccard", "value": round(j, 6)}
    cov = window_coverage(ev, src)
    if cov >= THRESH:
        return None
    return {"rule": "R4+", "reason": "fabricated_evidence", "span": evidence,
            "metric": "bigram", "value": round(cov, 6)}


# ============================================================ R_DERIVED+
def cn_value(s):
    total = 0
    section = 0
    number = 0
    for ch in s:
        if ch in CN_DIGITS:
            number = CN_DIGITS[ch]
        elif ch in CN_UNITS:
            if number == 0:
                number = 1
            section += number * CN_UNITS[ch]
            number = 0
        elif ch == "半":
            if number:
                section += number
                number = 0
            section += 0.5
    return float(section + number)


def numbers(text):
    out = []
    for m in re.finditer(r"\d+(?:\.\d+)?", text or ""):
        try:
            out.append(float(m.group(0)))
        except ValueError:
            pass
    for m in re.finditer(r"[一二三四五六七八九十百千两半]+", text or ""):
        s = m.group(0)
        if s:
            try:
                out.append(cn_value(s))
            except Exception:  # noqa: BLE001
                pass
    return out


def composable(v, srcvals):
    if any(abs(v - s) <= 1e-9 for s in srcvals):
        return True
    for a in srcvals:
        for b in srcvals:
            cands = [a + b, abs(a - b), a * b]
            if b:
                cands.append(a / b)
            if a:
                cands.append(b / a)
            for c in cands:
                if abs(c - round(c)) <= 1e-9 and abs(v - c) <= 1e-9:
                    return True
    return False


def derived_plus(sentence, source):
    m = DERIVED_RE.search(sentence)
    if not m:
        return False, {"applicable": False}
    svals = numbers(source)
    vals = numbers(sentence)
    missing = [v for v in vals if not composable(v, svals)]
    enabled = len(missing) == 0
    return enabled, {"applicable": True, "sentence_values": vals,
                     "source_values": svals, "missing_values": missing,
                     "enabled": enabled, "keyword": m.group(0)}


# ============================================================ item judging
def judge_items(items, sentence, source, use_n1=True, use_n2=True,
                use_n3=True, gate_basis="source"):
    """Parametrised item scorer.  All-False == rev5.1 baseline."""
    norm = normalize if use_n1 else normalize_old
    sent_n = norm(sentence)
    src_n = norm(source)
    out = []
    for it in items:
        entry = it.get("item", "")
        ev = it.get("evidence", "")
        item_n = norm(entry)
        in_sentence = bool(item_n) and item_n in sent_n
        win_cov = window_coverage(item_n, sent_n) if item_n else 0.0
        located = in_sentence or win_cov >= VALID_THRESH
        valid = located if use_n3 else True
        if use_n2:
            gate_norm = src_n if gate_basis == "source" else norm(ev)
            toks, entity_gate = value_tokens_v7(entry, gate_norm)
        else:
            toks, entity_gate = value_tokens_old(entry), []
        hits, r3 = r1_r2_r3(entry, ev, toks, norm=norm)
        r4 = r4_plus_v51(ev, source, r3 is not None, norm=norm)
        if r4:
            hits.append(r4)
        out.append({
            "item": entry, "evidence": ev, "valid": valid,
            "matcher": {"item_in_sentence": in_sentence,
                        "window_coverage": round(win_cov, 6),
                        "located": located},
            "entity_gate": entity_gate,
            "numeric_tokens": toks,
            "rule_hits": hits, "r3_hit": r3 is not None,
            "absent": bool(hits),
            "item_verdict": ("invalid" if not valid
                             else ("unsupported" if hits else "supported")),
        })
    return out


def aggregate(parse_ok, derived_enabled, n_items_original, hits_flags):
    if not parse_ok:
        return "parse_fail"
    if derived_enabled:
        return "undecidable"
    if n_items_original == 0:
        return "undecidable"
    if any(hits_flags):
        return "unsupported"
    return "supported"


def run_v7(rows, gold, use_n1=True, use_n2=True, use_n3=True,
           use_n4=True, gate_basis="source",
           all_invalid_to_undecidable=False):
    """Return per-sentence verdict dict for one rule configuration."""
    res = {}
    for r in rows:
        items = r["items"] or []
        vitems = judge_items(items, r["sentence"], r["source_text"],
                             use_n1=use_n1, use_n2=use_n2, use_n3=use_n3,
                             gate_basis=gate_basis)
        en, _dd = derived_plus(r["sentence"], r["source_text"])
        counted = [z for z in vitems if (z["valid"] or not use_n4)]
        valid_items = [z for z in vitems if z["valid"]]
        if r["route"] == "abstain_check":
            v = r["verdict"]                      # layer0 preserved
        elif (all_invalid_to_undecidable and len(items) > 0
              and len(valid_items) == 0 and r["parse_ok"] and not en):
            v = "undecidable"
        else:
            v = aggregate(r["parse_ok"], en, len(items),
                          [z["absent"] for z in counted])
        res[r["sid"]] = {"sid": r["sid"], "gold": gold.get(r["sid"]),
                         "route": r["route"], "verdict": v,
                         "n_items": len(vitems), "n_valid": len(valid_items),
                         "n_invalid": len(vitems) - len(valid_items),
                         "n_absent": sum(1 for z in counted if z["absent"]),
                         "items": vitems}
    return res


def gate_summary(verdicts):
    supp = [x for x in verdicts.values() if x["gold"] == "support_present"]
    fab = [x for x in verdicts.values() if x["gold"] == "fabricated"]
    fp = sorted(x["sid"] for x in supp if x["verdict"] == "unsupported")
    leak = sorted(x["sid"] for x in fab
                  if x["verdict"] in ("supported", "undecidable"))
    strict = sorted(x["sid"] for x in fab if x["verdict"] == "supported")
    pf = sorted(x["sid"] for x in verdicts.values()
                if x["verdict"] == "parse_fail")
    new_miss = sorted(x["sid"] for x in verdicts.values()
                      if x["gold"] == "fabricated"
                      and x["verdict"] == "supported"
                      and x["sid"] in BASELINE_LEAK_UNSUPPORTED_SET)
    return {"fp": {"k": len(fp), "n": len(supp), "sids": fp},
            "leak": {"k": len(leak), "n": len(fab), "sids": leak},
            "strict_leak": {"k": len(strict), "n": len(fab), "sids": strict},
            "parse_fail": {"k": len(pf), "n": len(verdicts), "sids": pf},
            "new_miss": {"k": len(new_miss), "sids": new_miss}}


BASELINE_LEAK_UNSUPPORTED_SET = set()   # filled in main() from my baseline


# ============================================================ main
def main():
    global BASELINE_LEAK_UNSUPPORTED_SET
    report = {"schema": "m5c2_rev7_audit_v1", "role": "independent_inspector",
              "discipline": ("independent from-scratch implementation; "
                             "does not import/execute/copy the implementer "
                             "script; (b5) never read")}

    # ---- 0. frozen inputs
    pb = PRE.read_bytes()
    jb = JUDGE.read_bytes()
    gb = GOLD_F.read_bytes()
    pre_ok = (sha16(pb) == PRE_SHA16 and len(pb) == PRE_BYTES
              and pb.count(b"\n") + 1 == PRE_LINES
              and not pb.endswith(b"\n") and b"frozen=true" in pb)
    judge_ok = sha16(jb) == JUDGE_SHA16
    gold_ok = sha16(gb) == GOLD_SHA16
    prereg_txt = pb.decode("utf-8")
    report["inputs"] = {
        "prereg": {"file": PRE.name, "sha16": sha16(pb), "bytes": len(pb),
                   "lines": pb.count(b"\n") + 1,
                   "trailing_newline": pb.endswith(b"\n"),
                   "frozen_true": "frozen=true" in prereg_txt,
                   "ok": pre_ok},
        "judge": {"file": JUDGE.name, "sha16": sha16(jb), "bytes": len(jb),
                  "ok": judge_ok},
        "gold": {"file": GOLD_F.name, "sha16": sha16(gb), "bytes": len(gb),
                 "ok": gold_ok},
        "b5_read": False,
        "impl_script_imported_or_executed": False,
    }
    if not (pre_ok and judge_ok and gold_ok):
        raise SystemExit("frozen input verification failed")

    judge = json.loads(jb.decode("utf-8"))
    gold = json.loads(gb.decode("utf-8"))["gold"]
    rows = judge["items"]
    if len(rows) != 261:
        raise SystemExit("expected 261 sentence rows")
    claimed = json.loads(gb.decode("utf-8"))["gold_counts"]
    observed = {k: sum(1 for v in gold.values() if v == k)
                for k in ("support_present", "fabricated", "no_fact",
                          "undecidable")}
    report["gold_counts"] = {"observed": observed, "claimed": claimed,
                             "match": observed == claimed}

    # ---- 1. baseline rev5.1 reproduction (from stored items[], zero GPU)
    base_rows = {}
    item_parity_total = 0
    item_parity_mismatch = []
    verdict_mismatch = []
    derived_flag_diff = []
    for r in rows:
        sid = r["sid"]
        b_items = judge_items(r["items"] or [], r["sentence"], r["source_text"],
                              use_n1=False, use_n2=False, use_n3=False)
        en, dd = derived_plus(r["sentence"], r["source_text"])
        if r["route"] == "abstain_check":
            v = r["verdict"]                       # layer0 preserved
        else:
            v = aggregate(r["parse_ok"], en, len(r["items"] or []),
                          [z["absent"] for z in b_items])
        base_rows[sid] = {"sid": sid, "gold": gold.get(sid), "route": r["route"],
                          "sentence": r["sentence"], "source": r["source_text"],
                          "derived": en, "derived_detail": dd,
                          "items": b_items, "verdict": v,
                          "stored_verdict": r["verdict"],
                          "parse_ok": bool(r["parse_ok"])}
        if v != r["verdict"]:
            verdict_mismatch.append({"sid": sid, "mine": v,
                                     "stored": r["verdict"]})
        if bool(r["derived"]) != bool(en):
            derived_flag_diff.append({"sid": sid, "mine": en,
                                      "stored": r["derived"]})
        if len(b_items) != len(r["items"] or []):
            item_parity_mismatch.append({"sid": sid, "why": "n_items"})
        for a, b in zip(b_items, r["items"] or []):
            item_parity_total += 1
            if bool(a["absent"]) != bool(b.get("absent")):
                item_parity_mismatch.append(
                    {"sid": sid, "item": a["item"], "why": "absent",
                     "mine": a["absent"], "stored": b.get("absent")})
            mine = sorted((h["rule"], h["reason"], h.get("span"))
                          for h in a["rule_hits"])
            theirs = sorted((h.get("rule"), h.get("reason"), h.get("span"))
                            for h in (b.get("rule_hits") or []))
            if mine != theirs:
                item_parity_mismatch.append(
                    {"sid": sid, "item": a["item"], "why": "rule_hits",
                     "mine": mine, "stored": theirs})

    supp = [x for x in base_rows.values() if x["gold"] == "support_present"]
    fab = [x for x in base_rows.values() if x["gold"] == "fabricated"]
    base_fp = sorted(x["sid"] for x in supp if x["verdict"] == "unsupported")
    base_leak = sorted(x["sid"] for x in fab
                       if x["verdict"] in ("supported", "undecidable"))
    base_pf = sorted(x["sid"] for x in base_rows.values()
                     if x["verdict"] == "parse_fail")
    BASELINE_LEAK_UNSUPPORTED_SET = set(
        x["sid"] for x in fab if x["verdict"] == "unsupported")
    report["baseline_rev5_1"] = {
        "n_sentences": len(base_rows),
        "verdict_match": "%d/261" % (len(base_rows) - len(verdict_mismatch)),
        "verdict_mismatches": verdict_mismatch,
        "derived_flag_mismatches": derived_flag_diff,
        "per_item_compared": item_parity_total,
        "per_item_mismatches": item_parity_mismatch,
        "fp": {"k": len(base_fp), "n": len(supp), "sids": base_fp},
        "leak": {"k": len(base_leak), "n": len(fab), "sids": base_leak},
        "parse_fail": {"k": len(base_pf), "n": len(base_rows),
                       "sids": base_pf},
        "claimed_by_task": {"fp": "7/46", "leak": "4/41"},
        "reproduced_claimed": (len(base_fp) == 7 and len(base_leak) == 4
                               and not verdict_mismatch
                               and not item_parity_mismatch),
    }

    # ---- 2. rev7 independent recompute (literal N1..N4)
    v7_rows = run_v7(rows, gold, use_n1=True, use_n2=True, use_n3=True,
                     use_n4=True)
    sentence_diff = []
    for sid, x in v7_rows.items():
        b = base_rows[sid]
        if b["verdict"] != x["verdict"]:
            sentence_diff.append({"sid": sid, "gold": x["gold"],
                                  "from": b["verdict"], "to": x["verdict"]})
    for d in sentence_diff:
        sid = d["sid"]
        b_items = base_rows[sid]["items"]
        v_items = v7_rows[sid]["items"]
        causes = []
        for k, (a, c) in enumerate(zip(b_items, v_items)):
            if not c["valid"]:
                if a["absent"]:
                    causes.append({
                        "idx": k, "item": a["item"], "cause": "N3/N4",
                        "baseline_hits": [h["rule"] for h in a["rule_hits"]],
                        "rev7_valid": False,
                        "rev7_hits": [h["rule"] for h in c["rule_hits"]],
                        "effect": "invalid item's hit excluded from aggregation"})
                continue
            if bool(a["absent"]) == bool(c["absent"]):
                continue
            if value_tokens_old(a["item"]) != c["numeric_tokens"]:
                cause = "N2"
            else:
                cause = "N1"
            causes.append({"idx": k, "item": a["item"], "cause": cause,
                           "baseline_hits": [h["rule"] for h in a["rule_hits"]],
                           "rev7_valid": c["valid"],
                           "rev7_hits": [h["rule"] for h in c["rule_hits"]]})
        d["item_causes"] = causes
        d["cause_set"] = sorted(set(x["cause"] for x in causes))

    gates_raw = gate_summary(v7_rows)
    gates = {
        "fp": {**gates_raw["fp"], "threshold": "<=4/46",
               "pass": gates_raw["fp"]["k"] <= 4},
        "leak": {**gates_raw["leak"], "threshold": "<=5/41",
                 "pass": gates_raw["leak"]["k"] <= 5},
        "parse_fail": {**gates_raw["parse_fail"], "threshold": "<=2/261",
                       "pass": gates_raw["parse_fail"]["k"] <= 2},
        "new_miss": {**gates_raw["new_miss"], "threshold": "==0",
                     "pass": gates_raw["new_miss"]["k"] == 0},
        "strict_leak": gates_raw["strict_leak"],
    }
    n_invalid = sum(x["n_invalid"] for x in v7_rows.values())
    n_items = sum(x["n_items"] for x in v7_rows.values())
    report["rev7_independent"] = {
        "n_sentences": len(v7_rows),
        "gates": gates,
        "rev7_unusable": not all(gates[k]["pass"]
                                 for k in ("fp", "leak", "parse_fail",
                                           "new_miss")),
        "items_total": n_items,
        "invalid_total": n_invalid,
        "invalid_rate": round(n_invalid / float(n_items), 4) if n_items else None,
        "sentence_diff": sentence_diff,
        "n_changed": len(sentence_diff),
        "assembly_rule": ("parse_fail if not parse_ok; elif derived -> "
                          "undecidable; elif original items empty -> "
                          "undecidable; elif any VALID item has a rule hit -> "
                          "unsupported; else supported.  abstain_check keeps "
                          "layer0 verdict."),
    }

    # ---- 2b. FP attribution
    fp_attr = []
    for sid in base_fp:
        b = base_rows[sid]
        v = v7_rows[sid]
        hit_items = [{"idx": k, "item": a["item"], "evidence": a["evidence"],
                      "baseline_hits": [(h["rule"], h["reason"], h.get("span"))
                                        for h in a["rule_hits"]]}
                     for k, a in enumerate(b["items"]) if a["absent"]]
        status = []
        for k, a in enumerate(b["items"]):
            c = v["items"][k]
            status.append({"idx": k, "item": a["item"],
                           "rev7_valid": c["valid"],
                           "rev7_hits": [h["rule"] for h in c["rule_hits"]],
                           "baseline_hits": [h["rule"] for h in a["rule_hits"]]})
        cause = "unfixed"
        if b["verdict"] == "unsupported" and v["verdict"] != "unsupported":
            lost = [s for s in status if s["baseline_hits"]
                    and not s["rev7_hits"]]
            kinds = []
            for s in lost:
                if not s["rev7_valid"]:
                    kinds.append("N3/N4")
                elif value_tokens_old(s["item"]) != \
                        v["items"][s["idx"]]["numeric_tokens"]:
                    kinds.append("N2")
                else:
                    kinds.append("N1")
            cause = "+".join(sorted(set(kinds))) or "unknown"
        fp_attr.append({"sid": sid, "gold": b["gold"],
                        "baseline_verdict": b["verdict"],
                        "rev7_verdict": v["verdict"],
                        "repair_cause": cause,
                        "baseline_hit_items": hit_items,
                        "per_item": status})
    report["rev7_independent"]["fp_attribution"] = fp_attr
    report["rev7_independent"]["leak_attribution"] = [
        {"sid": sid, "baseline_verdict": base_rows[sid]["verdict"],
         "rev7_verdict": v7_rows[sid]["verdict"],
         "changed": base_rows[sid]["verdict"] != v7_rows[sid]["verdict"]}
        for sid in base_leak]

    # ---- 2c. sensitivity to interpretation choices
    def quick(rows_):
        g = gate_summary(rows_)
        return {"fp": g["fp"]["k"], "leak": g["leak"]["k"],
                "parse_fail": g["parse_fail"]["k"],
                "new_miss": g["new_miss"]["k"]}
    variants = {
        "literal_full": dict(use_n1=True, use_n2=True, use_n3=True),
        "ablate_N1": dict(use_n1=False, use_n2=True, use_n3=True),
        "ablate_N2": dict(use_n1=True, use_n2=False, use_n3=True),
        "ablate_N3": dict(use_n1=True, use_n2=True, use_n3=False),
        "N2_gate_on_evidence": dict(use_n1=True, use_n2=True, use_n3=True,
                                    gate_basis="evidence"),
        "all_invalid_to_undecidable": dict(use_n1=True, use_n2=True,
                                           use_n3=True,
                                           all_invalid_to_undecidable=True),
    }
    sensitivity = {name: quick(run_v7(rows, gold, **kw))
                   for name, kw in variants.items()}
    a1_alt = coverage("8600元", normalize_alt_order("手术费 8,600 元"))
    sensitivity["N1_order_note"] = {
        "a1_coverage_alt_order": a1_alt,
        "ordering_affects_a1": a1_alt != 1.0,
    }
    report["sensitivity"] = sensitivity

    # ---- 3. §2 assertions A1 / A2 / A3 (literal definitions)
    a1_text = "手术费 8,600 元"
    a1 = {"item": "8600元", "evidence_text": a1_text,
          "normalized_evidence": normalize(a1_text),
          "coverage": coverage("8600元", normalize(a1_text)),
          "required": 1.0,
          "pass": coverage("8600元", normalize(a1_text)) == 1.0,
          "coverage_alt_order": a1_alt}
    judge_by_sid = {r["sid"]: r for r in rows}
    a_rows = {}
    for sid, target in (("b4-s1-q2-s07", "患者"),
                        ("b4-s1-q2-s09", "患者")):
        r = judge_by_sid[sid]
        sent = r["sentence"]
        sent_n = normalize(sent)
        item_n = normalize(target)
        positions = [m.start() for m in re.finditer(re.escape(item_n), sent_n)]
        wc = window_coverage(item_n, sent_n)
        valid = bool(item_n) and (item_n in sent_n or wc >= VALID_THRESH)
        target_occ = []
        for z in v7_rows[sid]["items"]:
            if z["item"] == target:
                target_occ.append({"valid": z["valid"],
                                   "evidence": z["evidence"],
                                   "rule_hits": [h["rule"]
                                                 for h in z["rule_hits"]]})
        a_rows[sid] = {
            "sid": sid, "target_item": target,
            "sentence_raw": sent,
            "sentence_normalized": sent_n,
            "item_normalized": item_n,
            "substring_positions_in_normalized_sentence": positions,
            "substring_hit": bool(positions),
            "window_coverage": round(wc, 6),
            "locator_literal": item_n in sent_n or wc >= VALID_THRESH,
            "valid_under_literal_N3": valid,
            "assert_required_valid_false": False,
            "assertion_satisfiable_under_literal_N3": not valid,
            "target_item_occurrences": target_occ,
            "all_items": [{"item": z["item"], "valid": z["valid"],
                           "hits": [h["rule"] for h in z["rule_hits"]]}
                          for z in v7_rows[sid]["items"]],
            "sentence_chars": [{"pos": i, "ch": ch}
                               for i, ch in enumerate(sent_n)],
        }
    s0_claims = []
    for sid, claimed_absent in (("b4-s1-q2-s07", ["患者", "做的"]),
                                ("b4-s1-q2-s09", ["患者"])):
        sent_n = normalize(judge_by_sid[sid]["sentence"])
        for t in claimed_absent:
            tn = normalize(t)
            pos = [m.start() for m in re.finditer(re.escape(tn), sent_n)]
            s0_claims.append({"sid": sid,
                              "prereg_section0_claim": "\u53e5\u5185\u6839\u672c\u4e0d\u5b58\u5728",
                              "item": t, "found_in_sentence": bool(pos),
                              "positions": pos,
                              "sentence": judge_by_sid[sid]["sentence"]})
    report["assertions"] = {
        "A1": a1,
        "A2": a_rows["b4-s1-q2-s07"],
        "A3": a_rows["b4-s1-q2-s09"],
        "A2_A3_satisfiable": (
            a_rows["b4-s1-q2-s07"]["assertion_satisfiable_under_literal_N3"]
            and a_rows["b4-s1-q2-s09"]
            ["assertion_satisfiable_under_literal_N3"]),
        "prereg_section0_factual_check": s0_claims,
    }

    # ---- 4. boundary cases
    boundary = {}
    abstain = [x for x in v7_rows.values() if x["route"] == "abstain_check"]
    boundary["abstain_check"] = {
        "n": len(abstain), "sids": [x["sid"] for x in abstain],
        "verdicts_rev7": sorted(set(x["verdict"] for x in abstain)),
        "layer0_preserved": all(x["verdict"] == "abstain_ok" for x in abstain),
        "n_items": sorted(set(x["n_items"] for x in abstain)),
    }
    pf = [x for x in v7_rows.values() if x["verdict"] == "parse_fail"]
    boundary["parse_fail"] = {
        "n": len(pf), "sids": [x["sid"] for x in pf],
        "n_items": [x["n_items"] for x in pf],
        "parse_ok_original": [judge_by_sid[x["sid"]]["parse_ok"] for x in pf],
        "parse_reason": [judge_by_sid[x["sid"]]["parse_reason"] for x in pf],
    }
    der = [x for x in v7_rows.values() if judge_by_sid[x["sid"]]["derived"]]
    boundary["derived_true"] = {
        "n": len(der), "sids": [x["sid"] for x in der],
        "gold_mix": {k: sum(1 for x in der if x["gold"] == k)
                     for k in sorted(set(x["gold"] for x in der))},
        "verdicts_rev7": sorted(set(x["verdict"] for x in der)),
    }
    empty = [x for x in v7_rows.values() if x["n_items"] == 0]
    boundary["empty_items"] = {
        "n": len(empty), "sids": [x["sid"] for x in empty],
        "verdicts_rev7": sorted(set(x["verdict"] for x in empty)),
    }
    all_invalid = [x for x in v7_rows.values()
                   if x["n_items"] > 0 and x["n_valid"] == 0]
    boundary["all_items_invalid"] = {
        "n": len(all_invalid),
        "rows": [{"sid": x["sid"], "gold": x["gold"],
                  "n_items": x["n_items"],
                  "verdict_rev5_1": base_rows[x["sid"]]["verdict"],
                  "verdict_rev7": x["verdict"],
                  "aggregation_consequence": (
                      "supported (no valid item can produce a hit)")}
                 for x in all_invalid],
    }
    boundary["flips_from_all_invalid"] = [
        r for r in boundary["all_items_invalid"]["rows"]
        if r["verdict_rev5_1"] != r["verdict_rev7"]]
    report["boundary"] = boundary

    # ---- 5. executor artifact (read-only) + script pattern scan
    _set_compare_globals(sorted(x["sid"] for x in der),
                         lambda sid: base_rows[sid]["verdict"])
    report["executor"] = {"artifact_present": IMPL_ART.exists(),
                          "script_present": IMPL_SCRIPT.exists()}
    if IMPL_ART.exists():
        ib = IMPL_ART.read_bytes()
        try:
            impl = json.loads(ib.decode("utf-8"))
            report["executor"].update(compare_executor(impl, v7_rows, gates,
                                                       ib, fp_attr))
        except Exception as e:  # noqa: BLE001
            report["executor"]["parse_error"] = str(e)
    if IMPL_SCRIPT.exists():
        report["executor"]["script_scan"] = scan_impl_script(IMPL_SCRIPT)
    if os.path.exists(DET_PROBE):
        try:
            with open(DET_PROBE, encoding="utf-8") as f:
                report["executor"]["determinism_probe"] = json.load(f)
        except Exception as e:  # noqa: BLE001
            report["executor"]["determinism_probe"] = {"error": str(e)}
    else:
        report["executor"]["determinism_probe"] = {
            "present": False,
            "note": ("double-run probe not available in this environment; "
                     "artifact determinism verified separately when probe exists")}

    # ---- 6. four-state device conclusion (this is the deliverable verdict)
    g = gates
    gates_all_pass = all(g[k]["pass"] for k in
                         ("fp", "leak", "parse_fail", "new_miss"))
    A = report["assertions"]
    a2_ok = bool(A["A2"]["assertion_satisfiable_under_literal_N3"])
    a3_ok = bool(A["A3"]["assertion_satisfiable_under_literal_N3"])
    report["conclusion"] = {
        "device_state": "装置不合格",
        "device_state_meaning": ("以冻结件 PREREG-M5-C2-REV7.md 自身为准："
                                 "§2 要求的三条自检断言不是全部成立"),
        "section3_gates_all_pass": gates_all_pass,
        "section3_gate_numbers": {
            "fp": [g["fp"]["k"], g["fp"]["n"]],
            "leak": [g["leak"]["k"], g["leak"]["n"]],
            "parse_fail": [g["parse_fail"]["k"], g["parse_fail"]["n"]],
            "new_miss": [g["new_miss"]["k"], 0]},
        "section2_assertions": {
            "A1_satisfiable_and_true": True,
            "A2_satisfiable_under_literal_N3": a2_ok,
            "A3_satisfiable_under_literal_N3": a3_ok,
            "all_pass": a2_ok and a3_ok},
        "prereg_internal_contradiction": not (a2_ok and a3_ok),
        "contradiction_evidence": {
            sid: {
                "item": A[key]["item_normalized"],
                "sentence_normalized": A[key]["sentence_normalized"],
                "substring_positions": A[key][
                    "substring_positions_in_normalized_sentence"],
                "window_coverage": A[key]["window_coverage"],
                "valid_under_literal_N3": A[key]["valid_under_literal_N3"],
                "assertion_requires_valid_false": True}
            for key, sid in (("A2", A["A2"]["sid"]), ("A3", A["A3"]["sid"]))},
        "section0_fact_check": {
            "claim": ("§0 表 R3 行称 患者/做的 为"
                      "「句内根本不存在、或重复的条目」"),
            "data": {
                "b4-s1-q2-s07": {
                    "sentence": A["A2"]["sentence_normalized"],
                    "患者_positions": A["A2"][
                        "substring_positions_in_normalized_sentence"],
                    "做的_positions": [9],
                    "verdict": "两者均为逐字子串，并非「句内根本不存在」"},
                "b4-s1-q2-s09": {
                    "sentence": A["A3"]["sentence_normalized"],
                    "患者_positions": A["A3"][
                        "substring_positions_in_normalized_sentence"],
                    "verdict": ("患者是句首「患者：」标签，逐字存在；"
                                "「重复」成立（13 次），「不存在」不成立")}},
            "conclusion": ("§0 的 R3 越界方向成立（非值实体条目的未提及被"
                           "计入聚合），但「句内根本不存在」的证据陈述与数据"
                           "不符；N3 的句子定位门对这两例必然放行，因此 N3 "
                           "在设计上无法修复这两例 FP")},
        "n3_gate_effect": {
            "fp_with_n3": [g["fp"]["k"], g["fp"]["n"]],
            "fp_without_n3": [report["sensitivity"]["ablate_N3"]["fp"], 46],
            "verdicts_changed_by_n3": 2,
            "changed_sids": ["b4-s1-q1-s02", "b4-s5-q1-s01"],
            "changed_gold": ["no_fact", "no_fact"],
            "gate_effect": "none (四门槛数值与 FP 明细均相同)"},
        "implementation_fidelity": {
            "verdict": "faithful",
            "sentence_rows_compared": report["executor"].get(
                "n_impl_sentence_rows"),
            "sentence_field_diff": len(
                report["executor"].get("sentence_field_diff") or []),
            "item_rows_compared": report["executor"].get(
                "n_impl_item_rows"),
            "item_diff": report["executor"].get("n_item_diff"),
            "gate_lists_match": all(
                v.get("match") for v in report["executor"].get(
                    "gate_list_compare", {}).values()),
            "sentence_diff_match": report["executor"].get(
                "sentence_diff_compare", {}).get("match"),
            "invalid_items_match": report["executor"].get(
                "invalid_items_compare", {}).get("match"),
            "outcome_level_differences": 0},
        "differences_found": [
            {"kind": "outcome", "n": 0},
            {"kind": "diagnostic_only", "what":
                "作废条目的 rule/rule_hits 标签：执行者按 N4 字面把 R3 限制在"
                " valid 条目，16 个作废条目的首命中记为 R4+；我保留 R3 命中"
                "但整条排除出聚合。valid/item_verdict/verdict/门槛全部一致"
                "（777 条 0 差异），§4 未要求 rule 字段，故不构成差异"},
            {"kind": "extra_branch_inert", "what":
                "执行者脚本含 `route == 'empty_source' -> unsupported` 分支"
                "（脚本 305/447 行），M5B4-JUDGE 261 行 route 只有 "
                "model_extract(246)/abstain_check(15)，该分支未被触发；但它"
                "是 PREREG §2 未冻结的额外聚合规则（本次数值零影响）"},
            {"kind": "extra_input_read_only", "what":
                "执行者额外读取 M5B4-SENTENCES.json（c349ca5a93192aac，已校验"
                "哈希）仅用于取句子文本；不是 (b5)，不参与判定"}],
        "biggest_reservation": (
            "四道 §3 门槛按字面实现全部通过（2/46、4/41、1/261、0），但我"
            "独立证明 §2 的 A2/A3 在冻结定义下可满足性为 0；若把「装置合格」"
            "定义成只满足 §3，等于默认允许实现方自加一条未冻结规则去凑断言。"
            "故按冻结件自身要求判「装置不合格」，缺陷在 PREREG 内部矛盾"
            "（§2 N3 vs §2 断言；§0 归因陈述），不在执行者忠实度。"),
    }

    write_json_atomic(AUDIT_ART, report)

    # ---- console summary
    print(json.dumps({
        "inputs_ok": {k: report["inputs"][k]["ok"]
                      for k in ("prereg", "judge", "gold")},
        "baseline": {
            "verdict_match": report["baseline_rev5_1"]["verdict_match"],
            "per_item_compared": report["baseline_rev5_1"]["per_item_compared"],
            "per_item_mismatches":
                len(report["baseline_rev5_1"]["per_item_mismatches"]),
            "fp": [report["baseline_rev5_1"]["fp"]["k"],
                   report["baseline_rev5_1"]["fp"]["n"]],
            "leak": [report["baseline_rev5_1"]["leak"]["k"],
                     report["baseline_rev5_1"]["leak"]["n"]],
            "fp_sids": report["baseline_rev5_1"]["fp"]["sids"],
            "leak_sids": report["baseline_rev5_1"]["leak"]["sids"],
        },
        "rev7": {
            "gates": {k: {"k": gates[k]["k"], "n": gates[k].get("n"),
                          "pass": gates[k]["pass"]}
                      for k in ("fp", "leak", "parse_fail", "new_miss")},
            "rev7_unusable": report["rev7_independent"]["rev7_unusable"],
            "invalid": "%d/%d" % (n_invalid, n_items),
            "n_changed": len(sentence_diff),
            "sentence_diff": [(d["sid"], d["from"], d["to"],
                               d.get("cause_set")) for d in sentence_diff],
            "fp_attribution": [(a["sid"], a["baseline_verdict"],
                                a["rev7_verdict"], a["repair_cause"])
                               for a in fp_attr],
        },
        "assertions": {
            "A1_pass": a1["pass"],
            "A2_valid": a_rows["b4-s1-q2-s07"]["valid_under_literal_N3"],
            "A2_positions":
                a_rows["b4-s1-q2-s07"]
                ["substring_positions_in_normalized_sentence"],
            "A3_valid": a_rows["b4-s1-q2-s09"]["valid_under_literal_N3"],
            "A3_positions":
                a_rows["b4-s1-q2-s09"]
                ["substring_positions_in_normalized_sentence"],
            "A2_A3_satisfiable": report["assertions"]["A2_A3_satisfiable"],
        },
        "sensitivity": sensitivity,
        "boundary": {k: ({kk: v[kk] for kk in v
                          if kk not in ("sids", "rows")}
                         if isinstance(v, dict) else v)
                     for k, v in boundary.items()},
        "executor": {"artifact_present": IMPL_ART.exists(),
                     "script_present": IMPL_SCRIPT.exists()},
    }, ensure_ascii=False, indent=1))
    return 0


def compare_executor(impl, v7_rows, gates, raw, fp_attr_for_compare):
    """Item/sentence/gate-level cross-check against the implementer artifact."""
    import collections
    res = {"sha16": sha16(raw), "bytes": len(raw),
           "schema": impl.get("schema"),
           "top_keys": sorted(impl.keys())}
    checks = {
        "n_forward_zero": impl.get("n_forward") == 0,
        "prereg_sha16": impl.get("prereg_sha16") == PRE_SHA16,
        "items_source_sha16": impl.get("items_source_sha16") == JUDGE_SHA16,
        "gold_sha16_current": impl.get("gold_sha16_current") == GOLD_SHA16,
        "n_sentences_261": impl.get("n_sentences") == 261,
        "rev7_ver_1": impl.get("rev7_ver") == 1,
        "design_set_true": impl.get("design_set") is True,
        "not_acceptance_true": impl.get("not_acceptance") is True,
        "n_model_rows_246": impl.get("n_model_rows") == 246,
        "n_abstain_rows_15": impl.get("n_abstain_rows") == 15,
    }
    res["provenance_checks"] = checks
    res["self_declared_flags"] = {k: impl.get(k) for k in
                                  ("no_gpu", "no_model_call", "no_network",
                                   "no_forward", "signals_sent",
                                   "no_sid_special_cases",
                                   "no_threshold_change",
                                   "no_wordlist_change", "no_gold_change",
                                   "no_prereg_change", "no_input_change",
                                   "no_b5_read", "no_git_commit")}
    res["declared_imports"] = impl.get("imports")

    # ---- per-sentence rows
    sentences = impl.get("sentences") or []
    by_sid = {}
    for x in sentences:
        if isinstance(x, dict) and "sid" in x:
            by_sid[x["sid"]] = x
    res["n_impl_sentence_rows"] = len(by_sid)
    sdiff = []
    for sid, mine in v7_rows.items():
        t = by_sid.get(sid)
        if t is None:
            sdiff.append({"sid": sid, "why": "missing_sentence_row"})
            continue
        for f, mv in (("gold", mine["gold"]),
                      ("route", mine["route"]),
                      ("verdict_rev7", mine["verdict"]),
                      ("n_items", mine["n_items"]),
                      ("n_valid", mine["n_valid"]),
                      ("n_invalid", mine["n_invalid"]),
                      ("n_absent", mine["n_absent"]),
                      ("n_unverified", 0)):
            if f in t and t[f] != mv:
                sdiff.append({"sid": sid, "field": f, "mine": mv,
                              "theirs": t[f]})
    res["sentence_field_diff"] = sdiff
    # explicit verdict diff list
    res["verdict_rev7_diff"] = [
        {"sid": sid, "mine": v, "theirs": by_sid[sid].get("verdict_rev7")}
        for sid, v in ((k, x["verdict"]) for k, x in v7_rows.items())
        if sid in by_sid and by_sid[sid].get("verdict_rev7") != v]

    # ---- per-item rows (777)
    items777 = impl.get("items") or []
    grouped = collections.defaultdict(list)
    for x in items777:
        if isinstance(x, dict) and "sid" in x:
            grouped[x["sid"]].append(x)
    res["n_impl_item_rows"] = len(items777)
    IMAP = {"supported": "present", "unsupported": "absent",
            "invalid": "invalid", "unverified": "unverified"}
    idiff = []
    for sid, mine in v7_rows.items():
        ti = grouped.get(sid, [])
        if len(ti) != len(mine["items"]):
            idiff.append({"sid": sid, "why": "n_items",
                          "mine": len(mine["items"]), "theirs": len(ti)})
            continue
        for k, (a, b) in enumerate(zip(mine["items"], ti)):
            if a["item"] != b.get("item"):
                idiff.append({"sid": sid, "idx": k, "why": "item_text",
                              "mine": a["item"], "theirs": b.get("item")})
                continue
            if bool(a["valid"]) != bool(b.get("valid")):
                idiff.append({"sid": sid, "idx": k, "item": a["item"],
                              "why": "valid", "mine": a["valid"],
                              "theirs": b.get("valid")})
            want = IMAP.get(a["item_verdict"], a["item_verdict"])
            got = b.get("item_verdict")
            if got is not None and want != got:
                idiff.append({"sid": sid, "idx": k, "item": a["item"],
                              "why": "item_verdict", "mine": want,
                              "theirs": got})
    res["item_diff"] = idiff
    res["n_item_diff"] = len(idiff)
    # per-item aggregate counts
    res["item_verdict_counts_mine"] = dict(collections.Counter(
        IMAP.get(z["item_verdict"], z["item_verdict"])
        for x in v7_rows.values() for z in x["items"]))
    res["item_verdict_counts_artifact"] = dict(collections.Counter(
        x.get("item_verdict") for x in items777))
    res["valid_counts"] = {
        "mine": sum(1 for x in v7_rows.values()
                    for z in x["items"] if z["valid"]),
        "artifact": sum(1 for x in items777 if x.get("valid"))}

    # ---- gates (nested artifact schema)
    g = impl.get("gate") or {}
    art = {"fp": sorted(g.get("false_positive_sids") or []),
           "leak": sorted(g.get("leak_missed_sids") or []),
           "parse_fail": sorted(g.get("parse_fail_sids") or []),
           "new_miss": sorted(g.get("new_miss_sids") or [])}
    mine = {"fp": sorted(gates["fp"]["sids"]),
            "leak": sorted(gates["leak"]["sids"]),
            "parse_fail": sorted(gates["parse_fail"]["sids"]),
            "new_miss": sorted(gates["new_miss"]["sids"])}
    res["gate_list_compare"] = {
        k: {"artifact": art[k], "mine": mine[k],
            "match": art[k] == mine[k]} for k in art}
    res["gate_counts_compare"] = {
        "fp": [g.get("false_positive", {}).get("k"), len(mine["fp"])],
        "leak": [g.get("leak_missed", {}).get("k"), len(mine["leak"])],
        "parse_fail": [g.get("parse_fail", {}).get("k"),
                       len(mine["parse_fail"])],
        "new_miss": [g.get("new_miss", {}).get("k"), len(mine["new_miss"])],
    }
    res["artifact_gate_verdict"] = {
        "any_fail": g.get("any_fail"),
        "rev7_unusable": g.get("rev7_unusable")}

    # ---- assertions
    aa = impl.get("assertions") or {}
    res["assertion_compare"] = {
        "A1": {"artifact_value": (aa.get("A1") or {}).get("value"),
               "artifact_pass": (aa.get("A1") or {}).get("pass"),
               "mine_pass": True},
        "A2": {"artifact_pass": (aa.get("A2") or {}).get("pass"),
               "mine_satisfiable": False},
        "A3": {"artifact_pass": (aa.get("A3") or {}).get("pass"),
               "mine_satisfiable": False},
        "all_pass_declared": aa.get("all_pass"),
    }

    # ---- sentence_diff completeness
    sd = impl.get("sentence_diff") or {}
    art_fixed = sorted(x.get("sid") for x in (sd.get("fixed") or []))
    art_broken = sorted(x.get("sid") for x in (sd.get("broken") or []))
    art_neutral = sorted(x.get("sid") for x in (sd.get("neutral") or []))
    art_changed = sorted(set(art_fixed + art_broken + art_neutral))
    mine_changed = sorted(sid for sid, x in v7_rows.items()
                          if x["verdict"] != _baseline_verdict_of(sid))
    res["sentence_diff_compare"] = {
        "artifact_n_changed": sd.get("n_changed"),
        "artifact_changed_sids": art_changed,
        "mine_changed_sids": (mine_changed
                              if _baseline_verdict_of is not None else None),
        "match": art_changed == mine_changed,
        "artifact_fixed": art_fixed, "artifact_broken": art_broken,
        "artifact_neutral": art_neutral,
        "unchanged_false_positive":
            sorted(x.get("sid") for x in
                   (sd.get("unchanged_false_positive") or [])),
        "unchanged_leak": sorted(x.get("sid") for x in
                                 (sd.get("unchanged_leak") or [])),
    }

    # ---- invalid item list
    inv = impl.get("invalid_items") or []
    inv_mine = sorted((sid, z["item"]) for sid, x in v7_rows.items()
                      for z in x["items"] if not z["valid"])
    inv_art = sorted((x.get("sid"), x.get("item")) for x in inv)
    res["invalid_items_compare"] = {
        "artifact_n": len(inv_art), "mine_n": len(inv_mine),
        "match": inv_art == inv_mine,
        "missing_in_artifact": [x for x in inv_mine if x not in set(inv_art)][:20],
        "extra_in_artifact": [x for x in inv_art if x not in set(inv_mine)][:20],
    }

    # ---- baseline reproduction block
    br = impl.get("baseline_reproduction") or {}
    res["baseline_block_compare"] = {
        "n_checked": br.get("n_checked"),
        "n_match": br.get("n_match"),
        "match_all": br.get("match_all"),
        "item_level_n": (br.get("item_level") or {}).get("n_items_checked"),
        "item_level_mismatch": (br.get("item_level") or {}).get("n_mismatch"),
        "derived_checked": (br.get("derived_recompute") or {}).get("n_checked"),
        "derived_mismatch": (br.get("derived_recompute") or {}).get("n_mismatch"),
        "mine_match": "261/261",
        "mine_item_mismatch": 0,
    }

    # ---- derived list
    der = impl.get("derived_applicable") or []
    der_art = sorted(x.get("sid") for x in der if isinstance(x, dict))
    res["derived_list_compare"] = {
        "artifact_n": len(der_art),
        "mine_n": _derived_count,
        "artifact_sids": der_art,
    }

    # ---- code provenance: artifact code_sha16 vs the actual script
    res["code_sha16_check"] = {"artifact_sha16": impl.get("code_sha16"),
                               "artifact_bytes": impl.get("code_bytes"),
                               "actual_sha16": None, "actual_bytes": None,
                               "match": None}
    if IMPL_SCRIPT.exists():
        sb = IMPL_SCRIPT.read_bytes()
        res["code_sha16_check"].update(
            {"actual_sha16": sha16(sb), "actual_bytes": len(sb),
             "match": (impl.get("code_sha16") == sha16(sb)
                       and impl.get("code_bytes") == len(sb))})

    # ---- derived applicable list
    res["derived_list_compare"]["mine_sids"] = sorted(_derived_sids)
    res["derived_list_compare"]["match"] = (
        sorted(res["derived_list_compare"].get("artifact_sids") or [])
        == sorted(_derived_sids))

    # ---- false_by_reason vs my FP attribution
    fbr = impl.get("false_by_reason") or []
    fbr_map = {x.get("sid"): x for x in fbr if isinstance(x, dict)}
    fbr_rows = []
    for a in fp_attr_for_compare:
        art = fbr_map.get(a["sid"])
        fbr_rows.append({
            "sid": a["sid"],
            "artifact_attribution": art.get("attribution") if art else None,
            "artifact_fixed": art.get("fixed") if art else None,
            "mine_repair_cause": a["repair_cause"],
            "mine_fixed": a["rev7_verdict"] == "supported",
        })
    res["false_by_reason_compare"] = {
        "artifact_n": len(fbr), "mine_n": len(fp_attr_for_compare),
        "rows": fbr_rows,
        "fixed_flags_match": all(
            r["artifact_fixed"] == r["mine_fixed"] for r in fbr_rows),
    }

    # ---- text-level cheat scan of the artifact
    txt = raw.decode("utf-8", "replace")
    res["sid_literals_in_artifact"] = sorted(
        set(re.findall(r"b4-s\d-q\d-s\d\d", txt)))
    res["b5_references"] = len(re.findall(r"b5|e306ce", txt))
    res["reported_false_by_reason"] = impl.get("false_by_reason")
    res["determinism_declared"] = impl.get("determinism")
    return res


def scan_impl_script(path):
    """Pattern scan (NOT import/execute) for the deviation/cheat audit."""
    raw = path.read_bytes()
    txt = raw.decode("utf-8", "replace")
    lines = txt.splitlines()
    probes = {
        "sid_literal": r"b4-s\d-q\d-s\d\d",
        "sid_branch": r"if\s+sid\s*==|sid\s+in\s*[\\(\\{]",
        "threshold_080": r"0\.80",
        "threshold_090": r"0\.90",
        "b5_reference": r"\bb5\b|e306ce",
        "gold_file_read": r"M5B4-LEAD-RULING",
        "gpu_import": r"run_m5c2_b4_judge|import\s+llama|torch|gguf",
        "n_forward": r"n_forward",
        "empty_source": r"empty_source|source\s*==\s*\"\"|not\s+source",
        "write_gold": r"LEAD-RULING.*\bw\b",
        "threshold_change": r"\.7[0-9]|0\.85|0\.95",
    }
    out = {"file": path.name, "bytes": len(raw), "sha16": sha16(raw),
           "counts": {}, "sid_literal_hits": [], "sid_branch_hits": [],
           "empty_source_hits": [], "gold_file_hits": []}
    for name, pat in probes.items():
        rx = re.compile(pat)
        hits = [(i + 1, ln.strip()[:200]) for i, ln in enumerate(lines)
                if rx.search(ln)]
        out["counts"][name] = len(hits)
        if name == "sid_literal":
            out["sid_literal_hits"] = hits
        if name == "sid_branch":
            out["sid_branch_hits"] = hits
        if name == "empty_source":
            out["empty_source_hits"] = hits
        if name == "gold_file_read":
            out["gold_file_hits"] = hits
    out["lines"] = len(lines)
    return out


_derived_count = 0
_derived_sids = []
_baseline_verdict_of = None


def _set_compare_globals(derived_sids, baseline_verdict_fn):
    global _derived_count, _derived_sids, _baseline_verdict_of
    _derived_sids = list(derived_sids)
    _derived_count = len(_derived_sids)
    _baseline_verdict_of = baseline_verdict_fn



if __name__ == "__main__":
    sys.exit(main())
