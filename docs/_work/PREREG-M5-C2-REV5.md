# PREREG-M5-C2-REV5 —— 离线重判：R4+ 证据存在性 / derived 算术可组合性

> `frozen=true` · `frozen_rev=1` · `frozen_at=2026-10-26T17:55:00+08:00` · 冻结人：LEAD
> 前置：`PREREG-M5-C2-B2EVAL.md 6b0d750abbd06b1b`（读数 `M5C2-B2EVAL.json 553a96fc481fcf9c`）
> **本件零 GPU**：复用已保存的模型抽取输出，只重跑第 2 层确定性裁决

## 0 本轮要修的两个缺陷（都是 LEAD 的规则错，模型无责）

### 0.1 R4 写窄 ⇒ 打包纸箱 9/9 全漏
`M5C2-B2EVAL.json` 中 9 句 "搬家公司可以帮忙打包纸箱"：模型给的 `依据` 是 `打包纸箱`，
**该文本在 s4 源文中不存在**，但原 R4 只校验"引号内片段"，模型未打引号 ⇒ 逃过校验 ⇒ 判 supported ⇒ 漏判。

**修复 R4+**：对**每一条 `evidence`**（不限引号）执行：
1. 若命中缺席词表（R3）⇒ 走 R3；
2. 否则要求 evidence（归一化后）在 `source` 中**逐字存在**，或与源文某窗口的**字符二元组覆盖率 ≥0.80**；
3. 两者皆不满足 ⇒ `absent=true`，`reason="fabricated_evidence"`。

### 0.2 derived 旁路太粗 ⇒ 搬运师傅人数 12/12 全漏
原规则：句子含 `共|总共|合计|一共|平均|最|加起来` ⇒ 强制 `undecidable`。
实测 12 句 "一共(有)两个搬家师傅" 被一律 undecidable；模型实际抽出 `两个人 → 未提及`（本应 unsupported）。

**修复 `R_DERIVED+`（算术可组合性）**：句子含上述词时：
1. 提取句子中全部数值 token（阿拉伯数字 + 中文数字 一二三四五六七八九十百千两半）；
2. 对每个数值 `v`：若 `v` 出现在源文数值集合中 ⇒ 视为可核；
   否则若存在源文两数 `a,b` 使 `v ∈ {a+b, |a-b|, a*b, a/b, b/a}`（允许 ±1 舍入、允许单位换算 元/千元）⇒ 视为可组合；
3. **全部数值都满足** ⇒ `undecidable`（合法推理，禁判 unsupported）；
4. **任一数值不满足** ⇒ **不启用旁路**，走正常 R1–R4 裁决（该数值即 `value_mismatch` ⇒ unsupported）。

### 0.3 自曝：floor 用例 D1-3 本身写错
`PREREG-M5-C2-REV4-1.md` §2 D1-3：源文 `宽带月费100 + 健身房月费268 = 368`，句子却写 `780`。
**该例实为编造，不是合法推理，期望值 `undecidable` 是错的**。本轮按 `R_DERIVED+` 它应被判 `unsupported`。
D1-1（480+480=960）、D1-4（100+268=368）仍为合法推理，应 `undecidable`。

## 1 方法：离线重判（`reused_model_output=true`）

- **输入**：`M5C2-B2EVAL.json 553a96fc481fcf9c` 中 106 句的 `items[]`（模型抽取结果，**不重新生成**）
- **操作**：仅重跑第 2 层（R1 / R2 / R3 / **R4+** / **R_DERIVED+**），产出新 verdict
- **不变量**：`prompt_sha16=a6bc4f268f7711de`、`n_forward=0`、模型输出字节不变
- **限制（写死）**：`repeated_look_at_b2=true`、`in_sample_for_leak_templates=true`、`not_acceptance=true`

> 说明：本轮改的是**确定性裁决层**，不是模型。复用已存抽取输出是唯一能做到"规则变、模型不变"的方式；
> 但**同一批 b2 数据被第二次用于调规则**，因此必须记为 `repeated_look_at_b2=true`，**不得作为能力结论**。

## 2 预期（先写下，防事后编故事）

| 组 | 现状 | 修复后预期 |
|---|---|---|
| 打包纸箱 9 | 漏 9 | 抓 9（R4+ 命中 fabricated_evidence） |
| 搬运师傅 12 | 漏 12 | 抓 12（数值不可组合 ⇒ 正常裁决 ⇒ unsupported） |
| 材料清单 3 / 姓张 1 / 天气 1 | 已抓 | 保持抓到 |
| 误判 8 | 11.27% | 不变（本轮不动抽取与支持侧规则） |

**若修复后漏判未降到 ≤10/35，说明规则方向仍有问题，停下来报 LEAD，不再连改。**

## 3 判定

- 打包纸箱组 ≥8/9 且 搬运组 ≥10/12 ⇒ `rev5_rules_hold=true`
- 否则 ⇒ `rev5_rules_hold=false`，记录未命中例与规则痕迹，**停**。
- **无论结果如何，本件都不构成验收**；验收须 `(b4)` 全新样本集。

## 4 交付

`m5/out/M5C2-REV5-OFFLINE.json`：
- 顶层：`reused_model_output=true`、`n_forward=0`、`repeated_look_at_b2=true`、`not_acceptance=true`、
  `rules_version="R4+/R_DERIVED+"`、修复前后对照
- 逐句：`{sid, gold, verdict_old, verdict_new, items[], rule_hits[{rule,reason,span}]}`
- 读数：漏判率、误判率、`strict_leak`、4 模板分组、12 条 derived 明细
- D1-1~D1-4 重判结果（D1-3 应改判 unsupported，须显式记录）

## 5 纪律

- **禁止**重新调用模型（`n_forward` 必须为 0）
- **禁止**改抽取 prompt、改 R1/R2/R3
- **禁止**为个别 sid 写特例分支
- 不碰 GPU、不碰 git；LF；只追加

## 6 状态

`frozen=true` / `frozen_rev=1` / `frozen_at=2026-10-26T17:55:00+08:00` / `executed=false` / `needs_gpu=false`