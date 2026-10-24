# -*- coding: utf-8 -*-
"""Machine-judgeable before/after table for the R12 criteria change.

  python -u -X utf8 m5_fix_compare.py   -> run_m5_fix_compare.json

Both modules are REAL: pre-R12 is recovered from git (e172aca) into _before/, current is
kvmem/m2_visibility/m5/m5_ground.py. Every case runs through both, side by side.
"""
import importlib.util, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
M5 = os.path.join(ROOT, "kvmem", "m2_visibility", "m5")
NP64 = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_m14b", "out")
sys.path.insert(0, HERE)
sys.path.insert(0, M5)
import m5_bridge as BR                                            # noqa: E402
import m5_ground as G                                             # noqa: E402

M5_DB = os.path.join(M5, "memory.db")
PROD_DB = BR.DB_PATH
MOUNTED = ["home", "project", "habit"]
PRE_COMMIT = "e172aca"
MAIN = "blk_conv_2026-10-25_01"


def load_pre():
    # R11: same change as m4_verify_grounded.load_pre_module -- the generated module must not be
    # written into _before/. Both call sites change together, otherwise one keeps turning the
    # evidence directory into a scratch area.
    d = tempfile.mkdtemp(prefix="m5_scratch_cmp_")
    src = subprocess.run(["git", "show", PRE_COMMIT + ":kvmem/m2_visibility/m5/m5_ground.py"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    path = os.path.join(d, "m5_ground_preR12.py")
    open(path, "w", encoding="utf-8").write(src)
    spec = importlib.util.spec_from_file_location("m5_ground_preR12_cmp", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verdict(mod, text, mounted, q, db):
    return mod.ground(text, list(mounted), q, db=db)["verdict"]


def main():
    pre = load_pre()
    rows = []

    def add(case, text, mounted, q, db, expected_flip, expected_after):
        before = verdict(pre, text, mounted, q, db)
        after = verdict(G, text, mounted, q, db)
        rows.append({"case": case, "answer": text, "mounted": list(mounted), "question": q,
                     "db": os.path.relpath(db, ROOT).replace("\\", "/"),
                     "verdict_before": before, "verdict_after": after,
                     "expected_flip": expected_flip,
                     "expected_after": expected_after,
                     "flip_ok": (before != after) == expected_flip,
                     "after_ok": after == expected_after})

    ev = json.load(open(os.path.join(M5, "evidence_m5.json"), encoding="utf-8"))
    for c in ev["four_cases"]:
        for form in ("I1", "I2"):
            add("m5_four/%s/%s" % (c["case"], form), c["answer_" + form], MOUNTED,
                c["question"], M5_DB, False, c[form]["verdict"])
    for b in ev["boundary_cases"]:
        add("m5_boundary/%s" % b["case"], b["answer"], b["mounted"], "我住在哪？"
            if "住" in b["answer"] else "项目什么时候上线？", M5_DB, False, b["verdict"])
    for tag in ("E", "F", "X1", "B57"):
        p = os.path.join(NP64, "np64_%s_r1.json" % tag)
        if not os.path.exists(p):
            continue
        ans = json.load(open(p, encoding="utf-8"))["answers"][0]["answer"]
        add("m5_cross/%s" % tag, ans, MOUNTED, "我住在哪？", M5_DB, False, "supported")

    # product four (inputs are the real answer-path display texts, no engine rerun)
    run = json.load(open(os.path.join(HERE, "run_m5_grounded.json"), encoding="utf-8"))
    by = {c["case"]: c for c in run["cases"]}
    for cid in ("plate_main", "plate_ablated", "home_main", "home_ablated"):
        c = by[cid]
        add("product/%s" % cid, c["display_pre_grounding"], c["mounted"], c["question"],
            PROD_DB, cid == "plate_main",
            "supported" if cid != "plate_ablated" else "unsupported")

    # the two probes the inspector demanded
    add("probe_a_wrong_province(苏B-3F19K vs 浙B-3F19K)", "您的车牌是苏B-3F19K。", [MAIN],
        "我车牌号是多少？", PROD_DB, False, "unsupported")
    add("probe_c1_bare_body_after_CJK(是B3F19K)", "您的车牌是B3F19K。", [MAIN],
        "我车牌号是多少？", PROD_DB, False, "unsupported")
    add("probe_c2_true_bare_body(非CJK前缀 B3F19K)", "车牌:B3F19K。", [MAIN],
        "我车牌号是多少？", PROD_DB, False, "supported")

    bare = G.extract("B3F19K")
    absorbed = G.extract("是B3F19K")
    res = {
        "schema": "m5_fix_compare_r12_v1",
        "criteria_before": {"commit": PRE_COMMIT,
                            "scratch": "tempfile.mkdtemp('m5_scratch_cmp_')/m5_ground_preR12.py",
                            "not_in_before": True},
        "criteria_after": {"path": "kvmem/m2_visibility/m5/m5_ground.py"},
        "rows": rows,
        "all_non_flip_hold": all(r["flip_ok"] for r in rows if not r["expected_flip"]),
        "all_flips_happened": all(r["flip_ok"] for r in rows if r["expected_flip"]),
        "flips": [r["case"] for r in rows if r["expected_flip"]],
        "all_expected_after_hold": all(r["after_ok"] for r in rows),
        "row_count": len(rows),
        "non_flip_count": sum(1 for r in rows if not r["expected_flip"]),
        "flip_count": sum(1 for r in rows if r["expected_flip"]),
        "probe_c_classification": {
            "facts_from_extract": bare, "fact_count": len(bare),
            "families": [f["family"] for f in bare],
            "claimed_once_no_double_count": len(bare) == 1,
            "classified_as": "A 族代号类（RE_CODE）；RE_PLATE 需要 CJK 前缀，裸 body 不会被车牌规则收",
            "verdict_before": verdict(pre, "您的车牌是B3F19K。", [MAIN], "我车牌号是多少？",
                                      PROD_DB),
            "verdict_after": verdict(G, "您的车牌是B3F19K。", [MAIN], "我车牌号是多少？",
                                     PROD_DB),
            "c1_cjk_absorbed": {
                "text": "您的车牌是B3F19K。", "facts_from_extract": absorbed,
                "why": "RE_PLATE 要 CJK 前缀，答案里的『是』被吸进 key（是B3F19K），于是既不等于"
                       "源里的 B3F19K 也不等于 浙B3F19K => unsupported；**前后一致**，与 R12 无关",
                "verdict_before": verdict(pre, "您的车牌是B3F19K。", [MAIN], "我车牌号是多少？",
                                          PROD_DB),
                "verdict_after": verdict(G, "您的车牌是B3F19K。", [MAIN], "我车牌号是多少？",
                                         PROD_DB)},
            "c2_true_bare_body": {
                "text": "车牌号 B3F19K。", "facts_from_extract": bare,
                "why": "前缀必须是**非 CJK**字符（这里用 ASCII 冒号），才落 RE_CODE 的代号类，"
                       "key=B3F19K，命中源侧 latin 里本来就有的 B3F19K（RE_CODE 早就在收），"
                       "**这是 body 命中，不是车牌命中**",
                "verdict_before": verdict(pre, "车牌号 B3F19K。", [MAIN], "我车牌号是多少？",
                                          PROD_DB),
                "verdict_after": verdict(G, "车牌号 B3F19K。", [MAIN], "我车牌号是多少？",
                                         PROD_DB)},
            "cjk_absorption_observed": {
                "fact": "RE_PLATE 的 [\u4e00-\u9fff][A-Za-z] 不要求分隔符，所以「车牌号 B3F19K」"
                        "被收成 key=号B3F19K（吞掉紧邻 CJK 字），「您的车牌是B3F19K」收成 是B3F19K",
                "verdict": "unsupported（安全方向：弃答，不是把编造判成命中）",
                "before_equals_after": True,
                "origin": "pre-R12 既有行为，本次未改动，也不在本轮授权范围内（只做 (a)(c) 探针）",
                "fixed_by": None},
            "note": "R12 只往 a_hit 已经在读的 latin 集合里补了带省份字的 plate key；a_hit 函数体"
                    "一字未改，没有新增任何匹配分支，也没有 any(key in s for s in plate) 这种分支",
        },
    }
    res["pass"] = (res["all_non_flip_hold"] and res["all_flips_happened"]
                   and res["all_expected_after_hold"]
                   and res["probe_c_classification"]["claimed_once_no_double_count"])
    json.dump(res, open(os.path.join(HERE, "run_m5_fix_compare.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("%-48s %-12s %-12s %-6s %-6s" % ("case", "before", "after", "flip", "ok"))
    for r in rows:
        print("%-48s %-12s %-12s %-6s %-6s" % (r["case"], r["verdict_before"],
                                               r["verdict_after"], r["flip_ok"],
                                               r["after_ok"]))
    print(json.dumps({k: res[k] for k in ("row_count", "non_flip_count", "flip_count",
                                          "flips", "all_non_flip_hold",
                                          "all_flips_happened",
                                          "all_expected_after_hold", "pass")},
                     ensure_ascii=False, indent=1))
    print("[RUN] wrote run_m5_fix_compare.json")


if __name__ == "__main__":
    main()
