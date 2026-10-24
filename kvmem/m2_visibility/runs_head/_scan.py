# -*- coding: utf-8 -*-
"""T-004 step 0: cell_scan calibration (runs_head).

Reuses runs_iso2/_driver2.py for layout construction, and calls the NATIVE
kvshim_seq_cell_scan(h, seq=1, probe=2, ...) AFTER the ask, one run per process.
"""
import argparse, ctypes, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ISO2 = os.path.join(os.path.dirname(HERE), "runs_iso2")
sys.path.insert(0, ISO2)
import _driver2 as D2                     # noqa: E402  (layout definitions only)
P = D2.P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", required=True, choices=sorted(D2.LAYOUTS))
    ap.add_argument("--target", required=True)
    ap.add_argument("--run-json", required=True)
    a = ap.parse_args()
    manifest = P.load_manifest()
    layout = D2.build_layout(a.layout, manifest)
    t0 = time.time()
    res = {"schema": "iso_scan_v1", "experiment": a.layout, "target": a.target,
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "control_ok": False}
    eng = P.open_engine()
    try:
        eng.lib.kvshim_n_tokens.argtypes = [ctypes.c_void_p, ctypes.c_int]
        eng.lib.kvshim_n_tokens.restype = ctypes.c_int
        for bid, meta in manifest["blocks"]["m2"].items():
            if P.sha256_file(meta["path"]) != meta["sha256"]:
                raise RuntimeError("pristine block hash changed: %s" % meta["path"])
        P.reset_all(eng)
        ctexts = D2.get_control(eng, a.layout, layout)
        ok, ctrl = P.run_control(eng, layout, a.layout, ctexts, P.FULL, D2.CONTROL_ORDER)
        res["control_ok"] = bool(ok)
        res["control_questions_ok"] = [q["ok"] for q in (ctrl.get("questions") or [])]
        if not ok:
            res["failure"] = "CONTROL GATE FAILED"
            P._write_json(a.run_json, res)
            return 3
        P.reset_all(eng)
        placed = P.load_and_place(eng, layout)
        P.share_layout(eng, layout, placed)
        res["pre_ask"] = {"live_pos_max_raw": P.raw_pos_max(eng, P.LIVE),
                          "n_tokens": int(eng.lib.kvshim_n_tokens(eng.h, P.LIVE))}
        seg = next(s for s in layout["segments"] if s["id"] == a.target)
        q = P.FULL[seg["block_id"]]["q"]
        fact = P.FULL[seg["block_id"]]["fact"]
        eng.reset(P.LIVE)
        P.share_layout(eng, layout, placed)
        n_bytes, ans = D2.ask_native(eng, P.LIVE, q, P.CHAT, P.N_PREDICT)
        # ---- native cell scan AFTER the ask; probe seq = 2 (0=memory, 1=chat)
        cap = P.N_CTX
        buf = (ctypes.c_int * cap)()
        n = int(eng.lib.kvshim_seq_cell_scan(eng.h, P.LIVE, 2, buf, cap))
        positions = sorted(int(buf[i]) for i in range(max(n, 0)))
        expect = set()
        for s in layout["segments"]:
            expect.update(range(s["pos_lo"], s["pos_hi"]))
        got = set(positions)
        res["ask"] = {"kvshim_ask_at_return_bytes": n_bytes, "answer_len": len(ans),
                      "answer": ans.strip(), "expected": fact,
                      "ok": bool(P.fact_ok(fact, ans)),
                      "n_tokens_after_ask": int(eng.lib.kvshim_n_tokens(eng.h, P.LIVE))}
        res["scan"] = {"probe_seq": 2, "count": len(positions),
                       "pos_min": positions[0] if positions else None,
                       "pos_max": positions[-1] if positions else None,
                       "first20": positions[:20], "last20": positions[-20:],
                       "positions": positions}
        res["compare"] = {"expected_cells": len(expect), "reported_cells": len(got),
                          "missing_count": len(expect - got),
                          "missing_min": min(expect - got) if expect - got else None,
                          "missing_max": max(expect - got) if expect - got else None,
                          "extra_count": len(got - expect),
                          "extra_sample": sorted(got - expect)[:10]}
        segs = [{"id": s["id"], "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"],
                 "cells": s["cells"]} for s in layout["segments"]]
        res["layout"] = {"key": a.layout, "span_lo": layout["span_lo"],
                         "span_hi": layout["span_hi"], "segments": segs,
                         "head_gap_cells": (P.CHAT - 1) - (layout["span_hi"] - 1)}
        res["elapsed_s"] = round(time.time() - t0, 2)
        P._write_json(a.run_json, res)
        print("%s/%s ask=%d ans_ok=%s scan=%d pos[%s..%s] missing=%d extra=%d" % (
            a.layout, a.target, n_bytes, res["ask"]["ok"], len(positions),
            res["scan"]["pos_min"], res["scan"]["pos_max"],
            res["compare"]["missing_count"], res["compare"]["extra_count"]))
        return 0
    except Exception as exc:                                   # noqa: BLE001
        res["error"] = "%s: %s" % (type(exc).__name__, exc)
        P._write_json(a.run_json, res)
        print("ERROR %s" % exc)
        return 4
    finally:
        try:
            eng.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())