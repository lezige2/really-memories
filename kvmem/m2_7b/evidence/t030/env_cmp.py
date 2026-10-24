import json
W = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030"
ok = json.load(open(W + "/env_ok.json", encoding="utf-8"))
bad = json.load(open(W + "/env_fail.json", encoding="utf-8"))
print("成功跑: pos=%s ask=%s cells=%s rc=%s" % (ok["pos"], ok["ask_pos"], ok["cells"], ok["rc"]))
print("失败跑: pos=%s ask=%s cells=%s rc=%s" % (bad["pos"], bad["ask_pos"], bad["cells"], bad["rc"]))
for k in sorted(set(ok["env"]) | set(bad["env"])):
    a1, a2 = ok["env"].get(k), bad["env"].get(k)
    print("  %-26s 成功=%-26s 失败=%-26s %s" % (k, str(a1)[:26], str(a2)[:26], "相同" if a1 == a2 else "不同"))