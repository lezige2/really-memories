# -*- coding: utf-8 -*-
"""Grade the "A" experiment output (tools/quality/results_*.tsv).

Matching rule: the expected answer must appear as a substring of the model output
after normalisation (case-folded, whitespace and common punctuation removed).
That is deliberately lenient -- we are measuring "did it recall the fact", not
"did it format the sentence the way we imagined".

Usage:
  python tools/grade_quality.py [--dir tools/quality] [--show-failures 5]

Exit code: 0 always (grading is a report, not a gate). The >=90% bar is applied by
the caller / the handoff doc.
"""

import argparse
import glob
import os
import re
import sys

PUNCT = "，。、？！：；「」『』（）()[]【】\"'`~·…—－-_,./\\|:;!?<>"
TRANS = {ord(c): None for c in PUNCT}
DIGIT_MAP = str.maketrans("０１２３４５６７８９", "0123456789")


def norm(s: str) -> str:
    s = s.translate(DIGIT_MAP).lower()
    s = s.replace(" ", "").replace("\u3000", "")
    return s.translate(TRANS)


def load_qa(path):
    rows = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            rows[int(parts[0])] = (parts[1], parts[2])
    return rows


def load_results(path):
    rows = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            rows[int(parts[0])] = {"arm": parts[1], "kv": parts[2],
                                   "n_doc": parts[3], "answer": parts[4]}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "quality"))
    ap.add_argument("--qa", default="qa.tsv", help="qa file name inside --dir")
    ap.add_argument("--glob", default="results_*.tsv", help="results glob inside --dir")
    ap.add_argument("--show-failures", type=int, default=6)
    args = ap.parse_args()

    qa = load_qa(os.path.join(args.dir, args.qa))
    if not qa:
        print("no %s found in %s" % (args.qa, args.dir))
        return 0

    files = sorted(glob.glob(os.path.join(args.dir, args.glob)))
    if not files:
        print("no results_*.tsv found in %s" % args.dir)
        return 0

    ids = sorted(qa)
    n_band = 5
    per_band = max(1, len(ids) // n_band)

    def band(i):
        return min(n_band - 1, i // per_band)

    print("=" * 78)
    print("A -- 5k-token memory quality: hits / questions")
    print("=" * 78)
    print("%-22s %8s %10s %10s" % ("run", "hits", "acc", "n_doc"))
    print("-" * 78)

    summary = []
    for path in files:
        res = load_results(path)
        if not res:
            continue
        hit = 0
        n_doc = "-"
        for i in ids:
            r = res.get(i)
            if not r:
                continue
            n_doc = r["n_doc"]
            if norm(qa[i][1]) and norm(qa[i][1]) in norm(r["answer"]):
                hit += 1
        name = os.path.basename(path)[len("results_"):-len(".tsv")]
        acc = 100.0 * hit / len(ids)
        summary.append((name, hit, acc, n_doc, res))
        print("%-22s %5d/%-2d %9.0f%% %10s" % (name, hit, len(ids), acc, n_doc))

    # Per-depth band table: does recall degrade with distance?
    print()
    print("-" * 78)
    print("by document depth (band 0 = start of the document, %d = end)" % (n_band - 1))
    print("%-22s %s" % ("run", " ".join("%6d" % b for b in range(n_band))))
    print("-" * 78)
    for name, hit, acc, n_doc, res in summary:
        cells = []
        for b in range(n_band):
            b_ids = [i for k, i in enumerate(ids) if band(k) == b]
            ok = sum(1 for i in b_ids
                     if i in res and norm(qa[i][1]) and norm(qa[i][1]) in norm(res[i]["answer"]))
            cells.append("%3d/%-2d" % (ok, len(b_ids)))
        print("%-22s %s" % (name, " ".join("%6s" % c for c in cells)))

    # Failures, so a "miss" can be told apart from a formatting artefact.
    if args.show_failures:
        print()
        print("-" * 78)
        print("sample misses (raw output, truncated)")
        print("-" * 78)
        shown = 0
        for name, hit, acc, n_doc, res in summary:
            for k, i in enumerate(ids):
                if shown >= args.show_failures:
                    break
                r = res.get(i)
                if not r:
                    continue
                if norm(qa[i][1]) in norm(r["answer"]):
                    continue
                print("[%s] id=%d band=%d Q=%s" % (name, i, band(k), qa[i][0]))
                print("    expect=%r  got=%r" % (qa[i][1], r["answer"][:110]))
                shown += 1

    return 0


if __name__ == "__main__":
    sys.exit(main())