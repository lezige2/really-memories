# -*- coding: utf-8 -*-
"""M2 完整 L2：`detach` 未命中 `ranges` 时**静默**丢引用的构造床（零 GPU，stub 引擎）。

判据来源：`docs/_work/M2-FULL-PREREG-draft.md` §2.2（`4978c94474ba050c`）。
现状（红）：`detach(dst,lo,hi)` 在 `ranges` 里查不到键时 `block_seq=None`，但**仍然 `eng.drop`**，
且不落任何事件/计数 ⇒ 静默丢引用（记账漂移查不出）。
L2 要求：未命中必须落 `unbooked_detach` 事件 + 计数（不静默）；strict 模式（默认 strict）抛
`LeaseError` 且**不 drop**；命中则照常 drop。

本文件只**读数**，不改产品代码；`--out` 落产物，`--lease` 可指向临时目录的变体模块（后续红证明用）。
四条构造（= 三级分母的 detach 调用数 4）：
  H1 命中            ：attach 后 detach ⇒ hit=True、drop 1 次、无 unbooked、不抛
  U1 从未登记        ：detach 一个从未 attach 的区间 ⇒ 应 unbooked=1、抛、drop 0 次（现盘：drop 1、不抛 ⇒ 红）
  U2 表漂移          ：attach 后手工 pop 掉 ranges 键再 detach ⇒ 同上（现盘 ⇒ 红）
  U3 二次 detach     ：attach → detach（命中）→ 再 detach（未命中）⇒ 第二次 unbooked=1、抛、drop 不增

本文件不登记自身 sha（§22.3）。
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

    def drop_calls(self):
        return sum(1 for c in self.calls if c[0] == "drop")


def load_lease(path):
    spec = importlib.util.spec_from_file_location("m3_lease_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


STRICT_KW = {"accepted": None}       # BlockLeases 是否接受 strict= 关键字（L2 前后对比用）


def fresh(L, strict=True):
    eng = Stub()
    try:
        leases = L.BlockLeases(eng, strict=strict)
        STRICT_KW["accepted"] = True
    except TypeError:                     # L2 之前的模块没有 strict 形参：如实记下并按旧签名构造
        leases = L.BlockLeases(eng)
        STRICT_KW["accepted"] = False
    for seq, name in ((HOME, "home"), (PROJECT, "project"), (HABIT, "habit")):
        leases.register_block(seq, name)
    return eng, leases


def unbooked_events(leases):
    return [e for e in leases.events if e.get("kind") == "unbooked_detach"]


def unbooked_count(leases):
    """L2 落地后应存在计数属性（`unbooked_count`，初值 0）；未落地时返回 None（不冒充 0）。"""
    for attr in ("unbooked_count", "unbooked", "unbooked_detach", "counts"):
        v = getattr(leases, attr, None)
        if isinstance(v, int):
            return v
        if isinstance(v, dict) and "unbooked_detach" in v:
            return v["unbooked_detach"]
    return None


def run_case(L, case, kind, setup, probe, expect, pre=None, strict=True):
    """`pre` = 目标调用之前的合法调用（例如 U3 的第一次 detach）；`probe` = 被测的那一次。

    `drop_calls_delta` 是该例的 drop **总量**；`drop_delta_on_unbooked` 只统计**被拒绝的那次调用**
    上的 `eng.drop` 增量 —— 后者才能抓住「先 drop 再 raise」（U3 总量仍是 1，会蒙混过去）。
    """
    eng, leases = fresh(L, strict=strict)
    setup(eng, leases)
    keys_before = len(leases.ranges)                 # setup 之后的表（含 pre 之前的合法登记）
    shares_before = sum(1 for c in eng.calls if c[0] == "share")
    drops_after_setup = eng.drop_calls()             # 例内 drop 总量的基线（含 pre 阶段）
    if pre is not None:
        pre(leases)
    drops_at_target = eng.drop_calls()               # 目标调用开始前的 drop 计数
    raised, rtype, rmsg = False, None, ""
    ret = None
    try:
        ret = probe(leases)
    except L.LeaseError as exc:                      # 只捕被测错误类型，其余异常照抛
        raised, rtype, rmsg = True, "LeaseError", str(exc)
    drops_after = eng.drop_calls()
    keys_after = len(leases.ranges)
    unbooked = len(unbooked_events(leases))
    row = {
        "case": case, "kind": kind,
        "keys_before": keys_before, "keys_after": keys_after,
        "hit": ret is not None,
        "returned_block_seq": ret,
        "unbooked_events": unbooked,
        "unbooked_count": unbooked_count(leases),
        "raised": raised, "raised_type": rtype, "raised_msg": rmsg,
        "share_calls_before": shares_before,
        "share_calls_after": sum(1 for c in eng.calls if c[0] == "share"),
        "drop_calls_at_setup": drops_after_setup,
        "drop_calls_before": drops_at_target, "drop_calls_after": drops_after,
        "drop_calls_delta": drops_after - drops_after_setup,
        "drops_at_target": drops_at_target,
        "drop_delta_on_unbooked": drops_after - drops_at_target,
        "ranges_after": {"%d|%d|%d" % k: v for k, v in sorted(leases.ranges.items())},
        "holders_after": {str(k): sorted(v) for k, v in sorted(leases.holders.items())},
        "expect": expect,
    }
    row["checks"] = {
        "hit_ok": row["hit"] == expect["hit"],
        "raised_ok": row["raised"] == expect["raised"],
        "unbooked_events_ok": row["unbooked_events"] == expect["unbooked_events"],
        "unbooked_count_ok": row["unbooked_count"] == expect.get("unbooked_count"),
        "drop_calls_ok": row["drop_calls_delta"] == expect["drop_calls_delta"],
        "drop_on_unbooked_ok":
            row["drop_delta_on_unbooked"] == expect.get("drop_delta_on_unbooked"),
    }
    row["ok"] = all(row["checks"].values())
    return row


def cases(L):
    out = []
    # H1 命中：正常 detach 必须照旧（drop 1 次、无 unbooked、不抛）；这一次是**合法** call ⇒
    # drop_delta_on_unbooked 期望 1（名字沿用 lead 口径：该字段在命中例上就是"这次调用的 drop"）
    out.append(run_case(
        L, "H1_hit", "hit",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.detach(LIVE, 4045, 4095),
        {"hit": True, "raised": False, "unbooked_events": 0, "unbooked_count": 0,
         "drop_calls_delta": 1, "drop_delta_on_unbooked": 1}))
    # U1 从未登记：ranges 里没有这个键，却仍然 drop ⇒ 静默丢引用
    out.append(run_case(
        L, "U1_never_attached", "unbooked",
        lambda e, l: None,
        lambda l: l.detach(LIVE, 5000, 5010),
        {"hit": False, "raised": True, "unbooked_events": 1, "unbooked_count": 1,
         "drop_calls_delta": 0, "drop_delta_on_unbooked": 0}))
    # U2 表漂移：attach 后手工 pop 键（模拟记账漂移）再 detach
    def drift_setup(e, l):
        l.attach(HOME, LIVE, 4045, 4095)
        l.ranges.pop((LIVE, 4045, 4095), None)
    out.append(run_case(
        L, "U2_table_drift_pop", "unbooked", drift_setup,
        lambda l: l.detach(LIVE, 4045, 4095),
        {"hit": False, "raised": True, "unbooked_events": 1, "unbooked_count": 1,
         "drop_calls_delta": 0, "drop_delta_on_unbooked": 0}))
    # U3 二次 detach：第一次命中（合法 drop 1，记在 pre 阶段），第二次未命中（**不得 drop**、
    # 要抛、要记）⇒ 总量 1 但 drop_delta_on_unbooked 必须为 0
    out.append(run_case(
        L, "U3_second_detach", "unbooked",
        lambda e, l: l.attach(HOME, LIVE, 4045, 4095),
        lambda l: l.detach(LIVE, 4045, 4095),          # 目标：第二次（键已删）
        {"hit": False, "raised": True, "unbooked_events": 1, "unbooked_count": 1,
         "drop_calls_delta": 1, "drop_delta_on_unbooked": 0},
        pre=lambda l: l.detach(LIVE, 4045, 4095)))     # 第一次：合法命中
    # U4 非 strict 未命中（扩展床，不计入 4 例主分母）：仍记账/落事件/drop，但**不抛**
    out.append(run_case(
        L, "U4_non_strict_miss", "non_strict_miss",
        lambda e, l: None,
        lambda l: l.detach(LIVE, 5000, 5010),
        {"hit": False, "raised": False, "unbooked_events": 1, "unbooked_count": 1,
         "drop_calls_delta": 1, "drop_delta_on_unbooked": 1},
        strict=False))
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
    # 两套分母并列，不合并：主床 4 例（H1 + U1..U3，与 pre 基线可比）/ 扩展床 5 例（+U4 非 strict）
    main_rows = [r for r in rows if r["kind"] != "non_strict_miss"]
    ext_rows = list(rows)

    def denom(rs):
        return {"detach_calls": len(rs),
                "hits": sum(1 for r in rs if r["hit"]),
                "unbooked": sum(1 for r in rs if not r["hit"]),
                "unbooked_observed": sum(1 for r in rs if r["unbooked_events"] > 0)}

    fail = [r["case"] for r in rows if not r["ok"]]
    res = {
        "schema": "m3_l2_detach_v2",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "lease_module": {"path": lease_path, "sha16": lease_sha,
                         "strict_kw_accepted": STRICT_KW["accepted"]},
        "judge_source": {"path": "docs/_work/M2-FULL-PREREG-draft.md", "section": "§2.2 L2",
                         "sha16": "4978c94474ba050c"},
        "stub": "kvmem/m2_visibility/m3/_test_lease_detach.py::Stub（零引擎、只记调用）",
        "three_level_denominator": dict(
            denom(main_rows),
            cases=[r["case"] for r in main_rows],
            note="主床 4 例（H1 + U1..U3）：detach 调用数 / 命中数 / 未命中数 / observed unbooked"),
        "extended_three_level_denominator": dict(
            denom(ext_rows),
            cases=[r["case"] for r in ext_rows],
            note="扩展床 5 例（+U4_non_strict_miss）；与主床并列、不合并"),
        "drop_delta_on_unbooked": {r["case"]: r["drop_delta_on_unbooked"] for r in rows},
        "drop_calls_total": sum(r["drop_calls_delta"] for r in rows),
        "drop_calls_total_main": sum(r["drop_calls_delta"] for r in main_rows),
        "rows": rows, "fail_cases": fail,
        "exit": 0 if not fail else 2,
        "elapsed_s": round(time.time() - t0, 3),
    }
    out = args.out or os.path.join(tempfile.gettempdir(), "m3_lease_products",
                                   "M3-L2-%s.json" % time.strftime("%H%M%S"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    for r in rows:
        print("  %-20s kind=%-14s hit=%-5s raised=%-5s unbooked_ev=%-2s drop_tot=%-2s "
              "drop_on_unbooked=%-2s %s"
              % (r["case"], r["kind"], r["hit"], r["raised"], r["unbooked_events"],
                 r["drop_calls_delta"], r["drop_delta_on_unbooked"],
                 "ok" if r["ok"] else "RED"))
    d, e = res["three_level_denominator"], res["extended_three_level_denominator"]
    print("\n主床分母:   detach %d / 命中 %d / 未命中 %d（observed unbooked=%d）| drop_total=%d"
          % (d["detach_calls"], d["hits"], d["unbooked"], d["unbooked_observed"],
             res["drop_calls_total_main"]))
    print("扩展床分母: detach %d / 命中 %d / 未命中 %d（observed unbooked=%d）| drop_total=%d"
          % (e["detach_calls"], e["hits"], e["unbooked"], e["unbooked_observed"],
             res["drop_calls_total"]))
    print("drop_delta_on_unbooked: %s" % json.dumps(res["drop_delta_on_unbooked"],
                                                   ensure_ascii=False, sort_keys=True))
    print("lease sha16=%s | strict_kw=%s | fail=%s | exit=%d -> %s"
          % (lease_sha, STRICT_KW["accepted"], fail, res["exit"], out))
    return res["exit"]


if __name__ == "__main__":
    sys.exit(main())
