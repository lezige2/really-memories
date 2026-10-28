#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""长上下文压测的独立行为/上下文正确性复核。

输入：out/LONG-CONV-TEST.json（tmp/long_conv_test.py 产物）、
      kvmem/daily/service_eval3.log（服务访问日志）、
      kvmem/daily/{sessions,blocks,assistant}/（归档块/摘要/会话残留）。
检查：1) rollover 只压旧段、最近对话保留；2) 压缩后无政策复读/身份混乱/答非所问；
      3) 早期事实（阿泽/京A88888/成都/豆豆）经归档块+摘要召回而非丢失；
      4) 无 500/卡死/延迟异常。
输出：out/LONG-CONV-VERIFY.json（含逐项 pass/fail、证据、复现步骤）。
只写该产物；不跑 GPU、不改代码。
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "out"
TEST = OUT / "LONG-CONV-TEST.json"
LOG = ROOT / "kvmem" / "daily" / "service_eval3.log"
ART = OUT / "LONG-CONV-VERIFY.json"
DAILY = ROOT / "kvmem" / "daily"
EP = "http://127.0.0.1:8765"

POLICY_MARKERS = ("你是用户的本地记忆助手", "规则：", "不要输出思考过程",
                  "只依据记忆回答", "SYSTEM_POLICY", "只输出一行回答",
                  "若有多条相似记忆", "用户：", "回答：")
BRANDS = ("DeepSeek", "deepseek", "Qwen", "qwen", "GPT", "gpt", "通义",
          "ChatGLM", "Llama", "llama", "R1")
FACTS = [
    {"name": "阿泽", "probe": "我叫什么名字？", "tokens": ["阿泽"]},
    {"name": "京A88888", "probe": "我的车牌号是多少？", "tokens": ["京A88888"]},
    {"name": "成都", "probe": "我下周五要去哪开会？", "tokens": ["成都"]},
    {"name": "豆豆", "probe": "我养的猫叫什么名字？", "tokens": ["豆豆"]},
]
RECENT_MARKERS = ("工作", "周末", "资料", "计划", "安排", "休息", "转转",
                  "聊聊", "聊天")


def sha256(p):
    return __import__("hashlib").sha256(Path(p).read_bytes()).hexdigest()


def http_json(path, payload=None, timeout=120):
    url = EP + path
    if payload is None:
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(
            url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def scan_log():
    if not LOG.exists():
        return {"present": False}
    text = LOG.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    n_ask = sum(1 for ln in lines if "POST /ask" in ln)
    n_500 = sum(1 for ln in lines if re.search(r'"?\s500\s', ln))
    n_reset = sum(1 for ln in lines if "POST /reset" in ln)
    errs = [ln for ln in lines if re.search(r"Traceback|timeout|Exception|error", ln, re.I)]
    return {"present": True, "sha256": sha256(LOG), "bytes": len(text.encode("utf-8")),
            "n_lines": len(lines), "n_ask": n_ask, "n_500": n_500,
            "n_reset": n_reset, "n_error_lines": len(errs),
            "error_samples": errs[:10], "tail": lines[-5:]}


def grep_tree(sub, needle):
    hits = []
    base = DAILY / sub
    if not base.exists():
        return hits
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        try:
            if p.stat().st_size > 5 * 1024 * 1024:
                continue
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:            # noqa: BLE001
            continue
        if needle in txt:
            hits.append(str(p.relative_to(ROOT)).replace("\\", "/"))
    return hits


def main():
    if not TEST.exists():
        print(json.dumps({"status": "pending", "reason": "LONG-CONV-TEST.json missing"},
                         ensure_ascii=False))
        return 4
    doc = json.loads(TEST.read_text(encoding="utf-8"))
    log = scan_log()
    checks = []

    # ---------- 1) rollover 只压旧段 + 最近对话保留 --------------------
    rovs = doc.get("rollovers") or []
    rollover_detail = []
    prev_tokens = None
    drops = []
    for r in rovs:
        ov = r.get("rollover") or {}
        before = ov.get("before_tokens")
        after = ov.get("after_tokens")
        kept = ov.get("kept_turns")
        dropped = ov.get("dropped_turns")
        cur = r.get("tokens")
        rollover_detail.append({"turn": r.get("turn"), "tokens_now": cur,
                                "before": before, "after": after,
                                "kept_turns": kept, "dropped_turns": dropped,
                                "summary_id": ov.get("summary_id"),
                                "fallback": ov.get("fallback")})
        if isinstance(before, int) and isinstance(after, int):
            drops.append(after < before)
        elif isinstance(cur, int) and prev_tokens is not None:
            drops.append(cur < prev_tokens)
        if isinstance(cur, int):
            prev_tokens = cur
    rollover_ok = bool(rovs) and all(drops) if drops else bool(rovs)
    recent_ok = False
    recent_ans = ""
    if "recent" not in {c["name"] for c in checks}:
        pass
    checks.append({"name": "rollover occurred", "pass": bool(rovs),
                   "detail": {"n_rollovers": len(rovs), "rows": rollover_detail}})
    checks.append({"name": "rollover shrinks old segment only (tokens drop)",
                   "pass": bool(rollover_ok),
                   "detail": {"drops": drops}})

    # 最近对话保留：用压测自带 probe + 独立复查
    probes = {p.get("q"): p for p in (doc.get("probes") or [])}
    recent_probe = probes.get("最近在聊什么？") or {}
    recent_ans = str(recent_probe.get("answer") or "")
    recent_ok = any(k in recent_ans for k in RECENT_MARKERS) or \
        (bool(recent_probe.get("blocks")) and not recent_probe.get("pass") is False)
    checks.append({"name": "recent dialogue retained after rollover",
                   "pass": bool(recent_ok),
                   "detail": {"probe": "最近在聊什么？", "answer": recent_ans[:200],
                              "markers_hit": [k for k in RECENT_MARKERS
                                              if k in recent_ans],
                              "state": recent_probe.get("state"),
                              "blocks": recent_probe.get("blocks")}})

    # ---------- 2) 政策复读 / 身份混乱 / 答非所问 ----------------------
    policy_hits, brand_hits, echo_hits, empty_hits = [], [], [], []
    for q, p in probes.items():
        a = str(p.get("answer") or "")
        if not a.strip():
            empty_hits.append(q)
        for m in POLICY_MARKERS:
            if m in a:
                policy_hits.append({"q": q, "marker": m, "answer": a[:120]})
        for b in BRANDS:
            if b in a:
                brand_hits.append({"q": q, "brand": b, "answer": a[:120]})
        if a.strip() and (a.strip().rstrip("。！？?") ==
                          q.strip().rstrip("。！？?")):
            echo_hits.append({"q": q, "answer": a[:120]})
    checks.append({"name": "no policy recycling", "pass": not policy_hits,
                   "detail": {"hits": policy_hits}})
    checks.append({"name": "no identity/model-brand confusion", "pass": not brand_hits,
                   "detail": {"hits": brand_hits}})
    checks.append({"name": "no question echo / empty answers",
                   "pass": not echo_hits and not empty_hits,
                   "detail": {"echo": echo_hits, "empty": empty_hits}})
    off_topic = []
    for q, p in probes.items():
        if q in ("我们最开始聊了什么？", "最近在聊什么？",
                 "你现在记得几条长期记忆？"):
            continue
        a = str(p.get("answer") or "")
        expect = next((f["tokens"] for f in FACTS if f["probe"] == q), None)
        if expect and not any(w in a for w in expect):
            off_topic.append({"q": q, "answer": a[:160], "expect": expect})
    checks.append({"name": "fact probes answered correctly (not off-topic)",
                   "pass": not off_topic, "detail": {"fails": off_topic}})

    # ---------- 3) 早期事实召回（probe + 归档/摘要/块证据） -------------
    fact_rows = []
    for f in FACTS:
        p = probes.get(f["probe"]) or {}
        a = str(p.get("answer") or "")
        probe_ok = any(w in a for w in f["tokens"])
        archive = grep_tree("sessions", f["name"])
        blocks = grep_tree("blocks", f["name"])
        assistant = grep_tree("assistant", f["name"])
        fact_rows.append({"fact": f["name"], "probe": f["probe"],
                          "probe_pass": probe_ok, "answer": a[:160],
                          "state": p.get("state"), "blocks": p.get("blocks"),
                          "found_in_sessions": archive,
                          "found_in_blocks": blocks,
                          "found_in_assistant": assistant,
                          "retained": bool(probe_ok or archive or blocks
                                           or assistant)})
    checks.append({"name": "early facts recalled (probe or archive/summary)",
                   "pass": all(r["probe_pass"] for r in fact_rows),
                   "detail": {"facts": fact_rows,
                              "n_probe_pass": sum(1 for r in fact_rows
                                                  if r["probe_pass"])}})

    # ---------- 4) 500 / 卡死 / 延迟 ----------------------------------
    err_ok = log.get("n_500", 0) == 0 and log.get("n_error_lines", 0) == 0
    checks.append({"name": "no 500 / traceback / timeout in service log",
                   "pass": bool(err_ok), "detail": log})

    latency = []
    try:
        for q in ("现在方便吗？", "我叫什么名字？"):
            t0 = time.perf_counter()
            st, d = http_json("/ask", {"text": q}, timeout=120)
            latency.append({"q": q, "http": st,
                            "latency_s": round(time.perf_counter() - t0, 3),
                            "answer": str(d.get("answer") or "")[:120]})
    except Exception as exc:         # noqa: BLE001
        latency.append({"error": "%s: %s" % (type(exc).__name__, exc)})
    lat_ok = bool(latency) and all(isinstance(x.get("latency_s"), (int, float))
                                   and x["latency_s"] < 90 for x in latency)
    checks.append({"name": "post-test latency < 90s (no hang)",
                   "pass": bool(lat_ok) and doc.get("turns", 0) > 0,
                   "detail": {"probes": latency, "turns": doc.get("turns")}})

    fails = [c for c in checks if not c["pass"]]
    repro = []
    for c in fails:
        if c["name"] == "early facts recalled (probe or archive/summary)":
            repro.append("python -X utf8 tmp/long_conv_test.py（重跑压测）后，"
                         "对每个未召回事实 POST /ask 对应问句；对照 out/LONG-CONV-TEST.json.probes")
        elif "recent" in c["name"]:
            repro.append("压测后 POST /ask {\"text\":\"最近在聊什么？\"}，"
                         "检查答案是否含近段关键词（工作/周末/资料/计划）")
        elif "rollover" in c["name"]:
            repro.append("观察 out/LONG-CONV-TEST.json.rollovers 的 before/after_tokens；"
                         "若 after>=before，说明只压旧段逻辑失效")
        else:
            repro.append("按 %s 的 detail 复现；服务日志 %s"
                         % (c["name"], str(LOG.relative_to(ROOT)).replace("\\", "/")))
    art = {
        "schema": "long_conv_verify_v1",
        "role": "长上下文压测（4 万字符）行为/上下文正确性独立复核",
        "inputs": {"test": {"path": "out/LONG-CONV-TEST.json",
                            "sha256": sha256(TEST), "bytes": TEST.stat().st_size,
                            "turns": doc.get("turns"),
                            "chars": doc.get("chars"),
                            "tokens_now": doc.get("tokens_now")},
                   "service_log": log,
                   "probes_in_test": len(probes)},
        "checks": checks,
        "summary": {"n": len(checks),
                    "pass": sum(1 for c in checks if c["pass"]),
                    "fail": len(fails),
                    "failed": [c["name"] for c in fails]},
        "repro_steps": repro or ["无失败项；如需复跑：python -X utf8 tmp/long_conv_test.py"],
        "pass": not fails,
        "notes": ["本件复核行为/上下文正确性；滚动压缩的 token 曲线以 test 件 rollovers 为准。",
                  "身份检查允许『本地 14B 模型』式自述，禁止具体模型品牌。",
                  "facts 同时查 probe 答案与 sessions/blocks/assistant 归档残留。",
                  "未跑 GPU、未改代码；只写本产物。"],
    }
    ART.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(ART) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, ART)
    print(json.dumps({"artifact": str(ART), "sha256": sha256(ART),
                      "bytes": ART.stat().st_size,
                      "summary": art["summary"],
                      "pass": art["pass"],
                      "repro": art["repro_steps"]}, ensure_ascii=False,
                     indent=1))
    return 0 if art["pass"] else 3


if __name__ == "__main__":
    sys.exit(main())