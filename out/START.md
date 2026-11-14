# 启动（唯一命令）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\llama-mem\out\ops\start-wmi.ps1"
```

- `start-wmi.ps1` → `launch_service.py`，用 `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` 起无控制台子进程；PID 看 `netstat :8765`；
- 日志 `out/p1-enable/service.out/.err`；
- 不要用会话内后台 job / `Start-Process` 起服务：job 结束时可能带走子进程（已发生 exit 127 两次）；
- 如需前台调试，才用下面的 python 命令。

## 本版默认（v1 目标）
- `--lifecycle-cap` **on**：200 软上限，201 允许并给 `capacity_warning`，2000 硬拒；
- `--memory-access` **on**：异步、可丢、可关；
- `--lifecycle-archive` **on**：≥soft 才触发；**首次真实归档需 `--confirm-first-archive`（容量压力 + 副本演练通过后）**；触发时必须显示“已归档 N 条，可回滚”，禁止静默；
- `--lifecycle-fallback` **on**：主池空才查归档；
- `--audit` **on**：决策类事件；retrieve 仅 `--audit-debug`；
- K2 off、verifier v1、event off、TTS off。

## 启动后
1. 记录 PID、启动时间、配置指纹、DB sha；
2. `curl http://127.0.0.1:8765/health`；
3. `python -X utf8 tools/healthcheck.py`；
4. 跑验收清单。

## 停止
- Ctrl+C 或结束 PID；先确认无 `/ask` 在跑。
- 不要同时起两个 8765；启动前 `netstat -ano | findstr :8765`。

## 关闭默认（回滚）
```powershell
python -X utf8 tools/chat_service.py ... --no-lifecycle-cap --no-memory-access --no-lifecycle-archive --no-lifecycle-fallback --no-audit
```