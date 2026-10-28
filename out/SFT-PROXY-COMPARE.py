# -*- coding: utf-8 -*-
"""TASK-034 base vs sft proxy 逐条配对对比（proxy 口径，不可与 service 78/81、90/92 横比）。
输入：out/PROXY-base.json + out/PROXY-sft.json
输出：out/PROXY-COMPARE.json —— 分套件 pass 变化、新增 pass/fail 清单、memory/unknown_refusal/follow 类回归守卫、
      excluded 16+3 单列、effective 分母、逐条配对表。
用法：python -X utf8 out/SFT-PROXY-COMPARE.py --base out/PROXY-base.json --sft out/PROXY-sft.json
"""
import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITES = ["eval81", "heldout92", "extra20"]
# 回归守卫：这些类别 base pass 而 sft fail 视为违规
GUARD = {"memory": {"memory_qa", "memory", "long_memory"},
         "unknown_refusal": {"unknown_refusal", "unknown", "honest_refusal"},
         "follow": {"chat_followup", "follow"}}
PROXY_NOTE = ("proxy≠service 口径：llama-server /completion 文本记忆（无 topk/记忆库/KV mount/verify/refused/"
              "state/auto_memory/快速分支）；绝对通过率不可与 service 78/81、90/92、20/20 横比，"
              "本对比只衡量 base 与 base+lora 在同 prompt（temp=0/top_k=1）、同判据、同冻结时间下的相对变化。"
              "A3：proxy 的记忆类提升只能表述为“文本记忆格式下行为更贴合”，不得表述为“记忆能力变好”；"
              "真正的记忆能力结论必须来自 SFT-GGUF + service KV 挂载轮（含空库对照）。")
SAME_WEIGHTS_WARN = "两臂答案≥90%一致，先核 llama-server 启动命令是否真带 --lora"


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def sha16(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def load_arm(path, arm):
    d = json.load(open(path, encoding="utf-8"))
    if d.get("arm") != arm:
        print("ERROR: %s 的 arm=%r，期望 %r" % (path, d.get("arm"), arm), file=sys.stderr)
        raise SystemExit(3)
    return d


def main():
    ap = argparse.ArgumentParser(description="pairwise proxy compare: base vs sft")
    ap.add_argument("--base", default=os.path.join(ROOT, "out", "PROXY-base.json"))
    ap.add_argument("--sft", default=os.path.join(ROOT, "out", "PROXY-sft.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "PROXY-COMPARE.json"))
    args = ap.parse_args()
    if not os.path.isfile(args.base) or not os.path.isfile(args.sft):
        print("ERROR: 缺少臂结果（base=%s sft=%s）；先跑齐两臂，禁止生成假通过"
              % (os.path.isfile(args.base), os.path.isfile(args.sft)), file=sys.stderr)
        raise SystemExit(2)
    b = load_arm(args.base, "base")
    s = load_arm(args.sft, "sft")
    warnings, fatal = [], []
    if not s.get("adapter_sha256"):
        fatal.append("sft 结果缺 adapter_sha256")
    if b.get("now") != s.get("now"):
        fatal.append("两臂 now 不一致：%r vs %r" % (b.get("now"), s.get("now")))
    # TASK-036：cases_sha 语义比较（旧 base 键 extra_v2，新键 extra；忽略 only_extra/contamination 等新键）
    cb, cs = b.get("cases_sha256") or {}, s.get("cases_sha256") or {}
    xb, xs = cb.get("extra_v2") or cb.get("extra"), cs.get("extra") or cs.get("extra_v2")
    if cb.get("dialog_cases") != cs.get("dialog_cases") or cb.get("heldout_run_heldout") != cs.get("heldout_run_heldout") \
            or (xb and xs and xb != xs):
        fatal.append("两臂底层用例 sha 不一致：dialog=%r/%r heldout=%r/%r extra=%r/%r"
                     % (cb.get("dialog_cases"), cs.get("dialog_cases"), cb.get("heldout_run_heldout"),
                        cs.get("heldout_run_heldout"), xb, xs))
    if b.get("model") != s.get("model"):
        warnings.append("两臂 model 路径不同：%r vs %r" % (b.get("model"), s.get("model")))
    # A2：两臂 harness 必须完全一致（缺任一侧也不可比）
    if not b.get("harness") or not s.get("harness") or b.get("harness") != s.get("harness"):
        fatal.append("两臂 harness 不一致/缺失：base=%r sft=%r" % (b.get("harness"), s.get("harness")))
    same_props = json.dumps(b.get("server_props"), sort_keys=True) == json.dumps(s.get("server_props"), sort_keys=True)
    if same_props:
        warnings.append("两臂 server_props 相同：区分依赖 adapter_sha256 / --expect-lora-sha，需人工确认 sft 服务确已加载 lora")
    if not (s.get("server_identity", {}).get("lora_seen_in_props")
            or s.get("server_identity", {}).get("distinguishable_by")):
        warnings.append("sft 臂 server_identity 无 lora 证据字段")
    if fatal:
        print("ERROR: " + "；".join(fatal), file=sys.stderr)
        raise SystemExit(4)
    bm = {(r["source"], r["id"]): r for r in b.get("results") or []}
    sm = {(r["source"], r["id"]): r for r in s.get("results") or []}
    order = [(r["source"], r["id"]) for r in (b.get("results") or [])]
    missing = [k for k in order if k not in sm]
    pairs = []
    for key in order:
        src, cid = key
        rb = bm[key]
        rs = sm.get(key)
        if rs is None:
            pairs.append({"source": src, "id": cid, "category": rb.get("category"), "excluded": False,
                          "missing_in_sft": True, "base_ok": bool(rb.get("ok")), "sft_ok": None})
            continue
        gclass = next((g for g, cats in GUARD.items() if (rs.get("category") or rb.get("category")) in cats), None)
        change = "same" if bool(rb.get("ok")) == bool(rs.get("ok")) else \
                 ("new_pass" if rs.get("ok") else "new_fail")
        pairs.append({"source": src, "id": cid, "category": rs.get("category") or rb.get("category"),
                      "guard_class": gclass, "excluded": bool(rb.get("excluded") or rs.get("excluded")),
                      "base_ok": bool(rb.get("ok")), "sft_ok": bool(rs.get("ok")), "change": change,
                      "base_why": rb.get("why"), "sft_why": rs.get("why"),
                      "base_answer": rb.get("answer"), "sft_answer": rs.get("answer"),
                      "answer_diff": str(rb.get("answer")) != str(rs.get("answer"))})
    by_suite = {}
    for suite in SUITES:
        rows = [p for p in pairs if p["source"] == suite]
        kept = [p for p in rows if not p.get("excluded")]
        exc = [p for p in rows if p.get("excluded")]
        by_suite[suite] = {
            "n": len(rows), "excluded_n": len(exc),
            "base_pass": sum(1 for p in rows if p.get("base_ok")),
            "sft_pass": sum(1 for p in rows if p.get("sft_ok")),
            "delta": sum(1 for p in rows if p.get("sft_ok")) - sum(1 for p in rows if p.get("base_ok")),
            "new_pass": [p["id"] for p in rows if p.get("change") == "new_pass"],
            "new_fail": [p["id"] for p in rows if p.get("change") == "new_fail"],
            "both_fail": [p["id"] for p in rows if p.get("base_ok") is False and p.get("sft_ok") is False],
            "effective": {"n": len(kept),
                          "base_pass": sum(1 for p in kept if p.get("base_ok")),
                          "sft_pass": sum(1 for p in kept if p.get("sft_ok")),
                          "delta": sum(1 for p in kept if p.get("sft_ok")) - sum(1 for p in kept if p.get("base_ok"))},
            "excluded": {"ids": [p["id"] for p in exc],
                         "base_pass": sum(1 for p in exc if p.get("base_ok")),
                         "sft_pass": sum(1 for p in exc if p.get("sft_ok"))}}
    eff = [p for p in pairs if not p.get("excluded") and not p.get("missing_in_sft")]
    regressions = {}
    for g, cats in GUARD.items():
        regressions[g] = [p["id"] for p in pairs
                          if p.get("guard_class") == g and p.get("base_ok") and p.get("sft_ok") is False]
    both_pass_ansdiff = [p["id"] for p in pairs if p.get("base_ok") and p.get("sft_ok") and p.get("answer_diff")]
    # A1：两臂疑似同一权重告警（193 对中两侧答案 norm 后完全一致比例 ≥90% → fatal exit 5）
    pair_n = len(pairs)
    identical_n = sum(1 for p in pairs if not p.get("missing_in_sft")
                      and norm(p.get("base_answer")) == norm(p.get("sft_answer")))
    identical_ratio = round(identical_n / max(1, pair_n), 6)
    suspected_same_weights = bool(pair_n and identical_ratio >= 0.90)
    if suspected_same_weights:
        warnings.append(SAME_WEIGHTS_WARN)
    out = {"schema": "sft_proxy_compare_v1", "task": "TASK-034", "proxy_note": PROXY_NOTE,
           "inputs": {"base": {"path": os.path.relpath(args.base, ROOT), "sha16": sha16(args.base),
                               "arm": b.get("arm"), "lora": b.get("lora"), "adapter_sha256": b.get("adapter_sha256")},
                      "sft": {"path": os.path.relpath(args.sft, ROOT), "sha16": sha16(args.sft),
                              "arm": s.get("arm"), "lora": s.get("lora"), "adapter_sha256": s.get("adapter_sha256")}},
           "meta": {"now": b.get("now"), "model": b.get("model"), "cases_sha256": b.get("cases_sha256"),
                    "n_predict": b.get("harness"), "harness_base": b.get("harness"), "harness_sft": s.get("harness"),
                    "server_props_same": same_props,
                    "sft_lora_seen_in_props": s.get("server_identity", {}).get("lora_seen_in_props")},
           "warnings": warnings, "missing_in_sft": [{"source": k[0], "id": k[1]} for k in missing],
           "summary": {"total": len(pairs), "effective_n": len(eff),
                       "base_pass": sum(1 for p in pairs if p.get("base_ok")),
                       "sft_pass": sum(1 for p in pairs if p.get("sft_ok")),
                       "delta": sum(1 for p in pairs if p.get("sft_ok")) - sum(1 for p in pairs if p.get("base_ok")),
                       "effective": {"n": len(eff), "base_pass": sum(1 for p in eff if p.get("base_ok")),
                                     "sft_pass": sum(1 for p in eff if p.get("sft_ok")),
                                     "delta": sum(1 for p in eff if p.get("sft_ok")) - sum(1 for p in eff if p.get("base_ok"))},
                       "excluded": {"n": sum(1 for p in pairs if p.get("excluded")),
                                    "base_pass": sum(1 for p in pairs if p.get("excluded") and p.get("base_ok")),
                                    "sft_pass": sum(1 for p in pairs if p.get("excluded") and p.get("sft_ok"))},
                       "identical_answer_n": identical_n, "pair_n": pair_n,
                       "identical_answer_ratio": identical_ratio,
                       "suspected_same_weights": suspected_same_weights},
           "by_suite": by_suite,
           "guard": {"policy": "memory/unknown_refusal/follow 类不得回归（base pass → sft fail 即违规）",
                     "regressions": regressions, "passed": all(not v for v in regressions.values())},
           "both_pass_but_answer_diff": {"n": len(both_pass_ansdiff), "ids": both_pass_ansdiff},
           "pairs": pairs}
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"out": os.path.relpath(args.out, ROOT), "summary": out["summary"],
                      "by_suite": {k: {"base_pass": v["base_pass"], "sft_pass": v["sft_pass"], "delta": v["delta"],
                                       "new_pass": v["new_pass"], "new_fail": v["new_fail"]}
                                   for k, v in by_suite.items()},
                      "guard": out["guard"], "warnings": warnings}, ensure_ascii=False, indent=1))
    if suspected_same_weights:                                # A1：疑似同一权重 → fatal 5
        return 5
    return 0 if out["guard"]["passed"] and not missing else 1


if __name__ == "__main__":
    sys.exit(main())