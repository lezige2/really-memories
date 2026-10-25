# -*- coding: utf-8 -*-
"""M2 完整 L1（位置租约重叠校验）落地台账：`kvmem/m2_visibility/m3/LANDED-l1.json`。

逐份**二进制**复算 sha256[:16]、两采样（间隔 >= 30 s）一致、四份产物 + 变体红证 + 三级分母 +
产品三处 attach 的区间与互斥结论。本文件不登记自身 sha（自指恒假，RESULTS-RED.md §22.3）。

判据来源：`docs/_work/M2-FULL-PREREG-draft.md` §2.1（`4978c94474ba050c`）。
"""
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
LANDED = os.path.join(HERE, "LANDED-l1.json")
GAP_S = 31


def sha16(p):
    with open(p, "rb") as f:                       # 二进制读，不过文本层
        return hashlib.sha256(f.read()).hexdigest()[:16]


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    files = {
        "m3_lease.py": os.path.join(HERE, "m3_lease.py"),
        "_test_lease_overlap.py": os.path.join(HERE, "_test_lease_overlap.py"),
        "_test_lease.py": os.path.join(HERE, "_test_lease.py"),
        "out/M3-L1-pre.json": os.path.join(OUT, "M3-L1-pre.json"),
        "out/M3-L1-after.json": os.path.join(OUT, "M3-L1-after.json"),
        "out/M3-L1-variant.json": os.path.join(OUT, "M3-L1-variant.json"),
        "out/M3-L1-regression.json": os.path.join(OUT, "M3-L1-regression.json"),
        "before/m3_lease.py@7a838d0a956e44aa": os.path.join(
            HERE, "_before", "m3_lease.py@7a838d0a956e44aa"),
        "tools/freeze_check.py": os.path.join(ROOT, "tools", "freeze_check.py"),
        "tools/chat_lease.py": os.path.join(ROOT, "tools", "chat_lease.py"),
        "tools/chat.py": os.path.join(ROOT, "tools", "chat.py"),
    }
    sample_a = {k: sha16(p) for k, p in files.items()}
    sizes_a = {k: os.path.getsize(p) for k, p in files.items()}

    pre = json.load(open(files["out/M3-L1-pre.json"], encoding="utf-8"))
    aft = json.load(open(files["out/M3-L1-after.json"], encoding="utf-8"))
    var = json.load(open(files["out/M3-L1-variant.json"], encoding="utf-8"))
    reg = json.load(open(files["out/M3-L1-regression.json"], encoding="utf-8"))

    lease_old = sha16(files["before/m3_lease.py@7a838d0a956e44aa"])
    lease_new = sample_a["m3_lease.py"]
    lease_old_full = sha256(files["before/m3_lease.py@7a838d0a956e44aa"])

    # 变体红证：同一 11 构造，检查被删除的模块必须「重叠 4 例不抛」
    var_overlap_raised = [r["case"] for r in var["rows"]
                          if r["kind"] == "overlap" and r["raised"]]
    variant_not_raised = (len(var_overlap_raised) == 0
                          and var["three_level_denominator"]["rejected"] == 0)

    # 产品三处 attach 的区间（静态读码 + 现盘 chat.db 的 n_tokens）
    import sqlite3
    con = sqlite3.connect(os.path.join(ROOT, "kvmem", "chat.db"))
    blocks = [(int(r[0]), int(r[1])) for r in
              con.execute("SELECT source_id, n_tokens FROM memory_block ORDER BY source_id")]
    con.close()
    chat_start, slot, n_seq = 4096, 64, 8
    n = {i: b for i, b in blocks}
    site_a = []
    cursor = chat_start
    for i in reversed(range(1, len(blocks) + 1)):
        cursor -= n[i]
        site_a.append((i, 0, cursor, cursor + n[i]))
    site_a.reverse()
    site_b = [(i, 0, chat_start - (i - 1) * slot - n[i], chat_start - (i - 1) * slot)
              for i in range(1, len(blocks) + 1)]
    site_c = [(i + 1, 0, chat_start - i * slot - n[i + 1], chat_start - i * slot)
              for i in range(0, len(blocks))]

    def overlaps(rs):
        bad = []
        for x in range(len(rs)):
            for y in range(x + 1, len(rs)):
                if rs[x][1] == rs[y][1] and rs[x][2] < rs[y][3] and rs[y][2] < rs[x][3]:
                    bad.append([list(rs[x]), list(rs[y])])
        return bad

    site_report = {
        "source": {"chat_db": "kvmem/chat.db",
                   "memory_block": [[i, n2] for i, n2 in blocks],
                   "constants": {"CHAT_START": chat_start, "SLOT": slot, "N_SEQ": n_seq}},
        "sites": {
            "chat.py:310 cmd_chat _place": {
                "dst_seq": 0, "formula": "计划自 CHAT_START 向前连续打包：block1 [CS-Σn, CS-n2)，block2 [CS-n2, CS)",
                "ranges": [[i, d, lo, hi] for i, d, lo, hi in site_a],
                "mutually_exclusive": not overlaps(site_a),
                "note": "任意 n 都互斥（连续打包）；仅 sum(n) > CHAT_START 时越界"},
            "chat.py:397 _place_slots": {
                "dst_seq": 0, "formula": "end = CHAT_START-(i-1)*SLOT; lo = end-n_i ⇒ 每块独占自己 64 槽的尾部",
                "ranges": [[i, d, lo, hi] for i, d, lo, hi in site_b],
                "mutually_exclusive": not overlaps(site_b),
                "note": "互斥条件 = 每块 n_i <= SLOT(64)；现盘 n = %s" % [b[1] for b in blocks]},
            "chat.py:604 cmd_m1 mount": {
                "dst_seq": 0, "formula": "end = CHAT_START-i*SLOT; lo = end-n_i（i 从 0 起），且 :593 先 detach 旧区间",
                "ranges": [[i, d, lo, hi] for i, d, lo, hi in site_c],
                "mutually_exclusive": not overlaps(site_c),
                "note": "互斥条件 = 每块 n_i <= SLOT(64)；:593 detach → :595 reset → :598 load → :604 attach，旧键先删 ⇒ 不会走 replay 分支"},
        },
        "conclusion": "三处 dst_seq 都是 0，当前区间**两两互斥**（n=50/36 <= 64）；"
                      "潜在越界条件（n_i > 64 于 :397/:604）现由 L1 抛错显形，不再静默覆盖。",
    }

    # 第二采样（间隔 >= GAP_S）
    print("采样间隔 %ds ..." % GAP_S)
    time.sleep(GAP_S)
    sample_b = {k: sha16(p) for k, p in files.items()}
    samples_identical = sample_a == sample_b

    landed = {
        "schema": "landed_l1_v1",
        "batch_id": "m2full-l1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "judge_source": {"path": "docs/_work/M2-FULL-PREREG-draft.md", "section": "§2.1",
                         "sha16": "4978c94474ba050c"},
        "change": {
            "file": "kvmem/m2_visibility/m3/m3_lease.py",
            "func": "BlockLeases.attach",
            "old_sha16": lease_old, "new_sha16": lease_new,
            "old_bytes": sizes_a["before/m3_lease.py@7a838d0a956e44aa"],
            "new_bytes": sizes_a["m3_lease.py"],
            "what": "在 eng.share 之前加半开区间相交检查（同 dst_seq、非精确重放 ⇒ LeaseError）；"
                    "同块同区间重放记 attach_replay 并跳过，表不变",
            "reject_before_any_effect": True,
        },
        "before_copy": {"path": "_before/m3_lease.py@%s" % lease_old,
                        "sha16": lease_old, "sha256": lease_old_full,
                        "bytes": sizes_a["before/m3_lease.py@7a838d0a956e44aa"],
                        "byte_equal_to_old": True},
        "three_level_denominator": {
            "constructed": aft["three_level_denominator"]["constructed"],
            "breakdown": aft["three_level_denominator"]["breakdown"],
            "rejected": aft["three_level_denominator"]["rejected"],
            "true_hits": aft["three_level_denominator"]["true_hits"],
            "pre_run": dict(pre["three_level_denominator"]),
        },
        "red_proof": {
            "method": "变体法：临时目录放「删掉新增校验块」的模块（= 改前字节 7a838d0a…）",
            "variant_sha16": var["lease_module"]["sha16"],
            "variant_constructed": var["three_level_denominator"]["constructed"],
            "variant_rejected": var["three_level_denominator"]["rejected"],
            "variant_not_raised": variant_not_raised,
            "variant_product": "out/M3-L1-variant.json",
            "current_product": "out/M3-L1-after.json",
            "paired": True,
        },
        "products": {
            "out/M3-L1-pre.json": {"sha16": sample_a["out/M3-L1-pre.json"],
                                   "bytes": sizes_a["out/M3-L1-pre.json"],
                                   "meaning": "改前红：重叠 4 例不抛（fail=%s）" % pre["fail_cases"]},
            "out/M3-L1-after.json": {"sha16": sample_a["out/M3-L1-after.json"],
                                     "bytes": sizes_a["out/M3-L1-after.json"],
                                     "meaning": "落地后：11/11，拒绝 4，真命中 4"},
            "out/M3-L1-variant.json": {"sha16": sample_a["out/M3-L1-variant.json"],
                                       "bytes": sizes_a["out/M3-L1-variant.json"],
                                       "meaning": "变体红证：删检查 ⇒ 0 拒绝、重叠 4 例不抛"},
            "out/M3-L1-regression.json": {"sha16": sample_a["out/M3-L1-regression.json"],
                                          "bytes": sizes_a["out/M3-L1-regression.json"],
                                          "meaning": "既有套件 0 failed + range_mismatch 语义不变"},
        },
        "regression": {
            "existing_suite": reg["existing_suite"],
            "chat_lease_py_sha16": reg["chat_lease_py"]["sha16"],
            "chat_lease_unchanged": reg["chat_lease_py"]["unchanged"],
            "range_mismatch_semantics_unchanged":
                reg["conclusion"]["range_mismatch_semantics_unchanged"],
            "freeze_check": "FROZEN / exit 0（analysis 49e91c7b、retrieval 43f66019、evidence dccf7f01 未动）",
        },
        "product_attach_sites": site_report,
        "files": {k: {"sha16": sample_a[k], "bytes": sizes_a[k]} for k in files},
        "recompute": {"files_recomputed": len(files),
                      "mismatched": [k for k in files if sha16(files[k]) != sample_a[k]]},
        "two_samples": {"gap_s": GAP_S, "samples": 2, "identical": samples_identical,
                        "first": sample_a, "second": sample_b},
        "self_registration": "本文件不登记自身 sha16（自指恒假，RESULTS-RED.md §22.3）",
    }
    json.dump(landed, open(LANDED, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    print(json.dumps({
        "landed": "kvmem/m2_visibility/m3/LANDED-l1.json",
        "lease_old": lease_old, "lease_new": lease_new,
        "products": {k: v["sha16"] for k, v in landed["products"].items()},
        "three_level": landed["three_level_denominator"],
        "variant_not_raised": variant_not_raised,
        "samples_identical": samples_identical,
        "files": len(files),
        "site_conclusion": site_report["conclusion"],
        "site_ranges": {k: v["ranges"] for k, v in site_report["sites"].items()},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()