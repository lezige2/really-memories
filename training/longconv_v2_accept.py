# -*- coding: utf-8 -*-
"""长上下文 I/O 风暴 —— 独立量化与验收（v2）。

职责（LEAD 指派，独立于另外 3 个审计 agent）：
  1) 在 32k/40k 字符长测期间独立测量：逐轮写入、rollover 写入、会话文件大小；
  2) 长测结束后独立探针复测 early/mid 事实召回（不采信被测脚本自报）；
  3) 与 out/IO-WRITE-AUDIT.json / out/IO-PROBE.json / out/IO-MEMORY-AUDIT.json 交叉核对，
     不一致逐条指出；
  4) 出 out/LONG-CONV-V2-JUDGE.json：验收表 + 评分 + 建议。
不改产品代码；只写 tmp/ 运行日志与 out/LONG-CONV-V2-JUDGE.json。

用法：
  python -X utf8 training/longconv_v2_accept.py --run        # GO 后：测量 + 跑长测 + 复测 + 交叉核对
  python -X utf8 training/longconv_v2_accept.py --judge-only # 只重判（用已有 tmp 测量/产物）
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
EP = "http://127.0.0.1:8765"
V2_SCRIPT = ROOT / "tmp" / "long_conv_test_v2.py"
V2_ART = ROOT / "tmp" / "LONG-CONV-TEST-V2.json"
RUN_LOG = ROOT / "tmp" / "LONG-CONV-V2-RUN.log"
MINE = ROOT / "tmp" / "LONG-CONV-V2-MINE.json"
OUT = ROOT / "out" / "LONG-CONV-V2-JUDGE.json"
IO_PROBE = ROOT / "out" / "IO-PROBE.json"
IO_WRITE = ROOT / "out" / "IO-WRITE-AUDIT.json"
IO_MEM = ROOT / "out" / "IO-MEMORY-AUDIT.json"

TREES = ["kvmem/daily", "kvmem/assistant", "kvmem/lease_logs", "kvmem/web_logs"]
BIG = 1024 * 1024
LIMITS = {"per_ask_write_bytes": 5 * BIG, "rollover_total_write_bytes": 150 * BIG,
          "session_file_bytes": 1024 * BIG}

# 验收阈值（LEAD 指定）
FACTS_EARLY_MID = [
    ("early", "我的车牌号是多少？", ["京A88888"]),
    ("early", "我养的猫叫什么名字？", ["豆豆"]),
    ("mid", "我下周五要去哪开会？", ["成都"]),
    ("mid", "我的工号是多少？", ["A12345"]),
    ("mid", "我妻子叫什么名字？", ["李娜"]),
    ("mid", "我老家在哪里？", ["青岛"]),
]


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def http(path, payload=None, timeout=60):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(EP + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def snapshot():
    out = {}
    for base in TREES:
        root = ROOT / base
        if not root.is_dir():
            continue
        for dirpath, _dn, fns in os.walk(root):
            for fn in fns:
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, ROOT).replace("\\", "/")
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                out[rel] = (st.st_size, st.st_mtime)
    return out


def tree_of(rel):
    for t in TREES:
        if rel.startswith(t):
            return t
    return "other"


def diff(before, after):
    total = 0
    per_tree = {}
    new_files, changed, deleted = [], [], []
    for rel, (size, mt) in after.items():
        b = before.get(rel)
        delta = size if b is None else size - b[0]
        if b is None:
            new_files.append({"path": rel, "bytes": size, "tree": tree_of(rel)})
        elif delta > 0:
            changed.append({"path": rel, "delta": delta, "after": size,
                            "tree": tree_of(rel), "mtime": mt})
        if delta > 0:
            total += delta
            per_tree[tree_of(rel)] = per_tree.get(tree_of(rel), 0) + delta
    for rel, (size, mt) in before.items():
        if rel not in after:
            deleted.append({"path": rel, "bytes": size})
    return {"total_bytes": total, "per_tree": per_tree, "new_files": new_files,
            "changed": changed, "deleted": deleted}


class Sampler(threading.Thread):
    def __init__(self, interval=1.0):
        super().__init__(daemon=True)
        self.interval = interval
        self.stop_flag = threading.Event()
        self.samples = []

    def run(self):
        while not self.stop_flag.wait(self.interval):
            try:
                total = 0
                per = {}
                for base in TREES:
                    root = ROOT / base
                    if not root.is_dir():
                        continue
                    s = 0
                    for dirpath, _dn, fns in os.walk(root):
                        for fn in fns:
                            try:
                                s += os.stat(os.path.join(dirpath, fn)).st_size
                            except OSError:
                                pass
                    per[base] = s
                    total += s
                self.samples.append({"t": time.time(), "total": total, "per_tree": per})
            except Exception:  # noqa: BLE001
                pass


def classify_rollover_files(files):
    """把新建/变更文件归因到 rollover：archive/*.txt + mode=auto_* 的 blocks。"""
    roll = []
    for f in files:
        rel = f.get("path") or ""
        if "/archive/" in rel:
            cat = f.get("bytes", f.get("delta", 0))
            roll.append({"path": rel, "bytes": cat, "kind": "archive_txt"})
        elif "/blocks/" in rel and rel.endswith(".kvmem"):
            try:
                obj = json.loads((ROOT / rel).read_text(encoding="utf-8", errors="replace"))
            except Exception:  # noqa: BLE001
                continue
            mode = str(obj.get("mode") or obj.get("meta", {}).get("mode") or "")
            if mode.startswith("auto_"):
                roll.append({"path": rel, "bytes": f.get("bytes", f.get("delta", 0)),
                             "kind": mode})
    return roll


def parse_io_probe(p):
    if not p.exists():
        return {"exists": False}
    d = json.loads(p.read_text(encoding="utf-8"))
    s = d.get("summary") or {}
    rounds = d.get("rounds") or []
    deltas = [r.get("delta_bytes") for r in rounds if isinstance(r.get("delta_bytes"), (int, float))]
    rolls = d.get("rollovers") or []
    return {"exists": True, "schema": d.get("schema"), "partial": d.get("partial"),
            "rounds": s.get("rounds"), "total_bytes_written": s.get("total_bytes_written"),
            "peak_round_bytes": (s.get("peak_round") or {}).get("delta_bytes"),
            "max_round_bytes": max(deltas) if deltas else None,
            "mean_round_bytes": (sum(deltas) / len(deltas)) if deltas else None,
            "rollover_count": len(rolls),
            "rollover_bytes_sum": sum(x.get("delta_bytes") or 0 for x in rolls) or None,
            "bytes_by_cat": s.get("bytes_by_cat")}


def deep_numbers(obj, path="", out=None):
    """通用提取（给未知 schema 的 IO-WRITE-AUDIT / IO-MEMORY-AUDIT 用）。"""
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            kk = ("%s.%s" % (path, k)).strip(".")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[kk] = v
            elif isinstance(v, str) and v.isdigit():
                out[kk] = int(v)
            else:
                deep_numbers(v, kk, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            deep_numbers(v, "%s[%d]" % (path, i), out)
    return out


def pick(nums, *needles):
    for key in sorted(nums):
        low = key.lower()
        if any(n in low for n in needles):
            return key, nums[key]
    return None, None


def load_other(p):
    if not p.exists():
        return {"exists": False}
    raw = p.read_bytes()
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return {"exists": True, "parse_error": True, "bytes": len(raw)}
    nums = deep_numbers(d)
    return {"exists": True, "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "schema": d.get("schema") if isinstance(d, dict) else None,
            "partial": d.get("partial") if isinstance(d, dict) else None,
            "numbers": nums,
            "per_ask_key": pick(nums, "per_ask", "perask", "max_ask", "single_ask")[0],
            "rollover_key": pick(nums, "rollover_total", "rollover_bytes", "rollover_write")[0],
            "session_key": pick(nums, "session_file", "session_bytes", "session_size")[0],
            "raw_head": raw[:1200].decode("utf-8", "replace")}


def run_v2():
    cmd = [sys.executable, "-X", "utf8", str(V2_SCRIPT),
           "--target-chars", "40000", "--out", str(V2_ART)]
    with open(RUN_LOG, "w", encoding="utf-8", newline="\n") as log:
        p = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                           cwd=str(ROOT), timeout=7200)
    return p.returncode


def sha16_of(path, max_bytes=None):
    import hashlib
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            left = max_bytes
            while True:
                chunk = f.read(1024 * 1024 if left is None else min(1024 * 1024, left))
                if not chunk:
                    break
                h.update(chunk)
                if left is not None:
                    left -= len(chunk)
                    if left <= 0:
                        break
    except Exception:  # noqa: BLE001
        return None
    return h.hexdigest()[:16]


def measure(run_test):
    run_start_epoch = time.time()
    before = snapshot()
    sampler = Sampler()
    sampler.start()
    t0 = time.time()
    rc, err = None, None
    if run_test:
        try:
            rc = run_v2()
        except Exception as exc:  # noqa: BLE001
            err = repr(exc)
    elapsed = round(time.time() - t0, 1)
    sampler.stop_flag.set()
    sampler.join(timeout=10)
    after = snapshot()
    d = diff(before, after)
    roll_files = classify_rollover_files((d["new_files"] or []) + (d["changed"] or []))
    roll_file_bytes = sum(x["bytes"] for x in roll_files)
    # 采样 burst（大写入秒）作为 rollover 窗口估计
    burst = []
    prev = None
    for s in sampler.samples:
        if prev is not None:
            delta = s["total"] - prev["total"]
            if delta > 0:
                burst.append({"t": s["t"], "delta": delta})
        prev = s
    bursts = sorted(burst, key=lambda x: -x["delta"])[:10]
    roll_burst_bytes = sum(b["delta"] for b in bursts if b["delta"] > 5 * BIG)
    # rollover“单次写”估计：把大写入秒按时间聚成事件（gap<=5s），取最大单事件
    big = sorted([b for b in burst if b["delta"] > 5 * BIG], key=lambda x: x["t"])
    clusters = []
    for b in big:
        if clusters and b["t"] - clusters[-1]["last_t"] <= 5.0:
            clusters[-1]["bytes"] += b["delta"]
            clusters[-1]["last_t"] = b["t"]
        else:
            clusters.append({"start_t": b["t"], "last_t": b["t"], "bytes": b["delta"]})
    roll_max_event_bytes = max([c["bytes"] for c in clusters] or [0])
    # 会话文件：按裁决②区分“本次新写（mtime>=run_start）”与 pre-fix stale（不计入 FAIL）
    sess_new, sess_stale = [], []
    for rel, (size, mt) in after.items():
        if "/sessions/" in rel:
            item = {"path": rel, "bytes": size,
                    "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(mt)),
                    "mtime_epoch": mt}
            if mt >= run_start_epoch:
                sess_new.append(item)
            else:
                sess_stale.append(item)
    sess_new.sort(key=lambda x: -x["bytes"])
    sess_stale.sort(key=lambda x: -x["bytes"])
    stale_pre = None
    if sess_stale:
        top = sess_stale[0]
        stale_pre = dict(top)
        stale_pre["sha16"] = sha16_of(str(ROOT / top["path"]))
        stale_pre["note"] = "pre-fix 遗留；按裁决不计入本次阈值，仅作证据（不删/不移动）"
    sess_files = sess_new + sess_stale
    art = None
    if V2_ART.exists():
        try:
            art = json.loads(V2_ART.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            art = None
    turns = ((art or {}).get("summary", {}).get("main_loop") or {}).get("turns")
    doc = {
        "schema": "longconv_v2_mine_v1", "generated_at": now(),
        "run": {"test_rc": rc, "error": err, "elapsed_s": elapsed,
                "test_script": str(V2_SCRIPT), "artifact": str(V2_ART),
                "artifact_exists": V2_ART.exists()},
        "snapshot_before_files": len(before), "snapshot_after_files": len(after),
        "total_written_bytes": d["total_bytes"], "per_tree": d["per_tree"],
        "new_files_n": len(d["new_files"]), "changed_files_n": len(d["changed"]),
        "deleted_files_n": len(d["deleted"]),
        "top_new_files": sorted(d["new_files"], key=lambda x: -x["bytes"])[:15],
        "top_changed_files": sorted(d["changed"], key=lambda x: -x["delta"])[:15],
        "rollover_files": roll_files, "rollover_file_bytes": roll_file_bytes,
        "burst_seconds_top": bursts, "rollover_burst_bytes": roll_burst_bytes,
        "rollover_events_from_bursts": clusters,
        "rollover_max_event_bytes": roll_max_event_bytes,
        "run_start_epoch": run_start_epoch,
        "run_start_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(run_start_epoch)),
        "session_files_new": sess_new, "session_files_stale": sess_stale,
        "stale_pre_fix_session_file": stale_pre,
        "session_new_max_bytes": (sess_new[0]["bytes"] if sess_new else 0),
        "session_files_top": sess_files[:10],
        "main_loop_turns": turns,
        "artifact_summary": (art or {}).get("summary"),
        "artifact_rollovers": (art or {}).get("rollovers"),
        "artifact_probes": (art or {}).get("probes"),
    }
    MINE.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return doc


def independent_probes():
    """长测结束后独立复测（不采信被测脚本自报）。"""
    out = []
    for tier, q, kws in FACTS_EARLY_MID:
        try:
            r = http("/ask", {"text": q}, timeout=180)
            a = str(r.get("answer") or "")
            ok = all(k in a for k in kws)
            out.append({"tier": tier, "q": q, "answer": a[:200], "pass": ok,
                        "state": r.get("state"), "blocks": r.get("block_ids")})
        except Exception as exc:  # noqa: BLE001
            out.append({"tier": tier, "q": q, "error": repr(exc), "pass": False})
    for q in ["我们最开始聊了什么？", "最近在聊什么？", "你现在记得几条长期记忆？"]:
        try:
            r = http("/ask", {"text": q}, timeout=180)
            out.append({"tier": "open", "q": q, "answer": str(r.get("answer") or "")[:260],
                        "state": r.get("state"), "blocks": r.get("block_ids")})
        except Exception as exc:  # noqa: BLE001
            out.append({"tier": "open", "q": q, "error": repr(exc)})
    return out


def build_judge(mine, probes):
    art = json.loads(V2_ART.read_text(encoding="utf-8")) if V2_ART.exists() else {}
    turns = mine.get("main_loop_turns") or 1
    total = mine.get("total_written_bytes") or 0
    per_ask_avg = total / max(1, turns)
    roll_total = mine.get("rollover_file_bytes") or 0
    roll_single = max(mine.get("rollover_max_event_bytes") or 0,
                      mine.get("rollover_burst_bytes") or 0)
    if roll_single == 0:
        # 无 burst 可归因时，用总量作为保守上界（总量<阈值 ⇒ 单次必<阈值）
        roll_single = roll_total
    roll_est = roll_single
    sess_max = mine.get("session_new_max_bytes")
    if sess_max is None:
        sess_max = max([s["bytes"] for s in mine.get("session_files_new") or []] or [0])
    io_probe = parse_io_probe(IO_PROBE)
    io_write = load_other(IO_WRITE)
    io_mem = load_other(IO_MEM)

    burst_deltas = sorted([b["delta"] for b in mine.get("burst_seconds_top") or []],
                          reverse=True)
    max_obs = burst_deltas[0] if burst_deltas else 0
    # 单次 ask 上限：排除最大的 rollover burst 秒（rollover 写入单列）
    max_non_burst = burst_deltas[1] if len(burst_deltas) > 1 else 0
    # 单次 ask 上限只用本 run 自身测量（不把他 run 的 IO-PROBE 数值混入验收）
    per_ask_max = max_non_burst

    # cross-check
    checks, discrepancies = [], []

    run_start = mine.get("run_start_epoch")

    def artifact_status(path, meta, min_rounds=0):
        info = {"exists": bool(meta.get("exists")), "path": str(path),
                "partial": meta.get("partial"), "same_run": None,
                "comparable": False, "reason": ""}
        if not info["exists"]:
            info["reason"] = "missing"
            return info
        try:
            mt = path.stat().st_mtime
        except OSError:
            mt = None
        info["mtime"] = (time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(mt))
                         if mt else None)
        if run_start and mt:
            info["same_run"] = mt >= float(run_start)
        info["rounds"] = meta.get("rounds")
        if info["partial"]:
            info["reason"] = "artifact partial（非完整 run）"
        elif not info["same_run"]:
            info["reason"] = "artifact 早于本次 run（pre-fix/跨 run 参考值，不作数值一致性判定）"
        elif min_rounds and (meta.get("rounds") or 0) < min_rounds:
            info["reason"] = "insufficient rounds"
        else:
            info["comparable"] = True
        return info

    probe_status = artifact_status(IO_PROBE, io_probe, min_rounds=10)
    write_status = artifact_status(IO_WRITE, io_write)
    mem_status = artifact_status(IO_MEM, io_mem)
    probe_usable = probe_status["comparable"]
    write_usable = write_status["comparable"]

    def cmp(name, mine_v, other_v, tol, other_src, usable=True):
        if mine_v is None or other_v is None or not usable:
            checks.append({"metric": name, "mine": mine_v, "other": other_v,
                           "source": other_src, "comparable": False})
            return
        diff = abs(mine_v - other_v) / max(1.0, abs(mine_v))
        ok = diff <= tol
        checks.append({"metric": name, "mine": mine_v, "other": other_v,
                       "source": other_src, "rel_diff": round(diff, 4),
                       "tolerance": tol, "ok": ok})
        if not ok:
            discrepancies.append({"metric": name, "mine": mine_v, "other": other_v,
                                  "source": other_src, "rel_diff": round(diff, 4)})

    cmp("per_ask_avg_bytes", per_ask_avg,
        io_probe.get("mean_round_bytes"), 0.30, "IO-PROBE.mean_round_bytes", probe_usable)
    cmp("per_ask_max_bytes", max_non_burst,
        io_probe.get("max_round_bytes"), 0.35, "IO-PROBE.max_round_bytes", probe_usable)
    cmp("rollover_total_bytes", roll_est, io_probe.get("rollover_bytes_sum"), 0.35,
        "IO-PROBE.rollover_bytes_sum", probe_usable)
    cmp("session_file_bytes", sess_max,
        (io_write.get("numbers") or {}).get(io_write.get("session_key") or "", None), 0.02,
        "IO-WRITE-AUDIT.session", write_usable)
    cmp("per_ask_avg_bytes", per_ask_avg,
        (io_write.get("numbers") or {}).get(io_write.get("per_ask_key") or "", None), 0.30,
        "IO-WRITE-AUDIT.per_ask", write_usable)
    cmp("rollover_total_bytes", roll_est,
        (io_write.get("numbers") or {}).get(io_write.get("rollover_key") or "", None), 0.35,
        "IO-WRITE-AUDIT.rollover", write_usable)

    # acceptance
    # per_ask_max 已在交叉核对前计算
    checks_acc = {
        "per_ask_write_bytes": {"limit": LIMITS["per_ask_write_bytes"],
                                 "measured_avg": round(per_ask_avg),
                                 "measured_max": int(per_ask_max),
                                 "pass": per_ask_max < LIMITS["per_ask_write_bytes"] and per_ask_avg < LIMITS["per_ask_write_bytes"]},
        "rollover_total_write_bytes": {"limit": LIMITS["rollover_total_write_bytes"],
                                       "measured": int(roll_est),
                                       "measured_total_file_bytes": int(roll_total),
                                       "measured_max_event_bytes": int(roll_single),
                                       "pass": roll_est < LIMITS["rollover_total_write_bytes"]},
        "session_file_bytes": {"limit": LIMITS["session_file_bytes"],
                               "measured": int(sess_max),
                               "scope": "仅 mtime>=run_start 的本次新写会话文件",
                               "stale_pre_fix_session_file": mine.get("stale_pre_fix_session_file"),
                               "pass": sess_max < LIMITS["session_file_bytes"]},
    }
    early = [p for p in probes if p.get("tier") == "early"]
    mid = [p for p in probes if p.get("tier") == "mid"]
    art_facts = ((art.get("probes") or {}).get("facts") or [])
    checks_acc["rollover_recall"] = {
        "independent_early": {"n": len(early), "pass": sum(1 for p in early if p.get("pass"))},
        "independent_mid": {"n": len(mid), "pass": sum(1 for p in mid if p.get("pass"))},
        "artifact_facts_pass": sum(1 for f in art_facts if f.get("pass")),
        "artifact_facts_n": len(art_facts),
        "pass": all(p.get("pass") for p in early) and all(p.get("pass") for p in mid),
    }
    all_pass = all(v.get("pass") for v in checks_acc.values())
    minor = [d for d in discrepancies if d["rel_diff"] <= 0.5]
    major = [d for d in discrepancies if d["rel_diff"] > 0.5]
    verdict = ("PASS" if all_pass and not discrepancies else
               ("PASS_WITH_NOTES" if all_pass and not major else "FAIL"))

    doc = {
        "schema": "long_conv_v2_judge_v1",
        "generated_at": now(),
        "role": "长上下文 I/O 风暴独立量化与验收（32k/40k 字符；不采信被测脚本/审计自报）",
        "criteria": {
            "per_ask_write_bytes_lt": LIMITS["per_ask_write_bytes"],
            "rollover_total_write_bytes_lt": LIMITS["rollover_total_write_bytes"],
            "session_file_bytes_lt": LIMITS["session_file_bytes"],
            "recall": "rollover 后 early(车牌/猫) 与 mid(成都/工号/妻子/老家) 全对；recent 作诊断",
        },
        "measurement": mine,
        "acceptance_rulings": {
            "stale_session": "pre-fix 遗留会话文件不计入 FAIL，仅作为 stale_pre_fix_session_file 证据；阈值只适用 mtime>=run_start 的新写文件（同名被重写则按新写计）",
            "baseline_gates": "主门 v11 重叠 22 条须 22/22 一致；辅门 v10 全量 81 条 diff 归因，缺变更清单则 PASS_WITH_NOTES；辅门不得抵消主门 FAIL",
        },
        "independent_probes": probes,
        "acceptance": checks_acc,
        "cross_check": {"io_probe": io_probe, "io_write_audit": io_write,
                         "io_memory_audit": io_mem,
                         "artifact_status": {"io_probe": probe_status,
                                             "io_write_audit": write_status,
                                             "io_memory_audit": mem_status},
                         "comparisons": checks, "discrepancies": discrepancies,
                         "minor": minor, "major": major},
        "verdict": {"overall": verdict, "all_thresholds_pass": all_pass,
                    "cross_check_major": len(major), "cross_check_minor": len(minor)},
        "scores": {
            "rollover_trigger_and_tokens": None,
            "io_per_ask": None, "io_rollover": None, "session_size": None,
            "recall_early_mid": None, "meta_answers": None,
        },
        "recommendations": [],
    }
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="测量 + 跑 40k 长测 + 独立复测 + 判分")
    ap.add_argument("--judge-only", action="store_true", help="只重判（已有 MINE/产物）")
    ap.add_argument("--skip-probes", action="store_true")
    a = ap.parse_args()
    if a.run:
        mine = measure(run_test=True)
    elif MINE.exists():
        mine = json.loads(MINE.read_text(encoding="utf-8"))
    else:
        print("缺少 tmp/LONG-CONV-V2-MINE.json；先 --run")
        return 2
    probes = [] if a.skip_probes else independent_probes()
    if probes:
        mine["independent_probes"] = probes
        MINE.write_text(json.dumps(mine, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    doc = build_judge(mine, probes or mine.get("independent_probes") or [])
    doc["measurement"].pop("artifact_probes", None)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    v = doc["verdict"]
    print("verdict:", v["overall"], "thresholds_pass:", v["all_thresholds_pass"],
          "major_discrepancies:", v["cross_check_major"])
    for k, val in doc["acceptance"].items():
        print(" ", k, "pass" if val.get("pass") else "FAIL", {kk: val.get(kk) for kk in val if kk != "pass"})
    print("wrote", OUT, "sha16", hashlib.sha256(OUT.read_bytes()).hexdigest()[:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())