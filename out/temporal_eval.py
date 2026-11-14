# -*- coding: utf-8 -*-
"""TIME-15 离线评测：时间+主题两轴 POC。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import temporal_retrieval as T  # noqa: E402


def main():
    cases = [json.loads(l) for l in open(os.path.join(ROOT, "out",
                                                      "TIME-15-CASES.jsonl"),
                                         encoding="utf-8")]
    rows, hit, miss = [], 0, []
    details = []
    for c in cases:
        r = T.search(c["query"], c["anchor"],
                     [{"id": 1, "text": c["block"], "created_at": c["created_at"]}])
        kind = c["expected"]["kind"]
        exp = c["expected"].get("value")
        ok = False
        if kind == "refusal":
            ok = r["abstain"]
        else:
            if r["kept"]:
                nd = r["kept"][0]["normalized_date"] or ""
                ok = (str(exp) in c["block"]) or nd.startswith(str(exp)[:7])
        hit += bool(ok)
        details.append({"id": c["id"], "kind": kind, "ok": bool(ok),
                        "abstain": r["abstain"], "reason": r["reason"],
                        "normalized_query": r["normalized_query"],
                        "kept": r["kept"]})
        if not ok:
            miss.append(c["id"])
    out = {"cases": len(cases), "hit": hit, "miss": miss,
           "rate": round(hit / len(cases), 4), "gate_14": hit >= 14,
           "details": details}
    json.dump(out, open(os.path.join(ROOT, "out", "TIME-15-RESULT.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("cases", "hit", "rate", "gate_14",
                                          "miss")}, ensure_ascii=False))
    for d in details:
        if not d["ok"]:
            print("MISS", d["id"], d["reason"], d["normalized_query"], d["kept"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
