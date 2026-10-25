# -*- coding: utf-8 -*-
"""L2 补正批次（task-27）驱动 + 台账：`kvmem/m2_visibility/m3/LANDED-l2.json`（v2，含 addendum）。

四项补正：
① `variant_rollback`（整体回退到 L1 版，保留）与 `variant_b`（落地版只删未命中分支、保留
   `unbooked_count` 初始化）分开；② 每例 `drop_delta_on_unbooked`（只在被拒绝那次调用上测）；
③ `U4_non_strict_miss` 进扩展床，分母两套并列（主 4 例 / 扩展 5 例）；④ `land_l2.py` 入账。
原批次读数不抹掉：进 `addendum.original`（原台账 sha 记 `550faba2fde22a79`）。

本文件不登记自身 sha（§22.3）。
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
BEFORE = os.path.join(HERE, "_before")
LANDED = os.path.join(HERE, "LANDED-l2.json")
GAP_S = 31
PY = sys.executable
ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
TEST = os.path.join(HERE, "_test_lease_detach.py")


def mpath(rel):
    """m3 目录内的相对路径（产物都在 m3/out 下，不在仓库根）。"""
    return os.path.join(HERE, rel)


def sha16(p):
    with open(p, "rb") as f:                       # 二进制读，不过文本层
        return hashlib.sha256(f.read()).hexdigest()[:16]


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=ENV, cwd=ROOT, **kw)


def make_variant_b(dst_dir):
    """落地版：只把 `detach` 的「未命中检测 + 抛错」分支换回旧实现，`__init__` 原样保留。"""
    cur = io.open(os.path.join(HERE, "m3_lease.py"), encoding="utf-8").read()
    old = io.open(os.path.join(BEFORE, "m3_lease.py@675f983f8d02f1df"), encoding="utf-8").read()

    def slice_func(src):
        i = src.index("    def detach(self, dst_seq, lo, hi):")
        j = src.index("    # -- gated destruction", i)
        return src[i:j]

    cur_detach, old_detach = slice_func(cur), slice_func(old)
    assert "unbooked_detach" in cur_detach and "unbooked_detach" not in old_detach
    variant = cur.replace(cur_detach, old_detach)
    p = os.path.join(dst_dir, "m3_lease.py")
    io.open(p, "w", encoding="utf-8", newline="\n").write(variant)
    return p


def main():
    tmp = tempfile.mkdtemp(prefix="l2_variants_")
    # 变体材料：L1 后态（675f983f）与 variant_b
    rollback_src = os.path.join(tmp, "rollback_mod", "m3_lease.py")
    os.makedirs(os.path.dirname(rollback_src), exist_ok=True)
    shutil.copyfile(os.path.join(BEFORE, "m3_lease.py@675f983f8d02f1df"), rollback_src)
    variant_b_src = make_variant_b(tmp)

    jobs = {
        "out/M3-L2-pre-v2.json": [PY, "-X", "utf8", TEST, "--lease", rollback_src,
                                  "--out", os.path.join(OUT, "M3-L2-pre-v2.json")],
        "out/M3-L2-after-v2.json": [PY, "-X", "utf8", TEST,
                                    "--out", os.path.join(OUT, "M3-L2-after-v2.json")],
        "out/M3-L2-variant-b.json": [PY, "-X", "utf8", TEST, "--lease", variant_b_src,
                                     "--out", os.path.join(OUT, "M3-L2-variant-b.json")],
        "out/M3-L2-variant-rollback-v2.json": [
            PY, "-X", "utf8", TEST, "--lease", rollback_src,
            "--out", os.path.join(OUT, "M3-L2-variant-rollback-v2.json")],
        "out/M3-L1-recheck-after-L2-v2.json": [
            PY, "-X", "utf8", os.path.join(HERE, "_test_lease_overlap.py"),
            "--out", os.path.join(OUT, "M3-L1-recheck-after-L2-v2.json")],
    }
    runs = {}
    for name, args in jobs.items():
        r = run(args)
        runs[name] = {"exit": r.returncode, "tail": r.stdout.strip().splitlines()[-1:]}
    suite = run([PY, "-X", "utf8", os.path.join(HERE, "_test_lease.py")])
    freeze = run([PY, "tools/freeze_check.py"])

    files = {
        "m3_lease.py": os.path.join(HERE, "m3_lease.py"),
        "_test_lease_detach.py": TEST,
        "_test_lease_overlap.py": os.path.join(HERE, "_test_lease_overlap.py"),
        "_test_lease.py": os.path.join(HERE, "_test_lease.py"),
        "land_l2.py": os.path.join(HERE, "land_l2.py"),
        "land_l1.py": os.path.join(HERE, "land_l1.py"),
        "before/m3_lease.py@675f983f8d02f1df": os.path.join(
            BEFORE, "m3_lease.py@675f983f8d02f1df"),
        "before/m3_lease.py@37a0a6f4b8ea1154": os.path.join(
            BEFORE, "m3_lease.py@37a0a6f4b8ea1154"),
        "tools/chat_lease.py": os.path.join(ROOT, "tools", "chat_lease.py"),
        "tools/freeze_check.py": os.path.join(ROOT, "tools", "freeze_check.py"),
        "kvmem/chat.db": os.path.join(ROOT, "kvmem", "chat.db"),
    }
    for name in jobs:
        files[name] = mpath(name)
    # 原批次保留的产物
    retained = {
        "out/M3-L2-pre.json": "改前红（首次，4/1/3、drop 5）",
        "out/M3-L2-after.json": "落地后（首次，4/1/3、drop 2）",
        "out/M3-L2-variant.json": "整体回退到 L1 版（现改名/改标注 = variant_rollback）",
        "out/M3-L1-recheck-after-L2.json": "L1 回归（首次）",
    }
    for name in retained:
        files[name] = mpath(name)

    a = {k: sha16(p) for k, p in files.items()}
    sizes = {k: os.path.getsize(p) for k, p in files.items()}

    def load(name):
        return json.load(open(mpath(name), encoding="utf-8"))

    pre = load("out/M3-L2-pre-v2.json")
    aft = load("out/M3-L2-after-v2.json")
    vb = load("out/M3-L2-variant-b.json")
    vr = load("out/M3-L2-variant-rollback-v2.json")
    l1 = load("out/M3-L1-recheck-after-L2-v2.json")
    prev = load("out/M3-L2-pre.json")
    prev_after = load("out/M3-L2-after.json")
    prev_var = load("out/M3-L2-variant.json")

    print("采样间隔 %ds ..." % GAP_S)
    time.sleep(GAP_S)
    b = {k: sha16(p) for k, p in files.items()}

    landed = {
        "schema": "landed_l2_v2",
        "batch_id": "m2full-l2-v2",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "supersedes": {
            "batch": "m2full-l2",
            "ledger_self_sha16": "550faba2fde22a79",
            "ledger_bytes": 6928,
            "note": "task-27 四项补正；原批次读数全文保留在 addendum.original，不抹掉",
        },
        "addendum": {
            "why": "task-27：① variant_rollback/variant_b 分离 ② 补 drop_delta_on_unbooked "
                   "③ 非 strict 补测 U4（两套分母）④ land_l2.py 入账",
            "original": {
                "products": {k: {"sha16": sha16(mpath(k)),
                                 "meaning": retained[k]} for k in retained},
                "three_level_denominator": prev["three_level_denominator"],
                "drop_calls_total": {"before": prev["drop_calls_total"],
                                     "after": prev_after["drop_calls_total"]},
                "variant": {"sha16": sha16(mpath("out/M3-L2-variant.json")),
                            "fail_cases": prev_var["fail_cases"],
                            "reading": "整体回退到 L1 版：H1 也红（缺 unbooked_count 属性），"
                                       "非 H1 行为坏；本 v2 起标注为 variant_rollback"},
                "old_ledger_self_sha16": "550faba2fde22a79",
            },
        },
        "change": {
            "file": "kvmem/m2_visibility/m3/m3_lease.py",
            "funcs": ["BlockLeases.__init__", "BlockLeases.detach", "BlockLeases docstring"],
            "l1_after_sha16": "675f983f8d02f1df",
            "l2_main_sha16": "37a0a6f4b8ea1154",
            "new_sha16": a["m3_lease.py"],
            "l2_main_bytes": sizes["before/m3_lease.py@37a0a6f4b8ea1154"],
            "new_bytes": sizes["m3_lease.py"],
            "after_main_note": "L2 主改动（get+记账+strict 抛/非 strict 留痕 drop）",
            "v2_delta": "仅类 docstring 补一句「记账与事件不关、只有 raise 关」（行为不变）",
        },
        "before_copies": {
            "_before/m3_lease.py@675f983f8d02f1df": {
                "sha16": a["before/m3_lease.py@675f983f8d02f1df"],
                "bytes": sizes["before/m3_lease.py@675f983f8d02f1df"],
                "role": "L1 后态 = L2 改前（施工前拷贝）"},
            "_before/m3_lease.py@37a0a6f4b8ea1154": {
                "sha16": a["before/m3_lease.py@37a0a6f4b8ea1154"],
                "bytes": sizes["before/m3_lease.py@37a0a6f4b8ea1154"],
                "role": "L2 主改动后态 = docstring 补正前（施工前拷贝）"},
        },
        "three_level_denominator": {
            "main_4": dict(aft["three_level_denominator"]),
            "extended_5": dict(aft["extended_three_level_denominator"]),
            "note": "两套并列不合并：主床与 pre 可比；扩展床含 U4_non_strict_miss",
            "pre_main_4": dict(pre["three_level_denominator"]),
        },
        "drop_delta_on_unbooked": {
            "after": aft["drop_delta_on_unbooked"],
            "pre": pre["drop_delta_on_unbooked"],
            "variant_b": vb["drop_delta_on_unbooked"],
            "expected": {"H1_hit": 1, "U1_never_attached": 0, "U2_table_drift_pop": 0,
                         "U3_second_detach": 0, "U4_non_strict_miss": 1},
        },
        "drop_calls_total": {
            "pre_v2_total": pre["drop_calls_total"],
            "pre_v2_main": pre["drop_calls_total_main"],
            "after_v2_total": aft["drop_calls_total"],
            "after_v2_main": aft["drop_calls_total_main"],
            "first_batch": {"before": 5, "after": 2},
        },
        "variants": {
            "variant_rollback": {
                "product": "out/M3-L2-variant-rollback-v2.json",
                "module_sha16": vr["lease_module"]["sha16"],
                "meaning": "整体回退到 L1 版（675f983f 字节）",
                "fail_cases": vr["fail_cases"],
                "unbooked_observed": vr["extended_three_level_denominator"]["unbooked_observed"],
                "drop_calls_total": vr["drop_calls_total"],
                "caveat": "H1 也红是因为该模块没有 unbooked_count 属性，不代表 H1 行为坏",
                "retained_first": "out/M3-L2-variant.json（同一构造，首次批次）",
            },
            "variant_b": {
                "product": "out/M3-L2-variant-b.json",
                "module_sha16": vb["lease_module"]["sha16"],
                "meaning": "落地版只删「未命中检测+抛错」分支，保留 unbooked_count 初始化",
                "fail_cases": vb["fail_cases"],
                "h1_ok": next(r["ok"] for r in vb["rows"] if r["case"] == "H1_hit"),
                "unbooked_observed": vb["extended_three_level_denominator"]["unbooked_observed"],
                "drop_calls_total": vb["drop_calls_total"],
                "load_bearing": "H1 绿 + U1–U3（及 U4）红 ⇒ 承重的是未命中分支本身",
            },
        },
        "products": {
            "out/M3-L2-pre-v2.json": {"sha16": a["out/M3-L2-pre-v2.json"],
                                      "bytes": sizes["out/M3-L2-pre-v2.json"],
                                      "meaning": "改前红（带 drop_delta_on_unbooked 与新分母）",
                                      "exit": runs["out/M3-L2-pre-v2.json"]["exit"]},
            "out/M3-L2-after-v2.json": {"sha16": a["out/M3-L2-after-v2.json"],
                                        "bytes": sizes["out/M3-L2-after-v2.json"],
                                        "meaning": "落地后：主床 4 例全绿 + 扩展 U4 绿",
                                        "exit": runs["out/M3-L2-after-v2.json"]["exit"]},
            "out/M3-L2-variant-b.json": {"sha16": a["out/M3-L2-variant-b.json"],
                                         "bytes": sizes["out/M3-L2-variant-b.json"],
                                         "meaning": "隔离变体：只删未命中分支",
                                         "exit": runs["out/M3-L2-variant-b.json"]["exit"]},
            "out/M3-L2-variant-rollback-v2.json": {
                "sha16": a["out/M3-L2-variant-rollback-v2.json"],
                "bytes": sizes["out/M3-L2-variant-rollback-v2.json"],
                "meaning": "整体回退到 L1 版（variant_rollback，带新字段重跑）",
                "exit": runs["out/M3-L2-variant-rollback-v2.json"]["exit"]},
            "out/M3-L1-recheck-after-L2-v2.json": {
                "sha16": a["out/M3-L1-recheck-after-L2-v2.json"],
                "bytes": sizes["out/M3-L1-recheck-after-L2-v2.json"],
                "meaning": "L1 回归：11/11",
                "exit": runs["out/M3-L1-recheck-after-L2-v2.json"]["exit"]},
            "out/M3-L2-variant.json": {"sha16": sha16(mpath("out/M3-L2-variant.json")),
                                       "bytes": os.path.getsize(mpath("out/M3-L2-variant.json")),
                                       "meaning": "保留：首次批次的 variant（现标注 variant_rollback）"},
        },
        "regression": {
            "l1_cases": l1["three_level_denominator"]["constructed"],
            "l1_rejected": l1["three_level_denominator"]["rejected"],
            "l1_true_hits": l1["three_level_denominator"]["true_hits"],
            "l1_fail_cases": l1["fail_cases"],
            "l1_ok": not l1["fail_cases"],
            "existing_suite_sha16": a["_test_lease.py"],
            "existing_suite_tail": (suite.stdout.strip().splitlines() or [""])[-1],
            "existing_suite_exit": suite.returncode,
            "freeze_exit": freeze.returncode,
            "freeze_line": (freeze.stdout.strip().splitlines() or [""])[-1],
            "chat_lease_sha16": a["tools/chat_lease.py"],
            "chat_lease_unchanged": a["tools/chat_lease.py"] == "619a043215035de7",
            "chat_db_sha16": a["kvmem/chat.db"],
            "chat_db_unchanged": a["kvmem/chat.db"] == "237d8e1f5de9a382",
        },
        "tooling": {
            "land_l2.py": {"sha16": a["land_l2.py"], "bytes": sizes["land_l2.py"],
                           "role": "本补正批次的驱动脚本（task-27 ④ 补入账）"},
            "land_l1.py": {"sha16": a["land_l1.py"], "bytes": sizes["land_l1.py"],
                           "role": "L1 施工脚本（补录）"},
        },
        "files": {k: {"sha16": a[k], "bytes": sizes[k]} for k in files},
        "recompute": {"files_recomputed": len(files),
                      "mismatched": [k for k in files if sha16(files[k]) != a[k]]},
        "two_samples": {"gap_s": GAP_S, "samples": 2, "identical": a == b,
                        "first": a, "second": b},
        "self_registration": "本文件不登记自身 sha16（自指恒假，RESULTS-RED.md §22.3）",
    }
    json.dump(landed, open(LANDED, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    print(json.dumps({
        "new_m3_lease": a["m3_lease.py"], "bytes": sizes["m3_lease.py"],
        "products": {k: v["sha16"] for k, v in landed["products"].items()},
        "denom_main": {k: landed["three_level_denominator"]["main_4"][k]
                       for k in ("detach_calls", "hits", "unbooked", "unbooked_observed")},
        "denom_ext": {k: landed["three_level_denominator"]["extended_5"][k]
                      for k in ("detach_calls", "hits", "unbooked", "unbooked_observed")},
        "drop_on_unbooked": aft["drop_delta_on_unbooked"],
        "drop_total": {"pre": pre["drop_calls_total"], "after": aft["drop_calls_total"],
                       "after_main": aft["drop_calls_total_main"]},
        "variant_b": landed["variants"]["variant_b"],
        "rollback": {k: landed["variants"]["variant_rollback"][k]
                     for k in ("module_sha16", "fail_cases", "drop_calls_total")},
        "l1_ok": landed["regression"]["l1_ok"],
        "suite": landed["regression"]["existing_suite_tail"],
        "freeze_exit": freeze.returncode,
        "samples_identical": a == b,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()