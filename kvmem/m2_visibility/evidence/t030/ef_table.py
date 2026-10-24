import json, os
W = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030"
print("=== E vs F 受控对（同几何/同 cells/同逐段位置，仅 slot4 张量不同）===")
e = json.load(open(os.path.join(W, "curve_E_r1.json"), encoding="utf-8"))
f = json.load(open(os.path.join(W, "curve_F_r1.json"), encoding="utf-8"))
print("%-4s %-9s %-6s %-9s %-8s %-9s %-24s %s" % ("组", "block", "cells", "base", "delta", "pos_lo", "file", "file_sha256"))
for tag, d in (("E", e), ("F", f)):
    for b in d["block_detail"]:
        print("%-4s %-9s %-6s %-9s %-8s %-9s %-24s %s" % (tag, b["id"], b["cells"], b["base"], b["delta"],
              b["pos_lo"], b["file"], b["file_sha256"][:16]))
print()
print("  同 id 的块两两比较：")
em = {b["id"]: b for b in e["block_detail"]}
fm = {b["id"]: b for b in f["block_detail"]}
for k in em:
    a, b = em[k], fm[k]
    print("    %-9s file_sha equal=%-5s delta equal=%-5s pos equal=%-5s (E %s / F %s)"
          % (k, a["file_sha256"] == b["file_sha256"], a["delta"] == b["delta"],
             a["pos_lo"] == b["pos_lo"], a["delta"], b["delta"]))