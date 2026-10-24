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

**结论（第二版，已按检测员的单例改口）：未查明。**
原先我写「块正文是对话记录形态即触发」，但那是**两个变量未分离**：A（含 assistant 轮，91 token，多行）与
B（散文，55 token，单行）长度、行结构、续写模式（rc 93 vs 230）同时不同，不能说成「对话形态」。
按检测员给的单例做了唯一变量对照（`_probe_think2.py` → `evidence_think_newline.json`）：**同一段文字、只删换行**
（127 → 119 字符，内容一字不改）→ **标签仍然出现**（91 → 90 token，rc 93）。
所以「换行/多行」也不是必要条件，归因降为**未查明**。

已知的只是触发面：本样例下**会**出现；M2/M3 的 run json 里**没有**（grep 过）；问句模板本身不含该标签
（`kvslots.py:53-58` 的 `"\n问：" + q + "\n答："`）。
**归因不影响处置**：M4 的产品形态就是对话段落落块，这条路径上标签必现，清洗是必需品。

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

## 15 第二轮改动（检测员 R7 / R9 / R10 与队长三条放行条件）

### 15.1 展示层三条硬条件（都进了代码与单测）
| 条件 | 实现 | 证据 |
|---|---|---|
| ① 差异可解释断言 | `assert_diff_explained()`：把删掉的字符收集成区间，逐段校验「∈ 标签」或「连续空行合并（该处 ≥3 个换行）」，再用**子序列对齐**确认 display 是 answer 删标签后的子序列；任何标点/空格/多删一字/少删一个标签 → 抛 `DiffNotExplained`，不静默 | `_test_display.py` 的 4 条反例（标点被改 / 一个字被删 / 标签残留 / 凭空多字）全部被拒 |
| ② 幂等 + 无标签逐字节相等 | `audit()` 内断言 `strip(strip(x)) == strip(x)`；无标签时直接原样返回并断言 `removed_chars == 0`；补「相邻连写」``` 与 `T*120` 两个极端 | 11 例 0 failed |
| ③ 留痕四项 | `per_tag_count / removed_chars / display_len / display_empty` 进 `derive()` → 子进程 json → 验收 `display_trace_fields`；清洗后为空置 `display_empty: true` 并保留空串，**不用原文顶替** | `only_tag` / 未闭合到结尾两例 display 为空且标记为 true |

**结构层 / 内容层分离**（不许一锅端）：控制标签属结构层，必须剔净；「问/答」自问自答与同句重复 `X\n\nX` 属内容层，
**默认不清洗**，只报 `content_warnings`；需要处理时用独立开关 `first_sentence_only`（只作用于 display、同样计数、
**只记告警不参与 pass/fail**）。

### 15.2 R9 检索单元去重
6 条记忆按**句子文本**去重成 **4 个检索单元**，`fanout = [1, 2, 1, 2]`（合计 6），不再把同一句索引两次。
`memory_source` 新增 `fanout` 列与 `UNIQUE(text)`；`memory.unit_id` 记录该记忆由哪个单元承载。
约束逐条守住：单元文本是块正文**逐字子串**（写路径里 `assert span in block_text`）、每个单元**至少 1 条记忆**、
映射到**实际挂载**的块（`source_block`）、**门限未调**——`gates` 是运行时从 `tools/retrieval.py` 读出来的
（`GATE 1.30 / COV_MIN 0.35 / INDEX_VERSION 5`，`unchanged: true`）。

### 15.3 R7 指代裁决：「别在那个时候给我推消息」
判据 §7（要锚定）与 §9（要逐字）冲突，按裁决：**value 逐字保留**，新增 `resolved / resolved_to` 两列。
本句的指代在同一句里能落地 ⇒ `resolved: "in_sentence"`，`resolved_to: "每天早上七点半出门"`。
无指代时记 `no_reference`；有指代但句内找不到先行词时记 `unresolved`——**绝不改写 value**。

### 15.4 `memory.type` 空列处理
原来该列永远是 NULL。恒空的列会让人以为有字段，所以按判定码填：`K1→fact / K2→preference / K3→plan /
K4→identity / K5→constraint / K6→meta`（映射冻结在 `m4_extract.TYPE_OF`）。实测 6 条全非空。

### 15.5 跨实验：同一布局删掉车牌句再问车牌
`m4_crosscheck.py` → `run_m4_crosscheck.json`（另存 `blocks/blk_conv_noplate.kvmem`，不覆盖主块）。
删掉「我车牌是浙B-3F19K。」后：块正文不含车牌（`block_contains_plate: false`）、判定层不再产出车牌记忆
（`has_plate_memory: false`），同一问题：

| 问题 | rc | 是否吐出 浙B-3F19K | 答 |
|---|---|---|---|
| 我车牌号是多少？ | 245 | **否** | 「我需要先确认您的身份…」（要求身份验证） |
| 我住在哪？（对照，同块） | 93 | — | 「我住在广陵路 12 号 2 单元 602。」**正确** |

对照正常 ⇒ 块本身可用，车牌问题的变化来自被删掉的那一句。**措辞**：由「支持性观察」升级为
**一例同布局消融对照（单例，非统计）**；不写成「已证明答案来自块」——单例、单模型、单问句，且模型是**回避**而非明说「不知道」。

## 16 验收键（第二轮，16 项；§8 的 11 项表为准的旧版）
`1_one_block / 2_memories_with_spans / 3_saved_and_inserted / 4_new_process_retrieval / 5_new_process_answer /
6_multi_value_keeps_old / 7_relative_time_anchored / 8_dedupe_no_new_row / 9_units_deduped_by_text /
10_type_and_resolved / position0_pass_and_refuse / display_never_decides / raw_answer_preserved /
display_trace_fields / gates_untouched / all_pass`

实测：**16 键全 true**（`run_m4_verify.json`）。

## 17 交接：`tools/chat.py` 接租约（下一轮，本轮不动）
我上一轮预判的 `:176/:284 走 safe_reset_all` **是错的**，检测员否掉了，理由我复核过
（`m3_lease.py:107-119`：`skip = set(skip) | set(self.blocks)` 会无条件跳过全部已注册块 seq，
块根本没被清，紧随的 `load_into` 会**叠在旧 cell 上**——静默走位，比报错糟）。正确方向：

| 位置 | 语义 | 用哪个 | 断言 |
|---|---|---|---|
| `:176` / `:284` | 放置路径（无引用） | **`leases.reset(seq)`**（无引用放行、有引用拒绝） | reset 后 `cells_of(seq) == 0` |
| `:444` | 卸旧（前面已有 drop，等价 detach） | `leases.reset` | 同上 |
| `:449` | 装新前清位（无引用） | `leases.reset` | 清完 `cells == 0` 再 `load_into` |

三条硬条件（队长）：默认路径答案逐字节一致；**M2 51 格布局改前改后各跑一次，三问答案 sha 必须相同**（唯一真回归，不用单测代替）；
单独一次提交，提交信息写明「未改变 reset-then-reload 语义，只加租约检查」。**`safe_reset_all` 不得出现在这几处。**

## 18 仍未检验（第二轮更新）
500–1000 token 长对话分段、多段并存、段间去重、supersede 多跳、词表外新属性的真实样例 —— **未检验**；
free VRAM —— **未测出**；think 标签的**归因** —— **未查明**（只测出会/不会出现的样例边界）；
跨实验 —— **单例**，非统计。

## 19 M5 接进作答路径（MD §4.5「接地与弃答（产品级）」）

### 19.1 接线：生成之后过一遍校验，判据文件一行未动
```
route（retrieval） → mount（真块进 seq1） → generate（真引擎） → display 层（think 清洗）
                                                        ↓
                                    m5_ground.ground(display, mounted=[真实挂载块 id], question)
                                                        ↓
                       supported → 原样显示   unsupported → 只显示「记忆里没有记录{主题词}。」
                       undecidable → 原样显示 + 标黄（记录，不静默）
```
新增文件（全在 `m4/`，没有改动任何既有脚本/块）：
| 文件 | 作用 |
|---|---|
| `m5_bridge.py` | 只**调用** `m5_ground`：建 M5 侧文本副本（`blocks` 表：source_text / sha256 / sha_match / source_path）、把校验报告翻成产品记录、决定显示文本 |
| `m4_answer_grounded.py` | 产品作答路径：route → mount → 生成 → display → M5 → 最终 `answer_display`（每次都新进程） |
| `m4_ablate.py` | 建消融块（同一段对话**只删车牌句**），真 14B 写入 → 79 cells → `_ablate/blocks/` |
| `m4_verify_grounded.py` | 四例验收编排 + 三值留痕 + 未改动断言 → `run_m5_grounded.json` |

### 19.2 字段契约（原文一律保留）
| 字段 | 含义 |
|---|---|
| `answer_exact` | 模型原文，**永不改写**（判据与 M4 验收一直靠它） |
| `answer` | display 层的 strip 副本，**保留** |
| `display_pre_grounding` | display 层输出（含四项留痕：`answer_display_changed / per_tag_count / removed_chars / display_len / display_empty / diff_explained / idempotent / content_warnings`） |
| `answer_display` | **最终显示**：只有 `unsupported` 时被替换 |
| `grounding` | `verdict`、`hard_facts`（family/raw/key/sentence/hit）、`hits/unhit/exempt/undecidable_items`、`mounted`、`mount_evidence`（cells、range、block path、block sha256）、`topic_word`、`m5_rewritten`、`recheck` |

**挂载块 id 不是手填的**：`m4_answer_grounded` 自己 route/mount，把**实际挂到 seq1 的那块**交给 M5，并同时记录引擎侧
`engine_cells_on_seq1` 与块行 `cells` 的相等断言（四例全 True）。

### 19.3 显示策略（产品决定，不是改判据）
`unsupported` ⇒ 只显示 `"记忆里没有记录{topic_word}。"` 一行；冻结校验器自己的句级改写留在 `m5_rewritten` 里原样可查
（它只替换涉及的句子、其余保留，所以模型那串「好的，好的…」会跟着留下——产品不把这类填充语和弃答行一起显示）。
`supported` / `undecidable` ⇒ display 与 `display_pre_grounding` 逐字节相同。

### 19.4 四例对照（真引擎、四例四进程，pid 各不相同）
| 例 | 问句 | 挂载块 | M5 三值 | 原始 hard facts | 原答案前 40 字 | 最终 display 前 40 字 |
|---|---|---|---|---|---|---|
| plate_main | 我车牌号是多少？ | `blk_conv_2026-10-25_01` | **supported**（R12 修复后，见 §19.9） | `A:浙B-3F19K hit=True` ×2 | `浙B-3F19K\nresponse\n\n车牌号是浙B-3F19K。` | `记忆里没有记录车牌号。` |
| plate_ablated | 我车牌号是多少？ | `blk_conv_noplate_2026-10-25_01` | **unsupported（正确）** | `A:苏K12345 hit=False` | `我车牌号是苏K12345。\n好的，我记下来了。…` | `记忆里没有记录车牌号。` |
| home_main | 我住在哪？ | `blk_conv_2026-10-25_01` | **supported** | `P:广陵路 T；N:12 T；N:2 T；N:602 T（共 8 条，全命中）` | `我住在广陵路 12 号 2 单元 602。\nresponse…` | 同左（仅 think 清洗） |
| home_ablated | 我住在哪？ | `blk_conv_noplate_2026-10-25_01` | **supported** | 同上（8 条全命中） | 同上 | 同上 |
| undecidable（桥级，无生成） | 我住在哪？ | 复用 home_main 的块 | **undecidable** | `P:廣陵路 hit=True`，`why=含繁体字，不做繁简转换（§2.1.6）` | `我住在廣陵路 12 号 2 单元 602。` | **不变**（逐字节相同），`flagged=true` |

三值都留痕（`supported / unsupported / undecidable`），每条都带 `mounted` + 块 sha256 + hard facts + 命中与否 + 最终显示文本。

### 19.5 A 族不对称缺陷的记录（**已按 R12 修复**，历史留档）

> 状态：判据侧修订 **R12**（数据之后追加），提交 `f63097b`（`+13/-1`，只动 `source_profile` 与 `a_hit` 两处，均在 A 族抽取/匹配内）。下面的原始诊断保留，作为「为什么修在抽取侧而不是匹配点」的依据。

**修法（R12）**：`source_profile` 对源文本也跑一次 `RE_PLATE`，收进**独立的`plate`桶**（不与 `latin` 混，避免污染 P/N 族），`a_hit` 先查 `plate` 再查 `latin`。没有采用「`a_hit` 双向包含」：那是在匹配点打补丁，两侧形状仍然不一致，换个省份字/分隔符同样的漏命中会以另一种形状回来。
实测：主块挂着、问题「我车牌号是多少？」、模型正确答 `车牌号是浙B-3F19K。` —— 校验器仍判 `unsupported`。原因是判据里
**答案侧与源侧的车牌归一化不对称**：
| 侧 | 规则 | 结果 |
|---|---|---|
| 答案 | `RE_PLATE = [\u4e00-\u9fff][A-Za-z][-· ]?[A-Za-z0-9]{4,6}` → `alnum_key` | key = `浙B3F19K`（**带省份字**） |
| 源 | `RE_CODE` 从拉丁/数字起 → `alnum_key` 进 `prof["latin"]` | `B3F19K`（**丢了省份字**） |
| 判定 | `a_hit= key in latin or any(key in s for s in latin)` | 只查「答案 key ⊂ 源词」，不查反向 ⇒ `浙B3F19K` vs `B3F19K` **漏命中** |

复现（一条命令，不需要引擎）：
```
cd kvmem/m2_visibility/m4 && python -X utf8 -c "
import sys,sqlite3; sys.path.insert(0,r'D:/llama-mem/kvmem/m2_visibility/m5')
import m5_ground as G
t,_=G.verify_sources(sqlite3.connect('_m5db/m5_m4_blocks.db'),['blk_conv_2026-10-25_01'])
p=G.source_profile(t); print(p['latin'], G.extract('浙B-3F19K'), G.a_hit('浙B3F19K',p), G.a_hit('B3F19K',p))"
# {'B3F19K'} […] '浙B3F19K' → False, 'B3F19K' → True
```
**这是判据缺陷，方向是「该支持判成不支持」**，产品可见后果是「把正确车牌答案答成『记忆里没有记录』」。
按你冻结判据的要求，我**没有**动 `m5_ground.py`（`git diff HEAD -- kvmem/m2_visibility/m5` 为空）。可选出路（请你定）：
1. 解冻 `a_hit` 一行改成双向包含：`return key in latin or any(key in s or s in key for s in latin)`（最小、可回归）；
2. 让 `source_profile` 也用 `RE_PLATE` 收一次 key（源侧补上省份字），同样是一行级；
3. 判据 1 改写为「车牌正向例在题型层面不参与」（即承认 A 族 CJK 前缀车牌暂不可判），我把这条记成已知缺口。

### 19.6 判据现状（`run_m5_grounded.json .acceptance`）
| # | 结果 |
|---|---|
| 1 车牌正向 supported + display 不变 | **true**（R12 后：`A:浙B-3F19K hit=True`，`answer_display == display_pre_grounding`） |
| 2 消融例 unsupported + display=`记忆里没有记录车牌号。` | **true** |
| 3 「我住在哪？」两块下都 supported + display 逐字节不变 | **true** |
| 4 四条记录齐全（挂载块/hard facts/三值/最终显示，可追到块 sha） | **true** |
| 4b 三值都留痕 | `["supported","undecidable","unsupported"]` |
| 5 判据只按 R12 改一处 | `git show f63097b -- kvmem/m2_visibility/m5/m5_ground.py` = 3 个 hunk、全在 `source_profile` / `a_hit`；工作树 blob `ee9ca1c` 与 HEAD 一致（`git diff HEAD` 空 = 测的就是提交的） |
| 附加 不退化 | `m3/` 未改、`m4/` 既有文件未改（只新增文件） |

### 19.7 一条可复制命令 + sha 锚点
```
cd kvmem/m2_visibility/m4 && python -u -X utf8 m4_verify_grounded.py     # 四例 + 三值 + 断言
```
| 对象 | sha256 |
|---|---|
| 主块 `blk_conv_2026-10-25_01.kvmem`（91 cells） | `81127d24fd64b96bc86751cd2789abdf40c06cc111d0a977437f596b347334e6` |
| 消融块 `blk_conv_noplate_2026-10-25_01.kvmem`（79 cells） | `e3bfec41d1f059e7d062a5e50a22802fe38cbf91cae2283b8a4a6c48ce940c04` |
| M5 侧文本副本（内容哈希，重建稳定） | `876deaa3a4b7ad1d4a01f49e2a451b0c577b3feb6aaf86f03920fe2e98e07edf` |

### 19.8 边界提醒（写死在这里，避免被误读）
- 校验器只管**无中生有**，不管**张冠李戴**：例如把「我住的小区叫蓝鲸」这种错配判 `supported` 是**设计**，不是缺陷。
- 本文档不写「M5 修好了接地」这种话。M5 只是**在生成之后**把「块里没有的硬事实」拦下来并置为弃答文本，
  且有 §19.5 那个反向缺陷 —— 它既不是万能的，也不是没错的。
### 19.9 R12 修复后的全量重跑（六项逐条，一条命令一条结果）
判据侧修订：**R12**（A 族源侧补 `RE_PLATE` 桶），提交 `f63097b`。
| # | 要求 | 实测 | 结论 |
|---|---|---|---|
| 1 | M5 原四例：住址/项目/习惯 supported、车牌 unsupported | 住址 supported、项目 supported、习惯 supported、车牌 **unsupported** | ✅ |
| 2 | M5 三边界 | 三月十四号 → supported；3月15日 → unsupported；源缺失 → **undecidable 且不重写** | ✅ |
| 3 | `form_invariant_all_four` | `true`（I1 首句 / I2 全文四例判定一致） | ✅ |
| 4 | 交叉检验 E/F/X1/B57 全 supported | E supported、F supported（含「蓝鲸」）、X1 supported、B57 supported | ✅ |
| 5 | `test_m5.py` 的 acceptance 全 true | `three_supported_in_both_forms / plate_unsupported_in_both_forms / form_invariant_all_four / supported_answers_untouched / boundary_all_pass / false_positive=0 / false_negative=0 / all_pass` —— **8 键全 true**（`evidence_m5.json` 真正结构是 `acceptance(8) + four_cases(4) + boundary_cases(3) + cross_check_np64(4)`，没有 16 键的 acceptance 块；「16 键」是 M4 `run_m4_verify.json` 那张表，§16） | ✅（附更正） |
| 6a | `plate_main` 必须转为 **supported** 且 display 逐字节等于原答案 | verdict `supported`，`A:浙B-3F19K hit=True` ×2，`answer_display == display_pre_grounding`（相对原答案 `answer_exact` 只少了 think 标签那一行，即除 think 清洗外逐字节相同） | ✅ |
| 6b | `plate_ablated` 必须**仍 unsupported** | `unsupported`，`A:苏K12345 hit=False`（消融块文本里没有车牌，`plate` 桶为空），display = `记忆里没有记录车牌号。` | ✅ 没放宽过头 |
| 6c | home 两例仍 supported | 两块下都 supported，display 逐字节不变 | ✅ |

方向相反的两半同时成立，这一对才是证据：**同一句问法，块里有 → 原样给；块里没有 → 弃答**。
一条命令：`cd kvmem/m2_visibility/m4 && python -u -X utf8 m4_verify_grounded.py`（M5 自身：`cd ../m5 && python -u -X utf8 test_m5.py`）
唯一新增判据字段：`source_profile.prof["plate"]`（独立桶）+ `a_hit` 先查 plate；其余判据、阈值、规则一律未动。

**R12 没有放宽过头**（桥级探针，同一块同一问法，只换答案里的车牌值）：
| 挂载块 | 答案里的硬事实 | 判定 | 显示 |
|---|---|---|---|
| 主块 | `A:浙B-3F19K` hit=True（源里真有） | supported | 原样 |
| 主块 | `A:苏K12345` hit=False（换了车牌） | **unsupported** | `记忆里没有记录车牌号。` |
| 消融块 | `A:苏K12345` hit=False | **unsupported** | `记忆里没有记录车牌号。` |
| 主块 | `N:13900001111` hit=False（幻觉手机号） | **unsupported** | `记忆里没有记录手机号。` |
修复只让**「源文本里真实存在的那个车牌」**能命中；换成另一个车牌、或换到没有车牌的块，仍然弃答。

### 19.10 R12 定稿：只动抽取侧 + (a)(c) 探针 + 交付锚点

**① R12 最终形状（`a_hit` 一字未改）**：`source_profile` 对源文本跑 `RE_PLATE`，
把带省份字的 key 补进 **`latin` 这个 `a_hit` 本来就在读的集合**（`prof["plate"]` 另存一份只作审计桶），
于是匹配逻辑完全不动。`git diff e172aca -- kvmem/m2_visibility/m5/m5_ground.py` 只有 3 个 hunk，
全在 `source_profile` 内；`def a_hit` 未出现（脚本里 `shape.touches_def_a_hit=false`、
`a_hit_body_identical_to_pre=true`，`alnum_key` 两处调用点 == `extract` 的 A 族抽取 + `source_profile` 的 plate 抽取）。
> 来源交代：`f63097b` 里那份 `m5_ground.py` 改动是被 `git add -A` 扫进去的（lead 已声明），
> 里面那版曾在 `a_hit` 里加过 plate 分支；**本提交把它改成抽取侧方案，`a_hit` 已回滚到与 `e172aca` 逐字节相同**。

**② (a) 省份错、身体对 ⇒ unsupported（省份字判别位还在）**
| 答案 | 源里的车牌 | 判据 key | verdict_before | verdict_after |
|---|---|---|---|---|
| `您的车牌是苏B-3F19K。` | `浙B-3F19K`（主块） | `苏B3F19K` ∉ {`B3F19K`, `浙B3F19K`} | unsupported | **unsupported** |
双向包含若被采用，这里会变成 `supported`（把编造当命中）；现在没有这条例外。

**③ (c) 裸 body 归属：A 族代号类，且只算一次**
| 写法 | extract 结果 | 归类 | 命中机制 | before | after |
|---|---|---|---|---|---|
| `您的车牌是B3F19K。` | key=`是B3F19K`（`RE_PLATE` 吞紧邻 CJK 字） | 车牌类 | 两侧都没有这个 key | unsupported | unsupported |
| `车牌:B3F19K。`（前缀非 CJK） | key=`B3F19K`，1 条 | **代号类（RE_CODE）** | 源侧 `latin` 早有 `B3F19K`（`RE_CODE` 收的） | supported | supported |
- **不两边各算一次**：`RE_PLATE` 需要 CJK 前缀，裸 body 只会被 `RE_CODE` 收，`extract` 的 masking 保证 1 条（`claimed_once=true`）。
- **不算 R12 的新命中面**：`a_hit` 里从来没有 `any(key in s for s in plate)` 这种分支（那是被否掉的草稿），
  R12 只是往它已经在读的 `latin` 里补了带省份字的 key。
- **顺带记一条既有行为**（本轮不授权修）：`RE_PLATE` 不要求分隔符，所以「是B3F19K」「号B3F19K」会把紧邻 CJK 字吞进 key，
  结果判 unsupported —— 方向是安全侧（弃答），且 before == after，与 R12 无关。

**④ 机器可判的 D 表**：`run_m5_fix_compare.json`（`m5_fix_compare.py` 产出）
| 键 | 值 |
|---|---|
| `row_count` / `non_flip_count` / `flip_count` | 22 / 21 / 1 |
| `flips` | `["product/plate_main"]` |
| `all_non_flip_hold` | true（20 条非预期翻转全部 before == after） |
| `all_flips_happened` | true |
| `all_expected_after_hold` | true（22/22 after 等于期望） |
| `pass` | true |
覆盖：M5 原四例 I1+I2（8）、三边界（3）、交叉检验 E/F/X1/B57（4）、产品四例（4）、(a)(1)、(c1)(c2)(2)。

**⑤ R13 口径（写死，别再混用）**
- **检索单元数 = `SELECT COUNT(DISTINCT unit_id) FROM memory`** → **4**；`SELECT unit_id, COUNT(*) FROM memory GROUP BY unit_id ORDER BY unit_id` → `[(2,1),(3,2),(4,1),(5,2)]`（fanout [1,2,1,2]）。
- `SELECT COUNT(*) FROM memory_source` → **5**，其中 `SELECT id,name,label FROM memory_source WHERE name LIKE 'conv%'` → `[(1,'conv_2026-10-25','对话')]` 是**段级行，不是检索单元**。
- 两个数差 1 是**定义差**，不是数据不一致。

**⑥ 本轮交付锚点（重跑即失效）**
| artifact | path | sha256[:16] | mtime |
|---|---|---|---|
| 判据文件（主角，在改动清单里） | `kvmem/m2_visibility/m5/m5_ground.py` | `86b7c501ab9904aa` | 03:51:46 |
| 桥 | `kvmem/m2_visibility/m4/m5_bridge.py` | `706c00d0345fe3c2` | 03:52:12 |
| 作答路径 | `kvmem/m2_visibility/m4/m4_answer_grounded.py` | `54125ea0ec1e4f51` | 04:03:06 |
| 消融块构建 | `kvmem/m2_visibility/m4/m4_ablate.py` | `172b5fa39eed84cd` | 03:37:27 |
| 验收编排 | `kvmem/m2_visibility/m4/m4_verify_grounded.py` | `9247e3fa19427eab` | 04:03:06 |
| 前后对照 | `kvmem/m2_visibility/m4/m5_fix_compare.py` | `0e9e60882c8f55ba` | 03:55:54 |
| 验收 json | `kvmem/m2_visibility/m4/run_m5_grounded.json` | `d97cdfdcbd6c6d3d` | 04:04:44 |
| 对照 json | `kvmem/m2_visibility/m4/run_m5_fix_compare.json` | `5f7c196a32a659a6` | 04:04:44 |
| 消融 json | `kvmem/m2_visibility/m4/_ablate/run_ablate.json` | `8d0998c0014dde03` | 03:38:01 |
| 消融库 | `kvmem/m2_visibility/m4/_ablate/m4_memory_noplate.db` | `c44abc2547aad560` | 03:38:01 |
| M5 文本副本（文件） | `kvmem/m2_visibility/m4/_m5db/m5_m4_blocks.db` | `9b833f09480a77cc` | 04:03:06 |
| 消融块 | `kvmem/m2_visibility/m4/_ablate/blocks/blk_conv_noplate_2026-10-25_01.kvmem` | `e3bfec41d1f059e7` | 03:38:00 |
| M5 证据 | `kvmem/m2_visibility/m5/evidence_m5.json` | `0f57f4357452a865` | 03:48:20 |
| M4 验收 json（未重跑） | `kvmem/m2_visibility/m4/run_m4_verify.json` | `bdf392e8f9a672a7` | 02:59:13 |
| M4 库（未重跑） | `kvmem/m2_visibility/m4/m4_memory.db` | `817a66e45a4e3594` | 02:57:20 |
| M4 写入 json（未重跑） | `kvmem/m2_visibility/m4/run_m4_write.json` | `6408d8e2ecdf6ee5` | 02:56:53 |
| 主块（未改） | `kvmem/m2_visibility/m4/blocks/blk_conv_2026-10-25_01.kvmem` | `81127d24fd64b96b` | 02:56:44 |

**M4 三产物未重跑**（本轮没有执行 `m4_verify.py` / `m4_write.py`）：
`run_m4_verify.json = bdf392e8f9a672a7｜m4_memory.db = 817a66e45a4e3594｜run_m4_write.json = 6408d8e2ecdf6ee5`，
与你独立重算的三个锚点一致。

**本轮未改动的文件清单**：`tools/` 全部、`kvmem/m2_visibility/m3/` 全部、`m4/` 既有脚本
（`m4_write.py / m4_extract.py / m4_store.py / m4_display.py / m4_newproc.py / m4_verify.py / m4_crosscheck.py / m4_pos0_refuse.py / _test_*.py / _probe_*.py`）、
`m4/blocks/blk_conv_2026-10-25_01.kvmem`（`81127d24fd64b96b`）、`m5/memory.db`、`m5/test_m5.py`、`m5/build_memory_db.py`。
改动清单只有：`m5/m5_ground.py`（R12，抽取侧一处）+ `m4/` 下 5 个新文件 + `m4/README.md`（本文）。


### 19.11 收尾两件（检测员非阻塞遗留）

**(i) 消融库「检索命中 0」的原始分数，现在在 `mount_evidence` 里**（原先只在 `mount_meta`，读的人看不到）
`run_m5_grounded.json → cases[plate_ablated].mount_evidence.retrieval_probe` 原值：

| 键 | 值 |
|---|---|
| `query` | `我车牌号是多少？` |
| `hit` / `hits` | **0 / 0** |
| `top` / `top_score` / `top_source_id` | `null / null / null` |
| `gate` | `{"GATE":1.3,"COV_MIN":0.35,"INDEX_VERSION":5}` |
| `value_gate` | `{"property":"plate","scope":null,"allowed_sources":0,"abstained":true}` |
| `value_gate.why` | `no memory_source states this property for this scope -> _search_one returns [] before scoring` |

「top 分」在消融库里**不存在**：不是分数低被门限挡掉，而是值门控在打分之前就弃权
（`tools/retrieval.py::_search_one` 里 `allowed` 为空直接 `return []`）。
这才是「为什么被迫 all-blocks」的可审计理由，比一个 0 分更硬。

**(ii) 四个 sha**：`run_m5_grounded.json` 因为 (i) 的补测必须重跑，按锚规则已换过两次：

| 文件 | 旧值 | 状态 | 当前 |
|---|---|---|---|
| `run_m5_grounded.json` | `5cd106eead0c9bac` → `dd8703d1022cdeb9` | **均已失效** | `d97cdfdcbd6c6d3d` |
| `run_m5_fix_compare.json` | — | 有效（重跑后字节相同） | `5f7c196a32a659a6` |
| `m5_ground.py` | — | 有效 | `86b7c501ab9904aa` |
| `_before/m5_ground_preR12.py` | — | 有效 | `ea749781368c798e` |

json 自身无法记录自己的 sha（写进去就变了），所以 `delivery_anchor` 里给的是
`run_m5_grounded_json_previous_run` 并在 `invalidated_anchors` 列出了作废值；
**权威值只认这张表**（表由产物文件重算，不手抄）。

**锚账本（只追加，README 是权威落点；`anchors_history.json` 是同内容的机器可读副本，按仓库策略不入库）**

| # | 字段 | old_sha16 | new_sha16 | 原因 | 时间 |
|---|---|---|---|---|---|
| 1 | `run_m5_grounded.json` | `5cd106eead0c9bac` | `dd8703d1022cdeb9` | 修验收脚本自身三处误报（C_shape / D_before_after / 未改动白名单）需真引擎重跑 | 03:57 |
| 2 | `run_m5_grounded.json` | `dd8703d1022cdeb9` | `d97cdfdcbd6c6d3d` | 收尾 (i)：mount_evidence 补原始检索分数（hit=0 / top=null / value_gate 理由）=> 重跑 | 04:04 |
| 3 | `m4_memory.db` | `817a66e45a4e3594` | **未变** | Stage 1b 未对真库执行（层 1 无 M4 语料容器，待裁决） | 04:20 |

规则：**只追加、不覆盖**；每跑一次就断一次链的记录等于没有记录。
验收结论里的锚值以验收方重算为准，本表与 json 只作旁证。

**并 store 一句**：`m5_ground.py` 的 R12 diff 落在 lead 的 `f63097b` 里（他 `git add -A` 扫的），
最终形状由 `0cf588b` 定稿；引用请用 `git diff e172aca -- kvmem/m2_visibility/m5/m5_ground.py`。


### 19.12 Stage 1b：层 2 可校验化（机制已就绪，**未对真库执行**）

**先说一条必须由 lead 裁决的事实**（机器输出，不是推测）：

| 层 | 内容 |
|---|---|
| 层 1 = `kvmem/chat.db::memory_source` | `id=1 profile(61 chars)`、`id=2 project(45 chars)` |
| 层 2 = `m4/m4_memory.db::memory_source` | `conv_2026-10-25(127)` + 4 条 `fact_*` |

`m4_layer2_link.py` 逐行解析的结果是 **5 行全部 no layer-1 container**：
M4 的语料（2026-10-25 那段对话）**根本不在注册表里**，注册表只有 chat.py 的 profile / project。
所以 C4-a / C4-b 照现状**不可能通过** —— 不是实现问题，是层 1 里没有容器。

两条路径都在**库副本**上跑过（真库一个字节没动）：

| 路径 | 做法 | 结果 |
|---|---|---|
| A 现状 | 不提升、直接链 | 四条断言全 FAIL，5 行 no layer-1 container |
| B 提升 | `--register-source conv_2026-10-25`（走未改动的 `put_source`） | C4-a/b/d/e **全 OK**：1 行 exact + 4 行 substring 全部指向 `conv_2026-10-25`，两条负向测试 OK |

路径 B 的关键原值：`conv_2026-10-25` 走 `exact`，4 条 fact（21/23/13/26 字符）走 `substring`，
全部落在同一层 1 行；`text_origin` 由 `m4.memory_source.text` 改写为
`registry:conv_2026-10-25@d8c094c1f5fcb8f1`，且能反解回 `(registry_source_id=3, sha256 全文)`。

**第二个事实**：消融库 `_ablate/m4_memory_noplate.db` 的 conv 文本是**删掉一句后的编辑文本**，
按"层 2 不得出现层 1 没有的文本"，它**不能被注册**（否则等于把衍生文本塞进权威层），
所以它的块在 `_m5db` 里被显式标为 `declared_synthetic`（见 `origins_summary`），不并入 registry 链。

**机制清单**（`m4/m4_layer2_link.py`，加 `--apply` 才写库）：
`migrate` 加两列；`do_link` 解析 exact / substring（多容器时拒绝猜测）；
`assert_linked` / `assert_substrings` / `assert_no_foreign` / `assert_not_stale` 四条断言；
`backfill_origins` 改写并回查；`resolve_origin` 反解 `registry:name@sha16`；
两条负向测试（外来文本 -> `ForeignText`；层 1 hash 变 -> `Stale`）。
`m5_bridge.py::origin_of` 已改为**链接优先**：已链写 `registry:name@sha16`，
未链保留字面量并标注 `unlinked: ...`（不会被误当已解析）。

**锚账本**：`m4/anchors_history.json`（只追加，每条 `(field, old_sha16, new_sha16, reason, time)`）——
因为 `delivery_anchor` 里的 `*_previous_run` 每跑一次就被覆盖，链条会断。
