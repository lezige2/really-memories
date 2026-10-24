# -*- coding: utf-8 -*-
"""Backfill the accounting fields the lead asked for. Nothing already recorded is altered;
every added block says it was appended after the run and on what basis."""
import json, os
D = os.path.dirname(os.path.abspath(__file__))
STAMP = "appended_after_run"

def patch(tag, fn):
    p = os.path.join(D, "out", tag + ".json")
    d = json.load(open(p, encoding="utf-8"))
    fn(d)
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
    return p

# 1. the np24 batch: the field did not exist when these were written.
for tag in ("run0_r1", "run0_r2", "E_r1", "E_r2", "F_r1", "F_r2",
            "X1_r1", "X1_r2", "B57_r1", "B57_r2"):
    def f(d, tag=tag):
        d["runner"]["n_predict_declared"] = 24
        d["runner"]["n_predict_declared_basis"] = (
            "backfilled; P.N_PREDICT default (tools/m2_visibility_probe.py:103); the "
            "runner.n_predict key did not exist when this run was written")
        d["runner"]["n_predict_declared_stamp"] = STAMP
    patch(tag, f)

# 2. run0 used a control window that the 7B get_control semantics would not produce.
for tag in ("run0_r1", "run0_r2"):
    def f(d):
        d["control_window_override"] = {
            "applied": True, "control_start": 3886, "target_n": 210,
            "why": "iso_home_only has layout start 4075 (21 cells); the control prefix is "
                   "67 tokens, so get_control's default target_n = 4096-4075 = 21 cannot "
                   "hold it. The control TEXT window was forced to 3886/210 (the same "
                   "window the four cells use). Placement geometry was NOT changed: "
                   "pos_lo/pos_hi stayed 4075/4096.",
            "differs_from_7b_get_control_semantics": True,
            "four_cells_same_override": "no-op there: layout start == 3886 already",
            "stamp": STAMP}
    patch(tag, f)

# 3. P1_pp18: record both readings rather than a bare false.
for tag in ("P1_pp18_r1", "P1_pp18_r2"):
    def f(d):
        a = d["answers"][0]
        sem = any(k in a["answer"] for k in ("三月十四", "3月14", "3 月 14"))
        d["answers"][0]["fact_ok_literal"] = a["ok"]
        d["answers"][0]["semantic_ok"] = bool(sem)
        d["answers"][0]["verdict_note"] = (
            "literal miss, semantic hit: expected %r, model wrote 三月十四号 (Chinese "
            "numerals). Not a payload failure." % a["expected"])
        d["answers"][0]["note_stamp"] = STAMP
    patch(tag, f)

print("backfilled")
for tag in ("run0_r1", "E_r1", "B57_r2"):
    d = json.load(open(os.path.join(D, "out", tag + ".json"), encoding="utf-8"))
    print(tag, "runner.n_predict=", d["runner"].get("n_predict"),
          "declared=", d["runner"].get("n_predict_declared"),
          "| control_window_override=", d.get("control_window_override", {}).get("applied"))
d = json.load(open(os.path.join(D, "out", "P1_pp18_r1.json"), encoding="utf-8"))["answers"][0]
print("P1_pp18_r1 literal=%s semantic=%s" % (d["fact_ok_literal"], d["semantic_ok"]))
