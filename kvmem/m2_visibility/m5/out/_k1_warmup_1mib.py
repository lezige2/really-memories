# -*- coding: utf-8 -*-
"""K1 1 MiB smoke: two warm-ups, no trace, no kill, no model.

Existing 1 MiB variant parameters: payload 1,048,576 B, chunk 52,429 B (20
chunks).  This is only a smoke test of the reduced payload; it is NOT an L1 run
and it does NOT exercise the formal before/after kill criteria.
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
M7 = ROOT / "kvmem/m2_visibility/m7"
sys.path.insert(0, str(M7 / "out"))
sys.path.insert(0, str(OUT))
import _e3gpu_run as E  # noqa: E402
import _k1_warmup_settle as W  # noqa: E402

CHILD = OUT / "_k1_park_child.py"
BEFORE = OUT / "M5-KILL-before.kvmem"
ART = OUT / "M5-K1-WARMUP-1MIB.json"
PAYLOAD_BYTES = 1048576
CHUNK_BYTES = 52429
CYCLES = 3
SOFT_S = 60.0
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


def ntokens(p):
    return int.from_bytes(open(p, "rb").read(12)[8:12], "little")


def run_one(n):
    target = OUT / "kill_k1" / ("warmup-1mib-%d" % n) / "target.kvmem"
    state = OUT / ("kill_state_warmup_1mib_%03d.log" % n)
    result = OUT / ("_k1_warmup_1mib_result_%03d.json" % n)
    for p in (state, result):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    if target.parent.exists():
        shutil.rmtree(target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    peak_s = W.start_sampler("1m%d" % n)
    cmd = [sys.executable, str(CHILD), "--run", str(950 + n), "--vk", "on", "--cycles", str(CYCLES),
           "--no-kill", "--payload-bytes", str(PAYLOAD_BYTES), "--chunk-bytes", str(CHUNK_BYTES),
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
    settle = (res or {}).get("settle")
    target_info = info(target)
    payload = open(BEFORE, "rb").read()[:PAYLOAD_BYTES]
    payload_sha = hashlib.sha256(payload).hexdigest()[:16]
    target_ok_payload = bool(target.exists() and sha16(target) == payload_sha and
                             ntokens(target) == 50 and target.stat().st_size == PAYLOAD_BYTES)
    tmp = sorted([q.name for q in target.parent.glob("target.kvmem.tmp*")])
    completed = bool((not timed_out) and p.returncode == 0 and res and
                     res.get("status") == "completed" and len(saves) == CYCLES and elapsed <= SLOW_S)
    return {
        "n": n, "elapsed_s": elapsed, "timed_out_gt60": bool(timed_out),
        "completed": completed, "freeze": bool(timed_out or not completed),
        "returncode": p.returncode, "signals_sent": signals,
        "slow_warmup": bool(elapsed > SLOW_S),
        "cycles": cycles, "n_cycles_completed": len(saves),
        "cycle_times_s": [x.get("cycle_time_s") for x in saves],
        "settle_probe": (settle or {}).get("probes"),
        "settle_total_s": (settle or {}).get("total_s"),
        "peak_gib": peak,
        "payload": {"bytes_requested": PAYLOAD_BYTES, "chunk_bytes": CHUNK_BYTES,
                    "chunks_expected": (PAYLOAD_BYTES + CHUNK_BYTES - 1) // CHUNK_BYTES,
                    "sha16": payload_sha},
        "target": target_info, "target_n_tokens": ntokens(target) if target.exists() else None,
        "target_ok_payload": target_ok_payload, "target_bytes_final": target.stat().st_size if target.exists() else None,
        "tmp_remaining": tmp,
        "state_log": info(state), "result": info(result),
        "last_state": W.parse_states(state)[-1] if W.parse_states(state) else None,
        "stderr_tail": (se or "")[-3000:],
    }


def main():
    art = {
        "schema": "m5_k1_warmup_1mib_v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "purpose": "1 MiB smoke only; no trace; no kill; no L1",
        "fixture": {"child": info(CHILD), "before": info(BEFORE),
                    "settle_changed": False, "trace_used": False},
        "payload_amended": {
            "before": "5,224,388 B / 80 chunk",
            "after": "1,048,576 B / 20 chunk (chunk 52,429 B; existing 1 MiB variant)",
            "reason": "post-destroy first large write freezes process at ~3 MiB; 1 MiB payload avoids environmental freeze"
        },
        "timeout_policy": {"warmup_soft_s": 60.0, "slow_s": 10.0,
                           "two_warmups": True, "stop_on_any_freeze": True},
        "a_plan": {
            "status": "planned_only_not_run",
            "atomicity_claim_size_independent": True,
            "large_payload_kill": "未做（环境冻结）",
            "note": "if 1 MiB smoke passes, formal A uses 1 MiB synthetic payload; do not present it as a large-payload kill",
            "before_fixture": "retain before n_tokens semantics; K1 target becomes 1 MiB synthetic payload (before 1 MiB prefix + valid header); payload_is_synthetic=true",
            "load_strict": "still uses real M5-KILL-before.kvmem (5.2 MB); if that write freezes, record separately"
        },
        "runs": [], "attempts": [], "status": "running", "judgment": {}
    }
    try:
        r1 = run_one(1)
        art["runs"].append(r1)
        art["attempts"].append({"id": "1mib_warmup_1", "counted": True, "attempts": 1, "rerun": False})
        print("1MIB %d elapsed=%.3f completed=%s freeze=%s cycles=%d settle=%s target_bytes=%s" % (
            r1["n"], r1["elapsed_s"], r1["completed"], r1["freeze"], r1["n_cycles_completed"],
            r1["settle_probe"], r1["target_bytes_final"]), flush=True)
        if not r1["freeze"]:
            r2 = run_one(2)
            art["runs"].append(r2)
            art["attempts"].append({"id": "1mib_warmup_2", "counted": True, "attempts": 1, "rerun": False})
            print("1MIB %d elapsed=%.3f completed=%s freeze=%s cycles=%d settle=%s target_bytes=%s" % (
                r2["n"], r2["elapsed_s"], r2["completed"], r2["freeze"], r2["n_cycles_completed"],
                r2["settle_probe"], r2["target_bytes_final"]), flush=True)
        else:
            art["attempts"].append({"id": "1mib_warmup_2", "counted": False,
                                    "reason": "not started: first 1 MiB warm-up froze"})
        freezes = [r["freeze"] for r in art["runs"]]
        if not any(freezes) and len(art["runs"]) == 2:
            art["status"] = "passed"
            art["judgment"] = {"passed": True, "both_under_10s": all(r["elapsed_s"] < SLOW_S for r in art["runs"]),
                               "next": "A-plan formal small-payload 100 kills pending lead order"}
        elif any(freezes):
            art["status"] = "stopped_freeze"
            art["judgment"] = {"passed": False, "freeze": freezes,
                               "next": "stop hand, discuss B-plan (fsync every 8 chunks) or record 未接上"}
        else:
            art["status"] = "incomplete"
            art["judgment"] = {"passed": False, "runs": len(art["runs"])}
    except BaseException as e:  # noqa: BLE001
        art["status"] = "未接上（smoke 异常）"
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
        print("1MIB_ART " + json.dumps({"status": art["status"], "judgment": art.get("judgment"),
                                        "fixture": art["fixture"], "sha16": sha16(ART),
                                        "bytes": ART.stat().st_size,
                                        "signals_sent": art["signals_sent"]}, ensure_ascii=False), flush=True)
    return 0 if art["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())