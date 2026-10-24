# -*- coding: utf-8 -*-
"""Render the 50-round table from run_m3_50.json. No model needed."""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(io.open(os.path.join(HERE, "run_m3_50.json"), encoding="utf-8"))
rows = d["rounds"]
lines = ["# M3 · 50 轮 attach/detach 逐轮表", "",
         "引擎一次加载跑完；块只在开头从原文件装载一次，之后每轮 attach/detach 同一批 cell。", "",
         "| 轮 | 块占用(cell) | raw_pos_max | 卸载后块占用 | 住址答案前 40 字 | 命中 | 块文件 sha16 | 耗时(s) |",
         "|---|---|---|---|---|---|---|---|"]
for r in rows:
    a = r["asks"][0]["answer"].replace("|", "/").replace("\n", " ")[:40]
    sha = " ".join("%s=%s" % (k, v) for k, v in sorted(r["block_sha16"].items()))
    lines.append("| %d | %d | %s | %d | %s | %s | %s | %.1f |"
                 % (r["round"], r["attach_block_cells"], r["attach_raw_pos_max"],
                    r["after_detach_block_cells"], a, "OK" if r["addr_ok"] else "MISS", sha,
                    r["elapsed_s"]))
io.open(os.path.join(HERE, "table_m3_rounds.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

cp = {r["round"]: r for r in rows if r["round"] in (1, 25, 50)}
out = ["", "## 第 1/25/50 轮完整答案", ""]
for k in (1, 25, 50):
    out.append("### 第 %d 轮" % k)
    for a in cp[k]["asks"]:
        out.append("- 问：%s" % a["question"])
        out.append("  - 答：%s" % a["answer"].replace("\n", " / "))
        out.append("  - 命中：%s" % (a["hit"] or "无"))
    out.append("")
io.open(os.path.join(HERE, "table_m3_rounds.md"), "a", encoding="utf-8").write("\n".join(out) + "\n")

acc = d["acceptance"]
print("cells distinct:", acc["1_cells_stable"]["distinct"],
      "| pos_max distinct:", acc["2_pos_max_stable"]["distinct"])
print("addr hits over 50:", acc["3_answer_stable"]["addr_hits_over_50_rounds"],
      "| identical 1/25/50:", acc["3_answer_stable"]["identical_1_25_50"])
print("r1 addr answer:", repr(cp[1]["asks"][0]["answer"][:60]))
print("distinct addr answers:", len({r["asks"][0]["answer"] for r in rows}))
print("total elapsed:", d["elapsed_s"], "s | median round:",
      sorted(r["elapsed_s"] for r in rows)[25])
print("wrote table_m3_rounds.md")
