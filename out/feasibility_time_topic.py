# -*- coding: utf-8 -*-
"""Offline feasibility: (1) can block text yield an event time? (2) topic match?

No service, no DB writes. Reads daily blocks read-only and MT20 cases from disk.
"""
import json
import re
import sqlite3
import sys

sys.path.insert(0, "tools")
import event_time as et  # noqa: E402

DAILY = sqlite3.connect("file:kvmem/daily/chat.db?immutable=1", uri=True)
BLOCKS = {int(r[0]): str(r[1]) for r in
          DAILY.execute("SELECT id,text FROM memory_source ORDER BY id")}
MT = [json.loads(l) for l in open("out/SFT-EXTRA-CASES-v9-MT20.jsonl", encoding="utf-8") if l.strip()]

# ---------------- 1) time gate ----------------
# 10 questions with explicit time words, each paired with the block that should answer.
TIME_CASES = [
    ("我去年去过哪？", "我去年去过云南大理。"),
    ("上个月我体检结果怎么样？", "上个月体检，医生说血脂偏高。"),
    ("三年前我在哪工作？", "三年前我在苏州的一家外企上班。"),
    ("我具体哪天去体检？", "我 2026-10-15 去体检。"),
    ("我明年有什么计划？", "明年我打算考一个证书。"),
    ("上周我去哪出差了？", "上周我去南京出差了。"),
    ("2025年3月我搬去哪了？", "2025年3月我搬到了杭州。"),
    ("我前天买了什么？", "前天我买了一个显示器。"),
    ("下个月我要做什么？", "下个月要交房子的续租合同。"),
    ("我什么时候开始学吉他的？", "我从 2024 年 5 月开始学吉他。"),
]
time_rows = []
for q, block in TIME_CASES:
    created = "2026-11-01T10:00:00"
    res = et.parse_event_time(block, created)
    # also try bare date token extraction as a secondary signal
    m = re.search(r"(\d{4})[-年](\d{1,2})[-月](\d{1,2})?", block)
    judgeable = bool(res.get("event_date")) or bool(m)
    time_rows.append({"question": q, "block": block,
                      "event_date": res.get("event_date"),
                      "confidence": res.get("event_confidence"),
                      "periodic": bool(et.is_periodic(block)),
                      "date_token": m.group(0) if m else None,
                      "judgeable": judgeable})
judgeable_n = sum(1 for r in time_rows if r["judgeable"])

# ---------------- 2) topic gate ----------------
STOP = set("我的 你 是 吗 呢 什么 多少 哪里 哪个 在哪 怎么 请问 一下 记得 告诉 过 我 有 在 和 与 就 也 都 很 了 吗".split())


def tokens(s):
    s = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", " ", str(s))
    out = []
    for w in s.split():
        if w and w not in STOP:
            out.append(w)
    # crude CN bigrams for recall
    for seg in re.findall(r"[\u4e00-\u9fff]+", s):
        for i in range(len(seg) - 1):
            bg = seg[i:i + 2]
            if bg not in STOP:
                out.append(bg)
    return out


def bm25_scores(query, docs):
    q = tokens(query)
    df = {}
    for d in docs:
        for w in set(tokens(d["text"])):
            df[w] = df.get(w, 0) + 1
    N = len(docs)
    avg = sum(len(tokens(d["text"])) for d in docs) / max(1, N)
    scores = []
    for d in docs:
        tf = {}
        for w in tokens(d["text"]):
            tf[w] = tf.get(w, 0) + 1
        s = 0.0
        dl = len(tokens(d["text"])) or 1
        for w in set(q):
            if w not in tf:
                continue
            idf = (N - df.get(w, 0) + 0.5) / (df.get(w, 0) + 0.5)
            s += (tf[w] * 2.5) / (tf[w] + 1.5 * (0.25 + 0.75 * dl / avg)) * idf
        scores.append((s, d["id"]))
    scores.sort(reverse=True)
    return scores


# pool: the case's own memories (gold) + daily blocks as distractors
topic_rows = []
for case in MT:
    golds = [st["text"] for st in case.get("pre_state") or [] if st["action"] == "remember"]
    docs = [{"id": "g%d" % i, "text": t, "gold": True} for i, t in enumerate(golds)]
    docs += [{"id": "d%d" % i, "text": t, "gold": False} for i, t in BLOCKS.items()]
    ranked = bm25_scores(case["input"], docs)
    top = ranked[0][1] if ranked else None
    hit = bool(docs[[d["id"] for d in docs].index(top)]["gold"]) if top else False
    topic_rows.append({"id": case["id"], "question": case["input"],
                       "top": top, "top_is_gold": hit,
                       "top_score": round(ranked[0][0], 3) if ranked else None,
                       "gold_n": len(golds), "pool_n": len(docs)})
topic_hit = sum(1 for r in topic_rows if r["top_is_gold"])
topic_rate = topic_hit / len(topic_rows)

rep = {
    "schema": "feasibility_time_topic_v1",
    "time_gate": {"n": len(time_rows), "judgeable": judgeable_n,
                  "rate": round(judgeable_n / len(time_rows), 3),
                  "collapse": judgeable_n == 0,
                  "rows": time_rows},
    "topic_gate": {"n": len(topic_rows), "hit": topic_hit,
                   "rate": round(topic_rate, 3), "pass_70": topic_rate >= 0.70,
                   "rows": topic_rows},
}
json.dump(rep, open("out/FEASIBILITY-TIME-TOPIC.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

md = ["# 离线可行性：时间门 / 主题门", "",
      "## 1 时间门（能否从块文本抽出事实时间）", "",
      "| # | 问题 | 块文本 | event_date | 置信 | 可判 |", "|---|---|---|---|---|---|"]
for i, r in enumerate(time_rows, 1):
    md.append("| %d | %s | %s | %s | %s | %s |" % (
        i, r["question"], r["block"][:26], r["event_date"] or "—",
        r["confidence"], "✅" if r["judgeable"] else "❌"))
md += ["", "可判 **%d/%d**；%s" % (judgeable_n, len(time_rows),
                                 "时间门塌" if judgeable_n == 0 else "时间门可用"), "",
       "## 2 主题门（BM25 top-1 是否命中该问题的正确记忆）", "",
       "| case | 问题 | top | 命中 | 分数 |", "|---|---|---|---|---|"]
for r in topic_rows:
    md.append("| %s | %s | %s | %s | %s |" % (
        r["id"], r["question"][:18], r["top"], "✅" if r["top_is_gold"] else "❌", r["top_score"]))
md += ["", "命中 **%d/%d = %.0f%%**；门 70%%：**%s**" % (
    topic_hit, len(topic_rows), 100 * topic_rate, "过" if topic_rate >= 0.70 else "不过")]
open("out/FEASIBILITY-TIME-TOPIC.md", "w", encoding="utf-8").write("\n".join(md))
print("time judgeable %d/%d | topic hit %d/%d = %.0f%%" % (
    judgeable_n, len(time_rows), topic_hit, len(topic_rows), 100 * topic_rate))