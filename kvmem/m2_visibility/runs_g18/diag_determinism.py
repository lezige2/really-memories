# -*- coding: utf-8 -*-
"""Diagnose the nondeterministic save: where do two encodings of the same text differ?"""
import hashlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P

TEXT = "我的雨伞放在书桌边，伞骨断了一根还留着。"
OUT = os.path.join(ROOT, "kvmem", "m2_v1", "blk_G_bos_c18.kvmem")
TWIN = os.path.join(HERE, "blk_G_bos_c18.twin.kvmem")

a = open(OUT, "rb").read()
b = open(TWIN, "rb").read()
print("sizes", len(a), len(b))
diffs = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
print("differing bytes:", len(diffs), "first10:", diffs[:10])
if diffs:
    print("first diff offset", diffs[0], "in header?" , diffs[0] < 708)
    # per-30480 cell blocks
    cells_a = (len(a) - 708) // 30480
    per = {}
    for i in diffs:
        if i < 708:
            per["header"] = per.get("header", 0) + 1
        else:
            c = (i - 708) // 30480
            per[c] = per.get(c, 0) + 1
    print("diff by cell:", per)
    # magnitude on one differing byte
    print("sample", [(i, a[i], b[i]) for i in diffs[:5]])

eng = P.open_engine()
try:
    # three encodes of the same text in three sequences, saved to scratch
    shas = []
    for k, seq in enumerate((2, 3, 4)):
        eng.reset(seq)
        eng.write(seq, TEXT, add_bos=True)
        p = os.path.join(HERE, "scratch_enc%d.kvmem" % k)
        eng.save(seq, p)
        eng.reset(seq)
        shas.append(hashlib.sha256(open(p, "rb").read()).hexdigest()[:16])
    print("3x encode same text:", shas)
    # same text twice in the SAME sequence slot, back to back
    eng.reset(5)
    eng.write(5, TEXT, add_bos=True)
    p1 = os.path.join(HERE, "scratch_same1.kvmem")
    eng.save(5, p1); eng.reset(5)
    eng.write(5, TEXT, add_bos=True)
    p2 = os.path.join(HERE, "scratch_same2.kvmem")
    eng.save(5, p2); eng.reset(5)
    s1 = hashlib.sha256(open(p1,"rb").read()).hexdigest()[:16]
    s2 = hashlib.sha256(open(p2,"rb").read()).hexdigest()[:16]
    print("same seq twice:", s1, s2, "equal" if s1 == s2 else "DIFFER")
    # reference: pristine project.kvmem rebuild (known-good fixture, 18 cells + BOS?)
    man = P.load_manifest()
    for bid in ("project", "habit", "home"):
        m = man["blocks"]["m2"][bid]
        print("%s fixture: cells=%d sha16=%s" % (bid, m["cells"], m["sha256"][:16]))
finally:
    eng.close()
