#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SUPPLEMENTARY GBNF-constrained diagnostic over the same 31 frozen rows.

This is NOT the preregistered floor run and does not replace
M5C2-FLOOR.json.  It exists only because the unconstrained floor run produced
31/31 parse_fail (the model continued with "，如A/B" instead of a single
letter).  It keeps the prompt byte-for-byte identical, but wraps generation in
the frozen GBNF grammar, so each output is a parsable A/B/C.  The artifact is
clearly marked non_prereg=true.
"""
import ctypes
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
sys.path.insert(0, str(M5))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/m7/out"))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/engine"))
sys.path.insert(0, str(ROOT / "tools"))

import _e3gpu_run as E  # noqa: E402
import run_m5c2_floor as F  # noqa: E402

ART = OUT / "M5C2-FLOOR-GBNF-EXPLORATORY.json"
LOG = OUT / "_m5c2_floor_gbnf_exploratory.log"
GRAMMAR = 'root ::= "A" | "B" | "C"'
ROOT_RULE = "root"


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def main():
    fx = F.verify_inputs()
    rows = F.build_rows(fx)
    gate0 = F.R2.host_gate()
    host0 = E.host_check("floor_gbnf_before")
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_floor_gbnf_exploratory_v1", "non_prereg": True,
               "status": "未接上", "reason": "host gate failed before load",
               "host_gate_before": gate0, "host_before": host0, "no_model_loaded": True,
               "signals_sent": False}
        write_json_atomic(ART, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2
    dll = F.verify_gbnf_dll()
    sampler = F.start_sampler()
    t0 = time.perf_counter()
    L = h = None
    meta = None
    cases = []
    aborted = None
    try:
        L, h = F.open_gbnf_engine()
        meta = {"pid": os.getpid(), "load_s": round(time.perf_counter() - t0, 3),
                "vulkan_imported": E.vulkan_loaded(), "dll_sha16": dll["sha16"],
                "n_gpu_layers_input": E.NGL, "n_ctx": E.NCTX, "n_seq": E.NSEQ, "kv": E.KV,
                "model_bytes": Path(E.MODEL).stat().st_size}
        for i, r in enumerate(rows):
            if time.perf_counter() - t0 > 900:
                aborted = "segment timeout >900s"
                break
            try:
                peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
            except Exception:  # noqa: BLE001
                peak = None
            if peak is not None and peak > 8.6:
                aborted = "VRAM fuse: peak %.4f > 8.6 GiB" % peak
                break
            L.kvshim_reset(h, 0)
            buf = ctypes.create_string_buffer(16384)
            top_ids = (ctypes.c_int * 3)()
            top_probs = (ctypes.c_float * 3)()
            n_allowed = ctypes.c_int(0)
            n = int(L.kvshim_ask_grammar_probs(
                h, 0, r["prompt"].encode("utf-8"), 0,
                GRAMMAR.encode("utf-8"), ROOT_RULE.encode("utf-8"),
                4, buf, 16384, 3, top_ids, top_probs, ctypes.byref(n_allowed)))
            raw = "" if n < 0 else buf.value.decode("utf-8", "replace")
            ch = F.parse(raw)
            verdict = {"A": "supported", "B": "unsupported", "C": "undecidable"}.get(ch)
            ok = verdict is not None
            if not ok:
                verdict = "parse_fail"
            probs = [{"token_id": int(top_ids[j]), "prob": float(top_probs[j])} for j in range(3)]
            cases.append({
                "fid": r["fid"], "arm": r["arm"], "arm_name": r["arm_name"],
                "qid": r["qid"], "prompt_sha16": r["prompt_sha16"],
                "raw_out": raw, "rc": n, "letter": ch, "verdict": verdict,
                "parse_ok": ok,
                "top_probs": probs, "top_probs_n": 3,
                "top_probs_sum": round(sum(float(top_probs[j]) for j in range(3)), 9),
                "n_allowed": int(n_allowed.value),
                "peak_gib_running": peak, "forward_idx": i + 1,
            })
            L.kvshim_reset(h, 0)
    except Exception as e:  # noqa: BLE001
        aborted = "exception: %r" % (e,)
    finally:
        if L is not None and h is not None:
            try:
                L.kvshim_close(h)
            except Exception:  # noqa: BLE001
                pass
        time.sleep(0.5)
        peak = F.stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 1)
        gate1 = F.R2.host_gate()
        host1 = E.host_check("floor_gbnf_after")

    complete = len(cases) == 31 and aborted is None
    parse_fail = sum(1 for c in cases if not c["parse_ok"])
    arm_rate = {}
    for a in (1, 2, 3, 4, 5):
        ar = [c for c in cases if c["arm"] == a]
        arm_rate[str(a)] = {
            "n": len(ar), "A": sum(1 for c in ar if c["verdict"] == "supported"),
            "B": sum(1 for c in ar if c["verdict"] == "unsupported"),
            "C": sum(1 for c in ar if c["verdict"] == "undecidable"),
            "parse_fail": sum(1 for c in ar if not c["parse_ok"]),
        }
    parse_bad = parse_fail > 3
    if parse_bad:
        r = {k: None for k in ("R1", "R2", "R3", "R4", "R5")}
        any_trigger = None
        can_judge = None
    else:
        r = {
            "R1": arm_rate["2"]["A"] > 0,
            "R2": arm_rate["1"]["A"] > 0,
            "R3": arm_rate["3"]["A"] > 1.0 / 6.0,
            "R4": arm_rate["4"]["B"] > 1.0 / 6.0,
            "R5": arm_rate["5"]["A"] < 6.0 / 7.0,
        }
        any_trigger = any(r.values())
        can_judge = not any_trigger
    out = {
        "schema": "m5c2_floor_gbnf_exploratory_v1",
        "non_prereg": True,
        "purpose": "supplementary because unconstrained floor had parse_fail 31/31",
        "status": "未接上" if (not complete or parse_bad) else "已判定",
        "complete": complete, "aborted": aborted, "n_done": len(cases),
        "n_planned": 31, "parse_fail_n": parse_fail,
        "arm_rate": arm_rate,
        "R1": r["R1"], "R2": r["R2"], "R3": r["R3"], "R4": r["R4"], "R5": r["R5"],
        "R_triggered": r, "any_trigger": any_trigger,
        "14B_can_judge": can_judge,
        "grammar": GRAMMAR, "root": ROOT_RULE,
        "n_probs_requested": 3, "post_sampling_probs": True,
        "prob_mode": "post_grammar_softmax_over_allowed_tokens",
        "dll": dll,
        "cases": cases,
        "prompts_first3": [{"fid": x["fid"], "prompt": x["prompt"], "sha16": x["prompt_sha16"]}
                           for x in rows[:3]],
        "device": meta, "host_gate_before": gate0, "host_gate_after": gate1,
        "host_before": host0, "host_after": host1,
        "peak_gib": peak, "target_gib": 8.0, "fuse_gib": 8.6,
        "elapsed_s": elapsed, "segment_limit_s": 900,
        "signals_sent": False, "no_parent_signals": True,
        "prompt_bytes_unchanged": True, "no_b2_blind_labels": True,
        "no_accuracy_or_f1": True, "no_stage2": True,
    }
    write_json_atomic(ART, out)
    print(json.dumps({k: out[k] for k in ("status", "n_done", "complete", "aborted",
                                          "parse_fail_n", "arm_rate", "R1", "R2", "R3",
                                          "R4", "R5", "14B_can_judge", "peak_gib",
                                          "elapsed_s", "dll", "device")},
                     ensure_ascii=False, indent=2))
    return 0 if (complete and not parse_bad) else 2


if __name__ == "__main__":
    sys.exit(main())