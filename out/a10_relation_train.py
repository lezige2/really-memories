# -*- coding: utf-8 -*-
"""A10: 14B QLoRA 关系判定训练 + held-out 评测。"""
import argparse, json, os, re, torch
from dataclasses import dataclass
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                          Trainer, TrainingArguments)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

class WeightedTrainer(Trainer):
    def __init__(self, *args, sampler=None, **kwargs):
        self._sampler = sampler
        super().__init__(*args, **kwargs)
    def _get_train_sampler(self, *args, **kwargs):
        return self._sampler

SYS = ("你是记忆写入的关系判定器。只输出一个 JSON，不要解释。"
       '格式：{"relation":"correct|new_subject|ambiguous"}')
USER = """旧事实：{old}
新事实：{new}

判定：
- correct：同一主体、同一属性，新值取代旧值；
- new_subject：同族但不同主体，两条都保留；
- ambiguous：线索不足，不能确定。
只输出 JSON。"""

def fmt_prompt(tok, old, new):
    msgs = [{"role": "system", "content": SYS},
            {"role": "user", "content": USER.format(old=old, new=new)}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

def load_rows(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]

class DS(torch.utils.data.Dataset):
    def __init__(self, rows, tok, maxlen=384):
        self.items = []
        for r in rows:
            p = fmt_prompt(tok, r["old"], r["new"])
            a = json.dumps({"relation": r["label"]}, ensure_ascii=False) + tok.eos_token
            pi = tok(p, add_special_tokens=False).input_ids
            ai = tok(a, add_special_tokens=False).input_ids
            ids = (pi + ai)[:maxlen]
            lab = ([-100] * len(pi) + ai)[:maxlen]
            self.items.append({"input_ids": ids, "labels": lab})
    def __len__(self): return len(self.items)
    def __getitem__(self, i): return self.items[i]

@dataclass
class Coll:
    tok: any
    def __call__(self, feats):
        m = max(len(f["input_ids"]) for f in feats)
        ids, lab, att = [], [], []
        for f in feats:
            pad = m - len(f["input_ids"])
            ids.append(f["input_ids"] + [self.tok.pad_token_id] * pad)
            lab.append(f["labels"] + [-100] * pad)
            att.append([1] * len(f["input_ids"]) + [0] * pad)
        return {"input_ids": torch.tensor(ids), "labels": torch.tensor(lab),
                "attention_mask": torch.tensor(att)}

def parse(txt):
    m = re.search(r"\{.*?\}", txt, re.S)
    if not m: return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    r = str(d.get("relation", ""))
    return r if r in ("correct", "new_subject", "ambiguous") else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--heldout", required=True)
    ap.add_argument("--test", required=True)
    ap.add_argument("--rule-correct", type=int, default=36)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--dropout", type=float, default=0.05)
    ap.add_argument("--amb-weight", type=float, default=2.0)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    tok.pad_token = tok.eos_token
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
                             bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, quantization_config=bnb,
                                                 device_map="auto", trust_remote_code=True)
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(r=args.r, lora_alpha=2*args.r, lora_dropout=args.dropout, bias="none",
                      task_type="CAUSAL_LM",
                      target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    train_rows = load_rows(args.train)
    ds = DS(train_rows, tok)
    weights = []
    for rr in train_rows:
        if rr["label"] == "ambiguous": weights.append(args.amb_weight)
        elif rr["label"] == "correct": weights.append(1.2)
        else: weights.append(1.0)
    sampler = torch.utils.data.WeightedRandomSampler(weights, num_samples=len(ds), replacement=True)
    targs = TrainingArguments(output_dir=args.out, per_device_train_batch_size=1,
        gradient_accumulation_steps=8, num_train_epochs=args.epochs, learning_rate=args.lr,
        logging_steps=20, save_strategy="no", bf16=True, optim="paged_adamw_8bit",
        gradient_checkpointing=True, max_grad_norm=0.3, report_to=[], remove_unused_columns=False)
    tr = WeightedTrainer(model=model, args=targs, train_dataset=ds, data_collator=Coll(tok), sampler=sampler)
    tr.train()
    model.save_pretrained(os.path.join(args.out, "adapter"))
    tok.save_pretrained(os.path.join(args.out, "adapter"))

    # eval both test (fit) and heldout (generalization)
    def eval_set(path):
        rows = load_rows(path)
        res = []
        for r in rows:
            p = fmt_prompt(tok, r["old"], r["new"])
            inp = tok(p, return_tensors="pt").to(model.device)
            with torch.no_grad():
                out = model.generate(**inp, max_new_tokens=24, do_sample=False,
                                     pad_token_id=tok.eos_token_id)
            txt = tok.decode(out[0][inp["input_ids"].shape[1]:], skip_special_tokens=True)
            res.append({"id": r.get("id", "row-%03d" % len(res)), "label": r["label"], "pred": parse(txt)})
        valid = [x for x in res if x["pred"]]
        correct = sum(1 for x in valid if x["pred"] == x["label"])
        cat = [x["id"] for x in valid if {x["pred"], x["label"]} == {"correct", "new_subject"}]
        bad_hide = [x["id"] for x in valid if x["label"] == "ambiguous" and x["pred"] == "correct"]
        amb = [x for x in valid if x["label"] == "ambiguous"]
        s = {"n": len(res), "valid": len(valid), "parse_fail": len(res)-len(valid),
             "correct": correct, "acc": correct/max(1,len(valid)),
             "catastrophic": len(cat), "catastrophic_ids": cat,
             "bad_hide": len(bad_hide), "bad_hide_ids": bad_hide,
             "ambiguous_recall": sum(1 for x in amb if x["pred"]=="ambiguous")/max(1,len(amb)),
             "confusion": {l: {q: sum(1 for x in valid if x["label"]==l and x["pred"]==q)
                               for q in ("correct","new_subject","ambiguous")}
                           for l in ("correct","new_subject","ambiguous")},
             "per_class_precision": {q: (sum(1 for x in valid if x["pred"]==q and x["label"]==q) /
                                         max(1, sum(1 for x in valid if x["pred"]==q)))
                                     for q in ("correct","new_subject","ambiguous")}}
        return s, res

    s_test, r_test = eval_set(args.test)
    s_held, r_held = eval_set(args.heldout)
    net = s_held["correct"] - args.rule_correct
    verdict = "not_established" if net < 5 else "established"
    out = {"test": s_test, "heldout": s_held,
           "rule_v2_heldout_correct": args.rule_correct,
           "net_gain_heldout": net, "verdict_pre_registered": verdict,
           "artifacts": {"adapter": os.path.join(args.out, "adapter")}}
    json.dump({"summary": out, "heldout_results": r_held, "test_results": r_test},
              open(os.path.join(args.out, "eval.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
