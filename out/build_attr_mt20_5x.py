# -*- coding: utf-8 -*-
"""Aggregate MT20 5x for attribute-recency POC (off vs on) + gate."""
import json
import math


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def load(prefix, k=5):
    per, fb, tot_k, tot_n = {}, 0, 0, 0
    for i in range(1, k + 1):
        d = json.load(open("out/%s-%d.json" % (prefix, i), encoding="utf-8"))
        for r in d["results"]:
            cid = r["id"]
            ok = bool(r.get("pass"))
            per.setdefault(cid, []).append(ok)
            tot_k += 1 if ok else 0
            tot_n += 1
            a = r.get("actual") or {}
            if a.get("state") == "verify_fallback":
                fb += 1
    return per, fb, tot_k, tot_n


def main():
    off, off_fb, off_k, off_n = load("POC-AT-OFF")
    on, on_fb, on_k, on_n = load("POC-AT-ON")
    ids = sorted(set(off) | set(on))
    cases, collapsed = [], []
    for cid in ids:
        o, a = off.get(cid, []), on.get(cid, [])
        cases.append({"id": cid, "off": sum(o), "on": sum(a), "n": len(o)})
        if sum(o) >= 4 and sum(a) <= 2:
            collapsed.append(cid)
    orate, arate = off_k / off_n, on_k / on_n
    gate = {"on_not_below_off": arate >= orate,
            "no_case_collapse": not collapsed,
            "collapsed": collapsed}
    md = ["# POC · attribute recency · MT20 5× (off / on)", "",
          "| 臂 | pass | rate | 95%CI | verify_fallback |", "|---|---|---|---|---|",
          "| off | **%d/%d** | %.3f | [%.3f, %.3f] | %d |" % (off_k, off_n, orate, *wilson(off_k, off_n), off_fb),
          "| on | **%d/%d** | %.3f | [%.3f, %.3f] | %d |" % (on_k, on_n, arate, *wilson(on_k, on_n), on_fb),
          "", "## 逐 case（5 次 pass 数）", "", "| case | off | on |", "|---|---|---|"]
    for c in cases:
        md.append("| %s | %d/5 | %d/5 |" % (c["id"], c["off"], c["on"]))
    md += ["", "## 门", "",
           "- on 不低于 off：**%s**（%.3f vs %.3f）" % ("过" if gate["on_not_below_off"] else "不过", arate, orate),
           "- 无 case 4–5→0–2：**%s**%s" % ("过" if not collapsed else "不过：" + ",".join(collapsed), ""),
           "- 触发率 ≤30%%：**%s**（实测 %d/%d = %.0f%%）" % (
               "过" if json.load(open("out/POC-AT-ATTR-RATE.json", encoding="utf-8"))["le_30pct"] else "不过",
               json.load(open("out/POC-AT-ATTR-RATE.json", encoding="utf-8"))["applied"],
               json.load(open("out/POC-AT-ATTR-RATE.json", encoding="utf-8"))["n"],
               100 * json.load(open("out/POC-AT-ATTR-RATE.json", encoding="utf-8"))["rate"])]
    open("out/POC-ATTR-MT20-5X.md", "w", encoding="utf-8").write("\n".join(md))
    json.dump({"off": {"k": off_k, "n": off_n, "rate": round(orate, 4), "fallback": off_fb},
               "on": {"k": on_k, "n": on_n, "rate": round(arate, 4), "fallback": on_fb},
               "cases": cases, "gate": gate,
               "attribute_trigger_rate": json.load(open("out/POC-AT-ATTR-RATE.json", encoding="utf-8"))},
              open("out/POC-ATTR-MT20-5X.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(md))


if __name__ == "__main__":
    main()