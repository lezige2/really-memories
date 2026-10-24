# Stage 1a 验收 · 权威源注册表（不变量落地）

验收人：inspector ｜ 2026-10-25 ｜ 判据依据：SRC-CRITERIA.md（I1-I6 / S1-*）
纪律：不在原库上动手；全部负向测试在 chat.db 的**副本**上做，用真实 API 触发。

## 1 我跑出来的（不是转述，每条都有代码原文或返回值）

- **幂等**：同 name 同 text 调 put_source ⇒ `id=1, created=False`，行数 2 → 2（不变）。
- **拒隐式修订**：同 name 不同 text ⇒ `SourceConflict`，消息里同时给出旧 hash 与新 hash（d3e57f11… vs 4097f…）。
- **拒空文本**：`ValueError: refusing to store an empty text`。
- **DB 级不可变（比 1a 自报更严，新事实）**：直接 `UPDATE memory_source SET text=...` 被 SQLite **触发器**拒绝——
  `IntegrityError: memory_source.text is immutable: insert a new row instead of editing history`（触发器名 `memory_source_text_is_immutable`）。
  即 I3/I5 不只是应用层约定，库层面就改不动。
- **fail-closed 是真的**：副本上 `DROP TRIGGER memory_source_text_is_immutable` 后把 text 追加「【篡改】」而 hash 不动，
  则 `get_source` 与 `assert_unique_texts` **双双**抛 `SourceHashMismatch`（消息：stored aa9769ad… != sha256(text) 763fa338…）。
  我另核了它的负向测试代码（check_registry.py:130-144）：copy → DROP TRIGGER → 篡改 → 断言抛错 ——**不是空转断言**。
- **读前重算的实现**：`get_source` 取最新行后调 `_verify_row(row)`，后者 `raise SourceHashMismatch(...)`，**不是 warning**；
  模块 docstring 亦写明「there is deliberately no try/except around it anywhere」。
- **I1 唯一副本**：`assert_unique_texts` 对同 hash 出现两次即抛错（代码原文已核）。

## 2 (i) 「消融库命中 0 的原始分数」——它给的答案比我要求的更好，我认

代码依据（tools/retrieval.py::_search_one）：
- 命名属性门在**打分之前**：`allowed = {sid ... if A.property_holds(txt, want_prop, scope)}` → `if not allowed: return []`，
  `_bm25(...)` 出现在这段**之后**。⇒ 消融库里没有任何源声称 plate 属性 ⇒ 直接弃权，**根本没有分数可报**。
所以 `hit=0 / top=null / top_score=null / value_gate.abstained=true + why` 是**正确且更可审计**的记录形态；
一个 null 配上"为什么 null"的代码路径，胜过一个语义错位的数字。我原条件作废，改判为**已满足**。

## 3 (ii) 锚点重锚（我自己重算，不采信二级汇总）

| 产物 | 我重算 | 结论 |
|---|---|---|
| run_m5_grounded.json | **d97cdfdcbd6c6d3d** | 新锚，M5 通过结论重新锚定于此 |
| run_m5_fix_compare.json | 5f7c196a32a659a6 | 有效 |
| m5/m5_ground.py | 86b7c501ab9904aa | 有效 |
| _before/m5_ground_preR12.py | ea749781368c798e | 有效 |
| m4_memory.db / run_m4_verify.json / run_m4_write.json | 817a66e45a4e3594 / bdf392e8f9a672a7 / 6408d8e2ecdf6ee5 | M4 三锚未动，M4「通过」继续有效 |

- **作废**：`dd8703d1`（我上一轮认定，因新增 retrieval_probe 字段重跑而失效）；`5cd106ee`（更早，我未见过该产物 ⇒ 标"作废、未经我复核"）。
- **重新锚定后我重验了新产物本体**（不是只换标签）：acceptance A–E 全 true、plate_main=supported、plate_ablated=unsupported、
  paired both_pass=true、`retrieval_probe` 已在 mount_evidence、undecidable 带 input_origin+synthetic、quadrants 里已有 **d_extraction_symmetry**（我要求的对称性自检）。

## 4 「json 装不了自己的 sha」这个约定 —— 认，但要三条

1. 权威值必须有**产物之外的落点**（README 章节或验收方产出的锚表）；当前 delivery_anchor 的 note + §19.10/19.11 满足。
2. `invalidated_anchors` / `*_previous_run` 必须**只追加**，每条带 (old_sha, new_sha, 原因, 时间) 四元；
   否则"previous"每跑一次就被覆盖，链条断了就再也拼不出来。
3. 验收结论里的锚值**以验收方重算的为准**，json 里的 previous 只作旁证（本轮即如此）。

## 5 Stage 1b 的前置要求（会动 M4 锚，预先说明）

- 1b 会改 `m4_memory.db` ⇒ **M4「通过」按规则过期**，我会重验而不是沿用。
- 重验时除既有 16 键外，我要看 C4 三条：① 层 2 每行 `registry_source_id` 非空；② 行文本是注册表文本的**逐字子串**（断言）；
  ③ 注册表变更而派生层未重建 ⇒ 必须报 **stale**（不是静默继续）。
- `text_origin` 改成 `registry:name@sha16` 后必须**可解析回查**（S3-4）；改名要在 diff 里显式声明。
- 1b 交付请给新三锚 + 一条负向测试（改坏注册表 ⇒ M4 侧报 stale/抛错），否则仍是"护栏就绪、无人接入"。