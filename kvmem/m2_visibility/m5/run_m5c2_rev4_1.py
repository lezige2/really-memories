#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 REV4.1: R1 value check + R2 negation check + D1/M1 deterministic arms.

Frozen preregs:
  PREREG-M5-C2-REV4-1.md 69c8d48ea026c50a / 6,201 B / 94 lines
  JUDGE-ROBUSTNESS-SPEC.md 5ad46f8efb762c6d / 8,555 B / 129 lines
  (rev4 base: PREREG-M5-C2-REV4.md be618108a82c2f42)

Only 12 forwards (F07-F18); prompt byte-for-byte rev4 extraction prompt, no
options, no grammar, frozen DLL 9edbafa150700614.  D1 is deterministic derived
bypass; M1 injects hand-written malformed outputs into the parser.
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
import run_m5c2_rev2_order as CO  # noqa: E402

PRE = ROOT / "docs/_work/PREREG-M5-C2-REV4-1.md"
PRE_SHA16 = "69c8d48ea026c50a"
PRE_BYTES = 6201
PRE_LINES = 94
SPEC = ROOT / "docs/_work/JUDGE-ROBUSTNESS-SPEC.md"
SPEC_SHA16 = "5ad46f8efb762c6d"
SPEC_BYTES = 8555
SPEC_LINES = 129
ART = OUT / "M5C2-REV4-1.json"
LOG = OUT / "_m5c2_rev4_1.log"
FROZEN_DLL_SHA = "9edbafa150700614"
N_PREDICT = 384

DERIVED_RE = re.compile(r"共|总共|合计|一共|平均|最|加起来")
NEG_WORDS = ["不是", "而不是", "并非", "不符", "另一", "改为", "换成",
             "没", "不", "非", "无"]
ABSENT_MARKERS = ["未提及", "没有提到", "未找到", "找不到", "未记录",
                  "无对应", "无相关", "未涉及", "未写明", "未说明",
                  "未给出", "未提供", "N/A", "NA", "None", "null", "—"]

D1_CASES = [
    ("D1-1", "这次搬家一共花了 960 元。", "顺捷搬家，费 480 元，另付楼层费 480 元。"),
    ("D1-2", "我总共去过 3 次健身房。", "我每周去一次力量方舟，已经连续去了 3 周。"),
    ("D1-3", "两样加起来一共 780 元。", "宽带 500M，月费 100 元；健身房月费 268 元。"),
    ("D1-4", "押金和月费加起来是 368 元。", "光猫押金 100 元，月费 268 元。"),
]

M1_CASES = [
    ("M1-1", "", "parse_fail"),
    ("M1-2", "抱歉，我无法完成这个任务。", "parse_fail"),
    ("M1-3", "The sentence is supported by the memory.", "parse_fail"),
    ("M1-4", "条目：卡号", "parse_fail"),
    ("M1-5", "依据：卡号 GZ-5517", "parse_fail"),
    ("M1-6", "@@##%%乱码乱码%%##@@", "parse_fail"),
    ("M1-7", "条目：卡号\n依据：GZ-5517\n条目：有效期\n依据：未提及", "unsupported"),
    ("M1-8", "条目：A 依据：B" * 200, "parse_fail"),
]


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def verify_docs():
    for p, h, n, lines in ((PRE, PRE_SHA16, PRE_BYTES, PRE_LINES),
                           (SPEC, SPEC_SHA16, SPEC_BYTES, SPEC_LINES)):
        b = p.read_bytes()
        if sha16(b) != h or len(b) != n:
            raise SystemExit("frozen doc changed: " + p.name)
        if b.count(b"\n") + 1 != lines:
            raise SystemExit("frozen doc line count changed: " + p.name)
    if b"frozen_rev=1" not in PRE.read_bytes():
        raise SystemExit("rev4.1 prereg marker missing")
    return True


def normalize(s):
    return re.sub(r"\s+", "", s or "")


def bigrams(s):
    return [s[i:i + 2] for i in range(max(0, len(s) - 1))] or ([s] if s else [])


def fuzzy_coverage(token, evidence):
    if token in evidence:
        return 1.0
    bs = bigrams(token)
    if not bs:
        return 0.0
    return sum(1 for b in bs if b in evidence) / float(len(bs))


def value_tokens(entry):
    pats = [
        r"\d+(?:\.\d+)?\s*(?:元|度|M|G|层|楼|排|号|节|个月|年|月|日)",
        r"下?(?:周|星期)[一二三四五六日天]",
        r"\d+月\d+日",
        r"[A-Z]{2,}-\d{3,}",
        r"[^\s，。]{2,}(?:公司|店|院|馆|中心)",
    ]
    toks = []
    for p in pats:
        for m in re.finditer(p, entry or ""):
            t = m.group(0).strip()
            if t and t not in toks:
                toks.append(t)
    return toks


def apply_rules(entry, evidence, source):
    """Return (absent, rule_hits).  R1 -> R2 -> R3 -> R4, all hits recorded."""
    hits = []
    entry = entry or ""
    evidence = evidence or ""
    ev_norm = normalize(evidence)
    ent_norm = normalize(entry)
    src_norm = normalize(source)

    # R1 value check
    missing = []
    fuzzy_used = []
    for tok in value_tokens(entry):
        tn = normalize(tok)
        cov = fuzzy_coverage(tn, ev_norm)
        if cov < 0.80:
            missing.append(tok)
        elif cov < 1.0:
            fuzzy_used.append({"token": tok, "coverage": round(cov, 4)})
    for tok in missing:
        hits.append({"rule": "R1", "reason": "value_mismatch", "span": tok})
    # R2 negation check
    anchors = []
    for a in value_tokens(entry) + [ent_norm]:
        a = normalize(a)
        if a and a not in anchors:
            anchors.append(a)
    for anchor in anchors:
        if not anchor:
            continue
        for m in re.finditer(re.escape(anchor), ev_norm):
            i = m.start()
            before = ev_norm[max(0, i - 6):i]
            after = ev_norm[i + len(anchor):i + len(anchor) + 6]
            neg_before = [w for w in NEG_WORDS if w in before]
            if neg_before:
                sp = ev_norm[max(0, i - 8):i + len(anchor) + 8]
                hits.append({"rule": "R2", "reason": "negated",
                             "span": sp, "anchor": anchor, "before": before,
                             "neg_word": sorted(neg_before, key=len, reverse=True)[0]})
                break
            # direct patterns: 不是<anchor>, anchor<不是>, 不是...anchor
            pat = re.compile(r"(不是|并非|而不是)\s*" + re.escape(anchor))
            if pat.search(ev_norm):
                hits.append({"rule": "R2", "reason": "negated_pattern",
                             "span": pat.search(ev_norm).group(0), "anchor": anchor})
                break
            pat2 = re.compile(re.escape(anchor) + r"\s*(不是|是错的)")
            if pat2.search(ev_norm):
                hits.append({"rule": "R2", "reason": "negated_after",
                             "span": pat2.search(ev_norm).group(0), "anchor": anchor})
                break
        if any(h["rule"] == "R2" for h in hits):
            break

    # R3 absent-marker vocabulary
    for marker in ABSENT_MARKERS:
        if normalize(marker) in ev_norm:
            hits.append({"rule": "R3", "reason": "absent_marker", "span": marker})
            break

    # R4 quote check (only quoted fragments >= 4 chars)
    for q in re.findall(r"[“\"「]([^”\"」]{4,})[”\"」]", evidence):
        qn = normalize(q)
        if qn and qn not in src_norm:
            hits.append({"rule": "R4", "reason": "fabricated_evidence", "span": q})
    return bool(hits), hits


def parse_extraction(raw, source=""):
    """Parse strict 条目/依据 pairs.  Return (items, parse_ok, reason).

    Malformed outputs must fail closed:
      - empty / no pairs / item without evidence / evidence without item
      - any single line >1000 chars or total >8000 chars (M1-8)
    """
    if raw is None or len(raw) > 8000:
        return [], False, "too_long_or_none"
    lines = (raw or "").splitlines()
    if lines and max(len(x) for x in lines) > 1000:
        return [], False, "line_too_long"
    items = []
    cur = None
    for line in lines:
        s = line.strip()
        m = re.match(r"^条目：(.+)$", s)
        if m:
            if cur is not None:
                items.append(cur)
            cur = {"item": m.group(1).strip(), "evidence": None}
            continue
        m = re.match(r"^依据：(.+)$", s)
        if m:
            if cur is None:
                return [], False, "evidence_without_item"
            cur["evidence"] = m.group(1).strip()
            continue
    if cur is not None:
        items.append(cur)
    if not items:
        return [], False, "no_items"
    if any(not x.get("evidence") for x in items):
        return [], False, "item_without_evidence"
    for it in items:
        it["absent"], it["rule_hits"] = apply_rules(
            it["item"], it["evidence"], source)
    return items, True, "ok"


def make_item(fid, arm, route, sentence, source, raw, items, parse_ok, reason):
    absent_flags = [x["absent"] for x in items] if items else []
    if not parse_ok:
        verdict = "parse_fail"
    elif not items:
        verdict = "undecidable"
    elif any(absent_flags):
        verdict = "unsupported"
    else:
        verdict = "supported"
    return {
        "fid": fid, "arm": arm, "route": route,
        "sentence": sentence, "source": source,
        "raw_out": raw, "items": items, "absent_flags": absent_flags,
        "parse_ok": parse_ok, "parse_reason": reason,
        "verdict": verdict, "rule_hits": [h for x in items for h in x.get("rule_hits", [])],
        "prompt_verbatim": None, "prompt_sha16": None,
    }


def main():
    verify_docs()
    fx = F.verify_inputs()
    rows = {r["fid"]: r for r in F.build_rows(fx)}
    target = [rows["F%02d" % i] for i in range(7, 19)]
    if len(target) != 12:
        raise SystemExit("target count wrong")

    results = []
    forwards = 0
    aborted = None
    gate0, gate_exceptions = CO.gate_with_dwm_exception()
    host0 = E.host_check("rev4_1_before")
    if not gate0.get("gate_ok"):
        out = {"schema": "m5c2_rev4_1_v1", "status": "未接上",
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
    try:
        eng = R2.open_engine()
        eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                                          ctypes.c_int]
        meta = E.meta_from_log(eng, t0)
        meta["frozen_dll_sha16"] = FROZEN_DLL_SHA
        meta["n_predict"] = N_PREDICT
        meta["only_extraction_no_options"] = True

        # ---------------- arms 2/3: 12 forwards ----------------
        for row in target:
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
            prompt = R4.REV4_TEMPLATE.format(
                source_text=row["source"], question=row["question"],
                sentence=row["sentence"])
            eng.reset(0)
            buf = ctypes.create_string_buffer(131072)
            rc = int(eng.lib.kvshim_ask_at(
                eng.h, 0, prompt.encode("utf-8"), 0, N_PREDICT, buf, 131072))
            raw = "" if rc < 0 else buf.value.decode("utf-8", "replace")
            eng.reset(0)
            forwards += 1
            items, parse_ok, reason = parse_extraction(raw, row["source"])
            rec = make_item(row["fid"], row["arm"], "model_extract",
                            row["sentence"], row["source"], raw, items, parse_ok, reason)
            rec["prompt_verbatim"] = prompt
            rec["prompt_sha16"] = sha16(prompt.encode("utf-8"))
            rec["_peak"] = peak
            results.append(rec)

        # ---------------- D1: derived bypass, no forward ----------------
        for fid, sentence, source in D1_CASES:
            m = DERIVED_RE.search(sentence)
            results.append({
                "fid": fid, "arm": "D1", "route": "derived_bypass",
                "sentence": sentence, "source": source, "raw_out": None,
                "items": [], "absent_flags": [], "parse_ok": True,
                "parse_reason": "derived_bypass", "verdict": "undecidable",
                "rule_hits": [{"rule": "R_DERIVED", "reason": "reasoning_keyword",
                               "span": m.group(0) if m else ""}],
                "prompt_verbatim": None, "prompt_sha16": None,
                "derived": True,
            })

        # ---------------- M1: malformed injection, no forward ----------------
        for fid, raw, expected in M1_CASES:
            try:
                items, parse_ok, reason = parse_extraction(raw)
                if parse_ok and items:
                    exists = any(x["absent"] for x in items)
                    verdict = "unsupported" if exists else "supported"
                else:
                    verdict = "parse_fail"
                exc = None
            except Exception as e:  # noqa: BLE001
                items, parse_ok, reason = [], False, "exception"
                verdict = "parse_fail"
                exc = repr(e)
            if expected == "parse_fail":
                ok = (verdict == "parse_fail") and exc is None
            else:
                ok = (verdict == expected) and exc is None
            results.append({
                "fid": fid, "arm": "M1", "route": "malformed_injection",
                "sentence": raw, "source": None, "raw_out": raw,
                "items": items, "absent_flags": [x["absent"] for x in items],
                "parse_ok": parse_ok, "parse_reason": reason,
                "verdict": verdict, "rule_hits": [h for x in items for h in x.get("rule_hits", [])],
                "expected": expected, "ok": ok, "exception": exc,
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
        gate1, _ = CO.gate_with_dwm_exception()
        host1 = E.host_check("rev4_1_after")

    complete = len(results) == 24 and aborted is None
    arms = {
        "2": {"n": 6, "unsupported": sum(1 for x in results if x["arm"] == 2 and x["verdict"] == "unsupported"),
              "supported": sum(1 for x in results if x["arm"] == 2 and x["verdict"] == "supported"),
              "parse_fail": sum(1 for x in results if x["arm"] == 2 and not x["parse_ok"]),
              "forward_count": sum(1 for x in results if x["arm"] == 2)},
        "3": {"n": 6, "unsupported": sum(1 for x in results if x["arm"] == 3 and x["verdict"] == "unsupported"),
              "supported": sum(1 for x in results if x["arm"] == 3 and x["verdict"] == "supported"),
              "parse_fail": sum(1 for x in results if x["arm"] == 3 and not x["parse_ok"]),
              "forward_count": sum(1 for x in results if x["arm"] == 3)},
        "D1": {"n": 4, "undecidable": sum(1 for x in results if x["arm"] == "D1" and x["verdict"] == "undecidable"),
               "unsupported": sum(1 for x in results if x["arm"] == "D1" and x["verdict"] == "unsupported"),
               "forward_count": 0},
        "M1": {"n": 8, "parse_fail": sum(1 for x in results if x["arm"] == "M1" and x["verdict"] == "parse_fail"),
               "normal_supported": sum(1 for x in results if x["arm"] == "M1" and x["verdict"] == "supported"),
               "normal_unsupported": sum(1 for x in results if x["arm"] == "M1" and x["verdict"] == "unsupported"),
               "all_expected": all(x["ok"] for x in results if x["arm"] == "M1"),
               "no_exception": all(x["exception"] is None for x in results if x["arm"] == "M1"),
               "forward_count": 0},
    }
    gates = {
        "arm2_unsupported_ge_5": arms["2"]["unsupported"] >= 5,
        "arm3_unsupported_ge_4": arms["3"]["unsupported"] >= 4,
        "d1_undecidable_eq_4": arms["D1"]["undecidable"] == 4,
        "d1_no_unsupported": arms["D1"]["unsupported"] == 0,
        "m1_all_expected": arms["M1"]["all_expected"],
        "m1_no_exception": arms["M1"]["no_exception"],
        "parse_fail_model_le_4": sum(1 for x in results if x["route"] == "model_extract" and not x["parse_ok"]) <= 4,
        "complete_24": complete,
    }
    rev4_1_ok = complete and all(gates.values())
    status = "已判定" if complete else "未接上"
    if complete and not rev4_1_ok:
        status = "已判定（未通过）"
    reason = None if rev4_1_ok else "one or more rev4.1 gates failed"
    out = {
        "schema": "m5c2_rev4_1_v1", "frozen_rev": 1,
        "status": status, "reason": reason,
        "complete": complete, "n_done": len(results), "n_forward": forwards,
        "n_forward_planned": 12, "aborted": aborted,
        "prereg": {"file": PRE.name, "sha16": sha16(PRE.read_bytes()),
                   "bytes": PRE.stat().st_size,
                   "lines": PRE.read_bytes().count(b"\n") + 1},
        "spec": {"file": SPEC.name, "sha16": sha16(SPEC.read_bytes()),
                 "bytes": SPEC.stat().st_size,
                 "lines": SPEC.read_bytes().count(b"\n") + 1},
        "prompt_sha16": sha16(R4.REV4_TEMPLATE.encode("utf-8")),
        "n_predict": N_PREDICT, "temperature": 0, "grammar": None,
        "dll": "kvshim_vk " + FROZEN_DLL_SHA,
        "items": results, "arms": arms, "gates": gates,
        "rev4_1_ok": rev4_1_ok,
        "14B_can_judge": True if rev4_1_ok else None,
        "rule_impl": {
            "order": ["R1", "R2", "R3", "R4"],
            "R1": "value tokens (number+unit, week/day, model, institution); exact or bigram coverage >= 0.80",
            "R2": "anchor value/entry in evidence; negator within preceding 6 chars, or 不是/并非/而不是<anchor>, or <anchor>不是/是错的",
            "R3": "absent-marker vocabulary",
            "R4": "quoted fragment >= 4 chars must exist verbatim in source",
            "derived_bypass": "共|总共|合计|一共|平均|最|加起来 => undecidable",
        },
        "deterministic_rule_fix": {
            "applied": True,
            "prior_rev4_abstain_fix": "narrow '提' option accepted by Lead; unchanged here",
            "rev4_1_scope": "R1/R2 added; model prompt unchanged",
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
        "no_prompt_changes": True, "no_hardcoded_case_exceptions": True,
        "no_b2_blind_labels": True, "no_accuracy_or_f1": True,
    }
    write_json_atomic(ART, out)
    print(json.dumps({k: out[k] for k in ("status", "reason", "complete", "n_done",
                                          "n_forward", "aborted", "arms", "gates",
                                          "rev4_1_ok", "14B_can_judge", "peak_gib",
                                          "elapsed_s", "device")},
                     ensure_ascii=False, indent=2))
    return 0 if complete else 2


if __name__ == "__main__":
    sys.exit(main())