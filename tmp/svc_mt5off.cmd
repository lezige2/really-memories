@echo off
cd /d D:\llama-mem
"C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe" -X utf8 tools\chat_service.py --port 8765 --model D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf --db kvmem\mt5off\chat.db --blocks kvmem\mt5off\blocks --sessions kvmem\daily\sessions --session kvc.json --n-ctx 32768 --chat-start 8192 --n-gpu-layers 28 --retrieval topk --topk 4 --no-lifecycle-cap --no-memory-access --no-lifecycle-archive --no-lifecycle-fallback --no-audit >> kvmem\daily\service_mt5off.out 2>> kvmem\daily\service_mt5off.err
