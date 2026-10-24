# -*- coding: utf-8 -*-
"""Recall vs. distance: where does the frozen model stop reading?

Takes every results_<tag>_kv_<kv>.tsv in tools/quality, joins it with meta_<tag>.tsv
(the character offset of each planted fact) and qa_<tag>.tsv (the expected answer),
and bins each question by "how many tokens of memory sit between the fact and the
question".

That distance is the number that matters: it is what attention has to reach across.
A flat curve means the model reads the whole memory; a decaying curve locates the
point where extra context stops being useful, which is the design constraint for the
memory layout (paging / retrieval gating / compression).

Usage:
  python tools/recall_curve.py [--dir tools/quality]
"""

import argparse
import glob
import os
import sys

BINS = [(0, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000), (16000, 10 ** 9)]


def norm(s: str) -> str:
    s = s.translate(str.maketrans("０１２３４５６７８９", "0123456789")).lower().replace(" ", "")
    for c in "，。、？！：；「」『』（）()[]\"'`~·…—－_,./\\|:;!?<>":
        s = s.replace(c, "")
    return s


def load_qa(path):
    qa = {}
    for line in open(path, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 3:
            qa[int(p[0])] = p[2]
    return qa


def load_meta(path):
    off = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#"):
            continue
        p = line.rstrip("\n").split("\t")
        if len(p) >= 3:
            off[int(p[0])] = int(p[1])
    return off


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "quality"))
    args = ap.parse_args()

    points = []   # (tag, kv, n_doc, distance_tokens, hit)
    for path in sorted(glob.glob(os.path.join(args.dir, "results_*_kv_*.tsv"))):
        base = os.path.basename(path)[len("results_"):-len(".tsv")]
        tag, kv = base.rsplit("_kv_", 1)
        qa_p  = os.path.join(args.dir, "qa_%s.tsv" % tag)
        meta_p = os.path.join(args.dir, "meta_%s.tsv" % tag)
        doc_p = os.path.join(args.dir, "doc_%s.txt" % tag)
        if not (os.path.exists(qa_p) and os.path.exists(meta_p) and os.path.exists(doc_p)):
            continue
        qa, meta = load_qa(qa_p), load_meta(meta_p)
        n_chars = len(open(doc_p, encoding="utf-8").read())

        for line in open(path, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) < 5:
                continue
            qi, n_doc, got = int(p[0]), int(p[3]), p[4]
            if qi not in meta or qi not in qa:
                continue
            # char offset -> token offset (linear; the corpus is uniform Chinese prose)
            tok = meta[qi] * (n_doc / float(n_chars))
            dist = n_doc - int(tok)
            hit = norm(qa[qi]) in norm(got)
            points.append((tag, kv, n_doc, dist, hit))

    if not points:
        print("no results found")
        return 0

    print("=" * 74)
    print("recall vs distance from the question")
    print("=" * 74)
    print("%-14s %8s %8s %10s %10s" % ("bin (tokens)", "n", "hits", "recall", ""))
    print("-" * 74)
    for lo, hi in BINS:
        sel = [p for p in points if lo <= p[3] < hi]
        if not sel:
            continue
        hits = sum(1 for p in sel if p[4])
        label = "%d-%dk" % (lo // 1000, hi // 1000) if hi < 10 ** 9 else ">%dk" % (lo // 1000)
        bar = "#" * int(round(40.0 * hits / len(sel)))
        print("%-14s %8d %8d %9.0f%% %s" % (label, len(sel), hits, 100.0 * hits / len(sel), bar))

    print()
    print("-" * 74)
    print("per-run")
    print("-" * 74)
    for tag, kv, n_doc in sorted({(p[0], p[1], p[2]) for p in points}):
        sel = [p for p in points if p[0] == tag and p[1] == kv]
        hits = sum(1 for p in sel if p[4])
        print("%-8s %-6s memory=%6d tokens   %2d/%2d = %3.0f%%"
              % (tag, kv, n_doc, hits, len(sel), 100.0 * hits / len(sel)))

    print()
    print("raw points (distance in tokens, X = hit)")
    for tag, kv, n_doc in sorted({(p[0], p[1], p[2]) for p in points}):
        sel = sorted([p for p in points if p[0] == tag and p[1] == kv], key=lambda p: p[3])
        print("%-8s %s" % (tag, " ".join("%5d%s" % (p[3], "X" if p[4] else ".") for p in sel)))
    return 0


if __name__ == "__main__":
    sys.exit(main())