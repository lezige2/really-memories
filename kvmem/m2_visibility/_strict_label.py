# -*- coding: utf-8 -*-
r"""Strict-label recount over EXISTING artifacts. Runs nothing, writes nothing.

raw_ok : the artifact's own ok field, verbatim
form   : frozen criterion (empty = len 0; quiz = a run of >=3 "_" or one of A./B./A、/B、; else plain)
cloze  : orthogonal dimension (>=3 groups of "\_" or a run of >=3 "_" or the text contains 填空)
strict : raw_ok is True AND form == "plain"   -- recall must be free-form to count as recall
         (ok is a substring match on the expected fact, so a cloze whose OPTION LIST contains
          the answer also scores ok; strict refuses to call that recall)

Records come from either artifact shape and are reported per shape, never merged:
  ask path      {"ask": {"ok":..,"answer":..,"expected":..}}
  answers path  {"answers": [{"segment":..,"ok":..,"answer":..,"expected":..}, ...]}
One run counts once per shape; when a run carries both shapes the answers path wins for the
per-layout tables (more specific) and the fact is printed.

Usage:  python -X utf8 _strict_label.py [root ...]      (default: every runs*/ under this dir)
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs_mask"))
import _form as F                                          # noqa: E402


def paths(roots):
    seen = set()
    for r in roots:
        for p in sorted(glob.glob(os.path.join(r, "**", "*.json"), recursive=True)):
            p = os.path.normpath(p)
            if p not in seen:
                seen.add(p)
                yield p


def layout_key(d):
    lay = d.get("layout")
    if isinstance(lay, dict) and lay.get("key"):
        return lay["key"]
    return d.get("layout_key") or d.get("experiment") or "<unknown>"


def shape(d):
    if isinstance(d.get("answers"), list):
        return "answers"
    if isinstance(d.get("ask"), dict) and "ok" in d["ask"]:
        return "ask"
    return None


def rows(root_list):
    out = []
    for p in paths(root_list):
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        sh = shape(d)
        if sh is None:
            continue
        for label, ok, ans, exp in F.records(p):
            ans = ans or ""
            form, cl = F.classify(ans), F.cloze_marker(ans)
            out.append({"path": p, "shape": sh, "run": os.path.basename(p)[:-5],
                        "layout": layout_key(d), "label": label, "raw_ok": ok,
                        "form": form, "cloze": cl, "len": len(ans),
                        "strict": (ok is True) and form == "plain",
                        "has_both": isinstance(d.get("answers"), list)
                                    and isinstance(d.get("ask"), dict)})
    return out


def cross(rs, sh):
    c = Counter((r["raw_ok"], r["form"]) for r in rs if r["shape"] == sh)
    print("  %-8s %-6s %5s" % ("raw_ok", "form", "n"))
    for k in sorted(c, key=lambda x: (str(x[0]), x[1])):
        print("  %-8s %-6s %5d" % (k[0], k[1], c[k]))
    n_ok = sum(1 for r in rs if r["shape"] == sh and r["raw_ok"] is True)
    n_st = sum(1 for r in rs if r["shape"] == sh and r["strict"])
    print("  合计: raw_ok=True %d ｜ strict=True %d ｜ 记录 %d" %
          (n_ok, n_st, sum(c.values())))


def main(argv):
    roots = argv or sorted(glob.glob("runs*"))
    rs = rows(roots)
    print("=== 扫描根: %s ===" % ", ".join(roots))
    print("=== 记录数: %d ｜ 文件（去重后）: %d ===" %
          (len(rs), len({r["path"] for r in rs})))
    both = {r["path"] for r in rs if r["has_both"]}
    print("=== 同时带 ask 与 answers 的文件: %d %s ===" % (len(both), sorted(both)[:3]))

    print()
    print("=== 表 1a: raw_ok x form （ask 路径） ===")
    cross(rs, "ask")
    print()
    print("=== 表 1b: raw_ok x form （answers[] 路径） ===")
    cross(rs, "answers")

    print()
    print("=== 表 2: 按 layout（同 run 取 answers 路径，其次 ask；每 run 一次） ===")
    by_run = {}
    for r in rs:
        key = r["path"]
        if key not in by_run or (r["shape"] == "answers" and by_run[key]["shape"] == "ask"):
            by_run[key] = r
    agg = defaultdict(lambda: [0, 0, 0])                  # raw_ok pass, strict pass, n
    diff = defaultdict(list)
    for r in by_run.values():
        a = agg[r["layout"]]
        a[2] += 1
        a[0] += 1 if r["raw_ok"] is True else 0
        a[1] += 1 if r["strict"] else 0
        if (r["raw_ok"] is True) != r["strict"]:
            diff[r["layout"]].append((r["run"], r["label"], r["raw_ok"], r["form"], r["cloze"]))
    print("  %-18s %6s %6s %5s" % ("layout", "raw", "strict", "n"))
    for k in sorted(agg):
        a = agg[k]
        mark = "   <-- 不一致" if k in diff else ""
        print("  %-18s %6d %6d %5d%s" % (k, a[0], a[1], a[2], mark))
    print()
    print("=== 表 2b: 不一致明细（raw_ok=True 但 strict=False，即被 strict 剥夺的 pass） ===")
    for k in sorted(diff):
        for run, label, ok, form, cl in diff[k]:
            print("  %-18s %-34s %-22s raw_ok=%s form=%-6s cloze=%s" % (k, run, label, ok, form, cl))

    print()
    print("=== 表 3: 已死假设的关键对照点（raw vs strict，只报数） ===")
    focus = ["iso_dup4", "iso_dup_p3", "iso_dup_p2", "iso_habit_bot",
             "iso_dup4_s128", "iso_car_back", "iso_no_car",
             "iso_home_only", "iso_habit_only", "iso_topgap"]
    print("  %-18s %5s %6s %6s   %s" % ("layout", "n", "raw", "strict", "各 run 的 (raw_ok,form→strict)"))
    for k in focus:
        if k not in agg:
            print("  %-18s %5s %6s %6s   （库中无此 layout 的记录）" % (k, "-", "-", "-"))
            continue
        a = agg[k]
        detail = []
        for r in sorted([x for x in by_run.values() if x["layout"] == k],
                        key=lambda x: x["run"]):
            detail.append("%s(%s,%s→%s)" % (r["run"], r["raw_ok"], r["form"], r["strict"]))
        print("  %-18s %5d %6d %6d   %s" % (k, a[2], a[0], a[1], " ".join(detail)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
