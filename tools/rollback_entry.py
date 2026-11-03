# -*- coding: utf-8 -*-
"""固定回滚入口（P1 日常化；local-only；默认 dry-run）。

用法：
  python -X utf8 tools/rollback_entry.py backup  --db X [--out Y] [--apply]
  python -X utf8 tools/rollback_entry.py restore --backup Y --target Z [--sha H] [--force] [--apply]
  python -X utf8 tools/rollback_entry.py drill   --db X [--keep]

- backup：SQLite 一致性备份 + sha256 sidecar（<backup>.sha256）。
- restore：先校验备份 sha（优先 --sha，否则读 sidecar），再恢复；
  目标非空必须 --force；恢复后再次校验目标 sha。
- drill：备份 -> 恢复到临时副本 -> 表/行/内容 sha 比对，输出 PASS/FAIL。
默认 dry-run，仅 --apply 才写 backup/target；drill 只写临时目录（--keep 保留）。
不依赖临场 SQL；不碰 kvmem/daily（无默认库）；不联网。
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time

SCHEMA = "rollback_entry_v1"


class RollbackError(Exception):
    pass


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def assert_local(paths):
    for p in paths:
        s = str(p or "")
        if not s or "://" in s or s.lower().startswith(("http", "ftp", "s3:")):
            raise RollbackError("local-only：拒绝非本地路径 %r" % (p,))


def _connect_ro(path):
    return sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)


def content_digest(path):
    """表集合 + 每表行数 + 全表行内容 sha（与文件字节 sha 独立）。"""
    assert_local([path])
    if not os.path.exists(path):
        raise RollbackError("db 不存在：%s" % path)
    con = _connect_ro(path)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        h = hashlib.sha256()
        schema = [(r[0], r[1]) for r in con.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name")]
        h.update(json.dumps(schema, ensure_ascii=False, sort_keys=True).encode())
        counts = {}
        for t in tables:
            rows = [list(r) for r in con.execute('SELECT * FROM "%s"' % t.replace('"', '""'))]
            rows.sort(key=lambda r: json.dumps(r, ensure_ascii=False, sort_keys=True))
            counts[t] = len(rows)
            h.update(t.encode())
            for r in rows:
                h.update(json.dumps(r, ensure_ascii=False, sort_keys=True).encode())
        return {"sha256": h.hexdigest(), "tables": counts,
                "rows": sum(counts.values()), "table_count": len(tables)}
    finally:
        con.close()


def sqlite_backup(src, dst):
    assert_local([src, dst])
    if not os.path.exists(src):
        raise RollbackError("源 db 不存在：%s" % src)
    os.makedirs(os.path.dirname(os.path.abspath(dst)) or ".", exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    s = _connect_ro(src)
    d = sqlite3.connect(dst)
    try:
        with d:
            s.backup(d)
    finally:
        s.close()
        d.close()


def write_sha(path, sha):
    with open(path + ".sha256", "w", encoding="utf-8") as f:
        f.write("%s  %s\n" % (sha, os.path.basename(path)))


def read_sha(path, explicit=None):
    if explicit:
        return explicit.strip().lower(), "--sha"
    side = path + ".sha256"
    if not os.path.exists(side):
        raise RollbackError("缺少 sha sidecar：%s（可用 --sha 显式给出）" % side)
    parts = open(side, encoding="utf-8").read().split()
    if not parts:
        raise RollbackError("sha sidecar 为空：%s" % side)
    return parts[0].strip().lower(), side


def default_backup_path(db):
    return "%s.bak-%s" % (db, time.strftime("%Y%m%d-%H%M%S"))


def cmd_backup(args):
    assert_local([args.db, args.out])
    bak = args.out or default_backup_path(args.db)
    plan = {"action": "backup", "db": args.db, "backup": bak,
            "db_sha256": sha_file(args.db), "apply": bool(args.apply)}
    if not args.apply:
        plan["dry_run"] = True
        return plan
    sqlite_backup(args.db, bak)
    sha = sha_file(bak)
    write_sha(bak, sha)
    plan.update({"dry_run": False, "backup_sha256": sha,
                 "backup_bytes": os.path.getsize(bak),
                 "sha_sidecar": bak + ".sha256"})
    return plan


def cmd_restore(args):
    assert_local([args.backup, args.target])
    if not os.path.exists(args.backup):
        raise RollbackError("备份不存在：%s" % args.backup)
    expected, src = read_sha(args.backup, args.sha)
    actual = sha_file(args.backup)
    if actual != expected:
        raise RollbackError("备份 sha 不匹配（拒绝恢复）：%s != %s" % (actual, expected))
    exists_nonempty = os.path.exists(args.target) and os.path.getsize(args.target) > 0
    if exists_nonempty and not args.force:
        raise RollbackError("目标已存在且非空：%s（需 --force）" % args.target)
    plan = {"action": "restore", "backup": args.backup, "target": args.target,
            "backup_sha256": actual, "sha_source": src,
            "overwrite": bool(exists_nonempty and args.force),
            "apply": bool(args.apply)}
    if not args.apply:
        plan["dry_run"] = True
        return plan
    os.makedirs(os.path.dirname(os.path.abspath(args.target)) or ".", exist_ok=True)
    if os.path.exists(args.target):
        os.remove(args.target)
    shutil.copy2(args.backup, args.target)
    out_sha = sha_file(args.target)
    if out_sha != actual:
        raise RollbackError("恢复后 sha 不一致：%s != %s" % (out_sha, actual))
    plan.update({"dry_run": False, "target_sha256": out_sha,
                 "target_bytes": os.path.getsize(args.target)})
    return plan


def cmd_drill(args):
    assert_local([args.db])
    tmp = tempfile.mkdtemp(prefix="rollback_drill_")
    bak = os.path.join(tmp, "drill.bak")
    restored = os.path.join(tmp, "drill.restored")
    try:
        src_dig = content_digest(args.db)
        sqlite_backup(args.db, bak)
        bak_sha = sha_file(bak)
        write_sha(bak, bak_sha)
        shutil.copy2(bak, restored)
        out_sha = sha_file(restored)
        out_dig = content_digest(restored)
        checks = {
            "backup_sha_matches_restore": bak_sha == out_sha,
            "content_sha_equal": src_dig["sha256"] == out_dig["sha256"],
            "rows_equal": src_dig["rows"] == out_dig["rows"],
            "tables_equal": src_dig["tables"] == out_dig["tables"],
        }
        ok = all(checks.values())
        return {"action": "drill", "db": args.db, "ok": ok, "checks": checks,
                "source": src_dig, "restored": out_dig,
                "backup_sha256": bak_sha, "restored_sha256": out_sha,
                "tmp": tmp if args.keep else None}
    finally:
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)


def build_parser():
    ap = argparse.ArgumentParser(description="固定回滚入口（默认 dry-run，local-only）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("backup")
    p.add_argument("--db", required=True)
    p.add_argument("--out", default=None)
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_backup)

    p = sub.add_parser("restore")
    p.add_argument("--backup", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--sha", default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser("drill")
    p.add_argument("--db", required=True)
    p.add_argument("--keep", action="store_true")
    p.set_defaults(func=cmd_drill)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        res = args.func(args)
    except Exception as exc:                     # noqa: BLE001
        print(json.dumps({"schema": SCHEMA, "ok": False,
                          "error": "%s: %s" % (type(exc).__name__, exc)},
                         ensure_ascii=False, indent=1))
        return 1
    res = dict(res)
    res["schema"] = SCHEMA
    res.setdefault("ok", True)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
