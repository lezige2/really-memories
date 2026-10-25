# -*- coding: utf-8 -*-
"""站点 3 的前提验证：detach 之后块 seq 自己的 cell 还在吗？reset 之后呢？

只回答一件事：**「删掉 m1.unmount.after_detach 的 reset ⇒ 块 seq 仍持有 cell」这个前提成立吗**。
（站点 1、2、4 的前提已被证伪：kvshim.cpp:572 kvshim_load 第一句就是 kvshim_reset。）
"""
import hashlib, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:\llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
import chat as C

def sha16(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]

eng = C.KVEngine(C.MODEL, n_ctx=C.N_CTX, n_seq=8, gpu=99, kv="q8_0")
con = C.ms.connect(C.DB); rows = C._rows_for_session(con, limit=2); con.close()
rec = {"schema": "m4c_site3_premise_v1",
       "question": "detach 后块 seq 是否仍持有 cell（⇒ reset 是否承重）",
       "provenance": {"chat_py_sha16": sha16(os.path.join(ROOT, "tools", "chat.py")),
                      "probe_sha16": sha16(os.path.abspath(__file__)),
                      "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
       "steps": []}
try:
    blocks = C._place_slots(eng, rows)
    leases = C.GuardedLeases(eng, site_prefix="m4c")
    for b in blocks:
        leases.register_block(b["seq"], b["name"])
    b = blocks[0]
    rec["steps"].append({"step": "placed", "n_tokens": int(eng.n_tokens(b["seq"])),
                         "pos_max": int(eng.pos_max(b["seq"]))})
    leases.detach(0, b["lo"], b["hi"], site="m4c.detach")
    rec["steps"].append({"step": "after detach (对话 seq 不再引用)",
                         "n_tokens": int(eng.n_tokens(b["seq"])),
                         "pos_max": int(eng.pos_max(b["seq"])),
                         "cells_of": int(leases.cells_of(b["seq"]))})
    try:
        leases.reset(b["seq"], site="m4c.reset_while_detached")
        rec["steps"].append({"step": "after reset", "n_tokens": int(eng.n_tokens(b["seq"])),
                             "pos_max": int(eng.pos_max(b["seq"])),
                             "cells_of": int(leases.cells_of(b["seq"]))})
    except Exception as exc:
        rec["reset_error"] = str(exc)
    d0, d1 = rec["steps"][1], rec["steps"][2] if len(rec["steps"]) > 2 else {}
    rec["verdict"] = ("站点 3 前提成立：detach 不释放块 seq 的 cell，只有 reset 释放"
                      if rec["steps"][1]["cells_of"] == b["n_tokens"] else
                      "站点 3 前提也不成立：detach 之后块 seq 已空")
finally:
    out = os.path.join(HERE, "out", "PREMISE-SITE3.json")
    json.dump(rec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
    print(json.dumps(rec, ensure_ascii=False, indent=2, default=str)[:1400])
    try: eng.close()
    except Exception: pass
