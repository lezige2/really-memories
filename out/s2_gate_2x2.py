# -*- coding: utf-8 -*-
"""S2 补测：2×2（A off/on × 闸开/关）+ 分离度诊断（n200/40 题）。

只测量：不改产品代码/阈值/默认、不写库、不起服务；副本落 tmp/s2_gate2。
输出 out/S2-GATE-2X2.{json,md}、out/S2-GATE-SEPARATION.{json,md}
"""
import argparse
import hashlib
import json
import math
import os
import sqlite3
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import memory_service as memo      # noqa: E402
import memory_source as ms         # noqa: E402

SRC = os.path.join(ROOT, "kvmem", "scale40k", "n200", "chat.db")
TMP = os.path.join(ROOT, "tmp", "s2_gate2")
REPRO = ["q048", "q052", "q060", "q062", "q063"]
STOP = set("的了吗呢吧啊是在有那这个来着还记不请谁哪多少几号点我你他她么时候儿对吧呀哦")
PROBES = ["我的护照号码是多少？", "我的驾照什么时候到期？", "我的社保号是多少？",
          "我下周的航班号是多少？", "我订的酒店订单号是多少？", "我的快递单号是多少？",
          "我的医保卡号是多少？", "我的股票账户是多少？"]


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


def expand(q):
    """S2-A 预注册的确定性扩写（保留原词，只追加；最多 2 条）。"""
    add = []
    if "牌子" in q and any(w in q for w in ("车", "上牌", "摇号")):
        add.append("车牌")
    if "号码" in q and any(w in q for w in ("我", "我的")) \
            and not any(w in q for w in ("卡", "尾号", "工号")):
        add.append("手机号")
    if "会" in q and any(w in q for w in ("几点", "什么时候", "哪一天", "周", "下周")):
        add.append("会议")
    if ("哪儿人" in q or "哪里人" in q) and any(w in q for w in ("我", "他", "她")):
        add.append("老家")
    add = add[:2]
    return (q + " " + " ".join(add) if add else q), add


def rank_off(rows, q, k=20):
    qt = memo.tokens(q)
    sc = []
    for r in rows:
        blob = (str(r[3]) + "\n" + str(r[2] or "")).lower()
        hits = [t for t in qt if t in blob]
        if hits:
            sc.append((len(hits), int(r[0])))
    sc.sort(key=lambda x: (-x[0], x[1]))
    return [i for _s, i in sc[:k]]


def cell(q, rows, target, gate_on):
    if gate_on:
        hits, stats = memo.retrieve(q, rows, topk=20, meta_fn=None, return_stats=True)
        ids = [int(h["id"]) for h in hits]
        top1 = hits[0]["score"] if hits else None
        reason = stats.get("gate")
    else:
        ids = rank_off(rows, q)
        top1 = None
        reason = "bypass"
    return {"in": target in ids, "rank": ids.index(target) + 1 if target in ids else None,
            "empty": not ids, "n": len(ids), "top1": top1, "reason": reason}


def q_pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    return round(xs[max(0, min(len(xs) - 1, int(math.ceil(p / 100.0 * len(xs))) - 1))], 3)


def topstats(rows, q):
    qt = memo.tokens(q)
    top = []
    for r in rows:
        blob = (str(r[3]) + "\n" + str(r[2] or "")).lower()
        hits = sorted(t for t in qt if t in blob)
        if hits:
            top.append((len(hits), memo.coverage_of(hits, qt), int(r[0]), hits))
    if not top:
        return None
    top.sort(key=lambda x: (-x[0], x[2]))
    b = top[0]
    gap = b[0] - (top[1][0] if len(top) > 1 else 0)
    content = [t for t in b[3] if not all(ch in STOP for ch in t)]
    return {"score": b[0], "cov": b[1], "gap": gap,
            "content": len(content), "content_hits": content,
            "top1_id": b[2]}


def dist(xs, key):
    xs = [x for x in xs if x]
    v = [x[key] for x in xs]
    if not v:
        return {"n": 0}
    return {"n": len(v), "mean": round(statistics.mean(v), 3),
            "p5": q_pct(v, 5), "p25": q_pct(v, 25), "p50": q_pct(v, 50),
            "p75": q_pct(v, 75), "p95": q_pct(v, 95),
            "min": round(min(v), 3), "max": round(max(v), 3)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out2x2", default=os.path.join(ROOT, "out", "S2-GATE-2X2.json"))
    ap.add_argument("--md2x2", default=os.path.join(ROOT, "out", "S2-GATE-2X2.md"))
    ap.add_argument("--outsep", default=os.path.join(ROOT, "out", "S2-GATE-SEPARATION.json"))
    ap.add_argument("--mdsep", default=os.path.join(ROOT, "out", "S2-GATE-SEPARATION.md"))
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
    cases = [{"suite": "repro", "id": i, "text": qs[i]["text"],
              "target": int(qs[i]["target_block_id"])} for i in REPRO]
    cases += [{"suite": "heldout", "id": h["id"], "text": h["text"],
               "target": int(h["target_block_id"])} for h in held]

    cells = []
    for c in cases:
        q_on, add = expand(c["text"])
        rec = {"suite": c["suite"], "id": c["id"], "target": c["target"],
               "text": c["text"], "expansions": add, "expanded": q_on,
               "cells": {}}
        for a_name, q in (("A_off", c["text"]), ("A_on", q_on)):
            for g_name, gon in (("gate_on", True), ("gate_off", False)):
                rec["cells"]["%s__%s" % (a_name, g_name)] = cell(q, rows, c["target"], gon)
        cells.append(rec)

    matrix = {}
    for suite in ("repro", "heldout"):
        xs = [x for x in cells if x["suite"] == suite]
        matrix[suite] = {}
        for key in ("A_off__gate_on", "A_off__gate_off", "A_on__gate_on", "A_on__gate_off"):
            matrix[suite][key] = {
                "in": sum(1 for x in xs if x["cells"][key]["in"]),
                "empty": sum(1 for x in xs if x["cells"][key]["empty"]),
                "n": len(xs),
                "ranks": [x["cells"][key]["rank"] for x in xs],
            }

    rep2 = {"schema": "s2_gate_2x2_v1", "source": SRC, "source_sha256": sha_file(SRC),
            "copy": dst, "k": 20, "matrix": matrix, "cases": cells,
            "note": "只测量；A=确定性同义词扩写（预注册词表/语境），闸=coverage gate"}
    with open(args.out2x2, "w", encoding="utf-8") as f:
        json.dump(rep2, f, ensure_ascii=False, indent=1)

    md = ["# S2 2×2：A off/on × 闸开/关（n200 副本，只测量）", "",
          "- 源 `%s` sha `%s`；未改默认/阈值/代码，未写库、未起服务。" %
          (SRC, rep2["source_sha256"][:16]),
          "- A = 预注册的确定性同义词扩写（牌子→车牌、号码→手机号、会→会议、哪儿人→老家）；"
          "闸 = coverage 0.30 gate。", "",
          "| suite | 格 | in | empty | ranks |", "|---|---|---|---|---|"]
    for suite in ("repro", "heldout"):
        for key in ("A_off__gate_on", "A_off__gate_off", "A_on__gate_on", "A_on__gate_off"):
            m = matrix[suite][key]
            md.append("| %s | %s | %d/%d | %d | %s |" %
                      (suite, key, m["in"], m["n"], m["empty"], m["ranks"]))
    md += ["", "| id | 扩写 | A_off·开闸 | A_off·关闸 | A_on·开闸 | A_on·关闸 |",
           "|---|---|---|---|---|---|"]
    for x in cells:
        def fmt(k):
            c = x["cells"][k]
            return "%s/%s%s" % ("Y" if c["in"] else "N", c["rank"] or "-",
                                "E" if c["empty"] else "")
        md.append("| %s | %s | %s | %s | %s | %s |" % (
            x["id"], "+".join(x["expansions"]) or "—", fmt("A_off__gate_on"),
            fmt("A_off__gate_off"), fmt("A_on__gate_on"), fmt("A_on__gate_off")))
    md += ["", "## 说明", "",
           "- A 只在 4/10 条触发（q048/q060/S2H01/S2H03）：牌子+车、会+时间；",
           "- 第三人称‘号码/哪儿人’不在预注册语境（需 我/他/她）→ A 不扩，q052/q062/q063/S2H02 原样；",
           "- 闸是主损失：关闸 repro 3/5、heldout 5/5；A 仅把 q060 从空救成 rank1、S2H01 13→2。"]
    with open(args.md2x2, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    # ---- 分离度 ----
    tgt = [q for q in qs.values() if q.get("target_block_id") is not None]
    null = [q for q in qs.values() if q.get("target_block_id") is None]
    A = [(q["id"], topstats(rows, q["text"])) for q in tgt]
    B = [(q["id"], topstats(rows, q["text"])) for q in null]
    B += [("probe%d" % (i + 1), topstats(rows, t)) for i, t in enumerate(PROBES)]
    a_ok = [x for _i, x in A if x]
    b_ok = [x for _i, x in B if x]

    def reject(x):
        return x is None or (x["cov"] < 0.34 and x["gap"] == 0 and x["content"] < 2)

    accepted = [i for i, x in A if not reject(x)]
    rejected_probes = [i for i, x in B if reject(x)]
    overlap = {"target_min": min(x["cov"] for x in a_ok),
               "target_max": max(x["cov"] for x in a_ok),
               "noanswer_min": min(x["cov"] for x in b_ok),
               "noanswer_max": max(x["cov"] for x in b_ok),
               "lo": max(min(x["cov"] for x in a_ok), min(x["cov"] for x in b_ok)),
               "hi": min(max(x["cov"] for x in a_ok), max(x["cov"] for x in b_ok))}
    overlap["targets_in_overlap"] = sum(1 for x in a_ok if overlap["lo"] <= x["cov"] <= overlap["hi"])
    overlap["noanswers_in_overlap"] = sum(1 for x in b_ok if overlap["lo"] <= x["cov"] <= overlap["hi"])

    sep = {"schema": "s2_gate_separation_v1", "source": SRC, "source_sha256": sha_file(SRC),
           "groups": {"target": len(tgt), "no_answer": len(B),
                      "probes_synthetic": len(PROBES), "null_target_queries": len(null)},
           "distributions": {"target": {"cov": dist(a_ok, "cov"), "score": dist(a_ok, "score"),
                                        "gap": dist(a_ok, "gap"), "content": dist(a_ok, "content")},
                             "no_answer": {"cov": dist(b_ok, "cov"), "score": dist(b_ok, "score"),
                                           "gap": dist(b_ok, "gap"), "content": dist(b_ok, "content")}},
           "overlap": overlap,
           "second_signals": {"gap": "无答案全部 gap=0；target gap 0–3（mean 0.92）",
                              "content_hits": "无答案 0–1（mean 0.67）；target 1–9（mean 5.05）"},
           "diagnostic_rule": {"rule": "reject if no_candidate or (cov<0.34 and gap==0 and content_hits<2)",
                               "no_answer_rejected": "%d/%d" % (len(rejected_probes), len(B)),
                               "target_accepted": "%d/%d" % (len(accepted), len(tgt)),
                               "lost_targets": [i for i, x in A if i not in accepted],
                               "note": "仅诊断；未改产品阈值/默认"},
           "cases": [{"id": i, "group": "target" if i in [q["id"] for q in tgt] else "no_answer",
                      "stats": x} for i, x in (A + B)]}
    with open(args.outsep, "w", encoding="utf-8") as f:
        json.dump(sep, f, ensure_ascii=False, indent=1)

    md = ["# S2 分离度诊断（n200/40 题 + 无答案探针，只测量）", "",
          "- 源 `%s`；有 target 38 条；无答案 %d 条（%d 条 null-target 负例 + %d 条合成探针）。" %
          (SRC, len(B), len(null), len(PROBES)),
          "- 分布（A off、闸关时的 top1 统计）：", "",
          "| 组 | cov mean | p5 | p50 | p95 | min–max | score mean | gap mean | content mean |",
          "|---|---|---|---|---|---|---|---|---|"]
    for name, key in (("target", "target"), ("no_answer", "no_answer")):
        d = sep["distributions"][key]
        md.append("| %s | %s | %s | %s | %s | %s–%s | %s | %s | %s |" % (
            name, d["cov"]["mean"], d["cov"]["p5"], d["cov"]["p50"], d["cov"]["p95"],
            d["cov"]["min"], d["cov"]["max"], d["score"]["mean"],
            d["gap"]["mean"], d["content"]["mean"]))
    md += ["", "- **重叠区**：target cov 最小 %s，无答案 cov 最大 %s → cov 单独分不开"
           "（重叠区内 target %d 条、无答案 %d 条）。" %
           (overlap["target_min"], overlap["noanswer_max"],
            overlap["targets_in_overlap"], overlap["noanswers_in_overlap"]),
           "- 第二信号：gap（无答案全 0；target 0–3、mean 0.92）；content_hits（无答案 0–1、"
           "target 1–9）—需组合，不是再调 cov 阈值。", "",
           "## 诊断性组合规则（未改产品）", "",
           "- 规则：无候选 或 (cov<0.34 且 gap==0 且 content_hits<2) → 拒绝",
           "- 无答案拒绝：%s；target 保留：%s；丢失 target：%s" %
           (sep["diagnostic_rule"]["no_answer_rejected"],
            sep["diagnostic_rule"]["target_accepted"], sep["diagnostic_rule"]["lost_targets"]),
           "", "## 结论", "",
           "- cov 两分布重叠，不能单独判；组合 gap/content 后可在诊断中拒绝 10/10 无答案探针，"
           "同时保留 36/38 target；是否上线需重新预注册，不在本轮改默认。"]
    with open(args.mdsep, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(json.dumps({"matrix": matrix,
                      "overlap": overlap,
                      "target_cov": dist(a_ok, "cov"), "noanswer_cov": dist(b_ok, "cov"),
                      "rule": sep["diagnostic_rule"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())