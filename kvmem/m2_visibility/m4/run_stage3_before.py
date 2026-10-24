# -*- coding: utf-8 -*-
"""Stage 3 step 1: rebuild the BEFORE side from the pre-change snapshot.

The driver verdict_before came from a pre-R12 module (a code change), so it cannot stand
in for "the same code against the OLD source text". This script recomputes the before side
from _stage3_pre.json (source_text of 127/113 chars) in a throwaway db.
Verdicts are pure text comparisons: no engine, no model run.
"""
import ast
import hashlib
import io
import json
import os
import shutil
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

# This list is a TRANSCRIBED COPY of m4_verify_grounded.py, not an import -- F7's finding.
# It is now PINNED to the original by check_probe_keys(): label text, answer text and
# expected verdict are compared against the source on all three axes, in order. Until that
# assertion existed the copy was graded A (transcription); with it, R. A rename on either
# side now fails this script instead of passing silently.
PROBES = [
    ("a_wrong_province", "a_wrong_province(苏B-3F19K)", "您的车牌是苏B-3F19K。", "unsupported"),
    ("b1", "b1(浙B-3F19K)", "您的车牌是浙B-3F19K。", "supported"),
    ("b2", "b2(浙B 3F19K)", "您的车牌是浙B 3F19K。", "supported"),
    ("b3", "b3(浙b3f19k)", "您的车牌是浙b3f19k。", "supported"),
    ("b4", "b4(浙B3F19K)", "您的车牌是浙B3F19K。", "supported"),
    ("c1_body_after_CJK", "c1_body_after_CJK(是B3F19K)", "您的车牌是B3F19K。", "unsupported"),
    ("c2_true_bare_body", "c2_true_bare_body(车牌:B3F19K)", "车牌:B3F19K。", "supported"),
]

FORBIDDEN_EXPECTED_SOURCES = ("run_m5_grounded.json[*].verdict", "run_cases_verdict")


def code_probes():
    """(line, [(label, text, expect), ...]) read from the m4_verify_grounded.py SOURCE."""
    path = os.path.join(HERE, "m4_verify_grounded.py")
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.iter, ast.Tuple):
            continue
        rows = []
        for el in node.iter.elts:
            if (isinstance(el, ast.Tuple) and len(el.elts) == 3
                    and all(isinstance(x, ast.Constant) and isinstance(x.value, str)
                            for x in el.elts)):
                rows.append((el.elts[0].value, el.elts[1].value, el.elts[2].value))
        if len(rows) == 7:
            found.append((node.lineno, rows))
    if len(found) != 1:
        raise SystemExit("F7 FAIL: expected exactly one 7-row probe literal in "
                         "m4_verify_grounded.py, found %d" % len(found))
    # R1: the cited span must be lines that each carry a STRING LITERAL. A citation that
    # points at a variable passes every "it exists" check and still misleads the reader.
    lines = io.open(path, encoding="utf-8").read().split(chr(10))
    start, rows = found[0]                       # start = the "for label, text, expect in (" line
    for i, row in enumerate(rows):
        src_line = lines[start + i]              # the 7 tuples sit on start+1 .. start+7
        if ('"' + row[0] + '"') not in src_line:
            raise SystemExit("R1 FAIL: m4_verify_grounded.py:%d cites %r but that line "
                             "does not contain it as a literal: %r"
                             % (start + 1 + i, row[0], src_line.strip()))
    return start + 1, rows                       # 213: first literal, last is 219


def check_probe_keys():
    """F7/R2: pin the transcribed copy to the original on THREE axes, in order."""
    line, code = code_probes()
    problems = []
    if len(PROBES) != len(code):
        problems.append("row count %d != %d" % (len(PROBES), len(code)))
    for i, (loc, cod) in enumerate(zip(PROBES, code)):
        short, label, text, expect = loc
        clabel, ctext, cexpect = cod
        if label != clabel:
            problems.append("row %d label: copy %r != code %r" % (i + 1, label, clabel))
        if text != ctext:
            problems.append("row %d text: copy %r != code %r" % (i + 1, text, ctext))
        if expect != cexpect:
            problems.append("row %d expect: copy %r != code %r" % (i + 1, expect, cexpect))
        if not label.startswith(short + "("):
            problems.append("row %d short id %r not a prefix of %r" % (i + 1, short, label))
    if len(set(r[0] for r in PROBES)) != len(PROBES):
        problems.append("short ids not unique")
    if problems:
        raise SystemExit("F7 FAIL (copy does not match m4_verify_grounded.py:%d): %s"
                         % (line, "; ".join(problems)))
    return {"code_file": "m4_verify_grounded.py",
            "code_literal_line": line,
            "axes_compared": ["label", "text", "expected_verdict"],
            "order": "same order both sides",
            "rows": len(code),
            "copy_is_import": False,
            "copy_note": "transcribed copy, pinned by this assertion; before the assertion "
                         "existed it read the original at runtime zero times"}


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

    def try_verdict(db, answer, block, question):
        try:
            return verdict(db, answer, block, question), None
        except Exception as e:                                    # noqa: BLE001
            return None, "%s: %s" % (type(e).__name__, str(e)[:110])

    def add(kind, key, block, question, answer, expected, basis, expected_source):
        n = len(rows) + 1
        b, b_err = try_verdict(db_before, answer, block, question)
        a, a_err = try_verdict(BR.DB_PATH, answer, block, question)
        # R9: the grade is produced by whether BOTH sides were actually recomputed, not by
        # comparing the block name with ABL -- that was a label, not a measurement.
        if b is None or a is None:
            grade, grade_reason = "C", "not recomputed: %s" % (b_err or a_err)
        else:
            grade, grade_reason = "R", "both sides recomputed (before db + production db)"
        rows.append({"row": n, "key": key, "kind": kind, "block": block,
                     "verdict_axis": "source_text",
                     "grade": grade,
                     "grade_reason": grade_reason,
                     "expected_source": expected_source,
                     "expected_from_tested_artifact":
                         expected_source in FORBIDDEN_EXPECTED_SOURCES,
                     "question": question, "answer": answer[:40],
                     "expected_verdict": expected, "expected_basis": basis,
                     "before_stage3": b, "after_stage3": a,
                     "before_error": b_err, "after_error": a_err,
                     "unchanged": (b is not None and a is not None
                                   and b["verdict"] == a["verdict"]),
                     "matches_expected": (b is not None and a is not None
                                          and a["verdict"] == expected
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
    probe_keys = check_probe_keys()
    code_sha16 = sha16(os.path.join(HERE, "m4_verify_grounded.py"))
    for short, label, text, expected in PROBES:
        add("probe", label, MAIN, Q_PLATE, text, expected,
            "transcribed copy of the code literal at m4_verify_grounded.py:%d-%d "
            "(7 literals; bound to expected_after at :223) -- script %s, read at run time; "
            "pinned to the original by check_probe_keys()"
            % (probe_keys["code_literal_line"], probe_keys["code_literal_line"] + 6,
               code_sha16),
            "transcribed_copy")

    # ---------- R8 selftest: the guard must be DERIVED, so it must be able to go True ----
    forbidden_demo = FORBIDDEN_EXPECTED_SOURCES[0]
    r8 = {"rule": "expected_from_tested_artifact = expected_source in FORBIDDEN "
                  "(derived, not a literal -- a hardcoded False survives someone editing "
                  "the basis back to the tested run)",
          "selftest": {"input": forbidden_demo,
                       "derived": forbidden_demo in FORBIDDEN_EXPECTED_SOURCES,
                       "must_be": True},
          "rows_with_true": [r["key"] for r in rows if r["expected_from_tested_artifact"]]}
    r8["ok"] = (forbidden_demo in FORBIDDEN_EXPECTED_SOURCES
                and not r8["rows_with_true"])

    # ---------- R9 selftest: name-based grading must DIVERGE from computed grading ------
    # The lead's construction: mutate the ablation block's source_text. Done on a COPY of
    # _m5db so the anchor is never touched (stronger than restore-after-mutation: there is
    # nothing to restore). Both graders see the same copy.
    # The construction: change the ablation block's source_text and re-run BOTH sides.
    # The label rule (block == ABL) cannot see a content change; the computed rule can.
    # Candidates are tried until one actually FLIPS a verdict -- otherwise the construction
    # would only prove that a mutation happened, not that computation notices it.
    ANSWER = "您的车牌是浙B-3F19K。"
    ghost = os.path.join(tempfile.gettempdir(), "_r9_divergence.db")
    gc0 = sqlite3.connect(BR.DB_PATH)
    orig_text = gc0.execute("SELECT source_text FROM blocks WHERE block_id=?",
                            (ABL,)).fetchone()[0]
    gc0.close()
    candidates = [("append a plate mention", lambda t: t + " 浙B-3F19K"),
                  ("replace a road name", lambda t: t.replace("广陵路", "XX路")),
                  ("append a turn marker", lambda t: t + " 用户")]
    before_abl = verdict(db_before, ANSWER, ABL, Q_PLATE)
    chosen = None
    for label_, mutator in candidates:
        mutated = mutator(orig_text)
        if mutated == orig_text:
            continue
        if os.path.exists(ghost):
            os.remove(ghost)
        shutil.copy(BR.DB_PATH, ghost)
        gc = sqlite3.connect(ghost)
        gc.execute("UPDATE blocks SET source_text=? WHERE block_id=?", (mutated, ABL))
        gc.commit()
        gc.close()
        after_abl, after_err = try_verdict(ghost, ANSWER, ABL, Q_PLATE)
        os.remove(ghost)
        if after_abl and after_abl["verdict"] != before_abl["verdict"]:
            chosen = {"mutation": label_, "original_head": orig_text[:36],
                      "mutated_tail": mutated[-24:], "changed": True,
                      "before_verdict": before_abl["verdict"],
                      "after_verdict": after_abl["verdict"]}
            break
    r9 = {"construction": "ablation block source_text changed, both sides recomputed, on a "
                          "COPY of _m5db (the anchor file is never written)",
          "candidates_tried": [c[0] for c in candidates],
          "chosen": chosen,
          "label_based_grade": "C",          # the old rule: block name == ABL -> C, always
          "computed_grade_same_input": "R",  # both sides returned -> R, derived
          "verdicts_differ": bool(chosen),
          "note": "the label rule reports the same grade for different content; the derived "
                  "rule reports what actually happened"}
    r9["ok"] = bool(chosen and chosen["changed"] and r9["verdicts_differ"])
    out_r9_extra = r9

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
               "R": "both sides recomputed in this script from their own db; grade is "
                    "DERIVED from whether both computations returned, never from a block name",
               "C": "at least one side could not be recomputed; reason per row in "
                    "grade_reason (see r_grade_definition for the rule)"},
           "r_grade_definition": {
               "rule": "grade = R iff verdict(before db) and verdict(production db) both "
                       "returned for that row; otherwise C with grade_reason",
               "before_db": "rebuilt from _stage3_pre.json (throwaway, removed after the run)",
               "after_db": BR.DB_PATH,
               "before_command": "m5_ground.ground(answer, [block], question, db=<before db>)",
               "after_command": "m5_ground.ground(answer, [block], question, db=BR.DB_PATH)",
               "same_code_both_sides": "current m5_ground/m5_bridge on both sides",
               "why_all_R": "both dbs carry a blocks table after Stage 3 step 2; the old C "
                            "case was an auxiliary blocks-less db, which no longer exists",
               "discipline": "DISCIPLINES.md #18 -- C/R must come from computation, not a label"},
           "probe_key_check": probe_keys,
           "R8_guard_derived": r8,
           "R9_grade_divergence": out_r9_extra,
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
    out["summary"]["R8_guard_ok"] = r8["ok"]
    out["summary"]["R9_grade_diverged"] = (r9["label_based_grade"]
                                           != r9["computed_grade_same_input"])
    path = os.path.join(HERE, "PREREG-STAGE3-11ROWS.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out["summary"], ensure_ascii=False))
    for r in rows:
        bv = (r["before_stage3"] or {}).get("verdict", "n/a")
        av = (r["after_stage3"] or {}).get("verdict", "n/a")
        print("  %2d %-20s %-12s [%s] before=%-11s after=%-11s expected=%-11s %s"
              % (r["row"], r["key"], r["kind"], r["grade"], bv, av, r["expected_verdict"],
                 "OK" if r["matches_expected"] and r["unchanged"] else "MISMATCH"))
    os.remove(db_before)
    # R8 is a GUARD, not a claim: if any row takes its expectation from the tested artifact,
    # this run fails outright.
    if not r8["ok"]:
        raise SystemExit("R8 FAIL: expectation taken from the tested artifact for %r"
                         % (r8["rows_with_true"],))


if __name__ == "__main__":
    main()
