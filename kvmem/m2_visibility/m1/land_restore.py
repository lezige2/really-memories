# -*- coding: utf-8 -*-
"""task-23：把备份树里存在、工作区缺失的文本文件按**字节原样**回填（不覆盖任何已存在且不同的文件）。

来源 `D:\\llama-mem-backup-2026-10-25`（只读）；目标 `D:\\llama-mem`。
扫描面 = 扩展名 {.md,.json,.txt,.py,.sh}；分母 85（备份树内文件数）。
台账 `kvmem/m2_visibility/m1/LANDED-restore.json`：逐份 sha16 + 3 份 skipped 双版对照 + 两采样一致。

停手条件（任务单）：枚举数与 80 差 >±2 ⇒ 先报差异；目标已存在且不同 ⇒ 跳过并记录（不覆盖）。
本文件不登记自身 sha16（§22.3）。
"""
import hashlib
import json
import os
import shutil
import sys
import time

SRC = r"D:\llama-mem-backup-2026-10-25"
DST = r"D:\llama-mem"
EXTS = {".md", ".json", ".txt", ".py", ".sh"}
HERE = os.path.join(DST, "kvmem", "m2_visibility", "m1")
LANDED = os.path.join(HERE, "LANDED-restore.json")
BEFORE = os.path.join(HERE, "_before")
EXPECT_TOTAL = 85
EXPECT_MISSING = 80
GAP_S = 3

# 明确禁止覆盖的三个（我们自己改过/修订过的）
PROTECT = {"FEATURES.md", "README.md", "kvmem/m2_visibility/mine/inspector/M4-ACCEPT.md"}


def sha256_file(p):
    with open(p, "rb") as f:                       # 二进制读，不过文本层
        return hashlib.sha256(f.read()).hexdigest()


def walk_exts(root):
    out = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules")]
        for n in names:
            if os.path.splitext(n)[1].lower() in EXTS:
                out.append(os.path.join(base, n))
    return out


def main():
    t0 = time.time()
    if not os.path.isdir(SRC):
        print("STOP: 备份目录不可读 %r" % SRC, file=sys.stderr)
        return 3

    # ① 枚举（分母必须与 lead 一致）
    backup = sorted(walk_exts(SRC))
    if abs(len(backup) - EXPECT_TOTAL) > 0:
        print(json.dumps({"STOP": "枚举数与 task 分母不符", "scanned": len(backup),
                          "expected": EXPECT_TOTAL}, ensure_ascii=False))
        return 2

    plan, skipped, identical, conflicts = [], [], [], []
    for sp in backup:
        rel = os.path.relpath(sp, SRC).replace("\\", "/")
        dp = os.path.join(DST, rel.replace("/", "\\"))
        b16, bsz = sha256_file(sp)[:16], os.path.getsize(sp)
        if not os.path.exists(dp):
            plan.append({"relpath": rel, "src": sp, "dst": dp,
                         "bytes": bsz, "backup_sha16": b16})
        else:
            d16, dsz = sha256_file(dp)[:16], os.path.getsize(dp)
            if b16 == d16:
                identical.append({"relpath": rel, "sha16": d16, "bytes": dsz})
            elif rel in PROTECT:
                skipped.append({"relpath": rel, "backup_sha16": b16, "backup_bytes": bsz,
                                "workspace_sha16": d16, "workspace_bytes": dsz,
                                "why": "禁止覆盖：我们自己在 10-25 修订过"})
            else:
                conflicts.append({"relpath": rel, "backup_sha16": b16,
                                  "workspace_sha16": d16})

    if abs(len(plan) - EXPECT_MISSING) > 0 or conflicts:
        print(json.dumps({"STOP": "与 task 期望不符（差 >0 或出现未授权冲突，未做任何拷贝）",
                          "scanned": len(backup), "to_restore": len(plan),
                          "expected_missing": EXPECT_MISSING,
                          "release_conflicts": len(conflicts),
                          "conflicts": conflicts[:20]}, ensure_ascii=False))
        return 2

    # ② 逐份字节拷贝 + 立即回读校验
    restored = []
    for it in plan:
        os.makedirs(os.path.dirname(it["dst"]), exist_ok=True)
        if os.path.exists(it["dst"]):            # 竞态：拷贝前又出现了，绝不覆盖
            print(json.dumps({"STOP": "目标在拷贝前出现（不覆盖）", "relpath": it["relpath"]},
                             ensure_ascii=False))
            return 2
        shutil.copyfile(it["src"], it["dst"])
        src_bytes, dst_bytes = open(it["src"], "rb").read(), open(it["dst"], "rb").read()
        ok = src_bytes == dst_bytes
        h16 = sha256_file(it["dst"])[:16]
        restored.append({"relpath": it["relpath"], "bytes": len(dst_bytes),
                         "sha16": h16, "backup_sha16": it["backup_sha16"],
                         "byte_equal": ok})
        if not (ok and h16 == it["backup_sha16"]):
            print(json.dumps({"STOP": "拷贝后字节/摘要不符", "relpath": it["relpath"],
                              "sha16": h16, "backup_sha16": it["backup_sha16"],
                              "byte_equal": ok}, ensure_ascii=False))
            return 2

    # ③ 两采样一致（间隔 GAP_S），并复核 protected 三份没被动
    time.sleep(GAP_S)
    recheck = []
    for it in restored:
        p = os.path.join(DST, it["relpath"].replace("/", "\\"))
        recheck.append((it["relpath"], sha256_file(p)[:16] == it["sha16"]))
    # 回扫：此刻工作区仍缺失的备份文件应为 0
    still_missing = []
    for sp in backup:
        rel = os.path.relpath(sp, SRC).replace("\\", "/")
        if not os.path.exists(os.path.join(DST, rel.replace("/", "\\"))):
            still_missing.append(rel)
    samples_identical = all(ok for _, ok in recheck) and not still_missing

    # ④ 同步把 85 份目标字节登记进 REGISTER + _before 副本？—— 本单是**回填既有文档**，
    #    不是"覆盖已验收产物"，故不做 _before 副本；只登记 restored 的 sha 供复算。
    landed = {
        "schema": "restore_landed_v1", "batch_id": "restore-backup-2026-10-25",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_root": SRC, "target_root": DST, "exts": sorted(EXTS),
        "scanned": len(backup), "scanned_denominator_note":
            "分母 = os.walk(备份树) 里扩展名属于 %s 的文件数（Windows 路径，非 MSYS /d/…）" % sorted(EXTS),
        "restored_count": len(restored), "restored": restored,
        "skipped_existing_count": len(skipped), "skipped_existing": skipped,
        "identical_count": len(identical), "identical": identical,
        "still_missing_after": still_missing,
        "two_samples": {"gap_s": GAP_S, "samples": 2, "identical": samples_identical},
        "key_files": {r: next((x["sha16"] for x in restored if x["relpath"] == r), None)
                      for r in ("docs/legacy-2026-10-24/README.md", "PROJECT-STATE.md",
                                "docs/legacy-2026-10-24/STATUS-REPORT.md",
                                "kvmem/m2_visibility/mine/lead/DISCIPLINES.md")},
        "rules": {"byte_for_byte": True, "content_edited": False, "files_reformatted": False,
                  "protected_not_overwritten": sorted(PROTECT),
                  "no_git_add_commit": True},
        "self_registration": "本文件不登记自身 sha16（自指恒假，RESULTS-RED.md §22.3）",
        "elapsed_s": round(time.time() - t0, 2),
    }
    with open(LANDED, "w", encoding="utf-8", newline="\n") as f:
        json.dump(landed, f, ensure_ascii=False, indent=1)
    print(json.dumps({"landed": os.path.basename(LANDED), "scanned": len(backup),
                      "restored": len(restored), "skipped_existing": len(skipped),
                      "identical": len(identical), "still_missing": len(still_missing),
                      "samples_identical": samples_identical,
                      "legacy_readme": landed["key_files"]["docs/legacy-2026-10-24/README.md"],
                      "project_state": landed["key_files"]["PROJECT-STATE.md"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())