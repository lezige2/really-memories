# -*- coding: utf-8 -*-
"""M6a-fix I2：红 / 绿 / 变体三臂（同一构造，只换臂名与守卫开关）。

构造（全程我们层：GuardedLeases 记账 + 引擎公开 API；不改引擎、不 rebuild）：
  1. `load(profile -> seq3)`  ⇒ 块 50 cells @[0,49]
  2. `leases.attach(3, 0, 0, 50)`  ⇒ 块挂对话 A(seq0)，holders={0}
  3. `leases.attach(3, 7, 0, 50)`  ⇒ 同一块再挂对话 B(seq7)，holders={0,7}（I2 的真实形态）
  4. `eng.repos_local(3, +100)`    ⇒ 移动被两个 seq 引用的块 cells

臂：
  red      改前（或守卫关掉）：静默移动 —— seq0/seq7 的位置区间都变 [100,149]（无报错）
  green    改后：守卫拒绝 —— `refused=true` + reason 带 seq/区间/referrers/块名 + 两个 seq 区间不变
  variant  改后 + `M3_LEASE_MOVE_GUARD=0`（守卫条件恒 False 的等价缝）：必须回到红（静默移动）

产物只落 `kvmem/m2_visibility/m6/out/`；事件日志目录也设到 `m6/out/_logs`（不写仓库
`kvmem/lease_logs/`）。DATABASE 不碰。

用法： PY -X utf8 _run_m6a_i2.py --arm red --out out/M6A-I2-RED.json
"""
import argparse
import ctypes
import hashlib
import json
import os
import sys
import traceback
from datetime import datetime

ROOT = r"D:\llama-mem"
TOOLS = os.path.join(ROOT, "tools")
M3 = os.path.join(ROOT, "kvmem", "m2_visibility", "m3")
M6 = os.path.join(ROOT, "kvmem", "m2_visibility", "m6")
for p in (TOOLS, M3):
    if p not in sys.path:
        sys.path.insert(0, p)

# 事件日志别落进仓库 kvmem/lease_logs/：本单只许写 m6/
os.environ.setdefault("CHAT_LEASE_LOG_DIR", os.path.join(M6, "out", "_logs", "lease"))

import chat as C                     # noqa: E402
from chat_lease import GuardedLeases  # noqa: E402
from m3_lease import LeaseError       # noqa: E402

BLOCK = os.path.join(ROOT, "kvmem", "blocks", "profile.kvmem")
BLOCK_SEQ, DST_A, DST_B = 3, 0, 7
DELTA = +100
DEFAULT_OUT = {
    "red": os.path.join(M6, "out", "M6A-I2-RED.json"),
    "green": os.path.join(M6, "out", "M6A-I2-GREEN.json"),
    "variant": os.path.join(M6, "out", "M6A-I2-VARIANT.json"),
}


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(DEFAULT_OUT))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out_path = args.out or DEFAULT_OUT[args.arm]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    eng = C.KVEngine(C.MODEL, n_ctx=C.N_CTX, n_seq=C.N_SEQ, gpu=99, kv="q8_0")
    L = eng.lib
    vp, ci, cp = ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)
    L.kvshim_seq_pos_max_raw.argtypes = [vp, ci]
    L.kvshim_seq_pos_max_raw.restype = ci
    L.kvshim_seq_cell_scan.argtypes = [vp, ci, ci, cp, ci]
    L.kvshim_seq_cell_scan.restype = ci
    PROBE = 6

    def cells(seq, cap=256):
        buf = (ctypes.c_int * cap)()
        n = int(L.kvshim_seq_cell_scan(eng.h, int(seq), PROBE, buf, cap))
        pos = sorted(int(buf[i]) for i in range(max(n, 0)))
        return {"n_cells": n, "pos_range": [pos[0], pos[-1]] if pos else [],
                "pos_max_raw": int(L.kvshim_seq_pos_max_raw(eng.h, int(seq)))}

    def snapshot():
        return {"seq0": cells(0), "seq7": cells(7),
                "block_seq3": cells(BLOCK_SEQ),
                "n_tokens_block_seq3": int(eng.n_tokens(BLOCK_SEQ))}

    steps = []
    result = {"schema": "m6a_i2_arm_v1", "arm": args.arm,
              "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
              "engine": {"model": C.MODEL, "n_ctx": C.N_CTX, "n_seq": C.N_SEQ,
                         "kv": "q8_0", "dll_sha16": sha16(os.path.join(TOOLS, "kvshim_vk.dll"))},
              "block": {"path": os.path.relpath(BLOCK, ROOT).replace("\\", "/"),
                        "sha16": sha16(BLOCK), "bytes": os.path.getsize(BLOCK),
                        "block_seq": BLOCK_SEQ, "dst": [DST_A, DST_B]},
              "code_sha16": {"m3_lease.py": sha16(os.path.join(M3, "m3_lease.py")),
                             "chat.py": sha16(os.path.join(TOOLS, "chat.py")),
                             "chat_lease.py": sha16(os.path.join(TOOLS, "chat_lease.py"))},
              "guard_env": {"M3_LEASE_MOVE_GUARD": os.environ.get("M3_LEASE_MOVE_GUARD", "1")},
              "steps": steps}
    leases = None
    try:
        leases = GuardedLeases(eng, site_prefix="m6a_i2")
        n = int(eng.load(BLOCK_SEQ, BLOCK))
        steps.append({"step": "load(profile->seq3)", "ret": n, "after": snapshot()})
        leases.register_block(BLOCK_SEQ, "profile")
        leases.attach(BLOCK_SEQ, DST_A, 0, n)
        steps.append({"step": "attach(seq3->seq0,[0,%d))" % n, "after": snapshot()})
        leases.attach(BLOCK_SEQ, DST_B, 0, n)
        steps.append({"step": "attach(seq3->seq7,[0,%d))" % n, "after": snapshot(),
                      "holders": leases.referrers(BLOCK_SEQ)})

        before = snapshot()
        refused, exc = False, None
        moved = None
        try:
            moved = int(eng.repos_local(BLOCK_SEQ, DELTA))
        except LeaseError as e:                              # 改后：可见拒绝
            refused = True
            exc = {"type": type(e).__name__, "msg": str(e),
                   "traceback_tail": traceback.format_exc().splitlines()[-1]}
        after = snapshot()
        refusals = list(getattr(leases, "move_refusals", []))
        rec = {"step": "repos_local(seq3,%+d)" % DELTA,
               "before": before, "after": after,
               "refused": refused, "moved": moved, "exception": exc,
               "move_refusals": refusals,
               "guard_disabled_reads": list(getattr(leases, "guard_disabled_reads", [])),
               "table_status": leases.status()}
        steps.append(rec)

        unchanged = (before["seq0"] == after["seq0"] and before["seq7"] == after["seq7"])
        still_shared = (after["seq0"]["n_cells"] == n and after["seq7"]["n_cells"] == n
                        and leases.referrers(BLOCK_SEQ) == [DST_A, DST_B])
        rec_shape = {
            "silent_move": (not refused and moved == n
                            and after["seq0"]["pos_range"] == [DELTA, DELTA + n - 1]
                            and after["seq7"]["pos_range"] == [DELTA, DELTA + n - 1]),
            "refused_with_reason": (refused and exc is not None
                                    and all(k in exc["msg"] for k in
                                           ("seq 3", "referrer", "profile"))
                                    and bool(refusals)),
            "both_unchanged": unchanged and still_shared,
        }
        expect = {"red": "silent_move", "variant": "silent_move",
                  "green": "refused_with_reason"}[args.arm]
        ok = bool(rec_shape[expect]) and (rec_shape["both_unchanged"] if args.arm == "green"
                                          else True)
        result["outcome"] = {"refused": refused, "moved": moved, "exception": exc,
                             "before": before, "after": after,
                             "move_refusals": refusals,
                             "rec_shape": rec_shape,
                             "expected_shape": expect, "pass": ok}
        result["event_log"] = _event_info()
    finally:
        if leases is not None:
            try:
                result["event_log"] = _event_info()
            except Exception:                               # noqa: BLE001
                result["event_log"] = None
        eng.close()

    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print("arm=%s out=%s sha16=%s bytes=%d pass=%s"
          % (args.arm, out_path, sha16(out_path), os.path.getsize(out_path),
             result.get("outcome", {}).get("pass")))
    print("rec_shape:", json.dumps(result.get("outcome", {}).get("rec_shape"), ensure_ascii=False))
    return 0 if result.get("outcome", {}).get("pass") else 3


def _event_info():
    try:
        from chat_lease import run_log
        return run_log()
    except Exception:                                       # noqa: BLE001
        return None


if __name__ == "__main__":
    sys.exit(main())