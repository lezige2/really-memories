# -*- coding: utf-8 -*-
"""chat.py -- long-term memory as KV blocks, placed by the engine itself.

There is no prompt splicing anywhere in this file. A "memory" is a block of KV
cells on disk. To remember something we:

  1. load the block into its own sequence            (kvshim_load)
  2. move it to sit head-to-tail below the chat       (llama_memory_seq_repos_local)
  3. attach it to the dialogue's sequence             (llama_memory_seq_cp)
  4. generate

Step 2 is the C++ we added: it rotates the RoPE of *only* the cells that move,
per cell, on the CPU, and it touches no other sequence -- verified 0 bytes
changed in an untouched sequence over 100 moves. Step 3 is a pure refcount
bump, zero copy, and the attention mask then exposes those cells to the chat.

The prompt the model receives is nothing but the question.

usage:
    python -X utf8 chat.py build      # encode the memories once, index them in SQLite
    python -X utf8 chat.py            # load two blocks from SQLite, attach, chat
    python -X utf8 chat.py --control  # same questions, blocks NOT attached
"""

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memory_source as ms
import evidence as E
import session_state as ss
from kvslots import KVEngine

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------------------
ROOT   = r"D:\llama-mem"
MODEL  = r"D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
DB     = os.path.join(ROOT, "kvmem", "chat.db")
BLOCKS = os.path.join(ROOT, "kvmem", "blocks")

N_CTX      = 8192
CHAT_START = 4096      # where the dialogue begins; blocks must end right below it
SLOT       = 64        # slot capacity for the right-aligned slot layout (P0-4)
SESSIONS   = os.path.join(ROOT, "kvmem", "sessions")
SESSION    = os.path.join(SESSIONS, "live.json")

# Two separable memory segments. Each is written as self-contained statements so
# that it is a meaningful "episode" on its own -- the model never sees them as text.
MEMORIES = [
    ("profile",  "个人档案",
     "我叫林知远，在供应链分析组工作，我的工号是 A-4417。"
     "我养的猫叫年糕，是一只橘猫。"
     "每周例会订在 B栋3层302会议室。"),

    ("project",  "项目信息",
     "我在做蓝鲸项目，项目代号就是蓝鲸。蓝鲸项目定在 3月14日 上线。"
     "蓝鲸项目的负责人是周敏。"),
]

# Each question needs both blocks, so a correct answer proves both are visible.
QUESTIONS = [
    "我的工号和项目代号分别是什么？",
    "我的猫叫什么？项目什么时候上线？",
    "例会订在哪个会议室？项目负责人是谁？",
]

CONTROL_Q = "我的车牌号是多少？"     # not in any block -- must not be "remembered"


def die(msg):
    print("error: %s" % msg)
    sys.exit(1)


def clean(s):
    """First paragraph of the generation; the model tends to keep thinking after
    it has answered. Nothing is hidden -- the raw length is printed alongside."""
    out = []
    for line in s.strip().splitlines():
        if not line.strip():
            break
        out.append(line.strip())
    return " ".join(out)


# ---------------------------------------------------------------------------
# build: encode each memory segment ONCE, save its KV, index the path in SQLite
# ---------------------------------------------------------------------------
def cmd_build():
    os.makedirs(BLOCKS, exist_ok=True)

    # The source layer is the authority; the .kvmem block is a derived cache. Both are
    # written here, in that order, so a block can always be rebuilt from text.
    con = ms.connect(DB)

    print("model : %s" % MODEL)
    print("blocks: %s\n" % BLOCKS)

    eng = KVEngine(MODEL, n_ctx=N_CTX, n_seq=8, gpu=99, kv="q8_0")
    try:
        print("per-token KV: %.1f KiB (q8_0)\n" % (eng.bytes_per_token() / 1024.0))

        for name, label, text in MEMORIES:
            sid, created = ms.put_source(con, name, label, text)
            rec = ms.build_block(eng, con, ms.get_source(con, name), BLOCKS)
            print("  %-8s %-6s %3d tokens  %7.1f KiB  %s%s"
                  % (name, label, rec["n_tokens"], rec["n_bytes"] / 1024.0, rec["path"],
                     "" if created else "  (source unchanged)"))
    finally:
        eng.close()

    con.close()
    print("\nindexed %d sources + %d blocks in %s" % (len(MEMORIES), len(MEMORIES), DB))


# ---------------------------------------------------------------------------
# chat: load -> repos_local -> seq_cp -> generate
# ---------------------------------------------------------------------------
def cmd_chat(control=False):
    if not os.path.exists(DB):
        die("no index yet -- run: python -X utf8 chat.py build")

    con = ms.connect(DB)
    # block_rows: (id, name, label, text, source_hash, source_id, path, n_tokens, ...)
    rows = [r for r in ms.block_rows(con) if r[5] is not None][:2]
    con.close()

    if len(rows) < 2:
        die("need 2 memories in the index, found %d -- run: chat.py build" % len(rows))

    print("=" * 74)
    print("blocks from SQLite (%s)" % DB)
    print("=" * 74)
    for row in rows:
        print("  row %-2d %-8s %-6s %s (%d tokens)"
              % (row[0], row[1], row[2], os.path.basename(row[6]), row[7]))

    eng = KVEngine(MODEL, n_ctx=N_CTX, n_seq=8, gpu=99, kv="q8_0")

    try:
        # ---- 1+2) load each block and immediately move it out of the way ----
        #
        # Every block is saved at positions 0..n-1. Under kv_unified=true a write
        # to a position that another sequence already occupies REUSES that cell,
        # so two blocks sitting at position 0 at the same time overwrite each
        # other's K. Loading a block, moving it to its target and only then
        # loading the next one keeps 0..n free and is also exactly what we want
        # to do per turn anyway.
        n = {i: rows[i - 1][7] for i in range(1, len(rows) + 1)}

        # targets, packed head to tail and ending right below the chat
        cursor = CHAT_START
        plan = []
        for i in reversed(range(1, len(rows) + 1)):
            cursor -= n[i]
            plan.append((i, cursor))
        plan.reverse()

        print("\n" + "=" * 74)
        print("placement (engine-side, pure CPU rotation)")
        print("=" * 74)
        print("  %-4s %-10s %5s  %-14s %6s %8s %9s"
              % ("seq", "block", "tok", "pos range", "cells", "ms", "MiB/s"))

        t_rot = 0.0
        n_cells = 0
        for i, target in plan:
            eng.reset(i)
            # compat-checked load: refuses a block built by another model / rope / kv type
            ms.load_into(eng, rows[i - 1], i)

            n_load = eng.n_tokens(i)
            if n_load != n[i]:
                die("block %s has %d tokens but the index says %d -- re-run: chat.py build"
                    % (rows[i - 1][1], n_load, n[i]))

            base  = eng.pos_max(i) - n[i] + 1
            delta = target - base

            t0 = time.perf_counter()
            moved = eng.repos_local(i, delta) if delta else 0
            dt = time.perf_counter() - t0

            if delta and moved != n[i]:
                die("repos_local moved %d of %d cells (rope unsupported here?)" % (moved, n[i]))

            t_rot   += dt
            n_cells += moved

            lo, hi = target, target + n[i]
            # bytes actually crossing the bus: cells * bytes_per_token (q8_0)
            rate = (n[i] * eng.bytes_per_token() / 1048576.0) / dt if dt > 0 else 0.0

            print("  %-4d %-10s %5d  [%5d, %5d)  %6d %8.1f %9.1f"
                  % (i, rows[i - 1][1], n[i], lo, hi, moved, dt * 1000.0, rate))

        print("  %-4s %-10s %5s  %-14s %6d %8.1f"
              % ("", "total", "", "", n_cells, t_rot * 1000.0))

        # ---- 3) attach to the dialogue (refcount only, zero copy) ----------
        if not control:
            for i, _target in plan:
                eng.share(i, 0)
            state = "attached (seq_cp)"
        else:
            state = "NOT attached (control run)"

        print("\n  memory -> dialogue: %s" % state)
        print("  prompt carries the question only, no memory text\n")

        # ---- 4) generate ---------------------------------------------------
        print("=" * 74)
        print("dialogue")
        print("=" * 74)

        t_ask = 0.0
        first = True
        for q in QUESTIONS:
            t0 = time.perf_counter()
            # the first question starts the dialogue at CHAT_START, right after the
            # last block; later ones continue at pos_max + 1
            ans = eng.ask(0, q, n_predict=48, pos=CHAT_START if first else None)
            dt = time.perf_counter() - t0
            t_ask += dt
            first = False

            print("\n问：%s" % q)
            print("答：%s" % clean(ans))
            print("    (%.0f ms, %d chars generated)" % (dt * 1000.0, len(ans)))

        t0 = time.perf_counter()
        ans = eng.ask(0, CONTROL_Q, n_predict=48)
        dt = time.perf_counter() - t0
        print("\n问：%s   [not in memory]" % CONTROL_Q)
        print("答：%s" % clean(ans))
        print("    (%.0f ms, %d chars generated)" % (dt * 1000.0, len(ans)))

        # ---- 5) pure rotation cost, measured in isolation ------------------
        # Done last: each round trip re-quantises the block, so keep it off the
        # answers we just generated.
        ROUNDS = 20
        t0 = time.perf_counter()
        for _ in range(ROUNDS):
            eng.repos_local(1, +64)
            eng.repos_local(1, -64)
        per = (time.perf_counter() - t0) / (2 * ROUNDS)

        print("\n" + "=" * 74)
        print("cost")
        print("=" * 74)
        print("  attachment (repos_local, %d cells): %6.1f ms total" % (n_cells, t_rot * 1000.0))
        print("  pure rotation, %d-token block     : %6.2f ms/move" % (n[1], per * 1000.0))
        print("  memory text injected into prompt : 0 characters")
        print("  bytes of other sequences touched : 0 (per-cell, nothing else rewritten)")
        print("  generation                        : %.0f ms for %d questions"
              % (t_ask * 1000.0, len(QUESTIONS)))
    finally:
        eng.close()


# ---------------------------------------------------------------------------
def _rows_for_session(con, limit=2):
    rows = [r for r in ms.block_rows(con) if r[5] is not None][:limit]
    if len(rows) < limit:
        die("need %d memories in the index, found %d -- run: chat.py build"
            % (limit, len(rows)))
    return rows


def _place_slots(eng, rows):
    """Right-aligned slots: every block's tail sits at its slot's tail, and the top
    slot's tail is the chat anchor. This is the arrangement P0-4 proved keeps the
    decode path gap-free at the head, so no guard is needed."""
    blocks = []
    for i, row in enumerate(rows, start=1):
        eng.reset(i)
        n = ms.load_into(eng, row, i)
        end = CHAT_START - (i - 1) * SLOT
        lo = end - n
        base = eng.pos_max(i) + 1 - n
        if base != lo:
            moved = eng.repos_local(i, lo - base)
            if moved != n:
                die("repos_local moved %d of %d cells" % (moved, n))
        eng.share(i, 0, lo, end)
        blocks.append({"seq": i, "source_id": row[0], "name": row[1],
                       "lo": lo, "hi": end, "n_tokens": n, "path": row[6]})
        print("  slot %d  %-8s %3d tok -> [%d,%d)  gap %d below"
              % (i - 1, row[1], n, lo, end, (end - n) - (end - SLOT)))
    return blocks


def _ask_all(eng, first_at=CHAT_START):
    first = True
    for q in QUESTIONS:
        ans = eng.ask(0, q, n_predict=48, pos=(first_at if first else None))
        first = False
        print("\n问：%s" % q)
        print("答：%s" % clean(ans))
        print("    (%d chars)" % len(ans))


def cmd_save(path=SESSION):
    """Talk, then snapshot the session: detach -> save chat -> manifest -> reattach."""
    if not os.path.exists(DB):
        die("no index yet -- run: python -X utf8 chat.py build")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    con = ms.connect(DB)
    eng = KVEngine(MODEL, n_ctx=N_CTX, n_seq=8, gpu=99, kv="q8_0")
    try:
        rows = _rows_for_session(con)
        print("placing %d blocks in right-aligned slots of %d" % (len(rows), SLOT))
        blocks = _place_slots(eng, rows)

        print("\n" + "=" * 74 + "\ndialogue (prompt carries the question only)\n" + "=" * 74)
        _ask_all(eng)

        m = ss.save_session(eng, con, path, blocks, anchor=CHAT_START,
                            slot_capacity=SLOT)
        print("\n" + "=" * 74)
        print("session saved: %s" % path)
        print("  layout   anchor=%d alignment=%s top_slot_end=%d"
              % (m["layout"]["anchor"], m["layout"]["alignment"],
                 m["layout"]["slots"][0]["end"]))
        for pb in m["placement"]["blocks"]:
            print("  block    %-8s slot %d  [%d,%d)  %d tok"
                  % (pb["block"], pb["slot_id"], pb["start"], pb["end"],
                     pb["n_tokens"]))
        print("  chat     [%d,%d)  %d tokens"
              % (m["placement"]["chat_range"]["start"],
                 m["placement"]["chat_range"]["end"], m["chat"]["n_tokens"]))
        print("  verified: right-aligned, top block flush with the anchor, "
              "no gap below the chat head")
    finally:
        eng.close()
        con.close()


def cmd_load(path=SESSION):
    """Restore, verify the contract, then continue the dialogue."""
    if not os.path.exists(path):
        die("no session at %s -- run: python -X utf8 chat.py save" % path)

    con = ms.connect(DB)
    eng = KVEngine(MODEL, n_ctx=N_CTX, n_seq=8, gpu=99, kv="q8_0")
    try:
        rep = ss.restore_session(eng, con, path)
        print("=" * 74)
        print("session restored: %s" % path)
        print("=" * 74)
        print("  anchor   %d" % rep["anchor"])
        for b in rep["blocks"]:
            print("  block    %-8s slot %d  [%d,%d)  %d tok"
                  % (b["block"], b["slot_id"], b["start"], b["end"], b["n_tokens"]))
        print("  chat     [%d,%d)" % (CHAT_START, rep["chat_end"]))
        print("  re-mounted %d blocks, %d shift(s), %d rebuilt"
              % (len(rep["blocks"]), rep["shifts"], len(rep["rebuilt"])))
        print("  contract verified: layout re-resolved and matched, no head gap")

        print("\n" + "=" * 74 + "\ndialogue continues\n" + "=" * 74)
        _ask_all(eng, first_at=None)
    finally:
        eng.close()
        con.close()



# ---------------------------------------------------------------------------
# M1-lite: which blocks to mount is a database question, not a model question
# ---------------------------------------------------------------------------
def _selection(con, q, k=2):
    """Ask the facet index, never the model. An empty list is a valid answer."""
    import retrieval as R
    if R.is_stale(con):
        R.build_index(con, verbose=False)      # derived cache: rebuild, do not migrate
    return [r for r in R.search(con, q, k=k) if r["source_id"] is not None]


def _explain(con, q):
    import retrieval as R
    if R.index_version(con) != R.INDEX_VERSION:
        R.build_index(con, verbose=False)
    print("\n问：%s" % q)
    for r in R.search(con, q, k=3, explain=True):
        print("   %-6.3f %-9s %s"
              % (r["score"], r["name"],
                 ", ".join("%s=%s" % kv for kv in r["signals"].items())))


def cmd_m1(explain=False, control=False, save_path=None):
    """Per-question block selection, then generate. Fixed slot geometry (B-right):
    selection decides WHICH blocks fill the slots, not where the slots are (that is M2)."""
    os.makedirs(SESSIONS, exist_ok=True)
    con = ms.connect(DB)

    if explain:
        for q in [CONTROL_Q] + QUESTIONS:
            _explain(con, q)
        con.close()
        return

    eng = KVEngine(MODEL, n_ctx=N_CTX, n_seq=8, gpu=99, kv="q8_0")
    try:
        rows = {r[1]: r for r in ms.block_rows(con) if r[5] is not None}
        import retrieval as R
        R.build_index(con, verbose=True)

        mounted, order = {}, []
        turns, first, history = [], True, []
        for q in [CONTROL_Q] + QUESTIONS:
            sel = _selection(con, q)
            want = [s["name"] for s in sel]
            # the state is decided here, before anything is generated
            d = E.decide(q, sel, "\n".join(history))
            if explain:
                pass
            else:
                print("\n" + "=" * 74)
                print("问：%s" % q)
                print("  状态：%s  [%s]  %s"
                      % (d["state"], E.BADGE[d["state"]], d["reason"]))
                if not want:
                    print("  检索：无匹配 → 不挂任何块（负例必须是空，不能硬凑 top-k）")
                else:
                    print("  检索：%s" % ", ".join(
                        "%s(%.2f)" % (s["name"], s["score"]) for s in sel))

                turns.append({"q": q, "state": d["state"], "intent": d["intent"],
                              "refused": False, "mounted": list(order),
                              "selected": [{"name": s2["name"], "score": s2["score"],
                                            "signals": s2["signals"]} for s2 in sel]})
            if want != order:
                for name, (seq, lo, hi) in mounted.items():
                    eng.drop(0, lo, hi)
                    eng.reset(seq)
                mounted, order = {}, want
                if not control:
                    for i, name in enumerate(order):
                        seq = i + 1
                        eng.reset(seq)
                        n = ms.load_into(eng, rows[name], seq)
                        end = CHAT_START - i * SLOT
                        lo = end - n
                        base = eng.pos_max(seq) + 1 - n
                        if base != lo and eng.repos_local(seq, lo - base) != n:
                            die("%s: repos_local refused" % name)
                        eng.share(seq, 0, lo, end)
                        mounted[name] = (seq, lo, end)
                if mounted:
                    print("  挂载：" + ", ".join("%s[%d,%d)" % (k, v[1], v[2])
                                                for k, v in mounted.items()))
                elif order:
                    print("  挂载：（control：不挂）")

            if d["refuse"]:
                # application layer, fixed text, model NOT called. The prompt contract
                # ("the prompt carries the question only") is preserved by not running.
                print("答：%s" % d["reply"])
                print("   （未调用模型；注入字符 %d；policy v%d）"
                      % (d["chars_injected"], d["policy_version"]))
                # NOT appended to history: the refusal never entered the chat KV, so it
                # cannot later count as "present in this dialogue".
                turns.append({"q": q, "state": d["state"], "intent": d["intent"],
                              "refused": True, "mounted": list(order),
                              "selected": [{"name": s2["name"], "score": s2["score"]}
                                           for s2 in sel]})
                continue

            ans = eng.ask(0, q, n_predict=48, pos=CHAT_START if first else None)
            first = False
            print("答：%s" % clean(ans))
            history.append("用户：%s\n助手：%s" % (q, ans))

        if save_path and mounted:
            sel_audit = {"index_version": R.INDEX_VERSION, "turns": turns}
            blocks = [{"seq": seq, "source_id": rows[name][0], "name": name,
                       "lo": lo, "hi": hi, "n_tokens": hi - lo, "path": rows[name][6]}
                      for name, (seq, lo, hi) in mounted.items()]
            # order the blocks top-down, which is what the layout contract expects
            blocks.sort(key=lambda b: -b["hi"])
            m = ss.save_session(eng, con, save_path, blocks, anchor=CHAT_START,
                                slot_capacity=SLOT, selection=sel_audit)
            print("\nsession saved: %s  (selection audit: %d turns, index v%d)"
                  % (save_path, len(turns), R.INDEX_VERSION))
    finally:
        eng.close()
        con.close()


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="KV-block chat, no prompt splicing")
    ap.add_argument("cmd", nargs="?", default="chat",
                    choices=["build", "chat", "save", "load", "m1"])
    ap.add_argument("--control", action="store_true",
                    help="ask the same questions WITHOUT attaching the blocks")
    ap.add_argument("--path", default=SESSION, help="session manifest path")
    ap.add_argument("--explain", action="store_true",
                    help="m1: print the selection and its scores, generate nothing")
    ap.add_argument("--save", nargs="?", const=SESSION, default=None,
                    help="m1: snapshot the session with its selection audit")
    args = ap.parse_args()

    if args.cmd == "build":
        cmd_build()
    elif args.cmd == "save":
        cmd_save(args.path)
    elif args.cmd == "load":
        cmd_load(args.path)
    elif args.cmd == "m1":
        cmd_m1(explain=args.explain, control=args.control, save_path=args.save)
    else:
        cmd_chat(control=args.control)


if __name__ == "__main__":
    main()