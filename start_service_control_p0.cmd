@echo off
cd /d D:\llama-mem
set LLAMA_MEM_CHAT_FORMAT=chatml
python -X utf8 tools\chat_service.py --port 8766 --model D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf --db kvmem\sft_control\chat.db --blocks kvmem\sft_control\blocks --sessions kvmem\sft_control\sessions --session control.json --n-ctx 32768 --chat-start 8192 --n-gpu-layers 28 --retrieval topk --topk 4 >> kvmem\sft_control\service.log 2>&1
