# -*- coding: utf-8 -*-
"""K1 pure-file save-loop microbenchmark.  NO Vulkan, NO model, NO signals.

Replicates the K1 child save loop exactly:
  80 x 65536-byte writes -> flush -> os.fsync -> _durable_replace (MoveFileExW,
  MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)

Two arms:
  fresh       target absent before round 1; first write creates it (cold/scan-prone)
  precreated  target copied and read once before timing (already existing/scanned)

10 rounds per arm, same target path overwritten each round.  Every chunk gets a
perf_counter measurement; slow chunks, >1 s events, first stall round and the
flush/fsync/replace phases are recorded.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "kvmem/m2_visibility/m5/out"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
from session_state import _durable_replace  # noqa: E402

SRC = OUT / "M5-KILL-before.kvmem"
CHUNK = 65536
ROUNDS = 10
ART = OUT / "M5-K1-IO-MICROBENCH.json"


def sha16_bytes(b):
    return hashlib.sha256(b).hexdigest()[:16]


def sha16_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def header_ntokens(path):
    b = open(path, "rb").read(12)
    return int.from_bytes(b[8:12], "little")


def ensure_source():
    if not SRC.exists():
        raise SystemExit("source missing: %s" % SRC)
    b = SRC.read_bytes()
    if len(b) != 5224388:
        raise SystemExit("source bytes changed: %d" % len(b))
    if sha16_bytes(b) != "3b046c8ee3fb3b53":
        raise SystemExit("source sha changed")
    return b


def precreate(target, data):
    t0 = time.perf_counter()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, target)
    with open(target, "rb+") as f:
        f.flush()
        os.fsync(f.fileno())
    warm = target.read_bytes()  # force the file through the cache/scan path
    time.sleep(2.0)
    return {"precreate_s": round(time.perf_counter() - t0, 3),
            "warm_read_bytes": len(warm), "target_sha16": sha16_bytes(warm)}


def one_round(target, data, rnd, target_was_preexisting):
    tmp = str(target) + ".tmp-%d-%d" % (os.getpid(), rnd)
    try:
        os.unlink(tmp)
    except FileNotFoundError:
        pass
    round_t0 = time.perf_counter()
    chunks = []
    over_1s = []
    phase_times = {}
    with open(tmp, "wb") as f:
        off = 0
        i = 0
        while off < len(data):
            chunk = data[off:off + CHUNK]
            i += 1
            t0 = time.perf_counter()
            f.write(chunk)
            t1 = time.perf_counter()
            write_ms = (t1 - t0) * 1000.0
            time.sleep(0.006)
            t2 = time.perf_counter()
            total_ms = (t2 - t0) * 1000.0
            rec = {"i": i, "bytes": len(chunk), "write_ms": round(write_ms, 3),
                   "sleep_ms": round((t2 - t1) * 1000.0, 3),
                   "total_ms": round(total_ms, 3)}
            chunks.append(rec)
            if write_ms > 1000.0 or total_ms > 1000.0:
                over_1s.append({"i": i, "write_ms": rec["write_ms"], "total_ms": rec["total_ms"]})
            off += len(chunk)
        t0 = time.perf_counter()
        f.flush()
        t1 = time.perf_counter()
        phase_times["flush_ms"] = round((t1 - t0) * 1000.0, 3)
        t0 = time.perf_counter()
        os.fsync(f.fileno())
        t1 = time.perf_counter()
        phase_times["fsync_ms"] = round((t1 - t0) * 1000.0, 3)
    t0 = time.perf_counter()
    mode = _durable_replace(tmp, str(target))
    t1 = time.perf_counter()
    phase_times["replace_ms"] = round((t1 - t0) * 1000.0, 3)
    phase_times["replace_mode"] = mode
    total_s = round(time.perf_counter() - round_t0, 3)
    tgt_sha = sha16_file(target)
    slow = max(chunks, key=lambda c: c["total_ms"]) if chunks else None
    phase_stall = {k: v for k, v in phase_times.items()
                   if isinstance(v, (int, float)) and v > 1000.0}
    first_stall = None
    for c in chunks:
        if c["total_ms"] > 1000.0:
            first_stall = {"phase": "chunk_write", "i": c["i"], "ms": c["total_ms"]}
            break
    if first_stall is None and phase_stall:
        first_stall = {"phase": "post_write", "detail": phase_stall}
    return {
        "round": rnd,
        "target_was_preexisting": target_was_preexisting,
        "total_s": total_s,
        "n_chunks": len(chunks),
        "slowest_chunk": slow,
        "chunks_over_1s": over_1s,
        "phase_ms": phase_times,
        "phase_over_1s": phase_stall,
        "first_stall": first_stall,
        "target_sha16_after": tgt_sha,
        "target_bytes_after": os.path.getsize(target),
        "target_n_tokens_after": header_ntokens(target),
        "tmp_removed": not os.path.exists(tmp),
        "chunks": chunks,
    }


def run_arm(mode, data):
    target = OUT / "_k1_io_probe" / mode / "target.kvmem"
    if target.parent.exists():
        shutil.rmtree(target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    pre = None
    if mode == "precreated":
        pre = precreate(target, data)
    if mode == "fresh":
        try:
            target.unlink()
        except FileNotFoundError:
            pass
    rounds = []
    aborted = False
    abort_reason = None
    for rnd in range(1, ROUNDS + 1):
        was_pre = target.exists()
        rec = one_round(target, data, rnd, was_pre)
        rounds.append(rec)
        print("IOARM %s round=%d total_s=%.3f slowest_ms=%s over1s=%d first_stall=%s" % (
            mode, rnd, rec["total_s"],
            rec["slowest_chunk"]["total_ms"] if rec["slowest_chunk"] else None,
            len(rec["chunks_over_1s"]), json.dumps(rec["first_stall"], ensure_ascii=False)), flush=True)
        # Stop if a 100 s-level stall appears after round 1 (steady state).
        if rnd > 1:
            if rec["slowest_chunk"] and rec["slowest_chunk"]["total_ms"] > 100000.0:
                aborted = True
                abort_reason = "steady-round chunk >100 s at round %d chunk %d" % (rnd, rec["slowest_chunk"]["i"])
                break
            heavy_phase = {k: v for k, v in (rec.get("phase_over_1s") or {}).items()
                           if isinstance(v, (int, float)) and v > 100000.0}
            if heavy_phase:
                aborted = True
                abort_reason = "steady-round phase >100 s at round %d: %r" % (rnd, heavy_phase)
                break
    totals = [r["total_s"] for r in rounds]
    first_stall_round = next((r["round"] for r in rounds if r["first_stall"]), None)
    return {"mode": mode, "target": str(target), "precreate": pre,
            "rounds": rounds, "aborted": aborted, "abort_reason": abort_reason,
            "totals_s": totals,
            "mean_total_s": round(sum(totals) / len(totals), 3) if totals else None,
            "max_total_s": max(totals) if totals else None,
            "first_stall_round": first_stall_round,
            "steady_rounds_max_slowest_ms": max((r["slowest_chunk"]["total_ms"] for r in rounds[1:]
                                                 if r.get("slowest_chunk")), default=None)}


def main():
    global ROUNDS
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=ROUNDS)
    a = ap.parse_args()
    ROUNDS = a.rounds
    data = ensure_source()
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    art = {"schema": "m5_k1_io_microbench_v1", "at": started,
           "source": {"path": str(SRC), "sha16": sha16_file(SRC), "bytes": len(data),
                      "n_tokens": header_ntokens(SRC)},
           "chunk_bytes": CHUNK, "rounds_per_arm": ROUNDS,
           "note": "pure file; no Vulkan/model; target overwritten each round; exact K1 save loop",
           "arms": [], "status": "running", "conclusion": None}
    try:
        for mode in ("fresh", "precreated"):
            arm = run_arm(mode, data)
            art["arms"].append(arm)
            print("IOARM_DONE %s rounds=%d aborted=%s" % (mode, len(arm["rounds"]), arm["aborted"]), flush=True)
            if arm["aborted"]:
                break
        fresh = next((x for x in art["arms"] if x["mode"] == "fresh"), None)
        pre = next((x for x in art["arms"] if x["mode"] == "precreated"), None)
        art["status"] = "completed" if len(art["arms"]) == 2 else "aborted"
        if fresh and pre:
            f_first = fresh["rounds"][0]["total_s"] if fresh["rounds"] else None
            f_steady = fresh["totals_s"][1:] if len(fresh["totals_s"]) > 1 else []
            p_all = pre["totals_s"]
            art["conclusion"] = {
                "fresh_first_round_s": f_first,
                "fresh_steady_mean_s": round(sum(f_steady) / len(f_steady), 3) if f_steady else None,
                "fresh_steady_max_slowest_ms": fresh["steady_rounds_max_slowest_ms"],
                "precreated_mean_s": pre["mean_total_s"],
                "precreated_max_slowest_ms": pre["steady_rounds_max_slowest_ms"],
                "precreated_max_total_s": pre["max_total_s"],
                "first_stall_round_fresh": fresh["first_stall_round"],
                "first_stall_round_precreated": pre["first_stall_round"],
                "stall_disappeared_with_precreated": bool(
                    fresh["first_stall_round"] is not None and pre["first_stall_round"] is None),
                "steady_100s_stall": bool(
                    (fresh and any(r["slowest_chunk"] and r["slowest_chunk"]["total_ms"] > 100000.0
                                   for r in fresh["rounds"][1:])) or
                    (pre and any(r["slowest_chunk"] and r["slowest_chunk"]["total_ms"] > 100000.0
                                 for r in pre["rounds"][1:]))),
            }
    except BaseException as e:  # noqa: BLE001
        art["status"] = "未接上（微基准异常）"
        art["error"] = type(e).__name__ + ": " + str(e)
    finally:
        art["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        p = Path(ART)
        tmp = str(p) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(art, f, ensure_ascii=False, indent=1)
        os.replace(tmp, p)
        print("IOART " + json.dumps({"status": art["status"], "conclusion": art["conclusion"],
                                     "sha16": sha16_file(p), "bytes": os.path.getsize(p)},
                                    ensure_ascii=False), flush=True)
    return 0 if art["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())