# -*- coding: utf-8 -*-
"""verdict() 表驱动测试：十二行，无引擎、毫秒级。

每行断言四样：退出码 / instrument / hits 完整有序 / is_red 与退出码正交。
不变式：hits 非空 <=> 码 5。
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m4c_harness as H

CUR = H.harness_sha16()


def rec(**kw):
    base = {"harness_sha16": CUR, "finalized": True, "asserts_ran": 2,
            "finalize_error": None, "coverage_ok": True, "is_red": False,
            "expected_red": kw.pop("expected_red", False), "def_mismatch": False,
            "covers_observed": ["site3"], "covers_declared": ["site3"]}
    base.update(kw); return base


ROWS = [
    ("pass_green",         rec(),                                    False, 0, None, []),
    ("pass_red",           rec(is_red=True),                         True,  0, None, []),
    ("no_discrimination",  rec(is_red=False),                        True,  5, "no_discrimination", ["no_discrimination"]),
    ("subject_broken",     rec(is_red=True),                         False, 1, None, []),
    ("stale",              rec(harness_sha16="deadbeefdeadbeef"),    False, 5, "stale", ["stale"]),
    ("not_finalized",      rec(finalized=False, asserts_ran=0),      False, 5, "not_finalized", ["not_finalized"]),
    ("finalize_error",     rec(finalized=False, asserts_ran=1, finalize_error="AssertionError('x')"),
                                                                     False, 5, "not_finalized", ["not_finalized", "finalize_error"]),
    ("coverage_shape",     rec(coverage_ok=None),                    False, 5, "coverage_shape", ["coverage_shape"]),
    ("coverage_not_met",   rec(coverage_ok=False),                   False, 5, "coverage_not_met", ["coverage_not_met"]),
    ("covered_but_red",    rec(coverage_ok=False, is_red=True),      False, 5, "coverage_not_met", ["coverage_not_met"]),
    ("not_met_and_blind",  rec(coverage_ok=False, is_red=False),     True,  5, "coverage_not_met", ["coverage_not_met", "no_discrimination"]),
    ("self_contradiction", rec(is_red=None),                         False, 5, "self_contradiction", ["self_contradiction"]),
    ("def_mismatch",       rec(def_mismatch=True),                   False, 5, "def_mismatch", ["def_mismatch"]),
]


def main():
    bad = 0
    for name, r, expect_red, want_code, want_inst, want_hits in ROWS:
        before = r.get("is_red")
        r["expected_red"] = expect_red
        code = H.verdict(r)
        ok = (code == want_code and r.get("instrument") == want_inst
              and r.get("instrument_hits") == want_hits and r.get("is_red") is before)
        inv = bool(r.get("instrument_hits")) == (code == 5)
        print("%-20s code=%d want=%d inst=%-18r hits=%s inv=%s %s"
              % (name, code, want_code, r.get("instrument"), r.get("instrument_hits"),
                 inv, "OK" if (ok and inv) else "FAIL"))
        if not (ok and inv):
            bad += 1
    print("rows=%d fail=%d" % (len(ROWS), bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
