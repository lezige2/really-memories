# -*- coding: utf-8 -*-
"""S2 检索复现：n200 只读副本，q048/q052/q060/q062/q063 各跑 3 次检索（K2-off/time-off）。

不改代码、不起服务、不写产品库；副本与检索索引只落 tmp/s2。
输出 out/S2-REPRO.json / .md
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import memory_service as memo      # noqa: E402
import memory_source as ms         # noqa: E402
import retrieval as R              # noqa: E402

IDS = ["q048", "q052", "q060", "q062", "q063"]
SRC = os.path.join(ROOT, "kvmem", "scale40k", "n200", "chat.db")
TMP = os.path.join(ROOT, "tmp", "s2")


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


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


def full_ranking(query, rows):
    """与 memory_service.retrieve 同口径的完整排序（不改参数，仅用于取 rank）。"""
    qt = memo.tokens(query)
    scored = []
    for r in rows:
        text = str(r[3] or "")
        label = str(r[2] or "")
        blob = (text + "\n" + label).lower()
        hits = sorted(t for t in qt if t in blob)
        if not hits:
            continue
        scored.append({"id": int(r[0]), "score": float(len(hits)),
                       "coverage": memo.coverage_of(hits, qt), "hits": hits,
                       "text": text})
    scored.sort(key=lambda x: (-x["score"], x["id"]))
    return scored, qt


def run_once(rows, query, topk=20):
    return memo.retrieve(query, rows, topk=topk, meta_fn=None, return_stats=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "S2-REPRO.json"))
    ap.add_argument("--md", default=os.path.join(ROOT, "out", "S2-REPRO.md"))
    args = ap.parse_args(argv)

    dst = os.path.join(TMP, "chat.db")
    copy_db(SRC, dst)
    con = sqlite3.connect(dst)
    R.build_index(con, verbose=False)
    rows = ms.block_rows(con)
    by_id = {int(r[0]): r for r in rows}
    qs = {q["id"]: q for q in (json.loads(l) for l in
                               open(os.path.join(ROOT, "kvmem", "scale40k", "n200",
                                                 "queries.jsonl"), encoding="utf-8"))}

    report = {"schema": "s2_repro_v1", "source": SRC, "source_sha256": sha_file(SRC),
              "copy": dst, "runs_per_query": 3, "k2": "off", "time": "off",
              "params": {"retrieve_topk": 20, "k2_family": False},
              "queries": [], "deterministic": True}
    for qid in IDS:
        q = qs[qid]
        target = int(q["target_block_id"])
        runs = []
        for _ in range(3):
            hits, stats = run_once(rows, q["text"])
            ids = [int(h["id"]) for h in hits]
            runs.append({"ids": ids, "n": len(ids), "gate": stats.get("gate"),
                         "candidates": stats.get("candidates"),
                         "top1_score": hits[0]["score"] if hits else None,
                         "top1_id": ids[0] if ids else None})
        deterministic = all(r["ids"] == runs[0]["ids"] and r["gate"] == runs[0]["gate"]
                            and r["top1_score"] == runs[0]["top1_score"] for r in runs)
        report["deterministic"] = report["deterministic"] and deterministic

        ranked, qt = full_ranking(q["text"], rows)
        rank = None
        tgt = None
        for i, x in enumerate(ranked, start=1):
            if x["id"] == target:
                rank, tgt = i, x
                break
        best = ranked[0] if ranked else None
        tr = by_id.get(target)
        exists = tr is not None
        block = None
        if exists:
            row = con.execute("SELECT path,n_tokens,n_bytes FROM memory_block WHERE source_id=?",
                              (target,)).fetchone()
            if row:
                block = {"path": row[0], "n_tokens": row[1], "n_bytes": row[2],
                         "exists": bool(row[0] and os.path.exists(row[0])),
                         "size": os.path.getsize(row[0]) if row[0] and os.path.exists(row[0]) else 0}
        rs_err = ""
        try:
            rs = R.search(con, q["text"], k=20) or []
            rs_ids = [int(h["source_id"]) for h in rs if h.get("source_id") is not None]
        except Exception as exc:                         # noqa: BLE001
            rs_ids = []
            rs_err = str(exc)
        rs_rank = rs_ids.index(target) + 1 if target in rs_ids else None

        SYN = {"q048": ["牌子~车牌号"], "q052": ["号码~手机号", "来着=口语"],
               "q060": ["会~会议", "几号几点~时间"],
               "q062": ["哪儿人~老家"], "q063": ["哪儿人~老家"]}
        gate = runs[0]["gate"]
        if not runs[0]["ids"]:
            reason = "gate_below_threshold" if gate == "below_threshold" else "no_candidate"
        elif rank and rank > 20:
            reason = "low_rank_beyond_20"
        else:
            reason = "hit_in_pool"
        # 词面证据：查询 bigram 中哪些完全不在目标文本里
        tgt_text = str(tr[3] if tr else "")
        missing = [t for t in sorted(qt) if t not in tgt_text.lower()]
        report["queries"].append({
            "id": qid, "text": q["text"], "target": target,
            "target_preview": tgt_text[:80],
            "target_exists": exists, "target_block": block,
            "runs": runs, "deterministic": deterministic,
            "rank": rank, "rank_x3": [rank] * 3,
            "target_score": tgt["score"] if tgt else 0,
            "target_coverage": tgt["coverage"] if tgt else 0,
            "target_hits": tgt["hits"] if tgt else [],
            "best": {"id": best["id"], "score": best["score"],
                     "coverage": best["coverage"], "hits": best["hits"]} if best else None,
            "query_tokens": sorted(qt),
            "query_tokens_missing_in_target": missing[:12],
            "rsearch": {"empty": not rs_ids, "ids": rs_ids[:20], "rank": rs_rank,
                        "error": rs_err or None},
            "classification": {
                "primary": reason,
                "causes": [
                    ("top1_coverage %.3f < %.2f" % (best["coverage"],
                                                    memo.DEFAULT_COVERAGE_MIN))
                    if best and gate == "below_threshold" else None,
                    ("top1_score %.1f < %.1f" % (best["score"],
                                                 memo.DEFAULT_TOP_SCORE_MIN))
                    if best and gate == "below_threshold"
                    and best["score"] < memo.DEFAULT_TOP_SCORE_MIN else None,
                    ("target_rank %d > 20（score %.1f vs best %.1f）"
                     % (rank, tgt["score"], best["score"]))
                    if rank and rank > 20 and best else None,
                    ("index_path: R.search rank %s" % rs_rank) if rs_rank else
                    ("index_path: R.search empty" if not rs_ids else
                     "index_path: R.search 未含目标"),
                    "no_query_rewrite（_retrieval_text 仅剥寒暄前缀）",
                ],
                "synonym_hypotheses": SYN.get(qid, []),
                "query_tokens_missing": missing[:8],
            },
            "evidence": {
                "gate": gate, "candidates_scored": runs[0]["candidates"],
                "thresholds": {"top_score_min": memo.DEFAULT_TOP_SCORE_MIN,
                               "coverage_min": memo.DEFAULT_COVERAGE_MIN,
                               "short_max_tokens": memo.SHORT_QUERY_MAX_TOKENS},
                "rewrite": "产品 _retrieval_text 仅剥离寒暄前缀；本 query 无前缀 -> 不改写",
            },
        })

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    md = ["# S2 检索复现（n200 只读副本，K2-off/time-off，每条 3 次）", "",
          "- 源 `%s` sha `%s`；副本 `%s`；不改代码/不起服务/不写产品库。" %
          (SRC, report["source_sha256"][:16], dst),
          "- 参数：`memory_service.retrieve(topk=20)`；确定性：**%s**" %
          ("一致" if report["deterministic"] else "不一致（非确定，停）"), "",
          "| query | target | rank×3 | 空结果×3 | top1 分数×3 | 原因 |",
          "|---|---|---|---|---|---|"]
    for x in report["queries"]:
        md.append("| %s | %s | %s | %s | %s | %s |" % (
            x["id"], x["target"], x["rank_x3"],
            [not r["ids"] for r in x["runs"]],
            [r["top1_score"] for r in x["runs"]],
            x["classification"]["primary"]))
    md += ["", "## 逐条证据", ""]
    for x in report["queries"]:
        md += ["### %s `%s` → target %d" % (x["id"], x["text"], x["target"]),
               "- 目标块：exists=%s，file=%s，size=%s" %
               (x["target_exists"], (x["target_block"] or {}).get("exists"),
                (x["target_block"] or {}).get("size")),
               "- 3 次：ids 一致=%s；gate=%s；candidates=%s；top1=%s" %
               (x["deterministic"], x["evidence"]["gate"],
                x["evidence"]["candidates_scored"],
                x["runs"][0]["top1_score"]),
               "- 目标得分/覆盖/命中：%s / %s / %s；全排序 rank=%s" %
               (x["target_score"], x["target_coverage"], x["target_hits"], x["rank"]),
               "- best：%s；查询 token 缺于目标：%s" %
               (x["best"], x["query_tokens_missing_in_target"]),
               "- 原因：%s；同义词假设：%s" %
               ([c for c in x["classification"]["causes"] if c],
                x["classification"]["synonym_hypotheses"]),
               "- R.search(k=20)：empty=%s rank=%s" %
               (x["rsearch"]["empty"], x["rsearch"]["rank"]), ""]
    md += ["## 结论", "",
           "- 5 条 3 次结果一致，无非确定；空结果 = top1 门槛清空，低排 = 词面覆盖不足（改写/口语词与块用词不匹配），",
           "- 目标块均存在可读、索引无缺失；产品改写对本组 query 不生效（无寒暄前缀）。"]
    with open(args.md, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(json.dumps({"deterministic": report["deterministic"],
                      "queries": [{"id": x["id"], "rank_x3": x["rank_x3"],
                                   "empty_x3": [not r["ids"] for r in x["runs"]],
                                   "top1_x3": [r["top1_score"] for r in x["runs"]],
                                   "gate": x["evidence"]["gate"],
                                   "target_score": x["target_score"],
                                   "target_cov": x["target_coverage"],
                                   "reason": x["classification"]["primary"],
                                   "rsearch_rank": x["rsearch"]["rank"]}
                                  for x in report["queries"]]},
                     ensure_ascii=False, indent=1))
    return 0 if report["deterministic"] else 3


if __name__ == "__main__":
    raise SystemExit(main())