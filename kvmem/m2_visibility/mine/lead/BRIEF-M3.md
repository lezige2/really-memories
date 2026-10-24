# BRIEF · M3 块生命周期管理器（排队，M5 落盘后自动开工）

2026-10-25 ｜ 依据 `STATUS-REPORT.md` §4.3 原文 + 队长取证（下面「已查清的事实」）

## 一、Goal
把 M3 的三件事做成可测的：① pin/refcount ② 文件只读永不回写 ③ cell 池余量监控；
并通过 MD 的原始验收：**attach/detach 50 轮，`pos_max`、answer、cell 占用三者稳定，无单调上升**。

## 二、已查清的事实（队长取证，直接用，不要重复摸）
- **attach 的现成实现**：`tools/chat.py:208-212` → `eng.share(i, 0)` → `llama_memory_seq_cp`，注释写明「refcount only, zero copy」。
- **detach 的现成实现**：`tools/session_state.py` 走的 detach-before-save：`quiesce → detach → save chat → manifest → reattach`；
  detach 用 `seq_rm(chat, 块区间)` 摘引用。**必须先摘引用再移动**（L7 陷阱 2）。
- **MD §9.1 #6 的现状**：`session_state.py:6` 原文——「A ledger would push token semantics into `seq_cp` (today a pure refcount); detach does the opposite」。
  也就是说 token 账本**是被有意放弃的设计**，不是漏做。你的任务是**定量它什么时候会撞**，不是把它补上。
- **MD 已证伪的说法**：原稿「再旋转一次即可，可逆」——L3b 显示约 10 次往返后数值就坏。所以文件只读不是保守，是必需。

## 三、Boundary
新建 `kvmem/m2_visibility/m3/`，产出全放这里（驱动、run json、表格、README）。
**不得修改**：`tools/m2_visibility_probe.py`、`tools/chat.py`、`tools/session_state.py`、DLL、`kvmem/m2_v1_14b/` 下的块、`m2/` 与 `m5/` 已交付文件。
若要改 `session_state.py` 加 pin 逻辑 —— **不许**。用外层包装实现 refcount 表，并说明为什么不动原文件。

## 四、Constraints
1. 14B + DLL `9edbafa1`（实测并记录）；`kv q8_0` / `n_ctx 8192` / `n_seq 8` / `-ngl 99` / `n_predict 64`；
2. **一次引擎加载跑完 50 轮**，不要每轮重载（重载会掩盖泄漏，也会掩盖退化）；
3. 每轮记录：轮次 / `pos_max` / cell 占用 / 本次答案 / 块文件 sha256；
4. 答案正确性抽查点：第 1、25、50 轮（三问全问，或至少问住址那一问）；
5. 跑前记 free VRAM；跑完记耗时。

## 五、Acceptance Criteria（MD 原文 + 落地判据）
| # | 判据 | 怎么判 |
|---|---|---|
| 1 | 50 轮后 `pos_max` 稳定 | 无单调上升趋势（给出逐轮序列与首末值）|
| 2 | 50 轮后 cell 占用稳定 | 同上；给出余量 |
| 3 | 50 轮后 answer 正确 | 第 50 轮三问仍全中 |
| 4 | 块文件未被回写 | 前后 sha256 逐个相同 |
| 5 | pin/refcount 生效 | 块被引用时对源 seq 执行 `reset` **必须失败或失败关闭**，并把实际行为记下来 |
| 6 | token 账本缺口定量 | 说明在什么条件下 `seq_cp` 不追加 token 会出问题（MD §9.1 #6）；做不出定量就写「未测出」 |

## 六、Required Evidence
1. 50 轮逐轮表（轮次/pos_max/cells/answer 前 40 字）；
2. 首末块 sha256 对照；
3. 第 1/25/50 轮完整答案原文；
4. 判据 5 的实际行为（成功/拒绝/崩溃，原样记录，不许润色）；
5. 一条可复制命令；
6. 结论按四词写：未检验 / 实验无效 / 未测出·欠功率 / 无效应。**「稳定」必须有逐轮数据支撑，不许只给一句「通过了」。**

## 七、Risks（预先说明，免得事后解释）
- 50 轮 attach/detach 若出现退化，先怀疑**位置移动**而不是 attach 本身（L3b 说的是往返移动）；把两者分开测；
- 若中途崩溃，**不要静默重试**：把崩溃前最后一轮的完整状态记下来，那本身就是结果；
- 不得为了让表好看而调整轮数或判据。