# -*- coding: utf-8 -*-
"""M6a 可达性红证：生成 `m6/out/M6A-REACHABILITY.json` + `chat_lease/LANDED-m6a.json`。

本脚本只**汇总**已发生的读数（探针产物 + 读码/日志证据），不跑引擎、不改引擎、不写已签目录。
四态口径：可达（未修）/ 不可达（未接上）/ 判据不成立（作废）/ 未做；
人造路径只作旁证，不进四态。
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime

ROOT = r"D:\llama-mem"
M6 = os.path.join(ROOT, "kvmem", "m2_visibility", "m6")
OUT = os.path.join(M6, "out")
PROBE = os.path.join(OUT, "M6A-PROBE.json")
PRODUCT = os.path.join(OUT, "M6A-REACHABILITY.json")
LEDGER = os.path.join(ROOT, "kvmem", "m2_visibility", "chat_lease", "LANDED-m6a.json")
TOOLS = os.path.join(ROOT, "tools")
PY = sys.executable
REPO_DB = os.path.join(ROOT, "kvmem", "chat.db")
MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
SPEC = os.path.join(ROOT, "docs", "_work", "M2-FULL-S1-SPEC-lead.md")
FROZEN = {"analysis.py": os.path.join(TOOLS, "analysis.py"),
          "retrieval.py": os.path.join(TOOLS, "retrieval.py"),
          "evidence.py": os.path.join(TOOLS, "evidence.py")}
BLOCKS = {k: os.path.join(ROOT, "kvmem", "blocks", k + ".kvmem")
          for k in ("profile", "project")}


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def ent(p):
    return {"path": os.path.relpath(p, ROOT).replace("\\", "/"),
            "sha16": sha16(p), "bytes": os.path.getsize(p)}


def cpp_numstat():
    r = subprocess.run(["git", "-C", os.path.join(ROOT, "llama.cpp"), "diff", "--numstat"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ins = dels = 0
    for ln in r.stdout.splitlines():
        f = ln.split("\t")
        if len(f) >= 2:
            ins += int(f[0])
            dels += int(f[1])
    return {"insertions": ins, "deletions": dels, "files": len(r.stdout.splitlines())}


# ---- 调用点判定表（file:line -> 语义）。行号取自现盘 grep；判定靠表达式与其构造。 ----
POS = "delta 恒正（块按 0..n-1 保存/载入，目标在 4096 以下不远处）"
SYM = "成对 ±：先 +后 -，位置不会 <0 ⇒ 不下溢"
NEGSAFE = "可为负但目标 >=0 ⇒ 不下溢"
ARB = "任意整数（工具臂 CLI），可为负且可下溢 ⇒ 只有工具臂能造出 I1"


def cs(file, line, expr, may_neg, underflow, note, live=True, kind="repos_local"):
    return {"file": file, "line": line, "call": kind, "expr": expr,
            "may_be_negative": may_neg, "underflow_possible": underflow,
            "note": note, "live": live}


CALL_SITES = [
    # product paths (chat.py)
    cs("tools/chat.py", 286, "eng.repos_local(i, delta), delta = target - base", False, False,
       "cmd_chat 装载路径；" + POS + "；base=pos_max-n+1=0（memory_source.py:347 在 0 编码）"),
    cs("tools/chat.py", 352, "eng.repos_local(1, +64)", False, False, "cmd_chat 自检：" + SYM),
    cs("tools/chat.py", 353, "eng.repos_local(1, -64)", True, False, "cmd_chat 自检：" + SYM),
    cs("tools/chat.py", 394, "eng.repos_local(i, lo - base)", False, False,
       "_place_slots；base=0，lo=end-n>=4096-128-n>0 ⇒ 恒正"),
    cs("tools/chat.py", 637, "eng.repos_local(seq, lo - base)", False, False,
       "cmd_m1 挂载前移动；reset+load 后 base=0，lo>0 ⇒ 恒正；attach 在 :640（移动之后）"),
    cs("tools/chat.py", 1021, "engine.repos_local(seq, base - cur)", False, False,
       "cmd_m1 循环挂载；cur=pos_max+1-n=0，base>0 ⇒ 恒正"),
    cs("tools/chat.py", 847, "self._eng.repos_local(seq, delta)", None, None,
       "GuardedLeases 转发层：delta 由调用方给（上方 4 个 product 调用均为正）"),
    # other product-ish paths
    cs("tools/session_state.py", 362, "eng.repos_local(seq, b[\"start\"] - base)", False, False,
       "恢复路径；start>0、base=0 ⇒ 恒正"),
    cs("kvmem/m2_visibility/m4/m4_write.py", 207,
       "eng.repos_local(BLOCK_SEQ, ASK_ANCHOR - moved - base)", False, False,
       "泄漏/隔离臂的装载移动；base=pos_max-n+1=0，目标 ASK_ANCHOR>0 ⇒ 恒正（工具臂）"),
    cs("kvmem/m2_visibility/m4/m4_write.py", 232,
       "eng.repos_local(BLOCK_SEQ, POS0 - (ASK_ANCHOR - moved))", True, False,
       NEGSAFE + "（目标 POS0=0，回拉不越界）"),
    cs("tools/m2_v1.py", 205, "eng.repos_local(6, 2600 - t0)", True, False,
       "t0=3000 ⇒ -400；目标 2600 仍 >0 ⇒ 不下溢（工具臂，非 product）"),
    cs("tools/m2_v1.py", 109, "eng.repos_local(slot, target - base)", False, False, POS),
    cs("tools/m2_v1.py", 198, "eng.repos_local(6, t0 - (pos_max-n+1))", False, False, POS),
    cs("tools/m2_v1.py", 204, "eng.repos_local(6, t0 - (pos_max-n+1))", False, False, POS),
    cs("tools/m2_v1.py", 208, "eng.repos_local(6, t0 - (pos_max-n+1))", False, False, POS),
    cs("tools/m2_visibility_probe.py", 452, "eng.repos_local(slot, target - base)", False, False, POS),
    cs("tools/m2_probe_cells.py", 63, "eng.repos_local(i, tgt - (pos_max-n+1))", False, False, POS),
    cs("tools/m2_probe_segments.py", 46, "eng.repos_local(slot, tgt - (pos_max-n+1))", False, False, POS),
    cs("tools/m2_probe_segments.py", 91, "eng.repos_local(3, tgt - (pos_max-n+1))", False, False, POS),
    cs("tools/hole_matrix.py", 80, "eng.repos_local(seq, target - base)", False, False, POS),
    cs("tools/hole_probe.py", 40, "eng.repos_local(seq, target - base)", False, False, POS),
    cs("tools/states_demo.py", 61, "eng.repos_local(seq, lo - base)", False, False, POS),
    cs("tools/variance_check.py", 73, "eng.repos_local(i, lo - base)", False, False, POS),
    cs("tools/p0_1a_check.py", 81, "eng.repos_local(SCRATCH, +64)", False, False, "自检 +64"),
    cs("tools/p0_1a_check.py", 143, "eng.repos_local(SCRATCH, target)", False, False, POS),
    cs("tools/p0_2_check.py", 125, "eng.repos_local(SCRATCH, +64)", False, False, "自检 +64"),
    cs("tools/p0_2_check.py", 139, "eng.repos_local(i, lo - base)", False, False, POS),
    cs("tools/p0_4b_right.py", 74, "eng.repos_local(seq, target - base)", False, False, POS),
    cs("tools/diag_place.py", 50, "eng.repos_local(1, t1)", False, False, POS),
    cs("tools/diag_place.py", 68, "eng.repos_local(1, +t1)", False, False, "自检 +t1"),
    cs("tools/diag_place.py", 69, "eng.repos_local(1, -t1)", True, False, "自检 -t1：" + SYM),
    cs("tools/diag_place.py", 111, "eng.repos_local(1, t1)", False, False, POS),
    cs("tools/diag_place.py", 120, "eng.repos_local(1, t1)", False, False, POS),
    cs("tools/diag_place.py", 126, "eng.repos_local(2, t2)", False, False, POS),
    cs("tools/diag_place.py", 149, "eng.repos_local(1, (CHAT - 50) - 0)", False, False, POS),
    cs("tools/diag_place.py", 167, "eng.repos_local(1, t1)", False, False, POS),
    cs("tools/diag_place.py", 168, "eng.repos_local(2, t2)", False, False, POS),
    cs("tools/kv_audit.py", 111, "eng.repos_local(1, +a.step)", False, False, "自检 +step"),
    cs("tools/kv_audit.py", 112, "eng.repos_local(1, -a.step)", True, False, "自检 -step：" + SYM),
    cs("tools/kv_audit.py", 131, "eng.repos_local(1, CHAT - n)", False, False, POS),
    cs("tools/kv_audit.py", 163, "eng.repos_local(1, CHAT - n)", False, False, POS),
    cs("tools/kvdrift.py", 114, "eng.repos_local(blk, args.shift)", True, True,
       ARB + "（--shift 默认 +1000，可传负值）"),
    cs("tools/kvdrift.py", 133, "eng.repos_local(blk, args.shift)", True, True, ARB),
    cs("kvmem/m2_visibility/chat_lease/bridge_probe.py", 35,
       "eng.repos_local(i, lo - base)", False, False, POS),
    cs("kvmem/m2_visibility/chat_lease/refusal_probe.py", 32,
       "eng.repos_local(BLOCK_SEQ, lo - base)", False, False, POS),
    cs("kvmem/m2_visibility/m14b_e10_probe/insert_localize.py", 63,
       "eng.repos_local(P.LIVE, +N, P.CHAT, chat_hi)", False, False, "自检 +N"),
    cs("kvmem/m2_visibility/m14b_e10_probe/insert_localize.py", 69,
       "eng.repos_local(7, P.CHAT - (pos_max-n+1))", False, False, POS),
    cs("kvmem/m2_visibility/m14b_e10_probe/insert_probe.py", 75,
       "eng.repos_local(P.LIVE, +n_new, P.CHAT, chat_hi)", False, False, "自检 +n_new"),
    cs("kvmem/m2_visibility/m14b_e10_probe/insert_probe.py", 80,
       "eng.repos_local(7, P.CHAT - base0)", False, False, POS),
    cs("kvmem/m2_visibility/m14b_e10_probe/insert_probe2.py", 56,
       "eng.repos_local(P.LIVE, +N, P.CHAT, chat_hi)", False, False, "自检 +N"),
    cs("kvmem/m2_visibility/m14b_e10_probe/insert_probe2.py", 60,
       "eng.repos_local(7, P.CHAT - (pos_max-n+1))", False, False, POS),
    cs("kvmem/m2_visibility/m14b_e10_probe/insert_probe3.py", 159,
       "eng.repos_local(7, P.CHAT - (pos_max-n+1))", False, False, POS),
    cs("kvmem/m2_visibility/m6/_probe_m6a.py", 110,
       "eng.repos_local(1, +100 / -1000 / -50)", True, True,
       "本单只读探针：-1000 造下溢（旁证）；不进 I1 四态", live=True),
]

# --- I2 的共享/attach 调用点 ---
SHARE_SITES = [
    cs("tools/chat.py", 834, "GuardedLeases.share -> self._eng.share(*a, **kw)", None, None,
       "share = seq_cp：同 stream 只加 cell 引用（kvslots.py:240；kvshim seq_cp）", kind="share"),
    cs("tools/chat.py", 640, "leases.attach(seq, 0, lo, end, site=\"m1.attach\")", None, None,
       "m1 挂载：移动（:637）在 attach（:640）之前 ⇒ 移动时该块还没有第二个 referrer",
       kind="attach"),
    cs("tools/chat.py", 1027, "leases.attach(seq, dst, base, pos_hi)", None, None,
       "S1 cmd_chat 挂载：repos_local（:1021）在 attach 之前 ⇒ 同一顺序", kind="attach"),
    cs("tools/chat_lease.py", 339, "def attach(block_seq, dst_seq, lo, hi)", None, None,
       "GuardedLeases.attach：登记共享区间并调 share", kind="attach"),
    cs("tools/kvslots.py", 240, "def share(src, dst, p0, p1) -> kvshim_seq_cp", None, None,
       "共享机制本体：只加引用、不加 tokens、无 refcount", kind="share"),
]

# --- I3 的 pos_add / seq_add 调用点 ---
POS_ADD_SITES = [
    cs("llama.cpp/src/llama-kv-cache.cpp", 927, "seq_add(): cells.pos_add(i, shift)",
       None, None, "seq_add 是 pending whole-tensor K-shift 的唯一入口（置 shift[]/has_shift）",
       kind="pos_add"),
    cs("llama.cpp/src/llama-kv-cache.cpp", 553,
       "seq_cp() 跨 stream 分支: v_cells[s1].pos_add(i, shift)", None, None,
       "只在 n_stream>1（非 unified）可达；现盘 kv_unified=true ⇒ n_stream=1 ⇒ 该分支不可达",
       kind="pos_add"),
    cs("tools/kvdrift.py", 135, "eng.repos(blk, args.shift) (= seq_add)", None, None,
       "工具臂：唯一走 seq_add 的 python 调用点（--local 之外）", kind="seq_add"),
    cs("tools/diag_place.py", 82, "eng.repos(1, t1) (= seq_add)", None, None,
       "工具臂：seq_add + 随后的 flush decode（专门测 pending shift）", kind="seq_add"),
    cs("tools/kvslots.py", 518, "eng.repos(s_mov, BASE) (= seq_add) demo", None, None,
       "kvslots 自演示（模块 __main__）", kind="seq_add"),
]


def main():
    probe = json.load(open(PROBE, encoding="utf-8"))
    st = {s["step"][0]: s for s in probe["steps"]}

    numstat = cpp_numstat()
    freeze = subprocess.run([PY, "-X", "utf8", os.path.join(TOOLS, "freeze_check.py")],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    verify = subprocess.run(["bash", os.path.join(ROOT, "verify.sh")],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    gitstat = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    m6_new = [l for l in gitstat.stdout.splitlines() if "m2_visibility/m6" in l]

    product = {
        "schema": "m6a_reachability_v1",
        "task": "task-37 M6a：引擎四条不变量可达性红证（只判不修）",
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "spec": ent(SPEC),
        "probe": ent(PROBE),
        "geometry": probe["geometry_from_log"],
        "items": [
            {
                "id": "I1",
                "claim": "负 delta 使 pos_move 在 pos[i]<0 时 seq[i].reset()+used.erase(i)，"
                         "静默回收 cell（含其它 seq 的引用），而 seq_repos_local 仍返回 moved=N",
                "call_sites": CALL_SITES,
                "construction": {
                    "static_proof": [
                        "块由 tools/memory_source.py:347 `eng.write_at(seq, text, 0)` 在位置 0 编码，"
                        "save 保留 0..n-1；DB memory_block.n_tokens=50/36 且 product loads "
                        "pos_max_after=49/35 是同一事实的产物侧读数",
                        "product 装载路径先 reset+load（base=pos_max+1-n=0），再把块移到目标："
                        "chat.py:286/394/637/1021 的 delta = target - base = target > 0；"
                        "S1 目标 [4075,4096)/[4650,4668)，m1 目标 = CHAT_START-i*SLOT-n，均 >0",
                        "唯一可能为负的 product 式子是 m4_write.py:231 / m2_v1.py:205 的"
                        "回拉，但目标 >=0 ⇒ 不下溢；kvdrift.py:114/133 的 args.shift 是工具臂 CLI",
                    ],
                    "probe_artifact": "M6A-PROBE.json steps D（旁证：-1000 ⇒ seq1/seq2 cells 都变 0，"
                                      "返回仍 50，tokens[] 仍 50）",
                },
                "observed": st["D"]["exhibit"],
                "four_state": "未接上",
                "why_unreachable": "product 路径没有负 delta：块恒按 0..n-1 保存（memory_source.py:347），"
                                   "装载后 base=0，所有目标 >0 ⇒ delta>0；负 delta 只出现在自测工具臂"
                                   "（kvdrift --shift / diag_place 对称回拉），且工具臂的负值也不下溢",
                "future_risk": "若将来出现'保存位置高于目标'的块文件（手工 .kvmem / 换编码基线），"
                               "product 路径会第一次传负 delta ⇒ 静默回收",
                "evidence": ["tools/memory_source.py:347", "tools/chat.py:241",
                             "tools/chat.py:286", "tools/chat.py:394", "tools/chat.py:637",
                             "tools/chat.py:1021", "llama.cpp/src/llama-kv-cells.h:481-501"],
                "can_run_now": True,
            },
            {
                "id": "I2",
                "claim": "seq_cp 同 stream 只加 cell 引用（无 refcount）；块挂给对话后 cell 属于两个 seq，"
                         "任一方 repos_local 会改掉另一方看到的位置语义",
                "call_sites": SHARE_SITES,
                "construction": {
                    "probe": "M6A-PROBE.json steps A-C：load(profile->seq1) 50 cells @[0,49] → "
                             "share(1->2) seq2 也是 50 cells（tokens[] 仍 0，必须看 raw cells）→ "
                             "repos_local(1,+100) 后 seq1/seq2 都是 [100,149]",
                },
                "observed": {"share": st["B"]["exhibit"], "move": st["C"]["exhibit"]},
                "four_state": "可达（未修）",
                "s1_status": "S1 未触发：S1 是 home→A、project→B 两块互不共享；且两处都是"
                             "先 repos_local 后 attach（chat.py:637→640、:1021→1027），"
                             "移动时没有第二个 referrer",
                "real_concurrency_failure": "真并发（同一块同时挂两个对话）时，一方 move 会让另一方的"
                                            "位置窗口静默平移：attach 记账仍是旧区间、K 在旧位置被旋转，"
                                            "生成不会报错，只是喂错位置的记忆（最坏：读到别的 token）",
                "evidence": ["tools/kvslots.py:240", "tools/chat_lease.py:339",
                             "tools/chat.py:834", "llama.cpp/src/llama-kv-cache.cpp:505-511",
                             "kvmem/m2_visibility/m6/out/M6A-PROBE.json"],
                "can_run_now": True,
            },
            {
                "id": "I3",
                "claim": "pos_add 置 shift[]/has_shift，pos_move 不置也不清；若同一批 cell 先 add 后 move，"
                         "残留 pending shift 会在下一次 decode 再旋转一次（二次旋转）",
                "call_sites": POS_ADD_SITES,
                "construction": {
                    "static_only": True,
                    "argument": [
                        "engine 里 pos_add 只有两处：seq_add（cpp:927）与 seq_cp 的跨 stream 分支（cpp:553）",
                        "现盘 kv_unified=true（tools/kvshim.cpp:162）⇒ n_stream=1"
                        "（llama-kv-cache.cpp:86/137）⇒ 跨 stream 分支不可达；同 stream seq_cp 走 "
                        "cells.seq_add(i,dst)（cpp:511），不碰 pos_add",
                        "python 侧唯一走 seq_add 的调用点是工具臂 kvdrift.py:135 / diag_place.py:82 "
                        "（及 kvslots 自演示:518）；product 路径（chat.py 4 处）只用 repos_local",
                        "因此现盘不存在'先 pos_add 后 pos_move 同一批 cell'的路径："
                        "product 在同一进程里从不调用 seq_add",
                    ],
                },
                "observed": None,
                "four_state": "未接上",
                "why_unreachable": "product 只用 seq_repos_local（自转 K、不记 shift）；seq_add 只在"
                                   "工具臂出现，且工具臂不随后调用 repos_local 同一批 cell",
                "evidence": ["llama.cpp/src/llama-kv-cells.h:448-501",
                             "llama.cpp/src/llama-kv-cache.cpp:86", ":137", ":511", ":553", ":927",
                             "tools/kvshim.cpp:162", "tools/chat.py:286/394/637/1021"],
                "can_run_now": False,
            },
            {
                "id": "I4",
                "claim": "seq_repos_local 的 preflight 只查 n_rot_k!=0 && n_rot!=n_embd_head_k，"
                         "不查 n_rot（fwht 传入的尺寸）是否 2 的幂；llama_kv_fwht 里 GGML_ASSERT "
                         "会 abort 进程",
                "call_sites": [
                    cs("llama.cpp/src/llama-kv-cache.cpp", 622,
                       "GGML_ASSERT(n>0 && (n&(n-1))==0) in llama_kv_fwht", None, None,
                       "n 为 hparams.n_rot(il)（:860/:868 调用点），非 n_rot_k", kind="assert"),
                    cs("llama.cpp/src/llama-kv-cache.cpp", 778,
                       "preflight: n_rot_k!=0 && n_rot!=n_embd_head_k ⇒ return 0", None, None,
                       "只拒绝 partial-rotary，不检查 n_rot 的幂次", kind="preflight"),
                    cs("llama.cpp/src/llama-kv-cache.cpp", 346,
                       "n_rot_k=64; while(n_embd_head_k_all%(2*n_rot_k)==0) n_rot_k*=2", None, None,
                       "n_rot_k 恒为 2 的幂；但 fwht 用的是 n_rot（可能 != n_rot_k）", kind="calc"),
                ],
                "construction": {
                    "observed_14b": {"n_rot": 128, "n_embd_head_k": 128, "n_rot_k": 128,
                                     "n_embd_head_k_all": 128, "kv_type": "q8_0",
                                     "log": "kvmem/m2_visibility/runs_m14b/loadC_ngl99_v.log:78,82,1560"},
                    "pow2": True,
                    "verdict": "128=2^7 ⇒ fwht(128) 安全；14B 不触发（未接上）",
                },
                "observed": None,
                "four_state": "未接上",
                "why_unreachable": "14B Qwen 的 n_rot=n_embd_head_k=128 且是 2 的幂；preflight 的"
                                   "n_rot==n_embd_head_k 条件成立 ⇒ 不 abort",
                "future_risk_models": "head_dim 是 64 的倍数但不是 2 的幂且 K 量化：192/320/384/448 "
                                      "（attn_rot_k 成立、n_rot_k 停在 64、use_hadamard=true、"
                                      "fwht(n_rot=192/…) 触发 GGML_ASSERT）；partial-rotary"
                                      "（n_rot != head_dim）反而被 preflight 安全拒绝",
                "evidence": ["kvmem/m2_visibility/runs_m14b/loadC_ngl99_v.log:78", ":82", ":1560",
                             ":1561", "llama.cpp/src/llama-kv-cache.cpp:622", ":778", ":346-352",
                             ":860", ":868"],
                "can_run_now": False,
            },
        ],
        "four_state_table": {"I1": "未接上", "I2": "可达（未修）",
                             "I3": "未接上", "I4": "未接上"},
        "discipline": {
            "engine_changed": False,
            "rebuild": False,
            "signed_dirs_written": False,
            "llama_cpp_numstat_after": numstat,
            "frozen_three_sha16": {k: sha16(v) for k, v in FROZEN.items()},
            "repo_db_sha16": sha16(REPO_DB),
            "blocks": {k: ent(v) for k, v in BLOCKS.items()},
            "model": {"path": MODEL, "bytes": os.path.getsize(MODEL)},
        },
        "stop_conditions_checked": {
            "needed_engine_change_or_rebuild": False,
            "wrote_14b_readings_to_signed_dir": False,
            "I1_reachable_and_S1_hit": False,
        },
        "no_self_sha": True,
    }
    os.makedirs(OUT, exist_ok=True)
    with open(PRODUCT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(product, fh, ensure_ascii=False, indent=1)

    ledger = {
        "schema": "landed_m6a_v1",
        "task": "task-37 M6a 可达性红证（只判不修）",
        "at": product["at"],
        "product": ent(PRODUCT),
        "probe": ent(PROBE),
        "scripts": {"_probe_m6a.py": ent(os.path.join(M6, "_probe_m6a.py")),
                    "_build_m6a.py": ent(os.path.abspath(__file__))},
        "code_change": {"changed": False,
                        "note": "不改 llama.cpp / 不 rebuild / 不动冻结三件；只新增 m6 目录下的"
                                "只读探针与汇总脚本"},
        "four_state": product["four_state_table"],
        "per_item_evidence": {i["id"]: i["evidence"] for i in product["items"]},
        "discipline": product["discipline"],
        "stop_conditions_checked": product["stop_conditions_checked"],
        "regressions": {
            "freeze_check": {"exit": freeze.returncode,
                             "first_line": (freeze.stdout.strip().splitlines() or [""])[0],
                             "status": "FROZEN" if "FROZEN" in freeze.stdout else "RED"},
            "verify_sh": {"exit": verify.returncode,
                          "last_line": (verify.stdout.strip().splitlines() or [""])[-1]},
            "git_status_m6_entries": m6_new,
        },
        "gaps": {
            "I2_no_product_run": "I2 只有探针（两 seq 共享后 move）与静态顺序论证；真并发臂未跑"
                                 "（要新块/新挂载组合，属 M6a-fix 后的回归臂）",
            "I1_probe_is_artificial": "探针的 -1000 是旁证，不进 I1 四态；I1 判 未接上",
        },
        "no_self_sha": True,
    }
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1)
    print("product: %s (%d B, sha16=%s)" % (PRODUCT, os.path.getsize(PRODUCT), sha16(PRODUCT)))
    print("ledger:  %s (%d B, sha16=%s)" % (LEDGER, os.path.getsize(LEDGER), sha16(LEDGER)))
    print("four_state:", json.dumps(product["four_state_table"], ensure_ascii=False))
    print("freeze:", ledger["regressions"]["freeze_check"]["status"],
          "| verify:", ledger["regressions"]["verify_sh"])
    return 0


if __name__ == "__main__":
    sys.exit(main())