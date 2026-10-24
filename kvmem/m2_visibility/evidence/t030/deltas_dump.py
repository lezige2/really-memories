# -*- coding: utf-8 -*-
"""Dump (file, cells, base, delta, pos_lo) for every block of a layout -- no ask."""
import json
import sys
sys.path.insert(0, r"D:/llama-mem/tools")
sys.path.insert(0, r"D:/llama-mem/kvmem/m2_visibility/runs_iso2")
import m2_visibility_probe as P
import _driver2 as D2

OUT = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/deltas_%s.json"
manifest = P.load_manifest()
eng = P.open_engine()
try:
    for key in sys.argv[1:]:
        layout = D2.build_layout(key, manifest)
        P.reset_all(eng)
        placed = P.load_and_place(eng, layout)
        print("=== %s ===" % key)
        for p in placed:
            print("  %-8s slot=%d cells=%2d base=%4d delta=%+5d pos=[%d,%d] file=%s"
                  % (p["id"], p["slot"], p["cells"], p["base"], p["delta"], p["pos_lo"],
                     p["pos_hi"] - 1, p["file"]))
        json.dump({"layout": key, "placed": placed}, open(OUT % key, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("  written:", OUT % key)
finally:
    eng.close()