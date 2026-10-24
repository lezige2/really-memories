# -*- coding: utf-8 -*-
"""Stage 1a: invariants of the authoritative source registry (kvmem/chat.db).

  python -u -X utf8 check_registry.py   -> run_registry_check.json

Nothing here writes to the authoritative db. The three write tests (idempotency,
refusal, tampering) run against copies in _test/, so the registry's own bytes stay
untouched and the M4 anchors stay valid.

What is proven, in the inspector's vocabulary:
  I1  one canonical row per text  -> assert_unique_texts + duplicate scan
  I2  verifiable                  -> read path recomputes sha256 and raises, not warns
  fail-closed                     -> a tampered copy makes the CONSUMER's own function
                                     (memory_source.get_source, the one chat.py calls)
                                     raise; the batch fails if any check returns instead
"""
import ast, hashlib, json, os, shutil, sqlite3, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import memory_source as ms                                        # noqa: E402

DB = os.path.join(ROOT, "kvmem", "chat.db")
TEST = os.path.join(HERE, "_test")
CHAT_PY = os.path.join(TOOLS, "chat.py")


def sha16(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def sha_file16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def copy_db(tag):
    os.makedirs(TEST, exist_ok=True)
    dst = os.path.join(TEST, "%s.db" % tag)
    if os.path.exists(dst):
        os.remove(dst)
    shutil.copy2(DB, dst)
    return dst


def must_raise(label, fn, types):
    """A check that returns instead of raising is a failure, not a warning."""
    try:
        out = fn()
    except types as e:
        return {"check": label, "raised": type(e).__name__, "message": str(e)[:300],
                "ok": True}
    return {"check": label, "raised": None, "returned_instead": repr(out)[:200],
            "ok": False, "why": "validation must fail closed, not return a value"}


def chat_memory_literal():
    """Does chat.py still carry a copy of the memory text? Read as source, never imported."""
    src = open(CHAT_PY, encoding="utf-8").read()
    tree = ast.parse(src)
    consts = [n for n in tree.body
              if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == "MEMORIES" for t in n.targets)]
    return {"memories_constant_present": bool(consts),
            "reads_indexable_sources": "ms.indexable_sources(" in src,
            "writes_sources_in_build": "ms.put_source(" in src}


def main():
    res = {"schema": "source_registry_invariants_1a_v1",
           "db": os.path.relpath(DB, ROOT).replace("\\", "/"),
           "db_sha16_before": sha_file16(DB)}
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")

    # ---------- 1. layer-1 hashes, both ends ----------
    rows = con.execute("SELECT id, name, label, text, source_hash, created_at "
                       "FROM memory_source ORDER BY id").fetchall()
    res["rows"] = [{"id": r[0], "name": r[1], "label": r[2], "chars": len(r[3]),
                    "stored_sha16": r[4][:16], "computed_sha16": sha16(r[3]),
                    "match": sha16(r[3]) == r[4][:16] and
                             hashlib.sha256(r[3].encode("utf-8")).hexdigest() == r[4],
                    "created_at": r[5]} for r in rows]
    res["row_count"] = len(rows)
    res["all_stored_hashes_self_consistent"] = all(r["match"] for r in res["rows"])

    # ---------- 2. I1 uniqueness ----------
    i1 = ms.assert_unique_texts(con)
    layers, flat = i1["layers"], i1["texts"]
    dup_in_layer = [("%s" % k, v) for k, layer in layers.items()
                    for v in layer.values() if len(v) > 1]
    cross = {k[:16]: v for k, v in flat.items() if len(v) > 1}
    res["I1_uniqueness"] = {
        "layers": {k: {"distinct_texts": len(v),
                       "rows": sum(len(x) for x in v.values())} for k, v in layers.items()},
        "distinct_texts_all_layers": len(flat),
        "row_count": len(rows),
        "one_row_per_text": (not dup_in_layer
                             and all(any("is_excerpt" in n for n in names) for names in cross.values())),
        "duplicates": dup_in_layer,
        "cross_layer_same_text": cross,
        "texts_by_sha16": cross,
        "assert_fn": "tools/memory_source.py::assert_unique_texts",
    }

    # ---------- 3. idempotent put (copy) ----------
    c1 = sqlite3.connect(copy_db("idem"))
    before = c1.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0]
    name0, _lbl0, text0 = ms.get_source(c1, rows[0][1])[4], None, None
    row0 = ms.get_source(c1, rows[0][1])
    sid_same, created = ms.put_source(c1, row0[4], row0[5], row0[6])
    after = c1.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0]
    res["put_idempotent"] = {"name": row0[4], "same_id": sid_same == row0[0],
                             "created": created, "rows_before": before, "rows_after": after,
                             "ok": (not created) and sid_same == row0[0] and before == after}
    c1.close()

    # ---------- 4. refusal of an implicit revision (copy) ----------
    c2 = sqlite3.connect(copy_db("refuse"))
    tgt = ms.get_source(c2, rows[0][1])
    mutated = tgt[6] + "（改）"
    r = must_raise("put_source(same name, different text)", 
                   lambda: ms.put_source(c2, tgt[4], tgt[5], mutated),
                   (ms.SourceConflict,))
    still = c2.execute("SELECT COUNT(*), text FROM memory_source WHERE name=?",
                       (tgt[4],)).fetchone()
    r["rows_for_name_after"] = still[0]
    r["text_unchanged"] = still[1] == tgt[6]
    r["ok"] = r["ok"] and still[0] == 1 and still[1] == tgt[6]
    res["put_refuses_implicit_revision"] = r

    # empty text must not become a row
    e = must_raise("put_source(name, '')", lambda: ms.put_source(c2, "blank_probe", "空白", "   "),
                   (ValueError,))
    res["put_refuses_empty_text"] = e
    c2.close()

    # ---------- 4b. negative test: the DATABASE itself refuses the UPDATE ----------
    c2b = sqlite3.connect(copy_db("trigger"))
    trig = must_raise(
        "UPDATE text with the immutability trigger in place",
        lambda: c2b.execute("UPDATE memory_source SET text = text || 'x' WHERE name = ?",
                            (tgt[4],)),
        (sqlite3.IntegrityError,))
    trig["trigger"] = c2b.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' "
        "AND name='memory_source_text_is_immutable'").fetchone()
    trig["ok"] = trig["ok"] and trig["trigger"] is not None
    res["trigger_layer_holds"] = trig
    c2b.close()

    # ---------- 5. negative test: tamper bypassing the trigger (copy) ----------
    c3 = sqlite3.connect(copy_db("tampered"))
    c3.execute("DROP TRIGGER memory_source_text_is_immutable")
    c3.execute("UPDATE memory_source SET text = text || '【篡改】' WHERE name = ?",
               (tgt[4],))
    c3.commit()
    tampered = c3.execute("SELECT text, source_hash FROM memory_source WHERE name=?",
                          (tgt[4],)).fetchone()
    nt = []
    nt.append(must_raise("consumer read: memory_source.get_source(name)",
                         lambda: ms.get_source(c3, tgt[4]), (ms.SourceHashMismatch,)))
    nt.append(must_raise("probe_text(id)", lambda: ms.probe_text(c3, tgt[0]),
                         (ms.SourceHashMismatch,)))
    nt.append(must_raise("assert_unique_texts(con)",
                         lambda: ms.assert_unique_texts(c3), (ms.SourceHashMismatch,)))
    probs = ms.verify(c3, blocks_dir=os.path.join(ROOT, "kvmem", "blocks"))
    nt.append({"check": "verify(con) report", "problems": probs,
               "ok": any("source_hash mismatch" in p for p in probs)})
    res["negative_test_tampered_copy"] = {
        "how": "copy of the registry, trigger dropped, text += '【篡改】', hash left alone",
        "text_after": tampered[0][-20:], "hash_left_at": tampered[1][:16],
        "checks": nt, "all_fail_closed": all(c["ok"] for c in nt)}
    c3.close()

    # ---------- 6. there is no second copy of the memory text (Stage 2) ----------
    lit = chat_memory_literal()
    res["no_second_copy_of_memory_text"] = {
        "how": "source scan of tools/chat.py (no import, no execution)",
        **lit,
        "registry_texts": [{"name": r[1], "chars": len(r[3]), "sha16": sha16(r[3])}
                           for r in rows],
        "ok": (not lit["memories_constant_present"]
               and lit["reads_indexable_sources"]
               and not lit["writes_sources_in_build"]),
        "note": "Stage 2 deleted the literal: the builder reads kvmem/chat.db::memory_source "
                "through ms.indexable_sources and no longer writes sources while building. "
                "An ok here means the text exists in exactly one place."}
    con.close()

    # ---------- 7. missing entry is explicit, not "" ----------
    c4 = sqlite3.connect(copy_db("missing"))
    missing = {"query": "no_such_source", "get_source": ms.get_source(c4, "no_such_source")}
    missing["probe_text"] = must_raise("probe_text(missing id)",
                                       lambda: ms.probe_text(c4, 999999), (KeyError,))
    missing["ok"] = (missing["get_source"] is None and missing["probe_text"]["ok"])
    res["missing_entry"] = missing
    c4.close()

    # ---------- 8. consumer coverage map (reported, nothing changed) ----------
    res["consumer_coverage"] = {
        "registry_api": "tools/memory_source.py",
        "readers_of_registry_text": [
            {"consumer": "tools/chat.py:113", "call": "ms.put_source(con, name, label, text)"},
            {"consumer": "tools/chat.py:122", "call": "ms.get_source(con, name)  # verify_hash default on"},
        ],
        "layers_not_yet_on_registry": [
            {"layer": "m4/m4_memory.db::memory_source",
             "cols": ["id", "name", "label", "text", "fanout"],
             "gap": "no source_hash, no registry id -- layer 2 is unverifiable (Stage 1b)"},
            {"layer": "m4/_m5db/m5_m4_blocks.db",
             "text_origin": "m4.memory_source.text (a literal expression, not (id, sha))",
             "gap": "Stage 1b rewrites text_origin as registry:name@sha16"},
        ],
        "note": "Stage 1a only tightens the registry API; every consumer line is unchanged.",
    }
    res["selfcheck_no_m5_literal_feeding"] = {
        "imports_m5": "m5_ground" in open(os.path.abspath(__file__), encoding="utf-8").read(),
        "note": "M5 is not imported and receives no text from this script",
    }
    res["db_sha16_after"] = sha_file16(DB)
    res["db_untouched"] = res["db_sha16_before"] == res["db_sha16_after"]
    # --- standing regressions (no writes to the live db) --------------------------
    kc = sqlite3.connect(DB)
    kinds = {r[0]: (r[1], r[2]) for r in kc.execute(
        "SELECT name, text_kind, contains_model_turns FROM memory_source ORDER BY id")}
    conv = [n for n, (k, _t) in kinds.items() if k == "conversation"]
    gate = {"conversation_names": conv}
    gate["conversation_rejected"] = bool(conv)
    gate["detail"] = []
    for n in conv:
        try:
            ms.assert_m5_source_allowed(kc, n)
            gate["conversation_rejected"] = False
            gate["detail"].append({"name": n, "raised": None})
        except ms.SourceNotAllowed as e:
            gate["detail"].append({"name": n, "raised": "SourceNotAllowed",
                                   "message": str(e)[:160]})
    kc.close()
    # I8: an undeclared insert must land on the refusal side (on a COPY, never the live db)
    import shutil, tempfile
    tmp = os.path.join(tempfile.gettempdir(), "i8_standing_probe.db")
    shutil.copyfile(DB, tmp)
    probe = {"text_kind": None, "contains_model_turns": None,
             "gate_raised": None, "ok": False}
    c2 = sqlite3.connect(tmp)
    try:
        txt = "探针：未声明类别的一行。"
        c2.execute("INSERT INTO memory_source (tenant,scope,mode,name,label,text,source_hash,"
                   "created_at) VALUES ('default','private','chat','i8_standing',?,?,?,?)",
                   ("probe", txt, ms.sha256_text(txt), "2026-10-25T00:00:00"))
        c2.commit()
        probe["text_kind"], probe["contains_model_turns"] = c2.execute(
            "SELECT text_kind, contains_model_turns FROM memory_source "
            "WHERE name='i8_standing'").fetchone()
        try:
            ms.assert_m5_source_allowed(c2, "i8_standing")
        except ms.SourceNotAllowed:
            probe["gate_raised"] = "SourceNotAllowed"
        probe["ok"] = (probe["text_kind"] == "conversation"
                       and probe["contains_model_turns"] == 1
                       and probe["gate_raised"] == "SourceNotAllowed")
    finally:
        c2.close()
        try:
            os.remove(tmp)
        except OSError:
            pass
    res["gate_regression"] = gate
    res["i8_undeclared_insert"] = probe

    res["acceptance"] = {
        "1_hashes_self_consistent": res["all_stored_hashes_self_consistent"],
        "2_tamper_raises": res["negative_test_tampered_copy"]["all_fail_closed"],
        "3_missing_is_explicit": res["missing_entry"]["ok"],
        "4_I1_unique": res["I1_uniqueness"]["one_row_per_text"],
        "5_idempotent": res["put_idempotent"]["ok"],
        "6_refuses_implicit_revision": res["put_refuses_implicit_revision"]["ok"],
        "7_refuses_empty": res["put_refuses_empty_text"]["ok"],
        "8_fidelity": res["no_second_copy_of_memory_text"]["ok"],
        "9_db_untouched": res["db_untouched"],
        "10_trigger_layer": res["trigger_layer_holds"]["ok"],
        # standing regression: a conversation row must never be admitted as an M5 source. This
        # is the assertion that caught the migrate-before-promote defect; it stays for good.
        "11_gate_rejects_conversation": res["gate_regression"]["conversation_rejected"],
        "12_undeclared_insert_fails_closed": res["i8_undeclared_insert"]["ok"],
        "13_no_second_copy_of_memory_text": res["no_second_copy_of_memory_text"]["ok"],
    }
    res["pass"] = all(res["acceptance"].values())
    json.dump(res, open(os.path.join(HERE, "run_registry_check.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)

    print("%-8s %-10s %-18s %-18s %s" % ("id", "name", "stored sha16", "computed sha16", "ok"))
    for r in res["rows"]:
        print("%-8s %-10s %-18s %-18s %s" % (r["id"], r["name"], r["stored_sha16"],
                                             r["computed_sha16"], r["match"]))
    print()
    print("  trigger layer: %s -> %s" % (res["trigger_layer_holds"]["raised"],
                                         (res["trigger_layer_holds"].get("message") or "")[:70]))
    for c in res["negative_test_tampered_copy"]["checks"]:
        print("  tamper -> %-42s %s" % (c["check"], c.get("raised") or c.get("problems")))
    print()
    for d in res["gate_regression"]["detail"]:
        print("  gate: %-20s -> %s" % (d["name"], d.get("raised")))
    pr = res["i8_undeclared_insert"]
    print("  i8 undeclared insert -> text_kind=%r turns=%r gate=%s"
          % (pr["text_kind"], pr["contains_model_turns"], pr["gate_raised"]))
    print(json.dumps(res["acceptance"], ensure_ascii=False, indent=1))
    print("PASS" if res["pass"] else "FAIL")


if __name__ == "__main__":
    main()
