#!/bin/bash
# A30 单卡：QLoRA → LoRA GGUF → merge → f16 → Q4_K_M → split
# 用法：V9=v9 bash export_v9.sh
set -uo pipefail
t0=$(date +%s); step(){ echo "==== $1 $(date '+%F %T') elapsed=$(( ($(date +%s)-t0)/60 ))min ===="; }

V=${V9:-v9}
H=$HOME/llm-ft
SRC=$H/llama.cpp
BIN=$H/llama.cpp/build/bin
ADAPTER=$H/output_${V}/final
MERGED=$H/merged_${V}
LORA=$H/qwen-sft-${V}-lora.gguf
F16=$H/qwen-sft-${V}-f16.gguf
Q4=$H/qwen-sft-${V}-Q4_K_M.gguf

step START; hostname; nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader || true
[ -f "$HOME/envs/llm-ft/bin/activate" ] && source "$HOME/envs/llm-ft/bin/activate" || { echo VENV_FAIL; exit 2; }
export HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=8  # 16G RAM 限制下别开太多线程，防 convert 阶段内存峰值
df -h "$HOME" | tail -1

step PRECHECK
[ -f "$ADAPTER/adapter_model.safetensors" ] || { echo NO_ADAPTER; exit 3; }
[ -e "$MERGED" ] && { echo MERGED_EXISTS; exit 4; }
[ -e "$F16" ] && { echo F16_EXISTS; exit 4; }
[ -e "$Q4" ] && { echo Q4_EXISTS; exit 4; }

step LORA_GGUF
python "$SRC/convert_lora_to_gguf.py" --base "$HOME/models/Qwen2.5-14B-Instruct" \
  --outfile "$LORA" --outtype f16 "$ADAPTER" || { echo LORA_FAIL; exit 5; }
ls -l "$LORA"; sha256sum "$LORA"

step MERGE_LORA
python "$H/merge_lora_shards.py" --base "$HOME/models/Qwen2.5-14B-Instruct" \
  --adapter "$ADAPTER" --merged "$MERGED" --verify 32 || { echo MERGE_FAIL; exit 6; }
du -sh "$MERGED"

step CONVERT_F16
python "$SRC/convert_hf_to_gguf.py" "$MERGED" --outfile "$F16" --outtype f16 || { echo CONVERT_FAIL; exit 7; }
ls -l "$F16"

step QUANTIZE
LD_LIBRARY_PATH="$BIN" "$BIN/llama-quantize" "$F16" "$Q4" Q4_K_M || { echo QUANT_FAIL; exit 8; }
ls -l "$Q4"; sha256sum "$Q4"

step SPLIT
rm -f "$Q4".part[0-9][0-9]
split -b 4600M -d "$Q4" "$Q4".part || { echo SPLIT_FAIL; exit 9; }
sha256sum "$Q4".part* > "$H/parts-${V}-SHA256SUMS"
cat "$H/parts-${V}-SHA256SUMS"

step DONE; ls -l "$Q4"*; echo TOTAL_MIN=$(( ($(date +%s)-t0)/60 ))