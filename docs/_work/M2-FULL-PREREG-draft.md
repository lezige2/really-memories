# M2 完整 预登记草案（权威版）

> **来源与采用关系**：本文件 = **executor 起草 → inspector 采用并修订**。输入稿 `docs/_work/M2-FULL-PREREG-draft.md` = `9855df9bdf5b00ee` / 19,170 B（lead 裁定：不删，以它为输入，出权威版，**最终只留这一份**）。
> **性质**：预登记**草案**，不是判据，不能当验收依据。**M2 完整四态 = 未做**（三件见 §1）。本文件不写「通过/验收」。
> **纪律**：每条现状事实指 `file:line`（可 grep 打假）；所有 sha16 = 本文件写作时**二进制读 + `sha256[:16]`** 现算；回填件按**史料**读、`PROGRESS` 是唯一权威；判据守四条红线 —— ① 首次读数应红 ② 空集/零读数报**三级分母** ③ 不许拿 `try` 里的异常当判据（期望抛错用显式 `expect_raise` 记返回态）④ 报数只引台账 sha，引用前现算。

---

## §0 输入锚（写作时点现算）

| 资产 | sha16 / 大小 | 用途 |
|---|---|---|
| `tools/chat.py` | **`cb70be52eef253fa`** / 34,319 B | 产品路径：单会话对话、租约调用点、几何常量 |
| `tools/chat_lease.py` | **`619a043215035de7`** / 19,274 B | `GuardedLeases` 包装、sites/refusal 记账、session_state 桥 |
| `kvmem/m2_visibility/m3/m3_lease.py` | **`7a838d0a956e44aa`** / 6,211 B | `BlockLeases`：本文 §2.1/§2.2 的改造对象 |
| `kvmem/m2_visibility/m2_planner/planner.py` | `01507f6bbf816c11` / 9,093 B | `plan:18` / `insert_ops:66` / `apply_insert:82` / `PlanRefused:8` |
| `kvmem/m2_visibility/m2_planner/plan.py` | `74da0732d9caa6a6` / 4,290 B | 冻结接口 `plan(blocks, chat_start, budget)` `:46` |
| `kvmem/m2_visibility/m2_planner/evict_policy.py` | `aa7cbf3f86df30f8` / 3,468 B | `DEFAULT_POLICY="off":23`、`evict_order:31`、`select_to_evict:41` |
| `m2_planner/out/RED-SUITE.json` / `GREEN-SUITE.json` / `PLAN-SELFTEST.json` | `13771a2d633a8bb4` / `d3485eb29a97e5cb` / `a0c0782b24171f7b` | 红套件 9 例 `all_as_designed=True`；绿套件 18 断言+4 契约 `all_green=True`；自测 12/12 + 3 必红 |
| `m2_planner/kvsim.py` / `assertions.py` / `fake_planner.py` | `2a28771133dd1571` / `ef74d2dfa12702d4` / `3f874eab06200c99` | `SimNoEffect:86`、S1–S6 断言、六种错法+位置对字节错 |
| `m2_planner/RESULTS-RED.md` | `16a4174c5f940d6c` / 33,456 B | `:94`/`:143`/`:150`/`:170` 的「无淘汰」前提与非目标 |
| `kvmem/m2_visibility/chat_lease/run_compare.json` | `1eb7029167edd7e0` | M3 接入 chat.py 的对比产物（**`FEATURES.md:18` 记的 `fd6333a4` 是旧快照**） |
| `kvmem/chat.db` | `237d8e1f5de9a382` / 110,592 B | `index_meta {docs:2, version:5, analysis:4}`，本文不重建 |
| `docs/_work/M2-ACCEPT-lead.md` / `out/M2-ACCEPT-r2.json` | `6f26bce0c876cea4` / `c95e0b7c2b7cc163` | M2 规划器已验收（r2），真机臂判据+红证模板 |
| `docs/_work/M4C-CLOSURE-lead.md` | `3309fb25cbd057f9` | 四站承重表（§4.3 `:73-81`、§7 `:112-113`）、变体快照法 |
| M1.8 收尾（背景，不属本文） | `freeze_check.py 6016085a`；A `673a2c9334d2f4a7` 17/17；A11 红证 `1997e32a2187e56f` | 检索层已冻结，M2 完整不得动它 |
| 本文件输入稿 | `9855df9bdf5b00ee` / 19,170 B | 仅作输入，不是判据 |

> **状态回填（2026-10-25 20:26）**：§0 下表是**写作时**读数，不回改；此后 `m3_lease.py` 已 `7a838d0a` → **`675f983f`**（L1 落地并已签，判决 `docs/_work/M2-FULL-L1-ACCEPT-lead.md 803e8f6d`，独立复核 `docs/_work/INSPECTOR-L1-REVIEW.md 66cf3aa5`）；L2 施工中（task-26）。L1/L2 状态变化不影响本草案 §2 判据文本。
>
> **行号口径**：`PROGRESS` 是活文档（本文件写作时 `761052001274bfdd` / 203,838 B），本文引它的行号 = **2026-10-25 20:50 现算**，同时给章节锚（§4 / §5.5 / §5.7 / §13.4）；行号漂移时以章节为准。
>
> 两处易错：`FEATURES.md:18` 的 `run_compare` sha 是**快照值**；`kvmem/m2_visibility/mine/inspector/*` 是 20:01 的**回填件（史料）**，引它只作格式先例，结论以 `PROGRESS` 为准。

---

## §1 现状事实（三件；每条给「可被打假的形式」）

### 1.1 pinned 驱逐：**查无**（现成的 pin 语义在租约层，不在引擎/策略层）

- **产品三文件没有 pin 字段或接口**：`tools/chat.py` 里 `pinned` 唯一字面在 `:103`（`_event` 的 docstring：「site is pinned to None」，几何语境，不是免驱逐标志）；`chat_lease.py` 与 `m3_lease.py` 命中 **0**。全仓其余 `pinned` 命中都是几何/event 语境：`tools/hole_matrix.py:11/:108/:230`、`tools/hole_probe.py:72`。
- **淘汰策略存在但明确不接主路径**：`evict_policy.py:23 DEFAULT_POLICY = "off"`、`:31 evict_order`、`:41 select_to_evict`（返回 `kept/evicted/over_budget_before/after`）；启用契约写在 `:13-15`；`plan.py:23-25` 写死「无淘汰，放不下就 `PlanRefused`」；产品路径 **不 import** 它 —— 唯一 import 是 `selftest_plan.py:22`（`land_m2planner.py:30` 只在落地清单里列文件名、`plan.py:25` 只在 docstring 提及，均非 import）；`PLAN-SELFTEST.json.eviction = {"default": "off", "in_main_path": false, "why": "签字版非目标（RESULTS-RED.md:150）+ S2↔S6 耦合论证以「无淘汰」为前提（RESULTS-RED.md:94/170）"}`（引号内为 `PLAN-SELFTEST.json` 的**原样文本**；其中 `RESULTS-RED.md` 指 `kvmem/m2_visibility/m2_planner/RESULTS-RED.md`，不另改引文）。
- **旧淘汰实现另有两处（不是产品路径）**：`tools/kvslots.py:32/:309/:438`（4 槽 LRU，M2-v1 时代过程工具）；`tools/m2_v1.py:26/:121-152/:206`（确定性 LRU + `pool.evict` + `assert_layout`），其 `:26` 自述「Deterministic eviction only (LRU). No product eviction policy in this cut.」
- **pin 的现成语义来源已经存在**：`m3_lease.py:59 def leased()`（`holders` 非空即被引用）、`:56 referrers()`；`GuardedLeases` 直接继承（`chat_lease.py:282`）。`PROGRESS:260/:295` 记 E7【明确未做·查无】（注：那条「三文件 grep 命中 0」是当时扫描口径，现值是「只有注释命中、无 pin 语义」，两者不矛盾）；`PROGRESS:761/:771-776` 已实测裁定：**引擎不拒绝 `reset` ⇒ pin 只能是外层租约表职责 + 需要承重自证**。
- **可打假形式**：任一产品文件出现 pin 字段/驱逐调用，或 `evict_policy` 被 `tools/chat.py`/`chat_lease.py` import ⇒ 本节错。

### 1.2 多序列：**单会话写死**（三处写死 + 一处预算结论修正）

- ① **容量**：`chat.py:76 N_SEQ = 8`；引擎构造 5 处都写死 `n_seq=8`（`:193/:235/:422/:458/:516`）。
- ② **对话只走 seq 0**：`eng.ask(0, …)` 在 `:330/:340/:408/:652`；attach 的目的序列写死 0（`leases.attach(<blk>, 0, …)` `:310/:397/:604`，共 3 处）；detach 目的序列写死 0（`:561/:593`，共 2 处）；漏清断言按 `range(1, N_SEQ)` 把「0=对话、1..7=块槽」写进代码（`:619`，另 `:554/:610` 的 per-seq 读数循环）。
- ③ **每轮重排块 seq**：`chat.py:588-589 for i, name in enumerate(order): seq = i + 1` —— 块的 seq 随挂载顺序漂移，没有「会话」维度。
- **④ 预算事实（修订 executor 初稿的结论，重要）**：位置空间是 **per-seq** 的（每个 seq 各自 0..n_ctx-1），被 n_ctx 约束的是**总 cell 池**（`plan.py:18-21`：`pool_bytes = n_ctx * bytes_per_token`，实测 `bytes_per_token=104,448` ⇒ 池 cell 数 = n_ctx = 8,192）。实测单会话 10 轮：`n_chat_cells_before_insert = 666`、`fact_ok.ask.n_tokens_after_ask = 740`（`out/M2-ACCEPT-r2.json`；另 `mounted_still_answers.n_tokens_before_ask = 740`），M2 r2 总 `live_cells = 736`（= 块 51 + chat 666 + car 19）。
  ⇒ **两会话 + 4 块 ≈ 2×(740+51) ≈ 1,582 cells < 8,192，池子放得下**。**（状态回填 21:55：`740` 是**插入 car 块之后**的 `n_tokens`，不是 chat 口径；chat 口径是 **666** ⇒ 按 chat 口径 `2×(666+51) = 1,434`，结论「放得下」不变；`740` 别再当 chat 用。）** 所以「第二段对话没有位置」**过强**：在 10 轮量级是**有位置**的；「没有位置」只在**长会话无轮数上限**时成立（50 轮 × ~74/轮 ≈ 3,700/会话，两会话 ≈7,400 + 块逼近上限）。真正缺的是：(a) 第二对话 seq 的分配与 `ask(seqB,…)` 调度；(b) **每会话轮数/chat_len 上限的冻结**；(c) 预算记账把「另一会话已占 cells」算进去（`planner.plan:31` 只判 `cells + chat_len > n_ctx`；调用方可传 `n_ctx_eff = N_CTX - resident`，**不必改冻结签名**）。
- **引擎侧真实上限**：`PROGRESS:312`（S3）多用户容量按 `std::bitset<LLAMA_MAX_SEQ>` = **256**（每 cell 32 B 位图）；当前实际被 `n_seq=8` 与池容量卡住，不是 256。
- **可打假形式**：盘上出现 `ask(1,…)` / 第二 chat seq 的调度，或 `N_SEQ > 8` ⇒ 「单会话写死」已不成立。

### 1.3 位置租约：**开着记账，没开校验**

- **真身** `m3_lease.py`：`class BlockLeases:31`；`blocks:40 / holders:41 / ranges:42`；`attach:63-76`（注册+非空校验后 `eng.share:72`，再写 `holders:73`、`ranges:74`）；`detach:78-88`（按 `(dst_seq,lo,hi)` 精确 pop，**未命中时 `block_seq=None` 但仍调 `eng.drop:81`**）；`reset:91`（有 holders 且非 force 则拒）；`safe_reset_all:107`；`cells_of:125`（异常时返回 1，注释明写「unknown: do not block on it」）；`status:132`；`LeaseError:27`。
- **没有区间重叠校验**：`attach` 对同一 `dst_seq` 的任意 `(lo,hi)` 一律接受；两个块挂到相交区间 ⇒ 后者覆盖前者 cells，而 `ranges` 只保留后者 ⇒ detach 前者时键不存在（记账漂移）；`grep -n overlap m3_lease.py` = **0**。**（状态回填 20:26：以上为 L1 前现状；L1 已于 20:12 落地 `675f983f`，同 `dst_seq` 重叠现抛 `LeaseError` 且拒绝前不 `share`；L2 施工中。本节事实按**预登记日**保留，供红证对照。）**
- **产品包装** `chat_lease.py`：`GuardedLeases:282`（继承 `BlockLeases`；`counts:288`；`sites:289`；reset 覆盖 `:316`，拒绝时计数+`raise`（**不吞**）`:320-326`，reset 后 `cells != 0` 抛 `:331-336`；attach 覆盖 `:339`，对 manifest 声明范围不符记 `range_mismatch:342-346`；detach 覆盖 `:351`；`report:359`；`from_manifest:296`；`STRICT:47`（未登记的非零 seq 直接拒）；session_state 桥 = `share:208` / `reset:218` / strict 拒 `:232-236`）。**executor 初稿引的 `:45/:212/:239` 是旧行号，已按现盘更正。**
- **当前调用面**：`chat.py` 里 `GuardedLeases(` 构造 3 处（`:236/:382/:517`）+ `from_manifest` 1 处（`:460`）；`leases.reset(` 4 处（`:270/:386/:562/:595`）；`leases.attach(` 3 处（`:310/:397/:604`）；`leases.detach(` 2 处（`:561/:593`）。
- **M4-C 覆盖到哪一站**：四站里只有 `m1.unmount.after_detach`（`chat.py:562`）证到**后果级承重**（`M4C-CLOSURE-lead.md 3309fb25cbd057f9` §4.3 `:73-81`、§7 `:112-113`：删 L562 ⇒ 被丢 seq 的 cell 留池 36→86 tokens ≈3.6→8.6 MiB；site1 实测未观察到引擎侧后果；site2/site4 未实测、其判据按读码作废；三站「不承重」**不签**）。**位置冲突从未被测过**。
- **可打假形式**：拿 `BlockLeases()` 喂「同 `dst_seq` 重叠区间的两个块」，现状**不抛错**（第二块覆盖第一块）；若盘上版本抛错 ⇒ 本节已过期。
- 回填影响：`m3_unit_falsifiers.py:30` 引的 `mine/inspector/M3-PREREG.md`（`3e4f465b67eebd3c`，史料）已回填，该引用不再是悬空路径；本文引它只作**格式先例**。

---

## §2 判据草案

**共用纪律**：判据必须**首次读数应红**；空集/零读数必须报**三级分母**（构造数 / 命中数 / 分母本身）；期望抛错一律用显式 `expect_raise` 记 `{raised, type, msg}` 返回态，**禁止 `try: ... except: pass`**；红证明一律用**变体法**（系统临时目录复制模块 → 删/停用被测检查 → 同构造必须不红），**不许在生产代码里留「关闭判据」的开关**；报数只引台账 sha，引用前现算。

### 2.1 L1 位置租约重叠校验（零 GPU，第一优先）

- **判据 L1**：`BlockLeases.attach(block_seq, dst_seq, lo, hi)` 必须在**调用 `eng.share` 之前**检查：对 `ranges` 中同 `dst_seq` 的已登记区间 `(klo,khi)`，若半开相交（`klo < hi and lo < khi`）且**不是同一 block 的精确重放**（`ranges[(dst_seq,lo,hi)] == block_seq`）⇒ 抛 `LeaseError`，消息含 `dst_seq`、两个 `[lo,hi)`、两个块名/seq；**抛错时 `holders`/`ranges` 不得变，且不得调 `eng.share`**（拒绝不得先做破坏动作）。不同 `dst_seq` 的区间重叠**合法**（同一块挂多 seq、不同块在不同 seq 同位置，正是 M2 并发形态）；同一块同一区间重放**幂等**（记 `attach_replay`，表不变）。
- **读数方式**：复用 `kvmem/m2_visibility/m3/_test_lease.py` 的 `Stub`（零 GPU、零引擎、只记调用与 token 数）。产物 JSON 每例：`{case, calls_before, calls_after, raised, ranges_after, holders_after}` —— **以 `raised`/状态判，不以异常逃逸判**。我写作时已现跑该单测：**0 failed**（零 GPU，未写任何产物）。
- **通过**：① 重叠 4 例全抛且表不变（同 dst 不同块 / 部分重叠 / 完全重叠 / 包含）；② 跨 dst 2 例不抛；③ 精确重放 1 例不抛且表不变；④ 既有 `_test_lease.py` 全绿，且 `GuardedLeases.from_manifest` 的 `range_mismatch` 语义不变（`chat_lease.py:342-346` 仍只在范围不符时记事件、不抛）。
- **未接上**：`BlockLeases` 未被产品调用（现状不是：`chat.py:37` import、3+1 处构造）或 stub 拿不到 ⇒ 报「未接上」并停在四态，不降级跳过。
- **红证明**：临时目录复制 `m3_lease.py` → 删除新增校验块 → 跑同一构造 ⇒ **不抛**（记 `variant_not_raised`）。当前版与变体版产物**成对**存在才算证成（M4-C 变体快照法；M18-3 预跑改前代码法）。
- **三级分母**：构造数（4 重叠 + 4 边界 + 2 跨 seq + 1 重放 = **11**）/ 拒绝数 / **真命中数**（拒绝原因确为区间相交，且报出的区间与构造一致）。
- **回归**：产品三处 attach 均落在互斥区间（`:310` fresh、`:397` slots、`:604` mount，且 detach+reset 在前）⇒ L1 落地后 M4-C 的 14B 绿臂不变量应不变；**若绿臂读数变，按「判据或实现错」处理，不许改断言**。
- **落地状态（20:26）**：L1 已落地 `m3_lease.py 675f983f` 并已签（`M2-FULL-L1-ACCEPT-lead.md 803e8f6d`）；独立复核链条闭合：我组 `pre 175ab618`（4 红，静默双 share `share_calls_after=2`）→ `after 8fdec7b6`（11/11）→ 变体 `5939c981`/`175ab618`（回红）；抛错路径三态不动；`chat_lease.py`/`_test_lease.py` 未动（`INSPECTOR-L1-REVIEW.md 66cf3aa5` §2–§4）。**真机臂 = 未做**（「不改 M4-C 读数」仅结构推断）。

### 2.2 L2 记账一致性（第二刀，可选；不阻塞 L1/P1）

- **判据 L2**：`detach(dst,lo,hi)` 未命中 `ranges` 时，现状仍 `eng.drop`（静默）。要求：未命中必须落 `unbooked_detach` 事件 + 计数（**不静默**）；strict 模式（默认 strict）抛 `LeaseError` 且**不 drop**。
- **读数**：stub 产物 `{case, keys_before, hit, unbooked, raised, calls_after}`。
- **通过**：未命中 1 例 ⇒ 计数=1、strict 抛、`eng.drop` **未被调用**；命中 1 例 ⇒ 计数=0、正常 drop。**红证明**：注入表漂移（先手工 pop 一条 `ranges` 再 detach）⇒ 变体（去掉检查）时 `unbooked=0` 且仍 drop ⇒ 断言红。
- **三级分母**：detach 调用数 / 命中数 / 未命中数。**不做**：不做自动修复/全表扫描。

### 2.3 P1 pinned 驱逐（零 GPU 可判；真机可选）

- **接口**：`evict_policy.select_to_evict(blocks, chat_len, n_ctx, policy=None, mount_cap=None, pinned=())` —— **新增关键字 `pinned`，缺省空集 ⇒ off/既有行为逐字不变**；`evict_order` 保持纯排序语义（不接 pinned），过滤只在 `select_to_evict` 内做。`plan()` 冻结签名**不动**。
- **pin 来源（不许猜）**：由调用方显式注入；产品侧建议取值 = `{s for s in range(1, N_SEQ) if leases.leased(s)}`（`m3_lease.py:59` 已有，`GuardedLeases` 继承），或 `from_manifest` 的 `declared`。**契约写明：pin 的对象是「被引用」，不是「重要」**；规划器/策略不得自己看引擎推断。
- **判据 P1**：① 混合集（3 pinned + 3 普通、超预算）⇒ `evicted` 非空且 `evicted` 与 `pinned` 交集为空；② **全 pinned + 超预算** ⇒ `evicted == []`、`over_budget_after == True`、`refused_reason == "all_pinned"`，调用方必须 `PlanRefused`（**不许静默降级继续**）；③ `policy="off"` 且不传 pinned 时，输出与现盘逐字段相同（RED/GREEN/PLAN-SELFTEST 回归）；④ 不发明阈值（`mount_cap=None` 即不启用）。
- **读数**：纯函数产物 `{blocks, pinned, policy, kept, evicted, over_budget_before, over_budget_after, refused_reason}`；三级分母：总块数 / pinned 数 / 被踢数（三个都报，缺一即读数无效）。
- **红证明**：① 变体删 pin 过滤 ⇒ pinned 出现在 `evicted`（断言红）；② 变体把「全 pinned」改成静默返回 ⇒ `refused_reason/over_budget_after` 断言红。③（可选，真机 1 轮）pin 一个已挂载块再触发 `reset` ⇒ `LeaseError` 且 cells 不变 —— 它证的是租约层，**不列 P1 必过项**。
- **未接上**：拿不到 `pinned`（租约表空/块未注册）⇒ 报「未接上」，**不许用空 pinned 冒充**。

### 2.4 S1 多序列（唯一必须 14B；前置裁定见 §3）

- **前置裁定（lead 必须先裁，否则判据不可执行）** —— 预算三方案：
  - **A 抬 `n_ctx`**（8,192 → 16,384）：要重测几何（51 cells / `[4045,4095]` / `CHAT_START=4096`）与显存；代价最大，长会话仍成立。
  - **B 同 `n_ctx` 内两段有界会话（我建议）**：冻结每会话轮数上限 N 与 chat_len 上限（按 10 轮 = 740 cells，两会话+块 ≈1.6k，留 2× 余量 ⇒ N ≤ 20）；**`chat_start` 不必改**（位置 per-seq）；改动集中在 `chat.py` 调度：第二对话 seq=1、块挂 seq 2..7、`ask(1,…)`、每会话独立记账；`planner.plan` 用 `budget = {n_ctx: N_CTX - resident_other, chat_len: chat_len_self}`（**不改签名**）。**（状态回填 21:55：本条设计已被 v4 冻结口径 `09cd7345cb333d29` 修正 —— 会话 seq 改为 **A=`0` / B=`7`**（`_place_slots` 写死 `start=1`，seq 7 天然空，helper/`m1`/`save` 零改动），块槽 `1..6` 不动；「第二对话 seq=1、块挂 seq 2..7」**作废**；`10 轮 = 666 chat cells`（`740` 是插 car 块后的 `n_tokens`，混了块，不是 chat 口径）；`chat_len` 按 `CHAT_LEN_CAP=1024` 预留、每轮校验实际增长。完整口径见 v4。）**
  - **C 两会话共享同一 chat 区**：不是真并发，只能测「块在多 seq 同时可见」；**不采用**（除非显式降级成子判据并明说）。
  - 三个方案都**不许静默降级**：超预算一律 `PlanRefused`。
- **S1 前提 P-1（租约表是唯一写路径；来自 L1 复核 §6b）**：L1 的保证域只有「经 `BlockLeases` 的挂载不重叠」——引擎侧外力（直接 `eng.share`/`drop`、`planner.py:66/:82`、`m2_v1`/`kvslots` 工具）**不在保护面**。因此 S1 的**所有**多会话 `share`/`drop` 必须走租约表；若某处必须直连引擎，则 S1 必须在同一次运行里断言 **「直接 `eng.share`/`drop` 计数 = 0（除租约表自身）」**，否则 L1 对多会话**失效**且不会报红。该断言列入 S1 必过项，不许以「反正没触发」代替。
- **S1 前提 P-2（replay 依赖表-引擎严格同步；来自 L1 复核 §6a）**：L1 新增的同块同区间重放分支**跳过 `eng.share`**（幂等）。当前产品三处 attach 不命中重放（`chat.py:310` 每轮重算计划、`:397`/`:604` 均 detach-before-attach，`:561`/`:593` 先删旧键），故现读数不受影响；但 S1 若复用重放（重复挂载、会话重启、跨轮复用同 `(seq,lo,hi)`），**必须先补「表-引擎一致性」判据**（引擎侧 cells 与 `ranges` 逐项对账），**或 S1 显式禁 replay**（`attach_replay` 计数 = 0 断言）。二者任选其一，不许两不选。
- **判据 S1（按 B 写；状态回填 21:55，v4 冻结口径 `09cd7345cb333d29` 为准）**：原文「A=seq0、B=seq1 **同时挂同一块集合**」**作废** ⇒ 修正为 **A=`seq0` 只挂 home（`seq1`→dst 0）、B=`seq7` 只挂 project（`seq2`→dst 7）、habit（`seq3`）只登记不挂（pool=3 / 挂载=2）**。**理由：同一集合下「专属块」是空集 ⇒ 交叉判据无定义（②a 只能空断言/恒假、②b 退化成模型复述抽奖）—— 这是判据不可执行，不是执行偏差。** 判据按修正后写：① 两会话各 `fact_ok` 命中自己块的事实（各 1 条，互不替代）；② 拆两层：**②a 结构层** `source_blocks`（= 实际选择并用于作答的块 seq 集，与 `mounted` 分开记）与对方专属块**不相交**（dry-run + 真机）、**②b 文本层** A 答案不含 B 事实、B 答案不含 A 事实（仅真机）；③ **公式写死** `n_tokens_self = Σ(本会话每轮 ask 增量)`、`pos_max_self = CHAT_START + n_tokens_self − 1`（A/B 同式独立；块的位置读数单列）；④ `cells_accounting` 按**每会话 ask 增量记账值**对账（`blocks + chat_A + chat_B = total`，**不许用 seq 读数替代**），且每轮 `chat_cells_self ≤ CHAT_LEN_CAP=1024` 否则 `PlanRefused`；⑤ `sha_stable` 仅真机臂（dry-run 记「未做」）。完整判法以 `docs/_work/M2-FULL-S1-SPEC-lead.md` **v4** 为准。
- **读数**：真机臂（`chat.py:47 MODEL` 已是 **14B**；几何 51 cells `[4045,4095]`、`CHAT_START=4096`）；零 GPU 前置：两套 `plan(blocks, 4096, budget)` 的几何断言 + `kvsim` 位置/字节模拟。
- **通过**：①–⑤ 全绿 + `exit 0` + `sha_stable` 同值。**红证明**：~~① 串话夹具（只 A 挂块、却让 B 答）⇒ 交叉断言红；② 同 seq/同 chat_start 夹具 ⇒ 几何断言红；③ 预算夹具（把 B 的 chat_len 记 0）⇒ 对账断言红。~~ **（状态回填 21:55：这三条红证已被 v4 的 R1/R2/R3/R4a/R4b/R5 取代（六条） —— 原①「只 A 挂块让 B 答」在零 GPU 下天然绿（空断言）作废，改为②a 注入 `source_blocks` 元数据；原③「chat_len 记 0」在 `plan()` 里只参与 refuse、不参与对账，红不了，改为 R3「记账少记 B 的 `chat_cells`」+ R5「删 CAP 校验」。完整见 v4 §5。）**
- **三级分母**：会话数（2）/ 挂载块数（v4：**2**，A:home / B:project；**登记 pool=3 另报，两个数不许混**）/ 交叉断言数（2 = ②a 结构 1 + ②b 文本 1；dry-run 只有 ②a，须写明「②b 未做」）。
- **未接上**：`n_seq < 2` 或拿不到第二对话 seq 的位置空间 ⇒ 「未接上」；**不许用共享 chat 区冒充**。

---

## §3 依赖顺序

| 顺序 | 件 | 依赖 | 为什么这个顺序 |
|---|---|---|---|
| 1 | **L1** 位置租约重叠校验 | 无（纯本地逻辑 + stub） | 零 GPU；是 P1 的**语义地基**（pin=「被引用」，而被引用只有租约表能答）；不依赖任何裁定 |
| 2 | **L2** 记账一致性（可选） | L1（同一文件、同一测试床） | 顺手第二刀；不阻塞 |
| 3 | **P1** pinned 驱逐 | L1（pin 取值可信）；`evict_policy` 保持 off 默认 | 零 GPU 可判；真机可选 |
| 4 | **S1** 多序列 | **lead 预算裁定（A/B/C）** + L1（多 seq 边界）+ **L1 复核两条前提 P-1/P-2（§2.4）** | 唯一动装置/调度的一件，放最后避免污染前两件的归因 |

- 与 M2 规划器契约：`plan(blocks, chat_start, budget)` **3 参不动**，多会话靠 `budget` 记账（`n_ctx_eff`）；`plan.py:6` 的冻结契约不受影响。
- 与 `chat_lease` 契约：**不改 API、不改 `sites` 事件格式**（M4-C 断言依赖 `seq/cells_after`）；`STRICT` 语义不动。
- 与「无淘汰」前提：`evict_policy` 默认 **off**、不接主路径（`kvmem/m2_visibility/m2_planner/RESULTS-RED.md:94/:143/:150/:170`）；P1 只加 pinned 过滤，**不把淘汰默认打开**。
- **S1 开工前置（两条，来自 L1 独立复核 `INSPECTOR-L1-REVIEW.md` §6；**21:55 v3 首修、22:15 升 v4**）：① **P-1 租约表唯一写路径** —— 多会话 `share`/`drop` 全走 `BlockLeases`；**判法改为计数等式**（v1 的「直接 `eng.share`/`drop` 计数 = 0」不可判：stub 只见总调用、分不出调用者）：`eng.share 次数 == events 中 attach 数`、`eng.drop 次数 == detach 命中数`；dry-run 用 stub、真机臂用 `CountingEngine` 透明代理跑同一等式。② **P-2 replay 一致性** —— S1 显式禁 replay（`leases.events` 中 `attach_replay` 计数 = 0）。**P-1 与 P-2 实为独立**：replay 分支 `_note("attach_replay")` 后直接 `return`，既不发 `eng.share` 也不发 `attach` 事件（`m3_lease.py:84-88`）⇒ 计数等式仍成立、P-1 不受 replay 影响。两条都是 **S1 的准入条件**，缺任一条时 S1 读数**不得签字**（与「真机臂必须 14B」「超预算必须 `PlanRefused`」同属硬前提）。完整见 `M2-FULL-S1-SPEC-lead.md` **v4** `09cd7345cb333d29`。

---

## §4 可复用资产（准确 sha + 用途）

| 类别 | 资产 | 用途 |
|---|---|---|
| 规划器 | `planner.py 01507f6b`（`plan:18`/`insert_ops:66`/`apply_insert:82`/`check_entry:59`）、`plan.py 74da0732`（`:46/:54/:60/:75/:80`） | S1 的预算/几何；**不改**其语义 |
| 套件 | `RED-SUITE 13771a2d`（9 例，`all_as_designed=True`）、`GREEN d3485eb2`（18 断言 + 4 契约，`all_green=True`）、`PLAN-SELFTEST a0c0782b`（12/12 + 3 必红，`eviction` 字段即 §1.1 证据） | 回归基线 |
| 错法 | `fake_planner.py 3f874eab`（六种故意写错 + 一种「位置对字节错」）、`kvsim.py 2a287711`（`SimNoEffect:86` 是假绿教科书形态） | 红证明的机制来源 |
| 租约 | `m3_lease.py 675f983f`（L1 后；L1 前 `7a838d0a`，红证对照用）、`chat_lease.py 619a0432`（`GuardedLeases`/`from_manifest`/`sites`/`report`/`STRICT`）、`m3/_test_lease.py`（stub，零 GPU；我现跑 0 failed）、`m3/_test_lease_overlap.py 7a92480b`（L1 11 例）、`m3_criteria.py`（判据纯函数共享，纪律 14）、`m3_unit_falsifiers.py`（单因子：`proven/not_alone/no_flip`） | L1/L2 的改造对象与测试床 |
| 真机 | `out/M2-ACCEPT-r2.json c95e0b7c`（判据 + 红证 + `r1_comparison` + `selection_layer` 模板）、`chat_lease/refusal_probe.py`（真引擎拒绝证据）、`run_site3.py`（绿/红/删除臂） | S1 的臂结构与红证写法 |
| 淘汰 | `evict_policy.py aa7cbf3f`（off/lru、不发明阈值）、`tools/kvslots.py 2c6984a7`（4 槽 LRU 先例）、`tools/m2_v1.py`（确定性 LRU + `pool.evict` 先例） | P1 的策略骨架与先例 |
| 格式 | `mine/inspector/M3-PREREG.md 3e4f465b`（**史料**，回填件） | 预登记版式先例 |
| 过程观测 | `chat_lease/` 下 **33 份 JSON** | **不是判据**（`PROGRESS:2018` 记 16 份是快照，现盘 33） |

---

## §5 不做什么（本预登记范围外）

- M5 判定器族、M4 写入链、M1.8 检索裁判（**已冻结，禁动**：`analysis.py 49e91c7b`/`retrieval.py 43f66019`/`evidence.py dccf7f01`/四阈值/两版本号）。
- E10 编码层可见性（`PROGRESS:133` 已定位未修）。
- **`gaps` 的来源**（`PROGRESS §13.4` 末段：现状无人回答；`plan()` 保持「gaps 只作输入」，不许规划器自己推）。
- 跨布局对照臂 `M2S3_car_back ↔ no_car`（M2 验收未采用为签字前提）。
- 约 4,000 的「挂载块上限」档（`kvmem/m2_visibility/m2_planner/RESULTS-RED.md:143` 已删，无出处）；**不发明任何新阈值**。
- 不动 `kvmem/chat.db`（`237d8e1f`）、不动冻结阈值与版本号、不重建索引。
- **不把 `evict_policy` 默认打开**；不做「pin 是引擎特性」的假设。
- 本草案不写「M2 完整 通过/验收」。

---

## §6 成本与「是否要 14B」

| 件 | 零 GPU | 14B 真机 | 说明 |
|---|---|---|---|
| L1 | **1 轮**（stub + 变体红证） | 0（可选回归：M4-C 绿臂 1 轮） | 判据落地即可红/绿，无需模型 |
| L2 | **0.5 轮** | 0 | 同一测试床顺手 |
| P1 | **1 轮**（纯函数 + 变体） | 0（真机 reset 拒绝证据可选 1 轮，非必过） | 契约改 `evict_policy`，默认 off 不变 |
| S1 | 1 轮前置（双 plan 几何 + kvsim） | **2–3 轮**（双会话）；若选方案 A 再加装置重测 1–2 轮 | **唯一必须 14B 的一件** |

- **模型现状**：`tools/chat.py:47 MODEL = D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` —— **产品路径已经是 14B**，S1 不需要「换模型/接模型」，需要的是**调度与预算记账**。7B 线已冻结（`PROGRESS:145`），任何 7B 结论不外推。
- 结论：**L1/L2/P1 全部可以零 GPU 把判据落地并做红证明；只有 S1 必须上 14B**，且它需要 lead 先裁预算方案。

---

## §7 先做哪一件 + 理由

**先做 L1（位置租约重叠校验）。**

1. **零 GPU、改动局部**：只动 `m3_lease.py:63-76` 一个函数 + 新增断言产物；红证明是「删检查 ⇒ 不抛」的教科书形态，机械可复现，不依赖装置、不依赖裁定。
2. **它是 P1 的语义地基**：`PROGRESS:761/:771-776` 已实测「引擎不拒绝 reset」⇒ pin 只能是外层租约表职责；而租约表当前**只记账不校验**，「重叠静默覆盖」会让 pin/驱逐的前提失真（谁被引用、引用到哪一段都不可信）。
3. **这是唯一「地基级且不需要 lead 裁定」的一件**：M4-C 只对 site3 证到后果级、**位置冲突从未测过**，是 M2 完整里最薄的一块。
4. **归因风险最低**：L1/L2/P1 连做都是零 GPU 逻辑变更；S1 最后做，避免装置变更把前面读数搅浑。

**给 lead 的两项裁定请求（阻塞 S1，不阻塞 L1/P1）**：
- **(i) 预算方案**：A 抬 n_ctx / **B 同 n_ctx 两段有界会话（建议）** / C 共享 chat 区（不采用）。附带：每会话轮数上限 N 取多少（我按 10 轮实测 740 cells 建议 **N ≤ 20**，两会话+块 ≈1.6k cells，2× 余量）。
- **(ii) pin 来源**：裁定为「调用方显式注入 + 产品侧取 `leases.leased()`」；**不要让规划器/策略自己看引擎**（那会把「pin 是引擎特性」的错直觉请回来）。

---

## §8 四态与只读自证

- **M2 完整 = 未做**（三件：pinned 查无 / 多序列单会话写死 / 位置租约记账不校验）。
- **本草案 = 已做（草案）**：它本身不是判据、不能当验收依据；L1/L2/P1/S1 的判据**尚未落地**（未做）。
- **只读自证**：本文件未改任何代码/产物/数据库；我唯一的运行动作 = `python -X utf8 kvmem/m2_visibility/m3/_test_lease.py`（零 GPU、stub、只打印，**不写产物**）与本文 shas 的现算；**未跑 GPU、未跑测试套件**（除该 unit）、未动 `kvmem/`。
- **复验方式**：§0 shas 现算；§1 每条 `file:line` 直接 grep；§2 构造在写断言时逐条落代码；§3–§7 是设计判断，可被 lead/executor 反驳，反驳须给替代判据或反例。

---

## §9 与 executor 初稿的差异（采用并修订记录）

**已修的两处已知缺陷**：① 初稿 §1.1 表格重复一行 `RESULTS-RED.md` → 已删重复；② 初稿 `:159` 裸文件名「`RESULTS-RED.md:94/:170`」→ 全文改为带目录 `kvmem/m2_visibility/m2_planner/RESULTS-RED.md`。

**事实更正 9 处**：`chat_lease.py` 行号（`:45→:47`，`:212→:208`，`:239→:218`）；`evict_policy.py` 行号（`:32→:31`，`:45→:41`）；`chat_lease/` JSON 数量（16→**33**，并标 `PROGRESS:2005` 是快照）；`chat.py:47` MODEL **已是 14B**（初稿把 14B 写成前置缺口）；**多序列预算结论**（初稿「第二段没有位置」→ 现改为「池子够、缺分配/调度/轮数上限」，见 §1.2④）；补 `m3_lease.leased():59`（pin 现成来源）；补 `detach` 未知键仍 `eng.drop:81`；补 M4-C 四站覆盖细节与 `:73-81/:112-113` 行号；补 `kvslots.py`/`m2_v1.py` 两处旧淘汰先例；补 `m3/_test_lease.py`/`m3_criteria.py`/`m3_unit_falsifiers.py` 复用件与 `mine/inspector/M3-PREREG.md` 回填事实。

**结构未变**：六问顺序（现状/判据/依赖/复用/不做/14B）+ 末尾「先做哪一件」保留；初稿 `9855df9b` 仅作输入，不作判据。