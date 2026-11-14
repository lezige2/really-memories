# -*- coding: utf-8 -*-
"""CPU tests: S2-A deterministic query expansion（默认 off）。

Run: python -X utf8 -m unittest discover -s tools -p "test_query_expand_cpu.py" -v
"""
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import query_expand as Q  # noqa: E402
import chat_daily as D  # noqa: E402


class ExpandRuleTests(unittest.TestCase):
    def test_plate_brand(self):
        out, hits = Q.expand_query("杨帆那辆车的牌子你还记得不？")
        self.assertIn("车牌", out)
        self.assertEqual(hits[0]["item"], "牌子→车牌")
        # 无车语境不扩
        out2, hits2 = Q.expand_query("这个牌子的衣服怎么样")
        self.assertNotIn("车牌", out2)
        self.assertEqual(hits2, [])

    def test_phone_number(self):
        out, hits = Q.expand_query("周昊号码多少来着？")
        self.assertEqual(hits, [])                        # 无“我”
        out, hits = Q.expand_query("我的号码是多少")
        self.assertIn("手机号", out)
        # 卡/尾号/工号语境不扩
        for q in ("我的银行卡号码是多少", "我的尾号号码是多少", "我的工号号码是多少"):
            _, h = Q.expand_query(q)
            self.assertEqual(h, [], q)

    def test_meeting_only_time_context(self):
        out, hits = Q.expand_query("杨帆那个会定在几号几点了？")
        self.assertIn("会议", out)
        self.assertEqual(hits[0]["item"], "会→会议")
        for q in ("我会做这个", "你学会了吗", "我开会去了"):
            _, h = Q.expand_query(q)
            self.assertEqual(h, [], q)

    def test_hometown(self):
        self.assertIn("老家", Q.expand_query("王强是哪儿人？")[0])
        self.assertIn("老家", Q.expand_query("杨帆是哪里人？")[0])

    def test_keep_original_and_max_two(self):
        q = "我的号码是几号，那车牌子呢"
        out, hits = Q.expand_query(q)
        self.assertTrue(out.startswith(q))                # 原词保留
        self.assertLessEqual(len(hits), 2)


class WireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="qexp_")
        cls.model = os.path.join(cls.tmp, "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, flag):
        tmp = tempfile.mkdtemp(prefix="qexp_%s_" % self.id())
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "daily.db"),
                          blocks_dir=os.path.join(tmp, "blocks"),
                          sessions_dir=os.path.join(tmp, "sessions"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4,
                          query_expand=flag, logger=False)

    def test_flag_off_original_query(self):
        app = self.make_app(False)
        seen = {}
        app._retrieval_select_normal = lambda text: seen.setdefault("q", text) or []
        app._retrieval_select("杨帆那辆车的牌子你还记得不？")
        self.assertEqual(seen["q"], "杨帆那辆车的牌子你还记得不？")
        self.assertFalse(app._last_query_expand["enabled"])

    def test_missing_module_falls_back_to_original(self):
        from unittest import mock
        app = self.make_app(True)
        seen = {}
        app._retrieval_select_normal = lambda text: seen.setdefault("q", text) or []
        with mock.patch.object(D, "_expand_query", None):
            app._retrieval_select("杨帆那辆车的牌子你还记得不？")
        self.assertEqual(seen["q"], "杨帆那辆车的牌子你还记得不？")
        self.assertFalse(app._last_query_expand["enabled"])
        self.assertTrue(app._last_query_expand["unavailable"])
        self.assertTrue(app.warnings)

    def test_module_present_uses_expansion(self):
        self.assertTrue(callable(D._expand_query))
        app = self.make_app(True)
        seen = {}
        app._retrieval_select_normal = lambda text: seen.setdefault("q", text) or []
        app._retrieval_select("杨帆那辆车的牌子你还记得不？")
        self.assertIn("车牌", seen["q"])

    def test_flag_on_expands_and_health(self):
        app = self.make_app(True)
        seen = {}
        app._retrieval_select_normal = lambda text: seen.setdefault("q", text) or []
        app._retrieval_select("杨帆那辆车的牌子你还记得不？")
        self.assertIn("车牌", seen["q"])
        self.assertEqual(app._last_query_expand["hits"][0]["item"], "牌子→车牌")
        h = app.health()
        self.assertTrue(h["retrieval"]["query_expand"]["enabled"])
        self.assertEqual(h["retrieval"]["query_expand"]["hits"][0]["item"], "牌子→车牌")


if __name__ == "__main__":
    unittest.main()