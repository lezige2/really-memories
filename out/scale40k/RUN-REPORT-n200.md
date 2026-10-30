# SCALE n200 实测（topk4 / K2-off → K2-on）

2026-10-30 · Qwen2.5-14B-Q4_K_M ngl28 · 服务端口 **8766**（8765 留空）· 已停服务
产物：`kvmem/scale40k/n200/{RESULT.json,RESULT-k2on.json,DATA-AUDIT-n200.json,WRITE-PROBE-n200.json,chat.db,blocks/}`
`out/scale40k/SLOPE-20-50-200.json`、`out/scale40k/{BUILD,RUN,SERVICE}-n200-*.log`

## 0 污染事件与重建

首次 n200 建完后，外部 K2E runner 重连 8765 并对本服务连续 `/reset`，把库从 200 行清到 115、
块文件清到 20。已 interrupt/kill 外部 runner，停服务止损，`--force` 重建。
重建后体检：行 200 / 块 200 / 块文件 200，source↔block 全配对，无孤儿、无 0 字节。

DB 指纹：建完 `5c54ce41…`；评测后 `2d84aefd…`（SQLite WAL checkpoint 造成字节差异）；
逻辑指纹（id:name:hash 有序）`4d23fefe…`；两次查询均为 200/200，未被写污染。

## 1 数据体检（最后重建版，`DATA-AUDIT-n200.json`，ok=true）

- 行 200 / 块 200 / 文件 200；孤儿 0；0 字节 0。
- token：min 9 / mean 216.0 / max 785 / **总 43205**；长块(≥600t)=19（20±10 内）；
  分布 <100:10、100–599:171、600+:19。
- 脏数据 5 对全在：hash 互异、NFKC 去空格后逐对相同、exact dup=0（norm_dup 5 组/10 行）。
- 40 查询：38 个 target 在库 + 2 空负例，id 无重复，文本不含目标值。
- 建库日志无 traceback/ERROR，built=200；seed 40000；三文件 sha 见 audit。

## 2 三档斜率（K2-off，同 40 条）

| 档 | recall@4 | pass | 旧值泄漏 | 拒答 | P50 / P95 | 丢弃/5xx/lock |
|---|---|---|---|---|---|---|
| n20 | 0.769 (10/13) | 0.175 | 0 | 0.375 | 13.6 / 35.2 s | 0/0/0 |
| n50 | 0.824 (14/17) | 0.175 | 0.025 | 0.15 | 14.3 / 21.4 s | 0/0/0 |
| n200 | 0.711 (27/38) | 0.15 | 0.125 | 0.125 | 15.3 / 30.5 s | 0/0/0 |

n20→n50 recall +5.4pp；n50→n200 **−11.3pp**，泄漏 +10pp、pass −2.5pp；延迟 P50 +5%。
n200 建库 260.5 s（200 块，20 长块≈785t）。

## 3 第 201 条写入（`WRITE-PROBE-n200.json`，8/8 通过）

- `POST /remember` → **HTTP 409**，`{"error":{"code":"memory_full","message":"记忆已达上限 200 条…"}}`
  （非 500、进程未崩）。
- 前后 `memory_source` 行数均 200；`/health.memories` 均 200。
- 写入被拒后立刻重问 q081：答案与 block_ids 与写入前**完全一致**，检索未污染。

## 4 K2-on（同库同 40 条，`RESULT-k2on.json`）

| 指标 | K2-off | K2-on |
|---|---|---|
| recall@4 | 0.711 (27/38) | **0.368 (14/38)** |
| pass | 0.15 | 0.2 |
| 旧值泄漏 | 0.125 | **0** |
| 拒答 | 0.125 | 0.025 |
| P50 / P95 | 15.3 / 30.5 s | 9.4 / 17.0 s |
| 5xx / lock | 0/0 | 0/0 |

按 kind（K2-off → K2-on）：
- direct recall 0.9 → **0.1**，paraphrase 0.3 → **0.0**：**误隐严重**（非链事实被同族合并后整族只留 1 块）。
- chain_last 0.7 → 0.8，pass 0.2 → 0.5，泄漏 0.3 → 0：链式“最新值”收窄有效。
- reverse 反序链：pass 0.5 → 0.833，ghost_picked 0/0，K2 仍取 created_at 最新 C。
- 满库（200 行）下 K2 未报错、未暴跌，仍能收窄；代价是同族事实大范围误隐。

## 5 结论与限制

- 20→50 微升，200 回落：**存取保留率**在 200 块/43k token 时 recall 0.71、泄漏 0.125；
  不称“40k 记忆容量”，200 为 `LIBRARY_MAX` 硬上限，201 条写入被结构化拒绝（409 memory_full）。
- K2-on 在满库下可继续收窄且不崩，但会跨人/跨事实误隐（direct/paraphrase 灾难性下降）。
- 40 条固定题只有 13/17/38 条目标在库，跨档比较以 recall@4 为准；n20/n50 的长块为 10 块，
  n200 为 20 块，长块比例不同，P50/P95 仅参考。
- 全部服务已停，8765/8766 均无监听。