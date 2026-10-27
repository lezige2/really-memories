# -*- coding: utf-8 -*-
"""小批量自然对话探测（带超时，避免卡死拖垮 shell）。"""
import json
import sys
import time
import urllib.request

URL = "http://127.0.0.1:8765/ask"
QS = [
    "我下周三要去上海开会",
    "我下周三去哪开会？",
    "解释一下什么是KV缓存",
    "你是什么模型",
    "我明天要去哪里出差？",
]

for q in QS:
    t0 = time.time()
    try:
        data = json.dumps({"text": q}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            d = json.loads(resp.read().decode("utf-8"))
        print("Q:", q)
        print("  A:", str(d.get("answer"))[:140].replace("\n", " "))
        print("  state=", d.get("state"), "blocks=", d.get("block_ids"),
              "ms=", int((time.time() - t0) * 1000))
    except Exception as exc:                                 # noqa: BLE001
        print("Q:", q, "| ERROR", type(exc).__name__, str(exc)[:80],
              "| ms=", int((time.time() - t0) * 1000))
    sys.stdout.flush()