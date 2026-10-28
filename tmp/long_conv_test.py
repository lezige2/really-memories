# -*- coding: utf-8 -*-
"""长对话压测：灌约 40k 字符，触发 rollover，再考察早期/中期/近期事实召回。"""
import json
import time
import urllib.request

EP = "http://127.0.0.1:8765"


def post(path, payload):
    req = urllib.request.Request(EP + path, data=json.dumps(payload, ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path):
    with urllib.request.urlopen(EP + path, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def status_tokens():
    try:
        return get("/status").get("session", {}).get("chat_tokens")
    except Exception:                                # noqa: BLE001
        return None


FACTS = {
    1: "我叫阿泽，我的车牌号是京A88888。",
    2: "我下周五要去成都开会，我养的猫叫豆豆。",
}


def main():
    post("/reset", {})
    sent_chars = 0
    turn = 0
    rollovers = []
    t0 = time.time()
    while sent_chars < 40000:
        turn += 1
        if turn in FACTS:
            text = FACTS[turn]
        else:
            _body = ("今天上午整理资料，下午开会讨论方案，晚上复盘并记录日志；"
                     "明天计划去图书馆查资料，周末想去公园走走，顺便买点日用品和水果；"
                     "另外还在考虑下个月的出差安排，需要提前订票和准备材料。")
            text = ("这是我第%d条测试消息，下面是我今天的安排：" % turn) + _body * 3
        d = post("/ask", {"text": text})
        sent_chars += len(text)
        if d.get("rollover"):
            rollovers.append({"turn": turn, "tokens": status_tokens(),
                              "rollover": d.get("rollover")})
            print("ROLLOVER at turn", turn, "chars", sent_chars,
                  json.dumps(d.get("rollover"), ensure_ascii=False)[:160], flush=True)
        if turn % 50 == 0:
            print("turn", turn, "chars", sent_chars, "tokens", status_tokens(), flush=True)
    print("done chars", sent_chars, "turns", turn, "tokens", status_tokens(),
          "rollovers", len(rollovers), "elapsed %.0fs" % (time.time() - t0), flush=True)

    probes = [
        ("我叫什么名字？", ["阿泽"]),
        ("我的车牌号是多少？", ["京A88888"]),
        ("我下周五要去哪开会？", ["成都"]),
        ("我养的猫叫什么名字？", ["豆豆"]),
        ("我们最开始聊了什么？", None),
        ("最近在聊什么？", None),
        ("你现在记得几条长期记忆？", None),
    ]
    out = []
    for q, expect in probes:
        d = post("/ask", {"text": q})
        a = str(d.get("answer") or "")
        ok = (expect is None) or any(w in a for w in expect)
        out.append({"q": q, "answer": a[:120], "pass": ok, "state": d.get("state"),
                    "blocks": d.get("block_ids")})
        print(("PASS " if ok else "FAIL ") + q + " -> " + a[:90], flush=True)
    json.dump({"turns": turn, "chars": sent_chars, "tokens_now": status_tokens(),
               "rollovers": rollovers, "probes": out},
              open("out/LONG-CONV-TEST.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("saved out/LONG-CONV-TEST.json")


if __name__ == "__main__":
    main()