# -*- coding: utf-8 -*-
"""Offline: resolve relative time words against created_at (speech anchor).

Levels: YYYY-MM-DD > YYYY-MM > YYYY > relative(fallback, non-resolvable).
No code changes, no DB writes, no service.
"""
import json
import re
from datetime import date, datetime, timedelta

ANCHOR = "2026-11-06"           # Friday
CASES = [
    ("我去年去过云南大理。", "2025", "Y"),
    ("前年我在成都工作。", "2024", "Y"),
    ("三年前我在苏州上班。", "2023", "Y"),
    ("上个月我体检了。", "2026-10", "M"),
    ("上周我去南京出差了。", "2026-10-26", "D"),
    ("前天我买了显示器。", "2026-11-04", "D"),
    ("明年我打算考证。", "2027", "Y"),
    ("下个月要交续租合同。", "2026-12", "M"),
    ("我 2026-10-15 去体检。", "2026-10-15", "D"),
    ("2025年我在上个月搬了家。", "2026-10", "M"),   # 月 比 年 更具体
]


def _prev_month(d):
    y, m = d.year, d.month - 1
    if m == 0:
        y, m = y - 1, 12
    return "%04d-%02d" % (y, m)


def _next_month(d):
    y, m = d.year, d.month + 1
    if m == 13:
        y, m = y + 1, 1
    return "%04d-%02d" % (y, m)


def _prev_week_start(d):
    # Monday of the previous ISO week
    monday = d - timedelta(days=d.weekday())
    return (monday - timedelta(days=7)).isoformat()


def resolve(text, anchor_iso):
    if not anchor_iso:
        return None, None, "anchor_unknown"
    try:
        d = date.fromisoformat(str(anchor_iso)[:10])
    except ValueError:
        return None, None, "anchor_unknown"
    t = str(text)
    cands = []          # (level_rank, value, level)
    # absolute: YYYY-MM-DD / YYYY年M月D日 / YYYY-MM / YYYY年M月 / YYYY年
    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", t)
    if m:
        cands.append((3, "%04d-%02d-%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3))), "D"))
    else:
        m = re.search(r"(\d{4})[-/年](\d{1,2})月?", t)
        if m:
            cands.append((2, "%04d-%02d" % (int(m.group(1)), int(m.group(2))), "M"))
        else:
            m = re.search(r"(\d{4})年", t)
            if m:
                cands.append((1, m.group(1), "Y"))
    rel = [
        ("三年前", (1, str(d.year - 3), "Y")),
        ("前年", (1, str(d.year - 2), "Y")),
        ("去年", (1, str(d.year - 1), "Y")),
        ("明年", (1, str(d.year + 1), "Y")),
        ("上个月", (2, _prev_month(d), "M")),
        ("下个月", (2, _next_month(d), "M")),
        ("上周", (3, _prev_week_start(d), "D")),
        ("前天", (3, (d - timedelta(days=2)).isoformat(), "D")),
    ]
    for word, item in rel:
        if word in t:
            cands.append(item)
    if not cands:
        return None, None, "no_time_word"
    cands.sort(key=lambda x: -x[0])
    rank, value, level = cands[0]
    return value, level, None


rows = []
for text, expected, exp_level in CASES:
    value, level, err = resolve(text, ANCHOR)
    rows.append({"text": text, "anchor": ANCHOR, "extracted": value, "level": level,
                 "expected": expected, "hit": value == expected, "error": err})

# anchor missing case
v, lv, err = resolve("我 2026-10-15 去体检。", None)
rows.append({"text": "我 2026-10-15 去体检。", "anchor": None, "extracted": v,
             "level": lv, "expected": None, "hit": err == "anchor_unknown",
             "error": err, "note": "created_at 缺失 -> anchor_unknown 回退"})

hits = sum(1 for r in rows if r["hit"])
rep = {"schema": "feasibility_time_anchor_v1", "anchor": ANCHOR,
       "n": len(rows), "hits": hits, "rate": round(hits / len(rows), 3),
       "rows": rows,
       "verdict": ("PASS：%d/%d 命中" % (hits, len(rows))) if hits == len(rows) else
                  ("未达 10/10：%d/%d" % (hits, len(rows)))}
json.dump(rep, open("out/FEASIBILITY-TIME-ANCHOR.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

md = ["# 离线可行性 · 时间门（created_at 作说话时间锚点）", "",
      "anchor = **%s**（周五）；规则：绝对日期 > 月 > 年 > 相对；多词取最具体。" % ANCHOR, "",
      "| # | 块文本 | 抽出 | 级别 | 期望 | 命中 |", "|---|---|---|---|---|---|"]
for i, r in enumerate(rows, 1):
    md.append("| %d | %s | %s | %s | %s | %s |" % (
        i, r["text"][:22], r["extracted"] or r.get("error"), r["level"] or "-",
        r["expected"] or "anchor_unknown", "✅" if r["hit"] else "❌"))
md += ["", "命中 **%d/%d**%s" % (hits, len(rows), "（10/10 达标）" if hits == len(rows) else ""), "",
       "## 说明",
       "- 相对时间全部由 anchor 推导：去年/前年/三年前/明年按年，上个月/下个月按自然月，上周按上一自然周起点，前天 -2d。",
       "- 多时间词例子「2025年…上个月…」取**月**（2026-10）而非年，符合“最具体优先”。",
       "- created_at 缺失 → `anchor_unknown`，不猜。"]
open("out/FEASIBILITY-TIME-ANCHOR.md", "w", encoding="utf-8").write("\n".join(md))
print("hits %d/%d" % (hits, len(rows)))