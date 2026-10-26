# -*- coding: utf-8 -*-
"""M5-C (c) 36-layer long-generation probe, PREREG-M5-C 250dbb41.

CAND side only.  One question per scenario, no retry/regeneration.  The parent
never sends a signal to an engine child; S8 uses two short-lived OS processes.
JUDGE is the frozen m5_ground_v2.py 5e11e1ac; ADJ labels are intentionally not
produced here (sealed by the inspector/ADJ role).
"""
import argparse
import ctypes
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
M7 = ROOT / "kvmem/m2_visibility/m7"
TMP = OUT / "tmp_m5c"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(M5))
sys.path.insert(0, str(ROOT / "kvmem/m2_visibility/engine"))
sys.path.insert(0, str(M7 / "out"))

import m5_ground_v2 as G                                      # noqa: E402
import m2_visibility_probe as P                               # noqa: E402
import _driver2 as D2                                         # noqa: E402
import _e3gpu_run as E                                        # noqa: E402

PREREG = ROOT / "docs/_work/PREREG-M5-C.md"
PREREG_SHA = "250dbb417a7e7470"
PREREG_BYTES = 14071
JUDGE = M5 / "m5_ground_v2.py"
JUDGE_SHA = "5e11e1ac06f022c7"
JUDGE_BYTES = 66413
DB = M5 / "memory.db"
MANIFEST = ROOT / "kvmem/m2_visibility/runs_m14b/fixtures_14b.json"
MODEL = E.MODEL
MODEL_BYTES = E.MODEL_BYTES
DLL = E.VK
DLL_SHA = E.VK_SHA16
DLL_BYTES = E.VK_BYTES
SAVE = OUT / "M5C-36-resume-S8.kvmem"
ART = OUT / "M5C-36-r1.json"
LANDED = M5 / "LANDED-m5-c.json"
STOP_GLOBAL = OUT / "_m5_stop.flag"
N_PREDICT = 192
N_PREDICT_S8A = 128
GATE_GIB = 8.6
TARGET_GIB = 8.0
SCENARIO_TIMEOUT = 900
ALL = ["home", "project", "habit"]
EMPTY_PUNCT = set("。！？\n，、；：,.!?;:「」『』（）()…—-\"'“”‘’ \t\r\u3000")
QUESTIONS = {
    "S1": "我住在哪？",
    "S2": "项目代号是什么？什么时候上线？",
    "S3": "我喝咖啡有什么习惯？",
    "S4": "我住在杭州对吧？",
    "S5": "我的车牌号是多少？",
    "S6": "我喝美式的时候，常想哪个项目、它什么时候上线？",
}
S7_QUESTIONS = [
    "我住在哪？",
    "项目代号是什么？",
    "我喝咖啡有什么习惯？",
    "项目什么时候上线？",
    "把这三件事连起来说一遍。",
    "我的住址具体到门牌。",
    "项目上线日期是几月几号？",
    "我的咖啡加糖吗？",
    "我住在哪？",
]
S8_Q = "我住在哪？"


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def info(path):
    b = Path(path).read_bytes()
    return {"path": str(path), "sha16": hashlib.sha256(b).hexdigest()[:16], "bytes": len(b)}


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def source_texts():
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    try:
        rows = {r["block_id"]: r["source_text"] for r in
                con.execute("select block_id,source_text from blocks where block_id in ('home','project','habit')")}
    finally:
        con.close()
    return rows


def build_layout(manifest):
    """Same 51-cell layout used by (a)/(c): home@[4075,4096), project@[4057,4075), habit@[4045,4057)."""
    pos = {"home": (1, 4075), "project": (2, 4057), "habit": (3, 4045)}
    segs, order = [], []
    for sid in ("home", "project", "habit"):
        b = manifest["blocks"]["m2"][sid]
        slot, lo = pos[sid]
        n = b["cells"]
        if b["path"].replace("\\", "/").find("/m2_v1_14b/") < 0:
            raise SystemExit("STOP: block %s is not under m2_v1_14b: %s" % (sid, b["path"]))
        if os.path.getsize(b["path"]) != 1188 + 104464 * n:
            raise SystemExit("STOP: %s size mismatch" % sid)
        if sha16(b["path"]) != b["sha256"][:16]:
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


def place(eng, layout):
    P.reset_all(eng)
    placed = P.load_and_place(eng, layout)
    P.share_layout(eng, layout, placed)
    cnt, positions = P.cell_scan(eng, P.LIVE)
    raw = P.raw_pos_max(eng, P.LIVE)
    geom = {"cells_total": cnt,
            "positions_min": positions[0] if positions else None,
            "positions_max": positions[-1] if positions else None,
            "first_question_pos": 4096,
            "head_gap_cells": (4096 - 1) - (layout["span_hi"] - 1),
            "raw_pos_max": raw, "overlaps": P.overlaps(layout),
            "segments": [{"id": s["id"], "cells": s["cells"], "pos_lo": s["pos_lo"],
                          "pos_hi": s["pos_hi"], "file_sha256": s["file_sha256"]} for s in layout["segments"]],
            "placed_base_delta": [{"id": p["id"], "base": p["base"], "delta": p["delta"]} for p in placed],
            "n_tokens_after_place": int(eng.n_tokens(P.LIVE)),
            "engine_handle": int(eng.h) if eng.h else None,
            "n_ctx": eng.n_ctx, "n_seq": eng.n_seq, "fresh_engine": True}
    geom["ok"] = bool(cnt == 51 and positions and positions[0] == 4045 and positions[-1] == 4095
                      and raw == 4095 and not geom["overlaps"] and geom["head_gap_cells"] == 0)
    return geom


def sentence_eval(answer, question):
    """PREREG §1 sentence attribution: one ground() over the whole answer, then aggregate."""
    rep = G.ground(answer, ALL, question, DB)
    segs = G.split_sentences(answer or "")
    n_seg = len(segs)
    facts_by, unhit_by, undec_by = {}, {}, {}
    for f in rep.get("facts", []):
        facts_by.setdefault(f.get("sentence"), []).append(f)
    for u in rep.get("unhit", []):
        unhit_by.setdefault(u.get("sentence"), []).append(u)
    for u in rep.get("undecidable_items", []):
        undec_by.setdefault(u.get("sentence"), []).append(u)
    bad_owner = []
    for kind, arr in (("facts", rep.get("facts", [])), ("unhit", rep.get("unhit", [])),
                      ("undecidable", rep.get("undecidable_items", []))):
        for x in arr:
            s = x.get("sentence")
            if not isinstance(s, int) or not (0 <= s < n_seg):
                bad_owner.append({"kind": kind, "sentence": s, "raw": x.get("raw")})
    sentences = []
    for idx, seg in enumerate(segs):
        rec = {"idx": idx, "text": seg, "empty": is_empty_seg(seg),
               "n_facts": len(facts_by.get(idx, [])), "n_unhit": len(unhit_by.get(idx, [])),
               "n_undecidable": len(undec_by.get(idx, [])),
               "facts": [{"family": f.get("family"), "raw": f.get("raw"), "key": str(f.get("key")),
                          "hit": f.get("hit"), "origin": f.get("origin")} for f in facts_by.get(idx, [])],
               "unhit": [{"family": u.get("family"), "raw": u.get("raw")} for u in unhit_by.get(idx, [])],
               "undecidable": [{"family": u.get("family"), "raw": u.get("raw"), "why": u.get("why")}
                               for u in undec_by.get(idx, [])],
               "u": rep.get("ngram", {}).get("u"),
               "branch": rep.get("branch"),
               "near_threshold": bool(rep.get("near_threshold", False)),
               "in_denominator": True}
        if rec["empty"]:
            rec["verdict"], rec["note"] = None, "空句（§1 单列，不进任何分母）"
            rec["in_denominator"] = False
        elif rec["n_unhit"]:
            rec["verdict"], rec["note"] = "unsupported", "本句 ≥1 条 unhit"
        elif rec["n_undecidable"]:
            rec["verdict"], rec["note"] = "undecidable", "本句有 undecidable 项（繁体/P-c 豁免）"
        elif rec["n_facts"]:
            rec["verdict"], rec["note"] = "supported", "本句 ≥1 条 fact 且无 unhit/undecidable"
        else:
            rec["verdict"], rec["note"] = "no_fact", "本句无 fact（单列）"
        sentences.append(rec)
    non_empty = [s for s in sentences if not s["empty"]]
    tail_idx = None
    if non_empty and (non_empty[-1]["text"][-1] not in G.SENT_END):
        tail_idx = non_empty[-1]["idx"]
    for s in sentences:
        if s["idx"] == tail_idx:
            s["in_denominator"] = False
            s["note"] = "末句未终止（单列，不进分母）"
    counted = [s for s in sentences if s["in_denominator"]]
    counts = {"total": len(sentences), "counted": len(counted),
              "supported": 0, "unsupported": 0, "undecidable": 0, "no_fact": 0,
              "tail": 1 if tail_idx is not None else 0, "empty": 0, "dup": 0}
    for s in counted:
        if s["verdict"] in counts:
            counts[s["verdict"]] += 1
    counts["empty"] = sum(1 for s in sentences if s["empty"])
    texts = [s["text"] for s in non_empty]
    counts["dup"] = len(texts) - len(set(texts))
    no_fact = [{"scenario": None, "idx": s["idx"], "text": s["text"]} for s in counted if s["verdict"] == "no_fact"]
    excluded = [{"idx": s["idx"], "text": s["text"],
                 "reason": "empty" if s["empty"] else "tail"} for s in sentences
                if s["empty"] or s["idx"] == tail_idx]
    return {"rep": rep, "sentences": sentences, "n_sentences": n_seg,
            "n_sentences_counted": len(counted), "counts": counts,
            "tail_idx": tail_idx, "no_fact": no_fact, "excluded": excluded,
            "bad_owner": bad_owner, "attribution_ok": not bad_owner,
            "answer_endswith_sent_end": bool(answer and answer[-1] in G.SENT_END)}


def facts_sig(rep):
    return sorted((str(f.get("family")), str(f.get("raw")), bool(f.get("hit"))) for f in rep.get("facts", []))


def fact_hit_keys(rep):
    return sorted((str(f.get("family")), str(f.get("raw"))) for f in rep.get("facts", []) if f.get("hit"))


def start_sampler(tag):
    flag = OUT / ("_m5c_stop_%s.flag" % tag)
    peak = OUT / ("_m5c_peak_%s.txt" % tag)
    for x in (flag, peak):
        try:
            x.unlink()
        except FileNotFoundError:
            pass
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(E.SAMPLER),
           "-Flag", str(flag), "-Out", str(peak)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         encoding="utf-8", errors="replace")
    time.sleep(0.2)
    return {"proc": p, "flag": flag, "peak": peak}


def stop_sampler(s):
    try:
        s["flag"].write_text("done", encoding="utf-8")
    except OSError:
        pass
    try:
        s["proc"].communicate(timeout=15)
    except subprocess.TimeoutExpired:
        pass
    try:
        return round(float(s["peak"].read_text().strip()) / (1024 ** 3), 4)
    except Exception:  # noqa: BLE001
        return None


def open_scenario_engine():
    t0 = time.perf_counter()
    eng = E.open_engine()
    # E.open_engine() does not declare kvshim_ask_at; without argtypes ctypes
    # treats a real engine handle as a C int and raises OverflowError.
    eng.lib.kvshim_ask_at.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    eng.lib.kvshim_ask_at.restype = ctypes.c_int
    P.bind_raw(eng)
    meta = E.meta_from_log(eng, t0)
    meta["pid"] = os.getpid()
    return eng, meta


def answer_one(eng, seq, question, pos, n_predict, scenario, tag, peak_gib=None):
    t0 = time.perf_counter()
    nb = int(eng.n_tokens(seq))
    pb = int(eng.pos_max(seq))
    rc, ans = D2.ask_native(eng, seq, question, pos, n_predict)
    el = round(time.perf_counter() - t0, 3)
    na = int(eng.n_tokens(seq))
    pa = int(eng.pos_max(seq))
    ev = sentence_eval(ans, question)
    rec = {"scenario": scenario, "tag": tag, "question": question,
           "answer": ans, "answer_sha16": hashlib.sha256(ans.encode("utf-8")).hexdigest()[:16],
           "answer_chars": len(ans), "n_sentences": ev["n_sentences"],
           "n_sentences_counted": ev["n_sentences_counted"],
           "sentences": ev["sentences"], "counts": ev["counts"],
           "tail_idx": ev["tail_idx"], "excluded": ev["excluded"],
           "no_fact": ev["no_fact"], "bad_owner": ev["bad_owner"],
           "attribution_ok": ev["attribution_ok"],
           "answer_endswith_sent_end": ev["answer_endswith_sent_end"],
           "judge_verdict": ev["rep"].get("verdict"), "judge_branch": ev["rep"].get("branch"),
           "judge_u": ev["rep"].get("ngram", {}).get("u"),
           "near_threshold": bool(ev["rep"].get("near_threshold", False)),
           "n_predict_requested": n_predict, "ask_rc": rc,
           "n_tokens_before": nb, "n_tokens_after": na, "n_tokens_delta": na - nb,
           "pos_before": pb, "pos_after": pa, "pos_asked": pos,
           "elapsed_s": el, "peak_gib": peak_gib,
           "events": [], "events_note": "引擎无事件通道；ask_rc/n_tokens_delta 记录本次调用",
           "_rep": ev["rep"]}
    return rec


def child_main(mode, save_path, child_out):
    os.environ.setdefault("PYTHONUTF8", "1")
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    layout = build_layout(manifest)
    eng, meta = open_scenario_engine()
    out = {"mode": mode, "device": meta, "geometry": None, "error": None}
    try:
        if not meta.get("vulkan_imported") or meta.get("n_gpu_layers_readback") != 36:
            out["error"] = "device self-proof failed"
            out["status"] = "未接上（装置）"
        else:
            if mode == "s8_a":
                out["geometry"] = place(eng, layout)
                pos = 4096
                rc, ans = D2.ask_native(eng, P.LIVE, S8_Q, pos, N_PREDICT_S8A)
                nb = int(eng.n_tokens(P.LIVE)); pa = int(eng.pos_max(P.LIVE))
                ns = int(eng.save(P.LIVE, str(save_path)))
                out.update({"answer": ans, "answer_sha16": hashlib.sha256(ans.encode("utf-8")).hexdigest()[:16],
                            "ask_rc": rc, "pos_asked": pos, "n_tokens_saved": nb,
                            "pos_saved": pa, "save_return": ns,
                            "save_sha16": sha16(save_path) if os.path.exists(save_path) else None,
                            "save_bytes": os.path.getsize(save_path) if os.path.exists(save_path) else None})
                out["status"] = "completed" if ns > 0 else "未接上（save 返回 ≤0）"
            elif mode == "s8_b":
                if not os.path.exists(save_path):
                    out["error"] = "save file missing"
                    out["status"] = "未接上（装置）"
                else:
                    n0 = int(eng.n_tokens(P.LIVE))
                    lr = int(eng.load_strict(P.LIVE, str(save_path)))
                    out["load_return"] = lr
                    out["n_tokens_after_load"] = int(eng.n_tokens(P.LIVE))
                    out["pos_after_load"] = int(eng.pos_max(P.LIVE))
                    out["n_tokens_before_load"] = n0
                    pos = int(eng.pos_max(P.LIVE)) + 1
                    rc, ans = D2.ask_native(eng, P.LIVE, S8_Q, pos, N_PREDICT)
                    out.update({"answer": ans, "answer_sha16": hashlib.sha256(ans.encode("utf-8")).hexdigest()[:16],
                                "ask_rc": rc, "pos_asked": pos,
                                "n_tokens_after_ask": int(eng.n_tokens(P.LIVE)),
                                "pos_after_ask": int(eng.pos_max(P.LIVE))})
                    out["status"] = "completed" if lr >= 0 else "未接上（load 返回 <0）"
            else:
                out["error"] = "unknown child mode"
                out["status"] = "未接上（装置）"
    except Exception as e:  # noqa: BLE001
        out["error"] = type(e).__name__ + ": " + str(e)
        out["status"] = "未接上（装置）"
    finally:
        try:
            eng.close()
        except Exception:  # noqa: BLE001
            pass
    write_json_atomic(child_out, out)
    print("M5CHILD " + json.dumps(out, ensure_ascii=False))
    return 0


def run_child(mode, save_path):
    OUT.mkdir(parents=True, exist_ok=True)
    child_out = OUT / ("_m5c_child_%s.json" % mode)
    cmd = [sys.executable, str(Path(__file__).resolve()), "--child", mode,
           "--save", str(save_path), "--child-out", str(child_out)]
    p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    try:
        so, se = p.communicate(timeout=SCENARIO_TIMEOUT)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        STOP_GLOBAL.write_text("timeout", encoding="utf-8")
        so, se, rc = "", "timeout", None
    if child_out.exists():
        try:
            data = json.load(open(child_out, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {"mode": mode, "status": "未接上（child output parse）", "error": "parse"}
    else:
        data = {"mode": mode, "status": "未接上（child 无输出）", "error": (se or "")[-1000:]}
    data["_child_exit"] = rc
    data["_child_stdout_tail"] = (so or "")[-1000:]
    data["_child_stderr_tail"] = (se or "")[-1000:]
    return data


def gate_check():
    g = E.gate_values()
    g["prereg_sha16"] = sha16(PREREG); g["prereg_ok"] = g["prereg_sha16"] == PREREG_SHA and PREREG.stat().st_size == PREREG_BYTES
    g["judge_sha16"] = sha16(JUDGE); g["judge_ok"] = g["judge_sha16"] == JUDGE_SHA and JUDGE.stat().st_size == JUDGE_BYTES
    g["dll_sha16"] = sha16(DLL); g["dll_ok"] = g["dll_sha16"] == DLL_SHA and os.path.getsize(DLL) == DLL_BYTES
    g["model_bytes"] = os.path.getsize(MODEL); g["model_ok"] = g["model_bytes"] == MODEL_BYTES
    g["free_ram_ok"] = (g.get("free_ram_kb") or 0) >= 8388608
    g["vram_baseline_ok"] = g.get("vram_baseline_gib") is not None and g["vram_baseline_gib"] <= 0.5
    g["gpu_procs_ok"] = g.get("gpu_procs_gt256mb") == 0
    g["browsers_ok"] = g.get("browser_or_code_procs") == 0
    g["gate_ok"] = all(g[k] for k in ("prereg_ok", "judge_ok", "dll_ok", "model_ok", "free_ram_ok",
                                      "vram_baseline_ok", "gpu_procs_ok", "browsers_ok"))
    return g


def known_controls():
    texts = source_texts()
    blob = G.prep("".join(texts[k] for k in ("home", "project", "habit")))
    out = []
    for cid, text, gn, u_exp, v_exp, note in G.CONTROLS:
        if cid not in ("C6", "C7", "C8", "C9", "C10"):
            continue
        r = G.ngram_check(text, blob)
        out.append({"id": cid, "text": text, "gram_n": r.get("gram_n"), "u": r.get("u"),
                    "verdict": r.get("verdict"), "expected": v_exp, "note": note,
                    "known_fp": r.get("verdict") == "unsupported"})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--child", choices=["s8_a", "s8_b"])
    ap.add_argument("--save", default=str(SAVE))
    ap.add_argument("--child-out", default="")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.child:
        return child_main(a.child, Path(a.save), Path(a.child_out))
    if not a.run:
        print("use --run to execute; --child is internal")
        return 2

    t_start = time.time()
    at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    for x in (STOP_GLOBAL,):
        try:
            x.unlink()
        except FileNotFoundError:
            pass

    gate_before = gate_check()
    host_before = E.host_check("before_m5c")
    minidumps_before = E.host_check("before_m5c_dumps")
    attempts = [{"n": 1, "at": at, "status": "started",
                 "reason": "PREREG-M5-C 250dbb41; CAND only; no retry; parent no signal"}]
    art = {"schema": "m5_probe_c_v2", "task": "M5-C (c) 36-layer long generation, out-of-sample",
           "role": "CAND", "at": at, "scope": "CAND 原始输出与装置/几何/自证；不做 ADJ/JUDGE 结论",
           "prereg": {"path": str(PREREG), "sha16": sha16(PREREG), "bytes": PREREG.stat().st_size},
           "judge": {"path": str(JUDGE), "sha16": sha16(JUDGE), "bytes": JUDGE.stat().st_size,
                     "version": "v2.1", "gate": {"theta": G.THETA, "stop_sha16": G.STOP_SHA16,
                                                 "frame_sha16": G.FRAME_SHA16,
                                                 "question_clause_excluded": True,
                                                 "no_fact_rule": "branch5 |G|==0 or u>theta -> no_fact; no_fact single-listed"}},
           "prompt_template": {"turn": "\\n问：" + "{q}" + "\\n答：", "answer": "buffer after ask; no stripping",
                               "source": "tools/kvslots.py turn()"},
           "gen_params": {"n_predict": N_PREDICT, "n_predict_s8_first": N_PREDICT_S8A,
                          "sampling": "argmax_greedy", "temperature": 0, "seed_known": True,
                          "degraded": False, "n_predict_current": N_PREDICT,
                          "note": "DLL generate() argmax; no sampler"},
           "gate_before": gate_before, "host_before": host_before,
           "device": {"model": MODEL, "model_bytes": MODEL_BYTES, "dll": DLL,
                      "dll_sha16": DLL_SHA, "dll_bytes": DLL_BYTES,
                      "n_gpu_layers_input": 36, "n_ctx": 8192, "n_seq": 8, "kv": "q8_0",
                      "chat_start": 4096, "vram_gate_gib": GATE_GIB, "target_gib": TARGET_GIB,
                      "signals_sent_by_parent": False, "engines": []},
           "geometry": [], "answers": [], "peaks": [], "counts": {},
           "near_threshold": [], "known_fp_controls": [], "no_fact_undecidable": [],
           "excluded": [], "sealed": {"adj_sha16": None, "review_sha16": None,
                                      "status": "pending_ADJ_blind_labeling"},
           "rates": {"leak": {"num": None, "den": None, "status": "pending_ADJ"},
                     "false": {"num": None, "den": None, "status": "pending_ADJ"},
                     "note": "CAND 不产 ADJ 标签；两率待 ADJ 盲标后计算；禁单一准确率"},
           "s7": None, "resume": None, "attempts": attempts, "limitations": [],
           "no_single_accuracy": True, "no_final_verdict": True}

    if not gate_before["gate_ok"]:
        attempts[0]["status"] = "gate_failed"
        art["status"] = "未接上（装置不合格：开工硬闸）"
        art["four_state"] = "未接上"
        art["gate_after"] = None
        art["host_after"] = None
        art["reboot"] = None
        art["limitations"].append("开跑前 host gate 未过，未开引擎")
        write_json_atomic(ART, art)
        write_landed(art)
        print("M5C_GATE_FAIL", json.dumps(gate_before, ensure_ascii=False))
        print("M5C_ART", info(ART))
        return 0

    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    layout = build_layout(manifest)
    art["geometry_layout"] = {"cells_total": layout["cells_total"], "span_lo": layout["span_lo"],
                              "span_hi": layout["span_hi"], "segments": layout["segments"]}
    degraded = False
    over80 = 0
    aborted = False
    engine_errors = []
    all_sentences_counts = {"total": 0, "counted": 0, "supported": 0, "unsupported": 0,
                            "undecidable": 0, "no_fact": 0, "tail": 0, "empty": 0, "dup": 0}

    def absorb(rec):
        for k in all_sentences_counts:
            all_sentences_counts[k] += int(rec["counts"].get(k, 0))
        art["answers"].append(rec)
        art["near_threshold"].extend([{"scenario": rec["scenario"], "u": rec["judge_u"],
                                       "verdict": rec["judge_verdict"]}] if rec["near_threshold"] else [])
        for nf in rec["no_fact"]:
            nf = dict(nf); nf["scenario"] = rec["scenario"]
            art["no_fact_undecidable"].append(nf)
        for ex in rec["excluded"]:
            ex = dict(ex); ex["scenario"] = rec["scenario"]
            art["excluded"].append(ex)
        if not rec["attribution_ok"]:
            engine_errors.append("sentence attribution out of range: " + rec["scenario"])

    # S1-S6: one fresh engine each; one question, one generation
    for sid in ("S1", "S2", "S3", "S4", "S5", "S6"):
        if aborted:
            break
        tag = "S" + sid[1:]
        peak = None
        s = start_sampler(tag)
        t0 = time.perf_counter()
        eng = None
        try:
            eng, meta = open_scenario_engine()
            art["device"]["engines"].append(meta)
            if not meta.get("vulkan_imported") or meta.get("n_gpu_layers_readback") != 36:
                engine_errors.append("device proof failed: " + sid)
                aborted = True
                continue
            geom = place(eng, layout); art["geometry"].append(geom)
            if not geom["ok"]:
                engine_errors.append("geometry failed: " + sid)
                aborted = True
                continue
            n_predict = 128 if degraded else N_PREDICT
            rec = answer_one(eng, P.LIVE, QUESTIONS[sid], 4096, n_predict, sid, sid, None)
            rec["geometry"] = geom
            rec["device"] = meta
            absorb(rec)
            print("M5C_PROGRESS %s chars=%d elapsed=%.1f peak=%s" % (sid, len(rec["answer"]), time.perf_counter() - t0, art["answers"][-1].get("peak_gib")), flush=True)
        except Exception as e:  # noqa: BLE001
            engine_errors.append("%s: %s: %s" % (sid, type(e).__name__, e))
            aborted = True
        finally:
            if eng is not None:
                try:
                    eng.close()
                except Exception:  # noqa: BLE001
                    pass
            elapsed = time.perf_counter() - t0
            peak = stop_sampler(s)
            if art["answers"] and art["answers"][-1]["scenario"] == sid:
                art["answers"][-1]["peak_gib"] = peak
                art["answers"][-1]["elapsed_s"] = round(elapsed, 3)
                if peak is not None:
                    art["peaks"].append({"scenario": sid, "peak_gib": peak})
                    if peak > TARGET_GIB:
                        over80 += 1
                    else:
                        over80 = 0
                    if over80 >= 2 and not degraded:
                        degraded = True
                        art["gen_params"]["degraded"] = True
                        art["gen_params"]["n_predict_current"] = 128
            if elapsed > SCENARIO_TIMEOUT:
                engine_errors.append("scenario timeout: " + sid)
                STOP_GLOBAL.write_text("timeout", encoding="utf-8")
                aborted = True
            if peak is not None and peak > GATE_GIB:
                engine_errors.append("VRAM %.4f > %.1f: %s" % (peak, GATE_GIB, sid))
                STOP_GLOBAL.write_text("vram_abort", encoding="utf-8")
                aborted = True

    # S7: one fresh engine, 9 sequential turns
    if not aborted:
        s = start_sampler("S7")
        t0 = time.perf_counter()
        eng = None
        s7recs = []
        try:
            eng, meta = open_scenario_engine()
            art["device"]["engines"].append(meta)
            geom = place(eng, layout); art["geometry"].append(geom)
            if not geom["ok"]:
                engine_errors.append("geometry failed: S7"); aborted = True
            else:
                for i, q in enumerate(S7_QUESTIONS, 1):
                    if i == 1:
                        pos = 4096
                    else:
                        pos = int(eng.pos_max(P.LIVE)) + 1
                    n_predict = 128 if degraded else N_PREDICT
                    rec = answer_one(eng, P.LIVE, q, pos, n_predict, "S7-R%d" % i, "S7", None)
                    rec["geometry"] = geom
                    rec["device"] = meta
                    rec["s7_turn"] = i
                    s7recs.append(rec)
                    absorb(rec)
                    print("M5C_PROGRESS S7-R%d chars=%d elapsed=%.1f peak=%s" % (i, len(rec["answer"]), time.perf_counter() - t0, None), flush=True)
        except Exception as e:  # noqa: BLE001
            engine_errors.append("S7: %s: %s" % (type(e).__name__, e)); aborted = True
        finally:
            if eng is not None:
                try:
                    eng.close()
                except Exception:  # noqa: BLE001
                    pass
            elapsed = time.perf_counter() - t0
            peak = stop_sampler(s)
            for rec in s7recs:
                rec["elapsed_s"] = rec.get("elapsed_s")
                rec["peak_gib"] = peak
            if s7recs:
                art["peaks"].append({"scenario": "S7", "peak_gib": peak})
                if peak is not None and peak > TARGET_GIB:
                    over80 += 1
                    if over80 >= 2:
                        degraded = True
                        art["gen_params"]["degraded"] = True
                        art["gen_params"]["n_predict_current"] = 128
                elif peak is not None:
                    over80 = 0
                if peak is not None and peak > GATE_GIB:
                    engine_errors.append("VRAM %.4f > %.1f: S7" % (peak, GATE_GIB))
                    aborted = True
                if elapsed > SCENARIO_TIMEOUT:
                    engine_errors.append("scenario timeout: S7"); aborted = True
                art["s7"] = {"turns": [{"turn": r["s7_turn"], "question": r["question"],
                                         "answer_sha16": r["answer_sha16"]} for r in s7recs],
                             "r1_vs_r9": fact_compare(s7recs[0], s7recs[-1]),
                             "total_elapsed_s": round(elapsed, 3), "peak_gib": peak}

    # S8: A process save, then B process fresh load
    if not aborted:
        try:
            if SAVE.exists():
                SAVE.unlink()
            s = start_sampler("S8-A")
            chA = run_child("s8_a", SAVE)
            peakA = stop_sampler(s)
            art["device"]["engines"].append(chA.get("device") or {})
            if chA.get("geometry"):
                art["geometry"].append(chA["geometry"])
            if chA.get("status") != "completed":
                engine_errors.append("S8-A: " + str(chA.get("status") or chA.get("error")))
                aborted = True
            else:
                recA = dict(chA)
                recA.update({"scenario": "S8-A", "tag": "S8", "question": S8_Q,
                             "n_sentences": 0, "n_sentences_counted": 0,
                             "sentences": [], "counts": {k: 0 for k in all_sentences_counts},
                             "no_fact": [], "excluded": [], "bad_owner": [], "attribution_ok": True,
                             "near_threshold": False, "peak_gib": peakA, "elapsed_s": None,
                             "events": [], "events_note": "child ask"})
                # judge the child's answer in this parent, one ground call
                ev = sentence_eval(chA.get("answer", ""), S8_Q)
                recA.update({k: ev[k] for k in ("sentences", "n_sentences", "n_sentences_counted",
                                                "counts", "tail_idx", "no_fact", "excluded",
                                                "bad_owner", "attribution_ok", "answer_endswith_sent_end")})
                recA["judge_verdict"] = ev["rep"].get("verdict"); recA["judge_branch"] = ev["rep"].get("branch")
                recA["judge_u"] = ev["rep"].get("ngram", {}).get("u")
                recA["near_threshold"] = bool(ev["rep"].get("near_threshold", False))
                recA["_rep"] = ev["rep"]
                absorb(recA)
                art["peaks"].append({"scenario": "S8-A", "peak_gib": peakA})
                if peakA is not None and peakA > GATE_GIB:
                    engine_errors.append("VRAM S8-A > gate"); aborted = True

            if not aborted:
                s = start_sampler("S8-B")
                chB = run_child("s8_b", SAVE)
                peakB = stop_sampler(s)
                art["device"]["engines"].append(chB.get("device") or {})
                if chB.get("status") != "completed":
                    engine_errors.append("S8-B: " + str(chB.get("status") or chB.get("error")))
                    aborted = True
                else:
                    recB = dict(chB)
                    recB.update({"scenario": "S8-B", "tag": "S8", "question": S8_Q,
                                 "n_sentences": 0, "n_sentences_counted": 0,
                                 "sentences": [], "counts": {k: 0 for k in all_sentences_counts},
                                 "no_fact": [], "excluded": [], "bad_owner": [], "attribution_ok": True,
                                 "near_threshold": False, "peak_gib": peakB, "elapsed_s": None,
                                 "events": [], "events_note": "child load+ask"})
                    ev = sentence_eval(chB.get("answer", ""), S8_Q)
                    recB.update({k: ev[k] for k in ("sentences", "n_sentences", "n_sentences_counted",
                                                    "counts", "tail_idx", "no_fact", "excluded",
                                                    "bad_owner", "attribution_ok", "answer_endswith_sent_end")})
                    recB["judge_verdict"] = ev["rep"].get("verdict"); recB["judge_branch"] = ev["rep"].get("branch")
                    recB["judge_u"] = ev["rep"].get("ngram", {}).get("u")
                    recB["near_threshold"] = bool(ev["rep"].get("near_threshold", False))
                    recB["_rep"] = ev["rep"]
                    absorb(recB)
                    art["peaks"].append({"scenario": "S8-B", "peak_gib": peakB})
                    art["resume"] = resume_record(chA, chB, recA.get("_rep"), recB.get("_rep"))
                    if not art["resume"]["selfproof_ok"]:
                        engine_errors.append("S8 save/load self-proof mismatch")
                    if peakB is not None and peakB > GATE_GIB:
                        engine_errors.append("VRAM S8-B > gate"); aborted = True
        except Exception as e:  # noqa: BLE001
            engine_errors.append("S8: %s: %s" % (type(e).__name__, e)); aborted = True

    # pull private rep fields out of JSON-facing answers
    for rec in art["answers"]:
        rec.pop("_rep", None)
    art["counts"] = all_sentences_counts
    art["peaks_all"] = art["peaks"]
    art["device"]["peak_gib"] = max([p["peak_gib"] for p in art["peaks"] if p.get("peak_gib") is not None] or [None]) if art["peaks"] else None
    art["device"]["three_proof_ok"] = bool(art["device"]["engines"]) and all(
        e.get("n_gpu_layers_readback") == 36 and e.get("vulkan_imported") is True for e in art["device"]["engines"])
    art["device"]["all_offloaded_lines"] = [e.get("offloaded_log_line") for e in art["device"]["engines"]]
    art["known_fp_controls"] = known_controls()
    art["host_after"] = E.host_check("after_m5c")
    art["gate_after"] = gate_check()
    art["reboot"] = E.derive_host_state(host_before, art["host_after"])
    art["voided_by_reboot"] = bool(art["reboot"].get("boot_changed"))
    art["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    art["elapsed_total_s"] = round(time.time() - t_start, 3)
    art["attempts"][0]["finished_at"] = art["finished_at"]
    art["attempts"][0]["status"] = "aborted" if (aborted or engine_errors) else "completed"
    art["attempts"][0]["reason"] = ("; ".join(engine_errors)[:1500] if engine_errors else
                                    "8 scenarios attempted; CAND outputs written; ADJ pending")
    art["limitations"] = [
        "CAND 侧只产原始输出与句级归属；ADJ 盲标未封存，两率未计算，不写通过/未通过。",
        "未做 kill 子臂（永久未做）；不覆盖掉电/驱动级 bug check/θ 已校准性。",
        "S7 各轮共享一个 sampler，peak 为整段 S7 的峰值；S8-A/B 分进程各自采样。",
        "events 通道不存在；以 ask_rc/n_tokens_delta 记录每次调用。",
        "S8 首次 n_predict=128，恢复段=192（若降档则 128）；未做任何重试/补生成。",
    ]
    if degraded:
        art["limitations"].append("峰值 >8.0 GiB 连续 2 场景，已按 §8 降 n_predict 192→128；两率须注明降档。")
    if engine_errors:
        art["limitations"].append("engine_errors: " + "; ".join(engine_errors)[:1500])
    if art["voided_by_reboot"]:
        art["status"] = "判据作废（蓝屏/重启）"; art["four_state"] = "判据作废"
    elif aborted or engine_errors:
        art["status"] = "未接上（装置/自证失败）"; art["four_state"] = "未接上"
    else:
        art["status"] = "CAND 已落盘；ADJ 待盲标"; art["four_state"] = "未接上"
    art["answer_count"] = len(art["answers"])
    art["scenario_count"] = len({a["scenario"].split("-")[0] for a in art["answers"]})
    write_json_atomic(ART, art)
    write_landed(art)
    print("M5C_STATUS " + json.dumps({"status": art["status"], "answers": len(art["answers"]),
                                      "elapsed_s": art["elapsed_total_s"], "errors": engine_errors,
                                      "device_peak": art["device"].get("peak_gib")}, ensure_ascii=False))
    print("M5C_ART " + json.dumps(info(ART), ensure_ascii=False))
    print("M5C_LANDED " + json.dumps(info(LANDED), ensure_ascii=False))
    return 0


def fact_compare(rec_a, rec_b):
    ha = fact_hit_keys(rec_a.get("_rep", {}))
    hb = fact_hit_keys(rec_b.get("_rep", {}))
    return {"r1_hit_facts": ha, "r9_hit_facts": hb, "fact_kept": ha == hb,
            "r1_verdict": rec_a.get("judge_verdict"), "r9_verdict": rec_b.get("judge_verdict")}


def resume_record(a, b, repA, repB):
    pos_saved = a.get("pos_saved"); pos_after = b.get("pos_after_load")
    n_saved = a.get("n_tokens_saved"); n_after = b.get("n_tokens_after_load")
    ha = fact_hit_keys(repA or {}); hb = fact_hit_keys(repB or {})
    return {"save_path": str(SAVE), "save_sha16": a.get("save_sha16"), "save_bytes": a.get("save_bytes"),
            "load_return": b.get("load_return"), "pos_saved": pos_saved, "pos_after_load": pos_after,
            "n_tokens_saved": n_saved, "n_tokens_after": n_after,
            "pos_equal": pos_saved is not None and pos_saved == pos_after,
            "n_tokens_equal": n_saved is not None and n_saved == n_after,
            "a_hit_facts": ha, "b_hit_facts": hb, "fact_kept": ha == hb,
            "selfproof_ok": bool(pos_saved is not None and pos_saved == pos_after and
                                 n_saved is not None and n_saved == n_after),
            "status": "selfproof_ok" if (pos_saved == pos_after and n_saved == n_after) else "未接上（装置）"}


def write_landed(art):
    files = {}
    for name, p in (("M5C-36-r1.json", ART),
                    ("M5C-36-resume-S8.kvmem", SAVE)):
        if p.exists():
            files[name] = info(p)
    led = {"schema": "m5_c_landed_v1",
           "task": "M5-C (c) CAND side",
           "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "prereg": {"path": str(PREREG), "sha16": sha16(PREREG), "bytes": PREREG.stat().st_size},
           "judge": {"path": str(JUDGE), "sha16": sha16(JUDGE), "bytes": JUDGE.stat().st_size,
                     "version": "v2.1"},
           "artifact": info(ART) if ART.exists() else None,
           "files": files,
           "status": art.get("status"), "four_state": art.get("four_state"),
           "attempts": art.get("attempts"), "limitations": art.get("limitations"),
           "no_final_verdict": True,
           "sealed": art.get("sealed"),
           "notes": "CAND 产物；ADJ 盲标与两率由 ADJ/LEAD 接续。台账不含两率结论。"}
    write_json_atomic(LANDED, led)


if __name__ == "__main__":
    sys.exit(main())