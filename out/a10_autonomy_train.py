# -*- coding: utf-8 -*-
"""A10: 14B QLoRA 自主性 SFT（messages 对话体；<SILENCE> 负例）。"""
import argparse, json, os, re, torch
from dataclasses import dataclass
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                          Trainer, TrainingArguments)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

class WeightedTrainer(Trainer):
    def __init__(self, *a, sampler=None, **kw):
        self._sampler = sampler
        super().__init__(*a, **kw)
    def _get_train_sampler(self, *a, **kw):
        return self._sampler

def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]

class DS(torch.utils.data.Dataset):
    def __init__(self, rows, tok, maxlen=512):
        self.items = []
        for r in rows:
            msgs = r["messages"]
            prompt = tok.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True)
            ans = str(msgs[-1]["content"]) + tok.eos_token
            pi = tok(prompt, add_special_tokens=False).input_ids
            ai = tok(ans, add_special_tokens=False).input_ids
            ids = (pi + ai)[:maxlen]
            lab = ([-100] * len(pi) + ai)[:maxlen]
            self.items.append({"input_ids": ids, "labels": lab})
    def __len__(self): return len(self.items)
    def __getitem__(self, i): return self.items[i]

@dataclass
class Coll:
    tok: any
    def __call__(self, fs):
        m = max(len(f["input_ids"]) for f in fs)
        ids, lab, att = [], [], []
        for f in fs:
            pad = m - len(f["input_ids"])
            ids.append(f["input_ids"] + [self.tok.pad_token_id] * pad)
            lab.append(f["labels"] + [-100] * pad)
            att.append([1] * len(f["input_ids"]) + [0] * pad)
        return {"input_ids": torch.tensor(ids), "labels": torch.tensor(lab),
                "attention_mask": torch.tensor(att)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--dev", required=True)
    ap.add_argument("--test", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--r", type=int, default=8)
    ap.add_argument("--dropout", type=float, default=0.1)
    a = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    tok.pad_token = tok.eos_token
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
                             bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(a.model, quantization_config=bnb,
                                                 device_map="auto", trust_remote_code=True)
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(
        r=a.r, lora_alpha=2*a.r, lora_dropout=a.dropout, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]))
    tr_rows = load(a.train)
    ds = DS(tr_rows, tok)
    targs = TrainingArguments(output_dir=a.out, per_device_train_batch_size=1,
        gradient_accumulation_steps=8, num_train_epochs=a.epochs, learning_rate=a.lr,
        logging_steps=10, save_strategy="no", bf16=True, optim="paged_adamw_8bit",
        gradient_checkpointing=True, max_grad_norm=0.3, report_to=[], remove_unused_columns=False)
    Trainer(model=model, args=targs, train_dataset=ds, data_collator=Coll(tok)).train()
    model.save_pretrained(os.path.join(a.out, "adapter"))
    tok.save_pretrained(os.path.join(a.out, "adapter"))

    model.eval()
    def gen(rows):
        out = []
        for r in rows:
            msgs = r["messages"][:-1]
            p = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inp = tok(p, return_tensors="pt").to(model.device)
            with torch.no_grad():
                o = model.generate(**inp, max_new_tokens=64, do_sample=False,
                                   pad_token_id=tok.eos_token_id)
            txt = tok.decode(o[0][inp["input_ids"].shape[1]:], skip_special_tokens=True).strip()
            out.append({"pred": txt, "gold": str(r["messages"][-1]["content"]).strip(),
                        "should_trigger": r.get("should_trigger")})
        return out
    res = {"dev": gen(load(a.dev)), "test": gen(load(a.test))}
    for k, rows in res.items():
        sil = sum(1 for x in rows if "<SILENCE>" in x["pred"])
        print(k, "n", len(rows), "pred_silence", sil)
    json.dump(res, open(os.path.join(a.out, "eval.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("saved", a.out)

if __name__ == "__main__":
    main()