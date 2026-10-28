#!/bin/bash
#SBATCH -J nodeprobe2
#SBATCH -p pro
#SBATCH -c 2
#SBATCH --mem=4G
#SBATCH -t 00:10:00
#SBATCH -o /share/home/xy002/llm/nodeprobe2-%j.out
echo "HOST=$(hostname)"
echo "=== root / ==="; ls -la / 2>/dev/null | head -30
echo "=== mounts ==="; df -h 2>/dev/null | head -20
echo "=== recent scripts (whole fs) ==="; find / -xdev -maxdepth 6 \( -name '*.slurm' -o -name '*.sh' \) -newermt '2026-10-27' 2>/dev/null | grep -vE '^/(proc|sys|usr|etc|snap|var)/' | head -30
echo "=== qwen/model files ==="; find / -xdev -maxdepth 6 \( -iname '*qwen*' -o -iname '*.safetensors' -o -iname '*llm*' \) 2>/dev/null | grep -vE '^/(proc|sys|usr|etc|snap|var)/' | head -20
