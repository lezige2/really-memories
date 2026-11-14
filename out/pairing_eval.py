# -*- coding: utf-8 -*-
"""TIME-35 组级配对评测（固定 now=2026-11-06）。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import temporal_pairing as TP  # noqa: E402

NOW = "2026-11-06T09:00:00"


def main():
    cases = [json.loads(l) for l in open(os.path.join(ROOT, "out",
                                                      "TIME-35-CASES.jsonl"),
                                         encoding="utf-8")]
    hit, misses, details = 0, [], []
    abstain_total = abstain_ok = 0
    amb_total = amb_ok = 0
    for c in cases:
        blocks = c.get("blocks") or [{"text": c["block"],
                                      "created_at": c["created_at"]}]
        rows = []
        for i, b in enumerate(blocks):
            rows.append({"id": i + 1, "text": b["text"],
                         "created_at": b.get("created_at") or c["created_at"],
                         "group_id": c.get("group_id"),
                         "related": c.get("related")})
        r = TP.retrieve(c["query"], NOW, rows)
        kind = c["expected"]["kind"]
        exp = c["expected"].get("value")
        if kind == "value":
            txt = "\n".join(b["text"] for b in blocks)
            ok = bool(r["kept"]) and (
                str(exp) in txt
                or any(k["intervals"] and str(exp)[:7] in k["intervals"][0]["start"]
                       for k in r["groups"]))
        elif kind in ("refusal", "abstain"):
            abstain_total += 1
            ok = r["abstain"]
            abstain_ok += bool(ok)
        else:                                          # fallback
            amb_total += 1
            ok = bool(r["ambiguous"] or r["created_conflict"])
            amb_ok += bool(ok)
        hit += bool(ok)
        details.append({"id": c["id"], "kind": kind, "ok": bool(ok),
                        "abstain": r["abstain"], "ambiguous": r["ambiguous"],
                        "created_conflict": r["created_conflict"],
                        "reason": r["reason"], "groups": r["groups"]})
        if not ok:
            misses.append(c["id"])
    out = {"cases": len(cases), "hit": hit, "rate": round(hit / len(cases), 4),
           "gate_32": hit >= 32, "misses": misses,
           "abstain": "%d/%d" % (abstain_ok, abstain_total),
           "ambiguity": "%d/%d" % (amb_ok, amb_total), "details": details}
    json.dump(out, open(os.path.join(ROOT, "out", "TIME-35-RESULT.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("cases", "hit", "rate", "gate_32",
                                          "misses", "abstain", "ambiguity")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
