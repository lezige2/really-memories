import json, os
W = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030"
def load(n):
    return json.load(open(os.path.join(W, n), encoding="utf-8"))
print("=== 四格（project 单块，只改块尾与提问点）===")
for name, tag in (("grid1.json", "(块尾4095, 问4096) 基线复核"),
                  ("grid4.json", "(块尾4095, 问4095) 第四格")):
    d = load(name)
    print("%-28s blocks=%s ask_pos=%s rc=%-3s ok=%-5s len=%d" % (tag, d["blocks"], d["ask_pos"], d["rc"], d["ok"], len(d["answer"])))
    print("    attention window pos: block=[%s,%s] cells=%s" % ("?", "?", d["cells_on_live"]))
    print("    answer=%r" % (d["answer"][:100],))
    print("    top5=%s" % [(t["token"], round(t["prob"], 5)) for t in d["topk"]])
print()
h = load("hole_askat4095_a.json")
print("=== 复查上一轮判别那一跑的构型 ===")
print("  块 [4077,4094]（18 cells，块尾 4094），提问 4095 ⇒ **洞 = 0**，rc=%s" % h["rc"])
print()
print("=== 六组答案全文 + top8 ===")
for n in "ABCDEF":
    d = load("curve_%s_r1.json" % n)
    print("%s blocks=%-28s ok=%-5s rc=%-3s p_fact=%s rank=%s" % (n, ",".join(d["blocks"]), d["ok"], d["rc"],
          d.get("p_fact"), d.get("rank_fact")))
    print("   answer: %s" % d["answer"].replace(chr(10), " / "))
    print("   top8  : %s" % [(t["token"], round(t["prob"], 5)) for t in d["topk"]])