# -*- coding: utf-8 -*-
"""audit_log：字段齐、不记原文、JSONL 追加、异常不炸调用方。"""
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

import audit_log as A  # noqa: E402


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="audit_")
        self.env = mock.patch.dict(os.environ, {"LLAMA_AUDIT_DIR": self.tmp})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def _lines(self):
        p = os.path.join(self.tmp, A.datetime.now().strftime("%Y%m%d") + ".jsonl")
        return [json.loads(l) for l in open(p, encoding="utf-8")]

    def test_fields_complete_and_no_raw_text(self):
        r = A.event("write", decision="allow", reason="ok", block_ids=[3, 22],
                    asked_slot="车牌", latency_ms=12.345,
                    query="我的车牌号是京A88888", answer="你的车牌号是京A88888")
        self.assertTrue(r["ok"])
        rec = self._lines()[-1]
        for k in ("trace_id", "ts", "stage", "decision", "reason", "block_ids",
                  "asked_slot", "tenant", "scope", "latency_ms",
                  "query_sha16", "answer_sha16"):
            self.assertIn(k, rec, k)
        raw = json.dumps(rec, ensure_ascii=False)
        self.assertNotIn("京A88888", raw)          # 不记原文
        self.assertNotIn("我的车牌", raw)
        self.assertEqual(rec["block_ids"], [3, 22])
        self.assertEqual(rec["latency_ms"], 12.35)

    def test_append(self):
        A.event("write", decision="allow", reason="a")
        A.event("align", decision="reject", reason="b")
        self.assertEqual(len(self._lines()), 2)

    def test_record_alignment(self):
        res = {"trace_id": "t1", "decision": "reject", "reason": "other_slot_value",
               "asked": {"subject": "self", "predicate": "保险到期"},
               "answer_slot": "保险到期", "fail_open": False,
               "query": "保险到期日", "answer": "京N·7K3Q3"}
        self.assertTrue(A.record_alignment(res)["ok"])
        rec = self._lines()[-1]
        self.assertEqual(rec["stage"], "align")
        self.assertEqual(rec["asked_slot"], "保险到期")
        self.assertNotIn("京N", json.dumps(rec, ensure_ascii=False))

    def test_exception_does_not_raise(self):
        with mock.patch("builtins.open", side_effect=OSError("disk full")):
            r = A.event("answer", decision="pass", reason="ok")
        self.assertFalse(r["ok"])
        self.assertIn("disk full", r["error"])

    def test_bad_stage(self):
        r = A.event("nope", decision="pass")
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
