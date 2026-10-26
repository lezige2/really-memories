#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B2EVAL: read 106 sentences (71 support + 35 fabricated) through the
full rev4.1 three-layer judge.  Read-only measurement, NOT acceptance.

Frozen prereg: docs/_work/PREREG-M5-C2-B2EVAL.md 6b0d750abbd06b1b / 4,113 B / 75 lines
Prompt: rev4 extraction prompt, sha16 must be a6bc4f268f7711de.
Safety: 8.0 target / 8.6 fuse / <=1500 s / dwm narrow exception recorded.
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
import run_m5c2_rev4 as R4  # noqa: E402
import run_m5c2_rev4_1 as R41  # noqa: E402
import run_m5c2_rev2_order as CO  # noqa: E402

PRE = ROOT / "docs/_work/PREREG-M5-C2-B2EVAL.md"
PRE_SHA16 = "6b0d750abbd06b1b"
PRE_BYTES = 4113
PRE_LINES = 75
SENT = OUT / "M5B2-SENTENCES.json"
SENT_SHA16 = "6529e151568dc593"
SENT_BYTES = 78825
FIX = OUT / "M5B2-fixture.json"
ADJ = OUT / "M5B2-adj-labels.json"
REV = OUT / "M5B2-review-labels.json"
LEAD = OUT / "M5B2-LEAD-RULING.json"
ART = OUT / "M5C2-B2EVAL.json"
LOG = OUT / "_m5c2_b2eval.log"
FROZEN_DLL_SHA = "9edbafa150700614"
N_PREDICT = 384
PROMPT_SHA = "a6bc4f268f7711de"


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / float(n)
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(max(0.0, center - half), 6), round(min(1.0, center + half), 6)]


def verify_prereg():
    b = PRE.read_bytes()
    if sha16(b) != PRE_SHA16 or len(b) != PRE_BYTES:
        raise SystemExit("B2EVAL prereg changed")
    if b.count(b"\n") + 1 != PRE_LINES:
        raise SystemExit("B2EVAL prereg line count changed")
    if b"not_acceptance=true" not in b:
        raise SystemExit("B2EVAL marker missing")
    sb = SENT.read_bytes()
    if sha16(sb) != SENT_SHA16 or len(sb) != SENT_BYTES:
        raise SystemExit("B2 sentences changed")
    return True


def load_inputs():
    sent = json.load(open(SENT, encoding="utf-8-sig"))["sentences"]
    fx = json.load(open(FIX, encoding="utf-8-sig"))["scenarios"]
    src = {s["id"]: s["source_text"] for s in fx}
    q = {}
    for s in fx:
        for x in s["questions"]:
            q[x["qid"]] = x["text"]
    adj = {x["sid"]: x["label"] for x in json.load(open(ADJ, encoding="utf-8-sig"))["labels"]}
    rev = {x["sid"]: x["label"] for x in json.load(open(REV, encoding="utf-8-sig"))["labels"]}
    lead = json.load(open(LEAD, encoding="utf-8-sig"))["rulings"]
    # Gold = agreement of the two blinded labels; Lead ruling resolves disagreements.
    gold = {}
    for sid in adj:
        gold[sid] = lead.get(sid) or adj[sid]
    return sent, src, q, gold, adj, rev, lead


def template_of(text):
    if "打包纸箱" in text:
        return "打包纸箱"
    if "身份证" in text and "学员卡" in text:
        return "材料清单"
    if "教练姓张" in text:
        return "教练姓张"
    if "天气" in text:
        return "天气"
    return None


def main():
    verify_prereg()
    sent, src, qtext, gold, adj, rev, lead = load_inputs()
    from collections import Counter
    gold_counts = Counter(gold.values())
    if gold_counts["support_present"] != 71 or gold_counts["fabricated"] != 35:
        raise SystemExit("gold counts mismatch: %r" % (gold_counts,))
    chosen = [x for x in sent if gold[x["sid"]] in ("support_present", "fabricated")]
    chosen.sort(key=lambda x: x["sid"])
    if len(chosen) != 106:
        raise SystemExit("expected 106 chosen, got %d" % len(chosen))

    gate0, gate_exceptions = CO.gate_with_dwm_exception()
    host0 = E.host_check("b2eval_before")
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_b2eval_v1", "status": "未接上",
               "reason": "host gate failed before load",
               "in_sample_for_leak_templates": True,
               "clean_for_false_rate": True, "not_acceptance": True,
               "host_gate_before": gate0, "gate_exceptions": gate_exceptions,
               "host_before": host0, "no_model_loaded": True,
               "signals_sent": False}
        write_json_atomic(ART, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    sampler = F.start_sampler()
    t0 = time.perf_counter()
    eng = None
    meta = {}
    results = []
    forwards = 0
    aborted = None
    try:
        eng = R2.open_engine()
        eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int]
        meta = E.meta_from_log(eng, t0)
        meta["frozen_dll_sha16"] = FROZEN_DLL_SHA
        meta["n_predict"] = N_PREDICT
        meta["only_extraction_no_options"] = True

        for x in chosen:
            if time.perf_counter() - t0 > 1500:
                aborted = "timeout >1500s"
                break
            try:
                peak = round(float(F.PEAK.read_text().strip()) / (1024 ** 3), 4)
            except Exception:  # noqa: BLE001
                peak = None
            if peak is not None and peak > 8.6:
                aborted = "VRAM fuse: peak %.4f > 8.6 GiB" % peak
                break
            sid = x["sid"]
            sentence = x["text"]
            source = src[x["scenario"]]
            question = qtext[x["qid"]]
            g = gold[sid]
            rec = {"sid": sid, "gold": g, "scenario": x["scenario"],
                   "qid": x["qid"], "sentence": sentence, "source": source,
                   "question": question, "route": None, "raw_out": None,
                   "items": [], "rule_hits": [], "verdict": None,
                   "parse_ok": False, "parse_reason": None, "derived": False}
            # layer 0
            if source.strip() == "":
                rec["route"] = "empty_source"
                rec["verdict"] = "unsupported"
                rec["parse_ok"] = True
                results.append(rec)
                continue
            if re.search(R4.ABSTAIN_REGEX_EFFECTIVE, sentence):
                det = R4.deterministic_abstain(sentence, source)
                rec["route"] = "abstain_check"
                rec["verdict"] = det["verdict"]
                rec["parse_ok"] = True
                rec["abstain"] = det
                results.append(rec)
                continue
            # layer 1: one extraction forward for every non-layer-0 sentence
            prompt = R4.REV4_TEMPLATE.format(
                source_text=source, question=question, sentence=sentence)
            rec["prompt_sha16"] = sha16(prompt.encode("utf-8"))
            eng.reset(0)
            buf = ctypes.create_string_buffer(131072)
            rc = int(eng.lib.kvshim_ask_at(
                eng.h, 0, prompt.encode("utf-8"), 0, N_PREDICT, buf, 131072))
            raw = "" if rc < 0 else buf.value.decode("utf-8", "replace")
            eng.reset(0)
            forwards += 1
            rec["route"] = "model_extract"
            rec["raw_out"] = raw
            items, parse_ok, reason = R41.parse_extraction(raw, source)
            rec["items"] = items
            rec["parse_ok"] = parse_ok
            rec["parse_reason"] = reason
            rec["rule_hits"] = [h for z in items for h in z.get("rule_hits", [])]
            derived = bool(R41.DERIVED_RE.search(sentence))
            rec["derived"] = derived
            if derived:
                rec["rule_hits"].append({"rule": "R_DERIVED",
                                         "reason": "reasoning_keyword",
                                         "span": (R41.DERIVED_RE.search(sentence).group(0)
                                                  if R41.DERIVED_RE.search(sentence) else "")})
            if not parse_ok:
                rec["verdict"] = "parse_fail"
            elif derived:
                rec["verdict"] = "undecidable"
            elif not items:
                rec["verdict"] = "undecidable"
            elif any(z["absent"] for z in items):
                rec["verdict"] = "unsupported"
            else:
                rec["verdict"] = "supported"
            rec["peak_gib_running"] = peak
            results.append(rec)
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
        host1 = E.host_check("b2eval_after")

    # Persist raw results before building the summary artifact, so a summary-side
    # bug cannot destroy a 106-forward run again.
    try:
        write_json_atomic(OUT / "_m5c2_b2eval_raw.json", {
            "results": results, "n_done": len(results), "n_forward": forwards,
            "aborted": aborted, "elapsed_s": elapsed, "peak_gib": peak,
            "device": meta, "gate_before": gate0, "gate_after": gate1,
            "gate_exceptions": gate_exceptions, "host_before": host0,
            "host_after": host1,
        })
    except Exception as e:  # noqa: BLE001
        print("raw checkpoint failed: %r" % (e,), file=sys.stderr)

    complete = len(results) == 106 and aborted is None
    by_gold = {
        "support_present": [x for x in results if x["gold"] == "support_present"],
        "fabricated": [x for x in results if x["gold"] == "fabricated"],
    }
    supp = by_gold["support_present"]
    fab = by_gold["fabricated"]
    leak = [x for x in fab if x["verdict"] in ("supported", "undecidable")]
    false = [x for x in supp if x["verdict"] == "unsupported"]
    any_non = [x for x in supp if x["verdict"] in ("unsupported", "undecidable")]
    strict_leak = [x for x in fab if x["verdict"] == "supported"]
    parse_fail_rows = [x for x in results if x["verdict"] == "parse_fail"]
    abstain_rows = [x for x in results if x["route"] == "abstain_check"]
    abstain_ok = [x for x in abstain_rows if x["verdict"] == "abstain_ok"]
    abstain_wrong = [x for x in abstain_rows if x["verdict"] == "abstain_wrong"]
    derived_rows = [x for x in results if x.get("derived")]

    rates = {
        "leak": {"numerator": len(leak), "denominator": len(fab),
                 "rate": round(len(leak) / len(fab), 4) if fab else None,
                 "wilson95": wilson(len(leak), len(fab))},
        "false": {"numerator": len(false), "denominator": len(supp),
                  "rate": round(len(false) / len(supp), 4) if supp else None,
                  "wilson95": wilson(len(false), len(supp))},
        "any_non_supported_false": {
            "numerator": len(any_non), "denominator": len(supp),
            "rate": round(len(any_non) / len(supp), 4) if supp else None,
            "wilson95": wilson(len(any_non), len(supp))},
        "strict_leak": {"numerator": len(strict_leak), "denominator": len(fab),
                        "rate": round(len(strict_leak) / len(fab), 4) if fab else None,
                        "wilson95": wilson(len(strict_leak), len(fab))},
        "parse_fail": {"numerator": len(parse_fail_rows), "denominator": len(results),
                       "rate": round(len(parse_fail_rows) / len(results), 4) if results else None,
                       "wilson95": wilson(len(parse_fail_rows), len(results))},
    }
    groups = {}
    for name in ("打包纸箱", "材料清单", "教练姓张", "天气"):
        gs = [x for x in fab if template_of(x["sentence"]) == name]
        gl = [x for x in gs if x["verdict"] in ("supported", "undecidable")]
        gc = [x for x in gs if x["verdict"] == "unsupported"]
        groups[name] = {"n": len(gs), "leaked": len(gl), "caught": len(gc),
                        "sids_leaked": [x["sid"] for x in gl],
                        "sids_caught": [x["sid"] for x in gc]}
    out = {
        "schema": "m5c2_b2eval_v1", "status": "已读数" if complete else "未接上",
        "in_sample_for_leak_templates": True,
        "clean_for_false_rate": True,
        "not_acceptance": True,
        "cov_note": "只覆盖 assertion 子集 264 句中的 106 句；no_fact 385 句未测",
        "complete": complete, "n_done": len(results), "n_planned": 106,
        "n_forward": forwards, "n_forward_planned": 106, "aborted": aborted,
        "prereg": {"file": PRE.name, "sha16": sha16(PRE.read_bytes()),
                   "bytes": PRE.stat().st_size,
                   "lines": PRE.read_bytes().count(b"\n") + 1},
        "inputs": {"sentences_sha16": sha16(SENT.read_bytes()),
                   "sentences_bytes": SENT.stat().st_size,
                   "fixture": FIX.name, "gold": LEAD.name,
                   "gold_counts": dict(gold_counts)},
        "gold_resolution": {
            "method": "adj==review agreement; LEAD-RULING overrides the 10 disagreements",
            "disagreements_n": len([s for s in adj if adj[s] != rev[s]]),
            "lead_rulings_n": len(lead),
        },
        "prompt_sha16": PROMPT_SHA,
        "actual_prompt_sha16": sha16(R4.REV4_TEMPLATE.encode("utf-8")),
        "prompt_matches_frozen": sha16(R4.REV4_TEMPLATE.encode("utf-8")) == PROMPT_SHA,
        "n_predict": N_PREDICT, "temperature": 0, "grammar": None,
        "dll": "kvshim_vk " + FROZEN_DLL_SHA,
        "rates": rates,
        "leak_rows": [x["sid"] for x in leak],
        "false_rows": [x["sid"] for x in false],
        "any_non_supported_false_rows": [x["sid"] for x in any_non],
        "strict_leak_rows": [x["sid"] for x in strict_leak],
        "parse_fail_rows": [x["sid"] for x in parse_fail_rows],
        "abstain": {"route_n": len(abstain_rows), "abstain_ok": len(abstain_ok),
                    "abstain_wrong": len(abstain_wrong),
                    "sids": [x["sid"] for x in abstain_rows]},
        "derived": {"n": len(derived_rows), "sids": [x["sid"] for x in derived_rows]},
        "template_leak_groups": groups,
        "reference": {"v2_4_leak": {"numerator": 14, "denominator": 35, "rate": 0.4},
                      "v2_4_false": {"numerator": 10, "denominator": 71, "rate": 0.1408}},
        "items": results,
        "device": meta,
        "host_gate_before": gate0, "host_gate_after": gate1,
        "gate_exceptions": gate_exceptions,
        "host_before": host0, "host_after": host1,
        "peak_gib": peak, "target_gib": 8.0, "fuse_gib": 8.6,
        "limit_s": 1500, "elapsed_s": elapsed,
        "signals_sent": False, "no_parent_signals": True,
        "no_grammar": True, "no_custom_dll": True,
        "no_options": True, "no_prompt_changes": True,
        "no_rule_changes": True, "no_threshold_changes": True,
        "no_tuning_from_this_run": True,
        "no_acceptance_verdict": True,
        "no_accuracy_or_f1": True,
    }
    write_json_atomic(ART, out)
    print(json.dumps({k: out[k] for k in ("status", "complete", "n_done", "n_forward",
                                          "aborted", "rates", "leak_rows", "false_rows",
                                          "any_non_supported_false_rows",
                                          "strict_leak_rows", "parse_fail_rows",
                                          "abstain", "derived", "template_leak_groups",
                                          "peak_gib", "elapsed_s", "gate_exceptions",
                                          "device")},
                     ensure_ascii=False, indent=2))
    return 0 if complete else 2


if __name__ == "__main__":
    sys.exit(main())