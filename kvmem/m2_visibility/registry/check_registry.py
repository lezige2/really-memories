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


def chat_memories():
    """chat.py's current constants, read as source (no import, no side effects)."""
    tree = ast.parse(open(CHAT_PY, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "MEMORIES" for t in node.targets):
            return [(n, lbl, txt) for n, lbl, txt in ast.literal_eval(node.value)]
    raise SystemExit("MEMORIES not found in %s" % CHAT_PY)


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
    uniq = ms.assert_unique_texts(con)
    dup_texts = [k for k, v in uniq.items() if len(v) > 1]
    res["I1_uniqueness"] = {
        "distinct_texts": len(uniq),
        "row_count": len(rows),
        "one_row_per_text": len(uniq) == len(rows) and not dup_texts,
        "duplicates": dup_texts,
        "texts_by_sha16": {k[:16]: v for k, v in uniq.items()},
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

    # ---------- 6. fidelity: registry vs chat.py constants ----------
    mem = chat_memories()
    by_name = {r[1]: r for r in rows}
    fid = []
    for nm, lbl, txt in mem:
        rr = by_name.get(nm)
        fid.append({"name": nm, "label_ok": bool(rr) and rr[2] == lbl,
                    "chars_const": len(txt), "chars_db": len(rr[3]) if rr else None,
                    "sha16_const": sha16(txt),
                    "sha16_db_stored": rr[4][:16] if rr else None,
                    "sha16_db_computed": sha16(rr[3]) if rr else None,
                    "byte_identical": bool(rr) and rr[3] == txt})
    res["fidelity_vs_chat_py_constants"] = {
        "how": "ast.literal_eval on tools/chat.py (no import, no execution)",
        "rows": fid, "ok": len(fid) == len(rows) and all(f["byte_identical"] for f in fid)}
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
    res["acceptance"] = {
        "1_hashes_self_consistent": res["all_stored_hashes_self_consistent"],
        "2_tamper_raises": res["negative_test_tampered_copy"]["all_fail_closed"],
        "3_missing_is_explicit": res["missing_entry"]["ok"],
        "4_I1_unique": res["I1_uniqueness"]["one_row_per_text"],
        "5_idempotent": res["put_idempotent"]["ok"],
        "6_refuses_implicit_revision": res["put_refuses_implicit_revision"]["ok"],
        "7_refuses_empty": res["put_refuses_empty_text"]["ok"],
        "8_fidelity": res["fidelity_vs_chat_py_constants"]["ok"],
        "9_db_untouched": res["db_untouched"],
    }
    res["pass"] = all(res["acceptance"].values())
    json.dump(res, open(os.path.join(HERE, "run_registry_check.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)

    print("%-8s %-10s %-18s %-18s %s" % ("id", "name", "stored sha16", "computed sha16", "ok"))
    for r in res["rows"]:
        print("%-8s %-10s %-18s %-18s %s" % (r["id"], r["name"], r["stored_sha16"],
                                             r["computed_sha16"], r["match"]))
    print()
    for c in res["negative_test_tampered_copy"]["checks"]:
        print("  tamper -> %-42s %s" % (c["check"], c.get("raised") or c.get("problems")))
    print()
    print(json.dumps(res["acceptance"], ensure_ascii=False, indent=1))
    print("PASS" if res["pass"] else "FAIL")


if __name__ == "__main__":
    main()
