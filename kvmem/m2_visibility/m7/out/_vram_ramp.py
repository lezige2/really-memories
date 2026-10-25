#!/usr/bin/env python3
"""M7-VRAM-RAMP: measured Vulkan dedicated-VRAM ramp for 14B at 32/36/40 layers.

One child per tier, env supplied at spawn, normal exit only.  The parent never
signals the GPU child; it only samples GPUAdapterMemory DedicatedUsage every
100 ms through a PowerShell sampler and stops launching *higher* tiers if the
measured peak exceeds 8.6 GiB.
"""
import ctypes
import ctypes.wintypes as W
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
TOOLS = ROOT / "tools"
OUT = ROOT / "kvmem/m2_visibility/m7/out"
MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
VK = str(TOOLS / "kvshim_vk.dll")
CPU = str(TOOLS / "kvshim.dll")
NCTX, NSEQ = 8192, 8
TIERS = [32, 36, 40]
GATE_GIB = 8.6
TARGET_GIB = 8.0
ART = OUT / "M7-VRAM-RAMP.json"
PS1 = OUT / "_vram_sampler.ps1"
BASELINE_PS = (
    "$m=Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory | "
    "Measure-Object -Property DedicatedUsage -Sum; "
    "[math]::Round($m.Sum/1GB,4)"
)

def sha16(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]

def sample_once():
    r = subprocess.run(["powershell", "-NoProfile", "-Command", BASELINE_PS],
                       capture_output=True, text=True, timeout=30)
    try:
        return float(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None

class PMC(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]

def ws_mb(pid):
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = ctypes.c_void_p
    h = k.OpenProcess(0x1000 | 0x0400, False, int(pid))
    if not h:
        return None
    try:
        c = PMC(); c.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(h), ctypes.byref(c), ctypes.sizeof(c))
        return round(c.WorkingSetSize / 1048576.0, 1)
    finally:
        k.CloseHandle(ctypes.c_void_p(h))

def vulkan_loaded():
    k = ctypes.windll.kernel32
    k.GetModuleHandleW.restype = ctypes.c_void_p
    return bool(k.GetModuleHandleW("vulkan-1.dll"))

def child():
    ngl = int(os.environ["M7_VRAM_NGL"])
    tier_path = Path(os.environ["M7_VRAM_OUT"])
    sys.path.insert(0, str(TOOLS))
    import kvslots
    t0 = time.perf_counter()
    eng = kvslots.KVEngine(MODEL, n_ctx=NCTX, n_seq=NSEQ, gpu=ngl, dll=VK)
    load_s = time.perf_counter() - t0
    dll_sha = sha16(VK)
    vk = vulkan_loaded()
    text = ("a " * 64).strip()
    t1 = time.perf_counter()
    n_pref = eng.write_at(0, text, 0, True)
    pref_s = time.perf_counter() - t1
    t2 = time.perf_counter()
    ans = eng.ask(0, "Hello", 16)
    dec_s = time.perf_counter() - t2
    res = {
        "schema": "m7_vram_tier_v1",
        "n_gpu_layers": ngl,
        "load_s": round(load_s, 3),
        "prefill_n": n_pref,
        "prefill_s": round(pref_s, 3),
        "prefill_tok_s": round(n_pref / pref_s, 2) if pref_s > 0 and n_pref else None,
        "decode_tokens": 16,
        "decode_s": round(dec_s, 3),
        "decode_tok_s": round(16 / dec_s, 2) if dec_s > 0 else None,
        "process_ws_mb": ws_mb(os.getpid()),
        "vulkan_imported": vk,
        "dll": VK,
        "dll_sha16": dll_sha,
        "gpu": ngl,
        "n_ctx": NCTX,
        "n_seq": NSEQ,
        "kv": "q8_0",
        "child_pid": os.getpid(),
        "answer_head": (ans or "")[:80],
        "ok": bool(vk and n_pref > 0),
    }
    tmp = str(tier_path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    os.replace(tmp, tier_path)
    print("VRAM_RESULT " + json.dumps(res, ensure_ascii=False), flush=True)
    eng.close()

def sampler_start(flag):
    return subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PS1),
         "-Flag", str(flag)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
        errors="replace")

def parse_tier(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None

def write_artifact(tiers, baseline, aborted, abort_at, started):
    obj = {
        "schema": "m7_vram_ramp_v1",
        "task": "M7-VRAM-RAMP 14B Vulkan 专用显存爬坡 32/36/40",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "started": started,
        "model": MODEL,
        "model_bytes": os.path.getsize(MODEL),
        "geometry": {"n_ctx": NCTX, "n_seq": NSEQ, "kv": "q8_0", "chat_start": 4096,
                     "blocks": 48, "embd": 5120, "heads": 40, "kv_heads": 8,
                     "ff": 13824, "head_dim": 128},
        "gpu": {"name": "AMD Radeon RX 6750 GRE 10GB", "driver": "32.0.21045.1000"},
        "dll": {"vulkan": VK, "vulkan_sha16": sha16(VK), "vulkan_bytes": os.path.getsize(VK),
                "cpu": CPU, "cpu_sha16": sha16(CPU), "cpu_bytes": os.path.getsize(CPU)},
        "env": {"n_gpu_layers_tiers": TIERS, "sampling_interval_ms": 100,
                "gate_gib": GATE_GIB, "target_gib": TARGET_GIB,
                "KVSHIM_THREADS": os.environ.get("KVSHIM_THREADS")},
        "baseline_gib": baseline,
        "tiers": tiers,
        "aborted": aborted,
        "abort_at": abort_at,
        "conclusion_max_layers_le_8_0": None,
        "boundary": "本测量只回答显存占用，不构成任何 GPU 正确性结论；E3-GPU 仍为 未做。GPU DLL provenance 与 CPU 臂分离（GPU=9edbafa1 ↔ 旧源码 51eb2adb）。",
        "no_self_sha": True,
    }
    ok = [t for t in tiers if t.get("ok") and t.get("vram_peak_gib") is not None
          and t["vram_peak_gib"] <= TARGET_GIB]
    obj["conclusion_max_layers_le_8_0"] = max([t["n_gpu_layers"] for t in ok], default=None)
    tmp = str(ART) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ART)
    return obj

def parent():
    OUT.mkdir(parents=True, exist_ok=True)
    assert Path(VK).exists() and Path(CPU).exists()
    assert sha16(VK) == "9edbafa150700614", "Vulkan DLL changed: " + sha16(VK)
    baseline = sample_once()
    tiers = []
    aborted, abort_at = False, None
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    for ngl in TIERS:
        flag = OUT / ("_vram_stop_%d.flag" % ngl)
        tier_path = OUT / ("_vram_tier_%d.json" % ngl)
        for f in (flag, Path(str(tier_path) + ".tmp")):
            try: f.unlink()
            except FileNotFoundError: pass
        try: tier_path.unlink()
        except FileNotFoundError: pass
        sampler = sampler_start(flag)
        env = {**os.environ, "M7_VRAM_NGL": str(ngl), "M7_VRAM_OUT": str(tier_path)}
        child_p = subprocess.Popen([sys.executable, "-X", "utf8", os.path.abspath(__file__),
                                    "child"], env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                   errors="replace")
        timed_out = False
        try:
            out, err = child_p.communicate(timeout=600)
        except subprocess.TimeoutExpired:
            timed_out = True
            out, err = "", "TIMEOUT waiting for child; no signal sent"
        flag.write_text("stop", encoding="utf-8")
        try:
            s_out, s_err = sampler.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            s_out, s_err = "", "sampler timeout"
        peak, samples = None, None
        try:
            j = json.loads(s_out.strip().splitlines()[-1])
            peak, samples = j.get("peak_bytes"), j.get("samples")
        except Exception:
            pass
        tier = parse_tier(tier_path) or {}
        tier["n_gpu_layers"] = ngl
        tier["vram_peak_gib"] = round(peak / 1073741824.0, 4) if peak else None
        tier["baseline_gib"] = baseline
        tier["sampler"] = {"samples": samples, "stderr_tail": (s_err or "").splitlines()[-2:],
                           "stdout_tail": (s_out or "").splitlines()[-2:]}
        tier["rc"] = child_p.returncode
        tier["timed_out"] = timed_out
        tier["child_stderr_tail"] = (err or "").splitlines()[-4:]
        if tier.get("vram_peak_gib") is None:
            tier["ok"] = False
            tier["error"] = "no VRAM sample"
        if tier.get("vulkan_imported") is not True:
            tier["ok"] = False
            tier["error"] = "未接上: vulkan_imported false"
        tiers.append(tier)
        write_artifact(tiers, baseline, aborted, abort_at, started)
        print("TIER " + json.dumps({k: tier.get(k) for k in ("n_gpu_layers", "vram_peak_gib",
              "load_s", "prefill_tok_s", "decode_tok_s", "process_ws_mb", "vulkan_imported",
              "ok", "rc", "timed_out")}, ensure_ascii=False), flush=True)
        if tier.get("vram_peak_gib") is not None and tier["vram_peak_gib"] > GATE_GIB:
            aborted, abort_at = True, ngl
            write_artifact(tiers, baseline, aborted, abort_at, started)
            break

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "child":
        child()
    else:
        parent()
