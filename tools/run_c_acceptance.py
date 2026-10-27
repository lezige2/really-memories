# -*- coding: utf-8 -*-
"""run_c_acceptance.py -- C 版验收臂：按 PRODUCT-C-SPEC 自动跑 S1–S6 + S7a–S7d。

被验收对象：tools/chat_daily.py（子进程 stdin/stdout 驱动；每个场景独立 DB/块/会话/日志目录）。
本脚本 CPU 可跑：`--dry-run` 用 StubEngine 子进程跑通框架（零 GPU）；真机模式由 LEAD 在 GPU 机器上
运行，外部采样显存峰值并落 C-V1-ACCEPT.json（SPEC §6 字段）。

用法：
  python -X utf8 tools/run_c_acceptance.py --dry-run          # 框架自检（零 GPU，exit 0=框架可用）
  python -X utf8 tools/run_c_acceptance.py                    # 真机验收（需模型+GPU）
  可选：--work-dir kvmem/_c_acceptance --out <C-V1-ACCEPT.json> --keep

判定：verdict ∈ {通过, 未通过, 未接上}
  * 通过   = S1–S6 全 pass 且 S7a–S7d 全 pass；
  * 未通过 = 任一场景断言 fail（如实记，不掩盖）；
  * 未接上 = 装置/环境/超时/外部显存采样不可用等（写明原因）。
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DAILY = os.path.join(HERE, "chat_daily.py")
INSPECT = os.path.join(HERE, "inspect_logs.py")
SPEC = os.path.join(ROOT, "docs", "_work", "PRODUCT-C-SPEC.md")
LOG_SPEC = os.path.join(ROOT, "docs", "_work", "PRODUCT-C-LOG-SPEC.md")
OUT_DEFAULT = os.path.join(ROOT, "kvmem", "m2_visibility", "m5", "out", "C-V1-ACCEPT.json")
WORK_DEFAULT = os.path.join(ROOT, "kvmem", "_c_acceptance")
MODEL_DEFAULT = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
DLL = os.path.join(HERE, "kvshim_vk.dll")

REFUSAL_MARKERS = ("不想猜", "记忆里没有", "不知道", "无法确认", "没有记录", "未提及", "不清楚")
PROMPT_TIMEOUT = 90.0        # 每问 ≤90 s
SCENARIO_TIMEOUT = 600.0     # 每场景 ≤10 min
VRAM_FUSE_GIB = 8.6
KILL_WAIT_S = 2.5

S1_FACTS = [
    ("store", "我在云栖书店买了三本书。", ["云栖书店"]),
    ("amount", "这三本书一共花了 120 元。", ["120"]),
    ("model", "书的型号是 YQ-7781。", ["YQ-7781"]),
]
S1_QUESTIONS = [
    ("q1", "我在哪家书店买的书？", ["云栖书店"]),
    ("q2", "这三本书一共花了多少钱？", ["120"]),
    ("q3", "书的型号是什么？", ["YQ-7781"]),
]
S2_QUESTIONS = [
    "我的车牌号是多少？",
    "我的生日是哪天？",
    "我的银行卡号是多少？",
    "我明天坐哪趟航班？",
    "我住的酒店叫什么？",
    "我的发票抬头是什么？",
]


def sha16_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def atomic_json(path, obj):
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# 外部显存采样（SPEC §4：验收峰值必须外部测，不用 /status 的 null）
# ---------------------------------------------------------------------------
class VramSampler:
    """外部显存采样（SPEC §4：验收峰值必须外部测；2 s 一次，取整段运行最大值）。

    回退链（本机无 nvidia-smi 时走 PowerShell，Lead 已实测可用）：
      1) nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits  (MiB -> GiB)
      2) powershell Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory
         -> DedicatedUsage 求和 / 1GB  (GiB)
      3) 都不可用 => 记 未接上（采样不可用），peak_gib_source="unavailable"
    采样线程任何异常都被吞掉，绝不影响验收主流程。
    """

    PS_CMD = ("$m=Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_"
              "GPUAdapterMemory -ErrorAction SilentlyContinue | "
              "Measure-Object DedicatedUsage -Sum; "
              "if($m.Sum){[math]::Round($m.Sum/1GB,3)}else{''}")

    def __init__(self, period=2.0):
        self.period = period
        self.samples = []
        self.source = "unavailable"          # 最后成功采样的路径
        self.sources_used = []
        self.error = None
        self._stop = threading.Event()
        self._thread = None
        self._smi = self._which("nvidia-smi.exe") or self._which("nvidia-smi")
        self._ps = self._which("powershell.exe") or self._which("powershell")

    @staticmethod
    def _which(name):
        for d in (os.environ.get("PATH", "") or "").split(os.pathsep):
            if not d:
                continue
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
        return None

    # -- 两条采样路径 -----------------------------------------------------
    def _poll_nvidia(self):
        if not self._smi:
            return None
        try:
            r = subprocess.run([self._smi, "--query-gpu=memory.used",
                                "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=8)
            if r.returncode != 0:
                return None
            vals = []
            for line in (r.stdout or "").splitlines():
                line = line.strip()
                if line.isdigit():
                    vals.append(int(line) / 1024.0)
            return round(max(vals), 3) if vals else None
        except Exception as exc:                            # noqa: BLE001
            self.error = "nvidia-smi: %s: %s" % (type(exc).__name__, exc)
            return None

    def _poll_powershell(self):
        if not self._ps:
            return None
        try:
            r = subprocess.run([self._ps, "-NoProfile", "-Command", self.PS_CMD],
                               capture_output=True, text=True, timeout=15)
            if r.returncode != 0:
                return None
            out = (r.stdout or "").strip()
            if not out:
                return None
            return round(float(out), 3)
        except Exception as exc:                            # noqa: BLE001
            self.error = "powershell: %s: %s" % (type(exc).__name__, exc)
            return None

    def _poll(self):
        v = self._poll_nvidia()
        if v is not None:
            return v, "nvidia-smi"
        v = self._poll_powershell()
        if v is not None:
            return v, "powershell-gpuadaptermemory"
        return None, None

    def _run(self):
        while not self._stop.is_set():
            try:
                v, src = self._poll()
                if v is not None:
                    self.samples.append(v)
                    self.source = src
                    self.sources_used.append(src)
            except Exception as exc:                        # noqa: BLE001  采样不得影响主流程
                self.error = "%s: %s" % (type(exc).__name__, exc)
            self._stop.wait(self.period)

    def start(self):
        if not (self._smi or self._ps):
            return self
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        return self

    @property
    def available(self):
        return bool(self.samples)

    def peak(self):
        return max(self.samples) if self.samples else None


# ---------------------------------------------------------------------------
# 子进程驱动
# ---------------------------------------------------------------------------
class ChildChat:
    def __init__(self, args, dry_run=False, label=""):
        self.args = list(args)
        self.dry_run = dry_run
        self.label = label
        self.proc = None
        self.lines = []
        self._q = None
        self._reader = None
        self.cold_start_s = None

    def _reader_loop(self):
        try:
            for line in self.proc.stdout:
                self._q.put(line.rstrip("\r\n"))
        except Exception:                                    # noqa: BLE001
            pass
        finally:
            self._q.put(None)

    def start(self, ready_timeout=180.0):
        import queue
        self._q = queue.Queue()
        env = dict(os.environ)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        t0 = time.time()
        self.proc = subprocess.Popen(
            [sys.executable, "-u", "-X", "utf8", DAILY] + self.args,
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", bufsize=1, env=env)
        self._reader = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader.start()
        self.wait_for(lambda ln: "就绪（READY）" in ln, ready_timeout,
                      what="READY")
        self.cold_start_s = round(time.time() - t0, 2)
        return self

    def _next_line(self, timeout, collected):
        import queue as _q
        try:
            ln = self._q.get(timeout=timeout)
        except _q.Empty:
            raise TimeoutError("%s: 等待输出超时（%.0fs）; 最近输出=%r"
                               % (self.label, timeout, collected[-6:]))
        if ln is None:
            raise RuntimeError("%s: 子进程已退出 rc=%r; 输出=%r"
                               % (self.label, self.proc.poll(), collected[-10:]))
        cleaned = ln
        if cleaned.startswith("你> "):
            cleaned = cleaned[3:]
        elif cleaned == "你>":
            cleaned = ""
        self.lines.append(cleaned)
        collected.append(cleaned)
        return cleaned

    def wait_for(self, pred, timeout=PROMPT_TIMEOUT, what="line"):
        collected = []
        deadline = time.time() + timeout
        while True:
            remain = deadline - time.time()
            if remain <= 0:
                raise TimeoutError("%s: 等待 %s 超时（%.0fs）" % (self.label, what, timeout))
            ln = self._next_line(remain, collected)
            if pred(ln):
                return collected

    def send(self, line):
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def remember(self, text):
        self.send("/remember " + text)
        self.wait_for(lambda ln: ln.startswith("已记住 #"), what="remember")
        m = re.search(r"#(\d+)", self.lines[-1] if self.lines else "")
        return int(m.group(1)) if m else None

    def ask(self, text, timeout=PROMPT_TIMEOUT):
        t0 = time.time()
        self.send(text)
        self.wait_for(lambda ln: ln.startswith("答："), timeout, "answer")
        answer = ""
        for ln in reversed(self.lines):
            if ln.startswith("答："):
                answer = ln[2:].strip()
                break
        tail = self.wait_for(lambda ln: ln.strip().startswith("（")
                             or ln.startswith("错误["), timeout, "answer tail")
        tail_line = tail[-1].strip() if tail else ""
        refused = ("拒答" in tail_line) or any(m in answer for m in REFUSAL_MARKERS)
        lat = None
        m = re.search(r"（([0-9.]+)s", tail_line)
        if m:
            lat = float(m.group(1))
        return {"answer": answer, "tail": tail_line, "refused": refused,
                "latency_s": lat, "wall_s": round(time.time() - t0, 2)}

    def forget(self, mem_id):
        self.send("/forget %d" % mem_id)
        self.send("y")
        self.wait_for(lambda ln: "已删除" in ln, what="forget")

    def quit(self, timeout=180.0):
        try:
            self.send("/quit")
            self.wait_for(lambda ln: ln.startswith("已保存：") or ln.startswith("会话已保存"),
                          timeout, "save-on-quit")
        except Exception:                                    # noqa: BLE001
            pass
        return self._wait_exit(timeout)

    def _wait_exit(self, timeout):
        try:
            return self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                self.proc.kill()
            except Exception:                                # noqa: BLE001
                pass
            return self.proc.wait(timeout=10)

    def kill_hard(self):
        if not self.proc:
            return None
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(self.proc.pid)],
                           capture_output=True, text=True, timeout=20)
        except Exception:                                    # noqa: BLE001
            pass
        return self._wait_exit(20)


# ---------------------------------------------------------------------------
# 场景
# ---------------------------------------------------------------------------
class Acceptance:
    def __init__(self, args):
        self.args = args
        self.dry = bool(args.dry_run)
        self.work = os.path.abspath(args.work_dir or WORK_DEFAULT)
        self.out = os.path.abspath(args.out or OUT_DEFAULT)
        self.model = args.model or MODEL_DEFAULT
        self.caveats = []
        self.scenarios = []
        self.sessions = []
        self.logs = []
        self.latencies = []
        self.sampler = VramSampler().start()
        self.cold_start_s = None
        self.started_at = now_iso()
        self.framework_checks = []

    # -- 子进程工厂 -------------------------------------------------------
    def dirs(self, name):
        base = os.path.join(self.work, name)
        return {"db": os.path.join(base, "daily.db"),
                "blocks": os.path.join(base, "blocks"),
                "sessions": os.path.join(base, "sessions"),
                "session": os.path.join(base, "sessions", "daily.json"),
                "logs": os.path.join(base, "assistant"),
                "base": base}

    def child_args(self, d, control=False):
        a = ["--db", d["db"], "--blocks", d["blocks"],
             "--sessions", d["sessions"], "--session", d["session"],
             "--n-ctx", str(self.args.n_ctx), "--chat-start", str(self.args.chat_start),
             "--n-gpu-layers", str(self.args.n_gpu_layers)]
        if self.dry:
            a += ["--dry-run", "--model", os.path.join(self.work, "model.stub")]
        if control:
            a.append("--control")
        return a

    def open_child(self, d, label, control=False):
        c = ChildChat(self.child_args(d, control), dry_run=self.dry, label=label)
        c.start()
        if self.cold_start_s is None:
            self.cold_start_s = c.cold_start_s
        self.sessions.append(d["session"])
        return c

    # -- 断言记录 ---------------------------------------------------------
    def scenario(self, sid, name, cases, evidence, passed, skipped_reason=None):
        if skipped_reason:
            passed = "未接上"
            self.caveats.append("%s: %s" % (sid, skipped_reason))
        self.scenarios.append({"id": sid, "name": name,
                               "pass": passed, "cases": cases,
                               "evidence": evidence})
        print("  [%s] %s => %s" % (sid, name, passed))
        for ev in evidence[-2:]:
            print("        %s" % ev)

    def modeval(self, ok):
        """内容型断言在 dry-run/stub 下不可判 => None（框架只验证链路）。"""
        return None if self.dry else ok

    def struct(self, cid, ok, detail=""):
        """框架判定：dry-run 与真机都必须过（链路是否通，不含答案质量）。"""
        self.framework_checks.append({"id": cid, "pass": bool(ok), "detail": detail})
        print("    * %-22s %s  %s" % (cid, "PASS" if ok else "FAIL", detail))
        return bool(ok)

    def case(self, cid, ok, detail):
        if ok is None and self.dry:
            print("    - %-18s [framework]" % cid)
        else:
            print("    - %-18s %s  %s" % (cid, "PASS" if ok else "FAIL", detail))
        return {"id": cid, "pass": ok, "detail": detail}

    def merged(self, sid, name, cases, evidence, skipped=None, passed=None,
               structural=False):
        vals = [c["pass"] for c in cases if c["pass"] is not None]
        if self.dry:
            # dry-run：内容型场景一律 未接上（只报 [framework]）；结构型场景（S7）照实记
            verdict = bool(passed) if structural else "未接上"
        elif skipped:
            verdict = "未接上"
        elif passed is not None:
            verdict = bool(passed)
        elif vals:
            verdict = all(vals)
        else:
            verdict = "未接上"
        self.scenario(sid, name, cases, evidence, verdict, skipped_reason=skipped)

    def _run_questions(self, child, questions):
        out = []
        for qid, q, expects in questions:
            r = child.ask(q)
            if r["latency_s"] is not None:
                self.latencies.append(r["latency_s"])
            hit = all(e in r["answer"] for e in expects)
            ok = (not r["refused"]) and hit
            out.append({"qid": qid, "q": q, "expect": expects,
                        "answer": r["answer"], "refused": r["refused"],
                        "pass": ok, "latency_s": r["latency_s"]})
        return out

    # -- S1 ---------------------------------------------------------------
    def s1(self):
        d = self.dirs("S1")
        c = self.open_child(d, "S1")
        cases, ev = [], []
        try:
            ids = []
            for key, text, vals in S1_FACTS:
                mid = c.remember(text)
                ids.append(mid)
                cases.append(self.case("remember." + key, mid is not None,
                                       "id=%r" % mid))
            for qid, q, expects in S1_QUESTIONS:
                r = c.ask(q)
                if r["latency_s"] is not None:
                    self.latencies.append(r["latency_s"])
                ok = self.modeval((not r["refused"])
                                  and all(e in r["answer"] for e in expects))
                cases.append(self.case("ask." + qid, ok,
                                       "%r expect=%r refused=%r"
                                       % (r["answer"], expects, r["refused"])))
                ev.append("%s: %s" % (q, r["answer"]))
            self.s1_ids = ids
            self.s1_dirs = d
            self.struct("S1.remember_3", len([x for x in ids if x is not None]) == 3,
                        "ids=%r" % ids)
            self.struct("S1.asks_done", len(ev) == 3, "answers=%d" % len(ev))
        finally:
            c.quit()
        self.struct("S1.save_on_quit",
                    os.path.exists(os.path.join(d["sessions"], "daily.json")))
        self.merged("S1", "记与答（3 条事实 3/3）", cases, ev)

    # -- S2 ---------------------------------------------------------------
    def s2(self):
        d = self.dirs("S2")
        c = self.open_child(d, "S2")
        cases, ev = [], []
        refusals = 0
        try:
            for i, q in enumerate(S2_QUESTIONS, start=1):
                r = c.ask(q)
                if r["latency_s"] is not None:
                    self.latencies.append(r["latency_s"])
                ok = r["refused"]
                refusals += 1 if ok else 0
                cases.append(self.case("q%d" % i, self.modeval(ok),
                                       "%r refused=%r" % (r["answer"], r["refused"])))
                ev.append("Q%d %s => %s" % (i, q, r["answer"]))
            cases.append(self.case("refusal_rate>=5/6", self.modeval(refusals >= 5),
                                   "%d/6（个体 q 为诊断，不单独判失败）" % refusals))
            self._s2_rate_ok = (refusals >= 5)
            self.struct("S2.ask_commands", len(cases) >= 7, "cases=%d" % len(cases))
        finally:
            c.quit()
        self.merged("S2", "不知道（≥5/6 明确拒答）", cases, ev,
                    passed=self._s2_rate_ok)

    # -- S3 + S4 ----------------------------------------------------------
    def s3_s4(self):
        d = self.s1_dirs
        c = self.open_child(d, "S3")
        cases, ev = [], []
        try:
            for qid, q, expects in S1_QUESTIONS:
                r = c.ask(q)
                if r["latency_s"] is not None:
                    self.latencies.append(r["latency_s"])
                ok = self.modeval((not r["refused"])
                                  and all(e in r["answer"] for e in expects))
                cases.append(self.case("reopen.ask." + qid, ok,
                                       "%r expect=%r refused=%r"
                                       % (r["answer"], expects, r["refused"])))
                ev.append("%s: %s" % (q, r["answer"]))
            self.struct("S3.reopen_asks", len(cases) == 3, "answers=%d" % len(cases))
        finally:
            c.quit()
        self.merged("S3", "跨进程持久（重开不 /load 3/3）", cases, ev)

        # S4：/forget 后同题不再引用该事实
        d = self.s1_dirs
        c = self.open_child(d, "S4")
        cases, ev = [], []
        try:
            mid = self.s1_ids[0]
            c.forget(mid)
            cases.append(self.case("forget", True, "id=%d deleted" % mid))
            r = c.ask(S1_QUESTIONS[0][1])
            leaked = any(e in r["answer"] for e in S1_QUESTIONS[0][2])
            impl = r["refused"] or ("已删除" in r["answer"])
            cases.append(self.case("after_forget", (not leaked) and impl,
                                   "%r refused=%r" % (r["answer"], r["refused"])))
            ev.append("after /forget: %s" % r["answer"])
        finally:
            c.quit()
        self.merged("S4", "删除生效（/forget 后不再引用）", cases, ev)

    # -- S5 ---------------------------------------------------------------
    def s5(self):
        d = self.dirs("S5")
        c = self.open_child(d, "S5", control=True)
        cases, ev = [], []
        refusals = 0
        try:
            for qid, q, expects in S1_QUESTIONS:
                r = c.ask(q)
                leaked = any(e in r["answer"] for e in expects)
                refusals += 1 if r["refused"] else 0
                cases.append(self.case("control." + qid,
                                       self.modeval((not leaked) and r["refused"]),
                                       "%r refused=%r" % (r["answer"], r["refused"])))
                ev.append("%s: %s" % (q, r["answer"]))
            cases.append(self.case("control.refusal>=2/3",
                                   self.modeval(refusals >= 2), "%d/3" % refusals))
            self.struct("S5.control_asks", len(cases) == 4, "cases=%d" % len(cases))
        finally:
            c.quit()
        self.merged("S5", "对照（不挂记忆应拒答）", cases, ev)

    # -- S6 ---------------------------------------------------------------
    def s6(self):
        d = self.dirs("S6")
        cases, ev = [], []
        skipped = None
        c = self.open_child(d, "S6")
        try:
            ids = [c.remember(t) for _k, t, _v in S1_FACTS]
            ok_ids = all(i is not None for i in ids)
            cases.append(self.case("remember", ok_ids, str(ids)))
            r = c.ask(S1_QUESTIONS[0][1])
            cases.append(self.case("answer_before_kill",
                                   self.modeval(not r["refused"]),
                                   "%r" % (r["answer"],)))
            # 回答进行中强杀
            c.send("我买书的那家书店周末几点关门？")
            time.sleep(KILL_WAIT_S)
            rc = c.kill_hard()
            cases.append(self.case("taskkill", rc is not None, "rc=%r" % rc))
            self.struct("S6.taskkill", rc is not None, "rc=%r" % rc)
            ev.append("killed during ask; taskkill rc=%r" % rc)
        except Exception as exc:                            # noqa: BLE001
            cases.append(self.case("kill_setup", False, repr(exc)))
            try:
                c.kill_hard()
            except Exception:                               # noqa: BLE001
                pass
        # 重开：记忆仍在、可答
        c2 = self.open_child(d, "S6-reopen")
        try:
            reopened = []
            for qid, q, expects in S1_QUESTIONS:
                r = c2.ask(q)
                if r["latency_s"] is not None:
                    self.latencies.append(r["latency_s"])
                ok = self.modeval((not r["refused"])
                                  and all(e in r["answer"] for e in expects))
                reopened.append(ok)
                ev.append("reopen %s: %s" % (q, r["answer"]))
            judged = [x for x in reopened if x is not None]
            cases.append(self.case("reopen_memories",
                                   (None if self.dry else all(judged)),
                                   "%d/3" % sum(1 for x in judged if x)))
            cases.append(self.case("crash_warning_hint", self.modeval(True),
                                   "（由 S7b 从日志核 crash_recovered）"))
            self.struct("S6.reopen_asks", len(ev) >= 3, "answers=%d" % len(ev))
        finally:
            c2.quit()
        peak = self.sampler.peak()
        if self.dry:
            cases.append(self.case("vram_peak<=8.6", None, "dry-run 不采样"))
        elif not self.sampler.available:
            skipped = "外部显存采样不可用（nvidia-smi 未找到或采样为空）：%s" \
                      % (self.sampler.error or "")
            cases.append(self.case("vram_peak<=8.6", None, skipped))
        else:
            cases.append(self.case("vram_peak<=8.6", peak is not None
                                   and peak <= VRAM_FUSE_GIB,
                                   "peak=%.3f GiB (%s)" % (peak, self.sampler.source)))
            ev.append("external VRAM peak=%.3f GiB via %s"
                      % (peak, self.sampler.source))
        self.s6_dirs = d
        peak = self.sampler.peak()
        self.struct("S6.peak_or_no_gpu",
                    self.dry or (self.sampler.available and peak is not None
                                 and peak <= VRAM_FUSE_GIB),
                    "peak=%r src=%s" % (peak, self.sampler.source))
        self.merged("S6", "资源与崩溃（强杀后记忆仍在 + 外部显存峰值）", cases, ev,
                    skipped=skipped)

    # -- S7 ---------------------------------------------------------------
    def s7(self):
        cases, ev = [], []
        # S7a：S1 与 S6 日志 --verify exit 0
        verify_ok = True
        for d, tag in ((self.s1_dirs, "S1"), (self.s6_dirs, "S6")):
            r = subprocess.run([sys.executable, "-X", "utf8", INSPECT,
                                "--root", d["logs"], "--verify"],
                               capture_output=True, text=True, timeout=120, cwd=ROOT)
            ok = r.returncode == 0
            verify_ok = verify_ok and ok
            cases.append(self.case("verify." + tag, ok, (r.stdout or "").strip()[:160]))
            ev.append("verify %s rc=%d" % (tag, r.returncode))
        # S7b：crash_recovered 事件出现（S6 重开后）
        crash = []
        sess_dir = os.path.join(self.s6_dirs["logs"], "sessions")
        if os.path.isdir(sess_dir):
            for fn in os.listdir(sess_dir):
                p = os.path.join(sess_dir, fn)
                try:
                    for line in open(p, encoding="utf-8"):
                        obj = json.loads(line)
                        if obj.get("event") == "crash_recovered":
                            crash.append(obj)
                except Exception:                        # noqa: BLE001
                    pass
        cases.append(self.case("crash_recovered", bool(crash),
                               "n=%d last=%r" % (len(crash),
                                                 crash[-1].get("last_event") if crash else None)))
        if crash:
            ev.append("crash_recovered last_event=%r last_seq=%r"
                      % (crash[0].get("last_event"), crash[0].get("last_seq")))
        # S7c：redacted 打码（独立会话，含手机号/身份证/密码）
        d = self.dirs("S7")
        c = self.open_child(d, "S7")
        sensitive = ("我的手机号是 13800138000，身份证 110101199001011234，"
                     "登录密码是 Passw0rd#2026。")
        try:
            c.remember(sensitive)
            c.ask("我的手机号是多少？")
        finally:
            c.quit()
        blob = ""
        for fn in (os.listdir(os.path.join(d["logs"], "sessions"))
                   if os.path.isdir(os.path.join(d["logs"], "sessions")) else []):
            blob += open(os.path.join(d["logs"], "sessions", fn),
                         encoding="utf-8").read()
        mask_ok = (("13800138000" not in blob) and ("110101199001011234" not in blob)
                   and ("Passw0rd#2026" not in blob) and ("138****8000" in blob))
        cases.append(self.case("redacted", mask_ok,
                               "raw leaked=%r" % (("13800138000" in blob)
                                                  or ("Passw0rd#2026" in blob))))
        ev.append("redacted: phone/id/password masked, input_sha16 present=%r"
                  % ('"input_sha16"' in blob))
        # S7d：answer 的 block_ids 能在后续 /status 记忆面核对（用 S1 会话）
        answer_ev = None
        s1_sess = os.path.join(self.s1_dirs["logs"], "sessions")
        for fn in (os.listdir(s1_sess) if os.path.isdir(s1_sess) else []):
            for line in open(os.path.join(s1_sess, fn), encoding="utf-8"):
                obj = json.loads(line)
                if obj.get("event") == "answer" and obj.get("block_ids"):
                    answer_ev = obj
        cases.append(self.case("answer_block_ids", answer_ev is not None,
                               "block_ids=%r"
                               % (answer_ev.get("block_ids") if answer_ev else None)))
        if answer_ev:
            ev.append("answer block_ids=%r engine=%r"
                      % (answer_ev["block_ids"], answer_ev.get("engine")))
        s7_ok = all(c["pass"] is True for c in cases)
        self.struct("S7.verify", verify_ok, "inspect_logs --verify rc=0")
        self.struct("S7.crash_recovered", bool(crash))
        self.struct("S7.redacted", mask_ok)
        self.struct("S7.answer_block_ids", answer_ev is not None)
        self.merged("S7", "日志完整性（a 完整性 / b 崩溃 / c 隐私 / d 可核对）",
                    cases, ev, passed=s7_ok, structural=True)

    # -- 资源与收尾 -------------------------------------------------------
    def resources(self):
        lat = sorted(self.latencies)
        def pct(p):
            if not lat:
                return None
            k = max(0, min(len(lat) - 1, int(round((p / 100.0) * (len(lat) - 1)))))
            return lat[k]
        return {"peak_gib": self.sampler.peak(),
                "peak_gib_source": self.sampler.source if self.sampler.available
                else "unavailable",
                "vram_samples": len(self.sampler.samples),
                "cold_start_s": self.cold_start_s,
                "answer_p50_s": pct(50), "answer_p95_s": pct(95),
                "answer_n": len(lat),
                "answer_max_s": lat[-1] if lat else None,
                "fuse_gib": VRAM_FUSE_GIB}

    def verdict(self):
        if self.dry:
            return "未接上"
        flags = [s["pass"] for s in self.scenarios]
        if any(f is False for f in flags):
            return "未通过"
        if any(f == "未接上" for f in flags):
            return "未接上"
        return "通过" if all(f is True for f in flags) else "未接上"

    def gather_logs(self):
        logs = []
        for base in (self.work,):
            for dirpath, _dirs, files in os.walk(base):
                for fn in files:
                    if fn.endswith(".jsonl"):
                        p = os.path.join(dirpath, fn)
                        try:
                            logs.append({"path": os.path.relpath(p, ROOT),
                                         "sha16": sha16_file(p),
                                         "bytes": os.path.getsize(p)})
                        except OSError:
                            pass
        return logs

    def write(self):
        res = self.resources()
        body = {
            "schema": "c_v1_accept_v1",
            "version": "c-1.0",
            "spec_pin": sha16_file(SPEC) if os.path.exists(SPEC) else None,
            "log_spec_pin": sha16_file(LOG_SPEC) if os.path.exists(LOG_SPEC) else None,
            "started_at": self.started_at,
            "ended_at": now_iso(),
            "mode": "dry_run_stub" if self.dry else "real_engine",
            "model_pin": ({"model_path": self.model,
                           "model_size": os.path.getsize(self.model)}
                          if os.path.exists(self.model) else {"model_path": self.model,
                                                              "present": False}),
            "dll_pin": ({"path": DLL, "bytes": os.path.getsize(DLL),
                         "sha16": sha16_file(DLL)} if os.path.exists(DLL) else None),
            "engine_meta": {"n_ctx": int(self.args.n_ctx), "n_seq": 8,
                            "chat_start": int(self.args.chat_start),
                            "n_gpu_layers": int(self.args.n_gpu_layers),
                            "kv": "q8_0", "n_predict": 192,
                            "mode": "stub" if self.dry else "real"},
            "scenarios": self.scenarios,
            "resources": res,
            "sessions": self.sessions,
            "logs": self.gather_logs(),
            "verdict": self.verdict(),
            "caveats": self.caveats,
        }
        atomic_json(self.out, body)
        return body


def main(argv=None):
    ap = argparse.ArgumentParser(description="C 版验收臂（S1–S6 + S7a–S7d）")
    ap.add_argument("--dry-run", action="store_true",
                    help="零 GPU：用 StubEngine 子进程跑通验收框架")
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--n-ctx", type=int, default=16384)
    ap.add_argument("--chat-start", type=int, default=8192)
    ap.add_argument("--n-gpu-layers", type=int, default=34)
    ap.add_argument("--keep", action="store_true", help="保留临时数据目录")
    args = ap.parse_args(argv)

    work = os.path.abspath(args.work_dir or WORK_DEFAULT)
    if os.path.isdir(work) and not args.keep:
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    if args.dry_run:
        # 给子进程的占位模型（chat_daily --dry-run 会 install_fake_model）
        p = os.path.join(work, "model.stub")
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write("acceptance dry-run placeholder model\n")

    if args.dry_run and not args.out:
        args.out = os.path.join(work, "C-V1-ACCEPT.dryrun.json")
    acc = Acceptance(args)
    print("C 版验收臂：mode=%s work=%s out=%s"
          % ("dry_run_stub" if args.dry_run else "real_engine", work, acc.out))
    ok = True
    try:
        acc.s1()
        acc.s2()
        acc.s3_s4()
        acc.s5()
        acc.s6()
        acc.s7()
    except Exception as exc:                                # noqa: BLE001
        ok = False
        traceback.print_exc()
        acc.caveats.append("验收臂异常：%s: %s" % (type(exc).__name__, exc))
        acc.scenarios.append({"id": "ABORT", "name": "验收臂异常", "pass": "未接上",
                              "cases": [], "evidence": [repr(exc)]})
    finally:
        acc.sampler.stop()
        body = acc.write()
    print("\nverdict = %s" % body["verdict"])
    print("accept file: %s（%d bytes）" % (acc.out, os.path.getsize(acc.out)))
    if args.dry_run:
        # dry-run 判定：框架链路全部走通（子进程/命令/日志/save-load/强杀恢复），
        # 内容型断言一律 [framework]，不参与判定。
        fw = list(acc.framework_checks)
        body["framework"] = {"mode": "dry_run_stub",
                             "checks": fw,
                             "pass": bool(fw) and all(c["pass"] for c in fw)}
        atomic_json(acc.out, body)
        framework_ok = (ok and os.path.exists(acc.out) and body["framework"]["pass"])
        print("dry-run framework = %s（%d/%d 框架检查通过）"
              % ("PASSED" if framework_ok else "FAILED",
                 sum(1 for c in fw if c["pass"]), len(fw)))
        return 0 if framework_ok else 1
    return 0 if body["verdict"] == "通过" else 1


if __name__ == "__main__":
    sys.exit(main())