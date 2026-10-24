# -*- coding: utf-8 -*-
"""Where does the closing think tag come from? Three block texts, one question, one engine.

  A = the M4 conversation (contains assistant turns)
  B = M2-style prose (no dialogue, no assistant turns)
  C = the same conversation with every assistant turn removed
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "kvmem", "m2_visibility", "m2"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "engine"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "m3"), HERE):
    sys.path.insert(0, p)
import m2_visibility_probe as P
import _driver_m2
import _driver2 as D2
import m4_extract as X

TS = "2026-10-25T09:00:00"
SAMPLE = [
    {"role": "user", "text": "你好呀！", "ts": TS},
    {"role": "assistant", "text": "你好！有什么可以帮你？", "ts": TS},
    {"role": "user", "text": "我住在广陵路 12 号 2 单元 602。", "ts": TS},
    {"role": "user", "text": "我每天早上七点半出门，别在那个时候给我推消息。", "ts": TS},
    {"role": "user", "text": "我车牌是浙B-3F19K。", "ts": TS},
    {"role": "assistant", "text": "记住了。", "ts": TS},
    {"role": "user", "text": "帮我查下明天天气。", "ts": TS},
    {"role": "user", "text": "谢谢，就这样吧。", "ts": TS},
    {"role": "user", "text": "对了，我女儿小名叫豆豆，下周三她生日，提醒我买蛋糕。", "ts": TS},
]
A = "\n".join(t["text"] for t in SAMPLE)
B = ("我住在广陵路 12 号 2 单元 602。项目三月十四上线。我喝美式咖啡不加糖。"
     "我每天早上七点半出门。我车牌是浙B-3F19K。")
C = "\n".join(t["text"] for t in SAMPLE if t["role"] == "user")
Q = "我住在哪？"
ANCHOR = 4096
TAG = "<" + "/think" + ">"

res = {"schema": "m4_think_probe_v1", "pid": os.getpid(), "question": Q,
       "template": repr("\n问：" + Q + "\n答："), "tag": TAG, "cases": []}
eng = P.open_engine()
try:
    for name, text in (("A_conversation_with_assistant", A),
                       ("B_prose_no_dialogue", B),
                       ("C_conversation_user_only", C)):
        eng.reset(1)
        eng.reset(0)
        n = eng.write_at(1, text, 0)
        base = eng.pos_max(1) - n + 1
        eng.repos_local(1, ANCHOR - n - base)
        lo, hi = ANCHOR - n, ANCHOR
        eng.share(1, 0, lo, hi)
        rc, ans = D2.ask_native(eng, 0, Q, ANCHOR, P.N_PREDICT)
        res["cases"].append({"case": name, "text_head": text[:40], "tokens": n,
                             "rc": rc, "has_tag": TAG in ans,
                             "answer": ans.strip()})
        print("[%s] tokens=%d rc=%d tag=%s" % (name, n, rc, TAG in ans), flush=True)
        print("   %r" % ans.strip()[:160].replace("\n", " | "), flush=True)
        eng.drop(0, lo, hi)
finally:
    eng.close()
print("@@JSON@@" + json.dumps(res, ensure_ascii=False), flush=True)
