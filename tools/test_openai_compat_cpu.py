# -*- coding: utf-8 -*-
import os as _os_env
_os_env.environ.setdefault("LLAMA_MEM_MODE", "strict")  # 这些用例验证 strict 模式的既有契约
"""test_openai_compat_cpu.py -- 服务层 OpenAI 兼容 API 的零 GPU 测试。

覆盖：GET /v1/models、POST /v1/chat/completions（非流式 usage、流式 SSE 分块顺序与
[DONE]）、自动记忆前缀（记住：/记一下：/remember）、超长 prompt 截断告警、
引擎错误映射（OpenAI 风格 error + 非 2xx）、并发串行（in_flight_max==1）。

运行： python -X utf8 tools/test_openai_compat_cpu.py ; exit 0 = 全过
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(HERE, "chat_service.py")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import chat_daily as D          # noqa: E402  (只取默认 n_ctx 断言)
MODEL_ID = "local-14b-memory"

FAILS = []
CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(name)
    if not cond:
        FAILS.append("%s %s" % (name, detail))
        print("FAIL %s %s" % (name, detail))
    else:
        print("ok   %s" % name)


def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def http_json(base, method, path, obj=None, headers=None, timeout=30):
    data = None if obj is None else json.dumps(obj).encode("utf-8")
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(base + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, dict(e.headers), json.loads(body)
        except ValueError:
            return e.code, dict(e.headers), {"raw": body}


def http_raw(base, method, path, obj=None, timeout=30):
    data = None if obj is None else json.dumps(obj).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, dict(r.headers), r.read().decode("utf-8")


def wait_health(base, proc, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            return False, "process exited rc=%r" % proc.poll()
        try:
            st, _, body = http_json(base, "GET", "/health", timeout=3)
            if st == 200:
                return True, ""
        except Exception:                                # noqa: BLE001
            pass
        time.sleep(0.25)
    return False, "health timeout"


def user(text):
    return [{"role": "user", "content": text}]


def main():
    tmp = tempfile.mkdtemp(prefix="oa_cpu_")
    port = free_port()
    base = "http://127.0.0.1:%d" % port
    logf = open(os.path.join(tmp, "service.log"), "w+", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", SCRIPT, "--fake-engine",
         "--port", str(port), "--data-dir", tmp,
         "--read-timeout", "30", "--queue-timeout", "20",
         "--sessions", os.path.join(tmp, "sessions"),
         "--session", "svc_smoke.json"],
        cwd=ROOT, stdout=logf, stderr=subprocess.STDOUT)
    try:
        up, err = wait_health(base, proc)
        check("T1.up", up, err)
        if not up:
            return 1

        # T2 /v1/models
        st, _, body = http_json(base, "GET", "/v1/models")
        ok = (st == 200 and body.get("object") == "list" and len(body.get("data", [])) == 1)
        m = body.get("data", [{}])[0]
        check("T2.models", ok, str(body))
        check("T2.model_id", m.get("id") == MODEL_ID, str(m))
        check("T2.model_ctx", m.get("context_window") == D.N_CTX_DEFAULT, str(m))
        check("T2.model_owned", m.get("owned_by") == "llama-mem", str(m))

        # T3 自动记忆前缀（三种写法）
        for i, pfx in enumerate(("记住：", "记一下：", "/remember ")):
            st, _, b = http_json(base, "POST", "/v1/chat/completions",
                                 {"model": MODEL_ID,
                                  "messages": user(pfx + "待办：本周五复盘，编号 TO-%d。" % i)})
            content = b["choices"][0]["message"]["content"]
            check("T3.%d.remember" % i, st == 200 and "已记住" in content, str(b)[:300])
        st, _, mem = http_json(base, "GET", "/memories")
        check("T3.memories_count", len(mem) == 3, str(mem)[:300])

        # T4 非流式完成 + usage
        st, _, b = http_json(base, "POST", "/v1/chat/completions",
                             {"model": MODEL_ID, "messages": user("本周要交什么？"),
                              "max_tokens": 64, "temperature": 0.0})
        check("T4.status", st == 200, str(b)[:300])
        check("T4.object", b.get("object") == "chat.completion", str(b.get("object")))
        check("T4.role", b["choices"][0]["message"]["role"] == "assistant", str(b)[:300])
        check("T4.finish", b["choices"][0]["finish_reason"] == "stop", str(b)[:300])
        usage = b.get("usage", {})
        check("T4.usage", all(isinstance(usage.get(k), int)
                              for k in ("prompt_tokens", "completion_tokens",
                                        "total_tokens")), str(usage))
        content = b["choices"][0]["message"]["content"]
        check("T4.content_nonempty", isinstance(content, str) and content, str(b)[:300])

        # T5 SSE 流式：分块顺序、拼接内容、finish_reason、[DONE]
        st, hdrs, raw = http_raw(base, "POST", "/v1/chat/completions",
                                 {"model": MODEL_ID,
                                  "messages": user("本周要交什么？"), "stream": True})
        check("T5.status", st == 200, str(st))
        check("T5.content_type", "text/event-stream" in hdrs.get("Content-Type", ""),
              str(hdrs))
        events = [ln[len("data: "):] for ln in raw.splitlines()
                  if ln.startswith("data: ")]
        check("T5.has_done", events and events[-1] == "[DONE]", str(events[-3:]))
        chunks = []
        final = None
        for ev in events:
            if ev == "[DONE]":
                continue
            obj = json.loads(ev)
            if obj.get("object") == "chat.completion.chunk":
                delta = obj["choices"][0].get("delta", {})
                if delta.get("content"):
                    chunks.append(delta["content"])
                if obj["choices"][0].get("finish_reason") == "stop":
                    final = obj
        joined = "".join(chunks)
        check("T5.stream_chunks", len(chunks) >= 1, "chunks=%d" % len(chunks))
        check("T5.stream_joined", joined == content,
              "stream=%r nonstream=%r" % (joined, content))
        check("T5.finish_stop", final is not None, "no finish_reason=stop chunk")
        # 顺序：chunk 的 id 全一致
        ids = {json.loads(e)["id"] for e in events if e != "[DONE]"}
        check("T5.stream_same_id", len(ids) == 1, str(ids))

        # T6 超长 prompt => 截断到预算并写 warning（用独立服务进程，避免撑爆主服务 chat 窗口）
        port2 = free_port()
        tmp2 = os.path.join(tmp, "longprompt")
        os.makedirs(tmp2, exist_ok=True)
        logf2 = open(os.path.join(tmp, "service-long.log"), "w+", encoding="utf-8")
        proc2 = subprocess.Popen(
            [sys.executable, "-X", "utf8", SCRIPT, "--fake-engine",
             "--port", str(port2), "--data-dir", tmp2,
             "--read-timeout", "30", "--queue-timeout", "20",
         "--sessions", os.path.join(tmp, "sessions"),
         "--session", "svc_smoke.json"],
            cwd=ROOT, stdout=logf2, stderr=subprocess.STDOUT)
        try:
            up2, err2 = wait_health("http://127.0.0.1:%d" % port2, proc2)
            check("T6.service_up", up2, err2)
            long_text = "本周任务：" + ("整理会议纪要并同步给组内同事；" * 1800) + "完。"
            st, _, b = http_json("http://127.0.0.1:%d" % port2, "POST",
                                 "/v1/chat/completions",
                                 {"model": MODEL_ID, "messages": user(long_text)},
                                 timeout=60)
            check("T6.status", st == 200, str(b)[:300])
            sess2 = os.path.join(tmp2, "assistant", "sessions")
            files2 = ([os.path.join(sess2, f) for f in os.listdir(sess2)]
                      if os.path.isdir(sess2) else [])
            warns = []
            for p in files2:
                for line in open(p, encoding="utf-8"):
                    obj = json.loads(line)
                    if (obj.get("event") == "warning"
                            and obj.get("code") == "prompt_truncated"):
                        warns.append(obj)
            check("T6.truncation_warning", len(warns) >= 1,
                  "no prompt_truncated warning; files=%d" % len(files2))
            check("T6.warning_fields", bool(warns) and
                  warns[0].get("evidence", {}).get("orig_chars", 0) > 0,
                  str(warns[:1])[:300])
        finally:
            proc2.terminate()
            try:
                proc2.wait(10)
            except subprocess.TimeoutExpired:
                proc2.kill()
                proc2.wait(10)
            logf2.close()
            try:
                import shutil
                shutil.rmtree(tmp2, ignore_errors=True)
            except Exception:                            # noqa: BLE001
                pass

        # T7 引擎错误映射（StubEngine 的测试钩子）
        st, _, b = http_json(base, "POST", "/v1/chat/completions",
                             {"model": MODEL_ID, "messages": user("__STUB_ERROR__")})
        check("T7.error_status", st >= 400, "status=%r" % st)
        check("T7.error_shape", isinstance(b.get("error"), dict) and
              all(k in b["error"] for k in ("message", "type", "code")), str(b)[:300])
        check("T7.error_type", b["error"]["type"] in ("server_error", "invalid_request_error"),
              str(b)[:300])

        # T8 缺 messages => OpenAI 风格 400
        st, _, b = http_json(base, "POST", "/v1/chat/completions", {"model": MODEL_ID})
        check("T8.400", st == 400 and b.get("error", {}).get("type") == "invalid_request_error",
              str(b)[:300])

        # T9 并发串行
        results = []

        def worker():
            try:
                results.append(http_json(base, "POST", "/v1/chat/completions",
                                         {"model": MODEL_ID,
                                          "messages": user("介绍一下长城的历史")},
                                         timeout=60)[0])
            except Exception as exc:                    # noqa: BLE001
                results.append("ERR:%r" % exc)

        ts = [threading.Thread(target=worker) for _ in range(3)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(60)
        check("T9.all_200", results == [200, 200, 200] or all(r == 200 for r in results),
              str(results))
        st, _, body = http_json(base, "GET", "/status")
        svc = body.get("service", {})
        check("T9.serial", svc.get("in_flight_max") == 1, str(svc))

        # T9b think 标签与问答模板回显：服务端必须只回可见答案
        st, _, b = http_json(base, "POST", "/v1/chat/completions",
                             {"model": MODEL_ID, "messages": user("__STUB_THINK__")})
        content = b["choices"][0]["message"]["content"]
        bad = [x for x in ("think", "答：", "我的车型", "？", "?") if x in content]
        check("T9b.nonstream_no_think_echo", st == 200 and not bad,
              "bad=%r content=%r" % (bad, content))
        st, _, raw = http_raw(base, "POST", "/v1/chat/completions",
                              {"model": MODEL_ID, "messages": user("__STUB_THINK__"),
                               "stream": True})
        streamed = "".join(
            json.loads(ev)["choices"][0].get("delta", {}).get("content", "")
            for ev in (ln[6:] for ln in raw.splitlines() if ln.startswith("data: "))
            if ev != "[DONE]")
        bad2 = [x for x in ("think", "答：", "我的车型", "？", "?") if x in streamed]
        check("T9b.stream_no_think_echo", not bad2,
              "bad=%r streamed=%r" % (bad2, streamed))

        # T10 X-Session-Id 响应头
        st, hdrs, b = http_json(base, "POST", "/v1/chat/completions",
                                {"model": MODEL_ID, "messages": user("介绍一下长城")},
                                headers={"X-Session-Id": "s-oa-0001"})
        check("T10.header", hdrs.get("X-Session-Id") == "s-oa-0001",
              str(hdrs.get("X-Session-Id")))
        _, _, askb = http_json(base, "POST", "/v1/chat/completions",
                               {"model": MODEL_ID, "messages": user("介绍一下长城")})
        # 会话路径检查放到 /status（ask 返回不含 session 时用 /save）
        st, _, sv = http_json(base, "POST", "/save", {})
        check("T10.session_path", sv.get("path", "").replace("/", "\\")
              .endswith("sessions\\svc_smoke.json"), str(sv))
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(10)
        logf.flush()
        try:
            logf.seek(0)
            log_text = logf.read()
        except Exception:                                # noqa: BLE001
            log_text = ""
        logf.close()
        check("T11.no_traceback", "Traceback (most recent call last)" not in log_text,
              log_text[-500:])
        try:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:                                # noqa: BLE001
            pass
    print("\n%d checks, %d failed" % (len(CHECKS), len(FAILS)))
    if FAILS:
        print("FAILURES:")
        for f in FAILS:
            print(" - %s" % f)
        return 1
    print("ALL PASS (zero GPU / fake engine)")
    return 0


if __name__ == "__main__":
    sys.exit(main())