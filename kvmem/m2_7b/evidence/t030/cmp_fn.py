# -*- coding: utf-8 -*-
"""Compare kvshim_ask_at with kvshim_ask_at_topk on ONE identical configuration."""
import argparse, json, os, sys
sys.path.insert(0, r"D:/llama-mem/tools")
sys.path.insert(0, r"D:/llama-mem/kvmem/m2_visibility/runs_iso2")
import m2_visibility_probe as P
import _driver2 as D2
ap = argparse.ArgumentParser()
ap.add_argument("--fn", choices=["ask_at", "topk"], required=True)
ap.add_argument("--block", default="project")
ap.add_argument("--ask-pos", type=int, default=4096)
a = ap.parse_args()
layout = D2.build_layout("iso_car_back", P.load_manifest())
seg = dict(next(s2 for s2 in layout["segments"] if s2["id"] == a.block))
seg["pos_hi"] = P.CHAT
seg["pos_lo"] = P.CHAT - seg["cells"]
one = {"key": "cmp", "segments": [seg], "add_order": [seg["id"]], "cells_total": seg["cells"],
       "spacing": layout["spacing"], "span_lo": seg["pos_lo"], "span_hi": seg["pos_hi"]}
os.environ["LLAMA_KV_MASK_LAYOUT"] = "envtest"
os.environ["LLAMA_KV_MASK_WINDOWS"] = "%s:%d:%d" % (seg["id"], seg["pos_lo"], seg["pos_hi"] - 1)
os.environ["LLAMA_KV_MASK_Q"] = "envtest"
q = P.FULL[seg["block_id"]]["q"]
eng = P.open_engine()
try:
    P.reset_all(eng)
    eng.reset(P.LIVE)
    placed = P.load_and_place(eng, one)
    P.share_layout(eng, one, placed)
    cnt, pos = P.cell_scan(eng, P.LIVE)
    if a.fn == "ask_at":
        nb, ans = D2.ask_native(eng, P.LIVE, q, a.ask_pos, P.N_PREDICT)
        out = {"fn": "ask_at", "rc": nb, "answer": ans.strip()}
    else:
        r = eng.ask_at_topk(P.LIVE, q, a.ask_pos, k=5, n_predict=P.N_PREDICT)
        out = {"fn": "topk", "rc": r["rc"], "answer": r["answer"].strip(),
               "top5": [(t["token"], round(t["prob"], 5)) for t in r["topk"]]}
    out.update({"block_pos": [seg["pos_lo"], seg["pos_hi"] - 1], "ask_pos": a.ask_pos,
                "cells_on_live": cnt})
    print(json.dumps(out, ensure_ascii=False))
finally:
    eng.close()