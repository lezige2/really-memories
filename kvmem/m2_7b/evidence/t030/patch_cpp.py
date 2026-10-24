import hashlib
CPP = r"D:/llama-mem/tools/kvshim.cpp"
ADD = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/cpp_add.txt"
src = open(CPP, encoding="utf-8").read()
add = open(ADD, encoding="utf-8").read()
NL = chr(10)
anchor = "#include <algorithm>" + NL
assert src.count(anchor) == 1
src = src.replace(anchor, anchor + "#include <cmath>" + NL)
tail = "// ---------------------------------------------------------------- state <-> file"
assert src.count(tail) == 1
src = src.replace(tail, add.lstrip(NL) + NL + tail)
open(CPP, "wb").write(src.encode("utf-8"))
print("kvshim.cpp lines:", len(src.split(NL)) - 1)
print("sha16:", hashlib.sha256(src.encode("utf-8")).hexdigest()[:16])
print("ask_at_topk occurrences:", src.count("kvshim_ask_at_topk"))