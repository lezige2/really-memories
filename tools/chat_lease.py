# -*- coding: utf-8 -*-
"""chat.py -> M3 lease adapter.  M3's last open item: the guard wired into the product path.

Direction (frozen by the reviewer, 2026-10-25)
----------------------------------------------
Every `eng.reset` in chat.py goes through `GuardedLeases.reset`, which

  * refuses while the block seq is still referenced by a dialogue seq (M3 §5), and
  * asserts `cells_of(seq) == 0` immediately after the reset.

The second rule is the important one. `safe_reset_all(seqs)` is FORBIDDEN in the placement
path: it computes `skip = set(skip) | set(self.blocks)`, so every registered block seq is skipped,
the block is NOT cleared, and the following `load_into` piles new cells on top of the old ones --
position drifts and the cell count grows with no error at all. That is the mirror image of the
`reset_all` trap M3 §6 recorded, and it is why each site asserts emptiness instead of trusting
the call.

Every refusal is appended to `kvmem/lease_refusals.jsonl` and re-raised: a refusal is never
swallowed (an unlogged refusal is exactly how the guard would become "ready but unwired" again).

Known limitation, by design: `tools/session_state.py` manages its own share/drop inside
`save_session` / `restore_session` (it is out of scope for this change), so the table is not
synchronised across those calls. No `reset` follows them in the same process, so the table
cannot produce a false refusal there.
"""
from __future__ import annotations

import json
import os
import sys
import time

_ROOT = r"D:/llama-mem"
_M3 = os.path.join(_ROOT, "kvmem", "m2_visibility", "m3")
if _M3 not in sys.path:
    sys.path.insert(0, _M3)

from m3_lease import BlockLeases, LeaseError                      # noqa: E402,F401

REFUSAL_LOG = os.environ.get("CHAT_LEASE_REFUSALS", os.path.join(_ROOT, "kvmem", "lease_refusals.jsonl"))
EVENT_LOG = os.environ.get("CHAT_LEASE_EVENTS", os.path.join(_ROOT, "kvmem", "lease_events.jsonl"))


def _append(path, rec):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass                                                   # logging never breaks the run


class GuardedLeases(BlockLeases):
    """BlockLeases + a post-reset emptiness assertion + refusal logging."""

    def __init__(self, eng, log=None, site_prefix=""):
        super().__init__(eng, log)
        self.site_prefix = site_prefix
        self.counts = {"reset": 0, "refused": 0, "attached": 0, "detached": 0}
        self.sites = {}

    # -- the gated reset ---------------------------------------------------
    def reset(self, seq, force=False, site=""):
        tag = site or (self.site_prefix + ".reset")
        try:
            super().reset(seq, force=force)
        except LeaseError as exc:
            self.counts["refused"] += 1
            rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "site": tag, "seq": int(seq),
                   "kind": "refused", "message": str(exc),
                   "referrers": self.referrers(seq)}
            _append(REFUSAL_LOG, rec)
            _append(EVENT_LOG, rec)
            raise                                              # never swallowed
        cells = self.cells_of(seq)
        self.counts["reset"] += 1
        self.sites.setdefault(tag, []).append({"seq": int(seq), "cells_after": cells})
        rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "site": tag, "seq": int(seq),
               "kind": "reset", "cells_after": cells}
        _append(EVENT_LOG, rec)
        if cells != 0:
            raise LeaseError(
                "reset(seq %d) at %s left %d cells -- the block was NOT cleared "
                "(safe_reset_all trap: load_into would stack on stale cells)" % (int(seq), tag, cells))
        return True

    # -- attach / detach keep the table honest -----------------------------
    def attach(self, block_seq, dst_seq, lo, hi, site=""):
        tag = site or (self.site_prefix + ".attach")
        super().attach(block_seq, dst_seq, lo, hi)
        self.counts["attached"] += 1
        _append(EVENT_LOG, {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "site": tag,
                            "kind": "attach", "block_seq": int(block_seq),
                            "dst_seq": int(dst_seq), "lo": int(lo), "hi": int(hi)})

    def detach(self, dst_seq, lo, hi, site=""):
        tag = site or (self.site_prefix + ".detach")
        block_seq = super().detach(dst_seq, lo, hi)
        self.counts["detached"] += 1
        _append(EVENT_LOG, {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "site": tag,
                            "kind": "detach", "block_seq": block_seq,
                            "dst_seq": int(dst_seq), "lo": int(lo), "hi": int(hi)})
        return block_seq

    def report(self):
        return {"counts": dict(self.counts), "sites": self.sites,
                "refusals_logged": self.counts["refused"],
                "all_sites_asserted_empty": all(e["cells_after"] == 0
                                                for evs in self.sites.values() for e in evs)}
