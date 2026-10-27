# -*- coding: utf-8 -*-
"""test_action_time_cpu.py -- v9 泛化回归：动作边界漏词 + 纯时间问句。

覆盖：
  - 动作请求（替我给老板发消息/给阿泽转50/回复微信/点个赞）=> 确定性「这个我帮不了哦」
  - 能力询问（你能做什么）不误伤
  - 纯时间问句（明天星期几/下周一几号/今天几号/后天周几）=> state=time_local，
    直接本地时间回答，不出现 verify_fallback / 没法核对

Run: python -X utf8 tools/test_action_time_cpu.py ; exit 0 = pass.
"""
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta

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


def main():
    tmp = tempfile.mkdtemp(prefix="act_time_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    app = D.DailyApp(
        D.StubEngine(),
        db_path=os.path.join(tmp, "daily.db"),
        blocks_dir=os.path.join(tmp, "blocks"),
        sessions_dir=os.path.join(tmp, "sessions"),
        model_path=model, restore=False, retrieval_mode="topk", topk=4, logger=False)
    try:
        # 动作请求：模型若答"你自己试试看"也必须被边界拒答截住
        app.eng.ask = lambda *a, **k: "你可以自己试试看。/ 好的，你想怎么回复呢"
        for q in ("你替我给老板发条消息", "帮我给阿泽转 50",
                  "帮我回复一下那条微信", "帮我点个赞", "帮我发条消息给老板"):
            r = app._ask_natural(q, time.perf_counter())
            check("action_" + q, r["answer"] == "这个我帮不了哦" and r["state"] == "boundary",
                  "%s -> %s/%s" % (q, r.get("state"), r["answer"]))

        # 能力询问不误伤
        r = app._ask_natural("你能做什么", time.perf_counter())
        check("capability_not_action",
              r["answer"] != "这个我帮不了哦" and "本地记忆助手" in r["answer"],
              r["answer"])

        # 纯时间问句：本地直答，不能 verify_fallback
        today = datetime.now().date()
        cases = {
            "明天是星期几": today + timedelta(days=1),
            "下周一几号": today - timedelta(days=today.weekday()) + timedelta(days=7),
            "今天几号": today,
            "后天是周几": today + timedelta(days=2),
        }
        for q, expect_d in cases.items():
            r = app._ask_natural(q, time.perf_counter())
            check("time_state_" + q, r.get("state") == "time_local", r.get("state"))
            check("time_not_verify_" + q, "没法核对" not in r["answer"], r["answer"])
            check("time_date_" + q,
                  ("%d 月 %d 日" % (expect_d.month, expect_d.day)) in r["answer"],
                  r["answer"])

        print("\n%s" % ("ALL PASS" if not FAILS else "FAILURES: %r" % (FAILS,)))
        return 0 if not FAILS else 1
    finally:
        app.close()


if __name__ == "__main__":
    sys.exit(main())