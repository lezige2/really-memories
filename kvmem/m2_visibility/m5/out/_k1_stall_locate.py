# -*- coding: utf-8 -*-
"""K1 stall location: 1 vk=on run + 1 vk=off comparison run, 5 cycles, no kill.

The child has a 200 ms heartbeat thread and high-resolution syscall boundaries.
No Vulkan is built in --vk=off. No model, no armed, no L1.
Soft timeout at 90 s is recorded but the process is allowed to finish the stall;
hard stop at 180 s only if it still has not exited.
"""
import json
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "kvmem/m2_visibility/m5/out"
CHILD = OUT / "_k1_park_child.py"
BEFORE = OUT / "M5-KILL-before.kvmem"
ART = OUT / "M5-K1-STALL-LOCATE.json"
SOFT_S = 90.0
HARD_S = 180.0
CYCLES = 5


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def info(p):
    p = Path(p)
    if not p.exists():
        return None
    return {"path": str(p), "sha16": sha16(p), "bytes": p.stat().st_size}


def parse_log(path):
    heartbeats, states = [], []
    try:
        for line in open(path, encoding="utf-8"):
            if line.startswith("[HEARTBEAT "):
                heartbeats.append(line.rstrip("\n"))
            elif line.startswith("[STATE "):
                states.append(line.rstrip("\n"))
    except FileNotFoundError:
        pass
    return heartbeats, states


def run_one(mode):
    tag = "vk_%s" % mode
    target = OUT / "_k1_stall_locate" / tag / "target.kvmem"
    state = OUT / ("kill_state_locate_%s.log" % tag)
    result = OUT / ("_k1_stall_locate_result_%s.json" % tag)
    for p in (state, result):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    if target.parent.exists():
        import shutil
        shutil.rmtree(target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(CHILD), "--run", "901" if mode == "on" else "902",
           "--vk", mode, "--cycles", str(CYCLES),
           "--source", str(BEFORE), "--target", str(target),
           "--state-log", str(state), "--result", str(result)]
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    soft = False
    hard = False
    while p.poll() is None:
        e = time.perf_counter() - t0
        if e >= SOFT_S and not soft:
            soft = True
        if e >= HARD_S:
            hard = True
            try:
                p.kill()
            except Exception:  # noqa: BLE001
                pass
            break
        time.sleep(0.005)
    try:
        so, se = p.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        so, se = "", ""
    elapsed = round(time.perf_counter() - t0, 3)
    hb, st = parse_log(state)
    res = json.load(open(result, encoding="utf-8")) if result.exists() else None
    last_state = st[-1] if st else None
    last_hb = hb[-1] if hb else None
    save = (res or {}).get("save") or {}
    saves = save.get("saves") or []
    chunks = []
    for c in saves:
        chunks.extend(c.get("chunk_timings") or [])
    slow = max(chunks, key=lambda x: x["total_ms"]) if chunks else None
    over1 = [x for x in chunks if x["total_ms"] > 1000.0]
    phases = [h.split("phase=", 1)[1].split("]", 1)[0] for h in hb if "phase=" in h]
    return {
        "mode": mode, "command": cmd, "elapsed_s": elapsed,
        "soft_timeout_90s": bool(soft), "hard_timeout_180s": bool(hard),
        "returncode": p.returncode, "signals_sent": 1 if hard else 0,
        "state_log": str(state), "state_log_info": info(state),
        "result": str(result), "result_info": info(result),
        "heartbeat_count": len(hb), "heartbeat_tail": hb[-25:],
        "phase_timeline": phases[-200:], "last_heartbeat": last_hb,
        "last_state": last_state,
        "states_tail": st[-20:],
        "status_from_child": (res or {}).get("status"),
        "elapsed_from_child": (res or {}).get("elapsed_s"),
        "vk": (res or {}).get("vk"),
        "save_ok": save.get("all_third_zero"),
        "n_cycles_completed": len(saves),
        "slowest_chunk": slow, "chunks_over_1s": over1,
        "target": info(target), "target_n_tokens": None,
        "syscall_trace": (res or {}).get("syscall_trace"),
        "phase_history": (res or {}).get("phase_history"),
        "stdout_tail": (so or "")[-4000:], "stderr_tail": (se or "")[-4000:],
    }


def main():
    art = {"schema": "m5_k1_stall_locate_v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "fixture": {"path": str(CHILD), "sha16": sha16(CHILD), "bytes": CHILD.stat().st_size,
                       "old_uninstrumented": {"sha16": "9339107866cbc84c", "bytes": 24243}},
           "instrumentation": {
               "heartbeat": "independent thread, 200 ms, phase snapshot",
               "phases": ["vulkan_init", "device_ready", "park_waitIdle", "park_destroyDevice",
                          "park_destroyInstance", "holding", "save_pre_tmp", "save_write(chunk_i)",
                          "save_flush", "save_fsync", "save_replace", "save_post", "sleep", "graceful_exit"],
               "syscall_boundaries": ["write", "flush", "fsync", "MoveFileExW", "durable_replace"],
               "chunk": "write_ms/gap_ms/total_ms per chunk",
               "armed_rejected": True, "armed_child_rc": None,
           },
           "timeout_policy": {"soft_s": SOFT_S, "hard_s": HARD_S,
                              "soft_note": "recorded at 90 s, process allowed to finish the stall",
                              "hard_note": "TerminateProcess only if still alive at 180 s"},
           "runs": [], "comparison": {}, "status": "running"}
    # Prove --armed is refused, no child run.
    try:
        q = subprocess.run([sys.executable, str(CHILD), "--armed"], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=10)
        art["instrumentation"]["armed_child_rc"] = q.returncode
        art["instrumentation"]["armed_stdout"] = q.stdout.strip()[-300:]
        art["instrumentation"]["armed_stderr"] = q.stderr.strip()[-300:]
    except Exception as e:  # noqa: BLE001
        art["instrumentation"]["armed_error"] = type(e).__name__ + ": " + str(e)
    try:
        on = run_one("on")
        art["runs"].append(on)
        print("LOCATE vk=on elapsed=%.3f soft=%s hard=%s rc=%s status=%s" % (
            on["elapsed_s"], on["soft_timeout_90s"], on["hard_timeout_180s"],
            on["returncode"], on["status_from_child"]), flush=True)
        off = run_one("off")
        art["runs"].append(off)
        print("LOCATE vk=off elapsed=%.3f soft=%s hard=%s rc=%s status=%s" % (
            off["elapsed_s"], off["soft_timeout_90s"], off["hard_timeout_180s"],
            off["returncode"], off["status_from_child"]), flush=True)
        on_to = on["soft_timeout_90s"] or on["hard_timeout_180s"]
        off_to = off["soft_timeout_90s"] or off["hard_timeout_180s"]
        if off_to and not on_to:
            conclusion = "vk=off also stalls => not Vulkan-specific; environment/IO"
        elif on_to and not off_to:
            conclusion = "only vk=on stalls => Vulkan-prelude interaction"
        elif on_to and off_to:
            conclusion = "both stall => environment/IO pressure, not Vulkan-specific"
        else:
            conclusion = "neither stalls in this run => stall did not reproduce; no attribution from this sample"
        art["comparison"] = {"vk_on_stall": bool(on_to), "vk_off_stall": bool(off_to),
                             "conclusion": conclusion,
                             "vk_on_last_phase": on.get("last_heartbeat"),
                             "vk_off_last_phase": off.get("last_heartbeat")}
        art["status"] = "completed"
    except BaseException as e:  # noqa: BLE001
        art["status"] = "未接上（定位异常）"
        art["error"] = type(e).__name__ + ": " + str(e)
    finally:
        art["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        art["signals_sent"] = sum(r.get("signals_sent", 0) for r in art["runs"])
        art["kill_attempts"] = 0
        art["armed"] = False
        art["no_model"] = True
        tmp = str(ART) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(art, f, ensure_ascii=False, indent=1)
        os.replace(tmp, ART)
        print("LOCATE_ART " + json.dumps({"status": art["status"], "comparison": art["comparison"],
                                           "fixture": art["fixture"],
                                           "sha16": sha16(ART), "bytes": ART.stat().st_size},
                                          ensure_ascii=False), flush=True)
    return 0 if art["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())