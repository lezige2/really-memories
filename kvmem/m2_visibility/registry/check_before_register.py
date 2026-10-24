# -*- coding: utf-8 -*-
"""_before/ 登记层自检（R11）。

_before/ 只保存【人登记的副本】。允许集合是正面枚举的：
    副本          <name>@<sha16>     每条必须有登记，且 名字 / 内容 / 登记 三者同值
    REGISTER.json
其余条目一律违规，并把违规项的文件名逐个列出（不是只印一个 False）。

运行时生成并立刻 import 的 scratch 模块已搬到 TEMP（见 m4_verify_grounded.py 的
load_pre_module 与 m5_fix_compare.py 的 load_pre），所以 _before 里再出现裸 .py 或
__pycache__ 就是真的违规 —— scratch 搬走之前，它们每次运行都会出现。

断言：
  (1) 每条登记 -> copy_path 必须【是文件】（os.path.isfile，不是 exists），basename 非空，
      路径确实在这个 _before 里；且 名字里的 sha16 == 内容重算 == 登记里的 source_sha16；
      且 copyist / copy_time / reason 三项齐全
  (2) 磁盘上每个带 @sha 的副本 -> 必须有登记
  (3) 允许集合之外的条目 -> 违规并列出文件名

能红：--selftest 在临时目录里造三种坏输入（删副本 / 改一字节 / 清 reason），逐条要求抓住；
所有改动只在临时目录内发生（改证据的自检比没有自检更糟）。

用法：
  python -X utf8 check_before_register.py
  python -X utf8 check_before_register.py --before-dir D:/x/_before
  python -X utf8 check_before_register.py --selftest
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.normpath(os.path.join(HERE, "..", "m4", "_before"))
REGISTER = "REGISTER.json"
HEX = "0123456789abcdef"
KEYS = ("register", "missing_copy", "not_a_file", "sha_mismatch", "unregistered",
        "unexpected", "changes")
REQUIRED_FIELDS = ("copyist", "copy_time", "reason")


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def split_name(name):
    """'m5_bridge.py@1a057b0feef53113' -> ('m5_bridge.py', '1a057b0feef53113')."""
    if "@" not in name:
        return name, None
    stem, _, claimed = name.rpartition("@")
    if len(claimed) != 16 or any(c not in HEX for c in claimed):
        return stem, None
    return stem, claimed


def is_copy_name(name):
    stem, claimed = split_name(name)
    return claimed is not None and stem != ""


def check(before_dir):
    d = before_dir
    problems = dict((k, []) for k in KEYS)
    regp = os.path.join(d, REGISTER)
    if not os.path.isfile(regp):
        problems["register"].append("REGISTER.json is missing or is not a file in %s" % d)
        return problems
    reg = json.load(open(regp, encoding="utf-8"))
    on_disk = sorted(os.listdir(d))
    d_abs = os.path.normcase(os.path.abspath(d))

    registered = {}
    for e in reg.get("entries", []):
        tag = "%s@%s" % (e.get("source_name"), e.get("source_sha16"))
        cp = e.get("copy_path")
        if not cp:
            problems["register"].append("entry %s holds no copy_path" % tag)
            continue
        base = os.path.basename(cp)
        if base == "":
            problems["register"].append(
                "entry %s: copy_path is a directory path, not a file: %r" % (tag, cp))
            continue
        registered[base] = e
        for field in REQUIRED_FIELDS:
            if not e.get(field):
                problems["register"].append("entry %s has no %s" % (base, field))
        if os.path.normcase(os.path.dirname(os.path.abspath(cp))) != d_abs:
            problems["register"].append("entry %s: copy_path is outside this _before: %r"
                                        % (base, cp))
        resolved = os.path.join(d, base)
        if not os.path.isfile(resolved):
            if os.path.isdir(resolved) or (os.path.exists(cp) and os.path.isdir(cp)):
                problems["not_a_file"].append({"registered": base, "copy_path": cp,
                                               "is": "directory"})
            else:
                problems["missing_copy"].append(base)
            continue
        stem, claimed = split_name(base)
        actual = sha16(resolved)
        if claimed is None or claimed != actual or e.get("source_sha16") != actual:
            problems["sha_mismatch"].append({"file": base, "name_claims": claimed,
                                             "content_is": actual,
                                             "register_says": e.get("source_sha16")})

    for f in on_disk:
        if is_copy_name(f) and f not in registered:
            problems["unregistered"].append(f)

    for f in on_disk:
        if f == REGISTER or is_copy_name(f):
            continue
        problems["unexpected"].append(f)

    # every registered anchor move must point at a copy that still holds the OLD content
    for ch in reg.get("changes", []):
        base = ch.get("copy", "")
        if base not in registered:
            problems["changes"].append("change entry names a copy with no registration: %r"
                                       % base)
            continue
        if not os.path.isfile(os.path.join(d, base)):
            problems["changes"].append("change entry %r: the old copy is gone" % base)
            continue
        stem, claimed = split_name(base)
        actual = sha16(os.path.join(d, base))
        if claimed != ch.get("from") or actual != ch.get("from"):
            problems["changes"].append(
                {"copy": base, "registered_from": ch.get("from"), "copy_claims": claimed,
                 "content_is": actual})
        if not ch.get("class") or not ch.get("why") or not ch.get("by"):
            problems["changes"].append("change entry %r lacks class / by / why" % base)
    return problems


def report(problems, before_dir):
    total = sum(len(v) for v in problems.values())
    print("before-dir: %s" % before_dir)
    copies = len([f for f in os.listdir(before_dir)
                  if os.path.isfile(os.path.join(before_dir, f)) and is_copy_name(f)])
    print("copies on disk: %d (+ %s)" % (copies, REGISTER))
    for key in KEYS:
        if problems[key]:
            print("  [%s] %d" % (key, len(problems[key])))
            for item in problems[key][:8]:
                print("      ", item)
    ok = total == 0
    print("BEFORE-REGISTER: %s (%d problem(s))" % ("PASS" if ok else "FAIL", total))
    return ok


def selftest(template_dir):
    """Three broken copies of the register, each of which must be caught.

    Every mutation happens INSIDE the temp copy: the register is rewritten so each copy_path
    points into the temp tree, and each touched path is asserted to stay under it.
    """
    results = []
    for scenario in ("delete a copy", "flip one byte", "clear a reason",
                     "corrupt a changes entry"):
        tmp = tempfile.mkdtemp(prefix="_br_selftest_")
        dst = os.path.join(tmp, "_before")
        try:
            shutil.copytree(template_dir, dst, ignore=shutil.ignore_patterns("__pycache__"))
            regp = os.path.join(dst, REGISTER)
            reg = json.load(open(regp, encoding="utf-8"))
            for e in reg["entries"]:
                cp = e.get("copy_path")
                if cp:
                    e["copy_path"] = os.path.join(dst, os.path.basename(cp)).replace(chr(92), "/")
            json.dump(reg, open(regp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            # discipline 25: the scope of a self-check is built by the self-check itself.
            # The target is chosen from the TEMP COPY's own listing -- never from a path string
            # the register hands me, because a corrupted register would then aim my pen at
            # somebody else's file.
            names = sorted(f for f in os.listdir(dst) if is_copy_name(f))
            target = os.path.join(dst, names[-1])
            assert os.path.abspath(target).startswith(os.path.abspath(tmp)), target

            if scenario == "delete a copy":
                os.remove(target)
            elif scenario == "flip one byte":
                with open(target, "ab") as fh:
                    fh.write(b" ")
            elif scenario == "corrupt a changes entry":
                reg["entries"][0]["reason"] = "kept"
                if reg.get("changes"):
                    reg["changes"][0]["from"] = "0" * 16
                json.dump(reg, open(regp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            else:
                reg["entries"][0]["reason"] = ""
                json.dump(reg, open(regp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            problems = check(dst)
            hits = dict((k, len(v)) for k, v in problems.items() if v)
            results.append((scenario, not hits, hits))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print()
    caught = True
    for scenario, stayed_green, hits in results:
        print("  %-16s -> %s" % (scenario,
                                 "NOT CAUGHT (bad)" if stayed_green else "caught: %s" % hits))
        caught = caught and not stayed_green
    print("SELFTEST: %s" % ("PASS -- every failure input was caught" if caught
                            else "FAIL -- the check can stay green on a broken register"))
    return caught


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--before-dir", default=DEFAULT_DIR)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    ok = report(check(args.before_dir), args.before_dir)
    if args.selftest:
        ok = selftest(args.before_dir) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
