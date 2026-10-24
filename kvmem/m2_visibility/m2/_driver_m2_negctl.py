# -*- coding: utf-8 -*-
"""M2 negative control: a 4th question about a fact that is NOT in the 51-cell layout.

Q1..Q3 are asked exactly as in _driver_m2.py, in the same session, no reset; Q4 follows them
at the continuing position. Q1..Q3 must be byte-identical to the existing run_m2_r1.json --
if they moved, the apparatus was disturbed and this script refuses to interpret Q4.

Everything else is frozen (geometry, blocks, DLL, n_ctx/n_seq/q8_0/fa/-ngl 99, n_predict=64).

  python -X utf8 kvmem/m2_visibility/m2/_driver_m2_negctl.py --run-json <path>
"""
import argparse, hashlib, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _driver_m2 as M2                                     # noqa: E402  (sets P.MODEL etc.)

P = M2.P
Q4 = "我的车牌号是多少？"
CAR_PLATE_FACT = "浙B-3F19K"      # exists in our corpus but NO car block is in this layout
REFUSE_KEYS = ("不知道", "无法", "不清楚", "没有", "抱歉", "不得而知", "无从", "不能确定")
# capture the whole plate including the province character, so the recorded string is what was
# actually invented ("苏A12345"), not just its tail ("A12345")
PLATE_RE = re.compile(r"[\u4e00-\u9fff]?[A-Za-z][\-\u2014 ]?[A-Za-z0-9]{5}")
CTRL_JSON = os.path.join(M2.ROOT, "kvmem", "m2_visibility", "runs_m14b", "control_texts_14b.json")
PROBES = ("车牌", "浙B", "3F19K")


def sha(x):
    return hashlib.sha256((x or "").encode("utf-8")).hexdigest()


def classify(ans):
    """Three values the lead asked for, plus 'other' if none applies (never silently forced)."""
    na = M2.norm(ans)
    if M2.norm(CAR_PLATE_FACT) in na:
        return "leak", None, "答出了布局里没有的那个车牌事实本身"
    m = PLATE_RE.search(ans)
    if "浙" in na or m:
        return ("fabricate", (m.group(0) if m else na[:20]),
                "给出了具体车牌形态；该事实不在本布局任何块里")
    hit = [k for k in REFUSE_KEYS if k in na]
    if hit:
        return "refuse", None, "含拒答措辞: %s" % ",".join(hit)
    return "other", None, "三值都不匹配，形态见全文"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-json", required=True)
    a = ap.parse_args()
    rj = a.run_json if os.path.isabs(a.run_json) else os.path.join(HERE, a.run_json)
    base = json.load(open(os.path.join(HERE, "run_m2_r1.json"), encoding="utf-8"))
    res = {"schema": "m2_negctl_run_v1", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "questions": [q for _, q, _ in M2.EXPECT] + [Q4],
           "negative_control_question": Q4,
           "why": ("车牌事实存在于语料，但 51 格布局里没有 car 块 => 模型无从得知；"
                   "用它区分『答得出』是否来自 KV")}
    t0 = time.time()
    eng = None
    try:
        dll_sha = M2.sha(os.path.join(M2.ROOT, "tools", "kvshim_vk.dll"))
        if dll_sha != M2.DLL_WANT:
            raise SystemExit("tools DLL is %s, expected 9edbafa1" % dll_sha)
        man = P.load_manifest()
        layout = M2.build_m2_layout(man)
        if layout["cells_total"] != 51 or layout["span_lo"] != 4045 or layout["span_hi"] != 4096:
            raise SystemExit("geometry changed: %s" % layout)
        res["engine"] = {"model": M2.MODEL14B, "dll_sha256_measured": dll_sha,
                         "n_ctx": P.N_CTX, "n_seq": P.N_SEQ, "gpu": P.GPU, "kv": P.KV,
                         "n_predict": P.N_PREDICT, "threads": 8, "flash_attn": "on"}
        res["blocks"] = [{"id": s["id"], "cells": s["cells"], "pos_lo": s["pos_lo"],
                          "pos_hi": s["pos_hi"], "file_sha256": s["file_sha256"]}
                         for s in layout["segments"]]
        eng = P.open_engine()
        res["engine"]["loaded_dll_sha256"] = M2.sha(getattr(eng.lib, "_name", None))
        P.reset_all(eng)
        placed = P.load_and_place(eng, layout)
        P.share_layout(eng, layout, placed)
        cnt, positions = P.cell_scan(eng, P.LIVE)
        res["geometry"] = {"cells_total": cnt, "positions_min": positions[0],
                           "positions_max": positions[-1],
                           "head_gap_cells": (P.CHAT - 1) - (layout["span_hi"] - 1),
                           "overlaps": P.overlaps(layout), "raw_pos_max": P.raw_pos_max(eng, P.LIVE)}
        if not (cnt == 51 and positions[0] == 4045 and positions[-1] == 4095
                and res["geometry"]["raw_pos_max"] == 4095
                and not res["geometry"]["overlaps"]):
            raise SystemExit("geometry selfcheck %s" % res["geometry"])

        # --- premise + residue assertions before asking anything -------------------
        # (a) the plate string must exist in NO block text of this layout, and no car block
        #     may be loaded; otherwise Q4 is not a negative control at all.
        blockprobe = {p: any(p in P.FULL[k]["text"] for k in ("home", "project", "habit"))
                      for p in PROBES}
        carprobe = any(s["id"] == "car" or s["block_id"] == "car" for s in layout["segments"])
        # (b) the string does exist in the control-texts file, so if Q4 ever leaks, residual
        #     control text in the shared KV pool is the first suspect -- which is why the
        #     control slot must be measurably empty.
        ctrlprobe = None
        if os.path.exists(CTRL_JSON):
            blob = open(CTRL_JSON, encoding="utf-8").read()
            ctrlprobe = {p: p in blob for p in PROBES}
        ctrl_cnt, ctrl_pos = P.cell_scan(eng, P.CTRL)
        res["negctl_premise"] = {
            "block_text_probe": blockprobe, "car_block_loaded": carprobe,
            "control_texts_probe": ctrlprobe,
            "control_texts_file": CTRL_JSON,
            "control_slot": P.CTRL, "control_slot_cells": ctrl_cnt,
            "live_total_cells": cnt,
            "own_tokens_before_first_question": M2.D2.n_tokens(eng, P.LIVE)}
        if any(blockprobe.values()) or carprobe:
            raise SystemExit("STOP: Q4 is not a negative control -- probe string is in a loaded "
                             "block or a car block is present: %s" % res["negctl_premise"])
        if ctrl_cnt != 0:
            raise SystemExit("STOP: control slot %d holds %d cells (expected 0) -- residual "
                             "control text could make Q4 a contamination probe, not a "
                             "negative control" % (P.CTRL, ctrl_cnt))

        pos = 4096
        res["asks"] = []
        for sid, q, expect in list(M2.EXPECT) + [("negctl", Q4, [])]:
            before = M2.D2.n_tokens(eng, P.LIVE)
            nb, ans = M2.D2.ask_native(eng, P.LIVE, q, pos, P.N_PREDICT)
            after = M2.D2.n_tokens(eng, P.LIVE)
            rec = {"segment": sid, "question": q, "pos_asked": pos,
                   "n_tokens_before": before, "n_tokens_after": after,
                   "kvshim_ask_at_return_bytes": nb,
                   "answer": ans.strip(), "answer_len": len(ans.strip()),
                   "answer_sha256": sha(ans.strip())}
            if sid != "negctl":
                na = M2.norm(ans)
                hit = [e for e in expect if M2.norm(e) in na]
                rec.update({"expected_any_of": expect, "hit": hit, "ok": bool(hit),
                            "hit_string": hit[0] if hit else None})
            else:
                v, tok, why = classify(ans)
                rec.update({"verdict": v, "verdict_token": tok, "verdict_why": why})
            res["asks"].append(rec)
            print("[Q] %-8s pos=%-4d ntok %d->%d %s" % (
                sid, pos, before, after,
                ("hit=%s" % rec.get("hit_string")) if sid != "negctl"
                else ("verdict=%s token=%s" % (rec["verdict"], rec["verdict_token"]))))
            print("    full: %r" % ans.strip())
            pos = pos + (after - before)

        # --- regression: Q1..Q3 must be byte-identical to the accepted run ---
        cmp_ = []
        for i in range(3):
            old = base["asks"][i]["answer"]
            new = res["asks"][i]["answer"]
            cmp_.append({"segment": res["asks"][i]["segment"],
                         "identical_to_run_m2_r1": old == new,
                         "sha256_old": sha(old), "sha256_new": sha(new),
                         "old": old, "new": new})
        res["regression"] = {"per_question": cmp_,
                             "all_identical": all(c["identical_to_run_m2_r1"] for c in cmp_),
                             "against": "run_m2_r1.json"}
        if not res["regression"]["all_identical"]:
            res["error"] = ("STOP: Q1..Q3 differ from run_m2_r1.json -- apparatus disturbed, "
                            "Q4 is not interpreted")
            res["negctl_interpreted"] = False
        else:
            res["negctl_interpreted"] = True
        res["first_three_pass"] = all(r.get("ok") for r in res["asks"][:3])
    except SystemExit as exc:
        res["error"] = str(exc)
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
        print("[RUN] wrote %s  negctl_interpreted=%s  first_three_pass=%s"
              % (rj, res.get("negctl_interpreted"), res.get("first_three_pass")))
        if res.get("error"):
            print("[ERROR] %s" % res["error"])
    return 0 if res.get("negctl_interpreted") and res.get("first_three_pass") else 1


if __name__ == "__main__":
    sys.exit(main())
