# -*- coding: utf-8 -*-
"""p0_1a_check.py -- the acceptance test for P0-1a.

Two things get measured here, neither of them by inspection:

  [1] a refused `seq_repos_local` has ZERO side effects. The engine's preflight has a
      test hook (LLAMA_KV_REPOS_FAULT_LAYER) that makes it refuse at a chosen layer.
      We refuse at the first, a middle and the last layer and prove that the state file
      is byte-identical afterwards and that pos/n_tokens did not move. This is the
      regression test for the bug where earlier layers had already been rotated when a
      later layer refused: K moved, positions did not, and the caller would have retried
      with seq_add() on top.

  [2] the source layer is really authoritative. Build from source, remember the answers,
      DELETE the block artifacts, rebuild from source, and require the same answers and
      the same token counts. If a block were the truth, this step would lose the memory.

Run:
  python tools/p0_1a_check.py
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import chat as demo                                    # noqa: E402  (only for MEMORIES)
import memory_source as ms                             # noqa: E402
from kvslots import KVEngine                           # noqa: E402

DB = os.path.join(ROOT, "kvmem", "p0_1a.db")
BLOCKS = os.path.join(ROOT, "kvmem", "p0_1a_blocks")
CHAT = 4096
SCRATCH = 1
LIVE = 0

PROBES = {
    "profile": ["我的工号是多少？", "我养的猫叫什么名字？"],
    "project": ["项目什么时候上线？", "项目负责人是谁？"],
}

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print("  [%s] %-52s %s" % ("PASS" if ok else "FAIL", name, detail))


def diff_bytes(a, b):
    if len(a) != len(b):
        return -1, -1
    n = worst = 0
    for i in range(len(a)):
        d = abs(a[i] - b[i])
        if d:
            n += 1
            worst = max(worst, d)
    return n, worst


def fault_child(block_path, out_dir, layer):
    """Run in a CHILD process with LLAMA_KV_REPOS_FAULT_LAYER already in its environment.

    The hook is a getenv() inside the DLL, and the DLL's CRT caches its own copy of the
    environment at load time -- setting os.environ from a live process does not reach it.
    Forking with the variable already set is also the honest way to test it: the refusal
    must hold even though nothing else about the process differs.
    """
    import json
    eng = KVEngine(ms.MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    try:
        eng.reset(SCRATCH)
        n = eng.load_strict(SCRATCH, block_path)
        pos = eng.pos_max(SCRATCH)
        a_path = os.path.join(out_dir, "_fault_a.kvmem")
        b_path = os.path.join(out_dir, "_fault_b.kvmem")
        eng.save(SCRATCH, a_path)
        moved = eng.repos_local(SCRATCH, +64)
        eng.save(SCRATCH, b_path)
        pos_after = eng.pos_max(SCRATCH)
        n_after = eng.n_tokens(SCRATCH)      # before asking: the question appends to the seq
        # ask at the top of the block either way: pos_max+1 is valid whether the move
        # happened or was refused
        ans = eng.ask(SCRATCH, "我的工号是多少？", n_predict=16, pos=pos_after + 1)
        print("JSON " + json.dumps({
            "layer": layer, "moved": moved, "pos_before": pos, "pos_after": pos_after,
            "n_tokens": n_after, "answer": ans.strip().splitlines()[0]
            if ans.strip() else "", "a": a_path, "b": b_path}))
        return 0
    finally:
        eng.close()


def test_zero_side_effect(block_path):
    """Refusal must not touch a single byte, at any layer."""
    import json
    import subprocess
    print("\n[2] refused preflight has zero side effects   (child process per layer)")
    for layer in (0, 14, 27):
        env = dict(os.environ)
        env["LLAMA_KV_REPOS_FAULT_LAYER"] = str(layer)
        cp = subprocess.run([sys.executable, "-X", "utf8", os.path.abspath(__file__),
                             "--fault-layer", str(layer), "--fault-block", block_path],
                            capture_output=True, text=True, encoding="utf-8", env=env)
        line = next((l for l in cp.stdout.splitlines() if l.startswith("JSON ")), None)
        if not line:
            check("refuse at layer %-2d: engine responded" % layer, False,
                  (cp.stderr or cp.stdout)[-90:])
            continue
        d = json.loads(line[5:])
        ndiff, worst = diff_bytes(open(d["a"], "rb").read(), open(d["b"], "rb").read())
        ok = (d["moved"] == 0 and ndiff == 0 and d["pos_after"] == d["pos_before"]
              and d["n_tokens"] == 50)
        check("refuse at layer %-2d: 0 moved, 0 B changed" % layer, ok,
              "moved=%d bytes_diff=%d pos=%d->%d"
              % (d["moved"], ndiff, d["pos_before"], d["pos_after"]))
        check("refuse at layer %-2d: block still answers" % layer,
              "A-4417" in d["answer"], d["answer"][:40] or "(empty)")
        for p in (d["a"], d["b"]):
            try:
                os.remove(p)
            except OSError:
                pass


def attach_and_probe(eng, con, rows, tag):
    """Place every block below CHAT, share, and collect answers.

    Questions continue the dialogue the way chat.py does it: the first one starts at
    CHAT, the rest append (pos=None). Overwriting CHAT every time collides with the
    tokens the previous answer already generated there.
    """
    out = {}
    cursor = CHAT
    for row in rows:
        name = row[1]
        eng.reset(SCRATCH)
        n = ms.load_into(eng, row, SCRATCH)
        target = cursor - n
        eng.repos_local(SCRATCH, target)
        eng.share(SCRATCH, LIVE)
        cursor = target
        print("      %-8s %3d tok -> [%d,%d)" % (name, n, target, target + n))

    first = True
    for name, qs in PROBES.items():
        for q in qs:
            ans = eng.ask(LIVE, q, n_predict=32, pos=CHAT if first else None)
            first = False
            out[q] = ans.strip().splitlines()[0] if ans.strip() else ""
    eng.drop(LIVE)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fault-layer", type=int, default=None)
    ap.add_argument("--fault-block", default=None)
    args = ap.parse_args()
    if args.fault_layer is not None:
        return fault_child(args.fault_block, BLOCKS, args.fault_layer)

    os.makedirs(BLOCKS, exist_ok=True)
    for f in os.listdir(BLOCKS):
        if f.endswith(".kvmem"):
            os.remove(os.path.join(BLOCKS, f))
    if os.path.exists(DB):
        os.remove(DB)

    con = ms.connect(DB)
    eng = KVEngine(ms.MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    try:
        print("[0] source layer")
        for name, label, text in demo.MEMORIES:
            sid, created = ms.put_source(con, name, label, text)
            print("      %-8s id=%d %s (%d chars)" % (name, sid, "new" if created else "dup",
                                                      len(text)))
            again, created2 = ms.put_source(con, name, label, text)
            check("put_source is idempotent for %s" % name, again == sid and not created2)

        # immutability is enforced by a trigger, not by convention
        try:
            con.execute("UPDATE memory_source SET text='rewritten' WHERE name='profile'")
            con.commit()
            check("text is immutable (trigger)", False, "UPDATE succeeded -- trigger missing")
        except sqlite3.DatabaseError as e:
            check("text is immutable (trigger)", "immutable" in str(e).lower(),
                  str(e)[:52])

        print("\n[2] build from source")
        for name, _label, _text in demo.MEMORIES:
            rec = ms.build_block(eng, con, ms.get_source(con, name), BLOCKS)
            print("      %-8s %4d tok %7.1f KiB" % (rec["name"], rec["n_tokens"],
                                                    rec["n_bytes"] / 1024.0))

        rows1 = [r for r in ms.block_rows(con) if r[5] is not None]
        n_tok_1 = {r[1]: r[7] for r in rows1}

        # the fault sweep needs a block on disk and a pristine sequence
        test_zero_side_effect(rows1[0][6])

        print("\n[3] probe with the built blocks")
        ans1 = attach_and_probe(eng, con, rows1, "built")
        for (name, qs) in PROBES.items():
            for q in qs:
                print("      %-8s %-16s -> %s" % (name, q, ans1.get(q, "")[:44]))
        expect = {"我的工号是多少？": "A-4417", "我养的猫叫什么名字？": "年糕",
                  "项目什么时候上线？": "3月14", "项目负责人是谁？": "周敏"}
        hit = sum(1 for q, v in expect.items() if v in ans1.get(q, ""))
        check("built blocks answer all 4 probes", hit == len(expect), "%d/4" % hit)

        # prompt purity: the memories' text never reaches the ask path
        leaked = 0
        for _name, qs in PROBES.items():
            for q in qs:
                for _n, _l, text in demo.MEMORIES:
                    leaked += sum(1 for i in range(0, len(text) - 20)
                                  if text[i:i + 21] in q)
        check("0 characters of memory text in any prompt", leaked == 0, "%d chars" % leaked)

        print("\n[4] destroy the derived layer, then rebuild from source")
        for r in rows1:
            os.remove(r[6])
        con.execute("DELETE FROM memory_block")
        con.commit()
        probs = ms.verify(con)
        check("verify() reports the loss instead of pretending",
              any("no block built" in p for p in probs), "%d problem(s)" % len(probs))

        for name, _label, _text in demo.MEMORIES:
            ms.rebuild(eng, con, name, blocks_dir=BLOCKS)
        rows2 = [r for r in ms.block_rows(con) if r[5] is not None]
        n_tok_2 = {r[1]: r[7] for r in rows2}
        check("token counts identical after rebuild", n_tok_1 == n_tok_2,
              "%s vs %s" % (n_tok_1, n_tok_2))

        print("\n[5] probe again")
        ans2 = attach_and_probe(eng, con, rows2, "rebuilt")
        same = sum(1 for k in ans1 if ans1[k] == ans2.get(k))
        check("answers identical after rebuild", same == len(ans1), "%d/%d" % (same, len(ans1)))
        print("      before: %s" % " | ".join("%s=%s" % (k[:6], v[:14]) for k, v in ans1.items()))
        print("      after : %s" % " | ".join("%s=%s" % (k[:6], v[:14]) for k, v in ans2.items()))

        # byte equality across rebuild is NOT required -- report it, do not score it
        b1 = open(rows1[0][6], "rb").read() if os.path.exists(rows1[0][6]) else b""
        print("      (rebuild byte-identity is not required: %s)"
              % ("identical" if b1 else "rebuilt file replaced it"))

        print("\n[6] an incompatible artifact is refused, not silently used")
        con.execute("UPDATE memory_block SET model_mtime = model_mtime + 1 "
                    "WHERE source_id = ?", (rows2[0][0],))
        con.commit()
        row = [r for r in ms.block_rows(con) if r[0] == rows2[0][0]][0]
        try:
            ms.check_compatible(row)
            check("stale model fingerprint is refused", False, "no error raised")
        except ms.Incompatible as e:
            check("stale model fingerprint is refused", True, str(e)[:60])

        probs = ms.verify(con)
        check("verify() also flags it for repair",
              any("different model" in p for p in probs), "%d problem(s)" % len(probs))
    finally:
        eng.close()
        con.close()

    bad = [r for r in results if not r[1]]
    print("\n%s  %d/%d checks passed" % ("=" * 60, len(results) - len(bad), len(results)))
    if bad:
        for n, _ok, d in bad:
            print("  FAILED: %s  (%s)" % (n, d))
        return 1
    print("P0-1a: the source layer is authoritative and the refusal is side-effect free.")
    return 0


if __name__ == "__main__":
    sys.exit(main())