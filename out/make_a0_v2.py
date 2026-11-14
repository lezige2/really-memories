# -*- coding: utf-8 -*-
"""A0 v2：不改 memory_source.text（权威层不动），只用 build_block(block_text=...) 格式化块内容。
用法：python -X utf8 out/make_a0_v2.py --mode header|dialogue_special|dialogue_ack
"""
import argparse, os, shutil, sqlite3, sys
ROOT = r"D:\llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kvslots
import memory_source as ms

FMT = {
    "header": lambda t: "以下是用户之前说过、需要记住的事实：" + t,
    "dialogue_special": lambda t: ("<|im_start|>user\n" + t + "<|im_end|>\n"
                                  "<|im_start|>assistant\n好的，记住了<|im_end|>"),
    "dialogue_ack": lambda t: "用户：" + t + "\n助手：好的，记住了",
}

ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=list(FMT), default="header")
ap.add_argument("--model", default=r"D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf")
ap.add_argument("--src", default=os.path.join(ROOT, "kvmem", "sft_eval", "chat.db"))
a = ap.parse_args()
dst = os.path.join(ROOT, "kvmem", "a0v2_" + a.mode)
blocks = os.path.join(dst, "blocks"); sessions = os.path.join(dst, "sessions")
os.makedirs(blocks, exist_ok=True); os.makedirs(sessions, exist_ok=True)
db = os.path.join(dst, "chat.db")
shutil.copy2(a.src, db)
for f in os.listdir(blocks):
    os.remove(os.path.join(blocks, f))
con = ms.connect(db)
rows = list(con.execute("SELECT id,name,text FROM memory_source WHERE tenant='default' AND scope='private'"))
print("memories", len(rows))
eng = kvslots.KVEngine(a.model, n_ctx=32768, n_seq=8, gpu=28, kv="q8_0")
tok_hist = []
try:
    for mid, name, text in rows:
        src = ms.get_source(con, name)
        p = os.path.join(blocks, name + ".kvmem")
        if os.path.exists(p):
            os.remove(p)
        r = ms.build_block(eng, con, src, blocks_dir=blocks, kv_type="q8_0",
                           model_path=a.model, seq=6, block_text=FMT[a.mode](text))
        tok_hist.append(r["n_tokens"])
    problems = ms.verify(con, blocks_dir=blocks, model_path=a.model)
    print("REBUILT", len(rows), "VERIFY", problems or "none",
          "tokens_min", min(tok_hist), "tokens_max", max(tok_hist),
          "tokens_sum", sum(tok_hist))
finally:
    eng.close()
print("DB", db)
