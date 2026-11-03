# norm-restate 收尾（轻量两项）

1) **默认 off 跑 81：81/81**（A 基线 81/81，不回归）

2) **flag on vs off 的 HTTP 响应**

| 场景 | duplicate | restated | restated_count | last_restated_at | created_at |
|---|---|---|---|---|---|
| on·首写 | none | - | - | - | 2026-11-03T22:33:49 |
| on·同句再写 | **exact** | **True** | **1** | 2026-11-03T22:33:49 | 不变 |
| on·归一化变体 | **norm** | **True** | **2** | 2026-11-03T22:33:49 | 不变 |
| **off**·同句再写 | True | **无字段** | 无 | 无 | 不变 |

- 注意：**默认已改为 off**，必须显式 `--norm-dedup` 才启用（我第一次未加 flag，变体各自新增行，属预期）。

3) 回滚等价性：两列可删、内容与 daily 逐行相同；**内容等价、非字节等价**（DROP COLUMN 重写页面）。

结论：默认 off；flag on 字段齐备；默认路径 81 不回归。未写 daily、未 commit、服务已停。