# -*- coding: utf-8 -*-
"""assistant_log.py -- C 版「个体日志」（PRODUCT-C-LOG-SPEC 56a7fca2b169bcf3 的 CPU 实现）。

只追加、不覆盖：
  kvmem/assistant/
    manifest.json                  assistant_id(UUID)/display_name/created_at/pins/log_config
    sessions/<session_id>.jsonl    逐事件（一行一条完整 JSON，flush+fsync，行末 \\n）
    daily/<YYYY-MM-DD>.jsonl       跨会话日索引（只含事件/延迟，不含原文）
    incidents.jsonl                error/warning/crash_recovered（severity）
    audit_index.json               末条 chain_sha16 / 行数 / 末写时间

链：每行 `chain_sha16` = **上一行内容（不含行尾换行）的 sha256 前 16 位**，首行为 ""。
写一行 = 一次 write + flush + fsync；崩溃最多丢最后一行，不会出现半行。

本模块零 GPU、零网络；chat_daily / chat_service / inspect_logs 共用。
"""

import hashlib
import json
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SCHEMA = "assistant_log_v1"
LOG_FSYNC = os.environ.get("LLAMA_MEM_LOG_FSYNC", "0").strip() in ("1", "true", "yes")
FSYNC_CALLS = [0]   # 诊断：进程内 fsync 调用计数


def _fsync(f):
    FSYNC_CALLS[0] += 1
    os.fsync(f.fileno())
MANIFEST_SCHEMA = "assistant_manifest_v1"
AUDIT_SCHEMA = "assistant_audit_v1"
DAILY_SCHEMA = "assistant_daily_v1"
LOG_VERSION = 1

MODES = ("full", "redacted", "hash_only")
DEFAULT_MODE = "redacted"

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_FILE_LINES = 200000

DEFAULT_ROOT = os.path.join(ROOT, "kvmem", "assistant")

# 必需字段（§3 表；inspect_logs 会逐条校验）
REQUIRED = {
    "session_start": ("pins", "log_config"),
    "session_resume": ("pins", "log_config"),
    "ask": (),
    "answer": ("latency_ms", "block_ids", "engine"),
    "refuse": ("reason",),
    "remember": ("id", "len_tokens"),
    "forget": ("deleted_count", "confirm"),
    "memories_list": ("count",),
    "save": ("path", "sha16"),
    "load": ("path", "sha16"),
    "status": (),
    "error": ("code", "message"),
    "warning": ("code", "message"),
    "crash_recovered": ("last_seq", "last_event", "last_ts", "unclean"),
    "context_rollover": ("before_tokens", "after_tokens", "summary_id",
                         "dropped_turns"),
    "session_end": ("reason", "duration_s", "n_events"),
}

# 敏感模式（redacted 模式打码；full 模式也禁止进 daily/incidents）
RX_ID18 = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")
RX_PHONE11 = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
RX_PASSWORD = re.compile(r"(密码|口令|password|passwd)(\s*[:：=是为]\s*)([^\s，,。;；]{2,64})",
                         re.IGNORECASE)


def sha256_hex(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha16(data):
    return sha256_hex(data)[:16]


def now_iso():
    # 本机时区 +08:00（产品口径：ts 带 +08:00）
    return datetime.now().astimezone().isoformat(timespec="seconds")


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def _iter_text_files(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, n) for n in os.listdir(folder)
                  if n.endswith(".jsonl"))


def mask_id18(value):
    return value[:3] + ("*" * 11) + value[-4:]


def mask_phone11(value):
    return value[:3] + "****" + value[-4:]


def scrub(text, mode):
    """按 log_config.mode 处理要落盘的文本。返回 (out_text, sha16, len)。

    redacted：身份证 18 位 / 手机号 11 位 / 密码值打码；
    hash_only：out_text = ""（调用方只写哈希与长度）。
    full：原文照写（但 daily/incidents 仍不写原文）。
    """
    raw = "" if text is None else str(text)
    h = sha16(raw)
    n = len(raw)
    if mode == "hash_only":
        return "", h, n
    if mode == "full":
        return raw, h, n
    out = RX_PASSWORD.sub(lambda m: m.group(1) + m.group(2) + "******", raw)
    out = RX_ID18.sub(lambda m: mask_id18(m.group(1)), out)
    out = RX_PHONE11.sub(lambda m: mask_phone11(m.group(1)), out)
    return out, h, n


class LogError(Exception):
    pass


class AssistantLog:
    """一个进程内可多次 switch 会话的日志写入器（单锁串行）。"""

    def __init__(self, root=None, session_id=None, mode=None, assistant_id=None,
                 display_name=None, pins=None, resume_crash_check=True,
                 create_session=True):
        self.root = os.path.abspath(root or DEFAULT_ROOT)
        self.sessions_dir = os.path.join(self.root, "sessions")
        self.daily_dir = os.path.join(self.root, "daily")
        os.makedirs(self.sessions_dir, exist_ok=True)
        os.makedirs(self.daily_dir, exist_ok=True)
        self.manifest_path = os.path.join(self.root, "manifest.json")
        self.incidents_path = os.path.join(self.root, "incidents.jsonl")
        self.audit_path = os.path.join(self.root, "audit_index.json")
        self._lock = threading.RLock()
        self.manifest = self._load_or_create_manifest(assistant_id, display_name)
        self.mode = (mode or self.manifest.get("log_config", {}).get("mode")
                     or DEFAULT_MODE)
        if self.mode not in MODES:
            self.mode = DEFAULT_MODE
        if pins:
            self.manifest.setdefault("pins", {}).update(pins)
        self.assistant_id = self.manifest["assistant_id"]
        self.started = time.time()
        self._session = None
        self.resumed = False
        self._resume_last = None
        if create_session:
            self.new_session(session_id=session_id)
            if resume_crash_check:
                self._resume_last = self.crash_check()
                if self._resume_last:
                    self.event("crash_recovered",
                               last_seq=self._resume_last.get("seq"),
                               last_event=self._resume_last.get("event"),
                               last_ts=self._resume_last.get("ts"),
                               unclean=True,
                               recovered_memories=self._resume_last.get("recovered_memories"),
                               source_session=self._resume_last.get("session_id"))
        else:
            self._session = self._blank_session(session_id or self._new_session_id())

    # -- manifest / identity ---------------------------------------------
    def _load_or_create_manifest(self, assistant_id=None, display_name=None):
        man = None
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, encoding="utf-8") as f:
                    man = json.load(f)
            except (OSError, ValueError):
                man = None
        if man and man.get("assistant_id"):
            if display_name:
                man["display_name"] = str(display_name)
            man.setdefault("pins", {})
            man.setdefault("log_config", {"mode": DEFAULT_MODE})
            self._write_manifest(man)
            return man
        man = {
            "schema": MANIFEST_SCHEMA,
            "schema_version": LOG_VERSION,
            "assistant_id": str(assistant_id or uuid.uuid4()),
            "display_name": str(display_name or "小助手"),
            "created_at": now_iso(),
            "pins": {},
            "log_config": {"mode": DEFAULT_MODE},
        }
        self._write_manifest(man)
        return man

    def _write_manifest(self, man):
        tmp = self.manifest_path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(man, f, ensure_ascii=False, indent=1)
            f.write("\n")
            f.flush()
            _fsync(f)
        os.replace(tmp, self.manifest_path)

    def set_display_name(self, name):
        with self._lock:
            self.manifest["display_name"] = str(name)
            self._write_manifest(self.manifest)
        return self.manifest["display_name"]

    def set_mode(self, mode):
        if mode not in MODES:
            raise LogError("mode must be one of %s" % (MODES,))
        with self._lock:
            self.mode = mode
            self.manifest.setdefault("log_config", {})["mode"] = mode
            self._write_manifest(self.manifest)
        return mode

    def pins_snapshot(self, model_path=None, dll_path=None, spec_path=None,
                      code_paths=(), force=False):
        """计算/复用 pins（model_sha16 对 9 GB 文件只算一次，缓存在 manifest 里）。"""
        pins = self.manifest.setdefault("pins", {})
        if model_path and os.path.exists(model_path):
            st = os.stat(model_path)
            cache = pins.get("model", {})
            if (force or cache.get("model_size") != st.st_size
                    or cache.get("model_mtime") != int(st.st_mtime)
                    or not cache.get("model_sha16")):
                pins["model"] = {"model_path": model_path, "model_size": st.st_size,
                                 "model_mtime": int(st.st_mtime),
                                 "model_sha16": sha16_file(model_path)}
        out = {}
        m = pins.get("model") or {}
        out["model_sha16"] = m.get("model_sha16")
        out["model_bytes"] = m.get("model_size")
        if dll_path and os.path.exists(dll_path):
            st = os.stat(dll_path)
            cache = pins.get("dll", {})
            if (cache.get("dll_bytes") != st.st_size or not cache.get("dll_sha16")
                    or cache.get("dll_mtime") != int(st.st_mtime)):
                pins["dll"] = {"dll_path": dll_path, "dll_bytes": st.st_size,
                               "dll_mtime": int(st.st_mtime),
                               "dll_sha16": sha16_file(dll_path)}
            out["dll_sha16"] = pins["dll"]["dll_sha16"]
            out["dll_bytes"] = pins["dll"]["dll_bytes"]
        if spec_path and os.path.exists(spec_path):
            out["spec_pin"] = sha16_file(spec_path)
            pins["spec_pin"] = out["spec_pin"]
        code = []
        for p in code_paths:
            if p and os.path.exists(p):
                code.append("%s:%s" % (os.path.basename(p), sha16_file(p)))
        if code:
            out["code_sha16"] = sha16("|".join(code))
            out["code_files"] = code
        pins.update(out)
        self._write_manifest(self.manifest)
        return out

    # -- session lifecycle -------------------------------------------------
    @staticmethod
    def _new_session_id():
        return "s-%s-%s" % (datetime.now().strftime("%Y%m%d-%H%M%S"),
                            uuid.uuid4().hex[:6])

    def _blank_session(self, session_id):
        return {"session_id": session_id, "seq": 1, "chain": "", "lines": 0,
                "bytes": 0, "path": os.path.join(self.sessions_dir,
                                                 session_id + ".jsonl"),
                "events": 0, "started": time.time(), "part": 1}

    def new_session(self, session_id=None):
        """切换/新建会话文件；是否 resume 由 self.resumed 告知调用方（由调用方写
        session_start / session_resume，保证 §3 的必填字段齐全）。"""
        with self._lock:
            self._session = self._blank_session(session_id or self._new_session_id())
            path = self._session["path"]
            self.resumed = False
            if os.path.exists(path):
                last = read_last_line(path)
                if last:
                    self._session["seq"] = int(last.get("seq", 0)) + 1
                    self._session["chain"] = sha16(last_raw_line(path))
                    self._session["lines"] = count_lines(path)
                    self._session["bytes"] = os.path.getsize(path)
                    self.resumed = True
            return self._session["session_id"]

    def current_session_id(self):
        return self._session["session_id"]

    def crash_check(self, exclude_current=True):
        """扫最近一个**非当前**会话文件；末事件不是 session_end 则返回它（供写 crash_recovered）。"""
        files = [p for p in _iter_text_files(self.sessions_dir)
                 if not (exclude_current and p == self._session["path"])]
        if not files:
            return None
        files.sort(key=lambda p: os.path.getmtime(p))
        path = files[-1]
        last = read_last_line(path)
        if not last:
            return None
        if last.get("event") == "session_end":
            return None
        return {"session_id": last.get("session_id"), "seq": last.get("seq"),
                "event": last.get("event"), "ts": last.get("ts"),
                "recovered_memories": last.get("memories_after")}

    # -- 写一行 -----------------------------------------------------------
    def _append_line(self, path, payload):
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        data = (line + "\n").encode("utf-8")
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "ab") as f:
            f.write(data)          # 整行一次写出
            f.flush()
            if LOG_FSYNC:          # 默认关闭逐事件 fsync，session_end/close 时统一刷
                _fsync(f)
        return line, data

    def _rotate_if_needed(self):
        s = self._session
        if s["part"] == 1 and (s["bytes"] > MAX_FILE_BYTES or s["lines"] > MAX_FILE_LINES):
            s["part"] += 1
            base, ext = os.path.splitext(self._session["path"])
            s["path"] = "%s.part%d%s" % (base, s["part"], ext)
            s["seq"] = 1
            s["chain"] = ""
            s["lines"] = 0
            s["bytes"] = 0
            return True
        return False

    def event(self, event, **fields):
        if event not in REQUIRED:
            raise LogError("unknown event %r (schema v%d)" % (event, LOG_VERSION))
        with self._lock:
            rotated = self._rotate_if_needed()
            s = self._session
            payload = {
                "schema": SCHEMA,
                "seq": s["seq"],
                "ts": now_iso(),
                "assistant_id": self.assistant_id,
                "session_id": s["session_id"],
                "event": event,
                "pid": os.getpid(),
                "chain_sha16": s["chain"],
            }
            payload.update(fields)
            line_str, data = self._append_line(s["path"], payload)
            s["chain"] = sha16(line_str)
            s["seq"] += 1
            s["lines"] += 1
            s["bytes"] += len(data)
            s["events"] += 1
            self._daily_append(payload)
            if event == "session_end":
                try:
                    with open(s["path"], "ab") as _f:
                        _fsync(_f)
                except Exception:                    # noqa: BLE001
                    pass
            if event in ("error", "warning", "crash_recovered"):
                self._incident_append(payload)
            if rotated:
                self._incident_append({"ts": payload.get("ts"), "event": "rotation",
                                       "session_id": s["session_id"], "seq": s["seq"],
                                       "severity": "info", "message": "rotated to %s"
                                       % s["path"]})
            self._audit_update(s)
            return payload

    def _daily_append(self, payload):
        # 日索引只放子集（事件/延迟/错误），任何模式都不放原文
        daily = {"schema": DAILY_SCHEMA, "ts": payload.get("ts"),
                 "seq": payload.get("seq"), "session_id": payload.get("session_id"),
                 "event": payload.get("event")}
        for k in ("latency_ms", "error_code", "refused", "reason", "deleted_count",
                  "count", "block_ids"):
            if k in payload:
                daily[k] = payload[k]
        path = os.path.join(self.daily_dir, today_str() + ".jsonl")
        with self._lock:
            self._append_line(path, daily)

    def _incident_append(self, payload):
        sev = "fatal" if payload.get("event") == "error" and payload.get("fatal") else (
            "error" if payload.get("event") == "error" else
            "warn" if payload.get("event") == "warning" else "info")
        rec = {"schema": DAILY_SCHEMA, "ts": payload.get("ts"),
               "session_id": payload.get("session_id"), "seq": payload.get("seq"),
               "event": payload.get("event"), "severity": sev,
               "code": payload.get("code"), "message": payload.get("message"),
               "where": payload.get("where"), "stack": payload.get("stack"),
               "last_seq": payload.get("last_seq"),
               "last_event": payload.get("last_event")}
        with self._lock:
            self._append_line(self.incidents_path, rec)

    def _audit_update(self, s):
        audit = {"schema": AUDIT_SCHEMA, "assistant_id": self.assistant_id,
                 "session_id": s["session_id"], "last_seq": s["seq"] - 1,
                 "last_chain_sha16": s["chain"], "lines_total": s["lines"],
                 "last_write_ts": now_iso(), "path": s["path"]}
        old = {}
        try:
            if os.path.exists(self.audit_path):
                with open(self.audit_path, encoding="utf-8") as f:
                    old = json.load(f)
        except (OSError, ValueError):
            old = {}
        audit["lines_all_sessions"] = int(old.get("lines_all_sessions", 0)) + 1
        tmp = self.audit_path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(audit, f, ensure_ascii=False, indent=1)
            f.write("\n")
            f.flush()
            if LOG_FSYNC:
                _fsync(f)
        os.replace(tmp, self.audit_path)

    # -- 高层事件（带隐私策略）------------------------------------------
    def log_ask(self, text, session_tokens=None, session_id=None, extra=None):
        out, h, n = scrub(text, self.mode)
        fields = {"input_sha16": h, "input_len": n}
        if self.mode != "hash_only":
            fields["input_text"] = out
        if session_tokens is not None:
            fields["session_tokens"] = int(session_tokens)
        if extra:
            fields.update(extra)
        return self.event("ask", **fields)

    def log_answer(self, answer, ask_seq, block_ids, engine, latency_ms, vram_gib=None,
                   refused=False, extra=None):
        out, h, n = scrub(answer, self.mode)
        fields = {"ask_seq": int(ask_seq), "answer_sha16": h, "answer_len": n,
                  "latency_ms": round(float(latency_ms), 1),
                  "block_ids": list(block_ids or []),
                  "engine": engine or {},
                  "vram_gib": vram_gib,
                  "tokens_out": n}
        if self.mode != "hash_only":
            fields["answer_text"] = out
        if extra:
            fields.update(extra)
        return self.event("answer", **fields)

    def log_refuse(self, reason, ask_seq, text=None, latency_ms=None, extra=None):
        fields = {"reason": reason, "ask_seq": int(ask_seq)}
        if latency_ms is not None:
            fields["latency_ms"] = round(float(latency_ms), 1)
        if text is not None and self.mode != "hash_only":
            out, h, n = scrub(text, self.mode)
            fields["reply_sha16"] = h
            fields["reply_text"] = out
        if extra:
            fields.update(extra)
        return self.event("refuse", **fields)

    def log_error(self, code, message, stack=None, where=None, fatal=False):
        return self.event("error", code=str(code), message=str(message),
                          stack=stack, where=where, fatal=bool(fatal))

    def log_warning(self, code, message, evidence=None):
        return self.event("warning", code=str(code), message=str(message),
                          evidence=evidence)

    def session_end(self, reason="user_quit", n_events=None):
        return self.event("session_end", reason=str(reason),
                          duration_s=round(time.time() - self._session["started"], 1),
                          n_events=int(n_events if n_events is not None
                                       else self._session["events"]))

    # -- 只读辅助 ---------------------------------------------------------
    def tail(self, n=20, session_id=None):
        path = self._path_for(session_id)
        if not path or not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        return [json.loads(x) for x in lines[-n:] if x.strip()]

    def _path_for(self, session_id=None):
        if session_id is None:
            return self._session["path"]
        return os.path.join(self.sessions_dir, session_id + ".jsonl")

    # -- purge -----------------------------------------------------------
    def purge(self, what="all", before_date=None):
        """删除日志文件（**仅用户显式命令**；append-only 不变式针对常规写入）。"""
        removed = []
        with self._lock:
            if what == "all":
                for p in _iter_text_files(self.sessions_dir) + _iter_text_files(self.daily_dir):
                    try:
                        os.remove(p)
                        removed.append(p)
                    except OSError:
                        pass
                for p in (self.incidents_path, self.audit_path):
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                            removed.append(p)
                        except OSError:
                            pass
                self._session = self._blank_session(self._new_session_id())
            else:
                cutoff = str(before_date or "")
                for p in _iter_text_files(self.sessions_dir) + _iter_text_files(self.daily_dir):
                    name = os.path.basename(p)
                    if cutoff and name[:10] >= cutoff:
                        continue
                    try:
                        os.remove(p)
                        removed.append(p)
                    except OSError:
                        pass
        return {"removed": len(removed), "files": [os.path.basename(x) for x in removed]}


def sha16_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def count_lines(path):
    n = 0
    with open(path, "rb") as f:
        for _ in f:
            n += 1
    return n


def read_last_line(path):
    last = None
    try:
        with open(path, "rb") as f:
            for raw in f:
                if raw.strip():
                    last = raw
    except OSError:
        return None
    if not last:
        return None
    try:
        return json.loads(last.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None


def last_raw_line(path):
    last = b""
    with open(path, "rb") as f:
        for raw in f:
            if raw.strip():
                last = raw
    return last.rstrip(b"\r\n").decode("utf-8", "replace")


def read_session(path):
    rows = []
    with open(path, "rb") as f:
        for i, raw in enumerate(f, start=1):
            try:
                rows.append((i, raw, json.loads(raw.decode("utf-8"))))
            except (UnicodeDecodeError, ValueError) as exc:
                rows.append((i, raw, {"__parse_error__": str(exc)}))
    return rows


def main():
    import argparse
    ap = argparse.ArgumentParser(description="assistant log self-check (CPU only)")
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--new-session", action="store_true")
    a = ap.parse_args()
    log = AssistantLog(root=a.root, create_session=a.new_session)
    print("assistant_id=%s session=%s mode=%s"
          % (log.assistant_id, log.current_session_id(), log.mode))
    print("root=%s" % log.root)
    return 0


if __name__ == "__main__":
    sys.exit(main())