# -*- coding: utf-8 -*-
"""隔离工具：路径越界断言 + 副本块路径重写（不接产品默认）。"""

import os


class SandboxViolation(Exception):
    pass


def assert_under(path, root):
    """要求 path 落在 root 内（realpath 归一后比较）；越界 abort。"""
    p = os.path.realpath(os.path.abspath(str(path or "")))
    r = os.path.realpath(os.path.abspath(str(root or "")))
    if not r:
        raise SandboxViolation("root 为空")
    if p != r and not p.startswith(r + os.sep):
        raise SandboxViolation("路径越界：%s 不在 %s 下" % (p, r))
    return p


def rewrite_block_paths(con, blocks_root):
    """副本 DB：把所有 memory_block.path 重写到 blocks_root/<basename>；返回映射。"""
    root = os.path.realpath(os.path.abspath(str(blocks_root or "")))
    if not root:
        raise SandboxViolation("blocks_root 为空")
    rows = con.execute("SELECT source_id,path FROM memory_block").fetchall()
    mapping = {}
    for sid, old in rows:
        base = os.path.basename(str(old or ""))
        if not base:
            continue
        new = os.path.join(root, base)
        assert_under(new, root)
        con.execute("UPDATE memory_block SET path=? WHERE source_id=?", (new, sid))
        mapping[int(sid)] = {"old": old, "new": new}
    con.commit()
    return mapping


def verify_all_under(con, blocks_root):
    for _sid, p in con.execute("SELECT source_id,path FROM memory_block"):
        assert_under(p, blocks_root)
    return True
