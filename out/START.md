# 启动（唯一命令）

```powershell
cd D:\llama-mem
python -X utf8 tools/chat_service.py `
  --db kvmem/daily/chat.db `
  --blocks kvmem/daily/blocks `
  --sessions kvmem/daily/sessions `
  --host 127.0.0.1 --port 8765 `
  --retrieval topk --topk 4 --n-gpu-layers 28 `
  --model "D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf"
```

## 本版默认（v1 目标）
- `--lifecycle-cap` **on**：200 软上限，201 允许并给 `capacity_warning`，2000 硬拒；
- `--memory-access` **on**：异步、可丢、可关；
- `--lifecycle-archive` **on**：≥soft 才触发；**首次真实归档需 `--confirm-first-archive`**；
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