# -*- coding: utf-8 -*-
"""S1-b（v6 口径）落台账：LANDED-s1-real.json。

读产品 + 逐文件现算 sha（二进制 sha256[:16]），台账不写自身 sha。
口径：docs/_work/M2-FULL-S1-SPEC-lead.md@ae2d88ad5ecc25d3
用法： PY -X utf8 _land_s1.py [--out out/LANDED-s1-real.json]
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")
OUT = os.path.join(ROOT, "kvmem", "m2_visibility", "m2_planner", "out")
SPEC = os.path.join(ROOT, "docs", "_work", "M2-FULL-S1-SPEC-lead.md")
SPEC_SHA = "ae2d88ad5ecc25d3"
REAL_DB = os.path.join(HERE, "tmp_db", "chat@237d8e1f.db")
NEW_DB = os.path.join(HERE, "tmp_db", "chat@cd430943.db")


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def jload(rel):
    with open(os.path.join(OUT, rel), encoding="utf-8") as fh:
        return json.load(fh), os.path.join(OUT, rel)


def entry(path):
    return {"path": os.path.relpath(path, ROOT).replace("\\", "/"),
            "sha16": sha16(path), "bytes": os.path.getsize(path)}


def canon(prod):
    r = prod["run"]
    return {"answers": r["answers"], "checks": r["checks"], "counters": r["counters"],
            "sessions": r["sessions"], "accounting": r["cells_accounting"],
            "budget": r["budget"], "per_round": prod["per_round"],
            "sha_stable_unchanged": r["sha_stable"].get("unchanged")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "LANDED-s1-real.json"))
    args = ap.parse_args()

    if sha16(SPEC) != SPEC_SHA:
        raise SystemExit("frozen spec sha 不符：%s != %s" % (sha16(SPEC), SPEC_SHA))
    if sha16(os.path.join(ROOT, "kvmem", "chat.db")) != "237d8e1f5de9a382":
        raise SystemExit("仓库 chat.db 不是 237d8e1f：%s"
                         % sha16(os.path.join(ROOT, "kvmem", "chat.db")))

    real, real_p = jload("S1-real.json")
    real2, real2_p = jload("S1-real-2.json")
    smoke, smoke_p = jload("S1-real-smoke.json")
    m1reg, m1_p = jload("S1-real-default-regression.json")
    main_cases, main_p = jload("S1-cases-main.json")
    pre, pre_p = jload("S1-pre.json")
    unchanged, unch_p = jload("S1-default-unchanged.json")
    dry1, dry1_p = jload("S1-dryrun.json")
    dry2, dry2_p = jload("S1-dryrun-2.json")
    corr, corr_p = jload("S1-real-default-regression-correction.json")
    variants = {}
    for key in ("R1", "R2", "R3", "R4a", "R4b", "R5"):
        prod, p = jload("S1-variant-%s.json" % key)
        variants[key] = {"product": entry(p), "label": prod["label"],
                         "expect_red": prod["expect_red"], "must_green": prod["must_green"],
                         "fail_cases": prod["fail_cases"], "n_pass": prod["n_pass"],
                         "n_cases": len(prod["cases"]),
                         "chat_sha16": prod["chat_sha16"]}
    variants["R5"].update({
        "red_kind": "case(M_CAP_refuses)",
        "note": "主臂 CAP=未触发绿（真机 10 轮 536/580 ≤ 1024，按设计不触发）；"
                "红的判可性来自 16 轮 case 级对照（refused=true / reason=chat_len_cap / "
                "over 1072>1024）；R5 删 CAP 校验后同输入 refused=false、B 跑满 16 轮 ⇒ "
                "case 级红足够证明守门，主产物不该红",
    })

    r = real["run"]
    r2 = real2["run"]
    checks = r["checks"]
    fact = real["fact_layer"]
    if r["exit"] != 0 or not checks.get("all_ok"):
        raise SystemExit("真机臂不是全绿：exit=%s checks=%s" % (r["exit"], checks))

    c1, c2 = canon(real), canon(real2)
    diff = [k for k in c1 if c1[k] != c2[k]]
    t_finish = datetime.strptime(real["finished_at"], "%Y-%m-%dT%H:%M:%S")
    t_start2 = datetime.strptime(real2["started_at"], "%Y-%m-%dT%H:%M:%S")
    gap_s = int((t_start2 - t_finish).total_seconds())

    modules = {
        "tools/chat.py": os.path.join(TOOLS, "chat.py"),
        "tools/chat_lease.py": os.path.join(TOOLS, "chat_lease.py"),
        "kvmem/m2_visibility/m3/m3_lease.py": os.path.join(ROOT, "kvmem", "m2_visibility",
                                                           "m3", "m3_lease.py"),
        "kvmem/m2_visibility/m2_planner/plan.py": os.path.join(ROOT, "kvmem", "m2_visibility",
                                                               "m2_planner", "plan.py"),
        "kvmem/m2_visibility/m2_planner/planner.py": os.path.join(
            ROOT, "kvmem", "m2_visibility", "m2_planner", "planner.py"),
        "kvmem/m2_visibility/m2_planner/evict_policy.py": os.path.join(
            ROOT, "kvmem", "m2_visibility", "m2_planner", "evict_policy.py"),
        "tools/analysis.py": os.path.join(TOOLS, "analysis.py"),
        "tools/retrieval.py": os.path.join(TOOLS, "retrieval.py"),
        "tools/evidence.py": os.path.join(TOOLS, "evidence.py"),
        "kvmem/chat.db": os.path.join(ROOT, "kvmem", "chat.db"),
    }
    blocks = {n: os.path.join(ROOT, "kvmem", "m2_v1_14b", n + ".kvmem")
              for n in ("home", "project", "habit")}
    scripts = {
        "bed": os.path.join(HERE, "_test_two_session.py"),
        "land": os.path.join(HERE, "_land_s1.py"),
        "run_s1_real": os.path.join(HERE, "_run_s1_real.py"),
        "run_m1_regression": os.path.join(HERE, "_run_m1_regression.py"),
        "write_s1_corrections": os.path.join(HERE, "_write_s1_corrections.py"),
    }
    variant_modules = {}
    for key, d in (("R1", "R1-inject-source"), ("R2", "R2-same-seq"),
                   ("R3", "R3-underrecord"), ("R4a", "R4a-bypass-leases"),
                   ("R4b", "R4b-replay"), ("R5", "R5-no-cap-check")):
        p = os.path.join(HERE, "tmp_variants_v6", d, "chat.py")
        variant_modules[key] = {"module": entry(p), "variant": d}

    raw = open(os.path.join(TOOLS, "chat.py"), "rb").read()
    line_stats = {"crlf": raw.count(b"\r\n"),
                  "lone_lf": raw.count(b"\n") - raw.count(b"\r\n"),
                  "lone_cr": raw.count(b"\r") - raw.count(b"\r\n"),
                  "ends_with_newline": raw.endswith(b"\n") or raw.endswith(b"\r\n")}

    four_state = {
        "S1-01_fact_hit": "通过（A 10/10 轮含广陵路；B 10/10 轮去空白后含 3月14）",
        "S1-02a_structural": "通过（降级为接线回归：source_blocks ⊆ mounted；不计交叉分母）",
        "S1-02b_text": "通过（A 不含 3月14、B 不含 广陵路；去空白后判；两采样一致）",
        "S1-02c_selection_text": "通过（dry-run 零 GPU：A/B selection 文本互不含对方事实）",
        "S1-03_readings": "通过（A 536/pos 4631=4096+536−1；B 580/pos 5229=4650+580−1）",
        "S1-04_accounting": "通过（39+536+580=1155 ≤ 8192；engine_match=done/ok）",
        "S1-05_sha_stable": "通过（冻结三件+home/project 跑前跑后同值；habit 只登记不检）",
        "P1a_share_eq": "通过（share=2 == attach 事件=2；R4a 红证）",
        "P1b_drop_eq": "未触发/不可判（S1 无 detach：drop=0、detach 命中=0 零实例）",
        "P2_replay": "通过（attach_replay=0；R4b 红证）",
        "CAP": "通过（10 轮 536/580 未触 CAP；16 轮构造触发 PlanRefused，R5 红证）",
        "default_path_m1_real": "未通过（G4 既有缺口：KeyError conv_2026-10-25#L5 @chat.py:598；"
                                "新旧副本逐字复现；单列，不阻塞 S1）",
        "default_path_m1_explain": "通过（新旧 m1 --explain 输出逐字节相同，654 B / 3e8aae60）",
        "S1-a_dry_suite_v6": "通过（main 12/12；R1–R4b 各 12/12；R5 11/12 仅 CAP 案例红；pre 2/12）",
    }

    ledger = {
        "schema": "landed_s1_real_v1",
        "batch_id": "m2full-s1-b-real-v6",
        "task": "task-31 · S1-b（14B 真机臂，v6 口径）",
        "owner": "executor",
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "why": "v5 在真机上被两处硬矛盾证伪（几何留空位 decode 拒绝 / attach hi 非排他），"
               "lead 裁 v6（游标顺延几何、hi=排他、②a 降级+②c、②b 去空白、P-1 拆两半、"
               "cap_ok 未跑记 not_run）；本台账落 S1-b 真机两采样 + v6 dry 回归 + 默认路径现状。",
        "frozen_spec": "docs/_work/M2-FULL-S1-SPEC-lead.md@" + SPEC_SHA,
        "spec": dict(entry(SPEC), lines=132),
        "before_copies": {
            "chat_v5": entry(os.path.join(HERE, "_before", "chat.py@b9010e9c2a3c6a13")),
            "chat_v4": entry(os.path.join(HERE, "_before", "chat.py@cb70be52eef253fa")),
            "land_v5": entry(os.path.join(HERE, "_before",
                                          "_land_s1.py@e11e69f8f8ffe6f2.py")),
            "note": "v6 改了 tools/chat.py（S1 块 + DB 环境变量），故留 v5(chat) 与 v5(land) 副本；"
                    "v5 判据床 _test_two_session.py@5a52ab3c72ae2f44 已按 v6 重写，未留 v5 副本"
                    "（inspector 复核记录在 docs/_work/INSPECTOR-S1A-REVIEW.md §2）",
        },
        "change": {
            "chat_py": {"old_sha16": "b9010e9c2a3c6a13", "old_bytes": 65789,
                        "new_sha16": sha16(os.path.join(TOOLS, "chat.py")),
                        "new_bytes": os.path.getsize(os.path.join(TOOLS, "chat.py")),
                        "line_stats": line_stats,
                        "note": "v6：几何/attach hi/③公式/cap_ok/②a+②c/②b 去空白/P-1 拆半/"
                                "S1-03 默认红/DB 可用 CHAT_DB 覆盖；默认分支未改"},
        },
        "frozen_numbers": {"N_ROUNDS": 10, "CHAT_LEN_CAP": 1024, "CHAT_START": 4096,
                           "N_SEQ": 8, "seqs": {"A": 0, "B": 7},
                           "pool": 3, "mounted_blocks": 2,
                           "geometry": "A home [4075,4096) chat_start_A=4096; "
                                       "B project [4096+n_chat_A, 4096+n_chat_A+18) "
                                       "chat_start_B=4096+n_chat_A+18（+18 的 18=project cells，"
                                       "不是常数偏移；换块 cells 时随之变）",
                           "attach_hi": "exclusive"},
        "products": {
            "real_s1": entry(real_p), "real_s2": entry(real2_p), "real_smoke": entry(smoke_p),
            "default_regression": entry(m1_p), "dry_s1": entry(dry1_p),
            "dry_s2": entry(dry2_p), "cases_main": entry(main_p), "pre": entry(pre_p),
            "default_unchanged": entry(unch_p),
            "corrections": entry(corr_p),
            "variants": {k: v["product"] for k, v in variants.items()},
        },
        "two_samples": {
            "s1": {"product": "out/S1-real.json", **entry(real_p),
                   "started_at": real["started_at"], "finished_at": real["finished_at"],
                   "run_s": real.get("run_s"), "engine_load_s": real.get("engine_load_s"),
                   "answers": r["answers"], "checks": checks, "counters": r["counters"],
                   "sessions": [{k: s[k] for k in ("id", "seq", "rounds", "chat_start",
                                                   "chat_cells", "n_tokens", "pos_max",
                                                   "pos_max_expect", "reading_ok")}
                                for s in r["sessions"]],
                   "accounting": r["cells_accounting"], "budget": r["budget"]},
            "s2": {"product": "out/S1-real-2.json", **entry(real2_p),
                   "started_at": real2["started_at"], "finished_at": real2["finished_at"],
                   "run_s": real2.get("run_s"), "engine_load_s": real2.get("engine_load_s"),
                   "answers": r2["answers"], "checks": r2["checks"], "counters": r2["counters"],
                   "sessions": [{k: s[k] for k in ("id", "seq", "rounds", "chat_start",
                                                   "chat_cells", "n_tokens", "pos_max",
                                                   "pos_max_expect", "reading_ok")}
                                for s in r2["sessions"]],
                   "accounting": r2["cells_accounting"], "budget": r2["budget"]},
            "sample_gap_s": gap_s,
            "readings_identical": not diff,
            "diff_fields": diff,
            "note": "14B 有随机性 ⇒ 两采样；canon 比对去掉 /at、sample 等易变字段；"
                    "①/②b 两次一致（不一致即停手报 lead）",
        },
        "main_readings": {
            "fact_layer": fact,
            "checks": checks,
            "counters": r["counters"],
            "counter_calls": real["counter_calls"],
            "cells_accounting": r["cells_accounting"],
            "budget": r["budget"],
            "blocks_geometry": r["blocks_geometry"],
            "sha_stable": {"status": r["sha_stable"].get("status"),
                           "unchanged": r["sha_stable"].get("unchanged"),
                           "checked": r["sha_stable"].get("checked"),
                           "not_checked": r["sha_stable"].get("not_checked"),
                           "db": r["sha_stable"].get("db")},
            "three_level_denominator": {"sessions": 2, "mounted_blocks": 2, "pool_blocks": 3,
                                        "cross_assertions_text": 2,
                                        "cross_assertions_selection_text": 2,
                                        "note": "v6：②a 降级为接线回归、不计交叉分母；"
                                                "交叉分母=②b 两条"},
            "engine": real.get("engine"),
        },
        "real_smoke": {"product": entry(smoke_p), "checks": smoke["run"]["checks"],
                       "answers": smoke["run"]["answers"],
                       "sessions": [{k: s[k] for k in ("id", "chat_start", "chat_cells",
                                                       "n_tokens", "pos_max", "reading_ok",
                                                       "plan")}
                                    for s in smoke["run"]["sessions"]],
                       "note": "1 轮 A + 1 轮 B 几何冒烟：真机 ask@chat_start 命中 + pos_max 对"},
        "dry_suite": {
            "main": {"product": entry(main_p), "n_pass": main_cases["n_pass"],
                     "n_cases": len(main_cases["cases"]),
                     "fail_cases": main_cases["fail_cases"],
                     "chat_sha16": main_cases["chat_sha16"]},
            "pre": {"product": entry(pre_p), "n_pass": pre["n_pass"],
                    "n_cases": len(pre["cases"]), "fail_cases": pre["fail_cases"],
                    "note": "pre = S1 前旧文件：two 不存在 ⇒ 判据全红（2/12 的两条是"
                            "F_fail_ids 空集与默认路径对照，不构成绿）"},
            "dry_s1": {"product": entry(dry1_p), "verdict": dry1["verdict"],
                       "fail_ids": dry1["fail_ids"], "checks": dry1["checks"]},
            "dry_s2": {"product": entry(dry2_p), "verdict": dry2["verdict"],
                       "fail_ids": dry2["fail_ids"], "checks": dry2["checks"]},
            "default_unchanged": {"product": entry(unch_p),
                                  "m1_explain": unchanged["m1_explain"],
                                  "two_cli": unchanged["two_cli"],
                                  "difflib_opcodes": unchanged["difflib_opcodes"],
                                  "repo_db_sha16": unchanged["repo_db_sha16"]},
        },
        "red_proofs": variants,
        "default_path": {
            "m1_real_regression": {"product": entry(m1_p),
                                   "g4_confirmed": m1reg["g4_confirmed"],
                                   "default_path_equiv": m1reg["default_path_equiv"],
                                   "new": {k: m1reg["m1_real_new"][k]
                                           for k in ("raised", "type", "msg", "frame")},
                                   "old": {k: m1reg["m1_real_old"][k]
                                           for k in ("raised", "type", "msg", "frame")},
                                   "explain_identical": m1reg["m1_explain"]["identical"],
                                   "note": "G4（v6 §11.4）：非 S1 引起；M4-C 绿臂当前不可直接重跑"},
            "two_cli_additive": {"old_exit": unchanged["two_cli"]["old_exit"],
                                 "new_exit": unchanged["two_cli"]["new_exit"]},
        },
        "module_shas": {**{k: entry(p) for k, p in modules.items()},
                        **{k: entry(p) for k, p in scripts.items()
                           if k in ("bed", "land", "run_s1_real", "run_m1_regression")}},
        "module_shas_note": {
            "set_definition": "10 件模块 + 4 件脚本（bed / land / run_s1_real / run_m1_regression）",
            "excluded": [{
                "path": "kvmem/m2_visibility/chat_lease/_write_s1_corrections.py",
                "sha16_current": "bff31b15f4a5b2b8",
                "reason": "一次性补正写入器（生成 out/S1-real-default-regression-correction.json）；"
                          "其输出已由 product db4724341f0a25c0 锁定；纳入 0 漂移集合会因写入器重写而"
                          "假漂移，故显式排除并登记理由（inspect 二轮 F3 要求）",
            }],
            "land_coordinate": {
                "declared_sha16": "b63b22d0",
                "declared_bytes": 19216,
                "current": entry(scripts["land"]),
                "status": "unverifiable",
                "reason": "task-32 签署时的 _land_s1.py 坐标 b63b22d0（19,216 B）无 _before 副本"
                          "（_before 仅 _land_s1.py@e11e69f8f8ffe6f2.py / 16,318 B），且该文件 git 未跟踪"
                          "（??）⇒ 无法复算；现值（module_shas.land）为本轮补正后态（旧现盘 bfe52d16 → 本脚本改动后新值）。按 inspector 二轮要求，"
                          "『落账脚本冻结坐标可复算』改为如实标 unverifiable（R→A）。",
            },
        },
        "scripts": {k: entry(p) for k, p in scripts.items()},
        "variant_modules": {
            "v6": variant_modules,
            "inspector_v5_variant_modules": ["ad85f8d8", "74b52aa8", "ad3b8c7b",
                                             "ac855dd5", "cd0072f2", "968a27b4"],
            "cross_check_note": "inspector 复算的 6 个 v5 变体模块 sha 与其 v5 产物 "
                                "chat_sha16 全等（INSPECTOR-S1A-REVIEW §2）；v5 作废后"
                                "本单按 v6 chat.py 重新生成 6 个变体模块，新 sha 见 v6 段；"
                                "v5 产物已被覆盖，故那 6 个值不再可现算，只作历史对照。",
        },
        "block_files": {k: entry(p) for k, p in blocks.items()},
        "db": {
            "repo": {"path": "kvmem/chat.db",
                     "sha16_now": sha16(os.path.join(ROOT, "kvmem", "chat.db")),
                     "sha16_signed_before": "237d8e1f5de9a382",
                     "sha16_observed_drift_at_start": "40def2a2e326484b",
                     "restored_to": "237d8e1f5de9a382",
                     "note": "chat.db 是指标派生库、非冻结源（G3）；已从 inspector temp 副本恢复，"
                             "此后所有臂用 temp 副本，仓库库只读"},
            "temp_copies": {
                "chat@237d8e1f.db": {
                    "path": os.path.relpath(REAL_DB, ROOT).replace("\\", "/"),
                    "sha16": sha16(REAL_DB), "bytes": os.path.getsize(REAL_DB),
                    "content_sha_before": "237d8e1f5de9a382",
                    "actual_sha16": sha16(REAL_DB),
                    "derived_rebuilt_by": "_run_m1_regression（cmd_m1 → "
                                          "R.build_index(chat.py:521)，无条件重建派生索引）",
                    "row_level_note": "inspector 逐表逐行：10 表中 8 张行级相同（memory_source/"
                                      "memory_block/memories/memory_source_excerpt/doc/facet/"
                                      "term/index_meta）；只有派生表 attr/value_kind 不同；"
                                      "块文件 sha 未变",
                    "filename_note": "文件名里的 237d8e1f 指**内容坐标**（跑前 content sha），"
                                     "不是当前字节 sha",
                    "readings_unaffected": True,
                },
                "chat@cd430943.db": entry(NEW_DB),
            },
        },
        "deviations": [
            "_StubEngine 仍在 tools/chat.py 内（v6 §2 要求测试床内实现）：本单按 lead 裁决暂可接受，"
            "下一刀搬走",
            "v6 改了 tools/chat.py 的 S1 块与 DB 环境变量覆盖（CHAT_DB）；默认 chat/m1 分支未改，"
            "m1 --explain 新旧逐字节相同",
            "②a 已降级为接线回归（恒真被证明），不计交叉分母；交叉证据改为 ②b（2 条）",
            "P1b（drop 等式）零实例，记 not_triggered/不可判，未记通过",
            "m1 真机臂当前 exit 1 KeyError（G4 既有，非 S1）：默认回归只落证，不修绿",
            "m1 真机回归会无条件重建派生索引（cmd_m1 → R.build_index(chat.py:521)），"
            "污染任何它跑过的 DB 副本（G3/G4 交界）⇒ 后续默认路径回归另用一次性副本，"
            "且 db_copy 必须 before/after 双记（见 addendum F1）",
        ],
        "stop_conditions_checked": {
            "lease_error": "无（真机两采样均无 LeaseError）",
            "engine_match": "对得上（measured_blocks=39，sum_accounted=sum_incr=1116，ok=true）",
            "samples_consistent": not diff,
            "sample_gap_s": gap_s,
            "exception": "无",
        },
        "four_state": four_state,
        "addendum": {
            "schema": "s1_ledger_addendum_v1",
            "supersedes": "98bbf28b65d1de19",
            "supersedes_note": "原台账全部读数/产物 sha/两采样全文保留；本 addendum 只补"
                               "标签、文本与口径（inspector INSPECTOR-S1B-REVIEW.md@"
                               "058d29dca281ea47 的 F1–F5），不改任何读数",
            "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "corrections_product": entry(corr_p),
            "F1_db_label": {
                "applies_to": "db.temp_copies['chat@237d8e1f.db']",
                "content_sha_before": "237d8e1f5de9a382",
                "actual_sha16": sha16(REAL_DB),
                # 双坐标补注（lead G4-CLOSURE §8 / inspector F1）：同一内容坐标在两次臂运行后各有一个
                # actual，correction 产物（db472434，不可回改）沿用旧值，本台账把两个都标出来源。
                "actual_dual_coordinates": {
                    "task32_copy_sha16": "2d3bae59168b6ed1",
                    "task32_source": "task-32 的 default-regression 臂结束时副本字节 sha；"
                                     "补正产物 out/S1-real-default-regression-correction.json"
                                     "（db4724341f0a25c0，不可回改）沿用此值",
                    "this_round_copy_sha16": sha16(REAL_DB),
                    "this_round_measured_at": "2026-10-25T22:11（写补正产物时实测；"
                                              "写本台账时现盘复测仍为同值）",
                    "this_round_source": "之后 S1 真机臂（_run_s1_real.py 的 chat.py 默认路径）"
                                         "在本副本上再次 cmd_m1 → build_index 无条件重建后的字节 sha",
                    "why_two_actuals": "G3 已证派生重建非确定（同一 237d8e1f 内容重建出不同字节，"
                                       "内容表不变）：2d3bae59 与 30d224c4 是同内容、不同重建批次，"
                                       "不是读数漂移，也不把真机读数退回重判",
                    "rebuilt_by": "cmd_m1 → R.build_index(chat.py:521)（无条件重建派生索引），"
                                  "由 _run_s1_real.py / _run_m1_regression.py 的默认路径共用",
                    "authority": "两个 actual 都有效、各带批次来源；correction 产物只读不回改",
                },
                "derived_rebuilt_by": "_run_m1_regression",
                "row_level_note": "内容行级与 237d8e1f 相同（inspector 逐表逐行复核）；"
                                  "attr/value_kind 属 G3 派生重建；真机读数不退回重判",
                "product_correction": "out/S1-real-default-regression-correction.json",
            },
            "F2_notes_static_text_error": {
                "flag": True,
                "applies_to": ["out/S1-real.json", "out/S1-real-smoke.json"],
                "field": "run.notes",
                "conflict": "notes 写 S1-01/S1-02b/S1-05=未做，而 run.checks 对应=true",
                "per_item": corr["F2_notes_static_text_error"]["per_item"],
                "correct_four_state": corr["F2_notes_static_text_error"]["correct_four_state"],
                "authority": "以 checks 与 fact_layer / run.sha_stable 为准；原产物不回改",
            },
            "F3_module_shas": {
                "before_n": len(modules), "after_n": len(modules) + 4,
                "added": ["_test_two_session.py", "_land_s1.py",
                          "_run_s1_real.py", "_run_m1_regression.py"],
                "note": "判据床/驱动/落账脚本也是冻结面（0 漂移集合必须覆盖判据本身）",
            },
            "F4_frozen_numbers_text": {
                "fixed_geometry":
                    "A home [4075,4096) chat_start_A=4096; "
                    "B project [4096+n_chat_A, 4096+n_chat_A+18) "
                    "chat_start_B=4096+n_chat_A+18（18=project cells；换块 cells 随之变）",
                "spec_lines_added": 132,
            },
            "F5_red_proof_R5": {
                "red_kind": "case(M_CAP_refuses)",
                "expect_red": [],
                "fail_cases": ["M_CAP_refuses"],
                "note": variants["R5"]["note"],
            },
            "original_readings_intact": True,
        },
        "verdict": "通过（S1-b 真机层，v6；P1b 未触发不可判；默认路径 m1 真机为 G4 既有缺口，单列）",
        "verdict_addendum": "读数层判决不变（通过）；F1–F5 为标签/文本/口径补正，不改读数、不重跑 14B",
        "next": "lead 复核后签 S1；M4-C 绿臂须先修 G4（selection→块行过滤/补块行）；"
                "_StubEngine 搬入测试床单列一刀",
        "no_self_sha": True,
    }
    out = os.path.abspath(args.out)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1)
    print("ledger: %s (%d B, sha16=%s)"
          % (out, os.path.getsize(out), sha16(out)))
    print("two_samples identical=%s gap=%ss" % (not diff, gap_s))
    print(json.dumps(four_state, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())