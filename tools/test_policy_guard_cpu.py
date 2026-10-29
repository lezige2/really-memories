# -*- coding: utf-8 -*-
"""防回归：SYSTEM_POLICY 必须保留"后台记住"承重句（P1 删除该句 → extra long_memory 5/10 的对照证据）。
运行：python -X utf8 tools/test_policy_guard_cpu.py
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


class PolicyGuardTest(unittest.TestCase):
    def test_memory_carry_sentence_present(self):
        import chat_daily
        pol = chat_daily.SYSTEM_POLICY
        self.assertIn("后台记住", pol)
        self.assertIn("优先依据记忆", pol)
        self.assertIn("不能操作任何应用", pol)
        self.assertIn("think", pol)

    def test_clean_answer_keeps_code(self):
        import chat_daily
        raw = "示例：\n\n```python\ndef f(a):\n    return a\n```"
        self.assertIn("def f(a)", chat_daily.clean_answer(raw))


if __name__ == "__main__":
    unittest.main(verbosity=2)
