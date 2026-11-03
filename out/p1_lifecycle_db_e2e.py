# -*- coding: utf-8 -*-
"""P1 lifecycle DB-level verification (no service, no daily writes).

Builds a throwaway SQLite DB with 250 memory rows (mixed created_at), exercises
auto_archive / active_rows / fallback_archive / reheat_plan, checks idempotency,
corrupt-zip handling, and reports DB state at 199/200/201/250 rows.

Scope note: this is DB-level only — NOT a service-level E2E.
"""
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "tools")
import memory_lifecycle as L  # noqa: E402

TMP = Path("tmp/p1_lifecycle")
OUT = Path("out/P1-LIFECYCLE-DB-E2E.json")
NAMES = ["张伟", "李娜", "王强", "刘敏", "黄婷", "徐斌", "陈杰", "杨帆"]
MONTHS = ["2026-09", "2026-10", "2026-11"]


def make_db(path, n):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE memory_source(id INTEGER PRIMARY KEY, name TEXT,"
                " mode TEXT, text TEXT, a TEXT, b TEXT, c TEXT, d TEXT, created_at TEXT)")
    rows = []
    for i in range(1, n + 1):
        month = MONTHS[i % 3]
        text = "%s的车牌号是皖K·%05d" % (NAMES[i % len(NAMES)], i)
        created = "%s-%02dT10:00:00" % (month, 1 + (i % 27))
        rows.append((i, "mem-%05d" % i, "chat", text, "", "", "", "", created))
    con.executemany("INSERT INTO memory_source(id,name,mode,text,a,b,c,d,created_at)"
                    " VALUES(?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    L.ensure_schema(con)
    return con, rows


def main():
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    arch = TMP / "archive"
    now = datetime(2026, 11, 4, 12, 0, 0)
    report = {"scope": "DB-level only (no service E2E)", "now": now.isoformat(),
              "days": 21}

    # ---------- A. auto_archive on 250 rows, 200 candidates ----------
    con, rows = make_db(TMP / "a.db", 250)
    L.record_access(con, list(range(1, 51)))          # fresh access -> not candidates
    r1 = L.auto_archive(con, rows, now, str(arch), days=21)
    marks1 = con.execute("SELECT COUNT(*) FROM memory_archive").fetchone()[0]
    active1 = len(L.active_rows(con, rows))
    zips1 = sorted(p.name for p in arch.glob("*.zip"))
    r2 = L.auto_archive(con, rows, now, str(arch), days=21)
    marks2 = con.execute("SELECT COUNT(*) FROM memory_archive").fetchone()[0]
    report["auto_archive"] = {
        "rows_total": len(rows),
        "candidates": len(r1["candidates"]),
        "months": {k: len(v) for k, v in r1["months"].items()},
        "zips": zips1,
        "archive_marks": marks1,
        "active_rows": active1,
        "idempotent_second_run_candidates": len(r2["candidates"]),
        "idempotent_marks_unchanged": marks1 == marks2,
        "active_plus_archived_equals_total": active1 + marks1 == len(rows),
    }

    # ---------- B. fallback_archive: hit old facts, skip bad zip ----------
    con.execute("UPDATE memory_archive SET superseded_by=NULL")
    con.commit()
    hits_ok = L.fallback_archive(con, "皖K·00007 车牌", str(arch), max_hits=5)
    # corrupt every zip -> sha mismatch -> skipped
    for p in arch.glob("*.zip"):
        with open(p, "ab") as fh:
            fh.write(b"CORRUPT")
    hits_bad = L.fallback_archive(con, "皖K·00007 车牌", str(arch), max_hits=5)
    report["fallback_archive"] = {
        "hits_before_corrupt": [{"id": h["id"], "score": h["score"]} for h in hits_ok[:3]],
        "hit_n_before": len(hits_ok),
        "hits_after_corrupt": len(hits_bad),
        "bad_zip_skipped_without_error": len(hits_bad) == 0,
    }

    # ---------- C. reheat_plan: newer -> skip_superseded, none -> restore ----------
    con2, rows2 = make_db(TMP / "c.db", 6)
    arch2 = TMP / "archive2"
    L.auto_archive(con2, rows2, now, str(arch2), days=21)
    # id 2 ("王强的车牌…") gets a newer live row of the same subject/predicate
    newer = (99, "mem-00099", "chat", "王强的车牌号是皖K·99999", "", "", "", "",
             "2026-12-15T10:00:00")
    live = list(rows2) + [newer]
    plan_newer = L.reheat_plan(con2, 2, live)
    plan_restore = L.reheat_plan(con2, 1, live)
    report["reheat_plan"] = {
        "with_newer": {"id": 2, "action": plan_newer["action"], "reason": plan_newer["reason"],
                       "superseded_by": plan_newer["superseded_by"]},
        "without_newer": {"id": 1, "action": plan_restore["action"], "reason": plan_restore["reason"]},
    }

    # ---------- D. capacity-state check at 199/200/201/250 ----------
    cap = {}
    for n in (199, 200, 201, 250):
        c, rr = make_db(TMP / ("cap%d.db" % n), n)
        L.record_access(c, [i for i in range(1, n + 1) if i % 5 == 0])
        a = TMP / ("cap%d_arch" % n)
        res = L.auto_archive(c, rr, now, str(a), days=21)
        marks = c.execute("SELECT COUNT(*) FROM memory_archive").fetchone()[0]
        act = len(L.active_rows(c, rr))
        cap[str(n)] = {"rows": n, "candidates": len(res["candidates"]),
                       "archived": marks, "active": act,
                       "consistent": act + marks == n}
    report["capacity_state"] = cap
    report["verdict"] = "DB 级验证；非服务级 E2E"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())