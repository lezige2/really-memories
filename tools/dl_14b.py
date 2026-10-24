import os, sys, time, urllib.request
URL = "https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
DST = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
PART = DST + ".part"
req = urllib.request.Request(URL, headers={"User-Agent": "curl/8"})
t0 = time.time()
with urllib.request.urlopen(req, timeout=60) as r, open(PART, "wb") as f:
    total = int(r.headers.get("Content-Length") or 0)
    print("total_bytes", total, flush=True)
    got = 0
    while True:
        b = r.read(1 << 22)
        if not b:
            break
        f.write(b); got += len(b)
        if got % (1 << 28) < (1 << 22):
            print("progress %.2f GB  %.1f MB/s" % (got / 2**30, got / 2**20 / max(time.time() - t0, 1)), flush=True)
print("done", got, "in", round(time.time() - t0, 1), "s", flush=True)
os.replace(PART, DST)
print("RENAMED", DST, os.path.getsize(DST), flush=True)
