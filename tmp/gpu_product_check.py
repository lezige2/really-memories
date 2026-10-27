# -*- coding: utf-8 -*-
"""Throwaway GPU product check: retrieval (10 memories) + rollover (forced).

Run after acceptance finishes: python -X utf8 tmp/gpu_product_check.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = r"D:\llama-mem"
WORK = os.path.join(ROOT, "kvmem", "_c_gpu2")
DAILY = os.path.join(ROOT, "tools", "chat_daily.py")

FACTS = [
    "我每周三晚上七点有组会，地点在B座302。",
    "我的工位在A座12层，内线电话是8021。",
    "我偏好喝美式咖啡，不加糖。",
    "本周待办：交周报、周三体检、周五复盘。",
    "我的车牌号是京A88888，车型是比亚迪汉。",
    "我对花生过敏，点餐时要避开花生。",
    "我的快递默认放在丰巢A区3号柜。",
    "团队周报要在每周五下午五点前提交。",
    "我常用的会议室是B座302（组会用）和A座101（评审用）。",
    "我的年度目标是完成三个可复现实验并写一份总结。",
]
TAGS = ["个人信息", "个人信息", "偏好", "待办", "个人信息",
        "偏好", "个人信息", "工作", "工作", "目标"]


def send(p, line, wait=1.0):
    p.stdin.write(line + "\n")
    p.stdin.flush()
    time.sleep(wait)


def read_until(p, pat, timeout=120):
    buf = []
    end = time.time() + timeout
    while time.time() < end:
        ln = p.stdout.readline()
        if not ln:
            break
        buf.append(ln.rstrip("\n"))
        if re.search(pat, ln):
            return buf
    return buf


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    for d in ("blocks", "sessions"):
        os.makedirs(os.path.join(WORK, d), exist_ok=True)
    args = [sys.executable, "-X", "utf8", DAILY,
            "--db", os.path.join(WORK, "chat.db"),
            "--blocks", os.path.join(WORK, "blocks"),
            "--sessions", os.path.join(WORK, "sessions"),
            "--session", "gpu.json",
            "--n-ctx", "16384", "--chat-start", "8192", "--n-gpu-layers", "34",
            "--retrieval", "topk", "--topk", "4", "--rollover-at", "0.02"]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.Popen(args, cwd=ROOT, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace",
                         bufsize=1, env=env)
    t0 = time.time()
    banner = read_until(p, "READY", timeout=180)
    load_s = round(time.time() - t0, 2)
    res = {"load_s": load_s, "remembers": [], "asks": [], "status": [], "rollover": {}}
    try:
        for fact, tag in zip(FACTS, TAGS):
            send(p, "/remember %s #%s" % (fact, tag), wait=0.05)
            lines = read_until(p, "已记住", timeout=120)
            res["remembers"].append(lines[-1] if lines else "NO-RESP")
        send(p, "/status", wait=0.05)
        st = read_until(p, "你>", timeout=60)
        res["status"].append("\n".join(st[-80:]))
        for q in ("我周几有组会？地点在哪？", "我的车牌号是多少？"):
            send(p, q, wait=0.05)
            lines = read_until(p, "你>", timeout=180)
            res["asks"].append({"q": q, "out": "\n".join(lines[-20:])})
        # forced rollover: threshold = 2% of 8192 ~= 164 tokens; two answers may cross it
        for q in ("本周待办有哪些？", "我喝咖啡有什么偏好？"):
            send(p, q, wait=0.05)
            lines = read_until(p, "你>", timeout=180)
            res["asks"].append({"q": q, "out": "\n".join(lines[-20:])})
        res["rollover"]["archive_files"] = sorted(
            os.listdir(os.path.join(WORK, "archive"))) if os.path.isdir(
                os.path.join(WORK, "archive")) else []
        send(p, "/status", wait=0.05)
        st = read_until(p, "你>", timeout=60)
        res["status"].append("\n".join(st[-80:]))
        send(p, "/quit", wait=0.5)
        try:
            p.wait(timeout=120)
        except subprocess.TimeoutExpired:
            p.kill()
    finally:
        try:
            p.kill()
        except Exception:
            pass
    with open(os.path.join(ROOT, "tmp", "gpu_product_check.json"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: (v if k != "asks" else [a["q"] for a in v])
                      for k, v in res.items()}, ensure_ascii=False, indent=1))
    print("written tmp/gpu_product_check.json")


if __name__ == "__main__":
    main()