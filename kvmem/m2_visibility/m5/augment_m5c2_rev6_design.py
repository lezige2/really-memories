#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Attach offline readout to M5C2-REV6-B4DESIGN.json; no model, no gold edits."""
import hashlib, json, os
from pathlib import Path

OUT = Path(r"D:\llama-mem\kvmem\m2_visibility\m5\out")
DES = OUT / "M5C2-REV6-B4DESIGN.json"
RO = OUT / "M5C2-REV6-B4DESIGN-READOUT.json"

def sha16(b): return hashlib.sha256(b).hexdigest()[:16]

def main():
    db = DES.read_bytes(); rb = RO.read_bytes()
    d = json.loads(db.decode("utf-8")); r = json.loads(rb.decode("utf-8"))
    if d.get("design_set") is not True or d.get("not_acceptance") is not True:
        raise SystemExit("design flags missing")
    if len(d.get("items", [])) != 261:
        raise SystemExit("expected 261")
    d["design_readout"] = {
        "gate": r["gate"],
        "evidence_verbatim_rate": r["evidence_verbatim_rate"],
        "false_unsupported": r["new_rev6"]["false_unsupported"],
        "false_by_reason": r["new_rev6"]["false_unsupported"]["by_reason"],
        "leak": r["new_rev6"]["leak"],
        "strict_leak": r["new_rev6"]["strict_leak"],
        "empty_items_model": r["new_rev6"]["empty_items_model"],
        "verdict_policyA_counts": r["new_rev6"]["verdict_counts"],
        "verdict_policyB_counts": r["new_rev6"]["verdict_policyB_counts"],
        "old_rev5_1": r["old_rev5_1"],
        "false_examples_change": r["false_examples_change"],
        "leak_examples_change": r["leak_examples_change"],
        "new_leak_added": r["new_leak_added"],
        "new_leak_removed": r["new_leak_removed"],
        "new_false_added": r["new_false_added"],
        "new_false_removed": r["new_false_removed"],
        "readout_artifact": "M5C2-REV6-B4DESIGN-READOUT.json",
        "readout_sha16": sha16(rb),
        "readout_offline_no_gpu": True,
    }
    d["gold_sha16_current"] = r["gold_sha16_current"]
    d["gold_sha16_original"] = r["gold_sha16_original"]
    d["gold_values_unchanged_vs_M5B4-RATES"] = r["gold_values_unchanged_vs_M5B4-RATES"]
    d["gold_file_note"] = r["gold_file_note"]
    d["same_sentences"] = 261
    d["same_gold_values"] = True
    d["readout_artifact_sha16"] = sha16(rb)
    tmp = str(DES) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1); f.write("\n")
    os.replace(tmp, DES)
    print(json.dumps({"design_sha16": sha16(DES.read_bytes()),
                      "design_bytes": DES.stat().st_size,
                      "readout_sha16": sha16(rb),
                      "gate": d["design_readout"]["gate"],
                      "verbatim": d["design_readout"]["evidence_verbatim_rate"]},
                     ensure_ascii=False, indent=1))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
