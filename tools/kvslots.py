# -*- coding: utf-8 -*-
"""kvslots.py -- Python binding over llama.cpp's per-sequence KV state API.

Design constraint: no prompt concatenation, ever. Memory is woken up by loading
its *binary KV block* into the engine, not by pasting text into a prompt.

Three state-level mechanisms from llama.h are used:

  llama_state_seq_save_file   dump one sequence's KV (+ its tokens) to a file
  llama_state_seq_load_file   load such a file back into ANY sequence id
  llama_memory_seq_cp         share src's KV cells with dst (refcount only)

The C side lives in tools/kvshim.cpp and exposes a flat ABI, so nothing here has
to guess a struct layout; every argument is int / char*.

IMPORTANT -- positions are a shared resource, not per-sequence:
    The KV pool is unified, so two sequences that put *different* tokens at the
    same position collide. Each conversation/memory block therefore gets its own
    position base (stride 256 here), allocated at write time and carried inside
    the saved file. That base is part of the memory's identity: load the file
    anywhere and its positions come back unchanged.

Run:
    python tools/kvslots.py
    python tools/kvslots.py --gpu 99 --kv q8_0 --ctx 8192 --window 2048 --slots 3

What the demo proves, in order:
  1. three conversations reside at once in three sequences (3 VRAM slots)
  2. each one's KV is dumped to a binary file; the accounting is exact
  3. after wiping everything the engine has forgotten; loading the file back into
     a *different* sequence id makes it remember again -- no text involved
  4. a 4th conversation evicts the least recently used slot (save-then-reset)
  5. a memory block is mounted as its own sequence and shared into a chat with
     seq_cp, so the chat answers from KV that was never in its prompt
"""

import argparse
import ctypes
import os
import sys
import time

# The DLL links libgcc/libstdc++ statically, but ggml-cpu may still pull in libomp.
_LLVM_BIN = (r"C:\Users\lezige\AppData\Local\Microsoft\WinGet\Packages"
             r"\MartinStorsjo.LLVM-MinGW.MSVCRT_Microsoft.Winget.Source_8wekyb3d8bbwe"
             r"\llvm-mingw-20260826-msvcrt-x86_64\bin")
if os.path.isdir(_LLVM_BIN):
    try:
        os.add_dll_directory(_LLVM_BIN)
    except (AttributeError, OSError):
        pass

ASK_SUFFIX = "\n答："      # without this the distilled model rambles instead of answering


def turn(q):
    """Wrap a question as a new turn so the model answers instead of continuing."""
    return "\n问：" + q + ASK_SUFFIX


class KVEngine:
    """Thin owner of a llama context that speaks sequence ids, not prompts."""

    def __init__(self, model, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0", dll=None):
        here = os.path.dirname(os.path.abspath(__file__))
        suffix = "_vk" if gpu else ""
        path = dll or os.path.join(here, "kvshim%s.dll" % suffix)
        if not os.path.exists(path):
            raise FileNotFoundError("%s (run build_tools.ps1 -Gpu -Dll -Only kvshim)" % path)

        self.lib = ctypes.WinDLL(path)
        L = self.lib
        vp, ci, cl, cp = ctypes.c_void_p, ctypes.c_int, ctypes.c_longlong, ctypes.c_char_p

        L.kvshim_init_log.restype = None
        L.kvshim_free_log.restype = None
        L.kvshim_open.argtypes = [cp, ci, ci, ci, ci]
        L.kvshim_open.restype = vp
        L.kvshim_close.argtypes = [vp]
        L.kvshim_bytes_per_token.argtypes = [vp]
        L.kvshim_bytes_per_token.restype = cl
        L.kvshim_pool_bytes.argtypes = [vp]
        L.kvshim_pool_bytes.restype = cl
        L.kvshim_n_ctx.argtypes = [vp]
        L.kvshim_n_ctx.restype = ci
        L.kvshim_seq_bytes.argtypes = [vp, ci]
        L.kvshim_seq_bytes.restype = cl
        L.kvshim_n_tokens.argtypes = [vp, ci]
        L.kvshim_n_tokens.restype = ci
        L.kvshim_pos_max.argtypes = [vp, ci]
        L.kvshim_pos_max.restype = ci
        L.kvshim_reset.argtypes = [vp, ci]
        L.kvshim_write.argtypes = [vp, ci, cp, ci]
        L.kvshim_write.restype = ci
        L.kvshim_write_at.argtypes = [vp, ci, cp, ci, ci]
        L.kvshim_write_at.restype = ci
        L.kvshim_ask.argtypes = [vp, ci, cp, ci, ctypes.c_void_p, ci]
        L.kvshim_ask.restype = ci
        L.kvshim_ask_at.argtypes = [vp, ci, cp, ci, ci, ctypes.c_void_p, ci]
        L.kvshim_ask_at.restype = ci
        L.kvshim_save.argtypes = [vp, ci, cp]
        L.kvshim_save.restype = cl
        L.kvshim_load.argtypes = [vp, ci, cp]
        L.kvshim_load.restype = ci
        L.kvshim_seq_cp.argtypes = [vp, ci, ci, ci, ci]
        L.kvshim_seq_rm.argtypes = [vp, ci, ci, ci]
        L.kvshim_repos.argtypes = [vp, ci, ci, ci, ci]
        L.kvshim_repos_local.argtypes = [vp, ci, ci, ci, ci]
        L.kvshim_repos_local.restype = ci
        L.kvshim_can_shift.argtypes = [vp]
        L.kvshim_can_shift.restype = ci

        L.kvshim_init_log()
        self.h = L.kvshim_open(model.encode("utf-8"), n_ctx, n_seq, gpu,
                               1 if kv == "q8_0" else 0)
        if not self.h:
            raise RuntimeError("kvshim_open failed (model=%s)" % model)
        self.n_seq = n_seq
        self.n_ctx = n_ctx

    # -- accounting -------------------------------------------------------

    def bytes_per_token(self):
        return self.lib.kvshim_bytes_per_token(self.h)

    def pool_bytes(self):
        return self.lib.kvshim_pool_bytes(self.h)

    def seq_bytes(self, seq):
        return self.lib.kvshim_seq_bytes(self.h, seq)

    def n_tokens(self, seq):
        return self.lib.kvshim_n_tokens(self.h, seq)

    def pos_max(self, seq):
        return self.lib.kvshim_pos_max(self.h, seq)

    # -- sequence ops -----------------------------------------------------

    def reset(self, seq):
        self.lib.kvshim_reset(self.h, seq)

    def write(self, seq, text, add_bos=True):
        return self.lib.kvshim_write(self.h, seq, text.encode("utf-8"), 1 if add_bos else 0)

    def write_at(self, seq, text, pos, add_bos=True):
        return self.lib.kvshim_write_at(self.h, seq, text.encode("utf-8"), pos, 1 if add_bos else 0)

    def ask(self, seq, text, n_predict=32, pos=None):
        buf = ctypes.create_string_buffer(8192)
        t = turn(text).encode("utf-8")
        if pos is None:
            n = self.lib.kvshim_ask(self.h, seq, t, n_predict, buf, 8192)
        else:
            n = self.lib.kvshim_ask_at(self.h, seq, t, pos, n_predict, buf, 8192)
        return "" if n < 0 else buf.value.decode("utf-8", "replace")

    def save(self, seq, path):
        return self.lib.kvshim_save(self.h, seq, path.encode("utf-8"))

    def load(self, seq, path):
        return self.lib.kvshim_load(self.h, seq, path.encode("utf-8"))

    def load_strict(self, seq, path):
        """Load, and treat the engine's refusal as an error instead of silently
        continuing with an empty sequence. The engine refuses when the state file was
        written by another model / rope config / kv type (it compares n_rot_k), which is
        exactly the case that must never be mistaken for "loaded but empty"."""
        n = self.lib.kvshim_load(self.h, seq, path.encode("utf-8"))
        if n < 0:
            raise RuntimeError(
                "kvshim_load refused %s -- incompatible state (model, rope, kv type or "
                "n_rot_k differs from when the block was written)" % path)
        return n

    def share(self, src, dst, p0=0, p1=-1):
        self.lib.kvshim_seq_cp(self.h, src, dst, p0, p1)

    def drop(self, seq, p0=0, p1=-1):
        self.lib.kvshim_seq_rm(self.h, seq, p0, p1)

    def repos(self, seq, delta, p0=0, p1=-1):
        """Shift positions by delta. The rope compensation is applied lazily by the
        next decode (engine-side build_graph_shift)."""
        self.lib.kvshim_repos(self.h, seq, p0, p1, delta)

    def can_shift(self):
        return self.lib.kvshim_can_shift(self.h) != 0

    def repos_local(self, seq, delta, p0=0, p1=-1):
        """Rotate ONLY the cells that move (no whole-tensor rewrite, no pending shift).
        Returns the number of cells touched."""
        return self.lib.kvshim_repos_local(self.h, seq, p0, p1, delta)

    def close(self):
        if getattr(self, "h", None):
            self.lib.kvshim_close(self.h)
            self.h = None
        self.lib.kvshim_free_log()


class PositionAllocator:
    """Hands out disjoint position bases for memory blocks."""

    def __init__(self, stride, limit):
        self.stride = stride
        self.limit = limit
        self.next = 0

    def take(self):
        if (self.next + 1) * self.stride > self.limit:
            raise RuntimeError("out of position space")
        base = self.next * self.stride
        self.next += 1
        return base


class SlotPool:
    """`size` KV slots, LRU, one file per conversation. A slot is a sequence id."""

    def __init__(self, eng, size, dirpath, alloc):
        self.eng = eng
        self.size = size
        self.dir = dirpath
        self.alloc = alloc
        os.makedirs(dirpath, exist_ok=True)
        self.slots = {}          # seq -> conv id
        self.last_used = {}      # seq -> tick
        self.base = {}           # conv id -> position base
        self.tick = 0
        self.hits = 0
        self.misses = 0

    def _path(self, cid):
        return os.path.join(self.dir, "conv_%s.kvmem" % cid)

    def _free_slot(self):
        for s in range(self.size):
            if s not in self.slots:
                return s
        victim = min(self.slots, key=lambda s: self.last_used[s])
        cid = self.slots.pop(victim)
        n = self.eng.save(victim, self._path(cid))
        self.eng.reset(victim)
        print("    [evict] slot %d (conv %s, %d B) -> %s"
              % (victim, cid, n, os.path.basename(self._path(cid))))
        return victim

    def touch(self, cid, text):
        for seq, c in self.slots.items():
            if c == cid:
                self.tick += 1
                self.last_used[seq] = self.tick
                self.hits += 1
                return seq
        self.misses += 1
        seq = self._free_slot()
        path = self._path(cid)
        if os.path.exists(path):
            n = self.eng.load(seq, path)
            print("    [wake ] conv %s -> slot %d, %d tokens, pos_max=%d"
                  % (cid, seq, n, self.eng.pos_max(seq)))
        else:
            base = self.base.setdefault(cid, self.alloc.take())
            n = self.eng.write_at(seq, text, base)
            print("    [write] conv %s -> slot %d, %d tokens at pos %d..%d"
                  % (cid, seq, n, base, base + n - 1))
        self.slots[seq] = cid
        self.tick += 1
        self.last_used[seq] = self.tick
        return seq

    def ask(self, cid, q, text, n_predict=24):
        return self.eng.ask(self.touch(cid, text), q, n_predict)


def mb(n):
    return n / (1024.0 * 1024.0)


def first_line(s):
    s = s.strip()
    return s.splitlines()[0][:56] if s else "(empty)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=r"D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf")
    ap.add_argument("--ctx", type=int, default=8192)
    ap.add_argument("--gpu", type=int, default=99)
    ap.add_argument("--kv", default="q8_0", choices=["q8_0", "f16"])
    ap.add_argument("--window", type=int, default=2048, help="position where the chat starts")
    ap.add_argument("--slots", type=int, default=3)
    ap.add_argument("--stride", type=int, default=256)
    args = ap.parse_args()

    W, NSEQ = args.window, args.slots + 12
    alloc = PositionAllocator(args.stride, args.ctx)

    t0 = time.perf_counter()
    eng = KVEngine(args.model, n_ctx=args.ctx, n_seq=NSEQ, gpu=args.gpu, kv=args.kv)
    print("engine up in %.1fs  ctx=%d  seq_max=%d  kv=%s  window=%d"
          % (time.perf_counter() - t0, eng.n_ctx, NSEQ, args.kv, W))
    bpt = eng.bytes_per_token()
    print("KV per token   : %d B" % bpt)
    print("KV pool total  : %.1f MiB  (%d ctx * %d B)" % (mb(eng.pool_bytes()), args.ctx, bpt))
    print()

    convs = {
        "A": ("我的工号是 A-4417，我住在杭州市西湖区。", "我的工号是多少？", "A-4417"),
        "B": ("我养了一只猫叫年糕，它今年三岁。", "我养的猫叫什么名字？", "年糕"),
        "C": ("我每周三下午两点在 B 栋 3 层 302 会议室开例会。", "我的例会在哪个会议室？", "302"),
    }
    bases = {}
    for i, cid in enumerate(convs):
        bases[cid] = alloc.take()

    print("=" * 74)
    print("1) three conversations, three sequences, all resident at once")
    print("=" * 74)
    for i, (cid, (text, q, expect)) in enumerate(convs.items()):
        n = eng.write_at(i, text, bases[cid])
        kv = eng.seq_bytes(i)          # measure the memory itself, before the Q&A
        ans = eng.ask(i, q, 24)
        ok = expect in ans
        print("  seq %d  conv %s  %3d tok  pos %4d..%4d  %6.1f KiB  %s  %s"
              % (i, cid, n, bases[cid], bases[cid] + n - 1,
                 kv / 1024.0, "OK  " if ok else "MISS", first_line(ans)))
    total = sum(eng.seq_bytes(s) for s in range(args.slots))
    print("  pool now holds %.1f KiB of dialogue (%.2f%% of the %.1f MiB KV pool);"
          % (total / 1024.0, 100.0 * total / eng.pool_bytes(), mb(eng.pool_bytes())))
    print("  1k tokens of memory costs %.1f MiB, so this pool is worth %d k tokens"
          % (1024 * bpt / (1024.0 * 1024.0), args.ctx // 1024))
    print()

    qdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quality")
    os.makedirs(qdir, exist_ok=True)

    print("=" * 74)
    print("2) dump every slot to a binary file -- the file IS the memory")
    print("=" * 74)
    for i, cid in enumerate(convs):
        path = os.path.join(qdir, "conv_%s.kvmem" % cid)
        ts = time.perf_counter()
        n = eng.save(i, path)
        dt = time.perf_counter() - ts
        print("  seq %d -> %-16s %9d B (%.1f KiB)  %.2f ms"
              % (i, os.path.basename(path), n, n / 1024.0, dt * 1000))
    print()

    print("=" * 74)
    print("3) wipe everything, then wake one up in a DIFFERENT sequence id")
    print("=" * 74)
    for i in range(args.slots):
        eng.reset(i)
    print("  after reset: seq 0 has %d tokens, pos_max=%d" % (eng.n_tokens(0), eng.pos_max(0)))
    cold = eng.ask(0, convs["A"][1], 24)
    print("  cold ask on empty seq 0 : %s" % first_line(cold))

    tag_seq = args.slots
    path = os.path.join(qdir, "conv_A.kvmem")
    ts = time.perf_counter()
    n = eng.load(tag_seq, path)
    dt = time.perf_counter() - ts
    print("  loaded conv A into seq %d: %d tokens, pos %d..%d, %.1f KiB, %.2f ms"
          % (tag_seq, n, eng.pos_max(tag_seq) - n + 1, eng.pos_max(tag_seq),
             eng.seq_bytes(tag_seq) / 1024.0, dt * 1000))
    ans = eng.ask(tag_seq, convs["A"][1], 24)
    print("  %s  Q:%s -> %s" % ("OK  " if convs["A"][2] in ans else "MISS",
                                convs["A"][1], first_line(ans)))
    print()

    print("=" * 74)
    print("4) a 4th conversation evicts the LRU slot (save-then-reset)")
    print("=" * 74)
    pool = SlotPool(eng, args.slots, os.path.join(qdir, "slots"), alloc)
    five = dict(convs)
    five["D"] = ("我下个月要去趟青岛出差。", "我下个月要去哪里？", "青岛")
    for cid in ["A", "B", "C"]:
        pool.touch(cid, five[cid][0])
    pool.last_used[0] = -1          # force slot 0 to be the victim
    pool.touch("D", five["D"][0])
    print("  resident: %s" % {s: c for s, c in sorted(pool.slots.items())})
    for cid in ["A", "D"]:
        text, q, expect = five[cid]
        ans = pool.ask(cid, q, text)
        print("  conv %s  %s  Q:%s -> %s" % (cid, "OK  " if expect in ans else "MISS",
                                             q, first_line(ans)))
    print("  slot hits/misses: %d/%d" % (pool.hits, pool.misses))
    print()

    print("=" * 74)
    print("5) memory mounted as its OWN sequence, shared into the chat via seq_cp")
    print("=" * 74)
    mem_seq, chat_seq = args.slots + 1, args.slots + 2
    mem_base = 2048
    mem_text = "林知远的手机尾号是 9031，他住在杭州市西湖区。"
    q = "林知远的手机尾号是多少？"

    eng.reset(chat_seq)
    bare = eng.ask(chat_seq, q, 24)
    print("  chat without memory : %s" % first_line(bare))

    n = eng.write_at(mem_seq, mem_text, mem_base)
    print("  memory block seq %d : %d tokens at pos %d..%d, %.1f KiB"
          % (mem_seq, n, mem_base, mem_base + n - 1, eng.seq_bytes(mem_seq) / 1024.0))

    # The chat must sit *directly above* the block: causal attention only looks
    # backwards, and a positional gap buys nothing (README-HANDOFF-2.md section 6.1).
    chat_pos = mem_base + n
    eng.reset(chat_seq)
    eng.share(mem_seq, chat_seq)
    print("  seq_cp(%d -> %d): chat now also references positions %d..%d (refcount only)"
          % (mem_seq, chat_seq, mem_base, mem_base + n - 1))
    print("  chat prompt starts at %d  ->  distance to memory = %d tokens"
          % (chat_pos, chat_pos - mem_base))
    ans = eng.ask(chat_seq, q, 24, pos=chat_pos)
    print("  %s  Q:%s -> %s" % ("OK  " if "9031" in ans else "MISS", q, first_line(ans)))

    # 5b) does a positional gap between the memory and the chat break it?
    # Section 6.1 says recall decays with distance; this checks something sharper:
    # whether a *hole* in the position range is tolerated at all.
    print("  gap sweep (same memory, same question, chat pushed further up):")
    for k, gap in enumerate([0, 1, 8, 64, 700]):
        s = args.slots + 3 + k
        eng.reset(s)
        eng.share(mem_seq, s)
        g = eng.ask(s, q, 24, pos=chat_pos + gap)
        print("    +%-4d pos %5d : %s" % (gap, chat_pos + gap, first_line(g)))

    # 6) option (b): reposition a block by rope-shifting its cells.
    # The decisive question is whether a shifted block is *identical* to one that
    # was decoded natively at that base. If yes, blocks are freely placeable and
    # swapping them costs one graph run instead of a chat re-prefill.
    print()
    print("=" * 74)
    print("6) reposition (b): shift a block +%d, compare against native encoding" % 4096)
    print("=" * 74)
    print("  cache can_shift = %s" % eng.can_shift())
    BASE = 4096
    blk = "林知远的手机尾号是 9031，他住在杭州市西湖区。"
    qb = "林知远的手机尾号是多少？"

    s_nat, s_mov = args.slots + 10, args.slots + 11
    n_nat = eng.write_at(s_nat, blk, BASE)
    t = time.perf_counter()
    a_nat = eng.ask(s_nat, qb, 24)
    t_nat = time.perf_counter() - t
    p_nat = os.path.join(qdir, "blk_native.kvmem")
    eng.save(s_nat, p_nat)

    n_mov = eng.write_at(s_mov, blk, 0)
    t = time.perf_counter()
    eng.repos(s_mov, BASE)              # lazy: applied by the next decode
    a_mov = eng.ask(s_mov, qb, 24)      # this decode runs build_graph_shift
    dt = time.perf_counter() - t
    p_mov = os.path.join(qdir, "blk_moved.kvmem")
    eng.save(s_mov, p_mov)              # snapshot BEFORE the repeat ask

    t = time.perf_counter()
    eng.ask(s_mov, qb, 24)              # same ask again, no pending shift
    t_again = time.perf_counter() - t

    print("  native : %d tok at pos %d..%d" % (n_nat, BASE, BASE + n_nat - 1))
    print("  moved  : %d tok, encoded at 0, shifted to %d..%d" % (n_mov, BASE, BASE + n_mov - 1))
    print("  ask cost: native %.0f ms | shifted %.0f ms | repeat %.0f ms  => shift ~%.0f ms"
          % (t_nat * 1000, dt * 1000, t_again * 1000, (dt - t_again) * 1000))
    print("  answers equal : %s" % ("YES" if a_nat.strip() == a_mov.strip() else "NO"))
    print("    native: %s" % first_line(a_nat))
    print("    moved : %s" % first_line(a_mov))

    # Byte-level check: the saved state holds positions + K/V. Equal positions are
    # a given; any difference in the payload is quantisation drift from the
    # dequant -> rope -> requant round trip in build_rope_shift.
    with open(p_nat, "rb") as f1, open(p_mov, "rb") as f2:
        b1, b2 = f1.read(), f2.read()
    if len(b1) == len(b2):
        diff = sum(1 for x, y in zip(b1, b2) if x != y)
        print("  state bytes: %d, differing %d (%.2f%%)"
              % (len(b1), diff, 100.0 * diff / len(b1)))
    else:
        print("  state bytes differ in length: %d vs %d" % (len(b1), len(b2)))

    eng.close()
    print()
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())