# -*- coding: utf-8 -*-
"""P1 E2E · 6 chains on a COPY. expected_action is hard-coded BEFORE the run.

C1..C5: archived baseline row, then a NEW fact with a different _fact_key
        -> expected restore (must not be falsely skipped).
C6     : same _fact_key, newer value -> expected skip_superseded, and the old
        value must NOT become current (the newer row stays the kept one).
"""
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, "tools")
import chat_daily as D          # noqa: E402
import memory_lifecycle as L    # noqa: E402
import memory_source as ms      # noqa: E402
import archive_store as A       # noqa: E402
import sandbox_guard as SG      # noqa: E402

ROOT = Path(".").resolve()
WORK = ROOT / "tmp" / "p1_e2e6"
MODEL = r"D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf"

# ---- expected actions fixed here, before running -------------------------
CASES = [
    {"cid": "C1", "src": 4, "new": "我每周六早上去游泳。",
     "query": "我下周三去北京出差，对吧？", "want": "北京", "expected_action": "restore"},
    {"cid": "C2", "src": 5, "new": "我对尘螨过敏，挺厉害的。",
     "query": "我下周三去上海开会，对吧？", "want": "上海", "expected_action": "restore"},
    {"cid": "C3", "src": 6, "new": "我的签证 2029 年到期。",
     "query": "我下周三去广州出差，对吧？", "want": "广州", "expected_action": "restore"},
    {"cid": "C4", "src": 7, "new": "我每周日晚上练字。",
     "query": "我下周四去广州开会，对吧？", "want": "广州", "expected_action": "restore"},
    {"cid": "C5", "src": 8, "new": "我的车险 2027 年 8 月到期。",
     "query": "我下周五去杭州开会，对吧？", "want": "杭州", "expected_action": "restore"},
    {"cid": "C6", "src": None, "new": None,
     "query": "我的健身年卡多少钱？", "want": "两千六", "expected_action": "skip"},
]
SAME_KEY_V1 = "我每周二晚上八点去健身，年卡两千块。"
SAME_KEY_V2 = "我每周二晚上八点去健身，年卡两千六。"


def make_copy():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    db, blk = WORK / "chat.db", WORK / "blocks"
    shutil.copy2(ROOT / "kvmem" / "daily" / "chat.db", db)
    shutil.copytree(ROOT / "kvmem" / "daily" / "blocks", blk)
    con = sqlite3.connect(db)
    SG.rewrite_block_paths(con, blk)
    for _sid, p in con.execute("SELECT source_id,path FROM memory_block"):
        SG.assert_under(p, blk)
    con.commit()
    con.close()
    return db, blk


def archive_one(app, sid, arch, tag):
    row = {int(r[0]): r for r in app._rows()}[sid]
    zp = str(Path(arch) / ("2026-11-%s.zip" % tag))
    man = A.archive_rows([{"id": sid, "name": str(row[1]), "text": str(row[3]),
                           "created_at": str(row[8]) if len(row) > 8 else "",
                           "subject": None, "predicate": None,
                           "block_sha": None, "block_bytes": 0}], zp, zp + ".sidecar.json")
    L.archive_mark(app.con, [sid], zp, man["zip_sha256"])
    return zp


def main():
    db, blk = make_copy()
    arch = WORK / "archive"
    eng = D.make_real_engine(MODEL, n_ctx=32768, n_gpu_layers=28)
    app = D.DailyApp(eng, db_path=str(db), blocks_dir=str(blk),
                     sessions_dir=str(ROOT / "kvmem" / "daily" / "sessions"),
                     session_path="kvc.json", model_path=MODEL,
                     retrieval_mode="topk", topk=4, n_ctx=32768,
                     n_gpu_layers=28, log=False, lifecycle_cap=True,
                     lifecycle_archive=True, archive_dir=str(arch))
    L.ensure_schema(app.con)
    rows = {int(r[0]): r for r in app._rows()}
    out = []

    for c in CASES:
        item = {"cid": c["cid"], "expected_action": c["expected_action"],
                "query": c["query"], "want": c["want"]}
        if c["cid"] != "C6":
            sid = c["src"]
            item["archived_id"] = sid
            item["archived_key"] = list(L._fact_key(str(rows[sid][3]))[0])
            archive_one(app, sid, arch, c["cid"])
            app.remember(c["new"])
            new_id = max(int(r[0]) for r in app._rows())
            item["new_id"] = new_id
            item["new_key"] = list(L._fact_key(c["new"])[0])
            res = app.reheat(sid)
            plan = res.get("plan") or {}
            item.update(got=plan.get("action"), reason=plan.get("reason"),
                        superseded_by=plan.get("superseded_by"),
                        executed=res.get("executed"),
                        block_rebuilt=bool((res.get("block") or {}).get("path")
                                           and os.path.exists((res.get("block") or {})["path"])))
            ans = app.ask(c["query"])
            item["answer"] = ans.get("answer")
            item["answer_ok"] = c["want"] in str(ans.get("answer") or "")
        else:
            app.remember(SAME_KEY_V1)
            sid = max(int(r[0]) for r in app._rows())
            item["archived_id"] = sid
            item["archived_key"] = list(L._fact_key(SAME_KEY_V1)[0])
            archive_one(app, sid, arch, "C6")
            app.remember(SAME_KEY_V2)
            new_id = max(int(r[0]) for r in app._rows())
            item["new_id"] = new_id
            item["new_key"] = list(L._fact_key(SAME_KEY_V2)[0])
            item["same_key"] = item["archived_key"] == item["new_key"]
            res = app.reheat(sid)
            plan = res.get("plan") or {}
            active_ids = [int(r[0]) for r in app._rows()]
            item.update(got=plan.get("action"), reason=plan.get("reason"),
                        superseded_by=plan.get("superseded_by"),
                        executed=res.get("executed"),
                        old_still_archived=sid not in active_ids,
                        new_is_kept=new_id in active_ids)
            ans = app.ask(c["query"])
            item["answer"] = ans.get("answer")
            item["answer_ok"] = c["want"] in str(ans.get("answer") or "")
        item["pass"] = (item.get("got") == c["expected_action"]
                        and item.get("answer_ok") is True
                        and (item.get("block_rebuilt") is not False))
        out.append(item)
        print(json.dumps(item, ensure_ascii=False))

    ok = sum(1 for x in out if x["pass"])
    rep = {"scope": "copy only; rewrite_block_paths + assert_under",
           "expected_fixed_before_run": True,
           "cases": out, "passed": ok, "n": len(out), "gate": "6/6",
           "verdict": "PASS" if ok == len(out) else "FAIL"}
    (ROOT / "out" / "P1-E2E-6CHAIN.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print("MATCH", ok, "/", len(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())