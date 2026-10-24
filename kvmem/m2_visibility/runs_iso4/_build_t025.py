# -*- coding: utf-8 -*-
"""T-025 block builder: pad three facts UP to a target cell count and prove the result.

Why a new script instead of _build_blocks.py: that one stops after save().  A block that
saves 40 cells but loads back 39 would then be used as a fixture, and a fixture defect would
be read as a finding.  Here every block must pass a roundtrip before it is reported:

  (a) cells   : load_strict() returns exactly target_n
  (b) twin    : save again from the LOADED state; the two files must share sha256
                (a save that cannot reproduce itself is not a block anyone can recompute)
  (c) reload  : the twin loads back to target_n as well
  (d) content : the recorded text keeps the pristine fact as its prefix and carries filler
                after it, plus a functional probe: the loaded block is asked its own
                question and the answer is recorded verbatim (informational, not a gate).
                NOTE: the engine exports no token-to-text path (kvshim_write / save / load /
                ask / pos_max / n_tokens and friends only), so "decode the block back to
                text" is not possible; (d) is the strongest available substitute and is
                reported as such, not as a decode.

Nothing here touches fixtures.json: this script only writes .kvmem files plus a report.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ISO2 = os.path.join(os.path.dirname(HERE), "runs_iso2")
sys.path.insert(0, ISO2)
import _driver2 as D2                                          # noqa: E402

P = D2.P
SCRATCH = 5
OUT = os.path.join(os.path.dirname(HERE), "blocks")
TMP = os.path.join(OUT, "_roundtrip_tmp.kvmem")

# (name, fact key, target cells).  Upward padding only: build_exact_text refuses to cut.
BLOCKS = [
    ("project_p40", "project", 40),
    ("habit_p28", "habit", 28),
    ("habit_p40", "habit", 40),
]


def sha256(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def measure(eng, text):
    eng.reset(SCRATCH)
    n = int(eng.write(SCRATCH, text, add_bos=True))
    eng.reset(SCRATCH)
    if n < 1:
        raise RuntimeError("tokenization failed for %r" % text[:40])
    return n


def build(eng, name, fact_key, target_n):
    base = P.FULL[fact_key]["text"]
    n_base = measure(eng, base)
    if n_base > target_n:
        raise RuntimeError("%s: base text is %d cells > target %d (upward padding only)"
                           % (name, n_base, target_n))
    text = base if n_base == target_n else P.build_exact_text(eng, base, target_n)
    n = measure(eng, text)
    if n != target_n:
        raise RuntimeError("%s: text measures %d, need %d" % (name, n, target_n))

    path = os.path.join(OUT, name + ".kvmem")
    if os.path.exists(path):
        raise RuntimeError("%s already exists; refusing to overwrite" % path)
    eng.reset(SCRATCH)
    nw = int(eng.write(SCRATCH, text, add_bos=True))
    if nw != target_n:
        raise RuntimeError("%s: write %d != %d" % (name, nw, target_n))
    eng.save(SCRATCH, path)
    sha1 = sha256(path)

    # (a) cells roundtrip
    eng.reset(SCRATCH)
    n_loaded = int(eng.load_strict(SCRATCH, path))
    if n_loaded != target_n:
        raise RuntimeError("%s: load_strict %d != %d" % (name, n_loaded, target_n))

    # (b) twin: save again from the loaded state
    if os.path.exists(TMP):
        os.remove(TMP)
    eng.save(SCRATCH, TMP)
    sha2 = sha256(TMP)
    if sha2 != sha1:
        raise RuntimeError("%s: re-save of the loaded state differs (%s vs %s)"
                           % (name, sha1[:16], sha2[:16]))

    # (c) the twin reloads to the same cell count
    eng.reset(SCRATCH)
    n_twin = int(eng.load_strict(SCRATCH, TMP))
    if n_twin != target_n:
        raise RuntimeError("%s: twin loads %d != %d" % (name, n_twin, target_n))
    os.remove(TMP)

    # (d) content: fact kept as prefix, filler after it; then a functional probe
    if not text.startswith(base):
        raise RuntimeError("%s: padded text lost the pristine prefix" % name)
    filler = text[len(base):]
    if filler == "":
        raise RuntimeError("%s: no filler appended but target > base cells" % name)
    eng.reset(SCRATCH)
    eng.load_strict(SCRATCH, path)
    answer = eng.ask(SCRATCH, P.FULL[fact_key]["q"], n_predict=24)
    eng.reset(SCRATCH)

    return {"name": name, "fact": fact_key, "path": path, "cells": n_loaded,
            "base_cells": n_base, "text": text, "filler": filler,
            "sha256": sha1, "twin_sha256": sha2, "twin_cells": n_twin,
            "bytes": os.path.getsize(path),
            "how": "exact" if n_base == target_n else "padded",
            "probe_q": P.FULL[fact_key]["q"], "probe_answer": answer,
            "probe_fact_in_answer": P.FULL[fact_key]["fact"] in (answer or "")}


def main():
    os.makedirs(OUT, exist_ok=True)
    eng = P.open_engine()
    try:
        out = {}
        for name, fact_key, target_n in BLOCKS:
            r = build(eng, name, fact_key, target_n)
            out[name] = r
            print("%-12s cells=%d (base %d) bytes=%d sha=%s how=%s" %
                  (r["name"], r["cells"], r["base_cells"], r["bytes"], r["sha256"][:16], r["how"]))
            print("   text   = %r" % r["text"])
            print("   filler = %r" % r["filler"])
            print("   twin   = %s (reload %d) %s" %
                  (r["twin_sha256"][:16], r["twin_cells"],
                   "IDENTICAL" if r["twin_sha256"] == r["sha256"] else "DIFFERS"))
            print("   probe  = %r  fact_in_answer=%s" % (r["probe_answer"], r["probe_fact_in_answer"]))
        with open(os.path.join(HERE, "built_t025.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print("ALL_ROUNDTRIP_OK")
        return 0
    finally:
        eng.close()


if __name__ == "__main__":
    sys.exit(main())