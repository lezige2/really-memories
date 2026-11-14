# -*- coding: utf-8 -*-
"""P2 新粗排（离线、只读）：raw top50 种子 -> BM25(CJK 1/2gram) + 实体/谓词加分 -> top20。

不改产品默认、不写库、不启服务、不 commit。仅用于 P2 Stage0 复核。
输出 out/P2-NEW-COARSE-POOL.json
"""
import hashlib
import json
import math
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import memory_service as memo      # noqa: E402  仅复用其 token（种子池用）
import memory_source as ms         # noqa: E402

SRC = os.path.join(ROOT, "kvmem", "scale40k", "n200", "chat.db")
QF = os.path.join(ROOT, "kvmem", "scale40k", "n200", "queries.jsonl")
OUT = os.path.join(ROOT, "out", "P2-NEW-COARSE-POOL.json")
K1, B = 1.2, 0.75
SEED_K, POOL_K = 50, 20

CJK = re.compile(r"[\u4e00-\u9fff]+")
LAT = re.compile(r"[a-zA-Z0-9]+")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
PHONE = re.compile(r"1[3-9]\d{9}")
PLATE = re.compile(r"[A-Za-z]·?[A-Za-z0-9]{5,}")

# 谓词表（query cue -> doc 命中词）；只做“精确命中加分”，不做 query 扩写
FAM = {
    "plate": (["车牌", "牌子", "车号"], ["车牌号", "车牌", "牌照"]),
    "phone": (["手机", "号码", "电话"], ["手机号", "电话号码", "手机"]),
    "meeting": (["会议", "几点", "几号", "什么时候"], ["会议", "定在"]),
    "hometown": (["老家", "哪儿人", "哪里人"], ["老家"]),
    "seat": (["座位", "位置", "坐"], ["座位", "排"]),
    "company": (["公司", "单位"], ["公司", "单位"]),
    "bank": (["银行卡", "卡号"], ["银行卡", "卡号"]),
    "color": (["颜色", "车色"], ["颜色", "车漆", "色"]),
    "cat": (["猫"], ["猫"]), "dog": (["狗"], ["狗"]),
}


def toks(text):
    t = str(text or "").lower()
    out = set()
    for run in CJK.findall(t):
        out.update(run)                              # unigram
        out.update(run[i:i + 2] for i in range(len(run) - 1))   # bigram
    out.update(w for w in LAT.findall(t))
    return out


def qfam(q):
    for f, (qk, _dk) in FAM.items():
        if any(k in q for k in qk):
            return f
    return None


def dfams(t):
    return {f for f, (_qk, dk) in FAM.items() if any(k in t for k in dk)}


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    con = sqlite3.connect("file:%s?mode=ro" % SRC.replace("\\", "/"), uri=True)
    rows = ms.block_rows(con)
    con.close()
    docs = [(int(r[0]), str(r[3])) for r in rows]
    d_toks = {i: toks(t) for i, t in docs}
    n = len(docs)
    avg = sum(len(v) for v in d_toks.values()) / float(n)
    df = {}
    for v in d_toks.values():
        for t in v:
            df[t] = df.get(t, 0) + 1
    # 实体：合成语料以人名开头 -> 前缀 2/3 字集合（Stage1 需换真实 subject sidecar）
    names = set()
    for _i, t in docs:
        for L in (2, 3):
            p = t[:L]
            if len(p) == L and all("\u4e00" <= c <= "\u9fff" for c in p):
                names.add(p)
    text_by_id = dict(docs)

    def bm25(qt, dt):
        s, dl = 0.0, len(dt)
        for t in qt:
            f = 1 if t in dt else 0
            if not f:
                continue
            idf = math.log(1 + (n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            s += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / avg))
        return s

    def seed50(q):
        qt = memo.tokens(q)
        sc = []
        for i, t in docs:
            h = [x for x in qt if x in t.lower()]
            if h:
                sc.append((len(h), i))
        sc.sort(key=lambda x: (-x[0], x[1]))
        return [i for _s, i in sc[:SEED_K]]

    def score(q, i):
        t = text_by_id[i]
        qt = toks(q)
        parts = {"bm25": round(bm25(qt, d_toks[i]), 4), "entity": 0.0,
                 "predicate": 0.0, "shape": 0.0}
        qf = qfam(q)
        if qf and qf in dfams(t):
            parts["predicate"] = 2.0
        if any(nm in q and nm in t for nm in names):
            parts["entity"] = 3.0
        if qf == "meeting" and DATE.search(t):
            parts["shape"] = 0.5
        if qf == "phone" and PHONE.search(t):
            parts["shape"] = 0.5
        if qf == "plate" and PLATE.search(t):
            parts["shape"] = 0.5
        parts["total"] = round(parts["bm25"] + parts["entity"]
                               + parts["predicate"] + parts["shape"], 4)
        return parts

    def rank_arm(q, arm):
        qf = qfam(q)
        scored = []
        for i in seed50(q):
            t = text_by_id[i]
            sc = bm25(toks(q), d_toks[i])
            if arm in ("predicate", "full") and qf and qf in dfams(t):
                sc += 2.0
            if arm == "full" and any(nm in q and nm in t for nm in names):
                sc += 3.0
            if arm == "full" and qf == "meeting" and DATE.search(t):
                sc += 0.5
            if arm == "full" and qf == "phone" and PHONE.search(t):
                sc += 0.5
            if arm == "full" and qf == "plate" and PLATE.search(t):
                sc += 0.5
            scored.append((sc, i))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [i for _s, i in scored[:POOL_K]]

    qs = [json.loads(l) for l in open(QF, encoding="utf-8")]
    per, hits = [], 0
    for q in qs:
        t = q.get("target_block_id")
        if t is None:
            continue
        t = int(t)
        seed = seed50(q["text"])
        scored = [(score(q["text"], i), i) for i in seed]
        scored.sort(key=lambda x: (-x[0]["total"], x[1]))
        pool = [i for _s, i in scored[:POOL_K]]
        in_pool = t in pool
        hits += in_pool
        rec = {"id": q["id"], "kind": q.get("kind"), "target": t,
               "seed_rank": seed.index(t) + 1 if t in seed else None,
               "in_pool": in_pool,
               "rank": pool.index(t) + 1 if in_pool else None,
               "pool_n": len(pool),
               "score": next((s for s, i in scored if i == t), None),
               "seed_n": len(seed)}
        per.append(rec)
    rep = {
        "schema": "p2_new_coarse_v1",
        "source": SRC, "source_sha256": sha_file(SRC),
        "queries": QF, "queries_sha256": sha_file(QF),
        "script": os.path.abspath(__file__), "script_sha256": sha_file(__file__),
        "params": {"seed_k": SEED_K, "pool_k": POOL_K, "bm25": {"k1": K1, "b": B},
                   "tokenizer": "CJK unigram+bigram + latin words",
                   "bonus": {"entity_exact": 3.0, "predicate_exact": 2.0,
                             "value_shape": 0.5},
                   "gate": "none (no coverage gate)", "query_expand": False},
        "n_targets": len(per), "pool_hits": hits,
        "pool_recall_at_20": round(hits / float(len(per)), 4),
        "misses": [x for x in per if not x["in_pool"]],
        "ablation": {
            arm: sum(1 for q in qs
                     if q.get("target_block_id") is not None
                     and int(q["target_block_id"]) in rank_arm(q["text"], arm))
            for arm in ("bm25", "predicate", "full")},
        "heldout_sanity": None,
        "per_query": per,
    }
    hp = os.path.join(ROOT, "out", "S2-HELDOUT-5.jsonl")
    if os.path.exists(hp):
        held = [json.loads(l) for l in open(hp, encoding="utf-8") if l.strip()]
        rep["heldout_sanity"] = {
            "file": hp, "sha256": sha_file(hp), "n": len(held),
            "pool_hits": sum(1 for h in held
                             if int(h["target_block_id"]) in rank_arm(h["text"], "full")),
            "arms": {arm: sum(1 for h in held
                              if int(h["target_block_id"]) in rank_arm(h["text"], arm))
                     for arm in ("bm25", "predicate", "full")},
        }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(json.dumps({"pool": "%d/%d" % (hits, len(per)),
                      "recall": rep["pool_recall_at_20"],
                      "misses": [m["id"] for m in rep["misses"]],
                      "prev_misses": {x["id"]: x["rank"] for x in per
                                      if x["id"] in ("q048", "q052", "q060",
                                                     "q062", "q063", "q070")}},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
