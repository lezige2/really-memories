# -*- coding: utf-8 -*-
"""绿套件：域内四条（S1/S3a/S4/S5）必须绿；契约测试三条（S2/S3b/S6）也必须有绿。

验收口径（lead 裁定）：**M2 通过 = 域内四条全绿 + 真机插入一次成功**。
契约测试不作为通过条件，但作为回归锁保留 —— 它们测的是**大负载行为**，M2 的运行点是小负载。
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kvsim, assertions as A, planner as PL

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
BPT, POOL = 104448, 855638016
BUDGET = {"n_ctx": 8192, "chat_len": 500, "bytes_per_token": BPT, "pool_bytes": POOL}
MANIFEST = {1: {"pos_lo": 4075, "pos_hi": 4095}, 2: {"pos_lo": 4014, "pos_hi": 4031},
            3: {"pos_lo": 3956, "pos_hi": 3967}}
CELLS = {1: 21, 2: 18, 3: 12}
KEYS = {1: 1, 2: 2, 3: 3}
GAPS = {1: 43, 2: 46}
CHAT_START = 4096
BLOCKS = [{"seq": s, "cells": CELLS[s]} for s in (1, 2, 3)]
DOMAIN = ("S1", "S3a", "S4", "S5")            # 计入验收
CONTRACT = ("S2", "S3b", "S6_nctx", "S6_pool")  # 回归锁，不计入验收

res = {"schema": "green_suite_v2",
       "acceptance_rule": "M2 通过 = 域内四条(S1/S3a/S4/S5)全绿 + 真机插入一次成功",
       "domain": list(DOMAIN), "contract_tests": list(CONTRACT), "assertions": {}}


def build(with_chat=True):
    s = kvsim.Sim()
    for b in BLOCKS:
        s.add_block(b["seq"], b["cells"], 0)
    if with_chat:
        s.set_chat(CHAT_START, BUDGET["chat_len"])
    return s


p = PL.plan(BLOCKS, CHAT_START, BUDGET, keys=KEYS, gaps=GAPS)
plan_tuples = [(e["seq"], e["pos_hi"]) for e in p]
sim = build()
rot, core_base = {}, []
for e in p:
    delta = PL.delta_for(e)
    sim.rotate(e["seq"], delta - sim.blocks[e["seq"]]["pos_lo"])
    rot[e["seq"]] = 1
    core_base.append({"seq": e["seq"], "delta_used": delta, "base": e["base"],
                      "pos_hi": e["pos_hi"], "cells": e["cells"], "ok": PL.check_entry(e)})

res["plan"] = p
res["assertions"]["S1"] = A.S1_geometry(sim, plan_tuples)
res["assertions"]["S1m_manifest"] = (
    all((e["base"], e["pos_hi"]) == (MANIFEST[e["seq"]]["pos_lo"], MANIFEST[e["seq"]]["pos_hi"]) for e in p),
    {"got": {e["seq"]: [e["base"], e["pos_hi"]] for e in p},
     "kind": "回归锁：gaps 反推自冻结几何，只证明『给定同一组空隙能复现同一布局』",
     "does_not_show": "不证明规划器能自己布局，也不证明它能推出缝宽"})
res["assertions"]["S2"] = A.S2_budget(sim, plan_tuples, BUDGET["chat_len"])
res["assertions"]["S3a"] = A.S3a_anchor(sim, plan_tuples, KEYS)
_s3b = A.S3b_order(sim, plan_tuples, KEYS)
_s3b[1]["triviality"] = ("本夹具三块 key 互不相同(1/2/3) => S3b 的绿在此夹具上平凡；"
                        "distance_key 由调用方注入，真实相关性打分完全可能平局，"
                        "平局来源(相关度计算)不在本模块范围")
res["assertions"]["S3b"] = _s3b
res["assertions"]["CORE_rot_once"] = (all(v == 1 for v in rot.values()), {"rotations_per_block": rot})
res["assertions"]["CORE_base_poshi"] = (all(c["ok"] for c in core_base) and
                                        all(c["delta_used"] == c["base"] for c in core_base),
                                        {"per_block": core_base})
res["assertions"]["CORE_base_anchor"] = (
    {e["seq"]: [e["base"], e["pos_hi"]] for e in p} == {k: [v["pos_lo"], v["pos_hi"]] for k, v in MANIFEST.items()},
    {"anchor_source": "冻结几何（既有产物常量），非本模块推导"})
_p2 = PL.plan([{"seq": 1, "cells": 21}, {"seq": 2, "cells": 18}, {"seq": 4, "cells": 19}],
              4096 + 19, dict(BUDGET), keys={1: 1, 2: 2, 4: 3})
res["assertions"]["CORE_base_poshi_newcells"] = (
    all(PL.check_entry(e) for e in _p2) and [e["cells"] for e in _p2] and 19 in [e["cells"] for e in _p2],
    {"plan": _p2, "note": "新块 cells=19 与既有 21/18/12 不同，不变式重验"})
try:
    PL.delta_for({"seq": 9, "pos_hi": 100, "cells": 4})
    _bad = "accepted pos_hi-only entry"
except PL.PlanInvariant:
    _bad = None
res["assertions"]["CORE_delta_rejects_poshi"] = (_bad is None, {"detail": _bad or "抛 PlanInvariant"})


def _refuse(budget):
    try:
        PL.plan(BLOCKS, CHAT_START, budget, keys=KEYS)
        return None
    except PL.PlanRefused as e:
        return e.reason


# S6 绿：小上下文(600)放不下 51 cells + 对话 —— 合法配置，不是荒谬输入
_s6 = A.S6_refuse(_refuse(dict(BUDGET, n_ctx=600, chat_len=560)), "n_ctx")
_s6[1]["why_legal"] = ("n_ctx=600 能放下 51 cells（51+560=611 才越界），只是放不下这么长的对话 —— 可以存在的配置；"
                                             "P8 当年用的 9.57 token 池连一个 cell 都放不下，自相矛盾，故被否")
res["assertions"]["S6_nctx"] = _s6
_s6p = A.S6_refuse(_refuse(dict(BUDGET, pool_bytes=1000000)), "pool_bytes")
res["assertions"]["S6_pool"] = _s6p
_s6p[1]["note"] = "防御性断言（池=整个 KV cache，默认预算下不可触发，不进判据表）"

# ---- S4 / S5：插入一块，既有三块位置与字节都不变 ----
before = {s: sim.blocks[s]["pos_lo"] for s in sim.blocks}
hashA = {s: sim.block_hash(s) for s in sim.blocks}
ranges = [(sim.blocks[s]["pos_lo"], sim.blocks[s]["pos_lo"] + CELLS[s] - 1) for s in sim.blocks]
ops = PL.insert_ops("chat", list(sim.blocks), ranges, 19)
order_ok = True
try:
    PL.check_ops(ops)
except PL.PlanInvariant:
    order_ok = False
sim.move_chat(19, blocks_dropped=True)
sim.add_block(4, 19, sim.chat_start() - 19)
sim.rotate(4, 0)
after = {s: sim.blocks[s]["pos_lo"] for s in before}
hashB = {s: sim.block_hash(s) for s in before}
res["assertions"]["S4"] = A.S4_no_drag(before, after, {4})
_s5 = A.S5_bytes(hashA, hashB, {4})
_s5[1]["covers"] = "对应 13.4 第三条（插入前后未参与块 0 字节变化）"
res["assertions"]["S5"] = _s5
res["assertions"]["S6b_ops_order"] = (order_ok, {"ops": [list(o) for o in ops]})

# ---- P10：S5 的**绿案例**，口径与真实产物 M2S3_car_back <-> no_car 相同 ----
a_sim = build()
for e in PL.plan(BLOCKS, CHAT_START, BUDGET, keys=KEYS, gaps=GAPS):
    a_sim.rotate(e["seq"], e["base"] - a_sim.blocks[e["seq"]]["pos_lo"])
b_sim = build()
for e in PL.plan(BLOCKS, CHAT_START, BUDGET, keys=KEYS, gaps=GAPS):
    b_sim.rotate(e["seq"], e["base"] - b_sim.blocks[e["seq"]]["pos_lo"])
b_sim.move_chat(19, blocks_dropped=True); b_sim.add_block(4, 19, b_sim.chat_start() - 19)
ha = {s: a_sim.block_hash(s) for s in (1, 2, 3)}
hb = {s: b_sim.block_hash(s) for s in (1, 2, 3)}
p10_ok = ha == hb
res["assertions"]["P10_S5_green"] = (p10_ok, {
    "kind": "跨布局比较（有 car 块 vs 无 car 块），与 M2S3_car_back <-> M2S3_no_car 同口径",
    "A_no_car": ha, "B_car_back": hb, "all_eq": p10_ok,
    "note": "S5 是唯一映射 13.4 第三条的判据；只有红没有绿等于没验过，故必须补这条绿"})

# ---- E1：apply_insert 的逐步读回验证（正确实现必须不抛，且 moved 与生效都核对）----
_es = kvsim.Sim()
for b in BLOCKS:
    _es.add_block(b["seq"], b["cells"], 0)
_es.set_chat(CHAT_START, 50)
_es.mark_visible("chat", 4000, 4021)
_es.mark_visible("chat", 4021, 4039)
_es.mark_visible("chat", 4039, 4051)
_es.mark_visible("chat", 4096, 4146)
_eranges = [(4000, 4021), (4021, 4039), (4039, 4051)]
try:
    _log = PL.apply_insert(_es, "chat", _eranges, (4096, 4146), 12,
                           cells_of=lambda q: 101, new_block=(1, 4158, 4170),
                           reshares=[(1, 4000, 4021), (2, 4021, 4039), (3, 4039, 4051)])
    _e1 = (True, {"log": _log})
except Exception as e:                                  # noqa: BLE001
    _e1 = (False, {"error": str(e)})
res["assertions"]["E1_effect_verified"] = _e1
try:
    PL.apply_insert(kvsim.SimNoEffect(), "chat", [(4000, 4021)], (4096, 4146), 12, cells_of=lambda q: 101)
    _e2 = (False, {"detail": "SimNoEffect 竟然通过 —— 效果验证失明"})
except PL.PlanInvariant as e:
    _e2 = (True, {"raised": str(e), "note": "「全 ok 但没动」必须被这条抓住"})
res["assertions"]["E1_fires_on_no_effect"] = _e2

doms = [res["assertions"][k][0] for k in DOMAIN]
contr = [res["assertions"][k][0] for k in CONTRACT]
res["domain_green"] = all(doms)
res["contract_green"] = all(contr)
res["all_green"] = all(v[0] for v in res["assertions"].values())
for k, v in res["assertions"].items():
    layer = "域内" if k in DOMAIN else ("契约" if (k in CONTRACT or k.startswith("S6")) else "约束")
    print("%-24s %-5s %s" % (k, layer, "GREEN" if v[0] else "**RED**"))
print("\ndomain_green=%s contract_green=%s all_green=%s" % (res["domain_green"], res["contract_green"], res["all_green"]))
json.dump(res, open(os.path.join(OUT, "GREEN-SUITE.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2, default=str)
sys.exit(0 if res["all_green"] else 1)
