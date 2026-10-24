# -*- coding: utf-8 -*-
"""I12 block builder: create two experiment blocks in runs_iso4/blocks/.
  project_pad19 : project text padded to exactly 19 cells (content = project)
  car_cut18     : car text trimmed to at most 18 cells (content = car)
Only token count / cells are changed; the fact text is kept intact where possible.
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
ISO2 = os.path.join(os.path.dirname(HERE), "runs_iso2")
sys.path.insert(0, ISO2)
import _driver2 as D2                     # noqa: E402
P = D2.P
SCRATCH = 5


def measure(eng, text):
    eng.reset(SCRATCH)
    n = int(eng.write(SCRATCH, text, add_bos=True))
    eng.reset(SCRATCH)
    return n


def make(eng, base, target_n, out_path):
    # candidate texts: exact prefixes, longest first, that fit inside target_n
    cands = [base]
    for k in range(len(base) - 1, 0, -1):
        cands.append(base[:k])
    chosen = None
    for c in cands:
        n = measure(eng, c)
        if n == target_n:
            chosen, how = c, "exact"
            break
        if n < target_n:
            chosen, how = c, "padded from %d" % n
            break
    if chosen is None:
        raise RuntimeError("no candidate fits %d tokens for %r" % (target_n, base[:20]))
    text = chosen if how == "exact" else P.build_exact_text(eng, chosen, target_n)
    n = measure(eng, text)
    if n != target_n:
        raise RuntimeError("built %d tokens, need %d" % (n, target_n))
    if os.path.exists(out_path):
        os.remove(out_path)
    eng.reset(SCRATCH)
    nw = int(eng.write(SCRATCH, text, add_bos=True))
    if nw != target_n:
        raise RuntimeError("write %d != %d" % (nw, target_n))
    written = int(eng.save(SCRATCH, out_path))
    eng.reset(SCRATCH)
    return {"path": out_path, "cells": target_n, "text": text, "write_rc": nw,
            "save_rc": written, "bytes": os.path.getsize(out_path), "how": how}


def main():
    manifest = P.load_manifest()
    blk = os.path.join(HERE, "blocks")
    os.makedirs(blk, exist_ok=True)
    eng = P.open_engine()
    try:
        out = {}
        proj_text = P.FULL["project"]["text"]
        car_text = P.FULL["car"]["text"]
        out["project_pad19"] = make(eng, proj_text, 19, os.path.join(blk, "project_pad19.kvmem"))
        out["car_cut18"] = make(eng, car_text, 18, os.path.join(blk, "car_cut18.kvmem"))
        out["_source"] = {"project_text": proj_text, "car_text": car_text,
                          "m2_project_cells": manifest["blocks"]["m2"]["project"]["cells"],
                          "m2_car_cells": manifest["blocks"]["m2"]["car"]["cells"]}
        with open(os.path.join(HERE, "built_blocks.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        for k, v in out.items():
            if k.startswith("_"):
                continue
            print("%-14s cells=%d bytes=%d how=%s text=%r" % (k, v["cells"], v["bytes"], v["how"], v["text"][:40]))
        return 0
    finally:
        eng.close()


if __name__ == "__main__":
    sys.exit(main())