# -*- coding: utf-8 -*-
"""TASK-085 M-b 单测：history_pairs 分组排列兜底 + chatml 顺序（无服务，纯单元测试）。
用法：python -X utf8 out/test_history_pairs.py
"""
import importlib.util
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location("ev_ut", os.path.join(ROOT, "out", "SFT-PROXY-EVAL.py"))
EV = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EV)


class TestHistoryPairs(unittest.TestCase):
    def test_interleaved_4(self):
        h = []
        for i in range(1, 5):
            h += [{"role": "user", "content": "u%d" % i}, {"role": "assistant", "content": "a%d" % i}]
        p = EV.history_pairs(h)
        self.assertEqual(len(p), 4)
        self.assertEqual(p, [("u1", "a1"), ("u2", "a2"), ("u3", "a3"), ("u4", "a4")])

    def test_grouped_4(self):
        # 分组排列：4 user 在前、4 assistant 在后（M-b 兜底场景）
        h = [{"role": "user", "content": "u%d" % i} for i in range(1, 5)] + \
            [{"role": "assistant", "content": "a%d" % i} for i in range(1, 5)]
        p = EV.history_pairs(h)
        self.assertEqual(len(p), 4)
        self.assertEqual(p, [("u1", "a1"), ("u2", "a2"), ("u3", "a3"), ("u4", "a4")])

    def test_pairlist_and_qa_dict(self):
        self.assertEqual(EV.history_pairs([["q1", "a1"], ["q2", "a2"], ["q3", "a3"]]),
                         [("q1", "a1"), ("q2", "a2"), ("q3", "a3")])
        self.assertEqual(EV.history_pairs([{"q": "q1", "a": "a1"}, {"q": "q2", "a": "a2"}]),
                         [("q1", "a1"), ("q2", "a2")])

    def test_incomplete_dropped(self):
        self.assertEqual(EV.history_pairs([{"role": "user", "content": "x"}]), [])
        self.assertEqual(EV.history_pairs([{"role": "user", "content": "x"},
                                           {"role": "user", "content": "y"},
                                           {"role": "assistant", "content": "z"}]), [("y", "z")])

    def test_mt20_each_case_expected_rounds(self):
        """S2：MT20 每条 case 的 history 偶数/交替，且 history_pairs 轮数==预期轮数。"""
        path = os.path.join(ROOT, "out", "SFT-EXTRA-CASES-v9-MT20.jsonl")
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        self.assertEqual(len(rows), 20)
        for r in rows:
            h = r["history"]
            expected = len(h) // 2
            self.assertIn(expected, (3, 4, 5, 6, 7, 8), r["id"])
            self.assertEqual([x["role"] for x in h], ["user", "assistant"] * expected, r["id"])
            self.assertEqual(len(EV.history_pairs(h)), expected, r["id"])

    def test_chatml_order_system_history_final_user(self):
        h = []
        for i in range(1, 9):      # 8 轮
            h += [{"role": "user", "content": "u%d" % i}, {"role": "assistant", "content": "a%d" % i}]
        p = EV.chatml("SYS", EV.history_pairs(h), "最后提问")
        self.assertTrue(p.startswith("<|im_start|>system\nSYS<|im_end|>\n"))
        self.assertEqual(p.count("<|im_start|>user"), 9)        # 8 历史 + 最后提问
        self.assertEqual(p.count("<|im_start|>assistant"), 9)   # 8 历史回答 + 生成前缀
        idx = [p.index("u%d" % i) for i in range(1, 9)] + [p.index("a8"), p.index("最后提问")]
        self.assertEqual(idx, sorted(idx))                       # 历史顺序正确
        self.assertLess(p.index("a8"), p.index("最后提问"))        # 最后一轮回答在最后提问之前
        self.assertIn("<|im_start|>user\n最后提问<|im_end|>\n<|im_start|>assistant\n", p)
        self.assertTrue(p.endswith("<|im_start|>assistant\n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)