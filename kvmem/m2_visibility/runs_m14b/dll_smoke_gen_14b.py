# -*- coding: utf-8 -*-
import os, sys, json, time, hashlib
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P

P.MODEL = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
eng = P.open_engine()
out = {"loaded_path": eng.lib._name}
def sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()

for name in ("home", "project", "habit"):
    t = P.FULL[name]["text"]
    eng.reset(2)
    n = eng.write_at(2, t, 0, True)
    rec = {"text": t, "cells_to_encode": n, "n_tokens": eng.n_tokens(2), "pos_max": eng.pos_max(2)}
    # contiguous generation: ask immediately after the block's last cell
    t1 = time.time()
    ans = eng.ask(2, P.FULL[name]["q"], n_predict=24, pos=n)
    dt = time.time() - t1
    rec.update({"ask_pos": n, "answer": ans, "answer_sha256": sha(ans),
                "seconds": round(dt, 2), "tok_per_s": round(24/dt, 2) if dt > 0 else None,
                "fact_ok": P.fact_ok(P.FULL[name]["fact"], ans)})
    out[name] = rec
print(json.dumps(out, ensure_ascii=False, indent=1))
