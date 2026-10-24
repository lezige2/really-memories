# -*- coding: utf-8 -*-
"""Acceptance harness: M5 grounding inside the M4 answer path.

  python -u -X utf8 m4_verify_grounded.py   -> run_m5_grounded.json

Every answer comes from a REAL child process (own pid) that routed, mounted a real block,
generated, and then grounded; nothing here is hand-filled except the questions.
"""
import hashlib, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, HERE)
import m5_bridge as BR                                            # noqa: E402

PY = sys.executable
ABL = os.path.join(HERE, "_ablate", "m4_memory_noplate.db")
CASES = [
    ("plate_main", "我车牌号是多少？", [], "routed"),
    ("plate_ablated", "我车牌号是多少？", ["--db", ABL, "--mount", "all"], "all"),
    ("home_main", "我住在哪？", [], "routed"),
    ("home_ablated", "我住在哪？", ["--db", ABL], "routed"),
]


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def child(extra):
    p = subprocess.run([PY, "-u", "-X", "utf8", os.path.join(HERE, "m4_answer_grounded.py")]
                       + extra, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    for line in (p.stdout or "").splitlines():
        if line.startswith("@@JSON@@"):
            return json.loads(line[len("@@JSON@@"):])
    raise SystemExit("no @@JSON@@ from %s\n%s\n%s" % (extra, p.stdout[-1500:], p.stderr[-1500:]))


def row(cid, d):
    g = d["grounding"]
    m = g["mount_evidence"]
    return {"case": cid, "pid": d["pid"], "question": d["query"], "db": d["db"],
            "mount_mode": m["mount_meta"]["mount_mode"],
            "routed_by": m["mount_meta"].get("routed_by"),
            "mounted": g["mounted"],
            "mount_evidence": {"cells_loaded": m["cells_loaded"],
                               "engine_cells_on_seq1": m["engine_cells_on_seq1"],
                               "cells_match_block_row": m["cells_match_block_row"],
                               "block_path": m["block_path"],
                               "block_sha256": m["block_sha256"],
                               "range": m["range"]},
            "verdict": g["verdict"], "reason": g["reason"], "topic_word": g["topic_word"],
            "hard_facts": g["hard_facts"], "hits": g["hits"], "unhit": g["unhit"],
            "exempt": g["exempt"], "undecidable_items": g["undecidable_items"],
            "flagged": g["flagged"],
            "answer_exact": d["answer_exact"], "answer": d["answer"],
            "display_pre_grounding": d["display_pre_grounding"],
            "m5_rewritten": g["m5_rewritten"], "display_policy": g["display_policy"],
            "answer_display": d["answer_display"],
            "display_trace": d["display_trace"]}


def main():
    res = {"schema": "m5_in_m4_answer_path_v1", "m5_db": BR.ensure_db(), "cases": []}
    for cid, q, extra, mode in CASES:
        d = child(["--q", q] + extra)
        r = row(cid, d)
        r["expected_mount_mode"] = mode
        res["cases"].append(r)
        print("[%s] %s -> %s (pid %s) mounted=%s" % (cid, q, r["verdict"], r["pid"],
                                                     r["mounted"]))

    by = {c["case"]: c for c in res["cases"]}
    # case 5: undecidable must be recorded and must NOT be rewritten (bridge level only)
    undec = BR.ground("我住在廣陵路 12 号 2 单元 602。",
                      {"mounted": [by["home_main"]["mounted"][0]],
                       "source": "bridge-level probe (no generation)", "mount_meta":
                       {"mount_mode": "reuse case 3 mount"}}, "我住在哪？")
    res["undecidable_case"] = {k: undec[k] for k in
                               ("verdict", "reason", "hard_facts", "undecidable_items",
                                "display_final", "display_changed_by_m5", "flagged",
                                "flag_note", "mounted")}
    res["undecidable_case"]["display_equals_input"] = (
        res["undecidable_case"]["display_final"] == "我住在廣陵路 12 号 2 单元 602。")

    def same_bytes(c):
        return c["answer_display"] == c["display_pre_grounding"]

    res["acceptance"] = {
        "1_plate_main_supported_display_unchanged":
            by["plate_main"]["verdict"] == "supported" and same_bytes(by["plate_main"]),
        "2_plate_ablated_unsupported_template":
            by["plate_ablated"]["verdict"] == "unsupported"
            and by["plate_ablated"]["answer_display"] == "记忆里没有记录车牌号。",
        "3_home_supported_under_both_blocks":
            all(by[k]["verdict"] == "supported" and same_bytes(by[k])
                for k in ("home_main", "home_ablated")),
        "4_four_records_complete":
            all(c["mounted"] and c["verdict"] and c["answer_display"] is not None
                and c["mount_evidence"]["block_sha256"] and c["hard_facts"] is not None
                and c["mount_evidence"]["cells_match_block_row"] for c in res["cases"]),
        "4b_three_values_recorded": sorted({by["plate_main"]["verdict"],
                                           by["plate_ablated"]["verdict"],
                                           by["home_main"]["verdict"],
                                           res["undecidable_case"]["verdict"]}),
    }
    # 5: the criteria file must be byte-identical to HEAD
    p = subprocess.run(["git", "diff", "--stat", "HEAD", "--",
                        "kvmem/m2_visibility/m5/m5_ground.py"],
                       cwd=ROOT, capture_output=True, text=True)
    res["m5_ground_diff"] = (p.stdout or "").strip()
    res["acceptance"]["5_m5_ground_unmodified"] = res["m5_ground_diff"] == ""
    det = subprocess.run(["git", "diff", "--stat", "HEAD", "--",
                          "kvmem/m2_visibility/m5"], cwd=ROOT, capture_output=True, text=True)
    res["m5_tree_diff"] = (det.stdout or "").strip()
    for label, path in (("m3_lease_untouched", "kvmem/m2_visibility/m3"),
                        ("m4_existing_files_untouched", "kvmem/m2_visibility/m4")):
        d = subprocess.run(["git", "status", "--porcelain", "--", path],
                           cwd=ROOT, capture_output=True, text=True)
        res[label] = [l for l in (d.stdout or "").splitlines() if not l.startswith("??")]
        res["acceptance"][label] = res[label] == []
    res["block_shas"] = {c["mounted"][0]: c["mount_evidence"]["block_sha256"]
                         for c in res["cases"]}
    res["block_shas"]["m5_text_copy_content"] = res["m5_db"]["content_sha256"]
    json.dump(res, open(os.path.join(HERE, "run_m5_grounded.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(res["acceptance"], ensure_ascii=False, indent=1))
    print(json.dumps({"m5_ground_diff": res["m5_ground_diff"] or "(empty)",
                      "block_shas": res["block_shas"]}, ensure_ascii=False, indent=1))
    print("[RUN] wrote run_m5_grounded.json")


if __name__ == "__main__":
    main()
