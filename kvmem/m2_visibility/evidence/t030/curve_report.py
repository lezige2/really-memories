import json, glob, math, os
W = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030"
d = json.load(open(os.path.join(W, "hole_askat4095_a.json"), encoding="utf-8"))
print("=== 判别：洞=1，块 [4077,4094]，提问点 4095 ===")
print("  blocks=%s ask_pos=%s rc=%s ok=%s len=%d" % (d["blocks"], d["ask_pos"], d["rc"], d["ok"], len(d["answer"])))
print("  answer=%r" % (d["answer"][:80],))
print()
print("=== A–F 曲线（问 home，首步 top-8，fact token 35946）===")
rows = {}
for name in "ABCDEF":
    r1 = json.load(open(os.path.join(W, "curve_%s_r1.json" % name), encoding="utf-8"))
    r2 = json.load(open(os.path.join(W, "curve_%s_r2.json" % name), encoding="utf-8"))
    same = r1["topk"] == r2["topk"] and r1["answer"] == r2["answer"]
    rows[name] = r1
    pf = r1.get("p_fact")
    print("%s %-14s blocks=%-22s cells=%-3s rc=%-3s ok=%-5s p_fact=%-9s rank=%-4s logp=%s det=%s" % (
        name, r1["name"], ",".join(r1["blocks"])[:22], r1["cells_on_live"], r1["rc"], r1["ok"],
        ("%.6f" % pf) if pf is not None else "-", r1.get("rank_fact"),
        ("%.3f" % math.log(pf)) if pf else "n/a", same))
    print("     top8=%s" % [(t["token"], round(t["prob"], 5)) for t in r1["topk"]])
    print("     answer=%r" % (r1["answer"][:50],))
print()
print("=== 比值（分母 A；若 p(A)<1e-3 判 uninformative） ===")
pa = rows["A"]["p_fact"]
for name in "BCDEF":
    p = rows[name]["p_fact"]
    print("  p(%s)/p(A) = %s" % (name, ("%.4f" % (p / pa)) if pa and pa >= 1e-3 else "uninformative"))
pa_ = rows["F"]["p_fact"]
print("  p(F)/p(E) = %s" % (("%.4f" % (rows["F"]["p_fact"] / rows["E"]["p_fact"])) if rows["E"]["p_fact"] else "n/a"))