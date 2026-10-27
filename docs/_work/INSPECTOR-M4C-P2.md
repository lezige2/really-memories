# INSPECTOR-M4C-P2 — 六臂产物独立验收

状态：**§1 是预登记（写于 16:26，六臂尚在跑）**；§2 起为看到全部产物后的审计，只许追加、不回改 §1。

## 1. 预登记（判据与判法全部来自 HANDOFF §4.5/§6，不是我选的口径）

**诚实披露已见值**：写本节时 b09 的 green（16:24:05）与 red（16:24:19）两份产物已存在，我只看过它们的 headline 字段：green `exit 0 / hits [] / die None / coverage_ok true / selfevidence (T,T,T)`；red `exit 1 / hits [] / die assertion / coverage_ok true / selfevidence (T,T,T)`。inject / drop / base / deleted 四份**尚未生成、未见**。

### 1.1 五条横切检查（每份产物都过）

| 编号 | 检查 | 判 |
|---|---|---|
| C1 | 六份 `batch_id` 全是 `b09`；`tag` 应为 `b09-green/red/inject/drop/base/deleted`（§4.3：tag 由 batch 派生，不许手写尝试号） | 不满足 ⇒ 该臂**未做** |
| C2 | `harness_sha16` 三段 = `(fixture_sha16, harness_sha16, verdict_sha16)`，逐段与 b09 台账比：site3 四臂首段必须是 `805482ea`（run_site3），DELETE 两臂首段必须是 `85d3b0b0`（redcheck_delete）；中段 `b48f037f`（m4c_harness）、末段 `f181518b`（m4c_verdict） | 任一段不入册 ⇒ **未做**，不签 |
| C3 | 产物 mtime > b09 mtime（16:20:10）且 `chat_py_sha16` = `cb70be52`（b09 在册） | 不满足 ⇒ **未做** |
| C4 | `selfevidence`：site3 四臂 + DELETE 两臂应 `(T,T,T)` 且 `identity_cross_check` 通过；**inject 臂期望 `(T,F,T)`**（版本项失败是设计，不是缺陷） | 见下 §1.3 |
| C5 | 旧批作废：b06 六份（15:46:16–39）与任何 `batch≠b09` 的产物一律不读（§6.13） | 引用即作废 |

### 1.2 §4.5 逐臂预期（照抄，不改）

| 臂 | 期望读数 |
|---|---|
| green | `exit 0`；selfevidence 三真；`hits []`；`coverage_ok true` |
| red | `is_red true`；`die_kind assertion`；`exit 1` |
| inject | selfevidence `(T,F,T)`；`instrument finalize_error`；`exit 5` |
| drop | `dropped_count > 0`；0 次 die |
| DELETE base | `attaches_done >= 1`；`coverage_ok true`；`loads` 与 deleted **逐字段相同** |
| DELETE deleted | 同 base |

四态映射（预登记，闭集）：
- **通过** = 该臂全部期望读数命中且 C1–C5 成立；
- **未通过** = 期望读数反了、且该读数是真读数（不是缺失、不是仪器错）；
- **未接上** = 该臂要求的信号在架构里没有位置/消费者/分母；
- **未做** = 无产物、产物旧批、或 C1–C3 任一项不过。
- **判据作废 ≠ 未通过**（先问「该判据要求的东西在架构里有没有位置」）。

### 1.3 预登记的「不能签」条件（先写死，避免看到数据再放宽）

1. 任一臂 C1/C2/C3 不过 ⇒ 该臂未做，六臂不齐不签整批。
2. **inject 臂**：`exit ≠ 5` 或 `instrument ≠ finalize_error`，或 selfevidence 版本项为 `True` ⇒ 未通过（仪器错没被抓住）。
3. **red 臂**：`die_kind ≠ assertion` 或 `exit ≠ 1` ⇒ 未通过；**唯一例外**：`die_kind` 为空但 `instrument_hits` 里是 drive 期异常 ⇒ 判**未接上**（仪器错，不是被测对象错），要点名。
4. **drop 臂**：只看到 `dropped_count > 0` 不够，必须有分母（`cells_readings_all` / `control` 的读数层）；无分母 ⇒ 按 §6.2 判「空集读数缺分母」，不能签「通过」。
5. **DELETE 两臂**：`loads` 逐字段（`seq/name/n_returned/n_tokens_after/pos_max_after`）必须相同；`attaches_done ≥ 1` 判通过，但若 `== 1` 必须能在 `assertions`/`attach` trace 里解释「另一条 `chat.attach` 路径为何没走」，解释不了 ⇒ 点名（不直接判未通过）。
6. **14B 物证（我自己加的独立判据，§6.18 的延伸）**：凡携带几何量的字段（`cells_readings_all`、DELETE 的 `loads`、`seqs_left_empty_per_turn`）必须与 14B 几何一致——n_tokens 50/36、块 5,224,388 / 3,761,892 B、**104448 B/格**；若出现 7B 量级（30,480 / 1,524,708 / 1,097,988）⇒ **装置没接上，整批不签**。
7. **同批一致性**：六份 `harness_sha16` 的三段必须彼此一致（同一批就是同一套字节）；任一份不同 ⇒ 那份不在本批。

## 2. 审计（16:30–16:32；§1 一字未改）

### 2.0 复核 lead 的数字表 —— 六份文件 sha16/bytes **逐份 agree**

| 臂 | 文件（`kvmem/m4c_leases/out/`） | 我算 sha16/B | lead 给 | 判 |
|---|---|---|---|---|
| green | M4C-SITE3-green-b09-green-b11f1875.json | f3f6ce7fe5f04040 / 7781 | 同 | agree |
| red | M4C-SITE3-red-b09-red-1b6187f9.json | dd46774cae873989 / 5750 | 同 | agree |
| inject | M4C-SITE3-green-b09-inject-18d4a704.json | 62e7973dfa1287c3 / 1315 | 同 | agree |
| drop | M4C-SITE3-unmount-dropnonempty-b09-drop-014ff511.json | 1636404475cf5390 / 7796 | 同 | agree |
| base | M4C-DELETE-SITE1-base-b09-base-e6463aa2.json | 12950f6a3fd0226f / 3806 | 同 | agree |
| deleted | M4C-DELETE-SITE1-deleted-b09-deleted-2c795100.json | 55cd3ba5216293b5 / 3858 | 同 | agree |

- b09 台账 16:31:44 复算 **9/9**（同意你 16:28 的复算）。
- `SELFCHECK-0f699908.json`：12 gates（`gates_passed` 列全）+ `gates_retired=['step11_docstring_only']`，self `c14c5c82` / verdict `f181518b`，`sampled 08:27:45Z`（六臂之后），`products_cited` = b09 inject（`62e7973dfa1287c3`）+ b09 deleted（`55cd3ba5216293b5`），两个 sha 与我自己算的**一致** ⇒ **P1B §3.8 的缺口④（b09 字节上无快闸）已闭**。
- 六份产物 `*model*` 字段数 **0/6** ⇒ F2 缺口的产物侧证据成立（装置只能物证溯源）。

### 2.1 逐份读数（我从产物里独立读，不抄 lead）

| 臂 | 产物 `exit` | 进程码 | is_red | die_kind | hits | cov | asserts | self | identity | chat_py | harness 三段 | sampled |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| green | 0 | 0 | false | null | [] | true | 2/2 | TTT | ok | cb70be52 | 805482ea:b48f037f:f181518b | 08:23:18Z |
| red | **1** | **0** | true | assertion | [] | true | 2/2 | TTT | ok | cb70be52 | 80548…:b48f…:f181… | 08:24:05Z |
| inject | **null** | **5** | null | null | [finalize_error, not_finalized, coverage_shape, asserts_short] | null | 0/None | **T,F,T** | **missing** | cb70be52 | **null** | 08:26:27Z |
| drop | 0 | 0 | false | null | [] | true | 2/2 | TTT | ok | cb70be52 | 80548…:b48f…:f181… | 08:26:27Z |
| base | 0 | 0 | false | null | [] | true | 2/2 | TTT | ok | cb70be52 | 85d3b0b0:b48f037f:f181518b | 08:26:47Z |
| deleted | 0 | 0 | false | null | [] | true | 2/2 | TTT | ok | cb70be52 | 85d3b0b0:b48f…:f181… | 08:27:01Z |

臂内特字段：
- **green**: `chat.attach` **3** 条（seq `[1,2,1]`）；`dropped_count 2`；`cells_control_empty_seq {seq:1, cells:0}`；`control_seq_in_use true`。
- **red**: `chat.attach` **2** 条（`[1,2]`）；`dropped_count 1`；`deleted_line_no 562`、`variant_sha16 0c149c11f3d8a0d0`、`src/var 700/700`；`die_message` = `error: M4-C 范围断言 @m1.unmount: 丢下 hits=[]，0 命中 != dropped=[2]，1 命中`；`assertion_failed_in_log true / contract_ok true`。
- **inject**: `finalize_error` = `FileNotFoundError: ... no_such_fixture.py`；`fixture_from_env true`；`assertions []`；`harness_sha16 null`。
- **drop**: `chat.attach` **3** 条（`[1,2,1]`）；`dropped_count **2**`；`cells_readings_all` 10 条；`cells_control_empty_seq {seq:1, cells:0}`；`die_kind null`。
- **base / deleted**: `chat.attach` 各 2 条（`[1,2]`）；`attaches_done 2` / `attach_events_ok True` / `attaches_expected_min 1`；`site1.place` checked ×2；`loads` = `[{seq1,profile,50,50,49},{seq2,project,36,36,35}]`，**两臂逐字段相同**；deleted 另带 `deleted_line_no 270` / `variant_sha16 1612061e38629bc9` / `700/700`。

### 2.2 横切 C1–C5 —— 全过，另两条读数

- C1 batch 六份全 `b09` ✓；tag 只能从**文件名**核（产物内没有 `tag` 字段）：`b09-green/red/inject/drop/base/deleted` ✓（§4.3 要求 tag 由 batch 派生——文件名合规，内容不载 = 小缺口）。
- C2 `harness_sha16` 三段逐段入 b09 台账 ✓：site3 四臂首段 `805482ea`（run_site3）、DELETE 两臂 `85d3b0b0`（redcheck_delete）、中段 `b48f037f`、末段 `f181518b`。
- C3 六份 `sampled_at` 全 > b09 ts（08:20:10Z）✓；`chat_py_sha16` 六份全 `cb70be52` ✓；文件 mtime 16:24:05–16:27:16 ✓。
- C4 `selfevidence`：五份 TTT + inject (T,F,T) ✓（正好是 §4.5 要的形状）；`identity_cross_check`：五份 ok + inject missing（`m4c_harness.py:124-125` 的显式设计：注入产物读不出版本身份 ⇒ missing 不算矛盾）。
- C5 六份全是 b09 新批；我另用 `V.verdict(产物 rec)` 重算六份，rc = 0/0/**5**/0/0/0 —— 与各自 `instrument_hits` 一致，inject 的 5 由此可**从产物重算**。
- **进程退出码的实际来源不是产物**，是 `tmp/arm-*.log` 与 `tmp/fourarms-b09.log`：green 0、red **0**、inject **5**、drop/base/deleted 0；「六臂每臂恰好一份产物」⇒ 每臂只跑了一次，无重跑冒充。

### 2.3 逐臂四态判定

| 臂 | 四态 | 依据（§4.5 逐项） | 签字强度 |
|---|---|---|---|
| green | **通过** | exit 字段 0 / hits [] / coverage_ok true / selfev TTT / asserts 2·2 / cov ['site3'] | 全 |
| red | **通过** | 字段 exit 1（= 判据红）/ is_red true / die_kind assertion / hits [] / 断言文本落在 A 判据 / 进程码 0 = 期望红被接受 | 全 |
| inject | **通过** | selfev (T,F,T) / instrument finalize_error / 进程码 5（日志）+ 我重算 verdict=5 / fixture_from_env true | 全（附口径缺口 ①） |
| drop | **通过** | dropped_count **2** >0 / die_kind null（0 次 die）/ hits [] / coverage_ok true / cells 10 条分母在 | 全 |
| base | **通过** | attaches_done 2 ≥1 / attach_events_ok true / coverage_ok true / loads 2 条 | 限「本夹具未观察到破坏」（见 2.4-5） |
| deleted | **通过** | 同 base，且 loads 与 base 逐字段相同 / deleted_line_no 270 | 同上 |

**六臂六通过**，但 base/deleted 的"通过"只能覆盖到「本夹具观测面」，理由见 2.4-5。

### 2.4 答 lead 的五点

**1) green 的 `chat.attach` 到底是 3 还是 4：3。** 证据：green 产物 `assertions` 里 `id=="chat.attach"` 的条目 **3 条**，`seq=[1,2,1]`；同法 red 2（`[1,2]`）、drop 3（`[1,2,1]`）、base/deleted 各 2（`[1,2]`）。executor 的「4」错。**进缺口（报告级）**：不影响 §4.5，但它是 DELETE 臂 `attaches_done` 的同类计数，若报告里出现"4"会让人以为多走了一次 attach；正确口径 = 数 `assertions` 里 `id=="chat.attach"` 的条目，不按对话轮数估。

**2) red 的红落在 A 判据：满足，不是"一半"。** A 判据 = `site3.unmount.flow`（rule：sites 调用流 list == dropped，漏/多/重复/乱序四种都抓），其 assertion 文本出现在 `die_message`（`@m1.unmount: 丢下 hits=[]，0 命中 != dropped=[2]`），触发链 = 断言响 → `die` 事件（`kind=assertion`）→ `die_kind=assertion` → `is_red=true` → 产物 `exit=1`，**有消费者、有判别力**，且同批双向：green 里同判据 `checked`、red 里它响 ⇒ **可红可绿成立**。
但要说清两层：**cells 见证者本批确实没红到**（被 A 抢死）。它的"可红"不是靠嘴说：最新 `WITNESS-ZERO-feed-3e1e362b.json`（15:32:39）`criterion_valid true / died true / exit 1 / log_has_assertion_failed true`，而被测函数 `_m4c_witness_cells_zero` 所在的 `chat.py` 在 b09 里只改了模型字面量与行尾（P1B §3.1 已证）⇒ **单元级成立、本批未演示**。所以：若 v2①-a 指的是"A 判据可红可绿"⇒ 满足；若它要求"cells 见证者也要在本批红一次"⇒ 只满足一半，需另跑一次"拆掉 A 判据的同臂"（本批不做）。

**3) red 的 `cells_control_empty_seq {seq:2, cells:36}`：值是正当读数，`why_empty` 是记录缺陷。** 36 的来历可追：红臂 `cells_readings_all` 里 seq2 的最后一条读数就是 load 后的 36（A 判据抢死发生在它之后的 turn 里，drop 读数没再产生）⇒ cells=36 合法。矛盾在 **`why_empty` 是 `run_site3.py:108` 写死的字符串**（"本臂该 seq 刚 reset、其后无 attach（reset 契约给的空）"），不是由读数派生的解释 ⇒ 红臂里它被自己的 36 反驳。判：**§6.19/§6.4 类记录缺陷**（记录里写死一个结论，被同一记录的数据推翻而不响）；它**不被 verdict 消费**（`attach_readings`/`instrument_hits` 都不读它）⇒ **不影响本批验收**，但**报告不得引用"红臂控制项为空"**。修法：`why` 由 `cells==0` 派生，或改成 `control_applicable:false, why:"die_before_control"`。

**4) inject 可签，判通过。** 两个"缺失"都是**正当缺席**不是未接上：
- `exit=null`：`rec["exit"]` 只在 `drive()` 内赋值（`run_site3.py:83-88`），inject 的夹具加载在 drive 之前就抛 `FileNotFoundError`（`run_make` 的 try 里）⇒ 该字段在本路径**没有位置**（§6.18 的标准问题，答案=没有）。
- `identity_cross_check="missing"`：`m4c_harness.py:124-125` 显式设计（"注入产物：版本读不出来，形态 (T,F,T)，不算矛盾"）。
- 进程码 5 有两条独立证据：`tmp/fourarms-b09.log` 记 `exit=5`；我从产物重算 `V.verdict(rec)=5`。
⇒ 不判未接上、不记未做。但要记一条**口径缺口**：产物的 `exit` 字段与进程退出码是两种东西（见 2.5-①）。

**5) DELETE 两臂：同意"未观察到破坏"，不同意说成"site1 不承重/冗余"。** 我给的替代解释（不是"夹具没走到"，而是**结构性遮蔽**）：
- `chat.py:270` 的 `leases.reset(i, site="chat.place.fresh")` 位于 `:268 register_block` 之后、`:271 ms.load_into` 之前；`load_into` 从 0 重写 n 个 token，且进程启动时 seq 为空 ⇒ 在本夹具里 `reset` 与 `pass` 的差别**在观测面上不可区分**（差别只在 guard 断言是否执行，而空 seq 的断言恒真）。
- 更关键：`site1.place` 判据自己写着"站点 1 的判据是 pre-existing 的 n_tokens == index n；**删掉该站点的 reset 不会红（load 自清），本条记覆盖不记冗余**" ⇒ 按 §6.1，**该判据对 M4-C 问题判别力为空**，它不是能证伪"删除 site1 reset"的判据。
- 所以 DELETE 臂唯一有效读数只有 `loads` 相等 + `attach_events_ok`，这两项对"承重性"的判别力也弱。
⇒ **可签**：「在 b09/14B/本夹具、`QUESTIONS=[]` 的 place 路径上，删掉 site1 的 reset，未观察到任何读数变化」；**不可签**：「site1 的 reset 是冗余的」。

### 2.5 缺口与不可签项（都不阻塞六臂结论，但签字文本必须限定）

① **`exit` 一词两义（§6.3）**：产物 `exit` = 被驱动代码的退出观测（0 / 1 / -1）；进程码 = 0（符合期望，**含 red**）/ 5（仪器）/ 3（台账）/ 4（几何）。§4.5 与你的六行表在 green/red 行用的是产物字段，inject 行用的是进程码——**同一列混了两种东西**。这还造成一次真实代价：`run-six-b09.sh` 的 `want` 列把 red 期望写成进程码 1，于是脚本在 red 处 STOP（`tmp/sixarms-b09.log` 只有 24 B，只有 STOP 行、缺 tee 行，**不能当"六臂一次跑齐"的证据**），后四臂另跑；好在每臂恰好一份产物、时间戳唯一，**读数唯一性未被破坏**。
② `why_empty` 写死（`run_site3.py:108`）——见 2.4-3。
③ `site1.place` 自述"不会红"⇒ DELETE 臂结论只能到"未观察到破坏"——见 2.4-5。
④ inject 进程码不在产物里，只能靠外部日志或重算；`tag` 不是字段、只在文件名里。

### 2.6 独立结论（一句话给 lead）

**六臂六通过（14B/b09），可签的 M4-C 判决 = 「在 14B 装置 + b09 批次 + 本夹具观测面上：删 site1 的 reset 未观察到破坏；删 m1.unmount 的 reset 被 A 判据抓住（red 臂）；仪器错路径按设计给出 exit 5 且自证 (T,F,T)」；不可签「site1 reset 冗余」与「cells 见证者本批可红」两条。** 唯一会改判的是：若 v2①-a 的原文要求见证者在本批红一次，则 red 臂只满足一半。

## 3. 对 lead 判词初稿的复核（16:40–16:45；`docs/_work/M4C-VERDICT-lead.md`）

### 3.0 先核数字

- 判词文件：**sha16 `c7ecd5ebb2d8ecf2` / 14,004 B / 135 行**（我逐字节算，与 lead 一致）。
- §2.2 die 文本与 b09 red 产物**逐字相同**：`error: M4-C 范围断言红 @m1.unmount: 调用流 hits=[]（0 条） != dropped=[2]（1 条）` ✓。
- "红先被范围断言抓住、orphan 未证"**准确**：red 产物里 `site3.turn_orphan` 只在 turn1 `checked`（orphan=0 / chat_n=0），随后 die 事件（kind=assertion），orphan 判据没有在 drop 后再读的机会。
- 其它抽查全对：green 三组流判据 `[]/[]、[2]/[2]、[1]/[1]`、orphan 三次 0、chat_n 0→63→108 ✓；drop 与 green **逐键相同**（值差异仅 `mode/run_id/sampled_at/assert_log_path` 四个键）⇒ G2 成立 ✓；两个 variant 快照 `1612061e`/`0c149c11`、700 行、L270/L562=`pass  # M4C-DELETED-SITE-N`、`leases.reset(` 5→4（L117 在 docstring 里）✓；`m4c_verdict.py:139 return 0` ✓；`chat.py:102 _event` ✓；`redcheck_delete.py:76 attaches_expected_min:1` ✓；`verify_landed("b09")==0` ✓；`SELFCHECK-0f699908` = `5fc96db90cce689f`/2041 ✓；DB 10 源 / 2 建块 ✓（`memory_source` 10、`memory_block` 2）。

### 3.1 五条必须改的（按"会不会让人签错"排）

**① 行②（L91）签错对象：把已作废的 v1 当成"未通过（1/4）"。**
"四条承重断言全红可复现" = **v1**；`CONSOLIDATION-LEDGER.md:3771` 已裁 **v1 作废**（前提被 `kvshim_load` L573 自清证伪，`:3762`）。按本会话自己的规矩"**判据作废 ≠ 未通过**"，不能记未通过。现行 v2② = "三处冗余有实测对照"（`:3772`），且 `:3775` 明写"**冗余证明不是判据，不许拿它凑数**"、不计入验收 ⇒ 它**不该占四态格**。改法：
- `v1①（四条全红）` = **作废**（附记录：本批 site3 一条红可复现）；
- `v2②（三处冗余对照）` = **记录 1/3**（site1 已给：loads 逐字段相同；site2/site4 无读数），不进四态。

**② 行③（L92）事实前提错 + 状态错。**
"磁盘只有 1 份（live.json）"**不成立**：盘上有 4 份 session JSON（`live/s/s_2/bridge`，锚分别 `fa94b1bc58c0e421`/`5ee2102ee068386a`/`f4264c9f2ea9393e`/`e438967a31f25466`），**全部是 7B 时代**（`model.model_path` = 7B）。真实状态：**同一状态的存盘只有 1 份**（live.json，03:33，7B）。而"三份 session 剔除 saved_at 后仍 = fa94"这条字面判据在 14B 切换后**恒不成立**（新存盘必带 14B `model` + 新 `placement.block_sha2`）⇒ 应记 **判据作废（原字面）** 或 **未做（按 14B 重设基线）**，不是"未接上"。
连带：**§1 装置表（L25）不该把锚列在"先签装置"**——它是 7B 时代产物、mtime 03:33 未被六臂改写，只能签"回归读数未变"，不能当 14B 装置证据。

**③ v2①-a（L89）不能签无条件"通过"。**
DESIGN §1 站点 3 行把红读数定在 `cells_of`（红时 = n）；本批唯一红是 A 判据（`chat.py:509-520`，读 `leases.sites` vs `dropped`）；G5 自认 `cells_of` 见证者被抢死 ⇒ **cells_of 层本批 = 未做**。A 的红使"可红可绿"在**调用流层**成立（ledger `:3905` 允许"字面成立 + 标注层级"）⇒ 正确记法 = **分层两格**：`v2①-a(调用流)` 通过 / `v2①-a(cells_of)` 未做。§0（L10）"可红可绿成立"也必须带层级。
另：A 判据 = `leases.sites`（桩记录）vs `dropped`（调用方名单）——**两边都不是引擎读数**，按 ledger `:3757`「不能用表读表（纪律 40）」它属表读表 ⇒ 无条件"通过"站不住。

**④ G1（L104）要补反向。**
"不支持冗余"会被读成"所以承重"。补："**也不证明承重——该臂对'承重/不承重'判别力 = 0**"。
另：引"源码 L278 自述"不准，note 字符串在 **L281**（`_crit` 调用起于 L278）。

**⑤ G8（L111）定性要改准，且判决必须与它自洽。**
不替用户裁 DESIGN §5 措辞**对**；但不是"两说待裁"：DESIGN §5 的文字已被后续裁定取代——`HANDOFF §5.3`（cells 见证者判空集、覆盖改由 L562–565 调用流判据承担）、ledger `:4165`（端点比对在范围问题上不成立 ⇒ 换调用流）、`:4174`（调用流断言 = 唯一签名依据）。建议改 G8 为"**请用户确认把 DESIGN §5 的 ❌ 改成'范围类判据必须观测调用流，且必须声明它不判后果'**"。若用户不认 ⇒ A 判据非法 ⇒ v2①-a 只能记"未接上（判据合法性未定）"，不能签通过。现在的写法（签通过 + 待改措辞）自相矛盾。

### 3.2 三条小错（不签字，但该修）

- L50 说"除 `mode/run_id/sampled_at/路径/tag`"——产物**没有 `tag` 字段**（G3 自己也这么说）；实际差异键只有 4 个：`mode/run_id/sampled_at/assert_log_path`。
- 表头 L4 说"判据作废进第 5 节决策记录"，但 §5 没有"决策记录"节（v2①-b/⑤ 的废因只在 §4 行内）⇒ 补 §5.0 或改表头。
- G11 `__pycache__` 我数 **14** 个（不是 13）；`.tmp` 4 个 ✓。

### 3.3 我同意的（逐条）

- 六份 sha16/bytes、batch/sampled/chat_py/harness 三段、selfevidence/identity 的逐份读数与我 §2.1 全一致；
- 行 green/red/inject/drop/base/deleted 六臂判"通过"（base/deleted 限"本夹具观测面"）——同意；
- inject 用"产物重算 `V.verdict`=5"替代产物自带 exit ——**同意，这是可复算不是补写**（纯函数 + 我独立复算同值 + `tmp/fourarms-b09.log` 实测 5）；
- §4 行 ③ 之外的 ⑤=作废、v2①-b=作废 ✓；M4-C-3/4 = 未做 ✓；site1 红场景"可达 ⇒ 未做" ✓（DESIGN §1 构造法存在）；
- G2/G3/G4/G5/G7/G9/G10/G12 与我 §2.5 判断一致（G5 请按 3.1-③ 升级为"cells_of 层未做"的一格）。

### 3.4 我的签字建议（改完可签）

六臂可签（14B/b09/本夹具）；**v2①-a 分层签：调用流层通过 / cells_of 层未做**；**v1① 作废**（不在四态，附"site3 一条红可复现"记录）；**v2② 记录 1/3**（不在四态）；**v2③ 作废（原字面）/ 未做（14B 重设基线）**；§1 锚行加"7B 时代、仅回归读数"限定；G8 改定性后与签名自洽。**在这些改动完成前，判词 L10 的"六份产物全部可签 + 可红可绿成立"会让人签错两处：把 cells_of 层当已复现、把 v1 当作"未通过"。**

## 4. 终稿复核（按字节核；sha16 `6a7ce54854e88137` / 17,699 B / 146 个换行、末行无换行 = 147 行）

**结论：方向全对，五条反驳已落；剩三处引证/措辞会让人签错（不改判），加一处小错。改完可定稿。**

### 4.1 三处必改

1. **L71（§4 #3）把 attempt 时代写成 b06**：写"b06 旧字节有过一次（`cells_of(seq2)=36`）"。实测：`M4C-SITE3-red-b06-red-d770742f.json` 的 die 是 **A 判据**（`范围断言红 … hits=[] != dropped=[2]`），与 b09 同型；`cells_of(seq2)=36` 来自 **`M4C-SITE3-red-attempt7.json`**（die=`承重断言红 @m1.unmount.after_detach (循环之后 / 挂载之前): cells_of(seq 2) = 36, expected 0`，attempt1–6 是 `cells_of(seq 1) = 50`）。改：**"臂级：attempt 时代旧字节（`M4C-SITE3-red-attempt7.json`，seq2=36；attempt1–6，seq1=50）；b06 red 的 die 是 A 判据，不是见证者；均非当前身份"** —— 否则读者会以为六臂批出过 cells_of 红（没有）。
2. **L85（§5）+ L91（§6-①）"对引擎状态都不是承重者 / 删任何一处 reset 引擎状态不变" 过强且自相矛盾**：删 site3 的 reset 后 `cells_of` 仍 = n（#3 自己引的 attempt 旧读数就是 50/36），只是下一次 `load` 把后果抹掉。改 L85：**"对『下游可观测后果』不是承重者（`kvshim_load` 先清 ⇒ 不叠 cell、不产生 2n/越界）；但『detach 之后、下次 load 之前』的瞬时 cell 占用会不同 —— 那正是 M4-C-4 未证的部分"**；L91 改成"删任何一处 reset 都**不会产生预登记的下游红读数**（不叠、不 2n、不越界）"。`L3762` 只支持"叠不上去"，不支持"引擎状态不变"。
3. **L74（§4 #6）"从未在盘上成立" 超出证据**：03:22 那次读数所用文件已被 03:33 的存盘覆盖（`live.json` mtime 03:33），**不可复核** ⇒ 只能断言"当前盘面不成立（4 份分属不同会话、锚互异）"。改："**当前盘面不能复现（4 份、4 锚、全 7B）；03:22 旧读数所用文件已不可考 ⇒ 冲突记 G13-②**"。

### 4.2 一处小错

**L27**：`SELFCHECK-0f699908` 产物**没有 `exit` 字段**（9 键）；"exit 0" 是进程码，出处应是 `tmp/selfcheck-b09.log`（PASS）⇒ 写成"产物实读"会被 `G3` 自己打脸。

### 4.3 两条确认

- **A（§4 #5 §13.2② = 未做）：认。** 若求严可把"site3 green 无 die、site1 base 无 die"括注成"未删状态下为绿、无'删→恢复'循环"，不改判。
- **B（§0 第 3 句）：正好，不用改。** 第 2 句已签"删 site3 会被调用流断言抓住"，第 3 句限的是"机制承重"这个总结论；两句合读无矛盾。
- **C（ledger 引证按内容核）：四行号全对** —— L3771=v1 作废行、L3772=v2 定义行、L3775="两栏分离/冗余证明不是判据"、L3762=`kvshim_load` L573 自清"叠不上去"、L4165=端点比对不成立→调用流、L4174=调用流断言唯一签名依据。
- 另核：sha16/bytes 与你给的一致；**行数 = 146 个换行、末行无换行 ⇒ 147 行内容**（你写的 146 = `wc -l` 口径，不算错）。

### 4.4 终稿复核（三处引证 + 一处小错已改；**可签**）

最终字节 **sha16 `d7eb117d5838fb6a` / 18,625 B / 146 换行（147 行）**，我逐处复读：

| 我指出的 | 位置 | 改后核验 |
|---|---|---|
| attempt 时代被写成 b06 | L71 / G5(L105) | ✓ 引 `M4C-SITE3-red-attempt7`（seq2=36）/ attempt1–6（seq1=50），并写明"b06 red 的 die 是 A 判据，不是见证者" |
| "对引擎状态都不是承重者"过强 | L85 / L91 | ✓ 收窄到"对**下游可观测后果**不是承重者（不叠/不 2n/不越界）"，并显式标注"瞬时 cell 占用确实不同（attempt7 的 36 是证据）⇒ M4-C-4 未证"；`L3762` 改为"只支持这一点" |
| "从未在盘上成立"超出证据 | L74 | ✓ 改为"当前盘面不能复现；03:22 旧读数所用文件已被 03:33 存盘覆盖、不可复核 ⇒ G13-②" |
| SELFCHECK 产物无 `exit` | L27 | ✓ 改为"进程 exit 0（产物无 exit 字段，9 键；PASS 见 `tmp/selfcheck-b09.log`）" |
| G9 写实 | L109 | ✓ 补 `sixarms-b09.log` 单行内容 + `fourarms-b09.log`/`arm-*.log` |

**结论：可签。** 签署范围、未签项、依赖项（仅 #2 依赖 §6-⑤ 裁定）、可复算项四处与 §4 判词一致；六份 sha16、台账 9/9、锚、纯函数 `V.verdict` 均已由我独立复算过。