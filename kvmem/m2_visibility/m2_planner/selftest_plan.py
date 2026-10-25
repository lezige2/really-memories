# -*- coding: utf-8 -*-
"""冻结接口 `plan()` 薄适配层 + 淘汰策略的**零 GPU 单测**（不加载引擎、不碰 GPU、不读块文件）。

跑法：`python -X utf8 selftest_plan.py` ⇒ 写 `out/PLAN-SELFTEST.json`，退出码 0 表示
「所有 case 的实得与期望一致，且三条必红构造都真的红了」。

口径纪律：
- 每个 case 只断言**一件事**，`expect` 与 `got` 都落盘，便于别人复算；
- 「必红构造」单独记在 `red_checks`：它证明不变式不是恒真 —— 只报绿不报红 = 没证明判据存在；
- 全部读数都是纯函数结果；本文件**不**给 M2 验收下结论。
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import plan as PLAN                # 本单新增：冻结接口适配层
import evict_policy as EV          # 本单新增：淘汰（独立、默认 off）
import planner as PL               # 既有实现（不改其语义）

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

BPT, POOL = 104448, 855638016      # 实测恒等：855638016 / 104448 = 8192 = n_ctx
CHAT_START = 4096
BASE_BUDGET = {"n_ctx": 8192, "chat_len": 500, "bytes_per_token": BPT, "pool_bytes": POOL}

# 冻结几何（M2-PLAN §1 的实测来源；gaps 是**输入**，反推自冻结几何 —— 见 PROGRESS:1799）
BLOCKS = [{"seq": 1, "cells": 21, "key": 1, "gap": 43},     # home
          {"seq": 2, "cells": 18, "key": 2, "gap": 46},     # project
          {"seq": 3, "cells": 12, "key": 3, "gap": 0}]      # habit
FROZEN = {1: (4075, 4095), 2: (4014, 4031), 3: (3956, 3967)}  # base, pos_hi

cases, red_checks = [], []


def case(cid, sub, what, expect, fn):
    ok, got, note = fn()
    cases.append({"id": cid, "sub_problem": sub, "what": what, "expect": expect,
                  "got": got, "pass": bool(ok), "note": note})


def red(cid, what, expect_raise, fn):
    try:
        fn()
        got, fired = "no exception", False
    except Exception as e:                       # noqa: BLE001 —— 红的判据是「抛了且类型对」
        got, fired = "%s: %s" % (type(e).__name__, e), isinstance(e, expect_raise)
    red_checks.append({"id": cid, "what": what, "expect_raise": expect_raise.__name__,
                       "got": got, "fired_as_designed": fired})


# ---------------- F1 返回类型 ----------------
def _f1():
    out = PLAN.plan(BLOCKS, CHAT_START, BASE_BUDGET)
    ok = (isinstance(out, list) and len(out) == 3
          and all(isinstance(t, tuple) and len(t) == 2 for t in out)
          and all(isinstance(s, int) and isinstance(p, int) for s, p in out)
          and sorted(s for s, _ in out) == [1, 2, 3])
    return ok, out, "冻结契约的返回形状：list[tuple[int, int]]，一个块一条"


case("F1", "contract", "plan() 返回 [(seq, target_pos)] 而不是 dict 列表",
     "list[tuple]，3 条，seq 集合 = {1,2,3}", _f1)


# ---------------- F2 无语义漂移 ----------------
def _f2():
    adapter = PLAN.plan_placements(BLOCKS, CHAT_START, BASE_BUDGET)
    direct = PL.plan(BLOCKS, CHAT_START, BASE_BUDGET,
                     keys={b["seq"]: b["key"] for b in BLOCKS},
                     gaps={b["seq"]: b["gap"] for b in BLOCKS if "gap" in b})
    same = ([(e["seq"], e["pos_hi"]) for e in adapter]
            == [(e["seq"], e["pos_hi"]) for e in direct])
    invariants = all(e["base"] + e["cells"] - 1 == e["pos_hi"] for e in adapter)
    got = {"adapter": [(e["seq"], e["base"], e["pos_hi"]) for e in adapter],
           "direct": [(e["seq"], e["base"], e["pos_hi"]) for e in direct],
           "identical": same, "base_plus_cells_minus_1_eq_pos_hi": invariants}
    return same and invariants, got, "适配层只折叠形状，不重排、不算位置"


case("F2", "contract", "适配层与既有 placement 逐条相同（不改语义）",
     "两列 (seq,base,pos_hi) 相同 且 base+cells-1==pos_hi", _f2)


# ---------------- F3 冻结几何回归锁 ----------------
def _f3():
    out = PLAN.plan_placements(BLOCKS, CHAT_START, BASE_BUDGET)
    got = {e["seq"]: (e["base"], e["pos_hi"]) for e in out}
    ok = got == FROZEN
    return ok, got, ("回归锁：**给定同一组空隙**能复现冻结几何；"
                     "不证明规划器会自己布局、更不证明它能推出缝宽（gaps 只作输入）")


case("F3", "order", "同一组输入复现冻结几何 4075/4095、4014/4031、3956/3967",
     dict(FROZEN), _f3)


# ---------------- F4 gaps 只作输入 ----------------
def _f4():
    zero_gaps = [{k: v for k, v in b.items() if k != "gap"} for b in BLOCKS]
    out_zero = PLAN.plan_placements(zero_gaps, CHAT_START, BASE_BUDGET)
    got_zero = {e["seq"]: (e["base"], e["pos_hi"]) for e in out_zero}
    out_frozen = PLAN.plan_placements(BLOCKS, CHAT_START, BASE_BUDGET)
    got_frozen = {e["seq"]: (e["base"], e["pos_hi"]) for e in out_frozen}
    changed = got_zero != got_frozen
    return changed, {"without_gap": got_zero, "with_gap": got_frozen,
                     "positions_changed": changed}, (
        "缺省 gap=0 与显式 gap 给出不同位置 ⇒ 缝宽是**被传进来的**，不是从几何反推的；"
        "缝宽由什么决定仍未回答（PROGRESS §13.4 末段）")


case("F4", "order", "gap 缺省=0，且显式 gap 会改变布局（缝宽是输入不是推导）",
     "positions_changed=True", _f4)


# ---------------- F5 最相关紧贴对话 + tie-break ----------------
def _f5():
    blocks = [{"seq": 1, "cells": 10, "key": 2}, {"seq": 2, "cells": 10, "key": 2}]
    out = PLAN.plan_placements(blocks, CHAT_START, BASE_BUDGET)
    pos = {e["seq"]: e["pos_hi"] for e in out}
    ok = (pos[1] == CHAT_START - 1 and pos[2] == CHAT_START - 1 - 10)
    return ok, {"pos_hi": pos, "chat_start": CHAT_START, "tie_break": "同 key ⇒ seq 小的更贴近对话"}, (
        "最相关块的 pos_hi = chat_start-1（距离 1）；平手按 seq 升序贴近")


case("F5", "order", "最相关紧贴对话、平手按 seq 决定先后", {"seq1": 4095, "seq2": 4085}, _f5)


# ---------------- F6 拒绝义务（不降级） ----------------
def _f6():
    got = {}
    try:
        PLAN.plan(BLOCKS, CHAT_START, dict(BASE_BUDGET, chat_len=8180))
        got["over_ctx"] = "no exception"
    except Exception as e:                        # noqa: BLE001
        if not isinstance(e, PL.PlanRefused):
            raise
        got["over_ctx"] = e.reason
    got["empty"] = PLAN.plan([], CHAT_START, BASE_BUDGET)
    try:
        PLAN.plan(BLOCKS, CHAT_START, dict(BASE_BUDGET, chat_len=8200))
        got["chat_alone"] = "no exception"
    except Exception as e:                        # noqa: BLE001
        if not isinstance(e, PL.PlanRefused):
            raise
        got["chat_alone"] = e.reason
    ok = (got["over_ctx"] == "n_ctx" and got["empty"] == []
          and got["chat_alone"] == "n_ctx")
    return ok, got, ("放不下 ⇒ 抛 PlanRefused(reason='n_ctx')，**不返回空表/不降级**；"
                     "空输入 ⇒ []（这不是「放不下」）")


case("F6", "budget", "超预算必须拒绝且理由正确；空输入返回空表",
     {"over_ctx": "n_ctx", "empty": [], "chat_alone": "n_ctx"}, _f6)


# ---------------- F7 target_pos 的所指 ----------------
def _f7():
    out = PLAN.plan_placements([{"seq": 1, "cells": 21, "key": 1}], CHAT_START, BASE_BUDGET)
    e = out[0]
    ok = (e["pos_hi"] == 4095 and e["base"] == 4075 and e["pos_hi"] != e["base"]
          and PLAN.target_pos_of(e) == e["pos_hi"])
    return ok, {"pos_hi": e["pos_hi"], "base": e["base"], "cells": e["cells"],
                "target_pos": PLAN.target_pos_of(e)}, (
        "target_pos = pos_hi（最大占用位），不是 base；差 cells-1 —— FIELDS.md 里那个坑")


case("F7", "contract", "target_pos 指的是 pos_hi 而不是 base（cells=21 时两者差 20）",
     {"pos_hi": 4095, "base": 4075}, _f7)


# ---------------- F8 插入顺序：先摘引用再移动 ----------------
def _f8():
    ops = PL.insert_ops(0, [1], [(4005, 4096)], 12)
    names = [o[0] for o in ops]
    drop_first = names.index("drop") < min(i for i, n in enumerate(names)
                                           if n == "repos_local")
    ordered = PL.check_ops(ops)
    return bool(drop_first and ordered), {"ops": ops, "drop_precedes_repos_local": drop_first,
                                          "check_ops": ordered}, (
        "§2.3 第 3 步的四步顺序：drop(seq_rm) → repos_local(chat,+n) → 新块落位 → 全部 seq_cp；"
        "先移对话会把块一起拖走（L7 陷阱 2）")


case("F8", "insert", "插入四步顺序断言：drop 早于 repos_local(chat)",
     "drop_precedes_repos_local=True 且 check_ops=True", _f8)


# ---------------- F9 淘汰默认 off ----------------
def _f9():
    order = EV.evict_order(BLOCKS)
    sel = EV.select_to_evict(BLOCKS, chat_len=8180, n_ctx=8192)
    ok = (order == [] and sel["evicted"] == [] and sel["over_budget_before"] is True
          and sel["over_budget_after"] is True)
    return ok, {"evict_order": order, "select": {k: sel[k] for k in
                                                 ("policy", "evicted", "over_budget_before",
                                                  "over_budget_after")}}, (
        "默认 off ⇒ 一个都不踢；装不下时 over_budget_after 仍 True，调用方的正确动作是**拒绝**"
        "（与 plan() 的 PlanRefused 一致），不是降级")


case("F9", "evict", "淘汰默认 off：不踢块，超预算读数照实留 True",
     {"evict_order": [], "evicted": [], "over_after": True}, _f9)


# ---------------- F10 显式 lru ----------------
def _f10():
    blocks = [{"seq": 1, "cells": 21, "key": 1, "last_used": 5},
              {"seq": 2, "cells": 18, "key": 2, "last_used": 4},
              {"seq": 3, "cells": 12, "key": 3, "last_used": 3},
              {"seq": 4, "cells": 19, "key": 4, "last_used": 2}]
    order = EV.evict_order(blocks, policy="lru")
    sel = EV.select_to_evict(blocks, chat_len=500, n_ctx=8192, policy="lru", mount_cap=40)
    kept_cells = sum(int(b["cells"]) for b in sel["kept"])
    ok = (order == [4, 3, 2, 1] and sel["evicted"] == [4, 3]
          and kept_cells <= 40 and sel["over_budget_after"] is False)
    return ok, {"evict_order": order, "evicted": sel["evicted"],
                "kept": [b["seq"] for b in sel["kept"]], "kept_cells": kept_cells,
                "mount_cap_used": sel["mount_cap_used"]}, (
        "显式开启才踢；顺序 = last_used 最旧先（4→3→2→1）；mount_cap 由调用方给数，"
        "本模块不发明阈值")


case("F10", "evict", "显式 lru：按 last_used 最旧先踢，踢到装得下为止",
     {"evict_order": [4, 3, 2, 1], "evicted": [4, 3], "kept_cells<=40": True}, _f10)


# ---------------- F11 主路径无淘汰 / mount_cap 档已删 ----------------
def _f11():
    with_cap = PLAN.plan(BLOCKS, CHAT_START, dict(BASE_BUDGET, mount_cap=40))  # 不设阈值的输入
    without = PLAN.plan(BLOCKS, CHAT_START, BASE_BUDGET)
    ok = (len(with_cap) == 3 and with_cap == without)
    return ok, {"with_mount_cap": with_cap, "without": without, "identical": with_cap == without,
                "why": "RESULTS-RED.md:143 该档已删除（无确切值）；plan() 不读它 ⇒ 主路径不淘汰"}, (
        "mount_cap 传进来也被忽略：主路径无淘汰、预算只有一档（n_ctx）")


case("F11", "evict", "plan() 主路径不淘汰（mount_cap 不在主路径里起作用）",
     "3 条 placement 全在，mount_cap 被忽略", _f11)


# ---------------- F12 字节档恒真（同一约束） ----------------
def _f12():
    with_bytes = PLAN.plan_placements(BLOCKS, CHAT_START, BASE_BUDGET)
    no_bytes = PLAN.plan_placements(BLOCKS, CHAT_START, {"n_ctx": 8192, "chat_len": 500})
    same = ([(e["seq"], e["pos_hi"]) for e in with_bytes]
            == [(e["seq"], e["pos_hi"]) for e in no_bytes])
    identity = POOL // BPT == 8192
    return same and identity, {"same_placements": same,
                               "identity": "%d / %d = %d = n_ctx" % (POOL, BPT, POOL // BPT)}, (
        "省掉 bytes 字段时按恒等式补齐，结果不变 ⇒ pool 档与 n_ctx 档是同一约束的两种货币写法")


case("F12", "budget", "bytes/pool 档恒真：补与不补，布局相同",
     {"same_placements": True, "identity": "855638016/104448=8192=n_ctx"}, _f12)


# ---------------- 必红构造 ----------------
red("R1", "把 base 改成 pos_hi 喂进 check_entry ⇒ 结构不变式必须抛",
    PL.PlanInvariant,
    lambda: PL.check_entry({"base": 4095, "cells": 21, "pos_hi": 4095}))

red("R2", "插入顺序反着来（先移对话后摘引用）⇒ check_ops 必须抛（L7 陷阱 2）",
    PL.PlanInvariant,
    lambda: PL.check_ops([("repos_local", 0, 12), ("drop", 0, 4005, 4096)]))

red("R3", "超预算却返回空表（静默降级）由 plan() 的 PlanRefused 挡住：这里直接验拒绝路径",
    PL.PlanRefused,
    lambda: PLAN.plan(BLOCKS, CHAT_START, dict(BASE_BUDGET, chat_len=8200)))


# ---------------- 汇总 ----------------
def _sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


n_pass = sum(1 for c in cases if c["pass"])
n_fail = len(cases) - n_pass
inv = [c["id"] for c in cases if not c["pass"]] + \
      [r["id"] for r in red_checks if not r["fired_as_designed"]]
res = {
    "schema": "m2_plan_frontdoor_selftest_v1",
    "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "scope": "冻结接口 plan() 薄适配 + 淘汰独立策略；零 GPU、纯函数、不加载引擎",
    "frozen_interface": "plan(blocks, chat_start, budget) -> [(seq, target_pos)]",
    "target_pos_meaning": "pos_hi（最大占用位），base = target_pos - cells + 1",
    "modules": {"plan.py": _sha16(os.path.join(HERE, "plan.py")),
                "evict_policy.py": _sha16(os.path.join(HERE, "evict_policy.py")),
                "planner.py": _sha16(os.path.join(HERE, "planner.py"))},
    "budget_tiers": {"n_ctx": "唯一预算档（cells + chat_len <= n_ctx）",
                     "bytes_tier": "恒真（pool_bytes = n_ctx * bytes_per_token），不进判据",
                     "mount_cap_tier": "已删除（无确切值/无出处，RESULTS-RED.md:143）"},
    "eviction": {"default": "off", "in_main_path": False,
                 "why": "签字版非目标（RESULTS-RED.md:150）+ S2↔S6 耦合论证以「无淘汰」为前提"
                        "（RESULTS-RED.md:94/170）"},
    "cases": cases,
    "red_checks": red_checks,
    "n_pass": n_pass, "n_fail": n_fail, "n_cases": len(cases), "n_red": len(red_checks),
    "invariant_failures": inv,
    "acceptance_claim": "none —— 本产物只证明适配层与淘汰策略的纯函数行为，**不构成 M2 验收**",
    "exit": 0 if not inv else 2,
}
p = os.path.join(OUT, "PLAN-SELFTEST.json")
with open(p, "w", encoding="utf-8", newline="\n") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)

print("%-4s %-9s %-6s %s" % ("id", "sub", "verdict", "what"))
for c in cases:
    print("%-4s %-9s %-6s %s" % (c["id"], c["sub_problem"], "GREEN" if c["pass"] else "RED",
                                 c["what"]))
for r in red_checks:
    print("%-4s %-9s %-6s %s" % (r["id"], "red", "FIRED" if r["fired_as_designed"] else "MISSED",
                                 r["what"]))
print("n_pass=%d n_fail=%d n_red=%d inv=%s" % (n_pass, n_fail, len(red_checks), inv))
sys.exit(res["exit"])