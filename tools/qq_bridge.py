#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qq_bridge.py — 把本地助手 HTTP 服务接入 QQ（OneBot v11 / NapCat / Lagrange）。

设计要点
--------
* CPU-only、纯标准库（asyncio + urllib），不依赖 websockets/aiohttp，不联网。
* 支持 OneBot v11 反向 WebSocket 的两种接法（配置切换，非“二选一代码分支”）：
    - ``reverse``：本 bridge 起 WS 服务器，NapCat 主动连进来（NapCat「WebSocket 服务器」）；
    - ``forward``：本 bridge 主动连 NapCat 的 WS（NapCat「WebSocket 客户端」）。
* 收 QQ 消息 -> 调本地助手 ``/ask`` -> 回消息；命令 ``/remember``/``/memories``/
  ``/forget``/``/status``。
* 群聊仅在 @ 机器人 或 前缀 触发（可配）；单会话串行；超时/错误有回执；
  回答超长自动截断/分条。
* 不落盘敏感内容：``kvmem/qq_logs/`` 只记元数据（时间/群号/是否命中/命令名/错误类型），
  不写消息正文、不写回答正文。

OneBot v11 事件/动作字段依据（本文件实现所用子集）
--------------------------------------------------
事件（NapCat -> bridge，顶层 ``post_type == "message"``）：
    post_type   "message"
    message_type "group" | "private"
    sub_type    "normal" | "anonymous" | "friend" ...
    message_id  整数（回执/回复用）
    group_id    群号（group 事件必需）
    user_id     发送者 QQ 号
    self_id     机器人 QQ 号（判断 @ 是否为自己）
    time        事件时间戳（秒）
    raw_message 原始字符串（含 CQ 码；命令解析的兜底来源）
    message     OneBot v11 消息段数组，如
                [{"type":"at","data":{"qq":"123456"}},{"type":"text","data":{"text":" /status"}}]
    sender      发送者信息（nickname/card/role；仅用于日志脱敏，不落盘）
动作（bridge -> NapCat，JSON 文本帧）：
    {"action":"send_group_msg","params":{"group_id":<int>,"message":<str>,
                                        "auto_escape":false},"echo":"<id>"}
    {"action":"send_private_msg","params":{"user_id":<int>,"message":<str>},"echo":"<id>"}
    {"action":"get_login_info","params":{},"echo":"<id>"}
响应：{"status":"ok"|"failed","retcode":<int>,"data":{...},"echo":"<id>"}；
    ``status != "ok"`` 或 retcode 非 0 视为发送失败。
握手：反向 WS 的鉴权头 ``Authorization: Bearer <token>``，或查询串
    ``?access_token=<token>``（两者都接受，见 ``_extract_token``）。
依据：OneBot v11 规范（botuniverse/onebot-11）的 message 事件与 send_*_msg 动作；
本文件只用上述字段，不做 CQ 码解析之外的扩展。

退出码：0 正常；2 配置/参数错误；1 运行期致命错误。
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import ssl
import struct
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import parse_qs, quote, urlparse

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
OP_CONT, OP_TEXT, OP_BIN, OP_CLOSE, OP_PING, OP_PONG = 0x0, 0x1, 0x2, 0x8, 0x9, 0xA
MAX_HEADER_BYTES = 64 * 1024
MAX_FRAME_BYTES = 8 * 1024 * 1024

DEFAULT_CONFIG: dict[str, Any] = {
    "mode": "reverse",
    "ws_url": "ws://127.0.0.1:3001/?access_token=CHANGE_ME",
    "ws_host": "127.0.0.1",
    "ws_port": 8766,
    "token": "CHANGE_ME",
    "http_base": "http://127.0.0.1:8765",
    "trigger_mode": "at",           # at | prefix | both | none
    "prefix": "/",
    "allowed_groups": [],           # 空 = 所有群；写群号列表则仅这些群
    "admin_qq": [],                 # 空 = /remember /forget 所有人可用
    "timeout_s": 60.0,              # 单次 /ask 超时（30–120）
    "reply_max_chars": 600,
    "reply_max_parts": 4,
    "reply_split_at": "\n。；;!?！？ ",
    "log_dir": "kvmem/qq_logs",
    "reconnect_min_s": 1.0,
    "reconnect_max_s": 30.0,
    "reconnect_factor": 2.0,
    "http_timeout_s": 65.0,
    "verbose": False,
}


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def log(msg: str, verbose: bool = True) -> None:
    if verbose:
        sys.stderr.write(f"[qq_bridge {now_iso()}] {msg}\n")
        sys.stderr.flush()


def ws_accept_key(sec_key: str) -> str:
    digest = hashlib.sha1((sec_key + WS_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def encode_frame(opcode: int, payload: bytes = b"", fin: bool = True,
                 mask: bool = False) -> bytes:
    b1 = (0x80 if fin else 0x00) | (opcode & 0x0F)
    n = len(payload)
    if n < 126:
        b2 = n
    elif n < 65536:
        b2 = 126
    else:
        b2 = 127
    if mask:
        b2 |= 0x80
    out = bytearray([b1, b2])
    if b2 & 0x7F == 126:
        out += struct.pack("!H", n)
    elif b2 & 0x7F == 127:
        out += struct.pack("!Q", n)
    if mask:
        key = os.urandom(4)
        out += key
        out += bytes(c ^ key[i % 4] for i, c in enumerate(payload))
    else:
        out += payload
    return bytes(out)


async def read_frame(reader: asyncio.StreamReader) -> tuple[bool, int, bytes]:
    head = await reader.readexactly(2)
    b1, b2 = head[0], head[1]
    fin = bool(b1 & 0x80)
    opcode = b1 & 0x0F
    masked = bool(b2 & 0x80)
    length = b2 & 0x7F
    if length == 126:
        length = struct.unpack("!H", await reader.readexactly(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", await reader.readexactly(8))[0]
    if length > MAX_FRAME_BYTES:
        raise ConnectionError(f"frame too large: {length}")
    mask = await reader.readexactly(4) if masked else b""
    payload = await reader.readexactly(length) if length else b""
    if masked:
        payload = bytes(c ^ mask[i % 4] for i, c in enumerate(payload))
    return fin, opcode, payload


# --------------------------------------------------------------------------
# WebSocket 连接
# --------------------------------------------------------------------------
class WSConn:
    """极简 WebSocket 连接：文本帧 + ping/pong/close；按 echo 关联 OneBot 响应。"""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 verbose: bool = False) -> None:
        self.reader = reader
        self.writer = writer
        self.verbose = verbose
        self.closed = False
        self._pending: dict[str, asyncio.Future] = {}
        self._echo = 0
        self._send_lock = asyncio.Lock()
        self._last_rx = time.monotonic()
        self._tasks: set[asyncio.Task] = set()

    # -- 发送 ---------------------------------------------------------
    async def _send_frame(self, opcode: int, payload: bytes = b"") -> None:
        async with self._send_lock:
            if self.closed:
                raise ConnectionError("ws closed")
            self.writer.write(encode_frame(opcode, payload, mask=False))
            await self.writer.drain()

    async def send_text(self, text: str) -> None:
        await self._send_frame(OP_TEXT, text.encode("utf-8"))

    async def close(self, code: int = 1000) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            await self._send_frame(OP_CLOSE, struct.pack("!H", code))
        except Exception:
            pass
        for fut in list(self._pending.values()):
            if not fut.done():
                fut.set_exception(ConnectionError("ws closed"))
        self._pending.clear()
        try:
            self.writer.close()
        except Exception:
            pass

    # -- 接收 ---------------------------------------------------------
    async def recv_json(self, timeout: Optional[float] = None) -> Optional[dict]:
        """读一个 JSON 文本帧（内部处理 ping/close）；超时/断开返回 None。"""

        async def _inner() -> Optional[dict]:
            frag = bytearray()
            frag_op: Optional[int] = None
            while True:
                fin, opcode, payload = await read_frame(self.reader)
                self._last_rx = time.monotonic()
                if opcode == OP_CLOSE:
                    try:
                        await self._send_frame(OP_CLOSE, payload[:2])
                    except Exception:
                        pass
                    self.closed = True
                    return None
                if opcode == OP_PING:
                    await self._send_frame(OP_PONG, payload)
                    continue
                if opcode == OP_PONG:
                    continue
                if opcode == OP_BIN:
                    continue
                if opcode in (OP_TEXT, OP_CONT):
                    frag += payload
                    if len(frag) > MAX_FRAME_BYTES:
                        raise ConnectionError("message too large")
                    if opcode == OP_TEXT:
                        frag_op = OP_TEXT
                    if not fin:
                        continue
                    if frag_op is None:
                        continue
                    try:
                        return json.loads(frag.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        if self.verbose:
                            log("丢弃非 JSON 文本帧", True)
                        frag = bytearray()
                        frag_op = None
                        continue

        try:
            if timeout is None:
                return await _inner()
            return await asyncio.wait_for(_inner(), timeout)
        except (asyncio.IncompleteReadError, ConnectionError, asyncio.TimeoutError):
            self.closed = True
            return None

    # -- OneBot 动作 --------------------------------------------------
    async def call(self, action: str, params: Optional[dict] = None,
                   timeout: float = 10.0) -> dict:
        if self.closed:
            raise ConnectionError("ws closed")
        _, fut = self._register_pending()
        echo = self._last_echo_key
        payload = json.dumps({"action": action, "params": params or {}, "echo": echo},
                             ensure_ascii=False).encode("utf-8")
        await self._send_frame(OP_TEXT, payload)
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            self._pending.pop(echo, None)

    def _register_pending(self) -> tuple[str, asyncio.Future]:
        self._echo += 1
        echo = f"echo-{self._echo}"
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[echo] = fut
        self._last_echo_key = echo
        return echo, fut

    # -- 分发：响应 -> pending，事件 -> on_event ----------------------
    async def run(self, on_event: Callable[["WSConn", dict], Awaitable[None]]) -> None:
        while not self.closed:
            msg = await self.recv_json()
            if msg is None:
                return
            echo = msg.get("echo") if isinstance(msg, dict) else None
            if echo is not None and echo in self._pending:
                fut = self._pending.pop(echo)
                if not fut.done():
                    fut.set_result(msg)
                continue
            if isinstance(msg, dict) and "post_type" in msg:
                task = asyncio.create_task(on_event(self, msg))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)


async def _read_http_head(reader: asyncio.StreamReader) -> tuple[str, dict[str, str]]:
    raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10.0)
    if len(raw) > MAX_HEADER_BYTES:
        raise ConnectionError("http head too large")
    text = raw.decode("latin-1")
    lines = text.split("\r\n")
    first = lines[0].strip()
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line:
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        headers[k.strip().lower()] = v.strip()
    return first, headers


def _extract_token(path: str, headers: dict[str, str]) -> Optional[str]:
    parsed = urlparse(path)
    query = parse_qs(parsed.query)
    for key in ("access_token", "token"):
        if query.get(key):
            return query[key][0]
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


async def ws_accept(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                    token: str = "", require_token: bool = True,
                    allowed_paths: tuple[str, ...] = ("/", "/onebot", "/ws", "/qq"),
                    verbose: bool = False) -> Optional[WSConn]:
    """服务端握手。鉴权失败回 401，路径/协议不对回 400/404。"""
    try:
        request_line, headers = await _read_http_head(reader)
    except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionError):
        _safe_close(writer)
        return None
    parts = request_line.split(" ")
    if len(parts) < 2:
        return await _reject(writer, 400, "bad request line")
    method, raw_path = parts[0], parts[1]
    upgrade = headers.get("upgrade", "").lower()
    key = headers.get("sec-websocket-key")
    if method.upper() != "GET" or upgrade != "websocket" or not key:
        return await _reject(writer, 400, "not a websocket upgrade")
    parsed = urlparse(raw_path)
    if parsed.path not in allowed_paths:
        return await _reject(writer, 404, "path not allowed")
    if require_token and token:
        supplied = _extract_token(raw_path, headers)
        if supplied != token:
            if verbose:
                log(f"拒绝连接：token 不匹配（path={parsed.path}）")
            return await _reject(writer, 401, "bad token")
    writer.write(
        ("HTTP/1.1 101 Switching Protocols\r\n"
         "Upgrade: websocket\r\n"
         "Connection: Upgrade\r\n"
         f"Sec-WebSocket-Accept: {ws_accept_key(key)}\r\n\r\n").encode("ascii"))
    await writer.drain()
    if verbose:
        log(f"WS 已握手（{parsed.path}）")
    return WSConn(reader, writer, verbose=verbose)


async def _reject(writer: asyncio.StreamWriter, code: int, reason: str) -> None:
    body = reason.encode("utf-8")
    writer.write((f"HTTP/1.1 {code} {reason}\r\nContent-Length: {len(body)}\r\n"
                  "Connection: close\r\n\r\n").encode("latin-1") + body)
    try:
        await writer.drain()
    except Exception:
        pass
    _safe_close(writer)
    return None


def _safe_close(writer: asyncio.StreamWriter) -> None:
    try:
        writer.close()
    except Exception:
        pass


async def ws_connect(url: str, token: str = "", timeout: float = 10.0,
                     verbose: bool = False) -> WSConn:
    """客户端握手（bridge 主动连 NapCat 的 WS 时用）。仅 ws:// 与 wss://。"""
    parsed = urlparse(url)
    if parsed.scheme not in ("ws", "wss"):
        raise ValueError(f"unsupported ws url: {url}")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    path = parsed.path or "/"
    query = parsed.query
    if token and "access_token=" not in query:
        query = (query + "&" if query else "") + "access_token=" + quote(token, safe="")
    target = path + ("?" + query if query else "")
    ssl_ctx = ssl.create_default_context() if parsed.scheme == "wss" else None
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port, ssl=ssl_ctx), timeout)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    req = (f"GET {target} HTTP/1.1\r\n"
           f"Host: {host}:{port}\r\n"
           "Upgrade: websocket\r\n"
           "Connection: Upgrade\r\n"
           f"Sec-WebSocket-Key: {key}\r\n"
           "Sec-WebSocket-Version: 13\r\n"
           "User-Agent: qq_bridge/1.0\r\n\r\n")
    writer.write(req.encode("ascii"))
    await writer.drain()
    try:
        status_line, headers = await _read_http_head(reader)
    except Exception:
        _safe_close(writer)
        raise ConnectionError("ws handshake read failed")
    if " 101 " not in f" {status_line} ":
        _safe_close(writer)
        raise ConnectionError(f"ws handshake failed: {status_line}")
    if headers.get("sec-websocket-accept") != ws_accept_key(key):
        _safe_close(writer)
        raise ConnectionError("ws handshake accept mismatch")
    if verbose:
        log(f"WS 已连接 {url}")
    return WSConn(reader, writer, verbose=verbose)


# --------------------------------------------------------------------------
# 配置
# --------------------------------------------------------------------------
@dataclass
class BridgeConfig:
    mode: str = "reverse"
    ws_url: str = "ws://127.0.0.1:3001/?access_token=CHANGE_ME"
    ws_host: str = "127.0.0.1"
    ws_port: int = 8766
    token: str = "CHANGE_ME"
    http_base: str = "http://127.0.0.1:8765"
    trigger_mode: str = "at"
    prefix: str = "/"
    allowed_groups: list[int] = field(default_factory=list)
    admin_qq: list[int] = field(default_factory=list)
    timeout_s: float = 60.0
    reply_max_chars: int = 600
    reply_max_parts: int = 4
    reply_split_at: str = "\n。；;!?！？ "
    log_dir: str = "kvmem/qq_logs"
    reconnect_min_s: float = 1.0
    reconnect_max_s: float = 30.0
    reconnect_factor: float = 2.0
    http_timeout_s: float = 65.0
    verbose: bool = False

    def normalized(self) -> "BridgeConfig":
        self.mode = (self.mode or "reverse").lower()
        if self.mode not in ("reverse", "forward"):
            raise ValueError(f"mode must be reverse|forward, got {self.mode!r}")
        self.trigger_mode = (self.trigger_mode or "at").lower()
        if self.trigger_mode not in ("at", "prefix", "both", "none"):
            raise ValueError(f"trigger_mode must be at|prefix|both|none, got {self.trigger_mode!r}")
        self.timeout_s = float(self.timeout_s)
        # 允许测试用较小值；生产路径由 load_config() 钳到 30–120 s
        if not (0.05 <= self.timeout_s <= 600.0):
            raise ValueError("timeout_s out of range")
        self.reply_max_chars = max(40, int(self.reply_max_chars))
        self.reply_max_parts = max(1, int(self.reply_max_parts))
        self.reconnect_min_s = max(0.01, float(self.reconnect_min_s))
        self.reconnect_max_s = max(self.reconnect_min_s, float(self.reconnect_max_s))
        self.reconnect_factor = max(1.0, float(self.reconnect_factor))
        self.allowed_groups = [int(x) for x in self.allowed_groups]
        self.admin_qq = [int(x) for x in self.admin_qq]
        self.http_base = self.http_base.rstrip("/")
        return self


def load_config(path: Optional[str] = None, **overrides: Any) -> BridgeConfig:
    """JSON 配置 + 命令行覆盖。timeout 的 30–120 s 约束在这里体现（默认 60）。"""
    data = dict(DEFAULT_CONFIG)
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            data.update(json.load(fh))
    for key, value in overrides.items():
        if value is not None:
            data[key] = value
    known = set(BridgeConfig.__dataclass_fields__.keys())
    unknown = set(data) - known
    for key in unknown:
        data.pop(key, None)
    cfg = BridgeConfig(**{k: v for k, v in data.items() if k in known}).normalized()
    cfg.timeout_s = max(30.0, min(120.0, cfg.timeout_s))   # 30–120 s 运行约束
    return cfg


# --------------------------------------------------------------------------
# 本地助手 HTTP 客户端
# --------------------------------------------------------------------------
class AssistantError(Exception):
    def __init__(self, message: str, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class AssistantClient:
    base: str
    http_timeout_s: float = 65.0
    verbose: bool = False
    _opener: Any = None

    async def _request(self, method: str, path: str, payload: Optional[dict],
                       timeout: float) -> Any:
        url = self.base + path

        def _do() -> Any:
            data = None
            headers = {"Accept": "application/json"}
            if payload is not None:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                headers["Content-Type"] = "application/json; charset=utf-8"
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = resp.read()
                    status = resp.status
            except urllib.error.HTTPError as exc:
                body = exc.read() or b""
                raise AssistantError(
                    f"助手返回 HTTP {exc.code}: {body[:200].decode('utf-8', 'replace')}",
                    status=exc.code)
            except urllib.error.URLError as exc:
                raise AssistantError(f"连不上本地助手（{url}）：{exc.reason}")
            except TimeoutError:
                raise AssistantError(f"本地助手超时（{timeout:.0f}s）")
            try:
                return json.loads(body.decode("utf-8")) if body else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise AssistantError(f"本地助手返回非 JSON（HTTP {status}）")

        return await asyncio.wait_for(asyncio.to_thread(_do), timeout + 5.0)

    async def ask(self, text: str) -> dict:
        return await self._request("POST", "/ask", {"text": text}, self.http_timeout_s)

    async def remember(self, text: str) -> dict:
        return await self._request("POST", "/remember", {"text": text}, self.http_timeout_s)

    async def memories(self) -> Any:
        return await self._request("GET", "/memories", None, self.http_timeout_s)

    async def forget(self, memory_id: Any) -> dict:
        return await self._request("POST", "/forget", {"id": memory_id}, self.http_timeout_s)

    async def status(self) -> Any:
        return await self._request("GET", "/status", None, self.http_timeout_s)

    async def health(self) -> Any:
        return await self._request("GET", "/health", None, min(5.0, self.http_timeout_s))


# --------------------------------------------------------------------------
# 解析与格式化
# --------------------------------------------------------------------------
def message_text(event: dict) -> str:
    """事件 -> 纯文本（message 段的 text 拼接；无段时回退 raw_message）。"""
    parts: list[str] = []
    message = event.get("message")
    if isinstance(message, list):
        for seg in message:
            if not isinstance(seg, dict):
                continue
            if seg.get("type") == "text":
                data = seg.get("data") or {}
                if isinstance(data, dict):
                    parts.append(str(data.get("text", "")))
    text = "".join(parts)
    if not text and isinstance(message, str):
        text = message
    if not text:
        raw = event.get("raw_message")
        text = str(raw) if raw else ""
    return text


def segments(event: dict) -> list[dict]:
    message = event.get("message")
    return [seg for seg in message if isinstance(seg, dict)] if isinstance(message, list) else []


def at_self(event: dict, self_id: Any) -> bool:
    target = str(self_id) if self_id is not None else None
    for seg in segments(event):
        if seg.get("type") != "at":
            continue
        data = seg.get("data") or {}
        qq = data.get("qq") if isinstance(data, dict) else None
        if qq is None:
            continue
        if target is not None and str(qq) == target:
            return True
        if str(qq) == "all":
            continue
    # 兼容 message 为字符串（CQ 码格式）的协议端
    if target is not None:
        raw = str(event.get("raw_message") or "")
        if f"[CQ:at,qq={target}]" in raw:
            return True
    return False


def strip_leading_command(text: str) -> str:
    return text.strip().lstrip("\u3000 ").strip()


def split_reply(text: str, max_chars: int, max_parts: int,
                split_chars: str = "\n。；;!?！？ ") -> list[str]:
    """把长回答切成 <= max_chars 的多条；最多 max_parts 条，末条加省略标记。"""
    text = (text or "").strip()
    if not text:
        return [""]
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    rest = text
    while rest and len(parts) < max_parts:
        if len(rest) <= max_chars:
            parts.append(rest)
            rest = ""
            break
        window = rest[:max_chars]
        cut = -1
        for idx in range(len(window) - 1, max(0, len(window) // 3), -1):
            if window[idx] in split_chars:
                cut = idx + 1
                break
        if cut <= 0:
            cut = max_chars
        parts.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        tail = rest[:max(20, min(len(rest), max_chars - 12))]
        parts[-1] = (parts[-1] + "…（超长截断）").strip() if parts[-1] else "…（超长截断）"
        if len(parts[-1]) > max_chars:
            parts[-1] = parts[-1][:max_chars - 1] + "…"
        parts.append(tail) if len(parts) < max_parts else None
    return [p for p in parts if p != ""] or [text[:max_chars]]


def format_memories(data: Any, limit: int = 10) -> str:
    items: list[Any] = []
    if isinstance(data, dict):
        for key in ("memories", "items", "data", "results"):
            value = data.get(key)
            if isinstance(value, list):
                items = value
                break
        if not items and isinstance(data.get("memory"), list):
            items = data["memory"]
    elif isinstance(data, list):
        items = data
    if not items:
        return "（目前没有记忆）"
    lines = [f"记忆 {min(len(items), limit)}/{len(items)} 条："]
    for item in items[:limit]:
        if isinstance(item, dict):
            mid = item.get("id", "?")
            text = str(item.get("text") or item.get("content") or item.get("memory") or "")
            text = text.replace("\n", " ")
            lines.append(f"#{mid} {text[:120]}")
        else:
            lines.append(f"- {str(item)[:120]}")
    return "\n".join(lines)


def format_answer(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("answer", "text", "reply", "response", "content"):
            value = data.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                nested = format_answer(value)
                if nested:
                    return nested
        return json.dumps(data, ensure_ascii=False)[:2000]
    return str(data)


# --------------------------------------------------------------------------
# Bridge
# --------------------------------------------------------------------------
class QQBridge:
    def __init__(self, cfg: BridgeConfig, assistant: Optional[AssistantClient] = None,
                 sleep: Optional[Callable[[float], Awaitable[None]]] = None) -> None:
        self.cfg = cfg
        self.assistant = assistant or AssistantClient(
            cfg.http_base, http_timeout_s=cfg.http_timeout_s, verbose=cfg.verbose)
        self._sleep = sleep or asyncio.sleep
        self._session_locks: dict[tuple[str, int], asyncio.Lock] = {}
        self._log_lock = asyncio.Lock()
        self._conn_lock = asyncio.Lock()
        self.conn: Optional[WSConn] = None
        self.stats = {
            "events": 0, "triggers": 0, "replies": 0, "errors": 0,
            "reconnects": 0, "timeouts": 0, "serialized_waits": 0,
        }
        self.reconnect_delays: list[float] = []
        self.pending_sessions: set[tuple[str, int]] = set()
        os.makedirs(cfg.log_dir, exist_ok=True)

    # -- 日志（只元数据） --------------------------------------------
    def _log_record(self, **record: Any) -> None:
        record = {"ts": now_iso(), **record}
        path = Path(self.cfg.log_dir) / f"bridge-{datetime.now().strftime('%Y%m%d')}.jsonl"
        line = json.dumps(record, ensure_ascii=False) + "\n"
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError as exc:
            log(f"日志写入失败：{exc}")

    # -- 触发判断 -----------------------------------------------------
    def group_trigger(self, event: dict, text: str) -> tuple[bool, str]:
        mode = self.cfg.trigger_mode
        if mode == "none":
            return False, text
        at_hit = at_self(event, event.get("self_id"))
        prefix = self.cfg.prefix or "/"
        stripped = text.strip()
        prefix_hit = bool(prefix) and stripped.startswith(prefix)
        if mode == "at":
            ok = at_hit
        elif mode == "prefix":
            ok = prefix_hit
        else:
            ok = at_hit or prefix_hit
        # 群里 @ 之后常跟一个空格/正文；把 @ 段替换为空白后交给命令/问答
        if ok and at_hit:
            stripped = _strip_at_text(stripped)
        return ok, stripped

    # -- 事件处理 -----------------------------------------------------
    async def handle_event(self, conn: WSConn, event: dict) -> None:
        if event.get("post_type") != "message":
            return
        message_type = event.get("message_type")
        if message_type not in ("group", "private"):
            return
        self.stats["events"] += 1
        try:
            group_id = int(event["group_id"]) if message_type == "group" else None
        except (KeyError, TypeError, ValueError):
            group_id = None
        try:
            user_id = int(event.get("user_id") or 0)
        except (TypeError, ValueError):
            user_id = 0
        text = message_text(event)
        if message_type == "group":
            if self.cfg.allowed_groups and group_id not in self.cfg.allowed_groups:
                self._log_record(kind="message", group_id=group_id, user_id=user_id,
                                 hit=False, reason="group_not_allowed")
                return
            hit, text = self.group_trigger(event, text)
        else:
            hit = True
            text = text.strip()
        if not hit:
            self._log_record(kind="message", group_id=group_id, user_id=user_id,
                             hit=False, reason="not_triggered")
            return
        self.stats["triggers"] += 1
        text = strip_leading_command(text)
        key = ("group", group_id) if group_id is not None else ("private", user_id)
        lock = self._session_locks.setdefault(key, asyncio.Lock())
        if lock.locked():
            self.stats["serialized_waits"] += 1
        async with lock:
            self.pending_sessions.add(key)
            try:
                await self.process(conn, event, message_type, group_id, user_id, text)
            finally:
                self.pending_sessions.discard(key)

    async def process(self, conn: WSConn, event: dict, message_type: str,
                      group_id: Optional[int], user_id: int, text: str) -> None:
        cmd, arg = parse_command(text)
        self._log_record(kind="command" if cmd else "ask", group_id=group_id,
                         user_id=user_id, hit=True, command=cmd or "")
        try:
            if cmd == "remember":
                reply = await self._cmd_remember(arg, user_id)
            elif cmd == "memories":
                reply = await self._cmd_memories()
            elif cmd == "forget":
                reply = await self._cmd_forget(arg, user_id)
            elif cmd == "status":
                reply = await self._cmd_status()
            elif cmd == "health":
                reply = await self._cmd_health()
            elif cmd == "help":
                reply = HELP_TEXT
            elif cmd == "ask":
                reply = await self._cmd_ask(arg)
            else:
                reply = await self._cmd_ask(text)
        except AssistantError as exc:
            self.stats["errors"] += 1
            self._log_record(kind="error", group_id=group_id, user_id=user_id,
                             hit=True, error=type(exc).__name__, command=cmd or "")
            reply = f"（本地助手错误：{exc}）"
        except (asyncio.TimeoutError, TimeoutError):
            self.stats["timeouts"] += 1
            self._log_record(kind="error", group_id=group_id, user_id=user_id,
                             hit=True, error="timeout", command=cmd or "")
            reply = f"（本地助手超时 {self.cfg.timeout_s:.0f}s，请稍后再试）"
        except Exception as exc:  # 兜底：不让单条消息打断连接
            self.stats["errors"] += 1
            self._log_record(kind="error", group_id=group_id, user_id=user_id,
                             hit=True, error=type(exc).__name__, command=cmd or "")
            reply = f"（处理失败：{type(exc).__name__}）"
        await self.send_reply(conn, message_type, group_id, user_id, reply)

    # -- 命令 ---------------------------------------------------------
    async def _cmd_ask(self, text: str) -> str:
        if not text:
            return "（请把问题写在后面）"
        data = await self.assistant.ask(text)
        return format_answer(data)

    async def _cmd_remember(self, arg: str, user_id: int) -> str:
        if self.cfg.admin_qq and user_id not in self.cfg.admin_qq:
            return "（仅管理员可 /remember）"
        if not arg:
            return "用法：/remember <要记住的内容>"
        data = await self.assistant.remember(arg)
        if isinstance(data, dict) and data.get("ok") is False:
            return f"（记忆失败：{data.get('error', 'unknown')}）"
        return "已记住。"

    async def _cmd_memories(self) -> str:
        return format_memories(await self.assistant.memories())

    async def _cmd_forget(self, arg: str, user_id: int) -> str:
        if self.cfg.admin_qq and user_id not in self.cfg.admin_qq:
            return "（仅管理员可 /forget）"
        if not arg:
            return "用法：/forget <id>"
        memory_id: Any = int(arg) if arg.lstrip("-").isdigit() else arg
        data = await self.assistant.forget(memory_id)
        if isinstance(data, dict) and data.get("ok") is False:
            return f"（删除失败：{data.get('error', 'unknown')}）"
        return f"已删除记忆 #{arg}。"

    async def _cmd_status(self) -> str:
        data = await self.assistant.status()
        if isinstance(data, dict):
            keep = {k: v for k, v in data.items()
                    if k in ("status", "ok", "uptime_s", "uptime", "memories", "memory_count",
                             "model", "engine", "version")}
            data = keep or data
        return "状态：" + (json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data)

    async def _cmd_health(self) -> str:
        return "健康：" + json.dumps(await self.assistant.health(), ensure_ascii=False)

    # -- 发送 ---------------------------------------------------------
    async def send_reply(self, conn: WSConn, message_type: str,
                         group_id: Optional[int], user_id: int, text: str) -> None:
        parts = split_reply(text or "（空回答）", self.cfg.reply_max_chars,
                            self.cfg.reply_max_parts, self.cfg.reply_split_at)
        for part in parts:
            params: dict[str, Any] = {"message": part}
            if message_type == "group" and group_id is not None:
                params["group_id"] = group_id
                action = "send_group_msg"
            else:
                params["user_id"] = user_id
                action = "send_private_msg"
            try:
                resp = await conn.call(action, params, timeout=self.cfg.http_timeout_s)
            except (asyncio.TimeoutError, TimeoutError, ConnectionError) as exc:
                self.stats["errors"] += 1
                self._log_record(kind="send_fail", group_id=group_id, user_id=user_id,
                                 hit=True, error=type(exc).__name__)
                return
            if resp.get("status") != "ok" and int(resp.get("retcode") or 0) != 0:
                self.stats["errors"] += 1
                self._log_record(kind="send_fail", group_id=group_id, user_id=user_id,
                                 hit=True, retcode=resp.get("retcode"))
                return
            self.stats["replies"] += 1

    # -- 运行 ---------------------------------------------------------
    async def run(self) -> None:
        if self.cfg.mode == "reverse":
            await self._run_reverse()
        else:
            await self._run_forward()

    async def _run_reverse(self) -> None:
        async def on_connect(reader: asyncio.StreamReader,
                             writer: asyncio.StreamWriter) -> None:
            conn = await ws_accept(reader, writer, token=self.cfg.token,
                                   require_token=bool(self.cfg.token),
                                   verbose=self.cfg.verbose)
            if conn is None:
                return
            async with self._conn_lock:
                self.conn = conn
            try:
                await conn.run(self.handle_event)
            finally:
                async with self._conn_lock:
                    if self.conn is conn:
                        self.conn = None
                await conn.close()

        server = await asyncio.start_server(on_connect, self.cfg.ws_host, self.cfg.ws_port)
        addrs = ", ".join(str(sock.getsockname()) for sock in (server.sockets or []))
        log(f"reverse 模式：WS 服务器监听 {addrs}（等待 NapCat 连入）", True)
        async with server:
            await server.serve_forever()

    async def _run_forward(self) -> None:
        delay = self.cfg.reconnect_min_s
        while True:
            try:
                conn = await ws_connect(self.cfg.ws_url, token=self.cfg.token,
                                        verbose=self.cfg.verbose)
            except Exception as exc:
                log(f"forward 连接失败：{exc}；{delay:.2f}s 后重试", True)
                self.reconnect_delays.append(round(delay, 3))
                self.stats["reconnects"] += 1
                await self._sleep(delay)
                delay = min(self.cfg.reconnect_max_s, delay * self.cfg.reconnect_factor)
                continue
            async with self._conn_lock:
                self.conn = conn
            delay = self.cfg.reconnect_min_s  # 连上后重置退避
            try:
                await conn.run(self.handle_event)
            except Exception as exc:
                log(f"WS 连接异常：{type(exc).__name__}: {exc}", True)
            finally:
                async with self._conn_lock:
                    if self.conn is conn:
                        self.conn = None
                await conn.close()
            log(f"WS 已断开；{delay:.2f}s 后重连", True)
            self.reconnect_delays.append(round(delay, 3))
            self.stats["reconnects"] += 1
            await self._sleep(delay)
            delay = min(self.cfg.reconnect_max_s, delay * self.cfg.reconnect_factor)

    async def stop(self) -> None:
        conn = self.conn
        if conn is not None:
            await conn.close()


COMMANDS = {
    "/remember": "remember", "/记住": "remember", "/记": "remember",
    "/memories": "memories", "/记忆": "memories", "/回忆": "memories",
    "/forget": "forget", "/忘记": "forget", "/删除记忆": "forget",
    "/status": "status", "/状态": "status",
    "/ask": "ask", "/问": "ask",
    "/health": "health", "/健康": "health",
    "/help": "help", "/帮助": "help",
}


def parse_command(text: str) -> tuple[Optional[str], str]:
    stripped = text.strip()
    if not stripped.startswith("/") and not any(
            stripped.startswith(k) for k in ("记住", "记忆", "忘记", "状态", "帮助")):
        return None, stripped
    for token in sorted(COMMANDS, key=len, reverse=True):
        if stripped == token:
            return COMMANDS[token], ""
        if stripped.startswith(token):
            rest = stripped[len(token):]
            if not rest or rest[0] in " \t\u3000":
                return COMMANDS[token], rest.strip()
            if token.startswith("/"):
                continue
            return COMMANDS[token], rest.strip()
    return None, stripped


def _strip_at_text(text: str) -> str:
    # 群消息里 @机器人 之后的常见形式："@bot /status" 或 "/status"
    return text.strip().lstrip("\u3000 ").strip()


HELP_TEXT = ("命令：/ask <问题>（默认直接问）｜/remember <内容>｜/memories｜"
             "/forget <id>｜/status")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="QQ bridge: OneBot v11 (NapCat/Lagrange) <-> local assistant HTTP")
    parser.add_argument("--config", help="JSON 配置（默认读 tools/qq_bridge.example.json）")
    parser.add_argument("--mode", choices=["reverse", "forward"])
    parser.add_argument("--ws-url", dest="ws_url")
    parser.add_argument("--ws-host", dest="ws_host")
    parser.add_argument("--ws-port", dest="ws_port", type=int)
    parser.add_argument("--token")
    parser.add_argument("--http-base", dest="http_base")
    parser.add_argument("--trigger-mode", dest="trigger_mode",
                        choices=["at", "prefix", "both", "none"])
    parser.add_argument("--prefix")
    parser.add_argument("--allowed-groups", dest="allowed_groups",
                        help="逗号分隔群号；空=所有群")
    parser.add_argument("--admin-qq", dest="admin_qq", help="逗号分隔管理员 QQ")
    parser.add_argument("--timeout", dest="timeout_s", type=float)
    parser.add_argument("--reply-max-chars", dest="reply_max_chars", type=int)
    parser.add_argument("--log-dir", dest="log_dir")
    parser.add_argument("--verbose", action="store_true")
    return parser


def _split_ints(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return [int(x) for x in value.replace("，", ",").split(",") if x.strip()]
    return value


def config_from_args(args: argparse.Namespace) -> BridgeConfig:
    overrides = {k: v for k, v in vars(args).items()
                 if k not in ("config",) and v is not None}
    overrides["allowed_groups"] = _split_ints(overrides.get("allowed_groups"))
    overrides["admin_qq"] = _split_ints(overrides.get("admin_qq"))
    overrides = {k: v for k, v in overrides.items() if v is not None}
    return load_config(args.config, **overrides)


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        cfg = config_from_args(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        log(f"配置错误：{exc}", True)
        return 2
    if cfg.token in ("", "CHANGE_ME") and not cfg.verbose:
        log("警告：token 仍是占位值，建议在配置里改成随机串（NapCat 侧一致）")
    bridge = QQBridge(cfg)
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        log("收到 Ctrl+C，退出")
        return 0
    except Exception as exc:
        log(f"致命错误：{type(exc).__name__}: {exc}", True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())