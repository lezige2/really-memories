#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""训练作业 1924 健康监控（AA 集群；只读 SSH，不提交/取消/改远端）。

每 15 分钟由后台循环调用一次：
  ssh ... "tr '\\r' '\\n' < ~/llm-ft/slurm-1924.out | tail -40; echo ---; squeue -u xy002; echo ---; sacct -j 1924 ..."
解析 step/总步数、s/it、loss（若日志有）、job state；扫描异常 NaN/Inf、device mismatch、
OOM、Traceback、srun error、非 RUNNING；追加到 out/TRAIN-1924-MONITOR.json 时间序列。
异常时置 alerts 并在 stdout 打印原始日志行（便于立即上报）。
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
ART = ROOT / "out" / "TRAIN-1924-MONITOR.json"
KEY = os.path.expanduser("~/.ssh/dftcloud-xy002-20261028.key")
HOST = "xy002@ssh.dftcloud.cn"
PORT = "6023"
REMOTE = ("tr '\\r' '\\n' < ~/llm-ft/slurm-1924.out | tail -60; "
          "echo ---SQUEUE---; squeue -u xy002; "
          "echo ---SACCT---; sacct -j 1924 --format=JobID,State,Elapsed,AllocTRES%40 -n 2>/dev/null; "
          "echo ---STATE---; "
          "S=$(find ~/llm-ft/output -maxdepth 3 -name trainer_state.json 2>/dev/null | head -1); "
          "if [ -n \"$S\" ]; then python3 -c \"import json;d=json.load(open('$S'));"
          "h=[x for x in d.get('log_history',[]) if 'loss' in x];"
          "print('LOSS_JSON', json.dumps(h[-1], ensure_ascii=False) if h else 'NONE')\" 2>/dev/null; "
          "else echo LOSS_JSON NONE; fi")


def ssh(cmd, timeout=90):
    t0 = time.time()
    try:
        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20",
             "-i", KEY, "-p", PORT, HOST, cmd],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout)
        return {"rc": r.returncode, "stdout": r.stdout or "",
                "stderr": r.stderr or "", "elapsed_s": round(time.time() - t0, 2)}
    except subprocess.TimeoutExpired:
        return {"rc": "TIMEOUT", "stdout": "", "stderr": "ssh timeout",
                "elapsed_s": round(time.time() - t0, 2)}


def parse(raw):
    lines = [ln.rstrip() for ln in raw.splitlines()]
    # 最后一条 tqdm 进度行
    prog = None
    for ln in reversed(lines):
        m = re.search(r"(\d+)/(\d+)\s*\[([0-9:]+)<([0-9:]+),\s*([0-9.]+)s/it\]", ln)
        if m:
            prog = {"step": int(m.group(1)), "total": int(m.group(2)),
                    "elapsed": m.group(3), "eta": m.group(4),
                    "s_per_it": float(m.group(5)),
                    "pct": round(100.0 * int(m.group(1)) / max(1, int(m.group(2))), 2)}
            break
    loss = None
    loss_step = None
    for ln in reversed(lines):
        m = re.search(r"'loss'\s*:\s*([0-9.eE+-]+)", ln)
        if m:
            try:
                loss = float(m.group(1))
            except ValueError:
                loss = m.group(1)
            break
    if "---STATE---" in raw:
        st = raw.split("---STATE---", 1)[1]
        for ln in st.splitlines():
            if ln.startswith("LOSS_JSON "):
                payload = ln[len("LOSS_JSON "):].strip()
                try:
                    obj = json.loads(payload)
                    loss = obj.get("loss", loss)
                    loss_step = obj.get("step")
                except Exception:      # noqa: BLE001
                    pass
                break
    # 异常扫描：只看训练日志段（---SQUEUE--- 之前），避免把 sacct 子步骤状态当训练异常
    log_lines = raw.split("---SQUEUE---")[0].splitlines()
    joined = "\n".join(log_lines)
    patterns = {
        "nan": r"\bNaN\b|\bnan\b",
        "inf": r"\bInf\b|\binf\b",
        "device_mismatch": r"Expected all tensors to be on the same device|device mismatch",
        "oom": r"OutOfMemoryError|CUDA out of memory|OOM",
        "traceback": r"Traceback \(most recent call last\)",
        "srun_error": r"srun: error|slurmstepd: error",
        "process_exit": r"exited with exit code|srun: error: .*exited|CANCELLED|FAILED",
    }
    hits = []
    for name, pat in patterns.items():
        for ln in log_lines:
            if re.search(pat, ln, re.I):
                hits.append({"kind": name, "line": ln[:300]})
    # job state：只看主作业行（JobID 精确 == "1924"）；子步骤（1924.0/.batch）单独记录
    state = None
    substeps = []
    sacct_lines = []
    if "---SACCT---" in raw:
        sacct_lines = raw.split("---SACCT---", 1)[1].strip().splitlines()
    for ln in sacct_lines:
        parts = ln.split()
        if not parts:
            continue
        jid = parts[0]
        if jid == "1924":
            state = parts[1] if len(parts) > 1 else None
        elif jid.startswith("1924."):
            substeps.append({"jobid": jid,
                             "state": parts[1] if len(parts) > 1 else None,
                             "elapsed": parts[2] if len(parts) > 2 else None})
    # 子步骤 CANCELLED/FAILED（如 srun nvidia-smi 超时）记为 warning，不算主作业异常
    substep_warn = [x for x in substeps
                    if x["state"] not in ("RUNNING", "COMPLETED", None)]
    squeue_state = None
    if "---SQUEUE---" in raw:
        sq = raw.split("---SQUEUE---", 1)[1].split("---SACCT---")[0].strip().splitlines()
        for ln in sq:
            if "1924" in ln:
                squeue_state = "RUNNING" if re.search(r"\bR\b", ln) else "NOT_RUNNING"
                break
    return {"progress": prog, "loss": loss, "loss_step": loss_step,
            "anomaly_hits": hits, "substeps": substeps,
            "substep_warnings": substep_warn,
            "job_state_sacct": state, "job_state_squeue": squeue_state,
            "raw_tail": lines[-12:]}


def main():
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    r = ssh(REMOTE)
    parsed = parse(r["stdout"] or r["stderr"] or "")
    anomalies = list(parsed["anomaly_hits"])
    if parsed["job_state_sacct"] and parsed["job_state_sacct"] != "RUNNING" \
            and parsed["job_state_squeue"] != "RUNNING":
        anomalies.append({"kind": "job_not_running",
                          "line": "state=%s" % parsed["job_state_sacct"]})
    sample = {"ts": now, "ssh": {"rc": r["rc"], "elapsed_s": r["elapsed_s"],
                                 "stderr": (r["stderr"] or "")[:300]},
              **parsed, "anomalies": anomalies}
    doc = {"schema": "train_1924_monitor_v1", "job_id": "1924",
           "node": "co2-cn2", "gpus": "2x V100-SXM2-16GB",
           "remote_log": "~/llm-ft/slurm-1924.out",
           "interval_s": 900, "samples": [], "alerts": []}
    if ART.exists():
        try:
            doc = json.loads(ART.read_text(encoding="utf-8"))
        except Exception:      # noqa: BLE001
            pass
    doc.setdefault("samples", []).append(sample)
    if anomalies:
        doc.setdefault("alerts", []).append({"ts": now, "n": len(anomalies),
                                             "kinds": sorted({a["kind"] for a in anomalies}),
                                             "lines": [a["line"] for a in anomalies[:5]]})
    doc["last_updated"] = now
    doc["latest"] = {
        "ts": now,
        "step": (parsed["progress"] or {}).get("step"),
        "total": (parsed["progress"] or {}).get("total"),
        "s_per_it": (parsed["progress"] or {}).get("s_per_it"),
        "eta": (parsed["progress"] or {}).get("eta"),
        "loss": parsed["loss"],
        "loss_step": parsed.get("loss_step"),
        "job_state": parsed["job_state_sacct"] or parsed["job_state_squeue"],
        "n_anomalies": len(anomalies),
    }
    doc["anomaly_policy"] = ("alerts 只报：主作业(1924)非 RUNNING、NaN/Inf、device mismatch、"
                             "OOM、Traceback、srun error；子步骤(1924.x) CANCELLED/FAILED "
                             "仅记 substep_warnings（如 srun nvidia-smi 超时不等于训练失败）。")
    doc["n_samples"] = len(doc["samples"])
    ART.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(ART) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, ART)
    print(json.dumps({"artifact": str(ART), "latest": doc["latest"],
                      "anomalies": anomalies[:5],
                      "n_samples": doc["n_samples"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())