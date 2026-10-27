# PREREG-M5-JUDGE-v2.3：成分分级修正（A 级必须覆盖 / B 级只绑定 / 系词白名单）

**状态**：预登记已立，**未实现、未执行、未验收**（`implemented=false` / `executed=false` / `acceptance=未做` / `in_sample_for_v2_3=true` / `theta_calibrated=false`）。
**as-of**：2026-10-26T13:20+08:00。**零 GPU**：只写规则，不改 `m5_ground*.py` 一字节、不跑模型/判据/回归、不碰 git。
**血统**：v2.1 `m5_ground_v2.py` `5e11e1ac06f022c7`/66,413 **冻结**、负责 (a) 既有读数；v2.2 `m5_ground_v2_2.py` `ae5ceea994c05691`/36,005 保留为**已实现诊断件**（`not_adopted`，理由：误伤 41/64）；本件是**另立**的新预登记，`supersedes: 无`。

## 0 为什么需要 v2.3（含 LEAD 的 spec 错误，如实写）

- v2.2 在 `in_sample_replay`（`M5-JUDGE-v2.2-INSAMPLE-REPLAY.json 29a9498f0750ba29/211,198`）上：**抓漏判 18/18（16 条 partial hit 全抓）**，但**误伤 41/64**。
- **根因 = v2.2 预登记 §1 的设计错误**：把 **③关系谓词、④否定词**（尤其系词 `是/为/在`）也列为「必须被 fact 覆盖的可核成分」。系词/谓词是**句法胶水**，不是需要记忆支撑的事实 ⇒ 正确句「我的地址是广陵路12号2单元602」因「是」「地址」未逐字命中被判 `unsupported`。误伤分布：`地址+是` 14、单独 `是` 9、`住址+是` 7、实体 `家庭地址在广陵路` 7（合计 37/41）。
- **纪律**：v2.2 **不得**在看过 (c) 之后回改（回改=数据窥探 ⇒ 该批作废）；v2.3 设计时**已知 v2.2 的 (c) 结果 ⇒ (c) 对 v2.3 同样 in-sample**；v2.3 有效性验收仍须 (b) 层新样本外集（§5）。

## 1 v2.3 判据（成分分级写死；其余沿用 v2.2 实现骨架）

**1.1 分级（核心修正）**
- **A 级「必须覆盖」**：①数词串 ②实体（六模式：`suffix/time/code/plate/loc/obj`）。句中**任一 A 级成分**未被 fact 覆盖 ⇒ 该句 `unsupported`。
- **B 级「只做绑定，不单独要求覆盖」**：③关系谓词（`PREDICATES`）④否定词（`NEG`）。**只用于**：把 A 级成分与谓词绑成语义单元（`停在…`、`住在…`、`不加糖`），并参与**否定极性冲突**判定；**不产生**覆盖要求、不单独决定 supported/unsupported。
- **系词白名单**：`是 / 为 / 在 / 有` 属句法胶水，**永不作成分**（即使 B 级也不进）；`在` **仅**作 `LOC_ENTITY` 的领词（`在+实体`），**领出的实体是 A 级**、`在` 本身不入成分；`到/去/回` 同此（仅领词）。
- 无 A 级成分且无极性冲突 ⇒ `no_fact`（不进两率分母，单列）；对 ADJ=supported 的句仍计**误伤**（已知代价，见 §2）。

**1.2 A 级抽取（沿用 v2.2 `ae5ceea9` 的六模式、顺序与去重；只明写一处改动）**
- 正则/词表/常量**逐字沿用** v2.2：`NUM`(§v2.2:40)、`SUFFIX_ENTITY/TIME_ENTITY/CODE_ENTITY/PLATE_ENTITY/LOC_ENTITY/OBJ_ENTITY`(v2.2:41-47)、`PREDICATES`(v2.2:49-50)、`NEG`(v2.2:51)、`PHRASE_BLOCKLIST`(v2.2:52)、`ORDINAL`(v2.2:53)、`_ENTITY_PREFIXES`(v2.2:132-136)、抽取顺序 `entities→predicates→negation binding→numbers`(v2.2:200-231)。
- **后缀实体前导修剪（v2.3 唯一实体规则改动，写死）**：先按 v2.2 `_ENTITY_PREFIXES` 反复剥；再取匹配串中**最后一个** `STOP_CHARS` 之后的尾段；尾段 <2 字则弃：
```
STOP_CHARS = frozenset("的在是为有我你他她它住停现回到去于和与被把将")
```
  目的：把「家庭地址在|广陵路12号」拆出 `广陵路12号`（v2.2 的 7 条误伤，见 §0）。**不改变**「12号2十单元」为单一后缀实体（串内无 `STOP_CHARS`），故 16 条 partial hit 仍全抓。
- **诚实性声明（LEAD 裁定 1，写死）**：`trimming_rule_motivated_by_in_sample=true`——这条修剪由 v2.2 在 (c) 上暴露的 7 条误伤**直接催生** ⇒ **它使 (c) 更不构成独立验证**；因此 **(b) 层样本外验收不可省、不可免**。
- `LOC/OBJ/CODE` 捕获值命中 `PHRASE_BLOCKLIST` 或以其任一词开头 ⇒ 弃（`在回答…` 类防误抽，沿用 v2.2 块表语义）。
- A 成分记 `(text, kind, span, text_canon)`，`kind∈{num,entity}`；B 成分另记 `(pred, polarity, span)`。

**1.3 B 级绑定与否定极性冲突（B 级唯一硬判据）**
- B 单元 = `(NEG? + PREDICATE + 紧邻 A 成分?)`；对**句子**与**每条 fact** 各跑同一函数，得 `(pred, polarity)`。
- **极性冲突**：句中某 B 单元与 facts 中同 `pred` 的 B 单元 **polarity 相反**（facts 有「只喝美式」而句说「不喝美式」，或反之）⇒ 该句 `unsupported`（`reason=polarity_conflict`，记 `polarity_conflicts[]`）。
- 除极性冲突外，B 级**不**参与覆盖、不单独判 supported/unsupported（只可能 `no_fact`）；**不得**以「B 未命中」为由加规则。

**1.4 覆盖判定（逐字沿用 v2.2:251-258，仅作用于 A 级）**
`c` 被覆盖 ⟺ ∃fact `f`：`c ⊆ f`（`text_canon` 归一后）**或**（`f ⊂ c` 且 `len(f) ≥ len(c) − 1`）。`f⊂c` 放行者单列 `short_fact_cover[]`。

**1.5 句级判定顺序（写死）**
1) 问句 ⇒ `excluded`（同 v2.2）；2) `truncated_tail` 且末 A 成分是贴尾 `num` ⇒ `undecidable`；3) 极性冲突 ⇒ `unsupported`；4) 有 A 且任一未覆盖 ⇒ `unsupported`；5) 有 A 且全覆 ⇒ `supported`；6) 无 A ⇒ `no_fact`。

**1.6 其余沿用 v2.2**：`ORDINAL` 句首序号剥离入 `extraction_fp[]`、`PHRASE_BLOCKLIST`、`short_fact_cover[]`、`branch5_structural_gap[]`、`known_fp_controls` T6–T10/C6–C10 单列不进两率、θ=0.20 固档、2-gram **仅**答案级 `facts==[]`、问句排除。
**1.7 禁**：accuracy/F1/总分；剔除后数字替代原始（原始与剔除后并列）；在 (c) 上调 θ/改词表；回改 v2.2。

## 2 预期与反预期（先声明，防事后解释）

- **预期**：16 条 partial hit 仍**全部抓住**——它们全是 **A 级**未覆盖：`在杭州`=LOC 实体、`地下停车场第2层`=OBJ/后缀实体、`12号2十单元`=单一后缀实体，不含对系词的要求。
- **预期**：误伤从 41/64 大幅下降：`地址+是`(14)、`是`(9)、`住址+是`(7) 由白名单+A/B 分级直接归零；`家庭地址在广陵路`(7) 由 §1.2 前导修剪归零；新增 `no_fact` 类误伤（habit 短句无 A 级成分）。
- **反预期风险（先写）**：①`LOC` 领词把正确句地名误领成 A 级、facts 只有部分词 ⇒ 依赖 `f⊂c 放行`，放行数须如实报；②某误伤若源于「B 级取消后结构性不可判」，**不得**事后加规则（要改 ⇒ v2.4）。
- **可达性预判（in-sample 粗算，非实现/非验收）**：按 §1 规则 + (c) ADJ 标签（64 supported / 18 fabricated）+ 近似 fact 集（三源句 + `review.fact_source.fact_keys` 9 条）在内存中粗算（脚本未落盘）⇒ 16/16 partial hit 全抓；fabricated 中 **17/18** 判 `unsupported`（S3-00 无 A 级 ⇒ `no_fact`，按字面**仍计漏判**，不掩饰）；supported 中 **4 条**变 `no_fact`（S7-R3/R4-10/R8-0/R8-2 的 habit 短句；S7-R3 因 branch5 排除不进率分母）⇒ **预计误伤 4/64（余量 6）**。若**不做** §1.2 修剪（纯 v2.2 保留口径）则 7 条 `家庭地址在广陵路` + 4 条 no_fact = **11/64 > 10 ⇒ 不可达**；故把 §1.2 修剪写死为 v2.3 组成部分，**不作事后调参**。
- **估算声明（LEAD 裁定 2/3，写死）**：上一段的数字是**内存粗算**、脚本**未落盘**（`replay_script_persisted=false`），只作 `estimate_only=true` 的估算——**不得**当作已证结论，也不得当成「已有实现」的证据。
- **验收前置（LEAD 裁定 3，写死）**：`acceptance_depends_on: entity_prefix_trimming`——可接受线（16/16 + ≤10/64）**依赖** §1.2 修剪规则；若该规则被删/被裁掉，按字面 **11/64 > 10 ⇒ 不可达**（此原话保留）。

## 3 与 v2.1 / v2.2 的关系

- v2.1 冻结、负责 (a)；v2.2 已实现但 `not_adopted`（理由：in-sample 误伤 41/64），**不回改**。
- **不得**写「v2.3 更好/已验证」；(c) 是 v2.3 样本内；v2.3 若在 (c) 达标，只说明「复现了设计假设」，**不是**独立验证。

## 4 验收（预先定义，下次实现时照做）

- **可接受线（LEAD 定，写死）**：(c) 重跑（`in_sample_replay` 口径）**16/16 抓 + 误伤 ≤10/64** 才算设计成立；**前置 `acceptance_depends_on: entity_prefix_trimming`**（见 §2）；未达线 ⇒ 立 **v2.4**，**不许调参**。
- **误伤定义**：ADJ=supported 中判非 supported（`unsupported/undecidable/no_fact`）；`no_fact` 子数单列。
- 必过（实现验收）：`selftest`（含 5c/分支5 端到端 + 真实断言）、`known_fp` 10/10 不回归、`--regression` 默认 `write=False`、跑后源件 sha 不变、`_freeze_check` 同时锁 v2.1 与 v2.3 预登记 sha。
- 报告必含：16/16 与误伤数/64、未覆盖句清单、`extraction_fp` 三类是否结构性 0、`short_fact_cover` 计数、`in_sample_for_v2_3=true`、`theta_calibrated=false`。

## 5 样本外集要求（写死）

- 验收集：**(b) 层新事实/新问题**，≥8 题、≥150 句；**不得**复用 (a)/(c) 的题目或事实（新 facet 原文另立件、跑前冻结 sha）。
- 若样本外结果与 (c) 差异大 ⇒ 只说明 (c) 设计输入有偏；**不得**回改 v2.3 规则（回改=数据窥探 ⇒ 该批作废）；要改就另立 v2.4。

## 6 状态、顺序与坐标

- 状态：`implemented=false`、`executed=false`、`acceptance=未做`、`in_sample_for_v2_3=true`、`theta_calibrated=false`；`supersedes: 无`；v2.1 冻结、不回溯 (a)、不在 (c) 上调 θ。
- 顺序：本件落盘 → （用户在場时）K1 100 次真杀 → v2.3 实现 → (c) `in_sample_replay` 对线 → (b) 层样本外验收。

| 件 | sha16 / 字节 |
|---|---|
| `m5_ground_v2.py`（v2.1，冻结） | `5e11e1ac06f022c7` / 66,413 |
| `PREREG-M5-JUDGE-v2.2.md` | `fdf7ca2ae939a3a4` / 9,351 |
| `m5_ground_v2_2.py`（v2.2 实现，`not_adopted`） | `ae5ceea994c05691` / 36,005 |
| `M5-JUDGE-v2.2-INSAMPLE-REPLAY.json` | `29a9498f0750ba29` / 211,198 |
| `_v22_selftest.json` | `f1b061ddcd851f84` / 3,948 |
| `LEAD-M5-C-ADJUDICATION.md` | `60fedd7d4bbf0556` / 10,023 |