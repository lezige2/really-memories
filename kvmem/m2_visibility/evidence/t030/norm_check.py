import hashlib, struct
A = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/kvshim_vk.baseline.dll"
B = r"D:/llama-mem/tools/kvshim_vk.dll"
a = open(A, "rb").read(); b = open(B, "rb").read()
off = 47838724
print("context a:", a[off-8:off+8].hex(), "| u32", struct.unpack_from("<I", a, off-2)[0])
print("context b:", b[off-8:off+8].hex(), "| u32", struct.unpack_from("<I", b, off-2)[0])
print("ts a", struct.unpack_from("<I", a, 0x80)[0], "ts b", struct.unpack_from("<I", b, 0x80)[0])


def norm(x):
    y = bytearray(x)
    y[0x80:0x84] = b"\x00\x00\x00\x00"
    y[off-2:off+2] = b"\x00\x00\x00\x00"
    return bytes(y)


print("normalized sha16 a:", hashlib.sha256(norm(a)).hexdigest()[:16])
print("normalized sha16 b:", hashlib.sha256(norm(b)).hexdigest()[:16])
print("NORMALIZED_EQUAL:", norm(a) == norm(b))