# -*- coding: utf-8 -*-
"""M1.8（task-17）留档批次 `m18`：已落的 M18-2/M18-1 + 全部证据，**不含未落地步骤**。

台账纪律：
- 每个源文件先 `_before/<name>@<sha16>` 逐字节留档，再登 REGISTER（去重追加）；
- 两采样（间隔 3 s）sha 必须一致；
- 本文件不登记自身 sha16（自指恒假，RESULTS-RED.md §22.3）；
- `steps[]` 里 `landed=false` 的条目**只作证据索引**，不表示已落地。
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
LANDED = os.path.join(HERE, "LANDED-m18.json")
GAP_S = 3

SOURCES = [
    "tools/analysis.py",
    "tools/retrieval.py",
    "tools/test_retrieval_judges.py",
    "kvmem/m2_visibility/m1/probe_m18_8.py",
    "kvmem/m2_visibility/m1/evidence/M18-2-analysis.patch",
    "kvmem/m2_visibility/m1/evidence/M18-1-retrieval.patch",
    "kvmem/m2_visibility/m1/evidence/M18-3-literal-cov+need2.patch",
    "kvmem/m2_visibility/m1/evidence/M18-3-need2-only.patch",
    "kvmem/m2_visibility/m1/out/M18-A-before.json",
    "kvmem/m2_visibility/m1/out/M18-A-after-M18-2.json",
    "kvmem/m2_visibility/m1/out/M18-A-after-M18-1.json",
    "kvmem/m2_visibility/m1/out/M18-A-after-M18-3.json",
    "kvmem/m2_visibility/m1/out/M18-A-after-M18-3b.json",
    "kvmem/m2_visibility/m1/out/M18-A-final-M18-2-1.json",
    "kvmem/m2_visibility/m1/out/M18-PROBES-before.json",
    "kvmem/m2_visibility/m1/out/M18-PROBES-after-M18-2.json",
    "kvmem/m2_visibility/m1/out/M18-PROBES-after-M18-1.json",
    "kvmem/m2_visibility/m1/out/M18-PROBES-after-M18-3.json",
    "kvmem/m2_visibility/m1/out/M18-PROBES-final-M18-2-1.json",
    "kvmem/m2_visibility/m1/out/M18-CMP-M18-2.json",
    "kvmem/m2_visibility/m1/out/M18-CMP-M18-1.json",
    "kvmem/m2_visibility/m1/out/M18-CMP-M18-3.json",
    "kvmem/m2_visibility/m1/out/M18-CMP-final-M18-2-1.json",
    "kvmem/m2_visibility/m1/out/M18-CMP-step3-vs-step2.json",
    "kvmem/m2_visibility/m1/out/M18-A-baseline-recheck.json",
    "kvmem/m2_visibility/m1/out/M18-A-after-M18-4.json",
    "kvmem/m2_visibility/m1/out/M18-PROBES-after-M18-4.json",
    "kvmem/m2_visibility/m1/out/M18-CMP-after-M18-4-vs-before.json",
    "kvmem/m2_visibility/m1/out/M18-CMP-M18-4-vs-step2.json",
    "kvmem/m2_visibility/m1/evidence/M18-4-keep-or-top1.patch",
    "kvmem/m2_visibility/m1/evidence/M18-3-INVALIDATES.md",
    "kvmem/m2_visibility/m1/evidence/P1-gap.md",
]

REASON = ("task-17 M1.8 施工：M18-2（analysis.py 作用域/锚定收紧+补漏）与 M18-1（属性闸门为权威）"
          "已落地；M18-3/M18-4 未落地（见 steps 与说明）")

STEPS = [
    {"id": "M18-2", "landed": True, "direction": "收紧+补漏", "file": "tools/analysis.py",
     "before_sha16": "9b9368524422f352", "after_sha16": None,
     "lead_signed": "2026-10-25T19:40+08:00",
     "changed": ["PROPERTIES: height 补『身高 裸数字』", "PROPERTIES: birthday 补相对日期（下周三）",
                 "PROPERTIES: address 的 scs 由 None 改 (住,地址,家)",
                 "property_holds: 无锚兜底由 True 改 False"],
     "assertions": {"before": "A4/A6/A7 RED", "after": "A4/A6/A7 GREEN（A2/A5/A9 无回归）"},
     "real_probes": {"compare": "out/M18-CMP-M18-2.json", "better": 3, "worse": 0}},
    {"id": "M18-1", "landed": True, "direction": "放松（属性闸门为权威）", "file": "tools/retrieval.py",
     "before_sha16": "c8e9e332ef8fd367", "after_sha16": "ac6ea8ccee09173b",
     "lead_signed": "2026-10-25T19:40+08:00",
     "changed": ["_search_one: 进候选条件加 `or (want_prop and sid in allowed)`",
                 "_passes: 加 `or bool(signals['prop'])`",
                 "keep: 空时保底（本步先写成 want_prop 守卫，M18-4 改为无条件）"],
     "assertions": {"before": "A1/A3 RED", "after": "A1/A3 GREEN（其余无回归）"},
     "real_probes": {"compare": "out/M18-CMP-M18-1.json", "better": 3, "worse": 0}},
    {"id": "M18-3", "landed": False, "invalidated": True, "direction": "收紧（规格作废，待重出）",
     "file": "tools/retrieval.py",
     "lead_ruling": "2026-10-25T19:40+08:00 裁：规格作废，A/B 两种变体都不接受；由 inspector 重出"
                    "（方向=例外按『命中的罕见字属于所问属性词表』而非『命中 1 个罕见字』）",
     "invalidates": ["kvmem/m2_visibility/m1/evidence/M18-3-literal-cov+need2.patch",
                     "kvmem/m2_visibility/m1/evidence/M18-3-need2-only.patch"],
     "tried": [
         {"variant": "照 §2.2 两条全改（cov 分母纳入 bigrams + 删 need=1）",
          "patch": "kvmem/m2_visibility/m1/evidence/M18-3-literal-cov+need2.patch",
          "result": "A9 RED：cov = 3.98/(3.98+12.36) = 0.24 < 0.35（out/M18-A-after-M18-3.json）"},
         {"variant": "只改 need=2（cov 分母不动）",
          "patch": "kvmem/m2_visibility/m1/evidence/M18-3-need2-only.patch",
          "result": "A8/A9 双绿但真实库 P2 5→ABSTAIN（out/M18-CMP-step3-vs-step2.json: worse=1）"}],
     "evidence_doc": "kvmem/m2_visibility/m1/evidence/M18-3-INVALIDATES.md"},
    {"id": "M18-4", "landed": True, "direction": "放松（修一致性：ABS_CUT 只是排序截断）",
     "file": "tools/retrieval.py",
     "before_sha16": "ac6ea8ccee09173b", "after_sha16": None,
     "changed": ["keep 为空时无条件保底 `out[:1]`（覆盖并取代 M18-1 的 want_prop 守卫）"],
     "assertions": {"before": "A10 RED（改后同一构造的基线复跑仍 4/11，见 out/M18-A-baseline-recheck.json）",
                    "after": "A10 GREEN，A1–A11 = 10/11，仅 A8 红（依赖 M18-3）"},
     "zone_reading": {"construction": {"reps": 200, "main_chars": 1407},
                      "cov": 0.44, "score": 0.883, "ABS_CUT": 1.1, "COV_MIN": 0.35},
     "real_probes": {"vs_before": {"compare": "out/M18-CMP-after-M18-4-vs-before.json",
                                   "better": 3, "same": 5, "worse": 0},
                     "vs_step2": {"compare": "out/M18-CMP-M18-4-vs-step2.json",
                                  "better": 0, "same": 8, "worse": 0}}},
]


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
        h = sha256_file(p)
        out[rel] = {"sha16": h[:16], "sha256": h, "bytes": os.path.getsize(p)}
    return out


def main():
    t0 = time.time()
    os.makedirs(BEFORE, exist_ok=True)
    s1 = snap()
    if s1 is None:
        return 3
    for st in STEPS:
        if st.get("landed") and st["file"] in s1 and not st.get("after_sha16"):
            st["after_sha16"] = s1[st["file"]]["sha16"]

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
        print(json.dumps({"STOP": "两次采样不一致", "s1": s1, "s2": s2}, ensure_ascii=False))
        return 2

    landed = {
        "schema": "m18_landed_v1", "batch_id": "m18",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sample_gap_s": GAP_S,
        "scope": "task-17 M1.8：M18-2 + M18-1 已落地；M18-3/M18-4 未落地（待裁）",
        "status_claim": "M18-2/M18-1（lead 已签）/M18-4 已落地；M18-3 规格作废待 inspector 重出。**不声称 M1.8 已验收**，也不声称四步全落",
        "lead_signatures": {"M18-2": "2026-10-25T19:40+08:00", "M18-1": "2026-10-25T19:40+08:00"},
        "supersedes": {"previous_ledger": "kvmem/m2_visibility/m1/_before/LANDED-m18.json@1688d8d19da0ec8a",
                       "why": "本批次新增 M18-4 落地与 M18-3 作废记录；旧台账按 _before 约定留档"},
        "baseline": {"tools/analysis.py": "9b9368524422f352",
                     "tools/retrieval.py": "c8e9e332ef8fd367",
                     "kvmem/chat.db": "237d8e1f5de9a382",
                     "thresholds": {"GATE": 1.30, "COV_MIN": 0.35,
                                    "REL_CUT": 0.55, "ABS_CUT": 1.10},
                     "note": "四个冻结阈值与 chat.db 一字未动（A11 每次跑都验）"},
        "final": {"tools/analysis.py": s1["tools/analysis.py"]["sha16"],
                  "tools/retrieval.py": s1["tools/retrieval.py"]["sha16"],
                  "tools/test_retrieval_judges.py": s1["tools/test_retrieval_judges.py"]["sha16"]},
        "steps": STEPS,
        "assertions_now": {"a_pass": 10, "a_total": 11, "a_fail": ["A8"],
                           "product": "kvmem/m2_visibility/m1/out/M18-A-after-M18-4.json",
                           "baseline_recheck": "kvmem/m2_visibility/m1/out/M18-A-baseline-recheck.json",
                           "note": "A8 依赖未落地的 M18-3；基线复跑 4/11（同一套断言）"},
        "real_probes_now": {"compare": "kvmem/m2_visibility/m1/out/M18-CMP-after-M18-4-vs-before.json",
                            "better": 3, "same": 5, "worse": 0, "no_worse": True,
                            "vs_previous_step": "kvmem/m2_visibility/m1/out/M18-CMP-M18-4-vs-step2.json"},
        "gaps": [{"id": "P1", "doc": "kvmem/m2_visibility/m1/evidence/P1-gap.md",
                  "reading": "我的地址是什么：ABSTAIN→块3（聚合块），目标块5 未居首；同分按 source_id 取首",
                  "judged": "same（不判 worse；内容含同一住址串、未进 must_not）",
                  "owner": "inspector §缺口 收录；修法属同分排序议题，本批未改"}],
        "freeze_check": {"status": "已知可解释红（lead 2026-10-25T19:40 裁：现在不要 bump）",
                         "observed": "SELECTION LAYER: CHANGED (2): analysis.py 9b93…→49e9…, retrieval.py c8e9…→ac6e…(再→b89f…)",
                         "why": "FROZEN 封存的是文件 sha，不是阈值；M18-2/M18-1 已签 ⇒ 漂移可解释",
                         "plan": "M1.8 收口时一次性 re-freeze（old→new + 理由），本批不动 freeze_check.py"},
        "files": {rel: {"sha16": i["sha16"], "bytes": i["bytes"]} for rel, i in s1.items()},
        "copies": copies,
        "register": {"path": REGISTER.replace("\\", "/"),
                     "entries_total_at_sampling": len(reg["entries"]),
                     "entries_added": added, "copyist": "executor"},
        "samples": 2, "samples_identical": identical,
        "self_registration": "本文件不登记自身 sha16（自指恒假，RESULTS-RED.md §22.3）",
        "elapsed_s": round(time.time() - t0, 2),
    }
    with open(LANDED, "w", encoding="utf-8", newline="\n") as f:
        json.dump(landed, f, ensure_ascii=False, indent=1)
    print(json.dumps({"landed": "LANDED-m18.json", "files": len(landed["files"]),
                      "entries_total": len(reg["entries"]), "added": added,
                      "samples_identical": identical,
                      "final": landed["final"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())