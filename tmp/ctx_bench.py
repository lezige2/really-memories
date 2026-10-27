# -*- coding: utf-8 -*-
"""Throwaway benchmark: n_ctx x n_gpu_layers tradeoff (tok/s + VRAM peak).

Not product code. Run: python -X utf8 tmp/ctx_bench.py
"""
import json
import os
import re
import subprocess
import sys
import threading
import time

ROOT = r"D:\llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kvslots  # noqa: E402

MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
SRC = ("我把一件灰色羽绒服送到巷口的洁雅干洗店，取衣单号 0427，洗涤费 58 元，"
       "店员说周四下午三点以后能取，领口那处油渍会重点处理。")
Q = "店员说几点能拿？哪一处油渍会重点处理？"
CONFIGS = [
    (36, 8192),
    (36, 12288),
    (32, 12288),
    (32, 16384),
    (28, 16384),
]
NPRED = 96


def vram_gib():
    ps = ("$m=Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_"
          "GPUAdapterMemory -ErrorAction SilentlyContinue | "
          "Measure-Object DedicatedUsage -Sum; "
          "if($m.Sum){[math]::Round($m.Sum/1GB,3)}else{''}")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=10)
        t = out.stdout.strip()
        return float(t) if t else None
    except Exception:
        return None


class Sampler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.stop_flag = False
        self.samples = []

    def run(self):
        while not self.stop_flag:
            v = vram_gib()
            if v is not None:
                self.samples.append(v)
            time.sleep(1.5)

    def stop(self):
        self.stop_flag = True
        self.join(timeout=5)

    def peak(self):
        return max(self.samples) if self.samples else None


def one(ngl, nctx):
    base = vram_gib()
    t0 = time.time()
    eng = kvslots.KVEngine(MODEL, n_ctx=nctx, n_seq=8, gpu=ngl, kv="q8_0")
    load_s = round(time.time() - t0, 2)
    try:
        smp = Sampler()
        smp.start()
        try:
            eng.reset(1)
            n_src = eng.write_at(1, SRC, 0)
            eng.reset(0)
            tok_before = eng.n_tokens(0)
            t = time.time()
            ans = eng.ask(0, Q, n_predict=NPRED, pos=4096 if nctx > 4096 else 1024)
            gen_s = time.time() - t
            tok_after = eng.n_tokens(0)
            gen_tokens = max(0, tok_after - tok_before)
            rate = gen_tokens / gen_s if gen_s > 0 else 0
            rec = {
                "n_gpu_layers": ngl, "n_ctx": nctx,
                "vram_base_gib": base,
                "load_s": load_s,
                "src_tokens": int(n_src),
                "gen_tokens": int(gen_tokens),
                "gen_s": round(gen_s, 2),
                "tok_per_s": round(rate, 2),
                "peak_gib": smp.peak(),
                "bytes_per_token": int(eng.bytes_per_token()),
                "pool_gib": round(eng.pool_bytes() / (1024 ** 3), 3),
                "answer_chars": len(ans),
            }
        finally:
            smp.stop()
    finally:
        eng.close()
    return rec


def main():
    print("model", os.path.getsize(MODEL), "bytes")
    out = []
    for ngl, nctx in CONFIGS:
        try:
            rec = one(ngl, nctx)
        except Exception as e:  # noqa: BLE001
            rec = {"n_gpu_layers": ngl, "n_ctx": nctx, "error": "%s: %s" % (type(e).__name__, e)}
        out.append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        time.sleep(2)
    path = os.path.join(ROOT, "tmp", "ctx_bench.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"results": out}, ensure_ascii=False, indent=1) + "\n")
    print("written", path)


if __name__ == "__main__":
    main()