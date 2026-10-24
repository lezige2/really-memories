# -*- coding: utf-8 -*-
import hashlib, json, os, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"D:/llama-mem/kvmem/m2_visibility/runs_t033")
sys.path.insert(0, r"D:/llama-mem/tools")
import _judge_t033 as J
import m2_visibility_probe as P

def sha(x): return hashlib.sha256(x.encode("utf-8")).hexdigest()
def load(tag): return json.load(open(os.path.join(D, "out", tag + ".json"), encoding="utf-8"))

CELLS = [("run0", "run0"), ("E", "E"), ("F", "F"), ("X1", "X1"), ("B57", "B57")]
res = {"schema": "np64_analysis_v1", "cells": [], "bookkeeping": []}

for cell, tag in CELLS:
    d24, d64 = load(tag + "_r1"), load("np64_" + tag + "_r1")
    a24, a64 = d24["answers"][0], d64["answers"][0]
    rec = {"cell": cell,
           "np24": {"answer": a24["answer"], "sha256": sha(a24["answer"]), "ok": a24["ok"],
                    "judge": J.judge(a24["question"], a24["answer"]),
                    "n_predict": d24["runner"].get("n_predict"),
                    "tok_after": a24["kvshim_n_tokens_after_ask"]},
           "np64": {"answer": a64["answer"], "sha256": sha(a64["answer"]), "ok": a64["ok"],
                    "judge": J.judge(a64["question"], a64["answer"]),
                    "n_predict": d64["runner"].get("n_predict"),
                    "n_predict_changed": d64["runner"].get("n_predict_changed"),
                    "tok_after": a64["kvshim_n_tokens_after_ask"]},
           "np24_is_prefix_of_np64": a64["answer"].startswith(a24["answer"]),
           "np24_eq_np64": a24["answer"] == a64["answer"],
           "r1_eq_r2_np64": load("np64_" + tag + "_r2")["answers"][0]["answer"] == a64["answer"]}
    res["cells"].append(rec)

# pairwise divergence among the four cells at np64, char and token level
eng = P.open_engine()
try:
    def toks(s):
        import ctypes
        eng.lib.kvshim_tokenize.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                            ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        eng.lib.kvshim_tokenize.restype = ctypes.c_int
        b = (ctypes.c_int * 4096)()
        n = int(eng.lib.kvshim_tokenize(eng.h, s.encode("utf-8"), b, 4096))
        return [int(b[i]) for i in range(n)]
    four = {c: load("np64_" + c + "_r1")["answers"][0]["answer"] for c, _ in CELLS if c != "run0"}
    pairs = []
    names = list(four)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            x, y = four[names[i]], four[names[j]]
            ci = next((k for k in range(min(len(x), len(y))) if x[k] != y[k]), min(len(x), len(y)))
            tx, ty = toks(x), toks(y)
            ti = next((k for k in range(min(len(tx), len(ty))) if tx[k] != ty[k]), min(len(tx), len(ty)))
            pairs.append({"a": names[i], "b": names[j], "same": x == y,
                          "first_diff_char_index": ci, "first_diff_token_index": ti,
                          "a_token": tx[ti] if ti < len(tx) else None,
                          "b_token": ty[ti] if ti < len(ty) else None,
                          "common_prefix": x[:ci]})
    res["pairwise_np64"] = pairs
    res["all_four_identical_np64"] = len({v for v in four.values()}) == 1
    res["all_four_identical_np24"] = len({load(c + "_r1")["answers"][0]["answer"]
                                          for c, _ in CELLS if c != "run0"}) == 1
finally:
    eng.close()

json.dump(res, open(os.path.join(D, "np64_analysis.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2, default=str)

print("| cell | 24 sha16 | 64 sha16 | 24-is-prefix-of-64 | r1==r2 @64 | ok24/ok64 |")
print("|---|---|---|---|---|---|")
for r in res["cells"]:
    print("| %s | %s | %s | %s | %s | %s/%s |" % (
        r["cell"], r["np24"]["sha256"][:16], r["np64"]["sha256"][:16],
        r["np24_is_prefix_of_np64"], r["r1_eq_r2_np64"], r["np24"]["ok"], r["np64"]["ok"]))
print()
print("=== full answers @64 ===")
for r in res["cells"]:
    print("%-5s %r" % (r["cell"], r["np64"]["answer"]))
print()
print("all four identical @24:", res["all_four_identical_np24"],
      "| @64:", res["all_four_identical_np64"])
print()
print("=== pairwise @64 ===")
for p in res["pairwise_np64"]:
    print("%-4s vs %-4s same=%-5s first_diff char=%d token=%d common_prefix=%r"
          % (p["a"], p["b"], p["same"], p["first_diff_char_index"],
             p["first_diff_token_index"], p["common_prefix"]))
