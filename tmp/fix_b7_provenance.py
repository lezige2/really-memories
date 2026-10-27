#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Provenance-only normalisation for the b7' merged EXTRACT (no GPU, no forwards).

RULING-M5C2-B7-EXTRACT-PROVENANCE-A3: the frozen resume script wrote a
`resume_provenance` shape that differs from RULING-M5C2-B7-EXTRACT-RESUME R2, so
5/36 merge-check assertions failed even though the merged data is correct.  This
post-processor rewrites ONLY `resume_provenance` into the ruled shape:
    {shard1{path,sha16,bytes,n_sids}, shard2{...},
     sids_completed_in_shard1, sids_in_shard2, overlap:0, missing:0}
and proves the records are untouched (canonical byte sha before/after).  It does
not re-run forwards, does not touch the frozen resume script, and keeps the old
EXTRACT as a preserved backup (superseded, recorded in the report).

Modes: --dry-run (assertions + planned rewrite; writes nothing) | default (write)
Exit: 0 ok; 2 pin/assertion error; 3 records changed (abort, nothing written).
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"

A3 = ROOT / "docs/_work/RULING-M5C2-B7-EXTRACT-PROVENANCE-A3.md"
A3_SHA16 = "6e997f4921b56eab"
A3_BYTES = 1403
A2A1 = ROOT / "docs/_work/RULING-M5C2-B7-EXTRACT-RESUME-A2-A1.md"
A2A1_SHA16 = "ecbebaa82448e0fb"
A2A1_BYTES = 636

EXTRACT = OUT / "M5C2-B7-EXTRACT.json"
OLD_SHA16 = "bed3b6517e9738c8"
OLD_BYTES = 952884
SENTS = OUT / "M5C2-B7-SENTS.json"
SENTS_SHA16 = "c5a49a696b66f0c7"
SENTS_BYTES = 288805
RAW1 = OUT / "_m5b7_extract_raw.json"
RAW2 = OUT / "_m5b7_extract_raw_shard2.json"
REPORT = OUT / "M5C2-B7-PROVENANCE-V2.json"
N_SENTS = 623
N_FORWARD = 581
N_LAYER0 = 42


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def verify_pin(path, want_sha, want_bytes, label):
    b = Path(path).read_bytes()
    if sha16(b) != want_sha or len(b) != want_bytes:
        raise SystemExit("%s changed: %s / %d B" % (label, sha16(b), len(b)))
    return {"path": str(Path(path).relative_to(ROOT)).replace("\\", "/"),
            "sha16": want_sha, "bytes": len(b)}


def load_json(path):
    return json.loads(Path(path).read_bytes().decode("utf-8"))


def load_shard(path):
    p = Path(path)
    b = p.read_bytes()
    d = json.loads(b.decode("utf-8"))
    if d.get("schema") != "m5c2_b7_extract_raw_v1":
        raise SystemExit("unexpected shard schema: %r" % (d.get("schema"),))
    sids = []
    seen = set()
    for r in d.get("records") or []:
        sid = r.get("sid")
        if sid is None:
            raise SystemExit("shard record without sid: %s" % p)
        if sid in seen:
            raise SystemExit("duplicate sid inside %s: %s" % (p, sid))
        seen.add(sid)
        sids.append(sid)
    return d, sids, {"path": str(p.relative_to(ROOT)).replace("\\", "/"),
                     "sha16": sha16(b), "bytes": len(b),
                     "n_sids": len(sids)}


def canonical_records_bytes(records):
    return json.dumps(records, ensure_ascii=False, indent=1).encode("utf-8")


def build(extract_path, sents_path, raw1_path, raw2_path, dry):
    pins = {
        "ruling_provenance_a3": verify_pin(A3, A3_SHA16, A3_BYTES,
                                           "RULING-M5C2-B7-EXTRACT-PROVENANCE-A3.md"),
        "ruling_resume_a2_a1": verify_pin(A2A1, A2A1_SHA16, A2A1_BYTES,
                                          "RULING-M5C2-B7-EXTRACT-RESUME-A2-A1.md"),
    }
    sb = Path(sents_path).read_bytes()
    sdoc = json.loads(sb.decode("utf-8"))
    if sha16(sb) != SENTS_SHA16 or len(sb) != SENTS_BYTES:
        raise SystemExit("SENTS changed: %s / %d B" % (sha16(sb), len(sb)))
    sents_sids = [r["sid"] for r in sdoc.get("sentences") or []]
    if len(sents_sids) != N_SENTS:
        raise SystemExit("SENTS n_sentences %d != %d" % (len(sents_sids), N_SENTS))

    old_bytes = Path(extract_path).read_bytes()
    doc = json.loads(old_bytes.decode("utf-8"))
    if sha16(old_bytes) != OLD_SHA16 or len(old_bytes) != OLD_BYTES:
        raise SystemExit("pre-provenance EXTRACT changed: %s / %d B "
                         "(expected %s / %d B)"
                         % (sha16(old_bytes), len(old_bytes), OLD_SHA16,
                            OLD_BYTES))
    recs = doc.get("records") or []
    if len(recs) != N_SENTS:
        raise SystemExit("EXTRACT records %d != %d" % (len(recs), N_SENTS))
    rec_sids = [r.get("sid") for r in recs]
    if rec_sids != sents_sids:
        raise SystemExit("EXTRACT records not in SENTS order / not the SENTS set")
    if len(set(rec_sids)) != N_SENTS:
        raise SystemExit("EXTRACT records contain duplicate sids")
    if doc.get("n_forward") != N_FORWARD:
        raise SystemExit("EXTRACT n_forward %r != %d" % (doc.get("n_forward"),
                                                         N_FORWARD))
    if doc.get("layer0_skipped") != N_LAYER0:
        raise SystemExit("EXTRACT layer0_skipped %r != %d"
                         % (doc.get("layer0_skipped"), N_LAYER0))
    if doc.get("aborted") is not None:
        raise SystemExit("EXTRACT aborted=%r; refusing provenance rewrite"
                         % (doc.get("aborted"),))

    d1, s1, meta1 = load_shard(raw1_path)
    d2, s2, meta2 = load_shard(raw2_path)
    overlap = len(set(s1) & set(s2))
    missing = len(set(sents_sids) - (set(s1) | set(s2)))
    extra = len((set(s1) | set(s2)) - set(sents_sids))
    if overlap or missing or extra:
        raise SystemExit("shard sets invalid: overlap=%d missing=%d extra=%d"
                         % (overlap, missing, extra))
    if set(s1) | set(s2) != set(sents_sids):
        raise SystemExit("shard union != SENTS set")

    new_prov = {
        "shard1": {"path": meta1["path"], "sha16": meta1["sha16"],
                   "bytes": meta1["bytes"], "n_sids": meta1["n_sids"]},
        "shard2": {"path": meta2["path"], "sha16": meta2["sha16"],
                   "bytes": meta2["bytes"], "n_sids": meta2["n_sids"]},
        "sids_completed_in_shard1": s1,
        "sids_in_shard2": s2,
        "overlap": 0,
        "missing": 0,
    }
    old_records_sha = sha256_hex(canonical_records_bytes(recs))
    new_doc = dict(doc)
    new_doc["resume_provenance"] = new_prov
    new_records_sha = sha256_hex(canonical_records_bytes(new_doc["records"]))
    base = Path(extract_path)
    backup = base.with_name("_b7_extract_pre_provenance_%s.json" % OLD_SHA16)

    report = {
        "schema": "m5c2_b7_provenance_v2_v1",
        "status": "dry_run" if dry else "ok",
        "rule": "RULING-M5C2-B7-EXTRACT-PROVENANCE-A3 R1/R2: rewrite only "
                "resume_provenance into the R2 shape; records must be "
                "byte-identical; old EXTRACT preserved",
        "pins": pins,
        "old_extract": {"path": str(base.relative_to(ROOT)).replace("\\", "/"),
                        "sha16": sha16(old_bytes), "bytes": len(old_bytes)},
        "new_provenance": new_prov,
        "records_sha256_before": old_records_sha,
        "records_sha256_after": new_records_sha,
        "records_identical": old_records_sha == new_records_sha,
        "assertions": {
            "sents_count_623": True,
            "records_623_unique_in_sents_order": True,
            "n_forward_581": True,
            "layer0_skipped_42": True,
            "aborted_null": True,
            "shards_disjoint": overlap == 0,
            "shards_union_623": set(s1) | set(s2) == set(sents_sids),
            "overlap_0": new_prov["overlap"] == 0,
            "missing_0": new_prov["missing"] == 0,
        },
        "no_gpu": True, "no_forward": True,
        "backup_path": str(backup.relative_to(ROOT)).replace("\\", "/"),
    }
    if old_records_sha != new_records_sha:
        report["status"] = "abort_records_changed"
        return report, 3

    if dry:
        candidate = (json.dumps(new_doc, ensure_ascii=False, indent=1)
                     + "\n").encode("utf-8")
        report["planned_new_sha16"] = sha16(candidate)
        report["planned_new_bytes"] = len(candidate)
        return report, 0

    if not backup.exists():
        shutil.copyfile(base, backup)
        os.chmod(backup, 0o444)
    elif backup.read_bytes() != old_bytes:
        raise SystemExit("backup file exists but differs: %s" % backup)
    write_json_atomic(base, new_doc)
    new_bytes = base.read_bytes()
    report["new_extract"] = {"path": str(base.relative_to(ROOT)).replace("\\", "/"),
                             "sha16": sha16(new_bytes), "bytes": len(new_bytes),
                             "supersedes_sha16": OLD_SHA16}
    report["status"] = "ok"
    return report, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", default=str(EXTRACT))
    ap.add_argument("--sents", default=str(SENTS))
    ap.add_argument("--raw-shard1", default=str(RAW1))
    ap.add_argument("--raw-shard2", default=str(RAW2))
    ap.add_argument("--report", default=str(REPORT))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    report, rc = build(a.extract, a.sents, a.raw_shard1, a.raw_shard2,
                       a.dry_run)
    if not a.dry_run and rc == 0:
        write_json_atomic(a.report, report)
        b = Path(a.report).read_bytes()
        report_print = {
            "status": report["status"],
            "report": str(Path(a.report).relative_to(ROOT)).replace("\\", "/"),
            "report_sha16": sha16(b), "report_bytes": len(b),
            "old_sha16": report["old_extract"]["sha16"],
            "new_sha16": report["new_extract"]["sha16"],
            "new_bytes": report["new_extract"]["bytes"],
            "records_identical": report["records_identical"],
            "backup": report["backup_path"],
        }
        print(json.dumps(report_print, ensure_ascii=False, indent=1))
    else:
        print(json.dumps({"status": report["status"],
                          "dry_run": a.dry_run,
                          "assertions": report["assertions"],
                          "records_identical": report["records_identical"],
                          "planned_new_sha16": report.get("planned_new_sha16"),
                          "planned_new_bytes": report.get("planned_new_bytes")},
                         ensure_ascii=False, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())