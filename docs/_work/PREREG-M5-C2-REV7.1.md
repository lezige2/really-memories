# PREREG-M5-C2-REV7.1 —— rev7 口径更正件（规则零改动）：§0 字符级定位更正 + §2 断言真值化

> `frozen=true` · `frozen_rev=1` · `frozen_at=2026-10-26T21:06:55+08:00` · `write_state=frozen` · 冻结人：LEAD · **LEAD 复核通过**
> `rev7_1_ver=1` · `supersedes=32eaf82ca56600c4`（`docs/_work/PREREG-M5-C2-REV7.md`，5,835 B / 88 行）· `correction_type=statement_correction`（**口径更正，非规则变更**）
> 性质：**口径更正（statement correction），不是规则变更**；本件**写于 rev7 结果之后**（rev7 产物 `M5C2-REV7-OFFLINE.json 1f8f44b921e575fe` / 507,657 B 已出；独立审计 `INSPECTOR-M5C2-REV7.md`、`M5C2-REV7-AUDIT.json`、`_rev7_audit.py 6695a4b4de403870` 已完成）
> **规则 / 阈值 / 词表 / 金标 / 输入零改动**：N1–N4 定义、`0.80` / `0.90` 阈值、`NEG_WORDS` / `ABSENT_MARKERS` 词表、金标 `M5B4-LEAD-RULING.json 9273ebc97aa1413a`、输入 `M5B4-JUDGE.json 6a3001b6ca23ef7d` 全部沿用 rev7，**逐字未改**
> 判定代码零改动：`run_m5c2_rev7_offline.py 65ed60125528d5d6` 的判定函数**逐字节不变**（本件对应的重跑脚本 `kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py` 仅改头注 / PREREG 常量 / 断言块 / 产物字段，判定函数与 rev7 逐字节一致，见附录 B）

## 0 更正后的 §0（取代 REV7 §0 第 11–19 行的归因表）

### 0.1 更正后归因表

| 归因 | 例数 | 例 | 根因 |
|---|---:|---|---|
| **R1 数值归一化缺失** | **3** | `b4-s1-q2-s01`、`b4-s1-q2-s15`、`b4-s1-q3-s03` | 句内值 `8600元` vs 依据 `8,600 元`：二元组覆盖 = **0.75 < 0.80** ⇒ 判 value_mismatch。**纯标点问题** |
| **R1 值域过宽（贪心实体正则）** | **2** | `b4-s2-q1-s01`、`b4-s8-q2-s02` | 正则 `[^\s，。]{2,}(?:公司\|店\|院\|…)` 贪心吞掉前缀：抽出 `租车公司`（覆盖 0.333）、`地点是宠安医院`（覆盖 0.5）⇒ 拿"描述语"当"值"比对 |
| **R3 缺席词越界** | **2**（N3 未修好，仍为 FP） | `b4-s1-q2-s07`、`b4-s1-q2-s09` | **模型把句首「患者：」标签与句中片段当成待核验条目（`患者` pos 0–1；`做的` pos 9–10，均逐字存在，见 §0.2）**，其 `未提及` 被计入聚合 ⇒ 整句 `unsupported` |

> **7 例 FP 归因互不重叠**：N1 **3**（已修）、N2 **2**（已修）、R3 **2**（N3 净贡献 0）；**N3/N4 对 7 例的修复数 = 0**（消融：去 N1 → FP 5、去 N2 → FP 4、去 N3 → FP 2）。

### 0.2 字符级事实（本件更正；0-based inclusive，基于 `normalize7`）

| 句 | `sentence` | 条目 | 在 `normalize7(sentence)` 内的位置 | 字面 N3 判定 |
|---|---|---|---|---|
| `b4-s1-q2-s07` | `患者：是在仁和口腔做的。` | `患者` | **pos 0–1**（子串命中） | `valid=true`，`coverage=1.0` |
| `b4-s1-q2-s07` | 同上 | `做的` | **pos 9–10**（子串命中） | `valid=true`，`coverage=1.0` |
| `b4-s1-q2-s09` | `患者：右下第一磨牙。` | `患者` | **pos 0–1**（子串命中，13 个同名条目同位置） | `valid=true`，`coverage=1.0` |

> 自校验值：`normalize7('患者：是在仁和口腔做的。') = '患者:是在仁和口腔做的。'`（长 12）；`normalize7('患者：右下第一磨牙。') = '患者:右下第一磨牙。'`（长 10）。
> ⇒ REV7 §0 原句对这两例的描述**作废**（旧文本仅作为 redline 引文保留在附录 A.1）。正确表述：**模型把句首「患者：」标签与句中片段当成了待核验条目（标签型 / 片段型 item）**；归因类别「R3 缺席词越界」**不变**，变更**仅限事实陈述**，不涉及规则。

### 0.3 结论（与 REV7 §0 第 19 行一致，不变）

**这不是"模型改写词汇"的问题，是判定层三个确定性 bug**（N1 数值归一化缺失 / N2 贪心实体正则 / R3 缺席词越界）。本件更正的是 §0 第 17 行对 `患者`、`做的` 的事实描述，**不改变**该归因结论。

## 1 §2 规则：与 REV7 逐字相同（引用原文，不重抄、不改写）

本件 §2 的规则定义**就是** `docs/_work/PREREG-M5-C2-REV7.md`（sha16 `32eaf82ca56600c4`）§2 第 32–54 行原文，**逐字相同**，本件不重抄、不改写、不新增任何条件：

| 规则 | REV7 §2 位置 | 本件处置 |
|---|---|---|
| **N1** 数值归一化（`normalize()` 扩展） | 第 34–39 行 | 引用，零改动 |
| **N2** R1 值域收窄（`value_tokens()` 改） | 第 41–45 行 | 引用，零改动 |
| **N3** 条目原子性门（新增） | 第 47–49 行 | 定义引用零改动；**仅断言 A2/A3 改为真值陈述**（§2.1） |
| **N4** 缺席词作用域（新增） | 第 51–52 行 | 引用，零改动 |

> **收束条款（逐字引用 REV7 §2 第 54 行）**：**「其余 R1/R2/R3/R4+/R_DERIVED+ 规则、阈值 0.80、词表一律不变。」**

### 2.1 断言更正：A2/A3 由「不可满足」改为「为真」

REV7 §2 N3 的两条自检断言（原句：`b4-s1-q2-s07` 的 `患者`、`b4-s1-q2-s09` 的 `患者` **必须**被判 `valid=false`）**撤回**——它们在字面 N3 定义下**不可满足**（证明见 §0.2；独立审计亦给出可满足性 = 0）。改为下列**为真的**断言（规则定义不动，仅断言改为真值陈述）：

- **A1（不变，N1 自检）**：`R5.coverage('8600元', normalize7('手术费 8,600 元')) == 1.0`。
- **A2（真）**：`b4-s1-q2-s07` 的 `患者`（pos 0–1）与 `做的`（pos 9–10）在字面 N3 下 **`valid=true`、`coverage=1.0`**；该句 `verdict_rev7 = unsupported`，gold = `support_present`，**仍是误判（FP）**；且 **N3 不改变该句 verdict**（`verdict_rev5_1 = verdict_rev7 = unsupported`）。
- **A3（真）**：`b4-s1-q2-s09` 的 `患者`（pos 0–1，13 个同名条目全部）在字面 N3 下 **`valid=true`、`coverage=1.0`**；该句 `verdict_rev7 = unsupported`，gold = `support_present`，**仍是误判（FP）**；且 **N3 不改变该句 verdict**（`verdict_rev5_1 = verdict_rev7 = unsupported`）。

**归因（新增，本件逐字采用）**：**四门槛的实际修复全部来自 N1 + N2；N3/N4 净贡献 = 0（消融：去 N3 后 FP 仍 2/46）。**

> 消融口径（执行者实测）：关闭 N3（等价于所有 item 均 `valid=true`，N4 随之失去作用面）后，四门槛读数**逐项不变** —— FP **2/46**（仍为 `b4-s1-q2-s07`、`b4-s1-q2-s09`）、漏判 **4/41**、`parse_fail` **1/261**、`new_miss` **0/35**；唯一差异是 2 句 gold=`no_fact` 的句子（`b4-s1-q1-s02`、`b4-s5-q1-s01`）由 `supported` 回到 `unsupported`，二者**不参与**四门槛。

## 3 门槛与 (b5) 准入（§3 门槛与 REV7 §3 **逐字相同**）

本件 §3 的门槛表与 `docs/_work/PREREG-M5-C2-REV7.md` §3（第 56–65 行）**逐字相同**，本件不重抄、不改动：

| 指标 | rev5.1 基线 | 门槛 |
|---|---:|---|
| 误判 | 7/46 = 15.22% | **≤ 4/46** |
| 漏判 | 4/41 = 9.76% | **≤ 5/41** |
| `parse_fail` | 1/261 | **≤ 2/261** |
| 漏判新增（gold=fabricated 由 `unsupported` → `supported`） | — | **= 0**（逐例检查，任何一例即判失败） |

- **`(b5)` 准入**：rev7.1 在 `(b4)` 设计集上实测满足上述四门槛 —— FP **2/46**、漏判 **4/41**、`parse_fail` **1/261**、`new_miss` **0/35** ⇒ `rev7_1_unusable=false`，**`(b5)` 准入**。
- **性质声明**：**rev7.1 是口径更正，不是调规则凑结果**。判定层规则、阈值、词表、金标、输入与 rev7 **逐字相同**；rev7.1 的数值与 rev7 **逐项相同**（FP 2/46、漏判 4/41、`parse_fail` 1/261、`new_miss` 0/35、7 句变化 5 fixed / 0 broken / 2 neutral、N3 作废 124/777），见重跑产物逐项 diff（附录 B.3）。
- **与 `PREREG-M5-C2-B5.md` §9.1 的关系**：B5 §9.1 把「判定层 = rev7」钉在 `PREREG-M5-C2-REV7.md 32eaf82ca56600c4`。本件**仅在文档身份上取代**该引用（`supersedes_sha16=32eaf82ca56600c4`），**实质零变更**：判据组成（抽取层 = rev5.1 prompt `a6bc4f268f7711de` + 判定层 = N1–N4）、§3 四门槛、H1 与 9.2–9.6 全部不变。即 `(b5)` 的判据组成写成「判定层 = rev7.1」时，与 B5 §9.1 原意**等价**。
- 若四门槛任一不过 ⇒ `rev7_1_unusable=true`，`(b5)` **不跑**，记 `blocked_by_judge_unusable`。

## 4 交付（rev7.1）

`kvmem/m2_visibility/m5/out/M5C2-REV7-1-OFFLINE.json`（`n_forward=0`）

- **顶层沿用 REV7 §4 全部字段**：`rev7_ver=1`、`n_sentences=261`、`n_forward=0`、`design_set=true`、`not_acceptance=true`、`prereg_sha16`、`items_source_sha16=6a3001b6ca23ef7d`、`gold_sha16_current=9273ebc97aa1413a`
- **顶层新增（本件）**：`rev7_1_ver=1`、`prereg_sha16`（= **本件** sha16，取代 rev7 的 `prereg_sha16`）、`supersedes_sha16=32eaf82ca56600c4`、`correction_type="statement_correction"`、`rule_code_unchanged=true`
- **逐条 / 逐句 / 读数 / `false_by_reason` / 逐句对照（fixed / broken / neutral 全列）/ 作废条目清单**：schema **同 REV7 §4**（字段与口径零改动）
- **断言**：A1 / A2 / A3 按本件 §2.1 取值（A2/A3 为**真值陈述**，应 **pass**）
- **自证标志**：`no_gpu` / `no_model_call` / `no_network` / `no_sid_special_cases` / `no_threshold_change` / `no_gold_change` / `no_input_change` 等，同 REV7
- **脚本**：`kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py`（rev7 脚本副本；判定函数逐字节一致，见附录 B）
- **钉哈希**：产物 sha16 在本件冻结后**重钉**并记入任务回报；独立审计方（**不 import** 执行者实现）复算两次须 **byte 级一致**且与本件数值 **diff = 0**

## 5 纪律（(b5) 阶段）

- **零 GPU、零模型、不联网**：本阶段纯确定性离线重算，`n_forward=0`；(b5) 跑之前不重跑任何模型
- **`(b5)` 一次性**：`one_shot=true`，只跑一次，**不许重跑**
- **`(b5)` 开跑前必须有已冻结的 `(b6)` 备用验收集**：按 `PREREG-M5-C2-B5.md` §9.5，`(b6)` 必须在 `(b5)` 开跑**之前**出题并冻结（防"看到结果再出题"）；`(b6)` 未冻结 ⇒ `(b5)` 不跑
- **不许据 `(b5)` 结果调参**：不得据 `(b5)` 修改 N1–N4、阈值、词表、聚合口径后重跑 `(b5)`；下一次改动只能用 `(b6)` 验
- 不许改金标、不许删例、不许调阈值；`(b5)` 结果不得用于任何"回填式"再次判定
- 若 `rev7_1_unusable=true`，`(b5)` **不跑**，记 `blocked_by_judge_unusable`

## 附录 A 文本更正 redline（old → new，仅头注 / §0 / §2 / §3）

### A.1 §0 归因表第 3 行（REV7 第 17 行）

- **old**：`| **R3 缺席词越界** | **2**（与上重叠 1 例） | b4-s1-q2-s07、b4-s1-q2-s09 | 模型列出句内根本不存在、或重复的条目（患者、做的），其 未提及 被计入聚合 ⇒ 整句 unsupported |`
- **new**：`| **R3 缺席词越界** | **2**（N3 未修好，仍为 FP） | b4-s1-q2-s07、b4-s1-q2-s09 | 模型把句首「患者：」标签与句中片段当成待核验条目（患者 pos 0–1；做的 pos 9–10，均逐字存在，见 §0.2），其 未提及 被计入聚合 ⇒ 整句 unsupported |`
- **变更实质**：删除「**句内根本不存在**」，改为「**逐字存在 + 字符级位置**」；归因类别不变。

### A.2 §2 N3 断言自检（REV7 第 49 行）

- **old**：`断言自检：b4-s1-q2-s07 的 患者、b4-s1-q2-s09 的 患者 必须被判 valid=false。`
- **new**（本件 §2.1 A2/A3）：`断言自检：字面 N3 下 b4-s1-q2-s07 的 患者（pos 0–1）与 做的（pos 9–10）、b4-s1-q2-s09 的 患者（pos 0–1，13 条）均为 valid=true、coverage=1.0；两句 verdict_rev7 = unsupported（gold=support_present，仍为 FP），且 N3 不改变其 verdict（rev5.1 = rev7 = unsupported）。`
- **变更实质**：把不可满足的「必须 valid=false」换成**已实测为真**的「valid=true / coverage=1.0 / verdict 不变」；N3 定义本身**一字未改**。

### A.3 §3 门槛表与 (b5) 准入（REV7 第 56–65 行）

- **old（第 65 行）**：`任一不过 ⇒ rev7_unusable=true，停，回报 LEAD，不许调阈值/N/规则重跑。`
- **new**（本件 §3）：门槛表**逐字不变**；仅新增准入段：`rev7.1 实测满足四门槛 ⇒ rev7_1_unusable=false，(b5) 准入；rev7.1 是口径更正，不是调规则凑结果；§3 门槛与 REV7 §3 逐字相同，B5 §9.1 所引 sha 仅在文档身份上被取代、实质零变更。`
- **变更实质**：不改任何数值门槛，只补 (b5) 准入与身份取代说明。

### A.4 新增归因句（本件 §2.1 末；REV7 无此句）

- **old**：（无）
- **new**：`四门槛的实际修复全部来自 N1 + N2；N3/N4 净贡献 = 0（消融：去 N3 后 FP 仍 2/46）。`

### A.5 头注（REV7 第 3–7 行）

- **old**：`> frozen=true · frozen_rev=1 · frozen_at=2026-10-26T20:15:00+08:00 · 冻结人：LEAD` + REV7 前置/回退/设计集说明
- **new**：本件头注（rev7_1_ver=1 / supersedes / correction_type / 写于 rev7 结果之后 / 规则·阈值·词表·金标·输入零改动 / 判定代码零改动）
- **变更实质**：仅身份与来源声明；无规则内容。

### A.6 §0 归因表例数更正（第 4 处 §0 事实更正）

- **old（REV7 §0 表）**：`N1 4 例 / N2 2 例 / R3 2 例（与上重叠 1 例）`
- **new（本件 §0.1）**：`N1 3 例 / N2 2 例 / R3 2 例（互不重叠，N3 修复 0 例）`
- **变更实质**：REV7 原表 N1 行例数 `4` 与其列出的 3 个 sid 自相矛盾；R3 行「与上重叠 1 例」无依据。实测证据 —— C32 `false_by_reason` 逐 sid 归因 = **3 / 2 / 2**（N1：`b4-s1-q2-s01`、`b4-s1-q2-s15`、`b4-s1-q3-s03`；N2：`b4-s2-q1-s01`、`b4-s8-q2-s02`；N3：`b4-s1-q2-s07`、`b4-s1-q2-s09`），三组互不重叠；消融边际：**去 N1 → FP 5、去 N2 → FP 4、去 N3 → FP 2**（基线 7 例中 N1 修 3、N2 修 2、N3 修 0）。
- **披露**：本节是**第 4 处 §0 事实更正**，超出用户点名的三处（§0 措辞 / §2 断言 / 归因句），但同属 §0 事实错误，已如实向 LEAD 报告、不隐瞒。

## 附录 B 规则零改动声明

### B.1 判定代码逐函数比对（= 0 差异）

`run_m5c2_rev7_1_offline.py` 与 `run_m5c2_rev7_offline.py`（`65ed60125528d5d6`）的**判定函数逐字节相同**。比对范围：两脚本的全部函数定义中，仅 `verify_inputs`（允许类别 ②⑤）、`main`（允许类别 ③④）与新增的 `item_assertion` / `verdict_assertion`（允许类别 ③）除外；其余 **14** 个函数逐字节相同 ——

`sha16`、`write_json_atomic`、`normalize7`、`value_tokens`、`token_kind_of_span`、`matcher`、`r1_r2_r3_rev7`、`r4_plus_rev7`、`verdict_v51`、`baseline_reproduce`、`judge_row_rev7`、`pick_attribution`、`rev7_causes`、`char_evidence`。

常量 `PURE_PATTERNS`、`ENTITY_PATTERN`、阈值 `0.80` / `0.90` 同样逐字节相同。比对方法：`ast.get_source_segment` 逐函数取原文切片 + `sha256` 比对（另加 `ast.dump` 结构比对），结果 **0 差异**。

### B.2 允许改动的仅五类

① 文件头 / 注释；② PREREG 路径与 sha16 / bytes / 行数常量；③ 断言块 A2/A3 → 真断言；④ 产物文件名 / `rev7_1` 标识 / 新增 top 字段；⑤ 新增「本件三处文本更正存在性」自检。**其余任何字节不得变**。

### B.3 数值不变

rev7.1 重跑产物与 rev7 产物（`1f8f44b921e575fe`）在 `verdict_rev7` / `items` / `gate` / `false_by_reason` / `sentence_diff` / `invalid_items` / `all_invalid_sentences` / `sentences` / 四门槛明细上**逐项相同**；只有 provenance（`prereg_sha16`、`code_sha16`、`code_file`、`code_bytes`、`schema`、`rev7_1_ver`、`supersedes_sha16`、`correction_type`、`rule_code_unchanged`）与 `assertions` 块不同。

### B.4 输入零改动

`docs/_work/PREREG-M5-C2-REV7.md`（`32eaf82ca56600c4`）、`M5B4-JUDGE.json`（`6a3001b6ca23ef7d`）、`M5B4-LEAD-RULING.json`（`9273ebc97aa1413a`）、`M5B4-SENTENCES.json`（`c349ca5a93192aac`）**全部未改**；未读 `(b5)` 任何文件；未 git 提交。

## 6 状态

`frozen=true`（LEAD 复核通过） / `frozen_rev=1` / `rev7_1_ver=1` / `executed=false` / `needs_gpu=false` / `next=b5_acceptance`