# -*- coding: utf-8 -*-
"""hole_matrix.py -- P0-4: is a gap in the position line fatal, and where?

L4 ("positions must be contiguous, a hole of >= 1 destroys the output") was measured in
exactly one place: between the last block and the head of the chat. A fixed-slot layout
(M2) needs to know whether the rule is about that place or about gaps anywhere.

Things this script is careful about, because a careless matrix measures the wrong
variable:

  * absolute positions are pinned. The chat always starts at CHAT; the block adjacent to
    it always ends at CHAT. A gap is created by pushing lower content down, never by
    moving the chat.
  * every gap is measured twice: left EMPTY, and owned by a sacrificial sequence
    ("other"). Same geometry, so `other` is the control that separates "a gap exists"
    from "the layout is simply longer".
  * the filler is binary-searched to exactly `size` tokens, so the gap is fully occupied
    -- a half-filled gap would be neither arm.
  * three probes per case: the 工号 fact, the 上线日期 fact, and one that needs both.
    "Answered, but only recovered one side" is a distinct failure from "empty", and it is
    the more dangerous one.

Usage:
  python tools/hole_matrix.py           # batch 1: 5 positions x {1,8,256} x empty, plus controls
  python tools/hole_matrix.py --full    # add sizes 2 and 64
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import chat as demo                                    # noqa: E402
import memory_source as ms                             # noqa: E402
from kvslots import KVEngine                           # noqa: E402

DB = os.path.join(ROOT, "kvmem", "p0_4.db")
BLOCKS = os.path.join(ROOT, "kvmem", "p0_4_blocks")

CHAT = 4096
LIVE = 0
FILLER = 3
SEQ_A, SEQ_B = 4, 5

Q_PROFILE, X_PROFILE = "我的工号是多少？", "A-4417"
Q_PROJECT, X_PROJECT = "项目什么时候上线？", "3月14"
Q_CROSS = "我的工号和项目上线日期分别是什么？"

results = []


def filler_text(eng, size):
    """A text that encodes to exactly `size` tokens."""
    if size == 0:
        return ""
    lo, hi = 0, max(8, size * 4 + 32)
    while lo <= hi:
        mid = (lo + hi) // 2
        eng.reset(FILLER)
        eng.write_at(FILLER, "填" * mid, 0)
        n = eng.n_tokens(FILLER)
        eng.reset(FILLER)
        if n == size:
            return "填" * mid
        if n < size:
            lo = mid + 1
        else:
            hi = mid - 1
    return None


def place(eng, row, target, seq):
    """Load a block from its pristine file and put it at `target`. One shift."""
    eng.reset(seq)
    n = ms.load_into(eng, row, seq)
    base = eng.pos_max(seq) - n + 1
    if base != target:
        moved = eng.repos_local(seq, target - base)
        if moved != n:
            raise RuntimeError("repos moved %d of %d" % (moved, n))
    if eng.pos_max(seq) - n + 1 != target:
        raise RuntimeError("block landed at %d, wanted %d"
                           % (eng.pos_max(seq) - n + 1, target))
    eng.share(seq, LIVE, target, target + n)
    return n


def ask(eng, q, pos):
    a = eng.ask(LIVE, q, n_predict=32, pos=pos)
    return a.strip().splitlines()[0].strip() if a.strip() else ""


def gap_range(layout, size, pn, jn):
    if layout == "bottom":
        h = CHAT - pn - jn - size
    elif layout == "between":
        h = CHAT - jn - size
    elif layout == "chat_head":
        h = CHAT - size
    else:
        h = None
    return h


def layout_blocks(layout, size, pn, jn):
    """(name, target) pairs, chosen so the chat and its neighbour stay pinned."""
    if layout == "bottom":                      # [gap][profile][project][chat]
        return [("profile", CHAT - pn - jn), ("project", CHAT - jn)]
    if layout == "between":                     # [profile][gap][project][chat]
        return [("profile", CHAT - jn - size - pn), ("project", CHAT - jn)]
    if layout == "chat_head":                   # [profile][project][gap][chat]
        return [("profile", CHAT - size - pn - jn), ("project", CHAT - size - jn)]
    if layout == "chat_inner":                  # gap inside the chat's own tokens
        return [("profile", CHAT - pn - jn), ("project", CHAT - jn)]
    if layout == "chat_tail":                   # [profile][chat][gap][project]
        return [("profile", CHAT - pn)]
    raise ValueError(layout)


def occlude(eng, size, h):
    """Fill [h, h+size) with cells owned by another sequence."""
    if size == 1:
        # write_at always emits BOS first, so "1 token" is not addressable: write two
        # tokens from h-1 and let the second one own h. Geometry is otherwise identical.
        eng.reset(FILLER)
        eng.write_at(FILLER, "填", h - 1)
        if eng.n_tokens(FILLER) != 2 or eng.pos_max(FILLER) != h:
            return "size-1 filler landed wrong (%d tok, pos_max %d)"
        return None
    txt = filler_text(eng, size)
    if txt is None:
        return "cannot build an exactly-%d-token filler" % size
    eng.reset(FILLER)
    eng.write_at(FILLER, txt, h)
    if eng.n_tokens(FILLER) != size:
        return "filler is %d tokens, wanted %d" % (eng.n_tokens(FILLER), size)
    return None


def run_case(eng, blocks, layout, size, occ, reps=1):
    for s in range(8):
        eng.reset(s)
    pn, jn = blocks["profile"][7], blocks["project"][7]
    ans = {}

    if layout == "chat_inner":
        for nm, tgt in layout_blocks(layout, size, pn, jn):
            place(eng, blocks[nm], tgt, SEQ_A if nm == "profile" else SEQ_B)
        ans["q"] = ask(eng, Q_PROFILE, CHAT)
        jump = eng.pos_max(LIVE) + 1 + size          # the gap is here, in the chat itself
        ans["q"] += " | " + ask(eng, Q_PROJECT, jump)
        ans["cross_log"] = cross_repeat(eng, None, reps)
        st, why = verdict(ans, "gap inside the chat's token stream", reps)
        return st, why, ans

    if layout == "chat_tail":
        place(eng, blocks["profile"], CHAT - pn, SEQ_A)
        ans["q"] = ask(eng, Q_PROFILE, CHAT)
        ce = eng.pos_max(LIVE) + 1
        if occ == "other":
            err = occlude(eng, size, ce)
            if err:
                return "skip", err, ans
        place(eng, blocks["project"], ce + size, SEQ_B)
        ans["q"] += " | " + ask(eng, Q_PROJECT, None)
        ans["cross_log"] = cross_repeat(eng, None, reps)
        st, why = verdict(ans, "gap after the chat, block above it", reps)
        return st, why, ans

    h = gap_range(layout, size, pn, jn)
    if occ in ("other", "guard"):
        err = occlude(eng, size, h)
        if err:
            return "skip", err, ans
        if occ == "guard":
            eng.share(FILLER, LIVE, h, h + size)   # make the gap VISIBLE to the chat
    for nm, tgt in layout_blocks(layout, size, pn, jn):
        place(eng, blocks[nm], tgt, SEQ_A if nm == "profile" else SEQ_B)
    ans["q"] = ask(eng, Q_PROFILE, CHAT)
    ans["q"] += " | " + ask(eng, Q_PROJECT, None)
    ans["cross_log"] = cross_repeat(eng, None, reps)
    st, why = verdict(ans, "gap at [%d,%d)" % (h, h + size), reps)
    return st, why, ans


def verdict(ans, where, reps=1):
    text = " ".join(v for k, v in ans.items() if k != "cross_log")
    if not text.strip():
        return "empty", where + "; no output at all"
    got_p, got_j = X_PROFILE in text, X_PROJECT in text
    log = ans.get("cross_log") or [ans.get("cross", "")]
    hits = sum(1 for a in log if all(e in a for e in (X_PROFILE, X_PROJECT)))
    detail = "%s; 工号:%s 上线:%s cross:%d/%d" % (where, "y" if got_p else "n",
                                                  "y" if got_j else "n", hits, len(log))
    if hits or (got_p and got_j):
        return "ok", detail
    return "partial", detail


def cross_repeat(eng, pos, reps):
    """Ask the cross question `reps` times; two facts in one sentence is noisy."""
    log = []
    for i in range(reps):
        log.append(ask(eng, Q_CROSS, pos if i == 0 else None))
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--only", default=None, help="comma-separated layout names")
    ap.add_argument("--reps", type=int, default=1, help="repeats of the cross question")
    ap.add_argument("--show", action="store_true", help="print the raw answers")
    a = ap.parse_args()

    os.makedirs(BLOCKS, exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)
    con = ms.connect(DB)
    eng = KVEngine(ms.MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    try:
        for name, label, text in demo.MEMORIES:
            ms.put_source(con, name, label, text)
            ms.build_block(eng, con, ms.get_source(con, name), BLOCKS)
        rows = [r for r in ms.block_rows(con) if r[5] is not None]
        blocks = {r[1]: r for r in rows}
        pn, jn = blocks["profile"][7], blocks["project"][7]
        print("profile %d tok, project %d tok, chat pinned at %d\n" % (pn, jn, CHAT))

        sizes = [1, 8, 256] + ([2, 64] if a.full else [])
        want = a.only.split(",") if a.only else None
        pos_list = [l for l in ("bottom", "between", "chat_head", "chat_inner",
                                "chat_tail") if not want or l in want]
        arms = ["empty", "other", "guard"]
        cases = [(l, s, o) for l in pos_list for o in arms for s in sizes]

        print("%-11s %5s %-6s %-8s %s" % ("position", "size", "gap", "status", "detail"))
        print("-" * 118)
        for layout, size, occ in cases:
            st, why, ans = run_case(eng, blocks, layout, size, occ, a.reps)
            results.append((layout, size, occ, st, why))
            print("%-11s %5d %-6s %-8s %s" % (layout, size, occ, st, why))
            if a.show and ans:
                print("        q: %s" % ans.get("q", "")[:180].replace("\n", " "))
                print("        cross: %s" % " || ".join(
                    x[:90].replace("\n", " ") for x in ans.get("cross_log", [])))
    finally:
        eng.close()
        con.close()

    print("\n" + "=" * 118)
    groups = {}
    for layout, size, occ, st, _ in results:
        groups.setdefault((layout, occ), []).append((size, st))
    for (layout, occ), rs in groups.items():
        print("  %-11s %-6s %s" % (layout, occ,
                                    ", ".join("%d:%s" % (s, st) for s, st in sorted(rs))))

    print("\nverdict")
    def arm(layout, occ):
        return [st for (l, s, o, st, _) in results if l == layout and o == occ]
    for layout in ("bottom", "between", "chat_head", "chat_inner", "chat_tail"):
        e = arm(layout, "empty")
        if not e:
            continue
        if all(s == "ok" for s in e):
            word = "HARMLESS"
        elif any(s == "ok" for s in e):
            word = "PARTIAL  (some sizes survive)"
        else:
            word = "FATAL"
        print("  %-11s empty gap: %s" % (layout, word))
    for layout in ("bottom", "between", "chat_tail"):
        o = arm(layout, "other")
        if o:
            print("  %-11s occupied gap: %s" % (layout,
                  "HARMLESS" if all(s == "ok" for s in o) else "HARMFUL"))
    return 0


if __name__ == "__main__":
    sys.exit(main())