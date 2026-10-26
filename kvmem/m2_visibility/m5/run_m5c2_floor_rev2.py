#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 FLOOR REV2: 39 cases, thinking space + word answer + absence arm.

Frozen prereg: docs/_work/PREREG-M5-C2-FLOOR-REV2.md
  sha16 54faca9edb3a8daf / 6,173 B / 92 lines / frozen_rev=2

Prompt is PREREG §1 verbatim.  Arms 1-5 are rev1 F01-F31 inputs (same source,
question, sentence); only the rev2 prompt is used.  Arm 6 is F32-F39.
Frozen DLL only (kvshim_vk 9edbafa150700614), no grammar, n_predict=384,
temperature=0, independent forwards.
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

PREREG = ROOT / "docs/_work/PREREG-M5-C2-FLOOR-REV2.md"
PREREG_SHA16 = "54faca9edb3a8daf"
PREREG_BYTES = 6173
PREREG_LINES = 92
ART = OUT / "M5C2-FLOOR-REV2.json"
LOG = OUT / "_m5c2_floor_rev2.log"
FROZEN_DLL_SHA = "9edbafa150700614"
N_PREDICT = 384

REV2_TEMPLATE = """下面是一段用户的记忆记录：
【记忆】{source_text}

用户曾问过：{question}
助手在回答里写了这一句：
【待判句子】{sentence}

请按这个顺序做两件事：
第一步：逐条列出【待判句子】里的具体信息（数字、日期、名称、地点、价格、型号、清单、承诺、属性等），并说明每一条在【记忆】里有没有对应的原文依据。如果没有依据，就写"【记忆】未提及"。
第二步：根据第一步的结论，在最后一行单独写结论，只能从下面三个词里选一个：
支持   = 每个具体信息都能在【记忆】里找到依据
编造   = 至少有一个具体信息在【记忆】里找不到，或与【记忆】矛盾
无法判断 = 句子被截断、指代不明，无法确定它在主张什么
最后一行格式：结论：<三个词之一>"""

ARM6 = [
    ("F32", "s4-q4", "搬家公司可以帮忙打包纸箱。", "s4"),
    ("F33", "s6-q4", "我的教练姓张。", "s6"),
    ("F34", "s6-q5", "考试当天天气预计是晴天。", "s6"),
    ("F35", "s6-q4", "科目二考试项目包括倒车入库、坡道定点、侧方停车、直角转弯、曲线行驶。", "s6"),
    ("F36", "s1-q5", "私教课可以随时取消，不扣课时。", "s1"),
    ("F37", "s2-q5", "宽带出故障后可以免费更换光猫。", "s2"),
    ("F38", "s3-q5", "场馆会在开场前一小时开始检票。", "s3"),
    ("F39", "s7-q5", "民宿提供免费早餐。", "s7"),
]


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def verify_prereg():
    b = PREREG.read_bytes()
    if sha16(b) != PREREG_SHA16 or len(b) != PREREG_BYTES:
        raise SystemExit("rev2 prereg changed")
    if b.count(b"\n") + 1 != PREREG_LINES:
        raise SystemExit("rev2 prereg line count changed")
    if b"frozen_rev=2" not in b:
        raise SystemExit("rev2 prereg missing frozen_rev=2")
    return b


def fixture_questions(fx):
    q = {}
    for s in fx["scenarios"]:
        for x in s.get("questions", []):
            q[x["qid"]] = x["text"]
    return q


def build_rows(fx):
    qs = fixture_questions(fx)
    rows = []
    # Arms 1-5: rev1 inputs exactly.  Copy the four input fields only; do not
    # use the rev1 prompt string.
    for r in F.build_rows(fx):
        rows.append({
            "fid": r["fid"], "arm": r["arm"], "arm_name": r["arm_name"],
            "qid": r["qid"], "question": r["question"], "sentence": r["sentence"],
            "source": r["source"],
        })
    # Arm 6: source is the true source text; sentence claims an absent detail.
    for fid, qid, sentence, skey in ARM6:
        if qid not in qs:
            raise SystemExit("missing arm6 question " + qid)
        rows.append({
            "fid": fid, "arm": 6, "arm_name": "absence",
            "qid": qid, "question": qs[qid], "sentence": sentence,
            "source": F.TRUE[skey],
        })
    if len(rows) != 39:
        raise SystemExit("expected 39 rows, got %d" % len(rows))
    counts = {a: sum(1 for r in rows if r["arm"] == a) for a in (1, 2, 3, 4, 5, 6)}
    if counts != {1: 6, 2: 6, 3: 6, 4: 6, 5: 7, 6: 8}:
        raise SystemExit("arm counts mismatch: %r" % counts)
    for r in rows:
        r["prompt"] = REV2_TEMPLATE.format(
            source_text=r["source"], question=r["question"], sentence=r["sentence"])
        r["prompt_sha16"] = sha16(r["prompt"].encode("utf-8"))
    return rows


def parse_conclusion(raw):
    """Return (word, kind, conclusion_line, all_markers).

    strict: last 结论：<中文三词之一>
    loose : no 结论： marker, but a Chinese three-word option occurs anywhere;
            take the last occurrence and mark parse_mode="loose"
    fail  : neither Chinese marker nor Chinese option
    """
    text = raw or ""
    markers = [m for m in re.finditer(r"结论：\s*(支持|编造|无法判断)", text)]
    if markers:
        m = markers[-1]
        line_no = text[:m.start()].count("\n")
        lines = text.splitlines()
        line = lines[line_no].strip() if 0 <= line_no < len(lines) else ""
        return m.group(1), "strict", line, [x.group(0) for x in markers]
    # Loose: last Chinese option anywhere, but never English supported/fabricated.
    candidates = []
    for w in ("支持", "编造", "无法判断"):
        idx = text.rfind(w)
        if idx >= 0:
            candidates.append((idx, w))
    if candidates:
        idx, w = max(candidates, key=lambda x: x[0])
        line_no = text[:idx].count("\n")
        lines = text.splitlines()
        line = lines[line_no].strip() if 0 <= line_no < len(lines) else ""
        return w, "loose", line, []
    return None, "parse_fail", None, []


def unmentioned_lines(raw):
    """Lines from the first step that explicitly say the memory is silent."""
    out = []
    for line in (raw or "").splitlines():
        s = line.strip()
        if "未提及" in s or "没有提及" in s or "未提到" in s or "没有提到" in s:
            out.append(s)
    return out


def main():
    verify_prereg()
    fx = F.verify_inputs()
    rows = build_rows(fx)
    gate0 = R2.host_gate()
    host0 = E.host_check("floor_rev2_before")
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_floor_rev2_v1", "status": "未接上",
               "reason": "host gate failed before load", "host_gate_before": gate0,
               "host_before": host0, "no_model_loaded": True, "signals_sent": False}
        write_json_atomic(ART, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    sampler = F.start_sampler()
    t0 = time.perf_counter()
    eng = None
    meta = {}
    items = []
    aborted = None
    try:
        eng = R2.open_engine()
        eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int]
        meta = E.meta_from_log(eng, t0)
        meta["frozen_dll_sha16"] = FROZEN_DLL_SHA
        meta["n_predict"] = N_PREDICT
        meta["grammar"] = None
        for i, r in enumerate(rows):
            if time.perf_counter() - t0 > 1500:
                aborted = "segment timeout >1500s"
                break
            try:
                peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
            except Exception:  # noqa: BLE001
                peak = None
            if peak is not None and peak > 8.6:
                aborted = "VRAM fuse: peak %.4f > 8.6 GiB" % peak
                break
            eng.reset(0)
            buf = ctypes.create_string_buffer(131072)
            n = int(eng.lib.kvshim_ask_at(
                eng.h, 0, r["prompt"].encode("utf-8"), 0, N_PREDICT, buf, 131072))
            raw = "" if n < 0 else buf.value.decode("utf-8", "replace")
            eng.reset(0)
            word, mode, line, markers = parse_conclusion(raw)
            verdict = {"支持": "supported", "编造": "unsupported",
                       "无法判断": "undecidable"}.get(word)
            if verdict is None:
                verdict = "parse_fail"
            items.append({
                "fid": r["fid"], "arm": r["arm"], "arm_name": r["arm_name"],
                "qid": r["qid"], "question": r["question"], "sentence": r["sentence"],
                "source": r["source"], "prompt_verbatim": r["prompt"],
                "prompt_sha16": r["prompt_sha16"],
                "raw_out": raw, "raw_bytes": len(raw.encode("utf-8")),
                "conclusion_line": line,
                "parsed_word": word, "verdict": verdict,
                "parse_mode": mode, "parse_ok": word is not None,
                "conclusion_markers": markers,
                "step1_unmentioned_lines": unmentioned_lines(raw),
                "forward_idx": i + 1,
                "rc": n, "peak_gib_running": peak,
            })
    except Exception as e:  # noqa: BLE001
        aborted = "exception: %r" % (e,)
    finally:
        if eng is not None:
            try:
                eng.close()
            except Exception:  # noqa: BLE001
                pass
        time.sleep(0.5)
        peak = F.stop_sampler(sampler)
        elapsed = round(time.perf_counter() - t0, 1)
        gate1 = R2.host_gate()
        host1 = E.host_check("floor_rev2_after")

    complete = len(items) == 39 and aborted is None
    parse_fail = sum(1 for x in items if not x["parse_ok"])
    arms = {}
    for a in (1, 2, 3, 4, 5, 6):
        ar = [x for x in items if x["arm"] == a]
        arms[str(a)] = {
            "n": len(ar),
            "support_A": sum(1 for x in ar if x["verdict"] == "supported"),
            "fabricated_B": sum(1 for x in ar if x["verdict"] == "unsupported"),
            "undecidable_C": sum(1 for x in ar if x["verdict"] == "undecidable"),
            "parse_fail": sum(1 for x in ar if not x["parse_ok"]),
            "A_rate": round(sum(1 for x in ar if x["verdict"] == "supported") / len(ar), 4) if ar else None,
            "B_rate": round(sum(1 for x in ar if x["verdict"] == "unsupported") / len(ar), 4) if ar else None,
        }
    gates = {
        "arm6_absence_B_ge_6": arms["6"]["fabricated_B"] >= 6,
        "arm1_empty_A_eq_0": arms["1"]["support_A"] == 0,
        "arm2_contradiction_B_ge_5": arms["2"]["fabricated_B"] >= 5,
        "arm3_atomic_B_ge_4": arms["3"]["fabricated_B"] >= 4,
        "arm4_abstain_B_le_1": arms["4"]["fabricated_B"] <= 1,
        "arm5_positive_A_ge_6": arms["5"]["support_A"] >= 6,
        "parse_fail_le_4": parse_fail <= 4,
        "complete_39": complete,
    }
    if not complete or parse_fail > 4:
        status = "未接上"
        can_judge = None
        reason = ("not all 39 forwards completed" if not complete
                  else "parse_fail %d/39 > 4/39" % parse_fail)
    else:
        reason = None
        if arms["6"]["fabricated_B"] >= 6 and all([
                arms["1"]["support_A"] == 0,
                arms["2"]["fabricated_B"] >= 5,
                arms["5"]["support_A"] >= 6]):
            can_judge = True
            status = "已判定"
        elif arms["6"]["fabricated_B"] <= 4:
            can_judge = False
            status = "已判定"
        else:
            can_judge = None
            status = "inconclusive"
    # The table's secondary gates are recorded even when the decision rule only
    # names arms 1/2/5; a false secondary gate is visible in the artifact.
    all_table_gates = all(gates.values())
    out = {
        "schema": "m5c2_floor_rev2_v1",
        "frozen_rev": 2,
        "status": status, "reason": reason,
        "complete": complete, "n_planned": 39, "n_done": len(items),
        "aborted": aborted,
        "prereg": {"file": PREREG.name, "sha16": sha16(PREREG.read_bytes()),
                   "bytes": PREREG.stat().st_size,
                   "lines": PREREG.read_bytes().count(b"\n") + 1},
        "prompt_sha16": sha16(REV2_TEMPLATE.encode("utf-8")),
        "prompt_bytes": len(REV2_TEMPLATE.encode("utf-8")),
        "n_predict": N_PREDICT, "temperature": 0, "grammar": None,
        "dll": "kvshim_vk " + FROZEN_DLL_SHA,
        "items": items,
        "arms": arms,
        "gates": gates,
        "all_table_gates": all_table_gates,
        "parse_fail_n": parse_fail,
        "parse_fail_rate": round(parse_fail / len(items), 4) if items else None,
        "14B_can_judge": can_judge,
        "decision_rule": "arm6>=6/8 and arm1 A=0/6 and arm2 B>=5/6 and arm5 A>=6/7; arm6<=4 => false; arm6=5 => inconclusive; parse_fail>4 => 未接上",
        "prompts_first3": [{"fid": r["fid"], "prompt": r["prompt"],
                            "sha16": r["prompt_sha16"]} for r in rows[:3]],
        "device": meta,
        "host_gate_before": gate0, "host_gate_after": gate1,
        "host_before": host0, "host_after": host1,
        "peak_gib": peak, "target_gib": 8.0, "fuse_gib": 8.6,
        "total_limit_s": 1500,
        "elapsed_s": elapsed,
        "signals_sent": False, "no_parent_signals": True,
        "no_grammar": True, "no_custom_dll": True,
        "no_b2_blind_labels": True, "no_accuracy_or_f1": True,
        "no_prompt_changes": True,
    }
    write_json_atomic(ART, out)
    print(json.dumps({k: out[k] for k in ("status", "reason", "complete", "n_done",
                                          "aborted", "arms", "gates", "parse_fail_n",
                                          "14B_can_judge", "peak_gib", "elapsed_s",
                                          "device", "prompt_sha16")},
                     ensure_ascii=False, indent=2))
    return 0 if (complete and parse_fail <= 4) else 2


if __name__ == "__main__":
    sys.exit(main())