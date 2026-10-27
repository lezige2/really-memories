#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""C1 session-invariance check for the b7' shard1 extraction (tmp, not frozen).

RULING-M5C2-B7-EXTRACT-RESUME-A2 C1: after shard2 completes and BEFORE the merge
is trusted, re-run 20 sentences sampled (seed=20261027) from the 388 forward
sentences already completed in shard1, in a NEW session with identical engine
configuration, and compare raw_out byte-for-byte (plus prompt_sha16 and rc).
All 20 equal => pass; any difference => 未接上, the merge must not be trusted.

Output: out/M5C2-B7-INVARIANCE20.json (atomic).  Extra: 10 pin assertions and a
negative pin test (tampered pin must exit non-zero).

Exit codes: 0 pass; 3 mismatch/未接上; 2 pins/input error.
"""
import ctypes
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
sys.path.insert(0, str(M5))

import run_m5c2_b7_extract as EX  # noqa: E402  (frozen, read-only import)
import _e3gpu_run as E  # noqa: E402

SENTS = OUT / "M5C2-B7-SENTS.json"
SENTS_SHA16 = "c5a49a696b66f0c7"
SENTS_BYTES = 288805
GEN_SHA16 = "041b51eb7837aa90"
GEN_BYTES = 140514
RAW1 = OUT / "_m5b7_extract_raw.json"
OUT_ART = OUT / "M5C2-B7-INVARIANCE20.json"
SEED = 20261027
N_SAMPLE = 20
N_PREDICT = 384
EXPECT_FORWARD_SIDS = 388


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def pins_assertions(pins):
    p = []
    p.append(("model_bytes", pins["model"]["frozen_bytes"] == 8988110240))
    p.append(("dll_sha16", pins["dll"]["frozen_sha16"] == "9edbafa150700614"))
    p.append(("prompt_sha16",
              pins["extraction_prompt"]["sha16"] == "a6bc4f268f7711de"))
    p.append(("n_ctx", E.NCTX == 8192))
    p.append(("n_seq", E.NSEQ == 8))
    p.append(("temperature", pins["harness"]["temperature"] == 0))
    p.append(("seed_none", pins["harness"]["seed"] is None))
    p.append(("n_gpu_layers", E.NGL == 36))
    p.append(("harness_reset", pins["harness"]["engine_reset_before_and_after"]
              is True and pins["harness"].get("grammar") is None))
    p.append(("judge_layer_sha16",
              pins["judge_layer"]["sha16"] == "17c8e32a16b75947"))
    return [{"pin": k, "pass": bool(v)} for k, v in p]


def negative_pin_test():
    """A tampered GEN pin must make the frozen pins checker fail (SystemExit)."""
    try:
        EX.verify_pins("0000000000000000", GEN_BYTES, SENTS_SHA16, SENTS_BYTES)
        return {"pass": False, "rc": "no-error"}
    except SystemExit as e:
        return {"pass": True, "rc": 2, "detail": str(e)[:120]}
    except Exception as e:  # noqa: BLE001
        return {"pass": True, "rc": "exception", "detail": repr(e)[:120]}


def main():
    pins = EX.verify_pins(GEN_SHA16, GEN_BYTES, SENTS_SHA16, SENTS_BYTES)
    pin_rows = pins_assertions(pins)
    neg = negative_pin_test()

    sdoc = json.loads(SENTS.read_bytes().decode("utf-8"))
    if sdoc.get("n_sentences") != 623:
        raise SystemExit("SENTS n_sentences != 623")
    row_by_sid = {r["sid"]: r for r in sdoc.get("sentences") or []}
    raw = json.loads(RAW1.read_bytes().decode("utf-8"))
    recs = [r for r in raw.get("records") or []
            if r.get("route") == "model_extract" and r.get("raw_out") is not None]
    if len(recs) != EXPECT_FORWARD_SIDS:
        raise SystemExit("shard1 forward records %d != %d"
                         % (len(recs), EXPECT_FORWARD_SIDS))
    rng = random.Random(SEED)
    sample = rng.sample(recs, N_SAMPLE)

    t0 = time.perf_counter()
    sampler = EX.F.start_sampler()
    eng = None
    comparisons = []
    try:
        eng = EX.R2.open_engine()
        eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                          ctypes.c_char_p, ctypes.c_int,
                                          ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int]
        meta = EX.E.meta_from_log(eng, t0)
        for rec in sample:
            sid = rec["sid"]
            row = row_by_sid[sid]
            prompt = EX.build_prompt(row)
            prompt_sha = sha16(prompt.encode("utf-8"))
            eng.reset(0)
            buf = ctypes.create_string_buffer(131072)
            rc = int(eng.lib.kvshim_ask_at(eng.h, 0, prompt.encode("utf-8"),
                                           0, N_PREDICT, buf, 131072))
            eng.reset(0)
            raw_now = buf.value.decode("utf-8", "replace")
            old_raw = str(rec.get("raw_out"))
            old_prompt_sha = rec.get("prompt_sha16")
            old_rc = rec.get("rc")
            same_bytes = raw_now.encode("utf-8") == old_raw.encode("utf-8")
            comparisons.append({
                "sid": sid,
                "prompt_sha16": prompt_sha,
                "prompt_sha16_matches": (prompt_sha == old_prompt_sha),
                "rc": rc,
                "rc_matches": (rc == old_rc),
                "raw_old_sha16": sha16(old_raw.encode("utf-8")),
                "raw_new_sha16": sha16(raw_now.encode("utf-8")),
                "raw_identical": bool(same_bytes),
                "n_chars_old": len(old_raw),
                "n_chars_new": len(raw_now),
            })
        peak = EX.F.stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 3)
    finally:
        if eng is not None:
            try:
                eng.close()
            except Exception:  # noqa: BLE001
                pass
        try:
            EX.F.stop_sampler(sampler)
        except Exception:  # noqa: BLE001
            pass

    n_ident = sum(1 for c in comparisons
                  if c["raw_identical"] and c["prompt_sha16_matches"]
                  and c["rc_matches"])
    passed = (n_ident == N_SAMPLE and not any(not r["pass"] for r in pin_rows)
              and neg["pass"])
    out = {
        "schema": "m5c2_b7_invariance20_v1",
        "status": "pass" if passed else "未接上",
        "pass": passed,
        "rule": "RULING-M5C2-B7-EXTRACT-RESUME-A2 C1: new-session re-run of 20 "
                "shard1 forward sentences; raw_out byte-identical, prompt_sha16 "
                "and rc identical; any diff => merge must not be trusted",
        "seed": SEED,
        "n_sample": N_SAMPLE,
        "n_identical": n_ident,
        "shard1": {"path": "kvmem/m2_visibility/m5/out/_m5b7_extract_raw.json",
                   "sha16": sha16(RAW1.read_bytes()),
                   "bytes": RAW1.stat().st_size,
                   "n_forward_sentences": len(recs)},
        "pins": {k: pins[k] for k in ("gen", "sents", "extraction_prompt",
                                     "dll", "model", "harness", "judge_layer")},
        "pin_assertions": pin_rows,
        "pin_assertions_all_pass": all(r["pass"] for r in pin_rows),
        "negative_pin_test": neg,
        "engine_meta": meta,
        "n_forward": N_SAMPLE,
        "peak_gib": peak,
        "elapsed_s": elapsed,
        "comparisons": comparisons,
        "no_gpu_left_running": True,
    }
    write_json_atomic(OUT_ART, out)
    b = OUT_ART.read_bytes()
    print(json.dumps({
        "status": out["status"], "pass": passed,
        "n_identical": n_ident, "n_sample": N_SAMPLE,
        "out": "kvmem/m2_visibility/m5/out/M5C2-B7-INVARIANCE20.json",
        "sha16": sha16(b), "bytes": len(b),
        "peak_gib": peak, "elapsed_s": elapsed,
        "pin_assertions_all_pass": out["pin_assertions_all_pass"],
        "negative_pin_test": neg,
        "failed_sids": [c["sid"] for c in comparisons if not c["raw_identical"]],
    }, ensure_ascii=False, indent=1))
    return 0 if passed else 3


if __name__ == "__main__":
    sys.exit(main())