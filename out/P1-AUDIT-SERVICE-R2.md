# P1 · audit 服务级 R2

| 项 | 结果 |
|---|---|
| ask 两条同 trace | 2 条、同 trace ✅ |
| retrieve.query_sha16 | **fd01f6dbf84d596a（已非空）** ✅ |
| reheat 事件数 | **2 条** ❌（`restore/no_newer` + `restore/reheat_execute`） |

- 结论：query_sha16 已修；**reheat 合并为 1 条仍未生效**（`app.reheat` 把 trace 传给 `reheat_execute`，plan 与 execute 各写一条）。