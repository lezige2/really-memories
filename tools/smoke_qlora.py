#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最小 QLoRA 冒烟：tiny 模型（0.5B）+ 4bit + LoRA 训练 3 步，验证整条链路。

用法：python tools/smoke_qlora.py [--model Qwen/Qwen2.5-0.5B-Instruct]
如需离线：--model /共享目录/models/Qwen2.5-0.5B-Instruct
"""
import argparse

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    a = ap.parse_args()
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16,
                             bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, quantization_config=bnb,
                                                 device_map="auto", torch_dtype=torch.float16)
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.05, task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]))
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)
    text = "用户：你好\n助手：你好，我是本地记忆助手。\n"
    batch = tok(text, return_tensors="pt").to("cuda")
    for step in range(3):
        out = model(**batch, labels=batch["input_ids"])
        out.loss.backward()
        opt.step()
        opt.zero_grad()
        print("step", step, "loss %.4f" % out.loss.item())
    print("SMOKE_OK peak_mem_GB %.2f" % (torch.cuda.max_memory_allocated() / 1024 ** 3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())