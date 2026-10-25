"""六种故意写错的 planner + 一种"位置对但字节错"的错法。

每个 fake 只为一件事存在：**让某一条断言必须红**。红不了，说明那条断言是假的。
用法：red_suite.py 逐个跑，判定"该红的红了、不该红的没红"。
"""


class PlanRefused(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _place_far_to_near(blocks, chat_start, keys):
    """正确骨架：最相关紧贴对话，其余按 (distance_key, seq) 由近到远外排；返回先远后近的放置序。"""
    most = min(blocks, key=lambda b: (keys[b["seq"]], b["seq"]))
    rest = [b for b in blocks if b["seq"] != most["seq"]]
    rest.sort(key=lambda b: (keys[b["seq"]], b["seq"]))
    out = []
    cursor = chat_start - 1
    for b in [most] + rest:
        pos_hi = cursor
        out.append((b["seq"], pos_hi))
        cursor = pos_hi - b["cells"]
    return out


# ---------- 正确版（供对照，不属于 fake）----------
def correct(blocks, chat_start, keys, budget):
    _check(blocks, chat_start, budget)
    plan = _place_far_to_near(blocks, chat_start, keys)
    return list(reversed(plan))          # 先远后近


def _check(blocks, chat_start, budget):
    cells = sum(b["cells"] for b in blocks)
    if cells + budget["chat_len"] > budget["n_ctx"]:
        raise PlanRefused("n_ctx")
    if cells * budget["bytes_per_token"] > budget["pool_bytes"]:
        raise PlanRefused("pool_bytes")


# ---------- P1: 几何错（两块重叠）----------
def fake_overlap(blocks, chat_start, keys, budget):
    plan = _place_far_to_near(blocks, chat_start, keys)
    if len(plan) >= 2:
        plan[1] = (plan[1][0], plan[0][1])        # 第二块压在第一块上
    return list(reversed(plan))


# ---------- P2: 无视预算 ----------
def fake_ignore_budget(blocks, chat_start, keys, budget):
    return list(reversed(_place_far_to_near(blocks, chat_start, keys)))


# ---------- P3: 锚点差一位（单调仍成立）----------
def fake_anchor_off_by_one(blocks, chat_start, keys, budget):
    """最相关块放在 chat_start-2：整体外移一位，S3b 单调仍成立，只有 S3a 会红。"""
    _check(blocks, chat_start, budget)
    most = min(blocks, key=lambda b: (keys[b["seq"]], b["seq"]))
    rest = sorted([b for b in blocks if b["seq"] != most["seq"]],
                  key=lambda b: (keys[b["seq"]], b["seq"]))
    out, cursor = [], chat_start - 2          # <-- 差一位
    for b in [most] + rest:
        out.append((b["seq"], cursor))
        cursor -= b["cells"]
    return list(reversed(out))


# ---------- P4: tie-break 反了 ----------
def fake_tie_reversed(blocks, chat_start, keys, budget):
    _check(blocks, chat_start, budget)
    most = min(blocks, key=lambda b: (keys[b["seq"]], b["seq"]))
    rest = [b for b in blocks if b["seq"] != most["seq"]]
    rest.sort(key=lambda b: (keys[b["seq"]], -b["seq"]))     # 同 key 时反向
    out, cursor = [], chat_start - 1
    for b in [most] + rest:
        out.append((b["seq"], cursor))
        cursor -= b["cells"]
    return list(reversed(out))


# ---------- P5: 插入时先移对话、后摘引用（L7 陷阱 2）----------
def fake_insert_no_drop(sim, new_cells):
    """返回 (ok, detail)。错误做法：先 move_chat(blocks_dropped=False)。"""
    sim.move_chat(new_cells, blocks_dropped=False)
    return True, {"order": "move_chat BEFORE drop"}


def correct_insert(sim, new_cells):
    sim.move_chat(new_cells, blocks_dropped=True)
    return True, {"order": "drop THEN move_chat"}


# ---------- P6: 放不下不抛，返回空表 ----------
def fake_refuse_empty(blocks, chat_start, keys, budget):
    cells = sum(b["cells"] for b in blocks)
    if cells + budget["chat_len"] > budget["n_ctx"]:
        return []
    return list(reversed(_place_far_to_near(blocks, chat_start, keys)))


# ---------- P7: 位置全对，但对未参与块多转一次（S5 专用）----------
def fake_double_rotate(sim, involved):
    for seq, b in sim.blocks.items():
        if seq in involved:
            continue
        b["rot"] += 2          # 位置逐位不变，字节必变
    return True, {"rotated_extra": [s for s in sim.blocks if s not in involved]}


# ---------- P8: 池字节不够但 n_ctx 够 —— 无拒绝义务，只有 S2 该红 ----------
def fake_over_pool_no_refusal(blocks, chat_start, keys, budget):
    """n_ctx 档检查、pool 档不看：返回越界方案（S2 红），而 S6 不参与（不是 n_ctx 场景）。"""
    if sum(b["cells"] for b in blocks) + budget["chat_len"] > budget["n_ctx"]:
        raise PlanRefused("n_ctx")
    return list(reversed(_place_far_to_near(blocks, chat_start, keys)))
