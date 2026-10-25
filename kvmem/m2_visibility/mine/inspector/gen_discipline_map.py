# -*- coding: utf-8 -*-
"""由 DISCIPLINES.md + 侧车重建 SRC-CRITERIA.md 的 §12.30 纪律映射表。

为什么生成: 同一个事实写在两个文件里、同步靠人记得，就会每加一条纪律红一次（四轮来回）。
生成的东西不会忘；人写的那一栏（「它改了哪条判据」）会忘，但忘的时候它红。

三向红（--check）:
  漂移      表里的行 != 由账本+侧车重新生成的行
  未判据化  编号在账本里，侧车里没有它那一条
  幽灵行    侧车里有编号，账本里没有
退出码由调用方 `cmd > file; echo rc=$?` 读取（纪律 29）。
"""
import argparse
import io
import json
import re
import sys

I = "D:/llama-mem/kvmem/m2_visibility/mine/inspector/"
C = I + "SRC-CRITERIA.md"
D = "D:/llama-mem/kvmem/m2_visibility/mine/lead/DISCIPLINES.md"
N = I + "DISCIPLINE-CRITERION-NOTES.json"
BEGIN = "<!-- GEN:DISCIPLINE-MAP:BEGIN 本表由 gen_discipline_map.py 生成，勿手改 -->"
END = "<!-- GEN:DISCIPLINE-MAP:END -->"
LEGACY_HEAD = "**历史行（编号冲突期的旧写法，不参与生成；保留以免丢证据）**:"


def read_lines(p):
    return io.open(p, encoding="utf-8").read().replace("\r\n", "\n").splitlines()


def disciplines():
    out = {}
    for l in read_lines(D):
        m = re.match(r"^\|\s*(\d+)\s*\|\s*(.*)$", l.strip())
        if m:
            out[int(m.group(1))] = m.group(2).strip()
    return out


def sidecar():
    return json.load(io.open(N, encoding="utf-8"))


def row_re():
    return re.compile(r"^\|\s*(.*?)\s*\|\s*#(\d+)\s*\|\s*(.*?)\s*\|\s*$")


def split_region(L):
    "returns (before, inner, after) where inner is lines between the markers (or None)"
    if BEGIN in L and END in L:
        b = L.index(BEGIN)
        e = L.index(END)
        return L[:b], L[b + 1:e], L[e + 1:]
    return L, None, []


def generate(dis, notes):
    rows, missing = [], []
    for n in sorted(dis):
        e = notes.get(str(n))
        if not e:
            missing.append(n)
            rows.append("| （未判据化）| #%d | UNMAPPED —— 账本有、侧车没有；补 `DISCIPLINE-CRITERION-NOTES.json` 的 %r |" % (n, str(n)))
            continue
        rows.append("| %s | #%d | %s |" % (e.get("section") or "（未标出处）", n, e.get("note") or "UNMAPPED"))
    ghost = sorted(int(k) for k in notes if int(k) not in dis)
    return rows, missing, ghost


def legacy_rows(L):
    """同一编号出现两次的行（编号冲突期旧写法）: 逐字保留在生成区之后，避免丢证据。

    已经在文件里存在历史块时不再重发（否则每次生成都会追加一份）。
    """
    if LEGACY_HEAD in L:
        return []
    before, inner, after = split_region(L)
    pool = (before + (inner or []) + after)
    seen = {}
    for l in pool:
        m = row_re().match(l.strip())
        if m:
            seen.setdefault(int(m.group(2)), []).append(l)
    out = []
    for n in sorted(seen):
        if len(seen[n]) > 1:
            out.extend(seen[n])
    return out


def build(dis, notes, legacy):
    rows, missing, ghost = generate(dis, notes)
    block = [BEGIN, "", "| 本文件出处 | #编号 | 它改了哪条判据（可被跑） |", "|---|---|---|"] + rows + ["", END]
    if legacy:
        block += ["", LEGACY_HEAD, "", "| 旧写法 | 旧编号 | 原文 |", "|---|---|---|"] + legacy
    return block, missing, ghost


def mode_write():
    L = read_lines(C)
    dis, sc = disciplines(), sidecar()
    legacy = legacy_rows(L)
    block, missing, ghost = build(dis, sc["notes"], legacy)
    before, inner, after = split_region(L)
    if inner is not None:
        new = before + block + after
    else:
        idx = [i for i, l in enumerate(L) if row_re().match(l.strip())]
        if idx:
            new = L[:idx[0]] + block + L[idx[-1] + 1:]
        else:
            new = L + [""] + block
    io.open(C, "w", encoding="utf-8", newline="\n").write("\n".join(new) + "\n")
    print("wrote §12.30 region: %d rows (%d legacy kept) | unmapped: %s | ghost: %s"
          % (len(dis) - len(missing), len(legacy), missing or "none", ghost or "none"))
    print("SRC-CRITERIA.md now %d lines" % len(new))
    return 0 if not missing and not ghost else 1


def mode_check():
    L = read_lines(C)
    dis, sc = disciplines(), sidecar()
    problems, notes = [], []
    rows, missing, ghost = generate(dis, sc["notes"])
    if missing:
        problems.append("NOT-MAPPED: 账本有这些编号、侧车没有判据化写法: %s" % missing)
    if ghost:
        problems.append("GHOST: 侧车有这些编号、账本没有: %s" % ghost)
    before, inner, after = split_region(L)
    if inner is None:
        problems.append("NO-REGION: 文件里没有 %s / %s 标记，无法判断表是否被手改过" % (BEGIN[:24], END[:16]))
    else:
        want = [r for r in rows]
        got = [l for l in inner if row_re().match(l.strip())]
        if got != want:
            only_file = [l for l in got if l not in want]
            only_gen = [l for l in want if l not in got]
            problems.append("DRIFT: 文件里的 %d 行与重新生成的 %d 行不一致（文件多 %d / 生成多 %d），第一处差异: %r"
                            % (len(got), len(want), len(only_file), len(only_gen), (only_file or only_gen)[:1]))
        else:
            notes.append("表 == 重新生成 (%d 行)" % len(got))
    nums = [int(row_re().match(l.strip()).group(2)) for l in got_region(L)]
    if len(nums) != len(set(nums)):
        problems.append("DUP-IN-REGION: 生成区内同一编号出现两次: %s" % sorted({n for n in nums if nums.count(n) > 1}))
    for p in problems:
        print("RED:", p)
    for n in notes:
        print("  note:", n)
    print()
    print("GEN-MAP:", "PASS" if not problems else "FAIL (%d)" % len(problems))
    return 0 if not problems else 1


def got_region(L):
    before, inner, after = split_region(L)
    if inner is None:
        return []
    return [l for l in inner if row_re().match(l.strip())]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.write:
        return mode_write()
    return mode_check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))