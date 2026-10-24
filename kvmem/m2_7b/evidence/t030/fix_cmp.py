import re
P = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/cmp_fn.py"
s = open(P, encoding="utf-8").read()
s = s.replace(', "n_ctx": eng.n_ctx()', '')
s = s.replace('os.environ["LLAMA_KV_MASK_LAYOUT"] = "cmp"', 'os.environ["LLAMA_KV_MASK_LAYOUT"] = "envtest"')
s = s.replace('q = P.FULL[seg["block_id"]]["q"]', 'os.environ["LLAMA_KV_MASK_Q"] = "envtest"' + chr(10) + 'q = P.FULL[seg["block_id"]]["q"]')
open(P, "w", encoding="utf-8").write(s)
print("patched cmp_fn")