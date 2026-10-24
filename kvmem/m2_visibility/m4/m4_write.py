# -*- coding: utf-8 -*-
"""M4 -- the real write path: judge -> segment -> write_at(seq, text, 0) -> save -> SQLite,
with the M3 lease table wired into the LIVE path (not a unit test).

L6: the block owns position 0 exclusively. The bus assertion runs twice: before the write
(target range empty in the engine AND unclaimed in the DB) and after it (scan == [0, n)).

  python -u -X utf8 kvmem/m2_visibility/m4/m4_write.py --out run_m4_write.json
"""
import argparse, hashlib, json, os, sqlite3, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "kvmem", "m2_visibility", "m2"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "m3"), HERE):
    sys.path.insert(0, p)
import m2_visibility_probe as P                                    # noqa: E402
import _driver_m2 as M2                                           # noqa: E402
import m3_lease as L                                              # noqa: E402
import m4_extract as X                                            # noqa: E402
import m4_store as S                                              # noqa: E402

BLOCK_SEQ = 1
LIVE = 0
POS0 = 0
TS = "2026-10-25T09:00:00"
DLL_WANT = "9edbafa1507006144".strip()[:-1] + "d99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c"
DLL_WANT = "9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c"
ASK_ANCHOR = 4096
ASK_Q = "我住在哪？"
HIT = "广陵路 12 号 2 单元 602"

SAMPLE = [
    {"role": "user", "text": "你好呀！", "ts": TS},
    {"role": "assistant", "text": "你好！有什么可以帮你？", "ts": TS},
    {"role": "user", "text": "我住在广陵路 12 号 2 单元 602。", "ts": TS},
    {"role": "user", "text": "我每天早上七点半出门，别在那个时候给我推消息。", "ts": TS},
    {"role": "user", "text": "我车牌是浙B-3F19K。", "ts": TS},
    {"role": "assistant", "text": "记住了。", "ts": TS},
    {"role": "user", "text": "帮我查下明天天气。", "ts": TS},
    {"role": "user", "text": "谢谢，就这样吧。", "ts": TS},
    {"role": "user", "text": "对了，我女儿小名叫豆豆，下周三她生日，提醒我买蛋糕。", "ts": TS},
]


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="run_m4_write.json")
    ap.add_argument("--db", default=os.path.join(HERE, "m4_memory.db"))
    ap.add_argument("--blocks", default=os.path.join(HERE, "blocks"))
    a = ap.parse_args()
    os.makedirs(a.blocks, exist_ok=True)
    res = {"schema": "m4_write_v1", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "line": "judge -> segment -> write_at(seq,text,0) -> save -> SQLite (+ leases in the live path)",
           "pos_max_policy": "only kvshim_seq_pos_max_raw counts; kvshim_pos_max reports -1 for "
                            "seq_cp-built sequences (M3 §0.5 warning 1)",
           "ts": TS, "block_seq": BLOCK_SEQ, "live_seq": LIVE, "position0": POS0}
    eng = None
    try:
        res["dll_sha256"] = sha_file(os.path.join(ROOT, "tools", "kvshim_vk.dll"))
        if res["dll_sha256"] != DLL_WANT:
            raise SystemExit("DLL is not 9edbafa1; refusing to run")

        # ---- 1) judge the conversation --------------------------------------
        rows = X.run(SAMPLE)
        keeps = [(r, m) for r in rows for m in r["memories"]]
        res["judge"] = {"sentences": len(rows),
                        "keeps": len(keeps),
                        "per_sentence": [{"sent_id": r["sent_id"], "turn": r["turn"],
                                          "role": r["role"], "text": r["text"],
                                          "verdict": r["verdict"], "code": r["code"],
                                          "reason": r["reason"]} for r in rows],
                        "memories": [dict(m, turn=r["turn"], sent_id=r["sent_id"], code=r["code"])
                                     for r, m in keeps]}
        print("[judge] %d sentences, %d keeps" % (len(rows), len(keeps)), flush=True)

        # ---- 2) segment: one block, text is the conversation verbatim --------
        block_text = "\n".join(t["text"] for t in SAMPLE)
        block_id = "blk_conv_2026-10-25_01"
        res["block_text"] = block_text
        res["block_text_policy"] = ("§8: the block text is the segment's original wording, "
                                    "byte for byte; nothing is rewritten or summarised")

        # ---- 3) engine: encode at position 0 ---------------------------------
        con, first = S.connect(a.db)
        bus = S.Position0Bus(con)
        eng = P.open_engine()
        leases = L.BlockLeases(eng)
        leases.register_block(BLOCK_SEQ, block_id)
        reset_info = leases.safe_reset_all(range(P.N_SEQ))
        res["safe_reset_all"] = reset_info
        cells_before = P.cell_scan(eng, BLOCK_SEQ)[0]
        ok, why = bus.check_before(block_id, "seq%d" % BLOCK_SEQ, cells_before)
        res["position0_before"] = {"cells_in_target": cells_before, "ok": ok, "detail": why}
        if not ok:
            raise SystemExit("position 0 not free: " + why)
        n = eng.write_at(BLOCK_SEQ, block_text, POS0)
        positions = P.cell_scan(eng, BLOCK_SEQ)[1]
        ok_after, why_after = bus.check_after(positions, n)
        res["encode"] = {"tokens_written": n, "cells": len(positions),
                         "pos_min": positions[0] if positions else None,
                         "pos_max_raw": P.raw_pos_max(eng, BLOCK_SEQ),
                         "pos_max_shim": eng.pos_max(BLOCK_SEQ),
                         "position0_after": {"ok": ok_after, "detail": why_after}}
        if not ok_after:
            raise SystemExit("position-0 exclusive assertion failed: " + why_after)
        print("[encode] %d tokens at [0, %d)" % (n, n), flush=True)

        # ---- 4) save + SQLite ------------------------------------------------
        path = os.path.join(a.blocks, block_id + ".kvmem")
        written = eng.save(BLOCK_SEQ, path)
        res["save"] = {"path": path, "bytes": written, "sha256": sha_file(path),
                       "cells_after_save": P.cell_scan(eng, BLOCK_SEQ)[0]}
        source_id = S.add_source(con, "conv_2026-10-25", "对话",
                                 block_text, 1)
        S.add_block(con, block_id, source_id, path, n, POS0, "seq%d" % BLOCK_SEQ)
        # R9: one retrieval unit per DISTINCT sentence; memories that quote the same sentence
        # share the unit and the sharing is recorded as fanout (no double indexing).
        units, unit_of = [], {}
        for r, m in keeps:
            span = m["evidence_span"]
            assert span in block_text, "unit text is not a verbatim substring of the block"
            sid = S.add_fact_source(con, block_id, m["attr"], span)
            m["unit_id"] = sid
            u = unit_of.setdefault(sid, {"source_id": sid, "attr": m["attr"], "text": span,
                                           "block_id": block_id, "memories": 0})
            u["memories"] += 1
        units = sorted(unit_of.values(), key=lambda u: u["source_id"])
        actions = []
        for r, m in keeps:
            act, mid = S.upsert_memory(con, m, turn=r["turn"], sent_id=r["sent_id"],
                                       code=r["code"], block_id=block_id)
            actions.append({"attr": m["attr"], "value": m["value"], "action": act,
                            "mem_id": mid, "anchored_time": m.get("anchored_time"),
                            "type": m.get("type"), "unit_id": m.get("unit_id"),
                            "resolved": m.get("resolved"),
                            "resolved_to": m.get("resolved_to")})
        res["retrieval_units"] = {
            "why": ("A single 91-token conversation block is rejected by retrieval's gate "
                    "(score 0.575 < GATE 1.30, coverage 0.12 < COV_MIN 0.35); the same fact as "
                    "its own unit scores 3.18. One KV block stays the context unit (1 block, "
                    "position 0); the retrieval units are verbatim substrings that map back to "
                    "it through source_block."),
            "dedup": {"keeps": len(keeps), "unique_units": len(units),
                      "fanout_sum": sum(u["memories"] for u in units),
                      "fanout": [u["memories"] for u in units]},
            "units": units}
        import retrieval as R
        res["gates"] = {"GATE": R.GATE, "COV_MIN": R.COV_MIN,
                        "INDEX_VERSION": R.INDEX_VERSION,
                        "unchanged": (R.GATE == 1.30 and R.COV_MIN == 0.35)}
        res["db"] = {"path": a.db, "source_id": source_id, "blocks": 1,
                     "sources": con.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0],
                     "memories": len(S.dump_memories(con)), "keeps": len(keeps),
                     "actions": actions,
                     "row_count_matches_keeps": len(S.dump_memories(con)) == len(keeps)}
        print("[db] memories=%d keeps=%d" % (len(S.dump_memories(con)), len(keeps)), flush=True)

        # ---- 5) leases in the LIVE path: attach -> refuse reset -> restore ---
        leases.attach(BLOCK_SEQ, LIVE, POS0, n)
        chain = {"placement_rule": (
                    "ask_pos must equal raw_pos_max+1 of that sequence. A block encoded at "
                    "position 0 therefore has to be repositioned so it ENDS at ANCHOR before "
                    "asking; asking at 4096 with the block still at [0, n) returns rc=-1 and an "
                    "empty answer (measured, see steps[1])."),
                 "steps": []}
        # --- 5a: attach as saved ([0, n)) and ask at ANCHOR: the measured failure
        leases.attach(BLOCK_SEQ, LIVE, POS0, POS0 + n)
        rc_far, ans_far = M2.D2.ask_native(eng, LIVE, ASK_Q, ASK_ANCHOR, P.N_PREDICT)
        chain["steps"].append({"step": "attach_as_saved", "range": [POS0, POS0 + n],
                               "live_cells": P.cell_scan(eng, LIVE)[0], "ask_pos": ASK_ANCHOR,
                               "raw_pos_max": P.raw_pos_max(eng, LIVE),
                               "rc": rc_far, "answer": ans_far.strip()[:120],
                               "hit": HIT in ans_far,
                               "referrers": leases.referrers(BLOCK_SEQ)})
        # --- 5b: the guard must stop a reset while the block is referenced
        before = P.cell_scan(eng, BLOCK_SEQ)[0]
        refused = False
        try:
            leases.reset(BLOCK_SEQ)                 # the real call the guard must stop
        except L.LeaseError as exc:
            refused = True
            chain["steps"].append({"step": "reset_while_attached", "refused": True,
                                   "error_type": "LeaseError", "message": str(exc),
                                   "engine_cell_count_after": P.cell_scan(eng, BLOCK_SEQ)[0]})
        chain["guard_refused_live_reset"] = refused
        chain["engine_block_cells_after_refusal"] = P.cell_scan(eng, BLOCK_SEQ)[0]
        chain["engine_untouched"] = P.cell_scan(eng, BLOCK_SEQ)[0] == before
        # --- 5c: legal order detach -> reset -> reload -> reposition -> attach -> ask
        leases.detach(LIVE, POS0, POS0 + n)
        chain["steps"].append({"step": "detach", "live_cells": P.cell_scan(eng, LIVE)[0],
                               "referrers": leases.referrers(BLOCK_SEQ)})
        leases.reset(BLOCK_SEQ)
        chain["steps"].append({"step": "reset_after_detach",
                               "block_cells": P.cell_scan(eng, BLOCK_SEQ)[0]})
        moved = eng.load_strict(BLOCK_SEQ, path)
        base = eng.pos_max(BLOCK_SEQ) - moved + 1
        eng.repos_local(BLOCK_SEQ, ASK_ANCHOR - moved - base)
        lo, hi = ASK_ANCHOR - moved, ASK_ANCHOR
        chain["steps"].append({"step": "reload_and_place", "cells": moved, "range": [lo, hi],
                               "pos_max_raw": P.raw_pos_max(eng, BLOCK_SEQ),
                               "file_sha_after": sha_file(path)})
        leases.attach(BLOCK_SEQ, LIVE, lo, hi)
        rc_near, ans_near = M2.D2.ask_native(eng, LIVE, ASK_Q, ASK_ANCHOR, P.N_PREDICT)
        chain["steps"].append({"step": "attach_adjacent", "range": [lo, hi],
                               "live_cells": P.cell_scan(eng, LIVE)[0],
                               "raw_pos_max": P.raw_pos_max(eng, LIVE),
                               "rc": rc_near, "answer": ans_near.strip()[:200],
                               "hit": HIT in ans_near})
        chain["answer_while_attached"] = {"rc": rc_near, "answer": ans_near.strip(),
                                          "hit": HIT in ans_near,
                                          "range": [lo, hi], "ask_pos": ASK_ANCHOR}
        # --- 5d: and the guard still refuses while it is attached in this position
        try:
            leases.reset(BLOCK_SEQ)
            chain["guard_refused_second_time"] = False
        except L.LeaseError as exc2:
            chain["guard_refused_second_time"] = True
            chain["steps"].append({"step": "reset_while_attached_adjacent", "refused": True,
                                   "message": str(exc2),
                                   "engine_cell_count_after": P.cell_scan(eng, BLOCK_SEQ)[0]})
        leases.detach(LIVE, lo, hi)
        eng.repos_local(BLOCK_SEQ, POS0 - (ASK_ANCHOR - moved))   # leave it at position 0
        chain["steps"].append({"step": "detach_and_restore_position0",
                               "block_cells": P.cell_scan(eng, BLOCK_SEQ)[0],
                               "pos_max_raw": P.raw_pos_max(eng, BLOCK_SEQ),
                               "referrers": leases.referrers(BLOCK_SEQ)})
        chain["file_unchanged"] = sha_file(path) == res["save"]["sha256"]
        res["lease_chain"] = chain
        print("[lease] refused=%s/%s untouched=%s rc_far=%s rc_near=%s hit=%s"
              % (chain["guard_refused_live_reset"], chain["guard_refused_second_time"],
                 chain["engine_untouched"], rc_far, rc_near, HIT in ans_near), flush=True)
        con.close()
    except SystemExit as exc:
        res["error"] = str(exc)
        print("STOP: %s" % exc, flush=True)
    except Exception as exc:                                        # noqa: BLE001
        import traceback
        res["error"] = "%s: %s" % (type(exc).__name__, exc)
        res["traceback"] = traceback.format_exc()[-1500:]
        traceback.print_exc()
    finally:
        if eng is not None:
            try:
                eng.close()
            except Exception:                                        # noqa: BLE001
                pass
        res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        out = a.out if os.path.isabs(a.out) else os.path.join(HERE, a.out)
        json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
        print("[RUN] wrote %s" % out, flush=True)
    return 0 if res.get("error") is None else 1


if __name__ == "__main__":
    sys.exit(main())
