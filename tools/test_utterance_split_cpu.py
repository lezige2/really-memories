# -*- coding: utf-8 -*-
"""utterance_split：逐字保真、最多4块、问句/否定/控制/单块不拆。"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import utterance_split as U  # noqa: E402


class SplitTests(unittest.TestCase):
    def test_semantic_example(self):
        t = "我下周三去北京开会"
        r = U.split_utterance(t)
        self.assertTrue(r["ok"])
        self.assertEqual(r["parts"], ["我", "下周三", "去北京", "开会"])
        self.assertEqual("".join(r["parts"]), t)

    def test_name_example(self):
        t = "我女儿的小名是米朵"
        r = U.split_utterance(t)
        self.assertTrue(r["ok"])
        self.assertTrue(r["parts"][0].startswith("我女儿"))
        self.assertIn("米朵", "".join(r["parts"]))
        self.assertEqual("".join(r["parts"]), t)

    def test_two_sentences_fidelity(self):
        t = "我上周去了南京。南京天气不错。"
        r = U.split_utterance(t)
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(len(r["parts"]), 2)
        self.assertIn("上周", r["parts"])
        self.assertEqual("".join(r["parts"]), t)

    def test_max_six_parts(self):
        t = "我去了北京。我见了客户。我吃了烤鸭。我买了特产。我坐高铁回来。"
        r = U.split_utterance(t)
        self.assertLessEqual(len(r["parts"]), 6)
        self.assertEqual("".join(r["parts"]), t)

    def test_skip_negation(self):
        self.assertFalse(U.split_utterance("不是去北京而是去上海。")["ok"])

    def test_skip_question_and_control(self):
        self.assertFalse(U.split_utterance("我下周去哪？")["ok"])
        self.assertFalse(U.split_utterance("记住我下周去北京。")["ok"])

    def test_single_clause(self):
        r = U.split_utterance("豆豆很可爱")
        self.assertFalse(r["ok"])
        self.assertEqual(r["parts"], ["豆豆很可爱"])

    def test_poc_fidelity(self):
        import json
        root = os.path.dirname(_HERE)
        p = os.path.join(root, "out", "SPLIT-POC.json")
        if not os.path.exists(p):
            self.skipTest("no poc file")
        d = json.load(open(p, encoding="utf-8"))
        self.assertEqual(d["fidelity"], d["n"])
        self.assertLessEqual(max(d["parts"]), 4)


if __name__ == "__main__":
    unittest.main()
