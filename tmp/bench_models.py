# -*- coding: utf-8 -*-
"""模型对比基准：依次在独立端口起服务，跑同一组句子，记录延迟/回答。

用法：
  python -X utf8 tmp/bench_models.py --model D:/models/A.gguf --tag r1
  python -X utf8 tmp/bench_models.py --model D:/models/B.gguf --tag qwen
输出：out/MODEL-COMPARE-<tag>.json（逐句 latency/answer/state）
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

QS = [
    "你好",
    "你是谁呀？",
    "待会有人加你qq你同意一下",
    "需要他的qq号吗",
    "你加什么了",
    "我下周五要去成都开会",
    "我下周五去哪开会？",
    "我明天要去哪里出差？",
    "今天北京天气怎么样",
    "随便聊聊吧",
]


def wait_health(port, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=3):
                return True
        except Exception:                         # noqa: BLE001
            time.sleep(2)
    return False


def ask(port, text, timeout=180):
    data = json.dumps({"text": text}, ensure_ascii=False).encode()
    req = urllib.request.Request("http://127.0.0.1:%d/ask" % port, data=data,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            d = json.loads(resp.read().decode("utf-8"))
        return {"q": text, "answer": d.get("answer"), "state": d.get("state"),
                "refused": d.get("refused"), "latency_s": round(time.time() - t0, 2)}
    except Exception as exc:                      # noqa: BLE001
        return {"q": text, "error": "%s: %s" % (type(exc).__name__, exc),
                "latency_s": round(time.time() - t0, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    out = os.path.join(root, "out", "MODEL-COMPARE-%s.json" % a.tag)
    log = os.path.join(root, "kvmem", "qq_logs", "bench_%s.log" % a.tag)
    cmd = [sys.executable, "-X", "utf8", os.path.join(root, "tools", "chat_service.py"),
           "--port", str(a.port), "--model", a.model,
           "--db", os.path.join(root, "kvmem", "daily", "chat.db"),
           "--blocks", os.path.join(root, "kvmem", "daily", "blocks"),
           "--sessions", os.path.join(root, "kvmem", "daily", "sessions"),
           "--session", "bench_%s.json" % a.tag, "--n-ctx", "16384",
           "--chat-start", "8192", "--n-gpu-layers", "34",
           "--retrieval", "topk", "--topk", "4"]
    with open(log, "wb") as fh:
        proc = subprocess.Popen(cmd, cwd=root, stdout=fh, stderr=subprocess.STDOUT)
    try:
        if not wait_health(a.port):
            print("HEALTH_TIMEOUT", a.tag)
            return 2
        rows = [ask(a.port, q) for q in QS]
        json.dump({"model": a.model, "tag": a.tag, "port": a.port, "rows": rows},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:                         # noqa: BLE001
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())