# M3 块生命周期验收 · **事先声明**（STATUS-REPORT §4.3）

**声明时刻**：2026-10-25 06:0x（`time.strftime` 打印值见下）；**我未见过任何一轮数据**，包括 lead 让执行者先跑的 3 轮 smoke。
```
**printed at write time**：2026-10-25 05:51:24（本文件由脚本写入，时刻由程序打印，不追记 —— 纪律 25）
```
**文档原判据（我不改它，只把它变可判）**：
> §4.3：**attach/detach 50 轮，`pos_max`、answer、cell 占用三者稳定，无单调上升。**

## 0 我独立算出的初值（不读任何人的报数）

`.kvmem` 头是 `qsgg` / ver 4，**offset 8 的 u32 就是 cell 数**；我自己读字节算的：

| 文件 | cells | 字节 |
|---|---|---|
| `m4/blocks/blk_conv_2026-10-25_01.kvmem` | **91** | 9,507,412 |
| `m4/_ablate/blocks/blk_conv_noplate_2026-10-25_01.kvmem` | **79** | 8,253,844 |
| `m4/blocks/pos0_A.kvmem` | **21** | 2,194,932 |

⇒ **本阶段所有判据里的界，用 `n_block = 91`**（不是「大约九十」）。若它报的数与 91 不同，**先查它**，不许调界。
（顺带：`pos0_A = 21 cells` 与 `m3_lease.py` 文档里「21 cells → 0」一致；`run_m4_write.json` 的 `encode.cells = 91` 也与我的字节读数一致 —— 两条独立路径同值。）

## 1 三条序列各自量什么（**在数据来之前**固定下来）

| 序列 | 量 | 取自 |
|---|---|---|
| `pos_max` | `P.raw_pos_max(eng, seq)` 逐轮读数 | **只用 raw**；`eng.pos_max` 对 seq_cp 建出来的序列返回 -1 |
| `answer` | 同题同 ask 位置的**完整字符串** | `kvshim_ask_at` 的返回 + rc |
| `cells` | `cell_scan(LIVE)[0]`（attach 中 / detach 后各一次）+ `cells_of(BLOCK_SEQ)` | `eng.n_tokens(seq)` |

轮内固定顺序（判据依赖这个顺序）：`reset(LIVE)` → `attach` → 记读数 → `ask` → `detach` → 记读数。

## 2 ① `pos_max` 稳定：三种形状里我选哪一种

**选「回到起点且逐轮相等」，不选「有界振荡」。**理由：本实验每轮都 detach 干净，位置理应被完整回收；
**允许振荡等于允许不回收**，而「不回收」正是要抓的东西。

**判定式（全部必须成立）**：
```
S1  每轮 detach 后 raw_pos_max(LIVE) == 第 1 轮 detach 后的值          （逐轮相等，不是「接近」）
S2  全程 max_t raw_pos_max(LIVE) <= init + 91                          （界=块自身 cells，事先固定）
S3  attach 期间 raw_pos_max(LIVE) - detach 后值 == 91                  （每轮都真的接上了 91 格）
```
**S3 是我加的**：只有 S1/S2 时，「attach 了什么也没接上」会让序列看起来完美稳定（今晚 74 分钟那次正是这样）。
**任何一轮读到 -1 ⇒ 无效轮（度量方式错），不是「稳定」。**

## 3 ② `answer` 在 50 轮里允许变吗

**不允许。**判两层，两层都写在这里，不做事后选择：
```
T1（必须）每轮答案【包含】记忆原文子串「广陵路 12 号 2 单元 602」
T2（必须）第 2..50 轮答案与第 1 轮【逐字节相等】
```
- T1 破 ⇒ **未通过（丢失记忆）**；
- T1 成立而 T2 破 ⇒ **未通过（答案不稳定）**，且必须记「哪几轮变、变成什么」；
- 答案为空串 或 rc != 0 ⇒ **无效轮**（不是未通过，也不是「答对」）。
**为什么 T2 要严格**：答案措辞变化通常意味着喂给模型的上下文变了（attach 的格数或位置不同）；把它当噪声抹掉，就等于**把位置错误洗成语言多样性**。

## 4 ③ `cell 占用` 的「无单调上升」判定式

```
C1  每轮 detach 后 cell_scan(LIVE)[0] == 第 1 轮 detach 后的值
C2  每轮 attach 中 cell_scan(LIVE)[0] - detach 后 == 91
C3  每轮开始与结束 cells_of(BLOCK_SEQ) == 91              （块自身一格都不许掉）
C4  不存在长度 >= 3 的连续轮窗口，使该窗口内 detach 后值逐个不减且总增 >= 1
C5  第 50 轮 detach 后值 == 第 1 轮 detach 后值            （末轮 vs 首轮）
```
**为什么用 C4（连续 k=3 不减）而不是斜率**：泄漏是**累积**的，斜率判据要先定一个「多大算上升」的阈值；
**阈值在这里没有先验来源**，定它就等于替数据选答案。C4 不需要阈值：**它只问「有没有连涨三轮且真涨了」**。
代价我写清楚：**C4 会漏掉「涨一次就停在高位」**，那一格由 C5 与 C1 兜（末轮≠首轮即红）。

## 5 ④ 泄漏：哪一项若上升就**必然**是泄漏

```
L1  detach 后 len(leases.holders[BLOCK_SEQ]) == 0        ；上升即泄漏（有人忘了还）
L2  detach 后 len(leases.ranges) == 0                    ；上升即泄漏（区间没还回去）
L3  detach 后 leases.status()['any_leased'] == False     ；为真即泄漏
L4  被 reset 的序列 n_tokens == 0                        ；若为 91，说明 reset 没真清（静默丢句柄的反面）
```
**这四条中任何一条上升/为真 ⇒ 判泄漏，与三条序列是否好看无关。**
因为它们是**引用计数**层面的量：它们错了，位置与答案的巧合正确不能作为豁免。

## 6 ⑤ 无效轮（必须作废重跑，不许计入 50）

```
I1  rc != 0  或  答案为空串
I2  ask 时 pos != raw_pos_max(eng, LIVE) + 1        （位置错则 rc=-1 且空串，见陷阱②）
I3  轮开始时 cells_of(BLOCK_SEQ) != 91              （块被清过，attach 会接 0 格）
I4  轮开始时 holders/ranges 非空                     （上一轮没还干净）
I5  读到 raw_pos_max == -1                           （度量方式错）
I6  本轮 attach 的区间长度 != 91
```
**无效轮不算「通过」，也不算「未通过」**：它只说明这一轮没资格参与判定。
**最终要求 50 个有效轮**；若为凑够 50 而重跑，必须保留「第几次尝试、哪几轮作废、为什么」的清单。

## 7 三个已知陷阱：各自变成一条断言，不是一条注意事项

| 陷阱 | 断言（写在轮内） | 它抓到的是 |
|---|---|---|
| ① `reset_all()` 清块槽位（今晚白跑 74 分钟）| **每轮轮首断言 `cells_of(BLOCK_SEQ) == 91`**，且驱动源码里 `reset_all` 出现次数必须为 0（`grep` 结果贴进产物）| 板上钉钉地当场红，而不是 50 轮后才发现全是空 attach |
| ② `ask` 静默失败（位置错 ⇒ rc=-1 + 空串）| **ask 前断言 `pos == raw_pos_max(LIVE)+1`**；空串一律 I1 | 「空答案被当成答对」 |
| ③ 20 次往返后数值会坏（L3b）| **真有 50 轮，逐轮原值入产物**，不许采样/不许均摊；轮次编号 1..50 齐全 | 「用代表性采样代替 50 轮」 |

**顺序必须是**：`eng.reset(LIVE)`（重置对话序列，**不动块**）；**绝不用** `reset_all()` / `safe_reset_all(seqs)` 含块序列。

## 8 能红的输入（红控），以及它的**顺序**

**红控 A（漏还）**：在**第 37 轮**（现在定死，不看数据再选）故意跳过 `detach`，第 38 轮照常继续。
预期：`pos_max` 序列出现上升、`holders` 非空 ⇒ **判据必须判「未通过（上升）」**。
若没判红 ⇒ **判据无用，正式 50 轮不跑**。

**红控 B（清块）**：单独短跑，把 `reset(LIVE)` 换成含块序列的安全重置。
预期：轮首 `cells_of(BLOCK_SEQ) == 0` ⇒ **I3 无效轮**（并且这是「陷阱①」的阳性对照）。
注意它红在**无效轮**而不是**未通过** —— 这是两条不同的路，混掉就分不清「驱动坏了」和「块泄漏了」。

**执行顺序（纪律：先让判据可满足，再让它变红）**：
```
① 3 轮短跑 ⇒ 证明三条序列都采得到、编号与位置正确（判据【可满足】）
② 红控 B ⇒ 证明 I3 能红
③ 红控 A ⇒ 证明三条主判据能红（不红则停）
④ 正式 50 轮 ⇒ 只有前三步都成立，它的「绿」才有意义
```

## 9 我先给出一个**可证伪**的预测（写在数据之前）

L3b 说「一块大约只能承受 ~10 次往返，25 次答案就坏」。**若本轮设置每轮只是 `share`/`drop`（不旋转、不 save）**，
我预测 **50 轮答案不退化**；此时 L3b 的边界**不适用于本设置**，必须写明它只约束「旋转式往返」。
**若第 k < 25 轮答案开始退化**，则 L3b 的边界比文档更严，且本阶段的判据应以 `k` 为新的实测边界。
**两个方向我都预先接受**，这样结果无论哪边都不是事后解释。

## 10 事后若必须改判据

写成 **「原声明 X → 改为 Y，因为 Z」**，保留 X 原文，不许直接覆盖。
并且：**任何在看过数据之后放松的界（91 / k=3 / 逐轮相等），都要单独列为「放松项」**，
因为**放松总是发生在看过数据之后**，而收紧通常发生在看之前。

## 3.1 针的来源（T1 的前提；lead 要求在放行前补，我复核后写入）

**T1 的字面量「广陵路 12 号 2 单元 602」不是我想出来的，它必须先是本案被判对象里的一段字节。**
判据里出现一个**在被判对象里不存在的字面量**，会让判据**永远不可满足**（正向断言永远红、负向断言永远为真）——今晚已栽过一次（`m2_link` 写成 `m4_layer2_link`）。

**被判对象**：`run_m4_write.json` 的 `block_text`（编码进块的正文），实测 **len = 127**。我在写入本声明时（仍在看数据之前）实测：
```
needle '广陵路 12 号 2 单元 602'  in block_text: True      <- T1 用的这一根
needle '广陵路12号2单元602'       in block_text: False     <- 去掉空格就【不可满足】，所以空格不是格式，是针的一部分
context: '…有什么可以帮你？\n我住在广陵路 12 号 2 单元 602。\n我每天早上七点半出门…'
```
**为什么不写成「广陵路」就够**：三字子串在「我住在广陵路」里必然命中，**它不能区分「记住了地址」与「提到了路名」**。针要长到能区分，短到能逐字节匹配。

**同时分清两个对象（一字段两问）**：`_m5db` 的 `source_text`（len 110）也含这串，但那是 **M5 侧**的输入；本阶段 T1 只问 `block_text`。**两个对象各自一根针，不互相顶替。**

**由此再加一条通用判据（本阶段生效）**：
> **凡判据里出现的字面量，必须先证明它存在于被判对象里；证明要打印「在 / 不在」，不是「应该在哪」。**
**3.1 补写时刻**：2026-10-25 05:53:41（仍在任何一轮数据之前；属【补来源】，不改任何判据 —— 方向=收紧）

---

## 11 修订记录（数据之后；按 §10 的写法，逐条带方向）

本节写于看过执行者 3 轮 smoke 产物（`m3/run_m3_lifecycle_3rounds.json`）**之后**。三条全部属于**改对象**（纪律 28 第三类），**既非放松也非收紧**。

### 11.1 `S3` —— 原参照点跨过了 ask，恒不可满足

> **原声明 S3**：`pos_max_at_attach - pos_max_after_detach == 91`
> **改为**：位置侧 `pos_max_at_attach == pos_hi - 1`（`pos_hi` 取自本轮 attach 区间，不写死）；格数侧 `cells_at_attach - cells_before_attach == 91`
> **因为**：① `raw_pos_max` 是**绝对位置**，两数相减得到的是位置跨度，不是格数；② `kvshim_ask_at` 把本轮问答**写回同一序列**，所以「detach 后」不是空序列 —— 它恢复到了「只剩本轮对话」。

**我读产物实测（不采信转述）**：`pos_max_at_attach=4095`、`pos_max_after_detach=4146` ⇒ `4095-4146 = -51`；换「attach 前」做参照：`4095-(-1) = 4096 ≠ 91`。**两个参照都不成立**，所以不是「差一点」，是这条判据写错了对象。

**意图与实现分开写**：S3 原本为防「attach 接上 0 格」（今晚 74 分钟那次）而加，**那个意图是对的**；错的只是**参照点**。所以本条不是撤掉 S3，而是把它拆成位置侧与格数侧两条，两个意图各自保住。

### 11.2 `C2` —— 同一处病灶的格数版

> **原声明 C2**：`cells_at_attach - cells_after_detach == 91`
> **改为**：`cells_at_attach - cells_before_attach == 91`（比较发生在 ask 之前的同一相位内）
> **因为**：`cells_after_detach = 51` 正是本轮问答写回 LIVE 的 token 数（产物里 `measured_residual_cells=[51]` 与 `measured_ask_tokens=[51]` 相等）；`91-51 = 40`。

### 11.3 `I1` —— 我自己没被指出、但性质更严重的一条

> **原声明 I1**：`rc != 0` ⇒ 无效轮
> **改为**：有效性只看 **答案非空 + needle 在场 + `pos_asked == raw_pos_max_before_ask + 1`**；`rc` 只记录、不作判据
> **因为**：产物里**每一轮 `ask_rc = 93`**（三轮全同）。按原 I1 字面，**50 轮会全部作废，验收永不可能通过**。

**这一条我自己报，理由**：`S3/C2` 是执行者与 lead 指出来的；`I1` 没有人在 `criterion_conflicts` 里列。我读逐轮原值时发现 `rc=93` 是**常态**而不是**异常** —— 若我不报，等于默认它被悄悄忽略。
**它是同一类病**：判据里出现一个**没有来源的常量**（`0`）当阈值，而它与被测系统的返回值语义无关。与 §4 那句同源：**判据里一个没有来源的数字，就是作者的选择，不是数据的性质。**

### 11.4 三条的共同性质：不是「太严」，是**恒红**

恒红判据的区分力 = 0：它每轮都红，提供的信息与没有这条判据完全相同，只多消耗注意力。⇒ 改对参照点**不等于降低要求**，而是把要求从「不可能」变成「可满足且可失败」。

**检验我自己的规矩有没有落到实处**：改后的 S3/C2/I1 必须能红。**若红控 A 只让 S1/S2 红、而 S3/C2 不红，说明改后的形式仍不可失败，须重查。**

| 条目 | 原声明 | 改为 | 方向 |
|---|---|---|---|
| S3 | attach 后位置 − detach 后位置 == 91 | 位置侧 == pos_hi-1；格数侧 attach−before == 91 | **改对象** |
| C2 | attach 格数 − detach 格数 == 91 | attach 格数 − attach 前格数 == 91 | **改对象** |
| I1 | rc != 0 即无效 | 空串 / needle 缺 / 位置失配 才无效；rc 只记录 | **改对象** |

**本轮无放松项。**（按纪律 26：放松须单列；本节明写为空。）
**11 节写入时刻**：06:03:16（看过 3 轮 smoke 之后；三条方向均为「改对象」，无放松项）

### 11.5 机器可比对的四条字符串（唯一权威形式；产物 effective_criteria 必须逐字相等）

理由：判据有两份副本（本文件 / 驱动代码）。只记 sha 只能说明声明变了，不能说明代码实现的是新那版。
下面的键名与字符串取自 §11.6 对齐后的实现形式；§11.6 记录了为什么改成这套符号。

```
S3_pos = "pos_max_at_attach == attach_pos_hi - 1"
S3_cells = "cells_at_attach - cells_before_attach == moved"
C2 = "cells_at_attach - cells_before_attach == moved (same phase, before ask)"
I = "empty answer / needle missing / pos_asked != raw_pos_max_before_ask + 1 / block cells at start != moved / holders or ranges carried / raw_pos_max == -1 / attach interval length != moved"
```

**四条而非三条**：§11.1 把 S3 拆成位置侧与格数侧，两条必须各自能单独判红，
否则等于把「接上 0 格」又埋回一条里（S3 的原始意图正是那一条）。

原文保留（不参与比对，故不加 `NAME = "…"` 形式）：

```
原 S3_position = "pos_max_at_attach == pos_hi - 1"
原 S3_cells = "cells_at_attach - cells_before_attach == 91"
原 I1_valid = "answer_nonempty and needle_present and pos_asked == raw_pos_max_before_ask + 1"
```


### 11.6 §11.5 的第二次修订（与实现的两份副本统一符号）

触发：执行者的产物 `effective_criteria` 与 §11.5 原四条**语义相同、字面不同**：
```
我写 pos_hi / 91        实现写 attach_pos_hi / moved
两者数值相同：attach_pos_hi-1 = 4096-1 = 4095 = 4005+91-1；moved = 91（load 时实测，产物 expectations.declared_n_block_cross_check 里 declared=loaded=91）
```
**按纪律 14（第二份副本须有断言）与你的要求（逐字比对，不一致就红）**：两份副本字面不一致 ⇒ 比对必然红。
**处理方式不是让代码来迁就我，而是我改成与代码同一套符号**，理由两条：
1. `attach_pos_hi` 是 `attach` 调用真正收到的界，`moved` 是它收到的长度 —— 都满足「用调用真正收到的值」；
2. 把写死的 `91` 换成 `moved`，**少一个自由量**（我 §4 那条「没有来源的常量」的自纠）。

> **原声明 §11.5**：`S3_position = "pos_max_at_attach == pos_hi - 1"` / `S3_cells = "cells_at_attach - cells_before_attach == 91"` / `I1_valid = "answer_nonempty and needle_present and pos_asked == raw_pos_max_before_ask + 1"`
> **改为**：下列四条（键名也与产物一致）
> **因为**：两份副本字面不同无法逐字比对；且 `moved` / `attach_pos_hi` 比 `91` / `pos_hi` 少一个自由量。

**方向标签：收紧**（把写死的常数换成调用收到的量；要求未变、对象未变）。**不是放松。**

权威四条（产物 `effective_criteria` 必须逐字等于这些值）：

```
S3_pos = "pos_max_at_attach == attach_pos_hi - 1"
S3_cells = "cells_at_attach - cells_before_attach == moved"
C2 = "cells_at_attach - cells_before_attach == moved (same phase, before ask)"
I = "empty answer / needle missing / pos_asked != raw_pos_max_before_ask + 1 / block cells at start != moved / holders or ranges carried / raw_pos_max == -1 / attach interval length != moved"
```

原文保留（不再参与比对，故不加 `NAME = "..."` 形式）：
```
原 S3_position = "pos_max_at_attach == pos_hi - 1"
原 S3_cells = "cells_at_attach - cells_before_attach == 91"
原 I1_valid = "answer_nonempty and needle_present and pos_asked == raw_pos_max_before_ask + 1"
```
**11.6 写入时刻**：06:06:53（方向=收紧；只统一符号，不动要求）
