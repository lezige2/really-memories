# -*- coding: utf-8 -*-
"""把 M2 规划器簇**纳入留档**并产 `LANDED-m2planner.json`（lead 裁定：补治理，不重写、不追认）。

做四件事，全部可复算：
1. 对每份源文件重算 sha16；若 `_before/<basename>@<sha16>` 不存在则拷贝；
   已存在但与源**字节不等** ⇒ 停手（exit 2），绝不覆盖既有副本。
2. `_before/REGISTER.json` 追加登记（已有同 `source_name`+`source_sha16` 的条目则跳过）。
3. **两次采样**（中间隔 `GAP_S` 秒）重算全部 sha16：两次不同 ⇒ exit 2，不写 LANDED。
4. 写 `LANDED-m2planner.json`：每文件 sha16/bytes + 副本 sha16 + 逐字节相等 + 登记条数。

**本文件不登记自身 sha16**（自指恒假，见 `RESULTS-RED.md` §22.3）。
**不声称 M2 验收通过**：状态 = 已实现·未验收（见 `STATUS.md`）。
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
LANDED = os.path.join(HERE, "LANDED-m2planner.json")
GAP_S = 3

PRE_EXISTING = ["planner.py", "test_planner.py", "red_suite.py", "fake_planner.py",
                "kvsim.py", "assertions.py", "FIELDS.md", "RESULTS-RED.md",
                "out/GREEN-SUITE.json", "out/RED-SUITE.json", "out/ORDER-EVIDENCE.json"]
NEW = ["plan.py", "evict_policy.py", "selftest_plan.py", "land_m2planner.py",
       "STATUS.md", "out/PLAN-SELFTEST.json"]
SOURCES = [(rel, "pre_existing") for rel in PRE_EXISTING] + [(rel, "new") for rel in NEW]

REASON = {"pre_existing": "纳入不动对象：M2 规划器簇（10-25 13:04–13:42）此前未入库、无 _before；"
                          "按 lead 裁定（task-15）先按字节留档，不改内容",
          "new": "本单新增文件首次落盘留档（task-15：冻结接口适配 + 淘汰独立策略 + 单测/状态）"}


def sha256_bytes(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(8 << 20), b""):
            h.update(c)
    return h.hexdigest()


def snap():
    out = {}
    for rel, kind in SOURCES:
        p = os.path.join(HERE, rel)
        if not os.path.exists(p):
            print("STOP: 缺文件 %s" % rel, file=sys.stderr)
            return None
        h = sha256_bytes(p)
        out[rel] = {"sha16": h[:16], "sha256": h, "bytes": os.path.getsize(p), "kind": kind}
    return out


def main():
    t0 = time.time()
    os.makedirs(BEFORE, exist_ok=True)

    s1 = snap()
    if s1 is None:
        return 3

    copies, conflicts = {}, []
    for rel, info in s1.items():
        name = os.path.basename(rel)
        copy_name = "%s@%s" % (name, info["sha16"])
        copy_path = os.path.join(BEFORE, copy_name)
        if os.path.exists(copy_path):
            if sha256_bytes(copy_path) != info["sha256"]:
                conflicts.append({"rel": rel, "copy": copy_name,
                                  "why": "同名副本已存在但字节不等 —— 拒绝覆盖"})
                continue
        else:
            shutil.copyfile(os.path.join(HERE, rel), copy_path)
        copies[rel] = {"copy_path": copy_path.replace("\\", "/"),
                       "copy_sha16": sha256_bytes(copy_path)[:16],
                       "byte_equal": sha256_bytes(copy_path) == info["sha256"],
                       "in_place": False}
    if conflicts:
        print(json.dumps({"STOP": "副本冲突", "conflicts": conflicts}, ensure_ascii=False))
        return 2

    reg = {"rule": "any run that overwrites an accepted artifact must first copy it to "
                   "_before/<name>@<sha16>; an anchor proves what a value WAS, it does not keep it",
           "updated_at": None, "entries": [], "changes": []}
    if os.path.exists(REGISTER):
        reg = json.load(open(REGISTER, encoding="utf-8"))
        reg.setdefault("entries", [])
        reg.setdefault("changes", [])
    existing = {(e.get("source_name"), e.get("source_sha16")) for e in reg["entries"]}
    added = 0
    for rel, info in s1.items():
        key = (rel, info["sha16"])
        if key in existing:
            continue
        reg["entries"].append({
            "source_name": rel,
            "source_sha16": info["sha16"],
            "copy_path": copies[rel]["copy_path"],
            "in_place": False,
            "copy_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "copyist": "executor",
            "reason": REASON[info["kind"]],
        })
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
        diff = {k: [s1[k]["sha16"], s2[k]["sha16"]] for k in s1 if s1[k]["sha16"] != s2[k]["sha16"]}
        print(json.dumps({"STOP": "两次采样不一致，不写 LANDED", "diff": diff}, ensure_ascii=False))
        return 2

    landed = {
        "schema": "m2planner_landed",
        "batch_id": "m2planner",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sample_gap_s": GAP_S,
        "scope": "M2 放置规划器簇（m2_planner/）纳入留档 + 本单新增的冻结接口适配/淘汰策略/单测",
        "status_claim": "已实现·未验收（本文件不声称验收通过；验收需真机臂，另单）",
        "files": {rel: {"sha16": i["sha16"], "bytes": i["bytes"], "kind": i["kind"]}
                  for rel, i in s1.items()},
        "copies": copies,
        "register": {"path": REGISTER.replace("\\", "/"), "entries_total": len(reg["entries"]),
                     "entries_added": added, "copyist": "executor"},
        "samples": 2,
        "samples_identical": identical,
        "self_registration": "本文件不登记自身 sha16（自指恒假，RESULTS-RED.md §22.3）",
        "how_to_verify": "对每份文件重算 sha256[:16] 与本表比对；再核 _before 副本逐字节相等。"
                         "不符 ⇒ 基于旧 sha 的读数作废",
        "elapsed_s": round(time.time() - t0, 2),
    }
    with open(LANDED, "w", encoding="utf-8", newline="\n") as f:
        json.dump(landed, f, ensure_ascii=False, indent=1)

    print(json.dumps({"landed": os.path.basename(LANDED),
                      "files": len(landed["files"]), "entries_total": len(reg["entries"]),
                      "entries_added": added, "samples_identical": identical,
                      "copies_dir": BEFORE.replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())