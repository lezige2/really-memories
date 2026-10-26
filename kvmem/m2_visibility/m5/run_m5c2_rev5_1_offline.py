#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 REV5.1 offline: only R4+ short-evidence metric changed.

Short evidence (normalized length <= 4) uses max character-set Jaccard >= 0.80
against same-length source windows.  Longer evidence keeps bigram coverage.
R1/R2/R3/R_DERIVED+ unchanged.  Zero GPU, zero forwards; reuses B2 items.

Output: m5/out/M5C2-REV5-1-OFFLINE.json
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
sys.path.insert(0, str(M5))
import run_m5c2_rev5_offline as R5  # noqa: E402

B2 = OUT / "M5C2-B2EVAL.json"
B2_SHA16 = "553a96fc481fcf9c"
REV5 = OUT / "M5C2-REV5-OFFLINE.json"
REV5_SHA16 = "f304690658cb328d"
ART = OUT / "M5C2-REV5-1-OFFLINE.json"
PROMPT_SHA = "a6bc4f268f7711de"


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def norm(s):
    return re.sub(r"\s+", "", s or "")


def char_jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / float(len(sa | sb))


def max_window_jaccard(ev, src):
    if not ev or not src:
        return 0.0
    if ev in src:
        return 1.0
    L = len(ev)
    if L > len(src):
        return char_jaccard(ev, src)
    best = 0.0
    for i in range(0, len(src) - L + 1):
        j = char_jaccard(ev, src[i:i + L])
        if j > best:
            best = j
            if best >= 0.999:
                break
    return best


def r4_plus_v51(evidence, source, has_r3):
    """R4+ with short-evidence char Jaccard (<=4) and long bigram coverage."""
    if has_r3:
        return None
    ev = norm(evidence)
    src = norm(source)
    if not ev:
        return {"rule": "R4+", "reason": "fabricated_evidence",
                "span": "(empty)", "metric": "empty", "jaccard_or_bigram": 0.0}
    if ev in src:
        return None
    if len(ev) <= 4:
        j = max_window_jaccard(ev, src)
        if j >= 0.80:
            return None
        return {"rule": "R4+", "reason": "fabricated_evidence",
                "span": evidence, "metric": "char_jaccard",
                "jaccard_or_bigram": round(j, 6)}
    cov = R5.window_coverage(ev, src)
    if cov >= 0.80:
        return None
    return {"rule": "R4+", "reason": "fabricated_evidence",
            "span": evidence, "metric": "bigram",
            "jaccard_or_bigram": round(cov, 6)}


def judge_items(items, source):
    out = []
    for it in items:
        entry = it.get("item", "")
        evidence = it.get("evidence", "")
        hits, r3 = R5.r1_r2_r3(entry, evidence)
        r4 = r4_plus_v51(evidence, source, r3 is not None)
        if r4:
            hits.append(r4)
        out.append({"item": entry, "evidence": evidence,
                    "absent": bool(hits), "rule_hits": hits,
                    "r3_hit": r3 is not None})
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / float(n)
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(max(0.0, center - half), 6), round(min(1.0, center + half), 6)]


def rate(k, n):
    return {"numerator": k, "denominator": n,
            "rate": round(k / n, 4) if n else None,
            "wilson95": wilson(k, n)}


def main():
    bb = B2.read_bytes()
    if sha16(bb) != B2_SHA16:
        raise SystemExit("B2 input changed")
    rb = REV5.read_bytes()
    if sha16(rb) != REV5_SHA16:
        raise SystemExit("rev5 input changed")
    b2 = json.loads(bb.decode("utf-8"))
    rev5 = json.loads(rb.decode("utf-8"))
    old_by_sid = {x["sid"]: x for x in rev5["items"] if x["sid"].startswith("S")}
    if len(old_by_sid) != 106:
        raise SystemExit("expected 106 rev5 B2 rows")

    rows = []
    for it in b2["items"]:
        sid = it["sid"]
        src = it["source"]
        sent = it["sentence"]
        old5 = old_by_sid[sid]["verdict_new"]
        old_b2 = it["verdict"]
        items_new = judge_items(it["items"], src)
        en, dd = R5.derived_plus(sent, src)
        if not it["parse_ok"]:
            newv = "parse_fail"
        elif en:
            newv = "undecidable"
        elif not items_new:
            newv = "undecidable"
        elif any(z["absent"] for z in items_new):
            newv = "unsupported"
        else:
            newv = "supported"
        rec = {
            "sid": sid, "gold": it["gold"], "sentence": sent, "source": src,
            "verdict_b2": old_b2, "verdict_old": old5, "verdict_new": newv,
            "items": items_new,
            "rule_hits": [h for z in items_new for h in z["rule_hits"]],
            "derived_plus": dd,
            "template": R5.template_of(sent),
            "parse_ok": it["parse_ok"],
            "changed_vs_rev5": old5 != newv,
        }
        if en:
            rec["rule_hits"].append({"rule": "R_DERIVED+",
                                     "reason": "all_values_composable",
                                     "span": dd.get("keyword", "")})
        rows.append(rec)

    supp = [x for x in rows if x["gold"] == "support_present"]
    fab = [x for x in rows if x["gold"] == "fabricated"]
    leak = [x for x in fab if x["verdict_new"] in ("supported", "undecidable")]
    false = [x for x in supp if x["verdict_new"] == "unsupported"]
    any_non = [x for x in supp if x["verdict_new"] in ("unsupported", "undecidable")]
    strict = [x for x in fab if x["verdict_new"] == "supported"]
    pf = [x for x in rows if x["verdict_new"] == "parse_fail"]

    groups = {}
    for name in ("打包纸箱", "材料清单", "教练姓张", "天气"):
        gs = [x for x in fab if x["template"] == name]
        gl = [x for x in gs if x["verdict_new"] in ("supported", "undecidable")]
        gc = [x for x in gs if x["verdict_new"] == "unsupported"]
        groups[name] = {"n": len(gs), "leaked": len(gl), "caught": len(gc),
                        "leaked_sids": [x["sid"] for x in gl],
                        "caught_sids": [x["sid"] for x in gc]}

    s0095 = next(x for x in rows if x["sid"] == "S0095")
    pack_examples = [x for x in rows if x["sid"] == "S0211"]
    # Measure the two named evidence strings explicitly.
    s_src = s0095["source"]
    p_src = pack_examples[0]["source"]
    metric_examples = {
        "S0095_带宽": {
            "evidence": "带宽", "source": s_src,
            "jaccard": round(max_window_jaccard("带宽", norm(s_src)), 6),
            "old_bigram": round(R5.window_coverage("带宽", norm(s_src)), 6),
            "decision_new": ("present" if max_window_jaccard("带宽", norm(s_src)) >= 0.80
                             else "absent"),
            "decision_old": ("present" if R5.window_coverage("带宽", norm(s_src)) >= 0.80
                             else "absent"),
        },
        "S0095_办理": {
            "evidence": "办理", "source": s_src,
            "jaccard": round(max_window_jaccard("办理", norm(s_src)), 6),
            "old_bigram": round(R5.window_coverage("办理", norm(s_src)), 6),
            "decision_new": ("present" if max_window_jaccard("办理", norm(s_src)) >= 0.80
                             else "absent"),
        },
        "打包纸箱": {
            "evidence": "打包纸箱", "source": p_src,
            "jaccard": round(max_window_jaccard("打包纸箱", norm(p_src)), 6),
            "old_bigram": round(R5.window_coverage("打包纸箱", norm(p_src)), 6),
            "decision_new": ("present" if max_window_jaccard("打包纸箱", norm(p_src)) >= 0.80
                             else "absent"),
            "decision_old": ("present" if R5.window_coverage("打包纸箱", norm(p_src)) >= 0.80
                             else "absent"),
        },
    }

    out = {
        "schema": "m5c2_rev5_1_offline_v1",
        "status": "已读数",
        "rules_version": "R4+/R_DERIVED+",
        "short_evidence_metric": "char_jaccard_0.80_le4",
        "reused_model_output": True,
        "n_forward": 0,
        "n_forward_planned": 0,
        "repeated_look_at_b2": True,
        "b2_look_number": 3,
        "in_sample_for_leak_templates": True,
        "not_acceptance": True,
        "b2_input": {"file": B2.name, "sha16": sha16(bb), "bytes": len(bb)},
        "rev5_input": {"file": REV5.name, "sha16": sha16(rb), "bytes": len(rb)},
        "prompt_sha16": PROMPT_SHA,
        "n_b2": len(rows), "n_done": len(rows),
        "rates": {
            "old_rev5": {
                "leak": rate(0, 35),
                "false": rate(9, 71),
                "strict_leak": rate(0, 35),
            },
            "new_rev5_1": {
                "leak": rate(len(leak), 35),
                "false": rate(len(false), 71),
                "any_non_supported_false": rate(len(any_non), 71),
                "strict_leak": rate(len(strict), 35),
                "parse_fail": rate(len(pf), 106),
            },
        },
        "leak_rows_new": [x["sid"] for x in leak],
        "false_rows_new": [x["sid"] for x in false],
        "any_non_supported_false_rows_new": [x["sid"] for x in any_non],
        "strict_leak_rows_new": [x["sid"] for x in strict],
        "parse_fail_rows_new": [x["sid"] for x in pf],
        "false_delta_vs_rev5": len(false) - 9,
        "leak_delta_vs_rev5": len(leak) - 0,
        "rev5_1_ok": (len(leak) == 0 and len(false) == 8),
        "checks": {
            "leak_eq_0": len(leak) == 0,
            "false_eq_8": len(false) == 8,
            "packing_caught_9": groups["打包纸箱"]["caught"] == 9,
            "s0095_supported": s0095["verdict_new"] == "supported",
            "no_forward": True,
        },
        "template_groups": groups,
        "metric_comparison": metric_examples,
        "s0095": {
            "sid": "S0095", "sentence": s0095["sentence"],
            "verdict_b2": s0095["verdict_b2"],
            "verdict_old": s0095["verdict_old"],
            "verdict_new": s0095["verdict_new"],
            "changed_vs_rev5": s0095["changed_vs_rev5"],
            "items": s0095["items"],
            "rule_hits": s0095["rule_hits"],
        },
        "items": rows,
        "d1_from_rev5": rev5.get("d1", []),
        "no_gpu": True, "signals_sent": False,
        "no_model_call": True,
        "no_prompt_change": True,
        "no_r1_r2_r3_change": True,
        "no_derived_change": True,
        "no_sid_special_cases": True,
        "no_threshold_change": True,
        "no_acceptance_verdict": True,
    }
    write_json_atomic(ART, out)
    print(json.dumps({k: out[k] for k in ("status", "short_evidence_metric",
                                          "n_forward", "n_done", "rates",
                                          "leak_rows_new", "false_rows_new",
                                          "rev5_1_ok", "checks", "template_groups",
                                          "metric_comparison", "s0095")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())