#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B4 judge runner — frozen rev5.1, dry-run by default.

Judge layers:
  0 empty source / deterministic abstain check
  1 one independent extraction forward per sentence (frozen prompt a6bc...)
  2 R1 / R2 / R3 / R4+ (short char-Jaccard <=4) / R_DERIVED+

No gold, no blind labels, no threshold/wordlist changes, no grammar.
Actual run only after LEAD says 开跑.  Each sentence is an independent forward
(engine reset before and after it), n_predict=384.
"""
import argparse
import ctypes
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
sys.path.insert(0, str(M5))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/engine"))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/m7/out"))
sys.path.insert(0, str(ROOT / "tools"))

import run_m5c2_rev4 as R4  # noqa: E402
import run_m5c2_rev4_1 as R41  # noqa: E402
import run_m5c2_rev5_offline as R5  # noqa: E402
import run_m5c2_rev5_1_offline as R51  # noqa: E402
import run_m5c2_rev2_order as CO  # noqa: E402
import run_m5c2_floor as F  # noqa: E402
import _e3gpu_run as E  # noqa: E402
import run_m5c2_r2 as R2  # noqa: E402

PRE = ROOT / "docs/_work/PREREG-M5-C2-B4.md"
PRE_SHA16 = "f30d89e30262b148"
PRE_BYTES = 10910
PRE_LINES = 132
SENT = OUT / "M5B4-SENTENCES.json"
SENT_SHA16 = "c349ca5a93192aac"
SENT_BYTES = 99636
ART = OUT / "M5B4-JUDGE.json"
RAW = OUT / "_m5b4_judge_raw.json"
PROMPT_SHA = "a6bc4f268f7711de"
JUDGE_VERSION = "rev5.1"
N_PREDICT = 384
TARGET_GIB = 8.0
FUSE_GIB = 8.6
LIMIT_S = 2400
FROZEN_DLL_SHA = "9edbafa150700614"


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def verify():
    b = PRE.read_bytes()
    if sha16(b) != PRE_SHA16 or len(b) != PRE_BYTES:
        raise SystemExit("B4 prereg changed")
    if b.decode("utf-8").count("\n") + 1 != PRE_LINES:
        raise SystemExit("B4 prereg line count changed")
    if "frozen=true" not in b.decode("utf-8"):
        raise SystemExit("B4 prereg not frozen")
    sb = SENT.read_bytes()
    if sha16(sb) != SENT_SHA16 or len(sb) != SENT_BYTES:
        raise SystemExit("M5B4-SENTENCES changed")
    if sha16(R4.REV4_TEMPLATE.encode("utf-8")) != PROMPT_SHA:
        raise SystemExit("frozen extraction prompt changed")
    return True


def load_sentences():
    d = json.loads(SENT.read_text(encoding="utf-8"))
    rows = d["sentences"]
    if len(rows) != 261:
        raise SystemExit("expected 261 B4 sentences, got %d" % len(rows))
    return rows


def build_prompt(row):
    return R4.REV4_TEMPLATE.format(
        source_text=row["source_text"], question=row.get("question", ""),
        sentence=row["text"])


def judge_layer2(items, sentence, source):
    """Frozen rev5.1 layer 2; no question dependency."""
    items_new = R51.judge_items(items, source)
    en, dd = R5.derived_plus(sentence, source)
    if en:
        return items_new, dd, "undecidable"
    if not items_new:
        return items_new, dd, "undecidable"
    if any(z["absent"] for z in items_new):
        return items_new, dd, "unsupported"
    return items_new, dd, "supported"


def dry_run(rows):
    prompts = []
    for row in rows[:3]:
        p = build_prompt(row)
        prompts.append({
            "sid": row["sid"], "qid": row["qid"], "scenario": row["scenario"],
            "source_text": row["source_text"], "question": row["question"],
            "sentence": row["text"], "prompt": p,
            "prompt_sha16": sha16(p.encode("utf-8")),
        })
    # Layer-0 dry scan only; no model.
    layer0 = []
    for row in rows:
        src = row["source_text"]
        sent = row["text"]
        if not str(src).strip():
            layer0.append({"sid": row["sid"], "route": "empty_source"})
        elif re.search(R4.ABSTAIN_REGEX_EFFECTIVE, sent):
            d = R4.deterministic_abstain(sent, src)
            layer0.append({"sid": row["sid"], "route": "abstain_check",
                           "verdict": d.get("verdict")})
    print(json.dumps({
        "schema": "m5c2_b4_judge_dry_run_v1",
        "status": "dry_run_only",
        "judge_version": JUDGE_VERSION,
        "prereg_sha16": PRE_SHA16,
        "sentences_sha16": SENT_SHA16,
        "n_sentences": len(rows),
        "n_predict": N_PREDICT,
        "prompt_template_sha16": PROMPT_SHA,
        "n_forward": 0,
        "no_gpu": True,
        "layer0_pre_scan_n": len(layer0),
        "layer0_pre_scan": layer0,
        "first_3_prompts": prompts,
    }, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--expected-prereg-sha16", default=None)
    a = ap.parse_args()
    verify()
    rows = load_sentences()
    if a.dry_run:
        return dry_run(rows)
    if not a.run:
        print("choose --dry-run or --run")
        return 2
    if a.expected_prereg_sha16 and a.expected_prereg_sha16 != PRE_SHA16:
        raise SystemExit("expected prereg sha does not match frozen B4")
    gate0, gate_exceptions = CO.gate_with_dwm_exception()
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_b4_judge_v1", "status": "未接上",
               "judge_version": JUDGE_VERSION, "prereg_sha16": PRE_SHA16,
               "reason": "host gate failed before load",
               "gate_before": gate0, "gate_exceptions": gate_exceptions,
               "n_forward": 0, "signals_sent": False, "no_model_loaded": True}
        write_json_atomic(ART, out)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 2
    sampler = F.start_sampler()
    t0 = time.perf_counter()
    eng = None
    results = []
    forwards = 0
    aborted = None
    try:
        eng = R2.open_engine()
        eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                          ctypes.c_char_p, ctypes.c_int,
                                          ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int]
        meta = E.meta_from_log(eng, t0)
        meta["frozen_dll_sha16"] = FROZEN_DLL_SHA
        meta["n_predict"] = N_PREDICT
        for row in rows:
            if time.perf_counter() - t0 > LIMIT_S:
                aborted = "timeout >%ds" % LIMIT_S
                break
            try:
                peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
            except Exception:  # noqa: BLE001
                peak = None
            if peak is not None and peak > FUSE_GIB:
                aborted = "VRAM fuse: peak %.4f > %.1f GiB" % (peak, FUSE_GIB)
                break
            src = row["source_text"]
            sent = row["text"]
            rec = {
                "sid": row["sid"], "qid": row["qid"], "scenario": row["scenario"],
                "source_text": src, "question": row["question"],
                "sentence": sent, "route": None, "raw_out": None,
                "items": [], "rule_hits": [], "verdict": None,
                "parse_ok": False, "parse_reason": None, "derived": False,
                "layer0": None,
            }
            if not str(src).strip():
                rec["route"] = "empty_source"
                rec["verdict"] = "unsupported"
                rec["parse_ok"] = True
                rec["layer0"] = {"route": "empty_source"}
                results.append(rec)
                continue
            if re.search(R4.ABSTAIN_REGEX_EFFECTIVE, sent):
                det = R4.deterministic_abstain(sent, src)
                rec["route"] = "abstain_check"
                rec["verdict"] = det["verdict"]
                rec["parse_ok"] = True
                rec["layer0"] = det
                results.append(rec)
                continue
            prompt = build_prompt(row)
            rec["prompt_sha16"] = sha16(prompt.encode("utf-8"))
            eng.reset(0)
            buf = ctypes.create_string_buffer(131072)
            rc = int(eng.lib.kvshim_ask_at(eng.h, 0, prompt.encode("utf-8"),
                                           0, N_PREDICT, buf, 131072))
            raw = "" if rc < 0 else buf.value.decode("utf-8", "replace")
            eng.reset(0)
            forwards += 1
            rec["route"] = "model_extract"
            rec["raw_out"] = raw
            items, parse_ok, reason = R41.parse_extraction(raw, src)
            rec["parse_ok"] = parse_ok
            rec["parse_reason"] = reason
            items2, dd, verdict = judge_layer2(items, sent, src)
            rec["items"] = items2
            rec["rule_hits"] = [h for z in items2 for h in z["rule_hits"]]
            rec["derived"] = bool(dd.get("enabled"))
            rec["derived_detail"] = dd
            if dd.get("enabled"):
                rec["rule_hits"].append({"rule": "R_DERIVED+",
                                         "reason": "all_values_composable",
                                         "span": dd.get("keyword", "")})
            if not parse_ok:
                rec["verdict"] = "parse_fail"
            else:
                rec["verdict"] = verdict
            results.append(rec)
            write_json_atomic(RAW, {"n_forward": forwards, "aborted": aborted,
                                    "results": results})
        gate1, gate_exceptions_after = CO.gate_with_dwm_exception()
        peak = F.stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 3)
        abstain_sids = [r["sid"] for r in results if r.get("route") == "abstain_check"]
        layer0_skipped = len([r for r in results if r.get("layer0") is not None])
        out = {
            "schema": "m5c2_b4_judge_v1",
            "status": "已读数" if aborted is None else "未接上",
            "judge_version": JUDGE_VERSION,
            "prereg_sha16": PRE_SHA16,
            "sentences_sha16": SENT_SHA16,
            "prompt_sha16": PROMPT_SHA,
            "actual_prompt_sha16": sha16(R4.REV4_TEMPLATE.encode("utf-8")),
            "prompt_matches_frozen": sha16(R4.REV4_TEMPLATE.encode("utf-8")) == PROMPT_SHA,
            "n_sentences": len(rows),
            "n_forward": forwards,
            "n_forward_planned": len(rows) - layer0_skipped,
            "layer0_skipped": layer0_skipped,
            "abstain_sids": abstain_sids,
            "abstain_gold_mix": "deferred_until_lead_gold",
            "aborted": aborted,
            "elapsed": elapsed,
            "elapsed_s": elapsed,
            "peak_vram": peak,
            "peak_gib": peak,
            "target_gib": TARGET_GIB,
            "fuse_gib": FUSE_GIB,
            "gate_before": gate0,
            "gate_after": gate1,
            "gate_exceptions": gate_exceptions,
            "gate_exceptions_after": gate_exceptions_after,
            "signals_sent": False,
            "no_parent_signals": True,
            "no_grammar": True,
            "no_model_switch": True,
            "no_prompt_changes": True,
            "no_rule_changes": True,
            "no_threshold_changes": True,
            "no_gold": True,
            "no_blind_labels_read": True,
            "question_not_used_in_judge": True,
            "items": results,
        }
        write_json_atomic(ART, out)
        print(json.dumps({k: out[k] for k in ("status", "judge_version", "n_forward",
                                              "n_sentences", "elapsed", "peak_vram",
                                              "signals_sent", "gate_exceptions")},
                         ensure_ascii=False, indent=1))
        return 0 if aborted is None else 3
    finally:
        if eng is not None:
            try:
                eng.close()
            except Exception:  # noqa: BLE001
                pass
        try:
            F.stop_sampler(sampler)
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main())