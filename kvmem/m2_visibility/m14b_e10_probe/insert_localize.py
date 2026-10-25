# -*- coding: utf-8 -*-
"""插入失败定位：四步都报 ok，但插入后 ask_at 返回 -1。逐个因子隔离。

配置（每次都在同一 engine 上 reset 后重建，避免模型重复加载）：
  D0 只放置 + share，问第二次      -> 排除「连问两次本身不行」
  D1 drop + re-share，不移动不插块  -> 排除「摘引用后重新挂」本身
  D2 drop + repos_local(+12) + re-share，不插块 -> 只测「移动对话」
  D3 drop + repos_local(+12) + 插块 + re-share（= 主实验）-> 应复现失败
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
OUT = os.path.join(HERE, "out", "INSERT-LOCALIZE.json")
N = 12


def build(eng, manifest):
    layout = D2.build_layout("iso_no_car", manifest)
    segs = layout["segments"]
    P.reset_all(eng)
    P.load_and_place(eng, layout)
    eng.reset(P.LIVE)
    P.share_layout(eng, layout, [{"id": s["id"], "slot": s["slot"],
                                  "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"]} for s in segs])
    return layout, segs


def ask(eng, q, pos, tag):
    t = time.time()
    n, a = D2.ask_native(eng, P.LIVE, q, pos, 64)
    return {"tag": tag, "ask_pos": pos, "return_bytes": n, "len": len(a),
            "answer": a.strip()[:60], "elapsed_ms": round((time.time() - t) * 1000, 1),
            "pos_max_live": eng.pos_max(P.LIVE), "can_shift": bool(eng.can_shift())}


def main():
    manifest = P.load_manifest()
    eng = P.open_engine()
    out = {"schema": "insert_localize_v1", "cases": []}
    try:
        for case in ("D0", "D1", "D2", "D3"):
            layout, segs = build(eng, manifest)
            seg = next(s for s in segs if s["id"] == "project")
            q, fact = P.FULL[seg["block_id"]]["q"], P.FULL[seg["block_id"]]["fact"]
            rec = {"case": case, "q": q, "expected": fact}
            # 先问一次，把对话写进 LIVE（与主实验一致）
            rec["ask_1"] = ask(eng, q, P.CHAT, "before_insert")
            chat_hi = eng.pos_max(P.LIVE) + 1
            rec["chat_hi_before"] = chat_hi
            new_lo = P.CHAT
            if case in ("D1", "D2", "D3"):
                for s in segs:
                    eng.drop(P.LIVE, s["pos_lo"], s["pos_hi"])
                rec["dropped"] = True
            if case in ("D2", "D3"):
                rec["moved_cells"] = eng.repos_local(P.LIVE, +N, P.CHAT, chat_hi)
                rec["chat_hi_after_move"] = eng.pos_max(P.LIVE) + 1
            if case == "D3":
                new_file = next(s for s in segs if s["id"] == "habit")["file"]
                eng.reset(7)
                n = eng.load_strict(7, new_file)
                eng.repos_local(7, P.CHAT - (eng.pos_max(7) - n + 1))
                eng.share(7, P.LIVE, P.CHAT, P.CHAT + n)
                rec["new_block"] = {"cells": n, "range": [P.CHAT, P.CHAT + n]}
            if case in ("D1", "D2", "D3"):
                P.share_layout(eng, layout, [{"id": s["id"], "slot": s["slot"],
                                              "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"]} for s in segs])
            scan = None
            try:
                cnt, positions = P.cell_scan(eng, P.LIVE)
                scan = {"cells": cnt, "min": positions[0], "max": positions[-1],
                        "gaps": [positions[i + 1] - positions[i] - 1 for i in range(len(positions) - 1)
                                 if positions[i + 1] - positions[i] > 1][:5]}
            except Exception as e:                     # noqa: BLE001
                scan = {"error": str(e)}
            rec["cell_scan"] = scan
            ask_pos = P.CHAT + (N if case in ("D2", "D3") else 0)
            rec["ask_2"] = ask(eng, q, ask_pos, "after_" + case)
            out["cases"].append(rec)
            print("%s: ask1 bytes=%s | ask2 bytes=%s len=%s pos=%s | scan=%s" % (
                case, rec["ask_1"]["return_bytes"], rec["ask_2"]["return_bytes"],
                rec["ask_2"]["len"], ask_pos, scan))
        return 0
    except BaseException as exc:                       # noqa: BLE001
        out["error"] = "%s: %s" % (type(exc).__name__, exc)
        print("ERROR", exc)
        return 4
    finally:
        json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
        try:
            eng.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
