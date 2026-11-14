# 实验隔离与事故防复发规则（2026-10-30）

> 事故：40k n200 在 8765 被 C2 的 K2E runner 重连后 `/reset`+`/remember`，200 行→115、200 块→20。
> 结论：并发隔离缺失 + 旧 runner 未杀 + 服务重启自动重连 + 无 DB 指纹门禁。

## 1 端口/库租约（硬规则）

| 端口 | 用途 | DB | Owner |
|---|---|---|---|
| 8765 | K2/verifier 产品验收 | `kvmem/daily/chat.db` | C2/A |
| 8766 | 40k 规模测试 | `kvmem/scale40k/n*/chat.db` | C6 |
| 8767+ | 其他实验，按需 | 独立副本 | 申请者 |

- **禁止复用 8765 跑规模/临时实验**；一个实验一个端口一个 DB。
- 服务启动前写租约文件 `out/EXPERIMENT-LEASE.json`（port/db/owner/pid/started_at），结束删除。

## 2 停/起服务

1. 停服务后必须确认：`netstat` 无 LISTENING、无 `run_training_eval`/客户端进程；
2. 起服务后记录 PID/uptime/`/health` model_size/memories，写入租约；
3. 若发现同一端口多个 PID → RED，立即停。

## 3 runner 门禁（防写错库）

- 请求 `/health`，校验 `model_size=8988110976` + `memories` 等于预期；
- 请求 `/status` 或直接读 DB，校验 **DB 指纹**（rows/sha256 前缀）与租约一致；不符 **ABORT，不写库**；
- `--reset-per-case`/`remember` 前再校验一次 rows；
- runner 启动时打印 port/db/owner，日志落 `out/`。

## 4 数据保护

- 评测前 `cp chat.db chat.db.bak-<ts>`，记录 sha；
- 污染后只能用备份重建，不得手改库绕过；
- 每次重建后重跑 DATA-AUDIT（行/块/孤儿/长块/脏对/查询 target）。

## 5 事故复盘模板

- 时间线、PID/端口、被污染文件/sha、根因分类（隔离/进程/门禁/人为）、修复、复发判据。
- 本次：根因=端口复用 + 旧 runner 未杀 + 无 DB 指纹；修复=8766 隔离 + 租约 + fingerprint preflight + 备份。