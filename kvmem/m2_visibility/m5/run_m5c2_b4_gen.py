#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B4 generation runner.

Dry run (no GPU):
    python -X utf8 run_m5c2_b4_gen.py --dry-run
Actual (only after LEAD freezes B4 and authorizes):
    python -X utf8 run_m5c2_b4_gen.py --run --expected-prereg-sha16 <sha16>

Generation only: one source memory per scenario, one forward per question,
n_predict=192, greedy, no grammar, raw answer written whole (no sentence split).
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

PRE = ROOT / "docs/_work/PREREG-M5-C2-B4.md"
ART = OUT / "M5B4-GEN.json"
SENT_ART = OUT / "M5B4-SENTENCES.json"
RAW_ART = OUT / "_m5b4_gen_raw.json"
CHAT_START = 4096
N_PREDICT = 192
TARGET_GIB = 8.0
FUSE_GIB = 8.6
SCENARIO_TIMEOUT = 900
FROZEN_DLL_SHA = "9edbafa150700614"
TURN_TEMPLATE = "\n问：{question}\n答："


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


SCEN_RE = re.compile(r"^###\s+(b4-s\d+)\s+(.*)$")
SRC_RE = re.compile(r"^-\s*源文（[^）]*）：「(.*)」\s*$")
Q_RE = re.compile(r"^-\s*(b4-s\d+-q\d+)\s*\[(detail|lure)\]：「(.*)」\s*$")


def parse_b4():
    text = PRE.read_text(encoding="utf-8")
    lines = text.splitlines()
    scenes = []
    cur = None
    for ln in lines:
        m = SCEN_RE.match(ln)
        if m:
            cur = {"sid": m.group(1), "domain": m.group(2).strip(),
                   "source_text": None, "questions": []}
            scenes.append(cur)
            continue
        if cur is None:
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
    if len(scenes) != 8:
        raise SystemExit("expected 8 scenes, got %d" % len(scenes))
    for s in scenes:
        if not s["source_text"]:
            raise SystemExit("missing source in %s" % s["sid"])
        if len(s["questions"]) != 5:
            raise SystemExit("%s has %d questions" % (s["sid"], len(s["questions"])))
        if not s["sid"].startswith("b4-"):
            raise SystemExit("bad sid %s" % s["sid"])
    qids = [q["qid"] for s in scenes for q in s["questions"]]
    if len(qids) != 40 or len(set(qids)) != 40:
        raise SystemExit("expected 40 unique qids, got %d/%d" % (len(qids), len(set(qids))))
    return scenes


def turn_prompt(question):
    # Verbatim kvslots.KVEngine.turn: ASK_PREFIX + question + ASK_SUFFIX.
    return "\n问：" + question + "\n答："


def prompt_text(source, question):
    # Provenance hash over the exact memory text + exact turn. The runtime
    # layout places source in KV memory and asks the turn at CHAT_START.
    return source + turn_prompt(question)


def split_sentences(answer):
    """PREREG §4: split by newline and 。！？; drop empty/pure-symbol/问 echo."""
    out = []
    for line in (answer or "").splitlines():
        parts = re.split(r"(?<=[。！？])", line)
        for seg in parts:
            s = seg.strip()
            if not s:
                continue
            if s.startswith("问：") or s.startswith("问:"):
                continue
            if not re.sub(r"[\s\W_]+", "", s):
                continue
            if re.match(r"^</?think\s*>$", s):
                continue
            out.append(s)
    return out


def verify_prereg(require_frozen):
    b = PRE.read_bytes()
    text = b.decode("utf-8")
    if require_frozen and "frozen=false" in text:
        raise SystemExit("B4 prereg is still frozen=false; wait for LEAD freeze")
    if require_frozen and "frozen=true" not in text:
        raise SystemExit("B4 prereg does not declare frozen=true")
    return {"file": PRE.name, "sha16": sha16(b), "bytes": len(b),
            "lines": len(text.splitlines())}


def dry_run(scenes, prereg):
    rows = []
    for s in scenes:
        for q in s["questions"]:
            p = prompt_text(s["source_text"], q["question"])
            rows.append({
                "qid": q["qid"], "scenario": s["sid"], "domain": s["domain"],
                "source_text": s["source_text"], "question": q["question"],
                "turn_prompt": turn_prompt(q["question"]),
                "prompt_sha16": sha16(p.encode("utf-8")),
            })
    print(json.dumps({
        "schema": "m5c2_b4_gen_dry_run_v1",
        "status": "dry_run_only",
        "prereg": prereg,
        "n_scenarios": len(scenes),
        "n_questions": len(rows),
        "n_predict": N_PREDICT,
        "chat_start": CHAT_START,
        "prompt_template_sha16": sha16(TURN_TEMPLATE.encode("utf-8")),
        "greedy": True,
        "grammar": None,
        "n_forward": 0,
        "no_gpu": True,
        "first_3_prompts": rows[:3],
    }, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--expected-prereg-sha16", default=None)
    a = ap.parse_args()
    scenes = parse_b4()
    prereg = verify_prereg(require_frozen=a.run)
    if a.run and a.expected_prereg_sha16 and prereg["sha16"] != a.expected_prereg_sha16:
        raise SystemExit("B4 prereg sha16 mismatch: %s != %s" %
                         (prereg["sha16"], a.expected_prereg_sha16))
    if a.dry_run:
        return dry_run(scenes, prereg)
    if not a.run:
        print("choose --dry-run or --run")
        return 2
    # Actual GPU run starts here; never import/load engine during dry-run.
    import run_m5c2_rev2_order as CO
    import run_m5c2_floor as F
    import run_m5_b2_v2 as G

    gate0, gate_exceptions = CO.gate_with_dwm_exception()
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_b4_gen_v1", "status": "未接上",
               "reason": "host gate failed before load", "prereg": prereg,
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
        eng, meta = G.open_engine()
        meta["frozen_dll_sha16"] = FROZEN_DLL_SHA
        meta["n_predict"] = N_PREDICT
        meta["chat_start"] = CHAT_START
        meta["kv_policy"] = "source_once_per_scenario_then_questions_no_reset"
        for s in scenes:
            if time.perf_counter() - t0 > SCENARIO_TIMEOUT * len(scenes):
                aborted = "timeout >%ds" % (SCENARIO_TIMEOUT * len(scenes))
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
                    aborted = "scenario %s timeout >900s" % s["sid"]
                    break
                # b2-compatible KV growth: first turn at CHAT_START, later turns
                # at pos_max+1 (no reset inside a scenario).
                pos = CHAT_START if qi == 0 else int(eng.pos_max(G.P.LIVE)) + 1
                p = prompt_text(s["source_text"], q["question"])
                rec = {
                    "sid": q["qid"] + "-s", "qid": q["qid"],
                    "scenario": s["sid"], "domain": s["domain"],
                    "kind": q["kind"], "source_text": s["source_text"],
                    "question": q["question"], "turn_prompt": turn_prompt(q["question"]),
                    "prompt_sha16": sha16(p.encode("utf-8")),
                    "build": build, "answer_full": None, "sentences": [],
                    "answer_sha16": None, "answer_chars": None,
                    "pos_asked": pos,
                    "n_tokens_before": None, "n_tokens_after": None,
                    "elapsed_s": None, "n_predict": N_PREDICT,
                }
                try:
                    one = G.ask_one(eng, q["question"], pos, N_PREDICT)
                    rec.update({
                        "answer_full": one["answer"],
                        "answer_sha16": one["answer_sha16"],
                        "answer_chars": one["answer_chars"],
                        "n_tokens_before": one["n_tokens_before"],
                        "n_tokens_after": one["n_tokens_after"],
                        "elapsed_s": one["elapsed_s"],
                        "rc": one["rc"],
                    })
                    rec["sentences"] = split_sentences(one["answer"])
                    forwards += 1
                except Exception as e:  # noqa: BLE001
                    rec["error"] = repr(e)
                    aborted = "question failed: %s %s" % (q["qid"], repr(e))
                results.append(rec)
                write_json_atomic(RAW_ART, {"n_forward": forwards, "aborted": aborted,
                                            "results": results})
                if aborted:
                    break
            if aborted:
                break
        gate1, gate_exceptions_after = CO.gate_with_dwm_exception()
        peak = F.stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 3)
        out = {
            "schema": "m5c2_b4_gen_v1",
            "status": "已生成" if aborted is None else "未接上",
            "prereg": prereg,
            "n_predict": N_PREDICT,
            "temperature": 0,
            "sampling": "argmax_greedy",
            "grammar": None,
            "dll": meta.get("dll_sha16"),
            "frozen_dll_sha16": FROZEN_DLL_SHA,
            "chat_start": CHAT_START,
            "kv_policy": "source_once_per_scenario_then_questions_no_reset",
            "n_scenarios": len(scenes),
            "n_questions_planned": 40,
            "n_forward": forwards,
            "aborted": aborted,
            "qa": results,
            "sentences_nonempty": sum(len(r.get("sentences") or []) for r in results),
            "gate_before": gate0,
            "gate_after": gate1,
            "gate_exceptions": gate_exceptions,
            "gate_exceptions_after": gate_exceptions_after,
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
            "sentence_split_done": True,
            "no_judge": True,
            "no_gold": True,
        }
        out["prereg_sha16"] = prereg["sha16"]
        out["prompt_template_sha16"] = sha16(TURN_TEMPLATE.encode("utf-8"))
        write_json_atomic(ART, out)
        # frozen sentence list for blind labeling; no verdict fields.
        sent_rows = []
        for r in results:
            for i, s in enumerate(r.get("sentences") or [], 1):
                sent_rows.append({
                    "sid": "%s-s%02d" % (r["qid"], i),
                    "qid": r["qid"], "scenario": r["scenario"],
                    "source_text": r["source_text"], "question": r["question"],
                    "text": s,
                })
        write_json_atomic(SENT_ART, {
            "schema": "m5c2_b4_sentences_v1",
            "prereg_sha16": prereg["sha16"],
            "n_sentences": len(sent_rows),
            "sentences_nonempty": len(sent_rows),
            "generated_from": ART.name,
            "no_verdict": True,
            "sentences": sent_rows,
        })
        print(json.dumps({k: out[k] for k in ("status", "n_forward", "aborted",
                                              "peak_gib", "elapsed_s", "prereg",
                                              "gate_exceptions")},
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