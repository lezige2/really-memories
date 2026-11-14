# -*- coding: utf-8 -*-
"""Aggregate K5 5x (off/on) + trigger rate + byte-exact check + gate."""
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
    per, fb, tk, tn = {}, 0, 0, 0
    for i in range(1, k + 1):
        d = json.load(open("out/%s-%d.json" % (prefix, i), encoding="utf-8"))
        for r in d["results"]:
            cid = r["id"]
            ok = bool(r.get("pass"))
            per.setdefault(cid, []).append(ok)
            tk += 1 if ok else 0
            tn += 1
            a = r.get("actual") or {}
            if a.get("state") == "verify_fallback":
                fb += 1
    return per, fb, tk, tn


def main():
    off, off_fb, ok_, on_ = load("K5-OFF")
    on, on_fb, ak, an = load("K5-ON")
    ids = sorted(set(off) | set(on))
    cases, collapsed = [], []
    for cid in ids:
        o, a = off.get(cid, []), on.get(cid, [])
        cases.append({"id": cid, "off": sum(o), "on": sum(a), "n": len(o)})
        if sum(o) >= 4 and sum(a) <= 2:
            collapsed.append(cid)
    orate, arate = ok_ / on_, ak / an
    try:
        rate = json.load(open("out/K5-TRIGGER.json", encoding="utf-8"))
    except Exception:
        rate = {"applied": None, "n": 20, "rate": None, "le_30pct": None,
                "rows": [], "note": "trigger probe not run"}
    try:
        base = json.load(open("out/K5-BASE-81.json", encoding="utf-8"))["summary"]
        extr = json.load(open("out/K5-BASE-EXTRA.json", encoding="utf-8"))["summary"]
        base_info = {"81": base["pass"], "extra": extr["pass"],
                     "extra_fails": [f["id"] for f in extr.get("failures", [])]}
    except Exception:
        base_info = {"81": None, "extra": None, "note": "not measured"}

    gate = {"on_ge_off": arate >= orate, "no_collapse": not collapsed,
            "collapsed": collapsed,
            "trigger_le_30": rate.get("le_30pct"),
            "base_ok": (base_info.get("81") == 81 and base_info.get("extra") in (17, 18))}

    md = ["# K5 · MT20 5×2（off / on）+ 触发率 + 81/extra", "",
          "| 臂 | pass | rate | 95%CI | fallback |", "|---|---|---|---|---|",
          "| off | **%d/%d** | %.3f | [%.3f, %.3f] | %d |" % (ok_, on_, orate, *wilson(ok_, on_), off_fb),
          "| on（`--slot-direct`） | **%d/%d** | %.3f | [%.3f, %.3f] | %d |" % (ak, an, arate, *wilson(ak, an), on_fb),
          "", "## 逐 case（5 次 pass）", "", "| case | off | on |", "|---|---|---|"]
    for c in cases:
        md.append("| %s | %d/5 | %d/5 |" % (c["id"], c["off"], c["on"]))
    md += ["", "## 触发率", "",
           "- applied **%s/%s = %s**，≤30%%：**%s**" % (
               rate.get("applied"), rate.get("n"),
               ("%.1f%%" % (100 * rate["rate"])) if rate.get("rate") is not None else "未测",
               rate.get("le_30pct")),
           "", "## 81 / extra", "",
           "- 81：**%s/81**；extra：**%s/20**（fail %s）" % (
               base_info.get("81"), base_info.get("extra"), base_info.get("extra_fails")),
           "", "## 门", "",
           "- on ≥ off：**%s**（%.3f vs %.3f）" % ("过" if gate["on_ge_off"] else "不过", arate, orate),
           "- 无 4–5→0–2：**%s**%s" % ("过" if not collapsed else "不过：" + ",".join(collapsed), ""),
           "- 触发 ≤30%%：**%s**" % ("过" if gate["trigger_le_30"] else "不过/未测"),
           "- 81/extra 不回归：**%s**" % ("过" if gate["base_ok"] else "不过/未测"),
           "", "结论：**%s**" % ("四项全过" if all([gate["on_ge_off"], not collapsed,
                                                    gate["trigger_le_30"], gate["base_ok"]]) else "未全过")]
    text = "\n".join(md)
    open("out/K5-MT20-5X.md", "w", encoding="utf-8").write(text)
    json.dump({"off": {"k": ok_, "n": on_, "rate": round(orate, 4), "fallback": off_fb},
               "on": {"k": ak, "n": an, "rate": round(arate, 4), "fallback": on_fb},
               "cases": cases, "trigger": rate, "base": base_info, "gate": gate},
              open("out/K5-MT20-5X.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(text)


if __name__ == "__main__":
    main()