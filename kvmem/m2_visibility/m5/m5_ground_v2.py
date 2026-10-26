# -*- coding: utf-8 -*-
"""M5 judge **v2.1** -- implements docs/_work/PREREG-M5-JUDGE-v2.md (frozen).

supersedes: "m5_ground.py 86b7c501ab9904aa"
prereg: 6c77b56f406432aa (frozen on disk, 35,739 B)
        coordinate history (R1): handoff said 8330fa716ef32a28 / 34,373 B / 405 lines;
        first read 135d020fe35deee2 / 35,716 B / 411 lines; frozen on disk 6c77b56f406432aa
        / 35,739 B.  This implementation follows the frozen on-disk version; the chain is
        also recorded in the regression artifact under /prereg/.
threshold_theta: 0.20

What changed relative to v1 (only one thing, and only downwards):
  v1  branch 5  (`unhit==[] and undec==[] and facts==[]`)  ->  `supported`  ("抽不到硬事实")
  v2  branch 5  (`unhit==[] and undec==[] and facts==[]`)  ->  ② 2-gram negative-evidence
                                                              coverage check  (u > theta -> unsupported,
                                                              u <= theta -> supported)
                                                              ① |G| == 0     -> undecidable/no_fact
Branches 1-4 (source_problems / unhit / undecidable / facts-all-hit) are semantically
equivalent to v1; the form differs only in three purely mechanical rewrites (`pseg` hoisted
out of the branch body, `_v1.TRAD` alias, if/elif chain split into labelled branches).
(An earlier draft said "byte-for-byte v1"; that overstated it -- see audit R6.)

Discipline (prereg §B3/§B4):
  * v1 file is NOT modified, NOT monkeypatched; it is imported read-only for its extraction
    primitives (prep / is_cjk / split_sentences / extract / source_profile / verify_sources /
    p_hit / date_hit / a_hit / topic_word / BLACKLIST / INTERROG / SENT_END / CRITERIA).
    The ground() control flow below is a copy of v1's with branch 5 replaced (prereg §B4.3
    explicitly allows "复制 v1 代码后加分支"; monkeypatching is forbidden).
  * THETA / STOP / FRAME are source constants (prereg §B4.4) -- no env var, no CLI override,
    no runtime parameter reaches ground().  ngram_check() takes theta only so that the
    prereg-mandated five-band in-sample threshold table can be computed by the harness;
    ground() always passes the frozen THETA.
  * There is no path from a v1 `unsupported` to a v2 `supported`: branch 2 (unhit) is
    evaluated before branch 5 can be reached, and branch 5 can only subtract support.
    `_assert_invariants()` checks it structurally (branch order, |G|==0 <=> 5c_no_fact,
    branch-5 totality over the three verdicts) and is run by --selftest; --selftest also
    drives the 5c exit through `ground()` end-to-end, not only through `ngram_check()`.
"""
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import m5_ground as _v1                      # read-only reuse; v1 stays independently runnable

# ---------------------------------------------------------------- frozen coordinates
JUDGE_VERSION = "v2.1"
SUPERSEDES = "m5_ground.py 86b7c501ab9904aa"
SUPERSEDES_SHA16 = "86b7c501ab9904aa"
SUPERSEDES_BYTES = 18496
PREREG_SHA16 = "6c77b56f406432aa"             # frozen on-disk version (was 8330fa716ef32a28)
PREREG_BYTES = 35739
PREREG_SHA16_HANDOFF = "8330fa716ef32a28"     # coordinate given in the handoff, superseded
PREREG_SHA16_FIRST_READ = "135d020fe35deee2"  # intermediate draft first read (35,716 B / 411 lines)
THETA = 0.20                                 # prereg §C2: fixed in advance, mid band
GRAM_N = 2
STRICT_GT = True                             # prereg §B1.7: comparison is strictly u > theta

CRITERIA = _v1.CRITERIA
DB_DEFAULT = _v1.DB_DEFAULT
INTERROG = _v1.INTERROG
SENT_END = _v1.SENT_END
prep = _v1.prep
is_cjk = _v1.is_cjk
split_sentences = _v1.split_sentences
extract = _v1.extract
source_profile = _v1.source_profile
verify_sources = _v1.verify_sources
p_hit = _v1.p_hit
date_hit = _v1.date_hit
a_hit = _v1.a_hit
topic_word = _v1.topic_word

# prereg §B1 frozen set: v1 FUNC ∪ INTERROG chars ∪ {问, 答}, codepoint-sorted, no separator.
STOP = "不与个为久么也了什会儿几只吗吧呢和哪啊喝在地多少就很怎是样点的答能要谁都里问"
STOP_SET = frozenset(STOP)
# prereg §B1 frozen set: v1 BLACKLIST ∪ {习惯,记得,好像,大概,印象,平时,一般}, codepoint-sorted,
# joined with "\n".
FRAME = ("一般", "习惯", "代号", "公司", "单位", "印象", "号码", "名字", "品牌", "地址",
         "大概", "好像", "姓名", "学校", "密码", "平时", "年龄", "序列号", "手机号", "生日",
         "电话", "电话号码", "编号", "职业", "血型", "记得", "账号", "身份证", "车型", "车牌",
         "车牌号", "车牌照", "邮编", "项目代号")

STOP_SHA16 = hashlib.sha256(STOP.encode("utf-8")).hexdigest()[:16]
FRAME_SHA16 = hashlib.sha256("\n".join(FRAME).encode("utf-8")).hexdigest()[:16]

# frozen-set self-check: a single changed character invalidates the prereg (§B1/§C3.1)
if STOP_SHA16 != "a4406d0bd1de47c7":
    raise RuntimeError("STOP set drifted from the frozen prereg: %s" % STOP_SHA16)
if FRAME_SHA16 != "f7df16d8ba96e68f":
    raise RuntimeError("FRAME set drifted from the frozen prereg: %s" % FRAME_SHA16)
if set(FRAME) != frozenset(FRAME) or list(FRAME) != sorted(FRAME):
    raise RuntimeError("FRAME must be the codepoint-sorted set with no duplicates")

# self coordinates (computed, never embedded -- a file cannot contain its own hash)
JUDGE_PATH = os.path.abspath(__file__)
with open(JUDGE_PATH, "rb") as _f:
    _SELF = _f.read()
JUDGE_SHA16 = hashlib.sha256(_SELF).hexdigest()[:16]
JUDGE_BYTES = len(_SELF)


# ---------------------------------------------------------------- branch labels
B_SOURCE = "1_source_problems"
B_UNHIT = "2_unhit"
B_UNDEC = "3_undecidable"
B_FACTS = "4_facts_hit"
B_NEG = "5a_2gram_negative"
B_COVERED = "5b_ngram_covered"
B_NOFACT = "5c_no_fact"


def _empty_ngram(branch):
    # gram_n = |G| (how many testable 2-grams this side has); gram_size = n = 2
    return {"threshold": THETA, "gram_size": GRAM_N, "gram_n": 0, "miss_n": 0,
            "u": None, "miss_grams": [], "near_threshold": False, "applied": False,
            "branch": branch, "stop_sha16": STOP_SHA16, "frame_sha16": FRAME_SHA16}


def _resolve_branch5(ngram):
    """The complete branch-5 decision table (prereg §B0/§B2): facts==[] has exactly one exit.

    This is deliberately a pure function so that `_assert_invariants()` can assert the real
    truth table instead of a tautology (audit R3): |G|==0 <=> 5c_no_fact, and every completed
    branch 5 settles on one of the three verdict values (no fourth value, §B3).
    """
    if ngram["verdict"] == "unsupported":
        return "unsupported", "2gram_negative_evidence", B_NEG
    if ngram["verdict"] == "supported":
        return "supported", "no_fact_ngram_covered", B_COVERED
    return "undecidable", "no_fact_unverifiable", B_NOFACT


# ---------------------------------------------------------------- ② coverage check
def ngram_check(text, blob, theta=THETA):
    """Prereg §B1 / §B5 -- negative 2-gram evidence against the source blob.

    Literal transcription of the §B5 reference implementation.  Sentence splitting happens
    BEFORE prep() (prep turns ？ into ? and would otherwise eat the split point).  The
    `core.rstrip("。！？!?\\n")` + `core.endswith(("？","?"))` pair is kept exactly as §B5 has
    it; question clauses are excluded in practice by the INTERROG word test (§B1.2), which is
    why the two are OR-ed as in the reference.

    Returns {verdict, u, gram_n, miss_n, miss_grams, near_threshold, miss_sent}.
      verdict      : "unsupported" | "supported" | "undecidable"
      u            : |G_miss| / |G|, or None when |G| == 0
      gram_n       : |G|            (0 => ① no_fact -> undecidable)
      miss_n       : |G_miss|       (reporting only; the decision is u > theta)
      miss_sent    : sentence indices that contributed at least one miss gram (for `rewritten`)
    NB: §B5's `supported` return zeroes miss_n/miss_grams because of its tuple shape; here the
    true values are kept -- it changes no verdict (the cut is `u > theta`) and it is what
    §B1.8 needs in order to explain a near-threshold side.
    """
    grams = set()
    miss_sent = set()
    per_sent = []
    for idx, seg_raw in enumerate(split_sentences(text or "")):
        seg = prep(seg_raw)
        core = seg.rstrip("。！？!?\n")
        if core.endswith(("？", "?")) or any(t in seg for t in INTERROG):
            continue                                   # question clauses yield no negative evidence
        for fw in FRAME:                               # string layer first (order fixed by §B1.3)
            seg = seg.replace(fw, "")
        runs, cur = [], ""                             # char layer: only CJK outside STOP survives
        for ch in seg:
            if is_cjk(ch) and ch not in STOP_SET:
                cur += ch
            else:
                if cur:
                    runs.append(cur)
                    cur = ""
        if cur:
            runs.append(cur)
        local = set()
        for r in runs:
            for i in range(len(r) - 1):                # 2-grams strictly inside one run
                local.add(r[i:i + 2])
        if local:
            per_sent.append((idx, local))
            grams |= local

    if not grams:
        return {"verdict": "undecidable", "u": None, "gram_n": 0, "gram_size": GRAM_N,
                "miss_n": 0, "miss_grams": [], "near_threshold": False, "miss_sent": []}

    miss = sorted(g for g in grams if g not in blob)
    u = len(miss) / len(grams)
    for idx, local in per_sent:
        if any(g in miss for g in local):
            miss_sent.add(idx)
    if u > theta:
        return {"verdict": "unsupported", "u": u, "gram_n": len(grams), "gram_size": GRAM_N,
                "miss_n": len(miss), "miss_grams": miss, "near_threshold": False,
                "miss_sent": sorted(miss_sent)}
    return {"verdict": "supported", "u": u, "gram_n": len(grams), "gram_size": GRAM_N,
            "miss_n": len(miss), "miss_grams": miss, "near_threshold": 0 < u <= theta,
            "miss_sent": sorted(miss_sent)}


# ---------------------------------------------------------------- rewrite template (v1 verbatim)
def _rewritten(answer, segs, involved, question):
    template = "记忆里没有记录%s。" % topic_word(question)
    parts = []
    for i, seg in enumerate(segs):
        if i in involved:
            delim = seg[-1] if seg and seg[-1] in SENT_END else ""
            parts.append(template + (delim if delim == "\n" else ""))
        else:
            parts.append(seg)
    return "".join(parts)


def ground(answer, mounted, question=None, db=DB_DEFAULT, _nested=False):
    """Same signature as v1 `ground`.  Branch order is prereg §B0 (order is semantics)."""
    con = sqlite3.connect(db)
    try:
        texts, problems = verify_sources(con, mounted)
    finally:
        con.close()
    rep = {"criteria": CRITERIA, "mounted": list(mounted), "question": question,
           "source_problems": problems,
           "judge_version": JUDGE_VERSION, "judge_sha16": JUDGE_SHA16,
           "judge_path": "kvmem/m2_visibility/m5/m5_ground_v2.py",
           "supersedes": SUPERSEDES, "supersedes_sha16": SUPERSEDES_SHA16,
           "prereg": PREREG_SHA16, "threshold_theta": THETA}

    # branch 1 -- fail closed, coverage check never intervenes
    if problems:
        rep.update({"verdict": "undecidable", "reason": "源校验失败：" + "；".join(problems),
                    "facts": [], "hits": [], "unhit": [], "exempt": [],
                    "rewritten": answer, "rewritten_is_original": True,
                    "branch": B_SOURCE, "near_threshold": False,
                    "ngram": _empty_ngram(B_SOURCE)})
        return rep

    prof = source_profile(texts)
    segs = split_sentences(answer)
    facts, hits, unhit, exempt = [], [], [], []
    # v1 fact loop, unchanged (extract / mask / P/N/D/A / p_hit / exemption / recheck untouched)
    for idx, seg in enumerate(segs):
        for f in extract(seg, source_latin=prof["latin"]):
            rec = dict(f, sentence=idx)
            k, fam = f["key"], f["family"]
            ok = (a_hit(k, prof) if fam == "A" else date_hit(k, prof) if fam == "D"
                  else p_hit(k, prof) if fam == "P" else k in prof["nums"])
            rec["hit"] = bool(ok)
            facts.append(rec)
            if ok:
                hits.append(rec)
                continue
            pseg = prep(seg)
            pos = pseg.find(f["raw"])
            before = pseg[max(0, pos - 6):pos] if pos >= 0 else ""
            if any(x in before for x in ("不是", "而不是", "应该说", "并非")):
                rec["why"] = "否定/自我更正语境（§5.5）"
                exempt.append(rec)
                continue
            if fam == "N":
                if any(str(k) in (str(d[1]), str(d[2])) for d in prof["dates"] if d[0] in ("MD", "YMD")) \
                        and re.search(r"(单元|楼|栋|室|号|个|次|分)", pseg):
                    rec["why"] = "同一数字在源文日期里也出现（§5.4）"
                    exempt.append(rec)
                    continue
            if fam == "P" and f.get("origin") == "P-c" and all(
                    ch in prof["blob"] for ch in str(f["raw"])):
                rec["why"] = ("P-c 抽到的串未原样出现，但每个字都在源文里；"
                              "它更像普通短语而非专名，按 §5.7 记黄（§5 漏判优先于误判）")
                exempt.append(rec)
                continue
            unhit.append(rec)

    undec = [dict(f, why="含繁体字，不做繁简转换（§2.1.6）")
             for f in facts if any(ch in _v1.TRAD for ch in str(f["raw"]))]
    undec += [dict(e, why=e["why"]) for e in exempt if e.get("why", "").startswith("P-c")]
    ans_n = Counter(f["key"] for f in facts if f["family"] == "N")
    note = ("重复出现的数字：%s；按 §9 R3 子集判断，不计次数"
            % {k: c for k, c in ans_n.items() if c > 1}) if any(
                c > 1 for c in ans_n.values()) else None

    ngram = _empty_ngram(B_FACTS)
    involved = set()
    # branch 2 -- unhit: unsupported, never relaxed (and evaluated before branch 5)
    if unhit:
        verdict, reason, branch = "unsupported", "至少一个硬事实未命中，且不属豁免/黑名单", B_UNHIT
        involved = {u["sentence"] for u in unhit}
        ngram = _empty_ngram(B_UNHIT)
    # branch 3 -- brittle facts (traditional / P-c yellow card): undecidable, never relaxed
    elif undec:
        verdict, reason, branch = "undecidable", "；".join(sorted({u["why"] for u in undec})), B_UNDEC
        ngram = _empty_ngram(B_UNDEC)
    # branch 4 -- every extracted hard fact hit: supported (unchanged)
    elif facts:
        verdict, reason, branch = "supported", "全部硬事实命中", B_FACTS
        ngram = _empty_ngram(B_FACTS)
    # branch 5 -- facts == []: the ONLY change.  No path here reaches `supported` without
    # the coverage check passing (prereg §B0 invariant).
    else:
        ngram = ngram_check(answer, prof["blob"], THETA)
        verdict, reason, branch = _resolve_branch5(ngram)
        if branch == B_NEG:
            involved = set(ngram["miss_sent"])
        ngram = dict(ngram, threshold=THETA, gram_size=GRAM_N,
                     stop_sha16=STOP_SHA16, frame_sha16=FRAME_SHA16,
                     applied=True, branch=branch)
        ngram.pop("verdict", None)
        ngram.pop("miss_sent", None)

    rewritten = answer
    if verdict == "unsupported":
        rewritten = _rewritten(answer, segs, involved, question)

    rep.update({"verdict": verdict, "reason": reason, "branch": branch,
                "near_threshold": bool(ngram.get("near_threshold", False)),
                "ngram": ngram,
                "facts": [{"family": f["family"], "raw": f["raw"], "key": str(f["key"]),
                           "sentence": f["sentence"], "hit": f["hit"],
                           "origin": f.get("origin")} for f in facts],
                "hits": [{"family": h["family"], "raw": h["raw"]} for h in hits],
                "unhit": [{"family": u["family"], "raw": u["raw"], "sentence": u["sentence"]}
                          for u in unhit],
                "exempt": [{"family": e["family"], "raw": e["raw"], "why": e["why"]}
                           for e in exempt],
                "undecidable_items": undec, "multiset_note": note,
                "rewritten": rewritten,
                "rewritten_is_original": rewritten == answer})
    if verdict == "unsupported" and not _nested:
        rep["recheck"] = recheck(answer, rewritten, mounted, question, db,
                                 {(f["family"], str(f["key"])) for f in facts})
    return rep


def recheck(original, rewritten, mounted, question, db, before):
    """v1 recheck body, v1 nested judgement (prereg §B3: `recheck` is one line unchanged).

    The nested call is bound explicitly to `_v1.ground`: name resolution alone would have
    silently switched it to v2's nested judgement.  That switch was a deviation from §B3
    and is reverted here (audit R4); it only affects the `recheck_verdict` reporting field,
    never a pair verdict.
    """
    r = _v1.ground(rewritten, mounted, question, db, _nested=True)
    fresh = {(f["family"], str(f["key"])) for f in r["facts"]}
    added = fresh - before
    untouched = True
    for seg in split_sentences(rewritten):
        if "记忆里没有记录" in seg:
            continue
        if seg not in original:
            untouched = False
    return {"1_no_unhit_fact_left": not r["unhit"],
            "2_no_new_hard_fact": not added, "2_added": sorted(added),
            "3_supported_sentences_byte_identical": untouched,
            "4_no_apology_wording": not any(w in rewritten for w in ("不知道", "抱歉", "对不起")),
            "recheck_verdict": r["verdict"]}


# ---------------------------------------------------------------- guards / self-test
def _assert_invariants(blob):
    """Prereg §B3, as real assertions (audit R3 -- the old body was a tautology).

    Checks (i) branch order, (ii) |G|==0 <=> 5c_no_fact on the declared controls,
    (iii) every completed branch 5 settles on one of the three verdict values.
    """
    order = [B_SOURCE, B_UNHIT, B_UNDEC, B_FACTS, B_NEG, B_COVERED, B_NOFACT]
    assert order.index(B_UNHIT) < order.index(B_NEG) < order.index(B_COVERED)
    assert order.index(B_UNDEC) < order.index(B_COVERED)
    # (iii) the branch-5 table is total: no fourth verdict value, no unlabelled exit (§B3)
    produced = set()
    for nv in ("unsupported", "supported", "undecidable"):
        v, reason, b = _resolve_branch5({"verdict": nv})
        assert v in ("supported", "unsupported", "undecidable"), "分支 5 走完必得三值之一"
        assert b in (B_NEG, B_COVERED, B_NOFACT) and reason
        produced.add(b)
    assert produced == {B_NEG, B_COVERED, B_NOFACT}, "branch 5 must be exhaustive"
    # (ii) real data: |G| == 0  <=>  branch 5c_no_fact; |G|==0 can never be supported
    probes = [(cid, text, v_exp) for cid, text, _gn, _u, v_exp, _n in CONTROLS]
    probes += [("no_fact", text, "undecidable") for text in NO_FACT_SYNTHETIC]
    for cid, text, v_exp in probes:
        r = ngram_check(text, blob)
        v, _reason, b = _resolve_branch5(dict(r))
        assert v == v_exp == r["verdict"], "%s: verdict mismatch" % cid
        assert (r["gram_n"] == 0) == (b == B_NOFACT), "%s: |G|==0 <=> 5c violated" % cid
        if r["gram_n"] == 0:
            assert v == "undecidable" and b == B_NOFACT, "%s: |G|==0 must be 5c" % cid
    if THETA != 0.20 or GRAM_N != 2 or not STRICT_GT:
        raise AssertionError("frozen gate drifted")
    return True


# prereg §C5 controls: (text, |G|, u, expected v2 verdict) -- declared in advance, never tuned.
CONTROLS = (
    ("C1", "我住在杭州西湖边。", 5, 0.800, "unsupported", "same as P13"),
    ("C2", "我只喝龙井茶，不加糖。", 3, 0.667, "unsupported", "same as P25"),
    ("C3", "我的咖啡只喝美式，不加糖。", 3, 0.000, "supported", "same as P28"),
    ("C4", "嗯，可能吧。", 0, None, "undecidable", "① |G|==0 smoke test"),
    ("C5", "好像是吧。", 0, None, "undecidable", "① |G|==0 smoke test"),
    ("C6", "我喝美式咖啡，不加糖。", 4, 0.250, "unsupported", "known_fp same-sense/composition"),
    ("C7", "我家在广陵路。", 3, 0.333, "unsupported", "known_fp 我家 not in source"),
    ("C8", "我喝美式咖啡。", 3, 0.333, "unsupported", "known_fp composition gram 式咖"),
    ("C9", "它就定在那天上线。", 3, 0.667, "unsupported", "known_fp anaphora/ellipsis"),
    ("C10", "它们都一样。", 1, 1.000, "unsupported", "known_fp pure pronoun sentence"),
)
# §B2 requires ① to be covered by synthetic tests, not left as dead code.
NO_FACT_SYNTHETIC = ("嗯，可能吧。", "好像是吧。", "也就是说。")


def selftest():
    """Deterministic, model-free, GPU-free checks that the implementation is faithful."""
    texts = ["我住在广陵路 12 号 2 单元 602。", "项目代号蓝鲸，计划 3 月 14 日上线。",
             "我的咖啡只喝美式，不加糖。"]
    blob = prep("".join(texts))
    _assert_invariants(blob)
    out = []
    for cid, text, gn, u_exp, v_exp, note in CONTROLS:
        r = ngram_check(text, blob)
        # prereg §C5 quotes u to 3 decimal places
        ok = (r["gram_n"] == gn and r["verdict"] == v_exp and
              (u_exp is None or abs((r["u"] or 0.0) - u_exp) < 5e-4))
        out.append({"id": cid, "text": text, "gram_n": r["gram_n"], "u": r["u"],
                    "verdict": r["verdict"], "miss_grams": r["miss_grams"],
                    "expected_gram_n": gn, "expected_u": u_exp, "expected_verdict": v_exp,
                    "note": note, "pass": ok})
    for text in NO_FACT_SYNTHETIC:
        r = ngram_check(text, blob)
        out.append({"id": "no_fact", "text": text, "gram_n": r["gram_n"], "u": r["u"],
                    "verdict": r["verdict"], "expected_verdict": "undecidable",
                    "note": "§B2 ① synthetic (|G|==0 -> undecidable)", "pass":
                    r["verdict"] == "undecidable" and r["gram_n"] == 0})
    # R3/§B2: the 5c exit of ground() itself is exercised end-to-end (previously untested).
    # mounted=[] suffices: |G| depends on the answer text alone, and no source problem is
    # raised, so this stays deterministic, model-free and GPU-free.
    for text in NO_FACT_SYNTHETIC:
        g = ground(text, [], None, DB_DEFAULT)
        out.append({"id": "no_fact_ground", "text": text, "verdict": g["verdict"],
                    "branch": g["branch"], "reason": g["reason"],
                    "gram_n": g["ngram"].get("gram_n"), "mounted": [],
                    "expected_verdict": "undecidable", "expected_branch": B_NOFACT,
                    "note": "§B2 ① end-to-end ground(): |G|==0 -> undecidable / 5c_no_fact",
                    "pass": (g["verdict"] == "undecidable" and g["branch"] == B_NOFACT
                             and g["reason"] == "no_fact_unverifiable"
                             and g["ngram"].get("gram_n") == 0)})
    out.append({"id": "frozen_sets", "pass": STOP_SHA16 == "a4406d0bd1de47c7"
                and FRAME_SHA16 == "f7df16d8ba96e68f",
                "stop_sha16": STOP_SHA16, "frame_sha16": FRAME_SHA16,
                "note": "§B1 frozen STOP/FRAME reproduced byte-exactly"})
    out.append({"id": "invariants", "pass": True,
                "note": "§B3 branch order; |G|==0 <=> 5c; branch 5 total over 3 verdicts"})
    return out


# ---------------------------------------------------------------- regression harness (46 pairs)
_R1_PAIRS = "kvmem/m2_visibility/m5/out/M5-36A-pairs.json"
_R2_PAIRS = "kvmem/m2_visibility/m5/out/M5-36A-pairs-model.json"
_ADJ = "kvmem/m2_visibility/m5/out/M5-36A-adj.json"
_MODEL_ADJ = "kvmem/m2_visibility/m5/out/M5-36A-model-adj.json"
_REVIEW = "docs/_work/REVIEW-M5-36A-blind.json"
_V1_JUDGE = "kvmem/m2_visibility/m5/out/M5-36A-judge.json"
_V1_MODEL_JUDGE = "kvmem/m2_visibility/m5/out/M5-36A-model-judge.json"
_OUT = "kvmem/m2_visibility/m5/out/M5-JUDGE-v2-regression.json"
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))

# prereg §C1: the only 12 sides that can depend on theta, with the reference-implementation
# values the prereg fixed in advance.  A mismatch here aborts (prereg §C3.2) -- no retuning.
REFERENCE_U = {"P13": 0.800, "P25": 0.667, "P28": 0.000, "P22": 0.000, "P24": 0.000,
               "P26": 0.000, "P16": 0.000}
DEFECT_PINS = ("P13", "P25")
THETAS = (0.10, 0.15, 0.20, 0.25, 0.30)


def _abs(rel):
    return rel if os.path.isabs(rel) else os.path.join(_ROOT, rel)


def _load(rel):
    with open(_abs(rel), "r", encoding="utf-8") as f:
        return json.load(f)


def _sha16(rel):
    with open(_abs(rel), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def _bytes(rel):
    return os.path.getsize(_abs(rel))


def _rate(pairs_rows, sub_block=None):
    """§F3/§F4 pair-level leak/false on the rewrite side."""
    rows = [r for r in pairs_rows if sub_block is None or r["block"] == sub_block]
    leak_den = [r for r in rows if r["truth_label"]["orig"] == "unsupported"]
    false_den = [r for r in rows if r["truth_label"]["orig"] == "supported"]
    leak = [r["pair_id"] for r in leak_den if r["v2_label"]["rewrite"] == "supported"]
    false = [r["pair_id"] for r in false_den if r["v2_label"]["rewrite"] == "unsupported"]
    leak_v1 = [r["pair_id"] for r in leak_den if r["v1_label"]["rewrite"] == "supported"]
    false_v1 = [r["pair_id"] for r in false_den if r["v1_label"]["rewrite"] == "unsupported"]
    dec_leak_den = [r for r in leak_den if r["v2_label"]["rewrite"] != "undecidable"]
    dec_false_den = [r for r in false_den if r["v2_label"]["rewrite"] != "undecidable"]
    undec = [r["pair_id"] for r in rows if r["v2_label"]["rewrite"] == "undecidable"]
    return {
        "n_pairs": len(rows),
        "leak": {"num": len(leak), "den": len(leak_den), "pairs": leak,
                 "definition": "truth.orig==unsupported and judge.rewrite==supported",
                 "denominator": "pairs whose truth orig label is unsupported",
                 "v1_num": len(leak_v1), "v1_pairs": leak_v1},
        "false": {"num": len(false), "den": len(false_den), "pairs": false,
                  "definition": "truth.orig==supported and judge.rewrite==unsupported",
                  "denominator": "pairs whose truth orig label is supported",
                  "v1_num": len(false_v1), "v1_pairs": false_v1},
        "decidable": {"den_leak": len(dec_leak_den), "den_false": len(dec_false_den),
                      "note": "§F4 verdict != undecidable; identical to raw when undecidable==0"},
        "rewrite_undecidable": {"num": len(undec), "pairs": undec},
        "sample_size_note": "leak/false 分母 <10 ⇒ 样本量不足以给区间，仅装置可用性",
    }


def run_regression(write=False):
    """Build the 46-pair regression artifact.

    `write` defaults to False (audit R2): a plain re-run only prints/compares and must never
    touch out/M5-JUDGE-v2-regression.json, because any rewrite changes `created_at` and
    invalidates the sha16 recorded in the landing ledger.  Persisting requires an explicit
    `--write` on the CLI.
    """
    created_at = _now()
    selftests = selftest()

    r1 = _load(_R1_PAIRS)
    r2 = _load(_R2_PAIRS)
    adj = {p["pair_id"]: p for p in _load(_ADJ)["pairs"]}
    rev = {p["pair_id"]: p for p in _load(_REVIEW)["rows"]}
    madj = {p["pair_id"]: p for p in _load(_MODEL_ADJ)["pairs"]}
    v1j = {p["pair_id"]: p for p in _load(_V1_JUDGE)["rows"]}
    v1mj = {p["pair_id"]: p for p in _load(_V1_MODEL_JUDGE)["rows"]}
    model_mounted = _load(_MODEL_ADJ)["source"]["mounted"]

    # ---- truth: ADJ + REVIEW consensus (must be 30/30), model arm = model ADJ (single blind)
    truth1, agree = {}, 0
    for pid, a in adj.items():
        rv = rev[pid]
        same = a["adj_orig"] == rv["label_orig"] and a["adj_rewrite"] == rv["label_rewrite"]
        agree += int(same)
        truth1[pid] = {"orig": rv["label_orig"], "rewrite": rv["label_rewrite"],
                       "source": "ADJ(M5-36A-adj)+REVIEW(REVIEW-M5-36A-blind) 2-of-2 consensus",
                       "adj": {"orig": a["adj_orig"], "rewrite": a["adj_rewrite"]},
                       "review": {"orig": rv["label_orig"], "rewrite": rv["label_rewrite"]}}
    truth2 = {pid: {"orig": v["adj_orig"], "rewrite": v["adj_rewrite"],
                    "source": "model-arm ADJ only (single blind; §G weaker evidence)",
                    "adj": {"orig": v["adj_orig"], "rewrite": v["adj_rewrite"]}}
              for pid, v in madj.items()}

    # ---- run v1 (live, must reproduce the frozen v1 JUDGE) and v2 on every side
    rows, side_rows, v1_mismatch, ref_u_mismatch, abort_reason = [], [], [], [], None
    ref_u_rows = []
    arms = (("R1", "rule arm 30 pairs", r1["pairs"], truth1, v1j, "f0767d84c16c31bb"),
            ("R2", "model arm 16 accepted pairs", r2["pairs"], truth2, v1mj, "aa9e6106925657e1"))
    for arm, arm_name, pairs, truth, v1judge, pairs_sha in arms:
        for p in pairs:
            pid = p["pair_id"]
            mounted = p.get("mounted") or model_mounted
            block = ("baseline12" if p["orig"] == p["rewrite"] else
                     "rewrite18" if arm == "R1" else "model16")
            rec = {"arm": arm, "arm_name": arm_name, "pair_id": pid, "block": block,
                   "dim": p.get("dim"), "orig": p["orig"], "rewrite": p["rewrite"],
                   "pairs_sha16": pairs_sha, "sides": {}}
            for side in ("orig", "rewrite"):
                r1r = _v1.ground(p[side], mounted, None, DB_DEFAULT)
                r2r = ground(p[side], mounted, None, DB_DEFAULT)
                v1s, v2s, ts = r1r["verdict"], r2r["verdict"], truth[pid][side]
                if v1s != v1judge[pid]["judge_" + side]:
                    v1_mismatch.append({"arm": arm, "pair_id": pid, "side": side,
                                        "live_v1": v1s,
                                        "frozen_v1": v1judge[pid]["judge_" + side]})
                ng = r2r["ngram"]
                if r2r["branch"].startswith("5"):
                    ref_u_rows.append({
                        "arm": arm, "pair_id": pid, "side": side,
                        "gram_n": ng.get("gram_n"), "u": ng.get("u"),
                        "u_3dp": None if ng.get("u") is None else round(ng["u"], 3),
                        "miss_grams": ng.get("miss_grams", []),
                        "branch": r2r["branch"],
                        "prereg_c1_u": REFERENCE_U.get(pid),
                        "matches_prereg_c1": (None if pid not in REFERENCE_U
                                              or ng.get("u") is None
                                              else abs(ng["u"] - REFERENCE_U[pid]) < 5e-4)})
                if r2r["branch"].startswith("5") and ng.get("u") is not None and pid in REFERENCE_U:
                    if abs(ng["u"] - REFERENCE_U[pid]) > 5e-4:   # §C1 quotes u to 3dp
                        ref_u_mismatch.append({"pair_id": pid, "side": side, "u": ng["u"],
                                               "prereg_c1_u": REFERENCE_U[pid]})
                rec["sides"][side] = {
                    "v1": v1s, "v2": v2s, "truth": ts,
                    "facts_n": len(r1r["facts"]), "hits_n": len(r1r["hits"]),
                    "unhit_n": len(r1r["unhit"]), "undecidable_items_n": len(r1r["undecidable_items"]),
                    "branch": r2r["branch"], "reason_v1": r1r["reason"], "reason_v2": r2r["reason"],
                    "gram_n": ng.get("gram_n", 0) if r2r["branch"].startswith("5") else 0,
                    "miss_n": ng.get("miss_n", 0) if r2r["branch"].startswith("5") else 0,
                    "u": ng.get("u"), "miss_grams": ng.get("miss_grams", []),
                    "near_threshold": bool(r2r.get("near_threshold")),
                    "no_fact": r2r["branch"] == B_NOFACT,
                    # R4 trace: only unsupported sides carry a recheck; with v1 semantics the
                    # nested verdict is v1's.  Reporting field only -- no pair verdict uses it.
                    "recheck_verdict": (r2r.get("recheck") or {}).get("recheck_verdict"),
                    "v2_label_ok_vs_truth": v2s == ts,
                }
                side_rows.append({"arm": arm, "pair_id": pid, "side": side,
                                  **{k: rec["sides"][side][k] for k in
                                     ("v1", "v2", "truth", "branch", "gram_n", "miss_n", "u")}})
            rec["v1_label"] = {s: rec["sides"][s]["v1"] for s in ("orig", "rewrite")}
            rec["v2_label"] = {s: rec["sides"][s]["v2"] for s in ("orig", "rewrite")}
            rec["truth_label"] = {s: rec["sides"][s]["truth"] for s in ("orig", "rewrite")}
            changed_sides = [s for s in ("orig", "rewrite") if rec["sides"][s]["v1"] != rec["sides"][s]["v2"]]
            if not changed_sides:
                rec["change"] = "unchanged"
            elif pid in DEFECT_PINS and all(
                    rec["sides"][s]["v1"] == "supported" and rec["sides"][s]["v2"] == "unsupported"
                    and rec["sides"][s]["truth"] == "unsupported" for s in changed_sides):
                rec["change"] = "defect_fixed"
            else:
                rec["change"] = "unexpected"
            rec["changed_sides"] = changed_sides
            rows.append(rec)

    # ---- §D4 diff table: pair-level, only rows whose labels moved
    diff = []
    for r in rows:
        if r["change"] == "unchanged":
            continue
        side0 = r["changed_sides"][0]
        diff.append({
            "pair_id": r["pair_id"], "arm": r["arm"], "block": r["block"],
            "old_verdict": r["sides"][side0]["v1"],
            "new_verdict": r["sides"][side0]["v2"],
            "sides_changed": r["changed_sides"],
            "branch": r["sides"][side0]["branch"],
            "u": r["sides"][side0]["u"],
            "miss_grams": r["sides"][side0]["miss_grams"],
            "gram_n": r["sides"][side0]["gram_n"],
            "change": r["change"],
            "why": ("抽取器漏抽实体（层 a）+ 空事实默认 supported（层 b）："
                    "v2 只在 facts==[] 分支改用 2-gram 负证据覆盖率判定"
                    if r["change"] == "defect_fixed" else "未预期的标签变化（§H7.2 停手条件）"),
            "v1_judge_sha16": SUPERSEDES_SHA16, "v2_judge_sha16": JUDGE_SHA16,
        })

    # ---- threshold table (in-sample only; §C1/§C3)
    def verdict_at(side, theta):
        br = side["branch"]
        if br == B_SOURCE or br == B_UNDEC:
            return "undecidable"
        if br == B_UNHIT:
            return "unsupported"
        if br == B_FACTS:
            return "supported"
        if br == B_NOFACT:
            return "undecidable"
        u = side["u"]
        if u is None:
            return "undecidable"
        return "unsupported" if u > theta else "supported"

    thr = []
    for theta in THETAS:
        counts = {"supported": 0, "unsupported": 0, "undecidable": 0}
        miss = false = 0
        miss_pairs, false_pairs = [], []
        pair_side = {}
        for r in rows:
            for s in ("orig", "rewrite"):
                side = r["sides"][s]
                v = verdict_at(side, theta)
                counts[v] += 1
                if side["truth"] == "unsupported" and v == "supported":
                    miss += 1
                    miss_pairs.append({"pair_id": r["pair_id"], "side": s})
                if side["truth"] == "supported" and v == "unsupported":
                    false += 1
                    false_pairs.append({"pair_id": r["pair_id"], "side": s})
            pair_side[(r["arm"], r["pair_id"])] = (
                verdict_at(r["sides"]["rewrite"], theta),
                r["truth_label"]["rewrite"], r["block"])
        rw18 = [(v2, t) for (arm, pid), (v2, t, b) in pair_side.items() if b == "rewrite18"
                and arm == "R1"]
        leak_den = sum(1 for v2, t in rw18 if t == "unsupported")
        false_den = sum(1 for v2, t in rw18 if t == "supported")
        leak = sum(1 for v2, t in rw18 if t == "unsupported" and v2 == "supported")
        fls = sum(1 for v2, t in rw18 if t == "supported" and v2 == "unsupported")
        thr.append({
            "theta": theta,
            "main": abs(theta - THETA) < 1e-9,
            "declared_in_advance": abs(theta - THETA) < 1e-9,
            "sides_92": {"denominator": 92, **counts},
            "sides_92_missed": {"num": miss, "den": sum(counts.values()),
                                "note": "真值 unsupported 且 v2==supported（漏判，按 side）",
                                "sides": miss_pairs},
            "sides_92_false": {"num": false, "den": sum(counts.values()),
                               "note": "真值 supported 且 v2==unsupported（误判，按 side）",
                               "sides": false_pairs},
            "pairs_46": {
                "denominator": 46,
                "supported": sum(1 for v, t, b in pair_side.values() if v == "supported"),
                "unsupported": sum(1 for v, t, b in pair_side.values() if v == "unsupported"),
                "undecidable": sum(1 for v, t, b in pair_side.values() if v == "undecidable"),
                "missed": sum(1 for v, t, b in pair_side.values()
                              if t == "unsupported" and v == "supported"),
                "false": sum(1 for v, t, b in pair_side.values()
                             if t == "supported" and v == "unsupported"),
                "note": ("pair verdict = rewrite side (prereg §F1 main口径)；漏判/误判按 pair 计"
                         "（真值取 rewrite 侧标签），与 sides_92 的两类错误口径并列，不混用")},
            "rewrite18": {"leak": {"num": leak, "den": leak_den},
                          "false": {"num": fls, "den": false_den},
                          "note": "leak/false 分母同 §F3（truth orig unsupported / supported），非 18"},
            "in_sample": True,
            "note": ("in-sample；θ 由预登记 §C2 事先固定，本表只证明 θ 落在不改变 46 对标签的平台"
                     "上，不构成 θ 已被校准的证据"),
        })
    # sanity: the prereg's §C1 claim that all five bands are indistinguishable here
    distinct_bands = len({json.dumps([t["sides_92"], t["sides_92_missed"]["num"],
                                      t["sides_92_false"]["num"], t["rewrite18"]], sort_keys=True)
                          for t in thr})

    # ---- no_fact / near_threshold / u spectrum
    no_fact_lines = [{"arm": r["arm"], "pair_id": r["pair_id"], "side": s,
                      "text": r[s]} for r in rows for s in ("orig", "rewrite")
                     if r["sides"][s]["no_fact"]]
    near = [{"arm": r["arm"], "pair_id": r["pair_id"], "side": s, "u": r["sides"][s]["u"]}
            for r in rows for s in ("orig", "rewrite") if r["sides"][s]["near_threshold"]]
    us = sorted({round(r["sides"][s]["u"], 6) for r in rows for s in ("orig", "rewrite")
                 if r["sides"][s]["u"] is not None})

    # ---- rates (§F)
    r1_rows = [r for r in rows if r["arm"] == "R1"]
    r2_rows = [r for r in rows if r["arm"] == "R2"]
    rw18 = [r for r in r1_rows if r["block"] == "rewrite18"]
    bl12 = [r for r in r1_rows if r["block"] == "baseline12"]
    rates = {
        "rewrite18_main": dict(_rate(rw18), v1_leak="0/5", v1_false="0/13",
                               note=("主口径（§F1）；leak 分母 = 真值 orig unsupported 的 accepted 对，"
                                     "false 分母 = 真值 orig supported 的 accepted 对；"
                                     "对 v1 的 0/5、0/13 不得恶化")),
        "model16": dict(_rate(r2_rows), v1_leak="0/5", v1_false="0/11",
                        note="模型臂 16 accepted（§F2）；真值只有模型臂 ADJ 单方盲标（§G 注）"),
        "baseline12": {
            "n_pairs": len(bl12),
            "agreement_v2": sum(1 for r in bl12 if all(r["sides"][s]["v2"] == r["sides"][s]["truth"]
                                                       for s in ("orig", "rewrite"))),
            "agreement_v1": sum(1 for r in bl12 if all(r["sides"][s]["v1"] == r["sides"][s]["truth"]
                                                       for s in ("orig", "rewrite"))),
            "denominator": "12 baseline pairs (§F1: no leak/false denominators here)",
            "note": "并列留档，不设 leak/false 分母",
        },
        "all30_old_scope": dict(_rate(r1_rows), note="旧口径并列留档，不为主（§F6）"),
        "no_single_accuracy": True,
    }

    # ---- known false-positive controls (§C5), never counted in the two rates
    blob = prep("".join(["我住在广陵路 12 号 2 单元 602。", "项目代号蓝鲸，计划 3 月 14 日上线。",
                         "我的咖啡只喝美式，不加糖。"]))
    known_fp = []
    for cid, text, gn, u_exp, v_exp, note in CONTROLS:
        r = ngram_check(text, blob)
        known_fp.append({"id": cid, "text": text, "gram_n": r["gram_n"], "u": r["u"],
                         "verdict": r["verdict"], "miss_grams": r["miss_grams"],
                         "expected_verdict": v_exp, "matches_prereg": r["verdict"] == v_exp,
                         "known_fp": v_exp == "unsupported" and "known_fp" in note,
                         "note": note})

    # ---- abort gate (§C3.3 / §H7.2 / §D4 / §D3)
    unexpected = [r["pair_id"] for r in rows if r["change"] == "unexpected"]
    if v1_mismatch:
        abort_reason = ("v1 复跑与冻结 JUDGE 不符（%d 个 side），实现基准不可信，停手：%s"
                        % (len(v1_mismatch), json.dumps(v1_mismatch[:5], ensure_ascii=False)))
    elif ref_u_mismatch:
        abort_reason = ("实现算出的 u 与预登记 §C1 参考值不符（%d 个 side）：%s"
                        % (len(ref_u_mismatch), json.dumps(ref_u_mismatch[:5], ensure_ascii=False)))
    elif len(diff) > 2:
        abort_reason = ("差异表 %d 行 > 2（预登记 §D4）：%s；不得调 θ/词表，停手报告 LEAD"
                        % (len(diff), [d["pair_id"] for d in diff]))
    elif unexpected:
        abort_reason = "出现 unexpected 行（§H7.2），停手：%s" % unexpected
    else:
        m = rates["rewrite18_main"]
        if m["leak"]["num"] > 0 or m["false"]["num"] > 0:
            abort_reason = ("rewrite18 主口径相对 v1 (0/5, 0/13) 恶化：leak %d/%d, false %d/%d"
                            % (m["leak"]["num"], m["leak"]["den"],
                               m["false"]["num"], m["false"]["den"]))
    abort = abort_reason is not None

    # ---- five §D acceptance checks
    pins = {pid: [r for r in rows if r["pair_id"] == pid] for pid in DEFECT_PINS}
    pin_ok = all(
        all(r["sides"][s]["v2"] == "unsupported"
            and r["sides"][s]["branch"] == B_NEG
            and abs((r["sides"][s]["u"] or -1) - u) < 5e-4
            for r in pins[pid] for s in ("orig", "rewrite"))
        for pid, u in (("P13", 0.800), ("P25", 0.667)))
    others = [r for r in r1_rows if r["pair_id"] not in DEFECT_PINS]
    same28 = all(all(r["sides"][s]["v1"] == r["sides"][s]["v2"] for s in ("orig", "rewrite"))
                 for r in others)
    kept_supported = all(r["sides"][s]["v2"] == "supported"
                         for r in others if r["pair_id"] in ("P28", "P22", "P24", "P26", "P16")
                         for s in ("orig", "rewrite"))
    checks = [
        {"id": 1, "name": "P13/P25 -> unsupported (reason=2gram_negative_evidence, u=0.800/0.667)",
         "pass": bool(pin_ok), "detail": {
             pid: [{"side": s, "v2": r["sides"][s]["v2"], "branch": r["sides"][s]["branch"],
                    "u": r["sides"][s]["u"], "miss_grams": r["sides"][s]["miss_grams"]}
                   for r in pins[pid] for s in ("orig", "rewrite")] for pid in DEFECT_PINS}},
        {"id": 2, "name": "其余 28 对与 v1 逐对标签一致（含 P28/P22/P24/P26/P16 仍 supported）",
         "pass": bool(same28 and kept_supported),
         "detail": {"unchanged_28": same28, "real_supported_kept": kept_supported}},
        {"id": 3, "name": "rewrite18 主口径不恶化（leak 0/5, false 0/13; decidable 分母同报）",
         "pass": bool(rates["rewrite18_main"]["leak"]["num"] == 0
                      and rates["rewrite18_main"]["false"]["num"] == 0
                      and rates["rewrite18_main"]["leak"]["den"] == 5
                      and rates["rewrite18_main"]["false"]["den"] == 13),
         "detail": {"leak": rates["rewrite18_main"]["leak"],
                    "false": rates["rewrite18_main"]["false"],
                    "decidable": rates["rewrite18_main"]["decidable"],
                    "v1_baseline": {"leak": "0/5", "false": "0/13"}}},
        {"id": 4, "name": "差异表只 P13/P25 两行（>2 行 ⇒ 停手，不调阈值凑数）",
         "pass": bool(len(diff) == 2 and [d["pair_id"] for d in diff] == ["P13", "P25"]),
         "detail": {"rows": len(diff), "pairs": [d["pair_id"] for d in diff]}},
        {"id": 5, "name": "46 对全跑（R1 30 + R2 16，两 side 均判，真值不顶替）",
         "pass": bool(len(r1_rows) == 30 and len(r2_rows) == 16 and len(rows) == 46
                      and agree == 30 and _sha16(_R1_PAIRS) == "f0767d84c16c31bb"
                      and _sha16(_R2_PAIRS) == "aa9e6106925657e1"),
         "detail": {"R1": len(r1_rows), "R2": len(r2_rows), "adj_review_agreement": "%d/30" % agree,
                    "R1_sha16": _sha16(_R1_PAIRS), "R2_sha16": _sha16(_R2_PAIRS)}},
    ]
    v2_signable = bool(all(c["pass"] for c in checks) and not abort)

    # ---- R4: recheck semantics.  Prereg §B3 says `recheck` is untouched, so the nested
    # judgement is bound explicitly to v1.  Record every side that carried a recheck.
    recheck_sides = [{"arm": r["arm"], "pair_id": r["pair_id"], "side": s,
                      "recheck_verdict": r["sides"][s]["recheck_verdict"]}
                     for r in rows for s in ("orig", "rewrite")
                     if r["sides"][s]["recheck_verdict"]]
    # sides where v2 runs a recheck that v1 never ran (v1 verdict was not `unsupported`)
    recheck_newly_triggered = [{"arm": r["arm"], "pair_id": r["pair_id"], "side": s,
                                "v1_verdict": r["sides"][s]["v1"],
                                "recheck_verdict": r["sides"][s]["recheck_verdict"]}
                               for r in rows for s in ("orig", "rewrite")
                               if r["sides"][s]["recheck_verdict"]
                               and r["sides"][s]["v1"] != "unsupported"]
    recheck_semantics = {
        "value": "v1_unchanged",
        "authority": "预登记 §B3：`recheck` 一行不动",
        "implementation": ("recheck() 模板逐行复制 v1；嵌套判定显式绑定 _v1.ground，"
                           "v2 不再改变 recheck 语义"),
        "deviation_fixed": ("盘上 34afeef1ee02ba82 曾让嵌套 `ground` 按名字解析到 v2，"
                            "P13/P25 的 recheck_verdict 因此为 unsupported（v1 在该对不触发 recheck）；"
                            "本版按预登记回退，属对偏离的纠正，不是新的偏离"),
        "sides_with_recheck": recheck_sides,
        "newly_triggered_vs_v1": recheck_newly_triggered,
        "recheck_verdict_impact": ("none on any pair verdict：recheck_verdict 只是报告字段，"
                                   "46 对 verdict / 92 side 判定与 v2 关联字段不变"),
    }

    reg = {
        "schema": "m5_judge_v2_regression_v1",
        "task": "M5 judge v2.1 — prereg-locked implementation + 46-pair in-sample regression",
        "judge_version": JUDGE_VERSION,
        "judge_path": "kvmem/m2_visibility/m5/m5_ground_v2.py",
        "judge_sha16": JUDGE_SHA16, "judge_bytes": JUDGE_BYTES,
        "supersedes": SUPERSEDES, "supersedes_sha16": SUPERSEDES_SHA16,
        "supersedes_bytes": _bytes("kvmem/m2_visibility/m5/m5_ground.py"),
        "supersedes_untouched": _sha16("kvmem/m2_visibility/m5/m5_ground.py") == SUPERSEDES_SHA16
        and _bytes("kvmem/m2_visibility/m5/m5_ground.py") == SUPERSEDES_BYTES,
        "prereg": {
            "sha16": PREREG_SHA16, "bytes": PREREG_BYTES,
            "path": "docs/_work/PREREG-M5-JUDGE-v2.md",
            "observed_sha16": _sha16("docs/_work/PREREG-M5-JUDGE-v2.md"),
            "observed_bytes": _bytes("docs/_work/PREREG-M5-JUDGE-v2.md"),
            "observed_matches_coordinate": (
                _sha16("docs/_work/PREREG-M5-JUDGE-v2.md") == PREREG_SHA16
                and _bytes("docs/_work/PREREG-M5-JUDGE-v2.md") == PREREG_BYTES),
            "coordinate_history": [
                {"stage": "handoff", "sha16": PREREG_SHA16_HANDOFF,
                 "bytes": 34373, "lines": 405,
                 "status": "superseded; never the frozen text. The old source/regression "
                           "cited this as `prereg` (audit R1)."},
                {"stage": "first_read", "sha16": PREREG_SHA16_FIRST_READ,
                 "bytes": 35716, "lines": 411,
                 "status": "intermediate draft seen at first read; superseded before any v2 "
                           "result was written, carries no result-fitting risk"},
                {"stage": "frozen_on_disk", "sha16": PREREG_SHA16,
                 "bytes": PREREG_BYTES, "lines": 411,
                 "status": "the version this implementation follows and now cites"}],
            "note": ("R1：源码与回归件原先把已取代稿 8330fa716ef32a28 标为 prereg。现统一改指盘上冻结版 "
                     "6c77b56f406432aa / 35,739 B；8330fa71 / 34,373 / 405 行是任务书坐标，"
                     "135d020f / 35,716 / 411 行是首读中间稿，两者均不再作为实现坐标。"
                     "内容与预登记 §B/§B5/§C/§D 逐条一致（五档不可区分、θ=0.20 固档、差异只许 "
                     "P13/P25），坐标链在此单件可读；未据此改动任何判定/阈值/词表"),
        },
        "threshold_theta": THETA,
        "recheck_semantics": recheck_semantics,
        "gate": {"theta": THETA, "stop_sha16": STOP_SHA16, "frame_sha16": FRAME_SHA16,
                 "question_clause_excluded": True, "no_fact_rule": "|G|==0",
                 "gram_n": GRAM_N, "strict_gt": STRICT_GT,
                 "theta_not_runtime_overridable": True,
                 "frozen_sets_verified": True,
                 "note": "§C3.1 θ/STOP/FRAME/问句排除/|G|==0 在落盘前不得改动；实现内为源码常量"},
        "inputs": {
            "R1_pairs": {"path": _R1_PAIRS, "sha16": _sha16(_R1_PAIRS), "bytes": _bytes(_R1_PAIRS),
                         "count": len(r1["pairs"])},
            "R2_pairs": {"path": _R2_PAIRS, "sha16": _sha16(_R2_PAIRS), "bytes": _bytes(_R2_PAIRS),
                         "count": len(r2["pairs"])},
            "adj": {"path": _ADJ, "sha16": _sha16(_ADJ)}, "review": {"path": _REVIEW, "sha16": _sha16(_REVIEW)},
            "model_adj": {"path": _MODEL_ADJ, "sha16": _sha16(_MODEL_ADJ)},
            "v1_judge": {"path": _V1_JUDGE, "sha16": _sha16(_V1_JUDGE)},
            "v1_model_judge": {"path": _V1_MODEL_JUDGE, "sha16": _sha16(_V1_MODEL_JUDGE)},
            "truth_consensus": {"adj_vs_review": "%d/30" % agree,
                                "rule": "§D2/§G: R1 truth = ADJ∩REVIEW 2-of-2; R2 truth = model ADJ only",
                                "model_arm_note": "R2 单方 ADJ，证据等级低于 R1，不得替代 rewrite18 主口径"},
        },
        "per_pair": [{k: r[k] for k in ("arm", "pair_id", "block", "dim", "orig", "rewrite",
                                        "v1_label", "v2_label", "truth_label", "change",
                                        "changed_sides")} | {"sides": r["sides"]} for r in rows],
        "diff_vs_v1": diff,
        "rows": [{"arm": r["arm"], "pair_id": r["pair_id"], "side": s,
                  "verdict_v1": r["sides"][s]["v1"], "verdict_v2": r["sides"][s]["v2"],
                  "v1_label": r["sides"][s]["v1"], "v2_label": r["sides"][s]["v2"],
                  "truth": r["sides"][s]["truth"], "facts_n": r["sides"][s]["facts_n"],
                  "unhit_n": r["sides"][s]["unhit_n"], "gram_n": r["sides"][s]["gram_n"],
                  "miss_n": r["sides"][s]["miss_n"], "u": r["sides"][s]["u"],
                  "branch": r["sides"][s]["branch"],
                  "near_threshold": r["sides"][s]["near_threshold"],
                  "miss_grams": r["sides"][s]["miss_grams"],
                  "recheck_verdict": r["sides"][s]["recheck_verdict"],
                  "reason_v1": r["sides"][s]["reason_v1"],
                  "reason_v2": r["sides"][s]["reason_v2"]}
                 for r in rows for s in ("orig", "rewrite")],
        "threshold_table": thr,
        "threshold_table_in_sample": True,
        "threshold_table_note": ("五个 θ 档在 46 对上完全不可区分（u 谱只有 %s，五档全落在真空区；"
                                 "实测五档读数只有 %d 种；§C1 的「五档不可区分」成立）；"
                                 "回归集对 θ 没有标定能力，本表只证明 θ 落在不改标签的平台上"
                                 % (us, distinct_bands)),
        "rates": rates,
        "no_fact_lines": no_fact_lines,
        "no_fact_lines_note": ("预测为 0（预登记 §C1/F6）：本回归没有「剔完 STOP/FRAME 后无可检 2-gram」"
                               "的软表述；① 的活性由 selftest 的三条合成句覆盖（ngram_check 层 + "
                               "ground() 端到端层），未留死代码"),
        "prereg_c1_u_check": ref_u_rows,
        "near_threshold": near,
        "u_spectrum": us,
        "known_fp_controls": known_fp,
        "selftest": selftests,
        "counts": {
            "pairs_total": len(rows), "sides_total": len(rows) * 2,
            "R1": len(r1_rows), "R2": len(r2_rows),
            "baseline12": len(bl12), "rewrite18": len(rw18),
            "diff_rows": len(diff),
            "no_fact_undecidable_count": len(no_fact_lines),
            "near_threshold_count": len(near),
            "unexpected_rows": len(unexpected),
            "decidable_denominators": {
                "rewrite18": rates["rewrite18_main"]["decidable"],
                "model16": rates["model16"]["decidable"]},
            "v2_verdict_distribution": {
                "sides": {v: sum(1 for r in rows for s in ("orig", "rewrite")
                                 if r["sides"][s]["v2"] == v)
                          for v in ("supported", "unsupported", "undecidable")}},
            "known_fp_controls": {"count": len(known_fp),
                                  "all_match_prereg": all(k["matches_prereg"] for k in known_fp),
                                  "known_fp_count": sum(1 for k in known_fp if k["known_fp"]),
                                  "note": "C6-C10 为预登记事先声明的已知误伤，单列，不进任何两率"},
            "v1_verdict_distribution": {
                "sides": {v: sum(1 for r in rows for s in ("orig", "rewrite")
                                 if r["sides"][s]["v1"] == v)
                          for v in ("supported", "unsupported", "undecidable")}},
        },
        "blocks": {"baseline12": [r["pair_id"] for r in bl12],
                   "rewrite18": [r["pair_id"] for r in rw18],
                   "model16": [r["pair_id"] for r in r2_rows]},
        "fitting_disclosure": {
            "frame_habit_is_load_bearing": True,
            "detail": ("§B1 披露：FRAME 的 34 项里只有「习惯」在 46 对回归上承重（去掉它 P26 的 u "
                       "从 0.000 变 0.400 ⇒ 变 unsupported ⇒ 差异表 3 行 + false 1/13）。其余 6 个新增"
                       "成员（记得/好像/大概/印象/平时/一般）在 12 个 no-fact side 上均不出现，本回归集"
                       "影响为空。这是 in-sample 拟合成分，不得作为「已校准」宣称。"),
            "question_exclusion_is_load_bearing": True,
            "theta_is_not_load_bearing": True,
            "note": "§C4：样本内承重旋钮 = FRAME 含「习惯」+ 问句排除；θ 本身不承重",
        },
        "corrections": (
            [{"kind": "判定差异", "pair_id": d["pair_id"], "side": s,
              "old_verdict": d["old_verdict"], "new_verdict": d["new_verdict"],
              "branch": d["branch"], "u": d["u"], "miss_grams": d["miss_grams"],
              "v1_judge_sha16": SUPERSEDES_SHA16, "v2_judge_sha16": JUDGE_SHA16,
              "reason": "双层缺陷修复：层(a) 抽取器漏抽实体 + 层(b) 空事实默认 supported"}
             for d in diff for s in d["sides_changed"]]
            + [{"kind": "口径修订",
                "item": "① 触发条件：草稿的 facts==[] / u==0 收窄为 |G|==0",
                "effect": "u==0（有 gram 且全被覆盖）走 5b supported，不再弃权",
                "authority": "预登记 §B2"},
               {"kind": "口径修订", "item": "差异表：草稿 6 行 → 2 行（P13/P25）",
                "effect": "P28/P22/P24/P26 等 4 例真实 supported 的软表述保住",
                "authority": "预登记 §A5/§D4"},
               {"kind": "口径修订",
                "item": "supersedes 链：m5_ground.py 86b7c501ab9904aa → %s" % JUDGE_SHA16,
                "effect": "v1 不修改、不 monkeypatch，仅 import 其抽取函数", "authority": "§B4.3"},
               {"kind": "留痕",
                "item": "自引用哈希不可自含", "effect": "本件 sha16/bytes 不写入本件，回填 LANDED 台账",
                "authority": "§0.2/§E2"},
               {"kind": "坐标纠正（audit R1）",
                "item": ("prereg 坐标：源码/回归件原写已取代稿 8330fa716ef32a28；现统一改指盘上冻结版 "
                         "%s / %d B（链：handoff 8330fa71 / 34,373 B / 405 行 → 首读 135d020f / "
                         "35,716 B / 411 行 → 冻结 6c77b56f / 35,739 B / 411 行）"
                         % (PREREG_SHA16, PREREG_BYTES)),
                "effect": ("实现坐标与磁盘冻结版一致；/prereg/ 保留 observed_* 与 coordinate_history；"
                           "未据此改动任何阈值、词表或判定"),
                "authority": "审计 R1 + §0.1 冻结输入纪律"},
               {"kind": "纪律纠正（audit R2）",
                "item": "--regression 默认 write=False（只打印/比对，不落盘）；落盘须显式 --write",
                "effect": ("复跑不再重写 out/M5-JUDGE-v2-regression.json，"
                           "台账里的 regression sha16 不会因复跑而失效"),
                "authority": "审计 R2"},
               {"kind": "覆盖补强（audit R3）",
                "item": ("selftest 新增 ground() 端到端 5c_no_fact 三条；_assert_invariants 由恒真断言改为"
                         "真断言（|G|==0 <=> 5c_no_fact；分支 5 走完必得三值之一）"),
                "effect": "5c 出口与分支 5 决策表有自动测试覆盖；分支重排或 5c 挪位会失败",
                "authority": "审计 R3 / 预登记 §B2"},
               {"kind": "偏离纠正（audit R4）",
                "item": ("recheck 回退为 v1 语义（嵌套判定显式 _v1.ground），记 recheck_semantics="
                         "v1_unchanged；盘上旧件曾用 v2 嵌套，P13/P25 的 recheck_verdict 由 "
                         "unsupported → supported"),
                "effect": "符合预登记 §B3「recheck 一行不动」；只影响报告字段，不影响任何对 verdict",
                "authority": "审计 R4 + 预登记 §B3"},
               {"kind": "措辞纠正（audit R6）",
                "item": ("docstring 的 byte-for-byte v1 改为「语义等价，形式三处改写」；"
                         "summary 改为「§D 五项验收：5/5 满足（装置可用性层面；非 v2 已通过）」"),
                "effect": "summary 不再可被引成「v2 已通过」（§H7.4）", "authority": "审计 R6"}]
        ),
        "excluded": [{"pair_id": p["pair_id"], "reason": p.get("reason", "verbatim_copy"),
                      "note": "模型臂 CAND 冻结剔除的 14 对，不进任何两率分母（§F2）"}
                     for p in _load(_R2_PAIRS).get("excluded", [])],
        "abort": abort, "abort_reason": abort_reason,
        "stop_conditions_checked": {
            "diff_rows_gt_2": len(diff) > 2,
            "unexpected_rows": unexpected,
            "rewrite18_worse_than_v1": bool(rates["rewrite18_main"]["leak"]["num"] > 0
                                            or rates["rewrite18_main"]["false"]["num"] > 0),
            "v1_rerun_mismatch": v1_mismatch,
            "u_vs_prereg_c1_mismatch": ref_u_mismatch,
        },
        "verdict": {
            "v2_signable": v2_signable,
            "scope": "仅表示「判定器缺陷修复可用」；不代表 M5 可进全量，θ 未被校准（§H7.4）",
            "checks": checks,
            "summary": ("§D 五项验收：5/5 满足（装置可用性层面；非 v2 已通过）"
                        if v2_signable else "未通过：见 checks / abort_reason"),
        },
        "no_single_accuracy": True,
        "no_final_verdict": True,
        "gpu_used": False, "model_calls": 0, "git_operations": 0,
        "created_at": created_at,
        "producer": {"role": "implementer (not ADJ, not REVIEW)", "note": "§G: v2 作者不得充任 v2 的 ADJ/REVIEW"},
    }
    if write:
        p = _abs(_OUT)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(reg, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return reg


def _now():
    import datetime
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--answer")
    ap.add_argument("--mounted")
    ap.add_argument("--question", default=None)
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--regression", action="store_true")
    ap.add_argument("--write", action="store_true",
                    help="persist the regression artifact (default: print/compare only)")
    a = ap.parse_args()
    if a.selftest:
        print(json.dumps(selftest(), ensure_ascii=False, indent=2))
        return 0
    if a.regression:
        reg = run_regression(write=a.write)
        cmp_note = None
        p = _abs(_OUT)
        if not a.write and os.path.exists(p):
            with open(p, "rb") as f:
                disk_raw = f.read()
            disk = json.loads(disk_raw.decode("utf-8"))
            mine, theirs = dict(reg), dict(disk)
            mine.pop("created_at", None)
            theirs.pop("created_at", None)
            cmp_note = {"mode": "dry_run_no_write",
                        "disk_sha16_before": hashlib.sha256(disk_raw).hexdigest()[:16],
                        "disk_bytes_before": len(disk_raw),
                        "matches_disk_ignoring_created_at": mine == theirs}
        print(json.dumps({"written": bool(a.write), "out_path": _OUT,
                          "write_note": ("已显式 --write 落盘" if a.write else
                                         "默认不落盘（audit R2）：仅打印/比对；落盘须显式 --write"),
                          "compare": cmp_note,
                          "verdict": reg["verdict"], "counts": reg["counts"],
                          "recheck_semantics": reg["recheck_semantics"]["value"],
                          "rates": {"rewrite18": reg["rates"]["rewrite18_main"]["leak"],
                                    "false": reg["rates"]["rewrite18_main"]["false"]},
                          "diff": [(d["pair_id"], d["old_verdict"], d["new_verdict"])
                                   for d in reg["diff_vs_v1"]],
                          "abort": reg["abort"]}, ensure_ascii=False, indent=2))
        return 0
    if not a.answer:
        ap.error("--answer is required (or use --selftest / --regression)")
    r = ground(a.answer, [x for x in (a.mounted or "").split(",") if x], a.question, a.db)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())