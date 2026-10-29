# -*- coding: utf-8 -*-
"""V10 离线评测：raw 布局（记忆原文前缀+时间+POLICY+chatml[history]+user） vs base / adapter。"""
import argparse, json, torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--bundle", required=True)
ap.add_argument("--adapter", default=None)
ap.add_argument("--tag", default="V10")
ap.add_argument("--out", required=True)
ap.add_argument("--max-new", type=int, default=96)
a = ap.parse_args()
B = json.load(open(a.bundle, encoding="utf-8"))
POLICY = B["p0min"] if a.tag.endswith("p0min") else B.get("p0")
if not POLICY:
    import sys, os
    sys.path.insert(0, "/root/llm-ft")
    POLICY = open("/root/llm-ft/policy-P0.txt", encoding="utf-8").read().strip()
tok = AutoTokenizer.from_pretrained(a.model)
model = AutoModelForCausalLM.from_pretrained(
    a.model, quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16),
    torch_dtype=torch.float16, device_map="auto", attn_implementation="sdpa", low_cpu_mem_usage=True)
if a.adapter:
    model = PeftModel.from_pretrained(model, a.adapter)
model.eval()
from datetime import datetime
TL = "当前时间：%s 星期%s %s。" % (datetime(2026, 10, 29).strftime("%Y-%m-%d"), "四", "14:00")

def facts(case):
    return [p["text"] for p in case.get("pre_state", []) if p.get("action") == "remember"]

def build(case):
    mem = "\n".join(facts(case))
    s = (mem + "\n" if mem else "") + "<|im_start|>system\n" + TL + "\n" + POLICY + "<|im_end|>\n"
    for m in (case.get("history") or []):
        s += "<|im_start|>" + m["role"] + "\n" + m["content"] + "<|im_end|>\n"
    s += "<|im_start|>user\n" + case["input"] + "<|im_end|>\n<|im_start|>assistant\n"
    return s

def gen(s):
    ids = tok(s, return_tensors="pt").to(model.device)
    with torch.no_grad():
        o = model.generate(**ids, max_new_tokens=a.max_new, do_sample=False,
                           temperature=None, top_p=None, top_k=None, pad_token_id=tok.eos_token_id)
    return tok.decode(o[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()

def judge(case, ans):
    e = case.get("expect") or {}
    ok = True
    if e.get("contains_any") and not any(x in ans for x in e["contains_any"]): ok = False
    if e.get("contains_all") and not all(x in ans for x in e["contains_all"]): ok = False
    if e.get("not_contains") and any(x in ans for x in e["not_contains"]): ok = False
    for pair in (e.get("conflict_if_all") or []):
        if pair and all(x in ans for x in pair): ok = False
    return ok

rows = []
for c in B["extra"] + B["mt20"]:
    ans = gen(build(c))
    rows.append({"id": c["id"], "category": c.get("category"), "answer": ans, "pass": judge(c, ans)})
    print(a.tag, c["id"], "PASS" if rows[-1]["pass"] else "FAIL", ans[:50].replace("\n", " "), flush=True)
lm = [r for r in rows if r["category"] in ("long_memory", "multi_turn_memory")]
summary = {"all_pass": sum(1 for r in rows if r["pass"]), "all_n": len(rows),
           "memory_pass": sum(1 for r in lm if r["pass"]), "memory_n": len(lm)}
json.dump({"rows": rows, "summary": summary}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("SUMMARY", a.tag, summary, flush=True)
