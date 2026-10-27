# PREREG-M5-C2-REV6-1 —— 依据核验器升级：确定性融合匹配（exact → 三元组 Dice → BM25 召回）+ 数值/实体硬校验

> `frozen=true` · `frozen_rev=1` · `frozen_at=2026-10-26T19:45:00+08:00` · 冻结人：LEAD
> 前置：`PREREG-M5-C2-REV6.md faaf2605116bb594`（抽取 prompt 改逐字复制）、`JUDGE-ROBUSTNESS-SPEC.md 5ad46f8efb762c6d`
> **本阶段零 GPU**：在 `(b4)` rev6 已落盘的 `items[]` 上**离线重算**判定，不调用模型。
> **设计集 = `(b4)`**（`designed_on_b4=true`）；**验收集 = `(b5)`**（另立预登记，只跑一次）

## 0 为什么要升级核验器

rev5.1 的证据核验只有一把刀：**字符二元组覆盖率 ≥ 0.80**。它在 `(b4)` 的 7 例误判里全部失手，因为：

| 句子用词 | 源文用词 | 二元组覆盖 | 后果 |
|---|---|---|---|
| `带宽` | `宽带` | 0（顺序不同） | 判"编造依据" ⇒ 误伤 |
| `办理` | `办了` | 0（字不同） | 同上 |

社区成熟方案（groundrails / VeriQuote / RAGGround）的共同结构是：**多层确定性匹配依次尝试，全部失败才升级**，且**数值/实体必须硬校验**。rev6.1 照此实现，仍保持**纯确定性、可复现、无模型**。

## 1 核验器定义（逐字冻结）

输入：`item.entry`（条目原文）、`item.evidence`（模型给的依据）、`source`（记忆源文）。
先做规范化：NFKC、全角→半角、去空白与标点、小写。以下所有比较都在规范化文本上做。

### 1.1 五层匹配（任一命中即 `present`，按序短路）

| 层 | 名称 | 判据 | 命中标签 |
|---|---|---|---|
| **M1** | 逐字包含 | `normalize(evidence)` 是 `normalize(source)` 的子串 | `present_exact` |
| **M2** | 字符三元组 Dice | `len(evidence) ≥ 4` 且与源文**等长窗口**滑动比对取最大 Dice，**Dice ≥ 0.75** | `present_trigram` |
| **M3** | 短串字符集 Dice | `len(evidence) ≤ 3` 且与源文等长窗口取最大**字符集** Dice，**≥ 0.80** | `present_charset` |
| **M4** | BM25 召回 | 以字符二元组为词元，源文为文档；`recall = |evidence_tokens ∩ source_tokens| / |evidence_tokens|`，**≥ 0.85** | `present_bm25` |
| **M5** | 数值/实体硬校验（**否决权**） | 若 `evidence` 含**数字/日期/金额/型号/编号**，则**必须**在源文中找到（M1 或逐字数字串）；找不到 ⇒ **整层否决，直接 `absent`** | `absent_number_mismatch` |

**Dice 定义**：`2·|A∩B| / (|A|+|B|)`，A/B 为字符三元组多重集；`len < 4` 时退化为字符集 Dice（由 M3 覆盖）。
**BM25**：仅用其**召回**（不排序、不打分阈值调参），`k1=1.2, b=0.75`，文档长度归一照标准式。

### 1.2 缺席词（沿用，不改）
`未提及` / `没有` / `未找到` / `未说明` / `无相关` / `不存在` / `未记录` / `未包含` 等 22 变体（词表冻结，来自 `JUDGE-ROBUSTNESS-SPEC.md`）。
命中缺席词 ⇒ `absent_declared`。

### 1.3 三级结论（**关键结构改动**）

| 组合 | 结果 | 说明 |
|---|---|---|
| M1–M4 任一命中 | `present` | 该条依据可核 |
| M5 否决 | `absent` | 数值/实体对不上，**无论文本多像** |
| 缺席词命中 | `absent` | 模型自认没有 |
| 全部未命中，且 `len(evidence) ≥ 4` | `absent_fabricated_evidence` | 模型声称逐字复制却查无此文 ⇒ **视为编造依据** |
| 全部未命中，且 `len(evidence) ≤ 3` 且不含数字/实体 | **`unverified`** | **新增格**：短词改写无法判定，既不算有据也不算编造 |

**`unverified` 的句子级后果**：该条不计入 absent，但句子**不得**判 `supported`；若句内存在 `absent*` 条目仍按 `unsupported`；若**全部条目都只是 `unverified`** ⇒ 句子判 `undecidable`（**不判 unsupported，也不判 supported**）。

> 依据：`unverified` 只对**≤3 字的短词**开放，且已被 M5 数值否决权挡在前面，因此**不会**把"打包纸箱""五年保修"这类长实词编造放过去（它们必然走 `absent_fabricated_evidence`）。

## 2 聚合策略

- **主口径 `policyA = any_absent`**：句内任一条目 ∈ {`absent*`} ⇒ `unsupported`（**与 rev5.1 一致，唯一有效口径**）
- 次要口径 `policyB = half_absent`：`absent` 条目占比 ≥ 1/2 ⇒ `unsupported`；否则若全为 `unverified` ⇒ `undecidable`（**纯披露，不参与过/不过**）

## 3 验收指标（阶段 A：设计集，非验收）

在 `(b4)` rev6 已落盘输出上重算，**门槛先定死**：

| 指标 | 门槛 | rev5.1 基线 |
|---|---|---|
| 误判数 | **≤ 4/46** | 7/46 |
| 误判中 `absent_fabricated_evidence` 误判数 | **≤ 2** | 7 |
| 漏判数 | **不恶化：≤ 5/41** | 4/41 |
| `unverified` 占比 | **≤ 15%**（过高说明核验器退化成"都不敢判"） | 0% |

任一不过 ⇒ `rev6_1_unusable=true`，**停**，回报 LEAD，**不许调阈值重跑**。

## 4 交付

`m5/out/M5C2-REV6-1-OFFLINE.json`（零 GPU，`n_forward=0`）
- 顶层：`rev6_1_ver=1`、`n_sentences=261`、`n_forward=0`、`design_set=true`、`not_acceptance=true`、`prereg_sha16`、
  `b4_items_source_sha16`（读的是哪份 rev6 输出）
- 逐条：`{sid, entry, evidence, matcher_hit(M1..M5/absent/unverified), dice, bm25_recall, numeric_ok, item_verdict}`
- 逐句：`{sid, items[], n_absent, n_unverified, verdictA, verdictB, verdict_rev5_1_baseline}`
- 读数：误判/漏判数与明细、`false_by_reason`（M1–M4 / M5 / fabricated_evidence / declared）、`unverified` 占比、
  **rev5.1 与 rev6.1 的逐句对照（谁修好了、谁被改坏了，必须都列）**

## 5 纪律

- **纯确定性**：不许调用任何模型（含 14B 与任何 NLI）；不许联网
- 阈值、词表、Dice/BM25 公式**冻结**；看到结果不许回头调
- 不许改 rev6 的 #抽取输出；不许改金标；不许删例
- `(b5)` 不得用于本阶段任何调参

## 6 状态

`frozen=true` / `frozen_rev=1` / `executed=false` / `needs_gpu=false` / `depends_on=M5C2-REV6-B4DESIGN.json`