import hashlib
KS = r"D:/llama-mem/tools/kvslots.py"
src = open(KS, encoding="utf-8").read()
NL = chr(10)
old = '        n = self.lib.kvshim_ask_at_topk(self.h, seq, t, pos, n_predict, k, probs, toks, buf, cap)'
assert src.count(old) == 1
new = (NL.join([
'        f = self.lib.kvshim_ask_at_topk',
                '        f.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int,',
                '                      ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_float),',
                '                      ctypes.POINTER(ctypes.c_int), ctypes.c_char_p, ctypes.c_int]',
                '        f.restype = ctypes.c_int',
                '        n = f(ctypes.c_void_p(self.h), seq, t, pos, n_predict, k, probs, toks,',
                '              buf, cap)']))
src = src.replace(old, new)
open(KS, "wb").write(src.encode("utf-8"))
print("kvslots sha16:", hashlib.sha256(src.encode("utf-8")).hexdigest()[:16])