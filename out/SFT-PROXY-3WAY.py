# -*- coding: utf-8 -*-
"""TASK-037 三方汇总：base vs sft-v2 vs sft-v3（proxy 口径）。
主套件输入：out/PROXY-base.json / out/PROXY-sft.json / out/PROXY-sft-v3.json
autonomy 输入（可选）：out/PROXY-autonomy-base.json / -sft.json / -sft-v3.json
输出：out/PROXY-COMPARE-3WAY.json（分套件 pass、deltas、guard、autonomy A/B/C/D、A1 同权重检查）
用法：python -X utf8 out/SFT-PROXY-3WAY.py
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITES = ["eval81", "heldout92", "extra20"]
GUARD = {"memory": {"memory_qa", "memory", "long_memory"},
         "unknown_refusal": {"unknown_refusal", "unknown", "honest_refusal"},
         "follow": {"chat_followup", "follow"}}
NOTE = ("proxy≠service 口径：llama-server /completion 文本记忆（无 检索/KV mount/verify/refused/state）；"
        "不可与 service 78/81、90/92、20/20 横比；仅 base/v2/v3 在同 prompt(temp=0,top_k=1)/同判据/同冻结时间下相对对比。"
        "D 类 autonomy 仅是文本探针，不等于真实主动发送。")


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def load(path, arm):
    if not os.path.isfile(path):
        return None
    d = json.load(open(path, encoding="utf-8"))
    if d.get("arm") != arm:
        print("ERROR: %s arm=%r 期望 %r" % (path, d.get("arm"), arm), file=sys.stderr)
        raise SystemExit(3)
    return d


def rows(d):
    return {(r["source"], r["id"]): r for r in (d.get("results") or [])}


def cases_ok(arms):
    ds = [a.get("cases_sha256") or {} for a in arms if a]
    if not ds:
        return True
    def key(d, k):
        return d.get(k) or (d.get("extra_v2") if k == "extra" else None) or (d.get("extra") if k == "extra_v2" else None)
    for k in ("dialog_cases", "heldout_run_heldout", "extra"):
        vals = {key(d, k) for d in ds}
        if len([v for v in vals if v]) > 1:
            return False
    return True


def suite_stats(d):
    out = {}
    m = rows(d)
    for s in SUITES:
        rs = [r for (src, _), r in m.items() if src == s]
        kept = [r for r in rs if not r.get("excluded")]
        out[s] = {"n": len(rs), "pass": sum(1 for r in rs if r["ok"]),
                  "pass_rate": round(sum(1 for r in rs if r["ok"]) / max(1, len(rs)), 4),
                  "excluded_n": len(rs) - len(kept),
                  "effective_n": len(kept), "effective_pass": sum(1 for r in kept if r["ok"])}
    out["_total"] = {"n": len(m), "pass": sum(1 for r in m.values() if r["ok"]),
                     "effective_n": sum(1 for r in m.values() if not r.get("excluded")),
                     "effective_pass": sum(1 for r in m.values() if not r.get("excluded") and r["ok"])}
    return out


def diff(a, b):
    ma, mb = rows(a), rows(b)
    common = [k for k in ma if k in mb]
    return {"new_pass": [k[1] for k in common if not ma[k]["ok"] and mb[k]["ok"]],
            "new_fail": [k[1] for k in common if ma[k]["ok"] and not mb[k]["ok"]],
            "identical_answer_n": sum(1 for k in common if norm(ma[k].get("answer")) == norm(mb[k].get("answer"))),
            "pairs": len(common)}


def guard(d):
    reg = {g: [] for g in GUARD}
    for r in rows(d).values():
        for g, cats in GUARD.items():
            if r.get("category") in cats and r.get("ok") is False:
                reg[g].append(r["id"])
    return reg


def autonomy_stats(d):
    m = rows(d)
    out = {}
    for cls in "ABCD":
        rs = [r for (_, cid), r in m.items() if cid.startswith(cls)]
        kept = [r for r in rs if not r.get("excluded")]
        out[cls] = {"n": len(rs), "pass": sum(1 for r in rs if r["ok"]),
                    "effective_n": len(kept), "effective_pass": sum(1 for r in kept if r["ok"]),
                    "fail_ids": [r["id"] for r in rs if not r["ok"]]}
    out["_total"] = {"n": len(m), "pass": sum(1 for r in m.values() if r["ok"]),
                     "effective_n": sum(1 for r in m.values() if not r.get("excluded")),
                     "effective_pass": sum(1 for r in m.values() if not r.get("excluded") and r["ok"])}
    return out


def main():
    paths = {"base": os.path.join(ROOT, "out", "PROXY-base.json"),
             "v2": os.path.join(ROOT, "out", "PROXY-sft.json"),
             "v3": os.path.join(ROOT, "out", "PROXY-sft-v3.json")}
    auto_paths = {"base": os.path.join(ROOT, "out", "PROXY-autonomy-base.json"),
                  "v2": os.path.join(ROOT, "out", "PROXY-autonomy-sft.json"),
                  "v3": os.path.join(ROOT, "out", "PROXY-autonomy-sft-v3.json")}
    arms = {k: load(p, "base" if k == "base" else "sft") for k, p in paths.items()}
    autos = {k: load(p, "base" if k == "base" else "sft") for k, p in auto_paths.items()}
    present = {k: v for k, v in arms.items() if v}
    if "base" not in present:
        print("ERROR: 缺 base 臂", file=sys.stderr)
        raise SystemExit(2)
    warnings = []
    if not cases_ok([a for a in arms.values() if a]):
        warnings.append("主套件两臂/三臂底层用例 sha 不一致")
    if not cases_ok([a for a in autos.values() if a]):
        warnings.append("autonomy 两臂/三臂底层用例 sha 不一致")
    nows = {a.get("now") for a in arms.values() if a}
    if len(nows) > 1:
        warnings.append("now 不一致：%r" % nows)
    res = {"schema": "sft_proxy_3way_v1", "task": "TASK-037", "proxy_note": NOTE,
           "inputs": {k: {"path": os.path.relpath(p, ROOT),
                          "sha16": hashlib.sha256(open(p, "rb").read()).hexdigest()[:16],
                          "arm": arms[k].get("arm"), "adapter_sha256": arms[k].get("adapter_sha256"),
                          "lora": arms[k].get("lora")} for k, p in paths.items() if arms[k]},
           "autonomy_inputs": {k: {"path": os.path.relpath(p, ROOT),
                                   "sha16": hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]}
                               for k, p in auto_paths.items() if autos[k]},
           "meta": {"now": sorted(nows), "model": arms["base"].get("model"),
                    "server_props_same_all": len({json.dumps(a.get("server_props"), sort_keys=True)
                                                  for a in present.values()}) <= 1,
                    "lora_evidence": {k: a.get("server_identity") for k, a in present.items()}},
           "warnings": warnings,
           "main": {}, "main_diffs": {}, "guard_fail_ids": {}, "autonomy": {}, "autonomy_diffs": {}}
    for k, a in present.items():
        st = suite_stats(a)
        res["main"][k] = st
        res["guard_fail_ids"][k] = guard(a)
    for a_name, b_name in (("base", "v2"), ("base", "v3"), ("v2", "v3")):
        if arms.get(a_name) and arms.get(b_name):
            res["main_diffs"]["%s->%s" % (a_name, b_name)] = diff(arms[a_name], arms[b_name])
    if autos.get("base"):
        for k, a in autos.items():
            if a:
                res["autonomy"][k] = autonomy_stats(a)
        for a_name, b_name in (("base", "v2"), ("base", "v3"), ("v2", "v3")):
            if autos.get(a_name) and autos.get(b_name):
                res["autonomy_diffs"]["%s->%s" % (a_name, b_name)] = diff(autos[a_name], autos[b_name])
    out = os.path.join(ROOT, "out", "PROXY-COMPARE-3WAY.json")
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"out": os.path.relpath(out, ROOT),
                      "main": {k: {"total": v["_total"], "by_suite": {s: [v[s]["pass"], v[s]["n"]] for s in SUITES}}
                               for k, v in res["main"].items()},
                      "main_delta": {k: {"new_pass": len(v["new_pass"]), "new_fail": len(v["new_fail"]),
                                         "identical": v["identical_answer_n"]} for k, v in res["main_diffs"].items()},
                      "guard": res["guard_fail_ids"],
                      "autonomy": {k: {c: [v[c]["pass"], v[c]["n"]] for c in "ABCD"} for k, v in res["autonomy"].items()},
                      "autonomy_delta": {k: {"new_pass": len(v["new_pass"]), "new_fail": len(v["new_fail"])}
                                         for k, v in res["autonomy_diffs"].items()},
                      "warnings": warnings}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()