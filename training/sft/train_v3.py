# -*- coding: utf-8 -*-
"""v3 增量训练：从 v2 LoRA adapter warm-start，在 autonomy 混合数据上再训 1 epoch。"""
import argparse
import glob
import os

import torch
from datasets import load_dataset
from peft import PeftModel, prepare_model_for_kbit_training
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig)
from trl import SFTConfig, SFTTrainer

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--data", required=True)
ap.add_argument("--adapter", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--epochs", type=float, default=1)
ap.add_argument("--lr", type=float, default=5e-5)
ap.add_argument("--max_len", type=int, default=512)
ap.add_argument("--max_steps", type=int, default=-1)
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(a.model)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(
    a.model,
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16),
    torch_dtype=torch.float16, device_map="auto",
    max_memory={0: "14GiB", 1: "14GiB"}, attn_implementation="sdpa",
    low_cpu_mem_usage=True)
model = prepare_model_for_kbit_training(model)
model = PeftModel.from_pretrained(model, a.adapter, is_trainable=True)
model.print_trainable_parameters()

ds = load_dataset("json", data_files=a.data, split="train")
cfg = SFTConfig(
    output_dir=a.out, num_train_epochs=a.epochs, max_steps=a.max_steps,
    per_device_train_batch_size=1, gradient_accumulation_steps=16,
    learning_rate=a.lr, lr_scheduler_type="cosine", warmup_ratio=0.03,
    max_grad_norm=0.3, fp16=True, bf16=False, gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    optim="paged_adamw_8bit", logging_steps=5,
    save_steps=50, save_total_limit=2, max_seq_length=a.max_len,
    report_to="none")
trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds, processing_class=tok)
trainer.model_accepts_loss_kwargs = False
trainer.train()
trainer.save_model(os.path.join(a.out, "final"))
print("V3_DONE saved ->", os.path.join(a.out, "final"))