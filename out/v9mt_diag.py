# -*- coding: utf-8 -*-
"""V9MT11/12 verifier-fallback diagnostic (isolated copy, no product changes).

Replays each case's pre_state exactly, then records the observable verify story:
final answer, state, verified, verdict, mismatches (claim/type/expected block),
attempts, block_ids. The pre-repair draft is not exposed by the API, so the
mismatch claims (which quote the offending spans) are the closest evidence.

Usage: v9mt_diag.py --arm event_on --times 5
Appends the arm's runs into out/V9MT11-12-VERIFIER-DIAG.json.
"""
import argparse
import json
import urllib.request
from pathlib import Path

EP = "http://127.0.0.1:8765"
DIAG = Path("out/V9MT11-12-VERIFIER-DIAG.json")


def post(path, body, timeout=240):
    req = urllib.request.Request(
        EP + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def run_case(case):
    post("/reset", {"reset": True})
    made = []
    for st in case.get("pre_state") or []:
        if st.get("action") == "remember":
            r = post("/remember", {"text": st["text"]})
            if r.get("id"):
                made.append(r["id"])
        elif st.get("action") == "ask":
            post("/ask", {"text": st["text"]})
    a = post("/ask", {"text": case["input"]})
    for i in made:
        post("/forget", {"id": i})
    post("/reset", {"reset": True})
    v = a.get("verify") or {}
    return {
        "answer": a.get("answer"),
        "state": a.get("state"),
        "verified": a.get("verified"),
        "verify_verdict": v.get("verdict"),
        "mismatches": v.get("mismatches"),
        "hint": v.get("hint"),
        "attempts": a.get("verify_attempts"),
        "block_ids": a.get("block_ids"),
        "k2": a.get("k2"),
        "created_ids": made,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--times", type=int, default=5)
    args = ap.parse_args()
    cases = {c["id"]: c for c in (
        json.loads(l) for l in Path("out/SFT-EXTRA-CASES-v9-MT20.jsonl")
        .read_text(encoding="utf-8").splitlines() if l.strip())}
    data = json.loads(DIAG.read_text(encoding="utf-8")) if DIAG.exists() else {
        "schema": "v9mt11_12_verifier_diag_v1", "endpoint": EP, "arms": {}}
    arm = {"times": args.times, "cases": {}}
    for cid in ("V9MT11", "V9MT12"):
        runs = [run_case(cases[cid]) for _ in range(args.times)]
        arm["cases"][cid] = {
            "input": cases[cid]["input"],
            "expect": cases[cid].get("expect"),
            "pre_remember": [p.get("text") for p in cases[cid]["pre_state"]
                             if p.get("action") == "remember"],
            "runs": runs,
            "dist_state": {s: sum(1 for r in runs if r["state"] == s)
                           for s in sorted({r["state"] for r in runs})},
            "dist_verdict": {str(s): sum(1 for r in runs if r["verify_verdict"] == s)
                             for s in {r["verify_verdict"] for r in runs}},
            "n_fallback": sum(1 for r in runs if r["state"] == "verify_fallback"),
            "n_attempts_gt0": sum(1 for r in runs if (r["attempts"] or 0) > 0),
        }
        print(cid, arm["cases"][cid]["dist_state"],
              arm["cases"][cid]["dist_verdict"], flush=True)
    h = json.load(urllib.request.urlopen(EP + "/health", timeout=30))
    arm["memories_after"] = h.get("memories")
    data["arms"][args.arm] = arm
    DIAG.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", DIAG, "arm", args.arm, "memories", h.get("memories"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())