#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""QQ 链路独立验收（模拟 NapCat 客户端；不登录 QQ、不读消息正文日志）。

流程：等 ws://127.0.0.1:8766 可连 → 用 third_party/qq_token.txt 做 OneBot v11
反向 WS 握手 → 依次发 3 条事件（群 @机器人「你好」、群 @机器人「我明天要去哪里
出差？」、私聊「我的车牌号是多少？」）→ 校验 bridge 回 send_group_msg /
send_private_msg 及内容 → 记录耗时 → 写 out/QQ-E2E-ACCEPT.json。
另有 1 条负测试（群里不 @，应不触发）。

安全/纪律：token 只驻留内存，产物只写 token 长度与来源路径，不写 token 本身；
不登录 QQ、不读盲标/研究数据；除 out/QQ-E2E-ACCEPT.json 外不写文件。

用法：python -X utf8 tmp/qq_e2e_accept.py [--wait 600] [--out ...]
"""
import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(r"D:\llama-mem")
TOKEN_FILE = ROOT / "third_party" / "qq_token.txt"
ART = ROOT / "out" / "QQ-E2E-ACCEPT.json"
WS_HOST = "127.0.0.1"
WS_PORT = 8766

BOT_ID = 10001
GROUP_ID = 20002
USER_ID = 30003
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


# ------------------------------------------------------------ ws helpers ----
class WS:
    def __init__(self, sock):
        self.s = sock
        self.buf = b""

    def send_frame(self, payload: bytes, opcode: int = 0x1) -> None:
        mask = os.urandom(4)
        n = len(payload)
        head = bytearray([0x80 | opcode])
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head += struct.pack("!H", n)
        else:
            head.append(0x80 | 127)
            head += struct.pack("!Q", n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.s.sendall(bytes(head) + mask + masked)

    def _read(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.s.recv(65536)
            if not chunk:
                raise ConnectionError("socket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv_frame(self, timeout: float):
        self.s.settimeout(timeout)
        try:
            b1, b2 = self._read(2)
        except socket.timeout:
            return None
        opcode = b1 & 0x0F
        masked = b2 & 0x80
        n = b2 & 0x7F
        if n == 126:
            n = struct.unpack("!H", self._read(2))[0]
        elif n == 127:
            n = struct.unpack("!Q", self._read(8))[0]
        mask = self._read(4) if masked else None
        payload = self._read(n) if n else b""
        if mask:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return {"opcode": opcode, "payload": payload}

    def close(self) -> None:
        try:
            self.send_frame(b"", opcode=0x8)
        except Exception:  # noqa: BLE001
            pass
        try:
            self.s.close()
        except Exception:  # noqa: BLE001
            pass


def ws_connect(host, port, token, timeout=10.0):
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    s = socket.create_connection((host, port), timeout=timeout)
    req = ("GET / HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n"
           "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\nAuthorization: Bearer %s\r\n\r\n"
           % (host, port, key, token))
    s.sendall(req.encode("ascii"))
    data = b""
    s.settimeout(timeout)
    while b"\r\n\r\n" not in data:
        chunk = s.recv(4096)
        if not chunk:
            raise ConnectionError("handshake closed")
        data += chunk
    head, _, rest = data.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    status = lines[0]
    if "101" not in status:
        s.close()
        raise ConnectionError("handshake rejected: %s" % status)
    expect = base64.b64encode(hashlib.sha1(
        (key + WS_GUID).encode("ascii")).digest()).decode("ascii")
    if expect.lower() not in head.decode("latin-1").lower():
        s.close()
        raise ConnectionError("bad Sec-WebSocket-Accept")
    ws = WS(s)
    ws.buf = rest
    return ws, {"request": "GET / (Authorization: Bearer <redacted>)",
                "response_status": status}


# --------------------------------------------------------------- events -----
def group_at_event(text, message_id):
    return {
        "post_type": "message", "message_type": "group", "sub_type": "normal",
        "message_id": message_id, "group_id": GROUP_ID, "user_id": USER_ID,
        "self_id": BOT_ID, "time": int(time.time()),
        "raw_message": "[CQ:at,qq=%d] %s" % (BOT_ID, text),
        "message": [{"type": "at", "data": {"qq": str(BOT_ID)}},
                    {"type": "text", "data": {"text": " " + text}}],
        "sender": {"user_id": USER_ID, "nickname": "acceptance"},
    }


def group_plain_event(text, message_id):
    ev = group_at_event(text, message_id)
    ev["message"] = [{"type": "text", "data": {"text": text}}]
    ev["raw_message"] = text
    return ev


def private_event(text, message_id):
    return {
        "post_type": "message", "message_type": "private", "sub_type": "friend",
        "message_id": message_id, "user_id": USER_ID, "self_id": BOT_ID,
        "time": int(time.time()), "raw_message": text,
        "message": [{"type": "text", "data": {"text": text}}],
        "sender": {"user_id": USER_ID, "nickname": "acceptance"},
    }


def wait_bridge(host, port, timeout_s):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            s = socket.create_connection((host, port), timeout=1.0)
            s.close()
            return True, round(time.time() - t0, 3)
        except OSError:
            time.sleep(1.0)
    return False, round(time.time() - t0, 3)


def run_case(ws, name, event, expect_action, content_check, quiet_s=2.5,
             wait_action_s=75.0, negative=False):
    """Send one event, collect bridge actions until quiet, answer each action."""
    t_send = time.perf_counter()
    raw = json.dumps(event, ensure_ascii=False)
    ws.send_frame(raw.encode("utf-8"))
    actions = []
    latencies = []
    deadline = t_send + (quiet_s if negative else wait_action_s)
    first_deadline = time.perf_counter() + (quiet_s if negative
                                            else wait_action_s)
    while time.perf_counter() < deadline:
        try:
            frame = ws.recv_frame(timeout=0.5)
        except (ConnectionError, OSError) as exc:
            return {"name": name, "pass": False, "error": "socket:%s" % exc,
                    "actions": actions}
        if frame is None:
            if actions and time.perf_counter() > deadline - quiet_s + 0.1:
                break
            continue
        op = frame["opcode"]
        if op == 0x8:
            break
        if op in (0x9, 0xA):
            if op == 0x9:
                ws.send_frame(frame["payload"], opcode=0xA)
            continue
        if op != 0x1:
            continue
        try:
            msg = json.loads(frame["payload"].decode("utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(msg, dict):
            continue
        if "action" in msg:
            lat = round((time.perf_counter() - t_send) * 1000.0, 1)
            latencies.append(lat)
            actions.append({"action": msg.get("action"),
                            "params": msg.get("params"),
                            "echo": msg.get("echo")})
            reply = {"status": "ok", "retcode": 0,
                     "data": {"message_id": 9000 + len(actions)},
                     "echo": msg.get("echo")}
            ws.send_frame(json.dumps(reply, ensure_ascii=False).encode("utf-8"))
            deadline = time.perf_counter() + quiet_s
        elif "post_type" in msg:
            continue
    first_action = actions[0] if actions else None
    got_action = first_action["action"] if first_action else None
    messages = [a["params"].get("message") for a in actions
                if isinstance(a.get("params"), dict)]
    text_all = "\n".join(m for m in messages if isinstance(m, str))
    ok_action = got_action == expect_action
    ok_content = bool(content_check(text_all)) if text_all else False
    ok_neg = (not actions) if negative else True
    if negative:
        ok_action = ok_content = True
    return {
        "name": name, "negative": negative,
        "action_expected": expect_action, "action_got": got_action,
        "actions": actions, "n_actions": len(actions),
        "messages": messages, "content_ok": ok_content,
        "action_ok": ok_action, "no_action_expected": ok_neg,
        "latency_ms": latencies[0] if latencies else None,
        "latencies_ms": latencies,
        "pass": bool(ok_action and ok_content and ok_neg),
        "sent_char_len": len(raw),
    }


def markers_greeting(text):
    return any(k in text for k in ("你好", "记忆助手", "帮助", "本地 14B"))


def markers_refusal(text):
    return any(k in text for k in ("没有提到", "不想猜", "记忆里没有",
                                   "没有这条", "未提及"))


def markers_plate(text):
    return "京A88888" in text or "8888" in text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=float, default=600.0)
    ap.add_argument("--out", default=str(ART))
    ap.add_argument("--host", default=WS_HOST)
    ap.add_argument("--port", type=int, default=WS_PORT)
    a = ap.parse_args()

    started = time.time()
    token = TOKEN_FILE.read_text(encoding="utf-8").strip() if TOKEN_FILE.exists() else ""
    if not token:
        print(json.dumps({"status": "FAIL", "reason": "token file missing/empty",
                          "path": str(TOKEN_FILE)}, ensure_ascii=False, indent=1))
        return 2

    up, waited = wait_bridge(a.host, a.port, a.wait)
    out = {
        "schema": "qq_e2e_accept_v1",
        "role": "independent QQ link acceptance: simulated NapCat (OneBot v11 "
                "reverse WS client); no QQ login",
        "endpoint": "ws://%s:%d" % (a.host, a.port),
        "token_source": {"path": "third_party/qq_token.txt",
                         "token_len": len(token), "token_persisted": False},
        "auth_header": "Authorization: Bearer <redacted>",
        "bridge_wait_s": waited,
        "bridge_up": up,
        "events": [], "cases": [], "started_at": time.strftime(
            "%Y-%m-%dT%H:%M:%S%z"),
    }
    if not up:
        out.update({"status": "未接上", "pass": False,
                    "reason": "bridge not listening within %.0fs" % a.wait})
        _write(a.out, out)
        print(json.dumps({"status": out["status"], "pass": False,
                          "reason": out["reason"]}, ensure_ascii=False))
        return 4

    try:
        ws, handshake = WS, None
        ws, handshake = ws_connect(a.host, a.port, token)
        out["handshake"] = handshake
    except Exception as exc:  # noqa: BLE001
        out.update({"status": "未接上", "pass": False,
                    "reason": "ws handshake failed: %s" % exc})
        _write(a.out, out)
        print(json.dumps({"status": out["status"], "pass": False,
                          "reason": out["reason"]}, ensure_ascii=False))
        return 4

    cases = [
        ("group_at_greeting", group_at_event("你好", 1), "send_group_msg",
         markers_greeting, False),
        ("group_at_no_memory_fact", group_at_event("我明天要去哪里出差？", 2),
         "send_group_msg", markers_refusal, False),
        ("private_plate_memory", private_event("我的车牌号是多少？", 3),
         "send_private_msg", markers_plate, False),
        ("group_not_at_control", group_plain_event("这是一条普通群消息", 4),
         None, lambda t: True, True),
    ]
    for name, event, expect, checker, neg in cases:
        rec = run_case(ws, name, event, expect, checker, negative=neg)
        rec["event_type"] = {"group_at_greeting": "group @bot 你好",
                             "group_at_no_memory_fact":
                                 "group @bot 我明天要去哪里出差？",
                             "private_plate_memory":
                                 "private 我的车牌号是多少？",
                             "group_not_at_control":
                                 "group 不 @（负测试）"}[name]
        out["cases"].append(rec)
    try:
        ws.close()
    except Exception:  # noqa: BLE001
        pass

    passed = sum(1 for c in out["cases"] if c["pass"])
    out.update({
        "n_cases": len(out["cases"]), "n_pass": passed,
        "elapsed_s": round(time.time() - started, 3),
        "pass": passed == len(out["cases"]),
        "status": "pass" if passed == len(out["cases"]) else "fail",
        "expected": {
            "greeting": "固定问候句（含「你好」/「记忆助手」）",
            "no_memory_fact": "固定拒答（含「没有提到」/「不想猜」/「记忆里没有」）",
            "private_plate": "长期记忆命中返回 京A88888（有记忆事实，不拒答）",
            "not_at_control": "群里不 @ 不应触发任何发送",
        },
        "notes": [
            "本件是模拟 NapCat 客户端的链路验收（OneBot v11 反向 WS）；未登录 QQ。",
            "token 只在内存中使用；产物只记录长度与来源路径，不落 token 明文。",
            "真实 QQ 号验收（扫码登录后）见 docs/QQ-ACCEPTANCE.md；本件不得作为"
            "“真号已验收”证据。",
            "bridge 侧只读事件与动作，不改代码/配置；数据目录与 token 未改动。",
        ],
    })
    _write(a.out, out)
    print(json.dumps({
        "status": out["status"], "pass": out["pass"],
        "n_pass": passed, "n_cases": len(out["cases"]),
        "artifact": a.out,
        "sha256": hashlib.sha256(Path(a.out).read_bytes()).hexdigest(),
        "cases": [{"name": c["name"], "action": c.get("action_got"),
                   "latency_ms": c.get("latency_ms"),
                   "pass": c["pass"],
                   "msg_sample": (c.get("messages") or [""])[0][:80]}
                  for c in out["cases"]],
    }, ensure_ascii=False, indent=1))
    return 0 if out["pass"] else 3


def _write(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(p) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, p)


if __name__ == "__main__":
    sys.exit(main())