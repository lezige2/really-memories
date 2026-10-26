#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M6a-2 probe I3: pending `has_shift` survives a pos_move, so the next decode
rotates K a second time.

NON-PRODUCT STUB.  No model, no kvshim, no GPU.  The state machine mirrors:

  pos_add(i,d)  (llama-kv-cells.h:448-475):
      seq_pos_rm(i); pos[i]+=d; shift[i]+=d; has_shift=true;
      if (pos[i]<0) {...}; seq_pos_add(i); return false;

  pos_move(i,d) (llama-kv-cells.h:482-505):
      seq_pos_rm(i); pos[i]+=d;
      // NO shift[] / has_shift bookkeeping
      if (pos[i]<0) {...}; seq_pos_add(i); return false;

  build_graph_shift / decode (llama-kv-cache.cpp:1193-1213):
      if (get_has_shift()) rotate K by shift[] once; then reset_shift().

The bad combination: seq_add() on a set of cells, then seq_repos_local() on the
same cells.  `seq_repos_local()` rotates K itself and calls pos_move(), which
leaves the pending shift from seq_add() alive -> the next decode rotates again.
"""
import json
import sys


class StubEngine:
    """Cells + the two position operations + one decode rotation counter."""

    def __init__(self, n=50):
        self.n = n
        self.pos = list(range(n))
        self.shift = [0] * n
        self.has_shift = False
        self.rotations = 0
        self.rotation_log = []

    def _rotate(self, why):
        # one build_graph_shift pass (whole-tensor K rotation)
        self.rotations += 1
        self.rotation_log.append({"why": why, "pending": list(self.shift),
                                  "has_shift": self.has_shift})

    def seq_add(self, d, p0=0, p1=10 ** 9):
        n = 0
        for i in range(self.n):
            if not (p0 <= self.pos[i] < p1):
                continue
            self.pos[i] += d
            self.shift[i] += d
            self.has_shift = True
            n += 1
        return n

    def repos_local(self, d, p0=0, p1=10 ** 9):
        # seq_repos_local(): rotates K itself, then calls pos_move()
        n = 0
        for i in range(self.n):
            if not (p0 <= self.pos[i] < p1):
                continue
            self.pos[i] += d
            n += 1
        self._rotate("seq_repos_local")
        return n

    def decode(self):
        if self.has_shift:
            self._rotate("decode.pending_shift")
            self.shift = [0] * self.n
            self.has_shift = False
            return True
        return False

    def state(self):
        return {"pos_range": [min(self.pos), max(self.pos)],
                "shift_nonzero": sum(1 for x in self.shift if x),
                "has_shift": self.has_shift, "rotations": self.rotations,
                "rotation_log": self.rotation_log}


def check_after_local_move(e):
    """Expected invariant: a local move must not leave a pending K-shift."""
    assert not e.has_shift, "pending has_shift survived pos_move"
    assert e.rotations == 1, "expected exactly one rotation, got %d" % e.rotations


def safe_arm():
    e = StubEngine()
    moved = e.repos_local(+5)
    checker_raised = None
    try:
        check_after_local_move(e)
    except AssertionError as exc:
        checker_raised = str(exc)
    return {"arm": "safe", "moved": moved, "state": e.state(),
            "checker_raised": checker_raised, "invariant_holds": checker_raised is None}


def red_arm():
    e = StubEngine()
    n_add = e.seq_add(+10)          # pending shift: has_shift=true
    moved = e.repos_local(+5)       # rotates K once; pos_move leaves has_shift
    pending_before_decode = e.has_shift
    checker_raised = None
    try:
        check_after_local_move(e)
    except AssertionError as exc:
        checker_raised = str(exc)
    rotated_at_decode = e.decode()  # second rotation
    return {"arm": "red", "seq_add_moved": n_add, "repos_local_moved": moved,
            "pending_before_decode": pending_before_decode,
            "state_before_decode": {"has_shift": e.has_shift, "rotations": e.rotations,
                                    "shift": e.shift},
            "checker_raised": checker_raised,
            "rotated_at_decode": rotated_at_decode,
            "state_after_decode": e.state(),
            "invariant_holds": checker_raised is None,
            "extra_rotation": e.rotations - 1}


def main():
    safe = safe_arm()
    red = red_arm()
    out = {
        "schema": "m6a2_probe_i3_v1",
        "invariant": "I3: pending shift[]/has_shift from seq_add survives pos_move, "
                     "so the next decode rotates K again (double rotation)",
        "stub": "pure Python state machine; no kvshim/DLL/model/GPU",
        "source_anchor": "llama.cpp/src/llama-kv-cells.h:448-475 (pos_add) / "
                         "482-505 (pos_move); llama-kv-cache.cpp:1193-1213 (decode shift)",
        "safe_arm": safe,
        "red_arm": red,
        "red_proof": {
            "observed": {"has_shift_after_repos_local": red["pending_before_decode"],
                         "rotations_after_decode": red["state_after_decode"]["rotations"],
                         "extra_rotation": red["extra_rotation"],
                         "assertion_raised": red["checker_raised"] is not None},
            "expected_safe": {"has_shift_after_repos_local": False,
                              "rotations_after_decode": 1},
            "failure_signature": "pending has_shift=%s after pos_move; decode performs "
                                 "rotation #%d (one extra); assertion raised: %s"
                                 % (red["pending_before_decode"],
                                    red["state_after_decode"]["rotations"],
                                    red["checker_raised"]),
        },
        "product_reachability": {
            "verdict": "未接上",
            "reason": "product (chat.py/S1/m1) has no seq_add call; the only seq_add users are "
                      "tool arms kvdrift.py:135 / diag_place.py:82 / kvslots.py:563; "
                      "tools/kvmem_persist.cpp:497 is a C++ tool with no subsequent repos_local",
        },
        "artificial_note": "seq_add + repos_local combination is constructed by this probe / tool "
                            "arms; it is not a product call site and does not count as product-reachable",
        "no_gpu": True,
        "no_model": True,
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())