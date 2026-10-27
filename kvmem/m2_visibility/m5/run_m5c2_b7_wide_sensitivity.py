#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M5C2 B7' wide-reading sensitivity pass (CPU-only, no GPU, no network).

Derived from the clean-blind rev7.2 implementation
(`run_m5c2_rev7_2_offline_cleanblind.py`), but ONLY the DECLARED reading
B = "任意子串包含" is kept: evidence (R3-normalized) occurs as a contiguous
substring of the answer sentence; when such answer-sentence-only evidence
cannot be located in the source, the item is re-grounded by relocating the item
in the source, and failure yields the fourth state `ungrounded` (U1: no absent /
no fabricated penalty; U2: all-ungrounded sentence => not-supported).

Purpose: for b7' report the B-reading verdicts side by side with the narrow
reading, and diff them against the b7 DECIDE artifact when it exists.

CLI:
  --extract PATH    b7 extract (default out/M5C2-B7-EXTRACT.json)
  --out PATH        output artifact (default out/M5C2-B7-WIDE-SENSITIVITY.json)
  --decide PATH     b7 decide artifact for per-sentence diff
                    (default out/M5C2-B7-DECIDE.json; missing => pending)
  --expected-sha16  optional: enforce extract sha16 (omit for fixtures)
  --allow-missing-input  write a pending artifact instead of failing when the
                    extract is absent (exit 4 either way; --force-exit0 to 0)

Output schema `m5c2_b7_wide_sensitivity_v1`:
  reading (declaration B), inputs (extract sha16/bytes, decide state),
  verdicts (sid -> verdict), verdict_map_sha16 (canonical), counts (four states),
  diff_vs_decide (pending | computed: n_diff/diff_sids/detail), discipline.

Exit codes: 0 success; 2 bad args; 3 malformed extract; 4 extract missing.
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
sys.path.insert(0, str(M5))

import run_m5c2_rev5_offline as R5      # noqa: E402
import run_m5c2_rev5_1_offline as R51   # noqa: E402

R41 = R5.R41

DEFAULT_EXTRACT = OUT / "M5C2-B7-EXTRACT.json"
DEFAULT_OUT = OUT / "M5C2-B7-WIDE-SENSITIVITY.json"
DEFAULT_DECIDE = OUT / "M5C2-B7-DECIDE.json"

READING = "B"

# --- frozen rule constants (same as rev7.1 / cleanblind) -------------------
PURE_PATTERNS = [
    r"\d+(?:\.\d+)?\s*(?:元|度|M|G|层|楼|排|号|节|个月|年|月|日)",
    r"下?(?:周|星期)[一二三四五六日天]",
    r"\d+月\d+日",
    r"[A-Z]{2,}-\d{3,}",
]
ENTITY_PATTERN = (r"(?:(?:是|叫|为|在|到)\s*)?"
                  r"([^\s，。是叫为在的]{2,8}(?:公司|店|院|馆|中心|银行|医院|学院|酒店|机场))")
FILLER_CHARS = "的是"
FILLER_WINDOW = 6
TRAILING_PUNCT = "。．.！？!?；;…—,，、"
_ASCII_ALNUM = re.compile(r"[0-9A-Za-z]")


def sha16(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def write_json_atomic(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(tmp, path)


def _anchor_spans(s):
    spans = []
    for pat in PURE_PATTERNS:
        for m in re.finditer(pat, s):
            spans.append(m.span())
    for m in re.finditer(ENTITY_PATTERN, s):
        if m.group(1):
            spans.append(m.span(1))
    for m in re.finditer(r"\d+", s):
        spans.append(m.span())
    return spans


def norm_r3(s):
    """R3 (M1): NFKC -> thousands -> N-4' narrow {的,是} deletion -> whitespace."""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"(?<=\d)[,，](?=\d{3})", "", s)
    spans = _anchor_spans(s)
    if spans:
        drop = set()
        for a, b in spans:
            for i in range(max(0, a - FILLER_WINDOW), min(len(s), b + FILLER_WINDOW + 1)):
                if s[i] in FILLER_CHARS:
                    drop.add(i)
        if drop:
            s = "".join(ch for i, ch in enumerate(s) if i not in drop)
    return re.sub(r"\s+", "", s)


def value_tokens(entry):
    toks, seen = [], []
    for pat in PURE_PATTERNS:
        for m in re.finditer(pat, entry or ""):
            t = m.group(0).strip()
            if t and t not in seen:
                seen.append(t)
                toks.append((t, "pure"))
    for m in re.finditer(ENTITY_PATTERN, entry or ""):
        t = (m.group(1) or "").strip()
        if t and t not in seen:
            seen.append(t)
            toks.append((t, "entity"))
    return toks


def matcher(item, sentence):
    a, b = norm_r3(item), norm_r3(sentence)
    if a and a in b:
        return "substring", 1.0
    cov = R5.window_coverage(a, b)
    return ("window" if cov >= 0.90 else "none"), cov


def r1_r2_r3(entry, evidence, source, valid):
    hits = []
    ev, ent, src = norm_r3(evidence), norm_r3(entry), norm_r3(source)
    toks = value_tokens(entry)
    for tok, kind in toks:
        tn = norm_r3(tok)
        participates = not (kind == "entity" and tn not in src)
        cov = R41.fuzzy_coverage(tn, ev) if tn else 0.0
        if participates and cov < 0.80:
            hits.append({"rule": "R1", "reason": "value_mismatch", "span": tok})
    anchors = []
    for a in [t for t, _ in toks] + [ent]:
        a = norm_r3(a)
        if a and a not in anchors:
            anchors.append(a)
    r2_done = False
    for anchor in anchors:
        if r2_done or not anchor:
            continue
        for m in re.finditer(re.escape(anchor), ev):
            i = m.start()
            before = ev[max(0, i - 6):i]
            neg = [w for w in R5.NEG_WORDS if w in before]
            if neg:
                hits.append({"rule": "R2", "reason": "negated",
                             "span": ev[max(0, i - 8):i + len(anchor) + 8],
                             "anchor": anchor, "before": before,
                             "neg_word": sorted(neg, key=len, reverse=True)[0]})
                r2_done = True
                break
            pat = re.compile(r"(不是|并非|而不是)\s*" + re.escape(anchor))
            mt = pat.search(ev)
            if mt:
                hits.append({"rule": "R2", "reason": "negated_pattern",
                             "span": mt.group(0), "anchor": anchor})
                r2_done = True
                break
            pat2 = re.compile(re.escape(anchor) + r"\s*(不是|是错的)")
            mt2 = pat2.search(ev)
            if mt2:
                hits.append({"rule": "R2", "reason": "negated_after",
                             "span": mt2.group(0), "anchor": anchor})
                r2_done = True
                break
    r3 = None
    if valid:
        for marker in R5.ABSENT_MARKERS:
            if norm_r3(marker) in ev:
                r3 = marker
                hits.append({"rule": "R3", "reason": "absent_marker", "span": marker})
                break
    return hits, r3


def r4_plus(evidence, source, has_r3):
    if has_r3:
        return None
    ev, src = norm_r3(evidence), norm_r3(source)
    if not ev:
        return {"rule": "R4+", "reason": "fabricated_evidence", "span": "(empty)",
                "metric": "empty", "jaccard_or_bigram": 0.0}
    if ev in src:
        return None
    if len(ev) <= 4:
        j = R51.max_window_jaccard(ev, src)
        if j >= 0.80:
            return None
        return {"rule": "R4+", "reason": "fabricated_evidence", "span": evidence,
                "metric": "char_jaccard", "jaccard_or_bigram": round(j, 6)}
    cov = R5.window_coverage(ev, src)
    if cov >= 0.80:
        return None
    return {"rule": "R4+", "reason": "fabricated_evidence", "span": evidence,
            "metric": "bigram", "jaccard_or_bigram": round(cov, 6)}


def is_answer_evidence(evidence, sentence):
    """Reading B: evidence occurs as a contiguous substring of the answer sentence."""
    ev, ans = norm_r3(evidence), norm_r3(sentence)
    return bool(ev) and ev in ans


def item_in_source(item, source):
    it, src = norm_r3(item), norm_r3(source)
    if not it or it not in src:
        return False
    start = 0
    while True:
        i = src.find(it, start)
        if i < 0:
            return False
        left_ok = (not _ASCII_ALNUM.match(it[0])
                   or i == 0 or not _ASCII_ALNUM.match(src[i - 1]))
        j = i + len(it)
        right_ok = (not _ASCII_ALNUM.match(it[-1])
                    or j >= len(src) or not _ASCII_ALNUM.match(src[j]))
        if left_ok and right_ok:
            return True
        start = i + 1


def judge_item(item, evidence, source, sentence):
    mh, cov = matcher(item, sentence)
    if mh == "none":
        return {"item": item, "valid": False, "absent": False,
                "item_verdict": "invalid", "matcher_hit": mh,
                "coverage": round(cov, 6), "rule_hits": [], "override": False,
                "relocated": False, "ungrounded": False}
    in_src = item_in_source(item, source)
    answer_ev = is_answer_evidence(evidence, sentence)
    ev_in_src = bool(norm_r3(evidence)) and norm_r3(evidence) in norm_r3(source)
    hits, r3 = r1_r2_r3(item, evidence, source, True)
    override = False
    if r3 is not None and in_src and not answer_ev:
        hits = [h for h in hits if h["rule"] != "R3"]
        r3 = None
        override = True
    if answer_ev and not ev_in_src:
        if hits:
            verdict = "absent"
        elif in_src:
            verdict = "present"
        else:
            verdict = "ungrounded"
        return {"item": item, "valid": True, "absent": verdict == "absent",
                "item_verdict": verdict, "matcher_hit": mh,
                "coverage": round(cov, 6), "rule_hits": hits,
                "override": override, "relocated": verdict == "present",
                "ungrounded": verdict == "ungrounded"}
    if override:
        return {"item": item, "valid": True, "absent": False,
                "item_verdict": "present", "matcher_hit": mh,
                "coverage": round(cov, 6), "rule_hits": hits,
                "override": True, "relocated": False, "ungrounded": False}
    r4 = r4_plus(evidence, source, r3 is not None)
    if r4:
        hits.append(r4)
    absent = bool(hits)
    return {"item": item, "valid": True, "absent": absent,
            "item_verdict": "absent" if absent else "present",
            "matcher_hit": mh, "coverage": round(cov, 6),
            "rule_hits": hits, "override": False, "relocated": False,
            "ungrounded": False}


def judge_sentence(rec):
    sentence = rec.get("text") or rec.get("sentence") or ""
    source = rec.get("source_text") or ""
    items = rec.get("items") or []
    item_recs = [judge_item(z.get("item", ""), z.get("evidence", ""), source, sentence)
                 for z in items]
    en, _dd = R5.derived_plus(sentence, source)
    if not rec.get("parse_ok"):
        verdict = "parse_fail"
    elif rec.get("route") == "empty_source":
        verdict = "unsupported"
    elif rec.get("route") == "abstain_check" and isinstance(rec.get("layer0"), dict):
        verdict = rec["layer0"].get("verdict", "undecidable")
    elif en:
        verdict = "undecidable"
    elif not item_recs:
        verdict = "undecidable"
    elif any(z["absent"] for z in item_recs):
        verdict = "unsupported"
    else:
        participants = [z for z in item_recs if z["valid"]]
        if participants and all(z["item_verdict"] == "ungrounded" for z in participants):
            verdict = "unsupported"
        else:
            verdict = "supported"
    return {"sid": rec["sid"], "verdict": verdict,
            "n_items": len(item_recs),
            "n_invalid": sum(1 for z in item_recs if z["item_verdict"] == "invalid"),
            "n_absent": sum(1 for z in item_recs if z["item_verdict"] == "absent"),
            "n_ungrounded": sum(1 for z in item_recs if z["item_verdict"] == "ungrounded"),
            "n_present": sum(1 for z in item_recs if z["item_verdict"] == "present"),
            "n_override": sum(1 for z in item_recs if z["override"]),
            "items": item_recs}


def canonical_map_sha16(mapping):
    blob = json.dumps(mapping, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def load_extract(path: Path, expected_sha16=None):
    raw = path.read_bytes()
    got = sha16(raw)
    if expected_sha16 and got != expected_sha16:
        raise ValueError("extract sha16 mismatch: %s != %s" % (got, expected_sha16))
    doc = json.loads(raw.decode("utf-8"))
    recs = doc.get("records") or doc.get("sentences") or []
    if not isinstance(recs, list) or not recs:
        raise ValueError("extract has no records[]")
    for r in recs:
        if not isinstance(r, dict) or "sid" not in r:
            raise ValueError("malformed record: %r" % (r,))
    return doc, recs, raw


def extract_verdict_map(doc):
    if isinstance(doc, dict):
        for key in ("verdicts", "verdict_map", "sid_to_verdict", "map"):
            val = doc.get(key)
            if isinstance(val, dict):
                out = {}
                for sid, v in val.items():
                    out[sid] = v if isinstance(v, str) else (
                        v.get("verdict") if isinstance(v, dict) else None)
                return out
        direct = {k: v for k, v in doc.items() if isinstance(v, str) and k.startswith("b7-")}
        if direct:
            return direct
        recs = doc.get("records") or doc.get("sentences")
        if isinstance(recs, list):
            out = {}
            for rec in recs:
                if isinstance(rec, dict) and "sid" in rec:
                    out[rec["sid"]] = rec.get("verdict") or rec.get("verdict_rev7_2")
            return out
    return {}


def diff_maps(a, b):
    sids = sorted(set(a) | set(b))
    diffs = [sid for sid in sids if a.get(sid) != b.get(sid)]
    return {"n_diff": len(diffs), "diff_sids": diffs,
            "detail": [{"sid": sid, "wide_B": a.get(sid), "decide": b.get(sid)}
                       for sid in diffs]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="b7' wide-reading (B) sensitivity pass")
    ap.add_argument("--extract", default=str(DEFAULT_EXTRACT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--decide", default=str(DEFAULT_DECIDE))
    ap.add_argument("--expected-sha16", default=None)
    ap.add_argument("--allow-missing-input", action="store_true")
    ap.add_argument("--force-exit0", action="store_true")
    args = ap.parse_args(argv)

    extract_path = Path(args.extract)
    out_path = Path(args.out)
    decide_path = Path(args.decide)

    artifact = {
        "schema": "m5c2_b7_wide_sensitivity_v1",
        "role": "b7' side-by-side wide-reading (B) verdicts, derived from the clean-blind rev7.2 implementation",
        "reading": {
            "declared": READING,
            "label": "B = 任意子串包含（evidence 归一化后是答案句的连续子串；整句相等为特例）",
            "basis": [
                "R5′ 原文用 ⊂（包含）：evidence 作为答案句的连续子串即视为答案句证据；"
                "第四态措辞“仅出现在答案句”覆盖截短引用。",
                "R4 的“evidence 非答案句”使用同一包含谓词；据此，答案句片段不触发 override。",
                "该读法与 narrow（A=去尾标点整句相等）并列报告；b5 上 A 复现 DEV diff=0、B diff=2"
                "（见 out/M5C2-REV7-2-CLEANBLIND-DECISION.json）。",
            ],
        },
        "inputs": {
            "extract": {"path": str(extract_path), "sha16": None, "bytes": None,
                        "n_records": 0},
            "decide": {"path": str(decide_path), "state": "pending"},
        },
        "verdicts": {},
        "verdict_map_sha16": None,
        "counts": {},
        "diff_vs_decide": {"state": "pending"},
        "discipline": {"zero_gpu": True, "no_network": True, "no_gold_read": True,
                       "no_blind_label_read": True, "frozen_inputs_untouched": True,
                       "files_written": [str(out_path)]},
    }

    if not extract_path.exists():
        artifact["inputs"]["extract"]["path"] = str(extract_path)
        artifact["status"] = "pending_extract"
        artifact["note"] = ("b7 extract 尚未产出；本文件为 pending 占位。"
                            "生成后用同一命令重跑即可填 verdicts/diff。")
        write_json_atomic(out_path, artifact)
        print(json.dumps({"status": "pending_extract", "out": str(out_path),
                          "extract": str(extract_path)}, ensure_ascii=False))
        return 0 if args.force_exit0 else 4

    try:
        doc, recs, raw = load_extract(extract_path, args.expected_sha16)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "bad_extract", "error": str(exc)}, ensure_ascii=False))
        return 3

    records = [judge_sentence(r) for r in recs]
    vmap = {r["sid"]: r["verdict"] for r in records}
    counts = {}
    for v in vmap.values():
        counts[v] = counts.get(v, 0) + 1
    artifact["status"] = "computed"
    artifact["inputs"]["extract"].update({"sha16": sha16(raw), "bytes": len(raw),
                                          "n_records": len(recs)})
    artifact["verdicts"] = vmap
    artifact["verdict_map_sha16"] = canonical_map_sha16(vmap)
    artifact["counts"] = dict(sorted(counts.items()))
    artifact["item_stats"] = {
        "n_items": sum(r["n_items"] for r in records),
        "n_invalid": sum(r["n_invalid"] for r in records),
        "n_absent": sum(r["n_absent"] for r in records),
        "n_ungrounded": sum(r["n_ungrounded"] for r in records),
        "n_present": sum(r["n_present"] for r in records),
        "n_override": sum(r["n_override"] for r in records),
    }
    artifact["records"] = records

    if decide_path.exists():
        decide_raw = decide_path.read_bytes()
        decide_doc = json.loads(decide_raw.decode("utf-8"))
        decide_map = extract_verdict_map(decide_doc)
        artifact["inputs"]["decide"] = {
            "path": str(decide_path), "state": "computed",
            "sha16": sha16(decide_raw), "bytes": len(decide_raw),
        }
        artifact["diff_vs_decide"] = {"state": "computed", **diff_maps(vmap, decide_map)}
    else:
        artifact["diff_vs_decide"] = {
            "state": "pending",
            "note": "b7 DECIDE 尚未产出；产出后用同一命令重跑即补 diff。",
        }

    write_json_atomic(out_path, artifact)
    summary = {
        "status": "computed",
        "out": str(out_path),
        "extract_sha16": sha16(raw),
        "n_records": len(recs),
        "counts": artifact["counts"],
        "verdict_map_sha16": artifact["verdict_map_sha16"],
        "diff_vs_decide": (artifact["diff_vs_decide"].get("state")
                           if isinstance(artifact["diff_vs_decide"], dict) else None),
    }
    if artifact["diff_vs_decide"].get("state") == "computed":
        summary["diff_n"] = artifact["diff_vs_decide"]["n_diff"]
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())