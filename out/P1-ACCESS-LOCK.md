# P1 · access 锁验证（50 次 ask）

| 项 | 结果 |
|---|---|
| ask 次数 / 错误 | **50 / 0** |
| `SQLITE_BUSY` / locked（服务日志） | **0** |
| busy_timeout | **5000 ms** |
| 状态分布 | {'natural': 30, 'no_evidence': 20} |
| block_ids 模式 | **4 种**（同问同块，各 10 次） |
| memory_access 行数 | **6** |
| P50 | **2.34s** |

## 结论
access 后台写入在 50 次连续 ask 下**无锁冲突、无失败**，块挂载稳定；`no_evidence` 20 次来自无记忆命中的问题（非错误）。