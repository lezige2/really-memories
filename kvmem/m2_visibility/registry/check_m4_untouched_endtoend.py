# -*- coding: utf-8 -*-
"""R12 的端到端红（F9）：在生产目录的一份【副本】上把已枚举对象改一个字节，判据必须红。

做法照 R11，一条不同（纪律 25）：
  * 被改的文件**从临时树自己的 listdir 里挑**，不拿 M4_UNTOUCHED 给的路径去定位生产文件；
  * 改完断言被改的绝对路径 startswith(临时目录) —— 改的是副本，要能证明。

判据代码本身一行未改：测试只把模块常量 HERE 指向临时树，走的是同一条代码路径，
因此不会因为一次测试就让所有锚作废重跑。

  python -X utf8 check_m4_untouched_endtoend.py [--selftest]
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
M4 = os.path.normpath(os.path.join(HERE, "..", "m4"))


def load_module():
    sys.path.insert(0, M4)
    spec = importlib.util.spec_from_file_location("mv_e2e", os.path.join(M4,
                                                                        "m4_verify_grounded.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pick_target(dst, enumerated):
    """Choose the file to touch from the TEMP COPY's own listing.

    discipline 25: the scope of the check is built by the check itself. The enumerated set
    supplies NAMES only (which objects the judgement is about); no path is ever taken from it
    and applied outside the temp tree.
    """
    found = []
    for dirpath, dirnames, filenames in os.walk(dst):
        dirnames[:] = [d for d in dirnames if d != "_before" and d != "__pycache__"]
        for f in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, f), dst).replace(os.sep, "/")
            if rel in enumerated:
                found.append(rel)
    if not found:
        raise SystemExit("no enumerated object found inside the temp copy")
    return sorted(found)[0]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="same thing; this tool IS a self-check")
    args = ap.parse_args(argv)
    mod = load_module()
    enumerated = set(rel for rel, _anchor in mod.M4_UNTOUCHED)
    real_here = mod.HERE
    tmp = tempfile.mkdtemp(prefix="_m4_untouched_")
    dst = os.path.join(tmp, "m4")
    ok = False
    try:
        shutil.copytree(real_here, dst, ignore=shutil.ignore_patterns("__pycache__"))
        mod.HERE = dst
        control = mod.m4_files_untouched_or_registered()
        print("control (temp copy, untouched): ok = %s, objects = %d"
              % (control["ok"], len(control["objects"])))
        if not control["ok"]:
            print("  control already red:", control["_failures"])
            return 1

        rel = pick_target(dst, enumerated)
        target = os.path.join(dst, rel.replace("/", os.sep))
        inside = os.path.abspath(target).startswith(os.path.abspath(tmp))
        print("picked from temp listdir    : %s" % rel)
        print("mutating                    : %s"
              % target.replace(os.sep, "/").replace(tmp.replace(os.sep, "/"), "$TMP"))
        with open(target, "ab") as fh:
            fh.write(b" ")
        red = mod.m4_files_untouched_or_registered()
        print("after one appended byte      : ok = %s" % red["ok"])
        print("failures                     : %s" % red["_failures"])
        print("detail                       : %s"
              % json.dumps(red["objects"][rel], ensure_ascii=False)[:170])
        print("mutated path inside $TMP     : %s" % inside)
        ok = (red["ok"] is False) and (rel in red["_failures"]) and inside
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        mod.HERE = real_here
    real = mod.m4_files_untouched_or_registered()
    print("production tree after test   : ok = %s (untouched)" % real["ok"])
    ok = ok and real["ok"]
    print("E2E-RED R12: %s" % ("PASS -- the judgement goes red on a changed enumerated object"
                              if ok else "FAIL -- the judgement stayed green"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
