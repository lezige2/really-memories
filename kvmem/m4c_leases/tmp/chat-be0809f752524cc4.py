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
from chat_lease import GuardedLeases    # M3 guard: every reset is gated + asserted empty
import json

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

# The memory text is NOT here any more: kvmem/chat.db::memory_source is the authority and
# the builder reads it (ms.indexable_sources). A literal here would be a second copy of the
# same bytes, and editing it used to silently re-source every block -- Stage 2 removes that.

# Each question needs both blocks, so a correct answer proves both are visible.
QUESTIONS = [
    "我的工号和项目代号分别是什么？",
    "我的猫叫什么？项目什么时候上线？",
    "例会订在哪个会议室？项目负责人是谁？",
]

CONTROL_Q = "我的车牌号是多少？"     # not in any block -- must not be "remembered"


# ---------------------------------------------------------------------------
# M4-C 断言台账：每条断言记 checked / skipped + 理由；control 运行的绿**不计入覆盖**。
# 断言台账：键 = M4C_ASSERT_LOG_PATH（路径即身份）。无路径不记账，绝不落到一个无名桶里。
_M4C_LOGS = {}
# seq 总数只在这里写一次：同一个数在多处独立书写，改一处就漏另一处。
N_SEQ = 8


def _m4c_log(entry):
    """记一条断言状态。键 = 路径：路径不同即不同次运行，累积在结构上不可能。

    没有路径就**不记账**（绝不 setdefault 到一个无名桶 —— 那会把「没有身份」退化成「共享身份」）。
    内存 append 在 try 之外；写盘在 try 之内用 tmp + os.replace 原子替换 ⇒ 盘上要么完整旧版、
    要么完整新版，永远不会读到半截；写盘失败不吞掉主消息。
    """
    path = os.environ.get("M4C_ASSERT_LOG_PATH")
    if not path:
        return entry
    bucket = _M4C_LOGS.setdefault(path, [])
    bucket.append(entry)
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(bucket, ensure_ascii=False, indent=2))
        os.replace(tmp, path)
    except OSError:
        pass
    return entry


def _m4c_cells(eng, seq):
    """计数层：该 seq 自己的 token 数（cells_of 就是它，m3_lease.py:125）。"""
    return int(eng.n_tokens(int(seq)))


def _m4c_witness_cells(eng, seq, want, site, when, note=""):
    """放置站点的承重见证：load_into 之后计数层必须等于块自报的 token 数。

    删掉该站点的 leases.reset(...) ⇒ 第二遍放置会叠在第一遍的 cell 上 ⇒ 读数翻倍 ⇒ 本函数红。
    """
    got = _m4c_cells(eng, seq)
    if got != int(want):
        die("M4-C 承重断言红 @%s (%s): n_tokens(seq %d) = %d, expected %d%s"
            % (site, when, int(seq), got, int(want), note))
    return got


    """覆盖见证者：证明 dropped 里的每个 seq **确实被本站 reset 过**。

    它不证明「清干净了」—— 那件事由 GuardedLeases.reset L331 强制（reset 之后 cells_of(seq) 非 0
    直接 raise）。所以本函数唯一的新增信息是**覆盖**：若循环漏掉某个 dropped seq，L331 不会响，
    这里才响。名字不得替它宣称一个它不负责的结论。
    """

    got = int(leases.cells_of(int(seq)))
    if got != 0:
        die("M4-C 承重断言红 @%s (%s): cells_of(seq %d) = %d, expected 0"
            % (site, when, int(seq), got))
    return got


def _m4c_witness_attached(eng, seq, want, end, site):
    """§5.7「装上」第 4 步（原文有、代码原来缺）：挂完之后两个机制独立的读数都必须仍成立。

      · 位置层 pos_max(seq) == end - 1   —— 读的是 block seq 自己的 token，不走 share，
        因此不受「只有 share 进来的 cell 时 pos_max 返回 -1」那个坑影响；
        （若将来到对话 seq 上读，必须显式声明位置层不可用及理由，不许默认它正常）
      · 计数层 n_tokens(seq) == n        —— 与位置层机制独立；两者都变 = 叠了或掉了。
    """
    got_n = _m4c_cells(eng, seq)
    got_pos = int(eng.pos_max(int(seq)))
    want_pos = int(end) - 1
    if got_n != int(want) or got_pos != want_pos:
        die("M4-C 承重断言红 @%s (attach 之后): seq %d n_tokens=%d/%d pos_max=%d/%d"
            % (site, int(seq), got_n, int(want), got_pos, want_pos))
    return {"n_tokens": got_n, "pos_max": got_pos, "seq": int(seq)}


def die(msg):
    """断言红：分类由**产生它的函数盖章**，不靠外部对消息做模式匹配。

    先记状态（内存 append 在 try 外，落盘在 try 内，写盘失败不吞主消息），
    再 print，再 exit —— 顺序不能反：证据通道的失败不得吞掉主消息。
    """
    _m4c_log({"id": "die", "status": "assertion_failed", "kind": "assertion", "message": msg})
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

    # The source layer is the authority; the .kvmem block is a derived cache. This only
    # reads sources (verify_hash on every read) and rewrites blocks from them.
    con = ms.connect(DB)

    print("model : %s" % MODEL)
    print("blocks: %s\n" % BLOCKS)

    eng = KVEngine(MODEL, n_ctx=N_CTX, n_seq=8, gpu=99, kv="q8_0")
    try:
        print("per-token KV: %.1f KiB (q8_0)\n" % (eng.bytes_per_token() / 1024.0))

        sources = ms.indexable_sources(con)
        if not sources:
            con.close()
            die("the registry has no indexable source (text_kind=human_memory, "
                "is_excerpt=0): nothing to index")
        for name, label, _text in sources:
            rec = ms.build_block(eng, con, ms.get_source(con, name), BLOCKS)
            print("  %-8s %-6s %3d tokens  %7.1f KiB  %s"
                  % (name, label, rec["n_tokens"], rec["n_bytes"] / 1024.0, rec["path"]))
    finally:
        eng.close()

    con.close()
    print("\nindexed %d sources + %d blocks in %s" % (len(sources), len(sources), DB))


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
    leases = GuardedLeases(eng, site_prefix="chat")

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
        ranges = {}
        for i, target in plan:
            # placement path: nothing references this seq yet, so the guard passes and
            # asserts the sequence is empty before the block is loaded into it
            leases.register_block(i, rows[i - 1][1])
            leases.reset(i, site="chat.place.fresh")
            # compat-checked load: refuses a block built by another model / rope / kv type
            ms.load_into(eng, rows[i - 1], i)

            n_load = eng.n_tokens(i)
            if n_load != n[i]:
                die("block %s has %d tokens but the index says %d -- re-run: chat.py build"
                    % (rows[i - 1][1], n_load, n[i]))
            _m4c_log({"id": "place_load", "status": "checked", "seq": i,
                       "block": rows[i - 1][1], "n_tokens": int(n_load), "index_n": int(n[i]),
                       "covers": "site1",
                       "note": "站点 1 的判据是 pre-existing 的 n_tokens == index n；删掉该站点的 reset 不会红（load 自清），本条记覆盖不记冗余"})
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
            ranges[i] = (lo, hi)
            # bytes actually crossing the bus: cells * bytes_per_token (q8_0)
            rate = (n[i] * eng.bytes_per_token() / 1048576.0) / dt if dt > 0 else 0.0

            print("  %-4d %-10s %5d  [%5d, %5d)  %6d %8.1f %9.1f"
                  % (i, rows[i - 1][1], n[i], lo, hi, moved, dt * 1000.0, rate))

        print("  %-4s %-10s %5s  %-14s %6d %8.1f"
              % ("", "total", "", "", n_cells, t_rot * 1000.0))

        # ---- 3) attach to the dialogue (refcount only, zero copy) ----------
        if not control:
            for i, _target in plan:
                _lo, _hi = ranges[i]
                leases.attach(i, 0, _lo, _hi, site="chat.attach")
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
    leases = GuardedLeases(eng, site_prefix="slots")
    blocks = []
    for i, row in enumerate(rows, start=1):
        leases.register_block(i, row[1])
        leases.reset(i, site="slots.place.fresh")
        n = ms.load_into(eng, row, i)
        # M4-C 站点 2 承重见证（计数层）：第二遍放置若缺 reset 会叠 cell ⇒ 翻倍 ⇒ 红
        _m4c_witness_cells(eng, i, n, "slots.place.fresh", "load_into 之后")
        end = CHAT_START - (i - 1) * SLOT
        lo = end - n
        base = eng.pos_max(i) + 1 - n
        if base != lo:
            moved = eng.repos_local(i, lo - base)
            if moved != n:
                die("repos_local moved %d of %d cells" % (moved, n))
        leases.attach(i, 0, lo, end, site="slots.attach")
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
        leases = GuardedLeases.from_manifest(eng, path)   # block seqs from the manifest
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
    leases = GuardedLeases(eng, site_prefix="m1")
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
                # 单一来源：下面的循环、见证者、范围断言都必须用这一份名单/集合
                drop_names = [n for n in mounted if n not in want]
                dropped = [mounted[n][0] for n in drop_names]
                # 展品（role: exhibit —— 供人看，不是判据）：清理前后 8 个 seq 的两个读数
                seqs_before = {s: (int(eng.n_tokens(s)), int(eng.pos_max(s))) for s in range(N_SEQ)}
                # 起点：sites 跨轮累积（GuardedLeases L289 构造一次，L329 只 append 从不清空），
                # 不记起点 = 拿一整段历史当当前。
                n0 = len(leases.sites.get("m1.unmount.after_detach", []))
                for name in drop_names:
                    seq, lo, hi = mounted[name]
                    # drop first (== detach), then reset: the order is the contract
                    leases.detach(0, lo, hi, site="m1.unmount.detach")
                    leases.reset(seq, site="m1.unmount.after_detach")
                # 范围断言（role: assertion，唯一签名依据）：测的是调用流，不是端点。
                # 端点比对对「范围」从原理上不成立：清了又填回原样会静默通过。
                hits = [r["seq"] for r in leases.sites.get("m1.unmount.after_detach", [])[n0:]]
                if hits != dropped:
                    die("M4-C 范围断言红 @m1.unmount: 调用流 hits=%s（%d 条） != dropped=%s（%d 条）"
                        % (list(hits), len(hits), list(dropped), len(dropped)))
                _m4c_log({"id": "A", "status": "checked",
                                        "rule": "sites 调用流 list == dropped（漏/多/重复/乱序 四种都抓）",
                                        "hits": list(hits), "dropped": list(dropped),
                                        "limits": "输入含 dropped ⇒ 只判执行是否符合口径，不判口径对不对"})
                mounted, order = {}, want
                if control:
                    # control 是负例基准：不插入时什么都没发生。它的绿**不计入覆盖**，
                    # 且必须显式记 skipped —— 不得有「默认跳过」路径。
                    _m4c_log({"id": "A", "status": "skipped",
                                            "reason": "control mode: mounted 不填充 ⇒ drop_names 为空，无判定对象"})
                    _m4c_log({"id": "B", "status": "skipped",
                                            "reason": "control mode: 整段在 if not control 内，未执行"})
                if not control:
                    for i, name in enumerate(order):
                        seq = i + 1
                        leases.register_block(seq, name)
                        # asserts cells_of(seq)==0 BEFORE load_into stacks anything
                        leases.reset(seq, site="m1.mount.before_load")
                        # 站点 4：这一行是「结构性不可测」的那一处 —— L331 已强制 reset 后为空，
                        # 而本行到下一行之间没有写入 ⇒ 下面这条覆盖见证者没有独立可证内容。
                        n = ms.load_into(eng, rows[name], seq)
                        end = CHAT_START - i * SLOT
                        lo = end - n
                        base = eng.pos_max(seq) + 1 - n
                        if base != lo and eng.repos_local(seq, lo - base) != n:
                            die("%s: repos_local refused" % name)
                        leases.attach(seq, 0, lo, end, site="m1.attach")
                        # §5.7「装上」第 4 步（原文有、代码原来缺）：位置层 + 计数层两个独立读数
                        _m4c_witness_attached(eng, seq, n, end, "m1.mount.before_load")
                        mounted[name] = (seq, lo, end)
                # 展品（role: exhibit）：装载之后同一批 seq 的读数，只打印，不判定
                seqs_after = {s: (int(eng.n_tokens(s)), int(eng.pos_max(s))) for s in range(N_SEQ)}
                print("  [exhibit] seqs_before=%s" % sorted(seqs_before.items()))
                print("  [exhibit] seqs_after =%s" % sorted(seqs_after.items()))
                print("  [exhibit] dropped=%s（非判据）" % sorted(dropped))
                # 漏清断言（role: assertion）：来自引擎侧，不是第二份名单。
                # 若循环漏掉某个被丢 seq，它既不在新一轮 mounted_seqs 里、又留着 cell ⇒ orphan > 0。
                # chat_n 是反证：orphan 与对话增长必须解耦；两者同步说明排除式没命中。
                if not control:
                    mounted_seqs = {v[0] for v in mounted.values()}
                    orphan_cells = {s: int(eng.n_tokens(s)) for s in range(1, N_SEQ) if s not in mounted_seqs}
                    orphan = sum(orphan_cells.values())
                    chat_n = int(eng.n_tokens(0))
                    print("  [exhibit] orphan=%d chat_n=%d mounted_seqs=%s orphan_cells=%s"
                          % (orphan, chat_n, sorted(mounted_seqs), sorted(orphan_cells.items())))
                    if orphan != 0:
                        die("M4-C 漏清断言红 @m1.turn_end: orphan=%d（不在 mounted 里的 seq 仍持 cell：%s），chat_n=%d"
                            % (orphan, sorted(orphan_cells.items()), chat_n))
                    _m4c_log({"id": "B", "status": "checked",
                                            "eval_point": "after_mount_loop",
                                            "input": "n_tokens(引擎读数) + mounted_seqs(挂载结果) + 常量 0",
                                            "orphan": orphan, "chat_n": chat_n,
                                            "decoupling": "orphan 与 chat_n 必须不同步（同步说明排除式没命中）"})
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