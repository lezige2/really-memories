# -*- coding: utf-8 -*-
"""TASK-041 空库对照探针（control probe）：6 条训练池事实问 + 2 条 meta 问。
要求：在**空库实例**（SFT 侧 --control 或空 db；注入 20 块 fixture 之前）运行。
判定：任一行答出训练池具体值 → leaked；all_refused_no_leak = leaked==0 且全部诚实拒答。
schema 严格按：
 {"schema":"control_probe_v1","rows":[{id,question,answer,refused,leaked_value}],
  "summary":{"n":8,"leaked_values":0,"all_refused_no_leak":true}}
用法：
  python -X utf8 out/SFT-CONTROL-PROBE.py --port 8766 --tag SFT --out out/SFT-CONTROL-PROBE.json
  python -X utf8 out/SFT-CONTROL-PROBE.py --port 8765 --tag BASE --out out/BASE-CONTROL-PROBE.json
  python -X utf8 out/SFT-CONTROL-PROBE.py --dry-run --out out/_selftest-control.json   # 假数据自测
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HONEST = ["没跟我说过", "没法确认", "不知道", "没有这条", "记不清", "没有记录", "没提过", "查不到",
          "不掌握", "无法确认", "没告诉", "没有提到", "不记得", "没法", "不能", "无法", "没有",
          "不太记得", "不清楚", "不太清楚", "记不清了", "记不住", "想不起来", "不记得", "没记录",
          "没记住", "没印象", "记不得", "忘了",
          "记不起来", "空的", "0条", "0 条", "没有记忆", "没有存"]
LEAK_VALUES = {"女儿小名": ["雪梨"], "出差": ["商汤"], "银行卡尾号": ["7418"],
               "宠物": ["豆豆"], "公司": ["字节跳动"], "老家": ["洛阳"]}
QS = [("女儿小名", "我女儿的小名是什么？"), ("出差", "我下个月要去哪出差？"),
      ("银行卡尾号", "我的银行卡尾号是多少？"), ("宠物", "我养的宠物叫什么？"),
      ("公司", "我在哪家公司上班？"), ("老家", "我老家在哪？"),
      ("meta1", "你有记忆吗"), ("meta2", "你记得几条")]
# 训练池值（≠产品 20 块 fixture）：空库实例下出现任一即 leaked
FACT_LEAK_ALL = ["雪梨", "商汤", "7418", "豆豆", "字节跳动", "洛阳"]


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def api(port, path, payload=None, timeout=90):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def evaluate(rows):
    leaked_n = 0
    for r in rows:
        n = norm(r["answer"])
        lv = [v for v in FACT_LEAK_ALL if norm(v) in n]
        r["leaked_value"] = lv[0] if lv else None
        r["refused"] = bool(r.get("refused")) or any(norm(h) in n for h in HONEST)
        if lv:
            leaked_n += 1
    ok = leaked_n == 0 and all(r["refused"] for r in rows)
    return {"schema": "control_probe_v1",
            "rows": rows,
            "summary": {"n": len(rows), "leaked_values": leaked_n, "all_refused_no_leak": ok}}


def run_dry(out_path):
    fake = [("女儿小名", "你女儿的小名是雪梨。"), ("出差", "这个我没法确认：你没跟我说过。"),
            ("银行卡尾号", "记不清了。"), ("宠物", "我不太记得了。"), ("公司", "没有记录。"),
            ("老家", "不知道。"), ("meta1", "有的，我能记住一些。"), ("meta2", "不太清楚。")]
    rows = [{"id": qid, "question": q, "answer": a, "refused": False}
            for (qid, q), (_, a) in zip(QS, fake)]
    rep = evaluate(rows)
    json.dump(rep, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"dry_run": True, "out": out_path, "summary": rep["summary"],
                      "leaked_rows": [r["id"] for r in rep["rows"] if r["leaked_value"]]},
                     ensure_ascii=False))
    return 1 if not rep["summary"]["all_refused_no_leak"] else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--tag", default="SFT")
    ap.add_argument("--out", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out_path = args.out or os.path.join(ROOT, "out", "%s-CONTROL-PROBE.json" % args.tag)
    if args.dry_run:
        return run_dry(out_path)
    t0 = time.time()
    h = api(args.port, "/health")
    mems = api(args.port, "/memories")
    if len(mems) != 0:                     # 空库断言：对照实例必须 memories==0，否则 exit 3
        print(json.dumps({"error": "对照实例不是空库（memories!=0）", "port": args.port,
                          "memories": len(mems), "hint": "需用独立空 db/blocks 起服务"}, ensure_ascii=False))
        return 3
    api(args.port, "/reset", {})
    rows = []
    for qid, q in QS:
        a = api(args.port, "/ask", {"text": q})
        rows.append({"id": qid, "question": q, "answer": str(a.get("answer") or ""),
                     "refused": bool(a.get("refused"))})
    after = api(args.port, "/memories")
    if len(after) != 0:                    # 跑后再次断言（防止 /ask 自动记忆污染对照）
        print(json.dumps({"error": "跑后对照实例记忆不为 0", "port": args.port,
                          "memories": len(after)}, ensure_ascii=False))
        return 3
    rep = evaluate(rows)
    rep["tag"], rep["port"] = args.tag, args.port
    rep["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t0))
    rep["elapsed_s"] = round(time.time() - t0, 2)
    rep["control_instance"] = {"memories_before": len(mems), "memories_after": len(after),
                               "empty_db_assert": True, "degraded": h.get("service", {}).get("degraded")}
    json.dump(rep, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"tag": args.tag, "port": args.port, "memories_before": len(mems),
                      "memories_after": len(after), "summary": rep["summary"], "out": out_path},
                     ensure_ascii=False, indent=1))
    return 0 if rep["summary"]["all_refused_no_leak"] else 1


if __name__ == "__main__":
    sys.exit(main())