#!/bin/bash
# 单卡训练（A10/3090 24G：20GiB；A100 40G：36GiB；V100-32G：28GiB）；约 40–60 分钟
set -eo pipefail
source "$HOME/envs/llm-ft/bin/activate"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=14
export HF_HUB_OFFLINE=1

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
python - <<'PY'
import torch
assert torch.cuda.is_available(), "CUDA 不可用"
print("torch", torch.__version__, "cuda", torch.version.cuda,
      "gpu", torch.cuda.get_device_name(0), "cap", torch.cuda.get_device_capability(0))
PY

mkdir -p "$HOME/llm-ft/output_v9"
python "$HOME/llm-ft/train_qlora.py" \
  --model "$HOME/models/Qwen2.5-14B-Instruct" \
  --data "$HOME/llm-ft/train_v9.jsonl" \
  --out "$HOME/llm-ft/output_v9" \
  --epochs 1 --max_len 768 --lr 1e-4 --max_memory 20GiB 2>&1 | tee "$HOME/llm-ft/train_v9.log"

echo "若 OOM：A10/3090 24G 把 --max_memory 降到 18GiB 或 --max_len 降为 640 重跑（脚本会自动从 checkpoint 续）；--seq 768 为 B 复核后的选择（完整 prompt p95 414/max 530，512 会截断 26 行）"
echo "TRAIN_DONE $(date '+%F %T')"; ls -lh "$HOME/llm-ft/output_v9/final"