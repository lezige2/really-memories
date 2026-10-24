# -*- coding: utf-8 -*-
"""T-004 round 3 driver (runs_iso3): two-axis design, zero new blocks.

Axis A (cells fixed at 5, content varies) : bottom = c_project / c_home / c_habit / c_car
Axis B (content fixed = project, cells)   : bottom = c_project(5) vs project(18)
I13 cells sweep                           : bottom = 5 / 12 / 18 / 19 / 20 / 28 / 31
Top three segments are always m2 home(slot1) / project(slot2) / habit(slot3).
"""
import argparse, ctypes, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ISO2 = os.path.join(os.path.dirname(HERE), "runs_iso2")
sys.path.insert(0, ISO2)
import _driver2 as D2                      # noqa: E402
P = D2.P
CTRL_CACHE = os.path.join(HERE, "control_texts.json")
CONTROL_ORDER = D2.CONTROL_ORDER
TOP3 = [(1, "home", "m2", "home"), (2, "project", "m2", "project"), (3, "habit", "m2", "habit")]


def lay(bot_sid, bot_family, bot_bid, spacing=64):
    return {"spacing": spacing, "segs": TOP3 + [(4, bot_sid, bot_family, bot_bid)]}


LAYOUTS3 = {
    "axA_c_project": lay("bot", "variant", "c_project"),
    "axA_c_home":    lay("bot", "variant", "c_home"),
    "axA_c_habit":   lay("bot", "variant", "c_habit"),
    "axA_c_car":     lay("bot", "variant", "c_car"),
    "I13_b_habit20": lay("bot", "variant", "b_habit"),
    "I13_b_proj28":  lay("bot", "variant", "b_project"),
    "I13_b_home31":  lay("bot", "variant", "b_home"),
}


def build_layout(key, manifest):
    spec = LAYOUTS3[key]
    segs, order = [], []
    for slot, sid, family, bid in spec["segs"]:
        b = manifest["blocks"][family][bid]
        n = b["cells"]
        lo = P.CHAT - (slot - 1) * spec["spacing"] - n
        segs.append({"id": sid, "block": family, "block_id": bid, "file": b["path"],
                     "file_sha256": b["sha256"], "cells": n, "slot": slot,
                     "pos_lo": lo, "pos_hi": lo + n, "add_order": len(order) + 1})
        order.append(sid)
    return {"key": key, "segments": segs, "add_order": order,
            "control_order": CONTROL_ORDER,
            "start": min(s["pos_lo"] for s in segs),
            "cells_total": sum(s["cells"] for s in segs),
            "span_lo": min(s["pos_lo"] for s in segs),
            "span_hi": max(s["pos_hi"] for s in segs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", required=True, choices=sorted(LAYOUTS3))
    ap.add_argument("--target", required=True)
    ap.add_argument("--run-json", required=True)
    a = ap.parse_args()
    manifest = P.load_manifest()
    layout = build_layout(a.layout, manifest)
    ids = [s["id"] for s in layout["segments"]]
    if a.target not in ids:
        raise SystemExit("target %s not in %s (%s)" % (a.target, a.layout, ids))
    t0 = time.time()
    res = {"schema": "iso_run_v3", "experiment": a.layout, "target": a.target,
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "layout_key": a.layout,
           "seg_ids": ids, "control_ok": False, "attributable": False}
    eng = P.open_engine()
    try:
        eng.lib.kvshim_n_tokens.argtypes = [ctypes.c_void_p, ctypes.c_int]
        eng.lib.kvshim_n_tokens.restype = ctypes.c_int
        ctexts = D2.get_control(eng, a.layout, layout)
        ok, ctrl = P.run_control(eng, layout, a.layout, ctexts, P.FULL, CONTROL_ORDER)
        res["control_ok"] = bool(ok)
        res["attributable"] = bool(ok)
        res["control"] = ctrl
        if not ok:
            res["failure"] = "CONTROL GATE FAILED"
            P._write_json(a.run_json, res)
            return 3
        P.reset_all(eng)
        placed = P.load_and_place(eng, layout)
        P.share_layout(eng, layout, placed)
        raw = P.raw_pos_max(eng, P.LIVE)
        cnt, positions = P.cell_scan(eng, P.LIVE)
        res["layout"] = {"key": a.layout, "start": layout["start"],
                         "cells_total": layout["cells_total"],
                         "span_lo": layout["span_lo"], "span_hi": layout["span_hi"],
                         "head_gap_cells": (P.CHAT - 1) - (layout["span_hi"] - 1),
                         "segments": [{"id": s["id"], "block_id": s["block_id"],
                                       "family": s["block"], "slot": s["slot"],
                                       "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"],
                                       "cells": s["cells"]} for s in layout["segments"]]}
        res["raw"] = {"live_pos_max_raw": raw, "cell_count": cnt,
                      "coverage": P.coverage(positions, layout),
                      "positions_min": positions[0] if positions else None,
                      "positions_max": positions[-1] if positions else None}
        seg = next(s for s in layout["segments"] if s["id"] == a.target)
        q = P.FULL[seg["block_id"]]["q"]
        fact = P.FULL[seg["block_id"]]["fact"]
        eng.reset(P.LIVE)
        P.share_layout(eng, layout, placed)
        n_bytes, ans = D2.ask_native(eng, P.LIVE, q, P.CHAT, P.N_PREDICT)
        res["answers"] = [{"segment": a.target, "block_id": seg["block_id"],
                           "slot": seg["slot"], "pos_lo": seg["pos_lo"],
                           "pos_hi": seg["pos_hi"], "cells": seg["cells"],
                           "kvshim_ask_at_return_bytes": n_bytes,
                           "kvshim_n_tokens_after_ask": int(eng.lib.kvshim_n_tokens(eng.h, P.LIVE)),
                           "question": q, "expected": fact, "answer": ans.strip(),
                           "ok": bool(P.fact_ok(fact, ans))}]
        res["elapsed_s"] = round(time.time() - t0, 2)
        P._write_json(a.run_json, res)
        print("%s/%s -> %s bytes=%d %r" % (a.layout, a.target,
              "OK" if res["answers"][0]["ok"] else "MISS", n_bytes, ans.strip()[:40]))
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