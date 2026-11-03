# -*- coding: utf-8 -*-
"""meta-v1 计数回答：仅命中问句、直查库、不调模型、口径 tenant+scope。"""
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
import p1b_subject as P  # noqa: E402


class MetaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="ma_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, flag, side_dir=None):
        tmp = tempfile.mkdtemp(prefix="ma_%s_" % self.id())
        if side_dir:
            os.environ["P1B_SIDECAR_DIR"] = side_dir
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                          blocks_dir=os.path.join(tmp, "b"),
                          sessions_dir=os.path.join(tmp, "s"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4, logger=False,
                          meta_answer=flag)

    def test_patterns_answer_without_model(self):
        app = self.make_app(True)
        app.remember("我叫阿泽")
        before = app.eng.ask_calls
        for q in ("我有几条记忆？", "我记了多少条记忆？",
                  "记忆条数是多少", "有多少条记忆"):
            res = app.ask(q)
            self.assertEqual(res["state"], "meta_answer", q)
            self.assertIn("记忆", res["answer"])
            self.assertIn("条", res["answer"])
            self.assertEqual(res["block_ids"], [])
        self.assertEqual(app.eng.ask_calls, before)       # 未调模型

    def test_non_pattern_goes_model(self):
        app = self.make_app(True)
        app._ask_natural = lambda t, t0: {"answer": "正常回答", "block_ids": []}
        with mock.patch.object(D, "NATURAL_MODE", True):
            res = app.ask("我的车牌号是多少？")
        self.assertEqual(res["answer"], "正常回答")

    def test_flag_off_original_path(self):
        app = self.make_app(False)
        app._ask_natural = lambda t, t0: {"answer": "正常回答", "block_ids": []}
        with mock.patch.object(D, "NATURAL_MODE", True):
            res = app.ask("我有几条记忆？")
        self.assertEqual(res["answer"], "正常回答")

    def test_default_on(self):
        tmp = tempfile.mkdtemp(prefix="ma_def_")
        app = D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                         blocks_dir=os.path.join(tmp, "b"),
                         sessions_dir=os.path.join(tmp, "s"),
                         model_path=self.model, restore=False,
                         retrieval_mode="topk", topk=4, logger=False)
        self.assertTrue(app.meta_answer)

    def test_zero_count_answer(self):
        app = self.make_app(True)
        res = app.ask("我有几条记忆？")
        self.assertEqual(res["state"], "meta_answer")
        self.assertEqual(res["answer"], "你还没有保存任何记忆。")

    def test_db_error_falls_back(self):
        app = self.make_app(True)
        app._ask_natural = lambda t, t0: {"answer": "回退模型", "block_ids": []}
        with mock.patch.object(app, "_count_valid_memories",
                               side_effect=RuntimeError("db down")):
            with mock.patch.object(D, "NATURAL_MODE", True):
                res = app.ask("我有几条记忆？")
        self.assertEqual(res["answer"], "回退模型")      # 不 500

    def test_logs_meta_answer(self):
        app = self.make_app(True)
        calls = []
        app.logger = mock.Mock()
        app.logger.log_warning = lambda *a, **k: calls.append((a, k))
        app.ask("我有几条记忆？")
        self.assertTrue(calls)
        ev = calls[-1][1].get("evidence") or {}
        for k in ("query", "tenant", "scope", "count", "latency_ms"):
            self.assertIn(k, ev, k)

    def test_count_scope_and_supersede_archive(self):
        side_dir = tempfile.mkdtemp(prefix="side_")
        app = self.make_app(True, side_dir=side_dir)
        ids = [app.remember(t)["id"] for t in
               ("我的猫叫豆豆", "我的猫叫球球", "我的猫叫圆圆")]
        self.assertEqual(app._count_valid_memories(), 3)
        self.assertEqual(app._count_valid_memories(tenant="other"), 0)  # scope 限定
        # supersede 一个
        path = P.sidecar_path(app.db_path)
        side = P.Sidecar(path).rebuild(app._rows())
        side.data["entries"][str(ids[0])]["superseded_by"] = ids[1]
        side.save()
        self.assertEqual(app._count_valid_memories(), 2)
        # archive 一个
        arch = os.path.join(os.path.dirname(path),
                            "%s.archive.json" % os.path.basename(path).split(".")[0])
        json.dump({"entries": [{"id": ids[2], "is_archived": True}]},
                  open(arch, "w", encoding="utf-8"))
        self.assertEqual(app._count_valid_memories(), 1)


if __name__ == "__main__":
    unittest.main()
