# -*- coding: utf-8 -*-
"""Mask-trace run: one engine PROCESS per run.

The DLL links a static CRT and snapshots the environment at process start, so an
in-process os.environ write is invisible to it.  This script therefore works in two
modes:

  launcher (default) -- builds the child environment (including the REAL layout key
                        taken from --layout, never a hand-typed shell label), spawns
                        this same file as a child process, and returns the child's
                        exit code.
  worker (--worker)  -- the old in-process body: opens the engine, places the layout,
                        asks, writes the run json.  It records the environment it
                        actually sees (child_env), never one the parent intended.
"""
import argparse, hashlib, json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ISO2 = os.path.join(os.path.dirname(HERE), "runs_iso2")
sys.path.insert(0, ISO2)
import _driver2 as D2                      # noqa: E402
P = D2.P

MASK_KEYS = ["LLAMA_KV_MASK_DEBUG", "LLAMA_KV_MASK_SEQ", "LLAMA_KV_MASK_LAYOUT",
             "LLAMA_KV_MASK_Q", "LLAMA_KV_MASK_WINDOWS", "LLAMA_KV_MASK_NODEDUP"]
TRACE_GATE = "llama-kv-cache.cpp:2031 i == ubatch->n_tokens - 1"
CPP = os.path.join(ROOT, "llama.cpp", "src", "llama-kv-cache.cpp")


def sha8(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def add_args(ap):
    ap.add_argument("--layout", required=True, choices=sorted(D2.LAYOUTS))
    ap.add_argument("--target", required=True)
    ap.add_argument("--run-json", required=True)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--mask-seq", type=int, default=None)
    ap.add_argument("--worker", action="store_true")
    ap.add_argument("--env-source", default="inherited")


def windows_for(layout):
    return ",".join("%s:%d:%d" % (s["id"], s["pos_lo"], s["pos_hi"] - 1)
                    for s in layout["segments"])


def launcher(argv):
    ap = argparse.ArgumentParser()
    add_args(ap)
    a = ap.parse_args(argv)
    manifest = P.load_manifest()
    layout = D2.build_layout(a.layout, manifest)
    seg = next(s for s in layout["segments"] if s["id"] == a.target)
    qs = sha8(P.FULL[seg["block_id"]]["q"])
    env = dict(os.environ)
    overridden = {}
    if a.debug:
        env["LLAMA_KV_MASK_DEBUG"] = "1"
        overridden["LLAMA_KV_MASK_DEBUG"] = "1"
    env["LLAMA_KV_MASK_LAYOUT"] = a.layout          # the REAL key, not a shell label
    overridden["LLAMA_KV_MASK_LAYOUT"] = a.layout
    env["LLAMA_KV_MASK_WINDOWS"] = windows_for(layout)
    overridden["LLAMA_KV_MASK_WINDOWS"] = env["LLAMA_KV_MASK_WINDOWS"]
    env["LLAMA_KV_MASK_Q"] = qs
    overridden["LLAMA_KV_MASK_Q"] = qs
    if a.mask_seq is not None:
        env["LLAMA_KV_MASK_SEQ"] = str(a.mask_seq)
        overridden["LLAMA_KV_MASK_SEQ"] = str(a.mask_seq)
    cmd = [sys.executable, "-X", "utf8", os.path.abspath(__file__), "--worker",
           "--layout", a.layout, "--target", a.target, "--run-json", a.run_json,
           "--env-source", "exported_by_driver"]
    if a.debug:
        cmd.append("--debug")
    if a.mask_seq is not None:
        cmd += ["--mask-seq", str(a.mask_seq)]
    print("[launcher] child env overrides: %s" % json.dumps(overridden, ensure_ascii=False))
    # The engine writes [MASKDBG*] to the child's stderr. We tee that stream and count it
    # HERE, on the live pipe -- an independent path from reading the log file afterwards.
    # Without it, "log vs json.trace_classes" would compare a file against a count of that
    # same file, i.e. an unfalsifiable check.
    counts = {"SUM": 0, "SUM2": 0, "blk": 0, "OK": 0}
    rx = {"SUM": re.compile(r"^\[MASKDBG-SUM\] "), "SUM2": re.compile(r"^\[MASKDBG-SUM2\] "),
          "blk": re.compile(r"^\[MASKDBG\] "), "OK": re.compile(r"MASKDBG-OK")}
    cp = subprocess.Popen(cmd, env=env, stderr=subprocess.PIPE)
    for raw in cp.stderr:
        sys.stderr.buffer.write(raw)
        sys.stderr.buffer.flush()
        try:
            text = raw.decode("utf-8", "replace")
        except Exception:                                      # noqa: BLE001
            continue
        for name, pat in rx.items():
            if pat.search(text):
                counts[name] += 1
                break
    cp.wait()
    try:
        d = json.load(open(a.run_json, encoding="utf-8"))
        # name it worker_counts per T-006 sign-off; the SOURCE is the driver's tee of the
        # child stderr pipe, because SUM/SUM2/blk are printed by the ENGINE, not by this script.
        d["worker_counts"] = counts
        d["worker_counts_source"] = ("launcher tee of the child stderr pipe "
                                     "(the engine emits SUM/SUM2/blk; the worker script emits only OK)")
        with open(a.run_json, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
    except Exception as exc:                                   # noqa: BLE001
        print("[launcher] could not record worker_counts: %s" % exc)
    return cp.returncode


def worker(argv):
    ap = argparse.ArgumentParser()
    add_args(ap)
    a = ap.parse_args(argv)
    manifest = P.load_manifest()
    layout = D2.build_layout(a.layout, manifest)
    seg = next(s for s in layout["segments"] if s["id"] == a.target)
    q = P.FULL[seg["block_id"]]["q"]
    fact = P.FULL[seg["block_id"]]["fact"]
    qs = sha8(q)
    child_env = {k: os.environ.get(k) for k in MASK_KEYS}
    t0 = time.time()
    res = {"schema": "mask_run_v3", "experiment": a.layout, "target": a.target,
           "debug": bool(a.debug), "q_sha": qs, "question": q,
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "cmdline": sys.argv, "child_env": child_env, "env_source": a.env_source,
           "asks_expected": 1,
           # one ask = 1 prompt ubatch + N_PREDICT decode ubatches; the "one p1 row per
           # ubatch" part is an ENGINE gate, so it is recorded as a named premise below.
           "decode_batches_expected": 1 + P.N_PREDICT,
           "trace_gate": TRACE_GATE,
           "trace_gate_cpp_sha256": (hashlib.sha256(open(CPP, "rb").read()).hexdigest()
                                     if os.path.exists(CPP) else None),
           "dll_sha256": hashlib.sha256(open(manifest["engine"]["dll"], "rb").read()).hexdigest()}
    eng = P.open_engine()
    try:
        for bid, meta in manifest["blocks"]["m2"].items():
            if P.sha256_file(meta["path"]) != meta["sha256"]:
                raise RuntimeError("pristine block hash changed: %s" % meta["path"])
        P.reset_all(eng)
        ctexts = D2.get_control(eng, a.layout, layout)
        okc, ctrl = P.run_control(eng, layout, a.layout, ctexts, P.FULL, D2.CONTROL_ORDER)
        res["control_ok"] = bool(okc)
        if not okc:
            res["failure"] = "CONTROL GATE FAILED"
            P._write_json(a.run_json, res)
            return 3
        P.reset_all(eng)
        placed = P.load_and_place(eng, layout)
        P.share_layout(eng, layout, placed)
        res["layout"] = {"key": a.layout, "spacing": 64,
                         "cells_total": layout["cells_total"],
                         "span_lo": layout["span_lo"], "span_hi": layout["span_hi"],
                         "head_gap_cells": (P.CHAT - 1) - (layout["span_hi"] - 1),
                         "windows": {s["id"]: [s["pos_lo"], s["pos_hi"] - 1] for s in layout["segments"]},
                         "segments": [{"id": s["id"], "block_id": s["block_id"], "slot": s["slot"],
                                       "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"],
                                       "cells": s["cells"]} for s in layout["segments"]]}
        # T-007: make the 3a anchors self-describing, so a third party holding ONLY this
        # json can recompute every expectation without reading this script.
        n_seg = len(res["layout"]["segments"])
        n_pred = P.N_PREDICT
        res["anchors"] = {
            "segments": res["layout"]["segments"],
            "n_segments": n_seg,
            "n_segments_source": ("len(layout.segments) in this json; segment ids/slots "
                                  "come from _driver2.LAYOUTS[key] and the probe block manifest"),
            "ask_n_predict": n_pred,
            "ask_n_predict_source": "probe constant, tools/m2_visibility_probe.py:103",
            "decode_batches_expected_expr": "1 + ask.n_predict",
            "decode_batches_expected_source": "1 prompt ubatch + ask.n_predict decode ubatches",
            "SUM": {"expect": 1 + n_pred, "expr": "decode_batches_expected",
                    "source": "engine prints one [MASKDBG-SUM] per ubatch, gate: " + TRACE_GATE},
            "SUM2": {"expect": 1 + n_pred, "expr": "SUM",
                     "source": "engine prints one [MASKDBG-SUM2] per traced p1 row (same gate)"},
            "blk": {"expect": n_seg * (1 + n_pred), "expr": "n_segments * SUM",
                    "source": "engine prints one [MASKDBG] per (p1 row, segment)"},
            "OK": {"expect": n_seg, "expr": "n_segments",
                   "source": "this driver prints one [MASKDBG-OK] per segment after the ask"},
        }
        eng.reset(P.LIVE)
        P.share_layout(eng, layout, placed)
        raw = P.raw_pos_max(eng, P.LIVE)
        cnt, positions = P.cell_scan(eng, P.LIVE)
        res["cell_layer"] = {"raw_pos_max": raw, "cell_count": cnt,
                             "positions_min": positions[0] if positions else None,
                             "positions_max": positions[-1] if positions else None,
                             "coverage": P.coverage(positions, layout),
                             "overlaps": P.overlaps(layout)}
        n_bytes, ans = D2.ask_native(eng, P.LIVE, q, P.CHAT, P.N_PREDICT)
        asha = hashlib.sha256(ans.encode("utf-8")).hexdigest()
        res["ask"] = {"kvshim_ask_at_return_bytes": n_bytes, "answer": ans.strip(),
                      "answer_sha256": asha, "expected": fact,
                      "n_predict": P.N_PREDICT,
                      "n_predict_source": "probe constant (tools/m2_visibility_probe.py:103)",
                      "ok": bool(P.fact_ok(fact, ans))}
        if a.debug:
            sys.stdout.flush()
            for s in layout["segments"]:
                sys.stderr.write("[MASKDBG-OK] layout=%s q=%s blk=%s cells=%d ok=%d ans_sha=%s\n"
                                 % (a.layout, qs, s["id"], s["cells"],
                                    1 if res["ask"]["ok"] else 0, asha[:8]))
            sys.stderr.flush()
        res["elapsed_s"] = round(time.time() - t0, 2)
        P._write_json(a.run_json, res)
        print("%s/%s ok=%s bytes=%d ans_sha=%s" % (a.layout, a.target, res["ask"]["ok"],
              n_bytes, asha[:8]))
        return 0
    except Exception as exc:                                   # noqa: BLE001
        res["error"] = "%s: %s" % (type(exc).__name__, exc)
        P._write_json(a.run_json, res)
        print("ERROR %s" % exc)
        return 4
    finally:
        try:
            eng.close()
        except Exception:
            pass


def main():
    if "--worker" in sys.argv[1:]:
        return worker(sys.argv[1:])
    return launcher(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
