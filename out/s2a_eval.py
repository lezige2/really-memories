# -*- coding: utf-8 -*-
"""S2-A 离线评估：repro 5 + held-out 5，baseline vs query-expand。

只读 n200 副本；不写产品库、不起服务。
输出 out/S2-A-EVAL.json / out/S2-A-EVAL.md
"""
import hashlib
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "out"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import memory_service as memo      # noqa: E402
import memory_source as ms         # noqa: E402
import query_expand as qexp        # noqa: E402

SRC = os.path.join(ROOT, "kvmem", "scale40k", "n200", "chat.db")
TMP = os.path.join(ROOT, "tmp", "s2a")
REPRO_IDS = ["q048", "q052", "q060", "q062", "q063"]
HELDOUT = os.path.join(ROOT, "out", "S2-HELDOUT-5.jsonl")


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def full_ranking(query, rows):
    qt = memo.tokens(query)
    scored = []
    for r in rows:
        text = str(r[3] or "")
        label = str(r[2] or "")
        blob = (text + "\n" + label).lower()
        hits = sorted(t for t in qt if t in blob)
        if not hits:
            continue
        scored.append({"id": int(r[0]), "score": float(len(hits))})
    scored.sort(key=lambda x: (-x["score"], x["id"]))
    return scored


def measure(rows, query, target):
    hits, _stats = memo.retrieve(query, rows, topk=20, meta_fn=None,
                                 return_stats=True)
    ids = [int(h["id"]) for h in hits]
    ranked = full_ranking(query, rows)
    rank = None
    for i, x in enumerate(ranked, start=1):
        if x["id"] == target:
            rank = i
            break
    return {"rank": rank, "empty": len(ids) == 0,
            "pool20_rank": bool(rank and rank <= 20),
            "pool20_mounted": target in ids, "n": len(ids)}


def main():
    os.makedirs(TMP, exist_ok=True)
    dst = os.path.join(TMP, "chat.db")
    if os.path.exists(dst):
        os.remove(dst)
    s = sqlite3.connect("file:%s?mode=ro" % SRC.replace("\\", "/"), uri=True)
    d = sqlite3.connect(dst)
    with d:
        s.backup(d)
    s.close()
    d.close()
    con = sqlite3.connect(dst)
    rows = ms.block_rows(con)
    con.close()

    qs = {q["id"]: q for q in
          (json.loads(l) for l in open(os.path.join(ROOT, "kvmem", "scale40k",
                                                    "n200", "queries.jsonl"),
                                       encoding="utf-8"))}
    cases = []
    for qid in REPRO_IDS:
        q = qs[qid]
        cases.append({"id": qid, "set": "repro", "text": q["text"],
                      "target": int(q["target_block_id"])})
    heldout_sha = sha_file(HELDOUT)
    for line in open(HELDOUT, encoding="utf-8"):
        h = json.loads(line)
        cases.append({"id": h["id"], "set": "heldout", "text": h["query"],
                      "target": int(h["target_block_id"])})

    out = []
    for c in cases:
        before = measure(rows, c["text"], c["target"])
        expanded, hits = qexp.expand_query(c["text"])
        after = measure(rows, expanded, c["target"]) if hits else dict(before)
        out.append({**c, "expansions": hits, "expanded_query": expanded,
                    "before": before, "after": after})

    def pool(caseset, key, metric):
        xs = [r for r in out if r["set"] == caseset]
        return sum(1 for r in xs if r[key][metric]), len(xs)

    stats = {}
    for name, cs in (("repro", "repro"), ("heldout", "heldout")):
        for phase in ("before", "after"):
            for metric in ("pool20_rank", "pool20_mounted"):
                stats["%s_%s_%s" % (name, phase, metric)] = "%d/%d" % pool(cs, phase, metric)
    summary = {
        **stats,
        "repro_empty_after": sum(1 for r in out if r["set"] == "repro" and r["after"]["empty"]),
        "heldout_empty_after": sum(1 for r in out if r["set"] == "heldout" and r["after"]["empty"]),
        "heldout_sha256": heldout_sha,
        # 预注册口径：held-out 5/5 进池（候选池 rank≤20）；原 5 条 ≥4/5
        "pass_offline": (pool("heldout", "after", "pool20_rank")[0] == 5
                         and pool("repro", "after", "pool20_rank")[0] >= 4),
    }
    report = {"schema": "s2a_eval_v1", "source": SRC,
              "source_sha256": sha_file(SRC), "heldout_sha256": heldout_sha,
              "summary": summary, "cases": out}
    json.dump(report, open(os.path.join(ROOT, "out", "S2-A-EVAL.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)

    lines = ["# S2-A 离线评估（baseline vs query-expand）", "",
             "- held-out sha256 `%s`；n200 源 sha `%s`" % (heldout_sha, sha_file(SRC)),
             "- 汇总：" + json.dumps(summary, ensure_ascii=False), "",
             "| id | set | query | target | before rank/mounted | after rank/mounted | expansions |",
             "|---|---|---|---|---|---|---|"]
    for r in out:
        lines.append("| %s | %s | %s | %s | %s/%s | %s/%s | %s |" % (
            r["id"], r["set"], r["text"], r["target"],
            r["before"]["rank"], r["before"]["pool20_mounted"],
            r["after"]["rank"], r["after"]["pool20_mounted"],
            ", ".join(h["item"] for h in r["expansions"]) or "-"))
    open(os.path.join(ROOT, "out", "S2-A-EVAL.md"), "w", encoding="utf-8").write(
        "\n".join(lines) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for r in out:
        print(r["id"], r["set"], "before", r["before"], "after", r["after"],
              [h["item"] for h in r["expansions"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())