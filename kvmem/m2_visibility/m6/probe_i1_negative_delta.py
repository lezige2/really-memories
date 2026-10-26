#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M6a-2 probe I1: negative-delta underflow in cells.pos_move.

NON-PRODUCT STUB.  This probe never loads a model, never opens kvshim, and
never uses the GPU.  It is a faithful state-machine transcription of the three
relevant bookkeeping operations in llama.cpp/src/llama-kv-cells.h:

  pos_move(i, d):
      seq_pos_rm(i); pos[i] += d;
      if (pos[i] < 0) { seq[i].reset(); pos[i] = -1; shift[i] = 0;
                        used.erase(i); return true; }
      seq_pos_add(i); return false;

  seq_share: cell's seq bitset has more than one sequence, and there is no
  refcount.  In the underflow branch `seq[i].reset()` clears *all* referrers.

The probe has two arms:
  safe  : move(seq1, +100)  -> seq2's refs and position window follow unchanged
  red   : move(seq1, -1000) -> both seqs lose all cells, while the return value
                               still reports `moved=50` and the per-seq token
                               vector (simulated tokens[]) is unchanged.

The red arm is the failure signature, not a claim that product currently
constructs it.  Product call sites are enumerated in M6A2-REACHABILITY.json.
"""
import json
import sys

N = 50


class Cell:
    __slots__ = ("pos", "seqs")

    def __init__(self, pos, seqs):
        self.pos = pos
        self.seqs = set(seqs)


class Arena:
    """Minimal cells + pos_move + share, no engine, no model, no GPU."""

    def __init__(self, n=N):
        self.cells = [Cell(i, {1}) for i in range(n)]
        self.tokens = {1: n, 2: 0}       # load() fills tokens[] only for the
                                         # sequence that loaded; share() does not.
        self.used = set(range(n))

    def share(self, src, dst):
        for c in self.cells:
            if src in c.seqs:
                c.seqs.add(dst)

    def move(self, seq, delta, p0=0, p1=10 ** 9):
        moved = 0
        lost = []
        for c in self.cells:
            if seq not in c.seqs or not (p0 <= c.pos < p1):
                continue
            moved += 1
            c.pos += delta
            if c.pos < 0:
                # seq[i].reset() -- clears every referrer, not just `seq`
                lost.append(sorted(c.seqs))
                c.seqs.clear()
                c.pos = -1
                self.used.discard(self.cells.index(c))
        return moved, lost

    def exhibit(self, seq):
        ps = sorted(c.pos for c in self.cells if seq in c.seqs and c.pos >= 0)
        return {"n_cells": len(ps), "pos_range": [ps[0], ps[-1]] if ps else [],
                "tokens": self.tokens.get(seq)}

    def all_exhibit(self):
        return {str(s): self.exhibit(s) for s in (1, 2)}


def invariant(after, moved, expected_moved, seq2_cells):
    """The property that must hold after any successful local move."""
    assert moved == expected_moved, "moved=%r expected=%r" % (moved, expected_moved)
    assert after["2"]["n_cells"] == seq2_cells, (
        "seq2 refs lost: n_cells=%r expected=%r" % (after["2"]["n_cells"], seq2_cells))
    assert after["1"]["n_cells"] == expected_moved, (
        "seq1 cells=%r expected=%r" % (after["1"]["n_cells"], expected_moved))


def run_safe():
    a = Arena()
    a.share(1, 2)
    before = a.all_exhibit()
    moved, lost = a.move(1, +100)
    after = a.all_exhibit()
    invariant(after, moved, N, N)
    return {"arm": "safe", "delta": +100, "before": before, "after": after,
            "moved": moved, "lost_cell_groups": lost,
            "invariant_holds": True}


def run_red():
    a = Arena()
    a.share(1, 2)
    before = a.all_exhibit()
    moved, lost = a.move(1, -1000)
    after = a.all_exhibit()
    # The assertion is deliberately the *same* invariant as the safe arm.
    # It must raise here; catching it is the red proof.
    try:
        invariant(after, moved, N, N)
        raised = None
    except AssertionError as exc:
        raised = str(exc)
    return {"arm": "red", "delta": -1000, "before": before, "after": after,
            "moved": moved, "lost_cell_groups": lost,
            "tokens_unchanged": after["1"]["tokens"] == before["1"]["tokens"]
                                and after["2"]["tokens"] == before["2"]["tokens"],
            "assertion_raised": raised is not None,
            "assertion_error": raised,
            "invariant_holds": False}


def main():
    safe = run_safe()
    red = run_red()
    out = {
        "schema": "m6a2_probe_i1_v1",
        "invariant": "I1: negative delta underflow in cells.pos_move silently drops shared cell refs",
        "stub": "pure Python state-machine transcription; no kvshim/DLL/model/GPU",
        "source_anchor": "llama.cpp/src/llama-kv-cells.h:448-501 (pos_move); "
                         "seq[i].reset() clears all referrers",
        "n_cells": N,
        "safe_arm": safe,
        "red_arm": red,
        "red_proof": {
            "observed": {"moved": red["moved"], "seq1_cells": red["after"]["1"]["n_cells"],
                         "seq2_cells": red["after"]["2"]["n_cells"],
                         "tokens_unchanged": red["tokens_unchanged"]},
            "expected_safe": {"moved": N, "seq1_cells": N, "seq2_cells": N},
            "failure_signature": "moved still 50; both seq cells -> 0; tokens[] unchanged; "
                                 "assertion raised: %s" % red["assertion_error"],
        },
        "product_reachability": {
            "verdict": "未接上",
            "reason": "product repos_local deltas are positive after fresh load (base=0,target>0); "
                      "chat.py:353 -64 is paired after +64; m4_write.py:232 targets 0, not <0",
        },
        "artificial_note": "stub construction of a negative delta is not a product call site; "
                            "it does not qualify as product-reachable evidence",
        "no_gpu": True,
        "no_model": True,
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())