#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""One-process runner: FLOOR REV2 (39) then ORDER (36), same engine/DLL.

Frozen preregs:
  PREREG-M5-C2-FLOOR-REV2.md 54faca9edb3a8daf / 6,173 B / 92 lines
  PREREG-M5-C2-ORDER.md      fb0da1b792004fa2 / 5,453 B / 96 lines

Both use the frozen DLL only (kvshim_vk 9edbafa150700614), no grammar,
n_predict=384, temperature=0.  The model is loaded once and closed only after
both batches, satisfying the same-session/same-DLL requirement.
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
import run_m5c2_floor_rev2 as R2V  # noqa: E402

REV2_ART = OUT / "M5C2-FLOOR-REV2.json"
ORDER_ART = OUT / "M5C2-ORDER.json"
LOG = OUT / "_m5c2_rev2_order.log"
FROZEN_DLL_SHA = "9edbafa150700614"
N_PREDICT = 384
ORDER_PREREG = ROOT / "docs/_work/PREREG-M5-C2-ORDER.md"
ORDER_SHA16 = "fb0da1b792004fa2"
ORDER_BYTES = 5453
ORDER_LINES = 96

ORDER_TEMPLATE = """下面是一段用户的记忆记录：
【记忆】{source_text}

用户曾问过：{question}
助手在回答里写了这一句：
【待判句子】{sentence}

请按这个顺序做两件事：
第一步：逐条列出【待判句子】里的具体信息（数字、日期、名称、地点、价格、型号、清单、承诺、属性等），并说明每一条在【记忆】里有没有对应的原文依据。如果没有依据，就写"【记忆】未提及"。
第二步：根据第一步的结论，在最后一行单独写结论，只能从下面三个词里选一个：
{ORDER_BLOCK}
最后一行格式：结论：<三个词之一>"""

ORDER_BLOCKS = {
    "O1": ("支持   = 每个具体信息都能在【记忆】里找到依据\n"
           "编造   = 至少有一个具体信息在【记忆】里找不到，或与【记忆】矛盾\n"
           "无法判断 = 句子被截断、指代不明，无法确定它在主张什么"),
    "O2": ("无法判断 = 句子被截断、指代不明，无法确定它在主张什么\n"
           "编造   = 至少有一个具体信息在【记忆】里找不到，或与【记忆】矛盾\n"
           "支持   = 每个具体信息都能在【记忆】里找到依据"),
    "O3": ("编造   = 至少有一个具体信息在【记忆】里找不到，或与【记忆】矛盾\n"
           "支持   = 每个具体信息都能在【记忆】里找到依据\n"
           "无法判断 = 句子被截断、指代不明，无法确定它在主张什么"),
}
FIRST_LISTED = {"O1": "支持", "O2": "无法判断", "O3": "编造"}

# oid, source fid, arm name, expected (support / fabricated / non-support / non-fabricated)
ORDER_CASES = [
    ("O-01", "F32", "absence", "编造"),
    ("O-02", "F33", "absence", "编造"),
    ("O-03", "F35", "absence", "编造"),
    ("O-04", "F39", "absence", "编造"),
    ("O-05", "F07", "contradiction", "编造"),
    ("O-06", "F09", "contradiction", "编造"),
    ("O-07", "F17", "atomic", "编造"),
    ("O-08", "F25", "positive", "支持"),
    ("O-09", "F27", "positive", "支持"),
    ("O-10", "F31", "positive", "支持"),
    ("O-11", "F01", "empty", "非支持"),
    ("O-12", "F19", "abstain", "非编造"),
]


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def verify_order_prereg():
    b = ORDER_PREREG.read_bytes()
    if sha16(b) != ORDER_SHA16 or len(b) != ORDER_BYTES:
        raise SystemExit("ORDER prereg changed")
    if b.count(b"\n") + 1 != ORDER_LINES:
        raise SystemExit("ORDER prereg line count changed")
    if b"frozen_rev=1" not in b:
        raise SystemExit("ORDER prereg missing frozen_rev=1")
    return b


def gate_with_dwm_exception():
    """Host gate with the Lead-authorized single-name dwm.exe exception.

    Only a lone dwm.exe above 256 MiB is tolerated.  The raw bytes and the
    unmodified decision booleans are retained.  Any non-dwm process above
    256 MiB, or any detail/count ambiguity, still fails closed.
    """
    g = R2.host_gate()
    exceptions = []
    if not g.get("gpu_procs_ok"):
        details = g.get("gpu_proc_details") or []
        parsed = []
        for d in details:
            m = re.search(r"NAME=(\S+)\s+BYTES=(\d+)", str(d))
            if m:
                parsed.append((m.group(1), int(m.group(2))))
        count = int(g.get("gpu_procs_gt256mb") or 0)
        other_ok = all(bool(g.get(k)) for k in (
            "prereg_ok", "free_ram_ok", "vram_baseline_ok",
            "boot_id_ok", "dll_ok", "model_ok"))
        baseline_ok = float(g.get("vram_baseline_gib") or 999) <= 1.5
        # Exact name only; no wildcard/extension expansion.
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
            g = dict(g)
            g["gate_ok_raw"] = g.get("gate_ok")
            g["gpu_procs_ok_raw"] = g.get("gpu_procs_ok")
            g["gate_ok"] = True
            g["gpu_procs_ok"] = True
            g["gate_exception_applied"] = True
            g["gate_exceptions"] = exceptions
    return g, exceptions


def summarize(items):
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
    parse_fail = sum(1 for x in items if not x["parse_ok"])
    gates = {
        "arm6_absence_B_ge_6": arms["6"]["fabricated_B"] >= 6,
        "arm1_empty_A_eq_0": arms["1"]["support_A"] == 0,
        "arm2_contradiction_B_ge_5": arms["2"]["fabricated_B"] >= 5,
        "arm3_atomic_B_ge_4": arms["3"]["fabricated_B"] >= 4,
        "arm4_abstain_B_le_1": arms["4"]["fabricated_B"] <= 1,
        "arm5_positive_A_ge_6": arms["5"]["support_A"] >= 6,
        "parse_fail_le_4": parse_fail <= 4,
    }
    return arms, gates, parse_fail


def run_one(eng, prompt):
    buf = ctypes.create_string_buffer(131072)
    n = int(eng.lib.kvshim_ask_at(eng.h, 0, prompt.encode("utf-8"), 0,
                                  N_PREDICT, buf, 131072))
    raw = "" if n < 0 else buf.value.decode("utf-8", "replace")
    return raw, n


def make_rev2_item(row, raw, rc, peak):
    word, mode, line, markers = R2V.parse_conclusion(raw)
    verdict = {"支持": "supported", "编造": "unsupported",
               "无法判断": "undecidable"}.get(word)
    if verdict is None:
        verdict = "parse_fail"
    return {
        "fid": row["fid"], "arm": row["arm"], "arm_name": row["arm_name"],
        "qid": row["qid"], "question": row["question"], "sentence": row["sentence"],
        "source": row["source"], "prompt_verbatim": row["prompt"],
        "prompt_sha16": row["prompt_sha16"],
        "raw_out": raw, "raw_bytes": len(raw.encode("utf-8")),
        "conclusion_line": line, "parsed_word": word, "verdict": verdict,
        "parse_mode": mode, "parse_ok": word is not None,
        "conclusion_markers": markers,
        "step1_unmentioned_lines": R2V.unmentioned_lines(raw),
        "rc": rc, "peak_gib_running": peak,
    }


def make_order_item(oid, src_fid, arm, order, source, question, sentence, raw, rc, peak):
    word, mode, line, _ = R2V.parse_conclusion(raw)
    verdict = {"支持": "supported", "编造": "unsupported",
               "无法判断": "undecidable"}.get(word)
    if verdict is None:
        verdict = "parse_fail"
    prompt = ORDER_TEMPLATE.format(
        source_text=source, question=question, sentence=sentence,
        ORDER_BLOCK=ORDER_BLOCKS[order])
    first = FIRST_LISTED[order]
    return {
        "oid": oid, "src_fid": src_fid, "arm": arm, "order": order,
        "first_listed": first, "question": question,
        "source": source, "sentence": sentence,
        "prompt_verbatim": prompt, "prompt_sha16": sha16(prompt.encode("utf-8")),
        "raw_out": raw, "raw_bytes": len(raw.encode("utf-8")),
        "conclusion_line": line, "parsed_word": word, "verdict": verdict,
        "parse_mode": mode, "parse_ok": word is not None,
        "hits_first_listed": (word == first),
        "rc": rc, "peak_gib_running": peak,
    }


def main():
    R2V.verify_prereg()
    verify_order_prereg()
    fx = F.verify_inputs()
    rev2_rows = R2V.build_rows(fx)
    by_id = {r["fid"]: r for r in rev2_rows}

    gate0, gate_exceptions = gate_with_dwm_exception()
    host0 = E.host_check("rev2_order_before")
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_floor_rev2_v1", "status": "未接上",
               "reason": "host gate failed before load", "host_gate_before": gate0,
               "host_before": host0, "no_model_loaded": True, "signals_sent": False}
        write_json_atomic(REV2_ART, out)
        write_json_atomic(ORDER_ART, {"schema": "m5c2_order_v1", "status": "未运行",
                                      "reason": "rev2 gate failed", "signals_sent": False})
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    sampler = F.start_sampler()
    t0 = time.perf_counter()
    eng = None
    meta = {}
    rev2_items = []
    rev2_aborted = None
    try:
        eng = R2.open_engine()
        eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int]
        meta = E.meta_from_log(eng, t0)
        meta["frozen_dll_sha16"] = FROZEN_DLL_SHA
        meta["n_predict"] = N_PREDICT
        meta["grammar"] = None
        meta["one_load_two_batches"] = True

        # ---------------- REV2: 39 forwards ----------------
        for i, r in enumerate(rev2_rows):
            if time.perf_counter() - t0 > 1500:
                rev2_aborted = "rev2 segment timeout >1500s"
                break
            try:
                peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
            except Exception:  # noqa: BLE001
                peak = None
            if peak is not None and peak > 8.6:
                rev2_aborted = "VRAM fuse: peak %.4f > 8.6 GiB" % peak
                break
            eng.reset(0)
            raw, rc = run_one(eng, r["prompt"])
            eng.reset(0)
            rev2_items.append(make_rev2_item(r, raw, rc, peak))
        rev2_elapsed = round(time.perf_counter() - t0, 1)
        rev2_peak = None
        try:
            rev2_peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
        except Exception:  # noqa: BLE001
            pass
        rev2_gate_after, _ = gate_with_dwm_exception()
        rev2_host_after = E.host_check("floor_rev2_after")

        rev2_complete = len(rev2_items) == 39 and rev2_aborted is None
        arms, gates, parse_fail = summarize(rev2_items)
        if not rev2_complete or parse_fail > 4:
            rev2_status = "未接上"
            rev2_reason = ("not all 39 forwards completed" if not rev2_complete
                           else "parse_fail %d/39 > 4/39" % parse_fail)
            can_judge = None
        else:
            rev2_reason = None
            if arms["6"]["fabricated_B"] >= 6 and all([
                    arms["1"]["support_A"] == 0,
                    arms["2"]["fabricated_B"] >= 5,
                    arms["5"]["support_A"] >= 6]):
                can_judge = True
                rev2_status = "已判定"
            elif arms["6"]["fabricated_B"] <= 4:
                can_judge = False
                rev2_status = "已判定"
            else:
                can_judge = None
                rev2_status = "inconclusive"
        rev2_out = {
            "schema": "m5c2_floor_rev2_v1", "frozen_rev": 2,
            "status": rev2_status, "reason": rev2_reason,
            "complete": rev2_complete, "n_planned": 39, "n_done": len(rev2_items),
            "aborted": rev2_aborted,
            "prereg": {"file": R2V.PREREG.name,
                       "sha16": sha16(R2V.PREREG.read_bytes()),
                       "bytes": R2V.PREREG.stat().st_size,
                       "lines": R2V.PREREG.read_bytes().count(b"\n") + 1},
            "prompt_sha16": sha16(R2V.REV2_TEMPLATE.encode("utf-8")),
            "prompt_bytes": len(R2V.REV2_TEMPLATE.encode("utf-8")),
            "n_predict": N_PREDICT, "temperature": 0, "grammar": None,
            "dll": "kvshim_vk " + FROZEN_DLL_SHA,
            "items": rev2_items, "arms": arms, "gates": gates,
            "all_table_gates": all(gates.values()),
            "parse_fail_n": parse_fail,
            "parse_fail_rate": round(parse_fail / len(rev2_items), 4) if rev2_items else None,
            "14B_can_judge": can_judge,
            "decision_rule": "arm6>=6/8 and arm1 A=0/6 and arm2 B>=5/6 and arm5 A>=6/7; arm6<=4 => false; arm6=5 => inconclusive; parse_fail>4 => 未接上",
            "prompts_first3": [{"fid": r["fid"], "prompt": r["prompt"],
                                "sha16": r["prompt_sha16"]} for r in rev2_rows[:3]],
            "device": meta,
            "host_gate_before": gate0, "host_gate_after": rev2_gate_after,
            "gate_exceptions": gate_exceptions,
            "host_before": host0, "host_after": rev2_host_after,
            "peak_gib": rev2_peak, "target_gib": 8.0, "fuse_gib": 8.6,
            "total_limit_s": 1500, "elapsed_s": rev2_elapsed,
            "signals_sent": False, "no_parent_signals": True,
            "no_grammar": True, "no_custom_dll": True,
            "no_b2_blind_labels": True, "no_accuracy_or_f1": True,
            "no_prompt_changes": True,
        }
        write_json_atomic(REV2_ART, rev2_out)
        print("REV2 " + json.dumps({k: rev2_out[k] for k in
                                    ("status", "reason", "complete", "n_done", "aborted",
                                     "arms", "gates", "parse_fail_n", "14B_can_judge",
                                     "peak_gib", "elapsed_s")}, ensure_ascii=False))
        sys.stdout.flush()

        # Stop before rev3 on the Lead's explicit safety rule.
        if not rev2_complete or parse_fail > 4:
            write_json_atomic(ORDER_ART, {
                "schema": "m5c2_order_v1", "status": "未运行",
                "reason": "rev2 failed: " + str(rev2_reason),
                "rev2_status": rev2_status, "rev2_sha16": sha16(REV2_ART.read_bytes()),
                "signals_sent": False})
            return 2

        # ---------------- ORDER rev3: 12 x 3 = 36 forwards ----------------
        order_items = []
        order_aborted = None
        for oid, src_fid, arm, expected in ORDER_CASES:
            row = by_id[src_fid]
            for order in ("O1", "O2", "O3"):
                if time.perf_counter() - t0 > 1500 + 1200:
                    order_aborted = "ORDER segment timeout >1200s after rev2"
                    break
                try:
                    peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
                except Exception:  # noqa: BLE001
                    peak = None
                if peak is not None and peak > 8.6:
                    order_aborted = "VRAM fuse: peak %.4f > 8.6 GiB" % peak
                    break
                eng.reset(0)
                prompt = ORDER_TEMPLATE.format(
                    source_text=row["source"], question=row["question"],
                    sentence=row["sentence"], ORDER_BLOCK=ORDER_BLOCKS[order])
                raw, rc = run_one(eng, prompt)
                eng.reset(0)
                it = make_order_item(oid, src_fid, arm, order, row["source"],
                                     row["question"], row["sentence"], raw, rc, peak)
                it["expected"] = expected
                if expected == "编造":
                    it["correct"] = it["parsed_word"] == "编造"
                elif expected == "支持":
                    it["correct"] = it["parsed_word"] == "支持"
                elif expected == "非支持":
                    it["correct"] = it["parsed_word"] in ("编造", "无法判断")
                elif expected == "非编造":
                    it["correct"] = it["parsed_word"] in ("支持", "无法判断")
                else:
                    it["correct"] = False
                order_items.append(it)
            if order_aborted:
                break
    except Exception as e:  # noqa: BLE001
        rev2_aborted = rev2_aborted or ("exception: %r" % (e,))
        order_aborted = "exception: %r" % (e,)
    finally:
        if eng is not None:
            try:
                eng.close()
            except Exception:  # noqa: BLE001
                pass
        time.sleep(0.5)
        final_peak = F.stop_sampler(sampler)
        total_elapsed = round(time.perf_counter() - t0, 1)
        gate1, _ = gate_with_dwm_exception()
        host1 = E.host_check("rev2_order_after")

    # ---------------- ORDER metrics ----------------
    order_complete = len(order_items) == 36 and order_aborted is None
    order_parse_fail = sum(1 for x in order_items if not x["parse_ok"])
    by_order = {}
    for order in ("O1", "O2", "O3"):
        ar = [x for x in order_items if x["order"] == order]
        correct = sum(1 for x in ar if x["correct"])
        by_order[order] = {
            "first_listed": FIRST_LISTED[order],
            "n": len(ar), "correct": correct,
            "correct_rate": round(correct / len(ar), 4) if ar else None,
            "hits_first_listed": sum(1 for x in ar if x["hits_first_listed"]),
        }
    consistency_examples = []
    for oid, _, _, _ in ORDER_CASES:
        words = [x["parsed_word"] for x in order_items if x["oid"] == oid]
        ok = len(words) == 3 and len(set(words)) == 1 and words[0] is not None
        consistency_examples.append({"oid": oid, "words": words, "consistent": ok})
    consistency_n = sum(1 for x in consistency_examples if x["consistent"])
    trap_n = sum(1 for x in order_items if x["hits_first_listed"])
    spread = None
    if all(x["correct_rate"] is not None for x in by_order.values()):
        rates = [x["correct_rate"] for x in by_order.values()]
        spread = round(max(rates) - min(rates), 4)
    if not order_complete or order_parse_fail > 4:
        order_status = "未接上"
        order_robust = None
        order_reason = ("not all 36 forwards completed" if not order_complete
                        else "parse_fail %d/36 > 4/36" % order_parse_fail)
    elif trap_n > 12 or (spread is not None and spread > (2.0 / 12.0)):
        order_status = "已判定"
        order_robust = False
        order_reason = "first_listed_trap>12/36 or order_spread>2/12"
    elif consistency_n < 10:
        order_status = "inconclusive"
        order_robust = None
        order_reason = "consistency<10/12"
    else:
        order_status = "已判定"
        order_robust = True
        order_reason = None
    rev2_valid = (True if order_robust is True else (False if order_robust is False else None))
    order_out = {
        "schema": "m5c2_order_v1", "frozen_rev": 1,
        "status": order_status, "reason": order_reason,
        "complete": order_complete, "n_planned": 36, "n_done": len(order_items),
        "aborted": order_aborted,
        "prereg": {"file": ORDER_PREREG.name, "sha16": sha16(ORDER_PREREG.read_bytes()),
                   "bytes": ORDER_PREREG.stat().st_size,
                   "lines": ORDER_PREREG.read_bytes().count(b"\n") + 1},
        "n_predict": N_PREDICT, "temperature": 0, "grammar": None,
        "dll": "kvshim_vk " + FROZEN_DLL_SHA,
        "items": order_items,
        "orders": by_order,
        "consistency": {"n_consistent": consistency_n, "total": 12,
                        "rate": round(consistency_n / 12.0, 4),
                        "examples": consistency_examples},
        "first_listed_trap": {"hits": trap_n, "total": len(order_items),
                              "rate": round(trap_n / len(order_items), 4) if order_items else None},
        "order_spread": spread,
        "parse_fail_n": order_parse_fail,
        "parse_fail_rate": round(order_parse_fail / len(order_items), 4) if order_items else None,
        "order_robust": order_robust,
        "rev2_valid": rev2_valid,
        "rev2_sha16": sha16(REV2_ART.read_bytes()) if REV2_ART.exists() else None,
        "rev2_status": rev2_status,
        "rev2_14B_can_judge": can_judge,
        "device": meta,
        "host_gate_before": gate0, "host_gate_after": gate1,
        "gate_exceptions": gate_exceptions,
        "host_before": host0, "host_after": host1,
        "peak_gib": final_peak, "target_gib": 8.0, "fuse_gib": 8.6,
        "total_limit_s": 1200,
        "elapsed_s": total_elapsed,
        "signals_sent": False, "no_parent_signals": True,
        "no_grammar": True, "no_custom_dll": True,
        "no_b2_blind_labels": True, "no_accuracy_or_f1": True,
        "same_session_same_dll": True,
    }
    write_json_atomic(ORDER_ART, order_out)
    print("ORDER " + json.dumps({k: order_out[k] for k in
                                 ("status", "reason", "complete", "n_done", "aborted",
                                  "orders", "consistency", "first_listed_trap",
                                  "order_spread", "parse_fail_n", "order_robust",
                                  "rev2_valid", "peak_gib", "elapsed_s",
                                  "same_session_same_dll")}, ensure_ascii=False))
    return 0 if order_complete else 2


if __name__ == "__main__":
    sys.exit(main())