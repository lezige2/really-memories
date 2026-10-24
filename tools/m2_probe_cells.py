# -*- coding: utf-8 -*-
"""m2_probe_cells.py -- is the 4th shared segment actually in the cache?

ask() is not evidence: a wrong answer can come from bad cells or from a model that goes
off-format with four statements in context. So this probe reads the cache directly, and
then runs the control experiment (the same four statements as ordinary tokens).

Per segment count:
  1..4, report expected cells, scanned cells, pos_max_raw, per-segment bit coverage,
  and segment overlap.
"""
import ctypes
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import kvslots as K                                          # noqa: E402

MODEL = os.path.join(r"D:\models", "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf")
D = os.path.join(ROOT, "kvmem", "m2_v1")
CHAT, SLOT, LIVE, PROBE = 4096, 64, 0, 7
ORDER = ["home", "project", "habit", "car"]
TEXT = {
    "home": "我住在广陵路 12 号 2 单元 602。",
    "project": "项目代号蓝鲸，计划 3 月 14 日上线。",
    "habit": "我的咖啡只喝美式，不加糖。",
    "car": "我的车牌是 浙B-3F19K，深灰色速腾。",
}
Q, FACT = "我住在哪？", "广陵路"


def main():
    eng = K.KVEngine(MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    lib, h = eng.lib, eng.h
    lib.kvshim_seq_pos_max_raw.restype = ctypes.c_int
    lib.kvshim_seq_pos_max_raw.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.kvshim_seq_cell_scan.restype = ctypes.c_int
    lib.kvshim_seq_cell_scan.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                         ctypes.POINTER(ctypes.c_int), ctypes.c_int]

    def scan(seq, cap=4096):
        buf = (ctypes.c_int * cap)()
        n = lib.kvshim_seq_cell_scan(h, seq, PROBE, buf, cap)
        return n, [buf[i] for i in range(max(n, 0))]

    def raw(seq):
        return lib.kvshim_seq_pos_max_raw(h, seq)

    try:
        print("%-4s %-6s %-6s %-8s %-6s %s" % ("k", "cells", "expect", "pos_max", "segs",
                                               "segments [lo,hi) covered/expected"))
        for k in range(1, 5):
            for s in range(8):
                eng.reset(s)
            segs = []
            for i, bid in enumerate(ORDER[:k], start=1):
                eng.reset(i)
                n = eng.load_strict(i, os.path.join(D, bid + ".kvmem"))
                tgt = CHAT - (i - 1) * SLOT - n
                eng.repos_local(i, tgt - (eng.pos_max(i) - n + 1))
                segs.append((bid, tgt, tgt + n))
            for i, (bid, lo, hi) in enumerate(segs, start=1):
                eng.share(i, LIVE, lo, hi)

            cnt, pos = scan(LIVE)
            pset = set(pos)
            expect = sum(hi - lo for _b, lo, hi in segs)
            desc = []
            for bid, lo, hi in segs:
                have = sum(1 for p in range(lo, hi) if p in pset)
                desc.append("%s[%d,%d)=%d/%d" % (bid, lo, hi, have, hi - lo))
            overlap = any(a_hi > b_lo for (_x, _a, a_hi), (_y, b_lo, _z)
                          in zip(segs, segs[1:]))
            print("%-4d %-6d %-6d %-8d %-6d %s%s"
                  % (k, cnt, expect, raw(LIVE), len(segs), " ".join(desc),
                     "  OVERLAP" if overlap else ""))

        # ---- control: the same statements as plain tokens (no seq_cp at all)
        print("\ncontrol (text in context, no shared cells):")
        for k in range(1, 5):
            eng.reset(LIVE)
            pos = 0
            for bid in ORDER[:k]:
                eng.write_at(LIVE, TEXT[bid], pos, add_bos=(pos == 0))
                pos = eng.pos_max(LIVE) + 1
            ans = eng.ask(LIVE, Q, n_predict=16, pos=pos)
            print("  k=%d -> %s %r" % (k, "OK" if FACT in ans else "MISS", ans.strip()[:30]))
        return 0
    finally:
        eng.close()


if __name__ == "__main__":
    sys.exit(main())