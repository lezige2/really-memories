# -*- coding: utf-8 -*-
"""test_watchdog_cpu.py -- /ask 看门狗：超时 503、服务存活、随后恢复。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chat_daily as D
import chat_service as S

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else " " + str(detail)))


class SlowApp:
    class Eng:
        mode = "real"
        def bytes_per_token(self):
            return 1024
    eng = Eng()
    logger = None
    session_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_wd_sess.json")

    def __init__(self, delay):
        self.delay = delay
        self.calls = 0

    def ask(self, text):
        self.calls += 1
        time.sleep(self.delay)
        return {"answer": "ok", "block_ids": []}

    def health(self):
        return {"status": "ok"}

    def status(self):
        return {"status": "ok"}


def main():
    app = SlowApp(1.2)
    svc = S.Service(app, host="127.0.0.1", port=0)
    svc.ask_timeout = 0.25
    t0 = time.time()
    try:
        svc.dispatch("POST", "/ask", {"text": "慢请求"})
        check("watchdog_timeout_raised", False, "no error")
    except D.DailyError as exc:
        check("watchdog_timeout_raised", exc.code == "ask_timeout", exc.code)
        check("watchdog_elapsed", time.time() - t0 < 1.0, time.time() - t0)
    h = svc.dispatch("GET", "/health", {})
    check("watchdog_health_alive", h.get("status") == "ok", h)
    check("watchdog_degraded_marked", svc.service_info().get("degraded") is True,
          svc.service_info())
    # worker 收尾后恢复；rollover/慢 ask 不会被看门狗杀
    time.sleep(1.3)
    check("watchdog_recovers", svc.degraded is False, svc.degraded)
    check("slow_worker_finishes_after_timeout", app.calls == 1, app.calls)

    # 快请求正常
    fast = SlowApp(0.0)
    svc2 = S.Service(fast, host="127.0.0.1", port=0)
    r = svc2.dispatch("POST", "/ask", {"text": "hi"})
    check("watchdog_fast_ok", r.get("answer") == "ok", r)
    bad = [c for c in CHECKS if not c[1]]
    print("%d checks, %d failed" % (len(CHECKS), len(bad)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
