# -*- coding: utf-8 -*-
"""Build the ABLATION block for M5-in-the-answer-path: the same conversation with the
license-plate sentence deleted. New files only -- no existing block is touched.

  python -u -X utf8 m4_ablate.py   -> _ablate/run_ablate.json

Same writer as the product path (judge -> write_at(seq, text, 0) -> save -> SQLite), so the
ablation differs from the main block in exactly one thing: the plate sentence is gone.
"""
import argparse, hashlib, json, os, sqlite3, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "kvmem", "m2_visibility", "m2"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "m3"), HERE):
    sys.path.insert(0, p)
import m2_visibility_probe as P                                    # noqa: E402
import _driver_m2                                                 # noqa: E402,F401
import m3_lease as L                                              # noqa: E402
import m4_extract as X                                            # noqa: E402
import m4_store as S                                              # noqa: E402
import retrieval as R                                             # noqa: E402

BLOCK_SEQ, POS0, ASK_ANCHOR = 1, 0, 4096
TS = "2026-10-25T09:00:00"
DLL_WANT = "9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c"
BLOCK_ID = "blk_conv_noplate_2026-10-25_01"
OUT = os.path.join(HERE, "_ablate")

SAMPLE = [
    {"role": "user", "text": "你好呀！", "ts": TS},
    {"role": "assistant", "text": "你好！有什么可以帮你？", "ts": TS},
    {"role": "user", "text": "我住在广陵路 12 号 2 单元 602。", "ts": TS},
    {"role": "user", "text": "我每天早上七点半出门，别在那个时候给我推消息。", "ts": TS},
    {"role": "user", "text": "我车牌是浙B-3F19K。", "ts": TS},          # <- the only deletion
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
    ap.add_argument("--out", default=os.path.join(OUT, "run_ablate.json"))
    a = ap.parse_args()
    os.makedirs(os.path.join(OUT, "blocks"), exist_ok=True)
    db = os.path.join(OUT, "m4_memory_noplate.db")
    if os.path.exists(db):
        os.remove(db)
    keep = [t for t in SAMPLE if "车牌" not in t["text"]]
    dropped = [t for t in SAMPLE if "车牌" in t["text"]]
    block_text = "\n".join(t["text"] for t in keep)
    res = {"schema": "m4_ablate_v1", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "block_id": BLOCK_ID, "dropped": [t["text"] for t in dropped],
           "block_text": block_text, "db": db,
           "ablation_policy": "delete the plate sentence only; every other sentence byte-identical"}
    if sha_file(os.path.join(ROOT, "tools", "kvshim_vk.dll")) != DLL_WANT:
        raise SystemExit("DLL is not 9edbafa1; refusing to run")
    rows = X.run(keep)
    keeps = [(r, m) for r in rows for m in r["memories"]]
    res["judge"] = {"sentences": len(rows), "keeps": len(keeps),
                    "per_sentence": [{"sent_id": r["sent_id"], "role": r["role"],
                                      "text": r["text"], "verdict": r["verdict"],
                                      "code": r["code"]} for r in rows],
                    "kept_attrs": [m["attr"] for _, m in keeps]}
    print("[judge] %d sentences, %d keeps" % (len(rows), len(keeps)), flush=True)

    con, _first = S.connect(db)
    eng = P.open_engine()
    try:
        leases = L.BlockLeases(eng)
        leases.register_block(BLOCK_SEQ, BLOCK_ID)
        leases.safe_reset_all(range(P.N_SEQ))
        n = eng.write_at(BLOCK_SEQ, block_text, POS0)
        positions = P.cell_scan(eng, BLOCK_SEQ)[1]
        res["encode"] = {"tokens": n, "cells": len(positions),
                         "pos_min": positions[0] if positions else None,
                         "pos_max_raw": P.raw_pos_max(eng, BLOCK_SEQ),
                         "position0_owner": "seq%d" % BLOCK_SEQ}
        if positions[:1] != [0]:
            raise SystemExit("position 0 not owned by the block: %r" % positions[:3])
        path = os.path.join(OUT, "blocks", BLOCK_ID + ".kvmem")
        written = eng.save(BLOCK_SEQ, path)
        res["save"] = {"path": path, "bytes": written, "sha256": sha_file(path),
                       "cells_after_save": P.cell_scan(eng, BLOCK_SEQ)[0]}
        print("[encode] %d tokens, %d cells -> %s" % (n, len(positions), path), flush=True)
    finally:
        eng.close()

    sid_conv = S.add_source(con, "conv_2026-10-25_noplate", "对话", block_text, 1)
    S.add_block(con, BLOCK_ID, sid_conv, path, n, POS0, "seq%d" % BLOCK_SEQ)
    units = {}
    for r, m in keeps:
        span = m["evidence_span"]
        assert span in block_text, "unit text is not a verbatim substring of the block"
        sid = S.add_fact_source(con, BLOCK_ID, m["attr"], span)
        m["unit_id"] = sid
        units.setdefault(sid, {"source_id": sid, "attr": m["attr"], "text": span})
    for r, m in keeps:
        S.upsert_memory(con, m, turn=r["turn"], sent_id=r["sent_id"], code=r["code"],
                        block_id=BLOCK_ID)
    if R.index_version(con) != R.INDEX_VERSION:
        R.build_index(con, verbose=False)
    res["db_state"] = {"sources": con.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0],
                       "memories": len(S.dump_memories(con)),
                       "retrieval_index": R.index_version(con)}
    # does the PLATE question still route in the ablated product db?
    hits = R.search(con, "我车牌号是多少？", k=3)
    res["plate_route_in_ablated_db"] = {
        "n_hits": len(hits),
        "top": ({"source_id": hits[0]["source_id"], "score": round(hits[0].get("score", 0), 3),
                 "name": hits[0].get("name")} if hits else None)}
    con.close()
    res["ok"] = bool(res["save"]["sha256"] and res["encode"]["cells"] > 0)
    json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: res[k] for k in ("block_id", "dropped", "encode", "save",
                                          "db_state", "plate_route_in_ablated_db", "ok")},
                     ensure_ascii=False, indent=1))
    print("[RUN] wrote", a.out)


if __name__ == "__main__":
    main()
