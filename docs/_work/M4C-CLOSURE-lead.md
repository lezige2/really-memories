# M4-C 闭项判决：M4-C-4 池泄漏臂（lead · 2026-10-25 17:40 本地）

> 承接 `M4C-VERDICT-lead.md`（`d7eb117d5838fb6a`）。本轮只加一件事：**M4-C 唯一未闭的实质项 M4-C-4**。
> 不改码、不跑引擎；审计 = 只读复算（sha16/字段/源码行序/变体逐行）。
> **审计链披露**：预登记由 inspector 写（`INSPECTOR-M4C-P3.md` 的 `7a6ee81d6b09c6b7`，落盘时点盘上 0 产物，先于 b10）；产物落地后它独立写 §2（`3f836dd6eae2bea8` / 16,561 B，17:34:58 落盘并回报），与本文件 17:36:12 的 lead 自审**同判"通过"、数字逐项一致 ⇒ 本轮双算成立**。它的 §3（`523b646c9350bc0e`）对本文档提的 4 条已按下面改完。

---

## 1. 新增身份（先签台账，再签读数）

| 项 | 值 | 出处 |
|---|---|---|
| b10 台账 | `80dedabcfcb992b8` / 1333 B · **10 文件 10/10 复算相符** · `verify_landed("b10")==0`（lead 亲跑） | `out/LANDED-b10.json` |
| 新夹具 | `run_m4c4.py` = `4fef084ccee39a45` / 10187 B（已登记 `land.py` FILES + `LANDED_FILES`） | b10 台账 |
| 被测源码 | `tools/chat.py` 仍 `cb70be52eef253fa`（b10 台账内），**一字节未动**；b09 六份产物未动 | 实读 |
| 快闸 | `SELFCHECK-409d2c82.json` `12af1aede278361b` / 2041 B，进程 exit 0 / PASS；扫描面 13→14（新文件 0 命中），step13 仍 `(311,True),(605,True)` | 执行侧报 + 产物 |
| 变体 | 磁盘 `tmp/variants/chat_site3_deleted.py.snap` = `0c149c11f3d8a0d0`，700 行；与 `chat.py` **去行尾后逐行 diff = 1 行**（L562 `leases.reset(seq, site="m1.unmount.after_detach")` → `pass  # M4C-DELETED-SITE-3`） | lead 逐行复算 |

## 2. 两臂读数

| 臂 | 产物 / sha16 / B | orphan_turn | max_orphan | engine_after（引擎实例） | chat_n | die_events | exit |
|---|---|---|---|---|---|---|---|
| green（不删） | `M4C4-green-b10-m4c4-green-fd9b6f9f.json`<br>`08a197d2da7322cf` / 4173 | t2 **0** · t3 **0** · t4 **0** | **0** | `seq0:[141,4236] seq1:[0,-1] seq2:[0,-1]` | `[0,63,108]` | **0 条** | 0 |
| deleted（删 L562） | `M4C4-deleted-b10-m4c4-deleted-1b599550.json`<br>`4ada6cec7621b660` / 5537 | t2 **0** · t3 **36**（seq2） · t4 **86**（seq1 50 + seq2 36） | **86** | `seq0:[141,4236] seq1:[50,4095] seq2:[36,4031]` | `[0,63,108]` | 6 条（全 role=exhibit） | 0 |

`is_red` 由 `max_orphan>0` 推出（`run_m4c4.py:180`），`expected_red=(mode=="deleted")`；两臂 `observation_arm/die_bypassed=true`，`die_events` 不进判据。
deleted 的 6 条 die：t3「范围断言 hits=[] != dropped=[2]」+「承重断言 `cells_of(seq 2)=36, expected 0`」+「漏清断言 orphan=36」；t4 同形（seq1=50 / orphan=86）。

## 3. 审计：按预登记 `INSPECTOR-M4C-P3.md` §1.2 六条逐条（先写死的那六条，不改）

| # | 项 | 判 | 依据 |
|---|---|---|---|
| a | 两臂唯一差异 = 删 site3 那一行 | **过** | 变体 vs `chat.py` 去行尾后 diff=1 行（L562）·700/700 行·`variant_sha16 0c149c11` 与磁盘一致·`deleted_line_no 562`·green 的 `variant_sha16`=原文件 `cb70be52` |
| b | 逐 turn 记且 `max_orphan==max(数组)` | **过** | `orphan_turn` 3 条 = 实际打印轮 3 轮（turn1 `want==prev` 不打印，源码 `chat.py:547/610-631`）；`max(0,36,86)=86` |
| c | `chat_n` 与 orphan 解耦 | **过** | 两臂 `chat_n` 逐项相同 `[0,63,108]`；`orphan_cells` 键 ⊂{1..7}（无 seq0）；green orphan 恒 0 而 chat_n 递增 |
| d | 观测臂标注、die 不当读数 | **过** | 两臂 `observation_arm/die_bypassed=true`；`is_red` 只由 orphan 推；`die_events` role=exhibit；`coverage_ok` 由 `orphan_turn` 非空推出 |
| e | self-evidence + batch | **过** | 两臂 selfev 均 `(T,T,T)`；`batch_id=b10`；`harness_sha16` 首段 `4fef084c` = b10 里 `run_m4c4.py`；`sampled_at` 09:25:43Z / 09:26:55Z 晚于台账 ts 09:25:32Z |
| f | 数字自洽 | **过（一处命名漂移，见下）** | `sum(orphan_cells)==orphan` 两臂逐轮全真；`orphan_leak==(max>0)`；`engine_after` 与末轮 `orphan_cells` 一致（`{1:50,2:36}`）；**但预登记写的 `expected_leak` 字段在产物里叫 `expected_red`**（语义同：green F / deleted T = `mode=="deleted"`），按映射核过 |

**f 的偏差必须写出来（不藏）**：预登记的字段名与产物字段名不同。这不是判据放宽——语义逐位对上；但按纪律应记 **G15 命名漂移**，且下一批预登记应"先看产物 schema 再写字段名"或显式写"若实现用等价字段名，需在审计里逐位映射"。

**预登记 §1.3 不可签条件**逐条未触发：deleted `max_orphan=86>0`（不是 0）· green `max_orphan=0`（阴性对照好）· bypass 可解释（`chat_n` 相同 + 每轮 `mounted_seqs==want` + 变体只差 1 行）· `engine_after` 可读 · die 未当验收读数。
**§1.5 两条风险**（inspector 预判"不污染/可用"）：由读数证实——两臂 `chat_n` 与 `seq0 engine_after=[141,4236]` 完全相同；打印点核过源码：`chat.py:622-623` 打印在 `chat.py:587-608` 挂载循环**之后**、`chat.py:624` 的 `if` 与 `chat.py:625-626` 的 `die` **之前**。

---

## 4. 判

### 4.1 M4-C-4 = **通过**

**删掉 `chat.py:562` 的 `leases.reset(seq, site="m1.unmount.after_detach")` ⇒ 被丢弃 seq 的 cell 不被回收**：orphan 逐轮 `0 → 36 → 86`（引擎读数），run 后引擎仍持 `seq1:[50,4095] / seq2:[36,4031]`；不删则三处全 0、`seq1/seq2=[0,-1]`。
**签名范围**（预登记 §1.6 先声明的边界，照签）：只到"cell 不被回收"这一级；**不签**池耗尽（长跑未测）、**不签** cell 复用（`kv_unified` 分支未测）、**不签**其他三站的池行为。

### 4.2 对上一版判词的更新（只改这两格，其余不动）

| 判据 | 旧 | 新 | 依据 |
|---|---|---|---|
| #3 v2①-a 的 `cells_of` 级读数 | 未做 | **通过** | b10 观测臂里 `cells_of(seq 2)=36`、`cells_of(seq 1)=50` 两次真红（b09 验收臂里被 A 判据抢先 abort，是仪器顺序缺陷，见 G16） |
| #9 M4-C-4 池泄漏 | 未做 | **通过** | §4.1 |

**M4-C 的实质问题现在可以回答**（这是整条 M4-C 线要的东西）：
> **这些 `leases.reset` 确实有承重者：站点 3 的那一处承重，承重对象是 cell 池不泄漏**——删掉它，被丢 seq 的 cell 留在池里（36→86 tokens × 104,448 B/token ≈ **3.6→8.6 MiB**，即 3.8→9.0 MB），且没有下游读者会把它们清掉（`kvshim_load` 只在 load 时清自己那个 seq，而被丢 seq 不再 load）。
> **不承重于"下游可观测后果"**（无读者）；**site1 实测未观察到破坏且该臂判别力=0；site2/site4 未实测**（判据按读码作废，见 §4.3）——四站里 **1 站证到后果级**。

---

### 4.3 四站总表（M4-C 的实质问题，逐站了结）

判法统一：**该站 reset 之后，是否还有一次 `load_into`？** 有 ⇒ `kvshim_load` 自己先 `reset`（`kvshim.cpp:573`）⇒ 删掉本站 reset 在引擎侧无后果 ⇒ 该站"承重断言"的红**不可构造**（判据前提不成立 ⇒ 作废）；没有 ⇒ cell 留池 ⇒ 承重。

| 站 | 代码位置 | 紧随动作 | 引擎侧后果（实测/可核） | 判 |
|---|---|---|---|---|
| site1 `chat.place.fresh` | `chat.py:270` | `:272 ms.load_into` | 删行后**未观察到引擎侧后果**（b09 DELETE 两臂 `loads` 逐字段相同、无 die）；源码结构上 load 内部先自清（`kvshim.cpp:573`）⇒ 后果被 shim 吸收（**源码推断**） | **承重性该臂不可判**（G1：reset 与 `pass` 在本路径观测面不可区分）；"删掉必须红"判据作废（红形态不可构造） |
| site2 `slots.place.fresh` | `chat.py:386` | `:388 ms.load_into` | 未实测（仅 7B 旧臂"未红"，不作当前身份）；结构同 site1 | 同上（判据作废）；**不签"不承重"** |
| site3 `m1.unmount.after_detach` | `chat.py:562` | **无** | **实测有**：cell 留池，deleted orphan 36→86（≈3.6→8.6 MiB），引擎 `engine_after {1:[50,4095],2:[36,4031]}`；green 全 0 | **承重（池不泄漏）** |
| site4 `m1.mount.before_load` | `chat.py:595` | `:598 ms.load_into`（前一步刚 detach） | 未单独跑；结构同 site1；DESIGN §2：结构性不可掩 + 被 site3 掩码 | 同上（判据作废，ledger 已判） |

**一句话总结（M4-C 的答案，签的与不签的分开写）**：
- **签**：`m1.unmount.after_detach` 这一处 `leases.reset` **承重**——它是四处里唯一"后面没有 `load_into` 兜底"的清理点，承重对象是 **cell 池不泄漏**（删 → 36→86 tokens 留池，不删 → 0）。
- **签**：site1/2/4 的"删掉必须红"判据**作废**——源码上它们的下一句就是 `ms.load_into`，而它内部先 `kvshim_load` 自清（`kvshim.cpp:573`）⇒ 红形态（`n_tokens` 翻倍）**在架构里不可构造**；这是**读码结论**，不是实测。
- **不签**：site1/2/4"不承重/冗余"（该臂对承重性判别力=0，见 G1）；"契约守门"是**解释性推断、未测，不进签字**；池耗尽、cell 复用也未测。

---

## 5. 缺口增补（承 `M4C-VERDICT-lead.md` §7 的 G1–G14）

- **G5 修正**：`cells_of` 见证者**不是坏的**——b10 观测臂里它两次正常红（`cells_of(seq 2)=36`）。b09 验收臂看不到它，是因为**A 判据先 `die` 抢先 abort**（顺序缺陷）。⇒ G5 从"未复现"降级为"被掩盖"，并新开 G16。
- **G15 命名漂移**：预登记写 `expected_leak`，产物写 `expected_red`（语义等价）。本轮按映射核过；下批预登记须先对齐 schema 或显式写映射规则。
- **G16 验收臂顺序缺陷**：验收路径上 A 判据（`chat.py:566-568`）先 die，导致 `cells_of` 级与 `orphan` 级读数在验收产物里永远看不到。**建议下一批小改**：A 判据改为"记录后继续"或把 `_crit` 的读数先落（不改判据语义、只改记录顺序），使一份验收产物同时带三级读数。
- **G17 小**：green 臂 `src_line_count/variant_line_count = null`（无变体），行数只能由 `chat.py` 外部核（700）；不影响判。
- **G18 审计链（已核正）**：预登记先于产物（`7a6ee81d`）；inspector 的 §2 于 **17:34:58** 落盘（`3f836dd6` / 16,561 B），本文档写于 **17:36:12** ⇒ **§2 早于本文档**，"lack 审计"的说法不成立。两方独立同判"通过"、六条横切与全部数字逐项一致 ⇒ 本轮双算成立（与 b09 同规格）。
- **G19 单通道（inspector 指出，接受）**：`orphan` 与 `engine_after` **同出 `eng.n_tokens`** ⇒ 只能签"两个测量点一致"，**不签**"两条机制独立读数"。
- **G20** `arm-m4c4-*.log` 未记进程码；产物 `exit=0` 自洽，但"进程 0"不可由产物复算（与 G3 同族）。
- **G21** 快闸 `products_cited` 仍是 b09 两件，**未覆盖** `out/m4c4/` 两份（观测臂不在 `out/M4C-*.json` 谱系）⇒ 快闸对本臂是"未覆盖"，不是"通过"。

---

## 6. 下一步（M4-C 剩余，按代价排序）

1. **G16 小改**（半天内）：让验收产物同时带 A/cells_of/orphan 三级读数——否则以后每份验收产物都要二次跑观测臂。
2. **site1 二次放置夹具**（DESIGN §1：同引擎放两遍，期望 `2n`）——补第一站；**site4 脏 seq 夹具**（DESIGN §4）——补第四站；site2 同法。
3. 三站补完后，M4-C 可按"四站承重表"定稿（每站一行：承重/未观察到/无位置），而不是靠一条"四条全红"的作废判据。
4. HANDOFF §5 九项（`except OSError: pass` 三处、`cells_of` 折 1、见证者 `no_discrimination`、`redcheck.py` run_id+tag、`stale` 谓词、M4-C-3 skip 出声、restore 定义）。

---

## 7. 签署

| 项 | 内容 |
|---|---|
| 签署人 | lead |
| 签署范围 | M4-C-4 = **通过**（"删 L562 ⇒ 池不回收"，orphan 36/86 + 引擎 `engine_after`；阴性对照 green 全 0）· v2①-a 的 `cells_of` 级 = **通过**（b10 观测臂两次真红）· **四站总表**（§4.3）：site3 承重（池，**实测**）；**site1 实测**未观察到引擎侧后果；**site2/site4 未实测**，其判据按读码作废（紧随 `load_into` 自清）；三站**承重性该臂不可判**（G1） |
| 未签 | site1/2/4 的"不承重/冗余" · "契约守门" · 池耗尽 · cell 复用 · 两条机制独立读数（单通道，G19） · 快闸覆盖本臂（G21） |
| 依赖 | 无（判据无作废理由；装置=b10/14B/本夹具） |
| 可复算 | b10 10/10 · 两臂 sha16 与字段 · 变体逐行 diff · 源码打印/die 行序 · `verify_landed("b10")==0` |
| 审计 | 预登记先于产物（inspector `7a6ee81d`）· 审计双算：lead 自审 + inspector §2（`3f836dd6`）独立同判 |