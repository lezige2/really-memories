import os, sys, time, urllib.request, threading
URL = "https://hf-mirror.com/bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
DST = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
N = 8
req = urllib.request.Request(URL, method="HEAD", headers={"User-Agent": "curl/8"})
with urllib.request.urlopen(req, timeout=60) as r:
    total = int(r.headers["Content-Length"])
    print("total", total, flush=True)
part = DST + ".dl"
if not os.path.exists(part) or os.path.getsize(part) != total:
    with open(part, "wb") as f:
        f.truncate(total)
chunk = total // N + 1
done = [0] * N
lock = threading.Lock()
t0 = time.time()

def worker(i):
    lo = i * chunk
    hi = min(lo + chunk, total) - 1
    if lo > hi:
        return
    with open(part, "r+b") as f:
        pos = lo
        while pos <= hi:
            end = min(pos + (1 << 22) - 1, hi)
            rq = urllib.request.Request(URL, headers={"User-Agent": "curl/8", "Range": "bytes=%d-%d" % (pos, end)})
            for attempt in range(5):
                try:
                    with urllib.request.urlopen(rq, timeout=60) as resp:
                        data = resp.read()
                    break
                except Exception:
                    time.sleep(2)
            else:
                raise RuntimeError("worker %d failed at %d" % (i, pos))
            f.seek(pos)
            f.write(data)
            with lock:
                done[i] += len(data)
            pos = end + 1

ts = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(N)]
for t in ts: t.start()
while any(t.is_alive() for t in ts):
    time.sleep(10)
    got = sum(done)
    print("progress %.2f/%.2f GB  %.2f MB/s" % (got / 2**30, total / 2**30, got / 2**20 / max(time.time() - t0, 1)), flush=True)
got = sum(done)
print("downloaded", got, "of", total, "in", round(time.time() - t0, 1), "s", flush=True)
if got == total:
    os.replace(part, DST)
    print("RENAMED", DST, os.path.getsize(DST), flush=True)
else:
    print("INCOMPLETE", got, flush=True)
