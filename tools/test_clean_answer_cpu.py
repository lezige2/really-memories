# -*- coding: utf-8 -*-
"""clean_answer 代码块/多段回答回归测试（CPU、无模型、无网络）。

运行：python -X utf8 tools/test_clean_answer_cpu.py
"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def load_chat_daily():
    spec = importlib.util.spec_from_file_location(
        "chat_daily_t", os.path.join(ROOT, "tools", "chat_daily.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CleanAnswerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_chat_daily()

    def test_code_block_preserved(self):
        raw = ("快速排序的 Python 代码如下：\n\n```python\ndef quicksort(a):\n"
               "    if len(a) <= 1:\n        return a\n    return a\n```")
        out = self.mod.clean_answer(raw)
        self.assertIn("def quicksort", out)
        self.assertTrue(out.startswith("快速排序"))

    def test_code_block_with_question_mark_preserved(self):
        raw = "示例：\n\n```python\n# a > b? 是的话交换\nif a > b: a, b = b, a\n```"
        out = self.mod.clean_answer(raw)
        self.assertIn("if a > b", out)

    def test_plain_answer_first_paragraph(self):
        out = self.mod.clean_answer("你好。\n\n第二段不应保留")
        self.assertIn("你好", out)
        self.assertNotIn("第二段", out)

    def test_template_echo_removed(self):
        out = self.mod.clean_answer("好的。\n答：继续编")
        self.assertNotIn("继续编", out)

    def test_code_block_template_echo_removed(self):
        raw = ("代码如下：\n\n```python\ndef f(a):\n    return a\n```\n答：后面继续编")
        out = self.mod.clean_answer(raw)
        self.assertIn("def f(a)", out)
        self.assertNotIn("后续继续编", out)

    def test_long_code_not_cut_mid_def(self):
        body = "\n".join("x%d = %d" % (i, i) for i in range(400))
        raw = "示例：\n\n```python\ndef long_func():\n" + body + "\n```"
        out = self.mod.clean_answer(raw)
        self.assertIn("def long_func", out)
        self.assertLessEqual(out.count("```"), 2)

    def test_question_echo_removed(self):
        out = self.mod.clean_answer("我不知道。\n你叫什么名字？")
        self.assertNotIn("你叫什么名字", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)