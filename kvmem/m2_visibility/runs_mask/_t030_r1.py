# -*- coding: utf-8 -*-
"""T-030 step 2 (R1): send the preamble through the SAME pipeline the memory blocks use.

    write_at(scratch,0) -> save -> load -> repos_local(-> start) -> seq_cp(LIVE)

Blocks are restored from files and then re-rotated cell by cell; a directly written preamble
is computed in the current graph and never rotated. If the rotated preamble loses its effect,
the restore+re-rotation path is the suspect; if the effect survives, that explanation dies.
"""
import argparse
import hashlib
import json
import os
import sys
sys.path.insert(0, r"D:/llama-mem/tools")
sys.path.insert(0, r"D:/llama-mem/kvmem/m2_visibility/runs_iso2")
import m2_visibility_probe as P
import _driver2 as D2

PRE = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t028/preambles.json"
SCRATCH = 6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="P", choices=["P", "C", "H", "N"])
    ap.add_argument("--mode", default="rotated", choices=["rotated", "direct"])
    ap.add_argument("--layout", default="iso_car_back")
    ap.add_argument("--target", default="home")
    ap.add_argument("--run-json", required=True)
    a = ap.parse_args()
    pre = json.load(open(PRE, encoding="utf-8"))["arms"][a.arm]["text"]
    manifest = P.load_manifest()
    layout = D2.build_layout(a.layout, manifest)
    os.environ["LLAMA_KV_MASK_LAYOUT"] = a.layout
    os.environ["LLAMA_KV_MASK_WINDOWS"] = ",".join(
        "%s:%d:%d" % (s["id"], s["pos_lo"], s["pos_hi"] - 1) for s in layout["segments"])
    os.environ["LLAMA_KV_MASK_Q"] = "r1"
    seg = next(s for s in layout["segments"] if s["id"] == a.target)
    q = P.FULL[seg["block_id"]]["q"]
    fact = P.FULL[seg["block_id"]]["fact"]
    res = {"schema": "t030_r1_v1", "arm": a.arm, "mode": a.mode, "layout": a.layout,
           "target": a.target, "cmdline": sys.argv}
    eng = P.open_engine()
    try:
        P.reset_all(eng)
        eng.reset(SCRATCH)
        lo_min = min(s["pos_lo"] for s in layout["segments"])
        n = P.measure(eng, pre) - 1
        start = lo_min - n
        res["preamble"] = {"text": pre, "n_tokens_measured": n, "start": start, "end": lo_min,
                           "sha256": hashlib.sha256(pre.encode("utf-8")).hexdigest()}
        placed = P.load_and_place(eng, layout)
        eng.reset(P.LIVE)
        if a.mode == "direct":
            rc = int(eng.write_at(P.LIVE, pre, start, add_bos=False))
            res["preamble"].update({"write_at_rc": rc, "pipeline": "write_at(LIVE) directly"})
        else:
            rc = int(eng.write_at(SCRATCH, pre, 0, add_bos=False))
            tmp = os.path.join(os.path.dirname(os.path.abspath(a.run_json)), "t030_scratch_%s.kvmem" % a.arm)
            eng.save(SCRATCH, tmp)
            saved_cells, saved_pos = P.cell_scan(eng, SCRATCH)
            eng.reset(SCRATCH)
            loaded = int(eng.load(SCRATCH, tmp))
            base = eng.pos_max(SCRATCH) - loaded + 1
            delta = start - base
            moved = int(eng.repos_local(SCRATCH, delta))
            after_cells, after_pos = P.cell_scan(eng, SCRATCH)
            eng.share(SCRATCH, P.LIVE)
            res["preamble"].update({
                "write_at_rc": rc, "saved_cells": saved_cells, "loaded_cells": loaded,
                "repos_delta": delta, "repos_moved": moved,
                "cells_after_repos": after_cells,
                "positions_after_repos": [after_pos[0], after_pos[-1]] if after_pos else None,
                "scratch_file": os.path.basename(tmp),
                "pipeline": "write_at(scratch,0) -> save -> load -> repos_local -> seq_cp(LIVE)"})
            if moved != loaded or after_pos[:1] != [start]:
                P._write_json(a.run_json, res)
                raise SystemExit("repos_local on the preamble did not land at %d" % start)
        P.share_layout(eng, layout, placed)
        cnt, pos = P.cell_scan(eng, P.LIVE)
        n_bytes, ans = D2.ask_native(eng, P.LIVE, q, P.CHAT, P.N_PREDICT)
        asha = hashlib.sha256(ans.encode("utf-8")).hexdigest()
        res.update({"cells_at_ask": cnt, "cells_min": pos[0] if pos else None,
                    "question": q, "expected": fact, "bytes": n_bytes,
                    "answer": ans.strip(), "len": len(ans.strip()),
                    "ok": P.fact_ok(fact, ans), "answer_sha256": asha})
        P._write_json(a.run_json, res)
        print("%s/%s %s cells=%d sha=%s ok=%s len=%d"
              % (a.arm, a.mode, a.target, cnt, asha[:16], res["ok"], res["len"]))
        return 0
    finally:
        eng.close()


if __name__ == "__main__":
    sys.exit(main())