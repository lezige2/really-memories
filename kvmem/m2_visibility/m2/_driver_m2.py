# -*- coding: utf-8 -*-
"""M2 landing: three long-term memories live as KV, never as prompt text.

One engine, one session, three questions asked back-to-back (no reset between them):
  1 我住在哪？             -> answer must contain 广陵路
  2 项目什么时候上线？      -> 3月14 or 三月十四 (Arabic or Chinese numerals)
  3 我喝咖啡有什么习惯？    -> 美式

Frozen: 14B + DLL 9edbafa1, n_ctx 8192 / n_seq 8 / gpu 99 / kv q8_0 / fa on / n_predict 64,
home(21)@[4075,4096) project(18)@[4057,4075) habit(12)@[4045,4057), gap 0, 51 cells.

Usage:
  python -X utf8 kvmem/m2_visibility/m2/_driver_m2.py --run-json <path>
"""
import argparse, hashlib, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "runs_iso2"))
import m2_visibility_probe as P
import _driver2 as D2

MODEL14B = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
MANIFEST = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_m14b", "fixtures_14b.json")
DLL_WANT = "9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c"
EXPECT = [("home", "我住在哪？", ["广陵路"]),
          # frozen judge: Chinese and Arabic numerals are equivalent, any one of these hits.
          # "十四号"/"14号" are separate entries because "三月十四号" contains "三月十四" but
          # "十四号上线" alone would otherwise match nothing and fake a miss.
          ("project", "项目什么时候上线？", ["3月14", "三月十四", "3月14日", "十四号", "14号"]),
          ("habit", "我喝咖啡有什么习惯？", ["美式"])]

P.MODEL = MODEL14B
P.MANIFEST = MANIFEST
P.N_PREDICT = 64


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def norm(s):
    return re.sub(r"[\s\u3000]+", "", s or "")


def build_m2_layout(man):
    """Explicit positions -- this geometry is not uniform-spacing, so build_layout can't make it."""
    pos = {"home": (1, 4075), "project": (2, 4057), "habit": (3, 4045)}
    segs, order = [], []
    for sid in ("home", "project", "habit"):
        b = man["blocks"]["m2"][sid]
        slot, lo = pos[sid]
        n = b["cells"]
        if b["path"].replace("\\", "/").find("/m2_v1_14b/") < 0:
            raise SystemExit("STOP: block %s is not under m2_v1_14b: %s" % (sid, b["path"]))
        if os.path.getsize(b["path"]) != 1188 + 104464 * n:
            raise SystemExit("STOP: %s size != 1188+104464*%d" % (sid, n))
        if sha(b["path"]) != b["sha256"]:
            raise SystemExit("STOP: %s sha mismatch" % sid)
        segs.append({"id": sid, "block": "m2", "block_id": sid, "file": b["path"],
                     "file_sha256": b["sha256"], "cells": n, "slot": slot,
                     "pos_lo": lo, "pos_hi": lo + n, "add_order": len(order) + 1})
        order.append(sid)
    segs.sort(key=lambda s: s["pos_lo"])
    return {"key": "m2_three", "spacing": None, "segments": segs, "add_order": order,
            "start": min(s["pos_lo"] for s in segs),
            "cells_total": sum(s["cells"] for s in segs),
            "span_lo": min(s["pos_lo"] for s in segs),
            "span_hi": max(s["pos_hi"] for s in segs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-json", required=True)
    a = ap.parse_args()
    rj = a.run_json if os.path.isabs(a.run_json) else os.path.join(HERE, a.run_json)
    res = {"schema": "m2_run_v1", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    t0 = time.time()
    eng = None
    try:
        dll_path = os.path.join(ROOT, "tools", "kvshim_vk.dll")
        dll_sha = sha(dll_path)
        if dll_sha != DLL_WANT:
            raise SystemExit("STOP: tools DLL is %s, expected 9edbafa1" % dll_sha)
        man = P.load_manifest()
        nm = lambda p: os.path.normcase(os.path.abspath(p.replace("\\", "/")))
        if nm(man["engine"]["model"]) != nm(MODEL14B):
            raise SystemExit("STOP: manifest model %r" % man["engine"]["model"])
        layout = build_m2_layout(man)
        if layout["cells_total"] != 51 or layout["span_hi"] != 4096 or layout["span_lo"] != 4045:
            raise SystemExit("STOP: geometry %s" % {k: layout[k] for k in
                                                   ("cells_total", "span_lo", "span_hi")})

        res["engine"] = {"model": MODEL14B, "model_size": man["engine"]["model_size"],
                         "model_sha256": man["engine"].get("model_sha256"),
                         "dll_path": dll_path, "dll_sha256_measured": dll_sha,
                         "n_ctx": P.N_CTX, "n_seq": P.N_SEQ, "gpu": P.GPU, "kv": P.KV,
                         "n_predict": P.N_PREDICT, "threads": 8, "flash_attn": "on"}
        res["blocks"] = [{"id": s["id"], "file": s["file"], "file_sha256": s["file_sha256"],
                          "cells": s["cells"], "slot": s["slot"],
                          "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"]} for s in layout["segments"]]

        eng = P.open_engine()
        res["engine"]["loaded_path"] = getattr(eng.lib, "_name", None)
        res["engine"]["loaded_dll_sha256"] = sha(res["engine"]["loaded_path"])
        res["engine"]["bytes_per_token"] = eng.bytes_per_token()
        P.reset_all(eng)
        placed = P.load_and_place(eng, layout)
        P.share_layout(eng, layout, placed)
        res["placed"] = placed
        cnt, positions = P.cell_scan(eng, P.LIVE)
        res["geometry"] = {"cells_total": cnt, "positions_min": positions[0],
                           "positions_max": positions[-1],
                           "head_gap_cells": (P.CHAT - 1) - (layout["span_hi"] - 1),
                           "overlaps": P.overlaps(layout),
                           "raw_pos_max": P.raw_pos_max(eng, P.LIVE),
                           "n_tokens_before_first_question": D2.n_tokens(eng, P.LIVE)}
        g = res["geometry"]
        # raw_pos_max is the absolute position of the last cell: 4095 means the KV really sits
        # at 4045..4095. (n_tokens cannot prove this -- it counts a sequence's own tokens and
        # reads 0 while the cells are shared in from the slot blocks.)
        if not (cnt == 51 and positions[0] == 4045 and positions[-1] == 4095
                and g["raw_pos_max"] == 4095
                and g["head_gap_cells"] == 0 and not g["overlaps"]):
            raise SystemExit("STOP: geometry selfcheck %s" % g)
        # n_tokens counts only tokens this sequence owns; cells shared in from slot blocks are
        # not counted (the 24/64-token runs all logged ntok 0->N). The first question is decoded
        # at the absolute position right after the last block cell, i.e. P.CHAT.
        g["first_question_pos"] = P.CHAT
        g["n_tokens_semantics"] = ("own tokens only; shared block cells at 4045..4095 are not "
                                   "counted, so 0 before the first question is expected")

        res["control_gate"] = {
            "present": False,
            "why": "this driver runs no control gate (M2 does not depend on one)",
            "substitute_evidence": ("cells_total==51, positions 4045..4095, raw_pos_max==4095, "
                                    "and the LIVE sequence owns 0 tokens before the first "
                                    "question => the session holds KV cells only, no prompt "
                                    "text"),
            "note": "recorded deliberately, not forgotten"}

        # --- the sequential part: one session, three questions, no reset in between ---
        pos = 4096
        res["asks"] = []
        for sid, q, expect in EXPECT:
            before = D2.n_tokens(eng, P.LIVE)
            nb, ans = D2.ask_native(eng, P.LIVE, q, pos, P.N_PREDICT)
            after = D2.n_tokens(eng, P.LIVE)
            na = norm(ans)
            hit = [e for e in expect if norm(e) in na]
            res["asks"].append({"segment": sid, "question": q, "expected_any_of": expect,
                                "pos_asked": pos, "n_tokens_before": before,
                                "n_tokens_after": after,
                                "kvshim_ask_at_return_bytes": nb,
                                "answer": ans.strip(),
                                "answer_len": len(ans.strip()),
                                "hit": hit, "ok": bool(hit),
                                "hit_string": hit[0] if hit else None})
            print("[Q] %-8s pos=%-4d ntok %d->%d hit=%-8s hit_string=%s"
                  % (sid, pos, before, after, bool(hit), hit[0] if hit else None))
            print("    full: %r" % ans.strip())
            # absolute end of the sequence, independent of what n_tokens counts
            pos = pos + (after - before)
        res["all_hits"] = [r["ok"] for r in res["asks"]]
        res["m2_pass"] = all(res["all_hits"])
        res["answers_sha256"] = [hashlib.sha256(r["answer"].encode("utf-8")).hexdigest()
                                for r in res["asks"]]
    except SystemExit as exc:
        res["error"] = str(exc)
        print(res["error"])
    except Exception as exc:                                   # noqa: BLE001
        res["error"] = "%s: %s" % (type(exc).__name__, exc)
        print("ERROR %s" % exc)
    finally:
        if eng is not None:
            try:
                eng.close()
            except Exception:                                  # noqa: BLE001
                pass
        res["elapsed_s"] = round(time.time() - t0, 2)
        res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        os.makedirs(os.path.dirname(rj), exist_ok=True)
        json.dump(res, open(rj, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
        print("[RUN] wrote %s  m2_pass=%s" % (rj, res.get("m2_pass")))
    return 0 if res.get("m2_pass") else 1


if __name__ == "__main__":
    sys.exit(main())
