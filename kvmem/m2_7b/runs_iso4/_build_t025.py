# -*- coding: utf-8 -*-
"""T-025 block builder: pad four facts UP to a target cell count and prove each result.

Why a new script instead of _build_blocks.py: that one stops after save().  A block that
saves 40 cells but loads back 39 would then be used as a fixture, and a fixture defect would
be read as a finding.  Every block here must pass these before it is reported:

  (a) cells        load_strict() returns exactly target_n
  (b) twin         save again from the LOADED state; both files must share sha256
                   (a save that cannot reproduce itself is not a block anyone can recompute)
  (c) reload       the twin loads back to target_n as well
  (d) content      recorded text keeps the pristine fact as its prefix and carries filler
                   after it, plus a functional probe: the loaded block is asked its own
                   question and the answer is recorded verbatim (informational, not a gate).
                   NOTE: the engine exports no token-to-text path (kvshim_write / save /
                   load / ask / pos_max / n_tokens and friends only), so "decode the block
                   back to text" is not possible; (d) is the strongest available substitute
                   and is reported as such, not as a decode.
  (e) determinism  the same text encoded twice, saved twice, must give identical sha256
                   (without this, a block cannot be recomputed by anyone else)
  (f) distinction  project_paraphrase18 must NOT be the project tensor: sha256 differs

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

# paraphrase of the project fact: same two facts, different wording, same 18 cells.
PP_CANDIDATES = [
    "项目代号叫蓝鲸，三月十四号正式上线。",
    "项目代号叫蓝鲸，三月十四号上线。",
    "项目叫蓝鲸，三月十四号上线。",
    "项目蓝鲸，三月十四号上线。",
]

# (name, fact key, target cells, paraphrase candidates or None).  Upward padding only.
BLOCKS = [
    ("project_p40", "project", 40, None),
    ("habit_p28", "habit", 28, None),
    ("habit_p40", "habit", 40, None),
    ("project_paraphrase18", "project", 18, PP_CANDIDATES),
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


def pick(eng, cands, target_n):
    for c in cands:
        n = measure(eng, c)
        if n <= target_n:
            return c, n
    raise RuntimeError("no paraphrase candidate fits %d cells: %r" % (target_n, cands))


def encode_twice(eng, text, target_n):
    """Encode the same text in two separate passes and prove the two saves agree."""
    shas = []
    for tag in ("a", "b"):
        tmp = os.path.join(OUT, "_det_%s.kvmem" % tag)
        if os.path.exists(tmp):
            os.remove(tmp)
        eng.reset(SCRATCH)
        n = int(eng.write(SCRATCH, text, add_bos=True))
        if n != target_n:
            raise RuntimeError("determinism pass %s: write %d != %d" % (tag, n, target_n))
        eng.save(SCRATCH, tmp)
        shas.append(sha256(tmp))
        os.remove(tmp)
    eng.reset(SCRATCH)
    return shas


def build(eng, name, fact_key, target_n, cands):
    pristine = P.FULL[fact_key]["text"]
    if cands is None:
        base, n_base = pristine, measure(eng, pristine)
        if n_base > target_n:
            raise RuntimeError("%s: base text is %d cells > target %d (upward padding only)"
                               % (name, n_base, target_n))
    else:
        base, n_base = pick(eng, cands, target_n)
    text = base if n_base == target_n else P.build_exact_text(eng, base, target_n)
    n = measure(eng, text)
    if n != target_n:
        raise RuntimeError("%s: text measures %d, need %d" % (name, n, target_n))

    path = os.path.join(OUT, name + ".kvmem")
    if os.path.exists(path):
        raise RuntimeError("%s already exists; refusing to overwrite" % path)

    # (e) determinism first: if encoding is not reproducible, stop before writing a block.
    shas = encode_twice(eng, text, target_n)
    if shas[0] != shas[1]:
        raise RuntimeError("%s: encoding is NOT deterministic (%s vs %s)"
                           % (name, shas[0][:16], shas[1][:16]))

    eng.reset(SCRATCH)
    nw = int(eng.write(SCRATCH, text, add_bos=True))
    if nw != target_n:
        raise RuntimeError("%s: write %d != %d" % (name, nw, target_n))
    eng.save(SCRATCH, path)
    sha1 = sha256(path)
    eng.reset(SCRATCH)

    # (a) cells roundtrip
    n_loaded = int(eng.load_strict(SCRATCH, path))
    if n_loaded != target_n:
        raise RuntimeError("%s: load_strict %d != %d" % (name, n_loaded, target_n))

    # (b) twin: save again from the loaded state
    tmp = os.path.join(OUT, "_twin.kvmem")
    if os.path.exists(tmp):
        os.remove(tmp)
    eng.save(SCRATCH, tmp)
    sha2 = sha256(tmp)
    if sha2 != sha1:
        raise RuntimeError("%s: re-save of the loaded state differs (%s vs %s)"
                           % (name, sha1[:16], sha2[:16]))

    # (c) the twin reloads to the same cell count
    eng.reset(SCRATCH)
    n_twin = int(eng.load_strict(SCRATCH, tmp))
    if n_twin != target_n:
        raise RuntimeError("%s: twin loads %d != %d" % (name, n_twin, target_n))
    os.remove(tmp)

    # (d) content: fact kept, filler after it; then a functional probe
    if isinstance(cands, list) and not text.startswith(base):
        raise RuntimeError("%s: padded text lost its own prefix" % name)
    filler = text[len(base):]
    if filler == "" and n_base != target_n:
        raise RuntimeError("%s: no filler appended but target > base cells" % name)
    eng.reset(SCRATCH)
    eng.load_strict(SCRATCH, path)
    answer = eng.ask(SCRATCH, P.FULL[fact_key]["q"], n_predict=24)
    eng.reset(SCRATCH)

    return {"name": name, "fact": fact_key, "path": path, "cells": n_loaded,
            "base_cells": n_base, "base_text": base, "text": text, "filler": filler,
            "sha256": sha1, "twin_sha256": sha2, "twin_cells": n_twin,
            "det_sha": shas, "bytes": os.path.getsize(path),
            "how": "exact" if n_base == target_n else "padded",
            "probe_q": P.FULL[fact_key]["q"], "probe_answer": answer,
            "probe_fact_in_answer": P.FULL[fact_key]["fact"] in (answer or "")}


def main():
    os.makedirs(OUT, exist_ok=True)
    eng = P.open_engine()
    try:
        out = {}
        for name, fact_key, target_n, cands in BLOCKS:
            r = build(eng, name, fact_key, target_n, cands)
            out[name] = r
            print("%-20s cells=%d (base %d) bytes=%d sha=%s how=%s" %
                  (r["name"], r["cells"], r["base_cells"], r["bytes"],
                   r["sha256"][:16], r["how"]))
            print("   text   = %r" % r["text"])
            print("   filler = %r" % r["filler"])
            print("   twin   = %s (reload %d) %s" %
                  (r["twin_sha256"][:16], r["twin_cells"],
                   "IDENTICAL" if r["twin_sha256"] == r["sha256"] else "DIFFERS"))
            print("   det    = %s / %s %s" %
                  (r["det_sha"][0][:16], r["det_sha"][1][:16],
                   "SAME" if r["det_sha"][0] == r["det_sha"][1] else "DIFFERS"))
            print("   probe  = %r  fact_in_answer=%s" %
                  (r["probe_answer"], r["probe_fact_in_answer"]))

        # (f) the paraphrase must not be the project tensor
        man = P.load_manifest()
        pj = man["blocks"]["m2"]["project"]
        pp = out["project_paraphrase18"]
        if pp["sha256"] == pj["sha256"]:
            raise RuntimeError("project_paraphrase18 has the SAME sha256 as project.kvmem; "
                               "the block is pointless")
        print("project.kvmem          sha=%s cells=%d" % (pj["sha256"][:16], pj["cells"]))
        print("project_paraphrase18   sha=%s cells=%d  DIFFERENT" %
              (pp["sha256"][:16], pp["cells"]))

        with open(os.path.join(HERE, "built_t025.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print("ALL_CHECKS_OK")
        return 0
    finally:
        eng.close()


if __name__ == "__main__":
    sys.exit(main())