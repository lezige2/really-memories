# -*- coding: utf-8 -*-
"""Throwaway: prefill latency at 16k context (prompt processing cost).

Measures time for one ask() with a short prompt when the KV context already
holds ~8k tokens, vs a near-empty context. Run: python -X utf8 tmp/prefill_bench.py
"""
import json
import os
import sys
import time

ROOT = r"D:\llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kvslots  # noqa: E402

MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
BASE = ("我把一件灰色羽绒服送到巷口的洁雅干洗店，取衣单号 0427，洗涤费 58 元，"
        "店员说周四下午三点以后能取，领口那处油渍会重点处理。")
Q = "店员说几点能拿？"


def fill_tokens(eng, seq, target_tokens):
    """Write repeated text into seq until >= target_tokens tokens are present."""
    n = 0
    while n < target_tokens:
        n += eng.write_at(seq, BASE, n)
    return n


def run(ngl, nctx, block_tokens):
    eng = kvslots.KVEngine(MODEL, n_ctx=nctx, n_seq=8, gpu=ngl, kv="q8_0")
    try:
        eng.reset(1)
        got = fill_tokens(eng, 1, block_tokens) if block_tokens else 0
        eng.reset(0)
        # one-token generation: cost is dominated by prompt processing + attention over context
        t0 = time.perf_counter()
        eng.ask(0, Q, n_predict=1, pos=nctx // 2)
        t1 = time.perf_counter()
        # 32-token generation for tok/s reference
        eng.reset(0)
        t2 = time.perf_counter()
        eng.ask(0, Q, n_predict=32, pos=nctx // 2)
        t3 = time.perf_counter()
        return {
            "n_gpu_layers": ngl, "n_ctx": nctx, "block_tokens": int(got),
            "one_token_ms": round((t1 - t0) * 1000, 1),
            "gen32_ms": round((t3 - t2) * 1000, 1),
            "gen32_tok_per_s": round(32 / (t3 - t2), 2),
            "pool_gib": round(eng.pool_bytes() / (1024 ** 3), 3),
        }
    finally:
        eng.close()


def main():
    out = []
    for ngl, nctx, block in [(34, 16384, 0), (34, 16384, 8000), (36, 8192, 4000)]:
        try:
            rec = run(ngl, nctx, block)
        except Exception as e:  # noqa: BLE001
            rec = {"n_gpu_layers": ngl, "n_ctx": nctx, "block_tokens": block,
                   "error": "%s: %s" % (type(e).__name__, e)}
        out.append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        time.sleep(2)
    with open(os.path.join(ROOT, "tmp", "prefill_bench.json"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"results": out}, ensure_ascii=False, indent=1) + "\n")
    print("written tmp/prefill_bench.json")


if __name__ == "__main__":
    main()