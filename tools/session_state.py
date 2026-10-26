# -*- coding: utf-8 -*-
"""session_state.py -- P0-2: save and restore a conversation that has memory attached.

Design: **detach-before-save**, not a token ledger. The block is a cache of the source
text and a session is "a dialogue plus a layout", not "a KV blob containing memories".
A ledger would push token semantics into `seq_cp` (today a pure refcount); detach does
the opposite -- it drops the chat's references to the block cells before saving, so the
saved sequence contains its own dialogue and nothing else.

    save :  quiesce -> detach -> save chat -> write manifest -> reattach
    load :  validate -> resolve -> compare -> load chat -> per block: load_strict ->
            verify -> repos_local to target -> seq_cp -> verify -> only then generate

The manifest carries two layers, and the difference matters:

    layout     the CONTRACT: anchor, slots (base/capacity/end), alignment, guard policy,
               planner version. Only this can express "right-aligned, top slot flush with
               the anchor" -- the one arrangement P0-4 proved is not fatal.
    placement  the RENDER: each block's resolved [start,end), slot id, role, token count,
               hash. Useful for audit and for a fast equality check.

On restore the ranges are recomputed from `layout` and compared with `placement`; a
mismatch fails closed. Storing only the render would leave us unable to tell whether the
top block really touched the anchor, or whether a gap was papered over with a guard.
"""
import ctypes
import hashlib
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import memory_source as ms  # noqa: E402

MANIFEST_VERSION = 2
PLANNER_VERSION = 1

# Windows has no directory fsync primitive; NTFS journals rename metadata.  This
# counter is product evidence, not a fallback for directory durability.
_DURABILITY = {"write_through": 0, "replace_fallback": 0}


def durability_snapshot():
    return dict(_DURABILITY)


def _movefile_ex_write_through(tmp, dst):
    """MoveFileExW(..., REPLACE_EXISTING|WRITE_THROUGH); False if unavailable/failed."""
    if os.name != "nt":
        return False
    try:
        fn = ctypes.windll.kernel32.MoveFileExW
        fn.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        fn.restype = ctypes.c_int
        return bool(fn(str(tmp), str(dst), 0x1 | 0x8))
    except Exception:                                      # noqa: BLE001
        return False


def _durable_replace(tmp, dst):
    """Return 'write_through' or fallback to os.replace + 'replace_fallback'."""
    if _movefile_ex_write_through(tmp, dst):
        _DURABILITY["write_through"] += 1
        return "write_through"
    os.replace(tmp, dst)
    _DURABILITY["replace_fallback"] += 1
    return "replace_fallback"


class LayoutMismatch(Exception):
    """The manifest does not describe a layout we can honour. Never generate on a guess."""


def _emit_unvalidated(manifest_path, manifest, chat_state, chat_path, actual_bytes,
                      n_tokens):
    """Old manifest without chat.bytes: loading is allowed, but never silently.

    One JSONL object on stderr, fields fixed by INSPECTOR-M7-CRITERIA (m7_f2_event_v1).
    chat_lease is intentionally not imported (it imports this module); nothing is ever
    written back to the old manifest (`wrote_manifest` is part of the event).
    """
    try:
        sys.stderr.write(json.dumps({
            "schema": "m7_f2_event_v1",
            "event": "chat_unvalidated",
            "unvalidated": True,
            "manifest": manifest_path,
            "manifest_sha16": hashlib.sha256(open(manifest_path, "rb").read()).hexdigest()[:16],
            "manifest_version": manifest.get("version"),
            "chat_state": chat_state,
            "chat_path": chat_path,
            "actual_bytes": actual_bytes,
            "expected_bytes": None,
            "reason": "missing_chat_bytes",
            "n_tokens": n_tokens,
            "wrote_manifest": False,
        }, ensure_ascii=False) + "\n")
        sys.stderr.flush()
    except Exception:                                        # noqa: BLE001
        pass


REQUIRED = {
    "top": ("version", "saved_at", "tenant", "scope", "kv_type", "state_version",
            "model", "chat", "layout", "placement"),
    "chat": ("state", "n_tokens", "start", "end"),
    "layout": ("anchor", "alignment", "planner_version", "slot_capacity", "slots"),
    "slot": ("id", "base", "capacity", "end", "block", "role"),
    "placement": ("blocks", "chat_range", "guard"),
    "pblock": ("block", "slot_id", "role", "start", "end", "n_tokens"),
}


def _req(obj, keys, what):
    missing = [k for k in keys if k not in obj]
    if missing:
        raise LayoutMismatch("%s is missing required field(s): %s"
                             % (what, ", ".join(missing)))


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------- layout intent

def plan_layout(blocks, anchor, slot_capacity=None, alignment="right",
                guard_policy="none"):
    """Right-aligned slots stacked downward from `anchor`, top slot flush with it.

    `blocks` must be ordered top-down (index 0 is the block nearest the dialogue).
    slot_capacity=None means "one slot per block, exactly as long as the block" (tight
    packing, gaps of zero) -- the same schema, no gaps.
    """
    slots = []
    for i, b in enumerate(blocks):
        cap = int(slot_capacity or b["n_tokens"])
        end = anchor - i * cap if slot_capacity else anchor - sum(
            int(x["n_tokens"]) for x in blocks[:i])
        slots.append({"id": i, "base": end - cap, "capacity": cap, "end": end,
                      "block": b["name"], "role": b.get("role", "memory")})
    layout = {
        "anchor": anchor,
        "alignment": alignment,
        "planner_version": PLANNER_VERSION,
        "slot_capacity": slot_capacity,
        "guard_policy": guard_policy,
        "slots": slots,
    }
    placement = {
        "blocks": [{
            "block": b["name"],
            "slot_id": i,
            "role": b.get("role", "memory"),
            "start": slots[i]["end"] - int(b["n_tokens"]),
            "end": slots[i]["end"],
            "n_tokens": int(b["n_tokens"]),
        } for i, b in enumerate(blocks)],
        "chat_range": {"start": anchor, "end": None},
        "guard": None,
    }
    return layout, placement


def resolve(layout, lens):
    """Recompute the render from the contract. `lens` maps block name -> token count."""
    out = []
    for slot in layout["slots"]:
        n = lens.get(slot["block"])
        if n is None:
            raise LayoutMismatch("slot %r refers to block %r, which is not in the session"
                                 % (slot["id"], slot["block"]))
        out.append({"block": slot["block"], "slot_id": slot["id"], "role": slot["role"],
                    "start": slot["end"] - int(n), "end": slot["end"],
                    "n_tokens": int(n)})
    return out


def check_layout(layout):
    """Structural invariants: these hold whatever the block lengths are."""
    problems = []
    if layout["alignment"] != "right":
        problems.append("alignment is %r; this build only emits right-aligned slots"
                        % layout["alignment"])
    slots = layout["slots"]
    if not slots:
        problems.append("layout has no slots")
        return problems
    if slots[0]["end"] != layout["anchor"]:
        problems.append("top slot ends at %d, anchor is %d"
                        % (slots[0]["end"], layout["anchor"]))
    for i, s in enumerate(slots):
        if s["end"] - s["base"] != s["capacity"]:
            problems.append("slot %d spans %d but capacity says %d"
                            % (s["id"], s["end"] - s["base"], s["capacity"]))
        if i:
            # the next slot must start exactly where this one ends: gaps live INSIDE a
            # slot (between its base and the block), never between slots
            if slots[i - 1]["base"] != s["end"]:
                problems.append("slot %d ends at %d but the slot above starts at %d"
                                % (s["id"], s["end"], slots[i - 1]["base"]))
    return problems


def check_placement(layout, placement_blocks, chat_range):
    """The render must obey the contract, and the head must be gap-free."""
    problems = []
    slots = {s["id"]: s for s in layout["slots"]}
    if not placement_blocks:
        return ["placement has no blocks"]
    for b in placement_blocks:
        s = slots.get(b["slot_id"])
        if s is None:
            problems.append("%s: unknown slot %r" % (b["block"], b["slot_id"]))
            continue
        if b["n_tokens"] > s["capacity"]:
            problems.append("%s: %d tokens do not fit a slot of %d"
                            % (b["block"], b["n_tokens"], s["capacity"]))
        if b["end"] != s["end"]:
            problems.append("%s: ends at %d, slot %d ends at %d (not right-aligned)"
                            % (b["block"], b["end"], s["id"], s["end"]))
        if b["start"] < s["base"]:
            problems.append("%s: starts at %d, before its slot base %d"
                            % (b["block"], b["start"], s["base"]))
    # order and overlap, top-down
    for a, b in zip(placement_blocks, placement_blocks[1:]):
        if a["start"] < b["end"]:
            problems.append("%s [%d,%d) overlaps %s [%d,%d)"
                            % (a["block"], a["start"], a["end"],
                               b["block"], b["start"], b["end"]))
    top = placement_blocks[0]
    if top["end"] != layout["anchor"]:
        problems.append("top block ends at %d, anchor is %d -- there is an invisible gap "
                        "directly below the chat head, which makes decode fail"
                        % (top["end"], layout["anchor"]))
    if chat_range["start"] != layout["anchor"]:
        problems.append("chat starts at %d, anchor is %d"
                        % (chat_range["start"], layout["anchor"]))
    return problems


# --------------------------------------------------------------- save

def save_session(eng, con, path, blocks, anchor, slot_capacity=None,
                 kv_type="q8_0", model_path=ms.MODEL, tenant="default",
                 scope="private", guard_policy="none", selection=None):
    """Snapshot the layout that is live right now, then put the session back together.

    `blocks` is ordered top-down and carries seq/source_id/name/lo/hi/n_tokens/path.
    The live ranges are checked against the contract before anything is written: a
    snapshot of a layout we cannot express is worse than no snapshot.
    """
    path = os.path.abspath(path)
    root = os.path.splitext(path)[0]
    chat_file = root + ".chat.kvmem"

    layout, placement = plan_layout(blocks, anchor, slot_capacity,
                                    guard_policy=guard_policy)
    problems = check_layout(layout)
    # the live ranges must be the ones the contract renders
    lens = {b["name"]: b["n_tokens"] for b in blocks}
    resolved = resolve(layout, lens)
    for live, want in zip(blocks, resolved):
        if (live["lo"], live["hi"]) != (want["start"], want["end"]):
            problems.append("%s sits at [%d,%d) but the layout renders [%d,%d)"
                            % (live["name"], live["lo"], live["hi"],
                               want["start"], want["end"]))
    if problems:
        raise LayoutMismatch("refusing to save a session whose layout is inconsistent:\n  "
                             + "\n  ".join(problems))

    chat_n = eng.n_tokens(0)
    chat_end = eng.pos_max(0) + 1 if chat_n else anchor
    placement["chat_range"] = {"start": anchor, "end": chat_end}
    problems = check_placement(layout, resolved, placement["chat_range"])
    if problems:
        raise LayoutMismatch("refusing to save:\n  " + "\n  ".join(problems))

    # detach first: the saved sequence must contain its own dialogue and nothing else
    for b in blocks:
        eng.drop(0, b["lo"], b["hi"])
    try:
        chat_bytes = None
        if chat_n:
            if eng.save(0, chat_file) <= 0:
                raise RuntimeError("saving the chat sequence produced no bytes")
            chat_bytes = os.stat(chat_file).st_size
        placement["blocks"] = resolved
        for pb, b in zip(placement["blocks"], blocks):
            pb["block_sha256"] = (_sha256_file(b["path"]) if b.get("path")
                                  and os.path.exists(b["path"]) else None)
        chat_entry = {"state": os.path.basename(chat_file) if chat_n else None,
                      "n_tokens": chat_n, "start": anchor, "end": chat_end}
        if chat_bytes is not None:
            chat_entry["bytes"] = chat_bytes       # size of the file just renamed in
        manifest = {
            "version": MANIFEST_VERSION,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "tenant": tenant,
            "scope": scope,
            "kv_type": kv_type,
            "state_version": ms.STATE_VERSION,
            "model": ms.model_fp(model_path),
            "chat": chat_entry,
            "layout": layout,
            "placement": placement,
            # audit only: what retrieval picked and which index version picked it.
            # The layout is authoritative for placement; this says *why* these blocks.
            "selection": selection,
        }
        # A manifest is only non-truncated if its CONTENT is durable before the name
        # flips: fsync the temp file, then use a write-through rename.  Windows has no
        # directory-fsync primitive; NTFS journal covers the rename metadata, so
        # directory flush is not a gap here (and no FlushFileBuffers is attempted).
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        mode = _durable_replace(tmp, path)
        manifest["durability"] = {"replace_mode": mode,
                                   "fallback_used": mode == "replace_fallback"}
    finally:
        for b in blocks:               # never leave the session detached
            eng.share(b["seq"], 0, b["lo"], b["hi"])
    return manifest


# --------------------------------------------------------------- load

def read_manifest(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_manifest(m, kv_type="q8_0", model_path=ms.MODEL):
    _req(m, REQUIRED["top"], "manifest")
    _req(m["chat"], REQUIRED["chat"], "manifest.chat")
    _req(m["layout"], REQUIRED["layout"], "manifest.layout")
    _req(m["placement"], REQUIRED["placement"], "manifest.placement")
    for s in m["layout"]["slots"]:
        _req(s, REQUIRED["slot"], "manifest.layout.slots[]")
    for b in m["placement"]["blocks"]:
        _req(b, REQUIRED["pblock"], "manifest.placement.blocks[]")

    if m["version"] != MANIFEST_VERSION:
        raise LayoutMismatch("manifest version %r != %r" % (m["version"], MANIFEST_VERSION))
    if m["state_version"] != ms.STATE_VERSION:
        raise LayoutMismatch("state format v%r != v%r"
                             % (m["state_version"], ms.STATE_VERSION))
    if m["kv_type"] != kv_type:
        raise LayoutMismatch("session built with kv=%s, engine is %s"
                             % (m["kv_type"], kv_type))
    fp = ms.model_fp(model_path)
    mfp = m["model"]
    if (mfp.get("model_path"), mfp.get("model_size"), mfp.get("model_mtime")) != \
       (fp["model_path"], fp["model_size"], fp["model_mtime"]):
        raise LayoutMismatch("session was saved by a different model (%s)"
                             % mfp.get("model_path"))


def restore_session(eng, con, path, kv_type="q8_0", model_path=ms.MODEL):
    """Rebuild the layout, verifying at every step. Returns a report dict."""
    path = os.path.abspath(path)
    root = os.path.splitext(path)[0]
    m = read_manifest(path)
    validate_manifest(m, kv_type, model_path)

    layout = m["layout"]
    problems = check_layout(layout)
    if problems:
        raise LayoutMismatch("layout contract is broken:\n  " + "\n  ".join(problems))

    # recompute the render from the contract, then require it to match what was saved
    lens = {b["block"]: b["n_tokens"] for b in m["placement"]["blocks"]}
    resolved = resolve(layout, lens)
    for want, saved in zip(resolved, m["placement"]["blocks"]):
        if (want["start"], want["end"]) != (saved["start"], saved["end"]):
            raise LayoutMismatch("%s: layout renders [%d,%d) but the manifest recorded "
                                 "[%d,%d) -- refusing to guess"
                                 % (saved["block"], want["start"], want["end"],
                                    saved["start"], saved["end"]))
    problems = check_placement(layout, resolved, m["placement"]["chat_range"])
    if problems:
        raise LayoutMismatch("placement violates the contract:\n  " + "\n  ".join(problems))

    rows = {r[0]: r for r in ms.block_rows(con)}
    by_name = {r[1]: r for r in rows.values()}
    # Audit B1-20261026 gap B: the old +1 made scratch equal to the highest
    # slot's target seq (slot_id+1), so the "preflight" reset that block's seq
    # first.  Keep scratch strictly above every target seq and inside n_seq.
    max_slot_id = max([b["slot_id"] for b in resolved] + [0])
    scratch = max_slot_id + 2
    n_seq = int(getattr(eng, "n_seq", 0) or 0)
    if n_seq and scratch >= n_seq:
        raise LayoutMismatch(
            "scratch seq %d collides with the engine's n_seq=%d -- refusing to guess"
            % (scratch, n_seq))
    report = {"shifts": 0, "rebuilt": [], "blocks": [], "layout_problems": []}

    # Size gate BEFORE reset: a rejected tail-extra must not clear seq 0, so the
    # caller can still inspect n_tokens/pos_max after the refusal (and a bad file
    # cannot be mistaken for "loaded but empty").
    chat_path = None
    unvalidated_chat_bytes = False
    if m["chat"]["state"]:
        chat_path = root + ".chat.kvmem"     # same construction as save, not join()
        if os.path.basename(chat_path) != m["chat"]["state"]:
            raise LayoutMismatch("manifest names chat state %r, expected %r"
                                 % (m["chat"]["state"], os.path.basename(chat_path)))
        declared = m["chat"].get("bytes")
        if declared is None:
            unvalidated_chat_bytes = True
            try:
                actual_old = os.stat(chat_path).st_size
            except OSError:
                actual_old = None
            _emit_unvalidated(path, m, m["chat"]["state"], chat_path, actual_old,
                              m["chat"]["n_tokens"])
        else:
            try:
                actual = os.stat(chat_path).st_size
            except OSError as e:
                raise LayoutMismatch("chat state file unreadable (%s): %s"
                                     % (chat_path, e))
            if actual != declared:
                raise LayoutMismatch(
                    "chat state file is %d bytes, manifest says %d (%s) -- "
                    "refusing before reset" % (actual, declared, chat_path))

    # P1: preflight the chat state into the unused scratch sequence BEFORE
    # touching seq0.  A refused/incompatible chat file must not clear the live
    # dialogue first.  If the preflight succeeds we still have to load seq0 for
    # the target state; that second load goes through kvshim_load (C++) and its
    # internal reset remains -- recorded as the C++ arm residual.
    reset0_done = False
    if m["chat"]["state"]:
        npre = eng.load_strict(scratch, chat_path)
        if npre != m["chat"]["n_tokens"]:
            raise LayoutMismatch("chat token count %d != manifest %d (preflight)"
                                 % (npre, m["chat"]["n_tokens"]))
        if eng.pos_max(scratch) + 1 != m["chat"]["end"]:
            raise LayoutMismatch("chat window ends at %d, manifest says %d (preflight)"
                                 % (eng.pos_max(scratch) + 1, m["chat"]["end"]))
        eng.reset(0)
        reset0_done = True
        n = eng.load_strict(0, chat_path)
        if n != m["chat"]["n_tokens"]:
            raise LayoutMismatch("chat token count %d != manifest %d"
                                 % (n, m["chat"]["n_tokens"]))
        if eng.pos_max(0) + 1 != m["chat"]["end"]:
            raise LayoutMismatch("chat window ends at %d, manifest says %d"
                                 % (eng.pos_max(0) + 1, m["chat"]["end"]))
        report["chat_bytes_verified"] = declared is not None
        report["unvalidated_chat_bytes"] = unvalidated_chat_bytes

    for i, b in enumerate(resolved):
        row = by_name.get(b["block"])
        if row is None:
            raise LayoutMismatch("%s: source row is gone" % b["block"])
        seq = b["slot_id"] + 1
        # P2: preflight into the unused scratch seq; a refused block must not
        # clear the target seq first.  The target load below is the allowed
        # second load (its C++ kvshim_load still resets; C++ arm residual).
        pre_ok = True
        try:
            ms.load_into(eng, row, scratch)
        except ms.Incompatible:
            # Do NOT reset the target here: rebuild below happens while the target
            # still holds its old contents, and the target reset only occurs after
            # a successful rebuild.  A hard (non-Incompatible) refusal propagates
            # before any reset.
            pre_ok = False
        n = -1
        if pre_ok:
            # No-chat manifests still want the dialogue seq cleared on a successful
            # restore, but only after the block preflight has passed; a failed block
            # must not clear seq0 either.
            if not reset0_done:
                eng.reset(0)
                reset0_done = True
            try:
                eng.reset(seq)
                n = ms.load_into(eng, row, seq)
            except ms.Incompatible as e:
                print("      %s: %s -- rebuilding from source" % (b["block"], e))
        if n != b["n_tokens"]:
            ms.rebuild(eng, con, b["block"], kv_type=kv_type, model_path=model_path,
                       seq=scratch)
            by_name = {r[1]: r for r in ms.block_rows(con)}
            eng.reset(seq)
            n = ms.load_into(eng, by_name[b["block"]], seq)
            report["rebuilt"].append(b["block"])
            if n != b["n_tokens"]:
                raise LayoutMismatch("%s: rebuilt to %d tokens, manifest says %d -- "
                                     "refusing to guess a layout"
                                     % (b["block"], n, b["n_tokens"]))
        base = eng.pos_max(seq) - n + 1
        if base != b["start"]:
            moved = eng.repos_local(seq, b["start"] - base)
            report["shifts"] += 1
            if moved != n:
                raise LayoutMismatch("%s: repos_local moved %d of %d cells"
                                     % (b["block"], moved, n))
        if eng.pos_max(seq) + 1 - n != b["start"]:
            raise LayoutMismatch("%s: landed at %d, manifest says %d"
                                 % (b["block"], eng.pos_max(seq) + 1 - n, b["start"]))
        eng.share(seq, 0, b["start"], b["end"])
        report["blocks"].append(b)

    expect_end = m["chat"]["end"]
    got_end = eng.pos_max(0) + 1 if eng.n_tokens(0) else max(
        [b["end"] for b in resolved] + [0])
    if got_end < expect_end:
        raise LayoutMismatch("window ends at %d, manifest says %d" % (got_end, expect_end))
    report["chat_end"] = expect_end
    report["chat_n_tokens"] = eng.n_tokens(0)
    report["anchor"] = layout["anchor"]
    return report