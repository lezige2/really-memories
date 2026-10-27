#!/usr/bin/env python3
"""Minimal OpenAI-compatible mock for DSH provider-route verification.

Endpoints (bound to 127.0.0.1:8765 by default):
  GET  /v1/models            -> {"object":"list","data":[{"id":"local14b",...}]}
  POST /v1/chat/completions  -> SSE stream (data: {...}\n\n ... data: [DONE])
  GET  /health               -> {"ok":true}

No model, no GPU, no network: answers are canned echoes. Purpose is only to prove
the wire shape DSH/pi-ai needs (stream=true SSE + [DONE], /v1/models listing).
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_ID = "local14b"
CREATED = int(time.time())


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quiet
        pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] in ("/v1/models", "/models"):
            self._json(200, {"object": "list", "data": [{"id": MODEL_ID, "object": "model", "owned_by": "local"}]})
        elif self.path.split("?")[0] in ("/health", "/status"):
            self._json(200, {"ok": True, "model": MODEL_ID})
        else:
            self._json(404, {"error": {"message": "not found", "type": "invalid_request_error"}})

    def do_POST(self):
        if self.path.split("?")[0] not in ("/v1/chat/completions", "/chat/completions"):
            self._json(404, {"error": {"message": "not found"}})
            return
        length = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            request = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": {"message": "bad json"}})
            return
        messages = request.get("messages") or []
        last_user = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                last_user = str(message.get("content") or "")
                break
        tool_count = len(request.get("tools") or [])
        reply = f"[mock {MODEL_ID}] 收到 {len(messages)} 条消息，tools={tool_count}；最后一条用户消息：{last_user[:80]}"

        self.send_response(200)
        self.send_header("content-type", "text/event-stream; charset=utf-8")
        self.send_header("cache-control", "no-cache")
        self.send_header("connection", "keep-alive")
        self.end_headers()

        def emit(obj):
            self.wfile.write(("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n").encode("utf-8"))
            self.wfile.flush()

        base = {"id": "chatcmpl-mock", "object": "chat.completion.chunk", "created": CREATED, "model": MODEL_ID}
        emit({**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]})
        for piece in [reply[i : i + 12] for i in range(0, len(reply), 12)]:
            emit({**base, "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]})
            time.sleep(0.01)
        emit({**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
        if request.get("stream_options", {}).get("include_usage"):
            emit({**base, "choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": len(reply), "total_tokens": 12 + len(reply)}})
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"mock listening on http://127.0.0.1:{port}/v1", flush=True)
    server.serve_forever()