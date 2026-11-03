# -*- coding: utf-8 -*-
"""P1 底座：记忆生命周期（access / archive），独立表，不改 memory_source。

- memory_access(source_id PK, access_count, last_accessed_at)
- memory_archive(source_id PK, archived_at, zip, zip_sha, superseded_by)
"""

import os
import sqlite3
from datetime import datetime, timedelta

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

def _row_created(row):
    try:
        if isinstance(row, dict):
            return str(row.get("created_at") or "")
        return str(row[8]) if len(row) > 8 and row[8] else ""
    except Exception:                                # noqa: BLE001
        return ""


def scan_candidates(con, rows, now=None, days=21,):
    """超期低访问（无 access 或 last_accessed 早于 now-days）；已归档跳过。"""
    now = now or datetime.now()
    cutoff = (now - timedelta(days=int(days))).isoformat(timespec="seconds")
    acc = access_stats(con)
    done = archived_ids(con)
    out = []
    for r in rows or []:
        sid = int(r[0])
        if sid in done:
            continue
        a = acc.get(sid) or {}
        last = a.get("last_accessed_at") or ""
        if not last or last < cutoff:
            out.append(r)
    return out


def row_month(row, now=None):
    created = _row_created(row)
    m = created[:7]
    if len(m) == 7 and m[4] == "-":
        return m
    return (now or datetime.now()).strftime("%Y-%m")


def _as_archive_row(r):
    if isinstance(r, dict):
        return r
    return {"id": int(r[0]), "name": str(r[1]), "text": str(r[3]),
            "created_at": _row_created(r), "subject": None, "predicate": None,
            "block_sha": None, "block_bytes": 0}


def auto_archive(con, rows, now, archive_dir, days=21):
    """候选按 row_month 分组 -> out/archive/YYYY-MM.zip + 标记；幂等。"""
    import archive_store as A
    ensure_schema(con)
    now_dt = now if isinstance(now, datetime) else datetime.fromisoformat(str(now))
    cands = scan_candidates(con, rows, now_dt, days)
    groups = {}
    for r in cands:
        groups.setdefault(row_month(r, now_dt), []).append(r)
    os.makedirs(archive_dir, exist_ok=True)
    res = {"candidates": [int(r[0]) for r in cands], "months": {}, "zips": []}
    for month, grp in sorted(groups.items()):
        zip_path = os.path.join(archive_dir, "%s.zip" % month)
        side = zip_path + ".sidecar.json"
        manifest = A.archive_rows([_as_archive_row(r) for r in grp], zip_path, side)
        ids = [int(r[0]) for r in grp]
        archive_mark(con, ids, zip_path, manifest["zip_sha256"])
        res["months"][month] = ids
        res["zips"].append({"zip": zip_path, "zip_sha256": manifest["zip_sha256"],
                            "n": len(ids)})
    return res
