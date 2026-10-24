# -*- coding: utf-8 -*-
"""B evidence: the load path's block resets are gated; the dialogue reset is an exception.

  python -X utf8 load_probe.py
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import chat                                                       # noqa: E402
import chat_lease as CL                                           # noqa: E402
import memory_source as ms                                        # noqa: E402
import session_state as ss                                        # noqa: E402
from kvslots import KVEngine                                       # noqa: E402

PATH = os.path.join(ROOT, "kvmem", "sessions", "live.json")
res = {"schema": "chat_lease_load_v1", "pid": os.getpid(), "manifest": PATH}
con = ms.connect(chat.DB)
eng = KVEngine(chat.MODEL, n_ctx=chat.N_CTX, n_seq=8, gpu=99, kv="q8_0")
try:
    log_start = (len(open(CL.EVENT_LOG, encoding="utf-8").readlines())
                 if os.path.exists(CL.EVENT_LOG) else 0)
    leases = CL.GuardedLeases.from_manifest(eng, PATH)
    res["declared"] = {str(k): v for k, v in leases.declared.items()}
    rep = ss.restore_session(eng, con, PATH)
    res["restore"] = {"blocks": [b["block"] for b in rep["blocks"]],
                      "chat_n_tokens": rep["chat_n_tokens"],
                      "refused_during_restore": leases.counts["refused"],
                      "resets_during_restore": leases.counts["reset"]}
    res["referrers_after_restore"] = {b["block"]: leases.referrers(b["slot_id"] + 1)
                                      for b in rep["blocks"]}

    # criterion 1: through the PROXY (the same object session_state sees), reset a block
    # that the restored dialogue still references -> must be refused, engine untouched
    proxy = CL.RecordingEngine(eng, leases)
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
    # legal order still works
    leases.detach(0, victim["start"], victim["end"], site="load.detach")
    leases.reset(seq, site="load.reset_after_detach")
    res["legal_order"] = {"cells_after_reset": eng.n_tokens(seq),
                          "referrers": leases.referrers(seq)}
    res["surface"] = CL.proxy_surface(eng, leases)
    res["table_count_in_process"] = len(CL._LIVE)
    res["report"] = leases.report()
finally:
    eng.close()
    con.close()

rows = [json.loads(l) for l in open(CL.EVENT_LOG, encoding="utf-8")] \
    if os.path.exists(CL.EVENT_LOG) else []
rows = rows[log_start:]          # only this run
res["coverage"] = {
    "block_reset_gated": sum(1 for r in rows if r["site"] == "session_state.reset"
                             and r["kind"] == "reset" and int(r.get("seq") or 0) >= 1),
    "dialogue_reset_exception": sum(1 for r in rows if r["kind"] == "unguarded_reset"
                                    and int(r.get("seq") or 0) == 0
                                    and r.get("reason") == "dialogue_seq"),
    "block_reset_unguarded": sum(1 for r in rows if r["kind"] == "unguarded_reset"
                                 and int(r.get("seq") or 0) >= 1),
    "refusals_logged": sum(1 for r in rows if r["kind"] == "refused"),
    "range_mismatch": sum(1 for r in rows if r["kind"] == "range_mismatch"),
}
res["restore"]["declared_ranges_honoured"] = res["coverage"]["range_mismatch"] == 0
res["ok"] = bool(res["deliberate_reset"]["refused"]
                 and res["deliberate_reset"]["cells_unchanged"]
                 and res["legal_order"]["cells_after_reset"] == 0
                 and res["restore"]["refused_during_restore"] == 0
                 and res["surface"]["clean"]
                 and res["coverage"]["block_reset_unguarded"] == 0
                 and res["coverage"]["range_mismatch"] == 0)
json.dump(res, open(os.path.join(HERE, "run_load.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(json.dumps({k: res[k] for k in ("declared", "restore", "referrers_after_restore",
                                      "deliberate_reset", "legal_order", "surface",
                                      "coverage", "table_count_in_process", "ok")},
                 ensure_ascii=False, indent=1)[:2600])
print("[RUN] wrote run_load.json")
