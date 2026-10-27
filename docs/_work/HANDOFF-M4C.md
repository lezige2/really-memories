# 交接稿 · llama-mem / M4-C 验收

> 新会话的第一件事：读这份，然后**重算所有 sha**。本稿里的 sha 在下一次落地后全部作废。

---

## 0. 会话设置（照抄）

**角色三分，同一套 DSH Agent Teams：**

| 角色 | 名字 | 职责 |
|---|---|---|
| Lead | `lead` | 分解 / 派单 / 复核 / 验收。**不动代码、不跑实验。** |
| 检测员 | `inspector` | **只读**分析、写台账、**审 lead 的报告**（它会指出 lead 的错，这是设计的一部分） |
| 执行者 | `executor` | **唯一动手方**（改码、跑实验） |

**用户原话定性**：「你当 lead：只做分解 / 派单 / 复核 / 验收，不亲自改代码、不亲自跑实验。」

**工作目录**：`C:\Users\lezige\Documents\deepseek-harness\default-workspace`
**仓库**：`D:\llama-mem`
**Python**：3.12.14（用 load_workspace_dependencies 取路径）

---

## 1. 项目是什么

**把长期记忆存在 KV tensor 里**，而不是 prompt 文本里。被测对象是 LLM 的 kv cache 内存管理（lease / seq / cell 三层）。

- 模型：`D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf`（8,988,110,240 B，sha256[:16] `0b319bd0572f2730`）
- n_ctx 8192 / n_seq 8 / `-ngl 99` / KV **q8_0** / bytes_per_token **104448**
- DLL `kvshim_vk.dll` sha16 `9edbafa150700614`
- 硬件：无 NVIDIA；AMD RX 6750 GRE 10GB + Vulkan
- **7B 那条线已冻结，不再使用**（用户裁定：「我请求不再使用 7b 的东西，全部在 14b 上重新测试」）

---

## 2. M4-C 要回答什么

**把某个站点（site）的 `leases.reset(...)` 调用删掉，会发生什么？** —— 检验这些内存管理机制是否真的在承重。

**四态验收（闭集）**：**通过 / 未通过 / 未接上 / 未做**

**关键区分**：**判据作废 ≠ 未通过**。判据要求的东西在架构里不存在 ⇒ 判据作废。判法：**先问这条判据要求的东西在架构里有没有位置。**

**当前判决（未签）**：
- v2①-a：**绿半可签 · 红半不可签**（无当前身份的红臂产物）
- v2①-b：**判据作废**
- ②：**未通过（1/3）**
- ③：**未接上**
- ⑤：**作废**（`control` 机制已删除）
- **锚 `fa94b1bc58c0e421` 可签**（`kvmem/sessions/live.json`，配方：json.loads → pop("saved_at") → json.dumps(sort_keys=True, ensure_ascii=False) → sha256[:16]）

---

## 3. 现在卡在哪：零条验收读数

**六臂还没跑。** 跑过一次，五份产物全是 `exit 5`，因为**当时写日志的函数体是空的（只剩 docstring）**。

链条是：**被测对象 → 判据 → 日志通道 → 产物 → 快闸 → 复核者**

---

## 4. 立即要做的四件事 + 六跑

### 4.1 四处落地（`tools/chat.py`）

1. `cmd_chat` 的 attach（~L298–301）之后写 `_event({"id": "chat.attach", "seq": i})`
2. `cmd_m1` 的 attach（~L587）之后同样写一条
3. 跑前自检，**三个条件**：`a.get("id") == "chat.attach" and a.get("role") == "event" and a.get("site") is None`；任一不符 ⇒ 停，报 lead
4. `attaches_done` 期望：DELETE 两臂 `>= 1`；读 0 ⇒ 停（不是「没 attach」，是「这条又坏了」）

`_event` 会把 `role="event"` / `site=None` 写死 ⇒ 构造上不进 `covers_observed`。
**不要带 `kind`** —— 所有消费者都是 `.get("kind")` 守卫，带了反而多一个可能与 `role` 打架的维度。

### 4.2 台账 `land.py` 三处

- **删 `lines`**（行数有口径自由度，且它会冒充「变了」）
- 加 `sample_gap_s`（两次采样间隔 + 值是否全同）
- **把自己也记进 `files`**（检查者若不过同一套检查，它就是回声的最后一个藏身处）

### 4.3 其余

- `scope_resolved` 落盘为**解析后的文件清单**，不是 glob（模式随环境变，清单不随）
- `tag` 由 `batch_id` 派生，不许手写（同一批里两个尝试号会让批次散掉）
- 第六臂四项读数：`cells_control_empty_seq`（带 `why_empty`）/ `cells_readings_all` / `control_tag`+`sites_readers` / `control_failed`

### 4.4 六跑（命令行只许从签名抄）

```
# run_site3.py L37-38: mode in (green, red, unmount-dropnonempty); tag = argv[2]
export M4C_FIXTURE_FILE=; python run_site3.py green                <batch>-green
export M4C_FIXTURE_FILE=; python run_site3.py red                  <batch>-red
export M4C_FIXTURE_FILE=no_such_fixture.py; python run_site3.py green <batch>-inject
export M4C_FIXTURE_FILE=; python run_site3.py unmount-dropnonempty <batch>-drop
# redcheck_delete.py  site=argv[1] mode=argv[2] tag=argv[3]
export M4C_FIXTURE_FILE=; python redcheck_delete.py 1 base    <batch>-base
export M4C_FIXTURE_FILE=; python redcheck_delete.py 1 deleted <batch>-deleted
```

### 4.5 每臂预期

| 臂 | 预期 |
|---|---|
| green | `exit 0` · selfevidence 全真 · `hits []` · `coverage_ok true` |
| red | `is_red true` · `die_kind assertion` · `exit 1` |
| inject | `selfevidence (T,F,T)` · `instrument finalize_error` · `exit 5` |
| drop | `dropped_count > 0` · 0 次 `die` |
| DELETE base / deleted | `attaches_done >= 1` · `coverage_ok true` · 两臂 `loads` 逐字段相同 |

---

## 5. 下一批（六跑之后）

1. `except OSError: pass` → `_M4C_WRITE_ERRORS` 收异常 **+ 由夹具落盘 `rec["log_write_errors"]` + `verdict` 消费**（三处同批，缺一即废）。**记录失败不能写回失败的那个通道。**
2. `cells_of` 出错折成 `1` → 返回 `None` 或抛专用异常，调用方记 `instrument`。**UNKNOWN 不许冒充差异。**
3. 删 `_m4c_witness_cells_zero` 调用点，函数标 `no_discrimination`（它能证伪的集合为空；覆盖由 L562–565 的 sites 调用流判据承担）
4. `redcheck.py` L119 加 `run_id` + tag（现在是 overwrite-only writer）
5. `m4c_verdict` 的 `def_mismatch_detail` 两个未读谓词；两处 docstring（`m4c_harness.verdict` → `m4c_verdict.verdict`；「八值」→「九/十值」）
6. `stale` 谓词挪到快闸，删 `harness_sha16_now`
7. **M4-C-3**：`cmd_m1` 对未建候选 KeyError ⇒ skip 必须出声（`skipped_unbuilt: [names]`），`except KeyError: continue` 禁止
8. **M4-C-4**：pool leak —— `orphan = sum(int(eng.n_tokens(s)) for s in range(1, N_SEQ) if s not in mounted_seqs)`，同时记 `chat_n`
9. **M4-C-2**：写断言之前，先定义 restore 之后每个 seq 装什么

---

## 6. 交接的核心：规矩集

**这一节比上面所有小节都值钱。** 它们是踩出来的，而且每条都是在它已经骗过我们一次之后才写的。

### 6.1 一条判据的价值 ≈ 它能证伪的东西的数量

**零 ⇒ 它不是判据。** 判「一条判据有没有判别力」的唯一方式是**枚举它的候选消费者**；docstring 是自述，不是枚举。

### 6.2 空集读数必须配三层分母

| 情况 | 分母 | 判 |
|---|---|---|
| 一个文件都没扫到 | `files_scanned = 0` | 失败 |
| 扫到 N 个，0 个可能违规的对象 | `with_calls = 0` | `no_discrimination` |
| N 个文件、M 个可能违规、0 违规 | `with_calls = M > 0` | `ok` |

**缺任何一层，「干净」就不成立。**

### 6.3 MISSING ∉ EQUAL，而它的反向是 UNKNOWN → RED

| 方向 | 形态 | 危险 |
|---|---|---|
| MISSING → PASS | 没看到证据 ⇒ 判通过 | 假绿 |
| **UNKNOWN → RED** | 量不到 ⇒ 判红 | **假红，而且它诱导我们去改被测对象** |

**两个方向同源：一个值承载了两个含义。表示「我不知道」的值必须在类型上与所有合法读数可分（`None` 可分，`1` 不可分）。**

**假红比假绿更容易被「修好」**：真的红要改被测对象，假的红要改测量；改了前者，缺陷仍在而读数变绿。

### 6.4 try 内不许用「表达式求值失败」表达判据

`assert` 不行、`TypeError` 不行、`KeyError` 不行。**`raise` 的接收方是 `except`，不是检查者。**

- 判据只能以**字段**形式落地，由 `instrument_hits` 判
- 要排除「漏写某个键」，**最有效的不是把它变成必填参数，而是让它没有可填的地方**（两个专用入口 `_crit` / `_event`）
- 修一个「会被吞掉的错误」时，**先问「吞它的是谁」，再决定改载体还是改接收方**。接收方不变，换任何载体都还是被吞
- `except` 里不许 `pass`，必须写一个字段 —— **那个异常本身就是读数**
- 但**记录失败不能写回失败的那个通道**（自指兜底在失败时必然一起失效）

### 6.5 守动作，不守声明

| 判断的对象 | 被守的是 | 被替代的是 |
|---|---|---|
| 类标签 | **调用方** | 结果长什么样 |
| 配置字段 | **发生了什么** | 允许了什么 |
| 写入者 | **文件路径的唯一写者** | 函数名的唯一调用者 |

### 6.6 覆盖必须等于「要回答的问题所涉站点」，不多不少

判据红时**先问「对象错了还是声明错了」**——大多数时候是声明被改宽了。
**收窄 = 范围是一个列表（可核）；开豁免 = 规则里有一个例外（不可核）。**
**排除必须被写下来**：`scope` 与 `scope_excluded` 同等重要，因为后者决定 0 命中能覆盖多远。

### 6.7 一条判据的 0 命中必须声明它覆盖哪些形态

**否则 0 被读成「全面干净」。** 已知三种死法：① `return` 之后 ② 被覆盖 ③ 零调用。`dead_after_return` 只抓 ①。

### 6.8 新判据的第一次读数应该是红

若第一次就绿，**先怀疑扫错范围**。
**但 ① 已知正确对象上不误报，必须早于 ② 人为构造的错误对象上能红。误报致死，漏报致病。**
**新判据的第一次读数是它自己的人为错误验收。**

### 6.9 「在 X 里」必须追问：词法还是语义？

**可核的那个不一定是真的那个，而它更容易被写进检查、也更容易通过。**
**位置 ≠ 可达**，已犯两次（`asserts_in_try` 词法 0 / 语义 3；`skipped` 代码里 2 / 本次配置下 0）。
**可达性不是一条判据，是一切的先决条件** —— 一条不可达的判据与一条不存在的判据观测上等价，而它的样子是「已实现」。

### 6.10 異层定义

**见证者参数表只允许「结果读数」与「常量」。** 参数表里出现、函数体不读的形参 = 承诺了但没写的谓词。

### 6.11 新键只加在有唯一读者时

`kind` 被「死因」占用，就不要再拿它承载「条目类别」（用 `role`）。
**同名参数必须同义；不同义必须不同名。**

### 6.12 可变量可以进报告，不许进判据

**标识只许 `sha16`**（内容同则必同、内容异则几乎必异）。行数有口径自由度，两个人都数了会数出两个不同的数，而**那个「不符」会冒充「变了」**。

### 6.13 报告与落地之间必须有先后

**先落地 → 再写台账（`LANDED-<batch_id>.json`：每份只记 `sha16` + `bytes`）→ 再报告；报告只引用台账里的 sha。**
**若某份报告写的 sha 在台账里不存在，那份报告从未存在过。**
**停手的可判定形式：间隔 ≥30 秒采样两次、七份 sha 完全相同。**

### 6.14 能构造上排除的，不要留成纪律

一条规矩若只在立它的那一节里被用，它就不算立。**它必须有一个可核形式**（集合不相交 / 字段 / 退出码）。

### 6.15 三向同批

- 加字段与接消费者同批
- 删字段与删守卫同批
- **换路径与删旧路径同批**（最隐蔽：行为不变而外观变了 = 「半改」）

### 6.16 删「唯一的见证」≠ 删死代码

在 diff 里长得一样，在证据链上完全不同。**判法：删之前问「这条判据被删掉之后，还有谁会在同样的情况下响？」答案「没有人」⇒ 那是撤判据，必须走撤判据的手续。**

### 6.17 一条「先怀疑 X」的规则，必须先说明「Y 在同样的读数下也成立」

否则它把 Y 放过去了。**今晚八次「我见过的错误 = 全部可能」**：判据 / 守卫 / 搜索范围 / 参数表 / 扫描面 / 可达性 / 唯一性 / 假红的归属。

### 6.18 阻塞判法

**一个缺陷是不是阻塞，判法是：它会不会让「期望的那份读数」不可解释。**
**不是「会不会让某个读数不可解释」——后者无界，而今晚九次追加就是这个判法的产物。**

### 6.19 字段名必须描述它数的是什么，不是它想回答什么

「想回答什么」在我们脑子里，「数的是什么」在代码里；两者一分叉，**名字就开始替读数作证**（`attaches_done` 说过「发生了几次 attach」，数的是「日志里几条 id 以 .attach 结尾」，而那类条目从来不存在）。

### 6.20 命令行参数只许从签名抄

**写全 ≠ 写对。** 已犯三次（redcheck_delete 的 argv 顺序、两个夹具 argv 不同、mode 名写成 green-dropnonempty 而签名是 unmount-dropnonempty）。

### 6.21 退出码

**0 PASS / 1 判据红（被测对象错） / 2 用法错 / 3 环境或编码错 / 4 控制闸几何不兼容 / 5 仪器错**

「两个人在不同的文件上工作」用 **3**，不用 5 —— 它不是仪器坏了。

### 6.22 自证四样

**主体（`fixture_file_used`）· 版本（`harness_sha16`）· 判定（`instrument`/`instrument_hits`）· 配置（`attaches_done`）**

**自证的上限是自洽；类别必须外赋。** 凡「关于这份产物的判断」，输入至少有一部分必须来自产物之外。
**引用用文件字节 `sha16`（永远可算）；自述用正文（可以缺）；两者结构上分开、不得平铺。**

### 6.23 链条的终点

**复核者是链条的终点，而终点没有见证——这是这个结构唯一诚实的缺陷。**
缓解：每个判定写成**带产物名与 sha16 的一句话**。**这不是让终点有见证，是让终点可被追责。**

---

## 7. 用户已经裁定过的事（不要重问）

| 事项 | 裁定 |
|---|---|
| 7B 模型 | **不再使用**，全部在 14B 上重测 |
| M2.5 | **归档销号**，从路线图移除 |
| `control` 机制 | **已删除**，判据作废 |
| 备份目录 | **移出仓库** |
| 参与度 | M3 用户跟；**M4/M5 由三个 agent 决定** |
| M4-C 怎么收口 | **未定**（见下） |

---

## 8. 悬而未决

1. **M4-C 怎么收口**：① 六跑读数一到就收口（能签的签、其余记缺口）② 先补两处会让读数不可解释的再跑 ③ 加固到六条判据全到位
   —— 用户答的是「为什么读数会是 0？」，然后要了外请教要，**没选**。
2. **外请教要已写**：`M4C-外请教要.md`。核心问题：**我们缺的那个词，很可能是「溯源性（traceability）」** —— 读数能不能溯源到一个与被测对象无关的基准。现在不能，它只能溯源到我们自己写下的那个字面量。

---

## 9. 其他文档

| 文件 | 大小 / sha16 |
|---|---|
| `D:\llama-mem\README.md` | 21,654 B / `85f6a7d38b85bb49` |
| `D:\llama-mem\PROGRESS-AND-ROADMAP.md` | 188,769 B / `32c68080b8f52d63` |
| `D:\llama-mem\docs\_work\CONSOLIDATION-LEDGER.md` | 557,487 B（检测员写的台账） |

**路线图位置**：L172 成本 · L779–805 §5.7 四站表 · L1751–1760 §13.2 M4-C · L1825–1831 §13.9 四项链式表。

---

## 10. 归档时的实测记录（不是结论，是一次采样）

> **这一节刻意不写「当前状态」。** 因为「当前」是一个会过期的词，而它不写在脸上——**§10 上一版写了「`LANDED-87106d8a` 已过期」，而那时最新台账已经是 `b06` 了；照着它读的人在 `b06` 上会重犯一次。**
> **所以下面写的是一次测量本身，加上复现它的方法。你读到的时候它一定已经旧了，这正是它该被复算的理由。**

### 10.1 采样记录

**采样方式**：列出 `kvmem/m4c_leases/out/LANDED-*.json`，按 mtime 取最新，逐份重算 `sha256[:16]` 与台账里的值比。

```
LANDED 文件数           7  (87106d8a, b01, b02, b03, b04, b05, b06)
按 mtime 最新          LANDED-b06.json
  ts                   2026-10-25T07:46:09Z
  sample_gap_s         32
  samples_identical    true
  记录文件数           8  （含 land.py 自己）
该台账与采样时文件的差   3 份
  m4c_selfcheck.py     fece7dd7740d2677 -> 44c2b43c34775bfe
  run_site3.py         f374a96b902aa843 -> 805482eab7236d41
  redcheck_delete.py   dc4e93602d7b6e5d -> bc832c82449f16a7
chat.py 里 chat.attach  3 处
```

**⇒ 三处要求过的都已落地**：`sample_gap_s`、`samples_identical`、`land.py` 记自己。
**⇒ 所以 `land.py` 现在会自己告诉你它过期了 —— 上面那 3 份不符，没有任何人记得，是比出来的。**

### 10.2 「已经有一个有效台账」是最容易误读的一句

**采样时最新是 `b06`，而 `b06` 已经与 3 份文件不符。**
**⇒ 任何「最新台账可用」的判断都必须当场重算，不能从文件名或 mtime 推。**
**⇒ `b01` … `b06` 这六份的存在说明：台账会被反复重出，而每一次重出都让上一份变成史料 —— 这正是它该有的样子。**

### 10.3 新会话的第一件事（顺序不许换）

1. **重算**：取最新 `LANDED-*.json`（按 mtime），逐份比 `sha16`；不符的列出来
2. **若有任何不符 ⇒ 让 executor 产出新台账**（间隔 ≥30 秒采样两次、全部相同才产出），**不要拿旧台账跑**
3. **确认 §4.1 四处落地**：`chat.attach` 的两处 `_event` + 三条件自检 + `attaches_done` 期望 `>= 1`
4. **再跑六臂**（§4.4 的命令，签名已贴）

**⇒ 若 executor 说「我已经做完了」，要它给台账，不是给文字。**
**⇒ 若它说「台账在，都在」，仍然重算 —— 本节就是重算之后写的。**

### 10.4 顺带记下的卫生问题（不影响判定）

```
TMP_LEFTOVERS  4 个 .tmp 残留（kvmem/m4c_leases/out/）
PYCACHE_DIRS   13 个 __pycache__ 目录（全仓）
```

**⇒ 都不影响六跑读数，属于清理项。**