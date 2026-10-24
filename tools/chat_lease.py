# -*- coding: utf-8 -*-
"""M3 lease guard, wired into the product path, plus the session_state bridge.

Two jobs, one table:

1. `GuardedLeases` -- every destructive reset goes through it: it refuses while the block
   seq is still referenced, asserts `cells_of(seq) == 0` afterwards (the `safe_reset_all` trap
   leaves the block uncleared and `load_into` then stacks on stale cells), and logs both the
   reset and every refusal. `safe_reset_all` is never used in a placement path.

2. `RecordingEngine` -- a pass-through proxy handed to `session_state.save_session/
   restore_session` so the table can see their own share/drop/reset without editing that
   file. It is a DYNAMIC SUBCLASS of the real engine's class, so `isinstance(proxy, KVEngine)`
   stays true (a `type(eng) is KVEngine` comparison would still fail; `surface_check.py` greps
   the codebase for that pattern and fails if one ever appears).

Logs are per run and never committed: `init_run(label)` opens
`kvmem/lease_logs/events_<label>_<stamp>.jsonl` and the run json records its path + sha256
(`run_log()`). Nothing here changes reset-then-reload semantics.
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import re
import sys
import time

_ROOT = r"D:/llama-mem"
_M3 = os.path.join(_ROOT, "kvmem", "m2_visibility", "m3")
if _M3 not in sys.path:
    sys.path.insert(0, _M3)

from m3_lease import BlockLeases, LeaseError                      # noqa: E402,F401

# -- per-run event logs -------------------------------------------------------
LOG_DIR = os.environ.get("CHAT_LEASE_LOG_DIR", os.path.join(_ROOT, "kvmem", "lease_logs"))
EVENT_LOG = os.environ.get("CHAT_LEASE_EVENTS", "")
REFUSAL_LOG = os.environ.get("CHAT_LEASE_REFUSALS", "")
_RUN = {}

# STRICT: an unregistered non-zero seq is refused instead of silently forwarded.
# Rationale: `BlockLeases.reset` only refuses REGISTERED blocks, so a block seq missing from
# the table would reset silently -- the same failure shape as the bug this guard exists for.
STRICT = os.environ.get("CHAT_LEASE_STRICT", "1") != "0"


def init_run(label="run", force=False):
    """Open this run's log files (never in git). Idempotent unless force."""
    global EVENT_LOG, REFUSAL_LOG, _RUN
    if _RUN and not force:
        return _RUN
    if os.environ.get("CHAT_LEASE_EVENTS") and not force:
        EVENT_LOG = os.environ["CHAT_LEASE_EVENTS"]
        REFUSAL_LOG = os.environ.get("CHAT_LEASE_REFUSALS") or EVENT_LOG
        _RUN = {"label": label, "events": EVENT_LOG, "refusals": REFUSAL_LOG}
        return _RUN
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label).strip("_") or "run"
    stamp = time.strftime("%Y%m%dT%H%M%S")
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except OSError:
        pass
    EVENT_LOG = os.path.join(LOG_DIR, "events_%s_%s.jsonl" % (safe, stamp))
    REFUSAL_LOG = os.path.join(LOG_DIR, "refusals_%s_%s.jsonl" % (safe, stamp))
    _RUN = {"label": label, "events": EVENT_LOG, "refusals": REFUSAL_LOG}
    return _RUN


def run_log():
    """Path, sha256 and line count of this run's event log (for the run json)."""
    info = dict(_RUN) if _RUN else init_run("default")
    info["lines"] = 0
    info["sha256"] = None
    if os.path.exists(info["events"]):
        blob = open(info["events"], "rb").read()
        info["sha256"] = hashlib.sha256(blob).hexdigest()
        info["lines"] = blob.count(b"\n")
    return info


def read_log(path=None):
    p = path or run_log()["events"]
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def _append(path, rec):
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass                                                   # logging never breaks the run


# -- registry + bridge --------------------------------------------------------
_LIVE = []          # live tables, creation order (identity-matched against the engine)
_BRIDGED = False    # session_state.save_session/restore_session installed once
_PROXY_CACHE = {}


def _active_for(eng):
    """The lease table bound to this exact engine object, or None."""
    for t in reversed(_LIVE):
        if t.eng is eng:
            return t
    return None


def _stamp(kind, **kw):
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind}
    rec.update(kw)
    return rec


def install_bridge(force=False):
    """Wrap session_state.save_session/restore_session once; swap in the proxy per call.

    Nothing is edited in session_state.py. A call gets the proxy only when a live table is
    bound to that exact engine object; otherwise it gets the real engine back (and logs
    `bridge.inactive`, so "no guard ran" is distinguishable from "the guard allowed it").
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

    def wrap(fn, attr):
        @functools.wraps(fn)
        def inner(eng, *a, **kw):
            if getattr(ss, attr, None) is not inner:
                raise RuntimeError(
                    "lease bridge for session_state.%s was replaced/removed after install; "
                    "re-run chat_lease.install_bridge(force=True) before continuing" % attr)
            table = _active_for(eng)
            if table is None:
                _append(EVENT_LOG, _stamp("bridge.inactive", call=attr,
                                          engine=type(eng).__name__))
                return fn(eng, *a, **kw)
            _append(EVENT_LOG, _stamp("bridge.active", call=attr,
                                      engine=type(eng).__name__))
            return fn(make_proxy(eng, table), *a, **kw)
        inner._lease_bridge = True
        inner._lease_original = fn
        return inner

    ss.save_session = wrap(ss.save_session, "save_session")
    ss.restore_session = wrap(ss.restore_session, "restore_session")
    _BRIDGED = True
    _append(EVENT_LOG, _stamp("bridge.installed"))
    return True


def assert_bridged(module=None):
    """Assert both entry points are still ours (catches from-import aliasing and rebinds)."""
    import session_state as ss
    mod = module or ss
    bad = [n for n in ("save_session", "restore_session")
           if not getattr(getattr(mod, n, None), "_lease_bridge", False)]
    if bad:
        raise RuntimeError("lease bridge missing on: %s -- a 'from session_state import %s' "
                           "alias captured the original before install_bridge() ran"
                           % (", ".join(bad), bad[0]))
    return True


# -- the proxy ----------------------------------------------------------------
INTERCEPTED = ("share", "drop", "reset")      # take over the call (table decides)
OBSERVED = ("load", "load_strict", "repos_local", "save", "write_at")  # forward + log only
DUNDERS_WE_DO_NOT_SUPPORT = ("__len__", "__iter__", "__next__", "__call__", "__getitem__",
                             "__setitem__", "__contains__", "__enter__", "__exit__",
                             "__copy__", "__deepcopy__", "__reduce__", "__getstate__")


class RecordingEngine:
    """Pass-through proxy: mirrors share/drop/reset into the table, forwards the rest.

    attach()/detach()/reset() already perform the real engine call on the real engine, so
    this proxy must NOT repeat them; it only routes. Anything it does not implement falls
    through `__getattr__` to the engine; attribute WRITES fall through `__setattr__` too.
    """

    def __init__(self, eng, leases):
        object.__setattr__(self, "_eng", eng)
        object.__setattr__(self, "_leases", leases)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_eng"), name)

    def __setattr__(self, name, value):
        if name in ("_eng", "_leases"):
            object.__setattr__(self, name, value)
        else:
            setattr(object.__getattribute__(self, "_eng"), name, value)

    # -- references and destruction (recorded / gated) ---------------------
    def share(self, block_seq, dst_seq, lo, hi):
        leases = object.__getattribute__(self, "_leases")
        if int(block_seq) not in leases.blocks:
            leases.register_block(int(block_seq), "seq%d@session_state" % int(block_seq))
        leases.attach(block_seq, dst_seq, lo, hi, site="session_state.share")

    def drop(self, dst_seq, lo, hi):
        object.__getattribute__(self, "_leases").detach(dst_seq, lo, hi,
                                                        site="session_state.drop")

    def reset(self, seq, *a, **kw):
        """seq 0 is the dialogue (documented exception); anything else is gated."""
        leases = object.__getattribute__(self, "_leases")
        eng = object.__getattribute__(self, "_eng")
        seq = int(seq)
        if seq == 0:
            _append(EVENT_LOG, _stamp("unguarded_reset", site="session_state.reset",
                                      seq=0, reason="dialogue_seq",
                                      cells_before=leases.cells_of(0)))
            return eng.reset(seq, *a, **kw)
        if seq not in leases.blocks:
            _append(EVENT_LOG, _stamp("unguarded_reset", site="session_state.reset",
                                      seq=seq, reason="unregistered_seq",
                                      cells_before=leases.cells_of(seq)))
            if STRICT:
                raise LeaseError(
                    "refusing reset(seq %d): not a registered block, so no lease can cover "
                    "it. Register it (register_block/from_manifest) or detach and force it. "
                    "Set CHAT_LEASE_STRICT=0 to downgrade this to a logged pass-through."
                    % seq)
            return eng.reset(seq, *a, **kw)
        return leases.reset(seq, site="session_state.reset")

    # -- calls that can move a block (logged, not intercepted) --------------
    def _forward_logged(self, name, *a, **kw):
        _append(EVENT_LOG, _stamp("engine_call", site="session_state." + name,
                                  seq=int(a[0]) if a and isinstance(a[0], int) else None))
        return getattr(object.__getattribute__(self, "_eng"), name)(*a, **kw)

    def repos_local(self, *a, **kw):
        return self._forward_logged("repos_local", *a, **kw)

    def load_strict(self, *a, **kw):
        return self._forward_logged("load_strict", *a, **kw)

    def load(self, *a, **kw):
        return self._forward_logged("load", *a, **kw)

    def save(self, *a, **kw):
        return self._forward_logged("save", *a, **kw)


def proxy_class(eng):
    """RecordingEngine + the real engine's class, so isinstance() keeps working."""
    base = type(eng)
    cls = _PROXY_CACHE.get(base)
    if cls is None:
        try:
            cls = type("RecordingEngine_%s" % base.__name__, (RecordingEngine, base), {})
        except TypeError:                                      # not subclassable (extension type)
            cls = RecordingEngine
        _PROXY_CACHE[base] = cls
    return cls


def make_proxy(eng, leases):
    cls = proxy_class(eng)
    obj = cls.__new__(cls)
    object.__setattr__(obj, "_eng", eng)
    object.__setattr__(obj, "_leases", leases)
    return obj


# -- the table ----------------------------------------------------------------
class GuardedLeases(BlockLeases):
    """BlockLeases + a post-reset emptiness assertion + refusal logging."""

    def __init__(self, eng, log=None, site_prefix=""):
        super().__init__(eng, log)
        self.site_prefix = site_prefix
        self.counts = {"reset": 0, "refused": 0, "attached": 0, "detached": 0}
        self.sites = {}
        self.declared = {}        # seq -> {block, start, end} exactly as the manifest says
        _LIVE.append(self)
        init_run("%s_p%d" % (site_prefix or "lease", os.getpid()))
        install_bridge()          # chat.py needs no change: the table is found by identity

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
        _append(EVENT_LOG, _stamp("registered", site=site_prefix + ".from_manifest",
                                  blocks={str(s): d["block"] for s, d in table.declared.items()}))
        return table

    # -- the gated reset ---------------------------------------------------
    def reset(self, seq, force=False, site=""):
        tag = site or (self.site_prefix + ".reset")
        try:
            super().reset(seq, force=force)
        except LeaseError as exc:
            self.counts["refused"] += 1
            rec = _stamp("refused", site=tag, seq=int(seq), message=str(exc),
                         referrers=self.referrers(seq))
            _append(REFUSAL_LOG, rec)
            _append(EVENT_LOG, rec)
            raise                                              # never swallowed
        cells = self.cells_of(seq)
        self.counts["reset"] += 1
        self.sites.setdefault(tag, []).append({"seq": int(seq), "cells_after": cells})
        _append(EVENT_LOG, _stamp("reset", site=tag, seq=int(seq), cells_after=cells))
        if cells != 0:
            raise LeaseError(
                "reset(seq %d) at %s left %d cells -- the block was NOT cleared "
                "(safe_reset_all trap: load_into would stack on stale cells)"
                % (int(seq), tag, cells))
        return True

    # -- attach / detach keep the table honest -----------------------------
    def attach(self, block_seq, dst_seq, lo, hi, site=""):
        tag = site or (self.site_prefix + ".attach")
        super().attach(block_seq, dst_seq, lo, hi)
        want = self.declared.get(int(block_seq))
        if want and (want["start"], want["end"]) != (int(lo), int(hi)):
            _append(EVENT_LOG, _stamp("range_mismatch", site=tag, block=want["block"],
                                      declared=[want["start"], want["end"]],
                                      attached=[int(lo), int(hi)]))
        self.counts["attached"] += 1
        _append(EVENT_LOG, _stamp("attach", site=tag, block_seq=int(block_seq),
                                  dst_seq=int(dst_seq), lo=int(lo), hi=int(hi)))

    def detach(self, dst_seq, lo, hi, site=""):
        tag = site or (self.site_prefix + ".detach")
        block_seq = super().detach(dst_seq, lo, hi)
        self.counts["detached"] += 1
        _append(EVENT_LOG, _stamp("detach", site=tag, block_seq=block_seq,
                                  dst_seq=int(dst_seq), lo=int(lo), hi=int(hi)))
        return block_seq

    def report(self):
        return {"counts": dict(self.counts), "sites": self.sites,
                "refusals_logged": self.counts["refused"],
                "all_sites_asserted_empty": all(e["cells_after"] == 0
                                                for evs in self.sites.values() for e in evs)}


# -- derived self-check (never hand-listed) -----------------------------------
def _defines(base, name):
    """True only if the class hierarchy itself defines name (object/metaclass excluded).

    hasattr(cls, "__call__") is True for every class via the metaclass, and __reduce__/
    __getstate__ come from object -- neither is a protocol the proxy could break.
    """
    for k in base.__mro__:
        if k is object:
            break
        if name in k.__dict__:
            return True
    return False


def surface(eng, leases):
    """Classify every name of the real engine's class by what the proxy does with it.

    Derived from dir(type(eng)) and the proxy class itself, so a new engine method shows up
    as 'passthrough' automatically and anything the proxy shadows by accident shows up as
    'shadowed' instead of being silently forgotten.
    """
    base = type(eng)
    cls = proxy_class(eng)
    p = make_proxy(eng, leases)
    rows = {"intercepted": [], "observed": [], "passthrough": [], "shadowed": [],
            "missing": [], "dunders_not_supported": []}
    for name in sorted(set(dir(base))):
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in INTERCEPTED:
            rows["intercepted"].append(name)
            continue
        if name in OBSERVED:
            rows["observed"].append(name)
            continue
        try:
            a, b = getattr(p, name), getattr(eng, name)
        except AttributeError:
            rows["missing"].append(name)
            continue
        fa, fb = getattr(a, "__func__", a), getattr(b, "__func__", b)
        (rows["passthrough"] if fa is fb else rows["shadowed"]).append(name)
    rows["dunders_not_supported"] = [n for n in DUNDERS_WE_DO_NOT_SUPPORT
                                     if _defines(base, n)]
    rows["isinstance_ok"] = isinstance(p, base)
    rows["proxy_class"] = cls.__name__
    rows["base_class"] = base.__name__
    rows["clean"] = not rows["shadowed"] and not rows["missing"]
    return rows


def forwarding_truth(eng, leases, cases=None):
    """Deliberate bad calls must raise the ENGINE's exception, not the proxy's.

    Compares (type name, message) for each case against the real engine.
    """
    p = make_proxy(eng, leases)
    cases = cases or [("n_tokens", ("not-an-int",), {}),
                      ("pos_max", ("not-an-int",), {}),
                      ("bytes_per_token", (1, 2, 3), {})]
    out = []
    for name, a, kw in cases:
        got = []
        for target in (eng, p):
            try:
                getattr(target, name)(*a, **kw)
                got.append(("no-exception", ""))
            except BaseException as exc:                       # noqa: BLE001 - comparing
                got.append((type(exc).__name__, str(exc)))
        out.append({"method": name, "engine": got[0], "proxy": got[1],
                    "same": got[0] == got[1]})
    return out


def setattr_forwarding(eng, leases, marker="_lease_probe_marker"):
    """An attribute written on the proxy must land on the engine (gap that used to exist)."""
    p = make_proxy(eng, leases)
    setattr(p, marker, 42)
    landed = getattr(eng, marker, None) == 42 and marker not in p.__dict__
    if hasattr(eng, marker):
        delattr(eng, marker)
    return {"marker": marker, "landed_on_engine": bool(landed)}
