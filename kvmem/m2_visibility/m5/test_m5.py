# -*- coding: utf-8 -*-
"""M5 regression + evidence per M5-CRITERIA.md (frozen) incl. addendum 9.1 R1-R5.

Two input forms (R1):  I1 = first sentence,  I2 = full model output (self Q/A continuation).
Invariance (R1): the same content must reach the same verdict in both forms.

  python -X utf8 kvmem/m2_visibility/m5/test_m5.py
"""
import hashlib, json, os, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m5_ground as G                                            # noqa: E402

M2 = os.path.join(HERE, "..", "m2")
NP64 = os.path.join(HERE, "..", "runs_m14b", "out")
MOUNTED = ["home", "project", "habit"]
IDS = ["addr", "project", "habit", "plate"]
CN = {"addr": "住址", "project": "项目", "habit": "习惯", "plate": "车牌"}


def load(p):
    return json.load(open(p, encoding="utf-8"))


def first_sentence(t):
    for i, ch in enumerate(t):
        if ch in "。！？":
            return t[:i + 1]
        if ch == "\n":
            return t[:i]
    return t


def main():
    r1 = load(os.path.join(M2, "run_m2_r1.json"))
    neg = load(os.path.join(M2, "run_m2_negctl_r1.json"))
    qs = {"addr": ("我住在哪？", r1["asks"][0]["answer"]),
          "project": ("项目什么时候上线？", r1["asks"][1]["answer"]),
          "habit": ("我喝咖啡有什么习惯？", r1["asks"][2]["answer"]),
          "plate": ("我的车牌号是多少？", neg["asks"][3]["answer"])}
    want = {"addr": "supported", "project": "supported",
            "habit": "supported", "plate": "unsupported"}
    out = {"schema": "m5_evidence_v2", "criteria": G.CRITERIA,
           "criteria_addendum": "§9.1 R1-R5 (added after data)",
           "mounted": MOUNTED,
           "input_forms": {"I1": "first sentence", "I2": "full model output"}}

    con = sqlite3.connect(os.path.join(HERE, "memory.db"))
    out["source_verification"] = [
        {"block_id": b, "cells": c, "sha256_db": s, "sha256_disk": d, "match": bool(m), "text": t}
        for b, c, s, d, m, t in con.execute(
            "SELECT block_id, cells, sha256, sha256_disk, sha_match, source_text "
            "FROM blocks ORDER BY cells")]
    con.close()

    print("## §7.2 memory.db 源校验")
    for s in out["source_verification"]:
        print("  %-8s cells=%-3d sha16=%s disk=%s match=%s"
              % (s["block_id"], s["cells"], s["sha256_db"][:16], s["sha256_disk"][:16], s["match"]))

    print("\n## §6 四例 × 两种输入形态（R1）")
    print("| 例 | I1 硬事实 | I1 | I2 硬事实 | I2 | 形态不变 |")
    print("|---|---|---|---|---|---|")
    cases = []
    for cid in IDS:
        q, full = qs[cid]
        row = {"case": cid, "label": CN[cid], "question": q,
               "answer_I2": full, "answer_I1": first_sentence(full),
               "I1_sha256": hashlib.sha256(first_sentence(full).encode()).hexdigest()}
        for form in ("I1", "I2"):
            a = row["answer_" + form]
            r = G.ground(a, MOUNTED, q)
            row[form] = {"verdict": r["verdict"], "expected": want[cid],
                         "facts": r["facts"], "unhit": r["unhit"], "exempt": r["exempt"],
                         "rewritten": r["rewritten"],
                         "rewritten_is_original": r["rewritten_is_original"],
                         "recheck": r.get("recheck"),
                         "multiset_note": r.get("multiset_note"),
                         "pass": (r["verdict"] == want[cid]
                                  and (r["rewritten"] == a) == (want[cid] == "supported"))}
        row["invariant"] = row["I1"]["verdict"] == row["I2"]["verdict"]
        cases.append(row)
        f = lambda x: " ".join("%s:%s%s" % (t["family"], t["raw"], "✓" if t["hit"] else "✗")
                               for t in x["facts"]) or "无"
        print("| %s | %s | **%s** | %s | **%s** | %s |"
              % (CN[cid], f(row["I1"]), row["I1"]["verdict"],
                 f(row["I2"]), row["I2"]["verdict"], row["invariant"]))
    out["four_cases"] = cases

    print("\n## 车牌例重写（两形态）")
    plate = cases[3]
    print("  I1 → %r" % plate["I1"]["rewritten"])
    print("  I2 → %r" % plate["I2"]["rewritten"])
    for form in ("I1", "I2"):
        print("  %s 复检 %s" % (form, json.dumps(plate[form]["recheck"], ensure_ascii=False)))

    print("\n## §6 三边界")
    bnd = []
    for tag, q, a, mounted, w in [
            ("日期等价/三月十四号", "项目什么时候上线？", "项目将在三月十四号上线。", MOUNTED, "supported"),
            ("不比中/3月15日", "项目什么时候上线？", "项目将在 3 月 15 日上线。", MOUNTED, "unsupported"),
            ("源缺失", "我住在哪？", "我住在广陵路 12 号 2 单元 602。", ["nosuch_block"], "undecidable")]:
        r = G.ground(a, mounted, q)
        bnd.append({"case": tag, "answer": a, "mounted": mounted, "verdict": r["verdict"],
                    "expected": w, "rewritten": r["rewritten"], "reason": r["reason"],
                    "pass": r["verdict"] == w})
        print("  %-18s %-12s (期望 %s) %s" % (tag, r["verdict"], w,
                                              "OK" if r["verdict"] == w else "MISMATCH"))
    out["boundary_cases"] = bnd

    print("\n## §7.3 交叉检验（np64 四跑，不预设期望）")
    cross = []
    for tag in ("E", "F", "X1", "B57"):
        p = os.path.join(NP64, "np64_%s_r1.json" % tag)
        if not os.path.exists(p):
            continue
        ans = load(p)["answers"][0]["answer"]
        r = G.ground(ans, MOUNTED, "我住在哪？")
        cross.append({"run": tag, "verdict": r["verdict"], "facts": r["facts"],
                      "unhit": r["unhit"], "rewritten": r["rewritten"]})
        print("  %-4s %-11s %s" % (tag, r["verdict"],
                                    " ".join("%s:%s%s" % (t["family"], t["raw"],
                                                          "✓" if t["hit"] else "✗")
                                             for t in r["facts"])))
    out["cross_check_np64"] = cross

    acc = {"three_supported_in_both_forms": all(c["I1"]["verdict"] == "supported"
                                               and c["I2"]["verdict"] == "supported"
                                               for c in cases[:3]),
           "plate_unsupported_in_both_forms": (cases[3]["I1"]["verdict"] == "unsupported"
                                               and cases[3]["I2"]["verdict"] == "unsupported"),
           "form_invariant_all_four": all(c["invariant"] for c in cases),
           "supported_answers_untouched": all(
               c[f]["rewritten_is_original"] for c in cases[:3] for f in ("I1", "I2")),
           "boundary_all_pass": all(x["pass"] for x in bnd),
           "false_positive": sum(1 for c in cases[:3] for f in ("I1", "I2")
                                 if c[f]["verdict"] != "supported"),
           "false_negative": sum(1 for f in ("I1", "I2") if cases[3][f]["verdict"] == "supported")}
    acc["all_pass"] = all([acc["three_supported_in_both_forms"],
                           acc["plate_unsupported_in_both_forms"],
                           acc["form_invariant_all_four"],
                           acc["supported_answers_untouched"],
                           acc["boundary_all_pass"]])
    out["acceptance"] = acc
    json.dump(out, open(os.path.join(HERE, "evidence_m5.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2, default=str)
    print("\nacceptance:", json.dumps(acc, ensure_ascii=False))
    return 0 if acc["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
