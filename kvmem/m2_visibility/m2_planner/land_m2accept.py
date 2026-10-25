# -*- coding: utf-8 -*-
"""M2 真机验收臂（task-16）的留档批次：`accept_m2_real.py` + `out/M2-ACCEPT-r1.json`。

写法与 `land_m2planner.py` 同一套（两采样、副本字节相等、REGISTER 去重追加），
但**另起批次** `m2accept`：先前批次 `LANDED-m2planner.json` 里登记的文件本次一个都不改，
所以那一批的 sha16 仍然有效（台账不是可覆盖的“最新状态”，它是“某次采样的读数”）。

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
LANDED = os.path.join(HERE, "LANDED-m2accept.json")
GAP_S = 3

SOURCES = ["accept_m2_real.py", "out/M2-ACCEPT-r1.json"]
REASON = ("task-16 M2 真机验收臂：脚本与产物首次落盘留档"
          "（装置 14B 0b319bd0572f2730 / dll 9edbafa150700614；几何 51 cells/[4045,4095]/first_q 4096）")


def sha256_bytes(p):
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
        out[rel] = {"sha16": sha256_bytes(p)[:16], "sha256": sha256_bytes(p),
                    "bytes": os.path.getsize(p)}
    return out


def main():
    t0 = time.time()
    os.makedirs(BEFORE, exist_ok=True)
    s1 = snap()
    if s1 is None:
        return 3

    copies, conflicts = {}, []
    for rel, info in s1.items():
        copy_name = "%s@%s" % (os.path.basename(rel), info["sha16"])
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

    landed = {
        "schema": "m2accept_landed", "batch_id": "m2accept",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sample_gap_s": GAP_S,
        "scope": "M2 真机验收臂（task-16）：脚本 accept_m2_real.py + 产物 out/M2-ACCEPT-r1.json",
        "verdict_claim": "产物 verdict=通过（executor 自报，待 lead/inspector 复核；本台账不声称验收已签）",
        "files": {rel: {"sha16": i["sha16"], "bytes": i["bytes"]} for rel, i in s1.items()},
        "copies": copies,
        "register": {"path": REGISTER.replace("\\", "/"),
                     "entries_total_at_sampling": len(reg["entries"]),
                     "entries_added": added, "copyist": "executor",
                     "note": "同一 REGISTER 由批次 m2planner(17 条) 与 m2accept 共用；"
                             "LANDED-m2planner.json 里记的 17 是它那次采样的读数"},
        "samples": 2, "samples_identical": identical,
        "self_registration": "本文件不登记自身 sha16（自指恒假，RESULTS-RED.md §22.3）",
        "how_to_verify": "对两份文件重算 sha256[:16] 与本表比对；再核 _before 副本逐字节相等",
        "elapsed_s": round(time.time() - t0, 2),
    }
    with open(LANDED, "w", encoding="utf-8", newline="\n") as f:
        json.dump(landed, f, ensure_ascii=False, indent=1)
    print(json.dumps({"landed": os.path.basename(LANDED), "files": len(landed["files"]),
                      "entries_total": len(reg["entries"]), "added": added,
                      "samples_identical": identical}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())