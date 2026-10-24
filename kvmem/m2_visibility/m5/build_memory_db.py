# -*- coding: utf-8 -*-
"""Build the authoritative text copy (memory.db) that M5 grounding checks against.

One row per block: block_id / cells / sha256 / model / source text / provenance.
The source text lives ONLY in this table -- it is never injected into a prompt.
Block sha256 is measured from the file on disk and cross-checked against the manifest.

  python -X utf8 kvmem/m2_visibility/m5/build_memory_db.py
"""
import hashlib, json, os, sqlite3, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P                              # noqa: E402

MANIFEST = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_m14b", "fixtures_14b.json")
CTRL_JSON = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_m14b", "control_texts_14b.json")
DB = os.path.join(HERE, "memory.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS blocks (
  block_id     TEXT PRIMARY KEY,
  family       TEXT NOT NULL,
  model        TEXT NOT NULL,
  cells        INTEGER NOT NULL,
  size_bytes   INTEGER NOT NULL,
  sha256       TEXT NOT NULL,
  sha256_disk  TEXT NOT NULL,
  sha_match    INTEGER NOT NULL,
  source_text  TEXT NOT NULL,
  source_path  TEXT NOT NULL,
  text_origin  TEXT NOT NULL,
  note         TEXT
);
CREATE TABLE IF NOT EXISTS control_texts (
  name        TEXT PRIMARY KEY,
  chars       INTEGER NOT NULL,
  sha256      TEXT NOT NULL,
  text        TEXT NOT NULL,
  note        TEXT
);
"""


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    man = json.load(open(MANIFEST, encoding="utf-8"))
    model = man["engine"]["model"]
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    rows = []
    for bid in ("home", "project", "habit"):
        b = man["blocks"]["m2"][bid]
        disk = sha_file(b["path"])
        text = P.FULL[bid]["text"]
        rows.append((bid, "m2", model, b["cells"], os.path.getsize(b["path"]),
                     b["sha256"], disk, int(disk == b["sha256"]), text,
                     b["path"].replace("\\", "/"), "m2_visibility_probe.FULL[%r][text]" % bid,
                     None))
    con.executemany("INSERT INTO blocks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    ctrl_rows = []
    if os.path.exists(CTRL_JSON):
        cache = json.load(open(CTRL_JSON, encoding="utf-8"))
        for name, val in cache.items():
            text = val if isinstance(val, str) else (val.get("text") or json.dumps(val))
            ctrl_rows.append((name, len(text),
                              hashlib.sha256(text.encode("utf-8")).hexdigest(), text,
                              "control text; NOT a memory block, never mountable"))
    con.executemany("INSERT INTO control_texts VALUES (?,?,?,?,?)", ctrl_rows)

    con.executemany("INSERT INTO meta VALUES (?,?)", [
        ("schema", "m5_memory_db_v1"),
        ("created_at", time.strftime("%Y-%m-%dT%H:%M:%S")),
        ("model", model),
        ("model_size", str(man["engine"]["model_size"])),
        ("manifest", MANIFEST.replace("\\", "/")),
        ("authority", "block files on disk are the authority; this table is their text copy"),
        ("red_line", "source_text is for verification only and is never put into a prompt"),
    ])
    con.commit()
    print("memory.db rows: blocks=%d control_texts=%d"
          % (con.execute("SELECT COUNT(*) FROM blocks").fetchone()[0],
             con.execute("SELECT COUNT(*) FROM control_texts").fetchone()[0]))
    for r in con.execute("SELECT block_id, cells, sha256, sha256_disk, sha_match, source_text "
                         "FROM blocks ORDER BY cells"):
        print("  %-8s cells=%-3d sha16=%s disk=%s match=%s text=%r"
              % (r[0], r[1], r[2][:16], r[3][:16], r[4], r[5]))
    con.close()
    return 0 if all(r[7] == 1 for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
