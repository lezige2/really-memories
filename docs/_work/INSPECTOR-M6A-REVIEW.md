# INSPECTOR 复核：M6a 四条不变量（四态 + 独立可达性）

> **as-of**：`2026-10-25T23:12+08:00`
> **入口锚**：`docs/_work/ANCHORS-CURRENT.md` = `d393d290680fc27a` / 16,847 B（本轮把 `LANDED-g4d` 更新到 `63dd3f49`、`M4C-fixture-rerun` 更新到 `bdafbe8e`，并补 M6a 三行）
> **复核人**：inspector（只读；未改产品/引擎/账本/DB；未重跑 14B；未新造人工红臂）
> **对象**：`kvmem/m2_visibility/m6/out/M6A-REACHABILITY.json` `be9d0a83` / 29,483 B；`M6A-PROBE.json` `ac27641c` / 3,710 B；`kvmem/m2_visibility/chat_lease/LANDED-m6a.json` `91c3d7db` / 3,283 B；`_build_m6a.py` `d025ec71`；`_probe_m6a.py` `62a06006`。
> **独立基线**：`M2-FULL-S1-SPEC-lead.md` `ae2d88ad`；`tools/chat.py` `22081c41`；`verify.sh` rc=0 / ALL PASS 12；`freeze_check.py` FROZEN；`llama.cpp` 600/0/6。

---

## 0. 先说结论（四态）

| 不变量 | executor 四态 | 我的独立判定 | 是否同 | 我的一句话理由 |
|---|---|---|---|---|
| I1 负 delta 静默回收 | 未接上 | **未接上** | 同 | 引擎/工具臂存在下溢路径，但 S1/m1 的 4 个 product 调用在装载后 `base=0`、target>0；这不是“判据作废” |
| I2 共享 cell 无 refcount | 可达（未修） | **可达（未修）；S1 未触发** | 同（措辞需补“引擎/探针级”） | `share` 后只移 seq1，seq2 的 raw cells 区间跟着变；但 S1 没有“块-块共享后再移” |
| I3 pending shift 叠加 | 未接上 | **未接上** | 同 | `pos_add` 两个写入点都在，但当前 product 没有“同一批 cell 先 add 后 move”的调用；不是判据作废 |
| I4 `n_rot` 幂次预检缺口 | 未接上 | **未接上** | 同 | 预检只查 `n_rot == n_embd_head_k`，不查幂次；14B 的 `n_rot=128=2^7` 只是当前模型不触发 |

**“判据作废 ≠ 未通过”**：这三条（I1/I3/I4）都**不是**“作废”，也**不是**“未通过”。它们各自在架构里有位置（引擎 API、`seq_add` 组合、模型装载器），只是**当前 product 调用组合没有接上**；所以只能写 `未接上`。I2 有可跑探针产物，写 `可达（未修）`；不能因为 S1 未触发就改写成 `未接上`。

---

## 1. 证据纪律与独立复算

### 1.1 哈希/命令

| 对象 | 现值 | 核对 |
|---|---|---|
| `M6A-REACHABILITY.json` | `be9d0a83431f47ac` / 29,483 B | 与 `LANDED-m6a` 所记一致；重算 sha256 一致 |
| `M6A-PROBE.json` | `ac27641c8f2d136f` / 3,710 B | 与 `LANDED-m6a` 一致；未重跑 14B，只核脚本/产物字段 |
| `LANDED-m6a.json` | `91c3d7db66ab2d17` / 3,283 B | 四态与 gap 文字已读 |
| `_build_m6a.py` | `d025ec71d90629e9` / 24,220 B | 写入逻辑只读；**没有自动 file:line 校验代码** |
| `_probe_m6a.py` | `62a060067c6183fe` / 8,916 B | raw accessor 构造已读 |

`verify.sh` 现跑 rc=0 / `ALL PASS (12 项)`；`freeze_check.py` `FROZEN (3 files, 3 thresholds)`；`git -C llama.cpp diff --numstat` 仍 `600/0/6`。M6a 未改引擎（这点与产物自述一致）。

### 1.2 一个必须先说的“66”语义

`M6A-REACHABILITY` 的 `items[].call_sites` 合计 **66 条 = I1 53 + I2 5 + I3 5 + I4 3**；它不是“全树 66 个 `repos_local` 调用点”。我按当前盘独立枚举，发现**至少 15 个直接/间接 live `repos_local` 调用点没有进 I1 的 53 条表**（见 §2.4）。因此 executor 若对 lead 说过“66 个调用点 file:line 全部自动校验 bad=0”，这句话在**“全体”与“自动校验”两个词**上都过强：产物和构建器里都没有一个 `bad` / mismatch 校验字段。

---

## 2. I1（负 delta 静默回收）：判定同，证据需三处更正

### 2.1 product 四处的独立推导

前提：块按 0..n−1 保存/载入。`chat.py` 的 product 装载路径都是先 `reset` + `load`，再算 `base`/`cur`：

| 调用点 | 装载后 base | 目标 | delta 符号 | 下溢？ |
|---|---|---|---|---|
| `tools/chat.py:286`（cmd_chat） | `base=pos_max-n+1=0` | `target` 来自 `plan`（≥0；S1/m1 均 >0） | ≥0 | 否 |
| `tools/chat.py:394`（`_place_slots`） | `base=pos_max+1-n=0` | `lo=end-n`，`end=CHAT_START-(i-1)*SLOT` > n（4 block 的 product 范围） | >0 | 否 |
| `tools/chat.py:637`（cmd_m1） | `base=pos_max+1-n=0` | `lo=end-n`，`end=CHAT_START-i*SLOT` > n | >0 | 否 |
| `tools/chat.py:1021`（S1 装载） | `cur=pos_max+1-cell=0` | `base` 来自 planner（S1: 4075 / 4632） | >0 | 否 |

**块 0-based 的现盘证据要分两条线，不能混：**

- m1 / `blocks/` 线：`memory_source.py:346-347`（`reset` 后 `write_at(seq,text,0)`）⇒ DB `memory_block.n_tokens=50/36`；`LANDED-g4d` / `M4C-fixture-rerun` 的 `loads` 实测 `profile 50 / pos_max_after 49`、`project 36 / pos_max_after 35`。这条线是 **m1/夹具**，不是 S1。
- S1 / `m2_v1_14b/` 线：`make_blocks_14b.py:131` 同样是 `write_at(2,text,0,add_bos=True)`；`blocks_14b_pass1.json` 的 `home/project` 为 `pos_max_in_seq=20/17`（cells 21/18）；`dll_smoke_14b.json` 为 `write_home_cells=21 / pos_max_after_write=20`；`S1-real.json` 的 `run.blocks` 实际是 `home base=4075,pos_hi=4096`、`project base=4632,pos_hi=4650`，cells 21/18。

按上面两线分别算，`base=0`（或 `cur=0`）成立，四处 product target>0 ⇒ **I1 在 S1/m1 未接上**。

### 2.2 负值/危险点并不等于下溢

- `tools/chat.py:353`：`repos_local(1,-64)` 之前先 `repos_local(1,+64)`（:352），位置从 64..113 回 0..49，**不会 <0**；它是 product 内的负 delta，不是“工具臂”。
- `kvmem/m2_visibility/m4/m4_write.py:232`：`POS0 - (ASK_ANCHOR - moved)`，目标 POS0=0，回拉到 0..moved−1，安全。
- `tools/m2_v1.py:205`：`2600 - t0`，`t0=3000` ⇒ −400，落点 2600，安全。
- `tools/kvdrift.py:114/133`：`--shift` 是任意 CLI 值；在块位置 0..n−1 上给足够负值**可以**触发 `pos_move` 的 `<0` 分支（`seq[i].reset()` / `used.erase(i)` / 返回仍=idx 数）。这就是“架构里有位置、当前 product 没接上”的证据，而不是人工红臂。
- 工具 `diag_place.py:69` 的 `-t1` 也先 `+t1`；`m4_write`/`m2_v1` 均目标≥0；这些不构成下溢。

### 2.3 与 executor 的分歧（I1）

1. **静态证明把 m1 与 S1 的块/目标串在一起。**
   - 原文：`S1 目标 [4075,4096)/[4650,4668)`。
   - 现盘：S1 `project` 是 **`[4632,4650)`**（`base=4632,pos_hi=4650`，18 cells）；`[4650,4668)` 不是 S1 的 project 区间。
   - 原文：`DB n_tokens=50/36 且 product loads pos_max_after=49/35`；这是 m1 / `M4C-fixture-rerun` 的 `blocks/` 线；S1 是 `m2_v1_14b` 的 **21/18**，不是 50/36。结论仍成立，但证据必须拆成“m1 线 / S1 线”两段。
2. **`why_unreachable` 的“product 路径没有负 delta”是事实错误。**
   - 原文：`product 路径没有负 delta ... 负 delta 只出现在自测工具臂`。
   - 现盘：`chat.py:353` 就是 product 内的负 delta（安全是因为前面 +64）；`m4_write.py:232` 也是负 delta（目标 0）。
   - 应改成：“product 有负 delta，但目标均 ≥0，故不下溢”；“无负值下溢”≠“无负 delta”。
3. **静态证明的行号小错。**
   - 原文引 `m4_write.py:231` 的回拉；当前 `repos_local` 在 **232**（231 是 `leases.detach`）。`call_sites` 表里写 232 是对的，`static_proof` 与表内自相矛盾。
4. **把注释当证明。**
   - `chat.py:241` 只是注释（“Every block is saved at positions 0..n-1”），不是可执行证据；应引 `memory_source.py:347` 或 `make_blocks_14b.py:131`。
5. **调用点枚举不完整。**
   - I1 表只列 53 条；我独立扫到至少 15 个 live 直接调用不在表内（§2.4）。这不改变“未接上”结论，但“全体 auto bad=0”不能签。

### 2.4 我补扫到的 15 个遗漏点（均未发现下溢）

| 文件:行 | 形态 | 安全性 |
|---|---|---|
| `kvmem/m2_7b/runs_mask/_t030_r1.py:67` | `repos_local(SCRATCH, delta)` | 现有 `t030_r1` 产物 `repos_delta=3853`（start=3853 > 0） |
| `kvmem/m2_visibility/m14b_e10_probe/insert_probe3.py:51` | 包装 `repos_local(seq,delta,...)` | delta 由上层负载正目标给 |
| `kvmem/m2_visibility/m2_planner/accept_m2_real.py:128` | `r["base"]-base` | 装载后 base=0、`r["base"]` 正 |
| `kvmem/m2_visibility/m2_planner/accept_m2_real.py:331` | `CHAT_START-base_in_file` | `base_in_file` 由当前 pos_max 得，目标 4096 正 |
| `kvmem/m2_visibility/m2_planner/planner.py:116` | `new_cells` 正目标 | 正 |
| `kvmem/m2_visibility/m3/m3_lifecycle_50.py:238` | `pos_lo-base` | pos_lo 为正、base=0 |
| `kvmem/m2_visibility/m3/m3_lifecycle_redB.py:51` | 同上 | 同上 |
| `kvmem/m2_visibility/m3/_driver_m3.py:127` | `p["pos_lo"]-base` | 同上 |
| `kvmem/m2_visibility/m4/m4_ablate_plate.py:93` | `POS_HI-moved-base` | POS_HI 正 |
| `kvmem/m2_visibility/m4/m4_answer_grounded.py:139` | `ASK_ANCHOR-n-base` | ASK_ANCHOR>n |
| `kvmem/m2_visibility/m4/m4_crosscheck.py:55` | `ANCHOR-n-base` | 同上 |
| `kvmem/m2_visibility/m4/m4_newproc.py:163` | `ASK_ANCHOR-n-base` | 同上 |
| `kvmem/m2_visibility/m4/_probe_place.py:36` | `ANCHOR-n-base` | 同上 |
| `kvmem/m2_visibility/m4/_probe_think.py:51` | `ANCHOR-n-base` | 同上 |
| `kvmem/m2_visibility/m4/_probe_think2.py:41` | `ANCHOR-n-base` | 同上 |

（`tools/chat.py:788`、`tools/chat_lease.py:247`、`tools/kvslots.py:254` 是转发/包装定义，不按裸调用计；`tools/chat.py:241` 是注释。）

**I1 结论**：`未接上` 保持。工具臂 `kvdrift --shift` 确实能下溢，因此不是“判据作废”；product 的 S1/m1 四处不接。

---

## 3. I2（共享 cell 无 refcount）：可达，但不是 S1 触发

### 3.1 独立读码/读产物

- `llama-kv-cache.cpp:475-511` 的 `seq_cp` 在 `s0==s1`（unified 下 `n_stream=1`）只做 `cells.seq_add`，没有 refcount；`kvshim.cpp:162` `cp.kv_unified=true`。
- `_probe_m6a.py:99-125`：
  - A `load(profile)`：seq1 50 cells，raw range 0..49；
  - B `share(1,2)`：seq2 `n_tokens=0`，但 raw `n_cells=50`、`pos_max_raw=49`；
  - C `repos_local(1,+100)`：seq1/seq2 都变 100..149；
  - D `repos_local(1,-1000)`：两者 cells=0、`pos_max=-1`，但 `n_tokens` 仍 50，返回 50；
  - E 重新 load，`+50` 后 share，再 `-50`：都回 0..49，安全。
- D 的“静默回收”是**旁证**，不是 I1 的产品红臂；I2 的可达性由 B/C 本身成立。
- 我未重跑 14B（遵守本轮约定）；`_probe_m6a.py` 当前 sha 与 `LANDED-m6a` 一致，输出字段与脚本构造逐项对得上。`kvshim_seq_cell_scan` 用 probe seq 做 `seq_cp` 后逐位 `seq_rm`，只清 probe 的 bit，不改源 seq；`kvshim_seq_pos_max_raw` 是只读的 `llama_memory_seq_pos_max` 包装。

### 3.2 S1 为什么不触发

S1 的 `home/project` 在 seq 1/2 两个块序列，分别 attach 到对话 seq 0/7；`chat.py:1021` 先 `repos_local(seq, base-cur)`，`chat.py:1027` 才 `attach`。**没有“两块共享同一批 cell 后再移动其中一块”**；`S1-real.json` 的 `counters.share=2` 是块→对话 attach 的两次 `seq_cp`，不是块-块 share。故 `S1 未触发` 成立。

### 3.3 分歧/措辞

- executor 写“可达（未修）”本身可接受；但“可达”是**引擎/探针级**，不是 S1 产品级。建议四态写成 `可达（未修；S1 未触发）`，并在结论里保留“不是产品路径可达”的限定。
- `LANDED-m6a` 的 `gaps.I2_no_product_run` 已诚实写“无 product run”，这点通过。

**I2 结论**：`可达（未修）/S1 未触发`，不是 `未接上`；不涉及作废。

---

## 4. I3（pending shift 叠加）：未接上，product 措辞过宽

### 4.1 源码/调用面

- `pos_add` 写入点确为两处：`llama-kv-cache.cpp:553`（`seq_cp` 跨 stream 的 `v_cells[s1].pos_add`）和 `:927`（`seq_add` 的 `pos_add`）。
- 当前 `kv_unified=true` ⇒ `n_stream=1` ⇒ `seq_cp` 走 `s0==s1` 分支（`:487-511`），用的是 `cells.seq_add`，不是 `pos_add`；`:553` 分支在当前配置不可达。
- `seq_add` 侧：Python 调用点 `tools/kvdrift.py:135`、`tools/diag_place.py:82`、`tools/kvslots.py:518` 之后都没有对同一批 cell 再 `repos_local`；`chat.py` 4 处 product 全用 `repos_local`。
- `kvmem_persist.cpp:497` 还有一个 `llama_memory_seq_add(mem,SEQ_CHAT,...,-n_discard)`；它不是 Python 调用点，且没有“随后 repos_local 同一批 cell”的组合，所以不改变 I3 未接上的判定；但它是“product 全用 repos_local”这句话的反例（若把 `kvmem_persist` 算 product）。

### 4.2 判定

当前没有“同一批 cell 先 `seq_add`（累积 `shift[]/has_shift`）再 `pos_move`”的 product/工具组合；I3 的坏方向（下一次 decode 双重旋转）需要这个组合才出现。引擎 API 在，组合未接上 ⇒ **未接上**，不是**判据作废**（`seq_add` 暴露在 `kvshim.cpp:614`，未来/外部调用可以组合）。

### 4.3 分歧

- “product 全用 repos_local”应限定为“`chat.py`/S1/m1 的 product 路径全用 `repos_local`”；`kvmem_persist.cpp:497` 是 C++ `seq_add` 路径。
- I3 的 5 条 `call_sites` 没列 `kvmem_persist.cpp:497`（以及对应 C++ `pos_add` 链）；这属于枚举不完整，不改变结论，但“全体 product”不能写满。

**I3 结论**：`未接上` 保持；不是作废、不是未通过。

---

## 5. I4（`n_rot` 幂次预检缺口）：未接上，14B 不触发

### 5.1 独立核对

- 同一份日志 `kvmem/m2_visibility/runs_m14b/loadC_ngl99_v.log`：
  - `:78` `n_rot=128`；
  - `:82` `n_embd_head_k=128`；
  - `:1560` `n_rot_k=128, n_embd_head_k_all=128`；
  - 同 log 的 `q8_0` / 48 layer / 4096 cells，确为同一模型/run。
- `:778` 预检条件：
  ```cpp
  if (n_rot_k != 0 && n_rot != n_embd_head_k) { ... return 0; }
  ```
  只查“部分旋转（`n_rot != head_dim`）时拒绝”，**不查 `n_rot` 是否 2 的幂**，也不查 `n_rot_k` 幂次。
- `llama_kv_fwht` 的 assert 在 `:622`：`n>0 && (n&(n-1))==0`；`use_hadamard` 由 `:822` `n_rot_k != 0` 打开；`n_rot=128=2^7` 通过，所以 14B 当前不触发。
- `n_rot_k` 由 `:347` 起从 64 倍增，本身是 2 的幂；缺口在 `n_rot`（fwht 实际参数）与 `head_dim` 的任意模型组合。

### 5.2 判定/分歧

- `未接上`（非作废）：模型装载器/rope 几何是开放的，非幂次 full-head 模型会走 `fwht` 断言；当前 14B 是 128，不触发。
- 若把范围硬缩成“只支持 14B”，才可能论“作废”；按 lead 的“架构里有位置”定义，应保持 `未接上`。
- 行号/值均对；没有需要改的硬事实。仅有文案小问题，不值得单列分歧。

**I4 结论**：`未接上` 保持；不是作废、不是未通过。

---

## 6. 四态纪律复核

1. **没有把“不可达”写成“未通过”**：I1/I3/I4 均写 `未接上`，没有写成 `未通过`；I2 写 `可达（未修）`，没有把 S1 未触发写成未通过。
2. **“可达”有可跑产物**：I2 的 `M6A-PROBE` 有 A–E 五步 `observed`，复算命令/脚本在；我未重跑 14B，但脚本/产物/raw accessor 已核。
3. **“不可达”有行级推导**：I1 的 4 个 product 调用逐点 `base/cur=0` 推导；I3 的 `pos_add` 两处 + unified 分支 + 无混合调用；I4 的 `:778` 预检缺口 + `:622` 断言 + 128 不触发。
4. **“判据作废”只用于前提无架构位置**：I1/I3/I4 都有引擎/装载器位置，故不作废；I2 已可达，故不涉及。
5. **人工路径未升格为红证**：`M6A-PROBE` D 只作 I1 旁证；I1 的四态不靠 D；I2 的可达性靠 B/C，不靠 D。

---

## 7. 与 executor 的分歧清单（按重要性）

| # | 位置 | executor 说法 | 现盘/我的判定 | 是否改四态 |
|---|---|---|---|---|
| 1 | I1 `construction.static_proof[1]` | `S1 目标 [4075,4096)/[4650,4668)` | S1 `project` 是 `[4632,4650)`；`[4650,4668)` 无对应块 | 否，但证据必须改 |
| 2 | I1 `construction.static_proof[0]` | DB 50/36 + pos_max 49/35 是 S1 的产物侧读数 | 50/36 + 49/35 是 m1/`blocks/` 线；S1 是 21/18、`m2_v1_14b` 线 | 否，证据分线 |
| 3 | I1 `why_unreachable` | product 没有负 delta | `chat.py:353` / `m4_write.py:232` 是 product 负 delta（安全） | 否，措辞改“无下溢” |
| 4 | I1 `static_proof[2]` | `m4_write.py:231` 回拉 | 当前 `repos_local` 在 232；`call_sites` 也写 232 | 否，行号改 232 |
| 5 | I1 表 | 66 条/“全体调用点 auto bad=0” | 66 条 = 53+5+5+3；至少 15 个 live 直接调用未入表；构建器无自动校验 | 否，但补枚举/删“全体 auto” |
| 6 | I1 `static_proof` | 以 `chat.py:241` 注释为“块 0..n-1”证据 | 注释不是可执行证据；应引 `memory_source.py:347` / `make_blocks_14b.py:131` | 否，证据换源 |
| 7 | I3 | product 全用 repos_local | `kvmem_persist.cpp:497` 是 C++ `seq_add`；无混合，故不改态 | 否，限定范围 |
| 8 | I2 | 可达（未修） | 可达是引擎/探针级；S1 未触发，建议补限定词 | 否 |
| 9 | `M6A-REACHABILITY`/`LANDED-m6a` | “bad=0”/自动校验 | 产物与 `_build_m6a.py` 无此字段/代码；我的独立 bad 检查只覆盖表内 66 条，表外 15 条另查 | 否，但“auto”不能签 |

**结论**：四态标签我全部认同（I2 加“S1 未触发”限定）；但 I1 的静态证明目前**不能作为“S1 四处恒正”的签署证据**，必须按 §2.3 修正后才可引。I3/I4 无硬事实错误，I3 仅措辞/枚举；I4 不用改。

---

## 8. 附：复核命令（可复算）

```bash
cd /d/llama-mem
sha256sum kvmem/m2_visibility/m6/out/M6A-REACHABILITY.json \
          kvmem/m2_visibility/m6/out/M6A-PROBE.json \
          kvmem/m2_visibility/chat_lease/LANDED-m6a.json \
          kvmem/m2_visibility/chat_lease/LANDED-g4d.json
bash verify.sh                       # 期望 ALL PASS (12 项) / rc=0
python tools/freeze_check.py        # 期望 FROZEN
git -C llama.cpp diff --numstat     # 期望 600/0/6
```

I1 的 S1/m1 分线读数：`S1-real.json` `run.blocks`（home 4075/4096、project 4632/4650，cells 21/18）；`LANDED-g4d.json` `arms.*.loads`（profile 50/pos_max 49、project 36/pos_max 35）；`blocks_14b_pass1.json` `pos_max_in_seq=20/17`；`dll_smoke_14b.json` `pos_max_after_write=20`。

---

### 交付限制

- 本轮 inspector **没有重跑 14B**（遵守只读/不重跑约束）；I2 是脚本/产物核对，不是新采样。
- 未修改任何产品、引擎、账本、DB、`chat.py`；只写本文件与 `ANCHORS-CURRENT.md` 的 M6a/G4d 锚行。
- `LANDED-g4d` 已在 22:57 更新到 `63dd3f49`（`gaps.orphan_expectation` 已补“未重跑”）；本文件 §0 的 G4d 事实以该新值为准。