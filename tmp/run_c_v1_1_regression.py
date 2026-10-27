# -*- coding: utf-8 -*-
"""tmp/run_c_v1_1_regression.py -- C 版 rev7.2 期间产品轻量回归（CPU 可备，GPU 由 LEAD 触发）。

用途（b7′ 判定同装置，确认 rev7.2 期间产品侧无回归）：
  A. 10 条库 + --retrieval topk --topk 4：问 4 个不同问题，记录
     mounted_ids/candidates/related 与答对情况；
  B. 强制 --rollover-at 0.05：确认 notice + daily/archive/*.txt +
     auto_archive / auto_summary 关联；
  C. 长回答延迟：--n-predict 320 让模型答约 250–300 字，记录单问耗时；
  D. inspect_logs.py --verify / --summary 记录日志完整性。
产出：kvmem/m2_visibility/m5/out/C-V1-1-REGRESSION.json（可用 --out 覆盖）。
零 GPU 自检：python -X utf8 tmp/run_c_v1_1_regression.py --dry-run
真机：      python -X utf8 tmp/run_c_v1_1_regression.py
纪律：不改冻结件、不动 b7 产物、不 commit；每问 ≤120 s，全程 ≤10 min 目标。
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DAILY = os.path.join(ROOT, "tools", "chat_daily.py")
INSPECT = os.path.join(ROOT, "tools", "inspect_logs.py")
OUT_DEFAULT = os.path.join(ROOT, "kvmem", "m2_visibility", "m5", "out",
                           "C-V1-1-REGRESSION.json")
WORK_DEFAULT = os.path.join(ROOT, "kvmem", "_c_regression")
REFUSAL_MARKERS = ("不想猜", "记忆里没有", "不知道", "无法确认", "没有记录", "未提及")
ASK_TIMEOUT = 120.0

MEMORIES = [
    ("车辆：车牌号是京A88888，车型是比亚迪汉。#车辆", ["京A88888"]),
    ("购书：在云栖书店买的旧书《城南旧事》，花了 120 元。#购书", ["云栖书店", "120"]),
    ("会议：每周三晚上 7 点组会，地点在 2 号会议室。#会议", ["2 号会议室"]),
    ("健康：周三上午体检，需要空腹。#健康", ["空腹"]),
    ("偏好：咖啡不加糖，只喝美式。#偏好", ["美式"]),
    ("旅行：9 月 18 日去杭州，住西湖边。#旅行", ["杭州"]),
    ("报销：发票抬头是云栖科技。#报销", ["云栖科技"]),
    ("阅读：《长夜难明》本周读完。#阅读", ["长夜难明"]),
    ("训练：周一练腿 60 公斤，周三练背 40 公斤。#训练", ["60 公斤"]),
    ("工作：每周五复盘，交付周报。#工作", ["周报"]),
]
RETRIEVAL_QUESTIONS = [
    ("q1", "我的车牌号是多少？", ["京A88888"]),
    ("q2", "每周三组会在哪个会议室？", ["2 号会议室"]),
    ("q3", "我喝咖啡是什么习惯？", ["美式", "不加糖"]),
    ("q4", "体检有什么要注意的？", ["空腹"]),
]
GENERAL_Q = ["介绍一下长城的历史。", "介绍一下长江的历史。", "介绍一下黄河的历史。",
             "介绍一下故宫的历史。", "介绍一下西湖的历史。", "介绍一下泰山的history。"]
LONG_Q = "请用大约 250 到 300 字，详细介绍长江的历史、流经省份和地理意义，尽量完整。"


def sha16_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


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


class Child:
    """python -u 子进程驱动 chat_daily；行缓冲可靠、超时不卡死。"""

    def __init__(self, args, label):
        self.args = list(args)
        self.label = label
        self.proc = None
        self._q = None
        self._lines = []

    def _reader(self):
        try:
            for line in self.proc.stdout:
                self._q.put(line.rstrip("\r\n"))
        except Exception:                                # noqa: BLE001
            pass
        finally:
            self._q.put(None)

    def start(self, ready_timeout=180.0):
        import queue
        self._q = queue.Queue()
        t0 = time.time()
        self.proc = subprocess.Popen(
            [sys.executable, "-u", "-X", "utf8", DAILY] + self.args,
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", bufsize=1)
        threading.Thread(target=self._reader, daemon=True).start()
        self.wait(lambda ln: "就绪（READY）" in ln, ready_timeout, "READY")
        return round(time.time() - t0, 2)

    def wait(self, pred, timeout, what):
        collected = []
        deadline = time.time() + timeout
        while True:
            remain = deadline - time.time()
            if remain <= 0:
                raise TimeoutError("%s: 等待 %s 超时（%ss）" % (self.label, what, timeout))
            try:
                ln = self._q.get(timeout=remain)
            except Exception:                            # noqa: BLE001
                raise TimeoutError("%s: 等待 %s 超时（%ss）" % (self.label, what, timeout))
            if ln is None:
                raise RuntimeError("%s: 子进程退出 rc=%r" % (self.label, self.proc.poll()))
            if ln.startswith("你> "):
                ln = ln[3:]
            self._lines.append(ln)
            collected.append(ln)
            if pred(ln):
                return collected

    def send(self, line):
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def remember(self, text):
        self.send("/remember " + text)
        self.wait(lambda ln: ln.startswith("已记住 #"), ASK_TIMEOUT, "remember")
        m = re.search(r"#(\d+)", self._lines[-1])
        return int(m.group(1)) if m else None

    def ask(self, text):
        t0 = time.time()
        self.send(text)
        self.wait(lambda ln: ln.startswith("答："), ASK_TIMEOUT, "answer")
        answer = ""
        for ln in reversed(self._lines):
            if ln.startswith("答："):
                answer = ln[2:].strip()
                break
        tail = self.wait(lambda ln: ln.strip().startswith("（") or ln.startswith("错误["),
                         ASK_TIMEOUT, "tail")[-1].strip()
        notice = None
        for ln in reversed(self._lines[-6:]):
            if "上下文已自动压缩" in ln:
                notice = ln.strip()
                break
        lat = None
        m = re.search(r"（([0-9.]+)s", tail)
        if m:
            lat = float(m.group(1))
        refused = ("拒答" in tail) or any(x in answer for x in REFUSAL_MARKERS)
        return {"answer": answer, "tail": tail, "refused": refused,
                "latency_s": lat, "wall_s": round(time.time() - t0, 3),
                "notice": notice}

    def quit(self, timeout=180.0):
        try:
            self.send("/quit")
            self.wait(lambda ln: "已保存" in ln, timeout, "save")
        except Exception:                                # noqa: BLE001
            pass
        try:
            return self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            return self.proc.wait(timeout=10)


def read_events(log_root):
    out = []
    sdir = os.path.join(log_root, "sessions")
    for fn in (os.listdir(sdir) if os.path.isdir(sdir) else []):
        for line in open(os.path.join(sdir, fn), encoding="utf-8"):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def last_exchange(log_root):
    ev = read_events(log_root)
    ask = None
    ans = None
    ref = None
    for e in ev:
        if e.get("event") == "ask":
            ask = e
        elif e.get("event") == "answer":
            ans = e
        elif e.get("event") == "refuse":
            ref = e
    retrieval = (ask or {}).get("retrieval") or {}
    return {"retrieval": retrieval,
            "block_ids": (ans or {}).get("block_ids"),
            "engine": (ans or {}).get("engine"),
            "refused": ref is not None,
            "latency_ms": (ans or ref or {}).get("latency_ms")}


class Regression:
    def __init__(self, args):
        self.args = args
        self.dry = bool(args.dry_run)
        self.work = os.path.abspath(args.work_dir or WORK_DEFAULT)
        if self.dry and not args.out:
            self.out = os.path.join(self.work, "C-V1-1-REGRESSION.dryrun.json")
        else:
            self.out = os.path.abspath(args.out or OUT_DEFAULT)
        self.base = {"n_ctx": args.n_ctx, "chat_start": args.chat_start,
                     "n_gpu_layers": args.n_gpu_layers,
                     "retrieval": "topk", "topk": 4}
        self.caveats = []
        self.started = datetime.now().astimezone().isoformat(timespec="seconds")

    def dirs(self, name):
        b = os.path.join(self.work, name)
        return {"base": b, "db": os.path.join(b, "daily.db"),
                "blocks": os.path.join(b, "blocks"),
                "sessions": os.path.join(b, "sessions"),
                "session": os.path.join(b, "sessions", "daily.json"),
                "logs": os.path.join(b, "assistant")}

    def child_args(self, d, extra=()):
        a = ["--db", d["db"], "--blocks", d["blocks"],
             "--sessions", d["sessions"], "--session", d["session"],
             "--n-ctx", str(self.args.n_ctx),
             "--chat-start", str(self.args.chat_start),
             "--n-gpu-layers", str(self.args.n_gpu_layers),
             "--retrieval", "topk", "--topk", "4"] + list(extra)
        if self.dry:
            a += ["--dry-run", "--model", self.args.model]
        return a

    def open(self, d, label, extra=()):
        c = Child(self.child_args(d, extra), label)
        c.start()
        return c

    # -- A 检索 -----------------------------------------------------------
    def phase_retrieval(self):
        d = self.dirs("A-retrieval")
        c = self.open(d, "A")
        rec = {"dirs": d, "questions": [], "remembered": [], "pass": None}
        try:
            for text, _vals in MEMORIES:
                rec["remembered"].append(c.remember(text))
            for qid, q, expects in RETRIEVAL_QUESTIONS:
                r = c.ask(q)
                lx = last_exchange(d["logs"])
                ret = lx["retrieval"]
                # 空白/全角半角差异不计入正确性（"2号会议室" vs "2 号会议室"）
                norm = lambda x: re.sub(r"\s+", "", str(x))
                ok = (not r["refused"]) and all(norm(x) in norm(r["answer"])
                                                for x in expects)
                rec["questions"].append({
                    "qid": qid, "q": q, "expect": expects,
                    "answer": r["answer"], "refused": r["refused"],
                    "correct": bool(ok), "latency_s": r["latency_s"],
                    "mounted_ids": lx["block_ids"] or [],
                    "candidates": ret.get("candidates"),
                    "related": ret.get("related"),
                    "selected_ids": ret.get("selected_ids"),
                    "scores": ret.get("scores"),
                })
        finally:
            rec["exit"] = c.quit()
        correct = sum(1 for x in rec["questions"] if x["correct"])
        rec["correct_n"] = correct
        rec["total"] = len(rec["questions"])
        rec["pass"] = None if self.dry else (correct >= 3)
        if not self.dry and correct < 4:
            self.caveats.append("A 检索：%d/4 答对（<4）" % correct)
        return rec

    # -- B 强制 rollover --------------------------------------------------
    def phase_rollover(self):
        d = self.dirs("B-rollover")
        ro = "0.001" if self.dry else "0.05"     # dry-run 只验机制，阈值故意压低
        c = self.open(d, "B", extra=["--rollover-at", ro])
        rec = {"dirs": d, "asks": 0, "notice": None, "pass": None}
        try:
            for text, _vals in MEMORIES[:3]:
                c.remember(text)
            for i, q in enumerate(GENERAL_Q):
                r = c.ask(q)
                rec["asks"] = i + 1
                if r["notice"]:
                    rec["notice"] = r["notice"]
                    rec["notice_after_ask"] = i + 1
                    break
            rec["exit"] = c.quit()
        finally:
            try:
                rec["archive_files"] = (
                    sorted(os.listdir(os.path.join(d["base"], "daily", "archive")))
                    if os.path.isdir(os.path.join(d["base"], "daily", "archive")) else [])
            except OSError:
                rec["archive_files"] = []
            try:
                con = sqlite3.connect(d["db"])
                rows = con.execute(
                    "SELECT id, mode, label, text FROM memory_source WHERE mode IN "
                    "('auto_summary','auto_archive') ORDER BY id").fetchall()
                metas = {r[0]: con.execute(
                    "SELECT tags, source, related_ids FROM daily_memory_meta "
                    "WHERE source_id=?", (r[0],)).fetchone() for r in rows}
                con.close()
            except sqlite3.Error as exc:
                rows, metas = [], {}
                self.caveats.append("B 读 DB 失败：%s" % exc)
            rec["rows"] = [{"id": r[0], "mode": r[1], "label": r[2]} for r in rows]
            summ = [r for r in rows if r[1] == "auto_summary"]
            arch = [r for r in rows if r[1] == "auto_archive"]
            rec["summary_ids"] = [r[0] for r in summ]
            rec["archive_ids"] = [r[0] for r in arch]
            if summ and arch:
                rel = metas.get(summ[0][0])[2] if metas.get(summ[0][0]) else None
                rec["summary_related_ids"] = json.loads(rel) if rel else []
                rec["link_ok"] = rec["summary_related_ids"] == [arch[0][0]]
            else:
                rec["link_ok"] = False
            rec["archive_file_ok"] = bool(rec["archive_files"])
            rec["events"] = [e.get("event") for e in read_events(d["logs"])
                             if e.get("event") in ("context_rollover", "warning")]
        structural = (bool(rec["notice"]) and rec["archive_file_ok"]
                      and rec["link_ok"] and len(rec["summary_ids"]) >= 1)
        rec["pass"] = None if self.dry else structural
        if not self.dry and not structural:
            self.caveats.append("B rollover 结构检查未过：notice=%r file=%r link=%r"
                                % (bool(rec["notice"]), rec["archive_file_ok"],
                                   rec["link_ok"]))
        return rec

    # -- C 长回答延迟 -----------------------------------------------------
    def phase_long_answer(self):
        d = self.dirs("C-long")
        c = self.open(d, "C", extra=["--n-predict", "320"])
        rec = {"dirs": d, "pass": None}
        try:
            c.remember("背景：我在写一份关于长江的地理笔记。")
            t0 = time.time()
            r = c.ask(LONG_Q)
            rec.update({"q": LONG_Q, "wall_s": round(time.time() - t0, 3),
                        "latency_s": r["latency_s"], "chars": len(r["answer"]),
                        "answer_head": r["answer"][:120], "refused": r["refused"]})
            rec["exit"] = c.quit()
        except TimeoutError as exc:
            rec["error"] = str(exc)
            try:
                c.proc.kill()
            except Exception:                            # noqa: BLE001
                pass
        ok = rec.get("chars", 0) >= 120 and not rec.get("refused", True)
        rec["pass"] = None if self.dry else ok
        if not self.dry and not ok:
            self.caveats.append("C 长回答过短：%r 字" % rec.get("chars"))
        return rec

    # -- D 日志 -----------------------------------------------------------
    def phase_logs(self, phase_dirs):
        rec = {"verify": [], "summary": [], "pass": None}
        ok = True
        for name, d in phase_dirs.items():
            if not os.path.isdir(d["logs"]):
                rec["verify"].append({"phase": name, "rc": None, "error": "no log dir"})
                continue
            r = subprocess.run([sys.executable, "-X", "utf8", INSPECT,
                                "--root", d["logs"], "--verify"],
                               capture_output=True, text=True, timeout=120, cwd=ROOT)
            rec["verify"].append({"phase": name, "rc": r.returncode,
                                  "out": (r.stdout or "").strip()[:200]})
            ok = ok and r.returncode == 0
            r2 = subprocess.run([sys.executable, "-X", "utf8", INSPECT,
                                 "--root", d["logs"], "--summary", "--json"],
                                capture_output=True, text=True, timeout=120, cwd=ROOT)
            try:
                summ = json.loads(r2.stdout)
            except ValueError:
                summ = {"raw": (r2.stdout or "")[:200]}
            rec["summary"].append({"phase": name, "rc": r2.returncode,
                                   "summary": summ})
        rec["pass"] = None if self.dry else ok
        if not self.dry and not ok:
            self.caveats.append("D inspect_logs --verify 非 0")
        return rec

    def run(self):
        os.makedirs(self.work, exist_ok=True)
        if os.path.isdir(self.work) and not self.args.keep and not self.dry:
            import shutil
            shutil.rmtree(self.work, ignore_errors=True)
            os.makedirs(self.work, exist_ok=True)
        if self.dry:
            m = self.args.model or os.path.join(self.work, "model.stub")
            if not os.path.exists(m):
                os.makedirs(os.path.dirname(m), exist_ok=True)
                with open(m, "w", encoding="utf-8", newline="\n") as f:
                    f.write("regression dry-run placeholder model\n")
            self.args.model = m
        body = {"schema": "c_v1_1_regression_v1", "mode": "dry_run_stub" if self.dry
                else "real_engine", "started_at": self.started,
                "spec_pin": (sha16_file(os.path.join(ROOT, "docs", "_work",
                                                     "PRODUCT-C-SPEC.md"))
                             if os.path.exists(os.path.join(ROOT, "docs", "_work",
                                                            "PRODUCT-C-SPEC.md")) else None),
                "base": self.base, "work": self.work, "caveats": self.caveats}
        if os.path.exists(self.out):
            body["supersedes"] = sha16_file(self.out)
        print("C 版 rev7.2 期间回归：mode=%s work=%s" % (body["mode"], self.work))
        try:
            a = self.phase_retrieval()
            print("  [A] 检索：correct=%s/%s mounted/candidates=%s"
                  % (a.get("correct_n", "?"), a.get("total", "?"),
                     [(x["mounted_ids"], x["candidates"], x["related"])
                      for x in a["questions"][:2]]))
            b = self.phase_rollover()
            print("  [B] rollover：notice=%r archive=%r link=%r"
                  % (bool(b.get("notice")), b.get("archive_file_ok"), b.get("link_ok")))
            cc = self.phase_long_answer()
            print("  [C] 长回答：%r 字, wall=%ss"
                  % (cc.get("chars"), cc.get("wall_s")))
            dd = self.phase_logs({"A": a["dirs"], "B": b["dirs"], "C": cc["dirs"]})
            print("  [D] verify rc=%s" % [x.get("rc") for x in dd["verify"]])
            body.update({"retrieval": {k: v for k, v in a.items() if k != "dirs"},
                         "rollover": {k: v for k, v in b.items() if k != "dirs"},
                         "long_answer": {k: v for k, v in cc.items() if k != "dirs"},
                         "logs": dd})
        except Exception as exc:                         # noqa: BLE001
            import traceback
            traceback.print_exc()
            body["error"] = "%s: %s" % (type(exc).__name__, exc)
        body["ended_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        phases = [body.get("retrieval", {}), body.get("rollover", {}),
                  body.get("long_answer", {}), body.get("logs", {})]
        if self.dry:
            body["verdict"] = "未接上"
            fw = (not body.get("error")
                  and all(p.get("pass") is None for p in phases))
            body["framework"] = {"pass": bool(fw),
                                 "checks": {"phases_ran": len(phases),
                                            "no_error": not body.get("error")}}
        else:
            fails = [p for p in phases if p.get("pass") is False]
            body["verdict"] = "未通过" if fails else (
                "通过" if all(p.get("pass") is True for p in phases) else "未接上")
            body["framework"] = {"pass": None}
        atomic_json(self.out, body)
        print("verdict = %s" % body["verdict"])
        print("out: %s（%d bytes）" % (self.out, os.path.getsize(self.out)))
        if self.dry:
            print("dry-run framework = %s" % ("PASSED" if body["framework"]["pass"]
                                              else "FAILED"))
            return 0 if body["framework"]["pass"] else 1
        return 0 if body["verdict"] == "通过" else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="C 版 rev7.2 期间轻量回归")
    ap.add_argument("--dry-run", action="store_true", help="零 GPU 验框架")
    ap.add_argument("--out", default=None)
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--n-ctx", type=int, default=16384)
    ap.add_argument("--chat-start", type=int, default=8192)
    ap.add_argument("--n-gpu-layers", type=int, default=34)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)
    if a.model is None:
        a.model = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
    return Regression(a).run()


if __name__ == "__main__":
    sys.exit(main())