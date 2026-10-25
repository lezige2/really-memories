# -*- coding: utf-8 -*-
"""单因子失败输入（纪律 31）：每条判据喂一个「只错一处」的账，看它是否真的会红。

被测的是 m3_criteria 里那两个函数 —— 驱动跑 50 轮时调的就是它们，不是抄件。
不碰引擎、不碰 DLL、不跑 50 轮。

三种结局，产物里分开写：
  proven        单因子注入后红的判据（说明「可失败」）
  not_alone     只能与别的判据一起红（不可单因子证伪，例如 C5 被 C1 蕴含）
  no_flip       注入了也不红 => 该判据是 ②类（恒真），不能当判据用

  python -X utf8 kvmem/m2_visibility/m3/m3_unit_falsifiers.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m3_criteria as CR                                             # noqa: E402

OUT = os.path.join(HERE, "run_m3_unit_falsifiers.json")
PREREG = os.path.join(r"D:/llama-mem", "kvmem", "m2_visibility", "mine", "inspector",
                      "M3-PREREG.md")
MOVED = 91
INIT_POS_MAX = 4095
ANSWER = "我住在广陵路 12 号 2 单元 602。"


def healthy_round(r):
    return {"round": r, "answer": ANSWER, "ask_rc": 93, "answer_empty": False,
            "attach_pos_lo": 4005, "attach_pos_hi": 4096, "attach_interval_len": 91,
            "pos_max_before_attach": -1, "cells_before_attach": 0,
            "pos_max_at_attach": 4095, "cells_at_attach": 91,
            "pos_asked": 4096, "raw_pos_max_before_ask": 4095,
            "pos_max_after_detach": 4146, "cells_after_detach": 51,
            "block_cells_at_start": 91, "block_cells_at_end": 91,
            "holders_at_start": 0, "ranges_at_start": 0,
            "holders_after_detach": 0, "ranges_after_detach": 0,
            "any_leased_after_detach": False, "n_tokens_live_after_reset": 0}


HEALTHY = [healthy_round(1), healthy_round(2), healthy_round(3)]

JUDGED = [k for k in CR.evaluate_checks(HEALTHY, MOVED, INIT_POS_MAX)
          if not k.startswith("_")]

# one factor per case: (id, judged criterion aimed at, mutation, expected flipped set,
#                      expected invalid-reason prefix or None)
CASES = [
    ("U-S1", "S1_pos_max_detach_equal",
     lambda rs: rs[1].__setitem__("pos_max_after_detach", 4147),
     ["S1_pos_max_detach_equal"], None),
    ("U-S2", "S2_pos_max_within_bound",
     lambda rs: rs[0].__setitem__("pos_max_at_attach", 10 ** 6),
     ["S2_pos_max_within_bound", "S3_pos_at_attach_equals_attach_pos_hi_minus_1"], None),
    ("U-S3pos", "S3_pos_at_attach_equals_attach_pos_hi_minus_1",
     lambda rs: [r.__setitem__("attach_pos_hi", r["attach_pos_hi"] + 1) for r in rs],
     ["S3_pos_at_attach_equals_attach_pos_hi_minus_1"], None),
    ("U-S3cells", "S3_cells_attach_minus_before_equals_moved",
     lambda rs: [r.__setitem__("cells_before_attach", 91) for r in rs],
     ["S3_cells_attach_minus_before_equals_moved",
      "C2_cells_attach_minus_before_equals_moved"], None),
    ("U-T1", "T1_needle_in_every_answer",
     lambda rs: rs[1].__setitem__("answer", "我住在广陵路。"),
     ["T1_needle_in_every_answer", "T2_answers_identical_to_round1"], None),
    ("U-T2", "T2_answers_identical_to_round1",
     lambda rs: rs[1].__setitem__("answer", ANSWER + " "),
     ["T2_answers_identical_to_round1"], None),
    ("U-C1", "C1_cells_detach_equal",
     lambda rs: rs[1].__setitem__("cells_after_detach", 52),
     ["C1_cells_detach_equal"], None),
    ("U-C3", "C3_block_cells_moved",
     lambda rs: rs[1].__setitem__("block_cells_at_end", 90),
     ["C3_block_cells_moved"], None),
    ("U-C4", "C4_no_3_round_non_decreasing_rise",
     lambda rs: rs[2].__setitem__("cells_after_detach", 142),
     ["C1_cells_detach_equal", "C4_no_3_round_non_decreasing_rise",
      "C5_last_equals_first"], None),
    ("U-C5", "C5_last_equals_first",
     lambda rs: rs[0].__setitem__("cells_after_detach", 52),
     ["C1_cells_detach_equal", "C5_last_equals_first"], None),
    ("U-L1", "L1_holders_zero",
     lambda rs: rs[1].__setitem__("holders_after_detach", 1), ["L1_holders_zero"], None),
    ("U-L2", "L2_ranges_zero",
     lambda rs: rs[1].__setitem__("ranges_after_detach", 1), ["L2_ranges_zero"], None),
    ("U-L3", "L3_any_leased_false",
     lambda rs: rs[1].__setitem__("any_leased_after_detach", True),
     ["L3_any_leased_false"], None),
    ("U-L4", "L4_reset_clears_tokens",
     lambda rs: rs[1].__setitem__("n_tokens_live_after_reset", 1),
     ["L4_reset_clears_tokens"], None),
    ("U-I1-empty", "I1", lambda rs: rs[1].__setitem__("answer", ""),
     ["T1_needle_in_every_answer", "T2_answers_identical_to_round1"], "I1 empty"),
    ("U-I1-needle", "I1", lambda rs: rs[1].__setitem__("answer", "我住在广陵路。"),
     ["T1_needle_in_every_answer", "T2_answers_identical_to_round1"], "I1 needle"),
    ("U-I2", "I2", lambda rs: rs[1].__setitem__("pos_asked", 4097), [], "I2"),
    ("U-I4", "I4", lambda rs: rs[1].__setitem__("holders_at_start", 1), [], "I4"),
    ("U-I5", "I5", lambda rs: rs[1].__setitem__("pos_max_at_attach", -1),
     ["S3_pos_at_attach_equals_attach_pos_hi_minus_1"], "I5"),
    ("U-I6", "I6", lambda rs: rs[1].__setitem__("attach_interval_len", 90), [], "I6"),
]


def main():
    base = CR.evaluate_checks(HEALTHY, MOVED, INIT_POS_MAX)
    res = {"schema": "m3_unit_falsifiers_v1", "pid": os.getpid(),
           "prereg": {"path": "kvmem/m2_visibility/mine/inspector/M3-PREREG.md",
                      "sha16": __import__("hashlib").sha256(
                          open(PREREG, "rb").read()).hexdigest()[:16],
                      "lines": len(open(PREREG, encoding="utf-8").read().splitlines())},
           "aim": "each judged criterion must have ONE single-factor input that makes it red; "
                  "a criterion that cannot go red carries zero information (discipline 34)",
           "baseline": {k: base[k] for k in JUDGED},
           "baseline_all_true": all(base[k] for k in JUDGED),
           "baseline_no_reason": CR.round_invalid_reasons(HEALTHY[0], MOVED) == [],
           "cases": []}
    proven, independent, no_flip = {}, {}, {}
    for cid, aimed, mutate, expect_flip, expect_reason in CASES:
        rounds = copy.deepcopy(HEALTHY)
        mutate(rounds)
        chk = CR.evaluate_checks(rounds, MOVED, INIT_POS_MAX)
        flipped = sorted(k for k in JUDGED if base[k] and not chk[k])
        reasons = CR.round_invalid_reasons(rounds[1], MOVED)
        rec = {"case": cid, "aimed_at": aimed, "flipped": flipped,
               "expected_flipped": sorted(expect_flip),
               "invalid_reasons": reasons}
        ok = flipped == sorted(expect_flip)
        if expect_reason:
            ok = ok and any(r.startswith(expect_reason) for r in reasons)
        rec["pass"] = ok
        res["cases"].append(rec)
        if ok:
            for k in flipped:
                proven.setdefault(k, []).append(cid)
                independent[k] = independent.get(k, False) or len(flipped) == 1
        else:
            no_flip.setdefault(aimed, []).append("case %s: flipped=%s expected=%s"
                                                 % (cid, flipped, sorted(expect_flip)))
    for k in ("L1_holders_zero", "L2_ranges_zero", "L3_any_leased_false",
              "C4_no_3_round_non_decreasing_rise", "C1_cells_detach_equal"):
        proven.setdefault(k, []).append("live red control A (run_m3_redA.json)")
        independent.setdefault(k, True)
    res["falsified_by"] = proven
    res["falsified_alone"] = {k: v for k, v in independent.items()}
    res["not_alone"] = sorted(k for k, v in independent.items() if not v)
    res["no_flip"] = no_flip
    res["never_falsified"] = sorted(k for k in JUDGED if k not in proven)
    res["note_C5"] = ("C5 (last == first) is implied by C1 (all equal): any single-factor input "
                      "that flips C5 also flips C1, so C5 cannot be falsified alone -- it is a "
                      "restatement, not an independent criterion.")
    res["note_S3C2"] = ("S3_cells and C2 are the same expression under two names; they always "
                        "flip together, so the count of independently verified criteria must "
                        "count them once.")
    res["verdict"] = ("UNIT-FALSIFIERS PASS -- every judged criterion except the restatements "
                      "has a single-factor red" if not no_flip else
                      "UNIT-FALSIFIERS RED -- some criterion did not flip")
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("baseline all true:", res["baseline_all_true"], "| baseline no reason:",
          res["baseline_no_reason"])
    for c in res["cases"]:
        print("%-12s %-50s flipped=%s %s" % (c["case"], c["aimed_at"], c["flipped"],
                                             "OK" if c["pass"] else "MISMATCH"))
    print("never falsified:", res["never_falsified"])
    print("not falsifiable alone:", res["not_alone"])
    print(res["verdict"])
    return 0 if not no_flip else 1


if __name__ == "__main__":
    sys.exit(main())
