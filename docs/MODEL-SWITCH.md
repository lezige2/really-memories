# MODEL-SWITCH（换模型必须做的三步）

> 背景：记忆是 **KV 块**（`memory_block`），块与「模型 + rope + KV 类型」绑定。
> 换模型后旧块会被引擎拒绝（`kvshim_load < 0` / `Incompatible`），
> 表现为 **`/ask` 的 `block_ids` 为空、模型说「记不清」、dry-run 显示未命中**——
> 这不是检索坏了，是块与新模型不兼容。**必须按顺序重建**。

## 0 先停服务（避免它占着 GPU/DB）

```powershell
# 找到 8765 的服务进程并停掉（PID 以实际为准）
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'chat_service.*8765' } |
  Select-Object ProcessId, CommandLine
Stop-Process -Id <PID>
```

## 1 备份 DB 与块目录（不可跳过）

```powershell
$ts = Get-Date -Format "yyyyMMddTHHmmss"
Copy-Item kvmem/daily/chat.db       "kvmem/daily/chat.db.bak-$ts"
Copy-Item -Recurse kvmem/daily/blocks "kvmem/daily/blocks.bak-$ts"
```

## 2 清会话 KV（旧模型的对话/会话 KV 也不能留给新模型）

```powershell
Remove-Item -Force kvmem/daily/sessions/daily.json,
                    kvmem/daily/sessions/daily.chat.kvmem,
                    kvmem/daily/sessions/daily.transcript.json -ErrorAction SilentlyContinue
# 保守做法：清空 sessions 下所有 kvmem/状态文件
Remove-Item -Force kvmem/daily/sessions/*.kvmem -ErrorAction SilentlyContinue
```

## 3 用新模型重建全部记忆块

```powershell
$env:LLAMA_MEM_MODEL = "D:/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf"   # 换成新模型
python -X utf8 - <<'PY'
import os, sys
sys.path.insert(0, "tools")
import kvslots, memory_source as ms

model = os.environ["LLAMA_MEM_MODEL"]
db    = "kvmem/daily/chat.db"
blocks = "kvmem/daily/blocks"
con = ms.connect(db)
eng = kvslots.KVEngine(model, n_ctx=16384, n_seq=8, gpu=34, kv="q8_0")
try:
    names = [r[0] for r in con.execute(
        "SELECT name FROM memory_source WHERE tenant='default' AND scope='private'")]
    for name in names:
        rec = ms.rebuild(eng, con, name, blocks_dir=blocks,
                         model_path=model, seq=6)     # seq6 = 临时建块 seq
        print("rebuilt %-22s n_tokens=%d" % (name, rec["n_tokens"]))
    problems = ms.verify(con, blocks_dir=blocks, model_path=model)
    print("verify problems:", problems if problems else "none")
finally:
    eng.close()
PY
```

## 4 重启服务并验收

```powershell
python -X utf8 tools/chat_service.py --port 8765 `
  --model D:/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf `
  --db kvmem/daily/chat.db --blocks kvmem/daily/blocks `
  --sessions kvmem/daily/sessions --session daily.json `
  --n-ctx 16384 --chat-start 8192 --n-gpu-layers 34 --retrieval topk --topk 4

# 验收（应看到 block_ids 非空、答案含记忆内容）
curl -s http://127.0.0.1:8765/status | Select-String model_pin
curl -s -X POST http://127.0.0.1:8765/ask -H "Content-Type: application/json" `
     -d '{"text":"我的车牌号是多少？"}'
```

## 排错对照

| 现象 | 原因 | 处理 |
|---|---|---|
| `/status` 有 11 条记忆但 `/ask` 的 `block_ids=[]`、回答「记不清」 | 自然模式没有调用检索选择（P0 已修：`_ask_natural` 内调用 `_retrieval_select`） | 确认 chat_daily.py 为修复版并重启服务 |
| 日志出现 `isolated_fallback`/`Incompatible`、块拒绝加载 | 块与当前模型/rope/kv 不匹配 | 回到第 3 步重建 |
| `/status` 的 `model_pin` 仍是旧模型 | 服务启动参数/`start_service.cmd` 未改 | 用新 `--model` 重启 |
| 挂载 0 但 dry-run 也 0 命中 | 会话/索引陈旧或检索 gate 未过 | 清 session KV 后重启；用 `memo.retrieve` 离线复核 |

> 相关 CPU 回归：`python -X utf8 tools/test_retrieval_service_cpu.py`（3 条记忆 + 车牌问句 → 必须挂载）。
