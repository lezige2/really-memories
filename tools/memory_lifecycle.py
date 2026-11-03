# -*- coding: utf-8 -*-
"""P1 底座：记忆生命周期（access / archive），独立表，不改 memory_source。

- memory_access(source_id PK, access_count, last_accessed_at)
- memory_archive(source_id PK, archived_at, zip, zip_sha, superseded_by)
"""

import sqlite3
from datetime import datetime

SCHEMA_SQL = (
    "CREATE TABLE IF NOT EXISTS memory_access ("
    " source_id INTEGER PRIMARY KEY,"
    " access_count INTEGER NOT NULL DEFAULT 0,"
    " last_accessed_at TEXT)",
    "CREATE TABLE IF NOT EXISTS memory_archive ("
    " source_id INTEGER PRIMARY KEY,"
    " archived_at TEXT,"
    " zip TEXT,"
    " zip_sha TEXT,"
    " superseded_by INTEGER)",
)


def ensure_schema(con):
    for sql in SCHEMA_SQL:
        con.execute(sql)
    con.commit()
    return {"ok": True, "tables": ["memory_access", "memory_archive"]}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def record_access(con, ids):
    """按 id 批量 upsert（count+1、last_accessed_at=now）。"""
    ids = sorted({int(i) for i in (ids or [])})
    if not ids:
        return 0
    ensure_schema(con)
    now = _now()
    for sid in ids:
        con.execute(
            "INSERT INTO memory_access(source_id,access_count,last_accessed_at)"
            " VALUES(?,1,?) ON CONFLICT(source_id) DO UPDATE SET"
            " access_count=access_count+1,last_accessed_at=excluded.last_accessed_at",
            (sid, now))
    con.commit()
    return len(ids)


def archived_ids(con):
    try:
        return {int(r[0]) for r in con.execute(
            "SELECT source_id FROM memory_archive WHERE archived_at IS NOT NULL")}
    except sqlite3.Error:
        return set()


def active_rows(con, rows):
    """过滤已归档（未归档/无记录均保留）。"""
    bad = archived_ids(con)
    return [r for r in (rows or []) if int(r[0]) not in bad]


def archive_mark(con, ids, zip_path, zip_sha, superseded_by=None):
    ids = sorted({int(i) for i in (ids or [])})
    ensure_schema(con)
    now = _now()
    for sid in ids:
        con.execute(
            "INSERT INTO memory_archive(source_id,archived_at,zip,zip_sha,superseded_by)"
            " VALUES(?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET"
            " archived_at=excluded.archived_at, zip=excluded.zip,"
            " zip_sha=excluded.zip_sha, superseded_by=excluded.superseded_by",
            (sid, now, zip_path, zip_sha, superseded_by))
    con.commit()
    return len(ids)


def access_stats(con):
    try:
        return {int(r[0]): {"access_count": int(r[1]), "last_accessed_at": r[2]}
                for r in con.execute(
                    "SELECT source_id,access_count,last_accessed_at FROM memory_access")}
    except sqlite3.Error:
        return {}