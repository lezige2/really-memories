# -*- coding: utf-8 -*-
"""离线回放：用历史 run 的 actual.answer + block_ids 跑 verifier v2。

块文本来源：kvmem/daily/chat.db.bak-20261029-2022（20 基块，只读）
          + 每 case setup.prelude 的 remember id 与 pre_state remember 文本按序配对。
不改库、不调模型。
"""
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

os.environ["VERIFIER_VERSION"] = "v2"
import answer_verifier as av  # noqa: E402

BACKUP = os.path.join(ROOT, "kvmem", "daily", "chat.db.bak-20261029-2022")
FILES = ("KVC-K2c-81.json", "KVC-K2-EXTRA.json", "KVC-K2-MT20.json")


def base_texts():
    con = sqlite3.connect("file:%s?mode=ro" % BACKUP.replace("\\", "/"), uri=True)
    try:
        return {int(r[0]): str(r[1]) for r in
                con.execute("SELECT id,text FROM memory_source ORDER BY id")}
    finally:
        con.close()


def case_blocks(case, base):
    texts = dict(base)
    remembers = [a.get("text") for a in case.get("pre_state") or []
                 if a.get("action") == "remember"]
    prelude = (case.get("setup") or {}).get("prelude") or []
    ids = [p.get("id") for p in prelude if p.get("action") == "remember"]
    for sid, text in zip(ids, remembers):
        texts[int(sid)] = str(text)
    out = []
    for bid in ((case.get("actual") or {}).get("block_ids") or []):
        try:
            bid = int(bid)
        except (TypeError, ValueError):
            continue
        if bid in texts:
            out.append({"id": bid, "text": texts[bid]})
    return out


def main():
    base = base_texts()
    all_rows = {}
    for name in FILES:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            print("skip missing", name)
            continue
        data = json.load(open(path, encoding="utf-8"))
        rows = []
        for r in data.get("results") or []:
            ans = str((r.get("actual") or {}).get("answer") or "")
            bl = case_blocks(r, base)
            v = av.verify(r.get("input") or "", ans, bl, mode="personal")
            rows.append({
                "id": r.get("id"),
                "pass": bool(r.get("pass")),
                "verdict": v.get("verdict"),
                "mismatches": v.get("mismatches") or [],
                "answer": ans,
                "block_ids": [b["id"] for b in bl],
            })
        fails = [x for x in rows if x["verdict"] != "pass"]
        false_kills = [x for x in fails if x["pass"]]
        true_errors = [x for x in fails if not x["pass"]]
        all_rows[name] = rows
        print("== %s: n=%d v2_fail=%d true_error=%d false_kill=%d"
              % (name, len(rows), len(fails), len(true_errors), len(false_kills)))
        for x in fails:
            print("  %-6s harness_pass=%s verdict=%s blocks=%s answer=%r"
                  % (x["id"], x["pass"], x["verdict"], x["block_ids"],
                     x["answer"][:60]))
    # 81 基线：必须 0 误杀
    base_rows = all_rows.get("KVC-K2c-81.json") or []
    fk81 = [x for x in base_rows if x["verdict"] != "pass" and x["pass"]]
    print("GATE 81: false_kill=%d -> %s" % (len(fk81), "OK" if not fk81 else "STOP"))
    return 0 if not fk81 else 3


if __name__ == "__main__":
    sys.exit(main())