# PRODUCT-C-LOG-SPEC（个体日志 · v1.0 预注册）

> 件性质：**个体日志验收口径**（先于实现；口径冻结后不放宽）· 作者：LEAD · frozen_at: 2026-10-26T23:56:00+08:00 · frozen_rev: 1
> 依据：用户要求「小助手必须有一个个体日志，以防万一出现我们不知道的问题」；本件是 `PRODUCT-C-SPEC.md`（`694ebbad136efbec`）的追加口径，S1–S6 不变，新增 **S7 日志完整性**。
> 身份：`assistant_id` 是**不可变 UUID**（首次启动生成）；显示名（用户后起）只改 `display_name`，不改 `assistant_id`，因此改名不影响日志连续性。

## 1 目标

小助手自己的每一个动作都留痕、可复核、可追责；出问题时能回答四个问题：
1) **它当时收到了什么**（输入原文/哈希、会话、上下文）；
2) **它做了什么**（命中了哪些记忆块、引擎 seq/cells、调用了哪个端点）；
3) **它答了什么**（回答原文/哈希、延迟、资源峰值）；
4) **异常从哪开始**（错误栈、最后一次完好事件、崩溃恢复记录）。

## 2 存储布局

```
kvmem/assistant/
  manifest.json                     # assistant_id(UUID)、display_name、created_at、schema_version、pins、log_config
  sessions/<session_id>.jsonl       # 逐事件，一行一条完整 JSON（append-only）
  daily/<YYYY-MM-DD>.jsonl          # 跨会话日索引（事件子集：ts/seq/session/event/latency/error）
  incidents.jsonl                   # 错误/异常（severity: info|warn|error|fatal）
  audit_index.json                  # 链校验摘要：最后一条 chain_sha16、行数、最后写入时间
```

- 只写本机；只追加（append-only）；**不覆盖、不改写历史行**。
- 每次追加后 `flush + fsync`；写入用「整行一次写出 + 行末 `\n`」，崩溃最多丢最后一行，不得出现半行。
- 文件按天/按会话切分；单文件 >64 MiB 或 >20 万行时切新片（`<name>.part2.jsonl`），并写 `rotation` 事件。

## 3 事件模型（schema `assistant_log_v1`）

每行公共字段：`schema, seq`（会话内单调递增，从 1 起）、`ts`（ISO8601 带 +08:00）、`assistant_id`、`session_id`、`event`、`pid`、`chain_sha16`（上一行整行的 sha256 前 16 位；首行为 `""`；用于防篡改/断行定位）。

事件类型与必填：

| event | 必填字段 |
|---|---|
| `session_start` / `session_resume` | pins{model_sha16, model_bytes, dll_sha16, spec_pin, code_sha16}、log_config |
| `ask` | input_text（或 input_sha16+input_len，按 log_config）、session_tokens |
| `answer` | answer_text（或哈希）、latency_ms、block_ids[]、engine{seq_ids[], cells}、vram_gib、tokens_out |
| `refuse` | reason（no_memory/parse/no_context/...）、input 对应 ask 的 seq |
| `remember` | id、first_line、len_tokens、block_sha16 |
| `forget` | id 或 all、deleted_count、confirm(true) |
| `memories_list` | count |
| `save` / `load` | path、sha16、bytes |
| `status` | vram_gib、memories、session_tokens |
| `error` | code、message、stack、where |
| `warning` | code、message、evidence |
| `crash_recovered` | last_seq、last_event、last_ts、unclean(true)、recovered_memories |
| `session_end` | reason(user_quit/eof/error)、duration_s、n_events |

## 4 隐私与内容策略（`log_config.mode`）

- `full`：记录原文（默认在本机单人环境）；
- `redacted`：对已知敏感模式（身份证 18 位、手机号 11 位、密码/密钥行的值）**打码**后再写；但保留 `input_sha16` 保证可对账；
- `hash_only`：只记哈希与长度，不记原文（最保守）。
- 无论哪种模式：**禁止**把密码/证件号写入 `manifest.json`、`daily/`、`incidents.jsonl`；`redacted/hash_only` 模式下 `daily/` 只记事件与延迟。
- 提供 `/log purge <before|all>`（需二次确认）与文档说明"日志含你的个人信息，删前先导出"。

## 5 崩溃与异常

1. 启动时扫描最后一个会话文件：若末事件不是 `session_end` ⇒ 写 `crash_recovered`（记录 last_seq/last_ts/最后事件类型），并在终端提示"上次异常退出，已恢复可核对"。
2. 任何未捕获异常 ⇒ `incidents.jsonl` 写 `error`（含 stack）+ 会话内 `error`，进程退出码非 0。
3. 引擎/显存异常（fuse 超限、VRAM 采样失败）⇒ `warning`/`error` 带 vram 读数。
4. `chain_sha16` 断链 ⇒ `tools/inspect_logs.py --verify` 报 `broken_chain` 并给出行号。

## 6 工具

`tools/inspect_logs.py`（CPU-only，零 GPU）：
- `--verify`：逐行校验 JSON 合法、seq 连续、chain_sha16 连续、必填字段齐全；exit 0/1。
- `--summary [session_id]`：事件计数、拒绝率、P50/P95 延迟、VRAM 峰值、错误数、崩溃恢复次数。
- `--tail N` / `--grep <kw>`：排障用。
- `--export <path>`：导出脱敏摘要（不含原文），供你发我看。

## 7 新增验收 S7（并入 C-V1-ACCEPT）

- **S7a 完整性**：S1–S6 全流程跑完后，`inspect_logs.py --verify` exit 0；每次 `ask` 都有对应 `answer`/`refuse`，seq 无缺号。
- **S7b 崩溃留痕**：在 `ask` 进行中 `taskkill /F` 强杀 → 重开进程：出现 `crash_recovered` 事件（含 last_seq/last_ts），此前事件完好，`--verify` 仍 exit 0。
- **S7c 隐私**：`redacted` 模式下，测试输入含"手机号 13800138000 / 身份证 / 密码"字样 → 日志中该值被打码、`input_sha16` 仍在。
- **S7d 可核对性**：任取一条 `answer` 事件，能凭 `block_ids[]` 在 `--summary` 中定位到对应记忆块，且 `engine.cells` 与当时 `/status` 一致（允许 ±1 次采样）。

## 8 不变式

- 日志只追加；不改历史；`assistant_id` 终身不变；改名不改身份。
- 日志不写入模型输出以外的私密推导；不联网上传。
- 日志缺失/断链 ⇒ 该次验收记**未接上**（不是通过）；不得事后补写伪造历史。