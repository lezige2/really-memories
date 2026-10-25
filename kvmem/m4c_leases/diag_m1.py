# -*- coding: utf-8 -*-
"""诊断：cmd_m1 为什么 KeyError（不加载 KV 引擎，只查 DB 与检索）"""
import json, os, sys
ROOT = r"D:\llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import chat as C
con = C.ms.connect(C.DB)
allrows = C.ms.block_rows(con)
print("block_rows 总数:", len(allrows))
print("字段示例:", [x for x in allrows[0]][:9] if allrows else None)
kept = [r for r in allrows if r[5] is not None]
print("r[5] is not None 的:", len(kept), [r[1] for r in kept])
print("被过滤掉的:", [r[1] for r in allrows if r[5] is None])
for q in [C.CONTROL_Q] + C.QUESTIONS:
    try:
        sel = C._selection(con, q)
        print("选择", q[:12], "->", [s["name"] for s in sel])
    except Exception as exc:
        print("选择失败", q[:12], type(exc).__name__, exc)
con.close()
