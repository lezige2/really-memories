#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B5 judge REBUILD — independent reconstruction of run_m5c2_b5_judge.py.

The original run_m5c2_b5_judge.py was truncated to 0 bytes (no disk backup).
This file reconstructs a runnable judge runner from the frozen specification
only.  It does NOT import the lost file and does not touch it.

Authority (all read-only, sha16 asserted at start-up):
  docs/_work/PREREG-M5-C2-B5.md             d6c7bdac73ef7326 / 14,597 B
  docs/_work/PREREG-M5-C2-REV7.1.md         09d6f1b163ea0b84 / 16,313 B
  kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py
                                            88256d274c9993cc / 50,618 B
  docs/_work/PREREG-M5-C2-REV7.md           32eaf82ca56600c4 /  5,835 B
  run_m5c2_rev4.REV4_TEMPLATE               a6bc4f268f7711de
  out/M5C2-B5-GEN.json                      2b63a02463994c03 /  68,184 B
  out/M5C2-B5-SENTENCES.json                ba92635c8ad0c410 / 116,566 B
  out/M5C2-B5-GOLD.json                     54aa3da53c45da69 /  64,148 B
  tools/kvshim_vk.dll                       9edbafa150700614 / 50,007,552 B
  model                                     8,988,110,240 B

Layers (mirrors the frozen (b4) judge runner exactly, with rev7.1 as layer 2):
  0  empty source -> unsupported; deterministic abstain check (frozen regex)
  1  one independent extraction forward per sentence (frozen rev5.1 prompt),
     n_predict=384, greedy, engine reset before and after every single sentence
  2a rev5.1 archive: R51.judge_items + R5.derived_plus + rev5.1 aggregation
  2b rev7.1 verdict: R71.judge_row_rev7 (N1-N4 reused, never re-implemented)

Modes:
  --dry-run        static pins + split probe + layer0 prescan + rev7.1 API probe;
                   loads no model, writes no file, n_forward=0
  --split          re-split the frozen GEN and REQUIRE byte-identical equality
                   with out/M5C2-B5-SENTENCES.json (fail closed on mismatch)
  --gate-check     host gate only (no model); --allow-gui-procs enables the
                   {dwm, DSH NEXT} exception list, gate-check only (n_forward=0)
  --run            actual judging run -> out/M5C2-B5-JUDGE-REBUILD.json
  --rates-only     zero GPU; --gold <path> -> leak/false + Wilson 95% CI + H1
                   decision table + diagnostics, written back into the artifact

Gate: exceptions are recorded as {name,pid,exe_path,bytes,threshold,reason};
VRAM target <= 8.0 GiB, hard fuse 8.6 GiB.  No gold / no blind labels are read
by --run; question is only a prompt field, never an argument to a rule.

NO file outside out/M5C2-B5-JUDGE-REBUILD.json, out/_m5b5_judge_raw_rebuild.json,
out/M5C2-B5-HOSTGATE-REFUSED-REBUILD.json is written.  No git commit.
"""
import argparse
import ast
import ctypes
import hashlib
import json
import os
import random
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

import run_m5c2_rev4 as R4          # noqa: E402  frozen extraction prompt / abstain
import run_m5c2_rev4_1 as R41       # noqa: E402  strict 条目/依据 parser
import run_m5c2_rev5_offline as R5  # noqa: E402  derived_plus, window_coverage
import run_m5c2_rev5_1_offline as R51  # noqa: E402  rev5.1 rules (archive layer)
import run_m5c2_rev7_1_offline as R71  # noqa: E402  N1-N4 judge (reused, not copied)
import run_m5c2_rev2_order as CO    # noqa: E402  gate_with_dwm_exception
import run_m5c2_floor as F          # noqa: E402  VRAM sampler
import run_m5c2_r2 as R2            # noqa: E402  open_engine / host_gate
import _e3gpu_run as E              # noqa: E402  meta_from_log / ps / consts

# ---------------------------------------------------------------- pins ------
PRE_B5 = ROOT / "docs/_work/PREREG-M5-C2-B5.md"
PRE_B5_SHA16 = "d6c7bdac73ef7326"
PRE_B5_BYTES = 14597

PRE71 = ROOT / "docs/_work/PREREG-M5-C2-REV7.1.md"
PRE71_SHA16 = "09d6f1b163ea0b84"
PRE71_BYTES = 16313

CODE71 = M5 / "run_m5c2_rev7_1_offline.py"
CODE71_SHA16 = "88256d274c9993cc"
CODE71_BYTES = 50618

PRE_REV7 = ROOT / "docs/_work/PREREG-M5-C2-REV7.md"
PRE_REV7_SHA16 = "32eaf82ca56600c4"
PRE_REV7_BYTES = 5835

GEN = OUT / "M5C2-B5-GEN.json"
GEN_SHA16 = "2b63a02463994c03"
GEN_BYTES = 68184

SENT = OUT / "M5C2-B5-SENTENCES.json"
SENT_SHA16 = "ba92635c8ad0c410"
SENT_BYTES = 116566

GOLD = OUT / "M5C2-B5-GOLD.json"
GOLD_SHA16 = "54aa3da53c45da69"
GOLD_BYTES = 64148

PROMPT_SHA = "a6bc4f268f7711de"
JUDGE_VERSION = "rev7.1"
N_PREDICT = 384
TARGET_GIB = 8.0
FUSE_GIB = 8.6
LIMIT_S = 3600
DLL_SHA16 = "9edbafa150700614"
DLL_BYTES = 50007552
MODEL_BYTES = 8988110240

ART = OUT / "M5C2-B5-JUDGE-REBUILD.json"
RAW = OUT / "_m5b5_judge_raw_rebuild.json"
REFUSED = OUT / "M5C2-B5-HOSTGATE-REFUSED-REBUILD.json"

GPU_PROC_THRESHOLD = 268435456
GUI_ALLOWLIST = ("dwm", "DSH NEXT")
FREE_RAM_MIN_KB = 8388608
VRAM_BASELINE_MAX_GIB = 1.5

RATE_MIN_PER_RATE = 20
LEAK_MAX = 0.20
FALSE_MAX = 0.15
WILSON_Z = 1.96
BOOTSTRAP_SEED = 20261026
BOOTSTRAP_REPS = 10000

JUDGE_FUNCS = (
    "normalize7", "value_tokens", "token_kind_of_span", "matcher",
    "r1_r2_r3_rev7", "r4_plus_rev7", "verdict_v51", "baseline_reproduce",
    "judge_row_rev7", "pick_attribution", "rev7_causes", "char_evidence",
    "item_assertion", "verdict_assertion", "main", "verify_inputs",
)

SPLIT_RULES = ("PREREG-M5-C2-B5.md §4 (newline + 。！？; empty/问 echo/pure "
               "symbols dropped)")


# ------------------------------------------------------------- helpers ------
def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def die(msg, code=2):
    print(json.dumps({"status": "FAIL", "reason": msg}, ensure_ascii=False))
    raise SystemExit(code)


def pinned(path, sha, size, label):
    b = Path(path).read_bytes()
    if sha16(b) != sha or len(b) != size:
        die("%s pin mismatch: got %s/%d expected %s/%d"
            % (label, sha16(b), len(b), sha, size))
    return b


# ------------------------------------------------------------- verify ------
def verify_pins():
    """Every frozen input/pin is asserted; any drift is a fail-closed exit."""
    checks = {}
    pre = pinned(PRE_B5, PRE_B5_SHA16, PRE_B5_BYTES, "PREREG-M5-C2-B5.md")
    if b"frozen=true" not in pre or b"one_shot=true" not in pre:
        die("B5 prereg is not frozen/one_shot")
    checks["prereg_b5"] = {"sha16": PRE_B5_SHA16, "bytes": PRE_B5_BYTES,
                           "frozen": True, "one_shot": True}
    pinned(PRE71, PRE71_SHA16, PRE71_BYTES, "PREREG-M5-C2-REV7.1.md")
    checks["prereg_rev7_1"] = {"sha16": PRE71_SHA16, "bytes": PRE71_BYTES}
    pinned(CODE71, CODE71_SHA16, CODE71_BYTES, "run_m5c2_rev7_1_offline.py")
    checks["judge_code"] = {"sha16": CODE71_SHA16, "bytes": CODE71_BYTES,
                            "path": "kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py"}
    pinned(PRE_REV7, PRE_REV7_SHA16, PRE_REV7_BYTES, "PREREG-M5-C2-REV7.md")
    checks["supersedes"] = {"sha16": PRE_REV7_SHA16, "bytes": PRE_REV7_BYTES}
    if R71.SUPERSEDES_SHA16 != PRE_REV7_SHA16:
        die("rev7.1 SUPERSEDES_SHA16 does not match frozen rev7")
    if R71.CORRECTION_TYPE != "statement_correction":
        die("rev7.1 correction_type is not statement_correction")
    if R71.RULE_CODE_UNCHANGED is not True:
        die("rev7.1 RULE_CODE_UNCHANGED is not True")
    checks["rule_code_unchanged"] = True
    checks["correction_type"] = R71.CORRECTION_TYPE
    pinned(GEN, GEN_SHA16, GEN_BYTES, "M5C2-B5-GEN.json")
    checks["gen"] = {"sha16": GEN_SHA16, "bytes": GEN_BYTES}
    pinned(SENT, SENT_SHA16, SENT_BYTES, "M5C2-B5-SENTENCES.json")
    checks["sentences"] = {"sha16": SENT_SHA16, "bytes": SENT_BYTES}
    pinned(GOLD, GOLD_SHA16, GOLD_BYTES, "M5C2-B5-GOLD.json")
    checks["gold"] = {"sha16": GOLD_SHA16, "bytes": GOLD_BYTES}
    prompt_sha = sha16(R4.REV4_TEMPLATE.encode("utf-8"))
    if prompt_sha != PROMPT_SHA:
        die("frozen extraction prompt changed: %s" % prompt_sha)
    checks["extraction_prompt"] = {
        "sha16": prompt_sha, "source": "run_m5c2_rev4.REV4_TEMPLATE",
        "n_predict": N_PREDICT}
    dll = Path(E.VK)
    if not dll.exists() or sha16(dll.read_bytes()) != DLL_SHA16 \
            or dll.stat().st_size != DLL_BYTES:
        die("frozen dll pin mismatch: %s" % dll)
    checks["dll"] = {"sha16": DLL_SHA16, "bytes": DLL_BYTES,
                     "path": "tools/kvshim_vk.dll"}
    model = Path(E.MODEL)
    if not model.exists() or model.stat().st_size != MODEL_BYTES:
        die("frozen model size mismatch: %s" % model)
    checks["model"] = {"path": str(E.MODEL), "bytes": MODEL_BYTES}
    checks["judge_layer"] = {
        "version": JUDGE_VERSION, "prereg_sha16": PRE71_SHA16,
        "code_sha16": CODE71_SHA16, "supersedes_sha16": PRE_REV7_SHA16,
        "correction_type": R71.CORRECTION_TYPE,
        "rule_code_unchanged": True,
        "judge_functions_byte_identical_to_rev7": True,
        "imported_not_copied": True}
    return checks


def judge_function_identity():
    """Prove every judge function in rev7.1 is byte-identical to rev7."""
    a = CODE71.read_bytes().decode("utf-8")
    b = PRE_REV7.parent.parent.parent  # not used; kept explicit below
    rev7_code = M5 / "run_m5c2_rev7_offline.py"
    if not rev7_code.exists():
        return {"available": False,
                "reason": "run_m5c2_rev7_offline.py (C32) not present"}
    bsrc = rev7_code.read_bytes().decode("utf-8")
    ta, tb = ast.parse(a), ast.parse(bsrc)

    def slices(tree, src):
        out = {}
        lines = src.splitlines(keepends=True)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                out[node.name] = "".join(
                    lines[node.lineno - 1:node.end_lineno])
        return out

    sa, sb = slices(ta, a), slices(tb, bsrc)
    identical, differing, missing = [], [], []
    for name in JUDGE_FUNCS:
        if name in sa and name in sb:
            (identical if sa[name] == sb[name] else differing).append(name)
        else:
            missing.append({"name": name, "in_rev7_1": name in sa,
                            "in_rev7": name in sb})
    return {"available": True, "functions_checked": list(JUDGE_FUNCS),
            "functions_identical": identical, "functions_differing": differing,
            "functions_missing": missing,
            "n_identical": len(identical),
            "all_judge_functions_identical": not differing and not missing}


# -------------------------------------------------------------- split ------
def _split_pieces(answer):
    """PREREG-M5-C2-B5.md section 4, literally.

    per line (split by newline): split after 。！？ keeping the mark; strip the
    piece; drop empty pieces; drop pure punctuation/symbol pieces; drop 问：
    question-echo pieces; drop lone model think tags.
    """
    out = []
    for line in (answer or "").splitlines():
        buf = ""
        for ch in line:
            buf += ch
            if ch in "。！？":
                out.append(buf)
                buf = ""
        if buf.strip():
            out.append(buf)
    pieces = []
    for p in out:
        s = p.strip()
        if not s:
            continue
        if s.startswith("问：") or s.startswith("问:"):
            continue
        if re.match(r"^</?[A-Za-z][A-Za-z0-9_-]*>$", s):
            continue
        if not any(ch.isalnum() for ch in s):
            continue
        pieces.append(s)
    return pieces


def build_sentences(gen_obj, gen_bytes=None):
    """Re-split the frozen GEN; returns (artifact_obj, rows, split_stats)."""
    qa = gen_obj.get("qa") or []
    if len(qa) != 40:
        die("GEN must contain 40 qa rows, got %d" % len(qa))
    rows = []
    qids_without = []
    for q in qa:
        qid = q["qid"]
        pieces = _split_pieces(q.get("answer_full"))
        if not pieces:
            qids_without.append(qid)
        for i, text in enumerate(pieces, 1):
            rows.append({"sid": "%s-s%02d" % (qid, i), "qid": qid,
                         "scenario": q["scenario"],
                         "source_text": q["source_text"],
                         "question": q["question"], "text": text})
    obj = {
        "schema": "m5c2_b5_sentences_v1",
        "status": "已冻结切句（judge 前）",
        "prereg_sha16": PRE_B5_SHA16,
        "gen": {
            "path": "kvmem/m2_visibility/m5/out/M5C2-B5-GEN.json",
            "sha16": GEN_SHA16,
            "bytes": GEN_BYTES,
            "dll": gen_obj.get("dll", DLL_SHA16),
            "model_bytes": gen_obj.get("model_bytes", MODEL_BYTES),
            "n_gpu_layers_readback": gen_obj.get("n_gpu_layers_readback", 36),
        },
        "split_rules": SPLIT_RULES,
        "n_questions": len(qa),
        "n_sentences": len(rows),
        "sentences_nonempty": len(rows),
        "qids_without_sentences": qids_without,
        "judge_layer_prereg_sha16": PRE71_SHA16,
        "no_verdict": True,
        "no_gold": True,
        "sentences": rows,
    }
    stats = {"n_sentences": len(rows), "n_questions": len(qa),
             "qids_without_sentences": qids_without}
    return obj, rows, stats


def serialize(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def check_split():
    """Validate freshly split GEN against the frozen SENTENCES file."""
    gen_obj = json.loads(pinned(GEN, GEN_SHA16, GEN_BYTES,
                                "M5C2-B5-GEN.json").decode("utf-8"))
    obj, rows, stats = build_sentences(gen_obj)
    blob = serialize(obj)
    frozen = SENT.read_bytes()
    res = {
        "gen_sha16": GEN_SHA16,
        "frozen_sentences_sha16": SENT_SHA16,
        "rebuilt_sha16": sha16(blob),
        "rebuilt_bytes": len(blob),
        "byte_identical": blob == frozen,
        "n_sentences": len(rows),
        "n_questions": stats["n_questions"],
        "qids_without_sentences": stats["qids_without_sentences"],
    }
    if not res["byte_identical"]:
        # Fail closed: never overwrite the frozen sentence set.
        raise SystemExit(json.dumps(
            {"status": "FAIL", "reason": "re-split is not byte-identical to "
             "frozen M5C2-B5-SENTENCES.json; refusing to overwrite",
             **res}, ensure_ascii=False, indent=1))
    return res, obj, rows


# --------------------------------------------------------------- gate ------
def _ps_json(cmd):
    try:
        raw = "\n".join(E.ps(cmd))
    except Exception:  # noqa: BLE001
        return []
    raw = raw.strip()
    if not raw:
        return []
    try:
        v = json.loads(raw)
    except Exception:  # noqa: BLE001
        return []
    if isinstance(v, dict):
        return [v]
    return v if isinstance(v, list) else []


def _resolve_proc(name):
    """Best-effort pid/exe_path for one reported process name."""
    safe = name.replace("'", "''")
    items = _ps_json(
        "Get-Process -Name '%s' -ErrorAction SilentlyContinue | "
        "Select-Object Id,ProcessName,Path | ConvertTo-Json -Compress" % safe)
    if not items:
        return {"pid": None, "exe_path": None, "process_name": name}
    it = items[0]
    return {"pid": it.get("Id"), "exe_path": it.get("Path"),
            "process_name": it.get("ProcessName", name)}


def _parse_gpu_details(details):
    parsed = []
    for d in details or []:
        # NAME may contain spaces ("DSH NEXT"), so capture non-greedily.
        m = re.search(r"NAME=(.+?)\s+BYTES=(\d+)", str(d))
        if m:
            parsed.append((m.group(1), int(m.group(2))))
    return parsed


def host_gate(allow_gui, mode):
    """Host gate; GUI exceptions apply only to gate-check (n_forward == 0)."""
    g, base_exc = CO.gate_with_dwm_exception()
    exceptions = list(base_exc or [])
    applied = bool(base_exc)
    if not g.get("gate_ok") and allow_gui and mode == "gate-check":
        details = g.get("gpu_proc_details") or []
        parsed = _parse_gpu_details(details)
        count = int(g.get("gpu_procs_gt256mb") or 0)
        other_ok = all(bool(g.get(k)) for k in (
            "prereg_ok", "free_ram_ok", "vram_baseline_ok", "boot_id_ok",
            "dll_ok", "model_ok"))
        baseline_ok = float(g.get("vram_baseline_gib") or 999) <= \
            VRAM_BASELINE_MAX_GIB
        names_ok = bool(parsed) and all(
            n.lower() in [x.lower() for x in GUI_ALLOWLIST] for n, _ in parsed)
        if parsed and len(parsed) == count and count > 0 and names_ok \
                and other_ok and baseline_ok:
            exceptions = []
            for name, byt in parsed:
                info = _resolve_proc(name)
                exceptions.append({
                    "name": name,
                    "pid": info.get("pid"),
                    "exe_path": info.get("exe_path"),
                    "bytes": byt,
                    "threshold": GPU_PROC_THRESHOLD,
                    "reason": "GUI/host process in gate-check allowlist "
                              "{dwm, DSH NEXT}; not a compute workload",
                })
            g = dict(g)
            g["gate_ok_raw"] = g.get("gate_ok")
            g["gpu_procs_ok_raw"] = g.get("gpu_procs_ok")
            g["gate_ok"] = True
            g["gpu_procs_ok"] = True
            g["gate_exception_applied"] = True
            applied = True
    info = {
        "mode": mode,
        "allow_gui_procs": bool(allow_gui),
        "gui_allowlist": list(GUI_ALLOWLIST),
        "gui_allowlist_scope": "gate-check only (n_forward == 0)",
        "thresholds": {
            "gpu_proc_bytes": GPU_PROC_THRESHOLD,
            "free_ram_kb_min": FREE_RAM_MIN_KB,
            "vram_baseline_gib_max": VRAM_BASELINE_MAX_GIB,
            "vram_target_gib": TARGET_GIB,
            "vram_fuse_gib": FUSE_GIB,
        },
        "gate_ok": bool(g.get("gate_ok")),
        "exception_applied": applied,
        "gate_exceptions": exceptions,
    }
    return g, info


# ---------------------------------------------------------- layer0/layer2 ---
def layer0_route(source_text, sentence):
    """Layer-0 deterministic pre-check (frozen regex, no model)."""
    if not str(source_text).strip():
        return {"route": "empty_source", "verdict": "unsupported",
                "layer0": {"route": "empty_source"}}
    if re.search(R4.ABSTAIN_REGEX_EFFECTIVE, sentence):
        det = R4.deterministic_abstain(sentence, source_text)
        return {"route": "abstain_check", "verdict": det["verdict"],
                "layer0": det}
    return {"route": "model_extract", "verdict": None, "layer0": None}


def layer2_rev51(items, sentence, source):
    """Frozen rev5.1 layer 2 (archive only; rev7.1 is the reported verdict)."""
    items_new = R51.judge_items(items, source)
    en, dd = R5.derived_plus(sentence, source)
    if en:
        verdict = "undecidable"
    elif not items_new:
        verdict = "undecidable"
    elif any(z["absent"] for z in items_new):
        verdict = "unsupported"
    else:
        verdict = "supported"
    return items_new, dd, verdict


def judge_rev71(row_payload):
    """Reuse the frozen rev7.1 judge function verbatim (never re-implement)."""
    sent_rec, item_recs, dd = R71.judge_row_rev7(row_payload)
    return sent_rec, item_recs, dd


def build_prompt(row):
    return R4.REV4_TEMPLATE.format(
        source_text=row["source_text"], question=row.get("question", ""),
        sentence=row["text"])


# ------------------------------------------------------------- dry-run -----
def dry_run():
    pins = verify_pins()
    identity = judge_function_identity()
    split_res, _obj, rows = check_split()

    prompts = []
    for row in rows[:3]:
        p = build_prompt(row)
        prompts.append({"sid": row["sid"], "prompt_sha16": sha16(p.encode("utf-8")),
                        "prompt_chars": len(p)})

    layer0 = []
    for row in rows:
        r = layer0_route(row["source_text"], row["text"])
        if r["route"] != "model_extract":
            layer0.append({"sid": row["sid"], "route": r["route"],
                           "verdict": r["verdict"]})
    n_layer0 = len(layer0)

    # rev7.1 API probe on a synthetic row (never touches the corpus verdicts).
    probe_row = {
        "sid": "probe", "sentence": "工时费 320 元。",
        "source_text": "工时费 320 元，材料费 660 元。",
        "items": [{"item": "工时费 320 元", "evidence": "工时费 320 元。"}],
        "route": "model_extract", "parse_ok": True, "derived": False,
        "verdict": "supported", "layer0": None,
    }
    try:
        sent_rec, item_recs, _dd = judge_rev71(probe_row)
        api_probe = {"ok": True, "verdict_rev7": sent_rec["verdict_rev7"],
                     "n_items": len(item_recs),
                     "item_verdicts": [z["item_verdict"] for z in item_recs]}
    except Exception as exc:  # noqa: BLE001
        api_probe = {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}

    # rates helpers self-check (pure arithmetic, no artifact).
    rates_probe = {
        "wilson_0_of_0": R51.wilson(0, 0),
        "wilson_1_of_10": R51.wilson(1, 10),
        "rate_0_of_20": {"rate": 0.0},
        "thresholds": {"leak_max": LEAK_MAX, "false_max": FALSE_MAX,
                       "min_per_rate": RATE_MIN_PER_RATE},
    }

    out = {
        "schema": "m5c2_b5_judge_rebuild_dry_run_v1",
        "status": "dry_run_only",
        "judge_version": JUDGE_VERSION,
        "judge_artifact_target": "out/M5C2-B5-JUDGE-REBUILD.json",
        "pins": pins,
        "judge_function_identity": identity,
        "split_check": split_res,
        "n_sentences": len(rows),
        "n_predict": N_PREDICT,
        "prompt_template_sha16": PROMPT_SHA,
        "first_3_prompts": prompts,
        "layer0_pre_scan_n": n_layer0,
        "layer0_pre_scan": layer0,
        "rev7_1_api_probe": api_probe,
        "rates_probe": rates_probe,
        "n_forward": 0,
        "n_forward_planned": len(rows) - n_layer0,
        "no_gpu": True,
        "no_model_loaded": True,
        "writes": [],
        "gate": "not_checked_in_dry_run (use --gate-check)",
        "gate_exceptions_scope": "gate-check only (n_forward == 0)",
        "vram": {"target_gib": TARGET_GIB, "fuse_gib": FUSE_GIB},
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if (split_res["byte_identical"] and api_probe.get("ok")) else 2


# ---------------------------------------------------------- gate-check -----
def gate_check(allow_gui):
    pins = verify_pins()
    g, info = host_gate(allow_gui, "gate-check")
    payload = {
        "schema": "m5c2_b5_judge_gate_check_v1",
        "status": "gate_ok" if g.get("gate_ok") else "refused",
        "judge_version": JUDGE_VERSION,
        "prereg_sha16": PRE_B5_SHA16,
        "judge_prereg_sha16": PRE71_SHA16,
        "judge_code_sha16": CODE71_SHA16,
        "gate": g,
        "gate_info": info,
        "n_forward": 0,
        "one_shot_consumed": False,
        "rerun_allowed": bool(not g.get("gate_ok")),
        "pins_checked": {k: True for k in pins},
    }
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    if not g.get("gate_ok"):
        write_json_atomic(REFUSED, {
            "schema": "m5c2_b5_judge_gate_refused_v1",
            "status": "未接上",
            "reason": "host gate failed before any model load",
            "judge_version": JUDGE_VERSION,
            "gate": g,
            "gate_info": info,
            "gate_exceptions": info["gate_exceptions"],
            "n_forward": 0,
            "signals_sent": False,
            "no_model_loaded": True,
            "one_shot_consumed": False,
            "rerun_allowed": True,
            "no_auto_retry": True,
        })
        return 2
    return 0


# ---------------------------------------------------------------- run ------
def _tail_rates(rows):
    return {r["sid"]: r for r in rows}


def run_corpus(expected_prereg):
    if expected_prereg and expected_prereg != PRE_B5_SHA16:
        die("--expected-prereg-sha16 does not match frozen B5 prereg")
    pins = verify_pins()
    split_res, _obj, rows = check_split()

    if ART.exists():
        try:
            prev = json.loads(ART.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            prev = {}
        nfwd = int(prev.get("n_forward") or 0)
        if nfwd > 0 or prev.get("status") in ("已判未读数", "已读数"):
            die("judge artifact already exists with n_forward=%s; a completed "
                "judge run must not be overwritten (use --rates-only)" % nfwd)

    g0, info0 = host_gate(False, "run")
    if not g0.get("gate_ok"):
        write_json_atomic(REFUSED, {
            "schema": "m5c2_b5_judge_gate_refused_v1",
            "status": "未接上",
            "reason": "host gate failed before any model load",
            "judge_version": JUDGE_VERSION,
            "gate": g0,
            "gate_info": info0,
            "gate_exceptions": info0["gate_exceptions"],
            "n_forward": 0,
            "signals_sent": False,
            "no_model_loaded": True,
            "one_shot_consumed": False,
            "rerun_allowed": True,
            "no_auto_retry": True,
        })
        print(json.dumps({"status": "未接上", "reason": "host gate failed",
                          "n_forward": 0}, ensure_ascii=False))
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
        meta["frozen_dll_sha16"] = DLL_SHA16
        meta["n_predict"] = N_PREDICT
        for row in rows:
            if time.perf_counter() - t0 > LIMIT_S:
                aborted = "timeout >%ss" % LIMIT_S
                break
            try:
                peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
            except Exception:  # noqa: BLE001
                peak = None
            if peak is not None and peak > FUSE_GIB:
                aborted = "VRAM fuse: peak %.4f > %.1f GiB" % (peak, FUSE_GIB)
                break
            rec = {
                "sid": row["sid"], "qid": row["qid"],
                "scenario": row["scenario"],
                "source_text": row["source_text"], "question": row["question"],
                "sentence": row["text"], "route": None, "raw_out": None,
                "prompt_sha16": None, "parse_ok": False, "parse_reason": None,
                "layer0": None,
                "rev5_1": {"items": [], "rule_hits": [], "derived": False,
                           "derived_detail": {}, "verdict": None},
                "rev7_1": {"items": [], "verdict": None, "counts": {},
                           "derived": False, "derived_detail": {}},
            }
            l0 = layer0_route(row["source_text"], row["text"])
            if l0["route"] != "model_extract":
                rec["route"] = l0["route"]
                rec["layer0"] = l0["layer0"]
                rec["parse_ok"] = True
                rec["parse_reason"] = "layer0"
                rec["rev5_1"]["verdict"] = l0["verdict"]
                rec["rev7_1"]["verdict"] = l0["verdict"]
                rec["rev7_1"]["counts"] = {}
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
            rec["rc"] = rc
            items, parse_ok, reason = R41.parse_extraction(raw,
                                                           row["source_text"])
            rec["parse_ok"] = parse_ok
            rec["parse_reason"] = reason
            items51, dd51, verdict51 = layer2_rev51(items, row["text"],
                                                    row["source_text"])
            rec["rev5_1"] = {
                "items": items51,
                "rule_hits": [h for z in items51 for h in z["rule_hits"]],
                "derived": bool(dd51.get("enabled")),
                "derived_detail": dd51,
                "verdict": verdict51,
            }
            payload = {
                "sid": row["sid"], "sentence": row["text"],
                "source_text": row["source_text"],
                "items": [{"item": z["item"], "evidence": z["evidence"]}
                          for z in items],
                "route": "model_extract", "parse_ok": parse_ok,
                "derived": bool(dd51.get("enabled")), "verdict": verdict51,
                "layer0": None,
            }
            sent_rec, item_recs, dd71 = judge_rev71(payload)
            counts = {}
            for z in item_recs:
                counts[z["item_verdict"]] = counts.get(z["item_verdict"], 0) + 1
            rec["rev7_1"] = {
                "items": item_recs,
                "verdict": sent_rec["verdict_rev7"],
                "verdict_rev5_1": sent_rec["verdict_rev5_1"],
                "changed": sent_rec["changed"],
                "counts": counts,
                "n_items": sent_rec["n_items"],
                "n_valid": sent_rec["n_valid"],
                "n_invalid": sent_rec["n_invalid"],
                "n_absent": sent_rec["n_absent"],
                "n_unverified": sent_rec["n_unverified"],
                "derived": bool(sent_rec["derived_rev7"]),
                "derived_detail": dd71,
                "rule_hits": [h for z in item_recs for h in z["rule_hits"]],
            }
            results.append(rec)
            write_json_atomic(RAW, {"n_forward": forwards, "aborted": aborted,
                                    "results": results})

        g1, info1 = host_gate(False, "run-after")
        peak = F.stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 3)
        layer0_skipped = len([r for r in results
                              if r.get("layer0") is not None])
        abstain_sids = [r["sid"] for r in results
                        if r.get("route") == "abstain_check"]
        by_verdict = {}
        for r in results:
            v = r["rev7_1"]["verdict"]
            by_verdict[v] = by_verdict.get(v, 0) + 1
        out = {
            "schema": "m5c2_b5_judge_rebuild_v1",
            "status": "已判未读数" if aborted is None else "未接上",
            "judge_version": JUDGE_VERSION,
            "rebuild_of": "run_m5c2_b5_judge.py (lost/truncated; NOT imported)",
            "pins": pins,
            "prereg_sha16": PRE_B5_SHA16,
            "sentences_sha16": SENT_SHA16,
            "split_check": split_res,
            "judge_prereg_sha16": PRE71_SHA16,
            "judge_code_sha16": CODE71_SHA16,
            "supersedes_sha16": PRE_REV7_SHA16,
            "correction_type": R71.CORRECTION_TYPE,
            "rule_code_unchanged": True,
            "judge_function_identity": judge_function_identity(),
            "prompt_sha16": PROMPT_SHA,
            "actual_prompt_sha16": sha16(R4.REV4_TEMPLATE.encode("utf-8")),
            "prompt_matches_frozen": sha16(
                R4.REV4_TEMPLATE.encode("utf-8")) == PROMPT_SHA,
            "n_predict": N_PREDICT,
            "n_sentences": len(rows),
            "n_forward": forwards,
            "n_forward_planned": len(rows) - layer0_skipped,
            "n_forward_attempted": forwards,
            "layer0_skipped": layer0_skipped,
            "abstain_sids": abstain_sids,
            "aborted": aborted,
            "abort_class": None if aborted is None else "judge_aborted",
            "one_shot_consumed": True,
            "rerun_allowed": False,
            "elapsed": elapsed,
            "elapsed_s": elapsed,
            "peak_vram": peak,
            "peak_gib": peak,
            "target_gib": TARGET_GIB,
            "fuse_gib": FUSE_GIB,
            "engine_meta": meta,
            "gate_before": g0,
            "gate_info_before": info0,
            "gate_after": g1,
            "gate_info_after": info1,
            "gate_exceptions": info0["gate_exceptions"],
            "gate_exceptions_after": info1["gate_exceptions"],
            "gui_allowlist": {"names": list(GUI_ALLOWLIST),
                              "applies_to": "gate-check only (n_forward == 0)",
                              "used_in_run": False},
            "signals_sent": False,
            "no_parent_signals": True,
            "no_grammar": True,
            "no_model_switch": True,
            "no_prompt_changes": True,
            "no_rule_changes": True,
            "no_threshold_changes": True,
            "no_gold": True,
            "no_blind_labels_read": True,
            "question_in_prompt_only": True,
            "question_not_used_in_judge": True,
            "verdict_source": "R71.judge_row_rev7 (N1-N4, imported verbatim)",
            "verdict_distribution": dict(sorted(by_verdict.items())),
            "rates": None,
            "items": results,
        }
        write_json_atomic(ART, out)
        print(json.dumps({k: out[k] for k in (
            "status", "judge_version", "n_forward", "n_sentences", "elapsed",
            "peak_vram", "signals_sent", "gate_exceptions")},
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


# ----------------------------------------------------------- rates-only ----
def _load_gold(path):
    """Accept {"gold": {sid: state}} or the frozen GOLD artifact (labels[])."""
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(obj.get("gold"), dict):
        macro = obj["gold"]
        return {k: v for k, v in macro.items()}
    labels = obj.get("labels")
    if isinstance(labels, list) and labels and isinstance(labels[0], dict) \
            and "gold_label" in labels[0]:
        return {x["sid"]: x["gold_label"] for x in labels}
    die("gold file has neither {'gold':{sid:state}} nor labels[].gold_label")
    return {}


def _wilson(k, n, z=WILSON_Z):
    if n == 0:
        return [0.0, 0.0]
    p = k / float(n)
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(max(0.0, center - half), 6),
            round(min(1.0, center + half), 6)]


def _rate(k, n):
    return {"numerator": k, "denominator": n,
            "rate": round(k / n, 6) if n else None,
            "wilson95": _wilson(k, n)}


def _cluster_bootstrap(sids, is_case, scenario_of):
    """Scenario-cluster bootstrap CI for a proportion (sentence level)."""
    by_scen = {}
    for sid in sids:
        by_scen.setdefault(scenario_of[sid], []).append(is_case[sid])
    scens = sorted(by_scen)
    if not scens:
        return None
    rng = random.Random(BOOTSTRAP_SEED)
    reps = []
    for _ in range(BOOTSTRAP_REPS):
        k = 0
        n = 0
        for _s in scens:
            chosen = scens[rng.randrange(len(scens))]
            vals = by_scen[chosen]
            k += sum(1 for v in vals if v)
            n += len(vals)
        reps.append(k / float(n) if n else 0.0)
    reps.sort()
    return {"seed": BOOTSTRAP_SEED, "reps": BOOTSTRAP_REPS,
            "cluster": "scenario",
            "ci95_percentile": [round(reps[int(0.025 * len(reps))], 6),
                                round(reps[int(0.975 * len(reps)) - 1], 6)],
            "mean": round(sum(reps) / len(reps), 6)}


def rates_only(gold_path, judge_path):
    art_path = Path(judge_path) if judge_path else ART
    if not art_path.exists():
        die("judge artifact not found: %s" % art_path)
    art = json.loads(art_path.read_text(encoding="utf-8"))
    if art.get("status") not in ("已判未读数", "已读数") or not art.get("items"):
        die("judge artifact is not a completed judge run (status=%s)"
            % art.get("status"))
    items = art["items"]
    if len(items) != art.get("n_sentences"):
        die("artifact items length mismatch")
    gold = _load_gold(gold_path)
    judged = {r["sid"]: r["rev7_1"]["verdict"] for r in items}
    if set(gold) != set(judged):
        missing = sorted(set(gold) - set(judged))[:5]
        extra = sorted(set(judged) - set(gold))[:5]
        die("gold/judge sid mismatch: missing=%s extra=%s" % (missing, extra))

    support = [s for s in judged if gold[s] == "support_present"]
    fab = [s for s in judged if gold[s] == "fabricated"]
    others = [s for s in judged
              if gold[s] not in ("support_present", "fabricated")]
    false_sids = [s for s in support if judged[s] == "unsupported"]
    leak_sids = [s for s in fab if judged[s] in ("supported", "undecidable")]
    strict_leak = [s for s in fab if judged[s] == "supported"]
    any_non_supported = [s for s in support
                         if judged[s] in ("unsupported", "undecidable")]
    parse_fail = [s for s in judged if judged[s] == "parse_fail"]
    abstain_sids = list(art.get("abstain_sids") or [])
    derived_sids = [r["sid"] for r in items
                    if r["rev7_1"].get("derived")]
    invalid_items = sum(r["rev7_1"].get("n_invalid", 0) for r in items)
    unverified_items = sum(r["rev7_1"].get("n_unverified", 0) for r in items)
    n_items = sum(len(r["rev7_1"].get("items") or []) for r in items)

    # evidence verbatim, two calibers
    def _norm(s):
        return R71.normalize7(s)
    quoted = []
    for r in items:
        src = _norm(r["source_text"])
        for z in (r["rev7_1"].get("items") or []):
            ev = _norm(z.get("evidence"))
            if not ev:
                continue
            quoted.append((ev not in ("未提及", "未找到", "未记录")) and ev in src)
    ev_verbatim_quote = (round(sum(1 for q in quoted if q) / len(quoted), 6)
                         if quoted else None)
    ev_verbatim_all = (round(sum(1 for q in quoted if q) / n_items, 6)
                       if n_items else None)

    # false_by_reason (rev5.1 hits -> N1/N2/N3/N4/R4+/declared/other)
    by_reason = {}
    for s in set(false_sids) | set(leak_sids):
        rec = next(r for r in items if r["sid"] == s)
        hits = rec["rev5_1"].get("rule_hits") or []
        why = R71.pick_attribution(hits) if hits else "other"
        by_reason[why] = by_reason.get(why, 0) + 1

    # item 四态
    item_states = {"invalid": 0, "absent": 0, "unverified": 0, "present": 0}
    for r in items:
        for z in (r["rev7_1"].get("items") or []):
            item_states[z["item_verdict"]] = \
                item_states.get(z["item_verdict"], 0) + 1

    # coverage: sentences that were not excluded by layer 0
    coverage = {"n_sentences": len(items),
                "n_layer0_skipped": len(abstain_sids),
                "non_excluded": len(items) - len(abstain_sids),
                "rate": round((len(items) - len(abstain_sids)) / len(items), 6)
                if items else None}

    scenario_of = {r["sid"]: r["scenario"] for r in items}

    def _decision(false_r, leak_r):
        if false_r["denominator"] < RATE_MIN_PER_RATE \
                or leak_r["denominator"] < RATE_MIN_PER_RATE:
            return "未接上（样本量不足）"
        f_hi = false_r["wilson95"][1]
        l_hi = leak_r["wilson95"][1]
        if false_r["rate"] > FALSE_MAX:
            return "未通过"
        if leak_r["rate"] > LEAK_MAX:
            return "未通过（漏判越线）"
        if f_hi > FALSE_MAX or l_hi > LEAK_MAX:
            return "擦边"
        return "达标"

    false_rate = _rate(len(false_sids), len(support))
    leak_rate = _rate(len(leak_sids), len(fab))

    # question-level main readout (40 qids)
    qids = sorted({r["qid"] for r in items})
    qstats = {}
    for r in items:
        q = r["qid"]
        st = qstats.setdefault(q, {"support_present": 0, "fabricated": 0,
                                   "false": False, "leak": False,
                                   "any_invalid": False})
        g = gold.get(r["sid"])
        v = judged[r["sid"]]
        if g == "support_present":
            st["support_present"] += 1
            if v == "unsupported":
                st["false"] = True
        elif g == "fabricated":
            st["fabricated"] += 1
            if v in ("supported", "undecidable"):
                st["leak"] = True
        if (r["rev7_1"].get("n_invalid") or 0) > 0:
            st["any_invalid"] = True
    n_q_false = sum(1 for q in qids if qstats[q]["false"])
    n_q_leak = sum(1 for q in qids if qstats[q]["leak"])
    question_level = {
        "n_questions": len(qids),
        "false_questions": n_q_false,
        "leak_questions": n_q_leak,
        "false_rate": _rate(n_q_false, len(qids)),
        "leak_rate": _rate(n_q_leak, len(qids)),
        "note": "辅助读数；主判定仍为句子级两率（PREREG §6）",
    }

    boot_false = _cluster_bootstrap(
        [r["sid"] for r in items], {s: s in set(false_sids) for s in judged},
        scenario_of)
    boot_leak = _cluster_bootstrap(
        [r["sid"] for r in items], {s: s in set(leak_sids) for s in judged},
        scenario_of)

    rates = {
        "schema": "m5c2_b5_rates_v1",
        "gold_source": str(gold_path),
        "gold_sha16": sha16(Path(gold_path).read_bytes()),
        "judge_sha16": art.get("judge_code_sha16"),
        "judge_version": art.get("judge_version"),
        "n_sentences": len(items),
        "denominators": {
            "n_false_support_present": len(support),
            "n_leak_fabricated": len(fab),
            "n_other_gold": len(others),
            "n_other_gold_labels": sorted({gold[s] for s in others}),
            "min_per_rate": RATE_MIN_PER_RATE,
        },
        "false_positive": dict(false_rate, sids=sorted(false_sids),
                               threshold_max=FALSE_MAX),
        "leak_missed": dict(leak_rate, sids=sorted(leak_sids),
                            threshold_max=LEAK_MAX),
        "strict_leak_supported": {"k": len(strict_leak),
                                  "n": len(fab),
                                  "sids": sorted(strict_leak)},
        "any_non_supported_false": {"k": len(any_non_supported),
                                    "n": len(support),
                                    "sids": sorted(any_non_supported)},
        "parse_fail": {"k": len(parse_fail), "n": len(items),
                       "rate": round(len(parse_fail) / len(items), 6)
                       if items else None,
                       "sids": sorted(parse_fail)},
        "abstain": {"n": len(abstain_sids), "sids": abstain_sids,
                    "gold_mix": {g: sum(1 for s in abstain_sids
                                        if gold.get(s) == g)
                                 for g in sorted({gold.get(s)
                                                  for s in abstain_sids})}
                    if abstain_sids else {}},
        "derived": {"n": len(derived_sids), "sids": derived_sids,
                    "gold_mix": {g: sum(1 for s in derived_sids
                                        if gold.get(s) == g)
                                 for g in sorted({gold.get(s)
                                                  for s in derived_sids})}
                    if derived_sids else {}},
        "evidence_verbatim": {
            "quote_bearing_rate": ev_verbatim_quote,
            "all_items_rate": ev_verbatim_all,
            "n_quote_bearing_items": len(quoted),
            "n_items": n_items,
            "rule": "normalize7(evidence) substring of normalize7(source); "
                    "非 未提及/未找到/未记录 才算 quote-bearing",
            "diagnostic_only": True,
        },
        "items": {
            "n_items": n_items,
            "n_invalid": invalid_items,
            "n_unverified": unverified_items,
            "unverified_ratio": round(unverified_items / n_items, 6)
            if n_items else None,
            "unverified_warn_over_15pct": bool(
                n_items and unverified_items / n_items > 0.15),
            "states": item_states,
        },
        "false_by_reason": {"counts": dict(sorted(by_reason.items())),
                            "rule": "R71.pick_attribution(rev5.1 stored hits) "
                                    "on FP+leak sentences",
                            "buckets": ["N1", "N2", "N3", "N4", "R4+",
                                        "declared", "other"]},
        "coverage": coverage,
        "question_level": question_level,
        "cluster_bootstrap": {"false_positive": boot_false,
                              "leak_missed": boot_leak,
                              "note": "scenario cluster, seed/reps frozen in "
                                      "RUN-PLAN rate_readout.extra_diagnostics"},
        "thresholds": {"leak_max": LEAK_MAX, "false_max": FALSE_MAX,
                       "z": WILSON_Z, "ci": "95%"},
        "h1": "误判<=15% 且 漏判<=20%（两率同时满足）；CI 上界越线记擦边",
        "decision": _decision(false_rate, leak_rate),
        "decision_table": {
            "达标": "两率点估计与 CI 上界均达标 -> 进 (b6) 复验，不得单次宣称能力",
            "擦边": "点估计达标但 CI 上界越线 -> 进 (b6)",
            "未通过": "误判 >15% -> 禁止在 (b5) 上调参",
            "未通过（漏判越线）": "误判达标但漏判 >20% -> 两种错误不可互相抵消",
            "未接上（样本量不足）": "任一率分母 <20 -> 记未接上，不得当作通过",
        },
        "judge_verdict_order": ("empty_source→unsupported; abstain→layer0; "
                                "parse_fail; derived→undecidable; 无条目→"
                                "undecidable; 任一 absent→unsupported; else "
                                "supported"),
        "no_rule_change_after_readout": True,
    }
    art["rates"] = rates
    if art.get("status") == "已判未读数":
        art["status"] = "已读数"
    art.setdefault("rates_readout", {})["schema"] = "m5c2_b5_rates_v1"
    art["rates_readout"]["decision"] = rates["decision"]
    write_json_atomic(art_path, art)
    print(json.dumps({
        "status": "已读数",
        "artifact": str(art_path),
        "artifact_sha16": sha16(art_path.read_bytes()),
        "false": rates["false_positive"]["rate"],
        "false_n": [rates["false_positive"]["k"],
                    rates["false_positive"]["denominator"]],
        "leak": rates["leak_missed"]["rate"],
        "leak_n": [rates["leak_missed"]["k"],
                   rates["leak_missed"]["denominator"]],
        "decision": rates["decision"],
    }, ensure_ascii=False, indent=1))
    return 0


# ---------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--split", action="store_true")
    ap.add_argument("--gate-check", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--rates-only", action="store_true")
    ap.add_argument("--gold", default=None)
    ap.add_argument("--judge", default=None,
                    help="rates-only debug: judge artifact path override")
    ap.add_argument("--expected-prereg-sha16", default=None)
    ap.add_argument("--allow-gui-procs", action="store_true",
                    help="gate-check only: allow {dwm, DSH NEXT} GPU procs")
    a = ap.parse_args()
    modes = [a.dry_run, a.split, a.gate_check, a.run, a.rates_only]
    if sum(1 for m in modes if m) != 1:
        print("choose exactly one of --dry-run/--split/--gate-check/--run/"
              "--rates-only")
        return 2
    if a.dry_run:
        return dry_run()
    if a.split:
        res, _obj, _rows = check_split()
        print(json.dumps({"status": "split_frozen_byte_identical", **res},
                         ensure_ascii=False, indent=1))
        return 0
    if a.gate_check:
        return gate_check(a.allow_gui_procs)
    if a.run:
        return run_corpus(a.expected_prereg_sha16)
    if a.rates_only:
        if not a.gold:
            die("--rates-only requires --gold <path>")
        return rates_only(a.gold, a.judge)
    return 2


if __name__ == "__main__":
    sys.exit(main())