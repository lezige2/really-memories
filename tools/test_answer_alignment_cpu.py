# -*- coding: utf-8 -*-
"""answer_alignment 三级漏斗：主体/槽位/显式值；fail-open；归一。"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import answer_alignment as A  # noqa: E402


class AlignTests(unittest.TestCase):
    def test_accept_aligned(self):
        r = A.decide("张伟的车牌是多少？", "张伟的车牌号是京N·7K3Q0",
                     [{"id": 19, "text": "张伟的车的车牌号是京N·7K3Q0，他说……"}])
        self.assertEqual(r["decision"], "pass")
        self.assertTrue(r["reason"])

    def test_reject_wrong_subject(self):
        r = A.decide("杨帆的车牌是多少？", "京N·7K3Q3",
                     [{"id": 21, "text": "吴静的车的车牌号是京N·7K3Q3，他说……"}])
        self.assertEqual(r["decision"], "reject")

    def test_reject_other_slot(self):
        r = A.decide("我的车牌保险到期日是哪天？", "京N·7K3Q3",
                     [{"id": 21, "text": "吴静的车牌号是京N·7K3Q3"}])
        self.assertEqual(r["decision"], "reject")
        self.assertIn(r["reason"], ("other_slot_value", "facet_time_mismatch")
                      if r["reason"].startswith("other_slot") else (r["reason"],))
        self.assertTrue("other_slot" in r["reason"] or "facet" in r["reason"])

    def test_fail_open_without_predicate(self):
        r = A.decide("今天天气怎么样？", "还行", [])
        self.assertEqual(r["decision"], "pass")
        self.assertTrue(r["fail_open"])

    def test_explicit_value_mismatch(self):
        r = A.decide("我的卡尾号8899对不对？", "对，是8898",
                     [{"id": 1, "text": "我的银行卡尾号是8899"}])
        self.assertEqual(r["decision"], "reject")

    def test_normalization(self):
        self.assertEqual(A.norm_value("８８９９"), "8899")
        self.assertEqual(A.norm_value("八九九"), "899")
        r = A.decide("我的车牌是多少？", "京Ｎ·7K3Q0",
                     [{"id": 19, "text": "我的车牌号是京N·7K3Q0"}])
        self.assertEqual(r["decision"], "pass")

    def test_output_fields(self):
        r = A.decide("张伟的车牌是多少？", "京N·7K3Q0",
                     [{"id": 19, "text": "张伟的车牌号是京N·7K3Q0"}])
        for k in ("decision", "reason", "fail_open", "asked", "trace_id"):
            self.assertIn(k, r)


class SelfCheckTests(unittest.TestCase):
    def test_s0b_pos20_query_answer_level(self):
        import json
        root = os.path.dirname(_HERE)
        raw = json.load(open(os.path.join(root, "out", "ALIGN-V3-RAW.json"),
                             encoding="utf-8"))
        bad = []
        for c in raw["positives"]:
            r = A.decide(c["query"], c["answer"], None)
            if r["decision"] != "pass":
                bad.append((c["id"], r["reason"]))
        self.assertEqual(bad, [])                     # 20/20，误拒 0

    def test_p2_counts(self):
        import json
        import sqlite3
        root = os.path.dirname(_HERE)
        d = json.load(open(os.path.join(root, "out", "P2-NEG-E2E.json"),
                           encoding="utf-8"))
        con = sqlite3.connect("file:%s?mode=ro" % os.path.join(
            root, "kvmem", "scale40k", "n200", "chat.db").replace("\\", "/"),
            uri=True)

        def blocks(ids):
            out = []
            for i in ids or []:
                r = con.execute("SELECT id,text FROM memory_source WHERE id=?",
                                (int(i),)).fetchone()
                if r:
                    out.append({"id": r[0], "text": r[1]})
            return out

        neg_rej = sum(1 for n in d["negatives"]
                      if A.decide(n["query"], n["answer"],
                                  blocks(n.get("block_ids")))["decision"] == "reject")
        pos_pass = sum(1 for p in d["targets"]
                       if A.decide(p["query"], p["answer"],
                                   blocks(p.get("block_ids")))["decision"] == "pass")
        self.assertEqual(neg_rej, 20)      # 其余为拒答/fail-open（见报告）
        self.assertEqual(pos_pass, 3)     # 3 条正例答案本身错（P2 targets_pass=2/10）


if __name__ == "__main__":
    unittest.main()
