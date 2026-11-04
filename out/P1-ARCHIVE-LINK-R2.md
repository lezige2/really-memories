# P1 · 200 行归档联动 R2（月份修复后）

- 副本 200 行，created_at 分跨 07/08/09：**{'2026-07': 67, '2026-08': 67, '2026-09': 66}**。

| 项 | 结果 |
|---|---|
| zip | **['2026-07.zip', '2026-08.zip', '2026-09.zip']** |
| 归档 / active / 总行 | **200 / 0 / 200** |
| 账目一致 | **True**（active+archived=total） |
| fallback 只读命中 | **3** 条（top id 1，score 0.8571） |

## event_date 优先

- 构造 created_at=`2026-11-01`、event_date=`2026-09-15` 的行 → 实际生成 **['2026-09.zip']**，月份归入 `2026-09` ✅
- 说明 `row_month` 已优先取 event_date，次选 memory_source.created_at（不再读 r[8]）。

## 结论

**PASS**：三月分桶、账目、fallback、event_date 优先四项均成立；此前的“全部堆到当前月”缺陷已修复。