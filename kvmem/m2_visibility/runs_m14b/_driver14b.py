# -*- coding: utf-8 -*-
"""14B four-cell driver = thin wrapper around the untouched runs_iso2/_driver2.py.

Why a wrapper and not a copy: _driver2.py is the 7B archive. This file only sets
module globals before D2.main() runs, exactly as SPEC-14B-4CELL.md 3.2 prescribes.

Usage: python -X utf8 _driver14b.py --layout iso_dup4 --target home --run-json out/E_r1.json
"""
import hashlib, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
ISO2 = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_iso2")
sys.path.insert(0, ISO2)
import _driver2 as D2                                   # noqa: E402

P = D2.P
MODEL14B = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
MANIFEST14 = os.path.join(HERE, "fixtures_14b.json")
CTRL14 = os.path.join(HERE, "control_texts_14b.json")
BLOCKDIR = "D:/llama-mem/kvmem/m2_v1_14b"
DLL = "D:/llama-mem/tools/kvshim_vk.dll"
SENTINEL = "FIXTURES_14B_V1_SENTINEL_9edbafa1"

# _driver2.py:182-183 resolves the question and the expected fact as P.FULL[block_id].
# A block whose block_id is not a FULL key needs an alias; pp18 must be asked the project
# question and judged against the project fact ("3月14"), which is exactly what this copies.
# Runtime only -- tools/m2_visibility_probe.py is never edited.
P.FULL.setdefault("project_paraphrase18", dict(P.FULL["project"]))
P.FULL.setdefault("g18_bos_c18", dict(P.FULL["home"]))

P.MODEL = MODEL14B
P.MANIFEST = MANIFEST14
D2.CTRL_CACHE = CTRL14

# P2: E's exact geometry with slot4 = the 14B re-encode of the 7B X0 unrelated fact.
D2.LAYOUTS["iso_dup4_g18"] = {"spacing": 64, "segs": [
    (1, "home", "home"), (2, "project", "project"), (3, "habit", "habit"),
    (4, "g18", "g18_bos_c18", "variant")]}
# P1: one block alone at slot 1 (build_layout puts it flush against the question point,
# lo = CHAT - n, so head_gap_cells == 0).
D2.LAYOUTS["iso_project_only"] = {"spacing": 64, "segs": [(1, "project", "project")]}
D2.LAYOUTS["iso_habit_only"] = {"spacing": 64, "segs": [(1, "habit", "habit")]}
# segment id must be "project": the driver resolves the question/expected fact from P.FULL[target],
# and --target has to name a segment id. Only the block_id points at pp18.
D2.LAYOUTS["iso_pp18_only"] = {"spacing": 64,
                               "segs": [(1, "project", "project_paraphrase18", "variant")]}

D2.LAYOUTS["iso_x1_57copy"] = {"spacing": 64, "segs": [
    (1, "home", "home"), (2, "project", "project"), (4, "project2", "project")]}
D2.LAYOUTS["iso_fac_nb57"] = {"spacing": 64, "segs": [
    (1, "home", "home"), (2, "project", "project"),
    (4, "pp18", "project_paraphrase18", "variant")]}


FORBIDDEN = ["DeepSeek-R1-Distill-Qwen-7B", "m2_v1/home.kvmem", "m2_v1/project.kvmem",
             "m2_v1/habit.kvmem", "runs_iso2/control_texts.json", "runs_iso2\\control_texts.json"]


def forbidden_markers(txt):
    """Block-path / model markers of the 7B provenance, NOT the bare token '7B'
    (our own key names contain it, which made a literal check self-trigger)."""
    return [m for m in FORBIDDEN if m in txt]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def free_vram_mib():
    """What the Vulkan driver itself reports, not a guess."""
    exe = os.path.join(ROOT, "build-vulkan", "bin", "llama-cli.exe")
    try:
        out = subprocess.run([exe, "--list-devices"], capture_output=True, text=True,
                             timeout=120).stdout
    except Exception as e:                                  # noqa: BLE001
        return None, "probe failed: %s" % e
    m = re.search(r"\((\d+) MiB, (\d+) MiB free\)", out)
    if not m:
        return None, out.strip()
    return int(m.group(1)), int(m.group(2))


def assert_manifest():
    """Double assertion: the path we set is the path the driver actually reads."""
    ev = {}
    # 1. module globals as seen by the object that will run
    ev["P.MANIFEST"] = P.MANIFEST
    ev["D2.P is P"] = (D2.P is P)
    # 2. read it back through the SAME loader the driver uses
    man = P.load_manifest()
    ev["loaded_via_P.load_manifest"] = True
    ev["schema"] = man.get("schema")
    ev["sentinel"] = man.get("sentinel")
    if man.get("schema") != "fixtures_14b_v1":
        raise SystemExit("STOP manifest: schema=%r (expected fixtures_14b_v1)" % man.get("schema"))
    if man.get("sentinel") != SENTINEL:
        raise SystemExit("STOP manifest: sentinel=%r != %r" % (man.get("sentinel"), SENTINEL))
    if man["engine"]["model"] != MODEL14B:
        raise SystemExit("STOP manifest: engine.model=%r" % man["engine"]["model"])
    ev["engine.model"] = man["engine"]["model"]
    ev["engine.model_size"] = man["engine"]["model_size"]
    ev["engine.n_ctx/n_seq/gpu/kv"] = [man["engine"]["n_ctx"], man["engine"]["n_seq"],
                                       man["engine"]["gpu"], man["engine"]["kv"]]
    # 3. every block must live under m2_v1_14b and hash must match disk
    paths = []
    for fam in man["blocks"].values():
        for name, meta in fam.items():
            p = meta["path"].replace("\\", "/")
            paths.append(p)
            if not p.startswith(BLOCKDIR):
                raise SystemExit("STOP: block %s is not under %s (%s)" % (name, BLOCKDIR, p))
            if sha(p) != meta["sha256"]:
                raise SystemExit("STOP: block %s sha mismatch on disk" % name)
            if meta["cells"] not in (21, 18, 12):
                raise SystemExit("STOP: block %s cells=%r" % (name, meta["cells"]))
    ev["block_paths"] = paths
    # 4. control cache must not be the 7B one
    ev["D2.CTRL_CACHE"] = D2.CTRL_CACHE
    if os.path.abspath(D2.CTRL_CACHE) == os.path.abspath(
            os.path.join(ISO2, "control_texts.json")):
        raise SystemExit("STOP: control cache is the 7B file")
    # 5. no 7B artefact path anywhere in the manifest text
    raw = open(MANIFEST14, encoding="utf-8").read()
    bad = forbidden_markers(raw)
    if bad:
        raise SystemExit("STOP: fixtures_14b.json contains 7B markers %s" % bad)
    ev["forbidden_markers_in_manifest"] = []
    return ev, man


def main():
    # --control-start N: the control gate window is defined by the control text dict,
    # and D2.get_control derives target_n from layout["start"].  For the four cells that
    # is already 3886 (== min pos_lo), so the override is a no-op there and is asserted
    # to be one.  run0 (home only, start=4075) needs it, otherwise the 67-token control
    # prefix cannot fit in 21 cells.
    argv = list(sys.argv[1:])
    ctrl_start = None
    np_orig, np_new = P.N_PREDICT, None
    if "--n-predict" in argv:
        i = argv.index("--n-predict")
        np_new = int(argv[i + 1])
        P.N_PREDICT = np_new          # _driver2.py:188 reads P.N_PREDICT at call time
        del argv[i:i + 2]
        print("[GEN] n_predict = %d" % np_new)
    if "--control-start" in argv:
        i = argv.index("--control-start")
        ctrl_start = int(argv[i + 1])
        del argv[i:i + 2]
    sys.argv = [sys.argv[0]] + argv

    ev, man = assert_manifest()
    if ctrl_start is not None:
        layout_key = argv[argv.index("--layout") + 1]
        lay_start = D2.build_layout(layout_key, man)["start"]
        if lay_start == ctrl_start:
            print("[CTRL] override %d == layout start %d (no-op)" % (ctrl_start, lay_start))
        else:
            print("[CTRL] override %d != layout start %d -- control window forced to the "
                  "canonical 210-cell window; placement geometry is UNCHANGED"
                  % (ctrl_start, lay_start))
        orig_gc = D2.get_control

        def patched(eng, key, layout):
            saved = layout.get("start")
            layout["start"] = ctrl_start
            try:
                return orig_gc(eng, key, layout)
            finally:
                layout["start"] = saved

        D2.get_control = patched
        ev["control_start_override"] = ctrl_start
    vram_total, vram_free = free_vram_mib()
    print("[MANIFEST] path        = %s" % ev["P.MANIFEST"])
    print("[MANIFEST] schema      = %s" % ev["schema"])
    print("[MANIFEST] sentinel    = %s" % ev["sentinel"])
    print("[MANIFEST] model       = %s (%d B)" % (ev["engine.model"], ev["engine.model_size"]))
    print("[MANIFEST] n_ctx/n_seq/gpu/kv = %s" % (ev["engine.n_ctx/n_seq/gpu/kv"],))
    print("[MANIFEST] ctrl_cache  = %s" % ev["D2.CTRL_CACHE"])
    print("[VRAM] before run: total=%s MiB free=%s MiB" % (vram_total, vram_free))

    opened = {}
    orig_open = P.open_engine

    def recording_open():
        eng = orig_open()
        opened["loaded_path"] = getattr(eng.lib, "_name", "?")
        opened["loaded_dll_sha256"] = sha(opened["loaded_path"])
        opened["bytes_per_token"] = eng.bytes_per_token()
        opened["pool_bytes"] = eng.pool_bytes()
        return eng

    P.open_engine = recording_open
    t0 = time.time()
    try:
        rc = D2.main()
    finally:
        P.open_engine = orig_open

    run_json = argv[argv.index("--run-json") + 1]
    if not os.path.isabs(run_json):
        run_json = os.path.join(os.getcwd(), run_json)
    if os.path.exists(run_json):
        res = json.load(open(run_json, encoding="utf-8"))
        res["runner"] = {"n_predict": P.N_PREDICT,
                         "n_predict_changed": ("%d->%d" % (np_orig, np_new)
                                               if np_new is not None and np_new != np_orig
                                               else None),
                         "script": os.path.abspath(__file__),
                         "wrapper_over_7b_driver": os.path.join(ISO2, "_driver2.py"),
                         "wrapper_over_7b_driver_sha256": sha(os.path.join(ISO2, "_driver2.py")),
                         "manifest_assertion": ev,
                         "vram_before_mib": {"total": vram_total, "free": vram_free},
                         "wall_s": round(time.time() - t0, 2)}
        res["engine"].update({
            "model": ev["engine.model"], "model_size": ev["engine.model_size"],
            "loaded_path": opened.get("loaded_path"),
            "loaded_dll_sha256": opened.get("loaded_dll_sha256"),
            "bytes_per_token": opened.get("bytes_per_token"),
            "pool_bytes": opened.get("pool_bytes"),
        })
        # per-segment geometry with the block's own fingerprint
        if "layout" in res:
            for s in res["layout"]["segments"]:
                fam = s["block_id"]
                meta = None
                for f, d in man["blocks"].items():
                    if fam in d:
                        meta = d[fam]
                        break
                if meta:
                    s["file"] = meta["path"]
                    s["file_sha16"] = meta["sha256"][:16]
        res["device_evidence"] = {
            "driver_run_llama_log": "DISCARDED inside the DLL (kvshim.cpp:52-54 quiet_log, "
                                    "installed unconditionally by kvshim_init_log "
                                    "kvshim.cpp:630-633); llama_log_set is not exported, so "
                                    "no per-run 'dev = Vulkan0' line can exist.",
            "paired_v_log_same_constants": "runs_m14b/loadD_ngl99_c8192.log",
            "paired_v_log_finding": "llama_kv_cache: layer N: dev = Vulkan0 for N=0..47 "
                                    "(48/48); Vulkan0 KV buffer size = 816.00 MiB",
            "code_chain": "llama-model.cpp:2936 offload=cparams.offload_kqv(default true, "
                          "llama-context.cpp:4028) -> llama-kv-cache.cpp:216-223 "
                          "buft=dev_buffer_type(model.dev_layer(il)); gpu=99 >= 48 layers "
                          "=> every layer's KV on Vulkan0",
            "verdict": "成立 (single Vulkan device; derivation + paired log, not per-run log)",
        }
        json.dump(res, open(run_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2,
                  default=str)
        txt = open(run_json, encoding="utf-8").read()
        bad = forbidden_markers(txt)
        if bad:
            raise SystemExit("STOP: run json contains 7B markers %s" % bad)
        print("[CHK] run json: no 7B block/model markers; blocks all under m2_v1_14b")
    return rc


if __name__ == "__main__":
    sys.exit(main())
