# -*- coding: utf-8 -*-
"""hole_probe.py -- what actually happens when the chat head is not adjacent.

hole_matrix showed that a gap between the last block and the chat destroys generation
even when the gap is owned by another sequence -- so "hole" is not the variable. The
suspicion is that decoding a token whose position is not `pos_max+1` makes the KV cache
shift the whole sequence, and that shifting a cell which is shared with a block
sequence desynchronises the block.

This prints pos_max per sequence before and after each step, which is the cheapest way
to see whether anything moved.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import memory_source as ms          # noqa: E402
import chat as demo                 # noqa: E402
from kvslots import KVEngine        # noqa: E402

ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "kvmem", "p0_4.db")
BLOCKS = os.path.join(ROOT, "kvmem", "p0_4_blocks")
CHAT = 4096


def state(eng, tag):
    print("  %-26s pos_max: live=%s a=%s b=%s   n_tokens: live=%s a=%s b=%s"
          % (tag, eng.pos_max(0), eng.pos_max(4), eng.pos_max(5),
             eng.n_tokens(0), eng.n_tokens(4), eng.n_tokens(5)))


def place(eng, row, target, seq):
    eng.reset(seq)
    n = ms.load_into(eng, row, seq)
    base = eng.pos_max(seq) - n + 1
    if base != target:
        eng.repos_local(seq, target - base)
    eng.share(seq, 0, target, target + n)
    print("  place %-8s seq=%d n=%d -> [%d,%d)" % (row[1], seq, n, target, target + n))


def main():
    con = ms.connect(DB)
    eng = KVEngine(ms.MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    try:
        rows = {r[1]: r for r in ms.block_rows(con) if r[5] is not None}
        pn, jn = rows["profile"][7], rows["project"][7]
        for s in range(8):
            eng.reset(s)

        print("A) chat_head, gap of 8 left EMPTY (blocks end at %d)" % (CHAT - 8))
        place(eng, rows["profile"], CHAT - 8 - pn - jn, 4)
        place(eng, rows["project"], CHAT - 8 - jn, 5)
        state(eng, "before asking")
        a = eng.ask(0, "我的工号是多少？", n_predict=8, pos=CHAT)
        state(eng, "after asking at 4096")
        print("  answer=%r" % (a[:60],))

        print("\nB) control: same blocks, no gap (they end at %d)" % CHAT)
        for s in range(8):
            eng.reset(s)
        place(eng, rows["profile"], CHAT - pn - jn, 4)
        place(eng, rows["project"], CHAT - jn, 5)
        state(eng, "before asking")
        a = eng.ask(0, "我的工号是多少？", n_predict=8, pos=CHAT)
        state(eng, "after asking at 4096")
        print("  answer=%r" % (a[:60],))

        print("\nC) asking at pos_max+1 instead of the pinned 4096")
        for s in range(8):
            eng.reset(s)
        place(eng, rows["profile"], CHAT - 8 - pn - jn, 4)
        place(eng, rows["project"], CHAT - 8 - jn, 5)
        a = eng.ask(0, "我的工号是多少？", n_predict=8, pos=eng.pos_max(0) + 1)
        state(eng, "after asking at pos_max+1")
        print("  answer=%r" % (a[:60],))
        print("\nD) chat_head, gap owned by seq 3 AND shared into seq 0 (contiguous)")
        for s in range(8):
            eng.reset(s)
        place(eng, rows["profile"], CHAT - 8 - pn - jn, 4)
        place(eng, rows["project"], CHAT - 8 - jn, 5)
        eng.reset(3)
        eng.write_at(3, "填" * 7, CHAT - 8)          # BOS + 7 chars covers [4088,4096)
        print("  filler n=%d pos_max=%d" % (eng.n_tokens(3), eng.pos_max(3)))
        eng.share(3, 0, CHAT - 8, CHAT)              # <- the difference from case A
        state(eng, "before asking")
        a = eng.ask(0, "我的工号是多少？", n_predict=8, pos=CHAT)
        state(eng, "after asking at 4096")
        print("  answer=%r" % (a[:60],))

        print("\nE) chat_head, gap shared *partially* (1 cell short)")
        for s in range(8):
            eng.reset(s)
        place(eng, rows["profile"], CHAT - 8 - pn - jn, 4)
        place(eng, rows["project"], CHAT - 8 - jn, 5)
        eng.reset(3)
        eng.write_at(3, "填" * 7, CHAT - 8)
        eng.share(3, 0, CHAT - 8, CHAT - 1)          # leave [4095,4096) invisible
        a = eng.ask(0, "我的工号是多少？", n_predict=8, pos=CHAT)
        state(eng, "after asking at 4096")
        print("  answer=%r" % (a[:60],))
    finally:
        eng.close()
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())