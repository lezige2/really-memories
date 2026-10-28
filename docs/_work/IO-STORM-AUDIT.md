# IO-STORM-AUDIT —— 32k 长测卡死 / I/O 风暴排查（记录与归档）

> **状态：审计已到（rev7-auditor）→ 修复中（rev7-impl 已 GO）→ 验收待跑**；本文件只做记录/归档，**不写"已修复"结论**（以修复后验收件为准）。不 commit、不改服务/代码、不重启服务（只由 LEAD 重启）。
> 依据（sha16 / 字节，盘上可核对）：
> - `out/IO-WRITE-AUDIT.json` = **`df85bc6ff796cb02`** / 15,990 B —— **rev7-auditor 写盘审计（11 条写路径、最重 3 条、每轮/rollover 字节估算）**
> - `out/LONG-CONV-HANG.json` = `ee843114679cfbd0` / 315 B（卡死现场）
> - `out/BLOCK-SIZE-PROBE.json` = `4ad1fcc9b9c5285f` / 13,189 B（块/会话体积探针；B≈104.5 KB/token）
> - `out/LONG-CONV-MEMORY.json` = `014ea420b3249888` / 16,426 B（b6 记忆层分析）
> - `out/LONG-CONV-VERIFY.json` = `e2cfc3a32b8b0f8d` / 9,267 B（行为复核）
> - `tmp/io_probe.py` = `8c0c4348e0082d2c` / 13,354 B（code-tracer I/O 实测脚本；`out/IO-PROBE.json` 当前为 partial，未引数）

## 1 背景（卡死现场）

- 32k 配置长测：服务 `n_ctx=32768 / n_gpu_layers=28 / chat_start=8192 / chat_budget=24576 / rollover 阈值 18432 token / kv=q8_0`。
- `out/LONG-CONV-HANG.json`：跑到 **50 turns / 13,615 字符 / chat_tokens=14,091** 时一次 `/ask` **卡死 >180 s**（`ask_timeout_s=180`），**rollovers=0**；卡死期间 `/health` 仍 200（`health_ok_while_ask_hung=true`）⇒ 不是进程死，而是单请求被拖住；日志 `kvmem/qq_logs/longconv.out`（`TimeoutError: timed out`）。
- 目标：定位"长上下文/rollover 场景下写入量爆炸"的真实源头与量级，并跟踪修复/验收。

## 2 三方审计分工（状态）

| 审计方 | 范围 | 状态 / 产物 |
|---|---|---|
| **rev7-auditor** | **代码写盘路径**：每个 `/ask`、`/save`、rollover 前后的写文件清单与次数（append vs 全量重写、`R.build_index` 重建频率、session 快照策略） | ✅ **已完成**：`out/IO-WRITE-AUDIT.json` **`df85bc6ff796cb02`** / 15,990 B（11 条写路径 W1–W11；最重 3 条见 §3） |
| **code-tracer** | **实测字节**：逐轮 `/ask` 前后 `kvmem/daily/**` 体积差、单文件 top、rollover 写入量 | ⏳ 脚本 `tmp/io_probe.py 8c0c4348`；`out/IO-PROBE.json` 目前 **partial/空 summary**，待稳定后引数 |
| **b6-designer（记忆层）** | rollover 归档/摘要/auto_turn 块的产生与 200 库上限、槽位/检索命中；为何长测没触发 rollover | ✅ 已落盘：`out/LONG-CONV-MEMORY.json` `014ea420b3249888`（§3.e） |

## 3 审计结论（rev7-auditor，已到）

**写路径全景（11 条，W1–W11）**：W1 会话 KV 快照 `eng.save(seq0)`；W2 rollover 前整段保存（同 W1 调用点）；W3 archive KV 块；W4 summary KV 块；W5 auto_turn 轮块；W6 archive 全文文本 + sidecar；W7 transcript/manifest 原子写；W8 logger 逐事件追加（session+daily jsonl，**每事件 1 次 open+write+fsync**）；W9 DB 写入；W10 `R.build_index` 全量重建（**仅在记忆变更轮**）；W11 rollover 元数据回填 + lease 记录。

**最重 3 条（修复前量级）**

| 排名 | 写路径 | 修复前 | 当前护栏后 |
|---|---|---|---|
| 1 | **W5 auto_turn 轮块**（每 chunk 全量 KV） | 每块 **~130–200 MB**；每次 rollover **5–11 块** ⇒ **0.5–1.5 GB/次 rollover** | `BLOCK_MAX_CHARS=140` ⇒ 每块 ≤**11.7 MB** |
| 2 | **W1/W2 会话 KV 快照** `eng.save(seq0)` | **528 MB @5,060 tok**（实测）；662 MB @6,340 tok；历史 1.95 GB | `rollover_skip_save_over_tokens=8000` ⇒ rollover 内跳过；**显式 `/save`/`close` 仍可写** |
| 3 | **W3 archive KV 块**（历史全文） | **202 MB（≈1,935 tok）** | 改为索引句（~40 字）⇒ ~3.4 MB；W4 summary 历史 136 MB（≈1,300 tok）⇒ `summary[:120]` ~10 MB |

**每 10 轮 / rollover 字节（审计估算，B≈104.5 KB/token）**

- 纯聊天（无陈述、无 rollover）：logger **16 KB / 10 轮**（40 次 fsync），DB/块 0。
- 含 1 条短陈述：+ 块 **2.5–5 MB**（上限 11.7 MB）+ DB 行与**全量索引重建 0.1–5 MB** ⇒ 典型 **3–10 MB / 10 轮**。
- rollover（当前护栏后）：archive 3.4 + summary ~10 + turn 块 5×11.7≈58 + 文本/元数据 0.1 ≈ **72–75 MB/次**（session 保存已跳过）⇒ 摊到 10 轮约 **15 MB**。
- **修复前 rollover**：session 528 MB + archive 202 + summary 136 + turn chunk(130–200 MB)×5–11 ⇒ **1.0–2.5 GB/次**，摊到 10 轮 **~200–500 MB/10 轮**（"500MB 级"来源）。

**关键发现（审计原文要点）**：① 500 MB 级写盘**全部来自 KV 状态文件**（`file ≈ 12+4N+104,553·N`），非文本/transcript；② 当前代码已加两道护栏（`BLOCK_MAX_CHARS=140`、rollover 内 `before>8000` 跳过整段保存）⇒ 500 MB 级单文件基本压到 ≤12 MB（**session 显式 save 除外**）；③ 历史 202 MB archive/136 MB summary/528 MB session 均符合 B≈104.5 KB/token（≈1,935/1,300/5,050 tok）；④ **rollover 是唯一大写入点**，且 rollover 时 `2+N` 次建块 ⇒ `2+N` 次全量索引重建；⑤ IOPS 风险在 logger（每事件 fsync ×2 文件）、DB commit、全量索引重建。

**b6 记忆层（已落盘，`LONG-CONV-MEMORY.json`）**：live 实测 40k 字符会触发 rollover（预计 ~23,009 字符）；**auto_turn 按轮写、200 库上限被吃满后 archive/summary 写不进去**（模拟 round1 dropped 310 / cap_dropped 121 / db_rows=200；round2/3 全被 cap 丢弃）⇒ 若 rollover 恰逢库满，归档/摘要缺失；另有槽位缺口（"妻子"→person 无）与检索回退缺口（`D_minimal_fixes` 5 条）。

## 4 修复与验收（进行中 / 待跑）

- **rev7-impl 已 GO 修复**，顺序（LEAD 定）：**① 会话保存 → ② 索引增量 → ③ 块上限 → ④ 看门狗 → ⑤ fsync → ⑥ n_seq**。
- 已观察到的护栏（审计口径）：块正文截断（140 字）+ rollover 内跳过大 session 保存；其余修复项（索引增量、fsync 合并、看门狗等）**待验收件确认**。
- **验收待跑**：32k 长测复现 + `tmp/io_probe.py` 稳定读数 + `out/IO-PROBE.json` 落盘 + 卡死是否消失。

| # | 待验收项 | 期望（跑后填） | 来源/状态 |
|---|---|---|---|
| 1 | 每 10 轮写入量（修复后） | 目标回到 MB 级；`out/IO-PROBE.json` 稳定后填 | code-tracer ⏳ |
| 2 | 单次 rollover 写入量（修复后） | 目标 ≤~75 MB（当前护栏估算）→ 修复后应更低 | code-tracer ⏳ |
| 3 | session 显式 `/save` 体积上限 | 是否仍可写 500 MB+；需 LEAD 定策略（上限/异步/告警） | 审计已标，修复待确认 |
| 4 | 索引重建（W10） | 是否已改增量/脏读；单次耗时 | rev7-impl 修复后确认 |
| 5 | 卡死复现 | 14k token 卡死是否消失；`/ask` 超时是否恢复 | 验收跑 |
| 6 | logger fsync 次数 | 每事件 4 次 fsync 是否合并/降频 | 修复后确认 |
| 7 | **结论** | 根因=KV 全量写盘 + rollover 多块 + 全量索引重建；修复后是否闭环 | **待验收件，不预写** |

## 5 后续问题清单

1. **session 显式 save 仍无上限**：`/save`/`close` 可写 500 MB+；是否加"超过 N token 提示/异步/限制"需 LEAD 定。
2. **rollover 多块一次性写**：修复顺序里"块上限"先于"索引增量"是否够；若 archive/summary 先写，cap 满时仍可能丢块（b6 已证）。
3. **索引全量重建**：W10 在记忆变更轮触发；rollover 时 `2+N` 次重建 ⇒ 是否改为增量/延迟标记。
4. **fsync 策略**：logger 每事件 4 次 fsync；是否合并为批量/flush 间隔（注意崩溃一致性）。
5. **看门狗**：卡死时 `/health` 200 但 `/ask` 无响应——看门狗应检测"请求内卡点"还是仅进程存活？
6. **验收必须复现 32k 卡死现场**：需 LEAD 重启并复跑 `tmp/long_conv_test.py`/`io_probe.py`；执行者不重启、不改配置。
7. **读数一致性**：三方产物（审计估算 vs 实测）差异要在验收报告并列，不互相替代。

## 6 纪律

- 只写本文；不改服务/代码/既有文件；不重启服务（只由 LEAD 重启）；不 commit。
- 数字更新只从落盘 JSON 抄，逐项标 sha16；验收件未到前不写"已修复/根因闭合"结论。