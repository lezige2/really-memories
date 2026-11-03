# meta 模板路径确认（润色已移出工作树）

- 配置：PID 1488、8765 单监听；daily 副本、K2 off、v1、event off、TTS off、**未传任何 meta flag**（默认 on）、ngl28/topk4、memories=20

| 项 | 结果 |
|---|---|
| 81 | **81/81 ✅**（0 fail） |
| P50 / P95 / mean | **1.94s / 4.43s / 2.03s** |
| elapsed | 181.2s |

## 两句探针

| 问题 | 答案 | block_ids | state | 延迟 |
|---|---|---|---|---|
| 你记得我有几条记忆？ | 你目前有 20 条有效记忆。 | `[]` | meta_answer | 0.005s |
| 记忆占多少空间？ | 你目前有 20 条有效记忆；记忆块 65.7 MB，数据库 0.2 MB，合计 65.9 MB（约 0.06 GB）。 | `[]` | meta_answer | 0.001s |

- 空间题模板**含 MB 与 GB**，数字与宿主注入一致（20 条 / 65.7 + 0.2 = 65.9 MB / ≈0.06 GB）；两句均**零模型调用**。
- 未见润色路径残留（无 prompt 泄漏、无闲聊追加）。

## 处置

- 未跑 extra/MT20；未写 daily、未 commit；服务已停（8765 无监听）。
- 产物：`META-TEMPLATE-81.md`、`META-TEMPLATE-81-REPORT.json`（评测原始件 `META-TEMPLATE-81.json` 未覆盖）。