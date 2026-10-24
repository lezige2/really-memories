# -*- coding: utf-8 -*-
"""T-030 pre-check child: mount ONE block, ask that block own question.

--place car_back : keep the block at its iso_car_back position (what the 4-block run uses)
--place top      : move the single block so it ends at CHAT-1 (how the iso_*_only layouts sit)
"""
import hashlib
import json
import os
import sys
sys.path.insert(0, r"D:/llama-mem/tools")
sys.path.insert(0, r"D:/llama-mem/kvmem/m2_visibility/runs_iso2")
import m2_visibility_probe as P
import _driver2 as D2

BLOCK = sys.argv[1]
PLACE = sys.argv[2] if len(sys.argv) > 2 else "car_back"
manifest = P.load_manifest()
full = D2.build_layout("iso_car_back", manifest)
seg = dict(next(s for s in full["segments"] if s["id"] == BLOCK))
if PLACE == "top":
    seg["pos_hi"] = P.CHAT
    seg["pos_lo"] = P.CHAT - seg["cells"]
one = {"key": "one_%s_%s" % (BLOCK, PLACE), "segments": [seg], "add_order": [seg["id"]],
       "cells_total": seg["cells"], "spacing": full["spacing"],
       "span_lo": seg["pos_lo"], "span_hi": seg["pos_hi"]}
os.environ["LLAMA_KV_MASK_LAYOUT"] = one["key"]
os.environ["LLAMA_KV_MASK_WINDOWS"] = "%s:%d:%d" % (seg["id"], seg["pos_lo"], seg["pos_hi"] - 1)
os.environ["LLAMA_KV_MASK_Q"] = "precheck"
eng = P.open_engine()
out = {"block": BLOCK, "place": PLACE, "cells": seg["cells"],
       "pos": [seg["pos_lo"], seg["pos_hi"] - 1]}
try:
    P.reset_all(eng)
    eng.reset(P.LIVE)
    placed = P.load_and_place(eng, one)
    P.share_layout(eng, one, placed)
    cnt, pos = P.cell_scan(eng, P.LIVE)
    q = P.FULL[seg["block_id"]]["q"]
    fact = P.FULL[seg["block_id"]]["fact"]
    n_bytes, ans = D2.ask_native(eng, P.LIVE, q, P.CHAT, P.N_PREDICT)
    out.update({"cells_on_live": cnt, "positions": [pos[0], pos[-1]] if pos else None,
                "question": q, "expected": fact, "bytes": n_bytes,
                "answer": ans.strip(), "ok": P.fact_ok(fact, ans),
                "len": len(ans.strip()),
                "answer_sha256": hashlib.sha256(ans.encode("utf-8")).hexdigest()})
finally:
    eng.close()
print(json.dumps(out, ensure_ascii=False))