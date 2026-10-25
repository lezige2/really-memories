"""M2 放置规划器（最小实现）：预算 + 顺序 + 中途插入。

定性核心：**给一个有损操作定最少调用次数** —— 每块只做一次 repos_local，先远后近。
（依据：每次重转约改写 48% 字节取值，见字段 own_repos_rewrite.ratio）
"""


class PlanRefused(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class PlanInvariant(Exception):
    pass


def plan(blocks, chat_start, budget, keys=None, gaps=None):
    """blocks: [{seq, cells, key?}]；keys: {seq: distance_key}（越小越相关）。
    gaps: {seq: 该块下方额外留空}（默认 0，用于复现冻结几何）。
    返回 [{seq, base, pos_hi, cells}]，**先远后近**排列。
    **两个位置都给**：base 是 repos_local 的摆放基点（delta 只接受 base），pos_hi 是最大占用位。
    一个词指两样东西（target）是上一版的风险源 —— 换算 base = pos_hi - cells + 1 不再留给调用方。
    """
    if not blocks:
        return []
    keys = dict(keys or {b["seq"]: b.get("key", 0) for b in blocks})
    gaps = dict(gaps or {})
    cells = sum(int(b["cells"]) for b in blocks)
    chat_len = int(budget["chat_len"])
    if cells + chat_len > budget["n_ctx"]:
        raise PlanRefused("n_ctx")
    if cells * int(budget["bytes_per_token"]) > int(budget["pool_bytes"]):
        raise PlanRefused("pool_bytes")

    order = sorted(blocks, key=lambda b: (keys[b["seq"]], b["seq"]))     # 相关度升序，tie-break seq
    cursor = chat_start - 1
    placement = []
    for b in order:
        cells = int(b["cells"])
        pos_hi = cursor
        base = pos_hi - cells + 1
        if base < 0:
            raise PlanInvariant("block %r does not fit below chat" % b["seq"])
        if base + cells - 1 != pos_hi:                    # 结构不变式
            raise PlanInvariant("base/pos_hi inconsistent for %r" % b["seq"])
        placement.append({"seq": b["seq"], "base": base, "pos_hi": pos_hi, "cells": cells})
        cursor = base - 1 - int(gaps.get(b["seq"], 0))
    return list(reversed(placement))          # 先远后近


def delta_for(entry):
    """repos_local 的 delta **只接受 base**：块文件里 pos 是 0..cells-1。"""
    if "base" not in entry:
        raise PlanInvariant("delta_for 只接受含 base 的条目（不接受 pos_hi / target_pos）")
    return entry["base"]


def check_entry(entry):
    """结构不变式：base + cells - 1 == pos_hi。绿套件必跑。"""
    if entry["base"] + entry["cells"] - 1 != entry["pos_hi"]:
        raise PlanInvariant("base+cells-1 != pos_hi: %r" % entry)
    return True


def insert_ops(chat_seq, block_seqs, block_ranges, new_cells):
    """中途插入的四步，写成有序操作（可在无 GPU 环境下断言顺序）。

    §2.3 原文：先 seq_rm 摘引用 -> 移动对话 -> 新块落到空出的区间 -> 全部重新 seq_cp。
    **顺序不许调换**：先移对话会把块一起拖走（L7 陷阱 2），S4/P5 已用假 planner 证明能被抓到。
    """
    if not block_ranges:
        raise PlanInvariant("no block range to detach")
    ops = [("drop", chat_seq, min(lo for lo, _ in block_ranges), max(hi for _, hi in block_ranges))]
    ops.append(("repos_local", chat_seq, +new_cells))
    ops.append(("repos_new_block", chat_seq, new_cells))
    for lo, hi in block_ranges:
        ops.append(("share", chat_seq, lo, hi))
    return ops


def apply_insert(eng, chat_seq, block_ranges, chat_range, new_cells, cells_of,
                 new_block=None, reshares=None, new_block_prepare=None, readback=None):
    """执行四步，并**逐步读回验证**。

    「操作成功」!＝「操作生效」；**返回码不算证据，读回状态才算**。
    eng 须提供：drop(seq,lo,hi) / repos_local(seq,delta,lo,hi)->moved / share(src,dst,lo,hi)
                / visible(seq,lo,hi)->bool（读回）
    cells_of(seq) -> 该 seq 的 cell 数（校验 repos_local 的 moved）
    new_block=(src, lo, hi)      -- 新块
    reshares=[(src, lo, hi), ...] -- 既有块的重新挂回
    readback: 可选的第二读数通道（**必须机制独立**，见 FIELDS.md）：
              readback.n_tokens(seq)->int（计数层，统计写入的 token，不依赖位置扫描）
              readback.raw_pos_max(seq)->int（位置层）
    """
    log = []
    # 必须在任何 drop 之前取总数：drop 之后 cells_of(chat_seq) 已经不含块引用
    chat_lo, chat_hi = chat_range
    n_chat = int(cells_of(chat_seq)) - sum(hi - lo for lo, hi in block_ranges)

    def _readback_visible(seq, lo, hi):
        """读回可见性 —— 不问引擎「成功了吗」，只问「现在看得见吗」。"""
        return bool(eng.visible(seq, lo, hi))

    # 1) 摘引用：读回必须不可见
    for lo, hi in block_ranges:
        eng.drop(chat_seq, lo, hi)
        visible_after_drop = _readback_visible(chat_seq, lo, hi)
        if visible_after_drop:
            raise PlanInvariant("drop 未生效（读回仍可见）: [%d,%d)" % (lo, hi))
        log.append({"op": "drop", "range": [lo, hi], "readback_visible": False, "verified": True})

    # 2) 移动对话：moved 必须 == 对话实际 cell 数（n_chat 在 drop 之前已取，见上）
    nt0 = readback.n_tokens(chat_seq) if readback is not None else None
    rp0 = readback.raw_pos_max(chat_seq) if readback is not None else None
    moved = int(eng.repos_local(chat_seq, new_cells, chat_lo, chat_hi))
    layers = {}
    if readback is not None:
        nt1 = readback.n_tokens(chat_seq)
        rp1 = readback.raw_pos_max(chat_seq)
        layers = {"L1_position_delta": rp1 - rp0, "L2_n_tokens_unchanged": nt1 == nt0,
                  "layers_used": 2,
                  "rule": "两个读数必须机制独立：不能是同一通道的两次调用、也不能是同一底层计算的两种包装；"
                          "且『移动不改 token 个数』——若个数也变了，说明那一步不是单纯移动"} 
        if (rp1 - rp0) != new_cells:
            raise PlanInvariant("位置层不符: raw_pos_max 增量 %d != new_cells %d" % (rp1 - rp0, new_cells))
        if nt1 != nt0:
            raise PlanInvariant("计数层不符: 移动后 n_tokens %d -> %d（移动不该改变个数）" % (nt0, nt1))
    moved_ok = (moved == n_chat)                      # moved == 期望 cell 数
    if not moved_ok:
        raise PlanInvariant("repos_local 生效不足: moved %d != 对话 cell 数 %d" % (moved, n_chat))
    log.append({"op": "repos_local", "delta": new_cells, "readback_layers": layers, "cells_moved": moved,
                "expected_cells_moved": n_chat, "cells_moved_ok": moved_ok,
                "naming": ("delta=位移(=%d)；cells_moved=被移动的 cell 数(=%d)。两件事，不许同名。"
                           % (new_cells, moved))})

    # 3) 新块：读回必须可见
    if new_block is not None:
        if new_block_prepare is not None:
            new_block_prepare()          # 新块必须在对话让位之后再落位（否则与旧对话位置冲突）
        src, lo, hi = new_block
        eng.share(src, chat_seq, lo, hi)
        visible_new = _readback_visible(chat_seq, lo, hi)
        if not visible_new:
            raise PlanInvariant("新块 share 未生效（读回不可见）: [%d,%d)" % (lo, hi))
        log.append({"op": "share_new", "range": [lo, hi], "readback_visible": True, "verified": True})

    # 4) 重新挂回既有块：读回必须可见
    for src, lo, hi in (reshares or []):
        eng.share(src, chat_seq, lo, hi)
        visible_back = _readback_visible(chat_seq, lo, hi)
        if not visible_back:
            raise PlanInvariant("重新 share 未生效（读回不可见）: [%d,%d)" % (lo, hi))
        log.append({"op": "share_existing", "range": [lo, hi], "readback_visible": True, "verified": True})

    verify_effects(log)
    return log


def verify_effects(log):
    """总闸：任何一步没有 readback 证据，视为未验证（返回码不算证据）。"""
    for rec in log:
        if rec["op"] == "repos_local":
            if not rec.get("cells_moved_ok"):
                raise PlanInvariant("repos_local 未生效: %r" % rec)
        elif rec["op"] == "drop":
            if rec.get("readback_visible") is not False:      # drop 的读回必须是"看不见"
                raise PlanInvariant("drop 缺 readback 证据: %r" % rec)
        else:                                                 # share 的读回必须是"看得见"
            if rec.get("readback_visible") is not True:
                raise PlanInvariant("share 缺 readback 证据: %r" % rec)
    return True


def check_ops(ops):
    """顺序不变量：drop 必须早于任何 repos_local(chat)。"""
    seen_drop = False
    for op in ops:
        if op[0] == "drop":
            seen_drop = True
        elif op[0] == "repos_local" and not seen_drop:
            raise PlanInvariant("repos_local(chat) 出现在 drop 之前 —— L7 陷阱 2")
    return True
