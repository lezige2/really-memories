#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M7 E3-GPU harness SKELETON -- DO NOT RUN until inspector's
`kvmem/m2_visibility/m7/PREREG-M7-E3-GPU.md` is on disk and lead sends go.

Hard rules encoded here:
  * parent never sends a signal to the GPU child (no kill/terminate/taskkill/
    Stop-Process); a stop request is a file flag `_e3gpu_stop.flag` that the
    child polls and exits normally;
  * each scenario has a 900 s wall budget: on timeout the parent only writes
    the stop flag and waits for self-exit;
  * dedicated-VRAM circuit breaker: > 8.6 GiB -> write stop flag; child exits
    normally; no later scenario is started;
  * the GPU DLL is `tools/kvshim_vk.dll` = 9edbafa150700614 / 50,007,552 B;
    it is never rebuilt or overwritten.

Operation point (to be frozen by PREREG):
  n_gpu_layers=36, n_ctx=8192, n_seq=8, kv=q8_0, CHAT_START=4096.
"""
import ctypes
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M7 = ROOT / "kvmem/m2_visibility/m7"
OUT = M7 / "out"
TOOLS = ROOT / "tools"
MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
VK = str(TOOLS / "kvshim_vk.dll")
VK_SHA16 = "9edbafa150700614"
VK_BYTES = 50007552
NGL, NCTX, NSEQ, KV = 36, 8192, 8, "q8_0"
CHAT_START = 4096
GATE_GIB = 8.6
SCENARIO_TIMEOUT_S = 900
STOP = OUT / "_e3gpu_stop.flag"
SAMPLER_PS = OUT / "_e3gpu_sampler.ps1"

# Filled after PREREG; keep this tuple explicit rather than silently running
# arbitrary scenarios.  Skeleton default is a single safe smoke scenario.
SCENARIOS = ("smoke_load_prefill_decode",)


def sha16(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def check_gpu_dll():
    got = sha16(VK)
    if got != VK_SHA16 or os.path.getsize(VK) != VK_BYTES:
        raise RuntimeError("GPU DLL changed: %s/%d expected %s/%d"
                           % (got, os.path.getsize(VK), VK_SHA16, VK_BYTES))


def ws_mb(pid):
    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t)]
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = ctypes.c_void_p
    h = k.OpenProcess(0x1000 | 0x0400, False, int(pid))
    if not h:
        return None
    try:
        c = PMC(); c.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(h),
                                                  ctypes.byref(c), ctypes.sizeof(c))
        return round(c.WorkingSetSize / 1048576.0, 1)
    finally:
        k.CloseHandle(ctypes.c_void_p(h))


def vulkan_loaded():
    k = ctypes.windll.kernel32
    k.GetModuleHandleW.restype = ctypes.c_void_p
    return bool(k.GetModuleHandleW("vulkan-1.dll"))


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def stop_requested():
    return STOP.exists()


def child_step(name, **kw):
    state = {"phase": name, "at": time.strftime("%H:%M:%S"), **kw}
    write_json_atomic(OUT / "_e3gpu_child_state.json", state)
    return state


def child_run():
    """Runs in a fresh process.  Never receives a signal; exits normally when
    STOP appears or after one bounded scenario."""
    check_gpu_dll()
    scenario = os.environ["M7_E3GPU_SCENARIO"]
    sys.path.insert(0, str(TOOLS))
    import kvslots

    if stop_requested():
        print(json.dumps({"status": "stopped_before_load", "scenario": scenario}))
        return 0
    t0 = time.perf_counter()
    eng = kvslots.KVEngine(MODEL, n_ctx=NCTX, n_seq=NSEQ, gpu=NGL,
                           kv=KV, dll=VK)
    load_s = time.perf_counter() - t0
    child_step("loaded", scenario=scenario, load_s=round(load_s, 3),
               dll_sha16=sha16(VK), vulkan_imported=vulkan_loaded(),
               ws_mb=ws_mb(os.getpid()))
    if stop_requested():
        eng.close()
        print(json.dumps({"status": "stopped_after_load", "scenario": scenario,
                          "load_s": round(load_s, 3)}))
        return 0

    # smoke only for the skeleton; prereg will add the real scenarios.
    text = ("a " * 64).strip()
    t1 = time.perf_counter()
    n_pref = eng.write_at(0, text, 0, True)
    pref_s = time.perf_counter() - t1
    child_step("prefilled", scenario=scenario, prefill_n=n_pref,
               prefill_s=round(pref_s, 3))
    if stop_requested():
        eng.close()
        print(json.dumps({"status": "stopped_after_prefill", "scenario": scenario}))
        return 0

    t2 = time.perf_counter()
    ans = eng.ask(0, "Hello", 16)
    dec_s = time.perf_counter() - t2
    child_step("decoded", scenario=scenario, decode_s=round(dec_s, 3))
    res = {"schema": "m7_e3gpu_tier_v1", "scenario": scenario,
           "n_gpu_layers": NGL, "n_ctx": NCTX, "n_seq": NSEQ, "kv": KV,
           "chat_start": CHAT_START, "load_s": round(load_s, 3),
           "prefill_n": n_pref, "prefill_s": round(pref_s, 3),
           "prefill_tok_s": round(n_pref / pref_s, 2) if pref_s else None,
           "decode_s": round(dec_s, 3), "decode_tok_s": round(16 / dec_s, 2) if dec_s else None,
           "process_ws_mb": ws_mb(os.getpid()),
           "vulkan_imported": vulkan_loaded(), "dll_sha16": sha16(VK),
           "child_pid": os.getpid(), "ok": True}
    eng.close()
    write_json_atomic(OUT / ("M7-E3-GPU-%s.json" % scenario), res)
    print("E3GPU_RESULT " + json.dumps(res, ensure_ascii=False), flush=True)
    return 0


def sampler_start():
    return subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(SAMPLER_PS), "-Flag", str(STOP),
         "-Out", str(OUT / "_e3gpu_peak.txt")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace")


def sample_peak_file():
    try:
        return float((OUT / "_e3gpu_peak.txt").read_text(encoding="utf-8").strip())
    except Exception:
        return 0.0


def parent_run():
    OUT.mkdir(parents=True, exist_ok=True)
    check_gpu_dll()
    if not SAMPLER_PS.exists():
        raise RuntimeError("sampler skeleton missing: %s" % SAMPLER_PS)
    for scenario in SCENARIOS:
        try:
            STOP.unlink()
        except FileNotFoundError:
            pass
        try:
            (OUT / "_e3gpu_peak.txt").unlink()
        except FileNotFoundError:
            pass
        child = subprocess.Popen(
            [sys.executable, "-X", "utf8", os.path.abspath(__file__), "child"],
            env={**os.environ, "M7_E3GPU_SCENARIO": scenario,
                 "M7_E3GPU_STOP": str(STOP)},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace")
        sampler = sampler_start()
        deadline = time.monotonic() + SCENARIO_TIMEOUT_S
        timed_out = False
        breaker = False
        while child.poll() is None:
            peak = sample_peak_file()
            if peak / 1073741824.0 > GATE_GIB:
                breaker = True
                STOP.write_text("vram_gate %.3f GiB" % (peak / 1073741824.0),
                                encoding="utf-8")
            if time.monotonic() > deadline:
                timed_out = True
                STOP.write_text("scenario timeout %ds" % SCENARIO_TIMEOUT_S,
                                encoding="utf-8")
            time.sleep(0.1)
        # Normal self-exit only; no signal was sent by this parent.
        STOP.write_text("scenario_done", encoding="utf-8")
        out, err = child.communicate()
        try:
            sampler.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        peak = sample_peak_file()
        res = {"schema": "m7_e3gpu_scenario_v1", "scenario": scenario,
               "n_gpu_layers": NGL, "returncode": child.returncode,
               "timed_out": timed_out, "vram_breaker": breaker,
               "vram_peak_gib": round(peak / 1073741824.0, 4) if peak else None,
               "child_stdout_tail": (out or "").splitlines()[-3:],
               "child_stderr_tail": (err or "").splitlines()[-3:]}
        write_json_atomic(OUT / ("M7-E3-GPU-%s-SCENARIO.json" % scenario), res)
        print("SCENARIO " + json.dumps(res, ensure_ascii=False), flush=True)
        if breaker or timed_out:
            break


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "child":
        raise SystemExit(child_run())
    else:
        parent_run()