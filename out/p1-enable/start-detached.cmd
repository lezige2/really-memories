@echo off
cd /d D:\llama-mem
python -X utf8 tools\chat_service.py --db kvmem\daily\chat.db --blocks kvmem\daily\blocks --sessions kvmem\daily\sessions --host 127.0.0.1 --port 8765 --retrieval topk --topk 4 --n-gpu-layers 28 --model "D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf" > out\p1-enable\obs-detached.out 2> out\p1-enable\obs-detached.err
