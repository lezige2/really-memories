# -*- coding: utf-8 -*-
import hashlib, json, os
D = os.path.dirname(os.path.abspath(__file__))
def sha(x): return hashlib.sha256(x.encode("utf-8")).hexdigest()
def load(t): return json.load(open(os.path.join(D, "out", t + ".json"), encoding="utf-8"))

CELLS = ["run0", "E", "F", "X1", "B57"]
rows = []
for c in CELLS:
    a24 = load(c + "_r1")["answers"][0]
    d64r1, d64r2 = load("np64_" + c + "_r1"), load("np64_" + c + "_r2")
    a64, b64 = d64r1["answers"][0], d64r2["answers"][0]
    cut = len(a24["answer"])
    shown = a64["answer"][:cut] + " ⟪24-token 截止处⟫ " + a64["answer"][cut:]
    rows.append({"cell": c, "sha24": sha(a24["answer"])[:16], "sha64": sha(a64["answer"])[:16],
                 "ok24": a24["ok"], "ok64": a64["ok"],
                 "r1r2_64": a64["answer"] == b64["answer"],
                 "np24_prefix_of_np64": a64["answer"].startswith(a24["answer"]),
                 "answer64_marked": shown,
                 "np64_changed": d64r1["runner"].get("n_predict_changed"),
                 "cells": d64r1["raw"]["cell_count"],
                 "gap": d64r1["layout"]["head_gap_cells"],
                 "pos": [d64r1["raw"]["positions_min"], d64r1["raw"]["positions_max"]],
                 "ctrl": d64r1["control_ok"],
                 "dll": d64r1["engine"]["loaded_dll_sha256"],
                 "vram_free": d64r1["runner"]["vram_before_mib"]["free"]})

print("B57_r2 present:", os.path.exists(os.path.join(D, "out", "np64_B57_r2.json")))
print()
for r in rows:
    print("| %s | %s | %s | %s | %s | %s |" % (r["cell"], r["sha24"], r["sha64"],
          r["r1r2_64"], r["np24_prefix_of_np64"], r["ok64"]))
print()
for r in rows:
    print("--- %s @64 ---" % r["cell"])
    print(r["answer64_marked"])
    print()
json.dump(rows, open(os.path.join(D, "final_table.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
# invariants across the whole np64 batch
inv = {k: {str(r[k]) for r in rows} for k in ("cells", "gap", "ctrl", "dll", "vram_free", "np64_changed")}
print("np64 batch invariants:", {k: (list(v)[0] if len(v) == 1 else v) for k, v in inv.items()})
print("positions:", {r["cell"]: r["pos"] for r in rows})
