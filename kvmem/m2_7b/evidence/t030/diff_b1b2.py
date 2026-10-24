import struct
A = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/kvshim_vk_topk_b1.dll"
B = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/kvshim_vk_topk_b2.dll"
a = open(A, "rb").read(); b = open(B, "rb").read()
print("sizes", len(a), len(b))
d = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
print("differing bytes:", len(d))
print("offsets:", d[:20], "..." if len(d) > 20 else "")
for off in (0x80, 47838724):
    print("u32 @%d: b1=%s b2=%s" % (off, struct.unpack_from("<I", a, off)[0], struct.unpack_from("<I", b, off)[0]))
# group diff offsets into runs
runs = []
for i in d:
    if runs and i - runs[-1][1] <= 4:
        runs[-1][1] = i
    else:
        runs.append([i, i])
print("runs:", runs[:10])