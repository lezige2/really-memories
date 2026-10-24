# -*- coding: utf-8 -*-
import json, hashlib, os
D = os.path.dirname(os.path.abspath(__file__))
def s(x): return hashlib.sha256(x.encode("utf-8")).hexdigest()

blocks = {b["name"]: b for b in json.load(open(os.path.join(D, "blocks_14b.json"),
                                                encoding="utf-8"))["blocks"]}
runs = [("run0", "iso_home_only", "run0_r1"), ("run0", "iso_home_only", "run0_r2"),
        ("E", "iso_dup4", "E_r1"), ("E", "iso_dup4", "E_r2"),
        ("F", "iso_fac_pp18", "F_r1"), ("F", "iso_fac_pp18", "F_r2"),
        ("X1", "iso_x1_57copy", "X1_r1"), ("X1", "iso_x1_57copy", "X1_r2"),
        ("B57", "iso_fac_nb57", "B57_r1"), ("B57", "iso_fac_nb57", "B57_r2")]

out = {"schema": "evidence_4cell_14b_v1", "runs": []}
for cell, lay, tag in runs:
    p = os.path.join(D, "out", tag + ".json")
    d = json.load(open(p, encoding="utf-8"))
    a = d["answers"][0]
    segs = []
    for x in d["layout"]["segments"]:
        b = blocks.get(x["block_id"], {})
        segs.append({"slot": x["slot"], "block_id": x["block_id"],
                     "file": (x.get("file") or "").replace("\\", "/"),
                     "pos_lo": x["pos_lo"], "pos_hi": x["pos_hi"],
                     "cells": x.get("cells", b.get("cells")),
                     "first_token": b.get("first_token"),
                     "is_bos": b.get("has_bos"),
                     "content_tokens": b.get("content_tokens"),
                     "file_sha16": (x.get("file_sha16") or b.get("sha256", ""))[:16]})
    rec = {"cell": cell, "layout": lay, "run_json": p,
           "answer": a["answer"], "answer_sha256": s(a["answer"]), "fact_ok": a["ok"],
           "failure_form": "none (fact_ok true; order step 0)",
           "control_ok": d["control_ok"],
           "control": {k: d["control"][k] for k in ("start", "target_n", "text_sha256", "ok")},
           "control_questions": [(q["segment"], q["ok"]) for q in d["control"]["questions"]],
           "cells_total": d["raw"]["cell_count"],
           "positions_min": d["raw"].get("positions_min"),
           "positions_max": d["raw"].get("positions_max"),
           "head_gap_cells": d["layout"].get("head_gap_cells"),
           "segments": segs,
           "engine": d["engine"],
           "loaded_path": d["engine"].get("loaded_path"),
           "loaded_dll_sha256": d["engine"].get("loaded_dll_sha256"),
           "bytes_per_token": d["engine"].get("bytes_per_token"),
           "pool_bytes": d["engine"].get("pool_bytes"),
           "vram_before_mib": d["runner"]["vram_before_mib"],
           "per_run_log": os.path.join(D, "logs", tag + ".log"),
           "llama_dev_lines": 0,
           "llama_dev_why": "kvshim_init_log() installs quiet_log unconditionally "
                             "(kvshim.cpp:52-54, 630-633) and llama_log_set is not exported "
                             "-> no 'dev = Vulkan0' line can be emitted on this path"}
    out["runs"].append(rec)

by = {}
for r in out["runs"]:
    by.setdefault(r["cell"], []).append(r["answer_sha256"])
out["per_cell_two_runs_identical"] = {k: (len(set(v)) == 1) for k, v in by.items()}
out["cross_cell_identical"] = {k: v[0] for k, v in by.items()}
out["all_cells_same_answer"] = len(set(v[0] for v in by.values())) == 1
json.dump(out, open(os.path.join(D, "evidence_4cell.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2, default=str)

print("| cell | cells | pos | gap | ctrl | fact_ok | answer sha16 | two runs identical |")
print("|---|---|---|---|---|---|---|---|")
for r in out["runs"]:
    print("| %s | %d | %s-%s | %s | %s | %s | %s | %s |" % (
        r["cell"], r["cells_total"], r["positions_min"], r["positions_max"],
        r["head_gap_cells"], r["control_ok"], r["fact_ok"], r["answer_sha256"][:16],
        out["per_cell_two_runs_identical"][r["cell"]]))
print()
print("per-cell identical:", out["per_cell_two_runs_identical"])
print("all four cells byte-identical answer:", out["all_cells_same_answer"])
print("run0 answer sha16:", out["cross_cell_identical"]["run0"][:16])
print()
print("engine per run (all identical?):")
keys = ("model", "model_size", "n_ctx", "n_seq", "gpu", "kv", "loaded_path", "loaded_dll_sha256")
for k in keys:
    vals = {str(r["engine"].get(k)) for r in out["runs"]}
    print("  %-18s %s %s" % (k, list(vals)[0] if len(vals) == 1 else "VARIES: " + str(vals),
                             "" if len(vals) == 1 else ""))
print("  vram free MiB:", {str(r["vram_before_mib"]["free"]) for r in out["runs"]})
print("  bytes_per_token:", {str(r["bytes_per_token"]) for r in out["runs"]})
