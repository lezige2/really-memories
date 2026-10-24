# -*- coding: utf-8 -*-
"""Mount ONE block, ending `hole` cells below the question point, then ask its own question."""
import hashlib
import json
import os
import sys
sys.path.insert(0, r"D:/llama-mem/tools")
sys.path.insert(0, r"D:/llama-mem/kvmem/m2_visibility/runs_iso2")
import m2_visibility_probe as P
import _driver2 as D2

BLOCK = sys.argv[1]
HOLE = int(sys.argv[2])
manifest = P.load_manifest()
full = D2.build_layout("iso_car_back", manifest)
seg = dict(next(s for s in full["segments"] if s["id"] == BLOCK))
seg["pos_hi"] = P.CHAT - HOLE
seg["pos_lo"] = seg["pos_hi"] - seg["cells"]
one = {"key": "hole_%d_%s" % (HOLE, BLOCK), "segments": [seg], "add_order": [seg["id"]],
       "cells_total": seg["cells"], "spacing": full["spacing"],
       "span_lo": seg["pos_lo"], "span_hi": seg["pos_hi"]}
os.environ["LLAMA_KV_MASK_DEBUG"] = "1"
os.environ["LLAMA_KV_MASK_LAYOUT"] = one["key"]
os.environ["LLAMA_KV_MASK_WINDOWS"] = "%s:%d:%d" % (seg["id"], seg["pos_lo"], seg["pos_hi"] - 1)
os.environ["LLAMA_KV_MASK_Q"] = "hole"
out = {"block": BLOCK, "hole": HOLE, "pos": [seg["pos_lo"], seg["pos_hi"] - 1],
       "gap_to_question": P.CHAT - seg["pos_hi"]}
eng = P.open_engine()
try:
    P.reset_all(eng)
    eng.reset(P.LIVE)
    placed = P.load_and_place(eng, one)
    P.share_layout(eng, one, placed)
    cnt, pos = P.cell_scan(eng, P.LIVE)
    q = P.FULL[seg["block_id"]]["q"]
    fact = P.FULL[seg["block_id"]]["fact"]
    n_bytes, ans = D2.ask_native(eng, P.LIVE, q, P.CHAT, P.N_PREDICT)
    txt = ans.strip()
    out.update({"cells": cnt, "positions": [pos[0], pos[-1]] if pos else None,
                "question": q, "expected": fact, "bytes_rc": n_bytes,
                "answer": txt, "len": len(txt), "ok": P.fact_ok(fact, txt),
                "answer_sha256": hashlib.sha256(ans.encode("utf-8")).hexdigest()})
finally:
    eng.close()
print(json.dumps(out, ensure_ascii=False))