# -*- coding: utf-8 -*-
"""Shared geometry / scoring helpers for the kvshim_score_at probe.

Position convention is the repo's own (runs_iso2/_driver2.build_layout): a block's TOP is
top - (slot-1)*64, so the gap between the memory top and the question point is 0 for the
slot that owns the top, and the bottom moves with the cell count. Nothing here invents a
new layout rule.

Blocks live at base 0 on disk (pristine m2 blocks and the neutral baselines both), so
placing one at pos_lo applies repos delta = pos_lo; the delta actually applied is read
back from kvshim, never assumed.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P      # noqa: E402

SPACING = P.SLOT                     # 64
BASELINES_JSON = os.path.join(P.WORK_DIR, "blocks_filler21_G18.json")

# The two neutral baselines created by make_blocks_filler21_G18.py, exposed as a manifest
# family so load_and_place / share_layout can treat them like any pristine block.
NEUTRAL = "neutral"


def manifest(include_baselines=True):
    m = P.load_manifest()
    if include_baselines:
        extra = json.load(open(BASELINES_JSON, encoding="utf-8"))
        fam = m["blocks"].setdefault(NEUTRAL, {})
        for b in extra["blocks"]:
            fam[b["name"]] = {"path": b["path"], "cells": b["cells"],
                              "sha256": b["sha256"], "text": b["text"]}
    return m


def layout(segs, top=None, man=None):
    """segs: [(slot, sid, block_id, family)] -> layout dict, top-aligned.

    top defaults to CHAT (4096): the question point every established run uses. Pass a
    different top to move the whole configuration down without changing its shape.
    """
    m = man or manifest()
    top = P.CHAT if top is None else int(top)
    out, order = [], []
    for slot, sid, bid, fam in segs:
        b = m["blocks"][fam][bid]
        n = b["cells"]
        hi = top - (slot - 1) * SPACING
        lo = hi - n
        out.append({"id": sid, "block": fam, "block_id": bid, "file": b["path"],
                    "file_sha256": b["sha256"], "cells": n, "slot": slot,
                    "pos_lo": lo, "pos_hi": hi, "add_order": len(order) + 1})
        order.append(sid)
    return {"key": "score", "segments": out, "add_order": order, "spacing": SPACING,
            "start": min(s["pos_lo"] for s in out),
            "cells_total": sum(s["cells"] for s in out),
            "span_lo": min(s["pos_lo"] for s in out),
            "span_hi": max(s["pos_hi"] for s in out)}


def place(eng, lay):
    """Fresh load of every block in lay at its top-aligned range (verifies cells + pos)."""
    return P.load_and_place(eng, lay)


def score(eng, lay, placed, prompt, answer, pos, cap=64):
    """One independent score_at run: LIVE is wiped and re-shared before every measurement,
    so no run inherits a decoded prompt from the previous one."""
    eng.reset(P.LIVE)
    P.share_layout(eng, lay, placed)
    r = eng.score_at(P.LIVE, prompt, answer, pos, cap=cap)
    r["piece_list"] = [eng.piece(t) for t in r["tokens"]]
    r["pieces"] = "".join(x or "" for x in r["piece_list"])
    return r


def segments_text(lay):
    return [(s["id"], s["pos_lo"], s["pos_hi"], s["cells"], os.path.basename(s["file"]),
             s["file_sha256"][:12]) for s in lay["segments"]]


def show(lay):
    for sid, lo, hi, n, fname, sha in segments_text(lay):
        print("    %-9s [%4d,%4d) %2d cells  %-18s %s" % (sid, lo, hi, n, fname, sha))
