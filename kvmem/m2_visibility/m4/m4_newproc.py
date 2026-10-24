# -*- coding: utf-8 -*-
"""M4 acceptance 4/5 -- a GENUINELY new process retrieves and answers.

  python -X utf8 m4_newproc.py --mode search --q "我住在哪？"
  python -X utf8 m4_newproc.py --mode answer --q "我住在哪？"

answer resolves the block THROUGH retrieval (the product path), never by guessing a path.
Every mode prints one JSON line carrying os.getpid(), so the caller can prove the work did not
happen in the writer's process.
"""
import argparse, json, os, sqlite3, sys

import m4_display as DISP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "kvmem", "m2_visibility", "engine"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "m2"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "m3"), HERE):
    sys.path.insert(0, p)

ASK_ANCHOR = 4096
DB = os.path.join(HERE, "m4_memory.db")


def out(d):
    d["pid"] = os.getpid()
    print("@@JSON@@" + json.dumps(d, ensure_ascii=False), flush=True)


def _index(con):
    import retrieval as R
    if R.index_version(con) != R.INDEX_VERSION:
        R.build_index(con, verbose=False)
    return R


def _route(con, q, k=3):
    """retrieval hit -> (block_id, path, source_id, score, unit_text)."""
    R = _index(con)
    hits = R.search(con, q, k=k)
    if not hits:
        return None, {"reason": "no hits", "gate": "score>=1.30 or coverage>=0.35"}
    top = hits[0]
    sid = top["source_id"] if isinstance(top, dict) else top[0]
    row = con.execute("SELECT block_id FROM source_block WHERE source_id=?", (sid,)).fetchone()
    if not row:
        return None, {"reason": "hit %r has no block mapping" % (sid,), "hit": str(top)[:200]}
    block_id = row[0]
    br = con.execute("SELECT path, cells FROM block WHERE block_id=?", (block_id,)).fetchone()
    txt = con.execute("SELECT text FROM memory_source WHERE id=?", (sid,)).fetchone()[0]
    return (block_id, br[0], br[1], sid, txt), {"score": round(top.get("score", 0), 3)
                                               if isinstance(top, dict) else None}


def mode_search(a):
    con = sqlite3.connect(a.db)
    R = _index(con)
    hits = R.search(con, a.q, k=a.k, explain=bool(a.explain))
    routed = []
    for h in hits:
        sid = h["source_id"] if isinstance(h, dict) else h[0]
        r = con.execute("SELECT block_id FROM source_block WHERE source_id=?", (sid,)).fetchone()
        routed.append({"source_id": sid,
                       "name": h.get("name") if isinstance(h, dict) else None,
                       "score": round(h.get("score", 0), 3) if isinstance(h, dict) else None,
                       "block_id": r[0] if r else None})
    out({"mode": "search", "query": a.q, "index_version": R.index_version(con),
         "sources_in_db": con.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0],
         "hits": routed, "n_hits": len(routed)})
    con.close()
    return 0 if routed else 1


def mode_answer(a):
    import m2_visibility_probe as P
    import _driver_m2                                       # sets P.MODEL/P.MANIFEST (14B line)
    import _driver2 as D2
    import m3_lease as L
    con = sqlite3.connect(a.db)
    route, meta = _route(con, a.q, k=a.k)
    if route is None:
        out({"mode": "answer", "query": a.q, "error": "retrieval did not route to a block",
             "meta": meta})
        con.close()
        return 1
    block_id, path, cells, sid, unit_text = route
    eng = P.open_engine()
    try:
        leases = L.BlockLeases(eng)
        leases.register_block(1, block_id)
        leases.safe_reset_all(range(P.N_SEQ))
        n = eng.load_strict(1, path)
        base = eng.pos_max(1) - n + 1
        eng.repos_local(1, ASK_ANCHOR - n - base)
        lo, hi = ASK_ANCHOR - n, ASK_ANCHOR
        leases.attach(1, 0, lo, hi)
        rc, ans = D2.ask_native(eng, 0, a.q, ASK_ANCHOR, P.N_PREDICT)
        out({"mode": "answer", "query": a.q, "routed_by": {"source_id": sid,
                                                            "unit_text": unit_text,
                                                            "score": meta.get("score")},
             "block_id": block_id, "block_path": path, "cells_loaded": n, "range": [lo, hi],
             "ask_pos": ASK_ANCHOR, "rc": rc,
             "answer": ans.strip(),                       # evidence, byte-identical to before
             "answer_exact": ans,                         # untouched model output
             "answer_display": DISP.strip_think(ans.strip()),   # derived, user-facing
             "answer_display_changed": DISP.has_tag(ans.strip()),
             "live_cells": P.cell_scan(eng, 0)[0],
             "block_cells": P.cell_scan(eng, 1)[0],
             "engine": {"model": getattr(P, "MODEL", None), "n_ctx": P.N_CTX,
                        "n_seq": P.N_SEQ, "kv": P.KV}})
    finally:
        eng.close()
    con.close()
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=("search", "answer"))
    ap.add_argument("--q", required=True)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--explain", action="store_true")
    a = ap.parse_args()
    return mode_search(a) if a.mode == "search" else mode_answer(a)


if __name__ == "__main__":
    sys.exit(main())
