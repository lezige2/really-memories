# -*- coding: utf-8 -*-
"""F11：.kvmem 枚举完整性 —— 枚举根、名字模式、每一项的取舍理由，三者写死。

三个人对「m4 下有几个 .kvmem」数出 9 / 3 / 2，因为根和模式都没写：
    根 m2_visibility/  **/*.kvmem 递归 => 9（含 runs_m14b 的 6 个，那不是 m4 的账）
    根 m4/            **/*.kvmem 递归 => 3（两个 blk_conv* + pos0_A）
    根 m4/            blocks/blk_*.kvmem 等 => 2
本工具写死的是第三行：根 = kvmem/m2_visibility/m4/，模式 = blocks/blk_*.kvmem +
_ablate/blocks/blk_*.kvmem。匹配用 os.walk + fnmatch，不用 glob —— glob 若忘记 recursive=True
会把 ** 静默当成单层，于是 3 变 2（检测员实测踩到过）。

三条腿：
  A 断言 1（检测员给的形态）：(枚举 - M4_UNTOUCHED - EXCLUDED) 非空 => 红，**打印缺失文件名**
  B 分类完整性：blocks/*.kvmem + _ablate/blocks/*.kvmem 每个都必须在 M4_UNTOUCHED ∪ EXCLUDED 里
                （否则「因为不在 glob 里所以自然不算」就是负定义 —— 不许）
  C 豁免不空转：EXCLUDED 的每一项都必须真的出现在 B 的枚举结果里

缺的不是锚值（_stage3_pre.json 记得很全），是「它在清单上」这件事。补数据时人会去查还缺什么；
补引用时人只会在下次缺的时候才发现缺过 —— 所以这条断言必须常驻。

用法：
  python -X utf8 check_m4_kvmem_coverage.py
  python -X utf8 check_m4_kvmem_coverage.py --selftest
"""
import argparse
import fnmatch
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
M4 = os.path.normpath(os.path.join(HERE, "..", "m4"))

ENUM_ROOT = M4
MUST_BE_ANCHORED = ("blocks/blk_*.kvmem", "_ablate/blocks/blk_*.kvmem")
CLASSIFY = ("blocks/*.kvmem", "_ablate/blocks/*.kvmem")

# 豁免清单：每项一个理由，且理由要经得起别人复核（谁读 / 与谁同源 / 本步读不读）
EXCLUDED = [
    {"name": "blocks/pos0_A.kvmem",
     "why": "① 谁读：m4_pos0_refuse.py:43 取这个路径做 eng.save(SEQ, path)，:31/:36/:45 还把它"
            "注册成 lease 与 block（pos0 拒绝用例）。"
            "② 与谁同源：内容 sha16 = 73843fc55efd1ab3、2194932 B，与 "
            "runs_m14b/encode_pass2/home.kvmem 及 runs_m14b/aborted_run1_home.kvmem 逐字节同值 "
            "=> 它是某次 encode 的派生物，不是独立输入。"
            "③ 本步读不读：_stage3_pre.json / run_stage3.py / run_m5_grounded.json 里 pos0_A 出现 0 次"
            "（grep -c）=> Stage 3 不读它。按纪律 24，会被正常流程重写的量也不能作锚。"},
]


def load_mod():
    sys.path.insert(0, M4)
    spec = importlib.util.spec_from_file_location("mv_cov", os.path.join(M4,
                                                                       "m4_verify_grounded.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def enumerate_files(patterns):
    out = set()
    for dirpath, dirnames, filenames in os.walk(ENUM_ROOT):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in filenames:
            rel = os.path.relpath(os.path.join(dirpath, f), ENUM_ROOT).replace(os.sep, "/")
            for pattern in patterns:
                if fnmatch.fnmatchcase(rel, pattern):
                    out.add(rel)
                    break
    return sorted(out)


def coverage(mod, excluded):
    names = [e["name"] for e in excluded]
    anchored = set(rel for rel, _a in mod.M4_UNTOUCHED if rel.endswith(".kvmem"))
    must = enumerate_files(MUST_BE_ANCHORED)
    every = enumerate_files(CLASSIFY)
    missing = [r for r in must if r not in anchored]
    unclassified = [r for r in every if r not in anchored and r not in names]
    stale = [n for n in names if n not in every]
    thin = [e["name"] for e in excluded if len((e.get("why") or "").strip()) < 40]
    return {"root": ENUM_ROOT.replace(os.sep, "/"),
            "must_be_anchored": must, "classified_root": every,
            "anchored": sorted(anchored),
            "missing_from_checklist": missing,
            "unclassified": unclassified,
            "stale_exemptions": stale,
            "exemptions_without_a_real_reason": thin,
            "ok": not missing and not unclassified and not stale and not thin}


def report(res):
    print("enum root : %s" % res["root"])
    print("patterns  : must-anchor %s | classify %s"
          % (list(MUST_BE_ANCHORED), list(CLASSIFY)))
    print("anchored  : %s" % res["anchored"])
    if res["missing_from_checklist"]:
        print("MISSING (on disk, not on the checklist): %s" % res["missing_from_checklist"])
    if res["unclassified"]:
        print("UNCLASSIFIED (neither anchored nor exempted): %s" % res["unclassified"])
    if res["stale_exemptions"]:
        print("STALE EXEMPTION (names a file that is not there): %s" % res["stale_exemptions"])
    if res["exemptions_without_a_real_reason"]:
        print("THIN EXEMPTION (no usable reason): %s" % res["exemptions_without_a_real_reason"])
    print("KVMEY-COVERAGE: %s" % ("PASS" if res["ok"] else "FAIL"))


def selftest():
    mod = load_mod()
    base = list(mod.M4_UNTOUCHED)
    results = []
    try:
        victim = "blocks/blk_conv_2026-10-25_01.kvmem"
        mod.M4_UNTOUCHED = [t for t in base if t[0] != victim]
        r1 = coverage(mod, EXCLUDED)
        results.append(("drop an anchored entry", not r1["ok"], r1["missing_from_checklist"]))

        mod.M4_UNTOUCHED = base
        r2 = coverage(mod, [])
        results.append(("exempt nothing (pos0_A unclassified)", not r2["ok"],
                        r2["unclassified"]))

        r3 = coverage(mod, EXCLUDED + [{"name": "blocks/nope.kvmem", "why": "x" * 50}])
        results.append(("exempt a nonexistent file", not r3["ok"], r3["stale_exemptions"]))

        r4 = coverage(mod, [{"name": "blocks/pos0_A.kvmem", "why": "派生物"}])
        results.append(("exemption with no real reason", not r4["ok"],
                        r4["exemptions_without_a_real_reason"]))
    finally:
        mod.M4_UNTOUCHED = base
    print()
    ok = True
    for name, turned_red, names in results:
        print("  %-38s -> %s" % (name, ("red, names=%s" % names) if turned_red
                                 else "STAYED GREEN (bad)"))
        ok = ok and turned_red and bool(names)
    print("SELFTEST: %s" % ("PASS -- every failure input turned it red and named the file"
                            if ok else "FAIL -- the check can stay green or print no filename"))
    return ok


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    mod = load_mod()
    res = coverage(mod, EXCLUDED)
    report(res)
    for e in EXCLUDED:
        print("exempt    : %s" % e["name"])
    ok = res["ok"]
    if args.selftest:
        ok = selftest() and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
