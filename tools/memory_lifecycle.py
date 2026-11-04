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
    " superseded_by INTEGER,"
    " reheated_at TEXT)",
)


def ensure_schema(con):
    for sql in SCHEMA_SQL:
        con.execute(sql)
    # 兼容旧表：补 reheated_at
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(memory_archive)")}
        if "reheated_at" not in cols:
            con.execute("ALTER TABLE memory_archive ADD COLUMN reheated_at TEXT")
    except sqlite3.Error:
        pass
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
            "SELECT source_id FROM memory_archive WHERE archived_at IS NOT NULL"
            " AND (reheated_at IS NULL OR reheated_at = '')")}
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


def row_month(row, now=None, con=None):
    """月份：优先 event_date，其次 memory_source.created_at（不依赖列序）。"""
    date = ""
    sid = None
    try:
        sid = int(row[0])
    except Exception:                                # noqa: BLE001
        sid = None
    if con is not None and sid is not None:
        try:
            cols = {r[1] for r in con.execute("PRAGMA table_info(memory_source)")}
            if "event_date" in cols:
                r = con.execute("SELECT created_at,event_date FROM memory_source"
                                " WHERE id=?", (sid,)).fetchone()
                if r:
                    date = str(r[1] or "") or str(r[0] or "")
            else:
                r = con.execute("SELECT created_at FROM memory_source WHERE id=?",
                                (sid,)).fetchone()
                if r:
                    date = str(r[0] or "")
        except sqlite3.Error:
            date = ""
    if not date:
        date = _row_created(row)
    m = date[:7]
    if len(m) == 7 and m[4] == "-" and m[:4].isdigit():
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
        groups.setdefault(row_month(r, now_dt, con=con), []).append(r)
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


def _fact_key(text):
    """同族键：(subject, event_or_action, place, time, object)。

    任一项不同 -> 不同族；event/action 都抽不出 -> 键不完整（不合并）。
    """
    sl = _slots(text)
    subject = sl.get("person")
    if not subject:
        try:
            import p1b_subject as P
            subject = (P.extract(str(text or "")) or {}).get("subject")
        except Exception:                            # noqa: BLE001
            subject = None
    if not subject and "我" in str(text or ""):
        subject = "self"
    event = sl.get("event") or None
    action = sl.get("action") or None
    event_or_action = event or action
    key = (subject, event_or_action, sl.get("place") or None,
           sl.get("time") or None, sl.get("object") or None)
    complete = bool(event_or_action) and bool(subject)
    return key, complete


def _key_of(text):
    key, complete = _fact_key(text)
    return key[0], key[1], not complete


def _read_archived_text(con, source_id):
    import hashlib
    import json as _json
    import zipfile
    row = con.execute(
        "SELECT zip, zip_sha, superseded_by, reheated_at FROM memory_archive"
        " WHERE source_id=?", (int(source_id),)).fetchone()
    if not row:
        return None, "not_archived"
    zip_path, zip_sha, _sup, reheated = row
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


def _created_of(con, source_id):
    try:
        r = con.execute("SELECT created_at FROM memory_source WHERE id=?",
                        (int(source_id),)).fetchone()
        return str(r[0]) if r and r[0] else ""
    except sqlite3.Error:
        return ""


def _newer(con, newer_id, older_id, older_created):
    """按 memory_source.created_at 比较；解析失败回退 id 比较（保守）。"""
    from datetime import datetime as _dt
    c_new = _created_of(con, newer_id)
    try:
        return _dt.fromisoformat(c_new) > _dt.fromisoformat(older_created)
    except Exception:                                # noqa: BLE001
        try:
            if c_new and older_created:
                return c_new > older_created
        except Exception:                            # noqa: BLE001
            pass
        return int(newer_id) > int(older_id)


def reheat_plan(con, source_id, live_rows, trace_id=None, audit=False):
    """纯函数：校验归档 -> 抽槽 -> 与 live 比较；只返回 plan，不写 DB。"""
    try:
        r0 = con.execute("SELECT reheated_at FROM memory_archive WHERE source_id=?",
                         (int(source_id),)).fetchone()
        if r0 and r0[0]:
            plan0 = {"source_id": int(source_id), "action": "skip",
                     "reason": "already_reheated", "subject": None,
                     "predicate": None, "superseded_by": None,
                     "unresolved": False}
            if audit:
                _audit(trace_id, "skip", "already_reheated", [int(source_id)], 1)
            return plan0
    except sqlite3.Error:
        pass
    text, err = _read_archived_text(con, source_id)
    plan = {"source_id": int(source_id), "action": "skip", "reason": err,
            "subject": None, "predicate": None, "superseded_by": None,
            "unresolved": False}
    if text is None:
        if audit:
            _audit(trace_id, plan["action"], plan["reason"], [int(source_id)], 1)
        return plan
    key, complete = _fact_key(text)
    subject, predicate = key[0], key[1]
    unresolved = not complete
    plan.update(subject=subject, predicate=predicate, unresolved=unresolved)
    if subject is None:
        plan.update(action="skip", reason="no_subject")
        if audit:
            _audit(trace_id, "skip", "no_subject", [int(source_id)], 1)
        return plan
    if not complete:
        plan.update(action="restore", reason="key_incomplete")
        if audit:
            _audit(trace_id, "restore", "key_incomplete", [int(source_id)], 1)
        return plan
    arch_created = _created_of(con, source_id)
    for r in live_rows or []:
        if int(r[0]) == int(source_id):
            continue
        k2, c2 = _fact_key(r[3] if len(r) > 3 else "")
        if not c2 or k2 != key:
            continue
        if int(r[0]) > int(source_id) and _newer(con, int(r[0]), source_id,
                                                 arch_created):
            plan.update(action="skip_superseded", reason="newer_same_family",
                        superseded_by=int(r[0]))
            return plan
    plan.update(action="restore", reason="no_newer")
    if audit:
        _audit(trace_id, plan["action"], plan["reason"],
               [plan["source_id"]] + ([plan["superseded_by"]]
                                      if plan.get("superseded_by") else []), 1)
    return plan

def reheat_execute(con, source_id, rows, block_builder, trace_id=None):
    """执行回热：仅 restore；原行保持（不新建），重设 archive.reheated_at，重建块。"""
    plan = reheat_plan(con, source_id, rows, trace_id=trace_id, audit=False)
    out = {"executed": False, "plan": plan, "block": None,
           "source_id": int(source_id)}
    if plan.get("action") != "restore":
        _audit(trace_id, "skip", plan.get("reason") or "not_restore",
               [int(source_id)], 1)
        return out
    ensure_schema(con)
    row = con.execute("SELECT id,name,text,created_at FROM memory_source WHERE id=?",
                      (int(source_id),)).fetchone()
    if not row:
        out["plan"] = dict(plan, action="skip", reason="source_row_missing")
        _audit(trace_id, "skip", "source_row_missing", [int(source_id)], 1)
        return out
    payload = {"id": int(row[0]), "name": str(row[1]), "text": str(row[2]),
               "created_at": str(row[3] or "")}
    block = block_builder(payload)
    con.execute("UPDATE memory_archive SET reheated_at=? WHERE source_id=?",
                (_now(), int(source_id)))
    con.commit()
    out.update(executed=True, block=block)
    _audit(trace_id, "restore", "reheat_execute",
           [int(source_id)] + ([plan["superseded_by"]]
                               if plan.get("superseded_by") else []), 1)
    return out