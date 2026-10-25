"""最小确定性 KV 模拟器：只模拟 M2 需要的三个量 —— 位置、重转次数、字节哈希。

字节哈希 = sha16("seq|pos_lo|rot")。这不是真 KV 字节，它是**受控替身**：
  · 位置相同 + 重转次数相同  => 哈希相同（对应真实产物里跨布局 pre/post sha16 相等）
  · 位置相同 + 重转次数不同  => 哈希不同（对应 requant 有损：约 48% 字节取值改变）
  · 位置不同                 => 哈希不同
这样 S5（字节）与 S4（位置）才能分别被触发，而不是互相顶替。
"""
import hashlib


def h(seq, pos_lo, rot):
    return hashlib.sha256(("%d|%d|%d" % (seq, pos_lo, rot)).encode()).hexdigest()[:16]


class Sim:
    def __init__(self, n_ctx=8192, bytes_per_token=104448, pool_bytes=855638016):
        self.n_ctx = n_ctx
        self.bytes_per_token = bytes_per_token
        self.pool_bytes = pool_bytes
        self.blocks = {}          # seq -> dict(cells, pos_lo, rot)
        self.chat = None          # dict(pos_lo, len)
        self.visible_positions = {}   # seq -> set(pos)

    # --- 块 ---
    def add_block(self, seq, cells, pos_lo):
        self.blocks[seq] = {"cells": cells, "pos_lo": pos_lo, "rot": 0}

    def rotate(self, seq, delta):
        b = self.blocks[seq]
        b["pos_lo"] += delta
        b["rot"] += 1
        return b["cells"]

    def pos_hi(self, seq):
        b = self.blocks[seq]
        return b["pos_lo"] + b["cells"] - 1

    def block_hash(self, seq):
        b = self.blocks[seq]
        return h(seq, b["pos_lo"], b["rot"])

    # --- 对话 ---
    def set_chat(self, pos_lo, length):
        self.chat = {"pos_lo": pos_lo, "len": length}

    def chat_start(self):
        return self.chat["pos_lo"]

    def move_chat(self, delta, blocks_dropped):
        """delta>0: 对话上移。blocks_dropped=False 时，块跟着一起被拖走（L7 陷阱 2）。"""
        self.chat["pos_lo"] += delta
        if not blocks_dropped:
            for b in self.blocks.values():
                b["pos_lo"] += delta   # 被拖走：位置变了，但没有重转（rot 不变）


    # --- 可见性（供 apply_insert 读回验证）---
    def visible(self, seq, lo, hi):
        return any(lo <= p < hi for p in self.visible_positions.get(seq, set()))

    def mark_visible(self, seq, lo, hi):
        self.visible_positions.setdefault(seq, set()).update(range(lo, hi))

    def unmark_visible(self, seq, lo, hi):
        for p in range(lo, hi):
            self.visible_positions.get(seq, set()).discard(p)

    def drop(self, seq, lo, hi):
        self.unmark_visible(seq, lo, hi)
        return None

    def share(self, src, dst, lo, hi):
        self.mark_visible(dst, lo, hi)

    def repos_local(self, seq, delta, lo, hi):
        """返回 moved。bug 版由子类覆盖成 0（模拟「全 ok 但没动」）。"""
        ps = self.visible_positions.get(seq, set())
        moving = {p for p in ps if lo <= p < hi}
        ps -= moving
        ps |= {p + delta for p in moving}
        self.visible_positions[seq] = ps
        return len(moving)


class SimNoEffect(Sim):
    """假绿的教科书形态：每步都返回成功，但**什么都没生效**（moved 恒 0、可见性不变）。"""

    def repos_local(self, seq, delta, lo, hi):
        return 0

    def drop(self, seq, lo, hi):
        return None

    def share(self, src, dst, lo, hi):
        return None
