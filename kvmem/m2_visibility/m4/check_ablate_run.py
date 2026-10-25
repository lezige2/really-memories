# -*- coding: utf-8 -*-
# Read-only verifier for an ablation artifact. Prints the cells a reviewer checks, with the value
# next to each one, and treats a null reading as UNVERIFIED rather than as a pass.
#
#   python -u -X utf8 check_ablate_run.py run_m4_ablate_plate_a6.json
#
# This program grades an artifact produced by another program, so what it prints is an R, not the
# script grading itself (contrast run_outfilter_selftest.json, which is graded_by: self).
import json, sys

def val(d, *path, default="<absent>"):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

def main(argv):
    if len(argv) < 2:
        print("usage: check_ablate_run.py <artifact.json>")
        return 2
    d = json.load(open(argv[1], encoding="utf-8"))
    arms = d.get("arms") or []
    by = {a.get("arm"): a for a in arms}
    cells = []

    def cell(name, value, ok, note=""):
        cells.append({"cell": name, "value": value, "ok": ok, "note": note})

    nps = [(a.get("arm"), a.get("n_predict"), a.get("n_predict_consistent", "<absent>")) for a in arms]
    consistent = [c for _, _, c in nps]
    # Tri-state, and the target is read from the artifact itself (it declares what it asked the
    # engine for: top-level n_predict, else engine.n_predict). No literal here: 24 was the old
    # ruler, 64 is a7's declared value, and neither belongs in the grader.
    declared = d.get("n_predict")
    if declared is None:
        declared = val(d, "engine", "n_predict", default=None)
    if all(c == "<absent>" for c in consistent):
        cell("n_predict", nps, None, "field absent: this artifact predates the n_predict fix")
    elif declared is None or declared == "<absent>":
        cell("n_predict", nps, None,
             "artifact declares no n_predict (top-level or engine.*) = UNVERIFIED")
    else:
        mism = [(arm, np_) for arm, np_, _ in nps if np_ != declared]
        if mism:
            cell("n_predict", nps, False,
                 "arm n_predict != declared %s: %s" % (declared, mism))
        elif any(c is None for c in consistent):
            cell("n_predict", nps, None,
                 "declared %s; engine exposes no n_predict attribute = UNVERIFIED" % declared)
        else:
            cell("n_predict", nps, True, "consistent with declared %s" % declared)

    spans = [(a.get("arm"), a.get("cells_span_matches_attach_range", "<absent>")) for a in arms]
    if all(s == "<absent>" for _, s in spans):
        cell("cells_span_matches_attach_range", spans, None, "field absent (pre-fix artifact)")
    else:
        ok = all(s is True or s is None for _, s in spans)
        cell("cells_span_matches_attach_range", spans, ok,
             "None = --no-repos run, where the span is deliberately not asserted")

    pmax = [(a.get("arm"), a.get("raw_pos_max_block_after_attach")) for a in arms]
    ok = all(v == 4095 for _, v in pmax)
    cell("raw_pos_max_block_after_attach", pmax, ok, "must be 4095 once the cells are repositioned")

    plate = [(a.get("arm"), a.get("answers_plate")) for a in arms]
    ctrl_ok = bool(val(by.get("product_block_control") or {}, "answers_plate", default=False))
    reenc_ok = bool(val(by.get("reencoded_with_sentence") or {}, "answers_plate", default=False))
    cell("controls_answer_plate", plate, ctrl_ok and reenc_ok,
         "if either control fails the run is inconclusive, whatever the ablation arms say")

    why = val(d, "judgement", "why", default="")
    has_lenmatch = "length_matched_control" in by
    if has_lenmatch:
        cell("confound_note", why, True, "equal-length arm ran, so the verdict may name content")
    else:
        ok = "confound is NOT separated" in why
        cell("confound_note", why, ok,
             "without the equal-length arm the verdict must say the confound is unsplit")

    print("artifact : %s" % argv[1])
    print("verdict  : %s" % val(d, "judgement", "verdict"))
    for c in cells:
        flag = "OK  " if c["ok"] is True else ("SKIP" if c["ok"] is None else "FAIL")
        print("[%s] %-32s %s" % (flag, c["cell"], c["value"]))
        if c["note"]:
            print("       %s" % c["note"])
    hard_fail = [c for c in cells if c["ok"] is False]
    skipped = [c for c in cells if c["ok"] is None]
    print("graded_by: external (this program read the artifact; the artifact did not grade itself)")
    print("RESULT: %s (%d failed, %d unverified)" % ("PASS" if not hard_fail else "FAIL",
                                                    len(hard_fail), len(skipped)))
    return 0 if not hard_fail else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))