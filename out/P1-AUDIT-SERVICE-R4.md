# P1 · audit 服务级 R4（最终）

## 复验

| 项 | 结果 |
|---|---|
| 外部 `reheat_plan`（无 trace） | 0 条 ✅ |
| `app.reheat` | **1 条**（`restore/reheat_execute`）✅ |
| ask 同 trace | ✅（retrieve+answer） |
| `query_sha16` | **fd01f6dbf84d596a** 非空 ✅ |

## P1 门四项（extra 按 B 修正口径）

| 项 | 状态 |
|---|---|
| extra 19 逐 case | **PASS**：基线 17/19（fail ['L07', 'L09']）、P1 17/19（fail ['L07', 'L09']）→ 失败集相同 |
| rollback drill | **PASS**（201 行不变、备份逐字节还原） |
| audit trace | **PASS**（同 trace、query_sha16 非空、无原文） |
| reheat 1 条 | **PASS**（1 条 `reheat_execute`） |

## 说明

- L05 已证为答案层 flaky（单条 20 次 16–18/20 波动、5 次仅 2–4/5），按 B 口径从 extra 分母剔除；剔除后两边均为 17/19、失败集同为 L07/L09。
- 此前 `reheat` 双事件经 `if audit:` 守卫修复，本次实测 1 条。