# -*- coding: utf-8 -*-
"""证明所有 --selftest 的作用范围真的隔离（纪律 19/25）：跑前摘要 / 跑后摘要 / 差异为空。

覆盖范围 = _before 全部文件（副本 + REGISTER）+ 判据枚举的每一个 M4 对象（含两个 .kvmem 输入盘）
           + 覆盖检查器分类到的每一个 .kvmem（含被豁免的 pos0_A —— 豁免说的是「不作锚」，不是「没人看」），
跑三个 --selftest：check_before_register / check_m4_untouched_endtoend / check_m4_kvmem_coverage。
都进覆盖，否则那个没被看管的失败输入测试本身就是纪律 19 的对象。

「我发现改坏了又改回来」只证明我会修；这一段证明的是【不可能改坏】。
"""
import hashlib
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
M4 = os.path.normpath(os.path.join(HERE, "..", "m4"))
BEFORE = os.path.join(M4, "_before")
SELFTESTS = (os.path.join(HERE, "check_before_register.py"),
             os.path.join(HERE, "check_m4_untouched_endtoend.py"),
             os.path.join(HERE, "check_m4_kvmem_coverage.py"))


def enumerated_objects():
    """The judged objects + every .kvmem the coverage checker classifies (so an exempted
    artifact is watched too -- an exemption is about anchoring, not about being ignored)."""
    sys.path.insert(0, M4)
    spec = importlib.util.spec_from_file_location("mv_iso", os.path.join(M4,
                                                                        "m4_verify_grounded.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rels = [rel for rel, _anchor in mod.M4_UNTOUCHED]
    sys.path.insert(0, HERE)
    import check_m4_kvmem_coverage as cov
    for rel in cov.enumerate_files(cov.CLASSIFY):
        if rel not in rels:
            rels.append(rel)
    return rels


def snapshot(extra):
    out = {}
    for dirpath, dirnames, filenames in os.walk(BEFORE):
        dirnames.sort()
        for f in sorted(filenames):
            p = os.path.join(dirpath, f)
            rel = "m4/_before/" + os.path.relpath(p, BEFORE).replace(os.sep, "/")
            with open(p, "rb") as fh:
                out[rel] = hashlib.sha256(fh.read()).hexdigest()
    for rel in extra:
        p = os.path.join(M4, rel.replace("/", os.sep))
        if os.path.exists(p):
            with open(p, "rb") as fh:
                out["m4/" + rel] = hashlib.sha256(fh.read()).hexdigest()
    return out


def digest(snap):
    blob = "".join("%s %s" % (k, snap[k]) for k in sorted(snap))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def main():
    extra = enumerated_objects()
    pre = snapshot(extra)
    print("scope : %d file(s) = _before %d + enumerated M4 objects %d"
          % (len(pre), len([k for k in pre if k.startswith("m4/_before/")]), len(extra)))
    print("pre   : %d file(s), digest=%s" % (len(pre), digest(pre)))
    rc = 0
    for tool in SELFTESTS:
        proc = subprocess.run([sys.executable, "-X", "utf8", tool, "--selftest"],
                              capture_output=True, text=True, encoding="utf-8")
        tail = [l for l in proc.stdout.strip().splitlines()
                if l.startswith("SELFTEST:") or l.startswith("E2E-RED")]
        print("%-28s %s (exit %d)" % (os.path.basename(tool),
                                      tail[-1] if tail else "no verdict", proc.returncode))
        rc = rc or proc.returncode
    post = snapshot(extra)
    print("post  : %d file(s), digest=%s" % (len(post), digest(post)))
    diff = [k for k in sorted(set(pre) | set(post)) if pre.get(k) != post.get(k)]
    print("diff  : %s" % ("[] (empty)" if not diff else diff))
    ok = not diff and rc == 0 and digest(pre) == digest(post)
    print("ISOLATION: %s" % ("PASS -- the self-checks touched nothing they are testing" if ok
                             else "FAIL -- a self-check changed the evidence"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
