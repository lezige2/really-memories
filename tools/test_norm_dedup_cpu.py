# -*- coding: utf-8 -*-
"""norm_hash 去重：空格/全角/标点命中；跨 scope 不吞；近似不误吞；off 不变。"""
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import norm_dedup as N  # noqa: E402
import chat_daily as D  # noqa: E402


class NormTests(unittest.TestCase):
    def test_spaces_fullwidth_punct(self):
        base = N.norm_hash("我叫阿泽，车是京A12345")["norm_hash"]
        for v in ("我叫阿泽 车是京A12345", "我叫阿泽,车是京A12345。",
                  "我叫阿泽　车是京Ａ１２３４５"):
            self.assertEqual(N.norm_hash(v)["norm_hash"], base, v)

    def test_different_text_not_equal(self):
        a = N.norm_hash("我叫阿泽")["norm_hash"]
        b = N.norm_hash("我叫阿泽的朋友")["norm_hash"]
        self.assertNotEqual(a, b)
        self.assertIsNone(N.norm_hash("，。！ "))


class WireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="nd_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, flag):
        tmp = tempfile.mkdtemp(prefix="nd_%s_" % self.id())
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                          blocks_dir=os.path.join(tmp, "b"),
                          sessions_dir=os.path.join(tmp, "s"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4, logger=False,
                          norm_dedup=flag)

    def test_off_unchanged(self):
        app = self.make_app(False)
        a = app.remember("我叫阿泽")
        b = app.remember("我叫阿泽。")          # 标点不同：off 走原 hash，仍新建
        self.assertNotEqual(a["id"], b["id"])
        self.assertNotIn("duplicate_norm", b)
        self.assertEqual(app.con.execute(
            "SELECT COUNT(*) FROM memory_source").fetchone()[0], 2)

    def test_on_duplicate_hits(self):
        app = self.make_app(True)
        a = app.remember("我叫阿泽，车是京A12345")
        b = app.remember("我叫阿泽,车是京A12345。")
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(b.get("duplicate"), "norm")
        self.assertTrue(b.get("duplicate_norm"))
        self.assertEqual(app.con.execute(
            "SELECT COUNT(*) FROM memory_source").fetchone()[0], 1)
        self.assertEqual(app._meta_get(a["id"])["tags"], [])   # 不写 tags

    def test_cross_scope_not_swallowed(self):
        app = self.make_app(True)
        a = app._put_memory_source("我叫阿泽", tenant="default", scope="private")
        # 同文本但不同 scope：不得被 default/private 的已有行吞掉
        b = app._put_memory_source("我叫阿泽", tenant="other", scope="private")
        self.assertFalse(b.get("duplicate_norm"))
        self.assertNotEqual(a["id"], b["id"])

    def test_enum_none_exact_norm(self):
        app = self.make_app(True)
        a = app.remember("我叫阿泽")                     # 新建 none
        self.assertEqual(a.get("duplicate"), "none")
        self.assertFalse(a.get("duplicate_norm"))
        b = app.remember("我叫阿泽")                     # 完全相同 exact
        self.assertEqual(b.get("duplicate"), "exact")
        self.assertFalse(b.get("duplicate_norm"))
        c = app.remember("我叫阿泽。")                   # 归一相同 norm
        self.assertEqual(c.get("duplicate"), "norm")
        self.assertTrue(c.get("duplicate_norm"))
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(a["id"], c["id"])

    def test_off_duplicate_bool_legacy(self):
        app = self.make_app(False)
        a = app.remember("我叫阿泽")
        self.assertIs(a.get("duplicate"), False)         # 旧 bool
        b = app.remember("我叫阿泽")                     # 完全相同 -> True
        self.assertIs(b.get("duplicate"), True)
        self.assertNotIn("duplicate_norm", b)

    def test_near_similar_not_deduped(self):
        app = self.make_app(True)
        app.remember("我叫阿泽")
        b = app.remember("我叫阿泽的朋友")
        self.assertNotIn("duplicate_norm", b)
        self.assertEqual(app.con.execute(
            "SELECT COUNT(*) FROM memory_source").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
