# -*- coding: utf-8 -*-
"""Unit tests for the display stripper (no GPU).   python -X utf8 _test_display.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m4_display as D

TAG = D.CLOSE + ">"

CASES = [
    # name, input, expected
    ("tag_at_start", TAG + "\n\n我住在广陵路 12 号 2 单元 602。", "我住在广陵路 12 号 2 单元 602。"),
    ("tag_in_middle", "我住在广陵路 12 号 2 单元 602。\n\n" + TAG + "\n\n我住在广陵路 12 号 2 单元 602。",
     "我住在广陵路 12 号 2 单元 602。\n\n我住在广陵路 12 号 2 单元 602。"),
    ("tag_multiple", TAG + "\nA\n" + TAG + "\nB\n" + TAG, "A\nB"),
    ("closed_pair", "答案在" + D.OPEN + ">想一想" + TAG + "里面", "答案在里面"),
    ("unclosed_tail", "答案在前面。" + D.OPEN + ">还没想完", "答案在前面。"),
    ("no_tag_identical", "我住在广陵路 12 号 2 单元 602。\n\n答：就是这里。",
     "我住在广陵路 12 号 2 单元 602。\n\n答：就是这里。"),
    ("empty", "", ""),
]


def main():
    fails = []
    for name, src, want in CASES:
        got = D.strip_think(src)
        ok = got == want
        if name == "no_tag_identical":
            ok = ok and got is src or got == src
            ok = (got == want)
        print("%-20s %s  in=%r out=%r" % (name, "PASS" if ok else "FAIL", src[:34], got[:34]))
        if not ok:
            fails.append({"case": name, "got": got, "want": want})
    # the raw answer must survive untouched in the derived pair
    raw = "我住在广陵路 12 号 2 单元 602。\n\n我住在广陵路 12 号 2 单元 602。"
    pair = D.derive(raw)
    ok_raw = pair["answer"] == raw and TAG not in pair["answer_display"]
    print("%-20s %s  raw_kept=%s display=%r" % ("derive_pair", "PASS" if ok_raw else "FAIL",
                                                pair["answer"] == raw, pair["answer_display"]))
    if not ok_raw:
        fails.append({"case": "derive_pair", "pair": pair})
    print("\n%d case(s), %d failed" % (len(CASES) + 1, len(fails)))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
