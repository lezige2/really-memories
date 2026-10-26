#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M7 E3-GPU (a) no-kill arm -- actual runner.

Frozen prereg: kvmem/m2_visibility/m7/PREREG-M7-E3-GPU.md
  full-file sha16 e75a425b7ef15201 / 8,833 B; self rule d7f71236038527db.

Parent rules:
  * never sends a signal to the GPU child (no Popen.kill/terminate, taskkill,
    Stop-Process, GenerateConsoleCtrlEvent);
  * one child process per scenario; stop is only the file `_e3gpu_stop.flag`;
  * <=900 s per scenario: on timeout only write the flag, then
    communicate(timeout=120); hung leave un-killed and do not start more;
  * 100 ms dedicated-VRAM sampler; peak >8.6 GiB -> flag + aborted=true.

Child rules:
  * polls `_e3gpu_stop.flag` every 200 ms (watcher thread) and exits normally;
  * real 14B/vulkan child, `n_gpu_layers=36`, `n_ctx=8192`, `n_seq=8`, `kv=q8_0`;
  * the DLL's own llama log callback is re-installed only to capture the real
    `offloaded N/M layers to GPU` line; the DLL is not modified/rebuilt.
"""
import ctypes
import glob
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
TOOLS = ROOT / "tools"
M7 = ROOT / "kvmem/m2_visibility/m7"
OUT = M7 / "out"
TMP = OUT / "tmp" / "e3gpu"
MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
MODEL_BYTES = 8988110240
VK = str(TOOLS / "kvshim_vk.dll")
CPU = str(TOOLS / "kvshim.dll")
PROFILE = str(ROOT / "kvmem/blocks/profile.kvmem")
DB = str(ROOT / "kvmem/chat.db")
VK_SHA16 = "9edbafa150700614"
VK_BYTES = 50007552
NGL, NCTX, NSEQ, KV, CHAT_START = 36, 8192, 8, "q8_0", 4096
GATE_GIB = 8.6
SCENARIO_TIMEOUT = 900
STOP = OUT / "_e3gpu_stop.flag"
PEAK = OUT / "_e3gpu_peak.txt"
SAMPLER = OUT / "_e3gpu_sampler.ps1"
ART = OUT / "M7-E3-GPU.json"
LANDED = M7 / "LANDED-m7-e3-gpu.json"
AUDIT = ROOT / "docs/_work/INSPECTOR-M7-E3GPU-AUDIT.md"
AUDIT_SHA = "e6a58bf315680610"
OLD_M7_SHA16 = "36c5bf21bcfee9c9"
OLD_M7_BYTES = 14400
OLD_LANDED_SHA16 = "09e767fed6a2687f"
OLD_LANDED_BYTES = 4662
PREREG = M7 / "PREREG-M7-E3-GPU.md"
PREREG_SHA = "e75a425b7ef15201"

_CB_REF = None
_LOG_LINES = []


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def sz(path):
    return os.path.getsize(path) if os.path.exists(path) else None


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def free_ram_kb():
    class ME(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = ME(); m.dwLength = ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return int(m.ullAvailPhys // 1024)


def vulkan_loaded():
    k = ctypes.windll.kernel32
    k.GetModuleHandleW.restype = ctypes.c_void_p
    return bool(k.GetModuleHandleW("vulkan-1.dll"))


def ps(cmd, timeout=40):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return (r.stdout or "").strip().splitlines()


def gate_values():
    pnp = 0
    for x in ps("$p=Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | ? { $_.FriendlyName -match 'RNDIS|Remote NDIS|USB Audio|USB 音频' }; @($p).Count"):
        if x.strip().isdigit():
            pnp = int(x.strip())
    vram = None
    for x in ps("$m=Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -ErrorAction SilentlyContinue | Measure-Object -Property DedicatedUsage -Sum; [math]::Round($m.Sum/1GB,4)"):
        try:
            vram = float(x.strip())
        except ValueError:
            pass
    free_kb = None
    boot = None
    for x in ps("$o=Get-CimInstance Win32_OperatingSystem; \"FREE=\"+$o.FreePhysicalMemory; \"BOOT=\"+$o.LastBootUpTime.ToString('o')"):
        if x.startswith("FREE="):
            free_kb = int(x.split("=", 1)[1])
        elif x.startswith("BOOT="):
            boot = x.split("=", 1)[1]
    gpu_procs = 0
    for x in ps("$g=Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory -ErrorAction SilentlyContinue | ? { $_.DedicatedUsage -gt 268435456 }; @($g).Count"):
        if x.strip().isdigit():
            gpu_procs = int(x.strip())
    browser = 0
    for x in ps("$b=Get-Process chrome,msedge,firefox,opera,brave,Discord,obs64,Code -ErrorAction SilentlyContinue; @($b).Count"):
        if x.strip().isdigit():
            browser = int(x.strip())
    return {"pnp_rndis_usb_audio": pnp, "vram_baseline_gib": vram,
            "free_ram_kb": free_kb, "gpu_procs_gt256mb": gpu_procs,
            "browser_or_code_procs": browser, "boot_id": boot}


def residual_results():
    # Raw child logs and the two deliverable artifacts are intentionally present
    # on a re-run; only stray stop/peak/scratch JSON count as residue.
    pats = ["_e3gpu_stop.flag", "_e3gpu_peak*.txt", "_e3gpu_*.json"]
    out = []
    for p in pats:
        out += glob.glob(str(M7 / p)) + glob.glob(str(OUT / p))
    return sorted(set(out))


HOST_CMD_DUMP = (
    "Get-ChildItem -LiteralPath 'C:\\Windows\\Minidump' -Filter '*.dmp' "
    "-File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | "
    "Select-Object Name,Length,@{n='LastWriteTime';e={$_.LastWriteTime.ToString('o')}} "
    "| ConvertTo-Json -Compress"
)
HOST_CMD_BOOT = "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString('o')"


def _ps_raw(cmd):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=45)
    return {"command": cmd, "rc": r.returncode,
            "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "stdout": (r.stdout or "").strip(),
            "stderr": (r.stderr or "").strip()}


def host_check(tag):
    """B2: actually execute Minidump and LastBootUpTime queries and keep raw I/O."""
    boot = _ps_raw(HOST_CMD_BOOT)
    dump = _ps_raw(HOST_CMD_DUMP)
    boot_id = boot["stdout"].strip() or None
    dumps = []
    raw = dump["stdout"].strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                parsed = [parsed]
            for x in parsed or []:
                dumps.append({"name": x.get("Name"), "bytes": x.get("Length"),
                              "mtime": x.get("LastWriteTime")})
        except Exception as e:  # noqa: BLE001
            dump["parse_error"] = type(e).__name__ + ": " + str(e)
    dumps.sort(key=lambda x: (x.get("mtime") or "", x.get("name") or ""))
    return {"tag": tag,
            "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "boot": boot, "minidump": dump,
            "parsed": {"boot_id": boot_id, "dumps": dumps,
                       "existing_count": len(dumps),
                       "latest_mtime": dumps[-1]["mtime"] if dumps else None}}


def derive_host_state(before, after):
    b = {x["name"]: (x["bytes"], x["mtime"]) for x in before["parsed"]["dumps"]}
    a = {x["name"]: (x["bytes"], x["mtime"]) for x in after["parsed"]["dumps"]}
    new = [{"name": k, "bytes": v[0], "mtime": v[1]}
           for k, v in a.items() if k not in b or b[k] != v]
    return {"boot_id_before": before["parsed"]["boot_id"],
            "boot_id_after": after["parsed"]["boot_id"],
            "minidump_before_count": before["parsed"]["existing_count"],
            "minidump_existing_count": after["parsed"]["existing_count"],
            "minidump_latest_mtime": after["parsed"]["latest_mtime"],
            "minidump_new": bool(new), "minidump_new_files": new,
            "boot_changed": before["parsed"]["boot_id"] != after["parsed"]["boot_id"]}


BROWSER_LIST = ("Get-Process -Name msedge -ErrorAction SilentlyContinue | "
                "Select-Object Id,MainWindowHandle | ConvertTo-Json -Compress")


def _msedge_state():
    raw = _ps_raw(BROWSER_LIST)
    procs = []
    txt = raw["stdout"].strip()
    if txt:
        try:
            v = json.loads(txt)
            if isinstance(v, dict):
                v = [v]
            for x in v or []:
                procs.append({"pid": x.get("Id"), "main_window_handle": x.get("MainWindowHandle")})
        except Exception as e:  # noqa: BLE001
            raw["parse_error"] = type(e).__name__ + ": " + str(e)
    return procs, raw


def browser_prep():
    """User-authorized B: close only msedge, graceful first, then forced if needed."""
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    before, before_raw = _msedge_state()
    graceful = _ps_raw(
        "(Get-Process -Name msedge -ErrorAction SilentlyContinue | "
        "Where-Object { $_.MainWindowHandle -ne 0 }) | "
        "ForEach-Object { $_.CloseMainWindow() } | Out-Null; Start-Sleep -Seconds 10")
    after_grace, after_grace_raw = _msedge_state()
    force_used = False
    force_raw = None
    if after_grace:
        force_used = True
        force_raw = _ps_raw(
            "Get-Process -Name msedge -ErrorAction SilentlyContinue | Stop-Process -Force")
    after, after_raw = _msedge_state()
    finished = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    return {"action": "close_browsers",
            "authorized_by": "user (ask_user_question option B)",
            "method": "CloseMainWindow→Stop-Process(msedge only)",
            "pids": [x["pid"] for x in before],
            "started_at": started, "finished_at": finished,
            "before_count": len(before), "after_graceful_count": len(after_grace),
            "after_count": len(after), "force_used": force_used,
            "other_processes_touched": False,
            "raw": {"list_before": before_raw, "close_main_window": graceful,
                    "list_after_graceful": after_grace_raw,
                    "force_msedge_only": force_raw, "list_after": after_raw}}


# ---------------------------------------------------------------- child

def _install_logger(dll):
    """Re-install llama's own log callback after kvshim_init_log() set quiet_log.

    This calls the same `llama_log_set` inside the fixed DLL (RVA 0x28320) via
    its address; the DLL file is not modified.  Only used to capture the real
    `offloaded N/M layers to GPU` line.
    """
    global _CB_REF
    k = ctypes.windll.kernel32
    k.GetModuleHandleW.restype = ctypes.c_void_p
    base = k.GetModuleHandleW("kvshim_vk.dll")
    if not base:
        raise RuntimeError("cannot get kvshim_vk.dll base")
    proto = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)
    log_set = proto(base + 0x28320)  # llama_log_set from this exact DLL

    def cb(level, text, user):
        try:
            s = text.decode("utf-8", "replace") if text else ""
            if s:
                _LOG_LINES.append(s)
                log_path = os.environ.get("M7_E3GPU_LOG", str(OUT / "_e3gpu_llama.log"))
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(s)
        except Exception:
            pass

    _CB_REF = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)(cb)
    log_set(ctypes.cast(_CB_REF, ctypes.c_void_p), None)


def open_engine():
    sys.path.insert(0, str(TOOLS))
    import kvslots
    if sha16(VK) != VK_SHA16:
        raise RuntimeError("GPU DLL changed: " + sha16(VK))
    L = ctypes.WinDLL(VK)
    L.kvshim_init_log.restype = None
    L.kvshim_free_log.restype = None
    L.kvshim_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    L.kvshim_open.restype = ctypes.c_void_p
    L.kvshim_close.argtypes = [ctypes.c_void_p]
    L.kvshim_n_tokens.argtypes = [ctypes.c_void_p, ctypes.c_int]
    L.kvshim_n_tokens.restype = ctypes.c_int
    L.kvshim_pos_max.argtypes = [ctypes.c_void_p, ctypes.c_int]
    L.kvshim_pos_max.restype = ctypes.c_int
    L.kvshim_reset.argtypes = [ctypes.c_void_p, ctypes.c_int]
    L.kvshim_write_at.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
    L.kvshim_write_at.restype = ctypes.c_int
    L.kvshim_save.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
    L.kvshim_save.restype = ctypes.c_longlong
    L.kvshim_load.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
    L.kvshim_load.restype = ctypes.c_int
    L.kvshim_seq_cp.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    L.kvshim_seq_rm.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    L.kvshim_repos_local.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    L.kvshim_repos_local.restype = ctypes.c_int
    L.kvshim_init_log()
    _install_logger(L)
    h = L.kvshim_open(MODEL.encode("utf-8"), NCTX, NSEQ, NGL, 1 if KV == "q8_0" else 0)
    if not h:
        raise RuntimeError("kvshim_open failed")
    eng = object.__new__(kvslots.KVEngine)
    eng.lib = L
    eng.h = h
    eng.n_seq = NSEQ
    eng.n_ctx = NCTX
    return eng


def connect_ro():
    con_uri = "file:" + DB.replace("\\", "/") + "?mode=ro"
    return sqlite3.connect(con_uri, uri=True)


def stop_watcher():
    ev = threading.Event()

    def loop():
        while not ev.is_set():
            if STOP.exists():
                return
            time.sleep(0.2)

    th = threading.Thread(target=loop, daemon=True)
    th.start()
    return ev, th


def stopped():
    return STOP.exists()


def build_chat_189(eng):
    candidates = [("a " * 189).strip(), "a" * 189, ("the " * 189).strip(),
                  ("hello " * 189).strip()]
    best = None
    for text in candidates:
        eng.reset(0)
        n = eng.write_at(0, text, CHAT_START, False)
        if best is None or abs(n - 189) < abs(best[0] - 189):
            best = (n, eng.pos_max(0))
        if n == 189:
            return n, eng.pos_max(0)
    return best


def setup_profile_block(eng):
    npf = eng.load(1, PROFILE)
    moved = eng.repos_local(1, 4046, 0, npf)
    ppos = eng.pos_max(1)
    lo = ppos - npf + 1
    if moved != npf or lo != 4046:
        raise RuntimeError("profile reposition moved=%s lo=%s npf=%s" % (moved, lo, npf))
    eng.share(1, 0, lo, ppos + 1)
    return {"name": "profile", "seq": 1, "source_id": 1, "role": "memory",
            "lo": lo, "hi": ppos + 1, "n_tokens": npf, "path": PROFILE}


def meta_from_log(eng, t0):
    txt = "".join(_LOG_LINES)
    m = re.search(r"offloaded (\d+)/(\d+) layers to GPU", txt)
    first = int(m.group(1)) if m else None
    second = int(m.group(2)) if m else None
    return {"pid": os.getpid(), "load_s": round(time.perf_counter() - t0, 3),
            "vulkan_imported": vulkan_loaded(), "dll_sha16": sha16(VK),
            "n_gpu_layers_input": NGL, "n_gpu_layers_readback": first,
            "n_gpu_layers_readback_total": second,
            "offloaded_log_line": m.group(0) if m else None,
            "gpu": NGL, "n_ctx": NCTX, "n_seq": NSEQ, "kv": KV,
            "model_bytes": sz(MODEL)}


def child(mode):
    ev, th = stop_watcher()
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    eng = open_engine()
    meta = meta_from_log(eng, t0)
    print("E3META " + json.dumps(meta, ensure_ascii=False), flush=True)
    try:
        if stopped():
            print("E3RESULT " + json.dumps({"mode": mode, "status": "stopped_after_load"}), flush=True)
            return 0
        tdir = TMP
        if mode == "s1_save":
            nchat, pos = build_chat_189(eng)
            if nchat != 189:
                raise RuntimeError("chat expected 189 tokens, got %s" % nchat)
            block = setup_profile_block(eng)
            target = str(tdir / "s1.json")
            print("E3SAVE_START " + target, flush=True)
            sys.path.insert(0, str(TOOLS))
            import session_state as ss
            buf = io.StringIO()
            import contextlib
            with contextlib.redirect_stderr(buf):
                man = ss.save_session(eng, None, target, [block], CHAT_START, model_path=MODEL)
            chat = os.path.splitext(os.path.abspath(target))[0] + ".chat.kvmem"
            print("E3SAVE_DONE", flush=True)
            # S4: copy the self-made 14B fixture under its own name.
            s4man = str(tdir / "s4.json")
            s4chat = str(tdir / "s4.chat.kvmem")
            shutil.copyfile(target, s4man)
            shutil.copyfile(chat, s4chat)
            mm = json.load(open(s4man, encoding="utf-8"))
            mm["chat"]["state"] = os.path.basename(s4chat)
            mm["saved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            with open(s4man, "w", encoding="utf-8") as f:
                json.dump(mm, f, ensure_ascii=False, indent=2)
            res = {"mode": mode, "load_s": meta["load_s"], "prefill_n": nchat,
                   "prefill_pos_max": pos, "profile_n_tokens": block["n_tokens"],
                   "profile_lo": block["lo"], "profile_hi": block["hi"],
                   "chat_n_tokens": nchat, "chat_sha16": sha16(chat),
                   "chat_bytes": sz(chat), "manifest": target,
                   "manifest_sha16": sha16(target),
                   "manifest_chat_bytes": man.get("chat", {}).get("bytes"),
                   "manifest_chat_n_tokens": man.get("chat", {}).get("n_tokens"),
                   "save_events": len(buf.getvalue().splitlines()),
                   "s4_manifest": s4man, "s4_chat": s4chat,
                   "s4_bytes": sz(s4chat), "s4_sha16": sha16(s4chat),
                   "vulkan_imported": meta["vulkan_imported"]}
            print("E3RESULT " + json.dumps(res, ensure_ascii=False), flush=True)
        elif mode == "s1_load":
            sys.path.insert(0, str(TOOLS))
            import session_state as ss
            target = str(tdir / "s1.json")
            chat = os.path.splitext(os.path.abspath(target))[0] + ".chat.kvmem"
            con = connect_ro()
            buf = io.StringIO()
            import contextlib
            with contextlib.redirect_stderr(buf):
                rep = ss.restore_session(eng, con, target, model_path=MODEL)
            ev_lines = [x for x in buf.getvalue().splitlines() if x.strip()]
            res = {"mode": mode, "load_ok": True, "events": len(ev_lines),
                   "event_lines": ev_lines,
                   "chat_n_tokens": eng.n_tokens(0), "chat_pos_max": eng.pos_max(0),
                   "chat_sha16": sha16(chat), "chat_bytes": sz(chat),
                   "manifest_chat_bytes": json.load(open(target, encoding="utf-8"))["chat"].get("bytes"),
                   "manifest_chat_n_tokens": rep.get("chat_n_tokens"),
                   "report_chat_end": rep.get("chat_end"),
                   "report_anchor": rep.get("anchor")}
            print("E3RESULT " + json.dumps(res, ensure_ascii=False), flush=True)
            con.close()
        elif mode == "s2_tail":
            sys.path.insert(0, str(TOOLS))
            import session_state as ss
            tail_man = str(tdir / "s2_tail.json")
            tail_chat = str(tdir / "s2_tail.chat.kvmem")
            base_man = str(tdir / "s1.json")
            base_chat = str(tdir / "s1.chat.kvmem")
            shutil.copyfile(base_chat, tail_chat)
            with open(tail_chat, "ab") as f:
                f.write(b"\x00" * 1024)
            mm = json.load(open(base_man, encoding="utf-8"))
            mm["chat"]["state"] = os.path.basename(tail_chat)
            with open(tail_man, "w", encoding="utf-8") as f:
                json.dump(mm, f, ensure_ascii=False, indent=2)
            # sentinel: 7 tokens at 0..6
            eng.reset(0)
            sent_n = eng.write_at(0, "a a a a a a a", 0, False)
            sent_pos = eng.pos_max(0)
            reset_calls, load_calls = [], []
            orig_reset, orig_load, orig_load_strict = eng.reset, eng.load, eng.load_strict
            def r_reset(seq):
                reset_calls.append(int(seq)); return orig_reset(seq)
            def r_load(seq, path):
                load_calls.append((int(seq), os.path.basename(path))); return orig_load(seq, path)
            def r_load_strict(seq, path):
                load_calls.append((int(seq), os.path.basename(path))); return orig_load_strict(seq, path)
            eng.reset, eng.load, eng.load_strict = r_reset, r_load, r_load_strict
            before = {"n_tokens": eng.n_tokens(0), "pos_max": eng.pos_max(0),
                      "reset_calls": len(reset_calls), "load_calls": len(load_calls)}
            err = None
            con = connect_ro()
            try:
                ss.restore_session(eng, con, tail_man, model_path=MODEL)
            except Exception as e:  # noqa: BLE001
                err = type(e).__name__ + ": " + str(e)
            after = {"n_tokens": eng.n_tokens(0), "pos_max": eng.pos_max(0),
                     "reset_calls": len(reset_calls), "load_calls": len(load_calls)}
            con.close()
            res = {"mode": mode, "manifest": tail_man, "chat": tail_chat,
                   "manifest_chat_bytes": mm["chat"].get("bytes"), "chat_bytes": sz(tail_chat),
                   "sentinel_n_tokens": sent_n, "sentinel_pos_max": sent_pos,
                   "before": before, "after": after, "exc": err,
                   "expected_exc": "LayoutMismatch",
                   "pass": bool(err and "LayoutMismatch" in err
                                and after["reset_calls"] == 0
                                and (before["n_tokens"], before["pos_max"]) == (after["n_tokens"], after["pos_max"]))}
            print("E3RESULT " + json.dumps(res, ensure_ascii=False), flush=True)
        elif mode == "s3_old":
            sys.path.insert(0, str(TOOLS))
            import session_state as ss
            old_man = str(tdir / "s3_old.json")
            old_chat = str(tdir / "s3_old.chat.kvmem")
            base_man = str(tdir / "s1.json")
            base_chat = str(tdir / "s1.chat.kvmem")
            shutil.copyfile(base_chat, old_chat)
            mm = json.load(open(base_man, encoding="utf-8"))
            mm["chat"].pop("bytes", None)
            mm["chat"]["state"] = os.path.basename(old_chat)
            with open(old_man, "w", encoding="utf-8") as f:
                json.dump(mm, f, ensure_ascii=False, indent=2)
            con = connect_ro()
            import contextlib
            buf = io.StringIO()
            old_ok = None
            old_exc = None
            with contextlib.redirect_stderr(buf):
                try:
                    rep_old = ss.restore_session(eng, con, old_man, model_path=MODEL)
                    old_ok = True
                except Exception as e:  # noqa: BLE001
                    old_exc = type(e).__name__ + ": " + str(e)
            ev_old = [x for x in buf.getvalue().splitlines() if x.strip()]
            buf2 = io.StringIO()
            orig_ok = None
            with contextlib.redirect_stderr(buf2):
                try:
                    rep_orig = ss.restore_session(eng, con, base_man, model_path=MODEL)
                    orig_ok = True
                except Exception as e:  # noqa: BLE001
                    orig_ok = False
            ev_orig = [x for x in buf2.getvalue().splitlines() if x.strip()]
            con.close()
            res = {"mode": mode, "old_manifest": old_man, "old_chat": old_chat,
                   "manifest_chat_bytes": None, "old_load_ok": old_ok, "old_exc": old_exc,
                   "events": len(ev_old), "event_lines": ev_old,
                   "unvalidated_chat_bytes": (rep_old or {}).get("unvalidated_chat_bytes") if old_ok else None,
                   "original_load_ok": orig_ok, "original_events": len(ev_orig),
                   "original_event_lines": ev_orig,
                   "pass": bool(old_ok and len(ev_old) == 1 and orig_ok and len(ev_orig) == 0)}
            print("E3RESULT " + json.dumps(res, ensure_ascii=False), flush=True)
        elif mode == "s4_fixture":
            sys.path.insert(0, str(TOOLS))
            import session_state as ss
            con = connect_ro()
            import contextlib
            buf = io.StringIO()
            ok = None
            exc = None
            with contextlib.redirect_stderr(buf):
                try:
                    rep = ss.restore_session(eng, con, str(tdir / "s4.json"), model_path=MODEL)
                    ok = True
                except Exception as e:  # noqa: BLE001
                    exc = type(e).__name__ + ": " + str(e)
            ev_lines = [x for x in buf.getvalue().splitlines() if x.strip()]
            con.close()
            res = {"mode": mode, "load_ok": ok, "exc": exc,
                   "chat_bytes_verified": (rep or {}).get("chat_bytes_verified") if ok else None,
                   "events": len(ev_lines), "event_lines": ev_lines,
                   "fixture_independence": "S4 = S1 产物改名，不是独立 fixture",
                   "pass": bool(ok and (rep or {}).get("chat_bytes_verified") is True and len(ev_lines) == 0)}
            print("E3RESULT " + json.dumps(res, ensure_ascii=False), flush=True)
        else:
            raise RuntimeError("unknown mode " + mode)
        return 0
    finally:
        try:
            eng.close()
        except Exception:
            pass
        ev.set()


# ---------------------------------------------------------------- parent

def sample_peak(peak_path):
    try:
        return float(peak_path.read_text(encoding="utf-8").strip())
    except Exception:
        return 0.0


def sampler_start(peak_path):
    return subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(SAMPLER), "-Flag", str(STOP), "-Out", str(peak_path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace")


def parse_pref(out, pref):
    for line in (out or "").splitlines():
        if line.startswith(pref + " "):
            return json.loads(line[len(pref) + 1:])
    return None


def run_child(mode, scenario, watch_targets=None):
    peak_path = OUT / ("_e3gpu_peak_%s.txt" % scenario)
    log_path = OUT / ("_e3gpu_log_%s.log" % scenario)
    try:
        STOP.unlink()
    except FileNotFoundError:
        pass
    try:
        peak_path.unlink()
    except FileNotFoundError:
        pass
    # B3: append-only per-child log; never delete/truncate before the child.
    log_path.touch(exist_ok=True)
    tmp_seen = []
    seen_lock = threading.Lock()
    wstop = threading.Event()

    def watcher():
        while not wstop.is_set():
            for pat in ("*.tmp-*", "*.tmp"):
                for x in glob.glob(str(OUT / "tmp" / "e3gpu" / pat)):
                    with seen_lock:
                        if x not in tmp_seen:
                            tmp_seen.append(x)
            time.sleep(0.02)

    wth = None
    if watch_targets:
        wth = threading.Thread(target=watcher, daemon=True)
        wth.start()
    target_existed_before = (os.path.exists(str(OUT / "tmp" / "e3gpu" / "s1.json"))
                             if watch_targets else None)
    sampler = sampler_start(peak_path)
    time.sleep(0.15)
    env = {**os.environ,
           "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
           "KV_ACCEPT_GPU_KILL_RISK": "1",
           "M7_E3GPU_MODE": mode, "M7_E3GPU_SCENARIO": scenario,
           "M7_E3GPU_LOG": str(log_path)}
    child = subprocess.Popen(
        [sys.executable, "-X", "utf8", os.path.abspath(__file__), "child", mode],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
        errors="replace", creationflags=0x00004000, env=env)
    t0 = time.perf_counter()
    deadline = t0 + SCENARIO_TIMEOUT
    timed_out = False
    aborted = False
    hung = False
    out = err = None
    while True:
        rc = child.poll()
        peak = sample_peak(peak_path)
        if peak and peak / (1024 ** 3) > GATE_GIB and not aborted:
            aborted = True
            STOP.write_text("vram_gate %.4f GiB" % (peak / (1024 ** 3)), encoding="utf-8")
        if time.monotonic() > deadline and not timed_out:
            timed_out = True
            STOP.write_text("scenario_timeout_900s", encoding="utf-8")
        if rc is not None:
            out, err = child.communicate()
            break
        if timed_out:
            # no signal: give self-exit a bounded window, then record hung
            try:
                out, err = child.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                hung = True
                break
            break
        time.sleep(0.1)
    elapsed = round(time.perf_counter() - t0, 2)
    STOP.write_text("scenario_done", encoding="utf-8")
    try:
        sampler.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        pass
    wstop.set()
    if wth:
        wth.join(timeout=1)
    peak_bytes = sample_peak(peak_path)
    meta = parse_pref(out, "E3META")
    res = parse_pref(out, "E3RESULT")
    tmp_clean = not glob.glob(str(OUT / "tmp" / "e3gpu" / "*.tmp-*")) and \
                not glob.glob(str(OUT / "tmp" / "e3gpu" / "*.tmp"))
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    off = re.search(r"offloaded (\d+)/(\d+) layers to GPU", log_text)
    return {"scenario": scenario, "mode": mode, "child_pid": child.pid,
            "rc": child.returncode, "elapsed_s": elapsed,
            "timeout": timed_out, "hung": hung, "aborted": aborted,
            "vram_peak_gib": round(peak_bytes / (1024 ** 3), 4) if peak_bytes else None,
            "meta": meta, "result": res, "stdout_tail": (out or "").splitlines()[-4:],
            "stderr_tail": (err or "").splitlines()[-8:],
            "raw_log": {"path": str(log_path), "sha16": sha16(log_path) if log_path.exists() else None,
                        "bytes": sz(log_path), "mode": "append_only_no_predelete"},
            "offloaded_log_line": off.group(0) if off else None,
            "peak_file": {"path": str(peak_path),
                          "sha16": sha16(peak_path) if peak_path.exists() else None,
                          "bytes": sz(peak_path)},
            "atomic_shape": {"tmp_seen": bool(tmp_seen),
                             "tmp_pattern": [os.path.basename(x) for x in tmp_seen],
                             "tmp_cleaned_after": tmp_clean,
                             "target_existed_before": target_existed_before},
            "stop_flag": STOP.read_text(encoding="utf-8") if STOP.exists() else None}


def _old_file(path):
    if not path.exists():
        return None
    b = path.read_bytes()
    return {"path": str(path), "sha16": hashlib.sha256(b).hexdigest()[:16], "bytes": len(b)}


def parent():
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    try:
        STOP.unlink()
    except FileNotFoundError:
        pass
    try:
        (OUT / "_e3gpu_peak.txt").unlink()
    except FileNotFoundError:
        pass
    old_m7 = _old_file(ART)
    old_landed = _old_file(LANDED)
    run_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    device_prep = browser_prep()
    host_before = host_check("before")
    gates = gate_values()
    # B2: boot identity is taken from host_check's raw LastBootUpTime output.
    gates["boot_id"] = host_before["parsed"]["boot_id"]
    residual = residual_results()
    gates["residual_results"] = residual
    gates["residual_count"] = len(residual)
    gates["prereg_sha16"] = sha16(PREREG)
    gates["prereg_sha_ok"] = gates["prereg_sha16"] == PREREG_SHA
    gates["dll_sha16"] = sha16(VK)
    gates["dll_bytes"] = sz(VK)
    gates["dll_ok"] = gates["dll_sha16"] == VK_SHA16 and gates["dll_bytes"] == VK_BYTES
    gates["model_bytes"] = sz(MODEL)
    gates["model_ok"] = gates["model_bytes"] == MODEL_BYTES
    gates["free_ram_ok"] = (gates.get("free_ram_kb") or 0) >= 8388608
    gates["vram_baseline_ok"] = gates.get("vram_baseline_gib") is not None and gates["vram_baseline_gib"] <= 0.6
    gates["pnp_ok"] = gates.get("pnp_rndis_usb_audio") == 0
    gates["gpu_procs_ok"] = gates.get("gpu_procs_gt256mb") == 0
    gates["browsers_ok"] = gates.get("browser_or_code_procs") == 0
    gates["residual_ok"] = gates["residual_count"] == 0
    gate_ok = all(gates[k] for k in ("dll_ok", "model_ok", "free_ram_ok",
                                     "vram_baseline_ok", "pnp_ok", "gpu_procs_ok",
                                     "browsers_ok", "prereg_sha_ok", "residual_ok"))
    art = {"schema": "m7_e3_gpu_v1",
           "task": "M7 E3-GPU (a) 无 kill 子臂 14B Vulkan 36 层",
           "at": run_at,
           "scope": "只覆盖无 kill 子臂，不得借用 CPU 臂结论",
           "kill_arm": "未做（主机不安全）",
           "freeze": {"prereg_sha16": gates["prereg_sha16"], "prereg_bytes": sz(PREREG),
                      "expected_prereg_sha16": PREREG_SHA,
                      "prereg_self_sha16_rule": "d7f71236038527db"},
           "hash_semantics": {
               "chat_sha16": "两侧 sha 均由文件字节（sha256(file)）算出；不是引擎加载后内容哈希",
               "s1_scope": "S1 只证结构往返（文件字节未被改写 + 引擎 n_tokens/pos_max 一致 + events=0），不证 KV 语义往返；无 decode/输出对比"},
           "s4_fixture_note": "S4 = S1 产物改名，不是独立 fixture；只验证带 bytes 的正常 load。",
           "device_prep": device_prep,
           "device_prep_note": "device_prep 是用户授权的浏览器关闭准备动作，不属于 GPU child 信号；signals_sent_by_parent 仍只描述 GPU child。",
           "host_check": {"before": host_before, "after": None},
           "attempts": [
               {"attempt": 1, "at": "2026-10-26T08:04:00+08:00", "status": "failed",
                "error": "ctypes.ArgumentError: argument 1: OverflowError: int too long to convert（手工 engine 未设 kvshim_seq_rm.argtypes）",
                "artifacts": [], "readings_used": False,
                "note": "守护器自检失败；无有效产物，无失败读数进入本次最终四场景"},
               {"attempt": 2, "at": run_at, "status": "running",
                "artifacts": [str(ART), str(LANDED)], "readings_used": True,
                "note": "本次重跑；B1–B3 修复后只使用本轮读数"}],
           "corrections": [{
               "artifact": "M7-E3-GPU.json",
               "old_sha16": OLD_M7_SHA16,
               "old_bytes": OLD_M7_BYTES,
               "new_sha16": "见 LANDED-m7-e3-gpu.json corrections[0].new_sha16（写入后自哈希，避免自指）",
               "audit_sha16": AUDIT_SHA, "audit_bytes": sz(AUDIT),
               "changes": ["B1: host_safety.bsod_incidents 3->5 + 5 份 dump 枚举",
                            "B2: host_check() 实跑 Minidump/LastBootUpTime 并保留命令+原始输出+时间",
                            "B3: 每 child 独立 _e3gpu_log_<scenario>.log（append，不删不覆盖）",
                            "G8: 每场景独立 peak 文件", "G5: S4 明写为 S1 副本改名",
                            "G3: 明写 chat_sha16 为文件字节哈希", "G7: attempts[] 记录 attempt#1 失败"]}],
           "device": {"qualified": gate_ok, "gate": gates,
                      "boot_id_before": host_before["parsed"]["boot_id"],
                      "geometry": {"n_gpu_layers": NGL, "n_ctx": NCTX, "n_seq": NSEQ,
                                   "kv": KV, "chat_start": CHAT_START},
                      "dll": {"path": VK, "sha16": VK_SHA16, "bytes": VK_BYTES},
                      "cpu_dll_control": {"path": CPU, "sha16": sha16(CPU), "bytes": sz(CPU)},
                      "model": {"path": MODEL, "bytes": MODEL_BYTES},
                      "env": {"KV_ACCEPT_GPU_KILL_RISK": "1",
                              "KVSHIM_THREADS": os.environ.get("KVSHIM_THREADS")},
                      "signals_sent_by_parent": False,
                      "sampler_interval_ms": 100, "vram_gate_gib": GATE_GIB,
                      "s1_offloaded_log_excerpt": None},
           "scenarios": {}, "raw_logs": {}, "peak_files": {},
           "reproducibility": None,
           "reboot": {"voided_by_reboot": False, "boot_id_before": None,
                      "boot_id_after": None, "minidump_new": None,
                      "minidump_new_files": []},
           "conclusion": None,
           "host_safety": {"bsod_incidents": 5,
                           "incidents": [{"seq": 1, "bugcheck": "0xA"}, {"seq": 2, "bugcheck": "0xA"},
                                         {"seq": 3, "bugcheck": "0x44"}, {"seq": 4, "bugcheck": "0x144"},
                                         {"seq": 5, "bugcheck": "0xA"}],
                           "minidump_files": None, "minidump_count": None,
                           "source": "今晚主机 5 次蓝屏（0xA/0xA/0x44/0x144/0xA）；Minidump 现场枚举由 host_check() 生成",
                           "policy": "无 SIGKILL；只置 stop flag；不杀 child"}}

    def finish_host(host_after):
        hs = derive_host_state(host_before, host_after)
        art["host_check"]["after"] = host_after
        art["reboot"].update({"boot_id_before": hs["boot_id_before"],
                              "boot_id_after": hs["boot_id_after"],
                              "voided_by_reboot": hs["boot_changed"],
                              "minidump_new": hs["minidump_new"],
                              "minidump_new_files": hs["minidump_new_files"],
                              "minidump_before_count": hs["minidump_before_count"],
                              "minidump_existing_count": hs["minidump_existing_count"],
                              "minidump_latest_mtime": hs["minidump_latest_mtime"]})
        art["host_safety" ].update({"minidump_files": host_after["parsed"]["dumps"],
                                    "minidump_count": host_after["parsed"]["existing_count"],
                                    "minidump_latest_mtime": host_after["parsed"]["latest_mtime"]})
        art["device"]["boot_id_after"] = hs["boot_id_after"]
        return hs

    if not gate_ok:
        finish_host(host_check("after"))
        for s, exp in (("S1", "正常往返"), ("S2", "tail 注入"), ("S3", "老格式"), ("S4", "S1 副本改名")):
            art["scenarios"][s] = {"expected": exp, "observed": None,
                                   "verdict": "未接上（装置不合格）", "readings": {},
                                   "vram_peak_gib": None, "timeout": False,
                                   "child_pid": None, "rc": None}
        art["conclusion"] = {"S1": "未接上（装置不合格）", "S2": "未接上（装置不合格）",
                             "S3": "未接上（装置不合格）", "S4": "未接上（装置不合格）",
                             "overall": "未接上（装置不合格）", "kill_arm": "未做（主机不安全）"}
        art["attempts"][1]["status"] = "failed_gate"
        write_json_atomic(ART, art)
        try:
            STOP.unlink()
        except FileNotFoundError:
            pass
        print("GATE_FAILED " + json.dumps(gates, ensure_ascii=False))
        return 2

    # one child per scenario; S1 save is watched for atomic shape
    s1s = run_child("s1_save", "S1-save", watch_targets=True)
    art["scenarios"]["S1-save"] = s1s
    art["raw_logs"]["S1-save"] = s1s.get("raw_log")
    art["peak_files"]["S1-save"] = s1s.get("peak_file")
    meta = s1s.get("meta") or {}
    readback_ok = (meta.get("n_gpu_layers_readback") == NGL
                   and meta.get("vulkan_imported") is True
                   and meta.get("dll_sha16") == VK_SHA16)
    art["device"].update({"vulkan_imported": meta.get("vulkan_imported"),
                          "n_gpu_layers_readback": meta.get("n_gpu_layers_readback"),
                          "n_gpu_layers_readback_total": meta.get("n_gpu_layers_readback_total"),
                          "offloaded_log_line": meta.get("offloaded_log_line"),
                          "s1_offloaded_log_excerpt": s1s.get("offloaded_log_line"),
                          "n_gpu_layers_readback_ok": readback_ok,
                          "first_child_pid": meta.get("pid"),
                          "load_s": meta.get("load_s")})
    if not readback_ok:
        finish_host(host_check("after"))
        art["device"]["qualified"] = False
        art["device"]["qualified_reason"] = "日志缺 offloaded 36 行或 vulkan/dll 自证失败"
        art["conclusion"] = {"S1": "未接上（装置不合格）", "S2": "未接上（装置不合格）",
                             "S3": "未接上（装置不合格）", "S4": "未接上（装置不合格）",
                             "overall": "未接上（装置不合格）", "kill_arm": "未做（主机不安全）"}
        art["attempts"][1]["status"] = "failed_readback"
        write_json_atomic(ART, art)
        try:
            STOP.unlink()
        except FileNotFoundError:
            pass
        print("READBACK_FAILED " + json.dumps(meta, ensure_ascii=False))
        return 3

    s1r = s1s.get("result") or {}
    atomic = s1s["atomic_shape"]
    save_ok = bool(s1r.get("chat_bytes") and s1r.get("manifest_chat_bytes") == s1r.get("chat_bytes")
                   and s1r.get("chat_sha16") and s1r.get("manifest_sha16")
                   and atomic.get("tmp_cleaned_after") is True)
    s1_load = run_child("s1_load", "S1-load")
    art["scenarios"]["S1-load"] = s1_load
    art["raw_logs"]["S1-load"] = s1_load.get("raw_log")
    art["peak_files"]["S1-load"] = s1_load.get("peak_file")
    lr = s1_load.get("result") or {}
    s1_ok = bool(save_ok and lr.get("load_ok") is True
                 and lr.get("chat_n_tokens") == s1r.get("chat_n_tokens") == 189
                 and lr.get("chat_pos_max") == s1r.get("prefill_pos_max")
                 and lr.get("chat_sha16") == s1r.get("chat_sha16")
                 and lr.get("events") == 0)
    art["scenarios"]["S1"] = {
        "expected": "save->不同进程 load；n_tokens/pos_max/chat_sha16 三者一致且 events=0；无 kill 原子写形态记录",
        "observed": {"save": s1r, "load": lr, "atomic_shape": atomic},
        "verdict": "通过" if s1_ok else ("未接上" if lr.get("load_ok") is None else "未通过"),
        "readings": {
            "chat_bytes": s1r.get("chat_bytes"), "chat_sha16": s1r.get("chat_sha16"),
            "n_tokens": s1r.get("chat_n_tokens"), "pos_max": s1r.get("prefill_pos_max"),
            "manifest_sha16": s1r.get("manifest_sha16"),
            "load_n_tokens": lr.get("chat_n_tokens"), "load_pos_max": lr.get("chat_pos_max"),
            "events": lr.get("events"),
            "load_chat_sha16": lr.get("chat_sha16"),
            "manifest_chat_bytes_match": s1r.get("manifest_chat_bytes") == s1r.get("chat_bytes"),
            "n_tokens_match": lr.get("chat_n_tokens") == s1r.get("chat_n_tokens") == 189,
            "pos_max_match": lr.get("chat_pos_max") == s1r.get("prefill_pos_max") == 4284,
            "sha_match": lr.get("chat_sha16") == s1r.get("chat_sha16"),
            "events_zero": lr.get("events") == 0,
            "tmp_seen": atomic.get("tmp_seen"),
            "tmp_cleaned_after": atomic.get("tmp_cleaned_after"),
            "target_existed_before": atomic.get("target_existed_before"),
            "s1_raw_log_sha16": (s1s.get("raw_log") or {}).get("sha16"),
            "s1_offloaded_log_line": s1s.get("offloaded_log_line")},
        "vram_peak_gib": max([x for x in (s1s.get("vram_peak_gib"), s1_load.get("vram_peak_gib")) if x] or [None]),
        "timeout": bool(s1s.get("timeout") or s1_load.get("timeout")),
        "child_pid": [s1s.get("child_pid"), s1_load.get("child_pid")],
        "rc": [s1s.get("rc"), s1_load.get("rc")],
        "raw_logs": {"save": s1s.get("raw_log"), "load": s1_load.get("raw_log")},
        "peak_files": {"save": s1s.get("peak_file"), "load": s1_load.get("peak_file")},
        "atomic_shape": atomic}

    def scenario_block(s, expected):
        r = s.get("result") or {}
        art["raw_logs"][s.get("scenario")] = s.get("raw_log")
        art["peak_files"][s.get("scenario")] = s.get("peak_file")
        return {"expected": expected, "observed": r,
                "verdict": "通过" if r.get("pass") else "未通过",
                "readings": r,
                "vram_peak_gib": s.get("vram_peak_gib"), "timeout": s.get("timeout"),
                "child_pid": s.get("child_pid"), "rc": s.get("rc"),
                "raw_log": s.get("raw_log"), "peak_file": s.get("peak_file"),
                "offloaded_log_line": s.get("offloaded_log_line")}

    s2 = run_child("s2_tail", "S2")
    art["scenarios"]["S2"] = scenario_block(
        s2, "tail +1024B，manifest bytes 不变 => LayoutMismatch，reset_calls=0，哨兵不变")
    s3 = run_child("s3_old", "S3")
    art["scenarios"]["S3"] = scenario_block(
        s3, "去掉 chat.bytes => load 成功、恰 1 条 unvalidated、原件静默")
    s4 = run_child("s4_fixture", "S4")
    art["scenarios"]["S4"] = scenario_block(
        s4, "S1 副本改名（非独立 fixture），带 bytes 正常 load、verified=true、events=0")
    art["scenarios"]["S4"]["fixture_independence"] = "S4 = S1 产物改名，不是独立 fixture"

    # S3 explicit source hash + S4 hash semantics are added after raw capture.
    try:
        s3r = art["scenarios"]["S3"]["observed"] or {}
        if s3r.get("old_manifest"):
            s3r["source_manifest_sha16"] = sha16(s3r["old_manifest"])
    except Exception:
        pass

    hs = finish_host(host_check("after"))
    if hs["boot_changed"]:
        for k in list(art["scenarios"]):
            art["scenarios"][k]["verdict"] = "未接上（装置重启作废）"

    ref = {"source": "上一轮有效 M7-E3-GPU.json（old sha16=%s / %d B，审计 e6a58bf315680610）" % (OLD_M7_SHA16, OLD_M7_BYTES),
           "chat_bytes": 19744884, "chat_sha16": "6a2508d4df79fa57",
           "n_tokens": 189, "pos_max": 4284}
    obs = {"chat_bytes": (art["scenarios"]["S1"]["readings"] or {}).get("chat_bytes"),
           "chat_sha16": (art["scenarios"]["S1"]["readings"] or {}).get("chat_sha16"),
           "n_tokens": (art["scenarios"]["S1"]["readings"] or {}).get("n_tokens"),
           "pos_max": (art["scenarios"]["S1"]["readings"] or {}).get("pos_max")}
    fields = []
    for k in ("chat_bytes", "chat_sha16", "n_tokens", "pos_max"):
        fields.append({"field": k, "reference": ref[k], "observed": obs[k],
                       "status": "match" if ref[k] == obs[k] else "differs"})
    art["reproducibility"] = {"reference": ref, "observed": obs, "fields": fields,
                              "all_match": all(x["status"] == "match" for x in fields),
                              "conclusion_unchanged": True,
                              "note": "差异不改变四场景结构判据；本字段只记录可复现性"}

    verdicts = {s: art["scenarios"][s]["verdict"] for s in ("S1", "S2", "S3", "S4")}
    if art["reboot"]["voided_by_reboot"]:
        overall = "未接上（装置重启作废）"
    elif any(v.startswith("未接上") for v in verdicts.values()):
        overall = "未接上"
    elif any(v == "未通过" for v in verdicts.values()):
        overall = "未通过"
    else:
        overall = "通过"
    art["conclusion"] = {**verdicts, "overall": overall,
                         "kill_arm": "未做（主机不安全）",
                         "one_line": "S1/S2/S3/S4: %s; 总体=%s; kill 子臂=未做（主机不安全）"
                                     % (", ".join("%s=%s" % (k, v) for k, v in verdicts.items()), overall)}
    art["attempts"][1]["status"] = "completed"
    art["attempts"][1]["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    write_json_atomic(ART, art)
    try:
        STOP.unlink()
    except FileNotFoundError:
        pass
    print("ARTIFACT " + json.dumps({"path": str(ART), "sha16": sha16(ART),
                                    "bytes": sz(ART), "conclusion": art["conclusion"]},
                                   ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "child":
        raise SystemExit(child(sys.argv[2] if len(sys.argv) > 2 else "s1_save"))
    raise SystemExit(parent())
