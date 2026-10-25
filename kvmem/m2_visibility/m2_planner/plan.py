# -*- coding: utf-8 -*-
"""M2 放置规划器 —— **冻结接口**薄适配层（§2.3 / `PROGRESS:160`、`PROGRESS:1793`）。

冻结契约（不许改签名）：

    plan(blocks, chat_start, budget) -> [(seq, target_pos)]

语义（与 `planner.py` 的字段一一对应，**不新造词**）：

- `target_pos` = 该块的**最大占用位** `pos_hi`；`base = target_pos - cells + 1`；
  `repos_local` 的 `delta` 只接受 `base`（见 `FIELDS.md`：「一个词指两样东西」是上一版的风险源）。
- 输出顺序 = **先远后近**（继承 `planner.plan` 的语义），便于调用方从远到近逐块 `repos_local`。
- `blocks` 条目：`{seq, cells, key?, gap?}`。
  `key` = `distance_key`（越小越相关，由**调用方**给；相关度计算不在本模块）；
  `gap` = 该块下方额外留空（**只作输入**，来源未定义 —— 见 `PROGRESS:1799` / §13.4 末段：
  现有 `S1m` 的 `gaps={1:43,2:46}` 是从冻结几何反推的，**不许**让规划器自己推）。
- `budget`：`{n_ctx, chat_len}`；`bytes_per_token` / `pool_bytes` 可省。
  省掉时按**恒等式**补齐：`pool_bytes = n_ctx * bytes_per_token`（默认 `104448`）。
  理由（`RESULTS-RED.md` §8.2/§8.2b）：`855,638,016 / 104,448 = 8,192 = n_ctx` ⇒
  `pool_bytes` 档与 `n_ctx` 档是**同一个约束的两种货币写法，不是两个约束**。
  这两个数只是维持 `planner.py` 既有防御性断言，**不是新判据**；预算只有一档。

**无淘汰**：淘汰是签字版的非目标（`RESULTS-RED.md:150`、`M2-PLAN.md` §4），本文件不实现、
也不偷偷降级 —— 放不下就 `PlanRefused`（静默降级会变成假绿）。要淘汰请显式用
`evict_policy.py`（独立模块，默认 `off`），并注意那条「无淘汰」前提。

本文件**不改** `planner.py` 的任何语义：placement 完全由 `planner.plan()` 决定，
这里只做两件事 —— 把参数从 `blocks` 条目里取出来、把 dict 列表折成 `(seq, target_pos)` 元组。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import planner as _PL          # 既有实现（本次不改其语义）

BPT_DEFAULT = 104448           # 实测常量：pool_bytes / n_ctx（RESULTS-RED.md §8.2 的恒等式）
REFUSALS = ("n_ctx", "pool_bytes")

PlanRefused = _PL.PlanRefused
PlanInvariant = _PL.PlanInvariant


def plan(blocks, chat_start, budget):
    """冻结接口：返回 `[(seq, target_pos)]`，`target_pos = pos_hi`，先远后近。

    纯函数：不读时钟、不读磁盘、不碰引擎；同一输入永远同一输出。
    """
    return [(e["seq"], e["pos_hi"]) for e in plan_placements(blocks, chat_start, budget)]


def plan_placements(blocks, chat_start, budget):
    """同一次计算，但返回**带 base/cells 的完整条目**（供断言与调用方用）。

    条目：`{seq, base, pos_hi, cells}`；`base + cells - 1 == pos_hi` 由 `planner.check_entry` 保。
    """
    if not blocks:
        return []                        # 空输入 ⇒ 空列表（不是拒绝）
    chat_start = int(chat_start)
    keys = {b["seq"]: int(b.get("key", 0)) for b in blocks}
    gaps = {b["seq"]: int(b["gap"]) for b in blocks if "gap" in b}
    n_ctx = int(budget["n_ctx"])
    bpt = int(budget.get("bytes_per_token", BPT_DEFAULT))
    pool = int(budget.get("pool_bytes", n_ctx * bpt))
    full_budget = {"n_ctx": n_ctx, "chat_len": int(budget["chat_len"]),
                   "bytes_per_token": bpt, "pool_bytes": pool}
    out = _PL.plan(blocks, chat_start, full_budget, keys=keys, gaps=gaps or None)
    for e in out:
        _PL.check_entry(e)               # 结构不变式：base + cells - 1 == pos_hi
    return out


def target_pos_of(entry):
    """`target_pos` 就是 `pos_hi` —— 只此一个定义，防止再出现「一个词指两样东西」。"""
    return entry["pos_hi"]


def describe(placements, chat_start):
    """纯读数（不判定）：每块到对话的距离 + 是否紧贴。给调用方与单测共用。"""
    return [{"seq": e["seq"], "base": e["base"], "pos_hi": e["pos_hi"], "cells": e["cells"],
             "distance": int(chat_start) - e["pos_hi"]} for e in placements]