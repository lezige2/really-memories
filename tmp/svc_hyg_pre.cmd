@echo off
cd /d D:\llama-mem
set VERIFIER_VERSION=v2.2
"C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe" -X utf8 tools\chat_service.py --port 8765 --model D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf --db kvmem\hygiene\pre\chat.db --blocks kvmem\hygiene\pre\blocks --sessions kvmem\daily\sessions --session kvc.json --n-ctx 32768 --chat-start 8192 --n-gpu-layers 28 --retrieval topk --topk 4 --k2-family >> kvmem/daily/service_hyg_pre.out 2>> kvmem/daily/service_hyg_pre.err
