# -*- coding: utf-8 -*-
"""Bridge evidence: does the lease table see session_state's own share/drop?

One engine, one table, one real save_session -> restore_session round trip.

  python -X utf8 bridge_probe.py
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

PATH = os.path.join(ROOT, "kvmem", "sessions", "bridge.json")


def place(eng, leases, rows):
    """Same geometry as chat._place_slots, but through THIS table (no second table)."""
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


def snapshot(eng, leases, mounted_names, rows):
    """Per-seq view: what the table believes vs what the engine and the manifest show."""
    out = []
    for name, row in rows.items():
        seq = [b for b in mounted_names if b["block"] == name]
        want_refs = [0] if seq else []
        out.append({"block": name, "seq": seq[0]["slot_id"] + 1 if seq else None,
                    "expect_referrers": want_refs,
                    "table_referrers": leases.referrers(seq[0]["slot_id"] + 1) if seq else None,
                    "engine_cells": eng.n_tokens(seq[0]["slot_id"] + 1) if seq else None,
                    "match": (sorted(leases.referrers(seq[0]["slot_id"] + 1)) == want_refs)
                    if seq else True})
    return out


res = {"schema": "chat_lease_bridge_v1", "pid": os.getpid(), "path": PATH}
con = ms.connect(chat.DB)
rows_list = [r for r in ms.block_rows(con) if r[5] is not None][:2]
rows = {r[1]: r for r in rows_list}
eng = KVEngine(chat.MODEL, n_ctx=chat.N_CTX, n_seq=8, gpu=99, kv="q8_0")
try:
    leases = CL.GuardedLeases(eng, site_prefix="bridge")   # installs the bridge
    res["bridge_installed"] = bool(getattr(ss.save_session, "_lease_bridge", False))
    blocks = place(eng, leases, rows_list)
    # one question so the chat sequence owns cells (save writes a real chat state)
    eng.ask(0, chat.QUESTIONS[0], n_predict=16, pos=chat.CHAT_START)
    res["chat_cells_before_save"] = eng.n_tokens(0)

    man = ss.save_session(eng, con, PATH, blocks, anchor=chat.CHAT_START,
                          slot_capacity=chat.SLOT)
    mounted = man["placement"]["blocks"]
    res["after_save"] = {"manifest_mounted": [b["block"] for b in mounted],
                         "per_seq": snapshot(eng, leases, mounted, rows),
                         "table": leases.status()}
    res["after_save"]["all_match"] = all(b["match"] for b in res["after_save"]["per_seq"])

    rep = ss.restore_session(eng, con, PATH)
    mounted2 = rep["blocks"]
    res["after_restore"] = {"report_blocks": [b["block"] for b in mounted2],
                            "chat_n_tokens": rep["chat_n_tokens"],
                            "per_seq": snapshot(eng, leases, mounted2, rows),
                            "table": leases.status()}
    res["after_restore"]["all_match"] = all(b["match"] for b in res["after_restore"]["per_seq"])

    victim = mounted2[0]
    seq = victim["slot_id"] + 1
    before_cells = eng.n_tokens(seq)
    try:
        leases.reset(seq, site="bridge.reset_while_attached")
        res["after_roundtrip_refusal"] = {"refused": False,
                                          "error": "NO EXCEPTION -- table was out of sync"}
    except CL.LeaseError as exc:
        res["after_roundtrip_refusal"] = {"refused": True, "message": str(exc),
                                          "cells_after": eng.n_tokens(seq),
                                          "cells_unchanged": eng.n_tokens(seq) == before_cells,
                                          "block": victim["block"]}
    leases.detach(0, victim["start"], victim["end"], site="bridge.detach")
    leases.reset(seq, site="bridge.reset_after_detach")
    res["legal_order"] = {"cells_after_reset": eng.n_tokens(seq),
                          "referrers": leases.referrers(seq)}
    res["report"] = leases.report()
finally:
    eng.close()
    con.close()

res["events"] = {}
for line in (open(CL.EVENT_LOG, encoding="utf-8") if os.path.exists(CL.EVENT_LOG) else []):
    r = json.loads(line)
    k = "%s/%s" % (r["site"], r["kind"])
    res["events"][k] = res["events"].get(k, 0) + 1
res["ok"] = bool(res["after_save"]["all_match"] and res["after_restore"]["all_match"]
                 and res["after_roundtrip_refusal"].get("refused")
                 and res["after_roundtrip_refusal"].get("cells_unchanged")
                 and res["legal_order"]["cells_after_reset"] == 0)
json.dump(res, open(os.path.join(HERE, "run_bridge.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(json.dumps({k: res[k] for k in ("bridge_installed", "after_save", "after_restore",
                                      "after_roundtrip_refusal", "legal_order", "ok")},
                 ensure_ascii=False, indent=1)[:3000])
print("[RUN] wrote run_bridge.json")
