# 判据 · 源文本的权威副本（MD §9.1 阻塞缺口 #7）

冻结：2026-10-25，**Stage 1 之前**。此后只许追加（R1…），不许改条文后直接套用。
验收人：inspector。写法由我定；方向由 lead 给（三条硬要求已收编为 C1/C2/C3）。

## 0 现状（我核过的事实，作为判据依据；不是转述）

- tools/chat.py:57-68 是 **MEMORIES 字面量**（profile / project 两段），:112 用 put_source 把它落库。
- kvmem/chat.db.memory_source 已有 2 行，**source_hash = sha256(text) 已 MATCH**（我重算过：d3e57f11838e6bf8 / aa9769adb3cb4493）。
  ⇒ 形状已经在，缺的不是「建库」，是「唯一性 + 消费方全覆盖 + 可校验」。
- kvmem/m2_visibility/m4/_m5db/m5_m4_blocks.db 的 blocks.text_origin = 「m4.memory_source.text」——是一句**字面表达式**，不是 (id, sha) 对，无法校验。
- m4 库 memory_source.text 的来源是 m4_verify.py:24 等**代码字面量**，同一段会话在 m4_verify / m4_ablate / m4_crosscheck / m4_pos0_refuse / m4_write 各存一份。
- 主档案/项目文本在工具侧另有**至少 4 份字节不同的平行版本**：tools/diag_place.py:28、tools/eval_heldout.py:44、tools/eval_retrieval.py:35、tools/kvdrift.py:32。
  例：eval_heldout 写的是「我叫林知远，工号 A-4417，在供应链分析组工作，猫叫年糕。」——与权威两行**字节不同**。
- **结论**：#7 的真实形态不是「没有库」，而是「库存在，但权威链末端是代码字面量，且同一事实在工具侧有多个字节不同的平行版本」。

## 1 不变量（不可协商）

- **I1 唯一副本**：一条源的 text 全仓库只存 1 份（库里那行）。其它出现必须是**引用**（id + sha）或**显式 fixture**（带与注册表比对的 sha 断言）。
- **I2 可校验**：读取时重算 sha256(text) 与 source_hash 比对，不等即**显式失败**。不许「警告后继续」。
- **I3 只读消费**：消费者只读源文本，永不回写（与块文件同一条纪律）。
- **I4 缺源必须显式**：缺失或校验失败 ⇒ 抛错，或降级为 **undecidable**。**绝不允许空串当源**，绝不允许 supported。
- **I5 身份稳定**：一条源 = 一个 id；name 唯一且不复用；改名不新增行（否则指它的块全体孤儿）。
- **I6 禁止用字符串表达来源**：provenance 必须是 (source_id, sha256)；不许是 module.attr 或「m4.memory_source.text」这种字面表达式。

## 2 权威源库规格

表 source：id INTEGER PK ｜ name TEXT UNIQUE NOT NULL ｜ label TEXT ｜ text TEXT NOT NULL ｜ sha256 TEXT NOT NULL（CHECK 长度 64）｜ created_at。
- 写入：put_source(name, label, text) **幂等**——同 name 同 sha ⇒ 不新增行；同 name **不同 sha ⇒ 拒绝**，要求显式建新版本。
  （**不许静默覆盖**：静默改源会让所有指它的块悄悄分家，这是最隐蔽的一种失真。）
- 读取：get_source(name|id) 内含 I2 校验；另提供 get_source_or_fail 供消费方使用。
- 删除：仍被块引用时**拒绝**（与 BlockLeases 同一条纪律）。
- 变更：text 改动 ⇒ 新 id 或显式 version；旧块标 stale，**不许直接改 text 后当没事**。

## 3 消费方读法（C1-C3 是 lead 三条；C4-C6 我补）

- **C1 两段链都要对**：注册表行 → block.source_text → M5 源侧 profile，**任何一段 sha 不等 ⇒ 显式失败**。
  只断言「M5 源 == 挂载块源」不够——那只证明两者同源，不证明它们来自权威副本。
- **C2 缺源 ⇒ undecidable，绝不 supported**（与 R13-C② 同源：拿不到权威源时，任何「源里有」的判定都是编造）。
- **C3 M4 的 evidence_span 必须能在注册表文本里定位**：span 落在 text 内**且切片逐字相等**；不得只与自身副本自洽。
- **C4 M4 memory_source 是分段派生层**：每行必须带 registry_source_id，且断言行文本是注册表文本的**逐字子串**；注册表变了而派生层没重建 ⇒ 必须报 **stale**。
- **C5 工具侧字面量退场**：diag_place / eval_heldout / eval_retrieval / kvdrift 的平行文本，要么改读注册表，
  要么保留为 fixture 但**必须断言其 sha 与注册表一致**；**字节不一致的不许悄悄统一**，必须逐条列出决策（canonicalize / 标 fixture-variant 并记录差异）。
- **C6 text_origin 改写**：现值「m4.memory_source.text」属 I6 违例，必须改成 registry:name@sha16 形状，且能被解析回查注册表。
  它是**溯源字段**，改动必须在 diff 里显式声明。

## 4 (a) 两层合不合并 —— 裁决：**不合并**，但规定权威方向

- 层 1：**全局权威源注册表**（事实文本的唯一副本）。
- 层 2：**M4 项目级 memory_source**（段级行 + 句级行）＝ 层 1 文本的**分段派生**，不是第二个源。
- 规则：层 2 每行 registry_source_id 非空 + 子串断言（C4）；**层 2 不得出现层 1 没有的文本**（出现即等于第二种源）。
- 理由：合并会把「分段/切片」这件实现细节塞进注册表，让注册表变成 M4 的内脏；而不合并只要把方向写死，就不会长出两个源。
  这与 R13-C② 是同一条纪律：**派生数据不得冒充源**。

## 5 (b) 纯重构还是判据变更 —— 裁决：分阶段，不同结论

- **Stage 1**（建表 + 双写一致性断言，消费方一行不改）：**纯重构**。
  口径：chat.db 两行 source_hash 迁移前后**字节不变** + 既有三问答案 sha 不变（852a5e5e / dacdc1a8 / 46272e43）。
- **Stage 2**（chat.py 改读库）：**纯重构**。唯一真回归 = M2 51 格三问答案 sha **逐字节一致** + 几何 51 / [4045,4096) / gap 0（不用单测替代）。
- **Stage 3**（M5 改读库）：**重构，但必须判据级回归** = 22 行对照表 after **全部等于现版**；任一行变化 ⇒ 视为**判据变更**，停下重新冻结。
- **C5 的 4 个字节不同变体不属重构**：把它们改成注册表文本会改变工具行为与历史结果，**是判据变更**，必须逐条评审，Stage 1-3 不许夹带。

## 6 验收条件（可判形式）

- **S1-1** 表结构 + name 唯一 + sha256 长度 64；put_source 幂等可断言：同 name 同 sha ⇒ 行数不变；同 name 不同 sha ⇒ **被拒**（错误类型可断言）。
- **S1-2** 迁移不改字节：注册表 vs 现有 chat.db 两行 source_hash 相等（d3e57f11… / aa9769ad…）。
- **S1-3** 读取校验可触发：手改坏 1 个字节 ⇒ get_source **必须抛错**（不是返回旧值、不是警告）。
- **S2-1** M2 回归：三问 sha 852a5e5e / dacdc1a8 / 46272e43 逐字节同，几何 51 / [4045,4096) / gap 0。
- **S2-2** chat.py 里 MEMORIES 元组**不得再含 text**（grep 断言）；保留 name/label 或整体删除。
- **S3-1** M5 22 行 after==before（含 product 四例）。
- **S3-2** 两段链断言：注册表 sha == block.source_text sha == M5 profile 所用文本 sha。
- **S3-3** 缺源负向测试：删掉/改坏注册表那行 ⇒ 该问必须 **undecidable**（不许 supported、不许空串 supported）。
- **S3-4** text_origin 形如 registry:name@sha16，可解析回查。
- **S4-1** C5 变体清单：每条给 (path:line, sha16, 与注册表是否相同, 决策)。
- **S5** 全部产物给 artifact | path | sha256前16 | mtime（沿用 anchor 规则，重跑即失效）。

## 7 反例清单（写给实现者：这些「看起来完成」的形态一律不算）

- 「库里有这行」≠「消费方读的是它」。必须有**改坏注册表 → 消费方报错/降级**的负向测试（S1-3 / S3-3），否则就是 M3 那次的翻版（护栏就绪、无人接入）。
- 不许 try/except 包住校验后继续 —— 那是把 I2 变成装饰。
- 不许在测试里把 chat.py 的字面量喂给 M5 —— 那正是本轮要消灭的形态。
- 不许用「两张表都在、都对得上」代替「只有一份」：**唯一副本**是 I1，两条一致不等于一条。

## 8 R15 · conversation 源不得作 M5 源侧（冻结：2026-10-25，1b 之前）

**R15-a 规则（lead 定，我原文冻结）**
- 层 1 增两个**结构性**字段：`text_kind`（`human_memory` | `conversation`）与 `contains_model_turns`（0/1）。
  profile / project = `human_memory` / 0；conv_2026-10-25 = `conversation` / 1。`resolve_origin` 反查必须一并返回 `text_kind`。
- **`text_kind=conversation` 的源只能用于证明「块正文来自何处」（text_origin 回查），绝不得作为 M5 的源侧。**
  M5 源侧只接受 `text_kind=human_memory`。
- 理由（同 R13-C② 同一条病，从「解析值」换成「模型发言」）：对话记录含模型回合，
  若它当 M5 源，模型先前一句「记住了」甚至一句编造都会被当成「源里有」==> **拿自己的产出当接地依据**。
- **安全方向（写死，防止以后被人当缺陷来"修"）**：M5 源侧只取人类发言 ⇒ 有些人类发言不会进 M5 源 ⇒ 相关提问变 `undecidable`（弃答）。
  按 §5「漏判优先于误判」这是**安全方向，有意为之，不是缺陷**。
- 事实依据（我 dump 的）：主块 `blk_conv_2026-10-25_01` 9 行，其中 **2 行是模型回合**（第 1 行「你好！有什么可以帮你？」、第 5 行「记住了。」），其余 7 行为用户。

**R15-b M5 源侧到底是什么（我补，必须有定义，否则 1b 无法实现）**

R15-a 只说"conv 不得作 M5 源"，但没说"那 M5 源是什么"。三种可能，后果完全不同：

- **(a) 人类回合子集（role=user 的行）**：等于把 conv 切一半继续当源。**我否**——它仍是"块正文"的切片，不是可校验的源条目，且无法署名。
- **(b) 人类回合**入库为**摘录行**：层 1 增 `text_kind=human_memory` + `is_excerpt=1` + `derived_from=<conv name>@<sha16>`，
  并要求其 text 是 conv text 的**逐字子串**（断言）。M5 源侧 = 层 1 的 `human_memory` 行（含摘录）。**我裁定：取 (b)。**
- **(c) conv 一律不作源、也不建摘录** ⇒ M4 产品路径**没有**合法 M5 源 ⇒ 每一个硬事实都只能 `undecidable`。

**为什么必须现在定 (b)**：若取 (c)，`plate_main` 会从 `supported` 翻成 `undecidable` ⇒ **我上轮给的「M5 产品可用：通过」当场失效**。
这不是反对 (c) 的理由，而是说**这个选择必须显式做、写进判据**，不许在 1b 里悄悄漂过去。
我选 (b)：它既满足 R15-a（conv 不作源），又让可校验的人类事实有署名条目，且摘录带 `derived_from` + 逐字子串断言，符合 §4「派生数据不得冒充源」。

**R15-c 由此对 I1 的精确化（必要，否则 (b) 会与 I1 冲突）**
- I1 的原话「一条源的 text 全仓库只存 1 份」对**段落级源**成立；**摘录行允许与其容器共享字节**，但必须同时满足：
  ① `is_excerpt=1` 且 `derived_from` 非空；② text 是容器 text 的逐字子串（断言）；③ `assert_unique_texts` **不得**把摘录当作容器的重复副本（判重只在同 `text_kind` 且同 `is_excerpt` 层内做）。

## 9 D2 · `declared_synthetic` 必须显式可见（冻结）
- 消融库文本是"删掉一句"的编辑文本，不是原话 ⇒ **不注册**，标 `declared_synthetic`。正确，我认。
- **凡报告 origin 的地方**（`_m5db.text_origin`、bridge 输出、任何对照表/run json），`declared_synthetic` 必须**显式可见**：
  不许留空，不许写成普通名字，必须是可 grep 的字面标记（例如 `declared_synthetic:blk_conv_noplate_2026-10-25_01@<sha16>`）。
  否则读报告的人会误以为它也过了权威链。

## 10 1b 重验清单（C4-a~C4-e 基础上加 lead 四条 + 我两条）

| # | 判据 | 形态 |
|---|---|---|
| C4-f | 层 1 每行 `text_kind` 非空且取值合法（conv=conversation、profile/project=human_memory） | SQL 全表断言 |
| C4-g | `assert_m5_source_allowed` 对 conv **必须抛错**、对 profile **必须通过** | 两条实测输出（异常类型 + 返回） |
| C4-h | `resolve_origin` 返回含 `text_kind` | 实际反查输出 |
| C4-i | 负向两条：注册表 hash 变 => `Stale`；外来文本 => `ForeignText` | 两条实测输出 |
| C4-j（我补） | 摘录行（若采 R15-b）`is_excerpt=1` + `derived_from` 非空 + 逐字子串断言；`assert_unique_texts` 不误判为重复 | SQL + 断言 |
| C4-k（我补） | **调用点清单**：`assert_m5_source_allowed` 现在被哪些路径调用、Stage 3 将接哪些，用 grep 列出； |
| | 并加一条机器断言 —— **M5 取源必须经过它**（Stage 3 前允许 TODO，但 grep 测试要能证明"没有旁路"） | grep 输出 + 断言 |

**为什么 C4-k 是硬条件**：`assert_m5_source_allowed` 若无任何真实调用点，就是 §7 反例①「库里有这行 ≠ 消费方读的是它」的第三次重演 ——
本轮已经因为它逼出两次真问题（`get_source` 抛错的位置、`assert_m5_source_allowed` 的存在性），不能再让它第三次只存在于单元测试里。

### 8.1 R15-d · 角色是**声明**，不是从文本读出来的（冻结：2026-10-25，1b 之前）

**事实（我 dump 的）**：容器 `conv_2026-10-25` 9 行 / 127 字符 / `sha16 = d8c094c1f5fcb8f1`；
逐行长度 L1-L9 = 4 / 11 / 21 / 23 / 13 / 4 / 9 / 8 / 26；
**文本里没有任何角色标记**（行首无「用户/助手/User/Assistant/U/A」，也无短冒号前缀，正则实测 False）。
⇒ 「谁是用户」不是抽取出来的，是**一条声明**；声明错了摘录就错了，而摘录错了**没有任何字节层面的东西会报错**。

**R15-d 三条（lead 定）+ 我补两条**

- **① 显式枚举入库**：摘录集以 `(container_name, container_sha16, line_index, line_text, role)` **五元组**存进数据，不许用推断重算。
  **我加的关键点**：枚举**必须绑定 container_sha16** —— 纯行号索引脱离版本就是定时炸弹（容器改一行，`[3,4,5]` 会静默指到别的句子，且看着一切正常）。
- **② 声明可审**：`roles_declared=true` + 记录枚举来源（谁 / 何时 / 依据「对话上下文」）。
  **我加的硬断言**：每行必须 `line_text == container_text.split(换行)[line_index-1]` **逐字节相等**，不等立即报错；不许"取最近的"、不许跳过。
- **③ 确定性**：同一容器 + 同一枚举 ⇒ 同一组摘录与同一组 sha；跑两次断言相同；枚举**按行号升序规范化**，避免 sha 随书写顺序漂。
- **④（我补）角色只是准入闸门，不是内容过滤器**：`role` 仅决定"该行能否作 M5 源"，**不得用于任何内容判断** ——
  不许出现「人类行里的日期算、助手行里的日期不算」这类不可解释的规则。
- **⑤（我补）声明错误的曝光度必须可见**：报告里固定给出四元组 `(user 行数, assistant 行数, 被摘录覆盖的行数, 未覆盖的人类行数)`。
  当前实测：user 7 行中 **4 行**被覆盖（L3/L4/L5/L9），**3 行未覆盖**（L1「你好呀！」、L7「帮我查下明天天气。」、L8「谢谢，就这样吧。」）。
  ⇒ 与那 3 行相关的问题命中不了 ⇒ `undecidable`（弃答）。这是 R15-a 安全方向的**必然结果，不是缺陷**，但必须在交付里写明，否则以后会被当 bug "修"掉。

**我核定的枚举（与 lead 一致，1-based）**：`user = [1,3,4,5,7,8,9]`、`assistant = [2,6]`。
逐行原文我已核对（见上表长度），与 lead 给的完全一致；若执行者的枚举与此不同，**以容器原文裁决**，不许两说并存。

**既有 4 条 fact 的溯源（我验的，作为枚举正确性的旁证）**

| fact 行 | 落在行 | 是否用户行 | 是否容器子串 |
|---|---|---|---|
| fact_住址_2（21） | L3 | 是 | 是 |
| fact_作息_3（23） | L4 | 是 | 是 |
| fact_车牌_4（13） | L5 | 是 | 是 |
| fact_家庭成员_5（26） | L9 | 是 | 是 |

⇒ **没有任何现存 fact 来自助手行**，D4 过滤此前的行为是对的。但请注意：这也说明**枚举标错的后果目前是隐性的**
（今天把 L2 标成 user 也不会改变任何结果，因为 L2 没有事实）—— 所以 R15-d 的 ① ② 不是形式主义，
它防的是**将来**某条助手发言里恰好含一个硬事实时，被静默当成人类记忆存进层 1。

**R15-e 容器版本变更的处理（lead §5 的加严，我落成条文）**
- 容器 text **任何字节变化** ⇒ 该容器的枚举**整体失效**：必须重新声明角色并重建摘录行，旧摘录行标 stale（不许沿用行号）。
- 层 1 的 profile / project / conv 三行是 M2/M3/M4/M5 各链的源：**任一行 text 变字节 ⇒ 相关验收结论按锚规则宣布失效并重验**，
  不许只报「ALTER 加了字段」。当前容器版本锚：`conv_2026-10-25 @ d8c094c1f5fcb8f1`（127 字符 / 9 行）。

**R15-f 跨层可见性检查（lead §3 的加严，我落成条文）**
- 分层判重之后，必须保留一条**跨层可追溯**断言：每条摘录行的 `derived_from` 非空、且其 text 是容器 text 的**逐字子串**；
  否则「分层判重」会退化成「看不见的重复」——两条一样的内容，因为分层太干净而谁也追不到谁。

### 8.2 R15-g/H · 声明的可推翻性 + 「覆盖」与「可检索」必须分开数（冻结：2026-10-25，1b 之前）

**口径裁决（lead 定 A，我原文收编并落成可判形式）**
- **层 1 摘录（源侧）= 全部人类回合（7 行）** —— 它决定「一句话能不能支撑答案」。
- **层 2 事实 + 检索索引（4 条）** —— 它决定「一个问题能不能被命中」。
- ⇒ 报告固定给**五元组**：`(user 行数=7, assistant 行数=2, 层1 摘录行数=7, 被层2事实覆盖的行数=4, 可检索事实数=4)`。
- 并必须写明一句：**未覆盖的 L1「你好呀！」/ L7「帮我查下明天天气。」/ L8「谢谢，就这样吧。」是「不可检索」，不是「不可支撑」。**
  这两件事一旦混用，就会长出两种错误：「明明是人类说的却 undecidable」被当实现 bug；「undecidable」被当源缺失来"修"。
- **派生纪律**：报告里不得把「未被覆盖」写成「缺失源」「无源」；不可检索只报 `retrieval_miss`，源缺失只报 `source_missing`。

**R15-g 角色声明必须可被推翻（lead 定，我落成条文）**
- 若发现某行角色标错：**改声明 ⇒ 该容器的摘录集整体失效并重建**（与 R15-e 同等处理）。
- 必须留四元组记录：`(旧声明 sha16, 新声明 sha16, 原因, 时间)`，以及旧摘录行的处置（标 stale 或删除，二者明示其一）。
- **禁止就地 `UPDATE role` 字段了事** —— 那样「声明」与「摘录」之间会出现**无记录的错位**：
  声明说这行是助手，摘录却还留着它当源，而库层面没有任何东西会报错。这与今晚反复出现的静默变更（静默覆盖源、静默改行号）是同一条病。
- 机器可判形式：声明变更后，`assert_unique_texts` 与跨层可追溯断言（R15-f）必须对**新旧两份摘录**都能给出确定的结论（旧的 stale、新的通过），不许两者都"看起来正常"。

**§8.2-a 附记（数据之后追加）：我实测了「源侧从 9 行缩到 7 行」是否改变裁决 —— 结论是不改变，且这是可复算的**

我在 `m5_ground.source_profile()` 上直接对照两种入参（`[conv 全文]` vs `[7 条人类行]`）：

| 键 | 全文源 | 人类行源 | 是否相同 |
|---|---|---|---|
| `latin` | 2 | 2 | **同**（B3F19K / 浙B3F19K）|
| `plate` | 1 | 1 | **同**（浙B3F19K）|
| `nums` | — | — | **同** |
| `dates` | 0 | 0 | **同** |
| `props` | 2 | 2 | **同** |
| `blob` | 114 字符 | 99 字符 | **不同**：恰好少了那 2 条助手行 |

答案侧 A 族命中（`extract` + `a_hit` 实测）：`浙B-3F19K` 在两种源下**都命中**；`苏B-3F19K` 在两种源下**都不命中**（判别位不受影响）。
`blob` 侧：`记住了` 在全文源**在**、在人类行源**不在** —— 这正是 R15-a 要的效果（模型自己那行不得成为接地依据）。

⇒ **预测（供 Stage 3 对照）**：按 A 读法把 M5 源侧切换到层 1 人类摘录，对现有 4 个产品用例与 (a)/(c) 探针**裁决全部不变**，`plate_main` 仍 `supported`。
若 Stage 3 实测出现任何一处变化，说明切换引入了别的路径（不是"源缩小"导致的），按判据变更处理并停下重新冻结。

## 11 I7 · 总纪律「两处各存一半真相，就必须有不一致即报错的断言」（冻结：2026-10-25）

lead 合并出的总纪律，我收编为不变量，并**落成可核清单**（光有原则没用，每对必须有具体的断言字面）。

| # | 两处各存一半真相 | 必须存在的断言 | 现状 |
|---|---|---|---|
| 1 | 库触发器 vs API 写入路径 | `UPDATE memory_source SET text` 必须被拒（触发器）+ `put_source` 拒隐式修订 | **已有**（我实测：IntegrityError / SourceConflict）|
| 2 | 层 1 权威源 vs 层 2 派生表 | `registry_source_id` 非空 + 逐字子串断言 + 注册表变更未重建 ⇒ `Stale` | 1b 待建（C4-a~C4-e）|
| 3 | 角色声明 vs 摘录行 | 五元组逐字节断言（`line_text == split[line_index-1]`）+ 声明变更整体失效 | 1b 待建（R15-d/R15-g）|
| 4 | `text_origin` 字面 vs 实际来源 | 必须是 `registry:name@sha16` 且能解析回查 | 1b/Stage 3 待建（C4-h/S3-4）|
| 5 | 验收锚 vs 产物 | 验收方重算 + 重跑即失效 + (old,new,原因,时间) 四元 | **已有**（本轮已三次兑现）|

**判据要求**：上表任一行若在交付时"待建"，该阶段不得判定为通过；已被 1b 声明为待建的，必须在同一次交付里给出断言字面（不是计划）。

### 11.1 附记（数据之后追加）：④「消失的 key 来自哪一行」—— 当前语料实测为**零丢失**，附逐行归属表

lead 加严④：逐键前后对照之外，还要标出**每个消失的 key 来自哪一行、该行角色是什么**。我按要求做了逐行归属（每行单独跑 `source_profile`）：

| 行 | 角色 | 贡献 key 数 | 具体 key |
|---|---|---|---|
| L1 你好呀！ | user | 0 | — |
| L2 你好！有什么可以帮你？ | **assistant** | **0** | — |
| L3 我住在广陵路 12 号 2 单元 602。 | user | 4 | nums 12/2/602、props 广陵路 |
| L4 我每天早上七点半出门… | user | 0 | — |
| L5 我车牌是浙B-3F19K。 | user | 5 | latin B3F19K/浙B3F19K、plate 浙B3F19K、nums 19/3 |
| L6 记住了。 | **assistant** | **0** | — |
| L7 帮我查下明天天气。 | user | 0 | — |
| L8 谢谢，就这样吧。 | user | 0 | — |
| L9 对了，我女儿小名叫豆豆… | user | 1 | props 豆豆 |

**结论（可复算）**：两条 assistant 行贡献 **0 个 key** ⇒ 切源时 `latin / plate / nums / dates / props` 的**丢失键集全为空**。
所以 ④ 这条要求对当前语料**已经满足，且是零丢失**，不是"将来要小心"。
对**将来**的语料，④ 的可判形式定为：交付必须给出 `lost_keys = {key: (line_index, role)}` 映射（为空也要显式给空表），
并且**任何一个 lost key 的 role 是 user 时，必须停下**——那是"该有的被漏掉了"，不是"该少的"；只有 role=assistant 的丢失才是 R15-a 的预期效果。

### 11.2 I8 · 保护性字段的默认值必须等于拒绝态（冻结：2026-10-25，由 1b 缺陷 1 导出）

- **规则**：任何决定"是否放行"的字段，其 SQL 默认值必须等于**拒绝态**，而不是宽松态。
- **本例**：`text_kind` 默认值曾是 `human_memory`（放行态）⇒ 忘记写该列的行会被 M5 当合法源。应改为 `conversation`（拒绝态）+ `CHECK (text_kind IN ('human_memory','conversation'))`。
- **可判形式**：一条**只用老列**的 INSERT（不写 text_kind）⇒ 读回必须是拒绝态。这条测试必须存在，否则"改好了"无法验收。
- **推广**：凡"漏写即放行"的字段都是同类缺陷。它比"写错"更危险，因为没有字节层报错，只有在事后被断言抓住（本例正是这样被抓住的）。

### 11.3 附记：1b 的静态扫描器值得保留

`registry/check_m5_gate.py` 扫 `m5 / m4 / tools` 三个面，对凡是出现 `chat.db|memory_source|registry_source_id|probe_text|get_source` 的文件，
要求该行**要么带闸门调用、要么带 `TODO(stage3)` 标记**（跳过注释行与 def 行、跳过 `_before/_test/_ablate/_m5db`）。
这是"无旁路"的**可执行**形式，比 grep 数调用点强：它在 Stage 3 新增读源代码时会直接报出来。
但它只证明"每个读源点都被标记过"，**不证明闸门真的会拦** —— 所以 C4-g 的实测（conv 抛错）不能省。

### 11.4 I8-b · 相邻那一列：默认值方向 + **闸门根本没读它** + 强相关的正确形式（冻结：2026-10-25）

**lead 指出的第二处**：`contains_model_turns INTEGER NOT NULL DEFAULT 0` —— 漏写得到「不含模型回合」，同一条病。
我核了建表 sql：**CHECK 为 False**（`text_kind` 与 `contains_model_turns` 都没有 CHECK），与我先前实测一致。

**我另发现一件更要紧的**（比默认值更直接）：`assert_m5_source_allowed` 的实现**只判 `text_kind`**：
```
if kind != "human_memory": raise SourceNotAllowed(...)   # turns 只被拼进报错文案
```
⇒ 一行 `text_kind=human_memory` + `contains_model_turns=1` 会**通过闸门**。也就是说这一列目前是**装饰性的**，
它被写进返回值、写进报错消息，却**没有任何一处用它做决定**。这属于 I7「两处各存一半真相」——现在是"一存一存却互不校验"。

**lead 给的二选一我都不取，理由如下（这是我与 lead 唯一的判断分歧，请裁决时看理由）**

- **不取 (A) 纯派生（把该列删掉、由 `text_kind` 推）**：因为 `conversation ⇒ contains_model_turns=1` **不成立**。
  一份纯人类发言的会话记录，`text_kind=conversation` 而 `contains_model_turns=0` 是**合法事实**；
  强行派生会让这一类被错标成"含模型回合" —— 对闸门而言是安全方向（都要排除），但它把这个字段变成永远的真值替身，
  以后再有人拿它做别的事（比如报告里"这段对话是否含模型发言"）就会得到假值。**用一个假字段换掉两个可能不一致的字段，不是修好。**
- **不取 (B) 双向 CHECK（`conversation ⇒ turns=1`）**：同上，会禁止一行合法数据。
- **取 (C)：方向一，默认值翻向拒绝态，闸门三条件并列。** 三条一起，才能同时满足"单一真相""fail-closed""不放行假人类记忆"：

**I8-b 条文**

1. **默认值各自 fail-closed**：`text_kind DEFAULT 'conversation'`；`contains_model_turns DEFAULT 1`。
   （漏写 ⇒ `conversation` / `1` = 双重拒绝态；而今天的默认是 `human_memory` / `0` = 双重放行态，两个方向全错。）
2. **只加逻辑成立的那个方向约束**：`CHECK (NOT (text_kind = 'human_memory' AND contains_model_turns = 1))`。
   即「含模型回合的文本，绝不能被声明为人类记忆」——这一条是我们真正要防的；反方向（纯人类会话 turns=0）必须允许。
3. **闸门必须并列判三项**：`text_kind == 'human_memory'` **且** `contains_model_turns == 0` **且**（若 `is_excerpt=1`）`derived_from` 非空且逐字子串成立。
   任一项不满足 ⇒ `SourceNotAllowed`。当前实现只判第 1 项，**必须补齐后两项**。
4. **可判证据三条**（缺一不算关闭）：
   - (i) 只用老列的 INSERT（不写这两列）⇒ 读回 `conversation` / `1`；
   - (ii) 人造一行 `human_memory` + `1` ⇒ **被 CHECK 拒**（若实现选触发器/应用层，则必须在该路径上被拒并给出异常类型）；
   - (iii) 人造一行 `human_memory` + `1`（绕过 CHECK 直接改副本库）⇒ **闸门必须抛 `SourceNotAllowed`** ——
     这条证明"闸门读了这个列"，比任何默认值都更能说明它不再是装饰。

**若执行者坚持 (A)**：那也只能从**角色声明**派生（`assistant_lines` 非空 ⇒ 1），不能从 `text_kind` 派生；
并且必须同时给出「纯人类会话」这条反例的往返测试（`conversation` + `0` 仍可如实表达）。否则我不接受 (A)。

## 12 Stage 3 判据冻结（2026-10-25；冻结后任何改动都算判据变更，须重审）

依据：lead 批准的方案 v2 + lead 的三条收紧 + S3-1..S3-8 + 我 MC 的实测。
凡标注「我实测」的，都是我自己跑出来的原值，不是转述。

### 12.0 D3-0 · 两个长度是**两个量**，禁止互相比较

- 标签固定为 `source_text_len` 与 `profile_blob_len`；一句话里只许出现其一。
- 禁止写法：「从 127 变成 99」（跨量拼接会把两条独立事实说成一次回归）。
- 我实测（`source_profile([text])`，注意**必须传列表**）：`source_text_len` 127 -> 110；`profile_blob_len` 114 -> 99。
- 我实测五族 keys：latin 2/2、plate 1/1（浙B3F19K）、nums 5/5（12,19,2,3,602）、dates 0/0、props 2/2（广陵路,豆豆）；lost=[]、gained=[]。

**附一条自纠（我的第六个同类错误，记入纪律第五条）**：我第一次调用 `source_profile(cont)` 时传了字符串而不是列表，
函数内部 `for t in texts` 于是**逐字符**遍历，得到 latin 0/0、plate 0/0、props 0/0 的废数；SAME 结论侥幸成立，但数字全错。
=> 纪律第五条：**参数形态也属于「原值」**。报告计数/集合时，必须连调用形态一起给出，否则等于没给。

### 12.1 S3-1 · 追溯改为行级（我实测支持）

- 我实测：`joined in container` = **False**；7 行逐行 `in container` = **True**（行号 1,3,4,5,7,8,9）。
- 因此追溯单位 = `(line_index, line_sha256)`，7 对全命中；「源文本是容器逐字子串」这句话**只对单行成立**。
- **Stage 3 内必须存在一条期望负向断言**：`assert joined not in container_text`，并注明「跳过 L2/L6 是有意的；
  将来谁把它修成连续子串，等于把两条 assistant 行拉回源侧」。没有这条，下一个人会当 bug 修掉。
- 禁止：偏移定位（用 index/位置描述行）、拿 joined 的 sha 去比容器 sha。

### 12.2 S3-2 · origin 解析器唯一实现 + 语法冻结（含 lead 收紧一、二）

**语法**（三段，两处 `@`、一处 `#`）：
`<kind>:<container>@<container_sha16>#<L 行号表>@<joined_sha256>`

- **唯一实现**：`format_origin()` 与 `parse_origin()` 必须是同一文件里**相邻的**一对，writer 只准调 format，reader 只准调 parse；
  禁止「写时格式化、读时正则」两套。冻结时把两者的 `file:line` 记进验收。
- **重组段只接受 64 hex，拒绝 16**（这类 origin 形态是全新的，没有 legacy 需要兼容；接受 16 等于「任意 16 字符前缀相同即过」）。
  容器段仍是 16（它只是版本标识，强度由块侧 sha 与行 sha 兜底）。
- **行集顺序敏感**：比序列不比集合。必须同时满足 ① 升序 ② 互异 ③ 全在容器行号范围内 ④ `joined.split(换行)` 长度 == len(行号表)
  ⑤ 第 i 段与容器第 idx 行**逐字节**相等 ⑥ 每段 sha256 与 `memory_source_excerpt.line_sha256` 相等。
- 反解还必须：⑦ 用容器 sha16 校验容器未变（R15-e，不符抛 `Stale`）；⑧ origin 的 joined 段 == 该块 `source_text` 的 sha256。
  第 ⑧ 条是我加的：否则 origin 可以指向一串和实际入块文本不同的东西，而两边都「自洽」。
- **负向三测**：`L5`->`L6` 改动（正则能匹配、校验必须失败）、行号顺序打乱（L9..L1）必须拒且报错指明**行集/顺序**不符、
  joined 段写 16 hex 必须拒。
- **触底实测**：我算得 `origin(16/64)` = **139 字符**（`origin(16/16)` 只有 91），与 lead 同值。
  必须有一条「完整落库、读回**逐字节**相等」的实测（不许 START 前缀、不许取前 300 —— 今晚已经出过一次截断）。

### 12.3 S3-3 · 闸门位置可 AST 定位

- 用 AST 定位 `ensure_db()` 函数体，闸门必须在**选源函数返回之前**；生产路径接入点 >= 1 且打印 `file:line`。
- `check_m5_gate.py` 里 TODO 允许名单必须清零（见 S3-4），否则「标记覆盖」会一直遮住「未接入」。

### 12.4 S3-4 · `no_todo_stage3` = 0

- 全树 `TODO(stage3)` 计数 **0**；`m5_bridge.py:86` 真删，且**它的说明文字要搬进注释/文档**，不是丢掉。

### 12.5 S3-5 · `synthetic` 绑死前缀 —— 但 lead 给的 CHECK 有一个 NULL 洞（我实测）

我实测 SQLite 行为（表带 `CHECK ((origin LIKE 声明合成前缀) = (synthetic = 1))`）：

    PASS (None, 0)      <- origin 为 NULL 放行
    PASS (None, 1)      <- origin 为 NULL 放行
    PASS (registry:x, 0)
    PASS (declared_synthetic:y, 1)
    REJECT (declared_synthetic:y, 0)
    REJECT (registry:x, 1)

⇒ **CHECK 表达式求值为 NULL 时视为通过**。origin 为 NULL 的行会同时绕过 D3-1 与「非空」要求（若非空只写在应用层）。
必须写成：`CHECK (origin IS NOT NULL AND ((origin LIKE 声明合成前缀) = (synthetic = 1)))`，另加 `CHECK (synthetic IN (0,1))`。
并加负向：**origin 为 NULL 必须被 CHECK 拒**（当前形式会放行）。
`plate_main.synthetic=0`、`plate_ablated.synthetic=1`（我实测 noplate 块现状：`source_text_len` 113、sha16 93332bde804698bc）。

### 12.6 S3-6 · 预登记表与两张空表

- 11 行预登记逐行相等（不是「大体一致」）；`lost_keys` 与 `gained_keys` **两张表都必须显式给出**，五族全列，空就写空。
- 只报 lost 不报 gained，会漏掉 R12 那类「切源后多出一个命中」的失败模式。
- M5 自带回归 `false_negative=0` 必须复跑并给原值。
- 基线（我实测，容器 vs joined）：五族全 SAME、lost/gained 均空 ⇒ 「切源后裁决不变」在 key 层已成立。

### 12.7 S3-7 · 两个哈希分开记；M5 必须重锚

- `_m5db` 的**文件 sha** 与**内容哈希**分别记录，内容哈希必须附四要素（序列化方式、列集合、顺序、编码），否则不可复算（`876deaa3` 的教训）。
- `run_m5_grounded.json` 一变 ⇒ **M5「通过」必须重新锚定**，结论以我的重算为准。
- 现状（我实测）：`blk_conv_2026-10-25_01.source_text` 目前是**容器全文**（`source_text_len` 127、sha16 d8c094c1f5fcb8f1、`== container` 为 True），
  Stage 3 要把它换成 joined（`source_text_len` 110、sha256 2b3b6662b883d117f885cb1f5e995b673b1fb8175c226ebd86be92e8c41fade4）
  ⇒ 块 `source_text`、`text_origin`、`_m5db` 文件 sha、内容哈希**四处都会变**。

### 12.8 S3-8 · 「chat.db 不变」是可证伪声明

- 跑完必须复算并给原值：`kvmem/chat.db` sha16、`memory_source` 行数（现 10）、`memory_source_excerpt` 行数（现 7）。
- 若有变化，必须给 `(old, new, reason, time)` 追加记录，不许只说「没变」。
- 已知前情：`chat.db` 曾因另一阶段写盘从 5909b978 漂到 6d2ff37a，**内容未变**；文件级漂移与内容漂移必须分开写。

### 12.9 D3-3 · 账本自检（Stage 2 遗留，Stage 3 前必须关）

- 自检必须按**来源表达式文本**去重，**不得按取值去重**（判据全为 true 时，按取值去重会把每一项都判成重复）。
- 必须同时打印 `key_count` 与 `independent_count`，两者不等即失败。
- **负向测试**：注入一个别名（形如 `99_alias`: 复用已有来源）⇒ 自检必须失败。没有这条负向，自检本身未经验证（I7：每个断言都要证明它会响）。
- 我今天实跑（证明可构造，且给出当下原值）：条目 **12**、独立来源 **11**、唯一重复组
  `no_second_copy_of_memory_text -> [8_fidelity, 13_no_second_copy_of_memory_text]`。

### 12.10 I7 新增两行（Stage 3 交付前不得「待建」）

- **行 6**：块上的 `text_origin`（声称的行集）vs 库里的 `memory_source_excerpt`（登记的行集）。
  断言：把 origin 反解出的行序列与 excerpt 表中该容器的行序列**按序逐项**比对，不一致即 raise。
- **行 7**：`synthetic` 列 vs origin 前缀。DB 层由 12.5 的 CHECK 承接，**应用层另需一条同样的断言**（双保险；单靠 CHECK 会在 origin 为 NULL 时被绕过）。

### 12.11 冻结之外的既有约束（复述，避免被骗）

- 不得重调 GATE 1.30 / COV_MIN 0.35；三值结论不合并成命中率；不新增 7B<>14B 数字对照；交付只取首句。
- 任何「通过」都必须带 `file = sha256 前 16`；重跑改 sha 即作废旧结论。

### 12.12 三条通则（2026-10-25 冻结，来自 0-a / 0-c / 账本自检三次撞击）

**通 1 · NULL 等于「约束没生效」，不等于「约束满足」**
- SQLite（以及任何三值逻辑）里，CHECK 表达式求值为 NULL 时**视为通过**。
- 实测证据：`CHECK ((origin LIKE 声明合成前缀) = (synthetic = 1))` 对 `(None,0)` 与 `(None,1)` 均 **PASS**。
- 规则：凡 CHECK 涉及「列 与 列」或「列 与 常量」比较，**必须显式排除 NULL**（`col IS NOT NULL AND (...)`）。
- 推论：任何"某列非空"的要求，**只写在应用层等于没写**；DB 层必须也有一份，且那份也要被负向测过。

**通 2 · 凡新增断言，必须同时给一条能让它失败的输入**
- 没有负向输入的断言，等于一段永不执行的代码；它不减少任何风险，只增加账本的行数。
- 这条同样适用于**自检本身**：账本自检（键数 vs 独立判据数）也必须有一条"注入别名 ⇒ 必须失败"的负向。
- 这是 I7 的推广：I7 管「两处各存一半真相」，本条管「一处根本没在管」。

**通 3 · 计数与度量必须附「调用形态」**
- 与「查询语句原文 + 返回值」「哈希附定义」并列：报一个数，必须同时给出**入参的类型与结构**。
- 实证：`source_profile(texts)` 收列表；传字符串会逐字符遍历 ⇒ `latin/plate/props` 全空，而**结论方向恰好不变**。
- 这类错误最难被抓：它错的是量的定义，不是结论的方向；任何只看结论的复核都会漏掉。

### 12.13 验收单格式要求（2026-10-25 冻结）

**格式 A · CHECK 与负向一一对号**
- 每一个 DB 层 CHECK（以及每一条触发型约束）必须在验收单里登记「哪条负向用例覆盖了它」。
- **缺号的 CHECK 视为未验**，不得计入通过项。理由：一条没人测过的 CHECK，与一句注释等价；
  而读者看到 CHECK 会以为它已经被验证过。
- 已存在的 CHECK 清单（`memory_source`）：合法值三连（text_kind / contains_model_turns / is_excerpt）、
  `NOT (text_kind=human_memory AND contains_model_turns=1)`、`is_excerpt=0 OR derived_from IS NOT NULL`；
  Stage 3 将新增 `origin IS NOT NULL AND ((origin LIKE 声明合成前缀) = (synthetic=1))` 与 `synthetic IN (0,1)`。
  每条都要有号。

**格式 B · 账本自检的两个数必须同时打印**
- `key_count` 与 `distinct_judgements` 同时输出，不等即失败；并附 `retired_keys` 清单（退役项不得计入键数）。

**通 4 · 不得比对「渲染出来的字符串」，只比对结构或取值**
- 实证（我在真实提交上抓到的红态）：`ledger_selfcheck` 用 `ast.unparse` 渲染来源表达式，输出 `res['x']['ok']`（**单引号**）；
  而负向断言里写死的是 `res["x"]["ok"]`（**双引号**）⇒ 断言恒假 ⇒ `14_ledger_selfcheck_catches_alias=False` ⇒ 整体 `pass=False`。
- 这不是笔误的孤例，是「两处各存一半真相」在**字符串格式化层**的复现：生产端负责渲染，消费端硬编码同一格式，
  两者一旦不同就是静默错位（此处恰好被断言抓住，因为它比的是精确相等）。
- 规则：凡比对由格式化函数/序列化函数产生的字符串，必须改为比对**结构或取值**（如 `list(dup.values()) == [[...]]`）。
  现已按此修正，并有注释说明原因 —— 该注释必须保留。

**附：这条红的正面价值**
- 它证明负向测试**在真实提交上确实能变红**，不只是在我构造的探针里。
- 记录：`14= False` 曾真实出现于 04:4x 的一次中间产物中，随后修正；修正前后我都独立复跑过 `ledger_selfcheck`。

