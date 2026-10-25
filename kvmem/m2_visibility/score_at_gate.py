# -*- coding: utf-8 -*-
"""Metric validity gate for kvshim_score_at: the 1/3 positive-negative control.

Two configurations that differ ONLY in where the same 18-cell project block sits:

  (1) block [4078,4095] + question at 4096   -- known: generation normal AND memory adopted
  (3) block [4077,4094] + question at 4095   -- known: generation normal but memory NOT adopted

Each is scored twice: with the project block, and with the neutral 19-cell G18 block at the
same top (so the only difference is the content of the memory cells). Nothing else moves.

  Delta = S(project block) - S(G18 block)

Decision rule (fixed BEFORE looking at the numbers):
  * metric valid  <=> Delta(1) clearly > 0  AND  Delta(3) ~= 0
      clear       : delta_sum >= +0.50 nats  AND  delta_mean >= +0.05 nats/token
      ~= 0        : |delta_sum| <= 0.20 nats AND  |delta_mean| <= 0.02 nats/token
  * the two configurations must separate: delta_mean(1) - delta_mean(3) >= +0.05,
    otherwise the metric cannot tell "memory used" from "memory present but ignored" and
    every downstream number is meaningless.

Run: python -X utf8 kvmem/m2_visibility/score_at_gate.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import score_lib as S                     # noqa: E402
import m2_visibility_probe as P           # noqa: E402

OUT = os.path.join(P.WORK_DIR, "evidence", "score_at")
PRIMARY = "3 月 14 日上线"                 # the fact content of the project block
SECONDARY = "项目在3月14日上线"            # the answer the model actually gives when it recalls

CLEAR_SUM, CLEAR_MEAN = 0.50, 0.05
ZERO_SUM, ZERO_MEAN = 0.20, 0.02
SEP_MEAN = 0.05


def run_one(eng, man, top, ask_pos):
    """Same block, same question, two memory contents, one geometry."""
    prompt = P.K.turn(P.FULL["project"]["q"])
    out = {"top": top, "ask_pos": ask_pos, "prompt": prompt, "blocks": {}}
    for slot, sid, bid, fam in [(1, "project", "project", "m2"),
                                (1, "base", "blk_g18_nb", S.NEUTRAL)]:
        lay = S.layout([(slot, sid, bid, fam)], top=top, man=man)
        placed = S.place(eng, lay)
        ans_text = S.score(eng, lay, placed, prompt, PRIMARY, ask_pos)
        ans_alt = S.score(eng, lay, placed, prompt, SECONDARY, ask_pos)
        eng.reset(P.LIVE)
        P.share_layout(eng, lay, placed)
        generated = eng.ask(P.LIVE, P.FULL["project"]["q"], n_predict=P.N_PREDICT,
                            pos=ask_pos)
        out["blocks"][bid] = {
            "geometry": S.segments_text(lay), "placed": placed,
            "score_primary": ans_text, "score_secondary": ans_alt,
            "generated": generated.strip(),
            "fact_ok": P.fact_ok(P.FULL["project"]["fact"], generated),
        }
        print("    %-8s [%4d,%4d) %2d cells  S_sum=%9.4f S_mean=%8.4f | gen=%r"
              % (bid, lay["segments"][0]["pos_lo"], lay["segments"][0]["pos_hi"],
                 lay["segments"][0]["cells"], ans_text["sum"], ans_text["mean"],
                 generated.strip()[:24]))
    for key in ("primary", "secondary"):
        src = "score_" + key
        d = {m: out["blocks"]["project"][src][m] - out["blocks"]["blk_g18_nb"][src][m]
             for m in ("sum", "mean", "last")}
        d["n_project"] = out["blocks"]["project"][src]["n"]
        d["n_base"] = out["blocks"]["blk_g18_nb"][src]["n"]
        d["per_token_delta"] = [
            {"token": tp, "piece": out["blocks"]["project"][src]["piece_list"][i],
             "lp_project": out["blocks"]["project"][src]["logprobs"][i],
             "lp_base": out["blocks"]["blk_g18_nb"][src]["logprobs"][i],
             "d": out["blocks"]["project"][src]["logprobs"][i]
                  - out["blocks"]["blk_g18_nb"][src]["logprobs"][i]}
            for i, tp in enumerate(out["blocks"]["project"][src]["tokens"])]
        out["delta_" + key] = d
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    man = S.manifest()
    res = {"schema": "score_at_gate_v1", "primary": PRIMARY, "secondary": SECONDARY,
           "rule": {"clear_sum": CLEAR_SUM, "clear_mean": CLEAR_MEAN,
                    "zero_sum": ZERO_SUM, "zero_mean": ZERO_MEAN, "sep_mean": SEP_MEAN}}
    eng = P.open_engine()
    try:
        for name, top in (("case1", P.CHAT), ("case3", P.CHAT - 1)):
            P.reset_all(eng)
            print("== %s: block [%d,%d) + question at %d" % (name, top - 18, top - 1, top))
            res[name] = run_one(eng, man, top, top)
            d = res[name]["delta_primary"]
            print("    Delta(state) sum=%+.6f mean=%+.6f last=%+.6f"
                  % (d["sum"], d["mean"], d["last"]))
            d2 = res[name]["delta_secondary"]
            print("    Delta(natural answer) sum=%+.6f mean=%+.6f" % (d2["sum"], d2["mean"]))
    finally:
        eng.close()

    d1 = res["case1"]["delta_primary"]
    d3 = res["case3"]["delta_primary"]
    d1b, d3b = res["case1"]["delta_secondary"], res["case3"]["delta_secondary"]
    clear1 = (d1["sum"] >= CLEAR_SUM) and (d1["mean"] >= CLEAR_MEAN)
    zero3 = (abs(d3["sum"]) <= ZERO_SUM) and (abs(d3["mean"]) <= ZERO_MEAN)
    sep = (d1["mean"] - d3["mean"]) >= SEP_MEAN
    verdict = {
        "case1_clearly_positive": bool(clear1),
        "case3_about_zero": bool(zero3),
        "configs_separate": bool(sep),
        "metric_valid": bool(clear1 and zero3 and sep),
        "d1": {"sum": d1["sum"], "mean": d1["mean"]},
        "d3": {"sum": d3["sum"], "mean": d3["mean"]},
        "secondary": {"d1_sum": d1b["sum"], "d1_mean": d1b["mean"],
                      "d3_sum": d3b["sum"], "d3_mean": d3b["mean"],
                      "case1_positive": d1b["sum"] > 0, "case3_about_zero":
                      abs(d3b["mean"]) <= ZERO_MEAN},
    }
    res["verdict"] = verdict
    path = os.path.join(OUT, "gate.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print()
    print("VERDICT: case1 clear>0=%s (sum %+.4f / mean %+.4f) | case3 ~0=%s (sum %+.4f / mean %+.4f)"
          " | separated=%s | METRIC VALID=%s"
          % (clear1, d1["sum"], d1["mean"], zero3, d3["sum"], d3["mean"], sep,
             verdict["metric_valid"]))
    print("primary rule: clear sum>=%.2f mean>=%.2f ; zero |sum|<=%.2f |mean|<=%.2f ; sep mean>=%.2f"
          % (CLEAR_SUM, CLEAR_MEAN, ZERO_SUM, ZERO_MEAN, SEP_MEAN))
    print("secondary (natural answer): d1 sum=%+.4f mean=%+.4f | d3 sum=%+.4f mean=%+.4f"
          % (d1b["sum"], d1b["mean"], d3b["sum"], d3b["mean"]))
    print("gate -> %s" % path)
    return 0 if verdict["metric_valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
