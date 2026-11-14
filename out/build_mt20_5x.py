# -*- coding: utf-8 -*-
"""Aggregate MT20 5x per arm: total rate + Wilson CI + per-case pass counts + gate."""
import json
import math


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def load(arm, runs=5):
    out = {}
    tot_k = tot_n = 0
    for k in range(1, runs + 1):
        d = json.load(open("out/P1-MT5-%s-%d.json" % (arm, k), encoding="utf-8"))
        for r in d["results"]:
            cid = r["id"]
            ok = bool(r.get("pass"))
            out.setdefault(cid, []).append(ok)
            tot_k += 1 if ok else 0
            tot_n += 1
    return out, tot_k, tot_n


def main():
    off, offk, offn = load("OFF")
    on, onk, onn = load("ON")
    ids = sorted(set(off) | set(on))
    rows = []
    gate_bad = []
    for cid in ids:
        o = off.get(cid, [])
        a = on.get(cid, [])
        o_p, a_p = sum(o), sum(a)
        rows.append({"id": cid, "off": o_p, "on": a_p, "off_n": len(o), "on_n": len(a)})
        # gate: a case that was 4-5/5 in OFF but 0-2/5 in ON
        if o_p >= 4 and a_p <= 2:
            gate_bad.append(cid)
    orate = offk / offn if offn else 0
    arate = onk / onn if onn else 0
    oci = wilson(offk, offn)
    aci = wilson(onk, onn)
    diff = arate - orate
    gate_overall = abs(diff) <= 0.05
    rep = {
        "schema": "p1_mt20_5x_v1",
        "runs_per_arm": 5,
        "off": {"k": offk, "n": offn, "rate": round(orate, 4),
                "ci95": [round(x, 4) for x in oci]},
        "on": {"k": onk, "n": onn, "rate": round(arate, 4),
               "ci95": [round(x, 4) for x in aci]},
        "diff": round(diff, 4),
        "gate": {"overall_le_5pp": gate_overall,
                 "no_case_collapse": not gate_bad,
                 "collapsed_cases": gate_bad,
                 "pass": gate_overall and not gate_bad},
        "cases": rows,
        "verdict": ("开" if gate_overall and not gate_bad else "不开"),
    }
    json.dump(rep, open("out/P1-MT20-5X.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    md = ["# P1 · MT20 全量 5×（全关 vs 全开）", "",
          "| 臂 | pass | rate | 95%CI (Wilson) |", "|---|---|---|---|",
          "| 全关 | **%d/%d** | %.3f | [%.3f, %.3f] |" % (offk, offn, orate, *oci),
          "| 全开 | **%d/%d** | %.3f | [%.3f, %.3f] |" % (onk, onn, arate, *aci),
          "", "差值（开−关）= **%+.3f**（%.1f pp）" % (diff, diff * 100), "",
          "## 逐 case（5 次中的 pass 数）", "",
          "| case | 全关 | 全开 | 变化 |", "|---|---|---|---|"]
    for r in rows:
        d = r["on"] - r["off"]
        mark = "⚠️" if (r["off"] >= 4 and r["on"] <= 2) else ("↑" if d > 0 else ("↓" if d < 0 else "="))
        md.append("| %s | %d/%d | %d/%d | %s %+d |" % (r["id"], r["off"], r["off_n"],
                                                       r["on"], r["on_n"], mark, d))
    md += ["", "## 门判定", "",
           "- 总体差 ≤5pp：**%s**（实测 %+.3f）" % ("通过" if gate_overall else "不通过", diff),
           "- 无 case 从 4–5/5 掉到 0–2/5：**%s**%s"
           % ("通过" if not gate_bad else "不通过（%s）" % ",".join(gate_bad), ""),
           "", "结论：**%s**" % ("可开" if gate_overall and not gate_bad else "不开（系统性回归）")]
    open("out/P1-MT20-5X.md", "w", encoding="utf-8").write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()