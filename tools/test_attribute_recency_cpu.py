# -*- coding: utf-8 -*-
"""属性最新值 POC：手机/健身新胜旧；多实体/无属性/换牌不过滤。"""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import attribute_recency as A  # noqa: E402
import chat_daily as D  # noqa: E402


def meta(rows):
    return {i: {"created_at": t, "text": x} for i, t, x in rows}


def sel(ids):
    return [{"source_id": i, "name": "m%d" % i, "score": 1.0} for i in ids]


class RuleTests(unittest.TestCase):
    def test_phone_new_wins(self):
        d = A.apply_filter("我的手机号是多少？", sel([1, 2]), meta([
            (1, "2026-01-01T00:00:00", "我的手机号是139-0000-1111"),
            (2, "2026-02-01T00:00:00", "我的手机号是138-0000-2222")]))
        self.assertTrue(d["applied"])
        self.assertEqual(d["kept"], [2])
        self.assertEqual(d["hidden"], [1])

    def test_fitness_new_wins(self):
        d = A.apply_filter("我几点健身？", sel([1, 2]), meta([
            (1, "2026-01-01T00:00:00", "我周一早上七点健身"),
            (2, "2026-02-01T00:00:00", "我周三晚上八点健身")]))
        self.assertTrue(d["applied"])
        self.assertEqual(d["kept"], [2])
        self.assertEqual(d["hidden"], [1])

    def test_unrelated_block_preserved(self):
        d = A.apply_filter("我的手机号是多少？", sel([1, 2, 3]), meta([
            (1, "2026-01-01T00:00:00", "我的手机号是139-0000-1111"),
            (2, "2026-02-01T00:00:00", "我的手机号是138-0000-2222"),
            (3, "2026-01-15T00:00:00", "今天天气不错，出去走走")]))
        self.assertTrue(d["applied"])
        self.assertEqual(d["kept"], [2, 3])            # 无关块保留
        self.assertEqual(d["hidden"], [1])

    def test_single_valued_block_not_filtered(self):
        d = A.apply_filter("我的手机号是多少？", sel([1, 2]), meta([
            (1, "2026-01-01T00:00:00", "我的手机号是13900001111"),
            (2, "2026-01-15T00:00:00", "今天天气不错")]))
        self.assertFalse(d["applied"])
        self.assertEqual(d["reason"], "value_missing")

    def test_multi_entity_not_filtered(self):
        d = A.apply_filter("我的手机号是多少？", sel([1, 2]), meta([
            (1, "2026-01-01T00:00:00", "我的手机号是13900001111"),
            (2, "2026-02-01T00:00:00", "我还有一只手机号是13800002222")]))
        self.assertFalse(d["applied"])
        self.assertEqual(d["reason"], "multi_entity")

    def test_t003_not_filtered(self):
        d = A.apply_filter("我的车牌是多少？", sel([1, 2]), meta([
            (1, "2026-01-01T00:00:00", "牌子换成苏E8L2M6了"),
            (2, "2026-02-01T00:00:00", "又添了辆车，牌是苏E8L2M6")]))
        self.assertFalse(d["applied"])
        self.assertEqual(d["reason"], "no_attribute")

    def test_no_attribute(self):
        self.assertFalse(A.apply_filter("今天天气如何", sel([1]), {})["applied"])


class WireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="ar_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, flag):
        tmp = tempfile.mkdtemp(prefix="ar_%s_" % self.id())
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                          blocks_dir=os.path.join(tmp, "b"),
                          sessions_dir=os.path.join(tmp, "s"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4, logger=False,
                          attribute_recency=flag)

    def test_flag_off_no_field(self):
        app = self.make_app(False)
        with mock.patch.object(D, "NATURAL_MODE", True):
            app._ask_natural = lambda t, t0: {"answer": "x", "block_ids": []}
            res = app.ask("我的手机号是多少")
        self.assertNotIn("attribute_recency", res)

    def test_wire_filters_selection(self):
        app = self.make_app(True)
        app._retrieval_select_k2 = lambda text: [
            {"source_id": 1, "name": "a", "score": 1.0},
            {"source_id": 2, "name": "b", "score": 2.0}]
        for sid, text, ts in ((1, "我的手机号是13900001111", "2026-01-01T00:00:00"),
                              (2, "我的手机号是13800002222", "2026-02-01T00:00:00")):
            app.remember(text)
        # remember 使用真实 DB id；改用真实行 id
        ids = [r[0] for r in app._rows()]
        app._retrieval_select_k2 = lambda text: [
            {"source_id": i, "name": "m%d" % i, "score": 1.0} for i in ids]
        out = app._retrieval_select("我的手机号是多少？")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["source_id"], max(ids))


if __name__ == "__main__":
    unittest.main()
