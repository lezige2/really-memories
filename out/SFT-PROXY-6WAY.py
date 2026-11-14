# -*- coding: utf-8 -*-
"""TASK v7 六方对照：base / v2 / v3 / v4 / v5 / v7（proxy 口径）。
输入：out/PROXY-base.json、out/PROXY-sft.json、out/PROXY-sft-v3.json、out/PROXY-v4.json、out/PROXY-v5.json、out/PROXY-v7.json
      autonomy：out/PROXY-autonomy-{base,sft,sft-v3,v4,v5,v7}.json（v4/v5/v7 D 类为**空 user**口径）
输出：out/PROXY-COMPARE-6WAY.json（并复制一份 out/PROXY-COMPARE-v7.json），含
      主套件/by_suite/deltas、autonomy A/B/C/D、veto 风险关注项（c04/c06/c09/w01/w02/h701/L04/L09/D03）。
用法：python -X utf8 out/SFT-PROXY-6WAY.py [--out out/PROXY-COMPARE-6WAY.json]
"""
import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
SUITES = ["eval81", "heldout92", "extra20"]
ARMS = ["base", "v2", "v3", "v4", "v5", "v7"]
FILES = {"base": "PROXY-base.json", "v2": "PROXY-sft.json", "v3": "PROXY-sft-v3.json", "v4": "PROXY-v4.json", "v5": "PROXY-v5.json", "v7": "PROXY-v7.json"}
AUTO_CAND = {"base": ["PROXY-autonomy-base-dempty.json", "PROXY-autonomy-base.json"],
             "v2": ["PROXY-autonomy-sft-dempty.json", "PROXY-autonomy-sft.json"],
             "v3": ["PROXY-autonomy-sft-v3-dempty.json", "PROXY-autonomy-sft-v3.json"],
             "v4": ["PROXY-autonomy-v4.json"], "v5": ["PROXY-autonomy-v5.json"], "v7": ["PROXY-autonomy-v7.json"]}


def auto_path(arm):
    for name in AUTO_CAND[arm]:
        p = os.path.join(OUT, name)
        if os.path.isfile(p):
            return p
    return os.path.join(OUT, AUTO_CAND[arm][-1])
GUARD = {"memory": {"memory_qa", "memory", "long_memory"},
         "unknown_refusal": {"unknown_refusal", "unknown", "honest_refusal"},
         "follow": {"chat_followup", "follow"}}
WATCH = ["c04", "c06", "c09", "w01", "w02", "h701", "L04", "L09"]
WATCH_AUTO = ["D03"]
RISK_PAT = re.compile(r"℃|度|晴|多云|阴|雨|雪|限行|尾号|来源[:：]|别吃|换药|建议吃|可以吃|投资建议|直接签")
NOTE = ("proxy≠service：llama-server /completion 文本记忆；不可与 service 78/81、90/92 横比；"
        "仅 base/v2/v3/v4 同 prompt(temp=0,top_k=1)/同判据/同冻结时间相对对比。"
        "v4 autonomy 的 D 类为**空 user**口径（v2/v3/base 为文本触发句），D 类数字跨口径不可直接比，需看同一文件内 A/B/C。")


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def load(path, arm):
    if not os.path.isfile(path):
        return None
    d = json.load(open(path, encoding="utf-8"))
    if d.get("arm") != ("base" if arm == "base" else "sft"):
        print("ERROR: %s arm=%r 期望 %r" % (path, d.get("arm"), arm), file=sys.stderr)
        raise SystemExit(3)
    return d


def rows(d):
    return {(r["source"], r["id"]): r for r in (d.get("results") or [])}


def cases_ok(arms, tag):
    ds = [a.get("cases_sha256") or {} for a in arms if a]
    if len(ds) < 2:
        return True
    def k(d, key):
        return d.get(key) or (d.get("extra_v2") if key == "extra" else None) or (d.get("extra") if key == "extra_v2" else None)
    for key in ("dialog_cases", "heldout_run_heldout", "extra"):
        vals = {k(d, key) for d in ds}
        if len([v for v in vals if v]) > 1:
            return False
    return True


def suite_stats(d):
    m = rows(d)
    out = {}
    for s in SUITES:
        rs = [r for (src, _), r in m.items() if src == s]
        kept = [r for r in rs if not r.get("excluded")]
        out[s] = {"n": len(rs), "pass": sum(1 for r in rs if r["ok"]),
                  "excluded_n": len(rs) - len(kept), "effective_n": len(kept),
                  "effective_pass": sum(1 for r in kept if r["ok"])}
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


def auto_stats(d):
    m = rows(d)
    out = {}
    for cls in "ABCD":
        rs = [r for (_, cid), r in m.items() if cid.startswith(cls)]
        out[cls] = {"n": len(rs), "pass": sum(1 for r in rs if r["ok"]),
                    "fail_ids": [r["id"] for r in rs if not r["ok"]],
                    "empty_user_n": sum(1 for r in rs if r.get("empty_user"))}
    out["_total"] = {"n": len(m), "pass": sum(1 for r in m.values() if r["ok"])}
    return out


def watch(d, ids, auto=False):
    m = rows(d)
    res = {}
    for (_, cid), r in m.items():
        if cid in ids:
            ans = str(r.get("answer") or "")
            res[cid] = {"ok": bool(r["ok"]), "why": r.get("why"), "answer": ans[:180],
                        "risk_pattern": bool(RISK_PAT.search(ans))}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(OUT, "PROXY-COMPARE-6WAY.json"))
    args = ap.parse_args()
    arms = {a: load(os.path.join(OUT, FILES[a]), a) for a in ARMS}
    autos = {a: load(auto_path(a), a) for a in ARMS}
    present = {a: d for a, d in arms.items() if d}
    if "base" not in present:
        print("ERROR: 缺 base 臂", file=sys.stderr)
        raise SystemExit(2)
    warnings = []
    if not cases_ok([arms[a] for a in ARMS if arms[a]], "main"):
        print("ERROR: 主套件底层用例 sha 不一致", file=sys.stderr)
        raise SystemExit(4)
    if not cases_ok([autos[a] for a in ARMS if autos[a]], "auto"):
        warnings.append("autonomy 用例 sha 跨臂不同（v4 D 类为空 user 口径，属预期；A/B/C 仍可比）")
    nows = {a.get("now") for a in present.values()}
    if len(nows) > 1:
        warnings.append("now 不一致：%r" % nows)
    rep = {"schema": "sft_proxy_6way_v1", "task": "TASK-v7", "proxy_note": NOTE,
           "inputs": {a: {"path": os.path.relpath(os.path.join(OUT, FILES[a]), ROOT),
                          "sha16": sha16(os.path.join(OUT, FILES[a])),
                          "adapter_sha256": arms[a].get("adapter_sha256"),
                          "lora": arms[a].get("lora")} for a in ARMS if arms[a]},
           "autonomy_inputs": {a: {"path": os.path.relpath(auto_path(a), ROOT),
                                   "sha16": sha16(auto_path(a)),
                                   "d_mode": ("empty_user" if any(r.get("empty_user") for r in (autos[a].get("results") or [])
                                                                  if str(r.get("id", "")).startswith("D")) else "text_trigger")}
                               for a in ARMS if autos[a]},
           "missing": [a for a in ARMS if not arms[a]],
           "warnings": warnings, "main": {}, "main_diffs": {}, "guard_fail_ids": {},
           "autonomy": {}, "autonomy_diffs": {}, "veto_watch": {}, "autonomy_veto_watch": {}}
    for a in ARMS:
        if arms[a]:
            rep["main"][a] = suite_stats(arms[a])
            rep["guard_fail_ids"][a] = guard(arms[a])
        if autos[a]:
            rep["autonomy"][a] = auto_stats(autos[a])
    for a, b in (("v5", "v7"), ("v4", "v7"), ("v3", "v7"), ("base", "v7"), ("v4", "v5"), ("v3", "v5"), ("v2", "v5"), ("base", "v5"), ("v3", "v4"), ("v2", "v4"), ("base", "v4"), ("v3", "v2")):
        if arms.get(a) and arms.get(b):
            rep["main_diffs"]["%s->%s" % (a, b)] = diff(arms[a], arms[b])
        if autos.get(a) and autos.get(b):
            rep["autonomy_diffs"]["%s->%s" % (a, b)] = diff(autos[a], autos[b])
    best = "v7" if arms.get("v7") else ("v5" if arms.get("v5") else "v4")
    if arms.get(best):
        rep["veto_watch"] = watch(arms[best], WATCH)
        rep["veto_watch_arm"] = best
    if autos.get(best):
        rep["autonomy_veto_watch"] = watch(autos[best], WATCH_AUTO)
    json.dump(rep, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    v7path = os.path.join(OUT, "PROXY-COMPARE-v7.json")
    if os.path.abspath(args.out) != os.path.abspath(v7path):
        json.dump(rep, open(v7path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"out": os.path.relpath(args.out, ROOT), "missing": rep["missing"],
                      "main": {a: v["_total"] for a, v in rep["main"].items()},
                      "main_delta": {k: {"new_pass": len(v["new_pass"]), "new_fail": len(v["new_fail"]),
                                         "identical": v["identical_answer_n"]} for k, v in rep["main_diffs"].items()},
                      "autonomy": {a: {c: [v[c]["pass"], v[c]["n"]] for c in "ABCD"} for a, v in rep["autonomy"].items()},
                      "guard": rep["guard_fail_ids"], "veto_watch": rep["veto_watch"],
                      "warnings": warnings}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()