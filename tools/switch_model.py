# -*- coding: utf-8 -*-
"""一键切换模型：停服务 → 清会话 → 用目标模型重建全部记忆块 → 起服务 → 自检。

用法：
  python -X utf8 tools/switch_model.py --model D:/models/XXX.gguf [--port 8765]
不写任何密码/token；记忆原文只在本地 DB 与块文件之间流转。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def kill_port(port):
    import subprocess as sp
    out = sp.run(["powershell", "-NoProfile", "-Command",
                  "Get-NetTCPConnection -LocalPort %d -State Listen -ErrorAction SilentlyContinue "
                  "| ForEach-Object { $_.OwningProcess }" % port],
                 capture_output=True, text=True).stdout
    for line in out.split():
        line = line.strip()
        if line.isdigit():
            sp.run(["powershell", "-NoProfile", "-Command",
                    "Stop-Process -Id %s -Force" % line], capture_output=True)


def rebuild(model):
    import kvslots
    import memory_source as ms
    db = os.path.join(ROOT, "kvmem", "daily", "chat.db")
    blocks = os.path.join(ROOT, "kvmem", "daily", "blocks")
    con = ms.connect(db)
    eng = kvslots.KVEngine(model, n_ctx=16384, n_seq=8, gpu=34, kv="q8_0")
    try:
        names = [r[0] for r in con.execute(
            "SELECT name FROM memory_source WHERE tenant='default' AND scope='private'")]
        done = 0
        for name in names:
            src = ms.get_source(con, name)
            p = os.path.join(blocks, name + ".kvmem")
            if os.path.exists(p):
                os.remove(p)
            ms.build_block(eng, con, src, blocks_dir=blocks, kv_type="q8_0",
                           model_path=model, seq=6)
            done += 1
        problems = ms.verify(con, blocks_dir=blocks, model_path=model)
        return done, problems
    finally:
        eng.close()


def start(model, port):
    log = os.path.join(ROOT, "kvmem", "daily", "svc_switch.log")
    env = dict(os.environ, LLAMA_MEM_CHAT_FORMAT="chatml")
    cmd = [sys.executable, "-X", "utf8", os.path.join(ROOT, "tools", "chat_service.py"),
           "--port", str(port), "--model", model,
           "--db", os.path.join(ROOT, "kvmem", "daily", "chat.db"),
           "--blocks", os.path.join(ROOT, "kvmem", "daily", "blocks"),
           "--sessions", os.path.join(ROOT, "kvmem", "daily", "sessions"),
           "--session", "daily.json", "--n-ctx", "16384", "--chat-start", "8192",
           "--n-gpu-layers", "34", "--retrieval", "topk", "--topk", "4"]
    fh = open(log, "ab")
    return subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)


def wait(port, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=3):
                return True
        except Exception:                        # noqa: BLE001
            time.sleep(2)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    kill_port(a.port)
    time.sleep(2)
    ts = time.strftime("%Y%m%dT%H%M%S")
    for name in ("daily.json", "daily.chat.kvmem", "daily.transcript.json"):
        p = os.path.join(ROOT, "kvmem", "daily", "sessions", name)
        if os.path.exists(p):
            shutil.copy2(p, p + ".switch-" + ts)
            os.remove(p)
    n, problems = rebuild(a.model)
    print("rebuilt_blocks", n, "verify", problems or "none")
    proc = start(a.model, a.port)
    if not wait(a.port):
        print("SERVICE_FAILED pid", proc.pid)
        return 2
    print("SERVICE_UP", proc.pid, a.port, os.path.basename(a.model))
    return 0


if __name__ == "__main__":
    sys.exit(main())