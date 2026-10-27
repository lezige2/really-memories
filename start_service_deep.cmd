@echo off
cd /d D:\llama-mem
rem deep mode: R1-Distill reasoning model on port 8767 (QQ bridge can point here)
python -X utf8 tools\chat_service.py --port 8767 --model D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf --db kvmem\daily\chat.db --blocks kvmem\daily\blocks --sessions kvmem\daily\sessions --session daily.json --n-ctx 16384 --chat-start 8192 --n-gpu-layers 34 --retrieval topk --topk 4
