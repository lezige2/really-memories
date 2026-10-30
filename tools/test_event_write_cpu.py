# -*- coding: utf-8 -*-
"""CPU tests: /remember 写侧接 event_date（flag on）；flag off 逐字不变。

Run: python -X utf8 -m unittest discover -s tools -p "test_event_write_cpu.py" -v
"""
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import chat_daily as D  # noqa: E402


class EventWriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="event_write_")
        cls.model = os.path.join(cls.tmp, "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, event_date):
        tmp = tempfile.mkdtemp(prefix="event_write_%s_" % self.id())
        return D.DailyApp(
            D.StubEngine(), db_path=os.path.join(tmp, "daily.db"),
            blocks_dir=os.path.join(tmp, "blocks"),
            sessions_dir=os.path.join(tmp, "sessions"),
            model_path=self.model, restore=False, retrieval_mode="topk",
            topk=4, event_date=event_date, logger=False)

    def row(self, sid):
        return self.app.con.execute(
            "SELECT event_date,event_time,event_confidence,event_source,"
            "event_tz,event_parser_version,event_basis_ts FROM memory_source "
            "WHERE id=?", (sid,)).fetchone()

    def test_remember_tomorrow_writes_event(self):
        self.app = self.make_app(True)
        put = self.app._put_memory_source("明天下午三点开会")
        self.assertFalse(put["duplicate"])
        row = self.row(put["id"])
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(row[0], tomorrow)
        self.assertEqual(row[1], "15:00")
        self.assertEqual(row[2], "high")
        self.assertEqual(row[4], "Asia/Shanghai")
        self.assertEqual(row[5], "event-time-1.0")
        self.assertTrue(row[6])                     # event_basis_ts 完整时间戳

    def test_remember_periodic_has_null_date(self):
        self.app = self.make_app(True)
        put = self.app._put_memory_source("每周三晚上七点开会")
        row = self.row(put["id"])
        self.assertIsNone(row[0])
        self.assertEqual(row[2], "none")

    def test_archive_mode_not_parsed(self):
        self.app = self.make_app(True)
        put = self.app._put_memory_source("明天下午三点开会",
                                          label="自动摘要", mode="auto_summary")
        self.assertIsNone(self.row(put["id"])[0])

    def test_flag_off_unchanged(self):
        self.app = self.make_app(False)
        put = self.app._put_memory_source("明天下午三点开会")
        self.assertIsNone(self.row(put["id"])[0])
        self.assertIsNone(put["event_meta"])

    def test_duplicate_no_double_insert(self):
        self.app = self.make_app(True)
        a = self.app._put_memory_source("后天上午十点体检")
        b = self.app._put_memory_source("后天上午十点体检")
        self.assertTrue(b["duplicate"])
        self.assertEqual(a["id"], b["id"])


if __name__ == "__main__":
    unittest.main()