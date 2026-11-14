# -*- coding: utf-8 -*-
"""span_annotate：偏移/≤4类/否定不抽/整块命中/标签片段/预算。"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import span_annotate as SA  # noqa: E402


class AnnotateTests(unittest.TestCase):
    def test_offsets_and_classes(self):
        t = "我下周三去北京开会"
        a = SA.annotate(t)
        self.assertTrue(a["spans"])
        self.assertLessEqual(len(a["spans"]), 4)
        for s in a["spans"]:
            self.assertEqual(t[s["start"]:s["end"]], s["text"])
        types = {s["type"] for s in a["spans"]}
        self.assertIn("subject", types)
        self.assertIn("time", types)

    def test_negation_no_span(self):
        self.assertFalse(SA.annotate("不是去北京而是去上海。")["spans"])

    def test_search_returns_whole_block(self):
        b = {"id": 22, "text": "我下周三去北京开会"}
        hits = SA.search("下周三北京开会", [b])
        self.assertEqual(hits[0]["id"], 22)
        self.assertEqual(hits[0]["block"]["text"], b["text"])   # 整块，不切片

    def test_label_fragment(self):
        t = "我下周三去北京开会"
        a = SA.annotate(t)
        lab = SA.label_fragment(22, a["spans"])
        self.assertTrue(lab.startswith("块22｜"))
        for s in a["spans"]:
            self.assertIn("=%s" % s["text"], lab)
        self.assertNotIn("{", lab)

    def test_budget(self):
        fs = ["块1｜主体=我｜时间=下周三", "块2｜主体=我｜时间=下周"]
        r = SA.fit_labels(fs, 5)
        self.assertLessEqual(r["tokens"], 5)
        self.assertLessEqual(len(r["labels"]), 2)

    def test_poc(self):
        import json
        root = os.path.dirname(_HERE)
        p = os.path.join(root, "out", "SPAN-POC.json")
        if not os.path.exists(p):
            self.skipTest("no poc")
        d = json.load(open(p, encoding="utf-8"))
        self.assertEqual(d["offset_rate"], 1.0)
        self.assertLessEqual(d["max_classes"], 4)


if __name__ == "__main__":
    unittest.main()
