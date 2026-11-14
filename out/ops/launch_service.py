import os, sqlite3, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("LLAMA_MEM_ROOT") or os.path.dirname(os.path.dirname(HERE))
MODEL = os.environ.get("LLAMA_MEM_MODEL") or r"D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf"
LOG = os.path.join(ROOT, "out", "p1-enable")
os.makedirs(LOG, exist_ok=True)
DB = os.path.join(ROOT, "kvmem", "daily", "chat.db")
BLOCKS = os.path.join(ROOT, "kvmem", "daily", "blocks")

# Portable/embedded install: old DB rows may point at D:\llama-mem absolute
# paths. Rewrite only when the basename exists under the new blocks dir.
try:
    if os.path.exists(DB):
        con = sqlite3.connect(DB)
        for sid, p in con.execute("SELECT source_id,path FROM memory_block"):
            if not p:
                continue
            q = os.path.join(BLOCKS, os.path.basename(p))
            if q != p and os.path.exists(q):
                con.execute("UPDATE memory_block SET path=? WHERE source_id=?", (q, sid))
        con.commit()
        con.close()
except Exception:
    pass
out = open(os.path.join(LOG, "service.out"), "ab", buffering=0)
err = open(os.path.join(LOG, "service.err"), "ab", buffering=0)
cmd = [
    sys.executable, "-X", "utf8", os.path.join(ROOT, "tools", "chat_service.py"),
    "--db", DB,
    "--blocks", BLOCKS,
    "--sessions", os.path.join(ROOT, "kvmem", "daily", "sessions"),
    "--host", "127.0.0.1", "--port", "8765",
    "--retrieval", "topk", "--topk", "4", "--n-gpu-layers", "28",
    "--model", MODEL,
]
flags = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
p = subprocess.Popen(cmd, cwd=ROOT, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                     creationflags=flags, close_fds=True)
print(p.pid)