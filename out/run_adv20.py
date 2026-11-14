# -*- coding: utf-8 -*-
"""Run the 20 adversarial cases once against 8766 and dump per-case results."""
import json
import sys
import urllib.request

EP = "http://127.0.0.1:8766"
CASES = [json.loads(l) for l in open("out/POC-ADV20.jsonl", encoding="utf-8") if l.strip()]


def post(path, body, timeout=180):
    req = urllib.request.Request(EP + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def main(arm, out_path):
    res = []
    for c in CASES:
        post("/reset", {"reset": True})
        made = []
        for st in c["pre_state"]:
            if st["action"] == "remember":
                r = post("/remember", {"text": st["text"]})
                if r.get("id"):
                    made.append(r["id"])
            else:
                post("/ask", {"text": st["text"]})
        a = post("/ask", {"text": c["input"]})
        for j in made:
            post("/forget", {"id": j})
        post("/reset", {"reset": True})
        ans = a.get("answer") or ""
        want = (c.get("expect") or {}).get("contains_all") or []
        ok = all(v in ans for v in want)
        res.append({"id": c["id"], "kind": c["kind"], "pass": ok,
                    "answer": ans, "state": a.get("state"),
                    "attr": a.get("attribute_recency"),
                    "blocks": a.get("block_ids")})
        print("%s %s %s" % (arm, c["id"], "PASS" if ok else "FAIL"), flush=True)
    n = len(res)
    k = sum(1 for r in res if r["pass"])
    out = {"arm": arm, "n": n, "pass": k, "rate": round(k / n, 3),
           "fallback": sum(1 for r in res if r["state"] == "verify_fallback"),
           "phone": {"pass": sum(1 for r in res if r["kind"] == "phone" and r["pass"]),
                     "n": sum(1 for r in res if r["kind"] == "phone")},
           "fitness": {"pass": sum(1 for r in res if r["kind"] == "fitness" and r["pass"]),
                       "n": sum(1 for r in res if r["kind"] == "fitness")},
           "rows": res}
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("%s pass %d/%d fallback %d" % (arm, k, n, out["fallback"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])