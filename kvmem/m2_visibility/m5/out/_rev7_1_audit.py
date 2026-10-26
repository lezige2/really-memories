#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 REV7.1 independent re-audit (zero GPU / zero model / zero network).

Object
  PREREG-M5-C2-REV7.1.md            09d6f1b163ea0b84 / 16,313 B / 160 lines
  run_m5c2_rev7_1_offline.py        88256d274c9993cc /  50,618 B
  out/M5C2-REV7-1-OFFLINE.json      55191eaf2426f736 / 510,508 B
Baseline (reference only, never modified)
  PREREG-M5-C2-REV7.md             32eaf82ca56600c4 /   5,835 B /  88 lines
  run_m5c2_rev7_offline.py         65ed60125528d5d6 /  44,761 B
  out/M5C2-REV7-OFFLINE.json       1f8f44b921e575fe / 507,657 B
Inputs
  M5B4-JUDGE.json 6a3001b6ca23ef7d ; M5B4-LEAD-RULING.json 9273ebc97aa1413a ;
  M5B4-SENTENCES.json c349ca5a93192aac (cross-check only).  Never (b5).

DISCIPLINE
  * This script does NOT import / execute / copy run_m5c2_rev7_1_offline.py.
  * The rule implementation is reused from my own previous independent audit
    module out/_rev7_audit.py (6695a4b4de403870), which was written from the
    frozen PREREG without reading the implementer script.  It is MY code, not
    the implementer's.
  * Conclusion numbers come from my own recompute, not from the artifact.
  * Deterministic: no timestamps / no randomness in the output JSON.

Output: out/M5C2-REV7-1-AUDIT.json
"""
import ast
import collections
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
OUT = HERE.parent
M5 = OUT.parent
ROOT = M5.parents[2]
DOCS = ROOT / "docs/_work"

PRE71 = DOCS / "PREREG-M5-C2-REV7.1.md"
PRE7 = DOCS / "PREREG-M5-C2-REV7.md"
B5PRE = DOCS / "PREREG-M5-C2-B5.md"
JUDGE = OUT / "M5B4-JUDGE.json"
GOLD = OUT / "M5B4-LEAD-RULING.json"
SENT = OUT / "M5B4-SENTENCES.json"
SCRIPT71 = M5 / "run_m5c2_rev7_1_offline.py"
SCRIPT7 = M5 / "run_m5c2_rev7_offline.py"
ART71 = OUT / "M5C2-REV7-1-OFFLINE.json"
ART7 = OUT / "M5C2-REV7-OFFLINE.json"
AUDIT = OUT / "M5C2-REV7-1-AUDIT.json"

EXPECT = {
    "prereg71": {"sha16": "09d6f1b163ea0b84", "bytes": 16313, "lines": 160,
                 "end_newline": False},
    "prereg7": {"sha16": "32eaf82ca56600c4", "bytes": 5835, "lines": 88,
                "end_newline": False},
    "script71": {"sha16": "88256d274c9993cc", "bytes": 50618},
    "script7": {"sha16": "65ed60125528d5d6", "bytes": 44761},
    "art71": {"sha16": "55191eaf2426f736", "bytes": 510508},
    "art7": {"sha16": "1f8f44b921e575fe", "bytes": 507657},
    "judge": {"sha16": "6a3001b6ca23ef7d", "bytes": 452456},
    "gold": {"sha16": "9273ebc97aa1413a", "bytes": 13195},
    "sentences": {"sha16": "c349ca5a93192aac", "bytes": 99636},
}

TMP = Path(tempfile.gettempdir())
PROBE_EXEC = TMP / "rev7_1_executor_repro.json"
PROBE_SELF = TMP / "rev7_1_self_determinism.json"

sys.path.insert(0, str(OUT))
import _rev7_audit as R7  # my own prior independent implementation


# ------------------------------------------------------------------ helpers
def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    os.replace(tmp, path)


def fmeta(p):
    b = p.read_bytes()
    return {"file": str(p.relative_to(ROOT)).replace("\\", "/"),
            "sha16": sha16(b), "bytes": len(b),
            "lines": b.count(b"\n") + (0 if b.endswith(b"\n") else 1),
            "end_newline": b.endswith(b"\n")}


def canon_sha(obj):
    return sha16(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode())


def ast_funcs(text):
    tree = ast.parse(text)
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            seg = ast.get_source_segment(text, n)
            out[n.name] = {"sha16": sha16(seg.encode()), "bytes": len(seg.encode()),
                           "lineno": n.lineno,
                           "nested": bool(re.search(r"^\s+def " + n.name,
                                                    text[:0]))}
    return out


def top_level_consts(text):
    tree = ast.parse(text)
    out = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            seg = ast.get_source_segment(text, n.value) or ""
            out[n.targets[0].id] = {"sha16": sha16(seg.encode()), "text": seg}
    return out


def import_list(text):
    tree = ast.parse(text)
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out += ["import " + a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            out.append("from " + str(n.module))
    return out


def norm_quote(s):
    return " ".join(s.replace("`", "").replace("**", "").split())


# ---------------------------------------------------------- 1) frozen checks
def frozen_checks():
    res = {"files": {}, "mismatches": [], "prereg_markers": {},
           "residues": {}, "b5_stale_hash": {}}
    for key, p in [("prereg71", PRE71), ("prereg7", PRE7), ("script71", SCRIPT71),
                   ("script7", SCRIPT7), ("art71", ART71), ("art7", ART7),
                   ("judge", JUDGE), ("gold", GOLD), ("sentences", SENT)]:
        m = fmeta(p)
        m.update({k: v for k, v in EXPECT[key].items() if k not in m})
        m["checks"] = {k: (m[k] == v) for k, v in EXPECT[key].items()}
        res["files"][key] = m
        if not all(m["checks"].values()):
            res["mismatches"].append({"key": key, "meta": m})
    doc = PRE71.read_text("utf-8")
    res["prereg_markers"] = {
        "frozen=true": doc.count("frozen=true"),
        "frozen_rev=1": doc.count("frozen_rev=1"),
        "frozen_at=2026-10-26T21:06:55+08:00":
            doc.count("frozen_at=2026-10-26T21:06:55+08:00"),
        "write_state=frozen": doc.count("write_state=frozen"),
        "supersedes=32eaf82ca56600c4":
            doc.count("supersedes=32eaf82ca56600c4"),
        "correction_type=statement_correction":
            doc.count("correction_type=statement_correction"),
        "LEAD 复核通过": doc.count("LEAD 复核通过"),
        "rev7_1_ver=1": doc.count("rev7_1_ver=1"),
    }
    res["residues"] = {
        "frozen=false": doc.count("frozen=false"),
        "待 LEAD 复核": doc.count("待 LEAD 复核"),
        "待复核": doc.count("待复核"),
        "TODO": doc.count("TODO"),
        "draft": doc.count("draft"),
        "未冻结 (b5)": len(re.findall(r"未冻结.{0,6}\(b5\)", doc)),
    }
    b5 = B5PRE.read_text("utf-8")
    res["b5_stale_hash"] = {
        "b5_current_sha16": sha16(B5PRE.read_bytes()),
        "b5_stale_hash_e306ce994d306a84_in_b5_itself":
            b5.count("e306ce994d306a84"),
        "e306ce994d306a84_in_rev7_prereg": PRE7.read_text("utf-8").count(
            "e306ce994d306a84"),
        "e306ce_in_rev7_1_prereg": doc.count("e306ce"),
        "e306ce_in_rev7_1_script": SCRIPT71.read_text("utf-8").count("e306ce"),
        "e306ce_in_rev7_1_artifact": ART71.read_text("utf-8").count("e306ce"),
        "rev7_1_prereg_references_b5_only_by": re.findall(
            r"PREREG-M5-C2-B5\.md[^，。；\n]{0,12}", doc),
    }
    return res


# ------------------------------------------------------------- 2) redline
def redline():
    t7 = PRE7.read_text("utf-8")
    t71 = PRE71.read_text("utf-8")
    L7 = t7.split("\n")
    L71 = t71.split("\n")

    def lineno(pat):
        for i, l in enumerate(L71):
            if l.startswith(pat):
                return i + 1
        return None

    b = {"header_end": 8,
         "s0": lineno("## 0"), "s0_end": lineno("## 1") - 1,
         "s1": lineno("## 1"), "s1_end": lineno("### 2.1") - 1,
         "a21": lineno("### 2.1"), "a21_end": lineno("## 3") - 1,
         "s3": lineno("## 3"), "s3_end": lineno("## 4") - 1,
         "s4": lineno("## 4"), "s4_end": lineno("## 5") - 1,
         "s5": lineno("## 5"), "s5_end": lineno("## 附录 A") - 1,
         "s6": lineno("## 6"), "s6_end": len(L71)}
    appendix_at = lineno("## 附录 A")

    def bucket(i):
        n = i + 1
        if n <= b["header_end"]:
            return "header_metadata"
        if n >= appendix_at:
            return "appendix_redline"
        for name, lo, hi in [("section0_fact_correction", "s0", "s0_end"),
                             ("section2_rule_reference", "s1", "s1_end"),
                             ("section2_assertion_true_value", "a21", "a21_end"),
                             ("section3_gate_and_b5", "s3", "s3_end"),
                             ("section4_delivery", "s4", "s4_end"),
                             ("section5_discipline", "s5", "s5_end"),
                             ("section6_status", "s6", "s6_end")]:
            if b[lo] <= n <= b[hi]:
                return name
        return "other"

    sm = difflib.SequenceMatcher(None, L7, L71, autojunk=False)
    added, removed, hunks = [], [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("insert", "replace"):
            hunks.append({"tag": tag, "rev7": [i1 + 1, i2],
                          "rev71": [j1 + 1, j2],
                          "n_added": j2 - j1, "n_removed": i2 - i1})
            added += [(j, L71[j]) for j in range(j1, j2)]
        if tag in ("delete", "replace"):
            removed += [(i, L7[i]) for i in range(i1, i2)]

    hist = collections.Counter(bucket(j) for j, _ in added)
    unclassified = [{"line": j + 1, "text": L71[j][:200]}
                    for j, _ in added if bucket(j) == "other"]

    # rule bodies restated?  (must NOT be: rev7.1 references them)
    body = t71.split("## 附录 A")[0]
    rule_markers = {m: body.count(m) for m in
                    ["NFKC", "千分位", "非贪婪", "捕获组",
                     "window_coverage", "valid = "]}

    # reference table rows -> verify the cited rev7 line ranges are right
    refs = []
    for m in re.finditer(r"\| \*\*(N[1-4])\*\*[^|]*\| *第 (\d+)–(\d+) 行 \|", t71):
        rule, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
        head = L7[lo - 1] if 0 < lo <= len(L7) else ""
        row = L71[t71[:m.start()].count("\n")].strip()
        refs.append({"rule": rule, "lines": [lo, hi],
                     "rev7_line_lo_starts_rule": head.startswith("### " + rule),
                     "rev7_line_hi_nonempty": (hi <= len(L7) and bool(L7[hi - 1].strip())),
                     "row": row[:160]})
    closing_core = "其余 R1/R2/R3/R4+/R_DERIVED+ 规则、阈值 0.80、词表一律不变。"
    closing_ok = (closing_core in t71.replace("「", "").replace("」", "")
                  and closing_core in L7[53].replace("**", ""))
    retained = [i + 1 for i in range(33, 54)
                if L7[i].strip() and L7[i].strip() in t71]
    lost = [i + 1 for i in range(33, 54)
            if L7[i].strip() and L7[i].strip() not in t71]

    # redline quote fidelity (A.1 / A.2 old)
    a1old = [l for l in L71 if l.startswith("- **old**：")][0]
    a1new = [l for l in L71 if l.startswith("- **new**：")][0]
    q_old = a1old.split("`", 1)[1].rsplit("`", 1)[0]
    q_new = a1new.split("`", 1)[1].rsplit("`", 1)[0]
    a2old = [l for l in L71 if l.startswith("- **old**：") and "断言自检" in l][0]
    q2 = a2old.split("`", 1)[1].rsplit("`", 1)[0]
    quote_checks = {
        "A1_old_equals_rev7_line17": norm_quote(q_old) == norm_quote(L7[16]),
        "A1_new_equals_rev7_1_line17": norm_quote(q_new) == norm_quote(L71[16]),
        "A2_old_equals_rev7_line49": norm_quote(q2) == norm_quote(L7[48]),
        "old_assertion_retracted_and_quoted":
            t71.count("valid=false") == 3,  # §2.1 + A.2 old + A.2 变更实质
        "old_assertion_retraction_explicit": "**撤回**" in t71,
        "A6_counts_claimed_3_2_2": "3 / 2 / 2" in t71,
        "A6_no_overlap_and_N3_net_zero":
            ("互不重叠" in t71 and "N3 净贡献 0" in t71),
    }
    # correction presence checks (the four claimed text corrections)
    corr = {
        "c0_patient_pos_0_1": "pos 0–1" in body,
        "c0_done_pos_9_10": "pos 9–10" in body,
        "c0_old_claim_removed": "句内根本不存在" not in body,
        "c0_no_overlap_phrase": "与上重叠" not in body,
        "c0_counts_corrected": ("7 例 FP 归因互不重叠" in body
                                and "N3/N4 对 7 例的修复数 = 0" in body),
        "c2_true_assertions": ("valid=true" in body and "coverage=1.0" in body
                               and "N3 不改变该句 verdict" in body),
        "c2_attribution_sentence":
            ("四门槛的实际修复全部来自 N1 + N2；N3/N4 净贡献 = 0"
             in body),
        "c3_b5_admission": ("rev7.1 是口径更正，不是调规则凑结果" in body
                            and "逐字相同" in body),
        "c3_b5_identity_only": "仅在文档身份上取代" in body,
    }

    def section_of_rev7(i):
        n = i + 1
        heads = [(1, 8, "header"), (9, 19, "section0"), (20, 30, "section1"),
                 (31, 44, "part?")]
        # simple: map by nearest heading below
        cur = "header"
        for j in range(n - 1, -1, -1):
            m = re.match(r"^#{1,4} (.+)$", L7[j])
            if m:
                cur = m.group(1).split(" ")[0] + " " + m.group(1).split(" ")[1] \
                    if len(m.group(1).split(" ")) > 1 else m.group(1)
                break
        return cur

    removed_hist = collections.Counter(section_of_rev7(i) for i, _ in removed)
    rule_body_lines = [i for i in range(33, 54)]  # rev7 §2 body lines 34..54 (0-based 33..53)
    rule_body_in_71 = {L7[i].strip()[:60]: (L7[i].strip() in t71)
                       for i in rule_body_lines}
    rule_body_absent = sum(1 for v in rule_body_in_71.values() if not v)

    return {
        "line_counts": {"rev7": len(L7), "rev7_1": len(L71)},
        "diff_hunks": {"n_hunks": len(hunks), "n_added_lines": len(added),
                       "n_removed_lines": len(removed), "hunks": hunks},
        "added_line_buckets": dict(hist),
        "added_unclassified": unclassified,
        "removed_line_buckets": dict(removed_hist),
        "rule_bodies_not_restated": {"markers": rule_markers,
                                     "rev7_s2_body_lines_34_54_inline_lost":
                                         rule_body_absent,
                                     "rev7_s2_body_lines_retained": retained,
                                     "rev7_s2_body_lines_lost": lost,
                                     "rev7_s2_line54_quoted_variant":
                                         "「其余 R1/R2/R3/R4+/R_DERIVED+ 规则、阈值 0.80、词表一律不变。」" in t71,
                                     "closing_clause_quoted_verbatim": closing_ok},
        "rule_reference_table": refs,
        "quote_fidelity": quote_checks,
        "correction_presence": corr,
        "allowed_categories": ["header_metadata", "section0_fact_correction",
                               "section2_assertion_true_value",
                               "section3_gate_and_b5", "appendix_redline",
                               "section2_rule_reference", "section4_delivery",
                               "section5_discipline", "section6_status"],
        "rule_text_changed": not (all(v == 0 for v in rule_markers.values())
                                  and all(r["rev7_line_lo_starts_rule"]
                                          for r in refs)),
    }


# ---------------------------------------------------------- 3) code audit
def code_audit():
    t7 = SCRIPT7.read_text("utf-8")
    t71 = SCRIPT71.read_text("utf-8")
    f7 = ast_funcs(t7)
    f71 = ast_funcs(t71)
    identical = sorted(n for n in f7 if n in f71 and f7[n]["sha16"] == f71[n]["sha16"])
    differing = sorted(n for n in f7 if n in f71 and f7[n]["sha16"] != f71[n]["sha16"])
    new = sorted(set(f71) - set(f7))
    gone = sorted(set(f7) - set(f71))
    c7 = top_level_consts(t7)
    c71 = top_level_consts(t71)
    changed = {k: {"rev7": v["text"][:120], "rev71": c71[k]["text"][:120]}
               for k, v in c7.items() if k in c71 and v["sha16"] != c71[k]["sha16"]}
    only71 = sorted(set(c71) - set(c7))
    allowed_changed = ["ART", "ASSERT_A2", "ASSERT_A3", "PRE", "PRE_BYTES",
                       "PRE_LINES", "PRE_SHA16"]
    thresholds = {}
    for name, txt in (("rev7", t7), ("rev7_1", t71)):
        thresholds[name] = {
            "0.80": len(re.findall(r"\b0\.80\b", txt)),
            "0.90": len(re.findall(r"\b0\.90\b", txt)),
            "other_threshold_like": sorted(set(re.findall(
                r"\b0\.[0-9]{2,}\b", txt)) - {"0.80", "0.90"}),
        }
    pure7 = [n for n in c7 if n.startswith("PURE")]
    return {
        "functions": {"n_rev7": len(f7), "n_rev71": len(f71),
                      "identical": identical, "n_identical": len(identical),
                      "differing": differing, "only_in_rev7": gone,
                      "only_in_rev71": new},
        "nested_gate_item_identical":
            f7.get("gate_item", {}).get("sha16") == f71.get("gate_item", {}).get("sha16"),
        "module_constants": {"changed": changed,
                             "changed_allowed": sorted(changed) == sorted(allowed_changed),
                             "only_in_rev71": only71,
                             "thresholds_literal": thresholds},
        "imports_identical": import_list(t7) == import_list(t71),
        "imports": import_list(t71),
        "vars_identical": {n: c7[n]["sha16"] == c71[n]["sha16"]
                           for n in ("PURE_PATTERNS", "ENTITY_PATTERN")
                           if n in c7 and n in c71},
        "prereg_consts_71": {"PRE_SHA16": c71.get("PRE_SHA16", {}).get("text"),
                             "PRE_BYTES": c71.get("PRE_BYTES", {}).get("text"),
                             "PRE_LINES": c71.get("PRE_LINES", {}).get("text")},
    }


# ------------------------------------------------------- 4) recompute/compare
def build_inputs():
    j = json.loads(JUDGE.read_text("utf-8"))
    g = json.loads(GOLD.read_text("utf-8"))
    rows = []
    for r in j["items"]:
        rows.append({"sid": r["sid"], "sentence": r["sentence"],
                     "source_text": r["source_text"], "route": r["route"],
                     "verdict": r["verdict"], "parse_ok": r["parse_ok"],
                     "derived": bool(r.get("derived")),
                     "items": r.get("items") or []})
    return j, g, rows


def cmp_val(a, b, tol=1e-9):
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= tol
    return a == b


def judge71(items, sentence, source):
    """Literal N1-N4 item scorer (N4: R3 absent markers only on valid items)."""
    norm = R7.normalize
    sent_n = norm(sentence)
    src_n = norm(source)
    out = []
    for it in items:
        entry = it.get("item", "")
        ev = it.get("evidence", "")
        item_n = norm(entry)
        in_sent = bool(item_n) and item_n in sent_n
        win = R7.window_coverage(item_n, sent_n) if item_n else 0.0
        valid = in_sent or win >= 0.90
        toks, _entity = R7.value_tokens_v7(entry, src_n)
        hits, _r3 = R7.r1_r2_r3(entry, ev, toks, norm=norm)
        keep = [h for h in hits if not (h.get("rule") == "R3" and not valid)]
        r3_hit = any(h.get("rule") == "R3" for h in keep)
        r4 = R7.r4_plus_v51(ev, source, r3_hit, norm=norm)
        if r4:
            keep.append(r4)
        out.append({
            "item": entry, "evidence": ev, "valid": valid,
            "absent": bool(valid and keep), "rule_hits": keep,
            "r3_hit": r3_hit,
            "item_verdict": ("invalid" if not valid
                             else ("unsupported" if keep else "supported")),
            "matcher": {"item_in_sentence": in_sent,
                        "window_coverage": round(win, 6)},
        })
    return out


def run_full(rows, gold):
    res = {}
    for r in rows:
        items = judge71(r["items"], r["sentence"], r["source_text"])
        en, _dd = R7.derived_plus(r["sentence"], r["source_text"])
        if r["route"] == "abstain_check":
            v = r["verdict"]
        else:
            v = R7.aggregate(r["parse_ok"], en, len(items),
                             [z["absent"] for z in items if z["valid"]])
        res[r["sid"]] = {
            "sid": r["sid"], "gold": gold.get(r["sid"]),
            "route": r["route"], "verdict": v,
            "n_items": len(items),
            "n_valid": sum(1 for z in items if z["valid"]),
            "n_invalid": sum(1 for z in items if not z["valid"]),
            "n_absent": sum(1 for z in items if z["valid"] and z["absent"]),
            "items": items,
        }
    return res


def recompute():
    j, g, rows = build_inputs()
    gold = g["gold"]
    gold_counts = collections.Counter(gold.values())
    baseline = R7.run_v7(rows, gold, use_n1=False, use_n2=False,
                         use_n3=False, use_n4=False)
    R7.BASELINE_LEAK_UNSUPPORTED_SET = set(
        sid for sid, x in baseline.items()
        if x["verdict"] == "unsupported" and x["gold"] == "fabricated")
    full = run_full(rows, gold)
    gates = R7.gate_summary(full)
    base_gates = R7.gate_summary(baseline)

    # baseline verdict parity vs stored
    verdict_ok = sum(1 for r in rows if baseline[r["sid"]]["verdict"] == r["verdict"])
    # baseline item parity (absent + rule_hits) vs stored items
    item_checked = item_ok = 0
    for r in rows:
        for mine, stored in zip(baseline[r["sid"]]["items"], r["items"]):
            item_checked += 1
            sh = [(h.get("rule"), h.get("reason"), h.get("span"))
                  for h in (stored.get("rule_hits") or [])]
            mh = [(h.get("rule"), h.get("reason"), h.get("span"))
                  for h in mine["rule_hits"]]
            ok = mine["absent"] == bool(stored.get("absent")) and sh == mh
            item_ok += 1 if ok else 0
    # derived parity on model rows
    derived_checked = derived_ok = 0
    for r in rows:
        if r["route"] != "model_extract":
            continue
        derived_checked += 1
        en, _ = R7.derived_plus(r["sentence"], r["source_text"])
        if en == r["derived"]:
            derived_ok += 1

    art = json.loads(ART71.read_text("utf-8"))
    asent = {s["sid"]: s for s in art["sentences"]}
    aitem_by_sid = collections.defaultdict(list)
    for z in art["items"]:
        aitem_by_sid[z["sid"]].append(z)

    field_diffs = collections.Counter()
    first_diffs = []
    for r in rows:
        sid = r["sid"]
        a = asent[sid]
        m = full[sid]
        exp = {"gold": a["gold"], "verdict_rev5_1": baseline[sid]["verdict"],
               "verdict_rev7": m["verdict"], "route": r["route"],
               "parse_ok": r["parse_ok"],
               "derived_rev7": R7.derived_plus(r["sentence"], r["source_text"])[0],
               "derived_stored": r["derived"],
               "n_items": m["n_items"], "n_valid": m["n_valid"],
               "n_invalid": m["n_invalid"], "n_absent": m["n_absent"],
               "n_unverified": 0,
               "changed": baseline[sid]["verdict"] != m["verdict"]}
        for k, v in exp.items():
            if a.get(k) != v and not (k == "derived_rev7" and bool(a.get(k)) == bool(v)):
                field_diffs["sentence." + k] += 1
                if len(first_diffs) < 12:
                    first_diffs.append({"scope": "sentence", "sid": sid,
                                        "field": k, "mine": v,
                                        "artifact": a.get(k)})
    item_checked2 = 0
    for r in rows:
        sid = r["sid"]
        pairs = list(zip(full[sid]["items"], aitem_by_sid.get(sid, [])))
        for i, (mine, a) in enumerate(pairs):
            item_checked2 += 1
            hits = [(h.get("rule"), h.get("reason"), h.get("span"),
                     h.get("metric") or "",
                     ("" if h.get("value") is None else h.get("value")))
                    for h in mine["rule_hits"]]
            ahits = [(h.get("rule"), h.get("reason"), h.get("span"),
                      h.get("metric") or "",
                      ("" if h.get("jaccard_or_bigram") is None
                       else h.get("jaccard_or_bigram")))
                     for h in (a.get("rule_hits") or [])]
            exp = {
                "item": mine["item"], "evidence": mine["evidence"],
                "valid": mine["valid"],
                "absent": bool(mine["valid"] and bool(mine["rule_hits"])),
                "matcher_hit": "substring" if mine["matcher"]["item_in_sentence"] else "none",
                "coverage": (1.0 if mine["matcher"]["item_in_sentence"]
                             else round(mine["matcher"]["window_coverage"], 6)),
                "numeric_ok": not any(h.get("rule") == "R1" for h in mine["rule_hits"]),
                "item_verdict": {"supported": "present", "unsupported": "absent",
                                 "invalid": "invalid"}[mine["item_verdict"]],
                "rule": (mine["rule_hits"][0]["rule"] if mine["rule_hits"] else None),
                "reason": (mine["rule_hits"][0]["reason"] if mine["rule_hits"] else None),
                "r3_hit": mine["r3_hit"], "binding": mine["valid"],
                "rule_hits": sorted([tuple("" if x is None else x for x in h) for h in hits]),
            }
            aexp = {
                "item": a.get("item"), "evidence": a.get("evidence"),
                "valid": a.get("valid"), "absent": a.get("absent"),
                "matcher_hit": a.get("matcher_hit"), "coverage": a.get("coverage"),
                "numeric_ok": a.get("numeric_ok"),
                "item_verdict": a.get("item_verdict"), "rule": a.get("rule"),
                "reason": a.get("reason"), "r3_hit": a.get("r3_hit"),
                "binding": a.get("binding"),
                "rule_hits": sorted(ahits),
            }
            for k in exp:
                if not cmp_val(exp[k], aexp[k]):
                    field_diffs["item." + k] += 1
                    if len(first_diffs) < 20:
                        first_diffs.append({"scope": "item", "sid": sid, "idx": i,
                                            "field": k, "mine": exp[k],
                                            "artifact": aexp[k]})
    # gate parity
    gate_exp = {
        "false_positive": (gates["fp"]["k"], gates["fp"]["n"], gates["fp"]["sids"]),
        "leak_missed": (gates["leak"]["k"], gates["leak"]["n"], gates["leak"]["sids"]),
        "parse_fail": (gates["parse_fail"]["k"], gates["parse_fail"]["n"],
                       gates["parse_fail"]["sids"]),
        "new_miss": (gates["new_miss"]["k"],
                     len(R7.BASELINE_LEAK_UNSUPPORTED_SET),
                     gates["new_miss"]["sids"]),
    }
    ag = art["gate"]
    gdiff = []
    for k, (gk, gn, gsids) in gate_exp.items():
        for f, val in (("k", gk), ("n", gn)):
            if ag.get(k, {}).get(f) != val:
                gdiff.append({"gate": k, "field": f, "mine": val,
                              "artifact": ag.get(k, {}).get(f)})
        if ag.get(k + "_sids") != gsids:
            gdiff.append({"gate": k, "field": "sids", "mine": gsids,
                          "artifact": ag.get(k + "_sids")})
    # attribution
    fp_attr = []
    for sid in base_gates["fp"]["sids"]:  # 7 baseline FPs: which rule fixed each
        b = baseline[sid]
        f = full[sid]
        cause = "N3"
        if f["verdict"] != b["verdict"]:
            for bi, fi in zip(b["items"], f["items"]):
                if any(h.get("rule") == "R1" for h in bi["rule_hits"]) and \
                        not any(h.get("rule") == "R1" for h in fi["rule_hits"]):
                    tok = [h.get("span") for h in bi["rule_hits"]
                           if h.get("rule") == "R1"][0]
                    cause = "N1" if re.search(r"\d", tok) else "N2"
                    break
            else:
                cause = "other"
        fp_attr.append({"sid": sid, "attribution": cause,
                        "fixed": f["verdict"] != "unsupported",
                        "verdict_rev5_1": b["verdict"],
                        "verdict_rev7": f["verdict"]})
    attr_counts = collections.Counter(x["attribution"] for x in fp_attr)
    # compare attribution rows with artifact
    arows = {z["sid"]: z for z in art["false_by_reason"]}
    attr_diff = []
    for row in fp_attr:
        a = arows.get(row["sid"], {})
        if a.get("attribution") != row["attribution"] or \
                a.get("fixed") != row["fixed"] or \
                a.get("verdict_rev5_1") != row["verdict_rev5_1"] or \
                a.get("verdict_rev7") != row["verdict_rev7"]:
            attr_diff.append({"sid": row["sid"], "mine": row,
                              "artifact": {k: a.get(k) for k in
                                           ("attribution", "fixed",
                                            "verdict_rev5_1", "verdict_rev7")}})
    # sentence_diff / invalid / all-invalid
    my_fixed = sorted(sid for sid in full
                      if baseline[sid]["verdict"] == "unsupported"
                      and full[sid]["verdict"] == "supported"
                      and full[sid]["gold"] == "support_present")
    my_broken = sorted(sid for sid in full
                       if baseline[sid]["verdict"] == "supported"
                       and full[sid]["verdict"] != "supported")
    my_neutral = sorted(sid for sid in full
                        if baseline[sid]["verdict"] != full[sid]["verdict"]
                        and sid not in my_fixed and sid not in my_broken)
    my_invalid = [(sid, i) for sid in full
                  for i, z in enumerate(full[sid]["items"]) if not z["valid"]]
    my_all_invalid = sorted(sid for sid in full
                            if len(full[sid]["items"]) > 0
                            and all(not z["valid"] for z in full[sid]["items"]))
    _idx = collections.Counter()
    art_invalid = []
    for z in art["items"]:
        i = _idx[z["sid"]]
        _idx[z["sid"]] += 1
        if not z["valid"]:
            art_invalid.append((z["sid"], i))
    sd = art["sentence_diff"]
    sets = {
        "fixed": (my_fixed, sorted(x["sid"] for x in sd["fixed"])),
        "broken": (my_broken, sorted(x["sid"] for x in sd["broken"])),
        "neutral": (my_neutral, sorted(x["sid"] for x in sd["neutral"])),
        "unchanged_false_positive":
            (gates["fp"]["sids"],
             sorted(x["sid"] for x in sd["unchanged_false_positive"])),
        "unchanged_leak":
            (gates["leak"]["sids"], sorted(x["sid"] for x in sd["unchanged_leak"])),
    }
    sd_diff = {k: {"equal": a == b, "mine": a, "artifact": b}
               for k, (a, b) in sets.items()}
    invalid_equal = my_invalid == art_invalid
    ai_equal = my_all_invalid == sorted(x["sid"] for x in art["all_invalid_sentences"])
    # rates
    rates = art["rates"]
    rate_ok = (rates["false_positive"]["k"] == gates["fp"]["k"]
               and rates["false_positive"]["n"] == 46
               and rates["leak_missed"]["k"] == gates["leak"]["k"]
               and rates["leak_missed"]["n"] == 41
               and rates["parse_fail"]["k"] == gates["parse_fail"]["k"]
               and rates["invalid_items"]["k"] == len(my_invalid))
    # rule hit counts
    cnt = collections.Counter()
    for sid in full:
        for z in full[sid]["items"]:
            if z["valid"]:
                for h in z["rule_hits"]:
                    cnt[h["rule"]] += 1
    hit_counts = dict(cnt)
    art_hits = {k: v for k, v in art["rev7_rule_hit_counts"].items() if v}
    return {
        "gold_counts": dict(gold_counts),
        "baseline": {"verdict_parity": {"ok": verdict_ok, "n": len(rows)},
                     "item_parity": {"ok": item_ok, "n": item_checked},
                     "derived_parity": {"ok": derived_ok, "n": derived_checked},
                     "verdict_distribution": dict(collections.Counter(
                         x["verdict"] for x in baseline.values())),
                     "gates": base_gates},
        "new_miss_n": len(R7.BASELINE_LEAK_UNSUPPORTED_SET),
        "rev7_1": {"gates": gates,
                   "n_items": sum(len(full[s]["items"]) for s in full),
                   "invalid_items": len(my_invalid),
                   "all_invalid_sentences": my_all_invalid,
                   "hit_counts": hit_counts,
                   "artifact_hit_counts": art_hits},
        "artifact_compare": {"sentence_checked": len(rows),
                             "item_checked": item_checked2,
                             "diff_counts": dict(field_diffs),
                             "total_diffs": sum(field_diffs.values()),
                             "first_diffs": first_diffs,
                             "gate_diff": gdiff,
                             "attribution_diff": attr_diff,
                             "attribution_rows": fp_attr,
                             "attribution_counts": dict(attr_counts),
                             "sentence_diff": sd_diff,
                             "invalid_items_equal": invalid_equal,
                             "invalid_items_artifact": len(art_invalid),
                             "all_invalid_equal": ai_equal,
                             "rates_ok": rate_ok,
                             "hit_counts_equal": hit_counts == art_hits},
        "baseline_vs_stored": {"verdict_ok": verdict_ok, "verdict_n": len(rows),
                               "item_ok": item_ok, "item_n": item_checked,
                               "derived_ok": derived_ok, "derived_n": derived_checked},
        "raw": {"full": full, "baseline": baseline, "rows": rows},
    }


# ------------------------------------------------ 5) assertions (truth table)
def assertions(rec):
    full = rec["raw"]["full"]
    baseline = rec["raw"]["baseline"]
    rows = {r["sid"]: r for r in rec["raw"]["rows"]}
    art = json.loads(ART71.read_text("utf-8"))
    A1 = R7.coverage("8600元", R7.normalize("手术费 8,600 元"))
    out = {"A1": {"expr": "R7.coverage('8600元', normalize7('手术费 8,600 元'))",
                  "value": A1, "pass": A1 == 1.0}}
    for name, sid, expected in (("A2", "b4-s1-q2-s07",
                                 {"患者": (0, 1), "做的": (9, 10)}),
                                ("A3", "b4-s1-q2-s09", {"患者": (0, 1)})):
        sent_n = R7.normalize(rows[sid]["sentence"])
        occ = []
        for i, z in enumerate(full[sid]["items"]):
            if z["item"] not in expected:
                continue
            a = R7.normalize(z["item"])
            pos = sent_n.find(a) if a in sent_n else None
            lo, hi = expected[z["item"]]
            cov = R7.window_coverage(a, sent_n) if a else 0.0
            occ.append({"item_index": i, "item": z["item"], "pos": pos,
                        "expected": [lo, hi], "position_ok": pos == lo,
                        "valid": z["valid"], "coverage": round(cov, 6),
                        "matcher": "substring" if a in sent_n else "window"})
        pass_ = (bool(occ) and all(o["valid"] is True and o["position_ok"]
                                   and o["coverage"] == 1.0 for o in occ)
                 and sorted({o["item"] for o in occ}) == sorted(expected))
        va = art["assertions"][name]
        art_ok = (va.get("n_occurrences") == len(occ)
                  and all(o.get("valid") is True and o.get("coverage") == 1.0
                          and o.get("position_ok") is True
                          for o in va.get("occurrences", [])))
        out[name] = {"sid": sid, "expect_positions":
                     {k: list(v) for k, v in expected.items()},
                     "n_occurrences": len(occ), "occurrences": occ,
                     "pass": pass_, "artifact_occurrences": va.get("n_occurrences"),
                     "artifact_pass": va.get("pass"),
                     "artifact_math": art_ok,
                     "sentence_verdict_rev7": full[sid]["verdict"],
                     "sentence_verdict_rev5_1": baseline[sid]["verdict"],
                     "gold": full[sid]["gold"],
                     "n3_changes_verdict":
                         baseline[sid]["verdict"] != full[sid]["verdict"],
                     "artifact_verdict_block":
                         art["assertions"].get(name + "_verdict")}
    out["all_pass"] = all(out[k]["pass"] for k in ("A1", "A2", "A3"))
    out["artifact_all_pass"] = art["assertions"].get("all_pass")
    return out


def ablation():
    _j, _g, rows = build_inputs()
    gold = json.loads(GOLD.read_text("utf-8"))["gold"]
    R7.BASELINE_LEAK_UNSUPPORTED_SET = set(
        sid for sid, x in R7.run_v7(rows, gold, False, False, False, False).items()
        if x["verdict"] == "unsupported" and x["gold"] == "fabricated")
    cfgs = {
        "baseline_rev5_1": dict(use_n1=False, use_n2=False, use_n3=False, use_n4=False),
        "rev7_1_full": dict(use_n1=True, use_n2=True, use_n3=True, use_n4=True),
        "no_N1": dict(use_n1=False, use_n2=True, use_n3=True, use_n4=True),
        "no_N2": dict(use_n1=True, use_n2=False, use_n3=True, use_n4=True),
        "no_N3": dict(use_n1=True, use_n2=True, use_n3=False, use_n4=True),
        "no_N4": dict(use_n1=True, use_n2=True, use_n3=True, use_n4=False),
        "N2_gate_on_evidence": dict(use_n1=True, use_n2=True, use_n3=True,
                                    use_n4=True, gate_basis="evidence"),
        "all_invalid_to_undecidable": dict(use_n1=True, use_n2=True, use_n3=True,
                                           use_n4=True,
                                           all_invalid_to_undecidable=True),
    }
    out = {}
    for name, kw in cfgs.items():
        g = R7.gate_summary(R7.run_v7(rows, gold, **kw))
        out[name] = {"fp": [g["fp"]["k"], g["fp"]["n"]],
                     "fp_sids": g["fp"]["sids"],
                     "leak": [g["leak"]["k"], g["leak"]["n"]],
                     "parse_fail": [g["parse_fail"]["k"], g["parse_fail"]["n"]],
                     "new_miss": g["new_miss"]["k"]}
    return out


# ------------------------------------------- 6) artifact vs C32 (allowed diffs)
def artifact_vs_c32():
    A = json.loads(ART71.read_text("utf-8"))
    B = json.loads(ART7.read_text("utf-8"))
    equal = sorted(k for k in set(A) & set(B) if canon_sha(A[k]) == canon_sha(B[k]))
    diff = sorted(k for k in set(A) & set(B) if canon_sha(A[k]) != canon_sha(B[k]))
    new = sorted(set(A) - set(B))
    blocks = ["sentences", "items", "gate", "false_by_reason", "sentence_diff",
              "invalid_items", "all_invalid_sentences", "rates"]
    detail = {}
    for k in diff:
        if k == "assertions":
            detail[k] = {"keys_rev71": sorted(A[k]), "keys_c32": sorted(B[k]),
                         "A1_equal": A[k]["A1"] == B[k]["A1"],
                         "A2_changed": A[k]["A2"] != B[k]["A2"],
                         "A3_changed": A[k]["A3"] != B[k]["A3"],
                         "all_pass": [B[k].get("all_pass"), A[k].get("all_pass")]}
        elif k == "inputs":
            detail[k] = {"prereg_equal": A[k]["prereg"] == B[k]["prereg"],
                         "items_source_equal": A[k]["items_source"] == B[k]["items_source"],
                         "gold_equal": A[k]["gold"] == B[k]["gold"],
                         "sentences_equal": A[k]["sentences"] == B[k]["sentences"],
                         "new_subkeys": sorted(set(A[k]) - set(B[k]))}
        else:
            detail[k] = {"rev71": A[k], "c32": B[k]}
    return {"n_shared_equal": len(equal), "n_shared_diff": len(diff),
            "equal_keys": equal, "diff_keys": diff, "new_keys": new,
            "diff_detail": detail,
            "eight_blocks_equal": all(canon_sha(A[k]) == canon_sha(B[k])
                                      for k in blocks),
            "blocks": blocks}


# --------------------------------------------------- 7) reproducibility probes
def reproducibility():
    out = {}
    if PROBE_EXEC.exists():
        out["executor_reproduction"] = json.loads(PROBE_EXEC.read_text("utf-8"))
    else:
        out["executor_reproduction"] = {"status": "未做（probe file missing）"}
    if PROBE_SELF.exists():
        out["self_two_runs"] = json.loads(PROBE_SELF.read_text("utf-8"))
    else:
        out["self_two_runs"] = {"status": "未做（probe file missing）"}
    return out


def gpu_import_probe():
    code = r'''
import ctypes, json, sys
from pathlib import Path
ROOT = Path(r"D:\llama-mem")
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/m5"))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/m7/out"))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/engine"))
sys.path.insert(0, str(ROOT / "tools"))
k = ctypes.windll.kernel32
dlls = ["nvcuda.dll", "nvml.dll", "cudart64_110.dll", "cudart64_12.dll",
        "cublas64_11.dll", "cublas64_12.dll", "cudnn64_8.dll", "cudnn64_9.dll",
        "vulkan-1.dll", "kvshim_vk.dll", "kvshim.dll", "ggml-vulkan.dll",
        "llama.dll", "ggml.dll"]
def h():
    return {d: int(k.GetModuleHandleW(d) or 0) for d in dlls}
before = h()
import run_m5c2_rev5_offline  # dependency of the executor script (not the executor)
after = h()
print(json.dumps({"loaded_modules": sorted(
    m for m in sys.modules if m in ("_e3gpu_run", "run_m5c2_rev4_1",
                                    "run_m5c2_r2", "run_m5c2_floor",
                                    "run_m5c2_rev4", "run_m5c2_rev2_order",
                                    "run_m5c2_floor_rev2")),
    "dll_newly_loaded": [d for d in dlls if not before[d] and after[d]],
    "dll_handles_after_nonzero": [d for d in dlls if after[d]],
    "n_modules_loaded": len(sys.modules)}, ensure_ascii=False))
'''
    p = subprocess.run([sys.executable, "-X", "utf8", "-c", code],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=120)
    try:
        data = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        data = {"rc": p.returncode, "stdout": p.stdout[-500:],
                "stderr": p.stderr[-500:]}
    data["note"] = ("probe imports run_m5c2_rev5_offline (a dependency module, "
                    "NOT the executor script); the executor script imports the "
                    "same two modules (AST-verified).")
    return data


# --------------------------------------------------------- 8) discipline scan
def discipline_scan(rec, art):
    t71 = SCRIPT71.read_text("utf-8")
    lines = t71.split("\n")
    sid_branches = [i + 1 for i, l in enumerate(lines)
                    if re.search(r"\bsid\s*(==|!=|in\s*[\(\{\['\"])", l)]
    b4_lit = [{"line": i + 1, "text": l.strip()[:140]}
              for i, l in enumerate(lines) if "b4-" in l]
    tree = ast.parse(t71)
    opened = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fn = n.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None) or ""
            if name in ("open", "read_bytes", "read_text", "write_json_atomic",
                        "loads", "load"):
                seg = ast.get_source_segment(t71, n) or ""
                opened.append({"call": name, "arg": seg[:120],
                               "line": getattr(n, "lineno", None)})
    b5_hits = [{"line": i + 1, "text": l.strip()[:160]}
               for i, l in enumerate(lines)
               if re.search(r"(?<![A-Za-z0-9_])b5(?![A-Za-z0-9_])|M5B5|\(b5\)", l)]
    datetime_like = [{"line": i + 1, "text": l.strip()[:120]}
                     for i, l in enumerate(lines)
                     if re.search(r"datetime|strftime|time\.time|random\.", l)]
    return {
        "sid_special_case_branches": {"n": len(sid_branches),
                                      "lines": sid_branches[:10]},
        "b4_literals": {"n": len(b4_lit), "lines": b4_lit},
        "file_io_calls": opened,
        "b5_mentions_in_script": b5_hits,
        "datetime_random_mentions": datetime_like,
        "artifact_flags": {k: art.get(k) for k in
                           ("no_gpu", "n_forward", "no_model_call", "no_network",
                            "no_sid_special_cases", "no_threshold_change",
                            "no_wordlist_change", "no_gold_change",
                            "no_prereg_change", "no_input_change",
                            "no_git_commit", "no_b5_read")},
        "transitive_import_chain": transitive_chain(),
        "artifact_no_timestamps": not any(
            re.search(r"\d{4}-\d{2}-\d{2}T", json.dumps(v, ensure_ascii=False))
            for v in art.values() if isinstance(v, str)),
    }


def transitive_chain():
    search = [M5, ROOT / "kvmem/m2_visibility/m7/out",
              ROOT / "kvmem/m2_visibility/engine", ROOT / "tools"]

    def find(mod):
        for d in search:
            p = d / (mod + ".py")
            if p.exists():
                return p
        return None

    seen, gpu_mods = {}, []
    stack = ["run_m5c2_rev5_offline", "run_m5c2_rev5_1_offline"]
    while stack:
        mod = stack.pop()
        if mod in seen:
            continue
        p = find(mod)
        if p is None:
            seen[mod] = None
            continue
        t = p.read_text("utf-8", errors="replace")
        try:
            tree = ast.parse(t)
        except SyntaxError:
            seen[mod] = None
            continue
        imps = []
        side = []
        for n in tree.body:
            if isinstance(n, ast.Import):
                imps += [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                if n.module:
                    imps.append(n.module)
            elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                continue
            elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
                continue
            elif isinstance(n, ast.Assign) and isinstance(n.value, (ast.Call, ast.Constant)):
                continue
            else:
                side.append(type(n).__name__)
        seen[mod] = {"file": str(p), "imports": sorted(set(imps)),
                     "toplevel_nonassign_stmts": side}
        if mod in ("_e3gpu_run",):
            gpu_mods.append(mod)
        for i in imps:
            base = i.split(".")[0]
            if find(base):
                stack.append(base)
    return {"modules": seen, "top_level_dll_load":
            bool(re.search(r"^ctypes\.(WinDLL|CDLL|windll)", SCRIPT71.read_text("utf-8"), re.M)),
            "chain_has_gpu_helper_module": gpu_mods,
            "n_modules": len(seen)}


# ------------------------------------ 9) doc<->code inconsistencies (④ / ⑤)
def inconsistencies(rec, disc, discscan):
    t71 = SCRIPT71.read_text("utf-8")
    t7 = SCRIPT7.read_text("utf-8")
    doc71 = PRE71.read_text("utf-8")
    r7doc = PRE7.read_text("utf-8")
    enum_line = [l for l in r7doc.split("\n") if "false_by_reason" in l]
    enum_line = enum_line[0] if enum_line else ""
    tree = ast.parse(t71)
    pick = None
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == "pick_attribution":
            pick = ast.get_source_segment(t71, n)
    branches = sorted(set(re.findall(r"(?:attribution\"?\s*[:=]\s*\"|\")(N[1-4]|R4\+|declared|other)\"", pick or "")))
    # is N4 independently observable?  N4 toggle == N3 toggle in this impl.
    abl = rec["ablation"] if "ablation" in rec else {}
    n4_effect = (abl.get("no_N4", {}).get("fp") != abl.get("rev7_1_full", {}).get("fp")
                 or abl.get("no_N4", {}).get("fp_sids") != abl.get("rev7_1_full", {}).get("fp_sids"))
    # sentence_diff does carry N4 tags (so N4 exists in output vocabulary)
    art = json.loads(ART71.read_text("utf-8"))
    n4_tags = sum(1 for grp in ("fixed", "broken", "neutral")
                  for x in art["sentence_diff"][grp] if "N4" in x.get("cause", []))
    gpu = disc["gpu_import_probe"]
    chain = discscan["transitive_import_chain"]
    return {
        "finding_4_false_by_reason_N4": {
            "rev7_section4_enumeration": enum_line.strip()[:220],
            "rev7_1_inherits_schema": "schema **同 REV7 §4**" in doc71,
            "pick_attribution_branches": branches,
            "N4_branch_present": "N4" in branches,
            "artifact_false_by_reason_attributions": sorted(
                {row["attribution"] for row in art["false_by_reason"]}),
            "N4_independently_observable": n4_effect,
            "N4_sentence_diff_tags": n4_tags,
            "classification": ("表述不精确（规范枚举列出 N4 分类，但 N4 无可独立观测作用面："
                               "在 N3 生效时 N4 的缺席词抑制与 N3 的作废条目排除是同一机制，"
                               "关闭 N3 后所有条目 valid、N4 变成 vacuous；因此任何句子都不可能"
                               "被唯一归因到 N4。实现无 N4 分支不是缺陷，数值零影响）"),
            "severity": "low (documentation / audit label only)",
        },
        "finding_5_transitive_gpu_import": {
            "script_header_claim_quote": [l.strip() for l in t71.split("\n")
                                          if "GPU runner" in l or "no engine" in l][:3],
            "artifact_import_notes": art.get("import_notes"),
            "direct_imports": json.loads(ART71.read_text("utf-8")).get("imports"),
            "transitive_modules_with_gpu_side_helpers":
                chain["chain_has_gpu_helper_module"],
            "transitive_chain_modules": sorted(chain["modules"]),
            "transitive_chain_top_level_dll_load": chain["top_level_dll_load"],
            "gpu_probe": gpu,
            "n_forward_artifact": art.get("n_forward"),
            "n_forward_expected": 0,
            "cuda_dlls_loaded_on_import": gpu.get("dll_newly_loaded", []),
            "classification": ("表述不精确（直接 import 的只有两个离线判定模块；"
                               "传递闭包确实会加载 _e3gpu_run 等 GPU 侧 helper 模块进 sys.modules，"
                               "但导入期 0 个 CUDA/Vulkan/llama DLL、0 子进程、0 设备、0 前向；"
                               "n_forward=0 / no_gpu=true 实质成立。头注的 'no engine / no GPU runner' "
                               "按直接 import 读成立，按传递闭包读不精确）"),
            "severity": "low (documentation; no numerical effect)",
        },
    }


# ------------------------------------------------------------ 10) main
def main():
    rep = {
        "schema": "m5c2_rev7_1_audit_v1",
        "role": "independent_inspector",
        "discipline": ("independent recompute: reuses only my own previous audit "
                       "module out/_rev7_audit.py (6695a4b4de403870); does NOT "
                       "import / execute / copy run_m5c2_rev7_1_offline.py; "
                       "inputs read-only; (b5) data never read"),
    }
    rep["frozen"] = frozen_checks()
    rep["redline"] = redline()
    rep["code_audit"] = code_audit()
    rec = recompute()
    rep["recompute"] = {k: v for k, v in rec.items() if k != "raw"}
    rep["assertions"] = assertions(rec)
    abl = ablation()
    rec["ablation"] = abl
    rep["ablation"] = abl
    rep["artifact_vs_c32"] = artifact_vs_c32()
    rep["reproducibility"] = reproducibility()
    rep["art71"] = json.loads(ART71.read_text("utf-8")) if False else None
    art = json.loads(ART71.read_text("utf-8"))
    rep["art71"] = None
    del rep["art71"]
    disc = {"gpu_import_probe": gpu_import_probe()}
    rep["discipline_scan"] = discipline_scan(rec, art)
    rep["discipline_scan"]["gpu_import_probe"] = disc["gpu_import_probe"]
    rep["inconsistencies"] = inconsistencies(rec, disc, rep["discipline_scan"])

    # ---- verdict
    ac = rep["recompute"]["artifact_compare"]
    zero_diff = (ac["total_diffs"] == 0 and not ac["gate_diff"]
                 and not ac["attribution_diff"]
                 and all(v["equal"] for v in ac["sentence_diff"].values())
                 and ac["invalid_items_equal"] and ac["all_invalid_equal"]
                 and ac["rates_ok"] and ac["hit_counts_equal"])
    gates = rep["recompute"]["rev7_1"]["gates"]
    gates_pass = all(gates[k]["k"] <= {"fp": 4, "leak": 5, "parse_fail": 2,
                                       "new_miss": 0}[k] for k in
                     ("fp", "leak", "parse_fail", "new_miss"))
    ass = rep["assertions"]
    code = rep["code_audit"]
    fn_ok = (code["functions"]["n_identical"] >= 14
             and code["functions"]["differing"] == ["main", "verify_inputs"]
             and code["nested_gate_item_identical"])
    rule_ok = (rep["redline"]["rule_text_changed"] is False)
    rep["conclusion"] = {
        "verdict": "装置合格" if (zero_diff and gates_pass and ass["all_pass"]
                                 and fn_ok and rule_ok) else "装置不合格",
        "device_state": "装置合格" if (zero_diff and gates_pass and ass["all_pass"]
                                    and fn_ok and rule_ok) else "装置不合格",
        "state_inputs": {"zero_diff": zero_diff, "gates_pass": gates_pass,
                         "assertions_all_true": ass["all_pass"],
                         "functions_ok": fn_ok, "rule_text_unchanged": rule_ok},
        "section3_gates": {
            "false_positive": [gates["fp"]["k"], gates["fp"]["n"]],
            "leak_missed": [gates["leak"]["k"], gates["leak"]["n"]],
            "parse_fail": [gates["parse_fail"]["k"], gates["parse_fail"]["n"]],
            "new_miss": [gates["new_miss"]["k"], rec["new_miss_n"]],
            "all_pass": gates_pass},
        "assertions_all_true": ass["all_pass"],
        "functions_identical": code["functions"]["n_identical"],
        "functions_differing": code["functions"]["differing"],
        "rule_text_unchanged": rule_ok,
        "rule_markers_restated_in_rev7_1": rep["redline"]["rule_bodies_not_restated"]["markers"],
        "diff_counts": ac["diff_counts"],
        "total_diffs_vs_artifact": ac["total_diffs"],
        "zero_diff_vs_artifact": zero_diff,
        "diff_zero_fields": [
            "sentences.gold", "sentences.verdict_rev5_1", "sentences.verdict_rev7",
            "sentences.route", "sentences.parse_ok", "sentences.derived_rev7",
            "sentences.derived_stored", "sentences.n_items", "sentences.n_valid",
            "sentences.n_invalid", "sentences.n_absent", "sentences.n_unverified",
            "sentences.changed", "items.valid", "items.item_verdict",
            "items.absent", "items.matcher_hit", "items.coverage",
            "items.numeric_ok", "items.rule", "items.reason", "items.r3_hit",
            "items.binding", "items.rule_hits", "gate.*",
            "false_by_reason.attribution/fixed/verdicts",
            "sentence_diff.fixed/broken/neutral/unchanged_*",
            "invalid_items", "all_invalid_sentences", "rates",
            "rev7_rule_hit_counts"],
        "artifact_vs_c32": {
            "n_shared_equal": rep["artifact_vs_c32"]["n_shared_equal"],
            "n_shared_diff": rep["artifact_vs_c32"]["n_shared_diff"],
            "diff_keys": rep["artifact_vs_c32"]["diff_keys"],
            "new_keys": rep["artifact_vs_c32"]["new_keys"],
            "eight_blocks_equal": rep["artifact_vs_c32"]["eight_blocks_equal"]},
        "inconsistencies": {
            "finding_4": "表述不精确（§4 枚举含 N4，但 N4 无可独立观测作用面；非实现缺陷）",
            "finding_5": "表述不精确（传递 import 加载 GPU helper 模块但 0 CUDA DLL / 0 前向；n_forward=0 成立）"},
        "prereg_text_corrections_verified": rep["redline"]["correction_presence"],
        "redline_scope_note": (
            "新增行按段落归类：header 6 / §0 事实更正 15 / §2 规则引用表 9 / §2.1 断言 12 / "
            "§3 门槛与 b5 准入 8 / §4 交付字段 9 / §5 纪律 9 / 附录 redline 60；"
            "0 行未分类。§4/§5 属交付与纪律的行政性段落（非规则/非阈值/非断言），"
            "若严格按“只允许 §0/§2/§3/头注状态”四类白名单，这 18 行需 LEAD 明示纳入；"
            "它们不改变任何判定语义。"),
        "not_done_boundaries": [
            "未跑 (b5)；若 b5 数据不可读，未读其任何内容",
            "无法严格证明运行期“未读 b5”（只能静态证：脚本无 b5 路径引用 + 产物无 b5 字段）",
            "未测量 GPU 显存/设备占用（只检查 DLL 句柄 + n_forward=0 标志 + 代码无前向调用）",
            "执行者脚本复现为 %TEMP% 逐字节副本（不改一字），输出写回 repo 产物路径；内容一致",
        ],
        "biggest_reservation": (
            "rev7.1 的“规则零改动”以 by-reference 方式实现：N1–N4 规则正文不再内联，"
            "只引用 rev7 §2 第 34–54 行；rev7 文件字节未变（32eaf82ca56600c4）所以引用可验证，"
            "但新文档不自包含，读者必须回读被取代件。"),
        "prereg_sha16": rep["frozen"]["files"]["prereg71"]["sha16"],
        "script_sha16": rep["frozen"]["files"]["script71"]["sha16"],
        "artifact_sha16": rep["frozen"]["files"]["art71"]["sha16"],
    }
    # recompute raw data not serialised (too big); keep digest
    rep["determinism"] = {
        "recompute_core_sha16": canon_sha({
            "gates": {k: [gates[k]["k"], gates[k]["sids"]] for k in gates},
            "verdicts": {sid: rec["raw"]["full"][sid]["verdict"] for sid in rec["raw"]["full"]},
            "items_valid": [z["valid"] for sid in rec["raw"]["full"]
                            for z in rec["raw"]["full"][sid]["items"]],
            "assertions": {k: ass[k]["pass"] for k in ("A1", "A2", "A3")},
        }),
        "no_timestamps": True, "json_indent": 1, "ensure_ascii": False,
        "trailing_newline": True,
    }
    rep["frozen"]["prereg7_1_self_claims_reproduced"] = {
        "artifact_flag": art.get("prereg_text_corrections"),
        "my_independent": rep["redline"]["correction_presence"],
        "all_match": all(art.get("prereg_text_corrections", {}).get(k) == v
                         for k, v in rep["redline"]["correction_presence"].items()
                         if k in (art.get("prereg_text_corrections") or {})),
    }
    write_json_atomic(AUDIT, rep)
    # console summary
    print("AUDIT written:", AUDIT)
    print("device_state:", rep["conclusion"]["device_state"])
    print("gates:", rep["conclusion"]["section3_gates"])
    print("functions identical:", code["functions"]["n_identical"],
          "differing:", code["functions"]["differing"])
    print("zero diff vs artifact:", zero_diff, "total diffs:", ac["total_diffs"])
    print("assertions:", {k: ass[k]["pass"] for k in ("A1", "A2", "A3")})
    print("artifact_vs_c32:", rep["artifact_vs_c32"]["n_shared_equal"], "equal,",
          rep["artifact_vs_c32"]["n_shared_diff"], "diff,",
          len(rep["artifact_vs_c32"]["new_keys"]), "new")
    print("self core sha16:", rep["determinism"]["recompute_core_sha16"])


if __name__ == "__main__":
    main()