# CODE-TRACE-M5C2-REV7.1 —— 文档主张 ↔ 代码/产物 逐条追踪

> 由 `kvmem/m2_visibility/m5/out/m5c2_rev7_1_claim_map.py` 自动生成（`--check` 可只校验、不写盘）。
> 冻结件：PREREG `docs/_work/PREREG-M5-C2-REV7.1.md` sha16 `09d6f1b163ea0b84` / 16313 B；脚本 `kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py` sha16 `88256d274c9993cc` / 50618 B；产物 `kvmem/m2_visibility/m5/out/M5C2-REV7-1-OFFLINE.json` sha16 `55191eaf2426f736` / 510508 B。
> 对照 C32：脚本 `65ed60125528d5d6`、产物 `1f8f44b921e575fe`。

## 摘要

| 指标 | 值 |
|---|---:|
| claim 总数 | 84 |
| pass | 76 |
| fail（文档对不上代码/产物） | 5 |
| unverifiable（需运行/未来行为） | 3 |

> 退出码：`--check` 有任一 fail 返回 1；本表含 **5 条 fail**，故退出码 1 是结论（不是校验器故障），只有全部主张成立才返回 0。

| 分组 | 条数 | pass | fail | 不可验证 |
|---|---:|---:|---:|---:|
| §0 更正 | 11 | 11 | 0 | 0 |
| §1 引用 | 5 | 5 | 0 | 0 |
| §2.1 断言 | 6 | 6 | 0 | 0 |
| §3 门槛 | 7 | 6 | 1 | 0 |
| §4 交付 | 17 | 16 | 1 | 0 |
| §5 纪律 | 6 | 3 | 0 | 3 |
| §6 状态 | 2 | 1 | 1 | 0 |
| 附录A | 7 | 7 | 0 | 0 |
| 附录B | 6 | 5 | 1 | 0 |
| 读数 | 11 | 11 | 0 | 0 |
| 反硬编码 | 4 | 4 | 0 | 0 |
| 实现自述 | 2 | 1 | 1 | 0 |

## ① 文档确实对不上代码/产物（按严重度）

| claim | 严重度 | 文档行 | 文档说 | 实测 |
|---|---|---|---|---|
| `C3-UNUSABLE-FIELD` | medium | L72,96 | {"field": "rev7_1_unusable", "value": false} | {"rev7_1_unusable_present": false, "gate_keys": ["any_fail", "false_positive", "false_positive_sids", "leak_missed", "leak_missed_sids", "new_miss", "new_miss_s |
| `C6-EXECUTED` | low | L160,160 | {"executed": false, "artifact_exists": false} | {"executed_false_in_doc": true, "artifact_exists": true, "artifact_mtime_note": "frozen_at 21:06:55 < artifact 21:24"} |
| `B1-COUNT` | low | L140,140 | {"identical_count": 14} | {"identical_count": 15, "extra_beyond_list": ["gate_item"]} |
| `H-IMPORT-CLAIM` | low | L7,7 | {"header_claim": false, "gpu_runner_reachable": false} | {"header_claim_present": true, "transitive_local_modules": 12, "gpu_runner_reachable": true, "forward_calls": 0} |
| `C4-N4-ENUM` | low | L83,83 | {"doc_enumerates_N4": true, "implementation_has_N4_branch": true} | {"rev7_sec4_enumerates_N4": true, "rev7_sec4_quote": "- 读数：FP/leak 数与明细、`false_by_reason`（N1/N2/N3/N4/R4+/declared/other 逐例归类）、作废条目总数与占比、", "pick_attribution_re |

## ② C32 对照：8 个关键块逐键相等

| 块 | 与 C32 完全相等 |
|---|---|
| `verdict_rev7` | 是 |
| `items` | 是 |
| `gate` | 是 |
| `false_by_reason` | 是 |
| `sentence_diff` | 是 |
| `invalid_items` | 是 |
| `all_invalid_sentences` | 是 |
| `sentences` | 是 |

## ③ 逐条对照表

| claim_id | 文档行 | 代码 / 产物定位 | 检查方式 | 结果 |
|---|---|---|---|---|
| `IN-FROZEN-SHA` | L3-7 | `verify_inputs:131-194` | static_ref | PASS |
| `C0-N1-3` | L15 | `false_by_reason:0` | recompute | PASS |
| `C0-N2-2` | L16 | `value_tokens:118-132` | exec_assert | PASS |
| `C0-R3-2` | L17 | `false_by_reason:0` | recompute | PASS |
| `C0-NO-OVERLAP` | L19 | `false_by_reason:0` | recompute | PASS |
| `C0-S07-PATIENT` | L25 | `assertions.A2.occurrences[患者]:0` | recompute | PASS |
| `C0-S07-DONE` | L26 | `assertions.A2.occurrences[做的]:0` | recompute | PASS |
| `C0-S09-PATIENT` | L27 | `assertions.A3.occurrences:0` | recompute | PASS |
| `C0-SELFCHECK` | L29 | `normalize7:198-203` | exec_assert | PASS |
| `C0-VOID-OLD` | L30 | `prereg_text_corrections:0` | static_grep | PASS |
| `C0-3BUGS` | L34 | `false_by_reason:0` | recompute | PASS |
| `C0-ABL-N3OFF` | L59 | `sentence_diff.neutral:0` | recompute | PASS |
| `C1-REF` | L36-47 | `REV7 §2 L32-54` | static_grep | PASS |
| `C1-QUOTE` | L47 | `REV7 L54` | static_grep | PASS |
| `C1-ZERO-CHANGE` | L6 | `14 funcs + consts` | static_ref | PASS |
| `C1-CODE-IDENTICAL` | L7 | `main/verify_inputs:676-1143` | static_ref | PASS |
| `C1-SUPERSEDE` | L4-5 | `top-level` | static_grep | PASS |
| `C2-A1` | L53 | `main/A1:0` | exec_assert | PASS |
| `C2-A2` | L54 | `assertions.A2 / A2_verdict:0` | recompute | PASS |
| `C2-A3` | L55 | `assertions.A3 / A3_verdict:0` | recompute | PASS |
| `C2-ASSERT-5of5` | L84 | `assertions:0` | recompute | PASS |
| `C2-RETRACT` | L51 | `REV7 L49` | static_grep | PASS |
| `C2-N3-DEF` | L36-47 | `matcher/r1_r2_r3_rev7:242-321` | static_ref | PASS |
| `C3-TABLE` | L65-70 | `main/gate_item:818-821` | static_grep | PASS |
| `C3-READINGS` | L72 | `gate/sentences+gold:0` | recompute | PASS |
| `C3-UNUSABLE-FIELD` | L72-96 | `gate.rev7_1_unusable:0` | static_grep | **FAIL** |
| `C3-GATE-PASS` | L72 | `gate:0` | recompute | PASS |
| `C3-NO-TUNE` | L73 | `8 blocks` | recompute | PASS |
| `C3-B5-REF` | L74 | `B5 §9.1` | static_grep | PASS |
| `C3-SCOPE` | L72 | `design_set` | static_grep | PASS |
| `C4-ART` | L79 | `file` | static_ref | PASS |
| `C4-TOP-FIELDS` | L81 | `top-level` | static_grep | PASS |
| `C4-NEW-FIELDS` | L82 | `new top-level` | static_grep | PASS |
| `C4-SCHEMA` | L83 | `schema` | static_grep | PASS |
| `C4-BLOCK-verdict_rev7` | L83 | `json['verdict_rev7']:0` | recompute | PASS |
| `C4-BLOCK-items` | L83 | `json['items']:0` | recompute | PASS |
| `C4-BLOCK-gate` | L83 | `json['gate']:0` | recompute | PASS |
| `C4-BLOCK-false_by_reason` | L83 | `json['false_by_reason']:0` | recompute | PASS |
| `C4-BLOCK-sentence_diff` | L83 | `json['sentence_diff']:0` | recompute | PASS |
| `C4-BLOCK-invalid_items` | L83 | `json['invalid_items']:0` | recompute | PASS |
| `C4-BLOCK-all_invalid_sentences` | L83 | `json['all_invalid_sentences']:0` | recompute | PASS |
| `C4-BLOCK-sentences` | L83 | `json['sentences']:0` | recompute | PASS |
| `C4-ASSERT-PASS` | L84 | `assertions:0` | recompute | PASS |
| `C4-SELF-FLAGS` | L85 | `self flags` | static_grep | PASS |
| `C4-SCRIPT` | L86 | `file` | static_ref | PASS |
| `C4-AUDIT` | L87 | `audit json` | recompute | PASS |
| `C5-ZERO-GPU` | L91 | `flags` | static_grep | PASS |
| `C5-ONESHOT` | L92 | `no field` | static_grep | 不可验证 |
| `C5-B6` | L93 | `b6 prereg exists?` | static_grep | 不可验证 |
| `C5-NO-TUNING` | L94 | `14 funcs` | static_ref | PASS |
| `C5-NO-GOLD` | L95 | `gold` | static_grep | PASS |
| `C5-CONDITIONAL` | L96 | `gate` | static_grep | 不可验证 |
| `C6-EXECUTED` | L160 | `file exists` | static_grep | **FAIL** |
| `C6-META` | L158-160 | `top-level` | static_grep | PASS |
| `A1-REDLINE` | L102-104 | `REV7 L17` | static_grep | PASS |
| `A2-REDLINE` | L108-110 | `REV7 L49` | static_grep | PASS |
| `A3-REDLINE` | L114-116 | `REV7 L65` | static_grep | PASS |
| `A4-NEW` | L121 | `verify_inputs/c2_attribution_sentence:162-164` | static_grep | PASS |
| `A5-HEADER` | L125-127 | `REV7 L3-7` | static_grep | PASS |
| `A6-COUNTS` | L131-134 | `false_by_reason:0` | recompute | PASS |
| `A6-SUPERSEDE-CLEAR` | L129-134 | `REV7 L15/L17` | static_grep | PASS |
| `B1-FUNCS` | L140-144 | `14 funcs` | static_ref | PASS |
| `B1-COUNT` | L140 | `all funcs` | static_ref | **FAIL** |
| `B1-CONSTS` | L144 | `PURE_PATTERNS/ENTITY_PATTERN:89-97` | static_ref | PASS |
| `B2-ALLOWED` | L146-148 | `whole file diff` | static_ref | PASS |
| `B3-DIFFKEYS` | L152 | `top-level diff` | recompute | PASS |
| `B4-INPUTS` | L154-156 | `inputs` | static_grep | PASS |
| `R-261` | L72 | `sentences[]:0` | recompute | PASS |
| `R-0-FORWARD` | L91 | `n_forward:0` | recompute | PASS |
| `R-FP` | L72 | `gate.false_positive:0` | recompute | PASS |
| `R-LEAK` | L72 | `gate.leak_missed:0` | recompute | PASS |
| `R-PF` | L72 | `gate.parse_fail:0` | recompute | PASS |
| `R-NEWMISS` | L72 | `gate.new_miss:0` | recompute | PASS |
| `R-CHANGES` | L73 | `sentence_diff:0` | recompute | PASS |
| `R-INVALID` | L73 | `rates.invalid_items:0` | recompute | PASS |
| `R-ASSERT-5of5` | L84 | `assertions:0` | recompute | PASS |
| `R-GOLDDIST` | L72-73 | `gold` | recompute | PASS |
| `H-LITERALS` | L73 | `whole source` | static_grep | PASS |
| `H-261` | L72 | `main:0` | static_grep | PASS |
| `H-SID` | L78-85 | `whole source` | static_grep | PASS |
| `H-HIDDEN` | L82 | `whole source` | static_grep | PASS |
| `H-IMPORT-CLAIM` | L7 | `header L61` | static_grep | **FAIL** |
| `H-IMPORT-NOTES` | L7 | `import_notes:0` | static_grep | PASS |
| `C4-N4-ENUM` | L83 | `pick_attribution:533-548` | static_grep | **FAIL** |

## ④ 关键代码片段（每段 ≤5 行）

### normalize7（N1 三步：NFKC → 千分位 → 去空白）
```python
 198  def normalize7(s):
 199      """PREREG N1, literally: NFKC -> thousands strip -> whitespace strip."""
 200      s = unicodedata.normalize("NFKC", s or "")
 201      s = re.sub(r"(?<=\d)[,，](?=\d{3})", "", s)
 202      s = re.sub(r"\s+", "", s)
```

### item_assertion（§2.1 A2/A3 真值断言）
```python
 610  def item_assertion(sid, expected_positions, item_recs_by_sid):
 611      """REV7.1 section 2.1 true-value assertion: the listed items ARE valid.
 612  
 613      Each listed item must be valid=True with coverage==1.0 at the expected
 614      position in normalize7(sentence) (0-based inclusive).  This replaces the
```

### gate_item 四门槛阈值（4/5/2/0）
```python
 818          "false_positive": gate_item(len(fp), len(supp), 4),
 819          "leak_missed": gate_item(len(leak), len(fab), 5),
 820          "parse_fail": gate_item(len(pf), len(sent_recs), 2),
 821          "new_miss": gate_item(len(new_miss), len(fab_at_risk), 0, kind="eq"),
 822      }
```

### gate 只写 rev7_unusable（文档写 rev7_1_unusable）
```python
 829      gate["rev7_unusable"] = bool(gate["any_fail"])
 830      gate["rev7_unusable_basis"] = ("PREREG section 3: any of the four thresholds "
 831                                     "failing => rev7_unusable=true (assertions are "
 832                                     "reported separately, not a section-3 gate)")
 833  
```

### REV7.1 常量：PRE/PRE_SHA16/SUPERSEDES/CORRECTION_TYPE
```python
  70  PRE = ROOT / "docs/_work/PREREG-M5-C2-REV7.1.md"
  71  PRE_SHA16 = "09d6f1b163ea0b84"
  72  PRE_BYTES = 16313
  73  PRE_LINES = 160
  74  SUPERSEDES_SHA16 = "32eaf82ca56600c4"
```

## ⑤ 方法与复现

1. **文档→代码定位**：`ast.parse` 取函数行号区间 + 源切片 sha256；产物侧用 JSON 字段路径（`gate.false_positive`、`assertions.A2.occurrences`、`false_by_reason` …）。
2. **独立复算**：本映射自带 `normalize7`/`coverage`/`window_coverage`，对 777 条 item 重算 N3 判定；从 `sentences[]` + 金标复算四门槛、7 句变化、作废数、assertions 通过数。
3. **C32 对照**：对 8 个关键块做 Python `==` 深比较（不依赖任何审计结论），并列出全部顶层差异键。
4. **反硬编码**：扫描 46/41/777/124/35/261 字面量与 sid 特判；`b4-` 只允许出现在断言主体常量与自述清单。
5. **第三方审计交叉核对**：只读 `M5C2-REV7-1-AUDIT.json` 与 `_rev7_1_audit.py`，核对两次运行 byte 级一致与 independence（未 import 被测脚本），不作为计算来源。

```
python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_1_claim_map.py          # 生成映射
python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_1_claim_map.py --check  # 仅校验（有 fail 退出 1）
```
