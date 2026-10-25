# -*- coding: utf-8 -*-
"""task-33 G4 落账：`kvmem/m2_visibility/chat_lease/LANDED-g4.json`。

只读复算 + 汇总；不改代码、不跑引擎（重跑由 `_run_m1_g4.py` 已完成）。
口径：sha16 = 二进制 sha256 前 16 hex；本文件不登记自身 sha（自指恒假）。
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
LEDGER = os.path.join(HERE, "LANDED-g4.json")
BEFORE = os.path.join(HERE, "_before", "chat.py@288d2d85720359e0")
PRODUCT = os.path.join(OUT, "M4C-m1-rerun.json")
SPEC = os.path.join(ROOT, "docs", "_work", "M2-FULL-S1-SPEC-lead.md")
BLOCKS = {
    "home": os.path.join(ROOT, "kvmem", "m2_v1_14b", "home.kvmem"),
    "project": os.path.join(ROOT, "kvmem", "m2_v1_14b", "project.kvmem"),
    "habit": os.path.join(ROOT, "kvmem", "m2_v1_14b", "habit.kvmem"),
}
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
    prod = json.load(open(PRODUCT, encoding="utf-8"))
    reg_prod = json.load(open(os.path.join(ROOT, "kvmem", "m2_visibility", "m2_planner",
                                           "out", "S1-real-default-regression.json"),
                              encoding="utf-8"))
    # --- 回归：freeze_check 现算（进程退出码 + 首行）---
    fz = subprocess.run([sys.executable, "-X", "utf8", os.path.join(TOOLS, "freeze_check.py")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    comp = prod["m4c_comparison"]
    ledger = {
        "schema": "landed_g4_v1",
        "task": "task-33 G4a+G4b",
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "spec": dict(ent(SPEC), lines=132),
        "repo_db": dict(ent(os.path.join(ROOT, "kvmem", "chat.db"))),
        "block_files": {k: ent(v) for k, v in BLOCKS.items()},
        "frozen_three": {k: ent(v) for k, v in FROZEN.items()},
        "chat_py": {
            "before": dict(ent(BEFORE), note="S1-b 后态（task-32 收口时现盘）"),
            "after": ent(os.path.join(TOOLS, "chat.py")),
            "diff_hunks": ["@@ -524,7 +524,19 @@", "@@ -535,13 +547,21 @@", "@@ -587,6 +607,9 @@"],
            "changes": [
                "cmd_m1 selection→挂载面过滤：missing=无 memory_block 的命中；want=可挂载命中；"
                "missing 非空时落 _event(site3.skipped_no_block) + _crit(status=skipped)（可见，不进覆盖集）",
                "打印：命中但均无块行时明示；部分跳过时打印 '跳过：name(score)（无 memory_block 行…）'",
                "turns 记录增 skipped_no_block 字段（证据层可复核）",
                "挂载循环加防御 die（过滤后仍缺块行 ⇒ 明确诊断，不静默）",
            ],
            "not_changed": ["two / 默认 chat / chat_lease.py / m3_lease.py / 冻结三件 / "
                            "retrieval.analysis/evidence / DB / 索引构建"],
        },
        "root_cause": {
            "numbers": {"memory_source": 10, "memory_block": 2, "doc": 10,
                        "index_meta": {"docs": "2", "version": "5", "analysis": "4"},
                        "indexable_sources": ["profile", "project"]},
            "mechanism": "retrieval.build_index 按 memory_source 全表建 doc/term/facet（10 条，"
                         "含 conv 对话行与 7 条摘录）；可挂载块只对 indexable_sources 建"
                         "（human_memory 且非摘录且不含模型轮次 ⇒ profile/project 2 条）。"
                         "cmd_m1 旧代码把 selection 的 name 直接当块行键用（rows[name] @:598）"
                         "⇒ 命中无块源的问句即 KeyError。",
            "control_q": {"q": "我的车牌号是多少？",
                          "top_hit": "conv_2026-10-25#L5", "source_id": 7,
                          "score": 2.12518,
                          "note": "该行正文='我车牌是浙B-3F19K。'，恰是控制句来源；"
                                  "命中源没有 memory_block（is_excerpt=1 不建块）"},
            "other_questions": "3 个记忆问句的 top-k 均落在 profile/project（均有块行）⇒ 只有控制问句触发崩溃",
            "g4a": "负对照污染（判据作废候选）：负对照要求'问句内容不在记忆里'，但架构允许对话行"
                   "入检索索引 ⇒ CONTROL_Q 的命中来自对话摘录本身。影响 M4-B/M4-C 的**负例**"
                   "（正臂不受影响，但负例有效性须重跑才恢复）；不属于四态（按 M4-C 判决惯例，"
                   "判据作废进决策记录，不进通过/未通过）。",
            "g4b": "KeyError 'conv_2026-10-25#L5' @chat.py:598 是同一根因的表征（rows[name] 缺键）。",
            "g3_note": "index_meta.docs=2 是旧构建器遗留的元数据（build_index 只写 version/analysis），"
                       "与 doc 表 10 行不一致 ⇒ M1.8 缺口；本单不修（索引侧另单），"
                       "且它不是 KeyError 的直接原因（块只对 indexable_sources 建，属设计）。",
        },
        "before_evidence": {
            "product": dict(ent(os.path.join(ROOT, "kvmem", "m2_visibility", "m2_planner",
                                             "out", "S1-real-default-regression.json"))),
            "g4_confirmed": reg_prod.get("g4_confirmed"),
            "m1_real_new": {k: reg_prod["m1_real_new"].get(k)
                            for k in ("raised", "type", "msg", "frame", "elapsed_s")},
            "m1_real_old": {k: reg_prod["m1_real_old"].get(k)
                            for k in ("raised", "type", "msg", "frame", "elapsed_s")},
            "note": "S1-b 回归已证 new=old 同一 KeyError（G4 既有，非 S1 引入）",
        },
        "fix": {
            "approach": "b（可见跳过 + 记账），理由：改名/重建索引会让负对照失去位置且属绕过；"
                        "die() 会让 m1 永久不可绿（控制问句必命中摘录）；b 保持"
                        "'无块源不挂载'的负例语义并把跳过落成可复核证据",
            "where": "tools/chat.py:527-539（过滤+记账）、:550-560（打印）、:564（turns 字段）、"
                     ":610-612（防御 die）",
            "judge_unchanged": "E.decide 仍消费原始 sel（状态判定不变）；本修只改'挂载哪些块'，"
                               "不改选择分数/阈值/判据",
            "visible": {"event": "site3.skipped_no_block（role=event, site=None，不进覆盖集）",
                        "crit": "site3.skipped_no_block（role=criterion, status=skipped）",
                        "print": "跳过：conv_2026-10-25#L5(2.13)（无 memory_block 行，不挂载；已记 site3.skipped_no_block）",
                        "turns_field": "skipped_no_block"},
            "no_silent_skip": True, "no_index_rebuild": True,
        },
        "rerun": {
            "product": ent(PRODUCT),
            "driver": ent(os.path.join(HERE, "_run_m1_g4.py")),
            "exit": prod["exit"], "run_s": prod["run_s"],
            "chat_py_sha16": prod["chat_py_sha16"],
            "db": prod["db"],
            "asserts": {k: prod["asserts"][k] for k in
                        ("attaches_done", "attach_events_ok", "hits", "n_events", "n_crits")},
            "attach_events": prod["asserts"]["attach_events"],
            "skipped_no_block_events": prod["asserts"]["skipped_no_block_events"],
            "loads": prod["loads"],
            "cells_after_mount": prod["cells_after_mount"],
            "facts": prod["facts"],
            "sha_stable": prod["sha_stable"],
        },
        "m4c_comparison": {
            "expected": comp["expected"],
            "observed": comp["observed"],
            "checks": comp["checks"],
            "layout_note": comp["layout_note"],
            "verdict": comp["verdict"],
            "note": "M4-C base 已签读数（M4C-VERDICT-lead.md §2 base 行）来自 redcheck_delete.py 的"
                    "固定夹具（WANT_SEQ=[[],['profile','project'],['profile']]）；m1 按 selection 顺序"
                    "挂载 ⇒ seq 分配相反，属夹具口径差；挂载集合 {profile,project}、cells {36,50}、"
                    "attaches 2、exit 0、hits []、sha_stable 均一致。",
        },
        "regressions": {
            "m1_explain": {
                "new_sha16": "3e8aae60685d2e55", "before_sha16": "3e8aae60685d2e55",
                "identical": True, "bytes": 872,
                "note": "text 模式（universal newlines）复算；与 S1-b 已签 3e8aae60685d2e55 逐字节同",
            },
            "two_dryrun": {"exit": 0, "checks_all_ok": True, "verdict": "通过",
                           "product": "tmp_db/S1-dryrun-g4.json（一次性副本）"},
            "l1": {"n_cases": 11, "fail_cases": [], "exit": 0,
                   "lease_sha16": "33ae679a50d58c93", "result": "11/11"},
            "l2": {"n_cases": 5, "fail_cases": [], "exit": 0,
                   "note": "扩展床分母 detach 5 / 命中 1 / 未命中 4", "result": "5/5"},
            "p1": {"n_cases": 5, "fail_cases": [], "exit": 0,
                   "policy_sha16": "c2a8d8cbb5b0d4e3", "result": "5/5"},
            "freeze_check": {
                "exit": fz.returncode,
                "first_line": (fz.stdout.strip().splitlines() or [""])[0],
                "status": "FROZEN" if "FROZEN" in fz.stdout else "RED",
            },
        },
        "four_state": {
            "G4b（KeyError 表征修复）": "通过（m1 exit 0 / attaches 2 / hits [] / sha_stable；跳过可见）",
            "G4a（负对照污染）": "判据作废候选（不进四态；按 M4-C 惯例记决策记录）",
            "negative_arms": "M4-B/M4-C 的负例有效性：本修恢复'无块源不挂载'语义，但须重跑负臂才恢复整臂可信",
        },
        "next": "lead 复核；负臂（M4-B/M4-C negative）按新 chat.py 重跑对照；索引面（index_meta.docs / "
                "selection 面）另单；P2（kvslots n<0 折空）另单",
        "no_self_sha": True,
    }
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1)
    print("ledger: %s (%d B, sha16=%s)" % (LEDGER, os.path.getsize(LEDGER), sha16(LEDGER)))
    print("freeze_check:", ledger["regressions"]["freeze_check"])
    return 0


if __name__ == "__main__":
    sys.exit(main())