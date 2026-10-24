# -*- coding: utf-8 -*-
"""禁止「同一表达式/语句内先截断后读」（纪律 21）。

事故原样：
    io.open(p, 'w').write(io.open(p).read().replace(a, b))
"w" 在参数求值之前就完成了截断 —— 先清空再读，得 0 字节，原文不可恢复。

判据：同一条语句里同时出现
    (a) 打开同一路径用于写入（mode 字面量含 'w'）的调用，与
    (b) 一个 open(...).read() / .readlines() 调用
即违规。判据的样例在 fixtures/truncate_then_read_sample.py 里 —— --selftest 要求它必须被命中，
否则这条检查就是一条永远不会红的断言。

用法：
  python -X utf8 check_truncate_then_read.py                  # 扫仓库
  python -X utf8 check_truncate_then_read.py --root kvmem
  python -X utf8 check_truncate_then_read.py --selftest        # 样例必须被命中
"""
import argparse
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
FIXTURE_DIR = os.path.join(HERE, "fixtures")
SAMPLE = "truncate_then_read_sample.py"
SKIP_DIRS = {"__pycache__", ".git", "fixtures", "_before", "node_modules"}


def _mode_literal(call):
    if not isinstance(call, ast.Call):
        return None
    name = getattr(call.func, "id", None) or getattr(call.func, "attr", None)
    if name != "open":
        return None
    if len(call.args) > 1 and isinstance(call.args[1], ast.Constant):
        return call.args[1].value
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return "r"


def _opens_for_write(stmt):
    out = []
    for node in ast.walk(stmt):
        mode = _mode_literal(node)
        if isinstance(mode, str) and "w" in mode:
            out.append(node.lineno)
    return out


def _reads_in_same_statement(stmt):
    out = []
    for node in ast.walk(stmt):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) in ("read", "readlines"):
            # the receiver must be an open(...) call (or a Path read of the same shape)
            recv = node.func.value
            if isinstance(recv, ast.Call) and (getattr(recv.func, "id", None)
                                              or getattr(recv.func, "attr", None)) == "open":
                out.append(node.lineno)
    return out


# only SIMPLE statements: a compound statement (with/for/if/def) spans many statements, and
# treating it as one would flag a file that writes in one place and reads in another
SIMPLE = (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr, ast.Return, ast.Assert,
          ast.Delete, ast.Raise)


def scan_file(path):
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except (SyntaxError, UnicodeDecodeError):
        return []
    hits = []
    for stmt in ast.walk(tree):
        if not isinstance(stmt, SIMPLE):
            continue
        writes = _opens_for_write(stmt)
        reads = _reads_in_same_statement(stmt)
        if writes and reads:
            hits.append({"path": path.replace(os.sep, "/"), "line": min(writes),
                         "also_reads_at": sorted(set(reads))})
    return hits


def scan(root):
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                hits.extend(scan_file(os.path.join(dirpath, f)))
    return hits


def report(hits):
    for h in hits:
        print("  [truncate-then-read] %s:%d (read at %s)" % (h["path"], h["line"],
                                                            h["also_reads_at"]))
    ok = not hits
    print("TRUNCATE-THEN-READ: %s (%d hit(s))" % ("PASS" if ok else "FAIL", len(hits)))
    return ok


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=REPO)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    ok = report(scan(args.root))
    if args.selftest:
        sample = os.path.join(FIXTURE_DIR, SAMPLE)
        hits = scan_file(sample) if os.path.isfile(sample) else []
        print("  selftest sample: %s -> %s" % (sample.replace(os.sep, "/"),
                                               "caught at line %d" % hits[0]["line"] if hits
                                               else "NOT CAUGHT (bad)"))
        ok = ok and bool(hits)
        print("SELFTEST: %s" % ("PASS -- the sample is caught" if hits
                                else "FAIL -- the rule cannot see its own sample"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
