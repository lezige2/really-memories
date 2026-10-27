# DOCS-CONVERGENCE —— 文档收敛台账（2026-10-25 23:30，doc-scribe）

> **纪律**：每改一个文件，先算旧 `sha256[:16]`、改完算新值，old→new 入本表；每条改动给**一句话理由** + 我**当场核过的 `file:line`**。
> **禁止项（全程遵守）**：不改已签判决读数 / 不删任何文件 / 不碰 git（无 `add/commit/push/rm`）/ 不改代码 / 不跑 14B。
> **本地只许两份新文件**：`INDEX.md` + 本文件（lead 口径）；归档动作只 `mv`。
> 复算：`sha256sum <f> | cut -c1-16`；字节 `wc -c`。

---

## 1 old → new 对照（全部现场算，**不抄文档里的值**）

| # | 文件 | old sha16 / B | new sha16 / B | 动作 |
|---|---|---|---|---|
| 1 | `docs/_work/INDEX.md` | —（新建） | `db87aa8766b5b9e3` / 16,494 | **新建**：42 行清单 + 权威层级 + §0.5 旧文档处置规则（含 GitHub 发布口径）+ 术语表 + §3 归档区 |
| 2 | `PROGRESS-AND-ROADMAP.md` | `dec66017f54892a7` / 215,927 | `6de6b5dd946b1df2` / 217,951 | 修 6 处矛盾 + §0.1 头加权威口径句 + §0.1 标题纠偏 |
| 3 | `FEATURES.md` | `3fa067a454af9fb2` / 16,240 | `1f9e25404e54c1b7` / 16,739 | 修 3 处（§0 行10 / §3 M2完整 / §3 注） |
| 4 | `README.md` | `5466f139846a3b0a` / 22,222 | `6f4eea8ef35e1857` / 26,559 | **对外自足改版**（banner 发布口径 + 权威口径句 + 19 处本地化 + §6 尺子更新 + §7 目录纠偏 + §9 重写 + **新增 §12 依赖/复算/未做/免责**） |
| 5 | `PROJECT-STATE.md` | `fafa049fa9e1ebf4` / 52,015 | `d61083cfcee4a909` / 52,250 | banner 后 +1 行（权威口径） |
| 6 | `HANDOFF.md` | `9bb387c278da34e3` / 9,993 | `fc61c70eafc44552` / 10,228 | banner 后 +1 行（权威口径） |
| 7 | `docs/_work/DOCS-CONVERGENCE.md` | —（新建） | 自指不入表（见 `sha256sum docs/_work/DOCS-CONVERGENCE.md`） | **新建**（本台账） |

**归档（`mv`，内容字节不变 ⇒ sha 不变）**：
`docs/_work/archive/BOOTSTRAP-PROMPT.md` `cfb00459bb72b603` · `archive/INSPECTOR-M4C-P1.md` `f28790ce73098f27` · `archive/INSPECTOR-M4C-P1B.md` `395b22eff2d88c84`。

---

## 2 逐条改动：理由 + 当场核过的 `file:line`

### 2.1 `PROGRESS-AND-ROADMAP.md`（状态文档；只改与事实不符的句子 + §0.1 口径）

| # | 位置 | 原句（问题） | 改成 | 一句话理由（核过的证据） |
|---|---|---|---|---|
| P1 | `:144` §2.1 行14 | M4-C「**未开始**（M4 最大的洞）」 | ~~未开始~~ **已闭（17:40）**：四条承重表只 `m1.unmount.after_detach` 承重（orphan 36→86 / green 0），site1 无效果、site2/4 判据按读码作废；证据改指 `M4C-CLOSURE-lead.md 3309fb25` | 与本文 `:936` §6.6「已结项 17:40」、`:1767` §13.2 自相矛盾 |
| P2 | `:163` §2.2 | 「**M2 完整**（pinned 驱逐 / 多序列单会话 / 位置租约）**仍未做**」 | 删除线 + **已收口（22:20，L1/L2/P1/S1 全签，`M2-FULL-FINAL-lead.md 84ec4e3f`）** | `M2-FULL-FINAL-lead.md:9`「**M2 完整 = 已验收**」 |
| P3 | `:195` §2.3 | 「⇒ M2 的**规划器本身仍未实现**，只有「几何冻结」」 | 删除线 + **已推翻：规划器已实现并验收（19:45，`M2-ACCEPT-lead.md 6f26bce0`；r2 `c95e0b7c`），M2 完整亦已收口** | 同文档 `:152` 行22 已写「已验收」、`:1635` 已闭条目 |
| P4 | `:1960` 附录 | 「工作树内因此**只剩三份受跟踪 md**」 | 改为「84 份中 **80 份 md 已于 20:20 按字节回填**（`LANDED-restore.json fe1f2ff914a80196`：`80/80 byte_equal`、`skipped_existing=3`、`identical=2`、`still_missing_after=[]`）⇒ 不再成立；`.gitignore` 已放行 `docs/_work/**`」 | 本文 `:60` §0.1 回填公告 + 紧邻的 `:1957` 修正已判"不再成立" |
| P5 | `:2145` §15.5 | 「本轮：85 份 / 1,707,063 B，**未删任何文件**」 | 删除线 + **阶段 1 未删、阶段 2 逐文件复验后删 84 份、其中 80 份已回填** | 本文 `:1958` 两阶段 + `:2520` 同口径 |
| P6 | `:2522` 附录 | 「工作树内只剩三份受跟踪 md」 | 「**80 份 md 已于 20:20 按字节回填**（另 3 份本是现行版、2 份 identical）⇒ 不再成立」 | 同 P4 证据 |
| P7 | `:58` §0.1 标题 | 「（2026-10-25 20:20，**这一条覆盖性最强**）」 | 「（2026-10-25 20:20；**本节只覆盖档案回填，不是里程碑状态**）」 | inspector 指出"覆盖性最强"会被读成"状态权威"；`:1883` 自述权威在 §13 |
| P8 | `:58` §0.1 头（新增行） | —（无权威口径句） | 加**权威口径句**（与 INDEX / README 逐字一致，见 §2.5） | lead 指令 + inspector 判据（§13.x 权威 / §2.1-2.2 摘要 / §0.1 仅回填 / 坐标看 ANCHORS） |

> 统一标记：6 处矛盾修复均带 `（2026-10-25 收敛，见 docs/_work/INDEX.md）`。
> **未动**：§13.4.1（`:1816` 起，已有最新结论段）、§13.2/§6.6/§13.4、任何已签读数、其它句子。

### 2.2 `FEATURES.md`（能力账；只改与 §3 / 状态源互斥的行）

| # | 位置 | 原句 | 改成 | 理由 |
|---|---|---|---|---|
| F1 | `:22` §0 行10 | `M4-C leases 真调用 \| **未开始** \| 无 \| 无` | `**已闭（17:40）** \| M4C-CLOSURE-lead.md=3309fb25 · M4C-VERDICT-lead.md=d7eb117d \| **R**` | 同文件 §3 `:171` 已写「已闭」⇒ §0↔§3 互斥 |
| F2 | `:174` §3 行「M2 完整」 | 「预登记已批、**L1 施工中**…**S1 施工中**（口径 v3 `36325e12`）」 | 「**已验收（22:20，`M2-FULL-FINAL-lead.md 84ec4e3f`）**…**S1 已签**（口径 **v6 `ae2d88ad`**，判决 `6bba350a`）…v3 已作废」 | §0 行4「M2 完整 已验收」+ `M2-FULL-S1-SPEC-lead.md` 标题「v6（最终）…v1–v5 全部作废」 |
| F3 | `:167` §3 表头注 | 「`M2 规划器` 已实现（**未验收**）」 | 「已实现并**验收**（19:45，`M2-ACCEPT-lead.md 6f26bce0`）、**M2 完整亦已收口**」 | 与 §0 行3/行4、PROGRESS `:150` 互斥 |

> lead 原单说"4 行（M1.8 / M2 规划器 / M2 完整 / M4-C）"：现状里 `M1.8`（§0 行2）与 `M2 规划器`（§0 行3）**已是"已验收"**（审计快照后被 executor 对齐），故实际只 3 处可改。

### 2.3 `README.md` —— 对外自足改版（**唯一对外文档**）

| # | 位置 | 改动 |
|---|---|---|
| R1 | `:3-6` banner | 去掉所有 `[...](./...)` 可点链接 → 改为 `本地` 路径文字；新增 **发布口径行**：「**本仓库只发布本 README 一份文档**；完整状态/判决/证据文档仅存于本地工作区（`docs/_work/`）…下文路径都是本地线索，不承诺可点」；新增 **权威口径行**（逐字同 §2.5） |
| R2 | 19 处 `PROGRESS §x` / `进度文档 §x` | 一律前置「**本地**」，并标「（不随仓库发布）」；覆盖 §2、§3.2、§3.3、§4.2、§5、§6、§8、§10.9、§11.1、§15.3 |
| R3 | `:148` §5 头 | 新增**收敛注**：E10 症状在 14B 上不复现、M2.5 已**销号**（本地 PROGRESS §2.2/§13.11）；本节是 **7B 代现场记录**，现行已验收 M2 规划器/M2 完整/M4/M5 |
| R4 | `:97` §3.2 行2 | 「记忆读取能力 半真的」行补「（**7B 代读数**；14B 该症状不复现，见 §5 收敛注）」 |
| R5 | `:190` §6.1 / §6.2 | 「9 项断言，8 绿 1 红」→ **「12 项关系断言，ALL PASS（rc 0）」**；§6.2 重写为「实时 600 / 归档 500，关系断言不写死数字」—— 依据：**当场跑 `bash verify.sh` = `ALL PASS (12 项)`，rc 0** |
| R6 | `:236` 目录表 | `README.md` 行 → 「**唯一对外文档**（GitHub 只发布这一份文档）」 |
| R7 | `:238`/`:239` 目录表 | `PROJECT-STATE.md` 行「原件移至备份（工作树内不再有）」→「**已于 2026-10-25 20:20 按字节回填（史料，不随仓库发布）**」；`docs/` 行「仅 `_work/`、目录本体留空」→「`_work/`（本地文档库）+ `README-PHASE1-ENGINE.md`（原件保留）+ `legacy-2026-10-24/`（史料）」 |
| R8 | `:335-357` §9 | **重写**为"发布口径 + 6 行本地文档表（含 `docs/_work/INDEX.md` / `ANCHORS-CURRENT.md`）+ 仓库内 md 现状"；并把 lead 要的半句加上：**「已从工作树移出（后又于 2026-10-25 20:20 按字节回填 80 份…）」** |
| R9 | 文末（新增 §12） | **§12 依赖 / 一键复算 / 明确未做 / 免责**：依赖表（llama.cpp fork、Vulkan bin、`kvshim_vk.dll`、Python 3 仅标准库、14B q8_0 `-c 8192` / `n_seq 8` / ≥10 GB 显存、`*.gguf`/`*.kvmem` 不入库）；`bash verify.sh` 一键；5 条明确未做（无服务端 / 未训练 / 真并发未验 / 跨布局对照臂未做 + M6 另立 / pin 驱逐未接主路径）；免责（无 SLA、无输入净化层、派生层可重建） |

**自检**：`grep -n "](\./" README.md` ⇒ **0 命中**（无指向仓库内本地文档的可点链接残留）。

### 2.4 三份状态文档只加 banner 后一行（正文一字未改）

`README.md:4` / `PROJECT-STATE.md:5` / `HANDOFF.md:5` 各加同一句权威口径（见 §2.5）。

### 2.5 权威口径 —— **同一句，三处逐字一致**

> **里程碑状态以 `PROGRESS-AND-ROADMAP.md` §13 各收口节为准；§2.1/§2.2 只是索引/摘要（§1883 行自述"本表是摘要，不是权威"）；§0.1 只记录 80 份档案回填公告；坐标/sha 以 `docs/_work/ANCHORS-CURRENT.md` 两列四态为准。**

落点：`PROGRESS-AND-ROADMAP.md` §0.1 头 · `docs/_work/INDEX.md` §0 首行 · `README.md` banner（`PROJECT-STATE`/`HANDOFF` banner 引同一句）。
**依据**：`PROGRESS-AND-ROADMAP.md:1885` 自述「本表是摘要，不是权威…权威在 §13.2/§13.3/§13.4/§13.5」（当场 grep 核过）；`§0.1` 正文实测是档案回填公告（`:58` 起）。

> **行号漂移说明**：权威口径句里的「§1883 行」是 lead/inspector 引用时**那一版**的行号；本轮在 §0.1 头插了 2 行，该句（`本表是摘要，不是权威`）现实测在 **`:1885`**。**行号会随文档增长漂移 ⇒ 引用该句请用内容检索**（`grep -n "本表是摘要，不是权威"`），不要引行号当锚。

---

## 3 归档（**已执行**，`mv` 不删、不入库）

| 类 | 文件 | 被谁取代 | 现行文档引用（全仓 grep md/py/sh/json） | 结果 |
|---|---|---|---|---|
| A | `BOOTSTRAP-PROMPT.md` | `HANDOFF.md` §1 | **0** | ✅ `docs/_work/archive/BOOTSTRAP-PROMPT.md` |
| A | `INSPECTOR-M4C-P1.md` | `M4C-CLOSURE-lead.md` | **0** | ✅ `docs/_work/archive/INSPECTOR-M4C-P1.md` |
| A | `INSPECTOR-M4C-P1B.md` | `M4C-CLOSURE-lead.md` | **0** | ✅ `docs/_work/archive/INSPECTOR-M4C-P1B.md` |
| B | `HANDOFF-M4C.md` | `M4C-CLOSURE-lead.md` + PROGRESS §6.6 | 1（`INSPECTOR-M4C-P3.md:14`） | ⏸ 留原地，标 `superseded`（lead 裁定：断链比整洁严重） |
| B | `M4C-外请教要.md` | `AUDIT-RESPONSE-lead.md` | 2（`HANDOFF-M4C.md:282`、`INSPECTOR-M4C-P1.md:186`） | ⏸ 留原地，标 `superseded` |

`docs/_work/archive/` 由 git-keeper 加 `.gitignore`（**本地史料，不入库**）；本次**未执行任何 git 命令**。

---

## 4 计数口径（**以脚本复算为准**）

- 基线 41 份：**18 `current`（内含 `ANCHORS-CURRENT.md` 坐标权威特殊项 1）/ 18 `report` / 5 `superseded` / 0 `void`** —— 与 **inspector 2026-10-25 复核意见一致**。
- 补 `INSPECTOR-M6A-FIX.md`（`6aca6e62` / 9,214 B）为 `report` ⇒ **42 份 = 18 current / 19 report / 3 archived / 2 superseded / 0 void**（脚本按状态列逐行计数）。
- **lead 转述的「18 current + 1 特殊 + 17 report + 5 superseded = 41」**：合计与我一致，**项数归属差 1**——我按逐行状态列复算，`report` 是 18 不是 17（多出的那 1 份是 `M1.8-CONFLICTS-inspector.md`，其内容为 inspector 的定位/判定报告，属 report 而非 current）。**此处以脚本为准并留痕**（"转述即断言"）。

---

## 5 四态报告

| 任务 | 判 | 证据 |
|---|---|---|
| ① README 对外自足改版 | **通过** | `README.md` `6f4eea8e` / 26,559 B：banner 发布口径 + 权威口径句 + 19 处本地化 + §5 收敛注 + §6 尺子更新（当场 `bash verify.sh` = 12/12 ALL PASS, rc 0）+ §7 目录纠偏 + §9 重写（含 lead 要的半句）+ **新增 §12 依赖/复算/未做/免责**；`grep "](\./"` = 0 |
| ② PROGRESS §0.1 头一位 + 6 处矛盾 | **通过（6 处 + 口径 2 处）** | §2.1 P1–P8；指定 4 处全覆盖，另补 2 处同源残留；**未动 §13.4.1 与任何已签读数** |
| ③ FEATURES §0 与 §3 对齐 | **通过（3 处）** | F1–F3 |
| ④ INDEX 计数 / 漏项 / 权威句 | **通过** | 42 行、状态分布脚本复算、`INSPECTOR-M6A-FIX.md` 已补、权威口径句逐字一致、§0.5 加 GitHub 发布口径（第 4 条） |
| ⑤ 归档 A 类 3 份 | **通过（已执行）** | `docs/_work/archive/` 3 份，`ls` 核过；未删、未 git；B 类 2 份留原地标 `superseded` |
| 不许：改判决读数 / 删文件 / 碰 git / 改代码 / 跑 14B | **未做（遵守）** | `*-ACCEPT/CLOSURE/VERDICT-lead.md` 零改动；无 `rm`/`git`；无代码改动；未起模型 |

### 未接上 / 待他方（本台账只留痕，不代做）

1. `docs/_work/archive/` 的 `.gitignore` 条目 —— **git-keeper** 负责；我未碰 git。
2. `INSPECTOR-M6A-FIX.md` 的**结论**（现=仅 item3 未通过）—— inspector 说 executor 终版后由他更新；INDEX 已按当前结论登记，**更新时改该行 + sha**。
3. `M2-FULL-S1-ACCEPT-lead.md` 判决署名 `6bba350a` ≠ 现值 `c938da88`（22:20 更新）—— ANCHORS #17 已登记；INDEX 行内已写双值。
---

## 7 第二轮：ANCHORS 头部 + INDEX 补 4 行（2026-10-25 23:45；**本节曾被外部覆盖，已重放**）

> 只改文档；`PROGRESS`/`FEATURES`/`README` **未碰**；未新建第三份文件；无 git、无删除。
> **事故留痕**：本节首次写入后，`DOCS-CONVERGENCE.md` 于 **23:39** 被外部写回 §1–§5 状态（13,600 B，`214b0e44`），本节内容丢失；现**按原文重放**。**首次写入后的 `39d2f9ec0994cc87` 作废**，以本节末的现行 sha 为准。

### 7.1 old → new

| 文件 | old sha16 / B | new sha16 / B | 改动 |
|---|---|---|---|
| `docs/_work/ANCHORS-CURRENT.md` | `d393d290680fc27a` / 16,847 | **`0d36bbe845080b47`** / 17,660 | `:9-10` 加 2 行：①字节可复现（tracked @sha16）原文（main 受跟踪 **31** 个 `@<sha16>` = 28 裸 + 3 provenance 后缀，clone **31/31**；C3 `595cedb^..595cedb` 的 `--ignore-cr-at-eol` diff 空 103 files/36,903/36,903；C3b `9c8b25f` legacy 归一后 3/3；不覆盖未跟踪 `docs/_work` 与 `full`-only）；②项目级约定「**锚 = 工作区字节 `sha256[:16]`，不用 `git show` blob**」+「**不存在 27**」。表体整体下移 2 行 ⇒ 引锚按内容检索 |
| `docs/_work/INDEX.md` | `db87aa8766b5b9e3` / 16,494 | **`484862e640afa5d4`** / 17,750 | 补 4 行 + 4 处 sha 校正（见 §8）+ 统计脚本重算 |
| `docs/_work/DOCS-CONVERGENCE.md` | `214b0e44` / 13,600（被外部覆盖后） | 自指不入表（复算 `sha256sum`） | 重放 §7 + 新增 §8 |

### 7.2 INDEX 新增 4 行

| 文件 | sha16 / B（**现盘实测**） | 状态 | 说明 |
|---|---|---|---|
| `GIT-UPLOAD.md` | `10451fe44f88495f` / 22,531 | current（上传/复现口径） | git-keeper 上传卫生报告：`main` `f285640→caa9760` 11 commit / 233 文件 / 2,988,727 B；31 个 `@sha16` 件 clone 31/31；配套 §0.5-4 发布口径 |
| `M6A-FIX-VERDICT-lead.md` | `0526c2316d779ee7` / 4,673 | **current（已签判决）** | I2 共享 cell 移动 = **通过**（fail-closed 守卫）；I1/I3/I4 **未接上**；C4 自我更正留痕 |
| `INSPECTOR-M6B-REVIEW.md` | `e9011e9d45ea6c6e` / 16,515 | report | M6b 预登记复核：B1 未接上（产品主路径；机制/工具臂可达）/ B2a **可达未修**（红证 §4.5）/ B2b 未接上 / B3 未接上不排期 |
| `M6B-PREREG-draft.md` | `23f2c4afe78c6a8a` / 18,787（v3，105 行） | **current（预登记 v3）**；v2 `6b46fb01` superseded | m6b-analyst 草案：v1 `fe4a40ab` 作废 → v2 `6b46fb01` 作废 → **v3 现盘** |

---

## 8 第三轮：4 处 sha 校正 + 计数定稿（2026-10-25 23:50）

### 8.1 逐行 sha 校正（**全部现盘重算，旧值作废**）

| 行 | 表中旧值（作废） | 现盘实测 | 原因 |
|---|---|---|---|
| `ANCHORS-CURRENT.md` | `d393d290680fc27a` | **`0d36bbe845080b47`** / 17,660 B | 本轮头部 +2 行（§7.1） |
| `INSPECTOR-M6A-FIX.md` | `6aca6e62103a9788` | **`ab2f7ca6d1bad3bb`** / 10,421 B（原 9,214） | inspector 又更新一版（结论文本变化）；**旧值 `6aca6e62` 作废** |
| `INSPECTOR-M6B-REVIEW.md` | `ac3cf6ca54c94a45`（**我上一轮写的值**） | **`e9011e9d45ea6c6e`** / 16,515 B（原 15,894） | inspector 更新两版；**`ac3cf6ca` 作废**（lead 要求记一笔） |
| `M6B-PREREG-draft.md` | `6b46fb012ba389f1`（v2） | **`23f2c4afe78c6a8a`** / 18,787 B / **105 行，头部写 `v3`** | v3 已落盘；v2 `6b46fb01` 转 superseded（`superseded-pending` 已删） |

**校验**：脚本逐行比对全表 46 行「表内 sha16 vs 磁盘实算」⇒ **mismatch = 0**。

### 8.2 一处未能复现的转述（留痕）

lead 给的 v3 = `68dbd3abb82f4117` / 20,738 B / 117 行 —— **磁盘上不存在该状态**：现盘 `M6B-PREREG-draft.md` = `23f2c4af` / 18,787 B / 105 行，头部明写 `v3`，`grep 68dbd3ab` 全仓 0 命中。**按光盘值写入 INDEX**，`68dbd3ab` 记为"转述值、未能在磁盘复现"（可能是出件前中间态或他机副本）。**若 analyst 另有 v4/修订版落盘，请给文件名，我按现场值再校一次。**

### 8.3 定稿计数（脚本 `Counter` 复算，46 行）

`46 = current 21（含 `ANCHORS-CURRENT` 特殊项 1）/ report 20 / archived 3 / superseded 2 / void 0`
（lead 裁定：**按 46 行，`GIT-UPLOAD.md` 入表、不拆脚注**；无新增文件 ⇒ 仍 46，不因 sha 校正而变。）

### 8.4 四态

| 任务 | 判 | 证据 |
|---|---|---|
| v3 状态改为 `current（预登记 v3）`、删 `superseded-pending` | **通过** | INDEX 该行；`23f2c4af` 现盘复核 |
| `INSPECTOR-M6B-REVIEW` sha 重算 | **通过（与转述不符，按现场写）** | 现盘 `e9011e9d45ea6c6e` / 16,515 B；`ac3cf6ca` 记作废 |
| 顺带全表 46 行 sha 复验 | **通过** | mismatch = 0；另校正 `INSPECTOR-M6A-FIX` 与 `ANCHORS-CURRENT` 两行 |
| 计数 | **通过** | 46 = 21/20/3/2（脚本） |
| `68dbd3ab` / 20,738 B / 117 行 | **未接上** | 磁盘无此状态，已留痕 |
| 不碰 PROGRESS/FEATURES/README、不新建第三份 | **未做（遵守）** | 三份 sha 与会话前一致；目录内仅 INDEX/DOCS-CONVERGENCE 两份新件 |

---

## 9 第四轮：inspector 两份终版落盘后的 sha 追平（2026-10-25 23:55）

> 触发：inspector 报 `INSPECTOR-M6B-REVIEW.md` 终版 v3、`INSPECTOR-M6A-FIX.md` 再更新；**已现场重算确认，与 inspector 给值逐字节一致**。

### 9.1 逐行 sha 追平（**旧值作废链留痕**）

| 行 | 表中旧值（作废） | 现盘实测 | 漂移链 |
|---|---|---|---|
| `INSPECTOR-M6B-REVIEW.md` | `e9011e9d45ea6c6e` / 16,515 B | **`28abf30c0b39ca41`** / 14,474 B | `ac3cf6ca`(15,894) → `e9011e9d`(16,515) → **`28abf30c`(14,474，终版 v3)** |
| `INSPECTOR-M6A-FIX.md` | `ab2f7ca6d1bad3bb` / 10,421 B | **`2d1b1b017ce1bebe`** / 10,477 B | `6aca6e62`(9,214) → `ab2f7ca6`(10,421) → **`2d1b1b01`(10,477，M6A 结论不变)** |

**摘要同步**：`INSPECTOR-M6B-REVIEW.md` 行改为 inspector 给的四态（B1 未接上（产品主路径；机制可达）/ B2a 可达·未修（chat+block 红证已复现）/ B2b 未接上（码读候选，P3 前不签死）/ B3 未接上（不排期）；执行状态：B2a 红证成功但未修，其余未做）。**状态仍 `report`**（不因终版改 status）。

### 9.2 定稿

| 项 | 值 |
|---|---|
| `docs/_work/INDEX.md` | **`12d8d41948e6dcbb`** / 17,870 B |
| 表行数 / 分布 | **46 = current 21（含 ANCHORS 特殊项 1）/ report 20 / archived 3 / superseded 2 / void 0** |
| 全表 sha 校验 | 46 行逐行「表内 vs 磁盘」⇒ **mismatch = 0** |
| `M6B-PREREG-draft.md` | **现盘 `23f2c4af` / 18,787 B（自称 v3）**；lead 转述的 `68dbd3ab` / 20,738 B 全仓无命中 ⇒ **引用一律以现盘为准**（inspector 同判） |

### 9.3 四态

| 任务 | 判 | 证据 |
|---|---|---|
| M6B-REVIEW 终版 sha 追平 + 摘要 | **通过** | 现盘 `28abf30c` / 14,474 B（与 inspector 给值一致）；状态仍 report |
| M6A-FIX sha 追平 | **通过** | 现盘 `2d1b1b01` / 10,477 B |
| 计数 | **通过（仍 46）** | 脚本 `Counter`；46 = 21/20/3/2/0 |
| 全表一致性 | **通过** | mismatch = 0 |
| `68dbd3ab` | **未接上** | 磁盘无此状态（与 inspector 结论一致） |

---

## 10 第五轮：M6B 复核精度修正后追平（2026-10-25 24:00）

| 行 | 旧值（作废） | 现盘实测 | 说明 |
|---|---|---|---|
| `INSPECTOR-M6B-REVIEW.md` | `28abf30c0b39ca41` / 14,474 B | **`ba4aef2be218f4a3`** / 14,724 B | inspector 精度修正：**`RecordingEngine` 存在但不在 `chat.py`** —— 实际在 `tools/chat_lease.py:186`（`__getattr__` 透传代理）；`chat.py` 的 B1 边界是 `CountingEngine.load_block`。**摘要文字不变**，只换 sha |

**定稿**：`docs/_work/INDEX.md` = **`b7dd942aa3b34df4`** / 17,870 B；46 行 = 21 current / 20 report / 3 archived / 2 superseded / 0 void；全表 46 行「表内 vs 磁盘」**mismatch = 0**。
**漂移链**：`ac3cf6ca` → `e9011e9d` → `28abf30c` → **`ba4aef2b`**（前三者作废）。

### 10.1 四态

| 任务 | 判 | 证据 |
|---|---|---|
| M6B-REVIEW sha 换到 `ba4aef2b` | **通过** | 现盘 `ba4aef2be218f4a3` / 14,724 B（与 inspector 给值一致） |
| 摘要文字 | **未做（inspector 说不用改）** | INDEX 该行仅 sha 变 |
| 计数 / 全表一致性 | **通过** | 46 行不变；mismatch = 0 |

---

## 11 第六轮：M6B 复核终版（chat 红证 artifact 同步后）追平（2026-10-25 24:05）

| 行 | 旧值（作废） | 现盘实测 | 说明 |
|---|---|---|---|
| `INSPECTOR-M6B-REVIEW.md` | `ba4aef2be218f4a3` / 14,724 B | **`c37efa04b58d7ae1`** / 16,236 B | 终版：同步新 chat 红证产物 `M6B-B2A-CHAT-RED` = **`8aca9868cdeae5e1` / 6,867 B**（旧 `dce1f205` / 5,356 是补注前版本，作废）与台账 `0b0a6ff2`；**摘要四态不变**（B1 未接上 / B2a 可达·未修（红证已复现）/ B2b 未接上 / B3 未接上；执行状态 B2a 红证成功但未修、其余未做），**状态仍 report** |
| `INSPECTOR-M6A-FIX.md` | — | `2d1b1b017ce1bebe` / 10,477 B（**未变**，inspector 确认） | 无需改 |

**产物 sha 提示**：INDEX **不列实验产物**（只列 `docs/_work/*.md`），故 `M6B-B2A-CHAT-RED` 的 `8aca9868` 只在此留痕、不进表；引用该产物时**用 `8aca9868`，`dce1f205` 作废**。

**定稿**：`docs/_work/INDEX.md` = **`d81b07194e4c5b30`** / 17,870 B；46 行 = 21 current / 20 report / 3 archived / 2 superseded / 0 void；全表 **mismatch = 0**。
**漂移链**：`ac3cf6ca` → `e9011e9d` → `28abf30c` → `ba4aef2b` → **`c37efa04`**（前四者作废）。

### 11.1 四态

| 任务 | 判 | 证据 |
|---|---|---|
| M6B-REVIEW sha 换到 `c37efa04` | **通过** | 现盘 `c37efa04b58d7ae1` / 16,236 B（与 inspector 给值一致） |
| M6A-FIX 复核 | **通过（无需改动）** | 现盘 `2d1b1b01` / 10,477 B |
| 计数 / 全表一致性 | **通过** | 46 行不变；mismatch = 0 |
| `M6B-B2A-CHAT-RED` 入表 | **未做（设计上不入表）** | INDEX 只列 md 文档；产物 sha 已在此留痕 |

---

## 12 第七轮：新建 `ARTIFACTS-KEY.md`（产物索引）+ INDEX 指针（2026-10-25 24:10）

> lead 裁定：**产物不进 46 行文档表**（会污染"文档索引"的计数），改为**单列产物索引**；范围**定死** = 只收"判决文件点名的坐标产物"，不收 `out/*.json` 全集。这是 lead 明确批准的**第三份** `docs/_work` 新文件（前两份 = `INDEX.md` / 本台账）。

### 12.1 old → new

| 文件 | old sha16 / B | new sha16 / B | 改动 |
|---|---|---|---|
| `docs/_work/ARTIFACTS-KEY.md` | —（新建） | **`e745ecee6f0ea01a`** / 13,006 | 新建：77 件产物 = **A 台账 19 ｜ B 判定/红证 57 ｜ C 会话态 1**；每行 `路径 \| sha16 \| 字节 \| 被哪份判决引用（首个 `文件:line`）` |
| `docs/_work/INDEX.md` | `d81b07194e4c5b30` / 17,870 | **`c187387ed238642a`** / 18,089 | §0 顶部加 1 行指针 → `ARTIFACTS-KEY.md`；**明确"不计入 46 行文档计数"**；表格本身未动（仍 46 行） |
| `docs/_work/DOCS-CONVERGENCE.md` | `d75e493715b7a532` / 23,632 | 自指不入表 | 追加本节 |

### 12.2 建表方法（可复现）

1. 扫 `docs/_work/*-lead.md` **17 份判决**全文，抽取所有 `*.json` 路径串；
2. 按「精确相对路径 → basename 落盘匹配」解析到磁盘（上限 3 命中/串）；
3. 每件实算 `sha256[:16]` 与字节；
4. 「被哪份判决引用」= 引用它的判决文件集合 + **首个出现位置 `文件:line`**；
5. 分组：**A** `LANDED-*` / `REGISTER.json` / `anchors_history.json`（判决引作"落地坐标"）｜**B** 判定与红证产物｜**C** 会话态快照。

**不做的事（避免伪证据）**：**不**自动比对"判决所引 sha vs 现值"并打 ⚠️ —— 判决行内常同时出现别件 sha（如 `M6B-PREREG-ACCEPT` 行同引 `23f2c4af`），naive 比对会产生**假告警**。本表只给现值 + 引用位置；"签署坐标 ≠ 现值"按 ANCHORS 的 R→A 降级处理，**不以本表覆盖判决读数**（该纪律已写进表头）。

### 12.3 两条终值同步

| 件 | 值 | 依据 |
|---|---|---|
| `kvmem/m2_visibility/m6b/LANDED-m6b-b2a.json` | **`00e26b42823747ee`** / 8,143 B | lead 给的终值（executor 修指针 + 补 `corrections[]` 后）；旧 `0b0a6ff2` 作废 —— **与现场实算一致** |
| `kvmem/m2_visibility/m6b/out/M6B-B2A-CHAT-RED.json` | **`8aca9868cdeae5e1`** / 6,867 B | inspector 给的终值；旧 `dce1f205`（5,356）作废 —— **与现场实算一致** |
| `docs/_work/INSPECTOR-M6B-REVIEW.md` | `c37efa04b58d7ae1` / 16,236 B | 上轮已换（✓ 未再变） |

### 12.4 四态

| 任务 | 判 | 证据 |
|---|---|---|
| 新建 `ARTIFACTS-KEY.md` | **通过** | `e745ecee` / 13,006 B；77 件；表头写死范围/口径/不计入计数 |
| 范围不扩大 | **通过** | 只剩"判决点名"这一条准入；未收未引用产物；维护约定写明"入表须有判决点名" |
| INDEX 指针行 | **通过** | `c187387e` / 18,089 B；`grep "ARTIFACTS-KEY"` = 1 命中（指针）+ 本台账；**46 行文档表未动** |
| 两条终值同步 | **通过** | 12.3；均现场实算核过 |
| 产物 sha 与判决 sha 的自动比对 | **未做（决定不做）** | 会产生假告警（12.2 末段），改由 ANCHORS 四态承担 |
| 待追加 | **未接上** | `M6B-B2B-*`（P3 出件后 lead 给 sha，我追加行） |

---

## 13 第八轮：M6b 收口批（INDEX +2 行 / ARTIFACTS-KEY +4 行 / PROGRESS §13.12）（2026-10-25 24:20）

### 13.1 old → new

| 文件 | old sha16 / B | new sha16 / B | 改动 |
|---|---|---|---|
| `docs/_work/INDEX.md` | `c187387ed238642a` / 18,089 | **`20cc7cf29d05f061`** / 18,663 | 补 2 行：`M6B-PREREG-ACCEPT-lead.md`（current 已签受理+判决）、`ARTIFACTS-KEY.md`（current，标"不计入文档计数"）；另把 `INSPECTOR-M6B-REVIEW.md` 行 sha 追到现盘 `290b9c79` |
| `docs/_work/ARTIFACTS-KEY.md` | `e745ecee6f0ea01a` / 13,006 | **`a3ddd0c581edda91`** / 13,836 | B 组 +4 行（B2b/P3 批）+ 变更记录 1 行；统计行脚本重算 81 件 = A 20 / B 60 / C 1 |
| `PROGRESS-AND-ROADMAP.md` | `6de6b5dd946b1df2` / 217,951（我上一版） | **`0084e5f6a47f6f60`** / 219,498 | 末尾追加 §13.12（13 行）；**另含一次事故修复，见 13.3** |

### 13.2 计数（脚本复算）

`INDEX.md` 表 = **48 行 = current 23 / report 20 / archived 3 / superseded 2 / void 0**。
其中 `ARTIFACTS-KEY.md` 一行按 lead 口径标注"**不计入文档计数**" ⇒ **纯文档计数 = 47**，表行 = 48。两个数都写在这里，避免再出现转述计数漂移。

### 13.3 事故：`PROGRESS-AND-ROADMAP.md` 在 23:56 被外部写成"自身两份"

- **现象**：修改前该文件 = 437,449 B / **5,060 行**，含 **两份逐字节完全相同**的全文档：copy1 = `:1-2524`、copy2 = `:2525-5048`，两者 `sha256` 均 `753e9159fc4451ef`，`# llama-mem 项目进度与未来开发` 出现 **2 次**（`:1`、`:2525`），`§0.1` 出现 2 次（`:58`、`:2582`），`## 附录：本文完结状态` 2 次（`:2518`、`:5042`）；my §13.12 被追加在末尾（`:5052`）。
- **判定**：**非有意内容**（逐字节重复、无任何新段），属拼接事故；留在库里会破坏"本文唯一长篇进度文档"的自我声明，并使全文行号引用整体失真。
- **修复**：保留 copy1 + 末尾 §13.12，删除 copy2 ⇒ **`0084e5f6a47f6f60` / 219,498 B / 2,537 行**；校验 `# llama-mem`=1、`§0.1`=1、`附录：本文完结状态`=1、`§13.12`=1。
- **可回滚**：双份状态 sha = `dead432eebdbe624`（437,449 B）；需要回滚请说，我可原样还原（内容未破坏，仅拼接重复）。
- **mtime**：`23:56:41` —— 与上一轮 `docs/_work` 多文件 `23:39` 覆盖同属**外部写入**，非本 agent 动作（我只做过 23:45–24:10 的追加与换 sha）。

### 13.4 §13.12 编号说明

lead 派单写 `## §13.7 …`，但 **§13.7 已存在**（`:1859` ≡ 修复后 `### 13.7 训练路线（ICAE + LoRA…）`）⇒ 顺延为 **`### 13.12 2026-10-25 引擎风险收口（M6a / M6b）`**，并在节首写明原因。内容按 lead 给的五条逐字落：M6a 四态、M6b 四态、坐标 5 个 sha16、**权威口径句逐字**、GitHub 发布/count 行。

### 13.5 ARTIFACTS-KEY 新增 4 行（现盘实算）

| 件 | sha16 / B | 与 lead 给值 |
|---|---|---|
| `kvmem/m2_visibility/m6b/out/M6B-B2B-P3.json` | `bd8e36d8c5223b07` / 8,641 | 一致 ✓ |
| `kvmem/m2_visibility/m6b/LANDED-m6b-b2b.json` | `074ded0b7029af21` / 5,549 | 一致 ✓（lead 提示可能再变） |
| `kvmem/m2_visibility/m6b/_run_m6b_b2b.py` | `16a555835c7516a9` / 14,374 | 一致 ✓ |
| `docs/_work/INSPECTOR-M6B-REVIEW.md` | **`290b9c792ebd4c9c`** / 19,917 | **不符**：lead 给 `b258f2b87d84100e` / 19,774 ⇒ 按现盘写，`b258f2b8` 记作"未能在磁盘复现（可能在他机/中间态）" |

### 13.6 四态

| 任务 | 判 | 证据 |
|---|---|---|
| INDEX 补 2 行 + 计数脚本重算 | **通过** | 48 行 = 23/20/3/2（脚本 `Counter`）；纯文档 47 |
| ARTIFACTS-KEY +4 行（含变更记录） | **通过** | 81 件 = A 20 / B 60 / C 1；统计行脚本重算 |
| PROGRESS 追加 §13.12 | **通过（编号顺延为 13.12）** | `:2525` 起；权威口径句逐字；未改既有内容 |
| PROGRESS 自身重复事故 | **通过（已修 + 留回滚点）** | 13.3；`753e9159` ×2 → `0084e5f6` |
| `INSPECTOR-M6B-REVIEW` 按 lead 值写 | **未做（按现盘值写）** | 13.5；`b258f2b8` vs 现盘 `290b9c79`，按纪律取现盘并留痕 |
| `LANDED-m6b-b2b` 后续再变 | **未接上（等 lead 喊）** | 现盘 `074ded0b` 已写入 |

### 13.7 收尾追平（写交付前最后一次现场校准，24:25）

`INSPECTOR-M6B-REVIEW.md` 在**本轮 10 分钟内被观测到 4 个不同状态**（inspector 侧正在终版收尾）：
lead 给 `b258f2b8` / 19,774 → 我读到 `290b9c79` / 19,917 → `463037ee` / 19,880 → ****现盘 `0a97ec2e33b4608b` / 20,123 B**。
⇒ INDEX 与 ARTIFACTS-KEY **均按最后一次现盘 `0a97ec2e` 写入**；`b258f2b8` / `290b9c79` / `463037ee` 全部作废。
**若 inspector 再落新版，只需给我"`文件名 + sha16 + 字节`"，我换该两行（INDEX 表 + ARTIFACTS-KEY B 组）。**

同批顺带校准：`GIT-UPLOAD.md` 被 git-keeper 更新 ⇒ `10451fe4` / 22,531 → **`d7aa2c66a532fb96` / 29,573 B**（INDEX 该行已换）。

**交付定稿 sha（24:25 现场）**：

| 文件 | sha16 / B |
|---|---|
| `docs/_work/INDEX.md` | **`f4903b84c200c8ae`** / 18,663（48 行 = 23 current / 20 report / 3 archived / 2 superseded；纯文档 47） |
| `docs/_work/ARTIFACTS-KEY.md` | **`5b25d51ff63386de`** / 13,836（81 件 = A 20 / B 60 / C 1） |
| `PROGRESS-AND-ROADMAP.md` | **`0084e5f6a47f6f60`** / 219,498 / 2,537 行（单份 + §13.12） |
| `docs/_work/DOCS-CONVERGENCE.md` | 自指不入表（本节末由现场复算给值） |

**校验**：INDEX 表 48 行逐行「表内 sha vs 磁盘」⇒ **mismatch = 0**（含刚换的 3 行）。

---

## 14 第九轮（终版换行批，2026-10-25 24:35）

### 14.1 old → new

| 文件 | old sha16 / B | new sha16 / B | 改动 |
|---|---|---|---|
| `docs/_work/INSPECTOR-M6B-REVIEW.md` | `0a97ec2e33b4608b` / 20,123 | **`e7cb51a82aa2c22d`** / 21,436 | 终版（含 P4 复核 + B2b 拆行 + chat/block 可达性差异）；`c37efa04`/`b258f2b8`/`290b9c79`/`463037ee`/`0a97ec2e` **全作废** |
| `docs/_work/M6B-PREREG-ACCEPT-lead.md` | `76edd1ee5c738114` / 5,223 | **`a85dcb9ea9cf9ae0`** / 7,101 | 终版：B2b **拆两行** + 终版签署段 + 新坐标 |
| `kvmem/m2_visibility/m6b/LANDED-m6b-b2b.json` | `074ded0b7029af21` / 5,549 | **`3b1e4f016afd5016`** / 7,113 | executor 加 `B2b_overall` / `B2b_tail` 字段（本轮被观测到 3 个状态：`074ded0b`/5,549 → `e6466c4b`/6,262 → **`3b1e4f01`/7,113**，前两者作废） |
| `docs/_work/INDEX.md` | `f4903b84c200c8ae` / 18,663 | **`567ddf7f9ec558ff`** / 18,864 | 两行换 sha + B2b 拆行摘要（B2b-prefix 未接上 / B2b-tail 未通过 / **B2b 合计 未通过**）；`ARTIFACTS-KEY` 行 sha 随动 |
| `docs/_work/ARTIFACTS-KEY.md` | `5b25d51ff63386de` / 13,836 | **`a6c1db9573abf345`** / 14,263 | B 组 2 行换 sha（M6B-REVIEW / LANDED-m6b-b2b）+ 变更记录 1 行 |
| `PROGRESS-AND-ROADMAP.md` | `0084e5f6a47f6f60` / 219,498 | **`6d43c924a367f0c3`** / 219,698 | §13.12 M6b 行**判决级更正**（见 14.2） |

### 14.2 §13.12 判决级更正（红线项）

改前（错）：`B2b 半文件被当合法块 = **未接上（实测支持；scope = prefix 截断）**`
改后（对）：`B2b 半文件被当合法块 = **合计未通过**：**B2b-prefix 未接上**（实测支持）、**B2b-tail 未通过**（tail-extra 变体未通过；P4：两臂 +1KB 尾均被接受，chat 路径可达、block 有 DB size 闸门）—— 见 `M6B-PREREG-ACCEPT-lead.md` `a85dcb9e``

理由：把"未通过"写成"未接上"属**判决降级**（四态不可互换），已按 lead 指令修正并留痕。

### 14.3 计数 / 校验（24:35 现场）

- `INDEX.md` 表 **48 行 = current 23 / report 20 / archived 3 / superseded 2 / void 0**（纯文档 47，含 `ARTIFACTS-KEY` 1 行"不计入文档计数"）。
- `ARTIFACTS-KEY.md` **81 件 = A 20 / B 60 / C 1**。
- INDEX 表 48 行逐行「表内 vs 磁盘」⇒ **mismatch = 0**；`LANDED-m6b-b2b` 观测后 1.5 s 内稳定。
- `PROGRESS` 完整性复核：`# llama-mem` 标题 1 次、`§0.1` 1 次、`附录：本文完结状态` 1 次、`§13.12` 1 次（上轮重复事故未复发）。

### 14.4 四态

| 任务 | 判 | 证据 |
|---|---|---|
| INSPECTOR-M6B-REVIEW 终版换行 | **通过** | 现盘 `e7cb51a8` / 21,436 |
| M6B-PREREG-ACCEPT 终版换行 + B2b 拆行摘要 | **通过** | 现盘 `a85dcb9e` / 7,101 |
| PROGRESS §13.12 判决级更正 | **通过** | 14.2；PROGRESS `6d43c924` |
| LANDED-m6b-b2b 换行 | **通过（但该件本轮仍在动）** | 现盘 `3b1e4f01` / 7,113；`e6466c4b` 亦作废 |
| lead 说"executor 30 秒内出新 sha，我会给你" | **未接上（现场已可读）** | 我用现盘 `3b1e4f01` 写入；若 lead 的值不同，再换一次 |

### 14.5 终版二次换行（lead 改自己判决书，24:45）

| 文件 | old sha16 / B | new sha16 / B | 原因 |
|---|---|---|---|
| `docs/_work/M6B-PREREG-ACCEPT-lead.md` | `a85dcb9ea9cf9ae0` / 7,101 | **`99a6ae7d7f2819d2`** / 8,274 | B2b-tail 行补 **产品可达性**：**chat 路径可达**（`session_state.py:330 load_strict` 前无 size/checksum，`189==189` 能过）；**block 产品路径不可达**（`memory_source.py:389-391` 比**实际 `st_size`**，P4 的 +1KB = 5,225,412 ≠ 5,224,388 会被拒，P4 block accepted 只是**引擎直调**）；另加**自我更正 C6**（先前"闸门比 DB 记录、文件长度可绕过"是错的） |

**同步 3 处**：① INDEX 该行 sha（摘要文字不变，四态此前已写对）；② `PROGRESS §13.12` 内引用的 `M6B-PREREG-ACCEPT-lead.md` 坐标 `a85dcb9e` → **`99a6ae7d`**（避免死锚）；③ 本节。
**`LANDED-m6b-b2b.json` = `3b1e4f016afd5016` / 7,113** —— lead 复核确认"抓对了"，本轮末稳定。
**ARTIFACTS-KEY 的变更记录**里那行 `a85dcb9e`/7,101 属历史留痕（不改写），以本条 `99a6ae7d` 为准。
**校验**：INDEX 48 行 mismatch = 0；`PROGRESS §13.12` 内已无 `a85dcb9e` 死锚。
