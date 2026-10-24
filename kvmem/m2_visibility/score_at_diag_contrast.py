# -*- coding: utf-8 -*-
"""POST-HOC DIAGNOSTIC (not the pre-registered metric).

The pre-registered Delta (score of the fact string with the project block minus the same
score with a neutral block) is ~+2.6 nats/token in BOTH configurations, so it cannot tell
"memory adopted" from "memory read but not used" -- see gate.json.

This asks whether ANY score-based variant separates them. Instead of the absolute score of
the fact string it measures PREFERENCE: the fact continuation against the continuation the
unhelpful configuration actually produces.

  margin(geometry, block) = mean_logprob("项目在3月14日上线") - mean_logprob("项目什么时候上线")
  Delta_margin            = margin(project) - margin(neutral)

Run: python -X utf8 kvmem/m2_visibility/score_at_diag_contrast.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import score_lib as S                     # noqa: E402
import m2_visibility_probe as P           # noqa: E402

OUT = os.path.join(P.WORK_DIR, "evidence", "score_at")
FACT = "项目在3月14日上线"
ECHO = "项目什么时候上线"


def main():
    man = S.manifest()
    prompt = P.K.turn(P.FULL["project"]["q"])
    res = {"schema": "score_at_diag_contrast_v1", "fact": FACT, "echo": ECHO, "cases": {}}
    eng = P.open_engine()
    try:
        for name, top in (("case1", P.CHAT), ("case3", P.CHAT - 1)):
            P.reset_all(eng)
            row = {"top": top, "ask_pos": top, "blocks": {}}
            print("== %s: block [%d,%d), question at %d" % (name, top - 18, top - 1, top))
            for bid, fam in (("project", "m2"), ("blk_g18_nb", S.NEUTRAL)):
                lay = S.layout([(1, "b", bid, fam)], top=top, man=man)
                placed = S.place(eng, lay)
                f = S.score(eng, lay, placed, prompt, FACT, top)
                e = S.score(eng, lay, placed, prompt, ECHO, top)
                row["blocks"][bid] = {
                    "fact": {"mean": f["mean"], "sum": f["sum"], "n": f["n"],
                             "logprobs": f["logprobs"]},
                    "echo": {"mean": e["mean"], "sum": e["sum"], "n": e["n"],
                             "logprobs": e["logprobs"]},
                    "margin_mean": f["mean"] - e["mean"],
                }
                print("    %-10s fact_mean=%8.4f echo_mean=%8.4f margin=%+8.4f"
                      % (bid, f["mean"], e["mean"], f["mean"] - e["mean"]))
            d = (row["blocks"]["project"]["margin_mean"]
                 - row["blocks"]["blk_g18_nb"]["margin_mean"])
            row["delta_margin"] = d
            print("    Delta_margin = %+.4f" % d)
            res["cases"][name] = row
    finally:
        eng.close()

    d1 = res["cases"]["case1"]["delta_margin"]
    d3 = res["cases"]["case3"]["delta_margin"]
    res["verdict"] = {"d_margin_case1": d1, "d_margin_case3": d3,
                      "separates": bool(d1 > 0 and abs(d3) <= 0.2 * max(d1, 1e-9))}
    path = os.path.join(OUT, "diag_contrast.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print()
    print("Delta_margin: case1 %+.4f | case3 %+.4f | separates=%s"
          % (d1, d3, res["verdict"]["separates"]))
    print("-> %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
