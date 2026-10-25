# -*- coding: utf-8 -*-
"""M6a 只读探针：共享 cell 移动语义（I2）+ 负 delta 静默回收 cell（I1 旁证）。

**只读**：不改 llama.cpp、不 rebuild、不写任何已签产物目录；只加载 repo 现成的 14B 块
（DB `memory_block` 指向的 `kvmem/blocks/profile.kvmem` 50 tok / `project.kvmem` 36 tok），
调用现成 kvshim ABI，读数落 `kvmem/m2_visibility/m6/out/`。

关键口径：`kvshim_pos_max`/`n_tokens` 都看 `tokens[seq]` 向量，而 `seq_cp`（share）只加 cell
引用、不加 tokens ⇒ 共享方必须用 raw accessors（`kvshim_seq_pos_max_raw` /
`kvshim_seq_cell_scan`）才看得到；否则会把"共享成功"误读成 0 个 cell。

构造（公开 API，无引擎改动）：
  A. load(profile -> seq1)                 块按 0..n-1 落位
  B. share(seq1 -> seq2)                   seq_cp 同 stream 只加引用（无 refcount）
  C. repos_local(seq1, +100)               只移动一方，看另一方 position 区间是否跟着变（I2）
  D. repos_local(seq1, -1000)              位置下溢 ⇒ pos_move 里 seq[i].reset()+used.erase(i)；
                                           看 seq2 的 cells 是否一起丢、返回值是否仍报 N（I1 旁证）
  E. load -> +50 -> share -> -50           负 delta 不下溢：证明"负 delta 本身"不是问题，
                                           只有下溢才回收（给 I1 的边界）

用法： PY -X utf8 _probe_m6a.py [--model ...] [--out ...]
"""
import argparse
import ctypes
import hashlib
import json
import os
import sys
from datetime import datetime

ROOT = r"D:\llama-mem"
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from kvslots import KVEngine  # noqa: E402

BLOCKS = {"profile": os.path.join(ROOT, "kvmem", "blocks", "profile.kvmem"),
          "project": os.path.join(ROOT, "kvmem", "blocks", "project.kvmem")}
DB_EXPECTED_TOKENS = {"profile": 50, "project": 36}
DEFAULT_MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
DEFAULT_OUT = os.path.join(ROOT, "kvmem", "m2_visibility", "m6", "out", "M6A-PROBE.json")


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    eng = KVEngine(args.model, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    L = eng.lib
    vp, ci, cp = ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)
    L.kvshim_seq_pos_max_raw.argtypes = [vp, ci]
    L.kvshim_seq_pos_max_raw.restype = ci
    L.kvshim_seq_cell_scan.argtypes = [vp, ci, ci, cp, ci]
    L.kvshim_seq_cell_scan.restype = ci
    PROBE = 7  # scratch seq used by cell_scan (never used by this probe otherwise)

    def cells(seq, cap=256):
        buf = (ctypes.c_int * cap)()
        n = int(L.kvshim_seq_cell_scan(eng.h, int(seq), PROBE, buf, cap))
        return {"n_cells": n, "positions": [int(buf[i]) for i in range(max(0, min(n, cap)))]}

    steps = []
    try:
        def exhibit(seqs=(1, 2)):
            out = {}
            for s in seqs:
                out[str(s)] = {
                    "n_tokens": int(eng.n_tokens(s)),              # tokens[] 向量（load 才有）
                    "pos_max_raw": int(L.kvshim_seq_pos_max_raw(eng.h, int(s))),
                }
                c = cells(s)
                out[str(s)]["n_cells"] = c["n_cells"]
                out[str(s)]["pos_range"] = ([c["positions"][0], c["positions"][-1]]
                                            if c["n_cells"] else [])
            return out

        def step(tag, **kw):
            rec = {"step": tag, "exhibit": exhibit()}
            rec.update(kw)
            steps.append(rec)
            print("[%-30s] seq1=%s seq2=%s %s"
                  % (tag, rec["exhibit"]["1"], rec["exhibit"]["2"],
                     {k: v for k, v in kw.items() if k != "note"}))
            return rec

        # A. 块按 0..n-1 载入 seq1
        n_prof = int(eng.load(1, BLOCKS["profile"]))
        rec_a = step("A load(profile->seq1)", ret=n_prof,
                     note="块文件按 0..n-1 落位（DB memory_block.n_tokens=%d）；"
                          "这就是 product 路径 delta 恒正的来源" % DB_EXPECTED_TOKENS["profile"])

        # B. seq_cp 共享 cells（同 stream，只加 seq 引用）
        eng.share(1, 2)
        rec_b = step("B share(seq1->seq2)", note="seq_cp：cell 同属 seq1/seq2，无 refcount；"
                                                 "tokens[] 不变 ⇒ 必须看 raw cells 才看得见")

        # C. 移动 seq1：seq2 的 position 区间应一起变（I2）
        moved_pos = int(eng.repos_local(1, +100))
        rec_c = step("C repos_local(seq1,+100)", ret=moved_pos,
                     note="I2：只移动 seq1，seq2 的 cells 位置区间跟着 +100")

        # D. 负 delta 下溢：seq2 的引用被一起释放，但返回仍报 N（I1 旁证）
        moved_neg = int(eng.repos_local(1, -1000))
        rec_d = step("D repos_local(seq1,-1000)", ret=moved_neg,
                     note="I1 旁证：下溢 ⇒ pos_move 里 seq[i].reset()+used.erase(i)；"
                          "返回值仍=idx 数（不报失败），tokens[] 也仍 50（双重静默）")

        # E. 负 delta 不越界：安全
        eng.load(1, BLOCKS["profile"])
        m1 = int(eng.repos_local(1, +50))
        eng.share(1, 2)
        m2 = int(eng.repos_local(1, -50))
        rec_e = step("E load,+50,share,-50", ret={"plus50": m1, "minus50": m2},
                     note="负 delta 但不下溢 ⇒ 位置回到 0..49，seq2 仍在；边界=位置不得 <0")

        e = rec_e["exhibit"]
        c = rec_c["exhibit"]
        d = rec_d["exhibit"]
        out = {
            "schema": "m6a_probe_v1",
            "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "engine": {
                "model": args.model,
                "model_bytes": os.path.getsize(args.model),
                "n_ctx": 8192, "n_seq": 8, "gpu": 99, "kv": "q8_0",
                "unified": "kvshim.cpp:162 cp.kv_unified = true（单 pool，seq_cp 共享）",
            },
            "blocks": {k: {"path": os.path.relpath(v, ROOT).replace("\\", "/"),
                           "sha16": sha16(v), "bytes": os.path.getsize(v),
                           "db_n_tokens": DB_EXPECTED_TOKENS[k]}
                       for k, v in BLOCKS.items()},
            "geometry_from_log": {
                "log": "kvmem/m2_visibility/runs_m14b/loadC_ngl99_v.log",
                "lines": {"n_rot": 78, "n_embd_head_k": 82,
                          "n_rot_k": 1560, "n_embd_head_k_all": 1560},
                "values": {"n_rot": 128, "n_embd_head_k": 128,
                           "n_rot_k": 128, "n_embd_head_k_all": 128, "kv_type": "q8_0"},
            },
            "steps": steps,
            "conclusions": {
                "load_matches_db": rec_a["ret"] == DB_EXPECTED_TOKENS["profile"],
                "share_adds_cells_not_tokens": (rec_b["exhibit"]["2"]["n_cells"] == 50
                                                and rec_b["exhibit"]["2"]["n_tokens"] == 0),
                "I2_shared_move_observed": (c["1"]["pos_max_raw"] == 149
                                            and c["2"]["pos_max_raw"] == 149
                                            and c["2"]["n_cells"] == 50),
                "I1_underflow_observed": (d["1"]["n_cells"] == 0 and d["2"]["n_cells"] == 0),
                "I1_other_seq_refs_lost_together": d["2"]["n_cells"] == 0,
                "I1_return_still_reports_cells": moved_neg == n_prof,
                "I1_tokens_vector_unchanged": d["1"]["n_tokens"] == n_prof,
                "safe_negative_no_underflow": (e["1"]["pos_range"] == [0, 49]
                                                and e["2"]["n_cells"] == 50),
                "artificial_note": "本探针是'若这样用会怎样'的旁证：负 delta 由脚本直接传，"
                                   "product 路径（S1/m1）当前不会传负值；不进 I1 四态判定",
            },
            "no_engine_change": True,
            "no_signed_dir_write": True,
            "no_self_sha": True,
        }
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        print("probe: %s (%d B, sha16=%s)" % (args.out, os.path.getsize(args.out),
                                              sha16(args.out)))
        print("conclusions:", json.dumps(out["conclusions"], ensure_ascii=False))
    finally:
        eng.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())