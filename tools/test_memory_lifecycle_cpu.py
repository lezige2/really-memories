# -*- coding: utf-8 -*-
"""P1 底座：access/archive 独立表、软硬上限、schema 不动 memory_source。"""
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import memory_lifecycle as L  # noqa: E402
import chat_daily as D  # noqa: E402
import memory_source as ms  # noqa: E402


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="life_")
        self.con = sqlite3.connect(os.path.join(self.tmp, "d.db"))
        self.con.executescript(ms.SCHEMA)

    def tearDown(self):
        self.con.close()

    def test_schema_independent(self):
        before = [r[1] for r in self.con.execute("PRAGMA table_info(memory_source)")]
        L.ensure_schema(self.con)
        after = [r[1] for r in self.con.execute("PRAGMA table_info(memory_source)")]
        self.assertEqual(before, after)               # 不改 memory_source
        tabs = {r[0] for r in self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("memory_access", tabs)
        self.assertIn("memory_archive", tabs)

    def test_record_access_accumulates(self):
        L.record_access(self.con, [1, 2])
        L.record_access(self.con, [1])
        st = L.access_stats(self.con)
        self.assertEqual(st[1]["access_count"], 2)
        self.assertEqual(st[2]["access_count"], 1)
        self.assertTrue(st[1]["last_accessed_at"])

    def test_archive_filters_rows(self):
        rows = [(1, "a", "l", "t", "h", 1, "p", 8),
                (2, "b", "l", "t", "h", 1, "p", 8)]
        L.archive_mark(self.con, [2], "/tmp/x.zip", "sha")
        self.assertEqual([r[0] for r in L.active_rows(self.con, rows)], [1])

    def _app(self, cap, access):
        tmp = tempfile.mkdtemp(prefix="life_app_")
        model = os.path.join(tmp, "model.stub")
        D.install_fake_model(model)
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                          blocks_dir=os.path.join(tmp, "b"),
                          sessions_dir=os.path.join(tmp, "s"),
                          model_path=model, restore=False,
                          retrieval_mode="topk", topk=4, logger=False,
                          lifecycle_cap=cap, memory_access=access)

    def test_off_keeps_old_200_reject(self):
        app = self._app(False, False)
        app._mem_check_capacity(199)
        for n in (200, 201):
            with self.assertRaises(D.DailyError) as ctx:
                app._mem_check_capacity(n)
            self.assertEqual(ctx.exception.code, "memory_full")
            self.assertIn("上限 200", ctx.exception.message)

    def test_off_no_access_table(self):
        import json as _json
        app = self._app(False, False)
        with mock.patch.object(D, "NATURAL_MODE", True):
            app._ask_natural = lambda t, t0: {"answer": "x", "block_ids": [1, 2]}
            app.ask("q")
        tabs = {r[0] for r in app.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("memory_access", tabs)       # off 不建表

    def test_on_access_recorded(self):
        app = self._app(True, True)
        with mock.patch.object(D, "NATURAL_MODE", True):
            app._ask_natural = lambda t, t0: {"answer": "x", "block_ids": [1, 2]}
            app.ask("q")
        n = app.con.execute("SELECT COUNT(*) FROM memory_access").fetchone()[0]
        self.assertEqual(n, 2)

    def test_capacity_soft_hard(self):
        app = self._app(True, False)
        for n in (199, 200, 201):
            app.warnings = []
            app._mem_check_capacity(n)                # 不拒
            if n >= 200:
                self.assertTrue(app.warnings)
        with self.assertRaises(D.DailyError) as ctx:
            app._mem_check_capacity(2000)
        self.assertEqual(ctx.exception.code, "memory_full")


if __name__ == "__main__":
    unittest.main()
