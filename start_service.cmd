@echo off
chcp 65001 >nul
cd /d D:\llama-mem
title llama-mem 本地 14B 记忆服务（DSH provider: local14b）
if not exist kvmem\daily mkdir kvmem\daily
if not exist kvmem\daily\blocks mkdir kvmem\daily\blocks
if not exist kvmem\daily\sessions mkdir kvmem\daily\sessions
echo 正在启动本地 14B 记忆服务（127.0.0.1:8765）—— 36/34 层实测选型：n_ctx=16384, n_gpu_layers=34, chat_start=8192
echo 首次加载模型约 15-60 秒；日志：kvmem\daily\service.log
python -X utf8 tools\chat_service.py --port 8765 --n-ctx 16384 --chat-start 8192 --n-gpu-layers 34 --retrieval topk --topk 4 --db kvmem\daily\chat.db --blocks kvmem\daily\blocks --sessions kvmem\daily\sessions --session daily.json >> kvmem\daily\service.log 2>&1
if errorlevel 1 (
  echo.
  echo 服务异常退出，日志见 kvmem\daily\service.log
  pause
)
