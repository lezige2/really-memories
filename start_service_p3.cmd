@echo off
cd /d D:\llama-mem
set LLAMA_MEM_CHAT_FORMAT=chatml
set LLAMA_MEM_POLICY_FILE=out\policy-ab\P3-memorypos.txt
python -X utf8 tools\chat_service.py --port 8765 --model D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf --db kvmem\daily\chat.db --blocks kvmem\daily\blocks --sessions kvmem\daily\sessions --session eval3.json --n-ctx 32768 --chat-start 8192 --n-gpu-layers 28 --retrieval topk --topk 4 >> kvmem\daily\service_p3.log 2>&1
