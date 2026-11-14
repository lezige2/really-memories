# -*- coding: utf-8 -*-
"""POC: attribute recency on/off for V9MT03/04/05/06, 5 runs each arm."""
import json
import sys
import urllib.request

EP = "http://127.0.0.1:8766"
CASES = {c["id"]: c for c in
         (json.loads(l) for l in open("out/SFT-EXTRA-CASES-v9-MT20.jsonl", encoding="utf-8") if l.strip())}
IDS = ["V9MT03", "V9MT04", "V9MT05", "V9MT06"]


def post(path, body, timeout=180):
    req = urllib.request.Request(EP + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def run_case(cid):
    c = CASES[cid]
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
    exp = c.get("expect") or {}
    ans = a.get("answer") or ""
    ok = all(v in ans for v in (exp.get("contains_all") or [])) and \
        not any(v in ans for v in (exp.get("not_contains") or []))
    return {"pass": ok, "answer": ans, "state": a.get("state"),
            "blocks": a.get("block_ids"),
            "attr": a.get("attribute_recency"), "verify": a.get("verify")}


def main(arm, out_path, runs=5):
    out = {"arm": arm, "runs_per_case": runs, "cases": {}}
    for cid in IDS:
        rs = [run_case(cid) for _ in range(runs)]
        out["cases"][cid] = {"pass": sum(1 for r in rs if r["pass"]), "n": runs,
                             "runs": rs}
        print("%s %s pass %d/%d" % (arm, cid, out["cases"][cid]["pass"], runs))
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 5)