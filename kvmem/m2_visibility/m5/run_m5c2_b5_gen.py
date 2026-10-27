#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B5 generation runner — (b5) one-shot, 40 questions, zero retry.

Protocol source (read-only, frozen, never modified by this script):
    docs/_work/PREREG-M5-C2-B5.md   sha16=d6c7bdac73ef7326 / 14,597 B
    frozen=true / one_shot=true / 8 scenarios x 5 questions = 40 questions
    §3: per-question independent forward, n_predict=192, greedy,
        temperature=0, NO grammar; 14B Q4_K_M, 36 layers, n_ctx=8192,
        N_SEQ=8, kv=q8_0, CHAT_START=4096, dll=kvshim_vk 9edbafa150700614.
    §3 also says the raw answer is stored WHOLE (no sentence split here); the
    frozen split step is `run_m5c2_b5_judge.py --split`.

Modes (exactly one):
    --dry-run     Static validation only. Verifies the frozen prereg pin,
                  parses §1 (8 scenes x 5 questions), checks input paths and
                  sizes, and prints the plan.  NEVER imports the engine, NEVER
                  loads the model, NEVER touches the GPU, NEVER writes a file.
    --gate-check  Host-gate pre-flight only (no model load).  On refusal it
                  writes out/M5C2-B5-HOSTGATE-REFUSED.json and exits 2.
    --run         The one-shot generation (gate -> 40 forwards).  Refuses to
                  overwrite an already consumed one-shot artifact.

Host gate (checked before any model load, §3 "host gate"):
    boot_id present; free RAM >= 8388608 KB (8 GiB);
    VRAM baseline <= 1.5 GiB; no GPU process > 256 MiB except a LONE dwm.exe
    (the Lead-authorized compositor exception, same rule as
    run_m5c2_rev2_order.gate_with_dwm_exception); prereg/dll/model pins.
    Refusal => out/M5C2-B5-HOSTGATE-REFUSED.json + exit 2.  No retry.

VRAM: target <= 8.0 GiB, hard fuse 8.6 GiB (sampler peak > fuse => stop).

Abort semantics (proposal; full text in docs/_work/B5-RUN-PLAN.md §5):
    * device-level failure with NO output (gate refused, engine load failed,
      no forward ever attempted) => one_shot_consumed=false, rerun allowed
      after a fresh gate + trace;
    * any non-empty answer / any completed forward => one_shot_consumed=true,
      rerun forbidden, the run is recorded as 未接上 with the data it produced;
    * OOM / driver crash / power loss => classified by whether output was
      already flushed (this script writes incrementally); if no output exists
      the artifact still carries a conservative warning for the LEAD.

Deterministic artifact: no timestamps, indent=1, ensure_ascii=False, one
trailing newline, atomic replace.  Zero network.  No parent signals.
"""
import argparse
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

PRE = ROOT / "docs/_work/PREREG-M5-C2-B5.md"
PRE_SHA16 = "d6c7bdac73ef7326"
PRE_BYTES = 14597

ART = OUT / "M5C2-B5-GEN.json"
RAW = OUT / "_m5b5_gen_raw.json"          # incremental scratch (crash evidence)
REFUSED = OUT / "M5C2-B5-HOSTGATE-REFUSED.json"

CHAT_START = 4096
N_PREDICT = 192
SCENARIO_TIMEOUT = 900        # §3 single scenario <= 900 s
TOTAL_TIMEOUT = 7200          # 8 scenarios x 900 s
TARGET_GIB = 8.0
FUSE_GIB = 8.6
N_SCENARIOS = 8
N_QUESTIONS = 40

FROZEN_DLL_SHA = "9edbafa150700614"
# Cross-pins (verified by the judge side, recorded here for one artifact):
FROZEN_EXTRACTION_PROMPT_SHA = "a6bc4f268f7711de"
FROZEN_JUDGE_PRE_SHA = "09d6f1b163ea0b84"      # PREREG-M5-C2-REV7.1.md

TURN_TEMPLATE = "\n问：{question}\n答："
KIND_ORDER = ["detail", "detail", "detail", "lure", "lure"]

SCEN_RE = re.compile(r"^###\s+(b5-s\d+)\s+(.*)$")
SRC_RE = re.compile(r"^-\s*源文（[^）]*）：「(.*)」\s*$")
Q_RE = re.compile(r"^-\s*(b5-s\d+-q\d+)\s*\[(detail|lure)\]：「(.*)」\s*$")
SEC2_RE = re.compile(r"^##\s+\S")


def rel(p):
    try:
        return str(Path(p).relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def sha16_file(path, chunk=8 * 1024 * 1024):
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
            n += len(b)
    return h.hexdigest()[:16], n


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# frozen input parsing
# --------------------------------------------------------------------------
def parse_b5():
    """Parse §1 of the frozen prereg: 8 scenes x 5 questions (3 detail + 2 lure)."""
    text = PRE.read_text(encoding="utf-8")
    scenes = []
    cur = None
    in_s1 = False
    for ln in text.splitlines():
        if SCEN_RE.match(ln):
            in_s1 = True
            m = SCEN_RE.match(ln)
            cur = {"sid": m.group(1), "domain": m.group(2).strip(),
                   "source_text": None, "questions": []}
            scenes.append(cur)
            continue
        if SEC2_RE.match(ln):          # "## 2 ..." closes §1
            in_s1 = False
            cur = None
            continue
        if not in_s1 or cur is None:
            continue
        m = SRC_RE.match(ln)
        if m:
            if cur["source_text"] is not None:
                raise SystemExit("duplicate source in %s" % cur["sid"])
            cur["source_text"] = m.group(1).strip()
            continue
        m = Q_RE.match(ln)
        if m:
            cur["questions"].append({"qid": m.group(1), "kind": m.group(2),
                                     "question": m.group(3).strip()})
    if len(scenes) != N_SCENARIOS:
        raise SystemExit("expected %d scenes, got %d" % (N_SCENARIOS, len(scenes)))
    for s in scenes:
        if not s["source_text"]:
            raise SystemExit("missing source in %s" % s["sid"])
        if not s["domain"]:
            raise SystemExit("missing domain in %s" % s["sid"])
        if not (40 <= len(s["source_text"]) <= 90):
            raise SystemExit("%s source length %d outside 40..90" %
                             (s["sid"], len(s["source_text"])))
        if len(s["questions"]) != 5:
            raise SystemExit("%s has %d questions" % (s["sid"], len(s["questions"])))
        kinds = [q["kind"] for q in s["questions"]]
        if kinds != KIND_ORDER:
            raise SystemExit("%s kinds %r != %r" % (s["sid"], kinds, KIND_ORDER))
        want = ["%s-q%d" % (s["sid"], i) for i in range(1, 6)]
        got = [q["qid"] for q in s["questions"]]
        if got != want:
            raise SystemExit("%s qids %r != %r" % (s["sid"], got, want))
    qids = [q["qid"] for s in scenes for q in s["questions"]]
    if len(qids) != N_QUESTIONS or len(set(qids)) != N_QUESTIONS:
        raise SystemExit("expected %d unique qids, got %d/%d" %
                         (N_QUESTIONS, len(qids), len(set(qids))))
    return scenes


def verify_prereg():
    b = PRE.read_bytes()
    text = b.decode("utf-8")
    if sha16(b) != PRE_SHA16 or len(b) != PRE_BYTES:
        raise SystemExit("B5 prereg changed: %s / %d B" % (sha16(b), len(b)))
    if "frozen=true" not in text:
        raise SystemExit("B5 prereg is not frozen")
    if "frozen=false" in text:
        raise SystemExit("B5 prereg still declares frozen=false")
    if "one_shot=true" not in text:
        raise SystemExit("B5 prereg does not declare one_shot=true")
    return {"path": rel(PRE),
            "file": PRE.name, "sha16": PRE_SHA16, "bytes": len(b),
            "lines": len(text.splitlines()), "frozen": True, "one_shot": True}


def turn_prompt(question):
    # Verbatim kvslots.KVEngine.turn: ASK_PREFIX + question + ASK_SUFFIX.
    return TURN_TEMPLATE.format(question=question)


def prompt_text(source, question):
    # Provenance hash over the exact memory text + exact turn (same convention
    # as run_m5c2_b4_gen.py).  The runtime layout keeps the source in KV memory
    # and asks the turn at CHAT_START.
    return source + turn_prompt(question)


# --------------------------------------------------------------------------
# static pins (no engine import at module level; dry-run stays hermetic)
# --------------------------------------------------------------------------
def static_pins(hash_model=False):
    import _e3gpu_run as E
    dll = Path(E.VK)
    model = Path(E.MODEL)
    out = {
        "model": {"path": str(model), "bytes": model.stat().st_size,
                  "expected_bytes": E.MODEL_BYTES,
                  "ok": model.stat().st_size == E.MODEL_BYTES, "sha16": None},
        "dll": {"path": str(dll), "sha16": sha16(dll.read_bytes()),
                "bytes": dll.stat().st_size, "expected_sha16": FROZEN_DLL_SHA,
                "expected_bytes": E.VK_BYTES,
                "ok": sha16(dll.read_bytes()) == FROZEN_DLL_SHA
                      and dll.stat().st_size == E.VK_BYTES},
        "engine_const": {"NGL": E.NGL, "NCTX": E.NCTX, "NSEQ": E.NSEQ,
                         "KV": E.KV, "CHAT_START": E.CHAT_START,
                         "expected": {"NGL": 36, "NCTX": 8192, "NSEQ": 8,
                                      "KV": "q8_0", "CHAT_START": 4096}},
        "turn_prompt_template_sha16": sha16(TURN_TEMPLATE.encode("utf-8")),
        "extraction_prompt_sha16": FROZEN_EXTRACTION_PROMPT_SHA,
        "judge_prereg_sha16": FROZEN_JUDGE_PRE_SHA,
        "no_grammar": True, "temperature": 0, "sampling": "argmax_greedy",
        "n_predict": N_PREDICT, "one_shot": True,
    }
    ec = out["engine_const"]
    out["engine_const"]["ok"] = all((
        ec["NGL"] == 36, ec["NCTX"] == 8192, ec["NSEQ"] == 8,
        ec["KV"] == "q8_0", ec["CHAT_START"] == 4096))
    if hash_model:
        out["model"]["sha16"], n = sha16_file(model)
        out["model"]["sha16_bytes_read"] = n
    return out


# --------------------------------------------------------------------------
# host gate (§3 "host gate"; fail closed, no model load)
# --------------------------------------------------------------------------
def host_gate():
    """Compute the frozen host gate.  Mirrors the (b2)/(b4) gate contract.

    booleans: prereg_ok, dll_ok, model_ok, free_ram_ok (>=8388608 KB),
    vram_baseline_ok (<=1.5 GiB), gpu_procs_ok (no proc >256 MiB, with the
    Lead-authorized lone-dwm.exe exception), boot_id_ok.
    """
    import _e3gpu_run as E
    import run_m5c2_r2 as R2

    g = None
    details = []
    samples = []
    for _ in range(8):
        g = E.gate_values()
        raw = g.get("gpu_procs_gt256mb")
        corrected, cmd, details = R2.gpu_proc_count_exact()
        g["gpu_procs_gt256mb_reported_by_E"] = raw
        g["gpu_procs_gt256mb"] = corrected if corrected is not None else 999
        g["gpu_proc_query"] = cmd
        g["gpu_proc_details"] = details
        samples.append(g["gpu_procs_gt256mb"])
        if g["gpu_procs_gt256mb"] == 0:
            break
        time.sleep(0.5)
    g["gpu_proc_samples"] = samples

    g["prereg_path"] = rel(PRE)
    g["prereg_sha16"] = sha16(PRE.read_bytes())
    g["prereg_bytes"] = PRE.stat().st_size
    g["prereg_ok"] = (g["prereg_sha16"] == PRE_SHA16
                      and g["prereg_bytes"] == PRE_BYTES)
    g["free_ram_ok"] = (g.get("free_ram_kb") or 0) >= 8388608
    vram = g.get("vram_baseline_gib")
    g["vram_baseline_ok"] = isinstance(vram, (int, float)) and vram <= 1.5
    g["boot_id_ok"] = bool(g.get("boot_id"))
    dll = Path(E.VK)
    g["dll_path"] = str(dll)
    g["dll_sha16"] = sha16(dll.read_bytes())
    g["dll_bytes"] = dll.stat().st_size
    g["dll_ok"] = (g["dll_sha16"] == FROZEN_DLL_SHA
                   and g["dll_sha16"] == E.VK_SHA16
                   and g["dll_bytes"] == E.VK_BYTES)
    model = Path(E.MODEL)
    g["model_path"] = str(model)
    g["model_bytes"] = model.stat().st_size
    g["model_ok"] = g["model_bytes"] == E.MODEL_BYTES

    g["gpu_procs_ok"] = g["gpu_procs_gt256mb"] == 0
    exceptions = []
    if not g["gpu_procs_ok"]:
        parsed = []
        for d in details:
            m = re.search(r"NAME=(\S+)\s+BYTES=(\d+)", str(d))
            if m:
                parsed.append((m.group(1), int(m.group(2))))
        count = int(g.get("gpu_procs_gt256mb") or 0)
        other_ok = all(bool(g.get(k)) for k in (
            "prereg_ok", "free_ram_ok", "vram_baseline_ok", "boot_id_ok",
            "dll_ok", "model_ok"))
        baseline_ok = float(g.get("vram_baseline_gib") or 999) <= 1.5
        # Exact process name only; the compositor is not a compute workload.
        if (parsed and len(parsed) == count and count > 0
                and all(name == "dwm" for name, _ in parsed)
                and other_ok and baseline_ok):
            exceptions = [{
                "name": "dwm.exe",
                "observed_process_name": name,
                "bytes": byt,
                "threshold_bytes": 268435456,
                "reason": "system desktop compositor, not a compute workload",
            } for name, byt in parsed]
            g["gpu_procs_ok_raw"] = False
            g["gpu_procs_ok"] = True
            g["gate_exception_applied"] = True
    g["gate_exceptions"] = exceptions
    g["gate_ok"] = all(g[k] for k in (
        "prereg_ok", "dll_ok", "model_ok", "free_ram_ok",
        "vram_baseline_ok", "gpu_procs_ok", "boot_id_ok"))
    return g, exceptions


def write_refused(mode, gate, exceptions, extra=None):
    out = {
        "schema": "m5c2_b5_hostgate_refused_v1",
        "status": "未接上",
        "mode": mode,
        "reason": "host gate failed before any model load",
        "prereg": {"sha16": PRE_SHA16, "bytes": PRE_BYTES},
        "gate": gate,
        "gate_exceptions": exceptions,
        "n_forward": 0,
        "n_forward_attempted": 0,
        "no_model_loaded": True,
        "signals_sent": False,
        "no_parent_signals": True,
        "one_shot_consumed": False,
        "one_shot_consumed_reason": "no_token_no_forward",
        "abort_class": "device_gate_failed",
        "rerun_allowed": True,
        "retry_rule": "re-run only after a fresh gate and a written trace; "
                      "never auto-retry",
    }
    if extra:
        out.update(extra)
    write_json_atomic(REFUSED, out)
    print(json.dumps({k: out[k] for k in ("status", "mode", "reason",
                                          "gate_exceptions")},
                     ensure_ascii=False, indent=1))
    return out


# --------------------------------------------------------------------------
# dry run: static validation only
# --------------------------------------------------------------------------
def existing_attempt():
    if not ART.exists():
        return None
    try:
        d = json.loads(ART.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"path": str(ART), "parse_error": repr(e)}
    return {"path": rel(ART),
            "sha16": sha16(ART.read_bytes()), "bytes": ART.stat().st_size,
            "status": d.get("status"),
            "one_shot_consumed": d.get("one_shot_consumed"),
            "rerun_allowed": d.get("rerun_allowed"),
            "n_forward": d.get("n_forward"),
            "attempts": len(d.get("attempts") or [])}


def dry_run(scenes, prereg, pins):
    rows = []
    for s in scenes:
        for q in s["questions"]:
            p = prompt_text(s["source_text"], q["question"])
            rows.append({
                "qid": q["qid"], "scenario": s["sid"], "domain": s["domain"],
                "kind": q["kind"], "source_chars": len(s["source_text"]),
                "question": q["question"],
                "turn_prompt": turn_prompt(q["question"]),
                "prompt_sha16": sha16(p.encode("utf-8")),
            })
    checks = {
        "prereg_pin": True,
        "n_scenarios": len(scenes),
        "n_questions": len(rows),
        "kinds_per_scene": KIND_ORDER,
        "source_chars_range": [min(len(s["source_text"]) for s in scenes),
                               max(len(s["source_text"]) for s in scenes)],
        "model_bytes_ok": pins["model"]["ok"],
        "dll_ok": pins["dll"]["ok"],
        "engine_const_ok": pins["engine_const"]["ok"],
        "no_grammar": True, "greedy": True, "n_predict": N_PREDICT,
        "chat_start": CHAT_START,
        "vram_target_gib": TARGET_GIB, "vram_fuse_gib": FUSE_GIB,
        "scenario_timeout_s": SCENARIO_TIMEOUT, "total_timeout_s": TOTAL_TIMEOUT,
        "writes_any_file": False,
    }
    print(json.dumps({
        "schema": "m5c2_b5_gen_dry_run_v1",
        "status": "dry_run_only",
        "prereg": prereg,
        "pins": pins,
        "checks": checks,
        "host_gate": {"evaluated": False,
                      "reason": "dry-run never evaluates the host gate; "
                                "--gate-check does it without loading the model"},
        "one_shot": {"one_shot": True, "already_consumed": bool(
            existing_attempt() and existing_attempt().get("one_shot_consumed")),
            "existing_artifact": existing_attempt()},
        "n_forward": 0, "no_gpu": True, "no_model": True, "no_network": True,
        "questions": rows,
    }, ensure_ascii=False, indent=1))
    return 0


# --------------------------------------------------------------------------
# the one-shot run
# --------------------------------------------------------------------------
def classify_abort(aborted, engine_loaded, attempted, answers_nonempty, rc_ok):
    """Abort classes used by docs/_work/B5-RUN-PLAN.md §5."""
    if aborted is None:
        return "completed"
    if not engine_loaded:
        return "engine_load_failed"
    if attempted == 0:
        a = str(aborted)
        if a.startswith("VRAM fuse"):
            return "vram_fuse_pre_forward"
        if "timeout" in a.lower():
            return "timeout_pre_forward"
        return "pre_forward_abort"
    if not answers_nonempty:
        return "forward_failed_no_output"
    return "forward_failed_partial_output"


def run(scenes, prereg, expected_sha16):
    prev = existing_attempt()
    if prev and prev.get("one_shot_consumed"):
        raise SystemExit(
            "REFUSE: M5C2-B5-GEN.json exists and one_shot_consumed=true; "
            "the (b5) one-shot is already consumed and must not be re-run "
            "(PREREG-M5-C2-B5.md §0/§6).  See docs/_work/B5-RUN-PLAN.md §5.")
    gate0, exc0 = host_gate()
    if expected_sha16 and gate0["prereg_sha16"] != expected_sha16:
        raise SystemExit("expected prereg sha16 mismatch: %s != %s" %
                         (gate0["prereg_sha16"], expected_sha16))
    if not gate0.get("gate_ok"):
        write_refused("gen_run", gate0, exc0,
                      extra={"prereg": prereg, "expected_prereg_sha16": expected_sha16})
        return 2

    pins = static_pins(hash_model=True)

    import run_m5c2_floor as F
    import run_m5_b2_v2 as G

    sampler = F.start_sampler()
    t0 = time.perf_counter()
    eng = None
    results = []
    forwards = 0
    attempted = 0
    aborted = None
    engine_loaded = False
    meta = {}
    attempts = (prev or {}).get("attempts") or []
    try:
        try:
            eng, meta = G.open_engine()
            engine_loaded = True
        except Exception as e:  # noqa: BLE001
            aborted = "engine load failed: %r" % (e,)
            raise
        for s in scenes:
            if time.perf_counter() - t0 > TOTAL_TIMEOUT:
                aborted = "total timeout >%ds" % TOTAL_TIMEOUT
                break
            try:
                peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
            except Exception:  # noqa: BLE001
                peak = None
            if peak is not None and peak > FUSE_GIB:
                aborted = "VRAM fuse: peak %.4f > %.1f GiB" % (peak, FUSE_GIB)
                break
            t_sc = time.perf_counter()
            build = G.build_text_block(eng, s["source_text"])
            for qi, q in enumerate(s["questions"]):
                if time.perf_counter() - t_sc > SCENARIO_TIMEOUT:
                    aborted = "scenario %s timeout >%ds" % (s["sid"], SCENARIO_TIMEOUT)
                    break
                pos = CHAT_START if qi == 0 else int(eng.pos_max(G.P.LIVE)) + 1
                p = prompt_text(s["source_text"], q["question"])
                rec = {
                    "qid": q["qid"], "scenario": s["sid"], "domain": s["domain"],
                    "kind": q["kind"], "source_text": s["source_text"],
                    "question": q["question"],
                    "turn_prompt": turn_prompt(q["question"]),
                    "prompt_sha16": sha16(p.encode("utf-8")),
                    "prompt_chars": len(p),
                    "params": {"n_predict": N_PREDICT, "temperature": 0,
                               "sampling": "argmax_greedy", "seed": None,
                               "grammar": None, "chat_start": CHAT_START,
                               "pos_asked": pos,
                               "kv_policy": "source_once_per_scenario_then_questions_no_reset"},
                    "build": build, "answer_full": None, "answer_sha16": None,
                    "answer_chars": None, "rc": None,
                    "n_tokens_before": None, "n_tokens_after": None,
                    "elapsed_s": None, "error": None,
                }
                attempted += 1
                try:
                    one = G.ask_one(eng, q["question"], pos, N_PREDICT)
                    rec.update({
                        "answer_full": one["answer"],
                        "answer_sha16": one["answer_sha16"],
                        "answer_chars": one["answer_chars"],
                        "rc": one["rc"],
                        "n_tokens_before": one["n_tokens_before"],
                        "n_tokens_after": one["n_tokens_after"],
                        "elapsed_s": one["elapsed_s"],
                    })
                    forwards += 1
                except Exception as e:  # noqa: BLE001
                    rec["error"] = repr(e)
                    aborted = "question failed: %s %r" % (q["qid"], e)
                results.append(rec)
                write_json_atomic(RAW, {
                    "schema": "m5c2_b5_gen_raw_v1",
                    "prereg_sha16": PRE_SHA16,
                    "n_forward": forwards,
                    "n_forward_attempted": attempted,
                    "answers_nonempty": sum(
                        1 for r in results if (r.get("answer_full") or "").strip()),
                    "aborted": aborted,
                    "results": results,
                })
                if aborted:
                    break
            if aborted:
                break
        gate1, exc1 = host_gate()
        peak = F.stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 3)

        answers_nonempty = sum(
            1 for r in results if (r.get("answer_full") or "").strip())
        rc_ok = sum(1 for r in results
                    if isinstance(r.get("rc"), int) and r["rc"] >= 0)
        consumed = bool(answers_nonempty) or bool(rc_ok)
        abort_class = classify_abort(aborted, engine_loaded, attempted,
                                     answers_nonempty, rc_ok)
        rerun_allowed = not consumed
        conservative_note = None
        if attempted and not consumed and abort_class == "forward_failed_no_output":
            conservative_note = (
                "engine was loaded and a forward was attempted but produced no "
                "answer; the GPU may still have sampled tokens.  The protocol "
                "classifies this by flushed output (rerun allowed), but the "
                "LEAD must confirm before any rerun.")

        if aborted is not None:
            attempts = attempts + [{
                "attempt": len(attempts) + 1,
                "aborted": aborted,
                "abort_class": abort_class,
                "n_forward": forwards,
                "n_forward_attempted": attempted,
                "answers_nonempty": answers_nonempty,
                "gate_before": gate0,
                "gate_after": gate1,
                "gate_exceptions": exc0,
                "gate_exceptions_after": exc1,
                "peak_gib": peak,
                "elapsed_s": elapsed,
                "one_shot_consumed": consumed,
                "rerun_allowed": rerun_allowed,
            }]

        out = {
            "schema": "m5c2_b5_gen_v1",
            "status": "已生成" if aborted is None else "未接上",
            "prereg": prereg,
            "prereg_sha16": PRE_SHA16,
            "pins": pins,
            "engine_meta": meta,
            "n_gpu_layers_input": 36,
            "n_gpu_layers_readback": meta.get("n_gpu_layers_readback"),
            "n_gpu_layers_readback_total": meta.get("n_gpu_layers_readback_total"),
            "offloaded_log_line": meta.get("offloaded_log_line"),
            "n_predict": N_PREDICT,
            "temperature": 0,
            "sampling": "argmax_greedy",
            "seed": None,
            "grammar": None,
            "dll": meta.get("dll_sha16"),
            "frozen_dll_sha16": FROZEN_DLL_SHA,
            "model_bytes": pins["model"]["bytes"],
            "model_sha16": pins["model"].get("sha16"),
            "chat_start": CHAT_START,
            "kv_policy": "source_once_per_scenario_then_questions_no_reset",
            "n_scenarios": len(scenes),
            "n_questions_planned": N_QUESTIONS,
            "n_forward": forwards,
            "n_forward_attempted": attempted,
            "answers_nonempty": answers_nonempty,
            "aborted": aborted,
            "abort_class": abort_class,
            "one_shot_consumed": consumed,
            "one_shot_consumed_reason": ("answer_or_completed_forward" if consumed
                                         else "no_token_no_forward"),
            "rerun_allowed": rerun_allowed,
            "conservative_note": conservative_note,
            "retry_rule": "never auto-retry; a rerun is only allowed when "
                          "rerun_allowed=true and needs a fresh gate + trace",
            "qa": results,
            "sentence_split_done": False,
            "sentence_split_step": "run_m5c2_b5_judge.py --split",
            "gate_before": gate0,
            "gate_after": gate1,
            "gate_exceptions": exc0,
            "gate_exceptions_after": exc1,
            "peak_vram": peak,
            "peak_gib": peak,
            "target_gib": TARGET_GIB,
            "fuse_gib": FUSE_GIB,
            "elapsed": elapsed,
            "elapsed_s": elapsed,
            "signals_sent": False,
            "no_parent_signals": True,
            "no_grammar": True,
            "no_model_switch": True,
            "no_prompt_rewrite": True,
            "raw_answers_preserved": True,
            "no_judge": True,
            "no_gold": True,
            "no_network": True,
            "prompt_template_sha16": pins["turn_prompt_template_sha16"],
            "extraction_prompt_sha16": FROZEN_EXTRACTION_PROMPT_SHA,
            "judge_prereg_sha16": FROZEN_JUDGE_PRE_SHA,
            "attempt": len(attempts) if aborted is not None else len(attempts) + 1,
            "attempts": attempts,
        }
        write_json_atomic(ART, out)
        print(json.dumps({k: out[k] for k in (
            "status", "n_forward", "n_forward_attempted", "answers_nonempty",
            "aborted", "abort_class", "one_shot_consumed", "rerun_allowed",
            "peak_gib", "elapsed_s", "prereg_sha16")},
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
    ap.add_argument("--expected-prereg-sha16", default=None)
    ap.add_argument("--hash-model", action="store_true",
                    help="also hash the 9 GB model in --dry-run (static, no GPU)")
    a = ap.parse_args()
    modes = [m for m in (a.dry_run, a.gate_check, a.run) if m]
    if len(modes) != 1:
        print("choose exactly one of --dry-run / --gate-check / --run")
        return 2
    scenes = parse_b5()
    prereg = verify_prereg()
    if a.dry_run:
        return dry_run(scenes, prereg, static_pins(hash_model=a.hash_model))
    if a.gate_check:
        gate, exc = host_gate()
        if not gate.get("gate_ok"):
            write_refused("gate_check", gate, exc)
            return 2
        print(json.dumps({
            "schema": "m5c2_b5_gate_check_v1",
            "status": "gate_ok",
            "gate": gate, "gate_exceptions": exc,
            "n_forward": 0, "no_model_loaded": True, "no_gpu_work": True,
        }, ensure_ascii=False, indent=1))
        return 0
    return run(scenes, prereg, a.expected_prereg_sha16)


if __name__ == "__main__":
    sys.exit(main())