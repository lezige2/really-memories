#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-B2 out-of-sample runner, **do not run before PREREG-M5-B**.

Why this file exists
--------------------
`run_m5_c_v2.py` and `run_m5c_judge.py` are the frozen (c) batch runners.  Neither
accepts an external scenario/question JSON: both hardcode the three m2 facets,
the (c) question list, the (c) prereg/raw paths, and the v2.1 judge.  This file is
the smallest separate entry point for (b): it reads the fixture produced from
PREREG-M5-B and keeps the same safety envelope as (c):

  * host gate before/after (boot id, free RAM >= 8,388,608 kB, baseline VRAM
    <= 1.5 GiB, no >256 MiB GPU process, dump count unchanged);
  * 100 ms VRAM sampler, target <= 8.0 GiB, 8.6 GiB fuse;
  * parent never signals a child; only the stop flag is written;
  * one save -> fresh-process load probe per run, S8 style;
  * zero GPU, zero model call unless `--run` is explicit.

The build of a (b) scenario is a single text block written at
`CHAT_START - n_tokens .. CHAT_START-1`, then questions asked at 4096 onward with
no reset between the two questions of a scenario (PREREG-M5-B §2).  This is the
text-block analogue of `run_m5_c_v2.build_layout`; it is NOT a precomputed m2
.kvmem load.  If PREREG-M5-B specifies another build, stop and adjust this file
before running; do not silently mix modes.

Usage:
    python -X utf8 run_m5_b_v2.py                 # dry run: validate fixture only
    python -X utf8 run_m5_b_v2.py --run \
        --prereg-sha16 <sha16> --prereg-bytes <bytes>   # actual GPU run, later
"""
import argparse
import ctypes
import re
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from collections import Counter

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
sys.path.insert(0, str(M5))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/engine"))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/m7/out"))
sys.path.insert(0, str(ROOT / "tools"))

import _e3gpu_run as E                                      # noqa: E402
import _driver2 as D2                                       # noqa: E402
import m2_visibility_probe as P                             # noqa: E402
import m5_ground_v2_3 as J                                 # noqa: E402
from validate_m5b2_fixture import validate_fixture           # noqa: E402

PREREG = ROOT / "docs/_work/PREREG-M5-B2.md"
FIXTURE = OUT / "M5B2-fixture.json"
ART = OUT / "M5B2-GEN.json"
SAVE = OUT / "M5B2-probe.kvmem"
STOP = OUT / "_m5b2_stop.flag"
TMP = OUT / "tmp_m5b2"
CHAT_START = 4096
N_PREDICT = 192
TARGET_GIB = 8.0
GATE_GIB = 8.6
SCENARIO_TIMEOUT = 900
JUDGE_EXPECT_SHA16 = "cc03e48c360ae0ee"
JUDGE_EXPECT_BYTES = 44209


def sha16_bytes(b):
    return hashlib.sha256(b).hexdigest()[:16]


def info(path):
    b = Path(path).read_bytes()
    return {"path": str(path), "sha16": sha16_bytes(b), "bytes": len(b)}


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def gate_check(prereg_required=False):
    """Revised (b) host gate.  Browser/Code count is recorded, not used as a gate."""
    g = E.gate_values()
    g["free_ram_ok"] = (g.get("free_ram_kb") or 0) >= 8388608
    g["vram_baseline_ok"] = (g.get("vram_baseline_gib") is not None
                             and g["vram_baseline_gib"] <= 1.5)
    g["gpu_procs_ok"] = g.get("gpu_procs_gt256mb") == 0
    g["boot_id_ok"] = bool(g.get("boot_id"))
    g["prereg_exists"] = PREREG.exists()
    if g["prereg_exists"]:
        g["prereg_sha16"] = sha16_bytes(PREREG.read_bytes())
        g["prereg_bytes"] = PREREG.stat().st_size
    else:
        g["prereg_sha16"] = None
        g["prereg_bytes"] = None
    g["prereg_ok"] = (not prereg_required) or bool(g["prereg_exists"])
    g["judge_path"] = str(J.JUDGE_PATH) if hasattr(J, "JUDGE_PATH") else str(M5 / "m5_ground_v2_3.py")
    g["judge_sha16"] = sha16_bytes(Path(g["judge_path"]).read_bytes())
    g["judge_bytes"] = Path(g["judge_path"]).stat().st_size
    g["judge_ok"] = (g["judge_sha16"] == JUDGE_EXPECT_SHA16
                     and g["judge_bytes"] == JUDGE_EXPECT_BYTES)
    g["dll_sha16"] = sha16_bytes(Path(E.VK).read_bytes())
    g["dll_bytes"] = Path(E.VK).stat().st_size
    g["dll_ok"] = g["dll_sha16"] == E.VK_SHA16 and g["dll_bytes"] == E.VK_BYTES
    g["model_bytes"] = Path(E.MODEL).stat().st_size
    g["model_ok"] = g["model_bytes"] == E.MODEL_BYTES
    g["gate_ok"] = all(g[k] for k in ("prereg_ok", "judge_ok", "dll_ok", "model_ok",
                                      "free_ram_ok", "vram_baseline_ok",
                                      "gpu_procs_ok", "boot_id_ok"))
    return g


def start_sampler(tag):
    """Same 100 ms sampler contract as (c): parent only writes the stop flag."""
    flag = OUT / ("_m5b2_stop_%s.flag" % tag)
    peak = OUT / ("_m5b2_peak_%s.txt" % tag)
    for x in (flag, peak):
        try:
            x.unlink()
        except FileNotFoundError:
            pass
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(E.SAMPLER),
           "-Flag", str(flag), "-Out", str(peak)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         encoding="utf-8", errors="replace")
    time.sleep(0.2)
    return {"proc": p, "flag": flag, "peak": peak}


def stop_sampler(s):
    try:
        s["flag"].write_text("done", encoding="utf-8")
    except OSError:
        pass
    try:
        s["proc"].communicate(timeout=15)
    except subprocess.TimeoutExpired:
        pass
    try:
        return round(float(s["peak"].read_text().strip()) / (1024 ** 3), 4)
    except Exception:  # noqa: BLE001
        return None


def open_engine():
    t0 = time.perf_counter()
    eng = E.open_engine()
    # Same native ask binding as run_m5_c_v2.open_scenario_engine().
    eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p,
                                      ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    eng.lib.kvshim_ask_at.restype = ctypes.c_int
    P.bind_raw(eng)
    meta = E.meta_from_log(eng, t0)
    meta["pid"] = os.getpid()
    return eng, meta


def build_text_block(eng, source_text):
    """Build one source block ending at CHAT_START-1, with a measured token count."""
    eng.reset(P.LIVE)
    n0 = int(eng.write_at(P.LIVE, source_text, 0, True))
    n_tok = int(eng.n_tokens(P.LIVE))
    pm0 = int(eng.pos_max(P.LIVE))
    if n0 < 1 or n_tok < 1 or pm0 != n_tok - 1:
        raise RuntimeError("source tokenization failed: n0=%s n_tokens=%s pos_max=%s" %
                           (n0, n_tok, pm0))
    lo = CHAT_START - n_tok
    if lo < 0:
        raise RuntimeError("source too long for CHAT_START: %d tokens" % n_tok)
    eng.reset(P.LIVE)
    n1 = int(eng.write_at(P.LIVE, source_text, lo, True))
    nt = int(eng.n_tokens(P.LIVE))
    pm = int(eng.pos_max(P.LIVE))
    if n1 != n_tok or nt != n_tok or pm != CHAT_START - 1:
        raise RuntimeError("source placement mismatch: write=%s n_tokens=%s pos_max=%s" %
                           (n1, nt, pm))
    return {"source_tokens": n_tok, "pos_lo": lo, "pos_hi": CHAT_START,
            "n_tokens": nt, "raw_pos_max": pm, "ok": True}


def ask_one(eng, question, pos, n_predict=192):
    before_n = int(eng.n_tokens(P.LIVE))
    before_p = int(eng.pos_max(P.LIVE))
    t0 = time.perf_counter()
    rc, ans = D2.ask_native(eng, P.LIVE, question, pos, n_predict)
    elapsed = round(time.perf_counter() - t0, 3)
    after_n = int(eng.n_tokens(P.LIVE))
    after_p = int(eng.pos_max(P.LIVE))
    return {"question": question, "answer": ans,
            "answer_sha16": sha16_bytes(ans.encode("utf-8")),
            "answer_chars": len(ans), "rc": rc, "pos_asked": pos,
            "n_predict": n_predict, "elapsed_s": elapsed,
            "n_tokens_before": before_n, "n_tokens_after": after_n,
            "pos_before": before_p, "pos_after": after_p}


TAG_OPEN = chr(60) + "think" + chr(62)
TAG_CLOSE = chr(60) + "/think" + chr(62)
TAG_RE = re.compile(r"^</?think\s*>$")
_SENT_RE = re.compile(r"[\u3400-\u9fffA-Za-z0-9]")


def is_counted_segment(raw):
    """PREREG-M5-B2 §2 sentence: non-empty after strip; pure tag/symbol lines excluded.

    A line is counted iff, after removing a whole  tag pair, it still contains
    at least one CJK character, Latin letter or digit.  This is the same rule used
    for the >=150 gate and for filtering the judge's sentence list.
    """
    s = str(raw or "").strip()
    if not s:
        return False
    if TAG_RE.match(s):
        return False
    if s.startswith(TAG_OPEN) and s.endswith(TAG_CLOSE):
        s = s[7:-8].strip()
    if not s:
        return False
    return bool(_SENT_RE.search(s))


def judge_answer(answer, source_text, question):
    """One v2.3 ground call over the whole answer; filter to the non-empty sentence set."""
    rep = J.analyze_answer(answer, [source_text], question)
    segs = rep.get("sentences", [])
    kept = [s for s in segs if is_counted_segment(s.get("raw", ""))]
    dropped = [s for s in segs if not is_counted_segment(s.get("raw", ""))]
    counts = Counter(s.get("verdict") for s in kept)
    empty_no_fact = [s for s in dropped if s.get("verdict") == "no_fact"]
    return {
        "verdict": rep.get("verdict"), "branch": rep.get("branch"), "reason": rep.get("reason"),
        "sentence_counts": dict(counts),
        "n_sentences": len(kept),
        "raw_sentence_count": len(segs),
        "empty_segment_count": len(dropped),
        "judge_counts_empty_as_no_fact": bool(empty_no_fact),
        "empty_no_fact_count": len(empty_no_fact),
        "partial_hit_sentences": [x for x in rep.get("partial_hit_sentences", [])
                                  if is_counted_segment(x.get("text", ""))],
        "polarity_conflicts": rep.get("polarity_conflicts", []),
        "extraction_fp": rep.get("extraction_fp", []),
        "sentence_verdicts": [s.get("verdict") for s in kept],
        "judge_version": rep.get("judge_version"),
    }


def run_probe_child(save_path, fixture_path):
    """Fresh OS process: load saved KV, then ask the last fixture question."""
    OUT.mkdir(parents=True, exist_ok=True)
    child_out = OUT / "_m5b2_probe_child.json"
    if child_out.exists():
        child_out.unlink()
    cmd = [sys.executable, "-X", "utf8", str(Path(__file__).resolve()),
           "--probe-child", "--save", str(save_path), "--fixture", str(fixture_path),
           "--child-out", str(child_out)]
    p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    try:
        so, se = p.communicate(timeout=SCENARIO_TIMEOUT)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        STOP.write_text("probe_timeout", encoding="utf-8")
        so, se, rc = "", "timeout", None
    if child_out.exists():
        try:
            data = json.load(open(child_out, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {"status": "未接上（child output parse）", "error": "parse"}
    else:
        data = {"status": "未接上（child 无输出）", "error": (se or "")[-1000:]}
    data["_child_exit"] = rc
    data["_child_stdout_tail"] = (so or "")[-1000:]
    data["_child_stderr_tail"] = (se or "")[-1000:]
    return data


def probe_child_main(save_path, fixture_path, child_out):
    fixture = json.load(open(fixture_path, encoding="utf-8"))
    scenario = fixture["scenarios"][-1]
    q = scenario["questions"][-1]["text"]
    eng, meta = open_engine()
    out = {"mode": "probe_load", "device": meta, "question": q,
           "source_id": scenario["id"], "status": "started", "error": None}
    try:
        n0 = int(eng.n_tokens(P.LIVE))
        p0 = int(eng.pos_max(P.LIVE))
        lr = int(eng.load_strict(P.LIVE, str(save_path)))
        n1 = int(eng.n_tokens(P.LIVE))
        p1 = int(eng.pos_max(P.LIVE))
        out.update({"n_tokens_before_load": n0, "pos_before_load": p0,
                    "load_return": lr, "n_tokens_after_load": n1, "pos_after_load": p1})
        pos = p1 + 1
        rec = ask_one(eng, q, pos, N_PREDICT)
        out.update({"answer": rec["answer"], "answer_sha16": rec["answer_sha16"],
                    "ask_rc": rec["rc"], "pos_asked": pos,
                    "n_tokens_after_ask": rec["n_tokens_after"],
                    "pos_after_ask": rec["pos_after"], "status": "completed"})
    except Exception as e:  # noqa: BLE001
        out["status"] = "未接上（load/ask 失败）"
        out["error"] = type(e).__name__ + ": " + str(e)
    finally:
        try:
            eng.close()
        except Exception:  # noqa: BLE001
            pass
    write_json_atomic(child_out, out)
    print("M5BCHILD " + json.dumps(out, ensure_ascii=False))
    return 0


def dry_run(fixture_path):
    rep = validate_fixture(fixture_path, allow_placeholder=True)
    gate = gate_check(prereg_required=False)
    host = E.host_check("before_m5b_dryrun")
    plan = []
    if rep["ok"]:
        fx = json.load(open(fixture_path, encoding="utf-8"))
        for s in fx["scenarios"]:
            plan.append({"id": s["id"], "source_chars": len(s.get("source_text") or ""),
                         "facts": len(s.get("facts") or []),
                         "questions": [{"qid": q.get("qid"), "kind": q.get("kind"),
                                        "expected": q.get("expected")}
                                       for q in s["questions"]]})
    out = {"schema": "m5_b_dryrun_v1", "run": False, "fixture": info(fixture_path),
           "validate": rep, "gate": gate,
           "host": {"boot_id": host["parsed"]["boot_id"],
                    "dump_count": host["parsed"]["existing_count"],
                    "latest_mtime": host["parsed"]["latest_mtime"]},
           "plan": plan,
           "note": "dry run only: no model was loaded and no engine was opened"}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if rep["ok"] else 1


def run(fixture_path, prereg_sha16, prereg_bytes, expected_boot_id, out_path):
    rep = validate_fixture(fixture_path, allow_placeholder=False)
    if not rep["ok"]:
        print(json.dumps({"ok": False, "error": "fixture strict validation failed", "validate": rep},
                         ensure_ascii=False, indent=2))
        return 1
    if not PREREG.exists():
        print(json.dumps({"ok": False, "error": "PREREG-M5-B2.md missing; refusing to run"},
                         ensure_ascii=False, indent=2))
        return 1
    pre_b = PREREG.read_bytes()
    if sha16_bytes(pre_b) != prereg_sha16 or len(pre_b) != prereg_bytes:
        print(json.dumps({"ok": False, "error": "prereg coordinate mismatch",
                          "actual": {"sha16": sha16_bytes(pre_b), "bytes": len(pre_b)},
                          "expected": {"sha16": prereg_sha16, "bytes": prereg_bytes}},
                         ensure_ascii=False, indent=2))
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    try:
        STOP.unlink()
    except FileNotFoundError:
        pass
    gate_before = gate_check(prereg_required=True)
    host_before = E.host_check("before_m5b")
    if expected_boot_id and host_before["parsed"]["boot_id"] != expected_boot_id:
        gate_before["gate_ok"] = False
        gate_before["expected_boot_id"] = expected_boot_id
        gate_before["boot_id_mismatch"] = True
    art = {
        "schema": "m5_b_run_v1", "task": "M5-B out-of-sample acceptance generation",
        "role": "CAND", "at": now(), "executed": True,
        "prereg": {"path": str(PREREG), "sha16": sha16_bytes(pre_b), "bytes": len(pre_b)},
        "fixture": info(fixture_path),
        "judge": {"path": str(M5 / "m5_ground_v2_3.py"), "sha16": gate_before["judge_sha16"],
                  "bytes": gate_before["judge_bytes"], "version": "v2.3"},
        "gate_before": gate_before, "host_before": host_before,
        "device": {"model": E.MODEL, "model_bytes": E.MODEL_BYTES,
                   "dll": E.VK, "dll_sha16": E.VK_SHA16, "dll_bytes": E.VK_BYTES,
                   "n_gpu_layers_input": 36, "n_ctx": E.NCTX, "n_seq": E.NSEQ, "kv": E.KV,
                   "chat_start": CHAT_START, "vram_gate_gib": GATE_GIB, "target_gib": TARGET_GIB,
                   "engines": []},
        "prompt_template": {"turn": "\\n问：" + "{q}" + "\\n答：",
                            "source": "tools/kvslots.py turn()"},
        "gen_params": {"n_predict": N_PREDICT, "sampling": "argmax_greedy",
                       "temperature": 0, "seed_known": True, "reset_between_questions": False,
                       "source_mode": "single_text_block_at_CHAT_START"},
        "build": [], "scenarios": [], "peaks": [], "gate_after": None, "host_after": None,
        "save_probe": None, "known_fp_controls": [],
        "attempts": [{"n": 1, "at": now(), "status": "started",
                      "reason": "PREREG-M5-B; CAND only; no retry; parent no signal"}],
        "limitations": [], "signals_sent_by_parent": False,
        "no_single_accuracy": True, "no_final_verdict": True,
        "git_operations": 0,
    }
    write_json_atomic(out_path, art)
    if not gate_before["gate_ok"]:
        art["attempts"][0]["status"] = "gate_failed"
        art["attempts"][0]["finished_at"] = now()
        art["status"] = "未接上（装置不合格：开工硬闸）"
        art["four_state"] = "未接上"
        art["limitations"].append("开跑前 host gate 未过，未开引擎")
        write_json_atomic(out_path, art)
        print(json.dumps({"ok": False, "status": art["status"], "gate": gate_before},
                         ensure_ascii=False, indent=2))
        return 1

    fx = json.load(open(fixture_path, encoding="utf-8"))
    aborted = False
    errors = []
    over_target = []
    for si, s in enumerate(fx["scenarios"]):
        if aborted or STOP.exists():
            break
        sid = s["id"]
        sampler = start_sampler(sid)
        t0 = time.perf_counter()
        eng = None
        try:
            eng, meta = open_engine()
            art["device"]["engines"].append(meta)
            if not meta.get("vulkan_imported") or meta.get("n_gpu_layers_readback") != 36:
                errors.append("device proof failed: " + sid)
                aborted = True
                continue
            build = build_text_block(eng, s["source_text"])
            art["build"].append({"scenario": sid, "source_sha16": sha16_bytes(s["source_text"].encode("utf-8")),
                                 "source_chars": len(s["source_text"]), **build})
            scenario_rec = {"id": sid, "source_text": s["source_text"],
                            "source_sha16": sha16_bytes(s["source_text"].encode("utf-8")),
                            "facts": s["facts"], "build": build, "questions": [],
                            "peak_gib": None}
            first_q = True
            for q in s["questions"]:
                if STOP.exists():
                    aborted = True
                    break
                pos = CHAT_START if first_q else int(eng.pos_max(P.LIVE)) + 1
                first_q = False
                rec = ask_one(eng, q["text"], pos, N_PREDICT)
                rec.update({"qid": q["qid"], "kind": q["kind"], "expected": q["expected"],
                            "judge": judge_answer(rec["answer"], s["source_text"], q["text"])})
                scenario_rec["questions"].append(rec)
                print("M5B_PROGRESS %s %s chars=%d elapsed=%.1f" %
                      (sid, q["qid"], len(rec["answer"]), time.perf_counter() - t0), flush=True)
            if si == len(fx["scenarios"]) - 1 and not aborted and scenario_rec["questions"]:
                ns = int(eng.save(P.LIVE, str(SAVE)))
                saved = {"save_return": ns, "save_sha16": sha16_bytes(SAVE.read_bytes()),
                         "save_bytes": SAVE.stat().st_size,
                         "pos_saved": int(eng.pos_max(P.LIVE)),
                         "n_tokens_saved": int(eng.n_tokens(P.LIVE)),
                         "scenario": sid}
                scenario_rec["save"] = saved
                art["save_probe"] = {"parent": saved}
            scenario_rec["elapsed_s"] = round(time.perf_counter() - t0, 3)
            art["scenarios"].append(scenario_rec)
        except Exception as e:  # noqa: BLE001
            errors.append("%s: %s: %s" % (sid, type(e).__name__, e))
            aborted = True
        finally:
            if eng is not None:
                try:
                    eng.close()
                except Exception:  # noqa: BLE001
                    pass
            elapsed = time.perf_counter() - t0
            peak = stop_sampler(sampler)
            if art["scenarios"] and art["scenarios"][-1]["id"] == sid:
                art["scenarios"][-1]["peak_gib"] = peak
                art["scenarios"][-1]["elapsed_s"] = round(elapsed, 3)
            if peak is not None:
                art["peaks"].append({"scenario": sid, "peak_gib": peak})
                if peak > TARGET_GIB:
                    over_target.append({"scenario": sid, "peak_gib": peak})
                if peak > GATE_GIB:
                    errors.append("VRAM %.4f > %.1f: %s" % (peak, GATE_GIB, sid))
                    STOP.write_text("vram_abort", encoding="utf-8")
                    aborted = True
            if elapsed > SCENARIO_TIMEOUT:
                errors.append("scenario timeout: " + sid)
                STOP.write_text("timeout", encoding="utf-8")
                aborted = True

    if not aborted and art["save_probe"] and SAVE.exists():
        sampler = start_sampler("probe_load")
        try:
            child = run_probe_child(SAVE, fixture_path)
        finally:
            peak = stop_sampler(sampler)
        art["save_probe"]["child"] = child
        art["save_probe"]["peak_gib"] = peak
        parent = art["save_probe"]["parent"]
        child_ok = child.get("status") == "completed"
        pos_ok = (parent.get("pos_saved") == child.get("pos_after_load")
                  and parent.get("n_tokens_saved") == child.get("n_tokens_after_load"))
        art["save_probe"].update({"pos_ok": pos_ok, "child_ok": child_ok,
                                  "selfproof_ok": bool(child_ok and pos_ok),
                                  "load_return": child.get("load_return")})
        if not (child_ok and pos_ok):
            errors.append("save/load probe self-proof mismatch")

    sentences_nonempty = sum(q.get("judge", {}).get("n_sentences", 0)
                             for sc in art["scenarios"] for q in sc.get("questions", []))
    art["sentences_nonempty"] = sentences_nonempty
    art["sample_size_threshold"] = 150
    art["sample_size_gate"] = sentences_nonempty >= 150
    art["judge_counts_empty_as_no_fact"] = any(
        q.get("judge", {}).get("judge_counts_empty_as_no_fact", False)
        for sc in art["scenarios"] for q in sc.get("questions", []))
    art["raw_sentence_count"] = sum(q.get("judge", {}).get("raw_sentence_count", 0)
                                    for sc in art["scenarios"] for q in sc.get("questions", []))
    art["empty_segment_count"] = sum(q.get("judge", {}).get("empty_segment_count", 0)
                                     for sc in art["scenarios"] for q in sc.get("questions", []))
    art["gate_after"] = gate_check(prereg_required=True)
    art["host_after"] = E.host_check("after_m5b")
    art["reboot"] = E.derive_host_state(host_before, art["host_after"])
    art["dumps_unchanged"] = (not art["reboot"].get("minidump_new")
                              and art["reboot"].get("minidump_before_count") ==
                              art["reboot"].get("minidump_existing_count"))
    if not art["dumps_unchanged"]:
        errors.append("minidump count/content changed")
    if not art["gate_after"].get("gate_ok"):
        errors.append("post-run host gate is not clean")
    art["voided_by_reboot"] = bool(art["reboot"].get("boot_changed"))
    art["over_target"] = over_target
    art["known_fp_controls"] = J.known_fp_controls()
    art["attempts"][0]["finished_at"] = now()
    art["attempts"][0]["status"] = "aborted" if (aborted or errors) else "completed"
    art["attempts"][0]["reason"] = "; ".join(errors)[:1500] if errors else "all 8 scenarios attempted"
    if art["voided_by_reboot"]:
        art["status"] = "判据作废（蓝屏/重启）"
        art["four_state"] = "判据作废"
    elif errors or aborted:
        art["status"] = "未接上（装置/自证失败）"
        art["four_state"] = "未接上"
    elif not art["sample_size_gate"]:
        art["status"] = "未接上（样本量不足）"
        art["four_state"] = "未接上"
    else:
        art["status"] = "CAND 已落盘；ADJ/JUDGE 待盲标"
        art["four_state"] = "未接上"
    art["limitations"].append("CAND 侧只产原始输出；ADJ/REVIEW 盲标与两率未做，不写通过/未通过。")
    art["limitations"].append("browser_or_code_procs 仅记录、不作 gate；vram_baseline 见 gate_before。")
    write_json_atomic(out_path, art)
    print(json.dumps({"ok": not (errors or aborted), "out": info(out_path),
                      "status": art["status"], "four_state": art["four_state"],
                      "scenarios": len(art["scenarios"]),
                      "peaks": art["peaks"],
                      "gate_ok": art["gate_before"]["gate_ok"],
                      "sentences_nonempty": art.get("sentences_nonempty"),
                      "sample_size_gate": art.get("sample_size_gate"),
                      "save_probe": art["save_probe"],
                      "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not (errors or aborted) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", default=str(FIXTURE))
    ap.add_argument("--out", default=str(ART))
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--probe-child", action="store_true")
    ap.add_argument("--save", default=str(SAVE))
    ap.add_argument("--child-out", default="")
    ap.add_argument("--prereg-sha16", default="")
    ap.add_argument("--prereg-bytes", type=int, default=0)
    ap.add_argument("--expected-boot-id", default="")
    a = ap.parse_args()
    if a.probe_child:
        return probe_child_main(Path(a.save), a.fixture, Path(a.child_out))
    if not a.run:
        return dry_run(a.fixture)
    if not a.prereg_sha16 or a.prereg_bytes <= 0:
        print(json.dumps({"ok": False,
                          "error": "--run requires --prereg-sha16 and --prereg-bytes; "
                                   "no frozen PREREG-M5-B, refusing to open an engine"},
                         ensure_ascii=False, indent=2))
        return 2
    return run(a.fixture, a.prereg_sha16, a.prereg_bytes, a.expected_boot_id, a.out)


if __name__ == "__main__":
    sys.exit(main())