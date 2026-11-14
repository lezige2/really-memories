# -*- coding: utf-8 -*-
"""P2 离线预实验：检索池 → 时间过滤 → 池内 K2 → top4（不调模型、不起服务、不写产品库）。

用法：python -X utf8 out/p2_pool_probe.py
输出：out/P2-POOL-REPORT.json / .md
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import k2_family as K2          # noqa: E402
import memory_source as ms      # noqa: E402
import retrieval as R           # noqa: E402
import memory_service as memo    # noqa: E402

BANDS = (20, 50, 200)
TOP_POOL = 20
TOPK = 4
TODAY = date(2026, 10, 30)
STRIP = "\u00b7-\u2014\u2013_.\u3002\uff0c\u3001"


def compact(s):
    return "".join(ch for ch in str(s or "") if not ch.isspace() and ch not in STRIP)


def db_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    s = sqlite3.connect("file:%s?mode=ro" % src.replace("\\", "/"), uri=True)
    d = sqlite3.connect(dst)
    with d:
        s.backup(d)
    s.close()
    d.close()


def pool_for(con, q, rows, k=TOP_POOL):
    """K2 off / time off：产品同款本地检索（memory_service.retrieve）取前 k；
    空结果回退 retrieval.search（与产品 keyword fallback 同层，二者都不调模型）。"""
    hits = []
    try:
        hits = memo.retrieve(q, rows, topk=k, meta_fn=None, return_stats=False) or []
        hits = [{"source_id": int(h["id"]), "score": h.get("score")} for h in hits]
    except Exception:                                    # noqa: BLE001
        hits = []
    if not hits:
        try:
            hits = [{"source_id": int(h["source_id"]), "score": h.get("score")}
                    for h in (R.search(con, q, k=k) or []) if h.get("source_id") is not None]
        except Exception:                                # noqa: BLE001
            hits = []
    out, seen = [], set()
    for h in hits:
        sid = int(h["source_id"])
        if sid in seen:
            continue
        seen.add(sid)
        out.append(h)
    return out


def time_filter(pool, rows_by_id, times, modes):
    kept, dropped = [], []
    for c in pool:
        r = rows_by_id.get(c["source_id"])
        if r is None:
            continue
        text = str(r[3] or "")
        fam = K2.classify_row(text)["family"]
        if K2._is_expired(fam, text, times.get(c["source_id"]),
                          modes.get(c["source_id"]), TODAY):
            dropped.append(c["source_id"])
        else:
            kept.append(c)
    return kept, dropped


def k2_in_pool(pool, rows_by_id, q, times, modes):
    """池内 K2（subject 键）：hit -> keep_ids；无 hit -> 池序前 4。"""
    pool_rows = [rows_by_id[c["source_id"]] for c in pool if c["source_id"] in rows_by_id]
    ex = K2.select_k2_ex(pool_rows, q, topk=TOPK, times=times, modes=modes, today=TODAY)
    if ex.get("hit"):
        hit = ex["hit"][0]
        keep = [int(x) for x in (hit["signals"].get("keep_ids")
                                 or [hit["source_id"]])][:TOPK]
        return keep, ex.get("reason"), set(int(x) for x in hit["signals"].get("hidden_ids") or [])
    return [c["source_id"] for c in pool][:TOPK], ex.get("reason"), set()


def eval_arm(pool, final_ids, rows_by_id, q, target, not_contains):
    tgt = int(target) if target is not None else None
    hit = tgt is not None and tgt in final_ids
    leak = False
    for sid in final_ids:
        r = rows_by_id.get(sid)
        if not r:
            continue
        txt = str(r[3] or "")
        ct = compact(txt)
        for v in not_contains or []:
            if v and (str(v) in txt or compact(v) in ct):
                leak = True
                break
    mis = False
    if tgt is not None and tgt not in final_ids and tgt in [c["source_id"] for c in pool]:
        tr = rows_by_id.get(tgt)
        if tr:
            subj = K2.subject_of(tr[3])
            fam = K2.classify_row(tr[3])
            for sid in final_ids:
                r = rows_by_id.get(sid)
                if not r:
                    continue
                c = K2.classify_row(r[3])
                if K2.subject_of(r[3]) == subj and c["family"] == fam["family"] \
                        and c["predicate"] == fam["predicate"]:
                    mis = True
                    break
    return {"hit": hit, "leak": leak, "mis_hide": mis,
            "in_pool": tgt is not None and tgt in [c["source_id"] for c in pool]}


def summarize(items):
    n = len(items)
    with_target = [x for x in items if x["target"] is not None]
    return {
        "n": n,
        "targets_in_library": len(with_target),
        "recall_at_4": round(sum(1 for x in with_target if x["hit"]) / float(len(with_target)), 4)
                       if with_target else None,
        "hits": sum(1 for x in with_target if x["hit"]),
        "leak_proxy": round(sum(1 for x in items if x["leak"]) / float(n), 4) if n else None,
        "mis_hide": sum(1 for x in items if x["mis_hide"]),
        "target_in_pool": sum(1 for x in with_target if x["in_pool"]),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "P2-POOL-REPORT.json"))
    ap.add_argument("--md", default=os.path.join(ROOT, "out", "P2-POOL-REPORT.md"))
    ap.add_argument("--tmp", default=os.path.join(ROOT, "tmp", "p2"))
    args = ap.parse_args(argv)

    report = {"schema": "p2_pool_v1", "generated_for": "P2 offline pre-experiment",
              "top_pool": TOP_POOL, "topk": TOPK, "today": str(TODAY),
              "queries": None, "bands": {}}

    for n in BANDS:
        src = os.path.join(ROOT, "kvmem", "scale40k", "n%d" % n, "chat.db")
        dst = os.path.join(args.tmp, "n%d" % n, "chat.db")
        db_copy(src, dst)
        con = sqlite3.connect(dst)
        con.row_factory = sqlite3.Row
        R.build_index(con, verbose=False)
        qpath = os.path.join(ROOT, "kvmem", "scale40k", "n%d" % n, "queries.jsonl")
        queries = [json.loads(l) for l in open(qpath, encoding="utf-8") if l.strip()]
        report["queries"] = len(queries)
        rows = ms.block_rows(con)
        rows_by_id = {int(r[0]): r for r in rows}
        times = {int(r[0]): r[1] for r in con.execute(
            "SELECT id,created_at FROM memory_source")}
        modes = {int(r[0]): r[1] for r in con.execute(
            "SELECT id,mode FROM memory_source")}

        pools, arms = {}, {"k2off_top4": [], "p2_top10": [], "p2_top20": []}
        time_dropped = 0
        for q in queries:
            qid = q["id"]
            query = q["text"]
            tgt = q.get("target_block_id")
            pool20 = pool_for(con, query, rows, TOP_POOL)
            pools[qid] = pool20
            rows_by_id_local = rows_by_id

            # 对照 1：K2-off，直接检索前 4
            final = [c["source_id"] for c in pool20][:TOPK]
            arms["k2off_top4"].append(dict(eval_arm(pool20, final, rows_by_id_local, query,
                                                    tgt, q.get("not_contains") or []),
                                           id=qid, kind=q.get("kind"),
                                           target=tgt, k2_reason="off"))

            # P2 top10 / top20：时间过滤 -> 池内 K2 -> 取 4
            for arm, k in (("p2_top10", 10), ("p2_top20", 20)):
                pool = pool20[:k]
                tpool, dropped = time_filter(pool, rows_by_id_local, times, modes)
                time_dropped += len(dropped)
                final, reason, _hidden = k2_in_pool(tpool, rows_by_id_local, query, times, modes)
                arms[arm].append(dict(eval_arm(tpool, final, rows_by_id_local, query,
                                               tgt, q.get("not_contains") or []),
                                      id=qid, kind=q.get("kind"), target=tgt,
                                      k2_reason=reason,
                                      final=final, dropped=dropped))

        pool_stats = {"pool_recall_at_20": None, "pool_hits": 0,
                      "targets_in_library": 0, "pool_recall_at_10": None,
                      "targets_in_library_all38": 0, "pool_hits_all38": 0}
        tgt_items = [q for q in queries if q.get("target_block_id") is not None]
        pool_stats["targets_in_library"] = len(tgt_items)
        pool_stats["pool_hits"] = sum(
            1 for q in tgt_items
            if int(q["target_block_id"]) in [c["source_id"] for c in pools[q["id"]]])
        pool_stats["pool_recall_at_20"] = round(
            pool_stats["pool_hits"] / float(len(tgt_items)), 4) if tgt_items else None
        pool_stats["pool_hits_at_10"] = sum(
            1 for q in tgt_items
            if int(q["target_block_id"]) in [c["source_id"] for c in pools[q["id"]][:10]])
        pool_stats["pool_recall_at_10"] = round(
            pool_stats["pool_hits_at_10"] / float(len(tgt_items)), 4) if tgt_items else None
        pool_stats["pool_hits_all38"] = sum(
            1 for q in tgt_items
            if int(q["target_block_id"]) in [c["source_id"] for c in pools[q["id"]]])
        # 同 40 题里目标在 DB 的条数（n20=13 / n50=17 / n200=38）
        pool_stats["targets_in_library_all38"] = len(tgt_items)

        band = {"pool": pool_stats, "arms": {}}
        for arm, items in arms.items():
            band["arms"][arm] = summarize(items)
            band["arms"][arm]["by_kind"] = {
                k: summarize([x for x in items if x["kind"] == k])
                for k in ("direct", "paraphrase", "chain_last", "negative")
                if any(x["kind"] == k for x in items)}
            band["arms"][arm]["k2_reason"] = {}
            for x in items:
                rs = x.get("k2_reason") or "off"
                band["arms"][arm]["k2_reason"][rs] = \
                    band["arms"][arm]["k2_reason"].get(rs, 0) + 1
        misses = []
        for q in tgt_items:
            tgt = int(q["target_block_id"])
            if tgt in [c["source_id"] for c in pools[q["id"]]]:
                continue
            try:
                deep = memo.retrieve(q["text"], rows, topk=50, meta_fn=None) or []
                ids = [int(h["id"]) for h in deep]
                rank = ids.index(tgt) + 1 if tgt in ids else None
                nhit = len(ids)
            except Exception:                            # noqa: BLE001
                rank, nhit = None, None
            misses.append({"id": q["id"], "kind": q.get("kind"), "target": tgt,
                           "rank_full": rank, "n_hits_full": nhit,
                           "reason": "rank>20" if rank else "retrieval_empty_or_gated"})
        band["pool_misses"] = misses
        band["time_dropped_total"] = time_dropped
        band["pool_samples"] = {qid: pools[qid][:3] for qid in list(pools)[:3]}
        report["bands"]["n%d" % n] = band
        con.close()

    gate_band = report["bands"]["n200"]["pool"]
    gate_ok = (gate_band["pool_recall_at_20"] is not None
               and gate_band["pool_recall_at_20"] >= 0.95
               and gate_band["pool_hits"] >= 38)
    report["gate"] = {"band": "n200", "require_recall_at_20": 0.95,
                      "require_hits": 38, "actual": gate_band, "ok": bool(gate_ok)}

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    lines = ["# P2 离线预实验（检索池 → 时间过滤 → 池内 K2）", "",
             "不调模型、不起服务；DB 只读复制到 tmp/p2，检索索引建在副本上。", "",
             "## 池召回", "",
             "| 档 | 在库目标 | pool@20 命中 | pool@20 | pool@10 |",
             "|---|---|---|---|---|"]
    for n in BANDS:
        p = report["bands"]["n%d" % n]["pool"]
        lines.append("| n%d | %d | %d | %s | %s |" % (
            n, p["targets_in_library"], p["pool_hits"],
            p["pool_recall_at_20"], p["pool_recall_at_10"]))
    lines += ["", "门槛（n200）：@20≥0.95 且 ≥38/40 → **%s**" %
              ("PASS" if gate_ok else "FAIL，按预注册停止（不进入 P2 决策）"), ""]
    if not gate_ok:
        lines += ["未进池的 n200 目标："]
        for m in report["bands"]["n200"].get("pool_misses") or []:
            lines.append("- %s (%s) target=%s rank=%s/%s 原因=%s" % (
                m["id"], m["kind"], m["target"], m["rank_full"], m["n_hits_full"], m["reason"]))
        lines += [""]
    lines += [
              "## 各臂 recall@4 / 泄漏代理 / 误隐", "",
              "| 档 | 臂 | recall@4 | direct | chain_last | 泄漏代理 | 误隐 |",
              "|---|---|---|---|---|---|---|"]
    for n in BANDS:
        for arm in ("k2off_top4", "p2_top10", "p2_top20"):
            a = report["bands"]["n%d" % n]["arms"][arm]
            bk = a["by_kind"]
            lines.append("| n%d | %s | %s | %s | %s | %s | %d |" % (
                n, arm, a["recall_at_4"],
                (bk.get("direct") or {}).get("recall_at_4"),
                (bk.get("chain_last") or {}).get("recall_at_4"),
                a["leak_proxy"], a["mis_hide"]))
    with open(args.md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps({"gate": report["gate"], "bands": {
        k: {"pool": v["pool"], "arms": {a: {x: v["arms"][a][x] for x in
                                            ("recall_at_4", "leak_proxy", "mis_hide")}
                                        for a in v["arms"]}}
        for k, v in report["bands"].items()}}, ensure_ascii=False, indent=1))
    return 0 if gate_ok else 3


if __name__ == "__main__":
    raise SystemExit(main())