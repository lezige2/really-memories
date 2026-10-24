import hashlib
KS = r"D:/llama-mem/tools/kvslots.py"
B = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/bind.txt"
src = open(KS, encoding="utf-8").read()
add = open(B, encoding="utf-8").read()
NL = chr(10)
anchor = "    def save(self, seq, path):" + NL
assert src.count(anchor) == 1, src.count(anchor)
src = src.replace(anchor, add)
open(KS, "wb").write(src.encode("utf-8"))
print("kvslots.py sha16:", hashlib.sha256(src.encode("utf-8")).hexdigest()[:16])
print("ask_at_topk in kvslots:", src.count("kvshim_ask_at_topk"))