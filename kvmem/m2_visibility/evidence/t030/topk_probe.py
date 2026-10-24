# -*- coding: utf-8 -*-
"""First-step top-k for a single-block configuration, via the new additive shim export."""
import json
import os
import sys
sys.path.insert(0, r"D:/llama-mem/tools")
sys.path.insert(0, r"D:/llama-mem/kvmem/m2_visibility/runs_iso2")
import m2_visibility_probe as P
import _driver2 as D2

LAYOUT, BLOCK, TARGET = sys.argv[1], sys.argv[2], sys.argv[3]
manifest = P.load_manifest()
full = D2.build_layout(LAYOUT, manifest)
seg = dict(next(s for s in full["segments"] if s["id"] == BLOCK))
seg["pos_hi"] = P.CHAT
seg["pos_lo"] = P.CHAT - seg["cells"]
one = {"key": "topk_%s" % BLOCK, "segments": [seg], "add_order": [seg["id"]],
       "cells_total": seg["cells"], "spacing": full["spacing"],
       "span_lo": seg["pos_lo"], "span_hi": seg["pos_hi"]}
os.environ["LLAMA_KV_MASK_LAYOUT"] = one["key"]
os.environ["LLAMA_KV_MASK_WINDOWS"] = "%s:%d:%d" % (seg["id"], seg["pos_lo"], seg["pos_hi"] - 1)
tq = next(s for s in full["segments"] if s["id"] == TARGET)
q = P.FULL[tq["block_id"]]["q"]
fact = P.FULL[tq["block_id"]]["fact"]
eng = P.open_engine()
try:
    P.reset_all(eng)
    eng.reset(P.LIVE)
    placed = P.load_and_place(eng, one)
    P.share_layout(eng, one, placed)
    r = eng.ask_at_topk(P.LIVE, q, P.CHAT, k=5, n_predict=P.N_PREDICT)
    toks = []
    for e in r["topk"]:
        try:
            toks.append(llama_piece(eng, e["token"]))
        except Exception:
            toks.append(None)
    out = {"layout": LAYOUT, "block": BLOCK, "target": TARGET, "question": q,
           "expected": fact, "rc": r["rc"], "answer": r["answer"].strip(),
           "top5": [{"token": e["token"], "prob": e["prob"]} for e in r["topk"]]}
    print(json.dumps(out, ensure_ascii=False))
finally:
    eng.close()