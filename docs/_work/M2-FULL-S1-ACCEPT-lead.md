# M2 完整 · S1 定稿（lead · 2026-10-25 23:05 本地）

> 冻结晶口径：`docs/_work/M2-FULL-S1-SPEC-lead.md` **v6 `ae2d88ad5ecc25d3`** · 独立复核：`docs/_work/INSPECTOR-S1B-REVIEW.md` `058d29dca281ea47` · S1-a 判决 `M2-FULL-S1A-ACCEPT-lead.md` `4d80300d88e84204`
> 交付：`tools/chat.py` `cb70be52eef253fa` → `b9010e9c2a3c6a13`（v5）→ **`288d2d85720359e0`**（72,345 B，v6）

---

## 0 一句话

**S1（两会话 / 多序列）= 通过**：同一 `n_ctx=8192` 里，A（`seq 0`）挂 home、B（`seq 7`）挂 project，各跑 10 轮、**各命中自己的事实 10/10**、**交叉不串 2/2**、**账目合计 1,155 ≤ 8,192 且引擎实测对得上**、跑前跑后 sha 稳定、**share/attach 计数等式与禁 replay 在真机上成立**。**S1 是 M2 完整里唯一必须上 14B 的一件，也是"多序列"第一次真机落地。**

## 1 真机读数（14B q8_0，`n_ctx=8192`，`n_seq=8`，A→B，各 10 轮，两采样间隔 40 s）

| 项 | A（`seq 0`） | B（`seq 7`） |
|---|---|---|
| 挂载块 | home 21 cells @ `[4075,4096)` | project 18 cells @ `[4632,4650)` |
| `chat_start` | **4096**（`CHAT_START`） | **4650** = `4096 + n_chat_A(536) + 18` |
| `n_tokens` / `pos_max` | 536 / **4631** = 4096+536−1 | 580 / **5229** = 4650+580−1 |
| 事实命中 | `广陵路` **10/10**（字面亦 10/10） | `3月14` **10/10**（去空白；字面 0/10，实答「3 月 14 日」） |
| 对方事实出现 | `[]`（10 轮全无） | `[]`（10 轮全无） |
| 预算 | `n_ctx_eff=8192`、预留 1024、未触发 | `n_ctx_eff=7656`（=8192−536）、未触发 |

- **④ 账目**：`blocks 39 + chat_A 536 + chat_B 580 = 1,155 ≤ 8,192`；`engine_match=done`（`measured_blocks=39`、`sum_accounted=sum_incr=1,116`）。
- **⑤ sha_stable**：7 文件（`analysis.py 49e91c7b` / `retrieval.py 43f66019` / `evidence.py dccf7f01` / home / project / `chat.py 288d2d85` / spec）跑前跑后同值；habit「只登记未挂、不检」。
- **P-1a**：`share=2 == attach 事件=2`（R4a 红证：绕过租约直接 share ⇒ 红）；**P-1b**：`drop=0`、detach 命中=0 ⇒ **零实例、`not_triggered`、不可判（不记通过）**；**P-2**：`attach_replay=0`（R4b 红证：连续 attach 触发 replay ⇒ 红而 P-1 仍绿）。
- **CAP**：主臂 536/580 未触发；16 轮构造 1072>1024 ⇒ `refused=true / refused_reason="chat_len_cap"`、**exit 2**；R5 红在 case 级（`M_CAP_refuses`）。
- **两采样**：`readings_identical=true`（answers/checks/counters/sessions/accounting/budget/per_round 全同）⇒ **14B 随机性未影响任何判据**。

## 2 判据逐条（v6 §3）

| # | 判 | 依据 |
|---|---|---|
| ① | **通过** | A 10/10、B 10/10（norm 口径）；`other_fact_in_any_round=[]` 两侧 |
| ②a | **通过（接线回归，不计交叉分母）** | `source_blocks ⊆ mounted`；恒真性质已在 v6 认定 |
| ②b | **通过** | A 不含 `3月14`、B 不含 `广陵路` ⇒ **2/2**（交叉分母 = 2）|
| ②c | **通过（dry-run 零 GPU）** | selection 文本 A 16 字 / B 43 字，互不含对方事实 2/2 |
| ③ | **通过** | 两会话 `pos_max` 各按 `chat_start_self + n_tokens − 1` 成立；块尾紧邻 chat 起点、`hi` 排他 |
| ④ | **通过** | 1,155 ≤ 8,192；`engine_match done`；每轮 ≤ CAP |
| ⑤ | **通过** | 7 文件跑前跑后同值（仅真机臂判，dry-run 记未做）|
| P-1a / P-1b / P-2 | 通过 / **未触发·不可判** / 通过 | 见上 |
| 默认路径 `m1` 真机 | **未通过（G4 单列，非 S1）** | 新=旧同一 `KeyError 'conv_2026-10-25#L5' @ chat.py:598`；`m1 --explain` 新旧**逐字节同**（654 B / `3e8aae60685d2e55`）|

## 3 几何这条线（v5 错 → v6 对，值得记档）

v5 的 `end = CHAT_START − i*SLOT` **是 lead 写错的**（`_place_slots` 实际是 `CHAT_START − (i−1)*SLOT` 且 `hi` 排他）。真机实测把两条硬约束钉死：
1. **块尾必须紧邻本会话 chat 起点**，中间留空格 ⇒ 引擎 decode 直接拒绝（块 `0..11` 后 `pos=12` 命中、`pos=13` 空）；
2. **`attach(seq,dst,lo,hi)` 的 `hi` 是排他上界**（传 `end−1` 丢最后一格 ⇒ 顶对齐也红）。

v6 的解法不是"清单个块"（那会改 ④ 的"块常驻"语义），而是**游标顺延**：B 的块放在 A 的 chat 之后、`chat_start_B` 顺延到 B 块之后 ⇒ 两块都常驻、无重叠、两会话各自连续。**A 的 `0..4074` 大空前缀被证明可接受**（B 同构）—— 这条是"引擎允许前缀空、不允许中间空"的直接证据。

## 4 四态

| 项 | 判 |
|---|---|
| S1 零 GPU 层（S1-a） | **通过**（判决 `4d80300d88e84204`，四条折扣）|
| S1 真机层（①/②b/③/④/⑤/P-1a/P-2/CAP）| **通过** |
| ②c | 通过（dry-run）|
| ① 的**字面**口径（B 侧）| **未通过字面**（实答「3 月 14 日」）⇒ 判据按 v6 **去空白**口径判过；**字面口径记"不成立"** |
| P-1b（drop 等式）| **未触发 / 不可判**（零实例）|
| 默认路径 `m1` 真机 | **未通过（G4 既有，非 S1）** |
| 真并发 | **未做**（预登记明确非目标：两段**顺序**跑）|
| 不可签 | 「S1 是真并发」·「P-1 整体可判」·「字面口径成立」·「M4-C 绿臂可重跑」（G4）|

## 5 缺口与待补（非读数层）

- **G3（升级）**：`chat.db` 派生库、**重建非确定且可复现**（4 个独立进程重建同一 `237d8e1f` 得到 4 个不同 sha，内容表不变）。温故：`tmp_db/chat@237d8e1f.db` 实际 `2d3bae59`（跑前 `237d8e1f` + `_run_m1_regression → cmd_m1 → chat.py:521 build_index` 重建 `attr`/`value_kind`）；**逐表逐行 8/10 相同**；5 个 DB 状态上 `selection` 逐字段全同 ⇒ **读数可归因**。
- **待落账 7 条非读数补正**（task-32，判据不变）：F1 台账/产物 DB 标签（before/after）· F2 真机产品 `run.notes` 静态文案与 `checks` 冲突 · F3 判据床/落账/4 脚本并入 `module_shas` · F4 `frozen_numbers.geometry` 的 `+18` 笔误 · F5 `red_proofs.R5` 写 `red_kind:"case"`+「主臂 CAP 未触发绿」 · F6 G3 可复现非确定入档 · F7 `_StubEngine` 位置偏离（下一刀搬测试床）。
- **G4**：`m1` 真机 `KeyError`（selection 命中 `conv` 源但无块行）⇒ **M4-C 绿臂回归链暂断**，另开单修。

## 6 签署

| 项 | 内容 |
|---|---|
| 签署人 | lead |
| 签署 | **S1（多序列）= 通过**（2026-10-25）—— 两会话各自命中 10/10、交叉 2/2、账目 1,155≤8,192 且引擎实测对上、sha 稳定、P-1a/P-2 真机成立、CAP 越界必拒、两采样读数完全一致；`m1` 默认路径未通过属 **G4 既有缺口**，S1 不背；P-1b 零实例记不可判 |
| 可复算 | 产物 ⇐ `S1-real.json 3df8d70bec1c5b94` / `S1-real-2.json 39b7f9dee736d86b` / `S1-real-smoke.json a067294a524e42c3` / `S1-real-default-regression.json 39aa2505d74724a4` / dry `S1-dryrun f2ae36b3` / `S1-cases-main c9211e5d`；台账 ⇐ `LANDED-s1-real.json 98bbf28b65d1de19`（+ 待补正 addendum）；复核 ⇐ `058d29dca281ea47`；口径 ⇐ `ae2d88ad5ecc25d3` |
| 待补正 | §5 的 7 条（非读数层）；**补正不落 ⇒ 本判决台账坐标按原 sha 读、判定不变** |
| 下一步 | **M2 完整 收口**（`M2-FULL-FINAL-lead.md`）→ 另开 **G4** 修复单 |
---

## 7 补记（2026-10-25 23:55，外部审计二轮后；**不改 §1–§6 的判定**）

1. **②b 的口径方向要写明（纪律 26）**：B 侧「3月14」**字面 0/10**、**去空白 10/10**；v6 采用去空白口径，**方向 = 放松（post-data，看到真机答案后才定）**。反事实：按字面口径 B 侧**不成立**。§4 已列"字面口径不成立"，此处补**方向标注**，防止下一轮被读成"默认口径就是去空白"。
2. **`two` 路径不经过 `E.decide`**：`grep -n "E.decide" tools/chat.py` 只有 `:541`（`cmd_m1`）；S1 走 `_two_selection_texts`/`source_blocks`。⇒ **G4a-2（决策面把不可挂载的 selection 当 `memory_hit`）不影响 S1 任何读数**。
3. **`kvslots.ask` 把 `n<0` 折成 `""`**（审计查出）：S1 的 ① 是"含事实"判据，空答=未命中 ⇒ 偏保守不会假绿；但"引擎拒绝 vs 模型没答出"不可分，P2 必修，修后本判决补"空答语义可区分"，**判定不变**。
4. **`m1` 链的后续（G4a-2 / G4c）不并入本判决**：M4-C 绿臂的 `loads` 顺序已因 M1.8 查询侧变更而变（`project→seq1, profile→seq2`），属**另一条线**，本判决不引用 `m1` 任何读数。