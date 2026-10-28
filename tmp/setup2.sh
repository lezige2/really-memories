#!/bin/bash
set -x
source ~/llm/venv/bin/activate
pip install torch==2.4.1+cu121 -f https://mirrors.aliyun.com/pytorch-wheels/cu121/
pip install transformers peft bitsandbytes accelerate datasets trl sentencepiece 'huggingface_hub[cli]'
python -c 'import torch;print("TORCH_OK", torch.__version__, torch.cuda.is_available())'
echo SETUP2_DONE