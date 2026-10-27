#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qq_probe_real.py -- QQ 手测探针（CPU；只访问本机服务，不加载模型、不登录 QQ）。

用途：在真号手测前/后，把同一批句子直接发给本地助手 `POST /ask`，得到可对照的结果表；
与 QQ 里看到的行为逐条比对（QQ 走 bridge，逻辑相同；bridge 只多一层消息封装）。

用法：
  python -X utf8 tmp/qq_probe_real.py                     # 打 http://127.0.0.1:8765
  python -X utf8 tmp/qq_probe_real.py --base http://127.0.0.1:8765 --timeout 120
  python -X utf8 tmp/qq_probe_real.py --dry-run           # 只打印计划，不发请求
  python -X utf8 tmp/qq_probe_real.py --json tmp/qq_probe_results.json

注意：真发 /ask 会占用助手的推理（可能用 GPU）；本脚本自身零 GPU，只做 HTTP 客户端。
服务未启动时给出可读错误并退出码 1；部分失败仍输出表格、退出码 0。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8765"

# 与 docs/QQ-MANUAL-TEST.md 的步骤一一对应（顺序即脚本顺序）
SENTENCES = [
    "你好",
    "你是谁？",
    "记住：我的车停在 B2 层 37 号。",
    "我的车停在哪里？",
    "我的车牌号是多少？",
    "我的车停在 B2 层 12 号。",
    "珠穆朗玛峰有多高？",
    "今天北京天气怎么样？",
    "太好了，谢谢！",
    "我明天去杭州，我的车停哪？",
    "你还记得我上次说的停车位置吗？",
    "不知道就说不知道：我的车位号是多少？",
]

HONEST_WORDS = ("不知道", "不清楚", "不确定", "未提及", "没有记录", "无法", "不能", "没记")


def _post_ask(base: str, text: str, timeout: float) -> tuple[dict, float, str]:
    """返回 (json, elapsed_s, error)。"""
    payload = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base.rstrip("/") + "/ask", data=payload, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
        return json.loads(body.decode("utf-8")), time.monotonic() - t0, ""
    except urllib.error.HTTPError as exc:
        return {}, time.monotonic() - t0, f"HTTP {exc.code}: {exc.read()[:200].decode('utf-8','replace')}"
    except urllib.error.URLError as exc:
        return {}, time.monotonic() - t0, f"连接失败: {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        return {}, time.monotonic() - t0, f"{type(exc).__name__}: {exc}"


def _status(base: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(base.rstrip("/") + "/status", timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return True, (data.get("version") or "ok") if isinstance(data, dict) else "ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def _answer(data: dict) -> str:
    for key in ("answer", "reply", "text", "response", "content"):
        val = data.get(key) if isinstance(data, dict) else None
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _flag(answer: str, error: str) -> str:
    if error:
        return "ERROR"
    if not answer:
        return "EMPTY"
    if any(w in answer for w in HONEST_WORDS):
        return "honest/refusal"
    return "answer"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="QQ 手测探针（本机 /ask）")
    ap.add_argument("--base", default=DEFAULT_BASE, help="助手服务地址（默认 %s）" % DEFAULT_BASE)
    ap.add_argument("--timeout", type=float, default=120.0, help="单次 /ask 超时秒（默认 120）")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不发请求")
    ap.add_argument("--json", help="把结果写入该 JSON 文件")
    args = ap.parse_args(argv)

    ok, status = _status(args.base)
    print(f"[probe] service={args.base} status={'OK '+status if ok else 'UNAVAILABLE ('+status+')'}", flush=True)
    if not ok and not args.dry_run:
        print("[probe] 助手服务未启动：先运行 python -X utf8 tools/chat_daily.py，再重试。", flush=True)
        return 1

    rows = []
    for i, text in enumerate(SENTENCES, 1):
        if args.dry_run:
            print(f"[dry-run] {i:2d}. {text}", flush=True)
            rows.append({"i": i, "input": text, "flag": "DRY", "ms": 0, "answer": ""})
            continue
        data, elapsed, error = _post_ask(args.base, text, args.timeout)
        answer = _answer(data)
        flag = _flag(answer, error)
        rows.append({"i": i, "input": text, "flag": flag,
                     "ms": round(elapsed * 1000), "answer": answer, "error": error})
        shown = answer.replace("\n", " ")[:70] if answer else error[:70]
        print(f"{i:2d}. [{flag:>14s}] {round(elapsed*1000):>6d}ms  {text[:28]}  ->  {shown}", flush=True)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"base": args.base, "rows": rows,
                       "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
                      fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print(f"[probe] wrote {args.json}", flush=True)

    errors = sum(1 for r in rows if r["flag"] == "ERROR")
    if not args.dry_run:
        print(f"[probe] {len(rows)} steps, {errors} errors; 对照 docs/QQ-MANUAL-TEST.md 的预期行为逐条判读。", flush=True)
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())