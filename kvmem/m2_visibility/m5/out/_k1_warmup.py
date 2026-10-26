# -*- coding: utf-8 -*-
"""K1 amended-gate preflight + exactly 3 warm-up runs.  NO model, NO L1.

Uses the frozen unarmed child fixture (no kill in warm-up; a run over 10 s is
stopped and recorded as abnormal).  Parent only polls state; no kill is sent on
a normal warm-up.  The formal 100-run arm and TerminateProcess point are not
started here.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "kvmem/m2_visibility/m5/out"
M7 = ROOT / "kvmem/m2_visibility/m7"
sys.path.insert(0, str(M7 / "out"))
import _e3gpu_run as E  # noqa: E402

CHILD = OUT / "_k1_park_child.py"
PARENT = OUT / "_k1_park_parent.py"
RECOVERY = OUT / "_k1_recovery.py"
MANIFEST = OUT / "_k1_fixture_manifest.json"
BEFORE = OUT / "M5-KILL-before.kvmem"
ART = OUT / "M5-K1-WARMUP.json"
BASE_BOOT = "2026-10-26T03:24:52.5000000+08:00"
BASE_DUMPS = 5
VRAM_MAX = 1.5
PEAK_MAX = 8.6
WARMUPS = 3
RUN_TIMEOUT_S = 10.0


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def info(p):
    q = Path(p)
    if not q.exists():
        return None
    return {"path": str(q), "sha16": sha16(q), "bytes": q.stat().st_size}


def ntokens(p):
    b = open(p, "rb").read(12)
    return int.from_bytes(b[8:12], "little")


def write_json_atomic(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(p) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def fixture_check():
    expected = {
        "child": {"sha16": "9339107866cbc84c", "bytes": 24243},
        "parent": {"sha16": "7ac8cef82a1bbff3", "bytes": 20254},
        "recovery": {"sha16": "52f33f17e10ee7ca", "bytes": 7029},
        "manifest": {"sha16": "d2d6ab0b6f806e15", "bytes": 594},
    }
    files = {"child": info(CHILD), "parent": info(PARENT),
             "recovery": info(RECOVERY), "manifest": info(MANIFEST)}
    match = {k: bool(files[k] and files[k]["sha16"] == v["sha16"] and files[k]["bytes"] == v["bytes"])
             for k, v in expected.items()}
    m = json.load(open(MANIFEST, encoding="utf-8"))
    man_parent = ((m.get("files") or {}).get("parent") or {})
    return {"expected": expected, "observed": files, "match": match,
            "all_match": all(match.values()),
            "manifest_parent": man_parent,
            "manifest_parent_consistent": man_parent.get("sha16") == files["parent"]["sha16"] and
                                          man_parent.get("bytes") == files["parent"]["bytes"]}


def gate_check(tag):
    g = E.gate_values()
    h = E.host_check(tag)
    parsed = h.get("parsed") or {}
    reasons = []
    if g.get("boot_id") != BASE_BOOT:
        reasons.append("boot_id mismatch")
    if (g.get("free_ram_kb") or 0) < 8388608:
        reasons.append("free_ram_kb < 8388608")
    if g.get("gpu_procs_gt256mb") != 0:
        reasons.append("gpu_procs_gt256mb != 0")
    if parsed.get("existing_count") != BASE_DUMPS:
        reasons.append("minidump count != %d" % BASE_DUMPS)
    if g.get("vram_baseline_gib") is None or g["vram_baseline_gib"] > VRAM_MAX:
        reasons.append("vram_baseline > %.1f GiB" % VRAM_MAX)
    return {"tag": tag, "values": g, "minidump_count": parsed.get("existing_count"),
            "minidump_latest": parsed.get("latest_mtime"),
            "browser_present": bool((g.get("browser_or_code_procs") or 0) > 0),
            "browser_or_code_procs_recorded": g.get("browser_or_code_procs"),
            "gate_ok": len(reasons) == 0, "fail_reasons": reasons,
            "host_check_parsed": parsed}


def start_sampler(tag):
    flag = OUT / ("_k1_warmup_stop_%s.flag" % tag)
    peak = OUT / ("_k1_warmup_peak_%s.txt" % tag)
    for x in (flag, peak):
        try:
            x.unlink()
        except FileNotFoundError:
            pass
    p = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                          "-File", str(E.SAMPLER), "-Flag", str(flag), "-Out", str(peak)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
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


def parse_states(path):
    out = []
    try:
        for line in open(path, encoding="utf-8"):
            if line.startswith("[STATE "):
                out.append(line.rstrip("\n"))
    except FileNotFoundError:
        pass
    return out


def one_warmup(n):
    target = OUT / "kill_k1" / ("warmup-%d" % n) / "target.kvmem"
    state = OUT / ("kill_state_warmup_%03d.log" % n)
    result = OUT / ("_k1_warmup_result_%03d.json" % n)
    for p in (state, result):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    if target.parent.exists():
        shutil.rmtree(target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    peak_s = start_sampler("w%d" % n)
    t0 = time.perf_counter()
    p = subprocess.Popen([sys.executable, str(CHILD), "--run", str(n), "--source", str(BEFORE),
                          "--target", str(target), "--state-log", str(state), "--result", str(result)],
                         cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    timed_out = False
    signals = 0
    while p.poll() is None:
        if time.perf_counter() - t0 > RUN_TIMEOUT_S:
            timed_out = True
            break
        time.sleep(0.005)
    if timed_out:
        signals += 1
        try:
            p.kill()  # TerminateProcess: only to stop an over-10s warm-up
        except Exception:  # noqa: BLE001
            pass
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    else:
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            timed_out = True
    elapsed = round(time.perf_counter() - t0, 3)
    peak = stop_sampler(peak_s)
    try:
        so, se = p.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        so, se = "", ""
    res = json.load(open(result, encoding="utf-8")) if result.exists() else None
    target_info = info(target)
    tmp = sorted([q.name for q in target.parent.glob("target.kvmem.tmp*")])
    target_ok = False
    third = None
    if target.exists():
        tsha = sha16(target)
        ntk = ntokens(target)
        third = tsha != sha16(BEFORE)
        target_ok = (tsha == sha16(BEFORE)) and ntk == 50 and not tmp
    return {"n": n, "elapsed_s": elapsed, "timed_out_gt10": timed_out,
            "returncode": p.returncode, "signals_sent": signals,
            "state_log": {"path": str(state), "sha16": sha16(state) if state.exists() else None,
                          "bytes": state.stat().st_size if state.exists() else None},
            "states": parse_states(state), "child_result": res,
            "target": target_info, "target_n_tokens": ntokens(target) if target.exists() else None,
            "target_third": third, "target_ok": target_ok, "tmp_remaining": tmp,
            "peak_gib": peak, "model_loaded": False,
            "armed": True, "warmup_no_kill": True,
            "stdout_tail": (so or "")[-8000:], "stderr_tail": (se or "")[-8000:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-warmups", action="store_true")
    a = ap.parse_args()
    art = {
        "schema": "m5_k1_warmup_v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "prereg": {"path": str(ROOT / "docs/_work/PREREG-KILL-ARM-v2.md"),
                   "sha16": sha16(ROOT / "docs/_work/PREREG-KILL-ARM-v2.md"),
                   "bytes": (ROOT / "docs/_work/PREREG-KILL-ARM-v2.md").stat().st_size},
        "armed": True, "arm_scope": "K1 only",
        "armed_authorized_by": "user 2026-10-26T12:24+08:00",
        "kill_attempts": 0, "signals_sent": 0,
        "model_loaded": False, "warmup": True,
        "fixture_correction": {
            "old": "854fbe3dcd93ace5/17,535 (pre-fix, unused)",
            "new": "7ac8cef82a1bbff3/20,254",
            "reason": "Logger.st fix added pre/post sha assertions; manifest d2d6 self-consistent with 7ac8"
        },
        "gate_amended": True,
        "gate_amendment": {
            "kept": ["boot_id = 2026-10-26T03:24:52.5+08:00", "free_ram_kb >= 8388608",
                     "gpu_procs_gt256mb = 0", "minidump count = 5 and no new dump"],
            "relaxed": {"vram_baseline_gib": "<= 1.5", "browser_or_code_procs": "not gated, recorded every run"},
            "final_load_strict": "gpu_procs_gt256mb=0 + vram_baseline<=1.5 + peak<=8.6 GiB; browser_present recorded",
            "reason": "K1 does not load model; browser is the control channel; third/peak criteria unaffected",
            "amended_by": "lead 2026-10-26T12:2x+08:00; authorized by user arm grant 12:24"
        },
        "fixtures": fixture_check(),
        "warmups": [], "status": "running", "gate": {}, "warmup_times_s": []
    }
    if not art["fixtures"]["all_match"] or not art["fixtures"]["manifest_parent_consistent"]:
        art["status"] = "未接上（夹具不符合裁定 A）"
        write_json_atomic(ART, art)
        print("K1_WARMUP " + json.dumps({"status": art["status"], "fixtures": art["fixtures"]}, ensure_ascii=False))
        return 1
    pre = gate_check("warmup_pre")
    art["gate"]["pre"] = pre
    if not pre["gate_ok"]:
        art["status"] = "未接上（修订门未过）"
        write_json_atomic(ART, art)
        print("K1_WARMUP " + json.dumps({"status": art["status"], "gate": pre}, ensure_ascii=False))
        return 1
    if not a.run_warmups:
        art["status"] = "preflight_only"
        write_json_atomic(ART, art)
        print("K1_WARMUP " + json.dumps({"status": art["status"]}, ensure_ascii=False))
        return 0
    stop = False
    for n in range(1, WARMUPS + 1):
        r = one_warmup(n)
        art["warmups"].append(r)
        art["warmup_times_s"].append(r["elapsed_s"])
        art["signals_sent"] += r["signals_sent"]
        print("K1_WARMUP_RUN %d elapsed=%.3f timeout=%s rc=%s target_ok=%s peak=%s signals=%d" % (
            n, r["elapsed_s"], r["timed_out_gt10"], r["returncode"], r["target_ok"],
            r.get("peak_gib"), r["signals_sent"]), flush=True)
        if r["timed_out_gt10"] or r["elapsed_s"] > RUN_TIMEOUT_S:
            stop = True
            break
        if not r["target_ok"] or (r["peak_gib"] is not None and r["peak_gib"] > PEAK_MAX):
            stop = True
            break
    art["gate"]["after"] = gate_check("warmup_after")
    if not art["gate"]["after"]["gate_ok"]:
        stop = True
    art["status"] = "warmup_ok" if (not stop and len(art["warmups"]) == WARMUPS) else "stopped"
    art["stop_reason"] = None if art["status"] == "warmup_ok" else (
        "warm-up >10 s or target/peak abnormal; stopped before L1")
    art["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    write_json_atomic(ART, art)
    print("K1_WARMUP " + json.dumps({"status": art["status"], "times": art["warmup_times_s"],
                                     "signals_sent": art["signals_sent"],
                                     "gate_after": art["gate"]["after"]["gate_ok"],
                                     "artifact": info(ART)}, ensure_ascii=False))
    return 0 if art["status"] == "warmup_ok" else 1


if __name__ == "__main__":
    sys.exit(main())