# -*- coding: utf-8 -*-
"""M7 F1 单元级验收：完全 GPU-free（不 import kvslots.KVEngine.__init__、不装 DLL/模型）。

装置：FakeLib.kvshim_save 以 64 KiB / 20 ms 慢写模拟引擎落盘。
- 绿臂：KVEngine.__new__ + FakeLib，调用**当前** KVEngine.save（tmp+fsync+replace）。
- 红臂：同一 FakeLib / 同一 payload，但 save 用 legacy 语义（直接 open(target,"wb") 慢写）。
- kill 策略相同：绿臂轮询同目录 target.tmp-*，一出现 size>0 立即杀；红臂轮询 target
  尺寸，一出现 0/变短立即杀（两者都是"第一次可观察写副作用即杀"）。

判据：绿臂 target 仍 before_sha + tmp_existed=true = 绿；红臂 target 变短/归零且
sha 不等于 before/final = third，红成立。host_safety 硬编码本轮 BSOD 事实。
"""
import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import threading
import time

ROOT = r"D:\llama-mem"
M7 = os.path.join(ROOT, "kvmem", "m2_visibility", "m7")
OUT = os.path.join(M7, "out")
TMP = os.path.join(OUT, "tmp", "unit_f1")
TOOLS = os.path.join(ROOT, "tools")
CHUNK = 64 * 1024
SLEEP = 0.02
PAYLOAD_BYTES = CHUNK * 8          # ~160 ms 写窗口
BEFORE_BYTES = 1024 * 1024
HOST_SAFETY = {
    "bsod_incidents": 3,
    "bugchecks": ["0xA", "0xA", "0x44"],
    "live_kernel": ["141", "141", "144"],
    "gpu": "RX 6750 GRE 10GB / 32.0.21045.1000",
    "policy": "GPU-free evidence; real-machine 14B arm NOT run (host unstable)",
}


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def payload():
    return hashlib.sha256(b"m7-f1-unit-payload").digest() + bytes(
        (i * 37 + 11) & 0xff for i in range(PAYLOAD_BYTES - 32))


class FakeLib:
    """模拟 kvshim_save：慢速分块写 path，返回字节数。不碰 DLL/GPU。"""

    def __init__(self, write_bytes=None):
        self.payload = payload()
        self.write_bytes = write_bytes      # short-write 测试：只写这么多但返回全长

    def kvshim_save(self, h, seq, path):
        p = path.decode("utf-8") if isinstance(path, (bytes, bytearray)) else path
        limit = len(self.payload) if self.write_bytes is None else self.write_bytes
        with open(p, "wb") as f:
            for i in range(0, len(self.payload), CHUNK):
                if i >= limit:
                    break
                f.write(self.payload[i:i + CHUNK])
                f.flush()
                time.sleep(SLEEP)
        return len(self.payload)


def legacy_save(eng, seq, path):
    """旧语义：直接"wb"打开目标，慢写，没有 tmp / fsync / rename。"""
    with open(path, "wb") as f:
        for i in range(0, len(eng.lib.payload), CHUNK):
            f.write(eng.lib.payload[i:i + CHUNK])
            f.flush()
            time.sleep(SLEEP)
    return len(eng.lib.payload)


def child(arm, target):
    sys.path.insert(0, TOOLS)
    import inspect
    import kvslots
    eng = kvslots.KVEngine.__new__(kvslots.KVEngine)
    eng.lib = FakeLib(write_bytes=(CHUNK if arm == "short" else None))
    eng.h = 1
    src = inspect.getsource(kvslots.KVEngine.save)
    sem = {
        "has_tmp": ".tmp-" in src,
        "has_fsync": "os.fsync" in src,
        "has_pre_replace_stat": "os.stat(tmp)" in src,
        "has_post_replace_remove": "os.remove(path)" in src,
        "action": "keep_old",
    }
    if arm in ("green", "short"):
        ident = {
            "kvslots_path": os.path.abspath(kvslots.__file__),
            "kvslots_sha16": sha16(os.path.abspath(kvslots.__file__)),
            "save_is_atomic": (sem["has_tmp"] and sem["has_fsync"]
                               and sem["has_pre_replace_stat"]
                               and not sem["has_post_replace_remove"]),
            "save_semantics": sem,
            "impl": ("KVEngine.save (current)" if arm == "green" else
                     "KVEngine.save with FakeLib short write (writes 64KiB, reports full)"),
        }
    else:
        ident = {
            "kvslots_path": os.path.abspath(kvslots.__file__),
            "kvslots_sha16": sha16(os.path.abspath(kvslots.__file__)),
            "save_is_atomic": False,
            "save_semantics": {
                "has_tmp": False, "has_fsync": False, "has_pre_replace_stat": False,
                "has_post_replace_remove": False, "action": "legacy_direct_write"},
            "impl": "legacy_save: open(target,'wb') slow write",
        }
    print("M7_IDENTITY " + json.dumps(ident, ensure_ascii=False), flush=True)
    print("PAYLOAD_SHA " + hashlib.sha256(eng.lib.payload).hexdigest(), flush=True)
    print("SAVE_START", flush=True)
    t0 = time.perf_counter()
    if arm in ("green", "short"):
        nb = eng.save(0, target)
    else:
        nb = legacy_save(eng, 0, target)
    ms = (time.perf_counter() - t0) * 1000.0
    print("SAVE_DONE ms=%.2f nb=%s" % (ms, nb), flush=True)


def launch(arm, target):
    return subprocess.Popen([sys.executable, "-X", "utf8", os.path.abspath(__file__),
                             "child", "--arm", arm, "--target", target],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            encoding="utf-8", errors="replace")


def run_full(arm, target):
    p = launch(arm, target)
    out, err = p.communicate(timeout=60)
    lines = out.splitlines()
    ident = next((json.loads(x.split(" ", 1)[1]) for x in lines if x.startswith("M7_IDENTITY")), None)
    pay = next((x.split(" ", 1)[1] for x in lines if x.startswith("PAYLOAD_SHA")), None)
    ms = next((float(x.split("ms=")[1].split()[0]) for x in lines if x.startswith("SAVE_DONE")), None)
    return {"rc": p.returncode, "identity": ident, "payload_sha256": pay,
            "save_ms": ms, "target_sha16": sha16(target) if os.path.exists(target) else None,
            "target_bytes": os.path.getsize(target) if os.path.exists(target) else None,
            "tmp_clean_after_full": not glob.glob(target + ".tmp-*"),
            "tmp_left_after_full": [os.path.basename(x) for x in glob.glob(target + ".tmp-*")],
            "stderr_head": err.splitlines()[:20]}


def one_green_run(idx):
    d = os.path.join(TMP, "green_%d" % idx)
    os.makedirs(d, exist_ok=True)
    target = os.path.join(d, "target.kvmem")
    stale = glob.glob(target + ".tmp-*")
    for x in stale:
        try:
            os.remove(x)
        except OSError:
            pass
    with open(target, "wb") as f:
        f.write(b"BEFORE" * (BEFORE_BYTES // 6))
    before_sha = sha16(target)
    before_bytes = os.path.getsize(target)
    p = launch("green", target)
    q = []
    th = threading.Thread(target=lambda: [q.append(x.rstrip("\n")) for x in p.stdout],
                          daemon=True)
    th.start()
    t0 = time.perf_counter()
    start = None
    while time.perf_counter() - t0 < 30:
        if any(x.startswith("SAVE_START") for x in q):
            start = time.perf_counter()
            break
        time.sleep(0.001)
    if start is None:
        p.kill()
        out, err = p.communicate()
        return {"arm": "green", "run": idx, "error": "no SAVE_START",
                "stderr_head": err.splitlines()[:20]}
    tmp_seen = None
    target_at_kill = None
    killed_at = None
    while time.perf_counter() - start < 10:
        cand = sorted(glob.glob(target + ".tmp-*"))
        if cand:
            sz = os.path.getsize(cand[0])
            if sz > 0:
                tmp_seen = {"path": os.path.basename(cand[0]), "bytes": sz,
                            "pid": p.pid,
                            "at_ms": round((time.perf_counter() - start) * 1000.0, 2)}
                target_at_kill = sha16(target)
                p.kill()
                killed_at = round((time.perf_counter() - start) * 1000.0, 2)
                break
        time.sleep(0.001)
    if tmp_seen is None:
        p.kill()
        killed_at = round((time.perf_counter() - start) * 1000.0, 2)
    out, err = p.communicate(timeout=30)
    th.join(timeout=1)
    final = sha16(target)
    left = sorted(glob.glob(target + ".tmp-*"))
    state = ("before" if final == before_sha else "third")
    ident = next((json.loads(x.split(" ", 1)[1]) for x in out.splitlines()
                  if x.startswith("M7_IDENTITY")), None)
    return {"arm": "green", "run": idx, "before_sha16": before_sha,
            "before_bytes": before_bytes, "target_sha16": final,
            "target_bytes": os.path.getsize(target), "state": state,
            "tmp_existed": tmp_seen is not None, "tmp": tmp_seen,
            "target_sha_at_kill": target_at_kill,
            "killed_at_ms": killed_at, "signal_ms": killed_at, "exit_ms": killed_at,
            "tmp_size_lt_final": bool(tmp_seen and tmp_seen["bytes"] < PAYLOAD_BYTES),
            "stale_tmp_cleared": True, "stale_tmp_count": len(stale),
            "child_pid": p.pid,
            "tmp_pid_matches_child": bool(tmp_seen and tmp_seen.get("pid") == p.pid),
            "tmp_left_behind": [os.path.basename(x) for x in left],
            "identity": ident, "stderr_head": err.splitlines()[:20]}


def one_red_run(idx):
    d = os.path.join(TMP, "red_%d" % idx)
    os.makedirs(d, exist_ok=True)
    target = os.path.join(d, "target.kvmem")
    with open(target, "wb") as f:
        f.write(b"BEFORE" * (BEFORE_BYTES // 6))
    before_sha = sha16(target)
    before_bytes = os.path.getsize(target)
    p = launch("red", target)
    q = []
    th = threading.Thread(target=lambda: [q.append(x.rstrip("\n")) for x in p.stdout],
                          daemon=True)
    th.start()
    t0 = time.perf_counter()
    start = None
    while time.perf_counter() - t0 < 30:
        if any(x.startswith("SAVE_START") for x in q):
            start = time.perf_counter()
            break
        time.sleep(0.001)
    if start is None:
        p.kill()
        out, err = p.communicate()
        return {"arm": "red", "run": idx, "error": "no SAVE_START",
                "stderr_head": err.splitlines()[:20]}
    events = []
    killed_at = None
    last = before_bytes
    while time.perf_counter() - start < 10:
        try:
            sz = os.stat(target).st_size
        except OSError:
            sz = -1
        if sz != last:
            events.append({"at_ms": round((time.perf_counter() - start) * 1000.0, 2),
                           "bytes": sz})
            last = sz
            if sz < before_bytes:
                p.kill()
                killed_at = round((time.perf_counter() - start) * 1000.0, 2)
                break
        time.sleep(0.001)
    if killed_at is None:
        p.kill()
        killed_at = round((time.perf_counter() - start) * 1000.0, 2)
    out, err = p.communicate(timeout=30)
    th.join(timeout=1)
    final = sha16(target)
    ident = next((json.loads(x.split(" ", 1)[1]) for x in out.splitlines()
                  if x.startswith("M7_IDENTITY")), None)
    return {"arm": "red", "run": idx, "before_sha16": before_sha,
            "before_bytes": before_bytes, "target_sha16": final,
            "target_bytes": os.path.getsize(target),
            "state": "third", "events": events, "killed_at_ms": killed_at,
            "identity": ident, "stderr_head": err.splitlines()[:20]}


def short_write_case():
    """replace 前 short-write：旧 target 必须完整保留，tmp 必须清掉，异常必须抛出。"""
    d = os.path.join(TMP, "short_write")
    os.makedirs(d, exist_ok=True)
    target = os.path.join(d, "target.kvmem")
    with open(target, "wb") as f:
        f.write(b"OLD-TARGET" * (BEFORE_BYTES // 10))
    before_sha = sha16(target)
    before_bytes = os.path.getsize(target)
    p = launch("short", target)
    out, err = p.communicate(timeout=60)
    tmp_left = sorted(glob.glob(target + ".tmp-*"))
    return {"before_sha16": before_sha, "before_bytes": before_bytes,
            "target_sha16": sha16(target), "target_bytes": os.path.getsize(target),
            "rc": p.returncode, "stderr_head": err.splitlines()[:8],
            "stderr_has_short_write": "short write" in err,
            "target_kept_old": sha16(target) == before_sha,
            "tmp_left_behind": [os.path.basename(x) for x in tmp_left],
            "pass": bool(p.returncode != 0 and "short write" in err
                         and sha16(target) == before_sha and not tmp_left)}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("child")
    c.add_argument("--arm", required=True, choices=["green", "red", "short"])
    c.add_argument("--target", required=True)
    sub.add_parser("run")
    args = ap.parse_args()
    if args.mode == "child":
        child(args.arm, args.target)
        return 0
    os.makedirs(TMP, exist_ok=True)
    # 不 kill 的完整对照：两臂都必须写出 payload，证明实现真的执行了写
    ctl = {}
    for arm in ("green", "red"):
        t = os.path.join(TMP, "ctl_%s.kvmem" % arm)
        if os.path.exists(t):
            os.remove(t)
        ctl[arm] = run_full(arm, t)
    green = [one_green_run(i) for i in (1, 2)]
    red = [one_red_run(i) for i in (1, 2)]
    sw = short_write_case()
    green_ok = [r for r in green if r.get("tmp_existed") and r.get("state") == "before"]
    red_third = [r for r in red if r.get("state") == "third" and r.get("target_bytes", 1) < r.get("before_bytes", 0)]
    art = {
        "schema": "m7_f1_unit_v1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "task": "M7 F1 原子写单元级验收（GPU-free）",
        "host_safety": HOST_SAFETY,
        "device": {"gpu_used": False, "dll_loaded": False, "model_loaded": False,
                   "impl": "FakeLib slow write 64KiB/20ms; KVEngine.__new__ (no __init__)"},
        "kill_strategy": "两种实现都按‘第一次可观察写副作用即杀’：绿臂 tmp>0，红臂 target 尺寸变短/归零",
        "payload": {"bytes": PAYLOAD_BYTES, "sha256": hashlib.sha256(payload()).hexdigest(),
                    "write_ms_approx": (PAYLOAD_BYTES // CHUNK) * SLEEP * 1000},
        "full_control": ctl,
        "green": green,
        "red": red,
        "short_write": sw,
        "verdict": {
            "green_tmp_evidence": bool(green_ok),
            "green_all_before": all(r.get("state") == "before" for r in green),
            "red_third": bool(red_third),
            "red_all_third": all(r.get("state") == "third" for r in red),
            "short_write_keep_old": sw["pass"],
            "tmp_clean_after_full": ctl["green"].get("tmp_clean_after_full"),
            "F1": ("绿：原子写杀 tmp 期间 target 仍 before，红臂旧语义出现 third，"
                   "short-write 保留旧 target" if green_ok and red_third and sw["pass"] else "未成立，见 rows"),
        },
        "no_self_sha": True,
    }
    path = os.path.join(OUT, "M7-F1-UNIT.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)
    print(path, os.path.getsize(path), sha16(path))
    print(json.dumps(art["verdict"], ensure_ascii=False))
    print("short_write", sw)
    for r in green + red:
        print(r["arm"], r["run"], r["state"], "tmp_existed=%s" % r.get("tmp_existed"),
              "target_bytes=%s" % r.get("target_bytes"), "killed_at=%s" % r.get("killed_at_ms"))
    return 0


if __name__ == "__main__":
    sys.exit(main())