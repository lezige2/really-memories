# G4 收口（lead 判决，2026-10-25 22:40）

> 链：`task-33`（G4a-1 执行面 + G4b）→ `task-35`（G4a-2 决策面 + G4a-3 展示面）→ `task-36`（G4d 夹具臂回归链）。
> 起始症状：`m1` 真机臂 `exit 1 / KeyError 'conv_2026-10-25#L5' @ chat.py:598`，M4-C 绿臂回归链断。
> 状态：**已销号**（§5 有一处待 inspector 独立复核的读数同一性；复核不过则转"未通过"）。

## 1 四层判决（分开算，不合）

| 层 | 症状 | 修法 | 判 |
|---|---|---|---|
| **G4b 执行面** | `rows[name]` 缺块行 ⇒ KeyError | `rows` 过滤到有 `memory_block` 的源；无块命中**显式记账**（`_event site3.skipped_no_block` + `_crit status=skipped` + 打印「跳过：…」）；挂载循环防御 `die()` | **通过**（`m1` exit 0、跳过可见、无静默、回归全绿）|
| **G4a 判据层** | 检索面 10 源 / 挂载面 2 源；`CONTROL_Q` top-1 = `conv#L5`（正文 = **答案句** `我车牌是浙B-3F19K。`）⇒ 负对照"问句内容不在记忆里"在一个允许对话行入索引的架构里**不可成立** | 不修判据、不重建索引 | **判据作废**（口径：**仅 `m1` CLI 臂**；`M4-C` 夹具臂 `WANT_SEQ[0]=[]` 空 selection 从未污染；`M4-B` 删句消融负臂不受影响 ⇒ **M4-C/M4-B 不重签**）|
| **G4a-2 决策面** | `E.decide(q, sel, …)` 吃**未过滤** selection ⇒ 0 块挂载却 `memory_hit`/`refuse=False`/模型被调用并编造「鲁QXXXX」 | `sel_mountable`（有块行）+ `E.decide(q, sel_mountable, …)`；不动 `evidence.py`（冻结）、不收窄 `_selection`（`two`/chat 共用）| **通过**（`CONTROL_Q` → `no_evidence`/`refuse=True`/`ask=0`/`answers=[]`/回 `REFUSAL`；单点变体 `want→sel` 四点回红）|
| **G4a-3 展示面** | `_explain` 把不可挂载命中打印成"检索结果" | 每行标 `[可挂载]/[无块行→不可挂载]` + 「可挂载集：…」+ `explain_version: 2` | **通过**（可逆性脚本化：去 v2 标注后逐字节回 `3e8aae60`）|
| **G4d 回归链** | M4-C 绿臂能否在当前 `chat.py` 重跑 | 用**夹具臂** `redcheck_delete.py`（不是我先前判的 `m1` CLI 臂） | **通过**（base/site3-green/site3-red 读数与签署 `12950f6a`/`f3f6ce7f`/`dd46774c` **逐字段同**，仅行号/`chat_py_sha16` 随增长变）|

## 2 两次自我撤回（留痕，不回改上文）

| # | 我判的 | 证据 | 更正 |
|---|---|---|---|
| C1 | **G4c**：M1.8 改查询侧 ⇒ `loads` 顺序漂移 ⇒ M4-C 需重签 | `redcheck_delete.py:17` `WANT_SEQ` + `:99-103` `fixed_selection` 写死 seq 分配 | **撤回**。M4-C base 不读 retrieval 顺序；`m1` CLI 臂按分数排序（project 6.24 > profile 4.23）。两者 `loads` 相反 = **夹具口径差，接受** |
| C2 | **task-36 第 3 项**："删 `m1.mount.before_load` 的 reset ⇒ orphan 36→86" | `M4C-CLOSURE-lead.md` §4.3 总表：**36→86 是 site3 `m1.unmount.after_detach`** 的承重读数；site4（`mount.before_load`）的"删掉必须红"判据**签署时即作废**（后随 `load_into` 兜底、结构性不可掩） | **撤回**。site4 臂"无观测效果"是**签署预期**，不是回归失败；承重臂是 site3，已复验 |

**方法论**：两次都源于"采信转述/自己旧笔记而未先核源码"。纪律原话：**证据先于断言；转述也是断言。**

## 3 site4 的两条如实记录（不掩盖、不升格）

- **字面 site4 红臂无观测效果** ⇒ 与 `M4C-CLOSURE-lead.md §4.3` 的"判据作废"一致，**不是新失败**，四态记 **未通过（判据作废）**。
- **site4 两臂 `coverage_not_met`（declared site4 vs observed site3，rc 5）** ⇒ 结构性（被 site3 掩码 + 观测面不覆盖），记 **未接上**，不阻塞。

## 4 未做/另单（诚实清单）

- **`index_meta.docs="2"` vs `doc` 10 行**（M1.8 遗留、旧构建器元数据；不是 KeyError 直接原因）⇒ **未做**，索引侧另单。
- **索引层"对话行是否该入检索面"** ⇒ 本单**不修**（判据层问题已按"作废"处理；改检索语义会动 `two`/chat 共享读数，须单独立项 + 红证）。
- **M6a 引擎不变量**（负 delta / 共享 cell / pending shift / `n_rot` 幂次）⇒ 另里程碑，红证先行。

## 5 坐标（现行）

| 件 | sha16 | 备注 |
|---|---|---|
| `tools/chat.py` | **`22081c411c64fbe7`** / 75,310 B | 签署坐标链 `288d2d85`(S1) → `bb083a1b`(G4b) → `1790f3a9`(G4a-2/3) → `22081c41`(+`explain_version`) |
| `m1 --explain` | v1 `3e8aae60685d2e55` / 872 B → **v2 `dac30c8375502a2c` / 1,107 B**（含 `explain_version` 行实测 `c4cbad83784e647f` / 1,126 B）| superseded-by-design，可逆 |
| 增强产物 | `M4C-m1-rerun-v2 6c3e3f55`、`G4a2-variant-want2sel 9653e1d9`、`G4a2-red-variant 18127962`(prefix-regression)、`G4a2-containment b07a4608` | |
| 台账 | `LANDED-g4 7a9d6cea`、`LANDED-g4-addendum d5fe3e3e`、`LANDED-g4a2 ae44a406`、`LANDED-g4d 3ab31e41`（`m4c_leases/out/LANDED-g4d 6768a11c`）| |
| 夹具臂产物 | `M4C-fixture-rerun b997191a` | needle 唯一：site1 `:270` / site3 `:594` / site4 `:630`（现盘实测，不硬编码）|
| S1 台账 | `LANDED-s1-real **797a8450**`（重生成，原读数 `original_readings_intact=true`；F1 双坐标已补）| `_land_s1.py` 签署 `b63b22d0` 标 `unverifiable`（无 `_before`、git 未跟踪）；`_write_s1_corrections.py bff31b15` 显式排除并给理由 |
| 锚 | `ANCHORS-CURRENT.md **41a5b29b**`（35 行、两列四态）| banner 只指路径不钉 sha（v1 `a54c8109` 曾钉、已去） |

## 6 签署

**G4 = 已销号**：
- **可执行性**（G4b）：通过；
- **状态标签**（G4a-2）：通过 —— `m1` CLI 臂负例不再是"`memory_hit` 但 0 块 + 编造"，而是"`no_evidence` 拒答 + `ask=0`"；
- **展示面**（G4a-3）：通过（可逆）；
- **回归链**（G4d）：通过 —— M4-C 夹具臂 base/site3 三读数与签署逐字段同；
- **负对照污染**（G4a）：判据作废，**范围限 `m1` CLI 臂**；`M4-C`/`M4-B` 判决**不动**。

**不签**：索引层"对话行入检索面"该不该改（另单）；`index_meta.docs` 修复（另单）；site4 "删掉必须红"（判据作废，重签不可）。

## 7 inspector 独立复核（2026-10-25 22:48，`INSPECTOR-G4D-REVIEW.md`）

- **§5 读数同一性 = 通过**：base `12950f6a→87f060bd`（`loads` 50/50/49、36/36/35 逐字段同；attaches 2 / attach_ok true）、site3-green `f3f6ce7f→960af172`（orphans 0/0/0）、site3-red `dd46774c→f05e1de9`（die 文案**逐字同**）。
- **"只行号/`chat_py` sha 变"不精确**（inspector 更正）：还变了 `harness_sha16`（`b48f037f→12d3f37c`）、`def_fp` 行号、`variant_sha16`、`src/variant_line_count` —— 属调度/血缘，不是读数差。**采纳此措辞**。
- **§1 判决维持**：G4 已销号；G4d 本体**无失败**。

## 8 两条 gap（inspector 要求如实写，不许当"全绿无保留"）

1. **36→86 不在 G4d 的重跑范围**。G4d 的 DELETE red/green 两臂 orphan 全 **0/0/0**；36→86 属 `M4C-CLOSURE-lead.md §4.3` 的 **M4-C-4 测量臂**（b10：`m4c4/M4C4-deleted 4ada6cec`、green `08a197d2`），inspector 复算一致但**本轮未重跑该臂**。
   **字段级更正（2026-10-25 23:00，inspector 逐字段核出）**：语义已由 `stop_item.orphan_36_86_scope`（`rerun_this_round=false` / `verdict="未做（沿用 b10 历史读数，未重跑）"` / `non_blocking`）与 `four_state["36→86（M4-C-4 测量臂）"]` 如实记录，**但 `gaps.orphan_expectation` 字段本身当时没写"未重跑"** ⇒ 已要求补一行；本判决以 `stop_item` 为准，补行后关闭。
   ⇒ 四态记 **未做（沿用 b10 历史读数，未重跑）**；**不得**把 b10 读数写成"G4d 重跑结果"。**补跑该项可另开单**（非阻塞，G4d 复验的是"删了必须红（die）"，不是"36→86 复现"）。
2. ~~**F1 坐标不一致**~~ **已关闭（2026-10-25 23:00）**：`LANDED-s1-real.json` 重生成 = **`797a845029f3f374`**，`addendum.F1_db_label.actual_dual_coordinates` 已给 `task32_copy_sha16 = 2d3bae59`（correction `db472434` 沿用、不可回改）/ `this_round_copy_sha16 = 30d224c4`（22:11 写补正产物时实测，现盘复测同值），附 `why_two_actuals`（G3 派生重建非确定、同内容不同重建批次）。inspector 行级复核：`chat.db` 与 temp 副本 **10 表中 8 表逐行相同**（doc/facet/index_meta/memories/memory_block/memory_source/memory_source_excerpt/term），仅派生 `attr`/`value_kind` 不同 ⇒ "同内容不同重建批次"成立。**不动 correction 产物**是纪律，做到。

**决议**：G4 判决**生效**，措辞为"§1 四层全通过；§8.1 记未做（沿用 b10、字段待补一行）、§8.2 已关闭"。

## 9 复审（2026-10-25 23:00，`INSPECTOR-RULER-REVIEW.md 640ac760` / `INSPECTOR-G4D-REVIEW.md 2995e671`）

- banner 三份 **通过**（`README 5466f139` / `PROJECT-STATE fafa049f` / `HANDOFF 9bb387c2`；全文无硬 sha）；
- F1 双坐标 **通过**（见 §8.2）；
- `LANDED-g4d` orphan **语义如实、字段缺一行**（见 §8.1）。