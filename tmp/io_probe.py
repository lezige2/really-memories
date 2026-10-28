# -*- coding: utf-8 -*-
"""io_probe.py -- 长上下文 I/O 风暴实测探针（只读代码/只发 HTTP；不改仓库文件）。

在 127.0.0.1:8765 上跑 N 轮短/长对话，逐轮前后快照：
  * kvmem/daily/**（整体）
  * kvmem/daily/sessions/*.kvmem*（会话文件）
  * kvmem/daily/blocks/*.kvmem（记忆/archive/summary 块）
  * kvmem/daily/*.db（sqlite）
  * kvmem/assistant/**（assistant 日志/审计索引）
  * 其他 kvmem/daily 文件
并记录每轮：chat_tokens、rollover 事件、写入字节（total/分类/单文件 top）、耗时、错误。

策略：默认先发若干条长消息把会话推到 rollover 阈值（当前服务 32k：阈值 18432 token），
触发 rollover 后其余轮次用短消息；也可用 --no-long 只发短消息（用于对照/等 LEAD 用
--rollover-at 0.1 重启后再跑）。

用法：
  python -X utf8 tmp/io_probe.py --rounds 60 --out out/IO-PROBE.json
  python -X utf8 tmp/io_probe.py --rounds 60 --long-rounds 16 --long-chars 1600
  python -X utf8 tmp/io_probe.py --no-long            # 只短消息（当前配置下多半不触发 rollover）

输出：out/IO-PROBE.json（逐轮/rollover 事件/汇总），每轮原子落盘（中断也有 partial）。
不重置会话（--reset 可显式重置一次）；不重启服务；不改任何仓库文件。
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.abspath(__file__)
DEFAULT_EP = "http://127.0.0.1:8765"

SHORT = ["你好", "在吗", "今天过得怎么样", "随便聊聊", "谢谢", "你是谁",
         "讲个短句", "好的", "继续", "嗯嗯"]
LONG_BASE = ("继续聊一下今天的安排。上午处理了一些邮件和文档，下午把资料按主题重新归档，"
             "中间核对了几处细节，也顺手更新了进度记录。整体节奏还算稳定，后面先把剩下"
             "的收尾工作做完，再考虑下一步怎么推进。")

CATS = [("sessions", "kvmem/daily/sessions"), ("blocks", "kvmem/daily/blocks"),
        ("db", "kvmem/daily"), ("assistant", "kvmem/assistant"),
        ("archive", "kvmem/daily/archive"), ("other", "kvmem/daily")]


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def http_json(ep, path, payload=None, timeout=300.0, retries=2):
    url = ep.rstrip("/") + path
    body = None
    headers = {"Accept": "application/json"}
    method = "GET"
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
        method = "POST"
    last = None
    for attempt in range(1, retries + 2):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.status >= 500:
                    last = "HTTP %s" % r.status
                    time.sleep(0.5 * attempt)
                    continue
                return (json.loads(raw.decode("utf-8")) if raw else {}), attempt, None
        except urllib.error.HTTPError as exc:
            last = "HTTP %s" % exc.code
            if exc.code in (429, 500, 502, 503, 504) and attempt <= retries:
                time.sleep(0.5 * attempt)
                continue
            return None, attempt, last
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last = type(exc).__name__ + ": " + str(exc)[:120]
            if attempt <= retries:
                time.sleep(0.5 * attempt)
                continue
            return None, attempt, last
    return None, retries + 1, last


def snap():
    """快照 kvmem 下文件：rel -> (size, mtime_ns)。"""
    out = {}
    for base in ("kvmem/daily", "kvmem/assistant"):
        root = os.path.join(ROOT, base)
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, ROOT).replace("\\", "/")
                try:
                    st = os.stat(p)
                    out[rel] = (st.st_size, st.st_mtime_ns)
                except OSError:
                    continue
    return out


def cat_of(rel):
    if rel.startswith("kvmem/daily/sessions/"):
        return "sessions"
    if rel.startswith("kvmem/daily/blocks/"):
        return "blocks"
    if rel.startswith("kvmem/daily/archive/"):
        return "archive"
    if rel.startswith("kvmem/daily/") and rel.endswith((".db", ".db-wal", ".db-shm")):
        return "db"
    if rel.startswith("kvmem/assistant/"):
        return "assistant"
    return "other"


def diff(before, after):
    """返回 (total_delta, cat_delta, top_files, new_files)；只统计增长/新增。"""
    cat, top, newf = {}, [], []
    for rel, (size, mtime) in after.items():
        b = before.get(rel)
        if b is None:
            delta = size
            newf.append({"path": rel, "bytes": size})
        else:
            delta = size - b[0]
        if delta > 0:
            cat[cat_of(rel)] = cat.get(cat_of(rel), 0) + delta
            top.append({"path": rel, "delta": delta, "after": size,
                        "mtime_changed": (b is None or b[1] != mtime)})
    total = sum(cat.values())
    top.sort(key=lambda x: -x["delta"])
    return total, cat, top[:12], newf


def tokens_of(st):
    try:
        return int((st or {}).get("session", {}).get("chat_tokens"))
    except (TypeError, ValueError):
        return None


def dump(path, doc):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="I/O storm probe (HTTP only)")
    ap.add_argument("--endpoint", default=DEFAULT_EP)
    ap.add_argument("--rounds", type=int, default=60)
    ap.add_argument("--long-rounds", type=int, default=16,
                    help="先发多少条长消息以触发 rollover（0=先不发长消息）")
    ap.add_argument("--long-chars", type=int, default=1600)
    ap.add_argument("--short-chars", type=int, default=60)
    ap.add_argument("--request-timeout", type=float, default=300.0)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "IO-PROBE.json"))
    ap.add_argument("--reset", action="store_true", help="开始时 POST /reset（默认不重置）")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    doc = {"schema": "io_probe_v1", "version": 1, "started_at": now(),
           "plan": {"endpoint": a.endpoint, "rounds": a.rounds,
                    "long_rounds": a.long_rounds, "long_chars": a.long_chars,
                    "short_chars": a.short_chars, "reset": bool(a.reset),
                    "script": os.path.basename(SCRIPT),
                    "script_sha256": __import__("hashlib").sha256(
                        open(SCRIPT, "rb").read()).hexdigest()},
           "service_before": None, "rounds": [], "rollovers": [],
           "errors": [], "summary": {}, "partial": True}
    t0 = time.time()

    def log(*args):
        if not a.quiet:
            print(*args, flush=True)

    try:
        st, _n, err = http_json(a.endpoint, "/status", timeout=60)
        if err:
            doc["errors"].append({"phase": "status_before", "error": err})
        doc["service_before"] = {k: (st or {}).get(k) for k in
                                 ("version", "engine_meta", "model_pin", "session", "rollover")
                                 if isinstance(st, dict)} if st else None
        if a.reset:
            _r, _n, err = http_json(a.endpoint, "/reset", {}, timeout=120)
            if err:
                doc["errors"].append({"phase": "reset", "error": err})
        prev = snap()
        dump(a.out, doc)

        rollover_seen = False
        long_sent = 0
        for turn in range(1, a.rounds + 1):
            use_long = (not rollover_seen) and long_sent < a.long_rounds
            if use_long:
                text = LONG_BASE
                while len(text) < a.long_chars:
                    text += LONG_BASE
                text = text[:a.long_chars]
                long_sent += 1
            else:
                text = SHORT[(turn - 1) % len(SHORT)] + "（第%d轮）" % turn
                text = text[:a.short_chars]
            before = prev
            t1 = time.time()
            resp, attempts, err = http_json(a.endpoint, "/ask", {"text": text},
                                            timeout=a.request_timeout, retries=a.retries)
            dur = round(time.time() - t1, 3)
            after = snap()
            total, cat, top, newf = diff(before, after)
            prev = after
            st2, _n2, serr = http_json(a.endpoint, "/status", timeout=60)
            tokens = tokens_of(st2)
            roll = (resp or {}).get("rollover") if isinstance(resp, dict) else None
            if roll:
                rollover_seen = True
                doc["rollovers"].append({"turn": turn, "chat_tokens": tokens,
                                         "delta_bytes": total, "delta_by_cat": cat,
                                         "top_files": top[:8],
                                         "rollover": roll,
                                         "at": now()})
                log("ROLLOVER turn=%d tokens=%s delta=%.1f MB top=%s" %
                    (turn, tokens, total / 1048576,
                     top[0]["path"] if top else "-"))
            rec = {"turn": turn, "kind": "long" if use_long else "short",
                   "text_len": len(text), "answer_len": len(str((resp or {}).get("answer") or "")),
                   "state": (resp or {}).get("state") if isinstance(resp, dict) else None,
                   "rollover": roll, "chat_tokens": tokens, "duration_s": dur,
                   "attempts": attempts, "error": err, "status_error": serr,
                   "delta_bytes": total, "delta_by_cat": cat,
                   "top_files": top, "new_files": newf}
            doc["rounds"].append(rec)
            if err:
                doc["errors"].append({"phase": "ask", "turn": turn, "error": err,
                                      "attempts": attempts})
            if turn % 5 == 0 or rollover_seen or total > 50 * 1048576:
                log("turn=%d kind=%s tokens=%s tokens_delta=%s bytes_delta=%.1fMB dur=%.1fs" %
                    (turn, rec["kind"], tokens, "",
                     total / 1048576, dur))
            dump(a.out, doc)

        # ---- summary ----
        rounds = doc["rounds"]
        by_cat = {}
        by_path = {}
        for r in rounds:
            for k, v in r["delta_by_cat"].items():
                by_cat[k] = by_cat.get(k, 0) + v
            for tf in r["top_files"]:
                by_path[tf["path"]] = by_path.get(tf["path"], 0) + tf["delta"]
        peak = max(rounds, key=lambda r: r["delta_bytes"]) if rounds else None
        over50 = [{"turn": r["turn"], "delta_bytes": r["delta_bytes"],
                   "by_cat": r["delta_by_cat"]} for r in rounds
                  if r["delta_bytes"] > 50 * 1048576]
        doc["summary"] = {
            "rounds": len(rounds),
            "rollover_triggered": bool(doc["rollovers"]),
            "rollover_turns": [x["turn"] for x in doc["rollovers"]],
            "total_bytes_written": sum(r["delta_bytes"] for r in rounds),
            "bytes_by_cat": by_cat,
            "peak_round": {"turn": peak["turn"], "delta_bytes": peak["delta_bytes"],
                           "by_cat": peak["delta_by_cat"],
                           "top_files": peak["top_files"][:5]} if peak else None,
            "rounds_over_50MB": over50,
            "top_written_paths": sorted(by_path.items(), key=lambda kv: -kv[1])[:15],
            "errors": len(doc["errors"]),
            "wall_s": round(time.time() - t0, 1),
        }
        doc["finished_at"] = now()
        doc["partial"] = False
        dump(a.out, doc)
        s = doc["summary"]
        print("SUMMARY rolls=%d total=%.1fMB peak=%.1fMB(roll %s) over50MB=%d errors=%d wall=%.0fs" %
              (s["rounds"], s["total_bytes_written"] / 1048576,
               (s["peak_round"]["delta_bytes"] / 1048576) if s["peak_round"] else 0,
               s["peak_round"]["turn"] if s["peak_round"] else "-",
               len(s["rounds_over_50MB"]), s["errors"], s["wall_s"]), flush=True)
        return 0
    except KeyboardInterrupt:
        doc["partial"] = True
        doc["interrupted_at"] = now()
        dump(a.out, doc)
        print("INTERRUPTED; partial saved", flush=True)
        return 130
    except Exception as exc:                  # noqa: BLE001
        doc["partial"] = True
        doc["fatal"] = repr(exc)
        dump(a.out, doc)
        print("FATAL %r; partial saved" % exc, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())