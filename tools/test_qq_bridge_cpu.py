#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_qq_bridge_cpu.py — qq_bridge 的 CPU-only 测试（零 GPU / 零外网）。

全部依赖本机 mock：
  * MockAssistant  —— 用 http.server.ThreadingHTTPServer 模拟本地助手 127.0.0.1:8765；
  * MockOneBot     —— 用 asyncio 起一个 OneBot v11 WS 端（验证 forward 模式：bridge 连它）；
  * 反向模式直接让测试客户端连 bridge 的 WS 端口。
不触网、不读冻结件、不写 kvmem/qq_logs 以外目录（log_dir 指到临时目录）。

运行：
    python -X utf8 tools/test_qq_bridge_cpu.py -v
退出码：0 = 全部通过；非 0 = 有失败。
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qq_bridge as qb  # noqa: E402

TOKEN = "test-token"


# --------------------------------------------------------------------------
# Mock 本地助手服务
# --------------------------------------------------------------------------
class MockAssistant:
    def __init__(self, delay: float = 0.0, fail_status: Optional[int] = None,
                 answer: str = "这是 mock 回答。"):
        self.delay = delay
        self.fail_status = fail_status
        self.answer = answer
        self.records: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: Any) -> None:  # 静音
                pass

            def _read_body(self) -> Optional[dict]:
                length = int(self.headers.get("Content-Length") or 0)
                if not length:
                    return None
                raw = self.rfile.read(length)
                try:
                    return json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    return {"_raw": raw.decode("utf-8", "replace")}

            def _handle(self, method: str) -> None:
                body = self._read_body()
                started = time.monotonic()
                if outer.delay:
                    time.sleep(outer.delay)
                with outer._lock:
                    outer.records.append({
                        "method": method,
                        "path": self.path,
                        "body": body,
                        "start": started,
                        "end": time.monotonic(),
                    })
                if outer.fail_status:
                    outer._respond(self, outer.fail_status,
                                   {"error": "mock failure"})
                    return
                if self.path == "/health":
                    outer._respond(self, 200, {"status": "ok", "service": "mock"})
                elif self.path == "/ask" and method == "POST":
                    text = (body or {}).get("text", "")
                    outer._respond(self, 200, {"answer": outer.answer + f"[{len(text)}字]"})
                elif self.path == "/remember" and method == "POST":
                    outer._respond(self, 200, {"ok": True, "id": 1})
                elif self.path == "/memories" and method == "GET":
                    outer._respond(self, 200, {"memories": [{"id": 1, "text": "mock memory"}]})
                elif self.path == "/forget" and method == "POST":
                    outer._respond(self, 200, {"ok": True})
                elif self.path == "/status" and method == "GET":
                    outer._respond(self, 200, {"status": "ok", "uptime_s": 12,
                                               "memory_count": 1})
                else:
                    outer._respond(self, 404, {"error": "not found"})

            def do_GET(self) -> None:
                self._handle("GET")

            def do_POST(self) -> None:
                self._handle("POST")

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.httpd.handle_error = lambda *args, **kwargs: None  # 客户端提前断开时不刷屏
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self._thread: Optional[threading.Thread] = None

    @staticmethod
    def _respond(handler: BaseHTTPRequestHandler, status: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        try:
            handler.wfile.write(body)
        except BrokenPipeError:
            pass

    def start(self) -> "MockAssistant":
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def calls(self, path: Optional[str] = None) -> list[dict]:
        with self._lock:
            return [r for r in self.records if path is None or r["path"] == path]


# --------------------------------------------------------------------------
# Mock OneBot v11 WS 端（bridge 作为客户端连它 = forward 模式）
# --------------------------------------------------------------------------
class MockOneBot:
    def __init__(self, token: str = TOKEN):
        self.token = token
        self.server: Optional[asyncio.AbstractServer] = None
        self.conns: list[qb.WSConn] = []
        self.actions: list[dict] = []
        self.on_conn = None

    async def start(self) -> "MockOneBot":
        self.server = await asyncio.start_server(self._accept, "127.0.0.1", 0)
        port = self.server.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}/?access_token={self.token}"
        return self

    async def _accept(self, reader: asyncio.StreamReader,
                      writer: asyncio.StreamWriter) -> None:
        conn = await qb.ws_accept(reader, writer, token=self.token,
                                  require_token=True)
        if conn is None:
            return
        self.conns.append(conn)
        if self.on_conn:
            try:
                await self.on_conn(conn)
            except (ConnectionError, asyncio.CancelledError):
                pass

    async def stop(self) -> None:
        for conn in list(self.conns):
            await conn.close()
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def read_action(self, conn: qb.WSConn, timeout: float = 2.0,
                          respond: bool = True) -> Optional[dict]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            msg = await conn.recv_json(timeout=max(0.02, deadline - time.monotonic()))
            if msg is None:
                return None
            if "action" in msg:
                self.actions.append(msg)
                if respond:
                    await conn.send_text(json.dumps({
                        "status": "ok", "retcode": 0,
                        "data": {"message_id": len(self.actions)},
                        "echo": msg.get("echo"),
                    }, ensure_ascii=False))
                return msg
        return None


# --------------------------------------------------------------------------
# 公共工具
# --------------------------------------------------------------------------
def group_event(text: str, *, group_id: int = 100, user_id: int = 200,
                self_id: int = 999, at: bool = False, message_id: int = 1) -> dict:
    msg: list[dict] = []
    if at:
        msg.append({"type": "at", "data": {"qq": str(self_id)}})
    msg.append({"type": "text", "data": {"text": text}})
    return {
        "post_type": "message", "message_type": "group", "sub_type": "normal",
        "message_id": message_id, "group_id": group_id, "user_id": user_id,
        "self_id": self_id, "raw_message": text, "message": msg,
        "time": int(time.time()),
    }


def private_event(text: str, *, user_id: int = 200, self_id: int = 999,
                  message_id: int = 1) -> dict:
    return {
        "post_type": "message", "message_type": "private", "sub_type": "friend",
        "message_id": message_id, "user_id": user_id, "self_id": self_id,
        "raw_message": text,
        "message": [{"type": "text", "data": {"text": text}}],
        "time": int(time.time()),
    }


async def wait_until(predicate, timeout: float = 3.0, interval: float = 0.01) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return False


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class BridgeTestCase(unittest.IsolatedAsyncioTestCase):
    """提供 mock 助手、临时日志目录与 bridge 生命周期。"""

    async def asyncSetUp(self) -> None:
        # IsolatedAsyncioTestCase 默认 debug=True，会打印慢回调警告；测试里关掉以保持输出干净
        try:
            asyncio.get_running_loop().set_debug(False)
        except RuntimeError:
            pass
        self.tmpdir = tempfile.TemporaryDirectory(prefix="qq_bridge_test_")
        self.assistant = MockAssistant().start()
        self.onebot: Optional[MockOneBot] = None
        self.bridge_task: Optional[asyncio.Task] = None
        self.bridge: Optional[qb.QQBridge] = None

    async def asyncTearDown(self) -> None:
        if self.bridge_task:
            self.bridge_task.cancel()
            try:
                await self.bridge_task
            except (asyncio.CancelledError, Exception):
                pass
        if self.bridge:
            await self.bridge.stop()
        if self.onebot:
            await self.onebot.stop()
        self.assistant.stop()
        self.tmpdir.cleanup()

    def make_cfg(self, **kwargs: Any) -> qb.BridgeConfig:
        values = dict(
            mode="forward",
            ws_url="ws://127.0.0.1:1/",
            token=TOKEN,
            http_base=self.assistant.base,
            trigger_mode="at",
            prefix="/",
            timeout_s=2.0,
            reply_max_chars=600,
            reply_max_parts=4,
            log_dir=self.tmpdir.name,
            reconnect_min_s=0.02,
            reconnect_max_s=0.05,
            http_timeout_s=2.5,
        )
        values.update(kwargs)
        return qb.BridgeConfig(**values).normalized()

    async def start_forward_bridge(self, assistant: Optional[MockAssistant] = None,
                                   **cfg_kwargs: Any) -> qb.QQBridge:
        self.onebot = await MockOneBot().start()
        cfg = self.make_cfg(ws_url=self.onebot.url, **cfg_kwargs)
        if assistant is not None:
            cfg.http_base = assistant.base
        self.bridge = qb.QQBridge(cfg)
        self.bridge_task = asyncio.create_task(self.bridge.run())
        ok = await wait_until(lambda: len(self.onebot.conns) >= 1, timeout=3.0)
        self.assertTrue(ok, "bridge 未能连上 mock OneBot")
        return self.bridge

    async def start_reverse_bridge(self, wait_conn: bool = False,
                                   **cfg_kwargs: Any) -> qb.QQBridge:
        port = free_port()
        cfg = self.make_cfg(mode="reverse", ws_port=port, **cfg_kwargs)
        self.bridge = qb.QQBridge(cfg)
        self.bridge_task = asyncio.create_task(self.bridge.run())
        await asyncio.sleep(0.1)  # 让 asyncio.start_server 起来
        if wait_conn:
            ok = await wait_until(lambda: self.bridge.conn is not None, timeout=3.0)
            self.assertTrue(ok, "reverse bridge 未能监听")
        return self.bridge


class TestBasicFlow(BridgeTestCase):
    async def test_forward_private_message_ask_and_reply(self) -> None:
        bridge = await self.start_forward_bridge()
        conn = self.onebot.conns[0]
        await conn.send_text(json.dumps(private_event("你好，介绍一下你自己"), ensure_ascii=False))
        action = await self.onebot.read_action(conn)
        self.assertIsNotNone(action, "未收到回包动作")
        self.assertEqual(action["action"], "send_private_msg")
        self.assertEqual(action["params"]["user_id"], 200)
        self.assertIn("这是 mock 回答", action["params"]["message"])
        self.assertEqual(len(self.assistant.calls("/ask")), 1)
        self.assertEqual(self.assistant.calls("/ask")[0]["body"]["text"], "你好，介绍一下你自己")

    async def test_group_at_trigger(self) -> None:
        await self.start_forward_bridge()
        conn = self.onebot.conns[0]
        await conn.send_text(json.dumps(group_event("群里测试问题", at=True), ensure_ascii=False))
        action = await self.onebot.read_action(conn)
        self.assertIsNotNone(action)
        self.assertEqual(action["action"], "send_group_msg")
        self.assertEqual(action["params"]["group_id"], 100)
        self.assertEqual(len(self.assistant.calls("/ask")), 1)

    async def test_group_without_trigger_is_ignored(self) -> None:
        await self.start_forward_bridge()
        conn = self.onebot.conns[0]
        await conn.send_text(json.dumps(group_event("这条不该被处理", at=False)))
        await asyncio.sleep(0.25)
        self.assertEqual(self.assistant.calls("/ask"), [])
        self.assertEqual(self.onebot.actions, [])

    async def test_prefix_trigger_mode(self) -> None:
        await self.start_forward_bridge(trigger_mode="prefix", prefix="!")
        conn = self.onebot.conns[0]
        await conn.send_text(json.dumps(group_event("!状态查询")))
        action = await self.onebot.read_action(conn)
        self.assertIsNotNone(action)
        self.assertEqual(action["action"], "send_group_msg")
        # "!状态查询" 不是命令 -> 走 /ask
        self.assertEqual(len(self.assistant.calls("/ask")), 1)

    async def test_allowed_groups_filter(self) -> None:
        await self.start_forward_bridge(trigger_mode="both", allowed_groups=[777])
        conn = self.onebot.conns[0]
        await conn.send_text(json.dumps(group_event("被过滤", group_id=100, at=True)))
        await asyncio.sleep(0.2)
        self.assertEqual(self.assistant.calls("/ask"), [])
        await conn.send_text(json.dumps(group_event("放行", group_id=777, at=True)))
        action = await self.onebot.read_action(conn)
        self.assertIsNotNone(action)
        self.assertEqual(len(self.assistant.calls("/ask")), 1)


class TestCommands(BridgeTestCase):
    async def test_remember_memories_forget_status(self) -> None:
        await self.start_forward_bridge(trigger_mode="both")
        conn = self.onebot.conns[0]
        cases = [
            ("/remember 我喜欢喝美式", "send_private_msg", "已记住"),
            ("/memories", "send_private_msg", "记忆"),
            ("/forget 1", "send_private_msg", "已删除"),
            ("/status", "send_private_msg", "状态"),
        ]
        for text, expected_action, expected_text in cases:
            await conn.send_text(json.dumps(private_event(text, message_id=len(self.onebot.actions) + 1),
                                             ensure_ascii=False))
            action = await self.onebot.read_action(conn)
            self.assertIsNotNone(action, f"未回包：{text}")
            self.assertEqual(action["action"], expected_action)
            self.assertIn(expected_text, action["params"]["message"], f"{text} 回执异常")
        self.assertEqual(len(self.assistant.calls("/remember")), 1)
        self.assertEqual(self.assistant.calls("/remember")[0]["body"]["text"], "我喜欢喝美式")
        self.assertEqual(len(self.assistant.calls("/memories")), 1)
        self.assertEqual(self.assistant.calls("/forget")[0]["body"]["id"], 1)
        self.assertEqual(len(self.assistant.calls("/status")), 1)

    async def test_admin_only_remember(self) -> None:
        await self.start_forward_bridge(trigger_mode="both", admin_qq=[4242])
        conn = self.onebot.conns[0]
        await conn.send_text(json.dumps(private_event("/remember 越权尝试", user_id=200)))
        action = await self.onebot.read_action(conn)
        self.assertIsNotNone(action)
        self.assertIn("管理员", action["params"]["message"])
        self.assertEqual(self.assistant.calls("/remember"), [])


class TestResilience(BridgeTestCase):
    async def test_assistant_timeout_error_receipt(self) -> None:
        slow = MockAssistant(delay=1.0).start()
        try:
            await self.start_forward_bridge(assistant=slow, timeout_s=0.15,
                                            http_timeout_s=0.2)
            conn = self.onebot.conns[0]
            started = time.monotonic()
            await conn.send_text(json.dumps(private_event("慢问题")))
            action = await self.onebot.read_action(conn, timeout=3.0)
            elapsed = time.monotonic() - started
            self.assertIsNotNone(action, "超时应回执")
            self.assertIn("超时", action["params"]["message"])
            self.assertLess(elapsed, 2.0)
            self.assertEqual(slow.calls("/ask"), [])
        finally:
            slow.stop()

    async def test_assistant_http_500_error_receipt(self) -> None:
        broken = MockAssistant(fail_status=500).start()
        try:
            await self.start_forward_bridge(assistant=broken)
            conn = self.onebot.conns[0]
            await conn.send_text(json.dumps(private_event("会失败")))
            action = await self.onebot.read_action(conn)
            self.assertIsNotNone(action)
            self.assertIn("500", action["params"]["message"])
        finally:
            broken.stop()

    async def test_assistant_unreachable_error_receipt(self) -> None:
        await self.start_forward_bridge()
        self.bridge.cfg.http_base = "http://127.0.0.1:1"
        self.bridge.assistant.base = "http://127.0.0.1:1"
        conn = self.onebot.conns[0]
        await conn.send_text(json.dumps(private_event("连不上")))
        action = await self.onebot.read_action(conn, timeout=4.0)
        self.assertIsNotNone(action)
        self.assertIn("本地助手", action["params"]["message"])

    async def test_reconnect_backoff(self) -> None:
        self.onebot = await MockOneBot().start()

        async def handler(conn: qb.WSConn) -> None:
            # 收到一条事件 -> 读回包 -> 主动断开，逼 bridge 重连
            await conn.send_text(json.dumps(private_event("断线测试",
                                                          message_id=len(self.onebot.conns))))
            await self.onebot.read_action(conn)
            await conn.close()

        self.onebot.on_conn = handler
        cfg = self.make_cfg(ws_url=self.onebot.url, reconnect_min_s=0.02,
                            reconnect_max_s=0.05)
        self.bridge = qb.QQBridge(cfg)
        self.bridge_task = asyncio.create_task(self.bridge.run())
        ok = await wait_until(lambda: len(self.onebot.conns) >= 3, timeout=5.0)
        self.assertTrue(ok, f"未重连：conns={len(self.onebot.conns)}")
        self.assertGreaterEqual(self.bridge.stats["reconnects"], 2)
        self.assertTrue(all(d >= 0.02 for d in self.bridge.reconnect_delays))
        self.assertLessEqual(max(self.bridge.reconnect_delays), 0.05)

    async def test_serial_per_session_and_parallel_across_sessions(self) -> None:
        slow = MockAssistant(delay=0.15).start()
        try:
            await self.start_forward_bridge(assistant=slow, timeout_s=5.0,
                                            http_timeout_s=5.5)
            conn = self.onebot.conns[0]
            await conn.send_text(json.dumps(private_event("同会话1", message_id=1)))
            await conn.send_text(json.dumps(private_event("同会话2", message_id=2)))
            a1 = await self.onebot.read_action(conn)
            a2 = await self.onebot.read_action(conn)
            self.assertIsNotNone(a1)
            self.assertIsNotNone(a2)
            calls = slow.calls("/ask")
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0]["body"]["text"], "同会话1")
            self.assertEqual(calls[1]["body"]["text"], "同会话2")
            self.assertLessEqual(calls[0]["end"], calls[1]["start"] + 0.05,
                                 "同会话两条 /ask 不应重叠")
        finally:
            slow.stop()


class TestReplyAndLogs(BridgeTestCase):
    async def test_long_reply_split(self) -> None:
        long_answer = "长回答内容。" * 100  # ~600 字
        big = MockAssistant(answer=long_answer).start()
        try:
            await self.start_forward_bridge(assistant=big, reply_max_chars=120,
                                            reply_max_parts=3)
            conn = self.onebot.conns[0]
            await conn.send_text(json.dumps(private_event("给我长回答")))
            parts: list[str] = []
            for _ in range(3):
                action = await self.onebot.read_action(conn)
                if action is None:
                    break
                parts.append(action["params"]["message"])
                if len(parts) >= 3:
                    break
            self.assertGreaterEqual(len(parts), 2, "长回答应分条发送")
            self.assertLessEqual(len(parts), 3, "分条数不应超过 reply_max_parts")
            for part in parts:
                self.assertLessEqual(len(part), 120, f"分条超长：{len(part)}")
        finally:
            big.stop()

    async def test_logs_are_metadata_only(self) -> None:
        await self.start_forward_bridge(trigger_mode="both")
        conn = self.onebot.conns[0]
        secret = "SECRET-CONTENT-不应落盘"
        await conn.send_text(json.dumps(private_event(secret)))
        await self.onebot.read_action(conn)
        await asyncio.sleep(0.1)
        logs = [p for p in os.listdir(self.tmpdir.name) if p.endswith(".jsonl")]
        self.assertTrue(logs, "应产生元数据日志")
        blob = "".join(open(os.path.join(self.tmpdir.name, name), encoding="utf-8").read()
                       for name in logs)
        self.assertNotIn(secret, blob, "日志不得包含消息正文")
        records = [json.loads(line) for line in blob.splitlines() if line.strip()]
        self.assertTrue(any(r.get("kind") in ("ask", "command") for r in records))
        self.assertTrue(all("ts" in r for r in records))


class TestReverseMode(BridgeTestCase):
    async def test_reverse_mode_accepts_client(self) -> None:
        bridge = await self.start_reverse_bridge(trigger_mode="both")
        conn = await qb.ws_connect(f"ws://127.0.0.1:{bridge.cfg.ws_port}/onebot",
                                   token=bridge.cfg.token)
        ok = await wait_until(lambda: bridge.conn is not None, timeout=3.0)
        self.assertTrue(ok, "reverse bridge 未接受连接")
        try:
            await conn.send_text(json.dumps(private_event("反向模式问题")))
            action = await self.onebot_read_action(conn)  # type: ignore[attr-defined]
            self.assertIsNotNone(action)
            self.assertEqual(action["action"], "send_private_msg")
        finally:
            await conn.close()

    async def test_reverse_mode_rejects_bad_token(self) -> None:
        bridge = await self.start_reverse_bridge()
        with self.assertRaises(ConnectionError):
            await qb.ws_connect(f"ws://127.0.0.1:{bridge.cfg.ws_port}/onebot",
                                token="wrong-token")

    async def onebot_read_action(self, conn: qb.WSConn, timeout: float = 2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            msg = await conn.recv_json(timeout=max(0.02, deadline - time.monotonic()))
            if msg is None:
                return None
            if "action" in msg:
                return msg
        return None


if __name__ == "__main__":
    unittest.main(verbosity=2)