# -*- coding: utf-8 -*-
"""Bridge evidence (A) rerun under the strict rules.

  python -X utf8 bridge_probe.py  -> run_bridge.json

Same process on purpose: it shows both sides of the wire --
  * save_session is recorded (drop/share reach the table),
  * restore_session WITHOUT detaching is now REFUSED (the hazard this guard exists for),
  * after the legal detach, restore succeeds and referrers still match,
  * a deliberate reset of a referenced block is refused; detach->reset is allowed.
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

PATH = os.path.join(ROOT, "kvmem", "sessions", "bridge.json")


def place(eng, leases, rows):
    blocks = []
    for i, row in enumerate(rows, start=1):
        leases.register_block(i, row[1])
        leases.reset(i, site="bridge.place.fresh")
        n = ms.load_into(eng, row, i)
        end = chat.CHAT_START - (i - 1) * chat.SLOT
        lo = end - n
        base = eng.pos_max(i) + 1 - n
        if base != lo and eng.repos_local(i, lo - base) != n:
            raise SystemExit("repos_local refused")
        leases.attach(i, 0, lo, end, site="bridge.attach")
        blocks.append({"seq": i, "source_id": row[0], "name": row[1], "lo": lo, "hi": end,
                       "n_tokens": n, "path": row[6]})
    return blocks


def per_seq(eng, leases, mounted):
    out = []
    for b in mounted:
        seq = b["slot_id"] + 1
        out.append({"block": b["block"], "seq": seq, "expect_referrers": [0],
                    "table_referrers": leases.referrers(seq),
                    "engine_cells": eng.n_tokens(seq),
                    "match": leases.referrers(seq) == [0]})
    return out


res = {"schema": "chat_lease_bridge_v2", "pid": os.getpid(), "path": PATH,
       "strict": CL.STRICT, "bridge_env": os.environ.get("CHAT_LEASE_BRIDGE", "1")}
con = ms.connect(chat.DB)
rows_list = [r for r in ms.block_rows(con) if r[5] is not None][:2]
eng = KVEngine(chat.MODEL, n_ctx=chat.N_CTX, n_seq=8, gpu=99, kv="q8_0")
try:
    leases = CL.GuardedLeases(eng, site_prefix="bridge")
    res["bridged"] = CL.assert_bridged()
    blocks = place(eng, leases, rows_list)
    eng.ask(0, chat.QUESTIONS[0], n_predict=16, pos=chat.CHAT_START)
    man = ss.save_session(eng, con, PATH, blocks, anchor=chat.CHAT_START,
                          slot_capacity=chat.SLOT)
    mounted = man["placement"]["blocks"]
    res["after_save"] = {"mounted": [b["block"] for b in mounted],
                         "per_seq": per_seq(eng, leases, mounted)}
    res["after_save"]["all_match"] = all(b["match"] for b in res["after_save"]["per_seq"])

    try:
        ss.restore_session(eng, con, PATH)
        res["restore_without_detach"] = {"refused": False, "error": "NO EXCEPTION"}
    except CL.LeaseError as exc:
        res["restore_without_detach"] = {"refused": True, "message": str(exc)}

    for b in mounted:
        leases.detach(0, b["start"], b["end"], site="bridge.detach_all")
    rep = ss.restore_session(eng, con, PATH)
    res["after_restore"] = {"blocks": [b["block"] for b in rep["blocks"]],
                            "chat_n_tokens": rep["chat_n_tokens"],
                            "per_seq": per_seq(eng, leases, rep["blocks"])}
    res["after_restore"]["all_match"] = all(b["match"] for b in res["after_restore"]["per_seq"])

    proxy = CL.make_proxy(eng, leases)
    victim = rep["blocks"][0]
    seq = victim["slot_id"] + 1
    before = eng.n_tokens(seq)
    try:
        proxy.reset(seq)
        res["deliberate_reset"] = {"refused": False, "error": "NO EXCEPTION"}
    except CL.LeaseError as exc:
        res["deliberate_reset"] = {"refused": True, "message": str(exc),
                                   "cells_before": before, "cells_after": eng.n_tokens(seq),
                                   "cells_unchanged": eng.n_tokens(seq) == before}
    leases.detach(0, victim["start"], victim["end"], site="bridge.legal.detach")
    leases.reset(seq, site="bridge.legal.reset")
    res["legal_order"] = {"cells_after_reset": eng.n_tokens(seq),
                          "referrers": leases.referrers(seq)}
    res["surface"] = CL.surface(eng, leases)
    res["report"] = leases.report()
finally:
    eng.close()
    con.close()

rows = CL.read_log()
res["log"] = CL.run_log()
res["coverage"] = {
    "bridge_active_calls": sum(1 for r in rows if r["kind"] == "bridge.active"),
    "bridge_inactive_calls": sum(1 for r in rows if r["kind"] == "bridge.inactive"),
    "refusals": sum(1 for r in rows if r["kind"] == "refused"),
    "unguarded_unregistered": sum(1 for r in rows if r["kind"] == "unguarded_reset"
                                  and r.get("reason") == "unregistered_seq"),
    "range_mismatch": sum(1 for r in rows if r["kind"] == "range_mismatch"),
}
res["ok"] = bool(res["after_save"]["all_match"] and res["after_restore"]["all_match"]
                 and res["restore_without_detach"]["refused"]
                 and res["deliberate_reset"]["refused"]
                 and res["deliberate_reset"]["cells_unchanged"]
                 and res["legal_order"]["cells_after_reset"] == 0
                 and res["surface"]["clean"]
                 and res["coverage"]["range_mismatch"] == 0)
json.dump(res, open(os.path.join(HERE, "run_bridge.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(json.dumps({k: res[k] for k in ("bridged", "after_save", "restore_without_detach",
                                      "after_restore", "deliberate_reset", "legal_order",
                                      "coverage", "log", "ok")},
                 ensure_ascii=False, indent=1)[:2400])
print("[RUN] wrote run_bridge.json")
