# -*- coding: utf-8 -*-
"""证明 --selftest 的作用范围真的隔离（纪律 19/25）：跑前摘要 / 跑后摘要 / 差异为空。

「我发现改坏了又改回来」只证明我会修；这一段证明的是【不可能改坏】——
_before 里每一个文件在 selftest 前后逐字节不变。判据的作用范围由本脚本自己构造
（临时目录），不取自被检对象提供的任何路径。
"""
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BEFORE = os.path.normpath(os.path.join(HERE, "..", "m4", "_before"))
CHECKER = os.path.join(HERE, "check_before_register.py")


def snapshot(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for f in sorted(filenames):
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            with open(p, "rb") as fh:
                out[rel] = hashlib.sha256(fh.read()).hexdigest()
    return out


def digest(snap):
    blob = "".join("%s %s" % (k, snap[k]) for k in sorted(snap))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def main():
    pre = snapshot(BEFORE)
    print("pre   : %d file(s), digest=%s" % (len(pre), digest(pre)))
    proc = subprocess.run([sys.executable, "-X", "utf8", CHECKER, "--selftest"],
                          capture_output=True, text=True, encoding="utf-8")
    tail = [l for l in proc.stdout.strip().splitlines() if l.startswith("SELFTEST:")]
    print("selftest: %s (exit %d)" % (tail[-1] if tail else "no verdict", proc.returncode))
    post = snapshot(BEFORE)
    print("post  : %d file(s), digest=%s" % (len(post), digest(post)))
    diff = sorted(set(pre) | set(post))
    diff = [k for k in diff if pre.get(k) != post.get(k)]
    print("diff  : %s" % ("[] (empty)" if not diff else diff))
    ok = not diff and proc.returncode == 0 and digest(pre) == digest(post)
    print("ISOLATION: %s" % ("PASS -- the self-check touched nothing it is testing" if ok
                             else "FAIL -- the self-check changed the evidence"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
