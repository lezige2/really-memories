# -*- coding: utf-8 -*-
import json
import subprocess
import sys

CHILD = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/hole_child.py"
OUT = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/t030_hole_table.json"
BLOCK = sys.argv[1] if len(sys.argv) > 1 else "project"
HOLES = [0, 1, 2, 4, 8, 16, 32, 64]
rows = []
print("block=%s (one block alone, top moved down by HOLE cells)" % BLOCK)
for h in HOLES:
    p = subprocess.run([sys.executable, "-X", "utf8", CHILD, BLOCK, str(h)],
                       capture_output=True, text=True, encoding="utf-8")
    line = (p.stdout or "").strip().splitlines()
    if p.returncode != 0 or not line:
        print("hole=%-3d FAILED rc=%s %s" % (h, p.returncode, (p.stderr or "")[-120:]))
        rows.append({"hole": h, "error": (p.stderr or "")[-120:]})
        continue
    r = json.loads(line[-1])
    tr = (p.stderr or "").count("[MASKDBG-SUM]")
    r["trace_sum_lines"] = tr
    rows.append(r)
    print("hole=%-3d pos=%s bytes_rc=%-3d ok=%-5s len=%-3d traceSUM=%-2d sha=%s"
          % (h, r["pos"], r["bytes_rc"], r["ok"], r["len"], tr, r["answer_sha256"][:12]))
    print("        answer=%r" % (r["answer"][:60],))
json.dump({"experiment": "t030_hole_table", "block": BLOCK,
           "preregistration": ("a hard -1 at every hole>0 makes a gap between the block top "
                               "and the question point fatal, independent of content"),
           "rows": rows}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("written:", OUT)