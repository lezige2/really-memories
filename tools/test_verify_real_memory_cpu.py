# -*- coding: utf-8 -*-
"""test_verify_real_memory_cpu.py -- P0 verify 误拒回归（零 GPU，真 verifier）。

真记忆答案必须 pass；块外值 unsupported；诚实拒答 pass；无块含具体值 no_evidence；
并在 chat_daily 自然模式里验证：生成答案引用了挂载记忆 => verified=True。

Run: python -X utf8 tools/test_verify_real_memory_cpu.py ; exit 0 = pass.
"""
import os
import sys
import tempfile
import time

os.environ["LLAMA_MEM_MODE"] = "natural"
os.environ["LLAMA_MEM_VERIFY"] = "1"       # 用真 answer_verifier

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import answer_verifier as AV  # noqa: E402
import chat_daily as D  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("ok   %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s %s" % (name, detail))


BLOCKS = [
    {"id": 1, "text": "我叫阿泽，今天（2026-10-27）我们做完了 b7 实验；我的车牌号是京A88888。"},
    {"id": 2, "text": "我每周三晚上七点有组会，地点在B座302。"},
    {"id": 3, "text": "我下周三要去上海出差"},
    {"id": 4, "text": "我下周三要去北京出差"},
]


def t_verifier_matrix():
    cases = [
        ("我叫什么名字？", "你叫阿泽。", "pass"),
        ("我的组会在哪开？", "你的组会在 B 座 302。", "pass"),
        ("我的车牌号是多少？", "你的车牌号是京A88888。", "pass"),
        ("我下周三去哪出差？", "你下周三去上海出差。", "pass"),
        ("我下周三去哪出差？", "不知道，只记得你下周三去上海。", "pass"),
        ("我叫什么名字？", "你叫小明。", "unsupported"),
        ("我的组会在哪开？", "组会在 A 座 101。", "unsupported"),
        ("我下周三去哪出差？", "你下周四去杭州出差。", "unsupported"),
        ("我的车牌号是多少？", "不知道。", "pass"),          # 诚实拒答
    ]
    ok = True
    for q, a, exp in cases:
        v = AV.verify_answer(q, a, BLOCKS, mode="personal")
        got = v.get("verdict")
        if got != exp:
            ok = False
            check("verifier_case_%s" % exp, False, "%r -> %s (%r)" % (a, got, v))
    check("verifier_matrix_no_false_reject", ok, "")


def t_no_blocks_no_evidence():
    v = AV.verify_answer("我的车牌号是多少？", "京A88888", [], mode="personal")
    check("no_blocks_value_no_evidence", v.get("verdict") == "no_evidence", v)


def t_chat_natural_grounded():
    tmp = tempfile.mkdtemp(prefix="vfy_real_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    app = D.DailyApp(
        D.StubEngine(),
        db_path=os.path.join(tmp, "daily.db"),
        blocks_dir=os.path.join(tmp, "blocks"),
        sessions_dir=os.path.join(tmp, "sessions"),
        model_path=model, restore=False, retrieval_mode="topk", topk=4, logger=False)
    try:
        app.remember("我的车牌号是京A88888。")
        # 第一版答案引用记忆（应 pass，无需 repair）
        app.eng.ask = lambda seq, text, n_predict=32, pos=None: "你的车牌号是京A88888。"
        res = app._ask_natural("我的车牌号是多少？", time.perf_counter())
        check("natural_grounded_verified", res.get("verified") is True, res.get("verify"))
        check("natural_grounded_verdict",
              (res.get("verify") or {}).get("verdict") == "pass", res.get("verify"))
        check("natural_grounded_mounted", bool(res.get("block_ids")), res.get("block_ids"))

        # 第一版编造 -> 一次修复 -> 第二版 grounded => verified，且 attempts=1
        calls = iter(["你的车牌号是京A00000。", "你的车牌号是京A88888。"])
        app.eng.ask = lambda seq, text, n_predict=32, pos=None: next(calls)
        res2 = app._ask_natural("我的车牌号是多少？", time.perf_counter())
        check("natural_repair_verified", res2.get("verified") is True, res2.get("verify"))
        check("natural_repair_attempts", res2.get("verify_attempts") == 1,
              res2.get("verify_attempts"))
    finally:
        app.close()


def main():
    t_verifier_matrix()
    t_no_blocks_no_evidence()
    t_chat_natural_grounded()
    print("\n%s" % ("ALL PASS" if not FAILS else "FAILURES: %r" % (FAILS,)))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())