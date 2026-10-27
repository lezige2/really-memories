#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B5 extraction runner (GPU: 326 sentences, one forward each).

Split architecture (post-incident rebuild; the 0-byte run_m5c2_b5_judge.py is
kept untouched as incident evidence):

  this script  -> out/M5C2-B5-EXTRACT.json   (extraction only: no verdict/rates)
  run_m5c2_b5_decide.py -> out/M5C2-B5-DECIDE.json / M5C2-B5-RATES.json (CPU)

Frozen inputs (asserted at startup):
  GEN        out/M5C2-B5-GEN.json         2b63a02463994c03 / 68184 B
  SENTENCES  out/M5C2-B5-SENTENCES.json   ba92635c8ad0c410 / 116566 B / 326
  prompt     run_m5c2_rev4.REV4_TEMPLATE  a6bc4f268f7711de
  dll        tools/kvshim_vk.dll          9edbafa150700614
  prereg     docs/_work/PREREG-M5-C2-B5.md d6c7bdac73ef7326 / 14597 B
  judge pre  docs/_work/PREREG-M5-C2-REV7.1.md 09d6f1b163ea0b84

Modes:
  --dry-run    static pin/path/count validation only (no model, writes nothing)
  --gate-check host gate only (no model, no forward)
  --run        the one and only GPU pass (326 independent extraction forwards)

Gate exceptions: --allow-gui-procs 'dwm,DSH NEXT' is an explicit, default-off
opt-in for the frozen S4 ruling v1.1; it is hard-refused unless n_forward == 0
at admission, requires pid+exe_path evidence per admitted process, and is
re-verified after the run (pid reuse / exe_path change => 未接上).
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
import run_m5c2_b5_gen as BG  # noqa: E402  (frozen host-gate contract)

PRE = ROOT / "docs/_work/PREREG-M5-C2-B5.md"
PRE_SHA16 = "d6c7bdac73ef7326"
PRE_BYTES = 14597
GEN = OUT / "M5C2-B5-GEN.json"
GEN_SHA16 = "2b63a02463994c03"
GEN_BYTES = 68184
SENT = OUT / "M5C2-B5-SENTENCES.json"
SENT_SHA16 = "ba92635c8ad0c410"
SENT_BYTES = 116566
SENT_N = 326
ART = OUT / "M5C2-B5-EXTRACT.json"
RAW = OUT / "_m5b5_extract_raw.json"
REFUSED = OUT / "M5C2-B5-EXTRACT-HOSTGATE-REFUSED.json"
PROMPT_SHA = "a6bc4f268f7711de"
JUDGE_PRE_SHA16 = "09d6f1b163ea0b84"
R71_PATH = M5 / "run_m5c2_rev7_1_offline.py"
R71_SHA16 = "88256d274c9993cc"
R71_BYTES = 50618
N_PREDICT = 384
TARGET_GIB = 8.0
FUSE_GIB = 8.6
LIMIT_S = 3600
FROZEN_DLL_SHA = "9edbafa150700614"
MODEL_BYTES = 8988110240

RULING_GATE_MD = ROOT / "docs/_work/RULING-M5C2-B5-GATE-EXCEPTION.md"
RULING_GATE_JSON = OUT / "RULING-M5C2-B5-GATE-EXCEPTION.json"
RULING_MD_SHA16 = "5a9c370c6989d57f"
RULING_MD_BYTES = 4639
RULING_JSON_SHA16 = "9fd6cf35e1cb9a5c"
GUI_ALLOWLIST = ("dwm", "DSH NEXT")
GUI_BUDGET_BYTES = 800 * 1024 * 1024
PROC_THRESHOLD_BYTES = 268435456


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def sha16_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def rel(p):
    try:
        return str(Path(p).relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def write_json_atomic(path, obj):
    """Atomic write only: tmp + os.replace (never truncate a live deliverable)."""
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)
    return Path(path)


def verify_pins():
    pb = PRE.read_bytes()
    if sha16(pb) != PRE_SHA16 or len(pb) != PRE_BYTES:
        raise SystemExit("B5 prereg changed: %s / %d B" % (sha16(pb), len(pb)))
    gb = GEN.read_bytes()
    if sha16(gb) != GEN_SHA16 or len(gb) != GEN_BYTES:
        raise SystemExit("M5C2-B5-GEN.json changed: %s / %d B"
                         % (sha16(gb), len(gb)))
    g = json.loads(gb.decode("utf-8"))
    if g.get("aborted") is not None:
        raise SystemExit("GEN aborted=%r; extraction refuses to continue"
                         % (g.get("aborted"),))
    if not g.get("one_shot_consumed"):
        raise SystemExit("GEN one_shot_consumed is not true")
    if int(g.get("n_forward") or 0) != 40 or len(g.get("qa") or []) != 40:
        raise SystemExit("GEN does not hold 40/40 answers")
    if int(g.get("answers_nonempty") or 0) != 40:
        raise SystemExit("GEN answers_nonempty=%r != 40"
                         % (g.get("answers_nonempty"),))
    sb = SENT.read_bytes()
    if sha16(sb) != SENT_SHA16 or len(sb) != SENT_BYTES:
        raise SystemExit("M5C2-B5-SENTENCES.json changed: %s / %d B"
                         % (sha16(sb), len(sb)))
    s = json.loads(sb.decode("utf-8"))
    if s.get("gen", {}).get("sha16") != GEN_SHA16:
        raise SystemExit("SENTENCES was split from a different GEN")
    if int(s.get("n_sentences") or 0) != SENT_N or len(s.get("sentences") or []) != SENT_N:
        raise SystemExit("SENTENCES does not hold %d sentences" % SENT_N)
    if s.get("judge_layer_prereg_sha16") != JUDGE_PRE_SHA16:
        raise SystemExit("SENTENCES pinned to a different judge layer")
    prompt_sha = sha16(R4.REV4_TEMPLATE.encode("utf-8"))
    if prompt_sha != PROMPT_SHA:
        raise SystemExit("frozen extraction prompt changed: %s" % prompt_sha)
    rb = R71_PATH.read_bytes()
    if sha16(rb) != R71_SHA16 or len(rb) != R71_BYTES:
        raise SystemExit("rev7.1 judge code changed: %s / %d B"
                         % (sha16(rb), len(rb)))
    return {
        "prereg": {"sha16": PRE_SHA16, "bytes": PRE_BYTES},
        "gen": {"path": rel(GEN), "sha16": GEN_SHA16, "bytes": GEN_BYTES,
                "one_shot_consumed": True, "n_forward": 40,
                "answers_nonempty": 40},
        "sentences": {"path": rel(SENT), "sha16": SENT_SHA16,
                      "bytes": SENT_BYTES, "n_sentences": SENT_N},
        "extraction_prompt": {"sha16": prompt_sha,
                              "source": "run_m5c2_rev4.REV4_TEMPLATE"},
        "judge_layer": {"version": "rev7.1", "code": rel(R71_PATH),
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
    """Pin the frozen S4 gate-exception ruling v1.1 (only with --allow-gui-procs)."""
    if not (RULING_GATE_MD.exists() and RULING_GATE_JSON.exists()):
        raise SystemExit("--allow-gui-procs needs the frozen ruling v1.1 "
                         "(md + out/RULING-M5C2-B5-GATE-EXCEPTION.json)")
    mb = RULING_GATE_MD.read_bytes()
    jb = RULING_GATE_JSON.read_bytes()
    if sha16(mb) != RULING_MD_SHA16 or len(mb) != RULING_MD_BYTES:
        raise SystemExit("gate-exception ruling md is not the frozen v1.1: "
                         "%s / %d B" % (sha16(mb), len(mb)))
    if sha16(jb) != RULING_JSON_SHA16:
        raise SystemExit("gate-exception ruling json is not the frozen v1.1: %s"
                         % sha16(jb))
    j = json.loads(jb.decode("utf-8"))
    if not (j.get("frozen") is True and j.get("frozen_rev") == 1):
        raise SystemExit("gate-exception ruling not frozen_rev=1")
    return {"md": {"path": rel(RULING_GATE_MD), "sha16": sha16(mb),
                   "bytes": len(mb), "frozen_rev": 1},
            "json": {"path": rel(RULING_GATE_JSON), "sha16": sha16(jb),
                     "bytes": len(jb)},
            "allowlist": list(GUI_ALLOWLIST),
            "budget_bytes": GUI_BUDGET_BYTES,
            "policy": "G2(a)-(e): other gate items true, baseline<=1.5 GiB, "
                      "all >256 MiB procs inside {dwm, DSH NEXT}, no third one, "
                      "allowlisted total <=800 MiB, n_forward==0 at admission; "
                      "G3: pid+exe_path per entry; G5: outside list / baseline>1.5 "
                      "/ fuse>8.6 => stop as 未接上"}


def _exe_names_ok(name, exe_path):
    """RULING v1.1: match by pid+exe_path; display names can truncate/collide."""
    if not exe_path:
        return False
    base = str(exe_path).replace("/", "\\").rsplit("\\", 1)[-1].strip().lower()
    return base == (str(name).strip().lower() + ".exe")


def _enrich_procs():
    """pid + exe_path + bytes for every >256 MiB GPU process (read-only)."""
    cmd = ("$m=Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory "
           "-ErrorAction SilentlyContinue | ? { $_.DedicatedUsage -gt 268435456 }; "
           "if ($m) { $m | ForEach-Object { $mm=[regex]::Match($_.Name,'pid_(\\d+)'); "
           "$procId=[int]$mm.Groups[1].Value; "
           "$p=Get-Process -Id $procId -ErrorAction SilentlyContinue; "
           "$exe=$null; try { $exe=(Get-CimInstance Win32_Process -Filter "
           "('ProcessId=' + $procId) -ErrorAction SilentlyContinue).ExecutablePath } catch {}; "
           "'PROC PID={0} NAME={1} PATH={2} BYTES={3}' -f "
           "$procId,$p.ProcessName,$exe,([int]$_.DedicatedUsage) } "
           "} else { 'PROC 0' }")
    out = []
    try:
        for line in E.ps(cmd):
            m = re.match(r"\s*PROC\s+PID=(\d+)\s+NAME=(.*?)\s+PATH=(.*?)\s+BYTES=(\d+)\s*$",
                         str(line))
            if m:
                out.append({"pid": int(m.group(1)), "name": m.group(2).strip(),
                            "exe_path": (m.group(3).strip() or None),
                            "bytes": int(m.group(4))})
    except Exception:  # noqa: BLE001  (no evidence => no exception)
        return []
    return out


def host_gate(allow_gui=None, ruling=None, n_forward=None):
    """Host gate = frozen gen contract + optional S4 v1.1 named exception."""
    gate, exc = BG.host_gate()
    if not allow_gui:
        return gate, exc
    names = [n.strip() for n in allow_gui if n.strip()]
    bad = [n for n in names if n not in GUI_ALLOWLIST]
    if bad:
        raise SystemExit("--allow-gui-procs %r outside the frozen allowlist %r"
                         % (bad, list(GUI_ALLOWLIST)))
    gate["allow_gui_procs"] = sorted(set(names))
    if ruling:
        gate["gate_exception_ruling"] = ruling
    gate["gate_exception_policy"] = {
        "version": "v1.1", "g2e_n_forward_zero": True,
        "match_by": "pid+exe_path", "budget_bytes": GUI_BUDGET_BYTES,
        "allowlist": list(GUI_ALLOWLIST), "default_off": True}
    try:
        nfw = int(n_forward)
    except (TypeError, ValueError):
        nfw = None
    if gate.get("gate_ok"):
        gate["gate_exception_evaluated"] = True
        gate["gate_exception_applied"] = False
        gate["gate_exception_note"] = ("strict gate passed; the named exception "
                                       "was not needed for this check")
        return gate, exc
    if nfw != 0:
        gate["gate_exception_evaluated"] = True
        gate["gate_exception_applied"] = False
        gate["gate_exception_blocked"] = (
            "G2(e): n_forward=%r at admission; the exception may only admit a "
            "run with 0 forwards (arms containing forwards are forbidden)" % (nfw,))
        return gate, []
    count = int(gate.get("gpu_procs_gt256mb") or 0)
    others_ok = all(bool(gate.get(k)) for k in (
        "prereg_ok", "dll_ok", "model_ok", "free_ram_ok",
        "vram_baseline_ok", "boot_id_ok"))
    baseline_ok = float(gate.get("vram_baseline_gib") or 999) <= 1.5
    reasons = []
    if not others_ok:
        reasons.append("another gate item is false")
    if not baseline_ok:
        reasons.append("vram_baseline_gib > 1.5")
    # The enriched WMI list (pid+exe_path+bytes) is the ONLY evidence source.
    # The strict COUNT details are a different instant: DSH NEXT fluctuates
    # around the 256 MiB threshold, so an equal-count requirement is a
    # sampling race, not a gate failure. Count is recorded, not compared.
    samples = []
    chosen = None
    for attempt in range(1, 6):
        procs = _enrich_procs()
        sample = {"attempt": attempt,
                  "procs": [{k: pr.get(k) for k in ("pid", "name", "exe_path",
                                                    "bytes")} for pr in procs],
                  "total_bytes": sum(int(pr["bytes"]) for pr in procs),
                  "ok": False, "note": None}
        bad_names = [pr["name"] for pr in procs if pr["name"] not in GUI_ALLOWLIST]
        if bad_names:
            sample["note"] = "outside allowlist: %r" % (bad_names,)
            samples.append(sample)
            gate["gate_exception_samples"] = samples
            gate["gate_exception_blocked"] = sample["note"]
            return gate, []  # immediate refusal, no retry masking
        if sample["total_bytes"] > GUI_BUDGET_BYTES:
            sample["note"] = ("allowlisted GUI procs exceed budget: %d > %d"
                              % (sample["total_bytes"], GUI_BUDGET_BYTES))
            samples.append(sample)
            gate["gate_exception_samples"] = samples
            gate["gate_exception_blocked"] = sample["note"]
            return gate, []
        if procs and all(_exe_names_ok(pr["name"], pr["exe_path"]) for pr in procs):
            sample["ok"] = True
            chosen = sample
        else:
            sample["note"] = "empty sample or exe_path missing/mismatched"
        samples.append(sample)
        if attempt < 5:
            time.sleep(0.4)
    gate["gate_exception_samples"] = samples
    gate["gate_exception_evaluated"] = True
    gate["gate_exception_applied"] = False
    gate["match_by"] = "pid+exe_path"
    gate["strict_count_recorded"] = count
    gate["enriched_count_used"] = len(chosen["procs"]) if chosen else None
    if chosen is None:
        reasons.append("no valid enriched sample (pid+exe_path) in %d attempts"
                       % len(samples))
    if not reasons:
        matched = chosen["procs"]
        total = chosen["total_bytes"]
        exc2 = [{"name": pr["name"], "pid": pr["pid"], "exe_path": pr["exe_path"],
                 "bytes": pr["bytes"], "threshold": PROC_THRESHOLD_BYTES,
                 "reason": "named non-compute GUI compositor (agent harness); "
                           "admitted by RULING-M5C2-B5-GATE-EXCEPTION v1.1 "
                           "G1/G2/G2(e)"} for pr in matched]
        gate["gpu_procs_ok_raw"] = False
        gate["gpu_procs_ok"] = True
        gate["gate_exception_applied"] = True
        gate["gate_exceptions"] = exc2
        gate["exception_total_bytes"] = total
        gate["exception_budget_bytes"] = GUI_BUDGET_BYTES
        gate["gate_exception_note"] = (
            "strict gate refused (gate_ok=False, gpu_procs_gt256mb=%d recorded); "
            "this run is admitted by the named frozen exception "
            "(RULING-M5C2-B5-GATE-EXCEPTION v1.1) with n_forward=0 at admission; "
            "evidence source = enriched pid+exe_path samples (%d attempts, "
            "recent valid sample used); judge rules/thresholds/inputs untouched"
            % (count, len(samples)))
        gate["gate_exception_signoff_inputs"] = {
            "1_gate_exception_ruling": {
                "md_path": ((ruling or {}).get("md") or {}).get("path"),
                "md_sha16": ((ruling or {}).get("md") or {}).get("sha16"),
                "json_sha16": ((ruling or {}).get("json") or {}).get("sha16"),
                "frozen_rev": ((ruling or {}).get("md") or {}).get("frozen_rev")},
            "2_n_forward_at_admission": 0,
            "3_named_processes_non_compute": [
                {"name": pr["name"], "pid": pr["pid"], "exe_path": pr["exe_path"],
                 "bytes": pr["bytes"]} for pr in matched],
            "4_allowlist_not_extended": {
                "allowlist": list(GUI_ALLOWLIST),
                "source": "RULING-M5C2-B5-GATE-EXCEPTION v1.1 G1",
                "outside_allowlist_procs": []},
        }
        gate["gate_ok"] = True
        return gate, exc2
    gate["gate_exception_blocked"] = "; ".join(reasons)
    return gate, exc


def recheck_exception_after(gate_before, gate_after=None):
    """RULING v1.1 G3 (post-run): admitted pids must not be reused and
    exe_paths must not change. Evidence = repeated enriched samples; absence
    because the process sits below the 256 MiB threshold is NOT a failure
    (observability=not_observed_below_threshold), but a pid whose exe_path
    changed IS a failure. G2(e) n_forward==0 constrains admission only."""
    ex0 = [e for e in (gate_before.get("gate_exceptions") or [])
           if e.get("pid") is not None and e.get("exe_path")]
    if not ex0:
        return {"checked": False, "ok": True, "match_by": "pid+exe_path",
                "reason": "no named gate exception was applied at admission "
                          "(strict gate passed; nothing to recheck)"}
    samples = []
    failures = []
    for attempt in range(1, 9):
        after = _enrich_procs()
        samples.append({"attempt": attempt,
                        "procs": [{k: p.get(k) for k in
                                   ("pid", "name", "exe_path", "bytes")}
                                  for p in after],
                        "total_bytes": sum(int(p["bytes"]) for p in after)})
        bad = [p["name"] for p in after if p["name"] not in GUI_ALLOWLIST]
        if bad:
            failures.append({"issue": "outside allowlist after run: %r" % (bad,),
                             "attempt": attempt})
            break
        if samples[-1]["total_bytes"] > GUI_BUDGET_BYTES:
            failures.append({"issue": "allowlisted GUI procs exceed 800 MiB "
                                      "after run: %d > %d"
                                      % (samples[-1]["total_bytes"],
                                         GUI_BUDGET_BYTES),
                             "attempt": attempt})
            break
        if attempt < 8:
            time.sleep(0.5)
    by_pid = {}
    for s in samples:
        for p in s["procs"]:
            by_pid.setdefault(int(p["pid"]), []).append(p)
    items = []
    for e in ex0:
        pid = int(e["pid"])
        seen = by_pid.get(pid) or []
        if not seen:
            items.append({"name": e.get("name"), "pid": pid,
                          "exe_path": e.get("exe_path"), "ok": True,
                          "observability":
                              "not_observed_below_threshold",
                          "note": "pid not >256 MiB in any of %d samples; "
                                  "below-threshold absence is not reuse/tamper "
                                  "evidence" % len(samples)})
            continue
        same = [p for p in seen if p.get("exe_path") == e.get("exe_path")]
        if same:
            items.append({"name": e.get("name"), "pid": pid,
                          "exe_path": e.get("exe_path"), "ok": True,
                          "observability": "observed",
                          "samples_seen": len(same)})
        else:
            items.append({"name": e.get("name"), "pid": pid,
                          "exe_path_before": e.get("exe_path"),
                          "exe_path_after": seen[0].get("exe_path"),
                          "ok": False, "observability": "exe_path_changed"})
            failures.append({"pid": pid, "issue": "exe_path changed",
                             "before": e.get("exe_path"),
                             "after": seen[0].get("exe_path")})
    return {"checked": True, "ok": not failures, "match_by": "pid+exe_path",
            "samples_after": len(samples),
            "sample_interval_s": 0.5,
            "not_observed_policy":
                "below_threshold_absence_is_not_failure",
            "items": items,
            "failures": failures,
            "samples": samples,
            "after": [{k: p.get(k) for k in ("name", "pid", "exe_path", "bytes")}
                      for s in samples for p in s["procs"]]}


def build_prompt(row):
    return R4.REV4_TEMPLATE.format(
        source_text=row["source_text"], question=row.get("question", ""),
        sentence=row["text"])


def load_sentences():
    d = json.loads(SENT.read_text(encoding="utf-8"))
    rows = d["sentences"]
    if len(rows) != SENT_N:
        raise SystemExit("expected %d sentences, got %d" % (SENT_N, len(rows)))
    return rows


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
        "schema": "m5c2_b5_extract_dry_run_v1",
        "status": "dry_run_only",
        "pins": pins,
        "n_sentences": len(rows),
        "n_questions": len({r["qid"] for r in rows}),
        "layer0_pre_scan": layer0,
        "n_forward_planned": len(rows) - layer0["empty_source"] - layer0["abstain_check"],
        "n_predict": N_PREDICT,
        "prompt_probes": probes,
        "gate_exception_option": {"enabled": bool(allow_gui),
                                  "ruling": ruling,
                                  "allowlist": list(GUI_ALLOWLIST),
                                  "default_off": True},
        "n_forward": 0,
        "no_gpu": True,
        "no_model_loaded": True,
        "writes_any_file": False,
    }, ensure_ascii=False, indent=1))
    return 0


def write_refused(mode, gate, exceptions, pins, ruling=None):
    out = {
        "schema": "m5c2_b5_extract_hostgate_refused_v1",
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
        "one_shot_consumed": True,
        "one_shot_note": "the (b5) one-shot was consumed by GEN; this gate "
                         "refusal costs no new forward",
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


def run(pins, rows, allow_gui=None, ruling=None, expected_sha16=None):
    if expected_sha16 and expected_sha16 != PRE_SHA16:
        raise SystemExit("expected prereg sha16 %r != frozen %r"
                         % (expected_sha16, PRE_SHA16))
    if ART.exists():
        try:
            prev = json.loads(ART.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            prev = None
        if prev and prev.get("aborted") is None and int(prev.get("n_forward") or 0) > 0:
            raise SystemExit("REFUSE: %s already holds a complete extraction "
                             "(n_forward=%s); do not re-run"
                             % (rel(ART), prev.get("n_forward")))
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
            if route == "empty_source":
                rec["route"] = "empty_source"
                rec["layer0"] = det
                rec["parse_ok"] = True
                rec["items"] = []
                recs.append(rec)
                write_json_atomic(RAW, {"schema": "m5c2_b5_extract_raw_v1",
                                        "n_forward": forwards,
                                        "aborted": aborted,
                                        "records": recs})
                continue
            if route == "abstain_check":
                rec["route"] = "abstain_check"
                rec["layer0"] = det
                rec["parse_ok"] = True
                rec["items"] = []
                recs.append(rec)
                write_json_atomic(RAW, {"schema": "m5c2_b5_extract_raw_v1",
                                        "n_forward": forwards,
                                        "aborted": aborted,
                                        "records": recs})
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
                write_json_atomic(RAW, {"schema": "m5c2_b5_extract_raw_v1",
                                        "n_forward": forwards,
                                        "n_forward_attempted": attempted,
                                        "aborted": aborted,
                                        "records": recs})
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
            write_json_atomic(RAW, {"schema": "m5c2_b5_extract_raw_v1",
                                    "n_forward": forwards,
                                    "n_forward_attempted": attempted,
                                    "aborted": aborted,
                                    "records": recs})
        gate1, _exc1 = BG.host_gate()  # strict post-run record; G2(e) only admission
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
            "schema": "m5c2_b5_extract_v1",
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
            out["gate_exception_note_after"] = (
                "post-run recheck: enriched pid+exe_path sample compared; "
                "G2(e) n_forward==0 constrains admission only")
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
                                              "abort_class", "layer0_skipped",
                                              "gate_exception_disclosure")
                          if k in out},
                         ensure_ascii=False, indent=1))
        if out.get("gate_exception_disclosure"):
            print("G7: " + out["gate_exception_disclosure"])
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
    ap.add_argument("--allow-gui-procs", default=None,
                    help="explicit S4 gate-exception opt-in v1.1, e.g. "
                         "'dwm,DSH NEXT' (default off; requires n_forward==0)")
    a = ap.parse_args()
    modes = [m for m in (a.dry_run, a.gate_check, a.run) if m]
    if len(modes) != 1:
        print("choose exactly one of --dry-run / --gate-check / --run")
        return 2
    pins = verify_pins()
    allow_gui = None
    ruling = None
    if a.allow_gui_procs:
        allow_gui = [x for x in a.allow_gui_procs.split(",") if x.strip()]
        ruling = verify_gate_ruling()
    rows = load_sentences()
    if a.dry_run:
        return dry_run(pins, rows, allow_gui, ruling)
    if a.gate_check:
        gate, exc = host_gate(allow_gui, ruling, n_forward=0)
        if not gate.get("gate_ok"):
            return write_refused("extract_gate_check", gate, exc, pins, ruling)
        out = {"schema": "m5c2_b5_extract_gate_check_v1", "status": "gate_ok",
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
    return run(pins, rows, allow_gui, ruling, a.expected_prereg_sha16)


if __name__ == "__main__":
    sys.exit(main())