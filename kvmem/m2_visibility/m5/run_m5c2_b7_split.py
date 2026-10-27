#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5-C2 B7 sentence splitter (CPU only; frozen (b5) split rules, verbatim).

Rules (PREREG-M5-C2-B5.md §4 / RULING-M5C2-B7.md R3 (identical split rules)):
  * split on newline AND on 。！？ (delimiter stays with the preceding segment);
  * empty segments are dropped;
  * `</?think>` lines are dropped;
  * pure-symbol lines (after removing whitespace: only punctuation/symbols) are
    dropped;
  * question-echo segments starting with `问：` / `问:` are dropped;
  * nothing else is dropped: `答：` lines, `###` headers, list bullets and
    markdown bold markers are kept verbatim.

Acceptance (frozen, must pass before any b6 use):
  rebuilding M5C2-B5-SENTENCES.json byte-for-byte from M5C2-B5-GEN.json must
  reproduce sha16 ba92635c8ad0c410 / 116,566 B exactly (`--check-b5`).

Modes (exactly one):
  --check-b5   rebuild the frozen b5 SENTENCES and assert the byte-identical pin
  --gen-b7     read out/M5C2-B7-GEN.json and write out/M5C2-B7-SENTS.json
  --dry-run    static validation only (pins + counts; writes nothing)
"""
import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"

PRE_B5 = ROOT / "docs/_work/PREREG-M5-C2-B5.md"
PRE_B5_SHA16 = "d6c7bdac73ef7326"
PRE_B5_BYTES = 14597
GEN_B5 = OUT / "M5C2-B5-GEN.json"
GEN_B5_SHA16 = "2b63a02463994c03"
GEN_B5_BYTES = 68184
SENT_B5 = OUT / "M5C2-B5-SENTENCES.json"
SENT_B5_SHA16 = "ba92635c8ad0c410"
SENT_B5_BYTES = 116566
SENT_B5_N = 326

RULING = ROOT / "docs/_work/RULING-M5C2-B7.md"
RULING_SHA16 = "3dfafd1253f0a833"
RULING_BYTES = 9425
B7_IN = OUT / "M5C2-B7-QUESTIONS.json"
B7_IN_SHA16 = "f1f059539453d562"
B7_IN_BYTES = 15964
B7_FREEZE = OUT / "M5C2-B7-QUESTIONS-FREEZE.json"
B7_FREEZE_SHA16 = "1baeda859bc05549"   # updated freeze (corrections recorded)
B7_FREEZE_BYTES = 1697
GEN_B7 = OUT / "M5C2-B7-GEN.json"
SENT_B7 = OUT / "M5C2-B7-SENTS.json"
JUDGE_PRE_SHA16 = "09d6f1b163ea0b84"

PUNCT_EXTRA = set("#*-=_`~>|+•·—–…“”‘’「」『』《》〈〉【】〔〕")
SEG_RE = re.compile(r"[^。！？\n]*[。！？]|[^。！？\n]+")
THINK_RE = re.compile(r"</?think>")
ECHO_PREFIXES = ("问：", "问:")


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def rel(p):
    try:
        return str(Path(p).relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def write_json_atomic(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def is_pure(seg):
    """True iff, after removing whitespace, only punctuation/symbols remain."""
    t = re.sub(r"\s+", "", seg)
    if not t:
        return True
    for ch in t:
        if ch in PUNCT_EXTRA:
            continue
        if unicodedata.category(ch)[0] in ("P", "S"):
            continue
        return False
    return True


def split_answer(answer):
    """Frozen split: newline+。！？ boundaries, empty/think/pure/问-echo dropped."""
    out = []
    for seg in SEG_RE.findall(str(answer or "")):
        seg = seg.strip()
        if not seg:
            continue
        if THINK_RE.search(seg):
            continue
        if is_pure(seg):
            continue
        if seg.startswith(ECHO_PREFIXES):
            continue
        out.append(seg)
    return out


def read_json(path, expect_sha16, expect_bytes, label):
    b = Path(path).read_bytes()
    if sha16(b) != expect_sha16 or len(b) != expect_bytes:
        raise SystemExit("%s changed: %s / %d B (expected %s / %d B)"
                         % (label, sha16(b), len(b), expect_sha16, expect_bytes))
    return json.loads(b.decode("utf-8")), {"path": rel(path),
                                           "sha16": expect_sha16,
                                           "bytes": len(b)}


def build_b5_doc():
    gen, gen_meta = read_json(GEN_B5, GEN_B5_SHA16, GEN_B5_BYTES,
                              "M5C2-B5-GEN.json")
    if gen.get("aborted") is not None:
        raise SystemExit("b5 GEN aborted; frozen SENTENCES cannot be rebuilt")
    qa = gen.get("qa") or []
    if len(qa) != 40 or int(gen.get("n_forward") or 0) != 40:
        raise SystemExit("b5 GEN is not 40/40; refusing the acceptance check")
    doc = {
        "schema": "m5c2_b5_sentences_v1",
        "status": "已冻结切句（judge 前）",
        "prereg_sha16": PRE_B5_SHA16,
        "gen": {
            "path": rel(GEN_B5),
            "sha16": gen_meta["sha16"],
            "bytes": gen_meta["bytes"],
            "dll": gen.get("dll"),
            "model_bytes": gen.get("model_bytes"),
            "n_gpu_layers_readback": gen.get("n_gpu_layers_readback"),
        },
        "split_rules": "PREREG-M5-C2-B5.md §4 (newline + 。！？; empty/问 echo/"
                       "pure symbols dropped)",
        "n_questions": len({q["qid"] for q in qa}),
        "n_sentences": 0,
        "sentences_nonempty": 0,
        "qids_without_sentences": [],
        "judge_layer_prereg_sha16": JUDGE_PRE_SHA16,
        "no_verdict": True,
        "no_gold": True,
        "sentences": [],
    }
    rows = []
    for q in qa:
        texts = split_answer(q.get("answer_full"))
        if not texts:
            doc["qids_without_sentences"].append(q["qid"])
        for i, t in enumerate(texts, 1):
            rows.append({"sid": "%s-s%02d" % (q["qid"], i),
                         "qid": q["qid"], "scenario": q["scenario"],
                         "source_text": q["source_text"],
                         "question": q["question"], "text": t})
    doc["sentences"] = rows
    doc["n_sentences"] = len(rows)
    doc["sentences_nonempty"] = len(rows)
    return doc, gen_meta


def check_b5():
    doc, gen_meta = build_b5_doc()
    b = (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    got = sha16(b)
    ok = got == SENT_B5_SHA16 and len(b) == SENT_B5_BYTES
    print(json.dumps({
        "schema": "m5c2_b7_split_check_b5_v1",
        "check": "rebuild frozen M5C2-B5-SENTENCES.json from M5C2-B5-GEN.json",
        "gen": gen_meta,
        "target": {"path": rel(SENT_B5), "sha16": SENT_B5_SHA16,
                   "bytes": SENT_B5_BYTES},
        "rebuilt": {"sha16": got, "bytes": len(b),
                    "n_sentences": doc["n_sentences"]},
        "identical": bool(ok),
        "n_forward": 0, "no_gpu": True, "writes_any_file": False,
    }, ensure_ascii=False, indent=1))
    return 0 if ok else 4


def gen_b7():
    b7, b7_meta = read_json(B7_IN, B7_IN_SHA16, B7_IN_BYTES,
                            "M5C2-B7-QUESTIONS.json")
    if b7.get("schema") != "m5c2_b7_questions_v1":
        raise SystemExit("unexpected b7 questions schema")
    fp = B7_FREEZE.read_bytes()
    if sha16(fp) != B7_FREEZE_SHA16 or len(fp) != B7_FREEZE_BYTES:
        raise SystemExit("b7 questions freeze pin changed: %s / %d B"
                         % (sha16(fp), len(fp)))
    fpin = json.loads(fp.decode("utf-8"))
    if not (fpin.get("frozen") is True and int(fpin.get("frozen_rev") or 0) >= 1):
        raise SystemExit("b7 questions freeze pin is not frozen")
    if ((fpin.get("questions") or {}).get("sha16") != B7_IN_SHA16):
        raise SystemExit("b7 questions freeze pin does not pin this file")
    rb = RULING.read_bytes()
    if sha16(rb) != RULING_SHA16 or len(rb) != RULING_BYTES:
        raise SystemExit("RULING-M5C2-B7 changed: %s / %d B"
                         % (sha16(rb), len(rb)))
    if not Path(GEN_B7).exists():
        raise SystemExit("missing %s; run the b7 GPU generation first"
                         % rel(GEN_B7))
    gb = Path(GEN_B7).read_bytes()
    gen = json.loads(gb.decode("utf-8"))
    if gen.get("aborted") is not None:
        raise SystemExit("b7 GEN aborted=%r; refusing to split partial output"
                         % (gen.get("aborted"),))
    qa = gen.get("qa") or []
    if len(qa) != 75 or int(gen.get("n_forward") or 0) != 75:
        raise SystemExit("b7 GEN does not hold 75/75 answers")
    doc = {
        "schema": "m5c2_b7_sents_v1",
        "status": "已切句（盲标前；未判定）",
        "prereg_path": rel(RULING),
        "prereg_sha16": RULING_SHA16,
        "one_shot": True,
        "gen": {"path": rel(GEN_B7), "sha16": sha16(gb), "bytes": len(gb),
                "dll": gen.get("dll"),
                "model_bytes": gen.get("model_bytes"),
                "n_gpu_layers_readback": gen.get("n_gpu_layers_readback")},
        "split_rules": "PREREG-M5-C2-B5.md §4 / RULING-M5C2-B7 R3 (newline + "
                       "。！？; empty/问 echo/pure symbols/think dropped)",
        "split_rules_reference": "M5C2-B5-SENTENCES.json ba92635c8ad0c410 "
                                 "(byte-identical acceptance in "
                                 "run_m5c2_b7_split.py --check-b5)",
        "n_questions": len({q["qid"] for q in qa}),
        "n_sentences": 0,
        "sentences_nonempty": 0,
        "qids_without_sentences": [],
        "judge_layer_prereg_sha16": JUDGE_PRE_SHA16,
        "no_verdict": True,
        "no_gold": True,
        "sentences": [],
    }
    rows = []
    for q in qa:
        texts = split_answer(q.get("answer_full"))
        if not texts:
            doc["qids_without_sentences"].append(q["qid"])
        for i, t in enumerate(texts, 1):
            rows.append({"sid": "%s-s%02d" % (q["qid"], i),
                         "qid": q["qid"], "scenario": q["scenario"],
                         "source_text": q["source_text"],
                         "question": q["question"], "text": t})
    doc["sentences"] = rows
    doc["n_sentences"] = len(rows)
    doc["sentences_nonempty"] = len(rows)
    write_json_atomic(SENT_B7, doc)
    b = SENT_B7.read_bytes()
    print(json.dumps({"status": "已切句", "path": rel(SENT_B7),
                      "sha16": sha16(b), "bytes": len(b),
                      "n_sentences": len(rows),
                      "qids_without_sentences": doc["qids_without_sentences"],
                      "gen_sha16": doc["gen"]["sha16"]},
                     ensure_ascii=False, indent=1))
    return 0


def dry_run():
    out = {"schema": "m5c2_b7_split_dry_run_v1", "status": "dry_run_only",
           "n_forward": 0, "no_gpu": True, "writes_any_file": False}
    b6, b6_meta = read_json(B7_IN, B7_IN_SHA16, B7_IN_BYTES,
                            "M5C2-B7-QUESTIONS.json")
    pre = RULING.read_bytes()
    fp = B7_FREEZE.read_bytes()
    out["pins"] = {
        "ruling": {"path": rel(RULING), "sha16": sha16(pre),
                   "bytes": len(pre)},
        "questions_freeze": {"path": rel(B7_FREEZE),
                             "sha16": sha16(fp), "bytes": len(fp)},
        "machine_questions": b6_meta,
        "b5_reference": {"path": rel(SENT_B5), "sha16": SENT_B5_SHA16,
                         "bytes": SENT_B5_BYTES, "n_sentences": SENT_B5_N},
        "split_acceptance": "run --check-b5 (byte-identical rebuild)",
    }
    out["questions"] = {"n_scenarios": len(b6.get("scenarios") or []),
                        "n_questions": b6.get("n_questions"),
                        "prereg_link": b6.get("prereg_sha16")}
    out["expected_inputs"] = {
        "gen": rel(GEN_B7), "sents_out": rel(SENT_B7),
        "gen_present": Path(GEN_B7).exists(),
        "sents_present": Path(SENT_B7).exists()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-b5", action="store_true")
    ap.add_argument("--gen-b7", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    modes = [m for m in (a.check_b5, a.gen_b7, a.dry_run) if m]
    if len(modes) != 1:
        print("choose exactly one of --check-b5 / --gen-b7 / --dry-run")
        return 2
    if a.check_b5:
        return check_b5()
    if a.gen_b7:
        return gen_b7()
    return dry_run()


if __name__ == "__main__":
    sys.exit(main())