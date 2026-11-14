# -*- coding: utf-8 -*-
"""bge-reranker-v2-m3 POC（CPU-only，离线）：cross-encoder 能否压住 3/20 负例作答。

只读 n200 副本；raw top20 候选（现有 hit-count 检索、无 coverage 闸）；
对 (query, candidate) 打分，做阈值扫描；不接服务、不写库、不 commit。
输出 out/POC-RERANK.json
"""
import json
import os
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import memory_service as memo      # 仅用 tokenizer / 词面分（种子）
import memory_source as ms

DB = os.path.join(ROOT, "kvmem", "scale40k", "n200", "chat.db")
TARGETS = os.path.join(ROOT, "out", "P2-HELDOUT-20.jsonl")
NEGS = os.path.join(ROOT, "out", "P2-HELDOUT-20-NEG.jsonl")
MODEL = os.environ.get("RERANK_MODEL", r"D:\models\bge-reranker-v2-m3-ms")
OUT = os.path.join(ROOT, "out", "POC-RERANK.json")
TOPK = 20
BATCH = 8


def raw_top20(rows, q):
    qt = memo.tokens(q)
    sc = []
    for r in rows:
        t = str(r[3]).lower()
        h = [x for x in qt if x in t]
        if h:
            sc.append((len(h), int(r[0])))
    sc.sort(key=lambda x: (-x[0], x[1]))
    return [i for _s, i in sc[:TOPK]]


def main():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    rows = ms.block_rows(con)
    con.close()
    text_by_id = {int(r[0]): str(r[3]) for r in rows}
    tg = [json.loads(l) for l in open(TARGETS, encoding="utf-8")
          if l.strip() and json.loads(l).get("kind") == "target"]
    ng = [json.loads(l) for l in open(NEGS, encoding="utf-8") if l.strip()]

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL)
    model.eval()
    torch.set_num_threads(max(1, (os.cpu_count() or 4)))
    load_s = round(time.time() - t0, 1)

    def score_pairs(q, ids):
        out = []
        for i in range(0, len(ids), BATCH):
            chunk = ids[i:i + BATCH]
            pairs = [(q, text_by_id[j]) for j in chunk]
            enc = tok([p[0] for p in pairs], [p[1] for p in pairs], padding=True,
                      truncation=True, max_length=512, return_tensors="pt")
            with torch.no_grad():
                logits = model(**enc).logits.view(-1).float().tolist()
            out.extend(float(x) for x in logits)
        return out

    per = []
    t1 = time.time()
    for item in ([dict(x, kind="target") for x in tg] + [dict(x, kind="negative") for x in ng]):
        q = item["query"]
        ids = raw_top20(rows, q)
        scores = score_pairs(q, ids)
        ranked = sorted(zip(ids, scores), key=lambda x: (-x[1], x[0]))
        rec = {"id": item["id"], "kind": item["kind"], "query": q,
               "target": item.get("target"),
               "expected": item.get("expected"),
               "raw_ids": ids,
               "reranked": [{"id": i, "score": round(s, 4)} for i, s in ranked],
               "top1": {"id": ranked[0][0], "score": round(ranked[0][1], 4)},
               "top1_text": text_by_id[ranked[0][0]][:60]}
        if item["kind"] == "target":
            t = int(item["target"])
            ts = next((s for i, s in ranked if i == t), None)
            tr = next((n + 1 for n, (i, _s) in enumerate(ranked) if i == t), None)
            rec.update(target_score=round(ts, 4) if ts is not None else None,
                       target_rank=tr,
                       target_top1=(ranked[0][0] == t))
        per.append(rec)
        print("%s %s top1=%.3f %s" % (item["kind"][:3], item["id"],
                                      ranked[0][1], q[:30]), flush=True)
    infer_s = round(time.time() - t1, 1)

    # 阈值扫描（top1 分数）
    tg_per = [x for x in per if x["kind"] == "target"]
    ng_per = [x for x in per if x["kind"] == "negative"]
    flagged_ids = ["P2-N01", "P2-N08", "P2-N11"]
    tops = sorted({round(x["top1"]["score"], 4) for x in per})
    grid = tops + [round(tops[-1] + 0.5, 4)]
    curve = []
    best = None
    for T in grid:
        tgt_kept = sum(1 for x in tg_per
                       if x.get("target_score") is not None and x["target_score"] >= T)
        tgt_top1 = sum(1 for x in tg_per if x["top1"]["score"] >= T
                       and x.get("target_top1"))
        neg_kept = sum(1 for x in ng_per if x["top1"]["score"] >= T)
        flag_kept = [x["id"] for x in ng_per
                     if x["id"] in flagged_ids and x["top1"]["score"] >= T]
        row = {"T": T, "targets_kept": tgt_kept, "targets_top1": tgt_top1,
               "negatives_kept": neg_kept, "flagged_kept": flag_kept}
        curve.append(row)
        if not flag_kept:
            if best is None or tgt_kept > best["targets_kept"]:
                best = row
    rep = {
        "schema": "poc_rerank_v1",
        "model": MODEL,
        "env": {"torch": torch.__version__, "transformers": __import__("transformers").__version__,
                "device": "cpu", "threads": torch.get_num_threads()},
        "db": DB, "raw_topk": TOPK, "batch": BATCH,
        "load_s": load_s, "infer_s": infer_s,
        "n_target": len(tg_per), "n_negative": len(ng_per),
        "flagged_negatives": flagged_ids,
        "per_query": per,
        "threshold_curve": curve,
        "best_threshold": best,
        "conclusion": None,
    }
    # 结论
    if best:
        all_targets = best["targets_kept"] == len(tg_per)
        rep["conclusion"] = {
            "flagged_all_rejected": True,
            "targets_kept": best["targets_kept"], "n_target": len(tg_per),
            "negatives_kept": best["negatives_kept"],
            "threshold": best["T"],
            "pass": bool(all_targets),
            "text": ("存在阈值同时踢掉 3 条负例并保留全部 target"
                     if all_targets else "可踢掉 3 条负例，但 target 有损失"),
        }
    else:
        rep["conclusion"] = {"flagged_all_rejected": False,
                             "text": "不存在能同时踢掉 3 条负例的阈值（分数不可分）"}
    json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"load_s": load_s, "infer_s": infer_s,
                      "best": best, "conclusion": rep["conclusion"]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
