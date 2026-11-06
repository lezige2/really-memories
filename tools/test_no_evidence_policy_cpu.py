# -*- coding: utf-8 -*-
"""无证据策略：微信号不得被手机号顶替；正反回归 + K5 不触发。"""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import no_evidence_policy as N  # noqa: E402
import chat_daily as D  # noqa: E402


MEM_PHONE = [{"id": 1, "text": "我的手机号是138-0000-2222"}]


class PolicyTests(unittest.TestCase):
    def test_wechat_phone_violation(self):
        r = N.check("我的微信号是多少？", "你的微信号是 138-0000-2222", MEM_PHONE)
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "phone_claimed_as_wechat")

    def test_phone_explained_pass(self):
        r = N.check("我的微信号是多少？",
                    "你只告诉过我手机号 138-0000-2222，没告诉我微信号；这是手机号",
                    MEM_PHONE)
        self.assertTrue(r["ok"])
        self.assertEqual(r["reason"], "phone_explained_not_wechat")

    def test_phone_unexplained_fail(self):
        r = N.check("我的微信号是多少？", "138-0000-2222", MEM_PHONE)
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "phone_unexplained_for_wechat")

    def test_value_after_wechat_fail(self):
        r = N.check("我的微信号是多少？", "微信号：138-0000-2222", MEM_PHONE)
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "phone_claimed_as_wechat")

    def test_no_phone_in_memory_fail(self):
        r = N.check("我的微信号是多少？", "这是手机号：138-0000-2222", [])
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "phone_without_memory_evidence")

    def test_phone_question_ok(self):
        self.assertTrue(N.check("我的手机号是多少？", "138-0000-2222", MEM_PHONE)["ok"])

    def test_refusal_ok(self):
        self.assertTrue(N.check("我的微信号是多少？", "没有记录", MEM_PHONE)["ok"])

    def test_wechat_fact_present_ok(self):
        mem = [{"id": 1, "text": "我的微信号是 wx_abc"}]
        self.assertTrue(N.check("我的微信号是多少？", "wx_abc", mem)["ok"])


class K5RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="np_"), "model.stub")
        D.install_fake_model(cls.model)

    def test_wechat_not_slot_direct_phone_still(self):
        tmp = tempfile.mkdtemp(prefix="np_app_")
        app = D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                         blocks_dir=os.path.join(tmp, "b"),
                         sessions_dir=os.path.join(tmp, "s"),
                         model_path=self.model, restore=False,
                         retrieval_mode="topk", topk=4, logger=False,
                         slot_direct=True)
        app.remember("我的手机号是138-0000-2222")
        with mock.patch.object(D, "NATURAL_MODE", True):
            app._ask_natural = lambda t, t0: {"answer": "没有记录", "block_ids": []}
            wx = app.ask("我的微信号是多少？")
        self.assertNotEqual(wx.get("state"), "slot_direct")   # 不映射
        self.assertFalse(N.check("我的微信号是多少？", wx["answer"],
                                 MEM_PHONE)["ok"] is False)
        phone = app.ask("我的手机号是多少？")
        self.assertEqual(phone["state"], "slot_direct")
        self.assertEqual(phone["answer"], "138-0000-2222")

    def test_policy_doc_exists(self):
        root = os.path.dirname(_HERE)
        p = os.path.join(root, "out", "NO-EVIDENCE-POLICY.md")
        self.assertTrue(os.path.exists(p))
        body = open(p, encoding="utf-8").read()
        self.assertIn("BM25", body)
        self.assertIn("无别名", body)


if __name__ == "__main__":
    unittest.main()
