#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CPU-only unit tests for tools/exact_key.py (K2a 硬键精确检索，零 GPU/零服务).

Run: python -X utf8 -m unittest discover -s tools -p "test_exact_key_cpu.py" -v
Exit: 0 all pass, 1 failure.
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import exact_key as EK  # noqa: E402


def row(sid, name, text):
    """memory_source.block_rows() 形状：(id, name, label, text, hash, source_id, ...)."""
    return (int(sid), str(name), str(name), str(text), "h", 1, "/tmp/block", 8)


ROWS = [
    row(1, "mem-plate", "我的车牌是京A12345，停在B座。"),
    row(2, "mem-phone", "手机号 13812345678，工作用。"),
    row(3, "mem-email", "邮箱 zhang.san@example.com。"),
    row(4, "mem-card", "银行卡 6222 0000 1234，尾号1234。"),
    row(5, "mem-emp", "工号：A1234。"),
    row(6, "mem-pet", "猫叫豆豆，两岁。"),
    row(7, "mem-desk", "工位在B座302。"),
]


class ExtractTests(unittest.TestCase):
    def test_plate_lowercase_normalized(self):
        keys = EK.extract_keys("我的车牌是京a12345")
        self.assertEqual(keys["plate"], "京A12345")

    def test_plate_ignores_separators(self):
        keys = EK.extract_keys("车牌 京A·12345 停哪")
        self.assertEqual(keys["plate"], "京A12345")

    def test_phone_dashes(self):
        self.assertEqual(EK.extract_keys("手机 138-1234-5678")["phone"], "13812345678")

    def test_phone_spaces(self):
        self.assertEqual(EK.extract_keys("手机 138 1234 5678")["phone"], "13812345678")

    def test_email_lowercased(self):
        self.assertEqual(EK.extract_keys("邮箱 Zhang.San@Example.COM")["email"],
                         "zhang.san@example.com")

    def test_bank_tail_needs_keyword(self):
        self.assertEqual(EK.extract_keys("卡号尾号是1234")["bank_tail"], "1234")
        self.assertIsNone(EK.extract_keys("订单 1234")["bank_tail"])

    def test_emp_id_needs_keyword(self):
        self.assertEqual(EK.extract_keys("工号是 a1234")["emp_id"], "A1234")
        self.assertIsNone(EK.extract_keys("A1234")["emp_id"])

    def test_entity_aliases(self):
        self.assertIn("宠物", EK.extract_keys("我家宠物叫什么")["entity"])
        self.assertIn("工位", EK.extract_keys("我的座位在哪")["entity"])
        self.assertIn("会议", EK.extract_keys("几点开会")["entity"])
        self.assertEqual(EK.extract_keys("今天天气怎么样")["entity"], [])

    def test_nothing_extracted(self):
        keys = EK.extract_keys("我叫什么名字")
        self.assertTrue(all(keys[k] is None for k in
                            ("plate", "phone", "email", "bank_tail", "emp_id")))
        self.assertEqual(keys["entity"], [])


class SelectTests(unittest.TestCase):
    def test_plate_case_and_separator_hit(self):
        sel = EK.select_exact([row(1, "mem-plate", "车牌 京A·12345。")], "京a12345是哪辆", 4)
        self.assertIsNotNone(sel)
        self.assertEqual([s["name"] for s in sel], ["mem-plate"])
        self.assertEqual(sel[0]["source_id"], 1)

    def test_phone_with_separators_hit(self):
        sel = EK.select_exact([row(2, "mem-phone", "手机 13812345678。")],
                              "我的手机号 138-1234-5678 是多少", 4)
        self.assertEqual([s["name"] for s in sel], ["mem-phone"])

    def test_email_hit(self):
        sel = EK.select_exact([row(3, "mem-email", "邮箱 zhang.san@example.com。")],
                              "我的邮箱 Zhang.San@Example.com 是啥", 4)
        self.assertEqual([s["name"] for s in sel], ["mem-email"])

    def test_bank_tail_hit(self):
        sel = EK.select_exact([row(4, "mem-card", "银行卡 6222 0000 1234。")],
                              "我银行卡尾号是多少", 4)
        self.assertEqual([s["name"] for s in sel], ["mem-card"])

    def test_emp_id_hit_case_insensitive(self):
        sel = EK.select_exact([row(5, "mem-emp", "工号：A1234。")], "工号 a1234 是谁", 4)
        self.assertEqual([s["name"] for s in sel], ["mem-emp"])

    def test_entity_alias_hit(self):
        sel = EK.select_exact([row(6, "mem-pet", "猫叫豆豆。")], "我家宠物叫什么", 4)
        self.assertEqual([s["name"] for s in sel], ["mem-pet"])

    def test_reverse_protection_work_vs_private(self):
        # 问"工作号"、行里只有"私人号"：不得入选，整体回退
        rows = [row(2, "mem-phone", "私人号 13812345678。")]
        self.assertIsNone(EK.select_exact(rows, "我工作手机号 13812345678 是多少", 4))

    def test_predicate_positive(self):
        rows = [row(2, "mem-phone", "工作手机 13812345678。")]
        sel = EK.select_exact(rows, "我工作手机号 13812345678 是多少", 4)
        self.assertEqual([s["name"] for s in sel], ["mem-phone"])

    def test_miss_returns_none(self):
        self.assertIsNone(EK.select_exact(ROWS, "我的手机号 13900001111 是多少", 4))

    def test_no_key_returns_none(self):
        self.assertIsNone(EK.select_exact(ROWS, "我叫什么名字", 4))

    def test_keeps_input_order_not_newest(self):
        # B 修订：只按键召回，不选"最新"。输入顺序即输出顺序（这里故意让旧 id 在前）。
        rows = [row(2, "mem-old", "手机 13812345678。"),
                row(99, "mem-new", "手机 13812345678 备用。")]
        sel = EK.select_exact(rows, "手机 13812345678 是谁的", 4)
        self.assertEqual([s["name"] for s in sel], ["mem-old", "mem-new"])

    def test_topk_cap(self):
        rows = [row(i, "mem-%d" % i, "邮箱 a@b.com 记录%d" % i) for i in range(1, 7)]
        self.assertEqual(len(EK.select_exact(rows, "邮箱 a@b.com", 3)), 3)

    def test_signal_shape(self):
        sel = EK.select_exact(ROWS, "车牌 京A12345", 4)
        self.assertEqual(len(sel), 1)
        hit = sel[0]
        self.assertEqual(set(hit), {"name", "score", "source_id", "signals"})
        self.assertEqual(hit["score"], 9.0)
        self.assertIsInstance(hit["source_id"], int)
        self.assertTrue(hit["signals"]["exact"])
        self.assertIn("plate:京A12345", hit["signals"]["hits"])

    def test_empty_inputs(self):
        self.assertIsNone(EK.select_exact([], "京A12345", 4))
        self.assertIsNone(EK.select_exact(ROWS, "", 4))


if __name__ == "__main__":
    unittest.main()