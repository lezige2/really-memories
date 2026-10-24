# -*- coding: utf-8 -*-
"""Display-layer tests (no GPU).  python -X utf8 _test_display.py

Covers the inspector's R10 conditions: diff explainability, idempotence, byte-equality when there
is no tag, the adjacent and 100+ extremes, the four trace fields, and the content layer staying
separate from the structure layer.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m4_display as D

T, N = D.TAG, "\n"
CASES = [
    ("tag_at_start", T + N + N + "我住在广陵路 12 号 2 单元 602。", "我住在广陵路 12 号 2 单元 602。"),
    ("tag_in_middle", "我住在广陵路 12 号 2 单元 602。" + N + N + T + N + N +
     "我住在广陵路 12 号 2 单元 602。", "我住在广陵路 12 号 2 单元 602。" + N + N +
     "我住在广陵路 12 号 2 单元 602。"),
    ("tag_lines", T + N + "A" + N + T + N + "B", "A" + N + "B"),
    ("tag_adjacent", T + T + T + "X", "X"),
    ("tag_100", T * 120 + "答案", "答案"),
    ("closed_pair", D.OPEN + ">思考" + T + "答案", "答案"),
    ("unclosed_tail", "答案在前面。" + D.OPEN + ">还没想完", "答案在前面。"),
    ("only_tag", T, ""),
    ("no_tag_identical", "我住在广陵路 12 号 2 单元 602。" + N + N + "答：就是这里。",
     "我住在广陵路 12 号 2 单元 602。" + N + N + "答：就是这里。"),
    ("empty", "", ""),
]


def main():
    fails = []

    def chk(name, ok, detail=""):
        print("%-18s %s  %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append({"case": name, "detail": detail})

    for name, src, want in CASES:
        got = D.strip_think(src)
        chk(name, got == want, "in=%r out=%r" % (src[:26], got[:26]))
        d = D.audit(src)
        chk(name + ".diff", d["diff_explained"])
        chk(name + ".idem", D.strip_think(d["answer_display"]) == d["answer_display"])
        chk(name + ".fields", all(k in d for k in
                                 ("per_tag_count", "removed_chars", "display_len", "display_empty")))
        chk(name + ".coverage", d["per_tag_count"] == len(D.STRAY.findall(src)))
        if name == "no_tag_identical":
            chk(name + ".bytes", got is src or got == src)
            chk(name + ".hermetic", d["removed_chars"] == 0 and d["per_tag_count"] == 0
                and d["answer_display_changed"] is False)
        if name == "only_tag":
            chk(name + ".empty", d["display_empty"] is True and d["answer_display"] == "")

    raw = "我住在广陵路 12 号 2 单元 602。" + N + N + T + N + N + "我住在广陵路 12 号 2 单元 602。"
    d = D.derive(raw)
    chk("derive.raw_kept", d["answer"] == raw)
    chk("derive.display_clean", not D.has_tag(d["answer_display"]))
    chk("derive.tags", d["per_tag_count"] == 1 and d["removed_chars"] == 10)

    bad = [
        ("punctuation_changed", "答案 A 和 B。", "答案 A 和 B,"),
        ("char_deleted", "答案 A 和 B。", "答案 A 和"),
        ("tag_survived", T + "答案", "答案" + T),
        ("text_added", "答案 A", "答案 A 和"),
    ]
    for name, src, disp in bad:
        try:
            D.assert_diff_explained(src, disp)
            chk("reject." + name, False, "no exception")
        except D.DiffNotExplained as exc:
            chk("reject." + name, True, str(exc)[:40])

    chk("content.kept_out", D.strip_think("问：天气？答：晴。" + N + N + "问：天气？答：晴。")
        == "问：天气？答：晴。" + N + N + "问：天气？答：晴。")
    fs, meta = D.first_sentence_only("第一句。第二句。")
    chk("content.first_sentence", fs == "第一句。" and meta["first_sentence_only_applied"])
    chk("content.warn_types", "content_self_qa" in D.content_warnings("问：A？答：B。"))

    print(N + "%d case(s), %d failed" % (len(CASES) + 1, len(fails)))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
