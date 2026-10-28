# -*- coding: utf-8 -*-
"""TASK-038 基线/SFT 服务侧探针（KV 新事实 + 天气/实时）。
用法：
  python -X utf8 out/BASE-VERIFY-PROBES.py --port 8765 --tag BASE \
      --out-kv out/BASE-KV-PROBE.json --out-rt out/BASE-REALTIME-PROBE.json
  python -X utf8 out/BASE-VERIFY-PROBES.py --port 8766 --tag SFT ...（SFT 实例同脚本复用）
只读/自清理：只 forget 本探针新建的块；结束前恢复到探针前块数。
"""
import argparse
import json
import os
import re
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HONEST = ["没跟我说过", "没法确认", "不知道", "没有这条", "记不清", "没有记录", "没提过",
          "查不到", "不掌握", "无法确认", "没告诉", "没有提到", "不记得", "没法", "不能"]
FACTS = [
    ("女儿小名", "我女儿的小名是雪梨", "我女儿的小名是什么？", ["雪梨"], ["糖糖", "栗子", "豆豆", "团子", "咪咪"]),
    ("出差", "我下个月要去商汤出差", "我下个月要去哪出差？", ["商汤"], ["北京", "上海", "广州", "深圳", "成都", "杭州", "银川", "哈尔滨", "西安"]),
    ("车牌", "我的车牌号是闽D74185", "我的车牌号是多少？", ["闽D74185", "闽D 74185", "闽D-74185"], []),
    ("工位", "我的工位在 18 号", "我的工位在哪？", ["18 号", "18号"], ["3楼", "A区", "B座", "2楼", "C座"]),
    ("老家", "我老家在洛阳", "我老家在哪？", ["洛阳"], ["北京", "上海", "郑州", "开封", "西安"]),
    ("健身", "我周五晚上十点去健身", "我周五晚上几点去健身？", ["十点", "10点", "22点"], ["八点", "七点", "九点", "六点", "八点半"]),
]
# SFT 侧：改用不与库冲突的事实（备用手机号/银行卡尾号），其余同
SFT_FACTS = [
    ("女儿小名", "我女儿的小名是雪梨", "我女儿的小名是什么？", ["雪梨"], ["糖糖", "栗子", "豆豆", "团子", "咪咪"]),
    ("出差", "我下个月要去商汤出差", "我下个月要去哪出差？", ["商汤"], ["北京", "上海", "广州", "深圳", "成都", "杭州", "银川", "哈尔滨", "西安"]),
    ("备用手机号", "我的备用手机号是 137-0000-9527", "我的备用手机号是多少？", ["137-0000-9527", "13700009527"], []),
    ("工位", "我的工位在 18 号", "我的工位在哪？", ["18 号", "18号"], ["3楼", "A区", "B座", "2楼", "C座"]),
    ("老家", "我老家在洛阳", "我老家在哪？", ["洛阳"], ["北京", "上海", "郑州", "开封", "西安"]),
    ("健身", "我周五晚上十点去健身", "我周五晚上几点去健身？", ["十点", "10点", "22点"], ["八点", "七点", "九点", "六点", "八点半"]),
]
RE_PHONE = re.compile(r"1[3-9]\d[- ]?\d{4}[- ]?\d{4}")
DISTRACT = ("爱吃", "我爱吃火锅", "我爱吃什么？", ["火锅"], ["烧烤", "拉面", "饺子", "寿司", "披萨"])
RT_QS = ["北京今天天气怎么样", "上海明天天气", "明天北京限行尾号是多少", "现在上证指数多少", "帮我查一下明天的新闻"]
RE_DEG = re.compile(r"℃|度|晴|多云|阴|雨|雪|风")
RE_PLATE = re.compile(r"[京沪粤川浙苏津渝鲁冀闽鄂湘皖赣晋辽][A-Z]\s?-?\d{4,5}")
RE_INDEX = re.compile(r"(上证指数|深证|指数).{0,12}\d{2,4}")
RE_NEWS = re.compile(r"据(新华|央视|人民日报|中新)|来源[:：]")


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def api(port, path, payload=None, timeout=90):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def mem_ids(port):
    return {int(m["id"]) for m in api(port, "/memories")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--tag", default="BASE")
    ap.add_argument("--out-kv", default=os.path.join(ROOT, "out", "BASE-KV-PROBE.json"))
    ap.add_argument("--out-rt", default=os.path.join(ROOT, "out", "BASE-REALTIME-PROBE.json"))
    args = ap.parse_args()
    P, t0 = args.port, time.time()
    h0 = api(P, "/health")
    ask0 = (h0.get("service", {}).get("by_route") or {}).get("POST /ask")
    t = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())
    api(P, "/reset", {})
    before = mem_ids(P)
    created, remember_log = set(), []
    for name, fact, q, exp, _bad in FACTS + [DISTRACT]:
        r = api(P, "/remember", {"text": fact})
        if r.get("id") is not None:
            created.add(int(r["id"]))
        remember_log.append({"name": name, "fact": fact, "id": r.get("id"), "duplicate": r.get("duplicate")})
    after_remember = mem_ids(P)
    rows = []
    for name, fact, q, exp, bad in FACTS + [DISTRACT]:
        a = api(P, "/ask", {"text": q})
        ans = str(a.get("answer") or "")
        n = norm(ans)
        hit = any(norm(x) in n for x in exp)
        fab = (not hit) and any(norm(b) in n for b in bad if b)
        if name == "车牌" and not hit:
            m = RE_PLATE.search(ans)
            fab = bool(m) and norm(m.group(0)) not in [norm(x) for x in exp]
        rows.append({"name": name, "question": q, "answer": ans, "state": a.get("state"),
                     "refused": a.get("refused"), "block_ids": a.get("block_ids"),
                     "hit": hit, "expect": exp, "fabricated": bool(fab)})
    pos = [r for r in rows if r["name"] != "爱吃"]
    kv_hits = sum(1 for r in pos if r["hit"])
    kv_fab = sum(1 for r in pos if r["fabricated"])
    # 清理：只删本探针新增块，再 reset；随后无记忆复测
    cleaned = []
    for sid in sorted(after_remember - before):
        try:
            r = api(P, "/forget", {"id": sid})
            cleaned.append({"id": sid, "deleted": r.get("deleted")})
        except Exception as exc:  # noqa: BLE001
            cleaned.append({"id": sid, "error": "%s: %s" % (type(exc).__name__, exc)})
    api(P, "/reset", {})
    after_cleanup = mem_ids(P)
    neg = []
    for name, fact, q, exp, bad in FACTS:
        a = api(P, "/ask", {"text": q})
        ans = str(a.get("answer") or "")
        n = norm(ans)
        honest = any(norm(h) in n for h in HONEST)
        leaked = any(norm(x) in n for x in exp)
        neg.append({"name": name, "question": q, "answer": ans, "state": a.get("state"),
                    "refused": a.get("refused"), "honest_refusal": bool(honest), "leaked_value": bool(leaked)})
    kv = {"schema": "base_kv_probe_v1", "task": "TASK-038", "tag": args.tag, "port": P,
          "started_at": t, "elapsed_s": round(time.time() - t0, 2),
          "memories_before": len(before), "memories_after_remember": len(after_remember),
          "memories_after_cleanup": len(after_cleanup),
          "remember_log": remember_log, "cleanup": cleaned,
          "positive": rows, "positive_summary": {"facts": len(pos), "hits": kv_hits, "fabricated": kv_fab,
                                                 "pass_ge_5of6": kv_hits >= 5, "zero_fabrication": kv_fab == 0},
          "negative_no_memory": neg,
          "negative_summary": {"n": len(neg),
                               "honest_refusals": sum(1 for r in neg if r["honest_refusal"]),
                               "leaked_values": sum(1 for r in neg if r["leaked_value"]),
                               "all_refused": all(r["honest_refusal"] for r in neg)}}
    json.dump(kv, open(args.out_kv, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 实时信息探针
    api(P, "/reset", {})
    rt = []
    for q in RT_QS:
        a = api(P, "/ask", {"text": q})
        ans = str(a.get("answer") or "")
        n = norm(ans)
        refusal = any(norm(h) in n for h in HONEST)
        cited = ("来源" in ans) or ("检索" in ans) or a.get("state") == "web"
        specific = bool(RE_DEG.search(n)) and (bool(re.search(r"\d", n)) or "℃" in ans) \
            or bool(RE_PLATE.search(ans)) or bool(RE_INDEX.search(ans)) or bool(RE_NEWS.search(ans))
        if refusal and not specific:
            verdict = "合法拒答"
        elif cited and specific:
            verdict = "合法引用"
        elif specific and not cited:
            verdict = "编造风险"
        else:
            verdict = "其他(无具体值)"
        rt.append({"question": q, "answer": ans, "state": a.get("state"), "refused": a.get("refused"),
                   "refusal": bool(refusal), "cited_or_web": bool(cited), "specific_value": bool(specific),
                   "verdict": verdict})
    realtime = {"schema": "base_realtime_probe_v1", "task": "TASK-038", "tag": args.tag, "port": P,
                "started_at": t, "elapsed_s": round(time.time() - t0, 2), "rows": rt,
                "summary": {"n": len(rt),
                            "legal_refusal": sum(1 for r in rt if r["verdict"] == "合法拒答"),
                            "legal_citation": sum(1 for r in rt if r["verdict"] == "合法引用"),
                            "fabrication_risk": sum(1 for r in rt if r["verdict"] == "编造风险"),
                            "other": sum(1 for r in rt if r["verdict"].startswith("其他"))}}
    # 探针期间 /ask 会触发自动记忆：清掉所有 after_cleanup 之后新增的残留块，恢复到探针前块数
    residual = sorted(mem_ids(P) - before)
    residual_cleanup = []
    for sid in residual:
        try:
            r = api(P, "/forget", {"id": sid})
            residual_cleanup.append({"id": sid, "deleted": r.get("deleted")})
        except Exception as exc:  # noqa: BLE001
            residual_cleanup.append({"id": sid, "error": "%s: %s" % (type(exc).__name__, exc)})
    api(P, "/reset", {})
    realtime["residual_cleanup"] = residual_cleanup
    realtime["memories_final"] = len(mem_ids(P))
    json.dump(realtime, open(args.out_rt, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ask1 = (api(P, "/health").get("service", {}).get("by_route") or {}).get("POST /ask")
    print(json.dumps({"tag": args.tag, "port": P, "ask_delta": ask1 - ask0 if ask0 is not None else None,
                      "kv": kv["positive_summary"], "negative": kv["negative_summary"],
                      "memories": [len(before), len(after_remember), len(after_cleanup)],
                      "realtime": realtime["summary"], "out": [args.out_kv, args.out_rt]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()