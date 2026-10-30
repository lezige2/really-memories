# -*- coding: utf-8 -*-
"""三层 CLI 确认（/remember 显式冲突）单测；flag off 逐字不变。

Run: python -X utf8 -m unittest discover -s tools -p "test_confirm_writes_cpu.py" -v
"""
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import chat_daily as D  # noqa: E402

LEGACY_KEYS = {"id", "n_tokens", "created_at", "duplicate", "name", "tags",
               "source", "related_ids", "slots", "slots_unverified", "block_sha16"}


class ConfirmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="confirm_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, confirm):
        tmp = tempfile.mkdtemp(prefix="confirm_%s_" % self.id())
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "daily.db"),
                          blocks_dir=os.path.join(tmp, "blocks"),
                          sessions_dir=os.path.join(tmp, "sessions"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4,
                          confirm_writes=confirm, logger=False)

    def seed(self, app):
        app.remember("我的车牌号是京A11111")
        app.remember("我的车牌号是京B22222")

    CONFLICT_TEXT = "我的车牌号是沪C33333，原来是京A11111"

    def test_flag_off_unchanged(self):
        app = self.make_app(False)
        for i in range(20):
            r = app.remember("测试事实 %d：我的工位在B座30%d" % (i, i % 9))
            self.assertEqual(set(r), LEGACY_KEYS, i)     # 无新增字段
            self.assertNotIn("needs_confirmation", r)
        self.assertEqual(app._confirm_stats["total"], 0)

    def test_trigger_zero_write_then_confirm(self):
        app = self.make_app(True)
        self.seed(app)
        before = len(app._rows())
        calls = []
        orig = app._put_memory_source
        app._put_memory_source = lambda text, **kw: calls.append(text) or orig(text, **kw)
        r = app.remember(self.CONFLICT_TEXT)
        self.assertTrue(r.get("needs_confirmation"))
        self.assertNotIn("id", r)
        self.assertEqual(len(app._rows()), before)       # 确认前零写入
        self.assertEqual(calls, [])
        token = r["confirm_token"]
        r2 = app.remember(self.CONFLICT_TEXT, confirm_token=token)
        self.assertIn("id", r2)
        self.assertEqual(len(app._rows()), before + 1)
        self.assertEqual(len(calls), 1)                  # 同一 _put_memory_source

    def test_replay_and_changed_text_rejected(self):
        app = self.make_app(True)
        self.seed(app)
        tok = app.remember(self.CONFLICT_TEXT)["confirm_token"]
        app.remember(self.CONFLICT_TEXT, confirm_token=tok)
        with self.assertRaises(D.DailyError) as c1:      # 重放
            app.remember(self.CONFLICT_TEXT, confirm_token=tok)
        self.assertEqual(c1.exception.code, "confirm_invalid")
        tok2 = app.remember(self.CONFLICT_TEXT)["confirm_token"]
        with self.assertRaises(D.DailyError) as c2:      # 换文本
            app.remember("我的车牌号是粤D44444", confirm_token=tok2)
        self.assertEqual(c2.exception.code, "confirm_invalid")

    def test_expired_and_restart(self):
        app = self.make_app(True)
        self.seed(app)
        tok = app.remember(self.CONFLICT_TEXT)["confirm_token"]
        app._pending_confirms[tok]["expires"] = 0
        with self.assertRaises(D.DailyError) as c:
            app.remember(self.CONFLICT_TEXT, confirm_token=tok)
        self.assertEqual(c.exception.code, "confirm_expired")
        tok2 = app.remember(self.CONFLICT_TEXT)["confirm_token"]
        app2 = self.make_app(True)                        # 模拟进程重启（只存内存）
        self.assertNotIn(tok2, app2._pending_confirms)
        with self.assertRaises(D.DailyError):
            app2.remember(self.CONFLICT_TEXT, confirm_token=tok2)

    def test_trigger_rate_on_20_writes(self):
        app = self.make_app(True)
        for i in range(20):
            app.remember("日常事实 %d：我下周三要去第%d个城市出差" % (i, i))
        stats = app._confirm_stats
        rate = stats["asked"] / max(1, stats["total"])
        self.assertLessEqual(rate, 0.20, stats)          # >20% 判追问过多


if __name__ == "__main__":
    unittest.main()