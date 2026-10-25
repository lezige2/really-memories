# M2 规划器 · 状态（2026-10-25 19:12，executor）

> **状态 = 已实现 · 未验收。**
> 不写「通过」。真机验收臂未跑（3–5 块并发 / 第 10 轮插入 / 未参与块 0 字节变化 / `fact_ok`），另单。

---

## 1 盘面事实（先于任何结论）

`kvmem/m2_visibility/m2_planner/` 的一簇来自 **2026-10-25 13:04–13:42**，此前**未入库**
（`git status` = `??`、`git ls-files` 空、HEAD `f285640`），也**没有 `_before/` 与 REGISTER**。
本单按 lead 裁定只做**补治理**：不改内容、不重写、不追认签字。

- 已入库留档：`planner.py` `4162661cc04182e8` · `test_planner.py` `20059c5735733445` ·
  `red_suite.py` `1786ade212ad5e90` · `fake_planner.py` `3f874eab06200c99` ·
  `kvsim.py` `2a28771133dd1571` · `assertions.py` `ef74d2dfa12702d4` ·
  `FIELDS.md` `c096dccd0913ba52` · `RESULTS-RED.md` `16a4174c5f940d6c`(33,456 B) ·
  `out/GREEN-SUITE.json` `d3485eb29a97e5cb` · `out/RED-SUITE.json` `13771a2d633a8bb4` ·
  `out/ORDER-EVIDENCE.json` `259504f4baf675f8`
- 逐份副本与逐文件 sha16 台账：`_before/<name>@<sha16>` + `_before/REGISTER.json` +
  **`LANDED-m2planner.json`**（两次采样一致才写；本文件不登记自身 sha16 —— 自指恒假，见
  `RESULTS-RED.md` §22.3）。

### 1.1 对 `RESULTS-RED.md` §22（旧签字）的加注

**不改 §22 原文**，只在这里加注：

> **签字时基线 `32c68080b8f52d63`（188,769 B / 2,465 行）不在工作区**；现行
> `PROGRESS-AND-ROADMAP.md` = `8dc4ba252c2fa9a5`（195,585 B），且其 §13.4:1797 与
> `FEATURES.md:171` 仍写「未实现」。**实现是真的，台账与文档同步是缺的**
> ⇒ **M2 现行状态 = 已实现 · 未验收**，不追认 §22 的「M2 通过」。
> 另：§22 的签字口径依赖「域内四条（S1/S3a/S4/S5）全绿」，而同一份文档 §7（`:150`）把
> 淘汰列为非目标、§8.3（`:170`）把 S2↔S6 的红**结构耦合**归结为「**无淘汰**」前提 ——
> 这两条前提在下面第 4 节被显式限定，不再隐含。

---

## 2 已实现、可复算的部分（零 GPU）

| 文件 | 作用 | 判据形态 |
|---|---|---|
| `planner.py`（旧，不改语义） | 位置计算 + `insert_ops`/`apply_insert`/`check_ops` | `test_planner.py` 18 条全绿；`red_suite.py` 9 个必红全红 |
| **`plan.py`（本单新增）** | **冻结接口薄适配** `plan(blocks, chat_start, budget) -> [(seq, target_pos)]` | `selftest_plan.py` F1/F2/F7 |
| **`evict_policy.py`（本单新增）** | 淘汰策略：**独立、默认 `off`**、不接主路径 | F9/F10/F11 |
| **`selftest_plan.py`（本单新增）** | 适配层 + 淘汰的零 GPU 单测 | 产物 `out/PLAN-SELFTEST.json` |

本单复跑（我跑的，不是转抄）：
`python test_planner.py` ⇒ rc=0、`all_green=True`（18 条断言）；
`python red_suite.py` ⇒ rc=0、`all_as_designed=True`（9 个必红全红）；
`python selftest_plan.py` ⇒ rc=0、**12/12 GREEN + 3/3 必红 FIRED**、`invariant_failures=[]`。

---

## 3 冻结接口的口径（本单唯一新增的对外契约）

```
plan(blocks, chat_start, budget) -> [(seq, target_pos)]
```

- `target_pos` = **`pos_hi`（最大占用位）**；`base = target_pos - cells + 1`；
  `repos_local` 的 `delta` 只接受 `base`（`FIELDS.md`：「一个词指两样东西」是上一版的风险源）。
- `blocks` 条目：`{seq, cells, key?, gap?}`。`key` = `distance_key`（调用方给）；
  `gap` = 该块下方留空，**只作输入**（缝宽来源仍未定义，`PROGRESS:1799`）。
- 输出**先远后近**；空输入 ⇒ `[]`；放不下 ⇒ `PlanRefused(reason)`，**不降级**。
- `budget`：`{n_ctx, chat_len}` 必填；`bytes_per_token`/`pool_bytes` 可省，
  省掉按恒等式补齐（`pool_bytes = n_ctx * bytes_per_token`）。**预算只有一档**：
  `pool_bytes / bytes_per_token = 855,638,016 / 104,448 = 8,192 = n_ctx`（同一个约束的两种写法）。
- **挂载上限 ≈4000 那一档不实现、也不发明**：`RESULTS-RED.md:143` 记「已删除（无确切值/无出处）」。
  task-15 第 1 条里那个档按 lead 裁定**作废**。

---

## 4 淘汰：独立策略，默认 off（把签字版前提写成明文）

- 签字版把淘汰列为**非目标**（`RESULTS-RED.md:150`、`M2-PLAN.md` §4）。
- 签字版 S2↔S6 的**结构耦合**以「无淘汰」为前提（`RESULTS-RED.md:94`/`:170`）：
  「在『无淘汰』前提下，预算越界必然伴随拒绝义务」⇒ 主路径一旦踢块，这条读数就要重新解释。
- 因此：`evict_policy.evict_order(blocks)` 默认返回 `[]`；只有显式 `policy="lru"`
  才按「`last_used` 最旧先 → `key` 大的先 → `seq` 大的先」给出踢块顺序，
  且只做 `seq_rm`（摘引用），**文件不动**；阈值由**调用方给**（`mount_cap=None` = 不启用该档）。
- `plan()` **不读** `mount_cap`、也不淘汰（F11 断言：传了也忽略）。

---

## 5 差什么才算验收（真机臂，另单）

1. **3–5 块并发**：`plan()` 的布局在真机上 attach 后读回位置/`cells` 与规划一致。
2. **第 10 轮插入**：`insert_ops` 四步在真机上按序生效（`drop` 读回不可见 → `repos_local`
   位置层 +n 且计数层不变 → 新块可见 → 既有块重挂可见）。
3. **未参与移动的块 0 字节变化**：跨两次布局比 `block_bytes` 的 `pre_eq`/`post_eq`。
4. **`fact_ok`**（事实关键词命中，不是答案质量）。

真机臂设计一句话（给 lead 排期用）：**同一对话现有 3 块 → 插第 4 块 → 插前后对未参与块逐 slot
比 `block_bytes`（`pre_eq`/`post_eq`）+ 每块 attach 后读回 `(base, pos_hi, cells)` 与 `plan.py` 输出
逐条比 + 插入后问一句含新事实关键词的问题只判 `fact_ok`；全程一个 seq 一个引擎进程，不重跑已验收的 M3。**

---

## 6 本单边界（自证）

- 未跑 14B / 未加载引擎（`selftest_plan.py` 只 import 纯函数模块；无 `kvshim`、无 `kvslots`）。
- 未改 `tools/chat.py`、未改 `planner.py` 语义、未改 M5/M4/M4C 产物或台账、未写 `docs/_work/`。
- 未写「验收通过」；`out/PLAN-SELFTEST.json` 里 `acceptance_claim = "none"`。