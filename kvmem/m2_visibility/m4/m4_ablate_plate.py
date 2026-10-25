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
N_PREDICT = 24
QUESTION = "我的车牌号是多少？"
PLATE = "浙B-3F19K"
PRODUCT_BLOCK = "blk_conv_2026-10-25_01"


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha16(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def ask_arm(eng, leases, name, path, block_id, role):
    """reset -> register -> load -> attach at the same rule -> ask at the same position."""
    leases.register_block(BLOCK_SEQ, block_id)
    reset_info = leases.safe_reset_all(range(P.N_SEQ))
    moved = eng.load_strict(BLOCK_SEQ, path)
    cells = P.cell_scan(eng, BLOCK_SEQ)[0]
    lo, hi = POS_HI - moved, POS_HI
    pos_max_at_attach = P.raw_pos_max(eng, BLOCK_SEQ)
    leases.attach(BLOCK_SEQ, LIVE, lo, hi)
    pos = P.raw_pos_max(eng, LIVE) + 1
    nb, ans = M2.D2.ask_native(eng, LIVE, QUESTION, pos, N_PREDICT)
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
           "attach_rule": "lo = POS_HI - moved; hi = POS_HI",
           "attach_range": [lo, hi], "pos_max_at_attach": pos_max_at_attach,
           "pos_asked": pos, "n_predict": N_PREDICT, "ask_bytes": nb,
           "answer_raw": txt, "answer_len": len(txt),
           "answer_delivered": delivered,
           "output_filter": {"per_tag": f["per_tag"],
                             "tag_chars_removed": f["tag_chars_removed"],
                             "raw_to_delivered_delta": len(txt) - len(delivered),
                             "delivered_has_tag": OUT.scan(delivered)["total"]},
           "assertion": assertion,
           "answers_plate": PLATE in txt,
           "reset_info": reset_info}
    # READ, not guessed: m3_lease.py:78 is "def detach(self, dst_seq, lo, hi)" -- the block seq
    # is recovered from the range table inside, so passing it here is a TypeError. That is how
    # attempt 1 died after arm 1 had already asked its question.
    leases.detach(LIVE, lo, hi)
    print("[arm %-22s] cells=%s range=[%s,%s) pos=%s bytes=%s answers_plate=%s ans=%r"
          % (name, moved, lo, hi, pos, nb, rec["answers_plate"], txt[:40]), flush=True)
    return rec


def selfcheck():
    """No engine, no model: bind every call this driver makes against the REAL signatures.

    Attempt 1 died at run time on BlockLeases.detach(LIVE, lo, hi) being called with an extra
    argument -- a mistake that costs nothing to find offline and costs a model load to find
    online. Everything that can be撞 without the engine must be撞 without the engine.
    """
    import inspect
    import tempfile
    problems = []
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

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".kvmem")
    tmp.write(b"x" * 16)
    tmp.close()
    real = (P.cell_scan, P.raw_pos_max, M2.D2.ask_native)
    try:
        P.cell_scan = lambda eng, seq: (91, list(range(91)))
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
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    t0 = time.time()

    src = json.load(open(os.path.join(HERE, a.write_run), encoding="utf-8"))
    text = src["block_text"]
    prod_path = os.path.join(a.blocks, PRODUCT_BLOCK + ".kvmem")
    ab_path = os.path.join(a.blocks, "blk_conv_plateablate_attempt%d.kvmem" % a.attempt)
    if os.path.exists(ab_path):
        raise SystemExit("refusing to overwrite the ablated block from an earlier attempt: " + ab_path)

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
               "block_text_lines": len(lines),
               "ablated_sha256": sha_file_hex(ablated), "ablated_len": len(ablated),
               "ablated_lines": len(kept),
               "removed_lines": removed, "removed_lines_count": len(removed),
               "plate_absent_from_ablated": PLATE not in ablated,
               "only_removal_check": {"chars_removed": len(text) - len(ablated),
                                     "expected": sum(len(x) + 1 for x in removed),
                                     "other_lines_identical": kept == [ln for ln in lines if ln not in removed]},
               "product_block_path": prod_path.replace(os.sep, "/"),
               "product_block_sha256": sha_file(prod_path),
               "ablated_block_path": ab_path.replace(os.sep, "/"),
               "ablated_block_is_new": True,
               "product_block_untouched": "loaded read-only; the block file is never written here",
           },
           "arms": []}

    eng = P.open_engine()
    leases = L.BlockLeases(eng)
    res["engine"] = {"dll_sha256": sha_file(os.path.join(ROOT, "tools", "kvshim_vk.dll")),
                     "n_seq": P.N_SEQ, "n_predict": N_PREDICT}

    res["arms"].append(ask_arm(eng, leases, "product_block_control", prod_path,
                              PRODUCT_BLOCK, "control: known-answer block, untouched"))

    # Third arm: re-encode the ORIGINAL text through the same write path. Without it the pair
    # differs in two ways at once -- content AND provenance (product block file vs fresh encode)
    # -- and a lost answer could be blamed on the encoding path instead of the deleted sentence.
    ctrl_path = os.path.join(a.blocks, "blk_conv_platecontrol_attempt%d.kvmem" % a.attempt)
    if os.path.exists(ctrl_path):
        raise SystemExit("refusing to overwrite an earlier attempt: " + ctrl_path)
    leases.register_block(BLOCK_SEQ, "blk_conv_platecontrol_attempt%d" % a.attempt)
    leases.safe_reset_all(range(P.N_SEQ))
    n_ctrl = eng.write_at(BLOCK_SEQ, text, 0)
    res["inputs"]["reencoded_encode"] = {"tokens_written": n_ctrl,
                                         "bytes_saved": eng.save(BLOCK_SEQ, ctrl_path),
                                         "block_sha256": sha_file(ctrl_path),
                                         "path": ctrl_path.replace(os.sep, "/")}
    print("[encode] re-encoded control: %d tokens -> %s" % (n_ctrl, ctrl_path), flush=True)
    res["arms"].append(ask_arm(eng, leases, "reencoded_with_sentence", ctrl_path,
                               "blk_conv_platecontrol_attempt%d" % a.attempt,
                               "control 2: same text, same write path as the ablated arm"))
    leases.register_block(BLOCK_SEQ, "blk_conv_plateablate_attempt%d" % a.attempt)
    leases.safe_reset_all(range(P.N_SEQ))
    n_ab = eng.write_at(BLOCK_SEQ, ablated, 0)
    written = eng.save(BLOCK_SEQ, ab_path)
    res["inputs"]["ablated_encode"] = {"tokens_written": n_ab, "bytes_saved": written,
                                       "block_sha256": sha_file(ab_path)}
    print("[encode] ablated block: %d tokens -> %s" % (n_ab, ab_path), flush=True)
    res["arms"].append(ask_arm(eng, leases, "ablated_without_sentence", ab_path,
                              "blk_conv_plateablate_attempt%d" % a.attempt,
                              "ablation: same text minus the plate sentence"))

    ctrl = res["arms"][0]
    reenc = res["arms"][1]
    ab = res["arms"][2]
    res["comparison"] = {
        "question": QUESTION,
        "pos_asked": [ctrl["pos_asked"], ab["pos_asked"]],
        "same_position": ctrl["pos_asked"] == ab["pos_asked"],
        "same_question": True,
        "block_sha_changed": ctrl["block_sha256"] != ab["block_sha256"],
        "block_sha_note": "the pair cannot share a block sha: the ablation IS a different text, hence a different encoded block",
        "cells_loaded": [ctrl["cells_loaded"], ab["cells_loaded"]],
        "answers_plate": [ctrl["answers_plate"], reenc["answers_plate"], ab["answers_plate"]],
        "answers_side_by_side": [{"arm": ctrl["arm"], "answer": ctrl["answer_raw"]},
                                 {"arm": reenc["arm"], "answer": reenc["answer_raw"]},
                                 {"arm": ab["arm"], "answer": ab["answer_raw"]}],
        "encoding_path_controlled": ctrl["answers_plate"] == reenc["answers_plate"],
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
    else:
        verdict = "memory_carried_by_that_sentence"
        why = "with the plate sentence deleted the model no longer answered " + PLATE
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