# -*- coding: utf-8 -*-
import json
import subprocess
import sys

CHILD = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/precheck_child.py"
OUT = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/t030_precheck_single_block.json"
rows = []
for place in ("car_back", "top"):
    print("=== place=%s ===" % place)
    for b in ("home", "project", "habit", "car"):
        p = subprocess.run([sys.executable, "-X", "utf8", CHILD, b, place],
                           capture_output=True, text=True, encoding="utf-8")
        line = (p.stdout or "").strip().splitlines()
        if p.returncode != 0 or not line:
            print("%-8s FAILED rc=%s %s" % (b, p.returncode, (p.stderr or "")[-150:]))
            rows.append({"block": b, "place": place, "error": (p.stderr or "")[-150:]})
            continue
        r = json.loads(line[-1])
        rows.append(r)
        print("%-8s cells=%s pos=%s ok=%-5s bytes=%-3s len=%-3s sha=%s"
              % (b, r["cells_on_live"], r["positions"], r["ok"], r["bytes"], r["len"],
                 r["answer_sha256"][:16]))
        print("         answer=%r" % (r["answer"][:70],))
json.dump({"experiment": "t030_precheck_single_block", "layout": "iso_car_back",
           "preregistration": ("if single-block home->home passes, trial routing has a solution; "
                               "if it fails, the suppression story is dead and stage C is next"),
           "rows": rows}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("written:", OUT)