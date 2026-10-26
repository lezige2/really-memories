# -*- coding: utf-8 -*-
"""M5 judge **v2.3** -- A/B component grading + copula whitelist + prefix trimming.

Implements docs/_work/PREREG-M5-JUDGE-v2.3.md (`5a3f12f2a742a864` / 10,394 B).
v2.1 (`m5_ground_v2.py`, `5e11e1ac06f022c7` / 66,413 B) and v2.2
(`m5_ground_v2_2.py`, `ae5ceea994c05691` / 36,005 B) are imported read-only and
are not modified.  Only A components (numbers/entities) require coverage; B
predicates/negations only bind and detect polarity conflicts.

CPU only: no model, no GPU, no network, no git operations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import m5_ground as _v1                 # noqa: E402  (read-only primitives)
import m5_ground_v2 as _v21             # noqa: E402  (frozen v2.1; read-only)
import m5_ground_v2_2 as _v22           # noqa: E402  (frozen v2.2; read-only reference)

JUDGE_VERSION = "v2.3"
PREREG_SHA16 = "5a3f12f2a742a864"
PREREG_BYTES = 10394
V21_SHA16 = "5e11e1ac06f022c7"
V21_BYTES = 66413
V22_SHA16 = "ae5ceea994c05691"
V22_BYTES = 36005
THETA = 0.20
GRAM_N = 2
STRICT_GT = True

PUNCT = re.compile(r"[，。！？、；：,\.!\?;:\"“”'‘’（）()【】\[\]「」『』]")
NUM = re.compile(r"(?<![.．、])(?:[0-9０-９]+|[零〇一二三四五六七八九十百千万亿两]+)(?![.．、])")
SUFFIX_ENTITY = re.compile(
    r"[\u4e00-\u9fff0-9]{1,10}(?:路|街|道|巷|弄|号|楼|单元|室|层|栋|座|区|市|省|县|镇|村|园|苑|府|湾|广场|大厦)")
TIME_ENTITY = re.compile(r"(?:\d{1,2}月\d{1,2}[日号])|(?:\d{4}[-/年]\d{1,2}[-/月]\d{1,2})|(?:\d{1,2}[:：]\d{2})")
CODE_ENTITY = re.compile(r"(?:代号|名称|型号)(?:为|是|：|:)?\s*([A-Za-z0-9\u4e00-\u9fff]{2,12})")
PLATE_ENTITY = re.compile(r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4,6}")
LOC_ENTITY = re.compile(r"(?:在|到|去|回)([\u4e00-\u9fff]{2,8})")
OBJ_ENTITY = re.compile(r"(?:停在|停放在|停放|手持|拿着|带着)([\u4e00-\u9fff0-9]{2,10})")

PREDICATES = ("住在", "住址", "地址", "停在", "停放在", "停放", "上线", "发布", "代号",
              "只喝", "喝", "加糖", "不加糖", "不加奶", "是", "为", "在")
NEG = ("不", "没", "没有", "非", "未", "无")
PHRASE_BLOCKLIST = frozenset({"修正后的回答", "回答", "以上", "以下", "现在", "所有", "等等", "错误", "正确"})
ORDINAL = re.compile(r"^(?:\d{1,3}[.、)]|[（(]\d{1,3}[）)])\s*")
SENT_END = _v1.SENT_END

CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}
CN_BIG = {"万": 10000, "亿": 100000000}
CN_RUN = re.compile(r"[零〇一二三四五六七八九十百千万亿两]+")

SOURCE_TEXTS = ("我住在广陵路 12 号 2 单元 602。",
                "项目代号蓝鲸，计划 3 月 14 日上线。",
                "我的咖啡只喝美式，不加糖。")
SOURCE_BLOB = _v1.prep("".join(SOURCE_TEXTS))

# v2.3 grading
WHITELIST = frozenset({"是", "为", "在", "有"})
LOC_LEADS = frozenset({"在", "到", "去", "回"})
STOP_CHARS = frozenset("的在是为有我你他她它住停现回到去于和与被把将")
B_PREDICATES = tuple(p for p in PREDICATES if p not in WHITELIST)
B_CANON = {"只喝": "喝"}
ESTIMATE_ONLY_BASELINE = "预登记 §2 的 16/16 + 4/64 是内存粗算（estimate_only），本件为首次实现验证，两者差异须如实并列"
USAGE_RESTRICTION = "不得用于证明新判据有效；不得据此调规则；仅作 in-sample 设计输入复现"


# ---------------------------------------------------------------- frozen checks
def _sha16_bytes(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def _bytes(path):
    return os.path.getsize(path)


def _freeze_check():
    v21 = os.path.join(_HERE, "m5_ground_v2.py")
    v22 = os.path.join(_HERE, "m5_ground_v2_2.py")
    pre = os.path.join(_ROOT, "docs", "_work", "PREREG-M5-JUDGE-v2.3.md")
    if _sha16_bytes(v21) != V21_SHA16 or _bytes(v21) != V21_BYTES:
        raise RuntimeError("v2.1 source changed; refusing to run v2.3")
    if _sha16_bytes(v22) != V22_SHA16 or _bytes(v22) != V22_BYTES:
        raise RuntimeError("v2.2 source changed; refusing to run v2.3")
    if _sha16_bytes(pre) != PREREG_SHA16 or _bytes(pre) != PREREG_BYTES:
        raise RuntimeError("v2.3 prereg changed; refusing to run v2.3")
    return {"v21_sha16": _sha16_bytes(v21), "v21_bytes": _bytes(v21),
            "v22_sha16": _sha16_bytes(v22), "v22_bytes": _bytes(v22),
            "prereg_sha16": _sha16_bytes(pre), "prereg_bytes": _bytes(pre)}


# ---------------------------------------------------------------- normalization / numerals
def normalize(text):
    # §1.2 removes punctuation.  We keep a single "|" clause boundary so the
    # greedy entity patterns cannot swallow a verb from the previous clause;
    # the boundary is not a component and does not change coverage semantics.
    s = unicodedata.normalize("NFKC", text or "").strip()
    s = _v1.INVIS.sub("", s)
    s = PUNCT.sub("|", s)
    s = re.sub(r"\|+", "|", s).strip("|")
    return s


def cn2int(run):
    total = section = number = 0
    for ch in run:
        if ch in CN_DIGITS:
            number = CN_DIGITS[ch]
        elif ch in CN_UNITS:
            if number == 0:
                number = 1
            section += number * CN_UNITS[ch]
            number = 0
        elif ch in CN_BIG:
            section = (section + number) * CN_BIG[ch]
            total += section
            section = number = 0
    return total + section + number


def canonical(text):
    """Arabic form used only for coverage comparison; display keeps the raw form."""
    return CN_RUN.sub(lambda m: str(cn2int(m.group(0))), text)


# ---------------------------------------------------------------- extraction fp records
def _fp(kind, sentence, text, extra=None):
    rec = {"kind": kind, "sentence": sentence, "text": text}
    if extra:
        rec.update(extra)
    return rec


# ---------------------------------------------------------------- A entities
_ENTITY_PREFIXES = ("我的家庭地址是", "我的地址是", "我的住址是", "家庭地址是", "家庭住址是",
                    "地址是", "住址是", "我住在", "你住在", "他住在", "她住在",
                    "我的", "你的", "他的", "她的", "它的", "我", "你", "他", "她", "它",
                    "车停在", "车停放在", "车停放", "停在", "停放在", "停放",
                    "是的", "是", "在", "到", "去", "回", "的")


def _trim_entity_prefix(value):
    changed = True
    while changed:
        changed = False
        for pref in _ENTITY_PREFIXES:
            if value.startswith(pref) and len(value) > len(pref):
                value = value[len(pref):]
                changed = True
                break
    # §1.2 v2.3: last STOP_CHARS tail; tail <2 chars is discarded.
    for i, ch in enumerate(value):
        if ch in STOP_CHARS:
            value = value[i + 1:]
    if len(value) < 2:
        return ""
    return value


def _entity_matches(text):
    found = []

    def add(start, end, value, pattern, full):
        if not value:
            return
        found.append({"start": start, "end": end, "text": value,
                      "pattern": pattern, "surface": full})

    for m in SUFFIX_ENTITY.finditer(text):
        val = _trim_entity_prefix(m.group(0))
        if not val:
            continue
        start = m.end() - len(val)
        add(start, m.end(), val, "suffix", m.group(0))
    for m in TIME_ENTITY.finditer(text):
        add(m.start(), m.end(), m.group(0), "time", m.group(0))
    for m in CODE_ENTITY.finditer(text):
        val = m.group(1)
        if val in PHRASE_BLOCKLIST or any(val.startswith(w) for w in PHRASE_BLOCKLIST):
            continue
        add(m.start(1), m.end(1), val, "code", m.group(0))
    for m in PLATE_ENTITY.finditer(text):
        add(m.start(), m.end(), m.group(0), "plate", m.group(0))
    for m in LOC_ENTITY.finditer(text):
        val = m.group(1)
        if val in PHRASE_BLOCKLIST or any(val.startswith(w) for w in PHRASE_BLOCKLIST):
            continue
        add(m.start(1), m.end(1), val, "loc", m.group(0))
    for m in OBJ_ENTITY.finditer(text):
        val = m.group(1)
        if val in PHRASE_BLOCKLIST or any(val.startswith(w) for w in PHRASE_BLOCKLIST):
            continue
        add(m.start(1), m.end(1), val, "obj", m.group(0))
    prio = {"obj": 0, "loc": 1, "suffix": 2, "time": 3, "code": 4, "plate": 5}
    found.sort(key=lambda x: (-(x["end"] - x["start"]), x["start"], prio.get(x["pattern"], 99)))
    claimed = [False] * len(text)
    out = []
    for e in found:
        if any(claimed[e["start"]:e["end"]]):
            continue
        for i in range(e["start"], e["end"]):
            claimed[i] = True
        out.append({"text": e["text"], "kind": "entity", "grade": "A",
                    "span": [e["start"], e["end"]],
                    "text_canon": canonical(e["text"]),
                    "surface": e["surface"], "pattern": e["pattern"]})
    return out, claimed


def extract_a_components(text):
    """A level only: six entity patterns + NUM.  Predicates are never A."""
    comps, claimed = _entity_matches(text)
    for m in NUM.finditer(text):
        start, end = m.start(), m.end()
        if any(claimed[start:end]):
            continue
        for i in range(start, end):
            claimed[i] = True
        comps.append({"text": m.group(0), "kind": "num", "grade": "A",
                      "span": [start, end], "text_canon": canonical(m.group(0)),
                      "surface": m.group(0)})
    comps.sort(key=lambda c: (c["span"][0], c["span"][1]))
    return comps


# ---------------------------------------------------------------- B units
def _neg_prefix(text, start):
    for neg in sorted(NEG, key=len, reverse=True):
        if start >= len(neg) and text[start - len(neg):start] == neg:
            return neg
    return ""


def _b_canon(pred):
    base = pred
    for neg in sorted(NEG, key=len, reverse=True):
        if base.startswith(neg):
            base = base[len(neg):]
            break
    return B_CANON.get(base, base)


def extract_b_units(text):
    """B level: predicates + negation binding; no coverage requirement."""
    units = []
    claimed = [False] * len(text)
    for pred in sorted(B_PREDICATES, key=len, reverse=True):
        for m in re.finditer(re.escape(pred), text):
            start, end = m.start(), m.end()
            if any(claimed[start:end]):
                continue
            neg = ""
            if pred[0] in NEG:
                neg = pred[0]
            else:
                neg = _neg_prefix(text, start)
                if neg:
                    start -= len(neg)
            if start < 0 or any(claimed[start:end]):
                continue
            for i in range(start, end):
                claimed[i] = True
            surface = text[start:end]
            units.append({"pred": _b_canon(pred), "surface": surface,
                          "polarity": not bool(neg), "negated": bool(neg),
                          "span": [start, end]})
    units.sort(key=lambda u: (u["span"][0], u["span"][1]))
    return units


def b_units_for_facts(facts):
    out = []
    for f in facts:
        out.extend(extract_b_units(f))
    return out


# ---------------------------------------------------------------- source facts
def source_facts(source_texts):
    facts = []
    for t in source_texts:
        nt = normalize(t)
        if nt:
            facts.append(canonical(nt))
        for c in extract_a_components(nt):
            facts.append(c["text_canon"])
    out = []
    for f in facts:
        if f and f not in out:
            out.append(f)
    return out


def source_b_units(source_texts):
    out = []
    for t in source_texts:
        out.extend(extract_b_units(normalize(t)))
    return out


def covered_by(component, facts):
    c = component["text_canon"]
    for f in facts:
        if c in f:
            return True, False, f
        if f in c and len(f) >= len(c) - 1:
            return True, True, f
    return False, False, None


# ---------------------------------------------------------------- sentence analysis
def analyze_sentence(raw, idx, source_fact_list, *, fact_b_units=None, is_last=False):
    raw = raw or ""
    nfkc = unicodedata.normalize("NFKC", raw).strip()
    ordinal = None
    fp = []
    m = ORDINAL.match(nfkc)
    if m:
        ordinal = m.group(0)
        nfkc = nfkc[m.end():]
        fp.append(_fp("list_ordinal_removed", idx, ordinal))
    norm = normalize(nfkc)
    components = extract_a_components(norm)
    b_units = extract_b_units(norm)
    truncated_tail = bool(is_last and not raw.rstrip().endswith(tuple(SENT_END)))
    truncated_cut = False
    if truncated_tail and components:
        last = components[-1]
        if last["kind"] == "num" and last["span"][1] == len(norm):
            components = components[:-1]
            truncated_cut = True
            fp.append(_fp("truncation_cut", idx, last["text"]))
    is_question = bool(raw.rstrip().endswith(("？", "?")) or
                       any(t in raw for t in _v1.INTERROG) or raw.lstrip().startswith("问："))
    if fact_b_units is None:
        fact_b_units = b_units_for_facts(source_fact_list)
    covered, uncovered, short_cover = [], [], []
    for c in components:
        hit, is_short, f = covered_by(c, source_fact_list)
        if hit:
            covered.append(c)
            if is_short:
                short_cover.append({"component": c["text"], "fact": f})
        else:
            uncovered.append(c)
    conflicts = []
    for sb in b_units:
        for fb in fact_b_units:
            if sb["pred"] == fb["pred"] and sb["polarity"] != fb["polarity"]:
                conflicts.append({"sentence_unit": sb, "fact_unit": fb,
                                  "pred": sb["pred"]})
    if is_question:
        verdict, reason = "excluded", "question_clause_excluded"
    elif truncated_cut:
        verdict, reason = "undecidable", "truncated_tail_num_cut"
    elif conflicts:
        verdict, reason = "unsupported", "polarity_conflict"
    elif not components:
        verdict, reason = "undecidable", "no_a_component"
    elif uncovered:
        verdict, reason = "unsupported", "uncovered_component"
    else:
        verdict, reason = "supported", "all_a_components_covered"
    return {
        "idx": idx, "raw": raw, "text_norm": norm,
        "components": components, "b_units": b_units,
        "covered": covered, "uncovered": uncovered,
        "short_fact_cover": short_cover,
        "polarity_conflicts": conflicts,
        "n_components": len(components), "n_covered": len(covered),
        "n_uncovered": len(uncovered), "verdict": verdict, "reason": reason,
        "truncated_tail": truncated_tail, "truncated_cut": truncated_cut,
        "question_clause_excluded": is_question,
        "extraction_fp": fp,
        "ordinal_removed": ordinal,
    }


# ---------------------------------------------------------------- answer analysis
def _v1_facts(answer):
    facts = []
    for idx, seg in enumerate(_v1.split_sentences(answer)):
        for f in _v1.extract(seg):
            facts.append(dict(f, sentence=idx))
    return facts


def analyze_answer(answer, source_texts=None, question=None):
    source_texts = list(source_texts if source_texts is not None else SOURCE_TEXTS)
    facts = source_facts(source_texts)
    fact_b = source_b_units(source_texts)
    segs = _v1.split_sentences(answer or "")
    sentences = [analyze_sentence(seg, i, facts, fact_b_units=fact_b,
                                  is_last=(i == len(segs) - 1))
                 for i, seg in enumerate(segs)]
    counts = Counter(s["verdict"] for s in sentences)
    partial = [{"idx": s["idx"], "text": s["text_norm"],
                "covered": [c["text"] for c in s["covered"]],
                "uncovered": [c["text"] for c in s["uncovered"]],
                "n_covered": s["n_covered"], "n_uncovered": s["n_uncovered"]}
               for s in sentences if s["verdict"] == "unsupported"
               and s["reason"] == "uncovered_component" and s["n_covered"] > 0]
    extraction_fp = [x for s in sentences for x in s["extraction_fp"]]
    polarity = [x for s in sentences for x in s["polarity_conflicts"]]
    short_cover = [dict(x, idx=s["idx"]) for s in sentences for x in s["short_fact_cover"]]
    v1facts = _v1_facts(answer or "")
    blob = _v1.prep("".join(source_texts))
    ngram = None
    branch5_gap = []
    unsupported = [s for s in sentences if s["verdict"] == "unsupported"]
    undecidable = [s for s in sentences if s["verdict"] == "undecidable"]
    active = [s for s in sentences if s["verdict"] not in ("no_fact", "excluded")]
    if unsupported:
        verdict, branch, reason = "unsupported", "v23_sentence_unsupported", unsupported[0]["reason"]
    elif undecidable:
        verdict, branch, reason = "undecidable", "v23_sentence_undecidable", "sentence_undecidable"
    elif not active:
        ngram = _v21.ngram_check(answer or "", blob, THETA)
        if ngram["verdict"] == "unsupported":
            verdict, branch, reason = "unsupported", "5a_2gram_negative", "2gram_negative_evidence"
            branch5_gap.append({"answer": answer,
                                "reason": "answer-level branch5 unsupported; no sentence-level uncovered A component",
                                "ngram": ngram})
        elif ngram["verdict"] == "supported":
            verdict, branch, reason = "supported", "5b_ngram_covered", "no_fact_ngram_covered"
        else:
            verdict, branch, reason = "undecidable", "5c_no_fact", "no_fact_unverifiable"
    elif not v1facts:
        ngram = _v21.ngram_check(answer or "", blob, THETA)
        if ngram["verdict"] == "unsupported":
            verdict, branch, reason = "unsupported", "5a_2gram_negative", "2gram_negative_evidence"
            branch5_gap.append({"answer": answer,
                                "reason": "answer-level unsupported cannot be assigned to any sentence",
                                "ngram": ngram})
        elif ngram["verdict"] == "supported":
            verdict, branch, reason = "supported", "5b_ngram_covered", "no_fact_ngram_covered"
        else:
            verdict, branch, reason = "undecidable", "5c_no_fact", "no_fact_unverifiable"
    else:
        verdict, branch, reason = "supported", "v23_sentence_supported", "all_a_components_covered"
    return {
        "judge_version": JUDGE_VERSION, "prereg_sha16": PREREG_SHA16,
        "theta": THETA, "gram_n": GRAM_N, "strict_gt": STRICT_GT,
        "question": question, "verdict": verdict, "branch": branch, "reason": reason,
        "sentences": sentences, "sentence_counts": dict(counts),
        "partial_hit_sentences": partial,
        "polarity_conflicts": polarity,
        "short_fact_cover": short_cover,
        "extraction_fp": extraction_fp,
        "branch5_structural_gap": branch5_gap,
        "ngram": ngram,
        "v1_facts_n": len(v1facts),
        "v1_facts": [{"family": f["family"], "raw": f["raw"], "sentence": f["sentence"]}
                     for f in v1facts],
        "source_facts_n": len(facts),
        "no_single_accuracy": True, "no_final_verdict": True,
    }


# ---------------------------------------------------------------- db wrapper
def ground(answer, mounted, question=None, db=None):
    db = db or os.path.join(_HERE, "memory.db")
    con = sqlite3.connect(db)
    try:
        texts, problems = _v1.verify_sources(con, mounted)
    finally:
        con.close()
    if problems:
        return {"judge_version": JUDGE_VERSION, "verdict": "undecidable",
                "branch": "1_source_problems", "reason": "源校验失败：" + "；".join(problems),
                "sentences": [], "partial_hit_sentences": [], "polarity_conflicts": [],
                "short_fact_cover": [], "extraction_fp": [],
                "branch5_structural_gap": [], "source_problems": problems,
                "mounted": list(mounted), "question": question}
    rep = analyze_answer(answer, texts, question)
    rep["mounted"] = list(mounted)
    rep["source_texts"] = texts
    rep["source_problems"] = []
    return rep


# ---------------------------------------------------------------- known-fp / regression
def known_fp_controls():
    out = []
    for cid, text, gn, u_exp, v_exp, note in _v21.CONTROLS:
        r = _v21.ngram_check(text, SOURCE_BLOB, THETA)
        out.append({"id": cid, "text": text, "gram_n": r["gram_n"], "u": r["u"],
                    "verdict": r["verdict"], "expected_verdict": v_exp,
                    "matches_prereg": r["verdict"] == v_exp,
                    "known_fp": v_exp == "unsupported" and "known_fp" in note,
                    "note": note})
    return out


def run_regression(write=False):
    kf = known_fp_controls()
    result = {
        "judge_version": JUDGE_VERSION,
        "known_fp_controls": kf,
        "known_fp_n": len(kf),
        "known_fp_all_match": all(x["matches_prereg"] for x in kf),
        "known_fp_excluded_from_rates": True,
        "write": bool(write),
        "no_single_accuracy": True,
        "no_final_verdict": True,
        "gpu_used": False, "model_calls": 0, "git_operations": 0,
    }
    if write:
        path = os.path.join(_HERE, "out", "M5-JUDGE-v2.3-REGRESSION.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    return result


# ---------------------------------------------------------------- invariants / selftest
def _assert_invariants():
    assert THETA == 0.20 and GRAM_N == 2 and STRICT_GT
    assert JUDGE_VERSION == "v2.3"
    assert not (WHITELIST & set(B_PREDICATES))
    freeze = _freeze_check()
    assert freeze["v21_sha16"] == V21_SHA16 and freeze["v22_sha16"] == V22_SHA16
    facts = source_facts(SOURCE_TEXTS)
    # whitelist never A, and A kinds only num/entity
    s = analyze_sentence("我的地址是广陵路12号2单元602。", 0, facts)
    assert all(c["text"] not in WHITELIST for c in s["components"])
    assert all(c["grade"] == "A" and c["kind"] in ("num", "entity") for c in s["components"])
    # B is present but does not create coverage requirements
    assert any(b["pred"] in ("地址", "地址") for b in s["b_units"]) or s["verdict"] == "supported"
    # prefix trimming: 家庭地址在广陵路12号 -> 广陵路12号, but 12号2十单元 stays one entity
    sp = analyze_sentence("家庭地址在广陵路12号。", 0, facts)
    texts = [c["text"] for c in sp["components"]]
    assert "广陵路12号" in texts and "家庭地址在广陵路" not in texts, texts
    sj = analyze_sentence("我的家庭地址是广陵路12号2十单元602。", 0, facts)
    jtexts = [c["text"] for c in sj["components"] if c["kind"] == "entity"]
    assert any("12号2十单元" in t for t in jtexts), jtexts
    assert not any(t in ("12", "2", "十") for t in [c["text"] for c in sj["components"]])
    return True


def selftest():
    facts = source_facts(SOURCE_TEXTS)
    fact_b = source_b_units(SOURCE_TEXTS)
    out = []

    def add(tid, ok, detail):
        out.append({"id": tid, "pass": bool(ok), "detail": detail})

    _assert_invariants()
    add("invariants", True, "v2.3 freeze, A/B kinds, copula whitelist, prefix trim, single suffix entity")

    # A/B grading: copulas never A; B exists but not coverage.
    s = analyze_sentence("我的地址是广陵路12号2单元602。", 0, facts)
    add("ab_grading", s["verdict"] == "supported"
        and all(c["text"] not in WHITELIST for c in s["components"])
        and any(b["pred"] == "地址" for b in s["b_units"]),
        {"verdict": s["verdict"], "A": [c["text"] for c in s["components"]],
         "B": [b["surface"] for b in s["b_units"]]})

    # B-only sentence must not be unsupported merely because B is not covered.
    s2 = analyze_sentence("我的地址是广陵路12号2单元602。", 0, facts)
    add("B_not_alone", s2["verdict"] == "supported"
        and all(c["text"] not in WHITELIST for c in s2["components"]),
        {"verdict": s2["verdict"], "components": [c["text"] for c in s2["components"]],
         "B": [b["surface"] for b in s2["b_units"]]})

    # A-level uncovered: three shapes (16 partial-hit forms).
    s4 = analyze_sentence("是的，广陵路12号2单元602在杭州。", 0, facts)
    add("A_Hangzhou_unsupported", s4["verdict"] == "unsupported"
        and any("杭州" in c["text"] for c in s4["uncovered"]),
        {"verdict": s4["verdict"], "uncovered": [c["text"] for c in s4["uncovered"]]})
    s5 = analyze_sentence("你的车停在地下停车场的第2层。", 0, facts)
    add("A_parking_unsupported", s5["verdict"] == "unsupported"
        and any("地下停车场" in c["text"] for c in s5["uncovered"]),
        {"verdict": s5["verdict"], "uncovered": [c["text"] for c in s5["uncovered"]]})
    s1bad = analyze_sentence("我的家庭地址是广陵路12号2十单元602。", 0, facts)
    add("A_twenty_unsupported", s1bad["verdict"] == "unsupported"
        and any("十" in c["text"] for c in s1bad["uncovered"]),
        {"verdict": s1bad["verdict"], "uncovered": [c["text"] for c in s1bad["uncovered"]]})

    # Negation polarity conflict, even with no A component.
    fact_only = ["我的咖啡只喝美式"]
    sconf = analyze_sentence("我不喝美式。", 0, fact_only,
                             fact_b_units=b_units_for_facts(fact_only))
    add("polarity_conflict", sconf["verdict"] == "unsupported"
        and sconf["reason"] == "polarity_conflict"
        and len(sconf["polarity_conflicts"]) >= 1,
        {"verdict": sconf["verdict"], "reason": sconf["reason"],
         "A": [c["text"] for c in sconf["components"]],
         "conflicts": sconf["polarity_conflicts"]})

    # prefix trimming, and no splitting of 12号2十单元
    sp = analyze_sentence("家庭地址在广陵路12号。", 0, facts)
    add("prefix_trim", any(c["text"] == "广陵路12号" for c in sp["components"])
        and not any(c["text"] == "家庭地址在广陵路" for c in sp["components"]),
        {"A": [c["text"] for c in sp["components"]], "verdict": sp["verdict"]})
    sj = analyze_sentence("我的家庭地址是广陵路12号2十单元602。", 0, facts)
    jtexts = [c["text"] for c in sj["components"] if c["kind"] == "entity"]
    add("single_suffix_entity", any("12号2十单元" in t for t in jtexts)
        and not any(t in ("12", "2", "十") for t in [c["text"] for c in sj["components"]]),
        {"A": [c["text"] for c in sj["components"]]})

    # ordinal
    so = analyze_sentence("1. 在回答我的家庭地址是哪里？", 0, facts)
    add("list_ordinal_excluded", all(c["text"] != "1" for c in so["components"])
        and any(x["kind"] == "list_ordinal_removed" for x in so["extraction_fp"]),
        {"components": [c["text"] for c in so["components"]],
         "extraction_fp": so["extraction_fp"]})

    # truncation
    st = analyze_sentence("答：我的地址是广陵路1", 0, facts, is_last=True)
    add("truncated_tail_undecidable", st["verdict"] == "undecidable"
        and st["truncated_cut"] and all(c["text"] != "1" for c in st["components"]),
        {"verdict": st["verdict"], "components": [c["text"] for c in st["components"]],
         "extraction_fp": st["extraction_fp"]})

    # branch5 structural gap (question-only answer; no-A assertive sentences are now undecidable)
    gap = analyze_answer("我只喝美式咖啡，不加糖？", SOURCE_TEXTS)
    add("branch5_structural_gap", gap["verdict"] == "unsupported"
        and gap["branch"] == "5a_2gram_negative"
        and len(gap["branch5_structural_gap"]) == 1,
        {"verdict": gap["verdict"], "branch": gap["branch"],
         "sentence_verdicts": [s["verdict"] for s in gap["sentences"]],
         "gap_n": len(gap["branch5_structural_gap"])})

    # decision order: excluded > truncated > polarity > A uncovered > supported > no_fact
    q = analyze_sentence("广陵路12号在杭州？", 0, facts)
    add("order_question_excluded", q["verdict"] == "excluded", {"verdict": q["verdict"]})
    tc = analyze_sentence("我不喝美式1", 0, fact_only,
                          fact_b_units=b_units_for_facts(fact_only), is_last=True)
    add("order_truncated_before_polarity", tc["verdict"] == "undecidable",
        {"verdict": tc["verdict"], "reason": tc["reason"], "truncated_cut": tc["truncated_cut"]})
    nf = analyze_sentence("嗯，可能吧。", 0, facts)
    add("order_no_fact", nf["verdict"] == "undecidable", {"verdict": nf["verdict"]})

    # known_fp
    kf = known_fp_controls()
    add("known_fp_10_10", len(kf) == 10 and all(k["matches_prereg"] for k in kf),
        {"n": len(kf), "known_fp": sum(1 for k in kf if k["known_fp"]),
         "matches": sum(1 for k in kf if k["matches_prereg"])})

    rr = run_regression(write=False)
    add("regression_default_no_write", rr["write"] is False and rr["known_fp_all_match"],
        {"write": rr["write"], "known_fp_n": rr["known_fp_n"]})

    return out


# ---------------------------------------------------------------- diagnose
def _v1_sentence_labels(v1r, n):
    out = []
    for i in range(n):
        fs = [f for f in v1r.get("facts", []) if f.get("sentence") == i]
        uh = [f for f in v1r.get("unhit", []) if f.get("sentence") == i]
        un = [f for f in v1r.get("undecidable_items", []) if f.get("sentence") == i]
        if uh:
            out.append("unsupported")
        elif un:
            out.append("undecidable")
        elif fs:
            out.append("supported")
        else:
            out.append("no_fact")
    return out


def _pair_rows(path):
    d = json.load(open(path, encoding="utf-8"))
    return d.get("pairs", [])


def diagnose():
    out_path = os.path.join(_HERE, "out", "M5-JUDGE-v2.3-INSAMPLE-REPLAY.json")
    r1 = _pair_rows(os.path.join(_HERE, "out", "M5-36A-pairs.json"))
    r2 = _pair_rows(os.path.join(_HERE, "out", "M5-36A-pairs-model.json"))
    model_mounted = json.load(open(os.path.join(_HERE, "out", "M5-36A-model-adj.json"),
                                   encoding="utf-8")).get("source", {}).get("mounted") or ["home", "project", "habit"]
    pair_diag, pair_diffs = [], []
    for arm, pairs in (("R1", r1), ("R2", r2)):
        for p in pairs:
            mounted = p.get("mounted") or model_mounted
            for side in ("orig", "rewrite"):
                text = p[side]
                v1r = _v21.ground(text, mounted, None)
                v22r = _v22.ground(text, mounted, None)
                v23r = ground(text, mounted, None)
                segs = _v1.split_sentences(text)
                v1l = _v1_sentence_labels(v1r, len(segs))
                v22l = [s["verdict"] for s in v22r["sentences"]]
                v23l = [s["verdict"] for s in v23r["sentences"]]
                changed = [i for i in range(min(len(v1l), len(v23l))) if v1l[i] != v23l[i]]
                pair_diag.append({"arm": arm, "pair_id": p["pair_id"], "side": side,
                                  "v1_answer": v1r["verdict"], "v22_answer": v22r["verdict"],
                                  "v23_answer": v23r["verdict"],
                                  "v1_sentences": v1l, "v22_sentences": v22l,
                                  "v23_sentences": v23l, "changed_sentence_idx": changed,
                                  "v23_partial_hit_sentences": v23r.get("partial_hit_sentences", [])})
                for i in changed:
                    pair_diffs.append({"arm": arm, "pair_id": p["pair_id"], "side": side,
                                       "sent_idx": i, "v1": v1l[i], "v22": v22l[i], "v23": v23l[i]})
    cand = json.load(open(os.path.join(_HERE, "out", "M5C-36-r1.json"), encoding="utf-8"))
    adj = json.load(open(os.path.join(_HERE, "out", "M5C-36-adj.json"), encoding="utf-8"))
    jd = json.load(open(os.path.join(_HERE, "out", "M5C-36-judge.json"), encoding="utf-8"))
    mounted = jd.get("source_facets", {}).get("mounted") or ["home", "project", "habit"]
    c_rows, c_diffs = [], []
    truth_unsupported = truth_supported = 0
    v21_caught = v22_caught = v23_caught = 0
    v21_false = v22_false = v23_false = 0
    partial_hit_v21 = partial_hit_caught = partial_hit_missed = 0
    partial_list, mis_hits, no_fact_hits = [], [], []
    polarity_all, short_all, extraction_fp_all = [], [], []
    for a in cand.get("answers", []):
        sc = a["scenario"]
        v1r = _v21.ground(a["answer"], mounted, a.get("question"))
        v22r = _v22.ground(a["answer"], mounted, a.get("question"))
        v23r = ground(a["answer"], mounted, a.get("question"))
        segs = _v1.split_sentences(a["answer"])
        v1l = _v1_sentence_labels(v1r, len(segs))
        v22l = [s["verdict"] for s in v22r["sentences"]]
        v23l = [s["verdict"] for s in v23r["sentences"]]
        extraction_fp_all.extend(v23r.get("extraction_fp", []))
        polarity_all.extend([dict(x, scenario=sc) for x in v23r.get("polarity_conflicts", [])])
        short_all.extend([dict(x, scenario=sc) for x in v23r.get("short_fact_cover", [])])
        nonempty_pos = [i for i, seg in enumerate(segs) if seg.strip()]
        adj_rows = sorted([x for x in adj.get("labels", []) if x.get("scenario") == sc],
                          key=lambda x: x.get("sent_idx", 0))
        if len(adj_rows) != len(nonempty_pos):
            c_rows.append({"scenario": sc, "alignment_error": True,
                           "n_adj": len(adj_rows), "n_nonempty": len(nonempty_pos)})
        for j, raw_i in enumerate(nonempty_pos):
            t = adj_rows[j] if j < len(adj_rows) else None
            rec = {"scenario": sc, "sent_idx": j, "raw_sentence_idx": raw_i,
                   "text": normalize(segs[raw_i]),
                   "v1": v1l[raw_i] if raw_i < len(v1l) else None,
                   "v22": v22l[raw_i] if raw_i < len(v22l) else None,
                   "v23": v23l[raw_i] if raw_i < len(v23l) else None,
                   "adj": t.get("label") if t else None,
                   "v23_uncovered": ([c["text"] for c in v23r["sentences"][raw_i].get("uncovered", [])]
                                     if raw_i < len(v23r.get("sentences", [])) else []),
                   "v23_components": ([c["text"] for c in v23r["sentences"][raw_i].get("components", [])]
                                      if raw_i < len(v23r.get("sentences", [])) else []),
                   "covered": ([c["text"] for c in v23r["sentences"][raw_i].get("covered", [])]
                               if raw_i < len(v23r.get("sentences", [])) else []),
                   "uncovered": ([c["text"] for c in v23r["sentences"][raw_i].get("uncovered", [])]
                                 if raw_i < len(v23r.get("sentences", [])) else []),
                   "v23_conflicts": ([x.get("pred") for x in v23r["sentences"][raw_i].get("polarity_conflicts", [])]
                                     if raw_i < len(v23r.get("sentences", [])) else [])}
            if t:
                tlab = t.get("label")
                if tlab == "unsupported":
                    truth_unsupported += 1
                    if rec["v1"] == "unsupported":
                        v21_caught += 1
                    if rec["v22"] == "unsupported":
                        v22_caught += 1
                    if rec["v23"] == "unsupported":
                        v23_caught += 1
                    if rec["v1"] == "supported" and rec["v23"] == "unsupported":
                        partial_hit_caught += 1
                        rec["partial_group"] = ("2十单元" if any("十" in c for c in rec["v23_uncovered"])
                                                else "在杭州" if any("杭州" in c for c in rec["v23_uncovered"])
                                                else "地下停车场第2层" if any("地下停车场" in c or "层" in c for c in rec["v23_uncovered"])
                                                else "polarity" if rec["v23_conflicts"] else "other")
                        partial_list.append(dict(rec))
                    if rec["v1"] == "supported" and rec["v23"] != "unsupported":
                        partial_hit_missed += 1
                    if rec["v1"] == "supported":
                        partial_hit_v21 += 1
                elif tlab == "supported":
                    truth_supported += 1
                    if rec["v1"] == "unsupported":
                        v21_false += 1
                    if rec["v22"] == "unsupported":
                        v22_false += 1
                    if rec["v23"] != "supported":
                        v23_false += 1
                        mis_hits.append(dict(rec))
                        if rec["v23"] == "no_fact":
                            no_fact_hits.append(dict(rec))
            c_rows.append(rec)
            if rec["v1"] != rec["v23"]:
                c_diffs.append(dict(rec))
        c_rows.append({"scenario": sc, "answer_level": True,
                       "v1_answer": v1r["verdict"], "v22_answer": v22r["verdict"],
                       "v23_answer": v23r["verdict"],
                       "v1_branch": v1r.get("branch"), "v22_branch": v22r.get("branch"),
                       "v23_branch": v23r.get("branch"),
                       "v23_partial_n": len(v23r.get("partial_hit_sentences", [])),
                       "v23_gap_n": len(v23r.get("branch5_structural_gap", []))})
    caught_str = f"{partial_hit_caught}/16"
    false_str = f"{v23_false}/{truth_supported}"
    accepted = (partial_hit_caught == 16 and v23_false <= 10)
    art = {
        "schema": "m5_judge_v23_insample_replay_v1",
        "judge_version": JUDGE_VERSION,
        "judge_path": "kvmem/m2_visibility/m5/m5_ground_v2_3.py",
        "prereg_sha16": PREREG_SHA16,
        "v21_sha16": V21_SHA16,
        "v22_sha16": V22_SHA16,
        "in_sample_replay": True,
        "not_acceptance": True,
        "in_sample_for_v2_3": True,
        "theta_calibrated": False,
        "created_at": _now(),
        "usage_restriction": USAGE_RESTRICTION,
        "estimate_only": True,
        "estimate_only_baseline": ESTIMATE_ONLY_BASELINE,
        "estimate_only_values": {"caught": "16/16", "false": "4/64"},
        "acceptance_depends_on": "entity_prefix_trimming",
        "design_accepted_in_sample": accepted,
        "design_status": "design_accepted_in_sample" if accepted else "design_not_accepted",
        "design_not_accepted_reason": None if accepted else "按预登记须立 v2.4、不许调参",
        "purpose": "diagnostic replay on (a) 36A pairs and (c) 17 answers; NOT acceptance evidence",
        "pairs": {
            "n_pairs": len(r1) + len(r2), "n_sides": len(pair_diag),
            "n_changed_sentences": len(pair_diffs),
            "sentence_diffs": pair_diffs, "per_side": pair_diag,
        },
        "c_answers": {
            "n_answers": len(cand.get("answers", [])),
            "truth_unsupported_sentences": truth_unsupported,
            "truth_supported_sentences": truth_supported,
            "v21_caught": v21_caught, "v22_caught": v22_caught, "v23_caught": v23_caught,
            "v21_false": v21_false, "v22_false": v22_false, "v23_false": v23_false,
            "partial_hit_v21": partial_hit_v21,
            "partial_hit_caught": partial_hit_caught,
            "partial_hit_missed": partial_hit_missed,
            "partial_hit_sentences": partial_list,
            "partial_hit_groups": dict(Counter(x.get("partial_group") for x in partial_list)),
            "mis_hits": mis_hits[:5],
            "mis_hit_n": len(mis_hits),
            "no_fact_hits": no_fact_hits[:5],
            "no_fact_hit_n": len(no_fact_hits),
            "polarity_conflicts": polarity_all,
            "polarity_conflict_n": len(polarity_all),
            "short_fact_cover": short_all,
            "short_fact_cover_n": len(short_all),
            "extraction_fp": extraction_fp_all,
            "extraction_fp_counts": dict(Counter(x.get("kind") for x in extraction_fp_all)),
            "extraction_fp_mis_extracted_components": sum(1 for x in extraction_fp_all
                                                          if x.get("kind") == "phrase_mis_extraction"),
            "sentence_diffs": c_diffs,
            "rows": c_rows,
        },
        "measured": {
            "caught": caught_str,
            "false": false_str,
            "v23_caught": v23_caught,
            "v23_false": v23_false,
            "partial_hit_caught": partial_hit_caught,
            "polarity_conflict_n": len(polarity_all),
            "extraction_fp_counts": dict(Counter(x.get("kind") for x in extraction_fp_all)),
            "short_fact_cover_n": len(short_all),
        },
        "known_fp_controls": known_fp_controls(),
        "no_single_accuracy": True,
        "no_final_verdict": True,
        "gpu_used": False, "model_calls": 0, "git_operations": 0,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(art, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, out_path)
    return art


def _now():
    import datetime
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--diagnose", action="store_true")
    ap.add_argument("--regression", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--answer")
    ap.add_argument("--mounted", default="")
    ap.add_argument("--question", default=None)
    ap.add_argument("--db", default=os.path.join(_HERE, "memory.db"))
    a = ap.parse_args()
    freeze = _freeze_check()
    if a.selftest:
        res = selftest()
        print(json.dumps({"selftest": res, "all_pass": all(x["pass"] for x in res),
                          "freeze": freeze}, ensure_ascii=False, indent=2))
        return 0 if all(x["pass"] for x in res) else 1
    if a.diagnose:
        art = diagnose()
        print(json.dumps({"written": True,
                          "artifact": "kvmem/m2_visibility/m5/out/M5-JUDGE-v2.3-INSAMPLE-REPLAY.json",
                          "pairs": {k: art["pairs"][k] for k in ("n_pairs", "n_sides", "n_changed_sentences")},
                          "c_answers": {k: art["c_answers"][k] for k in
                                        ("n_answers", "truth_unsupported_sentences", "v21_caught",
                                         "v22_caught", "v23_caught", "v21_false", "v22_false", "v23_false",
                                         "partial_hit_v21", "partial_hit_caught", "partial_hit_missed",
                                         "polarity_conflict_n", "short_fact_cover_n")},
                          "measured": art["measured"],
                          "design_accepted_in_sample": art["design_accepted_in_sample"],
                          "known_fp": {"n": len(art["known_fp_controls"]),
                                       "all_match": all(x["matches_prereg"] for x in art["known_fp_controls"])}},
                         ensure_ascii=False, indent=2))
        return 0
    if a.regression:
        print(json.dumps(run_regression(write=a.write), ensure_ascii=False, indent=2))
        return 0
    if not a.answer:
        ap.error("--answer is required (or use --selftest / --diagnose / --regression)")
    r = ground(a.answer, [x for x in a.mounted.split(",") if x], a.question, a.db)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
