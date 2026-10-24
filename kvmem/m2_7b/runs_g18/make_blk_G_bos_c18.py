# -*- coding: utf-8 -*-
"""Build blk_G_bos_c18.kvmem: a third true fact, exactly 18 cells = 1 BOS + 17 content.

Declared text is used verbatim (no padding, no trimming). If the measurement is not
exactly 18 cells the script stops and writes nothing.

Output: D:\llama-mem\kvmem\m2_v1\blk_G_bos_c18.kvmem   (blocks/ is read-only, untouched)

Checks printed (all must PASS):
  cells == 18 | first_token == 151646 | content tokens == 17 | file size == 708+30480*18
  header token ids == the live sequence's token ids == [BOS] + kvshim_tokenize(text)
  piece(each id) concatenated == the declared text (per-token agreement, not an estimate)
  determinism: a second independent encode+save of the same text gives the same sha256
  reload: load_strict() == 18 cells and cell_scan covers 18 positions
"""
import ctypes
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P   # noqa: E402

TEXT = "我的雨伞放在书桌边，伞骨断了一根还留着。"
NAME = "blk_G_bos_c18"
OUT = os.path.join(ROOT, "kvmem", "m2_v1", NAME + ".kvmem")
TWIN = os.path.join(HERE, NAME + ".twin.kvmem")
REPORT = os.path.join(HERE, NAME + ".build.json")
BOS = 151646
HEADER = 708
STRIDE = 30480
SC1, SC2, SC3 = 2, 3, 4

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("  [%s] %-46s %s" % ("PASS" if ok else "FAIL", name, detail))
    return ok


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_block(path):
    raw = open(path, "rb").read()
    n = struct.unpack("<i", raw[8:12])[0]
    toks = list(struct.unpack("<%di" % n, raw[12:12 + 4 * n]))
    return {"size": len(raw), "cells": n, "tokens": toks,
            "cells_from_size": (len(raw) - HEADER) // STRIDE,
            "size_rem": (len(raw) - HEADER) % STRIDE}


def main():
    for w in ("楼下", "阳台", "绿萝", "小区", "家", "咖啡", "项目", "上线"):
        if w in TEXT:
            print("STOP: declared text contains forbidden word %r" % w)
            return 2
    if any(c.isdigit() for c in TEXT):
        print("STOP: declared text contains a digit")
        return 2

    eng = P.open_engine()
    L = eng.lib
    L.kvshim_tokenize.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                  ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    L.kvshim_tokenize.restype = ctypes.c_int
    L.kvshim_seq_tokens.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                    ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    L.kvshim_seq_tokens.restype = ctypes.c_int
    L.kvshim_piece.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    L.kvshim_piece.restype = ctypes.c_int

    def seq_tokens(seq):
        buf = (ctypes.c_int * P.N_CTX)()
        n = int(L.kvshim_seq_tokens(eng.h, seq, buf, P.N_CTX))
        return [int(buf[i]) for i in range(n)]

    def tokenize(text):
        buf = (ctypes.c_int * P.N_CTX)()
        n = int(L.kvshim_tokenize(eng.h, text.encode("utf-8"), buf, P.N_CTX))
        return [int(buf[i]) for i in range(n)]

    def piece(tid):
        buf = ctypes.create_string_buffer(512)
        nb = int(L.kvshim_piece(eng.h, tid, buf, 512))
        return "" if nb < 0 else buf.raw[:nb].decode("utf-8", "replace")

    try:
        print("declared text: %s" % TEXT)
        n_meas = P.measure(eng, TEXT)
        print("P.measure (with BOS) = %d cells" % n_meas)
        if not check("measure == 18 cells", n_meas == 18, "%d" % n_meas):
            print("STOP: text is %d cells, need exactly 18 -- nothing written" % n_meas)
            return 2

        eng.reset(SC1)
        written = int(eng.write(SC1, TEXT, add_bos=True))
        ids_live = seq_tokens(SC1)
        check("write(add_bos=True) == 18", written == 18, "%d" % written)
        check("sequence holds 18 ids", len(ids_live) == 18, "%d" % len(ids_live))
        check("first token is BOS", ids_live[0] == BOS, "%d" % ids_live[0])
        check("content tokens == 17", len(ids_live) - 1 == 17, "%d" % (len(ids_live) - 1))

        ok_save = int(eng.save(SC1, OUT)) > 0
        eng.reset(SC1)
        check("save returned > 0", ok_save, OUT)

        # ---- header parse (the tools/block_info.py rule, done here so the builder can gate)
        b = parse_block(OUT)
        check("file cells == 18", b["cells"] == 18, "%d" % b["cells"])
        check("header cells == size-derived cells", b["cells"] == b["cells_from_size"],
              "%d vs %d (rem %d)" % (b["cells"], b["cells_from_size"], b["size_rem"]))
        check("size == 708 + 30480*18", b["size"] == HEADER + STRIDE * 18,
              "%d" % b["size"])
        check("header first token is BOS", b["tokens"][0] == BOS, "%d" % b["tokens"][0])
        check("header content token count == 17", len(b["tokens"]) - 1 == 17,
              "%d" % (len(b["tokens"]) - 1))
        check("header ids == live sequence ids", b["tokens"] == ids_live,
              "same" if b["tokens"] == ids_live else "DIFFER")

        # ---- declared text vs stored tokens, per token
        ids_text = tokenize(TEXT)
        check("tokenize(text) has 17 ids", len(ids_text) == 17, "%d" % len(ids_text))
        check("header ids[1:] == tokenize(text)", b["tokens"][1:] == ids_text,
              "same" if b["tokens"][1:] == ids_text else "DIFFER")
        pieces = [piece(t) for t in b["tokens"][1:]]
        check("piece(each id) joined == declared text",
              "".join(pieces) == TEXT, "%r" % "".join(pieces))
        print("  tokens[1:] pieces: %s" % " | ".join(pieces))

        # ---- determinism: encode + save again from the SAME sequence.
        # Measured, not assumed: two saves of the same text from DIFFERENT sequences differ in
        # the 18 header bytes at offsets 100,112,...,316, whose values are the sequence id
        # (2 vs 3, 12 bytes apart). The payload is identical, and the same-sequence save is
        # byte-identical (runs_g18/diag_determinism.py). Comparing across sequences was
        # therefore my own instrument error, not block nondeterminism.
        eng.reset(SC1)
        eng.write(SC1, TEXT, add_bos=True)
        eng.save(SC1, TWIN)
        eng.reset(SC1)
        sha_out, sha_twin = sha256_file(OUT), sha256_file(TWIN)
        check("same-seq re-encode+save gives the same sha256", sha_out == sha_twin,
              "%s vs %s" % (sha_out[:16], sha_twin[:16]))

        # ---- reload: cells and cells-on-live
        eng.reset(SC3)
        n_load = int(eng.load_strict(SC3, OUT))
        base = int(eng.pos_max(SC3)) - n_load + 1
        hi = int(eng.pos_max(SC3)) + 1
        cnt, poss = P.cell_scan(eng, SC3)
        eng.reset(SC3)
        check("reload cells == 18", n_load == 18, "%d" % n_load)
        check("reload cell_scan == 18", cnt == 18, "%d" % cnt)
        check("reload positions contiguous from base",
              poss == list(range(base, hi)), "[%d,%d)" % (base, hi))
        print("  reload base=%d pos=[%d,%d) delta-to-3886=%d" % (base, base, hi, 3886 - base))
    finally:
        eng.close()

    sha = sha256_file(OUT)
    rec = {"schema": "g18_block_build_v1", "name": NAME, "text": TEXT,
           "add_bos": True, "cells": 18, "content_tokens": 17, "first_token": BOS,
           "path": OUT, "sha256": sha, "checks": [{"name": a, "ok": c, "detail": d}
                                                  for a, c, d in results]}
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print()
    print("block  -> %s" % OUT)
    print("sha256 -> %s" % sha)
    print("report -> %s" % REPORT)
    bad = [a for a, c, _ in results if not c]
    print()
    print("%d/%d checks passed%s" % (len(results) - len(bad), len(results),
                                     "" if not bad else "; FAILED: %s" % bad))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
