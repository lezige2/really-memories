# -*- coding: utf-8 -*-
"""P1 E2E on COPIES only: 5 same-family chains + 199/200/201 capacity boundary.

Safety: every copy first runs rewrite_block_paths() and assert_under() so no
absolute path can point back at kvmem/daily. daily is never opened for writing.
"""
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "tools")
import chat_daily as D          # noqa: E402
import memory_lifecycle as L    # noqa: E402
import memory_source as ms      # noqa: E402
import archive_store as A       # noqa: E402
import sandbox_guard as SG      # noqa: E402

ROOT = Path(".").resolve()
WORK = ROOT / "tmp" / "p1_e2e"
MODEL = r"D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf"
DAILY_DB = ROOT / "kvmem" / "daily" / "chat.db"
DAILY_BLOCKS = ROOT / "kvmem" / "daily" / "blocks"


def make_copy(tag):
    d = WORK / tag
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    db = d / "chat.db"
    blk = d / "blocks"
    shutil.copy2(DAILY_DB, db)
    shutil.copytree(DAILY_BLOCKS, blk)
    con = sqlite3.connect(db)
    SG.rewrite_block_paths(con, blk)
    for sid, p in con.execute("SELECT source_id,path FROM memory_block"):
        SG.assert_under(p, blk)                     # hard guard: never daily
    con.commit()
    con.close()
    return d, db, blk


def build_app(eng, db, blk, archive_dir=None, cap=False):
    app = D.DailyApp(eng, db_path=str(db), blocks_dir=str(blk),
                     sessions_dir=str(ROOT / "kvmem" / "daily" / "sessions"),
                     session_path="kvc.json", model_path=MODEL,
                     retrieval_mode="topk", topk=4, n_ctx=32768,
                     n_gpu_layers=28, log=False, lifecycle_cap=cap,
                     lifecycle_archive=bool(archive_dir),
                     archive_dir=(str(archive_dir) if archive_dir else None))
    L.ensure_schema(app.con)
    return app


def archive_one(app, sid, zip_name, archive_dir):
    row = {int(r[0]): r for r in app._rows()}[sid]
    zp = str(Path(archive_dir) / zip_name)
    man = A.archive_rows([{"id": sid, "name": str(row[1]), "text": str(row[3]),
                           "created_at": str(row[8]) if len(row) > 8 else "",
                           "subject": None, "predicate": None,
                           "block_sha": None, "block_bytes": 0}], zp, zp + ".sidecar.json")
    L.archive_mark(app.con, [sid], zp, man["zip_sha256"])
    return zp


def chains(app, arch):
    rep = []
    cases = [
        # (id, new text, expect)
        (1, "我每周三晚上七点有组会，地点改到C座201。", "skip_superseded"),   # same key 组会
        (2, "我下周三要去上海开会。", "restore"),                              # 组会 vs 开会
        (4, "我下周三要去上海开会。", "restore"),                              # 出差 vs 开会
        (5, "我下周三要去北京出差。", "restore"),                              # 开会 vs 出差
    ]
    for sid, new_text, expect in cases:
        zp = archive_one(app, sid, "2026-11-%02d.zip" % sid, arch)
        before = len(app._rows())
        app.remember(new_text)
        new_id = max(int(r[0]) for r in app._rows())
        res = app.reheat(sid)
        plan = res.get("plan") or {}
        item = {"source_id": sid, "archived_zip": os.path.basename(zp),
                "new_text": new_text, "new_id": new_id, "expected": expect,
                "got": plan.get("action"), "reason": plan.get("reason"),
                "superseded_by": plan.get("superseded_by"),
                "executed": res.get("executed"),
                "block_rebuilt": bool((res.get("block") or {}).get("path")
                                      and os.path.exists((res.get("block") or {})["path"])),
                "active_before_new": before, "active_after": len(app._rows())}
        rep.append(item)
    # 5th chain: 评审会（新建一条→归档→加组会）
    app.remember("我周五下午三点有评审会，地点在3号会议室。")
    pid = max(int(r[0]) for r in app._rows())
    zp = archive_one(app, pid, "2026-11-99.zip", arch)
    app.remember("我周四上午十点有组会，线上。")
    res = app.reheat(pid)
    plan = res.get("plan") or {}
    rep.append({"source_id": pid, "archived_zip": os.path.basename(zp),
                "new_text": "我周四上午十点有组会，线上。", "new_id": None,
                "expected": "restore", "got": plan.get("action"),
                "reason": plan.get("reason"), "superseded_by": plan.get("superseded_by"),
                "executed": res.get("executed"),
                "block_rebuilt": bool((res.get("block") or {}).get("path")
                                      and os.path.exists((res.get("block") or {})["path"])),
                "active_before_new": None, "active_after": len(app._rows())})
    return rep


def boundary(eng):
    out = {}
    for n in (199, 200, 201):
        d, db, blk = make_copy("cap%d" % n)
        con = sqlite3.connect(db)
        cur = con.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0]
        for i in range(cur + 1, n + 1):
            con.execute("INSERT INTO memory_source(tenant,scope,mode,name,label,text,"
                        "source_hash,created_at,text_kind,contains_model_turns,is_excerpt,"
                        "derived_from) VALUES('default','private','chat',?,'日常记忆',?,?,?,"
                        "'human_memory',0,0,NULL)",
                        ("cap-%d" % i, "填充句%d" % i, ms.sha256_text("填充%d" % i),
                         "2026-10-01T10:00:00"))
        # give every synthetic row a memory_block row so _rows() counts it
        base = con.execute("SELECT path,n_tokens,n_bytes,built_at,model_path,"
                           "model_size,model_mtime,kv_type,state_version "
                           "FROM memory_block ORDER BY source_id LIMIT 1").fetchone()
        have = {r[0] for r in con.execute("SELECT source_id FROM memory_block")}
        for sid in [r[0] for r in con.execute("SELECT id FROM memory_source")]:
            if sid in have:
                continue
            con.execute("INSERT INTO memory_block(source_id,path,n_tokens,n_bytes,built_at,"
                        "model_path,model_size,model_mtime,kv_type,state_version) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?)", (sid,) + tuple(base))
        con.commit()
        total = con.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0]
        con.close()
        row = {"rows": total}
        for cap in (False, True):
            app = build_app(eng, db, blk, cap=cap)
            try:
                app.remember("边界短句%d" % n)
                ok, err = True, None
            except D.DailyError as exc:
                ok, err = False, getattr(exc, "code", str(exc))
            rows_after = len(app._rows())
            archived = con_archived(app.con)
            row["cap_%s" % ("on" if cap else "off")] = {
                "write_ok": ok, "error": err, "active_after": rows_after,
                "archived": archived, "accounting_ok": rows_after + archived <= total + 1}
            app.con.close()
        out[str(n)] = row
    return out


def con_archived(con):
    try:
        return con.execute("SELECT COUNT(*) FROM memory_archive WHERE archived_at IS NOT NULL").fetchone()[0]
    except sqlite3.Error:
        return 0


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    eng = D.make_real_engine(MODEL, n_ctx=32768, n_gpu_layers=28)
    d, db, blk = make_copy("chain")
    arch = d / "archive"
    app = build_app(eng, db, blk, archive_dir=arch)
    cr = chains(app, arch)
    chain_ok = all(x["got"] == x["expected"] for x in cr)
    chain_rep = {"scope": "copy only; blocks rewritten + assert_under",
                 "cases": cr, "all_expected": chain_ok}
    app.con.close()

    bd = boundary(eng)
    b_ok = (bd["200"]["cap_off"]["write_ok"] is False and bd["201"]["cap_off"]["write_ok"] is False
            and all(bd[str(n)]["cap_on"]["write_ok"] for n in (199, 200, 201)))
    bound_rep = {"scope": "copy only; blocks rewritten + assert_under",
                 "results": bd, "boundary_ok": b_ok}

    (ROOT / "out" / "P1-E2E-5CHAIN.json").write_text(
        json.dumps(chain_rep, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "out" / "P1-E2E-BOUNDARY.json").write_text(
        json.dumps(bound_rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(chain_rep, ensure_ascii=False, indent=1))
    print(json.dumps(bound_rep, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())