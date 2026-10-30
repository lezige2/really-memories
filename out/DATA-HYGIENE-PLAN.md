# 京A88888 数据卫生方案（只读规划，**不执行**）

> 对象：`kvmem/daily/chat.db`，id 3 / 12 / 13（同一车牌值，同源不同上下文）。
> 状态：**只出方案**；不改库、不执行 SQL、不 commit。改 daily 需用户点头 + 备份。

## 1 谁改、怎么标

- **执行者：D**（数据 owner，唯一写库人）；**C 只提供只读 diff/校验脚本与回滚演练**；A 复核；用户批准。
- 只改 `daily_memory_meta.tags`（JSON 数组），**不改 text / source_hash / created_at / block**，**不删行**：

```sql
-- 建议值（未执行）；当前 id3/12/13 的 tags 均为 []
UPDATE daily_memory_meta SET tags='["plate:京A88888","context:primary"]'
 WHERE source_id=3;
UPDATE daily_memory_meta SET tags='["plate:京A88888","dup_of:3","context:restatement"]'
 WHERE source_id IN (12,13);
```

- 语义：id3 为主记录；12/13 标 `dup_of:3`（同值重复、保留可检索）；`plate:京A88888` 供检索/审计；`context:restatement` 标明复述来源。
- 若 meta 行缺失：先 `INSERT OR IGNORE INTO daily_memory_meta(source_id,tags,source,related_ids,slots) VALUES(?, '[]','manual','[]',NULL)` 再 UPDATE。

## 2 回滚

1. 改前备份：`copy chat.db tmp/hygiene/chat.db.pre` + sha256；`sqlite3 chat.db ".dump daily_memory_meta" > tmp/hygiene/meta.pre.sql`。
2. 撤销 SQL（若 tags 原值确为 `[]`）：
```sql
UPDATE daily_memory_meta SET tags='[]' WHERE source_id IN (3,12,13);
```
   或整表回灌：事务内 `DELETE FROM daily_memory_meta; INSERT ...` 用 `meta.pre.sql`。
3. 回滚验收：`memory_source` 内容 sha / 行数 20 / 块 sha 与改前逐项相等；tags 逐行回到原值；`/memories` 不再显示新标签。

## 3 42 对照（改前/改后）

- 夹具：`out/KV-CONFLICT-40.jsonl` = 42 条（30 KVC 冲突正例 + 12 KVN 阴性对照）。
- 流程：`chat.db.pre` 与 `chat.db.post` 两个副本，同一服务/模型/参数（topk4、K2 按实验臂固定），逐条跑 42；记录 answer/state/block_ids/pass。
- 统计：paired McNemar（改前 vs 改后）；**12 条 KVN 必须仍不被隐藏/仍 pass**；42 条逐条 diff。
- 预期：夹具自带 `pre_state`，不读 daily 旧行 → 42 条应 **全同**；任何差异都说明 tags 影响了检索打分，必须停查。
- 同轮回归：81 / extra / MT20 三件套 + `/memories` 输出（tags 展示）。

## 4 风险

1. **K2「同值不隐藏」**：id12/13 与 id3 同值，当前 K2 按 created_at 取最新，会把 id3 当旧值隐藏、甚至把 13 当 kept。必须显式跳过 `dup_of` 组：dup 行不参与 kept 选择、也不进 hidden；否则“id3 主记录”只是装饰，K2 仍答 13。
2. **tags 参与检索打分**（`memory_service.retrieve` 的 tag_hits，TAG_WEIGHT）：`plate:京A88888` 仅在 query 含该 token 时加分；`dup_of:3`/`context:*` 基本不命中 → 理论上 81/extra/MT20 不变，但必须回归验证。
3. **同值三块仍可同时挂载**（K2 off 时）：不影响 42，但会继续污染“同值泄漏”口径（已在 DATA-HYGIENE 报告标注）。
4. `/memories` 等消费方会看到新 tags；下游展示/统计若按 tags 分组需同步评估。

## 5 执行窗口

- **P1b（主体键/写时冲突）spec 定稿之后、40k 之前**；先副本上演练 42 + 三件套，再申请改 daily。
- 硬前提：**用户点头 + 备份（chat.db + meta dump）+ 回滚 SQL 已演练**；否则不执行。
- 本轮只读分析：未改 daily、未写 meta、未建标记、未 commit。
