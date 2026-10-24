# -*- coding: utf-8 -*-
"""T-033 arms: reuse _driver2.main() verbatim, inject only the layout.

Arm H1  iso_fac_hh12 : exactly H2's geometry (iso_fac_hp12), slot4 block swapped from
                       habit_paraphrase.kvmem to the pristine m2_v1/habit.kvmem copy.
Arm B   iso_fac_nb57 : home(slot1) + project(slot2) + project_paraphrase18(slot4),
                       habit absent.

No block is built, no fixtures.json field is edited: the layouts are injected into
_driver2.LAYOUTS before argparse reads its choices.
"""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ISO2 = os.path.join(os.path.dirname(HERE), "runs_iso2")
sys.path.insert(0, ISO2)
import _driver2 as D2                                            # noqa: E402

P = D2.P
sys.path.insert(0, os.path.join(P.ROOT, "tools"))
import block_info as BI                                          # noqa: E402

DLL = os.path.join(P.ROOT, "tools", "kvshim_vk.dll")
OLD_CTRL = [os.path.join(HERE, "..", "runs_t032", "control_texts_t032.json"),
            os.path.join(ISO2, "control_texts.json")]


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# start-position -> an already-measured control text for that start (verified by
# get_control itself: start must match and measure(text) must equal target_n).
def seed_ctrl(cache_path):
    if os.path.exists(cache_path):
        return
    seeds, by_start = {}, {}
    for p in OLD_CTRL:
        if not os.path.exists(p):
            continue
        for k, v in json.load(open(p, encoding="utf-8")).items():
            by_start.setdefault(v["start"], v)
    for key, spec in D2.LAYOUTS.items():
        if key not in ("iso_fac_hh12", "iso_fac_nb57"):
            continue
        start = min(P.CHAT - (s[0] - 1) * spec["spacing"]
                    - P.load_manifest()["blocks"][s[3] if len(s) > 3 else "m2"][s[2]]["cells"]
                    for s in spec["segs"])
        if start in by_start:
            seeds[key] = dict(by_start[start])
    if seeds:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(seeds, f, ensure_ascii=False, indent=1)


def block_meta(file):
    d = BI.info(file)
    return {"loaded_path": os.path.abspath(file),
            "file": os.path.basename(file), "cells": d["cells"],
            "cells_from_size": d["cells_from_size"], "size_rem": d["size_rem"],
            "has_bos": d["has_bos"], "content_tokens": d["content_tokens"],
            "sha256": sha256(file), "sha16": d["sha16"],
            "first8": [int(t) for t in d["tokens"][:8]]}


def main():
    D2.LAYOUTS["iso_fac_hh12"] = {
        "spacing": 64,
        "segs": [(1, "home", "home"), (2, "project", "project"),
                 (3, "habit", "habit"), (4, "habit_copy", "habit")]}
    D2.LAYOUTS["iso_fac_nb57"] = {
        "spacing": 64,
        "segs": [(1, "home", "home"), (2, "project", "project"),
                 (4, "pp18", "project_paraphrase18", "variant")]}
    D2.CTRL_CACHE = os.path.join(HERE, "control_texts_t033.json")
    seed_ctrl(D2.CTRL_CACHE)

    rc = D2.main()

    out = sys.argv[sys.argv.index("--run-json") + 1]
    if os.path.exists(out):
        d = json.load(open(out, encoding="utf-8"))
        if "engine" in d:
            d["engine"]["dll_sha256_manifest"] = d["engine"].get("dll_sha256")
            d["engine"]["dll_sha256"] = sha256(DLL)
            d["engine"]["dll_file"] = DLL
        files = []
        for s in d.get("layout", {}).get("segments", []) or []:
            seg = next(x for x in D2.LAYOUTS[d["layout_key"]]["segs"] if x[1] == s["id"])
            fam = seg[3] if len(seg) > 3 else "m2"
            path = P.load_manifest()["blocks"][fam][seg[2]]["path"]
            m = block_meta(path)
            m.update({"seg_id": s["id"], "slot": s["slot"], "pos_lo": s["pos_lo"],
                      "pos_hi": s["pos_hi"], "cells_in_layout": s["cells"]})
            files.append(m)
        d["blocks"] = files
        d["question_from"] = "P.FULL['home']['q']"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        if "answers" in d:
            a = d["answers"][0]
            print("[H] %s cells_on_live=%d ask_pos=%d gap=%d" % (
                d["layout_key"], d["raw"]["cell_count"], P.CHAT,
                P.CHAT - d["raw"]["positions_max"] - 1))
            for b in files:
                print("    seg=%-11s slot=%d file=%s cells=%d bos=%s content=%d sha256=%s"
                      % (b["seg_id"], b["slot"], b["file"], b["cells"], b["has_bos"],
                         b["content_tokens"], b["sha256"]))
                print("    seg=%-11s pos=[%d,%d)" % (b["seg_id"], b["pos_lo"], b["pos_hi"]))
            print("[H] overlaps=%s dll_sha256=%s" % (d["raw"]["overlaps"],
                                                     d["engine"]["dll_sha256"]))
            print("[H] answer=%r ok_fact=%s sha256=%s" % (
                a["answer"], a["ok"],
                hashlib.sha256(a["answer"].encode("utf-8")).hexdigest()))
    return rc


if __name__ == "__main__":
    sys.exit(main())
