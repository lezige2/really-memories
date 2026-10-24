# -*- coding: utf-8 -*-
"""Unit tests for the M3 lease guard. No model, no GPU: a stub engine records every call.

  python -X utf8 kvmem/m2_visibility/m3/_test_lease.py
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m3_lease as L                                              # noqa: E402

HOME, PROJECT, HABIT = 1, 2, 3
LIVE, CTRL = 0, 6
BLOCKS = (HOME, PROJECT, HABIT)


class Stub:
    """Minimal stand-in for KVSlots: records calls, keeps a token count per seq."""

    def __init__(self):
        self.calls = []
        self.tokens = {HOME: 21, PROJECT: 18, HABIT: 12, LIVE: 0}

    def share(self, src, dst, lo, hi):
        self.calls.append(("share", int(src), int(dst), lo, hi))

    def drop(self, dst, lo, hi):
        self.calls.append(("drop", int(dst), lo, hi))

    def reset(self, seq):
        self.calls.append(("reset", int(seq)))
        if int(seq) in BLOCKS:
            self.tokens[int(seq)] = 0          # measured behaviour: no refusal, handle emptied

    def n_tokens(self, seq):
        return self.tokens.get(int(seq), 0)

    def reset_count(self, seq):
        return sum(1 for c in self.calls if c[0] == "reset" and c[1] == int(seq))


def fresh():
    eng = Stub()
    leases = L.BlockLeases(eng)
    for seq, name in ((HOME, "home"), (PROJECT, "project"), (HABIT, "habit")):
        leases.register_block(seq, name)
    return eng, leases


def main():
    fails = []

    def check(name, cond, extra=""):
        print("  %-56s %s %s" % (name, "PASS" if cond else "FAIL", extra if not cond else ""))
        if not cond:
            fails.append(name)

    print("\n# 1 the dangerous order is refused")
    eng, leases = fresh()
    leases.attach(HOME, LIVE, 4045, 4095)
    try:
        leases.reset(HOME)
        check("reset while referenced raises", False)
    except L.LeaseError as exc:
        check("reset while referenced raises", True)
        check("engine.reset was never called", eng.reset_count(HOME) == 0)
        check("message names the detach-first order", "Detach first" in str(exc))

    print("\n# 2 an unleased sequence still resets")
    leases.reset(CTRL)
    check("reset(CTRL) went through", eng.reset_count(CTRL) == 1)

    print("\n# 3 detach releases the lease")
    leases.detach(LIVE, 4045, 4095)
    check("no referrers after detach", leases.referrers(HOME) == [])
    leases.reset(HOME)
    check("reset after detach allowed", eng.reset_count(HOME) == 1)

    print("\n# 4 force=True is explicit, not silent")
    eng, leases = fresh()
    leases.attach(HOME, LIVE, 4045, 4095)
    leases.reset(HOME, force=True)
    kinds = [e["kind"] for e in leases.events]
    check("forced reset recorded in the log", "force_reset" in kinds)
    check("forced reset reached the engine", eng.reset_count(HOME) == 1)

    print("\n# 5 the run-1 trap")
    eng, leases = fresh()
    out = leases.safe_reset_all(range(8))
    check("block seqs are skipped", set(out["skipped"]) == set(BLOCKS), str(out["skipped"]))
    check("no block seq was reset", all(eng.reset_count(s) == 0 for s in BLOCKS))
    check("non-block seqs were reset", eng.reset_count(CTRL) == 1 and eng.reset_count(LIVE) == 1)
    shim = Stub()
    for s in range(8):
        shim.reset(s)
    check("raw reset_all empties a loaded block slot", shim.n_tokens(HOME) == 0)

    print("\n# 6 attaching an emptied block is refused (run-1 signature)")
    eng, leases = fresh()
    eng.reset(HOME)
    try:
        leases.attach(HOME, LIVE, 4045, 4095)
        check("attach on an empty block raises", False)
    except L.LeaseError as exc:
        check("attach on an empty block raises", True)
        check("message says reload from file", "reload it from its file" in str(exc))

    print("\n# 7 status is introspectable")
    eng, leases = fresh()
    leases.attach(HOME, LIVE, 4045, 4095)
    st = leases.status()
    check("status shows one leased block",
          st["any_leased"] and st["blocks"]["home"]["referrers"] == [LIVE])

    print("\n%d failed" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
