# -*- coding: utf-8 -*-
"""P1 归档 CLI（local only；默认 dry-run；不碰 daily、不自动搬）。

子命令：
  list    --zip Z --sidecar S
  archive --rows rows.json | --db copy.db  --zip Z --sidecar S [--apply]
  restore --zip Z --sidecar S [--live live.json] [--out restored.json] [--apply]

默认 dry-run：只打印计划，不写任何文件；`--apply` 才落 zip/sidecar/restored.json。
restore 只把计划写到 JSON（副本），绝不写 daily；防覆盖沿用 archive_store.superseded_by。
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import archive_store as A  # noqa: E402


def load_rows(path):
    rows = json.load(open(path, encoding="utf-8"))
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("items") or []
    return [dict(r) for r in rows]


def rows_from_db(db_path):
    """只读副本导出 rows；不改副本。"""
    con = sqlite3.connect("file:%s?mode=ro" % db_path.replace("\\", "/"), uri=True)
    try:
        out = []
        for r in con.execute("SELECT id,name,text,created_at FROM memory_source ORDER BY id"):
            item = {"id": int(r[0]), "name": str(r[1]), "text": str(r[2]),
                    "created_at": str(r[3])}
            try:
                import p1b_subject as P
                info = P.extract(item["text"]) or {}
                item["subject"] = info.get("subject")
                item["predicate"] = info.get("predicate")
                item["block_sha"] = None
                item["block_bytes"] = 0
            except Exception:                        # noqa: BLE001
                pass
            out.append(item)
        return out
    finally:
        con.close()


def _default_paths(name):
    d = os.path.join(ROOT, "out", "p1b")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name + ".zip"), os.path.join(d, name + ".sidecar.json")


def cmd_archive(args):
    A.assert_local_only([args.zip, args.sidecar])
    rows = load_rows(args.rows) if args.rows else rows_from_db(args.db)
    plan = {"action": "archive", "n": len(rows), "zip": args.zip,
            "sidecar": args.sidecar, "apply": bool(args.apply),
            "ids": [int(r["id"]) for r in rows][:50]}
    if not args.apply:
        plan["dry_run"] = True
        return plan
    manifest = A.archive_rows(rows, args.zip, args.sidecar)
    idx_path = args.index or os.path.join(
        os.path.dirname(os.path.abspath(args.zip)), "index.json")
    idx = A.merge_index(A.load_index(idx_path), [dict(manifest, zip=args.zip)])
    A.save_index(idx, idx_path)
    plan.update({"dry_run": False, "zip_sha256": manifest["zip_sha256"],
                 "manifest": args.zip + ".manifest.json",
                 "index": idx_path,
                 "index_months": sorted(idx["months"])})
    return plan


def cmd_restore(args):
    A.assert_local_only([args.zip, args.sidecar])
    live = load_rows(args.live) if args.live else []
    plan = A.restore_plan(live, args.zip, args.sidecar)
    summary = {
        "restore": sum(1 for x in plan["plan"] if x["action"] == "restore"),
        "superseded": sum(1 for x in plan["plan"] if x["action"] == "skip_superseded"),
    }
    out = {"action": "restore", "apply": bool(args.apply), "summary": summary,
           "plan": plan, "out": args.out, "dry_run": not args.apply}
    if args.apply and args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        out["written"] = args.out
    return out


def cmd_scan(args):
    rows = load_rows(args.rows)
    refs = json.load(open(args.refs, encoding="utf-8")) if args.refs else {}
    sup = json.load(open(args.superseded, encoding="utf-8")) if args.superseded else {}
    marks = [int(x) for x in (args.marks or [])]
    now = args.now or datetime.now().isoformat(timespec="seconds")
    cand = A.scan_candidates(rows, now, days=args.days, refs=refs,
                             superseded=sup, marks=marks)
    out = {"action": "scan", "now": now, "days": args.days,
           "n_rows": len(rows), "n_candidates": len(cand),
           "candidates": cand, "apply": bool(args.apply)}
    if args.apply:
        path = args.out or os.path.join(ROOT, "out", "p1b", "scan.json")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        out["written"] = path
    return out


def cmd_fallback(args):
    if getattr(args, "db", None):
        import memory_lifecycle as L
        con = sqlite3.connect("file:%s?mode=ro" % args.db.replace("\\", "/"),
                              uri=True)
        try:
            hits = L.fallback_archive(con, args.query, args.archive_dir,
                                      max_hits=args.max_hits)
        finally:
            con.close()
        return {"action": "fallback", "query": args.query, "db": args.db,
                "archive_dir": args.archive_dir, "dry_run": True, "hits": hits}
    idx_path = args.index or os.path.join(
        os.path.dirname(os.path.abspath(args.zip)), "index.json")
    index = A.load_index(idx_path)
    res = A.fallback_months(args.query, index, max_months=args.max_months)
    res.update({"action": "fallback", "index": idx_path,
                "verify": A.verify_index(index), "apply": bool(args.apply)})
    if args.apply:
        path = args.out or os.path.join(ROOT, "out", "p1b", "fallback.json")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        res["written"] = path
    return res


def cmd_reheat(args):
    A.assert_local_only([args.zip, args.sidecar, args.out])
    live = load_rows(args.live) if args.live else []
    plan = A.reheat_plan(live, args.zip, args.sidecar)
    out = {"action": "reheat", "apply": bool(args.apply), "summary": plan["summary"],
           "whole_chain": True, "plan": plan, "dry_run": not args.apply,
           "out": args.out}
    if args.apply and args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        out["written"] = args.out
    return out


def cmd_list(args):
    A.assert_local_only([args.zip, args.sidecar])
    m = A.load_archive(args.zip, args.sidecar)
    return {"action": "list", "n": m["n"], "zip_sha256": m["zip_sha256"],
            "entries": [{k: e.get(k) for k in
                         ("id", "subject", "predicate", "value", "created_at")}
                        for e in m["entries"]]}


def build_parser():
    ap = argparse.ArgumentParser(description="P1 archive admin (local only, dry-run default)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--zip", default=None)
        p.add_argument("--sidecar", default=None)
        p.add_argument("--apply", action="store_true", default=False)

    p = sub.add_parser("list")
    common(p)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("archive")
    common(p)
    p.add_argument("--rows", default=None, help="显式 rows JSON")
    p.add_argument("--db", default=None, help="只读副本 db（不写）")
    p.add_argument("--index", default=None, help="月份索引（默认 out/p1b/index.json）")
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("scan")
    common(p)
    p.add_argument("--rows", required=True)
    p.add_argument("--days", type=int, default=21)
    p.add_argument("--refs", default=None, help="sidecar 引用计数 JSON {id:count}")
    p.add_argument("--superseded", default=None, help="superseded JSON {id:new_id}")
    p.add_argument("--marks", nargs="*", default=None, help="用户显式标记 id")
    p.add_argument("--now", default=None)
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("fallback")
    common(p)
    p.add_argument("--query", required=True)
    p.add_argument("--db", default=None, help="只读副本：走 memory_archive 兜底")
    p.add_argument("--archive-dir", default=os.path.join(ROOT, "out", "archive"))
    p.add_argument("--max-hits", type=int, default=5)
    p.add_argument("--index", default=None, help="月份索引（默认 out/p1b/index.json）")
    p.add_argument("--max-months", type=int, default=2)
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_fallback)

    p = sub.add_parser("reheat")
    common(p)
    p.add_argument("--live", default=None)
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_reheat)

    p = sub.add_parser("restore")
    common(p)
    p.add_argument("--live", default=None, help="当前 live rows JSON（防覆盖用）")
    p.add_argument("--out", default=None, help="恢复计划 JSON（副本）")
    p.set_defaults(func=cmd_restore)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    if not args.zip:
        args.zip, args.sidecar = _default_paths(args.cmd)
    elif not args.sidecar:
        args.sidecar = args.zip + ".sidecar.json"
    if args.cmd == "archive" and not (args.rows or args.db):
        ap.error("archive 需要 --rows 或 --db（不接受 daily 自动）")
    try:
        res = args.func(args)
    except Exception as exc:                         # noqa: BLE001
        print(json.dumps({"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)},
                         ensure_ascii=False))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())