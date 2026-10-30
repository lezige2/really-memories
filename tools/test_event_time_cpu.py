# -*- coding: utf-8 -*-
"""CPU tests for tools/event_time.py (P0 event_date) + migration helpers.

Run: python -X utf8 -m unittest discover -s tools -p "test_event_time_cpu.py" -v
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import event_time as E  # noqa: E402
import memory_source as ms  # noqa: E402

WED = "2026-10-28T10:00:00"      # v1_local_naive：本地 2026-10-28 10:00（周三）
THU = "2026-10-29T10:00:00"
FRI = "2026-10-30T10:00:00"
NEWYEAR = "2026-12-31T10:00:00"


def p(text, ts, **kw):
    return E.parse_event_time(text, ts, **kw)


class SemanticsTests(unittest.TestCase):
    def test_next_week_iso(self):
        r = p("下周三开会", WED)
        self.assertEqual(r["event_date"], date(2026, 11, 4))
        self.assertEqual(r["event_confidence"], "high")
        self.assertEqual(r["event_parser_version"], E.EVENT_PARSER_VERSION)

    def test_next_week_same_weekday_plus7(self):
        self.assertEqual(p("下周三", WED)["event_date"], date(2026, 11, 4))

    def test_this_week_past_ambiguous(self):
        r = p("这周三", THU)             # 周四问本周三 -> 已过
        self.assertIsNone(r["event_date"])
        self.assertEqual(r["event_confidence"], "ambiguous")

    def test_this_week_today_ok(self):
        r = p("这周三", WED)
        self.assertEqual(r["event_date"], date(2026, 10, 28))
        self.assertEqual(r["event_confidence"], "high")

    def test_bare_friday(self):
        self.assertEqual(p("周五", FRI)["event_date"], date(2026, 11, 6))   # 今天周五 -> +7
        self.assertEqual(p("周五", WED)["event_date"], date(2026, 10, 30))  # 周三 -> 本周五

    def test_next_month_rollover(self):
        self.assertEqual(p("下个月5号交材料", NEWYEAR)["event_date"], date(2027, 1, 5))

    def test_month_end(self):
        self.assertEqual(p("月底前交", "2026-10-31T10:00:00")["event_date"],
                         date(2026, 10, 31))
        self.assertEqual(p("月底前交", "2026-11-01T10:00:00")["event_date"],
                         date(2026, 11, 30))
        self.assertEqual(p("下个月31号", "2026-01-15T10:00:00")["event_confidence"],
                         "ambiguous")   # 2 月没有 31 号

    def test_local_naive_no_tz_conversion(self):
        # v1_local_naive：解析器不做时区转换；20:00 写“明天”= 次日（不跨天偏差）
        r = p("明天", "2026-10-27T20:00:10")
        self.assertEqual(r["event_date"], date(2026, 10, 28))
        self.assertEqual(r["event_basis_ts"], "2026-10-27T20:00:10")
        self.assertEqual(r["event_tz"], "Asia/Shanghai")
        self.assertEqual(r["created_at_semantics"], "v1_local_naive")
        # 22:00 也不因时区换算错天
        self.assertEqual(p("明天", "2026-10-27T22:00:00")["event_date"],
                         date(2026, 10, 28))
        # 22:00 的本地时间也不能跨天
        self.assertEqual(p("明天", "2026-10-27T22:00:00")["event_date"],
                         date(2026, 10, 28))

    def test_midnight_boundaries(self):
        r = p("明天晚上12点", WED)
        self.assertEqual(r["event_date"], date(2026, 10, 30))   # 次日 00:00
        self.assertEqual(r["event_time"], "00:00")
        r2 = p("明天凌晨2点", WED)
        self.assertEqual(r2["event_date"], date(2026, 10, 29))
        self.assertEqual(r2["event_time"], "02:00")
        self.assertEqual(p("睡觉", WED)["event_confidence"], "none")

    def test_bare_weekday_with_time_is_today(self):
        # E05：裸周三 + 明确时刻，今天周三 -> 当天
        r = p("周三晚上七点组会", WED)
        self.assertEqual(r["event_date"], date(2026, 10, 28))
        self.assertEqual(r["event_time"], "19:00")
        # E21：裸周五 + “下班前”，今天周五 -> 当天
        self.assertEqual(p("周五下班前", FRI)["event_date"], date(2026, 10, 30))
        # 无时刻的裸周五今天周五 -> +7（E38）
        self.assertEqual(p("周五", FRI)["event_date"], date(2026, 11, 6))

    def test_tonight_week_only_and_midnight(self):
        # E10 今晚八点 -> 当天 20:00
        r = p("今晚八点", WED)
        self.assertEqual(r["event_date"], date(2026, 10, 28))
        self.assertEqual(r["event_time"], "20:00")
        # E17 下周（无星期）-> ambiguous
        r2 = p("下周见", THU)
        self.assertIsNone(r2["event_date"])
        self.assertEqual(r2["event_confidence"], "ambiguous")
        # E25 半夜12点 -> 次日 00:00
        r3 = p("半夜12点", FRI)
        self.assertEqual(r3["event_date"], date(2026, 10, 31))
        self.assertEqual(r3["event_time"], "00:00")

    def test_periodic_and_archive(self):
        r = p("每周三晚上七点开会", WED)
        self.assertTrue(r["periodic"])
        self.assertIsNone(r["event_date"])
        r2 = p("明天开会", WED, allow_parse=False)
        self.assertEqual(r2["event_confidence"], "none")
        self.assertIsNone(r2["event_date"])


class RetrievalSideTests(unittest.TestCase):
    def test_time_query_lexicon(self):
        self.assertTrue(E.is_time_query("我下周三要去哪开会？"))
        self.assertTrue(E.is_time_query("这个什么时候到期"))
        self.assertFalse(E.is_time_query("我叫什么名字"))

    def test_expiry_today_not_expired(self):
        today = date(2026, 10, 30)
        self.assertFalse(E.is_expired(date(2026, 10, 30), today))
        self.assertTrue(E.is_expired(date(2026, 10, 29), today))
        self.assertFalse(E.is_expired(None, today))

    def test_filter_expired(self):
        today = date(2026, 10, 30)
        rows = [
            {"id": 1, "text": "明天开会", "event_date": "2026-10-29",
             "event_confidence": "high", "mode": "chat", "periodic": False},
            {"id": 2, "text": "每周三开会", "event_date": None,
             "event_confidence": "none", "mode": "chat", "periodic": True},
            {"id": 3, "text": "明天开会", "event_date": "2026-10-30",
             "event_confidence": "high", "mode": "chat", "periodic": False},
        ]
        kept = E.filter_expired(rows, "我明天几点开会？", today)
        self.assertEqual([r["id"] for r in kept], [2, 3])       # 当天不过期；periodic 豁免
        self.assertEqual(len(E.filter_expired(rows, "我叫什么名字", today)), 3)


class MigrationTests(unittest.TestCase):
    def _old_db(self, path):
        con = sqlite3.connect(path)
        con.executescript(ms.SCHEMA)
        for name, _t in ms.EVENT_COLUMNS:                        # 模拟旧库
            try:
                con.execute("ALTER TABLE memory_source DROP COLUMN %s" % name)
            except sqlite3.OperationalError:
                pass
        con.commit()
        return con

    def test_ensure_backup_add_and_drop(self):
        tmp = tempfile.mkdtemp(prefix="event_mig_")
        path = os.path.join(tmp, "old.db")
        con = self._old_db(path)
        try:
            self.assertNotIn("event_date", ms.event_column_names(con))
            info = ms.ensure_event_columns(con, db_path=path)
            self.assertIn("event_date", info["added"])
            self.assertTrue(os.path.exists(info["backup"]))
            self.assertEqual(len(info["sha256"]), 64)
            sid, created = ms.put_source(
                con, "m1", "l", "明天开会", tenant="default", scope="private",
                event_meta={"event_date": "2026-10-31", "event_time": None,
                            "event_source": "明天", "event_tz": "Asia/Shanghai",
                            "event_confidence": "high",
                            "event_parser_version": E.EVENT_PARSER_VERSION})
            self.assertTrue(created)
            row = con.execute("SELECT event_date,event_confidence FROM memory_source "
                              "WHERE id=?", (sid,)).fetchone()
            self.assertEqual(row, ("2026-10-31", "high"))
            dropped = ms.drop_event_columns(con)
            self.assertIn("event_date", dropped)
            self.assertNotIn("event_date", ms.event_column_names(con))
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()