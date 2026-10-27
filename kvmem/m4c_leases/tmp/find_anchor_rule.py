# -*- coding: utf-8 -*-
"""找出哪种口径能重现文档锚 fa94b1bc58c0e421（否则该锚不可复核）"""
import hashlib, json, re
P = r"D:\llama-mem\kvmem\sessions\live.json"
TARGET = "fa94b1bc58c0e421"
raw = open(P, "rb").read()
txt = raw.decode("utf-8")
doc = json.loads(txt)

def h(s):
    if isinstance(s, str): s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()[:16]

def strip(o):
    if isinstance(o, dict): return {k: strip(v) for k, v in o.items() if k != "saved_at"}
    if isinstance(o, list): return [strip(v) for v in o]
    return o

cands = {}
# 1 行级删除 saved_at 行后对原文取哈希
cands["raw_minus_saved_at_line"] = h("\n".join(l for l in txt.split("\n") if '"saved_at"' not in l))
# 2 去掉该行并补回结尾换行
cands["raw_minus_line_nl"] = h("\n".join(l for l in txt.split("\n") if '"saved_at"' not in l) + "\n")
# 3 正则删除 "saved_at": ... ,（含行尾逗号）
cands["raw_regex"] = h(re.sub(r'\s*"saved_at"\s*:\s*"[^"]*",?', "", txt))
# 4 canonical json 递归剥离
for name, kw in [("canon_sep", dict(sort_keys=True, ensure_ascii=False, separators=(",", ":"))),
                 ("canon_default", dict(sort_keys=True, ensure_ascii=False)),
                 ("canon_ascii", dict(sort_keys=True, ensure_ascii=True)),
                 ("indent2", dict(sort_keys=True, ensure_ascii=False, indent=2)),
                 ("indent2_ascii", dict(sort_keys=True, ensure_ascii=True, indent=2))]:
    cands["strip_" + name] = h(json.dumps(strip(doc), **kw))
# 5 只删顶层
top = {k: v for k, v in doc.items() if k != "saved_at"}
cands["toponly_canon"] = h(json.dumps(top, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
# 6 删除 saved_at 后按插入序
cands["strip_ordered"] = h(json.dumps(strip(doc), ensure_ascii=False, separators=(",", ":")))

hits = [k for k, v in cands.items() if v == TARGET]
print("目标:", TARGET)
for k, v in cands.items():
    print(("  HIT " if v == TARGET else "      ") + k, v)
print("命中口径:", hits or "无")
print("顶层键:", sorted(doc.keys()))
