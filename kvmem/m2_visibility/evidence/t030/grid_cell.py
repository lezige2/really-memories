# -*- coding: utf-8 -*-
"""Four-cell grid: block tail x ask position, block EXPLICITLY placed (no inherited layout position)."""
import argparse, json, os, sys
sys.path.insert(0, r"D:/llama-mem/tools")
sys.path.insert(0, r"D:/llama-mem/kvmem/m2_visibility/runs_iso2")
import m2_visibility_probe as P
import _driver2 as D2
ap = argparse.ArgumentParser()
ap.add_argument("--tail", type=int, required=True)
ap.add_argument("--ask-pos", type=int, required=True)
ap.add_argument("--block", default="project")
a = ap.parse_args()
layout = D2.build_layout("iso_car_back", P.load_manifest())
seg = dict(next(s2 for s2 in layout["segments"] if s2["id"] == a.block))
seg["pos_hi"] = a.tail + 1
seg["pos_lo"] = seg["pos_hi"] - seg["cells"]
one = {"key": "grid", "segments": [seg], "add_order": [seg["id"]], "cells_total": seg["cells"],
       "spacing": layout["spacing"], "span_lo": seg["pos_lo"], "span_hi": seg["pos_hi"]}
os.environ["LLAMA_KV_MASK_LAYOUT"] = "grid"
os.environ["LLAMA_KV_MASK_WINDOWS"] = "%s:%d:%d" % (seg["id"], seg["pos_lo"], seg["pos_hi"] - 1)
q = P.FULL[seg["block_id"]]["q"]
eng = P.open_engine()
try:
    P.reset_all(eng)
    eng.reset(P.LIVE)
    placed = P.load_and_place(eng, one)
    P.share_layout(eng, one, placed)
    cnt, pos = P.cell_scan(eng, P.LIVE)
    nb, ans = D2.ask_native(eng, P.LIVE, q, a.ask_pos, P.N_PREDICT)
    print(json.dumps({"tail": a.tail, "ask_pos": a.ask_pos,
                      "block": [seg["pos_lo"], seg["pos_hi"] - 1],
                      "gap": a.ask_pos - (seg["pos_hi"] - 1) - 1,
                      "cells_on_live": cnt, "cells_range": [pos[0], pos[-1]] if pos else None,
                      "rc": nb, "answer": ans.strip()[:70], "ok": P.fact_ok(P.FULL[seg["block_id"]]["fact"], ans)},
                     ensure_ascii=False))
finally:
    eng.close()