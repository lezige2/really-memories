# -*- coding: utf-8 -*-
"""TASK-105：MT20 两臂（base vs v9）配对表。
4WAY/NWAY 只按 eval81/heldout92/extra20 聚合，MT20 的 --only-extra 产物若混入会出现
n=20 vs n=193 不可比、cases_sha extra 冲突；故单独出配对表。
校验：同 cases_sha.extra（MT20 文件 sha）、同 now（冻结时间）、同 harness（temp=0/top_k=1）、
同 id 集、双方 only_extra=true、arm 正确。输出 out/PROXY-COMPARE-MT20.json。
用法：python -X utf8 out/SFT-PROXY-MT20-PAIR.py [--base out/PROXY-MT-base.json --v9 out/PROXY-MT-v9.json]
"""
import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
DIMS = ["猫名", "健身", "手机号", "工位", "车牌", "公司", "出差地", "老家", "爱吃", "女儿小名"]


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def load(p, want_arm):
    if not os.path.isfile(p):
        print("MISSING: %s" % p, file=sys.stderr)
        return None
    d = json.load(open(p, encoding="utf-8"))
    if d.get("arm") != want_arm:
        print("ERROR: %s arm=%r 期望 %r" % (p, d.get("arm"), want_arm), file=sys.stderr)
        raise SystemExit(3)
    return d


def rows(d):
    return {r["id"]: r for r in (d.get("results") or [])}


def dim_of(r):
    m = re.search(r"维度\s*(\S+?)[：:]", str(r.get("note") or ""))
    return m.group(1) if m else "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.path.join(OUT, "PROXY-MT-base.json"))
    ap.add_argument("--v9", default=os.path.join(OUT, "PROXY-MT-v9.json"))
    ap.add_argument("--out", default=os.path.join(OUT, "PROXY-COMPARE-MT20.json"))
    args = ap.parse_args()
    a = load(args.base, "base")
    b = load(args.v9, "sft")
    if a is None or b is None:
        print("MT20 配对不可用（缺产物）", file=sys.stderr)
        raise SystemExit(2)
    ra, rb = rows(a), rows(b)
    cs_a = (a.get("cases_sha256") or {}).get("extra")
    cs_b = (b.get("cases_sha256") or {}).get("extra")
    checks = {
        "both_only_extra": bool(a.get("only_extra")) and bool(b.get("only_extra")),
        "same_cases_sha_extra": bool(cs_a) and cs_a == cs_b,
        "same_now": a.get("now") == b.get("now"),
        "same_harness": a.get("harness") == b.get("harness"),
        "same_ids": set(ra) == set(rb),
        "n_20": len(ra) == len(rb) == 20,
        "temp0_topk1": "temperature=0.0" in str(a.get("harness")) and "top_k=1" in str(a.get("harness")),
    }
    common = sorted(set(ra) & set(rb))
    new_pass = [i for i in common if not ra[i]["ok"] and rb[i]["ok"]]
    new_fail = [i for i in common if ra[i]["ok"] and not rb[i]["ok"]]
    identical = sum(1 for i in common if norm(ra[i].get("answer")) == norm(rb[i].get("answer")))
    by_dim = {}
    for i in common:
        d = dim_of(ra[i])
        s = by_dim.setdefault(d, {"n": 0, "base_pass": 0, "v9_pass": 0, "fail_ids": []})
        s["n"] += 1
        s["base_pass"] += bool(ra[i]["ok"])
        s["v9_pass"] += bool(rb[i]["ok"])
        if not rb[i]["ok"]:
            s["fail_ids"].append(i)
    table = [{"id": i, "dim": dim_of(ra[i]), "base_ok": bool(ra[i]["ok"]), "v9_ok": bool(rb[i]["ok"]),
              "base_answer": str(ra[i].get("answer"))[:160], "v9_answer": str(rb[i].get("answer"))[:160]}
             for i in common]
    rep = {"schema": "sft_proxy_mt20_pair_v1", "task": "TASK-105",
           "inputs": {"base": {"path": os.path.relpath(args.base, ROOT), "sha16": sha16(args.base),
                               "adapter": a.get("adapter_sha256"), "now": a.get("now")},
                      "v9": {"path": os.path.relpath(args.v9, ROOT), "sha16": sha16(args.v9),
                             "adapter": b.get("adapter_sha256"), "now": b.get("now")}},
           "checks": checks,
           "totals": {"n": len(common), "base_pass": sum(1 for i in common if ra[i]["ok"]),
                      "v9_pass": sum(1 for i in common if rb[i]["ok"]),
                      "base_fail": sum(1 for i in common if not ra[i]["ok"]),
                      "v9_fail": sum(1 for i in common if not rb[i]["ok"])},
           "new_pass": new_pass, "new_fail": new_fail, "identical_answer_n": identical,
           "by_dim": by_dim, "table": table,
           "note": "MT20 两臂必须同 cases_sha.extra/同 now/同 harness(temp=0,top_k=1)；"
                   "该表只做 base↔v9 配对，不与 193 主套件数字混算"}
    if not all(checks.values()):
        rep["warning"] = "部分 checks 未通过，见 checks"
    json.dump(rep, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"out": args.out, "sha16": sha16(args.out), "checks": checks,
                      "totals": rep["totals"], "new_pass": new_pass, "new_fail": new_fail}, ensure_ascii=False, indent=1))
    if not all(checks.values()):
        raise SystemExit(4)


if __name__ == "__main__":
    main()