# -*- coding: utf-8 -*-
"""remember_file.py — Windows shell context-menu helper.

Usage: pythonw tools/remember_file.py "C:\\path\\file.txt"
Reads a text file and POSTs it to the local llama-mem service.
No service => message box; never writes to the DB directly.
"""
import ctypes
import json
import os
import sys
import urllib.request

API = os.environ.get("LLAMA_MEM_API", "http://127.0.0.1:8765")
MAX = 4000


def msg(text):
    try:
        ctypes.windll.user32.MessageBoxW(0, text, "llama-mem", 0x40)
    except Exception:
        print(text)


def read_text(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-16", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def main():
    if len(sys.argv) < 2:
        msg("用法：remember_file.py <文件路径>")
        return 2
    p = sys.argv[1]
    if not os.path.isfile(p):
        msg("文件不存在：\n" + p)
        return 2
    try:
        text = read_text(p).strip()
    except Exception as e:
        msg("读取失败：%s" % e)
        return 2
    if not text:
        msg("文件为空。")
        return 2
    text = text[:MAX]
    body = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API + "/remember", data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8") or "{}")
        msg("已存入记忆：\n%s" % text[:80])
        return 0
    except Exception as e:
        msg("服务未启动或存入失败：\n%s\n\n先启动 llama-mem 服务。" % e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())