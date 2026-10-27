# -*- coding: utf-8 -*-
"""Qwen2.5-14B-Instruct QLoRA 行为微调（单卡 12GB 可跑）。

用法（租机 Linux，Python 3.11）：
  pip install -U torch transformers peft bitsandbytes accelerate datasets trl
  python training/sft/train_qlora.py --base Qwen/Qwen2.5-14B-Instruct \
      --data training/sft/train.jsonl --out training/sft/out-r16

关键参数针对 3060 12G / seq512 调过：bs1、grad_accum16、gradient_checkpointing、paged_adamw_8bit、fp16。
"""
import argparse
import os

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                          DataCollatorForLanguageModeling, Trainer, TrainingArguments)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-14B-Instruct")
    ap.add_argument("--data", default="training/sft/train.jsonl")
    ap.add_argument("--out", default="training/sft/out-r16")
    ap.add_argument("--seq", type=int, default=512)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-steps", type=int, default=-1)
    a = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(a.base, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"

    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16,
                             bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(
        a.base, quantization_config=bnb, device_map="auto",
        torch_dtype=torch.float16, trust_remote_code=True)
    model = prepare_model_for_kbit_training(model)
    cfg = LoraConfig(r=a.r, lora_alpha=a.alpha, lora_dropout=0.05,
                     bias="none", task_type="CAUSAL_LM",
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                     "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, cfg)

    ds = load_dataset("json", data_files=a.data, split="train")

    def encode(ex):
        text = tok.apply_chat_template(ex["messages"], tokenize=False,
                                       add_generation_prompt=False)
        ids = tok(text, truncation=True, max_length=a.seq, add_special_tokens=False)
        return {"input_ids": ids["input_ids"], "attention_mask": ids["attention_mask"]}

    ds = ds.map(encode, remove_columns=ds.column_names, num_proc=a.workers)
    collator = DataCollatorForLanguageModeling(tok, mlm=False)

    args = TrainingArguments(
        output_dir=a.out, num_train_epochs=a.epochs,
        per_device_train_batch_size=1, gradient_accumulation_steps=16,
        gradient_checkpointing=True, fp16=True,
        learning_rate=a.lr, lr_scheduler_type="cosine", warmup_ratio=0.03,
        logging_steps=10, save_steps=200, save_total_limit=2,
        optim="paged_adamw_8bit", max_steps=a.max_steps,
        dataloader_num_workers=a.workers, report_to="none",
        remove_unused_columns=False)
    trainer = Trainer(model=model, args=args, train_dataset=ds, data_collator=collator)
    trainer.train()
    model.save_pretrained(a.out)
    tok.save_pretrained(a.out)
    print("saved adapter ->", a.out)


if __name__ == "__main__":
    main()