# -*- coding: utf-8 -*-
"""Stage 3 step 1: the M5 source is assembled from LAYER-1 human turns.

Run:  python -X utf8 kvmem/m2_visibility/m4/run_stage3.py
Writes run_stage3.json next to this file (untracked evidence, like the other run_*.json).

It does NOT rebuild any kvmem block file: the KV block content is not the source text.
"""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "m5"))

import memory_source as ms                                          # noqa: E402
import m5_bridge as BR                                              # noqa: E402
import m5_ground as G                                               # noqa: E402

DB = BR.DB_PATH
REG = os.path.join(ROOT, "kvmem", "chat.db")
PRE = os.path.join(HERE, "_stage3_pre.json")


def sha16_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def blocks_rows(con):
    cols = [r[1] for r in con.execute("PRAGMA table_info(blocks)")]
    out = {}
    for r in con.execute("SELECT %s FROM blocks ORDER BY block_id" % ",".join(cols)):
        d = dict(zip(cols, r))
        out[d["block_id"]] = d
    return cols, out


def content_sha16(con):
    """Definition: sha256(json.dumps([(block_id, sha256, source_text), ...],
    ensure_ascii=False).encode("utf-8"))[:16], ORDER BY block_id, default separators,
    no trailing newline, UTF-8. The block-file sha (sha256) is the disk hash of the
    kvmem file; neither is a hash of the other."""
    rows = list(con.execute("SELECT block_id, sha256, source_text FROM blocks ORDER BY block_id"))
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def err(fn, *a, **k):
    try:
        fn(*a, **k)
    except Exception as e:                                    # noqa: BLE001
        return {"raised": type(e).__name__, "message": str(e)[:400]}
    return {"raised": None, "message": None}


def main():
    res = {"schema": "stage3_step1_v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    pre = json.load(open(PRE, encoding="utf-8"))
    res["pre"] = {"file_sha16": pre["file_sha16"], "block_files": pre["block_files"]}

    # ---------- 1. rebuild the copy through the NEW selection path ----------
    BR.ensure_db()
    con = sqlite3.connect(DB)
    cols, post = blocks_rows(con)
    res["post"] = {"file_sha16": sha16_file(DB), "content_sha256_16": content_sha16(con),
                   "columns": cols}
    res["blocks"] = {}
    for bid, d in post.items():
        p = d["source_path"]
        res["blocks"][bid] = {
            "source_text_len": len(d["source_text"]),
            "source_text_sha256_16": hashlib.sha256(
                d["source_text"].encode("utf-8")).hexdigest()[:16],
            "text_origin": d["text_origin"], "text_origin_len": len(d["text_origin"]),
            "synthetic": d["synthetic"], "cells": d["cells"],
            "sha256_disk_16": d["sha256_disk"][:16], "note": d["note"],
            "block_file": {"path": p.replace(chr(92), "/"), "sha16": sha16_file(p),
                           "bytes": os.path.getsize(p), "mtime": os.path.getmtime(p)}}

    # ---------- 2. per-column change set (no whole-table hand-waving) ----------
    # A column that did not exist before is a SCHEMA addition, not a value drift: mixing the
    # two would let "added a column" hide inside "changed columns".
    changed, added_cols, per_block = set(), set(), {}
    for bid, d in post.items():
        old = pre["rows"][bid]
        cb = sorted(c for c in d if c in old and d[c] != old[c])
        per_block[bid] = {"changed": cb, "added_columns": sorted(c for c in d if c not in old)}
        changed |= set(cb)
        added_cols |= {c for c in d if c not in old}
    added = sorted(set(post) - set(pre["rows"]))
    removed = sorted(set(pre["rows"]) - set(post))
    res["row_sets"] = {"added_blocks": added, "removed_blocks": removed,
                       "counts": {"before": len(pre["rows"]), "after": len(post)},
                       "unit": "blocks rows (one per block_id), not columns",
                       "ok": added == [] and removed == []}
    res["changed_columns"] = {"set": sorted(changed),
                              "expected": ["source_text", "text_origin"],
                              "added": sorted(added_cols),
                              "added_expected": ["synthetic"],
                              "added_reason": "the synthetic column is NEW in Stage 3, so it is a schema addition; calling it a changed column would mix two different facts",
                              "per_block": per_block,
                              "ok": (sorted(changed) == ["source_text", "text_origin"]
                                     and sorted(added_cols) == ["synthetic"])}
    res["block_files_unchanged"] = {
        bid: {"sha_match": res["blocks"][bid]["block_file"]["sha16"] == pre["block_files"][bid]["sha16"],
              "bytes_match": res["blocks"][bid]["block_file"]["bytes"] == pre["block_files"][bid]["bytes"],
              "mtime_match": res["blocks"][bid]["block_file"]["mtime"] == pre["block_files"][bid]["mtime"],
              "sha16": res["blocks"][bid]["block_file"]["sha16"]}
        for bid in post}

    # ---------- 3. the two lengths, never compared with each other ----------
    reg = sqlite3.connect(REG)
    cid, ctext = reg.execute(
        "SELECT id, text FROM memory_source WHERE name='conv_2026-10-25'").fetchone()
    names = [r[0] for r in reg.execute("SELECT name FROM memory_source WHERE name LIKE 'conv_2026-10-25#%'")]
    bid_main = "blk_conv_2026-10-25_01"
    new_text = post[bid_main]["source_text"]
    res["quantities"] = {
        "source_text_len": {"before": len(ctext), "after": len(new_text)},
        "profile_blob_len": {"before": len(G.prep(ctext)), "after": len(G.prep(new_text)),
                             "definition": "len(m5_ground.prep(text)) -- the normalized blob inside source_profile"},
        "note": "two different quantities; never subtract one from the other"}

    # ---------- 4. lost_keys / gained_keys, both explicit ----------
    def keyset(t):
        p = G.source_profile([t])
        flat = {}
        for k in ("latin", "plate"):
            flat[k] = sorted(p[k])
        flat["nums"] = sorted(p["nums"])
        flat["dates"] = sorted(p["dates"])
        flat["props"] = sorted(p["props"])
        return flat
    ko, kn = keyset(ctext), keyset(new_text)
    res["keys"] = {k: {"old": ko[k], "new": kn[k], "same": ko[k] == kn[k]} for k in ko}
    res["lost_keys"] = sorted({x for k in ko for x in set(ko[k]) - set(kn[k])})
    res["gained_keys"] = sorted({x for k in ko for x in set(kn[k]) - set(ko[k])})

    # ---------- 5. (乙) evidence for every new constraint ----------
    ev = {}
    tmp = os.path.join(tempfile.gettempdir(), "_stage3_blocks.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    shutil.copy(DB, tmp)
    c = sqlite3.connect(tmp)
    c.execute("PRAGMA foreign_keys=ON")
    ins = ("INSERT OR REPLACE INTO blocks (block_id, family, model, cells, size_bytes, "
           "sha256, sha256_disk, sha_match, source_text, source_path, text_origin, note, "
           "synthetic) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)")
    good = ("probe", "m4", None, 1, 1, "a" * 64, "a" * 64, 1, "t", "p", "x", None, 0)

    def attempt(origin, synthetic):
        row = list(good)
        row[10] = origin
        row[12] = synthetic
        return err(c.execute, ins, tuple(row))

    ev["1_d3_1_null_origin"] = {
        "sql": "INSERT ... text_origin=NULL, synthetic=1",
        "null_with_synthetic_1": attempt(None, 1),
        "null_with_synthetic_0": attempt(None, 0),
        "prefix_without_flag": attempt("declared_synthetic:blk@0123456789abcdef", 0),
        "flag_without_prefix": attempt("registry:conv@d8c094c1f5fcb8f1", 1),
        "control_accepts_declared_synthetic": attempt("declared_synthetic:blk@0123456789abcdef", 1),
        "control_accepts_registry": attempt("registry:conv@d8c094c1f5fcb8f1", 0)}
    ev["1_d3_1_null_origin"]["ok"] = all([
        ev["1_d3_1_null_origin"]["null_with_synthetic_1"]["raised"] == "IntegrityError",
        ev["1_d3_1_null_origin"]["null_with_synthetic_0"]["raised"] == "IntegrityError",
        ev["1_d3_1_null_origin"]["prefix_without_flag"]["raised"] == "IntegrityError",
        ev["1_d3_1_null_origin"]["flag_without_prefix"]["raised"] == "IntegrityError",
        ev["1_d3_1_null_origin"]["control_accepts_declared_synthetic"]["raised"] is None,
        ev["1_d3_1_null_origin"]["control_accepts_registry"]["raised"] is None])

    ev["2_synthetic_domain"] = {"try_2": attempt("declared_synthetic:blk@0123456789abcdef", 2),
                                "try_3": attempt("declared_synthetic:blk@0123456789abcdef", 3)}
    ev["2_synthetic_domain"]["ok"] = (
        ev["2_synthetic_domain"]["try_2"]["raised"] == "IntegrityError")
    c.close()
    os.remove(tmp)

    main_origin = post[bid_main]["text_origin"]
    joined = new_text
    p16 = main_origin[:-16]
    ev["3_strict_64hex"] = {
        "parse_correct": {k: v for k, v in ms.parse_human_turns_origin(main_origin).items()
                          if k != "joined_sha256"},
        "parse_16hex": err(ms.parse_human_turns_origin, p16),
        "parse_63hex": err(ms.parse_human_turns_origin, main_origin[:-1]),
        "parse_65hex": err(ms.parse_human_turns_origin, main_origin + "0"),
        "parse_uppercase": err(ms.parse_human_turns_origin, main_origin[:-64] + "A" * 64)}
    m3 = (ev["3_strict_64hex"]["parse_16hex"]["raised"] == "OriginBadLength"
          and "64 hex" in (ev["3_strict_64hex"]["parse_16hex"]["message"] or "")
          and ev["3_strict_64hex"]["parse_65hex"]["raised"] == "OriginBadLength"
          and ev["3_strict_64hex"]["parse_uppercase"]["raised"] == "OriginBadLength")
    ev["3_strict_64hex"]["ok"] = m3

    shuffled = main_origin.replace("L1,L3,L4,L5,L7,L8,L9", "L9,L8,L7,L5,L4,L3,L1")
    ev["4_line_order"] = {
        "shuffled": shuffled[:120] + "...",
        "raised": err(ms.verify_human_turns_origin, reg, shuffled, joined),
        "same_members_as_set": sorted([1, 3, 4, 5, 7, 8, 9]) == sorted([9, 8, 7, 5, 4, 3, 1]),}
    ev["4_line_order"]["ok"] = (
        ev["4_line_order"]["raised"]["raised"] == "OriginLinesChanged"
        and "行集/顺序不符" in (ev["4_line_order"]["raised"]["message"] or ""))

    ev["5_cross_lock_8"] = {
        "control_correct": err(ms.verify_human_turns_origin, reg, main_origin, joined),
        "self_consistent_but_wrong_text": err(ms.verify_human_turns_origin, reg, main_origin,
                                              joined + "（另一段文本）")}
    ev["5_cross_lock_8"]["ok"] = (
        ev["5_cross_lock_8"]["control_correct"]["raised"] is None
        and ev["5_cross_lock_8"]["self_consistent_but_wrong_text"]["raised"] == "OriginJoinedMismatch"
        and "source_text" in (ev["5_cross_lock_8"]["self_consistent_but_wrong_text"]["message"] or ""))

    ev["6_joined_not_in_container"] = {
        "joined_in_container": joined in ctext,
        "all_lines_in_container": all(t in ctext for t in joined.split(chr(10))),
        "ok": (joined not in ctext) and all(t in ctext for t in joined.split(chr(10)))}
    res["evidence"] = ev
    res["constraints_ok"] = all(v.get("ok") is True for v in ev.values() if isinstance(v, dict))

    # ---------- 6. gate call site + 139-char round-trip ----------
    src = open(os.path.join(HERE, "m5_bridge.py"), encoding="utf-8").read().split(chr(10))
    res["gate_call_sites"] = [{"file": "m5_bridge.py", "line": i + 1, "text": l.strip()}
                              for i, l in enumerate(src)
                              if "assert_m5_source_allowed(" in l and l.strip().startswith("ms.")]
    res["todo_stage3_present"] = sum(1 for l in src if "TODO(stage3)" in l)
    tdb = os.path.join(tempfile.gettempdir(), "_origin_rt.db")
    if os.path.exists(tdb):
        os.remove(tdb)
    t = sqlite3.connect(tdb)
    t.execute("CREATE TABLE b (id TEXT PRIMARY KEY, text_origin TEXT NOT NULL)")
    t.execute("INSERT INTO b VALUES (?,?)", ("blk", main_origin))
    t.commit()
    back = t.execute("SELECT text_origin, length(text_origin) FROM b WHERE id='blk'").fetchone()
    t.close()
    os.remove(tdb)
    res["origin_roundtrip"] = {
        "sql": "INSERT INTO b(id, text_origin) VALUES ('blk', ?) / SELECT text_origin, length(text_origin) FROM b WHERE id='blk'",
        "chars_out": back[1], "byte_equal": back[0] == main_origin,
        "column_type": "TEXT (no length limit)", "ok": back[0] == main_origin}
    reg.close()
    con.close()

    res["status"] = {
        "S3-1_joined_not_substring": "通过" if ev["6_joined_not_in_container"]["ok"] else "未通过",
        "S3-2_origin_parse_verify": "通过" if all(ev[k]["ok"] for k in
                                     ("3_strict_64hex", "4_line_order", "5_cross_lock_8")) else "未通过",
        "S3-3_gate_wired_in_production_path": "按计划未到",
        "S3-4_no_todo_stage3": "按计划未到",
        "M5_product_usable": "失锚（待重跑）",
        "lost_keys_empty": "通过" if res["lost_keys"] == [] else "未通过",
        "row_sets_unchanged": "通过" if res["row_sets"]["ok"] else "未通过",
        "changed_columns_exact": "通过" if res["changed_columns"]["ok"] else "未通过",  # changed={source_text,text_origin}, added={synthetic}
        "block_files_unchanged": "通过" if all(v["sha_match"] and v["bytes_match"] and v["mtime_match"]
                                            for v in res["block_files_unchanged"].values()) else "未通过",}
    json.dump(res, open(os.path.join(HERE, "run_stage3.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"status": res["status"], "changed": res["changed_columns"]["set"],
                      "lost_keys": res["lost_keys"], "gained_keys": res["gained_keys"],
                      "quantities": res["quantities"]["source_text_len"],
                      "profile_blob_len": res["quantities"]["profile_blob_len"],
                      "file_sha16": res["post"]["file_sha16"],
                      "content_sha256_16": res["post"]["content_sha256_16"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()