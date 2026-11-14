# -*- coding: utf-8 -*-
"""Fallback 自主性 600：v3_autonomy 300 + 合成负例/变体 300（仅在 C7 阻塞时启用）。"""
import json, random, hashlib, os

random.seed(60001)
SRC = "training/sft/v3_autonomy.jsonl"
OUT = "out/autonomy600"

def main():
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8")]
    pos = rows[:300]
    neg = []
    times = ["2026-10-29 23:30", "2026-10-30 02:10", "2026-10-30 06:40"]
    users = [
        ("（用户沉默，无新消息）", "<SILENCE>"),
        ("今天有点累，先不聊了。", "好，早点休息。"),
        ("在吗？", "在的，你说。"),
        ("（用户正在开会，未回复）", "<SILENCE>"),
        ("刚看到一条新闻，晚点再说。", "好，等你。"),
    ]
    mems = ["我的银行卡尾号是7418。", "每周三晚上七点有组会。", "我对花生过敏。"]
    for i in range(300):
        u, a = random.choice(users)
        t = random.choice(times)
        m = random.choice(mems)
        sys = f"当前时间：{t}。\n\n记忆：{m}\n\n你是本地记忆助手；不确定是否该主动时，输出 <SILENCE>。"
        neg.append({"messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": u},
            {"role": "assistant", "content": a},
        ]})
    allrows = pos + neg
    random.shuffle(allrows)
    os.makedirs(OUT, exist_ok=True)
    ntr, ndev = 480, 60
    for name, part in (("train.jsonl", allrows[:ntr]),
                       ("dev.jsonl", allrows[ntr:ntr+ndev]),
                       ("test.jsonl", allrows[ntr+ndev:])):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            for r in part:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    data = open(os.path.join(OUT, "train.jsonl"), "rb").read()
    manifest = {"source": SRC, "rows": len(allrows), "negatives": len(neg),
                "negative_ratio": len(neg)/len(allrows),
                "sha256_train": hashlib.sha256(data).hexdigest(),
                "note": "fallback only; gate risk high; v3 300 + synthetic 300"}
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(manifest)

if __name__ == "__main__":
    main()