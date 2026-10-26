#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 REV4: extractive protocol, 39 cases / 27 forwards.

Frozen prereg: docs/_work/PREREG-M5-C2-REV4.md
  sha16 be618108a82c2f42 / 6,996 B / 125 lines / frozen_rev=1

Layer 0 (no model): empty source -> unsupported; abstain sentences -> string
check -> abstain_ok / abstain_wrong.
Layer 1 (one forward): model only extracts 条目/依据 pairs; no options, no
verdict, no grammar, frozen DLL 9edbafa150700614.
Layer 2 (no model): any 未提及 -> unsupported; all evidence -> supported;
no items -> undecidable.

NOTE on a frozen-rule defect found before the run: the prereg abstain regex
"(没有|未|无从).{0,6}(提到|提及|记录|说明)" does not match F20-F24, whose
sentences say "没有提..." (no 到).  The Lead's §3 says a layer-0 failure is a
rule error to fix and rerun.  A single narrow alternative "提" is added only for
abstain routing; the trigger is recorded in artifact.deterministic_rule_fix.
The model prompt is unchanged.
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
import run_m5c2_rev2_order as CO  # noqa: E402

PREREG = ROOT / "docs/_work/PREREG-M5-C2-REV4.md"
PREREG_SHA16 = "be618108a82c2f42"
PREREG_BYTES = 6996
PREREG_LINES = 125
ART = OUT / "M5C2-REV4.json"
LOG = OUT / "_m5c2_rev4.log"
FROZEN_DLL_SHA = "9edbafa150700614"
N_PREDICT = 384

REV4_TEMPLATE = """下面是一段用户的记忆记录：
【记忆】{source_text}

用户曾问过：{question}
助手在回答里写了这一句：
【待判句子】{sentence}

请只做抽取，不要下任何结论、不要评价真伪。把【待判句子】里的每一个具体信息（数字、日期、名称、地点、价格、型号、清单、承诺、属性等）单独列成一行，每行格式严格如下：
条目：<该信息在句子里的原文>
依据：<【记忆】里与之对应的原文片段；如果【记忆】里没有对应内容，就写 未提及>

注意：只列【待判句子】里真正出现的信息，不要替它补全；条目至少 1 条，最多 12 条。"""

ABSTAIN_REGEX_PREREG = r"(没有|未|无从).{0,6}(提到|提及|记录|说明)"
ABSTAIN_REGEX_EFFECTIVE = r"(没有|未|无从).{0,6}(提到|提及|提|记录|说明)"
STOPWORDS = ("记忆里", "记录里", "记忆", "记录", "里面", "之中",
             "没有提到", "没有提及", "没有提", "未提到", "未提及",
             "没有记录", "未记录", "找不到", "不知道", "不确定",
             "无法提供", "的", "是", "有", "吗", "呢")


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
        raise SystemExit("rev4 prereg changed")
    if b.count(b"\n") + 1 != PREREG_LINES:
        raise SystemExit("rev4 prereg line count changed")
    if b"frozen_rev=1" not in b or "抽取式判据".encode("utf-8") not in b:
        raise SystemExit("rev4 prereg marker missing")
    return b


def abstain_objects(sentence):
    t = sentence
    for w in STOPWORDS:
        t = t.replace(w, "")
    parts = [p.strip() for p in re.split(r"[，。！？；、,;!?\s]+", t) if p.strip()]
    return [p for p in parts if len(p) >= 2]


def deterministic_abstain(sentence, source):
    objs = abstain_objects(sentence)
    hits = [o for o in objs if o in (source or "")]
    verdict = "abstain_wrong" if hits else "abstain_ok"
    return {
        "object_terms": objs,
        "hits_in_source": hits,
        "verdict": verdict,
        "abstain_ok": verdict == "abstain_ok",
    }


def parse_extraction(raw):
    items = []
    cur = None
    for line in (raw or "").splitlines():
        s = line.strip()
        m = re.match(r"^条目：(.+)$", s)
        if m:
            if cur is not None:
                items.append(cur)
            cur = {"item": m.group(1).strip(), "evidence": None}
            continue
        m = re.match(r"^依据：(.+)$", s)
        if m and cur is not None:
            cur["evidence"] = m.group(1).strip()
            continue
    if cur is not None:
        items.append(cur)
    for it in items:
        ev = it.get("evidence") or ""
        it["absent"] = any(tok in ev for tok in ("未提及", "没有", "未找到", "找不到"))
    return items


def main():
    verify_prereg()
    fx = F.verify_inputs()
    rev1_rows = F.build_rows(fx)
    by_id = {r["fid"]: r for r in rev1_rows}
    # Arm 6 from the frozen rev2 rows; reuse source/question/sentence exactly.
    rev2_rows = R2V.build_rows(fx)
    for r in rev2_rows:
        if r["arm"] == 6:
            by_id[r["fid"]] = r
    rows = []
    for fid in ["F%02d" % i for i in range(1, 40)]:
        if fid not in by_id:
            raise SystemExit("missing row " + fid)
        rows.append(by_id[fid])
    if len(rows) != 39:
        raise SystemExit("expected 39 rows, got %d" % len(rows))

    gate0, gate_exceptions = CO.gate_with_dwm_exception()
    host0 = E.host_check("rev4_before")
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_rev4_v1", "status": "未接上",
               "reason": "host gate failed before load", "host_gate_before": gate0,
               "gate_exceptions": gate_exceptions, "host_before": host0,
               "no_model_loaded": True, "signals_sent": False}
        write_json_atomic(ART, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    sampler = F.start_sampler()
    t0 = time.perf_counter()
    eng = None
    meta = {}
    items_out = []
    aborted = None
    forward_count = 0
    try:
        eng = R2.open_engine()
        eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int]
        meta = E.meta_from_log(eng, t0)
        meta["frozen_dll_sha16"] = FROZEN_DLL_SHA
        meta["n_predict"] = N_PREDICT
        meta["grammar"] = None
        meta["only_extraction_no_options"] = True

        for row in rows:
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
            src = row["source"] or ""
            sent = row["sentence"]
            rec = {
                "fid": row["fid"], "arm": row["arm"], "arm_name": row["arm_name"],
                "qid": row["qid"], "question": row["question"], "sentence": sent,
                "source": src, "route": None,
                "prompt_verbatim": None, "prompt_sha16": None,
                "raw_out": None, "items": [], "absent_flags": [],
                "verdict": None, "parse_ok": False, "parse_mode": None,
                "deterministic": None, "rc": None, "peak_gib_running": peak,
            }
            # ---- layer 0 ----
            if src.strip() == "":
                rec["route"] = "empty_source"
                rec["verdict"] = "unsupported"
                rec["parse_ok"] = True
                rec["parse_mode"] = "deterministic"
                rec["deterministic"] = {"rule": "empty_source", "source_is_empty": True}
                items_out.append(rec)
                continue
            if re.search(ABSTAIN_REGEX_EFFECTIVE, sent):
                det = deterministic_abstain(sent, src)
                rec["route"] = "abstain_check"
                rec["verdict"] = det["verdict"]
                rec["parse_ok"] = True
                rec["parse_mode"] = "deterministic"
                rec["deterministic"] = det
                items_out.append(rec)
                continue
            # ---- layer 1: only extraction ----
            prompt = REV4_TEMPLATE.format(source_text=src, question=row["question"],
                                          sentence=sent)
            rec["route"] = "model_extract"
            rec["prompt_verbatim"] = prompt
            rec["prompt_sha16"] = sha16(prompt.encode("utf-8"))
            eng.reset(0)
            buf = ctypes.create_string_buffer(131072)
            rc = int(eng.lib.kvshim_ask_at(
                eng.h, 0, prompt.encode("utf-8"), 0, N_PREDICT, buf, 131072))
            raw = "" if rc < 0 else buf.value.decode("utf-8", "replace")
            eng.reset(0)
            forward_count += 1
            parsed = parse_extraction(raw)
            absent_flags = [x["absent"] for x in parsed]
            if not parsed:
                verdict = "undecidable"
                parse_ok = False
                parse_mode = "parse_fail"
            elif any(absent_flags):
                verdict = "unsupported"
                parse_ok = True
                parse_mode = "items"
            else:
                verdict = "supported"
                parse_ok = True
                parse_mode = "items"
            rec.update({
                "raw_out": raw, "raw_bytes": len(raw.encode("utf-8")),
                "items": parsed, "absent_flags": absent_flags,
                "verdict": verdict, "parse_ok": parse_ok, "parse_mode": parse_mode,
                "rc": rc,
            })
            items_out.append(rec)
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
        gate1, _ = CO.gate_with_dwm_exception()
        host1 = E.host_check("rev4_after")

    complete = len(items_out) == 39 and aborted is None
    parse_fail = sum(1 for x in items_out if not x["parse_ok"])
    arms = {}
    for a in (1, 2, 3, 4, 5, 6):
        ar = [x for x in items_out if x["arm"] == a]
        arms[str(a)] = {
            "n": len(ar),
            "supported": sum(1 for x in ar if x["verdict"] == "supported"),
            "unsupported": sum(1 for x in ar if x["verdict"] == "unsupported"),
            "undecidable": sum(1 for x in ar if x["verdict"] == "undecidable"),
            "abstain_ok": sum(1 for x in ar if x["verdict"] == "abstain_ok"),
            "abstain_wrong": sum(1 for x in ar if x["verdict"] == "abstain_wrong"),
            "parse_fail": sum(1 for x in ar if not x["parse_ok"]),
            "forward_count": sum(1 for x in ar if x["route"] == "model_extract"),
        }
    gates = {
        "arm6_unsupported_ge_6": arms["6"]["unsupported"] >= 6,
        "arm1_unsupported_eq_6": arms["1"]["unsupported"] == 6,
        "arm4_abstain_ok_eq_6": arms["4"]["abstain_ok"] == 6,
        "arm2_unsupported_ge_5": arms["2"]["unsupported"] >= 5,
        "arm3_unsupported_ge_4": arms["3"]["unsupported"] >= 4,
        "arm5_supported_ge_6": arms["5"]["supported"] >= 6,
        "parse_fail_le_4": parse_fail <= 4,
        "complete_39": complete,
    }
    if not complete or parse_fail > 4:
        status = "未接上"
        rev4_arch_ok = None
        can_judge = None
        reason = ("not all 39 cases completed" if not complete
                  else "parse_fail %d/39 > 4/39" % parse_fail)
    else:
        reason = None
        layer0_ok = arms["1"]["unsupported"] == 6 and arms["4"]["abstain_ok"] == 6
        if all(gates.values()):
            status = "已判定"
            rev4_arch_ok = True
            can_judge = True
        elif arms["6"]["unsupported"] <= 4:
            status = "已判定"
            rev4_arch_ok = False
            can_judge = False
        elif arms["6"]["unsupported"] == 5:
            status = "inconclusive"
            rev4_arch_ok = False
            can_judge = None
        elif not layer0_ok:
            status = "规则错误"
            rev4_arch_ok = False
            can_judge = None
        else:
            status = "已判定"
            rev4_arch_ok = False
            can_judge = None
    out = {
        "schema": "m5c2_rev4_v1", "frozen_rev": 1,
        "status": status, "reason": reason,
        "complete": complete, "n_planned": 39, "n_done": len(items_out),
        "n_forward": forward_count, "n_forward_planned": 27,
        "aborted": aborted,
        "prereg": {"file": PREREG.name, "sha16": sha16(PREREG.read_bytes()),
                   "bytes": PREREG.stat().st_size,
                   "lines": PREREG.read_bytes().count(b"\n") + 1},
        "prompt_sha16": sha16(REV4_TEMPLATE.encode("utf-8")),
        "prompt_bytes": len(REV4_TEMPLATE.encode("utf-8")),
        "n_predict": N_PREDICT, "temperature": 0, "grammar": None,
        "dll": "kvshim_vk " + FROZEN_DLL_SHA,
        "route_counts": {
            "empty_source": sum(1 for x in items_out if x["route"] == "empty_source"),
            "abstain_check": sum(1 for x in items_out if x["route"] == "abstain_check"),
            "model_extract": sum(1 for x in items_out if x["route"] == "model_extract"),
        },
        "items": items_out, "arms": arms, "gates": gates,
        "parse_fail_n": parse_fail,
        "parse_fail_rate": round(parse_fail / len(items_out), 4) if items_out else None,
        "rev4_arch_ok": rev4_arch_ok,
        "14B_can_judge": can_judge,
        "decision_rule": "six gates all pass => rev4_arch_ok=true; arm6<=4 => false; arm6=5 => inconclusive; parse_fail>4 => 未接上",
        "prompts_first3": [{"fid": x["fid"], "prompt": x["prompt_verbatim"],
                            "sha16": x["prompt_sha16"]}
                           for x in items_out if x["route"] == "model_extract"][:3],
        "deterministic_rule_fix": {
            "applied": True,
            "reason": "Prereg abstain regex (没有|未|无从).{0,6}(提到|提及|记录|说明) does not match F20-F24, whose sentences say '没有提' without '到'; layer-0 would send them to the model, violating the frozen arm4=6/6 deterministic requirement.",
            "regex_prereg": ABSTAIN_REGEX_PREREG,
            "regex_effective": ABSTAIN_REGEX_EFFECTIVE,
            "scope": "abstain routing only; model prompt unchanged; no other rule changed",
        },
        "device": meta,
        "host_gate_before": gate0, "host_gate_after": gate1,
        "gate_exceptions": gate_exceptions,
        "host_before": host0, "host_after": host1,
        "peak_gib": peak, "target_gib": 8.0, "fuse_gib": 8.6,
        "total_limit_s": 900, "elapsed_s": elapsed,
        "signals_sent": False, "no_parent_signals": True,
        "no_grammar": True, "no_custom_dll": True,
        "no_options": True, "no_verdict_prompt": True,
        "no_b2_blind_labels": True, "no_accuracy_or_f1": True,
        "no_prompt_changes": True,
    }
    write_json_atomic(ART, out)
    print(json.dumps({k: out[k] for k in ("status", "reason", "complete", "n_done",
                                          "n_forward", "aborted", "route_counts",
                                          "arms", "gates", "parse_fail_n",
                                          "rev4_arch_ok", "14B_can_judge",
                                          "peak_gib", "elapsed_s", "device",
                                          "deterministic_rule_fix")},
                     ensure_ascii=False, indent=2))
    return 0 if complete else 2


if __name__ == "__main__":
    sys.exit(main())