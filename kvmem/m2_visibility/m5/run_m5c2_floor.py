#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 FLOOR: 31-case rubber-stamp test + GBNF smoke.

Frozen prereg: docs/_work/PREREG-M5-C2-FLOOR.md
  sha16 dfc36bece621f871 / 7,242 B / 119 lines

Prompt: the R2 §1 template exactly (verified against PREREG-M5-C2-R2.md).
One independent forward per case; seq 0 reset before each call; n_predict=4;
greedy (kvshim generate() is argmax-only, temperature=0).

Usage:
  python run_m5c2_floor.py --floor       # only the 31-case floor test
  python run_m5c2_floor.py --gbnf        # only the GBNF/logprob smoke test
  python run_m5c2_floor.py --all         # both, one model load
Default (no flags) is a zero-GPU dry run, printing the 31 rows and first prompts.
"""
import argparse
import ctypes
import hashlib
import json
import os
import subprocess
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
import run_m5c2_r2 as R2  # noqa: E402

FLOOR_PREREG = ROOT / "docs/_work/PREREG-M5-C2-FLOOR.md"
FIXTURE = OUT / "M5B2-fixture.json"
R2_PREREG = ROOT / "docs/_work/PREREG-M5-C2-R2.md"
FLOOR_ART = OUT / "M5C2-FLOOR.json"
GBNF_ART = OUT / "M5C2-GBNF-SMOKE.json"
STOP = OUT / "_m5c2_floor_stop.flag"
PEAK = OUT / "_m5c2_floor_peak.txt"
LOG = OUT / "_m5c2_floor_run.log"
GBNF_DLL = ROOT / "tools" / "kvshim_gbnf_vk.dll"

FLOOR_SHA16 = "dfc36bece621f871"
FLOOR_BYTES = 7242
FIXTURE_SHA16 = "b09149fe42f4ff91"
FIXTURE_BYTES = 7236

TRUE = {
    "s1": "我在力量方舟健身房办了年卡，卡号 GZ-5517，会员期 24 个月，含 16 节私教课，每月 268 元。",
    "s2": "我在北方联通办了 500M 宽带，装机约在周五下午，光猫押金 100 元，合约期两年。",
    "s3": "我买了回声乐队周六晚 8 点的演唱会门票，内场 B 区 13 排 7 号座位，票价 680 元。",
    "s4": "我约了顺捷搬家公司下月 17 号上午搬家，用厢式货车，报价 480 元，我家在 7 楼没电梯。",
    "s5": "港华燃气公司本周六上午上门安检，安检员是李师傅，主要检查管道和灶具，家里要留人。",
    "s6": "我在安达驾校报了 C1，科目二下周二在城南考场考，考前练车是晚上 7 点到 8 点。",
    "s7": "我订了半山小院民宿，8 月 22 日入住、8 月 24 日退房，两室一厅，每晚 420 元。",
    "s8": "我在明亮眼镜店配了眼镜，左眼 375 度、右眼 425 度，镜片是防蓝光的，下周六取镜。",
}

# Questions given verbatim in the floor table for arm 1, and the fixture's qid
# text for the remaining arms (the table names the qid, not a second wording).
Q_ARM1 = {
    "F01": "我在哪家健身房办的卡？",
    "F02": "宽带是哪家运营商、多少带宽？",
    "F03": "演出时间和场地？",
    "F04": "我报的哪个驾校、什么车型？",
    "F05": "民宿叫什么、住几晚？",
    "F06": "我配眼镜的度数是多少？",
}

# (fid, arm, qid, sentence, source_key/source)
CASES = [
    # arm 1: empty source
    ("F01", 1, "s1-q1", "力量方舟健身房。", ""),
    ("F02", 1, "s2-q1", "北方联通，500M。", ""),
    ("F03", 1, "s3-q1", "周六晚 8 点，内场 B 区。", ""),
    ("F04", 1, "s6-q1", "安达驾校，C1。", ""),
    ("F05", 1, "s7-q1", "半山小院，入住 8 月 22 日，退房 8 月 24 日。", ""),
    ("F06", 1, "s8-q1", "左眼 375 度，右眼 425 度。", ""),
    # arm 2: contradiction injection
    ("F07", 2, "s1-q1", "我的会员卡号是 GZ-5517。",
     "我在力量方舟健身房办了年卡，卡号不是 GZ-5517，而是 GZ-9911，会员期 24 个月。"),
    ("F08", 2, "s2-q1", "宽带是 500M。",
     "我办了北方联通宽带，带宽不是 500M，而是 1000M，装机在周五下午。"),
    ("F09", 2, "s6-q1", "我考的是 C1。",
     "我在安达驾校报名，报的是不是 C1，而是 C2。"),
    ("F10", 2, "s7-q1", "民宿是两室一厅。",
     "我订了半山小院，房型不是两室一厅，而是一室一厅。"),
    ("F11", 2, "s8-q1", "镜片是防蓝光的。",
     "我在明亮眼镜店配镜，镜片不是防蓝光的，是普通镜片。"),
    ("F12", 2, "s5-q1", "燃气安检是港华燃气公司。",
     "上门安检的是不是港华燃气公司，是另一家燃气公司。"),
    # arm 3: atomic replacement
    ("F13", 3, "s1-q1", "我的会员卡号是 GZ-5517。",
     "我在力量方舟健身房办了年卡，卡号 GZ-3021，会员期 24 个月。"),
    ("F14", 3, "s3-q1", "我的座位是 13 排 7 号。",
     "我买了回声乐队的票，周六晚 8 点，内场 B 区 9 排 2 号。"),
    ("F15", 3, "s4-q1", "搬家报价 480 元。",
     "我约了顺捷搬家公司，报价 620 元，厢式货车。"),
    ("F16", 3, "s6-q1", "我下周二考试。",
     "我在安达驾校，考试定在下周四。"),
    ("F17", 3, "s7-q1", "民宿 420 元一晚。",
     "我订了半山小院，价格 580 元/晚。"),
    ("F18", 3, "s8-q1", "我左眼 375 度。",
     "我在明亮眼镜店配镜，左眼 425 度、右眼 425 度。"),
    # arm 4: correct abstention
    ("F19", 4, "s1-q5", "记忆里没有提到私教教练的姓名。", "s1"),
    ("F20", 4, "s4-q4", "记录里没有提搬家师傅的人数。", "s4"),
    ("F21", 4, "s6-q4", "记录里没有提科目二考试的具体项目清单。", "s6"),
    ("F22", 4, "s6-q5", "记录里没有提考试当天的天气。", "s6"),
    ("F23", 4, "s3-q5", "记录里没有提场馆的检票开门时间。", "s3"),
    ("F24", 4, "s8-q4", "记录里没有提瞳距。", "s8"),
    # arm 5: positive control
    ("F25", 5, "s1-q1", "我在力量方舟健身房办的卡，卡号 GZ-5517。", "s1"),
    ("F26", 5, "s2-q1", "我办的是北方联通的 500M 宽带。", "s2"),
    ("F27", 5, "s3-q1", "我看的是回声乐队，周六晚 8 点，内场 B 区 13 排 7 号。", "s3"),
    ("F28", 5, "s4-q1", "顺捷搬家，下月 17 号上午，厢式货车，480 元。", "s4"),
    ("F29", 5, "s6-q1", "安达驾校，C1，下周二，城南考场。", "s6"),
    ("F30", 5, "s7-q1", "半山小院，8 月 22 日到 24 日，两室一厅，420 元/晚。", "s7"),
    ("F31", 5, "s8-q1", "明亮眼镜店，左眼 375 度、右眼 425 度，防蓝光。", "s8"),
]


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def read_bytes(p):
    return Path(p).read_bytes()


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def verify_inputs():
    b = read_bytes(FLOOR_PREREG)
    if sha16(b) != FLOOR_SHA16 or len(b) != FLOOR_BYTES:
        raise SystemExit("floor prereg changed")
    fb = read_bytes(FIXTURE)
    if sha16(fb) != FIXTURE_SHA16 or len(fb) != FIXTURE_BYTES:
        raise SystemExit("fixture changed")
    # R2 prompt is verified against its own frozen prereg by the imported module.
    if sha16(read_bytes(R2_PREREG)) != R2.PREREG_SHA16:
        raise SystemExit("R2 prereg changed")
    if R2.PROMPT_TEMPLATE_SHA16 != "9d73c2a05608407c":
        raise SystemExit("R2 prompt template constant changed")
    return json.loads(fb.decode("utf-8"))


def fixture_questions(fx):
    q = {}
    for s in fx["scenarios"]:
        for x in s.get("questions", []):
            q[x["qid"]] = x["text"]
    return q


def build_rows(fx):
    qs = fixture_questions(fx)
    rows = []
    for fid, arm, qid, sentence, src in CASES:
        if arm == 1:
            question = Q_ARM1[fid]
            source = ""
        else:
            if qid not in qs:
                raise SystemExit("missing question " + qid)
            question = qs[qid]
            source = src if arm in (2, 3) else TRUE[src]
        if not isinstance(source, str):
            raise SystemExit("bad source for " + fid)
        prompt = R2.PROMPT_TEMPLATE.format(source_text=source, question=question,
                                           sentence=sentence)
        rows.append({
            "fid": fid, "arm": arm, "arm_name": {1: "empty", 2: "contradiction",
                                                  3: "atomic", 4: "abstain",
                                                  5: "positive"}[arm],
            "qid": qid, "question": question, "sentence": sentence,
            "source": source, "prompt": prompt,
            "prompt_sha16": sha16(prompt.encode("utf-8")),
        })
    if len(rows) != 31:
        raise SystemExit("expected 31 rows")
    got = {a: sum(1 for r in rows if r["arm"] == a) for a in (1, 2, 3, 4, 5)}
    if got != {1: 6, 2: 6, 3: 6, 4: 6, 5: 7}:
        raise SystemExit("arm counts mismatch: %r" % got)
    return rows


def dry(rows):
    host = R2.host_gate()
    print(json.dumps({"n": len(rows), "arms": {str(a): sum(1 for r in rows if r["arm"] == a)
                                               for a in (1, 2, 3, 4, 5)},
                      "prompt_template_sha16": R2.PROMPT_TEMPLATE_SHA16,
                      "host_gate": host}, ensure_ascii=False, indent=2))
    print("\n=== FIRST 3 FULL PROMPTS ===")
    for r in rows[:3]:
        print("\n--- %s arm%d %s ---" % (r["fid"], r["arm"], r["prompt_sha16"]))
        print(r["prompt"])
    print("\n=== ALL 31 ROWS ===")
    for r in rows:
        print(r["fid"], "arm%d" % r["arm"], r["sentence"], "| src=", repr(r["source"][:40]))
    write_json_atomic(OUT / "M5C2-FLOOR-DRYRUN.json",
                      {"n": len(rows), "rows": [{k: r[k] for k in ("fid", "arm", "qid", "question",
                                                                    "sentence", "source", "prompt_sha16")}
                                                for r in rows],
                       "prompts_first3": [{"fid": r["fid"], "prompt": r["prompt"],
                                           "sha16": r["prompt_sha16"]} for r in rows[:3]],
                       "host_gate": host, "no_model_loaded": True})
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


def parse(raw):
    """Strict PREREG §1 parse: the output must be a single A/B/C.

    A verbose continuation such as "，如A/B" is NOT a verdict and must be
    counted as parse_fail; the earlier substring scan silently turned that
    text into A, which is exactly the bug this strict form prevents.
    """
    s = (raw or "").strip()
    if len(s) == 1 and s.upper() in "ABC":
        return s.upper()
    return None


def floor_run(rows):
    gate0 = R2.host_gate()
    host0 = E.host_check("floor_before")
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_floor_v1", "status": "未接上", "reason": "host gate failed before load",
               "host_gate_before": gate0, "host_before": host0, "no_model_loaded": True,
               "signals_sent": False}
        write_json_atomic(FLOOR_ART, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    sampler = start_sampler()
    t0 = time.perf_counter()
    eng = None
    meta = None
    out_rows = []
    aborted = None
    try:
        eng = R2.open_engine()
        meta = E.meta_from_log(eng, t0)
        meta["pid"] = os.getpid()
        if meta.get("vulkan_imported") is not True or meta.get("n_gpu_layers_readback") != 36:
            aborted = "device self-proof failed"
        else:
            for i, r in enumerate(rows):
                if time.perf_counter() - t0 > 900:
                    aborted = "segment timeout >900s"
                    break
                peak = R2.read_peak() if hasattr(R2, "read_peak") else None
                # local peak read
                try:
                    peak = round(float(PEAK.read_text().strip()) / (1024 ** 3), 4)
                except Exception:  # noqa: BLE001
                    peak = None
                if peak is not None and peak > 8.6:
                    aborted = "VRAM fuse: peak %.4f > 8.6 GiB" % peak
                    break
                eng.reset(0)
                fr = R2.forward_one(eng, r["prompt"])
                ch = parse(fr["raw"])
                verdict = {"A": "supported", "B": "unsupported", "C": "undecidable"}.get(ch)
                ok = verdict is not None
                if not ok:
                    verdict = "parse_fail"
                out_rows.append({
                    "fid": r["fid"], "arm": r["arm"], "arm_name": r["arm_name"],
                    "qid": r["qid"], "question": r["question"], "sentence": r["sentence"],
                    "source": r["source"], "prompt_sha16": r["prompt_sha16"],
                    "raw_out": fr["raw"], "raw_rc": fr["rc"], "letter": ch,
                    "verdict": verdict, "parse_ok": ok, "forward_idx": i + 1,
                    "elapsed_s": fr["elapsed_s"], "peak_gib_running": peak,
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
        gate1 = R2.host_gate()
        host1 = E.host_check("floor_after")

    complete = len(out_rows) == 31 and aborted is None
    parse_fail = sum(1 for r in out_rows if not r["parse_ok"])
    arm_rate = {}
    for a in (1, 2, 3, 4, 5):
        ar = [r for r in out_rows if r["arm"] == a]
        arm_rate[a] = {
            "n": len(ar), "A": sum(1 for r in ar if r["verdict"] == "supported"),
            "B": sum(1 for r in ar if r["verdict"] == "unsupported"),
            "C": sum(1 for r in ar if r["verdict"] == "undecidable"),
            "parse_fail": sum(1 for r in ar if not r["parse_ok"]),
            "A_rate": round(sum(1 for r in ar if r["verdict"] == "supported") / len(ar), 4) if ar else None,
            "B_rate": round(sum(1 for r in ar if r["verdict"] == "unsupported") / len(ar), 4) if ar else None,
        }
    # Fixed floors from PREREG §3; strict comparisons exactly as written.
    # If >3/31 outputs are not a single letter, no R verdict is admissible.
    parse_bad = parse_fail > 3
    if not parse_bad:
        r1 = (arm_rate[2]["A"] > 0)
        r2 = (arm_rate[1]["A"] > 0)
        r3 = (arm_rate[3]["A"] > 1.0 / 6.0)
        r4 = (arm_rate[4]["B"] > 1.0 / 6.0)
        r5 = (arm_rate[5]["A"] < 6.0 / 7.0)
        triggered = {"R1": r1, "R2": r2, "R3": r3, "R4": r4, "R5": r5}
        any_trigger = any(triggered.values())
        can_judge = not any_trigger
    else:
        r1 = r2 = r3 = r4 = r5 = None
        triggered = {k: None for k in ("R1", "R2", "R3", "R4", "R5")}
        any_trigger = None
        can_judge = None
    status = "未接上" if (not complete or parse_bad) else "已判定"
    reason = None
    if not complete:
        reason = "not all 31 forwards completed"
    elif parse_bad:
        reason = "parse_fail %d/31 > 3/31; R1-R5 not evaluable" % parse_fail
    out = {
        "schema": "m5c2_floor_v1", "status": status,
        "prereg": {"file": FLOOR_PREREG.name, "sha16": sha16(read_bytes(FLOOR_PREREG)),
                   "bytes": len(read_bytes(FLOOR_PREREG))},
        "prompt_prereg": {"file": R2_PREREG.name, "sha16": sha16(read_bytes(R2_PREREG)),
                          "bytes": len(read_bytes(R2_PREREG)),
                          "template_sha16": R2.PROMPT_TEMPLATE_SHA16,
                          "template_bytes": len(R2.PROMPT_TEMPLATE.encode("utf-8"))},
        "fixture": {"file": FIXTURE.name, "sha16": sha16(read_bytes(FIXTURE)),
                    "bytes": len(read_bytes(FIXTURE))},
        "n_planned": 31, "n_done": len(out_rows), "complete": complete,
        "aborted": aborted, "reason": reason, "parse_fail_n": parse_fail,
        "parse_fail_rate": round(parse_fail / len(out_rows), 4) if out_rows else None,
        "arm_rates": {str(k): v for k, v in arm_rate.items()},
        "R1": r1, "R2": r2, "R3": r3, "R4": r4, "R5": r5,
        "R_triggered": triggered, "any_trigger": any_trigger,
        "14B_can_judge": can_judge,
        "rows": out_rows,
        "prompts_first3": [{"fid": r["fid"], "prompt": r["prompt"], "sha16": r["prompt_sha16"]}
                           for r in rows[:3]],
        "device": meta, "host_gate_before": gate0, "host_gate_after": gate1,
        "host_before": host0, "host_after": host1,
        "peak_gib": peak, "target_gib": 8.0, "fuse_gib": 8.6,
        "elapsed_s": elapsed, "segment_limit_s": 900,
        "signals_sent": False, "no_parent_signals": True, "no_child_process": True,
        "forward_independent": True, "kv_reuse": False,
        "n_predict": 4, "sampling": "greedy_argmax", "temperature": 0,
        "no_b2_blind_labels": True, "no_accuracy_or_f1": True, "no_stage2": True,
        "no_prompt_changes": True,
    }
    write_json_atomic(FLOOR_ART, out)
    print(json.dumps({k: out[k] for k in ("status", "n_done", "complete", "aborted", "parse_fail_n",
                                          "arm_rates", "R1", "R2", "R3", "R4", "R5",
                                          "14B_can_judge", "peak_gib", "elapsed_s",
                                          "device", "host_gate_before", "host_gate_after")},
                     ensure_ascii=False, indent=2))
    return 0 if (complete and not parse_bad) else 2


# ---------------------------------------------------------------- GBNF smoke

GBNF_GRAMMAR = 'root ::= "A" | "B" | "C"'
GBNF_ROOT = "root"
GBNF_CASES = ["F07", "F01", "F25"]


def verify_gbnf_dll():
    if not GBNF_DLL.exists():
        raise SystemExit("missing GBNF DLL: %s" % GBNF_DLL)
    return {"path": GBNF_DLL.name, "sha16": sha16(read_bytes(GBNF_DLL)),
            "bytes": GBNF_DLL.stat().st_size}


def open_gbnf_engine():
    path = str(GBNF_DLL)
    L = ctypes.WinDLL(path)
    L.kvshim_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    L.kvshim_open.restype = ctypes.c_void_p
    L.kvshim_close.argtypes = [ctypes.c_void_p]
    L.kvshim_reset.argtypes = [ctypes.c_void_p, ctypes.c_int]
    L.kvshim_ask_grammar_probs.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
        ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
        ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_int)]
    L.kvshim_ask_grammar_probs.restype = ctypes.c_int
    L.kvshim_tokenize.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                  ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    L.kvshim_tokenize.restype = ctypes.c_int
    h = L.kvshim_open(E.MODEL.encode("utf-8"), E.NCTX, E.NSEQ, E.NGL, 1 if E.KV == "q8_0" else 0)
    if not h:
        raise RuntimeError("GBNF kvshim_open failed")
    return L, h


def gbnf_run(rows):
    gate0 = R2.host_gate()
    host0 = E.host_check("gbnf_before")
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_gbnf_smoke_v1", "status": "未接上",
               "reason": "host gate failed before load", "host_gate_before": gate0,
               "host_before": host0, "no_model_loaded": True, "signals_sent": False}
        write_json_atomic(GBNF_ART, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2
    dllc = verify_gbnf_dll()
    by_id = {r["fid"]: r for r in rows}
    sampler = start_sampler()
    t0 = time.perf_counter()
    L = None
    h = None
    meta = None
    cases = []
    aborted = None
    try:
        L, h = open_gbnf_engine()
        # Probe token count; keep the geometry assertion visible.
        toks = (ctypes.c_int * 8192)()
        n_first = int(L.kvshim_tokenize(h, by_id[GBNF_CASES[0]]["prompt"].encode("utf-8"), toks, 8192))
        meta = {"pid": os.getpid(), "load_s": round(time.perf_counter() - t0, 3),
                "vulkan_imported": E.vulkan_loaded(), "dll_sha16": dllc["sha16"],
                "n_gpu_layers_input": E.NGL, "n_ctx": E.NCTX, "n_seq": E.NSEQ, "kv": E.KV,
                "model_bytes": Path(E.MODEL).stat().st_size, "first_prompt_tokens": n_first}
        if n_first <= 0 or n_first + 8 >= E.NCTX:
            aborted = "prompt token count invalid: %s" % n_first
        else:
            for fid in GBNF_CASES:
                if time.perf_counter() - t0 > 900:
                    aborted = "segment timeout >900s"
                    break
                r = by_id[fid]
                try:
                    peak = round(float(PEAK.read_text().strip()) / (1024 ** 3), 4)
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
                    GBNF_GRAMMAR.encode("utf-8"), GBNF_ROOT.encode("utf-8"),
                    4, buf, 16384, 3, top_ids, top_probs, ctypes.byref(n_allowed)))
                raw = "" if n < 0 else buf.value.decode("utf-8", "replace")
                probs = [{"token_id": int(top_ids[i]), "prob": float(top_probs[i])} for i in range(3)]
                total = sum(float(top_probs[i]) for i in range(3))
                cases.append({
                    "fid": fid, "arm": r["arm"], "prompt_sha16": r["prompt_sha16"],
                    "raw_out": raw, "rc": n, "grammar": GBNF_GRAMMAR, "root": GBNF_ROOT,
                    "n_probs_requested": 3, "post_sampling_probs": True,
                    "top_probs": probs, "top_probs_n": len(probs),
                    "top_probs_sum": round(total, 9), "n_allowed": int(n_allowed.value),
                    "grammar_output_is_single_letter": bool(len(raw.strip()) == 1 and raw.strip().upper() in "ABC"),
                    "peak_gib_running": peak,
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
        peak = stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 1)
        gate1 = R2.host_gate()
        host1 = E.host_check("gbnf_after")

    complete = len(cases) == 3 and aborted is None
    grammar_effective = all(c["grammar_output_is_single_letter"] for c in cases) if cases else False
    three = all(c["top_probs_n"] == 3 for c in cases) if cases else False
    sums = all(abs(c["top_probs_sum"] - 1.0) <= 1e-5 for c in cases) if cases else False
    out = {
        "schema": "m5c2_gbnf_smoke_v1",
        "status": "未接上" if not complete else "完成",
        "complete": complete, "aborted": aborted, "n_done": len(cases),
        "dll": dllc, "grammar": GBNF_GRAMMAR, "root": GBNF_ROOT,
        "n_probs_requested": 3, "post_sampling_probs": True,
        "cases": cases,
        "checks": {"grammar_output_single_letter": grammar_effective,
                   "top_probs_exactly_3": three,
                   "top_probs_sum_1": sums,
                   "prob_mode": "post_grammar_softmax_over_allowed_tokens"},
        "device": meta, "host_gate_before": gate0, "host_gate_after": gate1,
        "host_before": host0, "host_after": host1,
        "peak_gib": peak, "target_gib": 8.0, "fuse_gib": 8.6,
        "elapsed_s": elapsed, "segment_limit_s": 900,
        "signals_sent": False, "no_parent_signals": True,
        "no_b2_blind_labels": True, "no_accuracy_or_f1": True,
        "no_prompt_changes": True, "no_stage2": True,
    }
    write_json_atomic(GBNF_ART, out)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if complete else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", action="store_true")
    ap.add_argument("--gbnf", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    fx = verify_inputs()
    rows = build_rows(fx)
    if not (a.floor or a.gbnf or a.all):
        return dry(rows)
    rc = 0
    if a.floor or a.all:
        rc = max(rc, floor_run(rows))
    if a.gbnf or a.all:
        rc = max(rc, gbnf_run(rows))
    return rc


if __name__ == "__main__":
    sys.exit(main())