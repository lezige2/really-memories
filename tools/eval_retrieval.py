# -*- coding: utf-8 -*-
"""eval_retrieval.py -- M1-lite acceptance: does facet selection beat plain BM25?

The point of a fixed eval set is to be able to say "no" to a change. So this file owns:

  * a corpus of ten blocks with deliberately overlapping vocabulary (two of them mention
    projects, two mention dates), so "topically similar" is not the same as "correct";
  * queries typed by what they need: single-block, multi-block (must select BOTH),
    and absent (must select NOTHING);
  * a BM25 baseline that differs from the facet ranker in ONE way -- the scoring function.
    Same tokenizer, same corpus, same gate, same tie-break.

No model is loaded. Retrieval is measured as retrieval: folding generated text into the
signal would let the language model's noise decide whether the index is any good.

Usage:  python tools/eval_retrieval.py [--show]
"""
import argparse
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import retrieval as R                                     # noqa: E402

DB = os.path.join(ROOT, "kvmem", "eval.db")

# Ten episodes. Two share "项目", two share dates and numbers -- enough for a lexical
# ranker to be fooled if the only signal is overlap.
CORPUS = [
    ("profile", "个人档案",
     "我叫林知远，在供应链分析组工作，我的工号是 A-4417。我养的猫叫年糕，是一只橘猫。"
     "每周例会订在 B栋3层302会议室。"),
    ("project", "项目信息",
     "我在做蓝鲸项目，项目代号就是蓝鲸。蓝鲸项目定在 3月14日 上线，负责人是周敏。"),
    ("diet", "饮食",
     "我不吃香菜，咖啡只喝美式，不加糖，也不用奶精。"),
    ("commute", "通勤",
     "我住在城东的梧桐里，每天坐 4号线 到公司，通勤大约 40分钟。"),
    ("device", "设备",
     "我的开发机是 ThinkPad X1，外接一台 27寸 显示器，键盘是 HHKB。"),
    ("hobby", "爱好",
     "周末我喜欢爬山，去年爬过 泰山 和 黄山，今年想去 武功山。"),
    ("health", "健康",
     "我对 花生 过敏，体检时 血压 偏低，医生建议多睡觉。"),
    ("team", "团队",
     "我们组一共 7个人，前端是 李萌，后端是 陈昊，测试是 王雪。"),
    ("finance", "财务",
     "每月 15号 发工资，报销走 钉钉 审批，发票要纸质的。"),
    ("travel", "出行",
     "出差标准是 高铁二等座，住宿每晚不超过 500元，超过要提前申请。"),
]

# (query, gold block names, kind)
QUERIES = [
    ("我的工号是多少", ["profile"], "single"),
    ("我养的猫叫什么", ["profile"], "single"),
    ("蓝鲸项目什么时候上线", ["project"], "single"),
    ("项目负责人是谁", ["project"], "single"),
    ("周例会订在哪个会议室", ["profile"], "single"),
    ("我喝咖啡加糖吗", ["diet"], "single"),
    ("我对什么过敏", ["health"], "single"),
    ("我住哪儿，平时怎么上班", ["commute"], "single"),
    ("我们组有几个人", ["team"], "single"),
    ("出差住宿标准是多少", ["travel"], "single"),
    ("我的工号和项目上线日期分别是什么", ["profile", "project"], "multi"),
    ("猫叫什么，项目又是谁负责", ["profile", "project"], "multi"),
    ("我的过敏源和饮食禁忌分别是什么", ["health", "diet"], "multi"),
    ("开发机型号和显示器尺寸", ["device"], "multi"),
    ("我车牌号是多少", [], "absent"),
    ("我的护照号是多少", [], "absent"),
    ("我老家在哪个城市", [], "absent"),
    ("我的血型是什么", [], "absent"),
    ("我女朋友叫什么名字", [], "absent"),
]


def build(db=DB):
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE memory_source (
        id INTEGER PRIMARY KEY, tenant TEXT NOT NULL DEFAULT 'default',
        scope TEXT NOT NULL DEFAULT 'private', mode TEXT NOT NULL DEFAULT 'chat',
        name TEXT NOT NULL, label TEXT NOT NULL, text TEXT NOT NULL,
        source_hash TEXT NOT NULL, created_at TEXT NOT NULL);
    """)
    for i, (name, label, text) in enumerate(CORPUS, start=1):
        con.execute("INSERT INTO memory_source (id,name,label,text,source_hash,created_at) "
                    "VALUES (?,?,?,?,?,datetime('now'))", (i, name, label, text, "h%d" % i))
    con.commit()
    R.build_index(con)
    return con


def run(con, mode, k=5):
    per = []
    for q, gold, kind in QUERIES:
        sel = R.search(con, q, k=k, mode=mode)
        got = [r["name"] for r in sel]
        scores = [round(r["score"], 2) for r in sel]
        if gold:
            ranks = [got.index(g) + 1 for g in gold if g in got]
            rec = {kk: (len([g for g in gold if g in got[:kk]]) / len(gold)) for kk in (1, 3, 5)}
            mrr = (1.0 / min(ranks)) if ranks else 0.0
            ok = rec[k] == 1.0
        else:
            rec = {1: 0.0, 3: 0.0, 5: 0.0}
            mrr = 0.0
            ok = (len(got) == 0)
        per.append({"q": q, "kind": kind, "gold": gold, "got": got, "scores": scores,
                    "rec": rec, "mrr": mrr, "ok": ok})
    return per


def summarize(per, label):
    pos = [p for p in per if p["gold"]]
    neg = [p for p in per if not p["gold"]]
    r1 = sum(p["rec"][1] for p in pos) / len(pos)
    r3 = sum(p["rec"][3] for p in pos) / len(pos)
    r5 = sum(p["rec"][5] for p in pos) / len(pos)
    mrr = sum(p["mrr"] for p in pos) / len(pos)
    empty_ok = sum(1 for p in neg if p["ok"])
    print("%-6s recall@1 %.3f  recall@3 %.3f  recall@5 %.3f  MRR %.3f   "
          "absent->empty %d/%d" % (label, r1, r3, r5, mrr, empty_ok, len(neg)))
    return {"r1": r1, "r3": r3, "r5": r5, "mrr": mrr,
            "empty": empty_ok, "empty_n": len(neg)}


def show(per, title):
    print("\n" + title)
    for p in per:
        mark = "ok " if p["ok"] else "MISS"
        print("  %-4s %-26s gold=%-18s top=%s  %s"
              % (mark, p["q"][:26], ",".join(p["gold"]) or "(none)",
                 ",".join(p["got"]) or "(empty)", p["scores"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--k", type=int, default=3)
    a = ap.parse_args()

    con = build()
    try:
        print("eval corpus: %d blocks, %d queries (%d single, %d multi, %d absent)\n"
              % (len(CORPUS), len(QUERIES),
                 sum(1 for _q, _g, k in QUERIES if k == "single"),
                 sum(1 for _q, _g, k in QUERIES if k == "multi"),
                 sum(1 for _q, _g, k in QUERIES if k == "absent")))
        base = run(con, "bm25")
        fact = run(con, "facet")
        b = summarize(base, "bm25")
        f = summarize(fact, "facet")
        print("\ndelta: recall@1 %+.3f   recall@3 %+.3f   MRR %+.3f   absent->empty %+d"
              % (f["r1"] - b["r1"], f["r3"] - b["r3"], f["mrr"] - b["mrr"],
                 f["empty"] - b["empty"]))
        if a.show:
            show(base, "BM25 baseline")
            show(fact, "facet ranker")
        bad = [p for p in fact if not p["ok"]]
        if bad:
            print("\nfacet ranker misses:")
            for p in bad:
                print("  %-26s gold=%-18s got=%s"
                      % (p["q"][:26], ",".join(p["gold"]) or "(none)",
                         ",".join(p["got"]) or "(empty)"))
        return 0 if not bad else 1
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())