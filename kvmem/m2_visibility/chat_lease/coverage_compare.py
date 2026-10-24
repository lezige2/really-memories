# -*- coding: utf-8 -*-
"""Coverage + before/after log comparison (no numbers without the log lines behind them).

  python -X utf8 coverage_compare.py   -> run_coverage.json
"""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
LOGS = os.path.join(HERE, "logs")
BEFORE = os.path.join(ROOT, "kvmem", "lease_events.jsonl.b")   # A-era log (proxy logged, never gated)


def rows_of(path):
    if not os.path.exists(path):
        return [], None, 0
    blob = open(path, "rb").read()
    rows = [json.loads(l) for l in blob.decode("utf-8").splitlines() if l.strip()]
    return rows, hashlib.sha256(blob).hexdigest(), blob.count(b"\n")


def digest(path):
    rows, sha, lines = rows_of(path)
    return {"path": path, "sha256": sha, "lines": lines}


# -- before: the same restore path, in the A-era where the proxy only recorded --
b_rows, b_sha, b_lines = rows_of(BEFORE)
before_resets = [r for r in b_rows if r.get("site") == "session_state.reset"]
before_block = [r for r in before_resets if int(r.get("seq") or 0) >= 1]
before_dialogue = [r for r in before_resets if int(r.get("seq") or 0) == 0]

# -- after: the load round trip of the current code (per-run log, path+sha in its own json) --
rt = json.load(open(os.path.join(HERE, "run_rt_post_on.json"), encoding="utf-8"))
a_rows, a_sha, a_lines = rows_of(rt["log"]["events"])
after_resets = [r for r in a_rows if r.get("site") == "session_state.reset"]
after_gated = [r for r in a_rows if r.get("kind") == "reset" and r.get("site") == "session_state.reset"]
after_dialogue = [r for r in after_resets if r.get("reason") == "dialogue_seq"]
after_block_unguarded = [r for r in a_rows
                         if r.get("kind") == "unguarded_reset"
                         and int(r.get("seq") or 0) >= 1
                         and r.get("reason") != "unregistered_seq"]

sites = json.load(open(os.path.join(HERE, "run_coverage_sites.json"), encoding="utf-8"))
load = json.load(open(os.path.join(HERE, "run_load.json"), encoding="utf-8"))
bridge = json.load(open(os.path.join(HERE, "run_bridge.json"), encoding="utf-8"))

res = {
    "schema": "chat_lease_coverage_v2",
    "before": {"log": {"path": BEFORE, "sha256": b_sha, "lines": b_lines},
               "provenance": "A-era proxy: reset was logged (kind=unguarded_reset) but not gated; "
                              "these lines come from the same session_state.restore path",
               "block_seq_resets": before_block, "dialogue_seq_resets": before_dialogue},
    "after": {"log": digest(rt["log"]["events"]),
              "gated_block_resets": after_gated,
              "dialogue_seq_exception": after_dialogue,
              "block_seq_unguarded": after_block_unguarded},
    "counts": {"before_block_seq_unguarded": len(before_block),
               "after_block_seq_unguarded": len(after_block_unguarded),
               "after_gated_block_resets": len(after_gated),
               "after_dialogue_exception": len(after_dialogue),
               "unregistered_seq_exception": load["coverage"]["unregistered_seq_exception"],
               "refusals_during_legal_restore": load["restore"]["refused_during_restore"],
               "range_mismatch": load["coverage"]["range_mismatch"]},
    "sites": {"log": sites["log"], "counts": sites["log"]["sites"],
              "commands": {"chat.place.fresh": "python -X utf8 tools/chat.py",
                           "slots.place.fresh": "python -X utf8 tools/chat.py save",
                           "m1.mount.before_load": "python -X utf8 tools/chat.py m1",
                           "m1.unmount.after_detach": "python -X utf8 tools/chat.py m1"}},
    "roundtrip": {lbl: [p["sha16"] for p in json.load(
        open(os.path.join(HERE, "run_rt_%s.json" % lbl), encoding="utf-8"))["save"]["pairs"]]
        + [p["sha16"] for p in json.load(
            open(os.path.join(HERE, "run_rt_%s.json" % lbl), encoding="utf-8"))["load"]["pairs"]]
        for lbl in ("before", "b_after", "b_off", "post_on", "post_off")},
}
res["roundtrip_identical"] = len({tuple(v) for v in res["roundtrip"].values()}) == 1
res["ok"] = bool(res["counts"]["after_block_seq_unguarded"] == 0
                 and res["counts"]["after_gated_block_resets"] >= 2
                 and res["counts"]["after_dialogue_exception"] == 1
                 and res["counts"]["unregistered_seq_exception"] == 1
                 and res["counts"]["refusals_during_legal_restore"] == 0
                 and res["counts"]["range_mismatch"] == 0
                 and res["roundtrip_identical"]
                 and all(res["sites"]["counts"].get(s, 0) > 0 for s in (
                     "chat.place.fresh/reset", "slots.place.fresh/reset",
                     "m1.mount.before_load/reset", "m1.unmount.after_detach/reset")))
json.dump(res, open(os.path.join(HERE, "run_coverage.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(json.dumps({k: res[k] for k in ("counts", "roundtrip", "roundtrip_identical")},
                 ensure_ascii=False, indent=1))
print("before block-seq resets:")
for r in res["before"]["block_seq_resets"]:
    print("  " + json.dumps(r, ensure_ascii=False))
print("after block-seq resets:")
for r in res["after"]["gated_block_resets"]:
    print("  " + json.dumps(r, ensure_ascii=False))
print("after dialogue exception:")
for r in res["after"]["dialogue_seq_exception"]:
    print("  " + json.dumps(r, ensure_ascii=False))
print("[RUN] wrote run_coverage.json")
