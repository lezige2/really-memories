# INSPECTOR-M4C-P3 —— M4-C-4 池泄漏臂：预登记 + 独立审计（inspector）

> §1 为**预登记**，写定于 2026-10-25 17:20 本地（=09:20Z），**先于 b10 台账与两臂产物**。
> 写定时点盘上核验：`kvmem/m4c_leases/out/` 下 `b10` / `M4C4` 命中 **0 个**；`run_m4c4.py` **不存在**（executor 尚在写）。看到数据后**不许回改 §1**；判不掉的口径进 §2 的 G 清单。
> §2 为产物出现后的独立审计（另起）。

---

## 1. 预登记（先写死）

### 1.0 判据来源与我的独立读法（不抄 lead 措辞）

- **立案文本**：`CONSOLIDATION-LEDGER.md:4111`「站点 3 **确实承重**，承重对象是「cell 池不泄漏」⇒ **M4-C-4 立案**」；`:4113`「承重对象是池容量，不是任何读者看到的正确性」；`:4037`「被丢 seq 的 cell 不回收 ⇒ 长跑下可能耗尽」。
- **量**：`HANDOFF-M4C.md` §5 第 8 项给出定义 —— `orphan = sum(int(eng.n_tokens(s)) for s in range(1, N_SEQ) if s not in mounted_seqs)`，**同时记 `chat_n`**。
- **纪律 40（不许桩自证）**：orphan 只由 `eng.n_tokens`（引擎侧）产生，**不得**用 `leases.cells_of`/`leases.sites` 作为红读数；`cells_of` 只是 `n_tokens` 的转发（`m3_lease.py:125`），用它等于同一通道读两次。
- **测量点（我从源码核，不抄产物自述）**：`tools/chat.py:610-631` —— 每轮 `if want != order` 分支内，**mount 循环之后**先打印 `[exhibit] orphan=… chat_n=… mounted_seqs=… orphan_cells=…`（L624-625），**再** `if orphan != 0: die(…漏清断言红…)`（L626-628），**再** `_crit(site3.turn_orphan)`（L627-631）。⇒ 打印点 = 本轮挂载后的真实末态（此后生成只动 seq0，不动 block seq 的 cell）；`die` 在打印**之后**，所以 bypass 不影响打印。

### 1.1 判据（先写死，判"通过"的条件）

**M4-C-4 = 「删 site3 的 `leases.reset` ⇒ 被丢 seq 的 cell 不被回收」**，判据落地为三个字段：

1. **红形态**：`deleted` 臂 `max_orphan > 0` 且 `orphan_leak == true`；
2. **阴性对照**：`green` 臂 `max_orphan == 0`（同一夹具、同装置、同 batch，只差删行）；
3. **只读引擎侧**：`orphan_turn[]`、`engine_after` 都必须由 `eng.n_tokens` 产生；产物里**不得**出现用租约表读数当红依据。

**通过** = 上述 1+2+3 同时成立 **且** §1.2 六条横切全过。**只判到这个结构级**：不签"池耗尽"（长跑后果未测）、不签"复用同一 cell"（`kv_unified` 分支未测）。

**预登记预期值**（用于审计对照，不当作放宽/收紧的尺子；若不符按 §1.3 判）：

| 量 | green（预期） | deleted（预期） |
|---|---|---|
| `orphan_turn` 条数 | 3（turn 2/3/4；turn1 `want==order` 不打印） | 3 |
| `orphan_turn.orphan` | `[0, 0, 0]` | `[0, 36, 86]`（turn3 丢 seq2=36；turn4 丢 seq1=50，累计 86） |
| `orphan_turn.chat_n` | `[0, 63, 108]` | **同 green**（bypass 不得改生成） |
| `max_orphan` | `0` | `86` |
| `engine_after` | `{seq1:0, seq2:0}`（pos_max −1） | `{seq1:50, seq2:36}`（pos_max 仍在） |
| `die_events` | 空 | ≥2（turn3：A 判据 + witness_zero；turn4：A 判据 + witness_zero，共 4 条左右） |

### 1.2 六条横切（判法 + 什么算不通过）

| # | 横切项 | 判法（文件:行/字段） | 不通过的样子 |
|---|---|---|---|
| a | 两臂唯一差异 = 删 site3 那一行 | 磁盘变体与 `tools/chat.py` 逐字节 diff，**只差 1 行**、行数都 700；产物 `deleted_line_no=562`、`variant_sha16` 与磁盘变体一致；green 臂 `variant_sha16` = 原文件（`cb70be52` 或 b10 后的新 sha，以 b10 台账为准） | 差异 >1 行、行数≠700、variant_sha16 与磁盘不符、green 臂也带 variant |
| b | 逐 turn 记且用 max | `orphan_turn` 是数组、条数 = 实际 `want != order` 轮数（预期 3）；`max_orphan == max([t.orphan])`，**不是**只记末态 | 只给一个标量、或 `max_orphan` 与数组 max 不符、或条数与源码打印点不符（编造重复轮） |
| c | `chat_n` 与 orphan 解耦 | 两臂 `chat_n` 序列**逐项相同**（`[0,63,108]`）；`orphan_cells` 的键**不得含 0**（seq0 是对话 seq，不是池）；green 臂 orphan 恒 0 而 chat_n 增长 | 两臂 chat_n 不同、orphan_cells 含 seq0、orphan 与 chat_n 同步（说明排除式没命中） |
| d | 观测臂标注、die 不当读数 | 两臂 `observation_arm: true`、`die_bypassed: true`；`is_red` 必须 = `orphan_leak`（或 `expected_red` 口径），**不得**由 `die_events` 非空推出；产物须写明"不是验收臂" | 缺标注、`is_red` 由 die 事件推出、把 `die_events` 写进 coverage/判定字段 |
| e | self-evidence + batch | 三样 self-evidence（green 臂与 b09 同类：`(T,T,T)`；deleted 臂因预期红，若沿用 b09 口径应为"die 被记录 ⇒ expected"形态，按产物口径核 `is_red==expected_red`）；`batch_id=="b10"`；`harness_sha16` 首段 = b10 台账里 `run_m4c4.py` 的 sha16；`sampled_at` 晚于台账 ts | 任一项缺、或首段等于 b09 的 `805482ea`/`85d3b0b0`（引旧批） |
| f | 数字自洽 | 逐 turn `sum(orphan_cells.values()) == orphan`；`orphan_leak == (max_orphan>0)`；`expected_leak == (mode=="deleted")`；`engine_after` 与最后一轮 `orphan_cells` 一致（同一批 seq、同一读数） | 任一项不成立 ⇒ 读数不自洽；差额出现在 `engine_after` 与 `orphan_cells` 之间 ⇒ 两次读数至少一次不是引擎侧 |

### 1.3 不可签条件（先写死，看到数据不许放宽）

1. **`deleted.max_orphan == 0` ⇒ M4-C-4 = 未通过**（不是作废：cell 池在架构里有位置——两个块各占 50/36 cell，`n_tokens` 可读；删了不回收这件事**可测**，测出来是 0 就是未通过）。
2. **`green.max_orphan > 0` ⇒ 阴性对照坏 ⇒ 未通过**（装置/夹具问题，不是"通过"；先查是不是两臂不满足 a）。
3. **bypass 使读数不可解释 ⇒ 未接上**（并写明哪条读数不可解释）。具体触发子项：
   - (i) 两臂 `chat_n` 序列不同 ⇒ 生成被污染，闭包读数不可比；
   - (ii) 后续 turn 的 `mounted_seqs` 与 `want_sequence` 不符（多挂/少挂/挂错）⇒ 状态失真；
   - (iii) 变体与 `chat.py` 差异 >1 行 / 行数 ≠700 / 删的不是 L562；
   - (iv) 某 turn `orphan ≠ sum(orphan_cells)` ⇒ 打印不是真实末态（或字段拼装错）；
   - (v) 打印点与 `die` 顺序错位（用源码 L610-628 核，不信产物自述）。
4. **`engine_after` 缺失/不可读**：**不单独**把 M4-C-4 判成未接上（orphan 本身已是引擎侧读数），但记 G ⇒ 本轮不得签"两条独立读数一致"，只能签"单通道引擎读数"。
5. **`die_events` 只作诊断**：若产物把 die 当验收读数（d 项），判据形态错 ⇒ 未接上（测的不是后果级，而是调用流级旧口径）。

### 1.4 四态触发表（先写死）

| 判 | 触发条件 | 备注 |
|---|---|---|
| **通过** | deleted `max_orphan>0` ∧ `orphan_leak true` ∧ green `max_orphan==0` ∧ §1.2 a–f 全过 ∧ 只读引擎侧 | 只到"cell 不被回收"这一级；不签池耗尽/复用 |
| **未通过** | 判据跑了、读数可解释，但 `deleted.max_orphan==0`（或 green>0） | 未通过要求"试了没红"的读数；本臂就是试了 |
| **未接上** | 位置在（池、`n_tokens` 都可读），但本次读数不可解释：§1.3-3 任一子项 | 写明哪条读数不可解释 |
| **未做** | 两臂产物/台账缺失，或 `orphan_turn`/`max_orphan` 字段没落地（B 没接上） | 与"未接上"的区别：未做=读数根本没产生 |

> 判据作废不进四态：本判据**没有作废理由**（`kvshim_load` 自清只抹掉"叠 cell"这条后果，不抹掉"池不回收"——被丢 seq 不再 load，自清不会碰它）。

### 1.5 我先点破的设计风险（lead 要求的两条 + 我自己一条）

**(a) `die` 被 bypass 后控制流继续，会不会让后续 turn 的引擎状态失真？**
- 机制上**不应该**：`die` 是纯观察（print + `raise SystemExit`），bypass 成"记录并返回"后，控制流按原顺序继续，状态变更仍只有被删的那一行；`mounted` 的更新、`order` 的赋值、mount 循环都在 die 之前/之后的固定位置，不由 die 决定。
- 但**必须用读数证明，不靠推理**：判法 = 两臂 `chat_n` 逐项相同 + 每轮 `mounted_seqs` 与 `want_sequence` 一致 + 变体只差 1 行。这三条任一不过 ⇒ 按 §1.3-3 判**未接上**。
- 我的预判：**不会污染**；预期 deleted 的 `chat_n` 与 green 完全相同（`[0,63,108]`）。

**(b) `[exhibit]` 是 `cmd_m1` 自己打的：die 之后还会打吗？打的是不是本轮真实末态？**
- 源码顺序（`chat.py:610-631`）：`seqs_after`/`dropped` 展品 →（`if not control`）算 `mounted_seqs`/`orphan_cells`/`orphan`/`chat_n` → **打印 orphan（L624-625）** → `if orphan != 0: die`（L626-628）→ `_crit`。⇒ 打印在 die **之前**，bypass 与否都会打；打印点在本轮 mount 循环**之后** ⇒ 是"挂载后、生成前"的真实末态（生成只动 seq0，不动 block seq 的 cell）。
- 判法 = 用源码行序核（不信产物自述）+ 逐轮 `orphan == sum(orphan_cells)` + 与 `engine_after` 一致。若打印点实际在 mount 之前/之后错位（源码与产物矛盾）⇒ 未接上。
- 我的预判：**可用**。

**(c) 我自己加的一条：`orphan_turn` 条数不是 4 而是 3。**
- turn1 `want==order==[]` ⇒ 不进入该分支 ⇒ 不打印。产物若给 4 条（声称 turn1 也有），须核是不是编造/重复；若给 3 条，**不是缺陷**。审计按"条数 = 实际 `want != order` 轮数"判，不按 4 判。

### 1.6 边界（预先声明不签的东西）

- 不签"池耗尽"（长跑/多轮耗尽未测）、不签"cell 被复用"（`kv_unified` 分支未测）、不签"其他三站的池行为"（本臂只测 site3）。
- 不引 b06/b08 旧读数；不拿 b09 六臂读数当本臂证据（装置同、批次不同）。
- 本预登记**不预判最终四态**（只写判法）；最终判在 §2 给。

---

## 2. 审计（17:29，b10 产物落地后；§1 一字未改）

### 2.0 独立复算（先算字节，再读内容）

| 文件 | 我的 sha16 | bytes | 结论 |
|---|---|---|---|
| `out/LANDED-b10.json` | `80dedabcfcb992b8` | 1333 | **10/10 逐份相符**；`samples=2`/`sample_gap_s=32`/`samples_identical=true`；`verify_landed("b10")==0`；含 `run_m4c4.py` `4fef084c` |
| green 臂 | `08a197d2da7322cf` | 4173 | 与 lead 报值一致 |
| deleted 臂 | `4ada6cec7621b660` | 5537 | 与 lead 报值一致 |
| `out/SELFCHECK-409d2c82.json` | `12af1aede278361b` | 2041 | 12 gates passed + step11 retired；`self_sha16=c14c5c82`、`verdict_sha16=f181518b` 均等于 b10 台账两值 |

### 2.1 预登记 vs 实现（逐项对照）

| 量 | 预登记（§1.1） | green 实测 | deleted 实测 | 判 |
|---|---|---|---|---|
| `orphan_turn.orphan` | green `[0,0,0]` / deleted `[0,36,86]` | `[0,0,0]` | `[0,36,86]` | ✓ 逐值命中 |
| `max_orphan` | 0 / 86 | 0 | 86 | ✓ |
| `chat_n` 序列 | 两臂相同 `[0,63,108]` | `[0,63,108]` | `[0,63,108]` | ✓ |
| `engine_after` | green `{1:0,2:0}` / deleted `{1:50,2:36}` | `1:[0,-1],2:[0,-1]` | `1:[50,4095],2:[36,4031]` | ✓ |
| `die_events` | ≥2 | 0 | 6 | ✓（≥） |
| `orphan_turn` 条数 | 3（turn 2/3/4） | 3 | 3 | ✓ |

### 2.2 六条横切（一行一条）

- **a 两臂唯一差异 ✓**：变体与 `tools/chat.py` **逐行 diff = 1 行**（L562 `leases.reset(seq, site="m1.unmount.after_detach")` → `pass  # M4C-DELETED-SITE-3`），700/700；`deleted_line_no=562`；`variant_sha16=0c149c11f3d8a0d0` **= b09 同臂快照字节（该文件被本次重写后仍 0c149c11/33597 B）**；green `variant_sha16=cb70be52`（原文件）。
- **b 逐轮 + max ✓**：3 条（turn 2/3/4）；`max_orphan` 0/86 == `max(orphan_turn.orphan)`；给了数组不是末态标量。
- **c 解耦 ✓**：两臂 `chat_n` 逐项相同 `[0,63,108]`；`orphan_cells` 键 = 1..7（**无 seq0**）；green orphan 恒 0 而 chat_n 增长；deleted chat_n 相同而 orphan 变 ⇒ 排除式没命中对话增长。
- **d 标注 + die 不当读数 ✓**：两臂 `observation_arm=true`/`die_bypassed=true`；`is_red := max_orphan>0`（`run_m4c4.py:9` 写死，代码实施同源），`die_events` 只进 exhibit（6 条仅记录、未进 coverage/判定）；`exit` 由 `is_red is not expected_red` 判（green 0 / deleted 0）。
- **e self-evidence + batch ✓**：两臂 `selfevidence=(T,T,T)`；`batch_id="b10"`；`harness_sha16` 首段 `4fef084c` = b10 台账 `run_m4c4.py`；`sampled_at` 09:25:43Z / 09:26:55Z 均晚于台账 ts 09:25:32Z；`identity_cross_check="ok"`。
- **f 数字自洽 ✓**：逐 turn `sum_matches=true`（36=36；86=50+36）；`engine_after` 与末轮 `orphan_cells` 一致（seq1=50、seq2=36）；`expected_leak==orphan_leak==(mode=="deleted")`；两臂 seq0 `engine_after` 同为 `[141,4236]`。

### 2.3 §1.3 不可签项逐条排除

1. deleted `max_orphan=86>0` ⇒ **不触发**"未通过"。
2. green `max_orphan=0` ⇒ 阴性对照成立。
3. bypass 不可解释五子项全不触发：(i) 两臂 chat_n 相同；(ii) 逐 turn `mounted_matches_want=true`；(iii) 变体 1 行差异、700/700；(iv) 逐 turn `sum_matches=true`；(v) 源码打印点在 `die` 之前（`chat.py:610-631`），且 `stdout_exhibit_lines=3` = 应打印轮数 3。
4. `engine_after` 在 `eng.close()` 前真读、可读 ⇒ 不记缺口，另得第二个测量点。
5. die 未当读数（见 2.2-d）。

### 2.4 两条风险结论（lead 指定用读数证明）

- **(a) bypass 未污染 ✓**：两臂 `chat_n` 逐项相同 + **seq0 `engine_after` 同为 `[141,4236]`** + 逐 turn `mounted_matches_want` + 变体只差 1 行 + 两臂 `orphan_turn` 轮集相同 ⇒ 生成与挂载均未被 bypass 改变；两臂唯一差异只出现在 cell 占用（正是被删那一行的效应）。
- **(b) `[exhibit]` 可用 ✓**：打印点在 mount 循环之后、`die` 之前；逐 turn 求和自洽；与 close 前 `engine_after` 一致（turn4 86 = 50+36 = engine_after 的 seq1+seq2）⇒ 打的是"挂载后、生成前"的真实末态（生成只动 seq0）。

### 2.5 四态结论 + 签名范围 + 缺口

**M4-C-4 = 通过**（限：**cell 池不回收**这一级；单通道引擎读数）。

**可签的一句**：「删 L562（`m1.unmount.after_detach` 的 `leases.reset`）⇒ 被丢 seq 的 cell 不被回收：turn3 `orphan=36`（seq2）、turn4 `orphan=86`（seq2 36 + seq1 50）；同夹具同装置不删 ⇒ `max_orphan=0` ⇒ 可红可绿成立。」
**不签**：四处 reset 都承重 / 池耗尽 / cell 复用（`kv_unified`）/ 其他三站的池行为 / 快闸覆盖本臂。

- **G1 单通道**：`orphan` 与 `engine_after` 同出 `eng.n_tokens`（`cells_of` 只是转发）⇒ 不是两条机制独立的读数，只能签"引擎侧单通道 + 两个测量点"。
- **G2 进程码未落日志**：`arm-m4c4-*.log` 只有 stdout，无 rc/起止；产物 `exit=0` 与 `is_red==expected_red` 自洽，但"进程 0"不可复算。建议 executor 补 `echo rc >> log`。
- **G3 `die_events=6`**：每轮 3 条（A 判据 / witness_zero / 漏清断言），比预登记"≥2"多，符合设计（三条断言都会响）；逐条核过 turn 标注正确、无重复。
- **G4 快闸未覆盖本臂**：`SELFCHECK-409d2c82.products_cited` 仍是 b09 两件（m4c4 产物在 `out/m4c4/`，不在 `out/M4C-*.json` 谱系）⇒ 不能签"快闸已验本臂"，只能签"快闸自身 12 gates 通过"。
- **G5 green 臂 `deleted_line*`/`src_line_count` 为 null**（未删行）——与 b09 green 同类，非缺陷。
- **G6 我自己的预登记行号漂移**：§1.0 写"打印 L624-625 / die L626-628"，实测为 **L622-623 打印 / L625-626 die**（差 2 行）。判法不受影响（用的是"打印在 die 之前、mount 之后"的行序关系），记录备查。

### 2.6 给 lead 的 5 条

1. **可签**：两臂 `08a197d2` / `4ada6cec`，台账 `80dedabc` 10/10、`verify_landed==0`。
2. **六条横切全过**（证据见 2.2），预登记预期值逐项命中（orphan `[0,36,86]`、max 86、chat_n 两臂相同）。
3. **两条风险都不成立**：bypass 未污染（chat_n + seq0 engine_after 两臂相同）；`[exhibit]` 是真实末态（打印点在 die 前、挂载后 + 与 engine_after 一致）。
4. **签名范围必须限死**：只签"删 L562 ⇒ 池不回收（36/86）"，不签"四处 reset 都承重"。
5. **三条须写进交付**：G1 单通道、G2 进程码未落日志、G4 快闸未覆盖本臂（否则那三句不能签）。

---

## 3. 闭项文档复核（`M4C-CLOSURE-lead.md` `3ff890525e8599e8` / 11,863 B / 17:36:12）

**判：M4-C-4 与两臂读数部分照签无误；但闭项文档有 3 处须改、1 处小错，其中第 1、2 处会让人读成"本轮没双算"和"判词自相矛盾"。**

### 3.1 必改 1：审计独立性披露自相矛盾且不实（L5 vs G18 L88）

L5 写"inspector 在本轮审计中途失败、未写 §2 ⇒ 本审计由 lead 自做"；G18 写"后 inspector 补写 §2（`3f836dd6eae2bea8`）独立同判 ⇒ 本轮恢复双算"。**两句互斥，且 L5 不实**：我的 §2 于 **17:34:58** 落盘（`3f836dd6` / 16,561 B）、17:35 已回报；closure 写于 **17:36:12**（晚 1 分 14 秒）。
改 L5 为：「预登记由 inspector 写（`7a6ee81d`，先于产物）；产物落地后它独立写 §2（`3f836dd6`，17:34:58）并回报，与 lead 自审同判 ⇒ 本轮双算成立（前两轮模式）。」

### 3.2 必改 2：§4.3 四站表用"**不承重**"，与已签判词 G1 冲突

已签 `M4C-VERDICT-lead.md`（`d7eb117d`）G1（L101）明确：site1"**既不能写'冗余/不承重'**（reset 与 `pass` 在本路径观测面不可区分）**，也不能因此推'所以它承重'**"。closure L73/74/76 却写 site1/site2/site4 **"不承重（非池）"**，L78 又给它们一个未测的正面角色"**契约守门**"。
本夹具对"承重/不承重"判别力 = 0（G1 已裁），四站表只能写"**删行后未观察到引擎侧后果**"；"契约守门"是**解释性推断**（未测），不能进签字范围。改法（三格同改）：「**无引擎侧后果（本夹具/14B 观测）；承重性该臂不可判（G1）**——源码结构上紧随 `load_into`（`kvshim.cpp:573` 自清）⇒ 推断其后果被 shim 兜住；"契约守门"未测，不签。」

### 3.3 必改 3：L62 容量数字（两个数不同单位且 8.8 对不上）

"36→86 tokens ≈ 3.7→8.8 MB @102 KiB/token"：按 104,448 B/token，36 = **3.59 MiB / 3.76 MB**，86 = **8.57 MiB / 8.98 MB**。改「≈ **3.6→8.6 MiB**（3.8→9.0 MB）」。

### 3.4 小错：L43 die 行号

"`chat.py:622` 打印、`chat.py:624-626` die" ⇒ 实际 **L622-623 打印、L625-626 die**（L624 是 `if orphan != 0:`）。我预登记 §1.0 也漂了 2 行，已在 2.5-G6 自记。

### 3.5 照签无误的部分

§1 身份（b10 10/10、`run_m4c4.py 4fef084c`、chat.py 未动、变体 `0c149c11`/L562/700 行）· §2 两臂读数（green `08a197d2` max 0 / deleted `4ada6cec` max 86、`[0,36,86]`、`engine_after {1:[50,4095],2:[36,4031]}`、chat_n 两臂 `[0,63,108]`、die 6 条全 exhibit）· §3 六条横切全过 · §4.1 签名范围限死 · §4.2 两格更新（#3/#9 → 通过；#3 依据已写明是**观测臂**、G16 记录 A 判据抢先 abort 的源码顺序——我核过 `chat.py:567` A 在 `:574` 见证者之前，G16 事实成立）· G15/G16/G17/G19/G20/G21 与我一致。

### 3.6 改版复核（`b5e5e804ceec7b8d` / 12,732 B / 115 换行，按字节）

我 3.1–3.4 四条都已改到位：L5 改成"§2 17:34:58 落盘、本文档 17:36:12 ⇒ §2 早于本文档、双算成立"（且 `523b646c` 被引为我 §3 的字节）✓；§4.3 三格去掉"不承重"、改"未观察到引擎侧后果 + 承重性该臂不可判（G1）+ 源码推断"✓；容量 3.6→8.6 MiB（3.8→9.0 MB）✓；die 行号 622-623 / 624 / 625-626 ✓（挂载循环 587-608 也对）。

**残留词核查**：全文"不承重"4 处、"冗余"2 处，逐处看在**不签栏内**（L74/L81/L113）或已签判词的原话（L63"不承重于下游可观测后果"= `d7eb117d` §5 已签口径）⇒ **§4.3 无违规残留**。

**仍差一格（不阻塞，但签署栏比表格松）**：§7 L112 把三站并列写"site1/2/4 删行后未观察到引擎侧后果"，而 §4.3 自己写了 site2"未实测"、site4"未单独跑" ⇒ 签署栏读起来像三站都测过。改法：「site1 **实测**未观察到引擎侧后果；site2/4 **未实测**，其判据按读码作废（紧随 `load_into` 自清）」；同句"承重性**该夹具**不可判"→"**该臂**不可判"（G1 原口径）。另 L63 "site2/site4 **未做**" 建议改"未实测（判据按读码作废，§4.3）"，否则与 §4.3"作废"读着冲突。

### 3.7 终版（`3309fb25cbd057f9` / 12,799 B / 115 换行）——**可交付**

3.6 那两句已改：L112 =「site3 承重（池，**实测**）· **site1 实测**未观察到引擎侧后果 · **site2/site4 未实测**，判据按读码作废（紧随 `load_into` 自清）· 三站**承重性该臂不可判**（G1）」；L63 =「site1 实测未观察到破坏且该臂判别力=0；site2/site4 **未实测**（判据按读码作废，见 §4.3）」。全文核：`该夹具` 0 处、"不承重"4 处全在不签栏或 `d7eb117d` §5 已签原话、"未做"2 处只在 §4.2 的"旧→新"表（历史格，合法）。**我放行：可交付。**