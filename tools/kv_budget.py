"""读取 GGUF 元数据，算 KV cache 记忆预算。"""
import struct

PATH = r"D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
WANT = {
    "general.architecture", "block_count", "attention.head_count",
    "attention.head_count_kv", "embedding_length", "attention.key_length",
    "attention.value_length", "context_length", "rope.freq_base",
}


def rd_str(f):
    n = struct.unpack("<Q", f.read(8))[0]
    return f.read(n).decode("utf-8", "replace")


def rd_val(f, t):
    simple = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
              6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
    if t in simple:
        return struct.unpack(simple[t], f.read(struct.calcsize(simple[t])))[0]
    if t == 8:
        return rd_str(f)
    if t == 9:
        et = struct.unpack("<I", f.read(4))[0]
        n = struct.unpack("<Q", f.read(8))[0]
        return [rd_val(f, et) for _ in range(n)]
    raise ValueError(t)


with open(PATH, "rb") as f:
    magic = f.read(4)
    ver = struct.unpack("<I", f.read(4))[0]
    n_tensors, n_kv = struct.unpack("<QQ", f.read(16))
    print("magic", magic, "version", ver, "tensors", n_tensors, "kv", n_kv)
    meta = {}
    for _ in range(n_kv):
        key = rd_str(f)
        t = struct.unpack("<I", f.read(4))[0]
        val = rd_val(f, t)
        short = key.replace("qwen2.", "").replace("general.", "")
        if short in WANT or key in WANT:
            meta[short] = val

for k, v in meta.items():
    print(f"  {k} = {v}")

L = int(meta.get("block_count", 28))
kvh = int(meta.get("attention.head_count_kv", 4))
kl = int(meta.get("attention.key_length", 128))
vl = int(meta.get("attention.value_length", 128))

per_token_f16 = L * kvh * (kl + vl) * 2
per_token_q8 = L * kvh * (kl + vl) * 1
print()
print(f"每 token KV: fp16 = {per_token_f16/1024:.1f} KiB | q8_0 = {per_token_q8/1024:.1f} KiB")
for name, size in (("fp16", per_token_f16), ("q8_0", per_token_q8)):
    for toks in (8_000, 32_000, 100_000, 500_000, 1_000_000):
        print(f"  {name}: {toks:>9,} tokens = {toks*size/1024**3:6.2f} GiB")