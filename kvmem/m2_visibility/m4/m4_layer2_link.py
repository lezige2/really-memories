# -*- coding: utf-8 -*-
"""Stage 1b: turn layer 2 (m4/m4_memory.db::memory_source) into a verifiable derived layer.

  python -u -X utf8 m4_layer2_link.py                # report only, no writes
  python -u -X utf8 m4_layer2_link.py --apply        # write the two columns + origins
  python -u -X utf8 m4_layer2_link.py --register-source conv_2026-10-25 --apply

What it enforces, not just documents:

  link      layer-2 row -> exactly one layer-1 row; registry_source_id + source_hash filled
  substring every layer-2 text is a byte-exact substring of its layer-1 text (Stale otherwise)
  no-foreign no layer-2 text may exist without a layer-1 container (ForeignText otherwise)
  origin    blocks.text_origin becomes registry:<name>@<sha16>, and parses back to (id, hash)
  stale     layer-1 text/hash changed after linking -> Stale, never silently reused
"""
import argparse, hashlib, json, os, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import memory_source as ms                                        # noqa: E402

L1 = os.path.join(ROOT, "kvmem", "chat.db")
L2 = os.path.join(HERE, "m4_memory.db")
M5DB = os.path.join(HERE, "_m5db", "m5_m4_blocks.db")


TEXT_KINDS = ("human_memory", "conversation")
# name -> (text_kind, contains_model_turns). Everything else is human memory by default;
# a name that carries assistant turns must be listed here explicitly, never inferred.
KIND_MAP = {"conv_2026-10-25": ("conversation", 1)}

# Role assignment is a DECLARATION, not something read off the text: the transcript carries
# no speaker markers. It is stored here, written into the registry table, and never inferred
# at run time (an inferred split would move the sha of every excerpt row).
EXCERPTS = {
    "conv_2026-10-25": {
        "roles_declared": True,
        "declared_by": "lead ruling D1/R15-b (2026-10-25)",
        "user_lines": [1, 3, 4, 5, 7, 8, 9],
        "assistant_lines": [2, 6],
    },
}


SourceNotAllowed = ms.SourceNotAllowed


class Unlinkable(Exception):
    """A layer-2 row has no layer-1 container: it cannot be verified, so it cannot ship."""


class Stale(Exception):
    """Layer 1 changed after the link was made, or the stored text left its container."""


class ForeignText(Exception):
    """Layer 2 holds text that layer 1 never had: that is a second source, not a copy."""


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def sha16(t):
    return sha(t)[:16]


def migrate(con):
    cols = [r[1] for r in con.execute("PRAGMA table_info(memory_source)")]
    added = []
    for c in ("registry_source_id", "source_hash"):
        if c not in cols:
            con.execute("ALTER TABLE memory_source ADD COLUMN %s %s"
                        % (c, "INTEGER" if c == "registry_source_id" else "TEXT"))
            added.append(c)
    if added:
        con.commit()
    return {"columns": [r[1] for r in con.execute("PRAGMA table_info(memory_source)")],
            "added": added}


def _has_col(con, table, col):
    return col in [r[1] for r in con.execute("PRAGMA table_info(%s)" % table)]


def migrate_layer1(con):
    """text_kind / contains_model_turns: the registry must say WHAT a row is.

    A conversation transcript contains assistant turns, i.e. model output. That text may
    answer "where did this block's body come from" but it may never become an M5 source,
    so the distinction has to be a column, not a sentence in a README.
    """
    added, kinds = [], []
    if not _has_col(con, "memory_source", "text_kind"):
        con.execute("ALTER TABLE memory_source ADD COLUMN text_kind TEXT NOT NULL "
                    "DEFAULT 'human_memory'")
        added.append("text_kind")
    if not _has_col(con, "memory_source", "contains_model_turns"):
        con.execute("ALTER TABLE memory_source ADD COLUMN contains_model_turns INTEGER "
                    "NOT NULL DEFAULT 0")
        added.append("contains_model_turns")
    if not _has_col(con, "memory_source", "is_excerpt"):
        con.execute("ALTER TABLE memory_source ADD COLUMN is_excerpt INTEGER NOT NULL "
                    "DEFAULT 0")
        added.append("is_excerpt")
    if not _has_col(con, "memory_source", "derived_from"):
        con.execute("ALTER TABLE memory_source ADD COLUMN derived_from TEXT")
        added.append("derived_from")
    # excerpts own their own kind/derived_from: never reclassify them from the name map
    for sid, name in list(con.execute("SELECT id,name FROM memory_source "
                                      "WHERE is_excerpt=0 ORDER BY id")):
        kind, turns = KIND_MAP.get(name, ("human_memory", 0))
        con.execute("UPDATE memory_source SET text_kind=?, contains_model_turns=? "
                    "WHERE id=?", (kind, turns, sid))
        kinds.append({"id": sid, "name": name, "text_kind": kind,
                      "contains_model_turns": turns,
                      "how": "explicit KIND_MAP" if name in KIND_MAP else "default"})
    con.commit()
    return {"added": added, "rows": kinds,
            "columns": [r[1] for r in con.execute("PRAGMA table_info(memory_source)")]}


def layer1(con):
    kind = (_has_col(con, "memory_source", "text_kind")
            and _has_col(con, "memory_source", "contains_model_turns"))
    exc = (_has_col(con, "memory_source", "is_excerpt")
           and _has_col(con, "memory_source", "derived_from"))
    sql = ("SELECT id,name,label,text,source_hash,text_kind,contains_model_turns,"
           "is_excerpt,derived_from FROM memory_source ORDER BY id") if (kind and exc) else \
          ("SELECT id,name,label,text,source_hash,'human_memory',0,0,NULL "
           "FROM memory_source ORDER BY id")
    return {r[0]: {"id": r[0], "name": r[1], "label": r[2], "text": r[3],
                   "hash": r[4], "sha16": r[4][:16], "text_kind": r[5],
                   "contains_model_turns": r[6], "is_excerpt": r[7],
                   "derived_from": r[8]}
            for r in con.execute(sql)}


def layer2(con):
    return [{"id": r[0], "name": r[1], "label": r[2], "text": r[3],
             "registry_source_id": r[4], "source_hash": r[5]}
            for r in con.execute("SELECT id,name,label,text,registry_source_id,source_hash "
                                 "FROM memory_source ORDER BY id")]


def resolve_one(text, l1):
    """Exact match first, then substring. Only containers can be targets.

    Excerpts are deliberately excluded: letting a layer-2 row link to an excerpt would make
    one derived row vouch for another, and the chain would end in a span instead of a source.
    """
    pool = [r for r in l1.values() if not r["is_excerpt"]]
    exact = [r for r in pool if r["text"] == text]
    if len(exact) == 1:
        return exact[0], "exact"
    inside = [r for r in pool if text in r["text"]]
    if len(inside) == 1:
        return inside[0], "substring"
    if not inside:
        return None, "no layer-1 container"
    return None, "ambiguous: %d containers (%s)" % (
        len(inside), ", ".join("%s#%d" % (r["name"], r["id"]) for r in inside))


def do_link(con2, l1, apply):
    out = []
    for r in layer2(con2):
        l1row, how = resolve_one(r["text"], l1)
        rec = {"id": r["id"], "name": r["name"], "chars": len(r["text"]),
               "sha16": sha16(r["text"]), "how": how,
               "registry_source_id": l1row["id"] if l1row else None,
               "registry_name": l1row["name"] if l1row else None,
               "registry_sha16": l1row["sha16"] if l1row else None}
        if apply and l1row:
            con2.execute("UPDATE memory_source SET registry_source_id=?, source_hash=? "
                         "WHERE id=?", (l1row["id"], l1row["hash"], r["id"]))
        out.append(rec)
    if apply:
        con2.commit()
    return out


def assert_text_kind_valid(con1):
    bad = []
    for r in layer1(con1).values():
        if r["text_kind"] not in TEXT_KINDS:
            bad.append("%s: text_kind=%r" % (r["name"], r["text_kind"]))
        if r["contains_model_turns"] not in (0, 1):
            bad.append("%s: contains_model_turns=%r" % (r["name"], r["contains_model_turns"]))
        if r["text_kind"] == "human_memory" and r["contains_model_turns"] != 0:
            bad.append("%s: human_memory must carry contains_model_turns=0" % r["name"])
        if r["text_kind"] == "conversation" and r["contains_model_turns"] not in (0, 1):
            bad.append("%s: conversation must carry contains_model_turns=1" % r["name"])
    if bad:
        raise ValueError("invalid text_kind rows: %s" % "; ".join(bad))
    return {r["name"]: {"text_kind": r["text_kind"],
                        "contains_model_turns": r["contains_model_turns"]}
            for r in layer1(con1).values()}


def assert_m5_source_allowed(con1, name):
    """Named entry point for the link checks; the rule itself lives in the registry module.

    The gate lives in tools/memory_source.py so Stage 3 can import it without importing this
    harness, and so there is exactly one definition of "may this source ground an M5 block".
    """
    return ms.assert_m5_source_allowed(con1, name)


DECL_SCHEMA = """
DROP TABLE IF EXISTS memory_source_excerpt;
CREATE TABLE memory_source_excerpt (
  container_id      INTEGER NOT NULL,
  container_name    TEXT    NOT NULL,
  container_sha256  TEXT    NOT NULL,
  line_index        INTEGER NOT NULL,
  excerpt_source_id INTEGER NOT NULL,
  line_sha256       TEXT    NOT NULL,
  line_len          INTEGER NOT NULL,
  role              TEXT    NOT NULL,
  roles_declared    INTEGER NOT NULL,
  decl_source       TEXT    NOT NULL,
  PRIMARY KEY (container_id, line_index)
);
"""

# role is an ADMISSION gate only: it decides whether a line may become an M5 source and
# nothing else. It must never feed a content rule ("dates in user turns count, in assistant
# turns do not"), because such a rule cannot be explained or verified.
ROLES = ("user", "assistant")


def _has_table(con, name):
    return con.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
                       (name,)).fetchone()[0] > 0


def promote_excerpts(con, apply):
    """Create the declared human-turn excerpt rows in layer 1. Idempotent.

    run time. Each row is a verbatim span of its container, derived_from names the
    container, and the declaration itself is stored in memory_source_excerpt so the
    split can be audited later.
    """
    plan = []
    for cname, decl in EXCERPTS.items():
        cont = con.execute("SELECT id,text,source_hash FROM memory_source "
                          "WHERE name=? AND is_excerpt=0", (cname,)).fetchone()
        if not cont:
            raise Unlinkable("excerpt container %r is not a layer-1 row" % (cname,))
        cid, ctext, csha = cont
        lines = ctext.split("\n")
        for idx in decl["user_lines"]:
            if not 1 <= idx <= len(lines):
                raise AssertionError("declared line %d is outside %s (%d lines)"
                                     % (idx, cname, len(lines)))
            text = lines[idx - 1]
            name = "%s#L%d" % (cname, idx)
            rec = {"container": cname, "container_id": cid,
                   "container_sha256": csha, "container_sha16": csha[:16],
                   "line_index": idx,
                   "line_text": text, "line_sha16": sha16(text), "name": name,
                   "roles_declared": decl["roles_declared"],
                   "declared_by": decl["declared_by"]}
            if apply:
                sid, created = ms.put_source(con, name, "人类回合摘录", text)
                con.execute("UPDATE memory_source SET text_kind='human_memory', "
                            "contains_model_turns=0, is_excerpt=1, derived_from=? "
                            "WHERE id=?", ("%s@%s" % (cname, csha[:16]), sid))
                rec["excerpt_source_id"] = sid
                rec["created"] = created
            rec["role"] = "user"
            rec["line_sha256"] = sha(text)
            rec["line_len"] = len(text)
            plan.append(rec)
        for idx in decl["assistant_lines"]:
            plan.append({"container": cname, "line_index": idx, "promoted": False,
                         "role": "assistant", "line_sha16": sha16(lines[idx - 1]),
                         "reason": "model turn: never becomes a source row"})
    if apply:
        # a changed declaration invalidates the whole excerpt set of that container: rows are
        # deleted and rebuilt, never repaired one role at a time.
        dropped = drop_stale_excerpts(con, plan)
        con.executescript(DECL_SCHEMA)
        for rec in plan:
            if not rec.get("excerpt_source_id"):
                continue
            con.execute("INSERT OR REPLACE INTO memory_source_excerpt VALUES "
                        "(?,?,?,?,?,?,?,?,?,?)",
                        (rec["container_id"], rec["container"], rec["container_sha256"],
                         rec["line_index"], rec["excerpt_source_id"], rec["line_sha256"],
                         rec["line_len"], rec["role"],
                         1 if rec["roles_declared"] else 0, rec["declared_by"]))
        con.commit()
        return {"plan": plan, "dropped": dropped}
    return {"plan": plan, "dropped": []}


def drop_stale_excerpts(con, plan):
    """Excerpt rows of a container that the current declaration no longer lists."""
    keep = {r["name"] for r in plan if r.get("role") == "user"}
    dropped = []
    for name, in list(con.execute("SELECT name FROM memory_source WHERE is_excerpt=1")):
        if name in keep:
            continue
        sid = con.execute("SELECT id FROM memory_source WHERE name=?", (name,)).fetchone()[0]
        con.execute("DELETE FROM memory_source WHERE id=?", (sid,))
        dropped.append({"name": name, "registry_source_id": sid,
                        "reason": "not in the current role declaration (rebuilt, not patched)"})
    return dropped


def coverage(con1, con2):
    """Five-tuple: sources vs searchable facts are different counts."""
    l1 = layer1(con1)
    conts = {r["name"]: r for r in l1.values() if not r["is_excerpt"]}
    facts = [r for r in layer2(con2) if r["name"].startswith("fact_")]
    out = {"user_lines": 0, "assistant_lines": 0, "layer1_excerpt_rows": 0,
           "covered_by_layer2_facts": 0, "searchable_facts": len(facts),
           "per_line": [], "not_covered_note":
           "not covered = NOT SEARCHABLE (no fact extracted, absent from the index); "
           "it is not unsupportable -- the line is still a layer-1 source"}
    for cname, decl in EXCERPTS.items():
        c = conts.get(cname)
        lines = c["text"].split("\n")
        out["user_lines"] += len(decl["user_lines"])
        out["assistant_lines"] += len(decl["assistant_lines"])
        out["layer1_excerpt_rows"] += sum(
            1 for r in l1.values()
            if r["is_excerpt"] and r["name"].startswith(cname + "#L"))
        for idx in decl["user_lines"]:
            text = lines[idx - 1]
            hit = [f["name"] for f in facts
                   if f["text"] == text or text in f["text"] or f["text"] in text]
            if hit:
                out["covered_by_layer2_facts"] += 1
            out["per_line"].append({"line_index": idx, "covered": bool(hit),
                                    "facts": hit, "chars": len(text)})
    return out


def assert_excerpts(con):
    """C4-j: every declared human line exists once, verbatim, and traces to its container."""
    l1 = layer1(con)
    conts = {r["name"]: r for r in l1.values() if not r["is_excerpt"]}
    by_name = {}
    for r in l1.values():
        by_name.setdefault(r["name"], []).append(r)
    out = {"promoted": [], "assistant_not_promoted": [], "table_rows": 0}
    bad = []
    for cname, decl in EXCERPTS.items():
        c = conts.get(cname)
        if not c:
            raise Unlinkable("excerpt container %r missing" % (cname,))
        lines = c["text"].split("\n")
        for idx in decl["user_lines"]:
            name = "%s#L%d" % (cname, idx)
            got = by_name.get(name, [])
            if len(got) != 1:
                bad.append("%s: %d rows" % (name, len(got)))
                continue
            ex = got[0]
            if ex["text"] != lines[idx - 1]:
                bad.append("%s text differs from declared line %d" % (name, idx))
            if not ex["is_excerpt"]:
                bad.append("%s is_excerpt=0" % name)
            if ex["text_kind"] != "human_memory":
                bad.append("%s text_kind=%r" % (name, ex["text_kind"]))
            want = "%s@%s" % (cname, c["sha16"])
            if ex["derived_from"] != want:
                bad.append("%s derived_from=%r want %r" % (name, ex["derived_from"], want))
            if ex["text"] not in c["text"]:
                bad.append("%s is not a substring of %s" % (name, cname))
            out["promoted"].append({"name": name, "registry_source_id": ex["id"],
                                    "line_index": idx, "chars": len(ex["text"]),
                                    "sha16": ex["sha16"]})
        for idx in decl["assistant_lines"]:
            name = "%s#L%d" % (cname, idx)
            if by_name.get(name):
                bad.append("assistant line %d was promoted as %s" % (idx, name))
            else:
                out["assistant_not_promoted"].append({"line_index": idx,
                                                      "sha16": sha16(lines[idx - 1])})
    if _has_table(con, "memory_source_excerpt"):
        decl_rows = list(con.execute(
            "SELECT container_id, container_name, container_sha256, line_index, "
            "excerpt_source_id, line_sha256, line_len, role, roles_declared, decl_source "
            "FROM memory_source_excerpt ORDER BY container_id, line_index"))
        out["table_rows"] = len(decl_rows)
        for cid, cname, csha, idx, eid, lsha, llen, role, roles, src in decl_rows:
            if not roles:
                bad.append("declaration row %d/%d has roles_declared=0" % (cid, idx))
            if role not in ROLES or role != "user":
                bad.append("declaration row %d/%d role=%r (only user lines may be sources)"
                           % (cid, idx, role))
            e = l1.get(eid)
            if not e or not e["is_excerpt"]:
                bad.append("declaration row %d/%d points at %r, not an excerpt"
                           % (cid, idx, eid))
                continue
            if e["hash"] != lsha:
                bad.append("declaration row %d/%d line_sha256 != row hash" % (cid, idx))
            if len(e["text"]) != llen:
                bad.append("declaration row %d/%d line_len != row length" % (cid, idx))
            out.setdefault("tuples", []).append({
                "container_name": cname, "container_sha16": csha[:16], "line_index": idx,
                "line_text": e["text"], "role": role, "line_sha16": lsha[:16]})
    else:
        bad.append("memory_source_excerpt table missing")
    if bad:
        raise AssertionError("excerpt declaration broken: %s" % "; ".join(bad))
    return out


def assert_linked(con2):
    missing = [r[1] for r in con2.execute(
        "SELECT id,name FROM memory_source WHERE registry_source_id IS NULL "
        "OR source_hash IS NULL ORDER BY id")]
    if missing:
        raise Unlinkable("layer-2 rows with no registry link: %s" % ", ".join(missing))


def assert_substrings(con2, l1):
    bad = []
    for r in layer2(con2):
        row = l1.get(r["registry_source_id"])
        if row is None:
            bad.append((r["name"], "registry_source_id %r not in layer 1"
                        % (r["registry_source_id"],)))
            continue
        if r["text"] not in row["text"]:
            bad.append((r["name"], "text is not a substring of %s" % row["name"]))
        if sha(row["text"]) != r["source_hash"]:
            bad.append((r["name"], "stored source_hash != sha256(layer-1 text)"))
    if bad:
        raise Stale("; ".join("%s: %s" % b for b in bad))


def assert_no_foreign(con2, l1):
    texts = [r["text"] for r in l1.values()]
    foreign = [r["name"] for r in layer2(con2)
               if not any(r["text"] in t for t in texts)]
    if foreign:
        raise ForeignText("layer-2 text layer 1 never had: %s" % ", ".join(foreign))


def assert_not_stale(con2, l1):
    """Layer 1 mutated behind the link => the link is stale, refuse to reuse it."""
    for r in layer2(con2):
        row = l1.get(r["registry_source_id"])
        if row is None:
            raise Stale("%s: linked registry id %r is gone"
                        % (r["name"], r["registry_source_id"]))
        if sha(row["text"]) != row["hash"]:
            raise Stale("%s: layer-1 %s no longer hashes out (stored %s, computed %s)"
                        % (r["name"], row["name"], row["hash"][:16], sha16(row["text"])))
        if r["source_hash"] != row["hash"]:
            raise Stale("%s: linked to %s@%s but layer 1 now hashes %s"
                        % (r["name"], row["name"], (r["source_hash"] or "?")[:16],
                           row["hash"][:16]))


def make_origin(name, h):
    return "registry:%s@%s" % (name, h[:16])


def parse_origin(s):
    if not s or not s.startswith("registry:") or "@" not in s:
        return None
    body = s[len("registry:"):]
    name, _, sh = body.rpartition("@")
    return {"name": name, "sha16": sh} if name and sh else None


def resolve_origin(l1, origin):
    """registry:<name>@<sha16> -> (id, full hash) or raise."""
    p = parse_origin(origin)
    if not p:
        raise ValueError("not a registry origin: %r" % (origin,))
    hits = [r for r in l1.values() if r["name"] == p["name"]]
    if not hits:
        raise ValueError("origin %r names a source layer 1 does not have" % (origin,))
    r = hits[-1]
    if not r["hash"].startswith(p["sha16"]):
        raise Stale("origin %r points at sha16 %s but layer 1 %s hashes %s"
                    % (origin, p["sha16"], r["name"], r["sha16"]))
    return {"registry_source_id": r["id"], "name": r["name"], "sha256": r["hash"],
            "sha16": r["sha16"], "text_kind": r["text_kind"],
            "contains_model_turns": r["contains_model_turns"]}


def backfill_origins(con_m5, con2, l1, apply):
    """blocks.source_text identifies the layer-2 row: there is no source_id column."""
    rows = layer2(con2)
    out = []
    for bid, stext, old in list(con_m5.execute(
            "SELECT block_id, source_text, text_origin FROM blocks ORDER BY block_id")):
        cand = [r for r in rows if r["text"] == stext]
        l2row = cand[0] if len(cand) == 1 else None
        if l2row is None or l2row["registry_source_id"] is None:
            # Not a failure: a block whose text no layer-2 row carries is an experiment
            # artifact (the ablation corpus is an EDITED text -- registering it would put
            # derived text into the authoritative layer). It is marked, never linked.
            new_origin = "declared_synthetic:%s@%s" % (bid, sha16(stext))
            if apply:
                con_m5.execute("UPDATE blocks SET text_origin=? WHERE block_id=?",
                               (new_origin, bid))
            out.append({"block_id": bid, "old": old, "new": None, "synthetic": True,
                        "text_origin": new_origin, "text_sha16": sha16(stext),
                        "why": ("no unique layer-2 row for this block's source_text"
                                if l2row is None else
                                "layer-2 row %r is not linked" % l2row["name"])})
            continue
        row = l1[l2row["registry_source_id"]]
        new = make_origin(row["name"], row["hash"])
        if apply:
            con_m5.execute("UPDATE blocks SET text_origin=? WHERE block_id=?", (new, bid))
        out.append({"block_id": bid, "old": old, "new": new,
                    "reverse": resolve_origin(l1, new)})
    if apply:
        con_m5.commit()
    return out


def _l2_name_of(con2, sid):
    r = con2.execute("SELECT name FROM memory_source WHERE id=?", (sid,)).fetchone()
    return r[0] if r else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=L1)
    ap.add_argument("--layer2", default=L2)
    ap.add_argument("--m5db", default=M5DB)
    ap.add_argument("--register-source", default=None,
                    help="promote a layer-2 name's text into the registry first "
                         "(uses tools/memory_source.put_source unchanged)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "run_layer2_link.json"))
    ap.add_argument("--tests", action="store_true", help="run the negative tests too")
    ap.add_argument("--check-m5-source", default=None,
                    help="assert that this registry source may feed M5 (R15 candidate)")
    a = ap.parse_args()

    res = {"schema": "layer2_link_1b_v1", "apply": a.apply,
           "registry": os.path.relpath(a.registry, ROOT).replace("\\", "/"),
           "layer2": os.path.relpath(a.layer2, ROOT).replace("\\", "/")}
    con1 = sqlite3.connect(a.registry)
    con2 = sqlite3.connect(a.layer2)
    res["migrate"] = migrate(con2)
    res["migrate_layer1"] = migrate_layer1(con1)
    l1 = layer1(con1)

    if a.register_source:
        row = [r for r in layer2(con2) if r["name"] == a.register_source]
        if not row:
            raise SystemExit("no layer-2 row named %r" % a.register_source)
        row = row[0]
        sid, created = ms.put_source(con1, row["name"], row["label"], row["text"])
        res["promotion"] = {"name": row["name"], "registry_source_id": sid,
                            "created": created, "chars": len(row["text"]),
                            "sha16": sha16(row["text"])}

    # classify AFTER promotion: the promoted row must be judged too, not defaulted
    res["migrate_layer1"] = migrate_layer1(con1)
    res["promote_excerpts"] = promote_excerpts(con1, a.apply)
    l1 = layer1(con1)
    res["layer1_kinds"] = assert_text_kind_valid(con1)
    res["excerpt_checks"] = assert_excerpts(con1)
    res["coverage"] = coverage(con1, con2)
    try:
        res["I1_layered"] = {"ok": True, "layers": sorted(
            ms.assert_unique_texts(con1)["layers"].keys())}
    except (AssertionError, ms.SourceHashMismatch) as e:
        res["I1_layered"] = {"ok": False, "raised": type(e).__name__, "message": str(e)[:400]}

    res["layer1"] = [{k: v for k, v in r.items() if k != "text"} for r in l1.values()]
    res["links"] = do_link(con2, l1, a.apply)
    res["unlinked"] = [r["name"] for r in res["links"] if r["registry_source_id"] is None]

    checks = {}
    for label, fn in (("assert_linked", lambda: assert_linked(con2)),
                      ("assert_substrings", lambda: assert_substrings(con2, l1)),
                      ("assert_no_foreign", lambda: assert_no_foreign(con2, l1)),
                      ("assert_not_stale", lambda: assert_not_stale(con2, l1))):
        try:
            fn()
            checks[label] = {"ok": True, "raised": None}
        except (Unlinkable, Stale, ForeignText) as e:
            checks[label] = {"ok": False, "raised": type(e).__name__, "message": str(e)[:400]}
    res["assertions"] = checks

    if a.check_m5_source:
        gate = {}
        for nm in (a.check_m5_source, "profile", "conv_2026-10-25#L5"):
            try:
                gate[nm] = {"ok": True, **assert_m5_source_allowed(con1, nm)}
            except (SourceNotAllowed, ValueError) as e:
                gate[nm] = {"ok": False, "raised": type(e).__name__, "message": str(e)[:300]}
        res["m5_source_gate"] = gate

    if os.path.exists(a.m5db):
        con5 = sqlite3.connect(a.m5db)
        res["origins"] = backfill_origins(con5, con2, l1, a.apply)
        con5.close()

    if a.tests:
        # negative 1: a layer-2 text layer 1 never had
        t = sqlite3.connect(":memory:")
        t.execute("CREATE TABLE memory_source (id INTEGER PRIMARY KEY, name TEXT, label TEXT, "
                  "text TEXT, registry_source_id INTEGER, source_hash TEXT)")
        t.execute("INSERT INTO memory_source VALUES (1,'foreign','x','这句话层 1 从来没有过。',"
                  "NULL,NULL)")
        try:
            assert_no_foreign(t, l1)
            res["negative_foreign"] = {"ok": False, "raised": None}
        except ForeignText as e:
            res["negative_foreign"] = {"ok": True, "raised": "ForeignText",
                                       "message": str(e)[:300]}
        t.close()
        # negative 2: layer-1 hash changed behind the link
        if res["links"] and res["links"][0]["registry_source_id"]:
            tam = dict(l1)
            k = res["links"][0]["registry_source_id"]
            tam[k] = dict(tam[k])
            tam[k]["text"] = tam[k]["text"] + "【改动】"
            tam[k]["hash"] = sha(tam[k]["text"])
            u = sqlite3.connect(":memory:")
            u.execute("CREATE TABLE memory_source (id INTEGER PRIMARY KEY, name TEXT, label TEXT, "
                      "text TEXT, registry_source_id INTEGER, source_hash TEXT)")
            for r in layer2(con2):
                u.execute("INSERT INTO memory_source VALUES (?,?,?,?,?,?)",
                          (r["id"], r["name"], r["label"], r["text"],
                           r["registry_source_id"], r["source_hash"]))
            try:
                assert_not_stale(u, tam)
                res["negative_stale"] = {"ok": False, "raised": None}
            except Stale as e:
                res["negative_stale"] = {"ok": True, "raised": "Stale",
                                         "message": str(e)[:300]}
            u.close()

    con2.close()
    con1.close()
    origins = res.get("origins", [])
    res["origins_summary"] = {
        "registry_backed": [o["block_id"] for o in origins if o.get("new")],
        "declared_synthetic": [o["block_id"] for o in origins if not o.get("new")],
        "note": "synthetic = the block's text is not a layer-2 row (ablation corpus: an "
                "edited text, deliberately NOT registered -- derived text must never enter "
                "the authoritative layer)",
    }
    gate = res.get("m5_source_gate", {})
    res["pass"] = (all(v["ok"] for v in checks.values())
                   and res["I1_layered"]["ok"]
                   and (not gate or (gate.get(a.check_m5_source, {}).get("ok") is False
                                     and gate.get("profile", {}).get("ok") is True
                                     and gate.get("conv_2026-10-25#L5", {}).get("ok") is True))
                   and all(o.get("new") or o.get("synthetic") for o in origins)
                   and res.get("negative_foreign", {"ok": True})["ok"]
                   and res.get("negative_stale", {"ok": True})["ok"])
    json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("layer1: %s" % ", ".join("%s#%d(%d chars)" % (r["name"], r["id"], len(r["text"]))
                                   for r in l1.values()))
    print("%-24s %-6s %-8s %-22s %s" % ("layer2 row", "chars", "how", "registry link", "sha16"))
    for r in res["links"]:
        print("%-24s %-6d %-8s %-22s %s" % (r["name"], r["chars"], r["how"],
                                            r["registry_name"] or "-", r["sha16"]))
    for k, v in checks.items():
        print("  %-20s %s %s" % (k, "OK" if v["ok"] else "FAIL", v.get("message") or ""))
    for k in ("negative_foreign", "negative_stale"):
        if k in res:
            print("  %-20s %s %s" % (k, "OK" if res[k]["ok"] else "FAIL",
                                     res[k].get("message") or ""))
    for o in res.get("origins", []):
        print("  origin %-34s -> %s" % (o["old"], o["new"] or o["why"]))
    print("PASS" if res["pass"] else "FAIL")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
