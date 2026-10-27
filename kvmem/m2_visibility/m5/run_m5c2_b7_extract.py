#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B6 extraction runner (GPU: one forward per b6 sentence).

Split architecture (same as b5):
  run_m5c2_b7_gen.py    -> out/M5C2-B7-GEN.json    (40 answers, one-shot)
  run_m5c2_b7_split.py  -> out/M5C2-B7-SENTS.json  (frozen split rules)
  this script           -> out/M5C2-B7-EXTRACT.json (extraction only)
  run_m5c2_b7_decide.py -> out/M5C2-B7-DECIDE.json / M5C2-B7-RATES.json (CPU)

Frozen inputs (asserted at startup):
  PREREG-M5-C2-B6.md     ac27d47d3a3efff9 / 17,374 B
  M5C2-B7-SENTENCES.json 23588ec099ca9255 / 9,482 B (fixed questions)
  M5C2-B7-GEN.json       produced by the one-shot GPU pass (pinned at run time)
  M5C2-B7-SENTS.json     produced by run_m5c2_b7_split.py --gen-b7
  prompt run_m5c2_rev4.REV4_TEMPLATE a6bc4f268f7711de
  judge  run_m5c2_rev7_1_offline.py  88256d274c9993cc

Modes (exactly one):
  --dry-run    static pin/count validation only (no model, writes nothing)
  --gate-check host gate only (no model, no forward)
  --run        the one and only GPU extraction pass

Gate exceptions: `--allow-gui-procs "dwm,DSH NEXT"` is an explicit, default-off
opt-in for the frozen S4 ruling v1.1 (admission requires n_forward == 0; evidence
= enriched pid+exe_path samples; post-run recheck is admission-rule independent).
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
import run_m5c2_floor as F  # noqa: E402
import _e3gpu_run as E  # noqa: E402
import run_m5c2_r2 as R2  # noqa: E402
import run_m5c2_b7_gen as BG6  # noqa: E402  (frozen host-gate contract)

RULING = ROOT / "docs/_work/RULING-M5C2-B7.md"
RULING_SHA16 = "3dfafd1253f0a833"
RULING_BYTES = 9425
ADDENDUM = ROOT / "docs/_work/RULING-M5C2-B7-A1.md"
ADDENDUM_SHA16 = "eef371f776d1d8a9"
ADDENDUM_BYTES = 1513
QS = OUT / "M5C2-B7-QUESTIONS.json"
QS_SHA16 = "f1f059539453d562"
QS_BYTES = 15964
GEN = OUT / "M5C2-B7-GEN.json"
GEN_SHA16 = None   # frozen after the b7 GPU pass (--expect-gen-sha16)
GEN_BYTES = None
SENTS = OUT / "M5C2-B7-SENTS.json"
SENTS_SHA16 = None  # frozen after the b7 split (--expect-sents-sha16)
SENTS_BYTES = None
SENT_N = None       # derived after split
ART = OUT / "M5C2-B7-EXTRACT.json"
RAW = OUT / "_m5b7_extract_raw.json"
REFUSED = OUT / "M5C2-B7-EXTRACT-HOSTGATE-REFUSED.json"
PROMPT_SHA = "a6bc4f268f7711de"
JUDGE_PRE_SHA16 = "09d6f1b163ea0b84"
R71_PATH = M5 / "run_m5c2_rev7_2_offline.py"
R71_SHA16 = "17c8e32a16b75947"
R71_BYTES = 38200
N_PREDICT = 384
TARGET_GIB = 8.0
FUSE_GIB = 8.6
LIMIT_S = 3600
FROZEN_DLL_SHA = "9edbafa150700614"
MODEL_BYTES = 8988110240


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def rel(p):
    return BG6.rel(p)


def write_json_atomic(path, obj):
    BG6.write_json_atomic(path, obj)


class PendingArtifacts(SystemExit):
    """GEN/SENTS not produced yet: dry-run reports it instead of failing."""


def load_sents():
    if not SENTS.exists():
        raise PendingArtifacts(
            "missing %s (run the b7 GPU generation then "
            "run_m5c2_b7_split.py --gen-b7)" % rel(SENTS))
    sb = SENTS.read_bytes()
    d = json.loads(sb.decode("utf-8"))
    rows = d.get("sentences") or []
    if d.get("schema") != "m5c2_b7_sents_v1":
        raise SystemExit("unexpected b7 SENTS schema %r" % (d.get("schema"),))
    if not rows:
        raise SystemExit("b7 SENTS holds no sentences")
    gen_meta = d.get("gen") or {}
    if gen_meta.get("sha16") is None:
        raise SystemExit("b7 SENTS does not carry a gen sha16 pin")
    return d, rows, {"path": rel(SENTS), "sha16": sha16(sb), "bytes": len(sb)}


def verify_pins(expect_gen_sha=None, expect_gen_bytes=None,
                expect_sents_sha=None, expect_sents_bytes=None):
    pb = RULING.read_bytes()
    if sha16(pb) != RULING_SHA16 or len(pb) != RULING_BYTES:
        raise SystemExit("RULING-M5C2-B7 changed: %s / %d B"
                         % (sha16(pb), len(pb)))
    ab = ADDENDUM.read_bytes()
    if sha16(ab) != ADDENDUM_SHA16 or len(ab) != ADDENDUM_BYTES:
        raise SystemExit("RULING-M5C2-B7-A1 changed: %s / %d B"
                         % (sha16(ab), len(ab)))
    qb = QS.read_bytes()
    if sha16(qb) != QS_SHA16 or len(qb) != QS_BYTES:
        raise SystemExit("M5C2-B7-QUESTIONS.json changed: %s / %d B"
                         % (sha16(qb), len(qb)))
    if not GEN.exists():
        raise PendingArtifacts("missing %s (run_m5c2_b7_gen.py --run first)"
                               % rel(GEN))
    gb = GEN.read_bytes()
    gen_sha, gen_bytes = sha16(gb), len(gb)
    want_gen_sha = expect_gen_sha or GEN_SHA16
    want_gen_bytes = int(expect_gen_bytes) if expect_gen_bytes else GEN_BYTES
    if gen_sha != want_gen_sha or gen_bytes != want_gen_bytes:
        raise SystemExit("b7 GEN does not match the frozen pin: %s/%d B "
                         "(expected %s/%d B)"
                         % (gen_sha, gen_bytes, want_gen_sha, want_gen_bytes))
    gen = json.loads(gb.decode("utf-8"))
    if gen.get("aborted") is not None:
        raise SystemExit("b7 GEN aborted=%r; extraction refuses to start"
                         % (gen.get("aborted"),))
    if len(gen.get("qa") or []) != 75 or int(gen.get("n_forward") or 0) != 75:
        raise SystemExit("b7 GEN does not hold 75/75 answers")
    sdoc, rows, sents_meta = load_sents()
    if (sdoc.get("gen") or {}).get("sha16") != gen_sha:
        raise SystemExit("b7 SENTS was split from a different b7 GEN")
    want_sents_sha = expect_sents_sha or SENTS_SHA16
    want_sents_bytes = (int(expect_sents_bytes) if expect_sents_bytes
                        else SENTS_BYTES)
    if (sents_meta["sha16"] != want_sents_sha
            or sents_meta["bytes"] != want_sents_bytes):
        raise SystemExit("b7 SENTS does not match the frozen pin: %s/%d B "
                         "(expected %s/%d B)"
                         % (sents_meta["sha16"], sents_meta["bytes"],
                            want_sents_sha, want_sents_bytes))
    if SENT_N is not None and len(rows) != SENT_N:
        raise SystemExit("b7 SENTS holds %d sentences, frozen pin says %d"
                         % (len(rows), SENT_N))
    prompt_sha = sha16(R4.REV4_TEMPLATE.encode("utf-8"))
    if prompt_sha != PROMPT_SHA:
        raise SystemExit("frozen extraction prompt changed: %s" % prompt_sha)
    rb = R71_PATH.read_bytes()
    if sha16(rb) != R71_SHA16 or len(rb) != R71_BYTES:
        raise SystemExit("rev7.2 judge code changed: %s / %d B"
                         % (sha16(rb), len(rb)))
    return {
        "ruling": {"path": rel(RULING), "sha16": RULING_SHA16,
                   "bytes": RULING_BYTES},
        "addendum": {"path": rel(ADDENDUM), "sha16": ADDENDUM_SHA16,
                     "bytes": ADDENDUM_BYTES},
        "questions": {"path": rel(QS), "sha16": QS_SHA16, "bytes": QS_BYTES},
        "gen": {"path": rel(GEN), "sha16": gen_sha, "bytes": gen_bytes,
                "n_forward": 40, "answers_nonempty": gen.get("answers_nonempty"),
                "one_shot_consumed": gen.get("one_shot_consumed")},
        "sents": dict(sents_meta, n_sentences=len(rows)),
        "extraction_prompt": {"sha16": prompt_sha,
                              "source": "run_m5c2_rev4.REV4_TEMPLATE"},
        "judge_layer": {"version": "rev7.2", "code": rel(R71_PATH),
                        "sha16": R71_SHA16, "bytes": R71_BYTES,
                        "prereg_sha16": JUDGE_PRE_SHA16},
        "dll": {"frozen_sha16": FROZEN_DLL_SHA},
        "model": {"frozen_bytes": MODEL_BYTES},
        "harness": {"n_predict": N_PREDICT, "temperature": 0,
                    "sampling": "argmax_greedy", "seed": None, "grammar": None,
                    "engine_reset_before_and_after": True,
                    "no_parent_signals": True, "no_network": True},
    }


def verify_gate_ruling():
    return BG6.verify_gate_ruling()


def host_gate(allow_gui=None, ruling=None, n_forward=None):
    return BG6.host_gate_with_exception(allow_gui, ruling, n_forward)


def recheck_exception_after(gate_before, gate_after=None):
    return BG6.recheck_exception_after(gate_before, gate_after)


def build_prompt(row):
    return R4.REV4_TEMPLATE.format(
        source_text=row["source_text"], question=row.get("question", ""),
        sentence=row["text"])


def layer0_route(row):
    src = str(row.get("source_text") or "")
    sent = str(row.get("text") or "")
    if not src.strip():
        return "empty_source", {"route": "empty_source"}
    if re.search(R4.ABSTAIN_REGEX_EFFECTIVE, sent):
        det = R4.deterministic_abstain(sent, src)
        return "abstain_check", det
    return None, None


def dry_run(pins, rows, allow_gui=None, ruling=None):
    probes = []
    layer0 = {"empty_source": 0, "abstain_check": 0}
    for row in rows:
        route, det = layer0_route(row)
        if route:
            layer0[route] += 1
    for row in rows[:3]:
        p = build_prompt(row)
        probes.append({"sid": row["sid"], "qid": row["qid"],
                       "source_len": len(row["source_text"]),
                       "sentence_len": len(row["text"]),
                       "prompt_sha16": sha16(p.encode("utf-8")),
                       "prompt_prefix": p[:120]})
    print(json.dumps({
        "schema": "m5c2_b7_extract_dry_run_v1",
        "status": "dry_run_only",
        "pins": pins,
        "n_sentences": len(rows),
        "n_questions": len({r["qid"] for r in rows}),
        "layer0_pre_scan": layer0,
        "n_forward_planned": len(rows) - layer0["empty_source"]
                             - layer0["abstain_check"],
        "n_predict": N_PREDICT,
        "prompt_probes": probes,
        "gate_exception_option": {"enabled": bool(allow_gui), "ruling": ruling,
                                  "allowlist": list(BG6.GUI_ALLOWLIST),
                                  "default_off": True},
        "n_forward": 0, "no_gpu": True, "no_model_loaded": True,
        "writes_any_file": False,
    }, ensure_ascii=False, indent=1))
    return 0


def write_refused(mode, gate, exceptions, pins, ruling=None):
    out = {
        "schema": "m5c2_b7_extract_hostgate_refused_v1",
        "status": "未接上",
        "mode": mode,
        "reason": "host gate failed before any model load",
        "pins": pins,
        "gate": gate,
        "gate_exceptions": exceptions,
        "n_forward": 0,
        "no_model_loaded": True,
        "signals_sent": False,
        "no_parent_signals": True,
        "abort_class": "device_gate_failed",
        "rerun_allowed": True,
    }
    if ruling:
        out["gate_ruling"] = ruling
        out["allow_gui_procs"] = gate.get("allow_gui_procs")
    write_json_atomic(REFUSED, out)
    print(json.dumps({k: out[k] for k in ("status", "mode", "reason",
                                          "gate_exceptions")},
                     ensure_ascii=False, indent=1))
    return 2


def run(pins, rows, allow_gui=None, ruling=None):
    if ART.exists():
        try:
            prev = json.loads(ART.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            prev = None
        if prev and prev.get("aborted") is None and int(prev.get("n_forward") or 0) > 0:
            raise SystemExit("REFUSE: %s already holds a complete extraction; "
                             "do not re-run" % rel(ART))
    gate0, exc0 = host_gate(allow_gui, ruling, n_forward=0)
    if not gate0.get("gate_ok"):
        return write_refused("extract_run", gate0, exc0, pins, ruling)
    t0 = time.perf_counter()
    sampler = F.start_sampler()
    eng = None
    recs = []
    forwards = 0
    attempted = 0
    aborted = None
    abort_class = None
    try:
        eng = R2.open_engine()
        eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                          ctypes.c_char_p, ctypes.c_int,
                                          ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int]
        meta = E.meta_from_log(eng, t0)
        for row in rows:
            if time.perf_counter() - t0 > LIMIT_S:
                aborted = "timeout >%ds" % LIMIT_S
                abort_class = "timeout_mid"
                break
            try:
                peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
            except Exception:  # noqa: BLE001
                peak = None
            if peak is not None and peak > FUSE_GIB:
                aborted = "VRAM fuse: peak %.4f > %.1f GiB" % (peak, FUSE_GIB)
                abort_class = "vram_fuse_mid"
                break
            rec = {"sid": row["sid"], "qid": row["qid"],
                   "scenario": row["scenario"], "text": row["text"],
                   "source_text": row["source_text"], "route": None,
                   "layer0": None, "prompt_sha16": None, "raw_out": None,
                   "rc": None, "elapsed_s": None, "parse_ok": None,
                   "parse_reason": None, "items": None, "n_items": 0}
            route, det = layer0_route(row)
            if route:
                rec["route"] = route
                rec["layer0"] = det
                rec["parse_ok"] = True
                rec["items"] = []
                recs.append(rec)
                write_json_atomic(RAW, {"schema": "m5c2_b7_extract_raw_v1",
                                        "n_forward": forwards,
                                        "aborted": aborted, "records": recs})
                continue
            prompt = build_prompt(row)
            rec["route"] = "model_extract"
            rec["prompt_sha16"] = sha16(prompt.encode("utf-8"))
            eng.reset(0)
            buf = ctypes.create_string_buffer(131072)
            ts = time.perf_counter()
            rc = int(eng.lib.kvshim_ask_at(eng.h, 0, prompt.encode("utf-8"),
                                           0, N_PREDICT, buf, 131072))
            rec["elapsed_s"] = round(time.perf_counter() - ts, 3)
            eng.reset(0)
            attempted += 1
            if rc < 0:
                rec["rc"] = rc
                rec["error"] = "kvshim_ask_at returned %d" % rc
                recs.append(rec)
                aborted = "forward failed: rc=%d at %s" % (rc, row["sid"])
                abort_class = "forward_failed"
                write_json_atomic(RAW, {"schema": "m5c2_b7_extract_raw_v1",
                                        "n_forward": forwards,
                                        "n_forward_attempted": attempted,
                                        "aborted": aborted, "records": recs})
                break
            raw = buf.value.decode("utf-8", "replace")
            forwards += 1
            rec["rc"] = rc
            rec["raw_out"] = raw
            try:
                items, parse_ok, reason = R41.parse_extraction(
                    raw, str(row["source_text"]))
            except Exception as e:  # noqa: BLE001
                items, parse_ok, reason = [], False, "parse exception: %r" % (e,)
            rec["parse_ok"] = bool(parse_ok)
            rec["parse_reason"] = reason
            rec["items"] = items
            rec["n_items"] = len(items)
            recs.append(rec)
            write_json_atomic(RAW, {"schema": "m5c2_b7_extract_raw_v1",
                                    "n_forward": forwards,
                                    "n_forward_attempted": attempted,
                                    "aborted": aborted, "records": recs})
        gate1, _exc1 = BG6.host_gate()   # strict post-run record
        recheck = recheck_exception_after(gate0)
        gate_exceptions_after = (recheck.get("after") if allow_gui else None)
        if recheck.get("checked") and not recheck.get("ok"):
            aborted = ("gate exception pid/exe_path recheck failed after run: %r"
                       % (recheck.get("failures"),))
            abort_class = "gate_exception_recheck_failed"
        peak = F.stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 3)
        layer0_n = len([r for r in recs if r.get("layer0") is not None])
        out = {
            "schema": "m5c2_b7_extract_v1",
            "status": "已抽取未判定" if aborted is None else "未接上",
            "pins": pins,
            "engine_meta": meta,
            "n_sentences": len(rows),
            "n_forward": forwards,
            "n_forward_attempted": attempted,
            "layer0_skipped": layer0_n,
            "aborted": aborted,
            "abort_class": abort_class,
            "elapsed": elapsed,
            "elapsed_s": elapsed,
            "peak_gib": peak,
            "target_gib": TARGET_GIB,
            "fuse_gib": FUSE_GIB,
            "n_predict": N_PREDICT,
            "temperature": 0,
            "sampling": "argmax_greedy",
            "seed": None,
            "grammar": None,
            "gate_before": gate0,
            "gate_after": gate1,
            "gate_exceptions": exc0,
            "gate_exceptions_after": gate_exceptions_after,
            "gate_exception_samples": gate0.get("gate_exception_samples"),
            "gate_exception_match_by": gate0.get("match_by"),
            "gate_exception_strict_count_recorded": gate0.get(
                "strict_count_recorded"),
            "gate_exception_enriched_count_used": gate0.get(
                "enriched_count_used"),
            "gate_exception_recheck": recheck,
            "signals_sent": False,
            "no_parent_signals": True,
            "no_grammar": True,
            "no_verdict": True,
            "no_rates": True,
            "no_gold": True,
            "no_blind_labels_read": True,
            "no_rule_changes": True,
            "no_threshold_changes": True,
            "no_network": True,
            "records": recs,
        }
        if allow_gui:
            out["allow_gui_procs"] = sorted(set(allow_gui))
            out["gate_ruling"] = ruling
            out["gate_exception_policy"] = gate0.get("gate_exception_policy")
            out["gate_exception_applied"] = bool(gate0.get("gate_exception_applied"))
            out["gate_exception_note"] = gate0.get("gate_exception_note")
            out["gate_exception_signoff_inputs"] = gate0.get(
                "gate_exception_signoff_inputs")
            out["gate_exception_total_bytes"] = gate0.get("exception_total_bytes")
            out["gate_exception_budget_bytes"] = gate0.get("exception_budget_bytes")
            if gate0.get("gate_exception_applied"):
                seen_names = []
                for e in (exc0 or []):
                    n = str(e.get("name") or "").strip()
                    if n and n not in seen_names:
                        seen_names.append(n)
                out["gate_exception_disclosure"] = (
                    "strict gate 在 %s 拒绝（gpu_procs_gt256mb=%s: %s）；本次依 "
                    "RULING-M5C2-B5-GATE-EXCEPTION v1.1 以具名例外放行；例外清单与"
                    "用量见 gate_exceptions[]"
                    % (time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                       gate0.get("gpu_procs_gt256mb"), ", ".join(seen_names)))
                out["gate_exception_disclosure_names"] = seen_names
        write_json_atomic(ART, out)
        print(json.dumps({k: out[k] for k in ("status", "n_forward",
                                              "n_sentences", "elapsed_s",
                                              "peak_gib", "aborted",
                                              "abort_class", "layer0_skipped")},
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--gate-check", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--expect-gen-sha16", default=None)
    ap.add_argument("--expect-gen-bytes", default=None)
    ap.add_argument("--expect-sents-sha16", default=None)
    ap.add_argument("--expect-sents-bytes", default=None)
    ap.add_argument("--allow-gui-procs", default=None,
                    help="explicit S4 gate-exception opt-in v1.1 (default off; "
                         "requires n_forward==0)")
    a = ap.parse_args()
    modes = [m for m in (a.dry_run, a.gate_check, a.run) if m]
    if len(modes) != 1:
        print("choose exactly one of --dry-run / --gate-check / --run")
        return 2
    allow_gui = None
    ruling = None
    if a.allow_gui_procs:
        allow_gui = [x for x in a.allow_gui_procs.split(",") if x.strip()]
        ruling = verify_gate_ruling()
    try:
        pins = verify_pins(a.expect_gen_sha16, a.expect_gen_bytes,
                           a.expect_sents_sha16, a.expect_sents_bytes)
        _sdoc, rows, _meta = load_sents()
    except PendingArtifacts as e:
        if a.dry_run:
            print(json.dumps({"schema": "m5c2_b7_extract_dry_run_v1",
                              "status": "pending_generation",
                              "reason": str(e),
                              "expected": {"gen": rel(GEN), "sents": rel(SENTS)},
                              "n_forward": 0, "no_gpu": True,
                              "no_model_loaded": True,
                              "writes_any_file": False},
                             ensure_ascii=False, indent=1))
            return 0
        raise
    if a.dry_run:
        return dry_run(pins, rows, allow_gui, ruling)
    if a.gate_check:
        gate, exc = host_gate(allow_gui, ruling, n_forward=0)
        if not gate.get("gate_ok"):
            return write_refused("extract_gate_check", gate, exc, pins, ruling)
        out = {"schema": "m5c2_b7_extract_gate_check_v1", "status": "gate_ok",
               "gate": gate, "gate_exceptions": exc,
               "gate_exception_samples": gate.get("gate_exception_samples"),
               "gate_exception_match_by": gate.get("match_by"),
               "gate_exception_strict_count_recorded": gate.get(
                   "strict_count_recorded"),
               "gate_exception_enriched_count_used": gate.get(
                   "enriched_count_used"),
               "gate_exception_applied": bool(gate.get("gate_exception_applied")),
               "n_forward": 0, "no_model_loaded": True, "no_gpu_work": True}
        if allow_gui:
            out["allow_gui_procs"] = sorted(set(allow_gui))
            out["gate_ruling"] = ruling
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    return run(pins, rows, allow_gui, ruling)


if __name__ == "__main__":
    sys.exit(main())