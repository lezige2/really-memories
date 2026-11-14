# P1 · audit 服务级 R3 + 门状态

## 复验

| 项 | 结果 |
|---|---|
| 外部 `reheat_plan`（无 trace） | **0 条事件**（预期 0）✅ |
| `app.reheat` | **2 条** ❌（`restore/no_newer` + `restore/reheat_execute`，同 trace） |
| ask 同 trace | ✅（retrieve+answer） |
| `retrieve.query_sha16` | **fd01f6dbf84d596a**（非空）✅ |

## P1 门四项状态

| 项 | 状态 |
|---|---|
| extra 19 逐 case | ❌ 未达：P1 回归里 extra **17/20**（L05、L07、L09） |
| 回滚演练 | ✅ PASS（201 行内容不变、备份逐字节还原） |
| audit trace | ✅ ask 侧合格（同 trace、query_sha16、无原文） |
| reheat 1 条 | ❌ FAIL（仍 2 条） |

## 结论

`reheat_execute` 内 plan 与 execute 各 `_audit` 一次，合并逻辑未落到该路径；前一次修的是别处。