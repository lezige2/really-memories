# P1 归档 / 冷热分层规格 v0（讨论稿）

> 用户提案：定时扫描低 access、last_accessed>21d 的块 → is_archived=1 移出主池；主池 topk10，空/低置信 → 调归档 zip；zip 内是 .db；命中后解压检索，回写主库，防覆盖。
> 状态：**spec only，不写码**；P1 是产品变更，需用户点头 + 备份 + 回滚。P0 未完成、P2 未过门前不启动。

## 1 现状缺口

- 当前没有 `access_count` / `last_accessed_at` / `is_archived` / `archive_id` 字段；
- 读路径不记录“哪个块被挂载/被引用”，无法统计冷热；
- 没有 archive 目录/索引/zip 规范；
- 没有“低置信”分数阈值（当前 topk 检索没有 cosine 分数暴露）。

## 2 Schema（建议）

```sql
ALTER TABLE memory_source ADD COLUMN access_count INTEGER DEFAULT 0;
ALTER TABLE memory_source ADD COLUMN last_accessed_at TEXT;
ALTER TABLE memory_source ADD COLUMN is_archived INTEGER DEFAULT 0;
ALTER TABLE memory_source ADD COLUMN archived_at TEXT;
ALTER TABLE memory_source ADD COLUMN archive_id TEXT;       -- 月份包 id
ALTER TABLE memory_source ADD COLUMN superseded_by INTEGER; -- 回热防覆盖
```

- access 计数只算**最终挂载且被回答引用**的块，不算候选池/未用块；
- 每次读路径更新计数会写库，需 WAL/批量/异步，避免 /ask 变慢；
- 归档/回热必须事务化，不能半写。

## 3 归档单元与索引

- 默认按月：`archive_YYYY-MM.zip`，内含 `blocks.db` + `manifest.json`；
- 月份取值优先级：`event_date` → `created_at`（v1_local_naive）；periodic 不归档或单独；
- 维护 `archive_index` 表：month、archive_id、block_ids、sha256、count；
- “去年/两个月前”查询：先用 P0 event_date/相对时间词转绝对月，再精准解压；无时间词 → 从最近月份倒序盲搜，限制最多 2 个包/超时。

## 4 触发与检索

- 定时任务（每日 03:00）扫描：`access_count<=1 AND last_accessed_at < now-90d AND is_archived=0 AND mode not periodic`；
- 先把候选写 `archive_candidates`，人工/日志审阅后再搬；**不自动删**；
- 主池 topk10；置信度阈值必须**用本库分数分布校准**，不能照搬 cosine 0.4；
- 低置信/空结果 → 查 archive_index → 解压目标月 → 在临时 db 跑同款检索+K2 → 取命中；
- 延迟预算：归档命中 P95 ≤ 主池 + 2s；超时回退“无证据/追问”，不编。

## 5 回热（防覆盖）

1. 解压临时 db，命中块取出；
2. 查主库同 `subject+predicate` 最新事实：
   - 无更新 → INSERT 为新块，`last_accessed_at=now`；
   - 有更新 → INSERT 但 `superseded_by=新id`，**不得成为最新**；
3. 保留 archive 原件；回热只复制，不删除归档；
4. 事务 + 唯一约束；失败回滚，不半写；
5. 回热频率限制：同块 24h 内不重复回热，防抖。

## 6 分阶段（不直接上线）

| 阶段 | 内容 | 门槛 |
|---|---|---|
| P1-0 | schema + 只读 dry-run：算候选/主池大小/预计归档量，不搬 | 报告，不改库 |
| P1-1 | 影子归档：复制到 zip+index，主库不动；校验 restore | 归档/恢复 100%、sha 一致 |
| P1-2 | 隔离副本开 flag，搬 20/50/200 档，跑 81/extra/MT20 + 旧值泄漏 | 泄漏不升、K2 效果不降、无 5xx |
| P1-3 | 现网启用（默认 off → 用户批准开启），备份 + 一行回滚 | 用户点头 |

## 7 待 B/用户定

1. access 语义：挂载算、回答引用算、还是用户点“有用”算？
2. 归档时间基准：event_date / created_at / last_accessed？
3. 低置信阈值：先用分数分位数（如 top1 < P10）还是绝对 cosine？
4. 归档是否加密/放网盘？本地 zip 是否足够？
5. 主池目标 50/100？超期 N=21d 还是 90d？
6. 回热是否允许改变“最新事实”排序？默认只读回热、不改主事实。
## 8 B 修订（2026-10-30，覆盖前文冲突）

1. **不加 access_count**：自动挂载 topk10 ≠ 重要；v1 归档候选只用 **created_at（+superseded，若有）+ 用户显式标记（“这个别再提”）**；等有“答案里真正引用”的异步日志再升级，且可丢。
2. **时间基准**：`created_at` 为主；有 `event_date` 时优先；**不用 last_accessed**。“去年/上个月”解压必须靠 event_date；没有就**不许解压**，只能倒序盲搜并标“未定位”。
3. **低置信阈值**：禁止写死 cosine；用本库 top1 分数分位数校准（如近 N 次 p5），校准样本 sha 入报告；**无校准样本 → 判低置信但“不解压”**。
4. **dry-run 只读 zero-write**：输出“若归档会移走哪些块 + 若查回能否恢复”；恢复演练在临时副本，不动现网。
5. 顺序：**P0 收尾 → P1 dry-run（含恢复演练）→ 隔离副本 flag → 现网需用户批准**；解压/时间过滤等 P0。

## 9 存储红线（用户 2026-10-30）

- **不使用云盘/网盘/任何联网归档**；archive zip 只落本地磁盘（如 `D:\llama-mem\archive\`）。
- 归档包含记忆原文，等同 `chat.db` 敏感级：本地权限、sha256 manifest、可选本地加密；不得上传、不得自动同步。
- 解压只在本地临时目录；用完清理；不把归档文本发到任何远程服务。
- 备份/恢复也只能本地介质；跨机迁移需用户显式批准并加密。

## 10 B 实施裁定（2026-10-30）

- 升级为“**能力实现、默认 off、不自动搬**”：无定时器、无后台线程、无 admin 调用就绝不搬；启动时断言。
- P1 放独立模块，**不改 `put_source`**；列迁移排在 P0 迁移之后；启用等 P0E 过门。
- 验收门（缺一不可）：
  a) round-trip 20/20 id/文本/块 sha/字节一致；源不删，只标 `is_archived`；
  b) 恢复不得复活成最新：有 `superseded_by` 时仍从属；专门造“恢复后遇到更新事实”用例；
  c) 同链块整链归档或不动，禁止悬挂引用；
  d) 幂等：归档两次不重复、恢复两次同态；
  e) 回滚 = drop 列 + 删 zip 后，内容哈希回到归档前；
  f) local only，代码断言无网络调用；
  g) 无 auto scan 断言。
- `archive_index` 月表必须与 manifest/sha 对得上；**恢复只认 sha，不认文件名**。
