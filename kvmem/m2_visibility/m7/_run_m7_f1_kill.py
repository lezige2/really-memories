# -*- coding: utf-8 -*-
"""M7 F1 验收：时间点 kill，证明原子写之后 target 只可能是 before 或 final。

- child 模式：加载模型、写一段文本、打印 SAVE_START，然后调用 KVEngine.save(target)。
  `--old` 用改造前副本（m7/_before/kvslots.py@71498ea35f9d7cb4）做红对照。
- kill 模式：先测完整 save 的 t_save，再在 0.2t/0.5t/0.9t/1.5t 杀；每档都记录
  目标文件观察尺寸/sha 切换时刻。判据：final sha ∈ {before_sha, final_sha}；
  第三态 = 红。0.9 档若落在 replace 后，用 0.5 档补并记实际 replace 时刻。
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
import time

if os.environ.get("KV_ACCEPT_GPU_KILL_RISK") != "1":
    sys.exit("[disabled] GPU kill experiments caused 3 BSODs on this host (0xA/0x44, live-kernel 141/144). "
             "Use _run_m7_f1_unit.py. Set KV_ACCEPT_GPU_KILL_RISK=1 only with explicit user consent.")

ROOT = r"D:\llama-mem"
M7 = os.path.join(ROOT, "kvmem", "m2_visibility", "m7")
OUT = os.path.join(M7, "out")
TMP = os.path.join(OUT, "tmp")
TOOLS = os.path.join(ROOT, "tools")
OLD = os.path.join(M7, "_before", "kvslots.py@71498ea35f9d7cb4")
DLL = os.path.join(TOOLS, "kvshim_vk.dll")
M14 = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
M7B = r"D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
BASE = {"chat": os.path.join(ROOT, "kvmem", "sessions", "live.chat.kvmem"),
        "block": os.path.join(ROOT, "kvmem", "blocks", "profile.kvmem")}
MODEL = {"chat": M7B, "block": M14}
SEQ = {"chat": 0, "block": 1}
TEXT = ("M7 F1 atomic-save kill test. The quick brown fox jumps over the lazy dog. "
        "Memory state must never be left truncated. ") * 6


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def child(arm, target, old):
    sys.path.insert(0, TOOLS)
    if old:
        from importlib.machinery import SourceFileLoader
        mod = SourceFileLoader("kvslots_old", OLD).load_module()
        eng = mod.KVEngine(MODEL[arm], n_ctx=8192, n_seq=8, gpu=99, kv="q8_0", dll=DLL)
    else:
        import kvslots
        eng = kvslots.KVEngine(MODEL[arm], n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    try:
        seq = SEQ[arm]
        eng.reset(seq)
        eng.write_at(seq, TEXT, 0)
        print("SAVE_START", flush=True)
        t0 = time.perf_counter()
        nb = eng.save(seq, target)
        ms = (time.perf_counter() - t0) * 1000.0
        print("SAVE_DONE ms=%.2f nb=%s" % (ms, nb), flush=True)
    finally:
        eng.close()


def run_child(arm, target, old=False, timeout=180):
    cmd = [sys.executable, "-X", "utf8", os.path.abspath(__file__), "child",
           "--arm", arm, "--target", target]
    if old:
        cmd.append("--old")
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace")


def measure(arm):
    os.makedirs(TMP, exist_ok=True)
    target = os.path.join(TMP, "measure_%s.kvmem" % arm)
    if os.path.exists(target):
        os.remove(target)
    p = run_child(arm, target, old=old)
    out, err = p.communicate(timeout=300)
    if p.returncode != 0:
        raise RuntimeError("measure child rc=%s err=%s" % (p.returncode, err[-1000:]))
    ms = None
    for ln in out.splitlines():
        if ln.startswith("SAVE_DONE"):
            ms = float(ln.split("ms=")[1].split()[0])
    if ms is None:
        raise RuntimeError("no SAVE_DONE: %r" % out[-500:])
    return {"t_save_ms": ms, "final_sha16": sha16(target), "final_bytes": os.path.getsize(target),
            "target": target}


def one_kill(arm, frac, t_save_ms, before_sha, final_sha, old=False):
    d = os.path.join(TMP, "kill_%s_%s" % (arm, str(frac).replace(".", "p")))
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d, exist_ok=True)
    target = os.path.join(d, "target.kvmem")
    shutil.copyfile(BASE[arm], target)
    before_size = os.path.getsize(target)
    assert sha16(target) == before_sha
    p = run_child(arm, target)
    lines = []
    q = []

    def reader():
        for ln in p.stdout:
            q.append(ln.rstrip("\n"))
    th = threading.Thread(target=reader, daemon=True)
    th.start()
    t0 = time.perf_counter()
    start = None
    while time.perf_counter() - t0 < 180:
        if any(x.startswith("SAVE_START") for x in q):
            start = time.perf_counter()
            break
        if p.poll() is not None:
            break
        time.sleep(0.002)
    if start is None:
        p.kill()
        raise RuntimeError("never saw SAVE_START for %s %s: %r" % (arm, frac, q[-5:]))
    deadline = start + frac * (t_save_ms / 1000.0)
    events = []
    last_size = os.path.getsize(target)
    last_sha = sha16(target)
    events.append({"ms": 0.0, "bytes": last_size, "sha16": last_sha})
    killed = False
    while True:
        now = time.perf_counter()
        if now >= deadline:
            break
        try:
            sz = os.stat(target).st_size
        except OSError:
            sz = -1
        if sz != last_size:
            s = sha16(target) if sz >= 0 else None
            events.append({"ms": round((time.perf_counter() - start) * 1000.0, 2),
                           "bytes": sz, "sha16": s})
            last_size, last_sha = sz, s
        time.sleep(0.002)
    if frac < 1.5:
        p.kill()
        killed = True
    try:
        rest, err = p.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        p.kill()
        rest, err = p.communicate()
    th.join(timeout=1)
    final = sha16(target)
    final_size = os.path.getsize(target)
    if not events or events[-1]["sha16"] != final:
        events.append({"ms": round((time.perf_counter() - start) * 1000.0, 2),
                       "bytes": final_size, "sha16": final})
    replace_ms = None
    for e in events:
        if e["sha16"] not in (before_sha, final_sha):
            replace_ms = e["ms"]
            break
        if e["sha16"] == final_sha:
            replace_ms = e["ms"]
            break
    state = ("before" if final == before_sha else
             ("final" if final == final_sha else "third"))
    return {"arm": arm, "frac": frac, "t_save_ms": round(t_save_ms, 2),
            "killed": killed, "killed_at_ms": round((time.perf_counter() - start) * 1000.0, 2),
            "target_bytes": final_size, "target_sha16": final,
            "state": state, "before_sha16": before_sha, "final_sha16": final_sha,
            "observed_replace_ms": replace_ms,
            "observed": events, "child_rc": p.returncode}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("child")
    c.add_argument("--arm", required=True, choices=["chat", "block"])
    c.add_argument("--target", required=True)
    c.add_argument("--old", action="store_true")
    k = sub.add_parser("kill")
    k.add_argument("--arm", required=True, choices=["chat", "block"])
    k.add_argument("--fractions", default="0.2,0.5,0.9,1.5")
    k.add_argument("--old", action="store_true")
    args = ap.parse_args()
    os.makedirs(TMP, exist_ok=True)
    if args.mode == "child":
        child(args.arm, args.target, args.old)
        return 0

    old = args.old
    arm = args.arm
    fracs = [float(x) for x in args.fractions.split(",")]
    m = measure(arm) if not old else None
    if old:
        # 红对照也要一个 t_save 基准（旧代码直接写 target）
        base_t = os.path.join(TMP, "measure_old_%s.kvmem" % arm)
        if os.path.exists(base_t):
            os.remove(base_t)
        p = run_child(arm, base_t, old=True)
        out, err = p.communicate(timeout=300)
        assert p.returncode == 0, err[-500:]
        t = float([x for x in out.splitlines() if x.startswith("SAVE_DONE")][0].split("ms=")[1].split()[0])
        m = {"t_save_ms": t, "final_sha16": sha16(base_t),
             "final_bytes": os.path.getsize(base_t), "target": base_t}
    before_sha = sha16(BASE[arm])
    runs = [one_kill(arm, f, m["t_save_ms"], before_sha, m["final_sha16"], old=old) for f in fracs]
    bad = [r for r in runs if r["state"] == "third"]
    art = {"schema": "m7_f1_kill_v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "arm": arm, "old_code": old,
           "t_save_ms": round(m["t_save_ms"], 2),
           "before_sha16": before_sha, "final_sha16": m["final_sha16"],
           "before_bytes": os.path.getsize(BASE[arm]), "final_bytes": m["final_bytes"],
           "runs": runs,
           "third_state_count": len(bad),
           "verdict": "红（第三态）" if bad else
                      ("绿（全部 before/final；0.9 若 after 另看 replace 时刻）")}
    path = os.path.join(OUT, "M7-F1-KILL-%s%s.json" % (arm, "-RED" if old else ""))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)
    print(path, os.path.getsize(path), sha16(path))
    for r in runs:
        print(arm, r["frac"], r["state"], "t=%s" % r["t_save_ms"],
              "replace_ms=%s" % r["observed_replace_ms"])
    print("third", len(bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())