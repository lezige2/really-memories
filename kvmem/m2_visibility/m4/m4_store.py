# -*- coding: utf-8 -*-
"""M4 -- landing zone: SQLite rows for blocks, sources and memories, plus the position-0 bus.

Two tables matter to other code and are frozen by tools/retrieval.py:
  memory_source(id, name, label, text)   <- build_index() reads exactly these columns
The rest is M4's own bookkeeping.

Multi-value rule (§5): a new value for the same (subject, attr) marks the old row superseded
and KEEPS it -- never a silent overwrite.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import os
import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS memory_source (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, label TEXT NOT NULL, text TEXT NOT NULL,
    fanout INTEGER NOT NULL DEFAULT 1,       -- how many memories share this unit (R9 dedupe)
    UNIQUE (text));
CREATE TABLE IF NOT EXISTS block (
    block_id TEXT PRIMARY KEY, source_id INTEGER NOT NULL, path TEXT NOT NULL,
    sha256 TEXT NOT NULL, cells INTEGER NOT NULL, pos_lo INTEGER NOT NULL,
    pos_hi INTEGER NOT NULL, position0_owner TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS memory (
    mem_id INTEGER PRIMARY KEY, turn INTEGER, sent_id INTEGER, code TEXT,
    subject TEXT NOT NULL, attr TEXT NOT NULL, value TEXT NOT NULL, type TEXT,
    evidence_span TEXT, anchored_time TEXT, confidence REAL,
    unit_id INTEGER,                          -- R9: which retrieval unit carries this memory
    resolved TEXT, resolved_to TEXT,          -- R7: value stays verbatim, reference gets resolved
    status TEXT NOT NULL DEFAULT 'live', superseded_by INTEGER, superseded_at TEXT,
    block_id TEXT, created_at TEXT NOT NULL,
    UNIQUE (subject, attr, value));
CREATE TABLE IF NOT EXISTS source_block (      -- retrieval unit -> KV block
    source_id INTEGER PRIMARY KEY, block_id TEXT NOT NULL, kind TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS review (              -- §6: closed vocab, new attrs wait here
    review_id INTEGER PRIMARY KEY, sent_id INTEGER, text TEXT, attr TEXT, reason TEXT,
    created_at TEXT NOT NULL);
"""


def connect(path):
    first = not os.path.exists(path)
    con = sqlite3.connect(path)
    con.executescript(DDL)
    con.commit()
    return con, first


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


class Position0Bus:
    """The L6 assertion: position 0 on one sequence belongs to exactly one block.

    Checked twice -- before the write (the target range must be empty in the engine AND
    unclaimed in the DB) and after it (the scan must be exactly [0, n)).
    """

    def __init__(self, con):
        self.con = con

    def claim(self, seq_label, block_id):
        row = self.con.execute(
            "SELECT block_id FROM block WHERE position0_owner=? AND pos_lo=0 AND block_id<>?",
            (seq_label, block_id)).fetchone()
        return row[0] if row else None

    def check_before(self, block_id, seq_label, engine_cells):
        if engine_cells:
            return False, "sequence %s already holds %d cells; position 0 is not free" % (
                seq_label, engine_cells)
        owner = self.claim(seq_label, block_id)
        if owner:
            return False, "position 0 on %s is already claimed by block %s" % (seq_label, owner)
        return True, "position 0 free on %s (0 cells, no DB claim)" % seq_label

    def check_after(self, positions, n_tokens):
        want = list(range(0, n_tokens))
        ok = positions == want
        return ok, ("scan covers exactly [0, %d)" % n_tokens if ok else
                    "scan is %s, expected [0, %d)" % (_span(positions), n_tokens))


def _span(positions):
    return "[%s..%s] n=%d" % (positions[0], positions[-1], len(positions)) if positions else "[]"


def add_source(con, name, label, text, source_id=None):
    if source_id is None:
        r = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM memory_source").fetchone()
        source_id = r[0]
    con.execute("INSERT OR REPLACE INTO memory_source (id, name, label, text) VALUES (?,?,?,?)",
                (source_id, name, label, text))
    con.commit()
    return source_id


def add_fact_source(con, block_id, attr, span, kind="fact"):
    """One retrieval unit per DISTINCT text (R9). text is a verbatim substring of the block.

    Measured why units exist at all: the whole 91-token block scores 0.575 / coverage 0.12 and is
    rejected by retrieval.GATE=1.30 / COV_MIN=0.35, while the same fact as its own unit scores
    3.18. Two memories that quote the SAME sentence share one unit; fanout records the sharing
    instead of indexing the same text twice.
    """
    row = con.execute("SELECT id FROM memory_source WHERE text=?", (span,)).fetchone()
    if row:
        con.execute("UPDATE memory_source SET fanout=fanout+1 WHERE id=?", (row[0],))
        con.commit()
        return row[0]
    sid = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM memory_source").fetchone()[0]
    con.execute("INSERT INTO memory_source (id, name, label, text, fanout) VALUES (?,?,?,?,1)",
                (sid, "fact_%s_%s" % (attr, sid), attr, span))
    con.execute("INSERT OR REPLACE INTO source_block (source_id, block_id, kind) VALUES (?,?,?)",
                (sid, block_id, kind))
    con.commit()
    return sid


def add_block(con, block_id, source_id, path, cells, pos_lo, position0_owner):
    con.execute(
        "INSERT OR REPLACE INTO block (block_id, source_id, path, sha256, cells, pos_lo, "
        "pos_hi, position0_owner, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (block_id, source_id, path, sha256_file(path), cells, pos_lo, pos_lo + cells - 1,
         position0_owner, now()))
    con.commit()


def upsert_memory(con, mem, turn=None, sent_id=None, code=None, block_id=None):
    """Insert, dedupe or supersede. Returns (action, mem_id)."""
    row = con.execute("SELECT mem_id, evidence_span FROM memory WHERE subject=? AND attr=? AND value=?",
                      (mem["subject"], mem["attr"], mem["value"])).fetchone()
    if row:
        span = row[1] or ""
        if mem["evidence_span"] not in span:            # §5: dedupe keeps the first span
            con.execute("UPDATE memory SET evidence_span=? WHERE mem_id=?",
                        (span + " | " + mem["evidence_span"], row[0]))
            con.commit()
        return "deduped", row[0]

    live = con.execute("SELECT mem_id FROM memory WHERE subject=? AND attr=? AND status='live'",
                       (mem["subject"], mem["attr"])).fetchall()
    mid = None
    if live:
        cur = con.execute(
            "INSERT INTO memory (turn, sent_id, code, subject, attr, value, type, evidence_span, "
            "anchored_time, confidence, unit_id, resolved, resolved_to, status, block_id, "
            "created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'live',?,?)",
            (turn, sent_id, code, mem["subject"], mem["attr"], mem["value"], mem.get("type"),
             mem["evidence_span"], mem.get("anchored_time"), mem.get("confidence"),
             mem.get("unit_id"), mem.get("resolved"), mem.get("resolved_to"),
             block_id, now()))
        mid = cur.lastrowid
        for (old,) in live:                             # keep, never delete
            con.execute("UPDATE memory SET status='superseded', superseded_by=?, superseded_at=? "
                        "WHERE mem_id=?", (mid, now(), old))
        con.commit()
        return "superseded_previous", mid

    cur = con.execute(
        "INSERT INTO memory (turn, sent_id, code, subject, attr, value, type, evidence_span, "
        "anchored_time, confidence, unit_id, resolved, resolved_to, status, block_id, "
        "created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'live',?,?)",
        (turn, sent_id, code, mem["subject"], mem["attr"], mem["value"], mem.get("type"),
         mem["evidence_span"], mem.get("anchored_time"), mem.get("confidence"),
         mem.get("unit_id"), mem.get("resolved"), mem.get("resolved_to"),
         block_id, now()))
    con.commit()
    return "inserted", cur.lastrowid


def add_review(con, sent_id, text, attr, reason):
    con.execute("INSERT INTO review (sent_id, text, attr, reason, created_at) VALUES (?,?,?,?,?)",
                (sent_id, text, attr, reason, now()))
    con.commit()


def dump_memories(con):
    return [dict(zip(("mem_id", "subject", "attr", "value", "type", "status", "anchored_time",
                      "superseded_by", "evidence_span", "code", "unit_id", "resolved",
                      "resolved_to"), r))
            for r in con.execute(
                "SELECT mem_id, subject, attr, value, type, status, anchored_time, superseded_by, "
                "evidence_span, code, unit_id, resolved, resolved_to FROM memory "
                "ORDER BY mem_id")]
