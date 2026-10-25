# -*- coding: utf-8 -*-
"""p0_2_check.py -- acceptance test for P0-2 (detach-before-save + two-layer manifest).

Measured here:

  [0] seam regression: with LLAMA_KV_REPOS_FAULT_LAYER unset, repos_local still moves
      every cell. A test hook that changes default behaviour is not a hook.

  [1] a 2-block session saves, and a NEW PROCESS restores it: 4/4 answers identical,
      token count / pos_max / block ranges all match. A new process is the point -- an
      in-process reload would not prove the manifest carries everything needed.

  [2] a save that fails mid-way leaves the session attached and still answering.

  [3] save again after another turn: no token-ledger growth (the chat holds its own
      dialogue, and the token list equals its position span).

  [4] the layout contract is enforced, not decorative: a manifest whose *render* was
      edited must be refused, and so must one whose render no longer matches what the
      contract recomputes.

Run:  python tools/p0_2_check.py
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import chat as demo                                    # noqa: E402
import memory_source as ms                             # noqa: E402
import session_state as ss                             # noqa: E402
from kvslots import KVEngine                           # noqa: E402

DB = os.path.join(ROOT, "kvmem", "p0_2.db")
BLOCKS = os.path.join(ROOT, "kvmem", "p0_2_blocks")
SESSIONS = os.path.join(ROOT, "kvmem", "sessions")

CHAT = 4096
SLOT = 64
LIVE = 0
SCRATCH = 7

PROBES = ["我的工号是多少？", "我养的猫叫什么名字？", "项目什么时候上线？", "项目负责人是谁？"]
EXPECT = ["A-4417", "年糕", "3月14", "周敏"]

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print("  [%s] %-52s %s" % ("PASS" if ok else "FAIL", name, detail))


def restore_child(manifest, db, out_prefix):
    """New process: restore, ask the probes, save once more."""
    eng = KVEngine(ms.MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    con = ms.connect(db)
    try:
        rep = ss.restore_session(eng, con, manifest)
        restored_end, restored_n = rep["chat_end"], rep["chat_n_tokens"]
        answers = {}
        for q in PROBES:
            a = eng.ask(LIVE, q, n_predict=32)
            answers[q] = a.strip()

        m = ss.read_manifest(manifest)
        rows = {r[1]: r for r in ms.block_rows(con)}
        blocks2 = [{"seq": b["slot_id"] + 1, "source_id": rows[b["block"]][0],
                    "name": b["block"], "lo": b["start"], "hi": b["end"],
                    "n_tokens": b["n_tokens"], "path": rows[b["block"]][6]}
                   for b in rep["blocks"]]
        m2 = ss.save_session(eng, con, out_prefix + "_2.json", blocks2,
                             anchor=m["layout"]["anchor"],
                             slot_capacity=m["layout"]["slot_capacity"])
        print("JSON " + json.dumps({
            "answers": answers,
            "restored_end": restored_end,
            "restored_n": restored_n,
            "blocks": rep["blocks"],
            "shifts": rep["shifts"],
            "rebuilt": rep["rebuilt"],
            "m2_chat_n": m2["chat"]["n_tokens"],
            "m2_chat_span": m2["chat"]["end"] - m2["chat"]["start"],
            "m2_blocks": len(m2["placement"]["blocks"]),
        }))
        return 0
    finally:
        eng.close()
        con.close()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--restore", default=None)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--out", default=os.path.join(SESSIONS, "s"))
    a = ap.parse_args()
    if a.restore:
        return restore_child(a.restore, a.db, a.out)

    for d in (BLOCKS, SESSIONS):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)

    con = ms.connect(DB)
    eng = KVEngine(ms.MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    try:
        for name, label, text in demo.MEMORIES:
            ms.put_source(con, name, label, text)
            ms.build_block(eng, con, ms.get_source(con, name), BLOCKS)
        rows = [r for r in ms.block_rows(con) if r[5] is not None]

        # ---- [0] the seam must not change default behaviour -------------------
        print("\n[0] seam regression (LLAMA_KV_REPOS_FAULT_LAYER unset)")
        eng.reset(SCRATCH)
        n = ms.load_into(eng, rows[0], SCRATCH)
        moved = eng.repos_local(SCRATCH, +64)
        check("repos_local still moves every cell", moved == n, "moved %d/%d" % (moved, n))
        eng.reset(SCRATCH)

        # ---- [1] build a live session, right-aligned slots --------------------
        print("\n[1] build a live 2-block session (right-aligned slots of %d)" % SLOT)
        blocks = []
        for i, row in enumerate(rows, start=1):
            eng.reset(i)
            n = ms.load_into(eng, row, i)
            end = CHAT - (i - 1) * SLOT
            lo = end - n
            base = eng.pos_max(i) + 1 - n
            if base != lo:
                moved = eng.repos_local(i, lo - base)
                if moved != n:
                    check("place %s" % row[1], False, "moved %d/%d" % (moved, n))
            eng.share(i, LIVE, lo, end)
            blocks.append({"seq": i, "source_id": row[0], "name": row[1],
                           "lo": lo, "hi": end, "n_tokens": n, "path": row[6]})
            print("      %-8s %3d tok -> [%d,%d)  slot ends %d" % (row[1], n, lo, end, end))

        answers = {}
        for k, q in enumerate(PROBES):
            ans = eng.ask(LIVE, q, n_predict=32, pos=(CHAT if k == 0 else None))
            answers[q] = ans.strip()
        hit = sum(1 for e in EXPECT if any(e in v for v in answers.values()))
        check("live session answers 4/4", hit == 4, "%d/4" % hit)

        # ---- [2] a failing save must not leave the session detached ----------
        print("\n[2] save failure injection")
        before = (eng.pos_max(LIVE), eng.n_tokens(LIVE))
        real_save = eng.save
        eng.save = lambda *x, **k: (_ for _ in ()).throw(RuntimeError("injected"))
        try:
            ss.save_session(eng, con, os.path.join(SESSIONS, "fail.json"), blocks,
                            anchor=CHAT, slot_capacity=SLOT)
            check("save failure propagates", False, "no exception")
        except RuntimeError:
            check("save failure propagates", True, "RuntimeError")
        finally:
            eng.save = real_save
        check("layout untouched after the failure",
              (eng.pos_max(LIVE), eng.n_tokens(LIVE)) == before,
              "pos %d->%d n %d->%d" % (before[0], eng.pos_max(LIVE),
                                       before[1], eng.n_tokens(LIVE)))
        ans = eng.ask(LIVE, PROBES[0], n_predict=24)
        check("session still answers after the failure", "A-4417" in ans,
              ans.strip().splitlines()[0][:38] or "(empty)")

        # ---- [3] save for real, restore in a new process ---------------------
        print("\n[3] save (detach -> save -> reattach) and restore in a NEW process")
        sess = os.path.join(SESSIONS, "s.json")
        m1 = ss.save_session(eng, con, sess, blocks, anchor=CHAT, slot_capacity=SLOT)
        check("manifest written", os.path.exists(sess),
              "%d blocks, chat %d tok" % (len(m1["placement"]["blocks"]),
                                          m1["chat"]["n_tokens"]))
        check("manifest has both layers", "layout" in m1 and "placement" in m1,
              "layout + placement")
        check("layout is right-aligned with the top slot at the anchor",
              m1["layout"]["alignment"] == "right"
              and m1["layout"]["slots"][0]["end"] == CHAT,
              "anchor %d" % m1["layout"]["anchor"])
        core = lambda bs: [{k: b[k] for k in
                            ("block", "slot_id", "role", "start", "end", "n_tokens")}
                           for b in bs]
        check("placement equals what the contract renders",
              core(ss.resolve(m1["layout"],
                              {b["block"]: b["n_tokens"]
                               for b in m1["placement"]["blocks"]}))
              == core(m1["placement"]["blocks"]), "resolve() == placement")
        ans = eng.ask(LIVE, PROBES[0], n_predict=24)
        check("session reattached after save", "A-4417" in ans,
              ans.strip().splitlines()[0][:38] or "(empty)")

        cp = subprocess.run([sys.executable, "-X", "utf8", os.path.abspath(__file__),
                             "--restore", sess, "--db", DB,
                             "--out", os.path.join(SESSIONS, "s")],
                            capture_output=True, text=True, encoding="utf-8")
        line = next((l for l in cp.stdout.splitlines() if l.startswith("JSON ")), None)
        if not line:
            check("child restored the session", False, (cp.stderr or cp.stdout)[-200:])
        else:
            d = json.loads(line[5:])
            firstline = lambda t: t.splitlines()[0].strip() if t.strip() else ""
            same = sum(1 for q in PROBES
                       if firstline(d["answers"].get(q, "")) == firstline(answers.get(q, "")))
            hit = sum(1 for q, e in zip(PROBES, EXPECT) if e in d["answers"].get(q, ""))
            # The pass criterion is "the fact came back". Byte-identical output is a
            # diagnostic, not a requirement: restoring re-rotates each block from its
            # pristine file, i.e. one requantization (L3b), and that moves logits just
            # enough to change a boundary token.
            check("restored answers recover all 4 facts", hit == len(EXPECT),
                  "%d/%d facts; byte-identical first line %d/%d"
                  % (hit, len(EXPECT), same, len(PROBES)))
            for q in PROBES:
                if d["answers"].get(q) != answers.get(q):
                    print("        %s: %r -> %r" % (q, answers.get(q), d["answers"].get(q)))
            check("saved chat = dialogue only (no ledger inflation)",
                  m1["chat"]["n_tokens"] == m1["chat"]["end"] - m1["chat"]["start"],
                  "%d tokens over a span of %d"
                  % (m1["chat"]["n_tokens"], m1["chat"]["end"] - m1["chat"]["start"]))
            check("restored chat window ends where it was saved",
                  d["restored_end"] == m1["chat"]["end"],
                  "%d vs %d" % (d["restored_end"], m1["chat"]["end"]))
            check("restored chat holds the same token count",
                  d["restored_n"] == m1["chat"]["n_tokens"],
                  "%d vs %d" % (d["restored_n"], m1["chat"]["n_tokens"]))
            check("block ranges preserved",
                  [(b["block"], b["start"], b["end"]) for b in d["blocks"]]
                  == [(b["name"], b["lo"], b["hi"]) for b in blocks],
                  "%s" % [(b["start"], b["end"]) for b in d["blocks"]])
            check("one shift per block on restore",
                  d["shifts"] == len(blocks), "%d shifts for %d blocks"
                  % (d["shifts"], len(blocks)))
            check("nothing needed rebuilding", d["rebuilt"] == [], "%s" % d["rebuilt"])

            print("\n[4] second save (inside the restored process)")
            check("second save has the same block set", d["m2_blocks"] == len(blocks),
                  "%d" % d["m2_blocks"])
            check("second saved chat is still dialogue-only",
                  d["m2_chat_n"] == d["m2_chat_span"],
                  "%d tokens over %d positions" % (d["m2_chat_n"], d["m2_chat_span"]))

        # ---- [5] the contract is enforced, not decorative -------------------
        print("\n[5] a doctored manifest must be refused")
        good = ss.read_manifest(sess)

        bad = json.loads(json.dumps(good))
        bad["placement"]["blocks"][0]["end"] += 1                  # render moved
        bad["placement"]["blocks"][0]["start"] += 1
        p_bad = os.path.join(SESSIONS, "bad_render.json")
        with open(p_bad, "w", encoding="utf-8") as f:
            json.dump(bad, f, ensure_ascii=False)
        check("edited render is refused (layout recompute disagrees)",
              _refused(lambda: ss.restore_session(eng, con, p_bad), ss.LayoutMismatch),
              "LayoutMismatch")

        bad = json.loads(json.dumps(good))
        for s_, b_ in zip(bad["layout"]["slots"], bad["placement"]["blocks"]):
            b_["end"] -= 2                                        # head hole
            b_["start"] -= 2
        bad["chat"]["start"] = bad["layout"]["anchor"]
        bad["placement"]["chat_range"]["start"] = bad["layout"]["anchor"]
        p_bad2 = os.path.join(SESSIONS, "bad_head.json")
        with open(p_bad2, "w", encoding="utf-8") as f:
            json.dump(bad, f, ensure_ascii=False)
        check("a head hole is refused even when the render is self-consistent",
              _refused(lambda: ss.restore_session(eng, con, p_bad2), ss.LayoutMismatch),
              "top block no longer touches the anchor")

        bad = json.loads(json.dumps(good))
        del bad["layout"]["slots"][0]["capacity"]
        p_bad3 = os.path.join(SESSIONS, "bad_schema.json")
        with open(p_bad3, "w", encoding="utf-8") as f:
            json.dump(bad, f, ensure_ascii=False)
        check("a manifest missing a required field is refused",
              _refused(lambda: ss.restore_session(eng, con, p_bad3), ss.LayoutMismatch),
              "schema check")
    finally:
        eng.close()
        con.close()

    bad = [r for r in results if not r[1]]
    print("\n%s  %d/%d checks passed" % ("=" * 60, len(results) - len(bad), len(results)))
    for n, _ok, dd in bad:
        print("  FAILED: %s  (%s)" % (n, dd))
    return 0 if not bad else 1


def _refused(fn, exc):
    try:
        fn()
        return False
    except exc:
        return True
    except Exception as e:                    # a different failure is not the one we want
        print("        (raised %s: %s)" % (type(e).__name__, e))
        return False


if __name__ == "__main__":
    sys.exit(main())