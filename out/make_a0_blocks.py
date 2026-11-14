# -*- coding: utf-8 -*-
"""A0 实验：把 20 条记忆重建为自描述格式（policy 不动）。
用法：python -X utf8 out/make_a0_blocks.py --mode dialogue|header
"""
import argparse, os, sqlite3, sys
ROOT = r"D:\llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kvslots
import memory_source as ms

ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=["dialogue", "dialogue_ack", "header"], default="dialogue")
ap.add_argument("--model", default=r"D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf")
ap.add_argument("--src", default=os.path.join(ROOT, "kvmem", "sft_eval", "chat.db"))
a = ap.parse_args()
src = sqlite3.connect(a.src)
rows = list(src.execute("SELECT name,label,text FROM memory_source WHERE tenant='default' AND scope='private'"))
src.close()
print("memories", len(rows))
dst = os.path.join(ROOT, "kvmem", "a0_" + a.mode)
blocks = os.path.join(dst, "blocks"); sessions = os.path.join(dst, "sessions")
db = os.path.join(dst, "chat.db")
os.makedirs(blocks, exist_ok=True); os.makedirs(sessions, exist_ok=True)
if os.path.exists(db):
    os.remove(db)
for f in os.listdir(blocks):
    os.remove(os.path.join(blocks, f))
con = ms.connect(db)
for name, label, text in rows:
    t = (text or "").strip()
    if a.mode == "dialogue":
        fmt = "用户：" + t
    elif a.mode == "dialogue_ack":
        fmt = "用户：" + t + "\n助手：好的，记住了"
    else:
        fmt = "以下是用户之前说过、需要记住的事实：" + t
    new_name = "a0" + "".join(ch for ch in name if ch.isdigit())[-2:] + "_" + ms.sha256_text(fmt)[:12]
    ms.put_source(con, new_name, (label or name) + " [a0]", fmt)
    print("WARN name-convention:", name, "->", new_name)
names = [r[0] for r in con.execute("SELECT name FROM memory_source")]
eng = kvslots.KVEngine(a.model, n_ctx=32768, n_seq=8, gpu=28, kv="q8_0")
try:
    for name in names:
        row = ms.get_source(con, name)
        p = os.path.join(blocks, name + ".kvmem")
        if os.path.exists(p):
            os.remove(p)
        ms.build_block(eng, con, row, blocks_dir=blocks, kv_type="q8_0",
                       model_path=a.model, seq=6)
    problems = ms.verify(con, blocks_dir=blocks, model_path=a.model)
    print("REBUILT", len(names), "VERIFY", problems or "none")
finally:
    eng.close()
print("DB", db)
