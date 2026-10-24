# -*- coding: utf-8 -*-
"""T-031 task 2 driver: reuse _driver2's run path verbatim, only the slot-4 block changes.

Nothing in _driver2.py or fixtures.json is modified: the new block and the new layout are
injected into the in-memory registries, so this run exercises the same code path (control
text, placement, ask) as the iso_fac_pp18 arm.
"""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ISO2 = os.path.join(os.path.dirname(HERE), "runs_iso2")
sys.path.insert(0, ISO2)
import _driver2 as D2                                            # noqa: E402

P = D2.P
SIDE = os.path.join(P.M2_DIR, "habit_paraphrase.json")
DLL = os.path.join(P.ROOT, "tools", "kvshim_vk.dll")


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    block = json.load(open(SIDE, encoding="utf-8"))
    if sha256(block["file"]) != block["sha256"]:
        raise SystemExit("habit_paraphrase.kvmem sha changed since it was built")

    orig = P.load_manifest

    def load_manifest(require=True):
        m = orig(require)
        m["blocks"]["variant"]["habit_paraphrase"] = {
            "path": block["file"], "cells": block["cells"], "sha256": block["sha256"],
            "text": block["text"], "source": "T-031 paraphrase of habit; roundtrip verified"}
        return m

    P.load_manifest = load_manifest
    D2.LAYOUTS["iso_fac_hp12"] = {
        "spacing": 64,
        "segs": [(1, "home", "home"), (2, "project", "project"),
                 (3, "habit", "habit"),
                 (4, "habit_paraphrase", "habit_paraphrase", "variant")]}
    D2.CTRL_CACHE = os.path.join(HERE, "control_texts_t032.json")

    rc = D2.main()

    # _driver2 records the dll sha from fixtures.json, which is stale after a rebuild.
    out = sys.argv[sys.argv.index("--run-json") + 1]
    if os.path.exists(out):
        d = json.load(open(out, encoding="utf-8"))
        d["engine"]["dll_sha256_manifest"] = d["engine"].get("dll_sha256")
        d["engine"]["dll_sha256"] = sha256(DLL)
        d["engine"]["dll_mtime"] = os.path.getmtime(DLL)
        d["slot4_block"] = {"file": block["file"], "cells": block["cells"],
                            "sha256": block["sha256"], "text": block["text"]}
        with open(out, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
