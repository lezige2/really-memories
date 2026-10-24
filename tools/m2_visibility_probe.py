# -*- coding: utf-8 -*-
"""m2_visibility_probe.py -- attributable fixture for the 4-shared-segment visibility bug.

Why this file exists
--------------------
The previous visibility probe (tools/m2_probe_segments.py and the ad-hoc runs recorded in
STATUS-REPORT.md) reused one engine across arms and built its "text control" out of
position-gapped write_at calls without BOS.  llama_decode wants consecutive positions, so
that control was not a control at all: a MISS could not be attributed to the engine.

This probe fixes the fixture, not the engine:

  * ONE FRESH ENGINE PER ARM.  Each arm is executed by a separate OS process
    (`--arm ... --run-json ...`); the parent driver only spawns subprocesses and never
    opens an engine itself.  No engine is shared between arms.
  * PRISTINE BLOCK FILES ONLY.  Every arm reloads its blocks from a read-only .kvmem
    file that is hash-verified against the fixture manifest.  Nothing ever writes back
    into a block file after setup.
  * THE CONTROL GATE RUNS FIRST, IN EVERY ARM PROCESS.  The control is ONE contiguous
    text, written from the layout's lowest position with add_bos=True on the first token
    only (a single write call), padded with neutral filler so that the last memory
    position is exactly CHAT-1=4095, then asked at CHAT=4096.  No gapped write_at, no
    seq_cp, no BOS re-insertion.  If any control question fails, the process stops and
    reports a fixture failure: segment results from a process whose control failed are
    never interpreted.
  * RAW ACCESSORS ONLY FOR THE CACHE.  `kvshim_pos_max` returns -1 for a seq_cp-built
    sequence (share copies cell refs, not tokens[]), so it cannot testify.  All cache
    readings here use `kvshim_seq_pos_max_raw` and `kvshim_seq_cell_scan`, bound locally
    in this file (they are not part of tools/kvslots.py, and kvslots.py is not modified).

Arms
----
  CONTROL  : gate only, on the 4-segment layout (fresh process).
  A        : 4 shared segments, 70 cells (home/project/habit/car at their M2 B-right
             ranges), one question per segment, each question in its own fresh engine.
  B        : 3 shared segments, 79 cells total (to separate segment COUNT from total
             CELL count: 3 > 79 cells vs 4 < 70 cells).
  C        : 4 micro segments, 5 cells each (20 cells total).
  D_FWD    : 4 segments, forward add order (mount + share order home,project,habit,car).
  D_REV    : 4 segments, reversed add order (car,habit,project,home); each segment stays
             at the SAME position range, so "added first/last" is separated from
             "lowest/highest position".

Layout math (B-right, same as m2_v1.py)
    for block n tokens in logical slot s (1-based, slot 1 flush with the chat anchor):
        pos_lo = CHAT - (s-1)*SLOT - n ; pos_hi = pos_lo + n
    CHAT = 4096, SLOT = 64, engine n_ctx = 8192, n_seq = 8, kv = q8_0 (Vulkan build).

Usage
-----
    # one-time fixture setup (creates the B/C variant blocks + control texts manifest)
    python -X utf8 tools/m2_visibility_probe.py --arm setup

    # the pre-flight gate, in a clean process (must pass before the full run)
    python -X utf8 tools/m2_visibility_probe.py --arm CONTROL

    # one arm (always a fresh process)
    python -X utf8 tools/m2_visibility_probe.py --arm A --target home
    python -X utf8 tools/m2_visibility_probe.py --arm B
    python -X utf8 tools/m2_visibility_probe.py --arm C
    python -X utf8 tools/m2_visibility_probe.py --arm D_FWD
    python -X utf8 tools/m2_visibility_probe.py --arm D_REV

    # everything, with the report (spawns each of the above as a subprocess)
    python -X utf8 tools/m2_visibility_probe.py --arm ALL

Do NOT modify m2_v1.py, the engine C++, retrievals, analysis or evidence from here.
"""
import argparse
import ctypes
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import kvslots as K                                          # noqa: E402

MODEL = os.path.join(r"D:\models", "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf")
M2_DIR = os.path.join(ROOT, "kvmem", "m2_v1")
WORK_DIR = os.path.join(ROOT, "kvmem", "m2_visibility")
BLOCK_DIR = os.path.join(WORK_DIR, "blocks")
RUN_DIR = os.path.join(WORK_DIR, "runs")
MANIFEST = os.path.join(WORK_DIR, "fixtures.json")
REPORT_MD = os.path.join(ROOT, "kvmem", "m2_visibility_report_v2.md")
REPORT_JSON = os.path.join(ROOT, "kvmem", "m2_visibility_report_v2.json")

CHAT = 4096
SLOT = 64
LIVE = 0            # the chat sequence
CTRL = 6            # the plain-text control sequence
PROBE = 7           # scratch sequence for kvshim_seq_cell_scan
N_SEQ = 8
N_CTX = 8192
GPU = 99
KV = "q8_0"
N_PREDICT = 24

# The four M2 statements / questions / expected facts (same as m2_v1.FACT_Q).
FULL = {
    "home": {"text": "我住在广陵路 12 号 2 单元 602。",
             "q": "我住在哪？", "fact": "广陵路"},
    "project": {"text": "项目代号蓝鲸，计划 3 月 14 日上线。",
                "q": "项目什么时候上线？", "fact": "3月14"},
    "habit": {"text": "我的咖啡只喝美式，不加糖。",
              "q": "我喝咖啡有什么习惯？", "fact": "美式"},
    "car": {"text": "我的车牌是 浙B-3F19K，深灰色速腾。",
            "q": "我的车牌号是多少？", "fact": "浙B-3F19K"},
}

# 5-cell micro blocks (exactly 5 tokens including the one BOS).  Each carries only the
# fragment of the fact that fits in 4 content tokens, so the micro arm asks the micro
# question; the control text is always the four FULL statements.
MICRO = {
    "home": {"text": "广陵路。", "q": "我住在哪？", "fact": "广陵路", "cells": 5},
    "project": {"text": "项目蓝鲸。", "q": "项目代号是什么？", "fact": "蓝鲸", "cells": 5},
    "habit": {"text": "我的美式。", "q": "我喝什么咖啡？", "fact": "美式", "cells": 5},
    "car": {"text": "我的速腾。", "q": "我的车是什么牌子？", "fact": "速腾", "cells": 5},
}

# Neutral filler used only for padding.  Measured content lengths at build time, never
# assumed.
FILLER_UNITS = [
    "另外，还有一些和问题无关的日常记录。",
    "今天天气一般。",
    "。我", "。今", "。记", "了",
]

# 3-segment variant: 31 + 28 + 20 = 79 cells total.
B3_TEXTS = {
    "home": FULL["home"]["text"] + "另外，还有一些和问题无关的日常记录。",          # 31
    "project": FULL["project"]["text"] + "另外，还有一些和问题无关的日常记录。",    # 28
    "habit": FULL["habit"]["text"] + "今天天气一般。" * 2,                          # 20
}
B3_Q = {
    "home": {"q": FULL["home"]["q"], "fact": FULL["home"]["fact"]},
    "project": {"q": FULL["project"]["q"], "fact": FULL["project"]["fact"]},
    "habit": {"q": FULL["habit"]["q"], "fact": FULL["habit"]["fact"]},
}


def log(msg):
    print(msg, flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s):
    return "".join((s or "").split())


def fact_ok(fact, ans):
    if not fact:
        return False
    return norm(fact) in norm(ans)


# --------------------------------------------------------------------- engine helpers

def open_engine():
    eng = K.KVEngine(MODEL, n_ctx=N_CTX, n_seq=N_SEQ, gpu=GPU, kv=KV)
    bind_raw(eng)
    return eng


def bind_raw(eng):
    """Bind the read-only raw accessors locally.  kvslots.py is deliberately untouched:
    these are test-side probes, not product API."""
    L = eng.lib
    L.kvshim_seq_pos_max_raw.argtypes = [ctypes.c_void_p, ctypes.c_int]
    L.kvshim_seq_pos_max_raw.restype = ctypes.c_int
    L.kvshim_seq_cell_scan.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                       ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    L.kvshim_seq_cell_scan.restype = ctypes.c_int


def raw_pos_max(eng, seq):
    return int(eng.lib.kvshim_seq_pos_max_raw(eng.h, seq))


def cell_scan(eng, seq):
    cap = N_CTX
    buf = (ctypes.c_int * cap)()
    n = int(eng.lib.kvshim_seq_cell_scan(eng.h, seq, PROBE, buf, cap))
    return n, sorted(int(buf[i]) for i in range(max(n, 0)))


def reset_all(eng):
    for s in range(N_SEQ):
        eng.reset(s)


def measure(eng, text):
    """Token count of `text` with BOS, measured by actually encoding it in the control
    sequence (never estimated from character counts)."""
    eng.reset(CTRL)
    n = eng.write(CTRL, text, add_bos=True)
    eng.reset(CTRL)
    if n < 1:
        raise RuntimeError("tokenization failed for %r" % text[:40])
    return n


def build_exact_text(eng, prefix, target_n, units=None):
    """Return prefix + neutral padding whose measured token count is exactly target_n.

    Tokenization is context sensitive at chunk boundaries, so every candidate append is
    verified by measuring the whole string; nothing is assumed additive.
    """
    units = list(units or FILLER_UNITS)
    text = prefix
    n = measure(eng, text)
    if n > target_n:
        raise RuntimeError("prefix already %d tokens > target %d" % (n, target_n))
    lens = [(u, measure(eng, u) - 1) for u in units]      # content tokens per unit
    lens.sort(key=lambda pair: -pair[1])
    steps = 0
    while n != target_n:
        steps += 1
        if steps > 600:
            raise RuntimeError("cannot hit exact token count %d (at %d)" % (target_n, n))
        progressed = False
        for unit, _cl in lens:
            if not unit:
                continue
            trial = text + unit
            m = measure(eng, trial)
            if n < m <= target_n:
                text, n, progressed = trial, m, True
                break
        if not progressed:
            raise RuntimeError("no filler unit advances token count toward %d (at %d)"
                               % (target_n, n))
    return text


# --------------------------------------------------------------------- fixtures/setup

def layout_specs(manifest_blocks):
    """Static layout definitions.  Positions are derived at setup time from the actual
    block cell counts (never hard-coded guesses)."""
    m2 = {sid: {"block": "m2", "id": sid} for sid in ("home", "project", "habit", "car")}
    b3 = {sid: {"block": "variant", "id": "b_" + sid} for sid in ("home", "project", "habit")}
    micro = {sid: {"block": "variant", "id": "c_" + sid} for sid in MICRO}
    return {
        "m2_fwd": {"segments": m2, "slots": {"home": 1, "project": 2, "habit": 3, "car": 4},
                   "add_order": ["home", "project", "habit", "car"],
                   "control_order": ["home", "project", "habit", "car"],
                   "questions": FULL},
        "m2_rev": {"segments": m2, "slots": {"home": 1, "project": 2, "habit": 3, "car": 4},
                   "add_order": ["car", "habit", "project", "home"],
                   "control_order": ["car", "habit", "project", "home"],
                   "questions": FULL},
        "b3": {"segments": b3, "slots": {"home": 1, "project": 2, "habit": 3},
               "add_order": ["home", "project", "habit"],
               "control_order": ["home", "project", "habit", "car"],
               "questions": B3_Q},
        "micro": {"segments": micro, "slots": {"home": 1, "project": 2, "habit": 3, "car": 4},
                  "add_order": ["home", "project", "habit", "car"],
                  "control_order": ["home", "project", "habit", "car"],
                  "questions": MICRO},
    }


def block_path(kind, bid):
    if kind == "m2":
        return os.path.join(M2_DIR, bid + ".kvmem")
    return os.path.join(BLOCK_DIR, bid + ".kvmem")


def run_setup():
    """Create the variant block files (once), verify all pristine inputs, derive the
    layouts and build the exact control texts.  One fresh engine; never reused by arms."""
    os.makedirs(BLOCK_DIR, exist_ok=True)
    os.makedirs(RUN_DIR, exist_ok=True)
    t_start = time.time()
    eng = open_engine()
    log("setup: engine open pid=%d" % os.getpid())
    try:
        # --- variant blocks: create only if absent, then always verify from disk
        variant = {}
        for sid, spec in MICRO.items():
            path = block_path("variant", "c_" + sid)
            n = None
            if os.path.exists(path):
                eng.reset(2)
                n = eng.load_strict(2, path)
                eng.reset(2)
                if n != spec["cells"]:
                    raise RuntimeError("%s has %d cells, expected %d" % (path, n, spec["cells"]))
                log("setup: keep existing micro block %s (%d cells)" % (os.path.basename(path), n))
            else:
                eng.reset(2)
                n = eng.write(2, spec["text"], add_bos=True)
                if n != spec["cells"]:
                    raise RuntimeError("micro text %r encoded to %d tokens, expected %d"
                                       % (spec["text"], n, spec["cells"]))
                written = eng.save(2, path)
                eng.reset(2)
                if written <= 0:
                    raise RuntimeError("failed to save %s" % path)
                log("setup: created micro block %s (%d cells)" % (os.path.basename(path), n))
            variant["c_" + sid] = {"path": path, "cells": n, "sha256": sha256_file(path),
                                   "text": spec["text"], "source": "created for micro arm"}
        for sid, text in B3_TEXTS.items():
            path = block_path("variant", "b_" + sid)
            n = None
            if os.path.exists(path):
                eng.reset(2)
                n = eng.load_strict(2, path)
                eng.reset(2)
                log("setup: keep existing 3-seg block %s (%d cells)" % (os.path.basename(path), n))
            else:
                eng.reset(2)
                n = eng.write(2, text, add_bos=True)
                written = eng.save(2, path)
                eng.reset(2)
                if written <= 0:
                    raise RuntimeError("failed to save %s" % path)
                log("setup: created 3-seg block %s (%d cells)" % (os.path.basename(path), n))
            variant["b_" + sid] = {"path": path, "cells": n, "sha256": sha256_file(path),
                                   "text": text, "source": "created for 3-segment arm"}

        # --- M2 pristine blocks: verify from disk, never rewrite
        m2 = {}
        for sid in ("home", "project", "habit", "car"):
            path = block_path("m2", sid)
            if not os.path.exists(path):
                raise RuntimeError("missing M2 pristine block %s" % path)
            eng.reset(2)
            n = eng.load_strict(2, path)
            eng.reset(2)
            m2[sid] = {"path": path, "cells": n, "sha256": sha256_file(path),
                       "source": "M2 pristine block (m2_v1 mount fixture)"}
            log("setup: verified M2 block %-8s %2d cells %s" % (sid, n, path))
        expected_m2 = {"home": 21, "project": 18, "habit": 12, "car": 19}
        bad = {k: (v["cells"], expected_m2[k]) for k, v in m2.items()
               if v["cells"] != expected_m2[k]}
        if bad:
            raise RuntimeError("M2 pristine block cell counts changed: %s" % bad)

        # --- derive layouts (positions from the real cell counts)
        blocks = {"m2": m2, "variant": variant}
        layouts = {}
        for key, spec in layout_specs(blocks).items():
            segs = []
            for sid in spec["add_order"]:
                b = blocks[spec["segments"][sid]["block"]][spec["segments"][sid]["id"]]
                slot = spec["slots"][sid]
                n = b["cells"]
                lo = CHAT - (slot - 1) * SLOT - n
                segs.append({"id": sid, "block": spec["segments"][sid]["block"],
                             "block_id": spec["segments"][sid]["id"], "file": b["path"],
                             "file_sha256": b["sha256"], "cells": n, "slot": slot,
                             "pos_lo": lo, "pos_hi": lo + n,
                             "add_order": spec["add_order"].index(sid) + 1})
            total = sum(s["cells"] for s in segs)
            layouts[key] = {
                "key": key, "segments": segs,
                "add_order": spec["add_order"],
                "control_order": spec["control_order"],
                "start": min(s["pos_lo"] for s in segs),
                "cells_total": total,
                "span_lo": min(s["pos_lo"] for s in segs),
                "span_hi": max(s["pos_hi"] for s in segs),
            }

        # --- build the exact control text per layout/order
        control_texts = {}
        for key, lay in layouts.items():
            target_n = CHAT - lay["start"]
            order = lay["control_order"]
            prefix = "".join(FULL[sid]["text"] for sid in order)
            t0 = time.time()
            text = build_exact_text(eng, prefix, target_n)
            n_meas = measure(eng, text)
            if n_meas != target_n or lay["start"] + n_meas - 1 != CHAT - 1:
                raise RuntimeError("control text for %s: %d tokens, need %d"
                                   % (key, n_meas, target_n))
            control_texts[key] = {
                "start": lay["start"], "target_n": target_n,
                "text": text, "measured_n": n_meas,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "prefix_order": order,
            }
            log("setup: control[%s] start=%d target=%d measured=%d text_sha=%s (%.1fs)"
                % (key, lay["start"], target_n, n_meas,
                   control_texts[key]["sha256"][:16], time.time() - t0))

        manifest = {
            "schema": "m2_visibility_fixtures_v1",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "project_root": ROOT,
            "engine": {"model": MODEL, "model_size": os.path.getsize(MODEL),
                       "model_mtime": os.path.getmtime(MODEL),
                       "n_ctx": N_CTX, "n_seq": N_SEQ, "gpu": GPU, "kv": KV,
                       "dll": os.path.join(HERE, "kvshim_vk.dll"),
                       "dll_sha256": sha256_file(os.path.join(HERE, "kvshim_vk.dll"))},
            "constants": {"CHAT": CHAT, "SLOT": SLOT, "LIVE": LIVE,
                          "CTRL": CTRL, "PROBE": PROBE},
            "blocks": blocks,
            "layouts": layouts,
            "control_texts": control_texts,
        }
        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        log("setup: manifest -> %s (%.1fs)" % (MANIFEST, time.time() - t_start))
        return 0
    finally:
        eng.close()


def load_manifest(require=True):
    if not os.path.exists(MANIFEST):
        if require:
            raise RuntimeError("missing %s -- run: python -X utf8 tools/m2_visibility_probe.py "
                               "--arm setup" % MANIFEST)
        return None
    with open(MANIFEST, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------- layout / control

def load_and_place(eng, layout):
    """Load every block fresh from its pristine file and place it at its B-right range.
    Verifies cell count and final position against the manifest."""
    placed = []
    by_slot = {}
    for sid in layout["add_order"]:
        seg = next(s for s in layout["segments"] if s["id"] == sid)
        slot = seg["slot"]
        eng.reset(slot)
        n = eng.load_strict(slot, seg["file"])
        if n != seg["cells"]:
            raise RuntimeError("fixture changed: %s loaded %d cells, manifest says %d"
                               % (seg["file"], n, seg["cells"]))
        base = eng.pos_max(slot) - n + 1
        target = seg["pos_lo"]
        moved = eng.repos_local(slot, target - base)
        if moved != n:
            raise RuntimeError("repos_local moved %d of %d for %s" % (moved, n, sid))
        pm = eng.pos_max(slot)
        if pm != seg["pos_hi"] - 1:
            raise RuntimeError("%s pos_max=%d, expected %d" % (sid, pm, seg["pos_hi"] - 1))
        # base is the position the .kvmem carries in its own file; delta is the re-rotation
        # actually applied here. Neither is implied by the layout, and without them a product
        # cannot answer "was this block rotated, and by how much".
        placed.append({"id": sid, "slot": slot, "cells": n, "file": os.path.basename(seg["file"]),
                       "base": base, "delta": target - base,
                       "pos_lo": seg["pos_lo"], "pos_hi": seg["pos_hi"]})
        by_slot[slot] = sid
    return placed


def share_layout(eng, layout, placed):
    by_id = {p["id"]: p for p in placed}
    for sid in layout["add_order"]:
        p = by_id[sid]
        eng.share(p["slot"], LIVE, p["pos_lo"], p["pos_hi"])


def coverage(positions, layout):
    pset = set(positions)
    cov = {}
    for seg in layout["segments"]:
        have = sum(1 for p in range(seg["pos_lo"], seg["pos_hi"]) if p in pset)
        cov[seg["id"]] = {"lo": seg["pos_lo"], "hi": seg["pos_hi"],
                          "cells": seg["cells"], "covered": have}
    return cov


def overlaps(layout):
    segs = sorted((s["pos_lo"], s["pos_hi"], s["id"]) for s in layout["segments"])
    out = []
    for a, b in zip(segs, segs[1:]):
        if a[1] > b[0]:
            out.append([a[2], b[2]])
    return out


LAYOUT_QUESTIONS = {"m2_fwd": FULL, "m2_rev": FULL, "b3": B3_Q, "micro": MICRO}


def run_control(eng, layout, layout_key, control_texts, questions, gate_order):
    """The gate.  One contiguous text, one write call, BOS on the first token only,
    last memory position exactly 4095, question asked at 4096."""
    ctext = control_texts[layout_key]
    text = ctext["text"]
    start = ctext["start"]
    target_n = ctext["target_n"]
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != ctext["sha256"]:
        raise RuntimeError("control text sha256 mismatch (manifest corrupted?)")
    recs = []
    ok_all = True
    for sid in gate_order:
        q = questions[sid]["q"]
        fact = questions[sid]["fact"]
        eng.reset(CTRL)
        nw = eng.write_at(CTRL, text, start, add_bos=True)
        rawm = raw_pos_max(eng, CTRL)
        ans = ""
        reason = None
        if nw != target_n:
            reason = "wrote %d tokens, expected %d" % (nw, target_n)
            ok = False
        elif rawm != CHAT - 1:
            reason = "last memory position %d, expected %d" % (rawm, CHAT - 1)
            ok = False
        elif start + nw - 1 != CHAT - 1:
            reason = "end position %d, expected %d" % (start + nw - 1, CHAT - 1)
            ok = False
        else:
            ans = eng.ask(CTRL, q, n_predict=N_PREDICT, pos=CHAT)
            ok = fact_ok(fact, ans)
            if not ok:
                reason = "answer did not contain expected fact"
        recs.append({"segment": sid, "question": q, "expected": fact,
                     "answer": ans.strip(), "ok": bool(ok),
                     "wrote_n": nw, "raw_pos_max_before_ask": rawm, "reason": reason})
        ok_all = ok_all and bool(ok)
        eng.reset(CTRL)
    return ok_all, {"ok": bool(ok_all), "layout": layout_key, "start": start,
                    "target_n": target_n, "text_sha256": ctext["sha256"],
                    "text_len": len(text), "questions": recs}


# --------------------------------------------------------------------- arm execution

ARM_LAYOUT = {"CONTROL": "m2_fwd", "A": "m2_fwd", "B": "b3", "C": "micro",
              "D_FWD": "m2_fwd", "D_REV": "m2_rev"}
ARM_TARGETS = {"CONTROL": [], "A": ["home", "project", "habit", "car"],
               "B": ["home", "project", "habit"],
               "C": ["home", "project", "habit", "car"],
               "D_FWD": ["home", "project", "habit", "car"],
               "D_REV": ["home", "project", "habit", "car"]}


def engine_identity(eng, manifest):
    return {
        "pid": os.getpid(),
        "handle": int(eng.h) if eng.h else None,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "n_ctx": eng.n_ctx, "n_seq": eng.n_seq, "gpu": GPU, "kv": KV,
        "dll": manifest["engine"]["dll"],
        "dll_sha256": manifest["engine"]["dll_sha256"],
        "model": manifest["engine"]["model"],
        "model_size": manifest["engine"]["model_size"],
        "model_mtime": manifest["engine"]["model_mtime"],
        "fresh_process": True,
    }


def run_arm(arm, target, run_json, argv):
    if arm not in ARM_LAYOUT:
        raise SystemExit("unknown arm %r (choose CONTROL/A/B/C/D_FWD/D_REV/ALL)" % arm)
    manifest = load_manifest()
    layout_key = ARM_LAYOUT[arm]
    layout = manifest["layouts"][layout_key]
    t_start = time.time()
    result = {
        "schema": "m2_visibility_run_v1", "arm": arm, "target": target,
        "run_id": os.path.splitext(os.path.basename(run_json))[0],
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "argv": argv, "control_ok": False, "attributable": False,
        "layout_key": layout_key,
    }
    eng = open_engine()
    try:
        result["process"] = {"pid": os.getpid(), "fresh_process": True,
                             "cwd": os.getcwd(), "command": " ".join(argv)}
        result["engine"] = engine_identity(eng, manifest)
        log("arm=%s target=%s pid=%d engine=%s start=%.6f" %
            (arm, target, os.getpid(), hex(int(eng.h or 0)), time.time()))

        # ---- (0) verify all pristine inputs still hash-match the manifest, then reset
        for kind in ("m2", "variant"):
            for bid, meta in manifest["blocks"][kind].items():
                if sha256_file(meta["path"]) != meta["sha256"]:
                    raise RuntimeError("pristine block hash changed: %s" % meta["path"])
        reset_all(eng)

        # ---- (1) CONTROL GATE, always first, in this fresh engine
        gate_order = list(layout["add_order"])
        control_ok, control = run_control(eng, layout, layout_key,
                                          manifest["control_texts"],
                                          LAYOUT_QUESTIONS[layout_key], gate_order)
        result["control"] = control
        result["control_ok"] = bool(control_ok)
        result["attributable"] = bool(control_ok)
        log("arm=%s control_ok=%s" % (arm, control_ok))
        for rec in control["questions"]:
            log("  control %-8s %s q=%s ans=%r"
                % (rec["segment"], "PASS" if rec["ok"] else "FAIL", rec["question"],
                   rec["answer"][:40]))
        if not control_ok:
            result["failure"] = "CONTROL GATE FAILED -- fixture failure, segment results not interpreted"
            _write_json(run_json, result)
            log("arm=%s STOP: control gate failed; no segment interpretation" % arm)
            return 3

        # ---- (2) the arm proper: fresh reload of every pristine block, then share
        reset_all(eng)
        placed = load_and_place(eng, layout)
        share_layout(eng, layout, placed)
        raw_live = raw_pos_max(eng, LIVE)
        cnt, positions = cell_scan(eng, LIVE)
        cov = coverage(positions, layout)
        expect_cells = sum(s["cells"] for s in layout["segments"])
        result["layout"] = {
            "key": layout_key, "start": layout["start"], "cells_total": expect_cells,
            "span_lo": layout["span_lo"], "span_hi": layout["span_hi"],
            "add_order": layout["add_order"],
            "segments": [dict(s, file_sha256=s["file_sha256"][:16]) for s in layout["segments"]],
        }
        result["raw"] = {
            "live_pos_max_raw": raw_live,
            "expected_cells": expect_cells,
            "cell_count": cnt,
            "coverage": cov,
            "overlaps": overlaps(layout),
            "positions_min": positions[0] if positions else None,
            "positions_max": positions[-1] if positions else None,
        }
        log("  layout span [%d,%d) cells=%d raw_pos_max=%d scan=%d overlaps=%s"
            % (layout["span_lo"], layout["span_hi"], expect_cells, raw_live, cnt,
               overlaps(layout)))

        # ---- (3) per-segment asks, each from a freshly reset chat sequence
        answers = []
        targets = [target] if (arm == "A" and target) else ARM_TARGETS[arm]
        for sid in targets:
            seg = next(s for s in layout["segments"] if s["id"] == sid)
            q = LAYOUT_QUESTIONS[layout_key][sid]["q"]
            fact = LAYOUT_QUESTIONS[layout_key][sid]["fact"]
            eng.reset(LIVE)
            share_layout(eng, layout, placed)
            raw_before = raw_pos_max(eng, LIVE)
            ans = eng.ask(LIVE, q, n_predict=N_PREDICT, pos=CHAT)
            ok = fact_ok(fact, ans)
            answers.append({
                "segment": sid, "add_order": seg["add_order"], "slot": seg["slot"],
                "pos_lo": seg["pos_lo"], "pos_hi": seg["pos_hi"], "cells": seg["cells"],
                "raw_pos_max_before_ask": raw_before, "live_pos_max_raw": raw_before,
                "question": q, "expected": fact, "answer": ans.strip(), "ok": bool(ok),
            })
            log("  ask %-8s add=%d [%d,%d) cells=%d raw=%d -> %s %r"
                % (sid, seg["add_order"], seg["pos_lo"], seg["pos_hi"], seg["cells"],
                   raw_before, "OK" if ok else "MISS", ans.strip()[:40]))
        result["answers"] = answers
        result["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        result["elapsed_s"] = round(time.time() - t_start, 2)
        _write_json(run_json, result)
        log("arm=%s done in %.1fs -> %s" % (arm, result["elapsed_s"], run_json))
        return 0
    except Exception as exc:                                   # noqa: BLE001
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
        result["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _write_json(run_json, result)
        log("arm=%s ERROR: %s" % (arm, exc))
        return 4
    finally:
        eng.close()


def _write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------- driver + report

def spawn(args, log_path):
    cmd = [sys.executable, "-X", "utf8", os.path.abspath(__file__)] + args
    t0 = time.time()
    with open(log_path, "w", encoding="utf-8", errors="replace") as lf:
        lf.write("COMMAND: %s\n" % subprocess.list2cmdline(cmd))
        lf.flush()
        proc = subprocess.run(cmd, cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT,
                              timeout=1800)
    return proc.returncode, time.time() - t0, cmd


def arm_run_path(arm, target):
    name = arm if not target else "%s_%s" % (arm, target)
    return os.path.join(RUN_DIR, name + ".json")


def read_run(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_all():
    os.makedirs(RUN_DIR, exist_ok=True)
    logs = {}
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    t_all = time.time()

    # 1) fixture setup in its own fresh process (one engine, never reused by arms)
    rc, dt, cmd = spawn(["--arm", "setup"], os.path.join(RUN_DIR, "setup.log"))
    logs["setup"] = {"rc": rc, "seconds": round(dt, 2), "command": subprocess.list2cmdline(cmd)}
    log("driver: setup rc=%d (%.1fs)" % (rc, dt))
    if rc != 0:
        return _finish_fixture_failure(logs, "fixture setup process failed (rc=%d)" % rc)
    manifest = load_manifest()

    # 2) THE GATE: single clean CONTROL process
    rc, dt, cmd = spawn(["--arm", "CONTROL"],
                        os.path.join(RUN_DIR, "CONTROL.log"))
    control_run = read_run(arm_run_path("CONTROL", None))
    logs["CONTROL"] = {"rc": rc, "seconds": round(dt, 2),
                       "command": subprocess.list2cmdline(cmd)}
    log("driver: CONTROL rc=%d control_ok=%s" % (rc, (control_run or {}).get("control_ok")))
    if rc != 0 or not control_run or not control_run.get("control_ok"):
        return _finish_fixture_failure(
            logs, "CONTROL gate failed in a clean process (rc=%d); fixture failure -- "
                  "segment results are NOT interpreted" % rc, control_run=control_run)

    # 3) arms, each in its own subprocess -> own fresh engine
    runs = [("CONTROL", None, control_run)]
    plan = [("A", "home"), ("A", "project"), ("A", "habit"), ("A", "car"),
            ("B", None), ("C", None), ("D_FWD", None), ("D_REV", None)]
    for arm, target in plan:
        path = arm_run_path(arm, target)
        if os.path.exists(path):
            os.remove(path)
        rc, dt, cmd = spawn(["--arm", arm] + (["--target", target] if target else []),
                            os.path.join(RUN_DIR, (arm + ("_" + target if target else "")) + ".log"))
        run = read_run(path)
        logs[arm + ("_" + target if target else "")] = {
            "rc": rc, "seconds": round(dt, 2), "command": subprocess.list2cmdline(cmd)}
        log("driver: %s%s rc=%d control_ok=%s" % (arm, "/" + target if target else "",
                                                  rc, (run or {}).get("control_ok")))
        if rc != 0 or not run:
            return _finish_fixture_failure(
                logs, "arm %s failed to produce a run record (rc=%d): %s"
                      % (arm + ("/" + target if target else ""), rc,
                         (run or {}).get("error", "no result file")),
                runs=runs, manifest=manifest)
        if not run.get("control_ok"):
            return _finish_fixture_failure(
                logs, "arm %s control gate failed -- fixture failure, results NOT interpreted"
                      % (arm + ("/" + target if target else "")),
                runs=runs + [(arm + ("_" + target if target else ""), target, run)],
                manifest=manifest)
        runs.append((arm + ("_" + target if target else ""), target, run))

    return _finish_ok(logs, runs, manifest, started, time.time() - t_all)


def _common_report(logs, manifest, verdict, runs):
    engine = (manifest or {}).get("engine", {})
    return {
        "schema": "m2_visibility_report_v2",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "task": "task-1 (fixture owner: m2_visibility_probe.py)",
        "project_root": ROOT,
        "probe": os.path.abspath(__file__),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "model": engine.get("model", MODEL),
            "model_size": engine.get("model_size"),
            "model_mtime": engine.get("model_mtime"),
            "dll": engine.get("dll", os.path.join(HERE, "kvshim_vk.dll")),
            "dll_sha256": engine.get("dll_sha256"),
            "n_ctx": N_CTX, "n_seq": N_SEQ, "gpu": GPU, "kv": KV,
            "CHAT": CHAT, "SLOT": SLOT, "LIVE": LIVE, "CTRL": CTRL, "PROBE": PROBE,
        },
        "processes": logs,
        "fixtures": (manifest or {}).get("blocks"),
        "layouts": (manifest or {}).get("layouts"),
        "control_texts": {
            k: {"start": v["start"], "target_n": v["target_n"],
                "measured_n": v["measured_n"], "sha256": v["sha256"],
                "text": v["text"], "prefix_order": v["prefix_order"]}
            for k, v in ((manifest or {}).get("control_texts") or {}).items()},
        "verdict": verdict,
        "runs": [r for _n, _t, r in runs],
    }


def _finish_fixture_failure(logs, reason, runs=None, manifest=None, control_run=None):
    manifest = manifest or load_manifest(require=False)
    runs = runs or ([] if control_run is None else [("CONTROL", None, control_run)])
    verdict = {
        "attributable": False,
        "control_passed": False,
        "status": "FIXTURE_FAILURE",
        "reason": reason,
        "interpretation": "none -- the control gate did not pass, so the segment answers "
                          "in this run are not attributable to the visibility question",
    }
    report = _common_report(logs, manifest, verdict, runs)
    _write_report_files(report)
    log("driver: FIXTURE FAILURE: %s" % reason)
    return 2


def _summarize_arm(run):
    return {
        "arm": run.get("arm"), "target": run.get("target"),
        "pid": (run.get("engine") or {}).get("pid", (run.get("process") or {}).get("pid")),
        "layout": run.get("layout_key"),
        "control_ok": run.get("control_ok"),
        "raw": run.get("raw"),
        "answers": run.get("answers", []),
    }


def _finish_ok(logs, runs, manifest, started, elapsed):
    # hash re-check: the pristine inputs must be byte-identical after the run
    blocks = manifest["blocks"]
    after = {}
    changed = []
    for kind in ("m2", "variant"):
        for bid, meta in blocks[kind].items():
            h = sha256_file(meta["path"])
            after[bid] = h
            if h != meta["sha256"]:
                changed.append(meta["path"])

    arms = [_summarize_arm(r) for _n, _t, r in runs if r.get("arm") != "CONTROL"]
    control_runs = [r for _n, _t, r in runs if r.get("arm") == "CONTROL"]
    per_arm = {}
    for a in arms:
        per_arm[a["arm"]] = per_arm.get(a["arm"], []) + a["answers"]
    verdict = {
        "attributable": all(r.get("control_ok") for _n, _t, r in runs),
        "control_passed": all(r.get("control_ok") for _n, _t, r in runs),
        "status": "OK",
        "pristine_inputs_unchanged": not changed,
        "changed_inputs": changed,
        "summary": {},
        "interpretation": "",
    }
    for arm, answers in sorted(per_arm.items()):
        ok = sum(1 for x in answers if x["ok"])
        verdict["summary"][arm] = {
            "asked": len(answers), "ok": ok,
            "segments": {x["segment"]: ("OK" if x["ok"] else "MISS") for x in answers},
        }
    verdict["summary"]["CONTROL"] = {
        "layout": control_runs[0].get("layout_key") if control_runs else None,
        "control_ok": control_runs[0].get("control_ok") if control_runs else None,
        "questions": (((control_runs[0] or {}).get("control") or {}).get("questions", [])),
    }
    verdict["interpretation"] = (
        "All arm processes passed the text control gate, so the per-segment answers below "
        "are attributable to the shared-cell mechanism (not to fixture geometry, missing "
        "BOS or gapped decoding).  This report states the observed visibility pattern; it "
        "does not assign a causal engine defect."
    )
    report = _common_report(logs, manifest, verdict, runs)
    report["driver"] = {"started_at": started, "elapsed_s": round(elapsed, 2),
                        "commands": {k: v["command"] for k, v in logs.items()}}
    _write_report_files(report, started=started, elapsed=elapsed)
    log("driver: all arms done in %.1fs; report -> %s" % (elapsed, REPORT_MD))
    return 0


def _fmt_pos(seg):
    return "[%d,%d)" % (seg["pos_lo"], seg["pos_hi"])


def _write_report_files(report, started=None, elapsed=None):
    _write_json(REPORT_JSON, report)
    lines = []
    a = lines.append
    a("# M2 shared-segment visibility -- controlled probe v2")
    a("")
    a("Task: `task-1` -- fixture owner `fixture-runner`.  Probe: `tools/m2_visibility_probe.py`.")
    a("")
    verdict = report["verdict"]
    gate = "PASSED" if verdict.get("control_passed") else "FAILED"
    a("## Control gate: **%s**" % gate)
    a("")
    if not verdict.get("control_passed"):
        a("> **FIXTURE FAILURE.** %s" % verdict.get("reason", ""))
        a(">")
        a("> No segment result in this report may be interpreted.  Fix the fixture and rerun.")
        a("")
    else:
        a("Every arm process ran, in order: (1) a contiguous plain-text control built from the")
        a("layout's lowest position, with BOS on the first token only and neutral filler up to")
        a("last memory position exactly 4095, asked at 4096; then (2) the shared-cell arm.")
        a("No arm result is interpreted unless its own control gate passed.")
        a("")
        a("| gate run | layout | start | target tokens | text sha256 | questions | result |")
        a("|---|---|---|---|---|---|---|")
        cr = (verdict.get("summary") or {}).get("CONTROL") or {}
        cq = cr.get("questions") or []
        txt = (report.get("control_texts") or {}).get(cr.get("layout") or "", {})
        a("| CONTROL | %s | %s | %s | `%s` | %d/%d | **%s** |"
          % (cr.get("layout"), txt.get("start", "?"), txt.get("target_n", "?"),
             (txt.get("sha256") or "")[:16], sum(1 for q in cq if q["ok"]), len(cq),
             "PASS" if cr.get("control_ok") else "FAIL"))
        a("")
        a("Per-question control evidence (plain text, no `seq_cp`):")
        a("")
        a("| layout | question | expected | answer | ok |")
        a("|---|---|---|---|---|")
        for key, ct in sorted((report.get("control_texts") or {}).items()):
            run = next((r for r in report["runs"]
                        if (r.get("control") or {}).get("layout") == key), None)
            for q in (((run or {}).get("control") or {}).get("questions", [])):
                a("| %s | %s | %s | %s | %s |"
                  % (key, q["question"], q["expected"],
                     (q["answer"] or "").replace("|", "\\|")[:50],
                     "PASS" if q["ok"] else "FAIL"))

    a("")
    a("## Exact commands")
    a("")
    a("```text")
    a(r"cd /d D:\llama-mem")
    a(r"python -X utf8 tools\m2_visibility_probe.py --arm setup        # one fresh engine, one-time fixture")
    a(r"python -X utf8 tools\m2_visibility_probe.py --arm CONTROL      # pre-flight gate, clean process")
    a(r"python -X utf8 tools\m2_visibility_probe.py --arm A --target home")
    a(r"python -X utf8 tools\m2_visibility_probe.py --arm A --target project")
    a(r"python -X utf8 tools\m2_visibility_probe.py --arm A --target habit")
    a(r"python -X utf8 tools\m2_visibility_probe.py --arm A --target car")
    a(r"python -X utf8 tools\m2_visibility_probe.py --arm B")
    a(r"python -X utf8 tools\m2_visibility_probe.py --arm C")
    a(r"python -X utf8 tools\m2_visibility_probe.py --arm D_FWD")
    a(r"python -X utf8 tools\m2_visibility_probe.py --arm D_REV")
    a("")
    a("# or the whole thing (the parent only spawns the processes above):")
    a(r"python -X utf8 tools\m2_visibility_probe.py --arm ALL")
    a("```")
    a("")
    a("Per-process logs and run records: `kvmem/m2_visibility/runs/` "
      "(one log + one JSON per process).")
    a("")
    a("## Environment and fingerprints")
    a("")
    env = report["environment"]
    a("| item | value |")
    a("|---|---|")
    a("| python | %s |" % env.get("python"))
    a("| platform | %s |" % env.get("platform"))
    a("| model | `%s` (%s bytes, mtime %s) |"
      % (env.get("model"), env.get("model_size"), env.get("model_mtime")))
    a("| dll | `%s` |" % env.get("dll"))
    a("| dll sha256 | `%s` |" % env.get("dll_sha256"))
    a("| engine | n_ctx=%s n_seq=%s gpu=%s kv=%s, one fresh process per arm |"
      % (env.get("n_ctx"), env.get("n_seq"), env.get("gpu"), env.get("kv")))
    a("| constants | CHAT=%s SLOT=%s LIVE=%s CTRL=%s PROBE=%s |"
      % (env.get("CHAT"), env.get("SLOT"), env.get("LIVE"),
         env.get("CTRL"), env.get("PROBE")))
    a("")
    a("Pristine blocks (hash-verified before and after every arm process; never rewritten):")
    a("")
    a("| block | file | cells | sha256 |")
    a("|---|---|---|---|")
    for kind in ("m2", "variant"):
        for bid, meta in ((report.get("fixtures") or {}).get(kind) or {}).items():
            a("| %s | `%s` | %d | `%s` |" % (bid, meta["path"], meta["cells"],
                                               meta["sha256"][:32]))
    a("")
    a("> The two 4-segment arms and the CONTROL use the untouched M2 pristine block files.")
    a("> Arm B (79 cells) and arm C (5-cell micro blocks) need cell counts the M2 blocks do")
    a("> not have; those fixtures are written exactly once by `--arm setup` into")
    a("> `kvmem/m2_visibility/blocks/`, hash-pinned in the manifest, and only ever loaded")
    a("> read-only afterwards.  `m2_v1.py`, retrieval, analysis, evidence and the engine")
    a("> are untouched.")
    a("")
    a("## Layouts (B-right, positions from the actual cell counts)")
    a("")
    a("| layout | segment | slot | pos range | cells | add order |")
    a("|---|---|---|---|---|---|")
    for key, lay in sorted((report.get("layouts") or {}).items()):
        for seg in sorted(lay["segments"], key=lambda s: -s["slot"]):
            a("| %s | %s | %d | %s | %d | %d |"
              % (key, seg["id"], seg["slot"], _fmt_pos(seg), seg["cells"], seg["add_order"]))
        a("| %s | **total** | | [%d,%d) | **%d** | %s |"
          % (key, lay["span_lo"], lay["span_hi"], lay["cells_total"],
             "→".join(lay["add_order"])))
    a("")
    a("## Arm processes (fresh engine each)")
    a("")
    a("| run | pid | layout | control | raw LIVE pos_max | scanned cells | expected | overlaps |")
    a("|---|---|---|---|---|---|---|---|")
    for run in report["runs"]:
        raw = run.get("raw") or {}
        a("| %s | %s | %s | %s | %s | %s | %s | %s |"
          % (run.get("run_id"), (run.get("engine") or {}).get("pid"),
             run.get("layout_key"),
             "PASS" if run.get("control_ok") else "FAIL",
             raw.get("live_pos_max_raw", "n/a"), raw.get("cell_count", "n/a"),
             raw.get("expected_cells", "n/a"), raw.get("overlaps", "n/a")))
    a("")
    a("## Segment answers")
    a("")
    if verdict.get("control_passed"):
        a("| arm | pid | segment | add order | pos range | cells | raw pos_max | question | expected | answer | result |")
        a("|---|---|---|---|---|---|---|---|---|---|---|")
        for run in report["runs"]:
            if run.get("arm") == "CONTROL":
                continue
            pid = (run.get("engine") or {}).get("pid")
            for x in run.get("answers", []):
                a("| %s%s | %s | %s | %d | [%d,%d) | %d | %s | %s | %s | %s | **%s** |"
                  % (run.get("arm"), ("/" + run["target"]) if run.get("target") else "",
                     pid, x["segment"], x["add_order"], x["pos_lo"], x["pos_hi"],
                     x["cells"], x.get("raw_pos_max_before_ask"), x["question"],
                     x["expected"], (x["answer"] or "").replace("|", "\\|")[:50],
                     "OK" if x["ok"] else "MISS"))
    else:
        a("_Suppressed: control gate failed, segment results are not interpreted._")
    a("")
    a("## Cell-scan evidence (raw accessors)")
    a("")
    a("`kvshim_seq_pos_max_raw` / `kvshim_seq_cell_scan`, not `kvshim_pos_max` (which is -1")
    a("for a `seq_cp`-built sequence by contract).")
    a("")
    a("| run | segment | shared cells | covered live cells | raw LIVE pos_max |")
    a("|---|---|---|---|---|")
    for run in report["runs"]:
        raw = run.get("raw") or {}
        for seg, cov in (raw.get("coverage") or {}).items():
            a("| %s | %s | %d | %d | %s |"
              % (run.get("run_id"), seg, cov["cells"], cov["covered"],
                 raw.get("live_pos_max_raw")))
    a("")
    a("## Verdict")
    a("")
    if not verdict.get("control_passed"):
        a("**FIXTURE FAILURE: %s**" % verdict.get("reason", ""))
        a("")
        a("The data are NOT attributable.  No conclusion about segment visibility is drawn.")
    else:
        a("All %d run processes passed their own control gate; the text baseline (one"
          % len(report["runs"]))
        a("contiguous text, BOS once, last position 4095, ask at 4096) answered every question")
        a("it was gated on.  Pristine inputs unchanged after the run: **%s**."
          % ("yes" if verdict.get("pristine_inputs_unchanged") else "NO -- investigate"))
        a("")
        a("| arm | asked | answered its own fact | per-segment |")
        a("|---|---|---|---|")
        for arm in ("A", "B", "C", "D_FWD", "D_REV"):
            s = (verdict.get("summary") or {}).get(arm)
            if not s:
                continue
            segs = ", ".join("%s=%s" % (k, v) for k, v in s["segments"].items())
            a("| %s | %d | %d/%d | %s |" % (arm, s["asked"], s["ok"], s["asked"], segs))
        a("")
        a(verdict.get("interpretation", ""))
        a("")
        a("Reading the pattern (evidence only, no causal claim beyond the gate):")
        a("")
        for arm in ("A", "B", "C", "D_FWD", "D_REV"):
            s = (verdict.get("summary") or {}).get(arm)
            if not s:
                continue
            if s["ok"] == s["asked"]:
                note = "every segment answered its own fact"
            elif s["ok"] == 0:
                note = "no segment answered its own fact (uniform MISS)"
            else:
                note = "mixed: %s" % ", ".join("%s=%s" % (k, v) for k, v in s["segments"].items())
            a("* `%s`: %s." % (arm, note))
        a("")
        a("Arm A asks one fact per fresh engine, so its rows cannot be explained by")
        a("within-engine question order; arm D_REV keeps each segment's position fixed and")
        a("only reverses mount/share order, so add order is separated from position.")
    a("")
    a("## Notes / limits")
    a("")
    a("* This probe does not change eviction, capacity, retrieval, analysis or evidence, and")
    a("  does not tune thresholds.  It creates a new file only.")
    a("* `kvshim_pos_max` / `n_tokens` are NOT used as visibility evidence: a seq assembled")
    a("  with `seq_cp` has no token bookkeeping by contract.")
    a("* Control gate records the raw last memory position before asking; 4095 is required.")
    a("* Generated answers use the same greedy `ask` path as `m2_v1.py`; answers are recorded")
    a("  verbatim in the JSON report.")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main(argv=None):
    argv = argv or sys.argv
    ap = argparse.ArgumentParser(description="M2 shared-segment visibility fixture")
    ap.add_argument("--arm", required=True,
                    choices=["setup", "CONTROL", "A", "B", "C", "D_FWD", "D_REV", "ALL"])
    ap.add_argument("--target", default=None,
                    help="segment id for arm A (home/project/habit/car)")
    ap.add_argument("--run-json", default=None,
                    help="where a single arm process writes its result record")
    args = ap.parse_args(argv[1:])

    if args.arm == "setup":
        return run_setup()
    if args.arm == "ALL":
        return run_all()
    out = args.run_json or os.path.join(
        RUN_DIR, (args.arm + ("_" + args.target if args.target else "")) + ".json")
    return run_arm(args.arm, args.target, out, [sys.executable] + argv)


if __name__ == "__main__":
    sys.exit(main())