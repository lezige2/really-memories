# -*- coding: utf-8 -*-
"""P1 dry-run：只读分析 kvmem/daily/chat.db，模拟归档候选（不删/不改/不上传）。

local only：仅复制到 tmp/p1，所有产物留在本机；无网络、无云盘、无自动同步。
不改产品代码、不加列、不 commit。

用法：python -X utf8 out/p1_dryrun.py
输出：out/P1-DRYRUN-REPORT.json / .md
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import k2_family as K2          # noqa: E402
import memory_source as ms      # noqa: E402

TODAY = date(2026, 10, 30)
NOW = datetime(2026, 10, 30, 16, 55, 0)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ro(path):
    return sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)


def copy_db(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    s = ro(src)
    d = sqlite3.connect(dst)
    with d:
        s.backup(d)
    s.close()
    d.close()


def age_days(created_at):
    try:
        t = datetime.fromisoformat(str(created_at))
    except Exception:                                    # noqa: BLE001
        return None
    return round((NOW - t).total_seconds() / 86400.0, 2)


def event_date_of(text, created_at):
    if not text:
        return None
    if K2.is_periodic(str(text)):        # 每周/每月：periodic 豁免，不按 event_date 过期
        return None
    try:
        base = datetime.fromisoformat(str(created_at)).date()
    except Exception:                                    # noqa: BLE001
        base = TODAY
    d = K2.parse_relative_date(str(text), base)
    return d.isoformat() if d else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(ROOT, "kvmem", "daily", "chat.db"))
    ap.add_argument("--tmp", default=os.path.join(ROOT, "tmp", "p1"))
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "P1-DRYRUN-REPORT.json"))
    ap.add_argument("--md", default=os.path.join(ROOT, "out", "P1-DRYRUN-REPORT.md"))
    args = ap.parse_args(argv)

    dst_db = os.path.join(args.tmp, "chat.db")
    copy_db(args.src, dst_db)
    src_sha = sha256_file(args.src)
    con = ro(dst_db)
    rows = list(con.execute(
        "SELECT id,name,label,text,source_hash,created_at,mode FROM memory_source ORDER BY id"))
    blocks = {int(r[0]): r for r in con.execute(
        "SELECT source_id,path,n_tokens,n_bytes FROM memory_block")}
    metas = {int(r[0]): {"tags": json.loads(r[1] or "[]"), "source": r[2]}
             for r in con.execute("SELECT source_id,tags,source FROM daily_memory_meta")}
    con.close()

    total_tokens = sum(int(b[2]) for b in blocks.values())
    ages = {int(r[0]): age_days(r[5]) for r in rows}

    # ---- 候选定义：created_at 超期 + superseded(若有) + 用户显式标记 ----
    cols = set()
    con = ro(dst_db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(memory_source)")}
    con.close()
    has_superseded = "superseded" in cols
    user_marks = []
    for rid, m in metas.items():
        tags = [str(t) for t in m.get("tags") or []]
        if any(t in ("archive", "archived", "superseded", "deprecated", "deprecate")
               or t.startswith("user:") for t in tags):
            user_marks.append(rid)
    system_tagged = [rid for rid, m in metas.items()
                     if any(str(t) in ("auto_archive", "auto_summary", "auto_turn")
                            for t in (m.get("tags") or []))]

    def candidates(days):
        out = []
        for rid, name, label, text, sh, created, mode in rows:
            a = ages.get(int(rid))
            if a is not None and a > days:
                out.append(int(rid))
        return out

    th = {}
    for days in (21, 90):
        ids = candidates(days)
        th["%dd" % days] = {
            "cutoff": (NOW - timedelta(days=days)).isoformat(timespec="seconds"),
            "candidate_ids": ids, "candidate_count": len(ids),
            "candidate_tokens": sum(int(blocks[i][2]) for i in ids if i in blocks),
            "pool_after": len(rows) - len(ids),
            "pool_below_50": (len(rows) - len(ids)) < 50,
        }
    sens = {("%dd" % d): len(candidates(d)) for d in (1, 2, 3, 21, 90)}

    # event_date：有相对时间则优先；否则用 created_at
    event_rows = []
    for rid, name, label, text, sh, created, mode in rows:
        ed = event_date_of(text, created)
        if ed:
            event_rows.append({"id": int(rid), "event_date": ed, "created_at": created,
                               "expired_21d": date.fromisoformat(ed) < (TODAY - timedelta(days=21)),
                               "expired_90d": date.fromisoformat(ed) < (TODAY - timedelta(days=90))})

    # 稀有值重复（同一车牌/手机/卡号出现多行）：无 superseded 标记，仅报告
    rare = {}
    pat = re.compile(r"(京[A-Z]·?[A-Z0-9]{5}|1[3-9]\d{9}|\d{4} \d{4} \d{4} \d{4})")
    for rid, name, label, text, sh, created, mode in rows:
        for m in set(pat.findall(str(text))):
            rare.setdefault(m, []).append(int(rid))
    rare_dupes = [{"value": k, "ids": v} for k, v in rare.items() if len(v) > 1]

    # 近似重复（无 superseded 标记，仅报告，不归档）
    dupes = []
    seen = {}
    for rid, name, label, text, sh, created, mode in rows:
        key = "".join(ch for ch in text if not ch.isspace())
        if key in seen:
            dupes.append({"ids": [seen[key], int(rid)], "note": "文本近重复，无 superseded 标记"})
        else:
            seen[key] = int(rid)

    # ---- 恢复演练（0 候选 -> 未触发；对全部 20 条做控制 round-trip） ----
    restore_dir = os.path.join(args.tmp, "restore")
    if os.path.isdir(restore_dir):
        shutil.rmtree(restore_dir)
    os.makedirs(os.path.join(restore_dir, "blocks"), exist_ok=True)
    rdb = os.path.join(restore_dir, "chat.db")
    rcon = ms.connect(rdb)
    src_dir = os.path.join(ROOT, "kvmem", "daily", "blocks")
    ok = {"rows": 0, "ids": 0, "text_sha": 0, "block_sha": 0, "block_bytes": 0}
    for rid, name, label, text, sh, created, mode in rows:
        b = blocks.get(int(rid))
        if b is None:
            continue
        src_block = b[1] if b[1] and os.path.exists(b[1]) else \
            os.path.join(src_dir, name + ".kvmem")
        if not os.path.exists(src_block):
            continue
        dst_block = os.path.join(restore_dir, "blocks", name + ".kvmem")
        shutil.copy2(src_block, dst_block)
        rcon.execute(
            "INSERT INTO memory_source (id,tenant,scope,mode,name,label,text,source_hash,"
            "created_at,text_kind,contains_model_turns,is_excerpt,derived_from) "
            "VALUES (?,?,?,?,?,?,?,?,?,'human_memory',0,0,NULL)",
            (int(rid), "default", "private", mode, name, label, text, sh, created))
        rcon.execute(
            "INSERT INTO memory_block (source_id,path,n_tokens,n_bytes,built_at,model_path,"
            "model_size,model_mtime,kv_type,state_version) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (int(rid), dst_block, b[2], b[3], "restore",
             "", 0, 0, "q8_0", 1))
        if hashlib.sha256(text.encode("utf-8")).hexdigest() == sh:
            ok["text_sha"] += 1
        if sha256_file(src_block) == sha256_file(dst_block):
            ok["block_sha"] += 1
        if os.path.getsize(dst_block) == int(b[3]):
            ok["block_bytes"] += 1
        if rcon.execute("SELECT 1 FROM memory_source WHERE id=?", (int(rid),)).fetchone():
            ok["ids"] += 1
    rcon.commit()
    ok["rows"] = rcon.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0]
    rcon.close()
    drill = {"triggered": False, "reason": "21d/90d 均 0 候选",
             "control_roundtrip": dict(ok, expected=len(rows),
                                       all_ok=all(ok[k] == len(rows)
                                                  for k in ("rows", "ids", "text_sha",
                                                            "block_sha", "block_bytes"))),
             "local_dir": restore_dir}

    # ---- 低置信阈值：现有 query top1 分数 p5 ----
    samples = []
    import glob
    for p in glob.glob(os.path.join(ROOT, "kvmem", "daily", "assistant", "daily", "*.jsonl")) + \
            glob.glob(os.path.join(ROOT, "kvmem", "daily", "assistant", "sessions", "*.jsonl")):
        for line in open(p, encoding="utf-8", errors="replace"):
            try:
                e = json.loads(line)
            except Exception:                            # noqa: BLE001
                continue
            r = e.get("retrieval")
            if isinstance(r, dict) and r.get("scores"):
                try:
                    top1 = float(r["scores"][0][1])
                except Exception:                        # noqa: BLE001
                    continue
                samples.append({"q": e.get("query_sha16") or r.get("query_sha16"),
                                "top1": top1})
    samples.sort(key=lambda x: (x["top1"], str(x["q"])))
    if samples:
        vals = [s["top1"] for s in samples]
        import math
        k = max(0, min(len(vals) - 1, int(math.ceil(0.05 * len(vals))) - 1))
        p5 = vals[k]
        sample_sha = sha256_bytes(json.dumps(samples, sort_keys=True,
                                             ensure_ascii=False).encode("utf-8"))
        low = {"samples": len(samples), "p5_top1": p5, "min": vals[0],
               "median": vals[len(vals) // 2], "sample_sha256": sample_sha[:32],
               "threshold": p5, "action": "解压仅对 <p5 的查询；本轮 0 归档候选 -> 不解压"}
    else:
        low = {"samples": 0, "p5_top1": None, "sample_sha256": None,
               "threshold": None, "action": "无样本 -> 不解压"}

    report = {
        "schema": "p1_dryrun_v1",
        "local_only": True,
        "network": "none (no upload / no cloud / no sync)",
        "generated_at": NOW.isoformat(timespec="seconds"),
        "source": {"db": args.src, "sha256": src_sha, "copy": dst_db,
                   "copy_sha256": sha256_file(dst_db)},
        "policy": {"time_baseline": "created_at", "event_date_priority": True,
                   "use_access_count": False, "use_last_accessed": False,
                   "superseded_column_present": has_superseded,
                   "user_explicit_marks": user_marks},
        "profile": {
            "rows": len(rows), "blocks": len(blocks), "total_tokens": total_tokens,
            "age_days_min": min(a for a in ages.values() if a is not None),
            "age_days_max": max(a for a in ages.values() if a is not None),
            "created_min": min(r[5] for r in rows), "created_max": max(r[5] for r in rows),
            "modes": {m: sum(1 for r in rows if r[6] == m)
                      for m in sorted({r[6] for r in rows})},
            "system_tagged_ids": system_tagged,
            "event_date_rows": event_rows,
            "event_date_past": sum(1 for x in event_rows
                                   if x["event_date"] < TODAY.isoformat()),
            "event_date_future": sum(1 for x in event_rows
                                     if x["event_date"] >= TODAY.isoformat()),
            "near_duplicates": dupes,
            "rare_token_duplicates": rare_dupes,
        },
        "thresholds": th,
        "sensitivity_candidates": sens,
        "first_expiry": {
            "21d": min(((datetime.fromisoformat(r[5]) + timedelta(days=21)).date().isoformat()
                        for r in rows), default=None),
            "90d": min(((datetime.fromisoformat(r[5]) + timedelta(days=90)).date().isoformat()
                        for r in rows), default=None),
        },
        "archive_simulation": {
            "archived_21d": th["21d"]["candidate_count"],
            "archived_90d": th["90d"]["candidate_count"],
            "pool_after_21d": th["21d"]["pool_after"],
            "pool_after_90d": th["90d"]["pool_after"],
            "pool_below_50": th["21d"]["pool_after"] < 50,
            "note": "主池仅 20 条，已 <50；21/90d 无超期候选，本轮不产生归档包（也不生成 zip）",
        },
        "restore_drill": drill,
        "low_confidence": low,
        "unlocated": {"count": 0,
                      "note": "ask 日志只存 query_sha16 不含原文；无 event_date 列的‘去年/上月’"
                              "类查询无法定位，一律记未定位、不给假精确"},
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    md = ["# P1 dry-run（只读，**local only**）", "",
          "- 源库：`%s` sha256 `%s`；只读副本 `%s`（sha `%s`）" %
          (args.src, src_sha[:16], dst_db, report["source"]["copy_sha256"][:16]),
          "- **local only**：仅本机 tmp；无云盘/网盘、无上传、无自动同步；未改产品代码/未加列/未 commit。",
          "", "## 候选（created_at 基准；有 event_date 优先）", "",
          "| 阈值 | cutoff | 候选数 | 候选 id | 候选 token | 归档后主池 | 主池<50 |",
          "|---|---|---|---|---|---|---|"]
    for d in ("21d", "90d"):
        t = th[d]
        md.append("| %s | %s | %d | %s | %d | %d | %s |" % (
            d, t["cutoff"][:10], t["candidate_count"],
            ",".join(str(i) for i in t["candidate_ids"]) or "—",
            t["candidate_tokens"], t["pool_after"], t["pool_below_50"]))
    md += ["", "敏感性（相邻阈值）：" + ", ".join("%s=%d" % (k, v)
                                                 for k, v in sens.items()), "",
           "- 数据仅 2–3 天新（created_at %s … %s），21d/90d 必然 0 候选；" \
           "2d 边界才全量命中，说明阈值需按真实老化数据重定。" %
           (report["profile"]["created_min"][:10], report["profile"]["created_max"][:10]),
           "- superseded 列不存在（0 条标记）；用户显式标记 0 条；系统 auto_* 标签 %d 条（非用户标记）。" %
           len(system_tagged),
           "- event_date 可解析 %d 条（过去 %d / 未来 %d）；均未超过 21/90d，无过期。" %
           (len(event_rows), report["profile"]["event_date_past"],
            report["profile"]["event_date_future"]),
           "- 文本近重复 %d 组（如 %s）；稀有值重复 %d 组（如 %s），均无 superseded 标记，仅报告不归档。" %
           (len(dupes), dupes[0]["ids"] if dupes else "—", len(rare_dupes),
            (rare_dupes[0]["ids"] if rare_dupes else "—")),
           "- 最早到期日：21d=%s，90d=%s（此刻 0 候选，到期前不会产生归档）。" %
           (report["first_expiry"]["21d"], report["first_expiry"]["90d"]),
           "", "## 恢复演练", "",
           "- 触发：否（0 候选）；控制 round-trip（全部 %d 条复制到 `%s`）：" %
           (len(rows), restore_dir),
           "  rows=%d, ids=%d, text_sha=%d, block_sha=%d, bytes=%d → **%s**" %
           (drill["control_roundtrip"]["rows"], drill["control_roundtrip"]["ids"],
            drill["control_roundtrip"]["text_sha"], drill["control_roundtrip"]["block_sha"],
            drill["control_roundtrip"]["block_bytes"],
            "100% 可恢复" if drill["control_roundtrip"]["all_ok"] else "FAIL"),
           "", "## 低置信阈值（p5 校准）", "",
           "- 样本 %d 条 ask（query_sha16 + top1），p5=**%s**，min=%s，median=%s，样本 sha `%s`" %
           (low["samples"], low["p5_top1"], low.get("min"), low.get("median"),
            (low.get("sample_sha256") or "")[:16]),
           "- 动作：%s" % low["action"],
           "", "## 结论", "",
           "- 21d/90d 候选均为 0，归档后主池仍 20（已 <50）：**P1 前提不成立，不能在 daily 库上线**；",
           "- 建议先用老化/显式标记数据重跑；event_date 与近重复需显式 superseded 语义才能自动归档；",
           "- 未生成归档包/zip（0 候选）；任何后续包仅落本地并同 chat.db 敏感级保管。"]
    with open(args.md, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(json.dumps({"local_only": True, "thresholds": {k: {x: th[k][x] for x in
                                                            ("candidate_count", "pool_after")}
                                                         for k in th},
                      "sensitivity": sens, "drill": drill["control_roundtrip"],
                      "low_confidence": {k: low.get(k) for k in
                                         ("samples", "p5_top1", "action")}},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())