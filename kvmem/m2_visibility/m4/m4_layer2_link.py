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


def layer1(con):
    return {r[0]: {"id": r[0], "name": r[1], "label": r[2], "text": r[3],
                   "hash": r[4], "sha16": r[4][:16]}
            for r in con.execute(
                "SELECT id,name,label,text,source_hash FROM memory_source ORDER BY id")}


def layer2(con):
    return [{"id": r[0], "name": r[1], "label": r[2], "text": r[3],
             "registry_source_id": r[4], "source_hash": r[5]}
            for r in con.execute("SELECT id,name,label,text,registry_source_id,source_hash "
                                 "FROM memory_source ORDER BY id")]


def resolve_one(text, l1):
    """Exact match first, then substring containers. More than one => refuse to guess."""
    exact = [r for r in l1.values() if r["text"] == text]
    if len(exact) == 1:
        return exact[0], "exact"
    inside = [r for r in l1.values() if text in r["text"]]
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
            "sha16": r["sha16"]}


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
            out.append({"block_id": bid, "old": old, "new": None, "synthetic": True,
                        "text_sha16": sha16(stext),
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
    a = ap.parse_args()

    res = {"schema": "layer2_link_1b_v1", "apply": a.apply,
           "registry": os.path.relpath(a.registry, ROOT).replace("\\", "/"),
           "layer2": os.path.relpath(a.layer2, ROOT).replace("\\", "/")}
    con1 = sqlite3.connect(a.registry)
    con2 = sqlite3.connect(a.layer2)
    res["migrate"] = migrate(con2)
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
        l1 = layer1(con1)

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
    res["pass"] = (all(v["ok"] for v in checks.values())
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
