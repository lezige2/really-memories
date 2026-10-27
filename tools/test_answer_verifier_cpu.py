# -*- coding: utf-8 -*-
"""test_answer_verifier_cpu.py -- T1「值抽取 + 匹配」单测（task-18；纯 CPU）。

范围：只测 tools/answer_verifier.py 的 extract_values(text) / match_values(values, blocks)
（verdict/hint/strip 由 task-19 负责，不在本文件断言）。
运行： python -X utf8 tools/test_answer_verifier_cpu.py ; exit 0 = 全过
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import answer_verifier as A      # noqa: E402

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(bool(cond))
    print(("ok   %s" % name) if cond else ("FAIL %s %s" % (name, detail)))


def main():
    # ---- 数字 ----
    v = A.extract_values("一共花了 120 元，课程 24 节。")
    check("num_arabic", "120" in v and "24" in v, str(v))
    v = A.extract_values("一共 1,200 元，折扣 3.5 折。")
    check("num_thousands_decimal", "1,200" in v and "3.5" in v, str(v))
    # ---- 中文数字 ----
    v = A.extract_values("买了三本书，交了两百元。")
    check("num_chinese_unit", any("三" in x for x in v) and any("两百元" in x or "百元" in x
                                                                for x in v), str(v))
    # ---- 英文数字 ----
    v = A.extract_values("I have twenty apples and one hundred books.")
    check("num_english_words", "20" in v and "100" in v, str(v))
    # ---- 日期 / 星期 / 时间 ----
    v = A.extract_values("3 月 5 日开会，周三上午 9 点开始。")
    check("date_md", any("3 月 5" in x or "3月5" in x or "3 月" in x for x in v), str(v))
    check("weekday", any("周三" in x for x in v), str(v))
    check("time_point", any("9 点" in x or "9点" in x for x in v), str(v))
    v = A.extract_values("下周一去，可能拖到 2026-10-27。")
    check("date_next_week", any("下周一" in x for x in v), str(v))
    check("date_iso", any("2026-10-27" in x for x in v), str(v))
    # ---- 地点 / 房间号 ----
    v = A.extract_values("从北京飞到上海，再去杭州和西安。")
    for c in ("北京", "上海", "杭州", "西安"):
        check("city_%s" % c, c in v, str(v))
    v = A.extract_values("在 B座302 开会，晚上 7 点。")
    check("room_code", "B座302" in v, str(v))
    v = A.extract_values("改到 3 号教室，或 A 教 201。")
    check("classroom", any("教室" in x or "教" in x for x in v), str(v))
    # ---- 实体：车牌 / 引号人名 ----
    v = A.extract_values("我的车牌号是京A88888，找“老王”处理。")
    check("plate", "京A88888" in v, str(v))
    check("quoted_person", "老王" in v, str(v))
    # ---- 「是/为/在/去/住/叫」后的名词短语 ----
    v = A.extract_values("我住在广陵路 12 号，去云栖书店买书。")
    check("after_verb_place", any("广陵路" in x for x in v), str(v))
    check("after_verb_entity", any("云栖书店" in x for x in v), str(v))
    # ---- 归一化 / 去重：全角数字、空格、被更长值包含的短值 ----
    v = A.extract_values("时间是７点，地点Ｂ座３０２。")
    check("normalize_fullwidth", any("7" in x for x in v) and
          any("302" in x or "B座302" in x for x in v), str(v))
    v = A.extract_values("B座302 的 302 房间。")
    check("dedupe_contained", "302" not in v or "B座302" in v, str(v))
    check("extract_empty", A.extract_values("   ") == [], "")
    # ---- 匹配：任一 block 出现即 supported；block_id 正确 ----
    blocks = [{"id": 1, "text": "每周三组会在 B座302，下午 3 点。"},
              {"id": 2, "text": "下周三去上海开会，坐高铁。"}]
    vals = A.extract_values("每周三下午 3 点在 B座302 开会。")
    matched = A.match_values(vals, blocks)
    check("match_supported", all(m["supported"] for m in matched), str(matched))
    check("match_block_id", {m["block_id"] for m in matched} == {1}, str(matched))
    vals = A.extract_values("下周三去上海开会。")
    matched = A.match_values(vals, blocks)
    check("match_second_block", all(m["supported"] and m["block_id"] == 2
                                    for m in matched), str(matched))
    vals = A.extract_values("下周三去北京开会。")
    matched = A.match_values(vals, blocks)
    bad = [m for m in matched if not m["supported"]]
    check("match_unsupported_city", any(m["value"] == "北京" for m in bad), str(matched))
    check("match_fields", matched and all(set(("value", "supported", "block_id"))
                                          <= set(m) for m in matched), str(matched[:1]))
    # 匹配归一化：block 带空格/全角数字
    vals = A.extract_values("2026-10-27 开会。")
    matched = A.match_values(vals, [{"id": 9, "text": "日期：２０２６－１０－２７"}])
    check("match_normalized", matched and matched[0]["supported"], str(matched))
    # 空值/空块
    check("match_empty_values", A.match_values([], blocks) == [], "")
    check("match_empty_blocks", all(not m["supported"] for m in
                                    A.match_values(["北京"], [])), "")

    failed = len(CHECKS) - sum(CHECKS)
    print("\n%d checks, %d failed" % (len(CHECKS), failed))
    return 0 if failed == 0 else 1


# ==========================================================================
# T2（task-19）：verdict 判定 / hint / strip_continuation —— 追加检查
# ==========================================================================
def t2_checks():
    before = len(CHECKS)
    B = [{"id": 1, "text": "停车在 B2 层 37 号，费用 58 元。"}]

    # ---- 诚实拒答 => pass ----
    r = A.verify("q", "我不知道。", [], "personal")
    check("t2_honest_unknown_pass", r["verdict"] == "pass", str(r))
    r = A.verify("q", "没有相关记录。", [], "personal")
    check("t2_honest_no_record_pass", r["verdict"] == "pass", str(r))
    r = A.verify("q", "没有。", [], "personal")
    check("t2_honest_short_no_pass", r["verdict"] == "pass", str(r))
    r = A.verify("q", "未提及", [], "personal")
    check("t2_honest_not_mentioned_pass", r["verdict"] == "pass", str(r))

    # ---- 诚实拒答但夹带具体值：不得直判 pass ----
    r = A.verify("q", "我不知道，不过大概是 58 元。", [], "personal")
    check("t2_honest_with_value_not_pass", r["verdict"] != "pass", str(r))
    # ---- 否定句里的 "没有" 不是拒答 ----
    r = A.verify("q", "我的车没有停在 B2层37号。", [], "personal")
    check("t2_negation_not_honest", r["verdict"] == "no_evidence", str(r))

    # ---- personal + blocks 空 + 具体值 => no_evidence ----
    r = A.verify("q", "B2层37号", [], "personal")
    check("t2_no_evidence_personal", r["verdict"] == "no_evidence", str(r))
    check("t2_no_evidence_mismatches", len(r["mismatches"]) >= 1,
          str(r["mismatches"][:3]))
    check("t2_no_evidence_hint_len", 0 < len(r["hint"]) <= 200, str(len(r["hint"])))
    check("t2_no_evidence_hint_wording",
          ("没有可用" in r["hint"] or "记忆" in r["hint"]) and "不知道" in r["hint"],
          r["hint"])

    # ---- personal + blocks 空 + 无具体值 => pass ----
    r = A.verify("q", "这个我不清楚。", [], "personal")
    check("t2_personal_empty_no_value_pass", r["verdict"] == "pass", str(r))

    # ---- personal + 有 blocks：支持 => pass；不支持 => unsupported ----
    r = A.verify("q", "停车在 B2 层 37 号", B, "personal")
    check("t2_supported_pass", r["verdict"] == "pass", str(r))
    r = A.verify("q", "停车在 B2 层 99 号", B, "personal")
    check("t2_unsupported", r["verdict"] == "unsupported", str(r))
    check("t2_unsupported_mismatch_type",
          all(m.get("type") == "value_not_in_memory" for m in r["mismatches"]),
          str(r["mismatches"][:2]))
    check("t2_unsupported_hint_len", 0 < len(r["hint"]) <= 200, str(len(r["hint"])))
    check("t2_unsupported_hint_instr",
          ("重答" in r["hint"]) and ("不知道" in r["hint"]), r["hint"])

    # ---- general 无 blocks + 具体值 => no_evidence（fuzz 加固；无值才 pass）----
    r = A.verify("q", "58 元", [], "general")
    check("t2_general_no_blocks_value_no_evidence",
          r["verdict"] == "no_evidence", str(r))
    r = A.verify("q", "这个我不清楚。", [], "general")
    check("t2_general_no_blocks_no_value_pass", r["verdict"] == "pass", str(r))

    # ---- hint 超长时截断但仍保留重答指令 + <=200 ----
    many = "、".join("%d号" % i for i in range(20))
    r = A.verify("q", "值：" + many, [{"id": 1, "text": "无关记忆"}], "personal")
    check("t2_hint_truncated_len", len(r["hint"]) <= 200, str(len(r["hint"])))
    check("t2_hint_keeps_instruction",
          "重答" in r["hint"] and "不知道" in r["hint"], r["hint"])

    # ---- strip_continuation ----
    check("t2_strip_user_tail",
          A.strip_continuation("58 元。用户：明天呢？") == "58 元",
          A.strip_continuation("58 元。用户：明天呢？"))
    check("t2_strip_answer_tail",
          A.strip_continuation("58 元。答：明天九点。") == "58 元",
          A.strip_continuation("58 元。答：明天九点。"))
    check("t2_strip_assistant_tail",
          A.strip_continuation("58 元。Assistant: 9 am.") == "58 元",
          A.strip_continuation("58 元。Assistant: 9 am."))
    check("t2_strip_response_tag",
          A.strip_continuation("58 元。</response>") == "58 元",
          A.strip_continuation("58 元。</response>"))
    check("t2_strip_bare_response",
          A.strip_continuation("58 元。 response") == "58 元",
          A.strip_continuation("58 元。 response"))
    check("t2_strip_escaped_tag",
          A.strip_continuation("58 元。&lt;/response&gt;") == "58 元",
          A.strip_continuation("58 元。&lt;/response&gt;"))
    check("t2_strip_repeat_sentence",
          A.strip_continuation("B2层37号。B2层37号。") == "B2层37号。",
          A.strip_continuation("B2层37号。B2层37号。"))
    check("t2_strip_preserves_normal",
          A.strip_continuation("答案是 58 元，用户满意度不错。") == "答案是 58 元，用户满意度不错。",
          A.strip_continuation("答案是 58 元，用户满意度不错。"))
    check("t2_strip_keeps_leading_answer_prefix",
          A.strip_continuation("答：58 元") == "答：58 元",
          A.strip_continuation("答：58 元"))
    check("t2_strip_keeps_ellipsis",
          A.strip_continuation("大概……58 元") == "大概……58 元",
          A.strip_continuation("大概……58 元"))

    # ---- 重复句归一化（task-30/F6 回归）：去空白/标点/全半角后比较 ----
    check("t2_strip_dup_think_space",
          A.strip_continuation("3楼开会。</redacted_thinking> 3楼开会。") == "3楼开会。",
          A.strip_continuation("3楼开会。</redacted_thinking> 3楼开会。"))
    check("t2_strip_dup_punct_diff",
          A.strip_continuation("重要：周三开会。重要：周三开会") == "重要：周三开会。",
          A.strip_continuation("重要：周三开会。重要：周三开会"))
    check("t2_strip_dup_fullwidth",
          A.strip_continuation("Ｂ座３０２开会。B座302开会。") == "Ｂ座３０２开会。",
          A.strip_continuation("Ｂ座３０２开会。B座302开会。"))
    check("t2_strip_dup_no_punct",
          A.strip_continuation("3楼开会 3楼开会") == "3楼开会",
          A.strip_continuation("3楼开会 3楼开会"))
    check("t2_strip_short_emphasis_kept",
          A.strip_continuation("好。好。") == "好。好。",
          A.strip_continuation("好。好。"))

    # ================= T12 fuzz 加固针对性用例 =================
    def _v(ans, blocks, mode="personal"):
        return A.verify("q", ans, blocks, mode)

    # 1) 数值子串误判必须 unsupported（数值相等，不是包含）
    check("t12_substr_1200_vs_11200",
          _v("价格 1200 元", [{"id": 1, "text": "价格 11200 元"}])["verdict"]
          == "unsupported", "")
    check("t12_substr_302_vs_1302",
          _v("302 室", [{"id": 1, "text": "1302 室"}])["verdict"] == "unsupported", "")
    check("t12_substr_15_vs_2015",
          _v("15 号", [{"id": 1, "text": "2015 号"}])["verdict"] == "unsupported", "")
    check("t12_exact_number_pass",
          _v("价格 1200 元", [{"id": 1, "text": "价格 1200 元"}])["verdict"] == "pass", "")
    # 2) 中文数字/单位抽取
    check("t12_cn_two_hours",
          _v("两小时后到", [{"id": 1, "text": "明天到"}])["verdict"] == "unsupported", "")
    check("t12_cn_km",
          _v("大概五公里", [{"id": 1, "text": "3 公里"}])["verdict"] == "unsupported", "")
    check("t12_cn_meter_eight",
          _v("一米八", [{"id": 1, "text": "175cm"}])["verdict"] == "unsupported", "")
    check("t12_cn_next_year_month",
          _v("明年三月", [{"id": 1, "text": "今年九月"}])["verdict"] == "unsupported", "")
    check("t12_cn_money",
          _v("三百块", [{"id": 1, "text": "200 元"}])["verdict"] == "unsupported", "")
    # 3) ID/邮箱/订单号/型号
    check("t12_id_a456",
          _v("工号是 A456", [{"id": 1, "text": "工号是 A123"}])["verdict"]
          == "unsupported", "")
    check("t12_email",
          _v("邮箱 c@d.com", [{"id": 1, "text": "邮箱 a@b.com"}])["verdict"]
          == "unsupported", "")
    check("t12_order_no",
          _v("订单号 SF999999", [{"id": 1, "text": "订单号 SF888888"}])["verdict"]
          == "unsupported", "")
    check("t12_model_iphone",
          _v("型号 iPhone 15", [{"id": 1, "text": "型号 iPhone 13"}])["verdict"]
          == "unsupported", "")
    # 4) 同义格式不得误报
    check("t12_weekday_format",
          _v("星期六", [{"id": 1, "text": "每周六开会"}])["verdict"] == "pass", "")
    check("t12_time_format",
          _v("15:00", [{"id": 1, "text": "下午3点开会"}])["verdict"] == "pass", "")
    check("t12_floor_format",
          _v("三楼", [{"id": 1, "text": "3 楼"}])["verdict"] == "pass", "")
    check("t12_age_format",
          _v("三十四岁", [{"id": 1, "text": "34 岁"}])["verdict"] == "pass", "")
    check("t12_date_format",
          _v("2026/10/27", [{"id": 1, "text": "2026-10-27"}])["verdict"] == "pass", "")
    # 5) _AFTER 连接词不得被当值
    check("t12_connective_not_value",
          _v("以第一条为准：1200 元", [{"id": 1, "text": "价格 1200 元"}])["verdict"]
          == "pass", "")
    # 6) 诚实拒答夹带具体主张仍需核对
    check("t12_honest_embedded_claim",
          _v("记忆里没有，不过你叫张三",
             [{"id": 1, "text": "用户叫李四"}])["verdict"] == "unsupported", "")
    # 7) 合法数值/车牌/中文单位 matched
    check("t12_room_numeric_supported",
          _v("302 室", [{"id": 1, "text": "B座302 室"}])["verdict"] == "pass", "")
    check("t12_plate_mismatch",
          _v("京B12345", [{"id": 1, "text": "京A88888"}])["verdict"] == "unsupported", "")
    check("t12_plate_supported",
          _v("京A88888", [{"id": 1, "text": "车牌 京A88888"}])["verdict"] == "pass", "")

    failed = len(CHECKS) - before - sum(CHECKS[before:])
    print("  [T2] %d checks, %d failed" % (len(CHECKS) - before, failed))
    return failed


if __name__ == "__main__":
    _rc_main = main()
    _rc_t2 = t2_checks()
    print("\nTOTAL %d checks, %d failed" % (len(CHECKS), len(CHECKS) - sum(CHECKS)))
    sys.exit(0 if (_rc_main == 0 and _rc_t2 == 0) else 1)