# -*- coding: utf-8 -*-
"""C2 independent labels for P0 event_date samples (labeler: C, non-implementer).

Rules applied literally from out/P0-EVENTDATE-SPEC.md §8 (B 2026-10-30):
  1 下周X = next ISO week's weekday; today == X -> +7
  2 这周X already past -> ambiguous
  3 bare weekday: today == that weekday -> +7; else the nearest upcoming one
  4 下个月 N 号 spans 12->1; 月底 = last day; 月底 day already past -> ambiguous
  5 created_at is UTC -> convert to Asia/Shanghai local date before applying
  6 晚上12点 = next day 00:00; 凌晨N点 = same day; 晚上11:59 = same day; 半夜12点 = next day
  periodic (每周/每月/每年) -> no event_date, periodic=true

Only text + created_at_local + spec were used; parser code/output was not read.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

SAMPLES = Path("out/P0-EVENTDATE-SAMPLES-40.jsonl")
OUT = Path("out/P0-EVENTDATE-C2-LABELS.jsonl")
LOCAL = timezone(timedelta(hours=8))

# Explicit, hand-made labels: id -> (event_date|None, confidence, periodic, note)
L = {
    "E01": ("2026-11-04", "high", False, "下周三：今天周三，下周 ISO 周三=11-04（§8.1 +7）"),
    "E02": ("2026-11-02", "high", False, "下周一：下一 ISO 周周一"),
    "E03": ("2026-10-28", "high", False, "这周三且今天正是周三：未过，取当天"),
    "E04": ("2026-10-30", "high", False, "这周五：本周五=10-30"),
    "E05": ("2026-11-04", "high", False, "裸“周三”且今天周三：按§8.3同理取+7=11-04（边界，请B复核）"),
    "E06": ("2026-11-09", "high", False, "下下周一：再下一 ISO 周周一"),
    "E07": ("2026-10-29", "high", False, "明天"),
    "E08": ("2026-10-30", "high", False, "后天"),
    "E09": ("2026-10-31", "high", False, "大后天"),
    "E10": ("2026-10-28", "high", False, "今晚=当天 20:00"),
    "E11": ("2026-10-30", "high", False, "明天（基准 10-29）"),
    "E12": ("2026-10-31", "high", False, "明天+晚上12点=次日00:00（§8.6）"),
    "E13": ("2026-10-30", "high", False, "明天凌晨两点=当天（§8.6）"),
    "E14": ("2026-10-30", "high", False, "裸周五且今天周四=本周五（§8.3）"),
    "E15": ("2026-10-30", "high", False, "这周五，今天周四，未过"),
    "E16": (None, "ambiguous", False, "这周三，今天周四，已过（§8.2）不猜"),
    "E17": (None, "ambiguous", False, "“下周”无星期几（§3 歧义）"),
    "E18": ("2026-10-31", "high", False, "月底=10-31，今天10-29未过"),
    "E19": ("2026-11-05", "high", False, "下个月5号=11-05"),
    "E20": (None, "none", True, "每周三=periodic 不写 event_date"),
    "E21": ("2026-11-06", "high", False, "裸周五且今天周五=+7（§8.3）"),
    "E22": ("2026-10-31", "high", False, "裸周六，今天周五=本周六"),
    "E23": ("2026-10-31", "high", False, "明天中午12点=当天12:00"),
    "E24": ("2026-10-31", "high", False, "明天晚上11:59=当天（§8.6）"),
    "E25": ("2026-10-31", "high", False, "半夜12点=次日00:00（§8.6）"),
    "E26": ("2026-11-01", "high", False, "后天（基准 10-30）"),
    "E27": ("2026-11-08", "high", False, "下周日出差：下一 ISO 周周日"),
    "E28": (None, "ambiguous", False, "下个月31号：11月仅30天，非法日期不猜"),
    "E29": ("2026-10-31", "high", False, "本月底=10-31"),
    "E30": (None, "none", True, "每月1号=periodic 不写 event_date"),
    "E31": ("2027-01-01", "high", False, "明天（基准 12-31）跨年"),
    "E32": ("2026-12-31", "high", False, "月底且今天正是月底：未过（§8.4/§8.8）"),
    "E33": ("2027-01-01", "high", False, "下个月1号，12→1（§8.4）"),
    "E34": ("2027-01-06", "high", False, "下周三（基准 12-31 周四）"),
    "E35": ("2027-01-06", "high", False, "裸周三，本周三已过→最近未来=01-06"),
    "E36": (None, "ambiguous", False, "这周一，今天周四，已过（§8.2）"),
    "E37": ("2026-10-28", "high", False, "这周三且今天=周三（边界样本，同 E03）"),
    "E38": ("2026-11-06", "high", False, "周五且今天=周五→+7（§8.3 边界样本）"),
    "E39": ("2027-01-05", "high", False, "下个月5号，12→1（§8.4 边界样本）"),
    "E40": ("2026-10-31", "high", False, "月底当天：未过（§8.4/§8.8 边界样本）"),
}


def main():
    raw = SAMPLES.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    rows = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
    assert len(rows) == 40, len(rows)
    assert set(L) == {r["id"] for r in rows}, "label/ids mismatch"
    out = []
    for r in rows:
        exp, conf, periodic, note = L[r["id"]]
        created = datetime.strptime(r["created_at_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        local = created.astimezone(LOCAL)
        out.append({
            "id": r["id"],
            "text": r["text"],
            "created_at_utc": r["created_at_utc"],
            "created_at_local": local.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "local_date": local.strftime("%Y-%m-%d"),
            "local_weekday": local.strftime("%A"),
            "expected_event_date": exp,
            "expected_confidence": conf,
            "expected_periodic": periodic,
            "label_note": note,
            "samples_sha256": sha,
            "labeler": "C (non-implementer)",
            "spec": "out/P0-EVENTDATE-SPEC.md §8",
        })
    OUT.write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in out), encoding="utf-8")
    from collections import Counter
    print("wrote", OUT, "n", len(out), "samples_sha256", sha)
    print("confidence", dict(Counter(o["expected_confidence"] for o in out)))
    print("periodic", sum(1 for o in out if o["expected_periodic"]))
    print("ambiguous ids", [o["id"] for o in out if o["expected_confidence"] == "ambiguous"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())