#!/bin/bash
#SBATCH -J nodeprobe
#SBATCH -p pro
#SBATCH -c 2
#SBATCH --mem=4G
#SBATCH -t 00:10:00
#SBATCH -o /share/home/xy002/llm/nodeprobe-%j.out
echo "HOST=$(hostname)"
echo "--- /opt:"; ls /opt 2>/dev/null
echo "--- /data /mnt /srv:"; ls /data /mnt /srv 2>/dev/null
echo "--- /root (perm):"; ls /root 2>/dev/null | head
echo "--- local slurm/sh scripts:"; find /opt /data /mnt /srv /usr/local /root -maxdepth 4 \( -name '*.slurm' -o -name '*.sh' \) 2>/dev/null | head -20
echo "--- qwen/torch:"; find /opt /data /mnt /srv /usr/local -maxdepth 5 \( -iname '*qwen*' -o -iname '*torch*' \) 2>/dev/null | head -15
ls -la /share/home/xy002/llm 2>/dev/null | head
