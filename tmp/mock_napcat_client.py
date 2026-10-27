# -*- coding: utf-8 -*-
"""tmp/mock_napcat_client.py -- mock NapCat 反向 WS 客户端（验证 qq_bridge）。

- 从环境变量 QQ_BRIDGE_TOKEN 读 token（不打印）；
- 先带错误 token 握手，期望 401；
- 再带正确 token 连 ws://127.0.0.1:8766/，发一条群 @机器人 消息，
  对 bridge 下发的 send_group_msg 动作回 {"status":"ok","retcode":0,...}，
  记录动作与回答摘要，输出 JSON（不含 token）。
用法：QQ_BRIDGE_TOKEN=... python -X utf8 tmp/mock_napcat_client.py --out tmp/qq_mock_result.json
"""

import argparse
import json
import os
import sys
import time

try:
    import websocket
except ImportError:                                      # pragma: no cover
    print("need websocket-client", file=sys.stderr)
    sys.exit(2)

WS_URL = "ws://127.0.0.1:8766/"
BOT_QQ = "10000"
GROUP_ID = 123456789
USER_ID = 10001


def now():
    return time.time()


def connect(token, extra_headers=None):
    headers = ["Authorization: Bearer " + token]
    if extra_headers:
        headers += extra_headers
    return websocket.create_connection(WS_URL, header=headers, timeout=10,
                                       enable_multithread=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("tmp", "qq_mock_result.json"))
    ap.add_argument("--timeout", type=float, default=180.0)
    a = ap.parse_args(argv)
    token = os.environ.get("QQ_BRIDGE_TOKEN", "")
    if not token:
        print("QQ_BRIDGE_TOKEN not set", file=sys.stderr)
        return 2
    result = {"schema": "qq_bridge_mock_v1", "ts": now(), "ws_url": WS_URL,
              "wrong_token": None, "connected": False, "event_sent": False,
              "actions": [], "responses": 0, "errors": [], "reply_excerpt": None,
              "assistant_latency_s": None}
    # 1) 错误 token 必须被拒
    try:
        bad = connect("definitely-wrong-token")
        result["wrong_token"] = {"accepted": True, "status_code": 101}
        bad.close()
    except websocket.WebSocketBadStatusException as exc:
        result["wrong_token"] = {"accepted": False,
                                 "status_code": int(getattr(exc, "status_code", 0))}
    except Exception as exc:                             # noqa: BLE001
        result["wrong_token"] = {"accepted": False, "error": type(exc).__name__}
    # 2) 正确 token：连入 + 发群消息 + 回收 bridge 动作
    try:
        ws = connect(token)
        result["connected"] = True
    except Exception as exc:                             # noqa: BLE001
        result["errors"].append("connect: %s: %s" % (type(exc).__name__, exc))
        _write(a.out, result)
        return 1
    event = {
        "post_type": "message", "message_type": "group", "sub_type": "normal",
        "message_id": 90001, "group_id": GROUP_ID, "user_id": USER_ID,
        "self_id": int(BOT_QQ), "time": int(time.time()),
        "raw_message": "[CQ:at,qq=%s] 你好" % BOT_QQ,
        "message": [{"type": "at", "data": {"qq": BOT_QQ}},
                    {"type": "text", "data": {"text": " 你好"}}],
        "sender": {"nickname": "mock"},
    }
    try:
        ws.send(json.dumps(event, ensure_ascii=False))
        result["event_sent"] = True
    except Exception as exc:                             # noqa: BLE001
        result["errors"].append("send_event: %s" % type(exc).__name__)
    deadline = now() + float(a.timeout)
    got_reply = False
    while now() < deadline and not got_reply:
        try:
            raw = ws.recv()
        except websocket.WebSocketTimeoutException:
            continue
        except Exception as exc:                         # noqa: BLE001
            result["errors"].append("recv: %s" % type(exc).__name__)
            break
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except ValueError:
            result["errors"].append("non-json frame")
            continue
        action = msg.get("action")
        if not action:
            continue
        params = msg.get("params") or {}
        rec = {"action": action, "echo": msg.get("echo")}
        if "group_id" in params:
            rec["group_id"] = params.get("group_id")
        if isinstance(params.get("message"), str):
            rec["message_chars"] = len(params["message"])
            rec["message_excerpt"] = params["message"][:120]
            if action == "send_group_msg":
                result["reply_excerpt"] = params["message"][:220]
                got_reply = True
        result["actions"].append(rec)
        ws.send(json.dumps({"status": "ok", "retcode": 0, "data": {"message_id": 1},
                            "echo": msg.get("echo")}, ensure_ascii=False))
        result["responses"] += 1
    try:
        ws.close()
    except Exception:                                    # noqa: BLE001
        pass
    result["ok"] = (result["connected"] and result["event_sent"]
                    and got_reply
                    and result["wrong_token"] is not None
                    and result["wrong_token"].get("status_code") == 401)
    _write(a.out, result)
    print(json.dumps({"ok": result["ok"],
                      "wrong_token_status": (result["wrong_token"] or {}).get("status_code"),
                      "connected": result["connected"],
                      "actions": [x["action"] for x in result["actions"]],
                      "reply_chars": len(result.get("reply_excerpt") or "")},
                     ensure_ascii=False))
    return 0 if result["ok"] else 1


def _write(path, obj):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


if __name__ == "__main__":
    sys.exit(main())