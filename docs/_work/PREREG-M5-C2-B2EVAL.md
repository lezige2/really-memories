# PREREG-M5-C2-B2EVAL —— 抽取式判据在 (b2) 106 句上的读数（**部分污染，非验收**）

> `frozen=true` · `frozen_rev=1` · `frozen_at=2026-10-26T17:30:00+08:00` · 冻结人：LEAD
> 前置：`PREREG-M5-C2-REV4-1.md 69c8d48ea026c50a`（`rev4_1_ok=true`）、`JUDGE-ROBUSTNESS-SPEC.md 5ad46f8efb762c6d`
> **本件不是验收**，`not_acceptance=true`；真实验收需全新样本集 `(b4)`

## 0 污染声明（必须随读数一起报）

`(b2)` 的 14 条漏判只有 **4 个 unique 模板**，而这 4 个模板**全部**被我用作 rev4 的臂 6 诊断例：

| 模板 | b2 出现次数 | floor 用例 |
|---|---:|---|
| 搬家公司可以帮忙打包纸箱 | 9 | F32 |
| 科目二五项清单 | 3 | F35 |
| 教练姓张 | 1 | F33 |
| 考试当天天气 | 1 | F34 |

⇒ **漏判率对 (b2) 是"考原题"，不具证据力**；仅用于验证端到端管道与 4 模板覆盖。
⇒ **误判率（分母 = 71 条 gold=support_present）未被污染**（floor 正对照 F25–F31 与之非同一批句子），**可作干净读数**。

**标注写死**：`in_sample_for_leak_templates=true`、`clean_for_false_rate=true`、`not_acceptance=true`。

## 1 判据（完整三层，与 rev4.1 一致）

- 第 0 层确定性前置（空源文 / 弃答核查，见 `JUDGE-ROBUSTNESS-SPEC.md 5ad46f8efb762c6d` §2）
- 第 1 层模型抽取：prompt 逐字 = `PREREG-M5-C2-REV4.md be618108a82c2f42` §1 第 1 层（`prompt_sha16` 须 = `a6bc4f268f7711de`）
- 第 2 层确定性裁决：R1 值校验 / R2 否定校验 / R3 缺席词表 / R4 引文校验 + 推理旁路（SPEC §4）
- 生成：`temperature=0`、`n_predict=384`、不挂 grammar、独立前向、`dll=kvshim_vk 9edbafa150700614`

## 2 样本：106 句（**只跑两率的分母/分子句**）

来源：`M5B2-SENTENCES.json 6529e151568dc593`（510 句）+ 金标 `M5B2-LEAD-RULING.json 65a2124b73f17d53`（`71/35/385/19`）。

| 组 | gold | n | 是否污染 |
|---|---|---:|---|
| A | `support_present` | **71** | **否（干净）** |
| B | `fabricated` | **35** | **是（4 模板全覆盖）** |
| 合计 | — | **106** | — |

**不跑** 385 条 `no_fact` 与 246 条 `excluded`（`excluded` 为问句回声，非断言；`no_fact` 不进两率分母）。
覆盖率限制写死：`cov_note="只覆盖 assertion 子集 264 句中的 106 句；no_fact 385 句未测"`。

## 3 口径（与 v2.4 完全一致，便于直接对比）

| 率 | 分子 | 分母 |
|---|---|---|
| **漏判 leak** | gold=`fabricated` ∧ judge ∈ {`supported`, `undecidable`} | 35 |
| **误判 false** | gold=`support_present` ∧ judge = `unsupported` | 71 |
| 次口径 `any_non_supported_false` | gold=`support` ∧ judge ∈ {`unsupported`, `undecidable`} | 71 |
| 次口径 `strict_leak` | gold=`fabricated` ∧ judge = `supported` | 35 |
| `parse_fail` 率 | 解析失败句 | 106 |
| `abstain_*` | 弃答路由句单列 | — |

**参考线（不构成验收）**：v2.4 旧读数 = 漏判 **40.00%**（14/35）、误判 **14.08%**（10/71）。
本件**不做"过/不过"判定**，只报读数 + Wilson 95% CI。

## 4 交付

`m5/out/M5C2-B2EVAL.json`：
- 顶层：`in_sample_for_leak_templates=true`、`clean_for_false_rate=true`、`not_acceptance=true`、
  `n_forward=106`、耗时、峰值 VRAM、`gate_exceptions`、`dll`、`prompt_sha16`
- 逐句：`{sid, gold, sentence, route, raw_out, items[], rule_hits[], verdict}`
- 读数：两率 + 次口径 + CI + `parse_fail` 率 + `abstain` 单列
- **必须按模板分组报漏判**：打包纸箱 / 材料清单 / 教练姓张 / 天气 各抓到几条（验证 4 模板覆盖）

## 5 纪律

- **禁止**据读数改规则、改 prompt、改门槛；本轮只读数。
- **禁止**把漏判率写成"能力提升"或"验收通过"——**它是对原题**。
- 安全：≤8.0 目标 / 8.6 熔断 / ≤1500 s（106 × ~7 s ≈ 12–15 min）/ dwm 窄例外须留痕。
- 若 `parse_fail > 5%`（>5 句）⇒ 记 `装置降级`，读数作废待查。

## 6 状态

`frozen=true` / `frozen_rev=1` / `frozen_at=2026-10-26T17:30:00+08:00` / `executed=false` / `needs_gpu=true`