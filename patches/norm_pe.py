# -*- coding: utf-8 -*-
"""Clear PE build stamps by STRUCTURE (never by value search).

Why not search: if the 4-byte stamp value happens to occur elsewhere (constant pool, an
immediate), clearing it would silently rewrite real content and still report "equal" -- a
forged reproducibility certificate. The site list below is derived from the PE layout only,
and the number of bytes cleared is asserted against the number the structure predicts.
"""
import hashlib
import struct
import sys


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rva_to_off(b, rva, sections):
    for va, vsz, praw in sections:
        if va <= rva < va + max(vsz, 1):
            return praw + (rva - va)
    raise SystemExit("debug directory RVA 0x%x is in no section" % rva)


def sites(path):
    b = open(path, "rb").read()
    e = u32(b, 0x3C)
    out = [("COFF.TimeDateStamp", e + 8)]
    nsec = u16(b, e + 6)
    optsz = u16(b, e + 20)
    opt = e + 24
    magic = u16(b, opt)
    dd = opt + (112 if magic == 0x20B else 96)
    out.append(("OptionalHeader.CheckSum", opt + 64))
    secs = []
    st = opt + optsz
    for i in range(nsec):
        o = st + 40 * i
        vsz, va, rawsz, praw = u32(b, o + 8), u32(b, o + 12), u32(b, o + 16), u32(b, o + 20)
        secs.append((va, vsz or rawsz, praw))
        out.append(("Section[%d].TimeDateStamp" % i, o + 8))
    drva, dsz = u32(b, dd + 6 * 8), u32(b, dd + 6 * 8 + 4)
    if drva and dsz:
        doff = rva_to_off(b, drva, secs)
        for i in range(dsz // 28):
            out.append(("DebugDir[%d].TimeDateStamp" % i, doff + 28 * i + 4))
    for name, off in out:
        if off + 4 > len(b):
            raise SystemExit("site %s at %d is past EOF -- structure parse is wrong" % (name, off))
    return b, out


def normalize(path):
    b, st = sites(path)
    b = bytearray(b)
    detail = []
    for name, off in st:
        detail.append((name, off, u32(bytes(b), off)))
        b[off:off + 4] = b"\x00\x00\x00\x00"
    cleared = 4 * len(st)
    assert cleared == 4 * len(detail), "cleared bytes do not match the enumerated sites"
    return bytes(b), detail, cleared


def main():
    hs = {}
    for p in sys.argv[1:]:
        nb, detail, cleared = normalize(p)
        h = hashlib.sha256(nb).hexdigest()
        hs[p] = h
        print(p)
        print("  raw sha16 %s" % hashlib.sha256(open(p, "rb").read()).hexdigest()[:16])
        print("  normalized sha16 %s   cleared %d sites / %d bytes" % (h[:16], len(detail), cleared))
        for name, off, val in detail:
            print("    %-34s @%-9d 原值 %d" % (name, off, val))
    if len(sys.argv) > 2:
        print("NORMALIZED_EQUAL=%s" % (len(set(hs.values())) == 1))


if __name__ == "__main__":
    main()