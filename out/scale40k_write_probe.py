# -*- coding: utf-8 -*-
"""n200 满库写入探针：第 201 条 /remember 必须返回结构化 memory_full（409），
且随后 /ask 与 /health 不受污染。只读查询 + 一次被拒写入。

输出 dst/WRITE-PROBE-n200.json
"""
import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _req(url, body=None, timeout=180):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="GET" if body is None else "POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r), (time.perf_counter() - t0) * 1000.0
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            obj = json.loads(raw.decode("utf-8") or "{}")
        except Exception:                                # noqa: BLE001
            obj = {"raw": raw.decode("utf-8", "replace")[:300]}
        return e.code, obj, (time.perf_counter() - t0) * 1000.0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dst", default=os.path.join(ROOT, "kvmem", "scale40k", "n200"))
    ap.add_argument("--endpoint", default="http://127.0.0.1:8765")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    ep = args.endpoint.rstrip("/")
    dst = os.path.abspath(args.dst)
    outpath = args.out or os.path.join(dst, "WRITE-PROBE-n200.json")

    qs = [json.loads(l) for l in open(os.path.join(dst, "queries.jsonl"), encoding="utf-8")
          if l.strip()]
    probe_q = next((q for q in qs if q.get("reverse_chain")), None) or qs[0]
    text = "体检写入：我的工号是 QA-20261030，仅用于满库拒绝测试。"
    rows_before = sqlite3.connect(os.path.join(dst, "chat.db")).execute(
        "SELECT COUNT(*) FROM memory_source").fetchone()[0]

    h_before, health0, _ = _req(ep + "/health")
    a0_code, a0, a0_ms = _req(ep + "/ask", {"text": probe_q["text"]})
    code, body, write_ms = _req(ep + "/remember", {"text": text})
    h_after, health1, _ = _req(ep + "/health")
    a1_code, a1, a1_ms = _req(ep + "/ask", {"text": probe_q["text"]})
    rows_after = sqlite3.connect(os.path.join(dst, "chat.db")).execute(
        "SELECT COUNT(*) FROM memory_source").fetchone()[0]

    err = (body or {}).get("error") or {}
    checks = {
        "http_409": code == 409,
        "code_memory_full": err.get("code") == "memory_full",
        "not_500": code != 500,
        "rows_unchanged": rows_before == rows_after == 200,
        "health_memories_unchanged": (health1 or {}).get("memories") == (health0 or {}).get("memories"),
        "ask_after_ok": a1_code == 200 and bool(a1.get("block_ids")) and bool(a1.get("answer")),
        "ask_answer_same": (a1.get("answer") == a0.get("answer")),
        "ask_blocks_same": (a1.get("block_ids") == a0.get("block_ids")),
    }
    out = {
        "schema": "scale40k_write_probe_v1",
        "dst": dst,
        "endpoint": ep,
        "text": text,
        "before": {"health_http": h_before, "memories": (health0 or {}).get("memories"),
                   "rows": rows_before,
                   "ask": {"http": a0_code, "answer": a0.get("answer"),
                           "state": a0.get("state"), "block_ids": a0.get("block_ids"),
                           "latency_ms": round(a0_ms, 1)}},
        "write": {"http": code, "body": body, "latency_ms": round(write_ms, 1)},
        "after": {"health_http": h_after, "memories": (health1 or {}).get("memories"),
                  "rows": rows_after,
                  "ask": {"http": a1_code, "answer": a1.get("answer"),
                          "state": a1.get("state"), "block_ids": a1.get("block_ids"),
                          "latency_ms": round(a1_ms, 1)}},
        "checks": checks,
        "ok": all(checks.values()),
    }
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"ok": out["ok"], "checks": checks,
                      "write_http": code, "write_body": body,
                      "memories": [out["before"]["memories"], out["after"]["memories"]]},
                     ensure_ascii=False, indent=1))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())