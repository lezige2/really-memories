# -*- coding: utf-8 -*-
"""M4 -> M5 thin layer. M5's criteria file is NOT touched: this module only CALLS m5_ground.

What it owns:
  * the M5-side text copy of the M4 blocks (m5_ground.verify_sources reads a `blocks` table
    with source_text / sha256 / sha_match / source_path), built from the M4 dbs + real files;
  * the three-way verdict record (supported / unsupported / undecidable) with hard facts,
    hits, unhit, exemptions and the final display text;
  * the display decision: M5 may ONLY replace the display text of an unsupported answer.

Nothing here rewrites a supported answer, and nothing rewrites an undecidable one --
an undecidable answer is kept verbatim and FLAGGED in the record (yellow, not silent).
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "m5"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import m5_ground as G                                              # noqa: E402
import memory_source as ms                                        # noqa: E402

DB_PATH = os.path.join(HERE, "_m5db", "m5_m4_blocks.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS blocks (
  block_id     TEXT PRIMARY KEY,
  family       TEXT NOT NULL,
  model        TEXT NOT NULL,
  cells        INTEGER NOT NULL,
  size_bytes   INTEGER NOT NULL,
  sha256       TEXT NOT NULL,
  sha256_disk  TEXT NOT NULL,
  sha_match    INTEGER NOT NULL,
  source_text  TEXT NOT NULL,
  source_path  TEXT NOT NULL,
  text_origin  TEXT NOT NULL,
  note         TEXT,
  -- Stage 3 / D3-1. The ablation block is an EDITED text and may never be registered in
  -- layer 1, so it needs an explicit exemption channel -- but an exemption nobody can see
  -- is worse than none. DEFAULT 0 is the REFUSAL direction: a real block that says
  -- nothing is still held to the gate, while a real block wrongly marked 1 would also
  -- have to carry the declared_synthetic: prefix, which the CHECK below forbids.
  synthetic    INTEGER NOT NULL DEFAULT 0 CHECK (synthetic IN (0, 1)),
  -- text_origin IS NOT NULL is not decoration: a CHECK comparing two columns evaluates
  -- to NULL when either side is NULL, and SQLite treats NULL as PASS -- so without this
  -- first clause a NULL origin slips past BOTH the prefix rule and its own non-null demand.
  CHECK (text_origin IS NOT NULL
         AND ((text_origin LIKE 'declared_synthetic:%') = (synthetic = 1)))
);
"""


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def origin_of(reg, src, sid, text, block_id):
    """text_origin for one block: registry:<name>@<sha16> when layer 2 is linked.

    The NAME must come from layer 1: a layer-2 id and a registry id are different id
    spaces, so resolving the name inside the layer-2 db silently yields the wrong source.
    Anything that cannot be resolved is labelled, never left looking authoritative.
    """
    try:
        row = src.execute("SELECT registry_source_id, source_hash FROM memory_source "
                          "WHERE id=?", (sid,)).fetchone()
    except sqlite3.OperationalError:
        # the ablation db has no registry columns: its text is an edited copy, not a source
        return "declared_synthetic:%s@%s" % (
            block_id, hashlib.sha256(text.encode("utf-8")).hexdigest()[:16])
    if not row or row[0] is None or not row[1]:
        return "m4.memory_source.text (unlinked: run m4_layer2_link.py --apply)"
    l1 = reg.execute("SELECT name, source_hash FROM memory_source WHERE id=?",
                     (row[0],)).fetchone() if reg else None
    if not l1:
        return "m4.memory_source.text (unlinked: registry id %r not in layer 1)" % (row[0],)
    if l1[1] != row[1]:
        return "stale:layer2@%s!=registry@%s" % (row[1][:16], l1[1][:16])
    return "registry:%s@%s" % (l1[0], l1[1][:16])


def register_block(con, block_id, text, path, cells, model, origin, synthetic=False):
    """One row per real block file; sha is measured from disk at registration time.

    TODO(stage3): when M5 selects its own sources from the registry, every source admitted
    here must first pass tools/memory_source.assert_m5_source_allowed(name). Today the M5
    text copy is built from the M4 db, so the gate is not on this path yet -- this marker is
    what tools/../registry/check_m5_gate.py looks for.
    """
    if ms.origin_is_synthetic(origin) != bool(synthetic):
        # the DB CHECK enforces the same rule; failing here names the CALLER instead of
        # handing back a bare IntegrityError.
        raise ms.OriginError(
            "origin prefix and synthetic flag disagree: origin=%r synthetic=%s"
            % (origin[:60], synthetic))
    disk = sha_file(path)
    con.execute("INSERT OR REPLACE INTO blocks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (block_id, "m4", model, int(cells), os.path.getsize(path), disk, disk, 1,
                 text, path.replace("\\", "/"), origin,
                 "registered by m4/m5_bridge.py from the M4 db + the file on disk",
                 1 if synthetic else 0))
    return {"block_id": block_id, "sha256_disk": disk, "cells": int(cells),
            "bytes": os.path.getsize(path), "text_len": len(text)}


REG_DB = os.path.join(ROOT, "kvmem", "chat.db")


def select_m5_source(regcon, src_l2, sid, block_id):
    """THE source-selection point: which text is allowed to become an M5 source.

    Layer 2 is derived. When its row points back at a registry id, the M5 text must be
    assembled from LAYER 1:
      * a conversation container is NEVER a source (it carries model turns) -- only its
        declared human excerpts are, joined in line order;
      * a human_memory container is used as-is.
    Without a registry link (the ablation db) the text is a DECLARED SYNTHETIC source:
    admitted only with synthetic=1 and a declared_synthetic: origin.
    """
    try:
        name, text, rid = src_l2.execute(
            "SELECT name, text, registry_source_id FROM memory_source WHERE id=?",
            (sid,)).fetchone()
    except sqlite3.OperationalError:
        # the ablation db has no registry columns: its text is an edited copy, not a source
        name, text = src_l2.execute("SELECT name, text FROM memory_source WHERE id=?",
                                    (sid,)).fetchone()
        rid = None
    if rid is None:
        if regcon is not None and regcon.execute(
                "SELECT 1 FROM memory_source WHERE name=?", (name,)).fetchone():
            raise ms.OriginError(
                "layer-2 row %r exists in layer 1 but is not linked: refusing to label it "
                "declared_synthetic (run m4_layer2_link.py --apply)" % name)
        return {"text": text, "names": [], "synthetic": True, "mode": "synthetic",
                "origin": origin_of(regcon, src_l2, sid, text, block_id)}
    c = regcon.execute(
        "SELECT id, name, text, text_kind, is_excerpt, source_hash FROM memory_source "
        "WHERE id=?", (rid,)).fetchone()
    if not c:
        raise ms.OriginError("registry id %r is not in layer 1 (stale link for %r)"
                             % (rid, name))
    cid, cname, ctext, kind, is_exc, chash = c
    if is_exc:
        raise ms.OriginError(
            "%r is an excerpt row; an excerpt is a span of its container, never a source"
            % (cname,))
    if kind == "conversation":
        ex = list(regcon.execute(
            "SELECT e.line_index, e.excerpt_source_id, s.name "
            "FROM memory_source_excerpt e JOIN memory_source s ON s.id = e.excerpt_source_id "
            "WHERE e.container_id=? ORDER BY e.line_index", (cid,)))
        if not ex:
            raise ms.OriginError(
                "容器 %r 没有任何已声明的人类摘录: 不能当源, 也不许悄悄退回容器全文" % (cname,))
        texts = [regcon.execute("SELECT text FROM memory_source WHERE id=?",
                                (r[1],)).fetchone()[0] for r in ex]
        joined = chr(10).join(texts)
        for nm in [r[2] for r in ex]:
            ms.assert_m5_source_allowed(regcon, nm)
        # S3-1 -- this assertion is the GUARD, not a bug to fix. Skipping the assistant
        # turns is DELIBERATE: making joined a contiguous substring again would pull the
        # model turns back onto the source side, which is exactly what R15 forbids.
        assert joined not in ctext, (
            "joined text must NOT be a contiguous substring of the container: it "
            "deliberately skips the model turns (L2/L6). Removing this assert re-admits "
            "model output as a memory source.")
        origin = ms.format_human_turns_origin(cname, chash[:16], [r[0] for r in ex], joined)
        return {"text": joined, "names": [r[2] for r in ex], "synthetic": False,
                "mode": "human_turns", "origin": origin}
    ms.assert_m5_source_allowed(regcon, cname)
    return {"text": ctext, "names": [cname], "synthetic": False, "mode": "container",
            "origin": origin_of(regcon, src_l2, sid, text, block_id)}

def ensure_db(db=DB_PATH):
    """Build the M5 text copy from the two M4 dbs (main + ablation). Idempotent."""
    os.makedirs(os.path.dirname(db), exist_ok=True)
    regcon = sqlite3.connect(REG_DB) if os.path.exists(REG_DB) else None
    if os.path.exists(db):
        os.remove(db)
    out = sqlite3.connect(db)
    out.executescript(SCHEMA)
    reg = []
    for m4db in (os.path.join(HERE, "m4_memory.db"),
                 os.path.join(HERE, "_ablate", "m4_memory_noplate.db")):
        if not os.path.exists(m4db):
            continue
        src = sqlite3.connect(m4db)
        try:
            for bid, sid, path, cells in src.execute(
                    "SELECT block_id, source_id, path, cells FROM block"):
                sel = select_m5_source(regcon, src, sid, bid)
                model = json.load(open(os.path.join(HERE, "_ablate", "run_ablate.json"),
                                       encoding="utf-8"))["save"]["path"] if False else None
                reg.append(register_block(out, bid, sel["text"], path, cells,
                                          model or _model_of(bid), sel["origin"],
                                          synthetic=sel["synthetic"]))
        finally:
            src.close()
    if regcon is not None:
        regcon.close()
    out.execute("INSERT OR REPLACE INTO meta VALUES (?,?)",
                ("built_at", __import__("time").strftime("%Y-%m-%dT%H:%M:%S")))
    out.commit()
    rows = list(out.execute("SELECT block_id, sha256, source_text FROM blocks "
                            "ORDER BY block_id"))
    out.close()
    canon = hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {"db": db, "blocks": reg, "content_sha256": canon,
            "content_sha256_note": "sha256 of the sorted (block_id, sha, text) rows, so it is "
                                   "stable across rebuilds"}


def _model_of(block_id):
    try:
        sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "m2"))
        import _driver_m2                                          # noqa: F401
        import m2_visibility_probe as P
        return getattr(P, "MODEL", "unknown")
    except Exception:                                             # noqa: BLE001
        return "unknown"


def a_family_symmetry(texts):
    """Extraction-side symmetry: the SAME text read by the answer-side extractor and by the
    source-side profile must agree on A-family keys. Nothing here relaxes matching -- it only
    proves the two harvesters produce the same shape."""
    prof = G.source_profile(texts)
    answer_side = {}
    for t in texts:
        for f in G.extract(t):
            if f["family"] == "A":
                answer_side[f["key"]] = f["raw"]
    hit = {k: G.a_hit(k, prof) for k in answer_side}
    plate = set(prof["plate"])
    return {
        "answer_side_A_keys": answer_side,
        "source_side_plate": sorted(plate),
        "source_side_latin": sorted(prof["latin"]),
        "plate_shaped_equal": set(answer_side) == plate,
        "only_in_answer_side": sorted(set(answer_side) - plate),
        "only_in_source_side": sorted(plate - set(answer_side)),
        "hit_map": hit,
        "all_source_A_keys_hittable": all(hit.values()),
        "assertion": "plate_shaped_equal and all_source_A_keys_hittable",
        "verdict": bool(set(answer_side) == plate and all(hit.values())),
    }


def ground(display_text, mount_record, question, db=DB_PATH):
    """Call the frozen validator and turn its report into the product record.

    mount_record: {"mounted": [block_id, ...], ...} as captured by the ANSWER PATH
    (never typed by hand -- the answer script fills it from what it actually mounted).
    """
    mounted = tuple(mount_record["mounted"])
    rep = G.ground(display_text, list(mounted), question, db=db)
    verdict = rep["verdict"]
    topic = G.topic_word(question)
    template = "记忆里没有记录%s。" % topic
    if verdict == "unsupported":
        # PRODUCT POLICY (not a criteria change): an ungrounded answer is not shown.
        # The frozen validator rewrites only the involved sentences and keeps the rest;
        # its verbatim output stays in the record as m5_rewritten, so nothing is hidden --
        # the product simply does not let model filler ride along with the refusal line.
        display, source = template, "m5_template"
    else:
        display, source = display_text, "display_layer"
    return {
        "verdict": verdict,
        "reason": rep["reason"],
        "criteria": rep["criteria"],
        "question": question,
        "topic_word": topic,
        "mounted": list(mounted),
        "mount_evidence": mount_record,
        "grounded_field": "display_pre_grounding",
        "hard_facts": rep["facts"],
        "hits": rep["hits"],
        "unhit": rep["unhit"],
        "exempt": rep["exempt"],
        "undecidable_items": rep["undecidable_items"],
        "multiset_note": rep["multiset_note"],
        "source_problems": rep["source_problems"],
        "input_origin": mount_record.get("input_origin",
                                         "answer-path generation (real engine, own pid)"),
        "synthetic": bool(mount_record.get("synthetic", False)),
        "display_policy": ("unsupported -> template only; m5_rewritten kept verbatim"
                           if verdict == "unsupported" else "verdict kept display verbatim"),
        "template": template,
        "unhit_sentences": sorted({int(u["sentence"]) for u in rep["unhit"]}),
        "display_final": display,
        "display_source": source,
        "display_changed_by_m5": display != display_text,
        "m5_rewritten": rep["rewritten"],
        "m5_rewritten_is_original": rep["rewritten_is_original"],
        "recheck": rep.get("recheck"),
        "flagged": verdict == "undecidable",
        "flag_note": ("undecidable 不改写，只标黄" if verdict == "undecidable" else None),
    }
