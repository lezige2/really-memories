# -*- coding: utf-8 -*-
"""S2 闸代价诊断：n200 副本，repro 5 + held-out 5，对比“开闸(现状)”与“绕过 gate 直取 top20”。

只测量：不改阈值/默认、不改产品代码、不写库、不起服务；副本落 tmp/s2_gate。
输出 out/S2-GATE-DIAG.json / .md
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

SRC = os.path.join(ROOT, "kvmem", "scale40k", "n200", "chat.db")
TMP = os.path.join(ROOT, "tmp", "s2_gate")
REPRO = ["q048", "q052", "q060", "q062", "q063"]


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


def rank_off(rows, query, k=20):
    """绕过 coverage/score 闸：只按 (score, -id) 排序取前 k（诊断用，不改产品）。"""
    qt = memo.tokens(query)
    scored = []
    for r in rows:
        text = str(r[3] or "")
        blob = (text + "\n" + str(r[2] or "")).lower()
        hits = sorted(t for t in qt if t in blob)
        if not hits:
            continue
        scored.append({"id": int(r[0]), "score": float(len(hits)),
                       "coverage": memo.coverage_of(hits, qt), "hits": hits})
    scored.sort(key=lambda x: (-x["score"], x["id"]))
    return scored, qt


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "S2-GATE-DIAG.json"))
    ap.add_argument("--md", default=os.path.join(ROOT, "out", "S2-GATE-DIAG.md"))
    args = ap.parse_args(argv)

    dst = os.path.join(TMP, "chat.db")
    copy_db(SRC, dst)
    con = sqlite3.connect(dst)
    rows = ms.block_rows(con)

    qs = {q["id"]: q for q in (json.loads(l) for l in
                               open(os.path.join(ROOT, "kvmem", "scale40k", "n200",
                                                 "queries.jsonl"), encoding="utf-8"))}
    held = [json.loads(l) for l in open(os.path.join(ROOT, "out", "S2-HELDOUT-5.jsonl"),
                                        encoding="utf-8") if l.strip()]
    cases = [{"suite": "repro", "id": qid, "text": qs[qid]["text"],
              "target": int(qs[qid]["target_block_id"])} for qid in REPRO]
    cases += [{"suite": "heldout", "id": h["id"], "text": h["text"],
               "target": int(h["target_block_id"]), "expect": h.get("expect_any")}
              for h in held]

    out = []
    for c in cases:
        ranked, qt = rank_off(rows, c["text"])
        ids = [x["id"] for x in ranked][:20]
        rank = None
        tgt = None
        for i, x in enumerate(ranked, start=1):
            if x["id"] == c["target"]:
                rank, tgt = i, x
                break
        off_in = c["target"] in ids
        # 开闸（现状）
        hits, stats = memo.retrieve(c["text"], rows, topk=20, meta_fn=None, return_stats=True)
        on_ids = [int(h["id"]) for h in hits]
        on_rank = on_ids.index(c["target"]) + 1 if c["target"] in on_ids else None
        out.append({
            "suite": c["suite"], "id": c["id"], "text": c["text"],
            "target": c["target"],
            "gate_on": {"empty": not on_ids, "in_pool": c["target"] in on_ids,
                        "rank": on_rank, "n": len(on_ids),
                        "gate": stats.get("gate"), "top1": hits[0]["score"] if hits else None},
            "gate_off": {"empty": not ranked, "in_pool": off_in, "rank": rank,
                         "n": len(ids), "top1": ranked[0]["score"] if ranked else None,
                         "target_score": tgt["score"] if tgt else 0,
                         "target_coverage": tgt["coverage"] if tgt else 0,
                         "query_tokens": len(qt)},
        })

    def summarize(suite):
        xs = [x for x in out if x["suite"] == suite]
        return {"n": len(xs),
                "gate_on_recall": sum(1 for x in xs if x["gate_on"]["in_pool"]),
                "gate_off_recall": sum(1 for x in xs if x["gate_off"]["in_pool"]),
                "gate_on_empty": sum(1 for x in xs if x["gate_on"]["empty"]),
                "gate_off_empty": sum(1 for x in xs if x["gate_off"]["empty"])}

    summ = {"repro": summarize("repro"), "heldout": summarize("heldout")}
    rescued = [x["id"] for x in out
               if not x["gate_on"]["in_pool"] and x["gate_off"]["in_pool"]]
    still_missing = [x["id"] for x in out if not x["gate_off"]["in_pool"]]
    verdict = {
        "repro_gate_off_5of5": summ["repro"]["gate_off_recall"] == 5,
        "heldout_gate_off_5of5": summ["heldout"]["gate_off_recall"] == 5,
        "rescued_by_bypass": rescued,
        "still_missing_after_bypass": still_missing,
        "conclusion": ("关闸后能救回：repro=%d/5, heldout=%d/5；%s" % (
            summ["repro"]["gate_off_recall"], summ["heldout"]["gate_off_recall"],
            "两档均 5/5 → 问题在闸语义" if summ["repro"]["gate_off_recall"] == 5
            and summ["heldout"]["gate_off_recall"] == 5
            else "仍有目标不进 top20 → 闸之外还有排序/词面问题，需再评估 C")),
    }

    report = {"schema": "s2_gate_diag_v1", "source": SRC, "source_sha256": sha_file(SRC),
              "copy": dst, "mode": "diagnostic bypass (no product change)",
              "k": 20, "cases": out, "summary": summ, "verdict": verdict}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    md = ["# S2 闸代价诊断（n200 副本，只测量）", "",
          "- 源 `%s` sha `%s`；副本 `%s`；未改阈值/默认、未写库、未起服务。" %
          (SRC, report["source_sha256"][:16], dst),
          "- 开闸=现状 `retrieve(topk=20)`（coverage 0.30 等 gate）；关闸=诊断脚本内绕过 gate，只按 score 取 top20。",
          "", "| suite | id | target | 开闸 in/rank | 关闸 in/rank | target score/cov |",
          "|---|---|---|---|---|---|"]
    for x in out:
        md.append("| %s | %s | %s | %s / %s | %s / %s | %s / %s |" % (
            x["suite"], x["id"], x["target"],
            x["gate_on"]["in_pool"], x["gate_on"]["rank"],
            x["gate_off"]["in_pool"], x["gate_off"]["rank"],
            x["gate_off"]["target_score"], round(x["gate_off"]["target_coverage"], 3)))
    md += ["", "## 汇总",
           "- repro：开闸 %d/5，关闸 %d/5；empty 开/关 = %d/%d" %
           (summ["repro"]["gate_on_recall"], summ["repro"]["gate_off_recall"],
            summ["repro"]["gate_on_empty"], summ["repro"]["gate_off_empty"]),
           "- heldout：开闸 %d/5，关闸 %d/5；empty 开/关 = %d/%d" %
           (summ["heldout"]["gate_on_recall"], summ["heldout"]["gate_off_recall"],
            summ["heldout"]["gate_on_empty"], summ["heldout"]["gate_off_empty"]),
           "- 关闸救回：%s" % (rescued or "无"),
           "- 关闸仍不进池：%s" % (still_missing or "无"),
           "", "## 结论", "- %s" % verdict["conclusion"]]
    with open(args.md, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(json.dumps({"summary": summ, "verdict": verdict,
                      "per_case": [{k: x[k] for k in ("suite", "id", "target",
                                                      "gate_on", "gate_off")}
                                   for x in out]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())