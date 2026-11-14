# -*- coding: utf-8 -*-
"""scale40k 子库评测：POST /ask → recall@k / 答案 pass / 旧值泄漏 / 拒答 / P50-P95。

只读 dst/queries.jsonl，写 dst/RESULT.json；不动产品代码、不建块、不调模型
（模型只由 8765 服务加载）。--check 完全离线，只校验 queries.jsonl 结构。

用法：
  python -X utf8 out/scale40k_run.py --dst kvmem/scale40k/n20 --check
  python -X utf8 out/scale40k_run.py --dst kvmem/scale40k/n20 --endpoint http://127.0.0.1:8765
"""
import argparse
import json
import math
import os
import re
import sys
import time
import sqlite3
import unicodedata
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFUSAL_MARKERS = ("不知道", "没有记录", "没记录", "不清楚", "没提过", "无法确定",
                   "记不清", "没有相关", "查不到", "没有找到", "无法回答", "没有这",
                   "不知道你", "抱歉", "未提及", "无相关信息")
STRIP_CHARS = "·-—–_.。,，、"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 文本归一（同值不同写法：空格/·/标点）
# ---------------------------------------------------------------------------
def compact(s):
    return "".join(ch for ch in str(s or "")
                   if not ch.isspace() and ch not in STRIP_CHARS)


def hit_any(answer, needles):
    """返回命中的 needle 列表；原文包含或去间隔符后包含都算。"""
    a = str(answer or "")
    ac = compact(a)
    hits = []
    for n in needles or []:
        n = str(n or "")
        if not n:
            continue
        if n in a or compact(n) in ac:
            hits.append(n)
    return hits


def is_refusal(answer):
    a = str(answer or "")
    return any(m in a for m in REFUSAL_MARKERS)


def norm_text(s):
    s = unicodedata.normalize("NFKC", str(s or ""))
    return "".join(ch for ch in s
                   if not ch.isspace() and ch not in "\u00b7-\u2014\u2013_.\u3002\uff0c\u3001")


def db_stats(path):
    """库内行数/块数/精确重复/norm 重复（脏数据证据）。"""
    if not path or not os.path.exists(path):
        return None
    con = sqlite3.connect(path)
    try:
        rows = list(con.execute("SELECT id,name,text,source_hash FROM memory_source"))
        nblocks = con.execute("SELECT COUNT(*) FROM memory_block").fetchone()[0]
    finally:
        con.close()
    exact, norm = {}, {}
    for sid, name, text, h in rows:
        exact.setdefault(h, []).append(int(sid))
        norm.setdefault(norm_text(text), []).append(int(sid))
    edup = {k: v for k, v in exact.items() if len(v) > 1}
    ndup = {k: v for k, v in norm.items() if len(v) > 1}
    return {"rows": len(rows), "blocks": int(nblocks),
            "exact_dup_groups": len(edup),
            "exact_dup_rows": sum(len(v) for v in edup.values()),
            "norm_dup_groups": len(ndup),
            "norm_dup_rows": sum(len(v) for v in ndup.values()),
            "norm_dup_pairs": [v for v in ndup.values()]}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def http_json(url, body=None, timeout=180):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def ask(endpoint, text, timeout):
    t0 = time.perf_counter()
    resp = http_json(endpoint.rstrip("/") + "/ask", {"text": text}, timeout=timeout)
    client_ms = (time.perf_counter() - t0) * 1000.0
    return resp, client_ms


# ---------------------------------------------------------------------------
# 指标
# ---------------------------------------------------------------------------
def pct(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = int(math.ceil(p / 100.0 * len(xs))) - 1
    return round(xs[max(0, min(len(xs) - 1, k))], 1)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


def ratio(num, den):
    return round(num / float(den), 4) if den else None


def summarize(items):
    asked = [x for x in items if x.get("ok")]
    if not asked:
        return {"n": 0, "asked": 0, "errors": len(items)}
    with_target = [x for x in asked if x.get("target_block_id") is not None]
    lat = [x.get("latency_ms") for x in asked if x.get("latency_ms") is not None]
    recall = sum(1 for x in with_target if x.get("target_in_block_ids"))
    recall4 = sum(1 for x in with_target if x.get("target_in_top4"))
    recall6 = sum(1 for x in with_target if x.get("target_in_top6"))
    passes = sum(1 for x in asked if x.get("pass"))
    leaks = sum(1 for x in asked if x.get("leak"))
    refus = sum(1 for x in asked if x.get("refusal"))
    trunc = sum(1 for x in asked if x.get("truncated"))
    ghost = sum(1 for x in asked if x.get("ghost_picked"))
    with_t = [x for x in asked if x.get("target_block_id") is not None]
    no_t = [x for x in asked if x.get("target_block_id") is None]
    ans = [x for x in asked if x.get("answerable")]
    return {
        "n": len(asked),
        "errors": len(items) - len(asked),
        "with_target": len(with_target),
        "recall_at_mounted": ratio(recall, len(with_target)),
        "recall_at_4": ratio(recall4, len(with_target)),
        "recall_at_6": ratio(recall6, len(with_target)),
        "pass": ratio(passes, len(asked)),
        "pass_answerable": ratio(sum(1 for x in ans if x.get("pass")), len(ans)),
        "answerable": len(ans),
        "absent_target": len(asked) - len(ans),
        "budget_dropped": sum(1 for x in asked if x.get("budget_dropped")),
        "old_value_leak": ratio(leaks, len(asked)),
        "refusal": ratio(refus, len(asked)),
        "refusal_on_answerable": ratio(
            sum(1 for x in with_t if x.get("refusal")), len(with_t)),
        "refusal_on_negative": ratio(
            sum(1 for x in no_t if x.get("refusal")), len(no_t)),
        "truncated": trunc,
        "http_5xx": sum(1 for x in items if int(x.get("http_status") or 0) >= 500),
        "lock_errors": sum(1 for x in items
                           if x.get("error_code") in ("lock", "busy", "queue_timeout",
                                                      "service_degraded")
                           or "lock" in str(x.get("error") or "").lower()),
        "ghost_picked": ghost,
        "latency_ms_mean": mean(lat),
        "latency_ms_p50": pct(lat, 50),
        "latency_ms_p95": pct(lat, 95),
    }


# ---------------------------------------------------------------------------
# 校验（离线）
# ---------------------------------------------------------------------------
def check_queries(rows):
    problems = []
    seen = set()
    for i, q in enumerate(rows, start=1):
        if not q.get("id"):
            problems.append("row %d: missing id" % i)
        if q.get("id") in seen:
            problems.append("row %d: duplicate id %s" % (i, q.get("id")))
        seen.add(q.get("id"))
        if not (q.get("text") or "").strip():
            problems.append("%s: empty text" % q.get("id"))
        if not isinstance(q.get("expect_any"), list) or not q.get("expect_any"):
            problems.append("%s: expect_any empty" % q.get("id"))
        if not isinstance(q.get("not_contains"), list):
            problems.append("%s: not_contains not a list" % q.get("id"))
        if q.get("target_in_library") and q.get("target_block_id") is None \
                and q.get("src_target_block_id"):
            problems.append("%s: in-library but target is null" % q.get("id"))
        if not q.get("target_in_library", True) and q.get("target_block_id") is not None:
            problems.append("%s: out-of-library but target set" % q.get("id"))
        if q.get("reverse_chain"):
            if q.get("ghost_block_id") is None:
                problems.append("%s: reverse chain without ghost id" % q.get("id"))
            if any(v in (q.get("expect_any") or []) for v in (q.get("not_contains") or [])):
                problems.append("%s: expect/not_contains overlap" % q.get("id"))
    return problems


def print_check(rows, problems):
    kinds, fams = {}, {}
    for q in rows:
        kinds[q.get("kind")] = kinds.get(q.get("kind"), 0) + 1
        fams[q.get("family")] = fams.get(q.get("family"), 0) + 1
    asked = [q for q in rows if q.get("in_sample", True)]
    print("queries      :", len(rows))
    print("asked/skipped: %d / %d" % (len(asked), len(rows) - len(asked)))
    print("kind         :", dict(sorted(kinds.items())))
    print("family       :", dict(sorted(fams.items())))
    print("reverse      :", sum(1 for q in rows if q.get("reverse_chain")))
    print("targets      : %d mapped / %d null / %d unmapped"
          % (sum(1 for q in rows if q.get("target_block_id") is not None),
             sum(1 for q in rows if q.get("in_sample") and q.get("target_block_id") is None),
             sum(1 for q in rows if not q.get("in_sample", True))))
    print("problems     :", problems or "none")
    return 0 if not problems else 1


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dst", default=os.path.join(ROOT, "kvmem", "scale40k", "n20"))
    ap.add_argument("--endpoint", default="http://127.0.0.1:8765")
    ap.add_argument("--out", default=None, help="默认 dst/RESULT.json")
    ap.add_argument("--label", default="", help="臂名，如 n100-k2on")
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--limit", type=int, default=0, help="只跑前 K 条（调试）")
    ap.add_argument("--check", action="store_true", help="离线校验 queries.jsonl，不发请求")
    ap.add_argument("--skip-health", action="store_true")
    ap.add_argument("--db", default=None, help="默认 dst/chat.db（审计行数/重复）")
    args = ap.parse_args(argv)

    dst = os.path.abspath(args.dst)
    qpath = os.path.join(dst, "queries.jsonl")
    outpath = os.path.abspath(args.out or os.path.join(dst, "RESULT.json"))
    if not os.path.exists(qpath):
        print("ERROR: 缺少 %s（先跑 scale40k_build.py）" % qpath, file=sys.stderr)
        return 2
    rows = []
    with open(qpath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    if args.limit:
        rows = rows[:args.limit]

    problems = check_queries(rows)
    if args.check or problems:
        print_check(rows, problems)
        if args.check:
            return 0 if not problems else 1
        print("ERROR: queries.jsonl 未通过校验", file=sys.stderr)
        return 2

    todo = [q for q in rows if q.get("in_sample", True)]
    skipped = len(rows) - len(todo)

    health = None
    if not args.skip_health:
        try:
            health = http_json(args.endpoint.rstrip("/") + "/health", timeout=15)
        except Exception as exc:                          # noqa: BLE001
            print("ERROR: 服务不可用 %s: %s" % (args.endpoint, exc), file=sys.stderr)
            return 3
        print("health     :", {k: health.get(k) for k in ("memories", "state", "model")})

    per_query = []
    t_start = time.time()
    for i, q in enumerate(todo, start=1):
        rec = {
            "id": q.get("id"), "kind": q.get("kind"),
            "family": q.get("family"), "text": q.get("text"),
            "target_block_id": q.get("target_block_id"),
            "ghost_block_id": q.get("ghost_block_id"),
            "reverse_chain": bool(q.get("reverse_chain")),
            "src_target_block_id": q.get("src_target_block_id"),
            "expect_any": q.get("expect_any"), "not_contains": q.get("not_contains"),
        }
        try:
            resp, client_ms = ask(args.endpoint, q.get("text") or "", args.timeout)
        except Exception as exc:                          # noqa: BLE001
            st, ec = None, None
            if isinstance(exc, urllib.error.HTTPError):
                st = exc.code
                try:
                    _b = json.loads(exc.read().decode("utf-8") or "{}")
                    ec = (_b.get("error") or {}).get("code")
                except Exception:                        # noqa: BLE001
                    pass
            rec.update(ok=False, error="%s: %s" % (type(exc).__name__, exc),
                       http_status=st, error_code=ec)
            per_query.append(rec)
            print("[%3d/%3d] %s ERROR %s" % (i, len(todo), rec["id"], rec["error"]))
            continue
        answer = str(resp.get("answer") or "")
        block_ids = [int(x) for x in (resp.get("block_ids") or []) if x is not None]
        retr = resp.get("retrieval") or {}
        lat_ms = resp.get("latency_s")
        lat_ms = round(float(lat_ms) * 1000.0, 1) if lat_ms is not None else round(client_ms, 1)
        hit = hit_any(answer, q.get("expect_any"))
        leak_hits = hit_any(answer, q.get("not_contains"))
        verify = resp.get("verify") or {}
        tgt = q.get("target_block_id")
        ghost = q.get("ghost_block_id")
        scores_ids = [int(x[0]) for x in (retr.get("scores") or []) if x]
        budget_dropped = bool(tgt is not None and retr.get("truncated")
                              and tgt in scores_ids
                              and tgt not in (retr.get("selected_ids") or []))
        answerable = (tgt is not None) or (q.get("src_target_block_id") is None)
        k2info = resp.get("k2") or {}
        rec.update(
            ok=True, answer=answer, state=resp.get("state"),
            k2=k2info, k2_mode=k2info.get("mode"),
            k2_gate=k2info.get("gate_reason"),
            refused=bool(resp.get("refused")), block_ids=block_ids,
            latency_ms=lat_ms, latency_ms_client=round(client_ms, 1),
            expect_hit=hit, pass_=bool(hit) and not leak_hits,
            leak_hits=leak_hits, leak=bool(leak_hits),
            refusal=bool(resp.get("refused")) or is_refusal(answer),
            verify_verdict=verify.get("verdict"),
            verify_attempts=resp.get("verify_attempts"),
            truncated=bool(retr.get("truncated")),
            budget_dropped=budget_dropped,
            answerable=answerable,
            target_in_library=bool(q.get("target_in_library", tgt is not None)),
            selected_ids=retr.get("selected_ids"),
            target_in_selected=(tgt in (retr.get("selected_ids") or []))
                               if tgt is not None else None,
            target_in_block_ids=(tgt in block_ids) if tgt is not None else None,
            target_in_top4=(tgt in block_ids[:4]) if tgt is not None else None,
            target_in_top6=(tgt in block_ids[:6]) if tgt is not None else None,
            ghost_picked=(ghost in block_ids and tgt not in block_ids)
                         if (ghost is not None and tgt is not None) else False,
        )
        rec["pass"] = rec.pop("pass_")
        per_query.append(rec)
        print("[%3d/%3d] %-5s %-10s pass=%s leak=%s lat=%.0fms ans=%r"
              % (i, len(todo), rec["id"], rec["kind"], rec["pass"], rec["leak"],
                 rec["latency_ms"], answer[:48]))

    def subset(pred):
        return [x for x in per_query if pred(x)]

    by_kind = {k: summarize(subset(lambda x, k=k: x.get("kind") == k))
               for k in sorted({x.get("kind") for x in todo})}
    by_family = {k: summarize(subset(lambda x, k=k: x.get("family") == k))
                 for k in sorted({x.get("family") for x in todo})}
    result = {
        "schema": "scale40k_result_v2",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "label": args.label,
        "dst": dst,
        "endpoint": args.endpoint,
        "queries_file": qpath,
        "counts": {"queries_total": len(rows), "asked": len(todo), "skipped_unmapped": skipped,
                   "errors": sum(1 for x in per_query if not x.get("ok"))},
        "health_before": health,
        "metrics": {
            "overall": summarize(per_query),
            "by_kind": by_kind,
            "by_family": by_family,
            "reverse_chain": summarize(subset(lambda x: x.get("reverse_chain"))),
            "non_reverse": summarize(subset(lambda x: not x.get("reverse_chain"))),
            "negative": summarize(subset(lambda x: x.get("kind") == "negative")),
            "answerable": summarize(subset(lambda x: x.get("answerable"))),
            "absent_target": summarize(subset(lambda x: not x.get("answerable"))),
        },
        "k2": {
            "mode": {k: sum(1 for x in per_query if x.get("k2_mode") == k)
                     for k in sorted({str(x.get("k2_mode")) for x in per_query})},
            "gate_reason": {k: sum(1 for x in per_query if x.get("k2_gate") == k)
                            for k in sorted({str(x.get("k2_gate")) for x in per_query})},
            "non_count": [x.get("id") for x in per_query
                          if x.get("k2_gate") not in (None, "count")],
        },
        "dist": {
            "state": {k: sum(1 for x in per_query if x.get("state") == k)
                      for k in sorted({str(x.get("state")) for x in per_query})},
            "verify_verdict": {k: sum(1 for x in per_query
                                      if str(x.get("verify_verdict")) == k)
                               for k in sorted({str(x.get("verify_verdict"))
                                                for x in per_query})},
        },
        "per_query": per_query,
        "db": db_stats(os.path.abspath(args.db or os.path.join(dst, "chat.db"))),
        "elapsed_s": round(time.time() - t_start, 1),
    }
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    m = result["metrics"]["overall"]
    print("RESULT   :", outpath)
    print("overall  : n=%d recall@mounted=%s pass=%s pass_answerable=%s leak=%s refusal=%s "
          "budget_dropped=%s P50=%sms P95=%sms"
          % (m["n"], m["recall_at_mounted"], m["pass"], m.get("pass_answerable"),
             m["old_value_leak"], m["refusal"], m.get("budget_dropped"),
             m["latency_ms_p50"], m["latency_ms_p95"]))
    if result.get("db"):
        print("db       : rows=%s blocks=%s exact_dup=%s norm_dup=%s"
              % (result["db"]["rows"], result["db"]["blocks"],
                 result["db"]["exact_dup_groups"], result["db"]["norm_dup_groups"]))
    print("reverse  :", {k: result["metrics"]["reverse_chain"].get(k)
                        for k in ("n", "recall_at_mounted", "pass", "ghost_picked")})
    return 0 if result["counts"]["errors"] == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())