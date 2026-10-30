# -*- coding: utf-8 -*-
"""Windows SAPI TTS 最小落地（本地 System.Speech；不联网、不云 TTS）。

- 只接受**最终答案文本**；本模块不读 DB / 块 / 记忆原文（无 sqlite/memory_source 依赖）。
- 默认只写 wav、不自动播；`--speak` 才本机播放。
- 敏感 / 拒答 / SILENCE 一律不播；默认库函数 enabled=False（未接入服务、默认 off）。
- QQ 语音只产 wav 文件，不接桥。

用法：
  python -X utf8 tools/tts_sapi.py --text "你好" --out tmp/tts/a.wav
  python -X utf8 tools/tts_sapi.py --text "你好" --out tmp/tts/a.wav --speak
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAX_CHARS = 500

# 拒答/无内容：不播
REFUSAL_MARKERS = ("不知道", "没有记录", "没记录", "不清楚", "没提过", "无法确定",
                   "记不清", "无法回答", "没有相关", "查不到", "没有找到", "抱歉",
                   "未提及", "无相关信息")
SILENCE_MARKERS = ("silence", "<silence>", "[silence]", "静音", "sil")
# 敏感：不播（密码/证件/银行卡长数字/密钥）
SENSITIVE_RE = re.compile(
    r"(密码|口令|验证码|身份证|银行卡号|卡号|secret|api[\s_-]?key|token\s*=|"
    r"(?<!\d)\d{16,19}(?!\d)|(?:\d{4}[ -]){3,4}\d{4})", re.I)
_THINK_RE = re.compile(r"<think[^>]*>.*?</think\s*>|</?analysis[^>]*>", re.S | re.I)
_CODE_RE = re.compile(r"```.*?```", re.S)
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_MD_RE = re.compile(r"[*_`#>|\[\]()]+|^\s*[-–—]\s*", re.M)
_WS_RE = re.compile(r"[\s\u3000]+")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(text):
    """清洗最终答案：去 think/代码块/URL/Markdown/控制符，压空白；不改事实词。"""
    s = str(text or "")
    s = _THINK_RE.sub(" ", s)
    s = _CODE_RE.sub(" ", s)
    s = _LINK_RE.sub(r"\1", s)
    s = _URL_RE.sub(" ", s)
    s = _MD_RE.sub(" ", s)
    s = _CTRL_RE.sub("", s)
    s = unicodedata.normalize("NFKC", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def truncate(text, max_chars=MAX_CHARS):
    """超长按句末截断并加省略号；返回 <= max_chars+1。"""
    s = str(text or "")
    if len(s) <= max_chars:
        return s
    cut = -1
    for ch in "。！？!?.":
        i = s.rfind(ch, 0, max_chars)
        if i > cut:
            cut = i
    if cut < 0:
        return s[:max_chars] + "…"
    return s[:cut + 1] + "…"


def skip_reason(text):
    """返回跳过原因（refusal/silence/sensitive/empty）或 None。"""
    s = str(text or "").strip()
    if not s:
        return "empty"
    low = s.lower()
    if low in SILENCE_MARKERS or low.strip("[]<> ") == "silence":
        return "silence"
    if any(m in s for m in REFUSAL_MARKERS):
        return "refusal"
    if SENSITIVE_RE.search(s):
        return "sensitive"
    return None


def _ps_quote(p):
    return "'" + str(p).replace("'", "''") + "'"


def synthesize(text, out=None, speak=False, enabled=True, max_chars=MAX_CHARS,
               rate=0, voice=None, timeout=60):
    """本地合成 wav（可选播放）。enabled=False 时零调用（默认 off）。"""
    if not enabled:
        return {"ok": True, "invoked": False, "skipped": "disabled"}
    raw = str(text or "")
    cleaned = clean_text(raw)
    reason = skip_reason(cleaned)
    if reason:
        return {"ok": True, "invoked": False, "skipped": reason,
                "chars": len(cleaned)}
    spoken = truncate(cleaned, max_chars)
    tmpdir = os.path.join(ROOT, "tmp", "tts")
    os.makedirs(tmpdir, exist_ok=True)
    if not out:
        out = os.path.join(tmpdir, "tts-%s.wav" % time.strftime("%Y%m%d-%H%M%S"))
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out) or tmpdir, exist_ok=True)
    txt_path = out + ".txt"
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write(spoken)
    ps = [
        "Add-Type -AssemblyName System.Speech",
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
        "$s.Rate = %d" % max(-10, min(10, int(rate))),
    ]
    if voice:
        ps.append("try { $s.SelectVoice(%s) } catch { }" % _ps_quote(voice))
    ps += [
        "$t = Get-Content -Raw -Encoding UTF8 %s" % _ps_quote(txt_path),
        "$s.SetOutputToWaveFile(%s)" % _ps_quote(out),
        "$s.Speak($t)",
        "$s.Dispose()",
    ]
    if speak:
        ps += ["$p = New-Object System.Media.SoundPlayer %s" % _ps_quote(out),
               "$p.PlaySync()"]
    ps_path = out + ".ps1"
    with open(ps_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(ps) + "\n")
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", ps_path],
        capture_output=True, text=True, timeout=timeout)
    latency_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    ok = proc.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0
    res = {"ok": bool(ok), "invoked": True, "wav": out,
           "bytes": os.path.getsize(out) if os.path.exists(out) else 0,
           "latency_ms": latency_ms, "chars": len(cleaned),
           "spoken_chars": len(spoken), "truncated": len(cleaned) > len(spoken),
           "speak": bool(speak), "stderr": (proc.stderr or "").strip()[:300]}
    for p in (txt_path, ps_path):
        try:
            os.remove(p)
        except OSError:
            pass
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="Windows SAPI local TTS (wav only by default)")
    ap.add_argument("--text", default=None, help="最终答案文本；缺省读 stdin")
    ap.add_argument("--out", default=None, help="wav 输出路径（默认 tmp/tts/tts-*.wav）")
    ap.add_argument("--speak", action="store_true", help="合成后本机播放（默认不播）")
    ap.add_argument("--max-chars", type=int, default=MAX_CHARS)
    ap.add_argument("--rate", type=int, default=0, help="-10..10")
    ap.add_argument("--voice", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    text = args.text if args.text is not None else sys.stdin.read()
    res = synthesize(text, out=args.out, speak=args.speak, enabled=True,
                     max_chars=args.max_chars, rate=args.rate, voice=args.voice)
    if args.json:
        print(json.dumps(res, ensure_ascii=False))
    else:
        if res.get("skipped"):
            print("SKIP %s" % res["skipped"])
        else:
            print("OK %s bytes=%s latency=%sms chars=%s->%s"
                  % (res.get("wav"), res.get("bytes"), res.get("latency_ms"),
                     res.get("chars"), res.get("spoken_chars")))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())