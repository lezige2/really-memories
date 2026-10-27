# PREREG-M5-C2-REV7 —— 判定层四处确定性修复（数值归一化 / R1 值域收窄 / 条目原子性 / 缺席词作用域）

> `frozen=true` · `frozen_rev=1` · `frozen_at=2026-10-26T20:15:00+08:00` · 冻结人：LEAD
> 前置：`M5B4-JUDGE.json 6a3001b6ca23ef7d`（rev5.1 输出）、`M5B4-LEAD-RULING.json 9273ebc97aa1413a`（金标）
> **抽取层回退到 rev5.1 prompt**；`PREREG-M5-C2-REV6.md faaf2605116bb594` 的 prompt **撤回，不作采纳**（理由见 §1）
> **本阶段零 GPU**：在 `M5B4-JUDGE.json` 已落盘的 `items[]` 上离线重算判定层
> **设计集 = `(b4)`**（`designed_on_b4=true`）；**验收集 = `(b5)` `e306ce994d306a84`（已冻结，未跑）**

## 0 LEAD 诊断更正（推翻 §13.32 的"改写式依据"归因）

`(b4)` rev5.1 的 7 例误判，**`R4+ fabricated_evidence` 命中数 = 0**（来自 `M5B4-JUDGE.json` 的 `rule_hits`）。真实归因：

| 归因 | 例数 | 例 | 根因 |
|---|---:|---|---|
| **R1 数值归一化缺失** | **4** | `b4-s1-q2-s01/-s15`、`b4-s1-q3-s03` | 句内值 `8600元` vs 依据 `8,600 元`：二元组覆盖 = **0.75 < 0.80** ⇒ 判 value_mismatch。**纯标点问题** |
| **R1 值域过宽（贪心实体正则）** | **2** | `b4-s2-q1-s01`、`b4-s8-q2-s02` | 正则 `[^\s，。]{2,}(?:公司\|店\|院\|…)` 贪心吞掉前缀：抽出 `租车公司`（覆盖 0.333）、`地点是宠安医院`（覆盖 0.5）⇒ 拿"描述语"当"值"比对 |
| **R3 缺席词越界** | **2**（与上重叠 1 例） | `b4-s1-q2-s07`、`b4-s1-q2-s09` | 模型列出句内根本不存在、或重复的条目（`患者`、`做的`），其 `未提及` 被计入聚合 ⇒ 整句 unsupported |

**结论：这不是"模型改写词汇"的问题，是判定层三个确定性 bug。** §13.32 的"误判瓶颈 = 抽取器产出改写式依据"**归因错误**，须在文档中更正。

## 1 rev6 处置：prompt 撤回

| 指标 | rev5.1 | rev6 | 判定 |
|---|---:|---:|---|
| quote-bearing item 逐字率 | **98.45%**（318/323） | **90.88%**（289/318） | rev6 **更差** |
| 漏判 | 4/41 | **6/41** | rev6 **更差** |
| 误判 | 7/46 | 4/46 | rev6 略好，但归因是 R1 用例变动，非 prompt 机制 |
| `parse_fail` | 1 | 3 | rev6 更差 |

⇒ **rev6 prompt 撤回**，抽取层回 rev5.1 prompt（`a6bc4f268f7711de`）。rev6 产物保留为失败留痕，**不得**写成"改进"。

## 2 四处修复定义（逐字冻结）

### N1 数值归一化（`normalize()` 扩展）
在现有"去空白"之前增加：
1. **NFKC**（全角数字/标点 → 半角）
2. **千分位剥离**：`re.sub(r'(?<=\d)[,，](?=\d{3})', '', s)`
3. 数字与单位之间空白删除（现有去空白已覆盖）
**验收自检（必须断言）**：`coverage('8600元', normalize('手术费 8,600 元')) == 1.0`

### N2 R1 值域收窄（`value_tokens()` 改）
1. **删除**通用实体式 `[^\s，。]{2,}(?:公司|店|院|馆|中心)`
2. 改为**非贪心 + 排除功能词前缀**：`(?:(?:是|叫|为|在|到)\s*)?([^\s，。是叫为在的]{2,8}(?:公司|店|院|馆|中心|银行|医院|学院|酒店|机场))`，取**捕获组 1**
3. **新增前置门**：实体型 token **只有在其本身于源文中出现时**才作为"值"参与 R1；不在源文中 ⇒ 视为描述语，**不参与 R1**，交由 R4+ 的证据核验处理
4. 纯值型 token（数字/日期/型号/编号/楼层/课次）**不变**，全部参与 R1

### N3 条目原子性门（新增）
对每条 item：若 `normalize(item.item)` **不能**在 `normalize(sentence)` 中定位（子串命中，或对该句的最优等长窗口覆盖 ≥0.90）⇒ 该 item **作废**：`valid=false`，**不参与聚合、不产生 absent、不计入 `unverified`**。
断言自检：`b4-s1-q2-s07` 的 `患者`、`b4-s1-q2-s09` 的 `患者` 必须被判 `valid=false`。

### N4 缺席词作用域（新增）
`未提及`/`没有`/`未找到` 等缺席词**仅在 `valid=true` 的条目上生效**；作废条目的缺席词**不进入**聚合。

**其余 R1/R2/R3/R4+/R_DERIVED+ 规则、阈值 0.80、词表一律不变。**

## 3 门槛（b4 设计集，零 GPU，先定死）

| 指标 | rev5.1 基线 | 门槛 |
|---|---:|---|
| 误判 | 7/46 = 15.22% | **≤ 4/46** |
| 漏判 | 4/41 = 9.76% | **≤ 5/41** |
| `parse_fail` | 1/261 | **≤ 2/261** |
| 漏判新增（gold=fabricated 由 unsupported → supported） | — | **= 0**（逐例检查，任何一例即判失败） |

任一不过 ⇒ `rev7_unusable=true`，**停**，回报 LEAD，**不许调阈值/N/规则重跑**。

## 4 交付

`m5/out/M5C2-REV7-OFFLINE.json`（`n_forward=0`）
- 顶层：`rev7_ver=1`、`n_sentences=261`、`n_forward=0`、`design_set=true`、`not_acceptance=true`、`prereg_sha16`、
  `items_source_sha16=M5B4-JUDGE.json 6a3001b6ca23ef7d`、`gold_sha16_current=9273ebc97aa1413a`
- 逐条：`{sid, item, evidence, valid(N3), matcher_hit, dice/coverage, numeric_ok, item_verdict}`
- 逐句：`{sid, gold, verdict_rev5_1, verdict_rev7, n_items, n_valid, n_invalid, n_absent, n_unverified}`
- 读数：FP/leak 数与明细、`false_by_reason`（N1/N2/N3/N4/R4+/declared/other 逐例归类）、作废条目总数与占比、
  **逐句对照（谁修好、谁改坏，必须全列）**
- **N1–N4 各自的自检断言结果**（§2 里写明的三条断言必须打印 pass/fail）

## 5 纪律

- 零 GPU、零模型、不联网；纯确定性重算
- 抽取层回 rev5.1 prompt，**不重跑模型**（本阶段直接用 `M5B4-JUDGE.json` 的 items）
- 不许改金标、不许删例、不许调阈值
- `(b5)` 不得用于本阶段任何调参；`(b5)` 在 rev7 冻结后**只跑一次**
- 若 `rev7_unusable=true`，`(b5)` **不跑**，记 `blocked_by_judge_unusable`

## 6 状态

`frozen=true` / `frozen_rev=1` / `executed=false` / `needs_gpu=false` / `next=b5_acceptance`