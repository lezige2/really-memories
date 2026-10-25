# -*- coding: utf-8 -*-
"""First-step top-k for one configuration (blocks listed explicitly, car_back geometry)."""
import argparse
import json
import os
import sys
sys.path.insert(0, r"D:/llama-mem/tools")
sys.path.insert(0, r"D:/llama-mem/kvmem/m2_visibility/runs_iso2")
import m2_visibility_probe as P
import _driver2 as D2

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--layout", required=True)
ap.add_argument("--blocks", required=True, help="comma separated, empty means the whole layout")
ap.add_argument("--target", default="home")
ap.add_argument("--k", type=int, default=8)
ap.add_argument("--ask-pos", type=int, default=-1)
ap.add_argument("--fact-token", type=int, default=-1)
a = ap.parse_args()

manifest = P.load_manifest()
layout = D2.build_layout(a.layout, manifest)
if a.blocks.strip():
    want = [b for b in a.blocks.split(",") if b]
    layout = dict(layout)
    layout["segments"] = [s for s in layout["segments"] if s["id"] in want]
    layout["add_order"] = [i for i in layout["add_order"] if i in want]
    layout["key"] = "%s_subset" % a.layout
os.environ["LLAMA_KV_MASK_LAYOUT"] = layout["key"]
os.environ["LLAMA_KV_MASK_WINDOWS"] = ",".join(
    "%s:%d:%d" % (s["id"], s["pos_lo"], s["pos_hi"] - 1) for s in layout["segments"])
os.environ["LLAMA_KV_MASK_Q"] = "curve"
tq = next(s for s in D2.build_layout(a.layout, manifest)["segments"] if s["id"] == a.target)
q = P.FULL[tq["block_id"]]["q"]
fact = P.FULL[tq["block_id"]]["fact"]
ask_pos = a.ask_pos if a.ask_pos >= 0 else P.CHAT
eng = P.open_engine()
try:
    P.reset_all(eng)
    eng.reset(P.LIVE)
    placed = P.load_and_place(eng, layout)
    P.share_layout(eng, layout, placed)
    cnt, pos = P.cell_scan(eng, P.LIVE)
    r = eng.ask_at_topk(P.LIVE, q, ask_pos, k=a.k, n_predict=P.N_PREDICT)
    import sys as _s; print("ENV " + str({k: v for k, v in os.environ.items() if k.startswith("LLAMA_")}), file=_s.stderr)
    topk = [{"token": e["token"], "prob": round(e["prob"], 8)} for e in r["topk"]]
    out = {"name": a.name, "layout": a.layout, "blocks": [p["id"] for p in placed],
           "block_detail": [{k2: p[k2] for k2 in ("id", "file", "file_sha256", "cells", "base", "delta", "pos_lo")}
                            for p in placed],
           "ask_pos": ask_pos, "cells_on_live": cnt,
           "cells_min": pos[0] if pos else None, "cells_max": pos[-1] if pos else None,
           "question": q, "expected": fact, "rc": r["rc"],
           "answer": r["answer"].strip(), "ok": P.fact_ok(fact, r["answer"].strip()),
           "topk": topk}
    if a.fact_token >= 0:
        probs = [t["prob"] for t in topk]
        ids = [t["token"] for t in topk]
        hit = [i for i, t in enumerate(ids) if t == a.fact_token]
        out["fact_token"] = a.fact_token
        out["p_fact"] = probs[hit[0]] if hit else 0.0
        out["rank_fact"] = (hit[0] + 1) if hit else None
        out["p_top1"] = probs[0]
        out["p_ratio_to_top1"] = round(out["p_fact"] / probs[0], 6) if probs[0] > 0 else None
    print(json.dumps(out, ensure_ascii=False))
finally:
    eng.close()