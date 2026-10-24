# -*- coding: utf-8 -*-
"""I8: rebuild memory_source so a forgotten declaration fails CLOSED.

The live table was created from an older DDL: text_kind defaulted to human_memory and
contains_model_turns to 0, and there was no CHECK. Defaults pointed at the permissive side,
so a row that forgot to declare what it is got ADMITTED as memory. SQLite cannot add a
CHECK in place, so the table is rebuilt from tools/memory_source.py::SCHEMA (one DDL source).

  python -u -X utf8 migrate_i8.py            # report only
  python -u -X utf8 migrate_i8.py --apply    # rebuild
  python -u -X utf8 migrate_i8.py --apply --tests    # + the three acceptance proofs
"""
import argparse, io, json, os, re, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import memory_source as ms                                        # noqa: E402

DB = os.path.join(ROOT, "kvmem", "chat.db")
COLS = ["id", "tenant", "scope", "mode", "name", "label", "text", "source_hash",
        "created_at", "text_kind", "contains_model_turns", "is_excerpt", "derived_from"]


def ddl():
    m = re.search(r"CREATE TABLE IF NOT EXISTS memory_source \(.*?\n\);", ms.SCHEMA, re.S)
    if not m:
        raise SystemExit("memory_source DDL not found in SCHEMA")
    return m.group(0)


NO_CHECK_DDL = """CREATE TABLE memory_source (
    id INTEGER PRIMARY KEY, tenant TEXT NOT NULL DEFAULT 'default',
    scope TEXT NOT NULL DEFAULT 'private', mode TEXT NOT NULL DEFAULT 'chat',
    name TEXT NOT NULL, label TEXT NOT NULL, text TEXT NOT NULL,
    source_hash TEXT NOT NULL, created_at TEXT NOT NULL,
    text_kind TEXT NOT NULL DEFAULT 'conversation',
    contains_model_turns INTEGER NOT NULL DEFAULT 1,
    is_excerpt INTEGER NOT NULL DEFAULT 0, derived_from TEXT)"""


def rows_of(con):
    return [tuple(r) for r in con.execute(
        "SELECT %s FROM memory_source ORDER BY id" % ",".join(COLS))]


def rebuild(con):
    new = ddl().replace("CREATE TABLE IF NOT EXISTS memory_source",
                        "CREATE TABLE memory_source_i8", 1)
    con.executescript(new)
    con.execute("INSERT INTO memory_source_i8 (%s) SELECT %s FROM memory_source"
                % (",".join(COLS), ",".join(COLS)))
    con.execute("DROP TABLE memory_source")
    con.execute("ALTER TABLE memory_source_i8 RENAME TO memory_source")
    con.executescript(ms.SCHEMA)          # index + immutability trigger
    con.commit()


def snapshot(con):
    d = {}
    for r in con.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name"):
        d["%s:%s" % (r[0], r[1])] = r[2]
    return d


def check_row_parity(before, after):
    bad = []
    if len(before) != len(after):
        bad.append("row count %d -> %d" % (len(before), len(after)))
    for a, b in zip(before, after):
        if a != b:
            bad.append("row %r changed" % (a[0],))
    return bad


def prove(con_copy, label):
    """The three machine-judgeable proofs; run on COPIES of the db."""
    out = {}
    # (i) legacy INSERT: old columns only, no declaration -> must land on the refusal side
    c = sqlite3.connect(con_copy)
    c.execute("INSERT INTO memory_source (tenant,scope,mode,name,label,text,source_hash,"
              "created_at) VALUES ('default','private','chat','i8_probe','probe',?,?,?)",
              ("这句是探针，不属于任何真实源。", ms.sha256_text("这句是探针，不属于任何真实源。"),
               "2026-10-25T00:00:00"))
    c.commit()
    got = c.execute("SELECT id, text_kind, contains_model_turns, is_excerpt, derived_from "
                    "FROM memory_source WHERE name='i8_probe'").fetchone()
    out["i_legacy_insert"] = {"row": got, "text_kind": got[1],
                              "contains_model_turns": got[2],
                              "ok": got[1] == "conversation" and got[2] == 1}
    try:
        ms.assert_m5_source_allowed(c, "i8_probe")
        out["i_gate"] = {"raised": None, "ok": False}
    except ms.SourceNotAllowed as e:
        out["i_gate"] = {"raised": "SourceNotAllowed", "message": str(e)[:180], "ok": True}
    # (ii) an explicit human_memory + 1 must be refused by the CHECK
    try:
        c.execute("INSERT INTO memory_source (tenant,scope,mode,name,label,text,source_hash,"
                  "created_at,text_kind,contains_model_turns) VALUES "
                  "('default','private','chat','i8_bad','bad',?,?,?,'human_memory',1)",
                  ("人类记忆不可能含模型回合。", ms.sha256_text("人类记忆不可能含模型回合。"),
                   "2026-10-25T00:00:00"))
        c.commit()
        out["ii_check"] = {"raised": None, "ok": False}
    except sqlite3.IntegrityError as e:
        out["ii_check"] = {"raised": "IntegrityError", "message": str(e)[:180], "ok": True}
    c.close()
    # (iii) bypass the CHECK entirely, then ask the gate: it must still refuse
    c = sqlite3.connect(con_copy)
    c.executescript("DROP TRIGGER IF EXISTS memory_source_text_is_immutable;"
                    "ALTER TABLE memory_source RENAME TO ms_no_check;"
                    + NO_CHECK_DDL + ";" +
                    "INSERT INTO memory_source SELECT * FROM ms_no_check;"
                    "DROP TABLE ms_no_check;")
    c.execute("UPDATE memory_source SET text_kind='human_memory', contains_model_turns=1 "
              "WHERE name='conv_2026-10-25'")
    c.commit()
    row = c.execute("SELECT text_kind, contains_model_turns FROM memory_source "
                    "WHERE name='conv_2026-10-25'").fetchone()
    try:
        ms.assert_m5_source_allowed(c, "conv_2026-10-25")
        out["iii_gate"] = {"row": row, "raised": None, "ok": False}
    except ms.SourceNotAllowed as e:
        out["iii_gate"] = {"row": row, "raised": "SourceNotAllowed",
                           "message": str(e)[:220], "ok": True}
    c.close()
    out["label"] = label
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tests", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "run_i8.json"))
    a = ap.parse_args()

    res = {"schema": "i8_migration_v1", "db": os.path.relpath(a.db, ROOT)}
    con = sqlite3.connect(a.db)
    before_rows = rows_of(con)
    res["rows_before"] = len(before_rows)
    res["ddl_has_check"] = "CHECK (NOT (text_kind = 'human_memory'" in ddl()
    res["ddl_defaults"] = {"text_kind": re.search(r"text_kind\s+TEXT\s+NOT NULL DEFAULT (\S+)",
                                                  ddl()).group(1),
                           "contains_model_turns": re.search(
                               r"contains_model_turns INTEGER NOT NULL DEFAULT (\d+)",
                               ddl()).group(1)}
    if a.apply:
        rebuild(con)
    after_rows = rows_of(con)
    res["rows_after"] = len(after_rows)
    res["row_parity"] = check_row_parity(before_rows, after_rows)
    sn = snapshot(con)
    res["trigger_present"] = "trigger:memory_source_text_is_immutable" in sn
    res["check_present"] = "CHECK (NOT (text_kind = 'human_memory'" in (
        sn.get("table:memory_source") or "")
    res["table_sql"] = (sn.get("table:memory_source") or "")[:900]
    con.close()

    if a.tests:
        import shutil, tempfile
        tmp = os.path.join(HERE, "_i8_test.db")
        shutil.copyfile(a.db, tmp)
        try:
            res["proofs"] = prove(tmp, "copies of the rebuilt db")
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    res["pass"] = (not res["row_parity"] and res["trigger_present"]
                   and res["check_present"]
                   and all(res.get("proofs", {}).get(k, {}).get("ok", True)
                           for k in ("i_legacy_insert", "i_gate", "ii_check", "iii_gate")))
    json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("rows %d -> %d | row_parity_problems=%s" % (res["rows_before"], res["rows_after"],
                                                      res["row_parity"] or "none"))
    print("defaults:", res["ddl_defaults"], "| CHECK:", res["check_present"],
          "| trigger:", res["trigger_present"])
    for k in ("i_legacy_insert", "i_gate", "ii_check", "iii_gate"):
        p = res.get("proofs", {}).get(k)
        if p:
            print("  %-18s ok=%s %s" % (k, p["ok"], (p.get("message") or p.get("row") or "")))
    print("PASS" if res["pass"] else "FAIL")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
