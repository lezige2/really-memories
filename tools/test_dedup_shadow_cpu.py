# -*- coding: utf-8 -*-
"""--dedup-shadow：off 零调用；on 只记 would_merge、绝不合并/改响应。"""
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
import shadow_dedup as S  # noqa: E402

ROOT = os.path.dirname(_HERE)


class ShadowFlagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="sd_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, flag):
        tmp = tempfile.mkdtemp(prefix="sd_%s_" % self.id())
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                          blocks_dir=os.path.join(tmp, "b"),
                          sessions_dir=os.path.join(tmp, "s"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4, logger=False,
                          dedup_shadow=flag)

    def test_off_zero_calls(self):
        app = self.make_app(False)
        with mock.patch.object(D.sdedup, "decide",
                               side_effect=AssertionError("must not call")):
            app.remember("我的猫叫豆豆")
        self.assertFalse(app._last_shadow["enabled"])
        self.assertEqual(app._last_shadow["checked"], 0)

    def test_on_logs_but_does_not_merge(self):
        app = self.make_app(True)
        a = app.remember("我的猫叫豆豆")
        b = app.remember("我家猫名字是豆豆")
        self.assertNotEqual(a["id"], b["id"])             # 未合并
        self.assertEqual(app.con.execute("SELECT COUNT(*) FROM memory_source")
                         .fetchone()[0], 2)
        self.assertTrue(app._last_shadow["hits"])
        hit = app._last_shadow["hits"][0]
        for k in ("id", "pair", "risk", "score", "merge_allowed"):
            self.assertIn(k, hit)
        self.assertNotIn("shadow", b)                     # 响应不改

    def test_multi_entity_risk(self):
        app = self.make_app(True)
        app.remember("我的车是白色")
        app.remember("我又买了一辆车，也是白色")
        risks = [h["risk"] for h in app._last_shadow["hits"]]
        self.assertIn("multi_entity", risks)

    def test_42_fixtures_zero_wrong_merge(self):
        fx = [json.loads(l) for l in
              open(os.path.join(ROOT, "out", "KV-CONFLICT-40.jsonl"),
                   encoding="utf-8")]
        fe = S.evaluate_fixtures(fx)
        self.assertEqual(fe["fixtures"], 42)
        self.assertEqual(fe["wrong_merge"], 0)


if __name__ == "__main__":
    unittest.main()
