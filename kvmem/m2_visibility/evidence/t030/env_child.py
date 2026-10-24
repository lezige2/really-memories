# -*- coding: utf-8 -*-
"""One ask under a chosen geometry; prints the LLAMA_KV_* environment it actually ran with."""
import argparse, json, os, sys
sys.path.insert(0, r"D:/llama-mem/tools")
sys.path.insert(0, r"D:/llama-mem/kvmem/m2_visibility/runs_iso2")
import m2_visibility_probe as P
import _driver2 as D2
ap = argparse.ArgumentParser()
ap.add_argument("--block", default="project")
ap.add_argument("--hole", type=int, default=0)
ap.add_argument("--ask-pos", type=int, default=4096)
a = ap.parse_args()
layout = D2.build_layout("iso_car_back", P.load_manifest())
seg = dict(next(s2 for s2 in layout["segments"] if s2["id"] == a.block))
seg["pos_hi"] = P.CHAT - a.hole
seg["pos_lo"] = seg["pos_hi"] - seg["cells"]
one = {"key": "envtest", "segments": [seg], "add_order": [seg["id"]], "cells_total": seg["cells"],
       "spacing": layout["spacing"], "span_lo": seg["pos_lo"], "span_hi": seg["pos_hi"]}
os.environ["LLAMA_KV_MASK_LAYOUT"] = one["key"]
os.environ["LLAMA_KV_MASK_WINDOWS"] = "%s:%d:%d" % (seg["id"], seg["pos_lo"], seg["pos_hi"] - 1)
os.environ["LLAMA_KV_MASK_Q"] = "envtest"
os.environ["LLAMA_KV_MASK_DEBUG"] = "1"
env = {k: v for k, v in os.environ.items() if k.startswith("LLAMA_")}
q = P.FULL[seg["block_id"]]["q"]
eng = P.open_engine()
try:
    P.reset_all(eng)
    eng.reset(P.LIVE)
    placed = P.load_and_place(eng, one)
    P.share_layout(eng, one, placed)
    cnt, pos = P.cell_scan(eng, P.LIVE)
    nb, ans = D2.ask_native(eng, P.LIVE, q, a.ask_pos, P.N_PREDICT)
    print(json.dumps({"block": a.block, "pos": [seg["pos_lo"], seg["pos_hi"] - 1],
                      "ask_pos": a.ask_pos, "cells": cnt, "rc": nb,
                      "answer": ans.strip()[:60],
                      "env": env}, ensure_ascii=False))
finally:
    eng.close()