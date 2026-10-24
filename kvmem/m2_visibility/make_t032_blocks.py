# -*- coding: utf-8 -*-
"""T-032 block maker (new blocks only; blocks/ is read-only).

Same discipline as the existing four blocks: written at base 0 with add_bos=True, so the
block is 1 BOS + N content tokens.  After saving, EVERY block is re-loaded from disk and
checked four ways: header cells, size-derived cells (size == 708 + 30480*n), first token
== 151646, and token-by-token equality with the declared text.

Usage: python -X utf8 kvmem/m2_visibility/make_t032_blocks.py --only habit_para12
"""
import argparse
import ctypes
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P      # noqa: E402

BOS = 151646
HEADER, STRIDE = 708, 30480
M2V1 = os.path.join(ROOT, "kvmem", "m2_v1")
OUT_JSON = os.path.join(P.WORK_DIR, "blocks_t032.json")

# name -> (text, cells INCLUDING BOS)
BLOCKS = {
    "habit_para12": ("我只喝美式咖啡，不加糖。", 12),
    "filler_bos_c21": ("小区门口的早餐店换了老板，豆浆两块钱一杯，油条涨了五毛。", 21),
    "G_bos_c18": ("我在市立图书馆做志愿者，每星期上午帮忙整理旧书和杂志。", 18),
}
NOTE = {
    "habit_para12": "habit 的受限同义改写（11 内容 token，与 habit 原块同 12 格）",
    "filler_bos_c21": "中性填充，1 BOS + 20 内容 token（上一轮无 BOS 的 filler_c21 的合规重造）",
    "G_bos_c18": "第三件真实事实，1 BOS + 17 内容 token（project 槽位格数的中性块）",
}


def header(path):
    raw = open(path, "rb").read()
    n = struct.unpack("<i", raw[8:12])[0]
    toks = list(struct.unpack("<%di" % n, raw[12:12 + 4 * n]))
    cells_size, rem = divmod(len(raw) - HEADER, STRIDE)
    return {"cells": n, "cells_from_size": cells_size, "size_rem": rem,
            "size": len(raw), "tokens": toks,
            "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", required=True, choices=sorted(BLOCKS))
    a = ap.parse_args()
    name = a.only
    text, want = BLOCKS[name]
    path = os.path.join(M2V1, name + ".kvmem")
    if os.path.exists(path):
        raise SystemExit("refusing to overwrite an existing block: %s" % path)

    rows = []
    if os.path.exists(OUT_JSON):
        rows = json.load(open(OUT_JSON, encoding="utf-8"))["blocks"]

    eng = P.open_engine()
    try:
        eng.lib.kvshim_seq_tokens.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                              ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        eng.lib.kvshim_tokenize.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                            ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        n_meas = P.measure(eng, text)          # with BOS
        if n_meas != want:
            raise SystemExit("STOP: %r measures %d cells (with BOS), declared %d -- no "
                             "padding, nothing written" % (text, n_meas, want))
        eng.reset(2)
        written = eng.write_at(2, text, 0, add_bos=True)
        if written != want:
            raise SystemExit("STOP: wrote %d tokens, expected %d" % (written, want))
        seq_toks = (ctypes.c_int * 4096)()
        n_seq = int(eng.lib.kvshim_seq_tokens(eng.h, 2, seq_toks, 4096))
        seq_list = [int(seq_toks[i]) for i in range(n_seq)]
        if eng.save(2, path) <= 0:
            raise SystemExit("STOP: save failed for %s" % path)
        eng.reset(2)

        txt_toks = (ctypes.c_int * 4096)()
        n_txt = int(eng.lib.kvshim_tokenize(eng.h, text.encode("utf-8"), txt_toks, 4096))
        txt_list = [int(txt_toks[i]) for i in range(n_txt)]
        eng.reset(5)
        n_load = eng.load_strict(5, path)
        rb = (ctypes.c_int * 4096)()
        n_rb = int(eng.lib.kvshim_seq_tokens(eng.h, 5, rb, 4096))
        rb_list = [int(rb[i]) for i in range(n_rb)]
        eng.reset(5)
    finally:
        eng.close()

    h = header(path)
    checks = {
        "measure_equals_declared": n_meas == want,
        "written_equals_declared": written == want,
        "header_cells": h["cells"] == want,
        "size_derived_cells": h["cells_from_size"] == want and h["size_rem"] == 0,
        "first_token_is_bos": h["tokens"][0] == BOS,
        "reload_cells": n_load == want,
        "tokens_match_declared_text": rb_list[1:] == txt_list and rb_list[0] == BOS,
        "in_memory_tokens_match": seq_list[0] == BOS and seq_list[1:] == txt_list,
    }
    if not all(checks.values()):
        raise SystemExit("STOP: post-write assertions failed: %s"
                         % [k for k, v in checks.items() if not v])

    rows = [r for r in rows if r["name"] != name] + [{
        "name": name, "path": os.path.abspath(path), "text": text, "note": NOTE[name],
        "cells": h["cells"], "content_tokens": h["cells"] - 1, "add_bos": True,
        "measure_with_bos": n_meas, "first_token": h["tokens"][0],
        "size": h["size"], "sha256": h["sha256"], "sha16": h["sha256"][:16],
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "token_ids": rb_list, "checks": checks}]
    json.dump({"schema": "t032_blocks_v1", "blocks": sorted(rows, key=lambda r: r["name"])},
              open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("%-16s cells=%d content=%d first=%d(BOS=%s) size=%d sha16=%s"
          % (name, h["cells"], h["cells"] - 1, h["tokens"][0], h["tokens"][0] == BOS,
             h["size"], h["sha256"][:16]))
    print("  text  = %s" % text)
    print("  text sha256 = %s" % hashlib.sha256(text.encode("utf-8")).hexdigest())
    print("  tokens = %s" % rb_list)
    print("  file  = %s" % os.path.abspath(path))
    print("  checks = %s" % json.dumps(checks, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
