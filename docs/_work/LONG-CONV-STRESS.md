# LONG-CONV-STRESS —— 4 万字符长对话 + rollover 召回压测（记录与归档）

> **状态：脚本已就绪；正式读数待 `out/LONG-CONV-TEST.json` 落盘后补齐（当前未生成 ⇒ 本文不写结论）**。
> 分工：**LEAD 负责运行与重启服务**；本文只做记录/归档，不改服务、不改代码、不 commit。
> 依据（盘上可核对）：`tmp/long_conv_test_v2.py` = `68775f8248ae21d9` / 21,534 B（主压测）；`tmp/long_conv_verify.py` = `73bb443f03d3f558` / 13,574 B（独立复核）；`tmp/long_conv_test.py` = `adf5d8b202d639f4` / 3,209 B（v1 旧版，仅对照）。

## 1 目的

1. 在约 **40,000 字符**连续对话中**触发 rollover**（上下文自动压缩），验证系统不 reset、不卡死；
2. 检验 **8 个事实**（按累计字符阈值埋在早期/中期/近期三档）**跨 rollover 后能否召回**；
3. 同一事实**重复问 3 次**答案是否稳定一致（一致性）；
4. 跨 rollover 后追问「刚才说的」是否还能指出 rollover 前最后一条具体事实；
5. 连续 10 问不 reset 时响应稳定、`chat_tokens` 线性增长（无隐性重置/卡死）；
6. 记录延迟、错误与重试，为后续「长上下文可用性」结论提供可复跑证据。

## 2 方法（脚本 / 埋点 / 探针）

- **调用方式**：只读 HTTP 调 `http://127.0.0.1:8765`（`/ask`、`/status`、`/reset`）；**不重启服务**（服务只由 LEAD 重启）；默认开始时 `POST /reset`（仅清内存会话，不删记忆；`--no-reset` 可关闭）。
- **命令**（正式跑，输出必须指到 `out/`，与复核脚本输入对齐）：
  ```bash
  python -X utf8 tmp/long_conv_test_v2.py --dry-run                       # 零请求自检
  python -X utf8 tmp/long_conv_test_v2.py --smoke                         # ≤2k 字符冒烟
  python -X utf8 tmp/long_conv_test_v2.py --target-chars 40000 --out out/LONG-CONV-TEST.json
  python -X utf8 tmp/long_conv_verify.py                                  # 独立复核 → out/LONG-CONV-VERIFY.json
  ```
  参数：`--request-timeout 300`、`--retries 3`（5xx/429/断连指数退避）、`--seed 20261028`、`--max-turns 500`、`--status-every 1`。
- **事实埋点**（8 条，阈值 `3000/6500/11000/16000/21000/26000/32000/37000` 字符）：

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

  填充语只做闲聊陈述（不含关键词，seed 固定可复现）。
- **探针/埋点**：逐 turn 记 `chat_tokens`（来自 `/status.session`）、`elapsed_s`、`attempts`、`error`、`state`、`refused`、`rollover`；每 turn 前后记录；`rollovers[]` 记 turn/字符数/token 前后值；`/status` 读 `session.rollover_at`、`session.rollover_threshold_tokens`、`engine_meta.n_ctx`（只读）。
- **场景**：`probes.facts`（8 条召回）、`probes.repeated`（最近事实×3，答案去空格全等=consistent）、`probes.post_rollover`（跨 rollover 追问）、`scenarios.no_reset_continuous`（10 连问 + `tokens_start/end/delta`）、`errors[]`。
- **判读**（脚本内固定）：`PASS` = 8 事实全过 **且** 重复 3 次全过且一致 **且** post_rollover 非 False（null=未触发 rollover，不算失败）**且** 10 连问全 ok；其余为 `CHECK`（需人工结合 turns/errors/rollovers 判读）。

## 3 结果（**待填**）

产件（未落盘前不写数字/结论）：`out/LONG-CONV-TEST.json`【待落盘】、`out/LONG-CONV-VERIFY.json`【待落盘】。

| 项 | 读数 | 备注 |
|---|---|---|
| 累计字符 / turn 数 / 脚本 sha | `【待填】` | 以 JSON `plan`+`summary` 为准 |
| rollover 是否触发 / 次数 / 阈值 token | `【待填】` | `summary.rollover_triggered`、`rollovers[]` |
| 8 事实召回（总/通过、按档 early/mid/recent） | `【待填】` | `summary.facts_recall` |
| 重复问 3 次一致性 | `【待填】` | `summary.repeated` |
| 跨 rollover「刚才说的」 | `【待填】` | `summary.post_rollover` |
| 10 连问 tokens 增长/是否卡死 | `【待填】` | `summary.no_reset_continuous` |
| 错误/重试、延迟（P50/P95，若 JSON 可算） | `【待填】` | `turns[].elapsed_s`、`errors[]` |
| 独立复核结论（行为/上下文正确性） | `【待填】` | `out/LONG-CONV-VERIFY.json` |
| `summary.verdict` / 一句话结论 | `【待填】` | PASS / CHECK + 人工判读 |

> 填表规则：所有数字**只从落盘 JSON 抄**，不手写估算；若 `partial=true` 或 `rollover_triggered=false`，必须在结论里显式说明（不得当 PASS）。

## 4 后续问题清单

1. **产物路径不一致**：v2 脚本默认 `--out tmp/LONG-CONV-TEST-V2.json`，而 `tmp/long_conv_verify.py` 按 `out/LONG-CONV-TEST.json` 读——正式跑必须显式 `--out out/LONG-CONV-TEST.json`，否则复核会读不到/读旧件。
2. **40k 是否足够多次 rollover**：rollover 阈值由 `/status.session.rollover_threshold_tokens` 决定；若只触发 1 次，需要更高 `--target-chars` 或确认预算，才能覆盖"跨多次压缩"。
3. **early 档召回来源**：early 事实经 rollover 后是命中 `auto_archive` 原文块还是 `auto_summary` 摘要？需结合 `/memories` 与块记录区分"摘要召回"vs"原文召回"。
4. **一致性口径**：`repeated.consistent` 用"去空格后完全一致"偏严；口语化改写是否应算一致，需 LEAD 定口径。
5. **10 连问 token 线性**：`no_reset_continuous` 的 token 增长是否在 rollover 点回落（压缩预期）还是持续增长（泄漏/未压缩）；需按 turn 看曲线。
6. **超时/重试对 verdict 的影响**：`attempts>1` 或 `errors[]` 非空时，即使 PASS 也要标注"重试后成功"；服务单线程长上下文请求易超时（本次预跑 `/status` 已见超时，需记 `request-timeout` 设置）。
7. **并发/多人同时压测**：单线程服务下并发会排队，读数不可与单跑混比；需记录是否有外部请求并行。
8. **多次/多 seed 稳健性**：单次 PASS 不足以当能力结论；至少 2–3 次（可不同 seed）读数并列，且不据此调参（沿用 R10 精神：失败不调参重跑）。
9. **结果件是否入库**：`out/LONG-CONV-TEST.json`/`VERIFY` 属产品/行为证据，入 git 前需 LEAD 确认口径（当前 git 已跟踪 `out/`）。

## 5 纪律

- 不改服务/代码/既有文件；不重启服务（只由 LEAD 重启）；不 commit。
- 只写本文件与后续"待填"数字；结果件由脚本落盘，本文只引用其 sha16 与字段。