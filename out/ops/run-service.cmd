@echo off
cd /d D:\llama-mem
start "" /min "C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe" -X utf8 tools\chat_service.py --db kvmem\daily\chat.db --blocks kvmem\daily\blocks --sessions kvmem\daily\sessions --host 127.0.0.1 --port 8765 --retrieval topk --topk 4 --n-gpu-layers 28 --model "D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf"
