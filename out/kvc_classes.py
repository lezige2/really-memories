# -*- coding: utf-8 -*-
"""Classify KVC-BASE-rN failures into 旧值/双列/拒答/其它.

Read-only over the eval output; writes out/KVC-BASE-rN-CLASSES.json.
Rules (in order), using only expect.not_contains / expect.contains_any and the
answer text (actual.answer), with actual.refused as a refusal hint:

  1. 双列 : answer contains BOTH a stale value (not_contains) and an expected value
  2. 旧值 : answer contains a stale value only
  3. 拒答 : not refused-expected -> answer is a refusal (actual.refused or refusal wording)
  4. 其它 : anything else (missing expected value, wrong value, empty answer, ...)
"""
import json
import re
import sys
from pathlib import Path

REFUSAL_PAT = re.compile(
    r"(不知道|不清楚|不记得|没有记|没记|没有(相关|任何)?(信息|记录|内容)|未(曾)?(提及|记录|提到)"
    r"|无法(回答|确定|得知|提供)|不能(回答|确定|提供)|无可奉告|抱歉|对不起|没有告诉我"
    r"|I (don't|do not) know|not (sure|aware)|no (information|record))"
)

# Soft/paraphrased refusal: recorded as an annotation only, never changes `class`,
# so 旧值/双列/拒答/其它 stay comparable with the frozen BASE runs.
REFUSAL_SOFT_PAT = re.compile(
    r"(没法(从|确认|核对|回答|确定)|不猜|核对不上|记不太清|记不清|没有印象|查不到)"
)


def norm(s):
    return (s or "").strip()


def classify(r):
    exp = r.get("expect") or {}
    act = r.get("actual") or {}
    ans = norm(act.get("answer"))
    stale = [v for v in (exp.get("not_contains") or []) if v and v in ans]
    good = [v for v in (exp.get("contains_any") or []) if v and v in ans]
    refused = bool(act.get("refused"))
    refuse_word = bool(REFUSAL_PAT.search(ans)) if ans else False
    refuse_soft = bool(REFUSAL_SOFT_PAT.search(ans)) if ans else False
    if stale and good:
        cls = "双列"
    elif stale:
        cls = "旧值"
    elif refused or refuse_word:
        cls = "拒答"
    else:
        cls = "其它"
    return {
        "id": r.get("id"),
        "class": cls,
        "answer": ans,
        "stale_hit": stale,
        "expected_hit": good,
        "refused_flag": refused,
        "refusal_wording": refuse_word,
        "refusal_soft": refuse_soft,
        "expect": exp,
        "failure_class_script": r.get("failure_class"),
        "problems": r.get("problems"),
        "infra_error": bool(r.get("infra_error")),
    }


def main():
    if len(sys.argv) < 3:
        print("usage: kvc_classes.py <out/KVC-BASE-rN.json> <out/KVC-BASE-rN-CLASSES.json>")
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    d = json.loads(src.read_text(encoding="utf-8"))
    rows = d.get("results") or []
    fails = [r for r in rows if r.get("pass") is False]
    items = [classify(r) for r in fails]
    counts = {}
    for it in items:
        counts[it["class"]] = counts.get(it["class"], 0) + 1
    out = {
        "schema": "kvc_base_classes_v1",
        "source": str(src).replace("\\", "/"),
        "n_results": len(rows),
        "n_pass": sum(1 for r in rows if r.get("pass") is True),
        "n_fail": len(fails),
        "n_infra": sum(1 for r in rows if r.get("infra_error")),
        "run_status": d.get("status"),
        "partial": d.get("partial"),
        "rule": ("1) not_contains命中且contains_any命中=双列 2) 仅not_contains命中=旧值 "
                 "3) refused或拒答措辞=拒答 4) 其余=其它"),
        "counts": counts,
        "counts_refusal_soft_annot": {
            "soft_ids": [it["id"] for it in items if it.get("refusal_soft")],
            "n_soft": sum(1 for it in items if it.get("refusal_soft")),
            "note": "换说法的拒答（如「这条我没法从记忆里核对，先不猜」）；仅标注，不并入拒答计数，保证与 BASE 各轮可比",
        },
        "fail_ids": [it["id"] for it in items],
        "by_class": {k: [it["id"] for it in items if it["class"] == k]
                     for k in ("旧值", "双列", "拒答", "其它")},
        "items": items,
        "summary": d.get("summary"),
        "hermetic": (d.get("hermetic") or {}).get("enabled") if d.get("hermetic") else None,
    }
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"out": str(dst), "n_fail": len(fails), "counts": counts,
                      "by_class": out["by_class"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())