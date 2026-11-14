# -*- coding: utf-8 -*-
"""200-row archive drill on tmp/p1arch-drill (never touches daily).

Calls memory_lifecycle.auto_archive directly (no --confirm-first-archive, so no
global unlock file is written). Verifies zip/manifest/sha/accounting, fallback
readback, archive_store.restore_plan, then drops archive tables + zips and
proves memory_source content is unchanged row-for-row.
"""
import glob
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime

sys.path.insert(0, "tools")
import archive_store as A          # noqa: E402
import memory_lifecycle as L       # noqa: E402
import memory_source as ms         # noqa: E402
import sandbox_guard as SG         # noqa: E402

W = "tmp/p1arch-drill"
DB = os.path.join(W, "chat.db")
BLK = os.path.join(W, "blocks")
ARCH = os.path.join(W, "archive")
t_all0 = time.perf_counter()
rep = {"schema": "p1_archive_drill200_v1", "workdir": W}


def dump_source(con):
    return con.execute("SELECT id,name,text,created_at FROM memory_source ORDER BY id").fetchall()


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy2("kvmem/daily/chat.db", DB)
    shutil.copytree("kvmem/daily/blocks", BLK)

    t0 = time.perf_counter()
    con = sqlite3.connect(DB)
    SG.rewrite_block_paths(con, BLK)
    for _sid, p in con.execute("SELECT source_id,path FROM memory_block"):
        SG.assert_under(p, BLK)
    con.commit()
    rep["rewrite_assert_s"] = round(time.perf_counter() - t0, 2)

    # build 200 rows (35% / 35% / 30%) with backdated created_at
    base = con.execute("SELECT path,n_tokens,n_bytes,built_at,model_path,model_size,"
                       "model_mtime,kv_type,state_version FROM memory_block ORDER BY source_id LIMIT 1").fetchone()
    con.execute("DELETE FROM memory_block")
    con.execute("DELETE FROM memory_source")
    t0 = time.perf_counter()
    spans = [("2026-05", 1, 70), ("2026-06", 71, 140), ("2026-07", 141, 200)]
    for month, lo, hi in spans:
        for i in range(lo, hi + 1):
            ca = "%s-%02dT09:00:00" % (month, (i % 27) + 1)
            con.execute(
                "INSERT INTO memory_source(id,tenant,scope,mode,name,label,text,source_hash,"
                "created_at,text_kind,contains_model_turns,is_excerpt,derived_from) "
                "VALUES(?,'default','private','chat',?,'日常记忆',?,?,?,'human_memory',0,0,NULL)",
                (i, "drill-%d" % i, "演练事实第%d条：我的工位是B区%d号" % (i, i % 9 + 1),
                 ms.sha256_text("drill%d" % i), ca))
            con.execute(
                "INSERT INTO memory_block(source_id,path,n_tokens,n_bytes,built_at,model_path,"
                "model_size,model_mtime,kv_type,state_version) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (i,) + tuple(base))
    con.commit()
    rep["build_s"] = round(time.perf_counter() - t0, 2)

    rows = [r for r in ms.block_rows(con) if r[5] is not None]
    before = dump_source(con)
    rep["rows"] = len(rows)

    # ---- auto_archive (direct call) ----
    t0 = time.perf_counter()
    res = L.auto_archive(con, rows, datetime(2026, 11, 5, 12, 0, 0), ARCH, days=21)
    rep["auto_archive_s"] = round(time.perf_counter() - t0, 2)
    archived = con.execute("SELECT COUNT(*) FROM memory_archive WHERE archived_at IS NOT NULL").fetchone()[0]
    active = len(L.active_rows(con, rows))
    zips = sorted(os.path.basename(z) for z in glob.glob(os.path.join(ARCH, "*.zip")))
    rep["archive"] = {"candidates": len(res["candidates"]), "months": {k: len(v) for k, v in res["months"].items()},
                      "zips": zips, "archived": archived, "active": active,
                      "accounting_ok": active + archived == len(rows)}

    # ---- zip / manifest / sha ----
    zpath = os.path.join(ARCH, zips[0])
    side = zpath + ".sidecar.json"
    man = json.load(open(side, encoding="utf-8"))
    sha_ok = hashlib.sha256(open(zpath, "rb").read()).hexdigest() == man.get("zip_sha256")
    rep["zip"] = {"name": zips[0], "bytes": os.path.getsize(zpath),
                  "entries": len(man.get("entries") or []),
                  "manifest_zip_sha256": man.get("zip_sha256"),
                  "recomputed_sha_match": sha_ok}

    # ---- fallback ----
    t0 = time.perf_counter()
    hits = L.fallback_archive(con, "我的工位是B区 工位", ARCH, max_hits=5)
    rep["fallback"] = {"hits": len(hits), "top": [(h["id"], h["score"]) for h in hits],
                       "s": round(time.perf_counter() - t0, 3)}

    # ---- restore_plan readback ----
    t0 = time.perf_counter()
    live_after = L.active_rows(con, rows)      # 归档后应为空
    plan_doc = A.restore_plan([{"id": int(r[0]), "subject": None, "predicate": None,
                                "text": str(r[3])} for r in live_after], zpath, side)
    plan = plan_doc.get("plan") or []
    acts = {}
    for x in plan:
        acts[x["action"]] = acts.get(x["action"], 0) + 1
    rep["restore_plan"] = {"entries": len(plan), "actions": acts,
                           "live_rows_passed": len(live_after),
                           "zip_sha256_match": plan_doc.get("zip_sha256") == man.get("zip_sha256"),
                           "s": round(time.perf_counter() - t0, 3)}

    # ---- rollback: drop archive/access + delete zips, source unchanged ----
    con.execute("DROP TABLE IF EXISTS memory_archive")
    con.execute("DROP TABLE IF EXISTS memory_access")
    con.commit()
    for z in glob.glob(os.path.join(ARCH, "*.zip")):
        os.remove(z)
    for s in glob.glob(os.path.join(ARCH, "*.sidecar.json")):
        os.remove(s)
    after = dump_source(con)
    rep["rollback"] = {"rows_before": len(before), "rows_after": len(after),
                       "content_identical": before == after,
                       "zips_left": len(glob.glob(os.path.join(ARCH, "*.zip")))}
    rep["total_s"] = round(time.perf_counter() - t_all0, 1)
    rep["ok"] = all([rep["archive"]["accounting_ok"], sha_ok,
                     rep["fallback"]["hits"] > 0, rep["rollback"]["content_identical"],
                     rep["restore_plan"]["entries"] > 0])
    json.dump(rep, open("out/P1-ARCHIVE-DRILL200.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()