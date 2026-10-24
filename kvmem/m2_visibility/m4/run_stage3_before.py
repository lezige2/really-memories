# -*- coding: utf-8 -*-
"""Stage 3 step 1: rebuild the BEFORE side from the pre-change snapshot.

The driver verdict_before came from a pre-R12 module (a code change), so it cannot stand
in for "the same code against the OLD source text". This script recomputes the before side
from _stage3_pre.json (source_text of 127/113 chars) in a throwaway db.
Verdicts are pure text comparisons: no engine, no model run.
"""
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "m5"))

import m5_bridge as BR                                              # noqa: E402
import m5_ground as G                                               # noqa: E402

PRE = os.path.join(HERE, "_stage3_pre.json")
MAIN = "blk_conv_2026-10-25_01"
ABL = "blk_conv_noplate_2026-10-25_01"
Q_PLATE = "我车牌号是多少？"
Q_HOME = "我住在哪？"

PROBES = [
    ("a_wrong_province", "您的车牌是苏B-3F19K。", "unsupported"),
    ("b1", "您的车牌是浙B-3F19K。", "supported"),
    ("b2", "您的车牌是浙B 3F19K。", "supported"),
    ("b3", "您的车牌是浙b3f19k。", "supported"),
    ("b4", "您的车牌是浙B3F19K。", "supported"),
    ("c1_body_after_CJK", "您的车牌是B3F19K。", "unsupported"),
    ("c2_true_bare_body", "车牌:B3F19K。", "supported"),
]


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def build_before_db():
    pre = json.load(open(PRE, encoding="utf-8"))
    db = os.path.join(tempfile.gettempdir(), "_stage3_before.db")
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    con.executescript(BR.SCHEMA)
    for bid, d in pre["rows"].items():
        # the pre snapshot predates the synthetic column; the flag is DERIVED from the
        # origin prefix, which is exactly the definition the CHECK enforces.
        row = dict(d)
        row["synthetic"] = 1 if str(d["text_origin"]).startswith("declared_synthetic:") else 0
        cols = list(row)
        sql = "INSERT INTO blocks (%s) VALUES (%s)" % (",".join(cols),
                                                       ",".join("?" * len(cols)))
        con.execute(sql, tuple(row[c] for c in cols))
    con.commit()
    con.close()
    return db, pre


def verdict(db, answer, block, question):
    r = G.ground(answer, [block], question, db=db)
    return {"verdict": r["verdict"], "reason": r.get("reason"),
            "source_problems": r.get("source_problems")}


def main():
    db_before, pre = build_before_db()
    cur = json.load(open(os.path.join(HERE, "run_m5_grounded.json"), encoding="utf-8"))
    by = {c["case"]: c for c in cur["cases"]}
    rows = []

    def add(kind, key, block, question, answer, expected, basis, expected_source):
        n = len(rows) + 1
        b = verdict(db_before, answer, block, question)
        a = verdict(BR.DB_PATH, answer, block, question)
        unchanged_input = (block == ABL)
        rows.append({"row": n, "key": key, "kind": kind, "block": block,
                     "verdict_axis": "source_text",
                     "grade": "C" if unchanged_input else "R",
                     "expected_source": expected_source,
                     "expected_from_tested_artifact": False,
                     "question": question, "answer": answer[:40],
                     "expected_verdict": expected, "expected_basis": basis,
                     "before_stage3": b, "after_stage3": a,
                     "unchanged": b["verdict"] == a["verdict"],
                     "matches_expected": (a["verdict"] == expected
                                          and b["verdict"] == expected)})

    # The 4 product rows: the expectation is the FROZEN CRITERION (the verdict must not move
    # when only the source text changes) evaluated on the REBUILT BEFORE SIDE -- never the
    # run's own verdict field, which would make matches_expected a tautology.
    for case, q, block in (("plate_main", Q_PLATE, MAIN),
                           ("plate_ablated", Q_PLATE, ABL),
                           ("home_main", Q_HOME, MAIN),
                           ("home_ablated", Q_HOME, ABL)):
        c = by[case]
        before_v = verdict(db_before, c["display_pre_grounding"], block, c["question"])
        add("product_case", case, block, c["question"], c["display_pre_grounding"],
            before_v["verdict"],
            "frozen criterion: the verdict must not move when only the source text changes; "
            "expectation = rebuilt before side (%s), not run_m5_grounded.json[*].verdict"
            % before_v["verdict"],
            "rebuilt_before_side")
    for label, text, expected in PROBES:
        add("probe", label, MAIN, Q_PLATE, text, expected,
            "code literal: m4_verify_grounded.py:223 expected_after (script 9247e3fa, pre-Stage3)",
            "code_literal")

    rg = os.path.join(HERE, "run_m5_grounded.json")
    run_at = (cur.get("at") or cur.get("run_at")
              or time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(rg))))
    run_sha16 = sha16(rg)
    out = {"schema": "stage3_11rows_v1",
           "product_kind": "reconstruction",
           "verdict_axis": "source_text",
           "axes_note": "this file is the SOURCE-TEXT axis. run_m5_grounded.json''s "
                        "before_after.verdict_before is the CODE axis (a pre-R12 module); "
                        "comparing across axes yields the false finding "
                        "plate_main: Stage 3 turned unsupported into supported.",
           "after_side_run": {"file": "run_m5_grounded.json", "sha16": run_sha16,
                              "run_time": run_at,
                              "run_time_source": "file mtime: the run json has no timestamp field"},
           "authored_after_run": True,
           "authored_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "authored_after_run_time": time.strftime("%Y-%m-%dT%H:%M:%S") > run_at,
           "why_after_run": "the 4 product rows had no machine expectation before the run; "
                            "writing one afterwards and calling it pre-registration would be "
                            "back-dating",
           "same_code_both_sides": "both sides use the CURRENT m5_ground/m5_bridge; only the "
                                   "source_text differs",
           "expected_sources": {
               "product_case": "rebuilt before side (frozen criterion: verdict must not move)",
               "probe": "code literal in m4_verify_grounded.py:223 (pre-Stage3)",
               "forbidden": "run_m5_grounded.json[*].verdict -- using it makes the check a "
                            "tautology (discipline 10)"},
           "before_provenance": {"file": "_stage3_pre.json", "sha16": sha16(PRE),
                                 "synthetic_derivation": "absent in the snapshot; derived from the origin prefix (declared_synthetic: => 1)",
                                 "note": "reconstruction, NOT a pre-registration"},
           "rows": rows,
           "evidence_grades": {
               "R": "recomputed independently in this script (both sides)",
               "C": "constructive coverage: the input is byte-identical on both sides, so the "
                    "result rests on unchanged input metadata, not on a fresh computation"},
           "summary": {"rows": len(rows),
                       "R_rows": 0, "C_rows": 0,
                       "unchanged": sum(1 for r in rows if r["unchanged"]),
                       "all_unchanged": all(r["unchanged"] for r in rows),
                       "all_match_expected": all(r["matches_expected"] for r in rows)}}
    out["summary"]["R_rows"] = sum(1 for r in rows if r["grade"] == "R")
    out["summary"]["C_rows"] = sum(1 for r in rows if r["grade"] == "C")
    out["summary"]["statement"] = ("source-text axis: %d rows R (recomputed) + %d rows C "
                                  "(constructive)" % (out["summary"]["R_rows"],
                                                      out["summary"]["C_rows"]))
    path = os.path.join(HERE, "PREREG-STAGE3-11ROWS.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out["summary"], ensure_ascii=False))
    for r in rows:
        print("  %2d %-20s %-12s [%s] before=%-11s after=%-11s expected=%-11s %s"
              % (r["row"], r["key"], r["kind"], r["grade"], r["before_stage3"]["verdict"],
                 r["after_stage3"]["verdict"], r["expected_verdict"],
                 "OK" if r["matches_expected"] and r["unchanged"] else "MISMATCH"))
    os.remove(db_before)


if __name__ == "__main__":
    main()
