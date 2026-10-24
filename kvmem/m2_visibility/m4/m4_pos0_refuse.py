# -*- coding: utf-8 -*-
"""M4 §12.6 -- the position-0 bus, one PASS and one REFUSAL, on a real engine.

Run in its own process (one engine at a time).
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "kvmem", "m2_visibility", "m2"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "engine"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "m3"), HERE):
    sys.path.insert(0, p)
import m2_visibility_probe as P
import _driver_m2
import m3_lease as L
import m4_store as S

SEQ = 2
DB = os.path.join(HERE, "_pos0.db")
TEXT_A = "我住在广陵路 12 号 2 单元 602。"
TEXT_B = "我车牌是浙B-3F19K。"

res = {"schema": "m4_pos0_v1", "pid": os.getpid(), "seq": SEQ}
if os.path.exists(DB):
    os.remove(DB)
con, _ = S.connect(DB)
bus = S.Position0Bus(con)
eng = P.open_engine()
try:
    leases = L.BlockLeases(eng)
    leases.register_block(SEQ, "pos0_A")
    leases.safe_reset_all(range(P.N_SEQ))

    # PASS: fresh sequence, nothing at position 0
    cells0 = P.cell_scan(eng, SEQ)[0]
    ok, why = bus.check_before("pos0_A", "seq%d" % SEQ, cells0)
    res["pass"] = {"cells_before": cells0, "ok": ok, "detail": why}
    if not ok:
        raise SystemExit("unexpected refusal on a fresh sequence: " + why)
    n = eng.write_at(SEQ, TEXT_A, 0)
    pos = P.cell_scan(eng, SEQ)[1]
    ok_after, why_after = bus.check_after(pos, n)
    path = os.path.join(HERE, "blocks", "pos0_A.kvmem")
    eng.save(SEQ, path)
    S.add_block(con, "pos0_A", S.add_source(con, "pos0_A", "text", TEXT_A, 1),
                path, n, 0, "seq%d" % SEQ)
    res["pass"].update({"tokens": n, "position0_after": {"ok": ok_after, "detail": why_after}})

    # REFUSAL: the same sequence already owns position 0
    cells1 = P.cell_scan(eng, SEQ)[0]
    refuses = []
    ok2, why2 = bus.check_before("pos0_B", "seq%d" % SEQ, cells1)
    refuses.append({"guard": "engine_cells", "ok": ok2, "detail": why2})
    # and the DB claim fires on its own, even with an empty engine range
    ok3, why3 = bus.check_before("pos0_B", "seq%d" % SEQ, 0)
    refuses.append({"guard": "db_claim", "ok": ok3, "detail": why3})
    # the lease table refuses a reset of the block that owns those cells
    leases.attach(SEQ, 0, 0, n)
    try:
        leases.reset(SEQ)
        lease_refused = False
        msg = ""
    except L.LeaseError as exc:
        lease_refused = True
        msg = str(exc)
    res["refuse"] = {"guards": refuses,
                     "both_guards_refuse": (not ok2) and (not ok3),
                     "lease_refuses_reset_while_attached": lease_refused,
                     "lease_message": msg,
                     "engine_cells_unchanged": P.cell_scan(eng, SEQ)[0] == cells1,
                     "cells_after_refusals": P.cell_scan(eng, SEQ)[0]}
    leases.detach(0, 0, n)
finally:
    eng.close()
    con.close()
print("@@JSON@@" + json.dumps(res, ensure_ascii=False), flush=True)
