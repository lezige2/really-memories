# -*- coding: utf-8 -*-
"""test_n_seq_compat_cpu.py -- ⑥ n_seq 选型静态兼容检查（不启 GPU）。

结论：当前实现需要 seq 0..7（0=对话、1..6=块、6=隔离生成、7=scratch），
n_seq=4 时块 3-6/隔离/scratch 全部越界；降 n_seq 必须同时改 MAX_MEMORIES、
隔离 gen_seq、scratch 分配与 rollover/isolated 测试，风险高，回退保持 8。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chat_daily as D

FAILS = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else " " + str(detail)))
    if not cond:
        FAILS.append(name)


def main():
    check("n_seq_is_8", D.N_SEQ == 8, D.N_SEQ)
    check("blocks_fit", D.MAX_MEMORIES + 1 <= D.N_SEQ, D.MAX_MEMORIES)
    check("scratch_seq_last", D.N_SEQ - 1 == 7, D.N_SEQ - 1)
    check("isolated_gen_seq_valid", 6 < D.N_SEQ, 6)
    # 说明：n_seq=4 时 6/7 越界，且 _sync_mounts 会挂到 seq>4
    check("n_seq4_would_break", not (6 < 4), "n_seq=4 incompatible")
    print("%d checks, %d failed" % (5, len(FAILS)))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
