# STAGE3 验收 · **定稿（终审关闭）**

| 组 | 数 | 说明 |
|---|---|---|
| ① 通过项 | **15** | R1–R7、R8a、R8b、R9、R10、R11、R12a、R12b、R13 |
| ② 强度分布 | **R 14 / A 1** | 唯一的 A 是 R8b |
| ③ 未闭 finding | **0** | F9 / F10 / F11 全关 |
| ④ 遗留 A 档 | **1** | R8b：理由=整跑 `main()` 会改写 `PREREG` 与两个库，**成本判断，不是能力边界** |

**这三个数不是我手记的**：由脚本以 `^\| R\d+[ab]? \|` 从本表数出（15 行），并对每行取档位列统计（R=14 / A=1）。
**凡条数写死就是又一份副本（纪律 14）** —— 所以这里记的是「怎么数出来的」，不是「数是几」。

**「通过」不等于「无缺陷」**：F9/F10/F11 三个 finding 全部关闭，但关闭是「修了并复核」，不是「没发生过」。
**R8b 维持 A 是证据边界，不是缺陷** —— 换一个读者愿意付整跑成本，它可以升 R。

**两个独立证人**：隔离证明我与 lead 各跑一次，均 `BYTE-IDENTICAL = True`；`fix_compare` 逐叶 diff 也是两人各算一次、结论相同（变化叶子 3 个，全在 `/criteria_before`）。

**档位以 lead 复算为准；本单保留我的独立证据与三处自我更正**（时间戳追记 / R8 未拆 / 枚举根写错）。

---
# Stage 3 · 验收报告（inspector，2026-10-25，Step 2 交付 d6e03f1）

**核对时刻**：本次全部读数取自 2026-10-25 05:04–05:16 的磁盘状态。
`m5_bridge.py` = `d400dfa1c4e95f43`（18439 B）；`PREREG-STAGE3-11ROWS.json` = `4e8375a24ec6dcbd`（11374 B）；
`_before/` = **21 / 21**（跟踪 / 磁盘，`*.pyc` 0 个 —— 22→21 少的那一个是 `__pycache__/*.pyc`，不是副本）。
**强度**：R 重算 / C 构造性覆盖 / A 锚定转录 / S 仅自述。**顺序**：块文件基线 → 三集合 → 逐列 → 11 行 → 锚重算。

## 0 结论

**通过**，附 6 处 finding。其中 **F4 记「未通过（引用不精确）」**（能改、改法明确），
F1/F2/F6 为**陈述或落盘缺口**（不影响数值），F3 为**口径偏保守**，F5 为**结构建议**。
**无「按计划未到」项，无「失锚」项。**

## 1 十七项

| # | 判据 | 我的验法 | 结果 | 强度 |
|---|---|---|---|---|
| 1 | 闸门在返回点的函数体内 | AST：`select_m5_source` 跨 130–230；`return` 在 192/226/229；闸门在 217/228 | 通过（措辞见 F2）| R |
| 2 | 可达 | AST 列举 `ms.assert_m5_source_allowed(` 调用 | 通过（:217, :228）| R |
| 3 | 运行时拒绝（权威层）| 注册库缺失⇒`OriginError` 含路径；`regcon=None`⇒`AssertionError` | 通过 | R |
| 4 | `no_todo_stage3` | `m5_bridge.py` 内 = 0；扫描器自身 4 处（`run_stage3.py:420`、`check_m5_gate.py:8/18/190`）| 通过（作用域见 F5）| R |
| 5 | A/B 六探针 | `probe_ab.py` A1 A2 B1 B2 B3 B4 | 6/6 通过 | R |
| 6 | 报错拆分（情形 1 / 2）| 两条独立分支、文案互斥；情形 2 不含链接动作串 | 通过 | R |
| 7 | P10 三问 | `p10_no_invariant_claim` / `p10_real_condition` / `p10_correct_action` 各自可单独变红 | 通过 | R |
| 8 | 预登记表成件 | 11 行；`authored_after_run=true`；`expected_sources` 三分类 + `forbidden` 条款 | 通过 | A |
| 9 | 期望的**出处引用**是否精确 | 逐行读 `expected_basis`，与 `m4_verify_grounded.py` 原文对照 | **未通过（引用不精确）**：写 `:223`，字面量在 `:213–219`，`:223` 是变量绑定 | R |
| 10 | 11 行期望 vs 我的重算 | 逐行 `expected_verdict` 与我的重算比对 | **零不符（11/11）** | R |
| 11 | 逐列：仅 `source_text`/`text_origin` 变 | 逐块逐列比对 `_stage3_pre.json` | 通过（另有**新增列** `synthetic`，见 F1）| R |
| 12 | 无增删块 | 集合差集 | `added=[] removed=[]` | R |
| 13 | 块文件不动（sha+bytes+**mtime**）| 对 `0a63717933055e65` 逐项比对 | 三项全 True | R |
| 14 | `_m5db` 锚 | sha256 前 16 | `200ed6b2f1af0363` | R |
| 15 | `_before` 规矩 | 磁盘 21 / REGISTER 20 条 / 跟踪 21 | 通过（`24fb336b`、`5cf3bbb1`、`aa5c0aa4` 在册）| R |
| 16 | 强度拆分 | 我按行重算归类 | **R 11**（与交付 R 9 / C 2 不同，见 F3）| R |
| 17 | baseline 自锚 | sha256 前 16 | `0a63717933055e65`（677 B）| R |

## 2 Findings

### F1 新增列 `synthetic` 未在「变更列」陈述中出现
`blocks` 由 12 列变 13 列，新增 `synthetic`，取值 0（主）/ 1（消融）。「变更列 = {source_text, text_origin}」只对**共有列**成立。
**要求**：陈述补一句「新增列 `synthetic`（0/1），用途 = 声明的消融豁免」。否则下一个人按「结构没变」比对会把新增列当意外。

### F2 「闸门在返回点」需限定：3 个 return 中 2 个被闸门覆盖
AST 事实：`return` 在 192/226/229，闸门在 217/228。**192 是未过闸门的返回** —— 「消融库无 registry 列 ⇒ 声明 synthetic」的豁免路径。
**要求**：改为「闸门覆盖 2 个数据返回路径；第 3 个返回是声明的消融豁免，由三处独立拒绝点（路径声明 / schema 观测 / 层 1 存在性）保护」。
这不是缺陷而是**措辞精度**：说「全部返回都在闸门之后」会被下一次 AST 检查直接推翻。

### F3 `R 9 / C 2` 偏保守：两行消融例现在也是 R
Step 2 把两块注册进同一 `_m5db`，消融例不再需要「无 blocks 表的辅助库」。我做了完整双侧重算（`db=PRE` vs `db=M5`，同一 `ground`）：
- `plate_ablated`：before `unsupported` / after `unsupported`（与 run 一致）；
- `home_ablated`：before `supported` / after `supported`（与 run 一致）。
**⇒ 我判 11 行全 R。** 交付的 C 依据（「消融库不可由 `ground` 驱动」）在该改造后不再成立。方向上**低估自己**，但口径必须更新。

### F4 `expected_basis` 的 `file:line` 指向绑定处（记「未通过」）
写的是 `m4_verify_grounded.py:223 expected_after`；实际 **:223 是 `"expected_after": expect`（变量绑定）**，7 个字面量在 **:213–219**。
读者到 :223 看到变量，还要再追一层 —— 而「字面量还是算出来的」正是这条 basis 要证明的东西。
**改法**：写 `:213–219`（声明处）；若同时写 :223 须标注「绑定处」。
**附带匹配隐患**：代码标签带后缀（`a_wrong_province(苏B-3F19K)`），预登记 key 无后缀 —— 比对前必须归一化，否则「11 行零不符」可能是巧合。

### F5 S3-4 扫描集合是硬编码单文件（正向枚举只做一半）
`run_stage3.py:420` 扫 `m5_bridge.py` 一个文件 —— 这是**显式清单**（不是 `all − x`，符合你的 ①），
但**新增第二个生产源文件时会静默不扫**，判据不会失败（你的 ③ 未满足）。
**建议**：清单写进代码 + 断言「覆盖所有调用 `assert_m5_source_allowed` 的文件」；清单外新增 ⇒ 判据失败。

### F6 `invalidated_anchors` 未落盘
`run_m5_grounded.json` 顶层无该键。旧锚 `d97cdfdcbd6c6d3d` → 新锚 `d13df1e987ee509c` 的五行记录仍缺。
`(old, new, reason="Stage 3 换源", time, expected_by=SRC-CRITERIA §12.7)` —— **`expected_by` 不是 none**：判据 §12.7 事先声明「换源后裁决不变」，本次失效是**被预期到的**。

## 3 锚（可复算）

| 对象 | 值 | 备注 |
|---|---|---|
| `_m5db/m5_m4_blocks.db` | `200ed6b2f1af0363` | 20480 B, 05:04:33 |
| `run_m5_grounded.json` | `d13df1e987ee509c` | 37440 B, 05:05:32 |
| `run_m5_fix_compare.json` | `5f7c196a32a659a6` | 未变 |
| `_stage3_pre.json` | `9500f1c7c59c118f` | before 侧 provenance |
| `PREREG-STAGE3-11ROWS.json` | `4e8375a24ec6dcbd` | 11374 B, 05:05:48 |
| `baseline_blocks.json` | `0a63717933055e65` | 677 B |
| `profile.kvmem` / `project.kvmem` | `3251081d…` / `981a9c77…` | 04:25:52 未动 |
| `blocks` 行数 / `source_text` 长度 | 2 / [110, 113] | — |

## 4 我对 `mine/lead/DISCIPLINES.md` 的审读（`fbef3d9f3338ef1c`，72 行）

**总评**：可用。13 条形式全部可执行，13 个实例全部对得上今晚的事。第 2 条起因写的是你（正确）。

**必须修的两处**：
1. **:14（纪律 5 的实例列）以「；另：」开头** —— 前半句丢了，现在读起来像后半截。这是**页面自身的「红得不对」**：有实例，但不是完整的那一条。
2. **:55 行「配置 / 事实 | —」** —— 空对照项，右列是破折号。按纪律十二（不许留空），要么填一句它为什么必须分开，要么删行。

**建议补两条**（都属于今晚已经付过代价的）：
- **凡 before 侧快照，必须登记 `copyist` / `copy_time` / `reason`** —— `_stage3_pre.json` 内容可靠，但**没登记谁复制、何时复制**，于是「它是不是 Stage 3 之前拍的」只能靠 mtime 推。
- **凡「新增 / 删除」，必须与「变更」分开陈述** —— 今晚 `synthetic` 列就是「新增」，但被并进「变更列」这句话里，读者会以为只有已有列在动。（我做验收单时也差点漏掉。）

## 5 v2 验收预登记：9 项返工 × 我事先声明的证伪方式

**规则**：每行必须附「能让它失败的输入」。我核的是**有没有这条输入**，不是「现在是不是 True」。
**若某项只改了措辞/标签而没有配对失败输入 ⇒ 我判「未通过（无失败输入）」。**

| # | 返工项 | 我会怎么证伪 | 通过条件 |
|---|---|---|---|
| R1 | `:223` → `:212-219` | **断言** `:212-219` 每行都含字符串字面量（非变量）；把行号改成 `:220-226` ⇒ 必须失败 | 断言存在且在错误行号下变红 |
| R2 | 副本钉原件（最重）| **改原件不动副本**（`m4_verify_grounded.py` 里 b1 期望改 `unsupported`）⇒ 必须失败 | 存在「副本 == 原件」断言，且我改动原件后运行即红 |
| R3 | `invalidated_anchors` | 读 `run_m5_grounded.json` 顶层；核五元组齐全且 `expected_by ≠ none` | `(old=d97cdfdc…, new=d13df1e9…, reason, time, expected_by=§12.7)` |
| R4 | 新增列与变更列分开 | 读交付陈述：是否把 `synthetic` 单列陈述 | 「新增列 `synthetic`（0/1）」独立成句 |
| R5 | 扫描清单完整性断言 | 造一个新的生产文件（含闸门调用）**不加入清单** ⇒ 必须失败 | 清单外调用点 ⇒ 判据红 |
| R6 | AST 措辞 | **AST 断言**：每个 `return` 要么在闸门之后、要么在豁免白名单；把 192 移出白名单 ⇒ 必须失败 | 白名单 + 断言存在，且删除豁免项后变红 |
| R7 | R 11 须带定义 | 只照它给的定义重算；不复用它的脚本 | 我按定义能算出同一 `R 11`，含两侧各算 |
| R8a | 守门布尔须派生：**派生式能否返回 True** | 输入可构造：FORBIDDEN 成员 ⇒ True（它的 selftest 已做，我复读产物确认 derived=true）| **档 R**：任何人照做可再跑 |
| R8b | 守门布尔须派生：**真实产物所有行为 False** | 需整跑 main()（会改写 PREREG 与两个库）⇒ **不值得为它做**（不是做不到）| **档 A**：关于某时刻的事实，非测试结果 |
| R9 | `grade` 须由真算产生 | **四步**：① 改前 `_m5db` 复制进 `_before/` 并登记 copyist/copy_time/reason ② 把消融块 `source_text` 改一个字符 ③ 断言「贴标签版=C」且「真算版 before≠after」④ **复原并复验内容哈希重新 = `76df01317bfaf3e7`** | 分叉成立 **且** 复验哈希回到原值；未复原即判未通过 |

**另按你 §5**：`#16` 记 **R 11**（带定义后）；`#8` 记 **A（转录，未与原件建断言）**；两格不留空。

## 6 v2 变动预登记：哪些锚**该**变、哪些**不许**变（出 v2 前写死）

**用途**：v2 之后若某个锚变了，我要能区分
**「按计划补了台账」** 与 **「有人偷偷重跑」** —— 前者在 `_before/` 里有登记的旧副本且 `reason` 指名返工项，后者不会有。

| 对象 | 现值 | v2 后允许变？ | 依据 | `_before/` 登记要求 |
|---|---|---|---|---|
| `m5_bridge.py` | `d400dfa1c4e95f43` | **允许**（R1/R6/R8/R9 会改代码）| R1 R6 R8 R9 | 每次改前一份，`reason` 指名 R 编号 |
| `run_m5_grounded.json` | `d13df1e987ee509c` | **允许**（R3 补 `invalidated_anchors`）| R3 | `reason="R3 补台账前预防"` |
| `PREREG-STAGE3-11ROWS.json` | `4e8375a24ec6dcbd` | **允许**（R7 带定义、R2 断言落地后重生成）| R2 R7 | 同上，指名 R 编号 |
| `_m5db/m5_m4_blocks.db` 文件 sha | `200ed6b2f1af0363` | **允许**（R9 会临时改并复原）| R9 | 五段第 ① 段必存 |
| `_m5db` **内容哈希** | `76df01317bfaf3e7` | **不许变**（R9 第五段必须复验回到此值）| §12.31 | 若不等 ⇒ R9 判未通过，且后续全部作废 |
| `run_m5_fix_compare.json` | `5f7c196a32a659a6` | **不许变**（与 Stage 3 无关）| — | 变了即是越界重跑 |
| `kvmem/blocks/profile.kvmem` | `3251081d…` / 1,524,708 B / 04:25:52 | **不许变**（sha + bytes + mtime 三项）| §12.16 | 任一变 ⇒ 停，先查 |
| `kvmem/blocks/project.kvmem` | `981a9c77…` / 1,097,988 B / 04:25:52 | **不许变**（同上）| §12.16 | 同上 |
| `_stage3_pre.json` | `9500f1c7c59c118f` | **不许变**（before 侧 provenance）| §12.20 | 变了则全部 before 侧结论失锚 |
| `baseline_blocks.json` | `0a63717933055e65` | **不许变**（自锚）| §12.16 | — |

**复检顺序（你补的那条）**：先核上表「不许变」各行 → 全部通过才继续；任一行变 ⇒ **停**，不进入 R1–R9 复核。
理由：R9 的失败输入测试会写 `_m5db`，**若它忘了复原，后面所有项都是在脏地基上做的**。

## 7 v2 新增三项（R11 / R12 / R13）预登记

| # | 返工项 | 我会怎么证伪 | 通过条件 |
|---|---|---|---|
| R11 | `_before/` 登记层自检（`check_before_register.py`）| 先查文件是否存在；存在则我跑三条红线：删一个副本 / 改一个副本一字节 / 清掉一条 reason | 三条各自能红，且**分别打印名字**（不是一个总数）|
| R12 | `m4_existing_files_untouched` 去自指 | 读代码：对象是「git status 差集」还是「正面枚举」；再看字段名是否改为 `m4_files_untouched_or_registered` | 正面枚举 + 判定为「未变 或 已登记且 reason 指名本步」+ 名字带轴 |
| R13 | 截断事故变成可复跑断言 | 读检查：是否禁止「同一表达式内先 `open(...,'w')` 再 `open(...).read()`」；并跑它给的命中样例 | 有样例且样例真的命中；无样例即判「永远为真」 |

**R11 现状（我已手工审计，`_before` 25 条登记 / 25 个副本 / 1 个 `__pycache__` 目录）**：
- A 登记了但磁盘不在 `_before`：`_stage3_pre.json@9500f1c7c59c118f`（`copy_path` 指向 m4 目录本身，basename 为空）；
- B 磁盘有但名字不带 sha 且无登记：`m5_ground_preR12.py`；
- 24 个带 `@sha` 的副本：登记 sha == 名字 sha == 内容重算 sha，**全对**;
- 附带：`_before/__pycache__` 目录又出现了（被忽略，不影响跟踪数，但 R11 的 ③ 应把它排除或清掉）。
**R11 定性：按计划未到**（R11-R13 是 05:3x 才派的，执行者仍在跑）。下面不是判定，是**独立复核（审计栏）**：
- 复核时刻 05:40 前后；该目录 05:45 又变过一次，故每结论带时刻（纪律十三）。
- **F8（比 A/B 更根本）**：`_before/` 被当成运行时暂存区 —— `m4_verify_grounded.py:129-131` 与 `m5_fix_compare.py:32-34` 在运行时把 pre-R12 源码写进 `_before/m5_ground_preR12.py` 再 import；该文件此刻**不存在**（跑一次才出现）。
- ⇒ B（名字不带 `@sha`）与 `__pycache__` 重现是**同一条**，根因是「证据面与运行时暂存同目录」。
- ⇒ 因此「`.py` 一律改名」会破坏那两个 loader；「`__pycache__` 再现即红」当前会**恒红**（每次正常运行都生成）。建议：scratch 移出 `_before`（`tempfile` 或 `_scratch/`），之后该红才有意义。
- **A 的根因**（我查出）：`copy_path` 指向 m4 目录本身、`basename` 为空 ⇒ 检查须用 `isfile` + 非空 `basename`（纪律二十二）。

## 8 v2 终审（R1–R13；核对时刻 05:38–05:45，命令与返回行随行注）

**判定表（四态 + 强度，无空格）**

| # | 项 | 判定 | 强度 | 我的证据（可复跑） |
|---|---|---|---|---|
| R1 | `:212-219` 行号与字面量断言 | 通过 | R | `check_probe_keys()` 返回 `code_literal_line=268`（行号已随文件变动），正控 PASS |
| R2 | 副本钉原件 | 通过 | R | 我改**原件**三处（应答文本/期望判决/标签名）⇒ 各自红并报具体行与字段；正控 PASS |
| R3 | `invalidated_anchors` 五元组 | 通过 | R（lead 复算）| 读 `run_m5_grounded.json`（`007cb08b`）顶层键与五元组 |
| R4 | 新增列与变更列分开 | 通过 | R（lead 复算）| 交付陈述把 `synthetic` 独立成句；列集合 13 |
| R5 | 扫描清单完整性断言 | 通过 | R（lead 复算）| 读断言 + 清单；未构造新生产文件（在 M4 内，超出我的写权限）|
| R6 | AST 逐 `return` 分类 | 通过 | R（lead 复算）| AST 描述为「2 数据返回 + 1 声明豁免」，读代码与豁免白名单 |
| R7 | R 11 带定义 | 通过 | R（lead 复算）| 定义写明两侧各算的 db 与命令；我按定义复核 11 行 |
| R8a | 派生式可返回 True | 通过 | R | 产物 `selftest.derived=true`、`rows_with_true=[]`、`ok=true` |
| R8b | 真实产物全行为 False | 通过 | A | 关于某时刻的事实；变 R 需整跑 `main()`（改写 `PREREG` 与两库）⇒ **不值得，不是做不到** |
| R9 | `grade` 由真算产生 | 通过 | R | 我在 tempfile 副本上重跑分叉：`unsupported → supported`，`diverged=True`；前后内容哈希 `76df0131` |
| R10 | 探针短 id 与标签三轴 | 通过 | R | 与 R2 同一断言覆盖（label/text/expect 三轴 + 短 id 前缀）|
| R11 | `_before` 登记层自检 | 通过 | R | 见下：plain PASS（27 副本 / 0 问题）+ 三红各自命中正确类别 + **我自建的前后全量 sha 相等** |
| R12a | 机制：改一个已枚举对象 ⇒ 判据必须红 | 通过 | R | 我跑 check_m4_untouched_endtoend.py： control ok=True ⇒ 追加一字节后 ok=False，failures 打印文件名，current_sha16 00965dcf508e90ce vs expected e3bfec41d1f059e7；mutated path inside $TMP: True；production tree after test: ok=True (untouched) |
| R12b | 范围：清单不得漏掉应被枚举的对象（F11）| 通过 | R | 我跑 check_m4_kvmem_coverage.py： 根 + 两组模式写死；--selftest 三红各自点名文件（删锚定项 / 删 pos0_A 豁免 / 豁免不存在文件）|
| R13 | 截断事故可复跑断言 | 通过 | R | 检查 0 命中；`--selftest` **命中样例在 line 8** ⇒ 不是空断言 |

**R11 细节（三件事分开写，纪律 25 口径）**
- **判据本身**：`copies on disk: 27 (+ REGISTER.json)` / `BEFORE-REGISTER: PASS (0 problem(s))`。
- **自检是否伤人**：`--selftest` 在 `tempfile.mkdtemp('_br_selftest_')` 内 `copytree` 后**重写每条 `copy_path` 进临时树**，并 `assert abspath(target).startswith(abspath(tmp))` ⇒ **隔离，不是复原**。
- **隔离证明（我自己做的第二个观测）**：跑 `--selftest` 前后对 `_before` 全部 **28 个文件**做 sha+bytes 快照 ⇒ **byte-identical = True**。
  三红命中类别：`delete a copy → missing_copy:1`、`flip one byte → sha_mismatch:1`、`clear a reason → register:1`。
- **受损副本恢复**：`run_m5_grounded.json@d13df1e987ee509c` = **37440 字节 / sha16 `d13df1e9`**（与 lead 独立复核一致）。

**F9（已修复，我复核 05:5x）**：`m4_files_untouched_or_registered` **没有端到端失败输入**。

**修法已交付并被我复核**：check_m4_untouched_endtoend.py 在 mkdtemp("_m4_untouched_") 内 copytree，并 assert abspath(target).startswith(abspath(tmp))；输出含 mutated path inside $TMP: True 与 production tree after test: ok=True (untouched) ⇒ **隔离，不是复原**。

原先的两半（保留作历史）：
- **做不到**：红需改 M4 生产目录内一个已枚举文件 —— 超出我的写权限。**这不扣分。**
- **没做**：交付里没有对应的 `--selftest`（R11 有、R12 没有）。**这一条扣。**
它的红可由「改一个被枚举文件但不登记」触发，但那次改动必须在 M4 生产目录内（超出我的写权限），且交付里没有对应 `--selftest`。
⇒ 现证据只到「合取项在反事实输入下可为 False」（我做的查找演示），**不到「端到端变红」** ⇒ 记 A，不计缺陷外的分。
建议：仿 R11 的做法，在 `tempfile` 里 `copytree` 一份 M4，改一字节后要求红。

**F10（新，登记文字）**：`_before/run_m5_fix_compare.json@5f7c196a32a659a6` 的 `reason` 是「运行前预防（Step 2 重跑之前）」，**没有指名 R11**。
它今天被用来支撑「`fix_compare` 按计划变」的判定（纪律 16 要求 `reason` 指名理由）。**判定我仍给「按计划变」，但依据是我自己的 diff，不是那条 reason**：
`run_m5_fix_compare.json` 旧 `5f7c196a`(15082 B) → 新 `9eab963b`(15141 B)，**变化叶子恰为 3 个，全在 `/criteria_before`**：
`path: '_before/m5_ground_preR12.py' → None`、`scratch: None → tempfile.mkdtemp('m5_scratch_cmp_')/…`、`not_in_before: None → True`；
`/all_non_flip_hold = True`、`/all_flips_happened = True` 两侧一致 ⇒ **判据结果未变，路径改述**（不是越界重跑）。

**我自己的两处更正（写进本单，不再口头说）**
1. 我报过「05:40 审计」，那**不是读数**：`_r11.py` 没有打印时钟。按当时 `disk copies=25` 与文件创建时刻反推区间为 **05:29:06–05:30:06**（推理，非测量）。已立判据：**没有打印过的时间一律写作「未测」**。
2. R8 原记 A 过于保守 ⇒ 拆 R8a(R) / R8b(A)，两条都准确。

## 9 F11（lead 05:4x 查出，我复核）：**承重输入不在锚表里**

**事实（我实测，05:47）**：`m4` 下共 9 个 `.kvmem`，其中两个是 Stage 3 的承重输入：

| 文件 | 字节 | sha16 | 在旧锚表里？ |
|---|---|---|---|
| `m4/blocks/blk_conv_2026-10-25_01.kvmem` | 9,507,412 | `81127d24fd64b96b` | **没有** |
| `m4/_ablate/blocks/blk_conv_noplate_2026-10-25_01.kvmem` | 8,253,844 | `e3bfec41d1f059e7` | **没有** |

两个值与你复算一致。它们**现在**在 `M4_UNTOUCHED` 里（`m4_verify_grounded.py:38-39`，锚走 `_stage3_pre.json.block_files`），
而 `_stage3_pre.json` 确实记了 `sha16` + `bytes` + `mtime`（我读了原文）⇒ **锚值本身一直是可靠的，缺的是「它在清单上」这件事。**

**为什么这比 F9/F10 重要**：
> **清单缺项不会红，只会让人以为看过了。**
F9 是「缺一条会红的输入」，F10 是「解释没写清」；F11 是「**最承重的两个输入，此前从未被要求不许变**」。
前两者的后果是「证据弱一档」，F11 的后果是「**清单给人虚假的完成感**」。

**这与我 F5/③ 是同一形态**：显式清单必须自证完整。⇒ 修法不是补两行，是加一条断言：
```
枚举 m4/{blocks,_ablate/blocks}/*.kvmem  ⇒  每个都必须在 M4_UNTOUCHED 里
差集非空 ⇒ 红（打印缺失文件名）
```
否则下次新增一个 block 文件，锚表仍然静默不全。

**F11 定性**：不是执行者的实现缺陷（`_stage3_pre.json` 记得很全），是**清单自身缺一条完整性断言** ⇒ 记在案，不扣 R12 的档。

### 9.1 三个数字的成因（我实测，05:52；**每条都写根 + 模式 + recursive**）

| 口径 | 根 | 模式 | recursive | 命中 | 集合 |
|---|---|---|---|---|---|
| **我的旧报数** | `m2_visibility/` | `**/*.kvmem` | 是 | **9** | 含 `runs_m14b/` 6 个 + `pos0_A` |
| **lead 的报数** | `m4/` | `**/*.kvmem` | 是 | **3** | 两个 `blk_conv*` + `pos0_A` |
| **规格** | `m4/` | `blocks/blk_*.kvmem` + `_ablate/blocks/blk_*.kvmem` | 单层 | **2** | 只有两个 `blk_conv*` |

**⇒ 三个数字都对，只是根与模式不同。** 我错在**把 `runs_m14b/` 算进了 m4 的账**（根写错），不是因为数错。

**顺带一条会让人静默数少的坑（我踩了）**：`glob.glob('**/*.kvmem')` **不传 `recursive=True` 时按单层处理**，
`m4/**/*.kvmem` 于是只回 2 个（漏掉 `_ablate/blocks/` 那个），传了才 3 个。**「静默少数」比报错危险。**

**`pos0_A.kvmem` 的取舍（显式分类，不是「不在 glob 里所以自然不算」）**：
- 它是 **`m4_pos0_refuse.py:43`** 读的输入（`os.path.join(HERE, "blocks", "pos0_A.kvmem")`，`:31/:36` 也有 `pos0_A` 的 lease 注册）；
- 与 `runs_m14b/…/home.kvmem` 同 sha `73843fc55efd1ab3`（2,194,932 B）⇒ **是某次 encode 的派生物**；
- ⇒ 分类：**`EXCLUDED`，理由 = 「另一步（pos0 拒答）的输入，且为同 sha 的派生物；本步（Stage 3 车牌/住址）不读它」**。

**断言规格（照 lead 版，补一条实现陷阱）**：
```
根    kvmem/m2_visibility/m4/
模式  blocks/blk_*.kvmem + _ablate/blocks/blk_*.kvmem    （blk_ 前缀，不是 *.kvmem）
断言  (枚举 - M4_UNTOUCHED - EXCLUDED) 非空 => 红，且打印缺失文件名
外加  EXCLUDED 每项必须真的出现在枚举结果里（否则豁免在空转）
实现  用 glob(..., recursive=True) 或 os.walk；** 不传 recursive 会静默按单层处理
失败  从 M4_UNTOUCHED 删掉一条 blk_conv => 必须红并打印该文件名（同时验证「红得信息够用」）
```

**F11（已修复，我复核 05:5x）**：check_m4_kvmem_coverage.py 已按三件套落盘，且理由比我的版本强：
- EXCLUDED[blocks/pos0_A.kvmem] 的理由是 **m4_pos0_refuse.py:43-45 每次运行 eng.save(SEQ, path) 重写它 ⇒ 按纪律 24 不能作锚**；
  我的旧理由只证明「它是复制品」，它的理由证明「它每次都被改写」—— **同一条豁免，理由强弱不同。**
- 三红各自点名：drop an anchored entry / drop the pos0_A exemption / exempt a nonexistent file ⇒ 豁免不空转那条被真跑到了。

### 9.2 它做了两件没被要求的事，以及我复核的数字（05:5x）

**(a) 腿 B：不只问「该上清单的上了没有」，还问「没上清单的有没有被分类过」**
```
A 腿  (枚举 − M4_UNTOUCHED − EXCLUDED) 为空        <- 该上的上了没有
B 腿  更宽的 blocks/*.kvmem 也必须落在 锚定 ∪ 豁免  <- 没上的有没有被分类
```
**A 腿能过而 B 腿不能过的那一格，藏着的正是「不在 glob 里所以自然不算」。**
B 腿把负定义堵死：**豁免是一个要写理由的分类，不是一个「没出现在模式里」的默认结果。**

**(b) `pos0_A` 被算进隔离覆盖：`34 = _before 28 + 枚举 M4 对象 6`**
> **豁免说的是「不作锚」，不是「没人看」。**
降级为观测值 **≠** 移出视野 —— 这与纪律 24 同根。

**我独立复核的三组数（不是采信清单）**
```
check_selftest_isolation.py
  scope : 34 file(s) = _before 28 + enumerated M4 objects 6
  pre   : digest=81abb458dd02a046   post: digest=81abb458dd02a046   diff: [] (empty)
  三个 selftest 全在覆盖内且全 PASS（before_register / m4_untouched_endtoend / m4_kvmem_coverage）
  ISOLATION: PASS -- the self-checks touched nothing they are testing
pos0_A 三方同值: blocks/pos0_A.kvmem / encode_pass2/home.kvmem / aborted_run1_home.kvmem
  均为 2,194,932 B / 73843fc55efd1ab3
```