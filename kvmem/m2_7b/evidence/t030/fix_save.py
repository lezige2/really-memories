import hashlib
KS = r"D:/llama-mem/tools/kvslots.py"
src = open(KS, encoding="utf-8").read()
bad = '    def save(self, seq, path):        return self.lib.kvshim_save(self.h, seq, path.encode("utf-8"))'
good = '    def save(self, seq, path):' + chr(10) + '        return self.lib.kvshim_save(self.h, seq, path.encode("utf-8"))'
assert src.count(bad) == 1
src = src.replace(bad, good)
open(KS, "wb").write(src.encode("utf-8"))
print("kvslots sha16:", hashlib.sha256(src.encode("utf-8")).hexdigest()[:16])