# -*- coding: utf-8 -*-
"""在 3090/实际训练机上用 Qwen tokenizer 复核 chat template 后的 token 长度。
用法：python tokenize_check.py --model ~/models/Qwen2.5-14B-Instruct --data train_v9.jsonl --seq 768
输出：p50/p95/max、>seq 行数、最长 5 行示例（id/长度）。
若 max > seq：建议 --seq 提到 1024 或回本地裁行（超长行会被截断，砍掉最后的问答监督）。
"""
import argparse
import json

from transformers import AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument('--model', required=True)
ap.add_argument('--data', default='train_v9.jsonl')
ap.add_argument('--seq', type=int, default=768)
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(a.model)
lens = []
rows = []
with open(a.data, encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        msgs = json.loads(line)['messages']
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        n = len(tok(text, add_special_tokens=False)['input_ids'])
        lens.append(n)
        rows.append((n, i))

lens.sort()
def q(p):
    return lens[min(len(lens) - 1, int(len(lens) * p))]

over = [r for r in rows if r[0] > a.seq]
print('rows', len(lens), 'seq', a.seq)
print('p50', q(0.50), 'p90', q(0.90), 'p95', q(0.95), 'p99', q(0.99), 'max', lens[-1])
print('over_seq', len(over), 'ratio', round(len(over) / max(1, len(lens)), 4))
for n, i in sorted(rows, reverse=True)[:5]:
    print('long', i, n)
print('RESULT', 'PASS' if len(over) == 0 else 'NEED_LARGER_SEQ_OR_TRIM')