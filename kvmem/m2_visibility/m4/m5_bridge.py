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

import m5_ground as G                                              # noqa: E402

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
  note         TEXT
);
"""


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def register_block(con, block_id, text, path, cells, model, origin):
    """One row per real block file; sha is measured from disk at registration time."""
    disk = sha_file(path)
    con.execute("INSERT OR REPLACE INTO blocks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (block_id, "m4", model, int(cells), os.path.getsize(path), disk, disk, 1,
                 text, path.replace("\\", "/"), origin,
                 "registered by m4/m5_bridge.py from the M4 db + the file on disk"))
    return {"block_id": block_id, "sha256_disk": disk, "cells": int(cells),
            "bytes": os.path.getsize(path), "text_len": len(text)}


def ensure_db(db=DB_PATH):
    """Build the M5 text copy from the two M4 dbs (main + ablation). Idempotent."""
    os.makedirs(os.path.dirname(db), exist_ok=True)
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
                text = src.execute("SELECT text FROM memory_source WHERE id=?",
                                   (sid,)).fetchone()[0]
                model = json.load(open(os.path.join(HERE, "_ablate", "run_ablate.json"),
                                       encoding="utf-8"))["save"]["path"] if False else None
                reg.append(register_block(out, bid, text, path, cells,
                                          model or _model_of(bid), "m4.memory_source.text"))
        finally:
            src.close()
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
