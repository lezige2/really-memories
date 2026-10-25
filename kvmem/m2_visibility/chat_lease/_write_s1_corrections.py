# -*- coding: utf-8 -*-
"""S1-b 补正产物（不重跑 14B、不改 chat.py、不回改 S1-real*.json 原内容）。

覆盖 lead 转达的 inspector 终审非读数层补正：
  F1  `S1-real-default-regression.json` 的 `db_copy.sha16` 是**跑前值**（假声明）；
      跑后 temp 副本 `attr`/`value_kind` 被 `cmd_m1 → R.build_index(chat.py:521)`
      重建 ⇒ 本补正给 before/after 双 sha + 派生重建来源 + 读数不受影响证据。
  F2  `S1-real.json` / `S1-real-smoke.json` 的 `run.notes` 是**静态文案**（沿 dry-run
      写成"未做"），与 real 臂 `checks=true` 冲突 ⇒ 标 `notes_static_text_error: true`，
      逐条给 notes 原文 / 实际 checks / 权威字段，并给正确四态文本。
  F4  `frozen_numbers.geometry` 的 `chat_start_B="+18"` 笔误 + spec 缺 `lines=132`
      —— 台账字段，本产物只做文字存档（真正落点在台账 addendum）。
  F5  `red_proofs.R5` 极性：`expect_red=[]` 而红在 `fail_cases=["M_CAP_refuses"]`
      —— 台账字段，本产物存档 `red_kind` 与"主臂 CAP=未触发绿"表述。

只读产品/台账/DB；产物落 `out/S1-real-default-regression-correction.json`，LF。
"""
import hashlib
import json
import os
import sys
from datetime import datetime

ROOT = r"D:\llama-mem"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "kvmem", "m2_visibility", "m2_planner", "out")
SPEC = os.path.join(ROOT, "docs", "_work", "M2-FULL-S1-SPEC-lead.md")
TEMP_DB = os.path.join(HERE, "tmp_db", "chat@237d8e1f.db")
REAL_DB = os.path.join(ROOT, "kvmem", "chat.db")
PRODUCT = os.path.join(OUT, "S1-real-default-regression-correction.json")


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def ent(path):
    return {"path": os.path.relpath(path, ROOT).replace("\\", "/"),
            "sha16": sha16(path), "bytes": os.path.getsize(path)}


def jload(name):
    p = os.path.join(OUT, name)
    with open(p, encoding="utf-8") as fh:
        return json.load(fh), p


def main():
    real, real_p = jload("S1-real.json")
    smoke, smoke_p = jload("S1-real-smoke.json")
    m1, m1_p = jload("S1-real-default-regression.json")
    checks = real["run"]["checks"]
    fact = real["fact_layer"]
    stab = real["run"]["sha_stable"]
    norm_hit_b = fact["B"]["own_hit_rounds"]
    notes = real["run"]["notes"]

    corr = {
        "schema": "s1_corrections_v1",
        "spec": "docs/_work/M2-FULL-S1-SPEC-lead.md@" + sha16(SPEC),
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "why": "inspector 终审 INSPECTOR-S1B-REVIEW.md@058d29dca281ea47 列出的"
               "非读数层补正（F1/F2/F4/F5；F3 在台账 module_shas）；"
               "按不可回改规则，不改任何已产出读数文件本体，只出本补正 + 台账 addendum",
        "original_products": {
            "S1-real.json": ent(real_p),
            "S1-real-smoke.json": ent(smoke_p),
            "S1-real-default-regression.json": ent(m1_p),
        },
        "F1_db_copy_correction": {
            "applies_to": "out/S1-real-default-regression.json",
            "original_claim": {"db_copy": {"path": m1["db_copy"]["path"],
                                           "sha16": m1["db_copy"]["sha16"]}},
            "corrected": {
                "sha16_before": sha16(REAL_DB),
                "sha16_after": sha16(TEMP_DB),
                "derived_rebuilt_by": "cmd_m1 → R.build_index(chat.py:521)（无条件重建派生索引）",
                "why_bytes_differ": "temp 副本的派生表 attr/value_kind 被重建；"
                                    "证据面 8 张表逐行相同（inspector 逐表逐行复核）",
                "readings_unaffected": True,
                "readings_unaffected_evidence":
                    "inspector 对 5 个 DB 状态跑 _selection + _two_selection_texts："
                    "每题 selection (name,score) 逐字段相同，A/B 选择文本逐字符相同"
                    "（A 16 字 / B 43 字），真机 selection_hits A=conv_2026-10-25#L3 / B=project "
                    "与 dry 一致 ⇒ 派生索引状态不改变 S1 选块/读数",
            },
            "originals_immutable": True,
            "authority": "本补正字段；原产品 db_copy 是跑前值，不得当跑后值引用",
        },
        "F2_notes_static_text_error": {
            "flag": True,
            "applies_to": ["out/S1-real.json", "out/S1-real-smoke.json"],
            "field": "run.notes",
            "error_kind": "static_text",
            "error_note": "notes 是 dry-run 口径的静态文案（把 real 才判的三条写成'未做'），"
                          "real 臂 checks 为 true；文案无判据效力，以 checks 与事实层为准",
            "per_item": [
                {"key": "S1-01",
                 "notes_text": notes.get("S1-01"),
                 "actual_checks": checks.get("S1-01"),
                 "evidence": {"fact_layer.A.own_hit_rounds": fact["A"]["own_hit_rounds"],
                              "fact_layer.A.rounds": fact["A"]["rounds"],
                              "fact_layer.B.own_hit_rounds_norm": fact["B"]["own_hit_rounds"],
                              "fact_layer.B.literal_hit_last":
                                  fact["B"]["own_hit_last_literal"]},
                 "judgement": "通过"},
                {"key": "S1-02b",
                 "notes_text": notes.get("S1-02b"),
                 "actual_checks": checks.get("S1-02b"),
                 "evidence": {"cross.a_to_b": real["run"]["cross"]["a_to_b"],
                              "cross.b_to_a": real["run"]["cross"]["b_to_a"]},
                 "judgement": "通过"},
                {"key": "S1-05",
                 "notes_text": notes.get("S1-05"),
                 "actual_checks": checks.get("S1-05"),
                 "evidence": {"sha_stable.status": stab.get("status"),
                              "sha_stable.unchanged": stab.get("unchanged"),
                              "sha_stable.checked_n": len(stab.get("checked") or [])},
                 "judgement": "通过"},
            ],
            "correct_four_state": {"S1-01": "通过", "S1-02b": "通过", "S1-05": "通过"},
            "dry_run_context": "notes 文本对 dry-run 是正确口径（dry 时 S1-01/02b/05 确为'未做'，"
                               "见 S1-dryrun.json checks），错在 real 臂沿用了同一静态文案",
            "originals_immutable": True,
        },
        "F3_module_shas": {
            "correction": "台账 module_shas 由 10 条扩到 14 条（并入判据床与 3 个驱动/落账脚本）",
            "added": ["kvmem/m2_visibility/chat_lease/_test_two_session.py",
                      "kvmem/m2_visibility/chat_lease/_land_s1.py",
                      "kvmem/m2_visibility/chat_lease/_run_s1_real.py",
                      "kvmem/m2_visibility/chat_lease/_run_m1_regression.py"],
            "note": "判据床/驱动/落账脚本也是冻结面（0 漂移集合必须覆盖判据本身）",
        },
        "F4_frozen_numbers_text_correction": {
            "field": "frozen_numbers.geometry",
            "old_text": "A home [4075,4096) chat_start_A=4096; B project [4096+n_chat_A, +18) "
                        "chat_start_B=+18",
            "new_text": "A home [4075,4096) chat_start_A=4096; "
                        "B project [4096+n_chat_A, 4096+n_chat_A+18) "
                        "chat_start_B=4096+n_chat_A+18（+18 中 18=project cells，"
                        "不是常数偏移；换块 cells 时随之变）",
            "spec_lines_added": 132,
            "note": "真机/干跑/产品读数与正确公式一致（A 536 ⇒ B 4650=4096+536+18；"
                    "dry 670 ⇒ B 4784），原文本只是台账笔误",
        },
        "F5_red_proof_R5_polarity": {
            "red_proof": "R5",
            "red_kind": "case(M_CAP_refuses)",
            "expect_red": [],
            "fail_cases": ["M_CAP_refuses"],
            "n_pass": "11/12",
            "note": "主臂 CAP=未触发绿（10 轮 536/580 ≤ 1024，按设计不触发）；"
                    "红的判可性来自 16 轮 case 级对照（refused=true, reason=chat_len_cap, "
                    "over 1072>1024）；R5 删 CAP 校验后同输入 refused=false、B 跑满 16 轮 "
                    "⇒ case 级红足够证明守门，主产物不该红",
        },
        "four_state_corrected": {
            "S1-01": "通过（真机：A 字面 10/10、B 去空白 10/10；以 checks.S1-01 + fact_layer 为准）",
            "S1-02b": "通过（真机：A 不含 3月14、B 不含 广陵路，2/2；以 checks.S1-02b + cross 为准）",
            "S1-05": "通过（真机：sha_stable done/unchanged=True，7 文件；以 run.sha_stable 为准）",
            "note": "run.notes 的'未做'是静态文案错误，不参与判决；其余条目不涉及本轮补正",
        },
        "no_product_modified": True,
    }
    out = PRODUCT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # 生成后写自身 sha 之外的字段：script sha 先记（脚本本身不再改）
    corr["script_sha16"] = sha16(os.path.abspath(__file__))
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(corr, fh, ensure_ascii=False, indent=1)
    print("corrections: %s (%d B, sha16=%s)"
          % (out, os.path.getsize(out), sha16(out)))
    print(json.dumps({"F2": corr["F2_notes_static_text_error"]["correct_four_state"],
                      "F1_before_after": [corr["F1_db_copy_correction"]["corrected"]["sha16_before"],
                                          corr["F1_db_copy_correction"]["corrected"]["sha16_after"]],
                      "originals": {k: v["sha16"] for k, v in corr["original_products"].items()}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())