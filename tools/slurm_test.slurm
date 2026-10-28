#!/bin/bash
#SBATCH --job-name=qm-test
#SBATCH --partition=CHANGE_ME            # 改成你们的 V100 分区
#SBATCH --gres=gpu:v100:2                # 或按你们写法: --gpus=2
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:10:00
#SBATCH --output=qm-test-%j.log

set -e
echo "== node =="; hostname; nvidia-smi
source ~/venv/bin/activate 2>/dev/null || true
python -u tools/env_probe.py
python -u tools/smoke_qlora.py
echo "SLURM_TEST_OK"