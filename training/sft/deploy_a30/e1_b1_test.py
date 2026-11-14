# -*- coding: utf-8 -*-
"""E1：B1 可行性实验（记忆作为真实聊turn文本 vs system 文本），HF 直接生成、greedy。
用法（A10）：python e1_b1_test.py --model /root/models/Qwen2.5-14B-Instruct --bundle /root/llm-ft/e1-bundle.json --out /root/llm-ft/E1-RESULTS.json
"""
import argparse, json, re, torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--bundle", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--max-new", type=int, default=96)
a = ap.parse_args()
B = json.load(open(a.bundle, encoding="utf-8"))
tok = AutoTokenizer.from_pretrained(a.model)
model = AutoModelForCausalLM.from_pretrained(
    a.model, quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16),
    torch_dtype=torch.float16, device_map="auto", attn_implementation="sdpa", low_cpu_mem_usage=True)

def gen(msgs):
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ids = tok(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=a.max_new, do_sample=False,
                             temperature=None, top_p=None, top_k=None, pad_token_id=tok.eos_token_id)
    return tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()

def facts_of(case):
    return [p["text"] for p in case.get("pre_state", []) if p.get("action") == "remember"]

def hist_msgs(case):
    return [{"role": m["role"], "content": m["content"]} for m in (case.get("history") or [])]

def judge(case, ans):
    exp = case.get("expect") or {}
    ca = exp.get("contains_any") or []; call = exp.get("contains_all") or []
    nc = exp.get("not_contains") or []
    cf = exp.get("conflict_if_all") or []
    ok = True
    if ca and not any(x in ans for x in ca): ok = False
    if call and not all(x in ans for x in call): ok = False
    if nc and any(x in ans for x in nc): ok = False
    for pair in cf:
        if pair and all(x in ans for x in pair): ok = False
    return ok

def run_variant(name, policy, mode):
    rows = []
    cases = B["extra"] + B["mt20"]
    for c in cases:
        fs = facts_of(c); h = hist_msgs(c)
        if mode == "turns":
            msgs = [{"role": "system", "content": policy}]
            for f in fs:
                msgs += [{"role": "user", "content": f}, {"role": "assistant", "content": "好的，记住了"}]
            msgs += h + [{"role": "user", "content": c["input"]}]
        elif mode == "system_text":
            sysc = policy + "\n以下是用户之前说过、需要记住的事实：" + "；".join(fs)
            msgs = [{"role": "system", "content": sysc}] + h + [{"role": "user", "content": c["input"]}]
        else:  # none
            msgs = [{"role": "system", "content": policy}] + h + [{"role": "user", "content": c["input"]}]
        ans = gen(msgs)
        rows.append({"id": c["id"], "category": c.get("category"), "mode": name, "answer": ans, "pass": judge(c, ans)})
        print(name, c["id"], "PASS" if rows[-1]["pass"] else "FAIL", ans[:50].replace("\n", " "), flush=True)
    return rows

res = {}
for name, pol, mode in [("E1a_turns_P0min", B["p0min"], "turns"),
                        ("E1b_systemtext_P0min", B["p0min"], "system_text"),
                        ("E1c_turns_P1min", B["p1min"], "turns")]:
    rows = run_variant(name, pol, mode)
    res[name] = rows
    lm = [r for r in rows if r["category"] in ("long_memory", "multi_turn_memory")]
    print("SUMMARY", name, "all", sum(1 for r in rows if r["pass"]), "/", len(rows),
          "memory", sum(1 for r in lm if r["pass"]), "/", len(lm), flush=True)
json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("DONE", a.out)
