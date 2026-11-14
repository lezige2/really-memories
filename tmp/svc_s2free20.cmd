@echo off
cd /d D:\llama-mem
set VERIFIER_VERSION=v2.2
set S2_GATE_OFF=1
"C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe" -X utf8 tools\chat_service.py --port 8766 --model D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf --db kvmem\s1_200\chat.db --blocks kvmem\s1_200\blocks --sessions kvmem\daily\sessions --session kvc.json --n-ctx 32768 --chat-start 8192 --n-gpu-layers 28 --retrieval topk --topk 20 --k2-family >> kvmem/daily/service_s2free20.out 2>> kvmem/daily/service_s2free20.err