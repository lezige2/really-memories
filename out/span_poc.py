# -*- coding: utf-8 -*-
"""20 条真实话 span POC：偏移有效/类别数/命中整块/标签内容。"""
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import span_annotate as SA  # noqa: E402


def sample():
    out = []
    for db in (os.path.join(ROOT, "kvmem", "daily", "chat.db"),
               os.path.join(ROOT, "kvmem", "scale40k", "n200", "chat.db")):
        if not os.path.exists(db):
            continue
        con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
        try:
            rows = con.execute(
                "SELECT id,text FROM memory_source WHERE text_kind='human_memory'"
                " LIMIT 40").fetchall()
        except sqlite3.Error:
            rows = []
        con.close()
        for i, t in rows:
            if t and t not in [x[1] for x in out]:
                out.append((i, t))
        if len(out) >= 20:
            break
    return out[:20]


def main():
    blocks = [{"id": i, "text": t} for i, t in sample()]
    res = {"n": len(blocks), "with_spans": 0, "offset_ok": 0,
           "max_classes": 0, "hit_whole_block": 0, "label_ok": 0,
           "samples": [], "failures": []}
    for b in blocks:
        a = SA.annotate(b["text"])
        res["with_spans"] += bool(a["spans"])
        res["max_classes"] = max(res["max_classes"], len(a["spans"]))
        off_ok = all(b["text"][s["start"]:s["end"]] == s["text"]
                     for s in a["spans"])
        res["offset_ok"] += bool(off_ok)
        # 命中整块：用块自身作 query
        hits = SA.search(b["text"], [b])
        whole = bool(hits) and hits[0]["id"] == b["id"] and \
            hits[0]["block"]["text"] == b["text"]
        if a["spans"]:
            res["hit_whole_block"] += bool(whole)
        lab = SA.label_fragment(b["id"], a["spans"])
        label_ok = (not a["spans"]) or (
            lab.startswith("块%d｜" % b["id"]) and
            all(("=%s" % s["text"]) in lab for s in a["spans"]))
        res["label_ok"] += bool(label_ok)
        item = {"id": b["id"], "text": b["text"][:40], "n": len(a["spans"]),
                "spans": a["spans"], "label": lab, "hit": bool(whole),
                "offset_ok": bool(off_ok), "label_ok": bool(label_ok)}
        res["samples"].append(item)
        if a["spans"] and not (off_ok and whole and label_ok):
            res["failures"].append(item)
    n = max(1, len(blocks))
    res.update(span_rate=round(res["with_spans"] / n, 4),
               offset_rate=round(res["offset_ok"] / n, 4),
               hit_rate=round(res["hit_whole_block"] /
                              max(1, res["with_spans"]), 4),
               label_rate=round(res["label_ok"] / n, 4))
    json.dump(res, open(os.path.join(ROOT, "out", "SPAN-POC.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: res[k] for k in ("n", "with_spans", "span_rate",
                                          "offset_rate", "hit_rate",
                                          "label_rate", "max_classes",
                                          "failures")}, ensure_ascii=False)[:500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
