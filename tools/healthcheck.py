# -*- coding: utf-8 -*-
"""healthcheck.py — 一键健康检查（只读，不启服务/不写库）。

用法:
  python -X utf8 tools/healthcheck.py --db kvmem/daily/chat.db --blocks kvmem/daily/blocks
输出 JSON: ok / checks / version。
"""
import argparse, json, os, sqlite3, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def git(*args):
    try:
        return subprocess.check_output(["git"] + list(args), cwd=ROOT,
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(ROOT, "kvmem", "daily", "chat.db"))
    ap.add_argument("--blocks", default=os.path.join(ROOT, "kvmem", "daily", "blocks"))
    ap.add_argument("--model", default=r"D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf")
    a = ap.parse_args()
    checks, errors = [], []
    def chk(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok: errors.append("%s: %s" % (name, detail))

    chk("db_exists", os.path.exists(a.db), a.db)
    chk("blocks_dir", os.path.isdir(a.blocks), a.blocks)
    chk("model_exists", os.path.exists(a.model), a.model)
    con = sqlite3.connect(a.db) if os.path.exists(a.db) else None
    if con:
        tabs = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
        for t in ("memory_source", "memory_block", "memory_access", "memory_archive"):
            chk("table:" + t, t in tabs)
        src = con.execute("select count(*) from memory_source").fetchone()[0]
        blk = con.execute("select count(*) from memory_block").fetchone()[0]
        chk("source_rows", src > 0, str(src))
        chk("block_rows", blk == src, "%s blocks / %s sources" % (blk, src))
        miss = []
        for sid, p in con.execute("select source_id,path from memory_block"):
            if not p or not os.path.exists(p):
                miss.append((sid, p))
        chk("block_files", not miss, "%d missing" % len(miss))
        con.close()
    try:
        import chat_daily as D
        args = D.build_arg_parser().parse_args([])
        chk("default:lifecycle_cap", bool(getattr(args, "lifecycle_cap", False)), str(getattr(args, "lifecycle_cap", None)))
        chk("default:memory_access", bool(getattr(args, "memory_access", False)), str(getattr(args, "memory_access", None)))
        chk("default:lifecycle_archive", bool(getattr(args, "lifecycle_archive", False)), str(getattr(args, "lifecycle_archive", None)))
        chk("default:lifecycle_fallback", bool(getattr(args, "lifecycle_fallback", False)), str(getattr(args, "lifecycle_fallback", None)))
        chk("default:audit", bool(getattr(args, "audit_enabled", False)), str(getattr(args, "audit_enabled", None)))
    except Exception as e:
        chk("import_chat_daily", False, str(e))
    out = {"ok": not errors, "checks": checks, "errors": errors,
           "version": {"head": git("rev-parse", "--short", "HEAD"),
                       "ahead": git("rev-list", "--count", "@{u}..HEAD"),
                       "dirty": git("status", "--porcelain") is not None}}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())