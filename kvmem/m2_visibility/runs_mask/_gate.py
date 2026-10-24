# -*- coding: utf-8 -*-
"""Four-item AND gate for one (log, json) pair.

Every item reads ONE class; no cross-class total is ever computed.

  1 A   per-class label      SUM lines carrying layout=<json.layout.key> == decode_batches_expected
                             and SUM lines carrying any other layout value == 0
  2 B   set assertion        set(layout values seen in the log) == {json.layout.key}   (no counts)
  3 3a  structural anchor    SUM  == decode_batches_expected            (= 1 + N_PREDICT)
                             blk  == len(layout.segments) * SUM
                             OK   == len(layout.segments)
                             SUM2 == SUM
     3b  internal agreement  per class: log count == json.trace_classes[cls]
                             (degenerate runs are self-consistent, so this is auxiliary only)
     3c  conflict            if 3a fails while 3b passes -> ask the DRIVER first, not the engine
  4 same-source              rows are written into THIS json; the log is pinned by sha256

Exit 0 only when all four items pass; otherwise 6.
"""
import argparse, hashlib, json, os, re, sys

CLS_RE = {
    "SUM": re.compile(r"^\[MASKDBG-SUM\] "),
    "SUM2": re.compile(r"^\[MASKDBG-SUM2\] "),
    "blk": re.compile(r"^\[MASKDBG\] "),
    "OK": re.compile(r"MASKDBG-OK"),
}
LAYOUT_RE = re.compile(r"layout=([A-Za-z0-9_]+)")


def sha256_file(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def scan(log_path):
    counts = {"SUM": 0, "SUM2": 0, "blk": 0, "OK": 0}
    sum_by_layout = {}
    values = set()
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = LAYOUT_RE.search(line)
            if m:
                values.add(m.group(1))
            for name, rx in CLS_RE.items():
                if rx.search(line):
                    counts[name] += 1
                    if name == "SUM":
                        key = m.group(1) if m else "<none>"
                        sum_by_layout[key] = sum_by_layout.get(key, 0) + 1
                    break
    return counts, sum_by_layout, values


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--run-json", required=True)
    ap.add_argument("--write-rows", action="store_true",
                    help="write _gate_rows into the run json (never used on frozen artifacts)")
    a = ap.parse_args()
    d = json.load(open(a.run_json, encoding="utf-8"))
    key = (d.get("layout") or {}).get("key")
    segs = (d.get("layout") or {}).get("segments") or []
    n_seg = len(segs)
    expect_sum = d.get("decode_batches_expected")
    declared = d.get("trace_classes") or {}
    counts, sum_by_layout, values = scan(a.log)
    items = []

    def row(name, expect, actual, ok, why="", status=None):
        st = status or ("pass" if ok else "fail")
        items.append({"item": name, "expect": str(expect), "actual": str(actual),
                      "pass": st == "pass", "status": st, "note": why})

    # 1) A -- per-class label correctness, SUM class only
    on_key = sum_by_layout.get(key, 0)
    off_key = counts["SUM"] - on_key
    row("A", "SUM(layout=%s)==%s 且 其它layout(%d种)的SUM行==0" % (key, expect_sum, len(values)),
        "on_key=%d off_key=%d (by layout: %s)" % (on_key, off_key,
        ", ".join("%s:%d" % kv for kv in sorted(sum_by_layout.items())) or "none"),
        expect_sum is not None and on_key == expect_sum and off_key == 0,
        "只数 SUM 类；SUM2/blk/OK 显式排除")

    # 2) B -- set assertion, no counts at all
    row("B", "set(layout 值)=={%s}" % key,
        "set=%s" % (sorted(values) or "empty"),
        key is not None and values == {key},
        "不含任何数量；整类缺失时会恒绿，故必须与 A/3a 一起看")

    # 3a) structural anchor
    e1 = (expect_sum is not None and counts["SUM"] == expect_sum)
    e2 = (counts["blk"] == n_seg * counts["SUM"])
    e3 = (counts["OK"] == n_seg)
    e4 = (counts["SUM2"] == counts["SUM"])
    row("3a", "SUM==%s, blk==%d*SUM, OK==%d, SUM2==SUM" % (expect_sum, n_seg, n_seg),
        "SUM=%d blk=%d OK=%d SUM2=%d (anchors: decode_batches_expected=%s segments=%d)"
        % (counts["SUM"], counts["blk"], counts["OK"], counts["SUM2"], expect_sum, n_seg),
        e1 and e2 and e3 and e4,
        "锚点前提: %s" % (d.get("trace_gate") or "<trace_gate 未记录>"))

    # 3b) per-class agreement between two DIFFERENT plumbing paths:
    #     log file (re-read here)  vs  the launcher's tee of the child stderr pipe.
    #     json.trace_classes is itself a count of the log file, so using it alone would be
    #     unfalsifiable -- it is only a fallback for artifacts predating the tee.
    # Three kinds of artifact, three verdicts -- never written as one:
    #   worker_counts present            -> 3b is a REAL check (pipe stream vs log file)
    #   new run (child_env) without it   -> driver bug, 3b RED, exit 7
    #   frozen pre-tee artifact          -> physically cannot have it, 3b INERT, no vote
    has_counts = isinstance(d.get("worker_counts"), dict)
    is_new_run = "child_env" in d
    driver_bug = (not has_counts) and is_new_run
    inert = (not has_counts) and (not is_new_run)
    side = d.get("worker_counts") if has_counts else declared
    diffs = []
    for cls in ("SUM", "SUM2", "blk", "OK"):
        want = side.get(cls)
        got = counts[cls]
        if want is None:
            diffs.append("%s: 未记录" % cls)
        elif want != got:
            diffs.append("%s: json=%s log=%s" % (cls, want, got))
    if inert:
        # INERT means NOT CHECKED, not "no differences": saying diffs=none would imply
        # the comparison happened and passed.
        row("3b", "逐类 log==worker_counts（该产物无独立计数，不可证伪）",
            "未对账（无独立计数；退化基准 trace_classes，不参与 overall）",
            True, "冻结产物早于 tee：3b INERT，不参与 overall", status="inert")
    elif driver_bug:
        # RED because the independent side is MISSING, not because values disagreed.
        # Saying diffs=none here would print RED next to a clean diff -- unreadable.
        row("3b", "逐类 log==worker_counts（SUM/SUM2/blk/OK 各自比）",
            "worker_counts 缺失（新 run 未接 tee 计数）",
            False, "新 run 缺 worker_counts（驱动未接 tee 计数）")
    else:
        row("3b", "逐类 log==worker_counts（SUM/SUM2/blk/OK 各自比）",
            "diffs=%s" % ("; ".join(diffs) if diffs else "none"),
            not diffs,
            "独立路径对账：log 文件 vs 驱动对子进程 stderr 的 tee 计数")

    # 3c) conflict hint -- not an extra item, printed only
    hint = ""
    if not items[2]["pass"] and items[3]["pass"]:
        hint = "3c: 3a 红而 3b 绿 -> 先查驱动计数与门控前提(trace_gate)，不先查引擎"

    # An inert item is one whose baseline is a count of the very file it checks, so it can
    # never go red. Counting it in the AND would mean "four-item gate" is really 3 + 1 always
    # green -- exactly the defect we keep rejecting. It stays printed, it does not vote.
    live = [it for it in items if it["status"] != "inert"]
    inert_n = len(items) - len(live)
    overall = all(it["pass"] for it in live)
    expr = ("%d 项 AND + 3b INERT（不计入）" % len(live)) if inert_n else "%d 项 AND" % len(live)
    print("=== gate on %s / %s ===" % (a.log, a.run_json))
    for it in items:
        tag = {"pass": "GREEN", "fail": "RED  ", "inert": "INERT"}[it["status"]]
        # a red line that hides WHY it is red just makes the next reader re-derive it
        tail = ("   <- %s" % it["note"]) if it["status"] == "fail" and it["note"] else ""
        print("  %-3s %-5s expect=%s | actual=%s%s" % (it["item"], tag, it["expect"],
                                                       it["actual"], tail))
    if inert_n:
        print("  门禁 %d/4 实测，3b INERT：该产物无独立计数（冻结产物，早于 tee）" % len(live))
    if hint:
        print(" ", hint)
    print("  OVERALL:", "GREEN" if overall else "RED", " (%s)" % expr)

    if a.write_rows:
        # _gate_rows keeps its original name and shape (the 25 trace rows written by
        # _assert_trace.py); the four-item result goes to a NEW key so no existing reader
        # of _gate_rows breaks.
        d["_gate_four"] = {"log": os.path.abspath(a.log), "log_sha256": sha256_file(a.log),
                           "json_sha256": sha256_file(a.run_json),
                           "trace_gate": d.get("trace_gate"),
                           "items": {it["item"]: {"expect": it["expect"], "actual": it["actual"],
                                                  "status": it["status"], "pass": it["pass"],
                                                  "note": it["note"]}
                                     for it in items},
                           "overall": overall, "overall_expr": expr, "hint": hint}
        with open(a.run_json, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
        print("  _gate_four written into", a.run_json)
    if overall:
        return 0
    return 7 if driver_bug else 6


if __name__ == "__main__":
    sys.exit(main())
