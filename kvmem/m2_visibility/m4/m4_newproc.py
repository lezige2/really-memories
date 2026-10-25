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
import outfilter as OUT

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


def _output_layer(d):
    """M4-A: the text we hand out must not carry a control tag, and every removal is counted.

    The assertion is load-bearing, not decoration: run_outfilter_selftest.py case S2 runs the
    same assertion with the filter disabled and it goes red. Raw evidence in d["answer"] is
    never touched by this function.
    """
    # Two stages, deliberately kept apart: counts are measured on the RAW answer, because that is
    # where a tag lives; the assertion is applied to the DELIVERED text, because that is what a
    # user reads. Measuring the counts on the delivered text (already normalised by m4_display)
    # reported per_tag={} and removed_chars=0 while the raw answer still carried a tag -- a green
    # count over an empty measurement. That happened in run_m4_verify_a2.json, attempt 2.
    raw = d.get("answer") or ""
    measured = OUT.filter_text(raw)
    f = OUT.filter_text(d.get("answer_display") or "")
    d["answer_display"] = f["text"]
    d["answer_display_changed"] = d["answer_display"] != raw
    d["output_filter"] = {"per_tag": measured["per_tag"], "total": measured["total"],
                          "before_len": measured["before_len"],
                          "after_len": measured["after_len"],
                          # attributable to the filter: the tags' own characters
                          "tag_chars_removed": measured["tag_chars_removed"],
                          # NOT attributable: the display layer collapses blank runs too, so this
                          # delta mixes two causes. Named for what it measures, not for a cause.
                          "raw_to_delivered_delta": len(raw) - len(d["answer_display"]),
                          "unknown_angle_tokens": measured["unknown_angle_tokens"],
                          "measured_on": "answer (raw, where a tag lives)",
                          "delivered_has_tag": OUT.scan(d["answer_display"])["total"]}
    try:
        OUT.assert_clean(d["answer_display"], "newproc answer_display")
        d["output_filter"]["assertion"] = "pass"
        d["output_layer_clean"] = True
    except OUT.ControlTagLeft as exc:
        d["output_filter"]["assertion"] = "FAIL"
        d["output_filter"]["assertion_raw_line"] = str(exc)
        d["output_layer_clean"] = False
    return d


def derive_or_fallback(ans):
    """A display-layer bug must never destroy the raw evidence: fall back, keep the reason."""
    raw = ans.strip()
    try:
        d = DISP.derive(raw)
    except Exception as exc:                      # noqa: BLE001 - recorded, never silent
        d = {"answer": raw, "answer_display": raw, "answer_display_changed": False,
             "display_error": "%s: %s" % (type(exc).__name__, exc),
             "per_tag_count": len(DISP.STRAY.findall(raw)),
             "removed_chars": 0, "display_len": len(raw), "display_empty": raw == "",
             "diff_explained": False, "idempotent": None, "content_warnings": []}
    return _output_layer(d)


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
             "answer_exact": ans,                         # untouched model output
             **derive_or_fallback(ans),                    # answer + display + 4 trace fields
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
