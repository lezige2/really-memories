# P1 E2E · 5 条同族链（副本，路径已重写）

- 安全前置：`rewrite_block_paths` 全部重写到 `tmp/p1_e2e/.../blocks`，并逐条 `assert_under` 通过；daily 未被打开写。

| # | 归档 id | 新事实 | 期望 | 实测 | reason | executed |
|---|---|---|---|---|---|---|
| 1 | 1 | 我每周三晚上七点有组会，地点改到C座201。 | skip_superseded | **restore** | no_newer | True |
| 2 | 2 | 我下周三要去上海开会。 | restore | **restore** | no_newer | True |
| 4 | 4 | 我下周三要去上海开会。 | restore | **restore** | no_newer | True |
| 5 | 5 | 我下周三要去北京出差。 | restore | **skip_superseded** | newer_same_family | False |
| 24 | 24 | 我周四上午十点有组会，线上。 | restore | **restore** | no_newer | True |

**结果 3/5**：
- id2（组会 vs 开会）、id4（出差 vs 开会）、id24（评审会 vs 组会）→ 正确 `restore`，**不同族未误 skip** ✅
- **id1（组会 vs 组会，同 key）→ 误 `restore/no_newer`**（应有更新却被复活）❌
- **id5（开会 vs 出差，不同族）→ 误 `skip_superseded/newer_same_family`**（本应复活却被拒）❌

### 根因（代码事实）
`reheat_plan` 里 `created = str(r[8])`，但 `live_rows` 来自 `ms.block_rows`，其第 8 列是 **`b.n_bytes`**，`created_at` 根本没被 SELECT。于是“更新”比较的是**字节数与 ISO 时间戳**，结果任意：id1 得到假 restore、id5 得到假 skip。
修复方向：`block_rows` 增选 `s.created_at`（或 `reheat_plan` 改用 `memory_source` 查询），并按 `_fact_key` 的五元组（subject/event/place/time/object）判定同族。