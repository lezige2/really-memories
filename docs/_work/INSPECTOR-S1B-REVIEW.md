# INSPECTOR S1-b 终审（M2 完整最后一道门）

- 审查人：`inspector`（检测员；只读角色，本单仅写本文件 + temp 读数）
- 对象：S1-b 真机臂（task-31）+ v6 口径 `docs/_work/M2-FULL-S1-SPEC-lead.md@ae2d88ad5ecc25d3`（16,437 B / 132 行）
- 被审产物：`kvmem/m2_visibility/chat_lease/LANDED-s1-real.json@98bbf28b65d1de19`（28,059 B）+ `kvmem/m2_visibility/m2_planner/out/` 15 个产品
- 本单**零 14B 重跑**（按 lead 指令）；所有新增读数落在 `C:\Users\lezige\AppData\Local\Temp\s1b\`（脚本 `verify_real2.py`、`verify_misc.py`、`verify_ledger.py`、`sel_all_states.py`、`explain_rebuild.py`、`build_index_repro.py`、`bi_child.py`、`rerun/*.json`）
- 读数口径：sha16 = 二进制 sha256 前 16 hex；行级比对 = sqlite 逐表逐行 `select *` 比较；不采用台账/产品自报值，一律现算

> **审前状态**：仓库 `kvmem/chat.db` = `237d8e1f5de9a382`（110,592 B），`tools/chat.py` = `288d2d85720359e0`（72,345 B / 1,391 CRLF / lone LF 0 / 末尾无换行），spec = `ae2d88ad5ecc25d3`，三块 `home/project/habit` = `73843fc5`/`536eac03`/`f6f8e85c`；审后复算**全部不变**（我的运行未写仓库）。

---

## 0. 结论摘要

| 项 | 四态 | 一句话 |
|---|---|---|
| **S1 整体（真机层 v6）** | **通过** | ①/②b/②c/③/④/⑤/P1a/P2/CAP 均判过；P1b 零实例=不可判；默认路径 m1 真机 = **G4 既有缺口单列，不属 S1** |
| **§A 台账 DB 标签** | **(a′)** | 内容行级相同、仅派生 `attr`/`value_kind` 被重建；**不是 (b) 内容不同**，真机读数可归因、不退回重判 |
| **S1 可签？** | **可签（带 5 条非读数性补正）** | 读数层无保留；清单见 §12 |
| 默认路径 G4 | 未通过（非 S1） | `m1` 真机新旧同 `KeyError 'conv_2026-10-25#L5' @chat.py:598`；`m1 --explain` 新旧逐字节同；**“M4-C 绿臂回归链暂断（G4）”** 必须在签字文里原样出现 |
| R5 极性（lead 第 7 问） | **case 级红足够** | 见 §7.4；但台账须写明“主臂 CAP=未触发绿、红的判可性来自 case 级对照” |

---

## §A 红线：`db.temp_copies["chat@237d8e1f.db"].sha16=2d3bae59` vs 文件名 `@237d8e1f`

### A.1 行级比对（决定性证据）

`tmp_db/chat@237d8e1f.db`（实际 sha `2d3bae59168b6ed1` / 110,592 B）对仓库 `kvmem/chat.db`（`237d8e1f5de9a382` / 110,592 B）：

- `sqlite_master`：表集合、建表 SQL、索引全等。
- **逐行相同（10 张里 8 张）**：`memory_source` 10 行、`memory_block` 2 行、`memories` 2 行、`memory_source_excerpt` 7 行、`doc` 10 行、`facet` 17 行、`term` 346 行、`index_meta` 3 行（docs=2 / version=5 / analysis=4）。
- **只有 2 张派生表不同**：`attr` 8 行（repo 有 `(1,address)`、`(2,address)`；temp 有 `(3,birthday)`、`(10,birthday)`）、`value_kind` 17 行（行集合/顺序差）。二者都是 `retrieval.build_index` 从 `memory_source` **重算的派生缓存**，不是证据源。
- 三块文件 sha 独立重算：`home 73843fc5` / `project 536eac03` / `habit f6f8e85c`，与台账 `block_files` 全等（块文件本身没被碰）。

⇒ **证据面（memory 源/块/摘录/doc/facet/term/index_meta）逐行相同；差异只在派生索引**。按 lead 的 G3 口径，`chat.db` 不是冻结源；这不是 (b)。

### A.2 差异来源已定位（可解释的确定性污染，不是“来路不明”）

1. `_run_m1_regression.py` 为落 G4 调用 `cmd_m1(explain=False)`；`cmd_m1` 在 `tools/chat.py:521` 执行 `R.build_index(con, verbose=True)`，**无条件重建派生索引**（不是只在 stale 时）。
2. 该脚本先把 `db_copy.sha16 = sha16(args.db)` 写进产品（`S1-real-default-regression.json` 里是 `237d8e1f5de9a382`，这是我复算的**跑前值**），**之后** `m1` 真机臂把同一份 temp 副本的 `attr/value_kind` 重写成了 `2d3bae59`；再接两采样真机臂（21:49 起）时用的就是这份，`S1-real.json`/`S1-real-smoke.json` 的 `db_copy.sha16_before=2d3bae59` 与现盘一致（这两处**没有**虚报）。
3. **零 GPU 复现（G3 可复现性升级）**：对同一 `237d8e1f` 副本跑 `R.build_index`，4 个**独立进程**得到 4 个不同 sha（`cfca0fce48adf09a` / `e10ff138398fab51` / `71a9a9bd7145cf4c` / `cbb7271d729935c2`），而 `memory_source`/`term`/`facet`/`doc` 每次相同 ⇒ 派生表跨进程非确定。这解释了 `2d3bae59` 的来路，也把 G3 从“观察到的漂移”升级为“**可复现的非确定性**”。
4. 反向事实：`237d8e1f` 里存的 `attr` 是旧代码产物（当前代码重建不出 `(1,address)/(2,address)`）——即 `is_stale` 只比 version/analysis 字符串、派生缓存“版本号未变但内容已过期”的 G3 深层面。

### A.3 读数可归因（决定性证据）

用 `_selection` + `_two_selection_texts` 对 **5 个 DB 状态**逐问题比较：仓库 `237d8e1f`、temp `2d3bae59`、两个独立重建态（`cfca…`/`e10f…`）、旧 `cd430943`：

- 每个问题的 selection `(name, score)` **逐字段相同**（如车牌问 → `conv_2026-10-25#L5` 2.12518；住址问 → `conv_2026-10-25#L3` 4.006126；项目 → `project` 5.843949…）；
- A/B 的 selection 文本逐字符相同（A 16 字、B 43 字，见 §5）；
- 真机产物 `selection_hits` A=`conv_2026-10-25#L3`(id 5) / B=`project`(id 2) 与 dry 一致。

⇒ **派生索引的 4 种状态都不改变 S1 选块/读数**；真机臂读数可归因到“237d8e1f 内容坐标”。

### A.4 §A 判决

**判 (a′)：内容行级相同、派生表被重建 ⇒ 良性标签瑕疵，不是读数污染。** 真机读数**不退回重判**。必修（executor task-32 已接）：
1. 台账 `db.temp_copies["chat@237d8e1f.db"]` 改名/加字段：`content_sha_before=237d8e1f` / `actual_sha16=2d3bae59` / `derived_rebuilt_by=_run_m1_regression` / `row_level_note=见 inspector 逐表比对`；
2. `S1-real-default-regression.json` 的 `db_copy` 改 `sha16_before`/`sha16_after` 双记（现在只有跑前值，现盘对不上，会被误读为假声明）；
3. `deviations` 增“m1 真机回归会无条件重建派生索引、改写 temp 副本（G3/G4 交界）”，后续默认路径回归改一次性副本。

---

## 1. 变更面：`cb70be52` v5 → `288d2d85` v6（静态）

`difflib` 逐行（非模糊）结果，**只有 5 个 hunk**：

| hunk | 旧行 | 新行 | 内容 |
|---|---|---|---|
| replace | 1 | 1 | `DB = os.environ.get("CHAT_DB") or os.path.join(ROOT,"kvmem","chat.db")`（默认值不变；env 只在显式设置时生效） |
| insert | 0 | 686 | S1 块（几何/attach hi/③ 公式/cap_ok/②a 降级+②c/②b 去空白/P-1 拆半/S1-03 默认红/notes/frozen 等） |
| replace | 1 | 1 | `--cmd` choices 增加 `two` |
| insert | 0 | 4 | `--dry-run`/`--out`/`--chat` 等 S1 CLI 参数 |
| insert | 0 | 2 | `elif args.cmd == "two": sys.exit(cmd_two(...)["exit"])` |

- **`cmd_m1` 函数体（v5 行 ~504–~673）零改动**：所有非 S1 hunk 的新行号都 ≥675 或 =48；我另做了 `old[504:510]==new[504:510]` 与 `main()` 尾部 `old[-6:]==new[-6:]` 逐字节断言，均等。
- **默认分支**：`chat`/`m1` 分支未改；`S1-default-unchanged.json@12cebec6e516fd3b` 给出同一组 5 个 opcode（`replace 1 / insert 686 / replace 1 / insert 4 / insert 2`），且 `two_cli`：旧文件对 `two` 报 `argparse exit 2`，新文件 `exit 0` ⇒ 纯增量子命令。
- **`m1 --explain` 新旧逐字节相同**：我独立用 temp DB 跑 `tools/chat.py m1 --explain`（v6）与 `_before/chat.py@cb70be52eef253fa`（v4 旧副本），stdout **654 B / sha16 `3e8aae60685d2e55`**，二者相等；与台账 `default_path.explain_identical=true`、`S1-default-unchanged.m1_explain`、`S1-real-default-regression.m1_explain` 三处互证。
- `db_copy` 默认 `CHAT_DB` 未设置时 `chat.DB == D:\llama-mem\kvmem\chat.db`（我静态 import 断言）；默认路径没有实质改动。
- **G4 说明**：默认路径 `m1` 真机新旧同 `KeyError 'conv_2026-10-25#L5'`（`chat.py:598`，`cmd_m1` 帧 `{'file':'chat.py','line':598,'func':'cmd_m1'}`）；证据见 §10。**必须写：“M4-C 绿臂回归链暂断（G4）”。**

---

## 2. 两采样（`S1-real.json` / `S1-real-2.json`）

- 递归 diff 全树：**恰好 7 个字段不同**，全部为易变元数据：`sample`(1/2)、`started_at`、`finished_at`、`elapsed_s`(113.8/113.9)、`run_s`(107.0/107.2)、`run.at`、`run.sha_stable.at`。`answers / checks / counters / sessions / per_round(20) / fact_layer / cross / accounting / budget / sha_stable 结构` 全同。
- 时间：`finished_at(s1)=21:51:52` → `started_at(s2)=21:52:32` = **40 s**；`chat_py_sha16=288d2d85`、`script_sha16=c434d750`、`spec@ae2d88ad` 两采样一致。
- 台账 `two_samples.readings_identical=true / diff_fields=[] / sample_gap_s=40` 与我的全字段 diff 一致（台账 canon 去掉的正是上述 7 个易变字段；严格说 `sample` 是编号不是时间，建议台账把这条写成“7 个易变字段（5 时间/耗时 + sample + run 时间戳）”以免歧义）。

---

## 3. 几何 / ③ 公式 / `hi` 排他（v6 核心修复）

真机读数（A/B）：

- A：`chat_start_A=4096`；home 块 `base=4075, cells=21, pos_hi=4096`；`n_tokens=536`、`pos_max=4631`。
- B：`chat_start_B=4650`；project 块 `base=4632, cells=18, pos_hi=4650`；`n_tokens=580`、`pos_max=5229`。
- **块尾 == 本会话 chat 起点**：A `4075+21=4096`；B `4650=4096+536+18=4650`；`pos_hi` 即排他上界（`attach(seq,dst,lo,end)`，v5 的 `end−1` 已消失）。
- **`hi` 排他实证**：块读数 `n_tokens_readback` = 21 / 18；`pos_max_readback` = `pos_hi−1` = 4095 / 4649；`blocks[].ok=true`。
- **③ 公式**：`chat.py:1053` `pos_expect = chat_start_self + n_self − 1`；A `4096+536−1=4631` ✓、B `4650+580−1=5229` ✓（不是硬编码 4096）。`pos_max == pos_max_expect` 两会话都成立；`checks.S1-03=true`。
- 几何连续性检查代码 `contiguity_ok`：每会话 `max(plan.pos_hi) == chat_start` 且 `attach_error is None`、`seqs_distinct`、块 seq 不与会话 seq 重叠、`TWO_BLOCK_SEQ_BANNED` 不在块 seq；真机/干跑均 true。
- dry（stub 670/轮）：A `chat_start=4096`、670 cells、pos 4765=4096+670−1；B `chat_start=4784=4096+670+18`、project `base=4766/pos_hi=4784`；与 `S1-cases-main` 的 `M_03_readings/M_03_blocks_geometry` 期望逐字相等。

---

## 4. ①（S1-01）/ ②b（S1-02b）逐轮重算

我不用 `fact_layer` 自报值，直接从 20 条 `per_round.answer` 重算：

- A：事实 `广陵路`，10 轮 **字面**命中 10/10、去空白后 10/10；最后轮字面 `true`；`other_fact_in_any_round=[]`（`3月14` 不去空白也在 A 任何轮都不出现）。
- B：事实 `3月14`，10 轮**字面**命中 0/10（真机答 `3 月 14 日`，v6 ②b 去空白正是为此），去空白后 10/10；最后轮 `own_hit_last_literal=false / own_hit_last_norm=true`；`other_fact_in_any_round=[]`（`广陵路` 不在 B 任何轮）。
- ②b 交叉：`cross.a_to_b={ok:true,a_contains_fact_b:false}`、`b_to_a={ok:true,b_contains_fact_a:false}`；`checks.S1-02b=true`。
- 两采样同（见 §2）⇒ ①/②b 不是“单次幸运”。dry 里 `S1-01/S1-02b="未做"`（`M_dry_not_done` 断言），没有假绿。

---

## 5. ②c（v6 新增，零 GPU）与 ②a 分母

- dry `S1-dryrun.json`：`checks.S1-02c=true`；`cross.c_selection_text.A={text_len:16, contains_other_facts:[], ok:true}`、`.B={text_len:43, contains_other_facts:[], ok:true}` ⇒ 未过滤 selection 文本 A 不含 `3月14`、B 不含 `广陵路`（去空白后判），2/2。
- **真机产品 `checks.S1-02c="未做"`**：代码按设计只在 dry 判（`bool(...) if dry else "未做"`）；真机 `cross.c_selection_text` 数据仍算出且 ok=true，但**不冒充真机判据**。这与“②c=零 GPU 判据”的 v6 口径一致，报告按 dry 记“通过（dry 层）”。
- **②a 降级**：`checks.S1-02a` 仅接线回归（`source_blocks ⊆ mounted` + structural），**不计入交叉分母**；台账/产品三处分母一致：sessions 2 / mounted 2 / pool 3（另列）/ `cross_assertions_text=2`（②b 两条）/ `cross_assertions_selection_text=2`（②c 两条）；`S1-cases-main.three_level_denominator` 与 dry 产品逐字段相同，note 明写“②a 不计入交叉分母”。
- ②a 的“恒真”已有 R1 反证：R1 注入 source_blocks 元数据 ⇒ `S1-02a=false`、`fail_ids=["S1-02a"]`，其余仍绿；所以保留下来的 ②a 不是空判据，但按 v6 只当接线回归用。

---

## 6. P1a / P1b / P2 与 R4a/R4b

真机：`share=2, attach=2, drop=0, detach_hits=0, attach_replay=0, reset=2`；`p1_share_eq=true`、`p1_drop_eq="not_triggered"`、`p2_ok=true`；`checks.P1a=true`、`checks.P1b="not_triggered"`（**不是 true/通过**）、`checks.P2=true`。

- **P1a（可判）**：share 等式 2==2 有正实例；R4a（绕过 leases 直调 `eng.share`）产品：`share=2, attach=0, p1_share_eq=false, P1a=false`，其余 `S1-03/S1-04/P2` 仍绿 ⇒ 红证成立。
- **P1b（不可判）**：S1 无 detach 路径 ⇒ drop=0/detach=0 零实例，真机与所有 dry 均 `not_triggered`；R4b 只红 P2（`attach_replay=2`，`p1_share_eq` 仍 true），不提供 drop 红证 ⇒ 按“零实例=不可判，不是通过”记，正确。
- **P2**：`attach_replay=0`；R4b 红（replay=2、`P2=false`），其余绿 ⇒ 可判且通过。

---

## 7. CAP 守门与 R5 极性（lead 第 7 问）

### 7.1 守门代码路径（真机执行点）

`chat.py` 每轮：`before=n_tokens` → `chat_round` → `delta=n_tokens−before` → `chat_accounted += delta` → `if chat_accounted > chat_len_cap(1024): cap_hit={round,chat_cells,cap}; cap_refused={PlanRefused, reason:"chat_len_cap", msg:"... @round r"}; break`。`cmd_two` 把 `cap_refused` 落成 `cap.refused/exit 2`；`checks.CAP = cap_guard_ok`（accounted≤cap 且 `cap_refused is None`）。

### 7.2 真机主臂（10 轮）

A 536、B 580，累计都 ≤1024 ⇒ **CAP 未触发**：`run.cap={refused:false,hit:null,error:null}`、`checks.CAP=true`。这是**未触发绿**，本身不证明守门代码存在。

### 7.3 16 轮构造（case 级）

`M_CAP_refuses`（`two_session_run(n_rounds=16)`，床内 `cap_refused_expected=True` **写死**，不随 `--expect-red` 变化）：

- shipped：`refused=true, reason="chat_len_cap", over_cap_cells=1072 > cap=1024, max_chat_cells=1072, B_rounds=0, B_cap_ok="not_run", B_reading_ok="not_run"` ⇒ 超 CAP 即 `PlanRefused`（exit 2 口径）。
- R5（单 hunk 删掉 CAP 校验块，模块 `4d9d11857875a146`）：`refused=false, reason=null, B_rounds=16, B_cap_ok=false, B_reading_ok=true`，即**没有拒绝、一路跑满 16 轮并超到 1672**；`M_CAP_refuses` 因此红，`fail_cases=["M_CAP_refuses"]`、`n_pass=11/12`。

### 7.4 结论（lead 第 7 问）

**case 级红足够证明 CAP 守门，主产物不需要也不应该改成红。** 理由：

1. 探测与主臂走**同一函数、同一 LOOP、同一 cap=1024**，只是把轮数拉到 16 使累计必然越界；shipped 在越界轮拒绝，R5 同一输入不拒绝 ⇒ 守门代码是**承重**的（不是死代码/旁路开关）。
2. 床内期望 `cap_refused_expected=True` 是**写死的不变量**，R5 不能靠 `--expect-red` 声明绿/红 ⇒ 反证不可伪造。
3. 主臂 536/580 距 1024 很远，**按设计就不该触发**；把主臂做成红需要往 14B 规范读数里注入超 CAP 轮次，会毁掉 ③/④/① 的干净读数，代价大于收益。
4. 但**极性表述必须写清**：R5 的红在 `fail_cases`（case 级），`expect_red=[]`（checks 级不红）；签阅者若只看 `checks.CAP/expect_red` 会把 R5 看成全绿。建议在台账 `red_proofs.R5` 增加 `red_kind:"case(M_CAP_refuses)"` 与一句“主臂 CAP=未触发绿；可判性来自 16 轮 case 级对照”。

---

## 8. ⑤ sha_stable（真机层）

`run.sha_stable`：`status=done`、`unchanged=true`；7 个被检文件（顺序）：`analysis.py@49e91c7b`、`retrieval.py@43f66019`、`evidence.py@dccf7f01`、`home.kvmem@73843fc5`、`project.kvmem@536eac03`、`chat.py@288d2d85`、spec `ae2d88ad5ecc25d3`；每项 `sha16_before==sha16_after==我现算`。`checked_blocks=["home","project"]`；`not_checked=[{"name":"habit","why":"只登记未挂、不检"}]`（与“登记未挂不检”口径一致）。DB 项：path=`tmp_db/chat@237d8e1f.db`，before/after=`2d3bae59`，`unchanged=true`（臂运行期间该副本未再变）。

- **边界说明**：⑤ 只覆盖 temp 副本 + 产物文件，不覆盖仓库 `kvmem/chat.db`；我独立复核仓库库仍 `237d8e1f`（且我的全部运行未写它）。§A 的派生重建发生在**臂前的回归步骤**，臂内无 DB 写入（before==after），所以 ⑤ 本身成立。
- 5 个文件（三冻结件 + 两已挂块 + chat.py + spec）跑前跑后同值 ⇒ v6 的“0 漂移”在臂内成立；但**任何把 `chat.db` 包含进“0 漂移”的说法都必须加“派生库，见 G3”**（A.2 已证明派生表跨进程非确定）。

---

## 9. 台账 / 产品 sha 复核

全部现算，**逐项相等**：

- `module_shas` 10 项：chat.py `288d2d85`/72,345、chat_lease `619a0432`/19,274、m3_lease `33ae679a`/9,047、plan `74da0732`/4,290、planner `01507f6b`/9,093、evict_policy `c2a8d8cb`/6,030、analysis `49e91c7b`/18,382、retrieval `43f66019`/18,197、evidence `dccf7f01`/6,997、chat.db `237d8e1f`/110,592。
- `scripts` 4 项：bed `88bbd4b1`/15,956、land `b63b22d0`/19,216、run_s1_real `c434d750`/9,572、run_m1_regression `c188957e`/6,801。
- `before_copies`：v5 `b9010e9c`/65,789、v4 `cb70be52`/34,319、v5 land `e11e69f8`/16,318。
- `products` 15 项：`real_s1 3df8d70b`、`real_s2 39b7f9de`、`real_smoke a067294a`、`default_regression 39aa2505`、`dry_s1 f2ae36b3`、`dry_s2 007015df`、`cases_main c9211e5d`、`pre 8bb70d6b`、`default_unchanged 12cebec6`、R1 `4be0b287`、R2 `4fe7e172`、R3 `6ae013be`、R4a `672f1a1b`、R4b `9c1b01f2`、R5 `98688eda`（bytes 全对）。
- `variant_modules.v6` 6 个模块 sha 全对；单 hunk 证明：R1 replace 1→2 行、R2 replace 1→1、R3 insert 2、R4a replace 1→1、R4b insert 1、R5 replace 1→1。
- `no_self_sha=true`，台账正文不含自身 sha `98bbf28b65d1de19`。
- `deviations` 5 条：`_StubEngine` 仍在 tools/chat.py（下刀搬）、v6 改 S1 块+CHAT_DB 默认分支未改、②a 降级、P1b `not_triggered`、m1 真机 G4 只落证不修绿。**§A 的“m1 回归无条件重建派生索引、污染 temp 副本”尚未入 deviations**（task-32 已接）。
- **两处台账文本问题**（非读数）：① `frozen_numbers.geometry` 写 `chat_start_B=+18`，应为 `4096+n_chat_A+18`（我判为 typo，真机/干跑/产品都与正确公式一致）；② `spec` 对象只有 `path/sha16/bytes`，缺 `lines=132`（v6 已知 132 行），建议补齐。
- `module_shas` 未含判据床/落账/4 脚本（它们在 `scripts` 段，sha 均对，但不在“0 漂移”集合里）——lead 第 9 条点名要求并入，task-32 已接。

---

## 10. 默认路径（G4）：`m1` 真机、`m1 --explain`、`two` 增量

- `S1-real-default-regression.json@39aa2505d74724a4`：`m1_real_new` / `m1_real_old` 均 `raised=true, type=KeyError, msg="'conv_2026-10-25#L5'", frame={"file":"chat.py","line":598,"func":"cmd_m1"}`；`g4_confirmed=true`、`default_path_equiv=true`。
- **静态复现（零 GPU）**：`rows = {r[1]:r for r in ms.block_rows(con) if r[5] is not None}` 的键只有 `profile/project`；`cmd_m1` 的 4 个问题里，车牌问 selection = `[('conv_2026-10-25#L5', source_id 7)]`，该源 `seq IS NULL` ⇒ 不在 `rows`，下一行 `tools/chat.py:598 n = ms.load_into(eng, rows[name], seq)` 抛 `KeyError`。v4 副本同一行 598 逐字节相同（`v4[593:600]==v6[593:600]`），故新旧同错。
- `m1 --explain`：新旧 stdout 654 B、sha16 `3e8aae60685d2e55`、逐字节相同（三处互证，见 §1）。
- `two` 子命令：旧文件 `argparse invalid choice 'two'`（exit 2），新文件 `exit 0` ⇒ 纯增量。
- **判**：默认路径 m1 真机 = **未通过（G4 既有缺口，非 S1 引起）**，单列、不折扣 S1；签字文必须原样写 **“M4-C 绿臂回归链暂断（G4）”**。修 G4 另开单（`m1` selection→块行过滤/补块行），不进 M2 完整判据。

---

## 11. 零 GPU 独立复现（我不采信 executor 自报，自己重跑测试床）

用 `_test_two_session.py@88bbd4b1` + temp DB 副本（从仓库 `237d8e1f` 拷出，`S1_TEST_DB` 指向它；仓库库只读），重跑 7 个产品：

| 产品 | 我的重跑 | 存储产品 | 比对（去掉 `at`） |
|---|---|---|---|
| main（v6） | 12/12，fail=[] | 12/12 | **逐字段相同** |
| R1 inject-source | 12/12 | 12/12 | 逐字段相同 |
| R2 same-seq | 12/12 | 12/12 | 逐字段相同 |
| R3 underrecord | 12/12 | 12/12 | 逐字段相同 |
| R4a bypass-leases | 12/12 | 12/12 | 逐字段相同 |
| R4b replay | 12/12 | 12/12 | 逐字段相同 |
| R5 no-cap-check | 11/12，fail=[`M_CAP_refuses`] | 11/12 同 | 逐字段相同 |

- 另独立跑 `m1 --explain` 新旧：654 B / `3e8aae60` 相同（§1）。
- pre（S1 前旧文件）：2/12，`fail_cases` 与台账 10 条全同；唯二 ok 的 `F_fail_ids`（空集）与 `D_default_m1_explain`（旧=旧对照）**不构成绿**，台账 note 已写明。
- 结论：S1-a/S1-b 的 12 例判据与 6 个变体红证**可复现**，非一次性结果。

---

## 12. 我发现的问题（按对签字的影响排序）与处理建议

| # | 问题 | 性质 | 是否挡签 | 建议 |
|---|---|---|---|---|
| F1 | §A：`chat@237d8e1f.db` 实际 `2d3bae59`，内容行级同、派生重建；`S1-real-default-regression.db_copy.sha16` 是跑前值（现盘 2d3bae59） | 标签/记录瑕疵，**不污染读数** | 否（但必须补正） | task-32：台账 addendum + 改名/双 sha + default-regression before/after + deviations 一条 |
| F2 | 真机产品 `run.notes` 是静态文案：`S1-01/S1-02b/S1-05` 写“未做”，而 `checks` 为 true / `sha_stable=done`（`S1-real.json` 与 `S1-real-smoke.json` 都有） | 产品文本自相矛盾，可能误导签阅 | 否 | 建议在 correction/addendum 里补 `notes_corrected` 或把 notes 改 mode 相关；不要改读数文件本体 |
| F3 | `module_shas` 未含 bed/land/run 4 脚本（在 `scripts` 段，sha 已对） | 覆盖口径缺口（“0 漂移”漏判据） | 否 | task-32 并入或改名 `frozen_shas`，并写清“判据床也是冻结面” |
| F4 | `frozen_numbers.geometry` 文本 `chat_start_B=+18`；`spec` 缺 `lines=132` | 台账文字 typo/缺字段 | 否 | 顺手补 |
| F5 | R5 `expect_red=[]` 而红在 `fail_cases=["M_CAP_refuses"]`；只看 checks/expect_red 会误读全绿 | 极性表述坑，非证据缺陷 | 否 | 台账 `red_proofs.R5` 增 `red_kind:"case"` + “主臂 CAP=未触发绿，判可性来自 16 轮对照”一句 |
| F6 | §A 根因：`cmd_m1` 无条件 `build_index` 会改写 DB（含 temp 副本）；G3 派生表跨进程非确定 | G3 档案应升级（lead 已要求）；流程上默认路径回归不该复用臂副本 | 否（对 S1） | G3 档案写“可复现非确定 + 4 进程反证”；G4/默认路径回归用一次性副本 |
| F7 | 真机 `checks.S1-02c="未做"` 但 `cross.c_selection_text` 数据存在 | 设计如此（②c 只 dry 判） | 否 | 报告按 dry 记通过，别把真机 ②c 当绿 |

---

## 13. S1 整体四态表（sign-off 用）

| 判据 | 层级/分母 | 四态 | 证据（可复核） | 折扣/备注 |
|---|---|---|---|---|
| ① S1-01 事实命中 | 真机 2 会话 ×10 轮 | **通过** | A 10/10 字面+去空白；B 10/10 去空白（字面 0/10）；`other_fact=[]`；两采样同 | 无 |
| ②a S1-02a 结构 | 接线回归（不计交叉分母） | **通过（接线层）** | `source_blocks ⊆ mounted`、structural 全 true；R1 可红 | 不作为交叉证据 |
| ②b S1-02b 文本 | 真机 2 条交叉（分母=2） | **通过** | `a_to_b/b_to_a ok=true`、facts=false；逐轮重算一致；两采样同 | 去空白后判（v6） |
| ②c S1-02c 选择文本 | dry 零 GPU 2/2 | **通过（dry）** | A 16 字/B 43 字 selection 文本互不含对方事实；`S1-02c=true` | 真机 `未做`（设计） |
| ③ S1-03 读数 | 真机 2 会话 | **通过** | A 536/4631=4096+536−1；B 580/5229=4650+580−1；hi 排他；块回读 21/4095、18/4649 | 无 |
| ④ S1-04 记账+预算 | 真机 1 次对账 | **通过** | 39+536+580=1155≤8192；engine_match done 39/1116=1116；B n_ctx_eff=7656 | 无 |
| ⑤ S1-05 sha_stable | 真机 7 文件 | **通过** | 三冻结件+home/project+chat.py+spec 跑前跑后同值；habit 只登记未检 | 不含仓库 chat.db；“0 漂移+chat.db”须注 G3 |
| P1a share 等式 | 真机 2 正实例 | **通过** | share==attach=2==2；R4a 红（share 2/attach 0/P1a false） | 无 |
| P1b drop 等式 | 0 实例 | **未触发/不可判** | drop=0、detach=0；全产品 `not_triggered` | **不得记通过** |
| P2 replay | 真机 0 命中 | **通过** | attach_replay=0；R4b 红（replay 2/P2 false） | 无 |
| CAP 守门 | 真机 10 轮 + 16 轮对照 | **通过** | 主臂未触发（536/580≤1024）；16 轮 over 1072>1024 `refused=true reason=chat_len_cap`；R5 case 红 | 表述见 §7.4；主臂=未触发绿 |
| 默认路径 m1 真机 | 1 次 | **未通过（G4，非 S1）** | 新旧同 `KeyError conv_2026-10-25#L5 @chat.py:598` | **“M4-C 绿臂回归链暂断（G4）”** |
| 默认路径 m1 --explain | 新旧对照 | **通过** | 654 B / `3e8aae60685d2e55` 逐字节同 | 无 |
| S1-a dry 回归 | 12 例 + 6 变体 | **通过** | main 12/12；R1–R4b 12/12；R5 11/12（仅 case）；pre 2/12 | 我独立重跑复现 |

**S1 整体判决：通过（真机层，v6；P1b 未触发不可判；默认路径 G4 单列）。**

**可签性：可签 S1。** 读数层无保留；签字前建议先把 §12 的 F1–F5（全是标签/文本/口径补正，不改读数、不需重跑 14B）落成 task-32；F6 进 G3 档案；G4 另开单。若 lead 要求“补正落账后才签”，则等 executor task-32 完成、我复核 addendum 后签；**不因 §A 把真机读数退回重判**。

---

## 14. 我没做的（诚实边界）

- 按 lead 指令**未重跑 14B**（两采样/真机读数来自 executor 产品 + 我的逐轮重算，未独立再生成 14B token）。
- 未解析三个 `.kvmem` 块文件的内部 cell 内容（只验 sha + DB 里 `memory_block` 行 + 真机/干跑读数）；块文件格式层不在本单判据。
- 未修任何代码/产物/台账/DB；未写仓库除本文件外的任何文件；所有实验均在 temp 副本上跑（仓库 `chat.db` 审前/审后 `237d8e1f`）。
- 未验证 G4 的修复方案（另单）；未验证 14B 引擎内部实现（只验调度/读数/账目）。

---

*检测员 inspector · S1-b 终审 · 读数落 `C:\Users\lezige\AppData\Local\Temp\s1b\` · 本文件只此一份*