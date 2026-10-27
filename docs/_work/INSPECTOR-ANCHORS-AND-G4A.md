# INSPECTOR 复核：锚定级 + task-32 补正 + G4a 判定 + G4d needle

> **as-of**：`2026-10-25T22:26+08:00`（`tools/chat.py` 正被 task-35 收口，见 §3）。
> **只读复核**：本报告不写代码/台账/DB/产品；只读现盘、`_before` 快照与 executor 产物；无 14B 重跑。
> **唯一锚入口**：`docs/_work/ANCHORS-CURRENT.md` = **`a54c81092cf585a8`** / 10,928 B（本报告 22:26 引它，不重复散落字面量）。
> **22:55 追补**：该锚再更新为 **`41a5b29b50849fdb` / 15,759 B**（banner 去硬 sha + F1 双坐标 + G4d orphan 字段追补后；22:52 的 `d2e0f181` 15,821 B 仅历史）；本报告 §3 的 `1790f3a9` 只作 22:26 中间坐标，引现值请用新锚。
> **本报告不写 G4c**：lead 已撤回「M1.8 查询侧 ⇒ M4-C `loads` 顺序漂移」的前提（`redcheck_delete.py:17` `WANT_SEQ` + `:99-103` `fixed_selection` 证明 M4-C base 夹具写死 seq，不读 retrieval 顺序）；改为 G4d（§3.5）。

## 0 一句话

- **锚**：主锚 13 条中，**合法演进 4 条**（`chat.py` 版本链、`planner.py`、PREREG、ledger addendum）、**非受控漂移 5 条**（`MANIFEST`、`M2-ACCEPT-lead` 的两条引文、`PROJECT-STATE`、`HANDOFF`、`_land_s1.py`）、**不可复算 3 类**（7B 线、archive 500 版、旧 DLL 基线）；`README` / `INSPECTOR-M1.8-FINAL` / `compare.py` / 补丁 / DLL 为 `current`。**R→A 的具体结论见 §1.2。**
- **task-32 补正**：**读数层通过**（15 产品 + 6 变体 sha 全等于现盘；geometry/R5/F2 三项补正正确）；**新增 1 条流程问题**：S1 签署时的落账脚本 `_land_s1.py b63b22d0` 未留副本、台账已改成现盘 `bfe52d16` ⇒ 「S1 落账脚本冻结坐标可复算」须 R→A（§2.5）。
- **G4a**：**不是“仅 KeyError”**。KeyError 是执行层症状（G4a-1）；深层是**状态判定层**把不可挂载的 `conv#L5` 当记忆命中（G4a-2）与**负例前提为假**（控制问句的答案句就在 `memory_source` 里）。判定：**“负例判据作废”仅限 `m1` CLI 臂（当前 10 源库 / 后续 m1 负例）**；**M4-C 的签名夹具臂负例语义未受影响**（`WANT_SEQ[0]=[]` ⇒ `CONTROL_Q` 空 selection、`decide([])` 就是 `no_evidence`，从未被污染），M4-B 的负臂是“删句消融”、车牌是正例，也未受影响。G4a-2 修复已独立验到 `ask_count=0` + 变体红（§3.3），`m1 --explain` 由 v1 `3e8aae60` 合法演进到 v2 `dac30c83`（展示层事实修正，可逆）。

---

## 1 锚定级

### 1.1 分类口径与总表

`ANCHORS-CURRENT.md` 已按 lead 要求给出：**两列**（签署坐标 / 现行坐标）、**四态**（`current|superseded-by-design|stale|unverifiable`）、**每行复算命令**，并声明“本文件自身 sha 不入文件”。三类问题对应：合法演进 = `superseded-by-design`；非受控漂移 = `stale`；报告内锚与所述对象不符 = `stale` 的说明列（如 `run_compare` 的 `judged_current_source`、`M2-ACCEPT` 的引文）。

| 类别 | 锚 | 判定 |
|---|---|---|
| **合法演进**（有 old→new 记录） | `tools/chat.py`：v4 `cb70be52` → v5 `b9010e9c` → v6 `288d2d85`（S1 签署）→ `bb083a1b`（task-33）→ `1790f3a9`（task-35，**未签**）；`m1 --explain`：v1 `3e8aae60` / 872 B → v2 `dac30c83` / 1,107 B（G4a-3 展示标注，**去掉标注即回 v1，逐字节同**）；`planner.py 4162661c → 01507f6b`（M2 后）；PREREG 内的预登记坐标；ledger `98bbf28b → 081becbb`（addendum `supersedes`） | 不判腐烂；**引时必须两列并写**，只写现行值也不合规 |
| **非受控漂移**（旧值当现值） | `patches/MANIFEST.txt`、`M2-ACCEPT-lead.md`（两处引文）、`PROJECT-STATE.md`、`HANDOFF.md`、`_land_s1.py` | 按 §1.2 逐条 **R→A** |
| **报告内锚与所述对象不符** | `run_compare.json` 的 `acceptance.judged_current_source = current:4c8d73e9`（其对照对象早已不是 current）；`M2-ACCEPT-lead` 引 `INSPECTOR-M2-ACCEPT 4801c0da`（现 `2a2ca2d`） | 判 `stale`；修正方式是改引本表/标“历史坐标” |
| **不可复算** | 7B 线、archive 500 版补丁、旧 DLL 基线（`49,952,768 / 849e7281`、`49,954,304 / 5d3e7e46`） | 单独归档，禁止升格为 14B/现行结论 |
| **current** | `compare.py a852aacf`、`planner.py 01507f6b`、`INSPECTOR-M1.8-FINAL 119e4771`、`README 85f6a7d3`、补丁 `db32faae/32,337/600`、DLL `9edbafa1/50,007,552`、G4 产物（§3）等 | 可用；逐条命令见 `ANCHORS-CURRENT.md` |

**关于 `index_meta.docs=2`**：这是遗留键，**不是锚、不是 G4 的根因**。`INSPECTOR-M1.8-FINAL §3` 已写：`index_meta={docs:2,version:5,analysis:4}`、`is_stale()` 返回 False；`docs` 不被 `tools/retrieval.py` 读取，`attr` 表全仓**只写不读**。`GEN`/排序请勿拿它当“当前 2 源”的证据。

### 1.2 R→A 清单（具体结论，不是“文档旧了”）

1. **MANIFEST 的补丁身份**：原文 `sha256 f41cbfbd… / bytes 26,577 / insertions 500 deletions 0`；现盘 `db32faae83bec9fc / 32,337 B / 600 ins / 0 del`（`git -C llama.cpp diff --numstat` 合计 600/0；补丁文件 710 行含 header）。⇒ 任何「补丁 = 500 insertions / 26,577 B」「MANIFEST 是补丁现行身份锚」的结论 **R→A**。
2. **MANIFEST 的 DLL 基线**：原文 `49,952,768 B / 849e7281c74a5288`；现盘 DLL `9edbafa1… / 50,007,552 B`。⇒ 「shipped baseline 为现值 / 构建可比性以 49,952,768 为准」**R→A**；旧基线另标 unverifiable（未归档）。
3. **M2-ACCEPT-lead 的装置坐标**：原文 `planner.py = 4162661cc04182e8`；现盘 `01507f6bbf816c11 / 9,093 B`。⇒ 「M2 验收的规划器冻结坐标可复算」**R→A**（M2-ACCEPT 的签署时刻值仍是 4162661c，作为史料可留，但不能当现值）。
4. **M2-ACCEPT-lead 的独立复核锚**：原文 `INSPECTOR-M2-ACCEPT = 4801c0da71d53534 / 24,252 B`；现盘 `2a2ca2d05bea741f / 28,262 B`。⇒ 「M2-ACCEPT 的独立复核 = 4801c0da」**R→A**。
5. **run_compare 的“current”声明**：`acceptance.judged_current_source = current:4c8d73e9…`，且 check 文案写「对比今天这份 chat.py 的静态结构」；实际它判的是当年 `4c8d73e9`，现盘 `1790f3a9`。⇒ 「run_compare 的 `2_no_bare_reset…` 静态检查针对当前 chat.py」**R→A**（作为历史 run 的对照仍有效）。
6. **PROJECT-STATE 的“现盘”状态**：仍写 `ins=500 del=0`、DLL `849e7281 / 49,952,768`，且 M4/M2 状态是 10-24 快照。⇒ 任何「当前补丁规模 / 当前 DLL / 当前未闭项」引用 **R→A**；其显式标注“冻结哈希（非现盘版本）”的段落可按史料引。
7. **HANDOFF 的交接状态**：10:16 快照仍写「M4-C 未开 / M4 三件 C 未开」；实际 M4-C 17:40 结项（`M4C-CLOSURE` `3309fb25`）、M4 19:05 验收（`M4-ACCEPT-lead`）、M2 已完整收口。⇒ 「HANDOFF 的未闭项清单 / 交接起点」**R→A**；须用新 HANDOFF。
8. **`_land_s1.py` 的冻结坐标**：S1 签署时实测 `b63b22d0` / 19,216 B（`INSPECTOR-S1B-REVIEW` 记录）；现盘 `bfe52d16864a7d96` / 24,426 B（task-32 补正时改，22:11），且台账 `scripts.land` / `module_shas.land` 已改成现值；**签署版无字节副本**（`_before/` 只有 pre-S1 `e11e69f8`）。⇒ 「S1 落账脚本冻结坐标可复算（b63b22d0）」**R→A**；须补 `land_before=b63b22d0` 或标 `unverifiable`（§2.5）。

**不算 R→A 的**：`chat.py` 的 S1 `288d2d85 → 1790f3a9` 是合法演进（v6 判决 + task-33/35 修复均有单），只要引 S1 读数时写签署坐标即可；`PREREG` 的旧坐标是预登记史料；`ledger` 的 addendum 保留原读数、`supersedes` 明确。

---

## 2 task-32 补正复核（台账 `081becbb`，原 `98bbf28b`）

### 2.1 五项逐条

| # | 检查 | 结果 | 证据 |
|---:|---|---|---|
| ① | 原读数逐字未改 | **通过（结构级）** | 15 个 `products` + 6 个 `variants` 的 `path/sha16` 现算全等（real_s1 `3df8d70b`、real_s2 `39b7f9de`、smoke `a067294a`、default_regression `39aa2505`、dry_*、cases_main、pre、default_unchanged；R1–R5 `4be0b287/4fe7e172/6ae013be/672f1a1b/9c1b01f2/98688eda`）；`four_state`（14 键）、`main_readings.checks`（含 `S1-02c:"未做"`、`P1b:"not_triggered"`）、`two_samples`、`verdict`、`red_proofs` 原值保留；addendum 只增 `addendum`/`verdict_addendum`/F1–F5、`module_shas` 10→14、`spec.lines`、geometry 文本、`deviations` 5→6。**限制**：旧台账 98bbf28b 无字节快照保留，故“逐字”用产品 sha + 保留字段核，不能做旧/新全文 byte-diff。 |
| ② | `frozen_numbers.geometry` 的 `+18` 修对 | **通过** | 现文本 `B project [4096+n_chat_A, 4096+n_chat_A+18)；chat_start_B=4096+n_chat_A+18（+18 的 18=project cells，不是常数偏移；换块 cells 时随之变）`；`spec.lines=132`；产品公式 A `[4075,4096)` / B 起点在此几何下自洽。 |
| ③ | `red_proofs.R5.red_kind` | **通过** | `R5.red_kind="case(M_CAP_refuses)"`；`expect_red=[]`、`fail_cases=["M_CAP_refuses"]`、`must_green` 保留；主臂 CAP 未触发绿 + 16 轮 case 级 red 的说明在 `note`，与 S1 判决口径一致（未把主臂写成红）。 |
| ④ | 新增 4 个 `module_shas` 与盘一致 | **通过，但含 1 条坐标问题** | `bed 88bbd4b19cc1cda5/15,956`、`run_s1_real c434d750aff953d5/9,572`、`run_m1_regression c188957e873b8e63/6,801` 均等；`land bfe52d16864a7d96/24,426` 等**现盘**，但**不是 S1 签署时跑出读数的 `b63b22d0`**（§2.5）。`module_shas` 未纳入 `_write_s1_corrections.py`（`scripts` 里已记 `bff31b15/10,113`），F3 的“0 漂移集合”漏了补正写入器本身。 |
| ⑤ | F2 三条 `notes_text` vs 实际 checks/fact_layer | **通过** | S1-01 / S1-02b / S1-05 的 `notes_text` 与 `S1-real.json` 的 `run.notes` **逐字相等**；`actual_checks=true`；证据对齐：A `own_hit_rounds=10/10`、B 归一 `10/10`（B 字面 last=**false**，hits 出现于重复轮次，见 S1 判决口径）、`sha_stable=done/unchanged/7`；三项判 `通过` 与四态一致。 |

### 2.2 F1 附加核对

`S1-real-default-regression.json` 的 `db_copy.sha16` 仍写 `237d8e1f5de9a382`（临时副本实际 `2d3bae59`），产品**未改**；correction product 的 F1 明确 `sha16_before=237d8e1f... / sha16_after=2d3bae59... / derived_rebuilt_by=_run_m1_regression / readings_unaffected=true`，并给出“5 个 DB 状态 selection (name,score) 逐字段相同”的证据。与我的 S1B 复核一致（派生表 `attr/value_kind` 重建，证据 8 张表逐行同）。**补正方式正确：不改产品，只加说明。**

### 2.3 结论

**task-32 = 读数层通过**；F1–F5 是标签/文本/口径补正，没有改任何读数或产品。**条件 1（阻断“冻结面可复算”强断言）**：`_land_s1.py` 签署版坐标丢失，须在台账补 `scripts_land_before: b63b22d0... / bytes 19,216`（或写 `unverifiable`），并保留/说明现盘 `bfe52d16` 是 task-32 后的落账器；否则“判据床 0 漂移”对落账脚本不成立。
**条件 2（弱）**：F3 的 14 件集合未含 `_write_s1_corrections.py`；建议加入或注明“补正写入器不属于 S1 冻结面”。

---

## 3 G4a 判定（含 G4a-2 独立验证、G4d）

### 3.1 事实链（独立复算）

1. **控制问句**：`tools/chat.py:68` `CONTROL_Q = "我的车牌号是多少？"`，注释 `# not in any block -- must not be "remembered"`；`cmd_chat` 把它当对照问，`cmd_m1` 把它作为第 1 问。
2. **selection 命中**：现盘 `_selection`/`R.search` 对 `CONTROL_Q` 的 top-1 唯一是 `conv_2026-10-25#L5`，`score=2.12518`（`_explain` 信号 `prop=plate, cov=0.11`）。
3. **L5 正文**：`memory_source.id=7` 的 `text` = **`我车牌是浙B-3F19K。`** —— 它是控制问句的**答案句**，**不是问句**。审计/lead 原句“正文就是控制句”不准确；但污染结论仍成立：**答案/事实在记忆里**，负例前提“问句所指内容不在记忆”为假。
4. **源/块面**：`memory_source` 10 行 = `profile` + `project` + `conv_2026-10-25` 父行 + 7 条摘录（`#L1,#L3,#L4,#L5,#L7,#L8,#L9`）；`memory_block` 仅 **2 行**（profile 50 tok / project 36 tok）；`indexable_sources` 实为 2。`doc` 10 行、`term`/`facet` 含 `车牌`/`b-3`/`f19`，冻结 `analysis.py 49e91c7b` + `retrieval.py 43f66019` 的 `build_index` **索引全部 10 行**，`_selection` 因此在宽面上返回 L5。`index_meta.docs=2` 是遗留键（§1.1），不参与此判。
5. **两条时间坐标**：现盘 `m1` CLI stdout `index v5 (analysis v4): 10 documents, 17 facets, 17 value kinds, 346 terms`，控制问句 `memory_hit`，随后 `KeyError 'conv_2026-10-25#L5' @chat.py:598`；M4-C 的 **m1 CLI 臂**产物 `run_after.json`（b09）当时是 `2 documents, 5 facets, 4 value kinds, 104 terms`、控制问句 `状态：no_evidence`、`检索：无匹配 → 不挂任何块`（此臂不是 M4-C 签名夹具臂，见 §3.4）。⇒ 污染是 **10 源库**的现态，不是 M4-C 签名夹具的读数。

### 3.2 三层拆分（lead 已采纳，本文按层判）

- **G4a-1 执行层**：`rows` 只保留有 `memory_block` 的 2 源，`order`/`want` 却来自全部 selection 名字 ⇒ `rows[name]` KeyError。现盘 `1790f3a9` 已改成 `missing=sel 中无块者 / sel_mountable=可挂载者 / want 取自 sel_mountable`，并落 `site3.skipped_no_block` event + crit、打印“跳过…（无 memory_block 行，不挂载）”、`turns.skipped_no_block`。`M4C-m1-rerun-v2`：exit 0、attaches 2、`hits=[]`、skip 1。**执行层修复有效，但不等价于负例恢复。**
- **G4a-2 状态判定层**：修复前 `E.decide(q, sel, ...)` 把 L5 当“长期记忆” ⇒ 控制问句 `memory_hit`、`refuse=false`，模型被调用；修复后 `E.decide(q, sel_mountable, ...)` ⇒ `n_selection=0`、`state=no_evidence`、`refuse=true`、`reason=personal fact, no memory…`、`reply` 为拒答、**`ask_count=0` / `answers=[]`**。`g4a2_checks` 5/5：`control_state_no_evidence / control_refuse_true / control_ask_zero / control_reply_refusal / mounts_profile_project`。
- **G4a-3 展示层**：`_explain` 现在每个命中行后标 `可挂载` / `无块行→不可挂载`，并打 `可挂载集：…`；控制问句显示 L5 但明确“不可挂载”，不再伪装成可用记忆。**独立复算**：在 `CHAT_DB`=临时 DB 副本上跑 `python tools/chat.py m1 --explain`，原始 CRLF 1,126 B；LF 归一后 **1,107 B / `dac30c8375502a2c`**（v2）。把新增标注 `  [可挂载]`/`  [无块行→不可挂载]` 与「可挂载集」行去掉后 **872 B / `3e8aae60685d2e55`**（= v1 签署值，逐字节回同）⇒ 只改展示、不改选择分数/读数，可逆。S1 已签的 872 B v1 仍是签署坐标；v2 是展示层修复后现值，须两列并写。

### 3.3 G4a-2 独立验证（不读他日志，读结构化字段 + 重跑他的计数产物）

我在 temp 只读/复算，不重跑 14B：

- 绿臂 `M4C-m1-rerun-v2.json`（`chat.py@1790f3a9`）：`control_q.decide.n_selection=0`、`selection_names=[]`、`state=no_evidence`、`refuse=true`、`reply="长期记忆里没有这条…"`；`control_q.ask_count=0`、`answers=[]`；`ask_by_question` 只有 3 个非控制问（各 1 次）⇒ 控制问 **零次 ask**；`g4a2_checks` 全 true；`stdout` 同时显示 `命中 1 条但均无 memory_block → 不挂任何块（跳过已记账）` + `跳过：conv_2026-10-25#L5(2.13)`。
- 红臂 `G4a2-red-variant.json`（`chat.py@bb083a1b`，pre-G4a-2，等价于“decide 吃 raw sel”）：`control_q.decide.state=memory_hit`、`refuse=false`、`ask_count=1`、`answers` 非空且生成 `您的车牌号是鲁QXXXX…`；`red_points` 4/4 true（`control_state_memory_hit / control_refuse_false / control_ask_nonzero / generated_answer_nonempty`）。
- **判定**：lead 要求的行为级红证成立——**绿臂 ask=0 + no_evidence + refuse + REFUSAL 文案，红臂回 memory_hit + 生成**。**限定**：红臂是 pre-fix 代码快照（bb083a1b），不是一行 `want→sel` 的显式变体；若要求“变体”严格是一次单点回退，建议让 executor 再给 `want→sel` 的显式变体（或把本臂标注为“pre-G4a-2 回归红”）。`E.decide` 入参从 `sel` 改 `sel_mountable` 是正确的面：`E` 是冻结件（`dccf7f01`），不能改它；也不收窄 `_selection`（`two` 等消费者共用）。

### 3.4 “负例判据作废”的边界：仅 `m1` CLI 臂；M4-C 夹具臂不受影响

- **M4-C 的签名臂 = 夹具臂**：`M4C-VERDICT-lead.md §2` 的 base/deleted 臂由 `redcheck_delete.py` 驱动；`:17 WANT_SEQ = [[], ["profile","project"], ["profile"]]` 的**索引 0 就是 `CONTROL_Q`**，`:99-103 fixed_selection` 对它返回 **`[]`** ⇒ `E.decide(q, [])` 直接是 `no_evidence`、不挂块、不生成。**该夹具臂的控制问句本来就空 selection、从未被 conv#L5 污染**；`loads` 顺序也是夹具写死的 seq 分配，不读 retrieval（`M4C-VERDICT:45` 不能当检索顺序证据）。⇒ **不写“M4-C 负例作废”**；M4-C 签名读数无需重签。
- **受影响的是 `m1` CLI 臂（真实检索）**：它的负例形态在修复前是 `memory_hit 但 0 块`（`E.decide` 吃到 `conv#L5`，状态标签错、模型仍可能被调用），修复后是 `no_evidence` 拒答。**该臂不是 M4-C 的签名臂**；`run_after.json` 的 m1 CLI 输出（b09 时 `2 documents`、`no_evidence`）只说明那个时点的 CLI 臂是干净的，不用于给签名夹具臂背书。
- **M4-B**：`run_m4_ablate_plate_a7.json 77e11a04` 四臂的“负”是**删掉车牌句的消融臂**（答案变 `苏A12345` 编造），车牌是**正例内容**，不把 `CONTROL_Q` 当“无记忆”判据。⇒ M4-B 已签结论不受 conv#L5 索引影响。
- **结论一句话**：**“负例判据作废”仅限 `m1` CLI 臂（其负例语义在当前 10 源库上不再成立）；M4-C 夹具臂的负例语义未受影响，M4-B 消融负臂也未受影响。** G4a 不是“仅 KeyError”：KeyError 只是执行层表征（G4a-1），状态标签（G4a-2）与负例前提（答案句在记忆里）才是判据层缺陷；但把它扩写成“M4-C 已签负例作废”是过度追溯。

### 3.5 G4d：`redcheck_delete.py` needle 唯一性（替 G4c）

- `redcheck_delete.py:15-16`：`NEEDLES = {1:'leases.reset(i, site="chat.place.fresh")', 4:'leases.reset(seq, site="m1.mount.before_load")'}`；`:17 WANT_SEQ`、`:99-103 fixed_selection`（confirm lead 的撤回依据）。
- 独立复算（逐行 `in`，含 signed/中间态）：

| 版本 | `tools/chat.py` sha16 | needle 1（site 1） | needle 4（site 4） |
|---|---|---|---|
| S1 签署 | `288d2d85` | **1 行 @270** | **1 行 @595** |
| task-33 中间 | `bb083a1b` | **1 行 @270** | **1 行 @618** |
| 现行（task-35） | `1790f3a9` | **1 行 @270** | **1 行 @629** |

- 结论：**两条 needle 在当前盘各唯一命中 1 行，≠1 的告警不成立**；G4b 的修改没有复制/移动承重行的语义（仅行号随新增行数漂移）。**lead 记的 `:618` 是 `bb083a1b` 中间态，现盘是 `:629`**——G4d 重跑的第一断言不要硬编码 618，应用 `NEEDLES[site]` 匹配 + 断言 `len(hits)==1`，并显式接受“行号可变、needle 唯一”这一现实。
- `redcheck_delete.py` 自身 `85d3b0b0855a83d4` / 6,513 B，M4-C 后未变；G4d 重跑时须同时断言 `WANT_SEQ` 仍为固定夹具（否则又会把“夹具口径”误读成检索顺序）。

---

## 4 附：本轮产物与边界

- 只读产物：`ANCHORS-CURRENT.md`（本报告唯一新增的锚文件）与本文；temp 读数未写仓库。
- **未做/不可判**：14B 重跑（不属我权限）；7B/archive-500/旧 DLL 基线（unverifiable）；task-35 的显式 `want→sel` 单点变体（若有，需 executor 再交一份，或按 §3.3 限定引用 pre-fix 回归红）。
- **待 executor 收口**：`LANDED-g4.json` 目前仍写 `judge_unchanged: E.decide 仍消费原始 sel`（task-33 时态），与 `1790f3a9` 的 G4a-2 不符；task-35 应把该台账更新为 `decide 消费 sel_mountable` + G4a-3 展示面 + G4a-2 红/绿产物 sha，否则台账与代码两列不一致。