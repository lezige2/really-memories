# P0 写入时间归一化（event_date）规格 v1

> B 准 P0 启动：按当前 topk4 基线复测；**若日后改粗排，P0 全部重测**。
> 产品默认 `--event-date` off；不改原文、不改 `created_at`；一行回滚（drop 列 + flag）。

## 1 目标

写入时把“明天/下周三/下个月 5 号/周五”确定性地归一化为**绝对日期**，存入 metadata，查询时可用；原文仍保留，模型看到的是原文 + 可选日期提示。

## 2 字段（SQLite metadata）

| 字段 | 例 | 说明 |
|---|---|---|
| `event_date` | `2026-11-04` | 绝对日期；解析不出为 NULL |
| `event_time` | `15:00` | 可选；只有明确时刻才填 |
| `event_source` | `下周三` | 原文片段，可审计 |
| `event_tz` | `Asia/Shanghai` | 固定；不随系统漂移 |
| `event_confidence` | `high/ambiguous/none` | `ambiguous` 不写 event_date |

## 3 解析规则（确定性，无模型）

- 基准 = `created_at` 的本地日期（Asia/Shanghai）；
- 支持：今天/明天/后天/大后天；这周X/下周X/下下周X；下个月 N 号/月底；周五（最近未来）；
- 时刻：上午/下午/晚上 + N 点；不明确则只写日期；
- **periodic**（每周三/每月/每年）不写 event_date，写 recurrence 标记；
- **歧义**（“下周”无星期、“月底”跨月不清）→ `event_confidence=ambiguous`，event_date=NULL，保留原文；
- 归档/回填/历史块**不解析**；只处理新写入。

## 4 检索使用（先最小）

- 仅在 query 明确问时间/到期时，用 event_date 排序/过滤；
- 不把 event_date 变成 prompt 长文本；只作为 metadata 参与排序；
- 过期策略：一次性事件 event_date 过后可降权/不挂；periodic 豁免；
- 与 K2 无关：K2 仍 off/auto，不使用 event_date。

## 5 迁移/回滚

- `ALTER TABLE memory_source ADD COLUMN event_date TEXT` 等；`PRAGMA user_version` 记录；
- 回滚：flag off + drop 列（或保留列但停用）；**不动 created_at/原文/块**；
- 备份 `chat.db` + sha 后再迁移；
- 不批量回填历史（无法知道写作时的“今天”）。

## 6 验收（B 定）

- 解析准确率 **≥95%**（40 条人工样本：明天/下周三/下月/周五/跨月/跨年/歧义/periodic）；
- 歧义 **不猜**，保留原文；
- periodic 豁免、归档不解析；
- 20 档 81/extra/MT20 不回归；
- flag off 时行为与现网逐字一致；
- 回滚演练：drop 列后服务正常、原文/created_at 不变。

## 7 不做

- 不做模型抽取、不做自然语言推理；
- 不改 `created_at`（写入时刻）语义；
- 不解析归档/回填；
- 不默认开启、不 push。
## 8 语义写死（B 2026-10-30）

1. **下周X**：按 ISO 周（周一为首），“下周X”= 下一个 ISO 周的周X；今天恰为周X → **+7**，不给 0。
2. **这周X 已过** → `ambiguous`；不回填过去日期，不自动下移。
3. **裸写“周X”**：今天恰为该周X 时——**带明确时刻或“下班前/上班前/今晚” → 当天**；仅日期、无时刻 → **+7**（避免“已过”歧义，如 E38）；今天周一至周四 → 本周五。E05「周三晚上七点组会」今天周三 → 当天；E21「周五下班前」今天周五 → 当天。
4. **跨月/跨年**：“下个月 N 号”处理 12→1 月；“月底”= 当月最后一天；若“月底”当天已过 → `ambiguous`。
5. **created_at 语义 = `v1_local_naive`（描述现实，不是定义正确）**：历史行写入的是**本地朴素时间**（如 `2026-10-27T20:00:10`），不是 UTC。解析器**不做任何时区转换**；metadata 同时记 `event_basis_ts`（完整本地时间戳）与 `event_tz=Asia/Shanghai`。未来若切 UTC，按 `created_at_semantics` 版本分读，**禁止混算**。
6. **时刻边界**：“晚上 12 点”= 次日 00:00；“凌晨 N 点”= 当天 00:00–05:59；“晚上 11:59”= 当天；“半夜 12 点”= 次日 00:00。
7. **检索侧“明确问时间”**：确定性时间词表（今天/明天/下周/几号/什么时候/到期/会议时间…），**不许模型判**。
8. **过期基准**：`event_date < today` 才算过期；`event_date == today` **不过期**；periodic 豁免：每天/每周/每月/每年/每工作日。

## 9 验收样本（冻结）

- 40 条人工样本，冻结 sha（当前 `ec8efc64660793de142e621514eb1b5642b2a3120657091c50bdf7a4ce03d491`）；独立标注（非实现者）；
- 必须含四个边界：**今天=周三**、**今天=周五**、**12/31**、**月底当天**；边界注释只放 `boundary` 字段，`text` 只留原句；
- 每条含：原文、`created_at_local`、期望 event_date/confidence、是否 periodic；
- 回滚演练：drop 列 + flag off 后，81/extra/MT20 **不回归**（不只“服务正常”）。
