# 外部审计（2026-10-25 21:15–21:35 快照）· lead 裁决（2026-10-25 23:40）

> 被审对象：`D:\llama-mem` 全面分析（用户转交）。**快照时点**：S1 干跑已落、S1 真机臂未跑（21:49 才跑）、`chat.py` 还是 v5 的 `b9010e9c`。
> 本裁决只写**与判决/纪律相关的部分**，不重复审计原文。

## 0 结论先行

审计**基本可信、方法对、有三条能改判决**。我逐条抽查后：**采纳 9 条、判为"快照已过期"2 条、判为"引擎级新里程碑"4 条**。最重要的一条是 **负对照被污染**——它把 G4 从"跑不起来"升级成**"判据作废候选"**。

## 1 我亲自复核过的（数字全部当场复算）

| 审计说法 | 我的复算 | 判 |
|---|---|---|
| `verify.sh` 写死 `ins/del == 500/0`，实时 600/0 | `git -C llama.cpp diff --numstat` = 20+17+491+13+31+28 = **600 / 0** | **成立**（第 1 项必红）|
| `kvslots.ask` 把引擎 `n<0` 折成 `""` | `kvslots.py:156` `return "" if n < 0 else ...` | **成立** |
| `.gitignore` 的 `_*/ ` 尾空格吞掉 `docs/_work` | `:45` 确实 `_*/ `（`cat -A` 见尾空格）；`git ls-files docs/_work` = **0**；`git ls-files PROGRESS-AND-ROADMAP.md` = **0** | **成立** |
| 检索索引含全部 `memory_source`，可挂载块只 2 条 | `retrieval.build_index` `SELECT id,name,label,text FROM memory_source`（10 行）；`block_rows` 是 LEFT JOIN ⇒ 有源无块 | **成立** |
| 补丁 `patches/persistent-memory.patch` = `db32faae` / 32,337 B / 600 | 复算 `db32faae83bec9fc` / 32,337 B / 600 行 | **成立** |
| DLL 与 MANIFEST 错位 | `tools/kvshim_vk.dll` = `9edbafa1` / 50,007,552 B | **成立** |
| `check_ablate_run.py` 硬编码 `np_==24` | 文件在 `kvmem/m2_visibility/m4/check_ablate_run.py`（不在 `tools/`）| **成立（位置需更正）** |
| 三份文档状态互斥（PROGRESS/FEATURES/HANDOFF）| 抽查 `FEATURES §0` 与 §3 互斥、`HANDOFF` 是 10:16 快照 | **成立** |

## 2 判为"快照已过期"（审计时点正确，现状已变）

1. **"`two` 的 `verdict=通过` 不要求全部声明检查；`_two_sha_stable` 恒 None"** —— 审计时点（v5）成立；**v6 已修**：`S1-03` 改默认红、`sha_stable` 在真机臂 `status=done/unchanged=true`（7 文件），S1 判决 `6bba350ab6621959` 有据。
2. **"S1 真机臂未跑"** —— 21:49 已跑，两采样读数完全一致（①10/10、②b 2/2、④ 1,155≤8,192、P-1a `2==2`、P-2 `0`）；判决同上。

## 3 能改判决的三条（按严重度）

### 3.1 ★负对照被污染 ⇒ **G4 升级为判据作废候选**

- 事实：索引 10 条源、可挂载块 2 条（profile/project）；`CONTROL_Q`（车牌问）的 selection 命中 `conv_2026-10-25#L5`，而该行正文就是控制句；`cmd_m1` 把 selection 名字直接当块行查 ⇒ `KeyError`。
- **判法（按"判据作废 ≠ 未通过"）**：先问"这条判据要求的东西在架构里有没有位置"——负对照要求"问句所指内容不在记忆里"，而架构**允许对话行入检索索引** ⇒ 位置有，问题在**索引/判据实现**，**不是"未通过"**。
- **结论**（2026-10-26 修订，见 §7 更正）：**污染范围仅限 `m1` CLI 臂** —— M4-C 的签名臂是**夹具臂**（`redcheck_delete.py` 的 `fixed_selection`，`WANT_SEQ[0]=[]` ⇒ `CONTROL_Q` 本来就是空 selection ⇒ `decide([])=no_evidence`，**从未被污染**）；M4-B 负臂是"删句消融"、车牌是**正例**，也不受影响。⇒ **M4-C / M4-B 均不需要因本条重签**；需重判的是 **`m1` CLI 臂的负例语义**（`memory_hit 但 0 块` → `no_evidence` 拒答），而该臂不是任何已签判决的签名载体。
- **处置**：G4 拆两半 —— **G4a 负对照重审 + 修复**（`_selection`/`order` 过滤到"有块行"的源，且**可见**：跳过必记账，不静默）；**G4b KeyError**（同一修复的自然结果）。修后重跑 `M4-C` 绿/红两臂 + 对照已签读数，再决定是否重签。

### 3.2 13 处锚腐烂 ⇒ 按自己纪律 R→A，但不回改旧判决

- 我复算的现行值：`chat.py 288d2d85`（我们 S1 改的，属**合法演进**，判决已写 old→new 双坐标）、`compare.py a852aacf`、`run_compare.json 1eb70291`、`planner.py 01507f6b`、`M2-ACCEPT-lead 21ec668d`、`PREREG 15451604`、`INSPECTOR-M1.8-FINAL 119e4771`、`patches/MANIFEST f35f8232`、`README 85f6a7d3`、`PROJECT-STATE 3d40d558`、`HANDOFF 3f660941`。
- **处置**：① **不回改**旧判决（签署时坐标当时有效，"锚=签署时坐标"是纪律）；② 新建 **`docs/_work/ANCHORS-CURRENT.md`** 作"现行锚"唯一入口，文档引用它而不是散落字面量；③ 腐烂清单由 inspector **独立复算**后入档（含"哪些结论由 R 降 A"）。

### 3.3 `kvslots.ask` 折 `n<0` 为 `""` ⇒ "引擎拒绝"与"空答"不可分

- 影响：S1 的 ① 判据是"答案含事实"，空答=未命中 ⇒ 偏**保守**（不会假绿）；但**"引擎拒绝"会被读成"模型没答出"**，属可解释性缺陷。
- **处置**：P2 必修（传播 `-1`/显式异常），修后 S1 判决补一句"空答语义已可区分"，**判定不变**。

## 4 判为"新里程碑"（不进 M2 范围）

引擎四条不变量（共享 cell 移动改所有引用者位置语义 / 负 delta 静默回收 cell / `pos_move` 不碰 `shift[]` / preflight 缺 `n_rot_k == n_rot` 与 2 的幂）⇒ 开 **M6「引擎不变量 fail-closed」**，**先写红证再改**（`chat.py` 的 `base - cur` 可为负 ⇒ 负 delta 路径**可达**，不是理论风险）。**M2 完整 判决不因此打折**：S1 是两段**顺序**会话，未触共享 cell 并发移动。

## 5 派单

| 单 | 内容 | 归属 |
|---|---|---|
| **task-33**（在跑）| G4 根因 + 可见修复 + M4-C 重跑对照 —— **范围扩为 G4a+G4b**（负对照污染必须写进根因报告）| executor |
| **task-34** | **尺子统一 P0**：`verify.sh` 改关系断言（实时==归档，不写死 500）、`MANIFEST` 记 600 版并对 500 版标 archive、`.gitignore:45` 修尾空格放行 `docs/_work/**`、`check_ablate_run.py` 的 `np_==24` 改"读声明值+三态"、`README/PROJECT-STATE/HANDOFF` 加 as-of 声明（**不重写长文，只加 banner + 指向 `ANCHORS-CURRENT.md`**）| executor |
| **inspector** | ① 复核 task-32 补正 addendum（7 条）② **13 处锚独立复算**（含"哪些结论 R→A"）③ 只读核 G4a 负对照：`CONTROL_Q` 的 selection 全链是否真的把控制句正文当记忆 | inspector |
| **M6** | 引擎四不变量 fail-closed（红证先行）| 待 G4/尺子统一后开 |

## 6 我对审计的一句话回应

它说的"最值钱的是证据方法论"我认同，但它同时点出了这套方法论的**自噬点**：**证据被 ignore 挡住、锚会腐烂、门禁自己过期**。所以 P0 不是"再加实验"，而是**把尺子统一**——这正是我上面 task-34 的内容；而它查出的负对照污染，是把"判据作废"那条纪律真正用上一次的机会。
---

## 7 更正记录（2026-10-26；两次自我推翻，留痕不回改上文）

| # | 我先前判的 | 证据 | 更正 |
|---|---|---|---|
| C1 | "G4c：M1.8 改查询侧使 selection 顺序变化 ⇒ M4-C `loads` 签名漂移" | `redcheck_delete.py:17` `WANT_SEQ=[[],["profile","project"],["profile"]]` + `:99-103` `chat._selection = fixed_selection`（写死 seq 分配）| **撤回 G4c**。M4-C base **不读 retrieval 顺序**；`m1` CLI 臂按分数排序。两者 `loads` 相反是**口径差，接受**。改为 **G4d**：用**夹具臂**重跑才能恢复回归链 |
| C2 | "`M4-B`/`M4-C` 的负例降级为待重判" | 见 §3.1 修订段 + `INSPECTOR-ANCHORS-AND-G4A.md c7df4063`：夹具臂 `CONTROL_Q` 空 selection；M4-B 负臂为删句消融 | **收窄为 `m1` CLI 臂**；M4-C/M4-B **不需重签** |
| C3 | 措辞"`conv#L5` 正文即控制句" | inspector 逐字核：正文是 **`我车牌是浙B-3F19K。`（答案句）**，不是问句 | 改为"**答案句**"；若"控制句"指答案句则成立，按字面问句则**不成立** |

**方法论记录**：C1/C2 都源于"采信转述而未先核夹具源码"。教训与项目纪律一致——**证据先于断言；转述也是断言**。
