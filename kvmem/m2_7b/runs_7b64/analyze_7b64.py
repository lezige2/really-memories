# -*- coding: utf-8 -*-
"""Mechanical F (§2) then P (§1) per BLIND-CHECK-7B64.md, plus the union of §6 fields."""
import hashlib, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P

def sha(x): return hashlib.sha256((x or "").encode("utf-8")).hexdigest()
def load(p): return json.load(open(p, encoding="utf-8"))

FIX = load(os.path.join(ROOT, "kvmem", "m2_visibility", "fixtures.json"))
BLOCKTEXT = {"home": P.FULL["home"]["text"], "project": P.FULL["project"]["text"],
             "habit": P.FULL["habit"]["text"],
             "pp18": FIX["blocks"]["variant"]["project_paraphrase18"]["text"]}
RES = ["住", "小区", "家", "地址", "门牌", "单元", "楼", "搬家"]
FOREIGN = ["蓝鲸", "鲸", "三月十四", "三月十四号", "3月14", "3月 14", "上线",
           "美式", "咖啡", "不加糖"]
SPLIT = re.compile(r"[。！？\n]")

def sentences(text):
    out, start = [], 0
    for m in SPLIT.finditer(text):
        out.append((start, text[start:m.end()]))
        start = m.end()
    if start < len(text):
        out.append((start, text[start:]))
    return out

def f_form(ans):
    """§2.1 -> (verdict, kind, breakdown_offset or None)"""
    flat = ans.replace("\\_", "_").replace("＿", "_")
    for m in re.finditer(r"_{2,}", flat):
        return "崩坏", "F1 填空模板(下划线)", m.start()
    if "填空" in flat:
        return "崩坏", "F1 填空模板(含'填空')", flat.index("填空")
    if re.search(r"A[.、].{0,20}?B[.、]", flat):
        m = re.search(r"A[.、]", flat)
        return "崩坏", "F1 选项枚举", m.start()
    sents = [s for _, s in sentences(ans) if len(s.strip()) >= 6]
    seen = {}
    for off, s in sentences(ans):
        k = s.strip()
        if len(k) >= 6:
            if k in seen:
                return "崩坏", "F2 退化复读(整句重复)", off
            seen[k] = off
    if ans.count("问：") >= 2:
        q = [s for _, s in sentences(ans) if "问：" in s]
        a = [s for _, s in sentences(ans) if "答：" in s]
        for qq in q:
            qs = set(qq)
            for aa in a:
                as_ = set(aa)
                if qs and as_ and len(qs & as_) / len(qs | as_) >= 0.8:
                    return "崩坏", "F2 退化复读(答句复述问句 Jaccard>=0.8)", ans.index(aa)
    grams = {}
    for i in range(len(ans) - 7):
        g = ans[i:i + 8]
        grams[g] = grams.get(g, 0) + 1
    worst = max(grams.items(), key=lambda kv: kv[1]) if grams else ("", 0)
    if worst[1] >= 3:
        return "崩坏", "F2 退化复读(8-gram 出现 %d 次: %r)" % (worst[1], worst[0]), ans.index(worst[0])
    if "\ufffd" in ans:
        return "崩坏", "F3 不可读(U+FFFD)", ans.index("\ufffd")
    if len(ans) < 6:
        return "崩坏", "F3 不可读(长度<6)", 0
    if ans and sum(1 for c in ans if c.isspace()) / len(ans) > 0.6:
        return "崩坏", "F3 不可读(空白占比>0.6)", 0
    return "可读", None, None

def p_verdict(ans):
    form, kind, cut = f_form(ans)
    T = ans if cut is None else ans[:cut]
    covered = {}
    for name, txt in BLOCKTEXT.items():
        for f in FOREIGN:
            if f in txt:
                covered.setdefault(f, set()).add(name)
    sents = sentences(T) if T else []
    foreign_in_T = [(f, [n for n in covered.get(f, set())]) for f in FOREIGN if f in T]
    if not T.strip() or not sents:
        return form, kind, cut, {"P": "NA", "why": "T 为空(崩坏起点在第 1 句内或无内容)",
                                 "T": T}
    if not foreign_in_T:
        return form, kind, cut, {"P": "NA", "why": "T 内无 FOREIGN 串", "T": T,
                                 "foreign_seen_in_corpus": sorted(covered)}
    for i, (off, s) in enumerate(sents):
        hits = [f for f in FOREIGN if f in s]
        if hits and any(r in s for r in RES):
            f0 = hits[0]
            return form, kind, cut, {
                "P": 1, "hit": hits, "sentence_index": i, "sentence": s,
                "covered_blocks": sorted(covered.get(f0, [])),
                "self_corrected": any(k in T for k in ("哦不对", "我应该说", "不是…而是", "哦，不对")),
                "T": T}
    return form, kind, cut, {"P": 0, "why": "有 FOREIGN 但无同句 RES", "sentences_in_T": T}

RUNS = [("E", "iso_dup4"), ("F", "iso_fac_pp18"), ("X1", "iso_x1_57copy"), ("B57", "iso_fac_nb57")]
H24 = {"E": os.path.join(ROOT, "kvmem/m2_visibility/runs_t031/t031_e_dup4_samedriver_r1.json"),
       "F": os.path.join(ROOT, "kvmem/m2_visibility/runs_t031/t031_f_pp18_r1.json"),
       "X1": os.path.join(ROOT, "kvmem/m2_visibility/runs_t033/x1_r1.json"),
       "B57": os.path.join(ROOT, "kvmem/m2_visibility/runs_t033/b57_r1.json")}

out = {"schema": "evidence_7b64_v1", "runs": []}
for cell, lay in RUNS:
    r1 = load(os.path.join(HERE, "out", cell + "_r1.json"))
    r2 = load(os.path.join(HERE, "out", cell + "_r2.json"))
    a1, a2 = r1["answers"][0]["answer"], r2["answers"][0]["answer"]
    h24 = load(H24[cell])["answers"][0]["answer"]
    form, kind, cut, pv = p_verdict(a1)
    form2, kind2, cut2, pv2 = p_verdict(a2)
    rec = {"cell": cell, "layout": lay,
           "answer_r1": a1, "sha256_r1": sha(a1),
           "answer_r2": a2, "sha256_r2": sha(a2),
           "two_runs_identical": a1 == a2,
           "answer24": h24, "sha256_24": sha(h24),
           "np24_is_literal_prefix_of_np64": a1.startswith(h24),
           "F_r1": {"form": form, "kind": kind, "breakdown_offset": cut},
           "F_r2": {"form": form2, "kind": kind2, "breakdown_offset": cut2},
           "P_r1": pv, "P_r2": pv2,
           "P_aggregate": (1 if (pv.get("P") == 1 or pv2.get("P") == 1)
                           else (0 if pv.get("P") == 0 or pv2.get("P") == 0 else "NA")),
           "P_unstable": pv.get("P") != pv2.get("P"),
           "schema_of_run_json": r1.get("schema"),
           "n_predict_answer": r1["runner"].get("n_predict"),
           "n_predict_control": r1["runner"].get("n_predict"),
           "control_ok": r1.get("control_ok"),
           "control_start": r1["control"].get("start"),
           "control_target_n": r1["control"].get("target_n"),
           "control_text_sha256": r1["control"].get("text_sha256"),
           "control_question_answer_lengths": [(q["segment"], q["ok"], len(q.get("answer", "")))
                                               for q in r1["control"]["questions"]],
           "geometry": {"cells_total": r1["raw"]["cell_count"],
                        "positions_min": r1["raw"]["positions_min"],
                        "positions_max": r1["raw"]["positions_max"],
                        "overlaps": r1["raw"]["overlaps"],
                        "head_gap_cells": r1["layout"].get("head_gap_cells")},
           "engine": {"model": r1["engine"].get("model"),
                      "dll_sha256_declared": r1["engine"].get("dll_sha256"),
                      "dll_sha256_measured": r1["engine"].get("loaded_dll_sha256"),
                      "loaded_path": r1["engine"].get("loaded_path"),
                      "n_ctx": r1["engine"].get("n_ctx"), "n_seq": r1["engine"].get("n_seq"),
                      "gpu": r1["engine"].get("gpu"), "kv": r1["engine"].get("kv"),
                      "bytes_per_token": r1["engine"].get("bytes_per_token")},
           "vram_before_mib": r1["runner"].get("vram_before_mib"),
           "blocks": r1["runner"]["manifest_assertion"].get("blocks")}
    out["runs"].append(rec)

out["dll_after_batch"] = "9edbafa1 (restored, double-computed)"
json.dump(out, open(os.path.join(HERE, "evidence_7b64.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2, default=str)

print("| 格 | F 形态 | 崩坏起点 | P | 命中串 | 覆盖块 | 自我更正 | 两跑同 | 24 是前缀 |")
print("|---|---|---|---|---|---|---|---|---|")
for r in out["runs"]:
    p1 = r["P_r1"]
    print("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
        r["cell"], r["F_r1"]["form"], r["F_r1"]["breakdown_offset"],
        p1.get("P"), p1.get("hit", "-"), p1.get("covered_blocks", "-"),
        p1.get("self_corrected", "-"), r["two_runs_identical"],
        r["np24_is_literal_prefix_of_np64"]))
print()
for r in out["runs"]:
    print("--- %s (%s) ---" % (r["cell"], r["layout"]))
    print("ans64 r1: %r" % r["answer_r1"])
    print("ans24   : %r" % r["answer24"])
    print("F: %s | %s | offset=%s" % (r["F_r1"]["form"], r["F_r1"]["kind"], r["F_r1"]["breakdown_offset"]))
    print("P detail: %s" % json.dumps({k: v for k, v in r["P_r1"].items() if k != "T"},
                                       ensure_ascii=False))
    print("T (P 判定用的那段): %r" % r["P_r1"].get("T"))
    print()
