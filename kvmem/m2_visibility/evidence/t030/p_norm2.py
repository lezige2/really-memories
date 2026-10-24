P = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/norm_pe.py"
s = open(P, encoding="utf-8").read()
s = s.replace("sites = [off for _n, off in detail]", "sites = [off for _n, off, _v in detail]")
open(P, "w", encoding="utf-8").write(s)
print("fixed unpack")