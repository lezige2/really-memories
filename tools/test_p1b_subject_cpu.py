# -*- coding: utf-8 -*-
"""P1b：sidecar 主体键 + 写时软覆盖/追问（默认 off）。

Run: python -X utf8 -m unittest discover -s tools -p "test_p1b_subject_cpu.py" -v
"""
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import p1b_subject as P  # noqa: E402
import chat_daily as D  # noqa: E402


def row(i, text, created="2026-10-01T10:00:00"):
    return (i, "m%d" % i, "l", text, "h", 1, "p", 8, created)


class PureTests(unittest.TestCase):
    def test_extract(self):
        info = P.extract("我的车牌号是京A11111")
        self.assertEqual(info["subject"], "self")
        self.assertEqual(info["predicate"], "车牌")
        self.assertEqual(info["value"], "京A11111")

    def test_sidecar_rebuild_and_delete(self):
        tmp = tempfile.mkdtemp(prefix="p1b_")
        path = os.path.join(tmp, "s.json")
        side = P.Sidecar(path).rebuild([row(1, "我的车牌号是京A11111")])
        side.save()
        again = P.Sidecar(path).load()
        self.assertIn(1, again.entries())
        self.assertEqual(again.entries()[1]["text_sha256"],
                         P.sha_text("我的车牌号是京A11111"))
        os.remove(path)
        self.assertEqual(P.Sidecar(path).load().entries(), {})   # 删 sidecar 回现网

    def test_decide_cue_supersede_and_ask(self):
        tmp = tempfile.mkdtemp(prefix="p1b_")
        side = P.Sidecar(os.path.join(tmp, "s.json")).rebuild(
            [row(1, "我的车牌号是京A11111")])
        dec = P.decide("我的车牌号换成京B22222了", "2026-10-02T10:00:00", side)
        self.assertEqual(dec["action"], "supersede")
        self.assertEqual(dec["target"], 1)
        # 无 cue 且 created_at 更早 -> 追问
        dec2 = P.decide("我的车牌号是京C33333", "2026-09-01T10:00:00", side)
        self.assertEqual(dec2["action"], "ask")
        self.assertEqual(dec2["reason"], "no_cue")
        # 否定 cue -> 追问
        dec3 = P.decide("我的车牌号已经不在京A11111", "2026-10-03T10:00:00", side)
        self.assertEqual(dec3["action"], "ask")
        self.assertEqual(dec3["reason"], "negative_cue")

    def test_ambiguous_subject_and_two_cars(self):
        tmp = tempfile.mkdtemp(prefix="p1b_")
        side = P.Sidecar(os.path.join(tmp, "s.json")).rebuild(
            [row(1, "我的车牌号是京A11111"),
             row(2, "赵磊的车牌号是京B22222"),
             row(3, "我的特斯拉是蓝色"), row(4, "比亚迪是黑色")])
        dec = P.decide("车牌换成京C33333了", "2026-10-02T10:00:00", side)
        self.assertEqual(dec["action"], "ask")
        self.assertEqual(dec["reason"], "ambiguous_subject")
        keep = P.latest_ids(side)
        self.assertIn(1, keep)                     # 不同 subject 不互相覆盖
        self.assertIn(2, keep)

    def test_same_second_counter(self):
        tmp = tempfile.mkdtemp(prefix="p1b_")
        side = P.Sidecar(os.path.join(tmp, "s.json")).rebuild(
            [row(1, "我的车牌号是京A11111", "2026-10-02T10:00:00")])
        P.decide("我的车牌号换成京B22222", "2026-10-02T10:00:00", side)
        self.assertEqual(side.data["stats"]["same_second_conflict"], 1)

    def test_key_lock_serializes_same_key(self):
        a = P.key_lock("default", "self", "车牌")
        b = P.key_lock("default", "self", "车牌")
        self.assertIs(a, b)


class C02SafetyTests(unittest.TestCase):
    """C02：新实体（又买/新买/第二辆/又办卡）绝不覆盖同族旧值。"""

    def _side(self):
        tmp = tempfile.mkdtemp(prefix="c02_")
        return P.Sidecar(os.path.join(tmp, "s.json")).rebuild(
            [row(1, "我的车牌号是沪A11111"),
             row(2, "我的银行卡尾号是1234")])

    def test_new_entity_variants_ask(self):
        for text in ("我又买了一辆车，车牌是沪C22222",
                     "新买的车车牌是沪D33333",
                     "再买一辆，车牌沪E44444",
                     "第二辆车车牌是沪F55555",
                     "我又办了一张卡，尾号8899"):
            dec = P.decide(text, "2026-10-05T10:00:00", self._side())
            self.assertEqual(dec["action"], "ask", text)
            self.assertEqual(dec["reason"], "new_entity", text)

    def test_new_entity_never_supersedes_even_with_cue(self):
        side = self._side()
        dec = P.decide("又买了一辆车，车牌换成沪G66666了", "2026-10-05T10:00:00", side)
        self.assertEqual(dec["action"], "ask")
        self.assertEqual(side.entries()[1].get("superseded_by"), None)
        self.assertEqual(side.entries()[2].get("superseded_by"), None)

    def test_old_car_still_kept_read_side(self):
        side = self._side()
        P.decide("新买一辆车，车牌是沪C22222", "2026-10-05T10:00:00", side)
        self.assertIn(1, P.latest_ids(side))          # 旧车仍可检索


class ExtractGapTests(unittest.TestCase):
    """extract 通用缺口：槽位词表 + 值模式（每类 2 个泛化变体）。"""

    def test_plate_variants(self):
        for t, v in (("旧的那块牌子沪A11111我还留着", "沪A11111"),
                     ("我的车号是京B22222", "京B22222")):
            info = P.extract(t)
            self.assertEqual(info["predicate"], "车牌", t)
            self.assertEqual(info["value"], v, t)

    def test_seat_variants(self):
        for t in ("我调到C区11号了", "从B座302搬走了"):
            self.assertEqual(P.extract(t)["predicate"], "工位", t)
        self.assertTrue(P.extract("我调到C区11号了")["value"])
        self.assertTrue(P.extract("从B座302搬走了")["value"])

    def test_bank_card_variants(self):
        self.assertEqual(P.extract("工资卡换成6217 0012 3456 7801")["value"], "7801")
        self.assertEqual(P.extract("信用卡号是6222 0000 1111 2222")["value"], "2222")

    def test_leave_and_move_variants(self):
        self.assertEqual(P.extract("我从顺丰离职了")["predicate"], "公司")
        self.assertEqual(P.extract("我从美团辞职了")["value"], "美团")
        self.assertEqual(P.extract("从B座302搬走了")["predicate"], "工位")

    def test_removal_variants(self):
        for t in ("猫已经送人了", "我不养狗了", "那个会员我已经退了",
                  "会员卡退掉了"):
            info = P.extract(t)
            self.assertTrue(info, t)
            self.assertEqual(info["value"], "__removed__", t)

    def test_removal_decide_asks_not_supersede(self):
        tmp = tempfile.mkdtemp(prefix="rm_")
        side = P.Sidecar(os.path.join(tmp, "s.json")).rebuild(
            [row(1, "我养的猫叫豆豆")])
        dec = P.decide("猫已经送人了", "2026-10-05T10:00:00", side)
        self.assertEqual(dec["action"], "ask")


class WireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="p1bw_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, p1b_flag):
        tmp = tempfile.mkdtemp(prefix="p1bw_%s_" % self.id())
        os.environ["P1B_SIDECAR_DIR"] = os.path.join(tmp, "side")
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "daily.db"),
                          blocks_dir=os.path.join(tmp, "blocks"),
                          sessions_dir=os.path.join(tmp, "sessions"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4,
                          p1b_subject=p1b_flag, logger=False)

    def test_flag_off_unchanged_no_sidecar(self):
        app = self.make_app(False)
        r = app.remember("我的车牌号是京A11111")
        self.assertIn("id", r)
        self.assertFalse(os.path.exists(P.sidecar_path(app.db_path)))

    def test_write_supersede_and_read_filter(self):
        app = self.make_app(True)
        old = app.remember("我的车牌号是京A11111")
        new = app.remember("我的车牌号换成京B22222了")
        self.assertIn("id", new)                       # 有 cue -> 直接写
        side = P.Sidecar(P.sidecar_path(app.db_path)).load()
        ent = side.entries()[new["id"]]
        self.assertEqual(ent["supersedes"], old["id"])
        self.assertEqual(side.entries()[old["id"]]["superseded_by"], new["id"])
        # 读侧只留最新
        app._retrieval_select_k2 = lambda text: [
            {"name": "old", "score": 1.0, "source_id": old["id"], "signals": {}},
            {"name": "new", "score": 2.0, "source_id": new["id"], "signals": {}}]
        out = app._retrieval_select("我的车牌号是多少？")
        self.assertEqual([s["source_id"] for s in out], [new["id"]])

    def test_no_cue_asks_zero_write_then_confirm(self):
        app = self.make_app(True)
        first = app.remember("我的车牌号是京A11111")
        before = len(app._rows())
        r = app.remember("我的车牌号是京C33333")       # created_at 更晚但无 cue -> 追问
        self.assertTrue(r.get("needs_confirmation"))
        self.assertEqual(len(app._rows()), before)     # 零写入
        r2 = app.remember("我的车牌号是京C33333", confirm_token=r["confirm_token"])
        self.assertIn("id", r2)


if __name__ == "__main__":
    unittest.main()