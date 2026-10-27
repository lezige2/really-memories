# WORKER-WATCHDOG-DESIGN（F2：engine 独立 worker + deadline/watchdog）

> 状态：设计稿（P1，不直接改代码）；目标：/health 永不因 decode 卡死、单请求有界、崩溃后可从 save 恢复；保持现有 KV/seq 语义不变。
> 前置事实：native decode 在 ctypes 进入 C 后不可取消；线程 join/timeout 只能“假装超时”，不能止损。唯一可靠终止是进程级。

## 1 架构（split-process）

- 前端进程：`chat_service`（HTTP/OpenAI 兼容），只做协议、鉴权边界、限流、deadline、错误映射；**不持有 KVEngine**。
- worker 进程：`engine_worker`（spawn，非 fork；Windows 下独立进程组）。持有 model、KVEngine、sqlite 连接、GuardedLeases、memory_isolated 的 seq6/7 生命周期。
- IPC：本机回环 socket（Windows named pipe 或 127.0.0.1 随机端口）上的 JSON Lines；一请求一响应 + 独立心跳。前缀长度/换行二选一，固定版本 `proto=1`。
- 前端 `/health` 不取 worker 请求队列锁；只返回 `{worker_alive, last_heartbeat_ms, busy_op, last_error}`，允许 200 但 `status=degraded`。

## 2 协议（proto=1）

- `req = {id, op, deadline_ms, payload}`；op ∈ `ask|remember|forget|save|load|rollover|mount|shutdown`。
- `resp = {id, status, answer?, block_ids?, refused?, latency_ms?, error?, worker_seq_state?}`；status ∈ `ok|error|degraded|timeout`。
- 单连接串行队列（worker 内一次只执行一个 op）；请求 id 幂等：重复 id 返回上次结果，不重复写记忆。
- 心跳 `{ts, n_tokens_seq0, current_op, progress}` 每 1s 一次；`n_tokens/progress` 用于检测 decode 停摆。
- 不支持“打断当前 decode”的 cancel；前端超时后只能由 supervisor 终止 worker。

## 3 deadline 与 watchdog

- 前端 deadline（默认）：ask 120s（含 retrieval+最多两轮生成+verify/repair）、save/load/rollover 30s、remember/forget 10s；可配 `WORKER_DEADLINE_*`。
- worker 自监控：current_op 开始时间 + 心跳 progress 不变超过 `stall_s=15s` ⇒ 标记 stalled，不再接新 op。
- supervisor（前端子进程）：心跳断开或 stalled 超 `grace=5s` ⇒ `SIGTERM`→2s→`SIGKILL`（Windows 用 TerminateProcess）；记录 kill 原因/op/seq token 快照（仅计数，不记原文）。
- 前端收到 timeout/degraded：返回固定 `未接上（worker timeout）`，**不返回半截答案**，不重试生成。

## 4 恢复语义

- worker 启动时：打开 model/DB → `load` 最近一次成功 save 的 session → 重建 seq0 历史与记忆挂载 → 清空 seq6/7 scratch → 才接受 op。
- save 在 worker 内串行执行，走现有 tmp+replace；kill 在 save 中途 ⇒ 旧 save 保留，恢复旧状态；当前 ask 结果丢失，记账 `aborted_inflight`。
- 每次成功 ask 后可选 checkpoint（`WORKER_CHECKPOINT_EVERY_TURNS`）；rollover 前强制 save；save 成功回执后才提交“已持久化”标记。
- 幂等：`remember` 重复 id/同文本由现有 source_hash 去重；`ask` 不写长期记忆，重试无副作用。
- 恢复后不假设上一次 seq 状态；seq0 从 save 重建，seq6/7 必须 reset 后才使用。

## 5 顺序与 lease

- 所有 op 在 worker 内串行；memory mount、isolated ask、rollover、save 不得并发；isolated 的 seq6/7 在 finally 清理并归还。
- GuardedLeases 只在 worker 内使用；attach/detach/register 与 op 同生命周期。
- 前端只转发 op，不直接调用 chat_daily/engine；保持“记忆文本不进 prompt/日志”的现有边界。

## 6 失败注入测试计划（必须）

1. fake engine 在 `ask` 永久 sleep ⇒ 心跳断/超时 ⇒ worker 被杀；/health <100ms 仍 200；请求返回 timeout；重启后 load 恢复 seq0。
2. fake engine 在 `mount/save/rollover` 中途 hang ⇒ 被杀；旧 session 文件仍可 load；无半写产物。
3. SIGKILL 在 ask 中途/在 save 中途各一次 ⇒ 重启/load 后 seq0 token 数与最近 checkpoint 一致；无重复 memory_source 行。
4. IPC 断连/半包/超长包/重复 id/乱序 id ⇒ 前端返回 error，不重复执行；worker 不崩溃。
5. 队列积压 + 多请求 ⇒ deadline 各自生效；/health 不受排队影响；无并发 engine op。
6. GPU 真机（可选一次）：单次 ask 中 kill worker ⇒ 重启后 1 次 ask 正常；seq0/save/rollover 断言不变；全程无记忆原文进日志。
7. 验收标准：卡死恢复 ≤ (stall 15s + grace 5s + 重启/load 时间)；`/health` 在 worker 卡死时始终可答；`ask` 最坏返回 bounded error。

## 7 边界

- 不改 shim/DLL；不改记忆文本/判据；不改 save 文件格式；不把 watchdog 的 kill 当作“运行结果”（必须记 `未接上`）。
- 先 feature flag 灰度：`WORKER_MODE=0/1`；0 保持现路径，1 走 worker；对比同请求答案/延迟后才切换默认。