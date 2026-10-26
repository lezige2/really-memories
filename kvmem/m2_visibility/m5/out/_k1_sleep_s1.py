# -*- coding: utf-8 -*-
"""K1 S1: true post-destroy wait (5 s) before save, no trace, no kill, no model.

Only S1 is run in this step.  S2 (2 s) is not started until the Lead accepts S1.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "kvmem/m2_visibility/m5/out"
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/m7" / "out"))
sys.path.insert(0, str(OUT))
import _k1_warmup_settle as W  # noqa: E402

CHILD = OUT / "_k1_park_child.py"
BEFORE = OUT / "M5-KILL-before.kvmem"
ART = OUT / "M5-K1-SLEEP-S1.json"
PARK_SLEEP = 5.0
CYCLES = 3
SOFT_S = 60.0
HARD_S = 60.0
SLOW_S = 10.0


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def info(p):
    p = Path(p)
    return {"path": str(p), "sha16": sha16(p), "bytes": p.stat().st_size} if p.exists() else None


def main():
    target = OUT / "kill_k1" / "sleep-s1" / "target.kvmem"
    state = OUT / "kill_state_sleep_s1.log"
    result = OUT / "_k1_sleep_s1_result.json"
    for p in (state, result):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    if target.parent.exists():
        shutil.rmtree(target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    peak_s = W.start_sampler("s1")
    cmd = [sys.executable, str(CHILD), "--run", "971", "--vk", "on", "--cycles", str(CYCLES),
           "--no-kill", "--no-settle", "--park-sleep", str(PARK_SLEEP),
           "--source", str(BEFORE), "--target", str(target),
           "--state-log", str(state), "--result", str(result)]
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    timed_out = False
    signals = 0
    while p.poll() is None:
        if time.perf_counter() - t0 > SOFT_S:
            timed_out = True
            break
        time.sleep(0.005)
    if timed_out:
        signals = 1
        try:
            p.kill()
        except Exception:  # noqa: BLE001
            pass
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    else:
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            timed_out = True
    elapsed = round(time.perf_counter() - t0, 3)
    peak = W.stop_sampler(peak_s)
    try:
        so, se = p.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        so, se = "", ""
    res = json.load(open(result, encoding="utf-8")) if result.exists() else None
    save = (res or {}).get("save") or {}
    saves = save.get("saves") or []
    cycles = [{"cycle": x.get("cycle"), "cycle_time_s": x.get("cycle_time_s"),
               "third": x.get("third"), "target_bytes": x.get("target_bytes"),
               "flush_ms": x.get("flush_ms"), "fsync_ms": x.get("fsync_ms")} for x in saves]
    states = W.parse_states(state)
    tmp = sorted([q.name for q in target.parent.glob("target.kvmem.tmp*")])
    target_sha = sha16(target) if target.exists() else None
    completed = bool((not timed_out) and p.returncode == 0 and res and
                     res.get("status") == "completed" and len(saves) == CYCLES and elapsed <= SLOW_S)
    art = {
        "schema": "m5_k1_sleep_s1_v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "purpose": "S1 only: park -> true sleep 5 s -> save 3 cycles; no trace, no kill, no L1",
        "fixture": {"child": info(CHILD), "before": info(BEFORE),
                    "settle_changed": False, "trace_used": False},
        "s1": {"park_sleep_s": PARK_SLEEP, "cycles": CYCLES,
               "settle_skipped": True,
               "payload": "original 5,224,388 B / 80 x 65,536 B"},
        "timeout_policy": {"soft_s": SOFT_S, "hard_s": HARD_S, "slow_s": SLOW_S},
        "attempts": [{"id": "S1", "counted": True, "attempts": 1, "rerun": False}],
        "result": {
            "elapsed_s": elapsed, "timed_out_gt60": bool(timed_out),
            "returncode": p.returncode, "signals_sent": signals,
            "completed": completed, "freeze": bool(not completed),
            "soft_timeout_60": bool(timed_out),
            "post_park_wait_s": (res or {}).get("post_park_wait_s"),
            "park_to_save_s": (res or {}).get("park_to_save_s"),
            "settle": (res or {}).get("settle"),
            "cycle_times_s": [x.get("cycle_time_s") for x in saves],
            "cycles": cycles, "n_cycles_completed": len(saves),
            "target": info(target), "target_sha16": target_sha,
            "target_n_tokens": (int.from_bytes(open(target, "rb").read(12)[8:12], "little")
                                if target.exists() else None),
            "tmp_remaining": tmp,
            "peak_gib": peak,
            "state_log": info(state), "result_file": info(result),
            "states_tail": states[-12:],
            "stdout_tail": (so or "")[-4000:], "stderr_tail": (se or "")[-4000:],
            "save_ok": save.get("all_third_zero"),
        },
        "status": "passed" if completed else "stopped_freeze",
    }
    tmpj = str(ART) + ".tmp"
    with open(tmpj, "w", encoding="utf-8", newline="\n") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)
    os.replace(tmpj, ART)
    b = ART.read_bytes()
    print("S1_ART " + json.dumps({"status": art["status"], "result": {k: art["result"][k] for k in
          ["elapsed_s", "completed", "freeze", "post_park_wait_s", "park_to_save_s",
           "cycle_times_s", "n_cycles_completed", "tmp_remaining", "peak_gib", "signals_sent"]},
          "fixture": art["fixture"], "sha16": hashlib.sha256(b).hexdigest()[:16], "bytes": len(b)},
          ensure_ascii=False), flush=True)
    return 0 if completed else 1


if __name__ == "__main__":
    sys.exit(main())