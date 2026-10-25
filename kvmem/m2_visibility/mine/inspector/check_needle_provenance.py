# -*- coding: utf-8 -*-
"""纪律 27 的常驻断言：判据里的字面量必须先证明它【在】被判对象里，
并同时证明它的【边界变体不在】—— 只验「在」挡不住「针被写松了也能过」。

用法:
  python -X utf8 check_needle_provenance.py --json <f> --key block_text \
         --needle "G" --boundary-strip-space --require 602
  python -X utf8 check_needle_provenance.py --json <f> --key block_text \
         --needle "T" --require 602            # 必须红（针太松 / 针不在）

被驱动调用（跑第一轮之前）:
  from check_needle_provenance import assert_needle
  assert_needle(block_text, NEEDLE, boundary=NEEDLE.replace(" ", ""), require="602")

UNCOVERED（射程，给读结论的人，不只写在 docstring 里）:
  1. 不能证明「这根针是对的那根」—— 后者只能靠人看上下文
  2. 不检查被判对象本身是否选对 —— 只保证针与该对象的关系
"""
import argparse, json, sys

UNCOVERED = (
    "UNCOVERED: 1. cannot prove THIS needle is the right one (a human must read the context)",
    "           2. does not check whether the judged object itself was chosen correctly",
)


def boundary_of(needle, strip_space=False):
    if strip_space and " " in needle:
        return needle.replace(" ", "")
    return None


def verify_needle(text, needle, boundary=None, require=None):
    present = needle in text
    b_present = (boundary in text) if boundary else None
    has_core = (require in needle) if require else None
    return {
        "needle": needle,
        "text_len": len(text),
        "needle_in_text": "\u5728" if present else "\u4e0d\u5728",
        "require": require,
        "require_in_needle": (None if require is None else ("\u5728" if has_core else "\u4e0d\u5728")),
        "boundary": boundary,
        "boundary_in_text": (None if boundary is None else ("\u5728" if b_present else "\u4e0d\u5728")),
        "ok": bool(present) and (b_present is not True) and (has_core is not False),
    }


def assert_needle(text, needle, boundary=None, require=None):
    r = verify_needle(text, needle, boundary, require)
    line = "needle=%r text_len=%d needle_in_text=%s" % (r["needle"], r["text_len"], r["needle_in_text"])
    if r["require"] is not None:
        line += " | require=%r require_in_needle=%s" % (r["require"], r["require_in_needle"])
    if r["boundary"] is not None:
        line += " | boundary=%r boundary_in_text=%s" % (r["boundary"], r["boundary_in_text"])
    print("  " + line, flush=True)
    if not r["ok"]:
        if r["needle_in_text"] == "\u4e0d\u5728":
            why = "needle is NOT in the judged object -- the criterion can never hold"
        elif r["require_in_needle"] == "\u4e0d\u5728":
            why = "needle lacks the declared core token -- too loose, matches for sure, discriminates nothing"
        else:
            why = "the boundary variant is ALSO present -- the needle was written loose"
        raise AssertionError("NEEDLE: FAIL -- %s; %s" % (why, line))
    return r


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--key", default="block_text")
    ap.add_argument("--needle", required=True)
    ap.add_argument("--boundary-strip-space", action="store_true")
    ap.add_argument("--require", default=None, help="core token the needle must contain (anti-loose)")
    a = ap.parse_args(argv)
    with open(a.json, encoding="utf-8") as f:
        obj = json.load(f)
    text = obj[a.key]
    b = boundary_of(a.needle, a.boundary_strip_space)
    ok = True
    try:
        assert_needle(text, a.needle, b, a.require)
    except AssertionError as e:
        print("  " + str(e), flush=True)
        print("NEEDLE-PROVENANCE: FAIL", flush=True)
        ok = False
    if ok:
        print("NEEDLE-PROVENANCE: PASS -- needle present, boundary variant absent", flush=True)
    for u in UNCOVERED:
        print(u, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
