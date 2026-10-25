# -*- coding: utf-8 -*-
"""真机插入探针：验证 §2.3 的四步（drop -> repos_local(chat) -> 新块 -> 重新 share）在 14B 上真的成立。

要产出（lead 指定）：
  · elapsed_ms（实测，唯一实测数）
  · 插入前后三块 pos_max
  · 插入后答案是否仍正确（问 project，与插入前对照）
  · 若失败，失败在哪一步
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "engine"))
import _driver2 as D2                      # noqa: E402
P = D2.P
P.FULL.setdefault("project_paraphrase18", dict(P.FULL["project"]))
P.FULL.setdefault("g18_bos_c18", dict(P.FULL["home"]))
P.MODEL = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
P.MANIFEST = os.path.join(HERE, "fixtures_probe14b.json")
D2.CTRL_CACHE = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_m14b", "control_texts_14b.json")

OUT = os.path.join(HERE, "out", "INSERT-REAL.json")
res = {"schema": "insert_real_v1", "layout": "iso_no_car", "target": "project",
       "steps": [], "answers": {}}


def step(name, fn):
    t = time.time()
    try:
        r = fn()
        dt = (time.time() - t) * 1000.0
        res["steps"].append({"step": name, "ok": True, "elapsed_ms": round(dt, 1), "result": r})
        print("  %-22s ok   %7.1f ms  %r" % (name, dt, r))
        return r
    except BaseException as exc:                       # noqa: BLE001
        dt = (time.time() - t) * 1000.0
        res["steps"].append({"step": name, "ok": False, "elapsed_ms": round(dt, 1),
                             "error": "%s: %s" % (type(exc).__name__, exc)})
        res["failed_at"] = name
        print("  %-22s FAIL %7.1f ms  %s" % (name, dt, exc))
        raise


def main():
    manifest = P.load_manifest()
    layout = D2.build_layout("iso_no_car", manifest)
    segs = layout["segments"]
    seg = next(s for s in segs if s["id"] == "project")
    q, fact = P.FULL[seg["block_id"]]["q"], P.FULL[seg["block_id"]]["fact"]
    new_file = next(s for s in segs if s["id"] == "habit")["file"]
    eng = P.open_engine()
    try:
        P.reset_all(eng)
        step("load_and_place(3 blocks)", lambda: [s["id"] for s in P.load_and_place(eng, layout)])
        eng.reset(P.LIVE)
        step("share_layout(3 blocks)", lambda: P.share_layout(eng, layout, P.load_and_place(eng, layout)) if False else P.share_layout(eng, layout, [{"id": s["id"], "slot": s["slot"], "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"]} for s in segs]))
        pos_before = {s["id"]: eng.pos_max(s["slot"]) for s in segs}

        n1, a_before = D2.ask_native(eng, P.LIVE, q, P.CHAT, 64)
        res["answers"]["before"] = {"answer": a_before.strip(), "ok": bool(P.fact_ok(fact, a_before)),
                                    "len": len(a_before), "return_bytes": n1}
        chat_hi = eng.pos_max(P.LIVE) + 1                  # exclusive
        res["chat"] = {"lo": P.CHAT, "hi_before": chat_hi, "ntok_before": D2.n_tokens(eng, P.LIVE)}
        print("baseline ok=%s chat=[%d,%d)" % (res["answers"]["before"]["ok"], P.CHAT, chat_hi))

        n_new = int(next(s for s in segs if s["id"] == "habit")["cells"])
        res["n_new_cells"] = n_new
        res["inserted_block"] = {"file": new_file, "note": "复用 habit 块（12 cells）作为新块；位置学与块内容无关"}

        t_all = time.time()
        step("1 drop(chat, block ranges)",
             lambda: [eng.drop(P.LIVE, s["pos_lo"], s["pos_hi"]) for s in segs] and "dropped %d" % len(segs))
        step("2 repos_local(chat, +%d)" % n_new,
             lambda: eng.repos_local(P.LIVE, +n_new, P.CHAT, chat_hi))
        def _new_block():
            eng.reset(7)
            n = eng.load_strict(7, new_file)
            base0 = eng.pos_max(7) - n + 1
            moved = eng.repos_local(7, P.CHAT - base0)
            eng.share(7, P.LIVE, P.CHAT, P.CHAT + n)
            return {"cells": n, "moved": moved, "pos_max": eng.pos_max(7)}
        step("3 new block -> [%d,%d)" % (P.CHAT, P.CHAT + n_new), _new_block)
        step("4 re-share 3 blocks",
             lambda: P.share_layout(eng, layout, [{"id": s["id"], "slot": s["slot"],
                                                   "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"]} for s in segs]))
        res["insert_elapsed_ms"] = round((time.time() - t_all) * 1000.0, 1)

        pos_after = {s["id"]: eng.pos_max(s["slot"]) for s in segs}
        res["block_pos_max"] = {"before": pos_before, "after": pos_after,
                                "unchanged": pos_before == pos_after}
        res["chat"]["hi_after"] = eng.pos_max(P.LIVE) + 1
        print("blocks unchanged=%s  %r -> %r" % (res["block_pos_max"]["unchanged"], pos_before, pos_after))

        n2, a_after = D2.ask_native(eng, P.LIVE, q, P.CHAT + n_new, 64)
        res["answers"]["after"] = {"answer": a_after.strip(), "ok": bool(P.fact_ok(fact, a_after)),
                                   "len": len(a_after), "return_bytes": n2}
        res["answers"]["expected"] = fact
        res["verdict"] = {"answer_still_ok": res["answers"]["after"]["ok"],
                          "blocks_undisturbed": res["block_pos_max"]["unchanged"]}
        print("after-insert ok=%s" % res["answers"]["after"]["ok"])
        return 0
    except BaseException as exc:                        # noqa: BLE001
        res["error"] = "%s: %s" % (type(exc).__name__, exc)
        return 4
    finally:
        res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
        try:
            eng.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
