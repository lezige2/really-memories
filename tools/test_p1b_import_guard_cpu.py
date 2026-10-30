# -*- coding: utf-8 -*-
"""P1b 可选依赖守卫：模块缺失时 import 成功、走原写路径；存在时接线可用。"""
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import chat_daily as D  # noqa: E402


class P1bGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="p1bg_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, p1b_flag):
        tmp = tempfile.mkdtemp(prefix="p1bg_%s_" % self.id())
        return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                          blocks_dir=os.path.join(tmp, "b"),
                          sessions_dir=os.path.join(tmp, "s"),
                          model_path=self.model, restore=False,
                          retrieval_mode="topk", topk=4,
                          p1b_subject=p1b_flag, logger=False)

    def test_import_succeeds_when_module_missing(self):
        code = ("import sys; sys.modules['p1b_subject']=None; "
                "sys.path.insert(0, 'tools'); import chat_daily as D; "
                "print(D._p1b is None)")
        out = subprocess.run([sys.executable, "-X", "utf8", "-c", code],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("True", out.stdout)

    def test_missing_module_falls_back_to_original_write(self):
        app = self.make_app(True)
        old = D._p1b
        D._p1b = None
        root = os.path.join("out", "p1b", "sidecar")
        before = set(os.listdir(root)) if os.path.isdir(root) else set()
        try:
            r = app.remember("我的车牌号是京A11111")
            self.assertIn("id", r)
            self.assertTrue(app.warnings)
            after = set(os.listdir(root)) if os.path.isdir(root) else set()
            self.assertEqual(after, before)          # 未写 sidecar
        finally:
            D._p1b = old

    def test_present_module_still_wired(self):
        self.assertIsNotNone(D._p1b)
        app = self.make_app(True)
        old = app.remember("我的车牌号是京A11111")
        new = app.remember("我的车牌号换成京B22222了")
        side = D._p1b.Sidecar(D._p1b.sidecar_path(app.db_path)).load()
        self.assertEqual(side.entries()[new["id"]]["supersedes"], old["id"])


if __name__ == "__main__":
    unittest.main()
