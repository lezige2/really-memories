# -*- coding: utf-8 -*-
"""K2 跳 dup：dup_of 块不参与 kept/hidden，但仍可挂载；K2 off 逐字不变。"""
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import chat_daily as D  # noqa: E402

ROWS = [
    (3, "dup-3", "l", "我的车牌号是京A88888（重复）", "h", 1, "/p", 8),
    (12, "old-12", "l", "我的车牌号是京A88888", "h", 1, "/p", 8),
    (13, "old-13", "l", "我的车牌号是京A88888", "h", 1, "/p", 8),
    (22, "new-22", "l", "我的车牌号换成津E54321了", "h", 1, "/p", 8),
]


class K2DupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="k2dup_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, k2, with_tags):
        tmp = tempfile.mkdtemp(prefix="k2dup_%s_" % self.id())
        app = D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                         blocks_dir=os.path.join(tmp, "b"),
                         sessions_dir=os.path.join(tmp, "s"),
                         model_path=self.model, restore=False,
                         retrieval_mode="topk", topk=4,
                         k2_family=k2, logger=False)
        app._rows = lambda: list(ROWS)
        if with_tags:
            app.con.execute("INSERT OR REPLACE INTO daily_memory_meta(source_id,tags) "
                            "VALUES(3,'[\"dup_of:12\"]')")
            app.con.commit()
        return app

    def test_k2_off_unchanged(self):
        base = self.make_app(False, False)
        marked = self.make_app(False, True)
        fn = lambda t: [{"name": "x", "score": 1.0, "source_id": 12, "signals": {}}]
        base._retrieval_select_normal = fn
        marked._retrieval_select_normal = fn
        self.assertEqual(base._retrieval_select("我的车牌号是多少？"),
                         marked._retrieval_select("我的车牌号是多少？"))

    def test_k2_on_dup_mounts_but_never_kept(self):
        app = self.make_app(True, True)
        out = app._retrieval_select("我的车牌号是多少？")
        ids = [s["source_id"] for s in out]
        self.assertEqual(out[0]["source_id"], 22)
        self.assertIn(3, ids)
        self.assertNotEqual(ids[0], 3)
        self.assertNotIn(12, ids)
        self.assertNotIn(13, ids)
        self.assertEqual(app._last_k2["gate_reason"], "ok")


if __name__ == "__main__":
    unittest.main()
