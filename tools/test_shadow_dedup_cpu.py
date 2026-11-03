# -*- coding: utf-8 -*-
"""shadow_dedup：99 对门 + 42 夹具误合并 0；纯代码不写库。"""
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import shadow_dedup as S  # noqa: E402

ROOT = os.path.dirname(_HERE)


def load_pairs():
    texts = {}
    for line in open(os.path.join(ROOT, "out", "SHADOW-PAIRS-100.jsonl"),
                     encoding="utf-8"):
        r = json.loads(line)
        texts[r["pair_id"]] = (r["text_a"], r["text_b"])
    labels = {}
    for line in open(os.path.join(ROOT, "out", "SHADOW-PAIRS-100-LABELS.jsonl"),
                     encoding="utf-8"):
        r = json.loads(line)
        if not r.get("uncertain"):
            labels[r["pair_id"]] = r["label"]
    return texts, labels


class RuleTests(unittest.TestCase):
    def test_same_paraphrase_merges(self):
        d = S.decide("张伟家的猫叫小橘。", "张伟养的那只猫，名字是小橘。")
        self.assertTrue(d["would_merge"])
        self.assertIsNone(d["risk"])

    def test_negation_not_merged(self):
        d = S.decide("我的猫叫豆豆。", "我的猫不叫豆豆。")
        self.assertFalse(d["would_merge"])
        self.assertEqual(d["risk"], "negation")

    def test_qualifier_and_number_mismatch(self):
        self.assertFalse(S.decide("我的手机号是13900001111。",
                                  "我的工作号是13900001111。")["would_merge"])
        self.assertFalse(S.decide("我的会议是2026-11-05 09:30。",
                                  "我的会议是2026-12-05 09:30。")["would_merge"])

    def test_multi_entity_flagged(self):
        d = S.decide("我的车是白色。", "我又买了一辆车，也是白色。")
        self.assertTrue(d["would_merge"])
        self.assertEqual(d["risk"], "multi_entity")
        self.assertFalse(d["merge_allowed"])          # 不许静默合并

    def test_no_db_side_effects(self):
        self.assertNotIn("sqlite3", vars(S))
        self.assertNotIn("memory_source", vars(S))


class GateTests(unittest.TestCase):
    def test_98_pairs_accuracy(self):
        texts, labels = load_pairs()
        ev = S.evaluate({k: texts[k] for k in labels}, labels)
        self.assertEqual(ev["total"], 98)
        self.assertEqual(ev["accuracy"], 1.0, ev["failures"][:3])
        self.assertEqual(ev["wrong_merge"], 0)
        self.assertEqual(ev["missed_merge"], 0)

    def test_42_fixtures_zero_wrong_merge(self):
        fx = [json.loads(l) for l in
              open(os.path.join(ROOT, "out", "KV-CONFLICT-40.jsonl"),
                   encoding="utf-8")]
        self.assertEqual(len(fx), 42)
        fe = S.evaluate_fixtures(fx)
        self.assertEqual(fe["fixtures"], 42)
        self.assertEqual(fe["wrong_merge"], 0)


if __name__ == "__main__":
    unittest.main()
