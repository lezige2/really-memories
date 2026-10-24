# -*- coding: utf-8 -*-
"""M4 cross-experiment: the same layout with the plate sentence REMOVED, then ask for the plate.

Purpose: turn the supporting observation ("the answer comes from the block") into a within-M4
ablation -- if the model still produces a plate when the block never contained one, the answer is
not block-derived and the wording must stay downgraded.
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
import m4_extract as X
import m4_display as DISP

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
DROP = "我车牌是浙B-3F19K。"
ASK_PLATE = "我车牌号是多少？"
ASK_HOME = "我住在哪？"
ANCHOR = 4096
TAG = "<" + "/think" + ">"

res = {"schema": "m4_crosscheck_v1", "pid": os.getpid(),
       "ablation": "removed the plate sentence from the SAME conversation",
       "removed_sentence": DROP}
rounded = [t for t in SAMPLE if t["text"] != DROP]
res["turns"] = len(rounded)
res["block_contains_plate"] = any("浙B-3F19K" in t["text"] for t in rounded)
keeps = [(r, m) for r in X.run(rounded) for m in r["memories"]]
res["keeps"] = [{"attr": m["attr"], "value": m["value"]} for _r, m in keeps]
res["has_plate_memory"] = any(m["attr"] == "车牌" for _r, m in keeps)

text = "\n".join(t["text"] for t in rounded)
eng = P.open_engine()
try:
    eng.reset(1)
    eng.reset(0)
    n = eng.write_at(1, text, 0)
    base = eng.pos_max(1) - n + 1
    eng.repos_local(1, ANCHOR - n - base)
    lo, hi = ANCHOR - n, ANCHOR
    res["block"] = {"tokens": n, "range": [lo, hi]}
    for label, q in (("plate", ASK_PLATE), ("home_control", ASK_HOME)):
        if label != "plate":
            eng.reset(0)                     # generated tokens stay resident; clear them
        eng.share(1, 0, lo, hi)
        rc, ans = D2.ask_native(eng, 0, q, ANCHOR, P.N_PREDICT)
        eng.drop(0, lo, hi)
        d = DISP.derive(ans.strip()) if DISP.has_tag(ans) else {"answer_display": ans.strip()}
        res[label] = {"q": q, "rc": rc, "answer": ans.strip(),
                      "answer_display": d.get("answer_display"),
                      "fabricated_value": "浙B-3F19K" in ans,
                      "says_unknown": any(w in ans for w in ("没有", "不知道", "未记录", "不清楚"))}
        print("[%s] rc=%d fake=%s unknown=%s" % (label, rc, res[label]["fabricated_value"],
                                                 res[label]["says_unknown"]), flush=True)
        print("   %r" % ans.strip()[:140].replace("\n", " | "), flush=True)
finally:
    eng.close()

plate = res["plate"]
res["verdict"] = ("block_derived" if not plate["fabricated_value"]
                  else "reproduced_without_source")
res["control_ok"] = (res.get("home_control", {}).get("rc") or -1) > 0
if not res["control_ok"]:
    res["verdict"] = "inconclusive_no_control"
print("VERDICT:", res["verdict"], flush=True)
out = os.path.join(HERE, "run_m4_crosscheck.json")
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("@@JSON@@" + json.dumps(res, ensure_ascii=False), flush=True)
print("[RUN] wrote", out, flush=True)
