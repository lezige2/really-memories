@echo off
cd /d D:\llama-mem
"C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe" -X utf8 tools\chat_service.py --port 8765 --model D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf --db kvmem\mt5on\chat.db --blocks kvmem\mt5on\blocks --sessions kvmem\daily\sessions --session kvc.json --n-ctx 32768 --chat-start 8192 --n-gpu-layers 28 --retrieval topk --topk 4 --lifecycle-cap --memory-access --lifecycle-archive --lifecycle-fallback --audit >> kvmem\daily\service_mt5on.out 2>> kvmem\daily\service_mt5on.err
