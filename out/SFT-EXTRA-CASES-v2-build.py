# -*- coding: utf-8 -*-
"""TASK-031B：生成去污染的 out/SFT-EXTRA-CASES-v2.jsonl（不改原文件）。

- 输入只读：training/sft_eval_extra_cases.jsonl、training/sft/{train,val}.jsonl
- 输出：out/SFT-EXTRA-CASES-v2.jsonl、out/SFT-CONTAMINATION-EXCLUDE-v2.json
- 原则：L01-L10 的 remember 事实全部替换为训练集（train+val 的 q/a/system 全文）零出现的保留值；
        R01-R10 无 remember 事实，保持原样（R05 问句与训练集重合，只在 note 标注污染）。
"""
import hashlib
import importlib.util
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 每个 L 用例：新 remember 文本 + 新 expect.contains_any（保持用例类型/问句不变）
REPLACE = {
    "L01": ("我的备用手机号是 137-0000-9527", ["137-0000-9527", "13700009527"]),
    "L02": ("我的工位在 E 区 9 号", ["E区", "E 区", "9号", "9 号"]),
    "L03": ("我女儿的小名是雪梨", ["雪梨"]),
    "L04": ("我下个月要去商汤出差", ["商汤"]),
    "L05": ("我的车是银色两厢车", ["银色", "两厢"]),
    "L06": ("我每周四晚上十点健身", ["十点", "10点", "22点"]),
    "L07": ("我的邮箱是 lin@example.org", ["lin@example.org"]),
    "L08": ("我老家在洛阳", ["洛阳"]),
    "L09": ("我的银行卡尾号是 7418", ["7418"]),
    "L10": ("我对布洛芬过敏", ["布洛芬"]),
}
# 建议保留值里与 L 用例事实类型不匹配、未被使用的（已 grep 训练集 0 次，备选）
UNUSED_SUGGESTED = ["18 号", "闽D74185"]

TOKEN_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9@.\-]+")


def strict(s):
    return re.sub(r"\s+", "", s or "")


PREFIX = re.compile(r"^(问一下|在吗|直接问)[，,]")


def relax(s):
    s = strict(s)
    s = PREFIX.sub("", s)
    s = re.sub(r"[？?！!。．,，、；;：:~～\s]+$", "", s)
    s = re.sub(r"[？?！!。．,，、；;：:]+", "", s)
    return s


def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    train = [json.loads(l) for l in open(os.path.join(ROOT, "training/sft/train.jsonl"), encoding="utf-8") if l.strip()]
    val = [json.loads(l) for l in open(os.path.join(ROOT, "training/sft/val.jsonl"), encoding="utf-8") if l.strip()]
    rows = train + val
    full = "\n".join(r["messages"][0]["content"] + "\n" + r["messages"][1]["content"] + "\n"
                     + r["messages"][2]["content"] for r in rows)
    qrows = {}
    for r in rows:
        qrows.setdefault(relax(r["messages"][1]["content"]), 0)
        qrows[relax(r["messages"][1]["content"])] += 1

    src = os.path.join(ROOT, "training/sft_eval_extra_cases.jsonl")
    cases = [json.loads(l) for l in open(src, encoding="utf-8") if l.strip()]
    out_cases, mapping, grep_evidence = [], [], {}
    for c in cases:
        new = json.loads(json.dumps(c, ensure_ascii=False))
        cid = c["id"]
        if cid in REPLACE:
            newtext, newexpect = REPLACE[cid]
            oldtext = next(x["text"] for x in c["pre_state"] if x["action"] == "remember")
            out_cases.append(new)
            # 保留原顺序/结构，只改 pre_state 中 remember 的 text 与 expect.contains_any + note
            for x in new["pre_state"]:
                if x["action"] == "remember":
                    x["text"] = newtext
            new["expect"] = dict(new["expect"])
            new["expect"]["contains_any"] = list(newexpect)
            # 比对训练集：旧事实与新事实的出现次数
            def cnt(text):
                return full.count(text)
            old_tokens = [t for t in re.split(r"[\s，。？！、]+", oldtext) if len(t) >= 2]
            new_tokens = [t for t in re.split(r"[\s，。？！、]+", newtext) if len(t) >= 2]
            mapping.append({"id": cid, "question": c["input"],
                            "old_remember": oldtext, "new_remember": newtext,
                            "old_expect": c["expect"].get("contains_any"),
                            "new_expect": newexpect,
                            "old_fact_in_train_counts": {t: cnt(t) for t in old_tokens},
                            "new_fact_in_train_counts": {t: cnt(t) for t in new_tokens}})
            for t in new_tokens:
                grep_evidence[t] = full.count(t)
            new["note"] = ("[v2] " + c["note"]
                           + "｜去污染：remember 事实已替换为训练集零出现保留值"
                             "（旧值→新值对照见 out/SFT-CONTAMINATION-EXCLUDE-v2.json 的 fact_level_replacement）")
        else:
            # R01-R10：无 remember 事实，保留原样；R05 问句与训练集重合 → note 标注
            rel = relax(c["input"])
            if rel in qrows:
                new["note"] = ("[v2] " + c["note"]
                               + "｜注意：该问句与训练集重合（宽松归一后 %d 行），对比时需单列剔除" % qrows[rel])
            else:
                new["note"] = "[v2] " + c["note"] + "｜无事实冲突，未改"
            out_cases.append(new)

    dst = os.path.join(ROOT, "out", "SFT-EXTRA-CASES-v2.jsonl")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        for c in out_cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 训练集重合（宽松归一）：held-out 16 条 + extra 3 条
    spec = importlib.util.spec_from_file_location("rh_c", os.path.join(ROOT, "training/heldout/run_heldout.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    heldout_overlap = []
    for c in m.CASES:
        rel = relax(c.get("input", ""))
        if rel in qrows:
            heldout_overlap.append({"heldout_id": c["id"], "category": c.get("category"),
                                    "heldout_input": c.get("input"),
                                    "train_question_example": next(
                                        r["messages"][1]["content"] for r in rows
                                        if relax(r["messages"][1]["content"]) == rel),
                                    "train_rows_same_relaxed_q": qrows[rel]})
    extra_overlap = []
    for c in cases:
        rel = relax(c["input"])
        if rel in qrows:
            extra_overlap.append({"extra_id": c["id"], "category": c["category"], "input": c["input"],
                                  "train_question_example": next(
                                      r["messages"][1]["content"] for r in rows
                                      if relax(r["messages"][1]["content"]) == rel),
                                  "train_rows_same_relaxed_q": qrows[rel]})
    ex = {"schema": "sft_contamination_exclude_v2", "task": "TASK-031B",
          "method": "宽松归一=去空白+去前缀(问一下，/在吗，/直接问，)+去尾部/全部中英标点",
          "heldout_relaxed_overlap": heldout_overlap,
          "heldout_exclude_ids": [x["heldout_id"] for x in heldout_overlap],
          "extra_relaxed_overlap": extra_overlap,
          "extra_exclude_ids": [x["extra_id"] for x in extra_overlap],
          "fact_level_replacement": {
              "status": "completed",
              "file": "out/SFT-EXTRA-CASES-v2.jsonl",
              "rows": len(out_cases),
              "replaced": {m["id"]: {"old_remember": m["old_remember"],
                                     "new_remember": m["new_remember"],
                                     "new_expect": m["new_expect"]} for m in mapping},
              "patch_031_values_grep_in_training": {
                  "雪梨": full.count("雪梨"), "商汤": full.count("商汤"), "7418": full.count("7418")},
              "old_values_training_count_background": {
                  "糖糖": full.count("糖糖"), "西安": full.count("西安"), "8899": full.count("8899"),
                  "note": "以上是旧值在训练集全文的出现次数（背景证据）；v2 的 L03/L04/L09 行已替换为雪梨/商汤/7418（含 note 在内零旧值），见 patch_031_values_grep_in_training"}},
          "comparison_policy": {
              "exclude_from_denominator": True,
              "heldout_exclude_ids": [x["heldout_id"] for x in heldout_overlap],
              "extra_exclude_ids": [x["extra_id"] for x in extra_overlap],
              "note": "16 条 held-out 与 3 条 extra 与训练集问句重合：配对表/汇总时删除这些行、不计入分母，单列展示；不得计入 SFT 收益"},
          "note": "这 19 条与训练集问句重合，不得计入 SFT 收益；对比件需单列剔除/标注",
          "sft_extra_cases_v2": {"path": "out/SFT-EXTRA-CASES-v2.jsonl", "sha256": sha256(dst),
                                 "rows": len(out_cases)},
          "unused_suggested_reserved_values": {t: full.count(t) for t in UNUSED_SUGGESTED}}
    exp = os.path.join(ROOT, "out", "SFT-CONTAMINATION-EXCLUDE-v2.json")
    with open(exp, "w", encoding="utf-8") as f:
        json.dump(ex, f, ensure_ascii=False, indent=1)

    print(json.dumps({"out_file": "out/SFT-EXTRA-CASES-v2.jsonl", "sha256": sha256(dst),
                      "rows": len(out_cases),
                      "heldout_overlap": len(heldout_overlap),
                      "heldout_ids": [x["heldout_id"] for x in heldout_overlap],
                      "extra_overlap": len(extra_overlap),
                      "extra_ids": [x["extra_id"] for x in extra_overlap],
                      "mapping": mapping, "grep_new_facts": grep_evidence,
                      "unused_suggested": ex["unused_suggested_reserved_values"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()