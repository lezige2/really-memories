# -*- coding: utf-8 -*-
"""Normalize the two PE build-time stamps so two rebuilds can be compared byte for byte.

Both fields are FOUR bytes each; zeroing only the low half of the second one would let a
different build machine slip through as "noise", so this script zeroes whole fields and
prints exactly what it cleared.
"""
import hashlib
import sys

FIELDS = [(128, 4, "COFF TimeDateStamp (PE header)"),
          (47838724, 4, "second build stamp (same clock)")]


def normalize(path):
    b = bytearray(open(path, "rb").read())
    for off, size, _why in FIELDS:
        b[off:off + size] = b"\x00" * size
    return bytes(b)


def main():
    for p in sys.argv[1:]:
        raw = hashlib.sha256(open(p, "rb").read()).hexdigest()
        zd = hashlib.sha256(normalize(p)).hexdigest()
        print("%s" % p)
        print("  raw        sha16 %s" % raw[:16])
        print("  normalized sha16 %s  (cleared %d fields, %d bytes total)"
              % (zd[:16], len(FIELDS), sum(s for _o, s, _w in FIELDS)))
        for off, size, why in FIELDS:
            print("    @%d +%d  %s" % (off, size, why))
    if len(sys.argv) > 2:
        h = {p: hashlib.sha256(normalize(p)).hexdigest() for p in sys.argv[1:]}
        print("NORMALIZED_EQUAL=%s" % (len(set(h.values())) == 1))


if __name__ == "__main__":
    main()