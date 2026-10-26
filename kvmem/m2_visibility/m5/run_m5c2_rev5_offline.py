#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 REV5 offline: R4+ evidence existence + R_DERIVED+ arithmetic
composability.  Reuses the 106 model extractions already stored in
M5C2-B2EVAL.json; ZERO GPU, ZERO forwards.

Frozen prereg: docs/_work/PREREG-M5-C2-REV5.md 81a5bb3ea4df642e / 4,807 B / 79 lines
Input: M5C2-B2EVAL.json 553a96fc481fcf9c
"""
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
import run_m5c2_rev4_1 as R41  # noqa: E402

PRE = ROOT / "docs/_work/PREREG-M5-C2-REV5.md"
PRE_SHA16 = "81a5bb3ea4df642e"
PRE_BYTES = 4807
PRE_LINES = 79
B2 = OUT / "M5C2-B2EVAL.json"
B2_SHA16 = "553a96fc481fcf9c"
REV41 = OUT / "M5C2-REV4-1.json"
ART = OUT / "M5C2-REV5-OFFLINE.json"
PROMPT_SHA = "a6bc4f268f7711de"

DERIVED_RE = R41.DERIVED_RE
NEG_WORDS = R41.NEG_WORDS
ABSENT_MARKERS = R41.ABSENT_MARKERS

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


def verify():
    b = PRE.read_bytes()
    if sha16(b) != PRE_SHA16 or len(b) != PRE_BYTES:
        raise SystemExit("rev5 prereg changed")
    if b.count(b"\n") + 1 != PRE_LINES:
        raise SystemExit("rev5 prereg line count changed")
    if b"R4+" not in b or b"R_DERIVED+" not in b:
        raise SystemExit("rev5 marker missing")
    bb = B2.read_bytes()
    if sha16(bb) != B2_SHA16:
        raise SystemExit("B2 input changed")
    return True


def normalize(s):
    return re.sub(r"\s+", "", s or "")


def bgrams(s):
    return [s[i:i + 2] for i in range(max(0, len(s) - 1))] or ([s] if s else [])


def coverage(a, b):
    if not a:
        return 0.0
    if a in b:
        return 1.0
    bs = bgrams(a)
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


def r1_r2_r3(entry, evidence):
    """Unchanged R1/R2/R3 from rev4.1, copied without old R4."""
    hits = []
    ev = normalize(evidence)
    ent = normalize(entry)
    # R1 value check
    for tok in R41.value_tokens(entry):
        cov = R41.fuzzy_coverage(normalize(tok), ev)
        if cov < 0.80:
            hits.append({"rule": "R1", "reason": "value_mismatch", "span": tok})
    # R2 negation check
    anchors = []
    for a in R41.value_tokens(entry) + [ent]:
        a = normalize(a)
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
    # R3 absent markers
    r3 = None
    for marker in ABSENT_MARKERS:
        if normalize(marker) in ev:
            r3 = marker
            hits.append({"rule": "R3", "reason": "absent_marker", "span": marker})
            break
    return hits, r3


def r4_plus(evidence, source, has_r3):
    """R4+: every non-absent-marker evidence must exist in source (exact or
    best-window bigram coverage >= 0.80)."""
    if has_r3:
        return None
    ev = normalize(evidence)
    src = normalize(source)
    if not ev:
        return {"rule": "R4+", "reason": "fabricated_evidence", "span": "(empty)"}
    if ev in src:
        return None
    cov = window_coverage(ev, src)
    if cov >= 0.80:
        return None
    return {"rule": "R4+", "reason": "fabricated_evidence",
            "span": evidence, "coverage": round(cov, 4)}


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
    # exact source value
    if any(abs(v - s) <= 1e-9 for s in srcvals):
        return True
    # arithmetic combinations of two source values, +/-1 rounding
    for a in srcvals:
        for b in srcvals:
            cands = [a + b, abs(a - b), a * b]
            if b:
                cands.append(a / b)
            if a:
                cands.append(b / a)
            for c in cands:
                # "±1 舍入" is an integer-rounding allowance, not a blanket
                # tolerance: 17/7=2.428 must not count as the claimed value 2.
                if abs(c - round(c)) <= 1e-9 and abs(v - c) <= 1e-9:
                    return True
    return False


def derived_plus(sentence, source):
    """Return (enabled, detail).  enabled=True => legal derived reasoning."""
    if not DERIVED_RE.search(sentence):
        return False, {"applicable": False}
    svals = numbers(source)
    vals = numbers(sentence)
    missing = [v for v in vals if not composable(v, svals)]
    enabled = len(missing) == 0
    return enabled, {
        "applicable": True,
        "sentence_values": vals,
        "source_values": svals,
        "missing_values": missing,
        "enabled": enabled,
        "keyword": (DERIVED_RE.search(sentence).group(0)
                    if DERIVED_RE.search(sentence) else ""),
    }


def judge_items(items, source):
    out = []
    for it in items:
        entry = it.get("item", "")
        evidence = it.get("evidence", "")
        hits, r3 = r1_r2_r3(entry, evidence)
        r4 = r4_plus(evidence, source, r3 is not None)
        if r4:
            hits.append(r4)
        out.append({"item": entry, "evidence": evidence,
                    "absent": bool(hits), "rule_hits": hits,
                    "r3_hit": r3 is not None})
    return out


def template_of(text):
    if "打包纸箱" in text:
        return "打包纸箱"
    if "身份证" in text and "学员卡" in text:
        return "材料清单"
    if "教练姓张" in text:
        return "教练姓张"
    if "天气" in text:
        return "天气"
    return None


def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / float(n)
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(max(0.0, center - half), 6), round(min(1.0, center + half), 6)]


def main():
    verify()
    b2 = json.load(open(B2, encoding="utf-8"))
    old_items = b2["items"]
    if len(old_items) != 106:
        raise SystemExit("expected 106 B2 items")
    old_false = set(b2["false_rows"])
    old_leak = set(b2["leak_rows"])
    old_strict = set(b2["strict_leak_rows"])

    rows = []
    for it in old_items:
        sid = it["sid"]
        src = it["source"]
        sent = it["sentence"]
        oldv = it["verdict"]
        items_new = judge_items(it["items"], src)
        en, dd = derived_plus(sent, src)
        if not it["parse_ok"]:
            newv = "parse_fail"
        elif en:
            newv = "undecidable"
        elif not items_new:
            newv = "undecidable"
        elif any(z["absent"] for z in items_new):
            newv = "unsupported"
        else:
            newv = "supported"
        rec = {
            "sid": sid, "gold": it["gold"], "sentence": sent, "source": src,
            "verdict_old": oldv, "verdict_new": newv,
            "items": items_new,
            "rule_hits": [h for z in items_new for h in z["rule_hits"]],
            "derived_plus": dd,
            "template": template_of(sent),
            "parse_ok": it["parse_ok"],
        }
        if en:
            rec["rule_hits"].append({"rule": "R_DERIVED+",
                                     "reason": "all_values_composable",
                                     "span": dd.get("keyword", "")})
        rows.append(rec)

    # D1 rejudge (deterministic; no model output needed)
    rev41 = json.load(open(REV41, encoding="utf-8"))
    old_d1 = {x["fid"]: x["verdict"] for x in rev41["items"] if x["arm"] == "D1"}
    d1_cases = R41.D1_CASES
    d1_rows = []
    for fid, sentence, source in d1_cases:
        items = [{"item": sentence, "evidence": source}]
        items_new = judge_items(items, source)
        en, dd = derived_plus(sentence, source)
        if en:
            newv = "undecidable"
        elif any(z["absent"] for z in items_new):
            newv = "unsupported"
        elif items_new:
            newv = "supported"
        else:
            newv = "undecidable"
        rec = {
            "sid": fid, "gold": None, "sentence": sentence, "source": source,
            "verdict_old": old_d1.get(fid), "verdict_new": newv,
            "items": items_new,
            "rule_hits": [h for z in items_new for h in z["rule_hits"]],
            "derived_plus": dd,
            "template": None, "parse_ok": True,
            "d1_changed": old_d1.get(fid) != newv,
        }
        if en:
            rec["rule_hits"].append({"rule": "R_DERIVED+",
                                     "reason": "all_values_composable",
                                     "span": dd.get("keyword", "")})
        d1_rows.append(rec)

    # B2 scoring
    supp = [x for x in rows if x["gold"] == "support_present"]
    fab = [x for x in rows if x["gold"] == "fabricated"]
    leak_new = [x for x in fab if x["verdict_new"] in ("supported", "undecidable")]
    false_new = [x for x in supp if x["verdict_new"] == "unsupported"]
    any_non_new = [x for x in supp if x["verdict_new"] in ("unsupported", "undecidable")]
    strict_new = [x for x in fab if x["verdict_new"] == "supported"]
    pf_new = [x for x in rows if x["verdict_new"] == "parse_fail"]

    def rate(k, n):
        return {"numerator": k, "denominator": n,
                "rate": round(k / n, 4) if n else None,
                "wilson95": wilson(k, n)}

    rates = {
        "old": {
            "leak": rate(len(old_leak), 35),
            "false": rate(len(old_false), 71),
            "strict_leak": rate(len(old_strict), 35),
        },
        "new": {
            "leak": rate(len(leak_new), 35),
            "false": rate(len(false_new), 71),
            "any_non_supported_false": rate(len(any_non_new), 71),
            "strict_leak": rate(len(strict_new), 35),
            "parse_fail": rate(len(pf_new), 106),
        },
    }
    groups = {}
    for name in ("打包纸箱", "材料清单", "教练姓张", "天气"):
        gs = [x for x in fab if x["template"] == name]
        old_leaked = [x for x in gs if x["verdict_old"] in ("supported", "undecidable")]
        new_leaked = [x for x in gs if x["verdict_new"] in ("supported", "undecidable")]
        old_caught = [x for x in gs if x["verdict_old"] == "unsupported"]
        new_caught = [x for x in gs if x["verdict_new"] == "unsupported"]
        groups[name] = {
            "n": len(gs),
            "old_leaked": len(old_leaked), "old_caught": len(old_caught),
            "new_leaked": len(new_leaked), "new_caught": len(new_caught),
            "new_leaked_sids": [x["sid"] for x in new_leaked],
            "new_caught_sids": [x["sid"] for x in new_caught],
        }
    moving = [x for x in fab if "搬家师傅" in x["sentence"] and "一共" in x["sentence"]]
    moving_detail = [{
        "sid": x["sid"], "sentence": x["sentence"],
        "verdict_old": x["verdict_old"], "verdict_new": x["verdict_new"],
        "values": x["derived_plus"].get("sentence_values"),
        "source_values": x["derived_plus"].get("source_values"),
        "missing_values": x["derived_plus"].get("missing_values"),
        "rule_hits": x["rule_hits"],
    } for x in moving]
    moving_caught = [x for x in moving if x["verdict_new"] == "unsupported"]
    packing_caught = groups["打包纸箱"]["new_caught"]
    rev5_rules_hold = packing_caught >= 8 and len(moving_caught) >= 10
    false_unchanged = set(x["sid"] for x in false_new) == old_false

    out = {
        "schema": "m5c2_rev5_offline_v1",
        "status": "已读数",
        "rules_version": "R4+/R_DERIVED+",
        "prereg": {"file": PRE.name, "sha16": sha16(PRE.read_bytes()),
                   "bytes": PRE.stat().st_size,
                   "lines": PRE.read_bytes().count(b"\n") + 1},
        "reused_model_output": True,
        "n_forward": 0,
        "n_forward_planned": 0,
        "repeated_look_at_b2": True,
        "in_sample_for_leak_templates": True,
        "not_acceptance": True,
        "b2_input": {"file": B2.name, "sha16": sha16(B2.read_bytes()),
                     "bytes": B2.stat().st_size},
        "prompt_sha16": PROMPT_SHA,
        "n_b2": len(rows), "n_d1": len(d1_rows), "n_done": len(rows) + len(d1_rows),
        "rates": rates,
        "leak_rows_new": [x["sid"] for x in leak_new],
        "false_rows_new": [x["sid"] for x in false_new],
        "any_non_supported_false_rows_new": [x["sid"] for x in any_non_new],
        "strict_leak_rows_new": [x["sid"] for x in strict_new],
        "parse_fail_rows_new": [x["sid"] for x in pf_new],
        "false_unchanged": false_unchanged,
        "false_delta": len(false_new) - len(old_false),
        "leak_delta": len(leak_new) - len(old_leak),
        "template_groups": groups,
        "moving_detail": {
            "n": len(moving), "caught": len(moving_caught),
            "leaked": len(moving) - len(moving_caught),
            "rows": moving_detail,
        },
        "rev5_rules_hold": rev5_rules_hold,
        "checks": {
            "packing_caught_ge_8": packing_caught >= 8,
            "moving_caught_ge_10": len(moving_caught) >= 10,
            "material_caught_3": groups["材料清单"]["new_caught"] == 3,
            "coach_caught_1": groups["教练姓张"]["new_caught"] == 1,
            "weather_caught_1": groups["天气"]["new_caught"] == 1,
            "false_unchanged": false_unchanged,
            "no_forward": True,
        },
        "d1": d1_rows,
        "d1_3_changed": next((x["d1_changed"] for x in d1_rows if x["sid"] == "D1-3"), None),
        "d1_3": next((x for x in d1_rows if x["sid"] == "D1-3"), None),
        "items": rows + d1_rows,
        "composition_note": "R_DERIVED+ requires exact integer/float compositions; the ±1 wording is treated as integer rounding of the candidate, not a ±1 numeric tolerance (so 17/7=2.43 and 1+1 are not treated as 2).",
        "no_gpu": True, "signals_sent": False,
        "no_prompt_change": True, "no_model_call": True,
        "no_rule_change_r1_r2_r3": True,
        "no_sid_special_cases": True,
        "no_acceptance_verdict": True,
        "no_threshold_change": True,
    }
    write_json_atomic(ART, out)
    print(json.dumps({k: out[k] for k in ("status", "rules_version", "n_forward",
                                          "n_b2", "n_d1", "rates", "leak_rows_new",
                                          "false_rows_new", "false_unchanged",
                                          "template_groups", "moving_detail",
                                          "rev5_rules_hold", "checks",
                                          "d1_3_changed", "d1_3")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())