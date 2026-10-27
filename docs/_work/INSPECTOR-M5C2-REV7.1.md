# INSPECTOR · M5-C2 REV7.1 独立复审计

- 角色：独立复审计员（不参与实现；上一轮 REV7 审计亦由本人完成）
- 对象：REV7.1「陈述更正重冻结」件及其离线重跑产物
- 复算入口：`kvmem/m2_visibility/m5/out/_rev7_1_audit.py`
  sha16 `051e85331dc77261` / 59,314 B / 1,220 行
- 审计数据：`kvmem/m2_visibility/m5/out/M5C2-REV7-1-AUDIT.json`
  sha16 `64ad2b4e27c7812d` / 44,528 B
- 结论：**四门槛数值复现 + 装置合格**（措辞严格：不写“rev7.1 通过”这种整体背书）

## 0. 冻结面核对（全部一致）

| 件 | sha16 | 字节 | 行 | 备注 |
|---|---|---|---|---|
| `PREREG-M5-C2-REV7.1.md` | `09d6f1b163ea0b84` | 16,313 | 160 | 无末尾换行 · `frozen=true`×3 · `write_state=frozen` · `supersedes=32eaf82ca56600c4` |
| `run_m5c2_rev7_1_offline.py` | `88256d274c9993cc` | 50,618 | — | 执行者脚本（本审计不 import/不执行之，除 §6 %TEMP% 复现披露） |
| `M5C2-REV7-1-OFFLINE.json` | `55191eaf2426f736` | 510,508 | — | 产物 |
| `PREREG-M5-C2-REV7.md`（被取代） | `32eaf82ca56600c4` | 5,835 | 88 | 字节未变 ⇒ by-reference 可验证 |
| `run_m5c2_rev7_offline.py`（C32） | `65ed60125528d5d6` | 44,761 | — | 比对基线 |
| `M5C2-REV7-OFFLINE.json`（C32 产物） | `1f8f44b921e575fe` | 507,657 | — | 比对基线 |
| `M5B4-JUDGE.json`（输入） | `6a3001b6ca23ef7d` | 452,456 | — | 只读 |
| `M5B4-LEAD-RULING.json`（gold） | `9273ebc97aa1413a` | 13,195 | — | 只读 |
| `M5B4-SENTENCES.json` | `c349ca5a93192aac` | 99,636 | — | 只读，交叉核对 |

冻结标志自洽：`frozen=true`×3、`frozen_rev=1`×3、`frozen_at=2026-10-26T21:06:55+08:00`×1、
`LEAD 复核通过`×2、`rev7_1_ver=1`×4、`correction_type=statement_correction`×1。
残留扫描：`frozen=false` 0、`待 LEAD 复核` 0、`待复核` 0、`TODO` 0、`draft` 0；
唯一“未冻结”字样是 §3 的合法条件句 `(b6) 未冻结 ⇒ (b5) 不跑`。

B5 身份面：B5 现行件 sha16 `d6c7bdac73ef7326`；B5 自身 0 次出现旧哈希 `e306ce994d306a84`；
rev7.1 文档/脚本/产物中 `e306ce` 出现 0 次；rev7.1 只以文件名 + §9.1/§9.5 引用 B5，
未复制任何哈希。**未发现“把 B5 旧哈希当现行值”的错误。**

## 1. 四态逐项

| # | 要求 | 状态 | 依据 |
|---|---|---|---|
| 1 | 重冻一致性 + 零残留 + supersedes | 通过 | §0；`supersedes_sha16=32eaf82ca56600c4` 与 rev7 实测哈希一致 |
| 2 | 规则零改动（N1–N4 语义、14 判定函数、阈值/词表/正则） | 通过（附注：by-reference 不自包含） | §2 |
| 3 | 独立重算 0 差异 + rev7.1 对 C32 仅允许差异 | 通过 | §3、§4 |
| 4 | A1/A2′/A3′ 真值化 + 归因/消融独立复核 | 通过 | §5 |
| 5 | §3 准入口径与 b5 性质说明；B5 §9.1 身份取代；不抄 stale hash | 通过 | §0、§2.4 |
| 6 | 我的实现两次重跑逐字节一致；执行者脚本复现产物哈希 | 通过 | §6 |
| 7 | 两条 doc↔code 不一致之定性 | 通过（均判“表述不精确 / low”） | §7 |
| 8 | cheat / 纪律扫描 | 通过 | §8 |

## 2. 规则零改动证据

### 2.1 文本层：rev7.1 不内联规则正文，只做 by-reference

- rev7.1 正文（附录 A 之前）中：`NFKC` 0 次、`千分位` 0 次、`非贪婪` 0 次、`捕获组` 0 次、
  `window_coverage` 0 次、`valid = ` 0 次 ⇒ N1–N4 的**定义性文本没有被重述**（不存在“借更正之名改规则”）。
- §1 引用表四行的行号与 rev7 实际结构逐行核对：
  N1 `第 34–39 行`、N2 `第 41–45 行`、N3 `第 47–49 行`、N4 `第 51–52 行`；
  四个起始行确为 rev7 对应 `### N1..N4` 标题行，行号区间非空。
  N3 行只在“备注”列写明“仅断言 A2/A3 改为真值陈述”，其余三行均标“引用，零改动”。
- 收束条款：rev7 第 54 行原文 `其余 R1/R2/R3/R4+/R_DERIVED+ 规则、阈值 0.80、词表一律不变。`
  在 rev7.1 中以「」引号逐字引用（内容比对一致；仅多出引号）。
- rev7 §2 第 34–54 行共 21 行，其中 17 行规则正文不再内联；第 54 行以引文形式保留。
  这是 rev7.1 的设计（by-reference），**使新文档不自包含**：读者必须回读被取代件。已列入保留意见。

### 2.2 代码层：函数源码切片逐字节比对

rev7.1 脚本 vs rev7 脚本，顶层 `FunctionDef` 源码切片 sha256：

- **15 个函数逐字节相同**（14 个判定函数 + 被 `judge_row_rev7` 内嵌的 `gate_item`）：
  `baseline_reproduce, char_evidence, gate_item, judge_row_rev7, matcher, normalize7,
  pick_attribution, r1_r2_r3_rev7, r4_plus_rev7, rev7_causes, sha16, token_kind_of_span,
  value_tokens, verdict_v51, write_json_atomic`
- 不同的只有 `main` 与 `verify_inputs`（断言块/输入揭示），新增 `item_assertion`、
  `verdict_assertion` 两个断言 helper。判定路径无一行改动。
- 模块级常量变化限于 7 个：`PRE, PRE_SHA16, PRE_BYTES, PRE_LINES, ART, ASSERT_A2, ASSERT_A3`
  （加上新增的 `ASSERT_A2_VERDICT, ASSERT_A3_VERDICT, CORRECTION_TYPE, REV7_1_VER,
  RULE_CODE_UNCHANGED, SUPERSEDES_SHA16`），无阈值/词表常量变化。
- `PURE_PATTERNS`、`ENTITY_PATTERN` 源码哈希相同；`import` 列表完全相同。
- 阈值字面量：`0.80` 出现 6（rev7）/7（rev7.1，多出的一处为文档声明“阈值 0.80 不变”）、
  `0.90` 5/5；不存在其它 `0.xx` 形态阈值。

### 2.3 规则语义：独立重算反证

用本人独立实现（见 §3）按 N1–N4 字面语义重算，“全开/全关”四套消融全部落在预期位置，
且产物与重算逐项相同（§3）——若规则被改，0 差异不可能同时成立。

### 2.4 §3 准入口径与 B5 关系

rev7.1 §3 保留四门槛表（`≤ 4/46`、`≤ 5/41`、`≤ 2/261`、`= 0` 逐例判失败）、
新增“rev7.1 是口径更正，不是调规则凑结果”与“仅在文档身份上取代 B5 §9.1 所指判定层”的表述；
B5 §9.1 仍把判定层钉在 rev7 `32eaf82ca56600c4`；rev7.1 的原话是“**仅在文档身份上取代该引用**
（`supersedes_sha16=32eaf82ca56600c4`），**实质零变更**……即 `(b5)` 的判据组成写成
「判定层 = rev7.1」时，与 B5 §9.1 原意**等价**”。rev7.1 未改 B5 文件、未引用 B5 旧哈希。

## 3. 独立重算 vs 产物：0 差异

实现纪律：复算入口只 import 本人上一轮独立审计模块 `out/_rev7_audit.py`（sha16 `6695a4b4de403870`，
本人所写、依据冻结 PREREG 而非阅读实现脚本）；**不 import / 不执行 / 不复制执行者脚本**。

### 3.1 基线自检（证明我的复算器确实在复现 rev5.1）

| 检查 | 结果 |
|---|---|
| 261 句 rev5.1 verdict 与 `M5B4-JUDGE.json` 存储值 | 261/261 一致 |
| 777 条 item 的 absent + rule_hits（rule/reason/span） | 777/777 一致 |
| 246 条 model_extract 的 derived 复算 | 246/246 一致 |
| 基线分布 | supported 65 / unsupported 167 / abstain_ok 15 / undecidable 13 / parse_fail 1 |

### 3.2 rev7.1 vs 我的独立重算（逐字段）

比对覆盖 261 句 × 14 字段（`gold, verdict_rev5_1, verdict_rev7, route, parse_ok,
derived_rev7, derived_stored, n_items, n_valid, n_invalid, n_absent, n_unverified, changed`）
与 777 条 × 12 字段（`item, evidence, valid, absent, matcher_hit, coverage, numeric_ok,
item_verdict, rule, reason, r3_hit, binding, rule_hits` 全量）以及 gate、false_by_reason、
sentence_diff、invalid_items、all_invalid_sentences、rates、rev7_rule_hit_counts：

- **差异计数：0**（`total_diffs=0`；sentence 0、item 0、gate 0、attribution 0）。
- 四门槛：FP **2/46**（sids `b4-s1-q2-s07`, `b4-s1-q2-s09`）、
  leak **4/41**（`b4-s2-q2-s01, b4-s3-q4-s03, b4-s3-q4-s11, b4-s3-q4-s12`）、
  parse_fail **1/261**（`b4-s2-q2-s05`）、new_miss **0/35**；全部达标。
- 作废条目 124/777；全作废句 6；`rev7_rule_hit_counts` R1 8 / R3 435 / R4+ 3 与产物一致。
- `sentence_diff`：fixed 5（`b4-s1-q2-s01, b4-s1-q2-s15, b4-s1-q3-s03, b4-s2-q1-s01,
  b4-s8-q2-s02`）、broken 0、neutral 2（`b4-s1-q1-s02, b4-s5-q1-s01`，gold=no_fact）、
  unchanged_false_positive 2、unchanged_leak 4 —— 与产物逐 sid 相同。
- `false_by_reason` 7 行：attribution N1 3（`b4-s1-q2-s01, b4-s1-q2-s15, b4-s1-q3-s03`）、
  N2 2（`b4-s2-q1-s01, b4-s8-q2-s02`）、N3 2（`b4-s1-q2-s07, b4-s1-q2-s09`）；
  fixed true 5 / false 2 —— 与产物逐行相同。

## 4. rev7.1 产物 vs C32 产物（只允许的差异）

共享键 54 个：**47 个逐字节相等** / **7 个不同** / **6 个新增键**。

- 不同的 7 个：`assertions`（A2/A3 由旧断言变真值断言，`all_pass` False→True；
  A1 相等）、`schema`、`prereg_sha16`、`code_sha16`、`code_file`、`code_bytes`、`inputs`
  （`inputs` 内 items_source/gold/sentences 相等，`prereg` 不等，新增子键
  `prereg_text_checks`）。
- 新增的 6 个：`correction_type`、`prereg_text_corrections`、`rev7_1_ver`、
  `rule_code_unchanged`、`supersedes_code_sha16`、`supersedes_sha16`。
- **8 个数据块全部相等**：`sentences / items / gate / false_by_reason / sentence_diff /
  invalid_items / all_invalid_sentences / rates`。
⇒ 数值面与 C32 完全同构，差异只落在 provenance 与断言块，符合“陈述更正”定位。

## 5. 断言真值表（独立复算，非引用产物）

A1（`normalize` 千分位）：`coverage('8600元', normalize7('手术费 8,600 元')) = 1.0`，通过。

| 断言 | sid | 条目 × 次数 | 位置 | valid | coverage | 句 verdict | gold | N3 是否改判 |
|---|---|---|---|---|---|---|---|---|
| A2′ | `b4-s1-q2-s07` | `患者`×1、`做的`×1 | pos 0–1、pos 9–10 | 全 true | 全 1.0（substring） | unsupported（rev5.1 亦 unsupported） | support_present | 否 |
| A3′ | `b4-s1-q2-s09` | `患者`×13 | 全 pos 0–1 | 全 true | 全 1.0（substring） | unsupported（rev5.1 亦 unsupported） | support_present | 否 |

⇒ 旧断言“`患者` 句内根本不存在 / `valid=false`”被证伪并撤回；真值陈述成立。
A2/A3 各“occurrences 数学”与产物断言块逐字段一致（`artifact_math=true`）。

消融（本人实现，FP 计数 / 分母 46）：

| 配置 | FP | 结论 |
|---|---|---|
| rev5.1 基线 | 7 | — |
| rev7.1 全开 | **2** | — |
| 关 N1 | 5 | N1 独立修复 3 例 |
| 关 N2 | 4 | N2 独立修复 2 例 |
| 关 N3 | 2 | N3 净贡献 0（只把 2 个 no_fact 句改为 neutral，不改四门槛） |
| 关 N4 | 2 | N4 净贡献 0 |
| N2 改在 evidence 上 | 2 | 与 source 口径读数相同（设计允许，见 §7 ④注） |
| 全作废句→undecidable | 2 | 门槛不变（口径稳健） |

归因 3/2/2 与消融 3/2/0/0 相互印证：四门槛的实际修复全部来自 N1+N2，N3/N4 净贡献 0。

## 6. 重跑与复现

### 6.1 我的独立实现：两次重跑逐字节一致

同一脚本、两个独立进程各跑两次；审计 JSON 的 sha256 前缀：

- 预探针两次：`5b5452166cf92e48` = `5b5452166cf92e48`
- 已内嵌探针两次：`3de3c256713a2c51` = `3de3c256713a2c51`
- 最终落盘件两次：`64ad2b4e27c7812d` = `64ad2b4e27c7812d`（44,528 B）

产物内无时间戳、无随机量；`determinism.recompute_core_sha16 = d65e08ebde9f96c4` 在全部运行中恒定。

### 6.2 执行者脚本复现（披露：**复现不是 import**）

将 `run_m5c2_rev7_1_offline.py` 逐字节复制到 `%TEMP%`（副本 sha16 仍 `88256d274c9993cc`），
以 `python -X utf8` 跑两次：两次退出码 0，产物 sha16 均为 `55191eaf2426f736` / 510,508 B，
与控制台输出哈希（`afedfcd25627b549`）两次一致；产物内容与仓库现有件相同，故未回写/未改字节。
复现前后 `M5C2-REV7-1-OFFLINE.json` 仍为 `55191eaf2426f736`（未被本次审计改动）。

## 7. 两条 doc↔code 不一致的定性

### ④ `false_by_reason` 枚举含 N4，但 `pick_attribution` 无 N4 分支

- rev7 §4 的 `false_by_reason` 说明枚举 `N1/N2/N3/N4/R4+/declared/other`；rev7.1 §4 以
  `schema 同 REV7 §4` 继承该枚举。
- 实测 `pick_attribution` 分支为 `N1, N2, N3, R4+, declared, other`（无 N4）；
  产物 `false_by_reason` 实际归因集合 = `{N1, N2, N3}`。
- 但 N4 在本实现中**没有独立可观测作用面**：N3 生效时“作废条目不计 absent”已使 N4 的
  “absent 词只在 valid 条目生效”退化为同一机制；关闭 N3 后所有条目 valid，N4 变成 vacuous。
  故任何句子都无法被**唯一**归因到 N4。产物中 N4 仅作为 `sentence_diff` 的 cause 标签出现 2 次。
- **定性：规范过度枚举 / 表述不精确；严重度 low（纯文档/审计标签，数值零影响），不是实现缺陷。**

### ⑤ 头注“no engine / no GPU runner” vs `R41 → _e3gpu_run` 传递 import

- 直接 import 只有 `run_m5c2_rev5_offline`、`run_m5c2_rev5_1_offline` 两个离线模块；
  但传递闭包会加载 `_e3gpu_run`、`run_m5c2_rev4_1`、`run_m5c2_r2`、`run_m5c2_floor`、
  `run_m5c2_floor_rev2`、`run_m5c2_rev4`、`run_m5c2_rev2_order` 进 `sys.modules`（9 模块）。
- 独立探针（import 依赖模块、**不 import 执行者**）：导入前后
  `nvcuda.dll, nvml.dll, cudart64_*, cublas64_*, cudnn64_*, vulkan-1.dll, kvshim*.dll,
  ggml-vulkan.dll, llama.dll, ggml.dll` 句柄全部为 0，**新增加载 0 个**；无子进程、无设备。
  这些模块顶层只有路径常量/`sys.path`/正则编译；被调用的 R41 函数是纯文本函数
  （`normalize/bigrams/fuzzy_coverage/value_tokens`）。
- 产物 `n_forward=0`、`no_gpu=true`，且代码路径无前向调用。
- **定性：表述不精确（按直接 import 读成立、按传递闭包读不精确）；严重度 low，无数值影响；
  “离线、零前向”的实质成立。**

## 8. cheat / 纪律扫描

| 检查 | 结果 |
|---|---|
| sid 特判分支 | 0（`sid ==/!=/in` 形态 0 处） |
| 脚本内 b4 字面量 | 7 行，全部是四门槛/断言期望清单（`EXPECT_FP/EXPECT_LEAK/ASSERT_A2/ASSERT_A3` 及归属注释），非按 sid 改写判定 |
| 文件 IO 调用 | 只读 3 个冻结输入 + 写 1 个产物；无 b5 路径 |
| b5 相关字符串 | 1 处：`design_set_note` 的“(b5) not run here”说明 |
| 时间/随机 | 脚本 0 处 datetime/random；产物无 ISO 时间戳 |
| 产物 12 项纪律标志 | `no_gpu, n_forward=0, no_model_call, no_network, no_sid_special_cases, no_threshold_change, no_wordlist_change, no_gold_change, no_prereg_change, no_input_change, no_git_commit, no_b5_read` 全 true |
| 输入/被取代件 | 全程只读；未 git 提交；(b5) 数据未读取 |

## 9. 未做 / 边界（诚实声明）

1. **(b5) 未跑**：验收集不在本次范围；若其数据不可读，我未读任何 (b5) 内容。
2. **无法严格证明“运行期未读 b5”**：只能静态证明脚本无 b5 路径引用、产物无 b5 字段、
   本次流程无 b5 数据源；运行期负事实不可形式化证明。
3. **未测 GPU 显存/设备占用**：只检查 DLL 句柄为 0、`n_forward=0`、代码无前向调用。
4. **执行者脚本复现为 %TEMP% 逐字节副本**：属“复现”而非 import；复算结论全部来自我的实现。
5. **我的复算入口 import 了本人上一轮审计模块** `_rev7_audit.py`（`6695a4b4de403870`）：
   那是本人所写代码，不是执行者代码，也不含执行者任何一行。
6. **redline 归属说明**：rev7.1 相对 rev7 提案 24 个 hunk、+128/−56 行；新增行按段落
   归类为 header 6 / §0 事实更正 15 / §2 规则引用表 9 / §2.1 断言 12 / §3 门槛与 b5 准入 8 /
   §4 交付字段 9 / §5 纪律 9 / 附录 redline 60，0 行未分类。其中 §4/§5 与附录属
   交付/纪律的行政性/引文段落（非规则、非阈值、非断言）；若把白名单严格限定为
   “§0/§2/§3/头注状态”，则该 18 行已由 `RULING-M5C2-REV7.1-REDLINE`
   （`docs/_work/RULING-M5C2-REV7.1-REDLINE.md`）裁定为纳入（§4/§5 行政性）——它们不改变任何判定语义。
7. **④的“N4 无独立作用面”是代码路径 + 消融推断**，未做形式化证明（该断言已由消融
   关 N4 = 关 N3 = FP 2 支撑）。
8. **保留意见（最大一条）**：rev7.1 的“规则零改动”依赖 by-reference，新文档不自包含；
   其可验证性完全建立在“rev7 文件字节不变（`32eaf82ca56600c4`）”之上。本次已核对 rev7
   未变，但若未来 rev7 被改写，rev7.1 的规则语义引用即失效（文档层风险，非本次数值风险）。

## 10. 结论

**四门槛数值复现（2/46、4/41、1/261、0/35）+ 装置合格。**

- 冻结面、残留、supersedes：一致；B5 身份引用正确且未抄旧哈希。
- 规则零改动：文本层无内联改写、代码层 15 个判定函数逐字节相同、阈值/词表/正则不变。
- 独立重算对产物：**0 差异**（句/条目/门槛/归因/逐句对照/作废/速率/命中计数全部一致）。
- rev7.1 对 C32：47 等 / 7 差（assertions + 6 provenance）/ 6 新增 / 8 数据块等。
- A1/A2′/A3′ 真值陈述成立；归因 3/2/2、消融 5/4/2 与 N3/N4 净贡献 0 互证。
- 两条 doc↔code 不一致均为**表述不精确、severity low、无数值影响**。
- 两次重跑逐字节一致；执行者脚本在 %TEMP% 复现出同一产物哈希。

措辞边界：以上支持“**装置合格**”与“四门槛数值复现”，**不构成**对 rev7.1 作为
整体方案（含 (b5) 验收）的“通过”背书；(b5) 未跑。