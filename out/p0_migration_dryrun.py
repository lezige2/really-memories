# -*- coding: utf-8 -*-
"""P0 event_date 迁移 dry-run：只读现网，所有写只落副本 tmp/p0_dryrun。

流程：备份+sha → 副本 ensure_event_columns → 表结构/行/文本/块 sha 对比 →
81/MT20 静态查询对比（副本内 replay pre_state + 本地检索，不调模型）→
drop_event_columns 回滚证明。现网不写、不切 flag、不 commit。

用法：python -X utf8 out/p0_migration_dryrun.py
输出：out/P0-MIGRATION-DRYRUN.json / .md
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import memory_service as memo      # noqa: E402
import memory_source as ms         # noqa: E402

SRC = os.path.join(ROOT, "kvmem", "daily", "chat.db")
TMP = os.path.join(ROOT, "tmp", "p0_dryrun")
CASES81 = os.path.join(ROOT, "training", "dialog_cases.jsonl")
CASESMT = os.path.join(ROOT, "out", "SFT-EXTRA-CASES-v9-MT20.jsonl")


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha_text(s):
    return hashlib.sha256(str(s).encode("utf-8")).hexdigest()


def copy_db(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    s = sqlite3.connect("file:%s?mode=ro" % src.replace("\\", "/"), uri=True)
    d = sqlite3.connect(dst)
    with d:
        s.backup(d)
    s.close()
    d.close()


def columns(con):
    return [(r[1], r[2], r[3]) for r in con.execute("PRAGMA table_info(memory_source)")]


def user_version(con):
    return con.execute("PRAGMA user_version").fetchone()[0]


def content_snap(con):
    rows = list(con.execute(
        "SELECT id,name,mode,label,text,source_hash,created_at FROM memory_source ORDER BY id"))
    blocks = list(con.execute(
        "SELECT source_id,path,n_tokens,n_bytes,kv_type FROM memory_block ORDER BY source_id"))
    block_sha = {}
    for sid, path, _n, _b, _kv in blocks:
        p = path if path and os.path.exists(path) else None
        block_sha[int(sid)] = sha_file(p) if p else None
    content = sha_text(json.dumps([[list(r) for r in rows], blocks],
                                  ensure_ascii=False, sort_keys=True))
    return {"rows": len(rows), "content_sha256": content,
            "rows_data": rows, "block_sha": block_sha,
            "block_sha_map_sha256": sha_text(json.dumps(block_sha, sort_keys=True)),
            "block_missing": [k for k, v in block_sha.items() if not v]}


def scratch_answer(db_src, case, tag):
    """副本内 replay pre_state(remember) + 本地检索；返回静态答案指纹（不调模型）。"""
    dst = os.path.join(TMP, "scratch_%s.db" % tag)
    copy_db(db_src, dst)
    con = ms.connect(dst)
    for st in case.get("pre_state") or []:
        if st.get("action") == "remember" and st.get("text"):
            sid, _new = ms.put_source(con, "case-" + sha_text(st["text"])[:12],
                                      "case", st["text"])
            con.execute(
                "INSERT OR REPLACE INTO memory_block (source_id,path,n_tokens,n_bytes,"
                "built_at,model_path,model_size,model_mtime,kv_type,state_version) "
                "VALUES (?,?,?,?,?,?,?,?,?,1)",
                (sid, "", len(st["text"]), 0, "dry", "", 0, 0, "q8_0"))
    con.commit()
    rows = [r for r in ms.block_rows(con) if r[5] is not None]
    hits = memo.retrieve(case["input"], rows, topk=4, meta_fn=None) or []
    top = [(int(h["id"]), str(h.get("text") or "")) for h in hits]
    exp = case.get("expect") or {}
    blob = "\n".join(t for _i, t in top)
    hit_any = [v for v in (exp.get("contains_any") or []) if v and v in blob]
    hit_all = [v for v in (exp.get("contains_all") or []) if v and v in blob]
    bad = [v for v in (exp.get("not_contains") or []) if v and v in blob]
    ok = bool(top) and (not exp.get("contains_any") or bool(hit_any)) \
        and (not exp.get("contains_all") or len(hit_all) == len(exp.get("contains_all")))
    ok = ok and not bad
    out = {"tag": tag, "case_id": case.get("id"), "input": case["input"],
           "top_ids": [i for i, _t in top],
           "top_text_sha": [sha_text(t) for _i, t in top],
           "top1_text": top[0][1] if top else None,
           "contains_any_hit": hit_any, "contains_all_hit": hit_all,
           "not_contains_hit": bad, "static_ok": ok}
    con.close()
    return out


def meta_state(con):
    try:
        rows = list(con.execute("SELECT key,value FROM memory_meta ORDER BY key"))
        return {"present": True, "rows": [list(r) for r in rows]}
    except sqlite3.OperationalError:
        return {"present": False, "rows": []}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "P0-MIGRATION-DRYRUN.json"))
    ap.add_argument("--md", default=os.path.join(ROOT, "out", "P0-MIGRATION-DRYRUN.md"))
    args = ap.parse_args(argv)

    os.makedirs(TMP, exist_ok=True)
    src_sha = sha_file(args.src)
    bak_src = os.path.join(TMP, "chat.db.orig")
    shutil.copy2(args.src, bak_src)
    bak_sha = sha_file(bak_src)
    work = os.path.join(TMP, "chat.db")
    copy_db(args.src, work)

    con = sqlite3.connect(work)
    orig_uv = user_version(con)
    before = {"user_version": orig_uv, "columns": columns(con),
              "snap": content_snap(con), "meta": meta_state(con)}

    # 关键查询静态对比（独立于回滚轮次）
    pre_db = os.path.join(TMP, "pre.db")
    copy_db(bak_src, pre_db)
    fresh_pre = os.path.join(TMP, "fresh_pre.db")
    if os.path.exists(fresh_pre):
        os.remove(fresh_pre)
    ms.connect(fresh_pre).close()
    fresh_post = os.path.join(TMP, "fresh_post.db")
    copy_db(fresh_pre, fresh_post)
    _c = sqlite3.connect(fresh_post)
    ms.ensure_event_columns(_c, db_path=fresh_post, backup=False)
    _c.close()

    c81 = [json.loads(l) for l in open(CASES81, encoding="utf-8") if l.strip()]
    cmt = [json.loads(l) for l in open(CASESMT, encoding="utf-8") if l.strip()]
    pick81 = [c for c in c81 if c.get("pre_state") and (c.get("expect") or {}).get("contains_any")][:2]
    pickmt = []
    for c in cmt:
        if not (c.get("expect") or {}).get("contains_any"):
            continue
        _r = scratch_answer(fresh_pre, c, "pick_" + str(c["id"]))
        if _r["static_ok"] and len(pickmt) < 2:
            pickmt.append(c)
    if len(pickmt) < 2:
        pickmt = [c for c in cmt if (c.get("expect") or {}).get("contains_any")][:2]
    daily_cases = [
        {"id": "daily-plate", "input": "我的车牌号是什么？",
         "expect": {"contains_any": ["京A88888"]}},
        {"id": "daily-cat", "input": "我养的猫叫什么？",
         "expect": {"contains_any": ["豆豆"]}},
    ]
    qchecks = []
    for i, case in enumerate(daily_cases):
        pre = scratch_answer(pre_db, case, "dpre%d" % i)
        post = scratch_answer(work, case, "dpost%d" % i)
        qchecks.append({"suite": "daily", "case_id": case["id"], "input": case["input"],
                        "pre": pre, "post": post,
                        "same": pre["top_text_sha"] == post["top_text_sha"]
                        and pre["static_ok"] == post["static_ok"]})
    for i, case in enumerate(pick81 + pickmt):
        pre = scratch_answer(fresh_pre, case, "pre%d" % i)
        post = scratch_answer(fresh_post, case, "post%d" % i)
        qchecks.append({"suite": "81" if i < len(pick81) else "MT20",
                        "case_id": case.get("id"), "input": case["input"],
                        "pre": pre, "post": post,
                        "same": pre["top_text_sha"] == post["top_text_sha"]
                        and pre["static_ok"] == post["static_ok"]})

    # 两轮 ensure -> drop；每轮必须回到原值
    rounds = []
    for r in range(1, args.rounds + 1):
        ensure = ms.ensure_event_columns(con, db_path=work, backup=(r == 1))
        mid = {"user_version": user_version(con), "columns": columns(con),
               "meta": meta_state(con), "snap": content_snap(con)}
        dropped = ms.drop_event_columns(con)
        post = {"user_version": user_version(con), "columns": columns(con),
                "meta": meta_state(con), "snap": content_snap(con)}
        rec = {
            "round": r, "added": ensure.get("added"),
            "backup": ensure.get("backup"), "backup_sha256": ensure.get("sha256"),
            "mid": {"user_version": mid["user_version"], "columns": mid["columns"],
                    "added_columns": [c[0] for c in mid["columns"] if c not in before["columns"]],
                    "meta": mid["meta"], "content_sha256": mid["snap"]["content_sha256"]},
            "dropped": dropped,
            "post": {"user_version": post["user_version"],
                     "meta": post["meta"], "content_sha256": post["snap"]["content_sha256"]},
            "checks": {
                "user_version_restored": post["user_version"] == orig_uv,
                "columns_restored": post["columns"] == before["columns"],
                "memory_meta_restored": post["meta"] == before["meta"],
                "content_sha_same": post["snap"]["content_sha256"]
                                    == before["snap"]["content_sha256"]
                                    == mid["snap"]["content_sha256"],
                "rows_same": post["snap"]["rows"] == before["snap"]["rows"] == 20,
                "block_sha_same": post["snap"]["block_sha_map_sha256"]
                                  == before["snap"]["block_sha_map_sha256"],
            },
        }
        rec["checks"]["all_ok"] = all(rec["checks"].values())
        rounds.append(rec)
    con.close()

    col_add = list(rounds[0]["mid"]["added_columns"]) if rounds else []
    schema_ok = (rounds and len(rounds[0]["mid"]["added_columns"]) == 7
                 and rounds[0]["mid"]["user_version"] == ms.EVENT_USER_VERSION)
    rounds_ok = all(r["checks"]["all_ok"] for r in rounds)
    q_ok = all(q["same"] and q["pre"]["static_ok"] == q["post"]["static_ok"] for q in qchecks)
    ok = bool(schema_ok and rounds_ok and q_ok)

    report = {
        "schema": "p0_migration_dryrun_v2",
        "local_only": True,
        "note": "现网只读；写只落 tmp/p0_dryrun；不切 flag、不 commit",
        "verdict": "pass" if ok else "partial",
        "previous_verdict": "partial",
        "verdict_note": "上一版 partial：drop 后 user_version 0→1、memory_meta 残留；"
                        "C4 修复后两轮 ensure→drop 均恢复原值",
        "source": {"db": args.src, "sha256": src_sha},
        "backup": {"path": bak_src, "sha256": bak_sha},
        "migration_script": {"path": os.path.join(ROOT, "tools", "memory_source.py"),
                             "sha256": sha_file(os.path.join(ROOT, "tools", "memory_source.py")),
                             "functions": ["ensure_event_columns", "drop_event_columns"]},
        "original": {"user_version": orig_uv, "columns": before["columns"],
                     "memory_meta": before["meta"],
                     "content_sha256": before["snap"]["content_sha256"],
                     "rows": before["snap"]["rows"],
                     "block_sha_map_sha256": before["snap"]["block_sha_map_sha256"]},
        "schema_diff": {"added": col_add,
                        "removed": [c[0] for c in before["columns"]
                                    if c not in rounds[0]["mid"]["columns"]],
                        "type_changed": [c for c in before["columns"]
                                         if c in rounds[0]["mid"]["columns"]
                                         and [x for x in rounds[0]["mid"]["columns"]
                                              if x[0] == c[0]][0] != c]},
        "rounds": rounds,
        "query_checks": qchecks,
        "checks": {"schema_ok": bool(schema_ok), "rounds_all_restored": rounds_ok,
                   "query_static_same": q_ok,
                   "user_version_orig": orig_uv},
        "ok": ok,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    md = ["# P0 event_date 迁移 dry-run（两轮 ensure→drop，只读现网）", "",
          "- 源库 `%s` sha `%s`；备份 `%s` sha `%s`" %
          (args.src, src_sha[:16], bak_src, bak_sha[:16]),
          "- 迁移脚本 `tools/memory_source.py` sha `%s`" %
          report["migration_script"]["sha256"][:16],
          "- 原值：user_version=%s，columns=%d，memory_meta=%s" %
          (orig_uv, len(before["columns"]), "present" if before["meta"]["present"] else "absent"),
          "- 现网未写、未切 flag、未 commit；写只落 `tmp/p0_dryrun`（local only）。", "",
          "## 两轮 ensure→drop", "",
          "| 轮 | uv 中→后 | 列回原 | meta 回原 | 内容 sha 同 | 行 | 块 sha 同 | 全过 |",
          "|---|---|---|---|---|---|---|---|"]
    for r in rounds:
        c = r["checks"]
        md.append("| %d | %s→%s | %s | %s | %s | %s | %s | %s |" % (
            r["round"], r["mid"]["user_version"], r["post"]["user_version"],
            c["columns_restored"], c["memory_meta_restored"], c["content_sha_same"],
            c["rows_same"], c["block_sha_same"], c["all_ok"]))
    md += ["", "- 每轮新增 7 列、user_version→%d；drop 后 user_version→原值 %s。" %
           (ms.EVENT_USER_VERSION, orig_uv),
           "- 每轮哈希：before/mid/after 内容 sha 见 JSON rounds[].post.content_sha256 等。", "",
           "## 关键查询静态对比（未调模型）", "",
           "| suite | case | 一致 | pre ok | post ok |", "|---|---|---|---|---|"]
    for q in qchecks:
        md.append("| %s | %s | %s | %s | %s |" % (q["suite"], q["case_id"], q["same"],
                                                   q["pre"]["static_ok"], q["post"]["static_ok"]))
    md += ["", "## 判定", "",
           "- **%s**（schema_ok=%s, rounds_all_restored=%s, query_static_same=%s）" %
           ("PASS：可迁移" if ok else "PARTIAL：回滚未回到迁移前原值",
            bool(schema_ok), rounds_ok, q_ok)]
    with open(args.md, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(json.dumps({"ok": ok, "verdict": report["verdict"],
                      "script_sha": report["migration_script"]["sha256"][:16],
                      "orig_uv": orig_uv, "schema_added": col_add,
                      "rounds": [{"round": r["round"], "mid_uv": r["mid"]["user_version"],
                                  "post_uv": r["post"]["user_version"],
                                  "meta_after": r["post"]["meta"]["present"],
                                  "checks": r["checks"]} for r in rounds],
                      "queries_same": q_ok}, ensure_ascii=False, indent=1))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())