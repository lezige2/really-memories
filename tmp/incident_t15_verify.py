#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P0 事故 T15：chat_daily.py 恢复/重建版本的独立验收。

检查项（逐项 pass/fail + sha256）：
  A) 静态：py_compile、import、tools/check_chat_daily.py rc=0（17 方法存在性）
  B) CPU 测试全绿：chat_daily(93) / retrieval / refusal / rollover / rollover_hier /
     slots(43) / retrieval_service / verify_wiring(42)
  C) fake 引擎冒烟：3 句（不能 500、不能政策复读）；含 fake-engine HTTP 服务 200 冒烟
  D) 线上六用例（服务由 LEAD 重启后）：下周三→广州、下周五→成都、我叫什么→阿泽、
     组会→B座302、养猫→豆豆、明天→没提过（服务不可达时记 pending，不算 fail）

产出：out/INCIDENT-T15-VERIFY.json（只写该件）。
零 GPU、不联网外部；不跑真实模型（C 用 StubEngine/fake-engine）。
"""
import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
TOOLS = ROOT / "tools"
ART = ROOT / "out" / "INCIDENT-T15-VERIFY.json"

SUITE = [
    ("chat_daily", "test_chat_daily_cpu.py", 93),
    ("retrieval", "test_retrieval_cpu.py", None),
    ("refusal", "test_refusal_cpu.py", None),
    ("rollover", "test_rollover_cpu.py", None),
    ("rollover_hier", "test_rollover_hier_cpu.py", None),
    ("slots", "test_slots_cpu.py", 43),
    ("retrieval_service", "test_retrieval_service_cpu.py", None),
    ("verify_wiring", "test_verify_wiring_cpu.py", 42),
]
SMOKE_PROMPTS = ["你好", "我下周三去哪开会？", "我的车牌号是多少？"]
POLICY_MARKERS = ("你是用户的本地记忆助手", "规则：", "不要输出思考过程",
                  "只依据记忆回答", "SYSTEM_POLICY", "只输出一行回答",
                  "若有多条相似记忆")
ONLINE = [
    {"q": "我下周三去哪开会？", "expect_contains": ["广州"], "label": "下周三→广州"},
    {"q": "我下周五去哪？", "expect_contains": ["成都"], "label": "下周五→成都"},
    {"q": "我叫什么名字？", "expect_contains": ["阿泽"], "label": "我叫什么→阿泽"},
    {"q": "组会在哪开？", "expect_contains": ["B座302", "B 座 302"],
     "label": "组会→B座302"},
    {"q": "我养的猫叫什么？", "expect_contains": ["豆豆"], "label": "养猫→豆豆"},
    {"q": "我明天去哪出差？", "expect_contains": [],
     "expect_refusal_markers": ["没提过", "没跟我提过", "没有提到", "未提及",
                                "不知道", "不想猜", "记忆里没有", "没有这条",
                                "没法从记忆里核对", "没法确认", "记不清"],
     "label": "明天→没提过"},
]


def sha256_file(p):
    b = Path(p).read_bytes()
    return hashlib.sha256(b).hexdigest()


def run(cmd, timeout=900, env=None):
    t0 = time.time()
    e = dict(os.environ)
    # 不注入 LLAMA_MEM_MODE：各测试脚本自己声明 strict/natural；
    # 注入会改变它们断言所依赖的运行模式（曾导致误判 chat_daily/retrieval/rollover 红）。
    if env:
        e.update(env)
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout,
                           env=e)
        return {"cmd": " ".join(cmd), "rc": r.returncode,
                "elapsed_s": round(time.time() - t0, 2),
                "stdout_tail": r.stdout[-2000:], "stderr_tail": r.stderr[-1500:]}
    except subprocess.TimeoutExpired as exc:
        return {"cmd": " ".join(cmd), "rc": "TIMEOUT",
                "elapsed_s": round(time.time() - t0, 2),
                "stdout_tail": str(exc.stdout or "")[-1000:],
                "stderr_tail": "timeout"}


def parse_counts(text):
    import re
    t = text or ""
    checks = failed = None
    m = re.search(r"checks\s*=\s*(\d+)", t)
    if m:
        checks = int(m.group(1))
    m = re.search(r"failed\s*=\s*(\d+)", t)
    if m:
        failed = int(m.group(1))
    if checks is None:
        m = re.search(r"(\d+)\s*checks\b[^\n]*?(\d+)\s*failed", t)
        if m:
            checks, failed = int(m.group(1)), int(m.group(2))
    if checks is None:
        m = re.search(r"(\d+)\s*/\s*(\d+)\s+passed", t)
        if m:
            checks, failed = int(m.group(2)), int(m.group(1)) and \
                max(0, int(m.group(2)) - int(m.group(1)))
    if checks is None:
        m = re.search(r"(\d+)\s*checks?\b", t)
        if m:
            checks = int(m.group(1))
            if failed is None:
                failed = 0 if "ALL PASS" in t or "all pass" in t.lower() else None
    return checks, failed


# ---------------------------------------------------------------- checks ----
def check_static():
    items = []
    pyc = run([sys.executable, "-X", "utf8", "-m", "py_compile",
               "tools/chat_daily.py"], timeout=120)
    items.append({"name": "py_compile chat_daily.py",
                  "pass": pyc["rc"] == 0, "detail": pyc})
    imp = run([sys.executable, "-X", "utf8", "-c",
               "import sys;sys.path.insert(0,'tools');"
               "import chat_daily as D;"
               "print('VERSION',getattr(D,'VERSION',None));"
               "print('DailyApp_ask',hasattr(D.DailyApp,'ask'))"],
              timeout=120)
    items.append({"name": "import chat_daily",
                  "pass": imp["rc"] == 0 and "DailyApp_ask True" in imp["stdout_tail"],
                  "detail": imp})
    chk = run([sys.executable, "-X", "utf8", "tools/check_chat_daily.py"],
              timeout=180)
    missing = []
    for line in chk["stdout_tail"].splitlines():
        if line.startswith("missing_required"):
            missing = line
    items.append({"name": "tools/check_chat_daily.py rc=0 (17 methods)",
                  "pass": chk["rc"] == 0,
                  "detail": chk, "missing_line": missing})
    return items


def check_suite():
    items = []
    for name, script, expect in SUITE:
        p = TOOLS / script
        if not p.exists():
            items.append({"name": name, "script": script, "present": False,
                          "pass": False, "reason": "script missing"})
            continue
        r = run([sys.executable, "-X", "utf8", "tools/" + script],
                timeout=900)
        checks, failed = parse_counts(r["stdout_tail"])
        ok = r["rc"] == 0 and (failed in (0, None))
        if expect is not None:
            ok = ok and checks == expect
        items.append({"name": name, "script": script, "present": True,
                      "pass": bool(ok), "rc": r["rc"],
                      "checks": checks, "failed": failed,
                      "expected_checks": expect,
                      "elapsed_s": r["elapsed_s"],
                      "stdout_tail": r["stdout_tail"][-1200:],
                      "stderr_tail": r["stderr_tail"][-600:]})
    return items


def check_fake_smoke():
    """StubEngine 3 句 + fake-engine HTTP 服务 200 冒烟。"""
    out = {"inproc": [], "http": None, "pass": False}
    sys.path.insert(0, str(TOOLS))
    import chat_daily as D
    try:
        D._iso = None
    except Exception:                # noqa: BLE001
        pass
    try:
        D.web_lookup.lookup_text = lambda *a, **k: None
    except Exception:                # noqa: BLE001
        pass

    base = Path(tempfile.mkdtemp(prefix="t15_smoke_"))
    try:
        (base / "blocks").mkdir()
        (base / "sessions").mkdir()
        model = base / "stub.model"
        D.install_fake_model(str(model))
        app = D.DailyApp(D.StubEngine(), db_path=str(base / "daily.db"),
                         blocks_dir=str(base / "blocks"),
                         sessions_dir=str(base / "sessions"),
                         session_path="case.json", model_path=str(model),
                         control=False, n_predict=D.N_PREDICT_DEFAULT,
                         retrieval_mode="off", topk=D.DEFAULT_TOPK,
                         rollover_at=1.0, n_ctx=D.N_CTX_DEFAULT,
                         chat_start=D.CHAT_START_DEFAULT, n_gpu_layers=0)
        for q in SMOKE_PROMPTS:
            try:
                r = app.ask(q)
                ans = str(r.get("answer") or "")
                policy_echo = [m for m in POLICY_MARKERS if m in ans]
                out["inproc"].append({
                    "input": q, "answer": ans[:200],
                    "state": r.get("state"), "refused": r.get("refused"),
                    "has_verify": "verify" in r,
                    "policy_echo": policy_echo,
                    "pass": bool(ans) and not policy_echo,
                })
            except Exception as exc:     # noqa: BLE001
                out["inproc"].append({"input": q, "error": "%s: %s"
                                      % (type(exc).__name__, exc),
                                      "pass": False})
        app.close(save=False, reason="incident_t15")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    # fake-engine HTTP service: 3 句不得 500/政策复读
    port = None
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    data = Path(tempfile.mkdtemp(prefix="t15_svc_"))
    outp = open(data / "out.log", "w", encoding="utf-8")
    errp = open(data / "err.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", "tools/chat_service.py",
         "--fake-engine", "--data-dir", str(data / "svc"),
         "--port", str(port)],
        cwd=str(ROOT), stdout=outp, stderr=errp,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    results = []
    try:
        base_url = "http://127.0.0.1:%d" % port
        ready = False
        for _ in range(120):
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(base_url + "/health", timeout=1) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:        # noqa: BLE001
                time.sleep(0.25)
        for q in SMOKE_PROMPTS:
            entry = {"input": q, "http_status": None, "answer": None,
                     "policy_echo": [], "pass": False}
            if ready:
                try:
                    body = json.dumps({"text": q}).encode("utf-8")
                    req = urllib.request.Request(
                        base_url + "/ask", data=body,
                        headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=60) as r:
                        entry["http_status"] = r.status
                        doc = json.loads(r.read().decode("utf-8"))
                        ans = str(doc.get("answer") or "")
                        entry["answer"] = ans[:200]
                        entry["policy_echo"] = [m for m in POLICY_MARKERS
                                                if m in ans]
                        entry["pass"] = bool(ans) and not entry["policy_echo"]
                except urllib.error.HTTPError as exc:
                    entry["http_status"] = exc.code
                    entry["error"] = "HTTP %s" % exc.code
                except Exception as exc:  # noqa: BLE001
                    entry["error"] = "%s: %s" % (type(exc).__name__, exc)
            results.append(entry)
        out["http"] = {"port": port, "ready": ready, "results": results,
                       "stderr_tail": (data / "err.log").read_text(
                           encoding="utf-8", errors="replace")[-800:]}
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=8)
        except Exception:            # noqa: BLE001
            try:
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/F"],
                               capture_output=True, timeout=20)
            except Exception:        # noqa: BLE001
                pass
        outp.close()
        errp.close()
        shutil.rmtree(data, ignore_errors=True)

    inproc_ok = all(x.get("pass") for x in out["inproc"]) and \
        len(out["inproc"]) == len(SMOKE_PROMPTS)
    http_ok = bool(out["http"] and out["http"]["ready"]
                   and all(x.get("pass") for x in out["http"]["results"]))
    out["pass"] = bool(inproc_ok and http_ok)
    return out


def check_online():
    base = "http://127.0.0.1:8765"
    out = {"service": base, "ready": False, "cases": [], "pass": None}
    try:
        with urllib.request.urlopen(base + "/health", timeout=3) as r:
            if r.status == 200:
                out["ready"] = True
                out["health"] = json.loads(r.read().decode("utf-8"))
    except Exception as exc:         # noqa: BLE001
        out["error"] = "%s: %s" % (type(exc).__name__, exc)
    if not out["ready"]:
        out["status"] = "pending_service_restart"
        return out
    for c in ONLINE:
        entry = {"label": c["label"], "input": c["q"], "pass": False}
        t0 = time.perf_counter()
        try:
            body = json.dumps({"text": c["q"]}).encode("utf-8")
            req = urllib.request.Request(base + "/ask", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                doc = json.loads(r.read().decode("utf-8"))
            ans = str(doc.get("answer") or "")
            entry.update({"http_status": 200, "answer": ans[:300],
                          "state": doc.get("state"),
                          "refused": doc.get("refused"),
                          "latency_s": round(time.perf_counter() - t0, 3)})
            if c.get("expect_contains"):
                entry["pass"] = any(tok in ans for tok in c["expect_contains"])
            else:
                marks = c.get("expect_refusal_markers") or []
                entry["pass"] = any(m in ans for m in marks) or \
                    bool(doc.get("refused"))
        except urllib.error.HTTPError as exc:
            entry.update({"http_status": exc.code, "error": "HTTP %s" % exc.code})
        except Exception as exc:      # noqa: BLE001
            entry["error"] = "%s: %s" % (type(exc).__name__, exc)
        out["cases"].append(entry)
    out["pass"] = all(x.get("pass") for x in out["cases"]) if out["cases"] else False
    out["status"] = "checked"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--online-only", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    art = {"schema": "incident_t15_verify_v1",
           "role": "P0 事故 T15：chat_daily.py 恢复/重建版本独立验收",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t0)),
           "commands": {
               "static": "python -m py_compile tools/chat_daily.py；"
                         "python tools/check_chat_daily.py",
               "suite": ["python -X utf8 tools/%s" % s for _, s, _ in SUITE],
               "online": "POST http://127.0.0.1:8765/ask（六用例）",
           }}
    art["pins"] = {
        "chat_daily": {"path": "tools/chat_daily.py",
                       "sha256": sha256_file(TOOLS / "chat_daily.py"),
                       "bytes": (TOOLS / "chat_daily.py").stat().st_size},
        "check_chat_daily": {
            "path": "tools/check_chat_daily.py",
            "sha256": sha256_file(TOOLS / "check_chat_daily.py")
            if (TOOLS / "check_chat_daily.py").exists() else None},
        "answer_verifier": {
            "path": "tools/answer_verifier.py",
            "sha256": sha256_file(TOOLS / "answer_verifier.py")
            if (TOOLS / "answer_verifier.py").exists() else None},
    }
    art["checks"] = []
    if not a.online_only:
        try:
            static = check_static()
        except Exception as exc:            # noqa: BLE001
            static = [{"name": "static checks", "pass": False,
                       "error": "%s: %s" % (type(exc).__name__, exc)}]
        art["checks"].extend(static)
        try:
            suite = check_suite()
        except Exception as exc:            # noqa: BLE001
            suite = [{"name": "cpu suite", "pass": False,
                      "error": "%s: %s" % (type(exc).__name__, exc)}]
        art["checks"].extend(suite)
        try:
            smoke = check_fake_smoke()
        except Exception as exc:            # noqa: BLE001
            smoke = {"pass": False, "error": "%s: %s"
                     % (type(exc).__name__, exc)}
        art["checks"].append({"name": "fake engine smoke (3 prompts + HTTP)",
                              "pass": bool(smoke.get("pass")),
                              "detail": smoke})
    online = check_online()
    if online.get("status") != "pending_service_restart":
        art["checks"].append({"name": "online six cases (service 8765)",
                              "pass": bool(online.get("pass")),
                              "detail": online})
    else:
        art["online_pending"] = online
    local = [c for c in art["checks"] if c.get("name", "").startswith(
        ("py_compile", "import ", "tools/check", "chat_daily", "retrieval",
         "refusal", "rollover", "slots", "verify_wiring", "fake engine"))]
    art["summary"] = {
        "n_checks": len(art["checks"]),
        "n_pass": sum(1 for c in art["checks"] if c.get("pass")),
        "n_fail": sum(1 for c in art["checks"] if not c.get("pass")),
        "local_pass": all(c.get("pass") for c in local) if local else None,
        "online": ("pending_service_restart" if online.get("status")
                   == "pending_service_restart" else bool(online.get("pass"))),
        "elapsed_s": round(time.time() - t0, 2),
    }
    art["pass"] = bool(art["summary"]["local_pass"]) and (
        online.get("pass") is True) if online.get("status") != \
        "pending_service_restart" else bool(art["summary"]["local_pass"])
    art["status"] = ("pass" if art["pass"] and online.get("pass") is not False
                     else "fail") if online.get("status") != \
        "pending_service_restart" else (
        "local_pass_online_pending" if art["summary"]["local_pass"] else "fail")

    ART.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(ART) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, ART)
    print(json.dumps({
        "artifact": str(ART), "status": art["status"],
        "sha256": hashlib.sha256(ART.read_bytes()).hexdigest(),
        "bytes": ART.stat().st_size,
        "summary": art["summary"],
        "failed": [c.get("name") for c in art["checks"] if not c.get("pass")],
        "online_pending": online.get("status") == "pending_service_restart",
        "pins": art["pins"],
    }, ensure_ascii=False, indent=1))
    return 0 if art["status"] in ("pass", "local_pass_online_pending") else 1


if __name__ == "__main__":
    sys.exit(main())