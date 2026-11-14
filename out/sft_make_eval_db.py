# -*- coding: utf-8 -*-
"""为被测模型建立独立评测记忆库：复制 chat.db + 用被测模型重建全部 KV 块。
用法：python -X utf8 out/sft_make_eval_db.py --model D:/models/qwen-sft-v4-Q4_K_M.gguf [--dst kvmem/sft_eval]
"""
import argparse
import os
import shutil
import sys

ROOT = r"D:\llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kvslots            # noqa: E402
import memory_source as ms  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dst", default=os.path.join("kvmem", "sft_eval"))
    ap.add_argument("--src-db", default=os.path.join("kvmem", "daily", "chat.db"))
    ap.add_argument("--ngl", type=int, default=28)
    ap.add_argument("--nctx", type=int, default=32768)
    a = ap.parse_args()
    dst = a.dst if os.path.isabs(a.dst) else os.path.join(ROOT, a.dst)
    blocks = os.path.join(dst, "blocks")
    sessions = os.path.join(dst, "sessions")
    db = os.path.join(dst, "chat.db")
    os.makedirs(blocks, exist_ok=True)
    os.makedirs(sessions, exist_ok=True)
    if not os.path.exists(db):
        shutil.copy2(a.src_db if os.path.isabs(a.src_db) else os.path.join(ROOT, a.src_db), db)
        print("COPIED_DB", db)
    con = ms.connect(db)
    names = [r[0] for r in con.execute(
        "SELECT name FROM memory_source WHERE tenant='default' AND scope='private'")]
    print("memories", len(names))
    if not names:
        print("EMPTY_MEMORY_LIB")
        return 2
    eng = kvslots.KVEngine(a.model, n_ctx=a.nctx, n_seq=8, gpu=a.ngl, kv="q8_0")
    try:
        for name in names:
            src = ms.get_source(con, name)
            p = os.path.join(blocks, name + ".kvmem")
            if os.path.exists(p):
                os.remove(p)
            ms.build_block(eng, con, src, blocks_dir=blocks, kv_type="q8_0",
                           model_path=a.model, seq=6)
        problems = ms.verify(con, blocks_dir=blocks, model_path=a.model)
        print("REBUILT", len(names), "VERIFY", problems or "none")
    finally:
        eng.close()
    print("MODEL", a.model)
    print("DB", db)
    return 0


if __name__ == "__main__":
    sys.exit(main())