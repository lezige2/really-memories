# -*- coding: utf-8 -*-
"""M4 answer path WITH M5 grounding: route -> mount -> generate -> verify -> display.

  python -u -X utf8 m4_answer_grounded.py --q "我车牌号是多少？"
  python -u -X utf8 m4_answer_grounded.py --q "我车牌号是多少？" \
      --db _ablate/m4_memory_noplate.db --mount all

Field contract
  answer_exact          untouched model output
  answer                display layer's stripped copy (unchanged)
  display_pre_grounding what the display layer produced (four trace fields below)
  answer_display        FINAL text: M5 may replace it ONLY for verdict=unsupported
  grounding             verdict + hard facts + hits/unhit/exempt + mount evidence
"""
import argparse, hashlib, json, os, sqlite3, sys

import m4_display as DISP
import m5_bridge as BR

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


def derive_or_fallback(ans):
    raw = ans.strip()
    try:
        return DISP.derive(raw)
    except Exception as exc:                      # noqa: BLE001
        return {"answer": raw, "answer_display": raw, "answer_display_changed": False,
                "display_error": "%s: %s" % (type(exc).__name__, exc),
                "per_tag_count": len(DISP.STRAY.findall(raw)),
                "removed_chars": 0, "display_len": len(raw), "display_empty": raw == "",
                "diff_explained": False, "idempotent": None, "content_warnings": []}


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def resolve_mounts(con, q, mode, k=3):
    """The block set the PRODUCT decides to mount. Never typed by hand."""
    import retrieval as R
    if R.index_version(con) != R.INDEX_VERSION:
        R.build_index(con, verbose=False)
    if mode == "all":
        rows = list(con.execute("SELECT block_id, path, cells FROM block ORDER BY block_id"))
        probe = R.search(con, q, k=k)
        return ([{"block_id": r[0], "path": r[1], "cells": r[2]} for r in rows],
                {"mount_mode": "all-blocks",
                 "why": "product policy for a small memory: mount every block it holds",
                 "retrieval_probe": {"query": q, "hits": len(probe),
                                     "top_score": (round(probe[0].get("score", 0), 4)
                                                   if probe else None),
                                     "top_source_id": (probe[0].get("source_id")
                                                       if probe else None),
                                     "note": "routing WOULD have failed here; that is the "
                                             "measured reason this case mounts by policy"}})
    hits = R.search(con, q, k=k)
    if not hits:
        return [], {"mount_mode": "routed", "reason": "no retrieval hit", "hits": 0}
    top = hits[0]
    sid = top["source_id"] if isinstance(top, dict) else top[0]
    r = con.execute("SELECT block_id FROM source_block WHERE source_id=?", (sid,)).fetchone()
    if not r:
        return [], {"mount_mode": "routed", "reason": "hit has no block", "source_id": sid}
    br = con.execute("SELECT path, cells FROM block WHERE block_id=?", (r[0],)).fetchone()
    return ([{"block_id": r[0], "path": br[0], "cells": br[1]}],
            {"mount_mode": "routed",
             "retrieval_probe": {"query": q, "hits": len(hits),
                                 "top_score": (round(hits[0].get("score", 0), 4)
                                               if isinstance(hits[0], dict) else None)},
             "routed_by": {"source_id": sid,
                           "unit_text": top.get("name"),
                           "score": round(top.get("score", 0), 3)
                           if isinstance(top, dict) else None}})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", required=True)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--mount", default="routed", choices=("routed", "all"))
    ap.add_argument("--k", type=int, default=3)
    a = ap.parse_args()

    import m2_visibility_probe as P
    import _driver_m2                                          # noqa: F401
    import _driver2 as D2
    import m3_lease as L

    con = sqlite3.connect(a.db)
    mounts, mount_meta = resolve_mounts(con, a.q, a.mount, k=a.k)
    if not mounts:
        out({"mode": "answer", "query": a.q, "db": a.db, "error": "retrieval did not route",
             "mount": mount_meta})
        con.close()
        return 1
    mounts = mounts[:1]                       # M4 product: one block per answer, seq 1
    blk = mounts[0]
    eng = P.open_engine()
    try:
        leases = L.BlockLeases(eng)
        leases.register_block(1, blk["block_id"])
        leases.safe_reset_all(range(P.N_SEQ))
        n = eng.load_strict(1, blk["path"])
        base = eng.pos_max(1) - n + 1
        eng.repos_local(1, ASK_ANCHOR - n - base)
        lo, hi = ASK_ANCHOR - n, ASK_ANCHOR
        leases.attach(1, 0, lo, hi)
        mounted_cells = P.cell_scan(eng, 1)[0]
        rc, ans = D2.ask_native(eng, 0, a.q, ASK_ANCHOR, P.N_PREDICT)
        live_cells = P.cell_scan(eng, 0)[0]
        disp = derive_or_fallback(ans)
        pre = disp["answer_display"]
        mount_rec = {"mounted": [blk["block_id"]], "source": "answer-path mount (seq 1)",
                     "mount_meta": mount_meta, "range": [lo, hi], "cells_loaded": n,
                     "engine_cells_on_seq1": mounted_cells,
                     "cells_match_block_row": mounted_cells == blk["cells"],
                     "block_path": blk["path"], "block_sha256": sha_file(blk["path"]),
                     "block_cells_row": blk["cells"]}
        g = BR.ground(pre, mount_rec, a.q)
        out({"mode": "grounded_answer", "query": a.q, "db": a.db, "rc": rc,
             "answer_exact": ans,
             "answer": disp["answer"],
             "display_pre_grounding": pre,
             "answer_display": g["display_final"],
             "display_source": g["display_source"],
             "display_changed_by_m5": g["display_changed_by_m5"],
             "display_trace": {k: disp.get(k) for k in
                               ("answer_display_changed", "per_tag_count", "removed_chars",
                                "display_len", "display_empty", "diff_explained", "idempotent",
                                "content_warnings", "display_error")},
             "grounding": g,
             "live_cells": live_cells,
             "engine": {"model": getattr(P, "MODEL", None), "n_seq": P.N_SEQ,
                        "n_predict": P.N_PREDICT, "kv": P.KV,
                        "ask_pos": ASK_ANCHOR}})
    finally:
        eng.close()
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
