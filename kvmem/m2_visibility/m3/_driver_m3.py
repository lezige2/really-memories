# -*- coding: utf-8 -*-
"""M3 -- block lifecycle: 50 attach/detach rounds in ONE engine load.

Acceptance (MD 4.3): attach/detach 50 rounds, pos_max / answer / cell usage stable with no
monotone rise; block files never written back; reset of a source seq while it is referenced
must fail or fail closed.

Order matters and is deliberate:
  1) 50 clean rounds (blocks loaded once from their pristine files, never reloaded)
  2) token-ledger quantification (non-destructive)
  3) pin test -- DESTRUCTIVE on purpose (reset a source seq that the dialogue references),
     then reload from file and prove the file is intact and the block can be restored.

  python -u -X utf8 kvmem/m2_visibility/m3/_driver_m3.py --run-json run_m3_50.json
"""
import argparse, hashlib, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "m2"))
import m2_visibility_probe as P                                    # noqa: E402
import _driver_m2 as M2                                           # noqa: E402

DLL_WANT = "9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c"
ROUNDS = 50
CHECKPOINT_ROUNDS = (1, 25, 50)
ADDR_Q, PROJ_Q, HABIT_Q = M2.EXPECT[0][1], M2.EXPECT[1][1], M2.EXPECT[2][1]
EXPECTS = {ADDR_Q: M2.EXPECT[0][2], PROJ_Q: M2.EXPECT[1][2], HABIT_Q: M2.EXPECT[2][2]}


_LOG = open(os.path.join(HERE, "run_m3_progress.log"), "a", encoding="utf-8", buffering=1)


def say(*a):
    """Progress goes to a file: stdout through a Windows pipe rejects flush=True (Errno 22)."""
    _LOG.write(" ".join(str(x) for x in a) + "\n")


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def free_vram():
    for exe in (r"C:/Windows/System32/nvidia-smi.exe",
                r"C:/Program Files/NVIDIA Corporation/NVSMI/nvidia-smi.exe"):
        if not os.path.exists(exe):
            continue
        try:
            out = subprocess.run([exe, "--query-gpu=memory.free,memory.total",
                                  "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=30).stdout.strip()
            f, t = out.splitlines()[0].split(",")
            return int(f), int(t)
        except Exception:                                            # noqa: BLE001
            continue
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-json", required=True)
    ap.add_argument("--rounds", type=int, default=ROUNDS)
    a = ap.parse_args()
    rj = a.run_json if os.path.isabs(a.run_json) else os.path.join(HERE, a.run_json)
    res = {"schema": "m3_lifecycle_v2", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "rounds_planned": a.rounds, "one_engine_load": True,
           "order": ["50_rounds", "ledger", "pin_test(destructive)+reload"]}
    t0 = time.time()
    eng = None
    try:
        dll = sha_file(os.path.join(ROOT, "tools", "kvshim_vk.dll"))
        if dll != DLL_WANT:
            raise SystemExit("DLL is %s, expected 9edbafa1" % dll)
        man = P.load_manifest()
        layout = M2.build_m2_layout(man)
        if layout["cells_total"] != 51:
            raise SystemExit("layout changed: %s" % layout["cells_total"])
        segs = {s["id"]: s for s in layout["segments"]}
        vfree, vtotal = free_vram()
        res["engine"] = {"model": M2.MODEL14B, "dll_sha256_measured": dll,
                         "n_ctx": P.N_CTX, "n_seq": P.N_SEQ, "gpu": P.GPU, "kv": P.KV,
                         "n_predict": P.N_PREDICT, "chat_anchor_pos": P.CHAT,
                         "vram_free_mib_before": vfree, "vram_total_mib": vtotal}
        eng = P.open_engine()
        P.reset_all(eng)
        placed = P.load_and_place(eng, layout)
        res["blocks"] = [{"id": p["id"], "slot": p["slot"], "cells": p["cells"],
                          "pos_lo": p["pos_lo"], "pos_hi": p["pos_hi"],
                          "file": p["file"], "file_sha256": p["file_sha256"],
                          "base": p["base"], "delta": p["delta"]} for p in placed]
        rng = [(p["pos_lo"], p["pos_hi"]) for p in placed]
        res["block_sha256_at_load"] = {p["id"]: p["file_sha256"] for p in placed}

        def attach():
            for p in placed:
                eng.share(p["slot"], P.LIVE, p["pos_lo"], p["pos_hi"])

        def detach():
            for p in placed:
                eng.drop(P.LIVE, p["pos_lo"], p["pos_hi"])

        def scan():
            n, positions = P.cell_scan(eng, P.LIVE)
            inblk = sum(1 for x in positions if any(lo <= x < hi for lo, hi in rng))
            return n, inblk, (positions[0] if positions else None), (positions[-1] if positions else None)

        def ask(q, pos):
            before = M2.D2.n_tokens(eng, P.LIVE)
            nb, ans = M2.D2.ask_native(eng, P.LIVE, q, pos, P.N_PREDICT)
            after = M2.D2.n_tokens(eng, P.LIVE)
            txt = ans.strip()
            return ({"question": q, "pos_asked": pos, "n_tokens_before": before,
                     "n_tokens_after": after, "answer": txt, "answer_len": len(txt),
                     "answer_sha256": hashlib.sha256(txt.encode("utf-8")).hexdigest()},
                    pos + max(after - before, 0))

        def restore_slot(p):
            seg = segs[p["id"]]
            eng.reset(p["slot"])
            n = eng.load_strict(p["slot"], seg["file"])
            base = eng.pos_max(p["slot"]) - n + 1
            moved = eng.repos_local(p["slot"], p["pos_lo"] - base)
            return {"reloaded_cells": n, "moved": moved,
                    "pos_max": eng.pos_max(p["slot"]),
                    "file_sha256_after": sha_file(seg["file"])}

        # ---------------- 1) the 50 rounds ------------------------------------
        say("[50 rounds] one engine load, blocks loaded once")
        rounds = []
        for r in range(1, a.rounds + 1):
            tr = time.time()
            eng.reset(P.LIVE)                      # fresh dialogue; blocks live in their own slots
            attach()
            n_att, blk_att, lo_att, hi_att = scan()
            nt = M2.D2.n_tokens(eng, P.LIVE)
            pmv = P.raw_pos_max(eng, P.LIVE)
            rec = {"round": r, "attach_cells": n_att, "attach_block_cells": blk_att,
                   "attach_positions": [lo_att, hi_att], "attach_raw_pos_max": pmv,
                   "n_tokens_owned_at_attach": nt, "asks": []}
            pos = P.CHAT
            qs = (ADDR_Q, PROJ_Q, HABIT_Q) if r in CHECKPOINT_ROUNDS else (ADDR_Q,)
            for q in qs:
                one, pos = ask(q, pos)
                one["expect_any_of"] = EXPECTS[q]
                one["hit"] = [e for e in one["expect_any_of"] if M2.norm(e) in M2.norm(one["answer"])]
                one["ok"] = bool(one["hit"])
                rec["asks"].append(one)
            rec["addr_ok"] = rec["asks"][0]["ok"]
            rec["answer_sha16_addr"] = rec["asks"][0]["answer_sha256"][:16]
            rec["n_tokens_after_asks"] = M2.D2.n_tokens(eng, P.LIVE)
            detach()
            n_after, blk_after, _, _ = scan()
            rec["after_detach_cells"] = n_after
            rec["after_detach_block_cells"] = blk_after
            rec["block_sha16"] = {p["id"]: sha_file(segs[p["id"]]["file"])[:16] for p in placed}
            rec["elapsed_s"] = round(time.time() - tr, 2)
            rounds.append(rec)
            say("  r%-2d blk_cells=%-3d pos_max=%-5s addr=%s after_detach_blk=%d %.1fs"
                % (r, blk_att, pmv, "OK" if rec["addr_ok"] else "MISS", blk_after, rec["elapsed_s"]))
        res["rounds"] = rounds

        # ---------------- 2) token ledger quantification -----------------------
        say("[ledger]")
        eng.reset(P.LIVE)
        attach()
        n_vis, blk_vis, lo_vis, hi_vis = scan()
        led = {"visible_cells": n_vis, "visible_block_cells": blk_vis,
               "visible_positions": [lo_vis, hi_vis],
               "n_tokens_owned": M2.D2.n_tokens(eng, P.LIVE),
               "pos_max_reported_by_shim": eng.pos_max(P.LIVE),
               "raw_pos_max": P.raw_pos_max(eng, P.LIVE)}
        led["mismatch"] = ("%d visible cells (all shared) but n_tokens=%d: seq_cp is a pure "
                           "refcount and adds nothing to the target's token accounting"
                           % (n_vis, led["n_tokens_owned"]))
        # (a) a caller that derives the write position from n_tokens writes the question at 0
        one, _ = ask(ADDR_Q, led["n_tokens_owned"])
        led["naive_pos_from_n_tokens"] = {"pos_used": led["n_tokens_owned"],
                                          "answer": one["answer"][:220],
                                          "pos_max_after": P.raw_pos_max(eng, P.LIVE),
                                          "addr_hit": any(M2.norm(e) in M2.norm(one["answer"])
                                                          for e in M2.EXPECT[0][2])}
        detach()
        # (b) save() of an attached seq serialises own tokens only
        eng.reset(P.LIVE)
        attach()
        tmp = os.path.join(HERE, "_ledger_probe.state")
        saved, err = None, None
        try:
            saved = eng.save(P.LIVE, tmp)
        except Exception as exc:                                     # noqa: BLE001
            err = "%s: %s" % (type(exc).__name__, exc)
        led["save_while_attached"] = {"bytes_returned": saved, "error": err,
                                      "own_tokens": M2.D2.n_tokens(eng, P.LIVE),
                                      "visible_cells": scan()[0],
                                      "file_bytes": os.path.getsize(tmp) if os.path.exists(tmp) else None}
        if os.path.exists(tmp):
            os.remove(tmp)
        detach()
        res["ledger"] = led
        say("   visible=%d owned=%d | naive pos=%d hit=%s | save bytes=%s"
            % (n_vis, led["n_tokens_owned"], led["naive_pos_from_n_tokens"]["pos_used"],
               led["naive_pos_from_n_tokens"]["addr_hit"], saved))

        # ---------------- 3) pin test (destructive, last) ----------------------
        say("[pin] reset a source seq WHILE the dialogue references it")
        eng.reset(P.LIVE)
        attach()
        n_before, blk_before, _, _ = scan()
        src = placed[0]
        seg0 = segs[src["id"]]
        sha_before = sha_file(seg0["file"])
        pin = {"source_block": src["id"], "source_slot": src["slot"],
               "live_cells_before": n_before, "live_block_cells_before": blk_before,
               "source_cells_before": P.cell_scan(eng, src["slot"])[0],
               "source_pos_max_before": eng.pos_max(src["slot"]),
               "file_sha256_before": sha_before}
        try:
            eng.reset(src["slot"])
            pin["reset_call"] = "returned normally, no exception, no error code"
            pin["reset_refused"] = False
        except Exception as exc:                                     # noqa: BLE001
            pin["reset_call"] = "raised %s: %s" % (type(exc).__name__, exc)
            pin["reset_refused"] = True
        pin["source_cells_after"] = P.cell_scan(eng, src["slot"])[0]
        pin["source_pos_max_after"] = eng.pos_max(src["slot"])
        n_after, blk_after, _, _ = scan()
        pin["live_cells_after"] = n_after
        pin["live_block_cells_after"] = blk_after
        one, _ = ask(ADDR_Q, P.CHAT)
        pin["addr_answer_after_reset"] = one["answer"][:220]
        pin["addr_hit_after_reset"] = any(M2.norm(e) in M2.norm(one["answer"])
                                          for e in M2.EXPECT[0][2])
        pin["file_sha256_after"] = sha_file(seg0["file"])
        pin["file_unchanged_by_reset"] = pin["file_sha256_after"] == sha_before
        detach()
        # recovery: the file is the source of truth
        pin["restore"] = restore_slot(src)
        pin["restore"]["file_sha256_matches"] = pin["restore"]["file_sha256_after"] == sha_before
        eng.reset(P.LIVE)
        attach()
        pin["recells_after_restore"] = scan()[0]
        one, _ = ask(ADDR_Q, P.CHAT)
        pin["addr_hit_after_restore"] = any(M2.norm(e) in M2.norm(one["answer"])
                                            for e in M2.EXPECT[0][2])
        pin["addr_answer_after_restore"] = one["answer"][:220]
        detach()
        res["pin_test"] = pin
        say("   reset -> %s | source cells %s -> %s | live block cells %d -> %d | hit=%s"
            % (pin["reset_call"], pin["source_cells_before"], pin["source_cells_after"],
               blk_before, blk_after, pin["addr_hit_after_reset"]))
        say("   file unchanged=%s | restored cells=%s | hit after restore=%s"
            % (pin["file_unchanged_by_reset"], pin["recells_after_restore"],
               pin["addr_hit_after_restore"]))

        # ---------------- acceptance ------------------------------------------
        cells = [x["attach_block_cells"] for x in rounds]
        pms = [x["attach_raw_pos_max"] for x in rounds]
        after = [x["after_detach_block_cells"] for x in rounds]
        shas = {p["id"]: {x["block_sha16"][p["id"]] for x in rounds} for p in placed}
        cp = {x["round"]: x for x in rounds if x["round"] in CHECKPOINT_ROUNDS}
        addrs = [cp[r]["asks"][0]["answer"] for r in CHECKPOINT_ROUNDS]
        res["acceptance"] = {
            "1_cells_stable": {"series_first_last": [cells[0], cells[-1]],
                               "distinct": sorted(set(cells)),
                               "stable_no_rise": len(set(cells)) == 1 and cells[0] == 51},
            "2_pos_max_stable": {"series_first_last": [pms[0], pms[-1]],
                                 "distinct": sorted(set(pms)),
                                 "stable_no_rise": len(set(pms)) == 1,
                                 "monotone_rise": all(b > a for a, b in zip(pms, pms[1:])),
                                 "expected": 4095},
            "3_answer_stable": {"r1_sha16": cp[1]["asks"][0]["answer_sha256"][:16],
                                "r25_sha16": cp[25]["asks"][0]["answer_sha256"][:16],
                                "r50_sha16": cp[50]["asks"][0]["answer_sha256"][:16],
                                "identical_1_25_50": len(set(addrs)) == 1,
                                "r50_three_questions_all_hit": all(x["ok"] for x in cp[50]["asks"]),
                                "addr_hits_over_50_rounds": sum(1 for x in rounds if x["addr_ok"])},
            "4_block_files_unchanged": {k: (len(v) == 1) for k, v in shas.items()},
            "4_block_sha16_seen": {k: sorted(v) for k, v in shas.items()},
            "5_pin": {"reset_refused": pin["reset_refused"],
                      "live_block_cells_before_after": [blk_before, blk_after],
                      "addr_hit_after_reset": pin["addr_hit_after_reset"],
                      "file_intact": pin["file_unchanged_by_reset"],
                      "recovers_by_reload": pin["recells_after_restore"] == 51
                                            and pin["addr_hit_after_restore"]},
            "6_ledger": led["mismatch"],
        }
        res["acceptance"]["all_criteria_evidence_present"] = all([
            res["acceptance"]["1_cells_stable"]["stable_no_rise"],
            res["acceptance"]["2_pos_max_stable"]["stable_no_rise"],
            res["acceptance"]["3_answer_stable"]["r50_three_questions_all_hit"],
            res["acceptance"]["4_block_files_unchanged"] == {p["id"]: True for p in placed},
            "5_pin" in res["acceptance"], "6_ledger" in res["acceptance"]])
    except SystemExit as exc:
        res["error"] = str(exc)
        say("STOP: %s" % exc)
    except Exception as exc:                                         # noqa: BLE001
        import traceback
        res["error"] = "%s: %s" % (type(exc).__name__, exc)
        res["traceback"] = traceback.format_exc()[-1500:]
        say("ERROR %s" % exc)
        traceback.print_exc()
    finally:
        if eng is not None:
            try:
                eng.close()
            except Exception:                                        # noqa: BLE001
                pass
        res["elapsed_s"] = round(time.time() - t0, 2)
        res["vram_free_mib_after"] = free_vram()[0]
        res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        os.makedirs(os.path.dirname(rj), exist_ok=True)
        json.dump(res, open(rj, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
        say("[RUN] wrote %s in %.1fs" % (rj, res["elapsed_s"]))
    return 0 if res.get("error") is None else 1


if __name__ == "__main__":
    sys.exit(main())
