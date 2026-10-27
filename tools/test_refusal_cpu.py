# -*- coding: utf-8 -*-
"""CPU-only: 服务端拒答/寒暄修复的回归断言（DOC-AUDIT D13）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence as E

HIST = "我是阿泽，今天做了b7实验，结论是擦边"
CHECKS = []


def check(name, cond):
    CHECKS.append((name, bool(cond)))


def main():
    # 1) 旧 bug：单字（u:天 等）导致"没记忆也当作文中已提"
    check("bogus_history_not_in_chat", E.dialogue_evidence("我明天要去哪里出差？", HIST) is False)
    # 2) 真正的对话内追问仍可命中
    check("real_followup_in_chat", E.dialogue_evidence("实验结论是什么？", HIST) is True)
    # 3) 与历史无关的新事实问题不应被当作 in-chat
    check("unrelated_fact_not_in_chat", E.dialogue_evidence("我明天要去哪里出差？", HIST) is False)
    # 4) 寒暄/能力类应走确定性回复（不调模型）
    import chat_daily as D
    app = object.__new__(D.DailyApp)
    for q in ("你好", "您好", "谢谢", "再见", "你是谁", "你能做什么", "帮助"):
        r = D.DailyApp._smalltalk_reply(app, q)
        check("smalltalk:" + q, isinstance(r, str) and len(r) > 0)
    # 4b) 重复/带语气问候（"你好你好"/"你好呀"/"在吗在吗"）
    for q in ("你好你好", "你好呀", "在吗在吗", "您好！", "早上好"):
        r = D.DailyApp._smalltalk_reply(app, q)
        check("smalltalk_repeat:" + q, isinstance(r, str) and len(r) > 0)
    # 4c) 身份/称赞类（"你是谁呀？"曾误判拒答）
    for q in ("你是谁呀？", "你是谁啊", "你叫啥", "你神了", "厉害"):
        r = D.DailyApp._smalltalk_reply(app, q)
        check("smalltalk_identity:" + q, isinstance(r, str) and len(r) > 0)
    # 4d) 能力/记忆库/联网/感叹类 -> 确定性回答（不调模型）
    app._rows = lambda: []
    for q in ("你的记忆力现在有什么", "你记得什么", "你能联网吗",
              "你的知识截止到什么时候", "我靠", "我服了", "你想认识我吗"):
        r = D.DailyApp._capability_reply(app, q)
        check("capability:" + q, isinstance(r, str) and len(r) > 0)
    check("capability_not_memory_question",
          D.DailyApp._capability_reply(app, "我的车牌号是多少？") is None)
    # 5) 非寒暄问题不得被 smalltalk 吞掉
    for q in ("我的车牌号是多少？", "我明天要去哪里出差？", "帮我记住这件事"):
        r = D.DailyApp._smalltalk_reply(app, q)
        check("not_smalltalk:" + q, r is None)
    bad = [n for n, ok in CHECKS if not ok]
    print("checks=%d failed=%d" % (len(CHECKS), len(bad)))
    if bad:
        print("FAILED:", bad)
        return 1
    print("ALL PASS (CPU only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
