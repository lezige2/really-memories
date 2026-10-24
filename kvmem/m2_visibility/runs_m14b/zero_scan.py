import os, sys, json, hashlib, time
P = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf.dl"
OUT = r"D:\llama-mem\kvmem\m2_visibility\runs_m14b\zero_scan.json"
BS = 1 << 20  # 1 MiB
ZERO = b"\x00" * BS
size = os.path.getsize(P)
h = hashlib.sha256()
t0 = time.time()
nblk = 0
zero_idx = []
nonzero = 0
last_nonzero_end = -1
first_nonzero_start = None
with open(P, "rb") as f:
    off = 0
    while True:
        b = f.read(BS)
        if not b:
            break
        h.update(b)
        nblk += 1
        if len(b) == BS and b == ZERO:
            zero_idx.append(off)
        else:
            # partial tail block: check all-zero properly
            if b.count(0) == len(b):
                zero_idx.append(off)
            else:
                nonzero += 1
                if first_nonzero_start is None:
                    first_nonzero_start = off
                last_nonzero_end = off + len(b)
        off += len(b)
        if off % (1 << 30) < BS:
            print("read %.2f/%0.2f GB  %.1f MB/s" % (off/2**30, size/2**30, off/2**20/max(time.time()-t0,1e-9)), flush=True)
dt = time.time() - t0
rep = {
  "path": P,
  "size_bytes": size,
  "block_size": BS,
  "total_blocks": nblk,
  "zero_blocks": len(zero_idx),
  "nonzero_blocks": nonzero,
  "zero_block_offsets_first10": zero_idx[:10],
  "zero_block_offsets_last10": zero_idx[-10:],
  "zero_ranges": None,
  "first_nonzero_offset": first_nonzero_start,
  "last_nonzero_end": last_nonzero_end,
  "sha256": h.hexdigest(),
  "seconds": round(dt,1),
  "mb_per_s": round(size/2**20/dt,1),
}
# compress zero block offsets into contiguous ranges
ranges = []
for o in zero_idx:
    if ranges and o == ranges[-1][1]:
        ranges[-1][1] = o + BS
    else:
        ranges.append([o, o + BS])
rep["zero_ranges"] = ranges
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rep, f, indent=1)
print("DONE size=%d zero_blocks=%d ranges=%d sha256=%s %.1fs" % (size, len(zero_idx), len(ranges), h.hexdigest(), dt), flush=True)
if len(ranges) <= 40:
    print("RANGES", ranges, flush=True)
