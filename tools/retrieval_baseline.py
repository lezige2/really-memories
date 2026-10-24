# -*- coding: utf-8 -*-
"""Retrieval baseline for the paged-memory index (README-HANDOFF-2.md section 6.3).

Section 6.2 showed that paging the *right* block restores recall from 20% to 85%.
That number was produced with an oracle index, so it is an upper bound. The question
this script answers is the cheap one that decides the whole remaining path:

    how good is a dumb, dependency-free retriever at picking that block?

If plain character-bigram BM25 already lands near the ceiling, the index is an
engineering detail; if it lands at chance, the index is the project.

No model, no GPU, no training: tokenising Chinese by character bigrams is crude but
it is the honest floor. Anything cleverer (embeddings, the multi-facet schema) has to
beat this number by enough to justify itself.

Usage:
  python tools/retrieval_baseline.py [--dir tools/quality] [--tag 20k] [--k 3]
"""

import argparse
import math
import os
import sys
from collections import Counter


def norm(s: str) -> str:
    s = s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    # keep CJK, latin and digits; drop everything else (punctuation, spaces)
    return "".join(ch for ch in s if ch.isalnum())


def bigrams(s: str):
    s = norm(s)
    if len(s) < 2:
        return [s] if s else []
    return [s[i:i + 2] for i in range(len(s) - 1)]


def load_blocks(path):
    doc = open(path, encoding="utf-8").read()
    out = []
    pos = 0
    while pos < len(doc):
        sep = doc.find("\n\n", pos)
        if sep == -1:
            sep = len(doc)
        p = doc[pos:sep].strip()
        if p:
            out.append(p)
        pos = sep + 2
    return out


def load_qa(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 3:
            rows.append((int(p[0]), p[1], p[2]))
    return rows


def bm25_rank(query, docs, k1=1.2, b=0.75):
    """Return docs ranked by BM25 over character bigrams."""
    doc_terms = [Counter(bigrams(d)) for d in docs]
    n = len(docs)
    avgdl = sum(sum(c.values()) for c in doc_terms) / max(1, n)

    df = Counter()
    for c in doc_terms:
        for t in c:
            df[t] += 1

    q = Counter(bigrams(query))
    scores = []
    for c in doc_terms:
        dl = sum(c.values())
        s = 0.0
        for t, qf in q.items():
            if t not in c:
                continue
            idf = math.log(1.0 + (n - df[t] + 0.5) / (df[t] + 0.5))
            tf = c[t]
            s += idf * (tf * (k1 + 1)) / (tf + k1 * (1.0 - b + b * dl / avgdl)) * qf
        scores.append(s)
    order = sorted(range(n), key=lambda i: -scores[i])
    return order, scores


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "quality"))
    ap.add_argument("--tag", default="20k")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--emit-rank", default="", help="write qid<TAB>block_id for kvmem_page --rank")
    args = ap.parse_args()

    docs = load_blocks(os.path.join(args.dir, "doc_%s.txt" % args.tag))
    qa = load_qa(os.path.join(args.dir, "qa_%s.tsv" % args.tag))
    n = len(docs)
    print("blocks=%d  questions=%d  retriever=BM25 over character bigrams" % (n, len(qa)))
    print()

    hit1 = hitk = 0
    print("%-4s %-40s %-8s %s" % ("id", "question", "rank", "verdict"))
    print("-" * 78)
    for qid, question, expect in qa:
        order, _ = bm25_rank(question, docs)
        rank = order.index(qid) + 1 if qid in order else -1
        if rank == 1:
            hit1 += 1
        if 1 <= rank <= args.k:
            hitk += 1
        mark = "OK" if rank == 1 else ("top%d" % args.k if rank <= args.k else "miss")
        print("%-4d %-40s %-8d %s" % (qid, question[:38], rank, mark))

    print("-" * 78)
    print("retrieval@1 = %d/%d = %.0f%%" % (hit1, len(qa), 100.0 * hit1 / len(qa)))
    print("retrieval@%d = %d/%d = %.0f%%" % (args.k, hitk, len(qa), 100.0 * hitk / len(qa)))
    print()
    print("end-to-end upper bound at this retrieval quality:")
    print("  paged, correct block scores 85%%  ->  %.0f%% * 85%% = %.0f%%"
          % (100.0 * hit1 / len(qa), 100.0 * hit1 / len(qa) * 0.85))

    if args.emit_rank:
        with open(args.emit_rank, "w", encoding="utf-8", newline="\n") as f:
            f.write("# qid\tblock_id\t(from BM25 character-bigram baseline)\n")
            for qid, question, expect in qa:
                order, _ = bm25_rank(question, docs)
                f.write("%d\t%d\n" % (qid, order[0]))
        print()
        print("rank file -> %s  (feed to kvmem_page query --rank)" % args.emit_rank)
    return 0


if __name__ == "__main__":
    sys.exit(main())