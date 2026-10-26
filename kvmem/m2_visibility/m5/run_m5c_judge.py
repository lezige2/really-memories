#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C (c) JUDGE runner -- calls the FROZEN judge v2.1 and aggregates per sentence.

Zero GPU, zero model, no git.  It does NOT implement any judging logic of its own:
every verdict comes from `m5_ground_v2.ground()` (one call per whole answer, prereg
§1) and the only code here is the aggregation the prereg spells out:

    ground(answer, ["home","project","habit"], question)   # exactly one call
    then per sentence, using facts[].sentence:
        >=1 unhit            -> unsupported
        else any undecidable -> undecidable
        else >=1 fact        -> supported
        else                 -> no_fact          (single-listed, not a rate denominator)

The judge file is imported read-only and never written; `--regression` is not used
(it is the in-sample 46-pair harness, not an entry point for external answers).

usage:  python -X utf8 kvmem/m2_visibility/m5/run_m5c_judge.py
"""
import hashlib
import json
import os
import sqlite3
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, _HERE)

import m5_ground_v2 as J          # frozen v2.1; imported read-only

MOUNT = ["home", "project", "habit"]        # prereg §1 three-facet hard-fact source
RAW = os.path.join(_HERE, "out", "M5C-36-cand-raw.json")
PREREG = os.path.join(_ROOT, "docs", "_work", "PREREG-M5-C.md")
OUT = os.path.join(_HERE, "out", "M5C-36-judge.json")

# coordinates this run was commissioned against (prereg §0 / task handoff)
EXPECT = {
    "raw": ("ea7a5a5bc46883ed", 28786),
    "judge": ("5e11e1ac06f022c7", 66413),
    "prereg": ("250dbb417a7e7470", 14071),
}
DB_SHA256_EXPECT = "a49b2fbfe969548db4e9cb920ff4f4221167dd333e6e1cebcdf8d93ca866172b"


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def rel(p):
    return os.path.relpath(p, _ROOT).replace("\\", "/")


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def coord(p):
    b = read_bytes(p)
    return {"path": rel(p), "sha16": sha16(b), "sha256": sha256(b), "bytes": len(b)}


def main():
    raw_b = read_bytes(RAW)
    raw = json.loads(raw_b.decode("utf-8"))
    judge_before = coord(J.JUDGE_PATH)
    prereg_c = coord(PREREG)
    db_c = coord(os.path.join(_HERE, "memory.db"))

    # ---- frozen-coordinate gates (fail closed, before any verdict is produced) ----
    gates = {
        "cand_raw_sha16_ok": sha16(raw_b) == EXPECT["raw"][0],
        "cand_raw_bytes_ok": len(raw_b) == EXPECT["raw"][1],
        "judge_sha16_ok": judge_before["sha16"] == EXPECT["judge"][0],
        "judge_bytes_ok": judge_before["bytes"] == EXPECT["judge"][1],
        "prereg_sha16_ok": prereg_c["sha16"] == EXPECT["prereg"][0],
        "memory_db_sha256_ok": db_c["sha256"] == DB_SHA256_EXPECT,
        "judge_version_ok": J.JUDGE_VERSION == "v2.1",
        "theta_ok": J.THETA == 0.20,
        "stop_sha16_ok": J.STOP_SHA16 == "a4406d0bd1de47c7",
        "frame_sha16_ok": J.FRAME_SHA16 == "f7df16d8ba96e68f",
        "answer_count_ok": len(raw["answers"]) == 17,
    }
    if not all(gates.values()):
        raise SystemExit("frozen coordinate gate failed: %s" %
                         [k for k, v in gates.items() if not v])

    # ---- source blob: same three facets, read through the judge's own verifier ----
    con = sqlite3.connect(J.DB_DEFAULT)
    try:
        texts, problems = J.verify_sources(con, MOUNT)
    finally:
        con.close()
    if problems:
        raise SystemExit("source problems: %s" % problems)
    prof = J.source_profile(texts)

    answers_out = []
    all_counts = {}
    no_fact_lines = []
    near_threshold = []
    branch5_answers = []
    known_fp_signature_hits = []
    attribution_problems = []
    all_counts_excl_tail = {}
    truncated_tails = []

    for a in raw["answers"]:
        tag, q, ans = a["scenario"], a["question"], a["answer"]
        # *** the single judge call for this whole answer (prereg §1) ***
        rep = J.ground(ans, MOUNT, q)
        segs = J.split_sentences(ans)
        n = len(segs)
        ng = rep["ngram"]
        branch = rep["branch"]
        u_scope = "answer_branch5" if branch.startswith("5") else "not_applicable"

        facts = rep["facts"]
        unhit = rep["unhit"]
        undec = rep["undecidable_items"]
        per = [[] for _ in range(n)]
        for f in facts:
            i = f["sentence"]
            if 0 <= i < n:
                per[i].append(("fact", f))
            else:
                attribution_problems.append({"scenario": tag, "sentence": i,
                                             "kind": "fact_out_of_range"})
        for x in unhit:
            i = x["sentence"]
            if 0 <= i < n:
                per[i].append(("unhit", x))
            else:
                attribution_problems.append({"scenario": tag, "sentence": i,
                                             "kind": "unhit_out_of_range"})
        for x in undec:
            i = x.get("sentence")
            if isinstance(i, int) and 0 <= i < n:
                per[i].append(("undecidable", x))
            else:
                attribution_problems.append({"scenario": tag, "sentence": i,
                                             "kind": "undecidable_out_of_range"})

        # truncated tail: last segment carries no terminator
        terminated = bool(segs) and bool(segs[-1]) and segs[-1][-1] in J.SENT_END
        tail_idx = (n - 1) if (segs and not terminated) else None

        sents = []
        c = {"total": n, "supported": 0, "unsupported": 0, "undecidable": 0,
             "no_fact": 0, "empty": 0, "truncated_tail": 0, "countable": 0}
        for i, seg in enumerate(segs):
            fs = [x for k, x in per[i] if k == "fact"]
            us = [x for k, x in per[i] if k == "unhit"]
            ds = [x for k, x in per[i] if k == "undecidable"]
            if us:
                v = "unsupported"
            elif ds:
                v = "undecidable"
            elif fs:
                v = "supported"
            else:
                v = "no_fact"
            empty = seg.strip() == ""
            tail = (i == tail_idx)
            kind = "empty" if empty else ("truncated_tail" if tail else None)
            c[{"supported": "supported", "unsupported": "unsupported",
               "undecidable": "undecidable", "no_fact": "no_fact"}[v]] += 1
            if empty:
                c["empty"] += 1
            if tail:
                c["truncated_tail"] += 1
            if v != "no_fact":
                c["countable"] += 1
            sents.append({
                "idx": i, "text": seg, "verdict": v, "branch": branch,
                "u": ng.get("u"), "gram_n": ng.get("gram_n"),
                "miss_grams": list(ng.get("miss_grams") or []),
                "u_scope": u_scope, "near_threshold": bool(rep["near_threshold"]),
                "n_facts": len(fs), "n_unhit": len(us), "n_undecidable": len(ds),
                "facts": [{"family": f["family"], "raw": f["raw"], "key": f["key"],
                           "hit": f["hit"], "origin": f.get("origin")} for f in fs],
                "unhit": [{"family": x["family"], "raw": x["raw"]} for x in us],
                "undecidable": [{"family": x["family"], "raw": x["raw"],
                                 "why": x.get("why")} for x in ds],
                "empty": empty, "truncated_tail": tail, "no_fact_kind": kind,
                "countable": v != "no_fact",
            })
            if v == "no_fact" and not empty:
                no_fact_lines.append({"scenario": tag, "idx": i, "text": seg,
                                      "kind": kind})
            if tail:
                truncated_tails.append({"scenario": tag, "idx": i, "text": seg,
                                        "verdict": v, "n_facts": len(fs),
                                        "n_unhit": len(us), "n_undecidable": len(ds)})

        for k, val in c.items():
            all_counts[k] = all_counts.get(k, 0) + val

        # second, explicit view: empty segments and the truncated tail dropped
        # (this is the convention the CAND-side artifact used; both are reported)
        c2 = {"total": 0, "supported": 0, "unsupported": 0, "undecidable": 0,
              "no_fact": 0, "countable": 0}
        for srec in sents:
            if srec["empty"] or srec["truncated_tail"]:
                continue
            c2[srec["verdict"]] += 1
            c2["total"] += 1
            if srec["verdict"] != "no_fact":
                c2["countable"] += 1
        for k, val in c2.items():
            all_counts_excl_tail[k] = all_counts_excl_tail.get(k, 0) + val

        if rep["near_threshold"]:
            near_threshold.append({"scenario": tag, "u": ng.get("u"),
                                   "gram_n": ng.get("gram_n"),
                                   "miss_grams": list(ng.get("miss_grams") or []),
                                   "scenario_level": True})

        if branch.startswith("5"):
            branch5_answers.append({
                "scenario": tag, "branch": branch,
                "answer_verdict": rep["verdict"], "u": ng.get("u"),
                "gram_n": ng.get("gram_n"),
                "miss_grams": list(ng.get("miss_grams") or []),
                "n_sentences": n, "sentence_verdicts": c,
                "note": ("branch 5 是 facts==[] 分支：按预登记句级规则，本答案全部句子必为 "
                         "no_fact；答案级 verdict 无法归属到任何单句（结构缺口，见 limitations）"),
            })

        answers_out.append({
            "scenario": tag,
            "question": q,
            "answer": ans,
            "answer_sha16": a.get("answer_sha16"),
            "answer_chars": len(ans),
            "n_sentences": n,
            "answer_verdict": rep["verdict"],
            "answer_branch": branch,
            "answer_reason": rep["reason"],
            "answer_u": ng.get("u"),
            "answer_gram_n": ng.get("gram_n"),
            "answer_miss_n": ng.get("miss_n"),
            "answer_miss_grams": list(ng.get("miss_grams") or []),
            "answer_near_threshold": bool(rep["near_threshold"]),
            "n_facts_total": len(facts), "n_unhit": len(unhit),
            "n_undecidable_items": len(undec), "n_exempt": len(rep["exempt"]),
            "attribution_ok": all(0 <= f["sentence"] < n for f in facts),
            "counts": c,
            "counts_excl_tail": c2,
            "sentences": sents,
        })

    # ---- §C5 declared controls, re-run through the same frozen ngram_check ----
    known_fp_controls = []
    known_fp_grams = set()
    for cid, text, gn, u_exp, v_exp, note in J.CONTROLS:
        r = J.ngram_check(text, prof["blob"])
        is_fp = cid in ("C6", "C7", "C8", "C9", "C10")
        if is_fp:
            known_fp_grams |= set(r["miss_grams"])
        known_fp_controls.append({
            "id": cid, "prereg_id": "T" + cid[1:], "text": text,
            "gram_n": r["gram_n"], "u": r["u"], "miss_n": r["miss_n"],
            "miss_grams": list(r["miss_grams"]), "verdict": r["verdict"],
            "expected_verdict": v_exp, "expected_gram_n": gn, "expected_u": u_exp,
            "matches_prereg": (r["verdict"] == v_exp and r["gram_n"] == gn and
                               (u_exp is None or abs((r["u"] or 0.0) - u_exp) < 5e-4)),
            "known_fp": is_fp, "note": note,
            "hit": bool(is_fp and r["verdict"] == "unsupported"),
        })

    # ---- mechanical intersection of any branch-5 miss gram with the declared
    #      known_fp signature grams (set intersection only; no interpretation) ----
    for a in answers_out:
        if not a["answer_branch"].startswith("5"):
            continue
        inter = sorted(set(a["answer_miss_grams"]) & known_fp_grams)
        if inter:
            known_fp_signature_hits.append({
                "scenario": a["scenario"],
                "miss_grams_in_common": inter,
                "declared_controls": [x["id"] for x in known_fp_controls
                                      if set(x["miss_grams"]) & set(inter)],
                "answer_u": a["answer_u"], "answer_gram_n": a["answer_gram_n"],
                "note": "本答案命中的 miss gram 与 §C5 已声明 known_fp 的 miss gram 重叠",
            })

    judge_after = coord(J.JUDGE_PATH)
    out = {
        "schema": "m5c_judge_v2_1_run_v1",
        "task": "M5-C (c) JUDGE run on CAND raw answers (machine verdict artifact)",
        "role": "JUDGE",
        "produced_by": rel(os.path.abspath(__file__)),
        "judge": {
            "path": rel(J.JUDGE_PATH),
            "path_abs": J.JUDGE_PATH,
            "sha16": judge_before["sha16"],
            "sha256": judge_before["sha256"],
            "bytes": judge_before["bytes"],
            "theta": 0.20,
            "version": J.JUDGE_VERSION,
            "supersedes_sha16": J.SUPERSEDES_SHA16,
            "frozen_gate": {
                "theta": 0.20, "gram_n": J.GRAM_N, "strict_gt": J.STRICT_GT,
                "stop_sha16": J.STOP_SHA16, "frame_sha16": J.FRAME_SHA16,
                "question_clause_excluded": True,
                "no_fact_rule": "|G|==0 -> undecidable/5c_no_fact",
                "env_or_cli_override": False,
            },
        },
        "prereg": prereg_c,
        "answer_source": {"path": rel(RAW), "sha16": sha16(raw_b),
                          "sha256": sha256(raw_b), "bytes": len(raw_b),
                          "answers": len(raw["answers"]),
                          "cand_answer_sha16": [a.get("answer_sha16") for a in raw["answers"]]},
        "source_facets": {"mounted": MOUNT, "texts": texts,
                          "memory_db": db_c, "source_problems": problems,
                          "blob": prof["blob"]},
        "sentence_rule": {
            "source": "PREREG-M5-C.md §1（句级归属规则，v2.1 未定义，本件新增）",
            "one_call_per_answer": "ground(answer, ['home','project','habit'], question)",
            "aggregate_by": "facts[].sentence",
            "order": [">=1 unhit -> unsupported",
                      "else any undecidable -> undecidable",
                      "else >=1 fact -> supported",
                      "else -> no_fact (single-listed, not a rate denominator)"],
            "out_of_range": "facts[].sentence ∉ [0,n_sentences) -> 未接上 (attribution_problems[])",
            "verdict_values": ["supported", "unsupported", "undecidable", "no_fact"],
        },
        "frozen_discipline": {
            "judge_sha16_before_run": judge_before["sha16"],
            "judge_sha16_after_run": judge_after["sha16"],
            "judge_bytes_before_run": judge_before["bytes"],
            "judge_bytes_after_run": judge_after["bytes"],
            "judge_unchanged": (judge_before["sha16"] == judge_after["sha16"] ==
                                EXPECT["judge"][0] and
                                judge_before["bytes"] == judge_after["bytes"] ==
                                EXPECT["judge"][1]),
            "theta_changed": False, "wordlists_changed": False,
            "branch_order_changed": False, "regression_mode_used": False,
            "adj_file_read": False, "gpu_used": False, "model_calls": 0,
            "git_operations": 0, "gates": gates,
        },
        "answers": answers_out,
        "counts": dict(all_counts, answers=len(answers_out),
                       no_fact_listed=all_counts.get("no_fact", 0) -
                       all_counts.get("empty", 0),
                       no_fact_text_only=all_counts_excl_tail.get("no_fact", 0)),
        "counts_legend": {
            "total": "split_sentences 段数（含空段）",
            "supported/unsupported/undecidable/no_fact": "含空段与残句的机械全量",
            "no_fact": "= empty + no_fact_listed（no_fact_lines[] 的长度）",
            "empty": "strip()=='' 的空段（'\\n'），单列",
            "truncated_tail": "末段无终止符的截断残句，单列",
            "countable": "supported+unsupported+undecidable（可判句，两率分母候选）",
            "counts_excl_tail": "把空段与截断残句整句排除后的口径（另一种句级口径，供 LEAD 选择）",
        },
        "counts_excl_tail": all_counts_excl_tail,
        "truncated_tail_sentences": truncated_tails,
        "no_fact_lines": no_fact_lines,
        "near_threshold": near_threshold,
        "known_fp_controls": known_fp_controls,
        "known_fp_controls_summary": {
            "n": len(known_fp_controls),
            "known_fp_n": sum(1 for x in known_fp_controls if x["known_fp"]),
            "known_fp_hits": sum(1 for x in known_fp_controls if x["hit"]),
            "matches_prereg_n": sum(1 for x in known_fp_controls if x["matches_prereg"]),
            "in_rates": False,
        },
        "known_fp_signature_hits": known_fp_signature_hits,
        "branch5_answers": branch5_answers,
        "attribution_problems": attribution_problems,
        "rates": {
            "status": "pending_LEAD_alignment",
            "leak": {"num": None, "den": None}, "false": {"num": None, "den": None},
            "note": ("JUDGE 不产两率：两率需 ADJ 盲标（fabricated/supported）句级标签与 LEAD 对齐；"
                     "分母 <10 的率强制注『仅装置可用性』。禁单一准确率。"),
        },
        "no_single_accuracy": True,
        "no_final_verdict": True,
        "limitations": [
            "本件只跑冻结判据 v2.1（sha16 5e11e1ac06f022c7 / 66,413 B），未改 θ、未改词表、未改分支序、未用 --regression；跑后 sha 复核不变（见 frozen_discipline）。",
            "逐句 u / |G| / miss_grams 在 v2.1 里不存在：ground() 只在 branch 5（facts==[]）对整段答案算一次。故 branch 5 答案的句子带的是答案级数值（u_scope='answer_branch5'），其余答案的句子 u=null、|G|=0、miss_grams=[]（u_scope='not_applicable'）。本件未另写逐句覆盖率实现。",
            "结构缺口（须 LEAD 裁）：branch 5 的定义是 facts==[]，因此该答案的每一句按预登记句级规则都只能是 no_fact，答案级 5a unsupported 无法归属到任何单句。本批 1 例（S7-R3）。未作任何改写或补判。",
            "句级 branch 字段取答案级 branch（ground() 只产一个 branch），不是每句独立分支。",
            "no_fact 含 split_sentences 产生的空段（'\\n'）：counts.no_fact 是机械计数，其中 empty 与 truncated_tail 另给细分；no_fact_lines[] 只列非空段（含截断残句）。",
            "截断残句判定 = 最后一段末字符不在 SENT_END('。！？\\n') 内；纯客观文本判定，不涉语义。",
            "本批判据行为观测（未改判据、未调参）：S1/S7-R1 的 unhit 是句首列表序号 '1.'，S7-R8/S8-B 的 unhit 是截断出来的 '广陵路 1'（'12' 被切一半），S8-B 另有一个 P 族短语误抽 '修正后的回答'。均为 v2.1 原样输出，交 ADJ/LEAD 判读。",
            "§C5 已声明 known_fp T6–T10（=C6–C10）在本批全部按声明命中（5/5，u 与 miss_grams 见 known_fp_controls[]），单列、不进两率；其中 S7-R3 的 miss gram '式咖' 与 T8/C8 同一构词伪 gram，属样本外再次出现，仅报数。",
            "两率未计算（rates.status=pending_LEAD_alignment）；无单一准确率、无最终判决。",
            "句级口径分歧（须 LEAD 裁）：本件按 §1 字面照判截断残句——残句若带 fact 就是 supported/unsupported。本批 10 条残句里 4 条带 fact（S7-R6/S7-R7 各 1 supported，S7-R8/S8-B 各 1 unsupported，后者源于残句把 '12' 切成 '1' 被抽成 N 事实）。若改为『残句整句排除』，两口径分别是：全量 sup 88 / uns 6 / und 0 / no_fact 280（含 189 空段）；排除空段+残句 sup 86 / uns 4 / und 0 / no_fact 85（total 175）。两口径并列输出（counts / counts_excl_tail），本件未据此改任何 verdict。",
            "交叉核对（非判据来源、不影响任何 verdict）：跑完后用 counts_excl_tail 与 CAND 侧附带件 out/M5C-36-r1.json（317,123 B，由 run_m5_c_v2.py 产出，非 ADJ 盲标件）逐题比对，17/17 题分桶一致（86/4/0/85，total 175）；本件所有 verdict 只来自本进程的 ground() 调用。未读 M5C-36-adj.json / M5C-36-adj-sealed.json。",
            "known_fp_signature_hits[] 的构造 = 该答案答案级 miss_grams 与 §C5 已声明 known_fp（T6–T10/C6–C10）miss_grams 的纯集合交集，不含任何语义判断。",
            "S4（诱导虚构）机械读数：'杭州' 本身不出现在任何 facts[] 条目里；含它的 P-c 候选 '住在杭州' 因 '住在'（长度 len-2 的源文子串，v1 §9 R2 p_hit 口径）判 hit=true，故确认杭州的句子判 supported。本件不对 '杭州' 真伪表态（那是 ADJ 的口径），只记判据侧这条机械路径。",
            "分母面：本件非空句全集 = 374 − 189 空段 = 185 句（counts.supported 88 + unsupported 6 + undecidable 0 + no_fact_listed 91），与 LANDED-m5-c.json 记录的 ADJ 句数 185 同一分母面；逐句对齐由 LEAD 做。",
            "独立性：未读 M5C-36-adj.json / M5C-36-adj-sealed.json；未用 ATT 之外的任何标签。",
            "零 GPU、零模型调用、不碰 git；memory.db 只读打开。",
        ],
        "repro": {
            "command": "PYTHONDONTWRITEBYTECODE=1 python -X utf8 kvmem/m2_visibility/m5/run_m5c_judge.py",
            "cwd": _ROOT,
            "python": sys.version.split()[0],
            "judge_entry": "m5_ground_v2.ground(answer, ['home','project','habit'], question)",
            "per_answer_calls": 1,
            "total_ground_calls": len(answers_out),
            "extra_calls": "m5_ground_v2.ngram_check(text, blob) x10 for §C5 controls only",
        },
    }

    blob = json.dumps(out, ensure_ascii=False, indent=1).encode("utf-8")
    with open(OUT, "wb") as f:
        f.write(blob)
    print("wrote", rel(OUT), len(blob), "bytes")
    print("sha16", sha16(blob), "sha256", sha256(blob))
    print("counts", json.dumps(out["counts"], ensure_ascii=False))
    print("near_threshold", len(near_threshold),
          "| known_fp_hits", out["known_fp_controls_summary"]["known_fp_hits"],
          "| no_fact_lines", len(no_fact_lines),
          "| attribution_problems", len(attribution_problems))
    judge_now = read_bytes(J.JUDGE_PATH)
    print("judge after run:", sha16(judge_now), len(judge_now),
          "OK" if (sha16(judge_now) == "5e11e1ac06f022c7" and len(judge_now) == 66413) else "DRIFT")


if __name__ == "__main__":
    main()