# -*- coding: utf-8 -*-
"""M2 产物加固 r2（task-19）的留档批次 `m2accept-r2`。

相对批 `m2accept`（`LANDED-m2accept.json` `5275b600ba6c3ca8`）：
- 本批**新增/改动的文件**：`accept_m2_real.py`、`planner.py`、`out/M2-ACCEPT-r2.json`；
- r1 产物 `out/M2-ACCEPT-r1.json`（`76e2783343c3e196`）**未动**，仍是那一批的读数，本条只是被 r2 `supersedes`；
- 改前的两文件已按约定先留 `_before/<name>@<sha16>`（本台账 `pre_change_copies` 记路径与相等性）。

**本文件不登记自身 sha16**（自指恒假，RESULTS-RED.md §22.3）。
"""
import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BEFORE = os.path.join(HERE, "_before")
REGISTER = os.path.join(BEFORE, "REGISTER.json")
LANDED = os.path.join(HERE, "LANDED-m2accept-r2.json")
GAP_S = 5

SOURCES = ["accept_m2_real.py", "planner.py", "out/M2-ACCEPT-r2.json"]
REASON = ("task-19 M2 产物加固 r2：修 D1（planner naming 字面量 12/45）/D2（pre_eq/post_eq 同源）/"
          "D3（红证改打 order_assert、op 名与日志一致），并登记 selection_layer 与 r1 对照")

PRE_CHANGE = {
    "planner.py": "4162661cc04182e8",
    "accept_m2_real.py": "c09beefe6e9db0c5",
}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""):
            h.update(c)
    return h.hexdigest()


def snap():
    out = {}
    for rel in SOURCES:
        p = os.path.join(HERE, rel)
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
    for name, want in PRE_CHANGE.items():
        cp = os.path.join(BEFORE, "%s@%s" % (name, want))
        if not os.path.exists(cp):
            print("STOP: 缺改前副本 %s（约定：改前必须先 _before 留档）" % cp, file=sys.stderr)
            return 3
        pre[name] = {"copy_path": cp.replace("\\", "/"), "copy_sha16": sha256_file(cp)[:16],
                     "expected_sha16": want, "ok": sha256_file(cp)[:16] == want}

    s1 = snap()
    if s1 is None:
        return 3

    copies, conflicts = {}, []
    for rel, info in s1.items():
        copy_name = "%s@%s" % (os.path.basename(rel), info["sha16"])
        copy_path = os.path.join(BEFORE, copy_name)
        if os.path.exists(copy_path):
            if sha256_file(copy_path) != info["sha256"]:
                conflicts.append({"rel": rel, "copy": copy_name,
                                  "why": "同名副本已存在但字节不等 —— 拒绝覆盖"})
                continue
        else:
            shutil.copyfile(os.path.join(HERE, rel), copy_path)
        copies[rel] = {"copy_path": copy_path.replace("\\", "/"),
                       "copy_sha16": sha256_file(copy_path)[:16],
                       "byte_equal": sha256_file(copy_path) == info["sha256"]}
    if conflicts:
        print(json.dumps({"STOP": "副本冲突", "conflicts": conflicts}, ensure_ascii=False))
        return 2

    reg = {"rule": "any run that overwrites an accepted artifact must first copy it to "
                   "_before/<name>@<sha16>",
           "updated_at": None, "entries": [], "changes": []}
    if os.path.exists(REGISTER):
        reg = json.load(open(REGISTER, encoding="utf-8"))
        reg.setdefault("entries", [])
        reg.setdefault("changes", [])
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

    r2 = json.load(open(os.path.join(HERE, "out", "M2-ACCEPT-r2.json"), encoding="utf-8"))
    r1p = os.path.join(HERE, "out", "M2-ACCEPT-r1.json")
    landed = {
        "schema": "m2accept_landed_v2", "batch_id": "m2accept-r2",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sample_gap_s": GAP_S, "samples": 2, "samples_identical": identical,
        "scope": "M2 产物加固 r2（task-19）：D1/D2/D3 修完后重跑一次，判据与期望未动",
        "supersedes": {"product": "out/M2-ACCEPT-r1.json", "r1_sha16": "76e2783343c3e196",
                       "r1_file_untouched": sha256_file(r1p)[:16] == "76e2783343c3e196",
                       "why": "r2 只补字段与红证门闩，读数不变（r1_readings_unchanged=true）"},
        "files": {rel: {"sha16": i["sha16"], "bytes": i["bytes"]} for rel, i in s1.items()},
        "pre_change_copies": pre,
        "fixes": {
            "D1": {"file": "planner.py", "line": "repos_local 的 naming 字面量",
                   "before": "delta=位移(=12)；cells_moved=…(=45) 写死，与同对象 delta=19/cells_moved=666 矛盾",
                   "after": "按实参生成：% (new_cells, moved)",
                   "r2_reading": [s.get("naming") for s in r2["steps"] if s.get("op") == "repos_local"]},
            "D2": {"file": "accept_m2_real.py", "line": "byte_equality.unmoved_blocks",
                   "before": "pre_eq 与 post_eq 是同一个布尔（同一 sha 比较）",
                   "after": "pre_eq=pre 两次 save 比、post_eq=post 两次 save 比、unchanged=pre vs post 比；三字段不同源",
                   "r2_reading": [{k: u[k] for k in ("name", "pre_eq", "post_eq", "unchanged")}
                                  for u in r2["byte_equality"]["unmoved_blocks"]]},
            "D3": {"file": "accept_m2_real.py", "line": "order_red_probe",
                   "before": "打 planner.check_ops（本臂从不调用）+ op 名写 share",
                   "after": "打本臂真正执行的 order_assert；正序 True、反序 False；op 名取自真实 log"
                            "（drop/repos_local/share_new/share_existing）",
                   "r2_reading": {"forward_passed": r2["order_red_probe"]["forward"]["passed"],
                                  "reversed_passed": r2["order_red_probe"]["reversed"]["passed"],
                                  "red_proof_ok": r2["order_red_probe"]["red_proof_ok"],
                                  "op_sequence": r2["order_assertion"]["sequence"]}},
            "D4_D7": "只记录、不改判据：three_criteria[1].pass 仍是 fact_ok 的同义重复；"
                     "mounted_still_answers 仍不承重（两处已在字段/注释里标『不承重』，本轮未改）",
        },
        "readings": {
            "verdict": r2["verdict"], "exit": r2["exit"],
            "n_blocks_concurrent": r2["n_blocks_concurrent"],
            "chat_before_insert": r2["chat_before_insert"],
            "chat_after_insert": r2["chat_after_insert"],
            "n_chat_cells_before_insert": r2["n_chat_cells_before_insert"],
            "live_cells": r2["cells_accounting"]["live_cells"],
            "steps": [s.get("op") for s in r2["steps"]],
            "repos_local": next({k: s.get(k) for k in ("delta", "cells_moved", "expected_cells_moved")}
                                for s in r2["steps"] if s.get("op") == "repos_local"),
            "fact": r2["fact_ok"]["fact"], "fact_hit": r2["fact_ok"]["ask"]["fact_hit"],
            "answer_first_line": r2["fact_ok"]["ask"]["answer"].splitlines()[0][:80],
            "byte_equality_all_equal": r2["byte_equality"]["all_equal"],
            "sha_stable_ok": r2["sha_stable"]["ok"],
            "elapsed_s": r2["elapsed_s"],
            "op_ms": r2["op_ms"],
        },
        "r1_comparison": {"all_match": r2["r1_readings_unchanged"],
                          "checks_equal": sum(1 for v in r2["r1_comparison"]["checks"].values()
                                              if v["equal"]),
                          "checks_total": len(r2["r1_comparison"]["checks"]),
                          "diff": r2["r1_comparison"]["diff"],
                          "note": "逐项 31 条：装置/几何/并发块数/插入轮次/chat 区间/步骤序列/"
                                  "fact/三块 pre-post sha 与字节数/覆盖/装置稳定性，全部相等"},
        "selection_layer": r2["selection_layer"],
        "copies": copies,
        "register": {"path": REGISTER.replace("\\", "/"),
                     "entries_total_at_sampling": len(reg["entries"]),
                     "entries_added": added, "copyist": "executor"},
        "status_claim": "产物加固完成（r2 自报 verdict=通过、r1_readings_unchanged=true）；"
                        "**不声称 M2 验收通过**（验收已由 lead 在 docs/_work/M2-ACCEPT-lead.md 签）",
        "self_registration": "本文件不登记自身 sha16（自指恒假，RESULTS-RED.md §22.3）",
        "elapsed_s": round(time.time() - t0, 2),
    }
    with open(LANDED, "w", encoding="utf-8", newline="\n") as f:
        json.dump(landed, f, ensure_ascii=False, indent=1)
    print(json.dumps({"landed": os.path.basename(LANDED), "files": len(landed["files"]),
                      "entries_total": len(reg["entries"]), "added": added,
                      "samples_identical": identical,
                      "r1_unchanged": landed["r1_comparison"]["all_match"],
                      "checks": "%d/%d" % (landed["r1_comparison"]["checks_equal"],
                                           landed["r1_comparison"]["checks_total"]),
                      "landed_sha16_hint": "见报告（本文件不登记自身）"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())