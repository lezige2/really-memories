r"""Answer-form classifier for mask/iso run artifacts.

FROZEN criterion (lead ruling (c), 2026-02): the pre-registered rule is NOT changed
after seeing results. Anything the rule cannot express is reported as a SEPARATE
dimension, never by bending the rule.

form:
    empty : answer length == 0
    quiz  : answer contains a run of >= 3 "_"   OR   one of "A." / "B." / "A、" / "B、"
    plain : otherwise
    (no normalization: a literal backslash-underscore pair is NOT an underscore)

cloze_marker (independent boolean, reported next to form, never merged into it):
    True iff any of
        >= 3 groups of "\_"
        a run of >= 3 "_"
        the text contains "填空"

Both counts are always printed, because a verdict without its counts cannot be audited:
    max_underscore : longest run of "_" in the raw text
    escaped_us     : number of literal backslash-underscore groups
"""
import json
import re
import sys

US = chr(92) + "_"                              # literal backslash + underscore
QUIZ_MARKERS = ("A.", "B.", "A\u3001", "B\u3001")   # A、 / B、
CLOZE_WORD = "\u586b\u7a7a"                       # 填空


def metrics(answer):
    return {
        "len": len(answer),
        "max_underscore": max((len(u) for u in re.findall(r"_+", answer)), default=0),
        "escaped_us": answer.count(US),
    }


def classify(answer):
    """Frozen three-way rule. Deliberately blind to escaped blanks."""
    m = metrics(answer)
    if m["len"] == 0:
        return "empty"
    if m["max_underscore"] >= 3 or any(k in answer for k in QUIZ_MARKERS):
        return "quiz"
    return "plain"


def cloze_marker(answer):
    m = metrics(answer)
    return bool(m["escaped_us"] >= 3 or m["max_underscore"] >= 3 or CLOZE_WORD in answer)


def records(path):
    """Yield (label, ok, answer, expected) from either artifact shape."""
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    if isinstance(d.get("answers"), list):
        for i, a in enumerate(d["answers"]):
            yield ("answers[%d] %s" % (i, a.get("segment")), a.get("ok"),
                   a.get("answer") or "", a.get("expected"))
    elif isinstance(d.get("ask"), dict):
        a = d["ask"]
        yield ("ask", a.get("ok"), a.get("answer") or "", a.get("expected"))


def main(argv):
    if not argv:
        print("usage: python -X utf8 _form.py <a.json> [b.json ...]")
        return 2
    print("%-34s %-5s %-6s %-7s %-7s %-6s %-4s %s"
          % ("file", "ok", "form", "cloze", "maxUnd", "escUS", "len", "expected"))
    for path in argv:
        for label, ok, answer, expected in records(path):
            m = metrics(answer)
            print("%-34s %-5s %-6s %-7s %-7d %-6d %-4d %s"
                  % (label[:34], str(ok), classify(answer),
                     "Y" if cloze_marker(answer) else "n",
                     m["max_underscore"], m["escaped_us"], m["len"], repr(expected)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
