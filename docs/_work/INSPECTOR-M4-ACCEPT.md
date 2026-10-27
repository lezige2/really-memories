# M4 验收独立复核：九项复算 / 三个未闭项 / 三套"九项"口径（inspector）

复核对象：`kvmem/m2_visibility/m4/`（写入固化链路）｜复核时点 2026-10-25 18:46｜**只读**（未改产物/脚本/台账/PROGRESS）
与 executor 并行、互不看结论｜本文件只从锚、块、DB、write json 自己算
判据原文：`D:/llama-mem-backup-2026-10-25/kvmem/m2_visibility/mine/inspector/M4-ACCEPT.md`（`c4186107246dd35d` / 25,038 B，**不在工作区**）
台账：`PROGRESS §6.3`（九项计数口径）、`§6.6/§6.7`（M4-C / 未闭项）、`§12.1`（`F-M4-*`）

## 1 判法（先写，后算）

**四态定义（每项只用这四态，不造第五态）**
| 态 | 定义 |
|---|---|
| **通过** | 台账记录值能**从指定产物独立复算且相等**（不采信产物自报的 `true`，要落回字段/文件） |
| **未通过** | 复算**不等**：数字错、口径错（记录的读数和产物不是同一件事）、或标签与值不符 |
| **未接上** | 该项在产物里**没有位置/字段**，或记录指向的产物不存在/不可回收 ⇒ 无法复算（不是"数错"，是"没处可读"） |
| **未做** | 从没跑过、没有产物 |

**独立性判法（用来判"九项全真"能不能当 9 个性质签）**
两项独立 ⇔ 读数来自不同产物/字段，**且不能由另一项按构造推出**。否则记 G（"同一读数的两种说法"），不计入独立性质个数。锚（sha）不是性质项，单列。

**本审计的"九项"取 `PROGRESS §6.3` 那九行**（那是台账要签的版本）。另两套"九项"单列对照（§4）：(i) `M4-ACCEPT.md` §0 的九行（判据原文版）；(ii) a4 `acceptance` 的 **17 键**（机器自证版）。

**签判词定义**
- 可签"九项全真" ⇒ 九行 **9/9 通过**；否则不可签（并给应改成的数）。
- 可签"M4 已验收" ⇒ 九项全真 **且** 三个未闭项按四态处理 **且** `M4-ACCEPT.md` §6 的三条放行条件全部落地 **且** 结论带可复算锚。缺一项就只能签"端到端链路成立"。

## 2 九项独立复算表（`PROGRESS §6.3` 字面）

锚与产物：`run_m4_verify_a4.json` `59edbd82d4b9ae44`/17,332 B（attempt 4，09:46:14–09:46:45，`acceptance` 17 键全 true）｜`run_m4_write.json` `6408d8e2ecdf6ee5`/13,402 B｜块 `81127d24fd64b96b`/9,507,412 B｜`m4_memory.db` `fd244c80c0cc974d`/86,016 B。四把我都重算过，与台账相等。

| # | 台账项 | 台账值 | 我的复算（产物:字段 → 值） | 判 |
|---:|---|---|---|---|
| 1 | 真实对话轮数 | 9 | `write.judge.per_sentence[*].turn` 去重 = **1..9**；`block_text` 9 行 | **通过** |
| 2 | 判定句数 = 进入判定的句子数 | 10 | `judge.sentences`=**10**；`per_sentence` len=**10**（turn2 被切两句，均 D4） | **通过** |
| 3 | keep 条数 | 6 | `judge.keeps`=**6**；`judge.memories` len=**6** | **通过**（注：a4 `dedupe.keeps`=7 是去重测试第二轮读数，不是本项） |
| 4 | 块数 / cells | 1 / 91 | `a4.blocks` len=**1**、`cells`=**91**；块文件 9,507,412 B = `write.save.bytes`；`save.cells_after_save`=91 | **通过** |
| 5 | 块落位与 `pos_max` | [4005,4096) / 4095 | `write.lease_chain` step `reload_and_place`：`range`=**[4005,4096]**、`pos_max_raw`=**4095**、`file_sha_after`=81127d24… | **通过**（标签须改词，见 G7） |
| 6 | memory 行数（含相对时间锚定） | 6（含 2026-10-28） | DB `memory` 6 行；仅 mem6「计划」`anchored_time`=**2026-10-28**，其余 5 行 NULL；`a4.stored` 6 行 == DB 6 行（逐字段相等） | **通过** |
| 7 | `memory_source` 行数 | **7** | DB `memory_source` = **5 行**（1 `conv_2026-10-25` + 4 条 fact 单元；`fanout` 1/1/2/1/2，文本 5 条互异） | **未通过**（G1） |
| 8 | 新进程检索作答 | **9/9** | a4 `search_checks` **2** 条、`answers` **2** 条；均 `new_process=true`、`child_of=parent_pid=12184` 不等；两条答案逐字命中 = **2/2** | **未通过**（G2） |
| 9 | 锚 | `run_m4_verify_a4.json` = 59edbd82d4b9ae44 | 文件 sha16 = **59edbd82d4b9ae44** ✓ | **通过**（锚项，非性质项） |

**小结：7/9 通过 · 2/9 未通过 · 0 未接上 · 0 未做。**

G1 出处（不是猜的）：`m4/README.md` §0 原文「+ **7 行** `memory_source`（1 块 + 6 条检索单元）」——那是 **R9 文本去重之前**的版本（6 单元）。R9 落地后 unit3=unit4、unit6=unit7 合并 ⇒ **5 行**。台账第 7 项停在旧值。
G2 出处：同一 §0 原文「9/9 验收项全过」= **九项验收 9/9**；台账第 8 项把它读成了"新进程检索作答 9/9"。实际检索作答是 **2 题 2 中**（a4），旧版 `M4-ACCEPT.md` §0 的 4/5 两项也是 2 条。

## 3 三个未闭项（`§6.7`）

| 编号 | 内容 | 现状（我复算） | 判 |
|---|---|---|---|
| `F-M4-1` | `n_predict` 引擎不暴露（记 null），声明 24 与实际不一致，无证据判定哪个生效 | **仍未闭**：`write`/`a4` 都**没有** `n_predict` 字段；`a7` 记 `engine_reports_n_predict=null`、`n_predict_consistent=null`、声明 64（`n_predict_source` 自述"常量递给 --child"）⇒ 仍只有"声明值"，没有"读回值" | **未闭（不阻塞 M4 验收）**：九项读数不依赖生成长度；但阻塞任何"n_predict=24/64 生效"的断言，M4-B 的 64 也只能写"声明 64" |
| `F-M4-3` | M4-C 未开始（leases 真调用） | **已闭**：2026-10-25 17:40 结项，判决 `M4C-CLOSURE-lead.md` `3309fb25cbd057f9`；`§12.1` 已标已闭 | **通过** |
| （无编号） | 版本差异（9 项 / 10 项 / 现版 16 键）必须一直写明 | **现版是 17 键**，不是 16：a4 `acceptance` 17 个键全 true（1..10 + `position0_pass_and_refuse`/`output_layer_clean`/`display_never_decides`/`raw_answer_preserved`/`display_trace_fields`/`gates_untouched` + `all_pass`） | **未通过**（G3：`§6.3` L857 与 `§6.7` 的"16 键"都要改 17） |

**G9（台账引用无落点）**：`§6.3` L857 说「`M4-ACCEPT.md` 记九项成立、**三个未闭项**」，但该文件里搜不到"未闭项"表（它的结构是 §0 九行 + §1–§9 判定 + §10 增补 + §6 更正记录）；`§6.7` 表只有 **2 个编号项**（F-M4-1 / F-M4-3）+ 1 条口径注记。所以"三个"这个数**没有原文落点**，要么补表、要么改成"两个编号项 + 一条口径注记"。

## 4 判据口径核对（三套"九项" + 版本坑）

| 套 | 出处 | 条目 | 现版核对 |
|---|---|---|---|
| A | `PROGRESS §6.3` | 9 行计数内核（轮/句/keep/块/位/行/源行/检索/锚） | 7/9 对（G1、G2 错） |
| B | `M4-ACCEPT.md` §0 | 9 行证据表（一块 / span / save+插入 / 新进程检索 / 新进程作答 / 多值 / 锚定 / 去重 / position0） | **9/9 可从现产物复算**：span 6 条都在 127 字 `block_text` 里、每条 value ⊂ span；save 9,507,412 B = 磁盘；`stored`==DB；多值 live1/superseded1/old_kept；去重 no_new_row + dedup_hit_the_repeat；position0 通过侧扫 [0,21) + 拒绝侧两道 guard 均 false。**但 pid 类读数是版本内瞬时值**（B 记 13288/8860、1920/9944，现版 a4 是 14168/4356、4784/13776，parent 12184）⇒ 具体 pid 不可跨版本沿用 |
| C | a4 `acceptance` | **17 键全 true** | 抽查可复算：`1_one_block`/`2_memories_with_spans`/`3_saved_and_inserted`/`4_new_process_retrieval`/`5_new_process_answer`/`6_multi_value_keeps_old`/`7_relative_time_anchored`/`8_dedupe_no_new_row`/`9_units_deduped_by_text`/`10_type_and_resolved` 全部与产物字段对得上；`gates_untouched`：GATE 1.3 / COV_MIN 0.35 未动 ✓ |

**版本坑（必须一并记）**
- "**9 项 / 10 项 / 16 键**"三个数并存：A 是 9 行计数、C 是 10 个编号 acceptance + 6 附加 + all_pass = **17 键**、B 是 9 行证据表。**当前以 C=17 键为机器口径、B=9 行为证据口径、A 为派生计数（且第 7/8 行错）**。
- `M4-ACCEPT.md` 自己是**活稿**（L224 原文「本文件仍是活稿，未交付验收」）；且**不在工作区**，只在备份（G4）。`m4/README.md` 同样只在备份（G4）。
- `M4-ACCEPT.md` §10 的三把锚：`run_m4_write.json` `6408d8e2` **未变** ✓；`m4_memory.db` `817a66e4`→`fd244c80`（`anchors_history.json` 有记录：Stage 1b layer-2 link，并写明"M4 acceptance anchors are VOID and were re-anchored by re-running m4_verify.py (16/16 true)"）；`run_m4_verify.json` `bdf392e8`→`857f13c5`（04:18）**没有任何记录**（全仓 grep `bdf392e8` = 0 命中）⇒ G5。
- `M4-ACCEPT.md` §6 更正「产物里**没有** `child_of` 字段」对现版 a4 **已不成立**（`answer_checks[*].child_of=12184` 在、`new_process=true`）⇒ 该更正是版本内结论，引用时要带版本。

## 5 缺陷 / 缺口（G 表，不改产物）

| # | 缺口 | 证据 |
|---|---|---|
| G1 | `§6.3` 第 7 项 `memory_source` 记 7，现产 **5** | DB 5 行；README §0 的 7 是 R9 去重前版本 |
| G2 | `§6.3` 第 8 项"新进程检索作答 **9/9**"是误读；实为"九项验收 9/9 全过"，检索作答 **2/2** | README §0「9/9 验收项全过」；a4 `search_checks`/`answers` 各 2 条 |
| G3 | "现版 16 键" → **17 键**（L857、§6.7 两处） | a4 `acceptance` 17 键（1..10 + 6 附加 + `all_pass`）；**16 键**是 `run_m4_verify.json`（现版 `857f13c5`，04:18，我复算 16 键全 true）——a4 多出 `output_layer_clean` |
| G4 | 判据原文 `M4-ACCEPT.md` 与交付报告 `m4/README.md` **都不在工作区**（只备份）；`M4-ACCEPT.md` 自述"活稿未交付" ⇒ 工作区内没有"验收判据"可被复核者直接读到 | `find . -name M4-ACCEPT.md` = 0；备份 `c4186107246dd35d` / README 50,434 B |
| G5 | 锚漂移无记录：`run_m4_verify.json` `bdf392e8`→`857f13c5`（04:18）不在 `anchors_history.json`；该 history 的 `chat.db` 末条 `5909b978` ≠ 现 `237d8e1f`（表停在 05:12） | `grep -rn bdf392e8` = 0；history 末 3 条 time ≤05:12 |
| G6 | 九项**非互相独立**：③ keep 6 ↔ ⑥ memory 6 行按构造相等（每 keep 必落 1 行）；④ 91 cells ↔ ⑤ [4005,4096) 同源于同一块的同一次重放；⑧ 与 B 套的 4/5 是同一动作的两种说法；⑨ 是锚不是性质 ⇒ 独立性质约 **6 族**，不能称"9 个独立性质全真" | 见 §2 各行依据；`stored`==DB 逐字段相等即"构造相等"的证明 |
| G7 | 第 5 项标签"块落位"易误读：[4005,4096) 是 **ask 前重放位置**；save 后块在 **[0,90]**（DB `block.pos_lo=0, pos_hi=90, position0_owner='seq1'`），`a4.blocks[0]` 也是 0/90 | DB block 行 + a4.blocks |
| G8 | output filter 的 `after_len` 与 `display_len` **互相矛盾**：answer0 `after_len=45` vs `display_len=44`（=len(answer_display)=44）；answer1 `24` vs `23`。`tag_chars_removed=8` + 去掉标签前换行 1 = `removed_chars/delta=9` 才是自洽的 | a4 `answer_checks[*].output_filter` vs `display_len` |
| G9 | "三个未闭项"无原文落点（见 §3 末） | M4-ACCEPT.md 无该表；§6.7 只有 2 编号 |

**放行条件（`M4-ACCEPT.md` §6 三条）现状：全部落地，可清零**
1. `</think` 泄漏 ⇒ 输出层已过滤并留痕：`per_tag_count=1`、`removed_chars=9`、`display_len=44/23`、`diff_explained=true`、`idempotent=true`、`unknown_angle_tokens=[]`、`raw_kept_unchanged=true`、`display_has_tag=false`，且 `acceptance.output_layer_clean=true`（会失败的断言在）；**附 G8（after_len 口径错，不影响上面这几条）**。
2. 补"同一 M4 布局删掉车牌句"对照 ⇒ `a7` **4 臂**（product_block_control / reencoded_with_sentence / ablated_without_sentence / **length_matched_control**，均 `n_predict=64`，等长对照 91 cells / `blk_conv_platematch_attempt7`），答案 **浙B-3F19K / 浙B-3F19K / 苏A12345 / 浙Q-00000**，verdict `memory_carried_by_that_sentence_content_not_length`，`direction_was_not_preselected=true` ✓。
3. R9 去重 + `memory.type` 空列 ⇒ 已落地：`memory_source` 5 单元（fanout 1/1/2/1/2）、`memory.type` = fact×3/constraint/identity/plan（无 None）、`resolved`/`resolved_to` 两列在（mem3 `in_sentence`→「每天早上七点半出门」，其余 `no_reference`）✓。

## 6 结论（≤5 条 + 签判）

1. **九项（`§6.3` 字面）不可签"全真"**：**7/9 通过、2/9 未通过**（G1 `memory_source` 7→**5**；G2 检索作答 9/9→**2/2**），0 未接上、0 未做。把这两处数改对后，可签"9/9 台账与产物一致"。
2. **可签"M4 端到端链路成立"**：a4 `acceptance` **17/17 全 true**，且我逐项抽查都落回字段/文件；四把锚（a4 `59edbd82d4b9ae44` / 块 `81127d24fd64b96b`·9,507,412 B / DB `fd244c80c0cc974d` / write `6408d8e2ecdf6ee5`）全部重算相等；块正文 127 字、6 条 span 逐字在内、value ⊂ span；`stored`==DB 6 行逐字段相等。
3. **三个未闭项**：`F-M4-3` 已闭（17:40，`3309fb25`）；`F-M4-1` **仍未闭**（产物无 `n_predict` 读回，a7 只有"声明 64 / 引擎 null"）——**不阻塞验收**，但阻塞"n_predict 生效"类断言；"版本差异"项须从"16 键"改成 **17 键**（G3）。
4. **可签"M4 已验收"（附 5 个条件）**：① 改 `§6.3` 第 7/8 项的数；② "16 键"→"17 键"（两处）；③ `§12.1` 登记 `F-M4-1` 未闭 + `§6.7` 版本注记更新；④ 补 `run_m4_verify.json` 锚漂移记录（`bdf392e8`→`857f13c5`）并把"锚四把"写进验收结论；⑤ 把 `M4-ACCEPT.md` / `m4/README.md` 收回工作区（或在判决里写明"判据原文以备份 sha `c4186107246dd35d` 为准"）。阻塞条件（等 M4-C）已消失（17:40 结项）⇒ **现在可以验收定稿**。
5. **两件引用提醒**：a4 的 `dedupe.keeps=7` 与 `judge.keeps=6` 不是矛盾（前者是去重测试第二轮），引用必须写清；B 套（`M4-ACCEPT.md` §0）的 pid 是**版本内瞬时值**，验收只断言"新进程/`child_of` 关系"，不许沿用具体 pid。

**签判汇总**
| 判词 | 判 |
|---|---|
| "九项全真"（`§6.3` 字面） | **不可签**（2 项数错；改数后可签） |
| "M4 端到端链路成立（17 键机器自证）" | **可签** |
| "M4 已验收" | **可签（附 §6 条件 1–5）** |
| "9 个独立性质全真" | **不可签**（G6：独立性质约 6 族 + 1 锚） |
| 三个未闭项已清零 | **不可签**（`F-M4-1` 未闭；不阻塞验收） |

## 7 复算口径（可复跑）

```python
import json, sqlite3, hashlib
d = json.load(open('kvmem/m2_visibility/m4/run_m4_verify_a4.json', encoding='utf-8'))
w = json.load(open('kvmem/m2_visibility/m4/run_m4_write.json', encoding='utf-8'))
assert hashlib.sha256(open('kvmem/m2_visibility/m4/blocks/blk_conv_2026-10-25_01.kvmem','rb').read()).hexdigest()[:16] == '81127d24fd64b96b'
turns = {s['turn'] for s in w['judge']['per_sentence']}            # -> 9
assert w['judge']['sentences'] == 10 and w['judge']['keeps'] == 6  # 2,3
assert len(d['blocks']) == 1 and d['blocks'][0]['cells'] == 91     # 4
step = [s for s in w['lease_chain']['steps'] if s['step'] == 'reload_and_place'][0]
assert step['range'] == [4005, 4096] and step['pos_max_raw'] == 4095   # 5
con = sqlite3.connect('kvmem/m2_visibility/m4/m4_memory.db')
assert con.execute('select count(*) from memory').fetchone()[0] == 6          # 6
assert con.execute("select count(*) from memory where anchored_time='2026-10-28'").fetchone()[0] == 1
assert con.execute('select count(*) from memory_source').fetchone()[0] == 5   # 7 = 5（台账写 7 ⇒ 错）
assert len(d['search_checks']) == len(d['answers']) == 2                      # 8 = 2/2（台账写 9/9 ⇒ 错）
assert all(v is True for v in d['acceptance'].values()) and len(d['acceptance']) == 17  # C 套
```

## 8 更正记录（2026-10-25 19:55；§1–§7 一字未改，逐条在此更正）

> 触发：做 lead 验收定稿的字节复核时，回到 `outfilter.py` / `m4_display.py` 读实现。**我自己的两条判断要改**（不是 lead 的）。

| # | 我的原文 | 更正 | 依据 |
|---|---|---|---|
| **C1** | §5 `G8`「output filter 的 `after_len` 与 `display_len` 互相矛盾（45 vs 44、24 vs 23），建议 `after_len` 改 44/23 或删字段」 | **撤回 G8（我的误判）**。`after_len` 是**标签删除后、空行尚未折叠**的 stage-1 长度；`display_len` 是交付串（`BLANK_RUN.sub("\n\n")` 把 3 个换行折成 2 个）的 stage-2 长度。差 1 = 空行合并，**不是矛盾**；`tag_chars_removed=8`（只算标签，可归因）与 `raw_to_delivered_delta=9`（raw→交付）本来就是两个口径，字段名已分开。**不要**按我旧文把 `after_len` 改成 44/23 —— 那会改坏一个正确的中间量 | `outfilter.py:80-99`（`clean = ANY_RX.sub("", raw)`；注释原文 "the display layer also collapses blank runs -- keep those two apart"）；`m4_display.py:55-67`（`BLANK_RUN.sub("\n\n")`）；`m4_display.py:101-121`（`assert_diff_explained` 明确允许 `count("\n") >= 3` 的空行删除）⇒ 与 M4-ACCEPT 放行条件 1-R10「标签 + 由此产生的连续空行合并」一致 |
| **C2** | §5「放行条件（`M4-ACCEPT.md` §6 三条）现状：**全部落地，可清零**」+ §6 第 4 条同句 | **收紧为：条件 2、3 全落地；条件 1 = 部分覆盖**。标签侧确实闭了（白名单 + 计数 + 会红的断言 S2 `ControlTagLeft` + 块正文 REFUSE），**但** §1 并列要求的「**重复句处置**」未做：交付串 `answer_display` 仍是同句两遍、`content_warnings=[]`、`m4_display.py:148 first_sentence_only()` 存在而交付路径 `derive(first_sentence=False)` 未启用 ⇒ 判「M4 通过」时必须带 **O1 部分覆盖** 的限定 | `a4.answer_checks[*].answer_display`；`m4_display.py:145-166`；`run_m4_accept_recompute.json.open_items[O1]` 读数与我一致 |

**连带影响（给 lead）**：① 判决 `M4-ACCEPT-lead.md` §6 的 `G8` 与 `M4-ACCEPT.md §11 R5` 应随 **C1 撤回**（建议直接删该行/该条，别去改 `after_len`）；② §3 的 `O1`「部分覆盖」写法比我旧 §5 准（**C2**）；③ 本文件 sha16 因本节而变，`PROGRESS §6.3` 与判决里引用的 `cc029fc23dabd488` 需改成新值（原 `cc029fc2` 作初版保留引用）。