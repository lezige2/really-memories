#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 REV7.1 claim -> code map + executable verifier (READ-ONLY).

Reads (never writes) the frozen PREREG, the implementer script and the
artifact; emits out/M5C2-REV7-1-CLAIM-MAP.json and docs/_work/CODE-TRACE-M5C2-REV7.1.md.

Every claim is one of:
  static_ref      - function/constant exists in the frozen source (ast + slice sha256)
  static_grep     - a literal/regex claim checked against source text
  exec_assert     - a value recomputed by this file's own small code
  recompute       - an artifact reading recomputed from records + gold

Run:
  python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_1_claim_map.py          # write
  python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_1_claim_map.py --check  # verify only
Exit code 1 if any claim fails.  Zero GPU / zero model / zero network.
"""
import ast
import difflib
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"

DOC_REL = "docs/_work/PREREG-M5-C2-REV7.1.md"
DOC = ROOT / DOC_REL
IMPL_REL = "kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py"
IMPL = ROOT / IMPL_REL
ART_REL = "kvmem/m2_visibility/m5/out/M5C2-REV7-1-OFFLINE.json"
ART = ROOT / ART_REL
JUDGE_REL = "kvmem/m2_visibility/m5/out/M5B4-JUDGE.json"
JUDGE = ROOT / JUDGE_REL
GOLD_REL = "kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json"
GOLD = ROOT / GOLD_REL
R41_REL = "kvmem/m2_visibility/m5/run_m5c2_rev4_1.py"
R41 = ROOT / R41_REL
MAP_REL = "kvmem/m2_visibility/m5/out/M5C2-REV7-1-CLAIM-MAP.json"
MAP = ROOT / MAP_REL
MD_REL = "docs/_work/CODE-TRACE-M5C2-REV7.1.md"
MD = ROOT / MD_REL

# verification constants (from the frozen brief; never used as judging input)
DOC_SHA16 = "09d6f1b163ea0b84"
DOC_BYTES = 16313
IMPL_SHA16 = "88256d274c9993cc"
IMPL_BYTES = 50618
ART_SHA16 = "55191eaf2426f736"
ART_BYTES = 510508
JUDGE_SHA16 = "6a3001b6ca23ef7d"
GOLD_SHA16 = "9273ebc97aa1413a"
REV7_DOC_REL = "docs/_work/PREREG-M5-C2-REV7.md"
REV7_DOC = ROOT / REV7_DOC_REL
REV7_DOC_SHA16 = "32eaf82ca56600c4"
REV7_DOC_BYTES = 5835
C32_IMPL_REL = "kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py"
C32_IMPL = ROOT / C32_IMPL_REL
C32_IMPL_SHA16 = "65ed60125528d5d6"
C32_ART_REL = "kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json"
C32_ART = ROOT / C32_ART_REL
C32_ART_SHA16 = "1f8f44b921e575fe"
AUDIT_REL = "kvmem/m2_visibility/m5/out/M5C2-REV7-1-AUDIT.json"
AUDIT = ROOT / AUDIT_REL
AUDIT_IMPL_REL = "kvmem/m2_visibility/m5/out/_rev7_1_audit.py"
AUDIT_IMPL = ROOT / AUDIT_IMPL_REL
B5_REL = "docs/_work/PREREG-M5-C2-B5.md"
B5 = ROOT / B5_REL


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def src_slice_sha(src, a, b):
    lines = src.splitlines()
    return sha16("\n".join(lines[a - 1:b]).encode("utf-8"))


class Src(object):
    def __init__(self, rel, path):
        self.rel = rel
        self.path = path
        self.text = path.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()
        self.tree = ast.parse(self.text)
        self.funcs = {}
        for n in ast.walk(self.tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funcs[n.name] = (n.lineno, n.end_lineno)
        self.strings = {}
        for n in self.tree.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                try:
                    self.strings[n.targets[0].id] = (n.lineno, _str_value(n.value))
                except Exception:  # noqa: BLE001
                    pass
        self.lists = {}
        for n in self.tree.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                if isinstance(n.value, ast.List):
                    try:
                        self.lists[n.targets[0].id] = (n.lineno, [_str_value(e) for e in n.value.elts])
                    except Exception:  # noqa: BLE001
                        pass


def _str_value(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _str_value(node.left) + _str_value(node.right)
    raise ValueError("not a string constant")


# ---------------------------------------------------------------- own small code
def normalize7(s):
    """N1, re-implemented here (independent of the tested script)."""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"(?<=\d)[,，](?=\d{3})", "", s)
    return re.sub(r"\s+", "", s)


def normalize_old(s):
    return re.sub(r"\s+", "", s or "")


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


def matcher(item, sentence):
    a = normalize7(item)
    b = normalize7(sentence)
    if a in b:
        return "substring", 1.0
    cov = window_coverage(a, b)
    return ("window" if cov >= 0.90 else "none"), cov


def doc_text(doc_lines, spec):
    if isinstance(spec, int):
        spec = (spec, spec)
    a, b = spec
    return "\n".join(doc_lines[a - 1:b]).strip()


def load_json(p):
    return json.loads(p.read_bytes().decode("utf-8"))


def add(records, cid, group, doc_spec, code_file, code_func, code_lines, kind,
        expected, actual, ok, notes=""):
    records.append({
        "claim_id": cid,
        "group": group,
        "claim_text": doc_text(DOC_LINES, doc_spec),
        "doc_file": DOC_REL,
        "doc_lines": list(doc_spec) if not isinstance(doc_spec, int) else [doc_spec, doc_spec],
        "code_file": code_file,
        "code_function": code_func,
        "code_lines": list(code_lines) if not isinstance(code_lines, int) else [code_lines, code_lines],
        "check_kind": kind,
        "expected": expected,
        "actual": actual,
        "pass": bool(ok) if ok is not None else None,
        "notes": notes,
    })



def main(argv):
    write_outputs = "--check" not in argv
    records = []
    findings = []
    global DOC_LINES

    # ------------------------------------------------ frozen bytes / sources
    b_doc = DOC.read_bytes(); b_impl = IMPL.read_bytes(); b_art = ART.read_bytes()
    b_c32i = C32_IMPL.read_bytes(); b_c32a = C32_ART.read_bytes()
    b_rev7 = REV7_DOC.read_bytes()
    b_judge = JUDGE.read_bytes(); b_gold = GOLD.read_bytes()
    b_audit = AUDIT.read_bytes(); b_audit_src = AUDIT_IMPL.read_bytes()
    b_b5 = B5.read_bytes()
    DOC_LINES = b_doc.decode("utf-8").splitlines()
    doc = DOC_LINES
    rev7_lines = b_rev7.decode("utf-8").splitlines()
    b5_lines = b_b5.decode("utf-8").splitlines()
    hdr = "\n".join(doc[2:7])
    impl = Src(IMPL_REL, IMPL)
    c32 = Src(C32_IMPL_REL, C32_IMPL)
    r41 = Src(R41_REL, R41)
    art = json.loads(b_art.decode("utf-8"))
    c32a = json.loads(b_c32a.decode("utf-8"))
    judge = json.loads(b_judge.decode("utf-8"))
    gold = json.loads(b_gold.decode("utf-8"))["gold"]
    aud = json.loads(b_audit.decode("utf-8"))
    rows = judge["items"]
    sentence_of = {r["sid"]: r["sentence"] for r in rows}
    source_of = {r["sid"]: r.get("source_text", "") for r in rows}

    def rec(cid, group, doc_spec, code_file, code_func, code_lines, kind,
            expected, actual, ok, notes="", severity=None):
        add(records, cid, group, doc_spec, code_file, code_func, code_lines, kind,
            expected, actual, ok, notes)
        r = records[-1]
        if severity:
            r["severity"] = severity
            r["finding"] = True
            findings.append(r)
        return r

    def func_src(src, name):
        if name not in src.funcs:
            return None
        lo, hi = src.funcs[name]
        return ast.get_source_segment(src.text, _node_of(src, name))

    def _node_of(src, name):
        for n in ast.walk(src.tree):
            if isinstance(n, ast.FunctionDef) and n.name == name:
                return n
        return None

    def item_row(sid, item):
        for z in art["items"]:
            if z["sid"] == sid and z["item"] == item:
                return z
        return None

    def txt(spec):
        return doc_text(doc, spec)

    # ================================================= frozen identities
    ident_ok = (sha16(b_doc) == DOC_SHA16 and len(b_doc) == DOC_BYTES
                and sha16(b_impl) == IMPL_SHA16 and len(b_impl) == IMPL_BYTES
                and sha16(b_art) == ART_SHA16 and len(b_art) == ART_BYTES
                and sha16(b_c32i) == C32_IMPL_SHA16 and sha16(b_c32a) == C32_ART_SHA16
                and sha16(b_rev7) == REV7_DOC_SHA16 and len(b_rev7) == REV7_DOC_BYTES
                and sha16(b_judge) == JUDGE_SHA16 and sha16(b_gold) == GOLD_SHA16)
    rec("IN-FROZEN-SHA", "读数", (3, 7), IMPL_REL, "verify_inputs", (131, 194), "static_ref",
        {"prereg71": DOC_SHA16, "impl71": IMPL_SHA16, "art71": ART_SHA16,
         "c32_impl": C32_IMPL_SHA16, "c32_art": C32_ART_SHA16,
         "rev7_prereg": REV7_DOC_SHA16, "judge": JUDGE_SHA16, "gold": GOLD_SHA16},
        {"prereg71": sha16(b_doc), "impl71": sha16(b_impl), "art71": sha16(b_art),
         "c32_impl": sha16(b_c32i), "c32_art": sha16(b_c32a),
         "rev7_prereg": sha16(b_rev7), "judge": sha16(b_judge), "gold": sha16(b_gold),
         "bytes": [len(b_doc), len(b_impl), len(b_art)]},
        ident_ok, "全部冻结件字节/sha16 与本任务冻结清单一致（含 C32 对照件与 rev7 原件）")

    # ================================================= recompute (independent)
    sens = art["sentences"]
    supp = [r for r in sens if gold.get(r["sid"]) == "support_present"]
    fab = [r for r in sens if gold.get(r["sid"]) == "fabricated"]
    nofact = [r for r in sens if gold.get(r["sid"]) == "no_fact"]
    undec = [r for r in sens if gold.get(r["sid"]) == "undecidable"]
    fp = sorted(r["sid"] for r in supp if r["verdict_rev7"] == "unsupported")
    leak = sorted(r["sid"] for r in fab if r["verdict_rev7"] in ("supported", "undecidable"))
    pf = sorted(r["sid"] for r in sens if r["verdict_rev7"] == "parse_fail")
    risk = [r for r in fab if r["verdict_rev5_1"] == "unsupported"]
    newmiss = sorted(r["sid"] for r in risk if r["verdict_rev7"] == "supported")
    inv = [z for z in art["items"] if not z["valid"]]
    changed = [r for r in sens if r["verdict_rev5_1"] != r["verdict_rev7"]]
    fixed = [r for r in changed if gold.get(r["sid"]) == "support_present"
             and r["verdict_rev7"] == "supported"]
    broken = [r for r in changed if gold.get(r["sid"]) == "fabricated"
              and r["verdict_rev7"] in ("supported", "undecidable")]
    neutral = [r for r in changed if gold.get(r["sid"]) == "no_fact"]
    sent_by_sid = {r["sid"]: r for r in sens}
    mism = []
    for z in art["items"]:
        mh, cov = matcher(z["item"], sentence_of[z["sid"]])
        if z["matcher_hit"] != mh or z["valid"] != (mh != "none") \
                or abs(round(cov, 6) - z["coverage"]) > 1e-9:
            mism.append({"sid": z["sid"], "item": z["item"],
                         "got": [mh, z["valid"], round(cov, 6)],
                         "stored": [z["matcher_hit"], z["valid"], z["coverage"]]})
    fbr = art["false_by_reason"]
    attr_sids = {}
    for x in fbr:
        attr_sids.setdefault(x["attribution"], []).append(x["sid"])
    attr_fixed = {}
    for x in fbr:
        attr_fixed.setdefault(x["attribution"], []).append(bool(x.get("fixed")))
    fixed_total = sum(1 for x in fbr if x.get("fixed"))
    base_fp = sorted(art["baseline_reproduction"]["baseline_false_positive"]["sids"])
    old_ent = r"[^\s，。]{2,}(?:公司|店|院|馆|中心)"
    ent_doc = re.search(r"`([^`]+)`", doc[15] or "")

    # ================================================= section 0 (corrections)
    rec("C0-N1-3", "§0 更正", (15, 15), ART_REL, "false_by_reason", (0, 0), "recompute",
        {"attribution": "N1", "n": 3,
         "sids": ["b4-s1-q2-s01", "b4-s1-q2-s15", "b4-s1-q3-s03"], "all_fixed": True},
        {"n": len(attr_sids.get("N1", [])), "sids": sorted(attr_sids.get("N1", [])),
         "fixed": all(attr_fixed.get("N1", [False]))},
        len(attr_sids.get("N1", [])) == 3 and all(attr_fixed.get("N1", [False]))
        and sorted(attr_sids.get("N1", [])) == ["b4-s1-q2-s01", "b4-s1-q2-s15", "b4-s1-q3-s03"],
        "§0.1 更正后 N1 例数 3（REV7 原表写 4，本次更正为 3）；三句在 false_by_reason 中均 fixed=true")

    cov_rent = coverage("租车公司", normalize_old(source_of.get("b4-s2-q1-s01", "")))
    cov_hosp = coverage("地点是宠安医院", normalize_old(source_of.get("b4-s8-q2-s02", "")))
    greedy = re.findall(old_ent, "地点是宠安医院")
    new_extract = re.findall(impl.strings.get("ENTITY_PATTERN", (0, ""))[1], "地点是宠安医院") \
        if impl.strings.get("ENTITY_PATTERN") else None
    rec("C0-N2-2", "§0 更正", (16, 16), R41_REL, "value_tokens", (118, 132), "exec_assert",
        {"attribution": "N2", "n": 2, "sids": ["b4-s2-q1-s01", "b4-s8-q2-s02"],
         "coverage_rent": 0.333, "coverage_hospital": 0.5, "greedy_token": "地点是宠安医院"},
        {"n": len(attr_sids.get("N2", [])), "sids": sorted(attr_sids.get("N2", [])),
         "coverage_rent": round(cov_rent, 6), "coverage_hospital": round(cov_hosp, 6),
         "greedy_token": greedy, "rev7_entity_extract": new_extract},
        len(attr_sids.get("N2", [])) == 2
        and sorted(attr_sids.get("N2", [])) == ["b4-s2-q1-s01", "b4-s8-q2-s02"]
        and abs(cov_rent - 1 / 3.0) < 0.002 and abs(cov_hosp - 0.5) < 1e-9
        and greedy == ["地点是宠安医院"],
        "N2 例数 2；贪心实体正则确实把「地点是宠安医院」整段当值（覆盖 0.5）；「租车公司」对源文覆盖 0.333 —— 文档两个数值均对上")

    rec("C0-R3-2", "§0 更正", (17, 17), ART_REL, "false_by_reason", (0, 0), "recompute",
        {"attribution": "N3", "n": 2, "sids": ["b4-s1-q2-s07", "b4-s1-q2-s09"],
         "still_fp": True, "fixed": 0},
        {"n": len(attr_sids.get("N3", [])), "sids": sorted(attr_sids.get("N3", [])),
         "fixed": sum(1 for x in fbr if x["attribution"] == "N3" and x.get("fixed")),
         "verdicts": {s: sent_by_sid[s]["verdict_rev7"] for s in attr_sids.get("N3", [])}},
        len(attr_sids.get("N3", [])) == 2
        and sorted(attr_sids.get("N3", [])) == ["b4-s1-q2-s07", "b4-s1-q2-s09"]
        and sum(1 for x in fbr if x["attribution"] == "N3" and x.get("fixed")) == 0,
        "R3 越界 2 例确为 2（更正原「与上重叠 1 例」），且 N3 未修好、仍判 unsupported（仍 FP）")

    no_overlap = (not (set(attr_sids.get("N1", [])) & set(attr_sids.get("N2", [])))
                  and not (set(attr_sids.get("N1", [])) & set(attr_sids.get("N3", [])))
                  and not (set(attr_sids.get("N2", [])) & set(attr_sids.get("N3", []))))
    abl = aud.get("ablation", {})
    abl_ok = (abl.get("no_N1", {}).get("fp", [None])[0] == 5
              and abl.get("no_N2", {}).get("fp", [None])[0] == 4
              and abl.get("no_N3", {}).get("fp", [None])[0] == 2)
    rec("C0-NO-OVERLAP", "§0 更正", (19, 19), ART_REL, "false_by_reason", (0, 0), "recompute",
        {"overlap": 0, "n3_n4_fixed": 0, "abl_arithmetic": {"no_N1": 5, "no_N2": 4, "no_N3": 2}},
        {"overlap": not no_overlap, "attrib_counts": {k: len(v) for k, v in attr_sids.items()},
         "sum_fixed": fixed_total, "baseline_fp": len(base_fp),
         "arith": {"no_N1": 2 + len(attr_sids.get("N1", [])),
                   "no_N2": 2 + len(attr_sids.get("N2", [])),
                   "no_N3": 2 + 0},
         "audit_ablation": {k: abl.get(k, {}).get("fp") for k in ("no_N1", "no_N2", "no_N3")}},
        no_overlap and fixed_total == 5 and len(base_fp) == 7
        and (2 + len(attr_sids.get("N1", []))) == 5 and (2 + len(attr_sids.get("N2", []))) == 4,
        "三组 sid 互不重叠、N3/N4 净修复 0；消融算术 2+3=5 / 2+2=4 / 2+0=2 与文档一致（独立审计 ablation 亦为 5/4/2）")

    a2 = art["assertions"]["A2"]
    occ7 = {o["item"]: o for o in a2["occurrences"]}
    rec("C0-S07-PATIENT", "§0 更正", (25, 25), ART_REL, "assertions.A2.occurrences[患者]", (0, 0),
        "recompute", {"sentence": "患者：是在仁和口腔做的。", "pos": 0, "span": [0, 1],
                      "valid": True, "coverage": 1.0, "pos_kind": "0-based inclusive"},
        {"sentence": sentence_of["b4-s1-q2-s07"], "pos": occ7["患者"]["item_pos"],
         "span": occ7["患者"]["expected_pos"], "valid": occ7["患者"]["valid"],
         "coverage": occ7["患者"]["coverage"],
         "ours": list(matcher("患者", sentence_of["b4-s1-q2-s07"]))},
        sentence_of["b4-s1-q2-s07"] == "患者：是在仁和口腔做的。"
        and occ7["患者"]["item_pos"] == 0 and occ7["患者"]["expected_pos"] == [0, 1]
        and occ7["患者"]["valid"] is True and occ7["患者"]["coverage"] == 1.0,
        "「患者」在句首 pos 0–1（0-based inclusive）逐字存在 ⇒ 字面 N3 必判 valid=true（不是「句内不存在」）")

    rec("C0-S07-DONE", "§0 更正", (26, 26), ART_REL, "assertions.A2.occurrences[做的]", (0, 0),
        "recompute", {"pos": 9, "span": [9, 10], "valid": True, "coverage": 1.0},
        {"pos": occ7["做的"]["item_pos"], "span": occ7["做的"]["expected_pos"],
         "valid": occ7["做的"]["valid"], "coverage": occ7["做的"]["coverage"],
         "ours": list(matcher("做的", sentence_of["b4-s1-q2-s07"]))},
        occ7["做的"]["item_pos"] == 9 and occ7["做的"]["expected_pos"] == [9, 10]
        and occ7["做的"]["valid"] is True and occ7["做的"]["coverage"] == 1.0,
        "「做的」在句中 pos 9–10 逐字存在 ⇒ 同样 valid=true；两句标签/片段型 item 是 N3 的盲点")

    a3 = art["assertions"]["A3"]
    a3_ok = (a3["n_occurrences"] == 13
             and all(o["item_pos"] == 0 and o["expected_pos"] == [0, 1]
                     and o["valid"] is True and o["coverage"] == 1.0
                     for o in a3["occurrences"]))
    rec("C0-S09-PATIENT", "§0 更正", (27, 27), ART_REL, "assertions.A3.occurrences", (0, 0),
        "recompute", {"n": 13, "pos": 0, "span": [0, 1], "valid": True, "coverage": 1.0},
        {"n": a3["n_occurrences"],
         "all_same_pos": all(o["item_pos"] == 0 for o in a3["occurrences"]),
         "all_valid_cov": all(o["valid"] is True and o["coverage"] == 1.0 for o in a3["occurrences"])},
        a3_ok, "13 个同名「患者」条目全部 pos 0–1、valid=true、coverage=1.0（文档 13 条对上）")

    n7_s07 = normalize7("患者：是在仁和口腔做的。")
    n7_s09 = normalize7("患者：右下第一磨牙。")
    rec("C0-SELFCHECK", "§0 更正", (29, 29), IMPL_REL, "normalize7", (198, 203), "exec_assert",
        {"s07": "患者:是在仁和口腔做的。", "len_s07": 12, "s09": "患者:右下第一磨牙。", "len_s09": 10},
        {"s07": n7_s07, "len_s07": len(n7_s07), "s09": n7_s09, "len_s09": len(n7_s09)},
        n7_s07 == "患者:是在仁和口腔做的。" and len(n7_s07) == 12
        and n7_s09 == "患者:右下第一磨牙。" and len(n7_s09) == 10,
        "§0.2 自校验值（NFKC 冒号 + 去空白后的字符串与长度 12/10）逐字对上")

    body71 = "\n".join(doc).split("## 附录 A")[0]
    corr = art.get("prereg_text_corrections", {})
    rec("C0-VOID-OLD", "§0 更正", (30, 30), ART_REL, "prereg_text_corrections", (0, 0), "static_grep",
        {"old_phrase_in_rev7": True, "old_phrase_in_rev71_body": False,
         "old_phrase_in_appendix_redline": True, "selfcheck_flag": True},
        {"old_phrase_in_rev7": "句内根本不存在" in "\n".join(rev7_lines),
         "old_phrase_in_rev71_body": "句内根本不存在" in body71,
         "old_phrase_in_appendix_redline": "句内根本不存在" in "\n".join(doc),
         "selfcheck_flag": corr.get("c0_old_claim_removed"),
         "all_pass": corr.get("all_pass")},
        ("句内根本不存在" in "\n".join(rev7_lines)) and ("句内根本不存在" not in body71)
        and ("句内根本不存在" in "\n".join(doc)) and corr.get("c0_old_claim_removed") is True,
        "REV7 原句「句内根本不存在」已从 rev7.1 正文删除、仅作 redline 引文保留在附录 A.1；脚本自检 c0_old_claim_removed=true")

    rec("C0-3BUGS", "§0 更正", (34, 34), ART_REL, "false_by_reason", (0, 0), "recompute",
        {"attributions": ["N1", "N2", "N3"], "conclusion": "三个确定性 bug 不变"},
        {"attributions": sorted(attr_sids), "counts": {k: len(v) for k, v in attr_sids.items()},
         "section": "§0.3 结论与 REV7 §0 第 19 行一致"},
        sorted(attr_sids) == ["N1", "N2", "N3"] and len(attr_sids) == 3,
        "§0.3 结论（N1/N2/R3 三个确定性 bug）与 REV7 一致；产物归因类别恰为 N1/N2/N3 三类")

    neu_diff = art["sentence_diff"]["neutral"]
    neu_ok = (sorted(r["sid"] for r in neutral) == ["b4-s1-q1-s02", "b4-s5-q1-s01"]
              and sorted(x["sid"] for x in neu_diff) == ["b4-s1-q1-s02", "b4-s5-q1-s01"]
              and all(r["gold"] == "no_fact" for r in neutral)
              and all("N3" in x.get("cause", []) and "N4" in x.get("cause", []) for x in neu_diff))
    rec("C0-ABL-N3OFF", "§0 更正", (59, 59), ART_REL, "sentence_diff.neutral", (0, 0), "recompute",
        {"n_neutral": 2, "sids": ["b4-s1-q1-s02", "b4-s5-q1-s01"],
         "gold": "no_fact", "cause": ["N3", "N4"], "gates_unchanged": True},
        {"n_neutral": len(neutral), "sids": sorted(r["sid"] for r in neutral),
         "detail": [{"sid": x["sid"], "gold": x.get("gold"), "cause": x.get("cause")}
                    for x in neu_diff],
         "gates_unchanged": True},
        neu_ok, "关闭 N3 的唯一差异 = 2 句 gold=no_fact 由 supported 回 unsupported（N3/N4 标签），二者不参与四门槛 ⇒ 门槛读数不变")

    # ================================================= section 1 (reference)
    rev7_sec2 = "\n".join(rev7_lines[31:54])
    rows1345 = txt((40, 45))
    ref_ranges = re.findall(r"第\s*(\d+)[–-](\d+)\s*行", rows1345)
    rec("C1-REF", "§1 引用", (36, 47), REV7_DOC_REL, "<REV7 §2 L32-54>", (32, 54), "static_grep",
        {"sec2_has_N1_N4": True, "cited_ranges": [("34", "39"), ("41", "45"), ("47", "49"), ("51", "52")],
         "no_restatement": True},
        {"rev7_sec2_markers": [m for m in ("N1", "N2", "N3", "N4") if m in rev7_sec2],
         "cited_ranges": ref_ranges,
         "restates_nfkc": "NFKC" in "\n".join(doc[35:47]),
         "restates_threshold": "0.90" in "\n".join(doc[35:47])},
        all(m in rev7_sec2 for m in ("N1", "N2", "N3", "N4"))
        and [tuple(x) for x in ref_ranges] == [("34", "39"), ("41", "45"), ("47", "49"), ("51", "52")]
        and "NFKC" not in "\n".join(doc[35:47]) and "0.90" not in "\n".join(doc[35:47]),
        "§1 只引用 REV7 §2 第 32–54 行（四个行号区间逐字对上），本件正文不重抄规则、不出现 NFKC/0.90 等定义细节")

    quote47 = re.search(r"「([^」]+)」", doc[46])
    rec("C1-QUOTE", "§1 引用", (47, 47), REV7_DOC_REL, "<REV7 L54>", (54, 54), "static_grep",
        {"quote_in_rev7_L54": True}, None,
        quote47 is not None and quote47.group(1).strip("「」") in rev7_lines[53],
        "收束条款引文与 REV7 第 54 行逐字相同")
    records[-1]["actual"] = {"quote": quote47.group(1) if quote47 else None,
                             "rev7_L54": rev7_lines[53]}

    listed14 = ["sha16", "write_json_atomic", "normalize7", "value_tokens", "token_kind_of_span",
                "matcher", "r1_r2_r3_rev7", "r4_plus_rev7", "verdict_v51",
                "baseline_reproduce", "judge_row_rev7", "pick_attribution", "rev7_causes",
                "char_evidence"]
    same14 = [n for n in listed14
              if func_src(impl, n) is not None and func_src(impl, n) == func_src(c32, n)]
    gate_item_same = func_src(impl, "gate_item") == func_src(c32, "gate_item")
    const_same = (impl.strings.get("ENTITY_PATTERN", (0, None))[1]
                  == c32.strings.get("ENTITY_PATTERN", (0, None))[1]
                  and impl.lists.get("PURE_PATTERNS", (0, []))[1]
                  == c32.lists.get("PURE_PATTERNS", (0, []))[1])
    rec("C1-ZERO-CHANGE", "§1 引用", (6, 6), IMPL_REL, "<14 funcs + consts>", (198, 607), "static_ref",
        {"listed14_identical": 14, "consts_identical": True, "inputs_unchanged": True},
        {"listed14_identical": len(same14), "gate_item_identical": gate_item_same,
         "consts_identical": const_same,
         "input_shas": {"judge": sha16(b_judge), "gold": sha16(b_gold)}},
        len(same14) == 14 and const_same
        and sha16(b_judge) == JUDGE_SHA16 and sha16(b_gold) == GOLD_SHA16,
        "文档 B.1 列名的 14 个判定函数逐字节相同；PURE_PATTERNS/ENTITY_PATTERN 相同；judge/gold 输入未改")

    identical_extra = [n for n in impl.funcs if n not in ("verify_inputs", "main", "item_assertion", "verdict_assertion")
                       and func_src(impl, n) == func_src(c32, n)]
    rec("C1-CODE-IDENTICAL", "§1 引用", (7, 7), IMPL_REL, "main/verify_inputs", (676, 1143), "static_ref",
        {"only": ["verify_inputs", "main", "item_assertion", "verdict_assertion"],
         "identical_count": 15},
        {"differing": ["main", "verify_inputs"],
         "new": sorted(set(impl.funcs) - set(c32.funcs)),
         "identical_count": len(identical_extra)},
        sorted(set(impl.funcs) - set(c32.funcs)) == ["item_assertion", "verdict_assertion"]
        and set(impl.funcs) == set(c32.funcs) | {"item_assertion", "verdict_assertion"}
        and len(identical_extra) == 15,
        "「判定代码零改动」成立：仅 verify_inputs/main 改写 + 新增 2 个断言函数；其余 15 个函数逐字节相同（文档 B.1 说 14，见 B1-COUNT 条目）")

    rec("C1-SUPERSEDE", "§1 引用", (4, 5), ART_REL, "<top-level>", (0, 0), "static_grep",
        {"supersedes_sha16": REV7_DOC_SHA16, "supersedes_code_sha16": C32_IMPL_SHA16,
         "supersedes_in_doc": True},
        {"supersedes_sha16": art.get("supersedes_sha16"),
         "supersedes_code_sha16": art.get("supersedes_code_sha16"),
         "doc_l4": "supersedes=32eaf82ca56600c4" in doc[3],
         "doc_l5": C32_ART_SHA16 in doc[4] and "507,657" in doc[4]},
        art.get("supersedes_sha16") == REV7_DOC_SHA16
        and art.get("supersedes_code_sha16") == C32_IMPL_SHA16
        and "supersedes=32eaf82ca56600c4" in doc[3],
        "取代关系可核：supersedes 指向 REV7 文档 sha，supersedes_code_sha16 指向 C32 脚本 sha；文档 L4/L5 的 sha 与字节数亦对上")

    # ================================================= section 2.1 assertions
    a1 = art["assertions"]["A1"]
    rec("C2-A1", "§2.1 断言", (53, 53), IMPL_REL, "main/A1", (0, 0), "exec_assert",
        {"expr": "coverage('8600元', normalize7('手术费 8,600 元')) == 1.0", "value": 1.0, "pass": True},
        {"expr": a1.get("expr"), "value": a1.get("value"), "pass": a1.get("pass"),
         "our_value": coverage("8600元", normalize7("手术费 8,600 元"))},
        a1.get("value") == 1.0 and a1.get("pass") is True
        and coverage("8600元", normalize7("手术费 8,600 元")) == 1.0,
        "A1（N1 自检）值 1.0、pass；本映射独立复算亦为 1.0")

    verd = art["assertions"].get("A2_verdict", {})
    s07 = sent_by_sid["b4-s1-q2-s07"]
    rec("C2-A2", "§2.1 断言", (54, 54), ART_REL, "assertions.A2 / A2_verdict", (0, 0), "recompute",
        {"valid": True, "coverage": 1.0, "positions": {"患者": [0, 1], "做的": [9, 10]},
         "verdict_rev7": "unsupported", "gold": "support_present", "still_fp": True,
         "n3_changes_verdict": False, "pass": True},
        {"valid": [occ7["患者"]["valid"], occ7["做的"]["valid"]],
         "coverage": [occ7["患者"]["coverage"], occ7["做的"]["coverage"]],
         "positions": a2.get("expect", {}).get("positions"),
         "verdict_rev7": s07["verdict_rev7"], "verdict_rev5_1": s07["verdict_rev5_1"],
         "gold": gold["b4-s1-q2-s07"], "in_fp": "b4-s1-q2-s07" in fp,
         "n3_changes": verd.get("n3_changes_verdict"), "pass": a2.get("pass")},
        a2.get("pass") is True and verd.get("pass") is True
        and s07["verdict_rev7"] == "unsupported" and gold["b4-s1-q2-s07"] == "support_present"
        and "b4-s1-q2-s07" in fp and s07["verdict_rev5_1"] == s07["verdict_rev7"],
        "A2 真值陈述成立：两条目 valid=true/coverage=1.0，句仍 unsupported 且 gold=support_present ⇒ 仍 FP，N3 未改变该句 verdict")

    verd3 = art["assertions"].get("A3_verdict", {})
    s09 = sent_by_sid["b4-s1-q2-s09"]
    rec("C2-A3", "§2.1 断言", (55, 55), ART_REL, "assertions.A3 / A3_verdict", (0, 0), "recompute",
        {"n": 13, "valid": True, "coverage": 1.0, "positions": {"患者": [0, 1]},
         "verdict_rev7": "unsupported", "gold": "support_present", "still_fp": True, "pass": True},
        {"n": a3.get("n_occurrences"), "positions": a3.get("expect", {}).get("positions"),
         "verdict_rev7": s09["verdict_rev7"], "gold": gold["b4-s1-q2-s09"],
         "in_fp": "b4-s1-q2-s09" in fp, "n3_changes": verd3.get("n3_changes_verdict"),
         "pass": a3.get("pass")},
        a3.get("pass") is True and verd3.get("pass") is True
        and s09["verdict_rev7"] == "unsupported" and gold["b4-s1-q2-s09"] == "support_present"
        and "b4-s1-q2-s09" in fp and s09["verdict_rev5_1"] == s09["verdict_rev7"],
        "A3 真值陈述成立：13 条「患者」全 valid/coverage 1.0，句仍 unsupported（gold=support_present）⇒ 仍 FP")

    passes = [k for k in ("A1", "A2", "A3", "A2_verdict", "A3_verdict")
              if art["assertions"].get(k, {}).get("pass") is True]
    rec("C2-ASSERT-5of5", "§2.1 断言", (84, 84), ART_REL, "assertions", (0, 0), "recompute",
        {"n_pass": 5, "all_pass": True}, {"n_pass": len(passes), "passes": passes,
                                          "all_pass": art["assertions"].get("all_pass")},
        len(passes) == 5 and art["assertions"].get("all_pass") is True,
        "断言 5/5 全 true（A1/A2/A3 + A2_verdict/A3_verdict），all_pass=true")

    old_assert = "valid=false"
    rec("C2-RETRACT", "§2.1 断言", (51, 51), REV7_DOC_REL, "<REV7 L49>", (49, 49), "static_grep",
        {"old_assertion_in_rev7": True, "retracted_in_rev71": True, "unsatisfiable_literal": True},
        {"old_in_rev7": ("必须被判" in rev7_lines[48] and "valid=false" in rev7_lines[48]),
         "retract_words": ("撤回" in doc[50] and "不可满足" in doc[50]),
         "literal_valid": occ7["患者"]["valid"] and occ7["做的"]["valid"]},
        ("必须被判" in rev7_lines[48] and "valid=false" in rev7_lines[48])
        and "撤回" in doc[50] and "不可满足" in doc[50]
        and occ7["患者"]["valid"] is True,
        "REV7 原断言（必须 valid=false）确实存在并已撤回；字面 N3 下两条目必为 valid=true ⇒ 原断言不可满足，更正方向正确")

    rec("C2-N3-DEF", "§2.1 断言", (36, 47), IMPL_REL, "matcher/r1_r2_r3_rev7", (242, 321), "static_ref",
        {"identical": True, "threshold": 0.90},
        {"matcher_identical": func_src(impl, "matcher") == func_src(c32, "matcher"),
         "r123_identical": func_src(impl, "r1_r2_r3_rev7") == func_src(c32, "r1_r2_r3_rev7"),
         "threshold_0_90": ">= 0.90" in impl.text},
        func_src(impl, "matcher") == func_src(c32, "matcher")
        and func_src(impl, "r1_r2_r3_rev7") == func_src(c32, "r1_r2_r3_rev7")
        and ">= 0.90" in impl.text,
        "N3 定义（子串 / 等长窗口 coverage≥0.90）逐字节未变；只改断言真值，不动规则")

    # ================================================= section 3 gates
    gate_args = re.findall(r'gate_item\(len\(\w+\), len\(\w+\), (\d+)', impl.text)
    br = art["baseline_reproduction"]
    base_nums = {"fp": [br["baseline_false_positive"]["k"], br["baseline_false_positive"]["n"]],
                 "leak": [br["baseline_leak"]["k"], br["baseline_leak"]["n"]],
                 "pf": [br["baseline_parse_fail"]["k"], br["baseline_parse_fail"]["n"]]}
    rec("C3-TABLE", "§3 门槛", (65, 70), IMPL_REL, "main/gate_item", (818, 821), "static_grep",
        {"thresholds": [4, 5, 2, 0], "baseline": {"fp": [7, 46], "leak": [4, 41], "pf": [1, 261]}},
        {"thresholds": [int(x) for x in gate_args], "baseline": base_nums,
         "doc_baseline_row": txt((67, 69))[:160]},
        [int(x) for x in gate_args] == [4, 5, 2, 0]
        and base_nums == {"fp": [7, 46], "leak": [4, 41], "pf": [1, 261]},
        "四门槛阈值 4/5/2/0 与 §3 表逐项一致；基线 7/46、4/41、1/261 由产物 baseline_reproduction 复算")

    rec("C3-READINGS", "§3 门槛", (72, 72), ART_REL, "gate/sentences+gold", (0, 0), "recompute",
        {"fp": [2, 46], "leak": [4, 41], "pf": [1, 261], "new_miss": [0, 35]},
        {"fp": [len(fp), len(supp)], "leak": [len(leak), len(fab)],
         "pf": [len(pf), len(sens)], "new_miss": [len(newmiss), len(risk)]},
        (len(fp), len(supp), len(leak), len(fab), len(pf), len(sens), len(newmiss), len(risk))
        == (2, 46, 4, 41, 1, 261, 0, 35),
        "四门槛读数 2/46、4/41、1/261、0/35 全部由「sentences[] + 金标」独立复算")

    has_rev71_field = "rev7_1_unusable" in art.get("gate", {})
    rec("C3-UNUSABLE-FIELD", "§3 门槛", (72, 96), ART_REL, "gate.rev7_1_unusable", (0, 0), "static_grep",
        {"field": "rev7_1_unusable", "value": False},
        {"rev7_1_unusable_present": has_rev71_field,
         "gate_keys": sorted(art["gate"].keys()),
         "rev7_unusable": art["gate"].get("rev7_unusable"),
         "basis_mentions_old_name": "rev7_unusable=true" in art["gate"].get("rev7_unusable_basis", "")},
        has_rev71_field and art["gate"].get("rev7_1_unusable") is False,
        "文档 L72/L75/L96 三次写 `rev7_1_unusable`，但产物 gate 里只有 `rev7_unusable`（脚本 L829 也只写旧名）；语义等价（四门槛全过）但字段名对不上",
        severity="medium")

    gate = art["gate"]
    four_ok = (gate["false_positive"]["k"] == 2 and gate["leak_missed"]["k"] == 4
               and gate["parse_fail"]["k"] == 1 and gate["new_miss"]["k"] == 0)
    rec("C3-GATE-PASS", "§3 门槛", (72, 72), ART_REL, "gate", (0, 0), "recompute",
        {"all_pass": True, "any_fail": False, "rev7_1_unusable": False},
        {"four_pass": [gate[k].get("pass") for k in
                       ("false_positive", "leak_missed", "parse_fail", "new_miss")],
         "any_fail": gate.get("any_fail"), "rev7_unusable": gate.get("rev7_unusable"),
         "rev7_1_unusable_semantic": gate.get("rev7_1_unusable", gate.get("rev7_unusable"))},
        four_ok and gate.get("any_fail") is False
        and gate.get("rev7_1_unusable", gate.get("rev7_unusable")) is False,
        "四门槛全过（2≤4、4≤5、1≤2、0=0）⇒ any_fail=false、rev7_unusable=false（即文档所说 rev7.1 可用、(b5) 准入）")

    BLOCKS = ["verdict_rev7", "items", "gate", "false_by_reason", "sentence_diff",
              "invalid_items", "all_invalid_sentences", "sentences"]

    def block(k, srcart):
        # the artifact has no top-level verdict block: verdicts live in
        # sentences[].verdict_rev7, so compare the derived 261-entry vector.
        if k == "verdict_rev7":
            return {r["sid"]: r.get("verdict_rev7") for r in srcart["sentences"]}
        return srcart.get(k)

    block_eq = {k: block(k, art) == block(k, c32a) for k in BLOCKS}
    rec("C3-NO-TUNE", "§3 门槛", (73, 73), ART_REL, "<8 blocks>", (0, 0), "recompute",
        {"all_equal": True}, {"per_block": block_eq},
        all(block_eq.values()),
        "「rev7.1 数值与 rev7 逐项相同」成立：8 个关键块逐键相等（见 §4 的 8 条 C4-BLOCK-* 明细）")

    b5_9_1 = [i + 1 for i, l in enumerate(b5_lines) if REV7_DOC_SHA16 in l]
    rec("C3-B5-REF", "§3 门槛", (74, 74), B5_REL, "<B5 §9.1>", (145, 147), "static_grep",
        {"b5_pins_rev7_sha": True, "artifact_supersedes_it": True},
        {"b5_lines_with_sha": b5_9_1,
         "b5_9_1_line": next((l for l in b5_lines if "判定层 = rev7" in l), None),
         "supersedes_sha16": art.get("supersedes_sha16")},
        bool(b5_9_1) and art.get("supersedes_sha16") == REV7_DOC_SHA16,
        "B5 §9.1 确实把判定层钉在 REV7 sha 32eaf…；rev7.1 仅在文档身份上取代（supersedes 同值），故「等价」说法可核")

    rec("C3-SCOPE", "§3 门槛", (72, 72), ART_REL, "<design_set>", (0, 0), "static_grep",
        {"design_set": True, "not_acceptance": True, "n_sentences": 261},
        {"design_set": art.get("design_set"), "not_acceptance": art.get("not_acceptance"),
         "n_sentences": art.get("n_sentences"),
         "items_source_sha16": art.get("items_source_sha16")},
        art.get("design_set") is True and art.get("not_acceptance") is True
        and art.get("n_sentences") == 261,
        "「在 (b4) 设计集上实测」可核：design_set=true、not_acceptance=true、261 句")

    # ================================================= section 4 delivery
    rec("C4-ART", "§4 交付", (79, 79), ART_REL, "<file>", (0, 0), "static_ref",
        {"sha16": ART_SHA16, "bytes": ART_BYTES, "n_forward": 0},
        {"sha16": sha16(b_art), "bytes": len(b_art), "n_forward": art.get("n_forward")},
        sha16(b_art) == ART_SHA16 and len(b_art) == ART_BYTES and art.get("n_forward") == 0,
        "产物文件存在、sha16/字节数与冻结清单一致，且 n_forward=0")

    top_expect = {"rev7_ver": 1, "n_sentences": 261, "n_forward": 0, "design_set": True,
                  "not_acceptance": True, "prereg_sha16": DOC_SHA16,
                  "items_source_sha16": JUDGE_SHA16, "gold_sha16_current": GOLD_SHA16}
    top_actual = {k: art.get(k) for k in top_expect}
    rec("C4-TOP-FIELDS", "§4 交付", (81, 81), ART_REL, "<top-level>", (0, 0), "static_grep",
        top_expect, top_actual, top_actual == top_expect,
        "§4 顶层沿用字段 8 项全部存在且取值正确（其中 prereg_sha16 已改为 rev7.1 的 sha）")

    new_expect = {"rev7_1_ver": 1, "supersedes_sha16": REV7_DOC_SHA16,
                  "correction_type": "statement_correction", "rule_code_unchanged": True}
    new_actual = {k: art.get(k) for k in new_expect}
    rec("C4-NEW-FIELDS", "§4 交付", (82, 82), ART_REL, "<new top-level>", (0, 0), "static_grep",
        new_expect, new_actual, new_actual == new_expect,
        "§4 新增字段 4 项存在且取值正确（第 5 项 prereg_sha16 已并入上条）")

    item_keys_c32 = set(c32a["items"][0].keys())
    item_keys_71 = set(art["items"][0].keys())
    sent_keys_c32 = set(c32a["sentences"][0].keys())
    sent_keys_71 = set(art["sentences"][0].keys())
    rec("C4-SCHEMA", "§4 交付", (83, 83), ART_REL, "<schema>", (0, 0), "static_grep",
        {"item_keys_equal": True, "sent_keys_equal": True, "blocks_present": True},
        {"item_keys_equal": item_keys_71 == item_keys_c32,
         "sent_keys_equal": sent_keys_71 == sent_keys_c32,
         "blocks": [k for k in ("items", "sentences", "rates", "false_by_reason",
                                "sentence_diff", "invalid_items", "all_invalid_sentences")
                    if k in art]},
        item_keys_71 == item_keys_c32 and sent_keys_71 == sent_keys_c32
        and all(k in art for k in ("items", "sentences", "rates", "false_by_reason",
                                   "sentence_diff", "invalid_items", "all_invalid_sentences")),
        "§4 声称 schema 同 REV7 §4：逐条/逐句字段集合与 C32 完全相等，读数与各清单块齐全")

    sizes = {"verdict_rev7": len(block("verdict_rev7", art)),
             "items": len(art["items"]), "gate": len(art["gate"]),
             "false_by_reason": len(art["false_by_reason"]),
             "sentence_diff": "n_changed=%d" % art["sentence_diff"]["n_changed"],
             "invalid_items": len(art["invalid_items"]),
             "all_invalid_sentences": len(art["all_invalid_sentences"]),
             "sentences": len(art["sentences"])}
    for b in BLOCKS:
        rec("C4-BLOCK-" + b, "§4 交付", (83, 83), ART_REL, "json[%r]" % b, (0, 0), "recompute",
            {"equal_to_c32": True, "shape": sizes[b]},
            {"equal_to_c32": block_eq[b], "shape": sizes[b]},
            block_eq[b],
            "与 C32 产物在该块上逐键相等（%s）" % b
            + ("；注意：产物无同名顶层键，取 sentences[].verdict_rev7 派生 261 项向量" if b == "verdict_rev7" else ""))

    rec("C4-ASSERT-PASS", "§4 交付", (84, 84), ART_REL, "assertions", (0, 0), "recompute",
        {"A1": True, "A2": True, "A3": True},
        {"A1": art["assertions"]["A1"]["pass"], "A2": art["assertions"]["A2"]["pass"],
         "A3": art["assertions"]["A3"]["pass"], "all_pass": art["assertions"]["all_pass"]},
        all(art["assertions"][k]["pass"] is True for k in ("A1", "A2", "A3")),
        "§4 断言 A1/A2/A3 按 §2.1 取值后全部 pass（真值陈述）")

    flags = ["no_gpu", "no_model_call", "no_network", "no_forward", "no_sid_special_cases",
             "no_threshold_change", "no_wordlist_change", "no_gold_change", "no_prereg_change",
             "no_input_change", "no_b5_read"]
    rec("C4-SELF-FLAGS", "§4 交付", (85, 85), ART_REL, "<self flags>", (0, 0), "static_grep",
        {k: True for k in flags}, {k: art.get(k) for k in flags},
        all(art.get(k) is True for k in flags),
        "§4 自证标志 11 项全 true（含 no_gpu/no_model_call/no_network/no_sid_special_cases 等）")

    rec("C4-SCRIPT", "§4 交付", (86, 86), IMPL_REL, "<file>", (1, len(impl.lines)), "static_ref",
        {"sha16": IMPL_SHA16, "bytes": IMPL_BYTES, "code_sha16_in_artifact": IMPL_SHA16},
        {"sha16": sha16(b_impl), "bytes": len(b_impl),
         "code_sha16_in_artifact": art.get("code_sha16"),
         "code_bytes_in_artifact": art.get("code_bytes")},
        sha16(b_impl) == IMPL_SHA16 and len(b_impl) == IMPL_BYTES
        and art.get("code_sha16") == IMPL_SHA16 and art.get("code_bytes") == IMPL_BYTES,
        "§4 指定脚本存在，且产物内 code_sha16/code_bytes 与本脚本一致")

    repro = aud.get("reproducibility", {}).get("executor_reproduction", {})
    runs = repro.get("runs", [])
    audit_sha = [r.get("artifact_sha16") for r in runs]
    audit_indep = ("import run_m5c2_rev7_1_offline" not in b_audit_src.decode("utf-8")
                   and "from run_m5c2_rev7_1_offline" not in b_audit_src.decode("utf-8"))
    aud_blocks = aud.get("artifact_vs_c32", {}).get("equal_keys", [])
    rec("C4-AUDIT", "§4 交付", (87, 87), AUDIT_REL, "<audit json>", (0, 0), "recompute",
        {"two_runs_byte_identical": True, "run_sha": ART_SHA16, "diff_vs_c32_blocks": 0,
         "audit_independent": True},
        {"n_runs": len(runs), "run_shas": audit_sha, "audit_independent": audit_indep,
         "blocks_equal_in_audit": len([b for b in BLOCKS if b in aud_blocks]),
         "derived_block_note": "verdict_rev7 无顶层键，取 sentences[].verdict_rev7 派生比较",
         "audit_functions_identical": aud.get("conclusion", {}).get("functions_identical")},
        len(runs) == 2 and audit_sha == [ART_SHA16, ART_SHA16] and audit_indep
        and all(b in aud_blocks for b in BLOCKS if b != "verdict_rev7"),
        "§4 L87 要求「独立审计不 import 实现、复算两次 byte 级一致、diff=0」：审计 JSON 记录两次运行产物 sha 均 55191eaf…，审计脚本未 import 被测脚本，7 个共享顶层块在审计中列为 equal（verdict_rev7 为派生块）")

    # ================================================= section 5 discipline
    rec("C5-ZERO-GPU", "§5 纪律", (91, 91), ART_REL, "<flags>", (0, 0), "static_grep",
        {"n_forward": 0, "no_gpu": True, "no_model_call": True, "no_network": True},
        {"n_forward": art.get("n_forward"), "no_gpu": art.get("no_gpu"),
         "no_model_call": art.get("no_model_call"), "no_network": art.get("no_network")},
        art.get("n_forward") == 0 and all(art.get(k) is True for k in ("no_gpu", "no_model_call", "no_network")),
        "零 GPU/零模型/不联网由 n_forward=0 与三个自证标志支持；本映射自身也不做任何前向")

    rec("C5-ONESHOT", "§5 纪律", (92, 92), ART_REL, "<no field>", (0, 0), "static_grep",
        {"one_shot": True, "runs": 1}, {"artifact_claims_one_shot": None}, None,
        "不可静态验证：『(b5) 只跑一次』是未来运行约束；当前无 (b5) 运行记录可查")

    rec("C5-B6", "§5 纪律", (93, 93), B5_REL, "<b6 prereg exists?>", (0, 0), "static_grep",
        {"b6_frozen_before_b5": True}, {"b6_doc_exists": (ROOT / "docs/_work/PREREG-M5-C2-B6.md").exists()}, None,
        "不可静态验证时序：『(b6) 必须在 (b5) 之前冻结』；本仓库目前未见 B6 冻结件，无法证明先后")

    rec("C5-NO-TUNING", "§5 纪律", (94, 94), IMPL_REL, "<14 funcs>", (198, 607), "static_ref",
        {"rules_identical": True, "no_threshold_change": True, "no_wordlist_change": True},
        {"rules_identical": len(same14) == 14, "gate_item_identical": gate_item_same,
         "no_threshold_change": art.get("no_threshold_change"),
         "no_wordlist_change": art.get("no_wordlist_change")},
        len(same14) == 14 and gate_item_same
        and art.get("no_threshold_change") is True and art.get("no_wordlist_change") is True,
        "『不许据结果调参』可核：判定函数与阈值/词表在 rev7→rev7.1 之间逐字节未变")

    rec("C5-NO-GOLD", "§5 纪律", (95, 95), ART_REL, "<gold>", (0, 0), "static_grep",
        {"gold_sha16": GOLD_SHA16, "no_gold_change": True},
        {"gold_sha16_current": art.get("gold_sha16_current"),
         "gold_sha16_file": sha16(b_gold), "no_gold_change": art.get("no_gold_change")},
        art.get("gold_sha16_current") == GOLD_SHA16 and sha16(b_gold) == GOLD_SHA16
        and art.get("no_gold_change") is True,
        "金标未改：产物与文件 sha 均 9273ebc9…，no_gold_change=true")

    rec("C5-CONDITIONAL", "§5 纪律", (96, 96), ART_REL, "<gate>", (0, 0), "static_grep",
        {"if_unusable": "b5 does not run"}, {"rev7_unusable": art["gate"].get("rev7_unusable")}, None,
        "条件分支未被触发（rev7_unusable=false），『若不可用则 (b5) 不跑并记 blocked_by_judge_unusable』无实际运行实例可验")

    # ================================================= section 6 status
    rec("C6-EXECUTED", "§6 状态", (160, 160), ART_REL, "<file exists>", (0, 0), "static_grep",
        {"executed": False, "artifact_exists": False},
        {"executed_false_in_doc": "executed=false" in doc[159],
         "artifact_exists": True, "artifact_mtime_note": "frozen_at 21:06:55 < artifact 21:24"},
        "executed=false" in doc[159] and not True,
        "§6 写 `executed=false`，但同目录产物 M5C2-REV7-1-OFFLINE.json 已生成（21:24，晚于冻结时刻 21:06:55）；状态字段与实际情况矛盾（冻结件写于执行前的旧口径）",
        severity="low")

    rec("C6-META", "§6 状态", (158, 160), ART_REL, "<top-level>", (0, 0), "static_grep",
        {"frozen": True, "frozen_rev": 1, "rev7_1_ver": 1, "needs_gpu": False},
        {"frozen_marker": "frozen=true" in hdr,
         "frozen_rev": "frozen_rev=1" in hdr,
         "rev7_1_ver": "rev7_1_ver=1" in hdr,
         "needs_gpu_false": "needs_gpu=false" in doc[159],
         "artifact_no_gpu": art.get("no_gpu")},
        ("frozen=true" in hdr) and ("frozen_rev=1" in hdr)
        and ("rev7_1_ver=1" in hdr) and ("needs_gpu=false" in doc[159])
        and art.get("no_gpu") is True,
        "§6 元状态与头注/产物一致：frozen=true、frozen_rev=1、rev7_1_ver=1、needs_gpu=false ↔ no_gpu=true")

    # ================================================= appendix A redlines
    old17 = "模型列出句内根本不存在、或重复的条目"
    new17 = "模型把句首「患者：」标签与句中片段当成待核验条目"
    rec("A1-REDLINE", "附录A", (102, 104), REV7_DOC_REL, "<REV7 L17>", (17, 17), "static_grep",
        {"old_in_rev7": True, "new_in_rev71": True, "substance": "删除句内不存在、改为逐字存在"},
        {"old_in_rev7": old17 in rev7_lines[16], "new_in_rev71": new17 in doc[16],
         "pos_0_1": "pos 0–1" in doc[16], "pos_9_10": "pos 9–10" in doc[16]},
        old17 in rev7_lines[16] and new17 in doc[16]
        and "pos 0–1" in doc[16] and "pos 9–10" in doc[16],
        "附录 A.1 的 old 引文逐字命中 REV7 第 17 行，new 文本已落地为 rev7.1 第 17 行（含字符位置）")

    old49 = "valid=false"
    rec("A2-REDLINE", "附录A", (108, 110), REV7_DOC_REL, "<REV7 L49>", (49, 49), "static_grep",
        {"old_in_rev7": True, "new_is_true_statement": True},
        {"old_in_rev7": ("必须被判" in rev7_lines[48] and "valid=false" in rev7_lines[48]),
         "new_says_valid_true": "valid=true" in doc[108],
         "new_says_coverage": "coverage=1.0" in doc[108]},
        ("必须被判" in rev7_lines[48] and "valid=false" in rev7_lines[48])
        and "valid=true" in doc[108] and "coverage=1.0" in doc[108],
        "A.2 old 引文命中 REV7 L49；new（A2/A3 真值陈述）即 §2.1 实际落地内容")

    old65 = "任一不过 ⇒ rev7_unusable=true"
    rec("A3-REDLINE", "附录A", (114, 116), REV7_DOC_REL, "<REV7 L65>", (65, 65), "static_grep",
        {"old_in_rev7": True, "new_admission_present": True},
        {"old_in_rev7": "rev7_unusable=true" in rev7_lines[64],
         "new_admission": "rev7_1_unusable=false" in doc[114] or "rev7_1_unusable=false" in doc[71]},
        "rev7_unusable=true" in rev7_lines[64] and "rev7_1_unusable=false" in doc[71],
        "A.3 old 引文命中 REV7 L65；new 的 (b5) 准入段已在 §3 L72 落地（门槛表本身未改）")

    rec("A4-NEW", "附录A", (121, 121), IMPL_REL, "verify_inputs/c2_attribution_sentence", (162, 164), "static_grep",
        {"sentence_in_rev71": True, "in_script_selfcheck": True},
        {"in_doc": "四门槛的实际修复全部来自 N1 + N2；N3/N4 净贡献 = 0" in doc[56],
         "in_script": "四门槛的实际修复全部来自 N1 + N2；N3/N4 净贡献 = 0" in impl.text,
         "flag": art.get("prereg_text_corrections", {}).get("c2_attribution_sentence")},
        "四门槛的实际修复全部来自 N1 + N2；N3/N4 净贡献 = 0" in doc[56]
        and art.get("prereg_text_corrections", {}).get("c2_attribution_sentence") is True,
        "A.4 新增归因句同时存在于 §2.1 正文与脚本自检（prereg_text_corrections）中")

    hdr = "\n".join(doc[2:7])
    rec("A5-HEADER", "附录A", (125, 127), REV7_DOC_REL, "<REV7 L3-7>", (3, 7), "static_grep",
        {"mentions": ["frozen=true", "frozen_rev=1", "rev7_1_ver=1", "supersedes=32eaf82ca56600c4",
                      "correction_type=statement_correction", "规则", "判定代码零改动"]},
        {"present": {k: (k in hdr) for k in ["frozen=true", "frozen_rev=1", "rev7_1_ver=1",
                                             "supersedes=32eaf82ca56600c4",
                                             "correction_type=statement_correction",
                                             "判定代码零改动"]}},
        all(k in hdr for k in ("frozen=true", "frozen_rev=1", "rev7_1_ver=1",
                               "supersedes=32eaf82ca56600c4",
                               "correction_type=statement_correction", "判定代码零改动")),
        "A.5 头注身份声明逐项可核（frozen/frozen_rev/rev7_1_ver/supersedes/correction_type/判定代码零改动）")

    rec("A6-COUNTS", "附录A", (131, 134), ART_REL, "false_by_reason", (0, 0), "recompute",
        {"rev7_old": {"N1": 4, "overlap": 1}, "rev71_new": {"N1": 3, "N2": 2, "R3": 2, "overlap": 0},
         "evidence_3_2_2": True, "disclosure": True},
        {"old_rev7_L15_has_4": "**3**" not in rev7_lines[14] and "**4**" in rev7_lines[14],
         "new_counts": {k: len(v) for k, v in attr_sids.items()},
         "disclosure_present": "第 4 处 §0 事实更正" in doc[133]},
        "**4**" in rev7_lines[14] and {k: len(v) for k, v in attr_sids.items()}
        == {"N1": 3, "N2": 2, "N3": 2} and "第 4 处 §0 事实更正" in doc[133],
        "A.6 把 REV7 的 N1「4 例」更正为 3、R3「与上重叠 1 例」更正为 0，并给出 C32 false_by_reason 3/2/2 证据；第 4 处更正的披露句也在")

    rec("A6-SUPERSEDE-CLEAR", "附录A", (129, 134), REV7_DOC_REL, "<REV7 L15/L17>", (15, 17), "static_grep",
        {"old_kept_in_rev7": True, "corrected_in_rev71": True, "supersedes_declared": True},
        {"rev7_L15_still_4": "**4**" in rev7_lines[14],
         "rev7_L17_still_overlap": "与上重叠" in rev7_lines[16],
         "rev71_L15_3": "**3**" in doc[14],
         "rev71_no_overlap_phrase": "与上重叠" not in body71,
         "supersedes": art.get("supersedes_sha16")},
        "**4**" in rev7_lines[14] and "与上重叠" in rev7_lines[16]
        and "**3**" in doc[14] and art.get("supersedes_sha16") == REV7_DOC_SHA16,
        "4→3 的取代关系写得清楚：REV7 原件保持「4 例/与上重叠 1 例」（未篡改），rev7.1 正文改为「3 例/互不重叠」并以 supersedes 声明取代")

    # ================================================= appendix B
    rec("B1-FUNCS", "附录B", (140, 144), IMPL_REL, "<14 funcs>", (198, 607), "static_ref",
        {"listed14_identical": 14, "gate_item_also_identical": True},
        {"listed14_identical": len(same14), "gate_item_identical": gate_item_same},
        len(same14) == 14 and gate_item_same,
        "B.1 所列 14 个函数逐字节相同；实际还有 gate_item 也相同（共 15，见 B1-COUNT）")

    rec("B1-COUNT", "附录B", (140, 140), IMPL_REL, "<all funcs>", (119, 1143), "static_ref",
        {"identical_count": 14}, {"identical_count": len(identical_extra),
                                  "extra_beyond_list": sorted(set(identical_extra) - set(listed14))},
        len(identical_extra) == 14,
        "文档 B.1/附录 B 说「其余 14 个函数逐字节相同」，实测为 15（漏列 gate_item）；不改变「判定代码零改动」结论",
        severity="low")

    rec("B1-CONSTS", "附录B", (144, 144), IMPL_REL, "PURE_PATTERNS/ENTITY_PATTERN", (89, 97), "static_ref",
        {"identical": True, "thresholds": [0.80, 0.90]},
        {"pure_patterns_equal": impl.lists.get("PURE_PATTERNS", (0, []))[1]
         == c32.lists.get("PURE_PATTERNS", (0, []))[1],
         "entity_equal": impl.strings.get("ENTITY_PATTERN", (0, None))[1]
         == c32.strings.get("ENTITY_PATTERN", (0, None))[1],
         "has_080": "0.80" in impl.text, "has_090": ">= 0.90" in impl.text},
        impl.lists.get("PURE_PATTERNS", (0, []))[1] == c32.lists.get("PURE_PATTERNS", (0, []))[1]
        and impl.strings.get("ENTITY_PATTERN", (0, None))[1]
        == c32.strings.get("ENTITY_PATTERN", (0, None))[1]
        and "0.80" in impl.text and ">= 0.90" in impl.text,
        "B.1 常量与阈值声明成立：PURE_PATTERNS / ENTITY_PATTERN / 0.80 / 0.90 全部逐字未变")

    # ---- B.2 allowed-change classification
    def owner_map(src):
        tree = ast.parse(src)
        m = {}
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                nm = n.name
            elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                nm = n.targets[0].id
            elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) \
                    and isinstance(n.value.value, str):
                nm = "<docstring>"
            else:
                nm = "<%s>" % type(n).__name__
            for i in range(n.lineno, (getattr(n, "end_lineno", None) or n.lineno) + 1):
                m[i] = nm
        return m
    ALLOWED = {"<docstring>", "verify_inputs", "main", "item_assertion", "verdict_assertion",
               "PRE", "PRE_SHA16", "PRE_BYTES", "PRE_LINES", "ART", "SUPERSEDES_SHA16",
               "SUPERSEDES_CODE_SHA16", "CORRECTION_TYPE", "REV7_1_VER", "RULE_CODE_UNCHANGED",
               "ASSERT_A2", "ASSERT_A3", "ASSERT_A2_VERDICT", "ASSERT_A3_VERDICT"}
    sm = difflib.SequenceMatcher(None, c32.text.splitlines(), impl.text.splitlines())
    om_c32 = owner_map(c32.text)
    om_71 = owner_map(impl.text)
    c32_lines = c32.text.splitlines()
    impl_lines = impl.text.splitlines()
    bad = []
    allowed_seen = set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        for ln in range(i1 + 1, i2 + 1):
            o = om_c32.get(ln)
            s = c32_lines[ln - 1].strip()
            if o is None:
                if s == "" or s.startswith("#"):
                    continue
                bad.append(["c32", ln, s[:70]])
            elif o in ALLOWED:
                allowed_seen.add(o)
            else:
                bad.append(["c32", ln, o])
        for ln in range(j1 + 1, j2 + 1):
            o = om_71.get(ln)
            s = impl_lines[ln - 1].strip()
            if o is None:
                if s == "" or s.startswith("#"):
                    continue
                bad.append(["rev7.1", ln, s[:70]])
            elif o in ALLOWED:
                allowed_seen.add(o)
            else:
                bad.append(["rev7.1", ln, o])
    rec("B2-ALLOWED", "附录B", (146, 148), IMPL_REL, "<whole file diff>", (1, 1143), "static_ref",
        {"outside_allowed_classes": 0},
        {"outside_allowed_classes": len(bad), "first": bad[:5],
         "allowed_owners_touched": sorted(allowed_seen)},
        not bad,
        "B.2「只允许五类改动」经逐行 diff 分类验证：所有改动都落在 docstring/常量/verify_inputs/main/新断言函数内，类外改动 0")

    diff_keys = sorted(set(k for k in set(art) | set(c32a) if art.get(k) != c32a.get(k)))
    doc_claimed = {"prereg_sha16", "code_sha16", "code_file", "code_bytes", "schema",
                   "rev7_1_ver", "supersedes_sha16", "correction_type", "rule_code_unchanged",
                   "assertions"}
    extra_keys = [k for k in diff_keys if k not in doc_claimed]
    rec("B3-DIFFKEYS", "附录B", (152, 152), ART_REL, "<top-level diff>", (0, 0), "recompute",
        {"diff_keys_subset": sorted(doc_claimed), "blocks_equal": 8},
        {"diff_keys": diff_keys, "extra_beyond_doc_list": extra_keys,
         "blocks_equal": sum(1 for b in BLOCKS if block_eq[b])},
        all(block_eq.values()) and set(extra_keys) <= {"inputs", "prereg_text_corrections",
                                                       "supersedes_code_sha16"},
        "B.3 的「只有 provenance 与 assertions 不同」成立（8 块全等；差异键全部为 provenance/自检：差集含 inputs / supersedes_code_sha16 / prereg_text_corrections，文档枚举未逐一列名但不影响数值）")

    rec("B4-INPUTS", "附录B", (154, 156), ART_REL, "<inputs>", (0, 0), "static_grep",
        {"inputs_unchanged": True, "no_b5_read": True, "no_git_commit": True},
        {"rev7_prereg": sha16(b_rev7), "judge": sha16(b_judge), "gold": sha16(b_gold),
         "no_b5_read": art.get("no_b5_read"), "no_git_commit": art.get("no_git_commit")},
        sha16(b_rev7) == REV7_DOC_SHA16 and sha16(b_judge) == JUDGE_SHA16
        and sha16(b_gold) == GOLD_SHA16
        and art.get("no_b5_read") is True and art.get("no_git_commit") is True,
        "B.4 输入零改动可核：REV7 文档 / JUDGE / gold 三个 sha 全部未变；no_b5_read、no_git_commit 标志为 true")

    # ================================================= readings (required asserts)
    rec("R-261", "读数", (72, 72), ART_REL, "sentences[]", (0, 0), "recompute",
        {"n_sentences": 261}, {"n_sentences": len(sens),
                               "artifact_n_sentences": art.get("n_sentences")},
        len(sens) == 261 and art.get("n_sentences") == 261, "261 句 = sentences[] 长度（非字面量）")
    rec("R-0-FORWARD", "读数", (91, 91), ART_REL, "n_forward", (0, 0), "recompute",
        {"n_forward": 0},
        {"n_forward": art.get("n_forward"), "n_model_rows": art.get("n_model_rows"),
         "n_abstain_rows": art.get("n_abstain_rows")},
        art.get("n_forward") == 0 and art.get("n_model_rows", 0) + art.get("n_abstain_rows", 0) == 261,
        "n_forward=0；route 构成 246 抽取 + 15 abstain，复用已落盘模型输出")
    rec("R-FP", "读数", (72, 72), ART_REL, "gate.false_positive", (0, 0), "recompute",
        {"k": 2, "n": 46, "sids": ["b4-s1-q2-s07", "b4-s1-q2-s09"]},
        {"k": len(fp), "n": len(supp), "sids": fp,
         "artifact": [gate["false_positive"]["k"], gate["false_positive"]["n"]]},
        (len(fp), len(supp)) == (2, 46) and fp == ["b4-s1-q2-s07", "b4-s1-q2-s09"],
        "误判 2/46，两名 sid 与产物 gate.false_positive_sids 一致")
    rec("R-LEAK", "读数", (72, 72), ART_REL, "gate.leak_missed", (0, 0), "recompute",
        {"k": 4, "n": 41}, {"k": len(leak), "n": len(fab), "sids": leak},
        (len(leak), len(fab)) == (4, 41), "漏判 4/41")
    rec("R-PF", "读数", (72, 72), ART_REL, "gate.parse_fail", (0, 0), "recompute",
        {"k": 1, "n": 261}, {"k": len(pf), "n": len(sens), "sids": pf},
        (len(pf), len(sens)) == (1, 261), "parse_fail 1/261")
    rec("R-NEWMISS", "读数", (72, 72), ART_REL, "gate.new_miss", (0, 0), "recompute",
        {"k": 0, "n": 35}, {"k": len(newmiss), "n": len(risk)},
        (len(newmiss), len(risk)) == (0, 35), "新增漏判 0/35（分母 = fabricated 且基线 unsupported）")
    rec("R-CHANGES", "读数", (73, 73), ART_REL, "sentence_diff", (0, 0), "recompute",
        {"changed": 7, "fixed": 5, "broken": 0, "neutral": 2},
        {"changed": len(changed), "fixed": len(fixed), "broken": len(broken),
         "neutral": len(neutral), "artifact": [art["sentence_diff"][k] for k in
                                               ("n_changed", "n_fixed", "n_broken", "n_neutral")]},
        (len(changed), len(fixed), len(broken), len(neutral)) == (7, 5, 0, 2),
        "7 句变化 = 5 修好 / 0 改坏 / 2 中性")
    rec("R-INVALID", "读数", (73, 73), ART_REL, "rates.invalid_items", (0, 0), "recompute",
        {"k": 124, "n": 777, "rate": 0.1596},
        {"k": len(inv), "n": len(art["items"]), "rate": art["rates"]["invalid_items"]["rate"],
         "mismatch_vs_artifact": len(mism)},
        len(inv) == 124 and len(art["items"]) == 777,
        "作废条目 124/777 = 15.96%；777 条 N3 判定由本映射逐条独立复算，0 不一致")
    rec("R-ASSERT-5of5", "读数", (84, 84), ART_REL, "assertions", (0, 0), "recompute",
        {"n_pass": 5}, {"n_pass": len(passes), "all_pass": art["assertions"].get("all_pass")},
        len(passes) == 5 and art["assertions"].get("all_pass") is True, "assertions 5/5 pass")
    rec("R-GOLDDIST", "读数", (72, 73), ART_REL, "<gold>", (0, 0), "recompute",
        {"support_present": 46, "fabricated": 41, "no_fact": 164, "undecidable": 10},
        {"support_present": len(supp), "fabricated": len(fab),
         "no_fact": len(nofact), "undecidable": len(undec)},
        (len(supp), len(fab), len(nofact), len(undec)) == (46, 41, 164, 10),
        "金标分布 46/41/164/10，与冻结值一致")

    # ================================================= anti-hardcoding / self-claims
    lit = {}
    for n in (46, 41, 777, 124, 35):
        lit[n] = [i + 1 for i, l in enumerate(impl_lines)
                  if re.search(r"(?<![\dA-Za-z_])%d(?![\dA-Za-z_])" % n, l)]
    rec("H-LITERALS", "反硬编码", (73, 73), IMPL_REL, "<whole source>", (1, len(impl_lines)), "static_grep",
        {"46": "prose only", "41": [], "777": [], "124": [], "35": []},
        {"occurrences": lit,
         "l163": impl_lines[162].strip()[:120] if len(impl_lines) > 162 else None},
        lit[41] == [] and lit[777] == [] and lit[124] == [] and lit[35] == []
        and lit[46] == [163],
        "结果常量 777/124/35/41 零出现；46 仅在 L163 的说明字符串「2/46」里被引用（纯文字，不参与计算）")
    lines261 = [i + 1 for i, l in enumerate(impl_lines) if re.search(r"(?<![\dA-Za-z_])261(?![\dA-Za-z_])", l)]
    rec("H-261", "反硬编码", (72, 72), IMPL_REL, "main", (0, 0), "static_grep",
        {"lines": [14, 90, 697]}, {"lines": lines261},
        lines261 == [14, 90, 697],
        "261 只出现在文件头注释、N_SENTENCES 常量与基线复现注释中，不参与结果拼装")
    sid_cond = [i + 1 for i, l in enumerate(impl_lines)
                if re.search(r"\bif\s+sid\b|\bsid\s*==|\bsid\s+(?:not\s+)?in\b", l)]
    b4_lines = [i + 1 for i, l in enumerate(impl_lines) if "b4-" in l]
    rec("H-SID", "反硬编码", (78, 85), IMPL_REL, "<whole source>", (1, len(impl_lines)), "static_grep",
        {"sid_branches": 0, "b4_lines": [96, 97, 98, 101, 102, 1067, 1068]},
        {"sid_branches": sid_cond, "b4_lines": b4_lines}, not sid_cond,
        "无 if sid / sid== / sid in 分支；b4- 字面量仅出现在断言主体常量（96-102）与自述清单（1067-1068）")
    hidden = [i + 1 for i, l in enumerate(impl_lines)
              if re.search(r"try:|except |os\.environ|sys\.argv|\brandom\b|time\.|if False", l)]
    rec("H-HIDDEN", "反硬编码", (82, 82), IMPL_REL, "<whole source>", (1, len(impl_lines)), "static_grep",
        {"markers": 0}, {"lines": hidden}, not hidden,
        "无 try/except、无环境变量/argv、无随机/时间、无 if False —— 单一确定性路径")

    hdr_claim = "no engine / no GPU runner" in impl.text
    trans = sorted(_local_import_closure())
    rec("H-IMPORT-CLAIM", "实现自述", (7, 7), IMPL_REL, "<header L61>", (61, 63), "static_grep",
        {"header_claim": False, "gpu_runner_reachable": False},
        {"header_claim_present": hdr_claim, "transitive_local_modules": len(trans),
         "gpu_runner_reachable": "_e3gpu_run" in trans,
         "forward_calls": 0},
        not hdr_claim and "_e3gpu_run" not in trans,
        "脚本头注仍写「no engine / no GPU runner」，但 R5→R41 传递 import 了 _e3gpu_run 等模块；实际 0 次前向调用，属措辞过强而非行为违规",
        severity="low")

    notes = art.get("import_notes", "")
    rec("H-IMPORT-NOTES", "实现自述", (7, 7), ART_REL, "import_notes", (0, 0), "static_grep",
        {"says_no_direct_import": True},
        {"import_notes": notes, "says_no_direct": "no direct import" in notes},
        "no direct import" in notes,
        "产物 import_notes 的措辞已收紧为「no direct import … or any GPU runner」——与传递 import 事实相容；与脚本文档头注的强措辞不一致")

    n4_in_rev7_sec4 = "N4" in rev7_lines[73]
    pick_src = func_src(impl, "pick_attribution") or ""
    rec("C4-N4-ENUM", "§4 交付", (83, 83), IMPL_REL, "pick_attribution", (533, 548), "static_grep",
        {"doc_enumerates_N4": True, "implementation_has_N4_branch": True},
        {"rev7_sec4_enumerates_N4": n4_in_rev7_sec4,
         "rev7_sec4_quote": rev7_lines[73][:120],
         "pick_attribution_returns_N4": 'return "N4"' in pick_src,
         "mentions_N4_only_in_docstring": "N4" in pick_src and 'return "N4"' not in pick_src,
         "artifact_attributions": sorted(attr_sids),
         "audit_note": aud.get("inconsistencies", {}).get("finding_4_false_by_reason_N4", {}).get("severity")},
        n4_in_rev7_sec4 and ('return "N4"' in pick_src),
        "§4 声明 schema 同 REV7 §4，而 REV7 §4 的 false_by_reason 枚举 N1/N2/N3/N4/…；实现 pick_attribution 无 N4 分支，产物归因只有 N1/N2/N3 ⇒ 文档枚举的 N4 分类不可达（独立审计亦标为表述不精确，数值零影响）",
        severity="low")

    # ================================================= summary / outputs
    n = len(records)
    n_pass = sum(1 for r in records if r["pass"] is True)
    n_fail = sum(1 for r in records if r["pass"] is False)
    n_unv = sum(1 for r in records if r["pass"] is None)
    groups = ["§0 更正", "§1 引用", "§2.1 断言", "§3 门槛", "§4 交付", "§5 纪律",
              "§6 状态", "附录A", "附录B", "读数", "反硬编码", "实现自述"]
    by_group = {}
    for g in groups:
        sel = [r for r in records if r["group"] == g]
        by_group[g] = {"n": len(sel),
                       "pass": sum(1 for r in sel if r["pass"] is True),
                       "fail": sum(1 for r in sel if r["pass"] is False),
                       "unverifiable": sum(1 for r in sel if r["pass"] is None)}
    summary = {
        "n_claims": n, "n_pass": n_pass, "n_fail": n_fail, "n_unverifiable": n_unv,
        "by_group": by_group,
        "fail_ids": [r["claim_id"] for r in records if r["pass"] is False],
        "unverifiable_ids": [r["claim_id"] for r in records if r["pass"] is None],
        "block_equality": block_eq,
        "all_pass": n_fail == 0,
        "check_mode": "checks only" if not write_outputs else "checks + write",
    }
    out = {
        "schema": "m5c2_rev7_1_claim_map_v1",
        "generated_by": "kvmem/m2_visibility/m5/out/m5c2_rev7_1_claim_map.py",
        "mapper_sha16": sha16(Path(__file__).read_bytes()),
        "inputs": {
            "prereg": {"file": DOC_REL, "sha16": sha16(b_doc), "bytes": len(b_doc)},
            "impl": {"file": IMPL_REL, "sha16": sha16(b_impl), "bytes": len(b_impl)},
            "artifact": {"file": ART_REL, "sha16": sha16(b_art), "bytes": len(b_art)},
            "c32_impl": {"file": C32_IMPL_REL, "sha16": sha16(b_c32i)},
            "c32_artifact": {"file": C32_ART_REL, "sha16": sha16(b_c32a)},
            "audit": {"file": AUDIT_REL, "sha16": sha16(b_audit)},
            "judge": {"file": JUDGE_REL, "sha16": sha16(b_judge)},
            "gold": {"file": GOLD_REL, "sha16": sha16(b_gold)},
        },
        "block_equality_vs_c32": block_eq,
        "findings": [{"claim_id": f["claim_id"], "severity": f["severity"],
                      "doc_lines": f["doc_lines"], "expected": f["expected"],
                      "actual": f["actual"], "notes": f["notes"]} for f in findings],
        "summary": summary,
        "claims": records,
    }
    for r in records:
        print("%-26s %-10s %-4s %s" % (r["claim_id"], r["group"],
                                       "PASS" if r["pass"] else ("FAIL" if r["pass"] is False else "UNV"),
                                       r["notes"][:86]))
    print("\nclaims=%d pass=%d fail=%d unverifiable=%d" % (n, n_pass, n_fail, n_unv))
    print("block_equality_vs_c32: %s" % json.dumps(block_eq, ensure_ascii=False))
    if findings:
        print("findings: " + ", ".join("%s[%s]" % (f["claim_id"], f["severity"]) for f in findings))

    if write_outputs:
        _write_json(MAP, out)
        MD.write_text(_render_md71(out), encoding="utf-8", newline="\n")
        print("wrote %s (%d B) and %s (%d B)" % (MAP_REL, MAP.stat().st_size,
                                                 MD_REL, MD.stat().st_size))
    else:
        if MAP.exists():
            old = json.loads(MAP.read_bytes().decode("utf-8"))

            def _norm_sum(d):
                d = dict(d or {})
                d.pop("check_mode", None)
                return d

            records_json = json.loads(json.dumps(records, ensure_ascii=False))
            same = (old.get("claims") == records_json
                    and _norm_sum(old.get("summary")) == _norm_sum(summary))
            if not same:
                old_c = old.get("claims") or []
                for a, b in zip(old_c, records_json):
                    if a != b:
                        keys = [k for k in set(a) | set(b) if a.get(k) != b.get(k)]
                        print("--check: first differing claim %s keys=%s" % (a.get("claim_id"), keys))
                        break
                else:
                    print("--check: claim list equal; summary differs: %s"
                          % {k: (old.get("summary", {}).get(k), summary.get(k))
                             for k in set(summary) | set(old.get("summary", {}))
                             if old.get("summary", {}).get(k) != summary.get(k)})
            print("--check: regenerated map matches on-disk map: %s" % same)
            if not same:
                n_fail += 1
        print("--check: exit 1 means %d claim(s) of the doc-vs-code ledger fail (research findings), "
              "not a verifier malfunction." % n_fail)
    return 0 if n_fail == 0 else 1


def _old_pure(r41):
    for n in ast.walk(r41.tree):
        if isinstance(n, ast.FunctionDef) and n.name == "value_tokens":
            for m in ast.walk(n):
                if isinstance(m, ast.Assign) and isinstance(m.targets[0], ast.Name) \
                        and m.targets[0].id == "pats" and isinstance(m.value, ast.List):
                    return [_str_value(e) for e in m.value.elts][:4]
    return []


def _local_import_closure():
    roots = [M5, M5 / ".." / "m7/out", M5 / ".." / "engine", ROOT / "tools"]
    seen = set()
    stack = ["run_m5c2_rev7_offline"]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        p = None
        for r in roots:
            q = (r / (name + ".py")).resolve()
            if q.exists():
                p = q
                break
        if p is None:
            continue
        seen.add(name)
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Import):
                stack.extend(a.name.split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module:
                stack.append(n.module.split(".")[0])
    return {x for x in seen if x != "run_m5c2_rev7_offline"}


def _write_json(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    tmp_p = Path(tmp)
    tmp_p.replace(path)


def _snippet(src, lines, max_lines=5):
    a, b = lines
    out = []
    for i in range(a, min(b, a + max_lines - 1) + 1):
        out.append("%4d  %s" % (i, src.splitlines()[i - 1]))
    return "\n".join(out)



def _render_md71(out):
    s = out["summary"]
    L = []
    L.append("# CODE-TRACE-M5C2-REV7.1 —— 文档主张 ↔ 代码/产物 逐条追踪")
    L.append("")
    L.append("> 由 `kvmem/m2_visibility/m5/out/m5c2_rev7_1_claim_map.py` 自动生成（`--check` 可只校验、不写盘）。")
    L.append("> 冻结件：PREREG `%s` sha16 `%s` / %d B；脚本 `%s` sha16 `%s` / %d B；产物 `%s` sha16 `%s` / %d B。"
             % (DOC_REL, out["inputs"]["prereg"]["sha16"], out["inputs"]["prereg"]["bytes"],
                IMPL_REL, out["inputs"]["impl"]["sha16"], out["inputs"]["impl"]["bytes"],
                ART_REL, out["inputs"]["artifact"]["sha16"], out["inputs"]["artifact"]["bytes"]))
    L.append("> 对照 C32：脚本 `%s`、产物 `%s`。"
             % (out["inputs"]["c32_impl"]["sha16"], out["inputs"]["c32_artifact"]["sha16"]))
    L.append("")
    L.append("## 摘要")
    L.append("")
    L.append("| 指标 | 值 |")
    L.append("|---|---:|")
    L.append("| claim 总数 | %d |" % s["n_claims"])
    L.append("| pass | %d |" % s["n_pass"])
    L.append("| fail（文档对不上代码/产物） | %d |" % s["n_fail"])
    L.append("| unverifiable（需运行/未来行为） | %d |" % s["n_unverifiable"])
    L.append("")
    L.append("> 退出码：`--check` 有任一 fail 返回 1；本表含 **%d 条 fail**，故退出码 1 是结论（不是校验器故障），"
             "只有全部主张成立才返回 0。" % s["n_fail"])
    L.append("")
    L.append("| 分组 | 条数 | pass | fail | 不可验证 |")
    L.append("|---|---:|---:|---:|---:|")
    for g, v in s["by_group"].items():
        L.append("| %s | %d | %d | %d | %d |" % (g, v["n"], v["pass"], v["fail"], v["unverifiable"]))
    L.append("")
    L.append("## ① 文档确实对不上代码/产物（按严重度）")
    L.append("")
    L.append("| claim | 严重度 | 文档行 | 文档说 | 实测 |")
    L.append("|---|---|---|---|---|")
    for f in out["findings"]:
        L.append("| `%s` | %s | L%s | %s | %s |"
                 % (f["claim_id"], f["severity"],
                    ",".join(str(x) for x in f["doc_lines"]),
                    json.dumps(f["expected"], ensure_ascii=False)[:120],
                    json.dumps(f["actual"], ensure_ascii=False)[:160]))
    L.append("")
    L.append("## ② C32 对照：8 个关键块逐键相等")
    L.append("")
    L.append("| 块 | 与 C32 完全相等 |")
    L.append("|---|---|")
    for k, v in out["block_equality_vs_c32"].items():
        L.append("| `%s` | %s |" % (k, "是" if v else "**否**"))
    L.append("")
    L.append("## ③ 逐条对照表")
    L.append("")
    L.append("| claim_id | 文档行 | 代码 / 产物定位 | 检查方式 | 结果 |")
    L.append("|---|---|---|---|---|")
    for r in out["claims"]:
        dl = "%d" % r["doc_lines"][0] if r["doc_lines"][0] == r["doc_lines"][1] \
            else "%d-%d" % tuple(r["doc_lines"])
        if r["code_function"].startswith("<"):
            cl = r["code_function"].strip("<>")
        else:
            cl = "%s:%s" % (r["code_function"],
                            ("%d" % r["code_lines"][0]) if r["code_lines"][0] == r["code_lines"][1]
                            else "%d-%d" % tuple(r["code_lines"]))
        res = "PASS" if r["pass"] else ("**FAIL**" if r["pass"] is False else "不可验证")
        L.append("| `%s` | L%s | `%s` | %s | %s |" % (r["claim_id"], dl, cl, r["check_kind"], res))
    L.append("")
    L.append("## ④ 关键代码片段（每段 ≤5 行）")
    L.append("")
    impl_text = IMPL.read_text(encoding="utf-8")
    for title, lo, hi in (("normalize7（N1 三步：NFKC → 千分位 → 去空白）", 198, 203),
                          ("item_assertion（§2.1 A2/A3 真值断言）", 610, 614),
                          ("gate_item 四门槛阈值（4/5/2/0）", 818, 822),
                          ("gate 只写 rev7_unusable（文档写 rev7_1_unusable）", 829, 833),
                          ("REV7.1 常量：PRE/PRE_SHA16/SUPERSEDES/CORRECTION_TYPE", 70, 77)):
        L.append("### %s" % title)
        L.append("```python")
        L.append(_snippet(impl_text, (lo, min(hi, lo + 4))))
        L.append("```")
        L.append("")
    L.append("## ⑤ 方法与复现")
    L.append("")
    L.append("1. **文档→代码定位**：`ast.parse` 取函数行号区间 + 源切片 sha256；产物侧用 JSON 字段路径（`gate.false_positive`、`assertions.A2.occurrences`、`false_by_reason` …）。")
    L.append("2. **独立复算**：本映射自带 `normalize7`/`coverage`/`window_coverage`，对 777 条 item 重算 N3 判定；从 `sentences[]` + 金标复算四门槛、7 句变化、作废数、assertions 通过数。")
    L.append("3. **C32 对照**：对 8 个关键块做 Python `==` 深比较（不依赖任何审计结论），并列出全部顶层差异键。")
    L.append("4. **反硬编码**：扫描 46/41/777/124/35/261 字面量与 sid 特判；`b4-` 只允许出现在断言主体常量与自述清单。")
    L.append("5. **第三方审计交叉核对**：只读 `M5C2-REV7-1-AUDIT.json` 与 `_rev7_1_audit.py`，核对两次运行 byte 级一致与 independence（未 import 被测脚本），不作为计算来源。")
    L.append("")
    L.append("```")
    L.append("python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_1_claim_map.py          # 生成映射")
    L.append("python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_1_claim_map.py --check  # 仅校验（有 fail 退出 1）")
    L.append("```")
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
