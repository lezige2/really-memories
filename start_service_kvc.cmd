@echo off
chcp 65001 >nul
cd /d D:\llama-mem
title llama-mem KV-only 实验服务（显式 Qwen2.5-14B，kvc 会话）
python -X utf8 tools\chat_service.py --port 8765 ^
  --model D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf ^
  --db kvmem\daily\chat.db --blocks kvmem\daily\blocks --sessions kvmem\daily\sessions ^
  --session kvc.json --n-ctx 32768 --chat-start 8192 --n-gpu-layers 28 ^
  --retrieval topk --topk 4 >> kvmem\daily\service_kvc.log 2>&1