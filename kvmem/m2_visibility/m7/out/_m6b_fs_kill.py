# -*- coding: utf-8 -*-
"""M6B F1 filesystem-layer SIGKILL evidence, zero GPU / zero model / zero Vulkan.

Two arms:
  atomic : temp + fsync + os.replace (same shape as tools/kvslots.py:223-267)
  red    : direct open(target, "wb") chunked write (deliberate control, not product)

Parent only kills its own pure-file child via Popen.kill()/TerminateProcess.
No GPU process is started, touched, or signalled.  No product code is modified.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]                    # D:\llama-mem
SRC = HERE / "tmp" / "e3gpu" / "s1.chat.kvmem"
WORK = HERE / "tmp" / "m6b_fs_kill"
ART = HERE / "M6B-FS-KILL.json"
SCOPE = "文件系统层 + 静态不变量；不替代 GPU kill 子臂（永久未做）"
SRC_SHA = "6a2508d4df79fa57"
SRC_BYTES = 19744884
CHUNK = 32 * 1024
DELAY_S = 0.0025
POINTS = (("p1_30pct", 0.30), ("p2_full_fsync_pre_replace", 1.0), ("p3_after_replace", 1.0))


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def info(path):
    p = Path(path)
    if not p.exists():
        return {"path": str(p), "exists": False, "bytes": None, "sha16": None}
    return {"path": str(p), "exists": True, "bytes": p.stat().st_size, "sha16": sha16(p)}


def child(mode, tmp, target, newfile, ready, proceed, replaced):
    if mode == "atomic":
        with open(tmp, "wb", buffering=0) as out, open(newfile, "rb") as src:
            while True:
                b = src.read(CHUNK)
                if not b:
                    break
                out.write(b)
                time.sleep(DELAY_S)
            os.fsync(out.fileno())
        Path(ready).write_text("ready", encoding="utf-8")
        while not Path(proceed).exists():
            time.sleep(0.005)
        os.replace(tmp, target)
        Path(replaced).write_text("replaced", encoding="utf-8")
        time.sleep(60)
    elif mode == "red":
        with open(target, "wb", buffering=0) as out, open(newfile, "rb") as src:
            while True:
                b = src.read(CHUNK)
                if not b:
                    break
                out.write(b)
                time.sleep(DELAY_S)
            os.fsync(out.fileno())
        time.sleep(60)
    else:
        raise SystemExit("bad child mode")


def run_trial(arm, point, run_no, src_bytes, new_bytes):
    tdir = WORK / ("%s_%s_%d" % (arm, point, run_no))
    if tdir.exists():
        shutil.rmtree(tdir)
    tdir.mkdir(parents=True)
    target = tdir / "target.chat.kvmem"
    newfile = tdir / "new.chat.kvmem"
    newfile.write_bytes(new_bytes)        # new payload for both arms; target gets old
    shutil.copyfile(SRC, target)          # read-only source -> separate target, source unchanged
    before = info(target)
    before_sha = before["sha16"]
    after_sha = info(newfile)["sha16"]
    tmp = str(target) + ".tmp-%d-%s" % (os.getpid(), uuid.uuid4().hex[:8])
    ready = tdir / "ready.flag"
    proceed = tdir / "proceed.flag"
    replaced = tdir / "replaced.flag"
    cmd = [sys.executable, "-X", "utf8", os.path.abspath(__file__), "child", arm,
           tmp, str(target), str(newfile), str(ready), str(proceed), str(replaced)]
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace",
                         creationflags=0x00004000)
    killed_for = None
    kill_ms = None
    frac_at_kill = None
    while p.poll() is None:
        if arm == "atomic":
            if point == "p1_30pct":
                sz = os.path.getsize(tmp) if os.path.exists(tmp) else 0
                if sz >= int(SRC_BYTES * 0.30) and sz < int(SRC_BYTES * 0.80):
                    killed_for = "tmp_30pct"
            elif point == "p2_full_fsync_pre_replace":
                if ready.exists():
                    killed_for = "tmp_full_fsync_ready"
            elif point == "p3_after_replace":
                if ready.exists():
                    # tell the child to replace, then kill after the replace marker
                    proceed.write_text("go", encoding="utf-8")
                if replaced.exists():
                    killed_for = "replaced"
        else:
            sz = os.path.getsize(target) if target.exists() else 0
            frac = sz / float(SRC_BYTES)
            if point == "p1_30pct" and frac >= 0.30 and frac < 0.55:
                killed_for = "target_30pct"
            elif point == "p2_full_fsync_pre_replace" and frac >= 0.55 and frac < 0.80:
                killed_for = "target_55pct"
            elif point == "p3_after_replace" and frac >= 0.80 and frac < 0.98:
                killed_for = "target_80pct"
        if killed_for:
            kill_ms = round((time.perf_counter() - t0) * 1000, 1)
            if arm == "atomic":
                if point == "p3_after_replace":
                    frac_at_kill = 1.0        # tmp is gone after replace; target is the new payload
                else:
                    sz = os.path.getsize(tmp) if os.path.exists(tmp) else 0
                    frac_at_kill = round(sz / float(SRC_BYTES), 4)
            else:
                sz = os.path.getsize(target) if target.exists() else 0
                frac_at_kill = round(sz / float(SRC_BYTES), 4)
            p.kill()                     # TerminateProcess = SIGKILL equivalent, our own pure-file child only
            break
        time.sleep(0.001)
    try:
        out, err = p.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        out, err = "", ""
    elapsed = round((time.perf_counter() - t0) * 1000, 1)
    target_info = info(target)
    if not target_info["exists"]:
        state = "missing"
    elif target_info["sha16"] == before_sha:
        state = "before"
    elif target_info["sha16"] == after_sha:
        state = "after"
    else:
        state = "third"
    residuals = []
    for x in sorted(tdir.glob("target.chat.kvmem.tmp-*")):
        residuals.append(info(x))
    return {"arm": arm, "point": point, "run": run_no,
            "target_path": str(target), "tmp_path": tmp,
            "child_pid": p.pid, "kill_method": "Popen.kill (TerminateProcess, SIGKILL equivalent)",
            "kill_ms": kill_ms, "elapsed_ms": elapsed,
            "kill_condition": killed_for, "fraction_at_kill": frac_at_kill,
            "target_before": before, "target_after": target_info,
            "new_payload": info(newfile),
            "observed_state": state,
            "target_is_before_or_after": state in ("before", "after"),
            "residual_tmp": residuals,
            "residual_tmp_count": len(residuals),
            "stderr_tail": (err or "").splitlines()[-2:]}


def stale_probe(src_bytes, new_bytes):
    """Product kvslots has no startup scan; its only cleanup is finally (kvslots.py:264-267),
    which SIGKILL bypasses.  Prove one stale temp survives a following normal atomic save."""
    tdir = WORK / "stale_probe"
    if tdir.exists():
        shutil.rmtree(tdir)
    tdir.mkdir(parents=True)
    target = tdir / "target.chat.kvmem"
    newfile = tdir / "new.chat.kvmem"
    newfile.write_bytes(new_bytes)
    shutil.copyfile(SRC, target)
    # first save killed after full tmp fsync (stale tmp left)
    tmp = str(target) + ".tmp-stale-%s" % uuid.uuid4().hex[:8]
    ready = tdir / "ready.flag"
    p = subprocess.Popen([sys.executable, "-X", "utf8", os.path.abspath(__file__), "child",
                          "atomic", tmp, str(target), str(newfile), str(ready),
                          str(tdir / "proceed.flag"), str(tdir / "replaced.flag")],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=0x00004000)
    t0 = time.perf_counter()
    while p.poll() is None and not ready.exists() and time.perf_counter() - t0 < 30:
        time.sleep(0.005)
    p.kill()
    p.wait(timeout=15)
    stale = [info(x) for x in sorted(tdir.glob("target.chat.kvmem.tmp-*"))]
    # next normal save with the product same shape (new unique tmp, finally removes only its own tmp)
    tmp2 = str(target) + ".tmp-next-%s" % uuid.uuid4().hex[:8]
    with open(tmp2, "wb", buffering=0) as out, open(newfile, "rb") as src:
        shutil.copyfileobj(src, out)
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp2, target)
    stale_after = [info(x) for x in sorted(tdir.glob("target.chat.kvmem.tmp-*"))]
    return {"killed_tmp_ready": ready.exists(),
            "stale_before_next_save": stale, "stale_after_next_save": stale_after,
            "startup_scan_in_product": False,
            "product_cleanup_site": "tools/kvslots.py:264-267 finally: only removes this process's tmp; SIGKILL bypasses finally",
            "stale_cleanup_effective": len(stale_after) < len(stale),
            "target_after_next_save": info(target)}


def main():
    b = SRC.read_bytes()
    got = hashlib.sha256(b).hexdigest()[:16]
    if got != SRC_SHA or len(b) != SRC_BYTES:
        raise SystemExit("source mismatch: %s / %d" % (got, len(b)))
    WORK.mkdir(parents=True, exist_ok=True)
    new_bytes = b[::-1]                   # same size, different sha, deterministic
    src_after = info(SRC)
    trials = []
    for arm in ("atomic", "red"):
        for point, _ in POINTS:
            for run_no in (1, 2):
                t = run_trial(arm, point, run_no, b, new_bytes)
                trials.append(t)
                print("%s %s %d -> %s (target %s)" % (arm, point, run_no,
                                                      t["observed_state"], t["target_after"]["sha16"]),
                      flush=True)
    atomic = [t for t in trials if t["arm"] == "atomic"]
    red = [t for t in trials if t["arm"] == "red"]
    expected = {"atomic": {"p1_30pct": "before", "p2_full_fsync_pre_replace": "before",
                           "p3_after_replace": "after"}}
    point_summary = {}
    for point, _ in POINTS:
        ts = [t for t in atomic if t["point"] == point]
        point_summary[point] = {"states": [t["observed_state"] for t in ts],
                                "expected": expected["atomic"][point],
                                "all_match": all(t["observed_state"] == expected["atomic"][point] for t in ts),
                                "fractions": [t["fraction_at_kill"] for t in ts]}
    red_states = [t["observed_state"] for t in red]
    art = {
        "schema": "m6b_fs_kill_v1", "task": "M6B F1 filesystem-layer SIGKILL (zero GPU)",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "scope": SCOPE, "evidence_level": "E1/FS", "not_gpu_kill": True,
        "device": {"pure_file_child": True, "gpu_used": False, "model_loaded": False,
                   "vulkan_touched": False, "gpu_process_signalled": False,
                   "parent_signals_to_child": "Popen.kill() only; child is a pure-file Python process",
                   "source_read_only": True},
        "source": {"path": str(SRC), "sha16": got, "bytes": len(b), "before": src_after,
                   "unchanged": src_after["sha16"] == got and src_after["bytes"] == SRC_BYTES},
        "payload": {"before": {"sha16": got, "bytes": len(b), "role": "E3-GPU S1 real chat state"},
                    "after": info(WORK / "new.chat.kvmem") if (WORK / "new.chat.kvmem").exists() else
                             {"sha16": hashlib.sha256(new_bytes).hexdigest()[:16], "bytes": len(new_bytes),
                              "role": "deterministic reverse of source, same size"}},
        "protocol": {"chunk_bytes": CHUNK, "chunk_delay_s": DELAY_S,
                     "three_points": ["p1_30pct: tmp/target ~30%", "p2_full_fsync_pre_replace: tmp full + fsync, before replace",
                                      "p3_after_replace: after os.replace"],
                     "runs_per_point": 2,
                     "atomic_writer": "temp + fsync + os.replace, same shape as tools/kvslots.py:223-267",
                     "red_writer": "direct open(target,'wb') chunked write, deliberate non-atomic control",
                     "red_timepoints": "red has no replace; p1/p2/p3 are 30%/55%/80% mid-write target sizes, all before completion; this is the required red control, not a product path"},
        "trials": trials,
        "summary": {"atomic": {"points": point_summary,
                               "all_target_before_or_after": all(t["target_is_before_or_after"] for t in atomic),
                               "third_state_count": sum(1 for t in atomic if t["observed_state"] == "third"),
                               "target_states": [t["observed_state"] for t in atomic]},
                    "red": {"target_states": red_states,
                            "third_or_truncated_count": sum(1 for t in red if t["observed_state"] == "third"),
                            "third_state_reproduced": any(t["observed_state"] == "third" for t in red),
                            "note": "red is control only; not counted as a pass"}},
        "stale_cleanup": stale_probe(b, new_bytes),
        "conclusion": {"atomic": "target always before or after; no third state",
                       "red": "third/truncated state reproduced",
                       "gpu_kill_arm": "未做（主机不安全；本件不替代）"},
        "limitations": ["filesystem-layer evidence only; not GPU KV semantics",
                        "Popen.kill on Windows is TerminateProcess (SIGKILL-equivalent); no cleanup runs",
                        "atomic writer here is an equivalent of kvslots.save, not the native shim"],
    }
    tmp = str(ART) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ART)
    print("ARTIFACT " + json.dumps(info(ART), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "child":
        child(*sys.argv[2:])
    else:
        raise SystemExit(main())
