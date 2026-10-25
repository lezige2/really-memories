# -*- coding: utf-8 -*-
# M4-B: the licence-plate ablation. Does the plate memory depend on the sentence carrying it?
#
# One run json, arms side by side, never split into two files (splitting means nobody looks at
# them in parallel). Same block source, same attach position rule, same question, same n_predict;
# the only intended difference between the ablation pair is whether the plate sentence exists in
# the block text.
#
#   python -u -X utf8 m4_ablate_plate.py --out run_m4_ablate_plate_a1.json --attempt 1
#
# This is an ablation, not a verification: neither direction is preferred in advance. What it
# does require is the product-block control arm -- if a known-answer block stops answering, the
# harness is broken and the ablation pair says nothing.
import argparse, hashlib, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
for _p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "kvmem", "m2_visibility", "m2"),
           os.path.join(ROOT, "kvmem", "m2_visibility", "m3"), HERE):
    sys.path.insert(0, _p)
import m2_visibility_probe as P
import _driver_m2 as M2
import m3_lease as L
import outfilter as OUT

BLOCK_SEQ = 1
LIVE = 0
POS_HI = 4096
# ONE source for n_predict. Attempt 4's record said 24 while its child engine ran 64 because
# --child never received the value: same family as attach_range being a declaration, not a reading.
N_PREDICT = int(P.N_PREDICT)
N_PREDICT_SRC = "top-level constant P.N_PREDICT, handed to --child via --n-predict"
QUESTION = "我的车牌号是多少？"
PLATE = "浙B-3F19K"
PRODUCT_BLOCK = "blk_conv_2026-10-25_01"
# The ablation is confounded by construction: deleting a sentence also shortens the block. This arm
# keeps the cell count and the attach range identical and changes only the words, so "content" and
# "length" stop being one variable.
LENMATCH_CANDIDATES = [
    "我车牌是浙Q-00000。",
    "我车牌是浙B-3F19L。",
    "我车牌是冀A-11111。",
    "我车牌是浙Q00000。",
    "我车牌是苏A12345。",
]


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha16(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def ask_arm(eng, leases, name, path, block_id, role, no_repos=False, n_predict=None,
            lenient_n_predict=False):
    """register -> gated reset -> load -> attach at the same rule -> ask at POS_HI.

    Attempt 2 asked at P.raw_pos_max(LIVE)+1, which came back 0, so the question was put at
    position 0 while the block sat at [4005,4096): the block never entered the context and all
    three arms answered from the prompt alone, byte-identically. m4_verify asks at ask_pos =
    pos_hi, so this driver now does exactly that and only REPORTS the raw pos_max readings.
    """
    leases.register_block(BLOCK_SEQ, block_id)
    # safe_reset_all skips registered blocks (m3's guard), so the seq keeps the previous arm's
    # cells unless it is cleared explicitly. reset() is the gated path: it refuses while leased.
    try:
        seq_cleared = leases.reset(BLOCK_SEQ)
        seq_clear_note = "reset via leases.reset (gated: refuses while leased)"
    except Exception as exc:
        seq_cleared = False
        seq_clear_note = "refused: %s" % (type(exc).__name__ + ": " + str(exc))
    moved = eng.load_strict(BLOCK_SEQ, path)
    # m4_newproc.py:161-166, mirrored line for line. load_strict leaves the cells at [0,n) and
    # share() must be given the range the cells ACTUALLY occupy, so the block has to be physically
    # moved to [ASK_ANCHOR-n, ASK_ANCHOR) before attaching. Attempt 3 skipped repos_local and
    # attached [4005,4096) over cells sitting at [0,91): the product block answered from the prompt
    # alone (鲁QXXXX) and both re-encoded arms came back empty.
    if no_repos:
        # step 1 of the plan: change ONE thing. With this switch the reposition is skipped and the
        # cells stay at [0,n) exactly as in attempt 3, so the only difference is process isolation.
        base = None
        span = P.cell_scan(eng, BLOCK_SEQ)[1]
        print("[arm %s] --no-repos: cells left at %r" % (name, (min(span), max(span)) if span else None),
              flush=True)
    else:
        base = eng.pos_max(BLOCK_SEQ) - moved + 1
        eng.repos_local(BLOCK_SEQ, POS_HI - moved - base)
        span = P.cell_scan(eng, BLOCK_SEQ)[1]
    cells = len(span)
    lo, hi = POS_HI - moved, POS_HI
    span_ok = bool(span) and min(span) == lo and max(span) == hi - 1
    if no_repos:
        span_ok = None   # deliberately not checked: this switch exists to reproduce the old state
    if span_ok is False:
        # fail before the ask, not after: an arm whose block is not inside the attached range is
        # answering from the prompt, and its answer looks real (that is the whole trap)
        raise RuntimeError("arm %s: block cells span %r but the attach range is [%s,%s); the "
                           "block would not be in the context"
                           % (name, [min(span), max(span)] if span else None, lo, hi))
    pos_max_block = P.raw_pos_max(eng, BLOCK_SEQ)
    leases.attach(BLOCK_SEQ, LIVE, lo, hi)
    pos_max_live = P.raw_pos_max(eng, LIVE)
    pos = POS_HI
    n_pred = N_PREDICT if n_predict is None else int(n_predict)
    engine_n_pred = getattr(eng, "n_predict", None)
    # None means the engine exposes no n_predict, i.e. UNKNOWN. Reporting that as True would be a
    # green reading of an empty measurement -- exactly what a2's output_filter_counts did.
    n_pred_consistent = None if engine_n_pred is None else (int(engine_n_pred) == n_pred)
    if n_pred_consistent is False and not lenient_n_predict:
        raise RuntimeError("n_predict declared %r but the engine reports %r; refusing to ask"
                           % (n_pred, engine_n_pred))
    nb, ans = M2.D2.ask_native(eng, LIVE, QUESTION, pos, n_pred)
    txt = (ans or "").strip()
    f = OUT.filter_text(txt)
    delivered = f["text"]
    try:
        OUT.assert_clean(delivered, name + " delivered text")
        assertion = "pass"
    except OUT.ControlTagLeft as exc:
        assertion = "FAIL: " + str(exc)
    rec = {"arm": name, "role": role,
           "block_path": path.replace(os.sep, "/"),
           "block_sha256": sha_file(path),
           "cells_loaded": moved, "cells_in_block_seq": cells,
           "attach_rule": "repos_local(POS_HI - moved - base) then lo = POS_HI - moved; hi = POS_HI "
                          "-- mirrored from m4_newproc.py:161-166",
           "cells_span_after_repos": [min(span), max(span)] if span else None,
           "cells_span_matches_attach_range": span_ok,
           "repos_skipped": bool(no_repos),
           "attach_range_is": "declared AND asserted equal to the measured cell span "
                              "(cells_span_after_repos); with --no-repos it is declared only",
           "n_predict": n_pred, "n_predict_source": N_PREDICT_SRC,
           "engine_reports_n_predict": engine_n_pred,
           "n_predict_consistent": n_pred_consistent,
           "n_predict_consistent_meaning": "None = the engine exposes no n_predict attribute, so "
                                           "the declared value is UNVERIFIED, not confirmed",
           "attach_range": [lo, hi], "pos_asked": pos,
           "pos_asked_source": "POS_HI (= pos_hi) -- the same value m4_verify passes as ask_pos",
           "raw_pos_max_block_after_attach": pos_max_block,
           "raw_pos_max_live_after_attach": pos_max_live,
           "raw_pos_max_readings_are_observations": "reported, never used to place the question",
           "seq_cleared_before_load": seq_cleared, "seq_clear_note": seq_clear_note,
           "ask_bytes": nb,
           "answer_raw": txt, "answer_len": len(txt),
           "answer_delivered": delivered,
           "output_filter": {"per_tag": f["per_tag"],
                             "tag_chars_removed": f["tag_chars_removed"],
                             "raw_to_delivered_delta": len(txt) - len(delivered),
                             "delivered_has_tag": OUT.scan(delivered)["total"]},
           "assertion": assertion,
           "answers_plate": PLATE in txt}
    # READ, not guessed: m3_lease.py:78 is "def detach(self, dst_seq, lo, hi)" -- the block seq
    # is recovered from the range table inside, so passing it here is a TypeError. That is how
    # attempt 1 died after arm 1 had already asked its question.
    leases.detach(LIVE, lo, hi)
    print("[arm %-22s] cells=%s range=[%s,%s) pos=%s bytes=%s answers_plate=%s ans=%r"
          % (name, moved, lo, hi, pos, nb, rec["answers_plate"], txt[:40]), flush=True)
    return rec


# Built by concatenation on purpose: a literal marker would also match the marker string inside
# this very file, and the first version of this predicate did exactly that -- it located its own
# literal instead of the function and reported a false defect. Self-reference is the default.
M_ASK = "def ask_" + "arm("
M_SELF = "def self" + "check("
M_MAIN = "def ma" + "in("
M_TAIL = "def sha_file_" + "hex("
# Third self-reference trap in a row: this marker is also searched for, so it must not appear as a
# literal either -- otherwise replace() hits the copy below instead of the real comment in main().
M_ENC = "    # ---- encode phase: BEFORE " + "anything is registered"
ARM_LINE = '    res["arms"].append(spawn_' + 'child(a, "product_block_control", prod_path,'


def _region(src, start, end):
    i = src.find(start)
    j = src.find(end)
    return src[i:j] if 0 <= i < j else None


def check_source(src):
    """The two attempt-2 defects, as predicates over the driver's own source text.

    They must be able to fail: run_selfcheck_negative() feeds them deliberately broken sources.
    """
    problems = []
    arm = _region(src, M_ASK, M_SELF)
    main = _region(src, M_MAIN, M_TAIL)
    if arm is None or main is None:
        return ["could not locate ask_arm/main in this source (predicate cannot run)"]
    pos_assigns = [ln.strip() for ln in arm.split(chr(10)) if ln.strip().startswith("pos = ")]
    if pos_assigns != ["pos = POS_HI"]:
        problems.append("ask position is not the POS_HI constant: %r" % (pos_assigns,))
    if any("raw_pos_max" in ln for ln in pos_assigns):
        problems.append("ask position derived from raw_pos_max; m4_verify asks at pos_hi")
    # the block must be MOVED onto the attach anchors before sharing, exactly as m4_newproc does;
    # attempt 3 omitted it and every arm answered from the prompt alone
    i_repos = arm.find("repos_local(")
    i_attach = arm.find("leases.attach(")
    if i_repos < 0:
        problems.append("ask_arm never calls repos_local; the cells stay at [0,n) while the "
                        "attach range is [POS_HI-n, POS_HI)")
    elif 0 <= i_attach < i_repos:
        problems.append("attach happens before the reposition; the shared range would be empty")
    i_enc = main.find("safe_reset_all(range(P.N_SEQ))")
    i_arm = main.find(chr(34).join(["res[", "arms", "].append("]))
    if i_enc < 0 or i_arm < 0:
        problems.append("could not locate the encode loop or the arm calls in main()")
    elif i_enc > i_arm:
        problems.append("encode runs after the first arm; safe_reset_all skips registered "
                        "blocks, so the seq keeps its cells and write_at returns -1")
    return problems


def selfcheck_negative():
    """Prove check_source() can go red, using mutated copies of this file's own source."""
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        src = f.read()
    cases = []
    broken_pos = src.replace("    pos = POS_HI",
                             "    pos = P.raw_pos_max(eng, LIVE) + 1", 1)
    cases.append(("ask position from raw_pos_max", broken_pos))
    # move the arms ABOVE the encode loop instead of shuffling the file: shuffling also destroys
    # the markers, so the predicate would complain about the wrong thing
    if M_ENC in src and ARM_LINE in src:
        cases.append(("an arm call placed before the encode loop",
                      src.replace(M_ENC, ARM_LINE + chr(10) + M_ENC, 1)))
    bad = []
    for label, text in cases:
        found = check_source(text)
        print("[selfcheck-negative] %-32s -> %s" % (label, found if found else "NOT CAUGHT"))
        if not found:
            bad.append(label)
    if len(cases) < 2:
        bad.append("negative cases could not be constructed")
    return bad


def run_child(a):
    """One child = one engine = one arm. Parallel engines are forbidden by the standing rule, and
    attempt 3 showed why arms must not share a process: identical block bytes gave 96 bytes in arm
    1 and -1 in arm 2, i.e. the earlier arms polluted the later ones."""
    eng = P.open_engine()
    try:
        leases = L.BlockLeases(eng)
        # nothing is registered before this reset, so it really clears the block seq
        leases.safe_reset_all(range(P.N_SEQ))
        if a.n_predict is not None and int(a.n_predict) != N_PREDICT:
            raise SystemExit("child got --n-predict %r but this file's constant is %r"
                             % (a.n_predict, N_PREDICT))
        rec = ask_arm(eng, leases, a.child, a.block_path, a.block_id, a.role or "",
                      no_repos=a.no_repos,
                      n_predict=N_PREDICT if a.n_predict is None else int(a.n_predict),
                      lenient_n_predict=a.lenient_n_predict)
        rec["n_predict_received_from_parent"] = a.n_predict is not None
    finally:
        pass
    rec["child_pid"] = os.getpid()
    print("JSON:" + json.dumps(rec, ensure_ascii=False), flush=True)
    return 0


def spawn_child(a, name, path, block_id, role):
    import subprocess
    cmd = [sys.executable, "-u", "-X", "utf8", os.path.abspath(__file__),
           "--child", name, "--block-path", path, "--block-id", block_id, "--role", role,
           "--blocks", a.blocks, "--attempt", str(a.attempt), "--n-predict", str(N_PREDICT)]
    if a.lenient_n_predict:
        cmd.append("--lenient-n-predict")
    if a.no_repos:
        cmd.append("--no-repos")
    print("[child] %s -> %s" % (name, " ".join(cmd[1:])), flush=True)
    pr = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    sys.stdout.write(pr.stdout)
    sys.stderr.write(pr.stderr)
    for line in pr.stdout.split(chr(10)):
        if line.startswith("JSON:"):
            rec = json.loads(line[5:])
            rec["child_rc"] = pr.returncode
            return rec
    raise SystemExit("child %s produced no JSON (rc=%s)" % (name, pr.returncode))


def encode_check(a):
    """Single-factor experiment: does the encode path itself return -1, or only when the seq is
    dirty? Nothing is registered here, so safe_reset_all really resets seq 1. Asks nothing."""
    src = json.load(open(os.path.join(HERE, a.write_run), encoding="utf-8"))
    text = src["block_text"]
    ablated = chr(10).join(ln for ln in text.split(chr(10)) if PLATE not in ln)
    eng = P.open_engine()
    leases = L.BlockLeases(eng)
    rows = []
    for tag, body in (("original_text", text), ("ablated_text", ablated)):
        info = leases.safe_reset_all(range(P.N_SEQ))
        n_tok = eng.write_at(BLOCK_SEQ, body, 0)
        cells = P.cell_scan(eng, BLOCK_SEQ)[0]
        rows.append({"case": tag, "tokens_written": n_tok, "cells_in_seq": cells,
                     "text_len": len(body), "reset_before_encode": info})
        print("[encode-check] %-14s tokens=%s cells=%s (text %d chars)"
              % (tag, n_tok, cells, len(body)), flush=True)
    # Expected values are RELATIONAL, never copied from a previous run. The earlier expectation of
    # "91 and 91" was wrong on its face: the ablated text is 14 characters shorter, so its token
    # count must be LOWER. Judging by a copied constant would have failed a healthy result and
    # then invited a fix to something that was never broken.
    by_tag = {r["case"]: r for r in rows}
    checks = {
        "original_tokens_positive": by_tag["original_text"]["tokens_written"] > 0,
        "ablated_tokens_positive": by_tag["ablated_text"]["tokens_written"] > 0,
        "original_cells_equal_tokens":
            by_tag["original_text"]["cells_in_seq"] == by_tag["original_text"]["tokens_written"],
        "ablated_cells_equal_tokens":
            by_tag["ablated_text"]["cells_in_seq"] == by_tag["ablated_text"]["tokens_written"],
        "ablated_shorter_than_original":
            by_tag["ablated_text"]["tokens_written"] < by_tag["original_text"]["tokens_written"],
        "shorter_text_is_shorter": len(ablated) < len(text),
    }
    print("[encode-check] criteria:", json.dumps(checks, ensure_ascii=False), flush=True)
    bad = [k for k, v in checks.items() if not v]
    print("[encode-check] %s (%d tokens / %d tokens; a -1 would mean the PATH is broken, while a "
          "-1 only in the full run means the seq was dirty)"
          % ("PASS" if not bad else "FAIL: " + ", ".join(bad),
             by_tag["original_text"]["tokens_written"],
             by_tag["ablated_text"]["tokens_written"]), flush=True)
    return 0 if not bad else 4


def selfcheck():
    """SCOPE: interface shape only. No engine, no model.

    What it proves: every lease/engine call this driver makes fits the REAL signature, and the
    arm skeleton wires the calls in the right order. That is exactly how attempt 1's extra
    detach() argument was caught offline.

    What it does NOT prove, and cannot: that the real path derives the same VALUES. Attempt 2
    asked at position 0 while the block sat at [4005,4096); this selfcheck said pos_asked=4096
    because the stub itself supplied 4096. A stub that feeds the value it then asserts proves the
    interface, not the wiring. So the value question is checked separately below by reading this
    driver's own source: the ask position must be the POS_HI constant and must never be derived
    from a pos_max reading.
    """
    import inspect
    import tempfile
    problems = []

    # -- real-value checks: read from SOURCE, not from the stub -----------------------
    # Attempt 2's two bugs were invisible to the stub by construction (the stub supplied the very
    # value it then asserted). These predicates look only at the code region that can hold the bug
    # -- and not at themselves, which is what made the first version of this check fire on its
    # own source line.
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        src = f.read()
    for why in check_source(src):
        problems.append(why)
    fake_self = object.__new__(L.BlockLeases) if hasattr(L, "BlockLeases") else object()

    def bind(fn, label, *args):
        try:
            inspect.signature(fn).bind(*args)
        except TypeError as exc:
            problems.append("%s%r -> %s" % (label, args, exc))

    bind(L.BlockLeases.register_block, "register_block", fake_self, BLOCK_SEQ, "blk")
    bind(L.BlockLeases.safe_reset_all, "safe_reset_all", fake_self, range(P.N_SEQ))
    bind(L.BlockLeases.attach, "attach", fake_self, BLOCK_SEQ, LIVE, 0, 91)
    bind(L.BlockLeases.detach, "detach", fake_self, LIVE, 0, 91)

    class StubEng(object):
        def __init__(self):
            self.calls = []

        def load_strict(self, seq, path):
            self.calls.append("load_strict")
            return 91

        def save(self, seq, path):
            self.calls.append("save")
            return 0

        def write_at(self, seq, text, pos):
            self.calls.append("write_at")
            return 91

        # mirrored from m4_newproc: load_strict leaves cells at [0,n), so pos_max is n-1 and the
        # reposition shift moves them onto anchors [ASK_ANCHOR-n, ASK_ANCHOR)
        def pos_max(self, seq):
            self.calls.append("pos_max")
            return 90

        def repos_local(self, seq, shift):
            self.calls.append(("repos_local", shift))
            return shift

    class StubLeases(object):
        def __init__(self):
            self.calls = []

        def register_block(self, seq, bid):
            self.calls.append(("register_block", seq, bid))

        def safe_reset_all(self, seqs):
            self.calls.append(("safe_reset_all", tuple(seqs)))
            return {"reset": list(seqs)}

        def attach(self, seq, dst, lo, hi):
            self.calls.append(("attach", seq, dst, lo, hi))

        def detach(self, dst, lo, hi):
            self.calls.append(("detach", dst, lo, hi))

        def reset(self, seq):
            self.calls.append(("reset", seq))
            return True

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".kvmem")
    tmp.write(b"x" * 16)
    tmp.close()
    real = (P.cell_scan, P.raw_pos_max, M2.D2.ask_native)
    try:
        P.cell_scan = lambda eng, seq: (91, list(range(POS_HI - 91, POS_HI))
                                        if seq == BLOCK_SEQ else [])
        # post-attach both sequences read POS_HI-1, so the ask position becomes POS_HI; the stub
        # must model the state AFTER attach, otherwise it is the stub that is wrong, not the driver
        P.raw_pos_max = lambda eng, seq: (POS_HI - 1)
        M2.D2.ask_native = lambda eng, seq, q, pos, n: (93, "浙B-3F19K")
        stub_l = StubLeases()
        rec = ask_arm(StubEng(), stub_l, "selfcheck_stub", tmp.name, "blk_selfcheck", "stub")
        want = [c[0] for c in stub_l.calls]
        if "detach" not in want:
            problems.append("ask_arm never detached: %r" % (want,))
        if rec["pos_asked"] != POS_HI:
            problems.append("pos_asked=%r expected %r" % (rec["pos_asked"], POS_HI))
        if rec["attach_range"] != [POS_HI - 91, POS_HI]:
            problems.append("attach_range=%r" % (rec["attach_range"],))
        if not rec["answers_plate"]:
            problems.append("stub answer should have been recognised as carrying the plate")
        if not rec["cells_span_matches_attach_range"]:
            problems.append("stub span check did not hold: %r vs range %r"
                            % (rec["cells_span_after_repos"], rec["attach_range"]))
        print("[selfcheck] lease calls:", want)
    finally:
        P.cell_scan, P.raw_pos_max, M2.D2.ask_native = real
        os.unlink(tmp.name)

    # the check must be able to go red: the attempt-1 call shape has to be rejected here
    try:
        inspect.signature(L.BlockLeases.detach).bind(fake_self, BLOCK_SEQ, LIVE, 0, 91)
        problems.append("negative case NOT caught: the arity check cannot fail, so it proves nothing")
    except TypeError:
        print("[selfcheck] negative case (attempt-1 call shape) correctly rejected")
    negative_misses = selfcheck_negative()
    if negative_misses:
        problems.append("check_source cannot fail on: %r" % (negative_misses,))
    print("[selfcheck] problems:", problems if problems else "NONE")
    print("[selfcheck] %s -- no engine was loaded" % ("PASS" if not problems else "FAIL"))
    return 0 if not problems else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="run_m4_ablate_plate_a1.json")
    ap.add_argument("--attempt", type=int, default=1)
    ap.add_argument("--blocks", default=os.path.join(HERE, "blocks"))
    ap.add_argument("--write-run", default="run_m4_write.json")
    ap.add_argument("--selfcheck", action="store_true",
                    help="bind every call against the real signatures and run the arm skeleton "
                         "with stubs; needs no engine and writes no artifact")
    ap.add_argument("--encode-check", action="store_true",
                    help="encode both texts through the same write path and print the token "
                         "counts; asks nothing and writes no artifact")
    ap.add_argument("--child", default=None, help="internal: run exactly one arm in this process")
    ap.add_argument("--block-path", default=None)
    ap.add_argument("--block-id", default=None)
    ap.add_argument("--role", default="")
    ap.add_argument("--n-predict", type=int, default=None,
                    help="internal: the parent's generation budget, so the child cannot fall "
                         "back to the engine default (attempt 4 ran 64 while the record said 24)")
    ap.add_argument("--lenient-n-predict", action="store_true",
                    help="record an engine/declared n_predict mismatch instead of refusing to ask: "
                         "the engine attribute is a constructor default, while the per-call "
                         "argument is what the shim receives")
    ap.add_argument("--no-lenmatch", action="store_true",
                    help="skip the equal-length arm, leaving the length confound unsplit")
    ap.add_argument("--no-repos", action="store_true",
                    help="step 1: skip the reposition so the ONLY change is process isolation")
    a = ap.parse_args()
    if a.child:
        return run_child(a)
    if a.selfcheck:
        return selfcheck()
    if a.encode_check:
        return encode_check(a)
    t0 = time.time()

    src = json.load(open(os.path.join(HERE, a.write_run), encoding="utf-8"))
    text = src["block_text"]
    prod_path = os.path.join(a.blocks, PRODUCT_BLOCK + ".kvmem")
    ab_path = os.path.join(a.blocks, "blk_conv_plateablate_attempt%d.kvmem" % a.attempt)
    ctrl_path = os.path.join(a.blocks, "blk_conv_platecontrol_attempt%d.kvmem" % a.attempt)
    for _p in (ab_path, ctrl_path):
        if os.path.exists(_p):
            raise SystemExit("refusing to overwrite a block from an earlier attempt: " + _p)

    lines = text.split(chr(10))
    removed = [ln for ln in lines if PLATE in ln]
    kept = [ln for ln in lines if PLATE not in ln]
    ablated = chr(10).join(kept)

    res = {"schema": "m4_ablate_plate_v1", "attempt": a.attempt, "pid": os.getpid(),
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "question": QUESTION, "plate": PLATE, "block_seq": BLOCK_SEQ, "live": LIVE,
           "pos_hi": POS_HI, "n_predict": N_PREDICT,
           "prereg": {
               "declared_before_run": True,
               "single_factor": "only the plate sentence is removed from the block text; every other line is byte-identical",
               "control_arm_required": "the product block must still answer the plate; otherwise both ablation arms are uninterpretable",
               "if_ablated_answers_plate": "the memory does not depend on that sentence (it is stored elsewhere, or the answer is fabricated)",
               "if_ablated_does_not_answer": "the memory is carried by that sentence",
               "asymmetry": "neither direction is preferred in advance: this is an ablation, not a verification",
               "what_it_cannot_show": "it cannot say WHERE else the plate could live, only whether deleting this sentence changes the answer",
           },
           "inputs": {
               "block_text_sha256": sha_file_hex(text), "block_text_len": len(text),
               "block_text_line_count": len(lines),
               "ablated_sha256": sha_file_hex(ablated), "ablated_len": len(ablated),
               "ablated_lines": len(kept),
               "removed_lines": removed, "removed_lines_count": len(removed),
               "ablated_block_text_lines": kept,
               "plate_in_ablated_text": PLATE in ablated,
               "plate_absent_from_ablated": PLATE not in ablated,
               "only_removal_check": {"chars_removed": len(text) - len(ablated),
                                     "expected": sum(len(x) + 1 for x in removed),
                                     "other_lines_identical": kept == [ln for ln in lines if ln not in removed]},
               # a sha proves "unchanged", not "what it says": without the lines nobody can answer
               # "is 苏A12345 in the block?" from the artifact alone
               "block_text_lines": lines,
               "block_text_lines_count": len(lines),
               "product_block_path": prod_path.replace(os.sep, "/"),
               "product_block_sha256": sha_file(prod_path),
               "ablated_block_path": ab_path.replace(os.sep, "/"),
               "ablated_block_is_new": True,
               "product_block_untouched": "loaded read-only; the block file is never written here",
           },
           "arms": []}

    res["engine"] = {"dll_sha256": sha_file(os.path.join(ROOT, "tools", "kvshim_vk.dll")),
                     "n_seq": P.N_SEQ, "n_predict": P.N_PREDICT,
                     "one_engine_per_process": True,
                     "process_model": "the parent holds no engine: encode and each arm run in "
                                      "their own child, sequentially"}
    eng = P.open_engine()          # encode phase only; released before any arm child starts
    leases = L.BlockLeases(eng)

    # ---- encode phase: BEFORE anything is registered -------------------------------
    # safe_reset_all SKIPS every seq in leases.blocks; that guard is why m3 exists. Attempt 2
    # registered first, so seq 1 was skipped, still held 91 cells, and write_at(seq, text, 0)
    # into a non-empty seq returned -1 twice -- "-1 tokens" was the engine REFUSING, not a count.
    for tag, body, path, key in (
            ("reencoded_with_sentence", text, ctrl_path, "reencoded_encode"),
            ("ablated_without_sentence", ablated, ab_path, "ablated_encode")):
        reset_info = leases.safe_reset_all(range(P.N_SEQ))
        n_tok = eng.write_at(BLOCK_SEQ, body, 0)
        cells = P.cell_scan(eng, BLOCK_SEQ)[0]
        saved = eng.save(BLOCK_SEQ, path) if n_tok > 0 else None
        res["inputs"][key] = {"tokens_written": n_tok, "cells_after_encode": cells,
                              "bytes_saved": saved,
                              "block_sha256": sha_file(path) if saved else None,
                              "reset_before_encode": reset_info,
                              "path": path.replace(os.sep, "/")}
        print("[encode] %-24s tokens=%s cells=%s -> %s" % (tag, n_tok, cells, path), flush=True)
        if n_tok <= 0:
            raise SystemExit("encode of %s returned %r: the engine refused (a non-empty seq is "
                             "the usual reason). Aborting before any arm runs -- an arm loaded "
                             "from a refused encode is not interpretable." % (tag, n_tok))
        if cells != n_tok:
            raise SystemExit("encode of %s wrote %d tokens but the seq holds %d cells"
                             % (tag, n_tok, cells))

    # ---- equal-length control: same cell count, same attach range, different words ------
    lenm = None
    lenmatch_path = os.path.join(a.blocks, "blk_conv_platematch_attempt%d.kvmem" % a.attempt)
    if not a.no_lenmatch:
        if os.path.exists(lenmatch_path):
            raise SystemExit("refusing to overwrite an earlier attempt: " + lenmatch_path)
        ctrl_tokens = res["inputs"]["reencoded_encode"]["tokens_written"]
        tried = []
        for cand in LENMATCH_CANDIDATES:
            body = chr(10).join([cand if PLATE in ln else ln for ln in lines])
            leases.safe_reset_all(range(P.N_SEQ))
            n_tok = eng.write_at(BLOCK_SEQ, body, 0)
            tried.append({"text": cand, "tokens_written": n_tok, "chars": len(cand)})
            print("[lenmatch] candidate %r tokens=%s (control %s)"
                  % (cand, n_tok, ctrl_tokens), flush=True)
            if n_tok == ctrl_tokens:
                saved = eng.save(BLOCK_SEQ, lenmatch_path)
                lenm = {"chosen_text": cand, "tokens_written": n_tok,
                        "cells_after_encode": P.cell_scan(eng, BLOCK_SEQ)[0],
                        "block_text_lines": [cand if PLATE in ln else ln for ln in lines],
                        "path": lenmatch_path.replace(os.sep, "/"),
                        "block_sha256": sha_file(lenmatch_path), "bytes_saved": saved}
                break
        res["inputs"]["length_matched_control"] = {
            "candidates_tried": tried,
            "chosen": lenm,
            "same_cell_count_as_control": bool(lenm),
            "why": "deleting a sentence also shortens the block, so the deleted-sentence arm changes "
                   "two things at once; this arm keeps the length and changes only the words",
            "if_unavailable": "the length confound stays unsplit and the verdict must say so"}
        if not lenm:
            print("[lenmatch] no candidate matched %s tokens: the equal-length arm is UNAVAILABLE"
                  % ctrl_tokens, flush=True)

    # release the encode engine before any arm child starts: two engines at once is forbidden
    del leases, eng
    res["arms"].append(spawn_child(a, "product_block_control", prod_path, PRODUCT_BLOCK,
                                   "control: known-answer block, untouched"))

    # Third arm: re-encode the ORIGINAL text through the same write path. Without it the pair
    # differs in two ways at once -- content AND provenance (product block file vs fresh encode)
    # -- and a lost answer could be blamed on the encoding path instead of the deleted sentence.
    res["arms"].append(spawn_child(a, "reencoded_with_sentence", ctrl_path,
                               "blk_conv_platecontrol_attempt%d" % a.attempt,
                               "control 2: same text, same write path as the ablated arm"))

    res["arms"].append(spawn_child(a, "ablated_without_sentence", ab_path,
                              "blk_conv_plateablate_attempt%d" % a.attempt,
                              "ablation: same text minus the plate sentence"))

    if lenm:
        res["arms"].append(spawn_child(a, "length_matched_control", lenmatch_path,
                                       "blk_conv_platematch_attempt%d" % a.attempt,
                                       "control 3: same cell count and range, different words"))

    ctrl = res["arms"][0]
    reenc = res["arms"][1]
    ab = res["arms"][2]
    lenm_rec = res["arms"][3] if len(res["arms"]) > 3 else None
    res["comparison"] = {
        "question": QUESTION,
        "pos_asked": [ctrl["pos_asked"], ab["pos_asked"]],
        "same_position": ctrl["pos_asked"] == ab["pos_asked"],
        "same_question": True,
        "block_sha_changed": ctrl["block_sha256"] != ab["block_sha256"],
        "block_sha_note": "the pair cannot share a block sha: the ablation IS a different text, hence a different encoded block",
        "cells_loaded": [ctrl["cells_loaded"], ab["cells_loaded"]],
        "answers_plate": [ctrl["answers_plate"], reenc["answers_plate"], ab["answers_plate"]],
        # ONE source for the answer text: arms[*].answer_raw. Attempt 2's artifact carried an
        # empty arms[*].answer next to a populated side-by-side copy, i.e. the same arm with two
        # values under one name (#39 family). Here the pair restates answer_raw by reference.
        "answer_field": "arms[*].answer_raw (the only place an arm answer is stored)",
        "answers_side_by_side": [{"arm": ctrl["arm"], "answer_raw": ctrl["answer_raw"]},
                                 {"arm": reenc["arm"], "answer_raw": reenc["answer_raw"]},
                                 {"arm": ab["arm"], "answer_raw": ab["answer_raw"]}],
        "encoding_path_controlled": ctrl["answers_plate"] == reenc["answers_plate"],
        # the length confound, reported rather than argued about
        "length_matched": (None if lenm_rec is None else {
            "arm": lenm_rec["arm"], "cells": lenm_rec["cells_loaded"],
            "same_cells_as_control": lenm_rec["cells_loaded"] == ctrl["cells_loaded"],
            "same_attach_range": lenm_rec["attach_range"] == ctrl["attach_range"],
            "answers_plate": lenm_rec["answers_plate"],
            "answer_raw": lenm_rec["answer_raw"]}),
        "length_confound_note": "the deleted-sentence arm is 12 cells shorter and attaches 12 "
                                "positions later; the equal-length arm is what separates content "
                                "from length, and only when it actually ran",
    }
    if not ctrl["answers_plate"]:
        verdict = "inconclusive_control_failed"
        why = "the known-answer product block did not answer the plate, so neither arm is interpretable"
    elif not reenc["answers_plate"]:
        verdict = "inconclusive_encode_path_differs"
        why = ("the product block answered but the same text re-encoded through our write path did "
               "not, so the ablation pair differs in provenance as well as content")
    elif ab["answers_plate"]:
        verdict = "memory_does_not_depend_on_that_sentence"
        why = "with the plate sentence deleted the model still answered " + PLATE
    elif lenm_rec is None:
        verdict = "memory_carried_by_that_sentence"
        why = ("with the plate sentence deleted the model no longer answered " + PLATE +
               "; the length confound is NOT separated, because no equal-length arm ran")
    elif not lenm_rec["answers_plate"]:
        verdict = "memory_carried_by_that_sentence_content_not_length"
        why = ("both the deleted-sentence arm and the equal-length arm (same cells, same range, "
               "different plate words) failed, so the loss follows the CONTENT of that sentence, "
               "not the shorter block")
    else:
        verdict = "inconclusive_length_or_plate_shape"
        why = ("the equal-length arm still answered " + PLATE + ", so a same-length block whose "
               "plate words differ keeps the answer; content is not singled out")
    res["judgement"] = {"verdict": verdict, "why": why,
                        "direction_was_not_preselected": True}
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    res["secs"] = round(time.time() - t0, 1)

    out = a.out if os.path.isabs(a.out) else os.path.join(HERE, a.out)
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("[done] verdict=%s sha16=%s -> %s" % (verdict,
          hashlib.sha256(open(out, "rb").read()).hexdigest()[:16], out))
    return 0 if verdict != "inconclusive_control_failed" else 3


def sha_file_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    sys.exit(main())