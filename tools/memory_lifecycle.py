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


def _audit(trace_id, decision, reason, block_ids=None, count=None):
    if not trace_id:
        return
    try:
        import audit_log
        audit_log.event("archive", decision=decision, reason=reason,
                        block_ids=block_ids or [], count=count,
                        trace_id=trace_id)
    except Exception:                                # noqa: BLE001
        pass


def auto_archive(con, rows, now, archive_dir, days=21, trace_id=None):
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
    _audit(trace_id, "archived" if res["candidates"] else "no_candidates",
           "auto_archive", res["candidates"], len(res["candidates"]))
    return res


def _bigrams(text):
    t = "".join(ch.lower() for ch in str(text or "") if ch.isalnum())
    return {t[i:i + 2] for i in range(max(0, len(t) - 1))}


def fallback_archive(con, query, archive_dir, max_hits=5, trace_id=None):
    """只读：查未 superseded 的归档条目，按 query bigram 覆盖率打分；坏 zip/sha 跳过。"""
    import json as _json
    import zipfile
    qg = _bigrams(query)
    if not qg:
        _audit(trace_id, "miss", "empty_query", [], 0)
        return []
    try:
        rows = con.execute(
            "SELECT source_id, zip, zip_sha, superseded_by FROM memory_archive"
            " WHERE superseded_by IS NULL").fetchall()
    except sqlite3.Error:
        _audit(trace_id, "miss", "no_archive_table", [], 0)
        return []
    hits = []
    for sid, zip_path, zip_sha, _sup in rows:
        z = str(zip_path or "")
        if not z or not os.path.exists(z):
            continue
        try:
            import hashlib
            if hashlib.sha256(open(z, "rb").read()).hexdigest() != (zip_sha or ""):
                continue
            side = z + ".sidecar.json"
            if not os.path.exists(side):
                continue
            manifest = _json.load(open(side, encoding="utf-8"))
            with zipfile.ZipFile(z) as zf:
                for e in manifest.get("entries") or []:
                    if int(e.get("id", -1)) != int(sid):
                        continue
                    body = zf.read(e["member"]).split(b"text:\n", 1)[-1]
                    if hashlib.sha256(body).hexdigest() != e.get("text_sha256"):
                        continue
                    text = body.decode("utf-8", "replace")
                    tg = _bigrams(text)
                    if not tg:
                        continue
                    score = len(qg & tg) / float(len(qg))
                    if score > 0:
                        hits.append({"id": int(sid), "score": round(score, 4),
                                     "zip": z,
                                     "month": os.path.basename(z)[:7],
                                     "text_sha": e.get("text_sha256")})
        except Exception:                            # noqa: BLE001
            continue
    hits.sort(key=lambda x: (-x["score"], x["id"]))
    hits = hits[:max(1, int(max_hits))]
    _audit(trace_id, "hit" if hits else "miss", "fallback_archive",
           [h["id"] for h in hits], len(hits))
    return hits

def _slots(text):
    try:
        import memory_service as memo
        return memo.extract_slots(str(text or "")) or {}
    except Exception:                                # noqa: BLE001
        return {}


def _key_of(text):
    # 优先用确定性事实抽取（p1b）拿 subject/predicate；槽位只做补充
    try:
        import p1b_subject as P
        info = P.extract(str(text or "")) or {}
        if info.get("predicate"):
            return (info.get("subject") or "self"), info["predicate"], False
    except Exception:                                # noqa: BLE001
        pass
    sl = _slots(text)
    if not sl:
        return None, None, True
    subject = sl.get("person") or "self"
    predicate = sl.get("action") or None
    return subject, predicate, predicate is None


def _read_archived_text(con, source_id):
    import hashlib
    import json as _json
    import zipfile
    row = con.execute(
        "SELECT zip, zip_sha, superseded_by FROM memory_archive WHERE source_id=?",
        (int(source_id),)).fetchone()
    if not row:
        return None, "not_archived"
    zip_path, zip_sha, _sup = row
    if not zip_path or not os.path.exists(zip_path):
        return None, "bad_zip_or_sha"
    if hashlib.sha256(open(zip_path, "rb").read()).hexdigest() != (zip_sha or ""):
        return None, "bad_zip_or_sha"
    side = zip_path + ".sidecar.json"
    if not os.path.exists(side):
        return None, "bad_zip_or_sha"
    manifest = _json.load(open(side, encoding="utf-8"))
    ent = next((e for e in manifest.get("entries") or []
                if int(e.get("id", -1)) == int(source_id)), None)
    if not ent:
        return None, "bad_zip_or_sha"
    with zipfile.ZipFile(zip_path) as zf:
        body = zf.read(ent["member"]).split(b"text:\n", 1)[-1]
    if hashlib.sha256(body).hexdigest() != ent.get("text_sha256"):
        return None, "bad_zip_or_sha"
    return body.decode("utf-8", "replace"), None


def reheat_plan(con, source_id, live_rows, trace_id=None):
    """纯函数：校验归档 -> 抽槽 -> 与 live 比较；只返回 plan，不写 DB。"""
    text, err = _read_archived_text(con, source_id)
    plan = {"source_id": int(source_id), "action": "skip", "reason": err,
            "subject": None, "predicate": None, "superseded_by": None,
            "unresolved": False}
    if text is None:
        _audit(trace_id, plan["action"], plan["reason"], [int(source_id)], 1)
        return plan
    subject, predicate, unresolved = _key_of(text)
    plan.update(subject=subject, predicate=predicate, unresolved=unresolved)
    if subject is None or predicate is None:
        plan.update(action="skip", reason="no_subject" if subject is None
                    else "no_predicate")
        _audit(trace_id, "skip", plan["reason"], [int(source_id)], 1)
        return plan
    try:
        arch_created = con.execute(
            "SELECT COALESCE((SELECT created_at FROM memory_source WHERE id=?), '')",
            (int(source_id),)).fetchone()[0] or ""
    except sqlite3.Error:
        arch_created = ""
    for r in live_rows or []:
        if int(r[0]) == int(source_id):
            continue
        s2, p2, _u2 = _key_of(r[3] if len(r) > 3 else "")
        if s2 != subject or p2 != predicate:
            continue
        created = str(r[8]) if len(r) > 8 and r[8] else ""
        newer = (int(r[0]) > int(source_id)) and (not arch_created
                                                 or created > arch_created)
        if newer or (int(r[0]) > int(source_id) and created > arch_created):
            plan.update(action="skip_superseded", reason="newer_exists",
                        superseded_by=int(r[0]))
            return plan
    plan.update(action="restore", reason="no_newer")
    _audit(trace_id, plan["action"], plan["reason"],
           [plan["source_id"]] + ([plan["superseded_by"]]
                                  if plan.get("superseded_by") else []), 1)
    return plan