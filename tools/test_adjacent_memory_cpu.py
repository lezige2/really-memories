# -*- coding: utf-8 -*-
"""test_adjacent_memory_cpu.py -- v7 回归：未知事实不得编造 + 陈述/remember 后立即追问。

覆盖：
  - 无记忆问生日/地址/妈妈生日 => no_evidence「没跟我说过」，不得出现具体值（即使模型编造）
  - 记忆里确有生日 => 正常 memory_hit
  - remember("我的银行卡尾号是6677") 后立即问尾号 => 挂载命中
  - 陈述"我下周三去上海开会"（自动记忆）后立即追问"我刚才说要去哪开会" => 挂载命中

Run: python -X utf8 tools/test_adjacent_memory_cpu.py ; exit 0 = pass.
"""
import os
import sys
import tempfile
import time

os.environ["LLAMA_MEM_MODE"] = "natural"
os.environ["LLAMA_MEM_VERIFY"] = "1"

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import chat_daily as D  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("ok   %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s %s" % (name, detail))


def make_app(tmp):
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    return D.DailyApp(
        D.StubEngine(),
        db_path=os.path.join(tmp, "daily.db"),
        blocks_dir=os.path.join(tmp, "blocks"),
        sessions_dir=os.path.join(tmp, "sessions"),
        model_path=model, restore=False, retrieval_mode="topk", topk=4, logger=False)


def main():
    tmp = tempfile.mkdtemp(prefix="adj_")
    app = make_app(tmp)
    try:
        # 1) 未知事实：模型即使编造，也必须被 no_evidence 截住
        app.eng.ask = lambda *a, **k: "你的生日是1990年5月15日，地址是北京市朝阳区某小区。"
        bad_values = ("1990", "5月15", "朝阳区", "某小区")
        for q in ("我生日是哪天", "我家地址是什么", "我妈妈的生日是哪天"):
            r = app._ask_natural(q, time.perf_counter())
            check("no_evidence_state_" + q, r.get("state") == "no_evidence",
                  "%s -> %s" % (q, r.get("state")))
            check("no_evidence_text_" + q, "没跟我说过" in r["answer"], r["answer"])
            check("no_fabrication_" + q,
                  not any(v in r["answer"] for v in bad_values), r["answer"])

        # 2) 记忆里确有生日 => 正常命中
        app.remember("我的生日是1月2日。")
        app.eng.ask = lambda *a, **k: "你的生日是1月2日。"
        r = app._ask_natural("我的生日是哪天", time.perf_counter())
        check("known_birthday_hit", bool(r.get("block_ids")) and "1月2日" in r["answer"],
              r["block_ids"])

        # 3) remember 尾部号码后立即追问（相邻轮）；模型即使拒答，也要从块里核对出 6677
        app.remember("我的银行卡尾号是6677。")
        app.eng.ask = lambda *a, **k: "你之前没有告诉我你的银行卡尾号，所以我不清楚。"
        r = app._ask_natural("我的银行卡尾号是多少？", time.perf_counter())
        check("card_after_remember_mount", bool(r.get("block_ids")), r["block_ids"])
        check("card_after_remember_answer_refusal_ignored",
              "6677" in r["answer"], r["answer"])
        check("card_after_remember_verified", r.get("verified") is True, r.get("verify"))

        # 4) 陈述句自动记忆后立即追问（f02）
        app.eng.ask = lambda *a, **k: "记住了。"
        app._ask_natural("我下周三去上海开会", time.perf_counter())
        app.eng.ask = lambda *a, **k: "你刚才说下周三去上海开会。"
        r = app._ask_natural("我刚才说要去哪开会？", time.perf_counter())
        check("followup_after_statement_mount", bool(r.get("block_ids")), r["block_ids"])
        check("followup_after_statement_answer", "上海" in r["answer"], r["answer"])

        # 5) x03：前导寒暄词不干扰检索
        app.remember("我每周三晚上七点有组会，地点在B座302。")
        app.eng.ask = lambda *a, **k: "你每周三晚上七点有组会，地点在B座302。"
        r = app._ask_natural("在吗，我几点开会？", time.perf_counter())
        check("greeting_prefix_retrieval", bool(r.get("block_ids")), r["block_ids"])
        check("greeting_prefix_answer", "302" in r["answer"] or "七点" in r["answer"],
              r["answer"])

        # 6) h01：动作请求确定性拒答；能力询问不误伤
        app.eng.ask = lambda *a, **k: "你可以自己操作一下。"
        r = app._ask_natural("帮我加个好友", time.perf_counter())
        check("action_request_refused",
              ("做不到" in r["answer"]) or r["answer"] == "这个我帮不了哦"
              or "不能操作" in r["answer"], r["answer"])
        r2 = app._ask_natural("你能做什么", time.perf_counter())
        check("capability_not_action_refusal",
              r2["answer"] != "这个我帮不了哦" and "本地记忆助手" in r2["answer"],
              r2["answer"])

        print("\n%s" % ("ALL PASS" if not FAILS else "FAILURES: %r" % (FAILS,)))
        return 0 if not FAILS else 1
    finally:
        app.close()


if __name__ == "__main__":
    sys.exit(main())