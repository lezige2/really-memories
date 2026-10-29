# -*- coding: utf-8 -*-
"""CPU-only tests for the neutral repair prompt（verifier repair 只带 query+answer）.

Run: python -X utf8 -m unittest discover -s tools -p "test_repair_prompt_cpu.py" -v
"""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import chat_daily as D  # noqa: E402
import answer_verifier as av  # noqa: E402


class FakeVerifier:
    def strip_continuation(self, text):
        return text


def blocks():
    return [{"id": 1, "text": "我的银行卡尾号是8899"},
            {"id": 2, "text": "我的车牌号是津D65432，下周三要去北京出差。"}]


class RepairPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="repair_prompt_")
        cls.model = os.path.join(cls.tmp, "model.stub")
        D.install_fake_model(cls.model)
        cls.app = D.DailyApp(
            D.StubEngine(), db_path=os.path.join(cls.tmp, "daily.db"),
            blocks_dir=os.path.join(cls.tmp, "blocks"),
            sessions_dir=os.path.join(cls.tmp, "sessions"),
            model_path=cls.model, restore=False, retrieval_mode="topk",
            topk=4, k2_family=True, logger=False)

    def test_prompt_contains_no_kv_text_or_values(self):
        p = self.app._repair_prompt("我的银行卡尾号是多少？", "你的尾号是88888", blocks())
        # 记忆块的值/实体/日期一律不得进入 repair prompt
        self.assertNotIn("8899", p)
        self.assertNotIn("津D65432", p)
        self.assertNotIn("北京", p)
        self.assertNotIn("记忆原文", p)
        self.assertNotIn("注意核对", p)
        self.assertNotIn("请确认", p)
        self.assertNotIn("当前时间", p)          # 不注入日期
        # 只允许原 query + 模型自己的答案
        self.assertIn("我的银行卡尾号是多少？", p)
        self.assertIn("88888", p)

    def test_prompt_identical_regardless_of_blocks(self):
        a = self.app._repair_prompt("我的车牌号是多少？", "京A88888", blocks())
        b = self.app._repair_prompt("我的车牌号是多少？", "京A88888", [])
        self.assertEqual(a, b)                  # 完全不用 KV 文本

    def test_prompt_meta_audit(self):
        self.app._repair_prompt("我的银行卡尾号是多少？", "你的尾号是88888", blocks())
        meta = self.app._last_repair_prompt_meta
        self.assertEqual(meta["sources"], ["query", "answer"])
        self.assertFalse(meta["contains_kv_text"])
        self.assertFalse(meta["contains_hint"])
        self.assertFalse(meta["contains_expected_value"])
        self.assertEqual(meta["blocks_included"], 0)
        self.assertFalse(meta["with_time"])

    def test_neutral_reask_repair_path(self):
        calls = {"n": 0}

        def fake_verify(text, answer, blks, mode, avv):
            calls["n"] += 1
            return {"verdict": "unsupported" if calls["n"] == 1 else "pass",
                    "mismatches": [], "hint": "记忆里的对应值是「8899」"}

        self.app._verify_run = fake_verify
        prompts = []

        def repair(prompt):
            prompts.append(prompt)
            return "能再说一次吗"

        with mock.patch.object(D, "_get_verifier", return_value=FakeVerifier()):
            final, info = self.app._verified_finalize(
                "我的银行卡尾号是多少？", "你的尾号是88888", blocks(),
                "personal", repair, time.perf_counter(), "natural")
        self.assertEqual(final, "能再说一次吗")     # 中性重问，不带值
        self.assertNotIn("8899", final)
        self.assertEqual(len(prompts), 1)
        self.assertNotIn("8899", prompts[0])        # 不把 verifier hint 塞进 prompt
        self.assertEqual(info["repair_prompt"]["sources"], ["query", "answer"])
        self.assertFalse(info["repair_prompt"]["contains_kv_text"])

    def test_v1_verify_path_unchanged(self):
        with mock.patch.dict(os.environ, {"VERIFIER_VERSION": "v1"}):
            v = av.verify("我的银行卡尾号是多少？", "你的尾号是88888",
                          blocks(), mode="personal")
        self.assertEqual(v["verdict"], "unsupported")
        self.assertEqual(v["mismatches"][0]["type"], "value_not_in_memory")


if __name__ == "__main__":
    unittest.main()