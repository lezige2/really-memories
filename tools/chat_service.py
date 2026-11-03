# -*- coding: utf-8 -*-
"""chat_service.py -- C 版本地 HTTP 服务（桌面端 / QQ 适配器共用）。

定位
----
`tools/chat_daily.py` 是交互 REPL；本文件只做**传输层**：把同一套 DailyApp API
暴露成 127.0.0.1 上的 JSON 服务。引擎、记忆、会话逻辑全部复用 chat_daily，不复制。

硬约束（对应 LEAD 追加要求）
----------------------------
* 只绑 127.0.0.1（默认端口 8765）；非回环地址启动直接拒绝。
* **单线程串行排队**：GPU 只有一张，禁止并发推理。HTTPServer 本身串行，再加一把
  `threading.Lock` 显式排队；`/status` 暴露 in_flight_max（预期恒为 1）。
* 请求带超时：半开/慢客户端在 `--read-timeout` 秒后被读侧超时关闭；响应里不会
  出现未捕获异常——任何错误都返回 `{"error":{"code":..,"message":..}}`。
* 可注入引擎：`--fake-engine` 用 chat_daily.StubEngine（零 GPU，CPU 测试用）；
  真实模式才 `import kvslots`（见 chat_daily.make_real_engine），本文件不直接碰引擎。
* 无鉴权（本机单用户），**不要暴露公网**；远程使用须自行加 token/TLS，属后续工作。

端点（JSON in / out，UTF-8，indent=1）
-------------------------------------
  GET  /health              -> {status, model_pin, dll_pin, vram_gib, memories, session, service}
  POST /ask      {text}     -> {answer, block_ids, latency_s, refused, state}
  POST /remember {text}     -> {id, len_tokens, created_at}
  GET  /memories            -> [{id, first_line, len, created_at, n_tokens}]
  POST /forget   {id|"all"} -> {deleted}
  POST /save     {path?}    -> {path, sha16}
  POST /load     {path?}    -> {path, sha16}
  GET  /status              -> 资源 / 记忆 / 会话 / 服务

运行：
  python -X utf8 tools/chat_service.py                     # 真实引擎（需模型与 GPU）
  python -X utf8 tools/chat_service.py --fake-engine       # 零 GPU 自测
"""

import argparse
import json
import os
import signal
import socket
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import chat_daily as D          # noqa: E402  (CPU 安全；真实引擎仍只在 make_real_engine 里 import)
import assistant_log as alog    # noqa: E402  (个体日志：服务端每个动作都落日志)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                     # noqa: BLE001
    pass

SERVICE_VERSION = "c-service-1.0"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
MAX_BODY = 1 << 20          # 1 MiB
FAKE_DATA_DEFAULT = os.path.join(D.ROOT, "kvmem", "_service_fake")
SERVICE_MODEL_ID = "local-14b-memory"
SERVICE_OWNER = "llama-mem"
CONTEXT_WINDOW = D.N_CTX

_ERR_HTTP = {
    "bad_request": 400,
    "too_many_blocks": 400,
    "not_found": 404,
    "memory_full": 409,
    "chat_full": 409,
    "conflict": 409,
    "timeout": 504,
    "internal": 500,
    "unavailable": 503,
    "method_not_allowed": 405,
    "queue_timeout": 429,
    "ask_timeout": 503,
    "service_degraded": 503,
    "model_error": 500,
}

# OpenAI 兼容错误 type 映射（错误体 {"error":{"message","type","code"}}）
_OPENAI_TYPE = {
    "bad_request": "invalid_request_error",
    "too_many_blocks": "invalid_request_error",
    "not_found": "invalid_request_error",
    "method_not_allowed": "invalid_request_error",
    "conflict": "invalid_request_error",
    "memory_full": "invalid_request_error",
    "chat_full": "invalid_request_error",
    "queue_timeout": "rate_limit_error",
    "model_error": "server_error",
    "internal": "server_error",
    "unavailable": "server_error",
}


class Service:
    """串行请求队列 + 统一异常映射；真正的业务全在 DailyApp。"""

    def __init__(self, app, host, port, read_timeout=30.0, queue_timeout=30.0):
        self.app = app
        self.queue_timeout = float(queue_timeout)
        self.host = host
        self.port = port
        self.read_timeout = float(read_timeout)
        self.lock = threading.Lock()
        self.started_at = time.time()
        self.requests = 0
        self.in_flight = 0
        self.in_flight_max = 0
        self.by_route = {}
        try:
            self.ask_timeout = float(os.environ.get("LLAMA_MEM_ASK_TIMEOUT", "90"))
        except ValueError:
            self.ask_timeout = 90.0
        self.degraded = False
        self._worker = None

    # -- 统一调用入口：任何动作都在锁内串行执行 ---------------------------
    def call(self, route, fn, timeout=None):
        wait = self.queue_timeout if timeout is None else float(timeout)
        if not self.lock.acquire(timeout=wait):
            raise D.DailyError("queue_timeout",
                               "GPU 串行队列已占用超过 %.1fs，请稍后重试" % wait)
        try:
            self.requests += 1
            self.by_route[route] = self.by_route.get(route, 0) + 1
            self.in_flight += 1
            self.in_flight_max = max(self.in_flight_max, self.in_flight)
            try:
                return fn()
            finally:
                self.in_flight -= 1
        finally:
            self.lock.release()

    def service_info(self):
        return {"version": SERVICE_VERSION, "host": self.host, "port": self.port,
                "serial": True, "requests": self.requests,
                "in_flight_max": self.in_flight_max,
                "by_route": dict(self.by_route),
                "uptime_s": round(time.time() - self.started_at, 1),
                "fake_engine": getattr(self.app.eng, "mode", "real") != "real",
                "degraded": bool(self.degraded),
                "ask_timeout_s": self.ask_timeout}

    # -- 路由 -------------------------------------------------------------
    def dispatch(self, method, path, payload):
        app = self.app
        allowed = KNOWN_ROUTES.get(path)
        if allowed is not None and method not in allowed:
            raise D.DailyError("method_not_allowed",
                               "%s 只支持 %s" % (path, "/".join(allowed)))
        if method == "GET" and path == "/health":
            h = app.health()
            h["service"] = self.service_info()
            return h
        if method == "GET" and path == "/status":
            st = app.status()
            st["service"] = self.service_info()
            return st
        if method == "GET" and path == "/memories":
            return app.memories()
        if method == "POST" and path == "/ask":
            text = _req_text(payload, "text")
            if self.degraded:
                raise D.DailyError("service_degraded",
                                   "上一个 /ask 仍未收尾，服务降级中；请稍后重启服务")
            box, err = {}, []
            def _run():
                try:
                    box["r"] = app.ask(text)
                except Exception as exc:                 # noqa: BLE001
                    err.append(exc)
                finally:
                    self.degraded = False
            th = threading.Thread(target=_run, daemon=True)
            self._worker = th
            self.degraded = True
            th.start()
            th.join(max(0.05, float(self.ask_timeout)))
            if th.is_alive():
                self.degraded = True
                try:
                    if app.logger:
                        app.logger.log_error(
                            "ask_timeout", "ask 超过 %.0fs 未返回，返回 503"
                            % self.ask_timeout, where="service:POST /ask")
                except Exception:                        # noqa: BLE001
                    pass
                raise D.DailyError("ask_timeout",
                                   "请求超过 %.0fs 未返回，已返回 503；worker 仍在收尾"
                                   % self.ask_timeout)
            self.degraded = False
            if err:
                raise err[0]
            r = box.get("r")
            if r is None:
                raise D.DailyError("internal", "ask worker 无结果")
            r["session"] = app.session_path
            return r
        if method == "POST" and path == "/remember":
            text = _req_text(payload, "text")
            r = app.remember(text, confirm_token=payload.get("confirm_token"))
            out = {"id": r.get("id"), "len_tokens": r.get("n_tokens"),
                   "created_at": r.get("created_at"), "duplicate": r.get("duplicate")}
            for k in ("needs_confirmation", "confirm_token", "reason",
                      "candidates", "expires_in", "restated",
                      "restated_count", "last_restated_at"):
                if k in r:
                    out[k] = r[k]                    # 只加字段，不改旧字段/状态码
            return out
        if method == "POST" and path == "/reset":
            r = app.reset_session()
            return {"reset": True, "chat_tokens": int(r.get("chat_tokens") or 0)}
        if method == "POST" and path == "/forget":
            if "id" not in payload:
                raise D.DailyError("bad_request", "缺少字段 id（数字或 \"all\"）")
            r = app.forget(payload["id"])
            return {"deleted": r["deleted"], "ids": r["ids"],
                    "dialogue_reset": r.get("dialogue_reset", False)}
        if method == "POST" and path == "/save":
            path = payload.get("path") or None
            r = app.save(path)
            return {"path": r["path"], "sha16": r["sha16"]}
        if method == "POST" and path == "/load":
            path = payload.get("path") or None
            r = app.load(path)
            return {"path": r["path"], "sha16": r["sha16"]}
        raise D.DailyError("not_found", "未知端点：%s %s" % (method, path))


def _req_text(payload, field):
    v = payload.get(field)
    if not isinstance(v, str) or not v.strip():
        raise D.DailyError("bad_request", "字段 %s 必须是非空字符串" % field)
    return v


def estimate_tokens(text):
    """粗估 token（CJK 约 2 字符/token）；只用于预算与 usage，不参与判据。"""
    return max(1, (len(str(text or "")) + 1) // 2)


def extract_last_user(messages):
    """OpenAI messages[] -> (最后一条 user 文本, 全部文本长度)。content 可为字符串或分块数组。"""
    if not isinstance(messages, list) or not messages:
        raise D.DailyError("bad_request", "messages 必须是非空数组")
    last = None
    total = 0
    for m in messages:
        if not isinstance(m, dict):
            continue
        content = m.get("content")
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
            content = "".join(parts)
        if not isinstance(content, str):
            content = ""
        total += len(content)
        if m.get("role") == "user":
            last = content
    if last is None or not last.strip():
        raise D.DailyError("bad_request", "messages 里没有可用的 user 文本")
    return last, total


def openai_error(exc):
    code = getattr(exc, "code", "internal")
    return {"error": {"message": getattr(exc, "message", str(exc)),
                      "type": _OPENAI_TYPE.get(code, "server_error"),
                      "code": code}}


class Handler(BaseHTTPRequestHandler):
    server_version = "chat_service/" + SERVICE_VERSION
    protocol_version = "HTTP/1.1"
    timeout = 30.0        # 读侧超时（由 --read-timeout 覆盖）

    # -- 基础设施 ---------------------------------------------------------
    def log_message(self, fmt, *args):
        sys.stderr.write("[service] %s %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, code, obj):
        body = (json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            sid = getattr(self, "x_session_id", None)
            if sid:
                self.send_header("X-Session-Id", sid)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _send_error(self, code, err_code, message):
        self._send_json(code, {"error": {"code": err_code, "message": message}})

    def _read_payload(self):
        raw_len = self.headers.get("Content-Length")
        if raw_len is None:
            return {}
        try:
            n = int(raw_len)
        except ValueError:
            raise D.DailyError("bad_request", "Content-Length 非法")
        if n < 0 or n > self.server.max_body:
            raise D.DailyError("bad_request", "请求体过大（上限 %d 字节）" % self.server.max_body)
        body = self.rfile.read(n)
        if not body:
            return {}
        try:
            obj = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise D.DailyError("bad_request", "请求体不是合法 UTF-8 JSON：%s" % exc)
        if not isinstance(obj, dict):
            raise D.DailyError("bad_request", "请求体必须是 JSON 对象")
        return obj

    # -- 请求入口：GET 无体 / POST 读体；所有异常都在这里兜住 ----------------
    def _handle(self, method):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            self._apply_session_header()
            payload = self._read_payload() if method == "POST" else {}
            result = self.server.service.call(
                "%s %s" % (method, path),
                lambda: self.server.service.dispatch(method, path, payload))
            self._send_json(200, result)
        except D.DailyError as exc:
            app = self.server.app
            if app.logger and exc.code != "queue_timeout":
                app.logger.log_error(exc.code, exc.message, where="service:%s %s"
                                     % (method, path))
            self._send_error(_ERR_HTTP.get(exc.code, 400), exc.code, exc.message)
        except Exception as exc:                            # noqa: BLE001  不崩进程
            app = self.server.app
            if app.logger:
                import traceback
                app.logger.log_error("internal", str(exc), stack=traceback.format_exc(),
                                     where="service:%s %s" % (method, path))
            self._send_error(500, "internal", "%s: %s" % (type(exc).__name__, exc))

    # -- OpenAI 兼容层：/v1/models 与 /v1/chat/completions -----------------
    def _apply_session_header(self):
        sid = (self.headers.get("X-Session-Id") or "").strip() or None
        self.x_session_id = sid
        if sid:
            app = self.server.app
            if app.logger and app.logger.current_session_id() != sid:
                app.log_session(sid)
            self.x_session_id = app.logger.current_session_id() if app.logger else sid
        else:
            app = self.server.app
            self.x_session_id = app.logger.current_session_id() if app.logger else None

    def _models_payload(self):
        return {"object": "list",
                "data": [{"id": SERVICE_MODEL_ID, "object": "model",
                          "owned_by": SERVICE_OWNER,
                          "context_window": int(getattr(self.server.app, "n_ctx",
                                                        CONTEXT_WINDOW)),
                          "created": 0}]}

    def _chat_action(self, payload, text, prompt_tokens):
        """记忆逻辑在服务端：只取最后一条 user 文本；记忆不拼进 prompt。"""
        app = self.server.app
        for pfx in ("记住：", "记一下：", "/remember "):
            if text.startswith(pfx):
                body = text[len(pfx):].strip()
                r = app.remember(body)
                return {"content": "已记住（id=%d，%d token）"
                                   % (r["id"], r.get("n_tokens") or 0),
                        "block_ids": [r["id"]], "refused": False,
                        "latency_s": 0.0, "state": "remember", "remember": True}
        r = app.ask(text)
        # 双保险：统一走 chat_daily.clean_answer（剥 think 标签 / 指令回显 / 续写问答模板），
        # 服务端绝不把思考段或模板残留吐给客户端。
        return {"content": D.clean_answer(r["answer"]), "block_ids": r["block_ids"],
                "refused": r["refused"], "latency_s": r["latency_s"],
                "state": r.get("state"), "remember": False,
                "notice": r.get("notice"), "rollover": r.get("rollover")}

    def _completion_body(self, res, payload, prompt_tokens):
        content = res["content"]
        completion_tokens = estimate_tokens(content)
        cid = "chatcmpl-" + uuid.uuid4().hex[:24]
        created = int(time.time())
        return {"id": cid, "object": "chat.completion", "created": created,
                "model": payload.get("model") or SERVICE_MODEL_ID,
                "choices": [{"index": 0,
                             "message": {"role": "assistant", "content": content},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": prompt_tokens,
                          "completion_tokens": completion_tokens,
                          "total_tokens": prompt_tokens + completion_tokens},
                "system_fingerprint": "llama-mem-c1",
                "x_memory": {"block_ids": res.get("block_ids") or [],
                             "refused": bool(res.get("refused")),
                             "remember": bool(res.get("remember"))},
                "x_notice": res.get("notice")}

    def _handle_chat_completions(self):
        try:
            payload = self._read_payload()
            if not isinstance(payload.get("messages"), list):
                raise D.DailyError("bad_request", "缺少 messages 数组")
            self._apply_session_header()
            text, total_len = extract_last_user(payload.get("messages"))
            used = int(self.server.app.eng.n_tokens(0))
            budget_tokens = max(64, int(self.server.app.chat_budget) - used
                                - int(payload.get("max_tokens") or D.N_PREDICT_DEFAULT)
                                - 128)
            budget_chars = budget_tokens * 2
            truncated = len(text) > budget_chars
            note = None
            if truncated:
                note = {"kept_chars": budget_chars, "orig_chars": len(text),
                        "orig_messages_chars": total_len,
                        "budget_tokens": budget_tokens}
                app = self.server.app
                if app.logger:
                    app.logger.log_warning(
                        "prompt_truncated",
                        "OpenAI 请求文本超过 chat 窗口预算，已截断（未静默丢弃）",
                        evidence=note)
                text = text[:budget_chars]
            prompt_tokens = estimate_tokens(text)
            res = self.server.service.call(
                "POST /v1/chat/completions",
                lambda: self._chat_action(payload, text, prompt_tokens))
            if bool(payload.get("stream")):
                self._send_sse(self._completion_body(res, payload, prompt_tokens),
                               res["content"])
            else:
                self._send_json(200, self._completion_body(res, payload, prompt_tokens))
        except D.DailyError as exc:
            self._send_json(429 if exc.code == "queue_timeout"
                            else _ERR_HTTP.get(exc.code, 400), openai_error(exc))
        except Exception as exc:                            # noqa: BLE001  不崩进程
            app = self.server.app
            if app.logger:
                import traceback
                app.logger.log_error("internal", str(exc),
                                     stack=traceback.format_exc(),
                                     where="openai.chat_completions")
            self._send_json(500, {"error": {"message": "%s: %s"
                                            % (type(exc).__name__, exc),
                                            "type": "server_error",
                                            "code": "internal"}})

    def _send_sse(self, body, content):
        """SSE：逐块 delta.content，最后 finish_reason=stop + [DONE]。"""
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            sid = getattr(self, "x_session_id", None)
            if sid:
                self.send_header("X-Session-Id", sid)
            self.end_headers()
            base = {"id": body["id"], "object": "chat.completion.chunk",
                    "created": body["created"], "model": body["model"]}
            step = 10
            for i in range(0, len(content), step):
                chunk = dict(base)
                chunk["choices"] = [{"index": 0,
                                     "delta": {"content": content[i:i + step]},
                                     "finish_reason": None}]
                self.wfile.write(("data: " + json.dumps(chunk, ensure_ascii=False)
                                  + "\n\n").encode("utf-8"))
                self.wfile.flush()
            final = dict(base)
            final["choices"] = [{"index": 0, "delta": {},
                                 "finish_reason": "stop"}]
            self.wfile.write(("data: " + json.dumps(final, ensure_ascii=False)
                              + "\n\n").encode("utf-8"))
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def handle_one_request(self):
        """慢客户端/半开连接：读超时只关连接，不打印 Python traceback。"""
        try:
            super().handle_one_request()
        except (socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
            self.close_connection = True
            try:
                sys.stderr.write("[service] closed slow/idle client: %s\n"
                                 % type(exc).__name__)
            except Exception:                            # noqa: BLE001
                pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/v1/models":
            self._send_json(200, self._models_payload())
            return
        self._handle("GET")

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/v1/chat/completions":
            self._handle_chat_completions()
            return
        self._handle("POST")

    def do_PUT(self):
        self._send_error(405, "method_not_allowed", "只支持 GET/POST")

    do_DELETE = do_PATCH = do_PUT


class ServiceHTTPServer(HTTPServer):
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        """未捕获异常的兜底：不打印 traceback（会进服务日志），只留一行告警。"""
        import traceback
        sys.stderr.write("[service] request error from %r: %s\n"
                         % (client_address,
                            traceback.format_exc(limit=2).splitlines()[-1]))

    def __init__(self, addr, service, max_body=MAX_BODY):
        self.service = service
        self.app = service.app
        self.max_body = int(max_body)
        super().__init__(addr, Handler)


KNOWN_ROUTES = {
    "/health": ("GET",), "/status": ("GET",), "/memories": ("GET",),
    "/ask": ("POST",), "/remember": ("POST",), "/forget": ("POST",),
    "/reset": ("POST",),
    "/save": ("POST",), "/load": ("POST",),
    "/v1/models": ("GET",), "/v1/chat/completions": ("POST",),
}


def build_app(args, data):
    """按模式构造 DailyApp：fake = StubEngine + 占位模型；real = 真实引擎。"""
    if args.fake_engine:
        model = os.path.join(data, "model.stub")
        D.install_fake_model(model)
        eng = D.StubEngine()
        db = args.db or os.path.join(data, "daily.db")
        blocks = args.blocks or os.path.join(data, "blocks")
        sessions = args.sessions or os.path.join(data, "sessions")
    else:
        model = args.model or D.MODEL
        if not os.path.exists(model):
            raise SystemExit("error: 模型不存在：%s" % model)
        eng = D.make_real_engine(model, n_ctx=getattr(args, "n_ctx", D.N_CTX_DEFAULT),
                                 n_gpu_layers=getattr(args, "n_gpu_layers",
                                                      D.N_GPU_LAYERS_DEFAULT))
        db = args.db or D.DB_DEFAULT
        blocks = args.blocks or D.BLOCKS_DEFAULT
        sessions = args.sessions or D.SESSIONS_DEFAULT
    return D.DailyApp(eng, db_path=db, blocks_dir=blocks, sessions_dir=sessions,
                      session_path=args.session, model_path=model,
                      control=args.control, n_predict=args.n_predict,
                      retrieval_mode=getattr(args, "retrieval", "off"),
                      k2_family=bool(getattr(args, "k2_family", False)),
                      event_date=bool(getattr(args, "event_date", False)),
                      query_expand=bool(getattr(args, "query_expand", False)),
                      confirm_writes=bool(getattr(args, "confirm_writes", False)),
                      p1b_subject=bool(getattr(args, "p1b_subject", False)),
                      tts=bool(getattr(args, "tts", False)),
                      tts_speak=bool(getattr(args, "tts_speak", False)),
                      tts_timeout=int(getattr(args, "tts_timeout", 20)),
                      assistant_memory=bool(getattr(args, "assistant_memory", False)),
                      norm_dedup=bool(getattr(args, "norm_dedup", False)),
                      json_output=bool(getattr(args, "json_output", False)),
                      dedup_shadow=bool(getattr(args, "dedup_shadow", False)),
                      meta_answer=bool(getattr(args, "meta_answer", True)),
                      lifecycle_cap=bool(getattr(args, "lifecycle_cap", False)),
                      memory_access=bool(getattr(args, "memory_access", False)),
                      topk=getattr(args, "topk", D.DEFAULT_TOPK),
                      rollover_at=getattr(args, "rollover_at", D.ROLLOVER_AT_DEFAULT),
                      n_ctx=getattr(args, "n_ctx", D.N_CTX_DEFAULT),
                      chat_start=getattr(args, "chat_start", D.CHAT_START_DEFAULT),
                      n_gpu_layers=getattr(args, "n_gpu_layers",
                                           D.N_GPU_LAYERS_DEFAULT))


def main(argv=None):
    ap = argparse.ArgumentParser(description="C 版本地记忆服务（HTTP/127.0.0.1）")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--fake-engine", action="store_true",
                    help="零 GPU：StubEngine（CPU 测试用，不加载模型）")
    ap.add_argument("--data-dir", default=None,
                    help="fake 模式的数据根目录（默认 kvmem/_service_fake）")
    ap.add_argument("--db", default=None)
    ap.add_argument("--blocks", default=None)
    ap.add_argument("--sessions", default=None)
    ap.add_argument("--session", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--n-predict", type=int, default=D.N_PREDICT_DEFAULT)
    ap.add_argument("--control", action="store_true", help="不挂载长期记忆（对照臂）")
    ap.add_argument("--retrieval", choices=["off", "topk"], default="off",
                    help="挂载模式：off=全部挂载；topk=每问只挂最相关 topk 条")
    ap.add_argument("--k2-family", action="store_true", default=False,
                    help="K2 同族只留最新（默认关；与 chat_daily 同名同义）")
    ap.add_argument("--event-date", action="store_true", default=False,
                    help="P0 event_date（默认关；与 chat_daily 同名同义）")
    ap.add_argument("--query-expand", action="store_true", default=False,
                    help="S2-A query expansion（默认关；与 chat_daily 同名同义）")
    ap.add_argument("--confirm-writes", action="store_true", default=False,
                    help="显式冲突写入需 confirm token（默认关；与 chat_daily 同名同义）")
    ap.add_argument("--p1b-subject", action="store_true", default=False,
                    help="P1b 主体键软覆盖（默认关；与 chat_daily 同名同义）")
    # do-not-enable-for-merge: diagnostic only
    ap.add_argument("--lifecycle-cap", action="store_true", default=False,
                    help="P1 软/硬上限（默认关；与 chat_daily 同名同义）")
    ap.add_argument("--memory-access", action="store_true", default=False,
                    help="P1 access 记录（默认关；与 chat_daily 同名同义）")
    ap.add_argument("--meta-answer", action=argparse.BooleanOptionalAction,
                    default=True,
                    help="meta-v1 计数回答（默认开；--no-meta-answer 回滚）")
    ap.add_argument("--dedup-shadow", action="store_true", default=False,
                    help="影子去重（默认关；仅诊断，不合并）")
    ap.add_argument("--json-output", action="store_true", default=False,
                    help="强制记忆类回答 JSON（默认关；与 chat_daily 同名同义）")
    ap.add_argument("--norm-dedup", action="store_true", default=False,
                    help="norm_hash 去重（默认关；与 chat_daily 同名同义）")
    ap.add_argument("--assistant-memory", action="store_true", default=False,
                    help="P3 助手显式承诺写入（默认关；与 chat_daily 同名同义）")
    ap.add_argument("--tts", action="store_true", default=False,
                    help="最终答案异步 TTS（默认关；与 chat_daily 同名同义）")
    ap.add_argument("--tts-speak", action="store_true", default=False,
                    help="TTS 本机播放（默认关）")
    ap.add_argument("--tts-timeout", type=int, default=20)
    ap.add_argument("--topk", type=int, default=D.DEFAULT_TOPK,
                    help="topk 模式每问挂载条数（1..%d）" % D.MAX_MEMORIES)
    ap.add_argument("--rollover-at", type=float, default=D.ROLLOVER_AT_DEFAULT,
                    help="对话窗占用达该比例时自动压缩（1.0 关闭）")
    ap.add_argument("--n-ctx", type=int, default=D.N_CTX_DEFAULT,
                    help="上下文长度（默认 %d）" % D.N_CTX_DEFAULT)
    ap.add_argument("--chat-start", type=int, default=D.CHAT_START_DEFAULT,
                    help="对话起点/记忆区上界（默认 %d）" % D.CHAT_START_DEFAULT)
    ap.add_argument("--n-gpu-layers", type=int, default=D.N_GPU_LAYERS_DEFAULT,
                    help="GPU 层数（默认 %d）" % D.N_GPU_LAYERS_DEFAULT)
    ap.add_argument("--read-timeout", type=float, default=30.0,
                    help="单请求读超时（秒）；慢客户端会被断开")
    ap.add_argument("--queue-timeout", type=float, default=30.0,
                    help="GPU 串行队列等待上限（秒）；超时返回 429 queue_timeout")
    ap.add_argument("--max-body", type=int, default=MAX_BODY)
    args = ap.parse_args(argv)

    if args.host not in LOOPBACK:
        print("error: 只允许绑定回环地址 %s（拒绝 %r）；远程访问须先加鉴权/隧道"
              % (sorted(LOOPBACK), args.host))
        return 2
    if not (1 <= args.port <= 65535):
        print("error: 端口非法：%r" % args.port)
        return 2

    data = args.data_dir or (FAKE_DATA_DEFAULT if args.fake_engine else None)
    if args.fake_engine:
        data = os.path.abspath(data)
        os.makedirs(data, exist_ok=True)
    try:
        app = build_app(args, data)
    except SystemExit as exc:
        print(exc)
        return 2
    except D.DailyError as exc:
        print("error[%s]: %s" % (exc.code, exc.message))
        return 1
    except Exception as exc:                                # noqa: BLE001
        print("error: %s" % exc)
        return 1

    service = Service(app, args.host, args.port, read_timeout=args.read_timeout,
                      queue_timeout=args.queue_timeout)
    Handler.timeout = float(args.read_timeout)
    try:
        srv = ServiceHTTPServer((args.host, args.port), service, max_body=args.max_body)
    except OSError as exc:
        print("error: 端口 %d 绑定失败：%s" % (args.port, exc))
        app.close(save=False)
        return 1

    print("C 版记忆服务 v%s 已启动：http://%s:%d" % (SERVICE_VERSION, args.host, args.port))
    print("  引擎模式：%s；只绑回环、无鉴权、勿暴露公网" %
          ("fake/stub（零 GPU）" if args.fake_engine else "real（需模型/GPU）"))
    print("  按下 Ctrl+C 停止（会尝试自动保存会话）")

    def _stop(_signum, _frame):
        raise KeyboardInterrupt()

    try:
        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)
    except (ValueError, OSError):
        pass

    rc = 0
    try:
        srv.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    except Exception as exc:                                # noqa: BLE001
        print("error: 服务循环异常：%s" % exc)
        rc = 1
    finally:
        try:
            srv.server_close()
        except Exception:                                   # noqa: BLE001
            pass
        try:
            service.call("shutdown", lambda: app.close(save=True))
        except Exception as exc:                            # noqa: BLE001
            print("[warn] 关闭时保存会话失败：%s" % exc)
        print("服务已停止。")
    return rc


if __name__ == "__main__":
    sys.exit(main())