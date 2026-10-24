# -*- coding: utf-8 -*-
"""Make the two neutral baselines (21 and 18 cells) used as memory-free pairs.

  blk_filler21_nb.kvmem : 21 cells = the home slot's cell count, so it lands on exactly
                          home's positions [4075,4096) with the same delta (4075)
  blk_g18_nb.kvmem      : 18 cells = the project slot's cell count (e.g. [4078,4096))

Written WITHOUT BOS on purpose: the brief quotes 21 / 18 tokens, and 21 / 18 is what the
block has to BE so that a paired run can swap it in cell for cell. With BOS the same text
is 22 / 19 cells and can no longer occupy home's positions -- the geometry (positions /
gap / delta) would drift, which is the one thing the pairing must not do.

The text is used verbatim and the measured token count must equal the target; nothing is
padded, appended or trimmed. If a measurement disagrees the script stops and writes
nothing.

Names carry _nb (no BOS) and do not collide with the concurrent executor's
blk_filler_c21.kvmem.

Run: python -X utf8 kvmem/m2_visibility/make_blocks_filler21_G18.py
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P      # noqa: E402

TEXTS = [
    ("blk_filler21_nb", "小区门口的早餐店换了老板，豆浆还是两块钱一杯，油条涨了五毛。", 21),
    ("blk_g18_nb", "楼下快递柜的取件码每天都会更新，超过三天不取就要退回。", 18),
]
OUT_JSON = os.path.join(P.WORK_DIR, "blocks_filler21_G18.json")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(P.BLOCK_DIR, exist_ok=True)
    man = P.load_manifest()
    home = man["blocks"]["m2"]["home"]
    eng = P.open_engine()
    rows = []
    try:
        # home's own base (0) is the base the baselines are written at, so placing them at
        # home's range needs exactly the same repos delta home needs.
        eng.reset(2)
        n_home = eng.load_strict(2, home["path"])
        home_base = eng.pos_max(2) - n_home + 1
        eng.reset(2)
        print("home block: %d cells, base=%d -> delta for [4075,4096) = %d"
              % (n_home, home_base, 4075 - home_base))

        for name, text, want in TEXTS:
            content_n = P.measure(eng, text) - 1        # BOS excluded: what the block holds
            if content_n != want:
                print("STOP: %s measures %d content tokens, expected %d -- text is used "
                      "verbatim, no filler, nothing written" % (name, content_n, want))
                return 2
            path = os.path.join(P.BLOCK_DIR, name + ".kvmem")
            eng.reset(2)
            written = eng.write_at(2, text, home_base, add_bos=False)
            if written != want:
                print("STOP: %s wrote %d cells, expected %d" % (name, written, want))
                return 2
            if eng.save(2, path) <= 0:
                print("STOP: save failed for %s" % path)
                return 2
            eng.reset(2)

            # read back from disk in a different sequence and count the cells for real
            eng.reset(3)
            n_load = eng.load_strict(3, path)
            base = eng.pos_max(3) - n_load + 1
            hi = eng.pos_max(3) + 1
            eng.reset(3)
            eng.reset(4)
            eng.load_strict(4, path)
            cnt, poss = P.cell_scan(eng, 4)
            eng.reset(4)
            if n_load != want or base != home_base or cnt != want:
                print("STOP: %s reloaded %d cells (scan %d) at base %d, expected %d at %d"
                      % (name, n_load, cnt, base, want, home_base))
                return 2
            rows.append({"name": name, "text": text, "n_tokens": content_n,
                         "cells": n_load, "cells_scanned": cnt, "add_bos": False,
                         "base": base, "pos_lo": base, "pos_hi": hi, "how": "exact",
                         "padding": "", "path": path, "sha256": sha256_file(path)})
    finally:
        eng.close()

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"schema": "score_at_blocks_v2", "bos": False, "blocks": rows}, f,
                  ensure_ascii=False, indent=2)
    print()
    for r in rows:
        print("%-16s n_tokens=%-3d cells=%-3d (scan %-3d) add_bos=%s pos=[%d,%d) how=%s"
              % (r["name"], r["n_tokens"], r["cells"], r["cells_scanned"], r["add_bos"],
                 r["pos_lo"], r["pos_hi"], r["how"]))
        print("                 text   = %s" % r["text"])
        print("                 sha256 = %s" % r["sha256"])
        print("                 file   = %s" % r["path"])
    print()
    print("blocks json -> %s" % OUT_JSON)
    return 0


if __name__ == "__main__":
    sys.exit(main())
