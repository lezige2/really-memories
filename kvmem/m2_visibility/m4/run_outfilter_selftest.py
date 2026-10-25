# -*- coding: utf-8 -*-
# M4-A self-proof (discipline 33): the "no control tag in the answer" assertion must be able
# to go RED. An assertion that can only pass is equivalent to having no assertion.
#
# S1 tagged text, filter ON        -> clean, per-tag counts
# S2 same text, filter OFF         -> assert_clean MUST raise ControlTagLeft
# S3 chatml tokens, filter ON      -> clean, named counts, no generic double count
# S4 trailing </response>-class    -> clean
# S5 unknown angle token           -> REPORTED, never silently removed
# S6 idempotent second pass        -> removes nothing
# S7 block text with a tag         -> guard REFUSES to filter it
# S8 the real captured M4 answer   -> filtered then asserted
#
#   python -X utf8 m4/run_outfilter_selftest.py
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import outfilter as F

OUT = os.path.join(HERE, "run_m4_outfilter_selftest.json")
TAG = "</" + "think" + ">"
ANSWER = "我住在广陵路 12 号 2 单元 602。"
TAGGED = ANSWER + chr(10) + TAG + chr(10) + chr(10) + ANSWER


def main():
    # no pid and no timestamps: this artifact is meant to be an anchor, and a field that changes
    # on every run would make its sha meaningless
    res = {"schema": "m4_outfilter_selftest_v1",
           "aim": "prove the no-control-tag assertion can fail, that the filter is whitelist-only, and that block text is never filtered",
           "cases": []}
    ok = True

    def case(cid, what, verdict, **kw):
        nonlocal ok
        rec = {"case": cid, "what": what, "verdict": verdict}
        rec.update(kw)
        res["cases"].append(rec)
        if verdict == "fail":
            ok = False
        print("%-4s %-44s %s" % (cid, what, verdict))

    r = F.filter_text(TAGGED)
    # removing the tag leaves the surrounding newlines in place: this module removes ONLY the
    # tag (so removed_chars == len(tag)). Collapsing the blank run it leaves behind is
    # m4_display's separate job (BLANK_RUN), not this module's -- one concern per module.
    want = ANSWER + chr(10) * 3 + ANSWER
    case("S1", "think-tagged, filter ON", "pass" if (r["total"] == 1 and r["per_tag"] == {"think": 1} and r["text"] == want) else "fail",
         per_tag=r["per_tag"], before_len=r["before_len"], after_len=r["after_len"],
         removed_chars=r["removed_chars"], tag_len=len(TAG), clean=r["text"],
         only_tag_removed=(r["removed_chars"] == len(TAG)))

    try:
        F.assert_clean(F.filter_text(TAGGED, enabled=False)["text"], "S2 filter disabled")
        case("S2", "same text, filter OFF -> must RED", "fail",
             detail="assertion PASSED with the filter off, so it cannot discriminate")
    except F.ControlTagLeft as exc:
        case("S2", "same text, filter OFF -> must RED", "pass",
             raised=type(exc).__name__, raw_line=str(exc))

    r3 = F.filter_text("<|im_start|>你好</response>")
    case("S3", "chatml tokens, filter ON",
         "pass" if (r3["per_tag"] == {"response": 1, "im_start": 1} and r3["text"] == "你好") else "fail",
         per_tag=r3["per_tag"], clean=r3["text"])

    tag_r = "<" + "/" + "response" + ">"
    r4 = F.filter_text("车牌号是浙B-3F19K。" + tag_r)
    case("S4", "trailing response-class tag", "pass" if r4["text"] == "车牌号是浙B-3F19K。" else "fail",
         per_tag=r4["per_tag"], clean=r4["text"])

    r5 = F.filter_text("<tool_call>我住在广陵路。</tool_call>")
    case("S5", "unknown angle token: reported, not removed",
         "pass" if ("<tool_call>" in r5["text"] and r5["removed_chars"] == 0 and r5["unknown_angle_tokens"]) else "fail",
         clean=r5["text"], unknown_angle_tokens=r5["unknown_angle_tokens"],
         why="an unknown token is reported so a human decides; silently stripping template or attacker markup is how content vanishes without a trace")

    r6 = F.filter_text(r["text"])
    case("S6", "idempotent second pass", "pass" if r6["total"] == 0 else "fail", per_tag=r6["per_tag"])

    try:
        F.guard_not_block_text(TAGGED, "S7 block_text")
        case("S7", "block text with a tag must REFUSE", "fail",
             detail="guard accepted tagged block text, so it would have been rewritten")
    except F.BlockTextWouldChange as exc:
        case("S7", "block text with a tag must REFUSE", "pass",
             raised=type(exc).__name__, raw_line=str(exc))

    real = None
    src = None
    wpath = os.path.join(HERE, "run_m4_write.json")
    if os.path.exists(wpath):
        w = json.load(open(wpath, encoding="utf-8"))
        real = (w.get("lease_chain") or {}).get("answer_while_attached", {}).get("answer")
        src = "run_m4_write.json lease_chain.answer_while_attached.answer"
    if real:
        rr = F.filter_text(real)
        try:
            F.assert_clean(rr["text"], "S8 real answer after filtering")
            case("S8", "real captured answer, filtered then asserted", "pass",
                 per_tag=rr["per_tag"], before_len=rr["before_len"], after_len=rr["after_len"],
                 removed_chars=rr["removed_chars"], clean=rr["text"], source=src)
        except F.ControlTagLeft as exc:
            case("S8", "real captured answer, filtered then asserted", "fail",
                 raised=type(exc).__name__, raw_line=str(exc))
    else:
        case("S8", "real captured answer", "skip", detail="no captured answer found")

    res["assertion_is_load_bearing"] = any(c["case"] == "S2" and c["verdict"] == "pass" for c in res["cases"])
    res["verdict"] = "OUTFILTER-SELFTEST PASS" if ok else "OUTFILTER-SELFTEST FAIL"
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print()
    print("assertion_is_load_bearing:", res["assertion_is_load_bearing"])
    print(res["verdict"])
    print("sha16:", hashlib.sha256(open(OUT, "rb").read()).hexdigest()[:16])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())