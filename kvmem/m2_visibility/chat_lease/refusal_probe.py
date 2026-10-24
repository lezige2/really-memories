# -*- coding: utf-8 -*-
"""Real-engine refusal evidence for the chat.py lease wiring (acceptance 4 and 5).

No stub: the same GuardedLeases the product path uses, a real kvshim engine, a real block file.
  python -X utf8 refusal_probe.py
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import chat                                                       # noqa: E402
import chat_lease as CL                                           # noqa: E402
from kvslots import KVEngine                                       # noqa: E402

BLOCK_SEQ, LIVE = 1, 0
res = {"schema": "chat_lease_refusal_v1", "pid": os.getpid(),
       "block": os.path.join(ROOT, "kvmem", "blocks", "profile.kvmem"),
       "refusal_log": CL.REFUSAL_LOG}
eng = KVEngine(chat.MODEL, n_ctx=chat.N_CTX, n_seq=8, gpu=99, kv="q8_0")
try:
    leases = CL.GuardedLeases(eng, site_prefix="probe")
    leases.register_block(BLOCK_SEQ, "profile")
    leases.reset(BLOCK_SEQ, site="probe.place.fresh")
    import memory_source as ms
    con = ms.connect(chat.DB)
    row = [r for r in ms.block_rows(con) if r[1] == "profile"][0]
    con.close()
    cells = ms.load_into(eng, row, BLOCK_SEQ)
    lo, hi = chat.CHAT_START - cells, chat.CHAT_START
    base = eng.pos_max(BLOCK_SEQ) + 1 - cells
    if base != lo and eng.repos_local(BLOCK_SEQ, lo - base) != cells:
        raise SystemExit("repos refused")
    leases.attach(BLOCK_SEQ, LIVE, lo, hi, site="probe.attach")
    before = eng.n_tokens(BLOCK_SEQ)
    res["before_refusal"] = {"cells_block_seq": before, "referrers": leases.referrers(BLOCK_SEQ),
                             "range": [lo, hi]}
    try:
        leases.reset(BLOCK_SEQ, site="probe.reset_while_attached")
        res["refused"] = False
        res["error"] = "NO EXCEPTION -- the guard did not fire"
    except CL.LeaseError as exc:
        res["refused"] = True
        res["message"] = str(exc)
    res["after_refusal"] = {"cells_block_seq": eng.n_tokens(BLOCK_SEQ),
                            "cells_unchanged": eng.n_tokens(BLOCK_SEQ) == before,
                            "referrers": leases.referrers(BLOCK_SEQ)}
    # the legal order still works, and the assertion is visible
    leases.detach(LIVE, lo, hi, site="probe.detach")
    leases.reset(BLOCK_SEQ, site="probe.reset_after_detach")
    res["after_detach_reset"] = {"cells": eng.n_tokens(BLOCK_SEQ),
                                 "reset_allowed": True}
    res["report"] = leases.report()
finally:
    eng.close()

res["log_lines"] = [json.loads(l) for l in open(CL.REFUSAL_LOG, encoding="utf-8")
                    if l.strip()] if os.path.exists(CL.REFUSAL_LOG) else []
res["ok"] = bool(res.get("refused") and res["after_refusal"]["cells_unchanged"]
                 and res["after_detach_reset"]["cells"] == 0
                 and res["report"]["all_sites_asserted_empty"])
out = os.path.join(HERE, "run_refusal.json")
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps({k: res[k] for k in ("refused", "message", "before_refusal", "after_refusal",
                                      "after_detach_reset", "ok")}, ensure_ascii=False, indent=1))
print("[RUN] wrote", out)
