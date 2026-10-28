# -*- coding: utf-8 -*-
"""SFT 微调前后对比评测（方案见 out/SFT-EVAL-PLAN.md；GO 后运行）。

输入（默认路径可 CLI 覆盖）：
  out/SFT-EVAL-81.json       微调后同一套 81 条（run_training_eval --hermetic 产出）
  out/TRAINING-EVAL-v10.json 基线（81/81，冻结）
  out/SFT-HELDOUT-EVAL.json  微调后 held-out 92 条（run_heldout.py 产出另存）
  out/HELDOUT-EVAL-baseline-<sha>.json  基线 held-out（GO 前复制保存）
  out/SFT-EXTRA-EVAL.json    微调后 20 条新增（长对话/记忆召回 10 + 拒答诚实 10）
输出：out/SFT-COMPARE.json
判定口径：沿用 v4 语义判据（pass 字段已由 runner/heldout judge 计算）；逐例只比
「pass/refused/state_class/blocks_present」与“是否满足同一 expect”，不比对措辞；
答案文本差异全部记录但不计 FAIL（SFT 会改变措辞）。FAIL 触发：回退
（基线 pass→微调 fail）、hard 六条 fail、held-out 回退、额外套件低于阈值。
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "out"
DEFAULT = {
    "post81": OUT / "SFT-EVAL-81.json",
    "base81": OUT / "TRAINING-EVAL-v10.json",
    "post_heldout": OUT / "SFT-HELDOUT-EVAL.json",
    "base_heldout": OUT / "HELDOUT-EVAL.json",
    "extra": OUT / "SFT-EXTRA-EVAL.json",
    "out": OUT / "SFT-COMPARE.json",
}
HARD_SIX = ["h02", "h03", "m02", "m03", "s03", "u05"]
HARD_EXTRA = ["h01"]
THINK = re.compile(r"<\|?/?\s*think\s*\|?>", re.I)


def sha(p):
    b = Path(p).read_bytes()
    return {"path": str(p), "bytes": len(b),
            "sha256": hashlib.sha256(b).hexdigest(),
            "sha16": hashlib.sha256(b).hexdigest()[:16]}


def norm_answer(a):
    a = THINK.sub("", str(a or ""))
    return re.sub(r"\s+", "", a).strip("。！？!?；;，,、 ")


def state_class(r):
    a = r.get("actual") or {}
    if a.get("refused"):
        return "no_evidence"
    st = str(a.get("state") or "")
    if st in ("identity", "capability", "smalltalk", "ack", "web"):
        return st
    if a.get("block_ids"):
        return "memory_hit"
    return "general"


def load_results(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    return d, {r["id"]: r for r in d.get("results") or []}


def compare81(base_doc, base, post_doc, post):
    ids = sorted(set(base) & set(post))
    regressions, improvements, stable, text_diffs = [], [], 0, 0
    for cid in ids:
        b, q = base[cid], post[cid]
        bp, qp = bool(b.get("pass")), bool(q.get("pass"))
        ba, qa = b.get("actual") or {}, q.get("actual") or {}
        fields = {"refused": (bool(ba.get("refused")), bool(qa.get("refused"))),
                  "state_class": (state_class(b), state_class(q)),
                  "blocks_present": (bool(ba.get("block_ids")), bool(qa.get("block_ids")))}
        struct_changed = {k: {"base": v[0], "post": v[1]}
                          for k, v in fields.items() if v[0] != v[1]}
        if bp and not qp:
            regressions.append({"id": cid, "category": q.get("category"),
                                "input": q.get("input"), "why": q.get("failure_class"),
                                "problems": q.get("problems"),
                                "base_answer": str(ba.get("answer") or "")[:200],
                                "post_answer": str(qa.get("answer") or "")[:200],
                                "struct_changed": struct_changed})
        elif not bp and qp:
            improvements.append({"id": cid, "category": q.get("category")})
        else:
            stable += 1
        if norm_answer(ba.get("answer")) != norm_answer(qa.get("answer")):
            text_diffs += 1
    hard_fail = [cid for cid in HARD_SIX + HARD_EXTRA
                 if cid in post and not post[cid].get("pass")]
    post_pass = sum(1 for cid in ids if post[cid].get("pass"))
    base_pass = sum(1 for cid in ids if base[cid].get("pass"))
    gate = "FAIL"
    if not regressions and not hard_fail and post_pass == len(ids):
        gate = "PASS"
    elif len(regressions) <= 1 and not hard_fail and post_pass == len(ids) - len(regressions):
        gate = "PASS_WITH_NOTES"
    return {"n": len(ids), "base_pass": base_pass, "post_pass": post_pass,
            "stable": stable, "regressions": regressions,
            "improvements": improvements, "hard_fail": hard_fail,
            "answer_text_diff_n": text_diffs, "verdict": gate}


def compare_heldout(base_p, post_p):
    bd = json.loads(Path(base_p).read_text(encoding="utf-8"))
    pd = json.loads(Path(post_p).read_text(encoding="utf-8"))
    base = {r["id"]: r for r in bd.get("rows") or []}
    post = {r["id"]: r for r in pd.get("rows") or []}
    ids = sorted(set(base) & set(post))
    regressions, improvements = [], []
    for cid in ids:
        bp, qp = bool(base[cid].get("pass")), bool(post[cid].get("pass"))
        if bp and not qp:
            regressions.append({"id": cid, "category": post[cid].get("category"),
                                "input": post[cid].get("input"),
                                "base_why": base[cid].get("why"),
                                "post_why": post[cid].get("why"),
                                "base_answer": str(base[cid].get("answer") or "")[:200],
                                "post_answer": str(post[cid].get("answer") or "")[:200]})
        elif not bp and qp:
            improvements.append({"id": cid, "category": post[cid].get("category")})
    gate = "PASS"
    if len(regressions) > 1 or (regressions and any(
            r.get("post_why") == "contains_forbidden" for r in regressions)):
        gate = "FAIL"
    elif regressions:
        gate = "PASS_WITH_NOTES"
    return {"n": len(ids), "base_pass": sum(1 for cid in ids if base[cid].get("pass")),
            "post_pass": sum(1 for cid in ids if post[cid].get("pass")),
            "regressions": regressions, "improvements": improvements, "verdict": gate}


def evaluate_extra(p):
    d, rows = load_results(p)
    by_cat = {}
    fails = []
    for cid, r in rows.items():
        cat = r.get("category") or "unknown"
        e = by_cat.setdefault(cat, {"n": 0, "pass": 0})
        e["n"] += 1
        if r.get("pass"):
            e["pass"] += 1
        else:
            fails.append({"id": cid, "category": cat, "input": r.get("input"),
                          "failure_class": r.get("failure_class"),
                          "problems": r.get("problems"),
                          "answer": str(((r.get("actual") or {}).get("answer")) or "")[:200]})
    long_ok = by_cat.get("long_memory", {}).get("pass", 0) >= 8
    refuse_ok = by_cat.get("honest_refusal", {}).get("pass", 0) >= 10
    gate = "PASS" if long_ok and refuse_ok else "FAIL"
    return {"by_category": by_cat, "fails": fails, "long_memory_ge_8": long_ok,
            "honest_refusal_all10": refuse_ok, "verdict": gate}


def main():
    ap = argparse.ArgumentParser()
    for k, v in DEFAULT.items():
        ap.add_argument("--" + k.replace("_", "-"), default=str(v))
    a = ap.parse_args()
    paths = {k: Path(getattr(a, k)) for k in DEFAULT}
    doc = {"schema": "sft_eval_compare_v1",
           "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "role": "SFT 微调前后对比（沿用 v4 语义判据；不比对措辞）",
           "inputs": {k: sha(v) for k, v in paths.items()
                      if v.exists() and k != "out"},
           "missing_inputs": [str(v) for k, v in paths.items()
                              if k != "out" and not v.exists()]}
    ok = True
    if paths["post81"].exists() and paths["base81"].exists():
        _, base = load_results(paths["base81"])
        _, post = load_results(paths["post81"])
        doc["regression_81"] = compare81(None, base, None, post)
        ok &= doc["regression_81"]["verdict"] != "FAIL"
    else:
        ok = False
        doc["regression_81"] = {"verdict": "FAIL", "reason": "missing input"}
    if paths["post_heldout"].exists() and paths["base_heldout"].exists():
        doc["heldout"] = compare_heldout(paths["base_heldout"], paths["post_heldout"])
        ok &= doc["heldout"]["verdict"] != "FAIL"
    else:
        ok = False
        doc["heldout"] = {"verdict": "FAIL", "reason": "missing input"}
    if paths["extra"].exists():
        doc["extra_20"] = evaluate_extra(paths["extra"])
        ok &= doc["extra_20"]["verdict"] != "FAIL"
    else:
        ok = False
        doc["extra_20"] = {"verdict": "FAIL", "reason": "missing input"}
    gates = [doc["regression_81"].get("verdict"), doc["heldout"].get("verdict"),
             doc["extra_20"].get("verdict")]
    if "FAIL" in gates:
        overall = "FAIL"
    elif "PASS_WITH_NOTES" in gates:
        overall = "PASS_WITH_NOTES"
    else:
        overall = "PASS"
    doc["verdict"] = {"overall": overall, "gates": gates,
                      "rule": "regression81: 81/81+hard 全过=PASS，1 回退=PASS_WITH_NOTES，否则 FAIL；"
                              "heldout: 无回退=PASS，1 回退=PASS_WITH_NOTES，>1/含禁词=FAIL；"
                              "extra: long_memory≥8/10 且 honest_refusal=10/10；任一 FAIL ⇒ overall FAIL"}
    doc["thresholds"] = {
        "regression_81": "post_pass=81/81 且 hard 六条+h01 全过；回退=FAIL（≤1 回退且无 hard fail=PASS_WITH_NOTES）",
        "heldout": "post_pass ≥ base_pass 且回退≤1；>1 回退或含禁词=FAIL",
        "extra_20": "long_memory ≥8/10；honest_refusal =10/10",
        "latency": "记录 median/max，作为诊断不单独判 FAIL（产品目标 ≤90s/问）",
    }
    out = paths["out"]
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"overall": overall, "gates": gates,
                      "regressions": len(doc["regression_81"].get("regressions") or []) if isinstance(doc["regression_81"], dict) else None,
                      "sha16": hashlib.sha256(out.read_bytes()).hexdigest()[:16]},
                     ensure_ascii=False))
    return 0 if overall != "FAIL" else 3


if __name__ == "__main__":
    sys.exit(main())