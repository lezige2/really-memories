# -*- coding: utf-8 -*-
"""T-032 runner: one fresh engine per process, blocks placed top-aligned at CHAT=4096.

Arms are DATA (slot, seg id, kvmem path, cells).  Nothing about geometry is recomputed
from a different rule: lo = CHAT - (slot-1)*64 - cells, the same _driver2.build_layout
uses, so slot 1 always lands on [CHAT-cells, CHAT) with head gap 0.

Every run records, per segment: file, file sha16 (raw bytes), cells from the header,
first token id + is_bos (header parse, tools/block_info.py rule), and the geometry the
engine actually reports back (raw pos_max, cell_scan count, per-segment coverage).
The answer records the native kvshim_ask_at return (rc) and the sha256 of the answer.

Usage:
  python -X utf8 kvmem/m2_visibility/t032_run.py --arm F_pp18 \
      --run-json kvmem/m2_visibility/runs_t032/t032_f_r1.json
"""
import argparse
import ctypes
import hashlib
import json
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P      # noqa: E402

T032 = os.path.join(P.WORK_DIR, "runs_t032")
CTRL_CACHE = os.path.join(T032, "control_texts.json")
CONTROL_ORDER = ["home", "project", "habit", "car"]
BOS = 151646
HEADER, STRIDE = 708, 30480

M2 = {"home": None, "project": None, "habit": None, "car": None}
PP18 = os.path.join(P.BLOCK_DIR, "project_paraphrase18.kvmem")
HABIT4 = os.path.join(ROOT, "kvmem", "m2_v1", "habit.kvmem")
HABIT_PARA12 = os.path.join(ROOT, "kvmem", "m2_v1", "habit_para12.kvmem")
FILLER_BOS21 = os.path.join(ROOT, "kvmem", "m2_v1", "filler_bos_c21.kvmem")
G_BOS18 = os.path.join(ROOT, "kvmem", "m2_v1", "G_bos_c18.kvmem")

# arm -> (segments, asked seg id, fact family for the expected answer)
ARMS = {
    # task 1: the failing F configuration, re-run
    "F_pp18": {"segs": [(1, "home", "m2:home", 21), (2, "project", "m2:project", 18),
                        (3, "habit", "m2:habit", 12), (4, "pp18", "f:" + PP18, 18)],
               "target": "home", "q_from": "home"},
    # task 2: project removed, habit and pp18 stay at their F positions (only project gone)
    "P_pp18_only": {"segs": [(1, "home", "m2:home", 21), (3, "habit", "m2:habit", 12),
                             (4, "pp18", "f:" + PP18, 18)],
                    "target": "home", "q_from": "home"},
    # task 3: H pair, identical 12-cell position, only the wording differs
    "H1_habit4": {"segs": [(1, "home", "m2:home", 21), (2, "project", "m2:project", 18),
                           (3, "habit", "m2:habit", 12), (4, "habit2", "f:" + HABIT4, 12)],
                  "target": "home", "q_from": "home"},
    "H2_habitpara12": {"segs": [(1, "home", "m2:home", 21), (2, "project", "m2:project", 18),
                                (3, "habit", "m2:habit", 12),
                                (4, "habit2", "f:" + HABIT_PARA12, 12)],
                       "target": "home", "q_from": "home"},
    # task 4: negative control -- a neutral 21-cell block (WITH BOS) in home's slot
    "NEG_filler_bos21": {"segs": [(1, "home", "f:" + FILLER_BOS21, 21),
                                  (2, "project", "m2:project", 18),
                                  (3, "habit", "m2:habit", 12),
                                  (4, "car", "m2:car", 19)],
                         "target": "home", "q_from": "home"},
}


def file_info(path):
    """tools/block_info.py rule: header parse, zero engine."""
    raw = open(path, "rb").read()
    n = struct.unpack("<i", raw[8:12])[0]
    toks = struct.unpack("<%di" % n, raw[12:12 + 4 * n])
    cells_size, rem = divmod(len(raw) - HEADER, STRIDE)
    return {"path": os.path.abspath(path), "name": os.path.basename(path),
            "cells": n, "cells_from_size": cells_size, "size_rem": rem,
            "size": len(raw), "first_token": int(toks[0]), "is_bos": int(toks[0]) == BOS,
            "content_tokens": n - 1 if int(toks[0]) == BOS else n,
            "sha16": hashlib.sha256(raw).hexdigest()[:16],
            "sha256": hashlib.sha256(raw).hexdigest()}


def resolve(spec, man):
    kind, _, rest = spec.partition(":")
    if kind == "m2":
        return man["blocks"]["m2"][rest]["path"]
    if kind == "f":
        return rest
    raise RuntimeError("bad block spec %r" % spec)


def build_layout(arm, man):
    segs, order = [], []
    for slot, sid, spec, cells in ARMS[arm]["segs"]:
        path = resolve(spec, man)
        n = file_info(path)["cells"]
        if n != cells:
            raise RuntimeError("fixture changed: %s has %d cells, arm says %d"
                               % (path, n, cells))
        lo = P.CHAT - (slot - 1) * P.SLOT - n
        segs.append({"id": sid, "block": "m2" if spec.startswith("m2:") else "file",
                     "file": path, "cells": n, "slot": slot, "pos_lo": lo, "pos_hi": lo + n,
                     "info": file_info(path)})
        order.append(sid)
    return {"key": arm, "segments": segs, "add_order": order, "spacing": P.SLOT,
            "start": min(s["pos_lo"] for s in segs),
            "cells_total": sum(s["cells"] for s in segs),
            "span_lo": min(s["pos_lo"] for s in segs),
            "span_hi": max(s["pos_hi"] for s in segs)}


def get_control(eng, key, layout):
    cache = {}
    if os.path.exists(CTRL_CACHE):
        cache = json.load(open(CTRL_CACHE, encoding="utf-8"))
    target_n = P.CHAT - layout["start"]
    ck = "n%d" % target_n
    if ck in cache:
        c = cache[ck]
        if (c["start"] == layout["start"]
                and hashlib.sha256(c["text"].encode("utf-8")).hexdigest() == c["sha256"]
                and P.measure(eng, c["text"]) == target_n):
            return {key: c}
    prefix = "".join(P.FULL[sid]["text"] for sid in CONTROL_ORDER)
    text = P.build_exact_text(eng, prefix, target_n)
    n = P.measure(eng, text)
    if n != target_n or layout["start"] + n - 1 != P.CHAT - 1:
        raise RuntimeError("control text %d tokens, need %d" % (n, target_n))
    c = {"start": layout["start"], "target_n": target_n, "text": text, "measured_n": n,
         "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
         "prefix_order": CONTROL_ORDER}
    cache[ck] = c
    os.makedirs(T032, exist_ok=True)
    json.dump(cache, open(CTRL_CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return {key: c}


def ask_native(eng, seq, question, pos, n_predict):
    buf = ctypes.create_string_buffer(8192)
    t = P.K.turn(question).encode("utf-8")
    n = int(eng.lib.kvshim_ask_at(eng.h, seq, t, pos, n_predict, buf, 8192))
    return n, ("" if n < 0 else buf.value.decode("utf-8", "replace"))


def n_tokens(eng, seq):
    return int(eng.lib.kvshim_n_tokens(eng.h, seq))


def one_answer(eng, layout, placed, q, fact, ask_pos):
    """reset(LIVE) + re-share, so no answer inherits the previous decode."""
    eng.reset(P.LIVE)
    P.share_layout(eng, layout, placed)
    before_raw = P.raw_pos_max(eng, P.LIVE)
    before_ntok = n_tokens(eng, P.LIVE)
    rc, ans = ask_native(eng, P.LIVE, q, ask_pos, P.N_PREDICT)
    after_ntok = n_tokens(eng, P.LIVE)
    stripped = ans.strip()
    return {"question": q, "expected": fact, "ask_pos": ask_pos,
            "raw_pos_max_before_ask": before_raw,
            "kvshim_n_tokens_before_ask": before_ntok,
            "kvshim_n_tokens_after_ask": after_ntok,
            "rc": rc, "answer_len": len(stripped), "answer": stripped,
            "answer_sha256": hashlib.sha256(stripped.encode("utf-8")).hexdigest(),
            "answer_sha16": hashlib.sha256(stripped.encode("utf-8")).hexdigest()[:16],
            "ok": bool(P.fact_ok(fact, stripped))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--run-json", required=True)
    a = ap.parse_args()
    man = P.load_manifest()
    layout = build_layout(a.arm, man)
    spec = ARMS[a.arm]
    if spec["target"] not in [s["id"] for s in layout["segments"]]:
        raise SystemExit("target %s not in %s" % (spec["target"], a.arm))
    t0 = time.time()
    res = {"schema": "t032_run_v1", "arm": a.arm, "target": spec["target"],
           "q_from": spec["q_from"], "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "argv": sys.argv, "control_ok": False, "attributable": False,
           "engine": {"dll_sha256": man["engine"]["dll_sha256"], "n_ctx": P.N_CTX,
                      "n_seq": P.N_SEQ, "kv": P.KV, "gpu": P.GPU,
                      "model_mtime": man["engine"]["model_mtime"], "pid": os.getpid()}}
    eng = P.open_engine()
    try:
        eng.lib.kvshim_n_tokens.argtypes = [ctypes.c_void_p, ctypes.c_int]
        eng.lib.kvshim_n_tokens.restype = ctypes.c_int
        eng.lib.kvshim_ask_at.restype = ctypes.c_int
        P.reset_all(eng)
        ctexts = get_control(eng, a.arm, layout)
        ok, ctrl = P.run_control(eng, layout, a.arm, ctexts, P.FULL, CONTROL_ORDER)
        res["control"] = ctrl
        res["control_ok"] = bool(ok)
        res["attributable"] = bool(ok)
        if not ok:
            res["failure"] = "CONTROL GATE FAILED -- not interpreted"
            P._write_json(a.run_json, res)
            print("CONTROL FAILED %s" % a.arm)
            return 3
        P.reset_all(eng)
        placed = P.load_and_place(eng, layout)
        P.share_layout(eng, layout, placed)
        raw = P.raw_pos_max(eng, P.LIVE)
        cnt, positions = P.cell_scan(eng, P.LIVE)
        cov = P.coverage(positions, layout)
        res["layout"] = {"key": a.arm, "start": layout["start"],
                         "cells_total": layout["cells_total"],
                         "span_lo": layout["span_lo"], "span_hi": layout["span_hi"],
                         "gap_top": (P.CHAT - 1) - (positions[-1] if positions else -1),
                         "segments": [{"id": s["id"], "slot": s["slot"],
                                       "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"],
                                       "cells": s["cells"], "file": s["info"]["path"],
                                       "file_sha16": s["info"]["sha16"],
                                       "file_sha256": s["info"]["sha256"],
                                       "first_token": s["info"]["first_token"],
                                       "is_bos": s["info"]["is_bos"],
                                       "content_tokens": s["info"]["content_tokens"]}
                                      for s in layout["segments"]]}
        res["placed"] = placed
        res["raw"] = {"live_pos_max_raw": raw, "cells_on_live": cnt,
                      "coverage": cov, "overlaps": P.overlaps(layout),
                      "positions_min": positions[0] if positions else None,
                      "positions_max": positions[-1] if positions else None,
                      "ask_pos": P.CHAT}
        q = P.FULL[spec["q_from"]]["q"]
        fact = P.FULL[spec["q_from"]]["fact"]
        res["answers"] = [one_answer(eng, layout, placed, q, fact, P.CHAT)]
        res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        res["elapsed_s"] = round(time.time() - t0, 2)
        P._write_json(a.run_json, res)
        ans = res["answers"][0]
        print("%s -> %s rc=%d ok=%s sha16=%s len=%d" % (
            a.arm, "OK" if ans["ok"] else "MISS", ans["rc"], ans["ok"],
            ans["answer_sha16"], ans["answer_len"]))
        print("  loaded: " + " | ".join("%s[%d]=%s(%d,%s,%s)" % (
            s["id"], s["slot"], s["info"]["name"], s["cells"],
            s["info"]["first_token"], "BOS" if s["info"]["is_bos"] else "NOBOS")
            for s in layout["segments"]))
        print("  geom: cells_on_live=%d pos_max=%s gap_top=%s ask_pos=%s home_cov=%s"
              % (cnt, res["raw"]["positions_max"], res["layout"]["gap_top"],
                 P.CHAT, cov.get("home")))
        print("  answer: %r" % ans["answer"])
        return 0
    except Exception as exc:                                    # noqa: BLE001
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
