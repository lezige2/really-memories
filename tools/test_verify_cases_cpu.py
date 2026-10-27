#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""T5: answer_verifier 行为用例（独立、纯 CPU、零 GPU/零网络）。

接口：`tools/answer_verifier.py::verify_answer(question, answer, blocks, mode)`。
断言只看对外可观察量：最终 verdict + 关键 mismatch（claim / expected_from_block）；
另覆盖 strip_continuation 的三类尾巴。不依赖实现内部细节。

运行：python -X utf8 tools/test_verify_cases_cpu.py [--verbose]
退出码：0 全过；1 有失败。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import answer_verifier as A  # noqa: E402


def blocks(*rows):
    out = []
    for i, t in enumerate(rows, 1):
        out.append({"id": i, "text": t})
    return out


CASES = []


def _cnorm(s):
    return "".join(str(s or "").replace(",", "").split())


def case(name, answer, blks, mode, expect_verdict, has_claims=(), not_has=(),
         expected_from_block=None, question="q"):
    CASES.append({
        "name": name, "answer": answer, "blocks": blks, "mode": mode,
        "question": question, "expect_verdict": expect_verdict,
        "has_claims": list(has_claims), "not_has": list(not_has),
        "expected_from_block": expected_from_block or {},
    })


# ---------------------------------------------------------------------------
# A. 正确值 -> pass
# ---------------------------------------------------------------------------
case("A1 plate exact pass", "沪A-12345。", blocks("我的车牌号是沪A-12345"),
     "personal", "pass")
case("A2 time+floor pass", "下午3点，在3楼。", blocks("我每周三下午3点在3楼开会"),
     "personal", "pass")
case("A3 room pass", "在B座302开会。", blocks("我下周三改去B座302"),
     "personal", "pass")
case("A4 city pass", "去上海开会。", blocks("我下周三去上海开会"),
     "personal", "pass")
case("A5 thousands pass", "工时费1,200元。", blocks("工时费1200元"),
     "personal", "pass")
case("A6 date pass", "2026-10-27 提交。", blocks("我在2026-10-27提交材料"),
     "personal", "pass")

# ---------------------------------------------------------------------------
# B. 错值 -> unsupported + 关键 claim/expected
# ---------------------------------------------------------------------------
case("B1 wrong city", "去上海出差。", blocks("我明天要去北京出差"),
     "personal", "unsupported", has_claims=["上海"],
     expected_from_block={"上海": "北京"})
case("B2 wrong time", "5点开会。", blocks("我每周三下午3点在3楼开会"),
     "personal", "unsupported", has_claims=["5点"])
case("B3 wrong number", "工时费420元。", blocks("工时费是320元"),
     "personal", "unsupported", has_claims=["420"],
     expected_from_block={"420": "320"})
case("B4 wrong plate", "京A88888。", blocks("我的车牌号是沪A-12345"),
     "personal", "unsupported", has_claims=["京A88888"])
case("B5 wrong room", "在B座302。", blocks("我下周改去A座101"),
     "personal", "unsupported", has_claims=["B座302"])
case("B6 wrong entity after 叫", "叫豆豆。", blocks("我养了一只猫叫咪咪"),
     "personal", "unsupported", has_claims=["豆豆"])
case("B7 wrong weekday", "下周四开会。", blocks("我下周三去上海开会"),
     "personal", "unsupported", has_claims=["下周四"])
case("B8 wrong date", "2026-11-01 提交。", blocks("我在2026-10-27提交材料"),
     "personal", "unsupported", has_claims=["2026-11-01"])
case("B9 wrong thousands", "工时费2,400元。", blocks("工时费1200元"),
     "personal", "unsupported", has_claims=["2400"])
case("B10 stale value vs newest-only block",
     "去上海开会。", blocks("我下周三改去B座302"),
     "personal", "unsupported", has_claims=["上海"])
case("B11 long answer two wrong values",
     "下周三去B座302开会，周五下午5点复诊。",
     blocks("我下周三去上海开会", "我周五下午3点复诊"),
     "personal", "unsupported", has_claims=["B座302", "5点"])
case("B12 wrong floor number", "在5楼开会。", blocks("我每周三在3楼开会"),
     "personal", "unsupported", has_claims=["5"])

# ---------------------------------------------------------------------------
# C. 无记忆 personal + 具体值 -> no_evidence
# ---------------------------------------------------------------------------
case("C1 fabricate number no memory", "工号是8848。", [], "personal",
     "no_evidence", has_claims=["8848"])
case("C2 fabricate plate no memory", "沪A-12345。", [], "personal",
     "no_evidence", has_claims=["12345"])
case("C3 fabricate city no memory", "去上海出差。", [], "personal",
     "no_evidence", has_claims=["上海"])

# ---------------------------------------------------------------------------
# D. 诚实拒答 -> pass
# ---------------------------------------------------------------------------
for i, ans in enumerate(("这个我不知道。", "记忆里没有这条。", "未提及具体时间。",
                         "我不确定。", "我不清楚。"), 1):
    case("D%d honest refusal pass" % i, ans, blocks("我养了一只猫叫豆豆"),
         "personal", "pass")
case("D6 digits beat honest-pass (checked)", "3点这个我没法核对，先不猜。",
     blocks("我养了一只猫叫豆豆"), "personal", "unsupported",
     has_claims=["3点"])

# ---------------------------------------------------------------------------
# E. general / 边界
# ---------------------------------------------------------------------------
case("E1 general no blocks pass", "中国的首都。", [], "general", "pass")
case("E2 personal empty answer pass", "", [], "personal", "pass")
case("E3 personal whitespace answer pass", "   ", [], "personal", "pass")
# task-29 #6 新口径：blocks 空 + 答案含具体值 ⇒ no_evidence（general 同样）
case("E4 general empty blocks with value -> no_evidence", "KV 缓存是缓存技术。", [],
     "general", "no_evidence")

# ---------------------------------------------------------------------------
# F. strip_continuation 三类尾巴
# ---------------------------------------------------------------------------
STRIP_CASES = []
STRIP_CASES.append(("F1 think tag tail",
                    "答案是上海。</redacted_thinking>",
                    lambda s: "</redacted_thinking>" not in s and "上海" in s))
STRIP_CASES.append(("F2 template continuation",
                    "答案是上海。 用户：再问一个 答：北京",
                    lambda s: "用户：" not in s and "北京" not in s
                    and "上海" in s))
STRIP_CASES.append(("F3 repeated tail sentence",
                    "记住：周三开会。记住：周三开会。",
                    lambda s: s.count("周三开会") == 1))
STRIP_CASES.append(("F4 think + template",
                    "去B座302。</redacted_thinking> 问：还有吗 答：没有",
                    lambda s: "</redacted_thinking>" not in s
                    and "问：" not in s and "B座302" in s))
STRIP_CASES.append(("F5 normal text unchanged",
                    "下周三去上海开会。",
                    lambda s: s.strip() == "下周三去上海开会。"))
STRIP_CASES.append(("F6 repeated + think combined",
                    "3楼开会。</redacted_thinking> 3楼开会。",
                    lambda s: "</redacted_thinking>" not in s
                    and s.count("3楼开会") == 1))


def run_strip_checks():
    checks = []
    for name, text, pred in STRIP_CASES:
        out = A.strip_continuation(text)
        checks.append((name, bool(pred(out)), out, ""))
    return checks


def run_verify_checks():
    checks = []
    for c in CASES:
        res = A.verify_answer(c["question"], c["answer"], c["blocks"],
                              c["mode"])
        verdict = res.get("verdict")
        claims = [str(m.get("claim")) for m in (res.get("mismatches") or [])]
        exp_map = res.get("mismatches") or []
        problems = []
        if verdict != c["expect_verdict"]:
            problems.append("verdict=%r != %r" % (verdict, c["expect_verdict"]))
        for need in c["has_claims"]:
            if not any(_cnorm(need) in _cnorm(cl) for cl in claims):
                problems.append("missing mismatch claim %r (claims=%r)"
                                % (need, claims))
        for exp_claim, exp_val in c["expected_from_block"].items():
            got = [m.get("expected_from_block") for m in exp_map
                   if exp_claim in str(m.get("claim"))]
            if not any(g and str(exp_val) in str(g) for g in got):
                problems.append("expected_from_block[%r]=%r not found (got=%r)"
                                % (exp_claim, exp_val, got))
        for forbidden in c["not_has"]:
            if any(_cnorm(forbidden) in _cnorm(cl) for cl in claims):
                problems.append("unexpected claim %r" % forbidden)
        checks.append((c["name"], not problems, res, "; ".join(problems)))
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    checks = run_verify_checks() + run_strip_checks()
    bad = [c for c in checks if not c[1]]
    print("verify_cases=%d strip_cases=%d checks=%d failed=%d"
          % (len(CASES), len(STRIP_CASES), len(checks), len(bad)))
    if a.verbose:
        for name, ok, res, why in checks:
            print(("PASS " if ok else "FAIL ") + name)
            if not ok:
                print("   why:", why)
                print("   res:", res)
    if bad:
        print("FAILED:")
        for name, _ok, res, why in bad:
            print(" - %s: %s" % (name, why))
            print("   actual:", res)
        return 1
    print("ALL PASS (CPU only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())