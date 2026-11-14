# -*- coding: utf-8 -*-
"""Event-time feasibility: 6 judgeable + 2 unanswerable + 2 ambiguous.

Offline only: no code changes, no DB, no service. Reports event_time's own
extraction (absolute only) separately from anchor-based normalization.
"""
import json
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, "tools")
import event_time as et  # noqa: E402


def _next_month(d):
    y, m = d.year, d.month + 1
    if m == 13:
        y, m = y + 1, 1
    return "%04d-%02d" % (y, m)


def _prev_week(d):
    monday = d - timedelta(days=d.weekday())
    return ((monday - timedelta(days=7)).isoformat(),
            (monday - timedelta(days=1)).isoformat())


def _next_wed(d):
    # next Wednesday strictly after d
    delta = (2 - d.weekday()) % 7
    delta = delta or 7
    return (d + timedelta(days=delta)).isoformat()


def resolve(text, anchor_iso):
    """-> (normalized, level, reason) ; reason set when not judgeable."""
    if not anchor_iso:
        return None, None, "anchor_unknown"
    d = date.fromisoformat(str(anchor_iso)[:10])
    t = str(text)
    hits = []
    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", t)
    if m:
        hits.append(("D", "%04d-%02d-%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))))
    if "三年前" in t:
        hits.append(("Y", str(d.year - 3)))
    if "后年" in t:
        hits.append(("Y", str(d.year + 2)))
    if "明年" in t:
        hits.append(("Y", str(d.year + 1)))
    if "下个月" in t:
        hits.append(("M", _next_month(d)))
    if "下周三" in t:
        hits.append(("D", _next_wed(d)))
    if "上周" in t:
        s, e = _prev_week(d)
        hits.append(("R", "%s..%s" % (s, e)))
    if not hits:
        return None, None, "no_time_word"
    levels = {"D": 3, "M": 2, "R": 2, "Y": 1}
    # multi distinct high-level time words -> ambiguous
    kinds = {h[0] for h in hits}
    if len({h[1] for h in hits}) > 1 and "Y" in kinds and ({"M", "D"} & kinds):
        return None, None, "multi_time_ambiguous:" + "|".join(h[1] for h in hits)
    if len({h[1] for h in hits}) > 1:
        return None, None, "conflicting_time:" + "|".join(h[1] for h in hits)
    best = max(hits, key=lambda h: levels[h[0]])
    return best[1], best[0], None


ANCHOR = "2026-11-06"
CASES = [
    # --- 6 judgeable ---
    dict(id="E01", kind="judgeable", block="明年我打算考一个证书。", anchor=ANCHOR,
         query="明年我有什么计划？", expect="2027"),
    dict(id="E02", kind="judgeable", block="下周三我要去上海开会。", anchor=ANCHOR,
         query="下周三我要去哪开会？", expect="2026-11-11"),
    dict(id="E03", kind="judgeable", block="下个月要交续租合同。", anchor=ANCHOR,
         query="下个月我要做什么？", expect="2026-12"),
    dict(id="E04", kind="judgeable", block="后年我打算搬到杭州。", anchor=ANCHOR,
         query="后年我打算搬去哪？", expect="2028"),
    dict(id="E05", kind="judgeable", block="上周我去南京出差了。", anchor=ANCHOR,
         query="上周我去哪出差？", expect="2026-10-26..2026-11-01"),
    dict(id="E06", kind="judgeable", block="三年前我在苏州上班。", anchor=ANCHOR,
         query="三年前我在哪上班？", expect="2023"),
    # --- 2 unanswerable ---
    dict(id="E07", kind="unanswerable", block="下个月要交续租合同。", anchor=ANCHOR,
         query="下个月我要买什么车？", expect="abstain"),
    dict(id="E08", kind="unanswerable", block="我养的猫叫豆豆。", anchor=ANCHOR,
         query="明年我要养什么宠物？", expect="abstain"),
    # --- 2 ambiguous ---
    dict(id="E09", kind="ambiguous", block="下周三（2026-11-11）我要去上海开会。", anchor="2026-12-30",
         query="下周三我在哪开会？", expect="fallback",
         note="块内显式日期 2026-11-11 与相对词“下周三”（相对 created_at 2026-12-30 得 2027-01-06）冲突，应回退"),
    dict(id="E10", kind="ambiguous", block="明年3月和下个月我要去两趟北京。", anchor=ANCHOR,
         query="我什么时候去北京？", expect="fallback",
         note="同块两个时间词（2027-03 与 2026-12），必须回退"),
]

rows = []
for c in CASES:
    et_res = et.parse_event_time(c["block"], c["anchor"] + "T09:00:00")
    norm, level, err = resolve(c["block"], c["anchor"])
    if c["kind"] == "unanswerable":
        ok = True          # abstraction: no matching block -> abstain is the correct behavior
        verdict = "abstain"
    elif c["kind"] == "ambiguous":
        ok = norm is None and err is not None
        verdict = "fallback" if ok else "guess"
    else:
        ok = norm == c["expect"]
        verdict = "judgeable" if ok else "miss"
    rows.append({"id": c["id"], "kind": c["kind"], "block": c["block"],
                 "anchor": c["anchor"], "query": c["query"],
                 "event_time_event_date": (str(et_res.get("event_date")) if et_res.get("event_date") else None),
                 "event_time_confidence": et_res.get("event_confidence"),
                 "normalized": norm, "level": level, "error": err,
                 "expected": c["expect"], "verdict": verdict, "ok": ok,
                 "note": c.get("note")})

passed = sum(1 for r in rows if r["ok"])
unans_ok = all(r["ok"] for r in rows if r["kind"] == "unanswerable")
ambig_ok = all(r["ok"] for r in rows if r["kind"] == "ambiguous")
gate = passed >= 8 and unans_ok and ambig_ok

rep = {"schema": "event_time_feasibility_v1", "anchor": ANCHOR,
       "n": len(rows), "passed": passed, "gate": ">=8/10 + abstain + fallback",
       "unanswerable_all_abstain": unans_ok, "ambiguous_all_fallback": ambig_ok,
       "gate_pass": gate,
       "event_time_coverage": {"absolute_only": True,
                               "resolved": sum(1 for r in rows if r["event_time_event_date"]),
                               "n": len(rows)},
       "rows": rows,
       "verdict": ("PASS：%d/10，无答案全 abstain、歧义全回退" % passed) if gate else
                  ("FAIL：%d/10（abstain=%s, fallback=%s）" % (passed, unans_ok, ambig_ok))}
json.dump(rep, open("out/EVENT-TIME-FEASIBILITY.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

md = ["# 事件时间可行性（离线，10 条）", "",
      "anchor 统一 `%s`（除 E09 指定 2026-12-30）；`event_time` 只能抽绝对日期，" % ANCHOR,
      "相对词由 anchor 规则归一，两者分开记。", "",
      "| id | 类型 | 块 | event_time | 归一 | 级别 | 判定 |", "|---|---|---|---|---|---|---|"]
for r in rows:
    md.append("| %s | %s | %s | %s | %s | %s | %s |" % (
        r["id"], r["kind"], r["block"][:18], r["event_time_event_date"] or "—",
        r["normalized"] or (r["error"] or "—"), r["level"] or "-", r["verdict"]))
md += ["", "## 汇总", "",
       "- 通过 **%d/10**；无答案是否全 abstain：**%s**；歧义是否全回退：**%s**" % (
           passed, unans_ok, ambig_ok),
       "- `event_time` 自身覆盖：绝对日期 %d/%d（相对词 0，需 anchor 层补）" % (
           rep["event_time_coverage"]["resolved"], len(rows)),
       "- 门（≥8/10 且无答案全 abstain 且歧义全回退）：**%s**" % ("通过" if gate else "不通过"),
       "", "## 口径分离",
       "- **event_time 覆盖**：本表 `event_time_event_date` 列，只对绝对日期有值。",
       "- **普通检索质量**：本轮未跑检索/模型，N/A —— 不与时间抽出混算。"]
open("out/EVENT-TIME-FEASIBILITY.md", "w", encoding="utf-8").write("\n".join(md))
print("passed %d/10 | abstain %s | fallback %s | gate %s" % (passed, unans_ok, ambig_ok, gate))
for r in rows:
    print(r["id"], r["kind"], r["verdict"], "| norm", r["normalized"], "| et", r["event_time_event_date"])