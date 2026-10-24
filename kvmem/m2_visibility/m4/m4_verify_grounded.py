# -*- coding: utf-8 -*-
"""Acceptance harness: M5 grounding inside the M4 answer path (R12 form).

  python -u -X utf8 m4_verify_grounded.py   -> run_m5_grounded.json

A paired assertions | B four quadrants | C shape of the criteria-file change
D before/after by really running the pre-R12 module | E undecidable kept verbatim
Every conclusion carries artifact sha256 (short 16 hex), see .delivery_anchor.
"""
import hashlib, importlib.util, io, json, os, sqlite3, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, HERE)
import m5_bridge as BR                                            # noqa: E402

PY = sys.executable
ABL = os.path.join(HERE, "_ablate", "m4_memory_noplate.db")
PRE_COMMIT = "e172aca"
MAIN = "blk_conv_2026-10-25_01"
TEMPLATE_PLATE = "记忆里没有记录车牌号。"
CASES = [
    ("plate_main", "我车牌号是多少？", [], "routed"),
    ("plate_ablated", "我车牌号是多少？", ["--db", ABL, "--mount", "all"], "all"),
    ("home_main", "我住在哪？", [], "routed"),
    ("home_ablated", "我住在哪？", ["--db", ABL], "routed"),
]


# R12: the object is a POSITIVELY ENUMERATED set of M4 product files, and the judgement asks
# whether each one still holds its recorded content -- not whether it is committed. A git
# status check answers a different question: an uncommitted-but-unchanged file looks dirty
# (false alarm) and a committed-but-rewritten file looks clean (false all-clear).
M4_UNTOUCHED = [
    ("m4_memory.db", "before_copy"),
    ("_ablate/m4_memory_noplate.db", "before_copy"),
    ("_stage3_pre.json", "before_copy"),
    ("blocks/blk_conv_2026-10-25_01.kvmem", "stage3_pre.block_files"),
    ("_ablate/blocks/blk_conv_noplate_2026-10-25_01.kvmem", "stage3_pre.block_files"),
]


def m4_files_untouched_or_registered():
    """Each enumerated object is either byte-identical to a registered copy of itself in
    _before/, or equal to the sha that _stage3_pre.json recorded before this step ran."""
    before = os.path.join(HERE, "_before")
    reg = json.load(open(os.path.join(before, "REGISTER.json"), encoding="utf-8"))
    by_base = {}
    for e in reg.get("entries", []):
        cp = e.get("copy_path")
        if cp:
            by_base[os.path.basename(cp)] = e
    pre = json.load(open(os.path.join(HERE, "_stage3_pre.json"), encoding="utf-8"))
    out = {}
    for rel, anchor in M4_UNTOUCHED:
        path = os.path.join(HERE, rel.replace("/", os.sep))
        cur = sha_file(path, 16) if os.path.exists(path) else None
        if anchor == "before_copy":
            base = "%s@%s" % (os.path.basename(rel), cur)
            e = by_base.get(base)
            out[rel] = {"anchor": "registered copy", "current_sha16": cur,
                        "registered_as": base if e else None,
                        "reason": (e or {}).get("reason"),
                        "ok": bool(e) and e.get("source_sha16") == cur and bool(e.get("reason"))}
        else:
            key = os.path.splitext(os.path.basename(rel))[0]
            want = (pre.get("block_files", {}).get(key) or {}).get("sha16")
            out[rel] = {"anchor": "_stage3_pre.json block_files", "current_sha16": cur,
                        "expected_sha16": want, "ok": cur is not None and cur == want}
    return {"name": "m4_files_untouched_or_registered",
            "objects_are": "positively enumerated M4 product files, not 'everything minus this "
                           "run own artefacts'",
            "judgement": "byte-identical to a registered copy in _before/, or equal to the sha "
                         "_stage3_pre.json recorded before this step",
            "git_status_not_used": "that answers whether a file is committed, not whether it "
                                   "is unchanged",
            "objects": out,
            "ok": all(v["ok"] for v in out.values()),
            "_failures": [k for k, v in out.items() if not v["ok"]]}


def sha_file(p, n=64):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:n]


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
            "mount_mode": m["mount_meta"]["mount_mode"], "mount_meta": m["mount_meta"],
            "mounted": g["mounted"],
            "mount_evidence": {"cells_loaded": m["cells_loaded"],
                               "engine_cells_on_seq1": m["engine_cells_on_seq1"],
                               "cells_match_block_row": m["cells_match_block_row"],
                               "block_path": m["block_path"],
                               "block_sha256": m["block_sha256"], "range": m["range"],
                               "retrieval_probe": m.get("retrieval_probe")},
            "verdict": g["verdict"], "reason": g["reason"], "topic_word": g["topic_word"],
            "hard_facts": g["hard_facts"], "hits": g["hits"], "unhit": g["unhit"],
            "exempt": g["exempt"], "undecidable_items": g["undecidable_items"],
            "flagged": g["flagged"], "input_origin": g["input_origin"],
            "synthetic": g["synthetic"], "answer_exact": d["answer_exact"],
            "answer": d["answer"], "display_pre_grounding": d["display_pre_grounding"],
            "m5_rewritten": g["m5_rewritten"], "display_policy": g["display_policy"],
            "answer_display": d["answer_display"], "display_trace": d["display_trace"]}


def load_pre_module():
    # R11: this module is GENERATED here and imported immediately. Writing it into _before/
    # turned the evidence directory into a scratch area (and its __pycache__ with it), which is
    # why a bare .py kept reappearing among the registered copies. Scratch lives in TEMP now.
    d = tempfile.mkdtemp(prefix="m5_scratch_")
    src = subprocess.run(["git", "show", PRE_COMMIT + ":kvmem/m2_visibility/m5/m5_ground.py"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    if "def a_hit" not in src:
        raise SystemExit("pre-R12 source not recovered")
    path = os.path.join(d, "m5_ground_preR12.py")
    open(path, "w", encoding="utf-8").write(src)
    spec = importlib.util.spec_from_file_location("m5_ground_preR12", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, {"commit": PRE_COMMIT, "path": path, "scratch_dir": d,
                 "not_in_before": True, "sha256": sha_file(path)}


def verdict(mod, text, block, q):
    return mod.ground(text, [block], q, db=BR.DB_PATH)["verdict"]


def main():
    import m5_ground as G
    res = {"schema": "m5_in_m4_answer_path_r12_v2", "m5_db": BR.ensure_db(), "cases": []}
    for cid, q, extra, mode in CASES:
        r = row(cid, child(["--q", q] + extra))
        r["expected_mount_mode"] = mode
        res["cases"].append(r)
        print("[%s] %s -> %s (pid %s) mounted=%s %s" % (cid, q, r["verdict"], r["pid"],
                                                        r["mounted"], r["mount_mode"]))
    by = {c["case"]: c for c in res["cases"]}

    # ---------------- A ----------------
    pm, pa = by["plate_main"], by["plate_ablated"]
    pa_unhit_raws = [u.get("raw") for u in pa["unhit"]]
    res["paired_assertions"] = {
        "A1_plate_main": {
            "verdict": pm["verdict"],
            "display_equal_pre_grounding": pm["answer_display"] == pm["display_pre_grounding"],
            "answer_display": pm["answer_display"],
            "display_pre_grounding": pm["display_pre_grounding"],
            "pass": pm["verdict"] == "supported"
                    and pm["answer_display"] == pm["display_pre_grounding"]},
        "A2_plate_ablated": {
            "verdict": pa["verdict"],
            "display_is_template": pa["answer_display"] == TEMPLATE_PLATE,
            "unhit_raws": pa_unhit_raws,
            "unhit_contains_plate": any("苏K12345" in (r or "") for r in pa_unhit_raws),
            "pass": pa["verdict"] == "unsupported"
                    and pa["answer_display"] == TEMPLATE_PLATE
                    and any("苏K12345" in (r or "") for r in pa_unhit_raws)},
    }
    res["paired_assertions"]["both_pass"] = all(
        v["pass"] for k, v in res["paired_assertions"].items() if k.startswith("A"))

    # ---------------- B ----------------
    con = sqlite3.connect(BR.DB_PATH)
    texts_main, _probs = G.verify_sources(con, [MAIN])
    con.close()
    prof_main = G.source_profile(texts_main)
    q_plate = "我车牌号是多少？"

    def g(text, block=MAIN, question=q_plate):
        return BR.ground(text, {"mounted": [block]}, question)

    a_wrong = g("您的车牌是苏B-3F19K。")
    b_spell = {s: g("您的车牌是%s。" % s) for s in ("浙B-3F19K", "浙B 3F19K",
                                                    "浙b3f19k", "浙B3F19K")}
    bare = G.extract("B3F19K")
    c_bare = {"facts_from_extract": bare, "fact_count": len(bare),
              "families": [f["family"] for f in bare], "claimed_once": len(bare) == 1,
              "a_hit": G.a_hit(bare[0]["key"], prof_main) if bare else None,
              "hit_reason": ("latin set already contains B3F19K from RE_CODE, so this is a "
                             "BODY match that exists before and after R12 (a_hit has no plate "
                             "branch); RE_PLATE needs a leading CJK char, so the bare body is "
                             "never claimed twice"),
              "classified_as": "A 族代号类（RE_CODE），不是车牌类（RE_PLATE）"}
    d_sym = BR.a_family_symmetry(texts_main)
    res["quadrants"] = {
        "a_wrong_province_same_body": {
            "text": "您的车牌是苏B-3F19K。", "block": MAIN, "block_plate": "浙B-3F19K",
            "verdict": a_wrong["verdict"], "hard_facts": a_wrong["hard_facts"],
            "display": a_wrong["display_final"],
            "pass": a_wrong["verdict"] == "unsupported"},
        "b_three_spellings_same_plate": {
            s: {"verdict": r["verdict"], "hard_facts": r["hard_facts"]}
            for s, r in b_spell.items()},
        "c_bare_body": c_bare,
        "d_extraction_symmetry": d_sym,
    }
    res["quadrants"]["b_three_spellings_same_plate"]["all_supported"] = all(
        r["verdict"] == "supported" for r in b_spell.values())
    res["quadrants"]["pass"] = (
        res["quadrants"]["a_wrong_province_same_body"]["pass"]
        and res["quadrants"]["b_three_spellings_same_plate"]["all_supported"]
        and c_bare["claimed_once"] and d_sym["verdict"])

    # ---------------- C ----------------
    diff = subprocess.run(["git", "diff", PRE_COMMIT, "--",
                           "kvmem/m2_visibility/m5/m5_ground.py"],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    added = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:] for l in diff.splitlines()
               if l.startswith("-") and not l.startswith("---")]
    pre_src = subprocess.run(["git", "show", PRE_COMMIT + ":kvmem/m2_visibility/m5/m5_ground.py"],
                             cwd=ROOT, capture_output=True, text=True,
                             encoding="utf-8").stdout

    def a_hit_block(src):
        if "def a_hit" not in src:
            return ""
        return "def a_hit" + src.split("def a_hit", 1)[1].split("\n\n", 1)[0].strip("\n")

    cur_src = open(os.path.join(ROOT, "kvmem", "m2_visibility", "m5", "m5_ground.py"),
                   encoding="utf-8").read()
    grep = subprocess.run(["grep", "-n", "alnum_key(",
                           "kvmem/m2_visibility/m5/m5_ground.py"],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    res["shape"] = {
        "diff_against": PRE_COMMIT,
        "added_lines": added, "removed_lines": removed,
        "touches_def_a_hit": any("def a_hit" in l for l in added + removed),
        "a_hit_body_identical_to_pre": a_hit_block(cur_src) == a_hit_block(pre_src),
        "a_hit_body_now": a_hit_block(cur_src),
        "alnum_key_call_sites": [l for l in grep.splitlines()
                                 if l.strip() and "def alnum_key" not in l],
        "defs_touched": sorted({l.split("(")[0].replace("def ", "").strip()
                                for l in added + removed if l.strip().startswith("def ")}),
    }
    res["shape"]["pass"] = (not res["shape"]["touches_def_a_hit"]
                            and res["shape"]["a_hit_body_identical_to_pre"]
                            and len(res["shape"]["alnum_key_call_sites"]) >= 2)

    # ---------------- D ----------------
    pre, pre_meta = load_pre_module()
    # a random temp path in the artefact would make every run differ in shape; record what
    # is reproducible instead (same source, same place-by-construction)
    res["before_module"] = {"commit": pre_meta["commit"],
                            "sha256": pre_meta["sha256"],
                            "scratch": "tempfile.mkdtemp('m5_scratch_')/m5_ground_preR12.py",
                            "not_in_before": True,
                            "why": "generated at run time and imported immediately; keeping it in _before/ turned the evidence directory into a scratch area"}
    d_rows = []
    for cid in ("plate_main", "plate_ablated", "home_main", "home_ablated"):
        c = by[cid]
        before = verdict(pre, c["display_pre_grounding"], c["mounted"][0], c["question"])
        d_rows.append({"case": cid, "question": c["question"], "block": c["mounted"][0],
                       "verdict_before": before, "verdict_after": c["verdict"],
                       "changed": before != c["verdict"]})
    probe_rows = []
    for label, text, expect in (
            ("a_wrong_province(苏B-3F19K)", "您的车牌是苏B-3F19K。", "unsupported"),
            ("b1(浙B-3F19K)", "您的车牌是浙B-3F19K。", "supported"),
            ("b2(浙B 3F19K)", "您的车牌是浙B 3F19K。", "supported"),
            ("b3(浙b3f19k)", "您的车牌是浙b3f19k。", "supported"),
            ("b4(浙B3F19K)", "您的车牌是浙B3F19K。", "supported"),
            ("c1_body_after_CJK(是B3F19K)", "您的车牌是B3F19K。", "unsupported"),
            ("c2_true_bare_body(车牌:B3F19K)", "车牌:B3F19K。", "supported")):
        before = verdict(pre, text, MAIN, q_plate)
        after = verdict(G, text, MAIN, q_plate)
        probe_rows.append({"probe": label, "verdict_before": before,
                           "verdict_after": after, "expected_after": expect,
                           "changed": before != after, "ok": after == expect})
    res["before_after"] = {
        "product_four": d_rows, "probes": probe_rows,
        "only_plate_main_flipped": all(r["changed"] == (r["case"] == "plate_main")
                                       for r in d_rows),
        "probes_all_ok": all(r["ok"] for r in probe_rows),
    }
    res["before_after"]["pass"] = (res["before_after"]["only_plate_main_flipped"]
                                   and res["before_after"]["probes_all_ok"])

    # ---------------- E ----------------
    undec = BR.ground("我住在廣陵路 12 号 2 单元 602。",
                      {"mounted": [MAIN],
                       "source": "bridge-level probe (no generation)",
                       "input_origin": "literal in m4_verify_grounded.py: undecidable probe",
                       "synthetic": True,
                       "mount_meta": {"mount_mode": "reuse home_main mount"}},
                      "我住在哪？")
    res["undecidable_case"] = {
        "verdict": undec["verdict"], "reason": undec["reason"],
        "input_origin": undec["input_origin"], "synthetic": undec["synthetic"],
        "mounted": undec["mounted"], "hard_facts": undec["hard_facts"],
        "undecidable_items": undec["undecidable_items"],
        "display_final": undec["display_final"],
        "display_changed_by_m5": undec["display_changed_by_m5"],
        "display_equals_input": undec["display_final"] == "我住在廣陵路 12 号 2 单元 602。",
        "flagged": undec["flagged"], "flag_note": undec["flag_note"],
        "pass": undec["verdict"] == "undecidable" and not undec["display_changed_by_m5"],
    }

    # ---------------- unit-count convention (dead-locked in README) ----------------
    mdb = sqlite3.connect(os.path.join(HERE, "m4_memory.db"))
    units = mdb.execute("SELECT COUNT(DISTINCT unit_id) FROM memory").fetchone()[0]
    fanout = [r[0] for r in mdb.execute(
        "SELECT COUNT(*) FROM memory GROUP BY unit_id ORDER BY unit_id")]
    src_rows = mdb.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0]
    seg_rows = [r[0] for r in mdb.execute(
        "SELECT name FROM memory_source WHERE name LIKE 'conv%'")]
    mdb.close()
    res["unit_count"] = {"retrieval_units": units, "fanout": fanout,
                         "memory_source_rows": src_rows,
                         "segment_level_rows": seg_rows,
                         "convention": "检索单元数 = distinct(unit_id)；memory_source 另含 1 条段级行"
                                       "（name=conv_*），它不是检索单元"}

    # ---------------- M5's own suite, raw ----------------
    ev = json.load(open(os.path.join(ROOT, "kvmem", "m2_visibility", "m5", "evidence_m5.json"),
                        encoding="utf-8"))
    acc = ev["acceptance"]
    res["evidence_m5"] = {"acceptance_raw": acc,
                          "all_pass": acc.get("all_pass"),
                          "false_positive": acc.get("false_positive"),
                          "false_negative": acc.get("false_negative"),
                          "four_cases": [{"case": c.get("case", c.get("name")),
                                          "I1": (c.get("i1") or {}).get("verdict"),
                                          "I2": (c.get("i2") or {}).get("verdict")}
                                         for c in (ev["four_cases"]
                                                   if isinstance(ev["four_cases"], list) else [])],
                          "boundary_cases": [{"case": b.get("case", b.get("name")),
                                              "verdict": b.get("verdict"),
                                              "expect": b.get("expect")}
                                             for b in (ev["boundary_cases"]
                                                       if isinstance(ev["boundary_cases"], list) else [])],
                          "cross_check_np64": ev["cross_check_np64"]}

    # ---------------- overall ----------------
    res["acceptance"] = {
        "A_paired_assertions": res["paired_assertions"]["both_pass"],
        "B_quadrants": res["quadrants"]["pass"],
        "C_shape": res["shape"]["pass"],
        "D_before_after": res["before_after"]["pass"],
        "E_undecidable_not_rewritten": res["undecidable_case"]["pass"],
        "form_invariant_all_four": acc.get("form_invariant_all_four"),
        "false_positive": acc.get("false_positive"),
        "false_negative": acc.get("false_negative"),
        "cells_match_block_row": all(c["mount_evidence"]["cells_match_block_row"]
                                     for c in res["cases"]),
    }
    res["m4_untouched"] = m4_files_untouched_or_registered()
    res["acceptance"][res["m4_untouched"]["name"]] = res["m4_untouched"]["ok"]
    st = subprocess.run(["git", "status", "--porcelain", "--", "kvmem/m2_visibility/m3"],
                        cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    dirty3 = [l for l in (st.stdout or "").splitlines() if not l.startswith("??")]
    res["m3_lease_untouched_dirty_files"] = dirty3
    res["acceptance"]["m3_lease_untouched"] = dirty3 == []
    res["block_shas"] = {c["mounted"][0]: c["mount_evidence"]["block_sha256"]
                         for c in res["cases"]}
    res["block_shas"]["m5_text_copy_content"] = res["m5_db"]["content_sha256"]
    run_sha = sha_file(os.path.join(HERE, "run_m5_grounded.json"), 16) \
        if os.path.exists(os.path.join(HERE, "run_m5_grounded.json")) else None
    cmp_sha = sha_file(os.path.join(HERE, "run_m5_fix_compare.json"), 16) \
        if os.path.exists(os.path.join(HERE, "run_m5_fix_compare.json")) else None
    # R3: which anchors this run invalidates -- five fields each.
    run_path = os.path.join(HERE, "run_m5_grounded.json")
    prev = sha_file(run_path, 16) if os.path.exists(run_path) else None
    res["invalidated_anchors"] = []
    if prev:
        res["invalidated_anchors"].append({
            "artifact": "run_m5_grounded.json",
            "old_sha16": prev,
            "new_sha16": None,
            "new_sha16_rule": ZERO_RULE,
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "reason": "rerun for the rework round R1-R9 (probe copy pinned, guard derived, "
                      "grade computed, added/changed columns split)",
            "expected_by": "SRC-CRITERIA.md 12.7 换源裁决不变: the verdicts must not move "
                           "when only the source text changes"})
    res["invalidated_anchors_history"] = [
        {"artifact": "run_m5_grounded.json", "old_sha16": "5cd106eead0c9bac",
         "new_sha16": None, "at": None, "grade": "A",
         "reason": "earlier rerun before Stage 3; its replacement sha was not recorded",
         "expected_by": "no criterion changed (same sources, same code)"},
        {"artifact": "run_m5_grounded.json", "old_sha16": "dd8703d1022cdeb9",
         "new_sha16": None, "at": None, "grade": "A",
         "reason": "earlier rerun before Stage 3; its replacement sha was not recorded",
         "expected_by": "no criterion changed (same sources, same code)"},
        {"artifact": "run_m5_grounded.json", "old_sha16": "d97cdfdc",
         "new_sha16": "d13df1e9", "at": "2026-10-25T05:05:32", "grade": "A",
         "reason": "Stage 3 step 2: gate wired at the source-selection site, TODO(stage3) "
                   "removed, P10 fix",
         "expected_by": "SRC-CRITERIA.md 12.7 换源裁决不变 (both sha16 transcribed from the "
                        "lead's independent recomputation)"}]
    res["delivery_anchor"] = {
        "note": "this json is written after these values are read, so run_m5_grounded.json "
                "and run_m5_fix_compare.json below describe the PREVIOUS run; the authoritative "
                "values are printed by the driver and recorded in README §19.10",
        "run_m5_grounded_json_previous_run": run_sha,
        "run_m5_fix_compare_json_previous_run": cmp_sha,
        "m5_ground.py": sha_file(os.path.join(ROOT, "kvmem", "m2_visibility", "m5",
                                              "m5_ground.py"), 16),
        "m5_ground_preR12.py": pre_meta["sha256"][:16],
        "m4_memory.db": sha_file(os.path.join(HERE, "m4_memory.db"), 16),
        "run_m4_verify.json": sha_file(os.path.join(HERE, "run_m4_verify.json"), 16)
        if os.path.exists(os.path.join(HERE, "run_m4_verify.json")) else None,
        "run_m4_write.json": sha_file(os.path.join(HERE, "run_m4_write.json"), 16)
        if os.path.exists(os.path.join(HERE, "run_m4_write.json")) else None,
        "blk_main.kvmem": sha_file(os.path.join(HERE, "blocks",
                                                MAIN + ".kvmem"), 16),
        "blk_noplate.kvmem": sha_file(os.path.join(HERE, "_ablate", "blocks",
                                                   "blk_conv_noplate_2026-10-25_01.kvmem"), 16),
        "invalidated_anchors_here_are_out_of_date_see_top_level_field": True,
        "invalidated_note": "两份 run json 在不同时间点被重跑过，旧 sha 一律失效；"
                            "README §19.10 记录 旧->失效->当前 的对照",
        "rule": "产物重跑、sha 变了 => 之前的验收结论自动失效，必须重新验收",
    }
    write_with_self_anchor(os.path.join(HERE, "run_m5_grounded.json"), res)
    print(json.dumps(res["paired_assertions"], ensure_ascii=False, indent=1))
    print(json.dumps(res["acceptance"], ensure_ascii=False, indent=1))
    print(json.dumps(res["before_after"], ensure_ascii=False, indent=1))
    print(json.dumps(res["quadrants"], ensure_ascii=False, indent=1))
    print(json.dumps(res["delivery_anchor"], ensure_ascii=False, indent=1))
    print("[RUN] wrote run_m5_grounded.json")


ZERO_RULE = ("new_sha16 = sha256 of the same file with every new_sha16 replaced by "
             "0000000000000000, dumped with ensure_ascii=False, indent=2; a file cannot "
             "contain its own sha and this rule makes the value recomputable")


def write_with_self_anchor(path, obj):
    """Write obj, filling each new_sha16 per ZERO_RULE."""
    def render():
        buf = io.StringIO()
        json.dump(obj, buf, ensure_ascii=False, indent=2)
        return buf.getvalue()
    for e in obj.get("invalidated_anchors", []):
        if e.get("new_sha16_rule") == ZERO_RULE:
            e["new_sha16"] = "0" * 16          # the placeholder the rule names
    sh = hashlib.sha256(render().encode("utf-8")).hexdigest()[:16]
    for e in obj.get("invalidated_anchors", []):
        if e.get("new_sha16_rule") == ZERO_RULE:
            e["new_sha16"] = sh
    open(path, "w", encoding="utf-8").write(render())


if __name__ == "__main__":
    main()
