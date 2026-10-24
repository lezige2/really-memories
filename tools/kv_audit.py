# -*- coding: utf-8 -*-
"""kv_audit.py -- check the assumptions the architecture rests on.

The STATUS report leans on four claims that were never measured directly. This tool
measures them, on the real engine, and prints a verdict for each:

  drift  Does moving the same block N times (quantize -> dequantize -> rotate ->
         quantize, per move) degrade its K? A block is q8_0 in the cache, so every
         move is a lossy round trip. The "0 bytes" isolation test says nothing about
         this: it only ever moves pristine reloads and never re-moves one block.

         Method: put the block at position 0, save the state file (byte A), do N
         round trips of (+step, -step) so it lands back at 0, save again (byte B),
         then compare A and B byte for byte. Same tokens, same positions, so any
         difference is pure numeric drift. Then ask the question anyway: drift that
         is invisible in the answer is still worth knowing about, and drift that
         is visible is a blocker.

  rss    Does loading/moving/dropping 50 blocks leak host memory? Samples the
         process working set (psapi) every 10 cycles and reports the trend.

Usage:
  python tools/kv_audit.py drift --n 100 --step 64
  python tools/kv_audit.py rss   --cycles 50
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kvslots import KVEngine  # noqa: E402

MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
BLOCK = r"D:\llama-mem\kvmem\blocks\profile.kvmem"
Q = "我的工号是多少？"
CHAT = 4096


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


_K32 = ctypes.WinDLL("kernel32", use_last_error=True)
_GET_WS = getattr(_K32, "K32GetProcessMemoryInfo", None)
if _GET_WS is None:                                   # very old Windows
    _GET_WS = ctypes.WinDLL("psapi").GetProcessMemoryInfo
_GET_WS.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wt.DWORD]
_GET_WS.restype = wt.BOOL


def rss_mib():
    """Working set of this process, in MiB, or raise -- a silent -1 hides leaks."""
    pmc = PROCESS_MEMORY_COUNTERS()
    pmc.cb = ctypes.sizeof(pmc)
    if not _GET_WS(_K32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
        raise OSError("K32GetProcessMemoryInfo failed (err=%d)"
                      % ctypes.get_last_error())
    return pmc.WorkingSetSize / (1024.0 * 1024.0)


def diff_bytes(a, b):
    """(differing bytes, max |delta|, first differing offset)."""
    n = min(len(a), len(b))
    n_diff = 0
    worst = 0
    first = -1
    for i in range(n):
        d = a[i] - b[i]
        if d:
            n_diff += 1
            if first < 0:
                first = i
            if abs(d) > worst:
                worst = abs(d)
    return n_diff, worst, first


def cmd_drift(a):
    eng = KVEngine(MODEL, gpu=99, kv=a.kv)
    try:
        eng.reset(1)
        eng.load(1, BLOCK)
        n = eng.n_tokens(1)
        print("block: %d tokens, %d B/token, pool %.1f MiB"
              % (n, eng.bytes_per_token(), eng.pool_bytes() / 1048576.0))

        tmp_a = os.path.join(HERE, "quality", "_drift_a.kvmem")
        tmp_b = os.path.join(HERE, "quality", "_drift_b.kvmem")

        # A: pristine, at position 0..n-1
        eng.save(1, tmp_a)

        # N round trips that return the block to exactly where it started
        for i in range(a.n):
            eng.repos_local(1, +a.step)
            eng.repos_local(1, -a.step)
        print("round trips: %d x (+%d, -%d)   pos now %d..%d"
              % (a.n, a.step, a.step, eng.pos_max(1) - n + 1, eng.pos_max(1)))

        eng.save(1, tmp_b)

        A = open(tmp_a, "rb").read()
        B = open(tmp_b, "rb").read()
        n_diff, worst, first = diff_bytes(A, B)
        print()
        print("state file A (pristine) : %d B" % len(A))
        print("state file B (%d trips) : %d B" % (a.n, len(B)))
        if n_diff == 0:
            print("byte drift             : 0 (bit-identical)")
        else:
            print("byte drift             : %d B differ (%.4f%%), max |delta| %d, "
                  "first at offset %d" % (n_diff, 100.0 * n_diff / len(A), worst, first))

        # does the drift reach the product? place it and ask
        eng.repos_local(1, CHAT - n)
        eng.share(1, 0)
        ans = eng.ask(0, Q, n_predict=24, pos=CHAT)
        print()
        print("after %d trips, %s -> %s"
              % (a.n, Q, ans.strip().splitlines()[0] if ans.strip() else "(empty)"))
        ok = "A-4417" in ans
        print("verdict: %s" % ("answer still correct" if ok else "ANSWER DEGRADED"))

        for p in (tmp_a, tmp_b):
            try:
                os.remove(p)
            except OSError:
                pass
        return 0 if ok else 1
    finally:
        eng.close()


def cmd_rss(a):
    eng = KVEngine(MODEL, gpu=99, kv=a.kv)
    try:
        eng.reset(1)
        eng.load(1, BLOCK)
        n = eng.n_tokens(1)
        samples = []
        base = rss_mib()
        print("start RSS %.1f MiB   block %d tokens" % (base, n))

        for c in range(1, a.cycles + 1):
            eng.reset(1)
            eng.load(1, BLOCK)
            eng.repos_local(1, CHAT - n)
            eng.share(1, 0)          # what the product does: attach to the dialogue
            eng.drop(0)              # ...and detach again
            if c % 10 == 0 or c == 1:
                r = rss_mib()
                samples.append((c, r))
                print("  cycle %3d  RSS %8.1f MiB  (%.2f over start)"
                      % (c, r, r - base))

        first = samples[0][1]
        last = samples[-1][1]
        grow = last - first
        print()
        print("cycles %d   RSS %.1f -> %.1f MiB   growth %.2f MiB (%.2f%% of start)"
              % (a.cycles, first, last, grow, 100.0 * grow / max(1e-9, base)))
        # a leak of one 1.5 MiB block per cycle over 50 cycles would be ~75 MiB
        verdict = "no monotonic growth" if grow < 8.0 else "SUSPICIOUS: investigate"
        print("verdict: %s" % verdict)
        return 0 if grow < 8.0 else 1
    finally:
        eng.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["drift", "rss"])
    ap.add_argument("--kv", default="q8_0")
    ap.add_argument("--n", type=int, default=100, help="drift: number of round trips")
    ap.add_argument("--step", type=int, default=64, help="drift: round-trip distance")
    ap.add_argument("--cycles", type=int, default=50, help="rss: attach/detach cycles")
    a = ap.parse_args()
    return cmd_drift(a) if a.cmd == "drift" else cmd_rss(a)


if __name__ == "__main__":
    sys.exit(main())