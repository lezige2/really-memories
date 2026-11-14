# -*- coding: utf-8 -*-
"""One real reheat closed loop on a daily COPY (never touches daily).

Covers: archive one short fact -> active excludes it -> reheat rebuilds the block
-> ask answers correctly -> second reheat says already_reheated -> a same-family
newer row makes an older archive skip_superseded.
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

ROOT = Path(".").resolve()
WORK = ROOT / "kvmem" / "reheat"
OUT = ROOT / "out" / "P1-REHEAT-LOOP.json"
MODEL = r"D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf"


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    db = WORK / "chat.db"
    blocks = WORK / "blocks"
    shutil.copy2(ROOT / "kvmem" / "daily" / "chat.db", db)
    shutil.copytree(ROOT / "kvmem" / "daily" / "blocks", blocks)
    arch = WORK / "archive"

    eng = D.make_real_engine(MODEL, n_ctx=32768, n_gpu_layers=28)
    app = D.DailyApp(eng, db_path=str(db), blocks_dir=str(blocks),
                     sessions_dir=str(ROOT / "kvmem" / "daily" / "sessions"),
                     session_path="kvc.json", model_path=MODEL,
                     retrieval_mode="topk", topk=4, n_ctx=32768,
                     n_gpu_layers=28, log=False)
    con = app.con
    L.ensure_schema(con)
    rows = app._rows()
    by_id = {int(r[0]): r for r in rows}
    # pick a fact whose (subject,predicate) is unique in the library, and another
    # whose family has a newer row (for the superseded branch)
    keys = {int(r[0]): L._key_of(str(r[3]))[:2] for r in rows}
    counts = {}
    for k in keys.values():
        counts[k] = counts.get(k, 0) + 1
    ASK = {14: ("我的猫叫什么？", "豆豆"), 12: ("我的车牌号是多少？", "京A88888"),
           2: ("我的组会在哪开？", "302")}
    uniq = [i for i, k in keys.items() if counts[k] == 1 and len(str(by_id[i][3])) < 40]
    pref = [i for i in ASK if i in uniq]
    sid = (pref or sorted(uniq))[0]
    fam = {}
    for i, k in keys.items():
        fam.setdefault(k, []).append(i)
    multi = [v for k, v in fam.items() if k[0] and k[1] and len(v) > 1]
    sid2 = sorted(multi[0])[0] if multi else 1
    rep = {"scope": "copy only; daily untouched", "source_id": sid}

    # 1) archive exactly one short fact
    row = by_id[sid]
    zip_path = str(arch / "2026-11.zip")
    side = zip_path + ".sidecar.json"
    man = A.archive_rows([{"id": sid, "name": str(row[1]), "text": str(row[3]),
                           "created_at": str(row[8]) if len(row) > 8 else "",
                           "subject": None, "predicate": None,
                           "block_sha": None, "block_bytes": 0}], zip_path, side)
    L.archive_mark(con, [sid], zip_path, man["zip_sha256"])
    active_after_archive = [int(r[0]) for r in L.active_rows(con, rows)]
    rep["archive"] = {
        "archived_id": sid, "zip": zip_path, "zip_sha256": man["zip_sha256"],
        "zip_exists": os.path.exists(zip_path),
        "active_excludes_it": sid not in active_after_archive,
        "active_n": len(active_after_archive),
    }

    # 2) remove its block file first, so a rebuild is provable
    bpath = con.execute("SELECT path FROM memory_block WHERE source_id=?", (sid,)).fetchone()
    removed = False
    if bpath and os.path.exists(bpath[0]):
        os.remove(bpath[0]); removed = True
    rep["block_removed_before_reheat"] = removed
    before_blocks = len(list(blocks.glob("*")))
    r1 = app.reheat(sid)
    blk = r1.get("block") or {}
    after_blocks = len(list(blocks.glob("*")))
    row_arch = con.execute("SELECT reheated_at FROM memory_archive WHERE source_id=?",
                           (sid,)).fetchone()
    rep["reheat_1"] = {
        "executed": r1.get("executed"), "plan_action": (r1.get("plan") or {}).get("action"),
        "block_id": blk.get("block_id"), "block_path": blk.get("path"),
        "block_exists": bool(blk.get("path") and os.path.exists(blk["path"])),
        "n_tokens": blk.get("n_tokens"),
        "duplicate_blocks": r1.get("duplicate_blocks"),
        "archive_record_kept": bool(con.execute(
            "SELECT 1 FROM memory_archive WHERE source_id=?", (sid,)).fetchone()),
        "reheated_at": row_arch[0] if row_arch else None,
        "blocks_before": before_blocks, "blocks_after": after_blocks,
    }

    # 3) ask the fact
    q, want = ASK.get(sid, ("我的猫叫什么？", "豆豆"))
    ans = app.ask(q)
    rep["ask"] = {"question": q, "expected": want, "answer": ans.get("answer"),
                  "block_ids": ans.get("block_ids"),
                  "answer_has_expected": want in str(ans.get("answer") or ""),
                  "state": ans.get("state")}

    # 4) second reheat -> already_reheated, no new block
    r2 = app.reheat(sid)
    blocks_after2 = len(list(blocks.glob("*")))
    rep["reheat_2"] = {"executed": r2.get("executed"),
                       "reason": (r2.get("plan") or {}).get("reason"),
                       "blocks_after": blocks_after2,
                       "no_new_block": blocks_after2 == after_blocks}

    # 5) older archive + newer same-family row -> skip_superseded
    row2 = by_id[sid2]
    zip2 = str(arch / "2026-10.zip")
    man2 = A.archive_rows([{"id": sid2, "name": str(row2[1]), "text": str(row2[3]),
                            "created_at": str(row2[8]) if len(row2) > 8 else "",
                            "subject": None, "predicate": None,
                            "block_sha": None, "block_bytes": 0}], zip2, zip2 + ".sidecar.json")
    L.archive_mark(con, [sid2], zip2, man2["zip_sha256"])
    con.execute("INSERT INTO memory_source(tenant,scope,mode,name,label,text,source_hash,"
                "created_at,text_kind,contains_model_turns,is_excerpt,derived_from) "
                "VALUES('default','private','chat','mem-newer','日常记忆',?,?,?,"
                "'human_memory',0,0,NULL)",
                ("我每周三晚上七点有组会，地点改到C座201了。", ms.sha256_text("x"), "2027-01-01T10:00:00"))
    con.commit()
    new_id = con.execute("SELECT MAX(id) FROM memory_source").fetchone()[0]
    r3 = app.reheat(sid2)
    rep["reheat_superseded"] = {"archived_id": sid2, "newer_live_id": int(new_id),
                                "executed": r3.get("executed"),
                                "plan_action": (r3.get("plan") or {}).get("action"),
                                "reason": (r3.get("plan") or {}).get("reason"),
                                "superseded_by": (r3.get("plan") or {}).get("superseded_by")}
    rep["verdict"] = ("closed loop PASS" if all([
        rep["archive"]["active_excludes_it"], rep["reheat_1"]["executed"],
        rep["reheat_1"]["block_exists"], rep["reheat_1"]["duplicate_blocks"] == 0,
        rep["reheat_1"]["archive_record_kept"], bool(rep["reheat_1"]["reheated_at"]),
        rep["ask"]["answer_has_expected"], rep["reheat_2"]["reason"] == "already_reheated",
        rep["reheat_2"]["no_new_block"],
        rep["reheat_superseded"]["plan_action"] == "skip_superseded",
    ]) else "closed loop FAIL")
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())