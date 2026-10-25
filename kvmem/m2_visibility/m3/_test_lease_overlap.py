# -*- coding: utf-8 -*-
"""M2 完整 L1：位置租约重叠校验的 11 例断言（零 GPU，stub 引擎）。

判据来源：`docs/_work/M2-FULL-PREREG-draft.md` §2.1（inspector 权威版，`4978c94474ba050c`）。
- 4 重叠（同 dst）：部分重叠 / 完全重叠 / 包含 / 同 dst 不同块 —— **必须抛 `LeaseError`**
- 4 边界：左右相邻（半开区间相接）/ 同块不同区间 / 远区间 —— **不抛**
- 2 跨 dst：同区间跨 dst / 重叠跨 dst —— **不抛**（同一块挂多 seq 是 M2 并发形态）
- 1 重放：同块同区间重复 attach —— **不抛且表不变**（幂等）

三条纪律：
1. **以 `raised`/状态判，不以异常逃逸判**：每例 `expect_raise` 记 `{raised, type, msg, calls_before/after, ranges_after, holders_after}`。
2. **拒绝不得先做破坏动作**：抛错例必须 `share` 调用数不增、`ranges`/`holders` 逐键不变。
3. 红证明用**变体法**：`--lease <临时目录副本>` 跑同一套构造，删掉校验的变体必须**不抛**。

跑法：
  python -X utf8 kvmem/m2_visibility/m3/_test_lease_overlap.py --out <产物.json>
  python -X utf8 .../_test_lease_overlap.py --lease <variant>/m3_lease.py --out <变体产物.json>

本文件不碰产品库/引擎/GPU；不登记自身 sha（§22.3）。
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HOME, PROJECT, HABIT = 1, 2, 3
LIVE = 0


class Stub:
    """零引擎桩：只记调用与 token 数（与 `_test_lease.py` 的 Stub 同语义）。"""

    def __init__(self):
        self.calls = []
        self.tokens = {HOME: 21, PROJECT: 18, HABIT: 12, LIVE: 0}

    def share(self, src, dst, lo, hi):
        self.calls.append(("share", int(src), int(dst), int(lo), int(hi)))

    def drop(self, dst, lo, hi):
        self.calls.append(("drop", int(dst), int(lo), int(hi)))

    def reset(self, seq):
        self.calls.append(("reset", int(seq)))
        if int(seq) in (HOME, PROJECT, HABIT):
            self.tokens[int(seq)] = 0

    def n_tokens(self, seq):
        return self.tokens.get(int(seq), 0)

    def share_calls(self):
        return sum(1 for c in self.calls if c[0] == "share")


def load_lease(path):
    spec = importlib.util.spec_from_file_location("m3_lease_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fresh(L):
    eng = Stub()
    leases = L.BlockLeases(eng)
    for seq, name in ((HOME, "home"), (PROJECT, "project"), (HABIT, "habit")):
        leases.register_block(seq, name)
    return eng, leases


def snapshot(leases):
    return {"ranges": {"%d|%d|%d" % k: v for k, v in sorted(leases.ranges.items())},
            "holders": {str(k): sorted(v) for k, v in sorted(leases.holders.items())}}


def run_case(L, case, kind, setup, probe, expect_raise, expect_intervals=None):
    """setup(eng, leases) 预置；probe 触发被测调用。返回一例的完整读数。"""
    eng, leases = fresh(L)
    setup(eng, leases)
    before = snapshot(leases)
    calls_before = list(eng.calls)
    raised, rtype, rmsg = False, None, ""
    try:
        probe(leases)
    except L.LeaseError as exc:                       # 只捕获被测错误类型，其余异常照抛
        raised, rtype, rmsg = True, "LeaseError", str(exc)
    after = snapshot(leases)
    calls_after = list(eng.calls)
    row = {
        "case": case, "kind": kind, "expect_raise": bool(expect_raise),
        "raised": raised, "raised_type": rtype, "raised_msg": rmsg,
        "share_calls_before": sum(1 for c in calls_before if c[0] == "share"),
        "share_calls_after": sum(1 for c in calls_after if c[0] == "share"),
        "ranges_before": before["ranges"], "ranges_after": after["ranges"],
        "holders_before": before["holders"], "holders_after": after["holders"],
        "tables_unchanged": before == after,
        # 真命中：拒绝原因确为区间相交，且消息里报出的两段区间与构造一致
        "true_hit": bool(raised and expect_intervals
                         and all(s in rmsg for s in expect_intervals)),
        "expect_intervals": list(expect_intervals or []),
    }
    row["ok"] = (raised == row["expect_raise"]) and (row["tables_unchanged"] or not expect_raise)
    return row


def cases(L):
    out = []

    # ---- 4 重叠（同 dst_seq） ----
    out.append(run_case(
        L, "O1_same_dst_diff_block_partial", "overlap",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.attach(PROJECT, LIVE, 4060, 4100),
        True, ["[4045,4095)", "[4060,4100)"]))
    out.append(run_case(
        L, "O2_partial_left", "overlap",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.attach(PROJECT, LIVE, 4000, 4050),
        True, ["[4045,4095)", "[4000,4050)"]))
    out.append(run_case(
        L, "O3_exact_same_range_diff_block", "overlap",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.attach(PROJECT, LIVE, 4045, 4095),
        True, ["[4045,4095)"]))
    out.append(run_case(
        L, "O4_contained", "overlap",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.attach(PROJECT, LIVE, 4060, 4080),
        True, ["[4045,4095)", "[4060,4080)"]))

    # ---- 4 边界（不抛） ----
    out.append(run_case(
        L, "B1_adjacent_left", "boundary",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.attach(PROJECT, LIVE, 3995, 4045), False))
    out.append(run_case(
        L, "B2_adjacent_right", "boundary",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.attach(PROJECT, LIVE, 4095, 4145), False))
    out.append(run_case(
        L, "B3_same_block_diff_range", "boundary",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.attach(HOME, LIVE, 4100, 4150), False))
    out.append(run_case(
        L, "B4_far_range", "boundary",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.attach(PROJECT, LIVE, 5000, 5010), False))

    # ---- 2 跨 dst（不抛） ----
    out.append(run_case(
        L, "X1_cross_dst_same_range", "cross_dst",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.attach(PROJECT, 1, 4045, 4095), False))
    out.append(run_case(
        L, "X2_cross_dst_overlap", "cross_dst",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.attach(PROJECT, 1, 4000, 4100), False))

    # ---- 1 重放（不抛且表不变） ----
    out.append(run_case(
        L, "R1_same_block_same_range_replay", "replay",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.attach(HOME, LIVE, 4045, 4095), False))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lease", default=os.path.join(HERE, "m3_lease.py"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    lease_path = os.path.abspath(args.lease)
    with open(lease_path, "rb") as f:
        lease_sha = hashlib.sha256(f.read()).hexdigest()[:16]
    L = load_lease(lease_path)

    t0 = time.time()
    rows = cases(L)

    n_overlap = sum(1 for r in rows if r["kind"] == "overlap")
    n_boundary = sum(1 for r in rows if r["kind"] == "boundary")
    n_cross = sum(1 for r in rows if r["kind"] == "cross_dst")
    n_replay = sum(1 for r in rows if r["kind"] == "replay")
    rejected = sum(1 for r in rows if r["raised"])
    true_hits = sum(1 for r in rows if r["true_hit"])
    fail = [r["case"] for r in rows if not r["ok"]]

    res = {
        "schema": "m3_l1_overlap_v1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "lease_module": {"path": lease_path, "sha16": lease_sha},
        "judge_source": {"path": "docs/_work/M2-FULL-PREREG-draft.md",
                         "section": "§2.1 L1", "sha16": "4978c94474ba050c"},
        "stub": "kvmem/m2_visibility/m3/_test_lease_overlap.py::Stub（零引擎、只记调用）",
        "three_level_denominator": {
            "constructed": len(rows),
            "breakdown": {"overlap": n_overlap, "boundary": n_boundary,
                          "cross_dst": n_cross, "replay": n_replay},
            "rejected": rejected,
            "true_hits": true_hits,
            "note": "真命中 = 拒绝且消息里报出的两段区间与构造一致",
        },
        "rows": rows,
        "fail_cases": fail,
        "exit": 0 if not fail else 2,
        "elapsed_s": round(time.time() - t0, 3),
    }
    out = args.out or os.path.join(tempfile.gettempdir(), "m3_lease_products",
                                   "M3-L1-overlap-%s.json" % time.strftime("%H%M%S"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    for r in rows:
        print("  %-32s expect_raise=%-5s raised=%-5s tables_unchanged=%-5s true_hit=%-5s %s"
              % (r["case"], r["expect_raise"], r["raised"], r["tables_unchanged"],
                 r["true_hit"], "ok" if r["ok"] else "RED"))
    d = res["three_level_denominator"]
    print("\n分母: 构造 %d (重叠%d/边界%d/跨seq%d/重放%d) / 拒绝 %d / 真命中 %d"
          % (d["constructed"], n_overlap, n_boundary, n_cross, n_replay,
             d["rejected"], d["true_hits"]))
    print("lease sha16=%s | fail=%s | exit=%d -> %s"
          % (lease_sha, fail, res["exit"], out))
    return res["exit"]


if __name__ == "__main__":
    sys.exit(main())