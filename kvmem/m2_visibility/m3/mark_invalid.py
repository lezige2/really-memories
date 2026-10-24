# -*- coding: utf-8 -*-
"""Stamp run_m3_50_INVALID.json so no batch tally can mistake it for a valid negative result."""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "run_m3_50_INVALID.json")
d = json.load(io.open(p, encoding="utf-8"))
d["INVALID"] = True
d["invalid_reason"] = ("Every round called m2_visibility_probe.reset_all(), which is "
                       "for s in range(N_SEQ): eng.reset(s) -- it wipes the three block slots. "
                       "All 50 rounds therefore attached 0 block cells and the model answered "
                       "from world knowledge. NOT evidence about lifecycle stability.")
d["do_not_aggregate"] = True
d["superseded_by"] = "run_m3_50.json"
d["schema"] = "m3_lifecycle_v1_INVALID"
d["rounds_summary"] = {"rounds": len(d["rounds"]),
                       "addr_ok_count": sum(1 for r in d["rounds"] if r["addr_ok"]),
                       "attach_block_cells": "not recorded in v1 schema; attach_cells was 0",
                       "note": "block cells were never attached, so every answer is world knowledge"}
json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
print("stamped INVALID")
