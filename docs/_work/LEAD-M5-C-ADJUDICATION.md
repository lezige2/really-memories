# LEAD-M5-C-ADJUDICATION：(c) 36 层长生成探针——裁决记录（判据作废 / 装置可用 / 行为读数有效）

**性质**：LEAD 裁决记录，**不是新实验**。数字由 LEAD 复算，本文件只如实成文并补证据出处；零 GPU（未跑模型、未跑判据、未改任何产物、未碰 git）。
**as-of**：2026-10-26T12:00+08:00（成文时点；裁决 = LEAD 2026-10-26 三方对齐结论）。
**依据**：预登记 `docs/_work/PREREG-M5-C.md` `250dbb41`/14,071（§1 双率字面定义 `:30-35`；四态与作废 `:83-88`）；判据 `m5_ground_v2.py` `5e11e1ac`/66,413（v2.1，θ=0.20 固档，跑后 sha/bytes 未变）。
**数据链**：CAND `ea7a5a5b` → ADJ 盲标 `0d882f20`（封存）→ REVIEW `3666cf58` → JUDGE `9c2d2be5` → ALIGN `aaed0822`（机械核对，不裁决）→ 本裁决。

## 0 最终读数（LEAD 复算，主口径）

**主口径定义**：预登记 §1 字面分子 + consensus 副口径并列 + 排除 `truncated_tail` 与 `branch5_structural` + 排除 `disputed`（6 条已裁定归属，见 §1 R4/R5）。
- **漏判率 = 17/18 = 94.44%**：ADJ=fabricated 的 18 句中，JUDGE ∈ {supported, undecidable, no_fact} 的 17 句。
- **误判率 = 3/61 = 4.92%**：ADJ=supported 的 61 句中，JUDGE ∈ {unsupported, undecidable, no_fact} 的 3 句。
- 两个分母均 ≥10，无需「样本不足」标注；**禁** accuracy / F1 / 加权总分 / 「通过」。

| 口径 | 漏判率 | 误判率 | 出处（现场复算） |
|---|---|---|---|
| **主口径（P，预登记 §1 字面）** | **17/18 = 94.44%** | **3/61 = 4.92%** | `out/M5C-36-alignment.json` `rates.alt_prereg_literal.P` |
| ① consensus(ruled) 副口径 | 17/18 | 3/65 | `rates` 行集 + `counts.consensus`（64/18/6/6）+ R4/R5 后复算 |
| ② 严格口径（**LEAD 派单错写，作废，仅留痕**） | 16/18 | 0/61 | 同件 `rates.P`（分子只算 supported） |
| ③ T 口径（保留残句 10 条） | 17/18 | 3/63 | 同件 `rates.alt_prereg_literal.T` |
| ④ P′（排除 5 条抽取假阳性） | 17/18 | 3/61 | 同件 `rates.alt_prereg_literal.P_prime`（5 条 FP 均不在分母 ⇒ 同值） |

## 1 六条裁定（逐条理由 + 证据）

- **R1/R2 口径以预登记 §1 字面为准**：漏判分子算 `{supported, undecidable, no_fact}`、误判分子算 `{unsupported, undecidable, no_fact}`（`PREREG-M5-C.md:32-33`）。派单里「只算 supported」是 LEAD **写窄了，作废但并列留痕**（上表②）。差异句 = S3-00（JUDGE 抽 0 fact ⇒ `no_fact`，见 `alignment.pending_lead_rulings` R1/R2）。
- **R3 残句口径**：主口径 P **排除**残句；T **并列**；残句 10 条单列。证据：`counts.flags.truncated_tail=10`、`judge.truncated_tail_sentences`（10 条，含 S7-R6/R7/S8-B 等）；T 分母 63 = P 61 + 2 条残句 supported。
- **R4 4 条 `meta_selfcorrection` 判 supported**：「…单元号是2单元，不是2十单元。」（S1 pos5、S7-R1 pos5、S8-A pos5、S8-B pos6，见 `alignment.disputes` type=`meta_selfcorrection`）。理由：其中「2单元」是可核断言、与 home:H4 一致；**否定无来源形式（2十单元）不构成新断言**，故整句不按 fabricated 计。
- **R5 2 条截断数字判 undecidable**：S7-R8「…广陵路1」、S8-B「…广陵路 1」（`alignment.disputes` type=`truncated_tail`）。理由：截断在事实中段、无法判定其断言内容；**两侧分母都不进**，单列。
- **R6 不做逻辑句合并**：保持 text 归一，不把自问自答/残句拼回逻辑句；6 条 `single_source`（只一方有标签）剔除并留痕（`counts.consensus.single_source=6`、`counts.flags.split_boundary=6`），两率口径不受影响。
- **R7 5 条 `judge_extraction_fp` 仅从 P′ 排除，P 照算**：句首列表序号「1.」×2（S1/S7-R1）、「修正后的回答」×1（S8-B）、残句 `12→1` ×2（S7-R8/S8-B）。证据：`alignment.judge_issues[]`（`kind=list_ordinal/meta_phrase/truncation_cut`）；5 条均不在 P 分母内（`rates.P_prime.fp_rows_in_P=0`）。

## 2 机制裁决（最关键：17 条漏判的构成）

- **`partial_hit_whole_sentence_supported`：16 条** —— 句内某 token（`2`、`广陵路`、`12`）命中 fact，判据即把**整句**判 `supported`，句内**无来源成分从未被检测**：`2 十单元` 4 条（S1、S7-R1、S8-A、S8-B）、`在杭州` 5 条（S4）、`地下停车场第 2 层/第 2 屁层` 7 条（S5）。证据：`rates.alt_prereg_literal.P.leak_rows`（其中 `judge_label=supported` 恰 16 行）。
- **`sentence_no_fact_judged_no_fact`：1 条** —— S3-00「我只喝美式咖啡，不加糖，不加奶，只加少量的黑咖啡豆。」判据抽 0 fact ⇒ `no_fact`，按预登记字面计入漏判。
- 另 1 条 fabricated（S5-00 车牌 `苏A12345`）被 JUDGE 正确判 `unsupported` ⇒ 17/18 而非 18/18。
- **结论句（写死）**：v2.1 的 `facts==[] → 2-gram` 修复**只覆盖答案级（branch5）**（`m5_ground_v2.py:_resolve_branch5:126`、`ngram_check:141`、`u > theta:197`、branch5 进入条件 `:301-305`），**句级没有「句内未覆盖成分」检测**——`ground()` 只把**抽到**的 fact 标注句号（`:243-248`），未抽出的无来源片段既不产生 `unhit` 也不产生 `undecidable` ⇒ **长生成下系统性漏判**。3 条误判同源：句级 `gram_n=0` ⇒ `no_fact`（S7-R4-10「我只喝美式咖啡，不加糖」、S7-R8-0「我不加糖」、S7-R8-2「我喝美式咖啡」）。

## 3 最终结论（四态，逐字定稿）

- **(c) 装置可用性 = 可用**：8 场景 17 答案跑完、`281.575 s`、峰值 `7.3379 → 7.4340 GiB`（未过 8.0、未熔断）、S8 `pos`/`n_tokens` 双等（4232/137，`load_return=137`）且 `load_strict` 通、无新增 Minidump、boot id 未变、`signals_sent_by_parent=false`；`attempt#1` 工具 `OverflowError` 已入 `attempts[]` 且 `counted_in_verdict=false`。证据：`M5C-36-r1.json` `elapsed_total_s/peaks/resume/reboot/device.signals_sent_by_parent/attempts`。
- **(c) 判据 = 作废**：依预登记 §4（JUDGE 系统性错误 ⇒ 判据作废、另立 v2.2，`PREREG-M5-C.md:88`）；**不是**「(c) 未通过」。不得用本批两率给 v2.1 判「通过/未通过」。
- **(c) 模型行为读数 = 有效**：附和「杭州」5 句、编造车牌 `苏A12345`、编造「地下停车场第 2 层」7 句、数字退化「2 十单元」4 句、S3-00 无来源扩写 1 句、R9 回问地址仍在（S7-R9 首句「我住在广陵路12号2单元602」）。证据：`M5C-36-adj.json.labels[]`、`M5C-36-cand-raw.json.answers[]`。
- **K1 kill 臂 = 夹具核心通过、未武装**：自管 Vulkan 三件 rc=0（instance/device/submit+fence/waitIdle/销毁，设备名 `AMD Radeon RX 6750 GRE 10GB`）、3/3 次 save `third=0`；129 s 一次性停顿（cycle1 chunk72→80）经纯文件微基准 20 轮**未复现**（2 臂×10 轮，steady 均 0.529 s、最慢 chunk 8.003 ms、无 stall）⇒ **不归因 save**；100 次真杀**等用户在场**、未武装（`M5-K1-DRYRUN.json` `device.dryrun.vulkan/attempts[1]/limitations`、`M5-K1-IO-MICROBENCH.json` `conclusion`）。
  口径说明：该件 `four_state` 原文 = `未接上（试装超时：优雅退出 132.3s > 8s；无第三次）`；本裁决不覆盖该字段——"夹具核心通过"指设备/保存路径已验证，"未武装"指超 8 s 上界、shoot 未启用；两者并记，不把超时读成夹具缺陷（微基准已否证 save 归因）。

## 4 边界与禁述

- 本批只覆盖：单 model / 单 DLL `9edbafa1` / 单 device / θ=0.20 固档 / argmax；**不覆盖**掉电、GPU 活跃期 kill、驱动级 bug check、θ 已校准性、长会话无界退化。
- **禁述**：把 (c) 说成「通过」或「未通过」；`判据作废` 与 `未通过` 混用；把 K1 说成 GPU 活跃期 kill；称「GPU kill 通过」「覆盖驱动级 bug check」。K2/K3 已裁为**裁剪/暂缓**（见 `PREREG-KILL-ARM-v3` `42434b91`），不构成 crash-safe save 结论的组成部分。
- 分母说明：主口径漏判 18、误判 61 均 ≥10；两率分母来自 ADJ 盲标 + consensus，非 JUDGE 单方。

## 5 §坐标（现场复算；sha16 = sha256 前 16 hex）

| 件 | sha16 | 字节 |
|---|---|---|
| `out/M5C-36-r1.json`（主件） | `c3b8c062e84b2463` | 317,123 |
| `out/M5C-36-cand-raw.json` | `ea7a5a5bc46883ed` | 28,786 |
| `out/M5C-36-adj.json`（= `-adj-sealed.json`） | `0d882f20987fea70` | 60,432 |
| `out/M5C-36-review.json` | `3666cf58b1c55317` | 87,811 |
| `out/M5C-36-judge.json` | `9c2d2be5aa839068` | 261,594 |
| `out/M5C-36-alignment.json` | `aaed082264712c59` | 245,640 |
| `LANDED-m5-c.json` | `4beb7497b023aa2e` | 10,875 |
| `out/M5C-36-resume-S8.kvmem` | `479683b524f136b1` | 19,640,216 |
| `docs/_work/PREREG-M5-C.md` | `250dbb417a7e7470` | 14,071 |
| `docs/_work/PREREG-KILL-ARM-v2.md`（v3 内容） | `42434b91d3923d1a` | 18,253 |
| `out/M5-K1-DRYRUN.json` | `2507a2a59362e2c7` | 29,461 |
| `out/M5-K1-IO-MICROBENCH.json` | `66577f63bd129dfa` | 227,945 |
| `m5_ground_v2.py`（v2.1，跑后未变） | `5e11e1ac06f022c7` | 66,413 |

两处现场差异（如实记）：① `M5-K1-DRYRUN.json` 实测 **29,461 B**（派单写 29,462，差 1 B；sha16 相符，以现场为准）；② `LANDED-m5-c.json.sealed.review_sha16` 仍为 `null`（REVIEW 件未登记进 LANDED），本裁决以 review 件自身坐标 `3666cf58` 为准。

## 6 下游

- **另立 v2.2**：v2.1 自 `5e11e1ac` 起冻结、**不得回头改 θ/词表/分支序**；v2.2 须补「句级未覆盖成分」检测（句内 coverage，而非答案级 branch5），新预登记、新批次、out-of-sample；本批读数只能作 v2.2 的动机证据，**不得复用为本批两率的改判**。
- **K1 100 次真杀**：夹具已备、未武装，等用户在場；K2 裁剪不排期、K3 不做。
- **口径**：日后引用 (c) 必须同时带「判据作废」与两率的分子/分母；单独引用任一率视为断章。