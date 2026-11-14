# P1 · 100 行 archive/fallback/reheat 联动（副本）

- 副本 `kvmem/p100`：先 `rewrite_block_paths` + 逐条 `assert_under`；100 行旧 created_at（07:35 / 08:35 / 09:30）。

| 项 | 结果 |
|---|---|
| 月份分桶 | **{'2026-07': 35, '2026-08': 35, '2026-09': 30}** |
| zip | **['2026-07.zip', '2026-08.zip', '2026-09.zip']** |
| 归档 / active / 总行 | **100 / 0 / 100**，账目一致 **True** |
| fallback 只读命中 | **3** 条（score 0.857） |
| reheat id 1 | executed=**True**、块存在=**True** |
| 回热后是否 active | **True**（archived 标记仍在，靠 `reheated_at` 放回） |
| 二次 reheat | **already_reheated**（幂等） |

## 说明
- “旧值不复活”在本轮不适用：这 100 条无同键更新行，reheat 走 restore 分支；该性质已由 6 链的 C6（同 key 更新 → skip_superseded、答新值）覆盖。
- 回热不删除归档记录，而是用 `reheated_at` 使 `archived_ids` 不再排除它——设计如此，账目仍可追溯。