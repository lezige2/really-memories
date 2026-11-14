# -*- coding: utf-8 -*-
"""P1b official R2 judgment replay (interface only; no implementation change).

Runs one held-out file through the public p1b API (extract/decide/Sidecar):
setup statements replayed in order, the LAST one is the statement under test.
Emits a per-case matrix, error classes and gate verdict. No service, no DB write.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path("tools").resolve()))
import p1b_subject as P  # noqa: E402


def label_of(res):
    a = res.get("action")
    if a == "supersede":
        return "supersede"
    if a == "ask":
        if res.get("reason") in ("ambiguous_subject", "no_cue", "negative_cue"):
            return "ambiguous"
        return "ask"
    if a in ("write", "same_value"):
        return "ignore"
    return str(a)


def apply_stmt(side, stmt, ts, nid):
    res = P.decide(stmt, ts, side)
    act, info = res.get("action"), res.get("info")
    if act in ("write", "supersede") and info and info.get("value"):
        eid = str(nid)
        side.data["entries"][eid] = {
            "block_id": nid, "text_sha256": P.sha_text(stmt), "created_at": str(ts),
            "subject": info["subject"], "predicate": info["predicate"],
            "value": info["value"], "subject_source": info["subject_source"],
            "supersedes": None, "superseded_by": None, "ambiguous": False}
        if act == "supersede" and res.get("target") is not None:
            old = side.data["entries"].get(str(res["target"]))
            if old is not None:
                old["superseded_by"] = eid
                side.data["entries"][eid]["supersedes"] = res["target"]
        return nid + 1
    return nid


def run(path):
    raw = Path(path).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    cases = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
    rows = []
    for c in cases:
        side = P.Sidecar(os.path.join(tempfile.mkdtemp(prefix="p1b_"), "s.json"))
        nid = 9001
        for i, st in enumerate((c.get("setup") or [])[:-1]):
            nid = apply_stmt(side, st, "2026-10-30T10:00:%02d" % i, nid)
        if c.get("setup"):
            last = c["setup"][-1]
            res = P.decide(last, "2026-10-30T10:00:59", side)
            info = res.get("info") or P.extract(last)
            mode = ("extract_miss" if not (info and info.get("value") and info.get("predicate"))
                    else ("no_prior" if res.get("action") == "write" else "decided"))
        else:
            res, info, mode = {"action": "write", "reason": "no_setup"}, None, "no_setup"
        got = label_of(res)
        row = {"id": c["id"], "group": c.get("group"), "kind": c.get("kind"),
               "query": c.get("query"), "expected": c.get("expected_action"),
               "got": got, "raw_action": res.get("action"), "reason": res.get("reason"),
               "extract": None if not info else {"subject": info.get("subject"),
                                                 "predicate": info.get("predicate"),
                                                 "value": info.get("value")},
               "failure_mode": mode, "match": got == c.get("expected_action")}
        if got == "supersede" and (c.get("target_block") or {}).get("kind") == "baseline":
            row["target_ok"] = int(res.get("target") or -1) == int(c["target_block"]["id"])
        rows.append(row)
    st = {}
    for g in sorted({r["group"] for r in rows}):
        rs = [r for r in rows if r["group"] == g]
        st[g] = {"n": len(rs), "match": sum(1 for r in rs if r["match"])}
    err = {
        "false_supersede": [r["id"] for r in rows if r["got"] == "supersede" and r["expected"] != "supersede"],
        "missed_supersede": [r["id"] for r in rows if r["expected"] == "supersede" and r["got"] != "supersede"],
        "ask_mismatch": [r["id"] for r in rows if r["got"] == "ask" and r["expected"] != "ask"],
        "ambiguous_mismatch": [r["id"] for r in rows if r["got"] == "ambiguous" and r["expected"] != "ambiguous"],
        "extract_miss": [r["id"] for r in rows if r["failure_mode"] == "extract_miss"],
    }
    neg = [r for r in rows if r["group"] == "negation"]
    amb = [r for r in rows if r["expected"] == "ambiguous"]
    gate = {
        "false_supersede_zero": len(err["false_supersede"]) == 0,
        "neg_amb_all_ask_or_abstain": all(r["got"] in ("ask", "ambiguous") for r in neg + amb),
        "single_subject_covered": all(r["got"] == "supersede" for r in rows
                                      if r["expected"] == "supersede"),
        "multi_subject_no_cross": all(r["got"] != "supersede" for r in rows
                                      if r["expected"] in ("ask", "ambiguous")
                                      or (r["expected"] == "ignore")),
    }
    gate["pass"] = all(gate.values())
    return {"file": path, "sha256": sha, "n": len(rows), "stats": st,
            "errors": err, "gate": gate, "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--r2", default="out/P1B-HELDOUT-R2.jsonl")
    ap.add_argument("--v1", default="out/P1B-HELDOUT-v1.jsonl")
    ap.add_argument("--v1-relabeled", dest="v1r", default="out/P1B-HELDOUT.jsonl")
    ap.add_argument("--out", default="out/P1B-C2-R2-REPORT.json")
    args = ap.parse_args()
    r2 = run(args.r2)
    v1 = run(args.v1)
    v1r = run(args.v1r)
    out = {"schema": "p1b_c2_r2_report_v1", "r2": r2, "v1_regression": v1,
           "v1_relabeled": v1r,
           "note": "answer_regression 的“仍拒答”需活服务，本回放仅覆盖决策/写路径"}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for tag, d in (("R2", r2), ("v1", v1), ("v1-relabeled", v1r)):
        print(tag, "sha", d["sha256"][:16], "n", d["n"], "stats", d["stats"])
        print("   errors", {k: v for k, v in d["errors"].items() if v})
        print("   gate", d["gate"])
    for r in r2["rows"]:
        print("%-8s %-10s exp=%-9s got=%-9s %s/%s %s %s" % (
            r["id"], r["group"], r["expected"], r["got"], r["raw_action"],
            r["reason"], r["failure_mode"], "OK" if r["match"] else "MISS"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())