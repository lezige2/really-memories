# -*- coding: utf-8 -*-
"""n200 数据体检：行/块/孤儿/字节、token 分布、脏数据对、查询目标与值泄漏、建库日志。

只读 DB + blocks + jsonl；输出 dst/DATA-AUDIT-n200.json。
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STRIP = "\u00b7-\u2014\u2013_.\u3002\uff0c\u3001"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def norm_text(s):
    s = unicodedata.normalize("NFKC", str(s or ""))
    return "".join(ch for ch in s if not ch.isspace() and ch not in STRIP)


def compact(s):
    return "".join(ch for ch in str(s or "") if not ch.isspace() and ch not in STRIP)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dst", default=os.path.join(ROOT, "kvmem", "scale40k", "n200"))
    ap.add_argument("--blocks-src", default=os.path.join(ROOT, "out", "scale40k", "blocks_200.jsonl"))
    ap.add_argument("--log", default=os.path.join(ROOT, "out", "scale40k", "BUILD-n200.log"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    dst = os.path.abspath(args.dst)
    outpath = args.out or os.path.join(dst, "DATA-AUDIT-n200.json")

    con = sqlite3.connect(os.path.join(dst, "chat.db"))
    rows = list(con.execute("SELECT id,name,text,source_hash,created_at FROM memory_source ORDER BY id"))
    blocks = list(con.execute("SELECT source_id,path,n_tokens,n_bytes FROM memory_block ORDER BY source_id"))
    con.close()

    problems = []
    # 1) 行/块/孤儿/字节
    n_rows, n_blocks = len(rows), len(blocks)
    src_ids = {int(r[0]) for r in rows}
    blk_ids = {int(b[0]) for b in blocks}
    missing_block = sorted(src_ids - blk_ids)
    orphan_block = sorted(blk_ids - src_ids)
    zero_files = []
    missing_files = []
    for sid, path, ntok, nbytes in blocks:
        if not path or not os.path.exists(path):
            missing_files.append(path)
        elif os.path.getsize(path) <= 0:
            zero_files.append(path)
    expected_blocks = len([f for f in os.listdir(os.path.join(dst, "blocks"))
                           if f.endswith(".kvmem")]) if os.path.isdir(os.path.join(dst, "blocks")) else 0
    if n_rows != 200:
        problems.append("rows=%d != 200" % n_rows)
    if n_blocks != 200:
        problems.append("blocks=%d != 200" % n_blocks)
    if missing_block:
        problems.append("sources without block: %r" % missing_block[:5])
    if orphan_block:
        problems.append("orphan blocks: %r" % orphan_block[:5])
    if zero_files:
        problems.append("zero-byte blocks: %r" % zero_files[:5])
    if missing_files:
        problems.append("missing block files: %r" % missing_files[:5])
    if expected_blocks != n_blocks:
        problems.append("block files on disk=%d != memory_block=%d" % (expected_blocks, n_blocks))

    # 2) token 分布
    toks = [int(b[2]) for b in blocks]
    long_blocks = [t for t in toks if t >= 600]
    total_tokens = sum(toks)
    if not (10 <= len(long_blocks) <= 30):
        problems.append("long(>=600t)=%d not in 20±10" % len(long_blocks))

    # 3) 脏数据 5 对
    text_by_id = {int(r[0]): r[2] for r in rows}
    hash_by_id = {int(r[0]): r[3] for r in rows}
    name_by_id = {int(r[0]): r[1] for r in rows}
    pairs = {}
    for r in rows:
        m = re.match(r"s40_dirty_(\d+)([ab])$", r[1])
        if m:
            pairs.setdefault(int(m.group(1)), {})[m.group(2)] = int(r[0])
    pair_report = []
    bad_pairs = []
    for i in sorted(pairs):
        p = pairs[i]
        if set(p) != {"a", "b"}:
            bad_pairs.append("pair %d incomplete" % i)
            continue
        a, b = p["a"], p["b"]
        ta, tb = text_by_id[a], text_by_id[b]
        ha, hb = hash_by_id[a], hash_by_id[b]
        # 全角/空格差异的判定：NFKC 后仅剩空白不同（NFKC 会把全角映射成 ASCII）
        fw_a = re.sub(r"\s+", "", unicodedata.normalize("NFKC", ta))
        fw_b = re.sub(r"\s+", "", unicodedata.normalize("NFKC", tb))
        fullwidth_or_space = (fw_a == fw_b) and (ta != tb)
        ok = (norm_text(ta) == norm_text(tb) and ha != hb and fullwidth_or_space)
        if not ok:
            bad_pairs.append("pair %d norm_same=%s hash_diff=%s fw_only=%s"
                             % (i, norm_text(ta) == norm_text(tb), ha != hb, fullwidth_or_space))
        pair_report.append({"pair": i, "ids": [a, b], "norm_same": norm_text(ta) == norm_text(tb),
                            "hash_diff": ha != hb, "diff_only_fullwidth_or_space": fullwidth_or_space,
                            "ok": ok})
    exact = {}
    for r in rows:
        exact.setdefault(r[3], []).append(int(r[0]))
    exact_dup_groups = [v for v in exact.values() if len(v) > 1]
    if len(pairs) != 5:
        problems.append("dirty pairs=%d != 5" % len(pairs))
    if bad_pairs:
        problems.append("dirty pair issues: %r" % bad_pairs)
    if exact_dup_groups:
        problems.append("exact dup groups=%d" % len(exact_dup_groups))

    # 4) 查询
    qpath = os.path.join(dst, "queries.jsonl")
    qs = [json.loads(l) for l in open(qpath, encoding="utf-8") if l.strip()]
    by_src = {}
    if os.path.exists(args.blocks_src):
        for line in open(args.blocks_src, encoding="utf-8"):
            if line.strip():
                b = json.loads(line)
                by_src[b["id"]] = b
    qids = [q.get("id") for q in qs]
    qprobs = []
    if len(qs) != 40:
        qprobs.append("queries=%d != 40" % len(qs))
    if len(set(qids)) != len(qids):
        qprobs.append("duplicate query ids")
    for q in qs:
        tgt = q.get("target_block_id")
        src = q.get("src_target_block_id")
        if tgt is not None and int(tgt) not in src_ids:
            qprobs.append("%s target %s not in DB" % (q.get("id"), tgt))
        if src is None:
            continue
        b = by_src.get(src) or {}
        val = str(b.get("value") or "")
        text = str(q.get("text") or "")
        if val and (val in text or compact(val) in compact(text)):
            qprobs.append("%s text contains target value %r" % (q.get("id"), val))
    if qprobs:
        problems.append("query issues: %r" % qprobs[:5])

    # 5) 建库日志
    log_txt = ""
    if os.path.exists(args.log):
        log_txt = open(args.log, encoding="utf-8", errors="replace").read()
    log_bad = [ln for ln in log_txt.splitlines()
               if ("Traceback" in ln or "ERROR" in ln or "失败" in ln or "rollback" in ln.lower())]
    built_lines = len([ln for ln in log_txt.splitlines() if ln.startswith("built")])
    if log_bad:
        problems.append("build log issues: %r" % log_bad[:3])
    if built_lines < n_blocks:
        problems.append("built lines=%d < blocks=%d" % (built_lines, n_blocks))

    audit = {
        "schema": "scale40k_data_audit_v1",
        "dst": dst,
        "ok": not problems,
        "problems": problems,
        "db": {"rows": n_rows, "blocks": n_blocks, "block_files": expected_blocks,
               "sources_without_block": missing_block, "orphan_blocks": orphan_block,
               "zero_byte": len(zero_files), "missing_files": len(missing_files)},
        "tokens": {"min": min(toks), "mean": round(total_tokens / float(len(toks)), 1),
                   "max": max(toks), "total": total_tokens,
                   "long_ge_600": len(long_blocks),
                   "hist": {"<100": sum(1 for t in toks if t < 100),
                            "100-599": sum(1 for t in toks if 100 <= t < 600),
                            "600+": len(long_blocks)}},
        "dirty": {"pairs": pair_report, "exact_dup_groups": len(exact_dup_groups)},
        "queries": {"n": len(qs),
                    "targets_in_db": sum(1 for q in qs if q.get("target_block_id") is not None),
                    "null_target": sum(1 for q in qs if q.get("target_block_id") is None),
                    "problems": qprobs},
        "build_log": {"path": args.log, "built_lines": built_lines, "bad_lines": log_bad[:5]},
        "seed": 40000,
        "sha256": {"blocks_200.jsonl": sha256_file(args.blocks_src),
                   "queries_100.jsonl": sha256_file(os.path.join(ROOT, "out", "scale40k",
                                                                 "queries_100.jsonl")),
                   "SCALE-40K-GEN.py": sha256_file(os.path.join(ROOT, "out", "SCALE-40K-GEN.py"))},
    }
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    print(json.dumps({"ok": audit["ok"], "problems": problems,
                      "db": audit["db"], "tokens": audit["tokens"],
                      "dirty_exact_dup": audit["dirty"]["exact_dup_groups"],
                      "queries": audit["queries"], "log_bad": log_bad[:3]},
                     ensure_ascii=False, indent=1))
    return 0 if audit["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())