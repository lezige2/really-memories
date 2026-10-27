# -*- coding: utf-8 -*-
"""合并 LoRA 到 fp16 基座并导出 GGUF（在 128GB 内存的租机上跑）。

用法：
  python training/sft/merge_export.py --base Qwen/Qwen2.5-14B-Instruct \
      --adapter training/sft/out-r16 --merged training/sft/merged \
      --gguf training/sft/qwen-sft-f16.gguf --quant q4_k_m
依赖：transformers, peft, safetensors, llama.cpp（git clone 后 pip install -r requirements）
"""
import argparse
import os
import subprocess
import sys

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-14B-Instruct")
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--merged", default="training/sft/merged")
    ap.add_argument("--gguf", default="training/sft/qwen-sft-f16.gguf")
    ap.add_argument("--quant", default="q4_k_m")
    ap.add_argument("--llama-cpp", default="llama.cpp")
    a = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(a.base, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        a.base, torch_dtype=torch.float16, device_map={"": "cpu"},
        low_cpu_mem_usage=True, trust_remote_code=True)
    model = PeftModel.from_pretrained(model, a.adapter)
    model = model.merge_and_unload()
    model.save_pretrained(a.merged, safe_serialization=True)
    tok.save_pretrained(a.merged)
    print("merged ->", a.merged)

    conv = os.path.join(a.llama_cpp, "convert_hf_to_gguf.py")
    if not os.path.exists(conv):
        print("WARN: llama.cpp 不存在，跳过 GGUF 转换；merged 目录已就绪", file=sys.stderr)
        return 0
    subprocess.check_call([sys.executable, conv, a.merged, "--outfile", a.gguf,
                           "--outtype", "f16"])
    print("gguf f16 ->", a.gguf)
    q = os.path.join(a.llama_cpp, "build", "bin", "llama-quantize")
    if os.path.exists(q):
        out_q = a.gguf.replace("f16", a.quant.upper())
        subprocess.check_call([q, a.gguf, out_q, a.quant.upper()])
        print("gguf quant ->", out_q)
    return 0


if __name__ == "__main__":
    sys.exit(main())