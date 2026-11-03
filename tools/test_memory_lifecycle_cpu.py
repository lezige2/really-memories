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

    def _app(self, cap, access, archive=False):
        tmp = tempfile.mkdtemp(prefix="life_app_")
        model = os.path.join(tmp, "model.stub")
        D.install_fake_model(model)
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                          blocks_dir=os.path.join(tmp, "b"),
                          sessions_dir=os.path.join(tmp, "s"),
                          model_path=model, restore=False,
                          retrieval_mode="topk", topk=4, logger=False,
                          lifecycle_cap=cap, memory_access=access,
                          lifecycle_archive=archive)

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

    def test_auto_archive_grouping_and_sha(self):
        import json as _json
        from datetime import datetime
        rows = [
            (1, "m1", "l", "t1", "h", 1, "p", 8, "2026-01-05T10:00:00"),
            (2, "m2", "l", "t2", "h", 1, "p", 8, "2026-01-20T10:00:00"),
            (3, "m3", "l", "t3", "h", 1, "p", 8, "2026-02-02T10:00:00"),
        ]
        now = datetime(2026, 3, 1)
        d = os.path.join(self.tmp, "archive")
        res = L.auto_archive(self.con, rows, now, d)
        self.assertEqual(sorted(res["months"]), ["2026-01", "2026-02"])
        self.assertEqual(sorted(res["months"]["2026-01"]), [1, 2])
        self.assertEqual(sorted(res["months"]["2026-02"]), [3])
        for z in res["zips"]:
            import hashlib
            self.assertTrue(os.path.exists(z["zip"]))
            self.assertEqual(hashlib.sha256(open(z["zip"], "rb").read()).hexdigest(),
                             z["zip_sha256"])
        self.assertEqual(L.active_rows(self.con, rows), [])   # 全部归档

    def test_auto_archive_idempotent(self):
        from datetime import datetime
        rows = [(1, "m1", "l", "t1", "h", 1, "p", 8, "2026-01-05T10:00:00")]
        d = os.path.join(self.tmp, "archive")
        L.auto_archive(self.con, rows, datetime(2026, 3, 1), d)
        r2 = L.auto_archive(self.con, rows, datetime(2026, 3, 1), d)
        self.assertEqual(r2["candidates"], [])         # 已归档跳过
        r3 = L.auto_archive(self.con, rows, datetime(2026, 3, 1), d)
        self.assertEqual(r3["zips"], [])

    def test_off_archive_writes_nothing(self):
        app = self._app(True, False, archive=False)
        app.archive_dir = os.path.join(self.tmp, "arch_off")
        app._rows = lambda: [(1, "m1", "l", "t1", "h", 1, "p", 8,
                              "2026-01-05T10:00:00")]
        app._mem_check_capacity(200)                   # on cap, archive off
        self.assertFalse(os.path.exists(app.archive_dir))
        self.assertEqual(L.archived_ids(app.con), set())

    def test_on_archive_writes(self):
        app = self._app(True, False, archive=True)
        app.archive_dir = os.path.join(self.tmp, "arch_on")
        app._rows = lambda: [(1, "m1", "l", "t1", "h", 1, "p", 8,
                              "2026-01-05T10:00:00")]
        app._mem_check_capacity(200)
        zips = [f for f in os.listdir(app.archive_dir) if f.endswith(".zip")]
        self.assertTrue(zips)
        self.assertEqual(L.archived_ids(app.con), {1})

    def _archived_app(self, flag):
        app = self._app(True, False)
        app.archive_dir = os.path.join(self.tmp, "arch_fb")
        rows = [(1, "m1", "l", "我的车牌号是皖K3D7F9", "h", 1, "p", 8,
                 "2026-01-05T10:00:00")]
        L.auto_archive(app.con, rows, __import__("datetime").datetime(2026, 3, 1),
                       app.archive_dir)
        app.lifecycle_fallback = flag
        return app

    def test_fallback_hit_and_miss(self):
        app = self._archived_app(True)
        hits = L.fallback_archive(app.con, "车牌号是多少", app.archive_dir)
        self.assertTrue(hits)
        self.assertGreater(hits[0]["score"], 0)
        self.assertEqual(hits[0]["month"], "2026-01")
        self.assertTrue(hits[0]["text_sha"])
        self.assertEqual(L.fallback_archive(app.con, "完全不相关的问题", app.archive_dir), [])

    def test_fallback_bad_zip_skipped(self):
        app = self._archived_app(True)
        z = [os.path.join(app.archive_dir, f) for f in os.listdir(app.archive_dir)
             if f.endswith(".zip")][0]
        data = bytearray(open(z, "rb").read())
        data[-6] ^= 0xFF
        open(z, "wb").write(bytes(data))
        self.assertEqual(L.fallback_archive(app.con, "车牌号是多少", app.archive_dir), [])

    def test_fallback_off_by_default(self):
        app = self._app(True, False)
        self.assertFalse(app.lifecycle_fallback)
        with mock.patch.object(D, "NATURAL_MODE", True):
            app._ask_natural = lambda t, t0: {"answer": "x", "block_ids": []}
            res = app.ask("车牌号是多少")
        self.assertNotIn("archive_hits", res)

    def test_fallback_no_daily_write(self):
        app = self._archived_app(True)
        before = app.con.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0]
        with mock.patch.object(D, "NATURAL_MODE", True):
            app._ask_natural = lambda t, t0: {"answer": "x", "block_ids": []}
            res = app.ask("车牌号是多少")
        self.assertIn("archive_hits", res)
        self.assertEqual(app.con.execute("SELECT COUNT(*) FROM memory_source")
                         .fetchone()[0], before)
        # 归档表未被改写
        n = app.con.execute("SELECT COUNT(*) FROM memory_archive").fetchone()[0]
        self.assertEqual(n, 1)

    def test_reheat_restore_and_skip(self):
        from datetime import datetime
        rows = [(1, "m1", "l", "我的车牌号是皖K3D7F9", "h", 1, "p", 8,
                 "2026-01-05T10:00:00")]
        d = os.path.join(self.tmp, "arch_rh")
        L.auto_archive(self.con, rows, datetime(2026, 3, 1), d)
        self.con.execute("INSERT INTO memory_source (id,tenant,scope,mode,name,"
                         "label,text,source_hash,created_at) VALUES "
                         "(1,'default','private','chat','m1','l',"
                         "'我的车牌号是皖K3D7F9','h','2026-01-05T10:00:00')")
        self.con.commit()
        p = L.reheat_plan(self.con, 1, [])
        self.assertEqual(p["action"], "restore")
        # 有更新行 -> skip_superseded
        live = [(5, "m5", "l", "我的车牌号是皖K9Z9Z9", "h", 1, "p", 8,
                 "2026-02-01T10:00:00")]
        p2 = L.reheat_plan(self.con, 1, live)
        self.assertEqual(p2["action"], "skip_superseded")
        self.assertEqual(p2["superseded_by"], 5)

    def test_reheat_bad_sha(self):
        from datetime import datetime
        rows = [(1, "m1", "l", "我的车牌号是皖K3D7F9", "h", 1, "p", 8,
                 "2026-01-05T10:00:00")]
        d = os.path.join(self.tmp, "arch_bad")
        L.auto_archive(self.con, rows, datetime(2026, 3, 1), d)
        z = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".zip")][0]
        data = bytearray(open(z, "rb").read())
        data[-6] ^= 0xFF
        open(z, "wb").write(bytes(data))
        p = L.reheat_plan(self.con, 1, [])
        self.assertEqual(p["action"], "skip")
        self.assertEqual(p["reason"], "bad_zip_or_sha")

    def test_reheat_no_subject_conservative(self):
        from datetime import datetime
        import archive_store as A
        d = os.path.join(self.tmp, "arch_ns")
        z = os.path.join(d, "2026-01.zip")
        side = z + ".sidecar.json"
        A.archive_rows([{"id": 7, "name": "m7", "text": "哈哈哈哈", "created_at":
                         "2026-01-05T10:00:00"}], z, side)
        L.archive_mark(self.con, [7], z, A.sha_file(z))
        p = L.reheat_plan(self.con, 7, [])
        self.assertEqual(p["action"], "skip")
        self.assertIn(p["reason"], ("no_subject", "no_predicate"))

    def test_reheat_no_db_write(self):
        from datetime import datetime
        rows = [(1, "m1", "l", "我的车牌号是皖K3D7F9", "h", 1, "p", 8,
                 "2026-01-05T10:00:00")]
        d = os.path.join(self.tmp, "arch_nw")
        L.auto_archive(self.con, rows, datetime(2026, 3, 1), d)
        before = self.con.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0]
        L.reheat_plan(self.con, 1, [])
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM memory_source")
                         .fetchone()[0], before)

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
