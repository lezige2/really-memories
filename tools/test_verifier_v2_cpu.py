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