# -*- coding: utf-8 -*-
"""上下文/层数配置探测：起服务 → 等健康 → 3 问 → 采样显存 → 关服务。"""
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def vram_gib():
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "$m=Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory "
                              "-ErrorAction SilentlyContinue|Measure-Object DedicatedUsage -Sum;"
                              "[math]::Round($m.Sum/1GB,3)"],
                             capture_output=True, text=True).stdout.strip()
        return float(out)
    except Exception:                              # noqa: BLE001
        return -1.0


def run(name, n_ctx, layers, chat_start=8192, port=8770):
    log = os.path.join(ROOT, "kvmem", "daily", "probe_%s.log" % name)
    env = dict(os.environ, LLAMA_MEM_CHAT_FORMAT="chatml")
    cmd = [sys.executable, "-X", "utf8", os.path.join(ROOT, "tools", "chat_service.py"),
           "--port", str(port),
           "--model", "D:/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf",
           "--db", os.path.join(ROOT, "kvmem", "daily", "chat.db"),
           "--blocks", os.path.join(ROOT, "kvmem", "daily", "blocks"),
           "--sessions", os.path.join(ROOT, "kvmem", "daily", "sessions"),
           "--session", "probe_%s.json" % name,
           "--n-ctx", str(n_ctx), "--chat-start", str(chat_start),
           "--n-gpu-layers", str(layers), "--retrieval", "topk", "--topk", "4"]
    fh = open(log, "wb")
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)
    t0 = time.time()
    ok = False
    while time.time() - t0 < 120:
        if proc.poll() is not None:
            break
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=3):
                ok = True
                break
        except Exception:                          # noqa: BLE001
            time.sleep(2)
    res = {"name": name, "n_ctx": n_ctx, "layers": layers, "health": ok,
           "vram_after_load": vram_gib(), "answers": []}
    if ok:
        for q in ("现在几点？", "你好", "我的车牌号是多少？"):
            t = time.time()
            try:
                data = json.dumps({"text": q}, ensure_ascii=False).encode()
                req = urllib.request.Request("http://127.0.0.1:%d/ask" % port, data=data,
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    d = json.loads(resp.read().decode())
                res["answers"].append({"q": q, "a": str(d.get("answer"))[:60],
                                       "s": round(time.time() - t, 2)})
            except Exception as exc:               # noqa: BLE001
                res["answers"].append({"q": q, "err": type(exc).__name__})
    res["vram_peakish"] = vram_gib()
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except Exception:                              # noqa: BLE001
        proc.kill()
    print(json.dumps(res, ensure_ascii=False))
    return res


if __name__ == "__main__":
    name = sys.argv[1]
    n_ctx = int(sys.argv[2])
    layers = int(sys.argv[3])
    run(name, n_ctx, layers)