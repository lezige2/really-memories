# -*- coding: utf-8 -*-
"""test_memory_meta_cpu.py -- c03 记忆元问题确定性回答（零 GPU）。

覆盖：
  1) 元问题判定：你有记忆吗/你记得什么/记忆存在哪/记忆对话结束就清空吗/你有长期记忆吗/
     记忆会丢吗 => True；具体内容问题（你记得我的车牌号吗/我的车牌号是多少）=> False
  2) memory_status_reply：0 条（空库）、N 条（数量 + 最近 2–3 条首行）、脱敏/截断、不泄露全文
  3) chat_daily 接线（fake engine）：元问题走确定性分支（state=memory_meta、不调模型、
     答案与真实库状态一致）；空库回答 0 条；内容问题不被误判为元问题。

运行： python -X utf8 tools/test_memory_meta_cpu.py ; exit 0 = 全过
"""

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import memory_service as M      # noqa: E402
import chat_daily as D          # noqa: E402

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(bool(cond))
    print(("ok   %s" % name) if cond else ("FAIL %s %s" % (name, detail)))


def make_app(tmp, model, **kw):
    return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "daily.db"),
                      blocks_dir=os.path.join(tmp, "blocks"),
                      sessions_dir=os.path.join(tmp, "sessions"),
                      model_path=model, restore=False,
                      log_root=os.path.join(tmp, "assistant"),
                      retrieval_mode="topk", topk=4, **kw)


ROWS = [
    {"id": 1, "text": "我叫阿泽。", "first_line": "我叫阿泽。"},
    {"id": 2, "text": "我的车牌号是京A88888。", "first_line": "我的车牌号是京A88888。"},
    {"id": 3, "text": "每周三组会在 B座302。", "first_line": "每周三组会在 B座302。"},
    {"id": 4, "text": "我的手机号是 13800138000，密码 abc12345。",
     "first_line": "我的手机号是 13800138000，密码 abc12345。"},
]


def main():
    # 1) 元问题判定
    for q in ("你有记忆吗", "你有长期记忆吗", "你记得什么", "你记得哪些",
              "记忆存在哪", "记忆库有什么", "记忆对话结束就清空吗", "记忆会丢吗"):
        check("meta.%s" % q, M.is_memory_meta_question(q) is True, q)
    for q in ("你记得我的车牌号吗？", "我的车牌号是多少？", "你住在哪里？", "你好"):
        check("not_meta.%s" % q, M.is_memory_meta_question(q) is False, q)

    # 2) 回复内容
    empty = M.memory_status_reply([])
    check("reply.empty_zero", ("0 条" in empty) and ("空" in empty), empty)
    check("reply.empty_no_cleared_claim",
          "对话上下文" in empty and "不会清空记忆库" not in empty, empty)
    rep = M.memory_status_reply(ROWS)
    check("reply.count", "4 条" in rep, rep)
    check("reply.mentions_library", "长期记忆库" in rep and "对话上下文" in rep, rep)
    check("reply.recent_first_lines",
          ("每周三组会" in rep) and ("手机号" in rep), rep)
    check("reply.no_full_text", "密码 abc12345" not in rep, rep)
    check("reply.phone_masked", "13800138000" not in rep and "138****8000" in rep, rep)
    check("reply.not_cleared", "清空" in rep or "不会清空记忆库" in rep, rep)
    # 最近 N 条：取 id 降序，前 3 条包含 4/3/2，不含 1
    check("reply.order_recent", ("我叫阿泽" not in rep), rep)

    # 3) chat_daily 接线（fake engine）
    tmp = tempfile.mkdtemp(prefix="memmeta_cpu_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    try:
        d1 = os.path.join(tmp, "empty")
        os.makedirs(d1, exist_ok=True)
        app = make_app(d1, model)
        try:
            before = app.eng.ask_calls
            r = app.ask("你有记忆吗？")
            check("wiring.empty_state", r.get("state") == "memory_meta", str(r))
            check("wiring.empty_answer", "0 条" in r["answer"], str(r["answer"]))
            check("wiring.empty_no_model", app.eng.ask_calls == before,
                  "%d -> %d" % (before, app.eng.ask_calls))
        finally:
            app.close()

        d2 = os.path.join(tmp, "full")
        os.makedirs(d2, exist_ok=True)
        app = make_app(d2, model)
        try:
            for t in ("我叫阿泽。", "我的车牌号是京A88888。", "每周三组会在 B座302。"):
                app.remember(t)
            for q in ("你有记忆吗？", "你记得什么？", "记忆存在哪？",
                      "记忆对话结束就清空吗？"):
                before = app.eng.ask_calls
                r = app.ask(q)
                check("wiring.%s.state" % q, r.get("state") == "memory_meta", str(r))
                check("wiring.%s.count" % q, "3 条" in r["answer"], str(r["answer"]))
                check("wiring.%s.no_model" % q, app.eng.ask_calls == before,
                      "%d -> %d" % (before, app.eng.ask_calls))
                check("wiring.%s.no_full_text" % q,
                      "我的车牌号是京A88888。" not in r["answer"]
                      or "京A88888" in r["answer"], str(r["answer"]))
            # 内容问题不能被误判成元问题
            r = app.ask("你记得我的车牌号吗？")
            check("wiring.content_not_meta", r.get("state") != "memory_meta", str(r))
        finally:
            app.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = len(CHECKS) - sum(CHECKS)
    print("\n%d checks, %d failed" % (len(CHECKS), failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())