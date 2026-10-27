#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""b7' S4 extract-merge verifier v2 (CPU-only, read-only inputs).

Structural checks (RULING-M5C2-B7-EXTRACT-RESUME R2/R3):
  * SENTS pin/count/sids
  * EXTRACT schema/records: 623 unique sids, exactly the SENTS set, SENTS order
  * shard1+shard2 raw: schema, sid sets disjoint, union == full set
  * resume_provenance fields: shard sha16/bytes/n_sids, sids lists, overlap=0, missing=0
  * pins: GEN/SENTS/prompt/model/dll/n_predict match frozen values
  * no '--allow-gui-procs' / 'allow_gui_procs' trace in EXTRACT or shard raws
  * optional: EXTRACT.gate_before is a strict gate (only lone dwm exception)

Evidence checks required by RULING-M5C2-B7-EXTRACT-RESUME-A2 (E):
  * C1: INVARIANCE20 (pin, pass, n=20, seed, negative rc, 10 pin assertions,
        comparison sids subset of shard1, raw byte-identical, shard1 forward count)
  * C2: layer0 = 42 records, route abstain_check, items=[], verdict abstain_ok,
        42 = shard1 19 + shard2 23 (by sid sets), 581+42=623
  * C3: run log exit 3 / timeout >3600s / timeout_mid; resume log success;
        signals_sent=false; gate_before.boot_id == gate_after.boot_id;
        EXTRACT-NOTES C3 graceful/no WATCHDOG-Minidump; out/ has no watchdog/minidump file

Exit codes: 0 pass, 1 assertion failure, 2 bad/missing core input.
Output: --out (default out/M5C2-B7-MERGE-CHECK.json), atomic tmp+os.replace.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import stat
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
OUT = ROOT / "kvmem/m2_visibility/m5/out"
DEFAULTS = {
    "gen_sha16": "041b51eb7837aa90", "gen_bytes": 140514,
    "sents_sha16": "c5a49a696b66f0c7", "sents_bytes": 288805,
    "prompt_sha16": "a6bc4f268f7711de",
    "model_bytes": 8988110240,
    "dll_sha16": "9edbafa150700614",
    "n_predict": 384,
    "n_sids": 623,
    "invariance_sha16": "a1d928df8affc5aa", "invariance_bytes": 8549,
    "provenance_sha16": "96cd4bfe8df05185", "provenance_bytes": 13992,
    "notes_sha16": "73118d5da940c506", "notes_bytes": 3804,
    "supersedes": "6aceb95c32697acd",
}


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def read_json(path):
    b = Path(path).read_bytes()
    return json.loads(b.decode("utf-8")), b


def load_optional(path):
    """Return (data, raw, error_string). Missing/bad => data=None, err set."""
    try:
        b = Path(path).read_bytes()
        return json.loads(b.decode("utf-8")), b, None
    except Exception as e:  # noqa: BLE001
        return None, None, repr(e)


def parse_log_with_exit(path):
    """Parse a log that is a JSON object optionally followed by 'EXIT=<n>'."""
    try:
        b = Path(path).read_bytes()
    except Exception:  # noqa: BLE001
        return None, None, None
    t = b.decode("utf-8", "replace").strip()
    m = re.search(r"\nEXIT=(-?\d+)\s*$", t)
    exit_code = int(m.group(1)) if m else None
    body = t[:m.start()] if m else t
    try:
        data = json.loads(body)
    except Exception:  # noqa: BLE001
        data = None
    return data, b, exit_code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", required=True)
    ap.add_argument("--sents", required=True)
    ap.add_argument("--shard1", required=True)
    ap.add_argument("--shard2", required=True)
    ap.add_argument("--out", default=str(OUT / "M5C2-B7-MERGE-CHECK.json"))
    ap.add_argument("--force-overwrite-readonly", action="store_true",
                    help="clear the read-only bit on --out before atomic replace")
    ap.add_argument("--invariance", default=str(OUT / "M5C2-B7-INVARIANCE20.json"))
    ap.add_argument("--provenance", default=str(OUT / "M5C2-B7-PROVENANCE-V2.json"))
    ap.add_argument("--notes", default=str(OUT / "M5C2-B7-EXTRACT-NOTES.json"))
    ap.add_argument("--run-log", default=str(OUT / "_m5b7_extract_run.log"))
    ap.add_argument("--resume-log", default=str(OUT / "_m5b7_extract_resume.log"))
    ap.add_argument("--expect-gen-sha16", default=DEFAULTS["gen_sha16"])
    ap.add_argument("--expect-gen-bytes", type=int, default=DEFAULTS["gen_bytes"])
    ap.add_argument("--expect-sents-sha16", default=DEFAULTS["sents_sha16"])
    ap.add_argument("--expect-sents-bytes", type=int, default=DEFAULTS["sents_bytes"])
    ap.add_argument("--expect-prompt-sha16", default=DEFAULTS["prompt_sha16"])
    ap.add_argument("--expect-model-bytes", type=int, default=DEFAULTS["model_bytes"])
    ap.add_argument("--expect-dll-sha16", default=DEFAULTS["dll_sha16"])
    ap.add_argument("--expect-n-predict", type=int, default=DEFAULTS["n_predict"])
    ap.add_argument("--expect-n-sids", type=int, default=DEFAULTS["n_sids"])
    ap.add_argument("--expect-invariance-sha16", default=DEFAULTS["invariance_sha16"])
    ap.add_argument("--expect-invariance-bytes", type=int, default=DEFAULTS["invariance_bytes"])
    ap.add_argument("--expect-provenance-sha16", default=DEFAULTS["provenance_sha16"])
    ap.add_argument("--expect-provenance-bytes", type=int, default=DEFAULTS["provenance_bytes"])
    ap.add_argument("--expect-notes-sha16", default=DEFAULTS["notes_sha16"])
    ap.add_argument("--expect-notes-bytes", type=int, default=DEFAULTS["notes_bytes"])
    a = ap.parse_args()

    checks = []
    warnings = []

    def add(cid, requirement, ok, detail):
        checks.append({"id": cid, "requirement": requirement,
                       "pass": bool(ok), "detail": detail})
        return bool(ok)

    # ---- core inputs ----
    try:
        sdoc, sb = read_json(a.sents)
        edoc, eb = read_json(a.extract)
        d1, b1 = read_json(a.shard1)
        d2, b2 = read_json(a.shard2)
    except Exception as e:  # noqa: BLE001
        print("INPUT ERROR: %r" % (e,), file=sys.stderr)
        return 2

    srows = sdoc.get("sentences") or sdoc.get("rows") or []
    sids = [r.get("sid") for r in srows]
    sid_set = set(sids)
    ex_recs = edoc.get("records") or []
    ex_sids = [r.get("sid") for r in ex_recs]
    r1 = d1.get("records") or []
    r2 = d2.get("records") or []
    s1 = [r.get("sid") for r in r1]
    s2 = [r.get("sid") for r in r2]

    # ---- SENTS ----
    add("sents_sha", "SENTS sha16/bytes == frozen pin",
        sha16(sb) == a.expect_sents_sha16 and len(sb) == a.expect_sents_bytes,
        "%s/%d B (expect %s/%d)" % (sha16(sb), len(sb),
                                     a.expect_sents_sha16, a.expect_sents_bytes))
    add("sents_n", "SENTS has %d sentences" % a.expect_n_sids,
        len(srows) == a.expect_n_sids, "%d sentences" % len(srows))
    add("sents_sid_unique", "SENTS sids unique",
        len(sid_set) == len(sids), "%d unique / %d" % (len(sid_set), len(sids)))

    # ---- EXTRACT records ----
    add("extract_schema", "EXTRACT schema is m5c2_b7_extract_v1",
        edoc.get("schema") == "m5c2_b7_extract_v1",
        "schema=%r" % (edoc.get("schema"),))
    add("extract_records_n", "EXTRACT has %d records" % a.expect_n_sids,
        len(ex_recs) == a.expect_n_sids, "%d records" % len(ex_recs))
    add("extract_n_sentences", "EXTRACT n_sentences == %d" % a.expect_n_sids,
        edoc.get("n_sentences") == a.expect_n_sids,
        "n_sentences=%r" % (edoc.get("n_sentences"),))
    add("extract_sid_unique", "EXTRACT sids unique",
        len(set(ex_sids)) == len(ex_sids), "%d unique / %d"
        % (len(set(ex_sids)), len(ex_sids)))
    add("extract_sids_equal_sents", "EXTRACT sid set == SENTS sid set",
        set(ex_sids) == sid_set,
        "missing=%d extra=%d" % (len(sid_set - set(ex_sids)),
                                 len(set(ex_sids) - sid_set)))
    add("extract_order_matches_sents", "EXTRACT record order == SENTS order",
        ex_sids == sids, "first mismatch at %r"
        % next((i for i, (x, y) in enumerate(zip(ex_sids, sids)) if x != y), None))
    add("extract_sids_in_sents", "every EXTRACT sid belongs to SENTS",
        all(x in sid_set for x in ex_sids), "unknown=%d"
        % len([x for x in ex_sids if x not in sid_set]))

    # ---- shards ----
    for name, d, raw in (("shard1", d1, b1), ("shard2", d2, b2)):
        add(name + "_schema", "%s schema is m5c2_b7_extract_raw_v1" % name,
            d.get("schema") == "m5c2_b7_extract_raw_v1", "schema=%r"
            % (d.get("schema"),))
    add("shard1_sids_unique", "shard1 sids unique",
        len(set(s1)) == len(s1), "%d unique / %d" % (len(set(s1)), len(s1)))
    add("shard2_sids_unique", "shard2 sids unique",
        len(set(s2)) == len(s2), "%d unique / %d" % (len(set(s2)), len(s2)))
    add("shards_subset_sents", "all shard sids belong to SENTS",
        all(x in sid_set for x in s1 + s2), "unknown=%d"
        % len([x for x in s1 + s2 if x not in sid_set]))
    actual_overlap = set(s1) & set(s2)
    add("shards_disjoint", "shard1 and shard2 sid sets are disjoint (overlap 0)",
        not actual_overlap, "overlap=%d" % len(actual_overlap))
    union = set(s1) | set(s2)
    add("shards_union_complete", "shard1 U shard2 == SENTS set (623/623, missing 0)",
        union == sid_set, "union=%d missing=%d extra=%d"
        % (len(union), len(sid_set - union), len(union - sid_set)))
    add("shards_union_n", "shard1 + shard2 sid counts sum to %d" % a.expect_n_sids,
        len(union) == a.expect_n_sids, "union=%d" % len(union))

    # ---- resume_provenance (R2 exact fields) ----
    prov = edoc.get("resume_provenance")
    ok_field = isinstance(prov, dict)
    add("prov_present", "EXTRACT.resume_provenance present (dict)", ok_field,
        "type=%s" % type(prov).__name__)
    if ok_field:
        p1 = prov.get("shard1") or {}
        p2 = prov.get("shard2") or {}
        ok_shape = all(isinstance(x, dict) and x.get("path") is not None
                       and x.get("sha16") is not None and x.get("bytes") is not None
                       and x.get("n_sids") is not None for x in (p1, p2))
        add("prov_shape", "resume_provenance shard1/shard2 {path,sha16,bytes,n_sids}",
            ok_shape, "shard1_keys=%r shard2_keys=%r"
            % (sorted(p1.keys()), sorted(p2.keys())))
        add("prov_shard1_file", "provenance shard1 sha16/bytes match actual shard1",
            sha16(b1) == str(p1.get("sha16")) and len(b1) == p1.get("bytes"),
            "actual=%s/%d recorded=%s/%r"
            % (sha16(b1), len(b1), p1.get("sha16"), p1.get("bytes")))
        add("prov_shard2_file", "provenance shard2 sha16/bytes match actual shard2",
            sha16(b2) == str(p2.get("sha16")) and len(b2) == p2.get("bytes"),
            "actual=%s/%d recorded=%s/%r"
            % (sha16(b2), len(b2), p2.get("sha16"), p2.get("bytes")))
        add("prov_counts", "provenance n_sids match actual shard records",
            p1.get("n_sids") == len(s1) and p2.get("n_sids") == len(s2),
            "shard1 %r vs %d; shard2 %r vs %d"
            % (p1.get("n_sids"), len(s1), p2.get("n_sids"), len(s2)))
        q1 = prov.get("sids_completed_in_shard1")
        q2 = prov.get("sids_in_shard2")
        add("prov_sids_lists", "provenance sids_completed_in_shard1 / sids_in_shard2 present",
            isinstance(q1, list) and isinstance(q2, list),
            "types=%s/%s" % (type(q1).__name__, type(q2).__name__))
        if isinstance(q1, list) and isinstance(q2, list):
            add("prov_sids_sets", "provenance sids lists == actual shard sids (as sets)",
                set(q1) == set(s1) and set(q2) == set(s2),
                "shard1 diff=%d shard2 diff=%d"
                % (len(set(q1) ^ set(s1)), len(set(q2) ^ set(s2))))
            add("prov_sids_union", "provenance sids lists union == SENTS (623, no dup)",
                set(q1) | set(q2) == sid_set and len(q1) + len(q2) == len(sid_set),
                "union=%d sum=%d" % (len(set(q1) | set(q2)), len(q1) + len(q2)))
        add("prov_overlap_missing_zero", "provenance overlap=0 and missing=0",
            prov.get("overlap") == 0 and prov.get("missing") == 0,
            "overlap=%r missing=%r" % (prov.get("overlap"), prov.get("missing")))
        add("prov_matches_actual",
            "provenance overlap/missing match actual shard sets",
            prov.get("overlap") == len(actual_overlap)
            and prov.get("missing") == len(sid_set - union),
            "actual overlap=%d missing=%d recorded=%r/%r"
            % (len(actual_overlap), len(sid_set - union),
               prov.get("overlap"), prov.get("missing")))

    # ---- pins ----
    pins = edoc.get("pins") or {}
    gp = pins.get("gen") or {}
    sp = pins.get("sents") or pins.get("sentences") or {}
    pp = pins.get("extraction_prompt") or {}
    mp = pins.get("model") or {}
    dp = pins.get("dll") or {}
    hp = pins.get("harness") or {}
    add("pin_gen", "GEN sha16/bytes match frozen pin",
        gp.get("sha16") == a.expect_gen_sha16 and gp.get("bytes") == a.expect_gen_bytes,
        "gen=%s/%r expect=%s/%d"
        % (gp.get("sha16"), gp.get("bytes"), a.expect_gen_sha16, a.expect_gen_bytes))
    add("pin_sents", "SENTS sha16/bytes match frozen pin",
        sp.get("sha16") == a.expect_sents_sha16 and sp.get("bytes") == a.expect_sents_bytes,
        "sents=%s/%r expect=%s/%d"
        % (sp.get("sha16"), sp.get("bytes"), a.expect_sents_sha16, a.expect_sents_bytes))
    add("pin_prompt", "extraction prompt sha16 match",
        pp.get("sha16") == a.expect_prompt_sha16,
        "prompt=%s expect=%s" % (pp.get("sha16"), a.expect_prompt_sha16))
    add("pin_model", "model frozen_bytes match",
        mp.get("frozen_bytes") == a.expect_model_bytes,
        "model=%r expect=%d" % (mp.get("frozen_bytes"), a.expect_model_bytes))
    add("pin_dll", "dll frozen_sha16 match",
        dp.get("frozen_sha16") == a.expect_dll_sha16,
        "dll=%s expect=%s" % (dp.get("frozen_sha16"), a.expect_dll_sha16))
    add("pin_n_predict", "n_predict == %d (harness)" % a.expect_n_predict,
        hp.get("n_predict") == a.expect_n_predict,
        "harness.n_predict=%r" % (hp.get("n_predict"),))
    add("extract_n_predict", "EXTRACT top-level n_predict == %d" % a.expect_n_predict,
        edoc.get("n_predict") in (None, a.expect_n_predict),
        "n_predict=%r" % (edoc.get("n_predict"),))
    add("pin_sampling", "greedy/no-grammar declared",
        hp.get("temperature") == 0 and hp.get("sampling") == "argmax_greedy"
        and hp.get("grammar") is None,
        "temperature=%r sampling=%r grammar=%r"
        % (hp.get("temperature"), hp.get("sampling"), hp.get("grammar")))
    if gp.get("n_forward") is not None and gp.get("n_forward") != 75:
        warnings.append("pins.gen.n_forward=%r (frozen GEN n_forward=75); "
                        "metadata only, not used by merge verdict"
                        % (gp.get("n_forward"),))

    # ---- no opt-in trace ----
    forbidden = ("--allow-gui-procs", "allow_gui_procs")
    hits = []
    for label, raw in (("extract", eb), ("shard1", b1), ("shard2", b2)):
        t = raw.decode("utf-8", "replace")
        for f in forbidden:
            if f in t:
                hits.append("%s:%s" % (label, f))
    add("no_allow_gui_trace", "no --allow-gui-procs / allow_gui_procs in artifacts",
        not hits, "hits=%r" % (hits,))

    # ---- optional gate strict ----
    gate = edoc.get("gate_before") or {}
    gate_after = edoc.get("gate_after") or {}
    if isinstance(gate, dict) and gate:
        names = [str(e.get("name", "")) for e in (gate.get("gate_exceptions") or [])]
        ok_gate = gate.get("gate_ok") is True and all(
            n.lower() in ("dwm", "dwm.exe") for n in names)
        add("gate_strict", "gate_before gate_ok and only lone dwm exception",
            ok_gate, "gate_ok=%r exceptions=%r"
            % (gate.get("gate_ok"), names))
    else:
        warnings.append("EXTRACT.gate_before missing; strict-gate check skipped")

    # ---- C1: session invariance (RULING A2 §C1) ----
    inv, inv_b, inv_err = load_optional(a.invariance)
    c1 = {"path": a.invariance, "error": inv_err, "pass": False}
    if inv_b is not None:
        c1.update({"sha16": sha16(inv_b), "bytes": len(inv_b)})
    add("c1_file_pin", "C1 invariance artifact sha16/bytes match pin",
        inv_b is not None and sha16(inv_b) == a.expect_invariance_sha16
        and len(inv_b) == a.expect_invariance_bytes,
        "err=%r actual=%s/%s expect=%s/%d"
        % (inv_err, sha16(inv_b) if inv_b else None,
           len(inv_b) if inv_b else None,
           a.expect_invariance_sha16, a.expect_invariance_bytes))
    if inv is None:
        for cid, req in (("c1_status", "C1 pass=true/status=pass"),
                        ("c1_n_seed", "C1 n_sample=20/n_identical=20/seed=20261027"),
                        ("c1_pins_10", "C1 ten pin assertions all pass"),
                        ("c1_negative_rc", "C1 negative pin test rc=2 (non-zero)"),
                        ("c1_shard1_pin", "C1 shard1 sha16/bytes == EXTRACT provenance shard1"),
                        ("c1_sids_subset", "C1 comparison sids are 20 shard1 sids"),
                        ("c1_raw_identical", "C1 all raw_out byte-identical/prompt/rc match"),
                        ("c1_forward_count", "C1 shard1 forward count == EXTRACT shard1 model_extract")):
            add(cid, req, False, "invariance file missing: %r" % (inv_err,))
    else:
        c1["pass"] = bool(inv.get("pass"))
        c1["n_sample"] = inv.get("n_sample")
        c1["n_identical"] = inv.get("n_identical")
        c1["seed"] = inv.get("seed")
        add("c1_status", "C1 pass=true/status=pass",
            inv.get("pass") is True and inv.get("status") == "pass",
            "pass=%r status=%r" % (inv.get("pass"), inv.get("status")))
        add("c1_n_seed", "C1 n_sample=20/n_identical=20/seed=20261027",
            inv.get("n_sample") == 20 and inv.get("n_identical") == 20
            and inv.get("seed") == 20261027,
            "n_sample=%r n_identical=%r seed=%r"
            % (inv.get("n_sample"), inv.get("n_identical"), inv.get("seed")))
        pa = inv.get("pin_assertions") or []
        add("c1_pins_10", "C1 ten pin assertions all pass",
            len(pa) == 10 and all(x.get("pass") is True for x in pa),
            "n=%d all_pass=%r" % (len(pa), all(x.get("pass") is True for x in pa)))
        neg = inv.get("negative_pin_test") or {}
        c1["negative_rc"] = neg.get("rc")
        add("c1_negative_rc", "C1 negative pin test rc=2 (non-zero)",
            neg.get("pass") is True and neg.get("rc") == 2,
            "pass=%r rc=%r" % (neg.get("pass"), neg.get("rc")))
        ish = inv.get("shard1") or {}
        psh = (prov or {}).get("shard1") or {}
        add("c1_shard1_pin", "C1 shard1 sha16/bytes == EXTRACT provenance shard1",
            ish.get("sha16") == psh.get("sha16") and ish.get("bytes") == psh.get("bytes"),
            "inv=%s/%r prov=%s/%r" % (ish.get("sha16"), ish.get("bytes"),
                                      psh.get("sha16"), psh.get("bytes")))
        comps = inv.get("comparisons") or []
        c1["sids"] = [x.get("sid") for x in comps]
        shard1_sids = set((prov or {}).get("sids_completed_in_shard1") or s1)
        add("c1_sids_subset", "C1 comparison sids are 20 shard1 sids",
            len(comps) == 20 and len(set(c1["sids"])) == 20
            and set(c1["sids"]) <= shard1_sids,
            "n=%d unique=%d outside_shard1=%d"
            % (len(comps), len(set(c1["sids"])),
               len(set(c1["sids"]) - shard1_sids)))
        add("c1_raw_identical", "C1 all raw_out byte-identical/prompt/rc match",
            bool(comps) and all(x.get("raw_identical") is True
                                and x.get("prompt_sha16_matches") is True
                                and x.get("rc_matches") is True for x in comps),
            "n=%d all=%r" % (len(comps), bool(comps) and all(
                x.get("raw_identical") is True and x.get("prompt_sha16_matches") is True
                and x.get("rc_matches") is True for x in comps)))
        shard1_forward = sum(1 for x in ex_recs
                             if x.get("sid") in shard1_sids and x.get("route") == "model_extract")
        add("c1_forward_count", "C1 shard1 forward count == EXTRACT shard1 model_extract",
            ish.get("n_forward_sentences") == shard1_forward,
            "inv=%r extract=%d" % (ish.get("n_forward_sentences"), shard1_forward))

    # ---- C2: layer0 heterogeneity (RULING A2 §C2, corrected by A2-A1) ----
    layer_recs = [r for r in ex_recs if r.get("layer0") is not None]
    route_ct = {}
    for r in ex_recs:
        route_ct[r.get("route")] = route_ct.get(r.get("route"), 0) + 1
    shard1_set = set((prov or {}).get("sids_completed_in_shard1") or s1)
    shard2_set = set((prov or {}).get("sids_in_shard2") or s2)
    l1 = sum(1 for r in layer_recs if r.get("sid") in shard1_set)
    l2 = sum(1 for r in layer_recs if r.get("sid") in shard2_set)
    c2 = {"layer0_skipped": edoc.get("layer0_skipped"),
          "layer0_records": len(layer_recs), "shard1": l1, "shard2": l2,
          "routes": route_ct,
          "composition": "19+23" if (l1, l2) == (19, 23) else "%d+%d" % (l1, l2)}
    add("c2_layer0_count", "C2 layer0_skipped == 42 and 42 layer0 records",
        edoc.get("layer0_skipped") == 42 and len(layer_recs) == 42,
        "layer0_skipped=%r records=%d"
        % (edoc.get("layer0_skipped"), len(layer_recs)))
    add("c2_layer0_semantics",
        "C2 every layer0 record: route=abstain_check, items=[], layer0.verdict=abstain_ok",
        bool(layer_recs) and all(
            r.get("route") == "abstain_check" and r.get("items") == []
            and isinstance(r.get("layer0"), dict)
            and r["layer0"].get("verdict") == "abstain_ok" for r in layer_recs),
        "bad=%d" % sum(1 for r in layer_recs if not (
            r.get("route") == "abstain_check" and r.get("items") == []
            and isinstance(r.get("layer0"), dict)
            and r["layer0"].get("verdict") == "abstain_ok")))
    add("c2_split_19_23", "C2 42 layer0 == shard1 19 + shard2 23 (by sid sets)",
        (l1, l2, len(layer_recs)) == (19, 23, 42),
        "shard1=%d shard2=%d total=%d" % (l1, l2, len(layer_recs)))
    add("c2_forward_plus_layer0", "C2 n_forward + layer0_skipped == 623",
        edoc.get("n_forward") == 581 and edoc.get("layer0_skipped") == 42
        and edoc.get("n_forward") + edoc.get("layer0_skipped") == a.expect_n_sids,
        "n_forward=%r layer0=%r sum=%r"
        % (edoc.get("n_forward"), edoc.get("layer0_skipped"),
           (edoc.get("n_forward") or 0) + (edoc.get("layer0_skipped") or 0)))
    pv, pv_b, pv_err = load_optional(a.provenance)
    c2["provenance_v2"] = {"path": a.provenance, "error": pv_err,
                           "sha16": sha16(pv_b) if pv_b else None,
                           "bytes": len(pv_b) if pv_b else None}
    if pv is not None:
        pa2 = (pv.get("assertions") or {})
        add("c2_provenance_v2", "C2 PROVENANCE-V2 pin + records_identical + layer0_skipped_42",
            sha16(pv_b) == a.expect_provenance_sha16 and len(pv_b) == a.expect_provenance_bytes
            and pv.get("records_identical") is True
            and pa2.get("layer0_skipped_42") is True,
            "sha=%s/%d records_identical=%r layer0_42=%r"
            % (sha16(pv_b), len(pv_b), pv.get("records_identical"),
               pa2.get("layer0_skipped_42")))
    else:
        add("c2_provenance_v2", "C2 PROVENANCE-V2 pin + records_identical + layer0_skipped_42",
            False, "missing provenance v2: %r" % (pv_err,))

    # ---- C3: timeout close mode (RULING A2 §C3) ----
    run_d, run_b, run_exit = parse_log_with_exit(a.run_log)
    res_d, res_b, res_exit = parse_log_with_exit(a.resume_log)
    notes, notes_b, notes_err = load_optional(a.notes)
    c3 = {"run_log": {"path": a.run_log,
                      "sha16": sha16(run_b) if run_b else None,
                      "bytes": len(run_b) if run_b else None,
                      "exit_code": run_exit, "data": run_d},
          "resume_log": {"path": a.resume_log,
                         "sha16": sha16(res_b) if res_b else None,
                         "bytes": len(res_b) if res_b else None,
                         "exit_code": res_exit, "data": res_d},
          "signals_sent": edoc.get("signals_sent"),
          "no_parent_signals": edoc.get("no_parent_signals"),
          "resume_exit_note": "resume log has no literal EXIT=<n> line; "
                              "success inferred from status/merge_complete/aborted=null",
          "boot_before": gate.get("boot_id"), "boot_after": gate_after.get("boot_id"),
          "notes": {"path": a.notes, "error": notes_err,
                    "sha16": sha16(notes_b) if notes_b else None,
                    "bytes": len(notes_b) if notes_b else None}}
    add("c3_run_log_exit3", "C3 run log: exit 3, timeout >3600s, timeout_mid",
        run_d is not None and run_exit == 3
        and run_d.get("aborted") == "timeout >3600s"
        and run_d.get("abort_class") == "timeout_mid"
        and run_d.get("n_forward") == 388
        and float(run_d.get("elapsed_s") or 0) > 3600,
        "exit=%r aborted=%r class=%r n_forward=%r elapsed=%r"
        % (run_exit, (run_d or {}).get("aborted"), (run_d or {}).get("abort_class"),
           (run_d or {}).get("n_forward"), (run_d or {}).get("elapsed_s")))
    ok_resume = (res_d is not None and res_d.get("status") == "已抽取未判定"
                 and res_d.get("aborted") is None
                 and res_d.get("merge_complete") is True
                 and (res_exit in (None, 0)))
    add("c3_resume_log_ok", "C3 resume log: success (exit 0 / merge_complete, no abort)",
        ok_resume, "exit=%r status=%r aborted=%r merge_complete=%r"
        % (res_exit, (res_d or {}).get("status"), (res_d or {}).get("aborted"),
           (res_d or {}).get("merge_complete")))
    add("c3_signals_sent", "C3 EXTRACT signals_sent=false and no_parent_signals=true",
        edoc.get("signals_sent") is False and edoc.get("no_parent_signals") is True,
        "signals_sent=%r no_parent_signals=%r"
        % (edoc.get("signals_sent"), edoc.get("no_parent_signals")))
    add("c3_boot_equal", "C3 gate_before.boot_id == gate_after.boot_id",
        bool(gate.get("boot_id")) and gate.get("boot_id") == gate_after.get("boot_id"),
        "before=%r after=%r" % (gate.get("boot_id"), gate_after.get("boot_id")))
    if notes is not None:
        n3 = notes.get("C3_close_mode") or {}
        c3["notes"]["C3_close_mode"] = n3
        add("c3_notes_c3", "C3 NOTES: exit_code=3/timeout_mid/graceful/no WATCHDOG-Minidump",
            sha16(notes_b) == a.expect_notes_sha16 and len(notes_b) == a.expect_notes_bytes
            and n3.get("exit_code") == 3 and n3.get("abort_class") == "timeout_mid"
            and "graceful" in str(n3.get("verdict", "")).lower()
            and ("未发现" in str(n3.get("watchdog_or_minidump", ""))
                 or "none" in str(n3.get("watchdog_or_minidump", "")).lower()),
            "sha=%s/%d exit=%r class=%r verdict=%r watchdog=%r"
            % (sha16(notes_b), len(notes_b), n3.get("exit_code"),
               n3.get("abort_class"), n3.get("verdict"),
               n3.get("watchdog_or_minidump")))
        add("c3_boot_notes", "C3 NOTES boot_id_before == boot_id_after == gate boot_id",
            n3.get("boot_id_before") == n3.get("boot_id_after")
            and n3.get("boot_id_before") == gate.get("boot_id"),
            "notes=%r/%r gate=%r" % (n3.get("boot_id_before"),
                                     n3.get("boot_id_after"), gate.get("boot_id")))
    else:
        add("c3_notes_c3", "C3 NOTES: exit_code=3/timeout_mid/graceful/no WATCHDOG-Minidump",
            False, "missing notes: %r" % (notes_err,))
        add("c3_boot_notes", "C3 NOTES boot_id_before == boot_id_after == gate boot_id",
            False, "missing notes: %r" % (notes_err,))
    wd_hits = [n for n in os.listdir(OUT)
               if "watchdog" in n.lower() or "minidump" in n.lower()]
    add("c3_no_watchdog_minidump_files", "C3 out/ has no *WATCHDOG*/*minidump* artifact",
        not wd_hits, "hits=%r" % (wd_hits,))

    # ---- falsifiability: each C1/C2/C3 group must be able to go red independently ----
    def _c1_group_ok(inv_x):
        if not isinstance(inv_x, dict):
            return False
        if not (inv_x.get("pass") is True and inv_x.get("status") == "pass"):
            return False
        if not (inv_x.get("n_sample") == 20 and inv_x.get("n_identical") == 20
                and inv_x.get("seed") == 20261027):
            return False
        pa = inv_x.get("pin_assertions") or []
        if not (len(pa) == 10 and all(x.get("pass") is True for x in pa)):
            return False
        neg = inv_x.get("negative_pin_test") or {}
        if not (neg.get("pass") is True and neg.get("rc") == 2):
            return False
        ish = inv_x.get("shard1") or {}
        psh = (prov or {}).get("shard1") or {}
        if not (ish.get("sha16") == psh.get("sha16")
                and ish.get("bytes") == psh.get("bytes")):
            return False
        comps = inv_x.get("comparisons") or []
        inv_sids = [x.get("sid") for x in comps]
        sh1 = set((prov or {}).get("sids_completed_in_shard1") or s1)
        if not (len(comps) == 20 and len(set(inv_sids)) == 20
                and set(inv_sids) <= sh1):
            return False
        if not all(x.get("raw_identical") is True
                   and x.get("prompt_sha16_matches") is True
                   and x.get("rc_matches") is True for x in comps):
            return False
        fwd = sum(1 for x in ex_recs if x.get("sid") in sh1
                  and x.get("route") == "model_extract")
        if ish.get("n_forward_sentences") != fwd:
            return False
        return True

    def _c2_group_ok(edoc_x, ex_recs_x, prov_x, pv_x, pv_b_x):
        if not isinstance(edoc_x, dict):
            return False
        layer = [r for r in ex_recs_x if r.get("layer0") is not None]
        if not (edoc_x.get("layer0_skipped") == 42 and len(layer) == 42):
            return False
        if not all(r.get("route") == "abstain_check" and r.get("items") == []
                   and isinstance(r.get("layer0"), dict)
                   and r["layer0"].get("verdict") == "abstain_ok" for r in layer):
            return False
        s1x = set((prov_x or {}).get("sids_completed_in_shard1") or [])
        s2x = set((prov_x or {}).get("sids_in_shard2") or [])
        l1 = sum(1 for r in layer if r.get("sid") in s1x)
        l2 = sum(1 for r in layer if r.get("sid") in s2x)
        if (l1, l2, len(layer)) != (19, 23, 42):
            return False
        if not (edoc_x.get("n_forward") == 581
                and edoc_x.get("layer0_skipped") == 42
                and edoc_x.get("n_forward") + edoc_x.get("layer0_skipped") == a.expect_n_sids):
            return False
        if pv_x is None or pv_b_x is None:
            return False
        pa2 = pv_x.get("assertions") or {}
        if not (sha16(pv_b_x) == a.expect_provenance_sha16
                and len(pv_b_x) == a.expect_provenance_bytes
                and pv_x.get("records_identical") is True
                and pa2.get("layer0_skipped_42") is True):
            return False
        return True

    def _c3_group_ok(run_d_x, run_exit_x, res_d_x, res_exit_x,
                     notes_x, notes_b_x, gate_x, gate_after_x):
        if not (run_d_x is not None and run_exit_x == 3
                and run_d_x.get("aborted") == "timeout >3600s"
                and run_d_x.get("abort_class") == "timeout_mid"
                and run_d_x.get("n_forward") == 388
                and float(run_d_x.get("elapsed_s") or 0) > 3600):
            return False
        if not (res_d_x is not None and res_d_x.get("status") == "已抽取未判定"
                and res_d_x.get("aborted") is None
                and res_d_x.get("merge_complete") is True
                and res_exit_x in (None, 0)):
            return False
        if not (edoc.get("signals_sent") is False
                and edoc.get("no_parent_signals") is True):
            return False
        if not (bool(gate_x.get("boot_id"))
                and gate_x.get("boot_id") == gate_after_x.get("boot_id")):
            return False
        if notes_x is None or notes_b_x is None:
            return False
        n3 = notes_x.get("C3_close_mode") or {}
        if not (sha16(notes_b_x) == a.expect_notes_sha16
                and len(notes_b_x) == a.expect_notes_bytes
                and n3.get("exit_code") == 3
                and n3.get("abort_class") == "timeout_mid"
                and "graceful" in str(n3.get("verdict", "")).lower()
                and ("未发现" in str(n3.get("watchdog_or_minidump", ""))
                     or "none" in str(n3.get("watchdog_or_minidump", "")).lower())):
            return False
        if not (n3.get("boot_id_before") == n3.get("boot_id_after")
                == gate_x.get("boot_id")):
            return False
        wd = [n for n in os.listdir(OUT)
              if "watchdog" in n.lower() or "minidump" in n.lower()]
        if wd:
            return False
        return True

    fals = {}
    if inv is not None:
        c1_pos = _c1_group_ok(inv)
        inv_bad1 = copy.deepcopy(inv)
        inv_bad1["comparisons"][0]["raw_identical"] = False
        inv_bad2 = copy.deepcopy(inv)
        inv_bad2["n_identical"] = 19
        c1_neg1 = _c1_group_ok(inv_bad1)
        c1_neg2 = _c1_group_ok(inv_bad2)
        c1_res = _c1_group_ok(inv)
        fals["C1"] = {
            "positive_group_pass": bool(c1_pos),
            "negative_case_c1": "fail_detected"
            if (c1_pos and not c1_neg1 and not c1_neg2 and c1_res) else "NOT_DETECTED",
            "mutations": ["comparisons[0].raw_identical=False", "n_identical=19"],
            "negative_group_pass": bool(c1_neg1 or c1_neg2),
            "restored_pass": bool(c1_res)}
    else:
        fals["C1"] = {"positive_group_pass": False,
                      "negative_case_c1": "NOT_DETECTED",
                      "mutations": [], "negative_group_pass": None,
                      "restored_pass": False}
    c2_pos = _c2_group_ok(edoc, ex_recs, prov, pv, pv_b)
    c2_bad41 = copy.deepcopy(edoc)
    c2_bad41["layer0_skipped"] = 41
    c2_bad43 = copy.deepcopy(edoc)
    c2_bad43["layer0_skipped"] = 43
    c2_neg1 = _c2_group_ok(c2_bad41, ex_recs, prov, pv, pv_b)
    c2_neg2 = _c2_group_ok(c2_bad43, ex_recs, prov, pv, pv_b)
    c2_res = _c2_group_ok(edoc, ex_recs, prov, pv, pv_b)
    fals["C2"] = {
        "positive_group_pass": bool(c2_pos),
        "negative_case_c2": "fail_detected"
        if (c2_pos and not c2_neg1 and not c2_neg2 and c2_res) else "NOT_DETECTED",
        "mutations": ["layer0_skipped=41", "layer0_skipped=43"],
        "negative_group_pass": bool(c2_neg1 or c2_neg2),
        "restored_pass": bool(c2_res)}
    c3_pos = _c3_group_ok(run_d, run_exit, res_d, res_exit, notes, notes_b,
                          gate, gate_after)
    c3_bad_run = copy.deepcopy(run_d) if run_d is not None else None
    if c3_bad_run is not None:
        c3_bad_run["aborted"] = "completed"
    c3_neg1 = _c3_group_ok(c3_bad_run, 0, res_d, res_exit, notes, notes_b,
                           gate, gate_after)
    gate_bad = dict(gate)
    gate_bad["boot_id"] = "9999-99-99T99:99:99"
    c3_neg2 = _c3_group_ok(run_d, run_exit, res_d, res_exit, notes, notes_b,
                           gate_bad, gate_after)
    c3_res = _c3_group_ok(run_d, run_exit, res_d, res_exit, notes, notes_b,
                          gate, gate_after)
    fals["C3"] = {
        "positive_group_pass": bool(c3_pos),
        "negative_case_c3": "fail_detected"
        if (c3_pos and not c3_neg1 and not c3_neg2 and c3_res) else "NOT_DETECTED",
        "mutations": ["run_log exit=0 + aborted=completed",
                      "gate_before.boot_id mismatch"],
        "negative_group_pass": bool(c3_neg1 or c3_neg2),
        "restored_pass": bool(c3_res)}
    fals["independence"] = {
        "C1_mutation_keeps_C2_C3": bool(
            _c2_group_ok(edoc, ex_recs, prov, pv, pv_b)
            and _c3_group_ok(run_d, run_exit, res_d, res_exit,
                             notes, notes_b, gate, gate_after)),
        "C2_mutation_keeps_C1_C3": bool(
            _c1_group_ok(inv)
            and _c3_group_ok(run_d, run_exit, res_d, res_exit,
                             notes, notes_b, gate, gate_after)),
        "C3_mutation_keeps_C1_C2": bool(
            _c1_group_ok(inv)
            and _c2_group_ok(edoc, ex_recs, prov, pv, pv_b)),
        "note": "each mutation is applied to an in-memory copy only; "
                "the other groups are re-evaluated on unmodified inputs"}
    fals["all_detected"] = all(
        fals[k].get("negative_case_" + k.lower()) == "fail_detected"
        for k in ("C1", "C2", "C3"))

    failed = [c["id"] for c in checks if not c["pass"]]
    if not fals.get("all_detected") and "falsifiability" not in failed:
        failed.append("falsifiability")
    verdict = "pass" if not failed else "fail"
    out = {
        "schema": "m5c2_b7_merge_check_v3",
        "version": 3,
        "supersedes": "b599a62d5a1a74d0",
        "supersedes_actual_before": "6ce45a78f2eb72a0",
        "supersedes_note": "lead-pinned v2 sha b599a62d5a1a74d0; "
                           "on-disk predecessor before v3 was 6ce45a78f2eb72a0 "
                           "(same 59 checks, different checked_at)",
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "inputs": {
            "extract": {"path": a.extract, "sha16": sha16(eb), "sha256": sha256(eb),
                        "bytes": len(eb)},
            "sents": {"path": a.sents, "sha16": sha16(sb), "sha256": sha256(sb),
                      "bytes": len(sb)},
            "shard1": {"path": a.shard1, "sha16": sha16(b1), "sha256": sha256(b1),
                       "bytes": len(b1)},
            "shard2": {"path": a.shard2, "sha16": sha16(b2), "sha256": sha256(b2),
                       "bytes": len(b2)},
            "invariance": {"path": a.invariance,
                           "sha16": sha16(inv_b) if inv_b else None,
                           "bytes": len(inv_b) if inv_b else None},
            "provenance_v2": {"path": a.provenance,
                              "sha16": sha16(pv_b) if pv_b else None,
                              "bytes": len(pv_b) if pv_b else None},
            "notes": {"path": a.notes,
                      "sha16": sha16(notes_b) if notes_b else None,
                      "bytes": len(notes_b) if notes_b else None},
            "run_log": {"path": a.run_log,
                        "sha16": sha16(run_b) if run_b else None,
                        "bytes": len(run_b) if run_b else None},
            "resume_log": {"path": a.resume_log,
                           "sha16": sha16(res_b) if res_b else None,
                           "bytes": len(res_b) if res_b else None},
        },
        "expected_pins": {
            "gen": {"sha16": a.expect_gen_sha16, "bytes": a.expect_gen_bytes},
            "sents": {"sha16": a.expect_sents_sha16, "bytes": a.expect_sents_bytes},
            "prompt_sha16": a.expect_prompt_sha16,
            "model_bytes": a.expect_model_bytes,
            "dll_sha16": a.expect_dll_sha16,
            "n_predict": a.expect_n_predict,
            "n_sids": a.expect_n_sids,
            "invariance": {"sha16": a.expect_invariance_sha16,
                           "bytes": a.expect_invariance_bytes},
            "provenance_v2": {"sha16": a.expect_provenance_sha16,
                              "bytes": a.expect_provenance_bytes},
            "notes": {"sha16": a.expect_notes_sha16, "bytes": a.expect_notes_bytes},
        },
        "evidence": {"C1": c1, "C2": c2, "C3": c3},
        "falsifiability": fals,
        "checks": checks,
        "failed_checks": failed,
        "warnings": warnings,
        "verdict": verdict,
        "n_checks": len(checks),
    }
    outp = Path(a.out)
    if getattr(a, "force_overwrite_readonly", False) and outp.exists():
        try:
            os.chmod(outp, stat.S_IWRITE)
        except OSError:
            pass
    outp.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(outp) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, outp)
    print(json.dumps({"verdict": verdict, "failed_checks": failed,
                      "n_checks": len(checks), "out": str(outp)},
                     ensure_ascii=False))
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())