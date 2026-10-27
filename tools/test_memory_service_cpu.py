# -*- coding: utf-8 -*-
"""test_memory_service_cpu.py -- 记忆数据层单测（零 GPU、零网络）。

覆盖：token/检索门槛/topk/标签加权、规则抽取、plan_upsert 去重与冲突
（supersedes）、静默记忆判据、拒答判据、联网判据、内省字段。
运行： python -X utf8 tools/test_memory_service_cpu.py ; exit 0 = 全过
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import memory_service as M      # noqa: E402

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(bool(cond))
    print(("ok   %s" % name) if cond else ("FAIL %s %s" % (name, detail)))


def rows():
    return [
        {"id": 1, "text": "我的车牌号是京A88888，车型比亚迪汉。", "tags": ["车辆"]},
        {"id": 2, "text": "在云栖书店买了旧书《城南旧事》，花了 120 元。", "tags": ["购书"]},
        {"id": 3, "text": "每周三晚上 7 点组会，地点 2 号会议室。", "tags": ["会议"]},
        {"id": 4, "text": "咖啡不加糖，只喝美式。", "tags": ["偏好"]},
        {"id": 5, "text": "周三上午体检，需要空腹。", "tags": ["健康"]},
    ]


def main():
    # ---- token ----
    t = M.tokens("车牌号京A88888 组会")
    check("tokens_cjk_bigram", "车牌" in t and "组会" in t, str(sorted(t)))
    check("tokens_latin_word", "a88888" in t or any("a88888" in x for x in t),
          str(sorted(t)))

    # ---- 检索 ----
    hit = M.retrieve("我的车牌号是多少？", rows(), topk=4)
    check("retrieve_hit", bool(hit) and hit[0]["id"] == 1, str(hit))
    check("retrieve_fields", all(k in hit[0] for k in
                                 ("id", "score", "coverage", "text")), str(hit[0]))
    check("retrieve_score_positive", hit[0]["score"] >= 2.0, str(hit[0]))
    # 门槛：只命中一个泛词 => 低于阈值（无 top1 覆盖/分数）
    low = M.retrieve("这个那个", rows(), topk=4)
    check("retrieve_gate_reject", low == [], str(low))
    # 短查询例外：2 token、1 命中、覆盖 0.5 => 通过
    short = M.retrieve("美式", rows(), topk=4)
    check("retrieve_short_query_exception", bool(short) and short[0]["id"] == 4,
          str(short))
    # topk 截断 + 并列按 id 升序
    many = [{"id": i, "text": "项目 X1 内容 %d。" % i, "tags": []} for i in range(1, 7)]
    cut = M.retrieve("项目 X1", many, topk=4)
    check("retrieve_topk", [x["id"] for x in cut] == [1, 2, 3, 4],
          str([x["id"] for x in cut]))
    # 标签加权：正文不含「车辆」，但标签命中可选中
    tagged = M.retrieve("车辆 车牌", rows(), topk=4)
    check("retrieve_tag_weight", bool(tagged) and tagged[0]["id"] == 1,
          str(tagged))

    # ---- 抽取 ----
    f1 = M.extract_facts("我的车牌号是京A88888")
    check("extract_plate", any(f["subject"] == "车牌号" and f["value"] == "京A88888"
                               for f in f1), str(f1))
    f2 = M.extract_facts("买书花了 120 元，5 月 20 日下单。")
    check("extract_amount", any(f["kind"] == "amount" and "120" in f["value"] for f in f2),
          str(f2))
    check("extract_time", any(f["kind"] == "time" and "5 月 20" in str(f["value"])
                              for f in f2), str(f2))
    f3 = M.extract_facts("我偏好咖啡不加糖")
    check("extract_preference", any(f["kind"] == "preference" for f in f3), str(f3))
    f4 = M.extract_facts("我明天要去出差")
    check("extract_fallback_unverified",
          bool(f4) and all(f.get("status") == "未核实" for f in f4), str(f4))
    check("extract_empty", M.extract_facts("   ") == [], "")

    # ---- upsert ----
    facts = [{"kind": "identifier", "subject": "车牌号", "predicate": "是",
              "value": "京A88888"}]
    plan_new = M.plan_upsert(facts, [{"id": 9, "text": "无关记忆。"}])
    check("upsert_insert", plan_new["summary"]["insert"] == 1
          and plan_new["actions"][0]["action"] == "insert", str(plan_new))
    plan_noop = M.plan_upsert(facts, [{"id": 7, "text": "我的车牌号是京A88888"}])
    check("upsert_noop", plan_noop["summary"]["noop"] == 1
          and plan_noop["actions"][0]["action"] == "noop"
          and plan_noop["actions"][0]["memory_id"] == 7, str(plan_noop))
    plan_upd = M.plan_upsert(facts, [{"id": 7, "text": "我的车牌号是京B12345"}])
    a = plan_upd["actions"][0]
    check("upsert_update_supersedes", a["action"] == "update"
          and a["supersedes"] == 7 and a["old_value"] == "京B12345"
          and a["new_value"] == "京A88888", str(plan_upd))
    check("upsert_key", M.fact_key(facts[0]) == ("车牌号", "是", "identifier"),
          str(M.fact_key(facts[0])))

    # ---- 行为判据 ----
    check("needs_auto_true", M.needs_auto_remember("我住在广陵路 12 号。") is True, "")
    check("needs_auto_false_question",
          M.needs_auto_remember("我的车牌号是多少？") is False, "")
    check("needs_auto_false_command", M.needs_auto_remember("/remember 我住在 A") is False, "")
    check("fact_question_true", M.is_fact_question("我的车牌号是多少？") is True, "")
    check("fact_question_false_world",
          M.is_fact_question("介绍一下长城的历史") is False, "")
    check("needs_lookup_weather", M.needs_lookup("今天北京天气怎么样？") is True, "")
    check("needs_lookup_memory", M.needs_lookup("我的车牌号是多少？") is False, "")

    # ---- 内省 ----
    ins = M.introspect(rows(), meta_fn=lambda sid: {"tags": ["t"], "source": "manual",
                                                    "related_ids": []})
    check("introspect_fields", ins and all(
        k in ins[0] for k in ("id", "first_line", "len", "source", "tags",
                              "related_ids", "created_at")), str(ins[:1]))
    check("introspect_sorted", [x["id"] for x in ins] == sorted(x["id"] for x in ins), "")

    failed = len(CHECKS) - sum(CHECKS)
    print("\n%d checks, %d failed" % (len(CHECKS), failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())