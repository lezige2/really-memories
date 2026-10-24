# -*- coding: utf-8 -*-
"""Put the inspector-frozen verdict text INSIDE run_m3_50.json (not only in the README)."""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "run_m3_50.json")
d = json.load(io.open(p, encoding="utf-8"))
d["verdict"] = {
    "criterion5_dangling_refcount": "no_effect",
    "criterion5_text": (
        "就「引用计数悬空」这一后果断言而言：无效应（reset 源 seq 后对话答案逐字不变，"
        "addr 命中 50/50 不受影响）。真正的损失不在悬空，而在源 seq 句柄静默失效"
        "（21 cell -> 0、pos_max -> -1、reset 无异常返回），只能靠文件重载恢复。"
        "「必须失败」不是 MD 的预设，是本轮派单的问法，不得写进对 MD 的判定。"),
    "pin_reason": "kept for diagnosability: turn a silent invalidation into an explicit refusal "
                  "(not to prevent dangling references, which did not occur)",
    "md_rule_validated": False,
    "guard_status": "ready_not_wired; product path (tools/chat.py :176/:284/:444/:449) has 0 "
                    "coverage; criterion 5 does NOT count toward M3 completion",
    "pos_max_policy": "only kvshim_seq_pos_max_raw (4095) counts; kvshim_pos_max reports -1 for "
                      "seq_cp-built sequences",
    "after_detach_cells": "two values only: 73 (one question) / 221 (rounds 1/25/50 ask three) — "
                          "not occupancy growth",
}
json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
print("stamped verdict into run_m3_50.json")
