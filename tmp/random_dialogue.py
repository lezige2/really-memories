# -*- coding: utf-8 -*-
"""以普通用户身份随机对话，检查服务端行为（只读、只调 /ask）。"""
import json
import sys
import time
import urllib.request

URL = "http://127.0.0.1:8765/ask"

QS = [
    "在吗",
    "早上好呀",
    "你还记得我是谁吗",
    "我叫什么名字？",
    "我的车牌号是多少？",
    "我周三有什么安排？",
    "我下周三去哪开会？",
    "我下周三要去广州出差",
    "我下周去哪出差？",
    "我明天要去哪里出差？",
    "今天北京天气怎么样",
    "你记得我有几条记忆？",
    "你能做什么",
    "你刚才说了什么",
    "我上一个问题是什么",
    "随便聊聊吧",
    "我觉得你不太聪明",
    "帮我记一下：我下周五要交周报",
    "我下周五要干嘛？",
    "你联网了吗？",
]


def ask(text):
    data = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    rows = []
    for q in QS:
        t0 = time.time()
        try:
            d = ask(q)
            rows.append({"q": q, "a": d.get("answer"), "state": d.get("state"),
                         "refused": d.get("refused"), "blocks": d.get("block_ids"),
                         "ms": int((time.time() - t0) * 1000)})
        except Exception as exc:                             # noqa: BLE001
            rows.append({"q": q, "error": "%s: %s" % (type(exc).__name__, exc)})
        print(json.dumps(rows[-1], ensure_ascii=False))
    with open("kvmem/qq_logs/random_dialogue.json", "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    print("\nTOTAL", len(rows))


if __name__ == "__main__":
    main()