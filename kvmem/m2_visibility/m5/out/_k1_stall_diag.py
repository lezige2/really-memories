# -*- coding: utf-8 -*-
"""Zero-GPU K1 stall diagnosis.

Imports the frozen child's ACTUAL save_cycles() and skips Vulkan entirely.
A_cold      : child save_cycles(), 5 cycles, exact flush/fsync/replace cadence.
A_preheated : target pre-created to 8 MiB and read once; then same 5 cycles.
B_one_fsync : same 5x data/chunk cadence, but no per-cycle fsync; one fsync at the end.

Important source fact: the frozen child does NOT fsync every chunk.  Its
save_cycles() has ONE flush+fsync per cycle, then _durable_replace().  So B
tests per-cycle fsync, not per-chunk fsync.  That is stated in the artifact.

NO Vulkan, NO model, NO kill, NO signal.
"""
import builtins
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "kvmem/m2_visibility/m5/out"
SRC = OUT / "M5-KILL-before.kvmem"
DIAG = OUT / "_k1_stall_diag"
ART = OUT / "M5-K1-STALL-DIAG.json"
sys.path.insert(0, str(OUT))
import _k1_park_child as CH  # noqa: E402  (module import only; no Vulkan object is created)


def sha16_bytes(b):
    return hashlib.sha256(b).hexdigest()[:16]


def sha16_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def ntokens(p):
    b = open(p, "rb").read(12)
    return int.from_bytes(b[8:12], "little")


class CaptureLogger:
    def __init__(self, state_log, cycle_ref=None):
        self.real = CH.Logger(state_log)
        self.events = []
        self.cycle_ref = cycle_ref

    def st(self, state, **detail):
        if self.cycle_ref is not None and state == "saving_cycle" and detail.get("phase") == "pre_tmp":
            self.cycle_ref[0] = detail.get("cycle", self.cycle_ref[0])
        t = time.perf_counter()
        rec = {"state": state, "t_perf": t, **detail}
        self.events.append(rec)
        self.real.st(state, **detail)
        return rec

    def close(self):
        self.real.close()


class TraceFile:
    """Records every write() call made by the imported child save_cycles()."""
    def __init__(self, f, chunks, cycle_ref):
        self.f = f
        self.chunks = chunks
        self.cycle_ref = cycle_ref
        self.serial = 0
        self.last_end = None

    def write(self, b):
        self.serial += 1
        t0 = time.perf_counter()
        gap_ms = 0.0 if self.last_end is None else (t0 - self.last_end) * 1000.0
        n = self.f.write(b)
        t1 = time.perf_counter()
        self.last_end = t1
        self.chunks.append({"cycle": self.cycle_ref[0], "serial": self.serial,
                            "bytes": n, "gap_ms": round(gap_ms, 3),
                            "write_ms": round((t1 - t0) * 1000.0, 3),
                            "total_ms": round(gap_ms + (t1 - t0) * 1000.0, 3)})
        return n

    def __getattr__(self, name):
        return getattr(self.f, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return self.f.__exit__(*exc)


def call_child_save(target, tag):
    """Call frozen child save_cycles(); only monkeypatch open to record chunk writes."""
    if target.parent.exists():
        shutil.rmtree(target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    chunks = []
    cycle_ref = [0]
    orig_open = builtins.open
    orig_replace = CH._durable_replace
    replace_events = []

    def traced_open(path, mode="r", *args, **kwargs):
        f = orig_open(path, mode, *args, **kwargs)
        if "w" in mode and str(path).endswith(tuple(".tmp-%d-%d" % (os.getpid(), i) for i in range(1, 10))):
            return TraceFile(f, chunks, cycle_ref)
        return f

    def traced_replace(tmp, tgt):
        t0 = time.perf_counter()
        mode = orig_replace(tmp, tgt)
        dt = round((time.perf_counter() - t0) * 1000.0, 3)
        replace_events.append({"cycle": cycle_ref[0], "ms": dt, "mode": mode})
        return mode

    builtins.open = traced_open
    CH._durable_replace = traced_replace
    try:
        log = CaptureLogger(OUT / ("_k1_stall_diag_%s.log" % tag), cycle_ref)
        t0 = time.perf_counter()
        res = CH.save_cycles(log, SRC, target, 5)
        total_s = round(time.perf_counter() - t0, 3)
        ev = log.events
        log.close()
    finally:
        builtins.open = orig_open
        CH._durable_replace = orig_replace

    cycles = []
    starts = {}
    for e in ev:
        if e.get("state") == "saving_cycle" and e.get("phase") == "pre_tmp":
            cycle_ref[0] = e["cycle"]
            starts[e["cycle"]] = e["t_perf"]
        if e.get("state") == "saving_cycle" and e.get("phase") == "done":
            c = e["cycle"]
            dt = (e["t_perf"] - starts.get(c, e["t_perf"])) * 1000.0
            cycles.append({"cycle": c, "total_ms": round(dt, 3)})
    by_cycle = {}
    for c in chunks:
        by_cycle.setdefault(c["cycle"], []).append(c)
    rounds = []
    for c in cycles:
        arr = by_cycle.get(c["cycle"], [])
        slow = max(arr, key=lambda x: x["total_ms"]) if arr else None
        over = [x for x in arr if x["total_ms"] > 1000.0]
        stall_near = bool(slow and 60 <= slow["serial"] <= 75 and slow["total_ms"] > 1000.0)
        rounds.append({"cycle": c["cycle"], "total_s": round(c["total_ms"] / 1000.0, 3),
                       "n_chunks": len(arr), "slowest_chunk": slow,
                       "chunks_over_1s": over, "stall_near_64_72": stall_near})
    return {"tag": tag, "target": str(target), "total_5cycles_s": total_s,
            "rounds": rounds, "replace_events": replace_events,
            "save_result": res, "events": ev, "chunks": chunks}


def precreate_8mb(target):
    target.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    with open(target, "wb") as f:
        f.write(b"\0" * (8 * 1024 * 1024))
        f.flush()
        os.fsync(f.fileno())
    b = target.read_bytes()
    time.sleep(0.5)
    return {"bytes": len(b), "sha16": sha16_bytes(b), "elapsed_s": round(time.perf_counter() - t0, 3),
            "read_once": True}


def arm_b_one_fsync(target):
    data = SRC.read_bytes()
    if target.parent.exists():
        shutil.rmtree(target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    rounds = []
    replace_events = []
    t_all = time.perf_counter()
    for cyc in range(1, 6):
        tmp = str(target) + ".tmp-b-%d" % cyc
        t0 = time.perf_counter()
        chunks = []
        last_end = None
        time.sleep(0.050)
        with open(tmp, "wb") as f:
            off = 0
            i = 0
            while off < len(data):
                chunk = data[off:off + 65536]
                i += 1
                w0 = time.perf_counter()
                gap_ms = 0.0 if last_end is None else (w0 - last_end) * 1000.0
                f.write(chunk)
                w1 = time.perf_counter()
                last_end = w1
                chunks.append({"serial": i, "bytes": len(chunk),
                               "gap_ms": round(gap_ms, 3),
                               "write_ms": round((w1 - w0) * 1000.0, 3),
                               "total_ms": round(gap_ms + (w1 - w0) * 1000.0, 3)})
                time.sleep(0.006)
                off += len(chunk)
            time.sleep(0.030)
            # no flush/fsync here: the one and only fsync is after all 5 cycles
        r0 = time.perf_counter()
        mode = CH._durable_replace(tmp, str(target))
        r1 = time.perf_counter()
        replace_events.append({"cycle": cyc, "ms": round((r1 - r0) * 1000.0, 3), "mode": mode})
        time.sleep(0.400)
        slow = max(chunks, key=lambda x: x["total_ms"]) if chunks else None
        over = [x for x in chunks if x["total_ms"] > 1000.0]
        rounds.append({"cycle": cyc, "total_s": round(time.perf_counter() - t0, 3),
                       "n_chunks": len(chunks), "slowest_chunk": slow,
                       "chunks_over_1s": over,
                       "stall_near_64_72": bool(slow and 60 <= slow["serial"] <= 75 and slow["total_ms"] > 1000.0)})
    with open(target, "rb+") as f:
        f.flush()
        os.fsync(f.fileno())
    return {"tag": "B_one_fsync", "target": str(target),
            "total_5cycles_s": round(time.perf_counter() - t_all, 3),
            "rounds": rounds, "replace_events": replace_events,
            "final_fsync_only": True,
            "target_sha16": sha16_file(target), "target_bytes": os.path.getsize(target),
            "target_n_tokens": ntokens(target)}


def main():
    data = SRC.read_bytes()
    if len(data) != 5224388 or sha16_bytes(data) != "3b046c8ee3fb3b53":
        raise SystemExit("source changed")
    art = {"schema": "m5_k1_stall_diag_v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "source": {"path": str(SRC), "sha16": sha16_bytes(data), "bytes": len(data)},
           "method": "imported frozen _k1_park_child.save_cycles; Vulkan skipped; no model; no kill",
           "actual_child_io_note": "frozen child's save_cycles does ONE flush+fsync per cycle, NOT per chunk; B_one_fsync tests per-cycle fsync frequency",
           "arms": {}, "judgment": {}, "status": "running"}
    try:
        a1 = call_child_save(DIAG / "A_cold" / "target.kvmem", "A_cold")
        art["arms"]["A_cold"] = a1
        print("STALL A_cold " + json.dumps({"rounds": [r["total_s"] for r in a1["rounds"]],
                                            "stall": [r["stall_near_64_72"] for r in a1["rounds"]]},
                                           ensure_ascii=False), flush=True)

        pre = precreate_8mb(DIAG / "A_preheated" / "target.kvmem")
        a2 = call_child_save(DIAG / "A_preheated" / "target.kvmem", "A_preheated")
        art["arms"]["A_preheated"] = a2
        art["preheat"] = pre
        print("STALL A_preheated " + json.dumps({"pre": pre, "rounds": [r["total_s"] for r in a2["rounds"]],
                                                  "stall": [r["stall_near_64_72"] for r in a2["rounds"]]},
                                                 ensure_ascii=False), flush=True)

        b = arm_b_one_fsync(DIAG / "B_one_fsync" / "target.kvmem")
        art["arms"]["B_one_fsync"] = b
        print("STALL B " + json.dumps({"rounds": [r["total_s"] for r in b["rounds"]],
                                        "stall": [r["stall_near_64_72"] for r in b["rounds"]]},
                                       ensure_ascii=False), flush=True)

        a_cold_stall = any(r["stall_near_64_72"] for r in a1["rounds"])
        a_pre_stall = any(r["stall_near_64_72"] for r in a2["rounds"])
        b_stall = any(r["stall_near_64_72"] for r in b["rounds"])
        if a_cold_stall and not b_stall:
            conclusion = "A-only => per-cycle fsync + file growth / IO-scan; not Vulkan"
        elif not a_cold_stall and not b_stall:
            conclusion = "neither A nor B reproduces => child's Vulkan prelude interaction is the remaining suspect"
        elif a_cold_stall and b_stall:
            conclusion = "both A/B reproduce => environment (Defender/disk), not child-specific"
        else:
            conclusion = "A not stalled but B stalled => inconsistent; investigate"
        art["judgment"] = {
            "A_cold_stall_near_64_72": bool(a_cold_stall),
            "A_preheated_stall_near_64_72": bool(a_pre_stall),
            "B_one_fsync_stall_near_64_72": bool(b_stall),
            "conclusion": conclusion,
            "preheat_effect": "stall disappeared after 8 MiB precreate+read" if a_cold_stall and not a_pre_stall else
                              ("still stalls after preheat" if a_pre_stall else "no cold stall to compare")
        }
        art["status"] = "completed"
    except BaseException as e:  # noqa: BLE001
        art["status"] = "未接上（诊断异常）"
        art["error"] = type(e).__name__ + ": " + str(e)
    finally:
        art["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        p = Path(ART)
        tmp = str(p) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(art, f, ensure_ascii=False, indent=1)
        os.replace(tmp, p)
        print("STALL_ART " + json.dumps({"status": art["status"], "judgment": art.get("judgment"),
                                         "sha16": sha16_file(p), "bytes": os.path.getsize(p)},
                                        ensure_ascii=False), flush=True)
    return 0 if art["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())