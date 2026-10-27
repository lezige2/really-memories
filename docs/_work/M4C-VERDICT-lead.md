# M4-C 验收判决（lead 签发 · 2026-10-25 16:50 本地 / 08:50Z）

> 只做验收判定，不改码、不跑引擎。数字出处 = 产物文件名（sha16 可由字节复算）或 `文件:行`。
> 四态闭集：**通过 / 未通过 / 未接上 / 未做**。**判据作废不进四态**，进 §6 决策记录。
> 复核链：lead 逐份复算 → inspector 独立审计（`INSPECTOR-M4C-P2.md` §2/§3）→ lead 按反驳改判。

---

## 0. 一句话（三句，先看这里）

1. **六份产物可签**：b09 台账 + 14B 装置 + 本夹具观测面上，六臂读数与 §4.5 逐项一致（§2/§3）。
2. **M4-C 的实质结论只到这里**：删 `m1.unmount.after_detach` 的 `leases.reset` **会被域内调用流断言抓住**（级=**调用流**，不是 `cells_of`、不是下游后果）；删 `chat.place.fresh` 的 `leases.reset` **在本夹具观测面上未观察到任何读数变化**；四站"承重断言全红"判据（v1①）**已因 shim 自清而作废**；真正可能承重的**池容量（M4-C-4）未做**。
3. **不签"这些内存管理机制在承重"这个总结论**：本批只证到"删一处会被发现 / 另一处删了没差别"，没有一处证到"删了会造成后果"。

---

## 1. 装置（先签装置，否则读数无处挂）

| 证据 | 值 | 出处 |
|---|---|---|
| 模型 | 14B Q4_K_M，sha16 `0b319bd0572f2730`，8,988,110,240 B | HANDOFF §1；`kvmem/chat.db` 两行 `model_size` |
| 源码两处常量 | `tools/chat.py:47`、`tools/memory_source.py:51` 均 14B | 实读 |
| 块字节公式 | `5,224,388 = 1188+104464×50`；`3,761,892 = 1188+104464×36` | 块文件实测 + `tmp/build-14b.log` |
| per-token KV | `102.0 KiB (q8_0)`，只有两块，build exit 0 | `tmp/build-14b.log` |
| 台账 b09 | **9/9 复算相符**（lead 16:28 / inspector 16:31 各一次），自身 sha16 `1efd3701c335b518` / 1228 B，`sample_gap_s=32`/`samples=2`/`identical=true`，`verify_landed("b09")==0` | `out/LANDED-b09.json` |
| 台账覆盖 | `land.py` FILES 9 项（含自身、`tools/memory_source.py`）；`m4c_harness.py:88-91` LANDED_FILES 8 项 | 实读 |
| 快闸 | `SELFCHECK-0f699908.json` `5fc96db90cce689f` / 2041 B，12 gates + retired step11，**进程 exit 0**（产物无 `exit` 字段，共 9 键；PASS 见 `tmp/selfcheck-b09.log`），`products_cited` = b09 inject + b09 deleted | 产物实读 + `tmp/selfcheck-b09.log` |

**装置边界（G6）**：模型指纹**不在**台账（`land.py` 只收 repo-relative；gguf 在 `D:\models`），六份产物 `*model*` 字段 **0/6** ⇒ 装置身份靠"源码 sha + 块字节公式 + DB 指纹"三条**外部**证据钉住，**产物本身不自证装置**。

**回归锚（单列，不是 14B 证据）**：`kvmem/sessions/live.json` 配方 → **`fa94b1bc58c0e421`**（lead 16:28 重算；mtime 03:33 未被六臂改写）。**它是 7B 时代产物**（`model.model_path`=7B/4,683,073,504 B）⇒ 只能签"旧存档未被本轮改写"，**不能当 14B 装置证据**。

---

## 2. 六份产物逐份（sha16 均由 lead 从磁盘字节重算，inspector 独立复算一致）

共同：`batch_id="b09"`；`chat_py_sha16="cb70be52eef253fa"`（=b09 台账 `tools/chat.py`）；`sampled_at` 08:23:18Z–08:27:01Z 全晚于 b09 ts 08:20:10Z；`harness_sha16` 首段 = 台账（site3 四臂 `805482eab7236d41`、DELETE 两臂 `85d3b0b0855a83d4`）。

| 臂 | 产物 / sha16 / B | 关键读数 |
|---|---|---|
| green | `M4C-SITE3-green-b09-green-b11f1875.json`<br>`f3f6ce7fe5f04040` / 7781 | 产物 exit 0（进程 0）· is_red false · die null · `hits []` · coverage_ok true · covers ['site3'] · asserts 2/2 · identity ok · selfev TTT · 范围断言 `[]/[]`、`[2]/[2]`、`[1]/[1]` 全 checked · `turn_orphan` orphan 0 / chat_n 0→63→108 · `chat.attach` 事件 **3 条**（[1,2,1]） |
| red | `M4C-SITE3-red-b09-red-1b6187f9.json`<br>`dd46774cae873989` / 5750 | **产物 exit 1**（进程 0：expected_red ⇒ `m4c_verdict.py:139`）· is_red true · expected_red true · die_kind assertion · assertions_status assertion_failed · deleted_line_no 562 · src/var 700/700 · variant `0c149c11f3d8a0d0`（磁盘变体：L562=`pass  # M4C-DELETED-SITE-3`）· die=`M4-C 范围断言红 @m1.unmount: 调用流 hits=[]（0 条） != dropped=[2]（1 条）` · selfev TTT |
| inject | `M4C-SITE3-green-b09-inject-18d4a704.json`<br>`62e7973dfa1287c3` / 1315 | 产物 `exit null`（正当缺席：`run_site3.py:83-88` 只在 `drive()` 内赋，本臂在 drive 前抛）· **进程 5** · finalized false · `finalize_error=FileNotFoundError …no_such_fixture.py` · instrument finalize_error · hits `[finalize_error, not_finalized, coverage_shape, asserts_short]` · selfev **(T,F,T)** · identity **missing**（`m4c_harness.py:124-125` 显式设计）· fixture_from_env true · **lead 重算 `V.verdict(rec)=5`** |
| drop | `M4C-SITE3-unmount-dropnonempty-b09-drop-014ff511.json`<br>`1636404475cf5390` / 7796 | exit 0 · `hits []` · coverage_ok true · dropped_count 2 · die null · **与 green 只有 4 个挥发键不同**（`mode/run_id/sampled_at/assert_log_path`）⇒ 增量判别力 **0**（G2） |
| base | `M4C-DELETE-SITE1-base-b09-base-e6463aa2.json`<br>`12950f6a3fd0226f` / 3806 | exit 0 · is_red false · `hits []` · coverage_ok true · covers ['site1'] · asserts 2/2 · selfev TTT · **attaches_done 2 / attach_events_ok true / attaches_expected_min 1** · `loads=[{seq1 profile 50/50/49},{seq2 project 36/36/35}]` · variant=原文件 |
| deleted | `M4C-DELETE-SITE1-deleted-b09-deleted-2c795100.json`<br>`55cd3ba5216293b5` / 3858 | 同上 · **loads 与 base 逐字段相同** · deleted_line_no 270 · variant `1612061e38629bc9`（磁盘变体：L270=`pass  # M4C-DELETED-SITE-1`，700 行，`leases.reset(` 5→4） |

**每臂四态**：green **通过** · red **通过** · inject **通过** · drop **通过**（但增量 0）· base **通过**（限"本夹具观测面"）· deleted **通过**（限"本夹具观测面"）。

---

## 3. §4.1 四处落地审计

| 落地 | 状态 | 位置 |
|---|---|---|
| (a) `cmd_chat` attach 后 `_event` | 落 | `tools/chat.py:311`（`_event` 在 `:102` 写死 `role="event"/site=None`） |
| (b) `cmd_m1` attach 后 `_event` | 落 | `tools/chat.py:605` |
| (c) 三条件自检（`id/role/site`） | 落（**形态改判**） | 运行时：`redcheck_delete.py:35-51` 落 `attach_events_ok` → `m4c_verdict.py:101-105`（`attach_config_not_met`，三态 None=不声明不判）；跑前静态：`m4c_selfcheck.py:385-389 step13_attach_wiring`（AST 数两个 `_event` 生产者） |
| (d) `attaches_done` 期望 `>=1` | 落并被消费 | `redcheck_delete.py:76 attaches_expected_min:1`；两臂实测 `2/True` |

**判定**："跑前自检"字面在架构里没有位置（日志跑后才存在）⇒ 现形态"跑前静态 + 跑后运行时"覆盖同一意图，**接受，记形态改判**。

---

## 4. 判据判决（权威出处 → 现行处置 → 本轮读数）

| # | 判据（出处） | 判 | 依据 / 读数 |
|---|---|---|---|
| 1 | **v1①** 四条承重断言全红可复现（`PROGRESS:1757` §13.2①） | **判据作废**（§6-①） | 前提被 `kvshim.cpp:573`（`kvshim_load` 无条件先 reset 该 seq）证伪；ledger L3771 已裁 v1 作废。**附记录**：site3 一条红可复现（见 #2） |
| 2 | **v2①-a** 站点 3 一条承重断言可红可绿（HANDOFF §2 现行） | **通过** | green/red 同批同装置：green 范围断言 checked（`[2]/[2]`、`[1]/[1]`）；red 删 L562 后 `hits=[] != dropped=[2]` ⇒ die ⇒ `is_red true`/产物 exit 1。**签名范围 = 「删行被观测到」（调用流层）；不签：「`cells_of` 级」「下游后果级」** |
| 3 | **v2①-a 的 `cells_of` 级读数**（DESIGN §1 站点 3 指定：红时 `cells_of=n`） | **未做** | 本批红落在 A 判据，`cells_of` 见证者被抢死、本臂未响。**臂级旧字节**：`M4C-SITE3-red-attempt7` die=`cells_of(seq 2) = 36, expected 0`，attempt1–6 为 `cells_of(seq 1) = 50`；**b06 的 red 与 b09 同型（A 判据），不是见证者红** ⇒ 均非当前身份（G5）。单元级另有 `WITNESS-ZERO-feed-3e1e362b` |
| 4 | **v2①-b** 承重到下游（HANDOFF §2） | **判据作废**（§6-②） | 无下游读者（存档只读已挂载列表 / detach 已摘引用 / 再挂载先清后用）⇒ 要求的东西不存在。真实承重对象 = 池容量（#9） |
| 5 | **§13.2 ②** 恢复后全绿（`PROGRESS:1757`） | **未做** | "四站恢复后全绿"本轮只到 2/4：site3 green 无 die、site1 base 无 die；site2/site4 未跑。（HANDOFF §2 的"② 未通过(1/3)"是旧计数，见 G13） |
| 6 | **§13.2 ③** 三份 session 剔除 `saved_at` 后 sha 仍 `fa94b1bc58c0e421` | **判据作废（原字面）**（§6-③） | 盘上 **4 份**真实 session（`live/s/s_2/bridge`），锚 `fa94b1bc58c0e421`/`5ee2102ee068386a`/`f4264c9f2ea9393e`/`e438967a31f25466` **互不相等**，且**全是 7B 时代** ⇒ **当前盘面不能复现**；03:22 那次读数所用文件已被 03:33 的存盘覆盖、**不可复核** ⇒ 冲突记 G13-②；14B 后新存盘必带新 `model`/`blocks` ⇒ 字面亦不可能再成立 |
| 7 | **③ 新形态**：同一状态改动前后各算一次（14B 基线） | **未做** | 本轮无存盘；基线记为 `fa94b1bc58c0e421`（7B 时代读数，可签为"未被改写"） |
| 8 | **⑤** control | **作废** | `control` 机制已删（HANDOFF §2）；drop 臂的 control 读数在 green 臂里同样存在（G2） |
| 9 | **M4-C-4** 池泄漏（orphan/chat_n；`chat.py:614-625`） | **未做** | 绿臂读数在（orphan 0，chat_n 0→63→108 解耦），**红未证**：删 L562 后范围断言先 die，漏清断言没被红到 ⇒ "承重到池容量"缺臂级证据 |
| 10 | **M4-C-3** 检索面/未建块 KeyError | **未做** | 本批未测（DB 旧读数：10 源 / 2 建块 / 8 未建） |
| 11 | **v2②** 三处冗余有实测对照（ledger L3772；**非判据**，L3775"冗余证明不是判据、不计入验收"） | **记录 1/3**（不进四态） | site1：b09 DELETE 两臂 loads 逐字段相同、无 die（本批实测）；site2：只有 7B 时代"未红"旧产物（`M4C-RED-SITE2`，不算"删与不删全同"对照）；site4：无 |

---

## 5. 本项目 M4-C 的实质结论（给验收者的一句话版）

**删 site3 的 reset ⇒ 被"清理循环覆盖了被丢集合"这条调用流断言抓住；删 site1 的 reset ⇒ 本夹具观测面无任何读数变化；其余两站与池容量未测。** 对**下游可观测后果**，四处 `leases.reset` 都不是承重者：`kvshim_load` 自己先清空 seq（`kvshim.cpp:573`）⇒ 不叠、不 `2n`、不越界（ledger `:3762` 只支持这一点，**不支持"引擎状态不变"**）。但**"detach 之后、下一次 load 之前"的瞬时 cell 占用确实不同**（attempt7 的 `cells_of(seq 2)=36` 就是证据）——**那正是 M4-C-4 未证的部分**。所以四处 reset 的真实作用只剩"租约表记账"与"确保无后续观察者时 cell 池不泄漏"；**后者是本批唯一可能的"承重"候选，未做。**

---

## 6. 决策记录（作废 / 改判，不进四态）

- **① v1① 作废**：前提被 `kvshim.cpp:573` 证伪（删任何一处 reset 都**不会产生预登记的下游红读数**：不叠、不 `2n`、不越界）。留档理由：否则将来没人知道标准被改过。
- **② v2①-b 作废**：无下游读者（第四腿"消费者"缺失）。
- **③ §13.2 ③ 原字面作废**：盘上 4 份 session 锚互异且全 7B 时代（G13）。
- **④ §4.1(c) 形态改判**："跑前自检"不可实现 ⇒ 改"跑前静态 + 跑后运行时"，同一意图。
- **⑤ A 判据的合法性与证明力上限（G8，待用户确认措辞，不阻塞六臂读数）**：DESIGN §5 明列"❌ 断言 `leases.reset` 被调用了几次——桩自证"。**该条已被后续裁定取代**：HANDOFF §5.3（`cells` 见证者判空集、覆盖改由调用流判据承担）、ledger `:4165`（端点比对在范围问题上原理上不成立 ⇒ 换调用流）、`:4174`（调用流断言 = 唯一签名依据）。但 A 判据两侧（`leases.sites` 桩记录 vs 调用方 `dropped` 名单）**都来自租约层**，按纪律 40 属"表读表"⇒ **它只能证"该行被执行"，不能证"承重"**。**本判词按现行裁定签 #2 通过，并把签名范围限死在"删行被观测到"；若用户否决上述裁定、恢复 DESIGN §5 原措辞 ⇒ A 判据非法 ⇒ 仅 #2 改判"未接上（判据合法性未定）"，其余各行不受影响。请用户确认并更新 DESIGN §5 措辞。**

---

## 7. 缺口清单

- **G1** site1 结论**双向受限**：只能写"b09/14B/本夹具/place 路径上删 site1 reset **未观察到读数变化**"；**既不能写"冗余/不承重"**（reset 与 `pass` 在本路径观测面不可区分：load 从 0 重写 + 启动 seq 空），**也不能因此推"所以它承重"**——该臂对"承重/不承重"判别力 = 0，`site1.place` 判据自述"删掉不会红"（`chat.py:281`）。
- **G2** 第六臂 drop 与 green **只有 4 个挥发键不同** ⇒ 六臂实际独立读数 5 份；根因 `run_site3.py:66` 对超 `want_sequence` 的轮次**静默返回 `[]`**（默认全丢），第 4 轮 = 3 声明 + 1 默认。
- **G3** `exit` 一词两义：green/red 行按**产物字段**、inject 行按**进程码**；inject 产物 `exit=null`；六份产物**无 `tag` 字段**（文件名承载 tag）。
- **G4** 写死字符串两处：`why_empty`（`run_site3.py:108`）被同记录 `cells=36` 反驳（36 是卸载**前**读数，不是泄漏值）⇒ 报告须写"红臂 die_before_control，控制项不适用"；`sites_readers` 的 `"chat.py L563"` 也是 `run_site3.py:102` 写死，范围断言 die 实际在 `chat.py:567`。
- **G5** `cells_of` 级红本批**未复现**（被 A 抢死）：臂级证据只有 attempt 时代旧字节（attempt7 `cells_of(seq2)=36` / attempt1–6 `cells_of(seq1)=50`；**b06 red 的 die 是 A 判据，不是见证者**）；单元级 `WITNESS-ZERO-feed-3e1e362b`。
- **G6** 14B 模型指纹不进台账；产物 `*model*` 0/6。
- **G7** sha16 同时承载内容与行尾：本轮 `chat.py` 34288→34319 = **+1（模型行）+30（LF→CRLF）**（inspector 用 snap 去行尾比对：内容差异仅 `:47`/`:270`；算术逐字节吻合）⇒ 接受不重做；建议 `.gitattributes` 或 `land.py` 记 `crlf_lines/lf_lines`。
- **G8** A 判据的合法性与证明力上限（见 §6-⑤）：DESIGN §5 该条已被 HANDOFF §5.3 + ledger `:4165/:4174` 取代，**请用户确认更新 DESIGN §5 措辞**；A 判据属"表读表"，只证"被执行"、不证"承重" ⇒ 交付里凡引它，必须同时写这一句。
- **G9** 六臂**不是一次跑齐**：runner 按"进程码=1"在 red 处误停（`tmp/sixarms-b09.log` 只有一行 `STOP: red exit=0 want=1`）；后四臂另跑并落 `tmp/fourarms-b09.log`（逐臂 start/end/exit），green/red 另有 `tmp/arm-*.log`。六份产物各一份、sampled_at 唯一 ⇒ **每臂一次、读数唯一性未破坏**；但 `sixarms-b09.log` 不能当"一次跑齐"证据。
- **G10** red 的 `exit 1` 是产物字段，**不是进程码**（进程 0）。
- **G11** 卫生：4 个 `.tmp` 残留、**14 个** `__pycache__` 未清。
- **G12** HANDOFF §5 九项未做：`except OSError: pass` 收异常三处同批、`cells_of` 出错折 1、见证者 `no_discrimination` 删除、`redcheck.py` run_id+tag、`def_mismatch_detail` 未读谓词、`stale` 谓词挪快闸、M4-C-3 skip 出声、M4-C-4 orphan、restore 后每 seq 装载定义。
- **G13** 文档冲突三处：① HANDOFF §2「② 未通过(1/3)」与 ledger L3771/L3775（v1① 已作废、v2② 只作记录）冲突；② `PROGRESS:802`「三份 session 剔除 saved_at 后全等」与盘上 4 份/4 锚不符；③ `PROGRESS:1757` §13.2① 未标注"已作废"。
- **G14** 静默变绿入口仍在：`cells_of` 的 `except: return 1`（`m3_lease.py`）与 `except OSError: pass`（chat.py 日志写）未修 ⇒ 异常时会给一个非红值。

---

## 8. 下一步（按优先级）

1. **M4-C-4 臂**（唯一能把"承重"从调用流级抬到后果级的实验）：临时旁路 A 判据或加"只判 orphan"模式，证删 L562 后 `orphan=36 ≠ 0`；并按 ledger 要求**逐轮记 orphan + 断言 max**（末轮重挂会把末态 orphan 抹回 0）。
2. **site3 的 `cells_of` 级红**：同臂让见证者先于 A 响（或临时禁 A），补齐 #3。
3. **site1 红场景**：同引擎二次放置（期望 `n_tokens=2n`，DESIGN §1）；**site4 红场景**：脏 seq 不进 `mounted`（DESIGN §4）。
4. M4-C-3（未建块 skip 出声）与 HANDOFF §5 其余项。
5. 记录级小修：G2/G3/G4/G7/G13（不动判据、不重跑读数）。

---

## 9. lead 自评（判词变化与责任）

1. **差点把"loads 相同"读成"site1 不承重"** —— inspector 按 §6.1（判据自身判别力=0）+ 结构性不可区分反驳，改成"未观察到破坏"并加双向声明（G1）。
2. **差点按 7B 跑六臂**（"14B 未接上"）—— inspector 按 §7 用户裁定反驳：读 7B 即越权；改为先接 14B 再跑。
3. **初稿两处判错被 inspector 抓住**：把 v1① 写成"未通过 1/4"（应为**作废**）；把 ③ 写成"磁盘只有 1 份 session"（实际 **4 份**、锚互异、全 7B 时代）。均已改。
4. 执行侧两处口径错由复核抓出：green"4×chat.attach"（实为 3）、red"进程 exit 1"（实为产物字段）。
5. 六臂非一次跑齐是**执行侧主动报**的；"每臂只跑一次"由我按六份产物时间戳唯一 + sha 唯一核过。
6. 本轮 lead 只做只读复算（重算 sha / 字段 / 纯函数 `V.verdict`）、未跑引擎、未改任何代码或数据；本文件是唯一写入。

---

## 10. 签署栏

| 项 | 内容 |
|---|---|
| 签署人 | lead（本会话） |
| 签署范围 | §2 六臂读数（14B / b09 / 本夹具观测面）· §4 #2（**限"删行被观测到"，调用流层**）· §1 装置三条外部证据 · 快闸 `SELFCHECK-0f699908` PASS |
| **未签** | "机制承重"总结论 · `cells_of` 级红 · 下游后果级 · site2/site4/池容量 · 四站"恢复后全绿" · 14B 指纹进台账 |
| 依赖 | 仅 §4 #2 依赖 §6-⑤ 的现行裁定（HANDOFF §5.3 + ledger `:4165/:4174`）；用户若否决该裁定，只改 #2，其余不变 |
| 可复算 | 六份产物 sha16 / 台账 9/9 / 锚 `fa94b1bc58c0e421` / 纯函数 `V.verdict` 全部可独立重算；本文件自身 sha16 见交付消息 |