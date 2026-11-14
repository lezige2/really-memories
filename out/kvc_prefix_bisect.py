# -*- coding: utf-8 -*-
"""Bounded prefix bisect for x03 (K2 arm only, no code changes).

For each prefix length N: run the first N cases of dialog_cases.jsonl through the
live service, then immediately /reset + /ask x03 and record the outcome.
Adaptive: start at the longest prefix that still excludes x03 (62), then move
down (fail) or step inside (pass). Hard deadline enforced.
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

EP = "http://127.0.0.1:8765"
CASES = "training/dialog_cases.jsonl"
X03 = "在吗，我几点开会？"
DEADLINE_S = 18 * 60
T0 = time.time()


def post(path, body, timeout=180):
    req = urllib.request.Request(
        EP + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def get(path, timeout=60):
    return json.load(urllib.request.urlopen(EP + path, timeout=timeout))


def ask_x03():
    post("/reset", {"reset": True})
    r = post("/ask", {"text": X03})
    v = r.get("verify") or {}
    return {"answer": r.get("answer"), "state": r.get("state"),
            "verified": r.get("verified"), "verdict": v.get("verdict"),
            "mismatches": v.get("mismatches"), "block_ids": r.get("block_ids"),
            "verify_attempts": r.get("verify_attempts")}


def run_prefix(n):
    out = "out/KVC-PREFIX-N%d.json" % n
    nxt = "out/KVC-PREFIX-N%d-NEXT.json" % n
    log = Path("out/KVC-PREFIX-N%d.log" % n)
    cmd = [sys.executable, "-X", "utf8", "training/run_training_eval.py",
           "--cases", CASES, "--out", out, "--next", nxt,
           "--limit", str(n), "--expect-memories", "20",
           "--reset-per-case", "--forget-created-per-case",
           "--hermetic", "--timeout", "90"]
    t = time.time()
    with log.open("w", encoding="utf-8") as fh:
        rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)
    summary = None
    p = Path(out)
    if p.exists():
        try:
            summary = json.loads(p.read_text(encoding="utf-8")).get("summary")
        except Exception:  # noqa: BLE001
            summary = None
    return {"n": n, "rc": rc, "elapsed_s": round(time.time() - t, 1),
            "out": out, "eval_pass": (summary or {}).get("pass"),
            "eval_n": (summary or {}).get("n")}


def main():
    cases = [json.loads(l) for l in Path(CASES).read_text(encoding="utf-8").splitlines() if l.strip()]
    x03_idx = next(i for i, c in enumerate(cases, 1) if c["id"] == "x03")
    seq = [x03_idx - 1]
    results = []
    verdict = None
    for n in seq:
        if time.time() - T0 > DEADLINE_S:
            verdict = "deadline"
            break
        pr = run_prefix(n)
        x = ask_x03()
        row = dict(pr, x03=x, last3=[c["id"] for c in cases[max(0, n - 3):n]])
        results.append(row)
        print(json.dumps({"n": n, "eval_pass": pr["eval_pass"], "x03_state": x["state"],
                          "x03_answer": (x["answer"] or "")[:40], "elapsed": pr["elapsed_s"]},
                         ensure_ascii=False), flush=True)

    # adaptive descent: if the longest prefix flips x03 to fail, bisect downward
    lo, hi = 0, seq[0]
    def flipped(n):
        pr = run_prefix(n)
        x = ask_x03()
        row = dict(pr, x03=x, last3=[c["id"] for c in cases[max(0, n - 3):n]])
        results.append(row)
        print(json.dumps({"n": n, "eval_pass": pr["eval_pass"], "x03_state": x["state"],
                          "x03_answer": (x["answer"] or "")[:40], "elapsed": pr["elapsed_s"]},
                         ensure_ascii=False), flush=True)
        return x["state"] == "verify_fallback" or x["verdict"] == "unsupported", row

    first = results[0]["x03"]
    fails_at_top = first["state"] == "verify_fallback" or first["verdict"] == "unsupported"
    minimal = None
    if fails_at_top:
        hi = seq[0]
        while hi - lo > 1 and time.time() - T0 < DEADLINE_S:
            mid = (lo + hi) // 2
            bad, _ = flipped(mid)
            if bad:
                hi = mid
            else:
                lo = mid
        minimal = hi if lo + 1 == hi else None
        verdict = "flip" if minimal is not None else "unresolved"
    else:
        verdict = "no_flip_up_to_%d" % seq[0]

    summary = {"schema": "kvc_prefix_bisect_v1", "arm": "K2 (--k2-family)",
               "x03_index": x03_idx, "verdict": verdict,
               "minimal_flip_n": minimal, "prefix_pass_n": lo if fails_at_top else seq[0],
               "elapsed_total_s": round(time.time() - T0, 1),
               "results": results,
               "note": "每次前缀跑完立即 /reset + /ask x03；前缀 N 不含 x03 本身（N<=62）"}
    Path("out/KVC-PREFIX-BISECT.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("VERDICT", verdict, "minimal_flip_n", minimal, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())