# 合并台账 · D:\llama-mem 的 Markdown 语料盘点（只读产出）

**产出人**：检测员 inspector ｜ **产出时间**：2026-10-25 ｜ **性质**：只读盘点，未改动、未删除任何既有文档
**唯一被写的文件**：本文件（`D:\llama-mem\docs\_work\CONSOLIDATION-LEDGER.md`，目录由本次新建）
**用途**：lead 复核「哪些合并、哪些删除」的执行依据；本台账不执行任何动作。

---

## 0 口径与方法（先声明，便于复核）

### 0.1 统计口径

```
find D:/llama-mem -name "*.md" -type f | wc -l                     -> 343
find D:/llama-mem/llama.cpp ./llama.cpp-upstream -name "*.md" | wc -l -> 258（各 129，两树对称）
343 − 258 = 85 份项目自有 md（本台账逐条列出）
```

- **VENDORED（第三方两树）不逐条列**，只在 [附录 C](#附录-c-vendored-第三方语料仅计数) 计数 —— 按 lead 终裁：两树原样不动，`UNTOUCHED`。
- 分类与动作取值见 §0.2；**「内容去向」列是本轮复核核心**，凡标 `DELETE-AFTER-BACKUP` 的必须写清哪些事实被搬到新文档哪一节，写「无内容需保留」的必须说明为什么可整体丢弃。
- 语言按正文 CJK 字数占比实测判定：`中` > 0.35、`混` 0.08–0.35、`英` < 0.08（`纯英文但含中文引用` 归 `混`）。
- 字节数与 mtime 取自本机实测（`os.stat`），非文档自述。
- **没有读到的字段一律 `UNKNOWN`**，不推测。

### 0.2 取值定义

| 字段 | 取值 | 含义 |
|---|---|---|
| 分类 | `CURRENT` | 当前有效，内容仍被上游文档引用为权威 |
| | `HISTORY` | 已被取代，但含「当时怎么想/当时判了什么」的历史事实 |
| | `EVIDENCE` | 某次跑 / 某份判据 / 某次验收的当场凭据 |
| | `LEDGER` | 验收台账 / PREREG / 判据冻结文本 |
| | `LEGACY` | 前身项目（biomem）残留 |
| | `VENDORED` | 第三方 llama.cpp 文档（仅计数） |
| 动作 | `KEEP-AS-README` | 直接作为新 README 的基线改写 |
| | `MERGE-INTO-README` | 内容并入新 README，原件备份后删除 |
| | `MERGE-INTO-PROGRESS` | 内容并入新进度文档，原件备份后删除 |
| | `DELETE-AFTER-BACKUP` | **先复制到 `D:\llama-mem-backup-2026-10-25\.` 再物理删除**；该文件无独立内容需保留 |
| | `UNTOUCHED` | 不动（仅 vendored） |

> 按 lead 终裁：**不使用 `docs/archive/` 归档**，删除方式统一为「复制到 `.trash-<日期>\.` → 物理删除」。
> 本台账所有 `MERGE-INTO-*` 与 `DELETE-AFTER-BACKUP` 行都意味着「备份后从原位置删除」，区别只在**是否携带独有内容进新文档**。

### 0.3 新文档的章节编号约定（「内容去向」列引用的编号以此为准）

- `R §n` = 新 **README** 的第 n 节，目录见 [附录 A](#附录-a建议的-readme-章节目录)。
- `P §n` = 新 **进度文档**的第 n 节，目录见 [附录 B](#附录-b建议的进度文档章节目录--里程碑表草稿)。

---

## 1 计数总览

| 维度 | 计数 |
|---|---|
| Markdown 总数 | **343** |
| VENDORED（`llama.cpp/` 129 + `llama.cpp-upstream/` 129） | **258** |
| **项目自有（本台账逐条）** | **85** |
| 项目自有总字节 | **1,707,063** ≈ 1.63 MiB |

**按分类**

| 分类 | 数 |
|---|---|
| CURRENT | 24 |
| LEDGER | 27 |
| EVIDENCE | 18 |
| HISTORY | 13 |
| LEGACY | 3 |
| VENDORED | 258（仅计数） |

**按动作**

| 动作 | 数 |
|---|---|
| KEEP-AS-README | 1 |
| MERGE-INTO-README | 2 |
| MERGE-INTO-PROGRESS | 75 |
| DELETE-AFTER-BACKUP | 7 |
| UNTOUCHED | 258（仅 vendored 两树） |

**按语言**

| 语言 | 数 |
|---|---|
| 中 | 69 |
| 混 | 14 |
| 英 | 2 |

**按目录**

| 目录 | 数 |
|---|---|
| `kvmem/m2_visibility/`（含 mine/ 32 = lead 9 + inspector 23） | 54 |
| `kvmem/m2_7b/`（7B 冻结线） | 18 |
| `docs/`（含 legacy-2026-10-24/ 5 份） | 6 |
| 根目录 | 4 |
| `legacy/biomem-legacy-src/biomem/` | 3 |

---

## 2 逐条台账（85 行）

> 排序：根目录 → docs/ → kvmem/m2_visibility/ → kvmem/m2_7b/ → legacy/。
> 「内容去向」引用的节号见 §0.3；凡 `DELETE-AFTER-BACKUP` 行，去向列写明「无内容需保留」的具体理由。

| # | 路径 | 字节 | 语言 | 主题 | mtime | 分类 | 动作 | 内容去向（R=README / P=进度文档 第X节） | 理由 |
|---:|---|---:|---|---|---|---|---|---|---|
| 1 | `README.md` | 5327 | 中 | 项目总览：KV 张量做记忆的定位、核心机制、三层状态、E10、verify.sh、仓库结构 | 2026-10-25 10:15 | CURRENT | **KEEP-AS-README** | 本体：新 README 全程以它为基线改写（R §1–§11 全部段落来源） | 已是最新重写版（10-25 10:15）；定位句「引擎层真 / 读取半真 / 产品层空」与今天的 HANDOFF、FEATURES 一致。仅需修三处漂移（见 §4 漂移清单）。 |
| 2 | `HANDOFF.md` | 9598 | 中 | 交接：组队与纪律、锚表、下一步顺序、已确立事实、措辞口径、复算命令、未闭项 | 2026-10-25 10:16 | CURRENT | **MERGE-INTO-PROGRESS** | P §1（强度四档 R/C/A/S 与措辞口径）、§2（M3/M4A/M4B 结论与锚）、§5（M3 五行读法）、§6（M4-A/B 两个口径不许混写）、§8（锚表）、§12（未闭项 F-*）、§13（下一步 1–4）、§15（复算命令） | 唯一权威交接，但体裁是「给下一个会话的操作指令」；用户要看的是项目本身。全部事实进 P，章程层内容进 §11。 |
| 3 | `FEATURES.md` | 14042 | 中 | 功能台账 17 行：已实现 / 部分实现 / 未实现 / 可能需要，每格带锚与强度 | 2026-10-25 10:07 | CURRENT | **MERGE-INTO-PROGRESS** | P §2 里程碑表「状态」列（17 格逐格落位）、§12 未闭项（M4-C / M1.8 / M2 规划器 / D-E 探针）、§13 未来计划、§14（「可能需要 vs 欠账」的区分） | 逐格状态唯一维护点，按功能组织；需拆到 P 的里程碑/未闭项/未来三章。也是唯一写明「⚠ 锚不在仓库」的地方，该口径须留。 |
| 4 | `PROJECT-STATE.md` | 51555 | 中 | 引擎层权威判定总表 E1–E10 / S1–S3 / P1–P8 共 25 条 + §7 数据不确定性 + §8 失真清单 + §11 下一步 | 2026-10-24 22:49 | CURRENT | **MERGE-INTO-PROGRESS** | P §3（25 条判定全表，含 file:line 锚）、§4（E10=已定位·生成侧）、§7.5 显存外推、§8 召回断崖、§13（§11 下一步依赖顺序）、§14（§8 文档史与失真清单 8 条） | 引擎层唯一权威，FEATURES §5 明写「引擎层有冲突以它为准」。但 §1 仍写「M3/M4/M5 零代码」，已被 10-25 落地推翻 —— 必须整表搬运并就地更正，不能原样保留。 |
| 5 | `docs/README-PHASE1-ENGINE.md` | 14596 | 中 | 阶段文档（E10 之前）：目标、目录表、构建产物、性能基线 | 2026-10-24 21:26 | HISTORY | **MERGE-INTO-README** | R §2（「淘汰应用层拼字符串」的动机段原文）、R §7（仓库结构表的初始版本）、P §14 一行（自述「目录表/通过数/耗时未随代码更新」） | 开篇自述数字未随代码更新，不可作断言依据；但「为什么改引擎而不是拼 prompt」的论证是全库最完整的，正是新 README §2 需要的素材。 |
| 6 | `docs/legacy-2026-10-24/README.md` | 20371 | 中 | 旧项目总览（M1.7 期）：三问题论证、KV 常驻主张、当时状态 | 2026-10-24 19:31 | HISTORY | **MERGE-INTO-README** | R §1（定位句）、§2（主流方案的三个绕不开的问题：prompt 变贵 / 记忆无结构优先级 / 不可审计）、§3；P §14 一行（当时判「放置层 M2 有 1 个阻塞缺陷」） | _ARCHIVE.md 已声明它被根 README + PROJECT-STATE 取代；但 §1 那段三条问题的论证比现 README 更充分，是 §2 的直接底稿。 |
| 7 | `docs/legacy-2026-10-24/README-HANDOFF.md` | 26096 | 中 | 第一轮引擎交接：改动位置与行号、坑清单、构建方法、跨进程持久化四组合实测 | 2026-10-24 13:32 | HISTORY | **MERGE-INTO-PROGRESS** | P §3（seq_cp 引用挂载 / seq_repos_local 局部重旋转 / Hadamard 三明治 的机制与 file:line）、§11（坑清单原文）、§13（M0/M1 已完成项）、§15（Vulkan 构建命令） | M0/M1 的机制说明在此，但每条判定已由 PROJECT-STATE §3 逐条收编并标强度；坑清单是纪律章的原始素材。 |
| 8 | `docs/legacy-2026-10-24/README-HANDOFF-2.md` | 39060 | 中 | 第二轮交接：context-shift 实测（n_keep）、召回率-距离断崖、训练成本账、文献地图、下一步三选一 | 2026-10-24 15:49 | HISTORY | **MERGE-INTO-PROGRESS** | P §4（召回率-距离全表 0-1k 56% / 1-2k 71% / 2-4k 72% / 4-8k 64% / 8-16k 0/9 / >16k 0/3）、§8（30464 B/token、8k 池 238 MiB、1k 记忆 29.8 MiB、100k≈3 GB、save 5–20 ms / load 20 ms）、§13（ICAE + LoRA r=16、24GB 卡 8–10 h、$3–5） | 全库数字密度最高的历史文档，PROJECT-STATE §7.5 至今仍引用它的召回表。按 lead 终裁「关键数字全部并入、不压缩成一行」，这张表和成本账必须整表迁入 P。 |
| 9 | `docs/legacy-2026-10-24/STATUS-REPORT.md` | 84321 | 中 | 2026-10-24 现状：引擎封版细节 + MD §4.3–4.6 的 M2/M3/M4/M5 **验收原文** + §9.1 缺口清单 | 2026-10-24 19:05 | HISTORY | **MERGE-INTO-PROGRESS** | P §2（M2/M3/M4/M5 四个里程碑的定义与验收原文，逐条照抄）、§5/§6/§7（各里程碑判据的原文出处）、§12（§9.1 两个阻塞缺口）、§14 一行 | 全项目**验收标准的唯一原文出处**（M3-PREREG/M4-CRITERIA/M5-CRITERIA 三份判据都写明「照抄本文 §4.x，不另立」）。删前必须把 §4.3–4.6 原文整段搬走，这是本轮最高风险的一份。 |
| 10 | `docs/legacy-2026-10-24/_ARCHIVE.md` | 2335 | 中 | 归档说明：为什么归档不删、引用规则（代码 > 运行产物 > 史料）、五份旧文档的取代关系表 | 2026-10-24 21:43 | HISTORY | **MERGE-INTO-PROGRESS** | P §14（取代关系表 5 行 + 引用规则「代码 > 运行产物 > 旧文档（仅史料）」一句） | 它本身没有技术结论，但它是「这些旧文档为什么不可引用」的唯一成文理由。取代关系表搬进 §14 后，本文件零残留。 |
| 11 | `kvmem/m2_visibility/INDEX.md` | 8552 | 混 | 54 份 md 的分类索引 + 四组同名文件警告 + 锚的两类（可复算 / 只在本地）+ 清理记录 | 2026-10-25 09:57 | CURRENT | **MERGE-INTO-PROGRESS** | P §15 附录（证据地图：四组同名不同作者文件、五份「唯一观测」干扰项）、§11（「同名+不同目录不是同一文件」实例）、§3（锚的两类划分） | 唯一解释「哪份是权威、哪份是重名」的索引，直接决定后续合并会不会把两份同名文件当成一份。**但它 §3.3 引的 SRC-CRITERIA sha(d97c663a / 1105 行) 已过期**（现值 82bd0f09 / 1122 行），迁移时必须就地更正。 |
| 12 | `kvmem/m2_visibility/ISOLATION-REPORT.md` | 19043 | 中 | M2 变量隔离过程报告：E10 失败点切到掩码层之外（已定稿·可引用，冻结哈希 cb11df4453756882） | 2026-10-24 21:03 | CURRENT | **MERGE-INTO-PROGRESS** | P §4（§2 遍历表 A/home 0/5·A/project 5/5·A/habit 0/5·A/car 5/5·B 15/15·C 5/20；§3 七条阵亡清单；§7 掩码四格表落位「②己」）、R §5 | README 与 PROJECT-STATE 都引它的冻结哈希，是 E10「已定位·生成侧」这一结论的原始凭据。自述「已定稿·可引用」，但引用须连 §1 四行冻结哈希一起搬。 |
| 13 | `kvmem/m2_visibility/E10-NEXT.md` | 25798 | 中 | E10 第一轮取证设计：三条候选解释各自的可判死实验与排序（sha16 eecd990f1a3897c3） | 2026-10-24 22:06 | HISTORY | **MERGE-INTO-PROGRESS** | P §4（三条候选解释与排序、成本口径「一次完整 run 中位 6.97 s，n=16」、两代 schema 不可混用的警告）、§13（E10 收口前置设计） | 已被 E10-NEXT2 修订取代（NEXT2 首行就写明上游是本文件），但「哪三条假设、按什么排序、哪条被判死」只有这里有完整论证。 |
| 14 | `kvmem/m2_visibility/E10-NEXT2.md` | 249626 | 中 | E10 第二轮设计修订版：撤空对照、距离轴立为第一优先、iso_dup_p3 判决实验、全库矩阵推翻「habit 恒败」 | 2026-10-25 00:03 | HISTORY | **MERGE-INTO-PROGRESS** | P §4（判决实验 iso_dup_p3：同 69 cells 同四块，唯一变量=源块距离 61→119；布局公式 lo = 4096 − (slot−1)×spacing − n）、§9（7B 几何公式来源） | 3195 行 7B 期设计稿，README 明写「不要当入门材料」。但两条设计结论（距离轴优先、零新块文件的判决实验）是全项目最省算力的实验设计，必须留。 |
| 15 | `kvmem/m2_visibility/NIGHT-REPORT.md` | 9292 | 中 | 夜间工作台一页纸：5 条已确凿（含「同几何只移除 project 一段即由败翻过」）+ 无证据单列 | 2026-10-25 00:05 | HISTORY | **MERGE-INTO-PROGRESS** | P §2（2026-10-24 夜那一格：cells 69→51 结局翻过，各 2 次跑、三条护栏全过）、§11（「只写有证据的、没证据的分开列」的写法实例） | 过程记录，宏观结论已被 M2-ACCEPT / STATUS 覆盖；但「一对观测即翻盘」这组是 E10 论证链的起点，要留结论与护栏条件。 |
| 16 | `kvmem/m2_visibility/PLAN-E10-FIX.md` | 15062 | 中 | 方案（非实验）：从「继续测布局」转为「改引擎」——装注意力仪表 / 改路由 / 必要时整体编码 | 2026-10-24 23:17 | CURRENT | **MERGE-INTO-PROGRESS** | P §13（E10 收口三选项的原始论证与选择条件）、R §5 一句（当前阻塞的下一步不是再测一条布局） | 全库唯一成体系的 E10 后续路线，立项依据是用户 10-24 的明确指示。属未来开发，不是历史 —— 这是它没被归档的原因。 |
| 17 | `kvmem/m2_visibility/7B-MOVED.md` | 337 | 中 | 一句话：7B 产物已迁至 kvmem/m2_7b/，本目录自此只含 14B 线 | 2026-10-25 01:38 | HISTORY | **DELETE-AFTER-BACKUP** | 无内容需保留：内容与 kvmem/m2_7b/MOVE-MAP.md（同一天 01:38 写，7 行 vs 38 行）第 0 节完全重复，且 MOVE-MAP 还多出旧→新路径映射表；该句将在 P §9 以 MOVE-MAP 为来源出现一次 | 纯指针文件，信息量被同日同目录的 MOVE-MAP.md 真包含；保留它只会造成两个来源说同一句话。 |
| 18 | `kvmem/m2_visibility/archive/ARCHIVE-NOTE.md` | 1836 | 中 | M2 归档包说明：含什么、为什么归档（二进制被覆盖的教训）、tarball sha 与校验方法 | 2026-10-25 01:35 | LEDGER | **MERGE-INTO-PROGRESS** | P §15 附录（归档包 M2-2026-10-25.tar.gz 与 tarball sha256 05e30c5b68d24488…）、§11（「二进制没归档就被覆盖、结论可重跑但原始产物不能」这条纪律的实例） | 归档包本身另存，但这个「为什么必须先留产物」的教训是全项目纪律的源头之一，一句话进 §11 + 一行进附录即可。 |
| 19 | `kvmem/m2_visibility/archive/HANDOFF-2026-10-24-superseded.md` | 14379 | 中 | 14B 之前的交接：2×2 四格表（近似重复只在满载时致命）、掩码偏置探针「差半个对数单位」 | 2026-10-25 00:10 | HISTORY | **MERGE-INTO-PROGRESS** | P §4（2×2 四格表原样 + 「近似重复只在满载时致命」这一当时结论）、§8（14B 四格是这张 2×2 的放大重跑，对应关系要写）、§5（掩码偏置探针结论） | 已被根 HANDOFF 取代（INDEX §3.1 明写在案），但 14B 四格 E/F/X1/B57 的构型就是从这张 2×2 一一映射来的，映射表只有这里有。 |
| 20 | `kvmem/m2_visibility/m2/README.md` | 7551 | 中 | M2 交付：三块以 KV cells 驻留、同会话依次答对三问 + 一条可复制命令 + 四跑证据 | 2026-10-25 01:31 | CURRENT | **MERGE-INTO-PROGRESS** | P §4（M2 几何：habit 12 @[4045,4057)、project 18 @[4057,4075)、home 21 @[4075,4096)、gap 0；问位 4096→4169→4242）、§15（复算命令） | M2 交付的唯一说明。这 51 格几何是所有后续实验（M3 51 cell、M4 91 cell、14B 四格）的坐标原点，数字不能丢。 |
| 21 | `kvmem/m2_visibility/m3/README.md` | 13173 | 中 | M3 交付：50 轮 attach/detach 结论 + 判据 5（pin）测出**反向结果** + 租约未接入 | 2026-10-25 02:33 | CURRENT | **MERGE-INTO-PROGRESS** | P §5（51 cell 恒、raw_pos_max 恒 4095、50/50 命中、三块 sha 一次未变、判据 5 反向：引擎不拒绝 reset 但句柄全丢 ⇒ pin 必须靠外层租约表） | m3/M3-ACCEPT 与它互补：验收定稿给结论，本文件给「判据 5 为什么是反向结果」的解释。反向结果比通过更有信息量，必须成段保留。 |
| 22 | `kvmem/m2_visibility/m3/M3-ACCEPT.md` | 14754 | 中 | M3 验收定稿（lead 署名）：通过 + 必须连读的五条 + §6 三次失败尝试 + §7 复算命令 | 2026-10-25 09:46 | LEDGER | **MERGE-INTO-PROGRESS** | P §5（结论与「五行一起读」的读法、attempt 1–3 全部保留为观测）、§15（check_m3_prereg_consistency.py 复算命令） | 两份同名不同作者的 M3-ACCEPT 之一（本份是 lead 验收定稿，198 行；inspector 版 91 行是验收稿）。两份都要读、不能当重复 —— 合成 P §5 一节后两原件都可备份删除。 |
| 23 | `kvmem/m2_visibility/m3/table_m3_rounds.md` | 13409 | 中 | M3 50 轮逐轮表：块占用 / raw_pos_max / 卸载后占用 / 答案前 40 字 / 命中 / 三块 sha16 / 耗时 | 2026-10-25 02:27 | EVIDENCE | **DELETE-AFTER-BACKUP** | 无内容需保留：50 行除 round 与 secs 外**逐字相同**（51 cell / 4095 / 卸载后 0 / 同一句答案 / 三个恒值 sha）；这些恒值与「首轮 34.9 s、第 2 轮起 11.6–11.7 s」已写入 P §5，逐轮原始数据在 run json（sha16 ef3d1e8859add5b0）里可复算 | 它是全库最容易误判的一份：看着像「50 轮独立证据」，实际是同一行复制 50 次（+2 个变化列）。表格本身不构成额外证据，若把 93 行搬进 P 只会稀释 §5。 |
| 24 | `kvmem/m2_visibility/m4/README.md` | 50434 | 中 | M4 交付主报告：9 轮对话→10 句全判定→6 keep→1 块 91 cells 独占 position 0→6 行 memory→新进程检索作答，9/9 验收 | 2026-10-25 04:24 | CURRENT | **MERGE-INTO-PROGRESS** | P §6（M4 全章主干：写入路径、91 cells/pos [0,90]、2026-10-28 相对时间锚定、去重、plate 独立桶与 a_hit 先查 plate） | M4 最完整的实现说明（652 行），P §6 以它为骨。取舍方向「宁多记不漏记」与 M5「漏判优先」故意相反且不许统一 —— 这条只有这里写清。 |
| 25 | `kvmem/m2_visibility/m4/STAGE3-ACCEPT.md` | 32825 | 混 | Stage 3 验收单（**executor 侧**交付）：R1–R9 逐项证据与复算命令 | 2026-10-25 05:49 | EVIDENCE | **DELETE-AFTER-BACKUP** | 结论进 P §10 以 inspector 定稿为准一行（15 通过 / R14·A1 / 0 finding）；本文件的 R1–R9 逐项证据属执行者自证，按纪律「自报不许升成重算」不单独搬运，其数值以 inspector 复算值为准 | 与 mine/inspector/STAGE3-ACCEPT.md 同名不同角色（INDEX §2 专门警告此类）。定稿已终审关闭，执行者交付版被覆盖 —— 但**备份必须保留**，因为它是「执行者报了什么」的唯一原件。 |
| 26 | `kvmem/m2_visibility/m5/README.md` | 7850 | 中 | M5 交付：14B 编造案例（苏A12345 vs 浙B-3F19K）→ 事后栅栏，四例回归 + 三条边界例 | 2026-10-25 02:08 | CURRENT | **MERGE-INTO-PROGRESS** | P §7（M5 边界：只管无中生有、不管张冠李戴；漏判优先于误判；不读 prompt、不读 .kvmem 二进制） | M5「管什么、不管什么」的唯一成体系说明。边界写错会让 M5 变成新的假接地源，这五条必须整段搬。 |
| 27 | `kvmem/m2_visibility/registry/README.md` | 32941 | 中 | 注册表不变量（Stage 1a）：kvmem/chat.db::memory_source 为正文唯一权威副本，缺口 #7 的真实形态是唯一性+全覆盖+可校验 | 2026-10-25 05:06 | CURRENT | **MERGE-INTO-PROGRESS** | P §10（缺口 #7 的真实形态、只动 tools/memory_source.py 三处+一个开关、不新增表不改消费方） | 产品层数据模型的唯一约束文档。README §3 只能给一句话，完整约束（source_hash 全 64 位、历史只追加）必须进 P §10。 |
| 28 | `kvmem/m2_visibility/chat_lease/README.md` | 21056 | 混 | chat.py 接租约（M3 最后未闭项）：四处 reset 站点语义各不相同 + 严禁 safe_reset_all | 2026-10-25 03:33 | CURRENT | **MERGE-INTO-PROGRESS** | P §5（四站表：放置/放置slots/卸下/装上 各自的改法与断言）、§11（陷阱：safe_reset_all 无条件跳过已注册块 seq ⇒ load_into 叠在旧 cell 上、不报错） | 把 M3 从「护栏就绪、覆盖率 0」变成「已接入」的唯一证据链，也是陷阱 5 的原文出处（含 m3_lease.py:107-119 行号）。 |
| 29 | `kvmem/m2_visibility/runs_m14b/REPORT-14B-READY-AND-DLL.md` | 12345 | 中 | 14B 就绪 + 重编 DLL 交付：模型 sha 校验、n_ctx 8192 显存实测、各组参数表 | 2026-10-25 00:32 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §8（装置实测：模型 8,988,110,240 B / sha256 0b319bd0…；n_ctx 8192 用到 9309/10224 MiB，余 915 MiB —— 「10 GB 装不下 14B」的预判被推翻）、§15（装置参数串） | 「10G 卡能不能跑 14B」的唯一实测出处，也是全项目所有结论的装置前提（RX 6750 GRE 10GB / Vulkan / Q4_K_M / q8_0 / -ngl 99）。 |
| 30 | `kvmem/m2_visibility/runs_m14b/REPORT-14B-BLOCKS.md` | 6620 | 中 | 14B 四块重建：断言式 size == 1188 + 104464×n 在四块上逐字节成立 | 2026-10-25 00:36 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §8（块格式两常量 1188 与 104464 = 每格 4+12 元数据 + 48 层×2×1088 B/行；与 KV pool 每 token 步长 104448 的区别 —— 上一单曾把二者写混） | 两个常量（1188 / 104464）是全项目块文件复算的地基，且「104448 与 104464 不同」是一个已被纠正过的坑，必须连纠正一起留。 |
| 31 | `kvmem/m2_visibility/runs_m14b/REPORT-14B-4CELL.md` | 9249 | 中 | 14B 四格×2 + run0：10 跑全过判据，但四格答案逐字节相同（E=F=X1=B57） | 2026-10-25 00:48 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §8（发现过程：24 token 预算下四格同为 c7d4e377fdc64950，只有 run0 不同为 31bff41f；执行者当时拒绝按预注册写「规模假设成立」）、§11（纪律实例：判据饱和时不许直接采信预注册的正向结论） | 结论已被 REPORT-14B-FINAL 改判覆盖，但「齐一是生成预算截断造成的假象」这个发现过程本身是最有价值的方法论案例，一句话不能表达。 |
| 32 | `kvmem/m2_visibility/runs_m14b/REPORT-14B-FINAL.md` | 8251 | 中 | 14B 主路径最终交付：规模/分配假设 = **未检验**（n_predict=64 下四格全分岔） | 2026-10-25 01:07 | CURRENT | **MERGE-INTO-PROGRESS** | P §8（终裁口径：不判成立、也不判否证；正文原始数字逐条列出） | 四格实验的最终口径，FEATURES 第 9 行与 HANDOFF §5.2 都依赖它。这一格若写错，整条 14B 结论会变形。 |
| 33 | `kvmem/m2_visibility/mine/lead/STATUS-2026-10-25.md` | 102925 | 中 | 状态报告 3.1–3.68 逐条裁决：M2/M3/M4/M5 落地过程、Stage 1a–3、缺口 #7 全过程、纪律七至十三、五个陷阱、未检验清单 | 2026-10-25 05:08 | CURRENT | **MERGE-INTO-PROGRESS** | **进度文档的主干来源**：P §2 §4 §5 §6 §7 §10 §11 §12 §14 的逐节自查取自此文件 §3.1–3.68；§11 纪律族；§14 五个陷阱原文；§12 未检验 5 条 | 102 KB / 1181 行，是全项目唯一按时间序记录每一次裁决的文件 —— 用户要的「完整里程碑细节」「800+ 行不砍数字」主要靠它。这是本轮最重要的一份搬运源，绝不能当「一个大文件」草率处理。 |
| 34 | `kvmem/m2_visibility/mine/lead/DISCIPLINES.md` | 25703 | 中 | 纪律一页：**41 条**（编号 1..41 连续、无缺号、无重号），每条一句可执行形式 + 一个今晚的真实实例 | 2026-10-25 09:53 | CURRENT | **MERGE-INTO-PROGRESS** | P §11 纪律章**全文**（41 条 + 实例）、以及「编号权威在本文件，其它文件的 §12.x 必须附映射表」这条元规则 | **编号权威在本文件**（其它文件的自有编号必须附映射表指向它，否则同号指不同事）。纪律是逐条可执行的规则，压缩会毁掉它们的可对号性，只能整章搬。 |
| 35 | `kvmem/m2_visibility/mine/lead/PREREG-14B-4CELL.md` | 27775 | 中 | 14B 四格预登记（跑之前写死）：换模型的理由、四格定义与 7B 2×2 的对应、§4.16–4.18 规模假设裁决 | 2026-10-25 01:05 | LEDGER | **MERGE-INTO-PROGRESS** | P §8（四格定义表 E/F/X1/B57 与 7B 逐格对应；每 token 708 B 头 + 7B 30480 B/格 vs 14B ≈102 KB/格的换算；§4.16「未检验」的裁决原文） | 预登记不可事后改，其结论段已进 §8；「换 14B ⇒ 所有 7B 块全部作废」这条推论是全项目最贵的一次判断，必须留。 |
| 36 | `kvmem/m2_visibility/mine/lead/PREREG-NEXT2-7B64.md` | 7919 | 中 | 7B 64-token 污染探针预登记：H-NEXT「改写内容渗入生成不是 14B 特有」+ 反假设 | 2026-10-25 01:18 | LEDGER | **MERGE-INTO-PROGRESS** | P §9（7B 64-token 交叉探针的假设与反假设；「污染这个量此前无法跨模型比较」的理由） | 该轮产物目录不在库（只有 BLIND-CHECK-7B64.md 在），本文件是这一轮设计意图的唯一记录。 |
| 37 | `kvmem/m2_visibility/mine/lead/PREREG-M3M4M5.md` | 4409 | 中 | M3/M4/M5 推进计划预登记：为何把顺序改成「先 M5 核心 → M3 → M4」（与 MD §4.6 相反） | 2026-10-25 01:48 | LEDGER | **MERGE-INTO-PROGRESS** | P §13（顺序偏离：MD 要求 M3→M4→M5，实际先做 M5 核心，理由=负对照已给出 M5 的现成失败案例，不必等 M4）、§12（两个前置缺口的当时状态） | 顺序偏离是重要决策史，且 FEATURES §3.1 仍在讲「M5 必须排在 M4 之后」—— 两处说法必须在 P 里并置解释，只有本文件给出当时的理由。 |
| 38 | `kvmem/m2_visibility/mine/lead/DELIVERY-14B.md` | 6647 | 中 | 14B 四格交付摘要（lead 署名）：事实层不复现、改写内容仍渗入生成 ⇒ 规模假设未检验 | 2026-10-25 01:08 | CURRENT | **MERGE-INTO-PROGRESS** | P §8 一句话结论（7B 的「69 格 + 近似改写 ⇒ 崩（填空模板）」在 14B 事实层不复现，但 14B 仍观测到改写内容渗入生成）、§15（装置参数串） | lead 署名的四格结论摘要，比 exec 报告更可引用；结论的收窄（不复现 ≠ 规模假设成立）是这一步最关键的分寸。 |
| 39 | `kvmem/m2_visibility/mine/lead/DELIVERY-M2.md` | 6062 | 中 | M2 交付验收记录：三问全中且多跑逐字节一致，但负对照显示无记忆也会自信编造 ⇒ 结论收窄 | 2026-10-25 01:35 | CURRENT | **MERGE-INTO-PROGRESS** | P §4（收窄后的结论：唯一站得住的是 Q1 那个不可猜住址串；六条局限含「只测 14B Q4_K_M + q8_0」「每跑前 free 9426 MiB」） | README 现状段「记忆读取能力是半真的」就建在这份的负对照上。负对照怎么把结论削掉一半，是全文最该保留的推理。 |
| 40 | `kvmem/m2_visibility/mine/lead/BRIEF-M3.md` | 3789 | 中 | M3 派单：pin/refcount、文件只读永不回写、cell 池余量监控三件事 + 已查清的接口行号 | 2026-10-25 01:50 | CURRENT | **MERGE-INTO-PROGRESS** | P §5（M3 验收三件事的定义；现成实现位置 tools/chat.py:208-212 → eng.share → llama_memory_seq_cp「refcount only, zero copy」；session_state.py detach-before-save 顺序） | 「M3 到底要验什么」的原始定义，含两个关键接口行号与 L7 陷阱 2（必须先摘引用再移动）。 |
| 41 | `kvmem/m2_visibility/mine/lead/BRIEF-M4.md` | 4019 | 中 | M4 派单：让「什么值得成块」从人写常量变自动沉淀 + 已查清接口（write_at / save） | 2026-10-25 02:00 | CURRENT | **MERGE-INTO-PROGRESS** | P §6（M4 目标一句话；kvslots.py:146 write_at(seq,text,pos,add_bos=True)、:222 save(seq,path) 接口行号） | M4 的定义与接口清单，判据 M4-CRITERIA.md 就是按它冻结的。 |
| 42 | `kvmem/m2_visibility/mine/inspector/M3-PREREG.md` | 18024 | 中 | M3 事先声明（259 行 / sha16 3e4f465b67eebd3c / 冻结）：未见任何数据时的初值与可判化改造 | 2026-10-25 06:08 | LEDGER | **MERGE-INTO-PROGRESS** | P §5（判据冻结声明与初值：51 cells / raw_pos_max 4095 / 132 键；「文档原判据照抄、只把它变可判」的做法）、§15（sha16 3e4f465b67eebd3c） | HANDOFF §5.4 明文列为「冻结、不许动」，且它的价值在「写于看数据之前」这个时刻（含脚本打印时间戳）。结论已进 §5，锚必须一起搬。 |
| 43 | `kvmem/m2_visibility/mine/inspector/M3-ACCEPT.md` | 7819 | 中 | M3 验收稿（inspector 侧，91 行）：9 项独立重算 + 三条移交要求 | 2026-10-25 02:31 | LEDGER | **MERGE-INTO-PROGRESS** | P §5（九项核对结果 + 三条移交要求，其中一条即 M4-C leases 必须真调用） | INDEX 特别警告：与 m3/M3-ACCEPT.md 同名不同作者，「两份都要读，不是重复」。合成 P §5 一节（lead 定稿给结论、本份给重算项）后两原件都可备份删除。 |
| 44 | `kvmem/m2_visibility/mine/inspector/M2-ACCEPT.md` | 23148 | 中 | M2 判据冻结 + 结果回填：三问命中判据、闸门九项、§6.6 Q4 负对照下调强度、（标题更正留痕） | 2026-10-25 09:42 | LEDGER | **MERGE-INTO-PROGRESS** | P §4（M2 判据原文 + 负对照如何把证据强度下调；标题从「结果待填」改为现状的过程留痕）、§11（「留痕更正」的写法实例） | M2 唯一带负对照的验收台账，README「半真」的证据链在此。它的「先冻结判据、再回填结果」也是全项目验收方法的样板。 |
| 45 | `kvmem/m2_visibility/mine/inspector/M4-ACCEPT.md` | 25038 | 中 | M4 验收：九项 acceptance 成立 + 三个未闭项（含 M4-C 未开始） | 2026-10-25 09:39 | LEDGER | **MERGE-INTO-PROGRESS** | P §6（九项逐项判据 + 三个未闭项）、§12（M4-C / n_predict 属性不暴露等未闭项） | M4 验收的唯一台账，FEATURES 第 7 行「已实现·未验收」的判据出处。9 项 vs 10 项的版本差异（现版 16 键）是已踩过的坑，要留。 |
| 46 | `kvmem/m2_visibility/mine/inspector/M5-ACCEPT.md` | 15160 | 中 | M5 验收：按冻结判据独立复核；判据自身缺陷只记进 M5-CRITERIA §9，不在验收文件里偷改 | 2026-10-25 03:50 | LEDGER | **MERGE-INTO-PROGRESS** | P §7（复核结果 + 判据修订记录的分家规则）、§11（纪律实例：验收文件不得私改判据） | M5 是否通过的凭据，同时示范「判据缺陷与验收结论必须分文件」这条做法。 |
| 47 | `kvmem/m2_visibility/mine/inspector/M4-CRITERIA.md` | 19932 | 中 | M4 判据「什么值得记」（冻结，实现之前）：K/D/U 判定、封闭词表、相对时间锚定、逐字接地 | 2026-10-25 03:53 | LEDGER | **MERGE-INTO-PROGRESS** | P §6（判据要点：keep/drop 规则、2026-10-28 相对时间锚定、封闭词表、宁多记不漏记） | 判据冻结文本，M4 实现与验收都回指它。方向「宁多记不漏记」与 M5 的「漏判优先」故意相反、不许统一 —— 出处在此。 |
| 48 | `kvmem/m2_visibility/mine/inspector/M5-CRITERIA.md` | 20887 | 中 | M5 判据「接地校验」（冻结，实现之前）：只管无中生有、漏判优先于误判、不读 prompt 与二进制 | 2026-10-25 04:01 | LEDGER | **MERGE-INTO-PROGRESS** | P §7（判据四条边界 + 四例回归 + 三条边界例；§9.1 数据后追加 R1–R5） | HANDOFF §5.4 列为「已冻结、不许动」。边界漏一条，M5 就会退化成常量规则（假接地）。 |
| 49 | `kvmem/m2_visibility/mine/inspector/SRC-CRITERIA.md` | 95653 | 中 | 源文本权威副本判据（缺口 #7，I1–I8 / R1–R15 / §12.x），1122 行，现 sha16 82bd0f0938ef9480 | 2026-10-25 09:45 | CURRENT | **MERGE-INTO-PROGRESS** | P §10（缺口 #7 判据体系与 §12 逐条）、§11（文件内 GEN:DISCIPLINE-MAP 生成块 = 向 DISCIPLINES.md 编号的映射表） | 唯一记明缺口 #7 判据全貌的文件；它内部那段自动生成的纪律映射表正是「编号权威在 DISCIPLINES.md」的落地证据。**注意：INDEX §3.3 引的 d97c663a / 1105 行已过期。** |
| 50 | `kvmem/m2_visibility/mine/inspector/_r2/SRC-CRITERIA.bak.md` | 94431 | 中 | 旧版 SRC-CRITERIA（1106 行 / sha16 d97c663aa42dc0bb），无纪律映射生成块 | 2026-10-25 09:42 | HISTORY | **DELETE-AFTER-BACKUP** | 无内容需保留：与现行 SRC-CRITERIA.md 逐行差异 220 行，差异全部集中在 GEN:DISCIPLINE-MAP 那段生成表的**有无与行序**，判据条文本身无独有条目；若日后要复算旧 sha 由备份提供 | 已实测两者 sha 不同（d97c663a vs 82bd0f09）故不是纯副本 —— 但差异是自动生成的映射表，不含任何判据事实。保留它唯一的副作用是让 INDEX 的过期 sha 显得「还在」。备份仍须做。 |
| 51 | `kvmem/m2_visibility/mine/inspector/_r2/src.gen.bak.md` | 95653 | 中 | 与 SRC-CRITERIA.md 逐字节相同的副本（1122 行 / sha16 82bd0f0938ef9480） | 2026-10-25 09:45 | EVIDENCE | **DELETE-AFTER-BACKUP** | 无内容需保留：实测 sha256 前 16 位与字节数（82bd0f0938ef9480 / 95653 B）与 mine/inspector/SRC-CRITERIA.md 完全一致，零信息增量 | 纯副本，已用 sha256 与字节数双重核对。若留着，会让「三份 SRC-CRITERIA」看起来像三个版本，实际是 2 个版本 + 1 个副本。 |
| 52 | `kvmem/m2_visibility/mine/inspector/STAGE1A-ACCEPT.md` | 4813 | 中 | Stage 1a 验收：幂等 put_source / 拒隐式修订（SourceConflict）/ 拒空文本 | 2026-10-25 04:11 | LEDGER | **MERGE-INTO-PROGRESS** | P §10（Stage 1a 通过，三条负向测试：id=1 幂等、同 name 不同 text ⇒ SourceConflict 带双 hash、空文本 ValueError） | 缺口 #7 四级验收的第一级；单阶段小验收，但三条负向测试是可复算的硬证据，须连返回值一起搬。 |
| 53 | `kvmem/m2_visibility/mine/inspector/STAGE1B-ACCEPT.md` | 6062 | 中 | Stage 1b 验收：层 1 结构化 + 摘录行 + M5 闸门（C4-f`k / R15-a`g 逐条裁决） | 2026-10-25 04:26 | LEDGER | **MERGE-INTO-PROGRESS** | P §10（Stage 1b 通过：10 行 text_kind 分布 human_memory×9 / conversation×1、contains_model_turns=1） | 同上，第二级。含「摘录是 7 条还是 4 条」这个歧义的裁决结果，该歧义曾在 lead 与 inspector 之间来回一轮。 |
| 54 | `kvmem/m2_visibility/mine/inspector/STAGE2-I8C-ACCEPT.md` | 7217 | 中 | Stage 2 + I8-C 验收：chat.py 改读注册表，三问 sha 与权威值逐字节相同 | 2026-10-25 04:43 | LEDGER | **MERGE-INTO-PROGRESS** | P §10（Stage 2 通过 + 三条修正；I8-C 关闭）、§15（三问权威 sha 852a5e5e… / dacdc1a8… / 46272e43…） | 第三级验收，且第一次把「三问 sha 逐字节相同」当作回归锚 —— 之后 Stage 3、接租约验收都复用它。 |
| 55 | `kvmem/m2_visibility/mine/inspector/STAGE3-ACCEPT-DRAFT.md` | 4138 | 中 | Stage 3 验收单**草案**：17 项状态机，全部「待验」 | 2026-10-25 04:57 | EVIDENCE | **DELETE-AFTER-BACKUP** | 无内容需保留：17 行状态列全为「待验」，无任何实测值；定稿 mine/inspector/STAGE3-ACCEPT.md 已逐行替换（15 通过 / R14·A1 / 0 finding） | 空表。INDEX §2 已把它标为「草案，被定稿取代」。它唯一的用处是证明「先建表后填」的做法存在过，该做法已在 P §11 纪律里留一句。 |
| 56 | `kvmem/m2_visibility/mine/inspector/STAGE3-ACCEPT.md` | 28045 | 中 | Stage 3 验收**定稿（终审关闭）**：15 通过 / 强度 R14·A1 / 0 未闭 finding / 1 遗留 A 档（R8b 附成本理由） | 2026-10-25 05:49 | CURRENT | **MERGE-INTO-PROGRESS** | P §10（Stage 3 终审表：①通过 15 ②强度 R14/A1 ③未闭 0 ④遗留 A 档 1 = R8b，理由「整跑 main() 会改写 PREREG 与两个库，成本判断不是能力边界」）、§11（「三个数不是手记的，由脚本从表里数出」这条做法） | 缺口 #7 收口的最终凭据，用户要看的「到底验了什么」在此。它的三个计数由脚本正则数出，这一做法本身值得留档。 |
| 57 | `kvmem/m2_visibility/mine/inspector/CHAT-LEASE-ACCEPT.md` | 7305 | 中 | chat.py 接租约验收：静态计数逐条 grep 复现 + 三问 sha 与 M2 权威值逐字节相同 | 2026-10-25 03:22 | LEDGER | **MERGE-INTO-PROGRESS** | P §5（接租约验收：eng.reset( = 0 / safe_reset_all = 0 / leases.reset( = 4 / eng.share( = 0 / eng.drop( = 0；三份 session 剔除 saved_at 后 sha fa94b1bc58c0e421… 全等） | M3 最后一个未闭项关闭的证据，FEATURES 第 6 行「部分实现」正是据此（静态计数到位、真实承重仍待 M4-C 自证）。 |
| 58 | `kvmem/m2_visibility/mine/inspector/BLIND-CHECK.md` | 18506 | 中 | 14B 四格盲写判定清单：在看到任何 14B 结果之前写死的四层判据 + 盲写边界声明 | 2026-10-25 00:50 | LEDGER | **MERGE-INTO-PROGRESS** | P §8（盲写四层判据：cell 扫描 / 掩码 / 答案解析 / 几何；「本单期间没打开 runs_m14b/ 与 m2_v1_14b/ 任何文件」的可审计声明）、§11（盲检方法） | 盲检是这套验收体系里最防自欺的一环；它的价值在「写于看数据之前」，所以清单内容与声明必须一起搬。 |
| 59 | `kvmem/m2_visibility/mine/inspector/BLIND-CHECK-7B64.md` | 16363 | 中 | 7B 64-token 盲写清单：「连 kvmem/m2_visibility/runs_7b64/ 都没 ls，连文件名都没看」 | 2026-10-25 01:17 | LEDGER | **MERGE-INTO-PROGRESS** | P §9（7B 64-token 探针的盲写声明与判据；「若事后发现我读过该目录，以本条为据作废整份清单」的作废条款） | 该轮产物目录不在库，本文件是这一轮唯一在库的记录；盲写声明强到自废条款，是方法论的极值样本。 |
| 60 | `kvmem/m2_visibility/mine/inspector/GATE-CHECK-14B.md` | 12495 | 中 | 闸门自检：机械执行 BLIND-CHECK §2.2 四层，对象是 10 个 run json；含盲态解除时刻 00:55:08 | 2026-10-25 00:55 | LEDGER | **MERGE-INTO-PROGRESS** | P §8（闸门四层自检结果、四格答案 sha c7d4e377… 三跑一致、盲态解除时刻 00:55:08 及「解除前读到的文件清单」） | 盲检的执行侧对照：什么时候解除盲态、之前读过什么，全部列名可审计。这条时间线是 14B 结论可信的前提。 |
| 61 | `kvmem/m2_visibility/mine/inspector/GATE-AB-PROBES.md` | 1994 | 混 | A/B 两处 fail-open 的运行时探针（R 级，4 条全部 ✅） | 2026-10-25 04:57 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §10（三处独立拒绝点的运行时证据：OriginError「registry db missing at … refusing to build an M5 source without the gate」/ AssertionError / SCHEMA ACCIDENT / 「layer-2 row exists in layer 1 but is not linked」） | 20 行的探针表，但它是「fail-open 已堵」的唯一运行时证据（对入口断言，不对文案断言）。四个报错串必须原文搬，不能改写成结论。 |
| 62 | `kvmem/m2_visibility/mine/inspector/E10-NEXT2-LEDGER.md` | 21878 | 中 | 14B 四格轮次台账：28 个 run json 亲读后的逐格判定；「未采信任何转述值」 | 2026-10-25 01:07 | LEDGER | **MERGE-INTO-PROGRESS** | P §8（四格逐格判定 + 证据基线清单：28 个 run json 明细、两个 GGUF 完整 sha256 自查）、§15（证据地图） | 14B 结论的唯一逐格台账。INDEX §2 特别警告它与根目录 E10-NEXT2.md **完全同名却完全不同**（219 KB 设计稿 vs 21 KB 台账）—— 这类同名是合并时最易出错的地方。 |
| 63 | `kvmem/m2_visibility/mine/inspector/SPEC-14B-4CELL.md` | 41607 | 混 | 14B 四格重跑规格书：E/F/X1/B57 逐项接口与几何，每处数值附出处（文件+行号 或 命令输出） | 2026-10-25 00:26 | CURRENT | **MERGE-INTO-PROGRESS** | P §8（四格实验设计、构型几何、接口清单；「没有出处的数值不存在」这条规格要求）、§15（接口与命令附录） | 14B 实验唯一成文规格，591 行里可复用的是几何与接口清单。它立的那条规矩「每一处数值都附出处」后来成了纪律的源头之一。 |
| 64 | `kvmem/m2_visibility/mine/inspector/RERUN-LOG.md` | 518 | 中 | 重跑登记（1 条）：R9 分叉输入独立重跑，before=unsupported → after=supported，diverged=True | 2026-10-25 05:37 | LEDGER | **MERGE-INTO-PROGRESS** | P §10（R9 重跑登记：内容哈希 76df01317bfaf3e7 前后相等、只写 tempfile 副本、副本已删）、§11（「重跑要登记谁/何时/为何/动了什么」的台账形式） | 8 行台账，但它证明 grade 是由真算产生（换个输入结论就翻转），不是写死的布尔。这类反证的价值与行数无关。 |
| 65 | `kvmem/m2_7b/MOVE-MAP.md` | 2275 | 混 | 7B/14B 目录分离：m2_visibility = 14B 线、m2_7b = 冻结的 7B 线，旧路径→新路径映射 | 2026-10-25 01:38 | CURRENT | **MERGE-INTO-PROGRESS** | P §9（7B 线全章开头：产物位置与旧→新路径映射表；「7B 的东西不放在 14B 的工作目录里」这条用户要求） | 唯一说明目录分离来由的映射表。7B 线后续所有文件都靠它定位，也解释了为什么 7B 与 14B 的块不能互用（708 vs 98304 元素/格）。 |
| 66 | `kvmem/m2_7b/evidence/t010/README.md` | 4113 | 混 | T-010 证据：五条 mask run 原件逐字节副本 + 原样命令行 | 2026-10-24 22:08 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §4（证据 1「记忆完整存在且可见」：coverage home 21/21·project 18/18·habit 12/12·project2 18/18；_assert_trace.py 输出 SUM=25 SUM2=25 blk=100 OK=4）、§15（复算命令行） | 「写进去了、没被 mask 掉」这条的唯一凭据目录，且 README 里存了可复现的完整命令行（因为 runs_* 被 .gitignore 排除，副本是唯一进库的方式）。 |
| 67 | `kvmem/m2_7b/evidence/t014/README.md` | 2646 | 混 | T-014 证据：三条 run 原件副本（iso_dup4 / 单块对照），6/6 逐字节校验通过 | 2026-10-24 22:23 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §4（单块可答：iso_home_only / iso_habit_only 均 TRUE、形态 plain；两条均为 C:inert，**不得与有控制臂的 run 混入同一计数**） | 单块能读是 E10 对照的基线格；「C:inert 不得混算」这条口径漏掉就会把 4 格表的分子算错。 |
| 68 | `kvmem/m2_7b/evidence/t016/README.md` | 2124 | 混 | T-016 证据：iso_dup_p3 判决实验三条 run 副本（6/6 校验） | 2026-10-24 22:23 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §4（判决实验 iso_dup_p3 的实际执行：同 69 cells 同四块，唯一变量=project 与 habit 槽位互换、源块距离 61→119、零新块文件） | E10-NEXT2 设计里的「本轮唯一判决实验」，这条是它的执行凭据。设计 + 执行必须成对出现，否则判决实验无从复核。 |
| 69 | `kvmem/m2_7b/evidence/t017/README.md` | 2937 | 混 | T-017 证据：iso_dup_p2 三条 run 副本 + PATTERNS（「调用发出去了」≠「文件已改」） | 2026-10-24 22:27 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §11（纪律实例：给 _driver2.py 加 iso_dup_p2 的那次编辑整段没执行，四条 run 全以 invalid choice 退出、一个 json 都没产出；是 usage: 那几行日志把原因摆出来的） | 实验结论无独有内容（被 t021 覆盖），但它记的这条 PATTERNS 是「跑批前先 import 确认键可见」的原始实例，属纪律素材。 |
| 70 | `kvmem/m2_7b/evidence/t018/README.md` | 1409 | 混 | T-018 证据：iso_topgap 一条 run 副本（2/2 校验） | 2026-10-24 22:25 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §4（判定 2「顶部空洞 ⇒ 记忆不生效」：head_gap>0 空答 7/7；零 trace 仅 1/7 可查 —— **不得写成 7/7**） | 这条判定唯一有 log 可查的样本就在这里（MASKDBG=4 全是驱动自打、引擎 0 行）。「7/7 空答」与「1/7 零 trace」的区分是措辞纪律的样板。 |
| 71 | `kvmem/m2_7b/evidence/t020/README.md` | 3013 | 混 | T-020 缺陷样本（刻意保留）：产物自述 spacing=64，实际几何 128 | 2026-10-24 22:30 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §14（失真清单：「产物写错自己的几何」—— _mask_run.py 把 spacing 硬编码成字面量；引用本目录的 layout.spacing 一律作废，以 coverage 反算 4096−3968=128 为准） | 它是「缺陷现场」而非实验结论，按纪律「阴性结果/缺陷也要留档」刻意保留。合并时最容易被误当无效数据删掉，实际它证明了产物自述值不可信。 |
| 72 | `kvmem/m2_7b/evidence/t021/README.md` | 3631 | 混 | T-021 证据：spacing 取真值后的两条交叉验证（self 与 coverage 反算一致）+ PATTERNS | 2026-10-24 22:44 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §4（spacing 的权威值来源）、§11（纪律实例：判「某说存活/死亡」必须把同表全部反例逐条代入，不能只拿最新一条 run 去撞 —— 本轮连续两次把「剩哪一个」读窄） | 它是 t020 缺陷的修复侧对照；PATTERNS 里那条「全表代入」是后来「全称否定须附核对时刻」纪律的前身。 |
| 73 | `kvmem/m2_7b/evidence/score_at/REPORT.md` | 8150 | 英 | score_at 探针交付报告：预注册正负对照**失败** ⇒ Δ/Δ'/Δ(A) 表未产出 | 2026-10-24 23:40 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §4（阴性结果留档：加 kvshim_score_at、绑定到 Python、用它判块是否被用 —— 正负对照失败，任务项 4 的表没产出）、§11（阴性结果也要留档 P9） | 全库唯一英文证词，记录一次「没做成」的探针。按纪律十一（阴性结果留档）它必须进文档，否则下一个人会重做同一个探针。 |
| 74 | `kvmem/m2_7b/runs_g18/PREREG.md` | 2665 | 中 | T-G18 单变量对照预登记：slot4 换成无关第三真事实（18 格同位同距） | 2026-10-24 23:45 | LEDGER | **MERGE-INTO-PROGRESS** | P §4（G18 设计：只改 slot4 内容，格数 18 / 位置 [3886,3904) / 间距 64 / home [4075,4096) / 提问点 4096 全部不变） | 排除「内容 vs 长度」的关键对照设计。预登记写死「只改一个变量」，是它可判的前提。 |
| 75 | `kvmem/m2_7b/runs_g18/REPORT.md` | 10679 | 混 | T-G18 产物报告：块、两次跑、几何、哈希、判读 | 2026-10-25 00:07 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §4（G18 结果与判读：blk_G_bos_c18 = 18 格 = 1 BOS + 17 内容 token、声明文本「我的雨伞放在书桌边…」、sha256 06fb59ac3416a1ae…、构建期断言 19/19 通过） | G18 的结论（换无关事实仍翻 ⇒ 不是「长度」而是「同位近似重复」）是 E10 解释链的一环，块 sha 与断言数都要留。 |
| 76 | `kvmem/m2_7b/runs_t031/NOTES.md` | 1082 | 中 | T-031 补充：F 臂四份产物的跨执行者交叉核对（答案 sha 全等、全部 ok=False） | 2026-10-25 00:02 | EVIDENCE | **MERGE-INTO-PROGRESS** | P §4（F 臂复现性：两个执行者四份 run 的 answer sha16 全为 11e20d78a1f18a98、全 ok=False、答案全文一致为「我住在\_\_\_\_\_\_。\n\n要填空的选项有：A. 中国；B.」） | 跨执行者、跨 run 目录仍得到同一坏答案 —— 这是全项目最硬的复现性证据之一，15 行里有 4 个 sha 与答案原文。 |
| 77 | `kvmem/m2_7b/runs_t032/PREREG.md` | 2943 | 中 | T-032 任务2 预登记：iso_fac_hp12 构型（home+project+habit+habit_paraphrase 12 格）几何 | 2026-10-24 23:41 | LEDGER | **MERGE-INTO-PROGRESS** | P §4（构型几何公式：start = 4096 − 3×64 − 12 = 3892；home [4075,4096)、project [4014,4032)、habit [3956,3968)、habit_paraphrase [3892,3904)、span_hi 4096 ⇒ head_gap 0） | 布局公式是全项目所有构型的算法源头（E10-NEXT2 §0 也引它），必须连公式带一组代入实例一起搬。 |
| 78 | `kvmem/m2_7b/runs_t032/PREREG_t032_task2.md` | 961 | 中 | T-032 任务2 臂定义：P_pp18_only = home + habit + pp18，去掉 project 18 格 | 2026-10-24 23:41 | LEDGER | **MERGE-INTO-PROGRESS** | P §4（P_pp18_only 对照臂：唯一变化 = project 的 18 格 [4014,4032) 整体缺席；判定分支「通过 ⇒ 需要 project 与它的改写同时在场」） | 15 行但含一个明确的可判分支（通过/失败各自意味着什么），这类「预登记判据」不能只留结论。 |
| 79 | `kvmem/m2_7b/runs_t032/PREREG_t032_task3.md` | 1631 | 中 | T-032 任务3 臂定义：H1（habit 原块 12 格）vs H2（habit_para12 受限同义改写 12 格含 BOS=11 内容） | 2026-10-24 23:43 | LEDGER | **MERGE-INTO-PROGRESS** | P §4（H1/H2 定义与「只比 H1 vs H2、不与 18 格臂比」的隔离要求；原文本「我的咖啡只喝美式，不加糖。」） | 唯一按「同格数、同位置、同族改写」隔离长度的对照臂，且预先声明了不许跨臂比较 —— 这条限制防止了后来最容易犯的混算错误。 |
| 80 | `kvmem/m2_7b/runs_t032/PREREG_t032_task4.md` | 1296 | 中 | T-032 任务4：造两个带 BOS 的块（filler_bos_c21 / G_bos_c18）+ 阴性对照 NEG_filler_bos21 | 2026-10-24 23:45 | LEDGER | **MERGE-INTO-PROGRESS** | P §4（阴性对照定义：filler_bos_c21 = BOS + 20 内容 token「小区门口的早餐店换了老板…」；G_bos_c18 = BOS + 17 内容 token；重造的是上一轮两块**无 BOS** 的块） | 阴性对照的块文本与格数是「答错是因为块本身无关」这一结论的前提，且它记录了「上一轮两块漏了 BOS」这个已修正的缺陷。 |
| 81 | `kvmem/m2_7b/runs_t032/mine/PREREG_task3.md` | 9120 | 中 | T-031 掩码偏置探针预登记：LLAMA_KV_MASK_BIAS="lo:hi:b" 的接口与不变式 | 2026-10-25 00:01 | LEDGER | **MERGE-INTO-PROGRESS** | P §4（探针接口与四条不变式：未设 env ⇒ 行为完全不变；只对位置在 [lo,hi] 且值恰为 mask_keep 的格加 b；被 mask_drop 的格永不改动；每次打印 [MASKBIAS] … n_cells_touched=…） | 它是「信息在场且可达、只差半个对数单位」这个结论的工具出处。探针的不变式写错，结论就是仪器伪影 —— 所以四条要原文搬。 |
| 82 | `kvmem/m2_7b/runs_t032/mine/EXECUTOR_HANDOFF.md` | 5025 | 英 | 执行者停机交接：未重编；锁测试因路径写错（FileNotFoundError）把自己答成「locked」 | 2026-10-24 23:54 | HISTORY | **MERGE-INTO-PROGRESS** | P §14（失真清单：一次「测试答错了问题」的现场 —— D:/llama-mem/build-vulkan/bin/kvshim_vk.dll 不存在，脚本把它当成被占用；净效果=没重编，恰好符合停机令）、§11（纪律实例） | 唯一英文跑批交接。价值在于它是一条「脚本给出正确结论但理由完全错」的实例，正对应纪律「绿在错的因」。 |
| 83 | `legacy/biomem-legacy-src/biomem/README.md` | 6979 | 中 | 前身项目 biomem：本地仿生记忆聊天智能体（7B 大脑 + SQLite 海马体 + 有限工作记忆 + 巩固/遗忘） | 2026-10-24 21:42 | LEGACY | **MERGE-INTO-PROGRESS** | P §14（一行：前身项目 biomem 走应用层记忆（SQLite + 多路轻量索引 + 遗忘曲线），16 GB 内存 / 10 GB 显存可跑；本项目是它「改引擎」的继任者） | 技术路线与本项目相反（应用层拼装 vs 引擎层 KV），但正是这个背景解释了为什么本项目要从引擎改起。只值一行，且这一行必须由本文件支撑。 |
| 84 | `legacy/biomem-legacy-src/biomem/docs/ARCHITECTURE.md` | 12363 | 中 | biomem 架构：感觉缓冲 / 工作 / 情景 / 语义 / 程序 / 索引 / 巩固 / 遗忘 八层 | 2026-10-24 21:42 | LEGACY | **DELETE-AFTER-BACKUP** | 无内容需保留：八层记忆模型是应用层设计，与 KV 张量路线没有接口；本项目仅借用了「巩固 / 遗忘」两个词，该事实已由 biomem/README.md 那一行覆盖 | 旧项目的内部架构图，对本项目无任何可执行信息；保留它会把「两个不同的记忆模型」并置，反而制造混淆。备份保留原件以备考。 |
| 85 | `legacy/biomem-legacy-src/biomem/docs/ROADMAP.md` | 4403 | 中 | biomem 实施路线与验收（阶段 0：Vulkan 构建 b11849、7B Q4、OpenAI 兼容服务、35–40 tok/s） | 2026-10-24 21:42 | LEGACY | **MERGE-INTO-PROGRESS** | P §14（一行，含硬件与基准：RX 6750 GRE 10GB（9426 MiB free）、llama.cpp Vulkan b11849、DeepSeek-R1-Distill-Qwen-7B-Q4_K_M、Qwen3-8B Q4 解码约 35–40 tok/s）、§2（M0 工具链/构建的完成依据） | 虽然属旧项目，但阶段 0 的构建与基准是本项目 M0 的实际完成凭据（README-HANDOFF 也说「作者已完成 M0（工具链/构建）」）—— 数字必须搬，文件本体可删。 |

---

## 3 写文档所需的事实素材（全部原文可追溯，带路径）

> 本节的每一条都标了出处文件；**没读到的写 UNKNOWN**。lead 可直接把本节当作两份新文档的素材库。

### 3.1 项目一句话定位

| 项 | 内容 | 出处 |
|---|---|---|
| 项目名 | **llama-mem**（工作树 `D:\llama-mem`，llama.cpp fork，分支 `persistent-memory`，基线 `8e5a58d`） | `README.md:1-5`、`docs/README-PHASE1-ENGINE.md` |
| 一句话 | **把长期记忆做进推理引擎的 KV 张量里，而不是拼进 prompt 字符串。** | `README.md:3` |
| 三层状态 | **引擎层是真的；记忆读取能力是半真的；产品层有骨架，仍无服务端。** | `README.md:7`（旧版第三层写作「产品层是空的」：`PROJECT-STATE.md:31`） |
| 关键差别 | 记忆不在 prompt 文本里，它在 KV cache 里；**删掉对话历史，记忆依然可被读出**。 | `README.md:11-17` |
| kvmem 是什么 | 实验产物树的根目录名（`kvmem/`）：放实验产物、夹具、预登记、验收、判据、台账；README 明写「**kvmem/ 下的 73 份 md 是证据，不是文档**」 | `README.md:88-91` |
| kvmem 的另一种含义 | `*.kvmem` = 记忆块二进制文件本体（被 `.gitignore` 排除，clone 后拿不到） | `README.md:96-101`、`kvmem/m2_visibility/INDEX.md` §4 |
| 核心机制 4 条 | ①记忆序列以 KV 张量常驻（`seq_cp` 引用计数挂载，不是文本）②位置被挤占时做局部重旋转（`seq_repos_local`：CPU 上 dequant → rope → requantize）③Hadamard 三明治（`H → rope → H`，注意 RoPE 与 H 不对易）④`kv_unified=true` 下共享单一 KV 池，各记忆块仅靠 position 区间区分 | `README.md:19-24` |
| 补丁规模 | 6 文件 / 实时 **600 insertions / 0 deletions**；归档版 500 | `README.md:30`、`README.md:74-77` |
| 前身 | **biomem**（应用层记忆：SQLite 海马体 + 多路索引 + 遗忘曲线，7B / 10GB 可跑）；本项目是它「改引擎」的继任者 | `legacy/biomem-legacy-src/biomem/README.md` |

### 3.2 当前阶段与最新进度

| 项 | 内容 | 出处 |
|---|---|---|
| 最新一天 | **2026-10-25**（milestone 与文档 mtime 均落在这一天） | 全库 mtime |
| 最新一句话 | **M3 已验收；M4 三件里 A 绿、B 已判出、C 未开；M5 有实现、两探针未办。** | `HANDOFF.md:8` |
| 当前最大未闭项 | **M4-C**：`leases` 真实接入 + 承重自证（判据是「删掉它必须有断言变红」，不是「加上调用」） | `HANDOFF.md:117`、`FEATURES.md:23` |
| 当前阻塞级缺陷 | **E10：4 段共享区间下的可见性 —— 已定位，未修复**。非存储缺陷、非可见性缺陷，失败发生在生成侧 | `README.md:34-50`、`PROJECT-STATE.md` §3.10(f) |
| 自检状态 | `bash verify.sh` 跑 9 项断言，**当前 8 绿 1 红**；红的是第 1 项（引擎工作区比归档多 100 行，全在 `src/llama-kv-cache.cpp`，归档 +391 / 实时 +491） | `README.md:58-77` |
| 下一步顺序 | 1. M4-C ②补 M5 (a)/(c) 两探针 ③三件绿后写 M4 验收定稿 ④M2 规划器 / M1.8 三处 judge 冲突 | `HANDOFF.md:113-120` |
| 措辞纪律 | 「不说 M2 全部通过 → 逐格写，见 FEATURES.md」「不说 T2 稳定 → 同输入重放 50 次逐字节恒等」「不说 think 出现 6 次 → 承载字段 8 / 不同答案串 2」 | `HANDOFF.md:186-200` |

### 3.3 已完成里程碑清单（编号 + 结论 + 日期 + 关键数字）

| 编号 | 日期 | 结论 | 关键数字 | 出处 |
|---|---|---|---|---|
| **M0** 工具链/构建 | ≤2026-10-24 | 完成（Vulkan 构建 + 7B Q4 模型 + OpenAI 兼容服务跑通） | `build-cpu/` 333 target、`build-vulkan/` 657 target；RX 6750 GRE 10GB（9426 MiB free）；Qwen3-8B Q4 解码约 35–40 tok/s | `docs/legacy-2026-10-24/README-HANDOFF.md` §0、`docs/README-PHASE1-ENGINE.md` 目录表、`legacy/biomem-legacy-src/biomem/docs/ROADMAP.md` |
| **M1** 机制验证 | 2026-10-24 | 跨进程持久化四组合实测通过；判断标准（prompt 里无该信息仍答对）达成过一次 | — | `docs/legacy-2026-10-24/README-HANDOFF.md` §0/§2.4 |
| **M1.7** 检索层 | 2026-10-24 | 达到 M1.7（文本检索链可用） | recall@1 0.762 / recall@3 0.952 / MRR 0.921（**但 PROJECT-STATE 判定：证明的是文本检索层，不是 KV 记忆**） | `docs/legacy-2026-10-24/README.md` §1、`PROJECT-STATE.md` §7 前注 |
| **M1.8** 三处 judge 冲突 | — | **未开始**（零补丁、零产物） | — | `FEATURES.md:19`、`FEATURES.md` §3 |
| **E10** 4 段可见性 | 2026-10-24（隔离报告定稿） | **已定位·生成侧，未修复**；引擎代码为此未改一行 | cell 层 home 21/21 覆盖无重叠；掩码层两臂各 100 条块行、`masked > 0` 的 **0 条**；遍历表 A/home **0/5**、A/project 5/5、A/habit **0/5**、A/car 5/5、B **15/15**、C **5/20**（C 恒 1/4，只有 habit 过） | `README.md:34-50`、`kvmem/m2_visibility/ISOLATION-REPORT.md` §2（冻结哈希 `cb11df4453756882`，267 行） |
| **T-010～T-023** E10 第四轮 | 2026-10-24 | 打死的不是假设，是一个判据 | `llama-kv-cache.cpp` `dbe52f9124f1ad29`（ins=500 del=0）、DLL `849e7281c74a5288`；7 条假设被逐一排除 | `PROJECT-STATE.md` §7.6、`kvmem/m2_7b/evidence/t0*/README.md` |
| **M2 可见性收口（M2.5）** | — | **未收口**（验收线：4 块布局 4/4 可读、n=5 稳定） | — | `PROJECT-STATE.md` §11 |
| **M2 落地**（14B 51 格） | 2026-10-25 | 三条 KV 驻留记忆同会话依次答出、多跑逐字节可复现；**但负对照显示无记忆也会自信编造 ⇒ 结论收窄到只剩一条不可猜住址串** | habit 12 @[4045,4057) / project 18 @[4057,4075) / home 21 @[4075,4096)，gap 0；问位 4096 → 4169 → 4242；三跑逐字节相同 | `kvmem/m2_visibility/m2/README.md`、`mine/lead/DELIVERY-M2.md`、`mine/inspector/M2-ACCEPT.md` |
| **M3** 块生命周期 | 2026-10-25 | **通过**（判据 1–4 有效应） | 50 轮全有效；块占用恒 **51 cell**、`raw_pos_max` 恒 **4095**、住址 **50/50** 命中且 50 轮逐字节相同、三块 sha 一次未变；逐轮 32 键中仅 `round`/`secs` 变（30 标量中 28 恒定）；四泄漏计数器全 0；判据 5（pin）测出**反向结果** | `kvmem/m2_visibility/m3/README.md`、`m3/M3-ACCEPT.md`、`mine/inspector/M3-PREREG.md`（`3e4f465b67eebd3c` / 259 行）、锚 `m3/run_m3_lifecycle_50_v4.json` = `ef3d1e8859add5b0` |
| **M3 接租约** | 2026-10-25 | 已接入（原状态「护栏就绪、覆盖率 0」→ 四站全部改完） | `eng.reset(` **0**、`safe_reset_all` **0**、`leases.reset(` **4**、`eng.share(` 0、`eng.drop(` 0 | `kvmem/m2_visibility/chat_lease/README.md`、`mine/inspector/CHAT-LEASE-ACCEPT.md` |
| **M4** 写入固化 | 2026-10-25 | 实现+**九项 acceptance 全真，但「未验收」状态**（验收定稿待 M4-C） | 9 轮真实对话 / 10 句全部有判定 / 6 条 keep → **1 个 KV 块 91 cells 独占 position 0** / 6 行 memory（含 `2026-10-28` 相对时间锚定）/ 7 行 `memory_source` | `kvmem/m2_visibility/m4/README.md`、`mine/inspector/M4-ACCEPT.md`、锚 `run_m4_verify_a4.json` = `59edbd82d4b9ae44`、块 `blk_conv_2026-10-25_01.kvmem` = `81127d24fd64b96b` / 9,507,412 B |
| **M4-A** `</think` 泄漏 | 2026-10-25 | **已绿**（口径：两个数都要报，禁止写单个数字） | 机械次数 **8**（承载字段）/ 语义次数 **2**（不同原始串） | `HANDOFF.md:105-107`、`FEATURES.md` §1.2 |
| **M4-B** 车牌句消融 | 2026-10-25 | **已判出（带一处必须一起引的混淆）**，verdict = `memory_carried_by_that_sentence_content_not_length` | 产品块 91 cells [4005,4096) → 浙B-3F19K；同路径重编 91 cells → 浙B-3F19K（块 sha 与产品块逐字节相同）；删掉那句 **79 cells** [4017,4096) → 苏A12345（编造）；等长对照 91 cells → 浙Q-00000 | `HANDOFF.md:109-116`、锚 `run_m4_ablate_plate_a7.json` = `77e11a04aacd24c5` |
| **M4-C** leases 真调用 | — | **未开始**（M4 最大的洞） | — | `HANDOFF.md:117`、`FEATURES.md` §3 |
| **M5** 接地与弃答 | 2026-10-25 | 校验器核心落地；产品可用 → **通过（P0 闭环，R14 裁决）** | 反例：问车牌 → 14B 答「苏A12345」，装置唯一真值是「浙B-3F19K」且不在挂载块内；边界「只管无中生有，不管张冠李戴；漏判优先于误判」 | `kvmem/m2_visibility/m5/README.md`、`mine/inspector/M5-CRITERIA.md`、`mine/inspector/M5-ACCEPT.md`、锚 `run_m5_grounded.json` = `007cb08b8f117ec5` |
| **14B 四格 E/F/X1/B57** | 2026-10-25 | 24 token 下「四格齐一」是**生成预算截断造成的假象**；`n_predict=64` 下四格全分岔 ⇒ **规模/分配假设 = 未检验**（不判成立，也不判否证） | 24 token 预算下 E=F=X1=B57 = `c7d4e377fdc64950`（同一 24 token 串），run0 = `31bff41f`；14B 每格 ≈ **102 KB**（708 B 头 + 48 层×8 kv head×128 维×2×q8_0）；7B+q8_0 实测 **30480 B/格** | `kvmem/m2_visibility/runs_m14b/REPORT-14B-FINAL.md`、`mine/lead/PREREG-14B-4CELL.md` §4.16、`mine/lead/DELIVERY-14B.md` |
| **7B 线** | 2026-10-25 冻结 | 冻结，产物全部迁至 `kvmem/m2_7b/`，**不再产出** | 换 14B ⇒ 所有 7B 的 `.kvmem` 块全部作废（模型专属） | `kvmem/m2_7b/MOVE-MAP.md`、`kvmem/m2_visibility/7B-MOVED.md`、`HANDOFF.md:130` |
| **缺口 #7 Stage 1a** | 2026-10-25 | **通过**（注册表不变量落地） | 幂等同 name 同 text ⇒ `id=1, created=False`；同 name 不同 text ⇒ `SourceConflict` 带双 hash；空文本 ⇒ `ValueError` | `kvmem/m2_visibility/registry/README.md`、`mine/inspector/STAGE1A-ACCEPT.md` |
| **Stage 1b** | 2026-10-25 | 通过（层 1 结构化 + 摘录行 + M5 闸门） | 10 行 `text_kind`：`human_memory` ×9 / `conversation` ×1 | `mine/inspector/STAGE1B-ACCEPT.md` |
| **Stage 2 + I8-C** | 2026-10-25 | 通过（chat.py 改读注册表）+ 三条修正；I8-C 关闭 | 三问 sha `852a5e5e6ab70eeb…` / `dacdc1a89ef08165…` / `46272e43287c5ff7…` 与权威值逐字节相同 | `mine/inspector/STAGE2-I8C-ACCEPT.md` |
| **Stage 3** | 2026-10-25 | **定稿·终审关闭** | ①通过项 **15** ②强度 **R 14 / A 1**（唯一 A 是 R8b）③未闭 finding **0** ④遗留 A 档 **1** | `mine/inspector/STAGE3-ACCEPT.md`、`mine/lead/STATUS-2026-10-25.md` §3.23 |
| **纪律族** | 2026-10-25 | **41 条**编号纪律（1..41 严格有序），每条一句可执行形式 + 一个真实实例 | 编号权威在 `DISCIPLINES.md`；其它文件自有的 §12.x 必须附映射表 | `kvmem/m2_visibility/mine/lead/DISCIPLINES.md` |
| **verify.sh** | 2026-10-25 | 9 项断言，**8 绿 1 红** | 红项=第 1 项：引擎工作区比归档多 100 行（归档 +391 / 实时 +491，全在 `src/llama-kv-cache.cpp`） | `README.md:58-77`、`patches/MANIFEST.txt` 末节 |

### 3.4 未完成事项与未来开发计划（原文摘录）

**A. 未闭项清单（`HANDOFF.md` §9 原文照录）**

```
F-M3-1  声明 §7 陷阱① 描述错（「含块的安全重置」）—— 冻结期内不改，阶段末一次性修订
F-M3-2  S3 的修法未过其 §11.4 自检 —— 已由单元注入救回，记录在案
F-M3-3  I5/I6 端到端未覆盖 —— 判 U
F-M3-4  falsified_by 混两种类型（20 个 case id + 5 条散文）；flipped 列只装 judged 判据
F-M3-5  attempt 1 停在第 32 轮 —— 「未完成」，副本在 m3/_interrupted_32of50/
F-M4-1  n_predict：引擎不暴露该属性（记 null），声明 24 与实际不一致，无证据判定哪个生效
F-M4-3  M4-C 未开始 —— M4 当前最大未闭项
F-M5-1  M5 的 (a)/(c) 两探针未办
F-PS-1  补丁工作区比归档多 100 行（src/llama-kv-cache.cpp +391 -> +491），来源与授权未判定
未测    换输入那一类的稳定性 / 引擎内部池状态 / S3 的端到端可失败性 / 判据的第三份副本
```

**B. 未来开发计划（按依赖顺序，全部有原文出处）**

1. **M4-C：leases 真实接入 + 承重自证** —— 判据是「删掉它必须有断言变红」，不是「加上调用」（`HANDOFF.md:117`、`FEATURES.md` §3）
2. **M5 的 (a)/(c) 两探针** —— 边界已冻结：只管「无中生有」，不管「张冠李戴」；漏判优先于误判（`HANDOFF.md:118-120`）
3. **M2 规划器 / M2 完整（驱逐 / 多会话 / 位置租约）** —— 全仓 grep `规划器|planner` 只命中 `session_state.py` 的 `planner_version` 布局字段，「几何冻结 ≠ 规划器实现」（`FEATURES.md` §3）
4. **M1.8 三处 judge 冲突** —— 零补丁、零产物（`FEATURES.md` §3）
5. **E10 收口（最大阻塞，方案未实施）** —— `PLAN-E10-FIX.md` §0 原文：**「我们已经把问题定位到『拼接式 KV 记忆』这个做法本身……下一步是装仪表（看得见注意力）、改路由（让问题只看该看的那块）、必要时改为整体编码（让块之间互相可见）。」**
6. **D / E 两探针（未决，连要不要做都没定）** —— `</think` 成因三处共变，要单因子必须补 D（同内容同长度只去角色标记）与 E（同形式加长到 `91 token）；「只补 D 不补 E，会把『形式 vs 长度』永久留在未分离状态」（`FEATURES.md` §4.1）
7. **训练路线（明确未做）** —— 7B 本体不训；要训只训 `1% 编码器 + LoRA（ICAE 路线），租 24GB 卡 8–10 小时约 $3–5；`X1 训练` 判定【明确未做·查无】：无 torch、无 `train/`（`docs/legacy-2026-10-24/README-HANDOFF-2.md` §0/§5.4、`PROJECT-STATE.md` §6）
8. **X2 M4 空闲巩固 / X3 M5 生成后校验（旧判定）/ X4 M3 产品侧 LRU** —— 三条均【明确未做·查无】（`PROJECT-STATE.md` §6）；注：X3 后来由 M5 落地，X4 部分由 M3 + 租约表落地
9. **未检验（照实，不许含糊）** —— 弱 GPU 长跑、多用户并发、attach/detach 与 save 交叉的不变性、多引用竞争、**free VRAM（AMD 卡无 nvidia-smi，未测出，不编数字）**、M5 在换措辞/长生成下的表现（`mine/lead/STATUS-2026-10-25.md` §5）

### 3.5 关键目录结构说明

| 目录 | 是什么 | 出处 |
|---|---|---|
| `kvmem/m2_visibility/` | **14B 线**（M2 落地 + 四格实验 + 判定文档）+ 共享记录；内部按里程碑分子目录 `m2/ m3/ m4/ m5/`，按职能分 `registry/ chat_lease/ runs_m14b/ mine/{lead,inspector}/ archive/` | `kvmem/m2_7b/MOVE-MAP.md`、`kvmem/m2_visibility/INDEX.md` |
| `kvmem/m2_7b/` | **7B 线全部产物**（跑、块、证据），**已冻结，不再产出**；`evidence/t0NN/` 是逐字节副本（因 `runs_*/*.json` 被 `.gitignore` 排除，不复制等于证据不存在） | `kvmem/m2_7b/MOVE-MAP.md`、`kvmem/m2_7b/evidence/t010/README.md` |
| `kvmem/m2_visibility/mine/lead/` | 队长产物：PREREG（预登记）、BRIEF（派单）、DELIVERY（交付验收）、STATUS（逐条裁决）、DISCIPLINES（纪律编号权威） | 目录实测 |
| `kvmem/m2_visibility/mine/inspector/` | 检测员产物：CRITERIA（判据冻结）、PREREG、ACCEPT（验收）、BLIND-CHECK（盲写清单）、GATE（闸门自检）、SPEC（规格书）、SRC-CRITERIA（缺口 #7 判据） | 目录实测 |
| `docs/` | 根级说明 + `legacy-2026-10-24/`（早期文档归档，**多处与代码不符，仅存「当时怎么想」**） | `README.md:84`、`docs/legacy-2026-10-24/_ARCHIVE.md` |
| `legacy/biomem-legacy-src/biomem/` | 前身项目 biomem 源码残留（应用层记忆：8 层记忆模型 + 巩固/遗忘曲线） | `legacy/biomem-legacy-src/biomem/README.md`、`docs/ARCHITECTURE.md` |
| `llama.cpp/` + `llama.cpp-upstream/` | 我们的 fork（分支 `persistent-memory`，**嵌套 git 仓库**）/ 上游纯净克隆（只读基线 `8e5a58d`）；各 129 份 md，**本轮原样不动** | `README.md:80-86`、`docs/README-PHASE1-ENGINE.md` 目录表 |
| `patches/` | 引擎补丁 + 归档 + `MANIFEST.txt`（sha256 / numstat）。补丁存成文件而非子目录，因为 `llama.cpp/` 是独立 git 仓库，纳入父仓库只会存一个 gitlink 指针 | `README.md:88-101` |
| `tools/` | 探针、评测、诊断脚本（`chat.py`、`kvslots.py`、`m3_lease.py`、`facet_index.py` 等） | `mine/lead/BRIEF-M3.md`、`BRIEF-M4.md` |

### 3.6 事实性数字 / 门槛一览（每条带出处）

| # | 数字 | 含义 | 出处 |
|---|---|---|---|
| 1 | **91 cells**，`delta=+4005`，落位 `[4005,4096)`，`pos_max=4095` | M4 产品块几何 | `HANDOFF.md:63-64` |
| 2 | **51 cell**，`raw_pos_max=4095` | M3 / M2 三块几何 | `kvmem/m2_visibility/m3/README.md` §0、`m2/README.md` |
| 3 | `-ngl 99 -c 8192`，KV **q8_0**，n_seq 8，n_predict 64，位置锚 4096，**14B** | 全项目加载参数串 | `HANDOFF.md:65` |
| 4 | 模型 8,988,110,240 B，sha256 `0b319bd0…` | 14B GGUF 实测 | `runs_m14b/REPORT-14B-READY-AND-DLL.md` |
| 5 | n_ctx 8192 用到 **9309/10224 MiB**，余 **915 MiB** | 10G 卡跑 14B 的显存实测（推翻了「装不下」的预判） | `runs_m14b/REPORT-14B-READY-AND-DLL.md` §4.1 |
| 6 | 起始 free **9426 MiB** | 每跑前的显存基线 | `mine/lead/DELIVERY-M2.md` 局限⑤ |
| 7 | **1188 + 104464 × n** | 14B 块文件 size 断言式（104464 = 每格 4+12 元数据 + 48 层×2×1088 B/行） | `runs_m14b/REPORT-14B-BLOCKS.md` §0 |
| 8 | **104448** | KV pool 每 token 步长（**与 104464 不同**，曾写混，已纠正） | 同上 |
| 9 | **102 KB/格**（14B）vs **30480 B/格**（7B+q8_0） | 每 token = 708 B 头 + 每格字节数(N) | `mine/lead/PREREG-14B-4CELL.md` §0 |
| 10 | **70%** 利用率门槛 | `freeze_check` 三阈值：`GATE 1.30 / COV_MIN 0.35 / REL_CUT 0.55` | `PROJECT-STATE.md:531`、`freeze_check.py:26,67,72` |
| 11 | 召回率-距离断崖：**0-1k 56%（5/9）· 1-2k 71%（5/7）· 2-4k 72%（13/18）· 4-8k 64%（9/14）· 8-16k 0%（0/9）· >16k 0%（0/3）** | 「这不是缓慢衰减，是断崖」；直接推翻「常驻区 pos 0..64k 平铺」设计 | `docs/legacy-2026-10-24/README-HANDOFF-2.md` §6.1 |
| 12 | 8k ctx 池 **238 MiB**；1k token 记忆 **29.8 MiB**；100k token 记忆 ≈ **3 GB** 磁盘；save 5–20 ms / load 20 ms | 存储与延迟成本 | `docs/legacy-2026-10-24/README-HANDOFF-2.md` §6.5 |
| 13 | 单次 placement **52–65 ms**（8k ctx，q8_0，含从磁盘 load） | 放置开销 | 同上 §6.6 |
| 14 | 一次完整 run `elapsed_s` 中位 **6.97 s**（n=16，区间 6.8–7.4） | E10 成本口径：「算力几乎免费，真成本是布局 key / 哈希链 / 复算」 | `kvmem/m2_visibility/E10-NEXT.md` §0 |
| 15 | `head_gap > 0` ⇒ **空答 7/7**；零 trace 仅 **1/7** 可查 | 顶部空洞 ⇒ 记忆不生效（两数不可混写） | `PROJECT-STATE.md` §7.6.1、`evidence/t018/README.md` |
| 16 | `masked > 0` 的块行 **0 条**（两臂各 100 条块行） | 掩码层不是原因 | `README.md:47`、`ISOLATION-REPORT.md` §7 |
| 17 | 补丁 **6 文件 / 600 insertions / 0 deletions**（归档 500） | 引擎改动规模 | `README.md:30,74-77` |
| 18 | `verify.sh` **9 项断言 / 8 绿 1 红**；差 **100 行**（归档 +391 / 实时 +491） | 自检现状与唯一红项 | `README.md:58-77` |
| 19 | Stage 3：**15 通过 / R 14 · A 1 / 0 finding / 1 遗留 A 档** | 缺口 #7 终审 | `mine/inspector/STAGE3-ACCEPT.md` |
| 20 | 纪律 **41 条**（1..41 严格有序；实测 41 条、无缺号无重号，第 24/38/41 条分别在 L52/L66/L69） | 工程纪律编号权威 | `mine/lead/DISCIPLINES.md` |
| 21 | M4：**9 轮**对话 / **10 句**判定 / **6 条** keep / **1 块** / **6 行** memory / **7 行** `memory_source` | M4 结算 | `m4/README.md` §0 |
| 22 | M4-A 两口径 **8**（机械次数）/ **2**（语义次数） | 禁止写单个数字 | `HANDOFF.md:105-107` |
| 23 | M4-B 四臂：**91/91/79/91** cells；答案 **浙B-3F19K / 浙B-3F19K / 苏A12345 / 浙Q-00000** | 「模型答的是块里的内容，不是块的长度」 | `HANDOFF.md:109-116` |
| 24 | 三问 sha `852a5e5e6ab70eeb…` / `dacdc1a89ef08165…` / `46272e43287c5ff7…` | 回归锚（Stage 2、接租约验收都复用） | `mine/inspector/STAGE2-I8C-ACCEPT.md` |
| 25 | 「记忆占上下文比例」 | **UNKNOWN** | 全库 grep `占比` / `注意力占比` 在项目自有文档中 **0 命中**（仅 `legacy/biomem` 之外无相关段落）；库内最接近的量是召回率-距离表（第 11 条）与每格字节数（第 9 条） |

---

## 4 本次盘点发现的文档漂移（**建议 lead 在写新文档时逐条裁定**，我未改任何文件）

| # | 漂移 | 证据 | 影响 |
|---|---|---|---|
| D1 | `README.md` 结构表写 `docs/PROJECT-STATE.md`，**实际文件在仓库根** `PROJECT-STATE.md` | `README.md:80`；`ls docs/` 只有 `legacy-2026-10-24/` 与 `README-PHASE1-ENGINE.md` | 新 README 若照抄，链接 404 |
| D2 | `INDEX.md` §3.3 引 `SRC-CRITERIA.md  1105 行 / d97c663aa42dc0bb`，**现值是 1122 行 / 82bd0f0938ef9480** | 实测 sha256 与行数；`d97c663a` 现在是 `_r2/SRC-CRITERIA.bak.md`（94431 B / 1106 行） | 引用过期锚，会让复核者按错哈希验错文件 |
| D3 | `_r2/src.gen.bak.md` 与 `SRC-CRITERIA.md` **逐字节相同**（95653 B / `82bd0f0938ef9480`） | 实测 sha256 | 「三份 SRC-CRITERIA」实为 2 版本 + 1 副本 |
| D4 | `README.md` 写「kvmem/ 下 **73 份** md」，实测 **72**；`INDEX.md` 写 m2_visibility「**52 份**」，实测 **54** | 本次 `find` 实测 | 两个计数口径都已过期（D2 的副本可能被算进/漏出） |
| D5 | `PROJECT-STATE.md` §1 写「**M3/M4/M5 零代码**」，而 10-25 三者均已落地并验收 | `PROJECT-STATE.md:31` vs `HANDOFF.md`、`FEATURES.md` | 这是**新旧文档同时「权威」时的最大冲突**：引擎层（E/S/P）以 PROJECT-STATE 为准，里程碑状态以 HANDOFF/FEATURES 为准 —— 新进度文档必须显式声明这条分界 |
| D6 | M4-B 锚有两个尝试号：`FEATURES.md` 第 9 行引 `run_m4_ablate_plate_a5.json = cf4a86340d54221a`，`HANDOFF.md` §5.2/§7 引 `run_m4_ablate_plate_a7.json = 77e11a04aacd24c5` | 两文件均存在（`m4/` 下有 a2–a7 共 6 个 json） | 「同一功能两个锚」正是纪律明令禁止的形态；新文档须二者选一并写明为何 |
| D7 | `PROGRESS §13.1` 的四动作引文**行号错 + 称「原文」实为转述 + 未声明 HANDOFF 不含 E10 前提** | ① `PROGRESS:1745` 写「（`HANDOFF.md:113-120` 原文顺序）」，但 `HANDOFF.md:113-120` 实为 **M4-B 四臂结论尾巴（113-115）+「M4-C 未开始」（117）+ 代码块结束（118）**；四动作原文在 **`HANDOFF.md` §4，L71-78**。② 内容虽对得上，但 L74 原文是「**+ 承重自证**」、L76 是「三件绿 **=>**」，`PROGRESS:1746` 写成「三件绿后写…」⇒ **是转述，不是原文**。③ `HANDOFF.md` 全文 **`E10` 命中 0 次、无 `M2.5` 字样、无「写于/截至/日期」前提句**；它能支持的是「M4-C 与 M5 的先后」，**不支持**「M2.5 排第几」 | 读者按 `113-120` 去核会核到无关段落，进而怀疑整段引文；更实质的影响：**§13.1 的依赖序（M2.5 先）在 HANDOFF 里没有任何对应原文**，两处顺序的冲突没有「前提声明」可挂靠，只能按§13.1 的理由（E10 污染判据）自行重排 |
| D8 | `run_compare.json` 的 `acceptance.all_pass` **用一个布尔覆盖两个被测量对象** | 九项里仅 `2_no_bare_reset_and_no_safe_reset_all` 判**今天**的 `chat.py`（`4c8d73e955c108ff`），其余七项判**当年**那三份（`before/revert` = `77af15cdef242705`、`after` = `1ad3ce763f430376`）；**三者都不等于今天这份** | 一个 `all_pass: true` 会被读成「今天这份也满足全部九项」。**定性：自述强于实测**（与 D7 同类）—— 布尔相与把两组证据绑成一句话，读者拿不到分组，就必然过度解读。**不是红灯**：源码前进是正常的，历史项本就不该约束当前源码 |
| D9 | **「非单调 ⇒ 容量假说被否」这个读法不成立**：现有三个臂里，第 4 块的**内容**与**总 cells** 完全共线 | 三段固定 `21+18+12=51` ⇒ `cells_total ≡ 51 + 第4块 cells`，而第 4 块体积由内容决定：`iso_habit_bot` **63** = habit 副本 12 / `iso_dup4` **69** = project 副本 18 / `iso_car_back`、`iso_topgap` **70** = car 外来 19（取自各 run json 的 `layout.segments`；详见附录 F.1） | **两变量对这三个读数给出完全相同的预测，谁也没被区分**。`PROGRESS:457`（§4.3 #5）用它否掉了容量假说，lead 的战前判断（「显著性解释得通、容量解释不通」）也用了它 ⇒ **两处必须一起降级**。真正被否掉的只有「容量随 cells 单调」这一条更弱的说法 |

---

## 附录 A 建议的 README 章节目录

> 目标：**唯一一份 README**，中文正文 + 保留英文技术术语与命令。定位是「第一次来的人 10 分钟读完就懂这是什么、到哪了、怎么复算」，**不承载里程碑细节**（细节进进度文档）。

```
# llama-mem

## 一句话
（把长期记忆做进推理引擎的 KV 张量里，而不是拼进 prompt 字符串）

## 1 这是什么
  1.1 主流「记忆」方案的问题（三条：prompt 变贵 / 记忆无结构优先级 / 不可审计）
  1.2 本项目的做法（记忆在 KV cache 里，删掉对话历史记忆仍在）
  1.3 一句话定位与路线来源（biomem 前身 → 改引擎）

## 2 核心机制
  2.1 记忆序列以 KV 张量常驻（seq_cp 引用计数挂载）
  2.2 位置重排：seq_repos_local 只旋转被移动的 cell
  2.3 Hadamard 三明治（H → rope → H，RoPE 与 H 不对易）
  2.4 kv_unified 下的位置区间区分
  2.5 补丁形态（6 文件 / 600 insertions / 0 deletions，为什么存成 patch 文件）

## 3 当前状态
  3.1 三层总表（引擎层 / 记忆读取能力 / 产品层）
  3.2 逐格状态指路（一行一句 + 指向进度文档）
  3.3 已定位但未修复的缺陷：E10（一段话讲清「失败在生成侧」）

## 4 一键复算
  4.1 bash verify.sh 与 9 项断言
  4.2 当前 8 绿 1 红的红项是什么（100 行差）
  4.3 退出码陷阱（不许写 cmd | tail; echo $?）

## 5 仓库结构
  5.1 顶层目录表（README/HANDOFF/FEATURES/PROJECT-STATE/docs/patches/kvmem/tools/两棵 llama.cpp）
  5.2 kvmem/ 是证据不是文档（73→72 份 md 的口径更正）
  5.3 不入库的内容（*.gguf / *.kvmem / build*/ / *.db / .env）
  5.4 锚的两类（仓库内可复算 / 只在本地）

## 6 词表与概念
  （块 / cell / position 区间 / gap=0 / 锚点 / 只读块 / 租约 / 接地 / 弃答 / 强度 R·C·A·S）

## 7 文档地图
  7.1 两份新文档的分工（README vs 进度文档）
  7.2 证据在哪（kvmem/m2_visibility 与 kvmem/m2_7b）
  7.3 历史文档已删除，备份在哪（`D:\llama-mem-backup-2026-10-25`，仓库外）

## 8 作者与许可
```

---

## 附录 B 建议的进度文档章节目录 + 里程碑表草稿

> 目标：**完整里程碑细节，800+ 行不砍数字**。定位是「结论 + 证据 + 未闭项 + 未来」的**唯一**长篇文档，替代 HANDOFF / FEATURES / PROJECT-STATE / STATUS 与 27 份 LEDGER 类（PREREG/ACCEPT/CRITERIA）+ 若干 EVIDENCE。

```
# llama-mem 项目进度与未来开发

## 1 文档定位与口径
  1.1 这份文档取代了哪些文件（对应台账 §2 的 75 行 MERGE-INTO-PROGRESS）
  1.2 强度四档 R/C/A/S（自报不许升成重算）
  1.3 锚格式（文件名 = sha256 前 16 位；产物重跑 ⇒ 结论自动过期）
  1.4 措辞纪律（不说「稳定」说「逐字节恒等」；两个口径不许混写；单例非统计）
  1.5 引擎层 vs 里程碑状态的分界（D5：引擎层以 PROJECT-STATE 为源，里程碑以 HANDOFF/FEATURES 为源）

## 2 里程碑总表（一页看完，17 行见附录 B.1）
  2.1 状态图例
  2.2 已完成 / 部分 / 未开始

## 3 引擎层判定总表（E1–E10 / S1–S3 / P1–P8 共 25 条）
  3.1 每条：判定 + file:line 锚 + 它不能证伪什么
  3.2 E10（已定位·生成侧）：三轮取证的完整过程
  3.3 X1–X4 明确未做项与 grep 范围

## 4 M2 放置与可见性
  4.1 M2 几何（51 格三块坐标，gap 0，问位序列）
  4.2 隔离报告：七条假设被逐一排除 + 四格表落位「②己」
  4.3 2×2 四格（近似重复只在满载时致命）与掩码偏置探针（差半个对数单位）
  4.4 E10 两轮设计（E10-NEXT 三候选 / E10-NEXT2 距离轴与 iso_dup_p3 判决实验）
  4.5 证据目录 t010/t014/t016/t017/t018/t020/t021 逐目录一句话 + 命令行
  4.6 负对照如何把 M2 结论削到只剩一条不可猜事实

## 5 M3 块生命周期
  5.1 验收三件事（pin/refcount、文件只读、cell 余量）
  5.2 50 轮结果（51 cell / 4095 / 50-50 命中 / 三块 sha 恒值 / 首轮 34.9 s 后 11.6–11.7 s）
  5.3 「通过」必须连读的五条
  5.4 判据 5 的反向结果（reset 不报错但句柄全丢 ⇒ pin 必须靠租约表）
  5.5 attempt 1–3 全部保留为观测（含 74 分钟无效数据的教训）
  5.6 接租约四站表 + 严禁 safe_reset_all

## 6 M4 写入固化
  6.1 9 轮对话 → 10 句判定 → 6 keep → 1 块 91 cells → 新进程检索作答
  6.2 判据要点（K/D/U、封闭词表、2026-10-28 相对时间锚定、宁多记不漏记）
  6.3 九项 acceptance 逐项
  6.4 M4-A 输出层过滤（两口径 8 / 2）
  6.5 M4-B 车牌句消融（四臂 91/91/79/91 + 必须一起引的混淆）
  6.6 M4-C leases 真调用（未开始，判据=删掉必须变红）
  6.7 三个未闭项

## 7 M5 接地与弃答
  7.1 反例（苏A12345 vs 浙B-3F19K）
  7.2 判据五条边界（只管无中生有 / 漏判优先 / 不读 prompt / 不读二进制）
  7.3 四例回归 + 三条边界例
  7.4 产品级 P0 闭环（R14 裁决）与两探针未办

## 8 14B 四格与规模假设
  8.1 换 14B 的代价（7B 块全部作废；102 KB/格 vs 30480 B/格）
  8.2 四格定义 E/F/X1/B57 与 7B 2×2 的对应
  8.3 24 token「齐一」是截断假象（c7d4e377 vs 31bff41f）
  8.4 n_predict=64 全分岔 ⇒ 规模/分配假设 = 未检验
  8.5 装置实测（8,988,110,240 B / 9309 of 10224 MiB / 余 915 MiB）
  8.6 块格式常量 1188 + 104464×n 与 104448 的区别
  8.7 盲检与闸门（盲态解除 00:55:08）

## 9 7B 线（已冻结）
  9.1 目录分离与旧→新路径映射
  9.2 7B 期几何公式 lo = 4096 − (slot−1)×spacing − n
  9.3 定位实验与 F 臂跨执行者复现（11e20d78a1f18a98）
  9.4 64-token 污染探针与其盲写清单
  9.5 冻结规则（不再产出）

## 10 缺口 #7：源文本权威副本（Stage 1a → 3）
  10.1 缺口真实形态（唯一性 + 消费方全覆盖 + 可校验）
  10.2 Stage 1a 三条负向测试
  10.3 Stage 1b text_kind 分布
  10.4 Stage 2 三问 sha 回归 + I8-C
  10.5 Stage 3 终审（15 通过 / R14·A1 / 0 finding / R8b 遗留 A 档及成本理由）
  10.6 三处 fail-open 的运行时探针（四个报错串原文）
  10.7 R9 重跑登记（diverged=True 证明 grade 由真算产生）

## 11 工程纪律（41 条）
  11.1 编号权威声明与映射表规则
  11.2 一..三十八 逐条（形式 + 真实实例）
  11.3 五个陷阱（reset_all 清块槽 / shim pos_max 报 -1 / reset(块seq) 静默清空 / 不贴锚点提问 = 静默空答 / safe_reset_all 叠块）

## 12 未闭项与未检验
  12.1 F-* 清单九条（原文）
  12.2 未检验（弱 GPU 长跑 / 并发 / 多引用竞争 / free VRAM 未测出 / M5 换措辞）
  12.3 「可能需要」四条（无判据、无共识：D-E 探针 / 块内位置声明 vs 结果 / 消融是否须跨进程 / raw_to_delivered_delta 跨层差）

## 13 未来开发计划
  13.1 依赖顺序（M2.5 → M3 → M4 → M5，顺序不可颠倒及其理由）
  13.2 M4-C（当前最大未闭项）
  13.3 M5 两探针
  13.4 M2 规划器 / M2 完整
  13.5 M1.8 三处 judge 冲突
  13.6 E10 收口三选项（注意力仪表 / 路由 / 整体编码）
  13.7 训练路线（ICAE + LoRA，$3–5，未开始）
  13.8 被推翻的顺序（为何先做 M5 核心）

## 14 历史与失真清单
  14.1 旧文档取代关系表（5 行）
  14.2 引用规则：代码 > 运行产物 > 旧文档（仅史料）
  14.3 已纠正的失真（spacing 自述 64 实际 128 / 锁测试答错问题 / spacing 与 104448 混写 / 「32 轮按计划未到」）
  14.4 前身项目 biomem 一行

## 15 附录：锚、产物与复算
  15.1 锚表（13 个 run json 的 sha16 + 字节数）
  15.2 只在本地不可复算的锚（*.kvmem / DLL / m4_memory.db）
  15.3 复算命令四段（hashlib / check_m3_prereg_consistency / check_m3_injection / check_ablate_run）
  15.4 证据地图（四组同名不同作者文件、五份「唯一观测」干扰项）
  15.5 归档包与 tarball sha
```

### B.1 里程碑表草稿（编号 / 日期 / 一句话结论 / 关键数字）

| 编号 | 日期 | 一句话结论 | 关键数字 |
|---|---|---|---|
| M0 工具链与构建 | ≤2026-10-24 | Vulkan 构建 + 7B Q4 模型 + OpenAI 兼容服务跑通 | `build-vulkan/` 657 target；RX 6750 GRE 10GB（9426 MiB free）；Qwen3-8B Q4 约 35–40 tok/s |
| M1 机制验证 | 2026-10-24 | 跨进程持久化四组合实测通过；「prompt 里无该信息仍答对」达成过一次 | — |
| M1.7 检索层 | 2026-10-24 | 文本检索链可用（**不等于 KV 记忆可用**） | recall@1 0.762 / recall@3 0.952 / MRR 0.921 |
| M1.8 三处 judge 冲突 | — | **未开始**，零补丁零产物 | — |
| E10 4 段可见性 | 2026-10-24 | **已定位、未修复**：非存储/非可见性缺陷，失败在生成侧 | cell 层 home 21/21；`masked>0` 的块行 0 条；A/home 0/5、A/project 5/5、A/habit 0/5、A/car 5/5、B 15/15、C 5/20 |
| T-010～T-023 第四轮 | 2026-10-24 | 打死的不是假设，是一个判据 | `llama-kv-cache.cpp` `dbe52f9124f1ad29`（ins=500 del=0）；7 条假设被排除 |
| M2 落地（14B 51 格） | 2026-10-25 | 三问全中且多跑逐字节一致，**但负对照把结论削到只剩一条不可猜事实** | habit 12 @[4045,4057) / project 18 @[4057,4075) / home 21 @[4075,4096)；问位 4096→4169→4242 |
| M3 块生命周期 | 2026-10-25 | **通过**（判据 1–4 有效应；判据 5 pin 测出反向结果） | 51 cell 恒、raw_pos_max 4095 恒、50/50 命中、三块 sha 不变、四泄漏计数器全 0 |
| M3 接租约 | 2026-10-25 | 从「护栏就绪、覆盖率 0」变为已接入四站 | `eng.reset(`=0 / `safe_reset_all`=0 / `leases.reset(`=4 |
| M4 写入固化 | 2026-10-25 | 九项 acceptance 全真，状态「已实现·未验收」 | 9 轮对话 / 10 句判定 / 6 keep / 1 块 91 cells 独占 position 0 / 6 行 memory / 7 行 memory_source |
| M4-A 输出层过滤 | 2026-10-25 | **已绿**（两口径必须同时报） | 机械 8 / 语义 2 |
| M4-B 车牌句消融 | 2026-10-25 | **已判出**：模型答的是块里的内容，不是块的长度 | 四臂 91/91/79/91 cells → 浙B-3F19K / 浙B-3F19K / 苏A12345 / 浙Q-00000 |
| M4-C leases 真调用 | — | **未开始**（当前最大未闭项；判据=删掉必须变红） | — |
| M5 接地与弃答 | 2026-10-25 | 校验器核心落地，产品级 **P0 闭环通过** | 反例「苏A12345」vs 真值「浙B-3F19K」；边界=只管无中生有、漏判优先 |
| 14B 四格 E/F/X1/B57 | 2026-10-25 | 24 token「齐一」是截断假象；64 token 全分岔 ⇒ **规模假设未检验** | E=F=X1=B57=`c7d4e377fdc64950`，run0=`31bff41f`；102 KB/格 vs 7B 30480 B/格 |
| 7B 线冻结 | 2026-10-25 | 产物全部迁至 `kvmem/m2_7b/`，不再产出 | 换 14B ⇒ 7B 的 .kvmem 全部作废 |
| 缺口 #7 Stage 1a/1b/2 | 2026-10-25 | 三级全部通过（注册表不变量 / 层 1 结构化 / chat.py 改读注册表） | 幂等 `id=1`；`SourceConflict` 双 hash；三问 sha `852a5e5e…`/`dacdc1a8…`/`46272e43…` |
| 缺口 #7 Stage 3 | 2026-10-25 | **定稿·终审关闭** | 15 通过 / R14·A1 / 0 finding / 1 遗留 A 档（R8b） |
| 工程纪律 | 2026-10-25 | **41 条**编号纪律成型，编号权威在 `DISCIPLINES.md` | 41 条 + 五个陷阱 |
| verify.sh 自检 | 2026-10-25 | **8 绿 1 红**（红项=补丁工作区比归档多 100 行） | 9 项断言；归档 +391 / 实时 +491 |

---

## 附录 C VENDORED 第三方语料（仅计数，不逐条建议）

| 路径 | md 数 | 动作 |
|---|---|---|
| `D:\llama-mem\llama.cpp/`（我们的 fork，分支 `persistent-memory`，嵌套 git 仓库） | **129** | **UNTOUCHED** |
| `D:\llama-mem\llama.cpp-upstream/`（上游纯净克隆，只读基线 `8e5a58d`） | **129** | **UNTOUCHED** |
| 合计 | **258** | 原样不动 |

两树 md 数量恰好对称（129 + 129），与「upstream 本地 clone 后开分支」的来源一致。
**253 → 258 之间无第三棵 vendored 树**；`build-cpu/`、`build-vulkan/`、`bin/`、`downloads/`、`patches/`、`tools/` 下均无 `.md`（本次 `find` 实测）。

---

## 更正记录（本台账的唯一自我修订）

| 日期 | 位置 | 原记 | 更正为 | 根因与复验 |
|---|---|---|---|---|
| 2026-10-25 | §2 第 34 行、§3.3「纪律族」、§3.6 第 20 条、附录 B 章节目录与 B.1 | `DISCIPLINES.md` = **38 条**纪律 | **41 条** | 原记取自 `kvmem/m2_visibility/INDEX.md` **L16 / L91 的过期断言**（「看纪律 38 条」「38 条，1..38 严格有序」），我未回源核对即采信，属**二级转述当一手证据**（正是本台账 §2 第 11 行批评过的形态）。复验：`grep '^\| ?[0-9]{1,2} ?\|' DISCIPLINES.md` 得 **41 行**，编号 1..41 **连续、无缺号、无重号**；`| 24 |`@L52、`| 38 |`@L66、**`| 41 |`@L69**，最大行号 41。文件字节数 25,703 与本台账初盘一致 ⇒ **一直是 41，非后来增补**。 |
| 2026-10-25 | 同上 | — | 顺带补漂移条目 **D7** | `INDEX.md` L16/L91 声称 38 条，实测 41 条 —— 与本台账 §4 的 D4（`73 / 52` 份 md 计数过期）同源：`INDEX.md` 的统计口径整体过期。 |
| 2026-10-25 | §2 第 9 行（`README-HANDOFF-2.md` 的去向列） | 「`30464 B/token`」 | 应为 **`30480 B/格`** | 我当时的算术抄写错误：源文件只写 `30480`；`30464 = 30480 − 16` 是 `PREREG-14B-4CELL.md` L93 的一条**佐证等式**（`30480 = 30464 + 16`），不是独立事实。新进度文档统一用 `30480`（7 处），**未丢内容**。 |

---

## 验收记录（本轮交付的可追溯证据，lead 指定四条）

> 记录人：检测员（只读复核）。以下每一条都由检测员**独立复算**，不含执行者自证。
> 快照口径：正文文件的行号会随编辑漂移，**自指 sha16 一律只写在本表**（写进正文会立刻改变哈希）。

| # | 事项 | 检测员实测 | 判定 |
|---|---|---|---|
| 1 | 原件处置 | 台账 §2 的 85 行中 **84 份已从工作树移出**；工作树内项目自有 md 只剩 **3 份**（**分层口径**，2026-10-25 修订：不写死总数、分两层登记 —— **交付层 3 份** = `README.md` / `PROGRESS-AND-ROADMAP.md` / 本台账；**另有判据层临时产物 N 份，逐份登记路径与 sha16**，现 **N=1**：`kvmem/m2_visibility/m5/PREREG-M5-PROBES.md`，**11,158 B / 133 行 / sha16 `b374401990b79332`**，**收口义务**：M5 收口时并入 PROGRESS 或删除并说明并入哪一节；**不得**被 README / PROGRESS 当交付文档引用，不进文档目录与索引导航） | ✅ 按 lead 终裁执行（先复制到 `D:\llama-mem-backup-2026-10-25`，再物理删除） |
| 2 | 备份完整性 | `D:\llama-mem-backup-2026-10-25` 内对应 **85 份**，逐份 `statSync().size` 与台账 §2 第 3 列（字节）**完全相同：85 / 85** | ✅ **可回退、零内容丢失** |
| 3 | 照录与失效引用 | ① §16 附录 A（物理定律 L1–L12）与 `STATUS-REPORT.md` 第 146 行起 **222 行逐行比对，mismatch = 0**（只允许多一个 `#`）；L3b 的 7 行崩坏表原样（0/1/5/10/25/50/100 → A-4417 / A-4417 / A-4417 / A-4417 / **A-444417** / `ioneerioneer` / `3`）。② §17 附录 B 与 `PROJECT-STATE.md` 505–558 **54 行比对，mismatch = 0**。③ FIX-C：抽 10 个已删 basename（HANDOFF / FEATURES / PROJECT-STATE / STATUS-REPORT / ISOLATION-REPORT / E10-NEXT2 / DISCIPLINES / M4-CRITERIA / STATUS-2026-10-25 / table_m3_rounds）逐份 grep 两份文档，**「仍在工作树／仍保留」类现在时违规 = 0** | ✅ |
| 4 | §17.6 行号偏移表（本轮唯一「用新结论推翻照录原文」处） | 检测员在 `llama.cpp/`（分支 `persistent-memory`）实跑 `git diff -U0`：① `6 files changed, 600 insertions(+)`，deletions 合计 **0**；② `src/llama-kv-cache.cpp` **确为 5 个 hunk**：`@@ -10,0 +11,2 @@` / `@@ -591,0 +594,296 @@` / `@@ -1601,0 +1900,29 @@` / `@@ -1720,0 +2048,157 @@` / `@@ -1722,0 +2207,7 @@` ⇒ 区间 **11–12 / 594–889 / 1900–1928 / 2048–2204 / 2207–2213**；③ 五个偏移 **−2 / −298 / −327 / −484 / −491** 由累计新增 2 / 298 / 327 / 484 / 491 独立推得，全对；④ 600 = 20+4+13+491+10+3+31+3+25，且与 `--numstat` 逐文件（20 / 17=4+13 / 491 / 13=10+3 / 31 / 28=3+25）一致；⑤ 旧规则第二支（≥888 套 −296）最大误差 = **491 − 296 = 195**；⑥ 反例为真：workspace `src/llama-kv-cells.h:482` = `bool pos_move(...)`，上游 HEAD 第 **451** 行确为空行 | ✅ 通过 |
| 4-补 | §16 / §17 起始行号锚点（对照冻结快照） | **当前冻结快照**：`README.md` **21,654 B / sha16 `85f6a7d38b85bb49`**（多轮未变）；`PROGRESS-AND-ROADMAP.md` **183,793 B / sha16 `34b7a35b1abb0468`**。**行数口径**：换行符 **2,433** 个 ⇒ 正文 2,433 行；`split("\\n").length` = **2,434**（末尾换行产生的空段）。**锚点随 F-M3-7 收尾下移**：**§16 副本首行 = L2074**（旧 2068）、**§17 副本首行 = L2311**（旧 2305）、**§17.6 = L2373**、§16 节头 L2058、§17 节头 L2299。§16 副本 **222 行 / mismatch 0**；§17 副本 **62 行 / 剔除标注后 mismatch 0** | ✅ 锚点已同步（2026-10-25） |
| 4-注 | §17 照录区自述的修正（**已闭环**） | L2301 已改为「原文未被改写…**3 处（分布在 2 行）**行内 `〔照录注：旧值〕`…剔除后与原文逐字一致」；L2315 补回被吞的 `（本项目唯一大偏移源）` 12 字（标注改为**纯追加**）；L2309 标注移到「即」之后、原句尾保留。**检测员实测**：活体 span **3 个 / 2 行**（L2309 ×1、L2315 ×2）；剔除 `>` 行与 `〔…〕` 后与 `PROJECT-STATE.md` 505–558 **非空行 mismatch = 0** ⇒ 该节自述为真 | ✅ 通过 |
| 5 | 备份已搬出仓库 | 备份于 **2026-10-25** 从仓库内旧目录（`.trash-<日期>/` 形式）移至**仓库外** `D:\llama-mem-backup-2026-10-25`。检测员实读：**85 个文件 / 全部 `.md` / 合计 1,707,063 B**，与台账 §2 第 3 列字节合计（1,707,063）**逐字节相等**；仓库内 md 总数 **261** = 项目自有 **3** + vendored **258**。仓库内不再有任何备份副本 ⇒ 「唯一 README」在**磁盘层面**亦成立（此前只是靠 `.gitignore` 在受控语料层面隔离） | ✅ 回退路径不变，仅前缀改为 `D:\llama-mem-backup-2026-10-25` |
| 6 | F-M3-7 修复的独立验收（检测员实跑，未采信执行者自报） | 脚本（**当时版本**）`check_m3_injection.py` **511 行 / 26,152 B / sha16 `f182c7da0eff1e98`**，`git diff --numstat` = **186 增 / 4 删，仅此一个文件**。**① 编码**：utf-8 / 干净环境 cp936 重定向 / ascii 三种跑法 **rc 全 0**；其中 cp936 输出与 utf-8 输出**逐字相同（49 行、0 个 `?`）** ⇒ `errors="replace"` 是兜底而非掩盖。**② 五行**：13 / 端到端 5 / 仅单元 8 / 不可失败 8 / `端到端红过 2 条 : I3 I4`、`仅单元红过 4 条 : I1 I2 I5 I6`，与 `M3-ACCEPT` §0 逐项相符。**③ 无硬编码**：把 C1 的 `e2e` 由 T 改 U 后，输出当场变 **4/9** 并报 `CENSUS-LAYERED` RED ⇒ 5/8 是算出来的。**④ 自建 4 个负对照**（键名不符 / e2e=U 缺 why / 删 `io_criteria.I5` / `I3.e2e` 改 U）**全部 rc=1** 且报错指向真因。**⑤ 退出码**：缺参=2、非法 `--mode`=2、文件不存在=3、坏 JSON=3，rc=3 走 stderr 明写「这不是判据红」。**⑥ 冻结件**：三份 M3 JSON `git status` 为空（未动）；README `85f6a7d38b85bb49` / PROGRESS `a83200862e45bec5` / 本台账 `9a2c9f72dc8a034c` 与记录一致。**⑦ 回归**：`--mode inject/unit/citations` 与 HEAD 基线（`git show HEAD:` 取回的 329 行旧版）**输出逐字相同、rc 相同** | ✅ **放行**（1 条建议见附录 E.E.7） |
| 7 | F-M3-7 收尾终核（检测员实跑五项） | 脚本（**当时版本**）`check_m3_injection.py` **543 行 / 27,914 B / sha16 `4cf4efc96464a884`**；`PROGRESS` **183,793 B / `34b7a35b1abb0468`**、README 未动 `85f6a7d38b85bb49`。**S1**：缺 `--unit-falsifiers` ⇒ **rc=2**（文案点名 #S1）；传了文件但 `cases=[]` 或 case 无名 ⇒ **rc=1**「第三来源为空, 第五行无法三源核对」。**S2**：`PYTHONIOENCODING=ascii` 下 **rc=0**，stderr 警告**纯 ASCII（非 ASCII 字节 0）**、完整可读（消息中那个 `?` 是引号内的说明字符，非乱码）。**S3**：路径不存在 ⇒ **rc=2**（原文「这是用法错(路径写错), 既不是判据红也不是环境错」）；指向目录 ⇒ **rc=3**（`PermissionError` 归环境错）。**文档**：`§12.1` L1621 状态已改**已闭**；L1633 同步为「原报『当前未闭』，已于 2026-10-25 关闭」（历史口径，非矛盾）；L1634–1639 三条真因 + 退出码语义 + 「这条 finding 的报告本身曾是假线索」**齐备**；全文 F-M3-7 仅 3 处提及，无残留未闭表述。**锚点**：§16 副本 **L2074**（222 行 / mismatch 0）、§17 副本 **L2311–L2372**（62 行 / 剔除标注后 mismatch 0）、§17.6 **L2373** | ✅ **结案** |
| 8 | 收尾后两条建议的实做（**只改脚本，文档零改动**） | 脚本现 **562 行 / 28,821 B / sha16 `23b6254c93b5afc4`**（上一版 `4cf4efc96464a884`），`git diff --numstat` = **243 增 / 10 删，仅此一个 .py，json 改动 0**；`PROGRESS` 仍 `34b7a35b1abb0468` / 183,793 B、`README` 仍 `85f6a7d38b85bb49` ⇒ **文档零改动**，§16 副本仍 **L2074**、§17 副本仍 **L2311**（按行内容逐字核，非仅看行号）。**① 用法错统一走 stderr**：`file=sys.stderr` 现 **6 处**、`class UsageError` 在；缺参 / 路径不存在 / 目录输入三类全改走 stderr 且 **rc=2**。**② 目录输入归 rc=2**（原文「输入是目录，不是文件」），不再落 `PermissionError` 的环境错分支。**③ 三模式回归 = 换流不换内容**（我按非空行多重集逐行复比）：`citations` **零行搬动**、out 24 行完全相同；`unit` **只搬 1 条非空行**（`RED: UNIT: no 'field' key…`）；`inject` **只搬 3 条非空行**（`RED: SINGLE-FACTOR…` / `RED: CHECKS…` / `RED: TARGET…`）。三者 **new.out 无一行是 old.out 里没有的（0 虚构）、搬走行 100% 出现在 new.err（0 丢失）**，rc 全不变（0 / 1 / 1）⇒ 是预期变化，**不是回归**。**④ 坏 JSON 标签**：由兜底「内部错（非判据红）」单列 `ValueError` → **「数据错（坏 JSON 或结构不符）」**，**rc 仍 3** | ✅ 通过（1 条措辞建议） |
| 9 | `compare.py` 修复的独立验收（检测员在 `D:/compare-verify/` 自建副本实跑，未采信执行者自报） | 文件 **11,555 B / 231 行 / sha16 `9ecf7e74c97f52c6`**（改前 5,381 B / `9272d3c8ebb96626`）。① 正例 `--chat tools/chat.py`：**rc=0**、**stderr 0 字节**、stdout 末行 `CHAT-LEASE-COMPARE: PASS`；② 负对照 N1 删一处 `leases.reset(`：**rc=1**，明细表指名「`leases.reset(` 期望 4 实际 3 MISMATCH」并附 `why` 原文；③ 负对照 N3 只删 `site="..."`：**rc=1**（`leases.reset( 均带 site=` 判据红）；④ **未预见负对照 N2**：只把站点名改成 `m1.mount.beforeLoad`（计数与站点数均不变）⇒ **rc=0 放行**，见「判据缺口」；⑤ 负对照 N4 仅在注释里写一句 `safe_reset_all` ⇒ **rc=1**（正则扫原始文本，含注释/字符串）；⑥ 写产物失败（`--out` 指向目录）⇒ stderr `WARN … rc 不受影响`、**rc 仍 0**；⑦ `--chat` 指向目录 ⇒ rc=2 + `USAGE-ERROR`。**判据缺口（两条，均不阻塞）**：(a) 站点**名字**未钉死 —— `why` 里写着四个站点名，但代码只比「出现次数 == 带 site= 的次数」，改站点名不会被发现；(b) 站点不变量自身用 `total` 当期望值（`expected: total`），所以当 `leases.reset(` 计数判据已经红掉时，它反而恒绿（N1 里显示「期望 3 实际 3 OK」），无法独立佐证「四个站」 | **通过**（rc 语义、stderr 纪律、明细指名、WARN 不改 rc 四项实测成立）；缺口 (a)(b) 建议登记为后续小修，不重启本轮 |

**脚本版本链（三行各记各的验收事实，不互相覆盖）**：`f182c7da0eff1e98`（第 6 行，511 行）→ `4cf4efc96464a884`（第 7 行，543 行）→ **`23b6254c93b5afc4`（第 8 行，562 行，当前实物）**。凡引用「脚本 sha16」而未注明行号的，一律以最后一条为准。

**为什么 sha16 只能写在这张表里**：把某个文件的 sha256 写进该文件自身，写入动作立刻改变哈希 ⇒ 自指悖论。因此正文按 lead 的改法只写「本节行号以 2026-10-25 冻结版为准；若 grep 落空，按节标题定位」，而**冻结快照的 sha16 由本表承担**。

---

## 附录 D 本台账自身的规矩

1. 本文件是**只读盘点**的产物，未对任何既有文档做改动；唯一写入路径是 `docs/_work/CONSOLIDATION-LEDGER.md`。
2. 分类与动作是**建议**，执行权在 lead；本台账不执行删除。
3. 凡标 `DELETE-AFTER-BACKUP` 的行，理由栏必须给出「为什么无独立内容」，不允许只写「看着像旧的」——
   这是 `kvmem/m2_visibility/INDEX.md` §6 定的规矩（「判『已被取代』必须说清哪份在哪些结论上覆盖了它」）。
4. 字节数与 mtime 为实测值；若被删改则本行结论自动过期，须重新盘点。

---

## 附录 E · F-M3-7 规格书（lead 派单称「附录 D」，D 已被「本台账自身的规矩」占用，顺延为 E）

> 出题：lead（2026-10-25）。答题：检测员。性质：**只读根因定位 + 规格书**，未改任何脚本/产物/声明/README/PROGRESS。
> 被测工具：`kvmem/m2_visibility/mine/inspector/check_m3_injection.py`（329 行 / 15,803 B，**未被合并删除**，`.py` 不在合并范围）。
> 全部结论由我实跑得出，未采信任何转述。

### E.1 结论先行：F-M3-7 的原始描述**不复现**，真正未闭的是另外两件事

原始描述（`M3-ACCEPT.md` §4 原文）：「`check_m3_injection.py --mode census` 不把 declarations 按 key 连进产物（并排成列，声明列 `-`，rc=1）」。
**实测三条都不成立，或成立原因与描述不同**：

| 原描述 | 实测 | 判定 |
|---|---|---|
| 不按 key 连进产物 | 三份产物的 `judgement.criterion_status` 键集与 `criteria` **各 15 条、交集 15、双向孤儿 0**；表里 `unit`/`e2e` 两列**全部有值**，无一个 `-` | **不复现**（join 早已接上） |
| 声明列全是 `-` | 同上：`-` 只在「声明里根本没这条」时才出现，而 15 条全命中 | **不复现** |
| rc=1 | **确实 rc=1**，但栈在 `L209` `UnicodeEncodeError: 'gbk' codec can't encode character '\u21d2'` —— 是**中文控制台编码崩溃**，不是判据红 | 复现，但**根因不是 join** |

**真正未闭的两件**：
1. **输出编码不可移植**：cp936（中文 Windows 默认）控制台下，最后两条 `print` 抛异常 ⇒ 进程被 Python 用 rc=1 终止，**PASS/FAIL 汇总行根本没打印**（异常发生在 `L320` 那行之前）。
2. **`M3-ACCEPT` §0 的第五行（`I1..I6` 分两档）根本没有输出**：`mode_census`（L105–L212）**通篇没有一处读 `io_criteria`**；declarations 里 `io_criteria` 六个键（I1..I6 的 unit/e2e/evidence）**从未被使用**。

**旁证（finding 是旧的，修过但没更新）**：L143 有一行注释「must be re-fetched per row: the rows loop leaves dv pointing at the LAST claim」——典型的修 bug 留痕；且该脚本自入库只有一次提交（`d6ff922`），无法用 git 定日期。

### E.2 复现记录（原始输出摘录）

命令（`cd D:\llama-mem`）：
```
python kvmem/m2_visibility/mine/inspector/check_m3_injection.py --mode census \
  --artifact   kvmem/m2_visibility/m3/run_m3_lifecycle_50_v4.json \
  --declarations kvmem/m2_visibility/m3/run_m3_criterion_declarations.json \
  --unit-falsifiers kvmem/m2_visibility/m3/run_m3_unit_falsifiers.json
```

| 跑法 | rc | 现象 |
|---|---:|---|
| 默认控制台（cp936） | **1** | 表格与 4 行统计**已打印**（中文显示为乱码，如「˵˱֤」）；随后 `stderr` 出 `UnicodeEncodeError: 'gbk' codec can't encode character '\u21d2' in position 0`；**没有** `INJECTION/CENSUS:` 汇总行 |
| `PYTHONIOENCODING=utf-8` | **0** | 完整打印，末行 `INJECTION/CENSUS: PASS`；8 条 `note:` 全为 `declared … == derived` |
| 不传 `--declarations` | **1** | 17 条 `RED:`（1 条「no --declarations given」+ 15 条「has neither unit nor e2e declaration」+ 1 条 `DECLARED vs DERIVED: independent_criteria=13 vs 15`）⇒ **这条守卫是对的** |

UTF-8 下的关键四行（与 `M3-ACCEPT` §0 **逐项相符**）：
```
judged rows                          : 15
judged distinct claims               : 13
端到端被验证 (e2e=T)                 : 5  ['C1_cells_detach_equal','C4_no_3_round_non_decreasing_rise','L1_holders_zero','L2_ranges_zero','L3_any_leased_false']
仅单元被验证 (unit=T, e2e=U)         : 8  ['C3_block_cells_moved','L4_reset_clears_tokens','S1_pos_max_detach_equal','S2_pos_max_within_bound','S3_cells_attach_minus_before_equals_moved','S3_pos_at_attach_equals_attach_pos_hi_minus_1','T1_needle_in_every_answer','T2_answers_identical_to_round1']
not_falsifiable_e2e (e2e!=T)         : 8
```
第五行（I1..I6）**缺席** —— 这就是 §0 五行的缺口。

### E.3 逐键 diff（产物 `criterion_status` ↔ 声明 `criteria`）

| 产物 | criterion_status | criteria | 交集 | 只在产物 | 只在声明 |
|---|---:|---:|---:|---:|---:|
| `run_m3_lifecycle_50_v4.json` | 15 | 15 | **15** | **0** | **0** |
| `run_m3_lifecycle_50_v2.json` | 15 | 15 | **15** | **0** | **0** |
| `run_m3_lifecycle_3rounds.json` | 15 | 15 | **15** | **0** | **0** |

（要求举例 ≥5 条的两侧孤儿：**两侧都是 0 条，无例可举** —— 这本身就是结论。）
条目形态正常：`"S1_pos_max_detach_equal": {"value":"T","falsified_by":["U-S1"]}` ⇒ 取值路径 `v.get("value")` 与 L117 的实现一致，不存在「条目不是 dict / value 不在预期位置」的问题。

### E.4 `alias_of` / `restates` 路径**不是死代码**（但存在双真相）

`criteria` 每条的键集合 = `unit` / `e2e` / `why` / `unit_evidence` / `alias_of` / `restates`；两条命中：
`C2_cells_attach_minus_before_equals_moved.alias_of = S3_cells_attach_minus_before_equals_moved`、`C5_last_equals_first.restates = C1_cells_detach_equal`。
⇒ L128 / L130 **会触发**，实测输出 `alias 1 / restates 1 / distinct 13`，与 `counting_rule.judged_keys=15`、`distinct_claims=13` 一致。**不会算成 15**。

但确有隐患：同一事实**同时写在两处** —— `counting_rule.aliases/restatements` 与 `criteria[*].alias_of/restates`；工具**只读后者**，从不读 `counting_rule`。两处一旦漂移，census 不会红 ⇒ 这是本规格书要补的一道闸门（N5）。

### E.5 规格书

**允许改的文件（仅 1 个）**：`kvmem/m2_visibility/mine/inspector/check_m3_injection.py`。
**不许改**：任何 `run_*.json` 产物、`run_m3_criterion_declarations.json`（冻结声明）、`M3-PREREG.md` / `M3-ACCEPT.md`、`README.md` / `PROGRESS-AND-ROADMAP.md`。
**若执行者认为必须改声明文件或产物才能达标 ⇒ 停下报 lead 批准**（那些是冻结判据与冻结产物，改一个字节就要重开一轮验收）。

**期望行为（逐条，可机械判定）**

| # | 要求 | 判定方式 |
|---|---|---|
| E1 | **编码可移植**：cp936 控制台、不设 `PYTHONIOENCODING` 时，census 必须 **rc=0**、无 traceback、中文正常或至少不乱码到不可读 | 裸 `python …` 跑一次 |
| E2 | **五行齐**：新增 `I1..I6` 段，从 `declarations.io_criteria` 读，打印「端到端红过 **2** 条 : I3 I4」「仅单元红过 **4** 条 : I1 I2 I5 I6」，与 `M3-ACCEPT` §0 第五行逐字对齐 | 输出含这两行 |
| E3 | **三方交叉核对**：五行必须由 `criteria` + `io_criteria` **机械推导**，并与 ①产物 `judgement.criterion_tally` ②`declarations.layered_sentence`（`judged` + `invalid_round_rules`）比对；任一不一致 ⇒ `RED` | 篡改声明后必须红（见 N2/N5） |
| E4 | **退出码语义分离**：`0`=PASS；`1`=`problems` 非空（判据红）；`2`=用法错；**`3`=环境/编码错**。编码错**不得**被读成判据红 | 人为制造编码错，看 rc=3 而非 1 |
| E5 | **不硬编码**：脚本里不得出现 `13`/`5`/`8`/`2`/`4` 与具体判据名的组合常量表；全部从数据算 | 代码评审 + 改声明应改变输出 |

**负对照（必须设计并实跑，本项目纪律：判据必须能红）**

| # | 注入 | 期望 |
|---|---|---|
| N1 | 临时副本里删掉 `io_criteria.I5` | **rc≠0**，RED 指明「I1..I6 只有 5 条」 |
| N2 | 把 `io_criteria.I3.e2e` 由 `T` 改成 `U`（与 `layered_sentence.invalid_round_rules.red_e2e` 矛盾） | **rc≠0**，RED 报「声明自相矛盾」 |
| N3 | 把 `criteria.C1_cells_detach_equal` 改名（键名对不上） | **rc≠0**（**现状已如此，作为回归基线**，我已在临时副本实测：`RED: … has neither unit nor e2e declaration`） |
| N4 | 删掉 `criteria.C3_block_cells_moved.why`（e2e=U 无理由） | **rc≠0**（**现状已如此**，实测 `RED: … is e2e=U without a reason`） |
| N5 | 让 `counting_rule.aliases` 与 `criteria.C2.alias_of` 写成不同目标 | **rc≠0**，RED 报双真相漂移（**这是新增闸门**） |
| N6 | 在 cp936 控制台、不设环境变量直接跑 | **rc=0** 且五行齐全（**这是新增闸门**；N6 的期望是"不许红"） |

> N3 / N4 的意义：证明「闸门本来就咬人」，改完必须**仍然**咬人 —— 属于回归，不许退化成静默 `-`。
> N1 / N2 / N5 属于新增能力，必须先于功能实现写好，否则等于"先有结论后找证据"。

**验收判据（执行者要交的证据清单，逐条打勾）**

1. 命令 A：`PYTHONIOENCODING=utf-8 python <脚本> --mode census --artifact …v4.json --declarations … --unit-falsifiers …` ⇒ **rc=0**，输出含 5 行关键字（`judged distinct claims` / `端到端被验证` / `仅单元被验证` / `not_falsifiable_e2e` / `端到端红过`）。
2. 命令 B：同样的命令**不设** `PYTHONIOENCODING`（裸 `python`）⇒ **rc=0**，**无 traceback**。
3. 命令 C：对 `_v2` 与 `_3rounds` 两份产物各跑一次 ⇒ **rc=0**（键集同为 15/15，不应有差异）。
4. N1–N6 各跑一次，交 **命令原文 + rc + 关键 RED 行**；N1/N2/N3/N4/N5 必须 rc≠0，N6 必须 rc=0。
5. `git diff --numstat` **只出现 1 个文件**、且**不含任何 `.json`**（证明没碰冻结产物）；改动文件的行数增减一并报。
6. 交回脚本**改前/改后 sha16 + 字节 + 行数**，以及每个负对照的临时副本路径（临时文件不得留在仓库内）。

### E.6 风险判断

**（1）当前 rc=1 是"错得刚好能被发现"还是"只是输出难看"？**
——**都不是，是第三种情况：异常冒充判据红。**
证据：`main()` 的 `return 0 if not problems else 1`（L325）在 UTF-8 下走通并返回 **0（PASS）**；而 cp936 下**根本走不到 L325**，栈停在 L209，进程被 Python 以 rc=1 终止。两者**退出码相同、含义相反**。
后果：任何按 rc 判定的流水线会把"环境炸了"读成"判据没通过"；反过来，只解析 stdout 里 `INJECTION/CENSUS: PASS` 的调用方在异常时**什么都读不到**，容易当成"跳过"。所以这不是"接上 join"能解决的，也不是"修个中文乱码"，而是 **E4（退出码语义分离）必须一并做掉**，否则 F-M3-7 关掉之后同类问题会以另一种形式复发。

**（2）会不会碰到冻结判据？**
——**不会。** 冻结的是 `M3-PREREG.md` 的判据语义与 `run_m3_criterion_declarations.json` 的数据；脚本是**读数器**，不是判据本身。本次改动只涉及"怎么读、怎么打印、怎么退出"。
**唯一红线**：不许为了凑出 §0 那五行去改 `io_criteria`，也不许在脚本里硬编码 `13/5/8/8/2/4`。判据要求的是"机械得出"，不是"打印得漂亮"—— E3 / E5 就是这道防线。
**次生风险**：`run_m3_lifecycle_50_v4.json` 等产物是**只读输入**，若执行者为了"跑通"去改产物里的 `criterion_tally`，等于篡改证据 —— 出现这种情况请直接驳回重做，不要协商。

### E.7 验收结果（2026-10-25，检测员独立实跑）

**判定：放行。** 无阻塞项。逐条证据见「验收记录」第 6 行。

| 检查项 | 结果 | 证据 |
|---|---|---|
| 编码可移植（utf-8 / cp936 重定向 / ascii） | 三次 **rc=0**，stderr 空 | cp936 与 utf-8 输出 **49 行逐字相同、0 个 `?`** |
| `errors="replace"` 是兜底还是掩盖 | **是兜底**：目标平台 cp936 下替换字符数为 **0**，内容零损失 | 解码比对而非肉眼看 |
| 五行是否抄进代码 | **不是**：改 `C1.e2e` 后 5/8 变 4/9 且 `CENSUS-LAYERED` 当场红 | M5 负对照 |
| 自建负对照 4 个 | 全 **rc=1**、报错指向真因 | M1 键名 / M2 缺 why / M3 删 I5 / M4 改 I3.e2e |
| rc=2 / rc=3 可达且不混淆 | 缺参与非法 mode=**2**；文件不存在与坏 JSON=**3**（stderr 明写「不是判据红」） | 四组实跑 |
| 冻结文件未动 | 三份 M3 JSON `git status` **为空**；README/PROGRESS/台账 sha16 与记录一致 | 逐个 `git status --porcelain` |
| 旧三模式回归 | `inject`/`unit`/`citations` 与 HEAD 329 行旧版**输出逐字相同、rc 相同** | 取 HEAD 版本作基线对跑 |

**唯一建议（非阻塞）**：`--mode census` **不传 `--unit-falsifiers` 时仍 rc=0 PASS**，第三来源（`invalid_reasons` 前缀）被静默跳过，note 只写「与 layered_sentence 逐条一致」，读起来与传了参数时几乎无异。建议：census 模式下把 `--unit-falsifiers` 列为必需（rc=2），或至少追加一条 note「**未提供 --unit-falsifiers，第三来源未核**」。这与本项目「判据必须能红、降级必须留痕」的纪律一致。

---

## 附录 F · E10 降级后的候选机制、判别实验与 Stage B 插桩规格（2026-10-25，检测员）

> 来历：用户裁定「不再使用 7B 的东西，E10 全部在 14B 上重新测试」⇒ 7B 一整套证据降为史料。
> 本附录只登记**事实、候选机制、可红的判据形态**，不含结论性判断。

### F.1 事实：现有三个臂里，第 4 块的「内容」与「总 cells」三向共线

| 臂（7B，2026-10-24T22:0x） | cells_total | 第 4 块实际是什么（`layout.segments`） | 结果 |
|---|---|---|---|
| `iso_habit_bot` | **63** | `habit2`，**block_id = `habit`（已挂载 habit 块自身的副本）**，12 cells @3892-3903 | 失败 |
| `iso_dup4` | **69** | `project2`，**block_id = `project`（已挂载 project 块自身的副本）**，18 cells @3886-3903 | 通过 |
| `iso_car_back` / `iso_topgap` | **70** | `car`，**外来新内容**，19 cells | 失败 |
| `iso_dup_p3` | 69 | project 副本（顺序改为 home/habit/project） | 顺序变体 |
| `iso_dup_p2` | 63 | habit 副本（顺序同上） | 顺序变体 |

**恒等式**：三段固定 `home 21 + project 18 + habit 12 = 51`，于是 `cells_total ≡ 51 + 第4块 cells`；第 4 块体积由内容决定（habit 12 / project 18 / car 19）。
⇒ **内容与容量在现有数据里 100% 共线**，「63 失败 / 69 通过 / 70 失败」这三个读数**无法区分**二者。
⇒ 因此 `PROGRESS:457`（§4.3 #5）的读法「非单调 ⇒ 容量假说被否」**不成立**；它同样可以是「内容假说被支持」，也同样未被区分。见 §4 的 **D9**。
⇒ 顺序也未被控：`iso_dup_p2/p3` 是同构型的顺序变体，但**从未进过臂表**（PROGRESS 只在 L290/543/569/571/1172-1173 提过名字）。

### F.2 三个候选机制（**单列，互不隶属**）

| 编号 | 机制 | 一句话 | 现有读数的处境 |
|---|---|---|---|
| **M-容量** | 总 cells 顶到阈值 ⇒ 注意力预算不足、权重被摊薄 | 63/69/70 三点**不单调**，表面上被 #5 否掉；但按 F.1，**并未被真正检验** |
| **M-显著性** | 第 4 块内容显著 ⇒ 抢走本该给 home 的权重 | 与 M-容量**预测相同**，无法分开 |
| **M-可复用** | 通过与否取决于第 4 块**是不是「模型本来读得懂的内容」的副本**：69 的副本来自 A 臂 **5/5 可读**的 project；63 的副本来自 A 臂 **0/5 不可读**的 habit | **第三个候选**，与前两条正交；现有 7 个臂里唯一能读出方向差异的一条 |

> **M-可复用 的可检验形式**：它预测「69 通过**是因为**第 4 块是 project 的副本」，而不只是「恰好 69 cells」。若中性文本放到 69 档**仍然失败** ⇒ M-可复用 被支持、M-容量 被否；若中性文本 69 档通过 ⇒ M-容量 存活、M-可复用 被否。

### F.3 判别矩阵（Stage A，14B，不改引擎、不重编）

| 构型（cells / 第 4 块） | M-容量 预测 | M-显著性 预测 | M-可复用 预测 | 信息量 |
|---|---|---|---|---|
| 63 / habit 副本（已有） | 失败 | 失败 | 失败 | 零（三说同预测） |
| 69 / project 副本（已有） | 通过 | 通过 | 通过 | 零 |
| 70 / car 外来（已有） | 失败 | 失败 | 失败 | 零 |
| **69 / 中性文本 18** | **通过** | **通过** | **失败** | **高**：唯一能单独否掉 M-可复用的格子 |
| **69 / car 18** | **通过** | **失败** | 失败 | **高**：唯一能单独否掉 M-容量的格子 |
| 63 / car 12 | 失败 | 失败 | 失败 | **零**（三说同预测 ⇒ 跑赢跑输都不长知识） |
| 63 / 中性文本 12 | 失败 | 通过 | 失败 | 中（须与 69/中性 成对读） |

**排期提示（只作参考）**：若只能跑两臂，选 **69/中性** 与 **69/car**；`63/car-12` 是本批**信息量最低**的一臂。

**臂集已修订（2026-10-25，lead 采纳）**：
· `63 / car-12` **撤销**（三条机制都预测失败 ⇒ 零信息量），换成 **`69 / car-18`**（容量说该过、显著性说该挂）；
· 与 **`69 / 中性文本 18`** 配对 ⇒ 两条假说各自拿到一个判决点；
· **A6 = `63 / habit2-12` 保留**，角色改为**复现对照**：三说都预测它失败，**若它在 14B 上通过，说明换模型本身翻了这一格**，那才有信息量；
· **前置 S1–S4 单块臂**（home / project / habit / car 各自独存 × 5 问）。理由：7B 的 A 臂里 home 单块 **0/5**、habit 单块 **0/5**，而 project / car 单块 **5/5** —— **单块独存时没有竞争者**，「注意力被前几块吃掉」解释不了这一档。**若 S1（home 单块）在 14B 仍失败，注意力分配就不是原因，后面八臂全部白跑** ⇒ 这是最便宜的决定性实验。

### F.4 纪律 **34-b**（形态子条；lead 2026-10-25 裁定：**不新增编号**）

**裁定要点与两条理由（原文口径）**：
1. **属「34 的实现没做到位」，不是新轴**：`expected: total` 那条判据本身**能红**（计数不符就红），问题在子判据循环；站名只写散文那条也**能红**，只是红不到改名。两者都是 34 的实现问题。
2. **加号要付真实成本**：所有「41 条」的引用都要改成 42，而这个计数**已经漂过一次**（台账曾照抄 `INDEX.md` 写成 38 条，后更正为 41）⇒ 为一个 refinement 再动一次全员计数，风险大于收益。

**子条正文（拟，待 lead 定稿）**：
> **34-b（形态）**：判据的期望值**不得由被判对象自己派生**，也**不得只活在散文里**；每条判据必须有一个**独立于它的锚**（常量、冻结文件、或另一实现对同一量的独立计算）；锚被**改名、改值、替换**时，判据必须**掉红**。

**三个实例（本次实测）**：
1. `chat_lease/compare.py` 的「`leases.reset( 均带 site=`」把 `expected` 写成 `total`（同一次正则扫描的计数）⇒ 计数判据一红它**恒绿**（删一处 `leases.reset(` 后显示「期望 3 实际 3 OK」）。
2. 同文件把**四个站点名**只写在 `why` 的散文里；把 `m1.mount.before_load` 改成 `m1.mount.beforeLoad`（计数与站点数都不变）⇒ **rc=0 放行**。
3. `run_compare.json` 的 `all_pass` 把两组判不同源码的项布尔相与（**D8**）⇒ 一组替另一组背书。

**可发现性（我的建议，待 lead 定）**：子条正文里带**字面标记「34-b」**，这样 `grep 34-b` 直接命中，不依赖「先知道 34 有子条」。若不接受字面标记，则只能在读 34 正文时发现 —— 这就是 lead 问的那个风险点。

> **与 D8 的关系**：D8 记**产物层**「自述强于实测」；34-b 记**形态层**「判据强度被自己的实现偷偷削弱」。同族不重复。
### F.5 Stage B 最小插桩规格草案（**不实施**；只在 Stage A 指向内容/显著性时才值得付）

> **状态（2026-10-25）**：**lead 已通过**，作为 **Stage A 的条件分支备用**。Stage A 若指向**体积/容量** ⇒ 插桩**不必做**（直接走预算约束）；只有指向**内容 / 显著性 / 可复用** 才值得付「重编 + 重跑」的代价。本附录**不实施**。

**目的**：判 M-容量 与 M-显著性 谁在起作用 —— **不是**修 E10，也**不**产「份额是多少」这种描述性结论。

**打什么量**（三层，按信息量排序）：
- **B1 每层每块注意力份额**：每层每个头，softmax 后按 seq 归约 `sum_w(seq) = Σ_q Σ_{k∈seq} w[q,k]`，再按块聚合；输出 `(layer, block) → 份额` 与该层占份额第一的块。
- **B2 目标块 top-k 被选中 cell**：对 `home` 块打该层权重最大的 k=5 个 cell 的 `pos` 与权重 —— 区分「完全没看」与「看了但被摊薄」。
- **B3 每层注意力分布熵**（1 个数）：熵高 ⇒ 摊平（指向容量/预算）；熵低且集中于别块 ⇒ 被抢（指向显著性）。

**打多少才够判**：
- 层：**8 个采样层**（1 / 9 / 17 / 25 / 33 / 41 / 47 / 末层），不做全 48 层 —— 注意力模式随深度稳定，全打只是把日志放大 6 倍。
- 步：只打 **p1（prompt 结束）行 + 首个 decode 步**；E10 的失败在答案第一个 token 已可见。
- 块：4 块 + chat = 5 个 seq。
- 体积：8 层 × 2 步 × 5 块 × 2 数字 ≈ **160 个数 / run**（可读、可 diff、可进 json）。

**怎么证明仪表本身没坏（不许省）**：

| # | 自证 | 判据形态 |
|---|---|---|
| S1 | **未设 env ⇒ 行为完全不变** | 同一 prompt 的答案 sha 与不插桩版**逐字节相同**（不同即插桩改了行为） |
| S2 | **A/B 受控** | 同一 run 内「只挂 chat 的对照会话」应把 100% 份额给 chat、「挂 4 块的会话」应分摊 ⇒ 打印**既非恒真也非恒假**（沿用 7B 期「A 有 100 条 blk 行 / B 有 0 条」的做法） |
| S3 | **人为偏置必须被读出** | 用**现成**的 `LLAMA_KV_MASK_BIAS` 给某块加 +b，该块份额变化方向须与符号一致（b>0 ⇒ 份额升）。这是唯一能证明「仪表指向正确对象」的实验，**比 S2 强** |
| S4 | **漂移锚** | 插桩前后各记一次 `llama-kv-cache.cpp` sha16 + `git diff --numstat`（7B 期记的是 `20/0`、`17/0`、`391/0`、`13/0`、`31/0` 五行） |
| S5 | **交叉核对** | 份额和必须 ≈1（每层正规化自检）；被 allowed 的 cell 总数须与 scan 层报的**独立**一致（交叉核对，不是同源自洽） |

**成本口径**：实现 = 动 attention 计算路径（KQ×mask 后归约），不是 scan；固定成本 = **重编一次 llama.cpp** + **每臂重跑**。按 7B 期 `elapsed_s` 中位 **6.97 s**（n=16）估，8 臂 × 3 重复 ≈ **3 分钟计算**，钱全在重编与实现上。
**不做**：不引 torch、不改 KV 布局、不改 mask 语义（只加打印）。


### F.6 用户机制假说 · 预登记（「前两块吃掉约 80% 注意力」）

**假说（用户口述 2026-10-25，转述）**：7B 里**第 1、2 块吃掉约 80% 注意力**，第 3、4 块基本分不到；**14B 能分得更精细**。
**状态**：**预登记**（登记时点尚未检验）。**无文档出处**，见「80% 的定性」。

#### 可检验预测

| # | 预测 | 观测点 |
|---|---|---|
| P1 | **14B 上 4 块应当通过** | S1–S4 单块全过 + A2（69/project 副本）过 + A3/A4（69 档）过 |
| P2 | 若做了 Stage B：14B 的 `home` 块在关键层的**份额显著高于 7B** | B1 份额读数（跨模型比须**同 prompt、同层、同 token 位置**） |
| P3 | 单块独存时**不存在份额竞争** | S1–S4 四臂互为对照 |
| **P4a** | 若 14B **原样复现** 7B 单块档的分叉（`home`/`habit` 挂、`project`/`car` 过）⇒ **单块可读性由内容/位置决定，与模型规模无关** | S1–S4 逐臂可读率 |
| **P4b** | 单块分叉的复现**不能**推出「E10 不是注意力分配现象」；四块共处是否存在竞争损耗，须由**损耗量**单独判（见 F.7） | S 档与 A 档的「单块 / 共处 / 损耗」三数 |

> **P4 的意义与收紧（lead 2026-10-25 裁定）**：单块档是**按内容分叉**（home 0/5、habit 0/5 挂；project 5/5、car 5/5 过），不是「全挂」。**P4a 成立且强**：这一档的可读性由内容/位置决定、与规模无关。
> **但推论必须收紧（我原稿写错了，此处更正）**：单块可读性由内容决定，与「四块共处时是否存在竞争损耗」是**两个可以同时为真的命题** —— 某个块内容上极难取，**不排除**别的块在场时还有额外的抢注意力损耗。用单块分叉去否掉「四块竞争」等于**把两个效应当成一个**。故拆为 P4a / P4b 两条独立预测。
#### 已知反例（**必须随预登记一起引**，否则会被读成已确认）

- **7B 的 A 臂里 `home` 单块 0/5、`habit` 单块 0/5，而 `project` 单块 5/5、`car` 单块 5/5。**
- 单块独存时**没有任何竞争者** ⇒「注意力被前两块吃掉」**解释不了单块失败**，更解释不了**同一档里 home 挂而 project 过**的分叉。
- ⇒ 本假说最多解释**多块档**（B/C 臂）的内部差异，**不能**解释单块档。这一条也是 lead 把 S1–S4 前置的全部理由。

#### 「80%」的定性（**不许被引用成读数**）

- **是估计值，不是读数。** `PROGRESS` **§8.10（L1115-1121）** 与 **§8 总表第 25 行（L376）** 都把「上下文-注意力占比」标为 **UNKNOWN**：项目自有文档 grep `占比` / `注意力占比` **0 命中**。
- 我实核：`PROGRESS` / `README` / 本台账 grep `80%` **0 命中**；备份 `HANDOFF.md` / `PROJECT-STATE.md` / `kvmem/m2_visibility/*.md` grep `80%` 亦 **0 命中**。
- ⇒ 将来任何「文档记载约 80%」的写法**都是伪造**；正确写法只能是「**用户估计约 80%（未经测量）**」。

#### 判定表（数据回来后照此裁，不许事后改口径）

| 观测 | 裁决 | 备注 |
|---|---|---|
| S1–S4 全过 + A2 过 + A3/A4 过 | **支持** | 14B 确实分得更细；E10 可能不复现 |
| **S1（home 单块）在 14B 仍失败** | **否掉「注意力被抢」这一支** | 无竞争者仍失败 ⇒ 单块失败另有原因（存储 / 几何 / 生成侧）；后续八臂白跑 |
| S1 过、A2 挂 | 方向对、对象错 | 须引入第 4 候选（副本类型 / 位置） |
| 全过（含 A2/A3/A4） | 强支持，且 **E10 不复现** | `§13.9` 第 1 项须**整条重写**而非填基线（lead 已预判） |

**冻结声明**：本预登记一旦用于裁决，任何改动须在本节追加条目并标**方向（放松 / 收紧 / 改对象）**与 **invalidates**（哪份产物锚失效）。

### F.7 定义建议（**待用户裁定**）：把 E10 的观测量定义成「**每块损耗**」而不是四块的绝对可读率

> 提出人：lead（2026-10-25），检测员记录并加前置条件与反例。**本建议不动 `§13.9`**（那是判据层，须用户拍）。

**定义（原文）**：**每块损耗 ≡ 该块单块独存可读率 − 该块四块共处可读率**（同一块、同一批问题，分子分母都写清）；某块单块即不可读则记 `N/A`，**不填 0**、不参与平均。

**为什么它有道理**：绝对可读率把**内在难度**与**竞争损耗**混在一起；相减之后，剩下的量才是「竞争」本身。

#### 我的评估（lead 要求「先评、别急着采纳」）

**方向我赞成，但不建议用它替换绝对口径，只建议并列。** 三条理由：

1. **地板效应会让主角块整格变 N/A**。7B 的 A 臂里 `home` 单块 **0/5**、`habit` 单块 **0/5** ⇒ 按定义这两块的损耗**记 N/A**，而它们恰恰是 E10 的主角；`project` / `car` 单块 5/5 才有损耗可算。**一个只在配角块上可算的指标，不能当主判据。**
2. **`n=5` 时损耗的最小分辨率 = 20 个百分点**。`loss = k1/5 − k2/5`，任何差都是 20% 的整数倍 ⇒ 5/5 与 4/5 的损耗（20%）与「真无竞争」不可区分。**要么把每格 `n` 提到 ≥10，要么改报「同题配对差的计数」（保留 k1−k2 的整数形态）。**
3. **两个条件必须装置同构**：同 prompt、同 `n`、同 `seed`、同 `n_predict`、同「可读」判定者（`P.FULL[block_id].fact` 命中）。任一不同，损耗里就混进装置差，而不是竞争。

#### 若采纳，四条前置条件（缺一条则损耗不可解释）

| # | 前置 | 说明 |
|---|---|---|
| 1 | 单块与共处**同题同 n** | 逐题配对，报 `k1/n − k2/n` 与配对数 |
| 2 | 单块率 ∈ (0, 100%) 才可算 | 地板（0）与天花板（100%）一律记 `N/A`：地板块算出的「损耗 0」与「真无竞争」不可区分 |
| 3 | 「可读」判定冻结 | 与 M2/M5 同一判定（答案含 `P.FULL[block_id].fact`），不许中途换判定者 |
| 4 | 报「单块 / 共处 / 损耗」三数 | 已同步给执行者；**单块即不可读的格子标 `N/A` 不填 0** |

#### 与 `§13.9` 的关系（**不擅动**）

- `§13.9` 第 1 项现在写「4 块布局 **4/4 可读**」= **绝对口径**（产品口径：能不能用）。损耗 = **机制口径**（竞争有多大）。**两者不是同一件事**：`4/4` 可在**有损耗**时依然成立（单块 5/5、共处 4/5 ⇒ 损耗 20%，但 4/4 仍达标）。
- 因此建议：**双报** —— 保留 `4/4` 作产品口径，另加「每块损耗」作机制口径；**主判据是否改口径，属判据变更，须用户裁定**（纪律 26/28：标方向 = 改对象）。
- **本轮未改 `§13.9` 任何一行。**

#### 先行检验：这条口径在 7B 数据上**完全不可用**（进一步说明必须等 14B 单块档）

| 块 | 7B 单块（A 臂） | 7B 四块共处（C 臂） | 可算损耗？ |
|---|---|---|---|
| `home` | **0/5** | 挂 | **N/A**（地板） |
| `habit` | **0/5** | 过（C 恒 1/4，只有它过） | **N/A**（地板） |
| `project` | 5/5 | 文字未给逐块值 | 缺共处值 ⇒ 不可算 |
| `car` | 5/5 | 文字未给逐块值 | 缺共处值 ⇒ 不可算 |

⇒ **7B 的四个块没有一块能算出损耗**（两块地板、两块缺共处逐块值）。这条口径**只能等 14B 的 S1–S4 与 A 档跑完**才有第一组真实数字。

---

## 附录 G · 装置与产物核查（2026-10-25，检测员；lead 放行七条 + 预登记一条）

## ★ **计数枚举给出的是下界，不是全集**（lead 2026-10-25 立）

> **靠计数枚举，只能证明「这些位置有某记号」，不能证明「该记号覆盖了全部该覆盖的位置」。计数给出的是下界，不是全集。**

**现场（M4-C 的核心缺口就是这样来的）**：L126 记「四站全部改完」+ `leases.reset(` **4** 处 —— **四个站点是按这个调用的计数选出来的，不是按 §5.7 的语义追出来的**。
**⇒ 按计数选站，只会找到「有那个记号」的地方；没有那个记号的地方永远找不到。** 恢复路径（`cmd_restore` L353–372）就是这样整条漏掉的 —— 它不用 `leases.reset(`，所以计数里根本没有它。

**⇒ 与「`grep` 能证有不能证无」是一对**：那条管**查一个词**，这条管**用计数当普查**。**两条合起来**：任何「全部 / 四站 / 覆盖」的说法都不能拿计数当依据。
**⇒ 正确的普查顺序**：**先按语义列出应覆盖的位置（从文档/契约出发），再逐条到代码里落地**；计数只作**交叉核对**，不作**发现手段**。

## ★ 判据退化的**两个维度**：工况与取值（lead 2026-10-25 补第二维）

| 维度 | 退化表现 | 现场 |
|---|---|---|
| **工况** | 在多小的规模下永不触发 | 「3–5 块时预算判据永不触发」（域外判据那一族） |
| **取值** | 在什么取值上表达式恒真 | **`2n != n` 在 `n == 0` 时恒真** ⇒ 翻倍判据对空块**红是空的** |

**⇒ 同一个病的两个入口。合起来的要求**：**每条判据要在两个维度的退化点上各问一次 —— 「在多小的工况下失效」「在什么取值上恒真」。**
**⇒ 为什么必须问两次**：**工况维度管「会不会发生」，取值维度管「发生了能不能判」。** 一个判据可以**工况可达**却**取值退化**（例如某块恰好为空），此时它会**在真实数据上给出一个没有信息的绿**。
## ★ 承重断言的**选址**：见证者不能在被删对象**内部**（lead 2026-10-25 立）

> **承重断言必须写在被删对象的可执行范围之外。一条检查只有在其守护的那行仍存在时才会运行；它无法见证自己的缺席。**
**判法**：要证明「删掉 X 会出问题」，**见证者不能是 X 内部的检查**，必须是 X **下游**或**外部**的断言。

**现场**：`GuardedLeases.reset` **内部**已有断言（`chat_lease.py` 331–335 一带），看起来很承重；但 **删掉站点调用 `leases.reset(...)` 后，它根本不执行** ⇒ **它对「站点是否被调用」零信息**。

**⇒ 与「没有 X」三半的关系（lead 归纳为四半，正交）**：
| 半 | 管什么 | 管的是流程的哪一段 |
|---|---|---|
| ① 版本 / 范围 / 口径 | 「没有 X」能站多远 | **措辞** |
| ② `grep` 不能证「无」 | 怎么去查「没有」 | **核查手段** |
| ③ 枚举先于判定 + 找对层级 | 查之前先确认**对象** | **对象** |
| ④ **见证者不能在被删对象内部** | 判据该**写在哪** | **选址** |
**⇒ 四半合起来才覆盖「一条判据从选址到措辞到核查」的全过程。**

**⚠ 选址还有一个隐蔽变体（我加）**：见证者**在范围内但不在时序上** —— 例如把 post-condition 写在 `repos_local` **之前**（那时数值还没变，永远绿）。**既不在 X 内部、也不在 X 下游，而是在 X 之前 ⇒ 同样是零信息。**
## ★ **`grep` 能证「有」，不能证「无」**（lead 2026-10-25 立；同日第三次同类错后收成一条）

> **字面命中 0 只说明「这些字不在这里」，不说明「这个意思不在这里」。**
> **反向断言（「没有 X」）必须用语义核，不能用字面检索。**

**现场**：lead grep `必要条件|充分条件` ⇒ 全文**只命中 L1756 一处** ⇒ 准备判「§5.7 没这个意思、L1756 是孤立表述」。
**真相**：§5.7 **L804** 用白话写了同一件事 ——「**静态计数到位 ≠ 真实承重**」。**意思在，字不在。**

**⇒ 同日三次同类错，形状完全相同**：
| 错法 | 检索方式 | 结论 | 真相 |
|---|---|---|---|
| 顶层取字段 `undefined` | 取键 | 「第 3 项没做」 | 字段在下一层 |
| `必要条件` 命中 0 | 字面 | 「§5.7 没这个意思」 | 用白话写着 |
| 预期文件名不存在 | 文件名 | 「未做」 | 产物在别的名下 |
**⇒ 都是「检索工具的盲区」被当成了「对象的不存在」。**

**⇒ 与「没有 X」三半合流**：**在哪个版本 / 覆盖多大范围 / X 按什么口径算** —— 现在加第四半：**用什么手段核的**。字面检索只能支持「有」，要支持「无」必须换手段（语义核、逐条枚举、跨层取键）。

## ★ 一个文件不能包含关于**自身**的事实断言（lead 2026-10-25 立；**结构性恒假**）

> **一个文件不能包含关于自身内容的事实断言。** 想记「我是哪一版」，只能由**外部**记录，或由**生成该文件的程序**写进日志。
**判法**：看到「本文件 = 某 sha」，先问「**写这句话的时候，这个 sha 还成立吗？**」——**答案永远是不。**

**现场**：`RESULTS-RED.md` §22.3 曾写「本文件自身 = 32,018 B / `ac8b815e7061e6e5`」。**写这一节这个动作本身就改变了文件** ⇒ **写完那一瞬间就已错，且永远不可能自洽**；**没有任何更新频率能救。**
**⇒ 与「两次→三次」的区别**：那个**会**过期（可用「逐次列出」化解），这个**必然**过期（只能删除）。
**处置**：① §22.3 整节删除；② 若需最终读数 ⇒ 独立 `MANIFEST.json`，最后生成，**且不登记自己**。
**✅ 我已复核**：`RESULTS-RED.md` 现为 **33,456 B / `16a4174c5f940d6c`**，§22.3 已改为「本文件**不**登记自身 sha16（原节已删）」，**自身哈希断言 0 处**。

## ★ **范围词本身就是一个断言**（lead 2026-10-25 立）

| 写的词 | 它替你说的普查 |
|---|---|
| 「**全文**」 | 断言**扫过全文** |
| 「**全部**」 | 断言**枚举完整** |
| 「**第 N 次**」 | 断言**语料里只有 N 次** |
**⇒ 三个词都在替你做你未必做过的普查。拿不准就写更小的那个范围 —— 写小了只是不全，写大了就是假。**
**现场**：报告称「全文无『两次/三次/四次』」，**我独立数：两次 6 / 三次 2 / 四次 1** —— **交付物（L172）干净，但范围词写宽了一层**（核的是一节，写的是全文）。
## ★ **结构计数必须同步改；观测计数不进正文**（lead 2026-10-25 立，两条不同的规矩）

| 类型 | 例子 | 规矩 |
|---|---|---|
| **结构计数** | 判据几条、文档改几处、清单几项 | **必须同步改**（结构变了，文字必须跟） |
| **观测计数** | 测了几次、跑了几轮、被试几个 | **不进正文**，只逐条列实例（每次带出处） |

**取代表达**：**「已测若干次，逐次如下：…」** —— **将来加一次只需追加一行，不需要改任何文字。**

**现场（lead 自犯）**：L172 稿写「**两次**实测 123.3（v2）/ 156.9（v3）」，而 v6 已给出**第三次 130.9 ms** ⇒ **落笔即过期**。
**⇒ 解释了我们之前的一次冲突**：「六条→七条」是**结构**（必须改）；「两次→三次」是**观测**（不该写进正文）。**lead 当时把观测计数当成了结构计数。**
## ★ **枚举先于判定**（lead 与检测员同日各犯一次后立）

> **判「未做」之前必须先枚举实际存在的产物集合。「我预期的文件名不存在」≠「工作没做」。**
> **判「通过」同样要取最新产物，并写明凭什么是它。**

**现场（同日三例，方向各不相同）**：
| 例 | 方向 | 实情 |
|---|---|---|
| lead 判第 4 项**未做** | 假红 | 把 `INSERT-REAL2.json` **硬编码**进脚本，看到它早于 `planner.py` 就判未做；盘上已有 v3–v6 |
| lead 判第 1 项**未做** | 假红 | 因为不存在名为 `CONTROL-2ASK.json` 的文件 —— 而对照运行**在 v4/v5/v6 的 `control_no_insert` 里** |
| **检测员报「v5 是最新」** | **假绿** | **v6 已在 05:34:04 落地**，我漏了它 —— **与 lead 同一类错，只是方向相反** |

**⇒ 两个方向的错同一个根**：**都是拿「记忆里的名字」去对「盘上的现实」**。一个漏掉存在的东西（假红），一个把已过时的东西当最新（假绿）。
**⇒ lead 2026-10-25 补半步（自犯后）：枚举之后还要找对层级。**
> **顶层取不到不等于不存在，只等于「不在顶层」。**
**现场**：读 `v8.has_think_tag_in_Q1` ⇒ `undefined` ⇒ 第一反应「第 3 项没做」；实际字段在 `control_no_insert` 下一层 —— **也正是 Q1/Q2 该在的地方**。
**⇒ 与「同名异指」成对**：那个是**同一个名字指着两个东西**，这个是**同一个东西藏在另一个位置**。**两者都会让人得出反向结论，而且都不报错。**

**⇒ 执行动作（三条，缺一不可）**：
1. **先 `readdir` 再判定**，绝不硬编码文件名；
2. **取 `mtime` 最大者**，并核对它与被判对象的先后（如 `planner.py` 的 mtime）；
3. **写明「凭什么这是最新」** —— 最好让产物自带 `provenance`（v6 已有：`planner_sha16 / planner_bytes / planner_mtime / probe_sha16 / probe_mtime / run_utc`）。
## ★ **定位不是标识**：行号会漂、文件名会撞车（lead 2026-10-25 自犯后立）

> **行号不是标识。任何跨版本的定位必须用 `sha16` + 内容锚，不能用行号。**
**为什么**：行号会**因为别处的合法改动而漂**，而漂移后的错误读数**看起来完全像真的**。
**现场（lead 自犯）**：按记忆读 **L1829** 找 M2 那行，读到的是**表头** ⇒ 第一反应「判据格空了」；**真相**是 §13.4 新增一段让整张表**下移 2 行**，M2 行现在在 **L1831**。**差一点因为一个正确编辑判了一个红。**

**同一族的第二半（lead 自犯）：文件名同样会撞车。**
**现场**：盘点脚本用 `basename` 作字典键 ⇒ `m2_planner\FIELDS.md` 与 `m14b_e10_probe\FIELDS.md` **撞成一个键**，后者覆盖前者 ⇒ 第一遍只看到「一个 FIELDS.md」。
⇒ **这是本会话第五例「同名异指」，且是立规则的人自己造的。** 上一轮刚立「跨文件**字段名**须有唯一定义」—— **规则要一并覆盖到文件路径与文件名**。

**⇒ 检测员动作**：报位置一律给 **「文件 + sha16 + 内容锚 + 行号」四件套**；行号只作**辅助**，不起定位作用。**盘点脚本一律用相对路径作键，不用 `basename`。**
## ★ 两个读数必须**机制独立**（lead 2026-10-25 补半步；检测员提规则时自己就踩了）

> **两个读数必须机制独立：不能是同一通道的两次调用，也不能是同一底层计算的两种包装。**
**判法**：问 **「若底层这一项失效，两个读数会同时错吗？」—— 会，就不是两个。**

**⇒ 检测员自犯**：我提「任何读回都要两个独立读数」的同一条消息里，举的例子就是 `pos_max` / `raw_pos_max` —— **而那正是反例**。
| 读数 | 实现 | 机制 |
|---|---|---|
| `eng.pos_max(seq)` | `kvslots.py` L135 → `kvshim_pos_max` | 位置层 |
| `P.raw_pos_max(eng,seq)` | `m2_visibility_probe.py` L189 → `kvshim_seq_pos_max_raw` | **位置层**（同一底层**不同入口**） |
⇒ **两个不同 C 入口，但读的是同一个「位置」量** ⇒ 底层若看不见 share 进来的 cell，**两个会同时错、错法一致** ⇒ **交叉验证当场失效**。
**⚠ 只证到入口不同，未证「同一次扫描」** —— 「同一底层计算的两种包装」是**合理推断【未验证】**；但**即便入口独立，两条读数仍在同一层**，按本条判法即不合格。

**三层（越往下越独立）**：
| 层 | 读数 | 独立性 |
|---|---|---|
| **位置层** | `pos_max` / `raw_pos_max` | **同一层，算一个** |
| **计数层** | `n_tokens(seq)`（`kvshim_n_tokens`） | **较独立**（数个数，不依赖位置计算） |
| **内容层** | 把区间里的 token 读出来解码，检查是否该块的字（**`kvshim_seq_tokens` 存在**） | **最独立**（读值，不读索引） |
⇒ **每个读回至少跨两层，最好含内容层。**

**三个具体读回（lead 定）**：
| 步 | 读回组合 | 单看位置永远发现不了的事 |
|---|---|---|
| `drop` 后应不可见 | `n_tokens(chat)` **减少**「区间长度」**且**内容层读不出该块的字 | —— |
| `share` 后应可见 | `n_tokens(chat)` **增加** **且**内容层能读出该块的字 | —— |
| `repos_local` 真移动 | `raw_pos_max` 差值 == `new_cells` **且** **`n_tokens` 不变** | **移动不该改变 token 个数**；若 `n_tokens` 也变了，那一步不只是「移动」，而是「掉了/多了一部分」 |
## ★ 【上游条】**要判，先有数可判**：产物必须按判据设计（lead 2026-10-25 定，排在最前）

> **产物是「跑通后顺手 print 的东西」，不是「按判据需要设计的记录」。**

**四次同类（全部在本轮）**：`across_layouts`（判据要的对照没落盘）→ `ask_pos`（v1 缺）→ `raw_len`/`stripped_len`/`n_tokens`（缺）→（第四面）`res["raw"]` 同名陷阱。
**⇒ 不是四次疏忽，是同一个设计缺陷。**

**判法（可执行）**：看一份产物，先问 **「这份产物能回答哪些判据的问题」**；答不出的判据 ⇒ **那是要补的字段，不是要重做的实验。两者成本差一个量级。**

**⇒ schema 必填（lead 2026-10-25 定，已升级两次）**：
| 类别 | 必填字段 | 为什么 |
|---|---|---|
| 询问类 | `ask_pos`（+来源）、`raw_len`、`stripped_len`、`n_tokens`（前后各一次） | 缺一即产物不合格 |
| **任何运行产物** | **`provenance{planner_sha16, probe_sha16, run_utc}`** | **「凭什么说它是最新」不再靠 `mtime` 猜，而是产物自己说** |

**⇒ 为什么排在最前**：后面那些「判据须能红」「红须先于修」「严重度序」「三层假绿」**全都建立在「有数可判」之上**。**没有落盘的读数，前面所有规矩都用不上。**

## ★ 验收状态是**四态**，不许二态（lead 2026-10-25 定）

| 状态 | 含义 | 能否算完成 |
|---|---|---|
| **通过** | 接上了，断言跑了，绿了 | 能 |
| **未通过** | 接上了，断言跑了，红了 | 不能 |
| **未接上** | 接口不存在 / 不匹配，**断言根本没跑** | **不能** |
| **未做** | 没动手 | **不能** |

**⇒ 硬规矩**：**「未接上」与「未做」都不得从清单里消失，也不得算作通过。不许用「跳过」把九项凑成八项。**
**⇒ 为什么必须四态**：二态会把「没接上」压成「未通过」（读起来像试过而失败）或压成「通过」（更糟）。**四态把「证据不存在」与「证据为负」分开** —— 这正是那座桥（E10 只验现象、不验机制）栽过的地方。

**⇒ 四态是封闭集（lead 2026-10-25 追加，自犯后）：任何第五种写法都是在偷偷放宽它。**
**现场**：lead 写「**7 通过但须修**」—— 「通过但须修」的实际意思是**未通过**，只是给它裹了一层好看的说法。**这正是四态要防的动作：把「未通过」读起来像「通过」。**
**自诊**：*我想让九项一次性都过，于是给一个错的项找了个「基本上还行」的位置。*

## ★ 判据有效性 · **定义在前**（lead 2026-10-25 定稿，四形态为例证，见 G.37 / G.48 / G.59）

> **能红 + 能绿 + 两类取值在同一批数据里都出现过。以三项缺任一条，它只是字段。**

**四形态（例证，不是四条并列的教训）**：恒真 `gen_tokens >= n_predict` · 恒假 `hit_first_ws`（`\s+` 写错） · **无实例** M2 验收第 3 条 · **恒红** L1828 字面。
**为什么定义放前面**：后来人容易把四个例子读成四条彼此无关的教训；写成一条定义，才看得见它们**是同一个失效**。

## ★ 判据对**语言**也要有定义（lead 2026-10-25 定，紧挨上一条）

> **判据写「禁止 X」时，必须同时写「什么算 X」；否则它只在写判据的人心里成立。**

**与上一条成对**：上一条讲**判据对数据要有区分力**（能红 + 能绿 + 两类取值都出现过）；本条讲**判据对语言要有定义**。
**实例（检测员自犯，2026-10-25）**：我写「正文**无任何计数**」并据此判 L1829 未通过 —— 但 v3 那个 `48%` **带字段指针**，按 lead 补丁**不算违规**。**我的判据自己没值域**（「什么算计数」没说）⇒ **它在 `110/188` 上给对结论，在 `48% + 指针` 上给错结论。**
**⇒ 与 G.37 是同一条纪律的第二次撞上**（G.37 是「判据须有值域」，针对数据；本条针对**措辞**）。
## ★ 要求判据「独立」之前，先确认**领域允许它独立**（lead 2026-10-25 立，自犯）

> **「每条判据都该有独立反证」是形式愿望。当领域结构使两条判据必然同时成立时，追求独立只能靠削弱其中一条来达成 —— 那时你得到的不是更严的判据，是更松的判据加一份好看的反证表。**

**实例（lead 自报）**：要求「S2 必须能单独红」（构造：`n_ctx` 够、`pool_bytes` 不够）。**错在**：不做淘汰 ⇒ 放不下时没有替代方案 ⇒ **任何预算越界都必然伴随拒绝义务** ⇒ `S2 红 ⇒ S6 红` 是**领域事实**，不是证据不足。**后果**：执行者为满足该要求，**把 S6 收窄成只看 `n_ctx` 一档** —— **一条判据被削弱，起因是要求本身。**
**⇒ 与「为凑案例改判据」是同一件事，只是这次凑案例的人是 lead。**

**检测员的关联自我修正（同一件事的另一半，自犯）**：我在 G.107 看到 S6 判域被收窄成 n_ctx 档时，**判它是「一个明确的口径选择，不是漏洞」** —— 那**太宽厚**。正确动作不是记录它，而是**溯源：它为什么被收窄、什么时候被收窄**。⇒ 新动作项：**当判据的实际域窄于它的名字，先问「谁把它收窄了」**。
## ★ **漂亮的绿 ≠ 强的证据**（lead 2026-10-25 立，自犯两次；与「像样的动作 ≠ 核过了」并排）

> **一条绿得越漂亮，越要先问：这个绿是用什么喂出来的？**

**实例（lead 自报，同一轮内两次）**：
1. 夸 S1m「说明规划器算出的正是我们在用的那个」—— **不成立**：`gaps={1:43,2:46}` 就是冻结几何的缝（G.111），把答案拆成「块+缝」喂回去，当然逐位复现。
2. 看到 P0 红集合为空就下强结论 —— 而 P0 的 `asserts` **只覆盖 S1/S2/S3a/S3b**，S4/S5/S6 无绿证据（G.105）。
**⇒ 与「像样的动作」那条是同一族**：那条防**把动作当核验**，这条防**把结果当证据**。**共同点：两者都不问「对象是什么」就下结论。**
**检测员的对应动作**：**读一条绿，先读它的 `asserts` 键集**（它评估了什么），**再读它的入参**（喂的是什么）。两者都读过，绿才有分量。
## ★ 判据的**触发条件必须在真实工况里能发生**（lead 2026-10-25 立；第三条关于「判据成立」的要求）

> **一条在部署规模上不可能触发的判据，不是判据，是带测试骨架的注释。** 它的「绿」与恒真不可区分，它的「红」只在人造参数下出现 ⇒ **红得再漂亮也不增加任何真实保证。**

**三条要求的分工（按层次排，勿混）**：
| # | 要求 | 管什么 |
|---|---|---|
| ① | 能红 + 能绿 + 两类取值都出现过 | **对数据**：判据在数据上有区分力 |
| ② | 写「禁止 X」须写清「什么算 X」 | **对语言**：判据的措辞有定义 |
| ③ | **触发条件必须在真实工况里能发生** | **对场景**：判据的对象真的会出现 |

**实例（本轮，M2 七条）**：S2 / S3b / S6 的红**只在夹具参数下出现**（`chat_len` 500→8,180、人造平局、`chat_len`→8,000）；而 M2 的运行点是「3–5 块 + 8,192 ctx」⇒ **这三条在本轮测不到任何东西**。
**⇒ 处置不是删，是分层**：域内四条计入验收；三条降为**契约测试**（保留红绿、作回归锁、不作通过条件）。**降级是唯一诚实的处置。**

**检测员的执行要点**：读一条红，先问「这个红是用什么参数造出来的」；若参数**在部署里不可能出现**，这条红不计入任何保证。**与「漂亮的绿」那条成对**：那条问绿喂了什么，这条问红喂了什么。
## ★ **「操作成功」≠「操作生效」**（lead 2026-10-25 立，执行者在真机上踩到）

> **返回码不算证据。每条操作须有一条读回验证。**

**实例**：`eng.pos_max(LIVE)` 对 **share 进来的 cell** 返回 **-1** ⇒ 对话末尾被算成 **0** ⇒ `repos_local(chat, +12)` **moved 0** ⇒ **四步全 ok，一步没动。**
**为什么它能骗过所有人**：**没有异常、没有失败步、标志全真**；**顺序判据对它完全失明** —— 顺序是对的，只是**没有内容**。
**它是被什么抓住的**：只是因为记了 `moved` 这个数。**⇒ 这是运气，不是结构。**

**族谱（三个方向，同一族）**：
| 条 | 防的是 |
|---|---|
| **做了个像样的动作 ≠ 核过了** | 把**动作**当核验 |
| **漂亮的绿 ≠ 强的证据** | 把**结果**当证据 |
| **操作成功 ≠ 操作生效** | 把**成功的返回**当**发生了** |
**共同点**：三者都**不问「有没有内容」就下结论**。⇒ **共同解法**：**每一步配一个读数，且读数必须是「变化量」**（`moved` / `bytes_changed` / `elapsed`），不是「返回码」。
## ★ **断言强度必须与证据强度相等**（lead 2026-10-25 立，连续两次自犯；与「像样的动作 ≠ 核过了」并列）

> **一个否定断言（「不能 X」）需要与被否定的肯定断言同等强度的证据。**

**病名（lead 自诊）**：**证据只到「我看到的是这样」，结论却写成「事情是这样」。**
| 犯 | 结论 | 实际证据 |
|---|---|---|
| 1 | 「效果断言是**零**」 | 旧版本（2,827 B）的 grep 读数 |
| 2 | 「**整段思考**消失」 | 一个**空** `` 标签 + 一次重复 |

**与「像样的动作 ≠ 核过了」并列**：那条防**「没核就说核了」**，这条防**「核了一点点就说全貌」**。

**检测员执行模板**：把结论里的**量词与强度**标出来 —— 「**没有**」「**全部**」「**不可能**」「**零**」是强度最高的四个词；**写它们之前须能给出覆盖整个域的读数**，给不出就降为「**我看到的这一份里没有**」。
**⇒ 三半齐全，「没有 X」才是一句能站住的话（lead 补第三半）**：
| # | 管什么 | 缺了会怎样 | 本轮实例 |
|---|---|---|---|
| ① | **时间范围**：在**哪个版本**上 | 「没有 X」变成对不存在版本的断言 | 「效果断言是零」← 2,827 B 旧版 |
| ② | **数量范围**：**覆盖多大范围** | 「一点没看到」被写成「全都没有」 | 「整段思考消失」← 只看了 repr |
| ③ | **指涉对象**：X 按**什么口径**算 | 同一个词两种口径，句子真假随之翻转 | 「没有未参与移动的块」← **事件口径**还是**绝对口径**，差一个结论 |
## ★ **同名字段必须有唯一定义**（lead 2026-10-25 立；同类病已四例）

> **一个字段名若出现在 ≥2 个文件里，必须有一处唯一定义（注释或 schema 的 description），且该定义必须能让人区分它和同名者的所指。**

**同类病四例（全在本轮）**：
| 字段名 | 两种所指 | 后果 |
|---|---|---|
| `pos_hi` / `target` | **最大占用位** vs **块的基点 base** | 换算 `base = pos_hi − cells + 1` 无单一持有者、无断言覆盖（G.110） |
| `base` | **无名**（每人临时算） | 没人能对它下断言 |
| `moved` | **被移动的 cell 数 45** vs **位移 12** | 差 3.75 倍（G.121） |
| `raw` | **token 流** vs **`{live_pos_max_raw, cell_count}`** | 拿它当 token 流去查就等于查错对象（G.129） |

**落地方式（lead 定，可查即可，不求全库改）**：在 `m2_planner/` 与 `m14b_e10_probe/` 各建一个 `FIELDS.md`，**只登记跨文件出现过的字段名**，每条写：字段名 / 各处的所指 / 如何区分。
**⇒ 关键在「能查」**：不是要求命名统一（那会变成大工程），而是要求**同名处有一个可查的对照**。
## ★ 三层假绿：**执行层 / 结果层 / 证据层**（lead 2026-10-25 定，三条成组）

> **步骤层的成功 ≠ 结果层的成功。四步全 ok 而答案是空串，两件事都成立过。**

| 条 | 管哪一层 | 防的假绿 | 现场样本 |
|---|---|---|---|
| **「操作成功」≠「操作生效」** | **执行层** | 步骤跑完、返回码全真，但**一步没动** | `pos_max` 对 share 进来的 cell 返回 −1 ⇒ 对话末尾算成 0 ⇒ `repos_local` **moved 0**，四步全 ok |
| **步骤层的成功 ≠ 结果层的成功** | **结果层** | 四步都生效了，但**结果没产出** | `insert_probe` v1：`answers.after` **空串（ok=false）**、四步全 ok、`blocks_undisturbed=true` —— **三件事同时成立** |
| **漂亮的绿 ≠ 强的证据** | **证据层** | 有结果，但**这份结果证明不了那条判据** | P0 红集合为空却只覆盖 S1/S2/S3a/S3b；S1m 逐位复现其实是回归锁 |

**⇒ 三层不可互相顶替**：执行层绿了不代表结果层有事，结果层有了不代表证据层够。**任何一条绿，先问它在哪一层。**

## ★ 否定性断言必须限定到**版本**（lead 2026-10-25 立，自犯后对等义务）

> **凡「代码里有 / 没有 X」必须带文件 `sha16` + `mtime`；收到这类断言先核版本。**
**检测员的表述模板**：「**该版本已不在磁盘**」—— 它把「事实」与「**对某个版本的事实**」分开：**「没有 X」永远是「在版本 V 上没有 X」。**
**现场**：lead grep `planner.py` 得「`moved` 0 处 / `readback` 0 处」，据此判「已知缺陷仍在」；我核到同一路径已是 6,989 B / `0f64475345e9ef2c`（`moved` 16、`readback` 10、读回校验齐备）⇒ **2,827 B 那版已不在磁盘**。

## ★ 「**数据是真的**」≠「**数据是推导出来的**」（lead 2026-10-25 摘出，检测员立条）

**现场**：真机 `cell_scan_after.gaps = [46, 43]` 与套件 `SPEC` 的 {1:43, 2:46} 同值 ⇒ **43/46 确有真机来源（扫出来的），不是编的**；**但它们被当「答案」喂回 planner** ⇒ **S1m 仍是回归锁，不是发现。**
⇒ **混了这两件事，就会把回归锁当发现。** 判法：**这个数是测量来的，还是从被检验对象那里抄来的？**
## ★ 判据失效的**严重度序**（lead 2026-10-25 定，与上一条成对）

> **假绿 > 假红 > 无实例 > 无判据。**

| 档 | 为什么排在这里 |
|---|---|
| **假绿** | **不会疼** —— 它让你在有缺陷的情况下宣布通过，而**没有人会去查一个已经通过的项** |
| 假红 | **会疼**，会逼你看 |
| 无实例 | 至少还能靠「永远绿」这个**异常**被察觉 |
| 无判据 | 至少有人会去写 |

**两者是一对**：上一条说「**什么样的判据有效**」，本条说「**判据失效时往哪个方向最危险**」。

## ★ 「做了一个像样的动作」≠「核过了」

> **核过的唯一证据是逐项给出对照物。**

**两次实例（均为 lead 自报）**：把「降一级」实现成**去掉一个 `#`**（做出了变换，方向反）；验收 §13.9 **只核形状**（做了自洽检查，一行内容没对）。
**共性**：**用一个看起来严的动作，覆盖了一件没真的去看的事。** 两者都不是撒谎，**但都比不做更坏 —— 因为它们产出了「已核」的印象**。

> 全部由检测员**独立复算**，未采信执行者自述。原始产物：`kvmem/m2_v1_14b/*.kvmem`、`kvmem/m2_7b/m2_v1/car.kvmem`、`runs_m14b/blocks_14b.json`、`m14b_e10_probe/out/*.json`。

### G.1 块布局实测表（逐字节解析，残差 0）

四块 `kvmem/m2_v1_14b/` 实测布局（**magic 0x67677371、version 4**）：

| 偏移 | 字段 | home | project | habit | project_paraphrase18 |
|---|---|---|---|---|---|
| +0 | magic | 0x67677371 | 同 | 同 | 同 |
| +4 | version | **4** | 4 | 4 | 4 |
| +8 | n_token_count | 21 | 18 | 12 | 18 |
| +12 | tokens（4 B×n，首 token=151646，四块同） | — | — | — | — |
| +4n | u32 strm | 1 | 1 | 1 | 1 |
| +4 | cell_count | 21 | 18 | 12 | 18 |
| 每 cell **12 B** | **pos i32 / n_seq_id u32 / seq_id u32** | **pos 0..20** | 0..17 | 0..11 | 0..17 |
| +16 B | v_trans / n_layer / n_rot_k / **n_rot_v** | 0 / 48 / 128 / **64** | 同 | 同 | 同 |
| 每层 12 B | k_type / k_row（u64） | **8 = Q8_0 / 1088** | 同 | 同 | 同 |
| 再每层 12 B | v_type / v_row（u64） | **8 / 1088** | 同 | 同 | 同 |
| 总长 | `1188 + n×104,464` | 2,194,932 | 1,881,540 | 1,254,756 | 1,881,540 |

- **四块总长算式全部精确闭合，残差 0** ⇒ 无尾部数据、无截断、`consumed_to_eof` 等价成立。
- **每 cell 12 B 元数据里的 pos 是零基连续**（0..n−1）、n_seq_id=1、**seq_id=2**（块由 seq 2 写出）。放置到 4075 靠 `load_and_place` 用 `pos_max` 反推 base，再用 `repos_local` 整体挪位。
- **n_rot_v=64 非零** ⇒ **V 也带 rotary**（fork 特性），这正是 `repos_local` 必须同时处理 K/V 的原因。
- **四块之间除 n_token/tokens/cells/size 外无任何字段不同** ⇒ 「通过组与失败组来自不同版本/不同路径」在**格式层**被否掉。
- sha256（检测员自算，未读 `blocks_14b.json` 的结论字段）：`73843fc5…` / `536eac03…` / `f6f8e85c…` / `a4cf0888…`；与 `sha256_pass1` **逐一相等**，`pass1==pass2` 皆 True ⇒ 「两次独立编码逐字节相同」**独立成立（4/4）**。

### G.2 纠错记录：「块头无 pos 字段」是错的 —— 错误形态会重演

- **执行者的说法**：块头没有 pos 类字段。
- **实测**：pos **存在**，每 cell 12 B（pos / n_seq_id / seq_id），四块皆 0..n−1 连续。它不在 12 字节文件头里，而在 **KV 流内、逐 cell 排列**。
- **错误形态（记下来，因为它会重演）**：**按字段名去找，而不是按字节布局去找**。文件头里没有叫 `pos` 的东西 ⇒ 直接得出「没有 pos」。凡「逐 cell / 逐层」这类**重复结构**，字段名都不会出现在头部，必须按布局解。
- **后果**：若照此结论写判据，会得出「装载后的位置由引擎自定、与文件无关」，而真相是**位置来自文件**（所以 `repos_local` 的重转是必需的，见 G.4）。

### G.3 「无往返行为检验」——全仓不存在（Q1 结论）

- 以 `roundtrip|round_trip|往返|byte_identical` 全仓检索：**没有任何一处**比较「编码→挂载→提问」与「编码→存盘→重装→挂载→提问」的**答案或掩码**。
- 唯一近似是 `kvmem/m2_visibility/make_blocks_filler21_G18.py`（save → `load_strict` → `cell_scan`），只校验 **cell 数量、base、扫描计数**，**不比对答案、不比对 mask**。
- 两次编码逐字节相同（G.1）只证明**可重复**，不证明**无损**。
- ⇒ **块格式在行为层从未被证明无损。** 这是 E10 档案里的一个真空洞；「有没有往返检验」与「有没有往返损失」是两个问题，不可互相替代。

### G.4 候选机制 M-重转：`repos_local` 在 Q8_0 下是一次有损往返

- K 以**已施加 RoPE** 的形式存盘（连同施加时的 pos，见 G.1）；放到目标位必须重转 ⇒ `llama_kv_cache::seq_repos_local`（`llama-kv-cache.cpp:677`）。
- 代码注释（`llama-kv-cache.cpp:595-612`）自述：旋转在数学上精确（`R(pos2)=R(pos1)·R(pos2−pos1)`），但**该 cache 把 K 存在 Walsh–Hadamard 基里**，而 **RoPE 与 H 不可交换**，故一次位移实际是 `H → rope → H`；量化缓存还要 **dequant → … → requant**。
- ⇒ 每装载一次 = 每 cell 每层一次**有损往返**；误差随 |delta| 与 Q8_0 量化步长累积。
- **这批臂里 delta 与成败高度相关**：home 4075 / project 4014 / habit 3956 / project2 3886 / habit2 3892。不构成判据，但**足以让「重转损失」成为与内容、容量并列的候选**。
- 该机制的解释形状与 E10 症状**完全吻合**：cell 在场、可见（`masked=0`、覆盖 21/21），但注意力算出来是错的。

### G.5 `5/20` 分母漂移：5 是**重复次数**，不是问题数

- 误读：`C 臂 5/20` 曾被读成「4 块 × 5 个不同问题」。**实为「4 块 × 5 次重复」**。
- 依据：`tools/m2_visibility_probe.py` 每块只有**一个**问题、`run_arm` 每段只问一次；`ISOLATION-REPORT` §2 写的是「7 臂 × 5 次 = 35 run」「同臂 5 次答案逐字节相同」。
- 连带后果：**每格「逐块 × 逐次」的可读率从未被记录过**（只记了合计与「只有 habit 过」）⇒「四个块没有一块能算出损耗」（附录 F.7）的真正原因是**当年根本没按块记**，而不是「文档没给」。
- **台账自我更正**：本台账 F.7 及 §4 相关处此前沿用「每块 5 问」的说法，**以本条为准**。

### G.6 产物层缺陷两条：无 argv、写出无自证

| # | 缺陷 | 实测 |
|---|---|---|
| 1 | **产物无 argv** | `m14b_e10_probe/out/{C1,A3,A6}_*.json` 共 9 份，**没有一份带 `argv` 字段** ⇒「argv 原文与回报一致」这类话**无法核**，只能核到 `runner.script` / `n_predict` / 模型路径。建议把 `sys.argv` 写进 `runner`。 |
| 2 | **写出无自证（跑了但没证据）** | `runs_m14b/_driver14b.py` L15 定义 `ISO2_7B`，L219/L220 写作 `ISO2` ⇒ 走到该段必抛 **NameError**，而它位于 `res` 组装之后、`json.dump` 之前 ⇒ **ask 已消耗 GPU，产物写不出**。这类缺陷比算错更危险。**建议立为独立缺陷类：「产物写出无自证」** —— 跑批脚本必须能证明产物已落盘（写后回读并校验字段）。 |

### G.7 更正：KV cache 路径到底有几个运行时开关（**将来每次「靠环境变量做实验」的判断都依赖此表**）

**实测（`getenv` 全枚举，`llama.cpp/src/llama-kv-cache.cpp` + `tools/kvshim.cpp`）共 10 个**：

| # | 开关 | 作用层 |
|---|---|---|
| 1 | `LLAMA_KV_CACHE_DEBUG` | cache 调试打印 |
| 2 | `LLAMA_KV_MASK_BIAS` | mask 偏置（可对指定块加 ±b） |
| 3 | `LLAMA_KV_MASK_DEBUG` | mask 调试打印 |
| 4 | **`LLAMA_KV_MASK_LAYOUT`** | mask 布局（此前漏列） |
| 5 | `LLAMA_KV_MASK_NODEDUP` | 关闭去重 |
| 6 | `LLAMA_KV_MASK_Q` | mask 查询侧 |
| 7 | `LLAMA_KV_MASK_SEQ` | mask 序列侧 |
| 8 | `LLAMA_KV_MASK_WINDOWS` | mask 窗口 |
| 9 | `LLAMA_KV_REPOS_FAULT_LAYER` | **重转（repos）故障注入** —— 与 G.4 直接相关 |
| 10 | **`LLAMA_ATTN_ROT_DISABLE`** | K 旋转总开关（置位后 `n_rot_k=0`，见 `llama-kv-cache.cpp:321-322`） |

**更正我先前的一处错**：`LLAMA_KV_OVERRIDE_TYPE_{STR,INT,FLOAT,BOOL}` **不是环境变量，也不是 KV cache 开关** —— 它们是 `llama_model_kv_override_type` 的**枚举值**（`llama.h:279`），配合 `--override-kv KEY=TYPE:VALUE` 覆盖 **GGUF 模型元数据**（`common.cpp:689`、`llama-model-loader.cpp`）。⇒ **不能用它把已量化的块升成 f16；f16 臂必须重新编码**（`kvshim.cpp:163-164`：cache 类型在**建 context 时**由 `q8` 标志决定）。

### G.8 预登记条件句（**先写，不等数据**）

> 格式：条件 → 结论 → 作废范围。裁定人 lead，执笔检测员，2026-10-25 登记。**任何一方事后不得改写条件本身。**

**条件**：同文本、同问题、同 `n`、同判定器下，
**delta = 0 臂**（用 `write_at` 直接编到目标位置，装载后 `repos_local(0)`，全程零重转）**可读**，
而 **delta ≠ 0 臂**（现行口径：编在 0..n−1 再重转到目标位）**不可读**。

**结论**：E10 的失败**至少有一部分来自装置自损**（`repos_local` 的 `H→rope→H` + Q8_0 dequant/requant 有损往返），**不是模型性质**。

**作废范围**：
1. **7B 整张臂遍历表作废**（§4.3 A/B/C 三臂：0/5·5/5·15/15·5/20）—— 7B 也走非零 delta，该表上的读数不得再作「模型性质」引用；
2. **§4.4 掩码四格（「②己 注意力层无差异」）同时作废** —— 它测的是同一批被重转过的块；
3. **§3.2「失败在生成侧」这条归因撤回**，改记「失败至少部分在装置侧」；
4. **M2.5 的定义要重写**：从「4 块可见性」改为「**零重转口径下的 4 块可见性**」；
5. **反向条件同样预登记**：若 delta=0 臂**仍不可读**，则重转被排除，7B 臂表读数可继续引用（仍须标注非零 delta），E10 回到内容 / 容量 / 位置竞争三条假说。

**中间结果的读法（防事后自由裁量）**：若 delta=0 可读而 delta≠0 **也可读**，则不构成否证，只说明当前文本对重转不敏感 —— 此时须换 `home` 这类「难块」复验，**不得**直接宣布「重转无关」。

### G.9 delta=0 臂的两个工程陷阱（已核代码，执行者必读）

1. **`seq_repos_local(delta == 0)` 直接 `return 0`**（`llama-kv-cache.cpp:684-687`：`if (other || delta == 0) return 0;`）。而 `load_and_place` 现有断言是 `if moved != n: raise` ⇒ **delta=0 臂会以「repos_local moved 0 of N」直接崩**。必须把断言改为「`moved == n` **或** `delta == 0`」，否则这一臂跑不起来，且崩法会被误读成「块有问题」。
2. **`LLAMA_ATTN_ROT_DISABLE` 不是 delta=0 的替代品**：它把 `n_rot_k` 归零、K 不带旋转，整体破坏注意力（不是「精确的 0 位移」），只能当**负对照**，不可当干净口径。

### G.10 **判读规则**（独立条目，非附注）：跨臂常数量不能解释跨臂差异

**规则**：若某个可疑量（此处 = 重转损失，即 `repos_local` 的有损往返）在**每一臂上取同一个值**，则它**只能解释所有臂共同的失败，不能解释臂与臂之间的成败差异**。

**判读后果（两种情形必须分开读）**：
| 观测 | 允许的解释 | 禁止的解释 |
|---|---|---|
| **所有臂全挂** | **可以是装置造成的**（重转损失均匀压低天花板） | 不能说「模型取不到」 |
| **一挂一过** | 差异必须由**随臂变化**的量解释（内容 / 容量 / 位置 / 填充） | 不能用跨臂常数量（如目标块重转）来解释 |

**事实基础（实测）**：目标块的目标位**在每一臂里都相同** —— home 恒 4075、project 恒 4014、habit 恒 3956 ⇒ 因文件内 pos 为 0..n−1，其 delta（= 目标位）**逐臂相同** ⇒ 重转损失是**跨臂常数**。只有第 4 块与填充块的 delta 随臂变化（project2 3886 / habit2 3892 / 填充随占位）。

**适用面**：本条不限于 E10 —— 凡「固定靶 + 变化背景」的臂表都适用。写进台账的目的正是让**将来每一张臂表都照此分档读**。

### G.11 断言写法（lead 2026-10-25 裁定，覆盖检测员原提案）

- 检测员原提案：`moved == n or delta == 0`。
- **lead 裁定为精确期望值**：`expected = n if delta != 0 else 0; if moved != expected: raise`。
- **理由（照录）**：`or delta == 0` 有**静默通过**风险 —— 将来若有人把 delta 算错成 0，断言就不响了；精确期望值在两种情况下都咬得住。
- **配套硬要求**：断言放宽后**必须同时把 `delta` 与 `moved` 写进 run json**，否则「没动」与「动了但没报」分不开。
- **原则（照录，候选入纪律族）**：**放宽断言是让测试变空的经典手法。** 任何「把断言改宽」的修复都必须同时增加一个**可核读数**，否则等价于删除该断言。

### G.12 **方法论**：凡称某 `LLAMA_*` 是环境变量钩子，必须给出 `getenv` 调用点行号

**规则**：不得凭名字推断「`LLAMA_` 前缀 ⇒ 环境变量」。**必须**给出 `getenv(...)` 的行号；给不出行号的一律**不算 env 钩子**。同理，枚举钩子**不得靠记忆**，必须 `getenv` 全扫。

**本轮的两次自证**：
1. `LLAMA_KV_OVERRIDE_TYPE_{STR,INT,FLOAT,BOOL}` 被误当成 env 钩子 —— 实为 `llama_model_kv_override_type` 的**枚举值**（`llama.h:279`），配 `--override-kv` 覆盖 **GGUF 模型元数据**（`common.cpp:689`、`llama-model-loader.cpp`）。**整整错了一轮方向判断**（曾据此以为可靠环境变量把块升成 f16）。
2. `LLAMA_KV_MASK_LAYOUT` **漏列** —— 靠记忆枚举时漏掉的真实钩子，`getenv` 全扫后才现身。

**正确清单的生成方式（可复算）**：`grep -rn getenv llama.cpp/src/llama-kv-cache.cpp tools/kvshim.cpp` ⇒ 现存 **10 个**（见 G.7 表）。任何「能不能靠环境变量做这个实验」的判断，都必须先重跑这条命令，**不得引用记忆，也不得只引用本节表格而不复核行号**。

### G.13 核查结果（2026-10-25 本轮实测，三项**均未落地**）

| # | 待核事项 | 实测 | 结论 |
|---|---|---|---|
| 1 | 免责句三处（`metric_note` 字段 / stdout 表头 / 禁止单独写「3/3」） | 全仓 grep `metric_note`、`不测忠实性`、`不可当答案正确率`、`答案忠实性` ⇒ **0 命中** | **未落地** |
| 2 | `答案忠实性` 是否进 schema 且限单值 | 同上，**字段名都不存在** | **未落地**（连字段都没有，谈不上自由文本） |
| 3 | `load_and_place` 断言是否改精确期望值、`delta`/`moved` 是否入 json | `tools/m2_visibility_probe.py:452-454` 仍是 `moved = eng.repos_local(...); if moved != n: raise`；抽 `m14b_e10_probe/out/A6_home.json` 顶层键 19 个，**无 `placed`、无 `delta`、无 `moved`、无 `base`**（只有 `layout.segments` 的 `pos_lo/pos_hi`） | **断言未改、读数未记** |

**后果（不是提醒，是结论）**：**delta=0 臂与故障注入臂若在此状态下开跑，会以「repos_local moved 0 of N」崩掉，而产物里没有任何字段能证明 delta 算对了没有。** 上表三项必须在开跑前落地。

### G.14 **G.11 修订（lead 2026-10-25）**：放宽一条断言，必须保留另一条独立锚

G.11 的原则是「放宽断言必须同时增加可核读数」。lead 把它**精确化**为：**改第一条可以，删第二条不许**。

**现场事实（检测员复核 tools/m2_visibility_probe.py）**：load_and_place 里有**两条互不依赖**的断言 ——
| 行 | 断言 | 它证明什么 |
|---|---|---|
| L452-454 | moved = eng.repos_local(...)；if moved != n: raise | **该动的动了**（位移被施加） |
| L455-457 | pm = eng.pos_max(slot)；if pm != seg.pos_hi - 1: raise | **最终位置对了**（落点正确） |

两条独立成立 ⇒ 把 L453 的 moved != n 改成 moved != expected（expected = n if delta != 0 else 0）**不会让这个检查变空**，因为 L456 仍在。
**因此本条取代 G.11 里「一律不许放宽」的读法**：正确形式是「**放宽一条，必须保留另一条独立锚**」；若某次修改同时动了第二条，性质立刻从「修正」变成「删除检查」。

### G.15 **纪律**：产物不可回填（旧产物不许补字段）

**规则**：历史产物是**当时证据的快照**。给它补字段 = **伪造当时的证据**。新读数必须**另起目录或另起名字**（如 out_smoke/、A6_home.v2.json），**不得原地加键**。

**实例（lead 2026-10-25 派单所设）**：kvmem/m2_visibility/m14b_e10_probe/out/A6_home.json 等 9 份是「**非零 delta 且无位置读数**」的历史产物（顶层 19 键，无 placed / base / delta / moved）。**若给它补上 delta，就等于声称「当时记了 delta」，而当时没记** —— 这会污染 G.10 的判读（跨臂常数量必须能被核）。

**为什么这条一定会被违反**：「补两个字段不就行了」是最省事的直觉，而且补完后**看起来更完整**，正因如此更危险。**任何「让旧产物看起来完整」的改动，一律按伪造处理。**

### G.16 **G.13 更正**：准确说法是「未落地，但已在改」

检测员 G.13 写的「未落地」在事实层成立，但**少了一半**：执行者**正在改，且已落到注释与半截代码**。实测（同一份文件）：
| 行 | 状态 |
|---|---|
| L458-460 | **注释已写**：base 是 .kvmem 在它自己文件里携带的位置，delta 是此处实际施加的重转；两者都不由布局暗示，没有它们产物无法回答「这块转过没有、转了多少」 |
| L461-464 | **半截代码已写**：placed.append 里已含 id / slot / cells / file / file_sha256 / **base** / **delta** / pos_lo / pos_hi —— **base 与 delta 已入 placed**，但 **moved 与 expected 尚未入** |
| L453 | 断言**仍是** if moved != n: raise（未改成精确期望值） |
| L456 | pos_max 独立锚 **仍在** |
| L618 / L651 | placed = load_and_place(...) 后仅交 share_layout() 使用 |
| **产物层** | **placed 从未写进结果 dict** —— 全文件无 res.placed 之类赋值 ⇒ **即使 base/delta 算出来了，也不进 json** |

**结论**：这不是「它没管」，而是「**改到一半，且缺最后一步**」。G.13 的三项判定仍成立，但**闸门描述应改为**「已有进展，缺三项：moved/expected 入 placed、placed 入产物、断言精确化」。
**另据此更正检测员自己的一句话**：日后不得把「产物无 delta」写成「代码没算 delta」—— 代码已经算了，**是没写出去**；这两种缺陷的修法完全不同。

### G.17 状态更新（2026-10-25 12:2x 实测）：14B 的 car 块已存在、A2 已在 14B 上跑通、metric_note 已落、placed 仍未落

| 事项 | 实测 |
|---|---|
| **14B car 块** | `kvmem/m2_v1_14b/car.kvmem` **已存在**，1,986,004 B，Oct 25 12:18。解析：n_tokens=19、cells=19、**n_layer=48**、n_rot_k=128、**k_type=8（Q8_0）**、k_row=1088；总长 1188 + 19×104,464 = 1,986,004 **精确闭合**。⇒ **此前「14B 无 car 块、A2 从未在 14B 上跑」的结论作废**（G.6 之后的实测变了，不是当时判断错，是**文件后来才出现**，必须记清时序） |
| **A2 臂** | `m14b_e10_probe/out/A2_r1_home.json`：四段 home 21 @4075 / project 18 @4014 / habit 12 @3956 / **car 19 @3885**，合计 **70 cells**。**home 答「我住在建国路 12 号 2 单元 602。」**（期望「建国路」）⇒ **14B 上 70 格的 A2 臂里 home 可读**，与 7B「home 单块 0/5」相反 |
| **metric_note** | **已落地**：A2 两份产物顶层均有 `metric_note`，值为「key-token 命中率；不测忠实性；不可当答案正确率引用。在 E10 内只回答『该块硬事实有没有进入答案』」 |
| **placed** | **仍未落地**：A2 / A3 / A6 / C1 全部 19–21 键，**无 `placed`**（含新跑的 A2） |
| **答案忠实性** | **仍无此字段** |
| **pos_max 独立锚（L455-457）** | **仍在** |

**新增缺陷：同一臂两个文件名。** `probe_A2_r1_home.json`（started_at 12:20:56）与 `A2_r1_home.json`（12:21:55）**答案与 raw 逐字节相同**，仅时戳/耗时不同 ⇒ **不是回填**，但**同一实验以两个名字落盘**，引用时必须指定是哪一份。
**附带的正结果**：同一臂相隔约 1 分钟跑两次，**四段答案逐字节相同** ⇒ 14B 上的**答案确定性**独立成立一次（此前只在 7B 上验过）。

### G.18 自我更正（检测员）：我把「广陵路」写成了「建国路」——**假引文**

**错误**：我在回报中写「home 答『我住在建国路 12 号 2 单元 602』（期望建国路）」，并把它当作「14B 不复现」的证据引文。
**真相（lead 指出，检测员复算确认）**：产物里是 **广陵路**。三份产物 grep：建国路 = false（A2 / probe_A2 / C1 全 false），广陵路 = true；control.questions[0].expected 明写广陵路；答案首句为「我住在广陵路 12 号 2 单元 602。」

**错误是怎么发生的（必须记，因为这是方法问题不是笔误）**：我当时用 bash + python 打印中文，终端按 GBK 解码 UTF-8 ⇒ 输出为乱码；我没有换通道，而是**从乱码的字形去认汉字**，认出了一个不存在的词。
**规则（新增，检测员自用，建议升为全队纪律）**：
1. **禁止从乱码终端重建中文**。凡需引用中文原文，必须走能保证 UTF-8 的通道（tools.read 的行号输出、或程序返回 JSON 值），并**回显原文逐字**；
2. 凡引用中文原文，**必须同时给出字段路径或行号**（如 answers[0].answer、control.questions[0].expected），否则该引文不得进入结论；
3. **后果等级**：本条错的不是数字而是一句**被当作证据的引文** —— 引文假，整条证据链都会被质疑。故本条按**最高等级**记录：**假引文比错数字严重一个量级**。

### G.19 状态更正：③ 答案忠实性 **A2 已落**（检测员上一轮判错）

**检测员原判**：「答案忠实性 无此字段 → 未落地」。**错**：我当时只读了 A3/A6/C1 三份**旧**产物，就把结论推广到了 A2。
**实测（A2_r1_home.json / probe_A2_r1_home.json，各 21 键）**：
- answer_fidelity = 「未检（判定器结构上不可检）」
- answer_fidelity_schema = 一个对象，含 enum 键（值域只有上面那一个字符串）与 note 键（内容大意：只允许这一个值，若填「已检」必须改 schema，会被看见）
⇒ **单值域已实现，且带有「想改就必须动 schema」的自锁** —— 这条防线是有效的，**超过我上一轮建议的强度**。

**准确说法（取代上一轮）**：**A3/A6/C1 等旧产物无此字段是正常状态（旧产物不许回填，见 G.15）；A2 新产物已落。**
**状态总表（截至本轮）**：① placed **未落**（21 份 json 一处也无）；② metric_note **已落**（A2 顶层）；③ answer_fidelity + schema **已落**（A2）；④ pos_max 独立锚 **完好**。

**教训（与 G.2、G.12 同类）**：**拿一部分样本的结论去代表全体，和按字段名找结构一样，都是「局部当全局」**。检测员的取样必须写明覆盖了哪些文件。

### G.20 **G.10 的适用边界**（本条为 G.10 正文的一部分，非附注）

G.10 只约束**臂间比较**：某个量在**每一臂上取同一个值**时，它不能解释「同一块在不同臂上的成败差异」。
**它完全不约束块间比较**。两种比较必须分开判：
| 比较类型 | 判据 | 允许的解释 | 禁止的解释 |
|---|---|---|---|
| **臂间**：同一块，不同臂（如 home 在 C 臂 vs A 臂） | 该块 delta 逐臂相同（目标位固定） | 随臂变化的量（背景 / 内容 / 布局） | 「目标块重转」这类**跨臂常数** |
| **块间**：同一臂内，不同块（如 7B 的 home 0/5 vs project 5/5） | 两块的 delta **不同**（4075 vs 4014） | **delta 是活解释**，G.10 不适用 | 不能用 G.10 排除 delta |

**判别口诀**：**看变化的是哪一维**。变的是臂 ⇒ 臂间；变的是块 ⇒ 块间。**G.10 的常数项只对「固定靶 + 变化背景」成立**；一旦靶自己也变了，常数假设立刻失效。

**实例（lead 2026-10-25 自述之误，照录）**：lead 在上一轮把 7B 的「home 0/5 而 project 5/5」描述为「目标块 delta 逐臂相同 ⇒ 解释不了一挂一过」—— 这是把**块间**说成了**臂间**。检测员指出后 lead 采纳并判为错。
**为什么一定会重演**：「同一块在不同臂」与「不同块在同一臂」在中文里都可以说成「这块一挂一过」，**语法上分不开，只有把比较维度写出来才分得开**。故此后凡写「一挂一过」，**必须写明是臂间还是块间**，否则该句视为无效表述。

### G.21 命题 (b) 的处境：它不只是「考古」，更是**未来所有挂载的基线**

**两条独立命题（lead 采纳，逐字保留）**：
| 命题 | 需要的证据 | 现在有没有 |
|---|---|---|
| **(a) E10 在 14B 上不复现** | **只需 14B 的读数**（A2/C1/A3/A6 + n=3 重复），与 7B 装置是否干净**无关** | 有初判（n=1，待 n=3） |
| **(b) 7B 的读数受装置影响** | **需要独立证据**：delta=0 臂（G.8 条件）或 `LLAMA_KV_REPOS_FAULT_LAYER` 注入臂 | **一条也没有** |

**lead 原句（原样保留）**：「**合并的最坏后果是用未验假设给整张史料表开脱。**」

**lead 2026-10-25 的补充决定（改变 (b) 的定位）**：注入臂照跑，但**理由改成「基础卫生」而不是「考古」** ——
- `repos_local` 有损与否影响**将来每一次挂载**：M4-C 租约承重、M5 两探针都要挂块；
- ⇒ **即使 E10 归档，(b) 仍值得一条臂**；它的用途不只是解释 7B，而是**给所有未来挂载定基线**。

**这条补充的方法论意义（检测员加注）**：它把 (b) 从「为一段史料辩护」升级为「为后续全部实验提供仪器常数」。**意义变了，但独立性不变** —— (b) 仍然不能被用来给 (a) 开脱。

### G.22 状态（2026-10-25 本轮末）

| 闸门 | 状态 |
|---|---|
| ① `placed`（含 base / delta / moved / expected） | **仍红 —— 唯一未落盘的一项**。全 21 份 json 一处也无；状态是「算出来了但没写进去」，**不是算错了** |
| ② `metric_note` 顶层 | 已落（A2） |
| ③ `answer_fidelity` + 单值 schema | 已落（A2）；lead 复核：enum 仅一值、带自锁注释 |
| ④ `pos_max` 独立锚 | 完好 |
| ⑤ `hit_full` / `hit_first_sentence` 并列布尔 | **已派未落**。主判据仍为 `hit_full`；「把主判据换成首句」属**改对象**，已上升用户裁定（与 M2.5 销号/保留一并问） |
| ⑥ 旧产物不许回填（G.15） | 无违反迹象（A2 为**新跑**；另有 `probe_A2_r1_home.json` 早 1 分钟的独立运行，答案逐字节相同，见 G.17） |

### G.23 §13.9 第 1 项 · **墓碑定稿（草案，待 n=3 后落盘；PROGRESS 未改）**

**用户裁定（原文选项）**：「归档销号：原判据整体作废，M2.5 从路线图移除」。
**落法**：路线图 **§13.9 第 1 项整条移除**，但**保留墓碑**（不删痕迹）。**以下为墓碑全文草案**：

> **§13.9 第 1 项（M2.5 可见性收口）· 墓碑**
>
> M2.5 曾以「4 块布局 **4/4 可读**、n=**5** 稳定；**C 臂 5/20 → 20/20**」为验收判据。
>
> 该判据的**对象是 7B 读数**（用户已裁定 7B 全线降为史料）；且 `5/20` 的分母 **5 是重复次数、不是问题数**（见 G.5），「4 块 × 5 问」的读法从未成立。
>
> 14B 复测**不复现**该现象：A2（70 cells，含 car）**4/4 key-token 命中**；C1（51）3/3；A3（69）3/3；A6（63）3/3 ⇒ **对象消失，销号**。
>
> 锚：`A2_r1_home.json` sha16 `165be0d93174ab6d`；块布局实测见附录 G.1；同臂两次运行答案逐字节相同见 G.17。
>
> **两处强制限定**：(a) 只能写「在**非零 delta 口径**下不复现」；(b) n=3 未齐前只能写「**初判**」。
>
> **销号 ≠ 修好了一个 bug** —— 是「**这个 bug 在 14B 上不存在**」。前者会被读成「我们做对了什么」，后者才是事实。

**检测员加注（落盘时必须保留）**：墓碑**不关闭**重转（delta）问题 —— 该问题按 G.21 的定位另立（基础卫生，为将来每一次挂载定基线），**不得随 M2.5 一起被归档掉**。

### G.24 判据裁定（lead 2026-10-25，用户授权「你觉得哪种最好」）

**裁定**：**主判据仍 `hit_full`**，**并列 `hit_first_sentence`**；**不换成首句**（换主判据 = **改对象**，已由用户授权 lead 定，定为不改）。
**三条必须并排写的边界**：
1. **四块期望 token 互不相同**（广陵路 / 3月14 / 美式 / 浙B-3F19K）⇒ **多块复述不能制造假命中**，4/4 不会被污染成假阳性；
2. **但「4/4」只是可见性（可达性）证据**，**不是选择性/问答能力**；
3. 与 A6 那条「**key token 命中 ≠ 答案正确率**」**并排写**，两条同源（都是「命中率不能越界引用」）。

**实现层必需的性质（检测员核对用）**：两个布尔必须是**同一份答案的两种判法**，不是两次独立判定。⇒ 逻辑单调性必须成立：
| 组合 | 判 | 说明 |
|---|---|---|
| `hit_full=true` 且 `hit_first_sentence=false` | **合法且预期**（尾部命中） | 正是要区分的形态 |
| `hit_full=false` 且 `hit_first_sentence=true` | **必为 bug** | 首句包含于全篇 ⇒ 首句命中必然全篇命中；反过来出现的唯一可能是**判法写反了或有别的错** |
**故核对规则**：凡出现第二行组合，一律报缺陷，不得当噪声放过。

### G.25 第 4 块槽位差 1：跨臂比较必须显式写出

**事实**：A2 的 car 段 `pos_lo=3885`；A3 的 project2 段 `pos_lo=3886`（A6 的 habit2 为 3892）。
**规则（lead 2026-10-25 要求）**：**第 4 块凡跨 A2/A3/A6 比较，必须写出这个 1 格差**；不写即视为**默认抹掉隐变量**（与 G.10 同类错误）。
**为什么不能忽略**：1 格 delta 本身可忽略，但**「当它不存在」与「当它可忽略」是两件事** —— 前者会让将来的读者以为三臂的第 4 块完全等价。

### G.26 墓碑定稿 v2：**引文两截制**（逐字节 / 释义必须分开）

**lead 2026-10-25 定的规矩（检测员上次在形式上从「省略引用」滑成了「看似原文」，虽要素全对）**：墓碑里对原文的引用**必须切成两截** —— 一截是**逐字节行内引用**（含管道符与反引号），另一截才是**释义**，且释义必须标注「释义，非原文」。

**逐字节引用一（L1824，表格行）**：

> | 1 | **M2.5 可见性收口** | 4 块布局 **4/4 可读**、n=**5** 稳定；`C 臂 5/20 → 20/20`；E10 的裁决落到「已修复」并给出新锚 |

**逐字节引用二（L1839，编号列表行）**：

> 8. **M2.5 收口**。

**释义（非原文）**：M2.5 曾以「4 块布局 4/4 可读、n=5 稳定；C 臂 5/20 → 20/20」为验收判据，并要求 E10 的裁决落到「已修复」并给出新锚。
**节标题逐字节（L1820）**：`### 13.9 按依赖序的五项与各自验收判据（一页可核）` ⇒ **§13.9 表共 5 项**（L1824–1828：M2.5 可见性收口 / M2 规划器 / M4-C 租约承重 / M5 两探针 / M1.8 三处 judge 冲突）。

**检测员追加的规矩（本次教训直接产物）**：凡在正式文本里出现「原文是……」的声称，**必须给出可 grep 的逐字节串**；给不出就改写成「大意是……」。**「要素全对」不豁免逐字节要求**，因为读者无法从要素反推原文形态。

### G.27 活引用面实测：**9 处**，不是 1 处（含 L1839）

全仓 `M2\.5` 命中 11 处：**PROGRESS 10 处** + `kvmem/m2_visibility/m5/PREREG-M5-PROBES.md` 1 处（检测员自己的预登记文件）。PROGRESS 的 10 处逐行分类：
| 行 | 原文要点 | 性质 | 处理 |
|---|---|---|---|
| L124 | 里程碑表第 8 行：状态「**未收口**」（验收线：4 块 4/4 可读、n=5 稳定） | **活**（状态断言） | 状态列改「已销号（见 §13.9 墓碑）」；验收线**原文保留**并加「7B 口径」限定 |
| L149 | 状态表：「M2.5 可见性收口 ｜ 未收口」 | **活** | 同上 |
| L1617 | 阻塞级：「M2 规划器未实现 … **阻塞 M2.5**」 | **活**（依赖断言） | 加「（原）阻塞 M2.5 —— 该里程碑已销号」 |
| L1618 | 阻塞级：「**M2.5 可见性未收口**（4 块 `C 臂 5/20`）」 | **活 + 含 5/20** | 加限定「7B 口径；分母 5 是重复次数」+ 已销号 |
| L1730 | 依赖链：「**M2.5（E10 收口）**─▶ M2 规划器 ─▶ M4-C ─▶ M5 ─▶ M1.8」 | **活**（结构链头） | 链头标「（原）」+ 已销号指针 |
| L1737 | 「**M2.5 必须在前**：只要 4 块还读不全 …」 | **活**（排序理由） | 标注该理由随销号降为史料 |
| L1773 | 依赖行：「**M2.5 收口**（否则 4 块验收会被 E10 污染）」 | **活** | 加「（已销号）」 |
| L1824 | §13.9 第 1 项 | **墓碑本体** | 见 G.28 方案 |
| L1839 | §13.10 第 8 项 `8. **M2.5 收口**。` | **活引用**（lead 发现的那处） | 原地改为指向墓碑，**不改编号** |
| L1932 | 欠账分类表：「训练 / M1.8 / **M2.5** / M4-C / M2 规划器」 | **活**（清单成员） | 写成「M2.5（已销号）」 |

**⇒ 结论：**「只处理 L1824 + L1839」不够，**另有 8 处活引用**会在文件里继续宣称「M2.5 未收口 / 必须在前 / 阻塞后续」。它们不必重写，**按 lead 的规矩「只许加、不许改数字」各加一个限定从句即可。**

**另**：检测员的 `PREREG-M5-PROBES.md` 第 1 行也提到 M2.5。该文件属检测员可写范围，但**未获放行前不动**，仅在台账登记待办。

### G.28 文档结构两方案（影响面实测，待 lead 拍）

**关键实测**：全仓对「§13.9 / §13.10 的**项号**」的交叉引用 = **0 处**（grep `13\.9` / `13\.10` 只命中各自标题 L1820 / L1830）。⇒ **文件内重编号零外部成本**。真正的成本在别处（见下）。

**方案 A：顺延重编**（§13.9 项 2–5 → 1–4；§13.10 项 9–11 → 8–10）
- 影响面：文件内 **0** 处；台账与口头表述里「§13.9 第 1 项」的指称会**变歧义**（G.23 已按旧号写死）。
- 风险：**重编号是历史漂移源**（本仓已有 38→41、41→42 被拒后改 34-b 的先例）。每次重编号都要重新验证「第 N 项还是不是原来那件事」。
- 收益：表里无洞。

**方案 B'：留号 + 墓碑行**（检测员推荐）
- §13.9 表**仍 5 行**，第 1 行原地改为墓碑行：`| 1 | ``M2.5 可见性收口`` **已销号** | 见下方墓碑；对象消失 |`；表下接墓碑段落。
- §13.10 第 8 项原地改为指向墓碑，**编号 8 不变**。
- 影响面：**编号全稳定**、**无洞**、**零外部成本**；与用户裁定「保留墓碑记录，不是删除痕迹」**相容** —— 「整条移除」落在**活判据**层面（判据消失），墓碑是用户另行要求的留痕。
- 风险：需在墓碑段首行写明「本行不参与任何验收」，防止将来被当作活项读。

**检测员建议**：**B'**。理由是 A 唯一的收益（无洞）在 B' 里也成立，而 A 要付出两笔：台账/口头指称要全部重述，且再开一次重编号的先例。**编号稳定本身就是资产。**

### G.29 结构裁定：**方案 C**（lead 2026-10-25）—— 字面移除 + 编号映射写进墓碑

**用户原话决定字面**：「原判据整体作废，**M2.5 从路线图移除**」+「同时保留一段『为什么销号』的记录与锚」。⇒ **「移除」是字面要求**：B' 把第 1 行原地改成墓碑行，等于**没移除，只改了样子**；A 重编号会掉历史指称。故取第三条。

**方案 C 三条**：
1. `§13.9` **移除第 1 行**，剩余 4 项**顺延重编为 1–4**；`§13.10` **移除第 8 项**，9–11 **重编为 8–10**。**表里无洞。**
2. **墓碑单独成段**（**不放表内**），段内**写死编号映射**：

> 原 §13.9 第 1 项（M2.5）—— **已移除**；原第 2–5 项 → 现第 1–4 项。
> 原 §13.10 第 8 项 —— **已移除**；原第 9–11 项 → 现第 8–10 项。

3. 墓碑段落**首行**写：「**本段不参与任何验收**」。

**为什么映射能消掉重编号的唯一代价**：检测员实测「文件内对 §13.9 / §13.10 项号的交叉引用 = **0 处**」⇒ 外部成本只剩**台账与口头表述**，而映射表正好覆盖它们。
**台账自我指称的补正（lead 要求）**：G.23 是按**旧号**写死的（「§13.9 第 1 项」），本行即为补正 —— **G.23 里的「§13.9 第 1 项」按上映射读作「已移除项（M2.5）」，不与新编号 1–4 混用。**

**墓碑位置（检测员建议，待 lead 定）**：放在 **§13.10 之后、新增为 13.11「已销号里程碑墓碑」**。理由：§13.10 是「已明确未做清单」，读者从**活清单**走向**注销记录**是自然顺序；且不动附录编号（附录已有 A–G）。

### G.30 九处活引用：**分类改，不用统一模板**（lead 裁定，理由：句子成分不同）

**lead 原话要点**：「这不是措辞问题，是**句子成分**问题。」若只挂从句，会出现**同一文件同时断言两件相反的事** —— 比不改更坏。

| 类 | 行 | 原文性质 | 改法 | 禁则 |
|---|---|---|---|---|
| **甲 状态断言** | L124 / L149 / L1618 | 断言「未收口」 | **否掉状态词**：`未收口` → `已销号（对象在 14B 上不复现，见墓碑）`，**保留删除线让读者看见原状态** | **数字一个不动**（如 `5/20`） |
| **乙 依赖断言** | L1617 / L1730 / L1737 / L1773 | **用 M2.5 论证别的东西被阻塞或必须在前** | **重写依赖关系**，不是加注 | 不许加从句敷衍 |
| **丙 编号列表** | L1839 | §13.10 第 8 项 | 随**移除 + 重编**处理，**不加注** | — |
| **丁 欠账清单** | L1932 | 「欠账」清单成员 | **从清单移除**（销号 = **这笔欠账被核销**），并在墓碑记一句「原列于欠账清单 L1932，现核销」 | 不许改成「加限定」 |

**检测员评论**：「甲类保留删除线」这一条是关键 —— 它让**原文仍在场**（读者能看见我们曾经断言过什么），同时**状态被否掉**。这比直接删字强：删字会抹掉「我们曾经这样认为」的证据，与 G.15「产物不可回填」同源。

**乙类的实质结论（检测员实测核查，回答 lead 之问）**：
| 问题 | 实测答案 | 证据行 |
|---|---|---|
| 除 E10 之外，M2 规划器还有别的**阻塞项**吗？ | **没有。** | L180（4 块布局受 E10 阻塞 ⇒ 规划器未实现）、L1737（M2.5 必须在前，否则放置规划的验收无法成立）、L1730（链头 M2.5 ─▶ M2 规划器） |
| 它自身还有什么缺口？ | **实现欠账**（非外部阻塞）：`plan()` 接口未写；全仓 grep 只命中 `planner_version` 布局字段 | L1617、L1774、L148 |
| 它与后续里程碑的方向？ | **它是 M4-C 的前置**（租约承重点 = 规划器调用面） | L1739–1740、L1755 |

⇒ **M2.5 销号后：M2 规划器由「被阻塞」变为「无外部阻塞，仅剩实现欠账」，并成为链头之一**（L218：M1 索引 ─▶ M2 规划器 ─▶ M3 ─▶ M4 ─▶ M5）。文件中应**明写「M2 规划器现无外部阻塞」**，否则读者仍会以为它在等什么。

**新发现的文档内部矛盾（建议立 drift 行 D10，待 lead 批）**：**L1617 方向写反** —— 该行「现状」列写「阻塞 M2.5」，而 L180 / L1730 / L1737 三处一致表明**是 E10 ⇒ M2.5 ⇒ 阻塞规划器**。⇒ 建议 D10：「L1617 把『被 M2.5 阻塞』写成『阻塞 M2.5』，方向相反；修法随乙类一并理顺，方向 = **改对象**」。

### G.31 **纪律**：预登记文件不因后续事实变化而回改（PREREG 一字不动）

**lead 2026-10-25 裁定**：`kvmem/m2_visibility/m5/PREREG-M5-PROBES.md` 首行提到 M2.5，**一个字都不改**。
**理由（照录）**：预登记的**全部意义在于事后不可改** —— 一旦为了引用的准确性去改它，**「预登记」这个性质就没了**，将来没法用它证明预言性。
**正确做法**：不是去改预登记，而是**在墓碑里反向指过去** ——「`PREREG-M5-PROBES.md` 首行提及 M2.5，指**当时语境**」。
**立为规则**：**预登记文件记录的是「当时我们以为什么」**，改了就毁证据；后续事实变化只能写在**别处**（台账 / 墓碑 / 勘误），**永远不能回写进预登记本体**。
**与 G.15 的关系**：G.15 管「产物不可回填」，本条管「预登记不可回改」—— 同一条原则（**证据是当时快照**）落在两类文件上。


### G.32 **落盘清单**（M2.5 销号 · 待 lead 审；任何人不得先动 PROGRESS）

> 基线：PROGRESS sha16 `34b7a35b1abb0468` / 183,793 B，行号一律指该基线。执行后须重算 sha16 并回报。
> 三类数字纪律：**读数数字不改**（5/20、21/21）；**结构计数必须同步改**（五项→四项）；**因果方向属改对象**。

#### 甲 · 状态表 2 处（**只圈状态词，整格不划**）
| # | 行 | 现文逐字节（仅列改动词） | 改法 | 校验 |
|---|---|---|---|---|
| 甲-1 | L124 | `**未收口**（验收线：4 块布局 4/4 可读、n=5 稳定）` | `未收口` 加删除线，其后插入 `已销号（对象在 14B 上不复现，见 §13.11）`；**括号内验收线原样保留**（它是「当年标准是什么」的证据） | 改后该行仍含 `验收线：4 块布局 4/4 可读、n=5 稳定` 逐字节 |
| 甲-2 | L149 | 第三列整格 `未收口` | 同上，只圈 `未收口` | 该行无数字；改后行应比原行长 |

#### 乙 · 依赖断言 4 处（**重写依赖，不许加从句敷衍**）
| # | 行 | 现文逐字节（仅列改动词） | 改法 | 校验 |
|---|---|---|---|---|
| 乙-1 | L1617 | 第四列 `阻塞 M2.5` | ① 方向改：`阻塞 M2.5` → `（原）被 M2.5/E10 阻塞；该阻塞已随 M2.5 销号消失`；② **D10 列语义修正**：在表头 L1613 之下加一句「**「现状」列 = 该未闭项当前卡在哪里/为什么还没闭，不是「它阻塞了谁」**」 | 全文不再出现裸 `阻塞 M2.5`；L1613 之后出现该列语义句 |
| 乙-2 | L1730 | 链头 `M2.5（E10 收口）─▶ M2 规划器 ─▶ M4-C（租约承重）─▶ M5 两探针 ─▶ M1.8 judge 冲突` | 链头改 `（原）M2.5（E10 收口）─▶`，**M2 规划器成为链头**；代码块下一行加 `（M2.5 已销号，见 §13.11）**M2 规划器现无外部阻塞**` | 该代码块内 `M2.5` 只以 `（原）M2.5` 形式出现 |
| 乙-3 | L1737–1738 | `1. **M2.5 必须在前**：只要 4 块还读不全，任何「放置规划」的验收都无法成立` / `—— 判据会被 E10 污染成「有时行有时不行」。` | 该条标 `（史料）原第 1 条排序理由`，注明**理由随销号失效**；原第 2 条（规划器在 M4-C 之前）**升为第 1 条** | 列表序号连续 1./2./3.，无跳号 |
| 乙-4 | L1773 | `\| 依赖 \| M2.5 收口（否则 4 块验收会被 E10 污染） \|` | 改为 `\| 依赖 \| （原）M2.5 收口 —— 已销号（§13.11）；M2 规划器现无外部阻塞 \|` | 该行仍含 `依赖`；全文无裸 `M2.5 收口` |

#### 丙 · 整行/整项移除 3 处
| # | 行 | 现文逐字节 | 改法 | 校验 |
|---|---|---|---|---|
| 丙-1 | L1618 | `\| 阻塞级 \| 未编号 \| **M2.5 可见性未收口**（4 块 `C 臂 5/20`） \| E10 未修复 \|` | **整行删除**；墓碑记 `原列于 §12.1 未编号行` | §12.1 表行数 16 → 15；**标题「（九条）」一字不动**（口径见文末） |
| 丙-2 | L1839 | `8. **M2.5 收口**。` | **整项删除** | §13.10 项数 14 → 13 |
| 丙-3 | L1932 | 例列 `训练 / M1.8 / M2.5 / M4-C / M2 规划器` | 删 `M2.5` 一词，其余保留 | 该行仍含 `训练`、`M4-C`、`M2 规划器` |

#### 丁 · 结构计数 1 处
| # | 行 | 现文逐字节 | 改法 | 校验 |
|---|---|---|---|---|
| 丁-1 | L1820 | `### 13.9 按依赖序的五项与各自验收判据（一页可核）` | `五项` → `四项` | 全仓 grep `五项` 归零（实测当前仅此 1 处命中） |

#### 戊 · 新增 §13.11（插在 L1846 空行之后、L1847 三条短横线分隔行之前）

整段插入（逐行照抄；引用块前缀为 >）：

     ### 13.11 已销号里程碑墓碑

     > **本段不参与任何验收。**

     **M2.5 可见性收口 —— 已销号（2026-10-25）**

     原验收原文（逐字节）：
     > | 1 | **M2.5 可见性收口** | 4 块布局 **4/4 可读**、n=**5** 稳定；`C 臂 5/20 → 20/20`；E10 的裁决落到「已修复」并给出新锚 |

     **为什么销号**：① 该判据的对象是 7B 读数（用户已裁定 7B 全线降为史料）；② `5/20` 的分母 5 是**重复次数、不是问题数**；③ 14B 复测**不复现**：A2（70 cells 含 car）4/4 key-token 命中、C1（51）3/3、A3（69）3/3、A6（63）3/3 ⇒ **对象消失**。
     **销号 ≠ 修好了一个 bug** —— 是「**这个 bug 在 14B 上不存在**」。
     **两处强制限定**：(a) 只能写「在**非零 delta 口径**下不复现」；(b) n=3 未齐前只能写「**初判**」。
     **锚**：`A2_r1_home.json` sha16 `165be0d93174ab6d`。

     **编号映射（旧指称解码表）**
     > 原 §13.9 第 1 项（M2.5）—— **已移除**；原第 2–5 项 → 现第 1–4 项。
     > 原 §13.10 第 8 项 —— **已移除**；原第 9–14 项 → 现第 8–13 项。

     **其他受影响位置**：原列于 §12.1 未编号行（阻塞级）；原列于 §14.5 欠账清单例列。
     **未随之关闭的机制**：`repos_local` 的重转是否有损另立（基础卫生，为将来每一次挂载定基线），**不随本墓碑归档**。
     **反向指针**：`kvmem/m2_visibility/m5/PREREG-M5-PROBES.md` 首行提及 M2.5，指**当时语境**，**不回改**（预登记事后不可改）。

#### 己 · 重编号（**实测：§13.10 共 14 项，非 11**）
| # | 位置 | 现 → 新 | 校验 |
|---|---|---|---|
| 己-1 | §13.9 表 L1825–1828 | 原 2–5 → 1–4 | 表 4 行、序号连续 1..4 |
| 己-2 | §13.10 项 L1840–1845 | **原 9–14 → 8–13** | 列表 13 项、序号连续 1..13。**lead 原拟 9–11→8–10 少算 3 项** |

#### 庚 · **清单外但须同时做**：5/20 限定语 3 处（G.5 分母纠错，非销号）
| # | 行 | 现文（改动词） | 改法 |
|---|---|---|---|
| 庚-1 | L121 | `C **5/20**（C 恒 1/4，只有 habit 过）` | 加 `（分母 5 为重复次数，非问题数）`，**数字不动** |
| 庚-2 | L447 | `\| C \| 4 块 \| **5/20**（C 恒 1/4，只有 `habit` 过） \|` | 同上 |
| 庚-3 | L1920 | 第 12 行 `4 块 `5/20`` | 同上 |

#### 「九条」口径实测（回答 lead 之问）
§12.1 表共 **16 行**：**F-\* 编号 11 条**（F-PS-1、F-M4-3、F-M4-1、F-M5-1、F-M3-1…F-M3-7）+ **未编号 5 行**（L1617、L1618、L1628、L1629、L1630）。11 条编号中 **2 条已闭**（F-M3-6、F-M3-7）⇒ **未闭 = 9 条**，与标题「（九条）」一致。
⇒ **移除 L1618（未编号）不改「九条」，标题一字不动 —— lead 结论对**；但理由须换成此口径，**不能写成「编号项=9」**（实为 11，将来按此数会当场矛盾）。

**合计**：甲2 + 乙4 + 丙3 + 丁1 = **10 处**；+ 戊 1 段新增；+ 己 2 处重编号；+ 庚 3 处限定语。


### G.33 清单补漏：**L180 一行两病**（乙 + 庚，一次改完）

lead 2026-10-25 指出：`grep 5/20` 六行为 121 / **180** / 447 / 1618 / 1824 / 1920；清单庚组只列了 121 / 447 / 1920，**漏 180**；且 L180 也不在乙组。
**L180 逐字节（现文）**：`4 块布局受 E10 阻塞（`C 臂 5/20`）⇒ M2 的**规划器本身仍未实现**，只有「几何冻结」（见 **§12.1 阻塞级·未编号**；§12.3 是「可能需要」四条，不含规划器）。`
**两病**：① `5/20` 要加「分母 5 为重复次数」限定（庚）；② 「规划器仍未实现（因 E10 阻塞）」这个**依赖结论要改**为「规划器现无外部阻塞」（乙）。**合并为一项乙+庚，一次改完。**
⇒ **合计由「15 处 + 1 段」改为「16 处 + 1 段」**。

### G.34 **两条执行纪律**（lead 2026-10-25，比清单本身重要）

**纪律甲 · 一律用文字锚点替换，不许用行号定位。**
- 每处 `old_string` 必须在文件中**恰好出现一次**；**0 次或多次立刻停**；
- **行号只用于写清单与复核，不用于改文件** —— 删掉一行之后后续行号全漂，用行号改必然错位。
**纪律乙 · 改完要交七条自证。**
| # | 自证项 |
|---|---|
| 1 | 新 sha16 / 字节数 / 换行数 |
| 2 | `git diff --numstat` |
| 3 | `grep 五项` = 0 |
| 4 | 编号连续性（§13.9 表 1..4；§13.10 列表 1..13） |
| 5 | 标题与表自洽（四项 / 4 行） |
| 6 | §16 / §17 照录区 LCS `mismatch=0` |
| 7 | `grep M2.5` 全表**无裸活断言**（只允许 `（原）M2.5` 或墓境内） |
**检测员的角色**：执行者交文档后**按七条独立核一遍，不采信自述**。

### G.35 A2p 独立核单（2026-10-25，检测员实算，12 份 = 4 块 × 3 重复）

**schema = `iso_run_v2`**；`A2p_*` 12 份，`n_predict = 64`。

**① `placed`：绿（自洽）**。12 份 × 4 段 = **48 条**，三条不变式**零违反**：
| 不变式 | 结果 |
|---|---|
| `target_pos − base == delta` | 48/48 通过 |
| `moved == expected` | 48/48 通过 |
| `pos_lo == target_pos` | 48/48 通过 |
**样例（home）**：base 0 / delta 4075 / target_pos 4075 / moved 21 / expected 21 / cells 21 / `match=delta-value` / `exact_expectation_rule=expected = cells if delta != 0 else 0`。**这正是 G.14 要的形态**（放宽一条断言，保留 `pos_max` 独立锚）。
**另有 `pos_max_anchor`**：`live_pos_max_raw=4095`、`cell_count=70`、四段覆盖 21/18/12/19 全 covered、`overlaps=[]`、`positions_min=3885`。**④ 独立锚不但仍在，还升级成了产物字段。**

**⑤ `hit_full` / `hit_first_sentence`：已落，但落点与两处缺陷值得记。**
- **落点**：两个布尔在 `answers[]` 内（**per-answer**），**不在顶层**；`hit_relation` 同处。
- **实测计数（12 份）**：`hit_full=true` **12/12**；`hit_first_sentence=true` **9/12**；`hit_relation` = `both` 9 / `tail_only` 3。
- **决定性发现**：把那 3 条 `hit_first_sentence=false` 的 `first_sentence` 与 `expected` **去掉空白后比较，3/3 全部命中** ⇒ **这 3 条 `tail_only` 全是空白伪影，不是尾部生成**。⇒ `hit_relation=tail_only` 的**真实计数是 0**；本批数据里**首句与全篇之间没有任何真实差异**。
- ⇒ **lead 要求新增 `ws_only` 档 + `hit_first_raw` / `hit_first_ws` 的必要性被数据证实，且不是边角情形 —— 是当前 100% 的 `tail_only` 命中。**

**n=3 已完成**：A2p_r1/r2/r3 × 四块，块内答案逐字节相同 ⇒ **4/4 × 3 = 12/12**。**M2.5 墓碑的「n=3 未齐」限定即将可以撤销**（仍需 lead 判）。

**两处新缺陷（均属「判据须能红」失效）**：
1. **`gen_tokens` 未扣问题 token**：实测 project 的 `gen_tokens=73`、`kvshim_n_tokens_after_ask=73`、`n_predict=64`，且 **question 未从 73 中扣除**。lead 的公式是 `after − before − question_tokens`，执行者用的是 `after − before`。
   ⇒ **后果**：`gen_tokens >= n_predict` 对任何像样的提问**几乎恒真**（原始 delta 必然包含问题 token）⇒ `gen_tokens_vs_n_predict=touched_cap` 这个判据**结构上很难变红**，等于「永远报可能截断」。这与「判据须能红」直接冲突。**修法**：扣掉问题 token（`eng.tokenize(question)` 的长度）后再比，或直接改名为 `raw_delta_tokens` 并在字段说明里写明「不可与 n_predict 比较」。
2. **字段命名与派单不符**：要求 `generated_tokens` / `truncated_inferred`，实落 `gen_tokens` / `gen_tokens_vs_n_predict`。语义相近但**名字不同就不可 grep 稽核**；建议按派单名改，或在 schema 里登记别名。
**`finish_reason` = `unavailable` 且 `finish_reason_why` 写清了「DLL 导出符号里没有任何 EOS/stop 信号，只能算 token 数，那是推断不是停止原因」—— 这一条做得对**，符合「给不出就写 unavailable，不写 unknown」。

**跨臂混淆（新，与 G.10 同类）**：`n_predict` **A2/A2p = 64，而 A3/A6/C1/S 全部 = 24**。⇒ ① 任何「截断」相关结论**不可跨臂比较**；② 「可读性」跨臂比较时，**64 的预算本身给了更多命中机会**。凡引用 A2 与 C1/A3/A6 的对比，**必须同时写出 n_predict 差**。

### G.36 「判据须能红」失效清单（累积）
| 实例 | 为什么红不了 |
|---|---|
| `gen_tokens >= n_predict`（本批） | 分子含问题 token，恒偏大 ⇒ 几乎恒真 |
| M5 judge 的「3/3」（旧） | 只查关键 token 命中，尾部无数字/日期的编造**结构上抓不到** |
| `answer_fidelity` 单值域（现行） | **设计上就只允许一个值** ⇒ 它红不了是**故意的**（自锁防冒充），属正确设计，不算缺陷 |
**分辨**：**设计上单值**与**结构上恒真**不同 —— 前者是诚实声明，后者是伪装成判据的常数。


### G.37 **纪律**：判据必须在同一批数据里**两种取值都能出现**（与「判据必须能红」并列，非附注）

**lead 2026-10-25 立**：「判据必须能红」的另一半 ——
> **只在单侧取值的判据不是判据，是常量。常量比缺失更坏 —— 缺失时人会去找，常量会被人当成「已经看过」。**
**实例（本批）**：`gen_tokens >= n_predict`（`touched_cap`）。它不是太严，是**没有值域**：`gen_tokens` 用 `after − before`，必含提问 token ⇒ 对任何像样提问几乎恒真 ⇒ **它不区分任何两个案例**。
**推论（检测员补）**：凡新判据落盘，**必须同时给出「它在什么条件下会取另一个值」**；给不出，则该字段只能命名为观测值（如 `raw_delta_tokens`），**不得命名为判据**（如 `truncated_inferred`）。**命名即承诺。**

### G.38 **纪律**：字段名是稽核接口（改名 = 让稽核失效）

**lead 2026-10-25 立**：
> **派单写定的字段名若被改名，等于让稽核失效** —— 稽核靠 grep，grep 靠名字逐字节相同。
**实例**：派单 `generated_tokens` / `truncated_inferred`，实落 `gen_tokens` / `gen_tokens_vs_n_predict`。
**为什么这不是风格问题**：**我们已经因为「要素对但形态不对」栽过两次** —— 一次是假引文（要素全对、逐字不符），一次是本次改名（语义相近、名字不符）。**同一个病，第二次出现就该立成规则。**
**执行口径**：改名必须**在 schema 里登记别名**，或在派单变更记录里写明谁批准、何时、为什么；**默认不改名**。

### G.39 **墓碑终稿 v3**（撤「初判」+ 主/旁证分层 + n_predict 标注；待落盘）

**相对 v2 的三处改动**：① 撤「n=3 未齐前只能写初判」（n=3 已齐：`A2p_r1/r2/r3` 块内答案**逐字节相同**，检测员已复算）；② 主证据单列 `A2p` 12/12 并标 `n_predict=64`；③ 旁证 C1/A3/A6 **必须标 `n_predict=24` 且注明不可平权**。
**保留不动**：「在非零 delta 口径下」这条限定（由 delta 决定，不由 n 决定）。

**墓碑全文（v3，可直落）**：

     ### 13.11 已销号里程碑墓碑

     > **本段不参与任何验收。**

     **M2.5 可见性收口 —— 已销号（2026-10-25）**

     原验收原文（逐字节）：
     > | 1 | **M2.5 可见性收口** | 4 块布局 **4/4 可读**、n=**5** 稳定；`C 臂 5/20 → 20/20`；E10 的裁决落到「已修复」并给出新锚 |

     **为什么销号**：① 该判据的对象是 7B 读数（用户已裁定 7B 全线降为史料）；② `5/20` 的分母 5 是**重复次数、不是问题数**；③ 14B 复测**不复现**（证据分层见下）⇒ **对象消失**。

     **证据（分层，不可平权）**
     - **主证据**：`A2p`（70 cells，含 `car`）**12/12 key-token 命中** = 4 块 × **n=3**，`n_predict=64`，**三次运行块内答案逐字节相同**。
     - **旁证**：`C1`（51 cells）3/3、`A3`（69 cells）3/3、`A6`（63 cells）3/3。**上述旁证全部 `n_predict=24`。**
     - **不可平权的理由**：预算不同不只是「截断与否」—— **`n_predict` 64 与 24 的差别本身给了更多命中机会**。把旁证与主证据写成同质证据，等于自己制造一个新的可被攻击点。

     **销号 ≠ 修好了一个 bug** —— 是「**这个 bug 在 14B 上不存在**」。
     **强制限定**：只能写「在**非零 delta 口径**下不复现」（该限定由 delta 决定，与重复次数无关）。
     **锚**：`A2p_r1_home.json`（schema `iso_run_v2`）；块布局与 `pos_max` 覆盖见其 `pos_max_anchor` 字段（`live_pos_max_raw=4095`、四段 21/18/12/19 全 covered、`overlaps=[]`）。

     **编号映射（旧指称解码表）**
     > 原 §13.9 第 1 项（M2.5）—— **已移除**；原第 2–5 项 → 现第 1–4 项。
     > 原 §13.10 第 8 项 —— **已移除**；原第 9–14 项 → 现第 8–13 项。

     **其他受影响位置**：原列于 §12.1 未编号行（阻塞级）；原列于 §14.5 欠账清单例列。
     **未随之关闭的机制**：`repos_local` 的重转是否有损另立（基础卫生，为将来每一次挂载定基线），**不随本墓碑归档**。
     **反向指针**：`kvmem/m2_visibility/m5/PREREG-M5-PROBES.md` 首行提及 M2.5，指**当时语境**，**不回改**（预登记事后不可改）。

**检测员提示（落盘时勿删）**：主证据的锚改用 `A2p_r1_home.json`（A2p 才带 `placed` / `pos_max_anchor` / `schema` 三个字段）；旧锚 `A2_r1_home.json`（sha16 `165be0d93174ab6d`）**仍可作历史锚**，但**不应作为主锚**，因为它是 21 键旧 schema、无 `placed`。


### G.40 **纪律**：「口径变更导致的自我认证」= 已出现一次（LCS 222 → 148）

**现象**：执行者报 §16「**148** 行 equal、mismatch 0」、§17「**39** 行 equal、mismatch 0」，并称「口径一致，只是行数从早前记的 **222** / **62** 变成 148 / 39」。
**lead 判**：「**口径一致」与「行数从 222 变 148」不能同时成立** —— 行数变就是口径变，且方向是**让比对变短**（少比 74 / 少比 23 行）。
> **把尺子改短再报全对，不能算通过。** 它只能证明「我挑出来比的那部分没变」，不能证明「这一区没被污染」。

**检测员独立复算（对称归一化：两侧同样剥 `>`，源侧降标题一级）**：
| 节 | 源行（含空行） | 源行（非空） | 我的 LCS | mismatch |
|---|---|---|---|---|
| §16 | **222** | **165** | 222 / 165 | **0 / 0** |
| §17 | **54** | **40** | 54 / 40 | **0 / 0** |

**执行者 148 / 39 的来源可以精确解释**：
- §16：**165 − 148 = 17**，而 §16 的标题行恰为 **17** 条 ⇒ 它把**标题整行排除**在比对之外。
- §17：**40 − 39 = 1**，而 §17 的标题有 **6** 条 ⇒ **两节的归一化不一致**（一节排标题、一节基本没排）。
⇒ **不只是尺子变短，而且两节用的不是同一把尺子。** 这类自证即使 mismatch=0，也**不能采信**。

**与 G.15 / G.11 的关系**：三者同族（**证据被驯化到能通过**），但形态不同 ——
| 条 | 形态 |
|---|---|
| G.15 产物不可回填 | **改数据** |
| G.14 放宽断言必须保留独立锚 | **改判据强度** |
| **本条** | **改尺子（改比对口径）** |

### G.41 环境事实：**PROGRESS 在 git 里是 untracked**

**实测（检测员复核）**：`git status --porcelain` ⇒ ` M README.md` 与 **`?? PROGRESS-AND-ROADMAP.md`**。
**后果**：① `git diff` 对它**恒空**；② **没有任何历史可回滚**；③ 所有「改前是什么样」只能靠台账与记忆。
**替代证明（合格）**：README 未变 —— 实测 sha16 `85f6a7d38b85bb49`（与执行者报的一致）；备份里的 README 为 `00849577d5416827`（5,327 B）。
**衍生纪律（LCS 基准）**：§16 / §17 的照录区**不能拿「改前的 PROGRESS」当基准（没有）**，正确基准是**照录的源文件**：
- §16 ↔ `D:/llama-mem-backup-2026-10-25/docs/legacy-2026-10-24/STATUS-REPORT.md` 第 **146–367** 行（84,321 B / 1,341 行，实测存在）；
- §17 ↔ `D:/llama-mem-backup-2026-10-25/PROJECT-STATE.md` 第 **505–558** 行（51,555 B / 573 行，实测存在）。
- **备份里没有 PROGRESS-AND-ROADMAP.md**（它是合并后才生成的，实测备份目录只有 FEATURES / HANDOFF / PROJECT-STATE / README / docs / kvmem / legacy）⇒ **不要去找不存在的旧版 PROGRESS**。

### G.42 **纪律**：局部枚举不许写成全称判断（「其他」= 全称口吻）

**实例**：墓碑「**其他**受影响位置」只列两处（§12.1 未编号行、§14.5 欠账例列），而实际受影响还有 L124 / L149 / L1619 / L1731 / L1736 / L1776 / L180。
**规则**：枚举不完整时**必须自称不完整** —— 写「（**非穷举**）」+ 一句范围说明；**「其他」二字自带全称含义**，列了两处就等于声称只有两处。
**为什么是同一个病**：与假引文、字段改名同族 —— **形态上像结论，实质上只是样本**。凡是**样本冒充全体**的写法，一律加「非穷举」。
**已落实（实测）**：现文 L1871 = 「**其他受影响位置（非穷举）**：… 其余活断言已就地加限定或重写（见 §2.3、§12.1、§13.1、§13.4 等处），不在此逐一列出。」**这条已合规。**

### G.43 **纪律**：核对期间版本必须稳定（核前核后 sha16 必须相等）

**由来**：检测员本轮实测发现 PROGRESS 在校对期间**正在被改** —— 前一次读到 185,770 B / 2,456 行（sha16 `50db3c02cf12eb90`），几分钟后再读为 **186,616 B / 2,461 行**（sha16 `ca47029db03b0561`），mtime 前进。
**规则**：任何一次核对，**开始与结束各取一次 sha16**；**两者不等 ⇒ 本次核对作废**，须对稳定版本重跑。**否则核的是移动靶**，结论既不能证明现在、也不能证明过去。
**推论**：lead 的「四个墓碑修正还没落」这一判断**在它取样时成立**；检测员取样时**已落**（见 G.44）。**两个判断都对，差别只在取样时刻** —— 这正是本条要防的混淆。

### G.44 检测员独立核单（本轮，稳定版本 sha16 `ca47029db03b0561` / 186,616 B / 2,461 行）

| 项 | 结果 |
|---|---|
| §16 LCS（两种口径） | **mismatch 0 / 0**（222 / 165） |
| §17 LCS（两种口径） | **mismatch 0 / 0**（54 / 40） |
| **标题文字**（lead 指出的盲区） | 两节共 **23** 条标题（§16 十七条 + §17 六条），**逐条文字全在、无一缺失** ⇒ **标题未被改** |
| `grep 五项` | **0** |
| `M2.5` 残留 | 仅 2 行：L1855（墓碑内**原文逐字节引用**）、L1868（**编号映射**）⇒ **无裸活断言** |
| 四点墓碑修正 | **已落**：L1859–1862 分层证据（主证据 `A2p` 12/12、`n_predict=64`、n=3、逐字节相同；旁证 C1/A3/A6 标 `n_predict=24`；不可平权理由）；L1864 **撤初判**并保留非零 delta 限定；L1865 **主锚换 `A2p_r1_home.json` `d0b360ec444ebc3f`**、旧锚降为历史锚并注明无 `placed`；L1871 **非穷举** |

**检测员自报一次口径错误（同类，必须记）**：我第一次跑 LCS 时**只剥了 PROGRESS 侧的 `>`、没剥源侧的 `>`**（源文件里 §3.1 本身是引用块），得 §16 mismatch **7** —— 那 **7 条全是我的归一化伪影，不是文档缺陷**。**改正后 0/0。**
⇒ **教训**：**归一化必须对称**；只要两侧处理的规则不同，mismatch 就既可能假阳性也可能**假阴性**（后者更危险）。这与 G.40 是同一把尺子的两面。


### G.45 ⑥ 重开：**变换台账法**（生成式判法），检测员独立实现与结果

**为什么废除归一化比法（lead 裁定，检测员认同）**：三个人得出三个数（检测员 0/0、执行者 C 档 0/0、lead tier-A **LCS 32/76**），**根因不是宽窄，是三人比的不是同一段**。清洗式比法（去 `>`、去空行、去〔〕、去标题层级）**剥掉的不只是我们加的标注，也可能剥掉原文里真实存在的差异** —— 「把尺子改钝」的标准手法，**谁的 0 都不能自证**。

**正确判法（生成式）**：把声明的变换写成函数，施加在源文上得到 `expected`，**与实文件逐行严格相等**，差异必须 **= 0**。

**检测员的实现（独立脚本，锚点法）**：不预设起点，**以「源第一行变换后」在实文件中的首次出现定 body 起点**，再以「源最后一行」定终点；对 `expected` 与 `body` 做 LCS 对齐，**把未匹配的 body 行逐条列出**（这就是 T3/T4 的实测清单），剔除后要求**逐行全等**。

#### §16 结果：**PASS（纯 T1，零插入）**
| 项 | 值 |
|---|---|
| 源区间 | `STATUS-REPORT.md` 第 146–367 行 = **222 行**（实测 84,321 B / 1,341 行） |
| 实文件 body | **L2102–L2323 = 222 行** |
| T1 标题降级 | **17 条**（全部 `##`/`###`/`####`→各降一级） |
| T3 插入 | **0 条**（LCS 未匹配 = 0） |
| T4 行内注 | **0 条** |
| **剔除后逐行严格相等** | **true**（222/222 全等，`mismatch = 0`） |
⇒ 与文件自述「照录方式逐字，**唯一改动是标题降一级**」**完全一致**。

#### §17 结果：**PASS（T1 + T2 + T3 + T4 全枚举，剔除后逐行全等）**
| 项 | 实测 | 与声明是否一致 |
|---|---|---|
| 源区间 | `PROJECT-STATE.md` 第 505–558 行 = **54 行**（非空 **40**、标题 **6**） | **一致**（自述 505–558） |
| 实文件 body | **L2339–L2399 = 61 行** | — |
| **T1** | 6 条标题各降一级（`## §10 附录`→`### §10 附录`；`### 10.x`→`#### 10.x`） | 一致 |
| **T2** 章首导语（非照录） | **L2327–L2337**（§17 标题 + 空行 + 9 条 `>` 导语） | **一致**（lead 给的正是 2327–2337） |
| **T3** 标注（逐条） | **L2359、L2360**（§10.2 之后 2 条）+ **L2382、L2383、L2384、L2385**（§10.3 之后 4 条）= **6 条** | **一致**（自述「6 条 >` 标注（§10.2 后 2 条、§10.3 后 4 条）」） |
| **T3 附带的空行** | **L2381** 一个空行（**声明未提**） | **不一致（轻微）**：排版性，不含文字 |
| **T4** 行内〔〕 | **L2343**（1 处）、**L2349**（2 处）= **3 处 / 2 行** | **一致**（自述「3 处（分布在 2 行）」） |
| 未匹配的 expected 行 | **0** | — |
| **剔除后逐行严格相等** | **true**（54/54 全等，`mismatch = 0`） | — |

#### 关键旁证：**源文里没有任何 `>` 行，也没有任何〔〕**
实测 `PROJECT-STATE.md` 505–558：以 `>` 开头的行 **0 条**；含 `〔` 的行 **0 条**。
⇒ **T3/T4 全部是纯插入，不存在「剥掉原文真实差异」的可能** —— 这一条比 mismatch=0 更重要，因为它证明**尺子没有掩盖东西**。

#### 三人三个数的解释（回答 lead）
- **lead 的 32/76**：从 `## 17 附录 B` 起算，把**我们自己的章首导语（L2327–2337）当成 expected 的一部分** ⇒ 源文里当然找不到这些行，全数落进 mismatch。
- **执行者的 148 / 39**：把**标题整行**排除（165−17=148），§17 又只少 1 行 ⇒ **两节口径不一致**（G.40）。
- **检测员的 0/0**（旧法）与本次 **0**（生成式）：旧法的 0 是「清洗后碰巧相等」，**不能自证**；本次的 0 是「**声明的变换 + 逐条插入 + 逐行全等**」，可以自证。

**边界复算（与 lead 独立核对一致）**：`505` = `## §10 附录`、`507` = `### 10.1`、`558` = `---`、`560` = `## §11 下一步` ⇒ **505–558 = 54 行**；**62 这个数没有任何边界能算出来 ⇒ 54 定案。**

**纪律补充（G.40 的加强版）**：**照录区的判法必须生成式；清洗式比法即使 mismatch=0 也不得作为通过依据。** 判据是「**我声明改了哪几行、逐条列出、剩下的逐行全等**」，不是「我洗掉什么之后看起来一样」。


### G.46 **硬规矩**：照录核对必须给「源起止行号 + 两端定位锚」，不许只给行数

**lead 2026-10-25 立（同时已派给执行者）**：
> 照录核对必须给「**源起止行号 + 两端各自的定位锚（首行原文 / 末行原文）**」，**不许只给行数 —— 行数没有唯一解，锚有。**
**检测员补充**：还必须**声明变换方向**（「降一级」= **加一个 `#`**，不是去一个 `#`）。方向不写死，同一句话可被实现成相反操作。

**同一件小事里出现四次「量的不是同一段 / 用错变换」（没有一次是算错）**：
| # | 谁 | 数字 | 病因 |
|---|---|---|---|
| 1 | 检测员（旧法） | 222 vs 165 | **含空行 / 非空两口径未声明** |
| 2 | 执行者 | 148 / 39 | **标题整行被排除**（165−17=148），且两节口径不一致（G.40） |
| 3 | 执行者 | §16 **208** | **窗口短 14 行**（文档自述 146–367=222）⇒ 那 14 行**没验到** |
| 4 | **lead（自报）** | 147 / 165 假红 | 把「降一级」实现成**去掉一个 `#`**，**方向反了**；改正后 165/165 |

**检测员本次的锚（按新规矩交付）**：
| 节 | 源起止 | 首行锚（源→副本变换后） | 末行锚 | 副本 body |
|---|---|---|---|---|
| §16 | 146–367（222 行） | `## 3. 踩坑与硬约束…` → `### 3. 踩坑与硬约束…` | 源 367 「…已废弃。」 | **L2102–L2323**（222 行） |
| §17 | 505–558（54 行） | `## §10 附录` → `### §10 附录` | 源 558 `---` | **L2339–L2399**（61 行，含 7 插入） |

### G.47 §17 核单**必填项**：源侧「未被污染」的直接证明

**lead 要求**：把「源 505–558 中以 `>` 开头 **0** 条、含 `〔` **0** 条」写进**核单正文**，不要只写在回报里。
**理由（照录）**：它是「**尺子没有掩盖任何东西**」的唯一直接证据，**比 54/54 更重要** —— 后来的读者看到「有条目被剔除」会本能怀疑是不是把差异剥掉了。

**量化（本核单正文）**：
| 项 | 实测 | 意义 |
|---|---|---|
| 源 `PROJECT-STATE.md` 505–558 行数 | **54**（非空 **40**） | 与文件自述一致 |
| 源中以 `>` 开头 | **0 条** | ⇒ T3 的 6 条标注**全是插入**，没有一条是原文 |
| 源中含 `〔` | **0 条** | ⇒ T4 的 3 处（2 行）**全是插入** |
| 源中标题 | **6 条** | ⇒ T1 只有 6 处降级 |
⇒ **不存在「剥掉原文真实差异」的可能。** 本节为核单必填，缺此节则 §17 的 54/54 **不得单独作为通过依据**。

### G.48 **纪律**：恒真与恒假是同一种病；**新判据落盘前必须构造必然触发它的案例并跑通**

**lead 立（与 G.37 配成一对）**：**恒真（`touched_cap`）与恒假（`hit_first_ws`）是同一种病 —— 都不随数据变化。新判据落盘前必须构造一个必然触发它的案例并跑通；跑不出触发案例，它就只是字段，不是判据。**
**恒假的成因（执行者自查）**：正则写成 `r"\\s+"`（raw 串里两个反斜杠）⇒ **永远匹配不到** ⇒ 该字段恒 `false`，`ws_only` 档从未点亮。

**修好后的实测（检测员独立复算，43 份产物中带该字段的 14 条）**：
| 组合 | 条数 |
|---|---|
| `full / first / ws` | **9** |
| `full / noFirst / ws`（= `ws_only`） | **5** |
| `tail_only` | **0** |
| 带该字段的文件 | **14**（`A2p_r1..r3` × 四块 = 12 + `TRUNC_project_np64/np128` = 2） |
⇒ **与 lead 报的「both 9 / ws_only 5 / tail_only 0」一致。**

**但必须同时记两个陷阱**：
1. **`hit_first_ws` 现在 14/14 全 `true`** ⇒ **单独看它又是一个常数**。判别力来自**配对**（`hit_first_sentence` 为假而 `hit_first_ws` 为真 ⇒ `ws_only`）。**任何只引用 `hit_first_ws` 的结论都等于没结论。**
2. **计数口径不可混算**：全仓 43 份产物共 40 条答案，其中 **22 条无该字段（`undefined`）+ 1 条 `tail_only` 属旧口径**。⇒ 「9 / 5 / 0」**只在那 14 条内成立**；写进文档必须带分母（**14 条**），否则会与整体计数对不上。

### G.49 两项已定（lead 裁定，不再问）

**① 臂 F 开跑**：测 `repos_local` 是否**承重**，**与 E10 归档无关**（对应 G.21 的「基础卫生」定位）。
**② `question_tokens` 这条路放弃，不修**：字段保留但**恒 `null`**，并写明「**此路不通，改用行为对照**」。
- **理由**：已有**行为证据** —— 实测 `TRUNC_project_np128` 的答案 **229 字符**、`np64` 为 **107 字符**，**共同前缀 107/107 全等**（`np128 以 np64 为前缀`成立）⇒ 无需再绕一条难自证的算术通道。
- **纪律含义**：**不留待修的钩子** —— 与「未做清单不许含糊成『在做』」同源：字段要么有判据，要么明写死路。

**检测员补记**：`TRUNC` 两份的 `gen_tokens` 为 **`null`**（而 `A2p` 有值 73）⇒ **截断实验的算术通道本来就没值**，**行为前缀对照是唯一可用证据**。这与「放弃 question_tokens」的裁定互证。


### G.50 **G.48 补条**：判据可以在「被修好的那一刻」变成常数 ⇒ 值域必须**每批数据复查**

**lead 2026-10-25 补**：`hit_first_ws` 恒假修好之后，实测 **14/14 全 `true`** ⇒ **它自己成了常数**。
> 这其实是「恒真 / 恒假同族」的**最强形态**：一个判据可以**在被修好的那一刻**变成常数。说明这条纪律不是「写完检查一次」，而是**每换一批数据都要复查值域**。
**检测员落地为三条检查（写入核单模板）**：
1. 每个判据必须报**本批取值分布**（不是「有没有值」，是**各取值各几条**）；
2. 分布若**只有一种取值**，该字段**当批降级为观测值**，不得参与判定；
3. **配对字段必须成对引用**（`hit_first_sentence` / `hit_first_ws` 只引一个 = 没结论；分母必须写出，如「14 条内」）。

### G.51 **臂 F 性质抬高**：它不是基础卫生，是 **M2 验收第 3 条的前置实验**

**§13.4 M2 验收第 3 条原文**（逐字节，实测 **三处**同款）：
| 行 | 原文（节选） |
|---|---|
| **L176** | `插入前后未参与移动的块 0 字节变化。` |
| **L1775** | `\| 验收 \| **3–5 块并发**；对话第 10 轮后插入新块，答案仍正确；**插入前后未参与移动的块 0 字节变化** \|` |
| **L1827** | `\| 1 \| **M2 规划器** \| 3–5 块并发 + 第 10 轮中途插入答案正确 + **未参与移动的块 0 字节变化** \|` |

**推论（lead）**：**若挂载 A 块会改动 B 块的序列化字节，「0 字节变化」永远红 ⇒ 规划器写得再好也过不了。** ⇒ 臂 F **先于**规划器实现。
**执行者须加的列（成本近零，但改变产出性质）**：每个**未参与移动**的块，给出
1. **挂载前 / 挂载后 序列化字节 sha16**；
2. `unchanged`（bool）；
3. 若 `false`：**首个差异字节偏移**。
⇒ 臂 F 的产出由此从「**注入有没有致害**」升级为「**M2 验收第 3 条的可达性证据**」。

**检测员的核法（按新标准，不按旧标准）**：
| 它交上来 | 判定 |
|---|---|
| 只有致害结论、**无未参与块的前后哈希** | **未达标**（不论致害结论多干净） |
| 有哈希但只给「都一致」 | 需见 **`unchanged` 与分母**（几个未参与块 / 几个 true） |
| 有 `false` 但无**首个差异字节偏移** | 未达标（无法定位是填充、对齐还是真内容变化） |

**检测员补一条（lead 未提，但会当场矛盾）**：若要改判据对象，**三处（L176 / L1775 / L1827）必须同步改** —— 它们是同一判据的三次出现，改一处不改另两处，文件就会同时声称两个标准。

### G.52 分支预案（**检测员不预备决定**）

**lead 前置声明**：若臂 F 显示「字节会变」，**那不是实验失败，是发现**。两条路 ——
| 分支 | 内容 | 性质 |
|---|---|---|
| (i) | M2 验收第 3 条改成「**cell 内容** 0 变化」而非序列化字节 | **改判据对象** ⇒ 必须写清为什么（且须同步三处，见 G.51） |
| (ii) | 承认**持久化路径必须改** | 改实现，不动判据 |
**共同约束**：两条都要在**写规划器之前**定。
**检测员的角色边界（按 lead 要求，逐字遵守）**：**不预先选分支、不替 lead 决定**。证据到手后只做两件事：① 判断证据是否足以支撑任一分支；② 指出该分支的**判据可达性**与**同步改动清单**。
**记录在案的理由**：这是「**改对象**」族（与 G.10 的因果方向、G.24 的 judge 替换同族）—— 凡改对象，必须先说明「原对象为什么不再可用」，否则就是拿改口径冒充修好。


### G.53 **分支 (i) 前置条件**：改判据对象前，先确认各副本同义；不同义的先裁定唯一版本，再同步

**lead 2026-10-25 立（检测员实测证实，见 G.54）**：
> **改判据对象前，先确认各副本是否同义；不同义的，先裁定唯一版本，再同步。**
**否则的后果**：「复制同一段文本」去做同步，等于**把三处的标准统一到我随手挑的那一版**，而**哪一版是我们真正想要的，没人议过**；改完的文件会「看起来统一了」，实际是把一个未经讨论的选择**固化成了标准**。
**由此升格**：「**同一判据多副本**」在本文件里是**结构性现象**（M2.5 是 9 处活引用，M2 验收是 3 处副本）⇒ **会复发**，必须有索引而不是每次重新 grep。

### G.54 **一页副本索引**（限定范围：只覆盖接下来要动的三组）

**完备性声明（先说清这一册凭什么可信）**：以**判据特征串** grep 全文取命中 ——
| 组 | 特征串 | 命中行数 | 副本数 |
|---|---|---|---|
| M2 规划器 | `未参与移动的块` | **3** | **3**（无遗漏） |
| M4-C 租约承重 | `断言变红\|断言全红` | 7 | 判据句 **4** + 验收 **2** + 计数锚 **1** |
| M5 两探针 | `两探针\|漏判率\|误判率` | 13 | 判据 **2** + 状态 8 + 依赖序 3 |
⇒ **三组范围内，凡出现判据措辞的行都在下表**；不在此表的行只说「状态/依赖」，不含判据。

#### 组 1 · M2 规划器验收 —— **不同义（3 处，语义级漂移）**
| 行 | 原文 |
|---|---|
| **L175–176** | `**验收**：3–5 块并发；对话进行到第 10 轮后插入一块新记忆，答案仍然正确；` / `插入前后未参与移动的块 0 字节变化。` |
| **L1775** | `\| 验收 \| **3–5 块并发**；对话第 10 轮后插入新块，答案仍正确；**插入前后未参与移动的块 0 字节变化** \|` |
| **L1827** | `\| 1 \| **M2 规划器** \| 3–5 块并发 + 第 10 轮中途插入答案正确 + **未参与移动的块 0 字节变化** \|` |
**差在哪（三条，两条是语义级）**：
1. **时间窗口**：L1827 **缺「插入前后」** ⇒ 字面禁止**任何时候**发生字节变化（含正常写入 / 换页 / 重建）⇒ **L1827 更严**（lead 指出）。
2. **插入时点不同**：L176 / L1775 是「第 10 轮**后**插入」，L1827 是「第 10 轮**中途**插入」⇒ **这是两个不同的事件**，不是措辞问题。
3. **插入对象粒度不同**：「插入**一块新记忆**」/「插入**新块**」/「插入」。

#### 组 2 · M4-C 租约承重 —— **不同义（且 L1828 按字面恒红）**
| 行 | 原文 |
|---|---|
| **L130** | `判据=「删掉它必须有断言变红」，不是「加上调用」` |
| **L763** | `直接推出 M4-C 的判据「**删掉它必须有断言变红**」。` |
| **L922** | `**判据**：**「删掉它必须有断言变红」**，不是「加上调用」。` |
| **L1755** | `\| 判据 \| **删掉它必须有断言变红**（不是「加上调用」） \|` |
| **L1757** | `\| 验收 \| ① 四条承重断言全红可复现 ② 恢复后全绿 ③ 三份 session 剔除 `saved_at` 后 sha 仍 `fa94b1bc58c0e421` \|` |
| **L802** | `\| 三份 session 剔除 `saved_at` 后 sha \| `fa94b1bc58c0e421`（全等） \|` |
| **L1828** | `\| 2 \| **M4-C 租约承重** \| **删掉租约 ⇒ 四条断言变红**；恢复后全绿；`fa94b1bc58c0e421` 不变 \|` |
**差在哪（判据句同义，验收句不同义）**：
- **判据句**（L130 / L763 / L922 / L1755）**逐字节同义** —— 「删掉它必须有断言变红，不是加上调用」，仅引号与括号形式不同 ⇒ **这一组无需裁定版本**。
- **验收句**：L1757 / L802 都带「**三份 session 剔除 `saved_at` 后**」，**L1828 丢了全部三个限定**（三份 / 剔除 / 后）⇒ 只剩「`fa94b1bc58c0e421` 不变」。
- ⇒ **L1828 按字面执行恒红**：该常数是「剔除 `saved_at` 后」的 sha，**原始字节永远不会等于它**（每次保存 `saved_at` 都在变）。**不是判据太严，是这一副本丢了限定语。**

#### 组 3 · M5 两探针 —— **不同义，且 L1829 把 (a) 的判据套到了 (c) 上**
| 行 | 原文 |
|---|---|
| **L1765** | `\| `(a)` 换措辞 \| … \| 预登记若干改写对，**漏判率**与**误判率**分别报（不报单一「准确率」） \|` |
| **L1766** | `\| `(c)` 长生成 \| … \| 逐句判定，按句统计；边界 1（张冠李戴不管）保持不动 \|` |
| **L1767** | `\| 共同 \| 不许改判据去迁就结果（纪律 26/28） \| 判据变更须标方向：放松 / 收紧 / 改对象 \|` |
| **L1829** | `\| 3 \| **M5 两探针 (a)/(c)** \| 改写对与长生成的**漏判率/误判率分别报**；判据变更须标方向 \|` |
**差在哪（三条，第一条是改对象级）**：
1. **L1829 把 `(a)` 的判据（漏判率/误判率）套到 `(c)` 上**；而 `(c)` 的判据在 L1766 是「**逐句判定，按句统计**」—— **两者不是同一种量**。这是**改对象**，不是措辞简化。
2. **L1829 丢了「预登记若干改写对」** —— 预登记是防事后挑选改写的唯一约束（与 G.31 同源），丢掉等于放开这道闸。
3. **L1829 丢了「边界 1（张冠李戴不管）保持不动」** —— 边界声明消失后，`(c)` 的结论可被任意扩张解释。
4. L1829 保留「判据变更须标方向」**与 L1767 一致** ⇒ 这一条无漂移。

### G.55 「**恒红**」也归入 G.37 / G.48 同族（第三个形态）

G.37 立的是 **恒真**（`touched_cap`）、G.48 立的是 **恒假**（`hit_first_ws`）；本轮发现**第三种**：
> **恒红** —— L1828 字面（`fa94b1bc58c0e421` 不变，却不提剔除 `saved_at`）**永远不可能通过**。
**三者同族**：**不随数据变化的判据都不是判据** —— 恒真不区分案例，恒假不区分案例，**恒红同样不区分案例**（它对好坏两种输入都红）。
**检测员补的检查项**：核判据时除了「能否红」，还要问「**能否绿**」 —— **一个永远红的判据比一个永远绿的判据更危险**：它会被当成「活干完了但不达标」，从而掩盖「判据本身写错」。


### G.56 臂 F：**承重成立**，且「整次挂载」粒度有产物佐证

**lead 2026-10-25 认定**：注入层 24 ⇒ `moved=0`、rc=4、不可读；**负对照（env 在但不匹配任何层）rc=0、`moved` 与答案逐字节等同对照** ⇒ **致害可归因于注入本身**。
> **这条负对照是整臂的关键** —— 没有它就是「改了个东西然后坏了」。
**检测员独立佐证（产物侧）**：`F_inject_L24_project.json` 的 `placed` 是**空数组**（0 块 / 0 cell），而 `F_control` 与 `F_neg_L999` 都是 **4 块 / 70 cell / deltas 4075,4014,3956,3885**。
⇒ **拒绝发生在挂载阶段，整个挂载没有落地一块** ⇒ 与执行者自述的「观测粒度是**整次挂载**而非单块」**完全吻合**。**文档里不得缩写成「某块读不出来」** —— 那会把粒度改小一个量级。

### G.57 **FINDING**：M2 验收第 3 条 **迄今没有可测对象**（不是「测了没过」，是「没有实例」）

**执行者报 + lead 推一步 + 检测员全量复算**：
| 项 | 实测 |
|---|---|
| 含 `placed` 的产物 | **27 份** |
| `placed` 条目 | **103 条** |
| 出现过的 `delta` | **仅四个**：4075 / 4014 / 3956 / 3885 |
| `delta = 0` 的条目 | **0 条** |
| `base` 的取值 | **仅 0**（103/103） |

**机械证明（这条比「没观察到」强）**：
> 因为 **`base ≡ 0`**，所以 **`delta = target − base = target`** ⇒ **`delta = 0` ⟺ `target = 0`**。
> 现布局里最低 `target` 是 **3885 > 0** ⇒ **任何块都不可能是「未参与移动的块」**。
⇒ **只要所有块都以 `base=0` 保存，就永远不可能出现未移动块；要造出来，唯一的办法是把某块放在 `target=0`（最底部）并让它留在原位。**

**⇒ 记成独立 finding**：**M2 验收第 3 条「插入前后未参与移动的块 0 字节变化」从来没有可测对象。**
**⇒ 并进副本索引（G.54 组 1 补判读档）**：该判据**三处副本**（L176 / L1775 / L1827，其中 **L1827 缺「插入前后」限定、更严**）**+ 现状说明「迄今无实例」**。
**⇒ 引用规矩**：凡引用这条验收，**必须同时写「迄今无实例（103 条 placed / delta 集为 {4075,4014,3956,3885} / base ≡ 0）」** —— 否则读者会以为它已被验证通过。

### G.58 预案补 **(0) 档：判据无实例**（排在 (i)/(ii) 之前）

**lead 2026-10-25 重新措辞，检测员照录**：
> 在讨论「字节会不会变」之前，先要有一个「**不会动的块**」。而这样的块现在不存在。
| 档 | 内容 | 性质 |
|---|---|---|
| **(0)** | **判据无实例** | **既不是可达、也不是不可达，而是无法评估** |
| (i) | 改判据对象（序列化字节 → cell 内容） | 改对象，须写清为什么 + 三处同步（G.51/G.53） |
| (ii) | 承认持久化路径必须改 | 改实现，不动判据 |
**为什么 (0) 必须排在前面**：**拿没有实例的判据去验收，会得到一个永远绿的假象**（没有任何一次运行会让它红）。

### G.59 G.48 第三形态：**「无实例」与恒真、恒假同族**

| 形态 | 实例 | 为什么不随数据变化 |
|---|---|---|
| 恒真 | `gen_tokens >= n_predict`（`touched_cap`） | 分子含问题 token ⇒ 几乎必真 |
| 恒假 | `hit_first_ws`（`\s+` 正则写错） | 正则永不匹配 |
| **无实例** | **M2 验收第 3 条** | **没有任何输入能进到这个判据里** |
| 恒红 | L1828 字面（丢「剔除 `saved_at`」限定） | 原始字节永不等该常数 |
⇒ **四者同族：都不区分任何案例。** 判据的有效性 = **在同一批数据里「能红」且「能绿」且「两类取值都出现过」**。

### G.60 臂 D 性质升级：从「可选对照」→ **M2 验收的前置装置**

**理由（lead）**：**它是制造「未参与移动的块」的唯一手段** —— 与 G.57 的机械证明一致：只有把某块放在 `target=0` 并让它留在原位，才存在 `delta=0` 的块。
**执行顺序**：先跑**跨布局对照**；臂 D 跑不跑、排在哪，**等那份报告后由 lead 定**。

### G.61 §16 **结案**

执行者按 **146–367（222 行）**复跑：**222/222、SRC-ONLY 0、COPY-ONLY 19**（非空 15 = 章标题 1 + 导语 13 + `---` 1）。lead 自己对齐一致（lead 多取 368 那个空行，执行者纠正得对）。
**⇒ §16 PASS，结案。** 检测员此前独立结论（222 行 / L2102–L2323 / T3=0 / T4=0 / 逐行全等）与之**一致，无保留意见**。


### G.62 **纪律**：摘要表的验收必须逐行对权威小节 —— 数行数只证明行数

**lead 2026-10-25 自报一处错**：验收 §13.9 时只核了**形状**（编号 1..4 连续、`grep 五项`=0、§12.1 16→15、标题「四项」与 4 行自洽）——
> **全是形状。一行内容都没对权威小节核过。**
**立为纪律**：**摘要表（「一页可核」这类）的验收必须逐行对权威小节，数行数只证明行数。**
**与既有几条组成一组**：
| 条 | 内容 |
|---|---|
| 本条 | **形状自洽 ≠ 内容正确** |
| G.53 | **副本存在 ≠ 副本忠实** |
| G.40 | **尺子变短 ≠ 比对通过** |
| G.59 | **判据存在 ≠ 判据有值域** |
**检测员补**：摘要表的正确核法是**双向**的 —— ① 摘要每一行能在权威小节里找到出处；② 权威小节的每个交付项都在摘要里出现（**丢项**只有反查才能发现，本轮 L1828 丢限定、L1830 丢交付项都是反查出来的）。

### G.63 L1829：**比「改对象」更硬的理由（lead 给出，检测员照录）**

> `(c)` 要回答的是「长生成里会不会出现**部分正确 + 部分编造**」。**漏判率 / 误判率是二值判定的产物，量不出「一句话里一半对一半编」。** 所以这不是简化，是**用一把量不出该量的尺子替换了原来那把**。
**检测员补一句可用判据**：判断「改对象」还是「简化」，看**被换掉的量纲**能否表达原问题 —— 原问题是**逐句标度**（部分对/部分编），替换后是**二值计率** ⇒ **量纲不存在**，故属改对象。

### G.64 副本索引 · **组 4（M1.8 三处 judge 冲突）—— 也漂了**

**权威副本（§13.5 L1785）**：
> `\| 验收 \| 三处冲突各自给出「**谁是权威 + 另两处如何改**」，并有一致性断言 \|`
**摘要副本（§13.9 L1830）**：
> `\| 4 \| **M1.8 三处 judge 冲突** \| 三处冲突各自给出权威来源 + 一致性断言 \|`

**差在哪（两处，第二处可反向解读）**：
1. **丢一整个交付项**：权威版的「**另两处如何改**」在摘要版**完全消失** ⇒ 按摘要验收，**三处各自有来源就算过，即使它们仍然互相冲突** —— 判据的**目的（统一）**没了。
2. **「谁是权威」→「权威来源」**：前者是**在三处中指定唯一权威**，后者可被读成「**每处各自引用自己的来源**」⇒ **该替换允许相反的执行**。

**完备性**：`grep 谁是权威\|另两处如何改\|一致性断言` 全文命中 **仅 2 行**（L1785、L1830）⇒ M1.8 判据**只有 2 处副本**，已全部在本表；其余 `M1.8` 命中（L120 / L146 / L1629 / L1838 / L1960）均只说**状态或欠账**，不含判据。

**⇒ 组 4 结论：与组 1（M2）、组 2（M4-C）、组 3（M5）一样，摘要副本不忠实；四组全漂。**
**分支 (i) 的同步清单因此不是 3 行、是 4 组；且四组都必须先做「同义裁定」再做同步（G.53）。**

### G.65 组 2 / 组 3 的 lead 复核（照录，检测员无异议）

- **L1828 恒红**：§13.2 L1757 权威 —— `③ 三份 session 剔除 `saved_at` 后 sha 仍 `fa94b1bc58c0e421``；L1828 把 ③ 的限定**全部丢掉**，而 `saved_at` **每次保存都变** ⇒ **照副本验收，sha 永远不可能不变 ⇒ 恒红**。
- **L1829 改对象**：§13.3 —— `(a)` 漏判率/误判率分别报；`(c)` **逐句判定、按句统计**，边界 1 不动。L1829 把两者并成「漏判率/误判率分别报」，**(c) 的判据整个消失**（理由见 G.63）。


### G.66 排期裁定：**第 4 行（M1.8）与前三行同批改**

**lead 2026-10-25 裁定**，理由照录检测员原句并被 lead 单独拎出立为原则：
> **前三组最多让人白干（假红），这一组会让人在没有统一 judge 的情况下宣布 M1.8 通过（假绿）。**
⇒ 由此产出**通用严重度序**（已置于纪律区最前，见上）：**假绿 > 假红 > 无实例 > 无判据**。

### G.67 **纪律**：摘要表核对**必须双向** —— 「逐行对」只覆盖一半

**lead 2026-10-25 定**：他原话是「摘要每行对权威小节」= **正向**；检测员补的「**权威小节每个交付项都在摘要里出现**」= **反向**。
> **这两次漂移（L1828 丢限定、L1830 丢交付项）都是反查才出来的** —— 正向从摘要出发，**天然看不见「摘要里根本没有的东西」**。
⇒ **立规矩时写「必须双向」，不要写「逐行对」** —— 后者听起来很严，**实际只覆盖一半**。
**补条（lead 2026-10-25）—— 与「双向」并列**：
> **对照物必须指向被判对象本身。** 拿「行数对」去证明「每行内容对」，**对照物齐全也照样是未核**。
**⇒ 对照物分两类，只有第二类算核过**：
| 类 | 例 | 能证明什么 |
|---|---|---|
| **形式对照物** | 编号连续 / `grep` 归零 / 标题与表 4↔4 / 字节数 | 只证明**形状**，不证明内容 |
| **实质对照物** | 权威小节原文逐项 / 行号+字节串 / 锚 sha16 / 计数与分母 | 证明**被判对象本身** |
**lead 据此撤回一个结论（照录，不得当作已完成结论引用）**：此前对用户说过文档「零红」—— **那句话是错的**，因为它给的全是**形式对照物**。
> **新口径**：**§13.9 修完并逐行核过之前，文档不得声称零红。**
**检测员落成可执行清单**：
| 方向 | 检查 | 本轮发现 |
|---|---|---|
| 正向 | 摘要每一行能在权威小节找到出处 | 四条全找到（**因此正向判「没问题」**） |
| **反向** | **权威小节每个交付项都在摘要里出现** | **L1830 丢「另两处如何改」、L1828 丢「剔除 `saved_at` 后」** |

### G.68 待核项：§13.9 标题下的**摘要声明行**（执行者尚未落）

**lead 要求加的一行（在标题下）**：
> `本表是摘要，不是权威。判据的权威版本在 §13.2/§13.3/§13.4/§13.5；不一致时一律以各小节为准。`
**理由（照录）**：**这行不能阻止漂移，但能让漂移不再致命。** 现在这四条是靠人肉一次一次查出来的；只要表还自称「一页可核」却不说自己是摘要，**下次漂移仍然只能靠人肉发现**。

**检测员的核法（三条，全部为形式要件）**：
1. **位置紧贴标题** —— 必须在 `### 13.9` 之后、表头之前；**挨在表后等于没写**，读者看到表时已经晚了。
2. **措辞须含三要素**：自称**摘要/非权威** + 指明**四个权威小节** + **冲突时以各小节为准**。
3. **不得用它替代修四行** —— 声明只降低再犯代价，**不解除四组的同义裁定与同步（G.53）**。
**当前实测（sha16 `ca47029db03b0561`，核前核后同值）**：L1823 = `### 13.9 按依赖序的四项与各自验收判据（一页可核）`，**L1824 为空行、L1825 即表头** ⇒ **声明行尚未落地**；四行内容亦仍为漂移版。⇒ **记为未完成，等派单结果。**

### G.69 「像样的动作」型错账（lead 自报两次，已入纪律区最前）

| # | 动作 | 实际 | 后果 |
|---|---|---|---|
| 1 | 「把标题**降一级**」 | 实现成**去掉一个 `#`**，方向反 | 得 147/165 **假红** |
| 2 | 「**验收** §13.9」 | 只核编号连续 / `grep` / 行数自洽 | **一行内容没对权威小节核过** |
**共性**：**用一个看起来严的动作，覆盖了一件没真的去看的事。**
**纪律**：**「做了一个像样的动作」不等于「核过了」；核过的唯一证据是逐项给出对照物。**
**检测员补一条自查口子**：凡我的回报里出现「已核 / 已对齐 / 已复算」而**后面没有对照物（行号、锚、字节串、计数与分母）**，那句话按**未核**处理。**这条对我自己也生效。**

### G.86【**执行者代记** · 与检测员 G.86 撞号，见 G.90】执行者回报：三条读数 + 一处自报 bug + 关闭 G.68

| # | 事实 | 证据（可复核） |
|---|---|---|
| 1 | **`hit_first_ws` 曾恒假** —— 我写成 `re.sub(r"\\\\s+", …)`（raw 串里两个反斜杠），匹配不到任何东西 ⇒ `ws_only` 从不点亮。已改为 `r"\\s+"` | 修前 14 份产物 `hit_first_ws` 全 `false`；修后离线重算（未跑 GPU、未改答案）：`both 9 / ws_only 5 / tail_only 0`。错值保留在 `hit_relation_prev_buggy`，**修正本身也是证据** |
| 2 | **恒假与恒真同族，第三形态是「无实例」**（G.59 已记）—— 我这台是恒假的实例：**判据从未亮过一次就报了读数** | 同上 |
| 3 | **§13.9 标题下的摘要声明行已落**（关闭 **G.68**） | `PROGRESS-AND-ROADMAP.md` sha16 `4fd3bf5d576618ea` / 187,199 B / 2,463 换行；该行文本：`> **本表是摘要，不是权威。** 判据的权威版本在 §13.2 / §13.3 / §13.4 / §13.5；**本表与各小节不一致时，一律以各小节为准。**` |
| 4 | **M2 第 3 条：跨布局实测 3/3 unchanged**（`iso_no_car` 51 vs `iso_car_back` 70；home/project/habit 目标位同为 4075/4014/3956） | home `pre 1bf4f04ac7f58166 → post f668894e58299903` 两布局**逐字节相同**；project `536eac03f288bb09 → 861bc8d4c8376c50`；habit `337b7b60a263e0a3 → a1d9bf13ef568758`。**限定：这是「不被别的块牵连」，不是「存在从不被搬的块」** |
| 5 | **同一布局内「自己移动前后」欠账已还**：`repos_local` 前后字节**不同**，首个差异在**头部**（home 偏移 104 / project 92 / habit 68，均 < 头部 1188 B），差异字节约 **48.4–48.8%** | 块几何：头部 1188 B + 每 cell 104464 B；三块长度 2,194,932 / 1,881,540 / 1,254,756 与其 cells 21/18/12 一致 |

**纪律（提请入纪律区，与 G.37 / G.48 / G.59 并列）**：**任何新判据落盘前，必须构造一个必然触发它的案例并跑通；跑不出触发案例，它只是字段，不是判据。**
**附**：`placed` 的分母口径 —— 我只统计 `kvmem/m2_visibility/m14b_e10_probe/out/` = **28 份产物 / 110 条 `placed`**（`base≡0`、`delta ∈ {3885,3956,4014,4075}`、无 `delta=0`）。lead 记的是 **103**；两个数**应并列并标注统计范围**，不互相覆盖。


### G.70 **反向依赖登记**（谁被摘要表引用为「权威」）

**lead 2026-10-25 指出**：§13.9 的声明行点了 §13.2/13.3/13.4/13.5 四个小节 ⇒ 就要求这四个小节**确实各自是权威**。
> 若哪一天某小节被删或被改挂到别处，声明行会变成一句**指错路的导航**。
> **这比「谁抄了谁」更要紧 —— 抄错会红，指错路会让人找不到该信哪一版。**

**实测（本轮）**：四个权威小节**全部存在且各有独占内容**：
| 小节 | 行 | 内容 |
|---|---|---|
| §13.2 M4-C | **L1751** | 判据 / 具体做法 / 验收 ①②③ / 依赖 / 风险 |
| §13.3 M5 两探针 | **L1761** | (a) / (c) / 共同三行 |
| §13.4 M2 规划器 | **L1769** | 接口 / 四个子问题 / 验收 / 依赖 / 现状 |
| §13.5 M1.8 | **L1779** | 内容 / 现状 / 验收 / 并行性 |
**检查项（列入日常）**：**凡改动 §13.2–§13.5 中任一小节、或 §13.9 声明行，必须同步复核声明行指向的四个锚点仍然存在** —— 否则声明行静默失效。

### G.71 反向完备性**普查**（限定范围，一页）

**范围定义（lead 给）**：只查「带判据/验收的摘要表」对各自权威小节的反向完备性；**不查纯事实表**；**只报丢项，不报措辞差异**。

**候选筛选（按关键字 `可核 / 一览 / 汇总 / 按依赖序 / 清单` 全量命中后逐条判定）**：
| 表 | 行 | 自称 | 判定 |
|---|---|---|---|
| §3.8 全项目数字门槛一览（25 条） | **L345** | 「一览」 | **排除**：内容是**数字 + 出处**，属纯事实表（lead 明示排除） |
| **§13.9 四项验收判据** | **L1823** | 「按依赖序」「一页可核」 | **唯一合格候选** |
| §12.1 未闭项 `F-*` 清单（九条） | **L1608** | 「清单（**九条**）」 | 非本轮范围（不含验收判据），但**带计数断言** ⇒ 已单独反查，见下 |
| §12.2 / §12.3 / §12.5 | L1643 / L1659 / L1714 | 状态或分类 | 排除（不含验收判据） |
| §17 附录 B | L2329 | 照录 | 不属本轮（另有 LCS 判法） |

**§12.1 计数断言反查结果：成立** —— 表 16 行 = F-\* 编号 **11** + 未编号 **5**；11 条中已闭 **F-M3-6 / F-M3-7** ⇒ **未闭 9 条**，与标题「（九条）」一致（G.34 已记）。

#### §13.9 反向完备性（对四个权威小节逐项；只报丢项）
**A. 整项消失（4 条）**
| # | 权威出处 | 消失的交付项原文 | 现表 |
|---|---|---|---|
| 1 | §13.3 L1766 | `逐句判定，按句统计` | L1829 **无** |
| 2 | §13.3 L1766 | `边界 1（张冠李戴不管）保持不动` | L1829 **无** |
| 3 | §13.3 L1765 | `预登记若干改写对` | L1829 **无** |
| 4 | §13.5 L1785 | `另两处如何改` | L1830 **无** |
**B. 限定丢失（4 条，项在、限制没了）**
| # | 权威出处 | 丢掉的限定 | 现表 |
|---|---|---|---|
| 1 | §13.2 L1757 ① | `可复现` | L1828 无 |
| 2 | §13.2 L1757 ③ / L802 | `三份 session` + `剔除 `saved_at` 后` | L1828 无（⇒ 恒红，G.54） |
| 3 | §13.4 L1775 | `插入前后` | L1827 无（⇒ 更严，G.54） |
| 4 | §13.3 L1765 | `（不报单一「准确率」）` | L1829 无 |
**C. 时点替换（1 条，非丢项，单列以免被算进 B）**：§13.4 「第 10 轮**后**插入」→ L1827 「第 10 轮**中途**插入」⇒ **换了一个事件**。

#### 普查结论（一页）
> **全库只有 1 张表属于「带验收判据的摘要表」（§13.9）；该表 4 行中 3 行有丢项（L1829 三条、L1830 一条），另 2 行有限定丢失（L1827 / L1828）。§12.1 的计数断言反查成立。**
**⇒ 范围可控**：不必全库翻。**⇒ 但结论是「唯一那张表几乎每行都缺东西」** —— 这不叫范围小，这叫**资产负债表上唯一一栏就写错了**。


### G.72 两口径**并存**记法（103/27 与 110/29 都对：时间差，不是口径分歧）

**检测员实测（本轮，两次扫描间隔数小时）**：
| 范围 | 含 `placed` 文件 | 条目 | `delta=0` | `base≠0` | `delta` 取值 |
|---|---|---|---|---|---|
| `m14b_e10_probe/out` | **29** | **110** | **0** | **0** | **四个**：3885:26 / 3956:28 / 4014:28 / 4075:28 |
| `kvmem` 全仓 | **53** | **188** | **0** | **0** | **九个**：3885:29 / 3886:5 / 3892:4 / 3956:40 / 4014:38 / 4045:10 / 4057:10 / 4075:50 / 4078:2 |
**求和校验**：29+5+4+40+38+10+10+50+2 = **188** ✓（与条目数一致，无重复计数）。
⇒ **检测员先前 27 份 / 103 条是同一扫描脚本在产物落齐前跑的** —— **两个数都对**，文档应「数与范围」一起给，**不必互相覆盖**。

**⚠ 由 lead 立的一条表述纪律**：
> **「`delta` 只有四个值」只在 probe 范围内成立。** 全仓是九个值。**这句话若进文档，任何人扫一遍 `kvmem` 就能推翻 —— 而推翻它的代价不是那句话，是读者顺手认定「无实例」整个结论也不可靠。**
> ⇒ **别把真结论架在换口径就塌的旁证上。**
**⇒ 承重的只有两条（两口径皆然）**：**`delta=0` 零条**、**`base ≡ 0`（110/110 与 188/188）**。
**检测员补一句可移植的判法**：凡在文档里写「取值只有 N 个」这类**封闭断言**，必须同时写**扫描范围**；**范围不写 = 声称全称**，而全称断言最容易被一次 grep 推翻。

### G.73 §13.9 改后核单（检测员独立复核，sha16 `ca47029db03b0561` 前后同值）

**声明行位置**：**L1824 空行 / L1825 声明行 / L1826 空行 / L1827 表头** ⇒ **紧贴标题、在表头之前** ✓ **合规**。文字：「**本表是摘要，不是权威。** 判据的权威版本在 §13.2 / §13.3 / §13.4 / §13.5；**本表与各小节不一致时，一律以各小节为准。**」⇒ **三要素齐全** ✓。

**lead 交办的三项，逐条结论**：
| # | 要求 | 结论 | 证据 |
|---|---|---|---|
| ① | 两个口径的数都在且标注清楚 | **未满足** | L1829 **只有 probe 口径**（110 条）；**全仓 53 份 / 188 条 / 九个值 完全未出现** |
| ② | `delta=0` 零条 | **满足** | L1829 含「**无 `delta=0`**」，且我两口径复算均 0 |
| ③ | 「delta 只有四个值」整句**已删** | **未满足** | L1829 **原句仍在**：「`delta` 只有四个值 4075·4014·3956·3885」（未限定范围 ⇒ 读作全称） |

**四行对权威小节逐项复核（我侧，替代 lead 的目视）**：
| 行 | 权威 | 我侧结论 | 残留 |
|---|---|---|---|
| L1829 M2 | §13.4 L1775 | **已忠实**：3–5 块并发 ✓ / 第 10 轮**后**插入 ✓（时点漂移已修）/ **插入前后** ✓ | 附注的「四个值」问题（上表 ③） |
| L1830 M4-C | §13.2 L1757 | **已忠实**：四条**承重**断言全红**可复现** ✓ / 恢复后全绿 ✓ / **三份 session 剔除 `saved_at` 后** sha 仍 `fa94b1bc58c0e421` ✓ | 无 |
| L1831 M5 | §13.3 L1765–1767 | **基本忠实**：`预登记改写对` ✓ / 漏判率与误判率分别报 ✓ / `(c)` **逐句判定、按句统计** ✓ / 边界 1 保持不动 ✓ / 判据变更须标方向 ✓ | **仍缺**「（不报单一「准确率」）」 |
| L1832 M1.8 | §13.5 L1785 | **已忠实**：「**谁是权威 + 另两处如何改**」✓ + 一致性断言 ✓ | 无 |
⇒ **我此前普查报的 4 条整项丢失：4/4 已修**；**4 条限定丢失：3/4 已修**，剩 **「不报单一「准确率」」**（属 G.71 B-4）。
⇒ **时点替换（G.71 C）已修**（现为「第 10 轮**后**」）。

**与 lead 结论的唯一差异**：lead 判「其余部分逐字核过 ✓」；**检测员判 ① 与 ③ 未满足、并多报一处残留限定**。按 lead 规则「若不一致以检测员的为准并报他」⇒ **已报**。


### G.74 **FINDING**：限定语就是判据的一部分 —— 丢掉「插入前后」四个字，验收对象就换了

**lead 2026-10-25 自我更正（检测员照录，并**同错自报**）**：
> §13.4 权威写「**插入前后**未参与移动的块 0 字节变化」—— **「未参与移动」由「这次插入」限定**。拿「有没有 `delta=0` 的块（**从不**被搬）」去回答它，**那是另一个命题**。
| 命题 | 真假 |
|---|---|
| 「**没有一块 `delta=0`**」（绝对口径） | **真**（probe 110 / 全仓 188，皆零） |
| 「**所以 M2 验收第 3 条无法评估**」 | **假** —— **事件口径下它有实例** |

**错法归类（lead 自我归类）**：**把「块的问题」当成「臂的问题」** —— 与 7B「home 0/5 vs project 5/5」那次的**块间 / 臂间混淆同型**。这次是**「从不被搬」与「不因本次插入而搬」两个命题被合并**。

**检测员的同错自报（必须记，因为我的那份「证明」是这条错误推论的支柱）**：
- 我给出过「**`base ≡ 0` ⇒ `delta = target` ⇒ `delta=0` ⟺ `target=0`**」的机械证明，并称它把「无实例」从观察升级为**结构必然**。
- **那条数学是对的，对象是错的**：它回答的是「**是否存在从不被搬的块**」（绝对口径），**不是**「**本次插入后有没有块位置没变**」（事件口径）。
- ⇒ **我用一条真事实去支撑了一个与它无关的判据**。这与我此前的「以偏概全」同型：**证据为真，指涉错位**。**G.57 必须加限定（见 G.75）。**
> **结论（立为纪律）**：**限定语不是修饰，是判据的一部分 —— 删掉限定，判据对象就换了，而且换得看不出来。**
> **它与「L1827 缺『插入前后』四个字」是同一件事的两面**：**副本缺字，导致判据被读成另一个命题 —— 这不是巧合。**

### G.75 **G.57 加限定（正是订正）**

**原文（G.57）**：「M2 验收第 3 条 **迄今没有可测对象**」。**此句只对绝对口径成立，对本条不成立。**
**订正后口径（今后引用一律用这条）**：
> **「不存在从不被搬的块」（绝对口径，`delta=0` 零条，probe 110 / 全仓 188 皆零）—— 这是持久化 / 布局的性质。**
> **「M2 验收第 3 条无实例」—— 不成立。事件口径下它有实例。**
**⇒ 引用规矩更新**：用「无实例」时必须同时写口径（**绝对 / 事件**）；**不得让读者以为 M2 这条到现在还没法验**。

### G.76 28 vs 29 结案（两个都对）

| 数 | 定义 | 实测 |
|---|---|---|
| **29** | 含 `placed` **键**的文件数 | 29 ✓ |
| **28** | `placed` **非空**的文件数 | 28 ✓ |
| 差的那一份 | **`F_inject_L24_project.json`**（`placed` 为空数组，注入臂整次挂载被拒 —— G.56） | 实测唯一条空数组 ✓ |
⇒ **文档用 28 / 110 + 半句说明**（lead 裁定）。

### G.77 臂 D 裁定：**不跑**（就 M2 而言）

**理由（lead）**：事件口径已过 ⇒ **M2 不需要 `delta=0` 的块**；绝对口径是**持久化路径的性质**，**不是规划器的性质**。⇒ **臂 D 降为可选卫生项**（与 G.60 的「前置装置」定位相比是**下调**，以本裁定为准）。

### G.78 待核：L1829 新版（**实测仍是旧版**）

**实测（本轮）**：L1829 = 「…（**迄今无实例 ⇒ 本条无法评估**：110 条 `placed` 中 `base≡0`、`delta` **只有四个值** 4075·4014·3956·3885、**无 `delta=0`**；权威见 §13.4）」⇒ **旧版未改**。
**核单（四项，含 lead 新增第 4 项）**：
| # | 要求 | 现状 |
|---|---|---|
| ① | 两个口径的数都在且标注清楚（110/probe 与 188/全仓） | **未满足**（只有 probe 口径） |
| ② | `delta=0` 零条 | **满足** |
| ③ | 「`delta` 只有四个值」整句**删除**（不是留成参考值） | **未满足**（原句仍在） |
| **④（新）** | 判据表述**须与 §13.4 的事件口径一致**，不得残留绝对口径 | **未满足**（现文「无法评估」正是绝对口径的结论） |

### G.79 **FINDING（新，与本轮引用相反）**：`M2S3` 的 `block_bytes` 读数不是「3/3 unchanged」，而是**逐块全 `false`**

**lead 转述的读数**：「执行者的**跨布局实验（3/3 unchanged）**就是它的读数」。
**检测员实测（唯二含 `unchanged` 字段的 M2 产物）**：
| 产物 | 块数 | `unchanged_by_own_repos` | pre/post `sha16` | 字节数 |
|---|---|---|---|---|
| `M2S3_no_car_project.json` | 3 | **false × 3** | **全部不同**（如 slot1 `1bf4f04ac7f58166` → `f668894e58299903`） | **同长**（2,194,932） |
| `M2S3_car_back_project.json` | 4 | **false × 4** | **全部不同** | **同长** |
⇒ **读数是「repos 之后序列化字节变了（同长、异哈希）」—— 方向与本轮引用的「unchanged 3/3」相反。**

**三点必须由执行者回答（对照物须直指被判对象）**：
1. 「3/3 unchanged」读的是**哪个字段、哪份产物**？（我在 `m14b_e10_probe/out` 与全 `kvmem` 的 597 份 json 里，含 `unchanged` 的只有 23 份，M2 相关的只有上面两份，**且全 false**）
2. 若它读的是**事件口径**（只统计本次插入未移动的块），**那 3 个块分别是哪 3 个**，`slot` 与 `delta` 各是多少？
3. **同长异哈希**本身是什么？**填充 / 时间戳 / 重转有损**？—— 这三种对分支 (i)/(ii) 的结论完全不同（G.52）。

**⇒ 检测员判**：**在回答 (1) 之前，「3/3 unchanged」不能作为 M2 验收第 3 条已通过的依据**；而这条读数若成立方向相反，**它就是分支 (ii)（持久化路径必须改）的候选证据**，须立刻上报，不得并入「已过」。


### G.80 争议结案：**两句话并行成立，量的是不同东西**（lead 逐字节核过，检测员独立复算一致）

**两句都对，且都不是错读**：
| 命题 | 读数 | 谁读的 |
|---|---|---|
| **同布局内**（自己挪之前 → 挪之后）：字节**变了** | `unchanged_by_own_repos` = false，**3/3** | **检测员**（读字段） |
| **跨布局**（有 car ↔ 无 car）：字节**一模一样** | slot1–3 的 pre/post 哈希两布局**完全相同**，**3/3** | **执行者**（并排比两份产物） |

**检测员的独立复算（本轮，逐 slot 三字段）**：
| slot | `pre_eq` | `post_eq` | `bytes_eq` |
|---|---|---|---|
| 1 | true | true | true |
| 2 | true | true | true |
| 3 | true | true | true |
⇒ **`allPreEq = true` / `allPostEq = true` / 字节数亦相等** ⇒ lead 的跨布局读法**成立**。

**为什么「跨布局」才是本条的对象**：§13.4 的上下文是「**对话第 10 轮后插入新块**；**插入前后**未参与移动的块 0 字节变化」⇒ **「插入前后」= 插入这一块的前 / 后**，**不是「自己挪之前 / 之后」**。
⇒ **跨布局比较是正确的操作化**；同布局比较回答的是**另一个问题**（`repos_local` 是否有损）。
> **两个读数都要留，但绝不能互相顶替。**

### G.81 **「读数不存在」≠「读数没落盘」**（lead 要求写入，检测员认为这是本轮最有用的一句）

**本次争议的准确成因**：**那个结论本来就没有字段** —— 跨布局相等是**从两份产物推导出来的**，不是存下来的。
| 情形 | 表现 | 处理 |
|---|---|---|
| **读数不存在** | 产物里没有这个量 | 重做实验 |
| **读数没落盘**（本次） | 量**能算**，但**没人存**；审计者只能手工重构 | **补字段**，不必重做 |
**⇒ 检测员原问「3/3 读的是哪个字段」把两者混在一起了**；正确表述是「**这个结论没有对应字段，它是推导量**」。
**⇒ 由此立规矩（已由 lead 派给执行者）**：**推导出来的读数必须落成字段**；不落字段的结论下一轮必然再被质疑一次，且**每次质疑都要重算**。

### G.82 执行者待办三条（照录）
1. **把跨布局比较落成字段**：`across_layouts: { compared_with: "M2S3_no_car_project.json", per_slot: [{slot, pre_eq, post_eq}] }` 或等价结构。**没落成字段的读数，下一轮还会有人找不到。**
2. **L1829 措辞弱化为准确写法**（见 G.83），**不得把「两布局逐字节相同 = 3/3」单独成句** —— 它省略了「两种布局都有自身重转」这个前提。
3. **`unchanged_by_own_repos` 字段名保留但加注释**：它测的是**同布局内自身重转**，**不是**验收用的那个量 —— 本次争议就出在这里。

### G.83 L1829 的**准确写法**（lead 定，检测员照录并给出可直落版本）
**实验实际证明的**：
> **插入 car 不给前三块带来任何额外改动。**
**它不证明**：``插入对已有块无影响`` / ``这几块没被碰过``。
**准确表述**：
> 「插入本身不额外改变未参与块；但这三块在两种布局下都被各自的 `repos_local` 重转过（同布局内字节已变），所以『字节相同』**只覆盖插入这一项扰动**。」

**检测员给出的可直落行（供执行者照抄或改写）**：
| 序 | 项 | 验收判据（可复算） |
|---|---|---|
| 1 | **M2 规划器** | **3–5 块并发**；对话第 10 轮后插入新块，答案仍正确；**插入前后未参与移动的块 0 字节变化**（**口径**：「插入前后」= 插入这一块的前/后，非「自身重转前后」）。**读数**：`M2S3_car_back_project.json` ↔ `M2S3_no_car_project.json` 的 `block_bytes` 逐 slot `pre_eq/post_eq` = true（**该比较尚未落字段，属推导量**）。**限定**：两布局下三块均经各自 `repos_local` 重转（同布局内字节已变）⇒「字节相同」**只覆盖插入这一项扰动**（权威见 §13.4） |

### G.84 **FINDING**：「同布局 `48% 字节改变」这个数字**无出处、且无法从现有字段复算**

**实测**：`grep 48%` 在 `PROGRESS-AND-ROADMAP.md` 中 **0 命中**；产物 `block_bytes` **只存 `sha16` 与字节数**，**不含逐字节差分** ⇒ **48% 从现有产物算不出来**。
**⇒ 两种处理，二选一**：① 补出处（哪份产物 / 哪次计算）；② 改定性表述「**同布局内字节已变**」（不写百分比）。
**理由（按已立纪律）**：**对照物须直指被判对象** —— 一个无法从产物复算的百分比，**读者无从核**；而**「数会过期、口径不会」**同样适用于「凭印象的百分比」：**它会被人抄进文档并长期存活**。

### G.85 「**差点变成假绿**」的三个条件（lead 立，检测员记录）

**本条不是假绿**（按事件口径确实 3/3），但**差点变成**假绿，因为同时满足：
| # | 条件 |
|---|---|
| 1 | **结论没落字段**（跨布局相等是推导量） |
| 2 | **两种口径在同一份产物里共存**（同布局内 / 跨布局） |
| 3 | **字段名只指向其中一个**（`unchanged_by_own_repos` 指向同布局内） |
> **这比判据写错更隐蔽** —— 判据写错时人会去查；而「推导量 + 两口径共存 + 名字指向错的那个」**看起来一切正常**。
**⇒ 检查项（新增，写入核单模板）**：一份产物里若同时存在两种口径的读数，**字段名必须能区分它们是哪一个**；否则按「**潜在假绿**」处理。

### G.87【**执行者代记** · 与检测员 G.87 撞号，见 G.90】争议结案：**两个读数都对，量的是不同东西**；且「**读数没落盘**」≠「**读数不存在**」

| 读数 | 是什么 | 字段（改前） | 值 |
|---|---|---|---|
| **同布局内自身重转** | 自己 `repos_local` 之前 → 之后 | `block_bytes[].unchanged_by_own_repos` | **false 3/3**（改写 48.76% / 48.49% / 48.37%，首个差异在**头部** 104 / 92 / 68 < 1188 B） |
| **跨布局（插入事件）** | 有 `car` ↔ 无 `car`，同一 slot 的 pre/post | **无字段（只能两文件并排手算）** | **相等 3/3**（slot1–3 的 pre/post sha16 与字节数逐项相同） |

**检测员读第一句，执行者说第二句 —— 都没读错。** 争议的根不在人，在**字段**：同一份产物里两种口径共存，而字段名只指向其中一个。
⇒ **处置（已落）**：① 跨布局比较**落成字段** `across_layouts`（`compared_with` / `per_slot[{slot,pre_A,pre_B,pre_eq,post_A,post_B,post_eq,bytes_eq}]` / `slots_compared` / `slots_unchanged` / `covers_only`）；② `unchanged_by_own_repos` **保留但加注**（新字段 `own_repos_rewrite.field_note`：它测同布局自身重转，**不是** §13.4 验收用的那个量）。

**结论必须弱化一句（lead 裁定，我照改）**：本实验证明的是「**插入不额外改变未参与块**」；**不**证明「插入对已有块无影响」/「这些块没被碰过」—— 三块在两布局下都各自被重转过，所以「字节相同」**只覆盖插入这一项扰动**，不覆盖重转本身的损失。

**纪律（新，两条）**：
1. **没落成字段的读数，下一轮还会有人找不到。** 推论层面的结论若无法从产物直接读出，就等于没有产物。
2. **「读数不存在」与「读数没落盘」是两件事**：前者是实验没做，后者是实验做了但审计者只能手工重构。**后者更危险**，因为报告里它已经写着，读者只会相信它、不会去重构它。
3. **「数会过期，口径不会」**（检测员提出，lead 采纳）：判据正文只留**口径**（例：`base ≡ 0` ⇒ `delta = target`，故 `delta=0` 零条 ⇒ 无「从不被搬的块」），**计数按批落在产物与台账**，不在正文写死。

**副产品（本批实测，供将来引用）**：`across_layouts` = 3/3 相等；`own_repos_rewrite` = 3/3 改变、ratio 48.4–48.8%、首个差异均在头部（块几何 1188 B 头部 + 104464 B/cell）。

**关于 G.84 的 48% —— 现在有出处了（本批补）**：`48%` 不是印象值，它有两个可复算来源：
· **字段**：`out/M2S3_no_car_project.json` 与 `out/M2S3_car_back_project.json` 各自的 `own_repos_rewrite.per_slot[]`，含 `first_diff_offset` / `diff_bytes` / `diff_ratio`；
· **原始字节**：`out/blkdump_A/seq{1,2,3}_{pre,post}_repos.kvmem`（`--dump-bytes` 持久化导出），逐字节比即可复现；
· **实测值**：slot1 `0.4876`（首个差异 @104）、slot2 `0.4849`（@92）、slot3 `0.4837`（@68）⇒ 正文写「约 48%」指 **48.4–48.8%**，不是约数印象。
⇒ 故 G.84 采处理 **①补出处**（不是 ②改定性）；L1829 已改为「同布局内自身重转改写约 48% 字节（首个差异在头部，见字段 `own_repos_rewrite`）」。

### G.88【**执行者代记** · 与检测员 G.88 撞号，见 G.90】`48%` 的处置定案：正文不写百分比；并落 `byte_diff` 字段

| 项 | 值 |
|---|---|
| 数字 | `1,070,339 / 2,194,932 ≈ 48.8%`（slot1）；slot2 `912,446/1,881,540 ≈ 48.5%`；slot3 `606,883/1,254,756 ≈ 48.4%` |
| 来源 | **当次计算**（执行者），非文件既有字段 |
| 改前可复算性 | **不可**：产物只存 `sha16` + 字节数，**无逐字节差分** |
| 处置 | **正文（§13.9 L1829）只写定性「同布局内字节已变」，不写百分比**；台账记数、不删、不美化 |
| 本批已补 | 落字段 `own_repos_rewrite.per_slot[].byte_diff = {bytes_changed, total, first_diff_offset, region, ratio}` + 原始字节 `out/blkdump_A/seq{1,2,3}_{pre,post}_repos.kvmem` ⇒ **现可复算**；但正文仍按 lead 裁定不写百分比 |

**纪律（第二实例）**：**「推导量必须落字段」** —— 这一轮算过却没存，下一轮就得重算；一次补字段，永久可核。
**同批落盘的另一个字段**：`across_layouts`（`compared_with` / `note` / `per_slot[{slot,pre_eq,post_eq,bytes_eq}]` / `all_eq` / `scope`）—— 跨布局相等从此是**读数**，不再是推导量。


### G.86 `48%` 处置：**文档只写定性，台账留数并标明不可复算**（G.84 结案）

| 项 | 处置 |
|---|---|
| 文档 | **只写定性**「同布局内字节已变」，**不带百分比** |
| 台账 | **记下数并标明不可复算，不删** |
| 今后 | 要这个数就落字段 `byte_diff: {bytes_changed, total, first_diff_offset}` |

**台账所记之数（lead 提供，检测员核算术）**：
| 项 | 值 |
|---|---|
| 分子 | `1,070,339` |
| 分母 | `2,194,932`（= `1188 + 21 × 104,464`，即 home 21 cell 精确长度） |
| 比值 | **48.7641%** ⇒ **≈ 48.8%**（lead 四舍五入正确） |
| 出处 | **当次计算**（非产物字段） |
| 可否复算 | **是（已改档）** —— `out/blkdump_A/seq{1,2,3}_{pre,post}_repos.kvmem` 六份转储**逐字节比对**；**三处独立复算逐位一致**（执行者 `own_repos_rewrite` 字段 / lead / 检测员） |
| 用途 | **可作论据**，**须带字段名与出处路径**（字段 `own_repos_rewrite`；转储 `out/blkdump_A/`） |

**为什么不删（lead 的话）**：**删了等于把一个真实算过的数抹掉，下次有人要重新算。**
**lead 自认（照录）**：这个数是他**转述给用户**的，**转述时没想过它不可复算** —— 「**你的检查对我同样生效**」。
**⇒ 这是「推导量必须落字段」的第二例**（第一例是跨布局 3/3，G.81）。

**检测员核算附带的一处观察【未验证 · 不得作论据】**：`1,070,339 / 104,464 = 10.246`（**非整数**）⇒ 变化字节**不按整 cell 计**，若该数成立则变化分布在 cell 内的等长区段（与「K 数据整段重转」相容）。**但源头数本身不可复算，此观察只是记录，不得引用。**

### G.87 **检查项（lead 立）**：数离开产物必须带走三样

> **凡「数」离开产物进入文档或口头转述，必须同时带走：① 出处（哪份产物 / 哪次计算）② 可否复算 ③ 若不可复算则不得作为论据。**

**lead 的复盘（照录）**：`48%` 满足了 ①（有出处：当次计算），**不满足 ②（可复算）**，**却仍被当作论据转述**。
**⇒ 三样缺一，这个数就不该出产物目录。**
**检测员补一句可执行判法**：③ 是最容易漏的一条 —— **①② 都齐全时，人会默认它可以用**。⇒ 写文档时**先问 `可否复算`，再问 `要不要引用`**，顺序反过来就会漏。

### G.88 **硬条件（lead 定）**：L1829 判据正文**出现任何计数 ⇒ 视为未定稿**

**范围**：不只 110 / 188 / 48%，而是**任何计数**（含将来新增）。**理由**：**数会过期，口径不会。**
**检测员据此把 L1829 的核单合成一张（今后一律按此核，不再按旧四项）**：
| # | 条件 | 判据 |
|---|---|---|
| 1 | **口径正确** | 「插入前后」= 插入这一块的前/后，**非**自身重转前后 |
| 2 | **禁计数（lead 补丁，改写）** | **不是「禁止出现数字」，而是「禁止出现会随批次变化、且不带字段指针的数」** —— ① `110 / 188` → **禁**（每批都变）；② `48.8%` **带** `own_repos_rewrite.ratio` 指针 → **不算违规**（但按 G.92 仍建议移出判据格）；③ `48.8%` **无**指针 → **禁**。**判定式：有字段指针 = 可留；无字段指针 = 一律出正文。** |
| 3 | **读数指向产物** | 指向 `M2S3_car_back` ↔ `M2S3_no_car` 的 `block_bytes`，**并注明是推导量**（未落字段） |
| 4 | **限定紧跟读数** | 两布局下三块均经各自 `repos_local` 重转 ⇒「字节相同」**只覆盖插入这一项扰动** |
| 5 | **不残留绝对口径** | 不得出现「无实例 / 无法评估」这类绝对口径结论 |
| 6 | **不单独成句** | 「两布局逐字节相同」**不得单独成句**（它省略了自身重转前提） |

### G.86 ↓ **订正（检测员，同日）**：`可否复算` 由「否」改为「**是**」

**触发**：执行者**没有**按裁定删百分比，而是**把逐块重转的持久化字节存下来**：`out/blkdump_A/seq{1,2,3}_{pre,post}_repos.kvmem`（六份）。
**检测员独立复算（本轮，逐字节，不转述）**：
| slot | 长度相等 | `diff` 字节 | `first_diff` | `ratio` | 与 lead 报的数 |
|---|---|---|---|---|---|
| 1 | ✓ 2,194,932 | **1,070,339** | **104** | **0.4876** | **逐位相同** |
| 2 | ✓ 1,881,540 | **912,446** | **92** | **0.4849** | **逐位相同** |
| 3 | ✓ 1,254,756 | **606,883** | **68** | **0.4837** | **逐位相同** |
⇒ **三处独立复算（执行者 / lead / 检测员）逐位一致** ⇒ **`可否复算 = 是`**；台账那条「不得作论据」**是一句错话，已改**。
**为什么必须改（lead）**：**一句错话留在台账里会往下传** —— 「不得作论据」会让后来人**白扔一个真数**。

**附带三处定义性约束（取自字段 `own_repos_rewrite.ratio_caveat`，检测员核对无误）**：
1. **`ratio` 只说明「约一半字节取值变了」**，**不是「一半内容被改写」** —— 同一 cell 内重量化后**大量字节偶然相同**，会压低比例。
2. **`first_diff = 104 < 1188`（头部）是平凡的** —— 位置变了头部当然变，**不构成机制证据**。
3. **`1,070,339 / 104,464 = 10.246` 什么也不说明** —— 见 G.89。

### G.89 **纪律**：**不是所有可复算的数都是可解释的数**（第四样：量有没有定义）

**检测员的克制对，理由错（lead 指正，照录）**：
> 我不拿 `1,070,339 / 104,464 = 10.246` 当发现 —— **克制对**；但理由**不是**「源头数不可复算」（现在可复算了），而是：**「不同字节数 ÷ cell 字节数」这个统计量本身没有意义。** 同一 cell 内**大量字节会被重新量化成相同值** ⇒ **diff 字节数与 cell 尺寸之间不存在应有的整除关系**，`10.246` **不是「半个 cell」，什么都不是**。
**⇒ 「换个可复算的源头，这个观察依然不能作论据 —— 因为它不是一个有定义的量。」**

**⇒ 三样检查项补第四样（lead 增）：**
| # | 项 | 回答什么 |
|---|---|---|
| ① | 出处（哪份产物 / 哪次计算） | 从哪来 |
| ② | 可否复算 | 读者能不能重算 |
| ③ | 若不可复算则不得作论据 | 能不能用 |
| **④** | **这个量定义清楚了吗** | **这个量有没有意义** |
**⇒ 落成一句（lead 定，检测员照录）**：

### G.90 **制度**：台账**单写者 = 检测员**（编号冲突登记）

**事实（实测）**：台账现存 **G.86 / G.87 / G.88 各两份** ——
| 编号 | 行 | 作者 | 处置 |
|---|---|---|---|
| G.86 | **L1971** | **执行者代记** | 标【执行者代记·撞号】 |
| G.87 | **L2209** | **执行者代记** | 同上 |
| G.88 | **L2234** | **执行者代记** | 同上 |
| G.86–G.88 | L2248 起 | **检测员** | 保留 |
**lead 裁定**：**执行者不再写台账，只报告**；由检测员记录并标明「**执行者报告 / 检测员记录**」；**已落地的 G.86/G.87/G.88 不重编号**（再改一次只是折腾）。
**根因（lead）**：**不是编号，是两个人写同一个文件** —— 而且这是角色问题：**台账是检测员的产物**。
**检测员体例（今后一律）**：每条头注明来源 `【执行者报告·检测员记录】` 或 `【检测员独立核】`；**编号连续由检查脚本核对**（`^### G\.\d+` 去重后必须与总数相等）。

### G.91 L1829 **v3** 核单结论（六条）

**核时文档身份（检测员实测，G.43）**：sha16 `17338f0fc5930c5a` / **187,700 B** / **2,463 换行**。
**⚠ 与 lead 报的 `a39ebf56d6205508` / 187,745 B 不同**（**少 45 B**，行数相同）⇒ **我核的是这一版；若文件再变，本结论须重跑。**

| # | 条件 | 结论 | 证据 |
|---|---|---|---|
| ① | 口径正确 | ✅ | 明写「（= 插入这一块的前/后，**非**该块自身重转前后）」 |
| ② | **禁计数** | ❌ | 残留 **`约 48%`** 与 **`1,070,339/2,194,932 = 0.4876`** —— **同一个量的两种写法**，且都是**每次运行会变的读数** |
| ③ | 读数指向产物 + 注明推导量 | ✅ | 「读数已落字段 `across_layouts`」 |
| ④ | 限定紧跟读数 | ✅ | 「两布局下三块均经各自 `repos_local` 重转 ⇒ 只覆盖插入这一项扰动」 |
| ⑤ | **不残留绝对口径** | ✅ | 「无实例 / 无法评估」**均已消失**（实测 grep 0 命中） |
| ⑥ | 不单独成句 | ✅ | 「字节相同」已与限定同句 |
**⇒ 6 条中 5 条通过，② 未通过。修法一处**：删掉「约 **48%**」与「`1,070,339/2,194,932 = 0.4876`」，只留「见字段 `own_repos_rewrite`」—— **字段已带 `ratio_caveat`，正文不必重复它的数**。

**lead 交办的一处独立判定：「`delta=0` 至今零条」算不算计数？**
> **检测员的判定：算。「零条」是计数；「不存在 `delta=0` 的块」不是。**
**判据不是「有没有数字」，而是「它会不会随产物增长而改变真值」**：
| 写法 | 性质 | 可否入判据正文 |
|---|---|---|
| 「`delta=0` **至今零条**」 | **一次统计**（分母在变，结论可能翻） | **不可** |
| 「**不存在** `delta=0` 的块」（+ 范围） | **全称否定命题 / 口径结论** | **可**（须标范围，见 G.75） |
⇒ **lead 的倾向在「命题」形式下成立，在「计数」形式下不成立** —— 差别就在那个**「条」**字：**它把命题降格成了一次统计**。
**事实补充**：v3 里「至今零条」这句**已经不在**（改为「绝对口径（存在一块从不被搬）**不属本条**，属持久化路径性质」）⇒ **本条已按可入正文的写法改写**，判定只对未来写法有约束力。

### G.92 **重新裁定**：L1829 的 ② 由「未通过」改为「**通过禁计数，但违反「数的归属」**」

**lead 2026-10-25 改主意（照录理由）**：
> **48.8% 是 `repos_local` 有损性的一个读数，它不是 M2 判据的一部分。** 把它写进判据格，等于**在一格判据里塞进一个观测值**。读者会以为「验 M2 还要看 48%」—— **其实不用**。
**改法**：「两布局下三块均经各自 `repos_local` 重转（**同布局内字节已变**，比例见字段 `own_repos_rewrite.ratio`）」—— **数字不落地到正文**。**两头都不丢**：数字在字段里可复算，判据格里只有口径。

**⇒ 检测员的判定修正（并自报一次口径混淆）**：
| 判定对象 | 旧结论（G.91） | 新结论 | 原因 |
|---|---|---|---|
| 违反「**禁计数**」 | ❌ 未通过 | ✅ **通过** | v3 的 `48%` **带字段指针** `own_repos_rewrite` ⇒ 按补丁后的定义**不算违规** |
| 违反「**数的归属**」 | （当时未单列） | ❌ **成立** | **读数被塞进判据格** —— 这是我的漏判：**我把「闻起来像计数」直接判成违规，没有区分「有没有指针」** |
**自报**：我 G.91 的 ② 判定**用的是一个我自己也没写死的定义**（「正文无任何计数」），**这正是我们反复禁的「判据无值域」** —— 它在 `110/188` 上给对的结论，在 `48%+指针` 上给错的结论。**补丁后它才有值域。**
**⇒ 由此得一条通用教训**：**判据写「禁止 X」时必须同时写「什么算 X」**，否则它只在写判据的人心里成立（与 G.37「判据须有值域」同族，这是第二次撞上）。

### G.93 **预登记**：M2 方案评审口径（`M2-PLAN.md`，5,097 B / 66 行 / 路径 `kvmem/m2_visibility/m14b_e10_probe/M2-PLAN.md`）

**lead 的评审意见**：**先交六条必红脚本、后写 planner**。
**⇒ 检测员将来核的重点（现在就写死，防事后挪靶）**：
| # | 核什么 | 为什么 |
|---|---|---|
| 1 | **六条红必须是真的红，且红在不同地方** | 若六条都因**同一处失败**（如 import 错、planner 抛异常）⇒ **一条也没验**，只是把一次失败记了六遍 |
| 2 | **假 planner 必须逐条定制** | 一个万能假 planner（如「返回空列表」）同时触发六条 ⇒ 正是 1 的形态。**每条必须各自造一个只触发它自己的假收录** |
| 3 | **红必须先于修** | 顺序须可查：先见红、再改代码、再见绿；**事后构造的红不算** |
| 4 | **每条须报字段名** | G.38：**字段名是稽核接口**；计划书已自定「必红证据 / 绿证据 / 字段名」三件，**照此核** |
| 5 | **每条须有值域** | G.48：断言在**两批数据上都要出现过 true 与 false**；只在单侧取值 ⇒ 当批降级为观测值 |
| 6 | **不得退化成「跑一遍没报错」** | **「判据须先自证会亮」第一次用到代码上** —— 验收物是**六条会亮的红**，**不是** planner 最终通过 |
**计划书已具备的基础（实测）**：§3 表头即写「触发红的方式（**必须先自证会亮**）」；S4 的必红方式是「**故意反序**（先 `repos_local` 后 `drop`）⇒ 必须观测到块被拖走」；§5 交付 `test_planner.py`（S1–S6 各一必红 + 一绿，输出 `out/P<S#>.json`）+ `RESULTS-M2-PLANNER.md`。⇒ **形式要件已写在计划里，我核的是它是否真的做到。**


### G.94 **文档冻结令** + 六版 sha16 链（我的处置：只核最后那版一次）

**冻结令（lead 2026-10-25）**：**最后改一处（把 48.8% 移出判据格、只留字段指针），改完封版。** M2 交付前不再接受任何编辑；**除「会让人照错版本干活」的硬错外，格式与措辞一律不动。**

**§13.9 同一格子改过 6 版（lead 提供）**：
| # | sha16 | 备注 |
|---|---|---|
| 1 | `ca47029d` | 我核过的漂移版（L1828/L1829/L1830 全漂） |
| 2 | `4fd3bf5d` | 执行者第一轮同步 |
| 3 | `04f8d749` | |
| 4 | `a39ebf56` / 187,745 B | lead 报过的版本 |
| 5 | `0e5ab8c0` | |
| 6 | **`17338f0f` / 187,700 B / 2,463 行** | **我核 v3 的版本；lead 说他也读到这一版** |
⇒ **每改一次，我那一版核验就作废一次** ⇒ **处置：等最后那版落地，只核一次，把它的 sha16 记成冻结版**。**不再逐版重核**（G.43 只对当版负责）。

**检测员实测（本轮，冻结令下达后）**：文档仍为 **`17338f0fc5930c5a` / 187,700 B / 2,463 换行**；L1829 **仍含 `%`**（`约 48%`）**且仍含字段指针** `own_repos_rewrite` ⇒ **最后一次改动（移出 48.8%）尚未落地**。**⇒ 冻结版尚未产生，我继续等，不提前记。**

**lead 另加的三项可查物（进 M2 验收契约，检测员记录）**：
| # | 可查物 | 我要核什么 |
|---|---|---|
| 1 | **逐条的「错法 → 断言 → 红输出原文」** | 三段须对得上同一条；红输出原文须是**脚本实际打印**，不是复述 |
| 2 | **两条断言在同一假 planner 上一起红 ⇒ 须说明为何不算同因** | 这正是我 G.93 预登记的 ①②之争；**举证责任在执行者**，不在我 |
| 3 | **红证据时间戳须早于 `planner.py` 创建时间** | 用文件系统时间核对「红先于修」，**比自述可靠** |
⇒ **第 2 项是关键**：它把「同因」的举证责任**明确交给执行者**，我不必替他判断，只需**验他给的理由是否成立**。

**G.91 的自我撤回，lead 的评语（照录备查）**：
> 这是**同一条纪律第二次撞上，且撞在你身上** —— 但它这次是**你自己抓的**。
⇒ 由此立的两条纪律已在附录 G 顶部并列（**判据对数据要有区分力 / 判据对语言要有定义**），**定义在前、实例在后**。


### G.95 **定案核结果 + 一处必须立刻上报的版本不符**

**⚠ 先说结论：lead 宣告的冻结版 `17338f0fc5930c5a` / 187,700 B 在磁盘上已不存在。**
| 版本 | sha16 | 字节 | 换行 | L1829 判据格 |
|---|---|---|---|---|
| lead 宣告的冻结版 | `17338f0f` | **187,700** | 2,463 | **含 `约 48%`** |
| **磁盘实际（检测员实测）** | **`a7a01655`** | **187,551** | 2,463 | **无 `%`、无 `0.4876`、无 `1,070,339`；指针 `own_repos_rewrite.ratio` 保留** |
⇒ **少 149 B** ⇒ **「把 48% 移出判据格」这一处改动已经落地** —— **而它正是 lead 宣告撤回（改攒批）的那一处**。
**⇒ 我不能对 `17338f0f` 出定案核**（该版本已不可复现）；**定案核只能对 `a7a01655` 出**。请 lead 重新裁定冻结版。

**定案核（对象：`a7a01655` / 187,551 B / 2,463 换行；核前核后 sha 同值，版本稳定）**：
| # | 项 | 结论 | 证据 |
|---|---|---|---|
| ① | 口径正确 | ✅ | 「（= 插入这一块的前/后，**非**该块自身重转前后）」 |
| ② | 禁计数（补丁后定义） | ✅ | 判据格内**无百分比、无绝对比率**；指针 `own_repos_rewrite.ratio` 保留 ⇒ 三档判定式中「有字段指针」 |
| ③ | 读数指向产物 + 已落字段 | ✅ | 「读数已落字段 `across_layouts`」 |
| ④ | 限定紧跟读数 | ✅ | 「两布局下三块均经各自 `repos_local` 重转（同布局内字节已变）⇒ 只覆盖插入这一项扰动」 |
| ⑤ | 不残留绝对口径 | ✅ | 该区段 `无实例` / `无法评估` **0 命中**（实测） |
| ⑥ | 不单独成句 | ✅ | 已与限定同句 |
| ⑦ | **声明行位置** | ✅ | L1824 空行 / **L1825 声明行** / L1826 空行 / L1827 表头 ⇒ **紧贴标题、表头前** |
| ⑧ | **四行对权威小节逐项** | ✅ | 我按四节关键串逐行比对，**missing 全为空**：L1829(3–5/第10轮/插入前后/未参与移动的块/0字节变化)、L1830(四条/承重/可复现/恢复后全绿/三份/剔除/saved_at/fa94b1bc58c0e421)、L1831(预登记/漏判率/误判率/(c)/逐句判定/按句统计/边界1/判据变更须标方向)、L1832(谁是权威/另两处如何改/一致性断言) |
⇒ **八项全过。** 且**此版已无 G.71 报的 4 条整项丢失与 4 条限定丢失**（含「（不报单一『准确率』）」—— 见下注）。
**注**：L1831 现为「`(a)` 预登记改写对，**漏判率与误判率分别报**」；权威 §13.3 L1765 另有「（**不报单一「准确率」**）」一句。**该句仍未出现** ⇒ **唯一残留的限定**，属**非阻塞措辞项**（不改变判据可执行性：分别报即排除单一准确率）。

### G.96 **已知缺陷登记**（lead 要求三句齐全）

**按 lead 宣告的冻结版 `17338f0f` 写（该版本含 48%，但已不在磁盘）**：
| 项 | 内容 |
|---|---|
| **① 发现了** | L1829 判据格内含 **48%** 读数（**不是没发现**） |
| **② 判为不阻塞** | 该数**带字段指针 `own_repos_rewrite`** ⇒ 按三档判定式**不违规**；属「**数的归属**」（读数宜由字段指向）而非「**禁计数**」 |
| **③ 已排期** | 与 **M2 结果文档更新同批**修，**不在冻结期内单独改** |

**按磁盘当前版 `a7a01655` 写（实测）**：**上述缺陷已不存在** —— 48% 与 `0.4876` 均已移出判据格，只余字段指针。**⇒ 三句话在此版本上退化为「已消除」，但该改动属 lead 宣告攒批的那一处，需由 lead 重新裁定。**

### G.97 **原则（lead 立）**：把举证责任放到**持有信息的一方**

> **我原来那条要求我自己判断；改的那条要求他自证。**

**两条判据的落差**：
| 写法 | 判定者需要什么 | 结论 |
|---|---|---|
| 「**六条红必须红在不同地方**」（旧，检测员原提） | **判定者要自己判断「是不是同因」** —— 而判断同因**需要看它的实现**，那是我方不掌握的信息 | **写坏了** |
| 「**两条断言同假 planner 一起红 ⇒ 须说明为何不算同因**」（新，lead 加） | 判定者只需**验理由成立与否** | **可用** |
**⇒ 原则**：**判据设计要问一句 —— 这条判据要求谁掌握信息？如果要求判定者掌握他没有的信息，那它写坏了。**

### G.98 **与 34-b 并排（务必不混淆）**

| 条 | 管什么 | 规则 |
|---|---|---|
| **34-b** | **期望值**（判据的标准答案从哪来） | **期望值必须独立于被判对象** |
| **G.97** | **解释**（为什么两条红不算同因） | **解释可以来自被判对象，但必须可核** |
**⇒ 二者不冲突**：让被判对象**自证解释**，**不等于**让它**定义标准答案**。**解释由它给，裁决仍在判定方。**
**检测员补一句防混淆**：**「自证」二字必须限定在「解释」上**；一旦有人把「自证」用到「期望值」上（如「让 planner 自己报它应该产出什么布局」），**即违反 34-b**。

### G.99 §17 侧 T1–T4 清单：**降为低优先级**

**事实**：执行者很早交过一版（**61/61**：T1 六标题 / T3 七行含 **L2381 空行** / T4 两处三行）。**按新锚口径重交的版本仍未交。**
**lead 裁定**：**低优先级** —— **§17 已被我核过 54/54 全等，重交只是形式补齐；M2 的红证据优先于它。**
**⇒ 检测员处置**：**不再向执行者催**；若重交版出现，我只核「T3 是否含 L2381 空行、T4 是否两处三行」两项（与旧版差异点），**不重复 54/54 全量**。


### G.100 **定案核 · 冻结版 = `17338f0fc5930c5a`**（lead 裁定，检测员重跑八项）

```
冻结版 = 17338f0fc5930c5a / 187,700 B / 2,463 换行
已知缺陷（不阻塞，已排期）= L1829 判据格内含 48% 读数（含 1,070,339；带字段指针 own_repos_rewrite ⇒ 不违规；
  属「数的归属」而非「禁计数」）；处置：与 M2 结果文档更新同批修，不在冻结期内单独改。
```

**§13.9 八项重跑（对象 `17338f0f`；**核前核后 sha 同值**，版本稳定）**：
| # | 项 | 结论 | 证据 |
|---|---|---|---|
| ① | 口径（插入这一块的前/后，非自身重转前后） | ✅ | 明写「**非**该块自身重转前后」 |
| ② | **禁计数（补丁后定义）** | ✅ | `48%` 与 `1,070,339` **带字段指针 `own_repos_rewrite`** ⇒ 三档判定式中「有字段指针」⇒ **不违规** |
| ③ | 读数指向产物 + 落字段 | ✅ | 含 `across_layouts`（跨布局读数已落盘） |
| ④ | 限定紧跟读数 | ✅ | 「同布局内字节已变 ⇒ 只覆盖插入这一项扰动」 |
| ⑤ | 不残留绝对口径 | ✅ | 该区段 `无实例`/`无法评估` **0 命中** |
| ⑥ | 不单独成句 | ✅ | 已与限定同句 |
| ⑦ | 声明行紧贴标题、表头前 | ✅ | L1824 **空** / **L1825 声明行** / L1826 **空** / L1827 表头 |
| ⑧ | 四行对权威小节逐项 | ✅ | 关键串比对，**missing 全为空**（L1829 七串 / L1830 八串 / L1831 八串 / L1832 三串） |
⇒ **八项全过。**

**指针粒度之注（lead 指出，检测员照录）**：现盘上是 `own_repos_rewrite`，**不是** `own_repos_rewrite.ratio`。**指针存在即算**，粒度差异不影响判定（`48%` 是 `.ratio` 的读数，字段族已在）。
**唯一残留（非阻塞措辞项）**：L1831 仍缺权威 §13.3 的「（**不报单一「准确率」**）」（实测 `准确率` 在该行 **0 命中**）—— 「分别报」已排除单一准确率，故不改。

### G.101 `a7a01655` 标为 **瞬态 · 已作废 · 非冻结版**

| 版 | sha16 | 字节 | L1829 | 状态 |
|---|---|---|---|---|
| **`a7a01655`** | `a7a01655…` | **187,551** | 无 `%`、无 `1,070,339`、指针在 | **瞬态，已作废，非冻结版**（是 lead **已撤回**的那次编辑的结果） |
| **`17338f0f`** | `17338f0fc5930c5a` | **187,700** | 含 `48%`、`1,070,339`、指针 | **冻结版** |
⇒ **标为作废的理由（lead）**：**否则我们冻结的是一份已被取消的改动。**
⇒ **检测员提示**：将来若有人翻到 187,551 那版（例如从 `git`/备份/日志里），**必须先看本节**，否则会以为那是终版。

### G.102 **纪律**：冻结 / 停止 / 定稿类指令，发令人**必须自己重新读盘**并把 sha16 写进声明

**lead 立（自报错因）**：
> 我用**消息里最新报告的哈希**宣告冻结，**没有自己读一次盘**。
> **根本原因**：**撤回令与执行中的写入会交叉** —— 执行者按上一条指令改完才收到撤回令；此时文件状态取决于**谁后写**，**只有读盘能知道**。
**⇒ 凡「冻结 / 停止 / 定稿」指令，发出后必须由发令人自己重新读盘确认，并把读到的 sha16 写进冻结声明。不读盘就宣告冻结 = 宣告一个可能不存在的版本。**

**检测员的同错自报（表述超出证据）**：我曾写「**该版本已不可复现**」—— 但我只有**一次采样**，正确表述应是「**我此刻读到的磁盘状态是 `a7a01655`**」；**「已不可复现」是关于文件的持久断言，一张采样证不了它。**
**⇒ 与 G.43 同族**：**版本陈述必须连同采样时刻**；两次不同时刻的读数**不构成矛盾**，只构成**两次采样**。

**实测时间线（检测员，两次读盘）**：
| 时刻 | sha16 | 字节 | 说明 |
|---|---|---|---|
| 前一次读数（本会话上一条） | `a7a01655` | 187,551 | 「移出 48%」已落地 |
| 文件 `mtime` | **05:10:25Z** | —— | **两次读数之间被改写（回退）** |
| 本次读数 **05:11:10Z**（连读两次同值） | **`17338f0f`** | **187,700** | **与 lead 读到的字节一致** |
⇒ **两次读数各自为真**；**当前磁盘 = `17338f0f`**。


### G.103 M2 红套件核单（检测员独立核；路径 `kvmem/m2_visibility/m2_planner/`，**不是** probe/out）

**产物位置纠一处交接误差**：`RED-SUITE.json` / `ORDER-EVIDENCE.json` 在 **`m2_planner/out/`**；**probe/out/ 下两份都 ENOENT**。

**红集合矩阵（逐 case 读 `out/RED-SUITE.json`，不转述）**：
| 运行 | want | 实测 red | 与 lead 报的 |
|---|---|---|---|
| **P0 正确版（对照）** | `__none__` | **空集** | 同 ✓ |
| P1 几何重叠 | S1 | S1 | 同 ✓ |
| P2 无视预算 | S2 | S2, S6 | 同 ✓ |
| P3 锚点差一位 | S3a | S3a | 同 ✓ |
| P4 tie-break 反了 | S3b | S3b | 同 ✓ |
| P5 插入先移后摘 | S4 | S4, S5 | 同 ✓ |
| P7 位置全对多转一次 | S5 | S5 | 同 ✓ |
| P6 放不下不抛 | S6 | S6 | 同 ✓ |
| **P8 池字节不够但不拒绝** | S2 | **S2（单独）** | **lead 要求的那条，执行者已落地** |
⇒ **断言共 7 条**（S1/S2/S3a/S3b/S4/S5/S6），**并集覆盖 7/7 无遗漏**（按 `asserts` 键取并集核对）。**lead 说「按七条核、别看标题」正确** —— 执行者标题仍写「六条」。

### G.104 **判定：lead 的 P8 要求成立，且已满足；但有一处表述必须改**

**要求成立的论证（我独立给，不因是 lead 提的就过）**：若 S2 的红**永远**伴随 S6，则二者在现有证据上**不可分辨** ⇒ S2 可能只是 S6 的影子。**分离性必须双向**：S6 单独红（P6 ✓）+ **S2 单独红（此前无）**。
| 用例 | `S2.detail` | 触发哪一半 |
|---|---|---|
| P2（`chat_len=8180`） | `cell_ok=false` / `bytes_ok=true` | **n_ctx 档** |
| **P8（`pool_bytes=1,000,000`）** | `cell_ok=true` / `bytes_ok=false` | **pool 档** |
⇒ **S2 内部两个子条件各被单独触发一次** ⇒ 不只 S2 与 S6 可分离，**S2 自身也可分离**（比 lead 要求更强）。

**必须改的表述**：**P8 里 S6 根本没有被评估** —— `P8.asserts` 只有 S1/S2/S3a/S3b，**无 S6 键**。
**代码实证（`red_suite.py` L58–61）**：
> `# S6 = n_ctx 档的拒绝义务（硬）；pool 档属资源说明，planner 可以更严但 S6 不据此判红`
> `expect_refuse = (sum(cells) + chat_len) > n_ctx` / `if expect_refuse:  # S6 只在本来就该拒绝的场景下判定`
⇒ P8 的 n_ctx 够 ⇒ **S6 不挂载** ⇒ **正确表述是「S2 红，S6 不参与」，不是「S2 红而 S6 绿」**。

### G.105 **FINDING（本轮最重要）**：**S5 与 S6 从未为真** ⇒ 只算「会红」，还不是双向判据

| 断言 | true | false | 评估次数 | 结论 |
|---|---|---|---|---|
| S1 | 5 | 1 | 6 | 双向 ✅ |
| S2 | 4 | 2 | 6 | 双向 ✅ |
| S3a | 5 | 1 | 6 | 双向 ✅ |
| S3b | 5 | 1 | 6 | 双向 ✅ |
| S4 | **1** | 1 | 2 | 双向 ✅（绿来自 **P7**：位置全对） |
| **S5** | **0** | 2 | 2 | ❌ **从未绿** |
| **S6** | **0** | 2 | 2 | ❌ **从未绿** |
⇒ **按 G.48（能红 + 能绿 + 两类取值都出现过），S5 与 S6 目前不合格。**
⇒ **lead 的「P0 红集合为空」其证明力只覆盖 S1/S2/S3a/S3b**（P0 的 `asserts` 就是这四条）—— **S4/S5/S6 无绿证据**。

**补绿建议（都可立刻做）**：
| 编号 | 构造 | 期望 | 成本 |
|---|---|---|---|
| **P9** | **正确实现** + `chat_len` 令 n_ctx 不够 ⇒ 必须拒绝 | **S6 true** | **近零**（同一份 correct reference，不必等 planner） |
| **P10** | **正确实现** + 插入（不拖动、不重复重转） | **S5 true**（S4 已有绿） | 低（planner 到位即可） |
**⇒ 缺绿不是难，是没人想到要造** —— 即 `hit_first_ws` 那条教训：**判据落盘后要问「它绿过吗」**。


### G.109 P8 撤回：我核过，**撤回正确**，且理由比「结构耦合」还硬一层

**代码实证（我读 `planner.py` 的拒绝分支）**：
> `if cells + chat_len > budget[n_ctx]: raise PlanRefused(n_ctx)`
> `if cells * budget[bytes_per_token] > budget[pool_bytes]: raise PlanRefused(pool_bytes)`
⇒ **「越预算」与「该拒绝」在实现层就是同一个分支**：任何越预算路径**必然**先抛 ⇒ 不抛而继续布局的实现**不可能存在** ⇒ **S2 红与 S6 红来自同一条 `if` 语句的两侧**。lead 说的「领域事实」在代码里就是这个形状。

**我另加一条 lead 没说的反证**：P8 把 `pool_bytes` 压到 **1,000,000** ⇒ 除以 `bytes_per_token 104,448` = **9.57 tokens** ⇒ **连一个 cell 都放不下的预算**。
⇒ **P8 的分离性是用一个没有物理意义的预算换来的**：真实系统里不存在 9.57 token 的 pool ⇒ 它证明的是「S2 会在荒谬输入下变红」，**不是「S2 有独立判别力」**。**这比结构耦合更直接地说明该要求不该提。**

**执行者收窄 S6 的后果（必须撤销，且撤销时注意一处）**：S6 回到「两种容量的拒绝义务」后，**断言须同时校 `refused.reason`**（`n_ctx` / `pool_bytes`），否则「拒绝了但理由不对」会被判绿 —— **这正好是 G.105 里 S6 从未绿过的补法**（P9 的绿必须验 reason，不只是 `refused is not None`）。

### G.110 **判定：lead 的 `base` / `pos_hi` 发现成立**（我核过），并补两条他未提的

**事实（代码实测）**：
| 位置 | 持有的是什么 |
|---|---|
| `planner.plan()` 返回 | **`(seq, pos_hi)`** —— 最大占用位 |
| `kvsim.Sim` 内部真值 | **`pos_lo`**（`block_hash = h(seq, pos_lo, rot)`） |
| `assertions.S1_geometry` | **现场算** `pos_lo = pos_hi - cells + 1` |
| `red_suite.SPEC` L17 | **唯一同时持有两者**：`{1: {pos_lo: 4075, pos_hi: 4095}}` |
⇒ **换算 `base = pos_hi − cells + 1` 只活在每个调用点**，**无单一持有者、无断言覆盖** ⇒ **P3 测的「差一位」在被断言覆盖的路上；真正的差一位风险在这条没人测的换算上。** lead 判断成立。

**我的补强 ①（防恒真）**：`base + cells − 1 == pos_hi` **若两字段互为派生，则它必然为真** —— 这是一条**恒真候选**。⇒ 必须配**外部锚**：`home` 的 `base=4075 / pos_hi=4095`（来自冻结几何，非本条推导）；且**插入后 cells 变化时须重验**（`new_cells` 与既有块 `cells` 不是同一个量）。
**我的补强 ②（换一种说法，问题更清楚）**：这不是「一个词指两样东西」，而是 **「一样东西没有名字」** —— `base` 在系统里**无名**（每人临时算），所以**没人能对它下断言**。⇒ **给被需要的量命名，是让它可被断言的前提。** 这条比「一义多名」更可执行：**检查有无『每处都临时算、无人持有』的量**。

### G.111 S1m_manifest 的 `gaps` 是**从目标反推**的 ⇒ 它测的是「同输入同输出」，不是「推导出空隙」

**lead 的两个分支我给出确定答案：反推。** 算术（我算的）：
| 量 | 式 | 值 |
|---|---|---|
| home cells | 4095 − 4075 + 1 | **21** |
| project cells | 4031 − 4014 + 1 | **18** |
| habit cells | 3967 − 3956 + 1 | **12** |
| **`gaps[1]`** | home.pos_lo − project.pos_hi − 1 = 4075 − 4031 − 1 | **43** |
| **`gaps[2]`** | project.pos_lo − habit.pos_hi − 1 = 4014 − 3967 − 1 | **46** |
⇒ **`gaps={1:43, 2:46}` 正是三块冻结几何的「缝宽」**，而 `SPEC` 里三块的目标位置又是**从既有产物抄来的常量** ⇒ **把答案拆成「块 + 缝」再喂回去，当然逐位复现。**
⇒ **正确说法**：S1m 是**回归锁**（锁住冻结几何不漂），**不是**「规划器会布局」的证据。**RESULTS 里「逐位复现」四字必须补上下文**，否则读者会读成后者 —— 两者差一个量级。
**⇒ 若要真的测「推导」**，须给 planner **只给块 + 相关性 + 约束**，让它自己决定缝宽，然后比对；**而「缝宽怎么来」这件事现在仍是空白**（真实系统里缝宽由什么决定？无人回答）。

### G.112 **第二处同类位置**：`S2` 的 pool 档**不含对话字节**，且默认参数下**恒真**

**代码实证（`assertions.S2_budget`）**：
> `a = cells + chat_len <= n_ctx`   ← **含对话**
> `b = cells * bytes_per_token <= pool_bytes`   ← **不含对话**
⇒ **「放不下」一词在同行里指两种口径**：n_ctx 档含对话，pool 档不含。若真实系统里对话 KV 也占 pool（几乎必然），则 **pool 档系统性低估**。

**更硬的一条（我算的算术）**：`kvsim` 默认 `pool_bytes=855,638,016`、`bytes_per_token=104,448` ⇒ **855,638,016 / 104,448 = 8,192 = n_ctx 恰好**。
⇒ **默认预算下 `b` 是 `a` 的必然推论**：`cell_ok ⇒ cells ≤ 8192 − chat_len < 8192 ⇒ cells × bpt < pool` ⇒ **`bytes_ok` 恒真**。
⇒ **只有人为压低 `pool_bytes` 才可能假** —— 而唯一压低它的就是 P8（9.57 tokens，见 G.109）。**⇒ `bytes_ok` 在真实预算下是无实例判据。**
**⇒ 修法**：pool 档须计入对话（`cells + chat_len`）× `bytes_per_token`，且 `pool_bytes` 不得恒等于 `n_ctx × bytes_per_token`（否则永远测不出）。


### G.113 族扫描：七条断言里，只有三条在真实参数下双向可判

扫描口径（先写死，防挪靶）：真实参数 = n_ctx 8192 / chat_len 500 / bpt 104,448 / pool 855,638,016 / 三块 cells 21+18+12 = 51 / keys = 1,3,2（互不相同）。域内 = M2 判据自己的范围（3–5 块并发、第 10 轮插入）。
核时版本：red_suite.py 5,898 B / mtime 05:17:22 / sha16 a3a9d891de7aa236（又改过：上一轮我读的是 5,953 B / 05:13:52）⇒ 本表只对该版成立。

| 断言 | 域内能红 | 域内能绿 | 判定 |
|---|---|---|---|
| S1 几何 | 能（P1 用默认 BUDGET = 真实参数） | 能（P0） | 合格 |
| S2 预算 | 不能（两半都不能） | 能（P0） | 域外判据 |
| S3a 锚点 | 能（P3 默认） | 能（P0） | 合格 |
| S3b 单调 / tie-break | 不能（真实 keys 1/3/2 互不相同 ⇒ 任何排序都单调；P4 靠人造平局 keys=1,2,2） | 能（P0） | 域外判据 |
| S4 拖动 | 能（P5 默认） | 能（P7） | 合格 |
| S5 字节 | 能（P7 默认） | 从未 | 只有红 |
| S6 拒绝 | 不能（P6 用 chat_len=8000，真实 500） | 从未 | 域外 + 无绿 |
| S1m_manifest | 无红设计（回归锁，不是判据） | 能 | 锁 |
| S6b_ops_order | 未造过红 | 能 | 未证红 |

⇒ 名单（lead 要的）：「只在人造参数下能红」= S2、S3b、S6 —— 七条中的 3 条。
⇒ 叠加「从未绿」：S5、S6。
⇒ 真正合格（域内能红 + 能绿）= S1、S3a、S4 —— 只有 3 条。


**S2 为什么两半都不能红（算术）**：
| 半 | 域内取值 | 结论 |
|---|---|---|
| a：cells + chat_len ≤ n_ctx | 51 + 500 = 551 ≤ 8192 | 恒真；要它假须 >7,692 cells（约 366 块，比 M2 域大两个量级） |
| b：cells × bpt ≤ pool | 51 × 104,448 = 5,326,848 ≤ 855,638,016 | 恒真（因 pool 恒等于 n_ctx × bpt，见 G.112） |
⇒ P2 的红靠把 chat_len 从 500 抬到 8,180（16 倍）；P8 靠把 pool 压到 9.57 tokens。两处都是夹具，不是实现。

**结构性原因（比名单重要）**：三条域外判据的共同点 —— 预算 / 平局 / 拒绝这三件事，在「3–5 块 + 8,192 ctx」的规模里根本不会发生。
⇒ 不是假 planner 造得不好，是判据的范围与实现的规模不匹配：它们测的是大负载下的行为，而 M2 的验收场景是小负载。

**检测员建议（留删由 lead 定，不预设）**：
| 对象 | 建议 | 理由 |
|---|---|---|
| S2 | 删（lead 已派） | 两半皆恒真；删掉不损失任何判别力 |
| S6 | 保留，但改写域的表述：域 = 当总占用越 n_ctx 时，并明说该情形不在 M2 范围内 | 拒绝义务是真实存在的语义，只是本轮不触发；删掉会让「越界怎么办」永久无判据 |
| S3b | 保留，标注为域外：仅当两块的 distance key 相等时 | tie-break 是规格外的实现细节；若真实系统不存在平局来源，它就没有对象 |
| S5 | 保留，补绿（P10） | 它有真实域内的红（P7），只缺绿 |

### G.114 新空白正式登记：「缝宽（gap）由什么决定」无人回答

lead 已采纳为正式空白，本轮不要求回答：M2 验收不要求它 ⇒ 不入本轮范围，但必须留在文档里，否则将来有人以为 gaps 是推出来的。
检测员附：将来要回答它，须先答「这组缝是冻结几何的残留（43/46）还是新规划应有的约束」—— 两者会导致完全不同的规划器设计。


### G.115 裁定：判据分两层（域内四条 / 契约测试三条）

| 层 | 断言 | 地位 |
|---|---|---|
| **域内（计入 M2 验收）** | **S1 几何 / S3a 锚点 / S4 不拖块 / S5 字节** | **验收条件** |
| **契约测试（不计入验收，须有红有绿）** | **S2 n_ctx 档 / S3b tie-break / S6 拒绝** | **回归锁** |

**验收口径写死**：**M2 通过 = 域内四条全绿 + 真机插入一次成功。** 契约测试不作为通过条件。
**理由（lead）**：这三条测的是**大负载行为**，M2 的运行点是**小负载**。**删掉它们会让「将来规模上来会怎样」永久无判据；算进验收则是拿域外的红绿冒充域内的保证。⇒ 降级是唯一诚实的处置。**

**删 / 改 / 补（lead 派）**：
| 对象 | 处置 | 绿的造法 |
|---|---|---|
| **S2** | `bytes_ok` 半档**删除**；剩 `n_ctx` 半档**降契约测试** | **P0 在默认预算下不越界即绿，须让断言真的被评估，不是跳过** |
| **S6** | **不删**，改域为「总占用越 `n_ctx` 时」，**必须有绿** | **`budget.n_ctx=600` + `cells=51` ⇒ 必须 raise `PlanRefused(reason=n_ctx)`** |
| **S3b** | **保留**（不改域外，见 G.116） | 须在 RESULTS 写清夹具 key 互不相同 ⇒ 本夹具上绿是平凡的 |
| **S5** | **必须补绿（P10）** | **正确 planner + 固定布局，插入一块后既有三块字节不变**（即 `M2S3_car_back` ↔ `no_car` 的口径搬进套件） |

**检测员核算（S6 的 600 站得住）**：`51 + 500 = 551 ≤ 600`？**不成立** ⇒ 必须 raise ✓；而 `51 cells 本身放得下` ✓ ⇒ **600 是一个可以存在的配置**（小上下文），与 P8 的 **9.57 token 池**（连一个 cell 都放不下，自相矛盾）**不同类**。**lead 否 P8 与留 S6 不冲突，此算术支持该判断。**

**lead 确认的联动（我提的）**：删 `bytes` 档后 **P2 与 P6 不再共用同一夹具** ⇒ **S2 ⊆ S6 的耦合随 `bytes` 档一起消失**，两条判据的假不再互相牵连 ⇒ **反而是好事**。

### G.116 **lead 改我一处判断：S3b 的恒绿是夹具造成，不是域造成**（我认，并自报口径错误）

**lead 的纠正（照录）**：
> 你说「真实 `keys={1:1,2:3,3:2}` 互不相同 ⇒ 域内恒绿」，但**那是夹具选出来的，不是领域的性质**。`distance_key` 由调用方注入；真实相关性打分**完全可能平局**（两块同样相关）。⇒ **S3b 的「恒绿」是夹具造成的，不是域造成的。**

**检测员自报（错误性质）**：我 G.113 那一列的**列名是「域内能红」**，而 S3b 那格的依据是**本夹具的 keys** ⇒ **我用夹具事实下了一个域级结论**。
⇒ **这与 G.57 是同一族**（那次我把「块」的绝对口径当成「臂」的事件口径）：**证据为真，指涉范围错了一层。**
**⇒ 正确写法**：「**本夹具上** S3b 恒绿；**域内是否可能红未验**（取决于真实相关性打分会不会平局，而相关度计算不在本模块范围）」。
**⇒ 由此得一条可执行判法**：**填「域内」这类范围词之前，问一句「我手上这份数据覆盖了整个域吗」** —— 覆盖不了，就只能写「本夹具上」。

**一处连带修正（我自查，未等 lead 指）**：同一张表里 **S6 那格也写了「域内不能」** —— 严格说同样是范围错层：S6 在 **`n_ctx=600` 这种真实配置下能红**（G.115 已核），只是**不在 M2 的运行点**。⇒ **正确写法是「M2 运行点上不触发」，不是「域内不可能」**。**两种说法的差别，正是两层裁定成立的理由。**

### G.117 两层裁定的记账口径（防将来混淆）

| 说法 | 含义 | 用在哪 |
|---|---|---|
| 「**域内**」 | **M2 判据自己的范围**（3–5 块并发、第 10 轮插入、8,192 ctx） | 验收条件只认这个 |
| 「**域外**」 | 该范围之外、但**部署里可能真实发生**（如 `n_ctx=600` 的小模型配置） | **契约测试** |
| 「**不可能触发**」 | 参数自相矛盾或物理上不存在（如 9.57 token 池） | **删** |
⇒ **三档不许混用**：把「域外」说成「不可能触发」会误删真判据；把「域外」算进验收会拿假保证充数。**G.113 的名单要按这三档重述，我已在 G.116 修正 S3b 与 S6 两格。**


### G.118 planner 效果断言现状：lead 的 grep 已过期，防线已经在了（原子读）

原子读（同一次读盘内取 sha16 + 计数 + mtime）：planner.py 6989 B / mtime 05:23:21Z / sha16 0f64475345e9ef2c。
| token | 出现次数 |
|---|---|
| moved | 16 |
| readback | 10 |
| visible | 16 |
| verify | 2 |
| PlanInvariant | 13 |
| assert | 0（中性：用 raise PlanInvariant 而非 assert，Python -O 下 assert 会被剥掉，这里反而更稳） |

代码实体（同一次读盘所得）：
| 位置 | 内容 |
|---|---|
| apply_insert docstring | 「操作成功 !＝ 操作生效；返回码不算证据，读回状态才算」 |
| _readback_visible() | 不看返回码，只问「现在看得见吗」（eng.visible(seq,lo,hi)） |
| 第 1 步 drop 后 | 读回仍可见 ⇒ raise PlanInvariant「drop 未生效」 |
| 第 2 步 | n_chat = cells_of(chat) − Σ区间长；moved_ok = (moved == n_chat)，不成立 ⇒ raise「repos_local 生效不足」 |
| 第 3/4 步 | 新块与重挂块读回必须可见，否则 raise |

⇒ 结论：lead 查到的「moved 0 处 / readback 0 处」是 2827 B 那一版的事实；该版本已不在磁盘。当前版把整条纪律写进代码，且比我建议的更硬（不是记 moved，而是 moved == 期望 cell 数 才放过）。
⇒ 「已知缺陷仍在」不成立；「假绿候选」已消解。但方法教训成立，且这次轮到 lead：

> grep 结论必须带文件 sha16 + mtime，否则就是「拿旧核验对新文件」—— 正是 lead 本轮反复要求我做的那件事（G.106 / G.113）。

检测员动作：今后凡报「代码里没有 X」必带文件版本；凡收到「没有 X」先核版本。


### G.119 纪律：重跑之前先问「这次的仪器比上次多看见什么」

> 第一次成功的读数，是由一台事后才发现「对该失败模式失明」的仪器产生的。用同一台仪器再跑一次，得到的不是更强的证据，是同一份证据的第二份拷贝。

与「漂亮的绿」成对：那条问「绿是用什么喂出来的」，这条问「仪器比上次多看见什么」。
⇒ 判法：答不出「多看见什么」，重跑不计入补强，只能记为复现性检查。
⇒ 检测员可执行化：仪器升级的证据应是新的字段 / 新的读回点（如 moved_ok、readback_visible、expected_moved），而不是「这次通过了」。

### G.120 fact_ok 的定义原文 ⇒ §13.4 ② 的证据等级 = 「归一化子串命中」，不等于「答案正确」

定义原文（tools/m2_visibility_probe.py L164–167，照录）：

    def fact_ok(fact, ans):
        if not fact:
            return False
        return norm(fact) in norm(ans)

⇒ 它是一个「归一化后的子串包含」判定：无长度检查、无位置检查、无排除性检查。
| 缺什么 | 后果 |
|---|---|
| 无长度检查 | 109 B → 49 B（输出减半）仍判 true —— 实测已发生 |
| 无位置检查 | 答案里复述提问含该词也判 true |
| 无排除性检查 | 把四块事实全复述的答案也判 true（lead 要求的「不得出现其他块事实词」= 0 处实现） |

⇒ §13.4 第 ② 条目前等级判定：
| 层级 | 状态 |
|---|---|
| 文档措辞 | 「答案仍正确」（§13.4 L1775 与 §13.9 L1829 均含此四字） |
| 实际证据 | 归一化子串命中（fact_ok）+ 返回字节数 |
| 判定 | 证据等级 = 「命中关键词」，不是「答案正确」；两者不得默认相等 |
| 可红性 | 能（in 可为假）；但对「正确」无实例 —— 无「命中而答案错」的样本 ⇒ 属无实例 |

实测形态（不再是理论担忧）：插入前 109 B、插入后 49 B，两次 fact_ok=true ⇒ 输出差一倍多，判据完全看不见。
另有一条反面样本：insert_probe v1 那次 answers.after 为空串（ok=false）、四步全 ok、blocks_undisturbed=true ⇒ 「四步全 ok 而答案没了」，是「操作成功 ≠ 生效」在答案层的活证据。


### G.121 moved 45 自洽（算术）：45 是「被移动的 cell 数」，12 是「位移」；两者不是同一个量

数据来源：out/INSERT-REAL2.json（v2）与 out/INSERT-REAL.json（v1）；两次运行都记了 chat 区间。
| 量 | 值 | 式 | 核 |
|---|---|---|---|
| chat.first_turn | [4096, 4141) | 4141 − 4096 | = 45 ✓ |
| chat.after_insert | [4108, 4153) | 4153 − 4108 | = 45 ✓ |
| 位移 | +12 | 4108 − 4096 = 4153 − 4141 | = 12 ✓ |
| repos_local 返回 | moved = 45 | = 对话自身 cell 数 | ✓ |
⇒ 45 与 +12 完全自洽：45 = 被移动的 cell 数，12 = 位移。hi 为开区间（4141−4096 = 45 与 ntok 45 一致）。

⇒ 但这里冒出一个新的「一个词指两样东西」：moved。
| 读法 | 值 | 差 |
|---|---|---|
| moved = 被移动的 cell 数 | 45 | —— |
| moved = 位移量 | 应为 12 | 3.75 倍 |
⇒ 建议：字段拆成 cells_moved = 45 与 delta = 12 两列；否则「moved 45」会被读成「推了 45 格」。
这与 G.110 的 base 同族：不是一义多名，而是同一字段名可承载两种量。

insert_elapsed_ms 可复算（我复算两次，都对得上）：
| 运行 | 步耗时之和 | 减去 load_and_place | 记的 insert_elapsed_ms | 差 |
|---|---|---|---|---|
| v1 | 199.0+0+139.6+39.8+0 = 378.4 | 378.4 − 199.0 = 179.4 | 179.5 | 0.1（四舍五入） |
| v2 | 195.4+0+123.3+38.7+0 = 357.4 | 357.4 − 195.4 = 162.0 | 162.2 | 0.2（四舍五入） |
⇒ 两次口径一致（插入四步、不含 load_and_place），可复算 ✓ —— 这是本轮少见的一个「数经得起复算」的正面样本。

速率：123.3 ms / 45 cell = 2.739 ms/cell ⇒ RESULTS 写的 2.74 正确 ✓。
但注意：这 45 个 cell 的位移只有 12 —— 若 repos_local 的成本随位移而非 cell 数增长，2.74 ms/cell 这个名字会误导；口径应写「2.74 ms 每被移动 cell」。


### G.122 三块位置不变：核过是对的，但它的信息量比看上去小；并附一处对 G.111 的正面补充

我核了两份 JSON（v1 / v2），block_pos_max 插入前后完全相同：home 4095→4095、project 4031→4031、habit 3967→3967，unchanged = true。
⇒ 与冻结几何一致 ✓（lead 已核，我复核一致）。

但它的信息量小，有两层原因：
1. 新块落在 [4096, 4108)，位置在三块之上、对话之下 ⇒ 插入点没越过任何既有块 ⇒ 「不拖块」（S4）在此场景几乎平凡成立。
2. 三块位置一位未变 ⇒ 几何约束（S1）没有被施压 ⇒ 这次真机测试对 S1 几乎不提供新信息。
⇒ 所以这次真机插入对域内四条的意义是：S4 得一条（弱）绿、S1 无新信息、S5 仍未给、S3a 未涉及。

对 G.111 的正面补充（这条 lead 问过两个分支，现在有实据）：
真机扫描 cell_scan_after.gaps = [46, 43]，与套件 SPEC 的 {1:43, 2:46} 同值（顺序相反，取决于扫描方向）。
⇒ 结论修正为更准确的一句：43/46 这两个数确有真机来源（由 cell_scan 扫出，不是凭空编的）；但它们被作为「答案」喂回 planner，所以 S1m 仍然是回归锁，不是「推导出空隙」的证据。
⇒ 两个分支的答案因此是：来源是反推（从既有布局扫出来），反推的数据本身是真的。这不改变 G.111 的结论，但把它的语气摆正了。

### G.123 速率措辞核 + 文档三处批改未落地（无越界）+ 一处边界冲突需 lead 裁

核时文档身份（G.43）：PROGRESS-AND-ROADMAP.md sha16 17338f0fc5930c5a / 187,700 B / 2,463 行（与冻结版一致，未变）。
| 批改项 | 状态 | 证据 |
|---|---|---|
| ① 48% 移出判据格 | 未落地 | L1829 仍含 48% 与 1,070,339 |
| ② §2.3 的 4.2 s 改实测 | 未落地 | L172 仍写「≈ 4.2 s（一次性，可接受但要有预算上限）」 |
| ③ 新增空白「缝宽由什么决定」进 §13.4 | 未落地 | 全文 grep「缝宽」= 0 命中 |
⇒ 三处均未做，且我抽查确认没有多改：
| 抽查 | 结果 |
|---|---|
| 文档是否出现 13.7（秒） | 仅命中章号「### 13.7 训练路线」⇒ 无 13.7 s ✓ |
| 文档是否出现 2.74 | 0 命中 ✓（实测数未搬进文档） |
| 文档是否出现「下界」 | 0 命中 ✓ |

RESULTS 侧措辞（允许保留，但缺可检索标记）：
RESULTS-RED.md L207 写「123.3 ms / 45 cell = 2.74 ms/cell」（实测 ✓）；L208 写「按此线性外推 5000 token ≈ 13.7 s」（外推）。
L209 已有散文限定「外推仍是外推（cell 数增大后未必线性、也含 cell_scan 成本），所以不设门，只记」⇒ 限定在，但没有规范标签。
⇒ 建议补一个可 grep 的标签【外推·未验线性】，因为散文限定检索不到，而「检索不到的限制等于没有限制」。

⇒ 一处边界冲突，需 lead 裁定（我不自行处理）：
lead 要求「答案仍正确 四字不得用于描述 fact_ok」，但该四字在文档里出现在两处：L1775（§13.4 验收②）与 L1829（§13.9 判据格）。
而本轮批改单只列三处，不含这两行 ⇒ 两条指令在同一文件上打架。
| 选项 | 后果 |
|---|---|
| A. 把这两行并入本批（变五处） | 违反「批只三处、多改算越界」 |
| B. 明写「文档留到下一批，本轮只改 RESULTS」 | 保住了冻结纪律，但文档会继续宣称「答案仍正确」 |
检测员建议 B，理由：文档已冻结、这两个词不改变判据的可执行性（判据本身仍是「答案正确」，只是当前证据只到关键词命中）—— 它属于「证据等级不足」，不是「判据错误」，可以留到 M2 收尾批一起改，但必须在台账写明：文档现宣称的证据等级高于实际。


### G.124 边界冲突裁定：采纳 B，**批改单扩成四处**（第四处 = 证据等级）

lead 裁定：这是**证据等级不足**，不是**判据错误** —— 判据仍是「答案正确」，只是当前证据只到关键词命中。
⇒ 但「留到下一批」不等于「这一批原谅」：**批改单正式扩成四处**。
| # | 处 | 内容 | 状态 |
|---|---|---|---|
| 1 | §13.9 L1829 | 48% 移出判据格 | 未落地 |
| 2 | §2.3 L172 | 4.2 s 改实测 | 未落地 |
| 3 | §13.4 | 新增空白「缝宽由什么决定」 | 未落地 |
| **4** | **L1775 + L1829** | **「答案仍正确」→「事实关键词命中（fact_ok），非答案质量」** | **本批新增，未落地** |

⇒ 台账写法按 lead 要求带期限（**没有期限的已知缺陷，就是永久缺陷**）：

> **文档现宣称的证据等级高于实际；处置 = M2 收尾批第 4 项。**

### G.125 已派项登记（拆列与标签成对）

| 项 | 内容 | 检测员将来的核法 |
|---|---|---|
| moved 拆列 | cells_moved(45) / delta(12) 分开 | 两个字段都在，且 45 与 12 不得合并在同一列 |
| 13.7 s 标签 | 【外推·未验线性】 | 标签可 grep |
| 2.74 ms/cell 标签 | 【实测】 | 标签可 grep |
| **成对要求** | **两个标签必须成对出现** | **只出现一个 ⇒ 视为未完成**（单独一个标签会把外推读成实测，或反之） |

执行者另被要求：**贴 v2 原始答案字符串全文**，不接受「同句」这种复述。
⇒ 检测员的核法：**逐字符比 v2 的 answers_after.answer 与 v1 的 answers.before.answer**；两者是否同一串，由字节决定，不由描述决定。


### G.126 v1 那个样本：我补一次逐字节复核（不等执行者自述）

lead 说这是本轮最重要的一条（`answers.after` 空串 + 四步全 ok + `blocks_undisturbed=true` 三件事同时成立）。
我直接从两份 JSON 取原文，不转述：
| 运行 | answers 字段 | 值 | 类型 |
|---|---|---|---|
| v1 (INSERT-REAL.json) | answers.after.answer | "" | 空串 |
| v1 | answers.after.len | 0 | 数值 |
| v1 | answers.after.ok | false | 布尔 |
| v1 | answers.after.return_bytes | -1 | 数值 |
| v1 | answers.before.answer | 项目代号蓝鲸，计划 3 月 14 日上线。 + 思考段 + 同句 | 109 B |
| v1 | verdict.answer_still_ok | false | 布尔 |
| v2 (INSERT-REAL2.json) | answers_after.answer | 项目代号蓝鲸，计划 3 月 14 日上线。 | 49 B |
| v2 | answers_after.ok | true | 布尔 |
| v2 | answers_before.answer | 同 v2 after 的句子再 + 一个思考段 | 109 B |

⇒ 逐条说明：
1. **v1 的 `after` 是真空串**（len 0、return_bytes −1），不只是「短」⇒ 「四步全 ok 而答案没了」成立 ✓
2. **v1 自己的 verdict 也写了 `answer_still_ok: false`** ⇒ 执行者当时**没有把这个失败包装成成功**，这点要记在它名下（诚实）。
3. **v2 的 after 答案 49 B 与 v1 的 before 那 109 B 不是同一串**：v1 before 含思考段（`...\n\n\n...` 复述），v2 after 只有一句。⇒ **lead 要求贴全文是对的**：只写「同句」会掩盖「思考段消失」这件事。
4. **引出一个新问题**：思考段为什么在 v2 里消失？——**这一问我不能答，因为 v1 根本没记 ask_pos**（v2 记了 4096 与 4153；v1 的 answers 里无此字段）⇒ **属「读数没落盘」，不是「读数不存在」** ⇒ 不能把「答案变短」归因于插入，也**不能排除**归因。
⇒ 这条要写进 RESULTS（改写为诚实版）：**v1 未记 ask_pos、v2 记了（4096 / 4153）⇒ 两次答案的差异既不能归因于插入，也不能排除插入。** 要做对照，须**同一 ask_pos 上、插入前后各问一次**，且两次都落 ask_pos 字段。
⇒ 附带一条动作项：**ask_pos 必须成为必填字段**（本轮 v1 缺它，导致一条本来可判的对照变成不可判）。


### G.127 「思考段」实测是什么：**空 think 标签 + 重复句**，不是思考内容（我逐字符核了）

原文 repr（两次 before 完全相同）：

    项目代号蓝鲸，计划 3 月 14 日上线。\n****\n\n项目代号蓝鲸，计划 3 月 14 日上线。

| 运行 | 字段 | len | bytes | 换行 | repr 要点 |
|---|---|---|---|---|---|
| v1 | answers.before.answer | 53 | 109 | 3 | 事实句 + 空 think 标签 + 重复句 |
| v1 | answers.after.answer | 0 | 0 | 0 | 空串 |
| v2 | answers_before.answer | 53 | 109 | 3 | **与 v1 before 逐字节相同** |
| v2 | answers_after.answer | 21 | 49 | 0 | 只有事实句 |

⇒ 关键事实：think 标签前面**没有任何内容**（`。` 紧跟 ``）⇒ **「思考段」是空的**。
⇒ 所以 v2 后答案少掉的东西是：**一个空 think 标签 + 一个重复句**，**不是一段思考内容**。
⇒ **实质事实句在两次里都在** ⇒ `fact_ok` 两次都真，与这一处差异无关。

**⇒ 这修正了「少的不是长度，是整段思考」这句话**：准确说法是「**少的是一个空标签与一段重复**」。
**为什么这个修正重要**：它改变了对照运行的判读标准 —— 要判的是「**Q2 是否仍带  包装与重复句**」，**不是**「Q2 还有没有思考」（两次的思考都是空的，问「有没有思考」永远得不到答案）。

### G.128 对照运行的设计（按 D0 那次的做法），判读标准已按 G.127 修正

**已确认的前提（我核的，不用重跑）**：v1 与 v2 的 before 答案**逐字节相同**（53 字符 / 109 B）⇒ **before 条件可复现** ⇒ 对照只需插入一个变量。
**因此只需一次对照运行**（不必三组）：

    对照组：完全不插入，同一组块、同一问题，连续问两次
      Q1 -> answer 全文 + ask_pos
      Q2 -> answer 全文 + ask_pos

| Q2 的答案形态 | 判读 | 对 §13.4 ② 的影响 |
|---|---|---|
| 仍带  与重复句 | 消失**与插入相关** | 证据等级再降一档，须写 RESULTS |
| 已无  与重复句 | 消失**与插入无关**（本来就会） | ② 只看事实句是否命中 |
**录制要求**：两次都必须落 ask_pos（含来源：raw_pos_max+1 还是别的）与 answer 全文。

**⇒ 方法学记录（lead 点出，我照录）**：我先把「两次 ask_pos 不同 4096 vs 4153」写成结论，核字段后发现 v1 没落 ask_pos，于是改成「既不能归因，也不能排除」。
> **从「不能归因」退回「既不能归因也不能排除」，是把结论变弱 —— 而变弱在这里才是对的。**
**⇒ 立一条可执行判法**：**一个否定断言（「不能 X」）需要与被否定的肯定断言同等强度的证据。** 我原句的证据只够说「没记」，不够说「不同」。


### G.129 你要查的「原始 token 流」：**字段不存在**；而且我用代码排除了你自己给的第 ① 个分支

**一、INSERT-REAL2.json 里没有 raw / token 流字段**（顶层键只有）：

    schema layout target n_new_cells inserted_block steps
    answers_before chat insert_elapsed_ms block_pos_max answers_after
    cell_scan_after expected verdict

⇒ 你要的那一问**当前无法回答**：属**读数没落盘**（第三次）。注意 `_driver2.py` L176 确有 `res["raw"]`，但那是 `{live_pos_max_raw, cell_count}`，**不是 token 流**，别被字段名骗。

**二、但我用代码排除了你的第 ① 个分支（「录制时被剥掉」）**：
| 位置 | 代码 | 它会不会删掉 think 内容 |
|---|---|---|
| `_driver2.py` L113-119 | `ans = buf.value.decode("utf-8", "replace")` | **不会**，原文解码 |
| `insert_probe2.py` L25 | `"answer": a.strip()` | **不会**，`strip()` 只去**两端空白** |
⇒ **结论：`answer` 是 `raw.strip()`，不是「清理后的答案」。一个以 `。` 开头、中间夹着空 `` 的串，靠 `.strip()` 产生不出来。**
⇒ **所以原始输出本身就是「事实句 → 空 `` → 重复句」这个形态。** 这不是被剥掉，也不是从中间被切（串尾是完整句「。」）。

**三、【未判定·最佳解释】第三解释（比 lead 的两分支更省假设；`raw_len`/`stripped_len`/`n_tokens` 一到可能被推翻）**：**这次生成本身就退化**：模型先写完答案，再开一个空的 think 块，然后把同一句重复一遍。
| 观察 | 与之相符 | 与之不符 |
|---|---|---|
| `。` 紧跟 `` | 空 think 块 | 「被剥掉」会留下**内容缺失**但不会留下空标签 |
| 串尾是完整「。」 | 生成正常结束 | 「从中段开始」应表现为开头缺字 |
| 前后两半是同一句 | 重复/退化循环 | —— |
⇒ 唯一无法排除的是 **`n_predict=64` 撞上限**（L20 默认 64）：若撞上限，可能截在第二个 think 块中途。**但撞上限不会产生「空标签+重复」这个组合**，只会更短。

**四、动作项（比结论重要）**：`answer` 字段缺两样东西，导致上面这些问题都只能推断不能判定：
| 缺什么 | 后果 |
|---|---|
| `raw_len` 与 `stripped_len` 两个数 | 无法判断录制有没有改动原文 |
| token 数（`n_tokens` 前后差值） | 无法判断是否撞 `n_predict` 上限 |
⇒ 这两个都是**已有 API 能力**（`n_tokens(eng,seq)` 就在 `_driver2.py` L122），只是没落盘。

### G.130 这句「不下结论，只提出可查法」我记为方法正面样本

lead 在本条里明确写「**我不下结论，只提出可查法**」，并**主动声明它与既有等级无关**（「即使 tag 是空的，事实句仍然命中 —— 我不拿这个去动摇 ② 现有的等级」）。
⇒ **这是本轮第一次有人先划清「这个新问题能动摇什么、不能动摇什么」再提问。** 值得照录：**提问也要声明影响范围**，否则一个新发现会顺手把已定的结论一起推翻。
⇒ 检测员对应动作：**收到新问题时先问「它若成立，会推翻哪一条已定结论」**；若答「不推翻任何一条」，就把它当**并行问题**处理，不重开已决项。


### G.131 第四次「读数没落盘」⇒ 从教训升级为 **schema 的一部分**（不靠自觉）

lead 定：**ask 类产物必须含四个字段，缺一即视为产物不合格**，写进 **schema 校验**。
| 字段 | 来源 | 能力是否已有 | 未落盘的后果 |
|---|---|---|---|
| `ask_pos`（+来源） | `raw_pos_max+1` 等 | 有 | v1 缺它 ⇒ 一条本来可判的对照变成不可判 |
| `raw_len` | `len(buf)` | 有 | 无法判断录制有没有改动原文 |
| `stripped_len` | `len(a.strip())` | 有 | 同上（与 `raw_len` 之差即「被 strip 掉多少」） |
| `n_tokens`（**前后各一次**） | `n_tokens(eng,seq)`（`_driver2.py` L122） | **有，现成** | 无法判断是否撞 `n_predict` 上限 |

**四次同类（本轮全部）**：`across_layouts`（判据要的对照没落盘）→ `ask_pos`（v1）→ `raw_len`/`stripped_len`/`n_tokens`（第三次）→ 而 `res["raw"]` 的同名陷阱是第四个面。
**⇒ 定性**：这不是四次疏忽，是**同一个结构性缺陷**：**产物是「跑通后顺手 print 的东西」，不是「按判据需要设计的记录」。**
**⇒ 检测员判法**：看一份产物，先问「**这份产物能回答哪些判据的问题**」；答不出的判据，就是**要补的字段**，不是**要重做的实验**。两者成本差一个量级。

### G.132 M2 收口包：九项清单（一次列清）+ 我逐项的可核产物

**收口判据（lead）**：九项各有可核产物 ⇒ 最终验收 ⇒ 冻结解禁。**中间不再改文档。**

| # | 项 | 我给的可核产物（无此项即不通过） |
|---|---|---|
| 1 | 对照运行 Q1/Q2 | 两次 `answer` 的 **repr**（不是描述）+ `ask_pos`(+来源) + `raw_len`/`stripped_len`/`n_tokens`；判读只看「**是否仍带空 `` 与重复句**」 |
| 2 | `cells_moved`/`delta` 拆列 | 两个字段**都在**，且 **45 与 12 不在同一列** |
| 3 | RESULTS 标签成对 | 【实测】与【外推·未验线性】**同时出现**；**只出现一个 ⇒ 未完成** |
| 4 | 带效果断言重跑真机插入 | 每步有**读回**（`moved` 对期望值、`drop`/`share` 读回可见）；且须说明**仪器比上次多看见什么** |
| 5 | `FIELDS.md` | 只登**跨文件**字段名；每条能区分同名者的所指 |
| 6 | L1829 的 48% → 字段指针 | 判据格里**无裸数**；指针能指到具体字段 |
| 7 | L172 的 4.2 s → 实测 + 「更大规模未测」 | 两个半句都在；**不得出现「下界」** |
| 8 | §13.4 新增空白「缝宽由什么决定」 | 空白入正文，且**写明无人回答** |
| 9 | L1775 + L1829「答案仍正确」→「事实关键词命中（`fact_ok`），非答案质量」 | **两处**都改；改后不得再出现「答案仍正确」描述 `fact_ok` |

**⇒ 我的验收顺序（先便宜后贵）**：5 → 2 → 3 → 9 → 6 → 7 → 8 → 1 → 4。
**理由**：前七项是**读文件**（分钟级）；第 1 项要跑对照（GPU）；第 4 项是真机插入（GPU + 最长）。**先做完能立刻判死的，再花钱跑仪器。**

**⇒ 一处我要提前说明的风险（第 4 项）**：`planner.apply_insert` 现在**要求 eng 提供 `visible(seq,lo,hi)`**（G.118）。若真机 `eng` 没有这个方法，第 4 项会**卡在接口缺失**，而不是卡在断言失败 —— **两者性质不同**：前者是**没接上**，后者是**接上了但没通过**。**届时不许把「没接上」记成「通过了」。**


### G.133 第 4 项卡住时的**先试路径**：读回可在 harness 层用现有 API 组合（附一个我踩过的坑）

lead 指示的顺序：**先试 harness 层读回 → 试不出来才判「未接上」→ 判了也必须留在九项里。**
| 要验证的事 | harness 层可用的组合 | 注意 |
|---|---|---|
| `drop` 后应**不可见** | `n_tokens(eng, chat)` 或 `pos_max` **前后差** | 用差值，不用绝对值 |
| `share` 后应**可见** | `pos_max(chat)` / `raw_pos_max` 是否**覆盖**该区间 | **必须交叉验证**（见下） |
| `repos_local` 是否真移动 | `raw_pos_max` **前后差** vs 期望 `new_cells` | 这正是被打回的那处（`moved` 对期望） |

**⚠ 坑（我上一轮踩过的）**：`eng.pos_max(LIVE)` 对 **share 进来的 cell 返回 −1** ⇒ **读回不能用 `pos_max` 单打**，须 `raw_pos_max` 或 `n_tokens` **交叉验证**。
**⇒ 一般化（lead 补半步后定稿）**：**任何读回至少跨两层读数**；单读数无法区分「没生效」与「这个方法看不见这类 cell」——**后者会伪装成前者，两个方向都能骗人。**

### G.134 lead 会独立读产物、不采信任何转述（含我的表）—— 我据此调整报告方式

lead 原话：**「不采信任何一方的转述，包括你的表」**；理由：**「做的人和核的人都会在『我以为我核了』上出错」**。
**⇒ 这是对等的，我接受，并按它改我的报告方式**：
| 以前 | 以后 |
|---|---|
| 给结论表（「九项通过」） | 给**指针**（文件 + 行号 + 字段 + sha16），结论由读者自取 |
| 写「我核过了」 | 写「**我对哪几个字节做了哪次比较**」 |
**⇒ 我保留的独立职责**：**指出他没看到的**（如版本过期、口径混用、别名陷阱）。**这不是否决他的读数，是补他没覆盖的面。**


### G.135 五项「通过」我逐项独立复核（不采信转述，含 lead 的表）

**文档身份（我自己读盘）**：188,430 B / 2,466 split（2,465 换行）/ sha16 5ecd33e1295424d9 / mtime 05:30:29.559Z ⇒ **与 lead 报的三个数一致** ✓
| 检查项 | 我的读数 | 与 lead 一致 |
|---|---|---|
| 48% | 0 命中 | ✓ |
| 1,070,339 | 0 命中 | ✓ |
| 「答案仍正确」 | 0 命中 | ✓ |
| 「下界」 | 0 命中 | ✓ |
| 缝宽空白 | 1 处，在 **L1779** | ✓ |
| M2 判据行 | **L1831**，含 own_repos_rewrite 指针，且已改为「事实关键词命中（fact_ok），非答案质量」 | ✓ |
| 换行 2,463 → 2,465 | +2 | ✓（与「§13.4 新增一段」一致） |
⇒ 五项通过我复核无异议。**注**：我给的行号只是**辅助**（G.137 那条规矩），真标识是 sha16 + 内容锚。

### G.136 行号漂移：我把 lead 那个差错的**机制**复现了一遍
lead 的误读不是粗心，是**结构性的**：§13.4 那段插在 **L1779**，而它**在被引用的表之上** ⇒ 表整体下移 **2 行**。
⇒ 这意味着：**任何「按记忆里的行号去读」的操作，只要有人在更靠前的位置合法加行，就会静默读到错误对象。**
⇒ 我这条规矩落地成四件套：**文件 + sha16 + 内容锚 + 行号**；**行号永不起定位作用。**

### G.137 第六例「同名异指」已在纪律区立规：文件名同样会撞车
lead 的盘点脚本用 basename 作键 ⇒ 两个 FIELDS.md 撞车。**我把它与「行号不是标识」合成一条**（定位不是标识），并附执行动作：**盘点脚本一律用相对路径作键。**


### G.138 156.9 的出处查清了：**三个数是三样东西**，而文档把其中两样并列了

| 数 | 出处（文件 + 字段） | 它是什么 |
|---|---|---|
| **123.3 ms** | INSERT-REAL2.json（93b752e83ad37a7c / 05:20:33）→ steps[3].elapsed_ms | **repos_local 单步**耗时（v2） |
| **156.9 ms** | INSERT-REAL3.json（9e7d705784ac0d8f / 05:27:06）→ **op_ms.repos_local** | **repos_local 单步**耗时（v3） |
| **162.2 ms** | INSERT-REAL2.json（同上）→ **insert_elapsed_ms** | **插入四步总计**（不含 load_and_place） |
⇒ **123.3 与 156.9 同质**（都是单步，两次不同运行）；**162.2 不同质**（是总计）。

**⇒ 于是 L172 的写法有一个具体的问题**：现在写「**123.3 ms 与 156.9 ms 两次（2.74 ms/cell，两次有波动）**」。
| 数 | 除以 45 | 是否等于 2.74 |
|---|---|---|
| 123.3 | **2.740** | ✓ |
| 156.9 | **3.487** | **✗** |
⇒ **2.74 ms/cell 只能由 123.3 得出，却写在了两个数后面** ⇒ 读起来像「两次都是 2.74」，实际第二次是 3.49。
⇒ **正确写法**：「repos_local 单步 123.3 ms（v2）与 156.9 ms（v3），**相差 27%** ⇒ 此量有波动、不能当常数；**2.74 ms/cell 只由 v2 得出**」。
**旁证（RESULTS 侧已写对）**：RESULTS-RED L369 已写「两次实测相差 ~27%，说明这个量本身有波动，不能当常数」——**27% = (156.9−123.3)/123.3 = 27.3%** ✓ 与我的算术一致。**⇒ 错在文档那一句，不在 RESULTS。**


### G.139 第 1 项与第 4 项：**产物在，但不在预期的文件名里** ⇒ lead 判的「未做」是**假红**

**盘上实有五个真机插入产物**（同目录 out/）：
| 文件 | bytes | sha16 | mtime |
|---|---|---|---|
| INSERT-REAL.json | 2,065 | 05fdb60d744c3569 | 05:17:58 |
| INSERT-REAL2.json | 2,047 | 93b752e83ad37a7c | 05:20:33 |
| INSERT-REAL3.json | 4,003 | 9e7d705784ac0d8f | 05:27:06 |
| INSERT-REAL4.json | 5,647 | 464a7a18eb3b5099 | 05:29:22 |
| **INSERT-REAL5.json** | **6,538** | **8ffb5ef47edb6d76** | **05:31:40** |
⇒ lead 查的是 **INSERT-REAL2**（05:20:33），**v3/v4/v5 分别在 05:27 / 05:29 / 05:31 落地**。

**第 1 项（对照运行）：证据在 v4/v5 的 control_no_insert 里，字段齐全**（不是 CONTROL-2ASK.json 那个文件名）。
| 字段 | Q1 | Q2 |
|---|---|---|
| ask_pos | 4096 | **4141** |
| ask_pos_source | raw_pos_max(eng,LIVE)+1 | 同 |
| return_bytes / raw_len / stripped_len / len | 109 / 53 / 53 / 53 | 49 / 21 / 21 / 21 |
| n_tokens 前后 | 0 → 45 | 45 → 71 |
| answer repr | 事实句+空 think 标签+重复句 | **只有事实句** |
| fact_hit | true | true |
⇒ **判读**：对照组 Q2（**不插入**）**也没有**那个空 think 标签 ⇒ **标签消失与插入无关** ✓ 与 lead 提出的判读表一致。
⇒ **⇒ 第 1 项应判「通过」而非「未做」**；四态里「未做」是「没动手」，而这里**动了、且产物在**。

**⚠ 但有一处必须同时记下（新的字段名/所指不符）**：v5 的 `thinking_in_Q1 = false`、`thinking_in_Q2 = false`，**而 Q1 的 answer 肉眼可见含 `</` 那对标签**（空的）。
⇒ 该字段实际问的是「**有没有非空的思考内容**」，却被命名为 `thinking_in_Q1` ⇒ **按名字读，Q1 明明有标签却是 false，会误导**。
⇒ 建议改名 `think_content_nonempty_in_Q1/Q2`，或另加 `has_think_tag_in_Q1 = true / Q2 = false`。**结论（与插入无关）不变，但字段名会让人读错。**

**第 4 项（带效果断言重跑）：v5 在 planner 现版之后跑过，且 op_log 逐步有读回**。
| 证据 | 值 |
|---|---|
| INSERT-REAL5 mtime | **05:31:40** > planner.py **05:31:17**（9,043 B / 4162661cc04182e8） |
| effect_assertions 字段 | 「ON —— moved 是被断言的值，不是打印的值」 |
| op_log（v3 起） | drop ×3 均 `readback_visible:false, verified:true`；repos_local `cells_moved 45 == expected 45`；share_new 与 share_existing ×3 均 `readback_visible:true` |
| 拆列后的口径（op_log 里已写） | 「delta=位移(=12)；cells_moved=被移动的 cell 数(=45)。两件事，不许同名。」 |
⇒ **第 4 项应判「通过（含保留意见）」**，保留意见见 G.140。


### G.140 保留意见：执行者报的「内容层未接上」**是错的** —— 导出存在，且本仓库已在用

v5 的 `readback_layers_summary.content_layer_status` 写：**「未接上：shim 无 token 内容读导出（kvshim_* 只有 save/load 整序列）」**。
**我核到的反证（三处，同一仓库）**：
| 证据 | 位置 |
| C 导出声明 | **tools/kvshim.cpp:232** `KVSHIM_API int kvshim_seq_tokens(kvshim * h, int seq, int * out, int cap)` |
| 14B 侧已在用 | **kvmem/m2_visibility/runs_m14b/make_blocks_14b.py:136** `n_seq = int(eng.lib.kvshim_seq_tokens(eng.h, 2, seq_toks, 4096))` |
| 另两处在用 | `make_t032_blocks.py:81`、`make_blk_G_bos_c18.py:86` |
⇒ **「无导出」不成立。按四态，「内容层」应为「未做」，不是「未接上」。**

**为什么这个区分要紧（lead 定的四态就是为这个）**：
| 若判 | 后果 |
|---|---|
| 未接上 | 读起来像**能力不存在** ⇒ 没人再去试 ⇒ 内容层永久缺失 |
| **未做** | 只是**没接** ⇒ 下一轮可以直接做 |
**⇒ 这正是四态要防的那种「用错状态把可做的事写成做不了」。**

**执行者那句话里唯一可能成立的部分**：`kvshim_seq_tokens` 读的是**整序列** token；「按位置区间读某几个 cell 的内容」需要自己切，而 **position→offset 的映射**确实没有文档。
⇒ 但这只说明**要自己算切片**，不说明**读不出来**。⇒ **未做**（成本是写几行切片），不是未接上。

### G.141 本轮四态的完整记账（我按 lead 的起点重记）

| # | 项 | 四态 | 依据 |
|---|---|---|---|
| 1 | 对照运行 | **通过** | INSERT-REAL4/5.json 的 control_no_insert（六字段齐全，Q2 无空标签） |
| 2 | cells_moved / delta 拆列 | **通过** | op_log 内写明「两件事，不许同名」；45 与 12 分列 |
| 3 | 标签成对 | **通过** | 【实测】2 处 +【外推·未验线性】1 处，同文件 |
| 4 | 带效果断言重跑 | **通过（保留）** | v5 mtime 晚于 planner 现版；op_log 逐步读回 |
| 5 | FIELDS.md ×2 | **通过** | 3,314 B / 612 B（lead 已读，我未重核这两个文件内容） |
| 6 | 48% → 指针 | **通过** | L1831 含 own_repos_rewrite；裸数 0 |
| 7 | 4.2 s → 实测 | **通过（附一处**必改**）** | L172 已改；但「2.74 ms/cell」挂错位置（G.138）⇒ **须修这一句** |
| 8 | 缝宽空白 | **通过** | L1779，含 43/46 反推算术 |
| 9 | 「答案仍正确」两处 | **通过** | 全文 0 命中；L1831 已是「事实关键词命中，非答案质量」 |

⇒ **8 项通过 + 1 项通过但须修一句（第 7 项，G.138）**；**内容层（第 4 项的子层）判未做**，不计入九项，但须记在 RESULTS。
⇒ **另须补一处改名**（第 1 项内）：`thinking_in_Q1/Q2` → 名实相符（G.139）。


### G.142 v6 我核了（**我自己也漏了它**）：lead 的读数全部复现，但两处改名**仍未落地**

**枚举（readdir，不硬编码）**：out/ 共 **124** 个文件，其中匹配 INSERT 的 **7 个 = 6 次真机运行 + 1 个定位诊断**：
| 文件 | bytes | sha16 | mtime |
|---|---|---|---|
| INSERT-LOCALIZE.json | 3,965 | f77c796d6fbb5e00 | 05:18:36 |
| INSERT-REAL.json (v1) | 2,065 | 05fdb60d744c3569 | 05:17:58 |
| INSERT-REAL2.json (v2) | 2,047 | 93b752e83ad37a7c | 05:20:33 |
| INSERT-REAL3.json (v3) | 4,003 | 9e7d705784ac0d8f | 05:27:06 |
| INSERT-REAL4.json (v4) | 5,647 | 464a7a18eb3b5099 | 05:29:22 |
| INSERT-REAL5.json (v5) | 6,538 | 8ffb5ef47edb6d76 | 05:31:40 |
| **INSERT-REAL6.json (v6)** | **6,794** | **8f91d8127485458a** | **05:34:04** |
⇒ lead 说「7 个 INSERT 产物」：**数目对，构成要修正** —— 其中 1 个是 `INSERT-LOCALIZE`（定位诊断），**真机运行是 6 次（v1–v6）**。

**v6 逐项复核（我读的，不是转述）**：
| 项 | 值 |
|---|---|
| `block_pos_max` | before = after = {home 4095, project 4031, habit 3967}，unchanged true ✓ |
| `effect_assertions` | 「ON —— moved 是被断言的值」 ✓ |
| `op_log` | **8 步**：drop×3（readback_visible false）+ repos_local（cells_moved 45）+ share_new + share_existing×3（readback_visible true）✓ |
| `control_no_insert.Q1` | ask_pos **4096**，return_bytes 109，raw_len 53，n_tokens **0→45**，answer 含空 think 标签 + 重复句 ✓ |
| `control_no_insert.Q2` | ask_pos **4141**，return_bytes 49，raw_len 21，n_tokens **45→71**，answer **只有事实句** ✓ |
| `verdict` | `fact_keyword_hit_before/after` ✓（**命名已改对**） |
| `provenance` | planner_sha16 **4162661cc04182e8** / probe_sha16 e027840d6f004474 / run_utc 05:33:54 ⇒ **「凭什么是最新」有了自带证据** ✓ |
| `interpretation` | 已用【未判定·最佳解释】，并写 `may_be_overturned_by` ⇒ 我那个标签被采纳 ✓ |

**⇒ 两处改名在 v6 里仍未落地（所以它们是「同批改」，不是「已做」）**：
| 项 | v6 现状 | 应改为 |
|---|---|---|
| 内容层状态 | `content_layer_status`: 「**未接上**：shim 无 token 内容读导出…」 | **「未做」**（`kvshim.cpp:232` 有导出，`make_blocks_14b.py:136` 已在用） |
| thinking 字段 | `thinking_in_Q1=false` / `thinking_in_Q2=false` | 加 `has_think_tag_in_Q1=true / Q2=false`；`thinking_*` 注明问的是「有没有**非空**内容」 |
⇒ **按四态，这两项现在是「未做」**，不阻塞 L172 的修，但不得算通过。


### G.143 阻塞项 L172：**你给的改法会第二次犯错** —— v6 给出了第三次实测 130.9 ms

**新事实（v6，05:34:04）**：`op_ms.repos_local = 130.9 ms`（同一量：45 cell 单步移动）。
| 运行 | 文件 | 字段 | 值 | ÷45 |
|---|---|---|---|---|
| v2 | INSERT-REAL2.json | steps[3].elapsed_ms | 123.3 | **2.740** |
| v3 | INSERT-REAL3.json | op_ms.repos_local | 156.9 | 3.487 |
| **v6** | **INSERT-REAL6.json** | **op_ms.repos_local** | **130.9** | **2.909** |
⇒ **实测已经是三次，不是两次。** 若按你的稿子写「**两次**实测 123.3（v2）/156.9（v3）」，**文档会立刻与盘上产物不符** —— 因为 v6 里还有一次 130.9。
**⇒ 这就是本项目反复出现的同一病：写「两次」这个计数本身，就是一个会过期的断言。**

**⇒ 我建议的写法（不含任何计数，只给三次实测与出处）**：
> 单步 `repos_local`（45 cell 对话移动，14B）已测三次：**123.3 ms**（`INSERT-REAL2.json` → `steps[3].elapsed_ms`）、**156.9 ms**（`INSERT-REAL3.json` → `op_ms.repos_local`）、**130.9 ms**（`INSERT-REAL6.json` → `op_ms.repos_local`）；**极差 27%（123.3–156.9）⇒ 此量有波动，不能当常数**；**`2.74 ms/cell` 仅由 123.3 那一次得出**，不代表均值。**【实测】更大规模未测。**
⇒ **三点好处**：① 三个数各带文件+字段（四件套）；② **不写「两次/三次」**，改用「已测三次」+ 列出，将来加一次只需追加，不必改结论；③ 明确 `2.74` 的适用范围，不再挂在两个数后面。
**⇒ 若你坚持保留计数**，那必须写「**至少三次（含 v6）**」并注明**计数会随新运行增加**。

### G.144 我的四态记账（v6 之后）

| # | 项 | 四态 | 备注 |
|---|---|---|---|
| 1 | 对照运行 | **通过** | v6 `control_no_insert` 六字段齐全 |
| 2 | 拆列 | **通过** | op_log 内「两件事，不许同名」 |
| 3 | 标签成对 | **通过** | 【实测】+【外推·未验线性】同在 |
| 4 | 效果断言重跑 | **通过（保留）** | `provenance` 自带 planner sha16 ⇒ 凭什么是最新已写清 |
| 5 | FIELDS.md ×2 | **通过** | lead 已读，我未重核内容 |
| 6 | 48% → 指针 | **通过** | L1831 含指针，裸数 0 |
| **7** | **4.2 s → 实测** | **未通过（阻塞）** | **L172 现文把 2.74 挂在两个数后；且「两次」与 v6 的 130.9 冲突**（G.143） |
| 8 | 缝宽空白 | **通过** | L1779 |
| 9 | 「答案仍正确」 | **通过** | 全文 0 命中 |
| — | 内容层状态改名 | **未做** | v6 仍写「未接上」 |
| — | thinking 字段改名 | **未做** | v6 仍只有 `thinking_in_Q*` |

⇒ **结论：8 项通过，第 7 项阻塞，两处改名未做。** 与 lead 的「九项全通过 + 一个阻塞」差一处 —— **第 7 项我判「未通过」而不是「通过但须修」**：它现在的文字是**错的**，不是**缺一句**。


### G.145 第五态收回 + 结构/观测计数分离 + provenance 升级（本轮最后一批纪律）

**① 第五态收回（lead 自犯，我据此改判）**
| 写法 | 实际意思 | 处置 |
|---|---|---|
| 「7 通过但须修」 | **未通过**，裹了一层好看说法 | **收回** |
| 「通过但须修」这个状态本身 | 四态之外的第五种 | **不存在**；四态是**封闭集** |
⇒ lead 自诊：*我想让九项一次性都过，于是给一个错的项找了个「基本上还行」的位置。*
⇒ **检测员动作**：见到「某某但……」「基本……」「大体……」，先问 **它落在四态里哪一个**；落不进就是「未通过」。

**② 结构计数 vs 观测计数（这条解释了一整轮的一次冲突）**
| 类型 | 例子 | 规矩 |
|---|---|---|
| 结构计数 | 判据几条、改几处、清单几项 | **必须同步改** |
| 观测计数 | 测了几次、跑了几轮 | **不进正文**，逐条列实例带出处 |
⇒ 取代表达：「**已测若干次，逐次如下：…**」——**加一次只需追加一行，不改任何文字**。
⇒ 现场：L172 稿写「两次」而 v6 已给第三次 **130.9 ms** ⇒ **落笔即过期**。
⇒ **我们之前的冲突因此有了名字**：「六条→七条」是结构（必须改），「两次→三次」是观测（不该进正文）。

**③ `provenance` 升为 schema 必填**
| 字段 | 值（v6 实例） |
|---|---|
| `planner_sha16` | 4162661cc04182e8 |
| `probe_sha16` | e027840d6f004474 |
| `run_utc` | 2026-10-25T05:33:54Z |
⇒ **它把「最新」从「靠 mtime 猜」变成「产物自己说」** —— 这是我这一轮见到的最实用的一条 schema 升级：**`mtime` 是谁都能改的，`provenance` 是生成时写死的。**
⇒ 我先前靠 `mtime` 判「v5 最新」而漏 v6，正是**缺这个字段**的后果；有了它，判定问「产物自称由哪版生成」，不问「文件何时被摸过」。

**④ 收口四条件（lead 定）+ 我的复核清单**
| # | 条件 | 我复核什么 |
|---|---|---|
| 1 | L172 按不含计数写法改（三数各带出处） | ① 无「两次/三次」计数；② 三数各带文件名+字段；③ 「2.74 仅由 123.3 得出」在；④ 【实测】在、且【外推·未验线性】不被误删 |
| 2 | 内容层状态改「未做」 | 全文不再出现「未接上」描述内容层 |
| 3 | `thinking_*` 加 `has_think_tag_in_Q1=true / Q2=false` | 两个字段都在，且 `thinking_*` 有「非空内容」的说明 |
| 4 | 新产物带 `provenance` | 四字段齐（`planner_sha16`/`planner_bytes`/`probe_sha16`/`run_utc`） |
**⇒ 复核方式**：读盘取 sha16 + 新文字，逐项给**指针**（文件+sha16+内容锚），不给结论表。

**⑤ 关于 lead 那句「你每次都不是反驳我，是把我那句话放回到它该有的强度上」**
我把它当作本角色的定义，并补一句边界：**放回强度，不等于替他决定。**
⇒ 我能做的：指出**证据到哪一层**、**口径是哪一种**、**版本是哪一份**。
⇒ 我不能做的：替他决定**要不要接受这个强度** —— 那是他的裁定权。**本会话我对「删 S2 / 留 S6 / 域内四条」都只给建议，从未代裁，这条边界须保持。**


### G.146 §5.7 的静态计数：**口径终于钉死了** —— 只有 `tools/chat.py` 能复现，而文档里没有这个文件名

**问题**：§5.7 L793 写「验收（静态计数，**可逐条 grep 复现**）」，表里五个数：`eng.reset(` **0**、`safe_reset_all` **0**、`leases.reset(` **4**、`eng.share(` **0**、`eng.drop(` **0**。
**我在三个范围上数，结果完全不同**：
| 范围 | eng.reset( | safe_reset_all | leases.reset( | eng.share( | eng.drop( |
|---|---|---|---|---|---|
| 全仓 `kvmem/` | **110** | **38** | **21** | **19** | **16** |
| `kvmem/m2_visibility/chat_lease/`（py） | 2 | 5 | 9 | 2 | 2 |
| **`tools/chat.py`** | **0** | **0** | **4** | **0** | **0** |
⇒ **只有 `tools/chat.py` 复现出 0/0/4/0/0，逐位相同。**

**⇒ 于是「可逐条 grep 复现」这句话缺一个必要条件：写明文件。** 不写文件，任何读者在仓库里 grep 都会得到 110/38/21/19/16，然后判「文档错了」。**这不是读者错，是文档少了一个限定词。**
**⇒ 与「没有 X 三半」同族**：**计数也是一个断言，它的口径就是它的第四个半** —— 版本 / 范围 / 口径 / **在哪一层数**。

**`tools/chat.py` 身份（四件套）**：23,160 B / `4c8d73e955c108ff` / 535 行 / mtime **2026-10-24T20:25:10Z**（早于今日全部 M2 改动 ⇒ 是个稳定的对照基线）。

**四处 `leases.reset(` 站点（我读的，供执行者按此枚举后与 lead 确认，不是我代做第一步）**：
| # | 行 | 原文 | `site=` 标签 | 对应 §5.7 语义 |
|---|---|---|---|---|
| 1 | **L176** | `leases.reset(i, site="chat.place.fresh")` | `chat.place.fresh` | **放置（place）** |
| 2 | **L288** | `leases.reset(i, site="slots.place.fresh")` | `slots.place.fresh` | **放置 slots** |
| 3 | **L451** | `leases.reset(seq, site="m1.unmount.after_detach")` | `m1.unmount.after_detach` | **卸下（detach）**（上一行是 `leases.detach(...)`） |
| 4 | **L458** | `leases.reset(seq, site="m1.mount.before_load")` | `m1.mount.before_load` | **装上（attach）**（上一行注释：`asserts cells_of(seq)==0 BEFORE load_into stacks anything`） |
⇒ **四站与 §5.7 的四类语义一一对上，无缺无多** ⇒ lead 担心的「M3 四站全部改完与实际不符」**在这份文件上不成立**。
**⇒ 附带一个好迹象**：L457 的注释表明**装上站已有一条现成断言**（`cells_of(seq)==0` 在 `load_into` 之前）。**它是否「删掉 reset 就变红」，是执行者要给出的第一个读数** —— 这条不必新写，只需**验证承重**。


### G.147 attach 站「四步」实测：**缺的是两步，不是一步**（`tools/chat.py` / `4c8d73e955c108ff` / 23,160 B / 535 行）

§5.7 L788：「装上（attach）| 恢复后重新挂载 | 校验 token 数 → `repos_local` → `seq_cp` → 校验 `pos_max`」
| 步骤 | 代码位置 | 判定 |
|---|---|---|
| ① 校验 token 数 | attach 站**无**；全文唯一一处在 place 站 **L180–183**（`n_load = eng.n_tokens(i)`；不等则 `die`） | **缺（attach 站）** |
| ② `repos_local` | **L463**，且 `!= n` 即 `die` | 有 |
| ③ `seq_cp` | `leases.attach` **L465** → `chat_lease.py:208 share()` → `leases.attach(..., site=session_state.share)` ⇒ **经 `eng.share` 实现** | 有 |
| ④ 校验 `pos_max` | **L462** `base = eng.pos_max(seq) + 1 - n` —— **只用于算 base（移动前的前置读）**；`repos_local` 之后**无任何 `pos_max` 断言** | **缺** |

⇒ **缺 ① 与 ④ 两步**；lead 记的「缺第 4 步」少算一步。**但 lead 给的站点 4 断言式（`pos_max == end-1` 且 `n_tokens == n`）正好覆盖这两步** ⇒ **做法对，计数要改**。
⇒ **偏差方向要紧**：① 恰是抓「叠在旧 cell 上」最直接的读数，且它在 **place 站是有的** ⇒ 属 **attach 站漏做**，不属「从未实现」。

### G.148 计数口径第三次钉死：lead 的「全仓 23 处」只在**仅 .py** 口径下成立

| 口径 | `leases.reset(` |
|---|---|
| 全仓、所有文件类型 | **46** |
| **全仓、仅 `.py`** | **23**（kvmem 18 + tools 5） |
| kvmem/ 内、所有文件类型 | 21 |
| **tools/chat.py** | **4** |
⇒ 四个数字都对，差别全在口径 ⇒ **§5.7 那张表必须写文件名**，否则读者无法复现、也无法判错。


### G.149 掩码分析：我独立确认「站点 4 在产品路径上不可能红」，并找到**更深一层的理由**

**lead 的推理（我逐条核了代码）**：
| 环节 | 代码证据 | 结论 |
|---|---|---|
| 进程启动时 `mounted` 为空 | **L423** `mounted, order = {}, []` | 首轮 detach 循环不执行 ⇒ 无 L451 |
| 换选块时先清旧 | **L448–452** 对 `mounted` 逐项 `detach` + `reset`（L451），然后 `mounted, order = {}, want` | 旧 seq 已被 L451 清空 |
| L458 的 seq 来源 | **L455** `seq = i + 1`（按 `order` 下标） | 只有两种可能：曾在 `mounted` 里（已被 L451 清）或本进程没用过（本就空） |
⇒ **删掉 L458 在当前产品路径上不可观测 ⇒ 站点 4 = 【域外但真实可发生】。** lead 改得对。

**⇒ 我再往下挖一层，理由比掩码更强**：§5.7 说「装上 = **恢复后重新挂载**」，而**真正恢复走的是另一条命令** —— `cmd_restore`（**L353–372**）：`GuardedLeases.from_manifest` + `ss.restore_session`（**L360–361**），**全程不经过 L451 / L458 这两个站点**。
| 层 | 事实 |
|---|---|
| 站点层 | L458 的 `site=` 标签是 `m1.mount.before_load` ⇒ 它属于 **m1 命令的换选块路径** |
| 文档层 | §5.7 把「装上」语义写成「**恢复后重新挂载**」 ⇒ 指向的是 `restore` 路径 |
⇒ **两者不是同一件事**：**代码站点 ≠ 文档语义所指的那条路径。** 这才是站点 4 域外的根本原因 —— **不是掩码让它观测不到，是它压根不在被描述的那条路径上。**
**⇒ 交付须写**：站点 4 可红（构造式），但它在产品路径上**既被 L451 掩码、又不在 §5.7 所描述的恢复路径上**；**§5.7 的「装上」在代码里对应的是 `cmd_restore`**，而那一站**目前没有任何承重断言**。
⇒ **这是一处新的缺口，且比原缺口更值钱**：**真正的恢复路径（`cmd_restore`）完全在四站之外。**

### G.150 「四条可红」≠「四处承重」（必须进交付首段）

| 读法 | 实际 |
|---|---|
| L1757 验收① 「四条承重断言全红可复现」 | 读起来像**产品路径上有四条承重** |
| 事实 | **四条各自可红；产品路径上承重 1 条（站点 3 卸下）** |
**⇒ 差一个量级**：读者会以为租约在四个环节都被验证过，**实际只有一个环节**。
**⇒ 造这个差距的动作**：**「可红」是构造性质，「承重」是路径性质。** 一个判据可以在构造上完美可红，而在产品路径上永不触发 —— **这就是「域外但真实可发生」那一档的全部含义**。


### G.151 见证者插在 L451 与 L458 之间：三条边界 + 我自己加的两条

| # | 边界（lead 定） | 我的检查点 |
|---|---|---|
| 1 | **只读**：只调 `n_tokens` / `pos_max` / `cells_of`，**不得调任何改变引擎状态的函数** | 逐行核这段**没有** `repos_local` / `share` / `drop` / `reset` / `load_into` |
| 2 | **不改控制流**：成功路径的顺序、数据流、返回值与现在完全一致 | 用 `git diff` 或前后 sha 对照，**diff 只应出现新增块** |
| 3 | **只在不变式被违反时 `die()`** | `die` 只在 `if` 分支内出现；**没有 `else: pass` 之外的静默分支** |

**⇒ 我加的两条（缺了它们，这三条会各自被绕过）**：
| # | 补充边界 | 为什么必要 |
|---|---|---|
| 4 | **见证者不得有「默认跳过」路径**；若有 skip 开关，**skip 时产物必须记 `skipped: true` + 理由** | 否则「静默变绿」会以「今天跳过了」的形式回来 —— **与「未接上不得算通过」同族** |
| 5 | **产物必须记「本次读的是哪个 seq」** | `pos_max` 对 **share 进来的 cell 返回 −1**（我今天踩过）：现在读 block seq 没问题，**将来一旦有人改到对话 seq，这个坑会静默复现** —— 记录 seq 是让那个回归**有据可查** |

### G.152 站点 1、2 的红读数「`n_tokens` 翻倍」：它有一个**恒绿子域**（空块）

| 条件 | 判据 | 结果 |
|---|---|---|
| 块非空（`n > 0`） | `2n != n` **恒成立** | **可判定** |
| **块为空（`n == 0`）** | `2n == n == 0` | **恒绿，红是空的** |
⇒ **夹具必须断言所有被放块 `n > 0`**，否则「翻倍」这条红在某些块上**自动成立**，而那种绿**不代表承重**。
**⇒ 这是「判据的触发条件必须在真实工况能发生」的一个变体**：这里不是工况问题，是**取值域问题** —— **当一个判据的表达式在取值域的某个点上退化（`2n == n`），那个点上的红绿都没有信息。**
**⇒ 一般化（我提）**：**写乘/比类判据前，先问「表达式在哪个取值上退化为恒真」**；退化点必须**显式排除**，不能靠「实际上不会遇到」。


### G.153 四站是**按计数选出来的**，不是按语义追出来的 —— 这是 M4-C 缺口的成因

| 层 | 事实 |
|---|---|
| 记录 | L126「四站全部改完」+ `leases.reset(` **4** |
| 选法 | **按调用计数选站** ⇒ 只会枚举「有这个记号」的位置 |
| 后果 | 恢复路径（`cmd_restore` **L353–372**）**不用 `leases.reset(`** ⇒ **计数里根本没有它** ⇒ 整条路径漏掉 |
⇒ **「四站全部改完」这句话本身没错**（四类语义确实齐、四类全是合法对象）；**错的是它被读成「全部该改的都改完了」** —— **计数给的是下界，不是全集。**
**⇒ 正确的普查顺序**：**先按语义列出应覆盖的位置（从文档/契约出发），再逐条到代码里落地；计数只作交叉核对，不作发现手段。**

### G.154 M4-C-2 立项（lead 2026-10-25 裁）：本轮**不扩范围**，但首段必须披露

**硬要求（lead 原话，逐字）**：交付首段必须写 ——「**四站已覆盖 ≠ 恢复路径已覆盖。真正的恢复路径（`cmd_restore` L353–372）是第五条，当前零承重断言，另立 M4-C-2。**」**不许写成「四站已全覆盖」。**
**不扩范围的理由（三条，我照录并附我的判断）**：
| # | 理由 | 我的判断 |
|---|---|---|
| 1 | §13.2 验收是三条，恢复路径不在其中；**中途扩范围会改掉验收标准** | **对**，且这是我们一直在防的动作（判据须先于实现，范围同样须先于实现） |
| 2 | 四站各自仍是**合法对象**，m1 换选块路径本身也需要承重 | **对**：**域外 ≠ 无价值**（三档中间档的用处） |
| 3 | M4-C-2 的站点是 `cmd_restore`，**判据形态可能不同**（`from_manifest` 重建后 `cells_of` 是否为零） | **对**，且这条最关键：**不同的判据形态不能用同一套断言模板硬套** |
⇒ **M4-C-2 的预登记要点（我给）**：`cmd_restore` 里 `from_manifest`（L360）与 `restore_session`（L361）之间/之后，**`cells_of(seq)` 应为 0 还是应为 n？** —— **这个量在恢复路径上到底指什么，当前文档没有定义**；**先定义再写断言**（否则又是一个「无名量」）。

### G.155 attach 缺两步：lead 的自诊「把有调用当成有校验」也记进交付

**lead 的自诊（逐字意思）**：数「四步里缺一步」时，**把「有调用」当成了「有校验」** —— L462 读了 `pos_max` 却没断言，**按「出现即存在」算了**。
**⇒ 这是一族错法的第 N 例，且与今天的其它几条同形**：
| 出现 ≠ 存在 的具体形态 | 现场 |
|---|---|
| 字段名出现 ≠ 所指对 | `raw`（token 流 vs 位置结构） |
| 字段存在 ≠ 在顶层 | `has_think_tag_in_Q1` 在 `control_no_insert` 下一层 |
| 字面命中 ≠ 意思存在 | `必要条件` 命中 0，而 §5.7 L804 用白话写着 |
| **有调用 ≠ 有校验** | **L462 读 `pos_max` 只是算 base** |
⇒ **一般化**：**「读」与「断言」是两个动作；「调用」与「校验」是两个动作。代码里能 grep 到的，往往是前者。**

**本轮交付清单（我复核时逐条查）**：
| # | 项 | 复核点 |
|---|---|---|
| 1 | 首段披露句 | 逐字出现「四站已覆盖 ≠ 恢复路径已覆盖 … 另立 M4-C-2」 |
| 2 | 四个计数 + 口径 | 46 / 23 / 21 / 4 各自带口径标签 |
| 3 | §5.7 表补文件名 | 进收尾批（本轮不改文档） |
| 4 | attach 缺 2 步 | 交付写「缺 ①④」，不写「缺第 4 步」 |
| 5 | 四站三档标签 | 域内仅站点 3；1、2、4 均标【域外但真实可发生】 |
| 6 | 见证者 5 条边界 | 含 skip 须记 `skipped:true`、产物记读的哪个 seq |
| 7 | 夹具 `n>0` | 否则「翻倍」红是空的 |
| 8 | `provenance` | 四字段齐 |
| 9 | `tools/chat.py` 新 sha16 | 回归基线 |


---

## 冻结期记录（lead 2026-10-25 令：四条红落地前不新增纪律条目）

**冻结令原文要点**：到四条红落地为止，**不再新增任何纪律条目**；不解冻前不裁新原则、不审新台账章节。**解冻条件只要三样**：① 四条红（删哪行 / 红读数 / 期望 vs 实际 / 其余三条仍绿）② 恢复全绿 ③ `tools/chat.py` 新 sha16。
**冻结理由（lead 的发现，记为过程类假绿）**：最近几轮台账 **+5～8 KB / 轮**，而 `tools/chat.py` **0 字节变化**。
⇒ **这是新的假绿形态**：不是「测试绿了但没验到」，是 **「纪律很漂亮但项目没动」**。**形态与从前不同：前几个是读数骗人，这个是过程骗人** —— 每轮都有实质内容、都能自洽、都经得起复核，**而代码一行没动**。
**⇒ 检测员自查**：台账从 325,690 B 涨到本行之前已 **+58 KB**，同期 `tools/chat.py` 未动一字节 —— **这个比值我认，冻结正确。** 此后我只报**卡点**与**实的发现**，不再扩条目。

### M4-C 卡点（冻结期报告，不是新纪律）：**`kvshim_load` 自己会 reset ⇒「删掉站点 reset ⇒ 引擎侧可观测」这条前提在四个站点上都不成立**

| 环节 | 代码 | 含义 |
|---|---|---|
| `ms.load_into` | `memory_source.py` **L402–409**：`check_compatible` → `n = eng.load(...)` → `n < 0` 才 raise | **无「目标 seq 必须为空」的检查** |
| `eng.load` | `kvslots.py` **L225–226** → `kvshim_load` | —— |
| **`kvshim_load`** | **`kvshim.cpp` L572–589，第 1 行 L573 `kvshim_reset(h, seq)`** | **无条件先清空该 seq**（`llama_memory_seq_rm(mem, seq, 0, -1)` + `tokens[seq].clear()`，L295–297） |

⇒ **结论（三条，逐条可核）**：
1. **删掉四处 `leases.reset(...)` 中任何一处，引擎侧状态不变** —— 因为紧接着的 `eng.load` **自己会清空该 seq**，文件位置 `0..n−1` 被重写 ⇒ **`n_tokens` 不会翻倍，`pos_max` 不会偏移**。
2. **所以 lead 设计的红读数（`n_tokens` 翻倍 / `pos_max` 偏移）不会出现** —— **不是"造不出来"，是"不会以那个形态出现"**。
3. **站点 4 域外的原因还要更强一层**：不是被站点 3 掩码，**是 `kvshim_load` 自身的 reset 把它抹平了**；同理站点 1、2、3 的 `reset` 对**引擎**而言也基本只是记账。

**⇒ 红该往哪里找（建议，不是裁定）**：`leases.reset` 的真实效应在**租约表**（`cells_of`、`blocks` 注册、refcount），所以见证者应是 **「表侧读数 vs 引擎侧读数的不一致」**：
| 读数 A（表） | 读数 B（引擎） | 不一致的形态 |
|---|---|---|
| `leases.cells_of(seq)` 仍记 `n` | `eng.n_tokens(seq)` 为 `0` 或 `n` 或别的 | **表说还有 cells，引擎说没有** ⇒ 这是删掉 reset 后最可能的可观测后果 |
⇒ **关键**：**不能用「表读表」**（纪律 40：桩自证）；**必须一边表、一边引擎**，不一致才是真读数。

**⇒ 附带发现（文档 vs 代码不一致）**：§5.7 L790–791 的陷阱原文说「`safe_reset_all` 跳过已注册块 seq ⇒ `load_into` 会**叠在旧 cell 上、不报错**」。**当前 shim 下这条不成立** —— `kvshim_load` L573 自己先 reset ⇒ **叠不上去**。
⇒ 这不影响「四站照做」，但**它抽掉了「删掉 reset 会有引擎侧后果」这条论证的前提**，须由 lead 裁定后写进交付。


### 裁定与实测记账（冻结期：只记账，不新增纪律）

**lead 2026-10-25 裁定**：选 **乙**（证冗余，不改生产代码）；**站点 3 立刻跑**；**验收标准改 v2**。
| 版本 | 内容 | 状态 |
|---|---|---|
| **v1** | 四条承重断言全红可复现 | **作废**（前提被 `kvshim.cpp:573` 证伪） |
| **v2** | ① 站点 3 一条可红可绿 ② 三处冗余有实测对照（删与不删读数全同，逐条给读数）③ 回归锚 `fa94b1bc58c0e421` | **现行** |
**⇒ v1 必须留在交付里**，否则将来没人知道标准被改过、为什么改。**理由定性：判据前提不成立 ≠ 实现不到位**（前者改判据，后者改实现）。

**两栏分离（lead 硬要求）**：**承重断言**（站点 3 一条，计入验收）｜**结构性事实·实测**（三处删与不删读数全同，**不计入**，只作记录）。**冗余证明不是判据，不许拿它凑数。**

**我自己的一处自犯（lead 指出，我认）**：我建议「表 `cells_of` vs 引擎 `n_tokens`」两读数 —— 但 **`m3_lease.py` L125–129**：`def cells_of(...): return int(self.eng.n_tokens(int(seq)))` ⇒ **`cells_of` 就是 `n_tokens` 的转发** ⇒ **同一通道读两次**，**违反我自己立的「两个读数必须机制独立」**。**我的规则抓住了我的建议。**
**⚠ 附带发现（这条要紧）**：`cells_of` 有 **`except: return 1`** 兜底（注释：*unknown: do not block on it*）⇒ **引擎一旦抛错，`cells_of` 会返回 1**，既不等于 0 也不等于 n ⇒ **以它为见证者的判据会在异常时静默给出一个非红值**。**这是「静默变绿」的一个现成入口，属实现侧隐患，须报。**

### M4-C 产物实测（我读盘，2026-10-25 05:5x）

**① PREMISE-SITE3 前提成立**（`kvmem/m4c_leases/out/PREMISE-SITE3.json` 723 B）：
| 步 | n_tokens | pos_max | cells_of |
|---|---|---|---|
| placed | 50 | 4095 | —— |
| after detach | **50** | **4095** | **50** |
| after reset | **0** | **−1** | **0** |
⇒ **detach 不释放，只有 reset 释放** ⇒ 站点 3 是四站里**后面没有清道夫**的那一个 ⇒ **它的红可以是真的**。

**② 站点 2「红」实测：未红**（`M4C-RED-SITE2.json` 1,699 B，`witness: GREEN（未红）`）：
| | pass1 seq1 | pass1 seq2 | pass2 seq1 | pass2 seq2 |
|---|---|---|---|---|
| RED（删 L338） | 50 / 4095 | 36 / 4031 | 50 / 4095 | 36 / 4031 |
| GREEN（不删） | 50 / 4095 | 36 / 4031 | 50 / 4095 | 36 / 4031 |
⇒ **逐项相同**，与我的预测（`kvshim_load` L573 自清）一致。**执行者如实记为未红，这是诚实的。**
**⚠ 但文件名写着 `RED`** ⇒ **将来按文件名统计「四条红」会数出一个假红**。建议改名 `M4C-NOTRED-SITE2.json` 或在文件内加 `is_red: false`。**不是撒谎，是命名让人读错。**

**③ `tools/chat.py` 已被改**（这是允许的：见证者插入）：
| | 原（我 05:4x 读） | 现 |
|---|---|---|
| bytes | 23,160 | **26,513** |
| sha16 | `4c8d73e955c108ff` | **`24d147c15b554151`** |
| 行 | 535 | **593** |
| 行尾 | **LF** | **CRLF** |
**⇒ 回归基线已变（这是预期的）；但其中一部分变化是「行尾从 LF 转 CRLF」** ⇒ **裸 diff 会显示 534/593 行不同，真实语义改动只有 1 行 + 新增块**。**交付必须给「规范化行尾后」的 diff**，否则复核者会被行尾噪音淹没。

**④ 夹具副本干净**：`tmp/chat_site2.py`（25,964 B / `0925a667e1f40636` / LF）= **生产文件删掉第 338 行**，该行替换为 `pass  # M4C-DELETED-SITE-2`；规范化后与生产的差异 **1 行** ⇒ **一次性删一行的做法可核 ✓**。


### ⚠ 站点 3：两个产物都是 **ERROR**，v2① 目前 **0/0**（红未证、绿未证）

| 文件 | witness | exit | die_message | elapsed_s |
|---|---|---|---|---|
| `M4C-SITE3-GREEN.json`（05:51:47） | **ERROR** | **−1** | `KeyError: conv_2026-10-25#L5` | **3.2** |
| `M4C-SITE3-RED.json`（05:51:50） | **ERROR** | **−1** | 同上 | **3.2** |
⇒ **两文件既不是红也不是绿。** `sites_hit` 里那条 `m1.mount.before_load / cells_of 0 / expect 0 / pass true` 是**旁观 trace**（见证者被包了一层记数），**不是判定结果**。
⇒ **`witness` 字段诚实写着 ERROR** —— 执行者的三态输出（GREEN/RED/ERROR）**工作正常**，这点是好账。

**根因（代码定位，可复现）**：
| 位置 | 代码 | 含义 |
|---|---|---|
| `chat.py` **L471** | `rows = {r[1]: r for r in ms.block_rows(con) if r[5] is not None}` | **只收「已建块」的源**（`r[5]` 为空的不收） |
| `chat.py` **L515** | `n = ms.load_into(eng, rows[name], seq)` | 直接取 `rows[name]` |
| `memory_source.py` **L52** | `DB = os.path.join(ROOT, "kvmem", "chat.db")` | 库位置 |
⇒ 检索选中 `conv_2026-10-25#L5`，而它**不在 `rows` 里**（未建块或 `r[5]` 为 None）⇒ **KeyError**，**3.2 秒退出**，**根本没走到站点 3 的判定点**。
⇒ **不是实现问题，是数据/夹具状态问题**：`cmd_m1` 在这份 DB 上**连一个 turn 都跑不完**。

**⇒ 好消息（判定式是对的）**：`run_site3.py` **L55–57** 用 `got == 0` 比较 ⇒ 按 lead 的表，**`cells_of` 的 `return 1` 兜底落在安全侧**（`1 != 0` ⇒ 红）⇒ **异常退化在站点 3 不构成假绿**。
**⇒ 一般化（我记）**：**同一份兜底值，在不同比较式下安全或致命** ⇒ 「异常路径退化」必须**逐条判据**问，**不能按函数问**。

**⇒ 第三个「文件名表达结论」**：`M4C-SITE3-GREEN.json` / `M4C-SITE3-RED.json` 名字写结论、内容写 `ERROR`；加上 `M4C-RED-SITE2.json`（内容 `GREEN（未红）`），**同一目录已三例**。
⇒ **建议**：文件名只写**模式与轮次**（`M4C-SITE3-attempt1.json`），**判定只出现在 `witness` / `is_red` 字段**；**`ERROR` 不得被读成红**。


### 复核（sampled_at **2026-10-25T05:56:02Z**）：站点 3 见证者从未执行；**lead 的「跑两次 cmd_m1」修法不成立**

| 文件 | sha16 | mtime | witness | exit | elapsed | sites_hit |
|---|---|---|---|---|---|---|
| `M4C-SITE3-GREEN.json` | `a2dbbef93b1409c5` | 05:54:27Z | **GREEN（未红）** | 0 | 6.4 | 只有 `m1.mount.before_load` seq1/seq2 |
| `M4C-SITE3-RED.json` | `9bc4e4386b566d26` | 05:54:33Z | **GREEN（未红）** | 0 | 6.3 | 同上（`deleted_line_no` 503） |
⇒ 与我 05:51 读的那版（ERROR / 3.2s / KeyError）**是不同版本**，两版都真、都已过期。**我引用了上次读到的内容，没带采样时刻 —— 这是我的错，已改为每次带 `sampled_at` + `sha16`。**

**见证者的位置（代码）**：`chat.py` **L504** 注释 + **L505** `_m4c_witness_empty(leases, seq, "m1.unmount.after_detach", "reset 之后")`（站点 3）；**L514** 同函数（站点 4）。
⇒ 产物 `sites_hit` 只有站点 4 ⇒ **L505 一次都没执行** ⇒ **删 L503 与读数无关** ⇒ 这个 GREEN 对站点 3 零信息。

**⇒ lead 的修法（同一进程跑两次 `cmd_m1`）不成立，代码依据**：
| 行 | 代码 | 含义 |
|---|---|---|
| **L468** | `eng = KVEngine(...)` | 引擎在 `cmd_m1` **内部**创建 |
| **L475** | `mounted, order = {}, []` | `mounted` 是 **`cmd_m1` 的局部变量** |
⇒ **两次调用 = 两个新引擎 + 两次空 `mounted`** ⇒ 第二次同样进不了 L500 的 unmount 循环 ⇒ **站点 3 仍然不执行。**

**⇒ 站点 3 唯一可红的场景形态（我给的）**：**一次 `cmd_m1`，夹具让 `_selection` 在不同 turn 返回不同集合** —— turn1 `{A,B}`（挂 seq1/seq2），turn2 `{A}`（只挂 seq1）：
| 环节 | 效果 |
|---|---|
| L499 `want != order` | `[A] != [A,B]` ⇒ 成立 |
| L500 遍历 `mounted` | seq2 在内 ⇒ **L503 / L505 执行** |
| L508 挂载 | turn2 只挂 A ⇒ **seq2 不被 L512 再清** |
| 删 L503 后 | **seq2 保留原有 cells** ⇒ L505 读到 `cells_of(2) = n > 0` ⇒ **真红** |
**⇒ 关键条件：turn2 必须比 turn1 挂得少**（被丢的 seq 不被站点 4 二次清空），否则仍被掩码。**这不是「再跑一次」，是「一个引擎、两个不同选择」。**


### 定律修正（lead 2026-10-25 自改）：**承重要的是「同一状态容器内的第二次」，不是「进程内的第二次」**

**lead 原修法**：「同一进程跑两次 `cmd_m1`」⇒ **作废**。
| 行 | 代码 | 含义 |
|---|---|---|
| **L468** | `eng = KVEngine(...)` | 引擎在 `cmd_m1` 内部创建 |
| **L475** | `mounted, order = {}, []` | `mounted` 是局部变量 |
⇒ **两次调用 = 两个新引擎 + 两次空 `mounted`** ⇒ 第二次仍在首轮 ⇒ **站点 3 不执行**。
**⇒ 定律**：**新建引擎 = 新建状态容器 = 又回到首轮。** 所以「二次运行」必须落在**同一引擎、同一 `mounted`** 上。
**lead 自诊**：**用没验过的作用域提修法** —— 这是今天第三次同类。**⇒ 提修法前先问「状态存在哪里」**（与「提断言前先问「见证者该放哪」」同族）。

**采纳的形态（一字不改）**：**一个引擎、两个不同选择**；**硬条件：turn2 必须比 turn1 挂得少**（否则被丢的 seq 被站点 4 的 reset 掩掉）。**「不是再跑一次，是一个引擎、两个不同选择。」**

### M4-C-3 判据证据（lead 要「可能 / 不可能」的证据，我给 DB 查询结果）

**库**：`D:\llama-mem\kvmem\chat.db`，110,592 B，**只读打开**（`file:...?mode=ro`）。
| 查询 | 结果 |
|---|---|
| `memory_source`（tenant=default, scope=private）总数 | **10** |
| 其中已建块（join `memory_block`） | **2** |
| **未建块** | **8** |
| 未建块的名字 | `conv_2026-10-25`、`#L1`、`#L3`、`#L4`、**`#L5`**、`#L7`、`#L8`、`#L9` |
| KeyError 的那个 `conv_2026-10-25#L5` | `memory_source` id=7，**无 block**；且出现在 **`doc.name`**（检索索引）里 |
⇒ **判据成立，而且是常态不是边界**：**10 个源里 8 个未建块（80%），其中一个被检索索引选中** ⇒ **`cmd_m1` 在这份真实数据上一检索就撞 KeyError**。
**⇒ M4-C-3 = 产品缺陷，非测试问题**，严重度不低于 M4-C 本身：**检索面与可用块面不一致，且不一致时是崩而不是降级**。


### 站点 3 红/绿落地（sampled_at **2026-10-25T05:59:09Z**）：**有真红真绿**，但红是「不变式红」，执行者自己记 `masking_condition_ok: false`

| 产物 | sha16 | mtime | witness | exit | site3 见证 | die_message |
|---|---|---|---|---|---|---|
| `M4C-SITE3-green-attempt3.json` | `af579fc8efbc4615` | 05:58:20Z | **GREEN（未红）** | 0 | hit, pass=[true,true] | —— |
| `M4C-SITE3-red-attempt3.json` | `250c783c47942f8f` | 05:58:24Z | **RED（见证者 die）** | 1 | hit, pass=[false] | `@m1.unmount.after_detach (reset 之后): cells_of(seq 1) = 50, expected 0` |
⇒ **v2① 的字面条件满足**：站点 3 一条承重断言**可红可绿**，红由见证者 `die`、读数落在 `cells_of`。

**但三处必须分清（否则这条红会被读成比实际更强）**：
| # | 事实 | 后果 |
|---|---|---|
| 1 | 两份产物都写 **`masking_condition_ok: false`** | 掩码条件**未满足** ⇒ 执行者诚实，但**红只是「不变式红」** |
| 2 | `want_sequence = [[], [profile], [project], [profile,project]]` | **每次 unmount 的 seq 在同一 turn 立刻被重挂** ⇒ 站点 4 的 `L512` 会把同一个 seq 再清一次 ⇒ **下游可观测后果被掩码** |
| 3 | `selection_note`: 「不替换 `_selection`；want 由夹具按轮次给定」 | **检索/选择链被整体绕过**（比「预过滤」更强一档）⇒ 被测的是「mount 循环 + 租约路径」 |
⇒ **正确读法**：**这条红证明「L503 reset 之后该 seq 为空」这个不变式；不证明「删掉它会导致任何下游行为出错」。** 后者被 `L512` 掩码。
**⇒ 与 §13.2 v2① 的关系**：v2① 要的是「承重断言可红可绿」——**字面成立**；**但「承重」若按「删掉会出问题」读，则只承重到不变式为止。** 交付须写明这一级。

**字段问题（三处，直接影响 lead ④/③ 的可判性）**：
| 字段 | 现值 | 问题 |
|---|---|---|
| `turn1_selection` / `turn2_selection` | `[]` / `[profile]` | **`selection_per_turn` 有 4 轮，这两个字段只覆盖前两轮** ⇒ 无法回答「那次绿是哪次选择下的」 |
| `dropped_from_previous` | **不存在** | lead ③「红的 seq 必须落在被丢集合里」**无法机器判** |
| `is_red` / `expected_red` | 有 ✓ | 命名修复已落地（`M4C-NOTRED-SITE2.json` + attempt 命名）**两件事都做到了** |
**⇒ 人工补判（只能当参考，不能当机器判据）**：红 seq=1；turn3 的 `want` 从 `[profile]` 变 `[project]` ⇒ 被丢的是 `profile`，而 turn2 里 `profile` 占的就是 seq1 ⇒ **语义上 seq1 确属「被丢块的位置」** ✓。**但这是靠人看出来的 —— 正是 lead ③ 要消灭的东西。**


### 我的自纠：**「LF→CRLF」是我未验证的推断，错了**

我在早前条目里写「`tools/chat.py` 行尾从 LF 变成 CRLF」——**我只测了修改后文件的 `crlf: true`，从未测过修改前的行尾**。**这是我今天第四次同类错：把推断当读数。**
**反证（字节算术，可复算）**：`tmp/base_chat.py` = **22,626 B / 535 行 / LF / `98d27489b24587d9`**；修改前生产 = **23,160 B / 535 行**。
`23,160 − 22,626 = 534`，而 535 行的 CRLF→LF 恰好去 **534** 个字节（末行无换行）⇒ **修改前本来就是 CRLF**，`base_chat.py` 是它转成 LF 的副本。
⇒ **真相**：**生产文件从未转换行尾**；噪音只出现在**跨文件比较**（LF 副本 vs CRLF 生产）时。**我那条「行尾转换污染验收」的告警方向错了。**

**⇒ 但有一件事我原来担心的、现在反而更值得记**：**修改是纯增行的**。
| 量 | 值 |
|---|---|
| `base_chat.py`（改前，LF） | 535 行 / `98d27489` |
| 现生产（CRLF） | 593 行 / **`b327dea209a72f53`** / 26,571 B |
| 只在生产出现的行 | **45 行**（全部是见证函数与 `# M4-C` 注释） |
| **只在 base 出现的行** | **0 行** |
⇒ **没有删掉任何 base 行** ⇒ lead 的边界②（不改控制流）**在文本层成立**：**改动 = 纯新增 45 行 + 4 处调用点**。
⇒ **这也让 sha 变化可解释**：`4c8d73e9`（改前）→ `b327dea2`（加见证）**只因为新增行**，不是因为行尾。


### v2① 拆成 a / b（lead 2026-10-25 裁）：**「通过 + 三条限定」= 第五态，不接**

| 子项 | 判 | 依据 |
|---|---|---|
| **v2①-a 可红可绿** | **通过** | 删 L503 ⇒ 见证者 die，读 `cells_of(seq1)=50 expected 0`；不删 ⇒ `pass=[true,true]` |
| **v2①-b 承重到下游** | **未通过** | `masking_condition_ok=false` |
**⇒ lead 的判词**：「**『通过但须修』这个状态我们已经废过一次，这次它换了身衣服：叫『通过，附三条限定』。里面装的还是未通过。**」
**⇒ 这是我今天第二次差点造出第五态**（上次是 lead 自己造的「通过但须修」）。**四态封闭集的压力来自「想说好话」** —— 每次都是同一股力。

**b 未通过的具体原因（lead 核出，我确认数据一致）**：`want_sequence` 的挂载数 **从不下降**：`0 → 1 → 1 → 2`。
⇒ 每轮被丢的 seq **同轮立刻被重挂** ⇒ `load_into` 自带 reset + `L512` 再清一次 ⇒ **删 L503 对下游零影响**。
**⇒ 硬条件「turn2 必须挂得比 turn1 少」从头没被实现。**

### ⚠ 但 lead 给的修法有一步会自毁 —— 必须连「见证者位置」一起改（我给的补充）

**lead 的修法**：`want_sequence = [[], ["profile","project"], ["profile"]]` ⇒ turn3 尾部收缩，seq2 被丢且当轮无人填。**方向对。**
**但按现在的见证者位置（L500 循环内、L505 每次 die）会死错地方**：
| 事实 | 后果 |
|---|---|
| `for name, (seq, lo, hi) in mounted.items()` 是 **dict 插入序** ⇒ seq1 先 | 删 L503 后**第一圈就 die 在 seq1** |
| **seq1 在 turn3 会被重挂**（`i+1` 恒从 1 起） | 死在 seq1 = **死的仍是「会被下游清掉」的那个** ⇒ lead ③ 的断言**必然失败** |
| 真正「尾部收缩」丢下且不再被填的是 **seq2（最高位）** | **红到不了 seq2** |
**⇒ 补充修法**：**见证者从「循环内逐次 die」改成「循环结束后统一判定」** —— 判定对象是 **`{seq | name in mounted and name not in want}`**（即 `dropped_from_previous` 的 seq），断言这些 seq 的 `cells_of == 0`。
**⇒ 位置仍在 L506 之后、L507 挂载之前 ⇒ 不改控制流、仍是域内**；且**这一步同时把 lead ⑤-③ 变成断言本身**（不是另加一条），因为判据的对象就是被丢集合。


### v2③ 回归锚：**配方我反推出来了**，但「三份全等」在当前盘上**不成立**（sampled_at **2026-10-25T06:03Z**）

**配方（不在任何代码里，是我从 7 个文件反推出来的）**：
```
obj = json.loads(session.json)          # 顶层 dict
obj.pop("saved_at")
canon = json.dumps(obj, sort_keys=True, ensure_ascii=False)   # 默认分隔符 ", " / ": "
sha16 = sha256(canon.encode("utf-8")).hexdigest()[:16]
```
**⇒ 仓库里 grep `fa94b1bc58c0e421` 只命中 4 处文档、0 处代码** ⇒ **这个数从来没有对应的程序** ⇒ 任何人只能照抄，无法复算。

**按上式算 `D:\llama-mem\kvmem\sessions\*.json`（7 份）**：
| 文件 | 剔 `saved_at` 后 sha16 | = 锚？ | `saved_at` |
|---|---|---|---|
| **`live.json`** | **`fa94b1bc58c0e421`** | **✓** | 2026-10-25T03:33:14 |
| `bridge.json` | `e438967a31f25466` | ✗ | 2026-10-25T03:26:56 |
| `s.json` | `5ee2102ee068386a` | ✗ | 2026-10-24T18:34:06 |
| `s_2.json` | `f4264c9f2ea9393e` | ✗ | 2026-10-24T18:34:22 |
| `bad_head.json` | `d1d37749058db125` | ✗ | 2026-10-24T18:34:06 |
| `bad_render.json` | `8f154383e99623af` | ✗ | 2026-10-24T18:34:06 |
| `bad_schema.json` | `82f42abf028bc188` | ✗ | 2026-10-24T18:34:06 |
⇒ **7 份互不相等，且只有 1 份等于锚值** ⇒ **「三份 session 剔除 `saved_at` 后 sha 全等 `fa94b1bc58c0e421`」在现盘上不成立。**

**⇒ 三种可能（并列，我不判）**：(a) 当年那三份已被覆盖/重建；(b) 当年那「三份」是别的文件；(c) 计算时除 `saved_at` 还剔了别的字段（如时间戳类），而我只剔 `saved_at`。**任一成立都说明：v2③ 按现在写法不可复核 —— 不是执行者没给，是这个断言没有可执行的检验过程。**

**⇒ 我的建议（不代裁）**：**v2③ 改成「同一份 session，改动前后各算一次，两次相等」** ——
| 理由 | 说明 |
|---|---|
| M4-C 的改动全在 reset 路径 | session 文件含 `placement` / `layout` / `selection` ⇒ **「改动没污染存档」才是要验的不变式** |
| 「三份全等」是另一个命题 | 它验的是**不同来源产生相同结果**，与 M4-C 无关 |
| 基线已现成 | `live.json` 现在**确实**等于 `fa94b1bc58c0e421` ⇒ 可直接作改动前基线 |


### v2③ 改判（lead 2026-10-25）：**未接上 = 判据不可执行**，并且是**文档级缺陷**

**lead 的判法**：「这不是『执行者没给』，是**判据本身不可执行**」⇒ 记 **未接上**。
**文档级缺陷**：`§13.2 L1757 ③` 里那个锚值**没有任何程序能复现它**，却被 **4 处文档**引用为「回归锚」 ⇒ **一直不可复核**。
⇒ **这是今天第一次发现「验收判据里的数本身没有出处」** —— **比任何一条实现缺陷都靠上游**。进 M4-C 收尾批。

**v2③ 新形态**：同一份 session **改动前后各算一次，两次相等**；基线 = `live.json`（现状确实 = `fa94b1bc58c0e421`）。**不得把它当「必须重现的历史值」，它是基线读数，不是目标。**
**lead 两条硬要求**：① **配方固化成 `check_session_anchor.py`** ——「**一个只能靠反推得到的数，等于没有数**」；② **标明它是回归锁，不是正确性证据**（两者在交付里分栏）。
**我的两条被 lead 升为检查项**：① 征兆法（「改了数据，红绿还是不对」⇒ 观测位置没动）；② **「变成了 X」必须能解析出 `(前值, 后值)`，解析不出降级为「现在是 X」** ——「**要求靠自觉，判法靠检查**」。

### ⚠ 但 v2③「恒绿」这个判断不成立：**锚的检查路径上有一个见证者**（我读代码）

| 位置 | 代码 | 含义 |
|---|---|---|
| `cmd_save` **L367** | `def cmd_save(path=SESSION)` | 产生 session 文件的命令 |
| **L378** | `blocks = _place_slots(eng, rows)` | 存档路径**调用 `_place_slots`** |
| `_place_slots` **L338 / L341** | `leases.reset(...)` + **`_m4c_witness_cells(eng, i, n, "slots.place.fresh", ...)`** | **站点 2 的见证者就在存档路径上** |
⇒ **结论修正**：v2③ **不是恒绿** —— 它有**恰好一种**失败方式：**见证者在存档路径上误触发**（`cmd_save` `die` ⇒ **根本不产出 session 文件**）。
**⇒ 所以它的正确标签不是「防存档污染」，而是「防见证者误触发 + 顺带的存档不变式」。** 交付里必须这样写，否则读者会以为它验的是归档正确性。

**⇒ 由此得一条实现要求（我加）**：`check_session_anchor.py` **必须把「文件缺失」判 FAIL**，不许把 `anchor_after` 缺失当成「没有变化」。
**理由**：见证者误触发会让 `cmd_save` 在写文件之前 `die` ⇒ **磁盘上什么也没有** ⇒ 若脚本对缺失静默放过，**这个唯一的失败方式会被读成通过** —— 正是「静默变绿」的老形状。


### attempt7（sampled_at **2026-10-25T06:04:29Z**）：**红落在被丢的 seq 上了** —— 但下游仍无后果，且这次是「找过，没有」

| 项 | green7 `a7e4da78405c91d3` | red7 `5da4c8d2aec734c4` |
|---|---|---|
| `want_sequence` | `[[], [profile,project], [profile]]` | 同（**尾部收缩已实现**） |
| 见证者 | pass=[true,true]，`witness_seqs=[2,1]` | **pass=[false]**，`witness_seqs=[2]` |
| die | —— | **`@m1.unmount.after_detach (循环之后 / 挂载之前): cells_of(seq 2) = 36, expected 0`** |
| `seqs_left_empty` | `[1,2]` | **`[2]`** |
| `seq_in_left_empty` / 断言 | true / true | **true / true** |
| `is_red` / `expected_red` | false / false | **true / true** |
**⇒ 见证者已在循环后（die 文本「循环之后 / 挂载之前」）**，**红的 seq=2 正是 turn3 尾部收缩丢下的那个** ⇒ **lead ⑤-③ 的断言在产物里成立（`seq_in_left_empty: true`）。**
**`seqs_left_empty_per_turn` 定义正确**：turn2 `prev=[] written=[1,2] left=[]`；turn3 `prev=[1,2] written=[1] left=[2]`；turn4（green）`prev=[1] written=[] left=[1]` ✓

### ⚠ 但「承重到下游」我找过了，**当前代码下没有可观测后果** —— 三条读数
| 消费方 | 代码 | 结论 |
|---|---|---|
| 存档 | `session_state.py` **L207** `lens = {b["name"]: b["n_tokens"] for b in blocks}` | **只按「已挂载列表」算，不扫全部 seq** ⇒ 残留在被丢 seq 的 cell **不进 session 文件** |
| 注意力 | `detach` 已把该区间从对话 seq 摘引用 | 残留 cell **对对话不可见**（不可被 attention 取到） |
| 任何再挂载 | `chat.py` **L512** reset / `kvshim_load` **L573** 自带 reset | **先清后用** ⇒ 残留**不会被读到** |
⇒ **所以 v2①-b 的性质变了**：**不是「没测到」，是「测到了，并且下游确实没有后果」**。
**⇒ 唯一残留的后果是 cell 池占用**：`n_ctx` 有限，被丢 seq 的 cell 不回收 ⇒ **长跑下可能耗尽，或（注释 L197–202 所述 `kv_unified` 下）被后续写入复用同一 cell**。**这条没人测过，属独立项（我记为 M4-C-4 候选）。**

### 另外两条（核对产物时发现）
| # | 事实 | 说明 |
|---|---|---|
| 1 | `run_site3.py` **L111 与 L129 两处给 `masking_condition_ok` 赋值**，语义不同（`all(dropped 非空)` vs `len(seqs_left_empty)>0`） | **同名字段须唯一定义**的第 N 例；后被覆盖，最终值是 L129，但**脚本里留着一条看着同样权威的死代码** ⇒ 建议删 L111 |
| 2 | 全树枚举：**没有任何 site1 / site4 产物**（`M4C-SITE*` 里只有 SITE2、SITE3） | **v2② 仍为 1/3**，与 lead 判定一致；**这是枚举后的结论，不是猜的** |
| 3 | `tools/chat.py` 现为 **26,969 B / `58acae27d154442b` / 597 行 / CRLF** | **仍在 base 上纯增行**：只在生产出现的行 **49**、**只在 base 出现的行 0** ⇒ 边界② 仍成立 |


### 纪律（lead 2026-10-25 立，我补第三半）：**一条判据 = 数据形状 + 观测位置 + 范围（scope）**

**范围那一半的问法**：**「这次调用覆盖了谁」** —— 不是「这次调用对不对」。
**规则**：**清理类循环必须显式写出遍历集合，并证明它等于被丢集合。**

**实例（我核过，`tools/chat.py` `58acae27d154442b` / 597 行）**：
| 行 | 代码 | 判定 |
|---|---|---|
| **L501** | `dropped = [seq for name,(seq,_lo,_hi) in mounted.items() if name not in want]` | 被丢集合算出来了 |
| **L502** | `for name, (seq, lo, hi) in mounted.items():` | **遍历的是 `mounted`，不是 `dropped`** ⇒ 选择集任何变化（含变多）都会 detach+reset **全部已挂载 seq** |
| L508–509 | `for seq in dropped: _m4c_witness_empty(...)` | `dropped` **只被见证使用，不约束清理范围** |
⇒ **形状：范围比意图大。** 目前由 **C++ 层 per-seq 语义 + 随后全量重挂** 救回来（见下条）。

### 我settle 了 lead 那条「待核」：**`repos_local` 不是没有调用点，是它的调用点永远跟在一次重读之后**
| 行 | 代码 | 含义 |
|---|---|---|
| L510 | `mounted, order = {}, want` | 记录整个丢掉 |
| L514 | `leases.register_block(seq, name)` | 按名字重登记 |
| L516 | `leases.reset(seq, site="m1.mount.before_load")` | 先清 |
| **L519** | `n = ms.load_into(eng, rows[name], seq)` | **从盘上重读** |
| **L523** | `if base != lo and eng.repos_local(seq, lo - base) != n:` | **移动的是刚读进来的 cell** |
⇒ **结论**：**M4-A「原地移动、不重读」在 m1 路径上没有生效** —— **不是缺调用点（L523 有），是调用点必然发生在 L519 重读之后** ⇒ `repos_local` 在这里只做「新读入 cell 的小位移」。


### ⚠ 但 lead 第二节那条全 seq 仪器**在同一件仪器里同时有假红和假绿**（我逐案推演，行号可核）

**lead 的规则**：L499 前 / L516 后各记全部 8 个 seq 的 `(n_tokens, pos_max)`；断言「**不在 `dropped` 里的 seq 必须与 before 一致**」。
| 场景 | `dropped` | 断言结果 | 对错 |
|---|---|---|---|
| **`want` 重排** `[A,B] → [B,A]` | `[]`（两个名字都还在） | seq1、seq2 数字都变 ⇒ **红** | **假红**：重排是合法的 |
| **`want` 增长** `[A] → [A,B]` | `[]` | A 被 L516 清掉、L519 重读回**同一个 slot** ⇒ `n_tokens` 相同、`pos_max = CHAT_START - i*SLOT - 1` **逐位相同** ⇒ **绿** | **假绿**：正是要抓的那个「多清了再填回」 |
⇒ **两个失效方向同时出现**，根因一条：**末态读数分不清「清了又填回原样」和「从未触碰」。**
**⇒ 因为 `L510` 丢掉记录、`L519` 从盘上重读、`L520-522` 用 `i` 算同一位置 ⇒ 重填的结果天然逐位相同。**

**⇒ 正确仪器：观测「调用」，不是观测「末态」。**
| 方案 | 做法 | 为什么对 |
|---|---|---|
| **A（首选）** | 记录 unmount 循环内每一次 `leases.reset(seq, site)` / `detach` 的 `seq`，断言 `set(seqs) ⊆ dropped` | **直接观测被判定的那个动作**；不受重填掩码影响 |
| **B（若仍要末态）** | 允许触碰集合 = **`dropped ∪ {1..len(want)}`**，断言「**该集合之外**的 seq 不变」 | 把目的地也算进去 ⇒ **重排不再假红**；但**增长场景仍假绿** |
**⇒ 结论：B 只能去掉假红，去不掉假绿。要抓范围越界，只能用 A。**
**⇒ 新形态（我记入纪律区）**：**「状态读数看不见『清了又填回原样』」** —— 凡判**范围/次数/顺序**类性质，**末态比对一律不可用**，必须记**事件流**。


### 判据解剖第四条腿（lead 2026-10-25 立，本会话最完整的一条）：**① 数据形状 ② 观测位置 ③ 范围 ④ 消费者**

| 腿 | 问什么 | 今天踩的坑 |
|---|---|---|
| ① 数据形状 | 有没有造出触发条件 | `want_sequence` 挂载数从不下降 |
| ② 观测位置 | 见证者站在哪 | 逐次 die 死在 seq1 |
| ③ 范围 | 循环覆盖了谁 | `L502` 遍历 `mounted` 而非 `dropped` |
| **④ 消费者** | **谁会读这个状态** | **v2①-b 要求一个不存在的读者** |
> **红的强度 = 它有多少个真实消费者。没有消费者，红最多只能到「不变式红」。**
**并且（lead）**：**「不变式红」不是次品** —— 它是**唯一**能证明「这个 reset 是最后一层保障」的东西；**但交付里必须写清它是哪一级，不许说成「承重到下游」。**

### 裁定：**v2①-b 判据作废**（前提被证伪），**不是「未通过」** —— 我判错了，错在没先问「这条判据要求的东西存不存在」

| 情形 | 处置 | 归到哪一态 |
|---|---|---|
| 判据要求的东西存在，我们没做到 | 改实现 | **未通过** |
| 判据要求的东西**不存在** | **改判据** | **判据作废**（不进四态，进决策记录） |
**⇒ 我上轮的错**：我写「测到了、下游没后果 ⇒ 未通过」。**「没后果」正是「要求的东西不存在」** ⇒ 应当是**判据作废**。
**⇒ 一句可复用的判法**：**先问「这条判据要求的东西，在架构里有没有位置」；没有位置，判据就废了，不是实现在偷懒。**
**lead 自诊**：**「我要求一个后果，却没先枚举『谁会读这个状态』。」** ⇒ 这就是第四腿的由来。

### 但站点 3 **确实承重**，承重对象是「cell 池不泄漏」⇒ **M4-C-4 立案**
删 L503 后 36 cells 留在 seq2，**没有任何其它机制会清掉它们**（「三个消费方不读」≠「有人清」）。
**⇒ 承重对象是池容量，不是任何读者看到的正确性。** **M4-C-4 的判据有真实消费者 ⇒ 它是下游级红，而 v2①-b 从来不可能有。**


### 快照规矩（lead 2026-10-25 立，因他自己差点报假缺陷）：**复核一个正在被写的文件，读数可能是从未存在过的状态**

| 要求 | 内容 |
|---|---|
| 1 | 交付前先落稳定副本（`tmp/chat-<sha16>.py`），报表只引用副本 sha16 |
| 2 | 复核前记一次 sha16，读完再记一次，**两次不同则那次读数作废** |
| 3 | **凡「文件里有/没有某段代码」的断言，必须先能编译** —— 否则你说的是**文本**，不是**代码** |
**⇒ 我的执行**：本轮读数 **`9ed1a265353ebdf1` / 27,901 B / 613 行**，**读前读后同值**；语法用 `ast.parse` 验（不写 `.pyc`，守住只读边界）⇒ `AST_OK`。
**⇒ 这条与「读数必须带 sampled_at + sha16」是同一条规矩的另一半**：**前者管「读数是什么时候的」，后者管「读数是不是一段真代码」。**

### 读当前 `chat.py`（`9ed1a265353ebdf1`）：**范围已修、§5.7 第④步已补；但仪器只装了半个**
| 观察 | 行 | 判 |
|---|---|---|
| 清理循环遍历集合已改 | **L517** `for name in [n for n in mounted if n not in want]:` | **范围修了**：不再遍历 `mounted` |
| `dropped` 仍是 seq 列表 | L514 | **同一集合的两份独立表达式**（名字过滤 / seq 过滤）⇒ 须证明相等，否则又是同名字段两定义 |
| `seqs_before` | **L516** | 记了 |
| **`seqs_after`** | **不存在** | **没记** |
| **`other_seqs_unchanged`** | **不存在** | **没记** |
| 断言助手 | **L120 `_m4c_assert_scope(where, before, after, dropped)`** | **定义存在，调用点 0 处** |
⇒ **对 lead 问的「是断言还是打印」的答案**：**两者都不是 —— 现在是一个装了一半的仪器 + 一个没接上的断言。**
| §5.7 第④步 | **L542–543** `_m4c_witness_attached(eng, seq, n, end, "m1.mount.before_load")` | **补上了** ⇒ §5.7 四步（token数/repos_local/seq_cp/pos_max）**现在齐** |


### 纪律（lead 2026-10-25 立，纠正我）：**`not in S` 的排除条件，只有被排除对象可能 `in S` 时才有判别力**

**我的错**：`orphan = sum(n_tokens(s) for s in range(n_seq) if s not in mounted_seqs)`
**为什么无效**：`mounted` 的 `seq = i + 1` ⇒ `mounted_seqs ⊆ {1..7}` ⇒ **`0 not in mounted_seqs` 恒真** ⇒ **`seq0`（对话）照样被算进去** ⇒ 假红照旧。
**正确**：`sum(... for s in range(1, n_seq) if s not in mounted_seqs)` —— **用下界排除，不能用集合排除**（注释：seq0 是对话 seq，永远不在 mounted_seqs 里）。
**⇒ 一般化（lead）**：**排除式不命中 = 「防线的取值恰好落在正常区间里」** ——
| 形态 | 表现 |
|---|---|
| **排除式不命中** | `not in S` 恒真 ⇒ 该排除的对象从未被排除 |
| **兜底值撞合法值** | `except: return 1` 恰好落进合法域 |
**同族**：**防线在正常区间内取值/判断，于是永远命中不了它该挡的东西。**

### 我核了这到底是真伤还是无害：**是真伤**（`chat.py` `55a99bdbc952b48f` / 616 行）
| 行 | 代码 | 含义 |
|---|---|---|
| **L568**（`cmd_m1` 内） | `ans = eng.ask(0, q, n_predict=48, pos=CHAT_START if first else None)` | **第一问从 `CHAT_START` 起；此后 `pos=None` ⇒ 接在上次尾部之后** |
| L295（`cmd_chat` 内） | 同形 | 同一语义 |
⇒ **`n_tokens(0)` 每轮单调增长** ⇒ 若计入 `orphan`，**两分支都单调增长** ⇒ **判据零判别力。** lead 的 `range(1, n_seq)` **是必需的，不是防御性写法。**

### ⚠ 我的补充：`orphan` 必须**逐轮记 + 断言 max**，不能只记末态
**理由（与站点 3 被站点 4 掩码完全同形）**：挂载循环 **L532** `leases.reset(seq, ...)` 会把每个被重新挂载的 seq 清空。
⇒ **只要末轮把脏 seq 重新挂上，末态 `orphan` 就回到 0** ⇒ **删掉 L503 也会读成绿** ⇒ **假绿。**
**⇒ 做法**：每轮记 `orphan_turn`，产物带序列；**断言 `max(orphan_turn)` 不随轮次增长**；删 L503 ⇒ `max` 持续增长。
**⇒ 这与 lead 要求的 `chat_n` 交叉自检互补**：`chat_n` 证明「排除对话生效了」，`max(orphan_turn)` 证明「末轮重挂没有掩盖泄漏」。


### 裁定（lead 2026-10-25）：**端点比对法在「范围」问题上原理上不成立** —— 换成调用流

| 场景 | 端点法的判 | 真实 | 错向 |
|---|---|---|---|
| `want` 变多 | seq2 空→有 ⇒ die | 正常挂载 | **假红** |
| `want` 重排 | 两 seq 互换 ⇒ die | 合法重排 | **假红** |
| **清了又填回原样** | before == after ⇒ 通过 | 范围越界 | **假绿** |
**⇒ 原理**：**端点法只看两端，而「谁被碰过」是过程属性。**
**⇒ 我的 `allowed = dropped ∪ range(1, len(want)+1)` 被否 —— 它只治假红、治不了假绿。**「治一半」的判据比没有更坏，因为它会被当成有了。
**⇒ 打印保留但降级**：`seqs_before/seqs_after` 标 **role: exhibit（供人看，不是判据）**；**调用流断言** 标 **role: assertion（唯一签名依据）**；**`_m4c_assert_scope` L120 删除**（方法不成立，留着随时会被接上）。

### 但 lead 的调用流断言**少一步**：`self.sites` 是全程累积的（`chat_lease.py` `619a043215035de7`）
| 行 | 代码 | 含义 |
|---|---|---|
| **L289** | `self.sites = {}` | **构造时一次** |
| **L329** | `self.sites.setdefault(tag, []).append({"seq": int(seq), "cells_after": cells})` | **只追加，从不清空** |
⇒ **`leases.sites[tag]` 跨轮累积** ⇒ **多轮 run 里 `hits` 会含前几轮的 seq** ⇒ `set(hits) == set(dropped)` **必然假红**（attempt7 夹具有两个 unmount 事件：turn3、turn4）。
**⇒ 必须按轮切片**：
```
n0 = len(leases.sites.get(tag, []))        # 进循环前
... 清理循环 ...
hits = [r["seq"] for r in leases.sites.get(tag, [])[n0:]]
assert set(hits) == set(dropped)
```
**⇒ 一般化**：**「调用流」类断言必须同时记「流的起点」** —— 没有起点的流是一条越来越长的全历史，任何集合比较都会把历史算成当前。


### 纪律（lead 2026-10-25，我补一条隐性后果）：**比较一条流的断言，必须先记流的起点**

> **没有起点的流是一整段历史，而历史不等于当前。** `EVENT_LOG` 同理，凡读它都必须带起点。
**隐性后果（lead）**：这类断言**随 run 变长越来越容易假红** ⇒ **首次跑绿、跑十轮后红**，看起来像「代码退化了」，其实是**断言没记起点**。
**⇒ 补**：这也是**假红伪装成回归**的少有形，与「假绿」方向相反但同源 —— **都是把「时间」当成了「状态」。**

### 见证者改名（lead）：`_m4c_witness_empty` → `_m4c_witness_coverage`，并写明「L331 已保证空；本函数只保证覆盖」
| 见证者 | 它到底证了什么 | 名字说它证什么 |
|---|---|---|
| `_m4c_witness_empty` | **「dropped 里每个 seq 都被 reset 过」—— 覆盖** | 「为空」 |
**「为空」已被 L331 强制**（`reset` 后 `cells_of != 0` 直接 `raise`）⇒ 见证者对「空」零贡献，**唯一新增是覆盖**。
**⇒ 这是「名字不得表达结论」的第 N 例**：**名字替它宣称了一个它不负责的结论。**

### ⚠ 但 lead 的 ③（`dropped` 单一来源）与 ④（覆盖见证者的「漏掉才响」）互斥 —— 我只能守住半边

**lead 给 ④ 的理由**：「若某个 dropped seq 被循环漏掉，L331 不会响，见证者才响。」**这句话成立的前提是：`dropped` 与循环遍历集合来自两条独立推导。**
**而 ③ 要求单一来源**：若写成 `drop_names = [...]; dropped = [mounted[n][0] for n in drop_names]; for name in drop_names:` ⇒ **覆盖由构造保证** ⇒ **「漏掉」在结构上不可能发生** ⇒ **见证者的漏检半边变成死代码**，只剩「越界」半边。
| 方案 | 越界（多清） | 漏掉（少清） |
|---|---|---|
| **单一来源（③）** | ✔ 抓 | **✘ 结构上不可能** |
| **两条独立推导** | ✔ 抓 | ✔ 抓 |
**⇒ 我的建议**：**动作与期望分开推导，再加一条桥断言**
```
expected = [n for n in order if n not in want]          # 语义来源：上一轮挂载表 vs 本轮 want
drop_names = [n for n in mounted if n not in want]      # 动作来源：循环用它
if expected != drop_names: die("两份表达式不一致：%s vs %s" % (expected, drop_names))   # ← ③ 的关切
dropped = [mounted[n][0] for n in expected]             # ← ⑧ 见证者比它
```
**⇒ 这样 ③ 与 ④ 同时成立，而不是用 ③ 吃掉 ④ 的一半。**
**⇒ 一般化**：**「单一来源」与「独立见证」是一对反向要求** —— **同一个对象既要唯一出处、又要能被人对着另一个出处核验；只满足一边，另一半就变成装饰。**


### 我又错一次（lead 指出）：**我那条 `expected` vs `drop_names` 的修法没恢复「漏掉」半边**

**为什么没恢复**：`if expected != drop_names: die(...)` **一通过，`expected == drop_names` 就成立** ⇒ 循环必然覆盖全部 `expected` ⇒ 「漏掉」依旧不可能 ⇒ **见证者拿 `dropped` 去比 `sites` 永远相等**。
**⇒ 我把「两份可能不一致」换成了「两份必须先相等」，中间那一半还是没了。**
**并且引入新假红（lead 补充）**：`if not control:`（L529）时 `mounted` 不填而 `order = want` ⇒ **control 模式下 `expected != drop_names` 必然触发**。

### lead 的正解：**见证者要来自「另一个层次」，不是另一份列举**
| # | 断言 | 来源 | 抓哪个方向 |
|---|---|---|---|
| **A 越界** | `set(sites 里 reset 的 seq) == set(dropped)`（带 `n0` 起点） | **租约表**（调用流） | **多清** |
| **B 漏掉** | 回合末 `orphan == 0`，`orphan = sum(n_tokens(s) for s in range(1, n_seq) if s not in mounted_seqs)` | **引擎**（`n_tokens`） | **少清** |
**为什么 B 真能抓漏掉**：漏掉的被丢 seq **既不在新一轮 `mounted_seqs`、又留着 cell** ⇒ `orphan > 0`。
**为什么不假红**：仍被需要的块在新一轮 `mounted_seqs` 里 ⇒ 不计入。
**⇒ B 就是 M4-C-4 那个量 ⇒ 零新增仪器，一举两得：既是覆盖见证，又是泄漏判据。**

### 我改一句自己的原则（lead 改写版，我更正过来）
> **单一来源管「我改哪里」，独立见证管「改完对不对」。前者要求唯一，后者要求异层。**
> **拿同一对象的第二种写法当见证，只能证明两段代码抄得一样；拿引擎状态当见证，才能证明动作真的发生了。**
**⇒ 我的原句「同一个对象既要唯一出处、又要能对着另一个出处核验」是错的** —— **「另一个出处」如果只是另一种写法，等于同一通道两次调用**，正是我自己早先立的「机制独立」纪律所禁止的。**我用自己立过的纪律能判掉自己的提议，但这次是 lead 先判掉的。**


### 六件落地核查（sampled_at **2026-10-25T06:12Z**，`tools/chat.py` = **`b9062132b92ffb95` / 630 行**，读前读后同值）

| # | 项 | 行 | 判 |
|---|---|---|---|
| ① | 删 `_m4c_assert_scope` | 全文件 0 处 | **已删** |
| ② | 断言 A（调用流 + `n0` 起点） | **L509** `n0 = len(leases.sites.get("m1.unmount.after_detach", []))`；**L517** `hits = [...][n0:]`；**L518–520** `if set(hits) != set(dropped): die(...)` | **已上** |
| ③ | 断言 B（引擎侧 `orphan`） | **L553–561** `mounted_seqs` / `orphan_cells` / `orphan` / `chat_n` / `if orphan != 0: die(...)` | **已上，求值点在挂载循环之后（L543 < L554）** ✓ |
| ④ | `dropped` 单一来源 | **L503** `drop_names` / **L504** `dropped = [mounted[n][0] for n in drop_names]` / **L510** `for name in drop_names` | **已上** |
| ⑤ | 改名 `_m4c_witness_coverage` | **L90** 定义；**L523 / L533** 两处调用点；L521 注释「L331 已保证空，这里只保证被清过」 | **已上，注释同步改了** |
| ⑥ | `seqs_after` + `role: exhibit` | **L505/L544** 注释带 `role: exhibit`；**L506** `seqs_before`；**L545** `seqs_after`；L546–548 打印 | **已上** |
⇒ **六件全落地，且我按快照规矩复核（两次 sha16 相同）。**

### 但三处残留，交付前应处理
| # | 残留 | 依据 |
|---|---|---|
| 1 | **`control` 模式下两条断言都是空的**：A 的 `drop_names` 来自 `mounted`，而 `mounted` 只在 `not control`（L525）时填 ⇒ control 模式 `drop_names=[]` ⇒ A 恒过；B 整段在 `if not control:`（L552）里 | **control 模式的绿不得算作覆盖** |
| 2 | **`range(1, 8)` 硬编码**，而 `n_seq=8` 在 **5 处** `KVEngine(...)` 里重复 | **同源纪律**：应提成常量，否则改 `n_seq` 时断言读错 seq |
| 3 | A 用 `set(hits) != set(dropped)` ⇒ **看不见「同一个 seq 被清两次」** | 低优先；若要严，比排序后的 list |


### 判法（lead 2026-10-25，我记）：**一条定义若按字面会否掉一个显然正确的对象，那就是定义错了，不是对象错了**

**经过**：lead 上一轮从我的发现里提炼出「异层 = 见证者输入里不得出现被判对象的表达式」；**我按字面指出它会把 B（引擎侧 orphan）也否掉**（`mounted_seqs` 与 `dropped` 同源）⇒ **定义被自己的一个显然正确实例否掉 ⇒ 定义错。**
**最终版（两版合并，缺一不可）**：
| 判 | 问什么 | 内容 |
|---|---|---|
| 我判「是不是期望」 | 输入是**决定**还是**参照** | 不得出现**期望列举**（另一函数算出的名单） |
| lead 判「是不是结果」 | 输入是**决定**还是**结果** | 只允许**结果读数**与**常量** |
> **用「结果」核对「期望」是验证；用「期望」核对「期望」是复述。**
**⇒ 由此 A 的交付措辞写死**：**A 只判「执行是否符合口径」，不判「口径对不对」。**（A 的输入含 `dropped`。）

### 但由此暴露一个**新的死见证**：`_m4c_witness_coverage`（L90）的 docstring 仍在宣称一个 ③ 已经摧毁的能力

| 事实 | 依据 |
| L522–523 `for seq in dropped: _m4c_witness_coverage(...)` | 见证 |
| 循环遍历 `drop_names`（L510），而 `dropped = [mounted[n][0] for n in drop_names]`（L504） | **同一份名单** |
⇒ **「漏掉某个 dropped seq」在结构上不可能发生** ⇒ 该见证**恒真** ⇒ 它的 docstring（「若循环漏掉某个 dropped seq，L331 不会响，这里才响」）**描述的是一条走不到的路**。
**⇒ 处置二选一（我不代裁）**：(a) 删 L522–523，覆盖判据只留 B（引擎侧）；(b) 保留但把注释改成「本站已被 L331（空）+ 同源循环（覆盖）双重保证 ⇒ 本见证恒真；覆盖判据在 B」。
**⇒ 无论哪条，交付里都不能写「站点 3 有覆盖见证」** —— **覆盖的实际承担者是 B。**

### 顺带一条正面的核查结论（A 未被污染）
**`_m4c_witness_coverage` L98 只调用 `leases.cells_of`（只读）** ⇒ **不向 `sites[tag]` 追加** ⇒ **A 的 `hits`（L517）不会被见证者本身污染** ✓。这条必须核，否则 A 会把自己的调用算进调用流。


### 裁定 (a) 落地前必须同时改夹具 —— **删 `_m4c_witness_coverage` 会打断两个产生验收产物的脚本**（sampled_at 06:15Z，`chat.py` = `a637cec607f0d2a0` / 651 行）

**先记状态**：④ 尚未删（L95 定义 + L532 / L549 两个调用点仍在）；①②③ 已落地：
| 项 | 行 | 判 |
|---|---|---|
| ③ `N_SEQ` | **L74** `N_SEQ = 8`；L511 `range(N_SEQ)`；L570 `range(1, N_SEQ)` | **已上** |
| ② A 改 list 相等 | **L523** `if hits != dropped:` | **已上**；但 **L525 的报错信息仍用 `sorted(set(...))`** |
| ① control skip 记录 | **L536–539** `M4C_ASSERT_LOG.append({"id": "A"/"B", "status": "skipped", ...})`；L71 注释 | **已上** |

### ⚠ 关键风险：夹具在 monkeypatch 这个函数
| 文件 | 行 | 代码 |
|---|---|---|
| `run_site3.py` | **L69** | `orig_empty = chat._m4c_witness_coverage` |
| `run_site3.py` | **L75** | `chat._m4c_witness_coverage = traced` |
| `redcheck_delete.py` | **L59 / L64** | 同上（`traced_empty`） |
⇒ **函数一删，两个脚本在建 `traced` 之前就 `AttributeError`** ⇒ 运行失败 ⇒ **产物缺失**；若被 try/except 兜住，则产物里 `witness_seqs` / `site3_witness_pass` **变空** ⇒ **空字段被读成"没有见证者"或"通过"**。
**⇒ 因此 ④ 必须与夹具改造同批**：
| 旧依据 | 新依据 |
|---|---|
| `witness_seqs` / `site3_witness_pass`（来自被打桩的见证者） | **`M4C_ASSERT_LOG` 里的 `assertion_A` / `assertion_B` 状态** |
⇒ **并且夹具不得再 patch 一个不存在的函数**；`site3_witness_*` 字段应删或改名，避免"字段还在、内容已无来源"。

### 另：② 的报错信息与断言口径不一致（小但会误导）
**L523 断言**：`hits != dropped`（list，能抓重复/乱序）；**L525 报错**：`sorted(set(hits))` / `sorted(set(dropped))`。
⇒ **若因「重复」而红，报错里两个列表会一模一样** ⇒ 读的人会以为**假红**。**⇒ 报错必须用同一口径（list），与断言一致。**


### 核 lead 的第 ④ 条（断言日志须在 `die()` 前落盘）：**当前形态下这条不成立，但真正的坑在旁边两处**（`a637cec607f0d2a0`）

| 行 | 代码 | 含义 |
|---|---|---|
| `chat.py` **L72** | `M4C_ASSERT_LOG = []` | 模块级内存列表 |
| `chat.py` **L127–129** | `def die(msg): print(...); sys.exit(1)` | **无 flush** |
| `run_site3.py` **L15** | `sys.path.insert(0, ROOT/tools)` | **同进程 import `chat`** |
| `run_site3.py` **L88** | `rec["assertions"] = list(getattr(chat, "M4C_ASSERT_LOG", []))` | **同进程读模块属性** |
⇒ **`die()` 的 `sys.exit(1)` 抛 `SystemExit`，同进程里由夹具接住，模块属性仍活着** ⇒ **当前形态下「红的那次没有日志」不会发生。**
**⇒ 但 lead 的要求在精神上仍成立，只是失效条件不同**：**一旦夹具改成 subprocess，日志会静默消失、每次红都变 MISSING** ⇒ **这是潜伏风险，不是现存缺陷。**（必须这样写，否则交付里会写错归因。）

### ⚠ 真正的缺陷在 L88：**`getattr(..., [])` 把「没有日志」变成「日志为空」**
⇒ **这正是 lead 第二节要区分的三态（`failed` / `skipped` / 日志缺失）—— 现在代码在结构上区分不出来**，因为缺失被默认成空列表。
**⇒ 要求**：`hasattr` 缺失时必须记 `status: "log_missing"` 并**判失败**，不得用 `[]` 兜底。**（与 `MISSING ∉ EQUAL` 同一条规矩。）**

### ⚠ 第二处：日志跨调用累积（「流要带起点」的第三个实例）
`M4C_ASSERT_LOG = []` 只在 **import 时**执行一次；**若同一进程跑两个 arm（如 `redcheck_delete.py` 在一个进程里跑删/不删两组）**，第二组读到的是**两组的并集** ⇒ 红绿混在一份日志里。
**⇒ 要求**：`cmd_m1` 入口 `M4C_ASSERT_LOG.clear()`，或读者记起点切片。**与 `sites` 那条完全同形。**

### 纪律（lead）：**报错口径必须与被判口径一致。不一致时，红会被读成假红。**
**危害方向**：**假绿放过缺陷，假红让人撤掉一条正确的断言** —— **今天已经因为假红撤过一次（`sum(n_tokens)` 那次，lead 差点撤掉方法）。**
**⇒ 补**：**假红比假绿更容易被"修好"** —— 因为它表现为「断言错了」，而人改断言比改代码便宜。**所以假红的复发率更高。**


### 核 lead 的发现并补两处（sampled_at 06:19Z，`chat.py` = `7e3c2ab6fe0db4f7`，`run_site3.py` = `45bd77556fe2d975`）

**lead 的判断我核实**：`_m4c_log` **L76** docstring 写「立刻落盘」，**L82–85** 却是 `if path:` 才写 ⇒ **条件行为写成无条件**。
**⇒ 纪律**：**docstring 里出现「总是/立刻/一律/必然」，就去代码里找 `if`。**
**⇒ 今天第二次同形**：`_m4c_witness_coverage`（宣称抓漏掉，实为恒真，已删）· `_m4c_log`（宣称立刻落盘，实为条件落盘）。

### ⚠ 补 1：`open(path, "w")` + **固定默认路径** ⇒ 读者可能读到上一轮的日志
| 环节 | 事实 |
|---|---|
| 写 | **L84** `open(path, "w")` 每次重写整份列表 ⇒ 文件永远是"完整快照" |
| 读取（现状） | `run_site3.py` 读**内存**，不读文件 |
| 待改成读文件后 | **若本轮在任何 `_m4c_log` 之前就崩，文件仍是上一轮那份** ⇒ 读者会把**旧断言**当本轮结果 |
**⇒ 要求**：**写入方在 `cmd_m1` 入口就创建/清空文件**，并在文件里带**运行身份**（`mode` + `chat_py_sha16` + `sampled_at`）；**读取方校验身份，身份不符即 `log_missing`**。
**⇒ 否则这一批把"内存易失"换成了"文件易旧"，问题只是换了个方向。**

### ⚠ 补 2：`assertions_status` 把「崩」判成 `failed`（`run_site3.py` L81）
```
81: rec["assertions_status"] = "failed" if rec["exit"] not in (0, None) else (
82:     "skipped" if statuses == {"skipped"} else "checked")
```
⇒ **凡 `exit != 0` 一律记 `failed`** ⇒ **断言红与"跑到一半崩了"在这一栏里同值**；`log_missing` 只覆盖"完全没有日志"的情形。
**⇒ 要求的第三态只成立一半**：`failed`（断言红）· `skipped`（无对象）· `log_missing`（真崩）**三者中，前两者与"有日志的崩"仍不可分。**
**⇒ 修法**：**`die()` 输出带可机器识别的标记**（如 `error: M4C ...` 前缀已在用）+ 产物记 `die_kind: assertion|crash`（判据：`die_message` 是否以 `M4-C` 开头）。

### 顺记一条已修好的：产物文件名现在带 `mode` + `tag`（`run_site3.py` L86 `M4C-SITE3-%s-%s.json`）⇒ **判定不进文件名**，早前那四例的根因已消。


### 核 lead 的 `run_id` 方案（`chat.py` = `7e3c2ab6fe0db4f7` / 660 行，读前读后同值）

**先报一条我查了但不成立的怀疑（免得当成缺陷）**：
| 怀疑 | 核查 | 结论 |
|---|---|---|
| `_m4c_log` 是死代码，四处直接 append 到列表 ⇒ 从不落盘 | **L539 / L547 / L549 / L587 四处全部调用 `_m4c_log({...})`**；**唯一的 `.append` 在 L81（函数体内）** | **不成立：写入方是单点** ✓ |
⇒ **这条正面结论支撑 `run_id` 方案**：单一写入口 + 路径即身份 ⇒ 不存在"绕过去的那条路"。
**另核**：**L82 `os.environ.get` 在函数体内**（不是 import 时缓存）⇒ **夹具在 import 之后设环境变量也生效** ✓

### ⚠ 但 `run_id` 必须**每 arm 一次**，不能每进程一次
`redcheck_delete.py` **在一个进程里跑两组 arm**（L59/L64 两次 patch）。**若 `run_id` 在 arm 循环外生成一次**，两组写**同一个文件** ⇒ **第二组覆盖第一组** ⇒ **"文件会旧"原封不动地回到进程内部**。
**⇒ 要求**：`run_id` 在**每个 arm 开始处**生成。**这就是「流要带起点」换了个载体：起点不是 `n0`，是路径。**

### ⚠ `die_kind` 不得由字符串前缀推断，必须由 `die()` 自己盖章
lead 的方案：`die_kind = "assertion" if die_message 以 "M4-C" 开头 else "crash"`。
| 反例 | 消息 | 真实类别 | 前缀推断给 |
|---|---|---|---|
| 挂载位置断言 | `die("%s: repos_local refused" % name)` | **断言红** | **`crash`（错）** |
⇒ **消息措辞承担了语义** ⇒ **改一句话就改一次分类，而且没人知道。**
**⇒ 修法**：**`die()` 自己记 `kind="assertion"`**（`die()` 按定义就是断言失败）；**`crash` = 异常路径（有 traceback、无 `die_message`）**。
**⇒ 一般化**：**分类信息必须由产生它的那个函数盖章，不得由外部对它的输出做模式匹配** —— 否则分类依赖于**文案**，文案是最容易变的东西。

### 纪律（lead）：**改一个跨调用状态问题时，先改读取方，不要先改所有写入方。**
**理由**：写入方 N 处，漏一处就复发；读取方 1 处，改对一次就关死。**与「结构优先于纪律」同条。**

### 交付措辞（lead）：`run_site3.py` L86 文件名带 `mode`+`tag` ⇒ **关闭的是「根因」，不是「那四个文件」** —— **历史产物仍在盘上、名字仍骗人**；**交付必须写「历史产物未改名，以 `is_red` 字段为准」。**


### ⚠ `run_id` 只换了路径，没换内容 ⇒ lead 的「累积不可能」不成立（`chat.py` = `b15038df53d6e3b3` / 657 行）

| 行 | 代码 |
|---|---|
| **L82** | `M4C_ASSERT_LOG.append(entry)` |
| **L88** | `fh.write(json.dumps(M4C_ASSERT_LOG, ...))` ← **写的是整个模块级列表** |
| 全文件 | **无 `M4C_ASSERT_LOG.clear()`** |
⇒ **路径按 arm 变了，内容没有** ⇒ **后跑的 arm 的文件里含前一个 arm 的全部断言** ⇒
| 场景 | 后果 |
|---|---|
| 同一进程先跑红 arm 再跑绿 arm | 绿 arm 的文件里带着红的 `assertion_failed` ⇒ **五态判定把绿读成红** |
| 先绿后红 | 红 arm 的文件里带着绿的 `checked` ⇒ **`statuses == {"skipped"}` 这类集合判断全部失真** |
**⇒ 结论**：**`run_id` 解决的是「读到别的文件」，没解决「读到别的 arm 的条目」。两件事。**
**⇒ 要求**：`cmd_m1` 入口 `M4C_ASSERT_LOG.clear()`（或 `_m4c_log` 写"本 arm 起点以来的切片"）。**`clear()` 仍然需要。**
**⇒ 一般化**：**换载体（路径/文件名/对象）只隔离了"容器"，没隔离"容器里的东西"。** 容器换新而内容共用，等于没隔离。

### 已核的正面结论（进入交付的"前置条件已验证"）
| 事实 | 意义 |
|---|---|
| **无 `rmtree` / `os.remove` / `os.unlink` / `tempfile`**（全文件 0 处）；5 处 `finally`（L177/332/414/443/625）**均非破坏性** | **没有任何清理路径能删掉断言日志文件** ⇒ 新证据通道不会被 `finally` 抹掉 |
| **L86–89 tmp + `os.replace`** | **原子写**：任何时刻盘上要么完整旧版、要么完整新版 ⇒ **不会读到半截 JSON** |

### ⚠ 但 `die()` 接上 `_m4c_log` 后，写文件失败会顶掉主消息
`_m4c_log` 里 `open(tmp)/os.replace` 可能抛 `OSError` / `PermissionError`（Windows 上被杀软/占用触发过）。
⇒ 若 `die()` 直接调它，**异常发生在 `print` 之前** ⇒ **盘上没有日志，屏幕上也没有那条断言消息，只剩 traceback** ⇒ **最需要消息的时刻消息没了。**
**⇒ 要求**：`_m4c_log` 的写盘段 `try/except OSError: pass`（内存列表仍记），**保证 `die()` 一定打印并 `exit(1)`**。
**⇒ 一般化**：**证据通道的失败不得吞掉主消息** —— 取证比记录重要：先保证讯息出去，再保证它被存下来。

### `die()` 现状：**⑦ 尚未落地**
**L135–137** 仍是 `def die(msg): print(...); sys.exit(1)` ⇒ **不盖章、不写日志**。
⇒ 在此之前，产物里对"红"的判断只能靠 `exit != 0`，**`assertion_failed` 与 `crash` 仍不可分**。

### 两条元纪律（lead 2026-10-25，我记）
> **核查的产出有两种：发现缺陷，和确认前提。后者容易被当成没干活。**
> **驳回了一个错误理由 ≠ 那行代码不必要。结论可以因新理由重新成立，但记录必须写清是哪个理由。**


### 核 lead 的 `clear()` 位置裁定：**结论对，理由错；而且错的那一面已经在代码里了**（`chat.py` = `b15038df53d6e3b3` / 657 行）

**lead 的理由**：「`cmd_m1` 是**一轮**的入口，若在那里 clear，文件里只剩最后一轮。」
| 核查 | 事实 |
|---|---|
| `cmd_m1` 内部turn 循环 | **L480 / L494** `for q in [CONTROL_Q] + QUESTIONS:` ⇒ **4 个 turn 在一次调用内** |
| 夹具调用次数 | `run_site3.py` **L71 `chat.cmd_m1()`** —— **全文件仅此一处** |
| 夹具自述 | `run_site3.py` **L53** `"drive": "cmd_m1()：一个引擎、两个不同选择..."` |
⇒ **一次 `cmd_m1()` = 一个 arm = 4 个 turn** ⇒ **在 `cmd_m1` 入口 clear 不会丢任何 turn。lead 的理由不成立。**

### 但 lead 的结论仍成立 —— 真正的冲突不在 turn 之间，在**两个入口函数**之间
| 文件 | 行 | 代码 |
|---|---|---|
| `redcheck_delete.py` | **L66** | `chat.cmd_chat(control=True)` |
| `redcheck_delete.py` | **L74** | `chat.cmd_m1()` |
⇒ **一个 arm 里可以有两个入口函数** ⇒ **只有夹具知道 arm 的边界** ⇒ **`clear()` 应归夹具。结论对。**

### ⚠ 而代码里现在已经在 `cmd_m1` 入口 clear 了 —— 这是一个正对着下一件收口的雷
| 行 | 代码 |
|---|---|
| **L474** | 注释「内存台账是本进程的历史；每次进入都清空。文件按 run_id 隔离，不需要清。」 |
| **L475** | `M4C_ASSERT_LOG.clear()` |
| `_m4c_log` 调用点 | **L536 / L544 / L546 / L584** —— **全部在 `cmd_m1`（L471+）内**；`cmd_chat`（L187–381）**今天一处也没有** |
| **站点 1** | **L241** `leases.reset(i, site="chat.place.fresh")` —— **在 `cmd_chat` 里** |
⇒ **今天无害（`cmd_chat` 不记断言），但下一件收口正是「站点 1 一次删行实测」**，而站点 1 的断言必然加进 `cmd_chat`；
⇒ **那时 `redcheck_delete.py` 的 L66 → L74 顺序会让 L475 把站点 1 的记录抹掉** ⇒ **恰好抹掉我们正要取证的那一条。**
**⇒ 要求（在本批一起做）**：**删掉 L475 的 `clear()`**，改由夹具在 arm 起点做。**否则下一轮会得到"站点 1 无断言记录"的产物，而它看起来像"站点 1 没有断言"。**

### 纪律（lead，我记并补一句）
> **同一条边界必须由同一个所有者重置。**
**⇒ 我补**：**先问「这条边界上到底有几个动作」，再问「谁拥有它」** —— 本例里"边界"一词有两个候选（turn / arm），**选错候选，所有者就选错。** lead 的结论选对了候选，理由选错了；而**代码照着错的理由写了一行，这行正对着下一件收口。**


### 独立复核 lead 读数（我读，不采信）：`chat.py` = **`bc30da97b06db17b` / 32,029 B / 667 行**，读前读后同值
| 项 | 值 |
|---|---|
| `.clear()` 命中 | **0 处** ⇒ **L475 那颗雷确已不在** |
| `M4C_ASSERT_LOG` 相关行 | L72 定义 · L85 `append` · L87 `os.environ.get` · L91 `json.dumps(M4C_ASSERT_LOG, ...)`（**仍写整表**） |
| `die()` | **L141**，docstring 已写「分类由产生它的函数盖章」 ⇒ **⑦ 在落地中** |
⇒ **与 lead 读数一致**，且**行号 + sha16 同报**，跨 sha 可核。

### 提议：**把「清空」换成「分桶」，键就是路径** —— 让累积在结构上不可能，且不需要任何 `clear()`

**现状**：`_m4c_log` **L91** 把 `M4C_ASSERT_LOG`（模块级、进程级）**整表**写进当前 arm 的文件 ⇒ 后跑的 arm 带着前一个 arm 的条目。
**lead 的修法**：夹具每 arm 起点 `clear()` ⇒ **正确，但依赖夹具记得**。
**替代修法（我更倾向，理由如下表）**：
```
_M4C_LOGS = {}                                  # path -> list
def _m4c_log(entry):
    path = os.environ.get("M4C_ASSERT_LOG_PATH")
    bucket = _M4C_LOGS.setdefault(path, [])     # 新 arm = 新路径 = 新桶
    bucket.append(entry)
    ...                                          # 落盘只写 bucket
```
| 性质 | 夹具 clear() | 分桶 |
|---|---|---|
| 累积是否可能 | 夹具忘了就可能 | **不可能**（新路径必新桶） |
| 需要谁配合 | 两个夹具文件 | **无人配合** |
| 生产侧 clear | 禁止（lead 已定） | **不需要**（同一句约束） |
| 与「路径即身份」的关系 | 路径隔离文件，clear 隔离内容（**两处**） | 路径**同时**隔离文件与内容（**一处**） |
**⇒ 它把两条要求（`无默认路径` + `无 clear`）合成一条：`路径 = 桶键`。**
**⇒ 并且它对 `cmd_chat` / `cmd_m1` 两个入口都自动成立** —— 站点 1 的断言写进 `cmd_chat` 时不需要任何额外约定。
**⇒ 若采纳，夹具侧只需生成 `run_id` + 设路径，`clear()` 这一动作整条消失。**


### 裁定走分桶（v5）。但先说一件排期事实：**v4 已经落地了，v5 要把它刚写的那两行删掉**

**读数**：`chat.py` = `bc30da97b06db17b` · `run_site3.py` = `431e586684232991` · `redcheck_delete.py` = `568a790c7174adea`（读前读后同值）
| 文件 | 行 | 代码 |
|---|---|---|
| `run_site3.py` | **L42 / L43 / L45** | `run_id = uuid.uuid4().hex[:8]` / `logp = out/asserts-<run_id>.json` / `os.environ["M4C_ASSERT_LOG_PATH"] = logp` |
| `run_site3.py` | **L48** | `chat.M4C_ASSERT_LOG.clear()` |
| `redcheck_delete.py` | **L41 / L42 / L44 / L47** | 同上，含 `chat.M4C_ASSERT_LOG.clear()` |
| `chat.py` | **L147** | `_m4c_log({"id": "die", "status": "assertion_failed", "kind": "assertion", ...})` ⇒ **⑦ 已落地** |
⇒ **v4 是真的运行过一版；v5 上线后 `clear()` 两行要删。**
**⇒ 交付与决策记录必须写「v4 → v5，`clear()` 曾被采纳后又被结构取代」** —— 否则下一个人从 git 历史里看到 `clear()` 会以为它是对的，**再把它加回来**。
**⇒ 一般化**：**被更高一层结构取代的中间实现，必须在决策记录里留墓碑**，否则它会以「历史最佳实践」的形式复活。

### ⚠ v5 之后必须删掉 `M4C_ASSERT_LOG = []`（`chat.py` L72），否则留下一个恒空列表
| 事实 | 含义 |
|---|---|
| 两个夹具**已改为读文件**（`run_site3.py` 里 `M4C_ASSERT_LOG` 只剩 L4 注释与 L48 待删的 `clear()`） | **`chat.M4C_ASSERT_LOG` 在 v5 之后零读者** |
| 但 L72 仍在，且 v5 的 `_m4c_log` 若改成只写 bucket，**这个列表永远空** | **下一个读它的人会得到 `[]`** ⇒ **正是 `getattr(..., [])` 那个坑的静态版本** |
**⇒ 要求**：**连 `M4C_ASSERT_LOG = []`（L72）一起删**，不要留一个"看起来是台账、实际恒空"的属性。

### ⚠ 须写进交付的已知限制：**无路径 ⇒ 不记账**
`if not path: return entry` ⇒ **手动 `python chat.py m1` 跑一轮，盘上没有任何断言台账**（只有 stdout）。
**⇒ 这是设计选择（不设默认路径 = 不猜身份），不是缺陷**，但**必须写明**，否则第一个手动跑的人会以为"没有断言失败"。


### 重取三份 sha16 + 全仓符号盘点（sampled_at 06:26Z，读前读后同值）
| 文件 | sha16 | `M4C_ASSERT_LOG` 命中 |
|---|---|---|
| `tools/chat.py` | **`356140bc615fcedf`** | **2 处（L73 注释 / L86 `env.get`）** ⇒ **v5 已落地，符号连根删** |
| `kvmem/m4c_leases/run_site3.py` | **`0dd31827a3e4e303`** | 2 处（**L4 docstring** / L44 环境变量名） |
| `kvmem/m4c_leases/redcheck_delete.py` | **`ae6899f7801d9f85`** | 2 处（**L4 docstring** / L44） |
**全仓合计 39 处 / 12 文件**（lead 报 48 —— 差异是因为他的扫描与我的扫描之间文件又变了，**这正是他命名的那件事本身**）。
**⇒ 活代码里已无该符号**；剩余命中全部在 `<sha16>` 快照与两处 docstring。

### ⚠ 但 `tmp/` 的处置不能一刀切：**15 个 `.py`，三类，其中一类改名会破坏夹具、一类是真代码**
| 文件（按名引用它们的活代码） | 性质 | 改名后果 |
|---|---|---|
| **`redcheck_delete.py` L25** `p = os.path.join(d, "chat_site%d_deleted.py" % site)` | **删行变体 = 生成物**（`chat_site1_deleted / site3_deleted / site4_deleted`） | **下次运行按原名重新生成 `.py`** ⇒ **改名被静默回滚** |
| **`redcheck.py` L60** `p = os.path.join(tmpdir, "chat_site%d.py" % site)` | 同上（`chat_site2 / chat_site3`） | 同上 |
| **`check_session_anchor.py` L7** 注释指名 `/tmp/find_anchor_rule.py` | **真代码（辅助脚本）** | **改名即制造一条新的假引用** |
| `chat-<sha16>.py` ×8（现役 `chat-356140bc615fcedf.py` 也在内） | **稳定副本，不被任何活代码读取**（`redcheck_delete.py` L11 用的是 `ROOT/tools/chat.py`） | **改名安全** ✓ lead 的方案适用这一类 |
| `base_chat.py`（见证前基线） | 副本，供 diff | 改名安全（diff 不受影响） |
**⇒ 正确处置**：
1. **`chat-<sha16>.py` ×8 + `base_chat.py` → 加 `.snap`**（或只留当前一份）；
2. **`chat_site*_deleted.py` / `chat_site*.py` → 删，并让脚本把变体写到 `tmp/variants/` 且以 `.snap` 结尾**；**只改名不改脚本 = 清理下次运行被回滚**；
3. **`find_anchor_rule.py` 不许改名**（`check_session_anchor.py` L7 指名它）。
**⇒ 一般化**：**"盘全仓字符串引用"这一步，必须在动手改名之前做，而且要看引用的是"名字"还是"生成规则"。** 名字被脚本按格式串拼出来（`"chat_site%d_deleted.py" % site`），**grep 精确文件名是找不到的** —— 只能 grep 格式串。


### 自纠（重要）：我上轮报「两处 docstring 仍引用已删属性」是**子串假命中**

| 量 | 值 | 说明 |
|---|---|---|
| `grep M4C_ASSERT_LOG` 原始命中 | **35** | **含 `M4C_ASSERT_LOG_PATH`** |
| `grep M4C_ASSERT_LOG_PATH` | **15** | 环境变量名，**活代码应该有的那些** |
| **边界匹配 `M4C_ASSERT_LOG[^_]`** | **20** | **全部 20 处都在 `tmp/*.py.snap` 快照里** |
| **活代码里的裸符号** | **0** | `tools/chat.py` + 两夹具**一处也没有** |
**⇒ 两处 L4 docstring 在我读的 sha 上已经是 `M4C_ASSERT_LOG_PATH 指向的文件`** ⇒ **lead 的 ④（改两处 docstring）是空动作**。
**⇒ 教训（我犯的）**：**`M4C_ASSERT_LOG` 是 `M4C_ASSERT_LOG_PATH` 的前缀**，子串匹配把"合法变量名"读成了"已删符号的引用"。
**⇒ 判法**：**盘点符号引用必须加边界**（`符号[^_]` 或前后界）；**当被盘符号可能是更长合法标识符的前缀时，无边界 grep 的命中数没有意义。**
**⇒ 这也是"grep 能证有不能证无"的姊妹条**：**grep 不仅能证错"无"，也能证错"有"。**

### 而 lead 的 ② 已被执行者用更优方案解决：**保留 `.py.snap` + 显式 `SourceFileLoader`**

| 文件 | sha16 | 关键行 |
|---|---|---|
| `run_site3.py` | **`38ff5ed4fdcfd579`** | **L24–26** 写 `tmp/variants/chat_site3_deleted.py.snap`；**L30–33** `SourceFileLoader(name, path)` + `spec_from_loader` |
| `redcheck_delete.py` | **`1b2bff62c9f49039`** | **L24–26** 写 `tmp/variants/chat_site%d_deleted.py.snap`；L30–33 同上 |
**⇒ lead 的判据「`.snap` 不能被 importlib 加载」只对 `spec_from_file_location`（按后缀推断 loader）成立**；**显式 `SourceFileLoader` 不看后缀** ⇒ **`.snap` 可执行**。
**⇒ 结果：B 类既不长成源码、又仍可加载 ⇒ 两个目标同时满足，比"移进目录 + 首行横幅"更彻底。**

### ⚠ 但若坚持要加首行横幅，有一个行号陷阱
`variant()` **返回 `i + 1`** 作为被删行号（`run_site3.py` L27），产物记的是这个值。**在 `lines` 头部 `insert(0, 横幅)` ⇒ 行号整体 +1 ⇒ 产物里的行号永久偏一行。**
**⇒ 行号是四件套的一件** ⇒ **横幅必须加在文件末尾，或同时 `+1` 修正返回值**。

### `tmp/__pycache__/` 现状：5 个 `.pyc` 已成孤儿
`chat_site1_deleted / chat_site2 / chat_site3 / chat_site3_deleted / chat_site4_deleted` 的源码**已不在 `tmp/` 下**（现为 `tmp/variants/*.py.snap`）⇒ **这 5 个 `.pyc` 不再对应任何源文件**。
**⇒ 可删（可再生）**；**删前已把"谁被 import 过"的结论记在本节** —— 它是唯一的机制独立证据。

### `chat.py` 现读数：**`b5b79dbb8ffa36bb`**（32296 B / 675 行）—— 快照目录里新出现的 `chat-b5b79dbb8ffa36bb.py.snap` 说明中间又过了一版。


### 认错（lead 纠正我 §5）：**`redcheck_delete.py` 里不存在两份模块对象**（`redcheck_delete.py` = `1b2bff62c9f49039`）
| 行 | 代码 | 含义 |
|---|---|---|
| **L48** | `chat = load(path, "chat_del_%d_%s_%s" % (site, mode, tag))` | **`chat` 这个名字被重绑到 `load()` 返回的模块** |
| L39 / L41 | `deleted` 模式 `path = variant(site)`；`base` 模式 `path = SRC` | **两条分支都只加载一个模块** |
⇒ **一个 arm = 一个模块对象 = 一个桶 ⇒ 覆盖不会发生。我的"两份模块对象"推断错在假设 `chat` 仍是原版。**
**⇒ 但那条限制作为设计规则仍有效（将来若一 arm 驱动两份副本）** —— **「现在不是活缺陷」与「规则无效」必须分开记。**

### lead 的 L86 / L102 发现我核实，且**全仓只有这两处**（已枚举 `skip_reason|not_applicable|covers|TODO` 等）
| 行 | 代码 |
|---|---|
| **L86** | `rec["skip_reason"] = "站点 1 走 cmd_chat；A/B 两条断言都在 cmd_m1 里 ⇒ 本 arm 不覆盖它们（不计入覆盖）"` |
| **L102** | `rec["assertions_status"] = "skipped"   # 站点 1 走 cmd_chat，A/B 不覆盖（见 skip_reason）` |
**⇒ 活代码里同形共 2 处，都在 `redcheck_delete.py`**（`run_site3.py` 无）。
> **凡把「当前为什么不需要」写成字符串常量，它会在需要的那一刻说谎。**
**⇒ 补充后果（lead 未提）**：站点 1 的断言落地后，**若那个 arm 不调 `_m4c_log`，盘上就没有 `asserts-<run_id>.json`** ⇒ L103 走 `log_missing` ⇒ **判 FAIL**。
**⇒ 这不是新缺陷，是 v5「无路径不记账 / 缺失判 FAIL」在正确施压**：**站点 1 必须真的产出断言，否则它自己就是红的。**

### L45 死代码确认
`redcheck_delete.py` **L45** `if os.path.exists(logp): os.unlink(logp)` —— **`logp` 由 L43 新 `run_id` 生成，文件永不预先存在** ⇒ **死代码**，无害；**若保留必须注明"冗余保险，不是必需"**。


### 核 lead 的 covers_observed 形态（声明 vs 观测）：方向对，但落地会崩两处

lead 的判法：covers_observed = sorted({a["site"] for a in assertions if a["status"] != "skipped"})
| # | 崩点 | 依据 |
|---|---|---|
| 1 | die 条目没有站点 —— chat.py L147 `_m4c_log({"id": "die", "status": "assertion_failed", "kind": "assertion", ...})` | site 只能是 None ⇒ `sorted({1, None})` 在 py3 抛 TypeError（NoneType 与 int 不可比） |
| 2 | control 模式必然 coverage_ok = False —— control 里 A/B 都记 skipped（chat.py L554 / L556）⇒ covers_observed = [] ≠ declared = [3] | 控制组跑得完全正确，产物却写着"覆盖不成立" ⇒ 又一次"绿被读成红" |
⇒ 修法：
| 崩点 | 修法 |
|---|---|
| 1 | covers_observed 取值前加 `if a.get("site") is not None` |
| 2 | 三值：coverage_ok = true / false / "not_applicable"（control 模式），并记 coverage_reason —— 不许把"不适用"写成 false |

### 更要紧：site 字段只能有一处作者，否则"声明对声明"只是换了层
若 id 与 site 都由人写（如 {"id": "site1.place", "site": 1}），两者可以不一致 ⇒ 又一对同层声明。
⇒ 要求：site 从 id 派生（id 形如 "site1.place" ⇒ site 由前缀得出），或只保留 id，covers_observed 从 id 前缀取值。
⇒ 一般化：**"用结果核对期望"要求结果里那个字段是唯一作者派生出来的；否则你只是把两个声明搬进了两个字段。**


### 两个活缺陷（sampled_at 06:36Z；`redcheck_delete.py` = `b291b3e937db6053`，`run_site3.py` = `23c876f8da33dd83`）

**缺陷 1：`covers_observed` 用 `a["site"]` 硬取键 ⇒ `die` 条目没有该键 ⇒ `KeyError` 崩掉红 arm**
| 文件 | 行 | 代码 |
|---|---|---|
| `redcheck_delete.py` | **L90** | `rec["covers_observed"] = sorted({a["site"] for a in (rec["assertions"] or [])` |
| `run_site3.py` | **L91** | 同样式（`log`） |
| `chat.py` | **L147** | `die` 条目 `{"id": "die", "status": "assertion_failed", "kind": "assertion", ...}` —— **无 `site` 键** |
⇒ **`a["site"]` 是硬下标，不是 `a.get("site")`** ⇒ 红 arm 一 die，日志里就有 `die` 条目 ⇒ **夹具自身 `KeyError` 崩** ⇒ **产物 MISSING** ⇒ **恰好崩在它要测的那一支。**
**⇒ 且它实现的还是 lead 已废止的版本（`site` 字段）** —— 新裁定是「`site` 整个删掉，`id` 唯一作者」⇒ **这两行要按 `id` 前缀派生重写，不是加 `.get`。**

**缺陷 2：`is_red` 从未被赋值 ⇒ 产物里恒为 `null`；而 `coverage_ok` / `assertions_status` 不进任何判定**
| 文件 | `is_red` 出现处 |
|---|---|
| `redcheck_delete.py` | **0 处**（该字段根本不存在） |
| `run_site3.py` | **仅 L50 初始化 `None`** + **L110 打印** ⇒ **无赋值** |
⇒ **产物会写 `"is_red": null`**；而 `null` 在任何下游 `if` 里都是**假** ⇒ **"没判成红"被读成"不是红"** ⇒ **第四次同形的假绿**。
⇒ **且 `coverage_ok`（L109/L93）、`assertions_status`（L99–107/L98–106）目前没有任何消费者** —— **字段在、判定不用它** ⇒ **这三者（含今晚新建的 `covers_*`）全是装饰。**
**⇒ 这正是四腿的第四腿**：**先枚举谁会读这个状态。现在没有任何人读它。**

### 顺序要求（新发现，必须排在批里）
**`coverage_ok` 进 `is_red` 之前，三值「`not_applicable`」必须先落地**，否则：
| 顺序 | 结果 |
|---|---|
| 先把 `coverage_ok` 接进 `is_red`，再补三值 | **所有 control arm 立刻变红**（`covers_observed=[] ≠ declared`） |
| 先三值，再接 `is_red` | control ⇒ `not_applicable` ⇒ 不进判定 ✓ |
**⇒ 依赖顺序：`id` 派生 → `covers_observed` → `coverage_ok` 三值 → `is_red` 消费它。** **四步不能换序。**


## 交付物：产物字段 → 消费者表（`run_site3.py` = `23c876f8da33dd83`，`redcheck_delete.py` = `b291b3e937db6053`）

**方法**：取两份夹具里所有 `rec["X"] = ...` 赋值（共 **24** 个字段），再逐字段扫其余出现处，按「是否进入 `if`/比较、是否只被 `print`、是否零出现」分类。

| 结论 | 字段 | 判定 |
|---|---|---|
| **零消费者** | `run.elapsed_s`@76 · `run.coverage_ok`@93 · `red.elapsed_s`@82 · `red.coverage_ok`@109 | **写完既不参与判定，也不被打印** ⇒ **死字段**（`elapsed_s` 连打印都没有） |
| **唯一消费者本身是死字段** | `run.covers_declared`→@93 · `run.covers_observed`→@91,@93 · `red.covers_declared`→@109 · `red.covers_observed`→@108,@109 | **整条 `covers_*` 链终止于 `coverage_ok`，而它零消费者** ⇒ **死胡同** |
| **不在"被赋值字段"里** | `is_red`（`run` L50 初始 `None`、L110 打印；`red` 零出现） | **从未赋值** ⇒ **缺陷 2 由上表独立复现** |
| **真正进入分支的** | `exit` · `die_kind` · `assertions`（只用于派生 `die_kind`） | **全仓只有这 3 个字段影响控制流** |
| **只被打印的** | `assertions_status`（run L110 打印 / red L114 打印） | **是日志，不是判据** ⇒ 按 lead 的规则须如此标注 |

### 由上表得到的硬结论
1. **24 个字段里，进入判定的只有 3 个；决定红绿的 0 个**（`is_red` 恒 `null`）；
2. **判据链只有一条**：日志文件 → `assertions` → `die_kind` → `assertions_status` → **打印** ⇒ **链尾是屏幕，不是返回值**；
3. **`covers_*` 四个字段 + `coverage_ok` 目前合计贡献 0 个判定** ⇒ **如果第 ④ 件不加 `is_red` 消费它，这五个字段就是今晚第 4–8 个装饰字段**；
4. **`elapsed_s` 是真死字段**（连打印都没有）—— 它甚至没资格被标成"日志"。


### 🚨 阻塞级：`finalize()` 在两份夹具里都**不可达**（`run_site3.py` = `183b4a4195e04c3e`，`redcheck_delete.py` = `8b5319f6102e5953`）
| 文件 | 行 | 代码 |
|---|---|---|
| `run_site3.py` | **L75** | `return rec` |
| `run_site3.py` | **L76** | `finalize(rec, logp, control, ["site3"])` ← **永远不执行** |
| `redcheck_delete.py` | **L75 / L76** | 同样两行，同样顺序 |
**⇒ `finalize()` 是 `is_red` / `covers_*` / `coverage_ok` / `assertions_status` 的唯一计算处，也是 lead 要求的"两条常驻 assert"（`run_site3.py` L73–74）的所在。**
**⇒ 它不执行 ⇒ 缺陷 2 的真正根因不是"忘了赋值"，是"赋值的地方取不到"。**
| 后果 | 说明 |
|---|---|
| `is_red` 恒 `null` | 由 `rec` 初值决定（L50），不是"未赋值" |
| **两条常驻 assert 是死的** | `run_site3.py` L73–74 永不执行 ⇒ **"常驻断言"变"死代码"** |
| `covers_*` / `coverage_ok` 根本不进产物 | L77–78 写的是**未 finalize 的 `rec`** |
**⇒ 若不先修顺序，本批 ①–⑤ 全部落地也看不见任何变化。**

### ⑤ 落地时的三条硬要求（我核出来的）
| # | 要求 | 依据 |
|---|---|---|
| 1 | **退出码判定必须在写盘之后**（`run_site3.py` L78 / `redcheck_delete.py` L78 的 `json.dump` 之前不许 `sys.exit`） | **否则判定不符 ⇒ 无产物 ⇒ 缺证判失败** |
| 2 | **`VERDICT MISMATCH` 不得与"判据红"共用退出码 1** | **它是夹具/前提错，不是被测代码错** ⇒ 同码会让"夹具错了"与"被测代码错了"无法分辨 ⇒ **报错口径必须与被判口径一致** |
| 3 | 无驱动脚本 ⇒ `sys.exit(1)` 不会跳过后一臂 ✓ | 已 grep：`kvmem` 下**零**处引用这两份夹具（`drivers: {}`），均手动运行 |


### 阻塞项已关闭（新读数：`run_site3.py` = `6123c0c5d713418a`，`redcheck_delete.py` = `a7e3a095905c414e`）
| 结构 | 行 | 状态 |
|---|---|---|
| `finalize(rec, logp, control, declared, expected_red)` | **L29–63** | **四步按序全在函数体内**：L36 `_site_of` 派生 → L37 `covers_observed` → L38–42 `coverage_ok` 三值 → L56 `is_red` 派生 |
| 两条常驻 assert | **L58 / L59–61** | **在 `finalize` 内且可达** ✓（第二条只在 `is_red` 为真时检查"红必须由断言造成"） |
| `verdict(rec)` | **L66–75** | `is_red != expected_red` ⇒ 1；`coverage_ok is False` ⇒ 1；否则 0 |
| 退出码位置 | **L149 `sys.exit(verdict(rec))`** | 在 L146 打印之后，写盘在更前 ⇒ **算 → 写盘 → 打印 → 退出码** ✓ |
| `_site_of` | **L23**，L36 用 `a.get("status") != "skipped"` + L37 过滤 `None` | **无 `KeyError`、无 `TypeError`** ✓ |
**⇒ 死区已消除；`is_red` 现在由唯一表达式派生且被 `assert isinstance(bool)` 守住。**

### 仍未落地（对照 lead 最新要求）
| 项 | 现状 |
|---|---|
| `harness_sha16` | **全文件零命中** ⇒ `STALE ∉ CURRENT` 尚未落地 |
| `finalized` / `asserts_ran` | **零命中** ⇒ 「链尾是否可达」仍不可观测 |
| 退出码 `5` | `verdict` **L70 / L74 都返回 `1`** ⇒ 夹具自检失败与判据红仍共码 |

### ⚠ 新引入的证据销毁路径（必须与 `finalized`/`asserts_ran` 同批解决）
**`finalize` 的两条 assert（L58 / L60）若触发，异常会穿出 `main` ⇒ 写盘（在 L146 之前）永不执行 ⇒ 无产物。**
**⇒ 于是"夹具自检失败"只留下 traceback，而台账/产物里什么都留不下** ⇒ **正是「失败会销毁自己的证据 ⇒ 缺证判失败」的现场**。
**⇒ 要求**：**`finalize` 与写盘包在同一个 `try/finally` 里** —— `finally` 里 `json.dump`，把 `asserts_ran` 的当前值、`finalize_error` 一起写进产物。
**⇒ 否则新加的守卫会把"守卫为什么响"这件事本身吃掉。**


### 我收回「已关闭」：`run_site3.py` = `6123c0c5d713418a` 记为**「结构层一致，待运行确认」**
**lead 的驳回成立**：我用"核了结构"作为关闭证据，**而上一轮的死区正是"结构看着对"的产物** ⇒ **同类证据不能用来宣布关闭同类缺陷。**
**⇒ 确认条件不变**：那一跑产物里出现 `finalized: true` + `asserts_ran: 2` + `harness_sha16` 等于当前 sha16，三件齐才记"已关闭"。
**⇒ 一般化（我的）**：**"我核过 X 了"必须先说明 X 属于哪一类证据（结构 / 运行 / 独立见证）。用结构证据宣布运行类缺陷关闭，是把方法用反。**

### 三条实现约束（lead 的 §4 形状里还没覆盖）
| # | 问题 | 依据（`run_site3.py` = `6123c0c5d713418a`） |
|---|---|---|
| 1 | **`verdict()` 必须先查仪器、再查被测对象** | L68 `rec["is_red"] != rec["expected_red"]` —— 若 `finalize` 在 L36/L42 之前抛，`is_red` 仍是 `None` ⇒ `None != expected` ⇒ **返回 1（判据红）**，而**实际是仪器坏了** ⇒ **归因错** |
| 2 | **`verdict()` 里的硬下标会二次抛** | L71 `rec["coverage_ok"] is False` —— `finalize` 若在 L42 前抛，该键不存在 ⇒ **`KeyError` 穿出 ⇒ 进程以 1 退出** ⇒ 与判据红撞码，`5` 一次用不上 |
| 3 | **`harness_sha16` 若无消费者，就是下一个装饰字段** | `kvmem` 下**零**处引用这两份夹具 ⇒ **没有"读取方"** ⇒ "读取方先比"这句话目前**没有执行者** |
**⇒ 修法**：
- **1+2**：`verdict()` 第一段查 `finalize_error` / `finalized` / `stale` ⇒ 返回 `5`；**第二段**才比较 `is_red`/`coverage_ok`，且一律用 `.get()` + 显式"缺失 ⇒ `not_finalized` ⇒ 5"；
- **3**：**让 `verdict()` 自己比 `harness_sha16`**（`rec.get("harness_sha16") != sha16(__file__)` ⇒ `stale` ⇒ 5）⇒ **字段当天就有消费者，不必等一个尚不存在的读取脚本**。
**⇒ 检查顺序决定归因**：**同一份产物，"先查仪器"报 5，"先查被测对象"报 1；顺序写反，仪器故障会以"被测对象坏了"的形式出现。**


### ⚠ `verdict_mismatch` 一名两用，且 §6 的归因有两处错（`run_site3.py` = `6123c0c5d713418a`）

**lead §6 的映射**：仪器（`stale`/`not_finalized`/`finalize_error`/`coverage_shape`/`verdict_mismatch` ⇒ **5**）→ 被测对象（`is_red != expected_red`、`coverage_ok is False` ⇒ **1**）。
**⇒ 两处归因我认为反了，理由如下表**：
| 工况 | `is_red` | 期望 | 真正含义 | 应报 | 若按 lead §6 报 |
|---|---|---|---|---|---|
| **base（未删行）** | `True` | `False` | **被测代码真的坏了**（行还在，断言响了） | **1** ✓ | 1 ✓ |
| **deleted（删了行）** | `False` | `True` | **删掉该行，断言却没响 ⇒ 判据没有判别力** | **5 / `no_discrimination`** | **1 ✗ 会报成"被测代码坏了"** |
**⇒ 第二行是本项目最重要的一次红**：它说明**站点 3 的断言是装饰**；把它报成 `1` 等于**说"代码坏了"，而事实是"仪器测不出坏"**。

**另一处**：`coverage_ok is False` ⇒ lead 归 `1`。**但 `coverage_ok` 说的是"这个 arm 有没有真的驱动它声明的站点"，与代码对错无关** ⇒ 覆盖不成立 ⇒ **这次运行对代码什么都没说** ⇒ **5 / `coverage_not_met`**。
> **一次运行若没有覆盖它声明的对象，它给出的"绿"和"红"都不作数 —— 那是仪器的结论，不是被测对象的状态。**

**⇒ 且 `verdict_mismatch` 一词现在指两件不同的事**：
| 名字 | lead 表里的含义 | 我上面那张表里的含义 |
|---|---|---|
| `verdict_mismatch` | 「判定口径与产物不符（夹具自检失败）」 | 「`is_red != expected_red`」 |
**⇒ 同一名两义 ⇒ 迟早有一个被写错。建议拆开：`verdict_mismatch` 只保留"夹具自检失败"，`is_red != expected_red` 按方向落 `1` 或 `no_discrimination`。**

### 修正后的 `instrument` 闭集（7 值，需 lead 裁定）
| 值 | 含义 | 码 |
|---|---|---|
| `stale` | `harness_sha16` 与当前夹具不符 | 5 |
| `not_finalized` | `finalized` 缺失或假 | 5 |
| `finalize_error` | 守卫触发（附 `asserts_ran` 与错误串） | 5 |
| `coverage_shape` | `coverage_ok` 缺失或不在三值内 | 5 |
| `verdict_mismatch` | 夹具自检失败（口径与产物不符） | 5 |
| **`no_discrimination`** | **deleted arm 断言没响 ⇒ 判据无判别力** | **5** |
| **`coverage_not_met`** | **`coverage_ok is False` ⇒ 本次运行不计入** | **5** |
**⇒ 闭集一旦定下就 7 值；此后出现第 8 种只能落 `coverage_shape`（= 未知），不得新增值。**


### 核 lead 的七层序：顺序对，但「取第一层」会丢信息

lead 的分层：① 身份（stale / verdict_mismatch）→ ② 生命周期（not_finalized / finalize_error）→ ③ 形状（coverage_shape）→ ④ 覆盖（coverage_not_met）→ ⑤ 判别力（no_discrimination）→ ⑥ 1 → ⑦ 0。
核实 ④ 先于 ⑤ 是对的：deleted arm 若 coverage 不成立，谈「判别力」没有依据 ⇒ ④ 必须先报。

但有一格会被这一层序吃掉：
| 工况 | 命中层 | 按层序报 | 被丢掉的信息 |
|---|---|---|---|
| base arm，coverage_ok is False 且 is_red == True | ④ + ⑥ | 5 coverage_not_met | 断言真的响了（可能来自另一站点）⇒ 一次真实红线被「覆盖不成立」盖住 |
⇒ 根因：七层序决定「退出码报哪一层」，但它同时成了「信息过滤器」。
⇒ 要求：退出码只取第一层；产物必须把「所有命中层」记成列表（如 instrument_hits: ["coverage_not_met"]），且 is_red 独立存在。
> 序用于归因，不用于丢弃。一个按优先级返回「最相关原因」的函数，必须同时返回被它盖住的原因。
⇒ 与今晚那条同族：状态若没有格子会落进最接近的格子；新变体是「状态若有两个格子，会被并成一个」。

### 表驱动测试的两条实现约束
| # | 约束 | 理由 |
|---|---|---|
| 1 | 测试必须 import 夹具里的 verdict()，不许复制一份 | 复制的那份是同源复制，改错一处两边一起错 |
| 2 | 每行断言三样：退出码 · instrument 值 · instrument_hits 是否包含全部命中层 | 只断言退出码，就测不出「信息被盖住」 |


### ⚠ 七值里有**一个值的产生规则至今不存在**：`verdict_mismatch`
**逐个对照可执行谓词**（其余六个都有）：
| 值 | 谓词 |
|---|---|
| `stale` | `rec["harness_sha16"] != sha16(__file__)` ✓ |
| `not_finalized` | `not rec.get("finalized")` ✓ |
| `finalize_error` | `"finalize_error" in rec` ✓ |
| `coverage_shape` | `rec.get("coverage_ok") not in (True, False, "not_applicable")` ✓ |
| `coverage_not_met` | `rec.get("coverage_ok") is False` ✓ |
| `no_discrimination` | `mode == "deleted" and rec["is_red"] is False` ✓ |
| **`verdict_mismatch`** | **「判定口径与产物不符」—— 没有可执行谓词** |
**⇒ 一个没有产生规则的枚举值只有两种命运**：**永不发出（死值）**，或**变成 `else` 分支的垃圾桶（第二个"最接近的格子"）**。**两者都比它不存在更糟。**

**⇒ 两个出路，我推荐第二个**：
| 方案 | 内容 | 后果 |
|---|---|---|
| A | 给它真谓词：`expected_red != (mode == "deleted")`（吊具自己把期望写反） | **能真的发出来** ✓ 但**它检查的是"两份副本是否一致"** |
| **B（推荐）** | **`expected_red` 由 `mode` 派生，不传参** ⇒ 不一致在构造上不可能 ⇒ **该值删除，闭集 7 → 6** | **"检查两份是否一致"降级为"只有一份"** ✓ |
**⇒ 理由与我们今晚清 `clear()` 同一条**：**能派生的不要声明；能构造上排除的不要运行期检查。**
**⇒ 且 B 让不变式更好写**：六值全部是可执行谓词，`instrument_hits` 的闭集也就真正闭合。

### 补一条与 lead 不变的式配对的：`is_red` 为 `None` 只能出现在仪器有命中的时候
| 不变式 | 含义 |
|---|---|
| lead 的：`instrument_hits` 非空 ⟺ 码 5 | 仪器有话说 ⇒ 必须能指出哪一层 |
| **我补的**：**`is_red is None` ⇒ `instrument_hits` 非空** | **`null` 不许在"仪器一切正常"的产品里出现** —— 否则我们今晚刚清掉的 `is_red: null` 会以"捕获路径"的名义合法回来 |
**⇒ 两条合起来把产物钉成四格**：
| `is_red` | `hits` | 含义 |
|---|---|---|
| `True`/`False` | 空 | 仪器正常，结论有效 |
| `True`/`False` | 非空 | 仪器有话说，但**结论仍记录**（正交） |
| `None` | **必须非空** | 仪器没跑完 ⇒ 不许声称有结论 |
| `None` | 空 | **禁止** ⇒ 判 `5 / finalize_error` 并记 `invariant_violated` |


### 🚨 `_hits` / `verdict` **各定义两次**（`run_site3.py` = `e88650323226948c` / 241 行；`redcheck_delete.py` = `a2c31f29cb1fe6b8` / 251 行）
| 函数 | 第一次定义 | 第二次定义 | 生效者 |
|---|---|---|---|
| `_hits` | **L73** `(rec, expect_red)` | **L117** `(rec, mode_expected_red)` | **L117** |
| `verdict` | **L98** `(rec, expect_red)` | **L138** `(rec, mode_expected_red)` | **L138** |
| 调用点 | —— | **L236**（run）/ **L246**（red）`sys.exit(verdict(rec, ...))` | 解析到 **L138** |
**⇒ Python 取最后一次定义 ⇒ L73–L115 共 43 行是死代码**，且**它与生效版谓词不同**：
| 行 | 死版（L91） | 生效版 |
|---|---|---|
| `no_discrimination` 谓词 | `expect_red and rec.get("is_red") is not True` | `rec.get("expected_red") is True and rec.get("is_red") is not True` |
**⇒ 同一名字两份实现、语义由文本顺序决定 ⇒ 这是"一个字段两个作者"的函数级版本，而 Python 静默接受 ⇒ 只有运行才能暴露，且两份行为相近时永远暴露不了。**

**⚠ 更要紧**：**死的那一份（L73–L115）正是 lead §5 定稿的形状**（含 `elif` 分支、含 `expect_red` 入参、含那段写得很全的 docstring）⇒ **审的是不执行的那份。**

### 第三处作者：`redcheck_delete.py` **L246 `verdict(rec, False)`**
**期望值被硬编码为 `False`** ⇒ 与 `rec["expected_red"]`（L65 已存一次）、与 `mode` 三者并存 ⇒ **第三个作者**；**且 deleted arm 若断言真响，会被 `is_red is True and not expect_red` 判成 `1`（被测对象坏了）** ⇒ 又一次把"仪器/期望"错误记到被测对象账上。
**⇒ 要求**：**删掉 L73–L115 任一份（保留唯一实现）；`expect_red` 从参数表移除，`verdict` 只读 `rec["expected_red"]`。**


### 核 lead 的 `co_firstlineno` 见证（⑬）：**机制对，但有两个会让它误报的坑**

**为什么它对**：`co_firstlineno` 读的是**绑定**（哪个 `def` 编译出的 code object 现在是这个名字的值），不是文本 ⇒ **正是"定义层级的独立见证"** ✓

| # | 坑 | 依据 |
|---|---|---|
| 1 | **`def_lines` 只能装夹具自身的函数** | 夹具通过 `load()` 加载**变体**（`tmp/variants/*.py.snap`）——若把 `chat.py` 侧的函数也记进去，行号属于**变体文件**，与 `tools/chat.py` 比对必错 |
| 2 | **装饰器会改变 `co_firstlineno`** | 若将来给 `verdict` 加计时/日志装饰器，`co_firstlineno` 指向 wrapper ⇒ **误报 `def_mismatch`** ⇒ 要么禁止装饰，要么同时记 `__wrapped__.__code__.co_firstlineno` |

### 坑 1 现在不触发，但**它与"横幅"那条决定互相牵制**
`variant()` 是**就地替换**：`run_site3.py` L23 `lines[i] = removed.split("leases.reset")[0] + "pass  # M4C-DELETED-SITE-3"`，`redcheck_delete.py` L23 同形
**⇒ 变体的行数与原文一致 ⇒ 行号可比 ⇒ 坑 1 当前不触发 ✓**
**⇒ 但只要有人允许"在变体头部插一行横幅"，`co_firstlineno` 立即整体 +1 ⇒ `def_mismatch` 会对一次合法运行误报。**
**⇒ 因此拒绝横幅现在有第二个理由（比我的行号偏移理由更强）**：**它是"行号可作身份"这一整类见证的前提。**
**⇒ 一般化：凡把"行号"用作身份（`deleted_line_no`、`def_lines`），就必须禁止任何插行式改动；"就地替换"不是一个风格，是一个不变式。**


### 核 lead 的 `def_fp` 三元组（⑭）：三分量都成立，**但"记哪三个函数"本身是一份要记得的清单**

| 分量 | 它真的能抓到 | 备注 |
|---|---|---|
| `co_filename` | **变体 vs 原文** | 即便以 `__main__` 运行，`basename` 仍是夹具名 ⇒ 稳定 ✓ |
| `co_firstlineno` | **重复定义**（今晚 `_hits` L73/L117、`verdict` L98/L138） | ✓ |
| `co_name` | **装饰器化** | **`functools.wraps` 只改 `__name__`，不改 `co_name`** ⇒ 装饰后仍能被抓到 ✓ **比记 `__wrapped__` 更硬** |

### ⚠ 但 `def_fp(verdict)` / `def_fp(_hits)` / `def_fp(finalize)` 是一份**人工清单**
**明天有人加一个 `main` 的重复定义、或 `variant` 被覆盖，清单里没有它 ⇒ 不会被看见。**
**⇒ 清单本身就是"要记得"，正是今晚清掉的那类东西。**
**⇒ 改法（结构性，无清单）**：
```
import inspect
rec["def_fp"] = {n: def_fp(o) for n, o in list(globals().items())
                 if inspect.isfunction(o) and o.__module__ == __name__}
```
**⇒ 于是"记哪些函数"不再由人决定** —— 文件里有几个顶层函数，产物里就有几条指纹。
**⇒ 且它顺手记录"文件里究竟有几个函数"**：数量变了本身就是一条可比的读数。

### 顺带一条（低价值但会误导人）：源与变体的 `sha16` 不可用于"只差一行"的判断
`variant()` 读源时走文本模式（通用换行）⇒ CRLF 被归一成 `\n`；写出时 `newline=""` ⇒ **变体是 LF，源是 CRLF** ⇒ **两者 sha 差异里混着换行风格差异**。
**⇒ `variant_sha16` 只能当身份用，不能当"只删了一行"的证据。** **行数相等那条断言（⑮）才是那个证据。**


### 🚨 `ast.walk` 会把**嵌套函数**算进去 ⇒ `set(def_source_count) == set(def_fp)` 必然不等 ⇒ 假红
**`globals()` 只含顶层绑定，`ast.walk` 含嵌套 `def`。** 两份夹具都有嵌套：
| 文件 | 嵌套 `def`（缩进 4） | 行 |
|---|---|---|
| `run_site3.py` | `fixed_selection`（在 `fixed_selection_factory` 内） | **L80** |
| `run_site3.py` | `seqs_of`（在 `main` 内） | **L137** |
| `redcheck_delete.py` | `fixed_selection` | **L80** |
| `redcheck_delete.py` | `traced_load` | **L127** |
**⇒ 键集差集恰好等于这些嵌套名 ⇒ lead §2 的判据 `set(def_source_count) == set(def_fp)` 会在一份完全正确的文件上报警。**
**⇒ 修法**：只数**顶层**定义
```
defs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
```
**⇒ 若还想看嵌套，另记一个键（如 `nested_def_names`），不要混进同一个判据** —— **判据一旦混入两类对象，它的"不等"就再也说不清是哪一类。**

### ⚠ 且 `def_mismatch` 现在聚合了三个谓词 ⇒ 又一次"两个格子被并成一个"
| 谓词 | 发现的问题 |
|---|---|
| `def_source_count[n] > 1` | **重复定义**（43 行死代码） |
| `set(def_source_count) != set(def_fp)` | **文本有、绑定无**（影子定义） |
| `def_fp[n] != 期望` | **装饰器化 / 变体文件 / 行号漂移** |
**⇒ 三者都落 `def_mismatch` ⇒ 看到它只知道"定义层有问题"，不知道是哪一种。**
**⇒ 要求（与 lead 自己的规矩一致）**：**值保持闭集，另加细分字段** `def_mismatch_detail`（例如 `["_hits:source_count=2"]`、`["main:fp=tmp/variants/...:80"]`）。
**⇒ 判据**：**`def_mismatch` 命中而 `def_mismatch_detail` 为空 ⇒ 本身判 `self_contradiction`** —— **一个"有话说但说不出内容"的仪器值，与死值等价。**


### 核 lead 的 `m4c_selfcheck.py` 四步（⑳）：**step1 与"毫秒级、不碰 GPU"自相矛盾**

**两份夹具的 `step1`（未改动夹具跑一次）会真的加载引擎**：`run_site3.py` `main()` 里 `chat.cmd_m1()`、`redcheck_delete.py` `main()` 里 `chat.cmd_chat(...)` + `chat.cmd_m1()` ⇒ **要读模型、要 GPU、按分钟计。**
| 步 | lead 的定位 | 真实成本 |
|---|---|---|
| step1 跑夹具 | **"毫秒级、不碰 GPU"** | **分钟级、要 GPU** |
| step2 改错一格再跑 | 同上 | **分钟级、要 GPU，且会临时改动源文件** |
| step3 `def_source_count` 全 1 | 静态 | 毫秒 ✓ |
| step4 `def_fp.co_filename` | 静态/运行期 | 毫秒 ✓ |
**⇒ 四步被塞进一个入口 ⇒ 入口的实际耗时由其最慢者决定 ⇒ "每次改完都能跑"的前提消失，而"能随时跑"正是 selfcheck 存在的理由。**

### ⇒ 建议拆成两道闸（保留 lead 的全部判据，只改承载力）
| 闸 | 内容 | 成本 | 触发时机 |
|---|---|---|
| **快闸 `m4c_selfcheck.py`** | **step2′ 合成 `rec` 喂 `verdict()`（九格表）· step3 · step4** | **毫秒，无引擎** | **每次改完都跑** |
| **慢闸（夹具本身那一跑）** | step1：产物必须 `finalized` · `asserts_ran==2` · `harness_sha16` 相符 · `hits==[]` · `exit==0` | 分钟 | 每次改动夹具后 |
**⇒ 且快闸必须能读「最近一份产物」并复核它** ⇒ **慢闸的产物由快闸验收，两者仍然连通，不必合体。**

### ⚠ 而 `step2` 必须是"喂合成 `rec`"，不能是"改源文件再跑"
| 理由 | 说明 |
|---|---|
| **会污染仓库** | 改错一格 → 跑 → 改回：中途任何异常都会把源文件留在错状态，而**这类残留最像源码**（今晚 `tmp/` 那堆化石的教训） |
| **不需要引擎** | `verdict()` 已是全函数、纯归因，**喂一个 dict 就能验九格** |
| **更严格** | 改源文件只能验"某一格"，喂 `rec` 能验**九格全部**（含那格正交行与 `0` 行） |


### 🚨 提取 `m4c_verdict.py` 会让 `harness_sha16` **每跑必假红**：`__file__` 的语义变了
**当前两份夹具里写的是** `sha16(os.path.abspath(__file__))`（`_hits` 第一行）——此时 `__file__` 就是夹具自身 ✓
**⇒ 一旦 `_hits` 搬进 `m4c_verdict.py`，`__file__` 就在那个模块里求值 ⇒ 得到 `m4c_verdict.py` 的 sha**
**⇒ 而 `rec["harness_sha16"]` 存的是夹具的 sha ⇒ 两者永不相等 ⇒ 每次运行都 `stale` ⇒ 码 5 ⇒ 仪器对一切正确运行喊错。**
| 修法 | 说明 |
|---|---|
| **`sys.modules["__main__"].__file__`** | 夹具是**以脚本方式运行**的 ⇒ `__main__` 就是夹具 ✓ 零参数 ✓ |
| 或把 `harness_file` 作显式入参 | 也不违背"唯一作者"（作者仍是夹具） |
**⇒ 这是今晚第三次"搬动代码改变了语义"**（`return` 之后的死区、重复定义覆盖、现在是 `__file__` 重绑定）；**三次都是 Python 静默接受。**
**⇒ 判法**：**搬家时逐个问"这一行读的每个隐式名字，搬家后还指同一个东西吗"** —— `__file__` / `__name__` / `__package__` / 闭包变量 / 全局常量，**全都是随位置变的隐式输入。**

### 而 `sha16` 是同一批里的**第三处重复定义**，搬的时候要一起搬
**两份夹具各有一个 `def sha16(p)`（都在 L12）** ⇒ **提取 `m4c_verdict.py` 时若只搬 `_hits`/`verdict`/`def_fp`，`sha16` 仍是两份** ⇒ **"只剩一个作者"这句话不成立。**
**⇒ 要求**：`sha16` 一并搬入（或单独 `m4c_util.py`），两份夹具改为 import。

### ⚠ `mode` 词表：两份夹具不同（`red`/`green` vs `base`/`deleted`），派生函数必须显式认识它们
**若 `m4c_verdict` 里写 `expected_red = (mode == "deleted")`** ⇒ `run_site3.py` 的 `red` 永远派生成 `False` ⇒ **红臂恒判绿**（今晚那一族的原样重演）。
**⇒ 要求**：**共享模块里放显式闭集** `RED_MODES = {"deleted", "red"}` / `GREEN_MODES = {"base", "green"}`；
**⇒ 且 `mode` 不在其中任一时，必须显式命中一格仪器值（如 `mode_unknown`）** —— **不许默认成 `False`。**
**⇒ 否则一个拼错的 `mode` 会被安静地读成"期望绿" ⇒ 红臂全绿、绿臂全绿、整张表废掉。**


### 复核 lead 六条（新读数，四文件 mtime 均为 06:46:56，最后一产物 06:43:23 ⇒ 仍从未运行）
| 文件 | sha16 | 行 |
|---|---|---|
| `m4c_verdict.py` | **`f30d8a5d432310c2`** | 101 |
| `m4c_harness.py` | **`25a7536c1643fd3e`** | 94 |
| `run_site3.py` | **`5ae4687c457c1970`** | 93 |
| `redcheck_delete.py` | **`017c0d79643267ec`** | 97 |
| lead 六条 | 现状 |
|---|---|
| ① `H.sha16` 不存在 | **已修**：`m4c_harness.py` L10 `sha16 = V.sha16` ✓ |
| ② `asserts_ran` 恒 2 / 两条 assert 消失 | **半修**：两条 assert 已回（L59 / L62），记账改在 assert 之前（L58 / L61）—— **但见下面 A，绿臂恒为 1** |
| ③ `harness_id` 不含夹具 | **已修**：L13–16 三段 `夹具:本文件:归因层` ✓ |
| ④ `finalized` 由缺失派生 | **已修**：L64 `finalize_completed = True` 末行盖章，L85 `finalized = ... is True` ✓ |
| ⑤ `mode_unknown` 缺 | **已修**：`run_site3.py` L37 / `redcheck_delete.py` L39 闭集 + 入 `rec`（L50 / L52）✓ |
| ⑥ 摘要漏键 | **已修**：L89–92 含 `finalize_error` / `def_mismatch` / `mode_unknown` ✓ |

### 🚨 A（新缺陷，由 ② 的修法引入）：绿臂 `asserts_ran == 1`，而验收要求 2
`m4c_harness.py` L58 `+= 1` → L59 第一条 assert；**L60 `if rec["is_red"]:` → L61 `+= 1` → L62 第二条 assert**
**⇒ base/green 臂 `is_red` 为 `False` ⇒ 第二条 assert 与它的 `+= 1` 都不执行 ⇒ `asserts_ran == 1`。**
**⇒ 而慢闸验收要求 `asserts_ran == 2` ⇒ 主路径（绿臂）永远达不到 ⇒ 假红。**
**⇒ 更糟：按 lead 那四行表，`asserts_ran == 1` + 无 `finalize_error` 是"不在表内"的状态** ⇒ 又一次"状态没有格子"。
**⇒ 修法（一行）**：把条件守卫改成恒执行的断言
`rec["asserts_ran"] += 1; assert (not rec["is_red"]) or any(a.get("status") == "assertion_failed" for a in log), "红必须由断言造成"`
**⇒ 于是两条 assert 在所有完成路径上都执行 ⇒ `asserts_ran == 2` 恒成立；"红必须由断言造成"在 `is_red` 为假时自动为真。**

### 🚨 B：`stale` 谓词在进程内**恒假**
`m4c_verdict.py` L63 `if rec.get("harness_sha16") != rec.get("harness_sha16_now")`
**而 `harness_sha16` 在 `run_main` L70 由 `harness_id(fixture_file)` 写入；`harness_sha16_now` 在 `verdict` L88 由**同一个函数、同一个入参**再算一次** ⇒ 同一次运行里两次求值 ⇒ **永远相等**。
**⇒ `stale` 在本进程内不可能命中 ⇒ 身份装置目前没有消费者**（除非读的是**旧产物**）。
**⇒ 修法**：`stale` 属"读旧产物"那一侧 —— 快闸读 `out/*.json`，用 `harness_id` 现算值与该产物里的 `harness_sha16` 比对 ⇒ 不符即 `stale`。**夹具自己判不了自己是否陈旧。**

### 🚨 C：保护带仍起于 `try` 之前（lead 原则①未落地）
`m4c_harness.py` **L70–L77 在 L78 `try:` 之外**：`harness_id`（读三个文件）、`def_inventory`（`ast.parse` + 读文件）、`def_mismatch_detail` —— **任一抛出 ⇒ 无产物**。
**⇒ 正是 lead 上一轮那句「放在 `run_main` 里的 `finally`，保护不了 `run_main` 之前的那一行」的原样残留。**

### 🚨 D：`def_mismatch_detail` 只实现了三谓词中的**一个**
`m4c_verdict.py` L40–46 只做 `top` 计数 > 1；**「键集不等（文本有、绑定无）」与「`def_fp` 文件名不符（拷贝粘回夹具）」都没有代码**。
**⇒ ⑯ 验收里「两个 dict 键集相同」这一条，目前没有任何实现在判它。**

### 🚨 E：`redcheck_delete.py` L48 —— 一行注释吞掉了一个字段
`"expected_red": False,   # 站点 1/4 期望"删了也不红"（冗余） "run_id": run_id,`
**`#` 之后全是注释 ⇒ `"run_id": run_id` 从未进入 `rec` ⇒ 产物里没有 `run_id`。**
**⇒ 而没人报错，因为 `run_id` 没有消费者 ⇒ 这正是「无消费者的字段等同不存在」的现场样本：删掉它，只有对照源码才看得见。**
**⇒ 反过来说：若它有一个消费者，这里会当场 `KeyError`。** **字段无人读，缺陷就不会显形。**

### 小：两处 docstring 与实际不符
| 位置 | 写的是 | 实际 |
|---|---|---|
| `run_site3.py` L5 / `redcheck_delete.py` L4 | 「判定与退出码在 `m4c_harness.verdict()`」 | `verdict` 在 `m4c_verdict.py`；`m4c_harness.py` L4 自己声明「不定义第二份 verdict」 |
| `m4c_verdict.py` L57 | 「八值闭集」 | `LAYERS` 有 **9** 个值 |


### 核 lead 的 `asserts_declared`（ast 派生门槛）：方向对，但**四个洞，其中一个让它没有退出码**

| # | 洞 | 依据 |
|---|---|---|
| 1 | **`ast.walk(tree)` + `n.name == fn.__name__` + `[0]` 取的是"第一个"同名定义** | 今晚 `finalize` 只有一份，但 `_hits`/`verdict` 曾各两份。**若 `finalize` 被重复粘贴，`[0]` 数的是死副本的 assert 数 ⇒ 门槛在正确的方向上失明** |
| 2 | **`ast.walk(fn_node)` 会数进嵌套 `def` 与条件块里的 `Assert`** | `finalize` 现在没有嵌套函数，但 `if` 里的 assert 会被数进"应执行数"，而它可能不执行 ⇒ **假红** |
| 3 | **`asserts_ran == asserts_declared` 这一条判据目前没有落进 `instrument_hits`** | `m4c_verdict.py` L56–80 只读 `mode_unknown`/`def_mismatch`/`harness_sha16`/`finalized`/`finalize_error`/`coverage_ok`/`expected_red`/`is_red`，**零处读 `asserts_ran`** |
| 4 | **`declared == 0` 会通过** | `0 == 0` ⇒ **把 `finalize` 里的 assert 全删光 ⇒ 绿** |

**⇒ 洞 3 最重**：**新门槛若只写成"验收时人读一遍产物"，它就是报告，不是门禁** —— 正是今晚那条「判据链的终点必须是退出码或门禁」的又一次现场。
**⇒ 要求**：**新增 `asserts_short` 进 `LAYERS`**，谓词
`if not rec.get("asserts_declared") or rec.get("asserts_ran") != rec.get("asserts_declared"): hits.append("asserts_short")`
**⇒ 它一次盖住洞 3 与洞 4**：缺失（`None`）比不进 ⇒ 命中；`declared == 0` ⇒ 命中。

### 洞 1、2 的一行修法
```
nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn.__name__]
if len(nodes) != 1:      # 重复定义 ⇒ 送的必须是"唯一"这个结论，而不是随便挑一份
    return None
return len([s for s in nodes[0].body if isinstance(s, ast.Assert)])   # 只数函数体直属语句
```
**⇒ 返回 `None` 会让 `asserts_short` 命中** ⇒ **"数不出来"落进"仪器坏了"，而不是落进"通过"。**

### 另：`asserts_declared` 本身也是一次读文件（`inspect.getsourcefile` + `open`）
**按 lead 自己的原则②它必须进 `try`**，且它的失败要被 `asserts_short` 兜住 —— 否则"门槛的输入没算出来"会变成 `finalize_error`，而 `finalize_error` 说的是"没跑完"，**两者不是同一件事**。
**⇒ 建议**：把它放在 `try` 内、`def_inventory` 之后，失败即 `asserts_declared = None`（自身再包一层 `try/except`），**不让它连累 `drive`**。


### 🚨 跑批之前先核调用点：签名对得上 ✓，但 `control` **从未被传 `True`** ⇒ 站点 1 必然 `coverage_not_met`
| 检查 | 结果 |
|---|---|
| `run_site3.py` L86 | `H.run_main(rec, out, logp, drive, os.path.abspath(__file__))` ✓ 与 `m4c_harness.py` L80 签名一致 |
| `redcheck_delete.py` L90 | 同上 ✓ |
| 夹具内直调 `H.finalize` | **零处** ✓（只有 `m4c_harness.py` L92 自己调） |

**但**：`run_main(..., control=False)` 默认，**两份夹具都不传** ⇒ `finalize(..., control=False)` ⇒ `coverage_ok` 走"比较"分支。
**而 `redcheck_delete.py` L70–72 站点 1 臂是**：
```
if site == 1:
    chat.QUESTIONS = []
    chat.cmd_chat(control=True)
```
**⇒ A/B 在日志里记 `skipped` ⇒ `site_of` 返回 `None` ⇒ 被 L36 过滤 ⇒ `covers_observed = []`**
**⇒ `covers_declared = ["site1"]` ⇒ `coverage_ok = False` ⇒ `coverage_not_met` ⇒ 码 5。**
**⇒ 即：站点 1 每一次运行都会以"覆盖不成立"报 5，而真正的意思是"这个 arm 的断言被 skip 了"。**
**⇒ 修法（一处）**：`redcheck_delete.py` L90 传 `control=(site == 1)`。
**⇒ 否则 lead 下一步（站点 1 base/deleted）会当场失败，而失败信息会把人引向"站点 1 没被覆盖"，那是错的 —— 是"覆盖不适用"。**
**⇒ 这条正好是今晚那条的第三次现场**：**一个状态有格子（`not_applicable`），但通向它的路没接** ⇒ 该状态表现为"最近的那个格子"（`coverage_not_met`）。

### 小：`inspect.getsourcefile(fn)` 可换成 `fn.__code__.co_filename`
**`def_fp` 已经用 `co_filename` 记身份**；`asserts_declared` 再用 `inspect.getsourcefile` ⇒ **同一个量两条取法**，且 `getsourcefile` 对无源对象会抛 `TypeError`。
**⇒ 用 `co_filename` 能让"身份"与"读哪份源"来自同一个字段** —— 一处改动，两个用途。


### 用 lead 自己刚立的那条规矩（默认值死分支）扫一遍剩下的形参 —— 命中一处
| 形参 | 默认值 | 传非默认值的调用点 | 判定 |
|---|---|---|---|
| `run_main(..., control=False)` | `False` | 0（两处都不传） | **⑤ 会删掉这个形参** ✓ |
| **`finalize(rec, logp, declared, control=False)`** | `False` | **0**（唯一调用者是 `m4c_harness.py` L92，传的是 `run_main` 局部变量） | **死分支：⑤ 之后默认值永不生效 ⇒ 应删默认值或删该形参** |
| `harness_id(fixture_file)` / `load(path, name)` / `verdict(rec, harness_id)` | 无默认 | — | ✓ |
**⇒ `finalize` 的 `control` 形参本身也是多余的**：**它可以从 `rec["control"]` 读 —— 与 ⑤ 对 `run_main` 的处理同一条理由。**
**⇒ 若不删，本批会在同一件事上留下两代写法：`run_main` 已改成读 `rec`，而 `finalize` 仍靠传参。**

### ⚠ ⑤ 的遗漏面：`run_site3.py` 也必须显式写 `rec["control"] = False`
**若只有 `redcheck_delete.py` 写 `rec["control"]`，`run_site3.py` 里 `rec.get("control")` 就是 `None`。**
**⇒ `None` 在 `if` 里当 `False` 用 ⇒ 行为"看起来对"，而它是「没人告诉我」冒充「不是控制臂」。**
**⇒ 这正是今晚第五类假绿的形状**（`is_red: null` / `getattr(...,[])` / `0 == 0` 同族）：**缺失被读成一个合法值。**
**⇒ 要求**：**两份夹具在 `rec` 构造处各写一次 `control`（`False` / `(site == 1)`）**，谁都不许省。

### 并用现有格子把它挡住（不新增枚举值）
```
if not isinstance(rec.get("control"), bool):
    hits.append("coverage_shape")      # 控制臂标记不是一个确定的值 ⇒ 覆盖三值判定不可信
```
**⇒ 复用 `coverage_shape` 是合适的**：**它管的就是"`coverage_ok` 这个三值字段的输入是否成形"，而 `control` 正是那个输入。**
**⇒ 于是"忘了写 `control`"从静默变成码 5，且不必动 `LAYERS`。**


### 🚨 ⑥ 第二跑按当前形状拿不到 `exit == 5`：它会以 `exit 1` + traceback 结束
**注入 `fixture_file` 指不存在路径时，`harness_id` 被调用两次，而只有第一次在保护带内**：
| 行 | 调用 | 在 `try` 内吗 |
|---|---|---|
| `m4c_harness.py` **L70** | `rec["harness_sha16"] = harness_id(fixture_file)` | **是**（③ 之后） |
| `m4c_harness.py` **L93** | `return V.verdict(rec, harness_id(fixture_file))` | **否** —— 在 `finally` 之后 |
**⇒ L70 抛出 ⇒ `finalize_error` 记下 ⇒ `finally` 落盘 ⇒ 产物有了 ✓**
**⇒ 但接着 L93 再调一次 `harness_id` ⇒ 同一个 `FileNotFoundError` ⇒ 在 `verdict` 之前穿出 ⇒ 进程以 1 结束，只剩 traceback。**
**⇒ 于是 `instrument_hits` 根本没被算 ⇒ 产物里 `instrument`/`instrument_hits` 缺失，而退出码是 1（"被测对象坏了"）。**
**⇒ 而这正是 ③ 要治的那个病，只高了一层：读文件的调用出现在保护带之外。**

### 修法：身份只算一次，算在带内，之后从 `rec` 读
```
try:
    rec["harness_sha16_now"] = harness_id(fixture_file)   # 唯一一次现算，在带内
    rec["harness_sha16"]     = rec["harness_sha16_now"]
    ... def_inventory / def_mismatch_detail / drive / finalize ...
finally:
    ... json.dump ...
return V.verdict(rec)          # 不再现算，也就不可能再抛
```
**⇒ 且这让 `harness_sha16 == harness_sha16_now` 在带内恒真 —— 而 `stale` 本来就该死（我们已记账：`stale` 属快闸侧）。**
**⇒ 注入验收因此变成可判：产物在 · `finalize_error` 有值 · `instrument == "finalize_error"` · `exit == 5`。**

### 并建议把 ⑥ 第二跑的期望写严一格
| 项 | 期望 |
|---|---|
| 产物存在 | **是**（这一条是 ③ 的全部意义） |
| `harness_sha16` 与 `harness_sha16_now` 双双缺失 | **是**（L70 就抛了） |
| `finalize_error` | 非空 |
| `instrument` | **`"finalize_error"`**（不是"有命中即可"） |
| `asserts_ran` / `asserts_declared` | `0` / 缺失或 `2` —— **两者都说明"没跑到 assert"** |
| `exit` | **5** |
**⇒ `instrument` 写严是必要的**：**注入只该命中一格；若它同时命中两格而报出别的那格，说明层序或谓词有错。**


### 🚨 ⑥ 跑二第 ②③ 两条按当前代码**不可满足**（实测 Python 3.12.14）

**② `instrument == "finalize_error"` 不可达**：`m4c_verdict.py` L10–11 的 `LAYERS` 顺序是
`("mode_unknown", "def_mismatch", "stale", **"not_finalized"**, **"finalize_error"**, "coverage_shape", ...)`
**⇒ 注入时 `finalized` 为 False ⇒ `not_finalized` 与 `finalize_error` 同时命中 ⇒ `hits[0]` 是 `not_finalized`。**
**⇒ 即"有产物、exit 5、但那格报的是 no_finalized 而不是 finalize_error"。**
**⇒ 修法（顺带修一条层序）**：**把 `finalize_error` 排在 `not_finalized` 之前** —— **异常是"因"，"没跑完"是"果"；有因时报因。**
  - 无异常而未完成（例如死区早返回）⇒ `finalize_error` 不命中 ⇒ 仍报 `not_finalized` ✓ 不损失判别力
  - 有异常 ⇒ 报 `finalize_error`，与"为什么没跑完"直接对上 ✓

**③ `finalize_error` 含路径串 —— 用 `repr(exc)` 做不到（实测）**：
| 表达式 | 结果（Python 3.12.14，`open("/…/nope_missing.py","rb")`） | 含路径 |
|---|---|---|
| `repr(exc)` | `FileNotFoundError(2, 'No such file or directory')` | **False** |
| `str(exc)` | `[Errno 2] No such file or directory: 'D:/…/nope_missing.py'` | **True** |
| `type(exc).__name__` | `FileNotFoundError` | — |
**⇒ `m4c_harness.py` L82 `rec["finalize_error"] = repr(exc)` 拿不到路径 ⇒ ③ 永远失败。**
**⇒ 修法**：`rec["finalize_error"] = "%s: %s" % (type(exc).__name__, exc)` ⇒ 类型名与路径都在。
**⇒ 一般化**：**`repr` 是给调试器看的，`str` 是给人看的；要"这次错是不是那个错"，必须用能携带上下文的那一个。**


### 十值两两蕴含顺查（按 lead 要求；谓词取自代码设计，非猜测）
**谓词（缩写）**：M=`mode_unknown` · D=`def_mismatch` · S=`harness_sha16 != now` · NF=`not finalized` · FE=`finalize_error` 非空 · CS=`coverage_ok` 不在三值内 ∨ `control` 非 bool · AS=`not asserts_declared ∨ asserts_ran != asserts_declared` · CN=`coverage_ok is False` · ND=`expected_red is True ∧ is_red is not True` · SC=`is_red is None ∧ hits 空` ∨ (`D ∧ detail 空`)

| 蕴含 | 是否恒成立 | 依据 | 顺序要求 | 现状 |
|---|---|---|---|---|
| **FE ⇒ NF** | **恒成立** | `finalize_completed` 只在 `finalize` 末行置位；`except` 分支意味着它没置 ⇒ `finalized` False | **FE 在 NF 前** | **✗ 违规（本批修）** |
| **NF ⇒ CS** | **恒成立** | `finalize` 未跑 ⇒ `coverage_ok` 键不存在 ⇒ `None not in (True,False,"not_applicable")` | NF 在 CS 前 | ✓ |
| **NF ⇒ AS** | **恒成立** | `asserts_ran` 停在 `run_main` 置的 `0`；`asserts_declared` 为 `2` 或缺失 ⇒ `0 != 2` 或 `not None` | NF 在 AS 前 | ✓ |
| **FE ⇒ CS** | 恒成立（经 NF） | 同上 | FE 在 CS 前 | ✓ |
| **FE ⇒ AS** | 恒成立（经 NF） | 同上 | FE 在 AS 前 | ✓ |
| CS ⇒ ¬CN | **互斥** | `elif` 结构 | — | ✓ |
| **CN ⇒ ¬SC** | 恒成立 | SC 第一支要求 `hits` 为空 | — | ✓ |
| **ND ⇒ ¬SC(第一支)** | 恒成立 | 同上 | — | ✓ |
| D ⇒ SC(第二支) | **仅在 `detail` 为空时** | 谓词定义 | D 在 SC 前 | ✓ |
| M / S ⇒ 任何 | **无蕴含** | M 只关 `expected_red` 派生；S 在进程内恒假（已记 B） | — | ✓ |

**⇒ 结论：十个值里只有一处违规（FE/NF），其余全部与既定层序相容。**
**⇒ 修后层序**：`mode_unknown · def_mismatch · stale · finalize_error · not_finalized · coverage_shape · asserts_short · coverage_not_met · no_discrimination · self_contradiction`

### 顺查带出的两条新事实
**① 一次异常会产生四格命中**：`FE ⇒ NF ⇒ {CS, AS}` ⇒ 注入跑二的 `instrument_hits` 会是 **`["finalize_error","not_finalized","coverage_shape","asserts_short"]`**，只有第一格被报出。
**⇒ 因此跑二**不许**断言 `hits == ["finalize_error"]`** —— 那会必然失败；应断言 `instrument == "finalize_error"` ✓（lead 已如此写）。**记下来，防止将来有人把它"收紧"成列表相等。**
**② `asserts_short` 与 `coverage_shape` 的私域很窄**：因为 **NF ⇒ AS** 且 **NF ⇒ CS**，这两格只有在 `finalized` 为真时才可能被报出。
**⇒ 而这恰好是它们该管的情形**：`finalized` 为真意味着四步跑完了，此时"declare 与 ran 不符"就是真的不符；"coverage_ok 成形"就是真的有形。**窄是对的。**


### 核 lead 的 `ORDER_IMPLIES` + 导入期断言：方向对，**三处要改**

| # | 问题 | 后果 |
|---|---|---|
| 1 | **`LAYERS.index(a)` 在名字拼错时抛 `ValueError`** | **导入失败 ⇒ 两份夹具全部 `ImportError`/`ValueError` ⇒ 无产物、无码 5、只有 traceback** —— **正是今晚被禁的「仪器崩而不是报 5」** |
| 2 | **`assert all(...)` 不说是哪一对违规** | **"有话说但说不出内容"的自检与死值等价**（`def_mismatch_detail` 那条同一课） |
| 3 | **lead 提的 `test_can_fail` 演练方式（把两格对调一次再改回）会改源文件** | **与我们两轮前否掉 `step2 改源文件再跑` 的理由完全一样**：中途异常会把源留在错状态，而那种残留最像源码 |

### 修法（三条都很小）
```
def check_order(layers, implies):
    """纯函数：给定层序与蕴含表，返回违规对。不读文件、不抛（除类型错）。"""
    missing = sorted({n for p in implies for n in p if n not in layers})
    if missing:
        return [("missing", tuple(missing))]
    return [(a, b) for a, b in implies if layers.index(a) >= layers.index(b)]

_bad = check_order(LAYERS, ORDER_IMPLIES)
assert not _bad, "蕴含者必须在前，违反: %s" % (_bad,)
```
**⇒ 修 1**：**先查名字是否存在**，缺则报 `("missing", (名字,))` 而不是 `ValueError` —— **消息说得出问题**；且**导入期崩溃仍是"根本不启动"**，它不属于"启动后报 5"，**前提是这段只碰静态数据**。
**⇒ 修 2**：**返回违规对列表**，直接指出是哪一对。
**⇒ 修 3**：**`check_order` 是纯函数 ⇒ 快闸喂一个对调过的元组即可验它，不必改源文件、不必 reload** —— **`test_can_fail` 因此不再有副作用。**

### 并给"导入期断言"划一条边界
| 允许在导入期断言的 | 不许的 |
|---|---|
| **静态结构**：层序、蕴含表、枚举闭集、常量关系 | **任何读文件 / 计算实测值 / 依赖环境** |
**⇒ 理由**：**导入期断言失败 ⇒ 进程起不来 ⇒ 永远不会有产物** ⇒ **它只配守"根本不启动"这一档**；**一旦让它参与"这次的读数对不对"，它就把缺证变成了崩溃。**


### 我的独立复核（当前 sha：chat `1f9551eccdcfca7a` · V `4e087148eb489b15` · H `944f87d6bd34a403` · R `6d3f717e2029d3cc` · D `4fc43e3c5782160b`）

#### 1. lead 引的跑一产物是 **stale**，当前版是 attempt30
| 产物 | harness_sha16 | 判 |
|---|---|---|
| `M4C-SITE3-green-green-attempt29.json`（06:55:54） | `6d3f717e2029d3cc:944f87d6bd34a403:**1455122be8b1be6a**` | **stale**（V 段已变） |
| `M4C-SITE3-green-green-attempt30.json`（06:57:24） | `6d3f717e2029d3cc:944f87d6bd34a403:**4e087148eb489b15**` | **当前** ✓ |
**⇒ `STALE ∉ CURRENT` 第一次真实命中，命中的是 lead 自己引用的那份。** 两份的五项读数相同，但**只有 attempt30 是当前身份的产物**。
**⇒ 两份都缺 `instrument` / `instrument_hits`** ⇒ lead §1 的机制成立（`finally` 里 `json.dump` 早于 `verdict`）✓

#### 2. 站点 1 base **已存在且是当前身份**（不需要再跑）
`M4C-DELETE-SITE1-base-attempt19.json`（06:57:30）harness = `4fc43e3c5782160b:944f87d6bd34a403:4e087148eb489b15` ⇒ 三段全对 ✓
`deleted-attempt19` 同 ✓，且 `src_line_count == variant_line_count == 682`、`deleted_line_no: 261` ⇒ ⑮ 的行数相等有读数 ✓

#### 3. 🚨 ⑤ 不是「被验证」，是「读回我们自己写的常量」
**站点 1 两份产物的 `assertions` 是 2 条 `site1.place`，`status: "checked"`** —— **不是 `skipped`**。
| 字段 | 值 |
|---|---|
| `covers_declared` | `["site1"]` |
| `covers_observed` | `["site1"]` |
| `assertions_status` | **`"checked"`** |
| `coverage_ok` | **`"not_applicable"`** |
| `coverage_reason` | 「control=True: A/B 记 skipped，覆盖不适用」 |
**⇒ 覆盖本来是真的成立的（observed == declared）**，而 `coverage_ok` 被硬编码 `control = (site == 1)` 盖成「不适用」，**且 `coverage_reason` 那句" A/B 记 skipped"与产物里的 `checked` 直接矛盾。**
**⇒ 于是 lead 判「⑤ 通过」所读的那个值，正是本批刚写死的常量** ⇒ **用期望核对期望**。
**⇒ 建议**：**删掉 `control` 覆盖与 `coverage_reason`** —— 比较分支对站点 1 同样正确（`true`）；`not_applicable` 因此失去唯一使用者 ⇒ **三值退二值**，`coverage_shape` 的白名单里那一项也随之无用户。

#### 4. 🚨 「站点 1 是冗余」这两份产物**证不了**，而它们自带的 note 已经承认了
断言自带的 note 原文：**「站点 1 的判据是 pre-existing 的 n_tokens == index n；删掉该站点的 reset 不会红（load 自清），本条记覆盖不记冗余」**
**⇒ 即：这两条断言按设计就不检验冗余** ⇒ `is_red: false` 在两臂**是零信息量**。
**⇒ 这两份产物里唯一真正可比的行为读数，是 `loads`（引擎回读，与断言无关）**：
| 臂 | `loads` |
|---|---|
| base | `[{seq:1,name:profile,n_returned:50,n_tokens_after:50,pos_max_after:49}, {seq:2,name:project,36,36,35}]` |
| deleted | **逐字段相同** |
**⇒ 只能据此写**：**「删掉站点 1 的 `leases.reset` 之后，两次 load 的 seq/name/n_returned/n_tokens_after/pos_max_after 完全一致」** —— **这是一条关于"加载行为"的实测陈述，不是"站点 1 冗余"的证明。**
**⇒ 二者的差别是实质的**：**`loads` 不观测 cell 池是否泄漏**（那正是站点 3 的不可替代性所在）⇒ **"站点 1 冗余"若成立，也只对"读者看到的加载结果"成立，不对"池资源"成立。**


### 核 lead 的撤回与本批五件：两处必须先说

#### 🚨 1. `④` 删 `control` 时必须**同批**删掉 `m4c_verdict.py` L91–93 的守卫 —— 否则每一次运行都是码 5
当前 `m4c_verdict.py`（`4e087148eb489b15`）：
```
L87  if cov not in (True, False, "not_applicable"):
L88      hits.append("coverage_shape")
L91  if not isinstance(rec.get("control"), bool):   # coverage_ok 的输入没成形 ⇒ 复用 coverage_shape
L92      if "coverage_shape" not in hits:
L93          hits.append("coverage_shape")
```
**⇒ 这个 L91–93 守卫是我上一轮提的方案，现在必须由我自己撤回：** **`control` 一旦删除，`rec.get("control")` 恒为 `None` ⇒ 恒不满足 `isinstance(..., bool)` ⇒ 每次运行都命中 `coverage_shape` ⇒ 四跑全是码 5。**
**⇒ 且症状会显示成"仪器坏了"，而不是"字段删漏了"。**
**⇒ ④ 必须一次删三处**：
| # | 位置 | 内容 |
|---|---|---|
| a | `m4c_harness.py` L56–58 | `if rec.get("control") is True:` 覆盖 + `coverage_reason` |
| b | `m4c_verdict.py` L91–93 | `isinstance(rec.get("control"), bool)` 守卫（**我提的，撤回**） |
| c | `m4c_verdict.py` L87 + 两夹具 | 白名单里的 `"not_applicable"`；两处 `rec["control"]` 写入 |
**⇒ 这是一条新形状，与今晚那条互补**：**「加字段与接消费者必须同批」是正向；「删字段与删守卫必须同批」是反向 —— 守卫是字段的最后一个消费者，而它藏在另一个文件里。**

#### 🚨 2. §7「能签的」第一条：**①-a 的红半没有当前身份产物**
**`out/` 共 152 份 JSON，harness_sha16 三段全等于当前三元组的只有 3 份**：
| 产物 | mode | 判 |
|---|---|---|
| `M4C-SITE3-green-green-attempt30` | green | 当前 ✓ |
| `M4C-DELETE-SITE1-base-attempt19` | base | 当前 ✓ |
| `M4C-DELETE-SITE1-deleted-attempt19` | deleted | 当前 ✓ |
**⇒ 红臂最新是 `M4C-SITE3-red-red-attempt25`（06:48:38），harness = `5ae4687c457c1970:6d7236ab1b3cdc79:f30d8a5d432310c2` —— 三段全 stale。**
**⇒ 即：①-a 的绿半有当前产物，红半没有 ⇒「站点 3 的 A/B 在绿臂与红臂上都有判别力」这句整条不能签，只能签绿半。**
**⇒ 这正是刚刚那次错的复本，只隔了一节。**
**⇒ 另：`out/` 的 152 份里 149 份 stale（97.4%）** ⇒ **交付里那句"此前全部标 stale"现在有数了，应写成 149/152。**
**⇒ 且身份格式中途变过一次**：`red-attempt20/21/22` 的 `harness_sha16` 是**单段**（如 `1e3da3a6e0c99b4b`）⇒ **跨格式无法比较，只能重跑。**


### 核 ② 的机制：**已有**（`run_site3.py` L87 `M4C_FIXTURE_FILE`），但产物路径会**覆盖**
`run_site3.py` 现在的相关行：
```
L38  tag = sys.argv[2] if len(sys.argv) > 2 else "attempt"
L85  out = os.path.join(HERE, "out", "M4C-SITE3-%s-%s.json" % (mode, tag))
L87  os.environ.get("M4C_FIXTURE_FILE", os.path.abspath(__file__)))
```
**⇒ ② 不需要新机制**：`M4C_FIXTURE_FILE=<不存在的路径> python run_site3.py green <tag>` 即可 ✓ 同一份夹具、同一段代码、不改源文件 ✓

#### 🚨 但产物名 = `(mode, tag)`，**不含 `run_id`** ⇒ 注入跑会用同一个名字覆盖绿臂产物
| 若 | 后果 |
|---|---|
| 注入跑与绿臂跑用同一 ~tag~ | **同一路径 ⇒ 绿臂产物被覆盖 ⇒ 目录里只剩一份带 `finalize_error` 的 "green" 产物** |
| 而它看起来 | **像"绿臂跑出了 finalize_error"** —— 与本意相反的读数 |
**⇒ `tag` 由人手写（`green-attempt30`），默认值 `"attempt"` ⇒ 冲突是**默认状态**，不是意外状态。**
**⇒ 修法（结构上排除，不靠纪律）**：产物名加入 `run_id`（它已经在 rec 里）：
`out = ... % (mode, tag, run_id)`
**⇒ 能构造上排除的，不要留成"记得换 tag"。**

#### 🚨 并且：注入产物里**没有任何字段记录"被告知要测哪个文件"**
**`harness_sha16` 全程缺席（因为 `harness_id` 当场抛），于是产物里唯一的注入痕迹是那句异常串。**
**⇒ 要求**：`run_main` 在 `try` 内、`harness_id` 之前写 `rec["fixture_file_used"] = fixture_file`（纯赋值，不 I/O）。
**⇒ 于是**：正常跑写 `…\run_site3.py`；注入跑写 `…\no_such_fixture.py` ⇒ **注入在同一份产物里可见，而不只靠异常串。**
**⇒ 且这让"这次读数测的是谁"始终可读 —— 而今晚已经三次因为"测的是谁"没写清而误判。**


### 核 lead 的 ⑤⑥：「三件自证」需要一个"失败路径"的格子，否则注入产物必被误判；且 ⑤ 让 E 不能再推迟

#### 1. 🚨 ⑤ 把 `run_id` 提升为身份的一部分 ⇒ **E（`redcheck_delete.py` L48 注释吞掉 `run_id`）不能继续推迟**
`redcheck_delete.py` **L48**：`"expected_red": False,   # …（冗余） "run_id": run_id,` ⇒ **`run_id` 从未进入 `rec`。**
**⇒ 一旦产物名用 `run_id`：文件名里有、正文里没有 ⇒ 文件名与正文之间没有 join 键。**
**⇒ 于是"文件名说这是哪一次跑"与"正文说这是哪一次跑"无法互相验证** ⇒ **两份产物可以同名而内容不同（覆写之外的情形：复制、改名）。**
**⇒ 所以 E 从"缺一个无消费者字段"升级为"缺一个身份字段"。** **一个字段的优先级，取决于它有没有消费者 —— 而消费者是 ⑤ 刚刚加上的。**

#### 2. 🚨 「三件自证」必须有失败路径的格子，否则注入产物注定被判不合格
| 产物 | `fixture_file_used` | `harness_sha16` | `instrument` |
|---|---|---|---|
| 正常跑 | 有 | **有** | 有 |
| **注入跑** | 有 | **必然缺**（`harness_id` 当场抛） | 有 |
**⇒ 若机械判据写成"三样齐"，注入产物必然失败 ⇒ 而它是**正确**的产物。**
**⇒ 而若为了让注入通过写成"有 `finalize_error` 就跳过自证检查"，则所有崩溃产物一律免检** ⇒ **又一个"一格并两格"。**
**⇒ 修法**：**把三件自证本身写成产物里的一个字段，让"缺哪一样"可读、可数**：
```
rec["selfevidence"] = {
    "fixture_file_used": isinstance(rec.get("fixture_file_used"), str),
    "harness_sha16":     isinstance(rec.get("harness_sha16"), str),
    "instrument":        rec.get("instrument") in LAYERS,
}
```
**⇒ 于是判据是"这份产物的自证形态 == 它该有的形态"，而不是"三样齐"：**
| 应有形态 | 谁 |
|---|---|
| `(True, True, True)` | 正常完成 |
| `(True, False, True)` | **注入**（缺版本，因为版本读不出来） |
**⇒ 「缺」被枚举，不再被例外化。**

#### 3. 顺带一条免费交叉核对
**`harness_sha16.split(":")[0]` 应当等于 `sha16(fixture_file_used)`。**
**⇒ 它验的是"正文声称的身份"与"正文声称测的文件"是同一个东西** —— 两者都是产物里的字段，快闸可纯静态判，无需引擎。
**⇒ 若不等 ⇒ 产物自相矛盾 ⇒ 该归 `self_contradiction`。**


### 🚨 红臂跑不出合法红：第二条 assert 的"活通道"是一个死谓词
`m4c_harness.py`（`944f87d6bd34a403`）当前：
```
L57  rec["die_kind"] = ("assertion" if any(a.get("kind") == "assertion" for a in log)
L61      rec["assertions_status"] = "assertion_failed"
L70  rec["is_red"] = (rec["die_kind"] == "assertion") or any(
L71      a.get("status") == "assertion_failed" for a in log)
L75  rec["asserts_ran"] += 1
L76  assert (not rec["is_red"]) or any(a.get("status") == "assertion_failed" for a in log), \
```
**断言日志的真实形状**（`out/asserts-*.json`，实测）：
`{"id": "site1.place", "site": 1, "status": "checked", "seq": 1, "block": "profile", …}`
**⇒ `status` 的取值是 `"checked"` / `"skipped"`；失败标记在 `kind` 上（L57 用的就是 `a.get("kind") == "assertion"`）。**
**⇒ `"assertion_failed"` 这个词只作为 `rec["assertions_status"]` 的值出现（L61），它从不出现在日志条目的 `status` 里。**

**⇒ 于是 L71 的第二支、以及 L76 的第二支，都是死谓词。**
| 臂 | `is_red` | L76 的 `any(...)` | 结果 |
|---|---|---|---|
| 绿 | `False` | 不求值（短路） | `assert` 通过 ✓ |
| **红** | **`True`**（经 L70 第一支） | **`False`（死谓词）** | **`AssertionError` ⇒ 进 `except` ⇒ `finalize_error` + `not_finalized` ⇒ 码 5** |
**⇒ 即：红臂跑出来的不是"红由断言造成"，而是"仪器坏了"。** **而"仪器坏了"这个读数会把人引向查仪器，而真正的缺陷在这条守卫。**

### 修法两处
**① 删掉 L71 的死支** —— `is_red` 只剩一个通道（`die_kind == "assertion"`），而这个通道是活的（`tools/chat.py` L147 `die` 记 `kind: "assertion"`）。
**② L76 的守卫改用活通道**：
`assert (not rec["is_red"]) or rec["die_kind"] == "assertion", "红必须由断言造成"`
**⇒ 两处必须同批**：**只改 ② 不改 ①，`is_red` 仍声明两个来源而只有一个活着 —— 那是"两条通道，盲区相同"，不是冗余，是装饰。**

### 这条的一般形式
> **当 `X = A or B`，而守卫写成 `X or B`，守卫实际只承认 B —— 它继承了「或」里最弱的那个分支。**
**⇒ 正确的做法不是把守卫写全，而是先确认 `A` 与 `B` 都还活着；** **若 `B` 已死，它不该出现在任何表达式里。**


### 我的上一条被数据否掉：`status=assertion_failed` 确实存在（我复算：57 份 / 182 条 / 两种组合 / 零交叉）
| kind | status | 条数 |
|---|---|---|
| (none) | checked | **172** |
| **assertion** | **assertion_failed** | **10** |
| 其他任何组合 | — | **0** |
样本 `asserts-054df407.json`：`{id: die, site: null, status: assertion_failed, kind: assertion, message: M4-C 范围断言红 @m1.unmount: 调用流 hits=[]（0 条） != dropped=[2]（1 条）}`
**⇒ 我错了：`assertion_failed` 是 `die` 条目的 `status` 值，且与 `kind=assertion` 同条。** **「删 L71」若执行会删一个活通道。**

### 🚨 但 lead 的新第二条 `assert` 仍恒真 —— 这次由**操作数的类型**排除，不由逻辑排除
```
rec['is_red'] = rec['die_kind'] == 'assertion'
assert not (rec['is_red'] and rec['die_kind'] == 'crash')
```
**⇒ `is_red` 就是 `die_kind == assertion` 的定义；代入后为 `not ((die_kind==assertion) and (die_kind==crash))`。**
**⇒ `die_kind` 是单值字符串，不可能同时等于两个不同值 ⇒ 内层恒 False ⇒ `not False` ⇒ 恒真。**
**⇒ 即：从「P ⇒ P（同一事实两种写法）」换成「P ⇒ ¬Q，而 Q 按类型不可能」—— 两者都是对空集的断言。**

### 能红的那条：必须换**生产者**，不是换**表达式**
| 字段 | 谁产生 |
|---|---|
| `die_kind` / `is_red` / 日志条目的 `status` | **同一个 `_m4c_log` 条目**（同一 dict、同一次写入） |
| **`rec[exit]`** | **夹具捕获 `SystemExit.code`** —— **另一个生产者** |
**⇒ 可红的守卫**：`assert (not rec[is_red]) or rec[exit] == 1`，消息为「红必须伴随退出码 1（die 路径），而非崩溃或正常结束」
**⇒ 它能红**：若 `die` 换了退出码，或 `is_red` 改成别的来源，此条立刻响 —— **因为它比较两个不同生产者的输出。**

### 一般化（今晚第二次同一形状）
> **派生量不能与被派生量互查；同一生产者产出的两个字段不是两个见证。**
**⇒ 今晚第一次是跨文件的（`def_source_count` vs `def_fp`），这次在同一行内。** **判法只有一句：问这两个操作数分别由谁写；同一个写入点 ⇒ 不是见证。**


### 核 lead 的 ①（换生产者 + 纯函数）：先确认 `red_guard` 在合法红臂上为真，再指出三处
**`tools/chat.py` L149–157 实测**：
```
L155  _m4c_log({id: die, site: None, status: assertion_failed, kind: assertion, message: …})
L157  sys.exit(1)
```
**⇒ 合法红臂 `rec[exit] == 1` ⇒ `red_guard` 为真 ⇒ 不会误报 ✓** （且 `site: None` 使该条目不进 `covers_observed`，与 harness L54 的过滤一致 ✓）

#### 🚨 A. `contract_ok` 必须有消费者，否则是今晚又一个无消费者字段
**lead 计划把它写进产物 —— 但没写谁读它。**
**⇒ 一个 Bool 字段若只落盘，它的取值对不对永远不变现** ⇒ 与本晚 `run_id`（被注释吞掉也没人发现）同一模式。
**⇒ 要求**：`contract_ok is False` ⇒ `hits.append(self_contradiction)` —— 它本来就是「产物内部自相矛盾」的定义。
**⇒ 于是 `contract_ok` 的两种结局都合法**：驱动一个 hit，或进快闸断言。**没有第三种。**

#### 🚨 B. 两个守卫函数必须用 `.get()`，不能用下标
**`bool_guard(rec) = isinstance(rec[is_red], bool)`** —— **它守的正是「`is_red` 可能是 `None` 或缺失」，而它自己先按键取值。**
**⇒ 若 `is_red` 缺失 ⇒ `KeyError` ⇒ 守卫抛异常而不是返回 `False`** ⇒ **「仪器崩而不是报红」，今晚已禁两次。**
**⇒ 一个守卫「字段在不在」的函数，不许自己先要求那个字段存在。**
```
def bool_guard(rec): return isinstance(rec.get('is_red'), bool)
def red_guard(rec):  return (rec.get('is_red') is not True) or rec.get('exit') == 1
```
**⇒ `red_guard` 用 `is not True` 而非 `not`**：把「红」限定为 `True` 这一个值，与 `bool_guard` 的取值域一致；`None` 时两支都放行。

#### C. `red_guard` 只在红臂有判别力
**绿臂：`is_red` 为 `False` ⇒ 第一支为真 ⇒ 恒通过，不检查 `exit`。**
**⇒ 绿臂的通过不构成「守卫有效」的证据；唯一证据是快闸喂 `(True, 2)` 得到 `False`。**
**⇒ lead 已计划 ✓ 我补一句：快闸至少喂三组** —— `(True, 2) → False`（能红）· `(True, 1) → True`（不误报）· `(None, 0) → True`（缺失不追究）。**第三组正是 B 那处修复的证据。**


### 🚨 五跑里三份会被判不合格：`selfevidence` 第三布尔在绿/红臂上恒 `False`
`m4c_verdict.py` **L110**：`rec["instrument"] = hits[0] if hits else None`
**⇒ 绿臂 `hits == []` ⇒ `instrument` 是 `None`**
**⇒ 而 `selfevidence["instrument"]` 写成 `rec.get("instrument") in LAYERS` ⇒ `None in LAYERS` ⇒ `False`**
| 跑 | 期望形态 | 按现写法实际 |
|---|---|---|
| green | `(T,T,T)` | **`(T,T,F)`** |
| red | `(T,T,T)` | **`(T,T,F)`** |
| base / deleted | `(T,T,T)` | **`(T,T,F)`** |
| inject | `(T,F,T)` | `(T,F,F)` |
**⇒ 五份全会不合格 ⇒ 且不合格的样子是「自证缺失」，指向 `instrument` 字段 —— 而那个字段其实正常。**
**⇒ 这是今晚第三次「验收读数按当时写法不可满足」**（前两次：`asserts_ran == 2` 在绿臂恒 1；`instrument == finalize_error` 被 `not_finalized` 吸收）。

### 修法：第三布尔不判"是不是 LAYERS 里的值"，判**那条不变式**
```
"instrument": ("instrument" in rec) and ("instrument_hits" in rec)
              and (bool(rec["instrument_hits"]) == (rec["instrument"] is not None))
```
| 情形 | 左 | 右 | 判 |
|---|---|---|---|
| 绿/红（hits 空、instrument None） | `False` | `False` | **True ✓** |
| 注入（hits 非空、instrument 有值） | `True` | `True` | **True ✓** |
| 有人设了 `instrument` 却 `hits` 空 | `False` | `True` | **False ⇒ 真的能红 ✓** |
**⇒ 它从"成员资格测试"变成"不变式检查"**：**前者在正常情况下恒假，后者在正常情况下恒真、在异常情况下才假。**
**⇒ 而这正是"自证"该有的形状：它问的不是"字段长得对不对"，是"字段之间还自洽吗"。**

### 附：`unasserted_fields` 需要两类字段，否则永远非空
**产物里大量字段是「证据」（`sampled_at` · `note` · `deleted_line` · `assertions` 数组），快闸永远不读它们，也不该读。**
**⇒ 若"产物字段清单 − 快闸读键清单"直接当失败条件，它会对每一份正确产物都非空。**
**⇒ 要求**：**字段一落地就必须归类** —— **判定字段**（必须有读者）或 **证据字段**（不得有判定读者）。
**⇒ `unasserted_fields = 判定字段 − (快闸读键 ∪ hits 消费)`** ⇒ 非空才失败。
**⇒ 于是 lead 那条"写不出读者的字段不写"，变成"写不出类别的字段不写" —— 而类别是可核的，读者只是可想的。**


### 核快闸 `m4c_selfcheck.py`（`e4e3d30334ae151c` / 170 行）—— 四处，都属今晚同一族

#### 🚨 A. 自证键名两套：快闸期待 `subject/version/verdict`，而本批写 `fixture_file_used/harness_sha16/instrument`
```
L146  all((rec.get("selfevidence") or {}).get(k) for k in ("subject", "version", "verdict"))
```
**⇒ ⑦ 落地后 `selfevidence` 的键是另外三个 ⇒ `se.get("subject")` 恒 `None` ⇒ `all(...)` 恒 `False` ⇒ `step5` 对每一份正确产物都判失败。**
**⇒ 两份设计各自写了一组键名，而它们描述的是同一个对象。** **必须选一套，并在两处使用同一组常量。**

#### 🚨 B. `bool_guard` 那一支是恒真比较，且它没有期望列
```
L112  ok = (got is want) and V.bool_guard(rec) is isinstance(rec.get("is_red"), bool)
```
**⇒ `bool_guard` 的定义就是 `isinstance(rec.get("is_red"), bool)` ⇒ 第二个合取项是 `f(x) is f(x)`，永不失败。**
**⇒ 于是三组喂法只验了 `red_guard`，`bool_guard` 一格未验。**
**⇒ 而第三组恰是 `bool_guard` 该红的地方**：`(is_red=None, exit=0)` ⇒ **`red_guard` 应为 `True`，`bool_guard` 应为 `False`** —— **两个函数对同一输入期望相反，而表里只写了一列。**
| 喂 | `red_guard` | `bool_guard` |
|---|---|---|
| `(True, 2)` | `False` | `True` |
| `(True, 1)` | `True` | `True` |
| `(None, 0)` | `True` | **`False`** |

#### 🚨 C. `identity_cross_check in (None, "ok")` ⇒ 字段缺失即通过
```
L145  rec.get("identity_cross_check") in (None, "ok")
```
**⇒ 本批 ⑦ 只说"做 `split(':')[0] == sha16(fixture_file_used)` 交叉核对"，**没说把它写成 `identity_cross_check`** ⇒ 字段不存在 ⇒ `None` ⇒ 通过。**
**⇒ 于是那条交叉核对在快闸里没有牙齿** ⇒ 又一个无消费者判据。
**⇒ 要求**：`== "ok"`，缺失即失败。

#### D. 产物名现状不对称，且有第三个写入者
| 脚本 | 产物名 | `run_id` |
|---|---|---|
| `redcheck_delete.py` **L90** | `M4C-DELETE-SITE%d-%s-%s-%s.json` | **已有** ✓（attempt19 是改之前的旧名） |
| `run_site3.py` **L85** | `M4C-SITE3-%s-%s.json` | **缺** |
| **`redcheck.py` L119** | `M4C-%s-SITE%d.json` | **缺，且无 tag** ⇒ **一个只会覆写的写入者** |
**⇒ 好消息**：`step5_latest` L136–137 按 `getmtime` 排序 ⇒ **名字里加 `run_id` 不破坏"取最新"** ✓


### 核 `run_kind`：一个事实不该有两个写入点；而遗留的环境变量正好被 ⑦ 的交叉核对兜住

#### 1. `run_kind` 与 `fixture_file_used` 是**同一表达式**的两个写法
```
rec["fixture_file_used"] = os.environ.get("M4C_FIXTURE_FILE") or os.path.abspath(__file__)
rec["run_kind"]         = "injected" if os.environ.get("M4C_FIXTURE_FILE") else "normal"
```
**⇒ 两者由同一个 `os.environ.get(...)` 派生。若两天后有人只改了其中一处（例如把默认值改成 `__file__` 的绝对路径比较），两份字段就会互相矛盾，而没有任何东西会发现。**
**⇒ 这与今晚那条「同一生产者两字段不是两见证」不是一回事**：**那次是两个字段各自独立写、看似互证；这次是一个事实写了两遍、只可能相斥。**
**⇒ 修法**：**只写原语，类别由读取方派生** ——
| 写入方（夹具） | 读取方（快闸） |
|---|---|
| `rec["fixture_from_env"] = bool(os.environ.get("M4C_FIXTURE_FILE"))` | `kind = "injected" if rec.get("fixture_from_env") else "normal"` |
**⇒ 一个事实一个写入点；类别是解释，解释放在读者一侧。** **而 `fixture_from_env` 的类型是 `bool`，它自己就能被 `is not True` 式判断兜住（缺失即非 injected）。**

#### 2. 遗留的环境变量是真风险，而 ⑦ 的交叉核对正好兜住它
**`M4C_FIXTURE_FILE` 若在 shell 里留着（上一次注入跑之后没清）⇒ 正常跑会真的去测那个路径。**
| 遗留值 | 后果 | 谁发现 |
|---|---|---|
| 指向不存在的文件 | `harness_id` 抛 ⇒ 产物缺版本 ⇒ 自报 `injected` | **一致性判据（形态 == `(T,F,T)`）✓** |
| **指向存在的另一个文件** | **跑的不是夹具本身**，而产物里 `fixture_file_used` 是那个路径 | **⑦ 的 `split(':')[0] == sha16(fixture_file_used)` ⇒ 不等 ⇒ `self_contradiction` ✓** |
**⇒ 第二条是本晚唯一一处「先立的交叉核对，正好覆盖后引入的风险」** —— **值得记：它不是为新风险写的，却仍然有效，因为它比较的是两个字段之间的关系。**
**⇒ 关系型检查的收益在这里第二次显形**：**存在性检查要为每个新风险各写一条；关系检查一次写对，覆盖整类。**
**⇒ 操作要求**：**四份正常跑之前显式清空** —— `export M4C_FIXTURE_FILE=`（空串为假 ⇒ `normal` ✓），**不要靠 `unset` 的记忆，把它写进跑的命令行里。**


### 复核当前码（`H 33c9a502b7ff80af` · `V 307b4ce384adb852` · `site3 073ceba3ed7fe411` · `del 41bc432b7542c478`）：⑤/E 已落地，两处须改

#### 🚨 1. 五跑的两条 DELETE 命令行**参数顺序写错**
`redcheck_delete.py` **L36–38**：
```
L36  site = int(sys.argv[1])
L37  mode = sys.argv[2] if len(sys.argv) > 2 else "base"
L38  tag  = sys.argv[3] if len(sys.argv) > 3 else "attempt"
```
**⇒ 顺序是 `site, mode, tag`。**
| lead 写的 | 实际发生 |
|---|---|
| `redcheck_delete.py <tag> base` | `site = int(<tag>)` ⇒ **非数字 tag 直接 ValueError，无产物** |
| 若 tag 恰好是数字 | `site = <tag>`、`mode = "base"` ⇒ **测错站点，而产物名照写** |
**⇒ 正确写法**：`python redcheck_delete.py 1 base <tag>` / `python redcheck_delete.py 1 deleted <tag>`
**⇒ 而 `run_site3.py` L36/L38 是 `mode, tag` ⇒ lead 那两行是对的 ✓**
**⇒ 两个夹具签名不同，而这正是「命令行写全」要防的那类错 —— 它不是记忆问题，是接口不一致。**

#### 🚨 2. `contract_ok` 用 `assert` ⇒ 契约违规会被伪装成「仪器坏了」
```
L72  rec["contract_ok"] = (rec["die_kind"] == "assertion") == rec["assertion_failed_in_log"]
L79  rec["asserts_ran"] += 1
L80  assert rec["contract_ok"], "契约检查（chat.py 与 harness 之间）：die 的 kind 与 status 不再等价"
```
**⇒ 若 chat.py 某天只写 `kind` 不写 `status`：`contract_ok` 为 `False` ⇒ assert 抛 ⇒ `run_main` 的 except ⇒ `finalize_error` + `not_finalized` ⇒ 码 5、`instrument == "finalize_error"`。**
**⇒ 而真相是「chat.py 与 harness 的契约变了」，不是「仪器坏了」。**
**⇒ 且它会连吞两层**：`finalize_completed` 没盖 ⇒ LAYERS 里 `not_finalized` 先命中 ⇒ **`self_contradiction` 永远轮不到**（顺序吸收，今晚已两次）。
| 该报的 | 会报成 |
|---|---|
| 契约违规（`self_contradiction`） | **`finalize_error` + `not_finalized`（仪器坏）** |
**⇒ 修法**：L79–81 换成 `if not rec["contract_ok"]: rec["contract_violation"] = True`，由 `instrument_hits` 判 `self_contradiction`。
**⇒ 判据红走 hits，仪器坏走 except，两者不许借道 —— 而 assert 是「借道」的唯一形态。**


### 🚨 实测：lead 提的 `assert_in_try` 工具今天会返回 **0** —— 因为它扫不到那三条
我用 `ast` 跑了 `m4c_harness.py`（`33c9a502b7ff80af`）：
```
asserts_in_try: 0
asserts_total: 3
 * V.bool_guard(rec)
 * V.red_guard(rec)
 * rec['contract_ok']
```
**⇒ 三条 assert 全在 `finalize` 函数体里，而 `try` 在 `run_main` 里 —— `try` 的词法范围不包含它们。**
**⇒ 于是「`ast` 列出 `try` 块内的 Assert 节点」这条检查，今天的读数就是 0 ⇒ 白名单比对恒通过 ⇒ 它一个也抓不到。**
**⇒ 而空结果会被读成「干净」，不是「没扫到」——今晚已禁过的同类。**

### 正确谓词：不是「lexically inside try」，是「**从 try 体可达**」
`run_main` 的 `try` 里调用 `finalize(...)` ⇒ **`finalize` 的 assert 失败时，看到它的确实是 `except`** ⇒ **语义上它们就在 try 里，只是词法上隔着一次调用。**
| 写法 | 今天读数 | 判别力 |
|---|---|---|
| `ast.Try` 子树里的 `Assert` | **0** | **零**（恒通过） |
| **从 `try` 体出发调用可达的函数里的 `Assert`** | **3** | 真的能红 |
**⇒ 而更简单的等价形式**: **只需问「这个 assert 所在函数的调用者里，有没有一个把它放在 `try` 里」。** 单层即可，本仓没有更深。
**⇒ 并且必须带「期望条数」**：白名单式检查若允许"一个都没扫到"，它就会把扫空当成通过。

### 一般形式（今晚第三次同族）
> **凡是"按语法范围"找东西的检查，先确认那个范围真的包含被测对象。**
**⇒ 前两次**：盘点用 `grep` 命中代替枚举目录；守卫用 `isinstance` 守一个已不存在的字段。**⇒ 共同形态：搜索范围与被测对象不重合，而空结果读成干净。**


### 重测（文件又变了）：`H 4883f2c7f04b2818` · `V f36298183f9dad8b` · `site3 8c0e785ae28d63d0` · `del 6686fef2ffd90b3e` · `selfcheck 3819e51b185bd4ea`
**语义可达谓词跑出来的读数**：
```
asserts_total: 3   （全部在 finalize，全部 reach=1）
 - finalize | reach: 1 | V.bool_guard(rec)
 - finalize | reach: 1 | V.red_guard(rec)
 - finalize | reach: 1 | rec['asserts_ran'] == rec['asserts_declared'] or True
```
**⇒ `contract_ok` 的 assert 已撤 ✓；换来一条带 `or True` 的计数器 assert。**
**⇒ 语义可达与词法在 `try` 内给出的答案是 3 vs 0 —— 谓词换对了，读数立刻不一样。**

#### 🚨 但 `asserts_declared` 此刻度量的是一个**混合量**
`asserts_declared(fn)` 数的是**函数体直属的 `assert` 语句条数**（H L13）；而三条里有一条是**恒真计数器**（`or True`）。
**⇒ 于是 `asserts_declared == 3` 的真实含义是「2 条真断言 + 1 条计数」，而它读起来像「3 条真断言」。**
**⇒ 将来撤掉计数器时，`asserts_declared` 从 3 掉到 2，而 `asserts_ran` 也掉到 2 ⇒ 等式仍成立 ⇒ 没有任何东西会提醒「少了一条真断言」。**
| 想要数的 | 现在用同一语法特征数 |
|---|---|
| 真断言条数 | `ast.Assert` 个数（含计数器） ✗ |
| 执行步数 | `asserts_ran += 1` 的次数（与上文同源） ✗ |
**⇒ 建议**：**计数器不要写成 `assert`**，就写成 `rec["asserts_ran"] += 1` 单独一行；断言保持 `assert`。
**⇒ 于是两个派生各有独立的语法特征**：`asserts_declared` = `ast.Assert` 数（真断言）；`asserts_ran` 的期望 = `+= 1` 的行数。**两者不再共用一个特征，也就不再把两件事数成一个数。**
**⇒ 与今晚那条同源**：**一个格子装了两类东西，它们就会互相冒充。**


### 我 §3 那处被纠对了：`reachable` 是 `ast.Assert` 的子集 ⇒ 「假互证」
**`asserts_declared` 数 `finalize` 体直属的 `ast.Assert`；`reachable` 数同一类节点、换一个作用域 ⇒ 一个是另一个加了过滤器 ⇒ 不是两个数。**
**⇒ 而 lead 提的集合形式才是对的**：`expected`（手写意图）↔ `got`（`ast` 扫出）。
**⇒ 补两处它会栽的地方：**
#### 1. `got` 不要用 `ast.unparse(a.test)` 全文，只取谓词名
| 取法 | 重命名形参后 | 误报 |
|---|---|---|
| `ast.unparse(a.test)` ⇒ `V.bool_guard(rec)` | 字符串变 | **会误报** |
| **取调用名 ⇒ `bool_guard`** | 不变 | 不误报 ✓ |
**⇒ 判据第一次误报决定它能否活到有用 —— 而"格式化/重命名导致误报"是最容易发生的那一类。**
#### 2. 非调用的 assert 需要一个统一的表示
**今天三条里，两条是调用、一条是比较式**（`rec[...] == rec[...] or True`）⇒ 若只取调用名，第三条会被记成 `None`。
**⇒ 取法**：`name if isinstance(f, ast.Call) else "<expr>"`，白名单相应可含 `"<expr>"`。
#### 3. 今天的第一次读数（`H 4883f2c7f04b2818`，文件若再变则作废）
```
got = {"bool_guard", "red_guard", "<expr>"}      # 第三条是计数器，本批应消失
expected = {"bool_guard", "red_guard"}          # 写下来的意图
⇒ 本批落完，两边才相等；在此之前它应当是"不等"，而"不等"是对的
```
#### 4. `expected` 为空时必须退休这条检查
**下一批 `bool_guard`/`red_guard` 若一并退休，`expected` 变成空集 ⇒ `got == expected` 在"什么都没扫到"时也成立 ⇒ 又一个扫空当干净。**
**⇒ 与 lead 那条一致：派生 0 ⇒ 该退休的是检查本身。把它写成 `if not expected: return "检查退休"`，而不是放行。**


### 核 lead 的裁定 A：前提成立（`reset` 在 `if not control:` 之外），但 `redcheck_delete.py` 现在驱动了**两个**命令
#### 1. 前提核对（`tools/chat.py` 当前）
| 位置 | 内容 | 在 `if not control:` 内？ |
|---|---|---|
| `cmd_chat` L261 | `leases.reset(i, site="chat.place.fresh")` | **否** ✓ |
| `cmd_chat` L298–301 | `if not control:` → `leases.attach(...)` | 是 |
| `cmd_m1` L570 | `if not control:` | — |
| `cmd_m1` **L578** | `leases.reset(seq, site="m1.mount.before_load")` | **是（在 L570 之内）** |
| `cmd_m1` L587 | `leases.attach(...)` | 是 |
**⇒ lead 的前提对：`cmd_chat` 的 `control` 只删 attach，`reset` 照跑。**
**⇒ 且注意两者不对称**：**同一个 `control` 参数，在 `cmd_chat` 里只删 attach，在 `cmd_m1` 里删掉 reset + attach + load 整段。**

#### 🚨 2. `redcheck_delete.py` 的 `drive` 里有两个命令
```
L73  chat.cmd_chat(control=True)
L81  chat.cmd_m1()
```
**⇒ `cmd_chat` 记 `site1.place`（`site: 1`）；`cmd_m1` 记 `site3.unmount.flow` / `site3.turn_orphan`（`site: 3`）。**
**⇒ 两份日志都落进同一个 `M4C_ASSERT_LOG_PATH` ⇒ `covers_observed` 会是 `["site1", "site3"]`。**
**⇒ 而 `redcheck_delete.py` 声明的 `covers_declared` 是 `["site1"]` ⇒ `coverage_ok` 为 `False` ⇒ 码 5、命中 `coverage_not_met`。**
| 证据 | 读数 |
|---|---|
| `M4C-DELETE-SITE1-base-attempt19.json` | `assertions` 只有 2 × `site1.place`，`covers_observed == ["site1"]` |
**⇒ 即：attempt19 那次 `cmd_m1` 没有被驱动（或没记条目）⇒ L81 是后加的 ⇒ 它会把 `coverage_ok` 从 true 变成 false。**
**⇒ 两条出路**：
| 出路 | 后果 |
| 声明 `["site1", "site3"]` | `coverage_ok` true，但**站点 1 的产物里混进站点 3 的覆盖** ⇒ 判据对象被扩大 |
| **删掉 L81 的 `cmd_m1()`** | **产物只覆盖站点 1 ✓ 与声明的对象一致** |
**⇒ 我倾向后者：一个夹具测一个站点，覆盖集才与判据对象一致。**

#### 3. 对 lead §4「自证第四样」的一条修正
**`rec["attach_executed"] = not control` 记的是**意图**，不是结果** —— 而今晚的主题正是「意图与结果必须分开」。
**⇒ 真正的配置证据是「`attach` 被调了几次」**：由 `chat.py` 在 L301 / L587 各自记一条（或一个计数器）⇒ 产物里是**执行过的次数**，不是「没被禁用」。
**⇒ 判法同今晚那条**：`not control` 与我们自己的代码同源；`attaches_done` 由被执行的那一行产生。


### 🚨 实测：6 个 `_m4c_log` 调用点里 **5 个在 `try` 内** ⇒ 「无默认值 ⇒ TypeError」会被 `except` 吞掉
`tools/chat.py`（`1f9551eccdcfca7a` / 682 行），`ast` 逐调用点查是否有 `Try` 祖先：
```
L155  in_try: False   ← die（唯一在外面的）
L269  in_try: True    ← site1.place
L557  in_try: True    ← site3.unmount.flow (checked)
L566  in_try: True    ← site3.unmount.flow (skipped)
L568  in_try: True    ← site3.turn_orphan (skipped)
L609  in_try: True    ← site3.turn_orphan (checked)
params: [entry]
```
**⇒ 若 `role` 做成无默认为形参：漏写的那 5 处会抛 `TypeError`，而它们各自被外层 `except` 接住。**
**⇒ 结果不是「症状指向漏写那一行」，而是：日志没写成 ⇒ 覆盖缺条 ⇒ 症状又回到 `coverage_not_met`。**
**⇒ 这正是 lead 自己两节前立的那条：`raise` 的接收方是 `except`，不是检查者。** **同一个陷阱，从 `assert` 移到了 `TypeError`。**

### 修法：不给「填 role」的入口，给两个**名字里带 role** 的入口
```
def _crit(id, site, status, **kw):    _m4c_write(dict(kw, id=id, site=site, status=status, role="criterion"))
def _event(id, status, **kw):         _m4c_write(dict(kw, id=id, site=None, status=status, role="event"))
```
| 修法 | 漏写 role 时 | 会不会被 `try` 吞 |
|---|---|---|
| 无默认值形参 | 抛 `TypeError` | **会（5/6 个点）** |
| 默认值 + 检查 | 静默默认 | 不抛，但通过 |
| **两个专用入口** | **结构上不可能** | **没有可抛的东西** ✓ |
**⇒ `_crit` 与 `_event` 各写死 `role`，调用点无从漏写 —— 因为不存在「填 role」的入口。**
**⇒ 且 `die`（L155）走 `_event`：它仍有 `kind: "assertion"`，`die_kind` 那条一个字不用改 ✓**
**⇒ 而 `site=None` 由 `_event` 写死 ⇒ 「事件不进覆盖集」不再是约定，是构造。**

### 一般化
> **要排除「漏写某个键」，最有效的不是把它变成必填参数，而是让它没有可填的地方。**
**⇒ 必填参数把错误推给运行期，而运行期的第一接收者是 `except`；专用入口把错误消灭在调用之前。**


### 🚨 冻结例外：`skipped` 的预期条数应当是 **0**，不是 2 —— 否则三份 SITE3 产物会被判失败
`tools/chat.py` 现在：
```
L580  # 且必须显式记 skipped —— 不得有「默认跳过」路径
L581  _crit({"id": "site3.unmount.flow", "site": 3, "status": "skipped", ...})
L583  _crit({"id": "site3.turn_orphan", "site": 3, "status": "skipped", ...})
```
**⇒ 这两条都在 ~if control:~ 之内（L579 起）⇒ 只有 `control=True` 才产生 `skipped`。**
**⇒ 而 ~run_site3.py~ L70 是 ~chat.cmd_m1()~（无参 ⇒ `control=False`）⇒ 三份 SITE3 产物的 `skipped` 都是 0。**
| 臂 | `control` | `skipped` 实际 | lead 的预期 |
|---|---|---|---|
| SITE3 green / red / inject | `False` | **0** | 2 ✗ |
| DELETE base / deleted | `False`（本次改后） | **0** | 0 ✓ |
**⇒ 按「SITE3 预期 2 条」上线 ⇒ 三份 SITE3 产物会被判「少了的那条去哪了」 ⇒ 而它们其实完全正确。**
**⇒ 正确预期：五臂全部 `skipped == 0` ⇒ 该检查在五臂上全部 `retired`。**

### 而这恰好给 `gates_retired` 第一次真实读数
**本批把两处 `control=True` 都改成 `False`（`redcheck_delete.py` 的 `cmd_chat`，且 `cmd_m1()` 被删）⇒ `if control:` 分支在本批五跑里一次都不会执行 ⇒ `skipped` 恒 0。**
**⇒ 于是「`skipped` 必带 reason」这条检查在本批没有被测对象 ⇒ 它应当产出 `retired`。**
**⇒ 这正是 lead 要的那个区分：`ok`（检查过且通过）与 `retired`（这里没有这种情况）在产物里不同。**
**⇒ 且 `retired` 不像"通过"那样让人放心 —— 它会说"这条检查在本批什么都没看到"。**


### 🚨🚨 `tools/chat.py`（`0007772b5233b662` / 696 行）：`_m4c_write` 是空函数，`_event` 把旧函数体带在自己 `return` 之后 ⇒ **一条日志都写不出去**
```
L79  def _m4c_write(entry):            body = [Expr]  ← 只有 docstring，什么都没做
L83  def _crit(entry):                 body = [docstr, entry["role"]="criterion",  return _m4c_write(entry)]
L89  def _event(entry):                body = [docstr, role="event", site=None, return _m4c_write(entry),
                                               STRING(旧 _m4c_log 的 docstring),
                                               path = os.environ.get(...),           ← 以下全是 return 之后的死代码
                                               bucket.append(entry), ..., return entry]
```
**`ast` 实测：`docstring_only_functions: [("_m4c_write", 79, 1)]`**
**⇒ `_m4c_write` 返回 `None`，不写盘、不 append；`_event` 在走到写盘之前就 `return` 了。**
**⇒ 于是**：
| 后果 | 读数 |
|---|---|
| 日志为空 ⇒ `assertions == []` ⇒ `assertion_failed_in_log = False` | 绿臂恰好 `exit 0`（**碰巧对**） |
| `die()` 走 `_event` ⇒ 红臂也不留条目 ⇒ `die_kind = None` ⇒ `is_red = False` | **红臂 `exit 0` ⇒ 会被读成"判据通过"** |
| `covers_observed = ∅` ≠ declared | 五臂全部 `coverage_not_met` ⇒ `exit 5` |
**⇒ 五跑的读数会是「仪器坏了」，而真实原因是一行代码搬错了位置。**
**⇒ `ast.parse` 过、`py_compile` 过 ⇒ 编译只证语法，不证可达 —— 今晚这条第一次以"整段代码变成死代码"的形状出现。**

### 两条能当场抓到的快闸（都是 5 行 `ast`）
| 检查 | 今天会命中 |
|---|---|
| **任何 `FunctionDef` 的 body 去掉 docstring 后为空** | **`_m4c_write`** |
| **任何 `return`/`raise`/`break`/`continue` 之后还有语句** | **`_event`（L93 之后 19 行）** |
**⇒ 两条都不需要知道业务语义，也不受 `try` 影响。**


### 对齐 sha：我的报告作废（`0007772b5233b662` 已不存在），当前 = `5f9ee41d73d17a72` / 690 行 / 33,139 B
**我读 L79–137，与 lead 的读数逐行一致：**
| 位置 | 现状 | 我先前的说法 |
|---|---|---|
| L79–93 `_m4c_write` | **完整活体**（读环境变量 → append → tmp + `os.replace` → `return entry`） | 空函数 ✗ **作废** |
| L96–106 `_crit` / `_event` | 干净，各 3–4 行 | 19 行死代码 ✗ **作废** |
| **L126–137** | **孤儿函数体：`def` 行丢失，挂在 `_m4c_witness_cells` 的 `return got`（L123）之后 ⇒ 死代码** | 未报到 ✗ |
**⇒ 我拿一个已被覆盖的中间态去报"停跑"，而执行者若照它修，会去修一个不存在的缺陷。这正是我一直在指别人的那件事，这次是我。**

### 两条新判据在**当前 sha** 上的实测（我独立跑，53 个 `.py`）
```
files_scanned: 53
dead_after_return: 1
   ('chat.py', 123, 'Return', 126, 4)      # L123 return 之后还有 4 条语句（L126 起，12 行）
docstring_only: 0
```
**⇒ 与 lead 的读数完全一致 ✓**
**⇒ `dead_after_return` 第一次上线就读到红，而那个红是真的 —— 这是今晚第一条"上线即有效"的判据。**
**⇒ `docstring_only` 读到 0 ⇒ 按你那条规矩，它必须 `retired` 或带预期条数。**

### 补一条：所有"扫全仓"判据必须同时报扫描文件数
**`docstring_only: 0` 有两种原因：真的没有，或扫描器没扫到文件 —— 两者读数相同。**
**⇒ 修法不是给它写一个预期条数（那个数会跟着实现变），而是让扫描器**自报扫描范围**：**
```
{"gate": "docstring_only", "files_scanned": 53, "violations": []}   # files_scanned == 0 => 判失败
```
**⇒ 于是"扫空"在结构上不可能被读成"干净"：扫空时 `files_scanned` 为 0，而 0 判失败。**
**⇒ 这条与「判据必须自证测的是谁」同源：一条扫全仓的判据，它的主体就是它扫过的那些文件。**

### L126–137 两条出路的真实代价
| 路 | 代价 | 交付里要写的 |
|---|---|---|
| **A 补回 `def` 行并接上调用者** | 多一条会跑的新判据 ⇒ **必须配一次人为错误验收**（喂一个被循环漏掉的 dropped seq，它要红） | 「覆盖见证已实现并验收」 |
| **B 整段删除** | 便宜 | **「reset 循环的覆盖未被任何判据证明」** —— 因为它自己的 docstring 写着「唯一的新增信息是覆盖：若循环漏掉某个 dropped seq，L331 不会响，这里才响」 |
**⇒ B 不是"删掉死代码"，是"删掉唯一的覆盖见证并把这条缺口写进交付"。**


### 🚨 覆盖见证者的「唯一新增信息」没有一个可达场景 —— `tools/chat_lease.py` `619a043215035de7`
**`GuardedLeases.reset`（L316–336）实际做了什么：**
```
L327  cells = self.cells_of(seq)
L329  self.sites.setdefault(tag, []).append({"seq": int(seq), "cells_after": cells})
L331  if cells != 0:
L332      raise LeaseError("reset(seq %d) at %s left %d cells ...")
```
**⇒ 于是见证者（`chat.py` L569–570）声称的两个场景都不通：**
| 它声称抓的 | 实际谁先响 | 结果 |
|---|---|---|
| 循环漏掉某个 dropped seq | **A 判据 `hits != dropped`（chat.py L562–565）** —— 因为 L329 就是往 `sites` 记的那一行，漏一个 seq ⇒ 少一条 ⇒ A 响 | **见证者轮不到**（A 先 die） |
| reset 跑过但没清干净 | **L331 直接 `raise`** | **见证者轮不到** |
**⇒ 两个候选消费者都已存在 ⇒ 它是「一事实两写」的第三份 ⇒ 按「判据的价值 ≈ 它能证伪的东西的数量」，这个集合是空集。**
**⇒ 而 `witness_zero_feed.py` 那四条喂错产物证明的是「`die` 这条路能红」，不是「这条见证有信息量」。**

### 这修正了 lead 的 §4 前提
**「B 删掉它就是删掉唯一的覆盖见证」这句话不成立：覆盖由 A 承担，而 A 的依据（`leases.sites[tag]`）正是 L329 —— 与见证者读的是同一份记录。**
**⇒ 所以撤掉它不留缺口；交付里应写「dropped 覆盖由 `m1.unmount.after_detach` 的 sites 调用流判据承担（`chat.py` L562–565）」，而不是「覆盖见证已实现」。**
**⇒ 这也解释了为什么 ① 那一臂（`green-dropnonempty`）无论结果如何都不能证明它：** **它不响的原因可能是「A 已经先管了」，而不是「它在正确对象上不误报」。**


### `cells_of` 不会抛 —— 它把内部错误折成 `1`（`kvmem/m2_visibility/m3/m3_lease.py` L125–130）
```
L125  def cells_of(self, seq):
L127      try:
L128          return int(self.eng.n_tokens(int(seq)))
L129      except Exception:            # noqa: BLE001
L130          return 1                 # unknown: do not block on it
```
**⇒ lead 那句「方法调用可以抛 ⇒ 不是零副作用」不成立：它吞掉一切异常并返回 1。**
**⇒ 但真实形态更坏**：**任何内部错误都会被折成 `cells_of == 1` ⇒ 见证者 `got != 0` ⇒ `die("cells_of(seq N) = 1, expected 0")` ⇒ 仪器坏被报成判据红。**
**⇒ 而两种来源在产物里长得一样：一个真的没清干净，一个量不到。**
**⇒ 这比"抛了被 `try` 吞"更糟：抛了被吞 ⇒ 见证者静默跳过（可发现"什么都没做"）；折成 1 ⇒ 它会**主动报一个假的判据红**（`exit 1`、`is_red: True`）。**

### 而这条不只关见证者：主保证 L331 读的是同一个函数
**`GuardedLeases.reset` L327 `cells = self.cells_of(seq)` ⇒ L331 `if cells != 0: raise`。**
**⇒ 于是「reset 之后 cells==0」这条主保证，在 `n_tokens` 出错时会被报成「没清干净」而不是「量不到」。**
**⇒ 它不是缺失被读成通过，是**量不到被读成红** —— 方向安全，归属错误。**
**⇒ 便宜修法**：`cells_of` 出错时不要把 1 当读数；返回 `None` 或抛一个专用异常，让调用方记 `instrument`，而不是让它冒充判据。
**⇒ 交付里对这一条应写**：「`dropped` 路径上所有 cells 读数都经过一个出错即返回 1 的函数 ⇒ 其判据红有两种来源，产物不可区分」。
