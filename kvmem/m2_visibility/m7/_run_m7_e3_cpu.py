# -*- coding: utf-8 -*-
"""M7 E3-CPU: real 14B engine, gpu=0, tools/kvshim.dll (CPU static libs).

GPU is never used here.  The 14B model is loaded with n_gpu_layers=0; the child
asserts that vulkan-1.dll is not in its module list.

Modes
  preflight                  no model load; print FreeRAM_MB
  atomic                     parent: control + 2 green kill attempts + 2 red kill
  tail                       parent: F2 real-engine tail / normal / old manifests

The child prints one machine-readable line per stage:
  E3META {json}
  E3RESULT {json}
"""
import ctypes
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = r"D:\llama-mem"
TOOLS = os.path.join(ROOT, "tools")
M7 = os.path.join(ROOT, "kvmem", "m2_visibility", "m7")
OUT = os.path.join(M7, "out")
TMP = os.path.join(OUT, "tmp", "e3cpu")
DLL = os.path.join(TOOLS, "kvshim.dll")
MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
MODEL_BYTES = 8988110240
PROFILE = os.path.join(ROOT, "kvmem", "blocks", "profile.kvmem")
SESS = os.path.join(ROOT, "kvmem", "sessions")
LIVE_MAN = os.path.join(SESS, "live.json")
LIVE_CHAT = os.path.join(SESS, "live.chat.kvmem")
DB = os.path.join(ROOT, "kvmem", "chat.db")
NCTX = 8192
NSEQ = 8
MIN_FREE_MB = 10 * 1024          # controlled release threshold (lead: 10.0 GiB)
SAFETY_11G_MB = 11 * 1024


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def sz(path):
    return os.path.getsize(path) if os.path.exists(path) else None


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    def __init__(self):
        super().__init__()
        self.dwLength = ctypes.sizeof(self)


def free_ram_mb():
    m = MEMORYSTATUSEX()
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return int(m.ullAvailPhys // (1024 * 1024))


class PMC(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


def process_ws_mb(pid, peak=True):
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ,
                                           False, int(pid))
    if not h:
        return None
    try:
        p = PMC()
        p.cb = ctypes.sizeof(p)
        if not ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(p), p.cb):
            return None
        v = p.PeakWorkingSetSize if peak else p.WorkingSetSize
        return int(v // (1024 * 1024))
    finally:
        ctypes.windll.kernel32.CloseHandle(h)


def pagefile_peak_mb():
    ps = ("$p=Get-CimInstance Win32_PageFileUsage; "
          "if($p){($p | Measure-Object -Property PeakUsage -Sum).Sum}else{0}")
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            text=True, encoding="utf-8", errors="replace", timeout=15)
        return int((out.strip() or "0").splitlines()[-1])
    except Exception:
        return None


def vulkan_loaded_here():
    return bool(ctypes.windll.kernel32.GetModuleHandleW("vulkan-1.dll"))


def make_prefill_text(n=189):
    # Qwen-family tokenizer: " a" is one token for the repeated letter; try a few
    # shapes and settle for exactly 189 where possible.
    return ("a " * n).strip()


def sentinel_189(eng):
    """Reset seq0 and put exactly 189 tokens at positions 0..188 when possible."""
    candidates = [("a " * 189).strip(), "a" * 189, ("the " * 189).strip(),
                  ("hello " * 189).strip()]
    best = None
    for text in candidates:
        eng.reset(0)
        n = eng.write_at(0, text, 0, True)
        if best is None or abs(n - 189) < abs(best[0] - 189):
            best = (n, eng.pos_max(0))
        if n == 189:
            return n, eng.pos_max(0)
    return best



def f2_sequence_14b(eng, d, fixture_man):
    """E3-CPU-F2-14B: S1 fixture (already saved), S2 normal, S3 tail, S4' old format."""
    import contextlib
    import io
    import shutil
    import sqlite3
    import session_state as ss

    con_uri = "file:" + DB.replace("\\", "/") + "?mode=ro"
    con = sqlite3.connect(con_uri, uri=True)
    fixture_chat = os.path.splitext(os.path.abspath(fixture_man))[0] + ".chat.kvmem"
    fixture = {"manifest": fixture_man, "chat": fixture_chat,
               "chat_bytes": sz(fixture_chat), "chat_sha16": sha16(fixture_chat),
               "manifest_sha16": sha16(fixture_man),
               "manifest_chat_bytes": json.load(open(fixture_man, encoding="utf-8"))["chat"].get("bytes"),
               "n_tokens": json.load(open(fixture_man, encoding="utf-8"))["chat"].get("n_tokens")}
    reset_calls, load_calls = [], []
    orig_reset, orig_load, orig_load_strict = eng.reset, eng.load, eng.load_strict
    def r_reset(seq):
        reset_calls.append(int(seq))
        return orig_reset(seq)
    def r_load(seq, path):
        load_calls.append((int(seq), os.path.basename(path)))
        return orig_load(seq, path)
    def r_load_strict(seq, path):
        load_calls.append((int(seq), os.path.basename(path)))
        return orig_load_strict(seq, path)
    eng.reset, eng.load, eng.load_strict = r_reset, r_load, r_load_strict

    # S2 normal, original with bytes: silently no event
    s2_man = os.path.join(d, "f2_14b_normal.json")
    s2_chat = os.path.join(d, "f2_14b_normal.chat.kvmem")
    mm = json.load(open(fixture_man, encoding="utf-8"))
    mm["chat"]["state"] = os.path.basename(s2_chat)
    json.dump(mm, open(s2_man, "w", encoding="utf-8"), ensure_ascii=False)
    shutil.copyfile(fixture_chat, s2_chat)
    buf = io.StringIO()
    r0, l0 = len(reset_calls), len(load_calls)
    try:
        with contextlib.redirect_stderr(buf):
            rep2 = ss.restore_session(eng, con, s2_man, model_path=MODEL)
        s2 = {"load_ok": True, "exc": None,
              "chat_n_tokens": (rep2 or {}).get("chat_n_tokens"),
              "chat_bytes_verified": (rep2 or {}).get("chat_bytes_verified"),
              "events": len([x for x in buf.getvalue().splitlines() if x.strip()]),
              "reset_calls": len(reset_calls) - r0, "load_calls": len(load_calls) - l0}
    except Exception as e:  # noqa: BLE001
        s2 = {"load_ok": False, "exc": type(e).__name__ + ": " + str(e),
              "chat_n_tokens": None, "chat_bytes_verified": None,
              "events": len([x for x in buf.getvalue().splitlines() if x.strip()]),
              "reset_calls": len(reset_calls) - r0, "load_calls": len(load_calls) - l0}

    # S3 tail + 7-token sentinel
    s3_chat = os.path.join(d, "f2_14b_tail.chat.kvmem")
    shutil.copyfile(fixture_chat, s3_chat)
    with open(s3_chat, "ab") as f:
        f.write(b"\x00" * 1024)
    s3_man = os.path.join(d, "f2_14b_tail.json")
    mm = json.load(open(fixture_man, encoding="utf-8"))
    mm["chat"]["state"] = os.path.basename(s3_chat)
    json.dump(mm, open(s3_man, "w", encoding="utf-8"), ensure_ascii=False)
    eng.reset(0)
    sent_n = eng.write_at(0, "a a a a a a a", 0, False)
    sent_pos = eng.pos_max(0)
    r0, l0 = len(reset_calls), len(load_calls)
    before = {"n_tokens": eng.n_tokens(0), "pos_max": sent_pos,
              "reset_calls": len(reset_calls), "load_calls": len(load_calls)}
    err = None
    try:
        ss.restore_session(eng, con, s3_man, model_path=MODEL)
    except Exception as e:  # noqa: BLE001
        err = type(e).__name__ + ": " + str(e)
    after = {"n_tokens": eng.n_tokens(0), "pos_max": eng.pos_max(0),
             "reset_calls": len(reset_calls) - r0, "load_calls": len(load_calls) - l0}
    s3 = {"manifest": s3_man, "chat": s3_chat, "chat_bytes": sz(s3_chat),
          "manifest_bytes": mm["chat"].get("bytes"), "sentinel_before": before,
          "after": after, "exc": err,
          "pass": bool(err and "LayoutMismatch" in err
                       and after["reset_calls"] == 0 and after["load_calls"] == 0
                       and (before["n_tokens"], before["pos_max"]) == (after["n_tokens"], after["pos_max"]))}

    # S4': same 14B fixture, remove bytes (simulates pre-M6b old format)
    s4_man = os.path.join(d, "f2_14b_oldformat.json")
    s4_chat = os.path.join(d, "f2_14b_oldformat.chat.kvmem")
    mm = json.load(open(fixture_man, encoding="utf-8"))
    mm.get("chat", {}).pop("bytes", None)
    mm["chat"]["state"] = os.path.basename(s4_chat)
    json.dump(mm, open(s4_man, "w", encoding="utf-8"), ensure_ascii=False)
    shutil.copyfile(fixture_chat, s4_chat)
    buf = io.StringIO()
    r0, l0 = len(reset_calls), len(load_calls)
    try:
        with contextlib.redirect_stderr(buf):
            rep4 = ss.restore_session(eng, con, s4_man, model_path=MODEL)
        ev_lines = [x for x in buf.getvalue().splitlines() if x.strip()]
        s4 = {"load_ok": True, "exc": None,
              "chat_n_tokens": (rep4 or {}).get("chat_n_tokens"),
              "report_unvalidated": (rep4 or {}).get("unvalidated_chat_bytes"),
              "events": len(ev_lines), "event_lines": ev_lines,
              "reset_calls": len(reset_calls) - r0, "load_calls": len(load_calls) - l0}
    except Exception as e:  # noqa: BLE001
        ev_lines = [x for x in buf.getvalue().splitlines() if x.strip()]
        s4 = {"load_ok": False, "exc": type(e).__name__ + ": " + str(e),
              "chat_n_tokens": None, "report_unvalidated": None,
              "events": len(ev_lines), "event_lines": ev_lines,
              "reset_calls": len(reset_calls) - r0, "load_calls": len(load_calls) - l0}

    # S4'' existing 7B-geometry old manifests: register, do not run (hard refusal proven)
    existing = []
    for name in ("s", "live", "s_2", "bridge"):
        p = os.path.join(SESS, name + ".json")
        existing.append({"name": name, "manifest": p, "sha16": sha16(p),
                         "status": "未做（几何不兼容：14B 引擎硬拒绝）",
                         "error": "kvshim_load refused ... incompatible state (model, rope, kv type or n_rot_k differs)"})

    ev_path = os.path.join(OUT, "M7-E3-CPU-EVENTS.jsonl")
    with open(ev_path, "w", encoding="utf-8", newline="\n") as f:
        for line in s4.get("event_lines") or []:
            f.write(line + "\n")

    # decode speed: one 32-token generation, after all gate checks
    eng.reset(0)
    dt0 = time.perf_counter()
    try:
        eng.ask(0, "Hello", 32)
        dec_ok = True
    except Exception:
        dec_ok = False
    decode_s = time.perf_counter() - dt0
    speed = {"decode_tok_per_s": round(32 / decode_s, 2) if decode_s > 0 and dec_ok else None,
             "decode_s": round(decode_s, 3), "decode_tokens": 32,
             "load_s": None, "chat_bytes": fixture["chat_bytes"]}
    try:
        con.close()
    except Exception:
        pass
    s4["source_manifest_sha16"] = sha16(fixture_man)
    return {"fixture": fixture, "s2_normal": s2, "s3_tail": s3, "s4_oldformat": s4,
            "s4_existing_4": existing,
            "con_db_path": DB, "con_mode": "ro", "speed": speed,
            "events": {"path": ev_path, "lines": s4["events"], "sha16": sha16(ev_path)},
            "verdict": {"S2_normal": s2["load_ok"] and s2["chat_n_tokens"] == fixture["n_tokens"]
                        and s2["events"] == 0,
                        "S3_tail": s3["pass"],
                        "S4_oldformat": s4["load_ok"] and s4["events"] == 1
                        and s4["report_unvalidated"] is True}}


def build_chat_189(eng, start=4096):
    """Build a 189-token chat sequence at CHAT_START without a 7B fixture file."""
    candidates = [("a " * 189).strip(), "a" * 189, ("the " * 189).strip(),
                  ("hello " * 189).strip()]
    best = None
    for text in candidates:
        eng.reset(0)
        n = eng.write_at(0, text, start, False)
        if best is None or abs(n - 189) < abs(best[0] - 189):
            best = (n, eng.pos_max(0))
        if n == 189:
            return n, eng.pos_max(0)
    return best


def child(mode, target):
    sys.path.insert(0, TOOLS)
    import ctypes as C
    import kvslots
    import memory_source as ms
    import session_state as ss

    k32 = ctypes.windll.kernel32
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    hproc = k32.GetCurrentProcess()
    k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    k32.SetPriorityClass.restype = ctypes.c_int
    k32.GetPriorityClass.argtypes = [ctypes.c_void_p]
    k32.GetPriorityClass.restype = ctypes.c_uint
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.SetProcessAffinityMask.restype = ctypes.c_int
    k32.GetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
                                           ctypes.POINTER(ctypes.c_size_t)]
    k32.GetProcessAffinityMask.restype = ctypes.c_int
    k32.SetPriorityClass(hproc, 0x00004000)  # BELOW_NORMAL
    # affinity deliberately unrestricted: the earlier 0x3F mask slowed 14B load to ~100 s
    prio = k32.GetPriorityClass(hproc)
    aff = ctypes.c_size_t(0); sysaff = ctypes.c_size_t(0)
    k32.GetProcessAffinityMask(hproc, ctypes.byref(aff), ctypes.byref(sysaff))
    meta = {"mode": mode, "pid": os.getpid(), "model": MODEL,
            "model_bytes": MODEL_BYTES, "dll": DLL, "gpu": 0,
            "backend": "cpu", "n_ctx": NCTX, "n_seq": NSEQ,
            "priority_class": ("below_normal" if prio == 0x00004000 else hex(prio)),
            "affinity_mask": hex(aff.value),
            "threads_env": os.environ.get("KVSHIM_THREADS"),
            "threads_default_8": os.environ.get("KVSHIM_THREADS") in (None, ""),
            "vulkan_loaded": vulkan_loaded_here()}
    t0 = time.perf_counter()
    eng = kvslots.KVEngine(MODEL, n_ctx=NCTX, n_seq=NSEQ, gpu=0, dll=DLL)
    meta["load_s"] = round(time.perf_counter() - t0, 3)
    meta["vulkan_loaded_after_load"] = vulkan_loaded_here()
    meta["free_ram_mb_after_load"] = free_ram_mb()
    meta["peak_ws_mb_after_load"] = process_ws_mb(os.getpid())
    meta["child_pid"] = os.getpid()
    meta["dll_sha16"] = sha16(DLL)
    meta["priority"] = meta["priority_class"]
    meta["affinity"] = meta["affinity_mask"]
    try:
        f = eng.lib.kvshim_threads
        f.argtypes = [ctypes.c_void_p]
        f.restype = ctypes.c_int
        meta["kvshim_threads_readback"] = int(f(ctypes.c_void_p(eng.h)))
    except Exception:
        meta["kvshim_threads_readback"] = None
    meta["kvshim_threads_env"] = os.environ.get("KVSHIM_THREADS")
    meta["threads_default_8"] = meta["kvshim_threads_env"] in (None, "")
    print("E3META " + json.dumps(meta, ensure_ascii=False), flush=True)
    if meta["vulkan_loaded"] or meta["vulkan_loaded_after_load"]:
        raise RuntimeError("vulkan-1.dll loaded in CPU run")
    try:
        if mode == "control":
            pf0 = time.perf_counter()
            nchat, pos = build_chat_189(eng, 4096)
            pref_s = time.perf_counter() - pf0
            if nchat != 189:
                raise RuntimeError("chat fixture expected 189 tokens, got %d" % nchat)
            # real 14B geometry block arm: profile block (50 tokens) below anchor
            npf = eng.load(1, PROFILE)
            # profile.kvmem loads at [0,50); move it to the contracted slot [4046,4096)
            moved = eng.repos_local(1, 4046, 0, npf)
            ppos = eng.pos_max(1)
            lo = ppos - npf + 1
            if lo != 4046 or moved != npf:
                raise RuntimeError("profile block reposition failed: moved=%s lo=%s" % (moved, lo))
            eng.share(1, 0, lo, ppos + 1)
            blocks = [{"name": "profile", "seq": 1, "source_id": 1,
                       "role": "memory", "lo": lo, "hi": ppos + 1,
                       "n_tokens": npf, "path": PROFILE}]
            t1 = time.perf_counter()
            man = ss.save_session(eng, None, target, blocks, 4096,
                                  model_path=MODEL)
            save_s = time.perf_counter() - t1
            chat = os.path.splitext(os.path.abspath(target))[0] + ".chat.kvmem"
            res = {"mode": mode, "load_s": meta["load_s"],
                   "prefill_n": nchat, "prefill_pos_max": pos,
                   "prefill_s": round(pref_s, 3),
                   "prefill_tok_per_s": round(nchat / pref_s, 2) if pref_s and nchat else None,
                   "profile_n_tokens": npf, "profile_lo": lo, "profile_hi": ppos + 1,
                   "chat_n_tokens": nchat, "save_s": round(save_s, 3),
                   "chat_file": chat, "chat_bytes": sz(chat),
                   "chat_sha16": sha16(chat),
                   "manifest": os.path.abspath(target),
                   "manifest_sha16": sha16(target),
                   "manifest_chat_bytes": man.get("chat", {}).get("bytes"),
                   "peak_ws_mb": process_ws_mb(os.getpid()),
                   "free_ram_mb_after": free_ram_mb()}
            if os.environ.get("M7_E3_SKIP_F2") != "1":
                res["f2"] = f2_sequence_14b(eng, os.path.dirname(os.path.abspath(target)), target)
            print("E3RESULT " + json.dumps(res, ensure_ascii=False), flush=True)
        elif mode in ("kill", "red", "red_full"):
            npf = eng.load(1, PROFILE)
            eng.repos_local(1, 4046, 0, npf)
            nchat, pos = build_chat_189(eng, 4096)
            if nchat != 189:
                raise RuntimeError("chat fixture expected 189 tokens, got %d" % nchat)
            if mode in ("red", "red_full"):
                def legacy(self, seq, path):
                    return self.lib.kvshim_save(ctypes.c_void_p(self.h), int(seq),
                                                path.encode("utf-8"))
                kvslots.KVEngine.save = legacy
            if mode == "red_full":
                t1 = time.perf_counter()
                nb = eng.save(0, target)
                print("E3RESULT " + json.dumps(
                    {"mode": mode, "chat_n_tokens": nchat, "nb": nb,
                     "save_s": round(time.perf_counter() - t1, 3),
                     "target_sha16": sha16(target), "target_bytes": sz(target),
                     "peak_ws_mb": process_ws_mb(os.getpid())}, ensure_ascii=False),
                    flush=True)
                return
            print("E3SAVE_START", flush=True)
            time.sleep(0.25)          # watcher window; does not change save semantics
            t1 = time.perf_counter()
            nb = eng.save(0, target)
            ms_save = time.perf_counter() - t1
            print("E3SAVE_DONE %s %.3f" % (nb, ms_save), flush=True)
            print("E3RESULT " + json.dumps(
                {"mode": mode, "chat_n_tokens": nchat, "nb": nb,
                 "save_s": round(ms_save, 3), "peak_ws_mb": process_ws_mb(os.getpid())},
                ensure_ascii=False), flush=True)
        elif mode == "f2":
            res = f2_sequence_14b(eng, os.path.dirname(os.path.abspath(target)), target)
            res["mode"] = "f2"
            print("E3RESULT " + json.dumps(res, ensure_ascii=False), flush=True)
        elif mode == "threads_probe":
            e = kvslots.KVEngine(MODEL, n_ctx=NCTX, n_seq=NSEQ, gpu=0, dll=DLL)
            try:
                f = e.lib.kvshim_threads
                f.argtypes = [ctypes.c_void_p]; f.restype = ctypes.c_int
                rb = int(f(ctypes.c_void_p(e.h)))
            finally:
                e.close()
            print("E3RESULT " + json.dumps(
                {"threads_probe": {"env": os.environ.get("KVSHIM_THREADS"),
                                   "readback": rb}}, ensure_ascii=False), flush=True)
        elif mode == "probe":
            rows = []
            for label, path in (("profile", PROFILE), ("live", LIVE_CHAT),
                                ("s", os.path.join(SESS, "s.chat.kvmem")),
                                ("live2", LIVE_CHAT)):
                eng.reset(0)
                try:
                    rc = eng.load_strict(0, path)
                    rows.append({"label": label, "path": path, "rc": rc,
                                 "n_tokens": eng.n_tokens(0), "pos_max": eng.pos_max(0)})
                except Exception as e:  # noqa: BLE001
                    rows.append({"label": label, "path": path, "rc": None,
                                 "exc": type(e).__name__ + ": " + str(e)})
            print("E3RESULT " + json.dumps({"probe": rows}, ensure_ascii=False), flush=True)
        elif mode == "tail":
            n, pos = sentinel_189(eng)
            meta["sentinel_n_tokens"] = n
            meta["sentinel_pos_max"] = pos
            print("E3SENTINEL " + json.dumps(
                {"n_tokens": n, "pos_max": pos}, ensure_ascii=False), flush=True)
            # counters
            reset_calls, load_calls = [], []
            orig_reset, orig_load, orig_load_strict = eng.reset, eng.load, eng.load_strict
            def r_reset(seq):
                reset_calls.append(int(seq))
                return orig_reset(seq)
            def r_load(seq, path):
                load_calls.append((int(seq), os.path.basename(path)))
                return orig_load(seq, path)
            def r_load_strict(seq, path):
                load_calls.append((int(seq), os.path.basename(path)))
                return orig_load_strict(seq, path)
            eng.reset, eng.load, eng.load_strict = r_reset, r_load, r_load_strict
            before = {"n_tokens": eng.n_tokens(0), "pos_max": eng.pos_max(0),
                      "reset_calls": len(reset_calls), "load_calls": len(load_calls)}
            tail_man, tail_chat = target
            err = None
            try:
                ss.restore_session(eng, None, tail_man, model_path=MODEL)
            except Exception as e:  # noqa: BLE001
                err = type(e).__name__ + ": " + str(e)
            after = {"n_tokens": eng.n_tokens(0), "pos_max": eng.pos_max(0),
                     "reset_calls": len(reset_calls), "load_calls": len(load_calls)}
            print("E3TAIL_RESULT " + json.dumps(
                {"before": before, "after": after,
                 "exc": err, "tail_manifest": tail_man, "tail_chat": tail_chat},
                ensure_ascii=False), flush=True)
        else:
            raise RuntimeError("unknown child mode " + mode)
    finally:
        try:
            eng.close()
        except Exception:
            pass


# ---------------------------------------------------------------- parent

def launch(mode, target):
    p = subprocess.Popen(
        [sys.executable, "-X", "utf8", os.path.abspath(__file__), "child",
         "--mode", mode, "--target", target if isinstance(target, str) else json.dumps(target)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace",
        creationflags=0x00004000,  # CREATE_BELOW_NORMAL_PRIORITY_CLASS
        env={**os.environ, "KVSHIM_THREADS": "6"})
    return p


def parse_line(lines, prefix):
    for x in lines:
        if x.startswith(prefix):
            return json.loads(x[len(prefix):])
    return None


def run_control(target_man):
    p = launch("control", target_man)
    out, err = p.communicate(timeout=1800)
    lines = out.splitlines()
    meta = parse_line(lines, "E3META ")
    res = parse_line(lines, "E3RESULT ")
    if p.returncode != 0 or res is None:
        raise RuntimeError("control failed rc=%s\n%s\n%s" % (p.returncode, out[-2000:], err[-2000:]))
    res["identity"] = meta
    res["stderr_tail"] = err.splitlines()[-5:]
    return res


def seed_target(path, src):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shutil.copyfile(src, path)


def run_full(mode, target):
    p = launch(mode, target)
    out, err = p.communicate(timeout=1800)
    res = parse_line(out.splitlines(), "E3RESULT ")
    if p.returncode != 0 or res is None:
        raise RuntimeError("full %s failed rc=%s\n%s\n%s" % (mode, p.returncode, out[-1500:], err[-1500:]))
    res["child_pid"] = p.pid
    return res


def kill_attempt(mode, target, before_sha, before_bytes, seed_sha, seed_bytes, idx):
    stale = glob.glob(target + ".tmp-*")
    for x in stale:
        try:
            os.remove(x)
        except OSError:
            pass
    stale_cleared = len(stale) > 0
    p = launch(mode, target)
    q = []
    import threading
    th = threading.Thread(target=lambda: [q.append(x.rstrip("\n")) for x in p.stdout],
                          daemon=True)
    th.start()
    t0 = time.perf_counter()
    state = None
    save_start_ms = None
    killed_at_ms = None
    tmp_obj = None
    peak = 0
    while time.perf_counter() - t0 < 1800:
        ws = process_ws_mb(p.pid)
        if ws:
            peak = max(peak, ws)
        if any(x.startswith("E3SAVE_START") for x in q):
            state = "save_start"
            save_start_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            break
        if p.poll() is not None:
            break
        time.sleep(0.02)
    if state == "save_start":
        while time.perf_counter() - t0 < 1800:
            ws = process_ws_mb(p.pid)
            if ws:
                peak = max(peak, ws)
            hit = False
            if mode == "kill":
                cand = glob.glob(target + ".tmp-*")
                cand = [x for x in cand if os.path.exists(x) and os.path.getsize(x) > 0]
                if cand:
                    path = sorted(cand)[0]
                    base = os.path.basename(path)
                    try:
                        tmp_pid = int(base.split(".tmp-")[1].split("-")[0])
                    except (IndexError, ValueError):
                        tmp_pid = None
                    tmp_obj = {"path": path, "size": sz(path), "pid": tmp_pid}
                    hit = True
            else:
                hit = os.path.exists(target) and os.path.getsize(target) < before_bytes
                if hit:
                    tmp_obj = {"path": target, "size": sz(target), "pid": None}
            if hit:
                killed_at_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                p.kill()
                break
            if p.poll() is not None:
                break
            time.sleep(0.002)
    if killed_at_ms is None:
        if p.poll() is None:
            p.kill()
        killed_at_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    out, err = p.communicate(timeout=60)
    exit_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    th.join(timeout=1)
    lines = q + out.splitlines()
    tmp_pid = (tmp_obj or {}).get("pid")
    for x in glob.glob(target + ".tmp-*"):
        try:
            os.remove(x)
        except OSError:
            pass
    tmp_clean = not glob.glob(target + ".tmp-*")
    return {"attempt": idx, "mode": mode, "before_sha16": before_sha,
            "before_bytes": before_bytes,
            "target_sha16": sha16(target) if os.path.exists(target) else None,
            "target_bytes": sz(target),
            "state": ("third" if not os.path.exists(target) or sha16(target) != before_sha
                      else "before"),
            "tmp": tmp_obj, "tmp_existed": tmp_obj is not None,
            "tmp_path": (tmp_obj or {}).get("path"),
            "tmp_size": (tmp_obj or {}).get("size"),
            "tmp_pid": tmp_pid,
            "tmp_pid_matches_child": bool(tmp_obj and tmp_pid == p.pid),
            "child_pid": p.pid,
            "target_sha": sha16(target) if os.path.exists(target) else None,
            "seed_sha16": seed_sha, "seed_bytes": seed_bytes,
            "seed_assert": (before_sha == seed_sha and before_bytes == seed_bytes),
            "tmp_clean_after_full": tmp_clean,
            "stale_tmp_cleared": stale_cleared,
            "killed_at_ms": killed_at_ms,
            "deadline_ms": killed_at_ms,
            "deadline_source": "first_observable_side_effect",
            "save_start_ms": save_start_ms,
            "signal_ms": killed_at_ms,
            "exit_ms": exit_ms,
            "peak_ws_mb_seen": peak,
            "stderr_tail": err.splitlines()[-5:],
            "stdout_tail": lines[-3:]}


def _prefill_from_atomic():
    try:
        a = json.load(open(os.path.join(OUT, "M7-E3-CPU-ATOMIC.json"), encoding="utf-8"))
        v = a.get("control", {}).get("prefill_tok_per_s")
        if v:
            return v
        return a.get("control", {}).get("prefill_s")
    except Exception:
        return None


def tail_main():
    free = free_ram_mb()
    if free < MIN_FREE_MB:
        raise SystemExit("REFUSED: FreeRAM %d MB < %d MB" % (free, MIN_FREE_MB))
    fixture = os.path.join(TMP, "atomic", "control.json")
    if not os.path.exists(fixture):
        raise SystemExit("missing fixture " + fixture)
    p = launch("f2", fixture)
    out, err = p.communicate(timeout=1800)
    lines = out.splitlines()
    meta = parse_line(lines, "E3META ")
    res = parse_line(lines, "E3RESULT ")
    if p.returncode != 0 or res is None:
        raise RuntimeError("f2 failed rc=%s\n%s\n%s" % (p.returncode, out[-2000:], err[-2000:]))
    art = {
        "schema": "m7_e3_cpu_tail_v1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "task": "M7 E3-CPU-F2-14B 长度校验（真实 14B CPU，fixture 由本臂生成）",
        "host_safety": {"bsod_incidents": 3, "bugchecks": ["0xA", "0xA", "0x44"],
                        "live_kernel": ["141", "141", "144"],
                        "gpu": "RX 6750 GRE 10GB / 32.0.21045.1000",
                        "policy": "CPU-only; gpu=0; no kill of GPU process"},
        "free_ram_mb_before": free,
        "free_ram_gate_mb": MIN_FREE_MB,
        "pagefile_peak_mb": pagefile_peak_mb(),
        "identity": meta,
        "f2_child_pid": meta.get("child_pid"),
        "con_db_path": res.get("con_db_path"),
        "con_mode": res.get("con_mode"),
        "speed": {**res.get("speed", {}), "prefill_tok_per_s": _prefill_from_atomic()},
        "fixture": res["fixture"],
        "S2_normal": res["s2_normal"],
        "S3_tail": res["s3_tail"],
        "S4_oldformat": res["s4_oldformat"],
        "S4_existing_4": res["s4_existing_4"],
        "events": res["events"],
        "sentinel_before": res["s3_tail"]["sentinel_before"],
        "sentinel_after": res["s3_tail"]["after"],
        "reset_calls": res["s3_tail"]["after"]["reset_calls"],
        "load_calls": res["s3_tail"]["after"]["load_calls"],
        "s2": res["s2_normal"], "s3": res["s3_tail"],
        "s4_prime": res["s4_oldformat"], "s4_double_prime": res["s4_existing_4"],
        "events_path": res["events"]["path"], "events_sha16": res["events"]["sha16"],
        "events_lines": res["events"]["lines"],
        "verdict": res["verdict"],
        "no_self_sha": True,
    }
    art["speed"]["load_s"] = meta.get("load_s")
    REQ_F2 = ["f2_child_pid","con_db_path","con_mode","sentinel_before","sentinel_after",
              "reset_calls","load_calls","speed","s2","s3","s4_prime","s4_double_prime",
              "events_path","events_sha16","events_lines"]
    miss = [k for k in REQ_F2 if k not in art]
    miss += ["identity."+k for k in ("child_pid","dll_sha16","kvshim_threads_readback","gpu","backend","vulkan_loaded") if k not in (art.get("identity") or {})]
    if art["speed"].get("decode_tok_per_s") is None:
        miss.append("speed.decode_tok_per_s")
    if miss:
        raise RuntimeError("tail artifact missing keys: " + ", ".join(miss))
    tp = os.path.join(OUT, "M7-E3-CPU-TAIL.json")
    with open(tp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)
    print(tp, sz(tp), sha16(tp), flush=True)
    print(json.dumps(art["verdict"], ensure_ascii=False), flush=True)


def atomic_main():
    free = free_ram_mb()
    if free < MIN_FREE_MB:
        raise SystemExit("REFUSED: FreeRAM %d MB < %d MB" % (free, MIN_FREE_MB))
    os.makedirs(TMP, exist_ok=True)
    d = os.path.join(TMP, "atomic")
    if os.path.isdir(d):
        for x in glob.glob(os.path.join(d, "*")):
            if os.path.isfile(x):
                os.remove(x)
    os.makedirs(d, exist_ok=True)
    control_man = os.path.join(d, "control.json")
    control = run_control(control_man)
    control_chat = os.path.join(d, "control.chat.kvmem")
    control["tmp_clean_after_full"] = not glob.glob(control_man + ".tmp-*")
    parent_vulkan = vulkan_loaded_here()
    target = os.path.join(d, "atomic_before.kvmem")
    control_sha = sha16(control_chat)
    control_bytes = sz(control_chat)
    green = []
    for i in (1, 2):
        seed_target(target, control_chat)
        green.append(kill_attempt("kill", target, control_sha, control_bytes, control_sha, control_bytes, i))
    # red full legacy write (no kill) = final_sha/final_bytes baseline
    seed_target(target, control_chat)
    red_full = run_full("red_full", target)
    red_full["target_sha"] = red_full.get("target_sha16")
    red_full["target_bytes"] = red_full.get("target_bytes")
    red_full["expected_final_sha"] = red_full.get("target_sha16")
    red_full["final_bytes"] = red_full.get("target_bytes")
    red_full["legacy_impl"] = "unittest.mock"
    red = []
    for i in (1, 2):
        seed_target(target, control_chat)
        red.append(kill_attempt("red", target, control_sha, control_bytes, control_sha, control_bytes, i))
    art = {
        "schema": "m7_e3_cpu_atomic_v1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "task": "M7 E3-CPU F1 原子写（真实 14B CPU，block 几何）",
        "host_safety": {"bsod_incidents": 3, "bugchecks": ["0xA", "0xA", "0x44"],
                        "live_kernel": ["141", "141", "144"],
                        "gpu": "RX 6750 GRE 10GB / 32.0.21045.1000",
                        "policy": "CPU-only; gpu=0; no kill of GPU process"},
        "free_ram_mb_before": free,
        "free_ram_gate_mb": MIN_FREE_MB,
        "pagefile_peak_mb": pagefile_peak_mb(),
        "parent_vulkan_loaded": parent_vulkan,
        "threads": {"env": os.environ.get("KVSHIM_THREADS"),
                    "default_8": os.environ.get("KVSHIM_THREADS") in (None, ""),
                    "process_priority": "below_normal", "affinity_mask": "0xfff"},
        "control": control,
        "target_before": {"path": target, "sha16": control_sha, "bytes": control_bytes},
        "green": green,
        "red_full": red_full,
        "red_before": {"sha16": control_sha, "bytes": control_bytes},
        "red": red,
        "verdict": {
            "green_all_before": all(r["state"] == "before" for r in green),
            "green_tmp_seen": all(r["tmp_existed"] and r["tmp_pid_matches_child"] for r in green),
            "green_stale_cleared": all(r["stale_tmp_cleared"] for r in green),
            "red_all_third": all(r["state"] == "third" for r in red),
            "red_full_final": bool(red_full.get("target_sha16")),
            "gpu_zero": all(r.get("gpu") == 0 for r in [control["identity"]]),
            "vulkan_imported": parent_vulkan,
            "tmp_clean_after_full": control["tmp_clean_after_full"],
        },
        "identity": control["identity"],
        "no_self_sha": True,
    }
    REQ_ID = ["mode","pid","child_pid","gpu","backend","dll_sha16","vulkan_loaded",
              "kvshim_threads_env","kvshim_threads_readback","priority","affinity",
              "threads_default_8","n_ctx","n_seq","model","model_bytes"]
    REQ_G = ["attempt","child_pid","tmp_pid","tmp_pid_matches_child","tmp.path","tmp.size",
             "tmp_existed","target_sha","target_bytes","seed_sha16","seed_bytes",
             "killed_at_ms","deadline_ms","signal_ms","exit_ms","state",
             "stale_tmp_cleared","tmp_clean_after_full"]
    REQ_R = ["attempt","tmp.path","tmp.size","tmp_existed","killed_at_ms","deadline_ms",
             "state","target_sha","target_bytes","seed_sha16","seed_bytes"]
    missing = []
    missing += ["identity."+k for k in REQ_ID if k not in art["identity"]]
    for i, row in enumerate(art["green"]):
        for k in REQ_G:
            if k.startswith("tmp."):
                if k.split(".", 1)[1] not in (row.get("tmp") or {}):
                    missing.append("green[%d].%s" % (i, k))
            elif k not in row:
                missing.append("green[%d].%s" % (i, k))
    for i, row in enumerate(art["red"]):
        for k in REQ_R:
            if k.startswith("tmp."):
                if k.split(".", 1)[1] not in (row.get("tmp") or {}):
                    missing.append("red[%d].%s" % (i, k))
            elif k not in row:
                missing.append("red[%d].%s" % (i, k))
    for k in ["target_sha","target_bytes","expected_final_sha","final_bytes","legacy_impl"]:
        if k not in art["red_full"]:
            missing.append("red_full."+k)
    if missing:
        raise RuntimeError("artifact missing keys: " + ", ".join(missing))
    p = os.path.join(OUT, "M7-E3-CPU-ATOMIC.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)
    print(p, sz(p), sha16(p), flush=True)
    print(json.dumps(art["verdict"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "child":
        mode = sys.argv[sys.argv.index("--mode") + 1]
        tg = sys.argv[sys.argv.index("--target") + 1]
        if tg.startswith("["):
            tg = tuple(json.loads(tg))
        else:
            tg = tg
        child(mode, tg)
    elif len(sys.argv) >= 2 and sys.argv[1] == "preflight":
        print("FreeRAM_MB=%d" % free_ram_mb())
    elif len(sys.argv) >= 2 and sys.argv[1] == "atomic":
        atomic_main()
    elif len(sys.argv) >= 2 and sys.argv[1] == "tail":
        tail_main()
    else:
        print("usage: preflight | atomic")