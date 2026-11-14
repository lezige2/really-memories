@echo off
cd /d D:\llama-mem
"C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe" -X utf8 tools\chat_service.py --port 8766 --model D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf --db kvmem\p3tts\chat.db --blocks kvmem\p3tts\blocks --sessions kvmem\p3tts\sessions --session kvc.json --n-ctx 32768 --chat-start 8192 --n-gpu-layers 28 --retrieval topk --topk 4 --assistant-memory >> kvmem\daily\service_p3a.out 2>> kvmem\daily\service_p3a.err
