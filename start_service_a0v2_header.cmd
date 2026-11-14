@echo off
cd /d D:\llama-mem
set LLAMA_MEM_CHAT_FORMAT=chatml
set LLAMA_MEM_POLICY_FILE=out\policy-ab\P1-minimal.txt
python -X utf8 tools\chat_service.py --port 8766 --model D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf --db kvmem\a0v2_header\chat.db --blocks kvmem\a0v2_header\blocks --sessions kvmem\a0v2_header\sessions --session a0.json --n-ctx 32768 --chat-start 8192 --n-gpu-layers 28 --retrieval topk --topk 4 >> kvmem\a0v2_header\service.log 2>&1
