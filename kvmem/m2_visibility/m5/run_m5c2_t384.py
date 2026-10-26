#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 T384: 10-case free-reasoning diagnostic (n_predict=384, no grammar).

Prompt is the Lead's corrected "T" version: explain the evidence in one
sentence, then put the final standalone line as A/B/C.  Ten cases:
  G1..G5 = contradiction-injection F07..F11
  G6..G10 = obvious-negative O1..O5

Frozen DLL only: kvshim_vk 9edbafa150700614.  No grammar, no custom DLL.
Artifact: m5/out/M5C2-T384.json
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

ART = OUT / "M5C2-T384.json"
LOG = OUT / "_m5c2_t384.log"
FROZEN_DLL_SHA = "9edbafa150700614"

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


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def parse_last_standalone_letter(raw):
    """Last line that consists of a single A/B/C (allow common markdown trim)."""
    lines = [x.strip() for x in (raw or "").splitlines() if x.strip()]
    for line in reversed(lines):
        m = re.fullmatch(r"[\s*_`>#\-]*([ABC])[\s*_`。.]*", line)
        if m:
            return m.group(1), line
    return None, (lines[-1] if lines else None)


def main():
    fx = F.verify_inputs()
    rows = F.build_rows(fx)
    by_id = {r["fid"]: r for r in rows}
    cases = []
    for fid in ["F07", "F08", "F09", "F10", "F11"]:
        r = by_id[fid]
        cases.append({
            "aid": "G%d" % (len(cases) + 1), "group": "contradiction", "fid": fid,
            "source": r["source"], "question": r["question"], "sentence": r["sentence"],
        })
    for i, (src, sent) in enumerate(O_CASES, 1):
        cases.append({
            "aid": "G%d" % (len(cases) + 1), "group": "obvious_negative", "fid": "O%d" % i,
            "source": src, "question": "这句话有依据吗？", "sentence": sent,
        })
    for c in cases:
        c["prompt_verbatim"] = T_TEMPLATE.format(
            source_text=c["source"], question=c["question"], sentence=c["sentence"])
        c["prompt_sha16"] = sha16(c["prompt_verbatim"].encode("utf-8"))

    gate0 = R2.host_gate()
    host0 = E.host_check("t384_before")
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_t384_v1", "status": "未接上",
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
        meta["n_predict"] = 384
        for it in cases:
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
            buf = ctypes.create_string_buffer(131072)
            n = int(eng.lib.kvshim_ask_at(
                eng.h, 0, it["prompt_verbatim"].encode("utf-8"), 0, 384, buf, 131072))
            raw = "" if n < 0 else buf.value.decode("utf-8", "replace")
            eng.reset(0)
            parsed, last_line = parse_last_standalone_letter(raw)
            rec = dict(it)
            rec.update({
                "raw_out": raw, "raw_bytes": len(raw.encode("utf-8")),
                "last_nonempty_line": last_line,
                "parsed": parsed, "parse_ok": parsed is not None,
                "dll": "kvshim_vk " + FROZEN_DLL_SHA,
                "grammar": None, "n_predict": 384, "rc": n,
                "peak_gib_running": peak,
            })
            items.append(rec)
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
        host1 = E.host_check("t384_after")

    complete = len(items) == 10 and aborted is None
    counts = {"A": sum(1 for x in items if x["parsed"] == "A"),
              "B": sum(1 for x in items if x["parsed"] == "B"),
              "C": sum(1 for x in items if x["parsed"] == "C"),
              "parse_fail": sum(1 for x in items if x["parsed"] is None)}
    if counts["B"] >= 8:
        protocol_was_the_problem = True
        can_judge = True
        conclusion = "protocol_was_the_problem=true; capability present; rev2 full FLOOR warranted"
    elif counts["B"] <= 4:
        protocol_was_the_problem = False
        can_judge = False
        conclusion = "14B_can_judge=false; 14B extractor only"
    else:
        protocol_was_the_problem = None
        can_judge = None
        conclusion = "inconclusive; 4 < B < 8"
    out = {
        "schema": "m5c2_t384_v1",
        "status": "完成" if complete else "未接上",
        "complete": complete, "n_planned": 10, "n_done": len(items),
        "aborted": aborted,
        "prereg": {"file": F.FLOOR_PREREG.name, "sha16": sha16(F.FLOOR_PREREG.read_bytes()),
                   "bytes": F.FLOOR_PREREG.stat().st_size},
        "prompt_prereg": {"file": F.R2_PREREG.name,
                          "sha16": sha16(F.R2_PREREG.read_bytes()),
                          "bytes": F.R2_PREREG.stat().st_size},
        "prompt_template": "Lead T arm: explain, then final standalone A/B/C",
        "n_predict": 384, "grammar": None,
        "dll": "kvshim_vk " + FROZEN_DLL_SHA,
        "items": items,
        "counts": counts,
        "protocol_was_the_problem": protocol_was_the_problem,
        "14B_can_judge": can_judge,
        "conclusion": conclusion,
        "device": meta,
        "host_gate_before": gate0, "host_gate_after": gate1,
        "host_before": host0, "host_after": host1,
        "peak_gib": peak, "target_gib": 8.0, "fuse_gib": 8.6,
        "elapsed_s": elapsed, "segment_limit_s": 900,
        "signals_sent": False, "no_parent_signals": True,
        "no_b2_blind_labels": True, "no_accuracy_or_f1": True,
        "no_grammar": True, "no_custom_dll": True,
    }
    write_json_atomic(ART, out)
    print(json.dumps({k: out[k] for k in ("status", "complete", "n_done", "aborted",
                                          "counts", "protocol_was_the_problem",
                                          "14B_can_judge", "conclusion", "peak_gib",
                                          "elapsed_s", "device")},
                     ensure_ascii=False, indent=2))
    return 0 if complete else 2


if __name__ == "__main__":
    sys.exit(main())