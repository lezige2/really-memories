# -*- coding: utf-8 -*-
"""Build P1-V9MT04-OFF100 + P1-DETERMINISM reports from the 100-run JSON."""
import collections
import json

D = json.load(open("out/P1-V9MT04-OFF100.json", encoding="utf-8"))
runs = D["runs"]
n = len(runs)

style = []          # classify each run
for r in runs:
    ans = r.get("answer") or ""
    if r.get("state") == "verify_fallback":
        style.append("fallback")
    elif "周三" in ans:
        style.append("draft_wed")
    elif "周二" in ans:
        style.append("ok_tue")
    else:
        style.append("other")
cnt = collections.Counter(style)
# a "V9MT04-style failure" = fallback / wrong weekday, i.e. the case got broken
fail_like = cnt.get("fallback", 0) + cnt.get("draft_wed", 0)
distinct_answers = collections.Counter((r.get("answer") or "") for r in runs)
n_forms = len(distinct_answers)

rep = {
    "schema": "p1_v9mt04_off100_v1",
    "arm": "all_off", "n": n, "pass": D["pass"], "fallback": D["fallback"],
    "style_counts": dict(cnt),
    "failure_like": fail_like,
    "criterion": {"threshold": 3, "flaky": fail_like >= 3, "suspect_all_on": fail_like == 0},
    "verdict": (
        "全关 100 次：fallback %d 次、草稿型“周三”%d 次 ⇒ 同类失败 %d 次；"
        "判据 ≥3 则记 flaky ⇒ %s"
        % (cnt.get("fallback", 0), cnt.get("draft_wed", 0), fail_like,
           "记 flaky，全量默认可开" if fail_like >= 3
           else ("无同类失败，需怀疑 all-on" if fail_like == 0 else "介于 1–2 次，证据不足"))),
}
json.dump(rep, open("out/P1-V9MT04-OFF100.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

det = {
    "schema": "p1_determinism_v1",
    "setup": "同 prompt/同 blocks（V9MT04 pre_state 后问“我几点去健身？”）× %d" % n,
    "distinct_answers": n_forms,
    "answer_forms": [{"answer": a, "count": c} for a, c in distinct_answers.most_common(6)],
    "both_normal_and_wed": ("ok_tue" in cnt) and (cnt.get("draft_wed", 0) > 0),
    "fallback_rate": round(cnt.get("fallback", 0) / n, 3),
    "verdict": (
        "同输入出现 %d 种答案形态（正常 %d、fallback %d）⇒ 单次 MT20 门不成立，应改区间/配对"
        % (n_forms, cnt.get("ok_tue", 0), cnt.get("fallback", 0))
        if n_forms > 1 else
        "同输入只有 1 种答案形态 ⇒ 单次判定有效"),
}
json.dump(det, open("out/P1-DETERMINISM.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

md = ["# P1 · V9MT04 全关 ×100", "",
      "| 项 | 值 |", "|---|---|",
      "| 运行次数 | %d |" % n,
      "| pass | **%d/%d** |" % (D["pass"], n),
      "| verify_fallback | **%d** |" % cnt.get("fallback", 0),
      "| 草稿含“周三” | **%d** |" % cnt.get("draft_wed", 0),
      "| 正常（周二） | **%d** |" % cnt.get("ok_tue", 0),
      "| 其它 | %d |" % cnt.get("other", 0),
      "", "## 判定", "",
      "- 判据：同类失败 ≥3 → 记 flaky、全量默认可开；0 次才怀疑 all-on。",
      "- 实测同类失败 **%d** 次 ⇒ %s。" % (fail_like, rep["verdict"].split("⇒ ")[-1]),
      "", "## 说明",
      "- 失败形态：`verify_fallback`（草案被 verifier 判 unsupported 后回退罐头句）。"]
open("out/P1-V9MT04-OFF100.md", "w", encoding="utf-8").write("\n".join(md))

md2 = ["# P1 · 确定性探针（同输入 ×%d）" % n, "",
       "| 项 | 值 |", "|---|---|",
       "| 不同答案形态 | **%d** |" % n_forms,
       "| 正常（周二） | %d |" % cnt.get("ok_tue", 0),
       "| fallback | %d |" % cnt.get("fallback", 0),
       "| 草稿含周三 | %d |" % cnt.get("draft_wed", 0),
       "", "## 答案形态（前 6）", "",
       "| 次数 | 答案 |", "|---|---|"]
for a, c in distinct_answers.most_common(6):
    md2.append("| %d | %s |" % (c, (a or "")[:40].replace("|", "/")))
md2 += ["", "## 结论", "", "- " + det["verdict"]]
open("out/P1-DETERMINISM.md", "w", encoding="utf-8").write("\n".join(md2))
print(json.dumps({"style": dict(cnt), "fail_like": fail_like,
                  "distinct_answers": n_forms}, ensure_ascii=False))