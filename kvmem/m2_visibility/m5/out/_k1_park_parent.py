# -*- coding: utf-8 -*-
"""K1 dry-run parent: no kill, no signal, `--no-kill` is the only behavior.

Segment 1: _k1_park_child.py (no model) -- self-managed Vulkan instance/device,
park (waitIdle -> destroyDevice -> destroyInstance), holding + 3 pure-file saves,
graceful exit.
Segment 2: _k1_recovery.py (one 14B engine, isolated) -- write the 80-token
M5-KILL-after.kvmem and load_strict read it back (n_tokens=80).

`--armed` is deliberately refused in this round; no TerminateProcess/taskkill/
SIGKILL path exists here.  The parent only polls the child's state file and waits.
"""
import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
M7 = ROOT / "kvmem/m2_visibility/m7"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(M7 / "out"))
import _e3gpu_run as E  # noqa: E402

PREREG = ROOT / "docs/_work/PREREG-KILL-ARM-v2.md"
PREREG_SHA = "42434b91d3923d1a"
PREREG_BYTES = 18253
BEFORE = OUT / "M5-KILL-before.kvmem"
AFTER = OUT / "M5-KILL-after.kvmem"
ART = OUT / "M5-K1-DRYRUN.json"
PROFILE = ROOT / "kvmem/blocks/profile.kvmem"
CHILD = OUT / "_k1_park_child.py"
RECOVERY = OUT / "_k1_recovery.py"
FIXTURE_MANIFEST = OUT / "_k1_fixture_manifest.json"
STATE = OUT / "kill_state_k1_001.log"
CHILD_RESULT = OUT / "_k1_park_result_001.json"
REC_RESULT = OUT / "_k1_recovery_result.json"
TARGET = OUT / "kill_k1/run-001/target.kvmem"
VK_GATE_GIB = 8.6


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def info(path):
    p = Path(path)
    if not p.exists():
        return None
    return {"path": str(p), "sha16": sha16(p), "bytes": os.path.getsize(p),
            "n_tokens": header_ntokens(p) if p.suffix == ".kvmem" else None}


def header_ntokens(path):
    b = open(path, "rb").read(12)
    return int.from_bytes(b[8:12], "little")


def write_json_atomic(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(p) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def start_sampler(tag):
    flag = OUT / ("_k1_stop_%s.flag" % tag)
    peak = OUT / ("_k1_peak_%s.txt" % tag)
    for x in (flag, peak):
        try:
            x.unlink()
        except FileNotFoundError:
            pass
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(E.SAMPLER),
           "-Flag", str(flag), "-Out", str(peak)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         encoding="utf-8", errors="replace")
    time.sleep(0.2)
    return {"proc": p, "flag": flag, "peak": peak}


def stop_sampler(s):
    try:
        s["flag"].write_text("done", encoding="utf-8")
    except OSError:
        pass
    try:
        s["proc"].communicate(timeout=15)
    except subprocess.TimeoutExpired:
        pass
    try:
        return round(float(s["peak"].read_text().strip()) / (1024 ** 3), 4)
    except Exception:  # noqa: BLE001
        return None


def gate_values():
    g = E.gate_values()
    g["prereg_sha16"] = sha16(PREREG)
    g["prereg_ok"] = g["prereg_sha16"] == PREREG_SHA and PREREG.stat().st_size == PREREG_BYTES
    g["free_ram_ok"] = (g.get("free_ram_kb") or 0) >= 8388608
    g["vram_baseline_ok"] = g.get("vram_baseline_gib") is not None and g["vram_baseline_gib"] <= 0.5
    g["gpu_procs_ok"] = g.get("gpu_procs_gt256mb") == 0
    g["browsers_ok"] = g.get("browser_or_code_procs") == 0
    g["gate_ok"] = all(g[k] for k in ("prereg_ok", "free_ram_ok", "vram_baseline_ok",
                                      "gpu_procs_ok", "browsers_ok"))
    return g


def gate_stable(tag, attempts=3, sleep_s=3.0):
    """First reading is preserved; if only vram_baseline is transiently high, recheck."""
    first = gate_values()
    reads = [first]
    cur = first
    for _ in range(attempts - 1):
        if cur["gate_ok"]:
            break
        if not cur.get("vram_baseline_ok") or cur.get("gpu_procs_ok") is False:
            time.sleep(sleep_s)
            cur = gate_values()
            reads.append(cur)
        else:
            break
    return {"tag": tag, "first": first, "final": cur, "reads": reads,
            "gate_ok": bool(cur["gate_ok"]), "transient_vram": not first["gate_ok"] and cur["gate_ok"]}


def host_snapshot(tag):
    h = E.host_check(tag)
    return {"tag": tag, "raw": h}


def parse_states(path):
    states = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.startswith("[STATE "):
                    continue
                try:
                    head, body = line.split("] ", 1)
                    name = head.split()[1]
                    detail = json.loads(body)
                    states.append({"state": name, "t_mono": detail.get("t_mono"),
                                   "t_wall": detail.get("t_wall"),
                                   "detail": {k: v for k, v in detail.items()
                                              if k not in ("state", "t_mono", "t_wall")}})
                except Exception:  # noqa: BLE001
                    states.append({"state": "parse_error", "raw": line.rstrip("\n")})
    except FileNotFoundError:
        pass
    return states


def run_child_segment():
    for p in (STATE, CHILD_RESULT):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    if TARGET.parent.exists():
        import shutil
        shutil.rmtree(TARGET.parent)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    s = start_sampler("dryrun")
    cmd = [sys.executable, str(CHILD), "--run", "1", "--source", str(BEFORE),
           "--target", str(TARGET), "--state-log", str(STATE), "--result", str(CHILD_RESULT)]
    p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    timeline = []
    poll_n = 0
    timed_out = False
    last_size = -1
    while p.poll() is None:
        poll_n += 1
        try:
            st = parse_states(STATE)
            if len(st) > len(timeline):
                timeline = st
        except Exception:  # noqa: BLE001
            pass
        if time.perf_counter() - t0 > 120:
            timed_out = True
            break
        time.sleep(0.005)
    # parent never signals; on timeout it records and stops (child is left to exit).
    if timed_out:
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
    try:
        so, se = p.communicate(timeout=20 if not timed_out else 1)
    except subprocess.TimeoutExpired:
        so, se = "", ""
    elapsed = round(time.perf_counter() - t0, 3)
    peak = stop_sampler(s)
    timeline = parse_states(STATE)
    res = json.load(open(CHILD_RESULT, encoding="utf-8")) if CHILD_RESULT.exists() else None
    return {"segment": "dryrun_no_model", "t0": t0, "elapsed_s": elapsed, "timed_out": timed_out,
            "returncode": p.returncode, "poll_iterations": poll_n, "peak_gib": peak,
            "state_log": {"path": str(STATE), "sha16": sha16(STATE) if STATE.exists() else None,
                          "bytes": os.path.getsize(STATE) if STATE.exists() else None},
            "states": timeline, "child_result": res,
            "stdout_tail": (so or "")[-8000:], "stderr_tail": (se or "")[-8000:],
            "signals_sent": 0, "armed": False, "model_loaded": False}


def run_recovery_segment():
    for p in (REC_RESULT,):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    t0 = time.perf_counter()
    s = start_sampler("recovery")
    cmd = [sys.executable, str(RECOVERY), "--before", str(BEFORE), "--after", str(AFTER),
           "--result", str(REC_RESULT)]
    p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    timed_out = False
    try:
        so, se = p.communicate(timeout=900)
    except subprocess.TimeoutExpired:
        timed_out = True
        so, se = "", ""
        try:
            p.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
    elapsed = round(time.perf_counter() - t0, 3)
    peak = stop_sampler(s)
    res = json.load(open(REC_RESULT, encoding="utf-8")) if REC_RESULT.exists() else None
    return {"segment": "recovery_14b_load_strict", "elapsed_s": elapsed, "timed_out": timed_out,
            "returncode": p.returncode, "peak_gib": peak, "result": res,
            "stdout_tail": (so or "")[-8000:], "stderr_tail": (se or "")[-8000:],
            "signals_sent": 0, "armed": False, "model_loaded": True}


def ensure_fixtures():
    if not PROFILE.exists():
        raise SystemExit("profile missing: %s" % PROFILE)
    p = info(PROFILE)
    if p["sha16"] != "3b046c8ee3fb3b53" or p["bytes"] != 5224388:
        raise SystemExit("profile identity changed: %r" % p)
    if not BEFORE.exists() or info(BEFORE)["sha16"] != p["sha16"]:
        import shutil
        BEFORE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROFILE, BEFORE)
        with open(BEFORE, "rb+") as f:
            os.fsync(f.fileno())
    b = info(BEFORE)
    b["source"] = "copy_of_profile.kvmem"
    b["written_by_engine"] = False
    return {"profile": p, "before": b, "after": info(AFTER),
            "before_n_tokens": header_ntokens(BEFORE),
            "after_present": AFTER.exists(),
            "after_source": "M5-KILL-after.kvmem is written by the isolated 14B engine in the recovery segment; never a copy"}


def fixture_code_state():
    files = {"child": info(CHILD), "parent": info(str(Path(__file__).resolve())),
             "recovery": info(RECOVERY)}
    return files


def fixture_assert(manifest_path):
    mp = Path(manifest_path)
    if not mp.exists():
        return {"manifest": str(mp), "manifest_present": False, "all_match": False,
                "observed": fixture_code_state(), "expected": None}
    m = json.load(open(mp, encoding="utf-8"))
    obs = fixture_code_state()
    expected = m.get("files") or {}
    match = all(
        expected.get(k, {}).get("sha16") == obs[k].get("sha16") and
        expected.get(k, {}).get("bytes") == obs[k].get("bytes")
        for k in ("child", "parent", "recovery")
    )
    return {"manifest": str(mp), "manifest_present": True,
            "manifest_sha16": sha16(mp), "manifest_bytes": os.path.getsize(mp),
            "expected": expected, "observed": obs, "all_match": bool(match)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--armed", action="store_true")
    ap.add_argument("--no-kill", action="store_true")
    ap.add_argument("--fixture-manifest", default=str(FIXTURE_MANIFEST))
    a = ap.parse_args()
    if a.armed:
        print("REFUSED: --armed is not implemented in this round; no kill signal was sent.", flush=True)
        return 2
    at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    art = {"schema": "m5_k1_dryrun_v1", "task": "K1 fixture + empty-gun dry run; no kill",
           "role": "CAND", "at": at,
           "prereg": {"path": str(PREREG), "sha16": sha16(PREREG), "bytes": PREREG.stat().st_size},
           "armed": False, "signals_sent": 0, "no_kill": True,
           "model_loaded": {"dryrun": False, "recovery": False}, "kill_attempts": 0,
           "segments": {}, "attempts": [],
           "host_gate": {}, "device": {}, "limitations": [], "status": "running",
           "four_state": "未做（100 次真杀未跑；本轮只做试装）"}
    try:
        art["fixtures"] = ensure_fixtures()
    except BaseException as e:  # noqa: BLE001
        art["status"] = "未接上（夹具不可用）"
        art["attempts"].append({"n": 1, "stage": "fixture", "status": "failed",
                                "reason": type(e).__name__ + ": " + str(e)})
        write_json_atomic(ART, art)
        print("K1_DRYRUN " + json.dumps({"status": art["status"], "error": art["attempts"]}, ensure_ascii=False))
        return 1
    pre = fixture_assert(a.fixture_manifest)
    art["fixtures"]["code"] = {"manifest": str(a.fixture_manifest), "pre": pre,
                               "pre_match": bool(pre.get("all_match"))}
    if not pre.get("all_match"):
        art["status"] = "未接上（夹具 sha 前置断言失败）"
        art["attempts"].append({"n": 1, "stage": "fixture_hash_pre", "status": "failed",
                                "reason": "fixture sha/bytes mismatch before run", "assert": pre})
        write_json_atomic(ART, art)
        print("K1_DRYRUN " + json.dumps({"status": art["status"], "assert": pre}, ensure_ascii=False))
        return 1
    g0 = gate_stable("before_dryrun")
    art["host_gate"]["before_dryrun"] = g0
    art["host_gate"]["before_dryrun_snapshot"] = host_snapshot("before_dryrun")
    if not g0["gate_ok"]:
        art["status"] = "未接上（装置不合格：试装前 gate）"
        art["attempts"].append({"n": 1, "stage": "dryrun", "status": "aborted_gate",
                                "reason": "host gate before dryrun failed", "gate": g0})
        write_json_atomic(ART, art)
        print("K1_DRYRUN " + json.dumps({"status": art["status"]}, ensure_ascii=False))
        return 1

    dry = run_child_segment()
    g1 = gate_stable("after_dryrun")
    art["segments"]["dryrun"] = dry
    art["host_gate"]["after_dryrun"] = g1
    art["host_gate"]["after_dryrun_snapshot"] = host_snapshot("after_dryrun")
    cr = dry.get("child_result") or {}
    vk = cr.get("vk") or {}
    saves = (cr.get("save") or {}).get("saves") or []
    dry_ok = (dry.get("returncode") == 0 and not dry.get("timed_out") and
              cr.get("status") == "completed" and vk.get("ok") and
              vk.get("device_destroyed") and vk.get("instance_destroyed") and
              len(saves) == 3 and all(not x.get("third") for x in saves) and
              (dry.get("elapsed_s") or 9999) < 8.0 and g1["gate_ok"])
    art["attempts"].append({"n": 1, "stage": "dryrun_no_model",
                            "status": "completed" if dry_ok else "failed",
                            "reason": "self-managed Vulkan park + 3 file saves + graceful exit" if dry_ok else
                                      "dryrun condition failed: return=%r timed_out=%r vk_ok=%r saves=%d gate=%r" %
                                      (dry.get("returncode"), dry.get("timed_out"), vk.get("ok"), len(saves), g1["gate_ok"]),
                            "signals_sent": 0, "armed": False})
    art["device"]["dryrun"] = {"vulkan": vk, "peak_gib": dry.get("peak_gib"),
                               "model_loaded": False, "offloaded": None,
                               "signals_sent": 0}

    if not dry_ok:
        art["status"] = "未接上（试装段失败）"
        art["limitations"].append("试装段失败；按上界停手，不跑恢复段，不重试。")
        write_json_atomic(ART, art)
        print("K1_DRYRUN " + json.dumps({"status": art["status"], "attempts": art["attempts"]}, ensure_ascii=False))
        return 1

    # Isolated recovery segment: only after the no-model child has fully exited.
    g2 = gate_stable("before_recovery", attempts=3, sleep_s=3.0)
    art["host_gate"]["before_recovery"] = g2
    art["host_gate"]["before_recovery_snapshot"] = host_snapshot("before_recovery")
    if not g2["gate_ok"]:
        art["status"] = "未接上（装置不合格：恢复段前 gate）"
        art["attempts"].append({"n": 2, "stage": "recovery", "status": "aborted_gate",
                                "reason": "host gate before recovery failed", "gate": g2})
        write_json_atomic(ART, art)
        print("K1_DRYRUN " + json.dumps({"status": art["status"], "attempts": art["attempts"]}, ensure_ascii=False))
        return 1

    rec = run_recovery_segment()
    g3 = gate_stable("after_recovery")
    art["segments"]["recovery"] = rec
    art["host_gate"]["after_recovery"] = g3
    art["host_gate"]["after_recovery_snapshot"] = host_snapshot("after_recovery")
    rr = rec.get("result") or {}
    ls = rr.get("load_strict") or {}
    rec_ok = (rec.get("returncode") == 0 and not rec.get("timed_out") and
              rr.get("status") == "completed" and ls.get("done") and ls.get("n_tokens") == 80 and
              ls.get("match") and rr.get("after_info", {}).get("n_tokens") == 80 and
              g3["gate_ok"] and (rec.get("peak_gib") is None or rec["peak_gib"] <= VK_GATE_GIB))
    art["attempts"].append({"n": 2, "stage": "recovery_14b_load_strict",
                            "status": "completed" if rec_ok else "failed",
                            "reason": "14B engine wrote after (80 tok) and load_strict read it back" if rec_ok else
                                      "recovery condition failed: return=%r timed_out=%r status=%r load=%r gate=%r peak=%r" %
                                      (rec.get("returncode"), rec.get("timed_out"), rr.get("status"), ls, g3["gate_ok"], rec.get("peak_gib")),
                            "signals_sent": 0, "armed": False, "model_loaded": True})
    art["device"]["recovery"] = {"model_loaded": True, "peak_gib": rec.get("peak_gib"),
                                 "meta": rr.get("device"), "load_strict": ls,
                                 "signals_sent": 0}
    bi = info(BEFORE)
    bi["source"] = "copy_of_profile.kvmem"
    bi["written_by_engine"] = False
    ai = info(AFTER)
    if ai:
        ai["source"] = "k1_recovery 14B engine"
        ai["written_by_engine"] = True
    art["fixtures"]["after"] = ai
    art["fixtures"]["after_present"] = AFTER.exists()
    art["fixtures_json"] = {"before": bi, "after": ai,
                            "before_n_tokens": header_ntokens(BEFORE) if BEFORE.exists() else None,
                            "after_n_tokens": header_ntokens(AFTER) if AFTER.exists() else None,
                            "distinction": "before = copy_of_profile.kvmem (not engine-written); after = written by k1_recovery 14B engine (80 tok)"}
    post = fixture_assert(a.fixture_manifest)
    art["fixtures"]["code"]["post"] = post
    art["fixtures"]["code"]["post_match"] = bool(post.get("all_match"))
    if not post.get("all_match"):
        rec_ok = False
        art["disposition"] = "夹具代码在运行中被改动：post sha/bytes 不一致，本次读数不得作为合格试装。"
    art["model_loaded"] = {"dryrun": False, "recovery": True}
    art["status"] = "dryrun_completed" if (dry_ok and rec_ok) else "未接上（试装/恢复失败）"
    art["four_state"] = "未做（100 次真杀未跑）" if art["status"] == "dryrun_completed" else "未接上（试装/恢复失败）"
    art["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    art["timeline"] = {"dryrun": dry.get("states"), "recovery": rr.get("steps")}
    art["limitations"] = [
        "本轮只做夹具试装，未发任何 kill 信号；真实 K1 100 run 未跑，等用户回来单独发单。",
        "试装段 model_loaded=false；恢复段 model_loaded=true，单独隔离进程，不在任何 kill 窗口内。",
        "K1 自管 VkDevice 不等同于 llama 引擎设备；本试装只证明装置/文件窗口可达。",
        "Vulkan destroy 入口本身返回 void，故 destroy_device/destroy_instance 记 completed=true、rc=null；create 的 VkResult 记在 calls。",
        "峰值由 100 ms 采样器读取，非内核级峰值。",
    ]
    if not dry_ok:
        art["limitations"].append("试装段条件未全过；不跑恢复段。")
    if not rec_ok:
        art["limitations"].append("恢复段条件未全过；不重试。")
    write_json_atomic(ART, art)
    print("K1_DRYRUN " + json.dumps({"status": art["status"], "attempts": art["attempts"],
                                     "device": art["device"], "artifact": info(ART)}, ensure_ascii=False))
    return 0 if (dry_ok and rec_ok) else 1


if __name__ == "__main__":
    sys.exit(main())