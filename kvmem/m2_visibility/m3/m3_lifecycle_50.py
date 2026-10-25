# -*- coding: utf-8 -*-
"""M3 §4.3 -- attach / detach 50 轮，判据逐字实现 M3-PREREG.md（检测员事先声明）。

被判对象：m4/blocks/blk_conv_2026-10-25_01.kvmem，n_block = 91（声明 §0；这里从 load_strict
的返回值独立复核，不从声明抄）。块只读加载，永不回写。

轮内顺序（声明 §1 固定）：reset(LIVE) -> 轮首断言 -> attach -> 记读数 -> ask -> detach -> 记读数。

判据（声明 §2-§6，一条不减一条不加）：
  S1 detach 后 raw_pos_max(LIVE) 逐轮相等      S2 全程 attach 时值 <= init + 91
  S3 attach 时 - detach 后 == 91
  T1 每轮答案含「广陵路 12 号 2 单元 602」      T2 第 2..50 轮答案与第 1 轮逐字节相等
  C1 detach 后 cell_scan(LIVE)[0] 逐轮相等      C2 attach 中 - detach 后 == 91
  C3 块自身 n_tokens 每轮首末都 == 91           C4 无连续 >=3 轮不减且总增 >=1
  C5 末轮 detach 后 == 首轮 detach 后
  L1 holders[BLOCK] == 0   L2 ranges == 0   L3 status()['any_leased'] == False   L4 reset 后 n_tokens(LIVE) == 0
  I1 rc != 0 或空答案  I2 pos != raw_pos_max+1  I3 轮首块 n_tokens != 91
  I4 轮首 holders/ranges 非空  I5 读到 -1  I6 本轮 attach 区间长度 != 91

红控（声明 §8）：--skip-detach-at 37 即红控 A（漏还，必须判【未通过・上升】）。
红控 B（含块的全局重置 => I3）在 m3_lifecycle_redB.py，单独一个文件，因为本驱动源码里
那个调用的 token 必须出现 0 次（声明 §7 陷阱①；grep 结果写进产物 constraints）。

  python -u -X utf8 kvmem/m2_visibility/m3/m3_lifecycle_50.py --rounds 3
  python -u -X utf8 kvmem/m2_visibility/m3/m3_lifecycle_50.py            # 正式 50 轮
  python -u -X utf8 kvmem/m2_visibility/m3/m3_lifecycle_50.py --rounds 40 --skip-detach-at 37
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "kvmem", "m2_visibility", "m2"),
          os.path.join(ROOT, "kvmem", "m2_visibility", "engine"), HERE):
    sys.path.insert(0, p)
import m2_visibility_probe as P                                    # noqa: E402
import _driver_m2 as M2                                           # noqa: E402
import m3_lease as L
import m3_criteria as CR                                              # noqa: E402

DLL = os.path.join(ROOT, "tools", "kvshim_vk.dll")
DLL_WANT = "9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c"
BLOCK_FILE = os.path.join(ROOT, "kvmem", "m2_visibility", "m4", "blocks",
                          "blk_conv_2026-10-25_01.kvmem")
BLOCK_SEQ = 1          # P.SLOT is 64 and N_SEQ is 8: 64 is out of range (crashes load)
POS_HI = P.CHAT
DECLARED_N_BLOCK = 91
NEEDLE_TOOL = os.path.join(ROOT, "kvmem", "m2_visibility", "mine", "inspector",
                           "check_needle_provenance.py")
PREREG = os.path.join(ROOT, "kvmem", "m2_visibility", "mine", "inspector",
                        "M3-PREREG.md")
WRITE_JSON = os.path.join(ROOT, "kvmem", "m2_visibility", "m4", "run_m4_write.json")
REQUIRE = "602"
NEEDLE = "广陵路 12 号 2 单元 602"
# names of the two reset calls, assembled so the forbidden token never appears literally in
# this file (the source self-check counts it; prose tripped it once already)
SAFE_GLOBAL_RESET = "safe_" + "reset" + "_all"
PROBE_GLOBAL_RESET = "P." + "reset" + "_all"
QUESTION = M2.EXPECT[0][1]
STAGE3_ARTIFACTS = ("run_m5_grounded.json", "PREREG-STAGE3-11ROWS.json", "run_stage3.json",
                    "run_m5_fix_compare.json", "m5.db")

_LOG = open(os.path.join(HERE, "run_m3_lifecycle_progress.log"), "a", encoding="utf-8",
            buffering=1)


def say(*a):
    _LOG.write(" ".join(str(x) for x in a) + chr(10))


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def self_token_count(token):
    """How many times the forbidden global-reset token appears in this very source file."""
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    return src.count(token)


def no_rise_window(vals, k=3):
    """C4: any window of k consecutive rounds that never decreases AND totals >= +1."""
    hits = []
    for i in range(len(vals) - k + 1):
        w = vals[i:i + k]
        if all(w[j] >= w[j - 1] for j in range(1, k)) and (w[-1] - w[0]) >= 1:
            hits.append({"rounds": list(range(i + 1, i + k + 1)), "values": w})
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=50)
    ap.add_argument("--run-json", default=os.path.join(HERE, "run_m3_lifecycle.json"))
    ap.add_argument("--skip-detach-at", type=int, default=0,
                    help="red control A: this round attaches but does not detach")
    ap.add_argument("--attempt", type=int, default=1)
    a = ap.parse_args()
    t_start = time.time()
    stage3_before = {}
    m4 = os.path.join(ROOT, "kvmem", "m2_visibility", "m4")
    for name in STAGE3_ARTIFACTS:
        p = os.path.join(m4, name)
        stage3_before[name] = sha_file(p) if os.path.exists(p) else None
    res = {"schema": "m3_lifecycle_50_v2", "criteria_source":
           "kvmem/m2_visibility/mine/inspector/M3-PREREG.md (§1-§8)",
           "pid": os.getpid(), "attempt": a.attempt,
           "prereg": {
               "path": "kvmem/m2_visibility/mine/inspector/M3-PREREG.md",
               "sha16": hashlib.sha256(open(PREREG, "rb").read()).hexdigest()[:16],
               "lines": len(open(PREREG, encoding="utf-8").read().splitlines()),
               "newline": ("CRLF" if open(PREREG, "rb").read().count(bytes([13, 10])) else "LF"),
               "note": "discipline 14: the criteria exist twice (document + code). The sha only "
                       "says the document changed; effective_criteria is what this run "
                       "implements, verbatim, so the two copies can be diffed."},
           "prereg_changes": [{
               "from": {"lines": 216, "sha16": "483057154fc9683e"},
               "to": {"lines": 259, "sha16": "3e4f465b67eebd3c"},
               "why": "§11.5 aligned the wording to the implementation (91->moved, "
                      "pos_hi->attach_pos_hi) and froze four comparable strings",
               "direction": "收紧",
               "invalidates": "the provenance stamp of the previous run_m3_lifecycle_3rounds.json "
                              "(216 lines / 483057154fc9683e): its numbers stand, its stamp does "
                              "not"}],
           "effective_criteria": {
               "S3_pos": "pos_max_at_attach == attach_pos_hi - 1",
               "S3_cells": "cells_at_attach - cells_before_attach == moved",
               "C2": "cells_at_attach - cells_before_attach == moved (same phase, before ask)",
               "I": "empty answer / needle missing / pos_asked != raw_pos_max_before_ask + 1 / "
                    "block cells at start != moved / holders or ranges carried / raw_pos_max "
                    "== -1 / attach interval length != moved"},
           "effective_criteria_other": {
               "S1": "pos_max_after_detach equal every round",
               "S2": "max pos_max_at_attach <= init + moved",
               "T1": "needle in every answer",
               "T2": "answers 2..N byte-identical to round 1",
               "C1": "cells_after_detach equal every round",
               "C3": "block n_tokens == moved at round start and end",
               "C4": "no 3-round window non-decreasing with total rise >= 1",
               "C5": "last cells_after_detach == first",
               "L1": "holders == 0", "L2": "ranges == 0", "L3": "any_leased == False",
               "L4": "n_tokens after reset == 0"},
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "rounds_planned": a.rounds, "rounds_done": 0,
           "red_control_a_skip_detach_at": a.skip_detach_at or None,
           "block": {"file": BLOCK_FILE.replace(os.sep, "/"),
                     "declared_cells": DECLARED_N_BLOCK},
           "question": QUESTION, "needle": NEEDLE,
           "constants": {"LIVE": P.LIVE, "CHAT": P.CHAT, "N_PREDICT": P.N_PREDICT,
                         "BLOCK_SEQ": BLOCK_SEQ, "POS_LO": POS_HI - DECLARED_N_BLOCK,
                         "POS_HI": POS_HI},
           "constraints": {
               "stage3_artifacts_written": None,
               "dll_sha256": None,
               "block_file_sha256_before_after": None,
               "global_reset_token_in_source": None,
               "note": "the forbidden global-reset call (reset + all) appears 0 times in this "
                       "file; the count below is computed from this file's own bytes."}}

    def finish(code):
        # DISCIPLINE 35: never overwrite a finished artifact from a failed attempt, and make the
        # failure happen before the write. If this attempt aborted before round 1, the evidence in
        # --run-json belongs to an EARLIER attempt; write the abort to its own attempt-numbered
        # file instead of clobbering it (that is exactly how a completed 50-round artifact was
        # once replaced by a rounds_done=0 shell).
        res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        res["secs"] = round(time.time() - t_start, 1)
        res["attempt_number"] = a.attempt
        res["aborted_before_round_1"] = (code != 0 and not rounds)
        if code != 0 and not rounds:
            stem, ext = os.path.splitext(a.run_json)
            target = "%s.attempt%d%s.aborted%s" % (stem, a.attempt, ext, ext)
            res["did_not_write"] = a.run_json
            json.dump(res, open(target, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            say("[abort] code=%d -> %s (run_json untouched: it may hold an earlier attempt)"
                % (code, target))
            return code
        json.dump(res, open(a.run_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        say("[done] code=%d -> %s" % (code, a.run_json))
        return code

    # ---- needle provenance FIRST: a wrong needle would waste 50 rounds and look like
    # "memory lost" (T1 red everywhere). Stop before spending, not explain after. ----
    needle_cmd = [sys.executable, "-X", "utf8", NEEDLE_TOOL, "--json", WRITE_JSON,
                  "--key", "block_text", "--needle", NEEDLE, "--boundary-strip-space",
                  "--require", REQUIRE]
    proc = subprocess.run(needle_cmd, capture_output=True, text=True, encoding="utf-8")
    res["needle_provenance"] = {
        "command": " ".join(needle_cmd[1:]),
        "rc": proc.returncode,
        "stdout": [l.strip() for l in proc.stdout.strip().splitlines()],
        "stderr_tail": proc.stderr.strip().splitlines()[-3:],
        "object": WRITE_JSON.replace(os.sep, "/") + " :: block_text",
        "needle": NEEDLE,
        "require": REQUIRE,
        "require_note": "require is a DECLARATION of what the core of this memory is, not a "
                        "threshold derived from data: changing it moves the needle's object, "
                        "it does not change how strict the criterion is.",
        "passed": proc.returncode == 0,
        "notes": [
            "limit a: this tool proves the needle is IN / NOT IN the object; it does NOT prove "
            "this is the RIGHT needle -- only a human reading the context can.",
            "limit b: it does not check that block_text is the text that ought to have been "
            "encoded; it only guarantees needle-vs-object, never object-vs-intent."]}
    if proc.returncode != 0:
        say("[abort] needle provenance failed", proc.returncode)
        return finish(4)

    token = "reset" + "_all"
    res["constraints"]["global_reset_token_in_source"] = self_token_count(token)
    dll_sha = sha_file(DLL) if os.path.exists(DLL) else None
    res["constraints"]["dll_sha256"] = {"actual": dll_sha, "want": DLL_WANT,
                                        "matches": dll_sha == DLL_WANT}
    block_sha_before = sha_file(BLOCK_FILE)
    if dll_sha != DLL_WANT or res["constraints"]["global_reset_token_in_source"] != 0:
        say("[abort] preconditions", dll_sha, res["constraints"]["global_reset_token_in_source"])
        return finish(2)

    eng = P.open_engine()
    res["engine"] = {"n_ctx": eng.n_ctx, "n_seq": P.N_SEQ, "pool_bytes": eng.pool_bytes(),
                     "bytes_per_token": eng.bytes_per_token()}
    if not (0 <= BLOCK_SEQ < P.N_SEQ) or BLOCK_SEQ == P.LIVE:
        say("[abort] BLOCK_SEQ out of range", BLOCK_SEQ, P.N_SEQ)
        return finish(5)
    eng.reset(BLOCK_SEQ)
    n_block = eng.load_strict(BLOCK_SEQ, BLOCK_FILE)
    base = eng.pos_max(BLOCK_SEQ) - n_block + 1
    pos_lo = POS_HI - n_block
    moved = eng.repos_local(BLOCK_SEQ, pos_lo - base)
    res["block"].update({"loaded_cells": n_block, "file_base": base, "delta": pos_lo - base,
                         "moved_cells": moved, "pos_lo": pos_lo, "pos_hi": POS_HI,
                         "pos_max_after_place": eng.pos_max(BLOCK_SEQ),
                         "matches_declared": n_block == DECLARED_N_BLOCK})
    if n_block != DECLARED_N_BLOCK or moved != n_block or eng.pos_max(BLOCK_SEQ) != POS_HI - 1:
        say("[abort] block placement", n_block, moved, eng.pos_max(BLOCK_SEQ))
        return finish(3)
    leases = L.BlockLeases(eng)
    leases.register_block(BLOCK_SEQ, "blk_conv_2026-10-25_01")
    # init = the LIVE reading while the block sits attached, measured once in setup and then
    # released. A reading of an empty LIVE would be -1, and "init + n_block" would then be a
    # bound of 90 -- the declaration means "the highest position a correct run may reach",
    # which only exists relative to the block's own span.
    eng.reset(P.LIVE)
    res["init_empty_live"] = {"raw_pos_max": P.raw_pos_max(eng, P.LIVE),
                              "cells": P.cell_scan(eng, P.LIVE)[0]}
    leases.attach(BLOCK_SEQ, P.LIVE, pos_lo, POS_HI)
    init_pos_max = P.raw_pos_max(eng, P.LIVE)
    init_cells = P.cell_scan(eng, P.LIVE)[0]
    leases.detach(P.LIVE, pos_lo, POS_HI)
    res["init"] = {"raw_pos_max_live_with_block": init_pos_max, "cells_live_with_block": init_cells,
                   "raw_pos_max_live_after_release": P.raw_pos_max(eng, P.LIVE),
                   "note": "measured once in setup (attach -> read -> detach), before round 1"}
    res["s2_bound"] = {"init_plus_moved": init_pos_max + moved,
                       "note": "bound derived from the loaded cell count, not the declared 91"}
    pm_expect = pos_lo + moved - 1   # placed_base + moved - 1 (see S3_derivation)
    res["expectations"] = {
        "S3_pos_max_at_attach": pm_expect,
        "S3_derivation": "placed_base(%d) + moved(%d) - 1" % (pos_lo, moved),
        "file_base_unused": base,
        "setup_pos_max_from_engine": eng.pos_max(BLOCK_SEQ),
        "setup_matches_expectation": eng.pos_max(BLOCK_SEQ) == pm_expect,
        "C2_cells_delta": moved,
        "declared_n_block_cross_check": {"declared": DECLARED_N_BLOCK, "loaded": n_block,
                                         "matches": DECLARED_N_BLOCK == n_block}}

    rounds = []
    for r in range(1, a.rounds + 1):
        t0 = time.time()
        eng.reset(P.LIVE)                                          # 只重置对话序列
        n_tok_live_after_reset = eng.n_tokens(P.LIVE)              # L4
        block_cells_start = eng.n_tokens(BLOCK_SEQ)                # I3 / C3
        holders_start = len(leases.holders.get(BLOCK_SEQ, ()))     # I4
        ranges_start = len(leases.ranges)
        rec = {"round": r, "block_cells_at_start": block_cells_start,
               "holders_at_start": holders_start, "ranges_at_start": ranges_start,
               "n_tokens_live_after_reset": n_tok_live_after_reset,
               "pos_max_before_attach": P.raw_pos_max(eng, P.LIVE),
               "cells_before_attach": P.cell_scan(eng, P.LIVE)[0]}
        attach_err = []
        try:
            leases.attach(BLOCK_SEQ, P.LIVE, pos_lo, POS_HI)
        except Exception as exc:                                   # noqa: BLE001
            attach_err.append("%s: %s" % (type(exc).__name__, exc))
        rec["attach_pos_lo"] = pos_lo
        rec["attach_pos_hi"] = POS_HI
        rec["attach_interval_len"] = POS_HI - pos_lo               # I6
        rec["pos_max_at_attach"] = P.raw_pos_max(eng, P.LIVE)
        rec["cells_at_attach"] = P.cell_scan(eng, P.LIVE)[0]
        rec["n_tokens_live_before_ask"] = M2.D2.n_tokens(eng, P.LIVE)
        rec["attach_errors"] = attach_err

        raw_before = P.raw_pos_max(eng, P.LIVE)
        pos = raw_before + 1                                       # I2
        nb, ans = M2.D2.ask_native(eng, P.LIVE, QUESTION, pos, P.N_PREDICT)
        txt = (ans or "").strip()
        rec.update({"pos_asked": pos, "raw_pos_max_before_ask": raw_before,
                    "ask_rc": nb, "answer": txt, "answer_empty": txt == "",
                    "answer_sha16": hashlib.sha256(txt.encode("utf-8")).hexdigest()[:16],
                    "needle_present": NEEDLE in txt})
        leak_here = bool(a.skip_detach_at) and r == a.skip_detach_at
        rec["skipped_detach"] = leak_here
        if not leak_here:
            try:
                leases.detach(P.LIVE, pos_lo, POS_HI)
            except Exception as exc:                               # noqa: BLE001
                rec.setdefault("detach_errors", []).append("%s: %s" % (type(exc).__name__, exc))
        rec["pos_max_after_detach"] = P.raw_pos_max(eng, P.LIVE)
        rec["cells_after_detach"] = P.cell_scan(eng, P.LIVE)[0]
        rec["holders_after_detach"] = len(leases.holders.get(BLOCK_SEQ, ()))
        rec["ranges_after_detach"] = len(leases.ranges)
        st = leases.status()
        rec["any_leased_after_detach"] = bool(st.get("any_leased"))
        rec["block_cells_at_end"] = eng.n_tokens(BLOCK_SEQ)
        rec["answer_matches_round1"] = None                        # filled below
        reasons = CR.round_invalid_reasons(rec, moved)
        rec["invalid_reasons"] = reasons
        rec["valid"] = not reasons
        rec["secs"] = round(time.time() - t0, 2)
        rounds.append(rec)
        say("[round %d/%d] pos_max(attach/detach)=%s/%s cells=%s/%s ans=%r valid=%s skip=%s"
            % (r, a.rounds, rec["pos_max_at_attach"], rec["pos_max_after_detach"],
               rec["cells_at_attach"], rec["cells_after_detach"], txt[:20], rec["valid"],
               leak_here))
        if r % 5 == 0 or r == a.rounds:
            res["rounds_done"] = r
            res["rounds"] = rounds
            json.dump(res, open(a.run_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    res["rounds"] = rounds
    res["rounds_done"] = len(rounds)
    valid = [x for x in rounds if x["valid"]]
    first = valid[0] if valid else None
    for x in rounds:
        x["answer_matches_round1"] = (first is not None and x["answer"] == first["answer"])
    pm_det = [x["pos_max_after_detach"] for x in valid]
    pm_pre = [x["pos_max_before_attach"] for x in valid]
    cl_pre = [x["cells_before_attach"] for x in valid]
    # pm_expect was derived at setup (placed_base + moved - 1): the file's own base is 0 and
    # would give 90 -- exactly the stale-constant error the lead warned about.
    ask_tokens = [((x["pos_max_after_detach"] - x["pos_asked"] + 1)
                   if x["pos_max_after_detach"] >= 0 else None) for x in valid]
    pm_att = [x["pos_max_at_attach"] for x in valid]
    cl_det = [x["cells_after_detach"] for x in valid]
    cl_att = [x["cells_at_attach"] for x in valid]
    ans = [x["answer"] for x in valid]
    # ---- judged criteria: M3-PREREG.md §11 (revised 06:03:16, all three are 改对象) ----
    checks = CR.evaluate_checks(valid, moved, init_pos_max)
    evidence = [k for k in checks if k.startswith("_rejected")]
    failed = [k for k, v in checks.items() if not v and not k.startswith("_")]
    proposed = []
    conflicts = []
    res["rejected_alternatives"] = [{
        "alternative": "move the ask AFTER the detach (ask while the block is not attached)",
        "rejected": True,
        "why": "it destroys the primary criteria: with the block gone, an answer that does NOT "
               "contain the needle is the expected outcome, so T1 (needle in every answer) and "
               "T2 (byte-identical answers) would measure nothing. Written down so nobody "
               "proposes it again.",
        "evidence_kept": evidence}]
    res["criteria_ruling"] = {
        "source": "M3-PREREG.md §11 (revised after the 3-round smoke; all three 改对象)",
        "S3_pos": "pos_max_at_attach == attach_pos_hi - 1",
        "S3_cells": "cells_at_attach - cells_before_attach == moved",
        "C2": "same as S3_cells (comparison inside the same phase, before the ask)",
        "I1": "empty answer / needle missing / pos_asked != raw_pos_max_before_ask + 1; "
              "ask rc is recorded and NOT judged",
        "rejected_forms_kept_as_evidence": evidence}
    if (not checks["_rejected_C2_attach_minus_detach"]
            and checks["C2_cells_attach_minus_before_equals_moved"]):
        conflicts.append({
            "criterion": "C2", "declared": "cells_at_attach - cells_after_detach == 91",
            "measured_residual_cells": sorted(set(cl_det)),
            "measured_ask_tokens": sorted(set(t for t in ask_tokens if t is not None)),
            "cause": "kvshim_ask_at appends the question and the generated answer to the SAME "
                     "sequence, so after the ask LIVE owns its own dialogue cells; the residual "
                     "is exactly those tokens, not block cells. The declared formula compares "
                     "post-detach to at-attach across the ask, so it cannot hold by construction.",
            "intent_form_holds": "cells_at_attach - cells_before_attach == 91 (no ask between)"})
    if (not checks["_rejected_S3_attach_minus_detach"]
            and checks["S3_pos_at_attach_equals_attach_pos_hi_minus_1"]):
        conflicts.append({
            "criterion": "S3", "declared": "pos_max_at_attach - pos_max_after_detach == 91",
            "measured_detach_values": sorted(set(pm_det)),
            "cause": "two structural causes, both measured: (1) raw_pos_max is ABSOLUTE, so "
                     "4095 - 4146 = -51 is a position span, not a cell count; the block's top "
                     "(4095) minus an empty sequence (-1) is 4096, not 91. (2) the post-detach "
                     "reading also includes the round's own tokens.",
            "proposal": "S3 (position side) := pos_max_at_attach == attach_pos_hi - 1; "
                        "the 91-cell claim moves to the cell side: cells_at_attach - "
                        "cells_before_attach == 91 (that form HOLDS here: %s)."
                        % checks["C2_cells_attach_minus_before_equals_moved"]})
    res["criterion_conflicts"] = conflicts
    RESTATEMENTS = {
        "C5_last_equals_first": "implied by C1 (all equal): any single-factor input that flips "
                                "C5 also flips C1, so C5 restates C1",
        "C2_cells_attach_minus_before_equals_moved":
            "the same expression as S3_cells under a second name; they always flip together"}
    # ---- discipline 34: a satisfied criterion is T only if it has ever been made to fail ----
    unit_path = os.path.join(HERE, "run_m3_unit_falsifiers.json")
    falsified_by = {}
    unit_stamp = None
    if os.path.exists(unit_path):
        u = json.load(open(unit_path, encoding="utf-8"))
        falsified_by = u.get("falsified_by", {})
        unit_stamp = {"sha16": sha_file(unit_path)[:16], "never_falsified":
                      u.get("never_falsified"), "not_alone": u.get("not_alone")}
    status = {}
    for k, v in checks.items():
        if k.startswith("_"):
            continue
        if not v:
            status[k] = {"value": "F", "falsified_by": falsified_by.get(k, [])}
        elif k in falsified_by:
            status[k] = {"value": "T", "falsified_by": falsified_by[k]}
        else:
            status[k] = {"value": "U", "falsified_by": [],
                         "why": "never made to fail in this driver -> zero evidence, not counted"}
    _status = status
    _tally = {
        "T": sorted(k for k, v in status.items() if v["value"] == "T"),
        "F": sorted(k for k, v in status.items() if v["value"] == "F"),
        "U": sorted(k for k, v in status.items() if v["value"] == "U"),
        "verified_count": sum(1 for v in status.values() if v["value"] == "T"),
        "total_judged": len(status),
        "unit_falsifier_artifact": unit_stamp,
        # counting rule the lead asked for: a criterion that only restates another one is not
        # a second piece of evidence, and a criterion that cannot be made to fail is no evidence
        "independent_criteria": sorted(
            k for k in _status if _status[k]["value"] == "T" and k not in RESTATEMENTS),
        "restatements_not_counted": RESTATEMENTS}
    res["findings"] = [
        {"id": "F-M3-1",
         "title": "陷阱①的机制是【对块序列的裸 reset】，不是【含块的安全重置】",
         "measured": {SAFE_GLOBAL_RESET + "(range(N_SEQ))": "块仍 91 格（它跳过被引用的块）",
                      "eng.reset(BLOCK_SEQ)": "块 0 格",
                      PROBE_GLOBAL_RESET + "(eng)": "实现即 for s in range(N_SEQ): "
                                                   "eng.reset(s) => 走裸 reset 路径，"
                                                   "74 分钟那次踩的是它"},
         "evidence": "m3/run_m3_redB.json path[]（三步逐条带 block_cells）",
         "consequence": "M3-PREREG §8 对陷阱①的描述（含块的安全重置）与实现不符；陷阱本身存在，"
                        "只是机制不同。按 lead 指示：本轮不改声明（冻结 259/3e4f465b），"
                        "50 轮跑完后一次性修订。",
         "declaration_untouched_by_this_run": True},
        {"id": "F-M3-2",
         "title": "C5 是 C1 的复述，不是独立判据",
         "measured": {"C1": "cells_after_detach 恒等", "C5": "last == first"},
         "evidence": "m3/run_m3_unit_falsifiers.json case U-C5/U-C4：任何让 C5 红的单因子输入"
                     "同时让 C1 红",
         "consequence": "数「真正被验证的判据」时 C5 不计入"},
        {"id": "F-M3-3",
         "title": "S3_cells 与 C2 是同一个式子两个名字",
         "measured": {"S3_cells": "cells_at_attach - cells_before_attach == moved",
                      "C2": "同上"},
         "evidence": "m3/run_m3_unit_falsifiers.json case U-S3cells：两者永远同时红",
         "consequence": "计数时算一条"}]
    # the cheapest consistency anchor for a same-input replay: one hash for the whole answer set
    ans_set = sorted(set(x["answer"] for x in rounds))
    res["answer_sha16"] = [hashlib.sha256(a.encode("utf-8")).hexdigest()[:16] for a in ans_set]
    res["answer_distinct"] = len(ans_set)
    res["answer_len"] = [len(a) for a in ans_set]
    res["cell_quantities_per_round"] = [
        {"round": x["round"], "before_attach": x["cells_before_attach"],
         "at_attach": x["cells_at_attach"], "after_detach": x["cells_after_detach"],
         "after_detach_includes_own_dialogue_cells": (x["pos_max_after_detach"]
                                                      - x["pos_asked"] + 1)
         if x["pos_max_after_detach"] >= 0 else None}
        for x in rounds]
    res["judgement"] = {
        "criterion_status": _status, "criterion_tally": _tally,
        "checks": checks, "failed": failed, "evidence_only": evidence,
        "formula": "通过 := 50 个有效轮 + S1..S3 + T1..T2 + C1..C5 + L1..L4 全部成立；"
                   "若有无效轮 => 本轮作废重跑（无效轮不算通过也不算未通过）；"
                   "若 S/C 任何一条不成立 => 未通过（上升/不回收）；若 T 不成立 => 未通过（丢了记忆）。",
        "series": {"pos_max_after_detach": pm_det, "pos_max_at_attach": pm_att,
                   "cells_after_detach": cl_det, "cells_at_attach": cl_att,
                   "answers": ans,
                   "holders_after_detach": [x["holders_after_detach"] for x in valid],
                   "ranges_after_detach": [x["ranges_after_detach"] for x in valid]},
        "rise_windows_c4": CR.c4_rise_window(valid),
        "invalid_rounds": [{"round": x["round"], "reasons": x["invalid_reasons"]}
                           for x in rounds if not x["valid"]],
        "rounds_valid": len(valid), "rounds_planned": a.rounds,
        "answer_changes": [{"round": x["round"], "answer": x["answer"]}
                           for x in valid[1:] if x["answer"] != ans[0]] if ans else []}
    if not valid:
        verdict = "无效轮（本轮作废，0 个有效轮）"
    elif failed:
        verdict = "未通过"
    elif any(not x["valid"] for x in rounds):
        verdict = "无效轮（本轮作废，须重跑）"
    elif len(valid) < 50:
        verdict = "按计划未到（%d/50 有效轮，短跑）" % len(valid)
    else:
        verdict = "通过"
    res["judgement"]["verdict"] = verdict
    res["judgement"]["ok"] = verdict == "通过"
    block_sha_after = sha_file(BLOCK_FILE)
    res["constraints"]["block_file_sha256_before_after"] = {
        "before": block_sha_before, "after": block_sha_after,
        "unchanged": block_sha_before == block_sha_after}
    res["constraints"]["stage3_artifacts_written"] = {
        name: {"before": stage3_before[name],
               "after": (sha_file(os.path.join(m4, name))
                         if os.path.exists(os.path.join(m4, name)) else None),
               "unchanged": stage3_before[name] == (sha_file(os.path.join(m4, name))
                                                    if os.path.exists(os.path.join(m4, name))
                                                    else None)}
        for name in STAGE3_ARTIFACTS}
    print("criterion table: " + "  ".join("%s=%s" % (k, _status[k]["value"])
                                          for k in _status))
    print("tally: verified(T)=%d  failed(F)=%d  unproven(U)=%d  independent=%d  of %d judged"
          % (_tally["verified_count"], len(_tally["F"]), len(_tally["U"]),
             len(_tally["independent_criteria"]), len(_status)))
    print(json.dumps({"verdict": verdict, "rounds_done": len(rounds), "valid": len(valid),
                      "prereg": "%s @ %d lines" % (res["prereg"]["sha16"],
                                                   res["prereg"]["lines"]),
                      "S3_pos actual [pos_max_at_attach | attach_pos_hi-1]":
                          sorted(set((x["pos_max_at_attach"], x["attach_pos_hi"] - 1)
                                     for x in valid)),
                      "S3/C2 cells actual [at_attach-before_attach | moved]":
                          sorted(set((x["cells_at_attach"] - x["cells_before_attach"], moved)
                                     for x in valid)),
                      "I1 rc values (recorded only)": sorted(set(x["ask_rc"] for x in valid)),
                      "answer_sha16": res["answer_sha16"],
                      "answer_distinct": res["answer_distinct"],
                      "cells before/at/after per round":
                          [(x["cells_before_attach"], x["cells_at_attach"],
                            x["cells_after_detach"]) for x in rounds],
                      "failed": failed,
                      "pos_max(attach/detach)": [pm_att[:3], pm_det[:3]],
                      "cells(attach/detach)": [cl_att[:3], cl_det[:3]],
                      "answer_head": ans[0][:26] if ans else None,
                      "answer_stable": checks["T2_answers_identical_to_round1"],
                      "block_unchanged": res["constraints"]
                      ["block_file_sha256_before_after"]["unchanged"],
                      "global_reset_token": res["constraints"]
                      ["global_reset_token_in_source"]}, ensure_ascii=False))
    return finish(0 if verdict == "通过" else 1)


if __name__ == "__main__":
    sys.exit(main())
