# -*- coding: utf-8 -*-
"""Run V9MT04 N times against a live endpoint; write result JSON per arm."""
import json
import sys
import urllib.request

EP = "http://127.0.0.1:8765"
PRE = ([{"action": "remember", "text": "我的健身时间是周日上午九点半"},
        {"action": "remember", "text": "我的健身时间是周二晚上七点四十"}]
       + [{"action": "ask", "text": t} for t in
          ["你平时喜欢干什么？", "今天忙不忙？", "晚上有空吗？", "周末有什么计划吗？",
           "最近在忙什么？", "有什么推荐的放松方式吗？"]])


def post(path, body, timeout=180):
    req = urllib.request.Request(EP + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def main(arm, out_path, n=20):
    runs = []
    for _ in range(n):
        post("/reset", {"reset": True})
        made = []
        for st in PRE:
            if st["action"] == "remember":
                r = post("/remember", {"text": st["text"]})
                if r.get("id"):
                    made.append(r["id"])
            else:
                post("/ask", {"text": st["text"]})
        a = post("/ask", {"text": "我几点去健身？"})
        ans = a.get("answer") or ""
        runs.append({"state": a.get("state"), "pass": "周二晚上七点四十" in ans,
                     "blocks": a.get("block_ids"), "verify": a.get("verify"),
                     "answer": ans})
        for j in made:
            post("/forget", {"id": j})
        post("/reset", {"reset": True})
    fails = [r for r in runs if not r["pass"]]
    out = {"arm": arm, "n": n, "pass": n - len(fails),
           "fallback": sum(1 for r in runs if r["state"] == "verify_fallback"),
           "fail_detail": [{"state": r["state"], "blocks": r["blocks"],
                            "verify": r["verify"], "answer": r["answer"]} for r in fails],
           "runs": runs}
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("%s pass %d/%d fallback %d" % (arm, out["pass"], n, out["fallback"]))
    return 0


if __name__ == "__main__":
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    raise SystemExit(main(sys.argv[1], sys.argv[2], n))