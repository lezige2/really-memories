# -*- coding: utf-8 -*-
"""CPU-only tests for answer_verifier v2（VERIFIER_VERSION=v2，默认 v1 不变）.

Run: python -X utf8 -m unittest discover -s tools -p "test_verifier_v2_cpu.py" -v
"""
import os
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import answer_verifier as av  # noqa: E402


def blocks(*texts):
    return [{"id": i, "text": t} for i, t in enumerate(texts, start=1)]


def run(q, a, bl):
    with mock.patch.dict(os.environ, {"VERIFIER_VERSION": "v2"}):
        return av.verify(q, a, bl, mode="personal")


def run21(q, a, bl):
    with mock.patch.dict(os.environ, {"VERIFIER_VERSION": "v2.1"}):
        return av.verify(q, a, bl, mode="personal")


def run22(q, a, bl):
    with mock.patch.dict(os.environ, {"VERIFIER_VERSION": "v2.2"}):
        return av.verify(q, a, bl, mode="personal")


class V22Tests(unittest.TestCase):
    """v2.2：claim=subject+predicate+value；碎片不触发；否定/冲突必须 fail。"""

    KEPT = blocks("我的公司是顺丰")
    Q11 = "我在哪家公司上班？"

    def test_v9mt11_fragments_pass(self):
        for ans in ("你在顺丰公司工作", "顺丰公司上班", "过你的公司是顺丰",
                    "一次", "什么名字", "我的公司是顺丰"):
            for _ in range(5):
                v = run22(self.Q11, ans, self.KEPT)
                self.assertEqual(v["verdict"], "pass", (ans, v))
                self.assertEqual(v["version"], "v2.2")
        # 一家公司 = 泛称碎片，不得触发
        self.assertEqual(run22(self.Q11, "你在一家公司上班", self.KEPT)["verdict"],
                         "pass")

    def test_negation_must_fail(self):
        for ans in ("我的公司不是顺丰", "我已经不在顺丰了", "这家公司不再是顺丰"):
            v = run22(self.Q11, ans, self.KEPT)
            self.assertEqual(v["verdict"], "unsupported", (ans, v))

    def test_conflict_must_fail(self):
        v = run22(self.Q11, "我的公司是中石油", self.KEPT)
        self.assertEqual(v["verdict"], "unsupported")
        self.assertEqual(v["mismatches"][0]["type"], "wrong_slot_value")

    def test_negated_conflict_then_correct_passes(self):
        self.assertEqual(run22(self.Q11, "不是中石油，是顺丰", self.KEPT)["verdict"],
                         "pass")

    def test_guards_l09_v9mt05(self):
        v = run22("我的银行卡尾号是多少？", "你的银行卡尾号是88888",
                  blocks("我的银行卡尾号是7418"))
        self.assertEqual(v["verdict"], "unsupported")
        self.assertEqual(v["mismatches"][0]["type"], "wrong_slot_value")
        self.assertEqual(run22("我的手机号是多少？", "你的手机号是15800002468",
                               blocks("我的手机号是158-0000-2468"))["verdict"], "pass")
        self.assertEqual(run22("我爱吃什么？", "你最爱吃粤菜",
                               blocks("我最爱吃湘菜"))["verdict"], "pass")

    def test_claim_requires_cue_and_value(self):
        # 只有值没有 predicate 线索 -> 碎片，不触发
        self.assertEqual(run22(self.Q11, "顺丰", self.KEPT)["verdict"], "pass")
        # 只有 predicate 没有值 -> 碎片，不触发
        self.assertEqual(run22(self.Q11, "你的公司是哪家", self.KEPT)["verdict"], "pass")


class V21Tests(unittest.TestCase):
    """S0：V9MT11/12 误触发修复（只改 verifier；默认仍 v1）。"""

    KEPT = blocks("我的公司是顺丰")
    Q11 = "我在哪家公司上班？"
    Q12 = "我的公司叫什么？"
    CLAIMS = ["你在顺丰公司工作", "顺丰公司上班", "你在一家公司上班",
              "你的公司是顺丰", "过你的公司是顺丰"]

    def test_v9mt11_12_claims_pass_5x(self):
        for q in (self.Q11, self.Q12):
            for claim in self.CLAIMS:
                for _ in range(5):
                    v = run21(q, claim, self.KEPT)
                    self.assertEqual(v["verdict"], "pass", (q, claim, v))
                    self.assertEqual(v["version"], "v2.1")

    def test_company_entity_normalization(self):
        self.assertEqual(av._v2_norm_entity("顺丰公司"), "顺丰")
        self.assertEqual(av._v2_norm_entity("顺丰（公司）"), "顺丰")
        self.assertTrue(av._v2_generic_entity("一家"))

    def test_v2_old_still_fails_on_generic_claim(self):
        # 改前（v2）对“一家公司”会误判 -> 说明 v2.1 是定点放宽
        v = run(self.Q11, "你在一家公司上班", self.KEPT)
        self.assertEqual(v["verdict"], "unsupported")

    def test_guards_unchanged(self):
        # L09 错值仍 fail
        v = run21("我的银行卡尾号是多少？", "你的银行卡尾号是88888",
                  blocks("我的银行卡尾号是7418"))
        self.assertEqual(v["verdict"], "unsupported")
        self.assertEqual(v["mismatches"][0]["type"], "wrong_slot_value")
        # L07 显式拒答仍 pass
        self.assertEqual(run21("我的邮箱是什么？", "你的邮箱我这里没有记录",
                               blocks("我的邮箱是 lin@example.org"))["verdict"], "pass")
        # V9MT05 单块手机 pass
        self.assertEqual(run21("我的手机号是多少？", "你的手机号是15800002468",
                               blocks("我的手机号是158-0000-2468"))["verdict"], "pass")
        # 无槽/无族仍 pass
        self.assertEqual(run21("我爱吃什么？", "你最爱吃粤菜",
                               blocks("我最爱吃湘菜"))["verdict"], "pass")


class VersionTests(unittest.TestCase):
    def test_default_is_v1(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(av.verifier_version(), "v1")

    def test_v1_path_unchanged(self):
        # v1 对"数字不在记忆里"给 unsupported，但 mismatch 类型仍是旧值
        with mock.patch.dict(os.environ, {"VERIFIER_VERSION": "v1"}):
            v = av.verify("我的银行卡尾号是多少？", "你的银行卡尾号是88888",
                          blocks("我的银行卡尾号是7418"), mode="personal")
        self.assertEqual(v["verdict"], "unsupported")
        self.assertNotEqual(v["mismatches"][0]["type"], "wrong_slot_value")


class NoSlotGuardTests(unittest.TestCase):
    """B 定护栏：family=None 或槽位不明确 -> pass，且不得触发 repair。"""

    def test_v9mt17_old_value_no_slot_passes(self):
        v = run("我最爱吃什么？", "你最爱吃湘菜，这个我记得很清楚",
                blocks("我最爱吃湘菜", "我最爱吃粤菜"))
        self.assertEqual(v["verdict"], "pass")
        self.assertEqual(v["checked_values"], 0)      # 未进入校验
        self.assertEqual(v["mismatches"], [])

    def test_v9mt18_old_value_no_slot_passes(self):
        v = run("我爱吃什么？", "你最爱吃湘菜，这个我记得很清楚",
                blocks("我最爱吃湘菜", "我最爱吃粤菜"))
        self.assertEqual(v["verdict"], "pass")
        self.assertEqual(v["checked_values"], 0)

    def test_meeting_without_slot_wrong_answer_passes(self):
        # 会议但无日期槽：即使答案错值也不判 fail（不许 repair）
        v = run("在吗，我几点开会？", "你下午三点开会",
                blocks("我每周三晚上七点有组会，地点在B座302。"))
        self.assertEqual(v["verdict"], "pass")
        self.assertEqual(v["checked_values"], 0)

    def test_slot_wrong_value_fails(self):
        v = run("我的银行卡尾号是多少？", "你的银行卡尾号是88888",
                blocks("我的银行卡尾号是7418"))
        self.assertEqual(v["verdict"], "unsupported")
        self.assertEqual(v["mismatches"][0]["type"], "wrong_slot_value")

    def test_slot_correct_value_passes(self):
        v = run("我的银行卡尾号是多少？", "你的银行卡尾号是7418",
                blocks("我的银行卡尾号是7418"))
        self.assertEqual(v["verdict"], "pass")


class L07L09Tests(unittest.TestCase):
    def test_l07_refusal_passes(self):
        v = run("我的邮箱是什么？", "你的邮箱我这里没有记录，可能记不清了",
                blocks("我的邮箱是 lin@example.org", "我的车牌号是京A88888"))
        self.assertEqual(v["verdict"], "pass")

    def test_l07_correct_passes(self):
        v = run("我的邮箱是什么？", "你的邮箱是 lin@example.org",
                blocks("我的邮箱是 lin@example.org"))
        self.assertEqual(v["verdict"], "pass")

    def test_l09_wrong_tail_fails(self):
        v = run("我的银行卡尾号是多少？", "你的银行卡尾号是88888",
                blocks("我的银行卡尾号是 7418", "我的车牌号是京A88888"))
        self.assertEqual(v["verdict"], "unsupported")
        self.assertEqual(v["mismatches"][0]["type"], "wrong_slot_value")

    def test_l09_correct_passes(self):
        v = run("我的银行卡尾号是多少？", "尾号是7418",
                blocks("我的银行卡尾号是 7418"))
        self.assertEqual(v["verdict"], "pass")

    def test_l09_missing_fails(self):
        v = run("我的银行卡尾号是多少？", "嗯，这个嘛，你先等等",
                blocks("我的银行卡尾号是 7418"))
        self.assertEqual(v["verdict"], "unsupported")
        self.assertEqual(v["mismatches"][0]["type"], "missing_slot_value")


class SlotTests(unittest.TestCase):
    def test_multi_value_skips(self):
        # V9MT05 式：两条手机号 -> 多值，不校验
        v = run("我的手机号是多少？", "你的手机号是13611113333",
                blocks("我的手机号是136-1111-3333", "我的手机号是158-0000-2468"))
        self.assertEqual(v["verdict"], "pass")

    def test_no_slot_skips(self):
        # V9MT18 式：吃/口味不在槽位表 -> 不校验
        v = run("我爱吃什么？", "你最爱吃粤菜", blocks("我最爱吃湘菜"))
        self.assertEqual(v["verdict"], "pass")

    def test_phone_separator_format_passes(self):
        v = run("我的手机号是多少？", "你的手机号是13611113333",
                blocks("我的手机号是136-1111-3333"))
        self.assertEqual(v["verdict"], "pass")

    def test_negation_counts_target_only(self):
        v = run("我的车牌号是多少？", "不是京A88888，是津E54321",
                blocks("我的车牌号是津E54321"))
        self.assertEqual(v["verdict"], "pass")

    def test_plate_wrong_value_fails(self):
        v = run("我的车牌号是多少？", "你的车牌号是沪F67890",
                blocks("我的车牌号是京A88888"))
        self.assertEqual(v["verdict"], "unsupported")

    def test_company_wrong_value_fails(self):
        v = run("我在哪家公司上班？", "你在字节跳动上班",
                blocks("我在云栖科技上班"))
        self.assertEqual(v["verdict"], "unsupported")

    def test_meeting_time_passes(self):
        v = run("我周三晚上几点有组会？", "晚上七点有组会",
                blocks("我每周三晚上七点有组会，地点在B座302。"))
        self.assertEqual(v["verdict"], "pass")

    def test_meeting_place_passes(self):
        v = run("周三的组会在哪开？", "在B座302",
                blocks("我每周三晚上七点有组会，地点在B座302。"))
        self.assertEqual(v["verdict"], "pass")

    def test_meeting_place_wrong_fails(self):
        v = run("周三的组会在哪开？", "在C座501",
                blocks("我每周三晚上七点有组会，地点在B座302。"))
        self.assertEqual(v["verdict"], "unsupported")

    def test_meeting_without_date_skips(self):
        # x03 式：无日期槽 -> 不校验
        v = run("在吗，我几点开会？", "这条我不太确定",
                blocks("我每周三晚上七点有组会，地点在B座302。"))
        self.assertEqual(v["verdict"], "pass")

    def test_fitness_time_passes(self):
        v = run("我几点去健身？", "晚上八点去健身",
                blocks("我每周四晚上八点健身"))
        self.assertEqual(v["verdict"], "pass")

    def test_allergy_leading_pronoun_passes(self):
        # L10 式："我对花生过敏" 的值是"花生"，不是"我对花生"
        v = run("我对什么过敏？", "你对花生过敏", blocks("我对花生过敏"))
        self.assertEqual(v["verdict"], "pass")

    def test_unclear_predicate_skips(self):
        v = run("我工号多少", "你的工号是A1234", blocks("我的工号是A1234"))
        self.assertEqual(v["verdict"], "pass")

    def test_multi_value_same_family_skips_wrong(self):
        v = run("我的车牌号是多少？", "你的车牌号是沪F67890",
                blocks("我的车牌号是京A88888", "我的车牌号是粤G09876"))
        self.assertEqual(v["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()