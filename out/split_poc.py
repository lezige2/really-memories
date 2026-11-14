# -*- coding: utf-8 -*-
"""20 条真实陈述的拆分 POC：保真率/块数/失败例。"""
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import utterance_split as U  # noqa: E402


def sample():
    out = []
    for db in (os.path.join(ROOT, "kvmem", "daily", "chat.db"),
               os.path.join(ROOT, "kvmem", "scale40k", "n200", "chat.db")):
        if not os.path.exists(db):
            continue
        con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
        try:
            rows = con.execute(
                "SELECT text FROM memory_source WHERE text_kind='human_memory'"
                " AND text NOT LIKE '%？%' AND text NOT LIKE '%?%' LIMIT 40").fetchall()
        except sqlite3.Error:
            rows = []
        con.close()
        for (t,) in rows:
            if t and t not in out:
                out.append(t)
        if len(out) >= 20:
            break
    return out[:20]


def main():
    texts = sample()
    res = {"n": len(texts), "fidelity": 0, "split_ok": 0, "parts": [],
           "failures": [], "details": []}
    for t in texts:
        r = U.split_utterance(t)
        good = "".join(r["parts"]) == t
        res["fidelity"] += bool(good)
        if r["ok"]:
            res["split_ok"] += 1
        res["parts"].append(len(r["parts"]))
        res["details"].append({"ok": r["ok"], "reason": r["reason"],
                               "n": len(r["parts"]), "text": t,
                               "parts": r["parts"]})
        if not good:
            res["failures"].append({"text": t, "reason": r["reason"]})
    res["fidelity_rate"] = round(res["fidelity"] / max(1, len(texts)), 4)
    res["split_rate"] = round(res["split_ok"] / max(1, len(texts)), 4)
    json.dump(res, open(os.path.join(ROOT, "out", "SPLIT-POC.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: res[k] for k in ("n", "fidelity", "fidelity_rate",
                                          "split_ok", "split_rate", "failures")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
