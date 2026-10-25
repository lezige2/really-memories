# -*- coding: utf-8 -*-
"""真机插入（修正版）：插入前后各问一次，**问题都写在对话末尾**（pos = pos_max+1）。

上一版的错法：第二次也写在 chat 起点（4096/4108），那是**覆写已有对话**的位置，
engine 直接返回 -1 —— 与插入无关。定位实验 D0（只放置、连问两次）同样 -1，已证明这一点。
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "engine"))
import _driver2 as D2                      # noqa: E402
P = D2.P
P.MODEL = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
P.MANIFEST = os.path.join(HERE, "fixtures_probe14b.json")
D2.CTRL_CACHE = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_m14b", "control_texts_14b.json")
OUT = os.path.join(HERE, "out", "INSERT-REAL2.json")


def ask_end(eng, q, tag, n_predict=64):
    pos = P.raw_pos_max(eng, P.LIVE) + 1             # 必须用 raw：eng.pos_max(LIVE) 不含 share 进来的 cell（返回 -1）
    t = time.time()
    n, a = D2.ask_native(eng, P.LIVE, q, pos, n_predict)
    return {"tag": tag, "ask_pos": pos, "return_bytes": n, "len": len(a),
            "answer": a.strip(), "elapsed_ms": round((time.time() - t) * 1000, 1)}


def main():
    manifest = P.load_manifest()
    layout = D2.build_layout("iso_no_car", manifest)
    segs = layout["segments"]
    seg = next(s for s in segs if s["id"] == "project")
    q, fact = P.FULL[seg["block_id"]]["q"], P.FULL[seg["block_id"]]["fact"]
    new_seg = next(s for s in segs if s["id"] == "habit")
    N = int(new_seg["cells"])
    res = {"schema": "insert_real_v2", "layout": "iso_no_car", "target": "project",
           "n_new_cells": N, "inserted_block": {"file": new_seg["file"],
           "note": "复用 habit 块（12 cells）作为新块；位置学与块内容无关"}, "steps": []}
    eng = P.open_engine()
    try:
        P.reset_all(eng)
        t = time.time(); P.load_and_place(eng, layout); res["steps"].append({"step": "load_and_place", "ok": True, "elapsed_ms": round((time.time()-t)*1000,1)})
        eng.reset(P.LIVE)
        P.share_layout(eng, layout, [{"id": s["id"], "slot": s["slot"], "pos_lo": s["pos_lo"],
                                      "pos_hi": s["pos_hi"]} for s in segs])
        pos_before = {s["id"]: eng.pos_max(s["slot"]) for s in segs}
        res["answers_before"] = ask_end(eng, q, "before_insert")
        res["answers_before"]["ok"] = bool(P.fact_ok(fact, res["answers_before"]["answer"]))
        chat_hi = P.raw_pos_max(eng, P.LIVE) + 1
        res["chat"] = {"first_turn": [P.CHAT, chat_hi], "ntok": D2.n_tokens(eng, P.LIVE)}

        t_all = time.time()
        for s in segs:
            eng.drop(P.LIVE, s["pos_lo"], s["pos_hi"])
        t1 = time.time()
        moved = eng.repos_local(P.LIVE, +N, P.CHAT, chat_hi)
        t2 = time.time()
        eng.reset(7)
        n = eng.load_strict(7, new_seg["file"])
        eng.repos_local(7, P.CHAT - (eng.pos_max(7) - n + 1))
        eng.share(7, P.LIVE, P.CHAT, P.CHAT + n)
        t3 = time.time()
        P.share_layout(eng, layout, [{"id": s["id"], "slot": s["slot"], "pos_lo": s["pos_lo"],
                                      "pos_hi": s["pos_hi"]} for s in segs])
        t4 = time.time()
        res["insert_elapsed_ms"] = round((t4 - t_all) * 1000, 1)
        res["steps"] += [
            {"step": "drop(chat, 3 block ranges)", "ok": True, "elapsed_ms": round((t1 - t_all) * 1000, 1)},
            {"step": "repos_local(chat, +%d)" % N, "ok": True, "moved": moved,
             "elapsed_ms": round((t2 - t1) * 1000, 1)},
            {"step": "new block -> [%d,%d) + share" % (P.CHAT, P.CHAT + n), "ok": True,
             "cells": n, "elapsed_ms": round((t3 - t2) * 1000, 1)},
            {"step": "re-share 3 blocks", "ok": True, "elapsed_ms": round((t4 - t3) * 1000, 1)}]
        pos_after = {s["id"]: eng.pos_max(s["slot"]) for s in segs}
        res["block_pos_max"] = {"before": pos_before, "after": pos_after,
                                "unchanged": pos_before == pos_after}
        res["chat"]["after_insert"] = [P.CHAT + N, P.raw_pos_max(eng, P.LIVE) + 1]
        res["answers_after"] = ask_end(eng, q, "after_insert")
        res["answers_after"]["ok"] = bool(P.fact_ok(fact, res["answers_after"]["answer"]))
        cnt, positions = P.cell_scan(eng, P.LIVE)
        res["cell_scan_after"] = {"cells": cnt, "min": positions[0], "max": positions[-1],
                                  "gaps": [positions[i+1]-positions[i]-1 for i in range(len(positions)-1)
                                           if positions[i+1]-positions[i] > 1]}
        res["expected"] = fact
        res["verdict"] = {"blocks_undisturbed": res["block_pos_max"]["unchanged"],
                          "answer_ok_before": res["answers_before"]["ok"],
                          "answer_ok_after": res["answers_after"]["ok"]}
        print("elapsed_ms=%s blocks_unchanged=%s answer before/after=%s/%s" % (
            res["insert_elapsed_ms"], res["block_pos_max"]["unchanged"],
            res["answers_before"]["ok"], res["answers_after"]["ok"]))
        print("before:", res["answers_before"]["answer"][:70])
        print("after :", res["answers_after"]["answer"][:70])
        return 0
    except BaseException as exc:                     # noqa: BLE001
        res["error"] = "%s: %s" % (type(exc).__name__, exc)
        print("ERROR", exc)
        return 4
    finally:
        json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
        try:
            eng.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
