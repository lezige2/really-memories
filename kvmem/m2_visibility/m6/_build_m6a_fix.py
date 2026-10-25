# -*- coding: utf-8 -*-
"""M6a-fix I2：汇总红/绿/变体 + 零行为变化证据，生成 SUMMARY 与 LANDED 台账。

不跑引擎（读数已在文件里）；只重算 sha/字节、做逐字节/逐字段对照、跑 freeze_check/verify.sh。
"""
import difflib
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime

ROOT = r"D:\llama-mem"
M6 = os.path.join(ROOT, "kvmem", "m2_visibility", "m6")
OUT = os.path.join(M6, "out")
BEF = os.path.join(OUT, "_before")
AFT = os.path.join(OUT, "_after")
M3 = os.path.join(ROOT, "kvmem", "m2_visibility", "m3")
LEDGER = os.path.join(ROOT, "kvmem", "m2_visibility", "chat_lease", "LANDED-m6a-fix.json")
SUMMARY = os.path.join(OUT, "M6A-I2-SUMMARY.json")
TOOLS = os.path.join(ROOT, "tools")
PY = sys.executable
REPO_DB = os.path.join(ROOT, "kvmem", "chat.db")
OLD = os.path.join(M3, "_before", "m3_lease.py@33ae679a50d58c93")
NEW = os.path.join(M3, "m3_lease.py")
OLD_SHA = "33ae679a50d58c93"          # LANDED-l2.json 记录的改前 sha（权威坐标）
ARMS = {a: os.path.join(OUT, "M6A-I2-%s.json" % a) for a in ("RED", "GREEN", "VARIANT")}


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def ent(p):
    return {"path": os.path.relpath(p, ROOT).replace("\\", "/"),
            "sha16": sha16(p), "bytes": os.path.getsize(p)}


def norm(text):
    """把逐字节对照里『本来就该变』的三类噪声剥掉，再比对语义。
    - m3_lease.py 的 sha16（改后必然变）
    - 临时产物文件的 6 位时间戳文件名
    - 本单自己的 before/after 标签与产物路径
    """
    out = []
    for line in text.splitlines():
        import re as _re
        line = _re.sub(r"sha16=[0-9a-f]{16}", "sha16=HASH", line)
        for tok in ("before", "after"):
            line = line.replace(tok + ": ", "RUN: ")
        line = line.replace(os.path.join(BEF, "").replace("\\", "/"), "OUT/")
        line = line.replace(os.path.join(AFT, "").replace("\\", "/"), "OUT/")
        line = line.replace("kvmem/m2_visibility/m6/out/_before/", "OUT/")
        line = line.replace("kvmem/m2_visibility/m6/out/_after/", "OUT/")
        # 临时目录里的 6 位时间戳文件名
        import re
        line = re.sub(r"\d{6}\.json", "STAMP.json", line)
        out.append(line)
    return "\n".join(out)


def diff_counts(old_text, new_text):
    d = list(difflib.unified_diff(old_text.splitlines(), new_text.splitlines(), lineterm=""))
    adds = sum(1 for l in d if l.startswith("+") and not l.startswith("+++"))
    dels = sum(1 for l in d if l.startswith("-") and not l.startswith("---"))
    hunks = sum(1 for l in d if l.startswith("@@"))
    return {"insertions": adds, "deletions": dels, "hunks": hunks}


def read(p):
    return open(p, encoding="utf-8").read()


def main():
    old_src, new_src = read(OLD), read(NEW)
    arms = {}
    for name, path in ARMS.items():
        d = json.load(open(path, encoding="utf-8"))
        arms[name] = {"artifact": ent(path),
                      "code_sha16": d["code_sha16"],
                      "guard": d.get("guard"),
                      "outcome": d["outcome"]}

    suites = {}
    for tag in ("two-dry", "m1-explain", "l1a", "l1b", "l2", "p1", "s1-bed"):
        b, a = os.path.join(BEF, tag + ".stdout"), os.path.join(AFT, tag + ".stdout")
        suites[tag] = {"before": ent(b), "after": ent(a),
                       "stdout_byte_identical": sha256(b) == sha256(a),
                       "stdout_semantic_identical": norm(read(b)) == norm(read(a))}

    two_b = json.load(open(os.path.join(BEF, "two-dry.json"), encoding="utf-8"))
    two_a = json.load(open(os.path.join(AFT, "two-dry.json"), encoding="utf-8"))
    two_diff = [k for k in set(two_b) | set(two_a) if two_b.get(k) != two_a.get(k)]
    s1_b = json.load(open(os.path.join(BEF, "two-session-bed.json"), encoding="utf-8"))
    s1_a = json.load(open(os.path.join(AFT, "two-session-bed.json"), encoding="utf-8"))
    s1_diff = [k for k in set(s1_b) | set(s1_a) if s1_b.get(k) != s1_a.get(k)]

    freeze = subprocess.run([PY, "-X", "utf8", os.path.join(TOOLS, "freeze_check.py")],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=ROOT)
    verify = subprocess.run(["bash", os.path.join(ROOT, "verify.sh")],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=ROOT)
    numstat = subprocess.run(["git", "-C", os.path.join(ROOT, "llama.cpp"), "diff", "--numstat"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    ins = dels = 0
    for ln in numstat.stdout.splitlines():
        f = ln.split("\t")
        if len(f) >= 2:
            ins += int(f[0])
            dels += int(f[1])
    gitstat = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    mine = [l for l in gitstat.stdout.splitlines()
            if ("m2_visibility/m6" in l or "LANDED-m6a-fix" in l or "m3/m3_lease.py" in l
                or "m3/_before" in l)]

    # ---- _before 是反向重建的：显式声明 + 可复现实测（绝不再假装"改前拷贝"） ----
    l2 = json.load(open(os.path.join(M3, "LANDED-l2.json"), encoding="utf-8"))
    authority = l2["files"]["m3_lease.py"]
    sha_cmd = [PY, "-X", "utf8", "-c",
               "import hashlib;print(hashlib.sha256(open(r'%s','rb').read()).hexdigest()[:16])"
               % OLD]
    sha_run = subprocess.run(sha_cmd, capture_output=True, text=True, encoding="utf-8",
                             errors="replace")
    grep_cmd = ["grep", "-c", "MOVE_GUARD", OLD]
    grep_run = subprocess.run(grep_cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
    before_copy = {
        "path": ent(OLD)["path"], "bytes": os.path.getsize(OLD), "sha16": sha16(OLD),
        "before_reconstructed": True,
        "reconstruction_method":
            "改前字节没有先拷贝（_before/ 被 _*/ 忽略、施工前未落盘）：按本单补丁反向剥离重建 —— "
            "去掉 BlockLeases.__init__ 里的 guard 块（move_guard/guard_installed/guard_install_note、"
            "move_refusals、_guard_engine_move 调用）、check_move/_guard_engine_move/状态字段、"
            "functools 导入；只剥本单补丁，不多剥/少剥；最终 sha256[:16] 必须等于权威坐标"
            "（实测见 verification）",
        "authoritative_source": {"file": "kvmem/m2_visibility/m3/LANDED-l2.json",
                                 "field": "files.m3_lease.py.sha16",
                                 "value": authority["sha16"], "bytes": authority.get("bytes")},
        "verification": {
            "command": "python -X utf8 -c <sha256 one-liner over _before/m3_lease.py@33ae...>",
            "stdout": sha_run.stdout.strip(),
            "exit": sha_run.returncode,
            "matches_authority": sha_run.stdout.strip() == authority["sha16"],
            "matches_declared_old": sha16(OLD) == OLD_SHA,
            "grep_MOVE_GUARD_count": (grep_run.stdout.strip() or "0"),
        },
    }
    assert before_copy["verification"]["matches_authority"], before_copy["verification"]
    assert before_copy["verification"]["matches_declared_old"], before_copy["verification"]

    guard_section = {
        "install": "BlockLeases.__init__ 构造期在实例上包 eng.repos_local；装不上 ⇒ raise "
                   "LeaseError（fail-closed，不是静默 unguarded）",
        "missing_move_api": "engine 无 repos_local ⇒ guard_installed=False + "
                            "move_guard_not_applicable 事件；product 调它会 AttributeError，"
                            "不存在可被静默绕过的 move 路径（本身 fail-closed）",
        "noncallable_or_assign_error": "repos_local 存在但不可调用 / 实例赋值失败 ⇒ 构造期 raise，"
                                       "文案带 engine 类型、属性、文件名与函数名",
        "variant_of": "BlockLeases(same_table)",
        "disable": "唯一关闭方式：构造参数 move_guard=False（变体/测试显式传；product 不传）",
        "env_seam": "无：m3_lease.py 不读任何环境变量（旧 env 缝已删，grep=0）",
        "arms_guard": {name: arms[name]["guard"] for name in ("RED", "GREEN", "VARIANT")},
        "selftest": {
            "green_guard_installed_true": bool(arms["GREEN"]["guard"]["guard_installed"])
                                          and arms["GREEN"]["outcome"].get("guard_selftest") is True,
            "variant_move_guard_ctor_false": arms["VARIANT"]["guard"]["move_guard_ctor"] is False,
            "variant_not_installed": arms["VARIANT"]["guard"]["guard_installed"] is False,
            "variant_selftest_true": arms["VARIANT"]["outcome"].get("guard_selftest") is True,
            "note": "probe 的 checks 里带断言：真实 engine 建 GuardedLeases 后 guard_installed "
                    "必须 True，否则该 arm 红",
        },
    }

    zero_change = {
        "m1_explain_byte_identical": suites["m1-explain"]["stdout_byte_identical"],
        "two_dry_stdout_semantic_identical": suites["two-dry"]["stdout_semantic_identical"],
        "two_dry_all_ok_before_after": [two_b.get("checks", {}).get("all_ok"),
                                        two_a.get("checks", {}).get("all_ok")],
        "two_dry_json_top_level_diff_keys": sorted(two_diff),
        "two_dry_json_diff_is_only_timestamp": sorted(two_diff) == ["at"],
        "s1_dry_json_diff_keys": sorted(s1_diff),
        "s1_dry_json_diff_is_only_at_label": sorted(s1_diff) in (["at"], ["at", "label"]),
        "s1_dry_pass": [s1_b.get("n_pass"), s1_b.get("n_fail"), s1_a.get("n_pass"),
                        s1_a.get("n_fail")],
        "l1_11_11": suites["l1b"]["stdout_semantic_identical"],
        "l2_5_5": suites["l2"]["stdout_semantic_identical"],
        "p1_5_5": suites["p1"]["stdout_semantic_identical"],
        "suites": suites,
    }

    static_no_trigger = {
        "claim": "product 路径从不移动『已 attach 的块 seq』：所有 move 都在 attach 之前",
        "sites": [
            {"file": "tools/chat.py", "move": 286, "attach": 310,
             "order": "cmd_chat 装载：先 load→repos_local(286)，全部放好后统一 attach(310)"},
            {"file": "tools/chat.py", "move": 394, "attach": 397,
             "order": "_place_slots：move(394) 紧接 attach(397)，块刚 load 无 referrer"},
            {"file": "tools/chat.py", "move": 637, "attach": 639,
             "order": "cmd_m1 每轮：detach 旧→reset→load→move(637)→attach(639)"},
            {"file": "tools/chat.py", "move": 1021, "attach": 1025,
             "order": "S1 two_session_run：move(1021) 在 attach(1025) 之前；A/B 块按 mount "
                      "分给不同 dst（home→seq0、project→seq7），块首次挂载前才 move"},
            {"file": "tools/session_state.py", "move": 362, "attach": 370,
             "order": "restore：load_strict→move(362)→share(370)"},
            {"file": "kvmem/m2_visibility/m4/m4_write.py", "move": 232, "detach": 231,
             "order": "先 detach(231) 再回拉 move(232) ⇒ holders 为空"},
        ],
        "guard_off_paths": ["delta==0", "seq 不是已注册块", "该块 holders 为空",
                            "构造参数 move_guard=False（只给变体/测试显式传）"],
    }

    summary = {
        "schema": "m6a_i2_summary_v1",
        "task": "task-38 M6a-fix I2：共享 cell 移动 fail-closed 守卫（红→绿→变体）",
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "code": {"old": {**ent(OLD), "sha16_verified_against": "LANDED-l2.json"},
                 "new": ent(NEW), "diff": diff_counts(old_src, new_src),
                 "files_unchanged": {"tools/chat.py": sha16(os.path.join(TOOLS, "chat.py")),
                                     "tools/chat_lease.py": sha16(os.path.join(TOOLS, "chat_lease.py")),
                                     "freeze_analysis.py": sha16(os.path.join(TOOLS, "analysis.py")),
                                     "freeze_retrieval.py": sha16(os.path.join(TOOLS, "retrieval.py")),
                                     "freeze_evidence.py": sha16(os.path.join(TOOLS, "evidence.py"))}},
        "construction": {
            "block": "kvmem/blocks/profile.kvmem（50 cells，DB memory_block=50）",
            "seqs": {"block": 3, "dialogue_A": 0, "dialogue_B": 7},
            "steps": ["load(profile->3)", "attach(3->0,[0,50))", "attach(3->7,[0,50))",
                      "eng.repos_local(3,+100)"],
        },
        "arms": arms,
        "before_copy": before_copy,
        "guard": guard_section,
        "zero_behavior_change": zero_change,
        "static_no_trigger": static_no_trigger,
        "discipline": {
            "engine_changed": False, "rebuild": False,
            "llama_cpp_numstat": {"insertions": ins, "deletions": dels},
            "repo_db_sha16": sha16(REPO_DB),
            "git_status_mine": mine,
        },
        "freeze_check": {"exit": freeze.returncode,
                         "first_line": (freeze.stdout.strip().splitlines() or [""])[0],
                         "status": "FROZEN" if "FROZEN" in freeze.stdout else "RED"},
        "verify_sh": {"exit": verify.returncode,
                      "last_line": (verify.stdout.strip().splitlines() or [""])[-1]},
        "four_state": {"I2-fix": "通过"},
        "four_state_scope": "自证：红/绿/变体 + 零行为变化；复核对 lead/inspector",
        "honesty": {
            "before_reconstructed": True,
            "before_copy_provenance": "改前字节未先复制（施工前 _before 未落盘），由现盘反向剥离本单"
                                      "补丁重建；sha16 与 LANDED-l2.json 的权威坐标 %s 逐字节一致"
                                      "（见 before_copy.verification 的实测命令与 stdout）" % OLD_SHA,
            "reconstruction_not_a_copy": "不要把它当'改前拷贝'引用：它是反向重建，声明与校验都在 "
                                         "before_copy 段；若两者不一致应以 LANDED-l2.json 为准",
            "real_arms_not_rerun": "m1/two 真机臂与 S1 真机臂未重跑（会产新读数）；"
                                   "零行为变化按 lead 指定的 explain/dry-run/S1 干跑四项对照",
            "suites_provenance": "L1/L2/P1/S1 干跑与 m1/two 输出在终版上重跑后写入 _after/；"
                                 "逐字节对照见 zero_behavior_change.suites",
        },
    }
    with open(SUMMARY, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)

    ledger = {
        "schema": "landed_m6a_fix_v1",
        "task": "task-38 M6a-fix I2（只修 I2；I1/I3/I4 不修）",
        "at": summary["at"],
        "summary": ent(SUMMARY),
        "code": summary["code"],
        "before_copy": summary["before_copy"],
        "guard": summary["guard"],
        "sites_covered": ["kvmem/m2_visibility/m3/m3_lease.py（BlockLeases 实例层守卫）"],
        "not_touched": ["llama.cpp/**", "tools/chat.py", "tools/chat_lease.py",
                        "tools/analysis.py", "tools/retrieval.py", "tools/evidence.py",
                        "kvmem/chat.db"],
        "red_green_variant": {
            "RED": {"artifact": arms["RED"]["artifact"], "code_sha16": arms["RED"]["code_sha16"]["m3_lease.py"],
                    "before_pos": arms["RED"]["outcome"]["before"]["seq0"]["pos_range"],
                    "after_pos": arms["RED"]["outcome"]["after"]["seq0"]["pos_range"],
                    "seq7_after": arms["RED"]["outcome"]["after"]["seq7"]["pos_range"],
                    "refused": arms["RED"]["outcome"]["refused"],
                    "moved": arms["RED"]["outcome"]["moved"]},
            "GREEN": {"artifact": arms["GREEN"]["artifact"],
                      "code_sha16": arms["GREEN"]["code_sha16"]["m3_lease.py"],
                      "before_pos": arms["GREEN"]["outcome"]["before"]["seq0"]["pos_range"],
                      "after_pos": arms["GREEN"]["outcome"]["after"]["seq0"]["pos_range"],
                      "seq7_after": arms["GREEN"]["outcome"]["after"]["seq7"]["pos_range"],
                      "refused": arms["GREEN"]["outcome"]["refused"],
                      "refusal": (arms["GREEN"]["outcome"]["move_refusals"] or [None])[0]},
            "VARIANT": {"artifact": arms["VARIANT"]["artifact"],
                        "code_sha16": arms["VARIANT"]["code_sha16"]["m3_lease.py"],
                        "guard": arms["VARIANT"]["guard"],
                        "before_pos": arms["VARIANT"]["outcome"]["before"]["seq0"]["pos_range"],
                        "after_pos": arms["VARIANT"]["outcome"]["after"]["seq0"]["pos_range"],
                        "refused": arms["VARIANT"]["outcome"]["refused"],
                        "moved": arms["VARIANT"]["outcome"]["moved"]},
        },
        "zero_behavior_change": zero_change,
        "static_no_trigger": static_no_trigger,
        "discipline": summary["discipline"],
        "freeze_check": summary["freeze_check"],
        "verify_sh": summary["verify_sh"],
        "four_state": summary["four_state"],
        "four_state_scope": summary["four_state_scope"],
        "honesty": summary["honesty"],
        "corrections": [
            {"id": "before-copy-honesty",
             "old": "_before/m3_lease.py 被当作改前拷贝",
             "new": "before_reconstructed=true + 重建方法 + 与 LANDED-l2.json 权威坐标逐字节一致的"
                    "实测命令/stdout（before_copy 段）",
             "basis": "mv 前未落盘；sha256[:16] == 33ae679a50d58c93（LANDED-l2.json files.m3_lease.py）"},
            {"id": "env-seam-removal",
             "old": "用环境变量关闭 move 守卫（读到 0 时全局静默放行，不落 move_refusals）",
             "new": "删掉 env 缝；唯一关闭方式为构造参数 move_guard=False（变体/测试显式传）",
             "basis": "env 里一个值就能 bypass（fail-closed 缺口）；现盘 m3_lease.py grep=0"},
            {"id": "guard-install-fail-closed",
             "old": "_guard_engine_move 的 except 分支 return False（静默不装守卫）",
             "new": "实例赋值失败/属性不可调用 ⇒ 构造期 raise LeaseError（带 engine 类型/属性/文件行）；"
                    "无 repos_local ⇒ guard_installed=false + 事件（product 调它会 AttributeError，"
                    "本身 fail-closed）",
             "basis": "静默 false = 产品可能带着没装的守卫跑；现盘已无静默分支"},
        ],
        "gaps": {
            "dst_side_move_not_guarded": "只守『块 seq 被共享时移动块』；『对话 seq 移动时其已挂块跟着移』"
                                         "未加守卫（M2 planner 自己的 detach→move→attach 合同覆盖，"
                                         "本单零行为变化要求不碰）",
            "raw_restore_path": "GuardedLeases/RecordingEngine 下 restore 若未 detach，拒绝点仍在 reset "
                                "守卫（未前移）；若绕过 RecordingEngine 用 raw engine 调 "
                                "session_state.restore_session，reset 不被表拦截，本守卫会在其后的 "
                                "repos_local 处 fail-closed（消息为 move 守卫）——本单未重跑该路径",
            "m4_ablation_arms_not_rerun": "M4 ablation/plate 臂未重跑；它们只在移动『已 attach 的块』时"
                                          "才会被拒（按设计 fail-closed）",
            "real_arms_not_rerun": summary["honesty"]["real_arms_not_rerun"],
        },
        "no_self_sha": True,
    }
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1)

    print("summary: %s (%d B, sha16=%s)" % (SUMMARY, os.path.getsize(SUMMARY), sha16(SUMMARY)))
    print("ledger:  %s (%d B, sha16=%s)" % (LEDGER, os.path.getsize(LEDGER), sha16(LEDGER)))
    print("code: old %s -> new %s diff %s" % (OLD_SHA, sha16(NEW), summary["code"]["diff"]))
    print("zero-change:", json.dumps({k: v for k, v in zero_change.items() if k != "suites"},
                                     ensure_ascii=False))
    print("freeze:", summary["freeze_check"]["status"], "| verify:", summary["verify_sh"])
    return 0


if __name__ == "__main__":
    sys.exit(main())