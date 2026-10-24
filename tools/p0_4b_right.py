# -*- coding: utf-8 -*-
"""p0_4b_right.py -- B-right: right-aligned slots, several gaps at once.

The matrix in hole_matrix.py tested ONE gap at a time. A fixed-slot layout produces one
gap per slot, so the question is whether gaps compose. B-right also removes the guard
from the design: if every block's tail is flush with its slot's tail, then the top block
is flush with the chat anchor and there is no gap directly below the chat head -- the one
arrangement P0-4 proved fatal.

    slot 0: [ gap ][ block C ]        <- tail flush with the chat anchor
    slot 1: [ gap ][ block B ]
    slot 2: [ gap ][ block A ]
    ...
    chat starts exactly at the anchor

Three arms, same blocks and same questions:

  A. contiguous   -- no slots, blocks packed tightly (the baseline)
  B. right        -- slots, every block tail-aligned (the proposal)
  C. left         -- slots, every block head-aligned: the top block ends before the
                     anchor, so there IS an invisible gap below the chat head. This arm
                     must fail, otherwise the test cannot tell the two apart.

Run:  python tools/p0_4b_right.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import memory_source as ms                             # noqa: E402
from kvslots import KVEngine                           # noqa: E402

DB = os.path.join(ROOT, "kvmem", "p0_4b.db")
BLOCKS = os.path.join(ROOT, "kvmem", "p0_4b_blocks")

CHAT = 4096
SLOT = 64
GAPS = [14, 28, 44]      # gap below each block, top-down
LIVE = 0

SOURCES = [
    ("profile", "我的档案", "我的工号是A-4417，隶属平台研发部，直属上级是周敏。"),
    ("project", "项目档案", "项目代号蓝鲸，计划3月14日上线，目前处于联调阶段。"),
    ("habit", "个人习惯", "我的咖啡只喝美式，不加糖，也不用奶精。"),
]
FACTS = {
    "profile": "A-4417",
    "project": "3月14",
    "habit": "美式",
}
QUESTIONS = [
    ("工号", "我的工号是多少？", ("A-4417",)),
    ("上线", "项目什么时候上线？", ("3月14",)),
    ("习惯", "我喝咖啡有什么习惯？", ("美式",)),
    ("跨三块", "我的工号、项目上线日期、喝咖啡的习惯分别是什么？", ("A-4417", "3月14", "美式")),
]

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print("  [%s] %-46s %s" % ("PASS" if ok else "FAIL", name, detail))


def place(eng, row, target, seq):
    eng.reset(seq)
    n = ms.load_into(eng, row, seq)
    base = eng.pos_max(seq) - n + 1
    if base != target:
        moved = eng.repos_local(seq, target - base)
        if moved != n:
            raise RuntimeError("repos moved %d of %d" % (moved, n))
    eng.share(seq, LIVE, target, target + n)
    return n


def run_arm(eng, rows, arm):
    for s in range(8):
        eng.reset(s)
    laid = []
    if arm == "contiguous":
        cursor = CHAT
        for i, (name, _l, _t) in enumerate(SOURCES, start=1):
            n = rows[name][7]
            tgt = cursor - n
            place(eng, rows[name], tgt, i)
            laid.append((name, tgt, tgt + n, n))
            cursor = tgt
    elif arm == "right_gaps":
        # each block tail-aligned inside its slot; the gap below each block follows the
        # requested curve (14 / 28 / 44 cells) instead of a uniform slot length
        cursor = CHAT
        for i, (name, _l, _t) in enumerate(SOURCES):
            n = rows[name][7]
            tgt = cursor - n
            place(eng, rows[name], tgt, i + 1)
            laid.append((name, tgt, tgt + n, n))
            cursor = tgt - GAPS[i]
    else:
        for i, (name, _l, _t) in enumerate(SOURCES, start=1):
            n = rows[name][7]
            tail = CHAT - (i - 1) * SLOT
            tgt = tail - n if arm == "right" else tail - SLOT
            place(eng, rows[name], tgt, i)
            laid.append((name, tgt, tgt + n, n))

    # geometry: is the chain up to the anchor contiguous, and where are the gaps?
    gaps = []
    spans = []
    for name, lo, hi, n in laid:
        spans.append("%s[%d,%d)" % (name, lo, hi))
        gaps.append((lo, hi))
    out = {}
    out["spans"] = " ".join(spans)
    pos = CHAT
    for name, lo, hi, n in laid:
        if lo == pos:
            pos = lo
    out["chain_reaches_anchor"] = any(hi == CHAT for _n, _l, hi, _k in laid)

    answers = {}
    total = 0
    first = True
    for key, q, expect in QUESTIONS:
        a = eng.ask(LIVE, q, n_predict=48, pos=(CHAT if first else None))
        first = False
        total += eng.n_tokens(LIVE)
        answers[key] = a.strip().replace("\n", " ")[:120]
    out["answers"] = answers
    out["n_tokens"] = eng.n_tokens(LIVE)
    out["generated"] = out["n_tokens"] > 0
    return out


def main():
    os.makedirs(BLOCKS, exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)
    con = ms.connect(DB)
    eng = KVEngine(ms.MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    try:
        for name, label, text in SOURCES:
            ms.put_source(con, name, label, text)
            ms.build_block(eng, con, ms.get_source(con, name), BLOCKS)
        rows = {r[1]: r for r in ms.block_rows(con) if r[5] is not None}
        lens = {k: rows[k][7] for k in rows}
        print("block lengths: %s   (slot = %d, anchor = %d)\n"
              % (lens, SLOT, CHAT))
        for k, n in lens.items():
            if n > SLOT:
                print("  ! %s is %d tokens, longer than the slot" % (k, n))

        runs = {}
        for arm in ("contiguous", "right", "right_gaps", "left"):
            out = run_arm(eng, rows, arm)
            runs[arm] = out
            print("[%s]" % arm)
            print("   spans: %s" % out["spans"])
            print("   decode produced tokens: %s (n_tokens=%d)"
                  % (out["generated"], out["n_tokens"]))
            for key, _q, expect in QUESTIONS:
                a = out["answers"][key]
                hit = all(e in a for e in expect)
                print("   %-6s %s  %s" % (key, "OK " if hit else "MISS", a[:74]))
            print()

        print("=" * 78)
        c, r, g, l = (runs["contiguous"], runs["right"],
                      runs["right_gaps"], runs["left"])

        def score(out):
            return sum(1 for key, _q, exp in QUESTIONS
                       if all(e in out["answers"][key] for e in exp))

        check("control (contiguous) generates", c["generated"], "n_tokens=%d" % c["n_tokens"])
        check("control (contiguous) answers 4/4", score(c) == 4, "%d/4" % score(c))
        check("B-right generates (decode accepted)", r["generated"],
              "n_tokens=%d" % r["n_tokens"])
        check("B-right answers 4/4 across three slots", score(r) == 4, "%d/4" % score(r))
        check("B-right: top block flush with the anchor", r["chain_reaches_anchor"],
              "no gap below the chat head")
        check("B-right with gaps 14/28/44 generates", g["generated"],
              "n_tokens=%d" % g["n_tokens"])
        check("B-right with gaps 14/28/44 answers 4/4", score(g) == 4, "%d/4" % score(g))
        check("left-aligned control FAILS as predicted", not l["generated"],
              "n_tokens=%d (must be 0)" % l["n_tokens"])
        check("gaps compose without eroding answers", score(r) == score(c),
              "right %d/4 vs contiguous %d/4" % (score(r), score(c)))
    finally:
        eng.close()
        con.close()

    bad = [x for x in results if not x[1]]
    print("\n%s  %d/%d checks passed" % ("=" * 78, len(results) - len(bad), len(results)))
    for n, _o, d in bad:
        print("  FAILED: %s (%s)" % (n, d))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())