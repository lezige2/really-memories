# -*- coding: utf-8 -*-
"""inspect_logs.py -- C 版个体日志查看/校验工具（CPU-only，零 GPU，零网络）。

用法：
  python -X utf8 tools/inspect_logs.py --verify
  python -X utf8 tools/inspect_logs.py --summary [session_id]
  python -X utf8 tools/inspect_logs.py --tail 20 [--session <id>]
  python -X utf8 tools/inspect_logs.py --grep 关键词
  python -X utf8 tools/inspect_logs.py --export kvmem/assistant/export-<date>.json

校验（--verify，exit 0/1）：
  * 每行是合法 UTF-8 JSON，schema=assistant_log_v1；
  * 公共字段齐全；event 合法；事件必填字段齐全（PRODUCT-C-LOG-SPEC §3）；
  * seq 连续（新会话从 1 起；resume 文件跨段仍连续）；
  * chain_sha16 连续（首行 ""，其后 = 上一行内容 sha256 前 16 位）；
  * 每次 ask 之后都有对应 answer/refuse（按 ask_seq）。
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import assistant_log as L          # noqa: E402

EXIT_OK, EXIT_BAD = 0, 1
COMMON = ("schema", "seq", "ts", "assistant_id", "session_id", "event", "pid",
          "chain_sha16")


def sessions(root):
    return L._iter_text_files(os.path.join(root, "sessions"))


def _line_sha(raw_line):
    return hashlib.sha256(raw_line.rstrip(b"\r\n")).hexdigest()[:16]


def verify(root):
    result = {"ok": True, "root": root, "sessions_checked": 0, "lines_checked": 0,
              "errors": [], "codes": {}, "sessions": []}
    for path in sessions(root):
        result["sessions_checked"] += 1
        result["sessions"].append(os.path.basename(path))
        rows = L.read_session(path)
        first_seq = None
        prev_sha = None
        asks = {}
        answered = set()
        for lineno, raw, obj in rows:
            result["lines_checked"] += 1

            def bad(code, msg, **kw):
                result["ok"] = False
                item = {"file": os.path.basename(path), "line": lineno,
                        "code": code, "message": msg}
                item.update(kw)
                result["errors"].append(item)
                result["codes"][code] = result["codes"].get(code, 0) + 1

            if "__parse_error__" in obj:
                bad("bad_json", obj["__parse_error__"])
                continue
            for k in COMMON:
                if k not in obj:
                    bad("missing_common", "缺公共字段 %s" % k)
            if obj.get("schema") != L.SCHEMA:
                bad("bad_schema", "schema=%r" % obj.get("schema"))
            ev = obj.get("event")
            if ev not in L.REQUIRED:
                bad("unknown_event", "event=%r" % ev)
                continue
            for k in L.REQUIRED[ev]:
                if k not in obj:
                    bad("missing_field", "%s 缺必填字段 %s" % (ev, k))
            seq = obj.get("seq")
            if not isinstance(seq, int):
                bad("bad_seq", "seq=%r" % seq)
            else:
                if first_seq is None:
                    first_seq = seq
                    if seq != 1:
                        bad("seq_start", "首行 seq=%d（应从 1 起）" % seq)
                elif "__parse_error__" not in rows[lineno - 2][2]:
                    prev_seq = rows[lineno - 2][2].get("seq")
                    if isinstance(prev_seq, int) and seq != prev_seq + 1:
                        bad("seq_gap", "seq=%d，上一行 seq=%r" % (seq, prev_seq))
            want_chain = "" if prev_sha is None else prev_sha
            if obj.get("chain_sha16") != want_chain:
                bad("broken_chain", "chain=%r，应为 %r（上一行 %s）"
                    % (obj.get("chain_sha16"), want_chain, os.path.basename(path)))
            prev_sha = _line_sha(raw)
            if obj.get("session_id") not in os.path.basename(path):
                bad("session_mismatch", "行内 session_id=%r 与文件名不符"
                    % obj.get("session_id"))
            if ev == "ask":
                asks[seq] = obj
            elif ev in ("answer", "refuse") and isinstance(obj.get("ask_seq"), int):
                answered.add(obj["ask_seq"])
        last_ev = rows[-1][2].get("event") if rows else None
        aborted = last_ev != "session_end"
        if aborted:
            result.setdefault("aborted_sessions", []).append(os.path.basename(path))
        for ask_seq in asks:
            if aborted:
                break          # S7b：被强杀的会话允许末个 ask 无 answer（已由 crash_recovered 留痕）
            if ask_seq not in answered:
                result["ok"] = False
                item = {"file": os.path.basename(path), "line": None,
                        "code": "ask_without_answer",
                        "message": "ask seq=%d 没有对应 answer/refuse" % ask_seq}
                result["errors"].append(item)
                result["codes"]["ask_without_answer"] = \
                    result["codes"].get("ask_without_answer", 0) + 1
    return result


def _load_events(root, session_id=None):
    out = []
    paths = sessions(root)
    for path in paths:
        if session_id and session_id not in os.path.basename(path):
            continue
        for lineno, raw, obj in L.read_session(path):
            if "__parse_error__" in obj:
                continue
            obj["_file"] = os.path.basename(path)
            obj["_line"] = lineno
            out.append(obj)
    return out


def _pct(values, p):
    if not values:
        return None
    vals = sorted(values)
    k = max(0, min(len(vals) - 1, int(round((p / 100.0) * (len(vals) - 1)))))
    return vals[k]


def summary(root, session_id=None):
    events = _load_events(root, session_id)
    counts = {}
    lat = []
    vram = []
    asks = 0
    answers = 0
    refuses = 0
    errors = 0
    crashes = 0
    sessions_seen = set()
    for e in events:
        ev = e.get("event")
        counts[ev] = counts.get(ev, 0) + 1
        sessions_seen.add(e.get("session_id"))
        if ev == "ask":
            asks += 1
        elif ev == "answer":
            answers += 1
            if e.get("latency_ms") is not None:
                lat.append(float(e["latency_ms"]))
            if e.get("vram_gib") is not None:
                vram.append(float(e["vram_gib"]))
        elif ev == "refuse":
            refuses += 1
            if e.get("latency_ms") is not None:
                lat.append(float(e["latency_ms"]))
        elif ev == "error":
            errors += 1
        elif ev == "crash_recovered":
            crashes += 1
    total_replies = answers + refuses
    return {
        "root": root,
        "session_filter": session_id,
        "sessions": sorted(x for x in sessions_seen if x),
        "events": counts,
        "n_events": len(events),
        "asks": asks,
        "answers": answers,
        "refuses": refuses,
        "refusal_rate": round(refuses / total_replies, 4) if total_replies else None,
        "latency_ms": {"p50": _pct(lat, 50), "p95": _pct(lat, 95),
                       "n": len(lat)},
        "vram_peak_gib": max(vram) if vram else None,
        "errors": errors,
        "crash_recovered": crashes,
        "generated_at": L.now_iso(),
    }


def tail(root, n=20, session_id=None):
    events = _load_events(root, session_id)
    return events[-int(n):] if n else []


def grep(root, kw):
    hits = []
    paths = sessions(root) + L._iter_text_files(os.path.join(root, "daily"))
    inc = os.path.join(root, "incidents.jsonl")
    if os.path.exists(inc):
        paths.append(inc)
    kw = str(kw)
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                for i, line in enumerate(f, start=1):
                    if kw in line:
                        hits.append({"file": os.path.basename(path), "line": i,
                                     "text": line.strip()[:400]})
        except OSError:
            continue
    return hits


def export_summary(root, out_path):
    """导出脱敏摘要：不含原文/回答，只有计数、延迟、错误码与时间。"""
    data = summary(root)
    data["schema"] = "assistant_log_export_v1"
    data["note"] = "脱敏摘要：不含任何原文/回答文本，可安全发给维护者"
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, out_path)
    return out_path, data


def main(argv=None):
    ap = argparse.ArgumentParser(description="C 版个体日志查看/校验（CPU-only）")
    ap.add_argument("--root", default=L.DEFAULT_ROOT, help="日志根目录")
    ap.add_argument("--verify", action="store_true", help="校验完整性（exit 0/1）")
    ap.add_argument("--summary", nargs="?", const="", default=None,
                    help="汇总（可带 session_id）")
    ap.add_argument("--tail", type=int, default=None, help="最后 N 条事件")
    ap.add_argument("--session", default=None, help="限定 session_id")
    ap.add_argument("--grep", default=None, help="按关键词检索")
    ap.add_argument("--export", default=None, help="导出脱敏摘要 JSON")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    a = ap.parse_args(argv)

    if not os.path.isdir(a.root):
        print("error: 日志目录不存在：%s" % a.root)
        return EXIT_BAD

    did = False
    rc = EXIT_OK
    if a.verify:
        did = True
        rep = verify(a.root)
        if a.json:
            print(json.dumps(rep, ensure_ascii=False, indent=1))
        else:
            print("verify: %s  sessions=%d lines=%d errors=%d"
                  % ("OK" if rep["ok"] else "FAILED", rep["sessions_checked"],
                     rep["lines_checked"], len(rep["errors"])))
            for err in rep["errors"][:20]:
                print("  - %s:%s [%s] %s" % (err.get("file"), err.get("line"),
                                             err.get("code"), err.get("message")))
            if rep["errors"]:
                print("  codes:", json.dumps(rep["codes"], ensure_ascii=False))
        if not rep["ok"]:
            rc = EXIT_BAD
    if a.summary is not None:
        did = True
        sid = a.summary or a.session
        rep = summary(a.root, sid)
        if a.json:
            print(json.dumps(rep, ensure_ascii=False, indent=1))
        else:
            print("summary: sessions=%d events=%d asks=%d answers=%d refuses=%d "
                  "refusal_rate=%s latency_p50=%s p95=%s vram_peak=%s errors=%d "
                  "crash_recovered=%d"
                  % (len(rep["sessions"]), rep["n_events"], rep["asks"],
                     rep["answers"], rep["refuses"], rep["refusal_rate"],
                     rep["latency_ms"]["p50"], rep["latency_ms"]["p95"],
                     rep["vram_peak_gib"], rep["errors"], rep["crash_recovered"]))
    if a.tail is not None:
        did = True
        for e in tail(a.root, a.tail, a.session):
            print(json.dumps(e, ensure_ascii=False))
    if a.grep is not None:
        did = True
        hits = grep(a.root, a.grep)
        for h in hits:
            print("%s:%d %s" % (h["file"], h["line"], h["text"]))
        print("grep: %d hit(s)" % len(hits))
    if a.export is not None:
        did = True
        path, data = export_summary(a.root, a.export)
        print("exported: %s（%d events）" % (path, data["n_events"]))
    if not did:
        print("用法见 --help；至少给 --verify / --summary / --tail / --grep / --export 之一")
        return EXIT_BAD
    return rc


if __name__ == "__main__":
    sys.exit(main())