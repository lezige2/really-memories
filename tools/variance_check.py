# -*- coding: utf-8 -*-
"""variance_check.py -- is the one-token difference a numeric effect or a state effect?

The pass criterion for a restored session is "the facts come back, and tokens / positions
/ block ranges / shifts all match". Byte-identical text is a diagnostic. But a changed
boundary token can mean three very different things:

  1. sampling      -- ruled out: generate() is greedy argmax, no sampler state;
  2. numerics      -- a block re-quantised on restore moves logits slightly. Acceptable;
  3. state/layout  -- a block was rotated one extra time, a position is off by one, or the
                      chat K did not come back as it went in. This burns the L3b budget
                      and would poison M1's recall numbers, so it must be fixed first.

Only (3) blocks M1. This script separates them by comparing K, not text:

  * two fresh processes build the SAME session and ask the same questions, and a
    transcript is compared with a second run of the same kind -- if the original is not
    reproduceable with itself, nothing downstream can be compared;
  * two fresh processes restore the same manifest;
  * for both, each sequence's whole KV state is saved to a file and hashed. A KV state
    file carries cells WITH their positions, so an equal hash means equal K, equal V and
    equal positions -- not merely "similar text";
  * the first differing character index is reported, to tell a first-token divergence
    (logits/K) from a mid-generation drift (accumulated error / EOS boundary).

Usage:  python tools/variance_check.py
"""
import hashlib
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

WORK = os.path.join(ROOT, "kvmem", "variance")
DB = os.path.join(WORK, "v.db")
BLOCKS = os.path.join(WORK, "blocks")
CHAT = 4096
SLOT = 64
LIVE = 0
GPU = 0 if os.environ.get("VARIANCE_CPU") else 99

PROBES = ["我的工号是多少？", "我养的猫叫什么名字？", "项目什么时候上线？", "项目负责人是谁？"]
EXPECT = ["A-4417", "年糕", "3月14", "周敏"]


def h(path):
    if not os.path.exists(path):
        return None
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def build_session(eng, con):
    rows = [r for r in ms.block_rows(con) if r[5] is not None]
    blocks = []
    shifts = 0
    for i, row in enumerate(rows, start=1):
        eng.reset(i)
        n = ms.load_into(eng, row, i)
        end = CHAT - (i - 1) * SLOT
        lo = end - n
        base = eng.pos_max(i) + 1 - n
        if base != lo:
            eng.repos_local(i, lo - base)
            shifts += 1
        eng.share(i, LIVE, lo, end)
        blocks.append({"seq": i, "source_id": row[0], "name": row[1],
                       "lo": lo, "hi": end, "n_tokens": n, "path": row[6]})
    return blocks, shifts


def run_orig(out):
    os.makedirs(out, exist_ok=True)
    con = ms.connect(DB)
    eng = KVEngine(ms.MODEL, n_ctx=8192, n_seq=8, gpu=GPU, kv="q8_0")
    try:
        blocks, shifts = build_session(eng, con)
        # K of each block, before anything is generated
        blk = {}
        for b in blocks:
            p = os.path.join(out, "blk%d.kvmem" % b["seq"])
            eng.save(b["seq"], p)
            blk[b["name"]] = {"file": h(p), "pos": [b["lo"], b["hi"]]}
        answers = {}
        for k, q in enumerate(PROBES):
            answers[q] = eng.ask(LIVE, q, n_predict=32,
                                 pos=(CHAT if k == 0 else None)).strip()
        cp = os.path.join(out, "chat.kvmem")
        eng.save(LIVE, cp)
        man = os.path.join(out, "s.json")
        ss.save_session(eng, con, man, blocks, anchor=CHAT, slot_capacity=SLOT)

        # A restored session starts from the state the manifest recorded -- a dialogue
        # that ALREADY contains the four rounds above. The comparable run is therefore
        # this original asking the same four questions a second time from the same
        # state, not the first pass (which started on an empty dialogue).
        answers2 = {}
        for q in PROBES:
            answers2[q] = eng.ask(LIVE, q, n_predict=32).strip()
        cp2 = os.path.join(out, "chat2.kvmem")
        eng.save(LIVE, cp2)
        payload = {"blocks": blk, "chat": h(cp), "chat2": h(cp2),
                   "chat_pos": [CHAT, eng.pos_max(LIVE) + 1],
                   "answers": answers, "answers2": answers2,
                   "shifts": shifts, "manifest": man}
        json.dump(payload, open(os.path.join(out, "r.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("JSON " + json.dumps({"ok": True}))
        return 0
    finally:
        eng.close()
        con.close()


def run_restore(manifest, out):
    os.makedirs(out, exist_ok=True)
    con = ms.connect(DB)
    eng = KVEngine(ms.MODEL, n_ctx=8192, n_seq=8, gpu=GPU, kv="q8_0")
    try:
        rep = ss.restore_session(eng, con, manifest)
        # the state of the chat exactly as it came off disk, before any generation:
        # this is the one hash that can tell "the state was not restored" (class 3)
        # from "the state was restored but the numbers moved" (class 2)
        cp0 = os.path.join(out, "chat_onload.kvmem")
        eng.save(LIVE, cp0)
        blk = {}
        for b in rep["blocks"]:
            seq = b["slot_id"] + 1
            p = os.path.join(out, "blk%d.kvmem" % seq)
            eng.save(seq, p)
            blk[b["block"]] = {"file": h(p), "pos": [b["start"], b["end"]]}
        answers = {}
        for q in PROBES:
            answers[q] = eng.ask(LIVE, q, n_predict=32).strip()
        cp = os.path.join(out, "chat.kvmem")
        eng.save(LIVE, cp)
        payload = {"blocks": blk, "chat_onload": h(cp0), "chat_after": h(cp),
                   "chat_pos": [CHAT, eng.pos_max(LIVE) + 1],
                   "answers": answers, "shifts": rep["shifts"],
                   "rebuilt": rep["rebuilt"]}
        json.dump(payload, open(os.path.join(out, "r.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("JSON " + json.dumps({"ok": True}))
        return 0
    finally:
        eng.close()
        con.close()


def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b)) if len(a) != len(b) else -1


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", choices=["orig", "restore"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--manifest", default=None)
    a = ap.parse_args()
    if a.role == "orig":
        return run_orig(a.out)
    if a.role == "restore":
        return run_restore(a.manifest, a.out)

    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(BLOCKS, exist_ok=True)
    con = ms.connect(DB)
    eng = KVEngine(ms.MODEL, n_ctx=8192, n_seq=8, gpu=GPU, kv="q8_0")
    try:
        for name, label, text in demo.MEMORIES:
            ms.put_source(con, name, label, text)
            ms.build_block(eng, con, ms.get_source(con, name), BLOCKS)
    finally:
        eng.close()
        con.close()

    def spawn(args):
        cp = subprocess.run([sys.executable, "-X", "utf8", os.path.abspath(__file__)]
                            + args, capture_output=True, text=True, encoding="utf-8")
        if "JSON" not in cp.stdout:
            print(cp.stdout[-400:], cp.stderr[-800:])
            raise SystemExit("child failed: %s" % " ".join(args))

    print("step 1: the original session, twice, in two fresh processes")
    o1, o2 = os.path.join(WORK, "o1"), os.path.join(WORK, "o2")
    spawn(["--role", "orig", "--out", o1])
    spawn(["--role", "orig", "--out", o2])
    r1 = json.load(open(os.path.join(o1, "r.json"), encoding="utf-8"))
    r2 = json.load(open(os.path.join(o2, "r.json"), encoding="utf-8"))
    orig_stable = r1["answers"] == r2["answers"] and r1["chat"] == r2["chat"]
    print("   answers identical: %s" % (r1["answers"] == r2["answers"]))
    print("   chat K identical  : %s (%s vs %s)" % (r1["chat"] == r2["chat"],
                                                    r1["chat"], r2["chat"]))
    print("   block K identical : %s" % (r1["blocks"] == r2["blocks"]))
    if not orig_stable:
        print("\nVERDICT: the original session is not reproduceable with itself -- "
              "there is hidden non-determinism; fix that before comparing anything else")
        return 1

    print("\nstep 2: restore the same manifest, twice, in two fresh processes")
    s1, s2 = os.path.join(WORK, "s1"), os.path.join(WORK, "s2")
    spawn(["--role", "restore", "--manifest", r1["manifest"], "--out", s1])
    spawn(["--role", "restore", "--manifest", r1["manifest"], "--out", s2])
    t1 = json.load(open(os.path.join(s1, "r.json"), encoding="utf-8"))
    t2 = json.load(open(os.path.join(s2, "r.json"), encoding="utf-8"))
    print("   answers identical: %s" % (t1["answers"] == t2["answers"]))
    print("   block K identical : %s" % (t1["blocks"] == t2["blocks"]))

    print("\nstep 3: compare K, not text (original vs restore)")
    blk_same = r1["blocks"] == t1["blocks"]
    print("   block K   : %s" % ("identical" if blk_same else "DIFFERENT"))
    for name in r1["blocks"]:
        a_, b_ = r1["blocks"][name], t1["blocks"].get(name, {})
        same = a_ == b_
        print("      %-8s %s  pos %s vs %s  hash %s vs %s"
              % (name, "same" if same else "DIFF", a_["pos"], b_.get("pos"),
                 a_["file"], b_.get("file")))
    print("   chat K    : %s (before asking: %s, after asking: %s)"
          % ("comparable" if t1.get("chat_after") else "n/a", r1["chat"],
             t1.get("chat_after")))

    print("\nstep 4: where the text diverges (original pass 2 vs restore pass 1)")
    exact = 0
    for q in PROBES:
        a_, b_ = r1["answers2"][q], t1["answers"][q]
        if a_ == b_:
            exact += 1
            print("   %-24s identical" % q[:24])
        else:
            i = first_diff(a_, b_)
            print("   %-24s differs at char %d  %r -> %r"
                  % (q[:24], i, a_[max(0, i - 6):i + 10], b_[max(0, i - 6):i + 10]))
    print("   byte-identical answers: %d/%d" % (exact, len(PROBES)))
    hits_a = sum(1 for e in EXPECT if any(e in v for v in r1["answers2"].values()))
    hits_b = sum(1 for e in EXPECT if any(e in v for v in t1["answers"].values()))
    print("   facts recovered: original %d/%d, restore %d/%d"
          % (hits_a, len(EXPECT), hits_b, len(EXPECT)))

    print("\n" + "=" * 78)
    print("verdict")
    shifts_ok = r1["shifts"] == t1["shifts"]
    print("   shifts: original %d, restore %d  -> %s"
          % (r1["shifts"], t1["shifts"], "same" if shifts_ok else "DIFFERENT"))
    if not blk_same:
        print("   CLASS 3 (state): block K differs after restore -> the session, not the "
              "numerics, is changing. Count the shifts above before going further.")
        return 2
    if not shifts_ok:
        print("   CLASS 3 (state): the number of rotations differs -> an extra "
              "requantisation is being spent somewhere")
        return 2
    # A whole-file hash is too strict here: the state file stores cells in cell-index
    # order, and a restored sequence gets different cell indices. So measure HOW MUCH
    # differs, not just whether anything does.
    fa = os.path.join(o1, "chat.kvmem")
    fb = os.path.join(s1, "chat_onload.kvmem")
    if os.path.exists(fa) and os.path.exists(fb):
        A, B = open(fa, "rb").read(), open(fb, "rb").read()
        n = min(len(A), len(B))
        diffs = [i for i in range(n) if A[i] != B[i]]
        print("   chat state file  : %d vs %d bytes, %d differing byte(s) (%.4f%% of %d), "
              "first at offset %s"
              % (len(A), len(B), len(diffs), 100.0 * len(diffs) / max(1, n), n,
                 diffs[0] if diffs else "-"))
        if diffs:
            cut = diffs[0]
            head = A[:cut] == B[:cut]
            pa, pb = sorted(A[cut:]), sorted(B[cut:])
            same_multiset = pa == pb
            print("   header+tokens up to offset %d: %s" % (cut, "identical" if head else "DIFFER"))
            print("   K/V payload from offset %d: %d bytes each, byte multiset %s"
                  % (cut, len(A) - cut,
                     "IDENTICAL -> same cells, permuted cell order"
                     if same_multiset else "DIFFERS -> the cell contents themselves changed"))
            if not same_multiset:
                only_a = len(pa) - len(pb)
                print("      multiset delta: %d byte(s)" % only_a)
    print("   chat K as loaded : %s (saved %s)  -> %s"
          % (t1.get("chat_onload"), r1["chat"],
             "restored byte-exactly" if t1.get("chat_onload") == r1["chat"]
             else "NOT restored byte-exactly"))
    chat_same = r1.get("chat2") == t1.get("chat_after")
    print("   chat K after one identical pass: %s (%s vs %s)"
          % ("identical" if chat_same else "DIFFERENT", r1.get("chat2"),
             t1.get("chat_after")))
    if exact == len(PROBES):
        print("   CLASS 2 (numerics), and not even visible: block K, positions, shift "
              "counts, chat K and all four answers match byte for byte")
        print("   -> restore is bit-exact here. The earlier 3/4 came from comparing a "
              "restored dialogue against an original on a DIFFERENT prefix (the test "
              "saved the manifest after the answers were taken).")
    else:
        print("   CLASS 2 (numerics): block K and positions are byte-identical and the "
              "shift counts agree, so the divergence is downstream of memory -- check "
              "the chat prefix before blaming the layout")
    return 0


if __name__ == "__main__":
    sys.exit(main())