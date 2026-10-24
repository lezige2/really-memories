# -*- coding: utf-8 -*-
"""7B @ n_predict=64 four-cell driver (PREREG-NEXT2-7B64.md).

Wrapper around the untouched runs_iso2/_driver2.py. Only module globals are set:
7B model, 7B manifest, a private control-text cache, and the four frozen layouts.
The DLL must already be c7ea09bb when this runs; the run json records the measured sha.
"""
import hashlib, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
ISO2 = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_iso2")
sys.path.insert(0, ISO2)
import _driver2 as D2                                   # noqa: E402

P = D2.P
MODEL7B = "D:/models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
MANIFEST7 = os.path.join(ROOT, "kvmem", "m2_visibility", "fixtures.json")
CTRL7 = os.path.join(HERE, "control_texts.json")
DLL = os.path.join(ROOT, "tools", "kvshim_vk.dll")
DLL_WANT = "c7ea09bbc7cb616f4c649d76d8c4839bb7c9934861a70d7999959f44d793e3b8"
HDR7, CELL7 = 708, 30480

P.MODEL = MODEL7B
P.MANIFEST = MANIFEST7
D2.CTRL_CACHE = CTRL7

# Geometry frozen by PREREG 2: spacing 64, slots 1..4, n from the block itself.
LAYOUTS = {
    "iso_dup4":      [(1, "home", "home"), (2, "project", "project"), (3, "habit", "habit"),
                      (4, "project2", "project")],
    "iso_fac_pp18":  [(1, "home", "home"), (2, "project", "project"), (3, "habit", "habit"),
                      (4, "pp18", "project_paraphrase18", "variant")],
    "iso_x1_57copy": [(1, "home", "home"), (2, "project", "project"),
                      (4, "project2", "project")],
    "iso_fac_nb57":  [(1, "home", "home"), (2, "project", "project"),
                      (4, "pp18", "project_paraphrase18", "variant")],
}
for k, v in LAYOUTS.items():
    D2.LAYOUTS[k] = {"spacing": 64, "segs": v}

EXPECT_POS = {4075: 21, 4014: 18, 3956: 12, 3886: 18}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def free_vram_mib():
    exe = os.path.join(ROOT, "build-vulkan", "bin", "llama-cli.exe")
    try:
        out = subprocess.run([exe, "--list-devices"], capture_output=True, text=True,
                             timeout=120).stdout
    except Exception as e:                                   # noqa: BLE001
        return None, "probe failed: %s" % e
    m = re.search(r"\((\d+) MiB, (\d+) MiB free\)", out)
    return (int(m.group(1)), int(m.group(2))) if m else (None, out.strip())


def check():
    ev = {"P.MANIFEST": P.MANIFEST, "D2.P is P": D2.P is P,
          "D2.CTRL_CACHE": D2.CTRL_CACHE, "dll_sha256_now": sha(DLL),
          "dll_sha256_want": DLL_WANT}
    if ev["dll_sha256_now"] != DLL_WANT:
        raise SystemExit("STOP: tools DLL is %s, expected c7ea09bb" % ev["dll_sha256_now"])
    if os.path.abspath(P.MANIFEST) != os.path.abspath(MANIFEST7):
        raise SystemExit("STOP manifest path")
    man = P.load_manifest()
    ev["schema"] = man.get("schema")
    ev["engine.model"] = man["engine"]["model"]
    # the manifest records the path with backslashes; compare normalised, not literally
    nm = lambda p: os.path.normcase(os.path.abspath(p.replace("\\", "/")))
    if nm(man["engine"]["model"]) != nm(MODEL7B):
        raise SystemExit("STOP: manifest model is %r" % man["engine"]["model"])
    if man.get("schema") != "m2_visibility_fixtures_v1" and "fixtures" not in str(man.get("schema")):
        ev["schema_note"] = "not asserted beyond model/cells (7B manifest predates this work)"
    for fam in man["blocks"].values():
        for name, meta in fam.items():
            p = meta["path"].replace("\\", "/")
            if not (p.startswith("D:/llama-mem/kvmem/m2_v1/")
                    or p.startswith("D:/llama-mem/kvmem/m2_visibility/blocks/")):
                raise SystemExit("STOP: block %s outside the 7B block dirs (%s)" % (name, p))
            n, sz = meta["cells"], os.path.getsize(p)
            # size formula is asserted only for the four blocks this batch actually places;
            # the manifest also carries variant blocks from other work.
            if name in ("home", "project", "habit", "project_paraphrase18"):
                if sz != HDR7 + CELL7 * n:
                    raise SystemExit("STOP: block %s size %d != 708+30480*%d" % (name, sz, n))
                ev.setdefault("blocks", {})[os.path.basename(p)] = {
                    "cells": n, "size": sz}
            if sha(p) != meta["sha256"]:
                raise SystemExit("STOP: block %s sha mismatch on disk" % name)
    if "fixtures_14b" in json.dumps(man):
        raise SystemExit("STOP: manifest points at the 14B fixtures")
    return ev, man


def main():
    argv = list(sys.argv[1:])
    np_orig, np_new = P.N_PREDICT, None
    if "--n-predict" in argv:
        i = argv.index("--n-predict")
        np_new = int(argv[i + 1])
        P.N_PREDICT = np_new
        del argv[i:i + 2]
        print("[GEN] n_predict = %d (was %d)" % (np_new, np_orig))
    sys.argv = [sys.argv[0]] + argv

    ev, man = check()
    vtot, vfree = free_vram_mib()
    print("[MANIFEST] path     = %s" % ev["P.MANIFEST"])
    print("[MANIFEST] model    = %s" % ev["engine.model"])
    print("[MANIFEST] ctrl     = %s" % ev["D2.CTRL_CACHE"])
    print("[MANIFEST] blocks   = %s" % ev.get("blocks"))
    print("[DLL] now sha256 = %s" % ev["dll_sha256_now"])
    print("[VRAM] before: total=%s free=%s MiB" % (vtot, vfree))

    opened = {}
    orig = P.open_engine

    def rec():
        eng = orig()
        opened["loaded_path"] = getattr(eng.lib, "_name", "?")
        opened["loaded_dll_sha256"] = sha(opened["loaded_path"])
        opened["bytes_per_token"] = eng.bytes_per_token()
        opened["pool_bytes"] = eng.pool_bytes()
        return eng

    P.open_engine = rec
    t0 = time.time()
    try:
        rc = D2.main()
    finally:
        P.open_engine = orig

    rj = argv[argv.index("--run-json") + 1]
    if not os.path.isabs(rj):
        rj = os.path.join(os.getcwd(), rj)
    if os.path.exists(rj):
        res = json.load(open(rj, encoding="utf-8"))
        res["runner"] = {"n_predict": P.N_PREDICT,
                         "n_predict_changed": ("%d->%d" % (np_orig, np_new)
                                               if np_new not in (None, np_orig) else None),
                         "script": os.path.abspath(__file__),
                         "wrapper_over_7b_driver_sha256": sha(os.path.join(ISO2, "_driver2.py")),
                         "manifest_assertion": ev,
                         "vram_before_mib": {"total": vtot, "free": vfree},
                         "wall_s": round(time.time() - t0, 2),
                         "dll_swapped_to": "c7ea09bb (from runs_m14b/dll_archive), "
                                           "restored to 9edbafa1 after the batch"}
        res["engine"].update({"model": ev["engine.model"],
                              "loaded_path": opened.get("loaded_path"),
                              "loaded_dll_sha256": opened.get("loaded_dll_sha256"),
                              "bytes_per_token": opened.get("bytes_per_token"),
                              "pool_bytes": opened.get("pool_bytes")})
        r = res.get("raw", {})
        geo = {"cells_total": r.get("cell_count"),
               "positions_min": r.get("positions_min"),
               "positions_max": r.get("positions_max"),
               "overlaps": r.get("overlaps"),
               "head_gap_cells": res.get("layout", {}).get("head_gap_cells"),
               "seg_positions": [[s["slot"], s["pos_lo"], s["pos_hi"], s["cells"]]
                                 for s in res.get("layout", {}).get("segments", [])]}
        res["geometry_selfcheck"] = geo
        json.dump(res, open(rj, "w", encoding="utf-8"), ensure_ascii=False, indent=2,
                  default=str)
        ok_geo = (geo["head_gap_cells"] == 0 and not geo["overlaps"]
                  and geo["positions_max"] == 4095
                  and all(EXPECT_POS.get(s[1]) == s[3] for s in geo["seg_positions"]))
        print("[GEO] %s cells=%s pos=%s..%s gap=%s overlaps=%s -> %s"
              % (res.get("layout_key"), geo["cells_total"], geo["positions_min"],
                 geo["positions_max"], geo["head_gap_cells"], geo["overlaps"],
                 "OK" if ok_geo else "FAIL"))
        if not ok_geo:
            raise SystemExit("STOP: geometry selfcheck failed: %s" % geo)
    return rc


if __name__ == "__main__":
    sys.exit(main())
