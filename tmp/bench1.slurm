#!/bin/bash
#SBATCH -J bench1
#SBATCH -p gpu
#SBATCH -N 1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -t 00:30:00
#SBATCH -o /share/home/xy002/llm-ft/bench1-%j.out
source $HOME/envs/llm-ft/bin/activate
export HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
python -c "import torch;print('gpus',torch.cuda.device_count())"
time python $HOME/llm-ft/train_qlora.py --model $HOME/models/Qwen2.5-14B-Instruct --data $HOME/llm-ft/data.jsonl --out $HOME/llm-ft/bench1 --max_steps 10 --max_len 512 --epochs 1
echo BENCH1_DONE
