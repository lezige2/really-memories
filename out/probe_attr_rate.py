# -*- coding: utf-8 -*-
"""Probe attribute_recency trigger rate over the 20 MT20 cases (one pass)."""
import json
import sys
import urllib.request

EP = "http://127.0.0.1:8766"
CASES = [json.loads(l) for l in open("out/SFT-EXTRA-CASES-v9-MT20.jsonl", encoding="utf-8") if l.strip()]


def post(path, body, timeout=180):
    req = urllib.request.Request(EP + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def main(out_path):
    rows = []
    for c in CASES:
        post("/reset", {"reset": True})
        made = []
        for st in c.get("pre_state") or []:
            if st["action"] == "remember":
                r = post("/remember", {"text": st["text"]})
                if r.get("id"):
                    made.append(r["id"])
            elif st["action"] == "ask":
                post("/ask", {"text": st["text"]})
        a = post("/ask", {"text": c["input"]})
        for j in made:
            post("/forget", {"id": j})
        post("/reset", {"reset": True})
        attr = a.get("slot_direct") or a.get("attribute_recency") or {}
        rows.append({"id": c["id"], "applied": bool(attr) or bool(attr.get("applied")),
                     "reason": attr.get("reason"), "value": attr.get("value"), "kept": attr.get("kept"),
                     "hidden": attr.get("hidden"), "state": a.get("state")})
    applied = sum(1 for r in rows if r["applied"])
    out = {"n": len(rows), "applied": applied, "rate": round(applied / len(rows), 3),
           "le_30pct": applied / len(rows) <= 0.30, "rows": rows}
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("applied %d/%d = %.1f%% | <=30%%: %s" % (applied, len(rows), 100 * applied / len(rows),
                                                   out["le_30pct"]))
    for r in rows:
        print(" ", r["id"], r["applied"], r["reason"], r["kept"], r["hidden"])


if __name__ == "__main__":
    main(sys.argv[1])