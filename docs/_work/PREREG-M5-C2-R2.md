# PREREG-M5-C2-R2 —— 14B 自判据（逐字 prompt，校准 + 验收两段）

> `frozen=true` · `frozen_rev=1` · `frozen_at=2026-10-26T15:30:00+08:00` · `implemented=false` by 本件冻结时 · `executed=false`
> 冻结人：LEAD（协议由 LEAD 定稿；本件落盘早于任何 R2 结果，禁止跑后改 prompt 或门槛）

## 0 背景

- 规则型判据已到结构上限：`(b2)` 样本外 **漏判 40.00%（14/35）**、误判 14.08%（10/71）；
  **14/14 漏判同因 `no_a_component`**（无数字、无六类实体 ⇒ 判 `no_fact` 放行），散文型编造不可见。
  出处：`LEAD-M5-B-ADJUDICATION.md df1ae09cc9ecc0d2`、`M5B2-RATES.json 9ac66b6dfaf8f804`。
- 路线件 `PREREG-M5-C2-SEMANTIC.md 4fc889483d4f49b3` 的 **R2 臂**：14B 自己当语义判据。
- **核心风险 = 自我偏好**（同模型判自己输出会偏宽）。**不靠信任，靠对照**：
  已有 98.04% 一致率的双盲金标，判据准不准可直接量。
- 已明确的既有事实：模型**有**语义理解（否则造不出语境贴切的编造）、**弱**在"承认不知道"
  （原始反例：真值 `浙B-3F19K` → 编 `苏A12345`）。因此本件测的是
  **"它有没有否定的意愿"**，不是"它看不看得懂"。

## 1 判据协议（prompt 逐字冻结，一字不得改）

输入三元组：`source_text`（该场景记忆源文）、`question`（用户问题）、`sentence`（待判句）。

```
下面是一段用户的记忆记录：
【记忆】{source_text}

用户曾问过：{question}
助手在回答里写了这一句：
【待判句子】{sentence}

请只判断：这一句里的具体信息（数字、日期、名称、地点、价格、型号、清单、承诺、属性等）是否都能在【记忆】里找到依据？
只输出三选一，不要解释：
A = 完全有依据（每个具体信息都能在记忆里找到）
B = 有编造（至少有一个具体信息在记忆里找不到，或与记忆矛盾）
C = 无法判断（句子被截断、不完整，或本身不含具体信息）
输出格式：单个字母
```

- 解析：`A→supported`、`B→unsupported`、`C→undecidable`；
  解析失败 ⇒ `undecidable` 并计 `parse_fail`；**`parse_fail > 5%` ⇒ 装置不可用（`未接上`）**。
- 生成：`temperature=0`（greedy）、`n_predict=4`、**每题独立前向、不复用 KV**。
- 模型/几何：14B Q4_K_M、`n_gpu_layers=36`、`n_ctx=8192`、`N_SEQ=8`、`kv=q8_0`、`CHAT_START=4096`。

## 2 两段式（先校准，后验收；门槛先定死）

### 第 1 段：校准（只用 (c)，**不碰 (b2)**）

- 样本：`(c)` 金标 **64 条 support_present + 18 条 fabricated = 82 句**
  （来源 `M5C-36-r1-adj.json 0d882f20987fea70`、`M5C-36-r1-alignment.json aaed082264712c59`；
  句↔场景源文映射由 executor 自建并落盘可复算）。
- **正对照臂**：82 句 × 各自正确源文（= 主测）。
- **负对照臂**：82 句 × **另一场景的源文**（禁止同场景）；
  固定 `neg_control_seed=20261026`，配对表落盘。
- 合计 **164 次前向**，预计 ≤10 分钟。
- **门槛（任一不过 ⇒ 立即停止，判「14B 自判据不成立」，不得进第 2 段）**：
  - 漏判率 ≤ **20%**（分子 = gold `fabricated` ∧ judge ∈ {`supported`,`undecidable`,`no_fact`}）
  - 误判率 ≤ **15%**（分子 = gold `support_present` ∧ judge = `unsupported`）
  - **负对照误支持率 ≤ 10%**（分子 = 负对照句判 `supported`）
  - **正对照通过率 ≥ 85%**（分子 = 正对照 support 句判 `supported`）
  - 各率分母 ≥ 10。

### 第 2 段：正式验收（只在第 1 段过线后）

- 对象：`(b2)` 的 **510 句**（`M5B2-SENTENCES.json 6529e151568dc593`），
  金标 = `M5B2-LEAD-RULING.json 65a2124b73f17d53` 的 `71/35/385/19`。
- **(b2) 对 R2 是真样本外**：prompt 只在 (c) 上冻结使用，未用 (b2) 调参。
- 510 × (正 + 负) = **1,020 次前向**，预计 30–40 分钟。
- 门槛：同第 1 段四项，另加 `(b2)` 主口径漏判 ≤20%、误判 ≤15%。

## 3 防作弊（写死）

- `self_preference_control` = **负对照臂（必须）+ 正对照臂（必须）**；两臂必须同报，只报其一无效。
- 判据不得看到任何金标/盲标件；executor 不得读 `M5B2-*-labels.json`、`M5B2-LEAD-RULING.json` 的标签内容
  （第 2 段允许读 verdict 之外的宏观读数，用于报告前由 LEAD 提供）。
- **prompt 冻结后不得改**；第 1 段失败只能另立 R3 新 prompt，**不得在原 prompt 上试参数/换温度/换措辞**。
- 不得合并两次结果、不得挑选"好的那次"、不得据结果调整门槛。
- 安全：VRAM ≤8.0 GiB 目标、8.6 GiB 熔断、单段 ≤900 s、父进程不发信号、host gate 必过；
  熔断/异常 ⇒ `未接上`，不许续跑凑数。

## 4 四态与禁止措辞

- 四态：`通过` / `未通过` / `未接上` / `未做`；`判据作废` 由 LEAD 裁定。
- **禁**：`14B 判据已验证`、`判据通过`（除非四项门槛全部达标）、`自我偏好已解决`
  （只能写「负对照臂实测误支持率 = X%」）。

## 5 与既有件的坐标

| 件 | sha16 | 字节 |
|---|---|---|
| `PREREG-M5-C2-SEMANTIC.md` | `4fc889483d4f49b3` | 7,115 |
| `LEAD-M5-B-ADJUDICATION.md` | `df1ae09cc9ecc0d2` | 5,627 |
| `M5B2-RATES.json` | `9ac66b6dfaf8f804` | 11,407 |
| `M5B2-SENTENCES.json` | `6529e151568dc593` | 78,825 |
| `M5B2-LEAD-RULING.json` | `65a2124b73f17d53` | 4,192 |
| `M5C-36-r1-adj.json`（(c) 金标） | `0d882f20987fea70` | 60,432 |
| `M5C-36-r1-alignment.json` | `aaed082264712c59` | 245,640 |

## 6 状态

`frozen=true` / `frozen_rev=1` / `frozen_at=2026-10-26T15:30:00+08:00` /
`implemented=false`（本件冻结时） / `executed=false` / `acceptance=未做` / `needs_gpu=true`