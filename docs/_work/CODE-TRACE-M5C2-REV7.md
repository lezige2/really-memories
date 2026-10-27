# CODE-TRACE-M5C2-REV7 —— 文档主张 ↔ 代码 逐条追踪

> 由 `kvmem/m2_visibility/m5/out/m5c2_rev7_claim_map.py` 自动生成（可 `--check` 重跑）。
> 冻结 PREREG `docs/_work/PREREG-M5-C2-REV7.md` sha16 `32eaf82ca56600c4` / 5835 B；被测脚本 `kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py` sha16 `65ed60125528d5d6`；产物 `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json` sha16 `1f8f44b921e575fe`。

## 摘要

| 指标 | 值 |
|---|---:|
| claim 总数 | 57 |
| pass | 48 |
| fail | 7 |
| unverifiable | 2 |

> 退出码说明：`--check` 在任一 claim fail 时返回 1。本表含 **7 条 fail**（均为文档主张与代码/数据对不上的结论），因此退出码为 1 属预期，不是校验器故障；只有全部主张成立时才返回 0。

| 分组 | 条数 | pass | fail | 不可验证 |
|---|---:|---:|---:|---:|
| §0 归因 | 7 | 4 | 3 | 0 |
| §2 规范 | 19 | 17 | 2 | 0 |
| §3 门槛 | 5 | 5 | 0 | 0 |
| §4 交付 | 6 | 5 | 1 | 0 |
| 读数 | 11 | 11 | 0 | 0 |
| 反硬编码 | 5 | 5 | 0 | 0 |
| 实现自述 | 2 | 1 | 1 | 0 |
| §5 纪律 | 2 | 0 | 0 | 2 |

## 逐条对照表

| claim_id | 文档行 | 代码 | 结果 |
|---|---|---|---|
| `IN-FROZEN-SHA` | L6 | `verify_inputs:112-136` | PASS |
| `S0-R4PLUS-ZERO` | L11 | `—` | PASS |
| `S0-N1-COUNT` | L15 | `—` | **FAIL** |
| `S0-N1-COVERAGE` | L15 | `fuzzy_coverage:109-115` | PASS |
| `S0-N2-GREEDY` | L16 | `value_tokens:118-132` | PASS |
| `S0-R3-COUNT` | L17 | `—` | **FAIL** |
| `S0-R3-PREMISE` | L17 | `matcher:193-200` | **FAIL** |
| `S0-TOTAL-7` | L13-17 | `—` | PASS |
| `S2-N1-REF` | L34-38 | `normalize7:149-154` | PASS |
| `S2-N1-NFKC` | L36 | `normalize7:149-154` | PASS |
| `S2-N1-THOUSAND` | L37 | `normalize7:152` | PASS |
| `S2-N1-WS` | L38 | `normalize7:153` | PASS |
| `S2-N1-ORDER` | L35 | `normalize7:151-153` | PASS |
| `S2-N1-ASSERT-A1` | L39 | `main:622-629` | PASS |
| `S2-N2-DELETE` | L42 | `ENTITY_PATTERN:87-97` | PASS |
| `S2-N2-REGEX` | L43 | `ENTITY_PATTERN:96-97` | PASS |
| `S2-N2-GROUP1` | L43 | `value_tokens:173-177` | PASS |
| `S2-N2-GATE` | L44 | `r1_r2_r3_rev7:212-225` | PASS |
| `S2-N2-PURE` | L45 | `PURE_PATTERNS:89-94` | PASS |
| `S2-N3-DEF` | L48 | `matcher:193-200` | PASS |
| `S2-N3-VOID` | L48 | `judge_row_rev7:410-426` | PASS |
| `S2-N3-ASSERT-A2` | L49 | `char_evidence:529-558` | **FAIL** |
| `S2-N3-ASSERT-A3` | L49 | `char_evidence:529-558` | **FAIL** |
| `S2-N4-SCOPE` | L52 | `r1_r2_r3_rev7:263-272` | PASS |
| `S2-REST-THRESHOLD` | L54 | `r1_r2_r3_rev7/r4_plus_rev7/matcher:224-299` | PASS |
| `S2-REST-AGG` | L54 | `judge_row_rev7:446-460` | PASS |
| `S2-REST-VOCAB` | L54 | `r1_r2_r3_rev7:227-272` | PASS |
| `S3-FP-DEF` | L60 | `main:693-696` | PASS |
| `S3-LEAK-DEF` | L61 | `main:696` | PASS |
| `S3-PF-DEF` | L62 | `main:697` | PASS |
| `S3-NEWMISS-DEF` | L63 | `main:698-699` | PASS |
| `S3-GATE-RESULT` | L65 | `main:709-724` | PASS |
| `S4-TOP-FIELDS` | L70-71 | `main:855-875` | PASS |
| `S4-ITEM-FIELDS` | L72 | `judge_row_rev7:428-444` | PASS |
| `S4-SENT-DIFF` | L75 | `main:727-779` | PASS |
| `S4-INVALID` | L74 | `main:810-827` | PASS |
| `S4-FALSE-BY-REASON` | L74 | `pick_attribution:484-499` | **FAIL** |
| `S4-ASSERTIONS` | L76 | `main:621-648` | PASS |
| `R-261` | L69 | `main:862` | PASS |
| `R-0-FORWARD` | L69 | `main:863-867` | PASS |
| `R-FP` | L60 | `main:918-920` | PASS |
| `R-LEAK` | L61 | `main:921-922` | PASS |
| `R-PF` | L62 | `main:923-924` | PASS |
| `R-INVALID` | L74 | `main:925-926` | PASS |
| `R-NEWMISS` | L63 | `main:713` | PASS |
| `R-CHANGES` | L75 | `main:758-779` | PASS |
| `R-GOLD-DIST` | L3 | `—` | PASS |
| `R-BASELINE` | L60-62 | `baseline_reproduce:353-361` | PASS |
| `H-NO-RESULT-LITERALS` | L60-63 | `—` | PASS |
| `H-261-VALIDATION` | L69 | `main:571-582` | PASS |
| `H-THRESHOLD-TRACEABLE` | L60-63 | `gate_item:701-713` | PASS |
| `H-NO-SID-BRANCH` | L78-85 | `—` | PASS |
| `H-NO-HIDDEN-BRANCH` | L82 | `—` | PASS |
| `IMP-IMPORT-CLAIM` | L78-80 | `docstring:49-52:49-56` | **FAIL** |
| `IMP-ZERO-GPU` | L80 | `main:946-950` | PASS |
| `U-B5-ONCE` | L83 | `—` | 不可验证 |
| `U-B5-CONDITIONAL` | L84 | `main:719-724` | 不可验证 |

## 对不上 / 不可验证 的条目（重点）

### 对不上（7 条）

- **S0-N1-COUNT**（doc L15,15 ↔ `<judge rule_hits>:0`）：文档说「/ **R1 数值归一化缺失** / **4** / `b4-s1-q2-s01/-s15`、`b4-s1-q3-s03` / 句内值 `8600元` vs 依据 `8,600 元`：二元组覆盖 = **0.75 < 0.80** ⇒ 判 value_mismatch。**纯标点问题** /」；实测 {"n1_examples": 3, "n1_sids": ["b4-s1-q2-s01", "b4-s1-q2-s15", "b4-s1-q3-s03"], "n1_items": 3}。文档写 4 例，但列出的 sid 只有 3 个；按纯值型 R1 命中实测 = 3 句/3 条目（对不上）
- **S0-R3-COUNT**（doc L17,17 ↔ `<judge rule_hits>:0`）：文档说「/ **R3 缺席词越界** / **2**（与上重叠 1 例） / `b4-s1-q2-s07`、`b4-s1-q2-s09` / 模型列出句内根本不存在、或重复的条目（`患者`、`做的`），其 `未提及` 被计入聚合 ⇒ 整句 unsupported /」；实测 {"r3_examples": 2, "r3_sids": ["b4-s1-q2-s07", "b4-s1-q2-s09"], "overlap": 0}。2 例对；『与上重叠 1 例』不成立：两组 sid 互不相交，重叠 0（对不上）
- **S0-R3-PREMISE**（doc L17,17 ↔ `matcher:193`）：文档说「/ **R3 缺席词越界** / **2**（与上重叠 1 例） / `b4-s1-q2-s07`、`b4-s1-q2-s09` / 模型列出句内根本不存在、或重复的条目（`患者`、`做的`），其 `未提及` 被计入聚合 ⇒ 整句 unsupported /」；实测 {"occurrences": [{"sid": "b4-s1-q2-s07", "item": "患者", "in_sentence": true, "pos": 0}, {"sid": "b4-s1-q2-s07", "item": "做的", "in_sentence": true, "pos": 9}, {"sid": "b4-s1-q2-s09", "item": "患者", "in_sentence": true, "pos": 0}]}。文档称这些条目『句内根本不存在』；实测 患者 pos0、做的 pos 9-10 都在句内（前提错误，N3 断言因此不可满足）
- **S2-N3-ASSERT-A2**（doc L49,49 ↔ `char_evidence:529`）：文档说「断言自检：`b4-s1-q2-s07` 的 `患者`、`b4-s1-q2-s09` 的 `患者` 必须被判 `valid=false`。」；实测 {"artifact_pass": false, "occurrences": [{"item_index": 0, "item": "患者", "sentence": "患者：是在仁和口腔做的。", "normalize7_item": "患者", "normalize7_sentence": "患者:是在仁和口腔做的。", "item_in_sentence": true, "item_pos": 0, "matcher_hit": "substring", "coverage": 1.0, "valid": true, "binding_hits": ["R3"]}]}。§2 N3 断言要求 患者 判 valid=false；产物 A2 FAIL：患者 pos=0、coverage=1.0、valid=true ⇒ 断言不可满足（文档主张与代码/数据对不上）
- **S2-N3-ASSERT-A3**（doc L49,49 ↔ `char_evidence:529`）：文档说「断言自检：`b4-s1-q2-s07` 的 `患者`、`b4-s1-q2-s09` 的 `患者` 必须被判 `valid=false`。」；实测 {"artifact_pass": false, "n_occurrences": 13}。同 A2：13 个 患者 条目全部 pos=0、coverage=1.0、valid=true ⇒ 断言不可满足，产物 A3 FAIL
- **S4-FALSE-BY-REASON**（doc L74,74 ↔ `pick_attribution:484`）：文档说「- 读数：FP/leak 数与明细、`false_by_reason`（N1/N2/N3/N4/R4+/declared/other 逐例归类）、作废条目总数与占比、」；实测 {"observed_attributions": ["N1", "N2", "N3"], "n4_return_branch": false}。§4 要求 false_by_reason 含 N4 归类，但 pick_attribution 无 N4 分支、实测只出现 N1/N2/N3（对不上）
- **IMP-IMPORT-CLAIM**（doc L78,80 ↔ `docstring:49-52:49`）：文档说「## 5 纪律

- 零 GPU、零模型、不联网；纯确定性重算」；实测 {"claim_in_docstring": true, "transitive_local_modules": ["_e3gpu_run", "kvslots", "memory_source", "run_m5c2_floor", "run_m5c2_floor_rev2", "run_m5c2_r2", "run_m5c2_rev2_order", "run_m5c2_rev4", "run_m5c2_rev4_1", "run_m5c2_rev5_1_offline", "run_m5c2_rev5_offline", "session_state"], "gpu_runner_rea。自述『未导入 engine/GPU runner』不成立：R5→R41→_e3gpu_run 等 10 个本地模块被传递导入（仅 import，无前向）

### 不可静态验证（2 条）

- **U-B5-ONCE**：不可静态验证：『(b5) 冻结后只跑一次』是未来运行行为；当前仓库无 (b5) 运行数据，无法从字节证据判定
- **U-B5-CONDITIONAL**：不可静态验证：条件本身未被触发（rev7_unusable=false），『则 (b5) 不跑、记 blocked_by_judge_unusable』无运行实例可验

## 关键代码片段（每段 ≤5 行）

### S2-N1-REF — `normalize7:149`
```python
 149  def normalize7(s):
 150      """PREREG N1, literally: NFKC -> thousands strip -> whitespace strip."""
 151      s = unicodedata.normalize("NFKC", s or "")
 152      s = re.sub(r"(?<=\d)[,，](?=\d{3})", "", s)
 153      s = re.sub(r"\s+", "", s)
```

### S2-N2-REGEX — `ENTITY_PATTERN:96`
```python
  96  ENTITY_PATTERN = (r"(?:(?:是|叫|为|在|到)\s*)?"
  97                    r"([^\s，。是叫为在的]{2,8}(?:公司|店|院|馆|中心|银行|医院|学院|酒店|机场))")
```

### S2-N3-DEF — `matcher:193`
```python
 193  def matcher(item, sentence):
 194      """N3 locator.  Returns (matcher_hit, coverage) with coverage of N3."""
 195      a = normalize7(item)
 196      b = normalize7(sentence)
 197      if a in b:
```

### S2-N4-SCOPE — `r1_r2_r3_rev7:263`
```python
 263      # --- R3 absent-marker vocabulary (N4: only on valid items) ---
 264      r3 = None
 265      if valid:
 266          for marker in R5.ABSENT_MARKERS:
 267              if normalize7(marker) in ev:
```

### S3-GATE-RESULT — `main:709`
```python
 709      gate = {
 710          "false_positive": gate_item(len(fp), len(supp), 4),
 711          "leak_missed": gate_item(len(leak), len(fab), 5),
 712          "parse_fail": gate_item(len(pf), len(sent_recs), 2),
 713          "new_miss": gate_item(len(new_miss), len(fab_at_risk), 0, kind="eq"),
```

## 方法与复现

1. **静态定位**：`ast.parse` 取函数行号区间，再对源切片算 sha256，证明函数/常量确实在冻结脚本内。
2. **运行期复算**：本脚本自带独立 `normalize7` / `coverage` / `window_coverage`，对 777 条 item 逐条重算 N3 的 `valid`，并从 `sentences[]` + 金标重算 FP/漏判/parse_fail/new_miss（不读产物 `gate`/`rates` 现成值，只在最后与它们对账）。
3. **反硬编码**：扫描 46/41/777/124/35 等结果常量，确认零出现；261 仅出现在常量与输入校验；门槛 4/5/2/0 只作为 `gate_item` 阈值参数。
4. **无 sid 特判**：`if sid` / `sid ==` / `sid in` / `startswith` 零命中；`b4-` 字面量只在 EXPECT/ASSERT 与自述字典。

```
python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_claim_map.py          # 生成映射
python -X utf8 kvmem/m2_visibility/m5/out/m5c2_rev7_claim_map.py --check  # 仅校验，fail 退出码 1
```
