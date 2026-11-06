# -*- coding: utf-8 -*-
"""属性最新值 POC：手机/健身新胜旧；多实体/无属性/换牌不过滤。"""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import attribute_recency as A  # noqa: E402
import chat_daily as D  # noqa: E402


def meta(rows):
    return {i: {"created_at": t, "text": x} for i, t, x in rows}


def sel(ids):
    return [{"source_id": i, "name": "m%d" % i, "score": 1.0} for i in ids]


class RuleTests(unittest.TestCase):
    def test_phone_new_wins(self):
        d = A.apply_filter("我的手机号是多少？", sel([1, 2]), meta([
            (1, "2026-01-01T00:00:00", "我的手机号是139-0000-1111"),
            (2, "2026-02-01T00:00:00", "我的手机号是138-0000-2222")]))
        self.assertTrue(d["applied"])
        self.assertEqual(d["kept"], [2])
        self.assertEqual(d["hidden"], [1])

    def test_fitness_new_wins(self):
        d = A.apply_filter("我几点健身？", sel([1, 2]), meta([
            (1, "2026-01-01T00:00:00", "我周一早上七点健身"),
            (2, "2026-02-01T00:00:00", "我周三晚上八点健身")]))
        self.assertTrue(d["applied"])
        self.assertEqual(d["kept"], [2])
        self.assertEqual(d["hidden"], [1])

    def test_unrelated_block_preserved(self):
        d = A.apply_filter("我的手机号是多少？", sel([1, 2, 3]), meta([
            (1, "2026-01-01T00:00:00", "我的手机号是139-0000-1111"),
            (2, "2026-02-01T00:00:00", "我的手机号是138-0000-2222"),
            (3, "2026-01-15T00:00:00", "今天天气不错，出去走走")]))
        self.assertTrue(d["applied"])
        self.assertEqual(d["kept"], [2, 3])            # 无关块保留
        self.assertEqual(d["hidden"], [1])

    def test_single_valued_block_not_filtered(self):
        d = A.apply_filter("我的手机号是多少？", sel([1, 2]), meta([
            (1, "2026-01-01T00:00:00", "我的手机号是13900001111"),
            (2, "2026-01-15T00:00:00", "今天天气不错")]))
        self.assertFalse(d["applied"])
        self.assertEqual(d["reason"], "value_missing")

    def test_multi_entity_not_filtered(self):
        d = A.apply_filter("我的手机号是多少？", sel([1, 2]), meta([
            (1, "2026-01-01T00:00:00", "我的手机号是13900001111"),
            (2, "2026-02-01T00:00:00", "我还有一只手机号是13800002222")]))
        self.assertFalse(d["applied"])
        self.assertEqual(d["reason"], "multi_entity")

    def test_t003_not_filtered(self):
        d = A.apply_filter("我的车牌是多少？", sel([1, 2]), meta([
            (1, "2026-01-01T00:00:00", "牌子换成苏E8L2M6了"),
            (2, "2026-02-01T00:00:00", "又添了辆车，牌是苏E8L2M6")]))
        self.assertFalse(d["applied"])
        self.assertEqual(d["reason"], "no_attribute")

    def test_no_attribute(self):
        self.assertFalse(A.apply_filter("今天天气如何", sel([1]), {})["applied"])


class RerankTests(unittest.TestCase):
    def test_phone_rerank_new_first_all_kept(self):
        m = meta([(1, "2026-01-01T00:00:00", "我的手机号是139-0000-1111"),
                  (2, "2026-02-01T00:00:00", "我的手机号是138-0000-2222")])
        d = A.apply_rerank("我的手机号是多少？", sel([1, 2]), m)
        self.assertTrue(d["applied"])
        self.assertEqual(d["order"], [2, 1])
        self.assertEqual(sorted(d["order"]), [1, 2])   # 不隐藏

    def test_fitness_rerank(self):
        m = meta([(1, "2026-01-01T00:00:00", "我周一早上七点健身"),
                  (2, "2026-02-01T00:00:00", "我周三晚上八点健身")])
        d = A.apply_rerank("我几点健身？", sel([1, 2]), m)
        self.assertTrue(d["applied"])
        self.assertEqual(d["order"], [2, 1])

    def test_unvalued_block_last_stable(self):
        m = meta([(1, "2026-01-01T00:00:00", "我的手机号是13900001111"),
                  (2, "2026-02-01T00:00:00", "我的手机号是13800002222"),
                  (3, "2026-01-15T00:00:00", "今天天气不错")])
        d = A.apply_rerank("我的手机号是多少？", sel([3, 1, 2]), m)
        self.assertEqual(d["order"], [2, 1, 3])        # 无值块随后

    def test_multi_entity_no_rerank(self):
        m = meta([(1, "2026-01-01T00:00:00", "我的手机号是13900001111"),
                  (2, "2026-02-01T00:00:00", "我还有一只手机号是13800002222")])
        d = A.apply_rerank("我的手机号是多少？", sel([1, 2]), m)
        self.assertFalse(d["applied"])
        self.assertEqual(d["reason"], "multi_entity")

    def test_one_valued_no_rerank(self):
        m = meta([(1, "2026-01-01T00:00:00", "我的手机号是13900001111"),
                  (2, "2026-01-15T00:00:00", "今天天气不错")])
        d = A.apply_rerank("我的手机号是多少？", sel([1, 2]), m)
        self.assertFalse(d["applied"])


class DirectTests(unittest.TestCase):
    def test_phone_latest_exact_bytes(self):
        rows = [{"id": 1, "text": "我的手机号是139-0000-1111",
                 "created_at": "2026-01-01T00:00:00"},
                {"id": 2, "text": "我的手机号是138-0000-2222",
                 "created_at": "2026-02-01T00:00:00"}]
        d = A.direct_answer("我的手机号是多少？", rows)
        self.assertTrue(d["applied"])
        self.assertEqual(d["value"], "138-0000-2222")   # 逐字节原文
        self.assertEqual(d["block_id"], 2)

    def test_fitness_latest(self):
        rows = [{"id": 1, "text": "我周一早上七点健身",
                 "created_at": "2026-01-01T00:00:00"},
                {"id": 2, "text": "我周三晚上八点健身",
                 "created_at": "2026-02-01T00:00:00"}]
        d = A.direct_answer("我几点健身？", rows)
        self.assertTrue(d["applied"])
        self.assertEqual(d["block_id"], 2)
        self.assertIn("周三", d["value"])

    def test_multi_entity_fallback(self):
        rows = [{"id": 1, "text": "我的手机号是13900001111",
                 "created_at": "2026-01-01T00:00:00"},
                {"id": 2, "text": "我还有一只手机号是13800002222",
                 "created_at": "2026-02-01T00:00:00"}]
        self.assertFalse(A.direct_answer("我的手机号是多少？", rows)["applied"])

    def test_negation_fallback(self):
        rows = [{"id": 1, "text": "我的手机号是13900001111",
                 "created_at": "2026-01-01T00:00:00"},
                {"id": 2, "text": "那个号码算了，不是这个",
                 "created_at": "2026-02-01T00:00:00"}]
        d = A.direct_answer("我的手机号是多少？", rows)
        self.assertFalse(d["applied"])
        self.assertEqual(d["reason"], "negation_in_latest")

    def test_same_second_id_tiebreak(self):
        rows = [{"id": 1, "text": "我的手机号是13900001111",
                 "created_at": "2026-02-01T00:00:00"},
                {"id": 2, "text": "我的手机号是13800002222",
                 "created_at": "2026-02-01T00:00:00"}]
        d = A.direct_answer("我的手机号是多少？", rows)
        self.assertTrue(d["applied"])
        self.assertEqual(d["block_id"], 2)
        self.assertEqual(d["reason"], "latest_same_second")

    def test_fitness_full_values(self):
        rows = [{"id": 1, "text": "我周二晚上七点四十健身",
                 "created_at": "2026-02-01T00:00:00"}]
        d = A.direct_answer("我几点健身？", rows)
        self.assertTrue(d["applied"])
        self.assertIn("七点四十", d["value"])
        rows2 = [{"id": 1, "text": "我周二晚上九点半健身",
                  "created_at": "2026-02-01T00:00:00"}]
        self.assertIn("九点半", A.direct_answer("我几点健身？", rows2)["value"])
        rows3 = [{"id": 1, "text": "我周二早上七点健身",
                  "created_at": "2026-02-01T00:00:00"}]
        self.assertIn("七点", A.direct_answer("我几点健身？", rows3)["value"])


class WireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="ar_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, flag):
        tmp = tempfile.mkdtemp(prefix="ar_%s_" % self.id())
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                          blocks_dir=os.path.join(tmp, "b"),
                          sessions_dir=os.path.join(tmp, "s"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4, logger=False,
                          attribute_recency=flag)

    def test_flag_off_no_field(self):
        app = self.make_app(False)
        with mock.patch.object(D, "NATURAL_MODE", True):
            app._ask_natural = lambda t, t0: {"answer": "x", "block_ids": []}
            res = app.ask("我的手机号是多少")
        self.assertNotIn("attribute_recency", res)

    def test_slot_direct_off(self):
        app = self.make_app(False)
        with mock.patch.object(D, "NATURAL_MODE", True):
            app._ask_natural = lambda t, t0: {"answer": "模型答案", "block_ids": []}
            res = app.ask("我的手机号是多少")
        self.assertNotEqual(res.get("state"), "slot_direct")
        self.assertNotIn("slot_direct", res)

    def test_slot_direct_audit_and_access(self):
        import json as _json
        import time as _t
        tmp = tempfile.mkdtemp(prefix="sd_aud_")
        model = os.path.join(tmp, "model.stub")
        D.install_fake_model(model)
        adir = os.path.join(tmp, "audit")
        os.environ["LLAMA_AUDIT_DIR"] = adir
        app = D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                         blocks_dir=os.path.join(tmp, "b"),
                         sessions_dir=os.path.join(tmp, "s"),
                         model_path=model, restore=False,
                         retrieval_mode="topk", topk=4, logger=False,
                         slot_direct=True, memory_access=True,
                         audit_enabled=True)
        app.remember("我的手机号是138-0000-2222")
        res = app.ask("我的手机号是多少？")
        self.assertEqual(res["state"], "slot_direct")
        app.flush_access(1.0)
        end = _t.time() + 2
        n = 0
        while _t.time() < end:
            try:
                n = app.con.execute("SELECT COUNT(*) FROM memory_access").fetchone()[0]
                if n:
                    break
            except Exception:                        # noqa: BLE001
                pass
            _t.sleep(0.02)
        self.assertGreaterEqual(n, 1)                  # access 仍记录
        f = [x for x in os.listdir(adir) if x.endswith(".jsonl")][0]
        evs = [_json.loads(l) for l in open(os.path.join(adir, f), encoding="utf-8")]
        self.assertTrue([e for e in evs if e["stage"] == "answer"])

    def test_slot_direct_on_returns_db_value(self):
        app = self.make_app(False)
        app.slot_direct = True
        import time as _t
        app.remember("我的手机号是139-0000-1111")
        _t.sleep(1.05)                                  # 避开同秒冲突
        app.remember("我的手机号是138-0000-2222")
        res = app.ask("我的手机号是多少？")
        self.assertEqual(res["state"], "slot_direct")
        self.assertEqual(res["answer"], "138-0000-2222")
        self.assertTrue(res["block_ids"])
        self.assertEqual(app._slot_stats["applied"], 1)

    def test_rerank_off_no_field(self):
        app = self.make_app(False)
        with mock.patch.object(D, "NATURAL_MODE", True):
            app._ask_natural = lambda t, t0: {"answer": "x", "block_ids": []}
            res = app.ask("我的手机号是多少")
        self.assertNotIn("attribute_rerank", res)

    def test_wire_rerank_changes_order_keeps_all(self):
        app = self.make_app(False)
        app.attribute_rerank = True
        app.remember("我的手机号是13900001111")
        app.remember("我的手机号是13800002222")
        ids = [r[0] for r in app._rows()]
        app._retrieval_select_k2 = lambda text: [
            {"source_id": i, "name": "m%d" % i, "score": 1.0} for i in ids]
        out = app._retrieval_select("我的手机号是多少？")
        self.assertEqual(len(out), 2)                  # 保留全部
        self.assertEqual(out[0]["source_id"], max(ids))  # 新值在前
        self.assertEqual(app._last_rerank["attribute"], "phone")

    def test_wire_filters_selection(self):
        app = self.make_app(True)
        app._retrieval_select_k2 = lambda text: [
            {"source_id": 1, "name": "a", "score": 1.0},
            {"source_id": 2, "name": "b", "score": 2.0}]
        for sid, text, ts in ((1, "我的手机号是13900001111", "2026-01-01T00:00:00"),
                              (2, "我的手机号是13800002222", "2026-02-01T00:00:00")):
            app.remember(text)
        # remember 使用真实 DB id；改用真实行 id
        ids = [r[0] for r in app._rows()]
        app._retrieval_select_k2 = lambda text: [
            {"source_id": i, "name": "m%d" % i, "score": 1.0} for i in ids]
        out = app._retrieval_select("我的手机号是多少？")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["source_id"], max(ids))


if __name__ == "__main__":
    unittest.main()
