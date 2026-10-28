# -*- coding: utf-8 -*-
"""双基线回归比对（rev7-auditor 裁决版）：
  主门：v12-regression ∩ v11(partial, 22 条) 逐例一致（忽略纯时延；答案/结构/拒答须一致）
  辅门：v12-regression vs v10(全量 81) 逐例 diff，归因；缺 v10→v11 变更清单 → PASS_WITH_NOTES + 全量 diff
       出现无法归因的结构性新差异 → FAIL；辅门不得抵消主门 FAIL。
输出：out/TRAINING-EVAL-v12-vs-v11-main.json、out/TRAINING-EVAL-v12-vs-v10.json（不覆盖基线）。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "out"
NEW = OUT / "TRAINING-EVAL-v12-regression.json"
V11 = OUT / "TRAINING-EVAL-v11.json"
V10 = OUT / "TRAINING-EVAL-v10.json"
MAIN_OUT = OUT / "TRAINING-EVAL-v12-vs-v11-main.json"
AUX_OUT = OUT / "TRAINING-EVAL-v12-vs-v10.json"

THINK = re.compile(r"<\|?/?\s*think\s*\|?>", re.I)


def norm_answer(a):
    a = THINK.sub("", str(a or ""))
    a = re.sub(r"\s+", "", a)
    return a.strip("。！？!?；;，,、 ")


def state_class(r):
    a = r.get("actual") or {}
    if a.get("refused"):
        return "no_evidence"
    st = str(a.get("state") or "")
    if st in ("identity", "capability", "smalltalk", "ack", "web"):
        return st
    if a.get("block_ids"):
        return "memory_hit"
    return "general"


def rowof(r):
    a = r.get("actual") or {}
    return {"pass": bool(r.get("pass")), "refused": bool(a.get("refused")),
            "state_class": state_class(r), "blocks_present": bool(a.get("block_ids")),
            "answer": str(a.get("answer") or ""), "answer_norm": norm_answer(a.get("answer")),
            "category": r.get("category"), "input": r.get("input"), "id": r["id"],
            "error": a.get("error")}


def load(p):
    if not p.exists():
        return None, {}
    d = json.loads(p.read_text(encoding="utf-8"))
    return d, {r["id"]: rowof(r) for r in d.get("results") or []}


def diff_fields(old, new):
    out = {}
    for k in ("pass", "refused", "state_class", "blocks_present", "answer_norm"):
        if old.get(k) != new.get(k):
            out[k] = {"old": old.get(k), "new": new.get(k)}
    return out


def main():
    new_doc, new = load(NEW)
    v11_doc, v11 = load(V11)
    v10_doc, v10 = load(V10)
    if new_doc is None:
        print(json.dumps({"status": "FAIL", "reason": "v12-regression missing: %s" % NEW},
                         ensure_ascii=False))
        return 2
    # ---------- 主门 ----------
    overlap11 = sorted(set(v11) & set(new))
    main_rows, main_mismatch = [], []
    for cid in overlap11:
        d = diff_fields(v11[cid], new[cid])
        d.pop("answer_norm", None) if not d.get("answer_norm") else None
        # 答案差异单独记：纯文本差异也计入不一致（裁决：只忽略时延）
        if norm_answer(v11[cid]["answer"]) != norm_answer(new[cid]["answer"]):
            d["answer_text"] = {"old": v11[cid]["answer"][:160], "new": new[cid]["answer"][:160]}
        row = {"id": cid, "category": new[cid]["category"], "input": new[cid]["input"],
               "consistent": not d, "diff": d,
               "old_pass": v11[cid]["pass"], "new_pass": new[cid]["pass"]}
        main_rows.append(row)
        if d:
            main_mismatch.append(row)
    main_missing = sorted(set(v11) - set(new))
    main_verdict = "PASS" if overlap11 and not main_mismatch and not main_missing else "FAIL"
    main_doc = {
        "schema": "training_eval_diff_v11_main_v1",
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "gate": "v12-regression ∩ v11(partial) must be consistent (ignore latency only)",
        "inputs": {
            "new": {"path": str(NEW), "sha256": __import__("hashlib").sha256(NEW.read_bytes()).hexdigest(),
                    "partial": new_doc.get("partial"), "n": len(new)},
            "v11": {"path": str(V11), "sha256": __import__("hashlib").sha256(V11.read_bytes()).hexdigest(),
                    "partial": v11_doc.get("partial"), "n": len(v11)},
        },
        "n_overlap": len(overlap11), "n_consistent": len(overlap11) - len(main_mismatch),
        "verdict": main_verdict, "mismatches": main_mismatch,
        "missing_in_new": main_missing, "rows": main_rows,
        "note": "v11 为 partial(22)；主门只判重叠集。任一不一致/缺例 ⇒ FAIL。",
    }
    MAIN_OUT.write_text(json.dumps(main_doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # ---------- 辅门 ----------
    overlap10 = sorted(set(v10) & set(new))
    # 用 v10→v11 重叠观察到的“已知变更”类别（若 v11 覆盖该 category）
    observed = {}
    for cid in sorted(set(v10) & set(v11)):
        d = diff_fields(v10[cid], v11[cid])
        cat = v11[cid]["category"]
        observed.setdefault(cat, set())
        if d:
            observed[cat].add("has_diff")
    aux_rows, unknown, known = [], [], []
    for cid in overlap10:
        old, cur = v10[cid], new[cid]
        d = diff_fields(old, cur)
        if not d:
            aux_rows.append({"id": cid, "category": cur["category"],
                             "input": cur["input"], "class": "no_diff", "diff": {}})
            continue
        structural = {k: v for k, v in d.items() if k != "answer_norm"}
        cat = cur["category"]
        if structural:
            # 结构性差异：若该 category 在 v10→v11 中观察到过差异，标“已知类别变更”，否则 unknown
            if observed.get(cat):
                klass = "known_category_change(structural)"
                known.append({"id": cid, "class": klass, "diff": d})
            else:
                klass = "unknown_structural_new_diff"
                unknown.append({"id": cid, "class": klass, "diff": d})
        else:
            klass = "answer_text_only"
            (known if observed.get(cat) else unknown).append({"id": cid, "class": klass, "diff": d})
        aux_rows.append({"id": cid, "category": cat, "input": cur["input"],
                         "class": klass, "diff": d})
    aux_verdict = "FAIL" if unknown else ("PASS_WITH_NOTES" if (known or aux_rows) else "PASS")
    aux_doc = {
        "schema": "training_eval_diff_v10_aux_v1",
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "gate": "v12 vs v10(81) 逐例 diff 归因；未知结构性新差异 ⇒ FAIL；缺官方变更清单 ⇒ 辅门记 PASS_WITH_NOTES 并附全量 diff",
        "inputs": {
            "new": {"path": str(NEW), "sha256": __import__("hashlib").sha256(NEW.read_bytes()).hexdigest()},
            "v10": {"path": str(V10), "sha256": __import__("hashlib").sha256(V10.read_bytes()).hexdigest(),
                    "partial": v10_doc.get("partial"), "n": len(v10)},
        },
        "change_list_status": "missing_official_v10_to_v11_change_list; observed categories from overlap=%s" % sorted(observed),
        "n_overlap": len(overlap10), "n_no_diff": sum(1 for r in aux_rows if r["class"] == "no_diff"),
        "n_known": len(known), "n_unknown": len(unknown),
        "verdict": aux_verdict, "unknown_diffs": unknown, "known_diffs": known, "rows": aux_rows,
    }
    AUX_OUT.write_text(json.dumps(aux_doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"main": {"verdict": main_verdict, "overlap": len(overlap11),
                               "mismatches": len(main_mismatch), "missing": main_missing},
                      "aux": {"verdict": aux_verdict, "overlap": len(overlap10),
                              "no_diff": aux_doc["n_no_diff"], "known": len(known),
                              "unknown": len(unknown)}},
                     ensure_ascii=False))
    return 0 if main_verdict == "PASS" else 3


if __name__ == "__main__":
    sys.exit(main())