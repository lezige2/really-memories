# -*- coding: utf-8 -*-
"""One-off: does the block have to sit ADJACENT to the ask position?

M2 placed blocks at [4045,4096) with the question at 4096. m4_write encoded at position 0
(L6) and then asked at 4096 -- a 4005-position gap -- and got an empty answer.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "kvmem", "m2_visibility", "m2"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "engine"), HERE):
    sys.path.insert(0, p)
import m2_visibility_probe as P
import _driver_m2 as M2
import _driver2 as D2

BLK = os.path.join(HERE, "blocks", "blk_conv_2026-10-25_01.kvmem")
Q = "我住在哪？"
ANCHOR = 4096

eng = P.open_engine()
try:
    n = eng.load_strict(1, BLK)
    print("loaded cells=%d pos_max_raw=%s" % (n, P.raw_pos_max(eng, 1)), flush=True)
    base = eng.pos_max(1) - n + 1
    print("saved base position = %d" % base, flush=True)

    # (a) as saved, at [0, 91) -- the 4005 gap case
    eng.share(1, 0, base, base + n)
    print("A) block at [%d,%d) live_cells=%d" % (base, base + n, P.cell_scan(eng, 0)[0]), flush=True)
    rc, ans = D2.ask_native(eng, 0, Q, ANCHOR, P.N_PREDICT)
    print("A) rc=%d answer=%r" % (rc, ans.strip()[:80]), flush=True)
    eng.drop(0, base, base + n)

    # (b) repositioned so it ends exactly at ANCHOR, like M2
    eng.repos_local(1, ANCHOR - n - base)
    lo, hi = ANCHOR - n, ANCHOR
    print("B) block moved to [%d,%d) pos_max_raw=%s" % (lo, hi, P.raw_pos_max(eng, 1)), flush=True)
    eng.share(1, 0, lo, hi)
    print("B) live_cells=%d" % P.cell_scan(eng, 0)[0], flush=True)
    rc2, ans2 = D2.ask_native(eng, 0, Q, ANCHOR, P.N_PREDICT)
    print("B) rc=%d answer=%r" % (rc2, ans2.strip()[:120]), flush=True)
    print("B) hit=%s" % ("广陵路 12 号 2 单元 602" in ans2), flush=True)
    print("B) file sha unchanged:", __import__("hashlib").sha256(open(BLK, "rb").read()).hexdigest()[:16], flush=True)
finally:
    eng.close()
