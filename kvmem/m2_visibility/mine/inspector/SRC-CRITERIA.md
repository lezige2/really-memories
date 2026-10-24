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