#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 FLOOR ARTIFACT: 15-case artifact-control test (P/T/O arms).

Lead ruling: formal FLOOR stays 未接上; do not promote GBNF group.  Before
calling the all-A result evidence, rule out three artifacts:
  P: position bias (options reordered; expected "1")
  T: no thinking space (n_predict=96; expected final-line "B")
  O: obvious contradiction (new extreme conflicts; expected "B")

Only P/O use the grammar-constrained DLL; T uses the frozen DLL, as required.
Artifact: m5/out/M5C2-FLOOR-ARTIFACT.json
"""
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
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/m7/out"))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/engine"))
sys.path.insert(0, str(ROOT / "tools"))

import _e3gpu_run as E  # noqa: E402
import run_m5c2_r2 as R2  # noqa: E402
import run_m5c2_floor as F  # noqa: E402

ART = OUT / "M5C2-FLOOR-ARTIFACT.json"
LOG = OUT / "_m5c2_floor_artifact.log"
GBNF_DLL_SHA = "138b6e13881219bc"
FROZEN_DLL_SHA = "9edbafa150700614"

P_TEMPLATE = """下面是一段用户的记忆记录：
【记忆】{source_text}

用户曾问过：{question}
助手在回答里写了这一句：
【待判句子】{sentence}

请只判断：这一句里的具体信息（数字、日期、名称、地点、价格、型号、清单、承诺、属性等）是否都能在【记忆】里找到依据？
只输出三选一，不要解释：
1 = 有编造（至少有一个具体信息在记忆里找不到，或与记忆矛盾）
2 = 完全有依据（每个具体信息都能在记忆里找到）
3 = 无法判断（句子被截断、不完整，或本身不含具体信息）
输出格式：单个数字"""

T_TEMPLATE = """下面是一段用户的记忆记录：
【记忆】{source_text}
用户曾问过：{question}
助手在回答里写了这一句：
【待判句子】{sentence}
请先用一句话说明这一句的具体信息在【记忆】里有没有依据，然后在最后一行只写一个字母：A=完全有依据，B=有编造，C=无法判断。"""

O_CASES = [
    ("我没有养任何宠物。", "我养了一只猫。"),
    ("我从来不去健身房。", "我每周去三次健身房。"),
    ("我不会开车，也没有驾照。", "我的驾照是 C1。"),
    ("我没有办过宽带。", "我办的是北方联通 500M 宽带。"),
    ("我没有订过民宿。", "我订了半山小院。"),
]

P_GRAMMAR = 'root ::= "1" | "2" | "3"'
ABC_GRAMMAR = 'root ::= "A" | "B" | "C"'


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def parse_digit(raw):
    s = (raw or "").strip()
    return s if len(s) == 1 and s in "123" else None


def parse_last_line_letter(raw):
    lines = [x.strip() for x in (raw or "").splitlines() if x.strip()]
    if not lines:
        return None
    last = lines[-1]
    m = re.search(r"[ABC]", last.upper())
    if not m:
        return None
    return m.group(0)


def gbnf_call(L, h, prompt, grammar, n_predict=4):
    L.kvshim_reset(h, 0)
    buf = ctypes.create_string_buffer(16384)
    top_ids = (ctypes.c_int * 3)()
    top_probs = (ctypes.c_float * 3)()
    n_allowed = ctypes.c_int(0)
    n = int(L.kvshim_ask_grammar_probs(
        h, 0, prompt.encode("utf-8"), 0, grammar.encode("utf-8"), b"root",
        n_predict, buf, 16384, 3, top_ids, top_probs, ctypes.byref(n_allowed)))
    raw = "" if n < 0 else buf.value.decode("utf-8", "replace")
    probs = [{"token_id": int(top_ids[j]), "prob": float(top_probs[j])} for j in range(3)]
    L.kvshim_reset(h, 0)
    return raw, n, probs, int(n_allowed.value)


def main():
    fx = F.verify_inputs()
    rows = F.build_rows(fx)
    by_id = {r["fid"]: r for r in rows}
    gate0 = R2.host_gate()
    host0 = E.host_check("artifact_before")
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_floor_artifact_v1", "status": "未接上",
               "reason": "host gate failed before load", "host_gate_before": gate0,
               "host_before": host0, "no_model_loaded": True, "signals_sent": False}
        write_json_atomic(ART, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    # Build all prompts before touching the GPU.
    p_items = []
    for i, fid in enumerate(["F07", "F08", "F09", "F10", "F11"], 1):
        r = by_id[fid]
        p_items.append({
            "aid": "P%d" % i, "arm": "P", "fid": fid,
            "source": r["source"], "sentence": r["sentence"],
            "question": r["question"],
            "prompt_verbatim": P_TEMPLATE.format(
                source_text=r["source"], question=r["question"], sentence=r["sentence"]),
        })
    t_items = []
    for i, fid in enumerate(["F07", "F08", "F09", "F10", "F11"], 1):
        r = by_id[fid]
        t_items.append({
            "aid": "T%d" % i, "arm": "T", "fid": fid,
            "source": r["source"], "sentence": r["sentence"],
            "question": r["question"],
            "prompt_verbatim": T_TEMPLATE.format(
                source_text=r["source"], question=r["question"], sentence=r["sentence"]),
        })
    o_items = []
    for i, (src, sent) in enumerate(O_CASES, 1):
        q = "这句话有依据吗？"
        o_items.append({
            "aid": "O%d" % i, "arm": "O", "fid": "O%d" % i,
            "source": src, "sentence": sent, "question": q,
            "prompt_verbatim": R2.PROMPT_TEMPLATE.format(
                source_text=src, question=q, sentence=sent),
        })

    sampler = F.start_sampler()
    t0 = time.perf_counter()
    items = []
    meta = {}
    aborted = None
    L = h = None
    eng = None
    try:
        # P/O: grammar-constrained custom DLL.
        L, h = F.open_gbnf_engine()
        meta["gbnf_load_s"] = round(time.perf_counter() - t0, 3)
        meta["gbnf_dll_sha16"] = GBNF_DLL_SHA
        meta["gbnf_vulkan_imported"] = E.vulkan_loaded()
        for it in p_items + o_items:
            if time.perf_counter() - t0 > 900:
                aborted = "segment timeout >900s"
                break
            try:
                peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
            except Exception:  # noqa: BLE001
                peak = None
            if peak is not None and peak > 8.6:
                aborted = "VRAM fuse: peak %.4f > 8.6 GiB" % peak
                break
            grammar = P_GRAMMAR if it["arm"] == "P" else ABC_GRAMMAR
            raw, rc, probs, n_allowed = gbnf_call(L, h, it["prompt_verbatim"], grammar, 4)
            parsed = parse_digit(raw) if it["arm"] == "P" else (
                raw.strip() if raw.strip() in "ABC" else None)
            rec = dict(it)
            rec.update({
                "raw_out": raw, "parsed": parsed,
                "ok": parsed is not None,
                "dll": "kvshim_gbnf_vk " + GBNF_DLL_SHA,
                "grammar": grammar, "n_predict": 4,
                "rc": rc, "top_probs": probs, "n_allowed": n_allowed,
                "peak_gib_running": peak,
            })
            items.append(rec)
        try:
            L.kvshim_close(h)
        except Exception:  # noqa: BLE001
            pass
        L = h = None
        time.sleep(0.5)

        # T: frozen DLL, no grammar, n_predict=96.
        gate_mid = R2.host_gate()
        meta["gate_before_t"] = gate_mid
        if not gate_mid.get("gate_ok"):
            aborted = "host gate failed before frozen T engine"
        else:
            eng = R2.open_engine()
            eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p,
                                              ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                                              ctypes.c_int]
            meta["frozen_load_s"] = round(time.perf_counter() - t0, 3)
            meta["frozen_dll_sha16"] = FROZEN_DLL_SHA
            for it in t_items:
                if time.perf_counter() - t0 > 900:
                    aborted = "segment timeout >900s"
                    break
                try:
                    peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
                except Exception:  # noqa: BLE001
                    peak = None
                if peak is not None and peak > 8.6:
                    aborted = "VRAM fuse: peak %.4f > 8.6 GiB" % peak
                    break
                eng.reset(0)
                buf = ctypes.create_string_buffer(32768)
                n = int(eng.lib.kvshim_ask_at(
                    eng.h, 0, it["prompt_verbatim"].encode("utf-8"), 0, 96, buf, 32768))
                raw = "" if n < 0 else buf.value.decode("utf-8", "replace")
                eng.reset(0)
                parsed = parse_last_line_letter(raw)
                rec = dict(it)
                rec.update({
                    "raw_out": raw, "parsed": parsed, "ok": parsed is not None,
                    "dll": "kvshim_vk " + FROZEN_DLL_SHA,
                    "grammar": None, "n_predict": 96, "rc": n,
                    "peak_gib_running": peak,
                })
                items.append(rec)
    except Exception as e:  # noqa: BLE001
        aborted = "exception: %r" % (e,)
    finally:
        if L is not None and h is not None:
            try:
                L.kvshim_close(h)
            except Exception:  # noqa: BLE001
                pass
        if eng is not None:
            try:
                eng.close()
            except Exception:  # noqa: BLE001
                pass
        time.sleep(0.5)
        peak = F.stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 1)
        gate1 = R2.host_gate()
        host1 = E.host_check("artifact_after")

    arms = {}
    for arm, expected in (("P", "1"), ("T", "B"), ("O", "B")):
        ar = [x for x in items if x["arm"] == arm]
        outs = [x["parsed"] for x in ar]
        arms[arm] = {
            "n": len(ar), "expected": expected, "outputs": outs,
            "match": sum(1 for x in outs if x == expected),
            "parse_fail": sum(1 for x in outs if x is None),
            "A_count": sum(1 for x in outs if x == "A"),
            "B_count": sum(1 for x in outs if x == "B"),
            "C_count": sum(1 for x in outs if x == "C"),
            "one_count": sum(1 for x in outs if x == "1"),
            "two_count": sum(1 for x in outs if x == "2"),
            "three_count": sum(1 for x in outs if x == "3"),
        }
    p = arms["P"]
    t = arms["T"]
    o = arms["O"]
    position_bias = (p["two_count"] > 0)
    needs_thinking_space = (t["B_count"] > 0)
    rubber_stamp = (o["A_count"] >= 4) and (not position_bias) and (not needs_thinking_space)
    all_normal = (p["one_count"] == 5 and t["B_count"] == 5 and o["B_count"] == 5
                  and p["parse_fail"] == 0 and t["parse_fail"] == 0 and o["parse_fail"] == 0)
    # T=B is both the expected normal result and the evidence that the earlier
    # n_predict=4 forced-letter run lacked thinking space.  Therefore all_normal
    # takes precedence over the generic needs_thinking_space branch: it means
    # "prior all-A invalid; do a rev2 prereg with the corrected question".
    if position_bias:
        conclusion = "position_bias=true; prior GBNF all-A invalid"
    elif all_normal:
        conclusion = "all_normal; prior all-A was n_predict=4/forced-letter artifact; needs rev2 prereg floor"
    elif needs_thinking_space:
        conclusion = "needs_thinking_space=true; prior GBNF all-A invalid"
    elif rubber_stamp:
        conclusion = "rubber_stamp=true; 14B_can_judge=false"
    else:
        conclusion = "inconclusive; inspect P/T/O individually"

    complete = len(items) == 15 and aborted is None
    out = {
        "schema": "m5c2_floor_artifact_v1",
        "status": "完成" if complete else "未接上",
        "complete": complete, "n_planned": 15, "n_done": len(items),
        "aborted": aborted,
        "prereg": {"file": F.FLOOR_PREREG.name, "sha16": sha16(F.FLOOR_PREREG.read_bytes()),
                   "bytes": F.FLOOR_PREREG.stat().st_size},
        "prompt_prereg": {"file": F.R2_PREREG.name,
                          "sha16": sha16(F.R2_PREREG.read_bytes()),
                          "bytes": F.R2_PREREG.stat().st_size,
                          "template_sha16": R2.PROMPT_TEMPLATE_SHA16},
        "items": items,
        "arms": arms,
        "position_bias": position_bias,
        "needs_thinking_space": needs_thinking_space,
        "rubber_stamp": rubber_stamp,
        "all_normal": all_normal,
        "conclusion": conclusion,
        "device": meta,
        "host_gate_before": gate0, "host_gate_after": gate1,
        "host_before": host0, "host_after": host1,
        "peak_gib": peak, "target_gib": 8.0, "fuse_gib": 8.6,
        "elapsed_s": elapsed, "segment_limit_s": 900,
        "signals_sent": False, "no_parent_signals": True,
        "no_b2_blind_labels": True, "no_accuracy_or_f1": True,
        "no_prompt_changes_to_formal_floor": True,
    }
    write_json_atomic(ART, out)
    print(json.dumps({k: out[k] for k in ("status", "complete", "n_done", "aborted",
                                          "arms", "position_bias", "needs_thinking_space",
                                          "rubber_stamp", "all_normal", "conclusion",
                                          "peak_gib", "elapsed_s", "device")},
                     ensure_ascii=False, indent=2))
    return 0 if complete else 2


if __name__ == "__main__":
    sys.exit(main())