# -*- coding: utf-8 -*-
"""M3 判据的纯函数实现 —— 驱动与单元注入共用同一份。

存在的理由（纪律 14）：判据有两份副本（声明 / 代码）。若单元测试再抄一份算式，
它测的就是抄件而不是驱动真正用的那份，两份一分叉就永远不会红。
所以驱动调这里的函数，单元测试也调这里的函数。
"""

NEEDLE = "广陵路 12 号 2 单元 602"


def no_rise_window(vals, k=3):
    """True when some k-length window is non-decreasing with total rise >= 1."""
    for i in range(len(vals) - k + 1):
        w = vals[i:i + k]
        if all(b >= a for a, b in zip(w, w[1:])) and (w[-1] - w[0]) >= 1:
            return [w, i]
    return None


def round_invalid_reasons(rec, moved, needle=NEEDLE):
    """I1..I6 for one round. Pure: reads only rec + moved, so a single wrong field
    can be injected without involving the engine (discipline 31: one factor)."""
    reasons = []
    if rec["answer"] == "":
        reasons.append("I1 empty answer (ask_return_bytes=%s, recorded not judged)"
                       % rec.get("ask_rc"))
    if needle not in rec["answer"]:
        reasons.append("I1 needle missing from the answer")
    if rec["pos_asked"] != rec["raw_pos_max_before_ask"] + 1:
        reasons.append("I2 pos=%d raw+1=%d" % (rec["pos_asked"],
                                               rec["raw_pos_max_before_ask"] + 1))
    if rec["block_cells_at_start"] != moved:
        reasons.append("I3 block cells at start = %d != %d"
                       % (rec["block_cells_at_start"], moved))
    if rec["holders_at_start"] or rec["ranges_at_start"]:
        reasons.append("I4 carried over: holders=%d ranges=%d"
                       % (rec["holders_at_start"], rec["ranges_at_start"]))
    if rec["pos_max_at_attach"] == -1 or rec["pos_max_after_detach"] == -1:
        reasons.append("I5 raw_pos_max == -1")
    if rec["attach_interval_len"] != moved:
        reasons.append("I6 interval %d != %d" % (rec["attach_interval_len"], moved))
    return reasons


def evaluate_checks(valid, moved, init_pos_max, needle=NEEDLE):
    """The judged criteria over the VALID rounds. M3-PREREG.md §11 forms."""
    pm_att = [x["pos_max_at_attach"] for x in valid]
    pm_det = [x["pos_max_after_detach"] for x in valid]
    cl_att = [x["cells_at_attach"] for x in valid]
    cl_det = [x["cells_after_detach"] for x in valid]
    cl_pre = [x["cells_before_attach"] for x in valid]
    ans = [x["answer"] for x in valid]
    rise = no_rise_window(cl_det, 3)
    return {
        "S1_pos_max_detach_equal": len(set(pm_det)) <= 1,
        "S2_pos_max_within_bound": (bool(pm_att) and max(pm_att) <= init_pos_max + moved),
        "S3_pos_at_attach_equals_attach_pos_hi_minus_1": (
            bool(pm_att) and all(x["pos_max_at_attach"] == x["attach_pos_hi"] - 1
                                 for x in valid)),
        "S3_cells_attach_minus_before_equals_moved": (
            bool(cl_att) and all(b - c == moved for b, c in zip(cl_att, cl_pre))),
        "C2_cells_attach_minus_before_equals_moved": (
            bool(cl_att) and all(b - c == moved for b, c in zip(cl_att, cl_pre))),
        "T1_needle_in_every_answer": all(needle in a for a in ans),
        "T2_answers_identical_to_round1": (bool(ans) and all(a == ans[0] for a in ans)),
        "C1_cells_detach_equal": len(set(cl_det)) <= 1,
        "C3_block_cells_moved": all(x["block_cells_at_start"] == moved
                                    and x["block_cells_at_end"] == moved for x in valid),
        "C4_no_3_round_non_decreasing_rise": not rise,
        "C5_last_equals_first": (bool(cl_det) and cl_det[-1] == cl_det[0]),
        "L1_holders_zero": all(x["holders_after_detach"] == 0 for x in valid),
        "L2_ranges_zero": all(x["ranges_after_detach"] == 0 for x in valid),
        "L3_any_leased_false": all(not x["any_leased_after_detach"] for x in valid),
        "L4_reset_clears_tokens": all(x["n_tokens_live_after_reset"] == 0 for x in valid),
        # evidence only, never judged
        "_rejected_S3_attach_minus_detach": (bool(pm_att) and
                                            all(b - c == moved for b, c in zip(pm_att, pm_det))),
        "_rejected_C2_attach_minus_detach": (bool(cl_att) and
                                            all(b - c == moved for b, c in zip(cl_att, cl_det))),
        "_rejected_I1_rc_nonzero_is_invalid": all(x.get("ask_rc") != 0 for x in valid),
    }


def c4_rise_window(valid):
    """The evidence FOR C4, deliberately NOT a key of evaluate_checks: a boolean table may hold
    criterion rows only. An annotation sitting among them makes a reader unable to tell which
    row is a criterion -- that is exactly what check_m3_prereg_consistency.py caught."""
    return no_rise_window([x["cells_after_detach"] for x in valid], 3)
