# -*- coding: utf-8 -*-
"""T-004 round 2 driver (runs_iso2). Reuses tools/m2_visibility_probe.py as a library.

Differences from runs_iso/_driver.py:
  * new layouts (I5 add-back, I8 add-order / block swap, I7 duplicated 4th block)
  * records NATIVE fields only: the int returned by kvshim_ask_at (bytes) and
    kvshim_n_tokens(seq) before/after the ask (kvshim.cpp:220) -- no invented field.
"""
import argparse, ctypes, hashlib, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P   # noqa: E402

CTRL_CACHE = os.path.join(HERE, "control_texts.json")
CONTROL_ORDER = ["home", "project", "habit", "car"]

# seg id -> block id (duplicates allowed: a second copy of one block)
LAYOUTS = {
    "iso_car_back": {"spacing": 64, "segs": [(1, "home", "home"), (2, "project", "project"),
                                            (3, "habit", "habit"), (4, "car", "car")]},
    "iso_no_car":   {"spacing": 64, "segs": [(1, "home", "home"), (2, "project", "project"),
                                            (3, "habit", "habit")]},
    "iso_no_home":  {"spacing": 64, "segs": [(2, "project", "project"), (3, "habit", "habit"),
                                            (4, "car", "car")]},
    "iso_order_rev":{"spacing": 64, "segs": [(1, "home", "home"), (2, "project", "project"),
                                            (3, "habit", "habit"), (4, "car", "car")],
                     "add_order": ["car", "habit", "project", "home"]},
    "iso_swap_top": {"spacing": 64, "segs": [(1, "car", "car"), (2, "project", "project"),
                                            (3, "habit", "habit"), (4, "home", "home")]},
    "iso_dup4":     {"spacing": 64, "segs": [(1, "home", "home"), (2, "project", "project"),
                                            (3, "habit", "habit"), (4, "project2", "project")]},
    "iso_habit_bot":{"spacing": 64, "segs": [(1, "home", "home"), (2, "project", "project"),
                                            (3, "habit", "habit"), (4, "habit2", "habit")]},
    "iso_car_mid":  {"spacing": 64, "segs": [(1, "home", "home"), (2, "car", "car"),
                                            (3, "habit", "habit"), (4, "project", "project")]},
    "iso_home_only": {"spacing": 64, "segs": [(1, "home", "home")]},
    "iso_habit_only": {"spacing": 64, "segs": [(1, "habit", "habit")]},
    "iso_dup_p3":   {"spacing": 64, "segs": [(1, "home", "home"), (2, "habit", "habit"),
                                            (3, "project", "project"), (4, "project2", "project")]},
    "iso_dup_p2":   {"spacing": 64, "segs": [(1, "home", "home"), (2, "habit", "habit"),
                                            (3, "project", "project"), (4, "habit2", "habit")]},
    "iso_topgap":   {"spacing": 64, "segs": [(2, "home", "home"), (3, "project", "project"),
                                            (4, "habit", "habit"), (5, "car", "car")]},
}


def build_layout(key, manifest):
    spec = LAYOUTS[key]
    m2 = manifest["blocks"]["m2"]
    segs, order = [], []
    for slot, sid, bid in spec["segs"]:
        b = m2[bid]
        n = b["cells"]
        lo = P.CHAT - (slot - 1) * spec["spacing"] - n
        segs.append({"id": sid, "block": "m2", "block_id": bid, "file": b["path"],
                     "file_sha256": b["sha256"], "cells": n, "slot": slot,
                     "pos_lo": lo, "pos_hi": lo + n, "add_order": len(order) + 1})
        order.append(sid)
    return {"key": key, "segments": segs,
            "add_order": spec.get("add_order", order),
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
                and hashlib.sha256(c["text"].encode("utf-8")).hexdigest() == c["sha256"]
                and P.measure(eng, c["text"]) == c["target_n"]):
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


def ask_native(eng, seq, question, pos, n_predict):
    """Same call path as kvslots.KVEngine.ask, but keeps the native return value."""
    buf = ctypes.create_string_buffer(8192)
    t = P.K.turn(question).encode("utf-8")
    n = int(eng.lib.kvshim_ask_at(eng.h, seq, t, pos, n_predict, buf, 8192))
    ans = "" if n < 0 else buf.value.decode("utf-8", "replace")
    return n, ans


def n_tokens(eng, seq):
    return int(eng.lib.kvshim_n_tokens(eng.h, seq))


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
        raise SystemExit("target %s not in %s (%s)" % (a.target, a.layout, ids))
    t0 = time.time()
    res = {"schema": "iso_run_v2", "experiment": a.layout, "target": a.target,
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "layout_key": a.layout,
           "spacing": LAYOUTS[a.layout]["spacing"], "seg_ids": ids,
           "add_order": layout["add_order"], "control_ok": False, "attributable": False}
    eng = P.open_engine()
    try:
        eng.lib.kvshim_n_tokens.argtypes = [ctypes.c_void_p, ctypes.c_int]
        eng.lib.kvshim_n_tokens.restype = ctypes.c_int
        res["engine"] = {"n_ctx": P.N_CTX, "n_seq": P.N_SEQ, "kv": P.KV, "gpu": P.GPU,
                         "dll_sha256": manifest["engine"]["dll_sha256"]}
        for bid, meta in manifest["blocks"]["m2"].items():
            if P.sha256_file(meta["path"]) != meta["sha256"]:
                raise RuntimeError("pristine block hash changed: %s" % meta["path"])
        P.reset_all(eng)
        ctexts = get_control(eng, a.layout, layout)
        ok, ctrl = P.run_control(eng, layout, a.layout, ctexts, P.FULL, CONTROL_ORDER)
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
                         "head_gap_cells": (P.CHAT - 1) - (layout["span_hi"] - 1),
                         "segments": [{"id": s["id"], "block_id": s["block_id"],
                                       "slot": s["slot"], "pos_lo": s["pos_lo"],
                                       "pos_hi": s["pos_hi"], "cells": s["cells"]}
                                      for s in layout["segments"]]}
        res["raw"] = {"live_pos_max_raw": raw, "cell_count": cnt,
                      "coverage": P.coverage(positions, layout),
                      "overlaps": P.overlaps(layout),
                      "positions_min": positions[0] if positions else None,
                      "positions_max": positions[-1] if positions else None}
        seg = next(s for s in layout["segments"] if s["id"] == a.target)
        q = P.FULL[seg["block_id"]]["q"]
        fact = P.FULL[seg["block_id"]]["fact"]
        eng.reset(P.LIVE)
        P.share_layout(eng, layout, placed)
        before_raw = P.raw_pos_max(eng, P.LIVE)
        before_ntok = n_tokens(eng, P.LIVE)
        n_bytes, ans = ask_native(eng, P.LIVE, q, P.CHAT, P.N_PREDICT)
        after_ntok = n_tokens(eng, P.LIVE)
        res["answers"] = [{"segment": a.target, "block_id": seg["block_id"],
                           "slot": seg["slot"], "pos_lo": seg["pos_lo"],
                           "pos_hi": seg["pos_hi"], "cells": seg["cells"],
                           "raw_pos_max_before_ask": before_raw,
                           "kvshim_n_tokens_before_ask": before_ntok,
                           "kvshim_n_tokens_after_ask": after_ntok,
                           "kvshim_ask_at_return_bytes": n_bytes,
                           "answer_len": len(ans),
                           "question": q, "expected": fact, "answer": ans.strip(),
                           "ok": bool(P.fact_ok(fact, ans))}]
        res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        res["elapsed_s"] = round(time.time() - t0, 2)
        P._write_json(a.run_json, res)
        print("%s/%s -> %s bytes=%d ntok=%d->%d %r" % (
            a.layout, a.target, "OK" if res["answers"][0]["ok"] else "MISS",
            n_bytes, before_ntok, after_ntok, ans.strip()[:40]))
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