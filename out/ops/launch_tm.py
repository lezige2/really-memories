# -*- coding: utf-8 -*-
"""Detached service launcher for K3 (port 8766, dedicated copy).

Usage: python out/ops/launch_k3.py <on|off> <db> <blocks>
Prints the PID; the process is DETACHED so a reaped parent job cannot kill it.
"""
import os
import subprocess
import sys

ROOT = r"D:\llama-mem"
arm, db, blocks = sys.argv[1], sys.argv[2], sys.argv[3]
mode_dir = os.path.join(ROOT, "out", "k5-ops")
os.makedirs(mode_dir, exist_ok=True)
out = open(os.path.join(mode_dir, "service_%s.out" % arm), "ab", buffering=0)
err = open(os.path.join(mode_dir, "service_%s.err" % arm), "ab", buffering=0)
cmd = [
    sys.executable, "-X", "utf8", os.path.join(ROOT, "tools", "chat_service.py"),
    "--db", db, "--blocks", blocks,
    "--sessions", os.path.join(ROOT, "kvmem", "k5", "sessions"),
    "--session", "kvc.json",
    "--host", "127.0.0.1", "--port", "8766",
    "--retrieval", "topk", "--topk", "4", "--n-gpu-layers", "28",
    "--n-ctx", "32768", "--chat-start", "8192",
    "--model", r"D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf",
]
if arm == "on":
    cmd.append("--temporal-memory")
flags = 0x00000008 | 0x00000200          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
p = subprocess.Popen(cmd, cwd=ROOT, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                     creationflags=flags, close_fds=True)
print(p.pid)