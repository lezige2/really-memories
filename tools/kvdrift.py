# -*- coding: utf-8 -*-
"""kvdrift.py -- does repeated repositioning erode the KV that is NOT being moved?

Section 6.6 measured one rope shift: the answer was bit-identical, but build_graph_shift
rewrites the WHOLE K tensor (dequant -> rope -> requant), so every resident sequence is
re-quantised each time any block is moved. A single shift is harmless. The question is
whether a *long-lived* sequence survives many of them.

This matters because the per-turn path is: reload the block from disk (pristine), shift
it into place, share it, ask. The block itself therefore never accumulates drift across
turns -- but the chat sequence stays resident, and it is the chat that gets re-quantised
on every swap.

Method: keep one chat with three facts, ask it, then perform N block placements and ask
the same chat again. If the answers stay identical, drift is below the decision margin at
that N; if they decay, the architecture needs f16 KV or a periodic reload of the chat.

Usage:
    python tools/kvdrift.py --n 100 --checkpoints 0,25,50,100
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kvslots import KVEngine, turn, first_line  # noqa: E402


CHAT = (
    "我叫林知远，工号是 A-4417。\n"
    "我养的猫叫年糕。\n"
    "我每周三下午两点在 B 栋 3 层 302 会议室开例会。\n"
)
QUESTIONS = [
    ("我的工号是多少？", "A-4417"),
    ("我养的猫叫什么名字？", "年糕"),
    ("我的例会在哪个会议室？", "302"),
]

# A throwaway block that gets placed and re-placed. Its content is irrelevant; only
# the fact that placing it triggers a full-cache rope shift matters.
BLOCK = "这是一段用于触发位置重排的占位记忆，内容与问题无关。" * 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=r"D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf")
    ap.add_argument("--ctx", type=int, default=8192)
    ap.add_argument("--gpu", type=int, default=99)
    ap.add_argument("--kv", default="q8_0", choices=["q8_0", "f16"])
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--checkpoints", default="0,25,50,100")
    ap.add_argument("--shift", type=int, default=1000)
    ap.add_argument("--reload", action="store_true",
                    help="load the block from disk each placement (the real per-turn path) "
                         "instead of re-encoding it")
    ap.add_argument("--local", action="store_true",
                    help="use seq_repos_local (rotate only the moved cells) instead of "
                         "seq_add (pending whole-tensor K-shift)")
    args = ap.parse_args()

    marks = sorted({int(x) for x in args.checkpoints.split(",") if x.strip()})
    marks = [m for m in marks if m <= args.n]

    eng = KVEngine(args.model, n_ctx=args.ctx, n_seq=8, gpu=args.gpu, kv=args.kv)
    print("ctx=%d  kv=%s  can_shift=%s  per-token=%d B"
          % (eng.n_ctx, args.kv, eng.can_shift(), eng.bytes_per_token()))

    chat, blk, scratch = 0, 1, 2
    hold = 3                                # never asked; a pure drift witness
    eng.write_at(chat, CHAT, 0)
    eng.write_at(hold, CHAT, 5000)
    print("chat: %d tokens, %d B KV" % (eng.n_tokens(chat), eng.seq_bytes(chat)))
    print("hold: %d tokens at pos 5000..%d (never queried, only re-quantised by shifts)"
          % (eng.n_tokens(hold), eng.pos_max(hold)))
    print()

    hold_a = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quality", "hold_n0.kvmem")
    hold_b = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quality", "hold_n%d.kvmem" % args.n)
    eng.save(hold, hold_a)

    def ask_all(tag):
        outs = []
        for q, expect in QUESTIONS:
            a = eng.ask(chat, q, 20)
            ok = expect in a
            outs.append((q, expect, a, ok))
        hit = sum(1 for o in outs if o[3])
        print("%-10s chat=%3d tok | %d/%d correct" % (tag, eng.n_tokens(chat), hit, len(outs)))
        for q, expect, a, ok in outs:
            print("    %s %-18s -> %s" % ("OK  " if ok else "MISS", q, first_line(a)))
        return outs

    base = ask_all("baseline")
    print()

    blk_path = None
    if args.reload:
        eng.reset(blk)
        eng.write_at(blk, BLOCK, 0)
        blk_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quality", "drift_blk.kvmem")
        nb = eng.save(blk, blk_path)
        print("block saved once: %s (%d B)" % (os.path.basename(blk_path), nb))
        print("each placement = load + shift + flush (no re-encoding)\n")

    print("mode: %s%s" % ("seq_repos_local" if args.local else "seq_add (whole-tensor K-shift)",
                          "" if args.local else " + flush decode"))
    if args.local:
        eng.reset(blk)
        eng.load(blk, blk_path)
        n0 = eng.n_tokens(blk)
        moved = eng.repos_local(blk, args.shift)
        print("sanity: %d token block, repos_local(+%d) moved %d cells -> pos %d..%d"
              % (n0, args.shift, moved, args.shift, eng.pos_max(blk)))
        eng.reset(blk)
    print()

    t_all = time.perf_counter()
    done = 0
    for m in marks:
        if m <= done:
            continue
        while done < m:
            eng.reset(blk)
            if blk_path:
                eng.load(blk, blk_path)
            else:
                eng.write_at(blk, BLOCK, 0)
            if args.local:
                # completes synchronously: no pending shift, so no flush decode
                eng.repos_local(blk, args.shift)
            else:
                eng.repos(blk, args.shift)          # pending shift
                eng.reset(scratch)
                eng.write(scratch, "。")            # this decode applies the shift
            done += 1
        dt = time.perf_counter() - t_all
        print("--- after %d placements (%.1f s total, %.0f ms each)"
              % (done, dt, dt * 1000.0 / done))
        cur = ask_all("N=%d" % done)
        if cur != base and all(o[3] for o in cur):
            print("    (answers differ but still correct)")
        print()

    dt = time.perf_counter() - t_all
    print("total %.1f s for %d placements = %.0f ms/placement" % (dt, args.n, dt * 1000.0 / args.n))

    # Numeric drift: the hold sequence was never asked anything, so its token list and
    # positions are identical in both snapshots. Every differing byte is requantisation
    # noise injected by build_graph_shift rewriting the whole K tensor.
    eng.save(hold, hold_b)
    with open(hold_a, "rb") as f1, open(hold_b, "rb") as f2:
        b1, b2 = f1.read(), f2.read()
    if len(b1) == len(b2):
        diff = sum(1 for x, y in zip(b1, b2) if x != y)
        print("hold state: %d B, %d differing after %d shifts (%.2f%%)"
              % (len(b1), diff, args.n, 100.0 * diff / len(b1)))
    else:
        print("hold state length changed: %d -> %d (unexpected)" % (len(b1), len(b2)))

    eng.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())