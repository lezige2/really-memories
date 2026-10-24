# -*- coding: utf-8 -*-
"""Normalize PE build stamps for byte comparison of two rebuilds.

The FIRST stamp is the COFF TimeDateStamp at 0x80. The second is NOT at a fixed offset --
it moves with the binary size (it sat at 47838724 in the 49,952,768-byte DLL and at
47,840,260 in the 49,954,304-byte one). So it is located by VALUE: every occurrence of the
same 32-bit stamp is cleared. This is size independent, which a hardcoded offset is not.
"""
import hashlib
import struct
import sys


def normalize(path):
    b = bytearray(open(path, "rb").read())
    ts = bytes(b[0x80:0x84])
    hits = [0x80]
    start = 0x84
    while True:
        i = b.find(ts, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    for off in hits:
        b[off:off + 4] = b"\x00\x00\x00\x00"
    return bytes(b), hits, struct.unpack("<I", ts)[0]


def main():
    res = {}
    for p in sys.argv[1:]:
        nb, hits, ts = normalize(p)
        h = hashlib.sha256(nb).hexdigest()
        res[p] = h
        print(p)
        print("  raw sha16 %s" % hashlib.sha256(open(p, "rb").read()).hexdigest()[:16])
        print("  normalized sha16 %s   stamp=%d cleared at %s (%d fields, %d bytes)"
              % (h[:16], ts, hits, len(hits), 4 * len(hits)))
    if len(sys.argv) > 2:
        print("NORMALIZED_EQUAL=%s" % (len(set(res.values())) == 1))


if __name__ == "__main__":
    main()