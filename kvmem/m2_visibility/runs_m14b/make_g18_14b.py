# -*- coding: utf-8 -*-
"""P2: re-encode the 7B X0 unrelated fact (blk_G_bos_c18 text) on the 14B model.

Text is read from fixtures.json at runtime -- not retyped. Cells must come out 18
(BOS + 17 content); anything else stops and reports.
"""
import argparse, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_blocks_14b import P, parse14, BOS, HDR14, CELL14   # noqa: E402

FIX = json.load(open(r"D:/llama-mem/kvmem/m2_visibility/fixtures.json", encoding="utf-8"))
TEXT = FIX["blocks"]["variant"]["blk_G_bos_c18"]["text"]
WANT = 18


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if os.path.exists(a.out):
        raise SystemExit("refusing to overwrite %s" % a.out)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    eng = P.open_engine()
    try:
        n = P.measure(eng, TEXT)
        print("measure(add_bos=True) = %d cells, want %d" % (n, WANT))
        if n != WANT:
            raise SystemExit("STOP P2: 14B tokenizes the X0 text to %d cells, 7B was 18. "
                             "Cell counts differ -> report before placing. text=%r" % (n, TEXT))
        eng.reset(2)
        w = eng.write_at(2, TEXT, 0, add_bos=True)
        if w != WANT:
            raise SystemExit("STOP: wrote %d of %d" % (w, WANT))
        if eng.save(2, a.out) <= 0:
            raise SystemExit("STOP: save failed")
        eng.reset(2)
        h = parse14(a.out)
        checks = {"cells_18": h["n_tokens"] == WANT,
                  "size_1188_plus_104464n": h["size"] == HDR14 + CELL14 * WANT,
                  "first_token_bos": h["first_token"] == BOS,
                  "n_layer_48": h["n_layer"] == 48,
                  "k_row_1088": h["k_row"] == 1088,
                  "v_row_1088": h["v_row"] == 1088,
                  "k_type_8": h["k_type"] == 8,
                  "v_type_8": h["v_type"] == 8,
                  "to_eof": h["consumed_to_eof"]}
        if not all(checks.values()):
            raise SystemExit("STOP: %s" % [k for k, v in checks.items() if not v])
        print(json.dumps({"path": os.path.abspath(a.out), "text": TEXT,
                          "text_sha256": hashlib.sha256(TEXT.encode("utf-8")).hexdigest(),
                          "cells": h["n_tokens"], "content_tokens": h["n_tokens"] - 1,
                          "first_token": h["first_token"], "size": h["size"],
                          "sha256": h["sha256"], "checks": checks},
                         ensure_ascii=False, indent=1))
    finally:
        eng.close()


if __name__ == "__main__":
    sys.exit(main())
