CPP = r"D:/llama-mem/llama.cpp/src/llama-kv-cache.cpp"
ADD = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/win_add.txt"
s = open(CPP, encoding="utf-8").read()
add = open(ADD, encoding="utf-8").read()
anchor = '                                (long long) first_pos, (long long) last_pos);' + chr(10)
assert s.count(anchor) == 1, s.count(anchor)
s = s.replace(anchor, anchor + add + chr(10))
open(CPP, "wb").write(s.encode("utf-8"))
print("win line inserted; MASKDBG-WIN count:", s.count("MASKDBG-WIN"))