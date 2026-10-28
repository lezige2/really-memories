# LONG-CONV-TEST-V2（长上下文压测 · 说明）

> 脚本：`tmp/long_conv_test_v2.py`（Python 3.11+，仅标准库；只读调用 `127.0.0.1:8765`，
> **不重启/不修改服务与既有文件**）。本文件为运行说明与判读口径。

## 1 目的

在约 40k 字符的连续对话中**触发 rollover**，然后检验：

1. **8 个事实**（每 3–5k 字符埋 1 个）在 rollover 后能否召回——分 **early / mid / recent** 三档；
2. **重复问同一事实** 3 次是否稳定一致；
3. **跨 rollover 后追问“刚才说的”** 是否还能指出 rollover 前最后一条具体事实；
4. **长时间连续提问不 reset**（10 连问）是否稳定、token 是否线性增长（无隐性重置/卡死）。

相对 `tmp/long_conv_test.py`（v1）的增强：请求超时/5xx 重试、逐 turn `chat_tokens` 与
rollover 事件留痕、事实埋点从 2 个扩到 8 个并分三档、增加重复/跨 rollover/不 reset 场景、
输出可复跑 JSON（含脚本 sha256 与完整参数）、`--dry-run/--smoke/--no-reset`。

## 2 前置条件

- 服务已在 `127.0.0.1:8765` 运行（`curl http://127.0.0.1:8765/health` 为 ok）；
- 服务 rollover 相关预算可从 `/status` 读到：`session.chat_tokens`、`session.rollover_at`、
  `session.rollover_threshold_tokens`、`engine_meta.n_ctx`（脚本只读取，用于记录/判读）；
- **服务只由 LEAD 重启**；本脚本只发 HTTP 请求，不碰进程/文件；
- 单次 `/ask` 可能较慢（长上下文），默认 `--request-timeout 300`。

## 3 运行

```bash
# 0) 零请求自检（打印计划/事实阈值/脚本 sha）
python -X utf8 tmp/long_conv_test_v2.py --dry-run

# 1) 小规模冒烟（2k 字符、最多 20 turn；仍会跑 8 事实探针 + 重复 + 不 reset 场景）
python -X utf8 tmp/long_conv_test_v2.py --smoke

# 2) 正式长压测（约 40k 字符；默认开始时 POST /reset）
python -X utf8 tmp/long_conv_test_v2.py --target-chars 40000 --out tmp/LONG-CONV-TEST-V2.json

# 变体
python -X utf8 tmp/long_conv_test_v2.py --no-reset            # 不重置会话（接着当前会话跑）
python -X utf8 tmp/long_conv_test_v2.py --retries 5 --backoff 2 --request-timeout 600
python -X utf8 tmp/long_conv_test_v2.py --fail-fast           # 首次请求失败即退出（默认继续并记录）
python -X utf8 tmp/long_conv_test_v2.py --status-every 5      # 每 5 turn 采一次 /status（省时）
```

参数总览：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--endpoint` | `http://127.0.0.1:8765` | 服务地址 |
| `--target-chars` | 40000 | 主循环累计发送字符数（事实也计入） |
| `--max-turns` | 500 | 主循环 turn 上限（防死循环） |
| `--request-timeout` | 300 | 单请求超时秒 |
| `--retries` | 3 | 5xx/429/断连/超时的重试次数（指数退避） |
| `--backoff` | 1.0 | 退避基数秒（第 n 次重试等待 base·2^(n-1)） |
| `--status-every` | 1 | 每 N turn 采 `/status.chat_tokens`；≠1 时其余 turn 记 null |
| `--seed` | 20261028 | 填充语随机种子（事实与阈值固定） |
| `--out` | `tmp/LONG-CONV-TEST-V2.json` | 输出路径（中断/失败也会落部分结果） |
| `--no-reset` | 关 | 不发送 `/reset`，接着当前会话 |
| `--fail-fast` | 关 | 首次请求失败即退出；默认记录后继续 |
| `--smoke` | 关 | 缩小到 ≤2k 字符 / ≤20 turn |
| `--dry-run` | 关 | 零请求，仅打印计划 |

## 4 埋点（8 事实，按累计字符阈值插入）

阈值固定：`3000, 6500, 11000, 16000, 21000, 26000, 32000, 37000`（约每 3–5k 字符 1 条）：

| id | 档 | 事实 | 召回问句 | 关键词 |
|---|---|---|---|---|
| 1 | early | 车牌号 京A88888 | 我的车牌号是多少？ | 京A88888 |
| 2 | early | 猫叫豆豆 | 我养的猫叫什么名字？ | 豆豆 |
| 3 | mid | 下周五去成都开会 | 我下周五要去哪开会？ | 成都 |
| 4 | mid | 工号 A12345 | 我的工号是多少？ | A12345 |
| 5 | mid | 妻子叫李娜 | 我妻子叫什么名字？ | 李娜 |
| 6 | mid | 老家在青岛 | 我老家在哪里？ | 青岛 |
| 7 | recent | 手机号 13800138000 | 我的手机号是多少？ | 13800138000 |
| 8 | recent | 下个月去西安出差 | 我下个月要去哪出差？ | 西安 |

填充语只做闲聊陈述（不包含上述关键词），避免互相污染。

## 5 输出 JSON（`--out`）

| 字段 | 内容 |
|---|---|
| `plan` | 脚本 basename/sha256、endpoint、目标字符、超时/重试、seed、事实清单 |
| `service_before` | 开始时 `/status` 的 version/engine_meta/session/memories（只读快照） |
| `turns[]` | 每 turn：`turn/chars_before/text_len/is_fact/fact_id/elapsed_s/attempts/error/chat_tokens/status_error/state/refused/answer_len/rollover` |
| `facts[]` | 每个事实实际插入的 turn 与当时累计字符 |
| `rollovers[]` | 每次 rollover：turn、字符数、当时 chat_tokens、服务返回的 rollover 事件 |
| `probes.facts[]` | 8 条召回：question/keywords/answer(截 160)/pass/state/attempts/error |
| `probes.repeated` | 最近事实重复问 3 次：runs[]、all_pass、consistent（答案去空格后完全一致） |
| `probes.post_rollover` | 跨 rollover 追问“刚才说的”：expect_fact_id/keywords/answer/pass；无 rollover 或无前置事实时 pass=null+reason |
| `scenarios.no_reset_continuous` | 10 连问：runs[]、tokens_start/end/delta、all_ok |
| `errors[]` | reset/ask 失败：phase、turn、error、attempts |
| `summary` | main_loop 统计、facts_recall（总数/通过/按档）、repeated、post_rollover、no_reset_continuous、rollover_triggered、errors、verdict |
| `partial` | true=中断/失败的部分结果（仍在 `--out` 落盘） |

## 6 判读

`summary.verdict` 规则（脚本内固定）：

- **PASS**：8 个事实召回全过 **且** 重复问 3 次全过且答案一致 **且** 跨 rollover「刚才说的」不是 False（null=未触发 rollover 时不算失败，但 `rollover_triggered` 会为 false）**且** 10 连问全 ok **且** 至少触发 1 次 rollover **且** errors=0。
- **CHECK**：其余情况——需结合 `turns[]`/`errors[]`/`rollovers[]` 人工判读（例如 rollover 未触发、个别事实被拒答、某次 5xx 重试后成功等）。

典型问题定位：

- `rollover_triggered=false`：目标字符不够或服务预算较大 ⇒ 增大 `--target-chars`/`--max-turns`，或先确认 `/status.session.rollover_threshold_tokens`。
- early 档 FAIL、recent PASS：早期事实被 rollover 压缩/遗忘（预期内的风险读数，逐条记录）。
- `repeated.consistent=false`：同一事实答案漂移，需检查检索/记忆是否稳定。
- `errors[]` 有值：看 `attempts`（重试是否最终成功）与 `phase`；5xx 重试成功不影响 verdict（errors 只记最终失败与 attempts>1 的失败记录；最终成功不计入 errors）。
- `status_error` 非空：`/status` 超时/失败，该 turn `chat_tokens=null`，不影响请求本身。

## 7 可复跑与纪律

- 事实、阈值、探针顺序固定；填充语由 `--seed` 决定 ⇒ 同 seed 同参数可复现。
- 输出 JSON 记录脚本 sha256；每次运行前可用 `--dry-run` 核对计划。
- 默认 `--reset` 会清空当前服务会话（仅内存会话，不删记忆）；不想影响现场请先与 LEAD 确认或使用 `--no-reset`。
- 本脚本**不修改服务、配置文件、既有脚本**；只写 `--out` 指定的 JSON（以及中断时的同名部分结果）。
- 服务重启/配置变更仍只由 LEAD 执行；执行者只跑测试并回报 JSON。

## 8 运行时长与分批建议（重要）

- 当前服务配置（`/status.engine_meta`：n_ctx 32768 / chat_budget 24576 / rollover 阈值 18432 token）
  下单次 `/ask` 可能数秒到数十秒；**40k 字符全量 + 每 turn `/status` 的完整跑批可能耗时较长**
  （本机冒烟：5 turn 约 4–5 分钟，0 error，部分结果已落盘；工具层若限 5 分钟需分批）。
- 建议：`--status-every 5` 降 `/status` 频率；先 `--smoke` 验证链路；正式跑用后台作业
  （`run_in_background`）或分 `--no-reset` 续跑；中断时 JSON 已含 `partial=true` 与已完成 turn，
  可据此判断再续。
- 若只关心 rollover 后召回，可先用 `/status.session.rollover_threshold_tokens` 估算所需字符数，
  设定更低 `--target-chars` 完成一轮后再按需加长。