# -*- coding: utf-8 -*-
"""K1 recovery segment: one 14B engine writes M5-KILL-after.kvmem (80 tokens),
then resets and load_strict reads it back (n_tokens=80).

Separate process from the no-model dry-run child; no kill signals; no other GPU
process is started by this script.  This is the ONLY model-loading segment of
the K1 dry run and is deliberately outside every kill window.
"""
import argparse
import ctypes
import hashlib
import json
import os
import struct
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
M7 = ROOT / "kvmem/m2_visibility/m7"
sys.path.insert(0, str(M7 / "out"))
import _e3gpu_run as E  # noqa: E402


def wall():
    return time.strftime("%Y-%m-%dT%H:%M:%S") + (".%03d" % (int(time.time() * 1000) % 1000)) + time.strftime("%z")


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def header(path):
    b = open(path, "rb").read(12)
    return {"n_tokens": int(struct.unpack("<i", b[8:12])[0]), "bytes": os.path.getsize(path),
            "sha16": sha16(path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default=str(OUT / "M5-KILL-before.kvmem"))
    ap.add_argument("--after", default=str(OUT / "M5-KILL-after.kvmem"))
    ap.add_argument("--result", default=str(OUT / "_k1_recovery_result.json"))
    a = ap.parse_args()
    before, after = Path(a.before), Path(a.after)
    result = {"schema": "m5_k1_recovery_v1", "model_loaded": True, "armed": False,
              "signals_sent": 0, "before": str(before), "after": str(after),
              "started_at": wall(), "status": "running", "error": None,
              "load_strict": {"done": False}, "device": None, "steps": []}
    eng = None
    t0 = time.perf_counter()
    try:
        if not before.exists():
            raise RuntimeError("before missing: %s" % before)
        result["before_info"] = header(before)
        if result["before_info"]["n_tokens"] != 50:
            raise RuntimeError("before n_tokens != 50: %s" % result["before_info"])
        eng = E.open_engine()
        meta = E.meta_from_log(eng, t0)
        result["device"] = meta
        result["steps"].append({"step": "engine_open", "t": round(time.perf_counter() - t0, 3),
                                "n_gpu_layers_readback": meta.get("n_gpu_layers_readback"),
                                "vulkan_imported": meta.get("vulkan_imported"),
                                "offloaded_log_line": meta.get("offloaded_log_line")})
        if meta.get("n_gpu_layers_readback") != 36 or meta.get("vulkan_imported") is not True:
            raise RuntimeError("36-layer self-proof failed")
        L = eng.lib
        L.kvshim_write.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        L.kvshim_write.restype = ctypes.c_int
        L.kvshim_tokenize.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_int),
                                      ctypes.c_int]
        L.kvshim_tokenize.restype = ctypes.c_int
        h = ctypes.c_void_p(eng.h)
        n = eng.load_strict(0, str(before))
        result["steps"].append({"step": "load_before", "t": round(time.perf_counter() - t0, 3),
                                "load_return": int(n), "n_tokens": int(eng.n_tokens(0))})
        if int(n) < 0 or int(eng.n_tokens(0)) != 50:
            raise RuntimeError("before load_strict n_tokens != 50")
        out = (ctypes.c_int * 64)()
        one = None
        candidates = ["的", "，", "。", "、", "a", "1", "我", "是", "在", "和", "了", "."]
        for cand in candidates:
            k = int(L.kvshim_tokenize(h, cand.encode("utf-8"), out, 64))
            if k == 1:
                one = cand
                break
        if one is None:
            raise RuntimeError("could not find a single-token text for 30-token append")
        result["steps"].append({"step": "one_token_found", "t": round(time.perf_counter() - t0, 3),
                                "text": one})
        for i in range(30):
            rc = int(L.kvshim_write(h, 0, one.encode("utf-8"), 0))
            nt = int(eng.n_tokens(0))
            if rc != 1 or nt != 51 + i:
                raise RuntimeError("write %d: rc=%r n_tokens=%d" % (i + 1, rc, nt))
        result["steps"].append({"step": "write_30", "t": round(time.perf_counter() - t0, 3),
                                "n_tokens": int(eng.n_tokens(0)), "pos_max": int(eng.pos_max(0))})
        nb = int(eng.save(0, str(after)))
        result["after_info"] = header(after) if after.exists() else None
        result["steps"].append({"step": "save_after", "t": round(time.perf_counter() - t0, 3),
                                "save_return": nb, "after_info": result["after_info"]})
        if nb <= 0 or not after.exists() or result["after_info"]["n_tokens"] != 80:
            raise RuntimeError("save_after failed/n_tokens != 80: %r" % result["after_info"])
        eng.reset(0)
        t_load = time.perf_counter()
        n2 = int(eng.load_strict(0, str(after)))
        load_s = round(time.perf_counter() - t_load, 3)
        ntok = int(eng.n_tokens(0))
        posmax = int(eng.pos_max(0))
        result["load_strict"] = {"done": True, "load_return": n2, "n_tokens": ntok,
                                 "pos_max": posmax, "expected_n_tokens": 80,
                                 "match": n2 >= 0 and ntok == 80, "load_s": load_s}
        result["steps"].append({"step": "load_strict_after", "t": round(time.perf_counter() - t0, 3),
                                "n_tokens": ntok, "pos_max": posmax, "load_return": n2})
        if not result["load_strict"]["match"]:
            raise RuntimeError("load_strict after n_tokens mismatch: %d" % ntok)
        result["status"] = "completed"
    except BaseException as e:  # noqa: BLE001
        result["status"] = "未接上（恢复段失败）"
        result["error"] = type(e).__name__ + ": " + str(e)
    finally:
        try:
            if eng is not None:
                eng.close()
        except Exception as e:  # noqa: BLE001
            result.setdefault("close_error", type(e).__name__ + ": " + str(e))
        result["finished_at"] = wall()
        result["elapsed_s"] = round(time.perf_counter() - t0, 3)
        result["model_loaded"] = True
        p = Path(a.result)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(p) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
        os.replace(tmp, p)
        print("K1_RECOVERY " + json.dumps({"status": result["status"], "n_tokens": result["load_strict"].get("n_tokens"),
                                           "elapsed": result["elapsed_s"]}, ensure_ascii=False), flush=True)
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())