# -*- coding: utf-8 -*-
"""test_tts_sapi_cpu.py -- Windows SAPI TTS 最小单测（纯 CPU，不需要音频设备）。

覆盖：文本清洗、超长截断、拒答/敏感/SILENCE 跳过、enabled=False 零调用、
      不依赖 DB/块（模块无 sqlite/memory_source 导入）。
运行： python -X utf8 tools/test_tts_sapi_cpu.py ; exit 0 = 全过
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import tts_sapi as T      # noqa: E402

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(bool(cond))
    print(("ok   %s" % name) if cond else ("FAIL %s %s" % (name, detail)))


def main():
    # 1) 清洗：markdown / URL / think / 代码块 / 控制符
    c = T.clean_text("**你好**\n\n[链接](https://example.com/a) 世界\x07")
    check("clean_markdown_url", c == "你好 链接 世界", repr(c))
    c = T.clean_text("前<think>内部推理</think>后")
    check("clean_think", "内部推理" not in c and "前后" in c.replace(" ", ""), repr(c))
    c = T.clean_text("答案\n```python\nprint(1)\n```\n结束")
    check("clean_code", "print" not in c and "答案" in c and "结束" in c, repr(c))
    check("clean_empty", T.clean_text(None) == "" and T.clean_text("  \n ") == "")

    # 2) 超长截断：按句末截断，<= max+1
    s = "第一句话。" * 300
    out = T.truncate(s, 20)
    check("truncate_len", len(out) <= 21, len(out))
    check("truncate_sentence", out.endswith("。…"), repr(out[-6:]))
    short = "短句。"
    check("truncate_short_unchanged", T.truncate(short, 100) == short)
    check("truncate_no_punct", len(T.truncate("啊" * 100, 10)) == 11)

    # 3) 跳过：拒答 / SILENCE / 敏感
    check("skip_refusal", T.skip_reason("这个我记不清了") == "refusal")
    check("skip_silence", T.skip_reason("SILENCE") == "silence")
    check("skip_empty", T.skip_reason("   ") == "empty")
    check("skip_password", T.skip_reason("密码是 123456") == "sensitive")
    check("skip_card", T.skip_reason("卡号 6217 0012 3456 7804") == "sensitive")
    check("skip_id", T.skip_reason("身份证 110101199001011234") == "sensitive")
    check("skip_phone", T.skip_reason("我的手机号是 13910002010") == "sensitive")
    check("keep_normal", T.skip_reason("你的车牌号是京A88888") is None)

    # 4) enabled=False：零调用（不启动 PowerShell）
    called = []

    def boom(*a, **k):
        called.append(1)
        raise AssertionError("should not be called")

    orig = T.subprocess.run
    T.subprocess.run = boom
    try:
        r = T.synthesize("你好", enabled=False)
        check("disabled_not_invoked", r["invoked"] is False and r.get("skipped") == "disabled" and not called,
              repr(r))
    finally:
        T.subprocess.run = orig

    # 5) 只吃最终答案文本：模块不依赖 DB/块
    src = open(os.path.join(HERE, "tts_sapi.py"), encoding="utf-8").read()
    check("no_db_import", "import sqlite3" not in src and "import memory_source" not in src
          and "import memory_block" not in src)

    # 6) 可选真实合成（默认关；不播）
    if os.environ.get("TTS_SAPI_REAL") == "1":
        r = T.synthesize("你好，这是测试。", out=os.path.join(HERE, "..", "tmp", "tts", "test.wav"))
        check("real_wav", r.get("ok") and r.get("bytes", 0) > 0 and not r.get("speak"), repr(r))

    bad = [i for i, ok in enumerate(CHECKS) if not ok]
    print("\n%d/%d checks passed" % (len(CHECKS) - len(bad), len(CHECKS)))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())