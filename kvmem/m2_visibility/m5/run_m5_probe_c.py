# -*- coding: utf-8 -*-
"""M5 探针 (c) 长生成：4 题 × 每题一次独立引擎会话 × n_predict=256，逐句判定。

判据/切句器/装置全部来自冻结预登记 `PREREG-M5-PROBE-C.md`（sha16 见产物）：
  - 判定器 m5_ground.py：只用它的 split_sentences / ground（**不另写切句器**）；
  - 句级判定**不逐句调 ground**：整段答案一次 ground(answer, mounted, question)，
    再按判定器自己给出的 facts[].sentence 索引聚合（§5.3）；
  - 装置 14B（DLL / 几何 51 cells 4045..4095 / first_question_pos 4096 / n_ctx 8192 /
    n_seq 8 / gpu 99 / kv q8_0 / fa on / threads 8 逐项自证）；
  - 每题 fresh engine，不共享上下文；n_predict=256，采样用 DLL 内置默认（seed_known=false）。
两个率分开报（编造率 / 存疑率），各带分子分母；不合成、不设阈值。

产物：kvmem/m2_visibility/m5/out/M5C-<batch>-<run_id>.json，另存 _before/<name>@<sha16>。

exit：0 = 产出且不变量全过；1 = 读数不可用（未通过类，例如可判句=0）；5 = 装置/证据缺、
      几何自证不符、句级归属不可用、边界 1 被改动、跑前跑后 sha 不一致（本轮作废）。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

ROOT = r"D:/llama-mem"
M5 = os.path.join(ROOT, "kvmem", "m2_visibility", "m5")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "engine"))
sys.path.insert(0, M5)
import m5_ground as G                                          # noqa: E402
import m2_visibility_probe as P                                # noqa: E402
import _driver2 as D2                                          # noqa: E402

PREREG = os.path.join(M5, "PREREG-M5-PROBE-C.md")
JUDGE = os.path.join(M5, "m5_ground.py")
EVIDENCE = os.path.join(M5, "evidence_m5.json")
DB = os.path.join(M5, "memory.db")
MANIFEST = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_m14b", "fixtures_14b.json")
OUTDIR = os.path.join(M5, "out")
BEFORE = os.path.join(M5, "_before")
REGISTER = os.path.join(BEFORE, "REGISTER.json")

MODEL = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
MODEL_SIZE = 8988110240
MODEL_SHA16_ANCHOR = "0b319bd0572f2730"
DLL = os.path.join(ROOT, "tools", "kvshim_vk.dll")
DLL_SHA256_WANT = "9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c"
JUDGE_SHA16_WANT = "86b7c501ab9904aa"
EVIDENCE_SHA16_WANT = "0f57f4357452a865"
N_PREDICT = 256
BATCH = "c01"
FIRST_Q_POS = 4096
ALL = ["home", "project", "habit"]
# §4 的 4 题顺序（写死；出数后只允许照此顺序）
CASE_ORDER = ["addr", "project", "habit", "plate"]
TOPIC_BLOCK = {"addr": "home", "project": "project", "habit": "habit", "plate": None}
BOUNDARY1 = {"sample": "我住的社区叫蓝鲸。", "question": "我住在哪？", "expected": "supported"}
EMPTY_PUNCT = set("。！？\n，、；：,.!?;:「」『』（）()…—-\"'“”‘’ \t\r\u3000")


def sha256_file(path, chunk=8 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(chunk), b""):
            h.update(c)
    return h.hexdigest()


def sha16(path):
    return sha256_file(path)[:16]


def sha(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def build_layout(man):
    """与 M2 相同的 51 格布局（home/project/habit 三块，非等距）。逐块核文件 sha 与尺寸。"""
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
        if sha256_file(b["path"]) != b["sha256"]:
            raise SystemExit("STOP: %s sha mismatch" % sid)
        segs.append({"id": sid, "block_id": sid, "file": b["path"], "file_sha256": b["sha256"],
                     "cells": n, "slot": slot, "pos_lo": lo, "pos_hi": lo + n,
                     "add_order": len(order) + 1})
        order.append(sid)
    segs.sort(key=lambda s: s["pos_lo"])
    return {"key": "m2_three", "segments": segs, "add_order": order,
            "cells_total": sum(s["cells"] for s in segs),
            "span_lo": min(s["pos_lo"] for s in segs),
            "span_hi": max(s["pos_hi"] for s in segs)}


def is_empty_seg(seg):
    s = (seg or "").strip()
    return (not s) or all(ch in EMPTY_PUNCT for ch in s)


def judge_answer(answer, question):
    """整段一次 ground，再按 facts[].sentence 聚合到句（§5.3）。返回 rep 与句级明细。"""
    rep = G.ground(answer, ALL, question, DB)
    segs = G.split_sentences(answer)
    n_seg = len(segs)
    facts_by, unhit_by, undec_by = {}, {}, {}
    for f in rep.get("facts", []):
        facts_by.setdefault(f["sentence"], []).append(f)
    for u in rep.get("unhit", []):
        unhit_by.setdefault(u["sentence"], []).append(u)
    for u in rep.get("undecidable_items", []):
        undec_by.setdefault(u.get("sentence"), []).append(u)
    bad_owner = [f["sentence"] for f in rep.get("facts", [])
                 if not (0 <= f["sentence"] < n_seg)]
    sentences = []
    for idx, seg in enumerate(segs):
        rec = {"idx": idx, "text": seg, "empty": is_empty_seg(seg),
               "n_facts": len(facts_by.get(idx, [])),
               "n_unhit": len(unhit_by.get(idx, [])),
               "n_undecidable": len(undec_by.get(idx, [])),
               "facts": [{"family": f["family"], "raw": f["raw"], "key": str(f["key"]),
                          "hit": f["hit"], "origin": f.get("origin")}
                         for f in facts_by.get(idx, [])],
               "unhit": [{"family": u["family"], "raw": u["raw"]}
                         for u in unhit_by.get(idx, [])]}
        if rec["empty"]:
            rec["verdict"], rec["note"] = None, "空句（§5.2 不计入任何分母）"
        elif rec["n_unhit"]:
            rec["verdict"], rec["note"] = "unsupported", "§5.3-1 该句有未命中硬事实"
        elif rec["n_undecidable"]:
            rec["verdict"], rec["note"] = "undecidable", "§5.3-2 该句有 undecidable 项"
        elif rec["n_facts"]:
            rec["verdict"], rec["note"] = "supported", "§5.3-3 该句硬事实全命中"
        else:
            rec["verdict"], rec["note"] = "no_fact", "§5.3-4 抽不到硬事实"
        sentences.append(rec)
    return rep, sentences, n_seg, bad_owner


def finalize_answer(case, question, answer, rep, sentences, n_seg, bad_owner):
    non_empty = [s for s in sentences if not s["empty"]]
    tail_idx = None
    if non_empty and (non_empty[-1]["text"][-1] not in G.SENT_END):
        tail_idx = non_empty[-1]["idx"]
    for s in sentences:
        s["in_denominator"] = (not s["empty"]) and s["idx"] != tail_idx
        if s["idx"] == tail_idx:
            s["verdict"], s["note"] = None, "末句未终止（§5.2 不计入分子或分母，单列）"
    counted = [s for s in sentences if s["in_denominator"]]
    counts = {"supported": 0, "unsupported": 0, "undecidable": 0, "no_fact": 0}
    for s in counted:
        counts[s["verdict"]] += 1
    texts = [s["text"] for s in non_empty]
    n_dup = len(texts) - len(set(texts))
    tail = [{"case": case, "idx": tail_idx, "text": sentences[tail_idx]["text"]}
            ] if tail_idx is not None else []
    no_fact = [{"case": case, "idx": s["idx"], "text": s["text"]}
               for s in counted if s["verdict"] == "no_fact"]
    return {
        "case": case, "question": question, "answer": answer,
        "answer_sha256": sha(answer), "n_chars": len(answer),
        "answer_endswith_sent_end": bool(answer) and answer[-1] in G.SENT_END,
        "n_segments": n_seg, "n_empty_segments": sum(1 for s in sentences if s["empty"]),
        "n_sentences": len(non_empty), "n_sentences_counted": len(counted),
        "n_tail_unterminated": len(tail), "tail_idx": tail_idx,
        "judge_verdict": rep.get("verdict"), "judge_reason": rep.get("reason"),
        "facts_sentence_ok": not bad_owner, "facts_sentence_out_of_range": bad_owner,
        "sentences": sentences,
        "counts": dict(counts, n_total=len(counted), n_duplicate_sentences=n_dup),
        "no_fact": no_fact, "truncated_last": tail,
    }, counts, n_dup


def attribution_candidates(res, profs):
    """§5.8 归属错误机械候选（不替代审计侧人工标注）：判 supported 且命中事实只出现在
    非题目所属块里。"""
    out = []
    topic = TOPIC_BLOCK.get(res["case"])
    for s in res["sentences"]:
        if s.get("verdict") != "supported":
            continue
        hit_blocks = set()
        for f in s["facts"]:
            if not f["hit"]:
                continue
            for bid, prof in profs.items():
                fam = f["family"]
                k = f["key"]
                ok = (G.a_hit(k, prof) if fam == "A" else G.date_hit(k, prof) if fam == "D"
                      else G.p_hit(k, prof) if fam == "P" else k in prof["nums"])
                if ok:
                    hit_blocks.add(bid)
        if hit_blocks and (topic not in hit_blocks):
            out.append({"case": res["case"], "idx": s["idx"], "text": s["text"],
                        "class": "归属错误（§5.8，机械候选，待审计复核）",
                        "mechanical": True, "topic_block": topic,
                        "hit_blocks": sorted(hit_blocks), "in_rates": False})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="r1")
    a = ap.parse_args()
    t0 = time.time()
    run_id = a.tag
    out_name = "M5C-%s-%s.json" % (BATCH, run_id)
    out_path = os.path.join(OUTDIR, out_name)

    pre = {
        "judge_sha16": sha16(JUDGE), "prereg_sha16": sha16(PREREG),
        "evidence_sha16": sha16(EVIDENCE), "db_sha16": sha16(DB),
        "prereg_bytes": os.path.getsize(PREREG),
        "out_dir_exists": os.path.isdir(OUTDIR),
        "out_dir_pre_files": sorted(os.listdir(OUTDIR)) if os.path.isdir(OUTDIR) else [],
    }
    inv = []            # 不变量失败（round_void 类）
    notes = []          # 未接上/读数不可用类

    # ---- 装置自证：DLL / 14B / manifest ----
    dll_sha256 = sha256_file(DLL)
    man = json.load(open(MANIFEST, encoding="utf-8"))
    me = man.get("engine", {})
    model_size = os.path.getsize(MODEL)
    model_sha256 = sha256_file(MODEL)
    model_sha16 = model_sha256[:16]
    device = {
        "model_path": MODEL, "model_size": model_size, "model_sha256": model_sha256,
        "model_sha16": model_sha16, "model_sha16_anchor": MODEL_SHA16_ANCHOR,
        "model_sha16_match": model_sha16 == MODEL_SHA16_ANCHOR,
        "model_sha256_provenance": ("本进程实算（sha256_file 全文件 9 GB，chunked）"
                                    "；size 与 runs_m14b/fixtures_14b.json engine.model_size "
                                    "一致；sha16 锚见 PREREG §3"),
        "dll_path": DLL, "dll_sha256": dll_sha256, "dll_sha256_want": DLL_SHA256_WANT,
        "dll_sha256_match": dll_sha256 == DLL_SHA256_WANT,
        "n_ctx": P.N_CTX, "n_seq": P.N_SEQ, "gpu": P.GPU, "kv": P.KV,
        "flash_attn": "on", "threads": 8,
        "manifest": MANIFEST, "manifest_sha16": sha16(MANIFEST),
    }
    if dll_sha256 != DLL_SHA256_WANT:
        inv.append("装置：DLL sha256=%s ≠ 9edbafa1…" % dll_sha256)
    if model_size != MODEL_SIZE or model_sha16 != MODEL_SHA16_ANCHOR:
        inv.append("装置非 14B：size=%d sha16=%s（锚 %s）"
                   % (model_size, model_sha16, MODEL_SHA16_ANCHOR))
    if me.get("model") and os.path.normcase(me["model"].replace("\\", "/")) != os.path.normcase(MODEL):
        inv.append("manifest engine.model 与 14B 路径不符")
    if pre["judge_sha16"] != JUDGE_SHA16_WANT:
        inv.append("判定器 sha16=%s ≠ %s" % (pre["judge_sha16"], JUDGE_SHA16_WANT))
    if pre["evidence_sha16"] != EVIDENCE_SHA16_WANT:
        inv.append("证据 sha16=%s ≠ %s" % (pre["evidence_sha16"], EVIDENCE_SHA16_WANT))

    # ---- 样本：evidence.four_cases 逐字，顺序写死 ----
    ev = json.load(open(EVIDENCE, encoding="utf-8"))
    cases = [(c.get("case"), c.get("question")) for c in ev.get("four_cases", [])]
    if [c for c, _ in cases] != CASE_ORDER:
        inv.append("样本顺序/集合与 §4 不符：%s" % ([c for c, _ in cases],))
    questions = [(c, q) for c, q in cases if c in CASE_ORDER]

    # ---- 布局（文件级自证） ----
    layout = build_layout(man)
    if (layout["cells_total"], layout["span_lo"], layout["span_hi"]) != (51, 4045, 4096):
        inv.append("布局几何与冻结值不符：%s" % json.dumps(
            {k: layout[k] for k in ("cells_total", "span_lo", "span_hi")}, ensure_ascii=False))

    # ---- 边界 1（形态检查，不进任何分母） ----
    b1 = G.ground(BOUNDARY1["sample"], ALL, BOUNDARY1["question"], DB)
    boundary1 = {"sample": BOUNDARY1["sample"], "question": BOUNDARY1["question"],
                 "expected": BOUNDARY1["expected"], "verdict": b1.get("verdict"),
                 "reason": b1.get("reason"),
                 "facts": [{"family": f["family"], "raw": f["raw"], "hit": f["hit"]}
                           for f in b1.get("facts", [])],
                 "ok": b1.get("verdict") == BOUNDARY1["expected"]}
    if not boundary1["ok"]:
        inv.append("边界 1 被改动：%s ⇒ %r（应 supported）"
                   % (BOUNDARY1["sample"], b1.get("verdict")))

    answers, geom_runs = [], []
    if not inv:
        P.MODEL = MODEL
        P.MANIFEST = MANIFEST
        for case, q in questions:
            eng = P.open_engine()          # 每题一次 fresh engine 会话
            try:
                P.reset_all(eng)
                placed = P.load_and_place(eng, layout)
                P.share_layout(eng, layout, placed)
                cnt, positions = P.cell_scan(eng, P.LIVE)
                raw = P.raw_pos_max(eng, P.LIVE)
                geom = {"case": case,
                        "cells_total": cnt, "positions_min": positions[0] if positions else None,
                        "positions_max": positions[-1] if positions else None,
                        "first_question_pos": FIRST_Q_POS,
                        "head_gap_cells": (FIRST_Q_POS - 1) - (layout["span_hi"] - 1),
                        "raw_pos_max": raw, "overlaps": P.overlaps(layout),
                        "segments": [{"id": s["id"], "cells": s["cells"],
                                      "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"],
                                      "file_sha256": s["file_sha256"]} for s in layout["segments"]],
                        "placed_base_delta": [{"id": p["id"], "base": p["base"],
                                               "delta": p["delta"]} for p in placed],
                        "engine_handle": int(eng.h) if eng.h else None,
                        "n_ctx": eng.n_ctx, "n_seq": eng.n_seq, "fresh_engine": True}
                ok_geom = (cnt == 51 and positions and positions[0] == 4045
                           and positions[-1] == 4095 and raw == 4095
                           and not geom["overlaps"] and geom["head_gap_cells"] == 0)
                geom["ok"] = bool(ok_geom)
                geom_runs.append(geom)
                if not ok_geom:
                    inv.append("几何自证不符（%s）：%s" % (case, json.dumps(
                        {k: geom[k] for k in ("cells_total", "positions_min", "positions_max",
                                              "raw_pos_max", "overlaps")}, ensure_ascii=False)))
                    break
                n_before = D2.n_tokens(eng, P.LIVE)
                nb, ans = D2.ask_native(eng, P.LIVE, q, FIRST_Q_POS, N_PREDICT)
                n_after = D2.n_tokens(eng, P.LIVE)
                rep, sentences, n_seg, bad_owner = judge_answer(ans, q)
                res, counts, n_dup = finalize_answer(case, q, ans, rep, sentences, n_seg, bad_owner)
                res.update({"pos_asked": FIRST_Q_POS, "n_predict": N_PREDICT,
                            "kvshim_ask_at_return_bytes": nb,
                            "n_tokens_before": n_before, "n_tokens_after": n_after,
                            "engine_handle": geom["engine_handle"]})
                if bad_owner:
                    notes.append("句级归属不可用（%s）：facts[].sentence 越界 %s"
                                 % (case, bad_owner))
                answers.append(res)
            finally:
                try:
                    eng.close()
                except Exception:                                  # noqa: BLE001
                    pass

    # ---- 逐句聚合 ----
    tot = {"supported": 0, "unsupported": 0, "undecidable": 0, "no_fact": 0}
    n_dup_all = 0
    for r in answers:
        for k in tot:
            tot[k] += r["counts"][k]
        n_dup_all += r["counts"]["n_duplicate_sentences"]
    n_total = sum(tot.values())
    counts_all = {"n_total_sentences": n_total, "n_supported": tot["supported"],
                  "n_unsupported": tot["unsupported"], "n_undecidable": tot["undecidable"],
                  "n_no_fact": tot["no_fact"],
                  "n_tail_unterminated": sum(r["n_tail_unterminated"] for r in answers),
                  "n_duplicate_sentences": n_dup_all,
                  "n_empty_segments": sum(r["n_empty_segments"] for r in answers)}
    judged = tot["supported"] + tot["unsupported"]
    rates = {"fabrication": {"num": tot["unsupported"], "den": judged},
             "undecidable": {"num": tot["undecidable"], "den": n_total}}

    # ---- §5.8 归属错误机械候选 ----
    try:
        import sqlite3
        con = sqlite3.connect(DB)
        texts, probs = G.verify_sources(con, ALL)
        con.close()
        profs = {bid: G.source_profile([t]) for bid, t in zip(ALL, texts)} if not probs else {}
    except Exception:                                          # noqa: BLE001
        profs = {}
    expected_miss = []
    for r in answers:
        expected_miss += attribution_candidates(r, profs)

    # ---- 跑前跑后冻结项一致 ----
    post = {"judge_sha16": sha16(JUDGE), "prereg_sha16": sha16(PREREG),
            "evidence_sha16": sha16(EVIDENCE), "db_sha16": sha16(DB)}
    stable = all(pre[k] == post[k] for k in post)
    if not stable:
        inv.append("跑前跑后冻结项 sha16 不一致：%s" % json.dumps(
            {k: [pre[k], post[k]] for k in post if pre[k] != post[k]}, ensure_ascii=False))

    round_void = bool(inv)
    no_judgeable = (judged == 0)
    if no_judgeable:
        notes.append("可判句 = 0（sup+unsup=0）⇒ 读数不可用（未通过类，§9）")
    code = 5 if round_void else (1 if no_judgeable else 0)
    if round_void or no_judgeable:
        rates_out = None
    else:
        rates_out = rates
    rec = {
        "schema": "m5_probe_c_v1", "probe": "c", "batch": BATCH, "run_id": run_id,
        "prereg_sha16": pre["prereg_sha16"], "prereg_bytes": pre["prereg_bytes"],
        "judge_sha16": pre["judge_sha16"], "judge_sha16_after": post["judge_sha16"],
        "evidence_sha16": pre["evidence_sha16"], "db_sha16": pre["db_sha16"],
        "frozen_sha_stable": stable,
        "sampled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "device": device, "manifest": {"path": MANIFEST, "sha16": device["manifest_sha16"]},
        "geometry": {"cells_total": layout["cells_total"], "positions": [layout["span_lo"],
                                                                        layout["span_hi"] - 1],
                     "first_question_pos": FIRST_Q_POS,
                     "segments": [{"id": s["id"], "cells": s["cells"], "pos_lo": s["pos_lo"],
                                   "pos_hi": s["pos_hi"]} for s in layout["segments"]],
                     "runs": geom_runs},
        "gen_params": {"n_predict": N_PREDICT,
                       "sampling": "DLL 内置默认（kvshim_ask_at 不暴露采样参数）",
                       "seed_known": False,
                       "note": "本题结论只对该次生成有效，不宣称分布（PREREG §3）"},
        "prompt_template": "turn(q) = \"\\n问：\" + q + \"\\n答：\"；答案 = 生成段",
        "answers": answers,
        "rates": rates_out,
        "fabrication_rate": rates_out["fabrication"] if rates_out else None,
        "doubt_rate": rates_out["undecidable"] if rates_out else None,
        "no_fact": [x for r in answers for x in r["no_fact"]],
        "truncated_last": [x for r in answers for x in r["truncated_last"]],
        "counts": counts_all,
        "boundary1": boundary1,
        "boundary1_check": boundary1,
        "expected_miss": expected_miss,
        "expected_miss_note": ("§5.8 四类命中最终标注属审计侧；本产物只给机械候选"
                               "（判 supported 且命中事实只出现在非题目所属块），in_rates=false"),
        "sentence_rule": ("句级判定：整段一次 ground(answer, ALL, question)，按判定器 facts[].sentence "
                          "聚合；优先级 §5.3-1 unhit > -2 undecidable > -3 有事实 > -4 no_fact；"
                          "空句与末句未终止不进任何分母"),
        "tail_rule": "末句终止符 = 最后一个非空句段是否以 SENT_END（。！？\\n）结尾",
        "invariant_failures": inv, "notes": notes, "round_void": round_void,
        "out_pre_state": {"dir_exists": pre["out_dir_exists"],
                          "files": pre["out_dir_pre_files"]},
        "exit": code,
    }
    os.makedirs(OUTDIR, exist_ok=True)
    json.dump(rec, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    out_sha16 = sha16(out_path)
    os.makedirs(BEFORE, exist_ok=True)
    copy = os.path.join(BEFORE, "%s@%s" % (out_name, out_sha16))
    with open(out_path, "rb") as f1, open(copy, "wb") as f2:
        f2.write(f1.read())
    reg = {"entries": []}
    if os.path.exists(REGISTER):
        reg = json.load(open(REGISTER, encoding="utf-8"))
        reg.setdefault("entries", [])
    reg["entries"].append({
        "source_name": out_name, "source_sha16": out_sha16,
        "copy_path": os.path.abspath(copy).replace("\\", "/"), "in_place": False,
        "copy_time": time.strftime("%Y-%m-%dT%H:%M:%S"), "copyist": "executor",
        "reason": "M5 探针 (c) 长生成产物落档：4 题独立引擎会话 n_predict=256，逐句判定，两率分开",
        "exit": code})
    json.dump(reg, open(REGISTER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rec_print = {"out": out_path, "sha16": out_sha16, "bytes": os.path.getsize(out_path),
                 "exit": code, "round_void": round_void,
                 "counts": counts_all, "rates": rates_out,
                 "boundary1": boundary1["verdict"],
                 "judge_sha16": pre["judge_sha16"], "prereg_sha16": pre["prereg_sha16"],
                 "evidence_sha16": pre["evidence_sha16"],
                 "model_sha16": model_sha16, "dll_sha256_ok": dll_sha256 == DLL_SHA256_WANT,
                 "elapsed_s": round(time.time() - t0, 1)}
    print(json.dumps(rec_print, ensure_ascii=False))
    for r in answers:
        print("[%s] q=%r n_sent=%d counted=%d sup=%d unsup=%d und=%d nofact=%d tail=%d judge=%s"
              % (r["case"], r["question"], r["n_sentences"], r["n_sentences_counted"],
                 r["counts"]["supported"], r["counts"]["unsupported"],
                 r["counts"]["undecidable"], r["counts"]["no_fact"],
                 r["n_tail_unterminated"], r["judge_verdict"]))
    if inv:
        print("INVARIANTS: %s" % json.dumps(inv, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())