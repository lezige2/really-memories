# -*- coding: utf-8 -*-
"""T-004 isolation driver. Reuses tools/m2_visibility_probe.py as a library;
does NOT modify it, llama.cpp, runs/ or runs_var/.

Custom layouts are built in this file from the manifest block metadata.
One process = one (layout, target) ask, mirroring the probe arm flow.
"""
import argparse, hashlib, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import m2_visibility_probe as P   # noqa: E402

ISO_DIR = HERE
CTRL_CACHE = os.path.join(ISO_DIR, "control_texts.json")

# --- experiment layouts: (spacing, [(slot, block_id)] )  positions = CHAT-(slot-1)*SPACING-n
LAYOUTS = {
    "iso_base":   {"spacing": 64,  "segs": [(1, "home"), (2, "project"), (3, "habit"), (4, "car")]},
    "iso_no_car": {"spacing": 64,  "segs": [(1, "home"), (2, "project"), (3, "habit")]},
    "iso_no_home":{"spacing": 64,  "segs": [(2, "project"), (3, "habit"), (4, "car")]},
    "iso_gap256": {"spacing": 256, "segs": [(1, "home"), (2, "project"), (3, "habit"), (4, "car")]},
    "iso_gap32":  {"spacing": 32,  "segs": [(1, "home"), (2, "project"), (3, "habit"), (4, "car")]},
}
CONTROL_ORDER = ["home", "project", "habit", "car"]


def build_layout(key, manifest):
    spec = LAYOUTS[key]
    m2 = manifest["blocks"]["m2"]
    segs = []
    order = []
    for slot, bid in spec["segs"]:
        b = m2[bid]
        n = b["cells"]
        lo = P.CHAT - (slot - 1) * spec["spacing"] - n
        segs.append({"id": bid, "block": "m2", "block_id": bid, "file": b["path"],
                     "file_sha256": b["sha256"], "cells": n, "slot": slot,
                     "pos_lo": lo, "pos_hi": lo + n, "add_order": len(order) + 1})
        order.append(bid)
    return {"key": key, "segments": segs, "add_order": order,
            "control_order": CONTROL_ORDER,
            "start": min(s["pos_lo"] for s in segs),
            "cells_total": sum(s["cells"] for s in segs),
            "span_lo": min(s["pos_lo"] for s in segs),
            "span_hi": max(s["pos_hi"] for s in segs)}


def get_control(eng, key, layout):
    cache = {}
    if os.path.exists(CTRL_CACHE):
        with open(CTRL_CACHE, "r", encoding="utf-8") as f:
            cache = json.load(f)
    if key in cache:
        c = cache[key]
        if (c.get("start") == layout["start"]
                and hashlib.sha256(c["text"].encode("utf-8")).hexdigest() == c["sha256"]):
            if P.measure(eng, c["text"]) == c["target_n"]:
                return {key: c}
    target_n = P.CHAT - layout["start"]
    prefix = "".join(P.FULL[sid]["text"] for sid in CONTROL_ORDER)
    text = P.build_exact_text(eng, prefix, target_n)
    n = P.measure(eng, text)
    if n != target_n or layout["start"] + n - 1 != P.CHAT - 1:
        raise RuntimeError("control text %d tokens, need %d" % (n, target_n))
    c = {"start": layout["start"], "target_n": target_n, "text": text, "measured_n": n,
         "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
         "prefix_order": CONTROL_ORDER}
    cache[key] = c
    with open(CTRL_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    return {key: c}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", required=True, choices=sorted(LAYOUTS))
    ap.add_argument("--target", required=True)
    ap.add_argument("--run-json", required=True)
    a = ap.parse_args()
    manifest = P.load_manifest()
    layout = build_layout(a.layout, manifest)
    ids = [s["id"] for s in layout["segments"]]
    if a.target not in ids:
        raise SystemExit("target %s not in layout %s (%s)" % (a.target, a.layout, ids))
    t0 = time.time()
    res = {"schema": "iso_run_v1", "experiment": a.layout, "target": a.target,
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "layout_key": a.layout, "spacing": LAYOUTS[a.layout]["spacing"],
           "seg_ids": ids, "control_ok": False, "attributable": False}
    eng = P.open_engine()
    try:
        res["engine"] = {"n_ctx": P.N_CTX, "n_seq": P.N_SEQ, "kv": P.KV, "gpu": P.GPU,
                         "dll_sha256": manifest["engine"]["dll_sha256"]}
        for bid, meta in manifest["blocks"]["m2"].items():
            if P.sha256_file(meta["path"]) != meta["sha256"]:
                raise RuntimeError("pristine block hash changed: %s" % meta["path"])
        P.reset_all(eng)
        ctexts = get_control(eng, a.layout, layout)
        ok, ctrl = P.run_control(eng, layout, a.layout, ctexts, P.FULL, layout["add_order"])
        res["control"] = ctrl
        res["control_ok"] = bool(ok)
        res["attributable"] = bool(ok)
        if not ok:
            res["failure"] = "CONTROL GATE FAILED -- not interpreted"
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
                         "segments": [{"id": s["id"], "slot": s["slot"],
                                       "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"],
                                       "cells": s["cells"]} for s in layout["segments"]]}
        res["raw"] = {"live_pos_max_raw": raw, "cell_count": cnt,
                      "coverage": P.coverage(positions, layout),
                      "overlaps": P.overlaps(layout),
                      "positions_min": positions[0] if positions else None,
                      "positions_max": positions[-1] if positions else None}
        seg = next(s for s in layout["segments"] if s["id"] == a.target)
        q = P.FULL[a.target]["q"]
        fact = P.FULL[a.target]["fact"]
        eng.reset(P.LIVE)
        P.share_layout(eng, layout, placed)
        before = P.raw_pos_max(eng, P.LIVE)
        ans = eng.ask(P.LIVE, q, n_predict=P.N_PREDICT, pos=P.CHAT)
        res["answers"] = [{"segment": a.target, "add_order": seg["add_order"],
                           "slot": seg["slot"], "pos_lo": seg["pos_lo"],
                           "pos_hi": seg["pos_hi"], "cells": seg["cells"],
                           "raw_pos_max_before_ask": before, "question": q,
                           "expected": fact, "answer": ans.strip(),
                           "ok": bool(P.fact_ok(fact, ans))}]
        res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        res["elapsed_s"] = round(time.time() - t0, 2)
        P._write_json(a.run_json, res)
        print("%s/%s -> %s %r" % (a.layout, a.target,
                                   "OK" if res["answers"][0]["ok"] else "MISS",
                                   ans.strip()[:50]))
        return 0
    except Exception as exc:                                   # noqa: BLE001
        res["error"] = "%s: %s" % (type(exc).__name__, exc)
        res["elapsed_s"] = round(time.time() - t0, 2)
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