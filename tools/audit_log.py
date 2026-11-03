# -*- coding: utf-8 -*-
"""审计/日志层（纯离线；不接服务、不改 alignment）。

JSONL 落 `out/audit/YYYYMMDD.jsonl`；只记 id/哈希/原因，**不记原文/答案全文**。
所有写入包裹异常，绝不炸调用方。
"""

import hashlib
import json
import os
import sys
import threading
import uuid
from datetime import datetime

STAGES = ("write", "retrieve", "answer", "align", "archive")
_LOCK = threading.Lock()
_FIELDS = ("trace_id", "ts", "stage", "decision", "reason", "block_ids",
           "asked_slot", "tenant", "scope", "latency_ms",
           "query_sha16", "answer_sha16", "fail_open", "count")


def audit_dir():
    return os.environ.get("LLAMA_AUDIT_DIR") or os.path.join("out", "audit")


def _sha16(v):
    if not v:
        return None
    return hashlib.sha256(str(v).encode("utf-8")).hexdigest()[:16]


def _clean(event):
    out = {}
    for k in _FIELDS:
        if k not in event:
            continue
        v = event[k]
        if k == "block_ids":
            try:
                v = [int(x) for x in (v or [])][:64]
            except (TypeError, ValueError):
                v = []
        elif k == "count":
            try:
                v = int(v)
            except (TypeError, ValueError):
                v = None
        elif k == "latency_ms":
            try:
                v = round(float(v), 2)
            except (TypeError, ValueError):
                v = None
        elif k in ("decision", "reason", "stage", "tenant", "scope", "asked_slot"):
            v = str(v)[:120] if v is not None else None
        out[k] = v
    return out


def event(stage, decision=None, reason=None, block_ids=None, asked_slot=None,
          tenant="default", scope="private", latency_ms=None, trace_id=None,
          query=None, answer=None, fail_open=None, count=None):
    """追加一条审计事件；失败返回 {"ok": False}，绝不抛异常。"""
    try:
        rec = _clean({
            "trace_id": trace_id or uuid.uuid4().hex,
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "stage": stage, "decision": decision, "reason": reason,
            "block_ids": block_ids or [], "asked_slot": asked_slot,
            "tenant": tenant, "scope": scope, "latency_ms": latency_ms,
            "query_sha16": _sha16(query), "answer_sha16": _sha16(answer),
            "fail_open": bool(fail_open) if fail_open is not None else None,
            "count": count,
        })
        if rec.get("stage") not in STAGES:
            return {"ok": False, "error": "bad_stage:%s" % stage}
        d = audit_dir()
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, datetime.now().strftime("%Y%m%d") + ".jsonl")
        line = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        with _LOCK:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return {"ok": True, "path": path, "record": rec}
    except Exception as exc:                            # noqa: BLE001
        try:
            sys.stderr.write("audit_log: %s\n" % exc)
        except Exception:                               # noqa: BLE001
            pass
        return {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}


def record_alignment(result):
    """消费 answer_alignment.decide() 的输出（不 import/不改该模块）。"""
    try:
        r = dict(result or {})
        asked = r.get("asked") or {}
        return event(stage="align", decision=r.get("decision"),
                     reason=r.get("reason"), block_ids=r.get("block_ids") or [],
                     asked_slot=(asked.get("predicate") if isinstance(asked, dict)
                                 else None),
                     tenant=r.get("tenant") or "default",
                     scope=r.get("scope") or "private",
                     latency_ms=r.get("latency_ms"),
                     trace_id=r.get("trace_id"),
                     query=r.get("query"), answer=r.get("answer"),
                     fail_open=r.get("fail_open"))
    except Exception as exc:                            # noqa: BLE001
        return {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}