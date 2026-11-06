# -*- coding: utf-8 -*-
"""时间两轴 POC：相对词归一/最具体/无答案 abstain/空过滤回退。"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import temporal_retrieval as T  # noqa: E402


class NormTests(unittest.TestCase):
    def test_relative_terms(self):
        a = "2026-11-06T09:00:00"
        self.assertEqual(T.normalize("去年", a)["start"], "2025-01-01")
        self.assertEqual(T.normalize("明年", a)["start"], "2027-01-01")
        self.assertEqual(T.normalize("上个月", a)["start"], "2026-10-01")
        self.assertEqual(T.normalize("前天", a)["start"], "2026-11-04")
        r = T.normalize("上周", a)
        self.assertEqual(r["start"], "2026-10-26")
        self.assertEqual(r["end"], "2026-11-01")

    def test_most_specific(self):
        p = T.normalize("2025年我在上个月搬了家", "2026-11-06T09:00:00")
        self.assertEqual(p["kind"], "M")
        self.assertEqual(p["start"][:7], "2026-10")
        p2 = T.normalize("我 2026-10-15 去体检", "2026-11-06T09:00:00")
        self.assertEqual(p2["kind"], "D")


class SearchTests(unittest.TestCase):
    A = "2026-11-06T09:00:00"

    def test_abstain_when_no_block_in_range(self):
        r = T.search("三年前我养过什么宠物？", self.A,
                     [{"id": 1, "text": "我现在养了一只猫",
                       "created_at": self.A}])
        self.assertTrue(r["abstain"])
        self.assertEqual(r["reason"], "no_time_match")
        self.assertEqual(r["kept"], [])

    def test_time_and_topic_kept(self):
        r = T.search("上周我去哪出差？", self.A,
                     [{"id": 1, "text": "上周我去南京出差了。",
                       "created_at": self.A}])
        self.assertFalse(r["abstain"])
        self.assertEqual(r["kept"][0]["normalized_date"], "2026-10-26")
        self.assertEqual(r["kept"][0]["anchor"], self.A)

    def test_no_time_never_empty(self):
        r = T.search("我的猫叫什么", self.A,
                     [{"id": 1, "text": "我养了一只猫叫豆豆",
                       "created_at": self.A}])
        self.assertFalse(r["abstain"])
        self.assertTrue(r["kept"])

    def test_15case_gate(self):
        import json
        root = os.path.dirname(_HERE)
        cases = [json.loads(l) for l in open(
            os.path.join(root, "out", "TIME-15-CASES.jsonl"), encoding="utf-8")]
        hit = 0
        for c in cases:
            r = T.search(c["query"], c["anchor"],
                         [{"id": 1, "text": c["block"],
                           "created_at": c["created_at"]}])
            if c["expected"]["kind"] == "refusal":
                hit += r["abstain"]
            elif r["kept"]:
                v = str(c["expected"]["value"])
                nd = r["kept"][0]["normalized_date"] or ""
                hit += (v in c["block"]) or nd.startswith(v[:7])
        self.assertGreaterEqual(hit, 14)


class RetroTests(unittest.TestCase):
    A = "2026-11-06T09:00:00"

    def test_retro_terms(self):
        for q in ("去年我去过哪", "上个月买了什么", "上周去哪出差",
                  "昨天做了什么", "三年前养过什么宠物"):
            self.assertTrue(T.is_retrospective(q, self.A), q)

    def test_future_not_retro(self):
        for q in ("下周三要做什么", "明年有什么计划", "下个月要交什么",
                  "今天忙不忙", "明天几点开会"):
            self.assertFalse(T.is_retrospective(q, self.A), q)

    def test_past_absolute_date(self):
        self.assertTrue(T.is_retrospective("2024-03-01 我在哪", self.A))
        self.assertFalse(T.is_retrospective("2027-03-01 我在哪", self.A))


class WireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        import chat_daily as D
        cls.D = D
        cls.tmp = tempfile.mkdtemp(prefix="tm_")
        cls.model = os.path.join(cls.tmp, "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, flag):
        D = self.D
        import tempfile
        tmp = tempfile.mkdtemp(prefix="tm_%s_" % self.id())
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                          blocks_dir=os.path.join(tmp, "b"),
                          sessions_dir=os.path.join(tmp, "s"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4, logger=False,
                          temporal_memory=flag)

    def _seed(self, app, text):
        app.remember(text)
        return app._rows()

    def test_lazy_no_time_identical(self):
        off, on = self.make_app(False), self.make_app(True)
        rows = self._seed(off, "我的猫叫豆豆")
        on._rows = lambda: rows
        off._rows = lambda: rows
        sel = [{"source_id": rows[0][0], "name": rows[0][1], "score": 1.0}]
        off._retrieval_select_k2 = lambda t: list(sel)
        on._retrieval_select_k2 = lambda t: list(sel)
        q = "我的猫叫什么"
        self.assertEqual(off._retrieval_select(q), on._retrieval_select(q))
        self.assertIsNone(on._last_temporal)

    def test_second_ask_without_time_no_field(self):
        app = self.make_app(True)
        app.remember("我去年去过云南大理")
        ids = [r[0] for r in app._rows()]
        app._retrieval_select_k2 = lambda t: [
            {"source_id": i, "name": "m%d" % i, "score": 1.0} for i in ids]
        from unittest import mock

        def fake(t, t0):
            app._retrieval_select(t)
            return {"answer": "x", "block_ids": []}

        app._ask_natural = fake
        with mock.patch.object(self.D, "NATURAL_MODE", True):
            app.ask("我去年去过哪")
            self.assertTrue(app._last_temporal)
            res2 = app.ask("我的猫叫什么")
        self.assertIsNone(app._last_temporal)
        self.assertNotIn("temporal_memory", res2)

    def test_next_week_lazy_identical(self):
        off, on = self.make_app(False), self.make_app(True)
        rows = self._seed(off, "下周三我要开会")
        on._rows = lambda: rows
        off._rows = lambda: rows
        sel = [{"source_id": rows[0][0], "name": rows[0][1], "score": 1.0}]
        off._retrieval_select_k2 = lambda t: list(sel)
        on._retrieval_select_k2 = lambda t: list(sel)
        q = "下周三我要做什么"
        self.assertEqual(off._retrieval_select(q), on._retrieval_select(q))
        self.assertIsNone(on._last_temporal)

    def test_abstain_message(self):
        app = self.make_app(True)
        app.remember("我现在养了一只猫")
        ids = [r[0] for r in app._rows()]
        app._retrieval_select_k2 = lambda t: [
            {"source_id": i, "name": "m%d" % i, "score": 1.0} for i in ids]
        from unittest import mock

        def fake(t, t0):
            app._retrieval_select(t)
            return {"answer": "模型自由发挥", "block_ids": []}

        app._ask_natural = fake
        with mock.patch.object(self.D, "NATURAL_MODE", True):
            res = app.ask("三年前我养过什么宠物")
        self.assertTrue(res["temporal_memory"]["abstain"])
        self.assertEqual(res["answer"], "那段时间没有记录。")

    def test_off_no_field(self):
        app = self.make_app(False)
        app._ask_natural = lambda t, t0: {"answer": "x", "block_ids": []}
        from unittest import mock
        with mock.patch.object(self.D, "NATURAL_MODE", True):
            res = app.ask("去年我去过哪")
        self.assertNotIn("temporal_memory", res)

    def test_time_filter_abstain_and_fields(self):
        app = self.make_app(True)
        app.remember("我去年去过云南大理")
        app.remember("我现在养了一只猫")
        ids = [r[0] for r in app._rows()]
        app._retrieval_select_k2 = lambda t: [
            {"source_id": i, "name": "m%d" % i, "score": 1.0} for i in ids]
        out = app._retrieval_select("我去年去过哪？")
        self.assertEqual(len(out), 1)
        self.assertEqual(app._last_temporal["normalized_query"]["start"],
                         "2025-01-01")
        self.assertTrue(app._last_temporal["kept"])
        self.assertIn("normalized_date", app._last_temporal["kept"][0])
        # abstain
        out2 = app._retrieval_select("三年前我养过什么宠物？")
        self.assertEqual(out2, [])
        self.assertTrue(app._last_temporal["abstain"])


if __name__ == "__main__":
    unittest.main()
