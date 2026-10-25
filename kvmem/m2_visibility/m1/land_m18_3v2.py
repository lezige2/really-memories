# -*- coding: utf-8 -*-
"""M18-3 重出版（B：`prop_gated`）的留档批次 `m18-3v2`（task-20）。

替代关系：
- 旧 M18-3 规格两条改法已作废：`kvmem/m2_visibility/m1/evidence/M18-3-INVALIDATES.md`；
- 新规格：`docs/_work/INSPECTOR-M18-3-RESPEC.md`（inspector，只读，我不登记它的字节副本，只引 sha）。

本批改动只有一个文件的一处（`tools/retrieval.py` L293-300，1 hunk / +6-5），
`tools/analysis.py` 一字节未动（仍 `49e91c7bd3dd32ef`）。**本文件不登记自身 sha16**（§22.3）。
"""
import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BEFORE = os.path.join(HERE, "_before")
REGISTER = os.path.join(BEFORE, "REGISTER.json")
LANDED = os.path.join(HERE, "LANDED-m18-3v2.json")
GAP_S = 3

PRE_CHANGE = {"tools/retrieval.py": "b89fb2004f7aa69a"}

SOURCES = [
    "tools/retrieval.py",
    "tools/test_retrieval_judges.py",
    "kvmem/m2_visibility/m1/out/M18-A-pre-M18-3v2.json",
    "kvmem/m2_visibility/m1/out/M18-A-after-M18-3v2.json",
    "kvmem/m2_visibility/m1/out/M18-PROBES-after-m18-3v2.json",
    "kvmem/m2_visibility/m1/out/M18-CMP-m18-3v2-vs-prev.json",
    "kvmem/m2_visibility/m1/out/M18-CMP-m18-3v2-vs-before.json",
    "kvmem/m2_visibility/m1/out/M18-PROBES-after-M18-4.json",
    "kvmem/m2_visibility/m1/out/M18-A-after-M18-4.json",
    "kvmem/m2_visibility/m1/evidence/M18-3-INVALIDATES.md",
    "tools/analysis.py",
]

REASON = ("task-20 M18-3 重出版（B：回退例外=「属性闸门已判定」）：只改 retrieval.py L293-300 一处，"
          "A1–A17 17/17、真实库 8 条 0 worse")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""):
            h.update(c)
    return h.hexdigest()


def snap():
    out = {}
    for rel in SOURCES:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print("STOP: 缺文件 %s" % rel, file=sys.stderr)
            return None
        out[rel] = {"sha16": sha256_file(p)[:16], "sha256": sha256_file(p),
                    "bytes": os.path.getsize(p)}
    return out


def main():
    t0 = time.time()
    os.makedirs(BEFORE, exist_ok=True)

    pre = {}
    for rel, want in PRE_CHANGE.items():
        cp = os.path.join(BEFORE, "%s@%s" % (os.path.basename(rel), want))
        if not os.path.exists(cp):
            print("STOP: 缺改前副本 %s" % cp, file=sys.stderr)
            return 3
        pre[rel] = {"copy_path": cp.replace("\\", "/"),
                    "copy_sha16": sha256_file(cp)[:16],
                    "expected_sha16": want, "ok": sha256_file(cp)[:16] == want}

    s1 = snap()
    if s1 is None:
        return 3
    if s1["tools/analysis.py"]["sha16"] != "49e91c7bd3dd32ef":
        print(json.dumps({"STOP": "analysis.py sha 变了（规格 §3.3 硬性不动项）",
                          "now": s1["tools/analysis.py"]["sha16"]}, ensure_ascii=False))
        return 2

    copies, conflicts = {}, []
    for rel, info in s1.items():
        name = "%s@%s" % (os.path.basename(rel), info["sha16"])
        dst = os.path.join(BEFORE, name)
        if os.path.exists(dst):
            if sha256_file(dst) != info["sha256"]:
                conflicts.append({"rel": rel, "copy": name, "why": "同名副本字节不等，拒绝覆盖"})
                continue
        else:
            shutil.copyfile(os.path.join(ROOT, rel), dst)
        copies[rel] = {"copy_path": dst.replace("\\", "/"),
                       "copy_sha16": sha256_file(dst)[:16],
                       "byte_equal": sha256_file(dst) == info["sha256"]}
    if conflicts:
        print(json.dumps({"STOP": "副本冲突", "conflicts": conflicts}, ensure_ascii=False))
        return 2

    reg = {"rule": "any run that overwrites an accepted artifact must first copy it to "
                   "_before/<name>@<sha16>", "updated_at": None, "entries": [], "changes": []}
    if os.path.exists(REGISTER):
        reg = json.load(open(REGISTER, encoding="utf-8"))
        reg.setdefault("entries", [])
    existing = {(e.get("source_name"), e.get("source_sha16")) for e in reg["entries"]}
    added = 0
    for rel, info in s1.items():
        if (rel, info["sha16"]) in existing:
            continue
        reg["entries"].append({"source_name": rel, "source_sha16": info["sha16"],
                               "copy_path": copies[rel]["copy_path"], "in_place": False,
                               "copy_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
                               "copyist": "executor", "reason": REASON})
        added += 1
    reg["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(REGISTER, "w", encoding="utf-8", newline="\n") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)

    time.sleep(GAP_S)
    s2 = snap()
    if s2 is None:
        return 3
    identical = all(s1[k]["sha16"] == s2[k]["sha16"] for k in s1)
    if not identical:
        print(json.dumps({"STOP": "两次采样不一致"}, ensure_ascii=False))
        return 2

    a_pre = json.load(open(os.path.join(ROOT, "kvmem/m2_visibility/m1/out/M18-A-pre-M18-3v2.json"),
                           encoding="utf-8"))
    a_after = json.load(open(os.path.join(ROOT, "kvmem/m2_visibility/m1/out/M18-A-after-M18-3v2.json"),
                             encoding="utf-8"))
    cmp_prev = json.load(open(os.path.join(ROOT, "kvmem/m2_visibility/m1/out/"
                                                 "M18-CMP-m18-3v2-vs-prev.json"), encoding="utf-8"))
    probes = json.load(open(os.path.join(ROOT, "kvmem/m2_visibility/m1/out/"
                                               "M18-PROBES-after-m18-3v2.json"), encoding="utf-8"))
    spec = os.path.join(ROOT, "docs/_work/INSPECTOR-M18-3-RESPEC.md")

    landed = {
        "schema": "m18_3v2_landed_v1", "batch_id": "m18-3v2",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sample_gap_s": GAP_S, "samples": 2, "samples_identical": identical,
        "scope": "task-20 M18-3 重出版：回退路径的例外对象 =「该候选是否已由属性闸门判定」"
                 "（`prop_gated = bool(want_prop) and allowed is not None and sid in allowed`）",
        "spec": {"path": "docs/_work/INSPECTOR-M18-3-RESPEC.md",
                 "sha16": sha256_file(spec)[:16], "bytes": os.path.getsize(spec),
                 "note": "inspector 只读产出，我未改；本台账只引 sha，不复制字节"},
        "invalidates": {"path": "kvmem/m2_visibility/m1/evidence/M18-3-INVALIDATES.md",
                        "sha16": s1["kvmem/m2_visibility/m1/evidence/M18-3-INVALIDATES.md"]["sha16"],
                        "what": "旧 M18-3 两条改法（cov 分母纳入 bigrams / 只删 need=1）判作废，不再重试"},
        "supersedes_old_m18_3": True,
        "change": {"file": "tools/retrieval.py", "hunk": "L293-300 的 `if used_fallback:` 处决块",
                   "before_sha16": "b89fb2004f7aa69a", "after_sha16": s1["tools/retrieval.py"]["sha16"],
                   "diff_scope": {"hunks": 1, "added_lines": 6, "removed_lines": 5,
                                  "only_that_block": True},
                   "hard_invariants": {
                       "analysis_py_unchanged": s1["tools/analysis.py"]["sha16"] == "49e91c7bd3dd32ef",
                       "thresholds_untouched": {"GATE": 1.30, "COV_MIN": 0.35,
                                                "REL_CUT": 0.55, "ABS_CUT": 1.10},
                       "need2_kept_on_value_gate_path": True,
                       "cov_denominator_untouched": True,
                       "index_version_and_analysis_version_untouched": True}},
        "assertions": {"before": {"pass": a_pre["n_pass"], "total": len(a_pre["cases"]),
                                  "fail": a_pre["fail_ids"],
                                  "product": "kvmem/m2_visibility/m1/out/M18-A-pre-M18-3v2.json"},
                       "after": {"pass": a_after["n_pass"], "total": len(a_after["cases"]),
                                 "fail": a_after["fail_ids"],
                                 "product": "kvmem/m2_visibility/m1/out/M18-A-after-M18-3v2.json",
                                 "note": "A8/A12/A15 三条改前红、改后绿 ⇒ 新断言承重；A14 命门绿"},
                       "new_cases": ["A12", "A13", "A14", "A15", "A16", "A17"]},
        "real_probes": {
            "vs_previous_step": {"compare": "kvmem/m2_visibility/m1/out/M18-CMP-m18-3v2-vs-prev.json",
                                 "better": cmp_prev["counts"]["better"],
                                 "same": cmp_prev["counts"]["same"],
                                 "worse": cmp_prev["counts"]["worse"],
                                 "no_worse": cmp_prev["no_worse"],
                                 "per_probe": [{"id": r["id"], "query": r["query"],
                                                "before": (r["before"]["top"] or {}).get("id"),
                                                "after": (r["after"]["top"] or {}).get("id"),
                                                "verdict": r["verdict"]} for r in cmp_prev["rows"]]},
            "product": "kvmem/m2_visibility/m1/out/M18-PROBES-after-m18-3v2.json",
            "checks": {"P2_top": 5, "P4": "ABSTAIN", "P8": "ABSTAIN"}},
        "files": {rel: {"sha16": i["sha16"], "bytes": i["bytes"]} for rel, i in s1.items()},
        "pre_change_copies": pre,
        "freeze_check": {"status": "已知可解释红（lead 裁：不 bump，M1.8 收口一次性 re-freeze）",
                         "observed": "analysis.py 9b9368524422f352 -> 49e91c7bd3dd32ef；"
                                     "retrieval.py c8e9e332ef8fd367 -> %s" % s1["tools/retrieval.py"]["sha16"]},
        "status_claim": "M18-3 重出版已落地（executor 自报：A1–A17 17/17、真实库 8 条 0 worse）；"
                        "**不声称 M1.8 已验收**（验收=inspector 复核 A1–A17 + 真实库不变差，另轮）",
        "copies": copies,
        "register": {"path": REGISTER.replace("\\", "/"),
                     "entries_total_at_sampling": len(reg["entries"]),
                     "entries_added": added, "copyist": "executor"},
        "self_registration": "本文件不登记自身 sha16（自指恒假，RESULTS-RED.md §22.3）",
        "elapsed_s": round(time.time() - t0, 2),
    }
    with open(LANDED, "w", encoding="utf-8", newline="\n") as f:
        json.dump(landed, f, ensure_ascii=False, indent=1)
    print(json.dumps({"landed": os.path.basename(LANDED), "files": len(landed["files"]),
                      "entries_total": len(reg["entries"]), "added": added,
                      "samples_identical": identical,
                      "assertions": "%d/%d" % (a_after["n_pass"], len(a_after["cases"])),
                      "probes": {"better": cmp_prev["counts"]["better"],
                                 "same": cmp_prev["counts"]["same"],
                                 "worse": cmp_prev["counts"]["worse"]}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())