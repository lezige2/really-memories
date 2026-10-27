# -*- coding: utf-8 -*-
"""test_chat_service_cpu.py -- C 版本地 HTTP 服务的零 GPU 测试。

覆盖：全部 REST 端点、串行排队（in_flight_max == 1）、错误码（400/404/405）、
慢客户端读超时、进程退出后端口释放。使用 --fake-engine（StubEngine，不加载模型）。

运行： python -X utf8 tools/test_chat_service_cpu.py ; exit 0 = 全过
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


def http(base, method, path, obj=None, headers=None, timeout=20):
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
            payload = json.loads(body)
        except ValueError:
            payload = {"raw": body}
        return e.code, dict(e.headers), payload


def wait_health(base, proc, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            return False, "process exited rc=%r" % proc.poll()
        try:
            st, _, body = http(base, "GET", "/health", timeout=3)
            if st == 200 and body.get("status") == "ok":
                return True, ""
        except Exception:                                    # noqa: BLE001
            pass
        time.sleep(0.25)
    return False, "health timeout"


def port_free(port, timeout=8.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            s.close()
            return True
        except OSError:
            s.close()
            time.sleep(0.2)
    return False


def main():
    tmp = tempfile.mkdtemp(prefix="svc_cpu_")
    port = free_port()
    base = "http://127.0.0.1:%d" % port
    out = open(os.path.join(tmp, "service.log"), "w+", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", SCRIPT, "--fake-engine",
         "--port", str(port), "--data-dir", tmp,
         "--read-timeout", "1.5", "--queue-timeout", "20"],
        cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
    try:
        up, err = wait_health(base, proc)
        check("T1.health_up", up, err)
        if not up:
            return 1

        # T2 REST 端点
        st, _, body = http(base, "GET", "/health")
        for k in ("status", "model_pin", "dll_pin", "vram_gib", "memories", "session",
                  "service"):
            check("T2.health.%s" % k, k in body, sorted(body.keys()))
        check("T2.health.fake", body["service"]["fake_engine"] is True, str(body["service"]))

        st, _, b = http(base, "POST", "/remember",
                        {"text": "我的工位在 6 楼 B 区，分机号 8042。"})
        check("T2.remember", st == 200 and b["id"] >= 1 and b["len_tokens"] > 0, str(b))
        m1 = b["id"]
        http(base, "POST", "/remember",
             {"text": "我每周三晚上 7 点有组会，地点在 2 号会议室。"})
        http(base, "POST", "/remember",
             {"text": "本周要交周报、周三体检、周五复盘；咖啡不加糖。"})
        st, _, mem = http(base, "GET", "/memories")
        check("T2.memories", st == 200 and len(mem) == 3, str(mem)[:300])
        check("T2.memories_fields",
              all(k in mem[0] for k in ("id", "first_line", "len", "created_at")),
              str(mem[0]))
        st, _, b = http(base, "POST", "/ask", {"text": "每周三晚上的组会在哪个会议室？"})
        check("T2.ask_hit", st == 200 and b.get("refused") is False and b.get("block_ids"),
              str(b))
        check("T2.ask_latency", isinstance(b.get("latency_s"), (int, float)), str(b))
        st, _, b = http(base, "POST", "/ask", {"text": "我的车牌号是多少？"})
        check("T2.ask_refuse", st == 200 and b.get("refused") is True, str(b))

        # T3 串行排队
        results = []
        errs = []

        def worker():
            try:
                results.append(http(base, "POST", "/ask",
                                    {"text": "介绍一下长城的历史"}, timeout=30))
            except Exception as exc:                        # noqa: BLE001
                errs.append(repr(exc))

        ts = [threading.Thread(target=worker) for _ in range(3)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        check("T3.concurrent_all_200", len(results) == 3 and all(r[0] == 200 for r in results),
              "results=%d errs=%r" % (len(results), errs))
        st, _, body = http(base, "GET", "/status")
        svc = body.get("service", {})
        check("T3.serial", svc.get("in_flight_max") == 1, str(svc))
        check("T3.serial_flag", svc.get("serial") is True, str(svc))
        check("T3.engine_max_active",
              body.get("engine", {}).get("max_active_asks") == 1,
              str(body.get("engine")))

        # T4 save/load
        spath = os.path.join(tmp, "sessions", "svc-save.json")
        st, _, b = http(base, "POST", "/save", {"path": spath})
        check("T4.save", st == 200 and len(b.get("sha16", "")) == 16 and
              os.path.exists(b.get("path", "")), str(b))
        st, _, b2 = http(base, "POST", "/load", {"path": spath})
        check("T4.load", st == 200 and len(b2.get("sha16", "")) == 16, str(b2))

        # T5 forget
        st, _, b = http(base, "POST", "/forget", {"id": m1})
        check("T5.forget", st == 200 and b.get("deleted") == 1, str(b))
        st, _, mem = http(base, "GET", "/memories")
        check("T5.memories_left", len(mem) == 2, str(mem))

        # T6 错误码
        st, _, b = http(base, "GET", "/nope")
        check("T6.404", st == 404 and b.get("error", {}).get("code") == "not_found", str(b))
        st, _, b = http(base, "GET", "/ask")
        check("T6.405", st == 405 and b.get("error", {}).get("code") == "method_not_allowed",
              str(b))
        st, _, b = http(base, "POST", "/ask", {})
        check("T6.400", st == 400 and b.get("error", {}).get("code") == "bad_request",
              str(b))
        st, _, b = http(base, "POST", "/forget", {"id": 999})
        check("T6.404_forget", st == 404, str(b))
        st, _, b = http(base, "POST", "/load", {"path": os.path.join(tmp, "none.json")})
        check("T6.404_load", st == 404, str(b))
        req = urllib.request.Request(base + "/ask", data=b"{bad json",
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10)
            st = 200
        except urllib.error.HTTPError as e:
            st = e.code
        check("T6.400_badjson", st == 400, "status=%r" % st)

        # T7 慢客户端读超时（服务端 --read-timeout 1.5s 后断开；进程不崩）
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        s.sendall(b"POST /ask HTTP/1.1\r\nHost: x\r\nContent-Length: 200\r\n\r\n"
                  b"{\"text\": ")
        t0 = time.time()
        closed = False
        s.settimeout(6)
        try:
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    closed = True
                    break
        except socket.timeout:
            closed = False
        except OSError:
            closed = True
        elapsed = time.time() - t0
        s.close()
        check("T7.read_timeout", closed and elapsed < 5.0,
              "closed=%r elapsed=%.1fs" % (closed, elapsed))
        st, _, _ = http(base, "GET", "/health")
        check("T7.alive_after_timeout", st == 200, "status=%r" % st)

        # T8 X-Session-Id
        st, hdrs, b = http(base, "POST", "/ask",
                           {"text": "介绍一下长城的历史"},
                           headers={"X-Session-Id": "s-test-0001"})
        check("T8.session_header", hdrs.get("X-Session-Id") == "s-test-0001",
              str(hdrs.get("X-Session-Id")))
        check("T8.session_file",
              os.path.exists(os.path.join(tmp, "assistant", "sessions",
                                          "s-test-0001.jsonl")),
              "session file missing")
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(10)
        out.flush()
        try:
            out.seek(0)
            log_text = out.read()
        except Exception:                                    # noqa: BLE001
            log_text = ""
        out.close()
        check("T9.port_released", port_free(port), "port %d still busy" % port)
        check("T9.no_traceback_in_log", "Traceback (most recent call last)" not in log_text,
              log_text[-400:])
        try:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:                                    # noqa: BLE001
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