# -*- coding: utf-8 -*-
"""Cycle1 replay pilot：用 base 模型自身的答案做 320 行 replay 数据。
用法（A10 上）：
  python make_replay.py --model ~/models/Qwen2.5-14B-Instruct \
    --data ~/llm-ft/train_v9.jsonl --policy ~/llm-ft/policy-P0.txt \
    --out ~/llm-ft/train_replay320.jsonl --n 320
要点：greedy(do_sample=False)、只用训练集提示词（不含评测题）、四护栏过滤。
"""
import argparse
import hashlib
import json
import random
import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

ap = argparse.ArgumentParser()
ap.add_argument('--model', required=True)
ap.add_argument('--data', required=True)
ap.add_argument('--policy', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--n', type=int, default=320)
ap.add_argument('--max-new-tokens', type=int, default=120)
a = ap.parse_args()

policy = open(a.policy, encoding='utf-8').read().strip()
tok = AutoTokenizer.from_pretrained(a.model)
model = AutoModelForCausalLM.from_pretrained(
    a.model,
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                                           bnb_4bit_use_double_quant=True,
                                           bnb_4bit_compute_dtype=torch.float16),
    torch_dtype=torch.float16, device_map='auto', attn_implementation='sdpa', low_cpu_mem_usage=True)

rows, seen = [], set()
with open(a.data, encoding='utf-8') as f:
    for line in f:
        r = json.loads(line)
        msgs = r['messages']
        if len(msgs) != 3:                      # 只用单轮 prompt
            continue
        sys_txt = msgs[0]['content']
        # 把 system 里的 policy 段替换成当前 policy（数据是 ast 绑定旧 policy 的）
        idx = sys_txt.rfind('\n\n')
        sys_new = (sys_txt[:idx] if idx > 0 else '') + '\n\n' + policy if idx > 0 else sys_txt
        key = (sys_new, msgs[1]['content'])
        if key in seen:
            continue
        seen.add(key)
        rows.append({'system': sys_new, 'user': msgs[1]['content']})
random.Random(20261029).shuffle(rows)
rows = rows[:a.n]

BAD_VALUE = re.compile(r'\d|℃|度|晴|多云|阴|雨|雪|级|元|块')
out = []
for i, r in enumerate(rows, 1):
    msgs = [{'role': 'system', 'content': r['system']}, {'role': 'user', 'content': r['user']}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ids = tok(text, return_tensors='pt').to(model.device)
    with torch.no_grad():
        gen = model.generate(**ids, max_new_tokens=a.max_new_tokens, do_sample=False,
                             temperature=None, top_p=None, top_k=None,
                             pad_token_id=tok.eos_token_id)
    ans = tok.decode(gen[0][ids['input_ids'].shape[1]:], skip_special_tokens=True).strip()
    # 四护栏
    if not (8 <= len(ans) <= 60):
        continue
    if any(w in ans for w in ('我记下了', '已记住', '记住了', '收到，我记')):
        continue
    if BAD_VALUE.search(ans) and re.search('天气|气温|限行|股价|新闻|汇率|油价|金价|路况|台风|空气', r['user']):
        continue
    out.append({'messages': [{'role': 'system', 'content': r['system']},
                             {'role': 'user', 'content': r['user']},
                             {'role': 'assistant', 'content': ans}]})
    if i % 20 == 0:
        print('done', i, 'kept', len(out), flush=True)
    if len(out) >= a.n:
        break

with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print('wrote', len(out), 'sha256', hashlib.sha256(open(a.out, 'rb').read()).hexdigest())
