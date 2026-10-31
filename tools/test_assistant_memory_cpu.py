# -*- coding: utf-8 -*-
"""P3 assistant 显式记忆钩子：off 不写、承诺写、普通/否定/敏感不写、异常不伤回答。"""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import chat_daily as D  # noqa: E402
import assistant_commit as AC  # noqa: E402


class ExtractTests(unittest.TestCase):
    def test_explicit_commitments(self):
        for text in ("我明天提醒你带伞。",
                     "我会在周五前把材料发给你。",
                     "下周我会来提醒你开会。"):
            items = AC.extract_commitments(text)
            self.assertEqual(len(items), 1, text)
            self.assertTrue(items[0]["text"].startswith("助手承诺："))

    def test_plain_answer_no_commit(self):
        for text in ("今天天气不错。", "你的手机号是13800138000。",
                     "这是一段普通说明。"):
            self.assertEqual(AC.extract_commitments(text), [], text)

    def test_negation_not_commit(self):
        for text in ("我不会提醒你的。", "明天不需要我提醒你。"):
            self.assertEqual(AC.extract_commitments(text), [], text)

    def test_sensitive_not_commit(self):
        self.assertEqual(AC.extract_commitments(
            "我明天提醒你密码是123456。"), [])


class WireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="p3_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, flag):
        tmp = tempfile.mkdtemp(prefix="p3_%s_" % self.id())
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                          blocks_dir=os.path.join(tmp, "b"),
                          sessions_dir=os.path.join(tmp, "s"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4, logger=False,
                          assistant_memory=flag)

    def test_off_no_write(self):
        app = self.make_app(False)
        app._ask_natural = lambda text, t0: {"answer": "我明天提醒你带伞。",
                                             "block_ids": []}
        app.ask("随便")
        n = app.con.execute(
            "SELECT COUNT(*) FROM memory_source WHERE mode='assistant_commit'"
        ).fetchone()[0]
        self.assertEqual(n, 0)
        self.assertFalse(app._last_assistant_commit["enabled"])

    def test_on_writes_commitment(self):
        app = self.make_app(True)
        app._ask_natural = lambda text, t0: {"answer": "我明天提醒你带伞。",
                                             "block_ids": []}
        res = app.ask("提醒我")
        self.assertEqual(res["answer"], "我明天提醒你带伞。")
        rows = app.con.execute(
            "SELECT id,text FROM memory_source WHERE mode='assistant_commit'").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn("助手承诺：", str(rows[0][1]))
        meta = app._meta_get(rows[0][0])
        self.assertIn("assistant_commit", meta["tags"])
        self.assertEqual(meta["source"], "assistant")
        self.assertEqual(app._last_assistant_commit["written"], [rows[0][0]])

    def test_duplicate_not_written_twice(self):
        app = self.make_app(True)
        app._ask_natural = lambda text, t0: {"answer": "我明天提醒你带伞。",
                                             "block_ids": []}
        app.ask("提醒我")
        app.ask("再提醒我")
        n = app.con.execute(
            "SELECT COUNT(*) FROM memory_source WHERE mode='assistant_commit'"
        ).fetchone()[0]
        self.assertEqual(n, 1)

    def test_exception_does_not_break_answer(self):
        app = self.make_app(True)
        app._ask_natural = lambda text, t0: {"answer": "我明天提醒你带伞。",
                                             "block_ids": []}
        with mock.patch.object(app, "_put_memory_source",
                               side_effect=RuntimeError("boom")):
            res = app.ask("提醒我")
        self.assertEqual(res["answer"], "我明天提醒你带伞。")
        self.assertEqual(len(app._last_assistant_commit["written"]), 0)


if __name__ == "__main__":
    unittest.main()
