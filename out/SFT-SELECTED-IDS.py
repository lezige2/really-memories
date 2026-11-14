# -*- coding: utf-8 -*-
"""TASK-117/118：从评测产物（+ assistant_log）导出 selected_ids 命中摘要。
每条 case：注入记忆 id（setup.prelude 的 remember id）是否出现在 selected_ids、排名第几。
优先 assistant_log（ask 事件 retrieval.selected_ids，按 text_sha16 匹配），否则用 actual.block_ids。
用法：python -X utf8 out/SFT-SELECTED-IDS.py --product out/POLICY-P3-MT20.json --out out/SFT-SELECTED-IDS.json
"""
import argparse
import glob
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha16(s):
    return hashlib.sha256(str(s).encode("utf-8")).hexdigest()[:16]


def load_log_index(log_dir):
    idx = {}
    for p in glob.glob(os.path.join(log_dir, "*.jsonl")):
        try:
            for line in open(p, encoding="utf-8", errors="replace"):
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("event") == "ask" and e.get("text_sha16"):
                    r = (e.get("retrieval") or {})
                    if r.get("selected_ids"):
                        idx[e["text_sha16"]] = (r.get("selected_ids") or [], r.get("scores") or [])
        except Exception:
            continue
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", action="append", required=True)
    ap.add_argument("--log-dir", default=os.path.join(ROOT, "kvmem", "assistant", "sessions"))
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "SFT-SELECTED-IDS.json"))
    args = ap.parse_args()
    log_idx = load_log_index(args.log_dir)
    rows = []
    for path in args.product:
        d = json.load(open(path, encoding="utf-8"))
        for r in d.get("results") or []:
            pre = (r.get("setup") or {}).get("prelude") or []
            injected = [int(x["id"]) for x in pre if x.get("action") == "remember" and x.get("id") is not None]
            act = r.get("actual") or {}
            sel_from_service = list(act.get("selected_ids") or [])
            selected = sel_from_service or list(act.get("block_ids") or [])
            src = "service.retrieval" if sel_from_service else "block_ids"
            hit = None
            rank = None
            if injected and selected:
                hit = any(i in selected for i in injected)
                rank = next((k + 1 for k, v in enumerate(selected) if v in injected), None)
            q = str(r.get("input") or "")
            if log_idx.get(sha16(q)):
                selected, _scores = log_idx[sha16(q)]
                src = "assistant_log"
                hit = any(i in selected for i in injected) if injected else None
                rank = next((k + 1 for k, v in enumerate(selected) if v in injected), None) if injected else None
            rows.append({"product": os.path.basename(path), "id": r.get("id"), "category": r.get("category"),
                         "ok": bool(r.get("pass")), "input": q, "injected_ids": injected,
                         "selected_ids": selected, "selected_source": src, "hit": hit, "rank": rank,
                         "answer": str(act.get("answer"))[:120]})
    inj = [x for x in rows if x["injected_ids"]]
    hitn = [x for x in inj if x["hit"]]
    rep = {"schema": "sft_selected_ids_v1", "tasks": ["TASK-117", "TASK-118"],
           "log_dir": args.log_dir, "log_index_n": len(log_idx),
           "summary": {"cases": len(rows), "with_injected": len(inj), "hit": len(hitn),
                       "hit_rate": round(len(hitn) / len(inj), 4) if inj else None,
                       "rank_hist": {str(k): sum(1 for x in inj if x["rank"] == k) for k in (1, 2, 3, 4)}},
           "rows": rows}
    json.dump(rep, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"out": args.out, "sha16": hashlib.sha256(open(args.out, "rb").read()).hexdigest()[:16],
                      "summary": rep["summary"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()