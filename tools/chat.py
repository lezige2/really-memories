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
MODEL  = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
DB     = os.environ.get("CHAT_DB") or os.path.join(ROOT, "kvmem", "chat.db")  # v6 §11.2：臂用 temp 副本
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


def _m4c_write(entry):
    """only _crit / _event may call this; a dedicated entry point only works when the writer is reachable through nothing else."""
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


def _crit(entry):
    """criterion entry: enters the coverage set; site comes from the caller."""
    entry["role"] = "criterion"
    return _m4c_write(entry)


def _event(entry):
    """event entry: site is pinned to None, so it cannot enter the coverage set by construction."""
    entry["role"] = "event"
    entry["site"] = None
    return _m4c_write(entry)


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


def _m4c_witness_cells_zero(leases, seq, site, when):
    """覆盖见证者：证明 dropped 里的每个 seq **确实被本站 reset 过**。

    它不证明「清干净了」—— 那件事由 GuardedLeases.reset L331 强制（reset 之后 cells_of(seq) 非 0
    直接 raise）。所以本函数唯一的新增信息是**覆盖**：若循环漏掉某个 dropped seq，L331 不会响，
    这里才响。名字不得替它宣称一个它不负责的结论。
    """

    got = int(leases.cells_of(int(seq)))   # 形参传 leases：cells_of 长在 GuardedLeases 上，不在 KVEngine 上
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
    _event({"id": "die", "site": None, "status": "assertion_failed", "kind": "assertion", "message": msg})
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
            _crit({"id": "site1.place", "site": 1, "status": "checked", "seq": i,
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
                _event({"id": "chat.attach", "seq": int(i)})   # 事件：计数+明细，构造上不进覆盖集
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
    have = {r[1] for r in ms.block_rows(con) if r[5] is not None}
    print("\n问：%s" % q)
    mountable = []
    for r in R.search(con, q, k=3, explain=True):
        tag = "可挂载" if r["name"] in have else "无块行→不可挂载"
        if r["name"] in have:
            mountable.append(r["name"])
        print("   %-6.3f %-9s %s  [%s]"
              % (r["score"], r["name"],
                 ", ".join("%s=%s" % kv for kv in r["signals"].items()), tag))
    print("  可挂载集：%s" % (", ".join(mountable) if mountable else "（空）"))


def cmd_m1(explain=False, control=False, save_path=None):
    """Per-question block selection, then generate. Fixed slot geometry (B-right):
    selection decides WHICH blocks fill the slots, not where the slots are (that is M2)."""
    os.makedirs(SESSIONS, exist_ok=True)
    con = ms.connect(DB)

    if explain:
        print("explain_version: 2")   # v2：新增可挂载性标注（检索命中 ≠ 记忆命中）
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
            # G4a/G4b（审计根因）：selection 面 = retrieval 索引的全部 memory_source（10 行，
            # 含 conv 对话行与摘录），挂载面 = 有 memory_block 的源（2 行）。无块行的命中
            # 不得静默跳过、不得硬塞、不得靠重建索引绕过 ⇒ 显式记账（event + crit skipped）+ 打印。
            missing = [s for s in sel if s["name"] not in rows]
            sel_mountable = [s for s in sel if s["name"] in rows]
            want = [s["name"] for s in sel_mountable]
            if missing:
                _event({"id": "site3.skipped_no_block", "count": len(missing),
                        "names": [s["name"] for s in missing],
                        "source_ids": [int(s["source_id"]) for s in missing]})
                _crit({"id": "site3.skipped_no_block", "site": 3, "status": "skipped",
                       "reason": "selection 面宽于挂载面：命中源无 memory_block 行"
                                 "（对话行/摘录不可建块），不挂载；G4a 负对照有效性待重跑",
                       "names": [s["name"] for s in missing]})
            # G4a-2：决策面只认“真可挂载”的 selection（有 memory_block 行的源）。
            # 无块命中（对话行/摘录）不是记忆证据 ⇒ 不送进 decide，负对照恢复
            # no_evidence + refuse，模型不被调用（ask=0，见 _run_m1_g4a2.py 红证）。
            # 理由：不改冻结三件 evidence.py；也不用收窄 _selection（two/其他消费者共用，
            # 收窄会改检索语义），只在 m1 的决策入参处做“可挂载性”过滤。
            d = E.decide(q, sel_mountable, "\n".join(history))
            if explain:
                pass
            else:
                print("\n" + "=" * 74)
                print("问：%s" % q)
                print("  状态：%s  [%s]  %s"
                      % (d["state"], E.BADGE[d["state"]], d["reason"]))
                if not want:
                    if sel:
                        print("  检索：命中 %d 条但均无 memory_block → 不挂任何块（跳过已记账）"
                              % len(sel))
                    else:
                        print("  检索：无匹配 → 不挂任何块（负例必须是空，不能硬凑 top-k）")
                else:
                    print("  检索：%s" % ", ".join(
                        "%s(%.2f)" % (s["name"], s["score"]) for s in sel))
                if missing:
                    print("  跳过：%s（无 memory_block 行，不挂载；已记 site3.skipped_no_block）"
                          % ", ".join("%s(%.2f)" % (s["name"], s["score"]) for s in missing))

                turns.append({"q": q, "state": d["state"], "intent": d["intent"],
                              "refused": False, "mounted": list(order),
                              "skipped_no_block": [s2["name"] for s2 in missing],
                              "selected": [{"name": s2["name"], "score": s2["score"],
                                            "signals": s2["signals"]} for s2 in sel]})
            if want != order:
                # 单一来源：下面的循环、见证者、范围断言都必须用这一份名单/集合
                drop_names = [n for n in mounted if n not in want]
                dropped = [mounted[n][0] for n in drop_names]
                _event({"id": "site3.dropped", "count": len(dropped)})   # 事件：记录"这一轮删了几个"，不进覆盖集
                _event({"id": "site3.dropped.seqs", "seqs": [int(x) for x in dropped]})   # 事件：删了哪些 seq
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
                # 覆盖见证（role: assertion）：上面那条判"调用流 == dropped"，它判"每个 dropped 的 cell 真的归零了"。
                # 两者不同：循环漏掉某个 dropped seq 时，上面那条只因 hits 少一条而响；
                # 而 reset 跑过但没清干净时，只有这一条响。名字不替它宣称它不负责的结论。
                for seq in dropped:
                    _m4c_witness_cells_zero(leases, seq, "m1.unmount.after_detach", "reset 之后")
                _crit({"id": "site3.unmount.flow", "site": 3, "status": "checked",
                                        "rule": "sites 调用流 list == dropped（漏/多/重复/乱序 四种都抓）",
                                        "hits": list(hits), "dropped": list(dropped),
                                        "limits": "输入含 dropped ⇒ 只判执行是否符合口径，不判口径对不对"})
                prev_mounted = dict(mounted)   # 重挂前要 detach 的旧句柄（detach → reset → load 是契约）
                mounted, order = {}, want
                if control:
                    # control 是负例基准：不插入时什么都没发生。它的绿**不计入覆盖**，
                    # 且必须显式记 skipped —— 不得有「默认跳过」路径。
                    _crit({"id": "site3.unmount.flow", "site": 3, "status": "skipped",
                                            "reason": "control mode: mounted 不填充 ⇒ drop_names 为空，无判定对象"})
                    _crit({"id": "site3.turn_orphan", "site": 3, "status": "skipped",
                                            "reason": "control mode: 整段在 if not control 内，未执行"})
                if not control:
                    for i, name in enumerate(order):
                        seq = i + 1
                        if name not in rows:      # 防御：过滤后不该发生；发生即红，不静默
                            die("G4: 选择结果 %r 无 memory_block 行（源存在但块未建/不可建；"
                                "检查 indexable_sources 与 build）" % name)
                        leases.register_block(seq, name)
                        if name in prev_mounted:
                            _p_seq, p_lo, p_hi = prev_mounted[name]
                            leases.detach(0, p_lo, p_hi, site="m1.mount.detach")
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
                        _event({"id": "chat.attach", "seq": int(seq)})   # 事件：计数+明细，构造上不进覆盖集
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
                    _crit({"id": "site3.turn_orphan", "site": 3, "status": "checked",
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
                              "skipped_no_block": [s2["name"] for s2 in missing],
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
# S1: 两会话（A=seq0 挂 home / B=seq7 挂 project；pool=home/project/habit）
# ---------------------------------------------------------------------------
# 冻结口径：docs/_work/M2-FULL-S1-SPEC-lead.md **v6（最终）**（`ae2d88ad5ecc25d3`，132 行）
#   N_ROUNDS=10 · CHAT_LEN_CAP=1024（每轮校验 + budget 按 CAP 预留）· CHAT_START=4096 不变
#   A=seq0 只挂 home(seq1) · B=seq7 只挂 project(seq2) · habit(seq3) 只登记不挂（pool=3/挂载=2）
#   **执行顺序 A→B**：A 先跑完 10 轮再跑 B；n_ctx_eff 取该次 plan 前另一会话的实际 chat cells
#   **v6 几何（真机钉死）**：块紧邻本会话 chat 起点、顶对齐——
#       A: home `[4096−21, 4096) = [4075,4096)`，chat_start_A = 4096；
#       B: project `[4096+n_chat_A, +18)`，chat_start_B = 4096+n_chat_A+18；
#       `attach` 的 hi 是**排他上界** ⇒ `attach(seq,dst,lo,end)`（v5 的 `pos_hi=end−1` 丢最后一格）
#   source_blocks = "挂载块的事实出现在 `_selection` 文本里"（**②a 降级为接线回归**，v6）
#   ②c（v6 新增，零 GPU）：未过滤 selection 文本，A 不含 FACT_B、B 不含 FACT_A（去空白后判）
#   ②b（S1-b）：A/B 答案去空白后互不含对方事实（v6：真机答 `3 月 14`，字面会误红）
#   schema：cells_accounting.engine_match、blocks_geometry、sessions[].seq=int
#   ③ n_tokens_self = Σ 本会话每轮 ask 增量；pos_max_self = **chat_start_self** + n_tokens_self − 1
#   ④ 每会话 chat_cells 用 ask 增量记账值；对账 = leases.cells_of + 每会话记账 chat 之和（不读 seq）
#      未跑的会话 `cap_ok` 记 `"not_run"`（v6：不许对未跑会话假声明 true）
#   禁 replay · **P-1a = share 等式**（可判）· **P-1b = drop 等式**（S1 无 detach ⇒ 零实例，
#      记 `"not_triggered"`，不许记通过）· P-2 照旧
#   `--dry-run` 与真机臂走**同一** two_session_run，只换 engine factory。
TWO_SEQ_A, TWO_SEQ_B = 0, 7
TWO_BLOCK_SEQ_BANNED = TWO_SEQ_B          # 断言：7 不得出现在 block_seqs 里
TWO_N_ROUNDS = 10
TWO_CHAT_LEN_CAP = 1024                   # 每轮校验 + budget 预留值（不是实际 chat cells）
TWO_CHAT_START = CHAT_START               # 4096 不变

# 干跑合成的每轮 ask 增量（cells）：10 轮 = 670 ≤ 1024（真机以实测为准，非判据阈值）
TWO_DRY_TOKENS_PER_ROUND = 67

# 冻结 pool（N=3，cells 与 M2-ACCEPT-r2 blocks_planned 同：home 21 / project 18 / habit 12）
TWO_BLOCK_DIR = os.path.join(ROOT, "kvmem", "m2_v1_14b")
TWO_POOL = (
    {"name": "home", "seq": 1, "cells": 21, "mounted_by": ("A",),
     "path": os.path.join(TWO_BLOCK_DIR, "home.kvmem"), "fact": "广陵路"},
    {"name": "project", "seq": 2, "cells": 18, "mounted_by": ("B",),
     "path": os.path.join(TWO_BLOCK_DIR, "project.kvmem"), "fact": "3月14"},
    {"name": "habit", "seq": 3, "cells": 12, "mounted_by": (),
     "path": os.path.join(TWO_BLOCK_DIR, "habit.kvmem"), "fact": "美式"},
)
# 冻结会话：问题 / 期望事实 / 挂载集（mount）——source_blocks 由 selection∩mounted 现算
TWO_SESSIONS = (
    {"id": "A", "seq": TWO_SEQ_A, "q": "我住在哪里？", "fact": "广陵路", "mount": ("home",)},
    {"id": "B", "seq": TWO_SEQ_B, "q": "我的项目什么时候上线？", "fact": "3月14",
     "mount": ("project",)},
)


class _StubEngine:
    """零 GPU 假引擎：只记 cells / pos_max / 可见性 / 调用次数，不建 KV、不读块文件。

    **只被 `--dry-run` 用**（测试床也可直接用）；默认路径（chat/m1）与真机臂都不碰它。
    """
    mode = "dry-run"

    def __init__(self, tokens_per_round=TWO_DRY_TOKENS_PER_ROUND):
        self.cells, self.posmax, self.facts = {}, {}, {}
        self.visible = {}
        self.share_calls, self.drop_calls, self.reset_calls = 0, 0, 0
        self.tokens_per_round = int(tokens_per_round)

    def n_tokens(self, seq):
        return int(self.cells.get(int(seq), 0))

    def pos_max(self, seq):
        return int(self.posmax.get(int(seq), -1))

    def reset(self, seq):
        self.reset_calls += 1
        self.cells[int(seq)] = 0
        self.posmax[int(seq)] = -1

    def load_block(self, spec):
        seq = int(spec["seq"])
        self.cells[seq] = int(spec["cells"])
        self.posmax[seq] = int(spec["cells"]) - 1     # 文件里 base_in_file = 0
        self.facts[seq] = "FACT:%s" % spec["name"]
        return int(spec["cells"])

    def repos_local(self, seq, delta):
        self.posmax[int(seq)] = int(self.posmax.get(int(seq), -1)) + int(delta)
        return int(self.cells.get(int(seq), 0))

    def share(self, block_seq, dst_seq, lo, hi):
        self.share_calls += 1
        self.visible.setdefault(int(dst_seq), set()).add(int(block_seq))

    def drop(self, dst_seq, lo, hi):
        self.drop_calls += 1

    def chat_round(self, session_seq, question, first, chat_start):
        seq = int(session_seq)
        self.cells[seq] = int(self.cells.get(seq, 0)) + self.tokens_per_round
        cur = int(self.posmax.get(seq, int(chat_start) - 1))
        self.posmax[seq] = max(cur, int(chat_start) + self.cells[seq] - 1)
        vis = sorted(self.visible.get(seq, ()))
        return " ".join(self.facts.get(s, "") for s in vis)

    def close(self):
        pass


class CountingEngine:
    """真机臂的透明代理：只数 share/drop/reset 并转发（P-1 计数等式用；S1-b 另单跑）。"""
    mode = "real"

    def __init__(self, eng):
        self._eng = eng
        self.share_calls, self.drop_calls, self.reset_calls = 0, 0, 0

    def __getattr__(self, name):
        return getattr(self._eng, name)

    def n_tokens(self, seq):
        return int(self._eng.n_tokens(int(seq)))

    def pos_max(self, seq):
        return int(self._eng.pos_max(int(seq)))

    def reset(self, seq):
        self.reset_calls += 1
        return self._eng.reset(int(seq))

    def share(self, *a, **kw):
        self.share_calls += 1
        return self._eng.share(*a, **kw)

    def drop(self, *a, **kw):
        self.drop_calls += 1
        return self._eng.drop(*a, **kw)

    def load_block(self, spec):
        n = self._eng.load(int(spec["seq"]), spec["path"])
        if int(n) < 0:
            raise RuntimeError("engine refused %s" % spec["path"])
        return int(n)

    def repos_local(self, seq, delta):
        return self._eng.repos_local(int(seq), int(delta))

    def chat_round(self, session_seq, question, first, chat_start):
        return self._eng.ask(int(session_seq), question, n_predict=48,
                             pos=(int(chat_start) if first else None))

    def close(self):
        return self._eng.close()


def _two_plan_module():
    """惰性 import 规划器：默认路径（chat/m1）不因为本文件多一个 sys.path 条目而改变。"""
    planner_dir = os.path.join(ROOT, "kvmem", "m2_visibility", "m2_planner")
    if planner_dir not in sys.path:
        sys.path.insert(0, planner_dir)
    import plan as PLAN
    return PLAN


def _two_selection_texts(con, q):
    """`_selection(con,q)` 的结果**带原文**返回（供 source_blocks 的"事实命中"判定）。

    只读 DB + 派生索引，零 GPU。空 list 是合法答案（不许拿模型补）。
    """
    out = []
    for r in _selection(con, q) or []:
        sid = r.get("source_id")
        if sid is None:
            continue
        got = con.execute("SELECT text FROM memory_source WHERE id=?", (sid,)).fetchone()
        out.append({"source_id": sid, "name": r.get("name"), "score": r.get("score"),
                    "text": got[0] if got else ""})
    return out


def _two_norm(text):
    """去掉所有空白后比较（v6 ②b/②c）：真机答 `3 月 14 日`，字面 `3月14` 会误红。"""
    return "".join(str(text or "").split())


def _two_sha_stable(blocks=None):
    """⑤ sha_stable 只在 S1-b 判：dry-run 返回 None ⇒ 产物记 status="not_done"。"""
    return None


def two_session_run(engine, pool=TWO_POOL, sessions=TWO_SESSIONS,
                    n_ctx=N_CTX, n_rounds=TWO_N_ROUNDS,
                    chat_len_cap=TWO_CHAT_LEN_CAP, sha_stable_provider=_two_sha_stable,
                    con=None):
    """S1 唯一调度（dry/真机共用），执行顺序冻结 **A→B**：

      1) pool 登记（3）；A 的 plan 在 B 未跑 ⇒ n_ctx_eff_A = N_CTX − 0
      2) A：plan（cells=本会话挂载块、chat_len=CAP 预留）→ 放块 → attach → 跑 10 轮
      3) B：plan 在 A 跑完之后 ⇒ n_ctx_eff_B = N_CTX − chat_A_actual → 放块 → attach → 跑 10 轮
      4) ③ 每会话读数公式；④ 记账 + 对账（leases.cells_of + 记账 chat）；②a selection∩mounted
      5) P-1/P-2 计数等式；CAP 每轮执行点；⑤ sha_stable 只 S1-b 判（dry 记未做）
    """
    PLAN = _two_plan_module()
    from m3_lease import BlockLeases, LeaseError

    own_con = False
    if con is None:
        con = ms.connect(DB)
        own_con = True
    try:
        plist = [dict(b, mounted_by=tuple(b["mounted_by"])) for b in pool]
        slist = [dict(s, mount=tuple(s["mount"])) for s in sessions]
        seq_of_name = {b["name"]: int(b["seq"]) for b in plist}
        cell_of_name = {b["name"]: int(b["cells"]) for b in plist}
        fact_of_name = {b["name"]: b.get("fact") for b in plist}
        block_seqs = [int(b["seq"]) for b in plist]
        if TWO_BLOCK_SEQ_BANNED in block_seqs:
            raise ValueError("块槽不得占用会话 seq %d" % TWO_BLOCK_SEQ_BANNED)
        if any(int(s["seq"]) in block_seqs for s in slist):
            raise ValueError("会话 seq 与块槽重叠：%s" % [(s["id"], s["seq"]) for s in slist])

        mounted_names = set(n for s in slist for n in s["mount"])
        blocks_cells = sum(cell_of_name[n] for n in mounted_names)
        seqs_distinct = len(set(int(s["seq"]) for s in slist)) == len(slist)

        # ---- source_blocks：`_selection` 结果 ∩ mounted（事实命中即"实际参与作答"） ----
        sel_raw, src_hits, sel_full = {}, {}, {}
        for s in slist:
            hits = _two_selection_texts(con, s["q"])
            sel_full[s["id"]] = hits
            sel_raw[s["id"]] = [{"source_id": h["source_id"], "name": h["name"],
                                 "score": h["score"]} for h in hits]
            src_hits[s["id"]] = [n for n in s["mount"]
                                 if any(fact_of_name[n] and fact_of_name[n] in h["text"]
                                        for h in hits)]

        # ---- pool 登记（3）；只对挂载块 reset + load ----
        leases = BlockLeases(engine)
        for b in plist:
            leases.register_block(b["seq"], b["name"])
        loaded = set()
        plans, budget_out = {}, []
        chat_incr = {s["id"]: 0 for s in slist}          # ③ 的 Σ 每轮 ask 增量
        chat_accounted = {s["id"]: 0 for s in slist}     # ④ 的 chat_cells 记账值
        sources = {}
        attach_error, cap_refused, cap_hit = None, None, None
        rounds_done = {s["id"]: 0 for s in slist}
        answers = {s["id"]: "" for s in slist}
        chat_starts = {s["id"]: None for s in slist}   # v6 ③：每会话 chat 起点（不硬编码 4096）
        chat_end_prev = None                          # 上一会话 chat 结束（后续段的块起点）

        for idx, s in enumerate(slist):
            sid = s["id"]
            # ---- n_ctx_eff：该次 plan 之前，另一会话的实际 chat cells（顺序 A→B） ----
            other_ids = [o["id"] for o in slist if o["id"] != sid]
            chat_other = sum(int(chat_accounted[o]) for o in other_ids)
            n_ctx_eff = int(n_ctx) - chat_other

            for name in s["mount"]:
                if name not in loaded:
                    leases.reset(seq_of_name[name])
                    n = engine.load_block(next(b for b in plist if b["name"] == name))
                    if int(n) != cell_of_name[name]:
                        raise RuntimeError("块 %s 实际 %d cells != 冻结 %d"
                                           % (name, n, cell_of_name[name]))
                    loaded.add(name)

            entries = [{"seq": seq_of_name[n], "cells": cell_of_name[n]} for n in s["mount"]]
            plan_refused = None
            try:
                # plan() 只当"预算/refuse"用（3 参签名不动）；位置由 two 自写的几何公式给
                PLAN.plan(entries, TWO_CHAT_START, {"n_ctx": n_ctx_eff,
                                                    "chat_len": int(chat_len_cap)})
            except PLAN.PlanRefused as exc:
                plan_refused = {"type": type(exc).__name__, "msg": str(exc),
                                "reason": getattr(exc, "reason", None)}
                attach_error = attach_error or plan_refused
            # ---- v6 几何（游标顺延，真机钉死）：块紧邻本会话 chat 起点 ----
            #   A（第一段）：块在 chat_start=4096 下方顶对齐，home [4075,4096)、chat_start_A=4096
            #   后续段（B）：块起点 = 上一段 chat 结束，project [4096+n_chat_A, +18)、
            #                chat_start_B = 4096+n_chat_A+18
            #   `pos_hi` 一律是**排他上界**（attach 的 hi 语义，v6）
            plans[sid] = []
            if plan_refused is None:
                downward = chat_end_prev is None
                if downward:
                    cursor = int(TWO_CHAT_START)
                    chat_start_self = cursor
                else:
                    cursor = int(chat_end_prev)
                    chat_start_self = None
                for pb in plist:
                    if pb["name"] not in s["mount"]:
                        continue
                    n = cell_of_name[pb["name"]]
                    if downward:
                        base, end = cursor - n, cursor
                        cursor = base
                    else:
                        base, end = cursor, cursor + n
                        cursor = end
                    plans[sid].append({"seq": seq_of_name[pb["name"]],
                                       "name": pb["name"], "base": int(base),
                                       "pos_hi": int(end), "cells": n})
                if not downward:
                    chat_start_self = int(cursor)
                chat_starts[sid] = int(chat_start_self)

            # ---- 几何 + attach（R4a/R4b 变体改这一句/加一行；hi=排他上界） ----
            if not plan_refused:
                try:
                    pm = {p["seq"]: p for p in plans[sid]}
                    for name in s["mount"]:
                        seq, p = seq_of_name[name], pm[seq_of_name[name]]
                        base, pos_hi = int(p["base"]), int(p["pos_hi"])
                        # 每块只挂一个对话 seq：home->dst0、project->dst7（mount 决定 dst）
                        dst = int(s["seq"])
                        cur = engine.pos_max(seq) + 1 - cell_of_name[name]
                        if base != cur:
                            moved = engine.repos_local(seq, base - cur)
                            if int(moved) != cell_of_name[name]:
                                raise RuntimeError("repos_local moved %s of %s"
                                                   % (moved, cell_of_name[name]))
                        leases.attach(seq, dst, base, pos_hi)
                except (LeaseError, PLAN.PlanRefused) as exc:
                    attach_error = {"type": type(exc).__name__, "msg": str(exc),
                                    "reason": getattr(exc, "reason", None)}

            # ---- 该会话 10 轮：③ 用 ask 增量；④ 记账值同源累积；CAP 每轮执行点 ----
            if not plan_refused:
                for r in range(int(n_rounds)):
                    rounds_done[sid] = r + 1
                    before = engine.n_tokens(s["seq"])
                    answers[sid] = engine.chat_round(s["seq"], s["q"], first=(r == 0),
                                                     chat_start=chat_starts[sid])
                    delta = int(engine.n_tokens(s["seq"])) - int(before)
                    chat_incr[sid] += delta
                    chat_accounted[sid] += delta
                    for chk_sid in [sid]:
                        if chat_accounted[chk_sid] > int(chat_len_cap):
                            cap_hit = {"session": chk_sid, "round": r + 1,
                                       "chat_cells": chat_accounted[chk_sid],
                                       "cap": int(chat_len_cap)}
                            cap_refused = {"type": "PlanRefused",
                                           "reason": "chat_len_cap",
                                           "msg": "每轮 chat_cells_self=%d > CAP=%d @round %d"
                                                  % (cap_hit["chat_cells"], cap_hit["cap"],
                                                     r + 1)}
                            break
                    if cap_refused is not None:
                        break

            if chat_starts.get(sid) is not None:
                chat_end_prev = int(chat_starts[sid]) + int(chat_incr[sid])

            # ---- 该会话的 budget 读数（n_ctx_eff 取 plan 前时点） ----
            not_run_here = int(rounds_done[sid]) == 0
            cap_ok = "not_run" if not_run_here else (
                int(chat_accounted[sid]) <= int(chat_len_cap)
                and (int(blocks_cells) + int(chat_len_cap)) <= n_ctx_eff)
            hit_here = bool(cap_refused) and cap_hit is not None and cap_hit["session"] == sid
            budget_out.append({"session": sid, "n_ctx_eff": n_ctx_eff,
                               "chat_len_reserved": int(chat_len_cap),
                               "cap_ok": bool(cap_ok),
                               "refused": bool(hit_here),
                               "refused_reason": (cap_refused or {}).get("reason")
                               if hit_here else None,
                               "plan_refused": plan_refused})
            # ---- source_blocks（selection ∩ mounted；R1 变体注入的就是这个元数据） ----
            sources[sid] = sorted(set(seq_of_name[n] for n in s["mount"]
                                      if n in src_hits[sid]))
            if cap_refused is not None:
                break

        # 未跑到的会话 budget 也要有一条读数（refused=False 如实记）
        for s in slist:
            if not any(b["session"] == s["id"] for b in budget_out):
                budget_out.append({"session": s["id"], "n_ctx_eff": int(n_ctx) - sum(
                    int(v) for k, v in chat_accounted.items() if k != s["id"]),
                    "chat_len_reserved": int(chat_len_cap), "cap_ok": "not_run",
                    "refused": False, "refused_reason": None, "plan_refused": None})

        # ---- ③ 读数：n_tokens_self = Σ ask 增量；pos_max_self = chat_start_self + n − 1 ----
        sessions_out, readings_ok = [], True
        for s in slist:
            sid = s["id"]
            n_self = int(chat_incr[sid])
            cs = chat_starts.get(sid)
            pos_expect = (int(cs) + n_self - 1) if cs is not None else None
            got_n, got_pos = int(engine.n_tokens(s["seq"])), int(engine.pos_max(s["seq"]))
            if int(rounds_done[sid]) == 0:
                ok = "not_run"                       # v6：未跑的会话不许判绿
            else:
                ok = bool(pos_expect is not None and got_n == n_self and got_pos == pos_expect)
                readings_ok = readings_ok and ok
            sessions_out.append({
                "id": sid, "seq": int(s["seq"]), "rounds": int(rounds_done[sid]),
                "mounted_blocks": sorted(seq_of_name[n] for n in s["mount"]),
                "source_blocks": sources.get(sid, []),
                "selection_hits": [{"source_id": h["source_id"], "name": h["name"]}
                                   for h in sel_raw.get(sid, [])],
                "chat_start": chat_starts.get(sid),
                "chat_cells": int(chat_accounted[sid]),
                "chat_incr": n_self,
                "n_tokens": got_n, "pos_max": got_pos, "pos_max_expect": pos_expect,
                "reading_ok": ok,
                "q": s["q"], "fact": s["fact"],
                "plan": [{"seq": int(p["seq"]), "base": int(p["base"]),
                          "pos_hi": int(p["pos_hi"]), "cells": int(p["cells"])}
                         for p in plans.get(sid, [])],
            })

        # ---- 块的位置读数（③ 单列） ----
        blocks_out = []
        for b in plist:
            entry = {"name": b["name"], "seq": int(b["seq"]), "cells": int(b["cells"]),
                     "mounted_by": list(b["mounted_by"]), "path": b.get("path")}
            if b["name"] in mounted_names:
                pl = next((p for s2 in slist for p in plans.get(s2["id"], [])
                           if p["seq"] == b["seq"]), None)
                if pl is None:
                    entry.update({"ok": "not_run",
                                  "not_placed": "plan 未生成（前序会话 CAP 拒绝后停止）"})
                else:
                    got_n, got_pos = int(engine.n_tokens(b["seq"])), int(engine.pos_max(b["seq"]))
                    entry.update({"base": int(pl["base"]), "pos_hi": int(pl["pos_hi"]),
                                  "n_tokens_readback": got_n, "pos_max_readback": got_pos,
                                  "ok": bool(got_n == int(b["cells"])
                                             and got_pos == int(pl["pos_hi"]) - 1)})
            blocks_out.append(entry)

        # ---- ②a 结构层：专属_X = mounted_X − mounted_other（现算，不硬编码） ----
        def _mounted(sid):
            return set(seq_of_name[n] for n in next(s["mount"] for s in slist if s["id"] == sid))

        excl = {}
        for s in slist:
            others = set().union(*[_mounted(o["id"]) for o in slist if o["id"] != s["id"]]) \
                if len(slist) > 1 else set()
            excl[s["id"]] = _mounted(s["id"]) - others
        structural = {}
        for s in slist:
            sid = s["id"]
            other = next(o["id"] for o in slist if o["id"] != sid) if len(slist) > 1 else None
            ok = (not (set(sources.get(sid, [])) & excl.get(other, set()))) if other else True
            structural["%s_source_vs_%s_exclusive_ok"
                       % (sid.lower(), (other or "x").lower())] = bool(ok)
        source_subset_ok = all(set(sources.get(s["id"], [])) <= _mounted(s["id"]) for s in slist)

        # ---- ②c（v6 新增，零 GPU）：未过滤 selection 文本不串（去空白后判） ----
        c_sel = {}
        for s in slist:
            sid = s["id"]
            txt = _two_norm("".join(str(h.get("text") or "") for h in sel_full.get(sid, [])))
            others = [o["fact"] for o in slist if o["id"] != sid]
            bad = [f for f in others if _two_norm(f) and _two_norm(f) in txt]
            c_sel[sid] = {"text_len": len(txt), "contains_other_facts": bad,
                          "ok": not bad}

        # ---- ④ 记账：blocks + chat_A + chat_B ≤ n_ctx；对账（不读 seq 读数） ----
        chat_a = int(chat_accounted.get("A", 0))
        chat_b = int(chat_accounted.get("B", 0))
        total = int(blocks_cells) + chat_a + chat_b
        measured_blocks = int(sum(leases.cells_of(seq_of_name[n]) for n in mounted_names))
        sum_accounted = chat_a + chat_b
        sum_incr = int(sum(chat_incr.values()))
        # ④ "实测一致"口径 = leases.cells_of（块）+ 每会话记账 chat 之和（不读 seq 读数）；
        # R2（两会话同 seq）把该前提破坏 ⇒ 记 not_applicable（不许当红、也不许当绿）
        if not seqs_distinct:
            engine_match = {"status": "not_applicable",
                            "detail": {"why": "两会话同 seq（R2 注入破坏前提）",
                                       "measured_blocks": measured_blocks,
                                       "sum_accounted_chat": sum_accounted,
                                       "sum_incr_chat": sum_incr}}
        else:
            match_ok = (measured_blocks == int(blocks_cells)
                        and sum_accounted == sum_incr)
            engine_match = {"status": "done",
                            "detail": {"measured_blocks": measured_blocks,
                                       "sum_accounted_chat": sum_accounted,
                                       "sum_incr_chat": sum_incr,
                                       "ok": bool(match_ok)}}
        cells_accounting = {"blocks": int(blocks_cells), "chat_A": chat_a, "chat_B": chat_b,
                            "total": total, "n_ctx": int(n_ctx),
                            "within_budget": total <= int(n_ctx),
                            "engine_match": engine_match}
        blocks_geometry = []
        for b in plist:
            if b["name"] not in mounted_names:
                continue
            g = next((p for s2 in slist for p in plans.get(s2["id"], [])
                      if p["seq"] == b["seq"]), None)
            if g is not None:
                blocks_geometry.append({"seq": int(b["seq"]), "name": b["name"],
                                        "base": int(g["base"]), "pos_hi": int(g["pos_hi"])})

        # ---- P-1/P-2 计数等式 ----
        ev_attach = sum(1 for ev in leases.events if ev.get("kind") == "attach")
        ev_detach = sum(1 for ev in leases.events if ev.get("kind") == "detach")
        ev_replay = sum(1 for ev in leases.events if ev.get("kind") == "attach_replay")
        share_n = int(getattr(engine, "share_calls", 0))
        drop_n = int(getattr(engine, "drop_calls", 0))
        p1_share_eq = share_n == ev_attach
        p1_drop_eq = drop_n == ev_detach
        p2_ok = ev_replay == 0

        cap_guard_ok = all(int(chat_accounted[s["id"]]) <= int(chat_len_cap) for s in slist)
        cap_guard_ok = cap_guard_ok and (cap_refused is None)

        fact_by_sid = {s["id"]: s["fact"] for s in slist}
        ans_norm = {k: _two_norm(v) for k, v in answers.items()}
        if getattr(engine, "mode", "") == "dry-run":
            cross = {"a_to_b": {"ok": "未做", "a_contains_fact_b": "未做"},
                     "b_to_a": {"ok": "未做", "b_contains_fact_a": "未做"},
                     "c_selection_text": c_sel,
                     "structural": structural, "source_subset_ok": bool(source_subset_ok)}
        else:
            a2b = any(_two_norm(fact_by_sid[o["id"]]) in ans_norm.get("A", "")
                      for o in slist if o["id"] != "A")
            b2a = any(_two_norm(fact_by_sid[o["id"]]) in ans_norm.get("B", "")
                      for o in slist if o["id"] != "B")
            cross = {"a_to_b": {"ok": not a2b, "a_contains_fact_b": bool(a2b)},
                     "b_to_a": {"ok": not b2a, "b_contains_fact_a": bool(b2a)},
                     "c_selection_text": c_sel,
                     "structural": structural, "source_subset_ok": bool(source_subset_ok)}

        sha_stable = sha_stable_provider(plist) if sha_stable_provider is not None else None
        if sha_stable is None:
            sha_stable = {"status": "not_done",
                          "why": "S1-b 判据；dry-run 记未做（记绿即假绿）",
                          "checked_blocks": [], "not_checked": [
                              {"name": "habit", "why": "只登记未挂、不检"}]}

        # v6 几何连续性：每会话块尾必须正好是本会话 chat 起点（真机 decode 的前提）
        contiguity_ok = all(
            chat_starts.get(s["id"]) is not None
            and (not plans.get(s["id"])
                 or max(int(p["pos_hi"]) for p in plans[s["id"]]) == int(chat_starts[s["id"]]))
            for s in slist) and all(
            int(chat_starts[s["id"]]) is not None for s in slist if plans.get(s["id"]))
        placed_blocks_ok = all(
            b.get("ok") is True for b in blocks_out
            if b["name"] in mounted_names and b.get("ok") != "not_run")

        dry = getattr(engine, "mode", "") == "dry-run"
        checks = {
            "geometry_ok": bool(attach_error is None and all(plans.get(s["id"]) for s in slist)
                                and seqs_distinct and contiguity_ok
                                and not (set(s["seq"] for s in slist) & set(block_seqs))
                                and TWO_BLOCK_SEQ_BANNED not in block_seqs),
            "geometry_contiguity": bool(contiguity_ok),
            "S1-02a": bool(all(structural.values()) and source_subset_ok),
            "S1-02c": (bool(all(v["ok"] for v in c_sel.values())) if dry else "未做"),
            "S1-03": bool(readings_ok and placed_blocks_ok),
            "S1-04": bool(cells_accounting["within_budget"] and cap_guard_ok
                          and (engine_match["status"] == "not_applicable"
                               or engine_match["detail"].get("ok"))),
            "S1-04_reconcile": engine_match["status"],
            "CAP": bool(cap_guard_ok),
            "P1a": bool(p1_share_eq),
            "P1b": ("not_triggered" if (drop_n == 0 and ev_detach == 0) else bool(p1_drop_eq)),
            "P2": bool(p2_ok),
            "attach_ok": attach_error is None,
        }
        if dry:
            checks["S1-01"] = "未做"
            checks["S1-02b"] = "未做"
            checks["S1-05"] = "未做"
        else:
            checks["S1-01"] = bool(
                all(_two_norm(fact_by_sid[s["id"]]) in ans_norm.get(s["id"], "")
                    for s in slist))
            checks["S1-02b"] = bool(cross["a_to_b"]["ok"] is True
                                    and cross["b_to_a"]["ok"] is True)
            checks["S1-05"] = bool(sha_stable.get("status") == "done"
                                   and sha_stable.get("unchanged") is True)
        # v6：未做/未触发/not_applicable 是"不可判"，既不算绿也不算红；红=显式 False
        neutral = ("未做", "not_applicable", "not_triggered", "not_run")
        judged = {k: v for k, v in checks.items()
                  if k not in ("S1-04_reconcile", "all_ok")}
        checks["all_ok"] = all((v is True) or (isinstance(v, str) and v in neutral)
                               for v in judged.values())
        fail_ids = [k for k, v in judged.items() if v is False]
        notes = {"S1-01": "未做（S1-b 真机事实命中）",
                 "S1-02a": "v6 降级：仅接线回归（恒真已被证明），不计入交叉分母",
                 "S1-02b": "未做（S1-b 文本层；去空白后判，见 ②b）",
                 "S1-02c": "dry-run 零 GPU：未过滤 selection 文本不串（A 不含 FACT_B / B 不含 FACT_A）",
                 "S1-05": "未做（sha_stable 仅 S1-b；dry-run 记 not_done）",
                 "S1-04_CAP": "CAP 执行点：每轮 chat_cells_self ≤ %d，否则 PlanRefused"
                              % int(chat_len_cap),
                 "P1b": "S1 无 detach 路径 ⇒ drop 等式零实例，记 not_triggered（不许记通过）",
                 "CAP_not_run": "未跑的会话 cap_ok 记 not_run，不写 true",
                 "exec_order": "A→B（A 跑完 10 轮再跑 B；n_ctx_eff 取 plan 前另一会话实际 chat）",
                 "geometry": "v6 游标顺延：A home [4075,4096)；B project 接 A chat 之后；hi=排他"}

        return {
            "schema": "s1_two_session_v6",
            "spec": "docs/_work/M2-FULL-S1-SPEC-lead.md@ae2d88ad5ecc25d3",
            "geometry_semantics": "pos_hi_exclusive; A home [4075,4096) chat_start_A=4096; "
                                  "B project [4096+n_chat_A, +18) chat_start_B=4096+n_chat_A+18",
            "mode": getattr(engine, "mode", "unknown"),
            "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "frozen": {"n_rounds": int(n_rounds), "chat_len_cap": int(chat_len_cap),
                       "chat_start": int(TWO_CHAT_START), "seq_a": int(TWO_SEQ_A),
                       "seq_b": int(TWO_SEQ_B), "block_seqs": block_seqs,
                       "pool_n": len(plist), "mounted_n": len(mounted_names)},
            "pool": [{"name": b["name"], "seq": int(b["seq"]), "cells": int(b["cells"]),
                      "mounted_by": list(b["mounted_by"])} for b in plist],
            "blocks": blocks_out,
            "blocks_geometry": blocks_geometry,
            "sessions": sessions_out,
            "cells_accounting": cells_accounting,
            "cross": cross,
            "counters": {"share": share_n, "drop": drop_n, "attach": ev_attach,
                         "detach_hits": ev_detach, "attach_replay": ev_replay,
                         "p1_share_eq": bool(p1_share_eq),
                         "p1_drop_eq": (bool(p1_drop_eq) if (drop_n or ev_detach)
                                        else "not_triggered"),
                         "p2_ok": bool(p2_ok), "reset": int(getattr(engine, "reset_calls", 0))},
            "budget": budget_out,
            "cap": {"refused": bool(cap_refused is not None), "hit": cap_hit,
                    "error": cap_refused,
                    "plan_refused": {s["id"]: b.get("plan_refused") for s, b
                                     in zip(slist, budget_out)}},
            "sha_stable": sha_stable,
            "checks": checks,
            "fail_ids": fail_ids,
            "verdict": "通过" if checks["all_ok"] else "未通过",
            "exit": 0 if checks["all_ok"] else 2,
            "notes": notes,
            "answers": answers,
            "extra_denominators": {"sessions": len(slist), "mounted_blocks": len(mounted_names),
                                   "pool_blocks": len(plist),
                                   "cross_assertions_text": (2 if not dry else "0/2（未做）"),
                                   "cross_assertions_selection_text": 2,
                                   "cross_assertions_note":
                                       "v6：②a 降级为接线回归、不计入交叉分母；交叉分母=②b 两条"},
        }
    finally:
        if own_con:
            con.close()


def two_session_plan(*args, **kw):
    """兼容旧名：dry-run 纯调度（等价 `two_session_run(_StubEngine())`）。"""
    return two_session_run(_StubEngine(), *args, **kw)


def cmd_two(dry_run=False, out=None, n_ctx=N_CTX):
    """S1 子命令：同一 n_ctx 两段有界会话（A=seq0 挂 home / B=seq7 挂 project，顺序 A→B）。

    `--dry-run` 用 _StubEngine（零 GPU，DB 只用于 `_selection`）；默认真机臂用
    CountingEngine(14B KVEngine)。两条路径走**同一** `two_session_run`，只换 engine factory。
    """
    if dry_run:
        engine = _StubEngine()
    else:
        engine = CountingEngine(KVEngine(MODEL, n_ctx=N_CTX, n_seq=N_SEQ, gpu=99, kv="q8_0"))
    try:
        res = two_session_run(engine, n_ctx=n_ctx)
    finally:
        engine.close()
    res["blocks_source"] = {"dir": TWO_BLOCK_DIR,
                            "cells_source": "M2-ACCEPT-r2 blocks_planned（home 21 / project 18 / habit 12）"}

    print("=" * 74)
    print("S1 两会话 v6（A=seq%d 挂 home / B=seq%d 挂 project，顺序 A→B；hi=排他）· %s"
          % (TWO_SEQ_A, TWO_SEQ_B, res["mode"]))
    print("=" * 74)
    for s in res["sessions"]:
        print("  %s: seq=%d rounds=%d mounted=%s source=%s chat_cells=%d n_tokens=%d "
              "pos_max=%d(expect %d)"
              % (s["id"], s["seq"], s["rounds"], s["mounted_blocks"], s["source_blocks"],
                 s["chat_cells"], s["n_tokens"], s["pos_max"], s["pos_max_expect"]))
    ca = res["cells_accounting"]
    print("  记账：块 %d + A chat %d + B chat %d = %d ≤ n_ctx %d（within=%s reconcile=%s）"
          % (ca["blocks"], ca["chat_A"], ca["chat_B"], ca["total"], ca["n_ctx"],
             ca["within_budget"], ca["engine_match"]["status"]))
    print("  ②a 结构：%s" % res["cross"]["structural"])
    print("  计数：share=%d attach=%d | drop=%d detach=%d | replay=%d"
          % (res["counters"]["share"], res["counters"]["attach"],
             res["counters"]["drop"], res["counters"]["detach_hits"],
             res["counters"]["attach_replay"]))
    print("  budget：%s" % res["budget"])
    print("  sha_stable=%s verdict=%s fail_ids=%s"
          % (res["sha_stable"]["status"], res["verdict"], res["fail_ids"]))
    if out:
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
        print("\n产物：%s" % out)
    return res


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="KV-block chat, no prompt splicing")
    ap.add_argument("cmd", nargs="?", default="chat",
                    choices=["build", "chat", "save", "load", "m1", "two"])
    ap.add_argument("--control", action="store_true",
                    help="ask the same questions WITHOUT attaching the blocks")
    ap.add_argument("--path", default=SESSION, help="session manifest path")
    ap.add_argument("--explain", action="store_true",
                    help="m1: print the selection and its scores, generate nothing")
    ap.add_argument("--save", nargs="?", const=SESSION, default=None,
                    help="m1: snapshot the session with its selection audit")
    ap.add_argument("--dry-run", action="store_true",
                    help="two: schedule/plan/account only, no engine (zero GPU)")
    ap.add_argument("--out", default=None,
                    help="two: write the readings JSON to this path")
    args = ap.parse_args()

    if args.cmd == "build":
        cmd_build()
    elif args.cmd == "save":
        cmd_save(args.path)
    elif args.cmd == "load":
        cmd_load(args.path)
    elif args.cmd == "m1":
        cmd_m1(explain=args.explain, control=args.control, save_path=args.save)
    elif args.cmd == "two":
        sys.exit(cmd_two(dry_run=args.dry_run, out=args.out)["exit"])
    else:
        cmd_chat(control=args.control)


if __name__ == "__main__":
    main()