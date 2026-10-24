#!/usr/bin/env python3
"""Block file inspector -- zero engine, pure header parse.

A .kvmem block is llama.cpp's state_seq serialization: a fixed 708-byte header
followed by payload. Header layout used here:
    [0:4]   magic           [4:8]   version
    [8:12]  n_tokens        [12:12+4*n] token ids (int32 LE)
Payload: size == 708 + 30480 * n_tokens.

Usage: python -X utf8 tools/block_info.py <file> [<file> ...]
"""
import hashlib
import os
import struct

BOS = 151646
HEADER = 708
STRIDE = 30480


def info(path):
    raw = open(path, "rb").read()
    n = struct.unpack("<i", raw[8:12])[0]
    toks = struct.unpack("<%di" % n, raw[12:12 + 4 * n])
    cells_from_size, rem = divmod(len(raw) - HEADER, STRIDE)
    return {
        "name": os.path.basename(path),
        "cells": n,
        "cells_from_size": cells_from_size,
        "size_rem": rem,
        "has_bos": toks[0] == BOS,
        "content_tokens": n - 1 if toks[0] == BOS else n,
        "tokens": toks,
        "sha16": hashlib.sha256(raw).hexdigest()[:16],
        "size": len(raw),
        "path": os.path.abspath(path),
    }


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    for p in argv:
        if not os.path.exists(p):
            print("%-34s MISSING" % os.path.basename(p))
            continue
        d = info(p)
        print("%-34s cells=%-3d bos=%-5s content=%-3d size=%d rem=%d sha16=%s"
              % (d["name"], d["cells"], d["has_bos"], d["content_tokens"],
                 d["size"], d["size_rem"], d["sha16"]))
        print("%-34s first8=%s" % ("", list(d["tokens"][:8])))
        if d["cells"] != d["cells_from_size"] or d["size_rem"] != 0:
            print("%-34s STRUCTURE MISMATCH: header cells vs size-derived cells" % "")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
