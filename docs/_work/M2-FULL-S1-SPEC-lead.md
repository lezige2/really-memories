# M2 完整 · S1 施工口径冻结 **v6（最终）**（lead · 2026-10-25 22:45 本地）

> 依据：预登记 `docs/_work/M2-FULL-PREREG-draft.md` `c2afd97aad278ade` §2.4/§3 · 裁定 (i) 预算方案 **B**
> **版本史**：v1 `7568d471ac387855`（作废）→ v2 `d2772dce2bc35c02`（作废，硬矛盾）→ v3 `36325e128641615c`（作废）→ v4 `09cd7345`（作废）→ v5 `43617284c5183291`（作废，**真机两处硬矛盾**）→ **v6 本文件为准**。
> **v6 的六处修正（真机实测驱动，非推测）**：① **几何改为"块紧邻 chat 起点 + 顶对齐"**（v5 的 `end=CHAT_START−i*SLOT` 会留 64/128 格空位 ⇒ 引擎 decode 直接拒绝）；② **`attach` 的 `hi` 是排他上界**（v5 写 `pos_hi=end−1` ⇒ 丢最后一格）；③ **B 的 chat 起点顺延**，不卸 A 的块；④ **②a 降级**（被证明恒真，不再是交叉证据），新增 ②c；⑤ **②b 用"去空白后子串"**；⑥ **CAP 的"数据化拒绝"被认可**（`cap.refused` + exit 2 等价于 `PlanRefused`，但 `cap_ok` 不许对未跑的会话假声明）。另：**chat.db 是指标派生库、非冻结源**（见 §11）。
> **v5 的五处修正**（`_place_slots` 接线写死 / 顺序措辞 / schema 两个字段 / 每轮提问序列 / `seq:int`）：**这一版是最终基线，不再回收口径意见**（除非出现硬矛盾）。
> **v4 的三处修正**：① `source_blocks` 口径写死 = **`_selection` 结果 ∩ `mounted_blocks`**（否则 `_selection(k=2)` 返回未挂载块 ⇒ ②a 正常臂假红）；② **R2 时 ④ 的"引擎实测一致"子断言记 `not_applicable`**（前提被该注入破坏），④ 的账目/预算子断言仍绿；③ **冻结执行顺序 A→B** 并写死 `n_ctx_eff` 取值时点。
> **v3 的关键修正**：**挂载集拆开**（原句"A 与 B 挂同一块集合"与交叉判据**互斥**）、**红证 R1/R2/R3 判法重写**、**`resident_other`/③ 公式写死**、**P-1/P-2 实为独立**（v2 理由写错）。

## 0 一句话

S1 = 同一 `n_ctx=8192` 里跑两段有界会话：**A（`seq 0`）只挂 home**、**B（`seq 7`）只挂 project**，habit 只登记不挂（留作 pool/控制）；各问自己那块的事实、**结构层与文本层都不串**、账目可对。**唯一需要 14B 的一件**：先零 GPU 做完调度/几何/记账/断言与红证，再上真机。

## 1 冻结数（v3）

| 项 | 冻结值 | 依据 / 修正点 |
|---|---|---|
| 每会话轮数上限 `N_ROUNDS` | **10** | 实测 10 轮 ⇒ `n_chat_cells=666`、末轮 `n_tokens_after_ask=666` |
| 每会话 chat 上限 `CHAT_LEN_CAP` | **1024 chat cells** | 余量 1024/666 ≈ **1.54×**（`740` 那个数插入了 car 块(19 cells)，**不是 chat 口径**，作废）|
| **CAP 执行点** | 每轮后 `chat_cells_self ≤ 1024`，否则 **`PlanRefused`** | `plan()` 只把 `chat_len` 当 refuse 预留、**从不校验实际增长** ⇒ `two` 自己判 |
| `budget.chat_len` | **按 CAP 预留（1024）**，不用实际值 | 用实际值会在最后一轮才超、回不了头 |
| **执行顺序（v6）** | **A 先跑完 10 轮 ⇒ 再跑 B 10 轮**（不交替、不做真并发）。`n_ctx_eff` 取**该次 plan 之前**另一会话的实际 chat cells | 顺序不定则 `n_ctx_eff` 取值不定 |
| **★几何（v6 真机钉死）** | **块紧邻本会话 chat 起点、顶对齐**：`chat_start_A = CHAT_START = 4096`；A 的 home(21) 放 `[4096−21, 4096) = [4075,4096)`；**B 的块起点 = A 的 chat 结束位置 = `4096 + n_chat_A`**，B 的 project(18) 放 `[4096+n_chat_A, 4096+n_chat_A+18)`，`chat_start_B = 4096 + n_chat_A + 18` | **v5 公式 `end=CHAT_START−i*SLOT` 作废**：真机实证"块尾必须正好紧邻 chat 起点，否则 decode 拒绝"（块 0..11 后 `pos=12` 命中、`pos=13` 空）；A 的 `0..4074` 空前缀已证可接受（D4），B 同构 |
| **`attach` 的 `hi` 语义（v6）** | **`hi` 是排他上界** ⇒ `leases.attach(seq, dst, lo, end)`，**不许传 `end−1`** | v5 传 `pos_hi=end−1` 丢最后一格 ⇒ 顶对齐也红（off-by-one）；`_place_slots` 传的就是 `end` |
| **不卸 A 的块** | A 的 home 全程常驻（B 的块放在 A chat 之后，不重叠）；④ 记账时点 = **B 跑完** | 卸 A 会改 ④ 口径（blocks 变 0）且破坏 ④ 的"块常驻"语义；位置顺延即可解决 |
| **`n_ctx_eff`（v4 写死）** | `n_ctx_eff_A = N_CTX − chat_B_before_plan`；`n_ctx_eff_B = N_CTX − chat_A_before_plan`；`plan()` 的 `cells` = **本会话挂载块** | `plan()` 的 `cells` 已含本会话块 ⇒ 若再把块放进 `resident_other` 就**重复计**；两条预算各判一半，④ 再兜总账 |
| 会话 seq | **A = `0`，B = `7`** | `_place_slots` 写死 `start=1`；B=7 天然空（r2 只挂 3 块）⇒ helper/`m1`/`save` **零改动**；`two` 断言 `7 ∉ block_seqs` |
| **挂载集（v3 关键修正）** | **A 挂 home（`seq 1`→dst 0）**；**B 挂 project（`seq 2`→dst 7）**；**habit（`seq 3`）只登记不挂** | **原句"A 与 B 挂同一块集合"作废**：同一集合下"专属块"是空集 ⇒ ②a 只能是空断言/恒假，②b 变成模型复述抽奖。拆开后 ②a 有定义（`source_blocks` 集合不相交）、②b 才成立（A 上下文没有 project ⇒ 不会说 `3月14`）|
| 块登记 pool | **3**（home/project/habit，`seq 1/2/3`） | 与 r2 `blocks_mounted` 一致；**不含 car**（car 属 r2 中途插入臂，S1 不做插入）|
| `CHAT_START` | **4096 不变** | 位置是 per-seq 的 |
| `attach_replay` 计数 | **必须 = 0（禁 replay）** | P-2 |
| 超预算 / 超 CAP | **`PlanRefused`** | 不许静默降级 |
| 事实/问题 | `Q_A` 问住址 ⇒ `FACT_A="广陵路"`；`Q_B` 问项目上线时间 ⇒ `FACT_B="3月14"` | 取自 r2 在用事实 |
| **每会话 10 轮提问脚本（v5 冻结）** | **A：`Q_A` × 10 轮**；**B：`Q_B` × 10 轮**（不做 A/B 交替、不插控制问题）| `666` 是 r2 的 **10 个不同问题**的结果 ⇒ **不能当 S1 的预测值**；③ 只判 `Σ ask 增量` 与 `pos_max` 公式，**不许硬编码 666**；CAP 一律按 1024 上限判 |

## 2 实施位置（不变）

- 新增子命令 `two`（`cmd_two()`）+ `--dry-run`；**默认 `chat`/`m1` 行为一字不变**。
- **`--dry-run` 与真机臂走同一调度代码**，只换 engine factory：`StubEngine`（零 GPU，测试床内实现，**不进 `chat.py` 主路径**）vs **`CountingEngine`（透明代理真引擎，只数 `share`/`drop`/`reset` 并转发）**。
- 复用 `_selection:485`、`_ask_all:405`、`GuardedLeases:282`、`BlockLeases:31`、`plan():46`；**`_place_slots:378` 只借它的几何公式，不直接调用**（见下）。
- **★接线写死（v5，最容易踩）**：`_place_slots` 内部是 `for i,row in enumerate(rows,start=1)` + `leases.attach(i, 0, lo, hi)` ⇒ **seq 从 1 起、dst 固定 0**。若 two 直接用它放 project，project 会落成 `seq1` 且挂到 **dst0（A 的对话 seq）** ⇒ A 看得见 project ⇒ ②a/②b **直接假红**。
  ⇒ **`two` 自写"放 + 挂"循环**（只沿用几何公式 `end = CHAT_START − i*SLOT; lo = end − n`，`i` 按块在池内的序号），并**每块只挂一个对话 seq**：**home(`seq1`) → `dst 0`**、**project(`seq2`) → `dst 7`**、**habit(`seq3`) → 不挂**。产物里 `pool[]` 的 `mounted_by` 必须是 `["A"]` / `["B"]` / `[]`。
- **`cmd_m1:554/:610/:619` 一行不动**；`two` 自带同口径读数。
- **不许动**：冻结三件、`chat_lease.py 619a0432`（必须改 ⇒ 停手报我）、`m2_planner/*`、`chat.db`、`m3_lease.py`。

## 3 判据（v3，逐条给公式/判法）

| # | 判据 | 判法 | 阶段 |
|---|---|---|---|
| ① | 两会话各命中自己块的事实 | A 答 `广陵路`、B 答 `3月14`，互不替代 | S1-b |
| **②a（v6 降级）** | **接线回归**（**不再是交叉证据**）| `source_blocks = selection ∩ mounted`；断言 `source_blocks_X ⊆ mounted_X`。**恒真已被证明**：`sources = mounted ∩ 命中`、`专属_other = mounted_other − mounted_X` ⇒ 交恒空；且本 DB 的 `_selection(k=2)` 对 Q_A/Q_B 都只返回 1 条。**⇒ 只作接线回归，不计入交叉分母** | dry-run（仅回归）|
| **②c（v6 新增，零 GPU 交叉旁证）** | **选择层文本不串**：用**未过滤**的 selection 结果文本判 | A 的 selection 文本**不含** `3月14`；B 的 selection 文本**不含** `广陵路`（去空白后判）| dry-run |
| **②b** | **文本层不串** | A 答案不含 `3月14`；B 答案不含 `广陵路`（2 条） | S1-b |
| ③ | 逐会话 `n_tokens`/`pos_max` 与期望一致 | **公式（v6）**：`n_tokens_self = Σ(本会话每轮 ask 增量)`；`pos_max_self = chat_start_self + n_tokens_self − 1`（**不是固定 CHAT_START**）；`chat_start_A=4096`、`chat_start_B=4096+n_chat_A+18`；块位置读数**单列** `blocks_geometry` | dry-run + 真机 |
| ④ | 账目合计 ≤ `n_ctx` 且可对账 | **每会话 `chat_cells` 一律取"本会话 ask 增量之和的记账值"**（**不许用 seq 读数替代**）；`blocks + chat_A + chat_B = total`；"实测一致"口径限定为 **`leases.cells_of`（块）+ 每会话记账 chat 之和**（**不读 seq**）；每轮 `chat_cells_self ≤ CHAT_LEN_CAP` 否则**拒绝**（v6 认可"数据化拒绝"：`cap.refused=true` + `refused_reason="chat_len_cap"` + 进程 **exit 2**，等价于 `PlanRefused`）；**未跑的会话 `cap_ok` 必须记 `not_run`，不许写 true** | dry-run + 真机 |
| ⑤ | `sha_stable` | 跑前跑后冻结三件 + **两侧块文件（home、project 两个；habit 只登记不挂 ⇒ 只记「登记未挂、不检」）** 同值 | **仅 S1-b**（dry-run 记「未做」，记绿即假绿）|

## 4 前置 P-1 / P-2（v3：**实为独立**）

**P-2**：`leases.events` 里 `kind == "attach_replay"` 计数 **= 0**。

**P-1（计数等式，替代不可判的"直接计数=0"）**：
- `eng.share` 调用次数 **==** `events` 中 `attach` 数
- `eng.drop` 调用次数 **==** `detach 命中数`
- 真机臂用 `CountingEngine` 透明代理跑同一等式。
- **P-1 拆两半（v6）**：**P-1a = share 等式**（有 2 正例 + R4a 红证 ⇒ 可判）；**P-1b = drop 等式**（S1 无 detach 路径 ⇒ `drop=0/detach命中=0` 是 0==0 **零实例，记「未触发/不可判」**，不许记"通过"）。

**v2 的错误理由作废**：v2 说"replay 跳过 `eng.share` ⇒ P-1/P-2 同时红"。**实测代码不是这样**：`m3_lease.attach` 的 replay 分支 `_note("attach_replay")` 后 **直接 `return`，既不发 `eng.share` 也不发 `attach` 事件**（`m3_lease.py:84-88`）⇒ 等式 `share == attach 事件` **仍然成立** ⇒ **P-1 不受 replay 影响，两条独立**。R4 拆开无碍。

## 5 红证（v3：五条，互不覆盖；每条必报"其余仍绿"）

| # | 夹具 | 期望红 | 必须仍绿 |
|---|---|---|---|
| **R1** | **只注入选择元数据**：把 `seq 1`（A 专属）塞进 B 的 `source_blocks`/选择结果，**不真挂 cells** | **②a** | ③④（几何/账目未被触碰）|
| **R2** | **同 seq**：B 也用 `seq 0`、`chat_start=4096` | **③** | ④ 的**账目公式/预算子断言仍绿**；④ 的**"引擎实测一致"子断言记 `not_applicable`**（其前提=两会话 seq 不同，被本注入故意破坏 ⇒ 不许算红，也不许算绿）|
| **R3** | **记账少记**：把 B 的 `chat_cells` 置 0（不动实际增长） | **④ 的对账断言** | ③（读数仍真）|
| **R4a** | **P-1 绕过**：不经 leases 直接 `eng.share` 一次 | **P-1 等式** | ①②③④ |
| **R4b** | **P-2 重放**：同块同区间连续 attach 两次（触发 replay） | **P-2（`attach_replay`>0）** | ①②③④（P-1 等式仍成立）|
| **R5** | **CAP 守门删掉**：构造第 11 轮 / `chat_cells` 超 1024 的输入，去掉每轮 CAP 校验 | **`PlanRefused`/CAP 断言**（④ 的子断言）| ③ |

红证一律**变体法**（临时目录复制调度模块，改一处，跑同一构造）；**不许在生产代码留关判据开关**；产物成对。

## 6 三级分母（缺一读数无效）

- 会话数 **2**
- **挂载块数 2**（A:home / B:project）；**登记 pool 3** —— **两个数都要报，不许混**
- 交叉断言数 **2**（②a 结构 1 + ②b 文本 1；dry-run 只有 ②a，须写明"②b 未做"）
- 另报：每会话实际轮数、`cells` 三项（blocks / chat_A / chat_B）与 `total`

## 7 产物 schema（v3，两阶段同构）

```
{schema, at, mode: "dry-run"|"real",
 pool: [{name, seq, cells, mounted_by: []|["A"]|["B"]}],
 sessions: [{id:"A"|"B", seq:int /*A=0,B=7; R2 变体可为 0*/, rounds,
             mounted_blocks:[seq...], source_blocks:[seq...],
             chat_cells, n_tokens, pos_max, pos_max_expect}],
 cells_accounting: {blocks, chat_A, chat_B, total, n_ctx, within_budget,
                     engine_match: {status:"done"|"not_applicable", detail}},
 blocks_geometry: [{seq, name, base, pos_hi}],   /* ③ 的块位置读数单列 */
 cross: {a_to_b: {ok, a_contains_fact_b}, b_to_a: {ok, b_contains_fact_a},
         structural: {a_source_vs_b_exclusive_ok, b_source_vs_a_exclusive_ok}},
 counters: {share, drop, attach, detach_hits, attach_replay,
            p1_share_eq, p1_drop_eq, p2_ok},
 budget: [{session, n_ctx_eff, chat_len_reserved, cap_ok, refused, refused_reason}],
 sha_stable: {status: "done"|"not_done", ...},
 verdict, fail_ids: [], exit}
```

## 8 四态与不做什么

- **四态**：通过 / 未通过 / 未接上 / 未做。**未接上** = 拿不到第二 seq 的位置空间或 `n_seq < 2` ⇒ 报"未接上"并停，**不许用共享 chat 区冒充**。
- **不做**：不做真并发（两段**顺序**跑，**A→B，不交替**）；不做跨布局对照；不抬 `n_ctx`；不动冻结三件；不改 `plan()` 签名；不做中途插入（car 不属 S1）。

## 9 与预登记的关系（必须留痕）

本 v3 **改写了预登记 §2.4 的一句**："A=seq0、B=seq1 **同时挂同一块集合**" ⇒ **作废**，改为"A 只挂 home、B 只挂 project、habit 只登记"。理由：同一集合下交叉判据无定义（空断言/恒假），**这是判据不可执行，不是执行偏差**。§3 的 P-1 表述同步改为计数等式。**inspector 已同意此改法（其审阅意见为直接来源）**；预登记文件本身由 inspector 回填这条修正。

## 10 签署（v3）

| 项 | 内容 |
|---|---|
| 冻结人 / 版本 | lead / **v4**（v1 `7568d471`、v2 `d2772dce`、v3 `36325e12` **均作废**）|
| 冻结内容 | 执行顺序 **A→B**（`n_ctx_eff` 取该次 plan 前另一会话实际 cells：A=8192、B=7526）· `source_blocks = selection ∩ mounted` · `N_ROUNDS=10` · `CHAT_LEN_CAP=1024 chat cells`（每轮校验 + budget 按 CAP 预留）· A=`seq0` 挂 home · B=`seq7` 挂 project · habit 只登记（pool=3/挂载=2）· `CHAT_START=4096` · `n_ctx_eff = N_CTX − 另一会话 chat_actual` · ③④ 公式 · 禁 replay · P-1 计数等式（与 P-2 独立）· 红证 R1/R2/R3/R4a/R4b/R5 · 分母 `2/2/2` + pool 3 |
| 生效 | 2026-10-25 22:10；跑起来后任何变更 ⇒ S1 判据作废重做 |

## 11 环境口径（v6 新增：chat.db 漂移与 m1 崩溃）

1. **`kvmem/chat.db` 是派生索引、不是冻结源**：21:29 起现盘从 `237d8e1f5de9a382` 变成 `cd430943dab180e0`（`memory_source` 10 行与三个块文件**逐字节未变**，变的是 `attr`/`value_kind` —— 同 `index_meta` 版本下**重建非确定**）。⇒ **冻结集 = `memory_source` + 块文件（home `73843fc5` / project `536eac03` / habit `f6f8e85c`）**；`chat.db` 只作"派生坐标"记录，**两版 DB 都留证**。
2. **恢复 + 隔离**：把仓库 `chat.db` 恢复到 `237d8e1f`（所有已签台账的坐标）；**此后所有臂一律用 temp DB 副本**，仓库库只读。
3. **缺口 G3（新）**：`build` 的派生字段（`attr`/`value_kind`）**非确定** ⇒ 同一 `memory_source` 可重建出不同 DB。凡"0 漂移"结论若含 `chat.db`，一律加注"派生库，见 G3"。
4. **缺口 G4（新，非 S1 引起）**：`m1` 真机臂在现库上 `exit 1 / KeyError 'conv_2026-10-25#L5' @ chat.py:598`（selection 命中 conv 源但无块行；task-5 重建后如此，**改前副本逐字复现**）。⇒ **M4-C 绿臂当前不可直接重跑**，须先修 selection→块行的过滤或补块行；单列，不阻塞 S1。
