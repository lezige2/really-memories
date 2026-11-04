# 安装 / 升级 / 环境前提（v1 目标）

## 1 环境前提
- Windows 11 x64；Python 3.14（当前 runtime）。
- 模型：`D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf`（8,988,110,976 B；mtime 1793102210）。
- GPU：10G 级；默认 `--n-gpu-layers 28`，CPU 层 20。
- 依赖：`torch 2.15 CPU`、`transformers`（仅 TTS/辅助，不用于记忆主路径）；本地 `kvshim_vk.dll`。
- 不需要云、网盘、外部 API。

## 2 新装（空库）
```powershell
cd D:\llama-mem
python -X utf8 tools/healthcheck.py --db kvmem/daily/chat.db --blocks kvmem/daily/blocks
# 首次启动会自动建 memory_access / memory_archive；不动 memory_source
python -X utf8 tools/chat_service.py --db kvmem/daily/chat.db --blocks kvmem/daily/blocks --sessions kvmem/daily/sessions --host 127.0.0.1 --port 8765 --retrieval topk --topk 4 --n-gpu-layers 28 --model "D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf"
```

## 3 旧版升级
1. 停旧服务；
2. `tools/rollback_entry.py backup --db kvmem/daily/chat.db --out out/upgrade/chat.db --apply`；
3. 备份 `kvmem/daily/blocks`；
4. 直接启动新版：`ensure_schema` 只加 `memory_access`/`memory_archive`，不改 `memory_source` 列；
5. 跑 `tools/healthcheck.py`；
6. 首次真实归档前，必须由用户执行一次：
   `python tools/chat_service.py ... --confirm-first-archive`（或写状态文件 `out/p1/archive_first_confirmed`）。

## 4 首次空库启动
- 空库也能起；`memory_source` 0 行时 `healthcheck` 的 `source_rows` 会失败，属预期；
- 先写 1 条 `/remember` 再跑健康检查。

## 5 故障排查
| 现象 | 处理 |
|---|---|
| 201 仍 409 | 默认未生效/旧进程；查 `--lifecycle-cap` 默认、端口是否单监听 |
| `Incompatible: ... different model` | 块与当前模型不匹配；不要删块，查 `model_path/model_mtime`，用同模型重建 |
| `SQLITE_BUSY/locked` | 查 access 写线程/其他进程；`busy_timeout` 5s，停重复服务 |
| GPU OOM | 降 `--n-gpu-layers`，查残留服务 |
| 归档不触发 | 20 条库不会触发；副本回拨 created_at 造 200 条验证 |
| 首次归档被 block | 需要 `--confirm-first-archive` 或状态文件 |
| 审计太多/太少 | 默认决策类；`--audit-debug` 才写 retrieve；轮转 8MB/14 天 |

## 6 非目标（明确出局）
- QQ 语音（桥只文本，不支持文件/语音）；
- Web/桌面 UI；
- 70B/云端模型；
- 多用户/多主体；
- 40k 生产容量（仅压测研究）。