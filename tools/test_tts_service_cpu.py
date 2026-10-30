# -*- coding: utf-8 -*-
"""TTS 服务集成单测：默认 off、敏感跳过、异步失败不影响回答、懒加载失败 off。"""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import chat_daily as D  # noqa: E402
import tts_sapi as T  # noqa: E402


class FakeTTS:
    def __init__(self, mode="ok", wav=None):
        self.mode = mode
        self.wav = wav
        self.calls = []

    def synthesize(self, text, out=None, speak=False, enabled=True, timeout=60):
        self.calls.append(text)
        if self.mode == "raise":
            raise RuntimeError("boom")
        reason = T.skip_reason(T.clean_text(text))
        if reason:
            return {"ok": True, "invoked": False, "skipped": reason}
        path = self.wav or out
        if path:
            open(path, "wb").write(b"RIFFfake")
        return {"ok": True, "invoked": True, "wav": path, "bytes": 9}


class TTSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = os.path.join(tempfile.mkdtemp(prefix="tts_"), "model.stub")
        D.install_fake_model(cls.model)

    def make_app(self, tts):
        tmp = tempfile.mkdtemp(prefix="tts_%s_" % self.id())
        app = D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                         blocks_dir=os.path.join(tmp, "b"),
                         sessions_dir=os.path.join(tmp, "s"),
                         model_path=self.model, restore=False,
                         retrieval_mode="topk", topk=4, logger=False,
                         tts=tts, tts_dir=os.path.join(tmp, "out_tts"))
        return app

    def wait(self, app, timeout=2.0):
        end = time.time() + timeout
        while time.time() < end:
            if app._last_tts.get("status") not in ("queued", "idle"):
                return app._last_tts
            time.sleep(0.01)
        return app._last_tts

    def test_off_never_calls(self):
        app = D.DailyApp(D.StubEngine(),
                         db_path=os.path.join(tempfile.mkdtemp(prefix="tts_off_"), "d.db"),
                         blocks_dir=os.path.join(tempfile.mkdtemp(), "b"),
                         sessions_dir=os.path.join(tempfile.mkdtemp(), "s"),
                         model_path=self.model, restore=False, retrieval_mode="topk",
                         topk=4, logger=False, tts=False)
        called = []
        with mock.patch.object(D, "_tts_module", lambda: called.append(1) or FakeTTS()):
            app._tts_emit("你好")
        self.assertEqual(called, [])
        self.assertEqual(app._last_tts["status"], "disabled")

    def test_sensitive_skipped(self):
        fake = FakeTTS()
        app = self.make_app(True)
        with mock.patch.object(D, "_tts_module", lambda: fake):
            app._tts_emit("你的手机号是13800138000")
            app._tts_emit("地址是B座302，余额 100 元")
            app._tts_emit("你的银行卡号是 6222 0000 1111 2222")
        self.assertEqual(fake.calls, [])
        self.assertEqual(app._last_tts["status"], "skipped")

    def test_async_exception_does_not_break_answer(self):
        app = self.make_app(True)
        fake = FakeTTS(mode="raise")
        with mock.patch.object(D, "_tts_module", lambda: fake):
            app._ask_natural = lambda text, t0: {"answer": "你好", "block_ids": []}
            res = app.ask("你好")
            self.assertEqual(res["answer"], "你好")
            meta = self.wait(app)
            self.assertEqual(meta["status"], "error")
            self.assertIn("boom", meta["error"])

    def test_wav_and_sha(self):
        app = self.make_app(True)
        tmp = tempfile.mkdtemp(prefix="wav_")
        fake = FakeTTS(wav=os.path.join(tmp, "a.wav"))
        with mock.patch.object(D, "_tts_module", lambda: fake):
            app._tts_emit("今天天气不错")
            meta = self.wait(app)
        self.assertEqual(meta["status"], "ok")
        self.assertTrue(meta.get("sha256"))

    def test_off_20_responses_identical(self):
        base = self.make_app(False)
        off = self.make_app(False)

        def fake(text, t0):
            return {"answer": "答案:" + text, "block_ids": [1, 2]}

        base._ask_natural = fake
        off._ask_natural = fake
        with mock.patch.object(D, "_tts_module", lambda: (_ for _ in ()).throw(
                AssertionError("TTS must not load when off"))):
            for i in range(20):
                self.assertEqual(base.ask("问题%d" % i), off.ask("问题%d" % i), i)

    def test_lazy_import_failure_off(self):
        app = self.make_app(True)
        D._TTS_CACHE["loaded"] = True
        D._TTS_CACHE["mod"] = None
        try:
            app._tts_emit("你好")
        finally:
            D._TTS_CACHE["loaded"] = False
            D._TTS_CACHE["mod"] = None
        self.assertEqual(app._last_tts["status"], "unavailable")
        self.assertTrue(app.warnings)


if __name__ == "__main__":
    unittest.main()
