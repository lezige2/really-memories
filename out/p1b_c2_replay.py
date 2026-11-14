# -*- coding: utf-8 -*-
"""P1b official C2 independent replay (interface only; no implementation change).

For each held-out case: replay its setup statements in order through the public
p1b decision API (p1b_subject.extract / decide / Sidecar), then read the action
for the LAST setup statement (the statement under test) and compare it with the
case's expected_action.

Label mapping (documented, used for the 23-case matrix):
  decide supersede            -> "supersede"
  decide ask (any reason)     -> "ask"        (reason kept verbatim)
      reason in {ambiguous_subject, no_cue, negative_cue} -> "ambiguous"
  decide write / same_value   -> "ignore"
No retrieval is run; answer_regression的“是否拒答”需要活服务，单独标注未覆盖。
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT / "tools"))
import p1b_subject as P  # noqa: E402

HELD = Path("out/P1B-HELDOUT.jsonl")
OUT = Path("out/P1B-C2-HELDOUT-REPORT.json")


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


def apply_stmt(side, stmt, ts, next_id):
    """Run one prior statement through the same decision path; act on it."""
    res = P.decide(stmt, ts, side)
    act = res.get("action")
    info = res.get("info")
    if act in ("write", "supersede") and info and info.get("value"):
        eid = str(next_id)
        side.data["entries"][eid] = {
            "block_id": next_id, "text_sha256": P.sha_text(stmt),
            "created_at": str(ts), "subject": info["subject"],
            "predicate": info["predicate"], "value": info["value"],
            "subject_source": info["subject_source"],
            "supersedes": None, "superseded_by": None, "ambiguous": False,
        }
        if act == "supersede" and res.get("target") is not None:
            old = side.data["entries"].get(str(res["target"]))
            if old is not None:
                old["superseded_by"] = eid
                side.data["entries"][eid]["supersedes"] = res["target"]
        return next_id + 1
    return next_id


def main():
    raw = HELD.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    cases = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
    rows = []
    for c in cases:
        side = P.Sidecar(os.path.join(tempfile.mkdtemp(prefix="p1b_"), "side.json"))
        nid = 9001
        for i, stmt in enumerate((c.get("setup") or [])[:-1]):
            nid = apply_stmt(side, stmt, "2026-10-30T10:00:%02d" % i, nid)
        if c.get("setup"):
            res = P.decide((c["setup"])[-1], "2026-10-30T10:00:59", side)
        else:
            res = {"action": "write", "reason": "no_setup"}
        got = label_of(res)
        tgt = c.get("target_block") or {}
        tgt_ok = None
        if got == "supersede" and tgt.get("kind") == "baseline" and res.get("target") is not None:
            tgt_ok = (int(res["target"]) == int(tgt["id"]))
        rows.append({
            "id": c["id"], "group": c["group"], "kind": c.get("kind"),
            "query": c.get("query"), "expected": c.get("expected_action"),
            "got": got, "raw_action": res.get("action"), "reason": res.get("reason"),
            "raw_target": res.get("target"), "target_expected": tgt,
            "target_ok": tgt_ok, "match": got == c.get("expected_action"),
            "must_answer": c.get("must_answer"),
            "note": c.get("note"),
        })
    def group_stats(g):
        rs = [r for r in rows if r["group"] == g]
        return {"n": len(rs), "match": sum(1 for r in rs if r["match"])}
    stats = {g: group_stats(g) for g in ("chain", "answer_regression", "negation")}
    stats["all"] = {"n": len(rows), "match": sum(1 for r in rows if r["match"]),
                    "rate": round(sum(1 for r in rows if r["match"]) / len(rows), 4)}
    false_sup = [r["id"] for r in rows if r["got"] == "supersede" and r["expected"] != "supersede"]
    miss_sup = [r["id"] for r in rows if r["expected"] == "supersede" and r["got"] != "supersede"]
    wrong_ask = [r["id"] for r in rows if r["got"] == "ask" and r["expected"] not in ("ask",)]
    wrong_amb = [r["id"] for r in rows if r["got"] == "ambiguous" and r["expected"] != "ambiguous"]
    out = {"schema": "p1b_c2_heldout_report_v1", "heldout_sha256": sha,
           "n": len(rows), "stats": stats,
           "errors": {"false_supersede": false_sup, "missed_supersede": miss_sup,
                      "ask_mismatch": wrong_ask, "ambiguous_mismatch": wrong_amb},
           "answer_regression": {"covered": False,
                                 "note": "本回放只走决策/写路径，未起服务；R01-R05 的“是否仍拒答”需活服务另测"},
           "rows": rows}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in rows:
        print("%-8s %-11s exp=%-9s got=%-9s (%s/%s) %s"
              % (r["id"], r["group"], r["expected"], r["got"], r["raw_action"],
                 r["reason"], "OK" if r["match"] else "MISS"))
    print(json.dumps(stats, ensure_ascii=False))
    print("errors", json.dumps(out["errors"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())