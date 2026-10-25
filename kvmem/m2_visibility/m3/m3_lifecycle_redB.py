# -*- coding: utf-8 -*-
"""红控 B（M3-PREREG §8）—— 把 reset(LIVE) 换成【含块的全局重置】，轮首必须读到块 0 格 => I3。

预期这条路红在【无效轮】（驱动坏了），不是【未通过】（块泄漏）。混掉就分不清两者。
本文件单独存在是刻意的：驱动 m3_lifecycle_50.py 里那个调用的 token 必须出现 0 次，
所以含块重置只允许活在这个 red control 里。

  python -u -X utf8 kvmem/m2_visibility/m3/m3_lifecycle_redB.py
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "kvmem", "m2_visibility", "m2"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "engine"), HERE):
    sys.path.insert(0, p)
import m2_visibility_probe as P                                    # noqa: E402
import _driver_m2 as M2                                           # noqa: E402
import m3_lease as L                                              # noqa: E402

BLOCK_FILE = os.path.join(ROOT, "kvmem", "m2_visibility", "m4", "blocks",
                          "blk_conv_2026-10-25_01.kvmem")
BLOCK_SEQ = 1
POS_HI = P.CHAT
N_BLOCK = 91
OUT = os.path.join(HERE, "run_m3_redB.json")
PREREG = os.path.join(ROOT, "kvmem", "m2_visibility", "mine", "inspector", "M3-PREREG.md")


def main():
    t0 = time.time()
    res = {"schema": "m3_redB_v1", "pid": os.getpid(),
           "prereg": {"path": "kvmem/m2_visibility/mine/inspector/M3-PREREG.md",
                      "sha16": hashlib.sha256(open(PREREG, "rb").read()).hexdigest()[:16],
                      "lines": len(open(PREREG, encoding="utf-8").read().splitlines()),
                      "newline": ("CRLF" if open(PREREG, "rb").read().count(bytes([13, 10]))
                                  else "LF")},
           "aim":
           "show that a block-inclusive global reset makes the round-start reading 0 cells, "
           "so I3 fires as an INVALID ROUND (not as 未通过)",
           "path": [], "verdict": None}
    eng = P.open_engine()
    eng.reset(BLOCK_SEQ)
    n = eng.load_strict(BLOCK_SEQ, BLOCK_FILE)
    base = eng.pos_max(BLOCK_SEQ) - n + 1
    pos_lo = POS_HI - n
    eng.repos_local(BLOCK_SEQ, pos_lo - base)
    res["setup"] = {"loaded_cells": n, "pos_lo": pos_lo, "pos_hi": POS_HI,
                    "pos_max": eng.pos_max(BLOCK_SEQ)}
    leases = L.BlockLeases(eng)
    leases.register_block(BLOCK_SEQ, "blk_conv_2026-10-25_01")
    eng.reset(P.LIVE)
    res["path"].append({"step": "baseline round start", "block_cells": eng.n_tokens(BLOCK_SEQ),
                        "i3_fires": eng.n_tokens(BLOCK_SEQ) != N_BLOCK})

    # the substitution under test: a "safe" global reset that includes the block sequence
    try:
        r = leases.safe_reset_all(range(P.N_SEQ))
        res["safe_reset_all_return"] = r if isinstance(r, (int, str, dict, list)) else repr(r)
        res["safe_reset_all_raised"] = None
    except Exception as exc:                                       # noqa: BLE001
        res["safe_reset_all_raised"] = "%s: %s" % (type(exc).__name__, exc)
    cells_after_safe = eng.n_tokens(BLOCK_SEQ)
    res["path"].append({"step": "after block-inclusive global reset",
                        "block_cells": cells_after_safe,
                        "i3_fires": cells_after_safe != N_BLOCK})

    if cells_after_safe == N_BLOCK:
        # safe_reset_all skipped the registered block; the raw reset of a block seq is the
        # other half of the same trap and must clear it -- otherwise the trap cannot be shown.
        eng.reset(BLOCK_SEQ)
        cells_after_raw = eng.n_tokens(BLOCK_SEQ)
        res["path"].append({"step": "after raw reset of the block sequence",
                            "block_cells": cells_after_raw,
                            "i3_fires": cells_after_raw != N_BLOCK})
        cells = cells_after_raw
    else:
        cells = cells_after_safe

    i3 = cells != N_BLOCK
    res["i3_reading"] = {"block_cells": cells, "expected": N_BLOCK,
                         "i3_fires": i3,
                         "reason": "I3 block cells at round start = %d != %d" % (cells, N_BLOCK)}
    res["verdict"] = ("RED-B PASS -- the round is an INVALID ROUND (I3), not 未通过"
                      if i3 else "RED-B FAIL -- the block survived the global reset; I3 cannot red")
    res["secs"] = round(time.time() - t0, 1)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("verdict", "i3_reading", "path")},
                     ensure_ascii=False))
    return 0 if i3 else 1


if __name__ == "__main__":
    sys.exit(main())
