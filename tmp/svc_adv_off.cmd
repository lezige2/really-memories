@echo off
cd /d D:\llama-mem
"C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe" -X utf8 tools\chat_service.py --port 8766 --model D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf --db kvmem\adv\chat.db --blocks kvmem\adv\blocks --sessions kvmem\adv\sessions --session kvc.json --n-ctx 32768 --chat-start 8192 --n-gpu-layers 28 --retrieval topk --topk 4 >> kvmem\daily\service_adv_off.out 2>> kvmem\daily\service_adv_off.err
