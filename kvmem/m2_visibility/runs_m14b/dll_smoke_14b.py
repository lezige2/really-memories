# -*- coding: utf-8 -*-
import os, sys, json, time, hashlib
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P

P.MODEL = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
out = {"model": P.MODEL, "model_size": os.path.getsize(P.MODEL),
       "n_ctx": P.N_CTX, "n_seq": P.N_SEQ, "gpu": P.GPU, "kv": P.KV}

t0 = time.time()
eng = P.open_engine()
out["open_seconds"] = round(time.time() - t0, 1)
out["loaded_path"] = getattr(eng.lib, "_name", "?")
h = hashlib.sha256()
with open(out["loaded_path"], "rb") as f:
    for c in iter(lambda: f.read(1 << 20), b""):
        h.update(c)
out["loaded_dll_sha256"] = h.hexdigest()
out["loaded_dll_size"] = os.path.getsize(out["loaded_path"])

out["bytes_per_token"] = eng.bytes_per_token()
out["pool_bytes"] = eng.pool_bytes()

home = P.FULL["home"]["text"]
try:
    eng.reset(1)
    n_meas = P.measure(eng, home)
    out["measure_home_cells"] = n_meas
    n_written = eng.write_at(1, home, 0, True)
    out["write_home_cells"] = n_written
    out["n_tokens_after_write"] = eng.n_tokens(1)
    out["pos_max_after_write"] = eng.pos_max(1)
except Exception as e:
    out["write_error"] = "%s: %s" % (type(e).__name__, e)

try:
    t1 = time.time()
    ans = eng.ask(1, P.FULL["home"]["q"], n_predict=P.N_PREDICT, pos=P.CHAT)
    dt = time.time() - t1
    out["ask_seconds"] = round(dt, 2)
    out["ask_pos"] = P.CHAT
    out["ask_n_predict"] = P.N_PREDICT
    out["answer"] = ans
    out["answer_sha256"] = hashlib.sha256(ans.encode("utf-8")).hexdigest()
    out["approx_tok_per_s"] = round(P.N_PREDICT / dt, 2) if dt > 0 else None
except Exception as e:
    out["ask_error"] = "%s: %s" % (type(e).__name__, e)

eng.close() if hasattr(eng, "close") else None
print(json.dumps(out, ensure_ascii=False, indent=1))
