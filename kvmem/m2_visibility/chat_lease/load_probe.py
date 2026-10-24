# -*- coding: utf-8 -*-
"""B evidence: load-path block resets are gated; dialogue seq is the only exception.

  python -X utf8 load_probe.py
Logs: kvmem/lease_logs/events_<label>_<stamp>.jsonl (never in git; path+sha in the run json)
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import chat                                                       # noqa: E402
import chat_lease as CL                                           # noqa: E402
import memory_source as ms                                        # noqa: E402
import session_state as ss                                        # noqa: E402
from kvslots import KVEngine                                       # noqa: E402

PATH = os.path.join(ROOT, "kvmem", "sessions", "live.json")
res = {"schema": "chat_lease_load_v1", "pid": os.getpid(), "manifest": PATH,
       "strict": CL.STRICT}
con = ms.connect(chat.DB)
eng = KVEngine(chat.MODEL, n_ctx=chat.N_CTX, n_seq=8, gpu=99, kv="q8_0")
try:
    leases = CL.GuardedLeases.from_manifest(eng, PATH)
    res["bridged"] = CL.assert_bridged()
    res["declared"] = {str(k): v for k, v in leases.declared.items()}
    try:
        rep = ss.restore_session(eng, con, PATH)
        res["restore"] = {"ok": True, "blocks": [b["block"] for b in rep["blocks"]],
                          "chat_n_tokens": rep["chat_n_tokens"],
                          "refused_during_restore": leases.counts["refused"],
                          "resets_during_restore": leases.counts["reset"]}
    except CL.LeaseError as exc:
        res["restore"] = {"ok": False, "error": str(exc)}
        raise
    res["referrers_after_restore"] = {b["block"]: leases.referrers(b["slot_id"] + 1)
                                      for b in rep["blocks"]}

    proxy = CL.make_proxy(eng, leases)
    victim = rep["blocks"][0]
    seq = victim["slot_id"] + 1
    before = eng.n_tokens(seq)
    try:
        proxy.reset(seq)
        res["deliberate_reset"] = {"refused": False, "error": "NO EXCEPTION"}
    except CL.LeaseError as exc:
        res["deliberate_reset"] = {"refused": True, "seq": seq, "block": victim["block"],
                                   "message": str(exc), "cells_before": before,
                                   "cells_after": eng.n_tokens(seq),
                                   "cells_unchanged": eng.n_tokens(seq) == before}
    # the exception is ONLY seq 0: an unregistered non-zero seq must not slip through
    unreg = None
    for cand in range(3, 8):
        if cand not in leases.blocks:
            unreg = cand
            break
    try:
        proxy.reset(unreg)
        res["unregistered_reset"] = {"seq": unreg, "refused": False, "error": "NO EXCEPTION"}
    except CL.LeaseError as exc:
        res["unregistered_reset"] = {"seq": unreg, "refused": True, "message": str(exc)}
    leases.detach(0, victim["start"], victim["end"], site="load.detach")
    leases.reset(seq, site="load.reset_after_detach")
    res["legal_order"] = {"cells_after_reset": eng.n_tokens(seq),
                          "referrers": leases.referrers(seq)}
    res["surface"] = CL.surface(eng, leases)
    res["tables_in_process"] = len(CL._LIVE)
    res["report"] = leases.report()
finally:
    eng.close()
    con.close()

rows = CL.read_log()
res["log"] = CL.run_log()
res["events"] = [r for r in rows]
cov = {
    "block_reset_gated": sum(1 for r in rows if r["kind"] == "reset"
                             and r.get("site") == "session_state.reset"),
    "dialogue_reset_exception": sum(1 for r in rows if r["kind"] == "unguarded_reset"
                                    and r.get("reason") == "dialogue_seq"),
    "unregistered_seq_exception": sum(1 for r in rows if r["kind"] == "unguarded_reset"
                                      and r.get("reason") == "unregistered_seq"),
    "block_reset_unguarded": sum(1 for r in rows if r["kind"] == "unguarded_reset"
                                 and int(r.get("seq") or 0) >= 1
                                 and r.get("reason") != "unregistered_seq"),
    "refusals_logged": sum(1 for r in rows if r["kind"] == "refused"),
    "range_mismatch": sum(1 for r in rows if r["kind"] == "range_mismatch"),
    "bridge_installed": sum(1 for r in rows if r["kind"] == "bridge.installed"),
    "bridge_active_calls": sum(1 for r in rows if r["kind"] == "bridge.active"),
    "bridge_inactive_calls": sum(1 for r in rows if r["kind"] == "bridge.inactive"),
}
res["coverage"] = cov
res["ok"] = bool(res["deliberate_reset"]["refused"]
                 and res["deliberate_reset"]["cells_unchanged"]
                 and res["unregistered_reset"]["refused"]
                 and res["legal_order"]["cells_after_reset"] == 0
                 and res["restore"]["refused_during_restore"] == 0
                 and res["surface"]["clean"] and res["surface"]["isinstance_ok"]
                 and cov["block_reset_unguarded"] == 0
                 and cov["range_mismatch"] == 0
                 and (cov["bridge_installed"] + cov["bridge_inactive_calls"]) >= 1)
json.dump(res, open(os.path.join(HERE, "run_load.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(json.dumps({k: res[k] for k in ("bridged", "restore", "referrers_after_restore",
                                      "deliberate_reset", "unregistered_reset", "legal_order",
                                      "coverage", "log", "tables_in_process", "ok")},
                 ensure_ascii=False, indent=1))
print("[RUN] wrote run_load.json")
