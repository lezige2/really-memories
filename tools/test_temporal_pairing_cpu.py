# -*- coding: utf-8 -*-
"""组级配对：多块组命中、组内主题不符 abstain、歧义/created 冲突 fallback、无组。"""
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import temporal_pairing as TP  # noqa: E402

NOW = "2026-11-06T09:00:00"
ROOT = os.path.dirname(_HERE)


def load():
    out = {}
    for line in open(os.path.join(ROOT, "out", "TIME-35-CASES.jsonl"),
                     encoding="utf-8"):
        c = json.loads(line)
        out[c["id"]] = c
    return out


def rows_of(c):
    blocks = c.get("blocks") or [{"text": c["block"],
                                  "created_at": c["created_at"]}]
    return [{"id": i + 1, "text": b["text"],
             "created_at": b.get("created_at") or c["created_at"],
             "group_id": c.get("group_id"), "related": c.get("related")}
            for i, b in enumerate(blocks)]


class PairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = load()

    def test_multi_block_group_hit(self):
        c = self.c["P01"]
        r = TP.retrieve(c["query"], NOW, rows_of(c))
        self.assertFalse(r["abstain"])
        texts = "\n".join(b["text"] for b in r["kept"])
        self.assertIn("培训", texts)
        self.assertTrue(any(g["group_id"] == "G1" for g in r["groups"]))

    def test_topic_mismatch_abstain(self):
        c = self.c["P02"]
        self.assertTrue(TP.retrieve(c["query"], NOW, rows_of(c))["abstain"])

    def test_group_ambiguity_fallback(self):
        c = self.c["P04"]
        r = TP.retrieve(c["query"], NOW, rows_of(c))
        self.assertTrue(r["ambiguous"])
        self.assertTrue(r["kept"])

    def test_created_conflict_fallback(self):
        c = self.c["P05"]
        r = TP.retrieve(c["query"], NOW, rows_of(c))
        self.assertTrue(r["created_conflict"])

    def test_no_group_abstain(self):
        r = TP.retrieve("去年我养过什么宠物？", NOW,
                        [{"id": 1, "text": "我现在养了一只猫",
                          "created_at": NOW}])
        self.assertTrue(r["abstain"])

    def test_35_gate(self):
        hit = abstain_total = abstain_ok = amb_total = amb_ok = 0
        for c in self.c.values():
            r = TP.retrieve(c["query"], NOW, rows_of(c))
            kind = c["expected"]["kind"]
            exp = c["expected"].get("value")
            if kind == "value":
                txt = "\n".join(b["text"] for b in
                                (c.get("blocks") or [{"text": c["block"]}]))
                ok = bool(r["kept"]) and (
                    str(exp) in txt
                    or any(g["intervals"] and str(exp)[:7] in
                           g["intervals"][0]["start"] for g in r["groups"]))
            elif kind in ("refusal", "abstain"):
                abstain_total += 1
                ok = r["abstain"]
                abstain_ok += bool(ok)
            else:
                amb_total += 1
                ok = bool(r["ambiguous"] or r["created_conflict"])
                amb_ok += bool(ok)
            hit += bool(ok)
        self.assertGreaterEqual(hit, 32)
        self.assertEqual(abstain_ok, abstain_total)     # abstain 100%
        self.assertEqual(amb_ok, amb_total)             # 歧义 100%


if __name__ == "__main__":
    unittest.main()
