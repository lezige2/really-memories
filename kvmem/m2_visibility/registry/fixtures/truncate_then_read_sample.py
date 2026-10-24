# -*- coding: utf-8 -*-
"""纪律 21 的命中样例：同一语句里先截断后读。这条文件【必须】被 check_truncate_then_read.py 命中。
它不被任何东西执行，只用来证明那条检查不是永远为真的空断言。"""


def bad(path, old, new):
    import io
    io.open(path, "w").write(io.open(path).read().replace(old, new))
