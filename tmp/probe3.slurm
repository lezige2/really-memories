#!/bin/bash
#SBATCH -J probe3
#SBATCH -p pro
#SBATCH -c 2
#SBATCH --mem=4G
#SBATCH -t 00:10:00
#SBATCH -o /share/home/xy002/llm/probe3-%j.out
echo HOST=$(hostname)
echo "=== /home ==="; ls -la /home 2>/dev/null; ls -la /home/* 2>/dev/null | head -20
echo "=== /opt recursive ==="; find /opt -maxdepth 3 2>/dev/null | head -40
echo "=== /sharedata3 ==="; ls -la /sharedata3 2>/dev/null | head; find /sharedata3 -maxdepth 3 2>/dev/null | head -20
echo "=== /sharedata1 read ==="; ls /sharedata1 2>&1 | head -5
echo "=== /sharedata2 read ==="; ls /sharedata2 2>&1 | head -5
echo "=== /tmp scripts ==="; find /tmp -maxdepth 2 \( -name '*.slurm' -o -name '*.sh' -o -iname '*qwen*' \) 2>/dev/null | head -10
