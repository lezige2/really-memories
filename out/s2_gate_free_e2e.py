# -*- coding: utf-8 -*-
"""S2 gate-free end-to-end probe runner (diagnostic only).

Runs the 20 held-out probes against a live service and records, per probe:
mounted block_ids, answer, target-in-mount, answer-contains-value, and for
negatives whether the answer is a refusal or a fabrication.

No product change, no DB write (only /ask + /reset).
"""
import argparse
import json
import re
import urllib.request
from pathlib import Path

PROBES = Path("out/S2-GATE-HELDOUT-20.jsonl")
OUT = Path("out/S2-GATE-FREE-E2E.json")

# expected value aliases per target probe
EXPECT = {
    "H01": ["小橘"], "H02": ["小柚"], "H03": ["小柠"], "H04": ["小栗"],
    "H05": ["小竹"], "H06": ["小枫"],
    "H07": ["5M8T1", "沪B"],
    "H08": ["6222 0201 8830 4408", "6222020188304408", "6222"],
    "H09": ["2026-11-05", "11-05", "09:30"],
    "H10": ["7排05号", "7排5号", "05号"],
}

REFUSAL = re.compile(
    r"(没有(记录|提到|说过|告诉)|没(有)?记(录|得)|不记得|记不清|不知道|不清楚|没法(确认|核对|回答)"
    r"|无法(确认|回答|核对)|未(曾)?(提及|记录|提到)|我这里没有|你没(跟我)?说过|无从(确认|得知))")


def post(ep, path, body, timeout=240):
    req = urllib.request.Request(
        ep + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:8766")
    ap.add_argument("--mount", required=True, help="top4 / top20")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    ep = args.endpoint.rstrip("/")
    probes = [json.loads(l) for l in PROBES.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = []
    for p in probes:
        post(ep, "/reset", {"reset": True})
        a = post(ep, "/ask", {"text": p["text"]})
        post(ep, "/reset", {"reset": True})
        ans = (a.get("answer") or "")
        blocks = a.get("block_ids") or []
        rec = {"id": p["id"], "kind": p["kind"], "text": p["text"], "target": p.get("target"),
               "answer": ans, "block_ids": blocks, "state": a.get("state"), "k2": a.get("k2")}
        if p["kind"] == "target":
            rec["target_in_mount"] = p["target"] in blocks
            rec["answer_has_value"] = any(v in ans for v in EXPECT.get(p["id"], []))
            rec["ok"] = bool(rec["target_in_mount"] and rec["answer_has_value"])
        else:
            rec["refused"] = bool(REFUSAL.search(ans))
            rec["fabricated"] = not rec["refused"]
            rec["ok"] = rec["refused"]
        rows.append(rec)
        print(p["id"], p["kind"], "blocks", blocks, "| ok", rec["ok"],
              "|", (ans or "")[:40], flush=True)
    pos = [r for r in rows if r["kind"] == "target"]
    neg = [r for r in rows if r["kind"] == "negative"]
    summary = {
        "mount": args.mount,
        "n": len(rows),
        "target_in_mount": sum(1 for r in pos if r["target_in_mount"]),
        "answer_has_value": sum(1 for r in pos if r["answer_has_value"]),
        "target_both": sum(1 for r in pos if r["ok"]),
        "target_n": len(pos),
        "neg_refused": sum(1 for r in neg if r["refused"]),
        "neg_fabricated": sum(1 for r in neg if r["fabricated"]),
        "neg_n": len(neg),
        "recall": round(sum(1 for r in pos if r["ok"]) / max(1, len(pos)), 4),
    }
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {
        "schema": "s2_gate_free_e2e_v1",
        "note": "gate-free (S2_GATE_OFF=1) diagnostic; no product/default change",
        "probe_file": str(PROBES),
        "mounts": {}}
    data["mounts"][args.mount] = {"rows": rows, "summary": summary}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())