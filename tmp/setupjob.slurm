#!/bin/bash
#SBATCH -J lmsetup
#SBATCH -p pro
#SBATCH -c 8
#SBATCH --mem=16G
#SBATCH -t 24:00:00
#SBATCH -o /share/home/xy002/llm/setupjob-%j.out

set -x
cd /share/home/xy002/llm
source /share/home/xy002/llm/venv/bin/activate

# 1) PyTorch（阿里云镜像）
pip install torch==2.4.1+cu121 -f https://mirrors.aliyun.com/pytorch-wheels/cu121/
# 2) 训练依赖
pip install transformers peft bitsandbytes accelerate datasets trl sentencepiece 'huggingface_hub[cli]'

# 3) 自检
python -c "import torch;print('TORCH_OK',torch.__version__,torch.cuda.is_available())"

# 4) 下载 14B 模型（28GB，并发 8）
export HF_ENDPOINT=https://hf-mirror.com
mkdir -p /share/home/xy002/llm/models
hf download Qwen/Qwen2.5-14B-Instruct \
  --local-dir /share/home/xy002/llm/models/Qwen2.5-14B-Instruct \
  --max-workers 8

echo SETUPJOB_DONE