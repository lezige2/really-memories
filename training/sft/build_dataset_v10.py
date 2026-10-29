# -*- coding: utf-8 -*-
"""V10 通道对齐数据：训练文本 = 记忆原文(无标签) + 时间行 + POLICY + chatml user/assistant。
布局对照说明：运行时记忆块挂在 [chat_start-n, chat_start)（对话起点之前），随后才是
<|im_start|>system(时间行+POLICY)... 所以本文本布局与推理 token 序列一致（G0 已核对）。
输出：training/sft/train_v10.jsonl（每行 {"text": ...}）+ out/SFT-DATA-v10-AUDIT.json
"""
import hashlib
import json
import os
import random
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "training", "sft"))
import build_dataset as bd  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "tools"))
import chat_daily  # noqa: E402

rng = random.Random(20261029)
NOW = datetime(2026, 10, 29, 14, 0)
POLICY = chat_daily.SYSTEM_POLICY

# 训练专用事实（必须与评测 fixture 互斥；脚本末尾断言）
FACTS = [
    ("我养了只猫叫年糕", "我养的猫叫什么名字？", "你养的猫叫年糕。"),
    ("我在小米上班", "我在哪家公司上班？", "你在小米上班。"),
    ("我的车牌号是苏A67890", "我的车牌号是多少？", "你的车牌号是苏A67890。"),
    ("我的工位在D区5号", "我的工位在哪？", "你的工位在D区5号。"),
    ("我的手机号是135-2222-7777", "我的手机号是多少？", "你的手机号是135-2222-7777。"),
    ("我每周日上午九点去健身", "我什么时候去健身？", "你周日上午九点去健身。"),
    ("我最爱吃烤鱼", "我最爱吃什么？", "你最爱吃烤鱼。"),
    ("我老家在无锡", "我老家在哪？", "你老家在无锡。"),
    ("我女儿小名叫葡萄", "我女儿小名是什么？", "你女儿小名叫葡萄。"),
    ("我的银行卡尾号是3046", "我的银行卡尾号是多少？", "你的银行卡尾号是3046。"),
    ("我对青霉素过敏", "我对什么过敏？", "你对青霉素过敏。"),
    ("我下周三要去厦门开会", "我下周三去哪开会？", "你下周三要去厦门开会。"),
]
OLD_NEW = [("我养了只猫叫年糕", "我养了只猫叫糯米", "我养的猫叫什么名字？", "你养的猫叫糯米。"),
           ("我的工位在D区5号", "我的工位在E区2号", "我的工位在哪？", "你的工位在E区2号。"),
           ("我老家在无锡", "我老家在常州", "我老家在哪？", "你老家在常州。"),
           ("我手机号是135-2222-7777", "我手机号是138-6666-8888", "我的手机号是多少？", "你的手机号是138-6666-8888。")]
ATTR = [("我的车是银色两厢车｜颜色=银色；车型=两厢", "我的车是什么颜色？", "你的车是银色的。"),
        ("我的邮箱是 wang@example.org｜邮箱=wang@example.org", "我的邮箱是什么？", "你的邮箱是 wang@example.org。")]
UNKNOWN = [("我姐姐叫什么名字？", "这个我没法确认：你没跟我说过。"),
           ("我妈妈的生日是哪天？", "这个我没法确认：你没跟我说过。"),
           ("我的护照号是多少？", "这个我没法确认：你没跟我说过。"),
           ("我小学在哪读的？", "这个我没法确认：你没跟我说过。")]
CHAT = [("你好", "你好呀，有什么想聊的？"), ("谢谢", "不客气。"), ("在吗", "在的，你说。"),
        ("你能做什么", "我能帮你记事实、按记忆回答问题；不能联网、不能操作应用。"),
        ("今天过得怎么样", "还行，陪你说说话。"), ("嗯嗯", "嗯，我在。"),
        ("讲个短句", "慢慢来，比较快。"), ("继续", "好，你说。")]


def make_text(mem_lines, q, a):
    mem = "\n".join(mem_lines)
    tl = "当前时间：%s 星期%s %s。" % (NOW.strftime("%Y-%m-%d"), "一二三四五六日"[NOW.weekday()],
                                    NOW.strftime("%H:%M"))
    head = mem + "\n" if mem else ""
    return (head + "<|im_start|>system\n" + tl + "\n" + POLICY + "<|im_end|>\n"
            + "<|im_start|>user\n" + q + "<|im_end|>\n"
            + "<|im_start|>assistant\n" + a + "<|im_end|>\n")


rows = []
# A 多块记忆（2-6 块，问其中一条）
for _ in range(260):
    k = rng.randint(1, 5)
    picked = rng.sample(FACTS, k + 1)
    target = picked[-1]
    blocks = [rng.choice(FACTS)[0] for _ in range(rng.randint(1, 5))] + [target[0]]
    rows.append(make_text(blocks, target[1], target[2]))
# B 冲突（旧→新，答新）
for _ in range(120):
    old, new, q, a = rng.choice(OLD_NEW)
    rows.append(make_text([old, new], q, a))
# C 0 块 + 未知
for _ in range(120):
    q, a = rng.choice(UNKNOWN)
    rows.append(make_text([], q, a))
# D 无关块 + 未知
for _ in range(120):
    q, a = rng.choice(UNKNOWN)
    blocks = [rng.choice(FACTS)[0] for _ in range(rng.randint(1, 3))]
    rows.append(make_text(blocks, q, a))
# E 属性归纳
for _ in range(60):
    m, q, a = rng.choice(ATTR)
    rows.append(make_text([m], q, a))
# F 闲聊/replay（带 0-2 块，答案自然）
for _ in range(100):
    q, a = rng.choice(CHAT)
    blocks = [rng.choice(FACTS)[0] for _ in range(rng.randint(0, 2))]
    rows.append(make_text(blocks, q, a))

rng.shuffle(rows)
out = os.path.join(ROOT, "training", "sft", "train_v10.jsonl")
with open(out, "w", encoding="utf-8", newline="\n") as f:
    for r in rows:
        f.write(json.dumps({"text": r}, ensure_ascii=False) + "\n")

# 断言：训练文本不与评测 fixture 值冲突
ev = json.load(open(os.path.join(ROOT, "out", "V9-EVAL-VALUES.json"), encoding="utf-8"))
bad = []
vals = set()
for key in ("eval_values_independent", "fixture_values", "fixture_entities", "independent_entities"):
    v = ev.get(key)
    if isinstance(v, list):
        for x in v:
            if isinstance(x, str) and len(x) >= 4:
                vals.add(x)
blob = "\n".join(rows)
for v in vals:
    if v in blob:
        bad.append(v)
audit = {"schema": "sft_data_v10_audit", "rows": len(rows), "sha256": hashlib.sha256(blob.encode()).hexdigest(),
         "layout": "memory_raw_prefix + time + policy + chatml(user,assistant)",
         "categories": {"A_memory_multi": 260, "B_conflict": 120, "C_zero_block": 120,
                        "D_irrelevant_block": 120, "E_attribute": 60, "F_chat_replay": 100},
         "eval_value_conflicts": bad}
json.dump(audit, open(os.path.join(ROOT, "out", "SFT-DATA-v10-AUDIT.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(audit, ensure_ascii=False))
if bad:
    print("FIXTURE_CONFLICT", bad[:10], file=sys.stderr)
    sys.exit(3)
