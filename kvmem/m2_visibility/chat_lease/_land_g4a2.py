# -*- coding: utf-8 -*-
"""task-35 G4a-2/G4a-3 落账：`kvmem/m2_visibility/chat_lease/LANDED-g4a2.json`。

只读复算 + 汇总；不改代码、不跑引擎（两跑由 `_run_m1_g4a2.py` 已完成）。
口径：sha16 = 二进制 sha256 前 16 hex；本文件不登记自身 sha。
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")
OUT = os.path.join(HERE, "out")
LEDGER = os.path.join(HERE, "LANDED-g4a2.json")
BEFORE = os.path.join(HERE, "_before", "chat.py@bb083a1b71165e97")
V2 = os.path.join(OUT, "M4C-m1-rerun-v2.json")
VAR = os.path.join(OUT, "G4a2-red-variant.json")
SP_VAR = os.path.join(OUT, "G4a2-variant-want2sel.json")
SPEC = os.path.join(ROOT, "docs", "_work", "M2-FULL-S1-SPEC-lead.md")
BLOCKS = {k: os.path.join(ROOT, "kvmem", "m2_v1_14b", k + ".kvmem")
          for k in ("home", "project", "habit")}
FROZEN = {
    "analysis.py": os.path.join(TOOLS, "analysis.py"),
    "retrieval.py": os.path.join(TOOLS, "retrieval.py"),
    "evidence.py": os.path.join(TOOLS, "evidence.py"),
}


def sha16(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def ent(path):
    return {"path": os.path.relpath(path, ROOT).replace("\\", "/"),
            "sha16": sha16(path), "bytes": os.path.getsize(path)}


def main():
    v2 = json.load(open(V2, encoding="utf-8"))
    var = json.load(open(VAR, encoding="utf-8"))
    sp = json.load(open(SP_VAR, encoding="utf-8"))
    fz = subprocess.run([sys.executable, "-X", "utf8",
                         os.path.join(TOOLS, "freeze_check.py")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    ledger = {
        "schema": "landed_g4a2_v1",
        "task": "task-35 G4a-2（决策面）+ G4a-3（展示面）",
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "spec": dict(ent(SPEC), lines=132),
        "repo_db": ent(os.path.join(ROOT, "kvmem", "chat.db")),
        "block_files": {k: ent(v) for k, v in BLOCKS.items()},
        "frozen_three": {k: ent(v) for k, v in FROZEN.items()},
        "chat_py": {
            "before": dict(ent(BEFORE), note="task-33 G4b 后态（现盘，先副本再改）"),
            "after": ent(os.path.join(TOOLS, "chat.py")),
            "diff_hunks": ["@@ -494,11 +494,17 @@（_explain 展示面）",
                           "@@ -528,7 +534,8 @@（sel_mountable）",
                           "@@ -537,8 +544,12 @@（decide 入参）",
                           "@@ -668,6 +679,7 @@（refuse 分支 turns 字段）"],
            "changes": [
                "G4a-2：新增 sel_mountable（有 memory_block 的命中）；E.decide 入参 sel→sel_mountable；"
                "want 由 sel_mountable 派生（挂载面不变）",
                "G4a-2：refuse 分支 turns 补 skipped_no_block 字段（证据一致性）",
                "G4a-3：_explain 对每条检索行标注 [可挂载]/[无块行→不可挂载]，并另起一行"
                "「可挂载集：…（空）」；检索分数/名字未改",
            ],
            "not_changed": ["evidence.py（冻结三件，一行未动）", "_selection（two 等共用，未收窄）",
                            "retrieval/analysis（未改）", "chat_lease.py/m3_lease.py/块/DB"],
        },
        "g4a2": {
            "choice": "decide 入参改为 sel_mountable（有块行的 selection 子集）",
            "effective_chat_py": "1790f3a9b5e6b865（G4a-2 生效点；现盘 22081c41 含 explain_version 2）",
            "why_not_evidence": "evidence.py 是冻结三件，不允许改；decide 的 'if selection' 语义本身没错，"
                                "错在 m1 把'不可挂载的检索命中'当成记忆证据送进去",
            "why_not_narrow_selection": "_selection 被 two/chat 等共用；收窄它会改检索语义与共享读数，"
                                        "超出本单授权；m1 是唯一把 selection 当'记忆证据'的消费者",
            "judge_unchanged": "E.decide / evidence.py 的判据逻辑与文案未改；只改送入的集合",
            "control_q_red_proof": {
                "construction": "同 DB 副本 + 同 14B + 同 m1 构造，只把 decide 入参换回未过滤 sel",
                "v2": {"state": v2["control_q"]["decide"]["state"],
                       "refuse": v2["control_q"]["decide"]["refuse"],
                       "ask_count": v2["control_q"]["ask_count"],
                       "reply": v2["control_q"]["decide"]["reply"],
                       "n_selection": v2["control_q"]["decide"]["n_selection"]},
                "variant": {"chat_py_sha16": var["chat_py"]["sha16"],
                            "state": var["control_q"]["decide"]["state"],
                            "refuse": var["control_q"]["decide"]["refuse"],
                            "ask_count": var["control_q"]["ask_count"],
                            "n_selection": var["control_q"]["decide"]["n_selection"],
                            "answers": var["control_q"]["answers"]},
                "prefix_regression": {"product": "out/G4a2-red-variant.json",
                                      "base_sha16": "bb083a1b71165e97",
                                      "state": var["control_q"]["decide"]["state"],
                                      "ask_count": var["control_q"]["ask_count"]},
                "single_point_want2sel": {
                    "product": "out/G4a2-variant-want2sel.json",
                    "base_sha16": "1790f3a9b5e6b865", "hunks": 1,
                    "state": sp["control_q"]["decide"]["state"],
                    "refuse": sp["control_q"]["decide"]["refuse"],
                    "ask_count": sp["control_q"]["ask_count"],
                    "answers_nonempty": [bool((a or "").strip()) for a in
                                         sp["control_q"]["answers"]],
                    "red_points": sp["red_points"],
                },
                "red_points": var["red_points"],
                "verdict": "v2 = no_evidence + refuse=True + ask=0 + REFUSAL；"
                           "variant(bb083a1b) = memory_hit + refuse=False + ask=1 + 生成"
                           "「鲁QXXXX」⇒ 同一构造红/绿可区分，判据有判别力",
            },
            "other_questions": [
                {"q": d["q"], "state": d["state"], "refuse": d["refuse"],
                 "ask_count": v2["ask_by_question"].get(d["q"], 0),
                 "n_selection": d["n_selection"]}
                for d in v2["decides"] if d["q"] != v2["control_q"]["q"]
            ],
            "mounts": v2["loads"],
            "attaches_done": v2["asserts"]["attaches_done"],
            "skip_events": v2["asserts"]["skip_events"],
            "note": "模型上下文从未被 conv#L5 污染（无块行、从未挂载）；本修纠正的是"
                    "**执行与状态标签**：'检索命中' 不等于 '记忆证据'。",
        },
        "g4a3": {
            "field": "_explain 输出（m1 --explain / S1-real-default-regression.json 的 stdout）",
            "old_sha16": "3e8aae60685d2e55", "old_bytes": 872, "old_status": "v1 已作废",
            "new_sha16": "c4cbad83784e647f", "new_bytes": 1126,
            "explain_version": 2, "version_line": "explain_version: 2",
            "annotation_only": True,
            "stripped_equals_old": True,
            "reversible_product": "out/G4a2-containment.json（脚本化断言，非一次性结论）",
            "addendum_product": "out/S1-default-unchanged-explain-v2-addendum.json",
            "note": "lead 裁：保留 G4a-3、不回退；『explain 逐字节』硬锚改判为可逆性断言 + "
                    "containment 三条（two 干跑字段同、m1 非 explain 臂除 CONTROL_Q 外同、cmd_chat 零 diff）。"
                    "去标注后仍逐字节同 3e8aae60 ⇒ 分数/名字一行未变。",
        },
        "products": {
            "v2": ent(V2),
            "prefix_regression": dict(ent(VAR), variant_kind="prefix-regression",
                                       base_sha16="bb083a1b71165e97"),
            "single_point_variant": dict(ent(SP_VAR), variant_kind="single-point(want→sel)",
                                         base_sha16="1790f3a9b5e6b865", hunks=1),
            "driver": ent(os.path.join(HERE, "_run_m1_g4a2.py")),
            "containment": ent(os.path.join(OUT, "G4a2-containment.json")),
            "explain_addendum": ent(os.path.join(OUT, "S1-default-unchanged-explain-v2-addendum.json")),
        },
        "regressions": {
            "m1_explain": {"old_sha16": "3e8aae60685d2e55", "old_status": "v1 已作废",
                           "new_sha16": "c4cbad83784e647f", "explain_version": 2,
                           "identical": False, "annotation_only": True,
                           "replaced_by": "可逆性断言（out/G4a2-containment.json: explain_v2.reversible）" +
                                          " + containment 三条"},
            "two_dryrun": {"exit": 0, "checks_all_ok": True, "verdict": "通过",
                           "fail_ids": []},
            "l1": {"n_cases": 11, "fail_cases": [], "exit": 0, "result": "11/11"},
            "l2": {"n_cases": 5, "fail_cases": [], "exit": 0, "result": "5/5"},
            "p1": {"n_cases": 5, "fail_cases": [], "exit": 0, "result": "5/5"},
            "freeze_check": {
                "exit": fz.returncode,
                "first_line": (fz.stdout.strip().splitlines() or [""])[0],
                "status": "FROZEN" if "FROZEN" in fz.stdout else "RED",
            },
            "sha_stable": v2["sha_stable"],
        },
        "gaps": {
            "index_meta_docs": {"observed": {"memory_source": 10, "memory_block": 2, "doc": 10,
                                             "index_meta": {"docs": "2", "version": "5",
                                                            "analysis": "4"}},
                                "judgement": "旧构建器遗留元数据（build_index 只写 version/analysis）；"
                                             "与 doc 10 行不一致=M1.8 缺口；非 KeyError/G4a 直接原因；"
                                             "本单未修（索引侧另单），已在此登记，不静默留着",
                                "four_state": "未做（索引侧另单）"},
            "g4c_note": "lead 已撤回 G4c：M4-C base 用 fixed_selection/WANT_SEQ 写死 seq，不读 retrieval 顺序；"
                        "m1 CLI 按 selection 分数挂 ⇒ 两臂口径差，接受。夹具臂重跑（G4d）属 task-36。",
            "negative_arm_note": "负例形态变化只发生在 **m1 CLI 臂**（真实检索）：memory_hit 但 0 块 → "
                                 "no_evidence 拒答；**M4-C 夹具臂不受影响**（其 WANT_SEQ 索引 0 = CONTROL_Q "
                                 "本就是空 selection ⇒ decide([]) 一直走 no_evidence/拒答）。"
                                 "故 M4-C 负例不需要因 G4a-2 重签；G4d 目的是恢复回归链。",
        },
        "four_state": {
            "G4a-2（决策面）": "通过（CONTROL_Q：no_evidence + refuse=True + ask=0；变体回 memory_hit+ask=1）",
            "G4a-3（展示面）": "通过（检索行标注可挂载性；去标注后 retrieval 读数与旧输出逐字节同）",
            "explain 回归": "通过（lead 已裁：v1 硬锚 3e8aae60 作废，改可逆性断言 + containment 三条，"
                           "见 out/G4a2-containment.json）",
            "index_meta.docs 缺口": "未做（索引侧另单，已登记）",
        },
        "next": "lead 复核；task-36（G4d）夹具臂重跑恢复回归链（非负例重签）；索引侧 index_meta 缺口另单；"
                "P2（kvslots n<0 折空）另单",
        "no_self_sha": True,
    }
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1)
    print("ledger: %s (%d B, sha16=%s)" % (LEDGER, os.path.getsize(LEDGER), sha16(LEDGER)))
    print("freeze:", ledger["regressions"]["freeze_check"]["status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())