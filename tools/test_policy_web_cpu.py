# -*- coding: utf-8 -*-
"""test_policy_web_cpu.py -- 政策复读清洗 + 报时 + 联网失败/成功路径（零 GPU/零网络）。

覆盖：
  - strip_policy_echo：泄漏前缀/整段策略/重复"标标标"被清掉；正常答案不受影响
  - natural 路径：模型复读策略 => 回退「我记不清了」
  - 报时：本地直答，state=time_local，无「来源」
  - 明确查询但无可靠资料：state=web_fail，含"无法/不联网"，无「来源」
  - 查询命中：state=web，正常返回并标来源
  - 限行类查询触发检索且清洗掉"是多少"

Run: python -X utf8 tools/test_policy_web_cpu.py ; exit 0 = pass.
"""
import os
import sys
import tempfile
import time

os.environ["LLAMA_MEM_MODE"] = "natural"
os.environ["LLAMA_MEM_VERIFY"] = "0"

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import chat_daily as D  # noqa: E402
import web_lookup as W  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("ok   %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s %s" % (name, detail))


LEAK = ("检索资料；说话自然、简短、口语化，像朋友聊天。用户告诉你事实时系统会在后台记住。"
        "标标标标标标标标标标标标标标标标标")


def t_strip_policy():
    check("policy_only_empty", D.strip_policy_echo(LEAK) == "", repr(D.strip_policy_echo(LEAK)))
    mixed = "检索资料；说话自然、简短、口语化。你的车牌号是京A88888。"
    out = D.strip_policy_echo(mixed)
    check("policy_prefix_removed", "京A88888" in out and "说话自然" not in out, out)
    normal = "你的组会在 B 座 302 开。"
    check("normal_answer_kept", D.strip_policy_echo(normal) == normal, D.strip_policy_echo(normal))
    check("policy_think_marker",
          D.strip_policy_echo("不要输出思考过程。回答是 42。") == "回答是 42。",
          D.strip_policy_echo("不要输出思考过程。回答是 42。"))


def make_app(tmp):
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    return D.DailyApp(
        D.StubEngine(),
        db_path=os.path.join(tmp, "daily.db"),
        blocks_dir=os.path.join(tmp, "blocks"),
        sessions_dir=os.path.join(tmp, "sessions"),
        model_path=model, restore=False, retrieval_mode="topk", topk=4, logger=False)


def t_policy_fallback_in_chat():
    tmp = tempfile.mkdtemp(prefix="pw_")
    app = make_app(tmp)
    try:
        app.eng.ask = lambda seq, text, n_predict=32, pos=None: LEAK
        res = app._ask_natural("今天天气怎么样？", time.perf_counter())
        check("policy_echo_fallback_answer", res["answer"] == "我记不清了", res["answer"])
        check("policy_echo_no_leak", "说话自然" not in res["answer"], res["answer"])
    finally:
        app.close()


def t_policy_empty_action_fallback():
    """拒绝语境 + 答案被政策清洗删空 => 必须「这个我帮不了哦」，不能「我记不清了」。"""
    tmp = tempfile.mkdtemp(prefix="pw_act_")
    app = make_app(tmp)
    try:
        app.eng.ask = lambda seq, text, n_predict=32, pos=None: LEAK
        res = app._ask_natural("你能帮我个忙吗", time.perf_counter())
        check("policy_empty_action_refusal", res["answer"] == "这个我帮不了哦",
              res["answer"])
        check("policy_empty_action_not_remember", res["answer"] != "我记不清了",
              res["answer"])
        # 普通问题仍回「我记不清了」
        res2 = app._ask_natural("今天天气怎么样", time.perf_counter())
        check("policy_empty_general_remember", res2["answer"] == "我记不清了",
              res2["answer"])
    finally:
        app.close()


def t_identity_fixes():
    """v6 身份类回归：合法身份句保留；身份问句不拿用户名答；能力询问不走动作拒答。"""
    ident = "我是你的本地记忆助手，说话自然、简短、口语化。"
    out = D.strip_policy_echo(ident)
    check("identity_sentence_kept", "本地记忆助手" in out, out)
    check("identity_instruction_removed", "说话自然" not in out, out)
    check("identity_pure_instruction_empty",
          D.strip_policy_echo("说话自然；检索资料；用户告诉你事实时系统会在后台记住。") == "",
          "policy-only should be empty")

    tmp = tempfile.mkdtemp(prefix="pw_id_")
    app = make_app(tmp)
    try:
        app.remember("我叫阿泽。")
        app.eng.ask = lambda *a, **k: "我叫阿泽。"
        for q in ("你是谁", "你是谁呀", "你叫什么", "你叫什么名字", "你叫啥",
                  "你是什么模型", "你是AI吗", "你是机器人吗"):
            r = app._ask_natural(q, time.perf_counter())
            ok = ("本地记忆助手" in r["answer"]) and ("阿泽" not in r["answer"])
            check("identity_q_" + q, ok and r.get("state") == "identity",
                  "%s -> %s/%s" % (q, r.get("state"), r.get("answer")))
        app.eng.ask = lambda *a, **k: ("不能操作任何应用（加好友/发消息/转账），"
                                       "说话自然、简短、口语化。")
        r = app._ask_natural("你能做什么", time.perf_counter())
        check("capability_not_action_refusal",
              r["answer"] != "这个我帮不了哦" and "本地记忆助手" in r["answer"],
              r["answer"])
    finally:
        app.close()


def t_local_time():
    tmp = tempfile.mkdtemp(prefix="pw_time_")
    app = make_app(tmp)
    try:
        app.eng.ask = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("local time must not call the model"))
        res = app._ask_natural("现在几点了", time.perf_counter())
        check("time_state", res.get("state") == "time_local", res.get("state"))
        check("time_answer_has_clock", "现在" in res["answer"] and ":" in res["answer"],
              res["answer"])
        check("time_no_source", "来源" not in res["answer"], res["answer"])
    finally:
        app.close()


def t_web_paths():
    tmp = tempfile.mkdtemp(prefix="pw_web_")
    app = make_app(tmp)
    calls = []
    try:
        # 1) 无可靠资料 -> web_fail
        orig = W.lookup_text
        W.lookup_text = lambda q, **kw: ""
        app.eng.ask = lambda *a, **k: "不应该被调用"
        res = app._ask_natural("帮我查一下明天的新闻", time.perf_counter())
        check("web_fail_state", res.get("state") == "web_fail", res.get("state"))
        check("web_fail_no_source", "来源" not in res["answer"], res["answer"])
        check("web_fail_refusal_words",
              any(w in res["answer"] for w in ("无法", "不联网", "不知道", "不能")),
              res["answer"])

        # 2) 限行查询触发检索且清洗 query（"是多少"不进入 query）
        def _lookup(q, **kw):
            calls.append((q, kw))
            return ""
        W.lookup_text = _lookup
        res = app._ask_natural("明天北京限行尾号是多少", time.perf_counter())
        check("limit_query_triggered", bool(calls), calls)
        if calls:
            q = calls[0][0]
            check("limit_query_cleaned", "限行" in q and "是多少" not in q, q)
        check("limit_query_state_web_fail", res.get("state") == "web_fail", res.get("state"))

        # 3) 有资料 -> web 正常返回并标来源
        W.lookup_text = lambda q, **kw: "1) 明日新闻 — 国内要闻（https://example.com）"
        app.eng.ask = lambda seq, text, n_predict=32, pos=None: "明天国内要闻如下。"
        res = app._ask_natural("帮我查一下明天的新闻", time.perf_counter())
        check("web_ok_state", res.get("state") == "web", res.get("state"))
        check("web_ok_source", "来源" in res["answer"], res["answer"])
    finally:
        W.lookup_text = orig
        app.close()


def main():
    t_strip_policy()
    t_policy_fallback_in_chat()
    t_policy_empty_action_fallback()
    t_identity_fixes()
    t_local_time()
    t_web_paths()
    print("\n%s" % ("ALL PASS" if not FAILS else "FAILURES: %r" % (FAILS,)))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())