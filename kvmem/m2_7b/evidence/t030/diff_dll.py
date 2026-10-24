import hashlib, struct, os, time
A = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/kvshim_vk.baseline.dll"
B = r"D:/llama-mem/tools/kvshim_vk.dll"
a = open(A, "rb").read(); b = open(B, "rb").read()
print("sizes", len(a), len(b))
diff = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
print("differing bytes:", len(diff))
print("first 20 offsets:", diff[:20])
print("last 5 offsets:", diff[-5:])
# PE/FILE header fields
pe = struct.unpack_from("<I", a, 0x3C)[0]
ts = struct.unpack_from("<I", a, pe + 8)[0]
ts2 = struct.unpack_from("<I", b, pe + 8)[0]
print("e_lfanew", hex(pe))
print("TimeDateStamp baseline", ts, time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts)), "UTC")
print("TimeDateStamp rebuilt ", ts2, time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts2)), "UTC")
for f in ("D:/llama-mem/llama.cpp/src/llama-kv-cache.cpp", "D:/llama-mem/tools/kvshim.cpp",
          "D:/llama-mem/build-vulkan/src/libllama.a"):
    st = os.stat(f)
    print("%-55s mtime %s size %d" % (f, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)), st.st_size))
# how many diffs fall outside the PE headers region (first 0x400 bytes)
inside = [d for d in diff if d < 0x400]
print("diffs inside first 0x400:", len(inside))
# build-id / rdata scan: count diffs in ranges of 4KB
from collections import Counter
c = Counter(d // 4096 for d in diff)
print("top pages:", c.most_common(8))