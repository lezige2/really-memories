# -*- coding: utf-8 -*-
"""Acceptance table for the chat.py lease wiring.  python -X utf8 compare.py"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
CHAT = os.path.join(ROOT, "tools", "chat.py")
LABELS = ("before", "after", "revert")


def load(p):
    return json.load(open(os.path.join(HERE, p), encoding="utf-8")) if os.path.exists(
        os.path.join(HERE, p)) else None


def table():
    rows = {}
    for cmd in ("chat", "m1", "save"):
        rows[cmd] = []
        per = {lb: {p["q"]: p["sha16"] for p in (load("run_%s.json" % lb) or {}).get(cmd, {}).get("pairs", [])}
               for lb in LABELS}
        qs = [p["q"] for p in (load("run_before.json") or {}).get(cmd, {}).get("pairs", [])]
        for q in qs:
            rows[cmd].append({"q": q, **{lb: per[lb].get(q) for lb in LABELS},
                              "identical": len({per[lb].get(q) for lb in LABELS}) == 1})
    return rows


def main():
    src = open(CHAT, encoding="utf-8").read()
    bare = {
        "eng.reset(": len(re.findall(r"(?<!leases\.)\beng\.reset\(", src)),
        "eng.share(": len(re.findall(r"(?<!leases\.)\beng\.share\(", src)),
        "eng.drop(": len(re.findall(r"(?<!leases\.)\beng\.drop\(", src)),
        "safe_reset_all": len(re.findall(r"safe_reset_all", src)),
        "leases.reset(": len(re.findall(r"leases\.reset\(", src)),
    }
    rows = table()
    m2b, m2a = load("_m2_before.json"), load("_m2_after.json")
    ref = load("run_refusal.json")
    runs = {lb: load("run_%s.json" % lb) for lb in LABELS}
    res = {
        "schema": "chat_lease_compare_v1",
        "chat_py_sha16": {lb: (runs[lb] or {}).get("chat_py_sha16") for lb in LABELS},
        "answers": rows,
        "m2": {"cells_before": (m2b or {}).get("geometry", {}).get("cells_total"),
               "cells_after": (m2a or {}).get("geometry", {}).get("cells_total"),
               "answers_sha256_before": (m2b or {}).get("answers_sha256"),
               "answers_sha256_after": (m2a or {}).get("answers_sha256"),
               "geometry_identical": (m2b or {}).get("geometry") == (m2a or {}).get("geometry"),
               "all_hits": (m2a or {}).get("all_hits")},
        "static": bare,
        "refusal": {"refused": (ref or {}).get("refused"),
                    "cells_unchanged": ((ref or {}).get("after_refusal") or {}).get("cells_unchanged"),
                    "message": (ref or {}).get("message"),
                    "logged_lines": len((ref or {}).get("log_lines") or [])},
    }
    all_identical = all(r["identical"] for cmd in rows.values() for r in cmd)
    res["acceptance"] = {
        "1_m2_51cell_sha_identical": (res["m2"]["answers_sha256_before"] ==
                                     res["m2"]["answers_sha256_after"] is not None)
                                     or bool(res["m2"]["answers_sha256_before"]) and
                                     res["m2"]["answers_sha256_before"] == res["m2"]["answers_sha256_after"],
        "1b_product_answers_identical_3_labels": all_identical,
        "2_no_bare_reset_and_no_safe_reset_all": (bare["eng.reset("] == 0 and bare["eng.share("] == 0
                                                  and bare["eng.drop("] == 0
                                                  and bare["safe_reset_all"] == 0
                                                  and bare["leases.reset("] == 4),
        "3_refusal_recorded": bool(res["refusal"]["refused"]) and res["refusal"]["logged_lines"] >= 1,
        "4_refusal_engine_untouched": bool(res["refusal"]["cells_unchanged"]),
        "5_revert_still_identical": all(r["identical"] for cmd in rows.values() for r in cmd),
        "6_rc_zero_every_run": all((runs[lb] or {}).get(k, {}).get("rc") == 0
                                   for lb in LABELS if runs[lb]
                                   for k in ("chat", "m1", "save")),
    }
    m2_rc = [k.get("kvshim_ask_at_return_bytes") for k in (m2a or {}).get("asks", [])]
    non_empty = all(p["chars"] > 0 for lb in LABELS if runs[lb]
                    for cmd in ("chat", "m1", "save")
                    for p in runs[lb].get(cmd, {}).get("pairs", []))
    res["return_codes"] = {"m2_ask_bytes": m2_rc,
                           "m2_ask_all_positive": bool(m2_rc) and all((x or 0) > 0 for x in m2_rc),
                           "product_answers_non_empty": non_empty}
    res["acceptance"]["7_rc_positive_and_answers_non_empty"] = bool(
        res["return_codes"]["m2_ask_all_positive"] and non_empty)
    res["acceptance"]["all_pass"] = all(v for k, v in res["acceptance"].items())
    json.dump(res, open(os.path.join(HERE, "run_compare.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("static:", json.dumps(bare, ensure_ascii=False))
    for cmd, rs in rows.items():
        for r in rs:
            print("  %-5s %-26s %s %s %s  %s" % (cmd, r["q"][:24], r["before"], r["after"],
                                                 r["revert"], "OK" if r["identical"] else "DIFF"))
    print("m2 cells", res["m2"]["cells_before"], "->", res["m2"]["cells_after"],
          "| sha identical", res["m2"]["answers_sha256_before"] == res["m2"]["answers_sha256_after"])
    print("acceptance:", json.dumps(res["acceptance"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
