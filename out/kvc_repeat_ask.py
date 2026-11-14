# -*- coding: utf-8 -*-
"""Repeat one case N times against a live service, replaying eval semantics.

/reset -> pre_state steps in order (remember/ask) -> main /ask -> forget created -> /reset

Read-only w.r.t. product code. Writes a JSON artifact with per-run answer/state/
verify verdict/block_ids so a distribution can be read directly.
"""
import argparse
import json
import urllib.request
from pathlib import Path

CASE_FILES = (
    "training/dialog_cases.jsonl",
    "training/sft_eval_extra_cases.jsonl",
    "out/SFT-EXTRA-CASES-v9-MT20.jsonl",
)


def post(ep, path, body, timeout=180):
    req = urllib.request.Request(
        ep + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def get(ep, path, timeout=60):
    return json.load(urllib.request.urlopen(ep + path, timeout=timeout))


def load_cases():
    cases = {}
    for f in CASE_FILES:
        p = Path(f)
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                cases.setdefault(c["id"], c)
    return cases


def run_once(ep, case):
    post(ep, "/reset", {"reset": True})
    made = []
    for st in case.get("pre_state") or []:
        if st.get("action") == "remember":
            r = post(ep, "/remember", {"text": st["text"]})
            if r.get("id"):
                made.append(r["id"])
        elif st.get("action") == "ask":
            post(ep, "/ask", {"text": st["text"]})
    resp = post(ep, "/ask", {"text": case["input"]})
    for i in made:
        post(ep, "/forget", {"id": i})
    post(ep, "/reset", {"reset": True})
    v = resp.get("verify") or {}
    return {
        "answer": resp.get("answer"),
        "state": resp.get("state"),
        "refused": resp.get("refused"),
        "verified": resp.get("verified"),
        "verify_verdict": v.get("verdict"),
        "verify_mismatches": v.get("mismatches"),
        "verify_attempts": resp.get("verify_attempts"),
        "block_ids": resp.get("block_ids"),
        "created_ids": made,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:8765")
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("--times", type=int, default=5)
    ap.add_argument("--out", required=True)
    ap.add_argument("--arm", default="")
    args = ap.parse_args()
    cases = load_cases()
    ep = args.endpoint.rstrip("/")
    out = {"schema": "kvc_repeat_ask_v1", "arm": args.arm, "endpoint": ep,
           "times": args.times, "cases": {}}
    for cid in args.ids:
        case = cases.get(cid)
        if not case:
            raise SystemExit("case not found: %s" % cid)
        runs = []
        for i in range(args.times):
            r = run_once(ep, case)
            runs.append(r)
            print("[%s %d/%d] state=%s verdict=%s ans=%r"
                  % (cid, i + 1, args.times, r["state"], r["verify_verdict"],
                     (r["answer"] or "")[:60]))
        out["cases"][cid] = {
            "input": case["input"],
            "expect": case.get("expect"),
            "runs": runs,
            "dist_state": {s: sum(1 for x in runs if x["state"] == s)
                           for s in sorted({x["state"] for x in runs})},
            "dist_verdict": {s: sum(1 for x in runs if x["verify_verdict"] == s)
                             for s in sorted({str(x["verify_verdict"]) for x in runs})},
            "dist_answer": {a: sum(1 for x in runs if x["answer"] == a)
                            for a in sorted({x["answer"] or "" for x in runs})},
        }
    h = get(ep, "/health")
    out["after"] = {"memories": h.get("memories")}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    print("wrote", args.out, "memories", h.get("memories"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())