#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B7 extract RESUME (shard2) — CPU-written / GPU-run companion.

Context: the frozen `run_m5c2_b7_extract.py` (2971b94397b18181) is fail-closed
with LIMIT_S=3600; a b7'-scale pass (623 sentences) can exceed that and stop as
timeout_mid.  RULING-M5C2-B7-EXTRACT-RESUME (LEAD) allows an offline S4 redo in
two shards: shard1 = the sentences already completed in the frozen pass's RAW
(in `_m5b7_extract_raw.json`), shard2 = the remaining sids taken by *sid set*
from the frozen SENTS file (never chosen by content).  The frozen script is NOT
modified; this new script reuses its prompt/layer0/gate/pins code by importing
it read-only.

Hard requirements enforced here:
  * strict host gate (NO --allow-gui-procs); same model/dll/prompt/n_predict=384;
  * shard2 = SENTS sids not present in shard1 (ordered by SENTS);
  * merge = shard1 records + shard2 records, unique sids, complete against the
    frozen SENTS file (623/623 for b7'), ordered exactly as SENTS;
  * any duplicate / missing sid => FAIL, never write a "completed" EXTRACT;
  * provenance: both shard RAW shas + sid sets + counts in the EXTRACT.

Modes:
  --dry-run   in-memory merge/dedup/completeness tests on synthetic shards (no
              engine, no GPU, no real artifact write) => exit 0 when all pass
  (default)   reads shard1 RAW, runs only the remaining sids, writes shard2 RAW,
              merges and writes out/M5C2-B7-EXTRACT.json only if complete.
"""
import argparse
import ctypes
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True   # keep frozen dirs untouched (no pycache writes)

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
sys.path.insert(0, str(M5))

import run_m5c2_b7_extract as EX  # noqa: E402  (frozen, read-only import)

DEFAULT_RAW1 = OUT / "_m5b7_extract_raw.json"
DEFAULT_SENTS = OUT / "M5C2-B7-SENTS.json"
DEFAULT_RAW2 = OUT / "_m5b7_extract_raw_shard2.json"
DEFAULT_OUT = OUT / "M5C2-B7-EXTRACT.json"
REFUSED = OUT / "M5C2-B7-EXTRACT-RESUME-HOSTGATE-REFUSED.json"
FAILED = OUT / "M5C2-B7-EXTRACT-RESUME-INCOMPLETE.json"
RESUME_LIMIT_S = 4200   # shard2 is ~half the set; margin over the observed 5-17 s/forward
EXPECT_N = 623

sha16 = EX.sha16
rel = EX.rel
write_json_atomic = EX.write_json_atomic


# --------------------------------------------------------------------------
# shard / merge helpers (pure; also exercised by --dry-run)
# --------------------------------------------------------------------------
def load_sents_rows(path):
    b = Path(path).read_bytes()
    d = json.loads(b.decode("utf-8"))
    if d.get("schema") != "m5c2_b7_sents_v1":
        raise SystemExit("unexpected SENTS schema %r" % (d.get("schema"),))
    rows = d.get("sentences") or []
    if not rows:
        raise SystemExit("SENTS holds no sentences")
    return rows, {"path": rel(path), "sha16": sha16(b), "bytes": len(b),
                  "n_sentences": len(rows)}


def load_shard_raw(path):
    p = Path(path)
    if not p.exists():
        raise SystemExit("missing shard1 RAW: %s" % rel(p))
    b = p.read_bytes()
    d = json.loads(b.decode("utf-8"))
    if d.get("schema") != "m5c2_b7_extract_raw_v1":
        raise SystemExit("unexpected RAW schema %r" % (d.get("schema"),))
    recs = d.get("records") or []
    return d, recs, {"path": rel(p), "sha16": sha16(b), "bytes": len(b),
                     "n_records": len(recs),
                     "n_forward": d.get("n_forward"),
                     "aborted": d.get("aborted")}


def completed_sids(recs):
    sids = []
    seen = set()
    for r in recs:
        sid = r.get("sid")
        if sid is None:
            raise SystemExit("shard RAW record without sid")
        if sid in seen:
            raise SystemExit("duplicate sid inside shard RAW: %s" % sid)
        seen.add(sid)
        sids.append(sid)
    return sids


def remaining_rows(rows, done_sids):
    done = set(done_sids)
    unknown = done - {r["sid"] for r in rows}
    if unknown:
        raise SystemExit("shard1 contains sids not in frozen SENTS: %r"
                         % (sorted(unknown)[:5],))
    return [r for r in rows if r["sid"] not in done]


def merge_records(shard1_recs, shard2_recs, rows, expect_n=None):
    """Merge by sid, unique, complete against SENTS, order exactly as SENTS."""
    by_sid = {}
    dups = []
    for src, recs in (("shard1", shard1_recs), ("shard2", shard2_recs)):
        for r in recs:
            sid = r.get("sid")
            if sid is None:
                raise SystemExit("merged record without sid (%s)" % src)
            if sid in by_sid:
                dups.append(sid)
                continue
            by_sid[sid] = r
    want = [r["sid"] for r in rows]
    merged = [by_sid[s] for s in want if s in by_sid]
    missing = [s for s in want if s not in by_sid]
    extra = [s for s in by_sid if s not in set(want)]
    complete = (not dups and not missing and not extra
                and len(merged) == len(want)
                and (expect_n is None or len(merged) == expect_n))
    ordered = [r["sid"] for r in merged] == [s for s in want if s in by_sid]
    return {
        "records": merged,
        "n_records": len(merged),
        "n_expected": len(want),
        "duplicates": dups,
        "missing": missing,
        "extra": extra,
        "ordered_ok": ordered,
        "complete": complete,
    }


def shard2_needed(rows, done_sids, expect_n=EXPECT_N):
    rem = remaining_rows(rows, done_sids)
    return rem, {"n_sents": len(rows), "n_done": len(done_sids),
                 "n_remaining": len(rem),
                 "expect_n": expect_n,
                 "completed_plus_remaining_total": len(done_sids) + len(rem)}


# --------------------------------------------------------------------------
# real mode
# --------------------------------------------------------------------------
def real(args):
    # Pass the explicit expectations into the frozen extract pins checker: the
    # b7 extract pins are dynamic (GEN_SHA16=None by design), so verify_pins()
    # without arguments cannot format them (regression fixed in resume v2).
    pins = EX.verify_pins(args.expect_gen_sha16,
                          args.expect_gen_bytes,
                          args.expect_sents_sha16,
                          args.expect_sents_bytes)
    rows, sents_doc_meta = load_sents_rows(args.sents)
    raw1, recs1, shard1_meta = load_shard_raw(args.raw_shard1)
    if sents_doc_meta["n_sentences"] != EXPECT_N:
        raise SystemExit("SENTS has %d sentences, expected %d"
                         % (sents_doc_meta["n_sentences"], EXPECT_N))
    done = completed_sids(recs1)
    rem, plan = shard2_needed(rows, done, EXPECT_N)

    gate0, exc0 = EX.host_gate(None, None, n_forward=0)   # strict, no opt-in
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_b7_extract_resume_hostgate_refused_v1",
               "status": "未接上", "mode": "resume_shard2",
               "reason": "strict host gate failed before any model load",
               "pins": pins, "gate": gate0, "gate_exceptions": exc0,
               "n_forward": 0, "no_model_loaded": True,
               "shard1": shard1_meta, "plan": plan}
        write_json_atomic(REFUSED, out)
        print(json.dumps({k: out[k] for k in ("status", "reason")},
                         ensure_ascii=False, indent=1))
        return 2

    t0 = time.perf_counter()
    sampler = EX.F.start_sampler()
    eng = None
    recs2 = []
    forwards2 = 0
    attempted2 = 0
    aborted = None
    abort_class = None
    try:
        eng = EX.R2.open_engine()
        eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                          ctypes.c_char_p, ctypes.c_int,
                                          ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int]
        meta = EX.E.meta_from_log(eng, t0)
        for row in rem:
            if time.perf_counter() - t0 > RESUME_LIMIT_S:
                aborted = "timeout >%ds (resume shard2)" % RESUME_LIMIT_S
                abort_class = "timeout_mid"
                break
            try:
                peak = round(float(EX.F.PEAK.read_text().strip())
                             / (1024 ** 3), 4)
            except Exception:  # noqa: BLE001
                peak = None
            if peak is not None and peak > EX.FUSE_GIB:
                aborted = "VRAM fuse: peak %.4f > %.1f GiB" % (peak,
                                                               EX.FUSE_GIB)
                abort_class = "vram_fuse_mid"
                break
            rec = {"sid": row["sid"], "qid": row["qid"],
                   "scenario": row["scenario"], "text": row["text"],
                   "source_text": row["source_text"], "route": None,
                   "layer0": None, "prompt_sha16": None, "raw_out": None,
                   "rc": None, "elapsed_s": None, "parse_ok": None,
                   "parse_reason": None, "items": None, "n_items": 0}
            route, det = EX.layer0_route(row)
            if route:
                rec["route"] = route
                rec["layer0"] = det
                rec["parse_ok"] = True
                rec["items"] = []
                recs2.append(rec)
                write_json_atomic(args.raw_shard2, {
                    "schema": "m5c2_b7_extract_raw_v1",
                    "shard": 2, "n_forward": forwards2,
                    "aborted": aborted, "records": recs2})
                continue
            prompt = EX.build_prompt(row)
            rec["route"] = "model_extract"
            rec["prompt_sha16"] = sha16(prompt.encode("utf-8"))
            eng.reset(0)
            buf = ctypes.create_string_buffer(131072)
            ts = time.perf_counter()
            rc = int(eng.lib.kvshim_ask_at(eng.h, 0, prompt.encode("utf-8"),
                                           0, EX.N_PREDICT, buf, 131072))
            rec["elapsed_s"] = round(time.perf_counter() - ts, 3)
            eng.reset(0)
            attempted2 += 1
            if rc < 0:
                rec["rc"] = rc
                rec["error"] = "kvshim_ask_at returned %d" % rc
                recs2.append(rec)
                aborted = "forward failed: rc=%d at %s" % (rc, row["sid"])
                abort_class = "forward_failed"
                write_json_atomic(args.raw_shard2, {
                    "schema": "m5c2_b7_extract_raw_v1",
                    "shard": 2, "n_forward": forwards2,
                    "n_forward_attempted": attempted2,
                    "aborted": aborted, "records": recs2})
                break
            raw = buf.value.decode("utf-8", "replace")
            forwards2 += 1
            rec["rc"] = rc
            rec["raw_out"] = raw
            try:
                items, parse_ok, reason = EX.R41.parse_extraction(
                    raw, str(row["source_text"]))
            except Exception as e:  # noqa: BLE001
                items, parse_ok, reason = [], False, "parse exception: %r" % (e,)
            rec["parse_ok"] = bool(parse_ok)
            rec["parse_reason"] = reason
            rec["items"] = items
            rec["n_items"] = len(items)
            recs2.append(rec)
            write_json_atomic(args.raw_shard2, {
                "schema": "m5c2_b7_extract_raw_v1",
                "shard": 2, "n_forward": forwards2,
                "n_forward_attempted": attempted2,
                "aborted": aborted, "records": recs2})
        gate1, _exc1 = EX.BG6.host_gate()   # strict post-run record
        peak = EX.F.stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 3)
        raw2 = Path(args.raw_shard2).read_bytes()
        shard2_meta = {"path": rel(args.raw_shard2),
                       "sha16": sha16(raw2), "bytes": len(raw2),
                       "n_records": len(recs2),
                       "n_forward": forwards2,
                       "aborted": aborted}
        m = merge_records(recs1, recs2, rows, EXPECT_N)
        provenance = {
            "rule": "RULING-M5C2-B7-EXTRACT-RESUME: shard2 = SENTS sids not in "
                    "shard1 (by sid set); merge only when prompts/pins/engine "
                    "identical; EXTRACT must be 623/623, unique, ordered by SENTS",
            "shard1": dict(shard1_meta,
                           sids_completed=sorted(done),
                           n_completed=len(done)),
            "shard2": dict(shard2_meta,
                           sids_in_shard2=[r["sid"] for r in recs2],
                           n_in_shard2=len(recs2)),
            "plan": plan,
            "merge": {k: m[k] for k in ("n_records", "n_expected",
                                        "duplicates", "missing", "extra",
                                        "ordered_ok", "complete")},
            "resume_attempt_no": 2,
            "attempt1": {"mode": "frozen extract single pass",
                         "abort_class": (raw1.get("aborted") or None),
                         "n_forward_raw": raw1.get("n_forward")},
        }
        if not m["complete"]:
            fail = {
                "schema": "m5c2_b7_extract_resume_incomplete_v1",
                "status": "未接上",
                "reason": "merged shards are not 623/623 unique+complete",
                "aborted": aborted, "abort_class": abort_class or
                "merge_incomplete",
                "provenance": provenance, "pins": pins,
                "gate_before": gate0, "gate_after": gate1,
                "no_gpu_after_stop": True,
            }
            write_json_atomic(FAILED, fail)
            print(json.dumps({"status": "未接上",
                              "reason": fail["reason"],
                              "missing": m["missing"][:10],
                              "duplicates": m["duplicates"][:10],
                              "shard2": shard2_meta},
                             ensure_ascii=False, indent=1))
            return 3
        out = {
            "schema": "m5c2_b7_extract_v1",
            "status": "已抽取未判定" if aborted is None else "未接上",
            "pins": pins,
            "engine_meta": meta,
            "n_sentences": len(m["records"]),
            "n_forward": int((shard1_meta.get("n_forward") or 0)) + forwards2,
            "n_forward_attempted": int((shard1_meta.get("n_forward") or 0))
                                   + attempted2,
            "layer0_skipped": sum(1 for r in m["records"]
                                  if r.get("layer0") is not None),
            "aborted": aborted,
            "abort_class": abort_class,
            "elapsed": elapsed,
            "elapsed_s": elapsed,
            "peak_gib": peak,
            "target_gib": EX.TARGET_GIB,
            "fuse_gib": EX.FUSE_GIB,
            "n_predict": EX.N_PREDICT,
            "temperature": 0,
            "sampling": "argmax_greedy",
            "seed": None,
            "grammar": None,
            "gate_before": gate0,
            "gate_after": gate1,
            "gate_exceptions": [],
            "gate_exceptions_after": None,
            "gate_exception_samples": [],
            "gate_exception_match_by": "pid+exe_path",
            "gate_exception_recheck": {
                "checked": False, "ok": True,
                "reason": "resume uses the strict gate only (no named exception)"},
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
            "resume_provenance": provenance,
            "records": m["records"],
        }
        write_json_atomic(args.out, out)
        b = Path(args.out).read_bytes()
        print(json.dumps({
            "status": out["status"], "out": rel(args.out),
            "sha16": sha16(b), "bytes": len(b),
            "n_sentences": out["n_sentences"],
            "n_forward": out["n_forward"],
            "n_forward_shard2": forwards2,
            "aborted": aborted, "abort_class": abort_class,
            "shard1": {"sha16": shard1_meta["sha16"],
                       "n_records": shard1_meta["n_records"]},
            "shard2": {"sha16": shard2_meta["sha16"],
                       "n_records": shard2_meta["n_records"]},
            "merge_complete": m["complete"],
        }, ensure_ascii=False, indent=1))
        return 0 if aborted is None else 3
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


# --------------------------------------------------------------------------
# dry-run: synthetic shards exercise merge/dedup/completeness only
# --------------------------------------------------------------------------
def dry_run():
    rows = [{"sid": "syn-%03d" % i, "qid": "syn-q%02d" % (i // 5),
             "scenario": "syn-s%d" % (i // 25), "text": "第%d句。" % i,
             "source_text": "源文%d。" % i} for i in range(25)]
    rec = lambda sid: {"sid": sid, "route": "model_extract", "rc": 0,
                       "parse_ok": True, "items": [], "n_items": 0,
                       "raw_out": "条目：x\n依据：x"}
    shard1 = [rec(r["sid"]) for r in rows[:20]]
    shard2_full = [rec(r["sid"]) for r in rows[20:]]
    cases = []
    m = merge_records(shard1, shard2_full, rows, 25)
    cases.append(("merge_complete_25", m["complete"] and not m["missing"]
                  and not m["duplicates"]))
    cases.append(("merge_ordered", m["ordered_ok"]))
    m_dup = merge_records(shard1, shard2_full + [rec(rows[0]["sid"])], rows, 25)
    cases.append(("duplicate_detected", not m_dup["complete"]
                  and m_dup["duplicates"] == [rows[0]["sid"]]))
    m_miss = merge_records(shard1, shard2_full[:-1], rows, 25)
    cases.append(("missing_detected", not m_miss["complete"]
                  and m_miss["missing"] == [rows[-1]["sid"]]))
    m_extra = merge_records(shard1, shard2_full + [rec("extra-999")], rows, 25)
    cases.append(("extra_detected", not m_extra["complete"]
                  and m_extra["extra"] == ["extra-999"]))
    rem, plan = shard2_needed(rows, [r["sid"] for r in shard1], 25)
    cases.append(("remaining_by_sid_set",
                  [r["sid"] for r in rem] == [r["sid"] for r in rows[20:]]
                  and plan["completed_plus_remaining_total"] == 25))
    cases.append(("real_expect_n_623", EXPECT_N == 623))
    ok = all(c[1] for c in cases)
    print(json.dumps({
        "schema": "m5c2_b7_extract_resume_dry_run_v1",
        "status": "dry_run_only",
        "n_forward": 0, "no_gpu": True, "writes_any_file": False,
        "cases": [{"case": c[0], "pass": c[1]} for c in cases],
        "all_pass": ok,
        "note": "synthetic 25-sentence SENTS + 20-record shard1; no engine, no "
                "GPU, no real artifact touched",
    }, ensure_ascii=False, indent=1))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-shard1", default=str(DEFAULT_RAW1))
    ap.add_argument("--raw-shard2", default=str(DEFAULT_RAW2))
    ap.add_argument("--sents", default=str(DEFAULT_SENTS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--expect-gen-sha16", default=None)
    ap.add_argument("--expect-gen-bytes", default=None)
    ap.add_argument("--expect-sents-sha16", default=None)
    ap.add_argument("--expect-sents-bytes", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        return dry_run()
    return real(a)


if __name__ == "__main__":
    sys.exit(main())