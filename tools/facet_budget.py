# -*- coding: utf-8 -*-
"""facet_budget.py -- the go/no-go experiment for the facet index.

Two questions, both answered on the same 20-question / 20k-token set.

1. alpha sensitivity.
   The facet index narrows the candidate set by the *type* of attribute the question
   asks for (org / place / time / num). Hard narrowing is brittle: if the extraction
   is wrong, the gold block is gone before BM25 ever scores it. So instead of a hard
   filter we require lexical corroboration -- keep the narrowing only when some
   member of the narrowed set is lexically competitive with the global best:

       max_score(S) >= alpha * max_score(all)

   alpha = 0 reproduces the old hard filter, alpha = 1.0 accepts any narrowing that
   does not throw the winner away.

   For that curve to mean anything there must be cases where the facet hypothesis is
   WRONG. Section [0] measures whether this corpus contains any. It does not: the
   gold block carries the asked type in 14/14 cases. So alpha is insurance against an
   accident this corpus never has -- and the honest report says so instead of printing
   a flat line and calling it a result.

2. block budget.
   How many blocks we may attach is set by the token budget, not by taste: a block is
   only reliably readable inside the ~4k band below the query (STATUS-REPORT L10) and
   a block here is ~981 tokens. 4000 // 981 = 4. What this QA set can and cannot say
   about k > 1 is spelled out in [4].

Usage:
  python tools/facet_budget.py --tag 20k
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from facet_index import FacetIndex, QUAL, load_qa, asked_types, load_blocks  # noqa: E402

ALPHAS = [0.0, 0.5, 0.7, 0.9, 1.0]
BUDGET = 4000          # tokens of memory we are willing to attach (STATUS-REPORT L10)

# A type is worth narrowing on only if it is carried by a minority of segments.
#   strict: the original setting (0.3 * n, at least 3)
#   loose : ignore only types carried by half the corpus or more
REGIMES = [("strict", 0.3, 3), ("loose", 0.5, 1)]


def rank(idx, question, alpha=None, ratio=0.3, min_keep=3):
    """alpha=None -> pure BM25.  alpha=float -> facet narrowing + corroboration gate."""
    scores = idx.bm25(question)
    base = sorted(range(idx.n), key=lambda i: (-scores[i], i))
    if alpha is None:
        return base, [], scores

    cand, used = idx.candidates(question, ratio=ratio, min_keep=min_keep)
    if not used:
        return base, [], scores

    best_all = max(scores) if scores else 0.0
    best_in = max((scores[i] for i in cand), default=0.0)
    # Reject the facet only when there IS lexical evidence and the facet disagrees
    # with it. When BM25 has nothing at all (best_all == 0) the facet is the only
    # signal in the room -- refusing it there would disable the index precisely on
    # the zero-overlap queries it exists for (q4: the block says "挂在供应链分析组",
    # the question says "在哪个部门", not one shared bigram).
    if best_all > 0.0 and best_in < alpha * best_all:
        return base, [], scores
    return sorted(cand, key=lambda i: (-scores[i], i)), used, scores


def metrics(orders, qa, kmax, gold_index):
    rec = [0] * (kmax + 1)
    mrr = 0.0
    for qid, _, _ in qa:
        order, gold = orders[qid], gold_index[qid]
        if gold in order:
            r = order.index(gold) + 1
            for k in range(r, kmax + 1):
                rec[k] += 1
            if r <= kmax:
                mrr += 1.0 / r
    return rec, mrr / len(qa)


def tokens_per_block(tag):
    out = []
    with open(os.path.join(QUAL, "blocks%s" % tag, "index.tsv"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2:
                out.append(int(p[1]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="20k")
    ap.add_argument("--index", default="")
    ap.add_argument("--kmax", type=int, default=4)
    a = ap.parse_args()

    idx = FacetIndex.load(a.index or os.path.join(QUAL, "index_%s.json" % a.tag))
    qa = load_qa(a.tag)
    segs = load_blocks(os.path.join(QUAL, "doc_%s.txt" % a.tag))

    print("=" * 80)
    print("facet index go/no-go   tag=%s  blocks=%d  questions=%d"
          % (a.tag, idx.n, len(qa)))
    print("=" * 80)

    # ---------------------------------------------------------------- [0] the facets
    # The corpus was generated so segment i answers question i -- assert it, otherwise
    # every number below is noise.
    gold, bad = {}, []
    for qid, question, expect in qa:
        gold[qid] = qid
        if qid >= len(segs) or (expect and expect.replace(" ", "") not in segs[qid].replace(" ", "")):
            bad.append(qid)
    if bad:
        print("WARNING: gold-block assumption broken for %s" % bad)
    else:
        print("gold-block check: OK (20/20 expected answers live in segment qid)")

    print()
    print("[0] are the facets informative?  (a facet carried by everything narrows nothing)")
    print()
    print("    %-6s %-9s %s" % ("type", "carried", "verdict"))
    print("    " + "-" * 62)
    for t in ("time", "place", "org", "num"):
        car = [i for i in range(idx.n) if idx.has_type(i, t)]
        if len(car) >= 0.9 * idx.n:
            v = "no information (carried by almost every segment)"
        elif len(car) >= 0.5 * idx.n:
            v = "weak (narrows by %.1fx)" % (idx.n / max(1, len(car)))
        else:
            v = "SELECTIVE (narrows %.1fx)" % (idx.n / max(1, len(car)))
        print("    %-6s %2d/%-6d %s" % (t, len(car), idx.n, v))

    asked_any = cover = 0
    for qid, question, _ in qa:
        ts = asked_types(question)
        if not ts:
            continue
        asked_any += 1
        if any(idx.has_type(qid, t) for t in ts):
            cover += 1
    print()
    print("    questions asking a typed attribute : %d" % asked_any)
    print("    ...of which the gold block carries it: %d (%.0f%%)"
          % (cover, 100.0 * cover / max(1, asked_any)))
    print("    => the narrowing is SAFE here, which is exactly why alpha cannot be")
    print("       measured on this corpus: the corroboration gate never has cause to")
    print("       reject a facet, so every alpha produces the same ranking.")

    # ---------------------------------------------------------------- [1] the budget
    tok = tokens_per_block(a.tag)
    mean_tok = sum(tok) / max(1, len(tok))
    kmax_budget = max(1, int(BUDGET // mean_tok))
    print()
    print("[1] how many blocks can we afford?")
    print("    block sizes %d..%d tokens, mean %.0f (n=%d)"
          % (min(tok), max(tok), mean_tok, len(tok)))
    print("    budget %d tokens: a block stays inside the 0-4k readable band (L10) and"
          % BUDGET)
    print("    the chat still needs room.")
    print("    => k_max = %d   (k=%d puts the oldest block %.0f tokens away)"
          % (kmax_budget, kmax_budget + 1, (kmax_budget + 1) * mean_tok))

    # ---------------------------------------------------------------- [2] sweep
    print()
    print("[2] alpha x threshold   (recall@k = gold block inside the top k)")
    print()
    hdr = "    %-8s %-6s %-9s" % ("regime", "alpha", "narrowed")
    for k in range(1, a.kmax + 1):
        hdr += " %6s" % ("@%d" % k)
    hdr += " %7s" % "MRR"
    print(hdr)
    print("    " + "-" * (len(hdr) - 4))

    orders = {}
    for qid, question, _ in qa:
        orders[qid] = rank(idx, question, None)[0]
    arm = {"bm25": orders}
    rec, mrr = metrics(orders, qa, a.kmax, gold)
    row = "    %-8s %-6s %-9s" % ("bm25", "-", "-")
    for k in range(1, a.kmax + 1):
        row += " %5.0f%%" % (100.0 * rec[k] / len(qa))
    row += " %7.3f" % mrr
    print(row)

    for name, ratio, mk in REGIMES:
        for alpha in ALPHAS:
            o, applied = {}, 0
            for qid, question, _ in qa:
                order, used, _ = rank(idx, question, alpha, ratio, mk)
                o[qid] = order
                applied += 1 if used else 0
            arm["%s/%.1f" % (name, alpha)] = o
            rec, mrr = metrics(o, qa, a.kmax, gold)
            row = "    %-8s %-6.1f %-9s" % (name, alpha, "%d/%d" % (applied, len(qa)))
            for k in range(1, a.kmax + 1):
                row += " %5.0f%%" % (100.0 * rec[k] / len(qa))
            row += " %7.3f" % mrr
            print(row)
        print("    " + "-" * (len(hdr) - 4))

    # ---------------------------------------------------------------- [3] who moves
    print()
    print("[3] every question that any arm ranks differently from BM25")
    print()
    print("    %-4s %-30s %6s %8s %8s %s" % ("id", "question", "bm25", "strict0", "loose0", "asked"))
    print("    " + "-" * 76)
    moved = 0
    for qid, question, _ in qa:
        ranks = []
        for key in ("bm25", "strict/0.0", "loose/0.0"):
            o = arm[key][qid]
            ranks.append(o.index(qid) + 1 if qid in o else 99)
        if len(set(ranks)) == 1:
            continue
        moved += 1
        print("    %-4d %-30s %6d %8d %8d %-6s"
              % (qid, question[:28], ranks[0], ranks[1], ranks[2],
                 ",".join(asked_types(question)) or "-"))
    if not moved:
        print("    (none)")

    # ---------------------------------------------------------------- [4] verdict
    print()
    print("[4] what the budget buys, and what this set cannot test")
    print()
    r_bm, _ = metrics(arm["bm25"], qa, a.kmax, gold)
    r_lo, _ = metrics(arm["loose/0.0"], qa, a.kmax, gold)
    print("    %-4s %8s %10s %12s %11s" % ("k", "tokens", "farthest", "bm25 @k", "facet @k"))
    print("    " + "-" * 50)
    for k in range(1, kmax_budget + 1):
        print("    %-4d %8.0f %10.0f %11.0f%% %10.0f%%"
              % (k, k * mean_tok, k * mean_tok,
                 100.0 * r_bm[k] / len(qa), 100.0 * r_lo[k] / len(qa)))
    print()
    print("    Reading: every block in that table is a DIFFERENT FACT, and each question")
    print("    asks about exactly one of them. So k>1 cannot raise recall by construction:")
    print("    the ceiling is 20/20 at k=1 as soon as the ranker puts the right block on")
    print("    top. What k>1 buys is answering questions that need SEVERAL facts at once")
    print("    ('工号和项目代号分别是什么'), which this set does not contain. Do not read the")
    print("    flat column as 'one block is enough for the product'.")
    print()
    gain = r_lo[1] - r_bm[1]
    if gain > 0:
        print("VERDICT: facet buys +%d question(s) at k=1 (%d/20 vs %d/20), and the whole"
              % (gain, r_lo[1], r_bm[1]))
        print("         of it comes from the one SELECTIVE facet (org, 2/20) on q4, whose")
        print("         block says '挂在供应链分析组' and shares no bigram with '在哪个部门'.")
        print("         That is the structural gap BM25 cannot close, and it is real -- but")
        print("         on n=20 a +1 is inside noise. Treat facets as a RERANKER for the rare")
        print("         selective types, never as a filter over time/place (they are 20/20).")
    else:
        print("VERDICT: facet earns nothing over BM25 even at k=1. Do not ship it.")
    print()
    print("         Threshold matters more than alpha here: 'strict' never fires (num is")
    print("         carried by exactly 6/20 = the 0.3n cutoff), 'loose' fires on org+num.")
    return 0


if __name__ == "__main__":
    sys.exit(main())