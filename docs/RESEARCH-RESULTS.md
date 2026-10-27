# RESEARCH-RESULTS — M5C2「记忆接地判据」研究线结论（负结果，已封版）

> **件性质**：研究线**最终结果**。面向三类读者：当时的我、半年后的我、外部审阅。
> **权威口径**：本文件所有数字均引用**冻结件 sha16**；与冻结件冲突时以冻结件为准。**研究线已封闭，不再开新数据集、不再修 rev7.x。**
> **隔离声明**：C 版产品可用性（`C-PRODUCT-ACCEPTANCE`）与本文的研究结论**严格分开**，不得互引。
> 生成：2026-10-27（CPU、只读、零 GPU）。

## 0 一句话结论（逐字引自冻结 supplement）

> **`M5C2-B7-VERDICT-SUPPLEMENT.json` = `a58c3c87393a5b0c` / 3,871 B**，其 `headline_reframed` 原文：
>
> b5 = 擦边；b6 = 未接上（样本量不足）；b7′ = 擦边。rev7.2 在唯一独立测试上的误判操作点为 22/147 = 14.97%（Wilson 95% CI 上界 21.62%），与上一版 rev7.1 在两个独立样本上的合并操作点 22/141 = 15.60%（CI [10.54, 22.50]）在统计上不可区分；而 H1 的 CI 门槛要求判据操作点 ≲12.70%（n→∞ 上限）。因此本判据在当前设计下不可达标，此结论不由样本量决定，也不由 dev 集读数（2.78%）支撑——dev 与 test 的 5.4 倍差距是『在 b5 上调机制』的过拟合实证，故 b5 不得再作任何 H1 证据。

**rev7.2 是判定层最后版本**（裁定 `RULING-M5C2-B7.md` = `3dfafd1253f0a833`，R10：b7 之后不再改判据；不得重跑 b7′）。

## 1 三数据集判定表（两率 + Wilson 95% + 结论）

| 数据集 | 判据层 | 误判 FP（Wilson 95%） | 漏判 leak（Wilson 95%） | 四态结论 |
|---|---|---|---|---|
| b5（dev） | rev7.1 | **9/72 = 12.50%**（[6.72%, 22.08%]） | **0/29 = 0.00%**（[0.00%, 11.70%]） | **擦边**（点估计在线内、FP 上界越 15%） |
| b6 | rev7.1 | 13/69 = 18.84%（诊断值；[11.35%, 29.61%]） | 1/17 = 5.88%（诊断值；[1.05%, 26.98%]） | **未接上**（leak 分母 17 < 20，§6 门槛不满足，不得给两率判定） |
| b7′（唯一独立测试） | rev7.2 | A 读 **22/147 = 14.97%**（[10.10%, 21.62%]）；B 读 21/147 = 14.29%（[9.54%, 20.85%]） | A 读 **10/62 = 16.13%**（[9.00%, 27.21%]）；B 读 11/62 = 17.74%（[10.21%, 29.04%]） | **擦边**（两读同档；点估计均在线内、Wilson 上界均越线） |

**关键对照**

- rev7.1 合并两独立样本：**22/141 = 15.60%，CI [10.54%, 22.50%]**（supplement `rev7_1_combined`），与 rev7.2 的 14.97% **统计上不可区分**。
- H1 可行界：Wilson 上界 ≤15% ⇒ **n→∞ 时点估计上限 ≈12.70%**；现操作点 ≈15% ⇒ **差约 2.3 pp，样本量只能缩 CI，不能移动操作点** ⇒ **不可达标属能力上限，非样本量不足**。
- b5 dev 读数 **2/72 = 2.78%** 不得引用为能力证据（过拟合实证，×5.4）。

## 2 分母与池口径（必须随两率一起读）

- b7′ gold 总计：`support_present 148 / fabricated 63 / no_fact 380 / undecidable 32`（623 句）。
- **layer0 42 句单列**：`abstain_check` 短路、与 forward 不同构，两率池**排除**（gold 混合 = 1 support + 1 fabricated + 40 no_fact）；**纳入版敏感性** 148/63 与排除版 147/62 结论不变（A 读 14.86%/15.87%；B 读 14.19%/17.46%，上界均越线）。
- 分母门槛：b7′ n_fp=147、n_leak=62 均 ≥20/25 ⇒ 可判；b6 leak=17 <20 ⇒ 只能记「未接上」。
- 句级口径：623 句含 layer0；两率池 = 581 句（`M5C2-B7-READINGS.json`）。

## 3 证据链（冻结件 sha16；字节数见括号）

| # | 环节 | 件（sha16） |
|---|---|---|
| 1 | 题面 | `M5C2-B7-QUESTIONS.json` `f1f059539453d562`（15,964）；pin `M5C2-B7-QUESTIONS-FREEZE.json` `1baeda859bc05549` |
| 2 | 生成 | `M5C2-B7-GEN.json` `041b51eb7837aa90`（140,514） |
| 3 | 切句 | `M5C2-B7-SENTS.json` `c5a49a696b66f0c7`（288,805）；pin `60b369bf8cfcef2b` |
| 4 | 盲标 | A `M5C2-B7-BLIND-A.json` `50d1b6da781e2c3b`（37,632）；B `M5C2-B7-BLIND-B.json` `d8e51d652c4e333f`（40,023） |
| 5 | gold | `M5C2-B7-GOLD.json` `d5726d9cc59bb6f6`（110,099）；pin `19a6a653f86f6b01` |
| 6 | 抽取 | `M5C2-B7-EXTRACT.json` `2804fbbb26bff2a3`（951,539）；说明 `73118d5da940c506` |
| 7 | 不变性 | `M5C2-B7-INVARIANCE20.json` `a1d928df8affc5aa`（20/20 逐字节相同） |
| 8 | 合并核 | `M5C2-B7-MERGE-CHECK.json` `6048139a67876f99`（v3；v2 `b599a62d5a1a74d0`） |
| 9 | 溯源 | `M5C2-B7-PROVENANCE-V2.json` `96cd4bfe8df05185` |
| 10 | 判定 | `M5C2-B7-DECIDE.json` `adaf010425a4f30d`（1,863,426） |
| 11 | 宽读法敏感性 | `M5C2-B7-WIDE-SENSITIVITY.json` `3e46633a6b27a561`（854,236） |
| 12 | 读数 | `M5C2-B7-READINGS.json` `15190c2e53137905`（15,100）；pin `529915a667f7dbe6` |
| 13 | 判定书 | `M5C2-B7-VERDICT.json` `1cb7a7961aefe0c6`（4,165）；pin `686f0ac963b1226d`；supplement `a58c3c87393a5b0c` |

审计与治理：读数审计 `e7ad14a9b576a442`（+补充 `f2222c3d6da5498e`）；独立 inspector `9de882c8492ef717`、S5 v2 `ee0abc1cad05c935`；裁定 `3dfafd1253f0a833`；中止裁定 `335a74c0a443b919`（pin `3458091481ebc50e`）；judge 冻结 `M5C2-REV7-2-FREEZE.json` `87a13b0c9aeae083`；脚本冻结 `558fd9aa28ad691c`。

## 4 必须披露的六件事（不带这些读两率会误判）

1. **dev→test ×5.4**：b5 dev 2.78% → b7′ 14.97%，差距是「在 b5 上调机制」的过拟合实证；**b5 永久 dev**，不得再作任何 H1 证据。
2. **读法敏感**：A（narrow）与 B（wide）FP 22 vs 21、leak 10 vs 11（diff n=11）；**A 读法漏报 1 例编造**（`b5-s4-q1-s01`，gold=fabricated）；**B 读法多检 2 句、其中 1 例为真漏判**（A4 固定句）。headline 取 A_narrow，但 B 同档 ⇒ 不降级。
3. **M4 残差未修**（`fixed=false`）：推断/否定类未纳入 rev7.2（R2）；b5 示例 `b5-s8-q1-s06`、`b5-s8-q4-s09`；b7′ 漏判行 10 条逐 sid 列于 verdict `m4_residual_disclosure`，**不剔除、不作废**。
4. **cosmetic 3 条**（不影响读数）：decide 脚本末段 `print` 用旧键致 exit=1（artifact 完整）；wide 脚本自带 `diff_vs_decide.n_diff=623/diff_sids=[]` 与其 verdicts 实差 11 不符（统计字段 bug）；readings 的 `fp_reading_caveat.caveat` 字符串拼出「>15%」字样但 `exceeds_threshold=false` 正确。
5. **timeout 归因**：extract 曾 `aborted=timeout >3600s`、`abort_class=timeout_mid`、exit=3；**属 `timeout_limit_underestimated`（计划错误，非装置故障）**——实测 8.99 s/句 × 623 句 ≈ 5,602 s > 3,600 s 限值；属脚本自身超时分支的 graceful return，非外部 kill；boot_id 前后一致、无 WATCHDOG/Minidump；resume exit=0 后合并完成。
6. **可证伪性**：验器对 C1（篡改抽检样本）/C2（layer0 计数）/C3（exit/boot_id 篡改）三注入均 `fail_detected` ⇒ 不是「只验能过」。

## 5 为什么这是一个有价值的负结果（1 段）

它把一个**看似接近达标**的判据钉死为「能力上限问题」：b7′ 点估计 14.97% 距 15% 只有 0.03 pp，若只报点估计，半年后的人一定会误以为「再补点数据/再修几条规则就能过」。但把 Wilson 上界、rev7.1 合并区间（[10.54,22.50]）、n→∞ 可行界（12.70%）与 dev→test 的 5.4 倍差放在一起，结论只能是**操作点 ~15% 高于 H1 能容纳的 ~12.70%**，样本量无法解决；且 b5 被用过一次即永久失效，这正是「一次性验收集＋先冻题面后冻判据」纪律的价值所在。**负结果的可复算性、可证伪性与披露完整性，本身就是交付物。**

## 6 禁语与判定禁述

**禁语四条**（冻结 supplement `banned_phrases`，出现即视为结论失真）：

1. 接近达标；
2. 就差一点；
3. 样本量不足导致；
4. 再多一点数据就能过。

**判定禁述**（verdict `prohibitions`）：不得写「通过」；不得写「未通过」（b7′ 点估计未越线）；擦边不得事后改解释为达标；不得用 b5 dev 2.78% 论证能力；不得据此重跑 rev7.2。

## 7 复算入口（任何一条都可独立验证）

```bash
cd /d/llama-mem
sha256sum kvmem/m2_visibility/m5/out/M5C2-B7-VERDICT.json \
          kvmem/m2_visibility/m5/out/M5C2-B7-VERDICT-SUPPLEMENT.json \
          kvmem/m2_visibility/m5/out/M5C2-B7-READINGS.json
python -X utf8 -c "import json;d=json.load(open('kvmem/m2_visibility/m5/out/M5C2-B7-VERDICT.json'));print(d['verdict'],d['readings']['A_narrow'])"
```

**读者路径**：先读 §0/§1 → 再看 §4 披露 → 需要细节时按 §3 表定位冻结件；**不要**从旧 PROGRESS 长文里找结论（旧文正被归档，且含已被本结果取代的中间口径）。