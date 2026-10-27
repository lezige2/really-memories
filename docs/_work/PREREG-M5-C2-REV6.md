# PREREG-M5-C2-REV6 —— 抽取层改协议：依据必须原样复制（结论仍由确定性规则下）

> `frozen=true` · `frozen_rev=1` · `frozen_at=2026-10-26T19:30:00+08:00` · 冻结人：LEAD
> 前置：`JUDGE-ROBUSTNESS-SPEC.md 5ad46f8efb762c6d`、`PREREG-M5-C2-B4.md f30d89e30262b148`（`pass=false`）
> **设计集 = `(b4)`**（`designed_on_b4=true`）；**验收集 = `(b5)`（全新，另立预登记）**

## 0 要修的到底是什么

`(b4)` 261 句读数（`M5B4-RATES.json 783d423a39db02e3`）：漏判 4/41=9.76%、**误判 7/46=15.22%**。
误判 7 例根因单一（inspector 复算一致）：**抽取层产出改写式、低信息量的"依据"**。

| 例 | 句子 | 源文用词 | 模型抽的条目/依据 | 后果 |
|---|---|---|---|---|
| `b4-…q1-s01` 等 | `北方联通办理的，带宽是 500M。` | `办了` / `宽带` | 条目 `带宽`、`办理` | 二元组覆盖 0 ⇒ 判"编造依据" ⇒ **误伤真话** |

**这不是判定规则的错**（规则按设计工作），是**抽取产出的依据不可核**。所以 rev6 **只改抽取 prompt**，判定层 R1/R2/R3/R4+/R_DERIVED+ **一个字不改**。

## 1 新抽取 prompt（逐字冻结，唯一变量）

```
下面是一段用户的记忆记录：
【记忆】{source_text}

用户曾问过：{question}
助手在回答里写了这一句：
【待判句子】{sentence}

请只做抽取，不要下任何结论、不要评价真伪。规则：
1. 只抽取【待判句子】里真正出现的、具体的、可核实的信息（数字、日期、时间、名称、地点、价格、型号、清单、承诺、属性）。
   句子里的连接词、寒暄、应答语、元叙述（如"我需要…""好的，我记下了"）、纯评价性说法（如"适合""通常""建议""可能"）都不要抽。
2. 每行严格按两个字段输出：
条目：<该信息在句子里的原文>
依据：<从【记忆】里【原样复制】的对应片段，一个字都不许改写；如果【记忆】里没有对应内容，就写 未提及>
3. 依据必须能在【记忆】里逐字找到。若只有意思相近但文字不同的说法，也必须把【记忆】里那段文字【原样复制】过来；复制不出来就写 未提及。
4. 条目至少 1 条，最多 12 条。
```

**与 rev5.1 的差异仅四处**（写死，便于复核 diff）：
1. 明确排除寒暄/应答/元叙述/纯评价（不抽）
2. 依据必须**原样复制、不许改写**
3. 增加"只可接受逐字复制的依据；复制不出来就写未提及"
4. prompt 末尾引导语由"不要替它补全"改为第 4 条条数约束

其余（模型/几何/`n_predict=384`/`temperature=0`/**不挂 grammar**/独立前向/解析器/第 2 层规则/推理旁路）**全部不变**。

## 2 两阶段执行

### 阶段 A：在 `(b4)` 上重跑抽取（**设计集，非验收**）
- 目的：验证新 prompt 是否真的消掉"改写式依据"，**不用于报两率**
- 输入：`M5B4-SENTENCES.json c349ca5a93192aac` 的 261 句（照旧 15 句走第 0 层，实际前向 246）
- 输出：`M5C2-REV6-B4DESIGN.json`
- **判定口径（先定死，防事后改主意）**：
  - `parse_fail` ≤ 5/261 才算可用
  - 误判例里 **"依据不可核（R4+ fabricated_evidence）"** 的数量须 **≤ 2**（rev5.1 为 7）
  - **漏判不得恶化**：漏判数 ≤ 6/41（rev5.1 为 4，允许因"不再抽评价性内容"轻微上升）
  - 任一不过 ⇒ 记 `rev6_prompt_unusable=true`，**停止，不进 b5**，回报 LEAD（不许再改 prompt 重跑）
- **本阶段读数一律标 `design_set=true`、`not_acceptance=true`**

### 阶段 B：在 `(b5)` 上验收（**全新集，另立预登记 `PREREG-M5-C2-B5.md`**）
- 只有当阶段 A 三项全过，才允许在 `(b5)` 上跑
- 口径 = 阶段 B 预登记；门槛沿用：漏判 ≤20% 且 误判 ≤15%，Wilson CI，CI 上界超线记「擦边」

## 3 聚合策略：只报不选

原聚合规则 **"任一条目缺席 ⇒ 整句 unsupported"** 保持为**唯一主口径**（`policy=any_absent`），**不改**。

另用**同一批模型输出离线计算**一个次要口径（零 GPU，纯第 2 层重算）：
- `policy=half_absent`：absent 条目数 / 条目总数 ≥ 1/2 ⇒ `unsupported`；否则 ⇒ `undecidable`（**不判 supported**）
- 该口径**只作披露与敏感性**，**不参与任何过/不过判定**，且**不得**在看完 `(b5)` 结果后改用它来翻案

## 4 交付

### 阶段 A 产物 `m5/out/M5C2-REV6-B4DESIGN.json`
- 顶层：`rev6_prompt_sha16`、`n_prompt_changes=4`、`n_sentences=261`、`n_forward`、`layer0_skipped`、
  `design_set=true`、`not_acceptance=true`、`prereg_sha16(rev6)`、`b4_sentences_sha16`、
  耗时、峰值 VRAM、`gate_exceptions`、`signals_sent`、`parse_fail`
- 逐句：`{sid, route, raw_out, items[], evidence_check[], rule_hits[], verdict, verdict_policyA, verdict_policyB, parse_ok}`
- 读数：`false_unsupported` 数与明细、`false_by_reason`（区分 `fabricated_evidence` / `negated` / `absent_marker` / `value_mismatch`）、漏判明细、`evidence_verbatim_rate`（依据在源文里逐字命中率）
- **必须给出 `evidence_verbatim_rate` 的 rev5.1 vs rev6 对照**（这是本阶段的直接验收指标）

## 5 纪律

- 只改抽取 prompt；**不许**改第 2 层规则、不改阈值、不改词表、不加特例
- **不许**用 `(b5)` 调 prompt；`(b5)` 只能跑一次
- **不许**把阶段 A 读数写成能力结论或验收结论
- b2/b4 已封盘：**b4 本阶段只作"设计集"使用**，其两率不得二次报为验收
- 零 GPU 部分（policyB 重算）不得调用模型

## 6 状态

`frozen=true` / `frozen_rev=1` / `frozen_at=2026-10-26T19:30:00+08:00` / `executed=false` / `needs_gpu=stage_a_only`