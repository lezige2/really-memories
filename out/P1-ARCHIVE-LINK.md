# P1 · 200 行旧库归档联动

- 副本 200 行、created_at 回拨至 **2026-08-06T00:00:00**；`auto_archive` 候选 **200**、归档 **200**、active **0**、总行 **200** ⇒ 账目一致 **True**、**无丢行**（missing 0）。
- zip：**['2026-11.zip']**；`fallback_archive` 只读命中 **5** 条（top id 1，score 0.8571）。

## 发现的缺陷
- **月分组用错列**：`row_month` 读 `r[8]`，而 `block_rows` 的第 8 列是 **`n_bytes`**（created_at 根本没被 SELECT）⇒ 200 行全部落进 **2026-11.zip**，尽管 created_at 是 2026-08-06。
- 影响：历史块无法按月归档，全部堆到当前月 zip；与 `reheat_plan` 早前同一类列索引错误。

## 结论
归档链路（候选→zip→标记→active 排除→fallback 命中）账目正确；**月分组需修**：`block_rows` 增选 created_at 或 `row_month` 改查库。