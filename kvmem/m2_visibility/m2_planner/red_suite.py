"""红脚本：每个 fake 只为一件事存在 —— 让某一条断言必须红。红不了 = 那条断言是假的。

产出：out/RED-SUITE.json + 终端表。退出码 0 表示"全部按设计红了"。
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kvsim, assertions as A, fake_planner as F, planner as PL

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

BPT, POOL = 104448, 855638016
BLOCKS = [{"seq": 1, "cells": 21, "pos_lo": 0, "key": 1},      # home
          {"seq": 2, "cells": 18, "pos_lo": 0, "key": 3},      # project（最不相关）
          {"seq": 3, "cells": 12, "pos_lo": 0, "key": 2}]      # habit
SPEC = {1: {"pos_lo": 4075, "pos_hi": 4095},
        2: {"pos_lo": 4014, "pos_hi": 4031},
        3: {"pos_lo": 3956, "pos_hi": 3967}}
CHAT_START = 4096
KEYS = {b["seq"]: b["key"] for b in BLOCKS}
BUDGET = {"n_ctx": 8192, "chat_len": 500, "bytes_per_token": BPT, "pool_bytes": POOL}


def build_sim():
    s = kvsim.Sim()
    for b in BLOCKS:
        s.add_block(b["seq"], b["cells"], 0)
    s.set_chat(CHAT_START, BUDGET["chat_len"])
    return s


def apply(sim, plan):
    for seq, target_pos in plan:
        b = sim.blocks[seq]
        want = target_pos - b["cells"] + 1
        sim.rotate(seq, want - b["pos_lo"])
    return sim


def run_case(name, planner, want_red, budget=None, keys=None):
    sim = build_sim()
    keys = keys or KEYS
    budget = budget or dict(BUDGET)
    refused, plan = None, None
    try:
        plan = planner(BLOCKS, sim.chat_start(), keys, budget)
    except F.PlanRefused as e:
        refused = e.reason
    res = {"case": name, "want_red": want_red, "refused": refused,
           "plan": plan, "asserts": {}}
    if plan is not None:
        apply(sim, plan)
        res["asserts"]["S1"] = A.S1_geometry(sim, plan, SPEC)
        res["asserts"]["S2"] = A.S2_budget(sim, plan, budget["chat_len"], budget["pool_bytes"])
        res["asserts"]["S3a"] = A.S3a_anchor(sim, plan, keys)
        res["asserts"]["S3b"] = A.S3b_order(sim, plan, keys)
    # S6 = **两档都算拒绝义务**（lead 撤回 P8 后恢复）。无淘汰 ⇒ 预算越界必伴随拒绝义务。
    expect_refuse = (sum(b["cells"] for b in BLOCKS) + budget["chat_len"]) > budget["n_ctx"] \
                    or (sum(b["cells"] for b in BLOCKS) * BPT) > budget["pool_bytes"]
    if expect_refuse:                      # S6 只在"本来就该拒绝"的场景下判定
        res["asserts"]["S6"] = A.S6_refuse(refused, "n_ctx")
    res["red"] = sorted(k for k, v in res["asserts"].items() if not v[0])
    res["as_designed"] = (want_red in res["red"])
    return res


def run_insert(name, mode, want_red):
    sim = build_sim()
    apply(sim, F.correct(BLOCKS, sim.chat_start(), KEYS, BUDGET))
    before = {s: sim.blocks[s]["pos_lo"] for s in sim.blocks}
    hashA = {s: sim.block_hash(s) for s in sim.blocks}
    new_cells = 19
    involved = {4}
    if mode == "no_drop":
        F.fake_insert_no_drop(sim, new_cells)
    else:
        F.correct_insert(sim, new_cells)
        if mode == "double_rotate":
            F.fake_double_rotate(sim, involved)
    for s in involved:
        sim.add_block(s, new_cells, sim.chat_start() - new_cells)
        sim.rotate(s, 0)
    after = {s: sim.blocks[s]["pos_lo"] for s in sim.blocks if s in before}
    hashB = {s: sim.block_hash(s) for s in before}
    res = {"case": name, "want_red": want_red,
           "asserts": {"S4": A.S4_no_drag(before, after, involved),
                       "S5": A.S5_bytes(hashA, hashB, involved)}}
    res["red"] = sorted(k for k, v in res["asserts"].items() if not v[0])
    res["as_designed"] = (want_red in res["red"])
    return res


def run_refuse():
    sim = build_sim()
    budget = dict(BUDGET, chat_len=8000)
    res = {"case": "P6 放不下不抛（返回空表）", "want_red": "S6", "asserts": {}}
    try:
        plan = F.fake_refuse_empty(BLOCKS, sim.chat_start(), KEYS, budget)
        res["plan"] = plan
    except F.PlanRefused as e:
        res["refused"] = e.reason
    res["asserts"]["S6"] = (res.get("refused") is not None, {"plan": res.get("plan")})
    res["red"] = sorted(k for k, v in res["asserts"].items() if not v[0])
    res["as_designed"] = "S6" in res["red"]
    return res


def run_no_effect(name, want_red):
    """P11：每一步都报成功，但什么都没生效 —— 顺序判据对此完全失明。"""
    sim = kvsim.SimNoEffect()
    for b in BLOCKS:
        sim.add_block(b["seq"], b["cells"], 0)
    sim.set_chat(CHAT_START, 50)
    for b in BLOCKS:
        sim.mark_visible("chat", 4000, 4000 + b["cells"])
    ranges = [(4000, 4000 + b["cells"]) for b in BLOCKS]
    err = None
    try:
        PL.apply_insert(sim, "chat", ranges, (4200, 4250), 12, cells_of=lambda q: 500,
                        new_block=(1, 4096, 4108))
    except PL.PlanInvariant as e:
        err = str(e)
    res = {"case": name, "want_red": want_red,
           "asserts": {"E1_effect": (err is not None, {"raised": err})}}
    res["red"] = sorted(k for k, v in res["asserts"].items() if not v[0])
    # 这一条的"达标"是**检查必须开火**（不是判据变红）：假 planner 全报 ok，安全检查必须抛
    res["as_designed"] = bool(err is not None)
    return res


cases = [
    run_case("P0 正确版（对照）", F.correct, want_red="__none__"),
    run_case("P1 几何重叠", F.fake_overlap, want_red="S1"),
    run_case("P2 无视预算", F.fake_ignore_budget, want_red="S2", budget=dict(BUDGET, chat_len=8180)),
    run_case("P3 锚点差一位", F.fake_anchor_off_by_one, want_red="S3a"),
    run_case("P4 tie-break 反了", F.fake_tie_reversed, want_red="S3b",
             keys={1: 1, 2: 2, 3: 2}),
    run_insert("P5 插入先移对话后摘引用", "no_drop", want_red="S4"),
    run_insert("P7 位置全对但多转一次", "double_rotate", want_red="S5"),
    run_refuse(),
    run_no_effect("P11 每步都 ok 但什么都没生效", want_red="__check_fires__"),
]

ok = True
for c in cases:
    flag = "RED-AS-DESIGNED" if c["as_designed"] else "**NOT AS DESIGNED**"
    if c["want_red"] == "__none__":
        flag = "GREEN-AS-DESIGNED" if not c["red"] else "**SHOULD BE GREEN**"
        ok = ok and not c["red"]
    else:
        ok = ok and c["as_designed"]
    print("%-30s want=%-7s red=%-16s %s" % (c["case"], c["want_red"], ",".join(c["red"]) or "-", flag))

json.dump({"schema": "red_suite_v1", "all_as_designed": ok, "note":
           "S4=位置(拖动)证据；S5=字节证据。两者不可互相顶替。S5 的必红构造成立的前提是"
           "『位置逐位相同、只多一次重转』——因为真实产物里 requant 会改变约 48% 字节取值。",
           "cases": cases}, open(os.path.join(OUT, "RED-SUITE.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2, default=str)
print("\nall_as_designed =", ok)
sys.exit(0 if ok else 1)
