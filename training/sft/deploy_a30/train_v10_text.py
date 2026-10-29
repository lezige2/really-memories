# -*- coding: utf-8 -*-
"""V10 通道对齐训练：数据每行 {"text": 记忆原文前缀+时间+POLICY+chatml 问答}，直接对 text 做 LM 训练。"""
import argparse, json, torch
from torch.utils.data import Dataset
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                          Trainer, TrainingArguments)
from peft import LoraConfig, get_peft_model

class TextDS(Dataset):
    def __init__(self, path, tok, max_len):
        self.items = []
        for line in open(path, encoding="utf-8"):
            t = json.loads(line)["text"]
            ids = tok(t, add_special_tokens=False)["input_ids"][:max_len]
            self.items.append(ids)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return {"input_ids": self.items[i]}

class Collator:
    def __init__(self, pad):
        self.pad = pad

    def __call__(self, batch):
        m = max(len(b["input_ids"]) for b in batch)
        ids = [b["input_ids"] + [self.pad] * (m - len(b["input_ids"])) for b in batch]
        attn = [[1] * len(b["input_ids"]) + [0] * (m - len(b["input_ids"])) for b in batch]
        t = torch.tensor(ids)
        return {"input_ids": t, "attention_mask": torch.tensor(attn), "labels": t.clone()}

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--data", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--lr", type=float, default=2e-5)
ap.add_argument("--epochs", type=float, default=2.0)
ap.add_argument("--max-len", type=int, default=768)
ap.add_argument("--max-steps", type=int, default=-1)
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(a.model)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(
    a.model, quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16),
    torch_dtype=torch.float16, device_map="auto", attn_implementation="sdpa", low_cpu_mem_usage=True)
model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05,
                                        task_type="CAUSAL_LM",
                                        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                                        "gate_proj", "up_proj", "down_proj"]))
model.enable_input_require_grads()
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
args = TrainingArguments(
    output_dir=a.out, num_train_epochs=a.epochs, max_steps=a.max_steps,
    per_device_train_batch_size=1, gradient_accumulation_steps=16,
    learning_rate=a.lr, lr_scheduler_type="cosine", warmup_ratio=0.03, max_grad_norm=0.3,
    fp16=True, bf16=False, logging_steps=10, save_steps=60, save_total_limit=2,
    optim="paged_adamw_8bit", report_to="none", gradient_checkpointing=False,
)
tr = Trainer(model=model, args=args, train_dataset=TextDS(a.data, tok, a.max_len),
             data_collator=Collator(tok.pad_token_id))
tr.train()
tr.model.save_pretrained(a.out, safe_serialization=True)
print("V10_DONE", a.out, flush=True)
