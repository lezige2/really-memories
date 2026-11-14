"""Qwen2.5-14B QLoRA 微调脚本（A30 24G / 单卡；transformers 4.46 / peft 0.13 / trl 0.12）
数据：jsonl，每行 {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}；
      支持多轮（system + 若干 user/assistant 对，最后一条是 assistant）。
要点：4bit NF4、fp16 计算、device_map 单卡、梯度检查点、paged_adamw_8bit；
      单卡 24G（A10/3090）建议 --max_memory 20GiB；OOM 时先降 18GiB，再不行 --max_len 640（A100 40G 可用 36GiB）。
"""
import argparse
import glob
import os

import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

ap = argparse.ArgumentParser()
ap.add_argument('--model', required=True)
ap.add_argument('--data', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--epochs', type=float, default=1)
ap.add_argument('--lr', type=float, default=1e-4)
ap.add_argument('--max_len', type=int, default=512)
ap.add_argument('--max_steps', type=int, default=-1)
ap.add_argument('--max_memory', default=None,
                help='单卡上限，如 21GiB；留空则 device_map=auto 自动')
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(a.model)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

mm = {0: a.max_memory} if a.max_memory else None
model = AutoModelForCausalLM.from_pretrained(
    a.model,
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                                           bnb_4bit_use_double_quant=True,
                                           bnb_4bit_compute_dtype=torch.float16),
    torch_dtype=torch.float16,
    device_map='auto',
    max_memory=mm,
    attn_implementation='sdpa',
    low_cpu_mem_usage=True,
)

ds = load_dataset('json', data_files=a.data, split='train')

cfg = SFTConfig(
    output_dir=a.out,
    num_train_epochs=a.epochs,
    max_steps=a.max_steps,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,
    learning_rate=a.lr,
    lr_scheduler_type='cosine',
    warmup_ratio=0.03,
    max_grad_norm=0.3,
    fp16=True, bf16=False,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={'use_reentrant': False},
    optim='paged_adamw_8bit',
    logging_steps=10,
    save_steps=100, save_total_limit=2,   # B 策略：262 步要有中间点，断连可续
    max_seq_length=a.max_len,
    report_to='none',
)
lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type='CAUSAL_LM',
                  target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj',
                                  'gate_proj', 'up_proj', 'down_proj'])

trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds, processing_class=tok, peft_config=lora)
# transformers 4.46 在 device_map 切分时 num_items_in_batch 会跨设备报错；关掉，loss 按每步平均。
trainer.model_accepts_loss_kwargs = False
resume = bool(glob.glob(os.path.join(a.out, 'checkpoint-*')))
trainer.train(resume_from_checkpoint=resume or None)
trainer.save_model(os.path.join(a.out, 'final'))
print('完成，LoRA 权重在', os.path.join(a.out, 'final'))