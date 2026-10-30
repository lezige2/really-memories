# P1 dry-run（只读，**local only**）

- 源库：`D:\llama-mem\kvmem\daily\chat.db` sha256 `0a7eae495c4be89c`；只读副本 `D:\llama-mem\tmp\p1\chat.db`（sha `acd50dcdbecc4fd6`）
- **local only**：仅本机 tmp；无云盘/网盘、无上传、无自动同步；未改产品代码/未加列/未 commit。

## 候选（created_at 基准；有 event_date 优先）

| 阈值 | cutoff | 候选数 | 候选 id | 候选 token | 归档后主池 | 主池<50 |
|---|---|---|---|---|---|---|
| 21d | 2026-10-09 | 0 | — | 0 | 20 | True |
| 90d | 2026-08-01 | 0 | — | 0 | 20 | True |

敏感性（相邻阈值）：1d=20, 2d=20, 3d=0, 21d=0, 90d=0

- 数据仅 2–3 天新（created_at 2026-10-27 … 2026-10-28），21d/90d 必然 0 候选；2d 边界才全量命中，说明阈值需按真实老化数据重定。
- superseded 列不存在（0 条标记）；用户显式标记 0 条；系统 auto_* 标签 6 条（非用户标记）。
- event_date 可解析 14 条（过去 6 / 未来 8）；均未超过 21/90d，无过期。
- 文本近重复 0 组（如 —）；稀有值重复 1 组（如 [3, 12, 13]），均无 superseded 标记，仅报告不归档。
- 最早到期日：21d=2026-11-17，90d=2027-01-25（此刻 0 候选，到期前不会产生归档）。

## 恢复演练

- 触发：否（0 候选）；控制 round-trip（全部 20 条复制到 `D:\llama-mem\tmp\p1\restore`）：
  rows=20, ids=20, text_sha=20, block_sha=20, bytes=20 → **100% 可恢复**

## 低置信阈值（p5 校准）

- 样本 22 条 ask（query_sha16 + top1），p5=**2.0**，min=1.0，median=5.0，样本 sha `5b257ef0e75fb6ce`
- 动作：解压仅对 <p5 的查询；本轮 0 归档候选 -> 不解压

## 结论

- 21d/90d 候选均为 0，归档后主池仍 20（已 <50）：**P1 前提不成立，不能在 daily 库上线**；
- 建议先用老化/显式标记数据重跑；event_date 与近重复需显式 superseded 语义才能自动归档；
- 未生成归档包/zip（0 候选）；任何后续包仅落本地并同 chat.db 敏感级保管。
