# -*- coding: utf-8 -*-
"""S2 诊断：S2_GATE_OFF=1 时 retrieve 不走 coverage 闸；默认逐字不变。"""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import memory_service as memo  # noqa: E402
import chat_daily as D  # noqa: E402


def row(i, text):
    return (i, "m%d" % i, "l", text, "h", 1, "p", 1)


class GateBypassTests(unittest.TestCase):
    def test_off_unchanged_gate_empty(self):
        rows = [row(1, "甲乙")]
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(memo.retrieve("甲乙丙丁戊己庚辛", rows, topk=20), [])

    def test_on_returns_candidates(self):
        rows = [row(i, "甲乙") for i in range(1, 26)]
        with mock.patch.dict(os.environ, {"S2_GATE_OFF": "1"}):
            hits, stats = memo.retrieve("甲乙丙丁戊己庚辛", rows, topk=20,
                                        return_stats=True)
        self.assertEqual(len(hits), 20)
        self.assertEqual(stats["gate"], "bypassed")

    def test_on_top4(self):
        rows = [row(i, "甲乙") for i in range(1, 6)]
        with mock.patch.dict(os.environ, {"S2_GATE_OFF": "1"}):
            self.assertEqual(len(memo.retrieve("甲乙丙丁戊己庚辛", rows, topk=4)), 4)

    def test_chat_daily_topk_cap(self):
        tmp = tempfile.mkdtemp(prefix="gate_")
        model = os.path.join(tmp, "model.stub")
        D.install_fake_model(model)
        base = dict(db_path=os.path.join(tmp, "d.db"),
                    blocks_dir=os.path.join(tmp, "b"),
                    sessions_dir=os.path.join(tmp, "s"),
                    model_path=model, restore=False, retrieval_mode="topk",
                    logger=False)
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(D.DailyApp(D.StubEngine(), topk=20, **base).topk, 6)
        with mock.patch.dict(os.environ, {"S2_GATE_OFF": "1"}):
            self.assertEqual(D.DailyApp(D.StubEngine(), topk=20, **base).topk, 20)


if __name__ == "__main__":
    unittest.main()


class MountLimitTests(unittest.TestCase):
    """S1：挂载数 >6 必须快速失败（400 too_many_blocks），不进原生。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mount_")
        model = os.path.join(cls.tmp, "model.stub")
        D.install_fake_model(model)
        cls.app = D.DailyApp(D.StubEngine(), db_path=os.path.join(cls.tmp, "d.db"),
                             blocks_dir=os.path.join(cls.tmp, "b"),
                             sessions_dir=os.path.join(cls.tmp, "s"),
                             model_path=model, restore=False,
                             retrieval_mode="topk", topk=20, logger=False)

    def test_five_six_ok(self):
        for n in (5, 6):
            self.app._assert_mount_limit(n)          # 不抛

    def test_seven_fast_fail(self):
        with self.assertRaises(D.DailyError) as ctx:
            self.app._assert_mount_limit(7)
        err = ctx.exception
        self.assertEqual(err.code, "too_many_blocks")
        self.assertIn("blocks=7", err.message)
        self.assertIn("limit=6", err.message)

    def test_sync_mounts_blocks_before_native(self):
        rows = [(i, "m%d" % i, "l", "t", "h", 1, "p", 8) for i in range(1, 8)]
        self.app._rows_for_selection = lambda sel: rows
        self.app._fit_budget = lambda rs: (rs, None)
        self.app._last_selection = [{"source_id": i, "name": "m%d" % i} for i in range(1, 8)]
        self.app.retrieval_mode = "topk"
        self.app.control = False
        with self.assertRaises(D.DailyError) as ctx:
            self.app._sync_mounts()
        self.assertEqual(ctx.exception.code, "too_many_blocks")
