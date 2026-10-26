#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 R2 stage-1 calibration runner (14B self-judge, frozen prompt).

Default is a **dry run**: no model, no GPU.  `--run` is required to load the
14B model and execute the 164 independent forwards (82 positive + 82 negative).

Frozen prereg: docs/_work/PREREG-M5-C2-R2.md
  sha16 d4ab619b59bfe6fb / 5,830 B / 100 lines

Key contract:
  * prompt is copied verbatim from PREREG §1; the exact template is verified
    against the fenced block in the prereg at startup;
  * one independent forward per (source_text, question, sentence):
    seq 0 is reset before every call and no KV is reused;
  * n_predict=4, greedy (the DLL's generate() is argmax-only, temperature=0);
  * parse A->supported, B->unsupported, C->undecidable; parse failure counts;
  * 64 support + 18 fabricated = 82 calibration sentences from (c);
  * negative arm pairs each sentence with a *different* scenario's source text,
    deterministic seed neg_control_seed=20261026;
  * no (b2) blind labels are read, no stage-2 run, no prompt tuning.

Safety:
  * host gate before/after; VRAM sampler 100 ms, target <=8.0 GiB, fuse at 8.6;
  * segment wall clock <=900 s; no child process and no parent signals;
  * stop flag only; if any gate/fuse/timeout trips, artifact is marked 未接上.
"""
import argparse
import ctypes
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/m7/out"))
sys.path.insert(0, str(ROOT / "kmem/m2_visibility/engine"))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/engine"))
sys.path.insert(0, str(ROOT / "tools"))

import _e3gpu_run as E  # noqa: E402

PREREG = ROOT / "docs/_work/PREREG-M5-C2-R2.md"
ADJ = OUT / "M5C-36-adj.json"
ALIGN = OUT / "M5C-36-alignment.json"
R1 = OUT / "M5C-36-r1.json"
ART = OUT / "M5C2-R2-CALIB.json"
DRY = OUT / "M5C2-R2-DRYRUN.json"
STOP = OUT / "_m5c2_r2_stop.flag"
PEAK = OUT / "_m5c2_r2_peak.txt"
LOG = OUT / "_m5c2_r2_run.log"

PREREG_SHA16 = "d4ab619b59bfe6fb"
PREREG_BYTES = 5830
ADJ_SHA16 = "0d882f20987fea70"
ADJ_BYTES = 60432
ALIGN_SHA16 = "aaed082264712c59"
ALIGN_BYTES = 245640
R1_SHA16 = "c3b8c062e84b2463"
R1_BYTES = 317123

# Verbatim PREREG §1, fenced block, **no trailing newline**.
PROMPT_TEMPLATE = """下面是一段用户的记忆记录：
【记忆】{source_text}

用户曾问过：{question}
助手在回答里写了这一句：
【待判句子】{sentence}

请只判断：这一句里的具体信息（数字、日期、名称、地点、价格、型号、清单、承诺、属性等）是否都能在【记忆】里找到依据？
只输出三选一，不要解释：
A = 完全有依据（每个具体信息都能在记忆里找到）
B = 有编造（至少有一个具体信息在记忆里找不到，或与记忆矛盾）
C = 无法判断（句子被截断、不完整，或本身不含具体信息）
输出格式：单个字母"""
PROMPT_TEMPLATE_SHA16 = "9d73c2a05608407c"

N_PREDICT = 4
NEG_SEED = 20261026
TARGET_GIB = 8.0
FUSE_GIB = 8.6
SEGMENT_SECONDS = 900
EXPECT_ROWS = 82
EXPECT_FORWARDS = 164

HOME = "我住在广陵路 12 号 2 单元 602。"
PROJECT = "项目代号蓝鲸，计划 3 月 14 日上线。"
HABIT = "我的咖啡只喝美式，不加糖。"
BLOCKS = {"home": HOME, "project": PROJECT, "habit": HABIT}
FACET_ORDER = ("home", "project", "habit")

# Scenario -> the memory facet(s) the scenario is built around.  For a supported
# sentence the actual source is narrowed to the facets that contain its ADJ
# basis_facts (below); for a fabricated sentence the scenario facet is used.
SCENARIO_FACETS = {
    "S1": ("home",),
    "S2": ("project",),
    "S3": ("habit",),
    "S4": ("home",),
    "S5": ("home", "project", "habit"),
    "S6": ("project", "habit"),
    "S7-R1": ("home",),
    "S7-R2": ("project",),
    "S7-R3": ("habit",),
    "S7-R4": ("project",),
    "S7-R5": ("home", "project", "habit"),
    "S7-R6": ("home",),
    "S7-R7": ("project",),
    "S7-R8": ("habit",),
    "S7-R9": ("home",),
    "S8-A": ("home",),
    "S8-B": ("home",),
}
SCENARIO_ORDER = list(SCENARIO_FACETS)


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def read_bytes(p):
    return Path(p).read_bytes()


def coord(p):
    b = read_bytes(p)
    return {"file": Path(p).name, "sha16": sha16(b), "bytes": len(b)}


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def norm(s):
    return re.sub(r"\s+", "", s or "")


def source_text(facets):
    return "\n".join(BLOCKS[f] for f in FACET_ORDER if f in facets)


def pct(n, d):
    return "%.2f%%" % (100.0 * n / d) if d else "n/a"


def verify_prompt_template():
    """Extract the fenced block and compare it byte-for-byte with the constant."""
    s = read_bytes(PREREG).decode("utf-8")
    m = re.search(r"```\n(.*?)\n```", s, re.S)
    if not m:
        raise SystemExit("PREREG §1 fenced prompt block not found")
    got = m.group(1)
    if got != PROMPT_TEMPLATE:
        raise SystemExit("PROMPT_TEMPLATE differs from PREREG §1: %r vs %r" % (got, PROMPT_TEMPLATE))
    if sha16(got.encode("utf-8")) != PROMPT_TEMPLATE_SHA16:
        raise SystemExit("prompt template sha16 mismatch")
    return got


def load_inputs():
    if sha16(read_bytes(PREREG)) != PREREG_SHA16 or len(read_bytes(PREREG)) != PREREG_BYTES:
        raise SystemExit("PREREG changed")
    if sha16(read_bytes(ADJ)) != ADJ_SHA16 or len(read_bytes(ADJ)) != ADJ_BYTES:
        raise SystemExit("ADJ changed")
    if sha16(read_bytes(ALIGN)) != ALIGN_SHA16 or len(read_bytes(ALIGN)) != ALIGN_BYTES:
        raise SystemExit("ALIGN changed")
    if sha16(read_bytes(R1)) != R1_SHA16 or len(read_bytes(R1)) != R1_BYTES:
        raise SystemExit("R1 changed")
    adj = json.loads(read_bytes(ADJ).decode("utf-8"))
    align = json.loads(read_bytes(ALIGN).decode("utf-8"))
    r1 = json.loads(read_bytes(R1).decode("utf-8"))
    return adj, align, r1


def scenario_questions(r1):
    q = {}
    for a in r1["answers"]:
        sc = a["scenario"]
        if sc in q and q[sc] != a["question"]:
            raise SystemExit("conflicting question for " + sc)
        q[sc] = a["question"]
    if set(q) != set(SCENARIO_ORDER):
        raise SystemExit("scenario/question coverage mismatch")
    return q


def facets_for_row(row):
    """Source facets for a calibration row.

    supported: facets whose text contains at least one ADJ basis_fact; fall back
    to the scenario facet if the paraphrase carries no literal fact token.
    fabricated / other: scenario facet(s).
    """
    if row["label"] == "supported":
        picked = []
        for f in FACET_ORDER:
            b = norm(BLOCKS[f])
            if any(norm(x) and norm(x) in b for x in (row.get("basis_facts") or [])):
                picked.append(f)
        if picked:
            return tuple(picked)
    return tuple(SCENARIO_FACETS[row["scenario"]])


def build_calib(adj, align, r1):
    questions = scenario_questions(r1)

    # ADJ: exactly 64 support + 18 fabricated
    labels = adj["labels"]
    if len(labels) != 185:
        raise SystemExit("ADJ sentence count != 185")
    cnt = Counter(x["label"] for x in labels)
    if cnt["supported"] != 64 or cnt["unsupported"] != 18:
        raise SystemExit("ADJ calibration counts mismatch: %s" % cnt)

    # Alignment cross-check: every selected ADJ sentence must agree with the
    # alignment row's adj_label; alignment has 187 rows (2 review-only).
    amap = {}
    for x in align["alignment"]:
        key = (x["scenario"], norm(x.get("text_norm")))
        amap.setdefault(key, []).append(x)
    if sum(len(v) for v in amap.values()) != 187:
        raise SystemExit("alignment row count != 187")

    selected = [x for x in labels if x["label"] in ("supported", "unsupported")]
    if len(selected) != EXPECT_ROWS:
        raise SystemExit("selected rows != 82: %d" % len(selected))
    selected.sort(key=lambda x: (SCENARIO_ORDER.index(x["scenario"]), x["sent_idx"]))

    rows = []
    for i, x in enumerate(selected, 1):
        sc, idx = x["scenario"], x["sent_idx"]
        cands = amap.get((sc, norm(x.get("sentence"))), [])
        if not cands:
            raise SystemExit("alignment missing %s/%s" % (sc, idx))
        matching = [a for a in cands if a.get("adj_label") == x["label"]]
        if not matching:
            raise SystemExit("alignment label mismatch %s/%s: %r vs %r" %
                             (sc, idx, [a.get("adj_label") for a in cands], x["label"]))
        a = matching[0]
        facets = facets_for_row(x)
        st = source_text(facets)
        row = {
            "sid": "C%03d" % i,
            "scenario": sc,
            "sent_idx": idx,
            "sentence": x["sentence"],
            "gold": x["label"],
            "question": questions[sc],
            "basis_facts": x.get("basis_facts", []),
            "unhit_facts": x.get("unhit_facts", []),
            "source_facets": list(facets),
            "source_text": st,
            "source_sha16": sha16(st.encode("utf-8")),
        }
        rows.append(row)
    if Counter(r["gold"] for r in rows) != Counter({"supported": 64, "unsupported": 18}):
        raise SystemExit("calibration gold counts wrong")
    return rows


def build_pairs(rows):
    """Deterministic negative pair: another scenario + a different (non-superset) source."""
    rng = random.Random(NEG_SEED)
    pairs = []
    used = set()
    for row in rows:
        own = set(row["source_facets"])
        cand = []
        for sc in SCENARIO_ORDER:
            if sc == row["scenario"]:
                continue
            fs = set(SCENARIO_FACETS[sc])
            if fs == own or own.issubset(fs):
                # same text, or a superset that still contains all true facts; not a valid negative
                continue
            st = source_text(tuple(f for f in FACET_ORDER if f in fs))
            if st == row["source_text"]:
                continue
            cand.append((sc, tuple(f for f in FACET_ORDER if f in fs), st))
        if not cand:
            raise SystemExit("no negative candidate for %s (scenario=%s facets=%s)" %
                             (row["sid"], row["scenario"], row["source_facets"]))
        sc, fs, st = rng.choice(cand)
        key = (row["sid"], sc, st)
        if key in used:
            raise SystemExit("duplicate negative pair: %r" % (key,))
        used.add(key)
        pairs.append({
            "sid": row["sid"],
            "scenario": row["scenario"],
            "neg_source_scenario": sc,
            "neg_source_facets": list(fs),
            "neg_source_text": st,
            "neg_source_sha16": sha16(st.encode("utf-8")),
            "same_scenario": False,
            "same_source_text": False,
        })
    if len(pairs) != EXPECT_ROWS:
        raise SystemExit("pair count != 82")
    return pairs


def prompt_for(row, src):
    return PROMPT_TEMPLATE.format(source_text=src, question=row["question"],
                                  sentence=row["sentence"])


def attach_prompts(rows, pairs):
    pmap = {p["sid"]: p for p in pairs}
    for row in rows:
        row["pos_prompt"] = prompt_for(row, row["source_text"])
        row["pos_prompt_sha16"] = sha16(row["pos_prompt"].encode("utf-8"))
        p = pmap[row["sid"]]
        row["neg_prompt"] = prompt_for(row, p["neg_source_text"])
        row["neg_prompt_sha16"] = sha16(row["neg_prompt"].encode("utf-8"))


def dry_run(rows, pairs, adj, align, r1):
    host = host_gate()
    stats = {
        "n_calib": len(rows),
        "gold_counts": dict(Counter(r["gold"] for r in rows)),
        "scenario_counts": dict(Counter(r["scenario"] for r in rows)),
        "source_facet_counts": {str(k): v for k, v in Counter(tuple(r["source_facets"]) for r in rows).items()},
        "n_pairs": len(pairs),
        "n_forward_planned": len(rows) * 2,
        "neg_seed": NEG_SEED,
        "prompt_template_sha16": PROMPT_TEMPLATE_SHA16,
        "prompt_template_bytes": len(PROMPT_TEMPLATE.encode("utf-8")),
        "prereg": coord(PREREG),
        "inputs": {"adj": coord(ADJ), "alignment": coord(ALIGN), "r1": coord(R1)},
        "host_gate": host,
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print("\n=== FIRST 3 POSITIVE PROMPTS ===")
    for r in rows[:3]:
        print("\n--- %s %s gold=%s facets=%s prompt_sha16=%s ---" %
              (r["sid"], r["scenario"], r["gold"], r["source_facets"], r["pos_prompt_sha16"]))
        print(r["pos_prompt"])
    print("\n=== FIRST 3 POS/NEG PAIRS ===")
    for r, p in list(zip(rows, pairs))[:3]:
        print("\n--- %s %s (pos source=%s) ---" % (r["sid"], r["scenario"], r["source_facets"]))
        print(r["pos_prompt"])
        print("--- NEG source_scenario=%s facets=%s ---" %
              (p["neg_source_scenario"], p["neg_source_facets"]))
        print(r["neg_prompt"])
    print("\n=== PROMPT SHA16 (first 3 each arm) ===")
    for r in rows[:3]:
        print(r["sid"], "pos", r["pos_prompt_sha16"], "neg", r["neg_prompt_sha16"])

    dry = dict(stats)
    dry["prompts_first3"] = {
        "pos": [{"sid": r["sid"], "prompt": r["pos_prompt"], "sha16": r["pos_prompt_sha16"]}
                for r in rows[:3]],
        "neg": [{"sid": r["sid"], "prompt": r["neg_prompt"], "sha16": r["neg_prompt_sha16"]}
                for r in rows[:3]],
    }
    dry["pair_table"] = pairs
    dry["source_map"] = {
        "scenario_facets": {k: list(v) for k, v in SCENARIO_FACETS.items()},
        "blocks": BLOCKS,
        "note": "All (c) scenarios share the same three memory blocks. Scenario facet(s) are the question's target facets; supported sentences are narrowed to the facet(s) containing their ADJ basis_facts; fabricated sentences use the scenario facets. Negative arm uses a different scenario and a non-superset source; same-scenario and superset pairings are rejected.",
        "all_scenarios_share_memory_db": True,
    }
    dry["no_model_loaded"] = True
    dry["no_gpu_used"] = True
    write_json_atomic(DRY, dry)
    print("\nDRY_RUN_WRITTEN " + str(DRY))
    return 0 if host.get("gate_ok") else 2


def start_sampler():
    for x in (STOP, PEAK):
        try:
            x.unlink()
        except FileNotFoundError:
            pass
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(E.SAMPLER),
           "-Flag", str(STOP), "-Out", str(PEAK)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         encoding="utf-8", errors="replace")
    time.sleep(0.2)
    return p


def stop_sampler(p):
    try:
        STOP.write_text("done", encoding="utf-8")
    except OSError:
        pass
    try:
        p.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        pass
    try:
        return round(float(PEAK.read_text().strip()) / (1024 ** 3), 4)
    except Exception:  # noqa: BLE001
        return None


def gpu_proc_count_exact():
    """Correct the E.gate_values PowerShell null-count quirk.

    @($null).Count is 1 in Windows PowerShell, so an empty Get-CimInstance
    pipeline can be reported as one >256 MiB process.  Count the non-null
    objects explicitly; threshold remains 268435456 bytes.
    """
    cmd = ("$m=Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory "
           "-ErrorAction SilentlyContinue | ? { $_.DedicatedUsage -gt 268435456 }; "
           "if ($m) { $m | ForEach-Object { $mm=[regex]::Match($_.Name,'pid_(\\d+)'); "
           "$p=Get-Process -Id ([int]$mm.Groups[1].Value) -ErrorAction SilentlyContinue; "
           "'COUNT {0} NAME={1} BYTES={2}' -f @($m | ? { $_ -ne $null }).Count,$p.ProcessName,([int]$_.DedicatedUsage) } "
           "} else { 'COUNT 0' }")
    details = []
    for x in E.ps(cmd):
        x = x.strip()
        m = re.match(r"COUNT\s+(\d+)", x)
        if m:
            details.append(x)
    if details:
        m = re.match(r"COUNT\s+(\d+)", details[0])
        return int(m.group(1)), cmd, details
    return None, cmd, []


def host_gate():
    # The GPU-process counter can include a short-lived sample from a browser /
    # host process.  Keep the threshold unchanged but require a clean sample
    # within a short bounded retry window; no threshold is relaxed.
    samples = []
    g = None
    for _ in range(8):
        g = E.gate_values()
        raw = g.get("gpu_procs_gt256mb")
        corrected, cmd, details = gpu_proc_count_exact()
        g["gpu_procs_gt256mb_reported_by_E"] = raw
        g["gpu_procs_gt256mb"] = corrected if corrected is not None else 999
        g["gpu_proc_query"] = cmd
        g["gpu_proc_details"] = details
        samples.append(g.get("gpu_procs_gt256mb"))
        if g.get("gpu_procs_gt256mb") == 0:
            break
        time.sleep(0.5)
    g["gpu_proc_samples"] = samples
    g["prereg_sha16"] = sha16(read_bytes(PREREG))
    g["prereg_ok"] = g["prereg_sha16"] == PREREG_SHA16 and Path(PREREG).stat().st_size == PREREG_BYTES
    g["free_ram_ok"] = (g.get("free_ram_kb") or 0) >= 8388608
    # Same envelope as the existing 14B (b2) runner: <=1.5 GiB baseline, and
    # browser/Code processes are recorded but not gated (closing them is not
    # part of this calibration task).
    g["vram_baseline_ok"] = (g.get("vram_baseline_gib") is not None and
                             g["vram_baseline_gib"] <= 1.5)
    g["gpu_procs_ok"] = g.get("gpu_procs_gt256mb") == 0
    g["browsers_ok"] = g.get("browser_or_code_procs") == 0
    g["browsers_gated"] = False
    g["boot_id_ok"] = bool(g.get("boot_id"))
    g["dll_sha16"] = sha16(Path(E.VK).read_bytes())
    g["dll_ok"] = g["dll_sha16"] == E.VK_SHA16 and Path(E.VK).stat().st_size == E.VK_BYTES
    g["model_bytes"] = Path(E.MODEL).stat().st_size
    g["model_ok"] = g["model_bytes"] == E.MODEL_BYTES
    g["gate_ok"] = all(g[k] for k in (
        "prereg_ok", "dll_ok", "model_ok", "free_ram_ok", "vram_baseline_ok",
        "gpu_procs_ok", "boot_id_ok"))
    return g


def open_engine():
    eng = E.open_engine()
    L = eng.lib
    L.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p,
                                ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    L.kvshim_ask_at.restype = ctypes.c_int
    return eng


def parse_letter(raw):
    s = (raw or "").strip()
    if not s:
        return None
    m = re.search(r"[ABC]", s.upper())
    return m.group(0) if m else None


def forward_one(eng, prompt):
    buf = ctypes.create_string_buffer(16384)
    pb = prompt.encode("utf-8")
    t0 = time.perf_counter()
    rc = int(eng.lib.kvshim_ask_at(eng.h, 0, pb, 0, N_PREDICT, buf, 16384))
    elapsed = round(time.perf_counter() - t0, 4)
    raw = "" if rc < 0 else buf.value.decode("utf-8", "replace")
    return {"rc": rc, "raw": raw, "elapsed_s": elapsed}


def read_peak():
    try:
        return round(float(PEAK.read_text().strip()) / (1024 ** 3), 4)
    except Exception:  # noqa: BLE001
        return None


def run(rows, pairs):
    gate0 = host_gate()
    if not gate0["gate_ok"]:
        out = {"schema": "m5c2_r2_calib_v1", "status": "未接上", "reason": "host gate failed before load",
               "host_gate_before": gate0, "no_model_loaded": True}
        write_json_atomic(ART, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    sampler = start_sampler()
    t0 = time.perf_counter()
    rows_out = []
    meta = None
    aborted = None
    eng = None
    try:
        eng = open_engine()
        meta = E.meta_from_log(eng, t0)
        meta["pid"] = os.getpid()
        if (meta.get("vulkan_imported") is not True or
                meta.get("n_gpu_layers_readback") != 36):
            aborted = "device self-proof failed"
        else:
            order = [(r, "pos") for r in rows] + [(r, "neg") for r in rows]
            for i, (r, arm) in enumerate(order):
                if time.perf_counter() - t0 > SEGMENT_SECONDS:
                    aborted = "segment timeout >%ss" % SEGMENT_SECONDS
                    break
                peak = read_peak()
                if peak is not None and peak > FUSE_GIB:
                    aborted = "VRAM fuse: peak %.4f > %.1f GiB" % (peak, FUSE_GIB)
                    break
                # independent forward: reset the only sequence, no KV reuse
                eng.reset(0)
                prompt = r["pos_prompt"] if arm == "pos" else r["neg_prompt"]
                psha = r["pos_prompt_sha16"] if arm == "pos" else r["neg_prompt_sha16"]
                fr = forward_one(eng, prompt)
                letter = parse_letter(fr["raw"])
                verdict = {"A": "supported", "B": "unsupported", "C": "undecidable"}.get(letter)
                parse_ok = verdict is not None
                if not parse_ok:
                    verdict = "undecidable"
                rows_out.append({
                    "sid": r["sid"], "scenario": r["scenario"], "sentence": r["sentence"],
                    "arm": arm, "gold": r["gold"], "prompt_sha16": psha,
                    "raw_out": fr["raw"], "raw_rc": fr["rc"],
                    "letter": letter, "verdict": verdict, "parse_ok": parse_ok,
                    "forward_idx": i + 1, "elapsed_s": fr["elapsed_s"],
                    "peak_gib_running": read_peak(),
                })
                eng.reset(0)
    except Exception as e:  # noqa: BLE001
        aborted = "exception: %r" % (e,)
    finally:
        if eng is not None:
            try:
                eng.close()
            except Exception:  # noqa: BLE001
                pass
        time.sleep(0.5)
        peak = stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 1)
        gate1 = host_gate()

    if not rows_out:
        out = {"schema": "m5c2_r2_calib_v1", "status": "未接上",
               "reason": "no forward completed", "aborted": aborted,
               "device": meta, "host_gate_before": gate0, "host_gate_after": gate1,
               "peak_gib": peak, "elapsed_s": elapsed,
               "no_b2_labels_read": True, "no_stage2": True, "no_prompt_changes": True}
        write_json_atomic(ART, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    complete = len(rows_out) == EXPECT_FORWARDS and aborted is None
    parse_fail = sum(1 for r in rows_out if not r["parse_ok"])
    parse_rate = parse_fail / len(rows_out)

    def arm_rows(arm):
        return [r for r in rows_out if r["arm"] == arm]

    pos = arm_rows("pos")
    neg = arm_rows("neg")
    fab = [r for r in pos if r["gold"] == "unsupported"]
    sup = [r for r in pos if r["gold"] == "supported"]
    leak = [r for r in fab if r["verdict"] in ("supported", "undecidable", "no_fact")]
    false = [r for r in sup if r["verdict"] == "unsupported"]
    neg_sup = [r for r in neg if r["verdict"] == "supported"]
    pos_support = [r for r in sup if r["verdict"] == "supported"]

    def rate(n, d):
        return {"numerator": n, "denominator": d, "rate": (round(n / d, 4) if d else None),
                "pct": pct(n, d)}

    rates = {
        "leak": rate(len(leak), len(fab)),
        "false": rate(len(false), len(sup)),
        "negative_false_support": rate(len(neg_sup), len(neg)),
        "positive_support_pass": rate(len(pos_support), len(sup)),
        "parse_fail": rate(parse_fail, len(rows_out)),
    }
    denominators_ok = all(rates[k]["denominator"] >= 10 for k in
                          ("leak", "false", "negative_false_support", "positive_support_pass"))
    parse_ok = parse_rate <= 0.05
    passes = (
        complete and denominators_ok and parse_ok
        and rates["leak"]["rate"] is not None and rates["leak"]["rate"] <= 0.20
        and rates["false"]["rate"] is not None and rates["false"]["rate"] <= 0.15
        and rates["negative_false_support"]["rate"] is not None and rates["negative_false_support"]["rate"] <= 0.10
        and rates["positive_support_pass"]["rate"] is not None and rates["positive_support_pass"]["rate"] >= 0.85
    )
    status = "通过" if passes else ("未通过" if complete and denominators_ok and parse_ok else "未接上")

    pair_map = {p["sid"]: p for p in pairs}
    for r in rows_out:
        p = pair_map.get(r["sid"])
        if p:
            r["neg_source_scenario"] = p["neg_source_scenario"]
            r["neg_source_facets"] = p["neg_source_facets"]
            r["neg_source_sha16"] = p["neg_source_sha16"]

    out = {
        "schema": "m5c2_r2_calib_v1",
        "status": status,
        "stage": "1_calibration_only",
        "in_sample": False,
        "no_b2_labels_read": True,
        "no_stage2": True,
        "no_prompt_changes": True,
        "no_accuracy_or_f1": True,
        "prereg": coord(PREREG),
        "prompt_template": PROMPT_TEMPLATE,
        "prompt_template_sha16": PROMPT_TEMPLATE_SHA16,
        "prompt_template_bytes": len(PROMPT_TEMPLATE.encode("utf-8")),
        "first_prompt_sha16": rows_out[0]["prompt_sha16"],
        "inputs": {"adj": coord(ADJ), "alignment": coord(ALIGN), "r1": coord(R1)},
        "source_map": {
            "scenario_facets": {k: list(v) for k, v in SCENARIO_FACETS.items()},
            "blocks": BLOCKS,
            "all_scenarios_share_memory_db": True,
            "note": "All (c) scenarios share the same three memory blocks. Positive source is narrowed to the facet(s) containing the sentence's ADJ basis_facts for supported rows; fabricated rows use the scenario facets. Negative arm takes a different scenario and a non-superset source; same-scenario/superset pairs are rejected.",
        },
        "neg_control_seed": NEG_SEED,
        "pair_table": pairs,
        "calib_rows": [{k: r[k] for k in ("sid", "scenario", "sent_idx", "sentence", "gold",
                                           "question", "source_facets", "source_text",
                                           "source_sha16", "pos_prompt_sha16", "neg_prompt_sha16")}
                       for r in rows],
        "n_forward_done": len(rows_out),
        "n_forward_planned": EXPECT_FORWARDS,
        "complete": complete,
        "aborted": aborted,
        "parse_fail_n": parse_fail,
        "parse_fail_rate": round(parse_rate, 4),
        "rates": rates,
        "thresholds": {"leak_max": 0.20, "false_max": 0.15,
                       "negative_false_support_max": 0.10, "positive_support_pass_min": 0.85,
                       "parse_fail_max": 0.05, "denominators_min": 10},
        "stage1_pass": passes,
        "rows": rows_out,
        "device": meta,
        "host_gate_before": gate0,
        "host_gate_after": gate1,
        "peak_gib": peak,
        "target_gib": TARGET_GIB,
        "fuse_gib": FUSE_GIB,
        "elapsed_s": elapsed,
        "segment_limit_s": SEGMENT_SECONDS,
        "signals_sent_by_parent": False,
        "no_child_process": True,
        "forward_independent": True,
        "kv_reuse": False,
        "n_predict": N_PREDICT,
        "sampling": "greedy_argmax",
        "temperature": 0,
        "no_gpu_batch_stage2": True,
        "no_b2_blind_files": True,
        "gpu_used": True,
        "model_calls": len(rows_out),
    }
    write_json_atomic(ART, out)
    print(json.dumps({k: out[k] for k in ("status", "n_forward_done", "complete", "parse_fail_n",
                                          "rates", "stage1_pass", "peak_gib", "elapsed_s",
                                          "device", "host_gate_before", "host_gate_after")},
                     ensure_ascii=False, indent=2))
    return 0 if status == "通过" else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="load 14B and execute 164 forwards")
    ap.add_argument("--dry-run", action="store_true", help="default; no model")
    a = ap.parse_args()
    verify_prompt_template()
    adj, align, r1 = load_inputs()
    rows = build_calib(adj, align, r1)
    pairs = build_pairs(rows)
    attach_prompts(rows, pairs)
    if not a.run:
        return dry_run(rows, pairs, adj, align, r1)
    print("RUN: 14B model will load; 164 independent forwards", flush=True)
    return run(rows, pairs)


if __name__ == "__main__":
    sys.exit(main())