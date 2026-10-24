# -*- coding: utf-8 -*-
"""p0_1b_check.py -- the derived layer, while it is damaged.

An index that only ever says "fine" is not an instrument. This test fabricates the three
states and requires the tool to tell them apart:

  managed  rebuildable          -- source + block, consistent
  legacy   READ ONLY            -- a block from before the source layer existed. Its text
                                   is gone, so it can never be rebuilt. It must be marked,
                                   not silently mixed in with managed blocks.
  orphan   FAIL CLOSED          -- the index still lists it, the file is gone. Attaching
                                   it would load an empty sequence and hallucinate.

Run:  python tools/p0_1b_check.py
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import chat as demo                                    # noqa: E402
import memory_source as ms                             # noqa: E402
from kvslots import KVEngine                           # noqa: E402

DB = os.path.join(ROOT, "kvmem", "p0_1b.db")
BLOCKS = os.path.join(ROOT, "kvmem", "p0_1b_blocks")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print("  [%s] %-52s %s" % ("PASS" if ok else "FAIL", name, detail))


def main():
    os.makedirs(BLOCKS, exist_ok=True)
    shutil.rmtree(BLOCKS, ignore_errors=True)
    os.makedirs(BLOCKS, exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)

    con = ms.connect(DB)
    eng = KVEngine(ms.MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    try:
        print("[0] one managed block")
        name, label, text = demo.MEMORIES[0]
        ms.put_source(con, name, label, text)
        ms.build_block(eng, con, ms.get_source(con, name), BLOCKS)
        c = ms.classify(con, BLOCKS)
        check("managed", c["managed"] == [name], "%s" % c["managed"])
        check("no legacy, no orphan", not c["legacy"] and not c["orphan"], "clean")

        print("\n[1] legacy: a block whose source text is gone")
        # exactly what an install looks like after upgrading from the pre-source-layer
        # demo: the file exists, the old index row exists, no source row exists.
        legacy_path = os.path.join(BLOCKS, "oldchat.kvmem")
        shutil.copy(os.path.join(BLOCKS, name + ".kvmem"), legacy_path)
        con.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, name TEXT, "
                    "label TEXT, path TEXT, n_tokens INTEGER, n_bytes INTEGER, "
                    "created_at TEXT)")
        con.execute("INSERT INTO memories (name,label,path,n_tokens,n_bytes,created_at) "
                    "VALUES (?,?,?,?,?,?)",
                    ("oldchat", "旧档案", legacy_path, 50, os.path.getsize(legacy_path), "-"))
        con.commit()
        c = ms.classify(con, BLOCKS)
        check("legacy is detected", any("oldchat" in s for s in c["legacy"]),
              "%s" % c["legacy"])
        check("legacy is NOT mixed into managed", "oldchat" not in c["managed"],
              "%s" % c["managed"])
        check("legacy is marked read-only / unrebuildable",
              any("read only" in s for s in c["legacy"]), "reason recorded")
        # read-only means: attaching is allowed, rebuilding must be impossible
        check("legacy cannot be rebuilt (no source row)",
              ms.get_source(con, "oldchat") is None, "no source row")

        print("\n[2] orphan: the index lists it, the file is gone")
        os.remove(os.path.join(BLOCKS, name + ".kvmem"))
        c = ms.classify(con, BLOCKS)
        check("orphan is detected", any(name in s for s in c["orphan"]), "%s" % c["orphan"])
        check("orphan is not managed", name not in c["managed"], "%s" % c["managed"])
        row = [r for r in ms.block_rows(con) if r[1] == name][0]
        try:
            ms.check_compatible(row)
            check("orphan fails closed on attach", False, "no error raised")
        except ms.Incompatible as e:
            check("orphan fails closed on attach", "missing" in str(e), str(e)[:54])
        probs = ms.verify(con, BLOCKS)
        check("verify() lists the orphan for repair",
              any("missing" in p for p in probs), "%d problem(s)" % len(probs))

        print("\n[3] the orphan is repairable from its source")
        ms.rebuild(eng, con, name, blocks_dir=BLOCKS)
        c = ms.classify(con, BLOCKS)
        check("rebuilt block is managed again", name in c["managed"], "%s" % c["managed"])
        check("orphan list is empty", not c["orphan"], "%s" % c["orphan"])
        check("legacy is still marked legacy",
              any("oldchat" in s for s in c["legacy"]), "%s" % c["legacy"])

        print("\n[4] an unbuilt source is not a broken block")
        ms.put_source(con, "later", "待建", "这是一条还没编码的记忆。")
        c = ms.classify(con, BLOCKS)
        check("unbuilt is its own state", "later" in c["unbuilt"], "%s" % c["unbuilt"])
        check("unbuilt is not orphan or legacy",
              "later" not in c["orphan"] and not any("later" in s for s in c["legacy"]),
              "separate bucket")
    finally:
        eng.close()
        con.close()

    bad = [r for r in results if not r[1]]
    print("\n%s  %d/%d checks passed" % ("=" * 60, len(results) - len(bad), len(results)))
    for n, _ok, d in bad:
        print("  FAILED: %s  (%s)" % (n, d))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())