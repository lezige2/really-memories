# P1 · 回滚演练 + audit trace（副本）

## 回滚演练：**PASS**

- 归档 **201 行**（1 个 zip）→ `DROP memory_archive`、`DROP memory_access`、删除 zip/sidecar。
- `memory_source`：**201 → 201 行**，**内容逐行相同**（id/name/text/created_at）。
- 用备份整库恢复：**逐字节一致**（sha 相同）。
- 结论：归档/回滚不动源表，回滚可完全还原。

## audit trace

- 事件 5 条，字段含 `trace_id / stage / decision / reason / block_ids / count / ts / query_sha16 / answer_sha16`；**无原文**（扫描「猫叫豆豆」为 False）。
- 但有三处不足：① `stage` **恒为 `archive`**；② `/ask` 前后 JSONL **5→5 行**，ask/retrieve/answer 阶段未接线；③ reheat 每次产生 **2 条**事件（plan + execute），重复。
- 结论：audit 本身字段与脱敏合格，但**覆盖面只到 lifecycle**，服务问答链路尚无审计。