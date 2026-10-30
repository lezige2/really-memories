# -*- coding: utf-8 -*-
"""CPU-only unit tests for tools/k2_family.py (K2 同族只留最新，零 GPU/零服务).

Run: python -X utf8 -m unittest discover -s tools -p "test_k2_family_cpu.py" -v
Exit: 0 all pass, 1 failure.
"""
import os
import sys
import sqlite3
import tempfile
import unittest
from datetime import date
from unittest import mock

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import k2_family as K  # noqa: E402
import chat_daily as D  # noqa: E402


def row(sid, name, text):
    """memory_source.block_rows() 形状：(id, name, label, text, hash, source_id, ...)."""
    return (int(sid), str(name), str(name), str(text), "h", 1, "/tmp/block", 8)


ROWS_PLATE = [
    row(3, "mem-3", "我叫阿泽，今天（2026-10-27）我们做完了 b7 实验，结论是擦边；"
                   "我的车牌号是京A88888。"),
    row(12, "mem-12", "我叫阿泽，我的车牌号是京A88888。"),
    row(13, "mem-13", "顺便说一下，我的车牌号是京A88888。"),
    row(22, "mem-22", "我的车牌号换成津E54321了"),
]


class ResolveTests(unittest.TestCase):
    def test_plate_new_wins_and_old_hidden(self):
        fam = K.resolve_family("我的车牌号是多少？", ROWS_PLATE)
        self.assertIsNotNone(fam)
        self.assertEqual(fam["family"], "车牌")
        self.assertEqual(fam["kept_id"], 22)
        self.assertEqual(sorted(fam["hidden_ids"]), [3, 12, 13])

    def test_plate_only_old_keeps_max(self):
        fam = K.resolve_family("我的车牌号是多少？", ROWS_PLATE[:3])
        self.assertEqual(fam["kept_id"], 13)
        self.assertEqual(fam["hidden_ids"], [3, 12])

    def test_work_vs_private_not_same_family(self):
        rows = [row(21, "mem-21", "我的工作号是130-2468-1111"),
                row(22, "mem-22", "我的私人号是131-0000-2222")]
        fam = K.resolve_family("我的工作号是多少？", rows)
        self.assertEqual(fam["kept_id"], 21)
        self.assertEqual(fam["hidden_ids"], [])       # 私人号不同主体，不得互隐

    def test_private_query_keeps_private(self):
        rows = [row(21, "mem-21", "我的工作号是130-2468-1111"),
                row(22, "mem-22", "我的私人号是131-0000-2222")]
        fam = K.resolve_family("我的私人号是多少？", rows)
        self.assertEqual(fam["kept_id"], 22)
        self.assertEqual(fam["hidden_ids"], [])       # 工作号不同主体，不互隐

    def test_two_cars_do_not_hide_each_other(self):
        rows = [row(21, "mem-21", "我的特斯拉是蓝色"),
                row(22, "mem-22", "我的比亚迪是黑色")]
        fam = K.resolve_family("我的特斯拉是什么颜色？", rows)
        self.assertEqual(fam["kept_id"], 21)
        self.assertEqual(fam["hidden_ids"], [])
        self.assertEqual(fam["owner"], "特斯拉")

    def test_meeting_different_days_not_same(self):
        rows = [row(21, "mem-21", "我下周五去杭州开会"),
                row(22, "mem-22", "改到下周一去成都开会")]
        fam = K.resolve_family("我下周一要去哪里开会？", rows)
        self.assertEqual(fam["kept_id"], 22)
        self.assertEqual(fam["hidden_ids"], [])

    def test_meeting_same_day_hides_old_place(self):
        rows = [row(21, "mem-21", "周一上午十点的会在7楼会议室"),
                row(22, "mem-22", "改到2楼会议室")]
        fam = K.resolve_family("周一上午十点的会在哪开？", rows)
        self.assertEqual(fam["kept_id"], 22)
        self.assertEqual(fam["hidden_ids"], [21])

    def test_meeting_without_date_falls_back(self):
        rows = [row(21, "mem-21", "周一上午十点的会在7楼会议室")]
        self.assertIsNone(K.resolve_family("我的会在哪里开？", rows))

    def test_recurring_meeting_not_merged_when_time_differs(self):
        rows = [row(1, "mem-1", "我每周三晚上七点有组会，地点在B座302；本周待办是交周报。"),
                row(21, "mem-21", "周三的会在三楼洽谈室"),
                row(22, "mem-22", "换到五楼大会议室")]
        fam = K.resolve_family("周三的会在哪里开？", rows)
        self.assertEqual(fam["kept_id"], 22)
        self.assertEqual(fam["hidden_ids"], [21])      # #1 是不同的会，保留

    def test_same_value_duplicates_still_hidden(self):
        rows = [row(12, "mem-12", "我叫阿泽，我的车牌号是京A88888。"),
                row(13, "mem-13", "顺便说一下，我的车牌号是京A88888。")]
        fam = K.resolve_family("我的车牌号是多少？", rows)
        self.assertEqual(fam["kept_id"], 13)
        self.assertEqual(fam["hidden_ids"], [12])

    def test_generic_query_includes_owned_rows(self):
        # "我的邮箱是什么" 无 owner：工作邮箱(22) 也算同族并胜出（KVC20 形状）
        rows = [row(21, "mem-21", "我的邮箱是lin@example.com"),
                row(22, "mem-22", "工作邮箱是lin.work@example.com")]
        fam = K.resolve_family("我的邮箱是什么？", rows)
        self.assertEqual(fam["kept_id"], 22)
        self.assertEqual(fam["hidden_ids"], [21])

    def test_unrecognized_new_fact_keeps_old_visible(self):
        # 已知局限：新事实无族键（"我换到美团了"）时 K2 不隐旧块（KVC12）
        rows = [row(21, "mem-21", "我的公司是字节跳动"),
                row(22, "mem-22", "我换到美团了")]
        fam = K.resolve_family("我的公司叫什么？", rows)
        self.assertEqual(fam["kept_id"], 21)
        self.assertEqual(fam["hidden_ids"], [])

    def test_miss_no_row_of_family(self):
        self.assertIsNone(K.resolve_family("我的猫叫什么？", ROWS_PLATE))

    def test_no_family_in_query(self):
        self.assertIsNone(K.resolve_family("我叫什么名字？", ROWS_PLATE))

    def test_empty_rows(self):
        self.assertIsNone(K.resolve_family("我的车牌号是多少？", []))
        self.assertIsNone(K.resolve_family("", ROWS_PLATE))


class SelectTests(unittest.TestCase):
    def test_select_shape(self):
        sel = K.select_k2(ROWS_PLATE, "我的车牌号是多少？", 4)
        self.assertEqual(len(sel), 1)
        hit = sel[0]
        self.assertEqual(set(hit), {"name", "score", "source_id", "signals"})
        self.assertEqual(hit["source_id"], 22)
        self.assertEqual(hit["score"], 9.0)
        self.assertEqual(sorted(hit["signals"]["hidden_ids"]), [3, 12, 13])
        self.assertTrue(hit["signals"]["k2"])

    def test_select_none_on_miss(self):
        self.assertIsNone(K.select_k2(ROWS_PLATE, "我叫什么名字？", 4))


class FallbackTests(unittest.TestCase):
    """B 要求：槽/键不明确时 select_k2 必须返回 None（上层走原逻辑）。"""

    def test_x03_meeting_without_slot(self):
        rows = [row(1, "mem-1", "我每周三晚上七点有组会，地点在B座302。"),
                row(2, "mem-2", "我每周三晚上七点有组会，地点B座302。")]
        self.assertIsNone(K.select_k2(rows, "在吗，我几点开会？", 4))
        self.assertIsNone(K.resolve_family("在吗，我几点开会？", rows))

    def test_l07_single_email_no_hiding(self):
        rows = [row(21, "mem-21", "我的邮箱是 lin@example.org")]
        self.assertIsNone(K.select_k2(rows, "我的邮箱是什么？", 4))

    def test_l09_single_card_no_hiding(self):
        rows = [row(21, "mem-21", "我的银行卡尾号是 7418")]
        self.assertIsNone(K.select_k2(rows, "我的银行卡尾号是多少？", 4))

    def test_bank_ambiguous_predicate_falls_back(self):
        rows = [row(21, "mem-21", "我的银行卡尾号是7418"),
                row(22, "mem-22", "尾号换成9032了")]
        # 只说"尾号"、未说银行卡 -> 谓词不明确
        self.assertIsNone(K.select_k2(rows, "我的尾号是多少？", 4))

    def test_email_conflict_still_filters(self):
        rows = [row(21, "mem-21", "我的邮箱是aze@example.com"),
                row(22, "mem-22", "邮箱改成aze.work@example.com")]
        sel = K.select_k2(rows, "我的邮箱是多少？", 4)
        self.assertIsNotNone(sel)
        self.assertEqual(sel[0]["source_id"], 22)
        self.assertEqual(sel[0]["signals"]["hidden_ids"], [21])

    def test_bank_conflict_still_filters(self):
        rows = [row(21, "mem-21", "我的银行卡尾号是7418"),
                row(22, "mem-22", "尾号换成9032了")]
        sel = K.select_k2(rows, "我的银行卡尾号是多少？", 4)
        self.assertIsNotNone(sel)
        self.assertEqual(sel[0]["source_id"], 22)
        self.assertEqual(sel[0]["signals"]["hidden_ids"], [21])

    def test_owner_ambiguity_falls_back(self):
        # 同族出现两个主体（个人/工作）且 query 无 owner -> 歧义，不筛
        rows = [row(21, "mem-21", "我的个人邮箱是p@example.com"),
                row(22, "mem-22", "工作邮箱是w@example.com")]
        self.assertIsNone(K.select_k2(rows, "我的邮箱是什么？", 4))

    def test_meeting_time_only_without_day_falls_back(self):
        rows = [row(21, "mem-21", "周三晚上七点的会在三楼洽谈室"),
                row(22, "mem-22", "换到五楼大会议室")]
        self.assertIsNone(K.select_k2(rows, "七点的会在哪里开？", 4))


class WireTests(unittest.TestCase):
    """开关接线：默认 off 时 select_k2 不得被调用；on 时过滤 hidden。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="k2_family_")
        cls.model = os.path.join(cls.tmp, "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, k2_family):
        return D.DailyApp(
            D.StubEngine(), db_path=os.path.join(self.tmp, "daily.db"),
            blocks_dir=os.path.join(self.tmp, "blocks"),
            sessions_dir=os.path.join(self.tmp, "sessions"),
            model_path=self.model, restore=False, retrieval_mode="topk",
            topk=4, k2_family=k2_family, logger=False)

    def test_default_off_in_constructor(self):
        app = self.make_app(None)
        self.assertFalse(app.k2_family)

    def test_off_does_not_call_select_k2(self):
        app = self.make_app(False)
        called = []
        base = [{"name": "n1", "score": 1.0, "source_id": 7, "signals": {}}]
        app._rows = lambda: ROWS_PLATE
        app._retrieval_select_normal = lambda text: base
        with mock.patch.object(D._k2f, "select_k2",
                               side_effect=lambda *a, **k: called.append(1)):
            out = app._retrieval_select("我的车牌号是多少？")
        self.assertEqual(called, [])
        self.assertEqual(out, base)

    def test_on_keeps_newest_and_filters_hidden(self):
        app = self.make_app(True)
        app._rows = lambda: ROWS_PLATE
        called = []
        app._retrieval_select_normal = lambda text: called.append(1) or []
        out = app._retrieval_select("我的车牌号是多少？")
        ids = [s["source_id"] for s in out]
        self.assertEqual(ids, [22])                   # 只挂 kept，同族旧块/跨族都不补
        self.assertEqual(called, [])                  # 命中后不再走普通 topk

    def test_on_miss_uses_original_logic(self):
        app = self.make_app(True)
        called = []
        base = [{"name": "n1", "score": 1.0, "source_id": 7, "signals": {}}]
        app._rows = lambda: []
        app._retrieval_select_normal = lambda text: base
        with mock.patch.object(D._k2f, "select_k2_ex",
                               side_effect=lambda *a, **k:
                               called.append(1) or {"hit": None, "reason": "no_family"}):
            out = app._retrieval_select("我的车牌号是多少？")
        self.assertEqual(called, [1])
        self.assertEqual(out, base)


class FillTests(unittest.TestCase):
    """B 定 fill 策略：同族可补、跨族不补；空结果回退。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="k2_fill_")
        cls.model = os.path.join(cls.tmp, "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self):
        return D.DailyApp(
            D.StubEngine(), db_path=os.path.join(self.tmp, "daily.db"),
            blocks_dir=os.path.join(self.tmp, "blocks"),
            sessions_dir=os.path.join(self.tmp, "sessions"),
            model_path=self.model, restore=False, retrieval_mode="topk",
            topk=4, k2_family=True, logger=False)

    def test_v9mt05_phone_query_does_not_mount_plates(self):
        # V9MT05 式：手机题只挂手机 kept，车牌不得跨族补进来
        rows = [row(21, "p21", "我的手机号是136-1111-3333"),
                row(22, "p22", "我的手机号是158-0000-2468"),
                row(3, "plate3", "我叫阿泽，我的车牌号是京A88888。"),
                row(12, "plate12", "我的车牌号是京A88888。")]
        app = self.make_app()
        app._rows = lambda: rows
        app._retrieval_select_normal = lambda text: [
            {"name": "plate3", "score": 1.0, "source_id": 3, "signals": {}}]
        out = app._retrieval_select("我的手机号是多少？")
        self.assertEqual([s["source_id"] for s in out], [22])
        self.assertNotIn(3, [s["source_id"] for s in out])
        self.assertNotIn(12, [s["source_id"] for s in out])

    def test_meeting_keeps_same_family_supplementary(self):
        # 会议+待办：同族但不同场（#1/#2 19:00）可留；同场旧值 #21 隐
        rows = [row(1, "m1", "我每周三晚上七点有组会，地点在B座302；本周待办是交周报。"),
                row(2, "m2", "我每周三晚上七点有组会，地点B座302。"),
                row(21, "old", "周三的会在三楼洽谈室"),
                row(22, "new", "换到五楼大会议室")]
        app = self.make_app()
        app._rows = lambda: rows
        app._retrieval_select_normal = lambda text: []
        out = app._retrieval_select("周三的会在哪里开？")
        self.assertEqual([s["source_id"] for s in out], [22, 1, 2])
        self.assertNotIn(21, [s["source_id"] for s in out])

    def test_two_cars_other_owner_not_hidden(self):
        rows = [row(21, "t", "我的特斯拉是蓝色"),
                row(22, "b", "我的比亚迪是黑色")]
        fam = K.resolve_family("我的特斯拉是什么颜色？", rows)
        self.assertEqual(fam["kept_id"], 21)
        self.assertEqual(fam["hidden_ids"], [])       # 不同主体不互隐

    def test_no_family_falls_back(self):
        app = self.make_app()
        base = [{"name": "x", "score": 1.0, "source_id": 1, "signals": {}}]
        app._rows = lambda: [row(1, "x", "随便一条记忆")]
        app._retrieval_select_normal = lambda text: base
        out = app._retrieval_select("我叫什么名字？")
        self.assertEqual(out, base)


class CounterTests(unittest.TestCase):
    """K2c：K2 分支不得压小共享计数；回退查询必须与 BASE 选择等价。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="k2_counter_")
        cls.model = os.path.join(cls.tmp, "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self):
        return D.DailyApp(
            D.StubEngine(), db_path=os.path.join(self.tmp, "daily.db"),
            blocks_dir=os.path.join(self.tmp, "blocks"),
            sessions_dir=os.path.join(self.tmp, "sessions"),
            model_path=self.model, restore=False, retrieval_mode="topk",
            topk=4, k2_family=True, logger=False)

    def test_hit_counters_use_library_size(self):
        app = self.make_app()
        app._rows = lambda: ROWS_PLATE
        called = []
        app._retrieval_select_normal = lambda text: called.append(1) or []
        app._retrieval_select("我的车牌号是多少？")
        self.assertEqual(called, [])                       # K2 分支不调普通 topk
        self.assertEqual(app._last_candidate_count, len(ROWS_PLATE))
        self.assertEqual(app._last_related_count, 0)

    def test_hit_never_shrinks_to_member_count(self):
        app = self.make_app()
        rows = [row(12, "p12", "我的车牌号是京A88888"),
                row(22, "p22", "我的车牌号换成津E54321了"),
                row(14, "cat", "我养的猫叫豆豆"),
                row(15, "dog", "我养的狗叫大黄")]
        app._rows = lambda: rows
        app._retrieval_select("我的车牌号是多少？")
        self.assertEqual(app._last_candidate_count, len(rows))   # 用库大小
        self.assertGreater(app._last_candidate_count, 2)         # 不是族内成员数

    def test_chat_daily_passes_times_map(self):
        # chat_daily 必须把 id->{created_at,mode} 传给 select_k2（时间戳 Phase 1）
        app = self.make_app()
        app._rows = lambda: []
        app._retrieval_select_normal = lambda text: []
        seen = {}
        with mock.patch.object(D._k2f, "select_k2_ex",
                               side_effect=lambda *a, **k:
                               seen.update(k) or {"hit": None, "reason": "no_family"}):
            app._retrieval_select("我的车牌号是多少？")
        self.assertIn("times", seen)
        self.assertIsInstance(seen["times"], dict)

    def test_fallback_queries_equal_base_selection(self):
        # x03 / L07 / L09 式查询：select_k2 回 None -> 选择与计数都与 BASE 等价
        app = self.make_app()
        cases = [
            ("在吗，我几点开会？",
             [row(1, "m1", "我每周三晚上七点有组会，地点在B座302。"),
              row(2, "m2", "我每周三晚上七点有组会，地点B座302。")]),
            ("我的邮箱是什么？", [row(21, "e21", "我的邮箱是 lin@example.org")]),
            ("我的银行卡尾号是多少？", [row(21, "c21", "我的银行卡尾号是 7418")]),
        ]
        for q, rows in cases:
            app._rows = (lambda rows=rows: rows)

            def fake_normal(text):
                app._last_candidate_count = 7
                app._last_related_count = 1
                return [{"name": "base", "score": 1.0, "source_id": 1,
                         "signals": {"hits": []}}]

            app._retrieval_select_normal = fake_normal
            out = app._retrieval_select(q)
            self.assertEqual(out, [{"name": "base", "score": 1.0, "source_id": 1,
                                    "signals": {"hits": []}}], q)
            self.assertEqual(app._last_candidate_count, 7, q)
            self.assertEqual(app._last_related_count, 1, q)


class TimeTests(unittest.TestCase):
    """时间戳 Phase 1：created_at 排序 + 一次性 meeting/travel 过期。"""

    TODAY = date(2026, 10, 29)

    def test_periodic_not_expired(self):
        rows = [row(5, "m5", "我每周三晚上七点有组会，地点B座302。"),
                row(9, "m9", "周三的会在三楼洽谈室。")]
        times = {5: {"created_at": "2020-01-01", "mode": "chat"},
                 9: {"created_at": "2021-01-01", "mode": "chat"}}
        sel = K.select_k2(rows, "周三晚上七点的会在哪里开？", 4,
                          times=times, today=self.TODAY)
        self.assertIsNotNone(sel)
        self.assertEqual(sel[0]["source_id"], 5)          # 周期性事实不过期
        self.assertIn(9, sel[0]["signals"]["expired_ids"])
        self.assertIn(9, sel[0]["signals"]["hidden_ids"])

    def test_one_off_expired_hidden(self):
        rows = [row(21, "m21", "我下周三要去北京出差"),
                row(22, "m22", "我下周三要去上海出差")]
        times = {21: {"created_at": "2026-10-01", "mode": "chat"},
                 22: {"created_at": "2026-10-28", "mode": "chat"}}
        sel = K.select_k2(rows, "我下周三要去哪里出差？", 4,
                          times=times, today=self.TODAY)
        self.assertIsNotNone(sel)
        self.assertEqual(sel[0]["source_id"], 22)
        self.assertEqual(sel[0]["signals"]["expired_ids"], [21])
        self.assertEqual(sorted(sel[0]["signals"]["hidden_ids"]), [21])

    def test_archive_blocks_not_date_parsed(self):
        rows = [row(9, "m9", "明天开会"),
                row(5, "m5", "下周三开会在三楼洽谈室。")]
        times = {9: {"created_at": "2026-10-20", "mode": "auto_archive"},
                 5: {"created_at": "2026-10-27", "mode": "chat"}}
        sel = K.select_k2(rows, "下周三的会在哪里开？", 4,
                          times=times, today=self.TODAY)
        self.assertIsNotNone(sel)
        self.assertEqual(sel[0]["source_id"], 5)
        self.assertEqual(sel[0]["signals"]["expired_ids"], [])   # 归档不解析"明天"

    def test_created_at_order_beats_id(self):
        rows = [row(10, "m10", "下周三开会在三楼"),
                row(20, "m20", "下周三开会在五楼")]
        times = {10: {"created_at": "2026-10-28", "mode": "chat"},
                 20: {"created_at": "2026-10-27", "mode": "chat"}}
        sel = K.select_k2(rows, "下周三的会在哪里开？", 4,
                          times=times, today=self.TODAY)
        self.assertEqual(sel[0]["source_id"], 10)         # created_at 优先于 id
        self.assertEqual(sel[0]["signals"]["hidden_ids"], [20])

    def test_without_times_falls_back_to_id(self):
        rows = [row(10, "m10", "下周三开会在三楼"),
                row(20, "m20", "下周三开会在五楼")]
        sel = K.select_k2(rows, "下周三的会在哪里开？", 4, today=self.TODAY)
        self.assertEqual(sel[0]["source_id"], 20)         # 无 times -> id DESC
        self.assertEqual(sel[0]["signals"]["hidden_ids"], [10])


class AutoGateTests(unittest.TestCase):
    """K2 auto：owner 门控 + count 兜底 + k2_mode/gate_reason 记录。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="k2_auto_")
        cls.model = os.path.join(cls.tmp, "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, k2=True):
        return D.DailyApp(
            D.StubEngine(), db_path=os.path.join(self.tmp, "daily.db"),
            blocks_dir=os.path.join(self.tmp, "blocks"),
            sessions_dir=os.path.join(self.tmp, "sessions"),
            model_path=self.model, restore=False, retrieval_mode="topk",
            topk=4, k2_family=k2, logger=False)

    def test_owner_known_runs_k2(self):
        rows = [row(21, "p21", "张伟的手机号是136-1111-3333"),
                row(22, "p22", "张伟的手机号是158-0000-2468")]
        ex = K.select_k2_ex(rows, "张伟的手机号是多少？", 4)
        self.assertEqual(ex["reason"], "ok")
        self.assertEqual(ex["hit"][0]["source_id"], 22)

    def test_self_single_entity_runs_k2(self):
        # 族内单实体（全是 self）：我的猫 -> ok，不因“无显式 owner”回退
        rows = [row(21, "c21", "我养的猫叫豆豆"),
                row(22, "c22", "我的猫叫球球")]
        ex = K.select_k2_ex(rows, "我的猫叫什么名字？", 4)
        self.assertEqual(ex["reason"], "ok")
        self.assertEqual(ex["hit"][0]["source_id"], 22)

    def test_self_two_cars_owner_missing(self):
        rows = [row(21, "t", "我的特斯拉是蓝色"),
                row(22, "b", "我的比亚迪是黑色")]
        ex = K.select_k2_ex(rows, "我的车是什么颜色？", 4)
        self.assertIsNone(ex["hit"])
        self.assertEqual(ex["reason"], "owner_missing")

    def test_self_two_numbers_owner_missing(self):
        rows = [row(21, "w", "我的工作号是130-2468-1111"),
                row(22, "p", "我的私人号是131-0000-2222")]
        ex = K.select_k2_ex(rows, "我的手机号是多少？", 4)
        self.assertIsNone(ex["hit"])
        self.assertEqual(ex["reason"], "owner_missing")

    def test_no_family_stays_no_family(self):
        rows = [row(21, "f1", "我最爱吃湘菜"),
                row(22, "f2", "我最爱吃粤菜")]
        ex = K.select_k2_ex(rows, "我爱吃什么？", 4)
        self.assertIsNone(ex["hit"])
        self.assertEqual(ex["reason"], "no_family")

    def test_owner_missing_multi_subject_falls_back(self):
        rows = [row(21, "p21", "张伟的手机号是136-1111-3333"),
                row(22, "p22", "刘敏的手机号是158-0000-2468")]
        ex = K.select_k2_ex(rows, "我的手机号是多少？", 4)
        self.assertIsNone(ex["hit"])
        self.assertEqual(ex["reason"], "owner_missing")

    def test_count_guard_over_50_falls_back(self):
        rows = [row(i, "p%d" % i, "我的手机号是136-1111-3333") for i in range(1, 52)]
        ex = K.select_k2_ex(rows, "我的手机号是多少？", 4)
        self.assertIsNone(ex["hit"])
        self.assertEqual(ex["reason"], "count")

    def test_under_50_with_owner_runs_k2(self):
        rows = [row(21, "p21", "张伟的手机号是136-1111-3333"),
                row(22, "p22", "张伟的手机号是158-0000-2468")]
        ex = K.select_k2_ex(rows, "张伟的手机号是多少？", 4)
        self.assertEqual(ex["reason"], "ok")
        self.assertLessEqual(len(rows), K.K2_MAX_ROWS)

    def test_app_records_k2_mode_and_gate_reason(self):
        app = self.make_app(True)
        rows = [row(21, "p21", "张伟的手机号是136-1111-3333"),
                row(22, "p22", "张伟的手机号是158-0000-2468")]
        app._rows = lambda: rows
        app._retrieval_select("张伟的手机号是多少？")
        self.assertEqual(app._last_k2["mode"], "auto_on")
        self.assertEqual(app._last_k2["gate_reason"], "ok")
        # health 暴露当前档位
        h = app.health()
        self.assertEqual(h["retrieval"]["k2"]["mode"], "auto_on")
        self.assertEqual(h["retrieval"]["k2"]["gate_reason"], "ok")

    def test_flag_off_unchanged(self):
        app = self.make_app(False)
        app._rows = lambda: [row(21, "p21", "张伟的手机号是136-1111-3333")]
        base = [{"name": "x", "score": 1.0, "source_id": 1, "signals": {}}]
        app._retrieval_select_normal = lambda text: base
        self.assertEqual(app._retrieval_select("张伟的手机号是多少？"), base)
        self.assertEqual(app._last_k2["mode"], "auto_off")
        self.assertEqual(app._last_k2["gate_reason"], "off")
        self.assertEqual(app.health()["retrieval"]["k2"]["mode"], "auto_off")


class TriggerTests(unittest.TestCase):
    """created_at 不可回写（只防未来；历史快照由 A 负责）。"""

    def test_created_at_update_aborts(self):
        import memory_source as ms
        con = sqlite3.connect(":memory:")
        try:
            con.executescript(ms.SCHEMA)
            con.execute(
                "INSERT INTO memory_source (name,label,text,source_hash,created_at) "
                "VALUES ('n','l','t','h','2026-10-29T10:00:00')")
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute(
                    "UPDATE memory_source SET created_at='2020-01-01' WHERE name='n'")
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()