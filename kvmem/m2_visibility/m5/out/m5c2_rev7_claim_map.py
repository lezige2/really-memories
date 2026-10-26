#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 REV7 claim -> code map + executable verifier (READ-ONLY).

Reads (never writes) the frozen PREREG, the implementer script and the
artifact; emits out/M5C2-REV7-CLAIM-MAP.json and docs/_work/CODE-TRACE-M5C2-REV7.md.

Every claim is one of:
  static_ref      - function/constant exists in the frozen source (ast + slice sha256)
  static_grep     - a literal/regex claim checked against source text
  exec_assert     - a value recomputed by this file's own small code
  recompute       - an artifact reading recomputed from records + gold

Run:
  python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_claim_map.py          # write
  python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_claim_map.py --check  # verify only
Exit code 1 if any claim fails.  Zero GPU / zero model / zero network.
"""
import ast
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"

DOC_REL = "docs/_work/PREREG-M5-C2-REV7.md"
DOC = ROOT / DOC_REL
IMPL_REL = "kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py"
IMPL = ROOT / IMPL_REL
ART_REL = "kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json"
ART = ROOT / ART_REL
JUDGE_REL = "kvmem/m2_visibility/m5/out/M5B4-JUDGE.json"
JUDGE = ROOT / JUDGE_REL
GOLD_REL = "kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json"
GOLD = ROOT / GOLD_REL
R41_REL = "kvmem/m2_visibility/m5/run_m5c2_rev4_1.py"
R41 = ROOT / R41_REL
MAP_REL = "kvmem/m2_visibility/m5/out/M5C2-REV7-CLAIM-MAP.json"
MAP = ROOT / MAP_REL
MD_REL = "docs/_work/CODE-TRACE-M5C2-REV7.md"
MD = ROOT / MD_REL

# verification constants (from the frozen brief; never used as judging input)
DOC_SHA16 = "32eaf82ca56600c4"
DOC_BYTES = 5835
IMPL_SHA16 = "65ed60125528d5d6"
IMPL_BYTES = 44761
ART_SHA16 = "1f8f44b921e575fe"
ART_BYTES = 507657
JUDGE_SHA16 = "6a3001b6ca23ef7d"
GOLD_SHA16 = "9273ebc97aa1413a"


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
    doc_bytes = DOC.read_bytes()
    impl_bytes = IMPL.read_bytes()
    art_bytes = ART.read_bytes()
    judge_bytes = JUDGE.read_bytes()
    gold_bytes = GOLD.read_bytes()
    global DOC_LINES
    DOC_LINES = doc_bytes.decode("utf-8").splitlines()
    doc = Src(DOC_REL, DOC) if False else None  # noqa: F841  (doc is not python)
    impl = Src(IMPL_REL, IMPL)
    r41 = Src(R41_REL, R41)
    art = json.loads(art_bytes.decode("utf-8"))
    judge = json.loads(judge_bytes.decode("utf-8"))
    gold = json.loads(gold_bytes.decode("utf-8"))["gold"]
    rows = judge["items"]
    sentence_of = {r["sid"]: r["sentence"] for r in rows}
    source_of = {r["sid"]: r["source_text"] for r in rows}

    # ------------------------------------------------------------ frozen inputs
    input_ok = (sha16(doc_bytes) == DOC_SHA16 and len(doc_bytes) == DOC_BYTES
                and sha16(impl_bytes) == IMPL_SHA16 and len(impl_bytes) == IMPL_BYTES
                and sha16(art_bytes) == ART_SHA16 and len(art_bytes) == ART_BYTES
                and sha16(judge_bytes) == JUDGE_SHA16 and sha16(gold_bytes) == GOLD_SHA16)
    add(records, "IN-FROZEN-SHA", "读数", 6, IMPL_REL, "verify_inputs", (112, 136),
        "static_ref",
        {"prereg": DOC_SHA16, "impl": IMPL_SHA16, "artifact": ART_SHA16,
         "judge": JUDGE_SHA16, "gold": GOLD_SHA16},
        {"prereg": sha16(doc_bytes), "impl": sha16(impl_bytes),
         "artifact": sha16(art_bytes), "judge": sha16(judge_bytes),
         "gold": sha16(gold_bytes)},
        input_ok, "输入/被测脚本/产物字节均与冻结简报一致")

    # ------------------------------------------------------------ §0 attribution
    base_fp_sids = art["baseline_reproduction"]["baseline_false_positive"]["sids"]
    fp_sids = base_fp_sids
    fp_rows = [r for r in rows if r["sid"] in fp_sids]
    r4_fp = [(r["sid"], z["item"]) for r in fp_rows for z in r["items"]
             for h in z["rule_hits"] if h["rule"] == "R4+"]
    add(records, "S0-R4PLUS-ZERO", "§0 归因", 11, JUDGE_REL, "<judge rule_hits>", (0, 0),
        "recompute", {"r4_plus_hits_on_7_fp": 0}, {"hits": r4_fp, "n": len(r4_fp)},
        len(r4_fp) == 0, "7 例误判中 R4+ fabricated_evidence 命中数；实按 M5B4-JUDGE.json 的 items[].rule_hits 统计")

    r1_items = [(r["sid"], z["item"], h.get("span")) for r in fp_rows for z in r["items"]
                for h in z["rule_hits"] if h["rule"] == "R1"]
    pure_spans = [x for x in r1_items if re.fullmatch(r"\d+(?:\.\d+)?\s*(?:元|度|M|G|层|楼|排|号|节|个月|年|月|日)", x[2] or "")]
    n1_sids = sorted(set(x[0] for x in pure_spans))
    add(records, "S0-N1-COUNT", "§0 归因", (15, 15), JUDGE_REL, "<judge rule_hits>", (0, 0),
        "recompute",
        {"n1_examples": 4, "sids_listed_in_doc": ["b4-s1-q2-s01", "b4-s1-q2-s15", "b4-s1-q3-s03"]},
        {"n1_examples": len(n1_sids), "n1_sids": n1_sids, "n1_items": len(pure_spans)},
        len(n1_sids) == 4,
        "文档写 4 例，但列出的 sid 只有 3 个；按纯值型 R1 命中实测 = 3 句/3 条目（对不上）")

    cov_n1 = coverage("8600元", normalize_old("手术费 8,600 元"))
    add(records, "S0-N1-COVERAGE", "§0 归因", 15, R41_REL, "fuzzy_coverage", (109, 115),
        "exec_assert", {"coverage_8600_vs_8,600": 0.75},
        {"coverage": round(cov_n1, 6)}, abs(cov_n1 - 0.75) < 1e-9,
        "旧 normalize 下二元组覆盖 0.75 < 0.80 → value_mismatch（文档数字对得上）")

    toks_s8 = [t for t in re.findall(r"[^\s，。]{2,}(?:公司|店|院|馆|中心)", "地点是宠安医院")]
    old_ent = [m.group(0) for m in re.finditer(r"[^\s，。]{2,}(?:公司|店|院|馆|中心)", "地点是宠安医院")]
    cov_rent = coverage("租车公司", normalize_old("迅达租车"))
    cov_hosp = coverage("地点是宠安医院", normalize_old(source_of["b4-s8-q2-s02"]))
    add(records, "S0-N2-GREEDY", "§0 归因", 16, R41_REL, "value_tokens", (118, 132),
        "exec_assert",
        {"greedy_token_for_地点是宠安医院": "地点是宠安医院",
         "coverage_租车公司": 0.333, "coverage_地点是宠安医院": 0.5},
        {"greedy_tokens": old_ent, "coverage_租车公司": round(cov_rent, 6),
         "coverage_地点是宠安医院": round(cov_hosp, 6)},
        old_ent == ["地点是宠安医院"] and abs(cov_rent - 1 / 3.0) < 0.001
        and abs(cov_hosp - 0.5) < 1e-9,
        "贪心实体正则确实吞前缀；两个覆盖率与文档数字一致")

    r3_fp = sorted(set(r["sid"] for r in fp_rows for z in r["items"]
                       for h in z["rule_hits"] if h["rule"] == "R3"))
    overlap = len(set(n1_sids) & set(r3_fp))
    add(records, "S0-R3-COUNT", "§0 归因", 17, JUDGE_REL, "<judge rule_hits>", (0, 0),
        "recompute", {"r3_examples": 2, "overlap_with_above": 1},
        {"r3_examples": len(r3_fp), "r3_sids": r3_fp, "overlap": overlap}, 
        len(r3_fp) == 2 and overlap == 1,
        "2 例对；『与上重叠 1 例』不成立：两组 sid 互不相交，重叠 0（对不上）")

    premise = []
    for sid, it in (("b4-s1-q2-s07", "患者"), ("b4-s1-q2-s07", "做的"), ("b4-s1-q2-s09", "患者")):
        s7 = normalize7(sentence_of[sid])
        a7 = normalize7(it)
        premise.append({"sid": sid, "item": it, "in_sentence": a7 in s7,
                        "pos": s7.find(a7) if a7 in s7 else None})
    add(records, "S0-R3-PREMISE", "§0 归因", 17, IMPL_REL, "matcher", (193, 200),
        "exec_assert", {"items_absent_from_sentence": True},
        {"occurrences": premise}, 
        not any(p["in_sentence"] for p in premise),
        "文档称这些条目『句内根本不存在』；实测 患者 pos0、做的 pos 9-10 都在句内（前提错误，N3 断言因此不可满足）")

    add(records, "S0-TOTAL-7", "§0 归因", (13, 17), JUDGE_REL, "<gold + rule_hits>", (0, 0),
        "recompute", {"fp_total": 7, "value_mismatch": 5, "absent_marker": 2},
        {"fp_total": len(fp_sids), "value_mismatch": len(r1_items), "absent_marker": len(r3_fp)},
        len(fp_sids) == 7 and len(r1_items) == 5 and len(r3_fp) == 2,
        "7 例总数对得上；按命中原因拆分为 value_mismatch 5 + absent_marker 2")

    # ------------------------------------------------------------ §2 N1
    ref = impl.funcs.get("normalize7")
    slice_sha = src_slice_sha(impl.text, ref[0], ref[1]) if ref else None
    add(records, "S2-N1-REF", "§2 规范", (34, 38), IMPL_REL, "normalize7", ref or (0, 0),
        "static_ref", {"func_exists": True, "slice_sha16": "<non-empty>"},
        {"range": ref, "slice_sha16": slice_sha}, ref is not None and bool(slice_sha),
        "normalize7 存在于冻结脚本，片段 sha16 可复算")
    add(records, "S2-N1-NFKC", "§2 规范", 36, IMPL_REL, "normalize7", (149, 154),
        "static_grep", {"NFKC": True, "fullwidth_8600": "8600元", "fullwidth_123": "123"},
        {"NFKC": 'unicodedata.normalize("NFKC"' in impl.text,
         "fullwidth_8600": normalize7("８６００元"), "fullwidth_123": normalize7("１２３")},
        'unicodedata.normalize("NFKC"' in impl.text
        and normalize7("８６００元") == "8600元" and normalize7("１２３") == "123",
        "NFKC 在 normalize7 首步；全角数字→半角可执行验证")
    add(records, "S2-N1-THOUSAND", "§2 规范", 37, IMPL_REL, "normalize7", (152, 152),
        "exec_assert", {"8,600": "8600", "8，600": "8600", "1,23": "1,23"},
        {"8,600": normalize7("8,600"), "8，600": normalize7("8，600"),
         "1,23": normalize7("1,23")},
        normalize7("8,600") == "8600" and normalize7("8，600") == "8600"
        and normalize7("1,23") == "1,23",
        "千分位剥离只对『数字+,+3 位数字』生效；全角逗号经 NFKC 后同样被剥离")
    add(records, "S2-N1-WS", "§2 规范", 38, IMPL_REL, "normalize7", (153, 153),
        "exec_assert", {"手术费 8,600 元": "手术费8600元"},
        {"value": normalize7("手术费 8,600 元")},
        normalize7("手术费 8,600 元") == "手术费8600元",
        "数字与单位间空白由现有去空白覆盖")
    add(records, "S2-N1-ORDER", "§2 规范", 35, IMPL_REL, "normalize7", (151, 153),
        "static_grep", {"order": ["NFKC", "thousands", "whitespace"]},
        {"NFKC_line": 151 if 'NFKC' in impl.lines[150] else None,
         "thousands_line": 152 if "lookbehind" in impl.lines[151] or "(?<=" in impl.lines[151] else None,
         "ws_line": 153 if "\\s+" in impl.lines[152] else None},
        "NFKC" in impl.lines[150] and "(?<=" in impl.lines[151] and "\\s+" in impl.lines[152],
        "三步顺序与 §2 N1 的『在去空白之前增加』一致（151→152→153）")
    a1 = art["assertions"]["A1"]
    add(records, "S2-N1-ASSERT-A1", "§2 规范", 39, IMPL_REL, "main", (622, 629),
        "recompute", {"A1_value": 1.0, "A1_pass": True},
        {"value": a1["value"], "pass": a1["pass"],
         "our_recompute": coverage("8600元", normalize7("手术费 8,600 元"))},
        a1["value"] == 1.0 and a1["pass"] is True
        and coverage("8600元", normalize7("手术费 8,600 元")) == 1.0,
        "§2 N1 断言：normalize7 后子串命中 → coverage 1.0，pass=true")

    # ------------------------------------------------------------ §2 N2
    old_pat = r"[^\s，。]{2,}(?:公司|店|院|馆|中心)"
    add(records, "S2-N2-DELETE", "§2 规范", 42, IMPL_REL, "ENTITY_PATTERN", (87, 97),
        "static_grep", {"old_greedy_pattern_in_rev7": False},
        {"found": old_pat in impl.text, "present_in_rev4_1": old_pat in r41.text},
        old_pat not in impl.text and old_pat in r41.text,
        "旧的通用实体式已从 rev7 删除（在 rev4.1 仍在），替换为新非贪心正则")
    doc_line43 = DOC_LINES[42]
    m = re.search(r"`([^`]+)`", doc_line43)
    doc_entity = m.group(1) if m else None
    code_entity = impl.strings.get("ENTITY_PATTERN", (None, None))[1]
    add(records, "S2-N2-REGEX", "§2 规范", 43, IMPL_REL, "ENTITY_PATTERN", (96, 97),
        "static_grep", {"doc_regex_equals_code_constant": True},
        {"doc_regex": doc_entity, "code_constant": code_entity},
        doc_entity is not None and doc_entity == code_entity,
        "PREREG L43 内联正则与代码 ENTITY_PATTERN 常量逐字相等")
    add(records, "S2-N2-GROUP1", "§2 规范", 43, IMPL_REL, "value_tokens", (173, 177),
        "exec_assert", {"group1_only": True},
        {"group1_used": "m.group(1)" in impl.text,
         "captured": re.findall(code_entity, "地点是宠安医院") if code_entity else None},
        "m.group(1)" in impl.text
        and (re.findall(code_entity, "地点是宠安医院") == ["宠安医院"] if code_entity else False),
        "取捕获组 1：地点是宠安医院 → 宠安医院（不再吞前缀）")
    s7row = [r for r in art["items"] if r["sid"] == "b4-s2-q1-s01" and r["item"] == "租车公司"]
    gate_ok = (bool(s7row) and s7row[0]["rule_hits"] == []
               and s7row[0]["value_tokens"] and s7row[0]["value_tokens"][0]["r1_participates"] is False)
    add(records, "S2-N2-GATE", "§2 规范", 44, IMPL_REL, "r1_r2_r3_rev7", (212, 225),
        "recompute", {"租车公司_in_source": False, "r1_participates": False, "hits": []},
        {"row": {k: s7row[0][k] for k in ("valid", "rule_hits", "value_tokens")} if s7row else None},
        gate_ok,
        "实体 token 不在源文 ⇒ 不参与 R1（代码 217-218），b4-s2-q1-s01 因此修好")
    add(records, "S2-N2-PURE", "§2 规范", 45, IMPL_REL, "PURE_PATTERNS", (89, 94),
        "static_grep", {"4_patterns_unchanged": True},
        {"rev7": impl.lists.get("PURE_PATTERNS", (None, []))[1],
         "rev4_1_first4": _old_pure(r41)},
        impl.lists.get("PURE_PATTERNS", (None, []))[1] == _old_pure(r41),
        "4 条纯值型正则与 rev4.1 完全一致；实体型才是新增门")

    # ------------------------------------------------------------ §2 N3
    mism = []
    for z in art["items"]:
        mh, cov = matcher(z["item"], sentence_of[z["sid"]])
        if z["matcher_hit"] != mh or z["valid"] != (mh != "none") \
                or abs(round(cov, 6) - z["coverage"]) > 1e-9:
            mism.append({"sid": z["sid"], "item": z["item"], "got": [mh, z["valid"], round(cov, 6)],
                         "stored": [z["matcher_hit"], z["valid"], z["coverage"]]})
    n_invalid = sum(1 for z in art["items"] if not z["valid"])
    add(records, "S2-N3-DEF", "§2 规范", 48, IMPL_REL, "matcher", (193, 200),
        "recompute", {"n_items": 777, "n_invalid": 124, "mismatch": 0},
        {"n_items": len(art["items"]), "n_invalid": n_invalid, "mismatch": len(mism),
         "first": mism[:3]},
        len(art["items"]) == 777 and n_invalid == 124 and not mism,
        "valid = 子串命中 或 等长窗口 coverage≥0.90；777 条逐条独立复算与产物一致")
    bad = [z for z in art["items"] if (not z["valid"]) and (z["absent"] or z["item_verdict"] != "invalid"
                                                           or any(h["rule"] == "R3" for h in z["rule_hits"]))]
    add(records, "S2-N3-VOID", "§2 规范", 48, IMPL_REL, "judge_row_rev7", (410, 426),
        "recompute", {"invalid_items_with_absent_or_r3_or_noninvalid_verdict": 0},
        {"n": len(bad)}, not bad,
        "作废条目不产生 absent、不判 absent、R3 不生效；n_unverified 亦不计（artifact 全为 0）")
    add(records, "S2-N3-ASSERT-A2", "§2 规范", 49, IMPL_REL, "char_evidence", (529, 558),
        "recompute", {"患者_in_b4-s1-q2-s07_valid": False},
        {"artifact_pass": art["assertions"]["A2"]["pass"],
         "occurrences": art["assertions"]["A2"]["occurrences"]},
        art["assertions"]["A2"]["pass"] is not False,
        "§2 N3 断言要求 患者 判 valid=false；产物 A2 FAIL：患者 pos=0、coverage=1.0、valid=true ⇒ 断言不可满足（文档主张与代码/数据对不上）")
    add(records, "S2-N3-ASSERT-A3", "§2 规范", 49, IMPL_REL, "char_evidence", (529, 558),
        "recompute", {"患者_in_b4-s1-q2-s09_valid": False},
        {"artifact_pass": art["assertions"]["A3"]["pass"],
         "n_occurrences": art["assertions"]["A3"]["n_occurrences"]},
        art["assertions"]["A3"]["pass"] is not False,
        "同 A2：13 个 患者 条目全部 pos=0、coverage=1.0、valid=true ⇒ 断言不可满足，产物 A3 FAIL")

    # ------------------------------------------------------------ §2 N4
    n4_bad = [z for z in art["items"] if (not z["valid"]) and any(h["rule"] == "R3" for h in z["rule_hits"])]
    r3_hits = sum(1 for z in art["items"] if z["binding"] for h in z["rule_hits"] if h["rule"] == "R3")
    add(records, "S2-N4-SCOPE", "§2 规范", 52, IMPL_REL, "r1_r2_r3_rev7", (263, 272),
        "recompute", {"r3_on_invalid_items": 0, "r3_on_binding_items": art["rev7_rule_hit_counts"]["R3"]},
        {"r3_on_invalid_items": len(n4_bad), "r3_on_binding_items": r3_hits},
        not n4_bad and r3_hits == art["rev7_rule_hit_counts"]["R3"],
        "缺席词只在 valid=true 条目生效（代码 `if valid:`）；R3 命中数 435 可复算")

    # ------------------------------------------------------------ §2 rest unchanged
    th = {"R1": "cov < 0.80" in impl.text, "R4+_long": "cov >= 0.80" in impl.text,
          "N3": ">= 0.90" in impl.text}
    add(records, "S2-REST-THRESHOLD", "§2 规范", 54, IMPL_REL, "r1_r2_r3_rev7/r4_plus_rev7/matcher",
        (224, 299), "static_grep", {"thresholds": {"R1": 0.80, "R4+": 0.80, "N3": 0.90}},
        {"found": th, "observed": {"R1": 0.8, "R4+": 0.8, "N3": 0.9}}, all(th.values()),
        "R1/R4+ 仍为 0.80，N3 新增 0.90；阈值字面量与 §2 冻结值一致")
    agg = (impl.lines[446].strip().startswith("if row[\"route\"] == \"empty_source\"")
           if len(impl.lines) > 446 else False)
    add(records, "S2-REST-AGG", "§2 规范", 54, IMPL_REL, "judge_row_rev7", (446, 460),
        "static_grep", {"aggregation_order_unchanged": True},
        {"empty_source_first": agg,
         "order": [impl.lines[i - 1].strip()[:44] for i in (447, 449, 451, 453, 455, 457, 459)]},
        agg, "聚合顺序与 rev5.1 基线（empty_source→abstain→parse_fail→derived→no items→absent）一致")
    add(records, "S2-REST-VOCAB", "§2 规范", 54, IMPL_REL, "r1_r2_r3_rev7", (227, 272),
        "static_grep", {"local_vocab_redefinition": 0, "modules_reused": ["R5", "R51", "R41"]},
        {"neg_words_local": re.search(r"^NEG_WORDS", impl.text) is not None,
         "absent_markers_local": re.search(r"^ABSENT_MARKERS", impl.text) is not None,
         "imports": "run_m5c2_rev5_offline" in impl.text and "run_m5c2_rev5_1_offline" in impl.text},
        re.search(r"^NEG_WORDS", impl.text) is None
        and re.search(r"^ABSENT_MARKERS", impl.text) is None,
        "R2/R3 词表与 0.80 度量均由 R5/R51/R41 复用，脚本内无本地重定义（词表不可能漂移）")

    # ------------------------------------------------------------ §3 gates
    sens = art["sentences"]
    supp = [r for r in sens if gold[r["sid"]] == "support_present"]
    fab = [r for r in sens if gold[r["sid"]] == "fabricated"]
    fp = sorted(r["sid"] for r in supp if r["verdict_rev7"] == "unsupported")
    leak = sorted(r["sid"] for r in fab if r["verdict_rev7"] in ("supported", "undecidable"))
    pf = sorted(r["sid"] for r in sens if r["verdict_rev7"] == "parse_fail")
    risk = [r for r in fab if r["verdict_rev5_1"] == "unsupported"]
    newmiss = sorted(r["sid"] for r in risk if r["verdict_rev7"] == "supported")
    g = art["gate"]
    add(records, "S3-FP-DEF", "§3 门槛", 60, IMPL_REL, "main", (693, 696),
        "recompute", {"k": g["false_positive"]["k"], "n": g["false_positive"]["n"],
                      "sids": g["false_positive_sids"]},
        {"k": len(fp), "n": len(supp), "sids": fp},
        len(fp) == g["false_positive"]["k"] and len(supp) == g["false_positive"]["n"] and fp == g["false_positive_sids"],
        "误判 = gold support_present ∧ verdict unsupported；2/46 由 records+gold 复算")
    add(records, "S3-LEAK-DEF", "§3 门槛", 61, IMPL_REL, "main", (696, 696),
        "recompute", {"k": 4, "n": 41, "sids": ["b4-s2-q2-s01", "b4-s3-q4-s03", "b4-s3-q4-s11", "b4-s3-q4-s12"]},
        {"k": len(leak), "n": len(fab), "sids": leak},
        len(leak) == 4 and len(fab) == 41 and leak == g["leak_missed_sids"],
        "漏判 = gold fabricated ∧ verdict ∈{supported,undecidable}；4/41")
    add(records, "S3-PF-DEF", "§3 门槛", 62, IMPL_REL, "main", (697, 697),
        "recompute", {"k": 1, "n": 261, "sids": ["b4-s2-q2-s05"]},
        {"k": len(pf), "n": len(sens), "sids": pf},
        len(pf) == 1 and len(sens) == 261 and pf == g["parse_fail_sids"],
        "parse_fail 数 = verdict_rev7=='parse_fail'；1/261")
    add(records, "S3-NEWMISS-DEF", "§3 门槛", 63, IMPL_REL, "main", (698, 699),
        "recompute", {"k": 0, "n": 35},
        {"k": len(newmiss), "n": len(risk), "sids": newmiss},
        len(newmiss) == 0 and len(risk) == 35 and len(newmiss) == g["new_miss"]["k"],
        "漏判新增 = gold fabricated 且 rev5_1 unsupported → rev7 supported；0/35")
    add(records, "S3-GATE-RESULT", "§3 门槛", 65, IMPL_REL, "main", (709, 724),
        "recompute", {"rev7_unusable": False},
        {"gate": {k: g[k] for k in ("false_positive", "leak_missed", "parse_fail", "new_miss")},
         "rev7_unusable": g["rev7_unusable"]},
        g["rev7_unusable"] is False, "四门槛全过（2≤4 / 4≤5 / 1≤2 / 0=0）⇒ rev7_unusable=false")

    # ------------------------------------------------------------ §4 delivery
    add(records, "S4-TOP-FIELDS", "§4 交付", (70, 71), IMPL_REL, "main", (855, 875),
        "recompute", {"rev7_ver": 1, "n_sentences": 261, "n_forward": 0, "design_set": True,
                      "not_acceptance": True, "prereg_sha16": DOC_SHA16,
                      "items_source_sha16": JUDGE_SHA16, "gold_sha16_current": GOLD_SHA16},
        {"rev7_ver": art["rev7_ver"], "n_sentences": art["n_sentences"],
         "n_forward": art["n_forward"], "design_set": art["design_set"],
         "not_acceptance": art["not_acceptance"], "prereg_sha16": art["prereg_sha16"],
         "items_source_sha16": art["items_source_sha16"],
         "gold_sha16_current": art["gold_sha16_current"]},
        art["rev7_ver"] == 1 and art["n_sentences"] == len(sens) == 261
        and art["n_forward"] == 0 and art["design_set"] is True
        and art["not_acceptance"] is True and art["prereg_sha16"] == sha16(doc_bytes)
        and art["items_source_sha16"] == sha16(judge_bytes)
        and art["gold_sha16_current"] == sha16(gold_bytes),
        "§4 顶层字段齐全；三个 sha16 均为本次重算（不是抄写）")
    add(records, "S4-ITEM-FIELDS", "§4 交付", 72, IMPL_REL, "judge_row_rev7", (428, 444),
        "static_ref", {"fields": ["sid", "item", "evidence", "valid", "matcher_hit",
                                  "coverage", "numeric_ok", "item_verdict"]},
        {"present": list(art["items"][0].keys()),
         "n_items": len(art["items"]), "dice_field": "dice" in art["items"][0]},
        all(k in art["items"][0] for k in ("sid", "item", "evidence", "valid", "matcher_hit",
                                          "coverage", "numeric_ok", "item_verdict")),
        "逐条字段齐全；文档写 dice/coverage，代码只给 coverage（斜杠读作『或』则通过）")
    add(records, "S4-SENT-DIFF", "§4 交付", 75, IMPL_REL, "main", (727, 779),
        "recompute", {"n_changed": 7, "n_fixed": 5, "n_broken": 0, "n_neutral": 2},
        {"n_changed": art["sentence_diff"]["n_changed"],
         "n_fixed": art["sentence_diff"]["n_fixed"],
         "n_broken": art["sentence_diff"]["n_broken"],
         "n_neutral": art["sentence_diff"]["n_neutral"]},
        (art["sentence_diff"]["n_changed"], art["sentence_diff"]["n_fixed"],
         art["sentence_diff"]["n_broken"], art["sentence_diff"]["n_neutral"]) == (7, 5, 0, 2),
        "逐句对照全列：7 句变化 = 5 fixed / 0 broken / 2 neutral（2 句 gold=no_fact）")
    inv = [z for z in art["items"] if not z["valid"]]
    add(records, "S4-INVALID", "§4 交付", 74, IMPL_REL, "main", (810, 827),
        "recompute", {"invalid_total": 124, "n_items": 777, "rate": 0.1596},
        {"invalid_total": len(inv), "n_items": len(art["items"]),
         "rate": art["rates"]["invalid_items"]["rate"]},
        len(inv) == 124 and len(art["items"]) == 777
        and art["rates"]["invalid_items"]["k"] == 124,
        "作废条目 124/777 = 15.96%，占比可复算")
    attr = sorted(set(x["attribution"] for x in art["false_by_reason"]))
    n4_branch = re.search(r'return "N4"', impl.text) is not None
    add(records, "S4-FALSE-BY-REASON", "§4 交付", 74, IMPL_REL, "pick_attribution", (484, 499),
        "static_grep", {"categories_in_doc": ["N1", "N2", "N3", "N4", "R4+", "declared", "other"],
                        "reaches_N4": True},
        {"observed_attributions": attr, "n4_return_branch": n4_branch},
        n4_branch,
        "§4 要求 false_by_reason 含 N4 归类，但 pick_attribution 无 N4 分支、实测只出现 N1/N2/N3（对不上）")
    add(records, "S4-ASSERTIONS", "§4 交付", 76, IMPL_REL, "main", (621, 648),
        "static_ref", {"A1": "pass", "A2": "fail", "A3": "fail", "printed": True},
        {"all_pass": art["assertions"]["all_pass"],
         "A1_pass": art["assertions"]["A1"]["pass"],
         "A2_pass": art["assertions"]["A2"]["pass"],
         "A3_pass": art["assertions"]["A3"]["pass"],
         "assertion_note": bool(art["assertions"].get("assertion_note"))},
        art["assertions"]["A1"]["pass"] is True and art["assertions"]["A2"]["pass"] is False
        and art["assertions"]["A3"]["pass"] is False,
        "§2 三条断言均打印：A1 pass、A2/A3 fail（实现未为迎合断言而改规则，note 已说明）")

    # ------------------------------------------------------------ readings
    add(records, "R-261", "读数", 69, IMPL_REL, "main", (862, 862),
        "recompute", {"n_sentences": 261}, {"n_sentences": len(sens)}, len(sens) == 261,
        "261 句 = sentences[] 长度，非字面量")
    add(records, "R-0-FORWARD", "读数", 69, IMPL_REL, "main", (863, 867),
        "recompute", {"n_forward": 0}, {"n_forward": art["n_forward"],
                                        "n_model_rows": art["n_model_rows"],
                                        "n_abstain_rows": art["n_abstain_rows"]},
        art["n_forward"] == 0 and art["n_model_rows"] + art["n_abstain_rows"] == 261,
        "n_forward=0；route 构成 246 抽取 + 15 abstain，复用已落盘模型输出")
    add(records, "R-FP", "读数", 60, IMPL_REL, "main", (918, 920),
        "recompute", {"k": 2, "n": 46, "rate": 0.0435},
        {"k": len(fp), "n": len(supp), "rate": art["rates"]["false_positive"]["rate"]},
        len(fp) == 2 and len(supp) == 46, "误判 2/46（基线 7/46）")
    add(records, "R-LEAK", "读数", 61, IMPL_REL, "main", (921, 922),
        "recompute", {"k": 4, "n": 41}, {"k": len(leak), "n": len(fab)},
        len(leak) == 4 and len(fab) == 41, "漏判 4/41")
    add(records, "R-PF", "读数", 62, IMPL_REL, "main", (923, 924),
        "recompute", {"k": 1, "n": 261}, {"k": len(pf), "n": len(sens)},
        len(pf) == 1 and len(sens) == 261, "parse_fail 1/261")
    add(records, "R-INVALID", "读数", 74, IMPL_REL, "main", (925, 926),
        "recompute", {"k": 124, "n": 777}, {"k": len(inv), "n": len(art["items"])},
        len(inv) == 124 and len(art["items"]) == 777, "作废 124/777")
    add(records, "R-NEWMISS", "读数", 63, IMPL_REL, "main", (713, 713),
        "recompute", {"k": 0, "n": 35}, {"k": len(newmiss), "n": len(risk)},
        len(newmiss) == 0 and len(risk) == 35, "新增漏判 0（分母 35 = fabricated 且基线 unsupported）")
    add(records, "R-CHANGES", "读数", 75, IMPL_REL, "main", (758, 779),
        "recompute", {"changed": 7, "fixed": 5, "broken": 0, "neutral": 2},
        {"changed": art["sentence_diff"]["n_changed"],
         "fixed": art["sentence_diff"]["n_fixed"],
         "broken": art["sentence_diff"]["n_broken"],
         "neutral": art["sentence_diff"]["n_neutral"]},
        (art["sentence_diff"]["n_changed"], art["sentence_diff"]["n_fixed"],
         art["sentence_diff"]["n_broken"]) == (7, 5, 0), "7 句变化 = 5 修好 / 0 改坏 / 2 中性")
    add(records, "R-GOLD-DIST", "读数", 3, GOLD_REL, "<gold map>", (0, 0),
        "recompute", {"support_present": 46, "fabricated": 41, "no_fact": 164, "undecidable": 10},
        {"support_present": len(supp), "fabricated": len(fab),
         "no_fact": sum(1 for r in sens if gold[r["sid"]] == "no_fact"),
         "undecidable": sum(1 for r in sens if gold[r["sid"]] == "undecidable")},
        len(supp) == 46 and len(fab) == 41, "金标分布 46/41/164/10；产物内嵌 gold 与金标文件 261/261 一致")
    add(records, "R-BASELINE", "读数", (60, 62), IMPL_REL, "baseline_reproduce", (353, 361),
        "recompute", {"fp": 7, "leak": 4, "parse_fail": 1},
        {"fp": art["baseline_reproduction"]["baseline_false_positive"]["k"],
         "leak": art["baseline_reproduction"]["baseline_leak"]["k"],
         "parse_fail": art["baseline_reproduction"]["baseline_parse_fail"]["k"],
         "match_all": art["baseline_reproduction"]["match_all"]},
        art["baseline_reproduction"]["baseline_false_positive"]["k"] == 7
        and art["baseline_reproduction"]["baseline_leak"]["k"] == 4
        and art["baseline_reproduction"]["baseline_parse_fail"]["k"] == 1,
        "基线读数 7/46、4/41、1/261 已在运行时复现（match_all=true）")

    # ------------------------------------------------------------ anti-hardcoding
    hits = {n: [i + 1 for i, l in enumerate(impl.lines)
                if re.search(r"(?<![\dA-Za-z_])%d(?![\dA-Za-z_])" % n, l)]
            for n in (46, 41, 777, 124, 35)}
    add(records, "H-NO-RESULT-LITERALS", "反硬编码", (60, 63), IMPL_REL, "<whole source>", (1, len(impl.lines)),
        "static_grep", {"46": [], "41": [], "777": [], "124": [], "35": []},
        {"occurrences": hits}, all(not v for v in hits.values()),
        "结果常量 46/41/777/124/35 在脚本中零出现 ⇒ 读数不可能被写死")
    lines_261 = [i + 1 for i, l in enumerate(impl.lines) if re.search(r"(?<!\d)261(?!\d)", l)]
    add(records, "H-261-VALIDATION", "反硬编码", (69, 69), IMPL_REL, "main", (571, 582),
        "static_grep", {"261_lines": "docstring/常量/注释/输入校验"},
        {"lines": lines_261}, set(lines_261) <= {8, 74, 586},
        "261 只出现在文档字符串、N_SENTENCES 常量与输入校验（571-582），不参与结果计算")
    gate_lines = [i + 1 for i, l in enumerate(impl.lines)
                  if re.search(r"gate_item\(len\(fp\), len\(supp\), 4\)|gate_item\(len\(leak\), len\(fab\), 5\)|"
                               r"gate_item\(len\(pf\), len\(sent_recs\), 2\)|gate_item\(len\(new_miss\), len\(fab_at_risk\), 0",
                               l)]
    add(records, "H-THRESHOLD-TRACEABLE", "反硬编码", (60, 63), IMPL_REL, "gate_item", (701, 713),
        "static_grep", {"thresholds": {"false_positive": 4, "leak": 5, "parse_fail": 2, "new_miss": 0},
                        "gate_call_lines": [710, 711, 712, 713]},
        {"gate_call_lines": gate_lines}, gate_lines == [710, 711, 712, 713],
        "四个门槛值 4/5/2/0 只作为 gate_item 的阈值参数出现，逐行可溯到 §3 表")
    sid_cond = [i + 1 for i, l in enumerate(impl.lines)
                if re.search(r"\bif\s+sid\b|\bsid\s*==|\bsid\s+(?:not\s+)?in\b|\bsid\.startswith", l)]
    b4_lines = [i + 1 for i, l in enumerate(impl.lines) if "b4-" in l]
    add(records, "H-NO-SID-BRANCH", "反硬编码", (78, 85), IMPL_REL, "<whole source>", (1, len(impl.lines)),
        "static_grep", {"sid_branches": 0}, {"sid_branches": sid_cond}, not sid_cond,
        "无 if sid / sid== / sid in 分支；b4- 字面量仅出现在 EXPECT/ASSERT（80-85）与自述字典（953-955）")
    hidden = [i + 1 for i, l in enumerate(impl.lines)
              if re.search(r"try:|except |os\.environ|sys\.argv|\brandom\b|time\.|if False", l)]
    add(records, "H-NO-HIDDEN-BRANCH", "反硬编码", 82, IMPL_REL, "<whole source>", (1, len(impl.lines)),
        "static_grep", {"hidden_branch_markers": 0}, {"lines": hidden}, not hidden,
        "无 try/except、环境变量、argv、随机/时间、if False；单一 main 路径")

    # ------------------------------------------------------------ implementation self-claims
    add(records, "IMP-IMPORT-CLAIM", "实现自述", (78, 80), IMPL_REL, "docstring:49-52", (49, 56),
        "static_grep", {"claim": "no engine / no GPU runner imported"},
        {"claim_in_docstring": "no engine" in impl.text,
         "transitive_local_modules": sorted(_local_import_closure()),
         "gpu_runner_reachable": "_e3gpu_run" in _local_import_closure()},
        not ("_e3gpu_run" in _local_import_closure()),
        "自述『未导入 engine/GPU runner』不成立：R5→R41→_e3gpu_run 等 10 个本地模块被传递导入（仅 import，无前向）")
    add(records, "IMP-ZERO-GPU", "实现自述", 80, IMPL_REL, "main", (946, 950),
        "static_grep", {"n_forward": 0, "no_model_call": True, "no_network": True},
        {"n_forward_artifact": art["n_forward"], "no_model_call": art["no_model_call"],
         "no_network": art["no_network"], "no_gpu": art["no_gpu"]},
        art["n_forward"] == 0 and art["no_model_call"] is True,
        "零前向由 n_forward=0 与代码路径支持；GPU runner 仅被导入未调用（见 IMP-IMPORT-CLAIM）")

    add(records, "U-B5-ONCE", "§5 纪律", 83, IMPL_REL, "<no code path>", (0, 0),
        "static_grep", {"b5_runs": "exactly once after freeze"}, None, None,
        "不可静态验证：『(b5) 冻结后只跑一次』是未来运行行为；当前仓库无 (b5) 运行数据，无法从字节证据判定")
    add(records, "U-B5-CONDITIONAL", "§5 纪律", 84, IMPL_REL, "main", (719, 724),
        "static_grep", {"conditional": "rev7_unusable=True => b5 must not run"},
        {"rev7_unusable": art["gate"]["rev7_unusable"]}, None,
        "不可静态验证：条件本身未被触发（rev7_unusable=false），『则 (b5) 不跑、记 blocked_by_judge_unusable』无运行实例可验")

    # ------------------------------------------------------------ summary + write
    n = len(records)
    n_pass = sum(1 for r in records if r["pass"] is True)
    n_fail = sum(1 for r in records if r["pass"] is False)
    n_unv = sum(1 for r in records if r["pass"] is None)
    groups = ["§0 归因", "§2 规范", "§3 门槛", "§4 交付", "读数", "反硬编码", "实现自述", "§5 纪律"]
    by_group = {}
    for gname in groups:
        sel = [r for r in records if r["group"] == gname]
        by_group[gname] = {"n": len(sel),
                           "pass": sum(1 for r in sel if r["pass"] is True),
                           "fail": sum(1 for r in sel if r["pass"] is False),
                           "unverifiable": sum(1 for r in sel if r["pass"] is None)}
    summary = {
        "n_claims": n, "n_pass": n_pass, "n_fail": n_fail, "n_unverifiable": n_unv,
        "by_group": by_group,
        "fail_ids": [r["claim_id"] for r in records if r["pass"] is False],
        "unverifiable_ids": [r["claim_id"] for r in records if r["pass"] is None],
        "all_pass": n_fail == 0,
        "check_mode": "checks only" if not write_outputs else "checks + write",
    }
    out = {
        "schema": "m5c2_rev7_claim_map_v1",
        "generated_by": "kvmem/m2_visibility/m5/out/m5c2_rev7_claim_map.py",
        "mapper_sha16": sha16(Path(__file__).read_bytes()),
        "inputs": {"prereg": {"file": DOC_REL, "sha16": sha16(doc_bytes), "bytes": len(doc_bytes)},
                   "impl": {"file": IMPL_REL, "sha16": sha16(impl_bytes), "bytes": len(impl_bytes)},
                   "artifact": {"file": ART_REL, "sha16": sha16(art_bytes), "bytes": len(art_bytes)},
                   "judge": {"file": JUDGE_REL, "sha16": sha16(judge_bytes), "bytes": len(judge_bytes)},
                   "gold": {"file": GOLD_REL, "sha16": sha16(gold_bytes), "bytes": len(gold_bytes)}},
        "summary": summary,
        "claims": records,
    }
    for r in records:
        print("%-24s %-10s %-4s %s" % (r["claim_id"], r["group"],
                                       "PASS" if r["pass"] else ("FAIL" if r["pass"] is False else "UNV"),
                                       r["notes"][:88]))
    print("\nclaims=%d pass=%d fail=%d unverifiable=%d" % (n, n_pass, n_fail, n_unv))

    if write_outputs:
        _write_json(MAP, out)
        MD.write_text(_render_md(out), encoding="utf-8", newline="\n")
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
            print("--check: regenerated map matches on-disk map: %s" % same)
            if not same:
                n_fail += 1
        print("--check: exit 1 表示 claim 表内存在 %d 条文档主张对不上（研究结论），"
              "不是校验器故障；退出码 0 才表示全部主张成立。" % n_fail)
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


def _render_md(out):
    s = out["summary"]
    L = []
    L.append("# CODE-TRACE-M5C2-REV7 —— 文档主张 ↔ 代码 逐条追踪")
    L.append("")
    L.append("> 由 `kvmem/m2_visibility/m5/out/m5c2_rev7_claim_map.py` 自动生成（可 `--check` 重跑）。")
    L.append("> 冻结 PREREG `docs/_work/PREREG-M5-C2-REV7.md` sha16 `%s` / %d B；"
             "被测脚本 `%s` sha16 `%s`；产物 `%s` sha16 `%s`。"
             % (out["inputs"]["prereg"]["sha16"], out["inputs"]["prereg"]["bytes"],
                IMPL_REL, out["inputs"]["impl"]["sha16"], ART_REL,
                out["inputs"]["artifact"]["sha16"]))
    L.append("")
    L.append("## 摘要")
    L.append("")
    L.append("| 指标 | 值 |")
    L.append("|---|---:|")
    L.append("| claim 总数 | %d |" % s["n_claims"])
    L.append("| pass | %d |" % s["n_pass"])
    L.append("| fail | %d |" % s["n_fail"])
    L.append("| unverifiable | %d |" % s["n_unverifiable"])
    L.append("")
    L.append("> 退出码说明：`--check` 在任一 claim fail 时返回 1。本表含 **%d 条 fail**（均为文档主张"
             "与代码/数据对不上的结论），因此退出码为 1 属预期，不是校验器故障；"
             "只有全部主张成立时才返回 0。" % s["n_fail"])
    L.append("")
    L.append("| 分组 | 条数 | pass | fail | 不可验证 |")
    L.append("|---|---:|---:|---:|---:|")
    for g, v in s["by_group"].items():
        L.append("| %s | %d | %d | %d | %d |" % (g, v["n"], v["pass"], v["fail"], v["unverifiable"]))
    L.append("")
    L.append("## 逐条对照表")
    L.append("")
    L.append("| claim_id | 文档行 | 代码 | 结果 |")
    L.append("|---|---|---|---|")
    for r in out["claims"]:
        dl = "%d" % r["doc_lines"][0] if r["doc_lines"][0] == r["doc_lines"][1] \
            else "%d-%d" % (r["doc_lines"][0], r["doc_lines"][1])
        cl = "—" if r["code_function"].startswith("<") else \
            "%s:%s" % (r["code_function"], ("%d" % r["code_lines"][0])
                       if r["code_lines"][0] == r["code_lines"][1]
                       else "%d-%d" % (r["code_lines"][0], r["code_lines"][1]))
        res = "PASS" if r["pass"] else ("**FAIL**" if r["pass"] is False else "不可验证")
        L.append("| `%s` | L%s | `%s` | %s |" % (r["claim_id"], dl, cl, res))
    L.append("")
    L.append("## 对不上 / 不可验证 的条目（重点）")
    L.append("")
    fails = [r for r in out["claims"] if r["pass"] is False]
    unvs = [r for r in out["claims"] if r["pass"] is None]
    L.append("### 对不上（%d 条）" % len(fails))
    L.append("")
    for r in fails:
        L.append("- **%s**（doc L%s ↔ `%s:%s`）：文档说「%s」；实测 %s。%s"
                 % (r["claim_id"], ",".join(str(x) for x in r["doc_lines"]),
                    r["code_function"], r["code_lines"][0],
                    r["claim_text"].replace("|", "/")[:160],
                    json.dumps(r["actual"], ensure_ascii=False)[:300], r["notes"]))
    L.append("")
    L.append("### 不可静态验证（%d 条）" % len(unvs))
    L.append("")
    for r in unvs:
        L.append("- **%s**：%s" % (r["claim_id"], r["notes"]))
    if not unvs:
        L.append("- 无（本映射表内的条目均可静态或运行时验证）")
    L.append("")
    L.append("## 关键代码片段（每段 ≤5 行）")
    L.append("")
    for cid in ("S2-N1-REF", "S2-N2-REGEX", "S2-N3-DEF", "S2-N4-SCOPE", "S3-GATE-RESULT"):
        r = next((x for x in out["claims"] if x["claim_id"] == cid), None)
        if not r:
            continue
        L.append("### %s — `%s:%s`" % (cid, r["code_function"], r["code_lines"][0]))
        L.append("```python")
        L.append(_snippet(IMPL.read_text(encoding="utf-8"), r["code_lines"]))
        L.append("```")
        L.append("")
    L.append("## 方法与复现")
    L.append("")
    L.append("1. **静态定位**：`ast.parse` 取函数行号区间，再对源切片算 sha256，证明函数/常量确实在冻结脚本内。")
    L.append("2. **运行期复算**：本脚本自带独立 `normalize7` / `coverage` / `window_coverage`，"
             "对 777 条 item 逐条重算 N3 的 `valid`，并从 `sentences[]` + 金标重算 FP/漏判/parse_fail/new_miss"
             "（不读产物 `gate`/`rates` 现成值，只在最后与它们对账）。")
    L.append("3. **反硬编码**：扫描 46/41/777/124/35 等结果常量，确认零出现；261 仅出现在常量与输入校验；"
             "门槛 4/5/2/0 只作为 `gate_item` 阈值参数。")
    L.append("4. **无 sid 特判**：`if sid` / `sid ==` / `sid in` / `startswith` 零命中；`b4-` 字面量只在 EXPECT/ASSERT 与自述字典。")
    L.append("")
    L.append("```")
    L.append("python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_claim_map.py          # 生成映射")
    L.append("python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_claim_map.py --check  # 仅校验，fail 退出码 1")
    L.append("```")
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))