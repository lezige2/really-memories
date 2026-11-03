# -*- coding: utf-8 -*-
"""强制 JSON：解析/单次重试/回退/渲染无花括号/自报 id 不作证据。"""
import json
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
import json_answer as J  # noqa: E402


class ParseTests(unittest.TestCase):
    def test_valid(self):
        p = J.parse('{"status":"found","answer":"顺丰","source_block_id":22}')
        self.assertEqual(p["status"], "found")
        self.assertEqual(p["answer"], "顺丰")
        self.assertEqual(p["source_block_id"], 22)
        p = J.parse('{"status":"not_found","answer":"不知道","source_block_id":null}')
        self.assertIsNone(p["source_block_id"])

    def test_fenced_and_think(self):
        p = J.parse("```json\n{\"status\":\"found\",\"answer\":\"A\","
                    "\"source_block_id\":3}\n```")
        self.assertEqual(p["answer"], "A")
        p = J.parse("<think>x</think>{\"status\":\"not_found\",\"answer\":\"B\","
                    "\"source_block_id\":null}")
        self.assertEqual(p["status"], "not_found")

    def test_missing_fields_invalid(self):
        for raw in ('{"status":"found"}', '{"status":"maybe","answer":"x"}',
                    '{"answer":"x"}', 'not json', '{"status":"found","answer":1}',
                    '[1,2]'):
            self.assertIsNone(J.parse(raw), raw)

    def test_render_no_braces(self):
        raw = '{"status":"found","answer":"顺丰","source_block_id":22}'
        self.assertEqual(J.render_answer(raw), "顺丰")
        bad = '{"status":"found","answer":"顺丰"'
        self.assertNotIn("{", J.render_answer(bad))
        self.assertEqual(J.render_answer("普通文本"), "普通文本")


class WireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="js_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, flag):
        tmp = tempfile.mkdtemp(prefix="js_%s_" % self.id())
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                          blocks_dir=os.path.join(tmp, "b"),
                          sessions_dir=os.path.join(tmp, "s"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4, logger=False,
                          json_output=flag)

    def test_off_unchanged(self):
        app = self.make_app(False)
        app._ask_natural = lambda t, t0: {"answer": "普通回答", "block_ids": [1]}
        with mock.patch.object(D, "NATURAL_MODE", True):
            res = app.ask("q")
        self.assertEqual(res["answer"], "普通回答")
        self.assertNotIn("json", res)
        self.assertNotIn("json_fallback", res)

    def test_valid_json_rendered_and_id_logged_only(self):
        app = self.make_app(True)
        payload = json.dumps({"status": "found", "answer": "顺丰",
                              "source_block_id": 999}, ensure_ascii=False)
        app._ask_natural = lambda t, t0: {"answer": payload, "block_ids": [22]}
        with mock.patch.object(D, "NATURAL_MODE", True):
            res = app.ask("q")
        self.assertEqual(res["answer"], "顺丰")
        self.assertNotIn("{", res["answer"])
        self.assertEqual(res["json"]["reported_block_id"], 999)
        self.assertFalse(res["json"]["reported_id_used_as_evidence"])
        self.assertEqual(res["block_ids"], [22])          # 实际挂载不变
        self.assertEqual(app._last_json["attempts"], 1)

    def test_retry_once_then_success(self):
        app = self.make_app(True)
        good = json.dumps({"status": "found", "answer": "A", "source_block_id": None})
        calls = {"n": 0}

        def fake(t, t0):
            calls["n"] += 1
            return {"answer": "bad" if calls["n"] == 1 else good,
                    "block_ids": [1]}

        app._ask_natural = fake
        with mock.patch.object(D, "NATURAL_MODE", True):
            res = app.ask("q")
        self.assertEqual(calls["n"], 2)                    # 恰好一次重试
        self.assertEqual(res["answer"], "A")
        self.assertFalse(res.get("json_fallback"))
        self.assertEqual(app._last_json["attempts"], 2)

    def test_second_failure_falls_back(self):
        app = self.make_app(True)
        calls = {"n": 0}

        def fake(t, t0):
            calls["n"] += 1
            return {"answer": "{bad json", "block_ids": [1]}

        app._ask_natural = fake
        with mock.patch.object(D, "NATURAL_MODE", True):
            res = app.ask("q")
        self.assertEqual(calls["n"], 2)                    # 不无限重试
        self.assertTrue(res.get("json_fallback"))
        self.assertNotIn("{", res["answer"])
        self.assertEqual(app._last_json["attempts"], 2)


if __name__ == "__main__":
    unittest.main()
