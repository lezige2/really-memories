# P0 event_date 报告（flag 默认 off）

> 2026-10-30 · 未 commit / 未迁移现网 / 未重启 / 未跑服务

## 1 文件

| 文件 | 变更 |
|---|---|
| `tools/event_time.py` | 新增：确定性解析器 + 检索侧词表/过期/过滤 |
| `tools/memory_source.py` | SCHEMA 增 7 列（含 `event_basis_ts`）+ `memory_meta`；`ensure_event_columns`（迁移前备份+sha）、`drop_event_columns`；`CREATED_AT_SEMANTICS=v1_local_naive` |
| `tools/chat_daily.py` | `--event-date`（默认 False）、`DailyApp(event_date=False)`、`_rows()` 过期钩子 |
| `tools/chat_service.py` | `--event-date` 透传（默认 False） |
| `tools/test_event_time_cpu.py` | 16 例 |
| `tools/test_event_write_cpu.py` | 5 例（/remember 写侧） |
| `out/P0-EVENTDATE-SAMPLES-40.jsonl` | 40 条冻结样本（含 4 边界），字段 `created_at_local`，sha256 `ec8efc64660793de142e621514eb1b5642b2a3120657091c50bdf7a4ce03d491` |
| `out/P0-EVENTDATE-C2-LABELS-LOCAL.jsonl` | C2 独立标注（按 id 绑定上述 sha） |

## 2 语义（SPEC §8）

- **created_at 语义 = `v1_local_naive`（描述现实，不是定义正确）**：历史行写的是本地朴素时间；
  解析器**不做任何时区转换**；metadata 记 `event_basis_ts`（完整本地时间戳）+ `event_tz=Asia/Shanghai`；
  `created_at_semantics` 单点定义在 `memory_source`，未来切 UTC 按版本分读、禁止混算。
- 下周X = 下一 ISO 周（今天同周X → +7）；这周X 已过 → ambiguous；今天=该周X → 当天；
- 裸“周X”：今天恰为该周X → +7，否则本周内未来那天；`下周`（无星期）→ ambiguous；
- 下个月 N 号（12→次年 1 月；无效日 ambiguous）；月底=当月最后一天，已过 → ambiguous；
- 今晚/今早 = 当天；晚上/半夜 12 点 = 次日 00:00；凌晨 N 点 = 当天；
- periodic 不写 event_date；归档/回填 `allow_parse=False` 不解析；`event_parser_version` 入 metadata。

## 3 检索侧（最小）

- 只用确定性时间词表 `is_time_query()`，无模型；
- `event_date < today` 才过期（当天不过期）；periodic / ambiguous / 归档一律豁免；
- flag off：`_rows()` 与原逻辑逐字一致（不读 event_*）。

## 4 迁移/回滚

- `ensure_event_columns(con, db_path)` 幂等加列，**迁移前**复制 `<db>.bak-eventdate-<ts>` 并返回 sha256；`user_version=2`；
- 回滚：`drop_event_columns()` + flag off；不动原文/created_at/块。

## 5 验收（B 复核后）

- 规则修正（SPEC §8.3）：裸周X + 明确时刻/“下班前/上班前/今晚” → **当天**；仅日期且无时刻、今天恰为周X → +7。
  E05「周三晚上七点组会」（今天周三）→ 10-28；E21「周五下班前」（今天周五）→ 10-30。
- 样本去污染：E37/E38/E39/E40 的括注移到 `boundary`，`text` 只留原句；
  新 sha256 `ec8efc64660793de142e621514eb1b5642b2a3120657091c50bdf7a4ce03d491`。
- 准确率（`out/P0-EVENTDATE-ACCURACY.json`）：
  * 按 B 复核修正后的期望：**40/40 = 100%**；
  * 对照 C2 现行标签文件：38/40，仅 E05/E21 两条为 B 复核前的旧期望（未改 C2 标签，待其重绑）。
- 全量 `test_*_cpu.py` = **184 OK**（event 16 + 写侧 5：/remember 明天下午三点→次日 15:00 high、periodic→NULL、归档不解析、flag off 空、重复不双写）。

## 6 未完成（仅此两项）

1. 服务级 81 / extra / MT20 不回归：待 C2 在服务上跑（P0E 回归已暂停，等本修完再跑）。
2. 现网 `kvmem/daily/chat.db` 迁移未做（未加列、未备份）；启用 `--event-date` 前需先迁移并留存 sha。