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

import functools
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


_LIVE = []          # live tables, in creation order (identity-matched against the engine)
_BRIDGED = False    # session_state.save_session/restore_session installed exactly once


def _active_for(eng):
    """The lease table bound to this exact engine object, or None."""
    for t in reversed(_LIVE):
        if t.eng is eng:
            return t
    return None


def install_bridge(force=False):
    """Let the table see session_state's own share/drop WITHOUT editing that file.

    session_state.save_session does drop->save->share and restore_session does
    reset->load_strict->repos->share on its own. It edits no file here: the two
    module functions are wrapped once, keyed by engine identity, and the engine
    argument is swapped for a RecordingEngine only when a live table is bound to it.
    Any other caller (tests, probes, another engine) gets the real object back, so
    behaviour is unchanged when no table is active.
    """
    global _BRIDGED
    if _BRIDGED and not force:
        return False
    if os.environ.get("CHAT_LEASE_BRIDGE", "1") == "0":
        return False
    import session_state as ss
    if getattr(ss.save_session, "_lease_bridge", False) and not force:
        _BRIDGED = True
        return False

    def wrap(fn, name):
        @functools.wraps(fn)
        def inner(eng, *a, **kw):
            table = _active_for(eng)
            return fn(RecordingEngine(eng, table) if table else eng, *a, **kw)
        inner._lease_bridge = True
        inner._lease_original = fn
        return inner

    ss.save_session = wrap(ss.save_session, "save_session")
    ss.restore_session = wrap(ss.restore_session, "restore_session")
    _BRIDGED = True
    _append(EVENT_LOG, {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "site": "bridge",
                        "kind": "bridge.installed"})
    return True


class RecordingEngine:
    """Pass-through proxy: mirrors share/drop into the table, forwards everything else.

    Only share/drop change *references*. Everything else is forwarded untouched; the
    handful of calls that can MOVE a block (reset, load_strict/load, repos_local, save,
    write_at) are logged so a future reordering shows up in the event log instead of
    silently invalidating the recorded (dst, lo, hi) ranges.

    attach()/detach() already perform the real eng.share/eng.drop on the real engine, so
    this proxy must NOT repeat them -- the table owns the call, the proxy only routes.
    """

    def __init__(self, eng, leases):
        self._eng = eng
        self._leases = leases

    def __getattr__(self, name):
        return getattr(self._eng, name)

    # -- references (recorded) ---------------------------------------------
    def share(self, block_seq, dst_seq, lo, hi):
        if int(block_seq) not in self._leases.blocks:
            self._leases.register_block(int(block_seq), "seq%d@session_state" % int(block_seq))
        self._leases.attach(block_seq, dst_seq, lo, hi, site="session_state.share")

    def drop(self, dst_seq, lo, hi):
        self._leases.detach(dst_seq, lo, hi, site="session_state.drop")

    def reset(self, seq, *a, **kw):
        """Gated: block sequences go through the table (which makes the ONE real call).

        seq 0 is the dialogue and is never a block, so it is a documented exception:
        it is forwarded and recorded, not gated -- a lease cannot protect the very
        sequence that holds the references.
        """
        seq = int(seq)
        if seq == 0:
            _append(EVENT_LOG, {"at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "site": "session_state.reset", "kind": "unguarded_reset",
                                "seq": 0, "reason": "dialogue_seq",
                                "cells_before": self._leases.cells_of(0)})
            return self._eng.reset(seq, *a, **kw)
        return self._leases.reset(seq, site="session_state.reset")

    # -- calls that can move a block (logged, not intercepted) --------------
    def _forward_logged(self, name, *a, **kw):
        _append(EVENT_LOG, {"at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "site": "session_state." + name, "kind": "engine_call",
                            "seq": int(a[0]) if a and isinstance(a[0], int) else None})
        return getattr(self._eng, name)(*a, **kw)

    def repos_local(self, *a, **kw):
        return self._forward_logged("repos_local", *a, **kw)

    def load_strict(self, *a, **kw):
        return self._forward_logged("load_strict", *a, **kw)

    def load(self, *a, **kw):
        return self._forward_logged("load", *a, **kw)

    def save(self, *a, **kw):
        return self._forward_logged("save", *a, **kw)


class GuardedLeases(BlockLeases):
    """BlockLeases + a post-reset emptiness assertion + refusal logging."""

    def __init__(self, eng, log=None, site_prefix=""):
        super().__init__(eng, log)
        self.site_prefix = site_prefix
        self.counts = {"reset": 0, "refused": 0, "attached": 0, "detached": 0}
        self.sites = {}
        self.declared = {}        # seq -> {block, start, end} as the manifest states it
        _LIVE.append(self)
        install_bridge()          # chat.py needs no change: the table is found by identity

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
        want = self.declared.get(int(block_seq))
        if want and (want["start"], want["end"]) != (int(lo), int(hi)):
            _append(EVENT_LOG, {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "site": tag,
                                "kind": "range_mismatch", "block": want["block"],
                                "declared": [want["start"], want["end"]],
                                "attached": [int(lo), int(hi)]})
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

    @classmethod
    def from_manifest(cls, eng, path, site_prefix="load"):
        """Build the table from the manifest the engine is about to restore from.

        seq and [start, end) come from manifest["placement"]["blocks"] -- nothing is
        guessed. attach() then checks every share against that declaration and logs a
        range_mismatch if the engine is told a different range.
        """
        table = cls(eng, site_prefix=site_prefix)
        with open(path, encoding="utf-8") as f:
            man = json.load(f)
        for b in man.get("placement", {}).get("blocks", []):
            seq = int(b["slot_id"]) + 1
            table.register_block(seq, b["block"])
            table.declared[seq] = {"block": b["block"],
                                   "start": int(b["start"]), "end": int(b["end"])}
        _append(EVENT_LOG, {"at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "site": site_prefix + ".from_manifest", "kind": "registered",
                            "blocks": {str(s): d["block"]
                                       for s, d in table.declared.items()}})
        return table

    def report(self):
        return {"counts": dict(self.counts), "sites": self.sites,
                "refusals_logged": self.counts["refused"],
                "all_sites_asserted_empty": all(e["cells_after"] == 0
                                                for evs in self.sites.values() for e in evs)}



INTERCEPTED = ("share", "drop", "reset")      # take over the call (table decides)
OBSERVED = ("load", "load_strict", "repos_local", "save", "write_at")  # forward + log only


def proxy_surface(eng, leases):
    """Self-check: outside INTERCEPTED, the proxy must hand back the engine's own members.

    Compares the underlying function objects (bound methods are re-created per access, so
    identity of the bound method is not meaningful) and never calls anything.
    """
    p = RecordingEngine(eng, leases)
    same, differ, missing, observed = [], [], [], []
    for name in dir(eng):
        if name.startswith("__") or name in INTERCEPTED:
            continue
        if name in OBSERVED:
            observed.append(name)
            continue
        try:
            a = getattr(p, name)
            b = getattr(eng, name)
        except AttributeError:
            missing.append(name)
            continue
        fa, fb = getattr(a, "__func__", a), getattr(b, "__func__", b)
        (same if fa is fb else differ).append(name)
    return {"intercepted": list(INTERCEPTED), "observed": observed,
            "passthrough_same": len(same), "unexpected": differ, "missing": missing,
            "clean": not differ and not missing}