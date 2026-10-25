# -*- coding: utf-8 -*-
"""M1.8 真实库 8 条探针（before/after 同一脚本，只读产品库，索引建在临时副本上）。

用法：
  python -X utf8 probe_m18_8.py --tag before --out out/M18-PROBES-before.json
  python -X utf8 probe_m18_8.py --tag after  --out out/M18-PROBES-after.json
  python -X utf8 probe_m18_8.py --compare out/M18-PROBES-before.json out/M18-PROBES-after.json

纪律：
- 产品库 `kvmem/chat.db` **只读**：拷到临时目录再 `build_index`，绝不写产品库；
- 8 条探针来自 inspector `M1.8-CONFLICTS-inspector.md` §1.1–§1.4 的**真实库读数**（§5 只给结论、
  未逐条枚举，故清单在此显式登记：每条带 `source` 行号与期望方向）；
- `no_worse` 判据：任一探针「before 对、after 不对」即 worse ⇒ 停手；
  同时记录「before 错、after 对」为 improved（不许只报好的）。
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))   # D:/llama-mem
sys.path.insert(0, os.path.join(ROOT, "tools"))
import retrieval as R          # noqa: E402
import analysis as A           # noqa: E402

DB = os.path.join(ROOT, "kvmem", "chat.db")

# id 沿用 inspector §1.2 的真实库读数（source_id → 块内容见产物里的 blocks 表）
PROBES = [
    {"id": "P1", "q": "我的地址是什么", "target": [5], "must_not": [1, 2],
     "source": "inspector §1.1（allowed=[1,2,3,5]，5=我住在广陵路…；改前 ABSTAIN）"},
    {"id": "P2", "q": "我的住址是什么", "target": [5], "must_not": [1, 2],
     "source": "inspector §1.1（同上）"},
    {"id": "P3", "q": "我生日是哪天", "target": [], "must_not": [2],
     "source": "inspector §1.2（source 2 被误判 birthday；改前会答 3月14）"},
    {"id": "P4", "q": "我车牌颜色是什么", "target": [], "must_not": [2],
     "source": "inspector §1.2（color 无作用域；改前 allowed=[2]）"},
    {"id": "P5", "q": "我住在哪", "target": [5], "must_not": [1],
     "source": "inspector §1.2（address 无作用域；改前 allowed 含 profile）"},
    {"id": "P6", "q": "我女儿什么时候生日", "target": [10], "must_not": [2],
     "source": "inspector §1.2/§4.4（source 10 只写『下周三』）"},
    {"id": "P7", "q": "我女儿生日是哪天", "target": [10], "must_not": [2],
     "source": "inspector §4.4（真实库 ABSTAIN）"},
    {"id": "P8", "q": "我身高多少", "target": [], "must_not": [],
     "source": "inspector §1.2（真实库无身高记录 ⇒ 应 ABSTAIN）"},
]


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def open_copy():
    tmp = tempfile.mkdtemp(prefix="m18probe_")
    dst = os.path.join(tmp, "chat.db")
    shutil.copyfile(DB, dst)
    con = sqlite3.connect(dst)
    return con, dst


def block_rows(con):
    return [{"id": i, "text": t} for i, t in
            con.execute("SELECT id, text FROM memory_source ORDER BY id")]


def attr_rows(con):
    try:
        return [{"source_id": s, "attr": a} for s, a in
                con.execute("SELECT source_id, attr FROM attr ORDER BY source_id, attr")]
    except sqlite3.Error:
        return []


def run(tag):
    t0 = time.time()
    con, db_copy = open_copy()
    R.build_index(con, verbose=False)
    blocks = block_rows(con)
    by_id = {b["id"]: b["text"] for b in blocks}
    rows = []
    for p in PROBES:
        want_prop = A.property_of(p["q"])
        scope = A.scope_of(p["q"], want_prop) if want_prop else None
        allowed = None
        if want_prop:
            allowed = sorted(sid for sid, txt in by_id.items()
                             if A.property_holds(txt, want_prop, scope))
        res = R.search(con, p["q"], k=3)
        top = res[0] if res else None
        rows.append({
            "id": p["id"], "query": p["q"], "source": p["source"],
            "target": p["target"], "must_not": p["must_not"],
            "want_prop": want_prop, "scope": scope, "allowed": allowed,
            "n_hits": len(res),
            "top": ({"id": top["source_id"], "name": top["name"],
                     "score": round(top["score"], 3),
                     "signals": top["signals"]} if top else None),
            "all": [{"id": r["source_id"], "score": round(r["score"], 3)} for r in res],
            "top_text": (by_id.get(top["source_id"], "")[:80] if top else None),
        })
    attr_rows_list = attr_rows(con)
    con.close()
    return {"schema": "m18_real_probes_v1", "tag": tag,
            "sampled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "db": DB, "db_sha16": sha16(DB),
            "code": {"analysis_sha16": sha16(os.path.join(ROOT, "tools", "analysis.py")),
                     "retrieval_sha16": sha16(os.path.join(ROOT, "tools", "retrieval.py"))},
            "thresholds": {"GATE": R.GATE, "COV_MIN": R.COV_MIN,
                           "REL_CUT": R.REL_CUT, "ABS_CUT": R.ABS_CUT},
            "probe_list_note": "8 条清单在脚本 PROBES 里显式登记（inspector §1.1-§1.4 的真实库读数）",
            "blocks": blocks,
            "rows": rows, "attr_rows": attr_rows_list, "elapsed_s": round(time.time() - t0, 2)}


def judge(before_row, after_row):
    """better / same / worse —— 三条规则先写死，再判。"""
    bt = before_row["top"]["id"] if before_row["top"] else None
    at = after_row["top"]["id"] if after_row["top"] else None
    tgt, bad = before_row["target"], before_row["must_not"]
    if tgt:                                   # 有目标块：答对=better，答错=worse，其余 same
        if at in tgt and bt not in tgt:
            return "better"
        if bt in tgt and at not in tgt:
            return "worse"
        return "same"
    if bad:                                   # 有禁区块：进禁区=worse，退出禁区=better
        if at in bad and bt not in bad:
            return "worse"
        if bt in bad and at not in bad:
            return "better"
        return "same"
    # 无目标无禁区（P8）：应保持 ABSTAIN；变出答案 = worse
    if bt is None and at is not None:
        return "worse"
    if bt is not None and at is None:
        return "better"
    return "same"


def compare(p_before, p_after):
    b = json.load(open(p_before, encoding="utf-8"))
    a = json.load(open(p_after, encoding="utf-8"))
    rows = []
    for rb, ra in zip(b["rows"], a["rows"]):
        rows.append({"id": rb["id"], "query": rb["query"],
                     "before": {"top": rb["top"], "n_hits": rb["n_hits"], "allowed": rb["allowed"]},
                     "after": {"top": ra["top"], "n_hits": ra["n_hits"], "allowed": ra["allowed"]},
                     "verdict": judge(rb, ra)})
    worse = [r for r in rows if r["verdict"] == "worse"]
    out = {"schema": "m18_real_probes_compare_v1",
           "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "before": {"path": p_before, "tag": b["tag"], "code": b["code"],
                      "db_sha16": b["db_sha16"]},
           "after": {"path": p_after, "tag": a["tag"], "code": a["code"],
                     "db_sha16": a["db_sha16"]},
           "rows": rows,
           "counts": {"better": sum(1 for r in rows if r["verdict"] == "better"),
                      "same": sum(1 for r in rows if r["verdict"] == "same"),
                      "worse": len(worse)},
           "no_worse": not worse,
           "worse_rows": worse}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="before")
    ap.add_argument("--out", required=False)
    ap.add_argument("--compare", nargs=2)
    args = ap.parse_args()
    if args.compare:
        out = compare(*args.compare)
    else:
        out = run(args.tag)
    path = args.out or os.path.join(HERE, "out", "M18-PROBES-%s.json" % out.get("tag", "cmp"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    if args.compare:
        print(json.dumps({"no_worse": out["no_worse"], "counts": out["counts"],
                          "worse": out["worse_rows"]}, ensure_ascii=False))
        print("%-3s %-18s %-10s %-10s %s" % ("id", "query", "before", "after", "verdict"))
        for r in out["rows"]:
            bt = r["before"]["top"]["id"] if r["before"]["top"] else "ABSTAIN"
            at = r["after"]["top"]["id"] if r["after"]["top"] else "ABSTAIN"
            print("%-3s %-18s %-10s %-10s %s" % (r["id"], r["query"], bt, at, r["verdict"]))
    else:
        print("%-3s %-18s %-10s %-6s %s" % ("id", "query", "top", "hits", "allowed"))
        for r in out["rows"]:
            print("%-3s %-18s %-10s %-6d %s" % (
                r["id"], r["query"], r["top"]["id"] if r["top"] else "ABSTAIN",
                r["n_hits"], r["allowed"]))
    print("->", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())