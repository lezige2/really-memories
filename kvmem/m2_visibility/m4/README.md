# M4 · 写入固化（一次对话 → 自动沉淀 1 块 → 新进程能检索、能作答）

2026-10-25 ｜ 判据：`mine/inspector/M4-CRITERIA.md`（冻结）+ `mine/lead/BRIEF-M4.md`
取舍方向：**宁多记不漏记**（K1/K3/K4/K5 recall 1.0）。这与 M5 的「漏判优先」**故意相反，不许统一**。

## 0 一句话

一次真实对话（9 轮，逐字未改）跑完：**10 句全部有判定**，6 条 keep → **1 个 KV 块**（91 token，独占 position 0）
+ **6 行 memory**（含证据片段与 `2026-10-28` 锚定）+ 7 行 `memory_source`（1 块 + 6 条检索单元）。
**新进程**检索到该块、**另两个新进程**逐字答出住址与车牌。9/9 验收项全过。

## 1 文件

| 文件 | 作用 |
|---|---|
| `m4_extract.py` | K/D/U 判定引擎（封闭词表、相对时间锚定、`§9` 逐字接地） |
| `_test_m4.py` | 冻结样例逐句对照 + 四条边界 + 锚定 + 去重 + 多值（**纯 CPU**） |
| `m4_store.py` | SQLite（`memory_source` / `block` / `memory` / `source_block` / `review`）+ position-0 总线 + 去重/多值 |
| `m4_write.py` | **真实写路径**：判定 → 写 position 0 → save → 入库 → **接入 m3 租约**全链路 |
| `m4_newproc.py` | **新进程**：`--mode search`（检索）/ `--mode answer`（检索→取块→作答） |
| `m4_pos0_refuse.py` | position-0 的**一次通过 + 一次拒绝**（真引擎） |
| `m4_verify.py` | 验收编排：起新进程、跑去重/多值、汇总 `run_m4_verify.json` |
| `_probe_place.py` | 定点实验：块必须紧贴问位（见 §5） |
| `evidence_m4_judge.json` / `run_m4_write.json` / `run_m4_verify.json` | 证据 |
| `m4_memory.db` / `blocks/blk_conv_2026-10-25_01.kvmem` | 落盘产物 |

## 2 判定层：冻结样例逐句（`_test_m4.py`，无 GPU）

| 轮 | 原文 | verdict | codes | 产出 |
|---|---|---|---|---|
| 1 | 你好呀！ | drop | D1 | — |
| 2 | 你好！有什么可以帮你？ | drop | D4 | — |
| 3 | 我住在广陵路 12 号 2 单元 602。 | keep | K1 | 住址=广陵路 12 号 2 单元 602 |
| 4 | 我每天早上七点半出门，别在那个时候给我推消息。 | keep | K1+K5 | 作息=每天早上七点半出门；提醒规则=别在那个时候给我推消息 |
| 5 | 我车牌是浙B-3F19K。 | keep | K1 | 车牌=浙B-3F19K |
| 6 | 记住了。 | drop | D4 | — |
| 7 | 帮我查下明天天气。 | drop | D3+D6 | — |
| 8 | 谢谢，就这样吧。 | drop | D1 | — |
| 9 | 对了，我女儿小名叫豆豆，下周三她生日，提醒我买蛋糕。 | keep | K4+K3 | 家庭成员=女儿小名叫豆豆；计划=提醒我买蛋糕（anchored_time=**2026-10-28**） |

**与冻结预期 9/9 一致**（码集合比较；第 9 轮我出 K3+K4，判据写 K4+K3，集合等价）。
附加边界 5/5：`我不吃辣`→K2 忌口｜`我不喜欢那个`→**U4**｜`我好累`→D7｜
`我长期失眠`→K1 健康｜`如果我搬到杭州，你会记得吗？`→**U2**（条件句优先于 D3）。

**逐句 ≠ 逐轮**：产出单位是**句子**（判据 §1），所以第 2 轮被切成两句（"你好！" / "有什么可以帮你？"），
两个都记 D4；冻结表按**轮**计 9 行。两种口径都在 `evidence_m4_judge.json` 里，不混用。

## 3 时间锚定（判据 §12.3）

`下周三` + `ts=2026-10-25T09:00:00` ⇒ **2026-10-28**。
规则（冻结）：周从周一起算；10-25 是周日 ⇒ 本周一 10-19，下周一 10-26，下周三 10-28。
给出 11-04 或原串 `下周三` 都算错——**实测是 2026-10-28**。
无 `ts` 的相对时间 ⇒ 记 **undecidable**、**不落盘**（词表里没有「有 ts 才写」的旁路）。

## 4 落盘与 position 0（判据 §12.6）

| 项 | 实测 |
|---|---|
| 写入前 | `cells_in_target=0`、DB 无 position-0 占用 ⇒ 允许（`check_before ok`） |
| `write_at(seq, text, 0)` | **91 token，位置 [0, 91)**，`pos_max_raw=90` |
| 写入后 | 扫描**恰好覆盖 [0, 91)**（`check_after ok`） |
| 块文件 | 9,507,412 字节，sha256 `81127d24fd64b96b…` |
| SQLite | `memory` **6 行 = keeps 6**；`memory_source` 7 行；`block` 1 行 |
| **拒绝一次** | 同一 seq 再要 position 0 ⇒ **两道守卫都拒**：`engine_cells`（已占 21 格）与 `db_claim`（已被 pos0_A 占用）；拒绝后引擎格数不变（21→21） |

## 5 一条新测出来的硬规则：**块必须紧贴问位**

`kvshim_ask_at` 只在 `pos == raw_pos_max + 1` 时工作。块编码在 position 0（L6 要求独占），
所以**用前必须先把它移到「结束于锚点」的位置**，否则：

| 情形 | 位置 | 问位 | rc | 答案 |
|---|---|---|---|---|
| 按原样挂 | [0, 91) | 4096 | **-1** | **空串** |
| 移到末尾对齐 | [4005, 4096) | 4096 | 93 | 「我住在广陵路 12 号 2 单元 602。…」**命中** |

（`_probe_place.py` 一次加载内对照两次，块文件 sha 不变。）
这条同时也解释了 M3 §7 的账本缺口：**按 `n_tokens` 推位置必然算错**（共享格不计入），
必须用 `raw_pos_max`。**凡是拿 shim 的 `pos_max` 做判断的上层都是错的**（M3 §0.5）。

## 6 检索：一个块检索不到，一条事实检索得到（这是设计决定，不是巧合）

验收 4 要「新进程跑 `retrieval.search` 能检索到该块」。实测**把整段对话当一个检索单元会失败**：

| 检索单元 | 查询 | score | coverage | 门限（`GATE 1.30 / COV_MIN 0.35`） |
|---|---|---|---|---|
| 整段对话（91 token） | 我住在哪？ | 0.575 | 0.12 | **拒绝** |
| 整段对话 | 广陵路 | 0.575 | 0.12 | **拒绝** |
| 整段对话 | 浙B-3F19K | 6.11 | — | 通过 |
| 单条事实「我住在广陵路 12 号 2 单元 602。」 | 我住在哪？ | **3.203** | — | 通过 |
| 单条事实「我车牌是浙B-3F19K。」 | 我车牌号是多少？ | **6.383** | — | 通过 |

**判据空白，实现自定（已报队长）**：一个 **KV 块**仍是"上下文单位"（1 块、position 0、正文逐字），
但 `memory_source` 里放 **6 条检索单元**，每条正文是块正文的**逐字子串**（不是改写），
用 `source_block` 映射回块。检索命中 → 知道是哪一块 → 载入该块作答。
这样「沉淀 1 块」（验收 1）与「新进程能检索」（验收 4）同时成立，且没有改 `tools/retrieval.py`。

**未做**：没有为长对话做「500–1000 token 分段」的实测（本样例 91 token，属**未检验**）；
没有调 `GATE` / `COV_MIN`（那是 `tools/`，且判据冻结）。

## 7 真实接入 m3 租约（验收要的全链路）

`m4_write.py` 的第五段是**真路径**，不是单测：`attach → reset(拒) → detach → reset → 重载 → 重定位 → attach → 再 reset(拒) → 复原`。

| 步骤 | 实测 |
|---|---|
| attach（原样 [0,91)） | live cells 91，`referrers(块seq)=[0]` |
| **reset(块seq)** | **LeaseError 拒绝**："still referenced by dialogue seq(s) [0]. Detach first…" |
| 拒绝后引擎 | 块格数 **91 = 91**（`engine_untouched: true`）——守卫拦在**下传之前** |
| detach → reset | live 0，块 0（合法顺序才放行） |
| 从文件重载 + 重定位 | 91 格回到 [4005,4096)，块文件 sha **不变** |
| 再 attach 后**再 reset** | **第二次也拒绝**（`guard_refused_second_time: true`） |
| 复原 | 移回 position 0，块 91 格，无残留引用 |

这两条拒绝记录都在 `run_m4_write.json → lease_chain.steps[]` 里（含完整错误文本）。
**M4 是 `m3_lease.py` 的第一个真实消费者**，M3 里「护栏就绪、未接入」的状态到这里才算有调用方——
但 **`tools/chat.py` 的四处裸 reset（:176/:284/:444/:449）仍未接入**，产品路径防护覆盖率还是 **0**。

## 8 验收（判据 §12 的 8 项 + position 0）

| # | 判据 | 实测 | 判 |
|---|---|---|---|
| 1 | 一次对话 → 1 块 | `block` 1 行，91 token，逐字未改 | **达成** |
| 2 | 三元组 + 证据片段，属性封闭 | 6 条，属性全在 31 词表内，`evidence_span` 均逐字 | **达成** |
| 3 | `write_at(seq,text,0)`→`save`→入库，position 0 独占断言 | 通过 1 次 / 拒绝 1 次（两道守卫），见 §4 | **达成** |
| 4 | **新进程**检索到该块 | pid 2880 / 15332，命中 fact_住址_2（3.203）、fact_车牌_5（6.383）→ 同一块 | **达成** |
| 5 | **新进程**加载该块后正确回答 | pid 11460 / 9008，答案逐字含「广陵路 12 号 2 单元 602」「浙B-3F19K」 | **达成** |
| 6 | 多值不覆盖 | 广陵路→文昌路：**2 行都在**，旧值 `superseded` 且 `superseded_by` 指向新行 | **达成** |
| 7 | 相对时间 | 有 ts → **2026-10-28**；无 ts → undecidable 不落盘 | **达成** |
| 8 | 去重 | 同句重复一遍：keeps 7、行数 **6**、动作 `deduped` | **达成** |
| + | position 0 | 通过 + 拒绝各一次（真引擎） | **达成** |

机器判读：`run_m4_verify.json → acceptance.all_pass = true`。
**新进程是真的新进程**：每个子进程自己打印 `os.getpid()`，与父进程不同（`new_process: true`）。

## 9 判据空白处我的决定（4 条，供检测员核）

1. **value 用逐字切片，不按 §11 的展示写法存。** 判据 §11 第 9 句写「(用户, 计划, 2026-10-28 女儿生日买蛋糕)」，
   但 §9 要求 value 必须在 `evidence_span` 里**逐字出现**，而「2026-10-28 女儿生日买蛋糕」在原文里不存在。
   ⇒ 我存 `value=提醒我买蛋糕` + `anchored_time=2026-10-28`。同理家庭成员的 value 是
   `女儿小名叫豆豆`（判据示例写 `女儿小名豆豆`），差一个「叫」字，因为原文如此。
2. **检索单元与块分离**（§6）：1 块 + 6 条逐字子串单元 + 映射表。
3. **问位必须等于 `raw_pos_max+1`**（§5），块用前重定位到「结束于 4096」。
4. **assistant 发言一律 D4**，只保留一种例外：用户**明确确认** assistant 上一句里的封闭词表事实
   （判据 §13 允许），且置信度降到 0.6、标 `derived_from=assistant`。本样例未触发。

## 10 未检验 / 不做（防过度宣称）

- **未检验**：500–1000 token 的**长对话分段**（本样例 91 token，一个段）、多段并存、段间去重、
  长会话里的 supersede 链（当前只测一跳）。
- **未检验**：属性词表外的新属性只走到 `U-attr`（进 `review` 表待审），没有真实撞到一例。
- **不做**：不改 `tools/` 下任何文件（含 `chat.py` / ~~kvslots.py~~ / ~~retrieval.py~~）、DLL（`9edbafa1…`）、
  `kvmem/m2_v1_14b/`、`m2/`、`m3/`、`m5/`。
- **不做**：不把 M4 与 M5 的取舍方向统一；M4 多记，M5 只判「有没有超出块正文」。

## 11 字段说明（`run_m4_write.json` / `run_m4_verify.json`，别猜字段名）

| 字段 | 含义 |
|---|---|
| `judge.sentences / .keeps` | 句子数（10）/ keep 条数（6）——**句子数 ≠ 轮数** |
| `judge.per_sentence[]` | 每句 verdict/code/reason（含 drop，绝不静默跳过） |
| `encode.tokens_written` | `write_at` 写入的 token 数（91） |
| `encode.pos_max_raw / pos_max_shim` | 同一 seq 的 raw 口径（90）与 shim 口径；**判断只用 raw** |
| `encode.position0_after` | 写入后扫描是否**恰好**覆盖 [0, n) |
| `position0_before` | 写前：目标区间空 + DB 无占用，两者都过才允许写 |
| `save.bytes / sha256` | 块文件字节数与哈希（9,507,412 / `81127d24…`） |
| `retrieval_units.units[]` | 每条检索单元（source_id / attr / 逐字 text / 所属 block_id） |
| `lease_chain.guard_refused_live_reset` | 真路径上租约表是否拒绝了下传的 reset |
| `lease_chain.engine_block_cells_after_refusal` | 拒绝后块 seq 的格数（应与拒绝前相同） |
| `lease_chain.steps[].rc / .hit` | 挂载后作答的返回码与是否命中（**rc=-1 就是位置不对**） |
| `acceptance.*`（verify） | 8 项 + position 0 的机器判读，逐条对应 §8 表 |
| `answer_checks[].new_process` | 子进程 pid ≠ 父进程 pid，即「真的是新进程」 |
| `answer_checks[].answer` | **证据原文**，逐字节；所有 hit 判定只用它 |
| `answer_checks[].answer_exact` | 模型原始输出（未做任何裁剪） |
| `answer_checks[].answer_display` | 派生展示文本（已剥离 think 段），**不参与任何 pass/fail** |
| `acceptance.display_never_decides` | 自检：hit 只由 `answer` 决定，且 display 里无标签 |
| `acceptance.raw_answer_preserved` | 自检：`answer_exact.strip() == answer` |

## 12 复现

```bash
cd D:/llama-mem/kvmem/m2_visibility/m4
python -X utf8 _test_m4.py                       # 判定层，纯 CPU
python -X utf8 _test_display.py                  # 展示层剔除规则，纯 CPU（8/8）
rm -f m4_memory.db blocks/*.kvmem
python -u -X utf8 m4_write.py --out run_m4_write.json   # 真引擎：写块 + 入库 + 租约全链路
python -u -X utf8 m4_verify.py                   # 新进程检索/作答 + 去重/多值 + position 0
```

## 13 已知产物缺陷：作答里混进 `</think>`（用户可见污染）

**现象**（两条作答原文，码点已核：U+003C U+002F think U+003E）：

```text
住址：我住在广陵路 12 号 2 单元 602。\n</think>\n\n我住在广陵路 12 号 2 单元 602。
车牌：浙B-3F19K\n</think>\n\n车牌号是浙B-3F19K。
```

**不影响事实命中**（值逐字都在），但这是**用户能看到的脏输出**，不能只写「命中」就放过。

**定位（三组对照，`_probe_think.py` → `evidence_think_tag.json`，一次引擎加载）**：

| 块正文 | token | rc | 出现 `</think>` |
|---|---|---|---|
| A 完整对话（含 assistant 轮） | 91 | 93 | **是** |
| B 无对话结构的散文（M2 风格） | 55 | 230 | **否** |
| C 同一对话，**去掉全部 assistant 轮** | 82 | 93 | **是** |

**结论**：触发条件是**块正文是「对话记录」形态**，**不是** assistant 轮、也不是问句模板——
模板是 `"\n问：" + q + "\n答："`（`kvslots.py:53-58`），本身不含 think 标签；
M2/M3 的 run json 里也**没有**这个标签（grep 过），所以这是**对话型块正文 + 蒸馏模型**才出现的。
最可能的机制：R1 蒸馏模型看到对话记录后被拉进「思考模式」，于是先吐一个闭合标签再作答。

**处置（队长 2026-10-25 定）：展示层清洗 + 原文强制留档；块正文一律不动。**

- **候选 1（采纳）**：只对「发给用户的那一份」剥掉标签段；KV、块文件、存库正文、run json 原文全不动。
- **候选 2（否决）**：给块正文加引导头 —— ① 违反已冻结的 `block_text_policy`「段内原话逐字，不重写不摘要」（判据 §8）；
  ② 会切断 M2/M3/M4 之间块正文的可比性。**块正文模板不属于本轮可改范围。**
- **候选 3（不采用）**：接受脏输出 —— 用户可见污染没解决。

**落地规格（已实现）**：

| 要求 | 实现 |
|---|---|
| run json 的 `answer` 保持原样逐字节 | `answer` 语义未变（仍只裁首尾空白，与前几轮一致）；另存 `answer_exact` = 模型原始输出，一字不剪 |
| 新增 `answer_display` 派生字段 | `m4_display.strip_think()` 产出，附 `answer_display_changed` |
| 所有验收判据只用 `answer` | `m4_verify.py` 的 `hit` 只读 `answer`；自检 `display_never_decides` / `raw_answer_preserved` 均 true |
| 「答案原文照抄」口径不变 | 原文在 `answer` 里，照抄照旧 |
| 剔除规则可复验 | 规则是 `m4_display.py` 的常量正则；`_test_display.py` **8/8 通过**：句首 / 句中 / 多处 / 闭合对 / 未闭合到结尾 / **无标签时逐字节不变** / 空串 / 派生对 |

实测对照（`run_m4_verify.json → answer_checks[]`；TAG 处即 think 标签，NL 处即换行）：

```text
住址  answer        : 我住在广陵路 12 号 2 单元 602。<TAG><NL><NL>我住在广陵路 12 号 2 单元 602。
      answer_display: 我住在广陵路 12 号 2 单元 602。<NL><NL>我住在广陵路 12 号 2 单元 602。
车牌  answer        : 浙B-3F19K<TAG><NL><NL>车牌号是浙B-3F19K。
      answer_display: 浙B-3F19K<NL><NL>车牌号是浙B-3F19K。
```

复验：`python -X utf8 _test_display.py`（8/8）→ `python -u -X utf8 m4_verify.py`（**11/11**，含两条展示层自检）。

## 14 消费方提醒

- 块文件里的位置是 **0 起**；载入后**必须重定位到「结束于问位锚点」**（§5），否则 rc=-1。
- `memory_source.text` 是**逐字子串**，不要当完整块正文用；块正文在 `block` 表 + `.kvmem` 文件里。
- 想接产品路径：`tools/chat.py` 的四处裸 reset 需要改成走 `m3_lease.BlockLeases`（本轮不许改）。
