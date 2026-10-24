P = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/curve_one.py"
s = open(P, encoding="utf-8").read()
old = '    r = eng.ask_at_topk(P.LIVE, q, ask_pos, k=a.k, n_predict=P.N_PREDICT)'
new = old + chr(10) + '    import sys as _s; print("ENV " + str({k: v for k, v in os.environ.items() if k.startswith("LLAMA_")}), file=_s.stderr)'
assert s.count(old) == 1
s = s.replace(old, new)
open(P, "w", encoding="utf-8").write(s)
print("patched curve_one")