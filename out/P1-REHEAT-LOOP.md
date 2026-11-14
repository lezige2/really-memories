# P1 回热 · 1 条真实闭环（副本，daily 未写）

## 闭环结果：**PASS**

| 步骤 | 结果 |
|---|---|
| 归档 id14「我养的猫叫豆豆」 | zip 存在、sha 有、`active_rows` 排除（20→19） |
| `reheat(14)` | **executed，plan=restore**，块文件重建存在（n_tokens 12）、`duplicate_blocks=0`、archive 记录保留 + `reheated_at` |
| 问「我的猫叫什么？」 | 「你的猫叫豆豆」、`block_ids=[14]` |
| 二次 `reheat(14)` | **already_reheated**、块数不变 |
| 同族更新后 `reheat(旧)` | **skip_superseded / newer_exists** |

## 必须报告的两个问题

### ① 我误删了 daily 的一个块文件（已恢复）
- 原因：副本 `chat.db` 里 `memory_block.path` 仍是 **daily 绝对路径**，脚本按该路径删除块以验证重建，结果删掉了 `kvmem/daily/blocks/mem-327723633d2d.kvmem`（id14）。
- 恢复：把 reheat 重建的同名块复制回 daily；现 daily **40 块**、`chat.db` sha **未变**（`0a7eae49…`）、`memory_block` 20 行、row14 路径存在。
- 验证：副本起服务问「我的猫叫什么？」→ **豆豆、block_ids=[14]**，说明恢复文件可正常挂载。
- 残留风险：独立重建同文本块**同尺寸但 sha 不同**（块内嵌非确定字节），无法用哈希证明与原文件逐字节相同。

### ② reheat 的“同族更新”判据过粗（真实缺陷）
- 首次跑 sid=2（组会）被判 **skip_superseded**，`superseded_by=5`——而 5 是「下周三去上海开会」，属于不同事件。
- 原因：`组会` 与 `开会/出差` 都归入 `会议` 族，按 predicate 粗匹配即认定为“更新”。
- 影响：本可回热的旧组会事实会被拒绝复活。

## 结论

闭环机制本身可用（restore / already_reheated / 块重建 / 作答），但 **reheat_plan 的同族判据需按事件槽位（日期/地点）细化**，否则会误杀；另需修脚本：副本 DB 内的绝对块路径必须先重写再操作。