# -*- coding: utf-8 -*-
"""Does the think tag depend on NEWLINES or on content? Same text, newlines deleted only.

Control from the inspector: A joined with `\n` vs A with every newline removed (no character added,
none removed otherwise). If the tag disappears -> newlines/multi-line is necessary.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "kvmem", "m2_visibility", "m2"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "engine"), HERE):
    sys.path.insert(0, p)
import m2_visibility_probe as P
import _driver_m2
import _driver2 as D2

TS = "2026-10-25T09:00:00"
SAMPLE = [
    ("user", "你好呀！"), ("assistant", "你好！有什么可以帮你？"),
    ("user", "我住在广陵路 12 号 2 单元 602。"),
    ("user", "我每天早上七点半出门，别在那个时候给我推消息。"),
    ("user", "我车牌是浙B-3F19K。"), ("assistant", "记住了。"),
    ("user", "帮我查下明天天气。"), ("user", "谢谢，就这样吧。"),
    ("user", "对了，我女儿小名叫豆豆，下周三她生日，提醒我买蛋糕。"),
]
A_NL = "\n".join(t for _r, t in SAMPLE)
A_FLAT = "".join(t for _r, t in SAMPLE)
Q = "我住在哪？"
ANCHOR = 4096
TAG = "<" + "/think" + ">"

res = {"schema": "m4_think_probe2_v1", "pid": os.getpid(), "question": Q,
       "control": "same characters, newlines removed only",
       "cases": []}
eng = P.open_engine()
try:
    for name, text in (("A_newline_joined", A_NL), ("A_newlines_removed", A_FLAT)):
        eng.reset(1); eng.reset(0)
        n = eng.write_at(1, text, 0)
        base = eng.pos_max(1) - n + 1
        eng.repos_local(1, ANCHOR - n - base)
        lo, hi = ANCHOR - n, ANCHOR
        eng.share(1, 0, lo, hi)
        rc, ans = D2.ask_native(eng, 0, Q, ANCHOR, P.N_PREDICT)
        res["cases"].append({"case": name, "tokens": n, "chars": len(text), "rc": rc,
                             "has_tag": TAG in ans, "answer": ans.strip()})
        print("[%s] tokens=%d chars=%d rc=%d tag=%s" % (name, n, len(text), rc, TAG in ans), flush=True)
        print("   %r" % ans.strip()[:150].replace("\n", " | "), flush=True)
        eng.drop(0, lo, hi)
finally:
    eng.close()
verdict = ("newlines_necessary" if res["cases"][0]["has_tag"] and not res["cases"][1]["has_tag"]
           else "not_explained_by_newlines")
res["verdict"] = verdict
print("VERDICT:", verdict, flush=True)
print("@@JSON@@" + json.dumps(res, ensure_ascii=False), flush=True)
