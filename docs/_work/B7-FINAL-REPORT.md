# B7-FINAL-REPORT（b7′ 收口报告 · 2026-10-27）

> 唯一结论来源：`M5C2-B7-VERDICT.json 1cb7a7961aefe0c6/4165`（pin `686f0ac963b1226d`）+ `M5C2-B7-VERDICT-SUPPLEMENT.json a58c3c87393a5b0c`（v2，headline 见 §1）。
> 三数据集总表、证据索引、披露、下一步，均以本件为准。

## 1 Headline（对外一句话版）

> **b5 = 擦边；b6 = 未接上（样本量不足）；b7′ = 擦边。rev7.2 在唯一独立测试上的误判操作点为 22/147 = 14.97%（Wilson 95% CI 上界 21.62%），与上一版 rev7.1 在两个独立样本上的合并操作点 22/141 = 15.60%（CI [10.54, 22.50]）在统计上不可区分；而 H1 的 CI 门槛要求判据操作点 ≲12.70%（n→∞ 上限）。因此本判据在当前设计下不可达标——此结论不由样本量决定，也不由 dev 集读数（2.78%）支撑。**

**dev 与 test 的 5.4 倍差距（2.78% → 14.97%）是"在 b5 上调机制"的过拟合实证；b5 自此永久降为 dev，不得再作任何 H1 证据。**

## 2 三数据集总表

| 数据集 | 判据 | 误判（FP） | 漏判 | 结论 |
|---|---|---|---|---|
| b5（8×5=40 题，326 句） | rev7.1 | 9/72 = 12.50%（hi 22.08%） | 0/29 = 0%（hi 11.70%） | 擦边 |
| b6（8×5=40 题，233 句） | rev7.1 | 13/69 = 18.84%（hi 29.61%）可测且越线 | 1/17 不可测（分母<20） | 未接上（样本量不足）；FP 分量指向未通过 |
| **b7′（15×5=75 题，623 句）** | **rev7.2** | **22/147 = 14.97%（hi 21.62%）** | **10/62 = 16.13%（hi 27.21%）** | **擦边**（两读一致） |

- b7′ 池：gold 148/63，排除 layer0 42 句（含 1 support + 1 fabricated）⇒ n_fp=147、n_leak=62；
- layer0 纳入版（148/63）：A FP 22/148=14.86%（hi 21.48）、漏判 10/63=15.87%（hi 26.81）；B 21/148=14.19%（hi 20.72）、11/63=17.46%（hi 28.62）——**两版均擦边，档位鲁棒**。

## 3 可达界论证（为什么不是"差一点"）

- H1 规则：两率 Wilson 95% 上界 ≤15% / ≤20%；
- `n_fp→∞` 时可过最大点估计 **12.70%**；n=147 时达标需 **FP ≤13/147=8.84%**；n=62 时漏判需 ≤6/62=9.68%；
- rev7.2 操作点 ≈15%，与 rev7.1 合并 15.60% 不可区分 ⇒ 差 ~2.3 个百分点，**样本量不能移动操作点**；
- 禁语：不得写「接近达标」「就差一点」「样本量不足导致」「再多一点数据就能过」。

## 4 完整证据链（b7′）

| 阶段 | 件 | sha16 |
|---|---|---|
| 题面冻结 | `M5C2-B7-QUESTIONS.json` / pin | `f1f05953` / `1baeda85` |
| 生成 | `M5C2-B7-GEN.json` | `041b51eb`（75/75、peak 8.1819、一次性消耗） |
| 切句 | `M5C2-B7-SENTS.json` / pin | `c5a49a69` / `60b369bf`（623 句） |
| 盲标 A/B | `M5C2-B7-BLIND-A/B.json` | `50d1b6da` / `d8e51d65`（一致 597/623=95.83%） |
| gold | `M5C2-B7-GOLD.json` / pin v2 | `d5726d9c` / `19a6a653`（148/63） |
| gold 复核 | `M5C2-B7-GOLD-REVIEW.json` | `f8aa4bfb`（25 agree/1 采纳改判） |
| 抽取 | EXTRACT / shard1 / shard2 | `2804fbbb` / `0b604a01` / `be8d4611`（n_forward 581、layer0 42） |
| 等价性 | INVARIANCE20 / MERGE-CHECK v3 | `a1d928df`（20/20）/ `6048139a`（59/59 + falsifiability 3/3） |
| provenance | PROVENANCE-V2 | `96cd4bfe`（records 不变） |
| 判定 | DECIDE / WIDE / READINGS | `adaf0104` / `3e46633a` / `15190c2e` |
| 独立审计 | READINGS-AUDIT / SUPPLEMENT | `e7ad14a9` / `f2222c3d` |
| 终检 | INSPECTOR-S5 v2 | `ee0abc1c`（①–④ pass） |
| 结论 | VERDICT / SUPPLEMENT v2 | `1cb7a796` / `a58c3c87` |

## 5 披露（必须随结果件）

1. dev→test：2.78% → 14.97%（×5.4），b5 永久 dev；
2. 读法敏感：A/B 并列，A 漏报 1 例（`b5-s4-q1-s01`）、B 多检 2 句含 1 真漏判；b7 diff 11（7 loose / 4 strict）；
3. layer0：42/623（19+23）abstain_check 单列、两率池排除；纳入版并列，结论不变；
4. M4 残差未修（b5 两例 + b7 漏判 10 例逐 sid 保留、不剔除）；
5. cosmetic 3 条：decide 摘要 KeyError、WIDE diff 字段 stale、AUDIT A4_4b 文案；
6. timeout 归因 `timeout_limit_underestimated`（非装置故障）；resume 峰值 8.5753 GiB（<8.6 fuse、>8.0 目标）；
7. MERGE-CHECK 可证伪：C1/C2/C3 三组负例均 fail_detected、restored_pass。

## 6 为什么这是有价值的负结果

它把"判据不行"从猜测变成可复核的算术：两版判据在三个独立样本上的操作点都停在 14.9–15.6%，而设计门槛要求 ≲12.7%。这否定了"再修几个规则/再加些数据就能过"的路线，并给出唯一两条合法后继：
1. **改测量**（零 GPU 受控注入，测漏检率，`diagnostic_only`）；
2. **改判据设计**（换范式，如强制 span 对齐；新预登记 + 新数据集）。

两条都不应现在做——先把这份干净的负结果写扎实。

## 7 状态

- rev7.2 = 最后一个判据版本（R10）；b7′ 失败即停，不开 b8；
- 文档已同步（PROGRESS §13.35 `399a5ce1`、README `40a4efb1`、PROJECT-STATE `e3270ec7`、FEATURES `d32ba7e2`、ARTIFACTS-KEY `35767078`、INDEX `ae6142c9`）；
- 台账 `M5C2-B7-ATTEMPTS.json` 待补 MERGE v3 / INSPECTOR v2 终值（`a3d51487` 为当前版）；
- 未 commit；C 版产品线与本研究结论严格隔离（见 `C-PRODUCT-ACCEPTANCE.md`）。
