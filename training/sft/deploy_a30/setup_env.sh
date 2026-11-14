# ===== RTX 3090 24G 单卡环境安装（约 15-25 分钟）=====
# 用法：bash setup_env.sh   （在能上网的 A30 机器上）
set -euo pipefail
H=$HOME

# 1) venv + pip 包（版本与出七臂的环境一致）
python3 -m venv "$H/envs/llm-ft"
source "$H/envs/llm-ft/bin/activate"
pip install -U pip wheel -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install torch==2.4.1 --index-url https://download.pytorch.org/whl/cu121
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
  transformers==4.46.3 trl==0.12.2 peft==0.13.2 accelerate==1.0.1 \
  bitsandbytes==0.44.1 datasets==3.1.0 safetensors==0.8.0 sentencepiece==0.2.0 \
  tokenizers==0.20.3 numpy==2.2.6 protobuf scipy \
  cmake ninja gguf hf_transfer

# 2) llama.cpp（只编译 CPU 工具：convert / quantize）
cd "$H/llm-ft"
if [ ! -d llama.cpp ]; then
  git clone --depth 1 https://github.com/ggml-org/llama.cpp
fi
cmake -S llama.cpp -B llama.cpp/build -DGGML_CUDA=OFF -DLLAMA_BUILD_TESTS=OFF \
      -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build -j 14 --target llama-quantize

# 3) 基座模型（28G；国内走 hf-mirror）
export HF_ENDPOINT=https://hf-mirror.com
if [ ! -f "$H/models/Qwen2.5-14B-Instruct/config.json" ]; then
  HF_HUB_ENABLE_HF_TRANSFER=1 huggingface-cli download Qwen/Qwen2.5-14B-Instruct \
    --local-dir "$H/models/Qwen2.5-14B-Instruct"
fi

# 4) 自检
python - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.version.cuda,
      "gpus", torch.cuda.device_count(),
      "cap", torch.cuda.get_device_capability(0) if torch.cuda.is_available() else None)
PY
echo "SETUP_DONE; 若 capability=(8,6) 说明认到 3090(Ampere)"