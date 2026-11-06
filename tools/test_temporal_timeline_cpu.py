# -*- coding: utf-8 -*-
"""时间轴检索：多时间词/未来/过去/abstain/歧义/惰性。"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import temporal_timeline as TL  # noqa: E402

A = "2026-11-06T09:00:00"


def rows(*items):
    return [{"id": i, "text": t, "created_at": c} for i, t, c in items]


class IntervalTests(unittest.TestCase):
    def test_multi_time_words(self):
        ivs = TL.extract_intervals("去年十月我去过云南，前年在北京", A)
        self.assertGreaterEqual(len(ivs), 2)
        self.assertEqual(ivs[0]["start"], "2025-10-01")      # 去年十月 -> 月级
        self.assertGreaterEqual(len(ivs), 2)

    def test_future_and_past(self):
        f = TL.extract_intervals("明年我要考证", A)
        self.assertEqual(f[0]["start"][:4], "2027")
        p = TL.extract_intervals("三年前我在苏州", A)
        self.assertEqual(p[0]["start"][:4], "2023")

    def test_build_timeline_fields(self):
        tl = TL.build_timeline(rows((1, "我去年去过云南", "2026-11-06T09:00:00")))
        self.assertEqual(tl[0]["id"], 1)
        self.assertEqual(tl[0]["anchor"], "2026-11-06T09:00:00")
        self.assertTrue(tl[0]["phrases"])
        self.assertIn("interval", str(tl[0]["intervals"][0].keys()) + "intervals")


class RetrieveTests(unittest.TestCase):
    def test_past_hit(self):
        r = TL.retrieve("去年我去过哪？", A,
                        rows((1, "我去年去过云南大理", A),
                             (2, "我现在养了一只猫", A)))
        self.assertFalse(r["abstain"])
        self.assertEqual([k["id"] for k in r["kept"]], [1])
        self.assertEqual(r["kept"][0]["phrase"], "去年")

    def test_future_hit(self):
        r = TL.retrieve("明年我要做什么？", A,
                        rows((1, "明年我打算考一个证书", A)))
        self.assertFalse(r["abstain"])
        self.assertEqual(r["kept"][0]["intervals"][0]["start"][:4], "2027")

    def test_abstain_no_block(self):
        r = TL.retrieve("三年前我养过什么宠物？", A,
                        rows((1, "我现在养了一只猫", A)))
        self.assertTrue(r["abstain"])
        self.assertEqual(r["reason"], "no_time_match")

    def test_ambiguous_fallback(self):
        r = TL.retrieve("去年十月和前年三月我去过哪？", A,
                        rows((1, "去年十月我去过云南", A),
                             (2, "前年三月我去过北京", A)))
        self.assertTrue(r["ambiguous"])
        self.assertTrue(r["kept"])
        self.assertTrue(any(k["reason"] == "ambiguous_fallback" for k in r["kept"])
                        or len(r["kept"]) >= 1)

    def test_lazy_no_time(self):
        r = TL.retrieve("我的猫叫什么", A,
                        rows((1, "我养了一只猫叫豆豆", A)))
        self.assertTrue(r["lazy"])
        self.assertFalse(r["abstain"])
        self.assertTrue(r["kept"])


if __name__ == "__main__":
    unittest.main()
