# -*- coding: utf-8 -*-
"""K1 mechanism discrimination: V1 prewarm, V2 1 MiB payload, V3 1 MiB chunks.

Each variant runs exactly once, vk=on, --no-kill, 5 cycles.  Trace boundaries are
flushed+fsynced by the child to a separate file immediately, so a frozen run
still leaves the last boundary on disk.  Soft timeout 90 s; hard stop 120 s is
only an emergency stop and is counted in signals_sent.
"""
import json
import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "kvmem/m2_visibility/m5/out"
CHILD = OUT / "_k1_park_child.py"
BEFORE = OUT / "M5-KILL-before.kvmem"
ART = OUT / "M5-K1-STALL-MECH.json"
SOFT_S = 90.0
HARD_S = 120.0
CYCLES = 5

VARIANTS = [
    {"id": "V1", "desc": "prewarm 5 MB tmp before Vulkan", "args": ["--prewarm"]},
    {"id": "V2", "desc": "payload 1 MiB / 20 chunks", "args": ["--payload-bytes", "1048576", "--chunk-bytes", "52429"]},
    {"id": "V3", "desc": "total 5 MB / 1 MiB x 5 chunks", "args": ["--chunk-bytes", "1048576"]},
]


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


def parse_state(path):
    hb, st = [], []
    try:
        for line in open(path, encoding="utf-8"):
            if line.startswith("[HEARTBEAT "):
                hb.append(line.rstrip("\n"))
            elif line.startswith("[STATE "):
                st.append(line.rstrip("\n"))
    except FileNotFoundError:
        pass
    return hb, st


def phase(h):
    return h.split("phase=", 1)[1].split("]", 1)[0] if "phase=" in h else None


def run_variant(v):
    vid = v["id"]
    target = OUT / "_k1_stall_mech" / vid / "target.kvmem"
    state = OUT / ("kill_state_mech_%s.log" % vid)
    result = OUT / ("_k1_stall_mech_result_%s.json" % vid)
    trace = OUT / ("_k1_trace_%s.log" % vid)
    for p in (state, result, trace):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    if target.parent.exists():
        shutil.rmtree(target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(CHILD), "--run", "801" if vid == "V1" else ("802" if vid == "V2" else "803"),
           "--vk", "on", "--no-kill", "--cycles", str(CYCLES),
           "--trace", str(trace), "--source", str(BEFORE), "--target", str(target),
           "--state-log", str(state), "--result", str(result)] + v["args"]
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    soft = hard = False
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
        se = p.communicate(timeout=10)[1]
    except subprocess.TimeoutExpired:
        se = ""
    elapsed = round(time.perf_counter() - t0, 3)
    hb, st = parse_state(state)
    res = json.load(open(result, encoding="utf-8")) if result.exists() else None
    save = (res or {}).get("save") or {}
    saves = save.get("saves") or []
    trace_lines = []
    try:
        trace_lines = [x.rstrip("\n") for x in open(trace, encoding="utf-8")]
    except FileNotFoundError:
        pass
    n_cycles = len(saves)
    completed = bool((not soft) and (not hard) and p.returncode == 0 and res and
                     res.get("status") == "completed" and n_cycles == CYCLES and elapsed <= 10.0)
    return {
        "id": vid, "desc": v["desc"], "args": v["args"], "command": cmd,
        "elapsed_s": elapsed, "soft_timeout_90s": bool(soft), "hard_timeout_120s": bool(hard),
        "returncode": p.returncode, "signals_sent": 1 if hard else 0,
        "completed": completed, "freeze": bool(soft or hard or not completed),
        "status_from_child": (res or {}).get("status"),
        "n_cycles_completed": n_cycles, "save_ok": save.get("all_third_zero"),
        "state_log": info(state), "result": info(result), "trace": info(trace),
        "trace_line_count": len(trace_lines), "trace_tail": trace_lines[-12:],
        "trace_last": trace_lines[-1] if trace_lines else None,
        "heartbeat_count": len(hb), "heartbeat_tail": hb[-8:],
        "last_heartbeat": hb[-1] if hb else None,
        "last_phase": phase(hb[-1]) if hb else None,
        "last_state": st[-1] if st else None, "states_tail": st[-8:],
        "target": info(target), "tmp_remaining": sorted([x.name for x in target.parent.glob("target.kvmem.tmp*")]),
        "stderr_tail": (se or "")[-3000:],
        "save": save if res else None,
    }


def main():
    art = {
        "schema": "m5_k1_stall_mech_v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "fixture": {"path": str(CHILD), "sha16": sha16(CHILD), "bytes": CHILD.stat().st_size,
                    "old_uninstrumented": {"sha16": "9339107866cbc84c", "bytes": 24243}},
        "instrumentation": {"trace_each_boundary_flush_fsync": True,
                            "trace_files": "_k1_trace_<V>.log",
                            "trace_boundaries": ["write_begin/write_end", "flush_begin/flush_end",
                                                 "fsync_begin/fsync_end", "MoveFileExW", "durable_replace_begin/end"],
                            "heartbeat": "200 ms, immediate flush to state log"},
        "timeout_policy": {"soft_s": SOFT_S, "hard_s": HARD_S,
                           "hard_stop": "emergency TerminateProcess only; signals_sent counts it"},
        "runs": [], "attempts": [
            {"id": "prior_vk_off_rerun", "counted": False,
             "reason": "first vk=off child was cut off by the 300 s orchestrator shell timeout; it was rerun once to obtain a complete 5-cycle control",
             "recorded_at": "2026-10-26T12:43+08:00"},
            {"id": "prior_vk_on_180s_hard_stop", "counted": True,
             "reason": "vk=on frozen; hard-stopped at 180 s in the previous locate run"}
        ],
        "status": "running", "judgment": {}
    }
    try:
        for v in VARIANTS:
            r = run_variant(v)
            art["runs"].append(r)
            print("MECH %s elapsed=%.3f soft=%s hard=%s rc=%s completed=%s freeze=%s last_phase=%s trace_last=%s" % (
                r["id"], r["elapsed_s"], r["soft_timeout_90s"], r["hard_timeout_120s"],
                r["returncode"], r["completed"], r["freeze"], r["last_phase"], r["trace_last"]), flush=True)
        f = {r["id"]: r["freeze"] for r in art["runs"]}
        if not f.get("V1") and not f.get("V2") and f.get("V3"):
            matrix = "V1 no / V2 no / V3 freeze => first growth + capacity threshold (prewarm can rescue)"
        elif not f.get("V1") and f.get("V2") and f.get("V3"):
            matrix = "V1 no / V2 freeze / V3 freeze => first growth only (prewarm can rescue)"
        elif f.get("V1") and f.get("V2") and f.get("V3"):
            matrix = "V1 freeze / V2 freeze / V3 freeze => Vulkan residual itself is the trigger; reorder the flow"
        elif not any(f.values()):
            matrix = "none freeze => stall did not reproduce in these variants"
        else:
            matrix = "other combination: %s" % json.dumps(f, ensure_ascii=False)
        art["judgment"] = {
            "freeze": f, "matrix_branch": matrix,
            "V1_prewarm_rescues": (not f.get("V1")),
            "V2_capacity_threshold": (not f.get("V2")),
            "V3_chunk_size_sensitivity": (not f.get("V3")),
            "note": "Scores are mechanism hypotheses only; exact syscall is in each trace tail.",
        }
        art["status"] = "completed"
    except BaseException as e:  # noqa: BLE001
        art["status"] = "未接上（机制判别异常）"
        art["error"] = type(e).__name__ + ": " + str(e)
    finally:
        art["signals_sent"] = sum(r.get("signals_sent", 0) for r in art["runs"])
        art["kill_attempts"] = 0
        art["formal_stage_kills"] = 0
        art["armed"] = False
        art["no_model"] = True
        art["l1_runs"] = 0
        art["upper_bound_changed"] = False
        art["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        tmp = str(ART) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(art, f, ensure_ascii=False, indent=1)
        os.replace(tmp, ART)
        print("MECH_ART " + json.dumps({"status": art["status"], "judgment": art.get("judgment"),
                                        "fixture": art["fixture"], "sha16": sha16(ART),
                                        "bytes": ART.stat().st_size,
                                        "signals_sent": art["signals_sent"]}, ensure_ascii=False), flush=True)
    return 0 if art["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())