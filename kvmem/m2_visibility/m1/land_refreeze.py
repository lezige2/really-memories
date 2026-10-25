# -*- coding: utf-8 -*-
"""M1.8 收口 re-freeze 台账（task-22）：`freeze_check.py` 选择层基线 + A11 锚同批更新。

三条硬纪律：
1. **不靠改断言换绿**：A11 的 `anchors["freeze_check.py"]` 是「期望值随 re-freeze 更新」，
   台账必须明写；另附 A11 **承重自证**（把锚回退到旧值 ⇒ A11 必红，产物 `M18-A11-redproof.json`）。
2. 阈值 / 版本 / 索引 / 库 / 选择层代码一律不动，只动那两处常量。
3. 本文件不登记自身 sha16（§22.3）。
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
LANDED = os.path.join(HERE, "LANDED-refreeze.json")
GAP_S = 3

OLD = {"tools/freeze_check.py": "8decec8a4715bc8b",
       "tools/test_retrieval_judges.py": "be3d93bfca7bc39d"}
NEW_EXPECT = {"tools/freeze_check.py": "6016085a05890581",
              "tools/test_retrieval_judges.py": "73053556db580d50"}

SOURCES = [
    "tools/freeze_check.py",
    "tools/test_retrieval_judges.py",
    "tools/analysis.py",            # 只引，不改（re-freeze 只承认它的新 sha）
    "tools/retrieval.py",
    "tools/evidence.py",
    "tools/eval_heldout.py",
    "kvmem/m2_visibility/m1/out/M18-A-after-refreeze.json",
    "kvmem/m2_visibility/m1/out/M18-A11-redproof.json",
]

REASON = ("task-22 M1.8 收口 re-freeze：经 inspector 复核 M18-1..M18-4 后按判据更新选择层基线；"
          "阈值与版本未变、无索引重建")


def sha256_file(p):
    with open(p, "rb") as f:                       # 二进制读，不过文本层
        return hashlib.sha256(f.read()).hexdigest()


def snap():
    out = {}
    for rel in SOURCES:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print("STOP: 缺文件 %s" % rel, file=sys.stderr)
            return None
        h = sha256_file(p)
        out[rel] = {"sha16": h[:16], "sha256": h, "bytes": os.path.getsize(p)}
    return out


def main():
    t0 = time.time()
    os.makedirs(BEFORE, exist_ok=True)

    # ① 改前副本自证（已在施工时落，这里只核字节相等）
    pre = {}
    for rel, want in OLD.items():
        cp = os.path.join(BEFORE, "%s@%s" % (os.path.basename(rel), want))
        if not os.path.exists(cp):
            print("STOP: 缺改前副本 %s" % cp, file=sys.stderr)
            return 3
        pre[rel] = {"copy_path": cp.replace("\\", "/"), "copy_sha16": sha256_file(cp)[:16],
                    "expected_sha16": want, "byte_equal": sha256_file(cp)[:16] == want}
        if not pre[rel]["byte_equal"]:
            print("STOP: 改前副本字节不等 %s" % rel, file=sys.stderr)
            return 2

    s1 = snap()
    if s1 is None:
        return 3
    for rel, want in NEW_EXPECT.items():
        if s1[rel]["sha16"] != want:
            print(json.dumps({"STOP": "sha 与施工时不符", "file": rel,
                              "want": want, "got": s1[rel]["sha16"]}, ensure_ascii=False))
            return 2
    hard = {"analysis.py": "49e91c7bd3dd32ef", "retrieval.py": "43f660196ab90a14",
            "evidence.py": "dccf7f010eaf9c7e", "eval_heldout.py": "597fd0ca671e898e"}
    for name, want in hard.items():
        got = s1["tools/" + name]["sha16"]
        if got != want:
            print(json.dumps({"STOP": "硬性不动项变了", "file": name, "want": want, "got": got},
                             ensure_ascii=False))
            return 2

    # ② 新产物字节副本入 _before + REGISTER
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

    # ③ 两采样一致
    time.sleep(GAP_S)
    s2 = snap()
    if s2 is None:
        return 3
    identical = all(s1[k]["sha16"] == s2[k]["sha16"] for k in s1)
    if not identical:
        print(json.dumps({"STOP": "两次采样不一致"}, ensure_ascii=False))
        return 2

    a = json.load(open(os.path.join(ROOT, "kvmem/m2_visibility/m1/out/M18-A-after-refreeze.json"),
                       encoding="utf-8"))
    a11 = [c for c in a["cases"] if c["id"] == "A11"][0]
    proof = json.load(open(os.path.join(ROOT, "kvmem/m2_visibility/m1/out/M18-A11-redproof.json"),
                           encoding="utf-8"))
    pa11 = [c for c in proof["cases"] if c["id"] == "A11"][0]
    if not (a["n_pass"] == 17 and not a["fail_ids"]):
        print(json.dumps({"STOP": "A 重跑不是 17/17", "n_pass": a["n_pass"],
                          "fail_ids": a["fail_ids"]}, ensure_ascii=False))
        return 2
    if pa11["pass"] is not False:
        print(json.dumps({"STOP": "A11 承重自证没红"}, ensure_ascii=False))
        return 2

    landed = {
        "schema": "m18_refreeze_landed_v1", "batch_id": "m18-refreeze",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sample_gap_s": GAP_S, "samples": 2, "samples_identical": identical,
        "scope": "M1.8 收口后的一次性 re-freeze：只承认选择层新基线（analysis/retrieval），"
                 "并把 A11 的 freeze_check 锚同批更新",
        "verdict_doc": {"path": "docs/_work/M1.8-VERDICT-lead.md",
                        "sha16": "3d45eec5d9bb17f6", "note": "lead 判决；只引 sha，不复制"},
        "changes": [
            {"file": "tools/freeze_check.py", "what": "FROZEN 的两个选择层摘要",
             "old": OLD["tools/freeze_check.py"], "new": NEW_EXPECT["tools/freeze_check.py"],
             "detail": {"analysis.py": ["9b9368524422f352", "49e91c7bd3dd32ef"],
                        "retrieval.py": ["c8e9e332ef8fd367", "43f660196ab90a14"],
                        "evidence.py": "dccf7f010eaf9c7e（未变）"}},
            {"file": "tools/test_retrieval_judges.py", "what": "A11 的 anchors 字典",
             "old": OLD["tools/test_retrieval_judges.py"], "new": NEW_EXPECT["tools/test_retrieval_judges.py"],
             "detail": {"freeze_check.py": ["8decec8a4715bc8b", NEW_EXPECT["tools/freeze_check.py"]],
                        "eval_heldout.py": "597fd0ca671e898e（未变）"}},
        ],
        "reason": REASON,
        "A11_anchor_updated": True,
        "A11_anchor_note": "**期望值随 re-freeze 更新**：A11 锚的是 `freeze_check.py` 自身的字节；"
                           "freeze_check.py 按本单要求改了 ⇒ 锚必须同批改，否则 A11 必红、"
                           "17/17 会变成「改断言换来的假绿」。阈值断言（GATE/COV_MIN/REL_CUT）"
                           "与 `eval_heldout.py` 锚**一字未动**。",
        "A11_anchors": {"old": {"freeze_check.py": "8decec8a4715bc8b",
                                "eval_heldout.py": "597fd0ca671e898e"},
                        "new": {"freeze_check.py": NEW_EXPECT["tools/freeze_check.py"],
                                "eval_heldout.py": "597fd0ca671e898e"}},
        "A11_load_bearing_proof": {
            "product": "kvmem/m2_visibility/m1/out/M18-A11-redproof.json",
            "method": "在系统临时目录复制现态 tools/ 6 件，只把 A11 锚回退成旧值 "
                      "`8decec8a4715bc8b`（其余全是现态字节），跑整套断言",
            "result": {"A11_pass": pa11["pass"], "fail_ids": proof["fail_ids"],
                       "exit": proof["exit"],
                       "anchor_files_seen": pa11["detail"]["anchor_files"]},
            "conclusion": "旧锚在现态 `freeze_check.py`（6016085a05890581）上必红 ⇒ A11 承重成立，"
                          "17/17 不是把断言放宽换来的"},
        "freeze_check": {"output": "SELECTION LAYER: FROZEN (3 files, 3 thresholds, versions "
                                   "{'INDEX_VERSION': 5, 'ANALYSIS_VERSION': 4})",
                         "exit": 0, "frozen_files": 3,
                         "frozen_thresholds": {"GATE": 1.30, "COV_MIN": 0.35, "REL_CUT": 0.55},
                         "frozen_versions": {"INDEX_VERSION": 5, "ANALYSIS_VERSION": 4}},
        "assertions": {"product": "kvmem/m2_visibility/m1/out/M18-A-after-refreeze.json",
                       "pass": a["n_pass"], "total": len(a["cases"]), "fail": a["fail_ids"],
                       "a11_detail_thresholds_now": a11["detail"]["thresholds_now"],
                       "a11_anchor_files_now": a11["detail"]["anchor_files"]},
        "hard_invariants": {
            "thresholds_untouched": True,
            "versions_untouched": True,
            "chat_db_untouched": "kvmem/chat.db 237d8e1f5de9a382（本单未读写）",
            "selection_code_untouched": True,
            "index_rebuilt": False,
        },
        "files": {rel: {"sha16": i["sha16"], "bytes": i["bytes"]} for rel, i in s1.items()},
        "pre_change_copies": pre,
        "copies": copies,
        "register": {"path": REGISTER.replace("\\", "/"),
                     "entries_total_at_sampling": len(reg["entries"]),
                     "entries_added": added, "copyist": "executor"},
        "self_registration": "本文件不登记自身 sha16（自指恒假，RESULTS-RED.md §22.3）",
        "status_claim": "re-freeze 已落地：`freeze_check` FROZEN/exit 0、A1–A17 仍 17/17、"
                        "A11 锚同批更新且有承重自证；**不声称 M1.8 由此重新验收**（已由 lead 签）",
        "elapsed_s": round(time.time() - t0, 2),
    }
    with open(LANDED, "w", encoding="utf-8", newline="\n") as f:
        json.dump(landed, f, ensure_ascii=False, indent=1)
    print(json.dumps({"landed": os.path.basename(LANDED), "files": len(landed["files"]),
                      "entries_total": len(reg["entries"]), "added": added,
                      "samples_identical": identical, "assertions": "%d/%d"
                      % (a["n_pass"], len(a["cases"])), "freeze_exit": 0,
                      "a11_redproof": "ok"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())